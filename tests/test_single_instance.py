from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from src.single_instance import SingleInstanceLock


class SingleInstanceLockTests(unittest.TestCase):
    def test_only_one_lock_can_be_held_and_release_allows_reacquire(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "state" / "server.lock"
            first = SingleInstanceLock(path)
            second = SingleInstanceLock(path)

            self.assertTrue(first.acquire())
            self.assertFalse(second.acquire())

            first.release()
            self.assertTrue(second.acquire())
            second.release()


if __name__ == "__main__":
    unittest.main()
