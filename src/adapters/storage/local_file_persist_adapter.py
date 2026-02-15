from __future__ import annotations

from pathlib import Path


class LocalFilePersistAdapter:
    def __init__(self, base_dir: Path) -> None:
        self._base_dir = base_dir
        self._data_dir = self._base_dir / "data"
        self._audio_dir = self._data_dir / "audio"
        self._transcript_dir = self._data_dir / "transcripts"

    def ensure_dirs(self) -> None:
        self._data_dir.mkdir(parents=True, exist_ok=True)
        self._audio_dir.mkdir(parents=True, exist_ok=True)
        self._transcript_dir.mkdir(parents=True, exist_ok=True)

    def save_bytes(self, payload: bytes, relative_path: str) -> None:
        target = self.resolve(relative_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(payload)

    def write_text(self, relative_path: str, content: str) -> None:
        target = self.resolve(relative_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")

    def read_text(self, relative_path: str) -> str:
        target = self.resolve(relative_path)
        if not target.exists():
            return ""
        return target.read_text(encoding="utf-8")

    def delete_file(self, relative_path: str) -> None:
        target = self.resolve(relative_path)
        if target.exists():
            target.unlink()

    def resolve(self, relative_path: str) -> Path:
        normalized = relative_path.replace("\\", "/")
        return self._base_dir / Path(normalized)
