from __future__ import annotations

import json
from pathlib import Path

from src.domain.entities import Item


class JsonItemRepository:
    def __init__(self, items_path: Path) -> None:
        self._items_path = items_path

    def list_items(self) -> list[Item]:
        payload = self._load_payload()
        return [Item.from_dict(entry) for entry in payload if _is_valid(entry)]

    def get_by_id(self, item_id: str) -> Item | None:
        for item in self.list_items():
            if item.id == item_id:
                return item
        return None

    def add(self, item: Item) -> None:
        items = self.list_items()
        items.append(item)
        self._save_items(items)

    def upsert(self, item: Item) -> None:
        items = self.list_items()
        updated = False
        result: list[Item] = []
        for existing in items:
            if existing.id == item.id:
                result.append(item)
                updated = True
            else:
                result.append(existing)
        if not updated:
            result.append(item)
        self._save_items(result)

    def delete(self, item_id: str) -> Item | None:
        items = self.list_items()
        remaining: list[Item] = []
        deleted: Item | None = None

        for item in items:
            if item.id == item_id:
                deleted = item
            else:
                remaining.append(item)

        if deleted:
            self._save_items(remaining)
        return deleted

    def _load_payload(self) -> list[dict[str, str]]:
        if not self._items_path.exists():
            return []
        try:
            raw = json.loads(self._items_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return []

        if not isinstance(raw, list):
            return []
        return [entry for entry in raw if isinstance(entry, dict)]

    def _save_items(self, items: list[Item]) -> None:
        self._items_path.parent.mkdir(parents=True, exist_ok=True)
        serialized = [item.to_dict() for item in items]
        self._items_path.write_text(json.dumps(serialized, indent=2), encoding="utf-8")


def _is_valid(entry: dict[str, str]) -> bool:
    required = {"id", "created_at", "audio_path", "transcript_path"}
    return required.issubset(entry.keys())
