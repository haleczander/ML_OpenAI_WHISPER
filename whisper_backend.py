from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Dict, Tuple

from faster_whisper import WhisperModel


@dataclass(frozen=True)
class BackendConfig:
    model_name: str = os.getenv("WHISPER_MODEL", "large-v3")
    device: str = os.getenv("WHISPER_DEVICE", "auto")
    compute_type: str = os.getenv("WHISPER_COMPUTE_TYPE", "auto")
    cpu_threads: int = int(os.getenv("WHISPER_CPU_THREADS", "0"))
    num_workers: int = int(os.getenv("WHISPER_NUM_WORKERS", "1"))


def _pick_device(requested_device: str) -> str:
    if requested_device in {"cpu", "cuda"}:
        return requested_device
    try:
        import torch

        return "cuda" if torch.cuda.is_available() else "cpu"
    except Exception:
        return "cpu"


def _pick_compute_type(device: str, requested_compute_type: str) -> str:
    if requested_compute_type != "auto":
        return requested_compute_type
    if device == "cuda":
        return "float16"
    return "int8_float32"


def load_model(config: BackendConfig) -> Tuple[WhisperModel, Dict[str, Any]]:
    device = _pick_device(config.device)
    compute_type = _pick_compute_type(device, config.compute_type)
    cpu_threads = max(0, config.cpu_threads)
    num_workers = max(1, config.num_workers)
    model = WhisperModel(
        config.model_name,
        device=device,
        compute_type=compute_type,
        cpu_threads=cpu_threads,
        num_workers=num_workers,
    )
    info = {
        "backend": "faster-whisper",
        "model": config.model_name,
        "device": device,
        "compute_type": compute_type,
    }
    return model, info


def transcribe_text(
    model: WhisperModel,
    audio_input: Any,
    language: str,
    task: str,
    *,
    temperature: float = 0.0,
    beam_size: int = 5,
    best_of: int = 5,
    vad_filter: bool = False,
) -> str:
    segments, _ = model.transcribe(
        audio_input,
        language=language,
        task=task,
        temperature=temperature,
        beam_size=beam_size,
        best_of=best_of,
        vad_filter=vad_filter,
    )
    return " ".join(segment.text.strip() for segment in segments).strip()
