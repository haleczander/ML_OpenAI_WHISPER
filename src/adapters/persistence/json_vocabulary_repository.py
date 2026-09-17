from __future__ import annotations

import json
from pathlib import Path
from threading import Lock

from src.adapters.logging_utils import get_adapter_logger


class JsonVocabularyRepository:
    """Server-local vocabulary used as Whisper's decoding prompt."""

    MAX_TERMS = 100
    MAX_TERM_LENGTH = 100
    MAX_PROMPT_LENGTH = 2_000

    def __init__(self, vocabulary_path: Path) -> None:
        self._logger = get_adapter_logger("json_vocabulary_repository")
        self._path = vocabulary_path
        self._lock = Lock()
        self._ensure_store()

    def list_terms(self) -> list[str]:
        with self._lock:
            return self._load_terms()

    def replace_terms(self, terms: list[str]) -> list[str]:
        normalized = self._normalize(terms)
        with self._lock:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            temporary_path = self._path.with_suffix(".tmp")
            temporary_path.write_text(
                json.dumps({"terms": normalized}, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            temporary_path.replace(self._path)
        self._logger.info("replace_terms.success count=%s", len(normalized))
        return normalized

    def build_prompt(self) -> str | None:
        terms = self.list_terms()
        if not terms:
            return None
        prompt = "Termes à privilégier : " + ", ".join(terms) + "."
        return prompt[:self.MAX_PROMPT_LENGTH]

    def _ensure_store(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        if not self._path.exists():
            self._path.write_text('{"terms": []}\n', encoding="utf-8")

    def _load_terms(self) -> list[str]:
        try:
            payload = json.loads(self._path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            self._logger.warning("load_terms.failure path=%s error=%s", self._path, exc)
            return []
        if not isinstance(payload, dict) or not isinstance(payload.get("terms"), list):
            return []
        return self._normalize(payload["terms"])

    def _normalize(self, terms: list[str]) -> list[str]:
        result: list[str] = []
        seen: set[str] = set()
        for term in terms:
            if not isinstance(term, str):
                continue
            cleaned = " ".join(term.split())[:self.MAX_TERM_LENGTH]
            key = cleaned.casefold()
            if cleaned and key not in seen:
                result.append(cleaned)
                seen.add(key)
            if len(result) >= self.MAX_TERMS:
                break
        return result
