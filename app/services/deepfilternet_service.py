import torchaudio
from df.enhance import enhance, init_df


def clean_audio_deepfilternet(input_path: str, output_path: str) -> None:
    model, df_state, _ = init_df()

    waveform, sr = torchaudio.load(input_path)
    waveform = waveform.float()

    target_sr = 48000

    if sr != target_sr:
        waveform = torchaudio.transforms.Resample(sr, target_sr)(waveform)
        sr = target_sr

    if waveform.dim() == 1:
        waveform = waveform.unsqueeze(0)

    enhanced = enhance(model, df_state, waveform)

    torchaudio.save(output_path, enhanced, sr)
