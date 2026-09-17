from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from src.adapters.persistence.json_item_repository import JsonItemRepository
from src.adapters.persistence.json_vocabulary_repository import JsonVocabularyRepository
from src.adapters.storage.local_file_persist_adapter import LocalFilePersistAdapter
from src.domain.entities import Item
from src.runtime_paths import RuntimePaths


class RuntimePathsTests(unittest.TestCase):
    def test_development_defaults_remain_in_project(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            app_dir = Path(temp) / "checkout"
            app_dir.mkdir()

            paths = RuntimePaths.discover(app_dir, environ={}, frozen=False)

            self.assertEqual(paths.state_root, app_dir)
            self.assertEqual(paths.data_dir, app_dir / "data")
            self.assertEqual(paths.cert_dir, app_dir / "certs")
            self.assertIsNone(paths.model_dir)

    def test_packaged_defaults_use_local_app_data(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            app_dir = root / "installed-app"
            app_dir.mkdir()

            paths = RuntimePaths.discover(
                app_dir,
                environ={"LOCALAPPDATA": str(root / "user-state")},
                frozen=True,
            )

            state_root = root / "user-state" / "DicteeCourriels"
            self.assertEqual(paths.state_root, state_root)
            self.assertEqual(paths.data_dir, state_root / "data")
            self.assertEqual(paths.cert_dir, state_root / "certs")
            self.assertEqual(paths.model_dir, state_root / "models")

    def test_external_state_survives_application_replacement(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            state_root = root / "persistent"
            environment = {"APP_STATE_DIR": str(state_root)}
            first_paths = RuntimePaths.discover(root / "app-v1", environ=environment, frozen=False)
            second_paths = RuntimePaths.discover(root / "app-v2", environ=environment, frozen=False)
            first_paths.ensure_directories()

            first_store = LocalFilePersistAdapter(first_paths.state_root)
            first_store.save_bytes(b"audio", "data/audio/recording.webm")
            first_store.write_text("data/transcripts/recording.txt", "transcript")
            repository = JsonItemRepository(first_paths.data_dir / "items.json")
            repository.add(
                Item(
                    id="recording",
                    created_at="2026-01-01T00:00:00+00:00",
                    audio_path="data/audio/recording.webm",
                    transcript_path="data/transcripts/recording.txt",
                )
            )
            vocabulary = JsonVocabularyRepository(first_paths.data_dir / "vocabulary.json")
            vocabulary.replace_terms(["Whisper", "courriel"])

            second_paths.ensure_directories()
            second_store = LocalFilePersistAdapter(second_paths.state_root)
            second_repository = JsonItemRepository(second_paths.data_dir / "items.json")
            second_vocabulary = JsonVocabularyRepository(second_paths.data_dir / "vocabulary.json")

            self.assertEqual(second_store.resolve("data/audio/recording.webm").read_bytes(), b"audio")
            self.assertEqual(second_store.read_text("data/transcripts/recording.txt"), "transcript")
            self.assertEqual([item.id for item in second_repository.list_items()], ["recording"])
            self.assertEqual(second_vocabulary.list_terms(), ["Whisper", "courriel"])
            self.assertFalse((root / "app-v2" / "data").exists())

    def test_legacy_migration_is_idempotent_and_never_overwrites(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            resource_root = root / "installed-app"
            state_root = root / "persistent"
            (resource_root / "data" / "audio").mkdir(parents=True)
            (resource_root / "certs").mkdir()
            (resource_root / "data" / "items.json").write_text("legacy", encoding="utf-8")
            (resource_root / "data" / "audio" / "old.webm").write_bytes(b"legacy-audio")
            (resource_root / "certs" / "local.pem").write_text("legacy-cert", encoding="utf-8")
            (state_root / "data").mkdir(parents=True)
            (state_root / "data" / "items.json").write_text("current", encoding="utf-8")
            paths = RuntimePaths.discover(
                resource_root,
                environ={"APP_STATE_DIR": str(state_root)},
                frozen=True,
            )

            paths.migrate_legacy_state()
            paths.migrate_legacy_state()

            self.assertEqual((state_root / "data" / "items.json").read_text(encoding="utf-8"), "current")
            self.assertEqual((state_root / "data" / "audio" / "old.webm").read_bytes(), b"legacy-audio")
            self.assertEqual((state_root / "certs" / "local.pem").read_text(encoding="utf-8"), "legacy-cert")
            self.assertEqual((resource_root / "data" / "items.json").read_text(encoding="utf-8"), "legacy")

    def test_ensure_directories_does_not_replace_existing_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            state_root = root / "state"
            (state_root / "data").mkdir(parents=True)
            items_path = state_root / "data" / "items.json"
            items_path.write_text(json.dumps([{"sentinel": True}]), encoding="utf-8")
            paths = RuntimePaths.discover(
                root / "app",
                environ={"APP_STATE_DIR": str(state_root)},
                frozen=False,
            )

            paths.ensure_directories()
            paths.ensure_directories()

            self.assertEqual(json.loads(items_path.read_text(encoding="utf-8")), [{"sentinel": True}])

    def test_file_store_rejects_paths_outside_state_directory(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            store = LocalFilePersistAdapter(Path(temp) / "state")
            with self.assertRaises(ValueError):
                store.resolve("data/../../outside.txt")
            with self.assertRaises(ValueError):
                store.resolve(str((Path(temp) / "absolute.txt").resolve()))


if __name__ == "__main__":
    unittest.main()
