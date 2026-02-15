from __future__ import annotations

import shutil
import subprocess
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

    def save_uploaded_file(self, file_obj, relative_path: str) -> None:
        target = self.resolve(relative_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        file_obj.save(target)

    def save_bytes(self, payload: bytes, relative_path: str) -> None:
        target = self.resolve(relative_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(payload)

    def convert_to_mp3_if_possible(self, src_relative_path: str) -> str:
        if not self._ffmpeg_exists():
            return src_relative_path

        src_path = self.resolve(src_relative_path)
        mp3_relative = f"data/audio/{src_path.stem}.mp3"
        mp3_path = self.resolve(mp3_relative)

        if self._convert_to_mp3(src_path, mp3_path):
            return mp3_relative
        return src_relative_path

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

    @staticmethod
    def _ffmpeg_exists() -> bool:
        return shutil.which("ffmpeg") is not None

    @staticmethod
    def _convert_to_mp3(src_path: Path, dst_path: Path) -> bool:
        try:
            subprocess.run(
                ["ffmpeg", "-y", "-i", str(src_path), str(dst_path)],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            return True
        except subprocess.CalledProcessError:
            return False
