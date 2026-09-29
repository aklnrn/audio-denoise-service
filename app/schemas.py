from pydantic import BaseModel


class TaskCreateResponse(BaseModel):
    task_id: str
    status: str
    original_filename: str


class TaskStatusResponse(BaseModel):
    task_id: str
    status: str
    original_filename: str | None = None
    output_filename: str | None = None
    detail: str | None = None
