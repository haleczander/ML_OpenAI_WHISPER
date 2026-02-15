from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import uuid

from src.application.ports import FilePersistPort, ItemRepositoryPort, TranscribePort
from src.domain.entities import Item


class TranscribeUseCase:
    def __init__(
        self,
        repository: ItemRepositoryPort,
        file_persist: FilePersistPort,
        transcriber: TranscribePort,
    ) -> None:
        self._repository = repository
        self._file_persist = file_persist
        self._transcriber = transcriber

    def from_upload(self, uploaded_file) -> tuple[Item, str]:
        filename = getattr(uploaded_file, "filename", "") or "audio.webm"
        suffix = Path(filename).suffix.lower() or ".webm"
        return self._transcribe_and_store(
            save_source=lambda relative_path: self._file_persist.save_uploaded_file(uploaded_file, relative_path),
            input_suffix=suffix,
        )

    def from_bytes(self, payload: bytes, extension: str = ".webm") -> tuple[Item, str]:
        suffix = extension if extension.startswith(".") else f".{extension}"
        return self._transcribe_and_store(
            save_source=lambda relative_path: self._file_persist.save_bytes(payload, relative_path),
            input_suffix=suffix,
        )

    def _transcribe_and_store(self, save_source, input_suffix: str) -> tuple[Item, str]:
        self._file_persist.ensure_dirs()

        item_id = uuid.uuid4().hex
        raw_path = f"data/audio/{item_id}{input_suffix}"
        save_source(raw_path)

        audio_path = self._file_persist.convert_to_mp3_if_possible(raw_path)
        transcript = self._transcriber.transcribe(self._file_persist.resolve(audio_path))

        transcript_path = f"data/transcripts/{item_id}.txt"
        self._file_persist.write_text(transcript_path, transcript + "\n")

        item = Item(
            id=item_id,
            created_at=datetime.now(timezone.utc).isoformat(),
            audio_path=audio_path,
            transcript_path=transcript_path,
        )
        self._repository.add(item)
        return item, transcript
