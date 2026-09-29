from pathlib import Path

from app.config import get_settings
from app.services.deepfilternet_service import clean_audio_deepfilternet

settings = get_settings()

OUTPUT_DIR = Path(str(settings.output_dir))
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def denoise_audio(input_path: str, original_filename: str, task_id: str) -> tuple[str, str]:
    input_file = Path(input_path)

    if not input_file.exists():
        raise FileNotFoundError(f"Input file not found: {input_file}")

    output_dir = OUTPUT_DIR / "deepfilternet"
    output_dir.mkdir(parents=True, exist_ok=True)

    clean_name = f"{Path(original_filename).stem}{settings.result_suffix}"
    stored_output_name = f"{task_id}_{clean_name}"

    output_path = output_dir / stored_output_name

    clean_audio_deepfilternet(str(input_file), str(output_path))

    return str(output_path), clean_name
