from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Audio Denoise Service"
    app_host: str = "0.0.0.0"
    app_port: int = 8000

    input_dir: str = "/app/data/input"
    output_dir: str = "/app/data/output"

    supported_audio_extensions: str = ".wav,.mp3,.ogg,.flac,.m4a"
    supported_video_extensions: str = ".mp4,.mov,.avi,.mkv"
    result_suffix: str = "_cleaned.wav"

    celery_broker_url: str = "redis://redis:6379/0"
    celery_result_backend: str = "redis://redis:6379/1"

    task_time_limit: int = 3600
    task_soft_time_limit: int = 3500

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
