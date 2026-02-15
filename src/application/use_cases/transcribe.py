from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import time
import uuid

from src.application.ports import (
    FilePersistPort,
    ItemRepositoryPort,
    TextPostProcessorPort,
    TranscribePort,
)
from src.application.services.transcription_service import TranscriptionService
from src.domain.entities import Item


class TranscribeUseCase:
    def __init__(
        self,
        repository: ItemRepositoryPort,
        file_persist: FilePersistPort,
        transcriber: TranscribePort,
        text_post_processor: TextPostProcessorPort,
        transcription_service: TranscriptionService | None = None,
    ) -> None:
        self._repository = repository
        self._file_persist = file_persist
        self._transcription_service = transcription_service or TranscriptionService(
            file_persist=file_persist,
            transcriber=transcriber,
            text_post_processor=text_post_processor,
        )

    def from_upload(self, uploaded_file) -> tuple[Item, str]:
        filename = getattr(uploaded_file, "filename", "") or "audio.webm"
        suffix = Path(filename).suffix.lower() or ".webm"
        return self._transcribe_and_store(
            save_source=lambda relative_path: self._file_persist.save_uploaded_file(uploaded_file, relative_path),
            input_suffix=suffix,
            submitted_at=self._utc_now(),
        )

    def from_bytes(
        self,
        payload: bytes,
        extension: str = ".webm",
        submitted_at: str | None = None,
    ) -> tuple[Item, str]:
        suffix = extension if extension.startswith(".") else f".{extension}"
        return self._transcribe_and_store(
            save_source=lambda relative_path: self._file_persist.save_bytes(payload, relative_path),
            input_suffix=suffix,
            submitted_at=submitted_at or self._utc_now(),
        )

    def _transcribe_and_store(self, save_source, input_suffix: str, submitted_at: str) -> tuple[Item, str]:
        self._file_persist.ensure_dirs()

        item_id = uuid.uuid4().hex
        raw_path = f"data/audio/{item_id}{input_suffix}"
        t0 = time.perf_counter()
        save_source(raw_path)
        t_save = time.perf_counter()

        # Keep original uploaded format to avoid a full extra conversion pass.
        audio_path = raw_path
        audio_full_path = self._file_persist.resolve(audio_path)
        audio_duration_seconds = self._transcription_service.probe_audio_duration_seconds(audio_full_path)
        transcribe_started_at = self._utc_now()
        raw_transcript, transcript = self._transcription_service.transcribe_audio(audio_full_path)
        t_transcribe = time.perf_counter()
        transcribe_finished_at = self._utc_now()
        t_post = time.perf_counter()

        transcript_path = f"data/transcripts/{item_id}.txt"
        self._file_persist.write_text(
            transcript_path,
            self._transcription_service.build_transcript_file(raw_transcript, transcript),
        )
        t_write = time.perf_counter()

        item = Item(
            id=item_id,
            created_at=submitted_at,
            audio_path=audio_path,
            transcript_path=transcript_path,
            submitted_at=submitted_at,
            transcribe_started_at=transcribe_started_at,
            transcribe_finished_at=transcribe_finished_at,
            audio_duration_seconds=audio_duration_seconds,
        )
        self._repository.add(item)
        t_repo = time.perf_counter()
        print(
            "[transcribe]"
            f" id={item_id[:8]}"
            f" save={t_save - t0:.2f}s"
            f" whisper={t_transcribe - t_save:.2f}s"
            f" post={t_post - t_transcribe:.2f}s"
            f" write={t_write - t_post:.2f}s"
            f" repo={t_repo - t_write:.2f}s"
            f" total={t_repo - t0:.2f}s"
        )
        return item, transcript

    @staticmethod
    def _utc_now() -> str:
        return datetime.now(timezone.utc).isoformat()
