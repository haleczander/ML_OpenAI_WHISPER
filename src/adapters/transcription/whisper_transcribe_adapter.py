from __future__ import annotations

import os
from pathlib import Path
import subprocess
import tempfile
from threading import Lock

import torch
import whisper

from src.adapters.logging_utils import get_adapter_logger


class WhisperTranscribeAdapter:
    def __init__(
        self,
        model_name: str = "turbo",
        language: str = "fr",
        task: str = "transcribe",
    ) -> None:
        self._logger = get_adapter_logger("whisper_transcribe_adapter")
        self._ffmpeg_cmd = self._configure_bundled_ffmpeg()
        self._model_name = model_name
        self._language = language
        self._task = task
        self._device = "cuda" if torch.cuda.is_available() else "cpu"
        self._model_lock = Lock()
        self._logger.info(
            "init.start model=%s language=%s task=%s device=%s",
            model_name,
            language,
            task,
            self._device,
        )
        self._model = whisper.load_model(model_name, device=self._device)
        self._logger.info("init.success model=%s", model_name)

    def _configure_bundled_ffmpeg(self) -> str:
        project_root = Path(__file__).resolve().parents[3]
        ffmpeg_exe = project_root / "vendor" / "ffmpeg" / "bin" / "ffmpeg.exe"
        if not ffmpeg_exe.exists():
            raise RuntimeError(f"Bundled ffmpeg not found: {ffmpeg_exe}")

        ffmpeg_dir = str(ffmpeg_exe.parent.resolve())
        path_value = os.getenv("PATH", "")
        path_entries = path_value.split(os.pathsep) if path_value else []
        normalized_entries = {entry.strip().lower() for entry in path_entries}
        if ffmpeg_dir.strip().lower() in normalized_entries:
            self._logger.info("bundled_ffmpeg.path_already_set dir=%s", ffmpeg_dir)
        else:
            os.environ["PATH"] = ffmpeg_dir + os.pathsep + path_value if path_value else ffmpeg_dir
            self._logger.info("bundled_ffmpeg.path_injected dir=%s", ffmpeg_dir)
        self._logger.info("bundled_ffmpeg.selected exe=%s", ffmpeg_exe)
        return str(ffmpeg_exe)

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def device(self) -> str:
        return self._device

    def transcribe(self, audio_path: Path) -> str:
        self._logger.info("transcribe.start audio_path=%s", audio_path)
        transcribe_path, cleanup_path = self._prepare_mono_audio(audio_path)
        try:
            with self._model_lock:
                result = self._model.transcribe(
                    str(transcribe_path),
                    language=self._language,
                    task=self._task,
                    fp16=(self._device == "cuda"),
                    temperature=0.0,
                )
            text = result.get("text", "").strip()
            self._logger.info(
                "transcribe.success audio_path=%s normalized_path=%s text_len=%s",
                audio_path,
                transcribe_path,
                len(text),
            )
            return text
        except Exception as exc:
            self._logger.exception("transcribe.failure audio_path=%s error=%s", audio_path, exc)
            raise
        finally:
            if cleanup_path and cleanup_path.exists():
                cleanup_path.unlink()

    def _prepare_mono_audio(self, source_path: Path) -> tuple[Path, Path | None]:
        self._logger.info("prepare_mono_audio.start source_path=%s", source_path)
        ffmpeg_cmd = self._ffmpeg_cmd

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp_path = Path(tmp.name)

        try:
            subprocess.run(
                [
                    ffmpeg_cmd,
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
            self._logger.info(
                "prepare_mono_audio.success source_path=%s output_path=%s ffmpeg=%s",
                source_path,
                tmp_path,
                ffmpeg_cmd,
            )
            return tmp_path, tmp_path
        except subprocess.CalledProcessError as exc:
            self._logger.exception(
                "prepare_mono_audio.failure source_path=%s ffmpeg=%s error=%s",
                source_path,
                ffmpeg_cmd,
                exc,
            )
            if tmp_path.exists():
                tmp_path.unlink()
            return source_path, None
