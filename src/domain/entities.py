from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Item:
    id: str
    created_at: str
    audio_path: str
    transcript_path: str
    submitted_at: str = ""
    transcribe_started_at: str = ""
    transcribe_finished_at: str = ""
    audio_duration_seconds: float = 0.0

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
            "submitted_at": self.submitted_at,
            "transcribe_started_at": self.transcribe_started_at,
            "transcribe_finished_at": self.transcribe_finished_at,
            "audio_duration_seconds": self.audio_duration_seconds,
        }

    @staticmethod
    def from_dict(payload: dict[str, str]) -> "Item":
        return Item(
            id=payload["id"],
            created_at=payload["created_at"],
            audio_path=_normalize_path(payload["audio_path"]),
            transcript_path=_normalize_path(payload["transcript_path"]),
            submitted_at=str(payload.get("submitted_at", payload.get("created_at", ""))),
            transcribe_started_at=str(payload.get("transcribe_started_at", "")),
            transcribe_finished_at=str(payload.get("transcribe_finished_at", "")),
            audio_duration_seconds=_to_float(payload.get("audio_duration_seconds", 0.0)),
        )


def _normalize_path(path_value: str) -> str:
    return Path(path_value.replace("\\", "/")).as_posix()


def _to_float(value) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0
