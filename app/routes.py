import shutil
from pathlib import Path
from tempfile import NamedTemporaryFile
from uuid import uuid4

from celery.result import AsyncResult
from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import FileResponse

from app.config import get_settings
from app.schemas import TaskCreateResponse, TaskStatusResponse
from app.services.audio_preprocess_service import (
    preprocess_uploaded_file,
    validate_media_extension,
)
from worker.celery_app import celery_app

router = APIRouter(prefix="/tasks", tags=["tasks"])

settings = get_settings()

INPUT_DIR = Path(settings.input_dir)
OUTPUT_DIR = Path(settings.output_dir)

INPUT_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def save_upload_to_temp_file(upload_file: UploadFile, suffix: str) -> Path:
    with NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
        shutil.copyfileobj(upload_file.file, temp_file)
        return Path(temp_file.name)


@router.post("/denoise", response_model=TaskCreateResponse)
async def create_denoise_task(file: UploadFile = File(...)):
    try:
        original_filename = validate_media_extension(file.filename)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    task_id = uuid4().hex
    input_suffix = Path(original_filename).suffix.lower()
    temp_input_path = save_upload_to_temp_file(file, input_suffix)

    try:
        prepared_input_path = preprocess_uploaded_file(
            input_path=str(temp_input_path),
            task_id=task_id,
            input_dir=str(INPUT_DIR),
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to preprocess uploaded file: {exc}",
        ) from exc
    finally:
        temp_input_path.unlink(missing_ok=True)

    celery_app.send_task(
        "worker.tasks.denoise_audio_task",
        args=[prepared_input_path, original_filename],
        task_id=task_id,
    )

    return TaskCreateResponse(
        task_id=task_id,
        status="PENDING",
        original_filename=original_filename,
    )


@router.get("/{task_id}", response_model=TaskStatusResponse)
def get_task_status(task_id: str):
    task_result = AsyncResult(task_id, app=celery_app)
    status = task_result.status

    if status == "PENDING":
        return TaskStatusResponse(
            task_id=task_id,
            status="PENDING",
            detail="Task is waiting in the queue",
        )

    if status == "STARTED":
        meta = task_result.info if isinstance(task_result.info, dict) else {}
        return TaskStatusResponse(
            task_id=task_id,
            status="STARTED",
            original_filename=meta.get("original_filename"),
            detail=meta.get("detail", "Task is being processed"),
        )

    if status == "SUCCESS":
        result_data = task_result.result if isinstance(task_result.result, dict) else {}
        return TaskStatusResponse(
            task_id=task_id,
            status="SUCCESS",
            original_filename=result_data.get("original_filename"),
            output_filename=result_data.get("output_filename"),
            detail=result_data.get("detail", "Task completed successfully"),
        )

    if status == "FAILURE":
        return TaskStatusResponse(
            task_id=task_id,
            status="FAILURE",
            detail=str(task_result.result),
        )

    return TaskStatusResponse(
        task_id=task_id,
        status=status,
        detail="Unknown task state",
    )


@router.get("/{task_id}/download")
def download_result(task_id: str):
    task_result = AsyncResult(task_id, app=celery_app)

    if task_result.status != "SUCCESS":
        raise HTTPException(
            status_code=409,
            detail=f"Task is not ready. Current status: {task_result.status}",
        )

    result_data = task_result.result if isinstance(task_result.result, dict) else {}

    output_path = result_data.get("output_path")
    output_filename = result_data.get("output_filename")

    if not output_path or not output_filename:
        raise HTTPException(
            status_code=500,
            detail="Task finished but output metadata is missing",
        )

    file_path = Path(output_path)

    if not file_path.exists():
        raise HTTPException(
            status_code=404,
            detail="Processed file was not found on server",
        )

    return FileResponse(
        path=file_path,
        media_type="audio/wav",
        filename=output_filename,
    )