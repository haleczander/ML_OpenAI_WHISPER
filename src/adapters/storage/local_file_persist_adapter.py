from __future__ import annotations

from pathlib import Path

from src.adapters.logging_utils import get_adapter_logger


class LocalFilePersistAdapter:
    def __init__(self, base_dir: Path) -> None:
        self._logger = get_adapter_logger("local_file_persist_adapter")
        self._base_dir = base_dir
        self._data_dir = self._base_dir / "data"
        self._audio_dir = self._data_dir / "audio"
        self._transcript_dir = self._data_dir / "transcripts"
        self._logger.info("init.success base_dir=%s", base_dir)

    def ensure_dirs(self) -> None:
        self._logger.info("ensure_dirs.start")
        try:
            self._data_dir.mkdir(parents=True, exist_ok=True)
            self._audio_dir.mkdir(parents=True, exist_ok=True)
            self._transcript_dir.mkdir(parents=True, exist_ok=True)
            self._logger.info("ensure_dirs.success")
        except Exception as exc:
            self._logger.exception("ensure_dirs.failure error=%s", exc)
            raise

    def save_bytes(self, payload: bytes, relative_path: str) -> None:
        self._logger.info("save_bytes.start relative_path=%s bytes=%s", relative_path, len(payload))
        try:
            target = self.resolve(relative_path)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(payload)
            self._logger.info("save_bytes.success relative_path=%s", relative_path)
        except Exception as exc:
            self._logger.exception("save_bytes.failure relative_path=%s error=%s", relative_path, exc)
            raise

    def write_text(self, relative_path: str, content: str) -> None:
        self._logger.info("write_text.start relative_path=%s chars=%s", relative_path, len(content))
        try:
            target = self.resolve(relative_path)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
            self._logger.info("write_text.success relative_path=%s", relative_path)
        except Exception as exc:
            self._logger.exception("write_text.failure relative_path=%s error=%s", relative_path, exc)
            raise

    def read_text(self, relative_path: str) -> str:
        self._logger.info("read_text.start relative_path=%s", relative_path)
        try:
            target = self.resolve(relative_path)
            if not target.exists():
                self._logger.info("read_text.success relative_path=%s chars=0 missing=true", relative_path)
                return ""
            content = target.read_text(encoding="utf-8")
            self._logger.info("read_text.success relative_path=%s chars=%s", relative_path, len(content))
            return content
        except Exception as exc:
            self._logger.exception("read_text.failure relative_path=%s error=%s", relative_path, exc)
            raise

    def delete_file(self, relative_path: str) -> None:
        self._logger.info("delete_file.start relative_path=%s", relative_path)
        try:
            target = self.resolve(relative_path)
            existed_before = target.exists()
            if target.exists():
                target.unlink()
            self._logger.info("delete_file.success relative_path=%s existed=%s", relative_path, existed_before)
        except Exception as exc:
            self._logger.exception("delete_file.failure relative_path=%s error=%s", relative_path, exc)
            raise

    def resolve(self, relative_path: str) -> Path:
        normalized = relative_path.replace("\\", "/")
        resolved = self._base_dir / Path(normalized)
        self._logger.info("resolve.success relative_path=%s resolved=%s", relative_path, resolved)
        return resolved
