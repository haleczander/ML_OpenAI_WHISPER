from __future__ import annotations

import json
import subprocess
from pathlib import Path

from src.adapters.logging_utils import get_adapter_logger
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
        self._logger = get_adapter_logger("transcription_service")

    def transcribe_audio(self, audio_path: Path) -> tuple[str, str]:
        self._logger.info("transcribe_audio.start audio_path=%s", audio_path)
        raw_text = self._transcriber.transcribe(audio_path)
        self._logger.info("transcribe_audio.raw_ok audio_path=%s raw_len=%s", audio_path, len(raw_text))
        post_text = self._text_post_processor.process(raw_text)
        self._logger.info("transcribe_audio.post_ok audio_path=%s post_len=%s", audio_path, len(post_text))
        return raw_text, post_text

    @classmethod
    def build_transcript_file(cls, raw_text: str, post_text: str) -> str:
        return (
            f"{cls.RAW_HEADER}\n"
            f"{raw_text.strip()}\n\n"
            f"{cls.POST_HEADER}\n"
            f"{post_text.strip()}\n"
        )

    def probe_audio_duration_seconds(self, audio_path: Path) -> float:
        project_root = Path(__file__).resolve().parents[3]
        ffprobe_exe = project_root / "vendor" / "ffmpeg" / "bin" / "ffprobe.exe"
        if not ffprobe_exe.exists():
            self._logger.info("probe_audio_duration.skip reason=missing_ffprobe path=%s", ffprobe_exe)
            return 0.0
        try:
            output = subprocess.check_output(
                [
                    str(ffprobe_exe),
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
            self._logger.exception("probe_audio_duration.failure audio_path=%s", audio_path)
            return 0.0
