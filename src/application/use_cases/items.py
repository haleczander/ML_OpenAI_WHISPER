from __future__ import annotations

from src.application.ports import FilePersistPort, ItemRepositoryPort


class ListItemsUseCase:
    def __init__(self, repository: ItemRepositoryPort, file_persist: FilePersistPort) -> None:
        self._repository = repository
        self._file_persist = file_persist

    def execute(self) -> list[dict[str, str]]:
        items = sorted(self._repository.list_items(), key=lambda item: item.created_at, reverse=True)
        response: list[dict[str, str]] = []
        for item in items:
            payload = {
                "id": item.id,
                "created_at": item.created_at,
                "submitted_at": item.submitted_at or item.created_at,
                "transcribe_started_at": item.transcribe_started_at,
                "transcribe_finished_at": item.transcribe_finished_at,
                "audio_duration_seconds": item.audio_duration_seconds,
            }
            payload["transcript"] = _extract_post_processed(self._file_persist.read_text(item.transcript_path))
            response.append(payload)
        return response


class GetItemUseCase:
    def __init__(self, repository: ItemRepositoryPort, file_persist: FilePersistPort) -> None:
        self._repository = repository
        self._file_persist = file_persist

    def execute(self, item_id: str) -> dict[str, str] | None:
        item = self._repository.get_by_id(item_id)
        if not item:
            return None
        payload = {
            "id": item.id,
            "created_at": item.created_at,
            "submitted_at": item.submitted_at or item.created_at,
            "transcribe_started_at": item.transcribe_started_at,
            "transcribe_finished_at": item.transcribe_finished_at,
            "audio_duration_seconds": item.audio_duration_seconds,
        }
        payload["transcript"] = _extract_post_processed(self._file_persist.read_text(item.transcript_path))
        return payload


class GetAudioPathUseCase:
    def __init__(self, repository: ItemRepositoryPort, file_persist: FilePersistPort) -> None:
        self._repository = repository
        self._file_persist = file_persist

    def execute(self, item_id: str):
        item = self._repository.get_by_id(item_id)
        if not item:
            return None
        audio_path = self._file_persist.resolve(item.audio_path)
        if not audio_path.exists():
            return None
        return audio_path


class GetTranscriptPathUseCase:
    def __init__(self, repository: ItemRepositoryPort, file_persist: FilePersistPort) -> None:
        self._repository = repository
        self._file_persist = file_persist

    def execute(self, item_id: str):
        item = self._repository.get_by_id(item_id)
        if not item:
            return None
        transcript_path = self._file_persist.resolve(item.transcript_path)
        if not transcript_path.exists():
            return None
        return transcript_path


class DeleteItemUseCase:
    def __init__(self, repository: ItemRepositoryPort, file_persist: FilePersistPort) -> None:
        self._repository = repository
        self._file_persist = file_persist

    def execute(self, item_id: str) -> bool:
        target = self._repository.delete(item_id)
        if not target:
            return False

        self._file_persist.delete_file(target.audio_path)
        self._file_persist.delete_file(target.transcript_path)
        return True


def _extract_post_processed(content: str) -> str:
    marker = "=== POST_PROCESSED ==="
    if marker not in content:
        return content.strip()
    _, post = content.split(marker, 1)
    return post.strip()
