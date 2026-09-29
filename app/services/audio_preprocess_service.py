import shutil
import subprocess
from pathlib import Path


SUPPORTED_AUDIO = {".wav", ".mp3", ".ogg", ".flac", ".m4a"}
SUPPORTED_VIDEO = {".mp4", ".mov", ".avi", ".mkv"}
SUPPORTED_MEDIA = SUPPORTED_AUDIO | SUPPORTED_VIDEO


def sanitize_filename(filename: str) -> str:
    if not filename:
        raise ValueError("Filename is empty")

    return Path(filename).name


def validate_media_extension(filename: str) -> str:
    safe_name = sanitize_filename(filename)
    ext = Path(safe_name).suffix.lower()

    if ext not in SUPPORTED_MEDIA:
        supported = ", ".join(sorted(SUPPORTED_MEDIA))
        raise ValueError(f"Unsupported file format: {ext}. Supported: {supported}")

    return safe_name


def convert_to_wav(input_path: str, output_path: str) -> None:
    command = [
        "ffmpeg",
        "-y",
        "-i",
        input_path,
        "-vn",
        "-ac",
        "1",
        "-ar",
        "16000",
        output_path,
    ]

    subprocess.run(command, check=True)


def preprocess_uploaded_file(input_path: str, task_id: str, input_dir: str) -> str:
    input_file = Path(input_path)
    ext = input_file.suffix.lower()

    output_dir = Path(input_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    output_wav = output_dir / f"{task_id}.wav"

    if ext == ".wav":
        if input_file.resolve() != output_wav.resolve():
            shutil.copy2(input_file, output_wav)
        return str(output_wav)

    if ext in SUPPORTED_AUDIO or ext in SUPPORTED_VIDEO:
        convert_to_wav(str(input_file), str(output_wav))
        return str(output_wav)

    raise ValueError(f"Unsupported file format: {ext}")
