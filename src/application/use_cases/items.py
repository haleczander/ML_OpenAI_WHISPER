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
            payload = item.to_dict()
            payload["transcript"] = self._file_persist.read_text(item.transcript_path).strip()
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
        payload = item.to_dict()
        payload["transcript"] = self._file_persist.read_text(item.transcript_path).strip()
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
