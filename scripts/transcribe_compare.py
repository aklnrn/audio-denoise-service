import argparse
import json
import re
import subprocess
import time
from pathlib import Path

import requests
from faster_whisper import WhisperModel
from jiwer import wer


def normalize_text(text):
    if text is None:
        return ""

    text = text.lower().replace("ё", "е")
    return text


def convert_to_wav(source_path: Path, wav_path: Path) -> None:
    if source_path.suffix.lower() == ".wav":
        wav_path.write_bytes(source_path.read_bytes())
        return

    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(source_path),
        "-vn",
        "-ac",
        "1",
        "-ar",
        "16000",
        str(wav_path),
    ]
    subprocess.run(cmd, check=True)

def transcribe(model: WhisperModel, wav_path: Path, language: str) -> str:
    segments, _ = model.transcribe(
        str(wav_path),
        language=language,
        beam_size=1
    )

    text = ""
    for segment in segments:
        text += segment.text

    return text.strip()


def submit_task(api_url: str, media_path: Path) -> str:
    with media_path.open("rb") as stream:
        response = requests.post(
            f"{api_url}/tasks/denoise",
            files={"file": (media_path.name, stream)},
            timeout=120,
        )

    response.raise_for_status()
    payload = response.json()
    return payload["task_id"]


def wait_for_task(api_url: str, task_id: str, poll_interval: int, timeout_seconds: int) -> dict:
    started_at = time.time()

    while True:
        response = requests.get(f"{api_url}/tasks/{task_id}", timeout=60)
        response.raise_for_status()
        payload = response.json()

        status = payload.get("status")
        if status in {"SUCCESS", "FAILURE"}:
            return payload

        if time.time() - started_at > timeout_seconds:
            raise TimeoutError(f"Task {task_id} did not finish in {timeout_seconds} seconds")

        time.sleep(poll_interval)


def download_result(api_url: str, task_id: str, output_path: Path) -> None:
    response = requests.get(f"{api_url}/tasks/{task_id}/download", timeout=300)
    response.raise_for_status()
    output_path.write_bytes(response.content)


def run_demucs(input_wav: Path, output_wav: Path):
    import subprocess
    import shutil

    cmd = [
        "demucs",
        "-n", "htdemucs",
        "--two-stems=vocals",
        str(input_wav),
    ]
    subprocess.run(cmd, check=True)

    separated_dir = Path("separated/htdemucs") / input_wav.stem
    vocals_path = separated_dir / "vocals.wav"

    if not vocals_path.exists():
        raise FileNotFoundError(f"Demucs output not found: {vocals_path}")

    output_wav.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(vocals_path, output_wav)


def save_copy(src: Path, dst: Path):
    import shutil
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(src, dst)


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare: original vs deepfilter vs demucs")

    parser.add_argument("--api-url", default="http://localhost:8000")
    parser.add_argument("--input-file", required=True)
    parser.add_argument("--reference-file", required=True)

    parser.add_argument("--language", default="ru")
    parser.add_argument("--whisper-model", default="small")

    args = parser.parse_args()

    input_path = Path(args.input_file).resolve()
    reference_path = Path(args.reference_file).resolve()
    output_dir = Path("evaluation/results")
    output_dir.mkdir(parents=True, exist_ok=True)

    reference_text = reference_path.read_text(encoding="utf-8")

    task_id = submit_task(args.api_url, input_path)
    print(f"Task created: {task_id}")

    original_wav = output_dir / f"{task_id}_original.wav"
    deepfilter_wav = output_dir / f"{task_id}_cleaned_deepfilternet.wav"
    demucs_wav = output_dir / f"{task_id}_cleaned_demucs.wav"

    deepfilter_data = Path(f"data/output/deepfilternet/{task_id}_{input_path.stem}_cleaned.wav")
    demucs_data = Path(f"data/output/demucs/{task_id}_{input_path.stem}_cleaned.wav")

    # original
    convert_to_wav(input_path, original_wav)

    task_result = wait_for_task(
        args.api_url,
        task_id,
        poll_interval=5,
        timeout_seconds=600,
    )

    # deepfilternet
    download_result(args.api_url, task_id, deepfilter_wav)

    save_copy(deepfilter_wav, deepfilter_data)

    # demucs
    print("Running Demucs")
    run_demucs(original_wav, demucs_wav)

    save_copy(demucs_wav, demucs_data)

    model = WhisperModel(args.whisper_model, device="cpu", compute_type="int8")

    print("Transcribing Original")
    original_text = transcribe(model, original_wav, args.language)

    print("Transcribing Deepfilternet")
    deep_text = transcribe(model, deepfilter_wav, args.language)

    print("Transcribing Demucs")
    demucs_text = transcribe(model, demucs_wav, args.language)


    ref_norm = normalize_text(reference_text)

    if original_text is None:
        print("Original transcription is None")

    orig_norm = normalize_text(original_text)

    if deep_text is None:
        print("DeepFilter transcription is None")

    deep_norm = normalize_text(deep_text)

    if demucs_text is None:
        print("Demucs transcription is None")

    demucs_norm = normalize_text(demucs_text)


    orig_wer = wer(ref_norm, orig_norm)
    deep_wer = wer(ref_norm, deep_norm)
    demucs_wer = wer(ref_norm, demucs_norm)


    print("\nRESULT")
    print(f"Original WER:     {orig_wer:.4f}")
    print(f"DeepFilter WER:   {deep_wer:.4f}")
    print(f"Demucs WER:       {demucs_wer:.4f}")

    print(f"DeepFilter: {orig_wer - deep_wer:+.4f}")
    print(f"Demucs:     {orig_wer - demucs_wer:+.4f}")

    best = min({
        "original": orig_wer,
        "deepfilter": deep_wer,
        "demucs": demucs_wer
    }, key=lambda x: {
        "original": orig_wer,
        "deepfilter": deep_wer,
        "demucs": demucs_wer
    }[x])

    print(f"\nBEST: {best.upper()}")

    summary = {
        "task_id": task_id,
        "input_file": str(input_path),
        "reference_file": str(reference_path),

        "original_wav": str(original_wav),
        "deepfilter_wav": str(deepfilter_wav),
        "demucs_wav": str(demucs_wav),

        "original_transcript": original_text,
        "deepfilter_transcript": deep_text,
        "demucs_transcript": demucs_text,

        "original_wer": orig_wer,
        "deepfilter_wer": deep_wer,
        "demucs_wer": demucs_wer,

        "wer_delta_deepfilter": orig_wer - deep_wer,
        "wer_delta_demucs": orig_wer - demucs_wer,

        "best": best
    }

    report_path = output_dir / f"{task_id}_report.json"
    report_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"\nReport saved to: {report_path}")

if __name__ == "__main__":
    main()