from pathlib import Path

import torch
import whisper


def main() -> int:
    audio_path = Path("sample3.mp3")
    model_name = "turbo"
    language = "fr"
    task = "transcribe"
    out_path = None

    if not audio_path.exists():
        raise SystemExit(f"Audio file not found: {audio_path}")

    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(device)
    model = whisper.load_model(model_name, device=device)

    result = model.transcribe(
        str(audio_path),
        language=language,
        task=task,
        fp16=(device == "cuda"),
    )

    text = result.get("text", "").strip()
    if out_path:
        Path(out_path).write_text(text + "\n", encoding="utf-8")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
