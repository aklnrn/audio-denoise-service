from pathlib import Path

import pytest

from app.services.audio_preprocess_service import (
    preprocess_uploaded_file,
    validate_media_extension,
)


def test_validate_media_extension_accepts_audio_and_video() -> None:
    assert validate_media_extension("voice.wav") == "voice.wav"
    assert validate_media_extension("clip.mp4") == "clip.mp4"


def test_validate_media_extension_rejects_unknown_extension() -> None:
    with pytest.raises(ValueError):
        validate_media_extension("notes.txt")


def test_preprocess_uploaded_wav_keeps_only_task_wav(tmp_path: Path) -> None:
    source = tmp_path / "source.wav"
    source.write_bytes(b"wav-data")

    result = preprocess_uploaded_file(
        input_path=str(source),
        task_id="task123",
        input_dir=str(tmp_path),
    )

    output = Path(result)
    assert output.name == "task123.wav"
    assert output.exists()
    assert output.read_bytes() == b"wav-data"


def test_preprocess_uploaded_video_converts_to_wav(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    source = tmp_path / "source.mp4"
    source.write_bytes(b"video-data")

    def fake_convert_to_wav(input_path: str, output_path: str) -> None:
        assert input_path.endswith("source.mp4")
        Path(output_path).write_bytes(b"converted-wav")

    monkeypatch.setattr(
        "app.services.audio_preprocess_service.convert_to_wav",
        fake_convert_to_wav,
    )

    result = preprocess_uploaded_file(
        input_path=str(source),
        task_id="task999",
        input_dir=str(tmp_path),
    )

    output = Path(result)
    assert output.name == "task999.wav"
    assert output.exists()
    assert output.read_bytes() == b"converted-wav"
