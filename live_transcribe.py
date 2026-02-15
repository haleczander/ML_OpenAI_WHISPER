import queue
import time
from dataclasses import dataclass
import os

import numpy as np
import sounddevice as sd

from whisper_backend import BackendConfig, load_model, transcribe_text


@dataclass
class Config:
    model_name: str = os.getenv("WHISPER_MODEL", "large-v3")
    language: str = "fr"
    task: str = "transcribe"
    out_path: str = "live_transcript.txt"
    sample_rate: int = 16000
    stride_seconds: float = 3.0
    window_seconds: float = 9.0
    channels: int = 1
    history_limit: int = 400
    max_overlap_check: int = 120


def transcribe_chunk(model, audio_chunk: np.ndarray, config: Config) -> str:
    return transcribe_text(
        model,
        audio_chunk,
        language=config.language,
        task=config.task,
        temperature=0.0,
        vad_filter=False,
    )


def dedupe_output(history: str, text: str, config: Config):
    max_overlap = 0
    history = history[-config.history_limit :]
    max_check = min(len(history), len(text), config.max_overlap_check)
    for i in range(1, max_check + 1):
        if history[-i:] == text[:i]:
            max_overlap = i
    new_part = text[max_overlap:].lstrip()
    if new_part:
        history = (history + " " + new_part).strip()
    return new_part, history


def drain_queue(q: queue.Queue[np.ndarray], full_audio: np.ndarray) -> np.ndarray:
    while True:
        try:
            block = q.get_nowait()
        except queue.Empty:
            break
        full_audio = np.concatenate([full_audio, block[:, 0]])
    return full_audio


def write_text(path: str, text: str) -> None:
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(text + "\n")


def main() -> int:
    config = Config()
    stride_samples = int(config.stride_seconds * config.sample_rate)
    window_samples = int(config.window_seconds * config.sample_rate)

    model, backend_info = load_model(BackendConfig(model_name=config.model_name))
    print(f"Using {backend_info['backend']} | {backend_info['model']} | {backend_info['device']} | {backend_info['compute_type']}")

    q: queue.Queue[np.ndarray] = queue.Queue()
    full_audio = np.zeros((0,), dtype=np.float32)
    history = ""
    last_text = ""
    last_transcribe = 0.0
    next_emit_samples = stride_samples

    def audio_callback(indata, frames, time_info, status) -> None:
        if status:
            print(f"[audio] {status}")
        q.put(indata.copy())

    if config.out_path:
        write_text(config.out_path, "")

    print("Listening... press Ctrl+C to stop.")
    with sd.InputStream(
        channels=config.channels,
        samplerate=config.sample_rate,
        dtype="float32",
        callback=audio_callback,
    ):
        try:
            while True:
                block = q.get()
                full_audio = np.concatenate([full_audio, block[:, 0]])

                now = time.time()
                if full_audio.size >= next_emit_samples and (now - last_transcribe) >= config.stride_seconds:
                    end = next_emit_samples
                    start = max(0, end - window_samples)
                    audio_chunk = full_audio[start:end]

                    text = transcribe_chunk(model, audio_chunk, config)
                    if text:
                        new_part, history = dedupe_output(history, text, config)
                        if new_part:
                            print(new_part)
                            if config.out_path:
                                write_text(config.out_path, history)
                        elif text != last_text:
                            print(text)
                            history = text
                            if config.out_path:
                                write_text(config.out_path, history)
                        last_text = text

                    next_emit_samples += stride_samples
                    last_transcribe = now
        except KeyboardInterrupt:
            print("\nStopped. Finalizing transcription...")
            full_audio = drain_queue(q, full_audio)
            if full_audio.size > 0:
                final_text = transcribe_chunk(model, full_audio, config)
                if final_text:
                    print("\nFull transcript:")
                    print(final_text)
                    if config.out_path:
                        write_text(config.out_path, final_text)
            else:
                print("No audio captured.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
