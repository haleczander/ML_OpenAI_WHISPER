from __future__ import annotations

from pathlib import Path
import shutil
import subprocess
import tempfile

import torch
import whisper


class WhisperTranscribeAdapter:
    def __init__(
        self,
        model_name: str = "turbo",
        language: str = "fr",
        task: str = "transcribe",
    ) -> None:
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
        transcribe_path, cleanup_path = self._prepare_mono_audio(audio_path)
        try:
            result = self._model.transcribe(
                str(transcribe_path),
                language=self._language,
                task=self._task,
                fp16=(self._device == "cuda"),
                temperature=0.0,
            )
            return result.get("text", "").strip()
        finally:
            if cleanup_path and cleanup_path.exists():
                cleanup_path.unlink()

    def _prepare_mono_audio(self, source_path: Path) -> tuple[Path, Path | None]:
        if shutil.which("ffmpeg") is None:
            return source_path, None

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp_path = Path(tmp.name)

        try:
            subprocess.run(
                [
                    "ffmpeg",
                    "-y",
                    "-i",
                    str(source_path),
                    "-ac",
                    "1",
                    "-ar",
                    "16000",
                    str(tmp_path),
                ],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            return tmp_path, tmp_path
        except subprocess.CalledProcessError:
            if tmp_path.exists():
                tmp_path.unlink()
            return source_path, None
