from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

from src.application.ports import FilePersistPort, TextPostProcessorPort, TranscribePort


class TranscriptionService:
    RAW_HEADER = "=== WHISPER_RAW ==="
    POST_HEADER = "=== POST_PROCESSED ==="

    def __init__(
        self,
        file_persist: FilePersistPort,
        transcriber: TranscribePort,
        text_post_processor: TextPostProcessorPort,
    ) -> None:
        self._file_persist = file_persist
        self._transcriber = transcriber
        self._text_post_processor = text_post_processor

    def transcribe_audio(self, audio_path: Path) -> tuple[str, str]:
        raw_text = self._transcriber.transcribe(audio_path)
        post_text = self._text_post_processor.process(raw_text)
        return raw_text, post_text

    @classmethod
    def build_transcript_file(cls, raw_text: str, post_text: str) -> str:
        return (
            f"{cls.RAW_HEADER}\n"
            f"{raw_text.strip()}\n\n"
            f"{cls.POST_HEADER}\n"
            f"{post_text.strip()}\n"
        )

    @staticmethod
    def probe_audio_duration_seconds(audio_path: Path) -> float:
        if shutil.which("ffprobe") is None:
            return 0.0
        try:
            output = subprocess.check_output(
                [
                    "ffprobe",
                    "-v",
                    "quiet",
                    "-print_format",
                    "json",
                    "-show_format",
                    str(audio_path),
                ],
                stderr=subprocess.DEVNULL,
            )
            payload = json.loads(output.decode("utf-8", errors="ignore"))
            duration = payload.get("format", {}).get("duration", 0.0)
            return float(duration)
        except (subprocess.CalledProcessError, json.JSONDecodeError, ValueError, TypeError):
            return 0.0
