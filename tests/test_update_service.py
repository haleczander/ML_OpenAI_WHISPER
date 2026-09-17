from __future__ import annotations

import unittest

from src.update_service import UpdateService


class FakeAsset:
    Version = "1.1.0"


class FakeUpdateInfo:
    TargetFullRelease = FakeAsset()


class FakeManager:
    def __init__(self, update_available: bool = True) -> None:
        self.update_available = update_available
        self.downloaded = False
        self.applied = False

    def get_current_version(self) -> str:
        return "1.0.0"

    def check_for_updates(self):
        return FakeUpdateInfo() if self.update_available else None

    def download_updates(self, update_info, progress_callback) -> None:
        progress_callback(42)
        self.downloaded = True

    def apply_updates_and_restart(self, update_info) -> None:
        self.applied = True


class UpdateServiceTests(unittest.TestCase):
    def test_disabled_service_does_not_start_workers(self) -> None:
        service = UpdateService(enabled=False, manager_factory=lambda: FakeManager())
        self.assertIsNone(service.check_async())
        self.assertEqual(service.snapshot()["status"], "disabled")

    def test_update_can_be_checked_downloaded_and_applied(self) -> None:
        manager = FakeManager()
        service = UpdateService(enabled=True, manager_factory=lambda: manager)

        check_worker = service.check_async()
        self.assertIsNotNone(check_worker)
        check_worker.join(timeout=2)
        self.assertEqual(service.snapshot()["status"], "available")
        self.assertEqual(service.snapshot()["current_version"], "1.0.0")
        self.assertEqual(service.snapshot()["available_version"], "1.1.0")

        download_worker = service.download_async()
        self.assertIsNotNone(download_worker)
        download_worker.join(timeout=2)
        self.assertTrue(manager.downloaded)
        self.assertEqual(service.snapshot()["status"], "downloaded")
        self.assertEqual(service.snapshot()["progress"], 100)

        apply_worker = service.apply_async()
        self.assertIsNotNone(apply_worker)
        apply_worker.join(timeout=2)
        self.assertTrue(manager.applied)

    def test_no_available_update_reports_up_to_date(self) -> None:
        service = UpdateService(enabled=True, manager_factory=lambda: FakeManager(False))
        worker = service.check_async()
        worker.join(timeout=2)
        self.assertEqual(service.snapshot()["status"], "up_to_date")

    def test_manager_failure_is_reported(self) -> None:
        def fail():
            raise RuntimeError("offline")

        service = UpdateService(enabled=True, manager_factory=fail)
        worker = service.check_async()
        worker.join(timeout=2)
        state = service.snapshot()
        self.assertEqual(state["status"], "error")
        self.assertIn("offline", state["error"])


if __name__ == "__main__":
    unittest.main()
