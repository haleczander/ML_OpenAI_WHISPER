from __future__ import annotations

import json
from pathlib import Path

from src.adapters.logging_utils import get_adapter_logger
from src.domain.entities import Item


class JsonItemRepository:
    def __init__(self, items_path: Path) -> None:
        self._logger = get_adapter_logger("json_item_repository")
        self._items_path = items_path
        self._logger.info("init.start items_path=%s", items_path)
        self._ensure_store()
        self._logger.info("init.success items_path=%s", items_path)

    def list_items(self) -> list[Item]:
        self._logger.info("list_items.start")
        payload = self._load_payload()
        items = [Item.from_dict(entry) for entry in payload if _is_valid(entry)]
        self._logger.info("list_items.success count=%s", len(items))
        return items

    def get_by_id(self, item_id: str) -> Item | None:
        self._logger.info("get_by_id.start item_id=%s", item_id)
        for item in self.list_items():
            if item.id == item_id:
                self._logger.info("get_by_id.success item_id=%s found=true", item_id)
                return item
        self._logger.info("get_by_id.success item_id=%s found=false", item_id)
        return None

    def add(self, item: Item) -> None:
        self._logger.info("add.start item_id=%s", item.id)
        items = self.list_items()
        items.append(item)
        self._save_items(items)
        self._logger.info("add.success item_id=%s total=%s", item.id, len(items))

    def upsert(self, item: Item) -> None:
        self._logger.info("upsert.start item_id=%s", item.id)
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
        self._logger.info("upsert.success item_id=%s updated=%s total=%s", item.id, updated, len(result))

    def delete(self, item_id: str) -> Item | None:
        self._logger.info("delete.start item_id=%s", item_id)
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
        self._logger.info("delete.success item_id=%s deleted=%s total=%s", item_id, deleted is not None, len(remaining))
        return deleted

    def _load_payload(self) -> list[dict[str, str]]:
        self._logger.info("load_payload.start path=%s", self._items_path)
        if not self._items_path.exists():
            self._logger.info("load_payload.success path=%s count=0 missing=true", self._items_path)
            return []
        try:
            raw = json.loads(self._items_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            self._logger.exception("load_payload.failure path=%s error=%s", self._items_path, exc)
            return []

        if not isinstance(raw, list):
            self._logger.info("load_payload.success path=%s count=0 invalid_type=true", self._items_path)
            return []
        payload = [entry for entry in raw if isinstance(entry, dict)]
        self._logger.info("load_payload.success path=%s count=%s", self._items_path, len(payload))
        return payload

    def _save_items(self, items: list[Item]) -> None:
        self._logger.info("save_items.start path=%s count=%s", self._items_path, len(items))
        self._items_path.parent.mkdir(parents=True, exist_ok=True)
        serialized = [item.to_dict() for item in items]
        self._items_path.write_text(json.dumps(serialized, indent=2), encoding="utf-8")
        self._logger.info("save_items.success path=%s count=%s", self._items_path, len(items))

    def _ensure_store(self) -> None:
        self._logger.info("ensure_store.start path=%s", self._items_path)
        self._items_path.parent.mkdir(parents=True, exist_ok=True)
        if not self._items_path.exists():
            self._items_path.write_text("[]", encoding="utf-8")
        self._logger.info("ensure_store.success path=%s exists=%s", self._items_path, self._items_path.exists())


def _is_valid(entry: dict[str, str]) -> bool:
    required = {"id", "created_at", "audio_path", "transcript_path"}
    return required.issubset(entry.keys())
