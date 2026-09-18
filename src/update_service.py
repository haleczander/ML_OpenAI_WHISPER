from __future__ import annotations

import threading
from collections.abc import Callable
from typing import Any


DEFAULT_UPDATE_REPOSITORY = "https://github.com/haleczander/ML_OpenAI_WHISPER"


class UpdateService:
    def __init__(
        self,
        *,
        enabled: bool,
        repository_url: str = DEFAULT_UPDATE_REPOSITORY,
        manager_factory: Callable[[], Any] | None = None,
    ) -> None:
        self._enabled = enabled
        self._repository_url = repository_url
        self._manager_factory = manager_factory or self._create_manager
        self._manager: Any | None = None
        self._update_info: Any | None = None
        self._lock = threading.Lock()
        self._state: dict[str, Any] = {
            "enabled": enabled,
            "status": "idle" if enabled else "disabled",
            "current_version": None,
            "available_version": None,
            "progress": 0,
            "error": None,
        }

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return dict(self._state)

    def check_async(self) -> threading.Thread | None:
        with self._lock:
            if not self._enabled or self._state["status"] in {"checking", "downloading", "applying"}:
                return None
            self._state.update(status="checking", error=None, progress=0)
        return self._start_worker(self._check)

    def download_async(self) -> threading.Thread | None:
        with self._lock:
            if self._state["status"] != "available" or self._update_info is None:
                return None
            self._state.update(status="downloading", error=None, progress=0)
        return self._start_worker(self._download)

    def apply_async(self) -> threading.Thread | None:
        with self._lock:
            if self._state["status"] != "downloaded" or self._update_info is None:
                return None
            self._state.update(status="applying", error=None)
        return self._start_worker(self._apply)

    def _create_manager(self):
        import velopack

        if self._repository_url.lower().startswith(("https://github.com/", "http://github.com/")):
            source = velopack.GithubSource(self._repository_url)
        else:
            # Velopack also accepts a local directory or a static HTTP feed.
            source = self._repository_url
        return velopack.UpdateManager(source)

    def _get_manager(self):
        if self._manager is None:
            self._manager = self._manager_factory()
        return self._manager

    def _check(self) -> None:
        try:
            manager = self._get_manager()
            current_version = manager.get_current_version()
            update_info = manager.check_for_updates()
            with self._lock:
                self._state["current_version"] = current_version
                if update_info is None:
                    self._update_info = None
                    self._state.update(status="up_to_date", available_version=None)
                else:
                    self._update_info = update_info
                    self._state.update(
                        status="available",
                        available_version=str(update_info.TargetFullRelease.Version),
                    )
        except Exception as exc:
            self._set_error(exc)

    def _download(self) -> None:
        try:
            manager = self._get_manager()
            manager.download_updates(self._update_info, self._set_progress)
            with self._lock:
                self._state.update(status="downloaded", progress=100)
        except Exception as exc:
            self._set_error(exc)

    def _apply(self) -> None:
        try:
            self._get_manager().apply_updates_and_restart(self._update_info)
        except Exception as exc:
            self._set_error(exc)

    def _set_progress(self, progress: int) -> None:
        with self._lock:
            self._state["progress"] = max(0, min(100, int(progress)))

    def _set_error(self, exc: Exception) -> None:
        with self._lock:
            self._state.update(status="error", error=f"{type(exc).__name__}: {exc}")

    @staticmethod
    def _start_worker(target: Callable[[], None]) -> threading.Thread:
        worker = threading.Thread(target=target, daemon=True)
        worker.start()
        return worker
