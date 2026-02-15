from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Item:
    id: str
    created_at: str
    audio_path: str
    transcript_path: str

    @property
    def audio_url(self) -> str:
        return f"/audio/{self.id}"

    def to_dict(self) -> dict[str, str]:
        return {
            "id": self.id,
            "created_at": self.created_at,
            "audio_path": self.audio_path,
            "audio_url": self.audio_url,
            "transcript_path": self.transcript_path,
        }

    @staticmethod
    def from_dict(payload: dict[str, str]) -> "Item":
        return Item(
            id=payload["id"],
            created_at=payload["created_at"],
            audio_path=_normalize_path(payload["audio_path"]),
            transcript_path=_normalize_path(payload["transcript_path"]),
        )


def _normalize_path(path_value: str) -> str:
    return Path(path_value.replace("\\", "/")).as_posix()
