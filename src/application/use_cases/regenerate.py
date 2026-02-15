from __future__ import annotations

from datetime import datetime, timezone

from src.application.ports import FilePersistPort, ItemRepositoryPort
from src.application.services.transcription_service import TranscriptionService
from src.domain.entities import Item


class RegenerateTranscriptUseCase:
    def __init__(
        self,
        repository: ItemRepositoryPort,
        file_persist: FilePersistPort,
        transcription_service: TranscriptionService,
    ) -> None:
        self._repository = repository
        self._file_persist = file_persist
        self._transcription_service = transcription_service

    def execute(self, item_id: str) -> tuple[bool, str]:
        item = self._repository.get_by_id(item_id)
        if not item:
            return False, "item_not_found"

        audio_path = self._file_persist.resolve(item.audio_path)
        if not audio_path.exists():
            return False, "audio_not_found"

        transcribe_started_at = self._utc_now()
        raw_transcript, transcript = self._transcription_service.transcribe_audio(audio_path)
        transcribe_finished_at = self._utc_now()

        self._file_persist.write_text(
            item.transcript_path,
            self._transcription_service.build_transcript_file(raw_transcript, transcript),
        )

        updated_item = Item(
            id=item.id,
            created_at=item.created_at,
            audio_path=item.audio_path,
            transcript_path=item.transcript_path,
            submitted_at=item.submitted_at or item.created_at,
            transcribe_started_at=transcribe_started_at,
            transcribe_finished_at=transcribe_finished_at,
            audio_duration_seconds=self._transcription_service.probe_audio_duration_seconds(audio_path),
        )
        self._repository.upsert(updated_item)
        return True, transcript

    @staticmethod
    def _utc_now() -> str:
        return datetime.now(timezone.utc).isoformat()
