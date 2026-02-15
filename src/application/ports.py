from __future__ import annotations

from pathlib import Path
from typing import Protocol

from src.domain.entities import Item


class ItemRepositoryPort(Protocol):
    def list_items(self) -> list[Item]:
        ...

    def get_by_id(self, item_id: str) -> Item | None:
        ...

    def add(self, item: Item) -> None:
        ...

    def delete(self, item_id: str) -> Item | None:
        ...


class FilePersistPort(Protocol):
    def ensure_dirs(self) -> None:
        ...

    def save_uploaded_file(self, file_obj, relative_path: str) -> None:
        ...

    def save_bytes(self, payload: bytes, relative_path: str) -> None:
        ...

    def convert_to_mp3_if_possible(self, src_relative_path: str) -> str:
        ...

    def write_text(self, relative_path: str, content: str) -> None:
        ...

    def read_text(self, relative_path: str) -> str:
        ...

    def delete_file(self, relative_path: str) -> None:
        ...

    def resolve(self, relative_path: str) -> Path:
        ...


class TranscribePort(Protocol):
    def transcribe(self, audio_path: Path) -> str:
        ...

    @property
    def model_name(self) -> str:
        ...

    @property
    def device(self) -> str:
        ...
