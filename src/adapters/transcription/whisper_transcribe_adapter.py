from __future__ import annotations

from pathlib import Path

import torch
import whisper


class WhisperTranscribeAdapter:
    def __init__(self, model_name: str = "turbo", language: str = "fr", task: str = "transcribe") -> None:
        self._model_name = model_name
        self._language = language
        self._task = task
        self._device = "cuda" if torch.cuda.is_available() else "cpu"
        self._model = whisper.load_model(model_name, device=self._device)

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def device(self) -> str:
        return self._device

    def transcribe(self, audio_path: Path) -> str:
        result = self._model.transcribe(
            str(audio_path),
            language=self._language,
            task=self._task,
            fp16=(self._device == "cuda"),
            temperature=0.0,
        )
        return result.get("text", "").strip()
