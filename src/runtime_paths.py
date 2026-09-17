from __future__ import annotations

import os
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping


APP_DIRECTORY_NAME = "DicteeCourriels"


@dataclass(frozen=True)
class RuntimePaths:
    """Separate replaceable application resources from persistent state."""

    resource_root: Path
    state_root: Path
    model_dir: Path | None

    @classmethod
    def discover(
        cls,
        resource_root: Path,
        *,
        environ: Mapping[str, str] | None = None,
        frozen: bool | None = None,
    ) -> "RuntimePaths":
        env = os.environ if environ is None else environ
        is_frozen = bool(getattr(sys, "frozen", False)) if frozen is None else frozen
        resolved_resource_root = resource_root.resolve()

        configured_state_root = env.get("APP_STATE_DIR", "").strip()
        if configured_state_root:
            state_root = Path(configured_state_root).expanduser().resolve()
        elif is_frozen:
            local_app_data = env.get("LOCALAPPDATA", "").strip()
            if not local_app_data:
                raise RuntimeError("LOCALAPPDATA is required for the packaged application")
            state_root = (Path(local_app_data) / APP_DIRECTORY_NAME).resolve()
        else:
            # Preserve the repository and current portable archive layout in development.
            state_root = resolved_resource_root

        configured_model_dir = env.get("APP_MODEL_DIR", "").strip()
        if configured_model_dir:
            model_dir: Path | None = Path(configured_model_dir).expanduser().resolve()
        elif is_frozen or configured_state_root:
            model_dir = state_root / "models"
        else:
            # Preserve Whisper's standard user cache for existing development installs.
            model_dir = None

        return cls(
            resource_root=resolved_resource_root,
            state_root=state_root,
            model_dir=model_dir,
        )

    @property
    def data_dir(self) -> Path:
        return self.state_root / "data"

    @property
    def cert_dir(self) -> Path:
        return self.state_root / "certs"

    @property
    def log_dir(self) -> Path:
        return self.data_dir / "logs"

    @property
    def adapter_log_dir(self) -> Path:
        return self.log_dir / "adapters"

    def migrate_legacy_state(self) -> None:
        """Copy legacy in-install state once, without overwriting user files."""
        if self.resource_root == self.state_root:
            return
        self._copy_missing_tree(self.resource_root / "data", self.data_dir)
        self._copy_missing_tree(self.resource_root / "certs", self.cert_dir)

    @staticmethod
    def _copy_missing_tree(source: Path, destination: Path) -> None:
        if not source.is_dir():
            return
        for source_path in source.rglob("*"):
            relative_path = source_path.relative_to(source)
            destination_path = destination / relative_path
            if source_path.is_dir():
                destination_path.mkdir(parents=True, exist_ok=True)
            elif not destination_path.exists():
                destination_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source_path, destination_path)

    def ensure_directories(self) -> None:
        directories = [
            self.data_dir,
            self.data_dir / "audio",
            self.data_dir / "transcripts",
            self.log_dir,
            self.adapter_log_dir,
            self.cert_dir,
        ]
        if self.model_dir is not None:
            directories.append(self.model_dir)
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
