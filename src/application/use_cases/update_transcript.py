from __future__ import annotations

from datetime import datetime, timezone
from threading import Lock

from src.application.ports import FilePersistPort, ItemRepositoryPort
from src.application.services.transcription_service import TranscriptionService
from src.domain.entities import Item


class UpdateTranscriptUseCase:
    def __init__(self, repository: ItemRepositoryPort, file_persist: FilePersistPort) -> None:
        self._repository = repository
        self._file_persist = file_persist
        self._lock = Lock()

    def execute(self, item_id: str, transcript: str, revision: int, force: bool = False) -> tuple[str, dict | None]:
        # The JSON repository has no transaction support; serialise check/write/upsert.
        with self._lock:
            return self._execute_locked(item_id, transcript, revision, force)

    def _execute_locked(self, item_id: str, transcript: str, revision: int, force: bool) -> tuple[str, dict | None]:
        item = self._repository.get_by_id(item_id)
        if not item:
            return "not_found", None
        if revision != item.revision and not force:
            return "conflict", self._payload(item)

        existing = self._file_persist.read_text(item.transcript_path)
        self._file_persist.write_text(
            item.transcript_path,
            TranscriptionService.replace_post_processed(existing, transcript),
        )
        updated = Item(
            id=item.id, created_at=item.created_at, audio_path=item.audio_path,
            transcript_path=item.transcript_path, submitted_at=item.submitted_at,
            transcribe_started_at=item.transcribe_started_at,
            transcribe_finished_at=item.transcribe_finished_at,
            audio_duration_seconds=item.audio_duration_seconds, revision=item.revision + 1,
            updated_at=datetime.now(timezone.utc).isoformat(), manually_edited=True,
        )
        self._repository.upsert(updated)
        return "ok", self._payload(updated)

    def _payload(self, item: Item) -> dict:
        return {
            "id": item.id,
            "transcript": _extract_post_processed(self._file_persist.read_text(item.transcript_path)),
            "revision": item.revision,
            "updated_at": item.updated_at,
            "manually_edited": item.manually_edited,
        }


def _extract_post_processed(content: str) -> str:
    marker = TranscriptionService.POST_HEADER
    return content.split(marker, 1)[1].strip() if marker in content else content.strip()
