from __future__ import annotations

from pathlib import Path

from src.adapters.persistence.json_item_repository import JsonItemRepository
from src.adapters.storage.local_file_persist_adapter import LocalFilePersistAdapter
from src.adapters.transcription.whisper_transcribe_adapter import WhisperTranscribeAdapter
from src.application.use_cases.items import DeleteItemUseCase, GetAudioPathUseCase, GetItemUseCase, ListItemsUseCase
from src.application.use_cases.transcribe import TranscribeUseCase


class AppContainer:
    def __init__(self, base_dir: Path) -> None:
        data_dir = base_dir / "data"

        self.file_persist = LocalFilePersistAdapter(base_dir=base_dir)
        self.repository = JsonItemRepository(items_path=data_dir / "items.json")
        self.transcriber = WhisperTranscribeAdapter(model_name="turbo", language="fr", task="transcribe")

        self.transcribe_use_case = TranscribeUseCase(
            repository=self.repository,
            file_persist=self.file_persist,
            transcriber=self.transcriber,
        )
        self.list_items_use_case = ListItemsUseCase(repository=self.repository, file_persist=self.file_persist)
        self.get_item_use_case = GetItemUseCase(repository=self.repository, file_persist=self.file_persist)
        self.get_audio_path_use_case = GetAudioPathUseCase(repository=self.repository, file_persist=self.file_persist)
        self.delete_item_use_case = DeleteItemUseCase(repository=self.repository, file_persist=self.file_persist)
