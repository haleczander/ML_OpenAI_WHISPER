from pathlib import Path

from whisper_backend import BackendConfig, load_model, transcribe_text


def main() -> int:
    audio_path = Path("sample3.mp3")
    language = "fr"
    task = "transcribe"
    out_path = None

    if not audio_path.exists():
        raise SystemExit(f"Audio file not found: {audio_path}")

    model, backend_info = load_model(BackendConfig())
    print(f"{backend_info['backend']} | {backend_info['device']} | {backend_info['compute_type']}")

    text = transcribe_text(
        model,
        str(audio_path),
        language=language,
        task=task,
        temperature=0.0,
    )

    if out_path:
        Path(out_path).write_text(text + "\n", encoding="utf-8")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
