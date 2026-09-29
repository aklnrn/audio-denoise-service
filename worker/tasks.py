import logging

from model.inference import denoise_audio
from worker.celery_app import celery_app


logger = logging.getLogger(__name__)


@celery_app.task(bind=True, name="worker.tasks.denoise_audio_task")
def denoise_audio_task(self, input_path: str, original_filename: str) -> dict:
    try:
        logger.info(f"START TASK: {self.request.id}")
        logger.info(f"Input path: {input_path}")
        logger.info(f"Original filename: {original_filename}")

        self.update_state(
            state="STARTED",
            meta={
                "task_id": self.request.id,
                "original_filename": original_filename,
                "detail": "Audio is being processed by DeepFilterNet",
            },
        )

        output_path, output_filename = denoise_audio(
            input_path=input_path,
            original_filename=original_filename,
            task_id=self.request.id,
        )

        logger.info(f"SUCCESS: output saved to {output_path}")

        return {
            "task_id": self.request.id,
            "status": "SUCCESS",
            "original_filename": original_filename,
            "output_filename": output_filename,
            "output_path": output_path,
            "detail": "Audio has been cleaned successfully",
        }

    except Exception as e:
        logger.exception("TASK FAILED")

        self.update_state(
            state="FAILURE",
            meta={
                "task_id": self.request.id,
                "original_filename": original_filename,
                "detail": str(e),
            },
        )

        raise e