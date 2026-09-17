from __future__ import annotations

import json
import os
import socket
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping


@dataclass(frozen=True)
class AppConfig:
    host: str = "0.0.0.0"
    port: int = 8000
    https: bool = False

    @classmethod
    def load(
        cls,
        path: Path,
        *,
        environ: Mapping[str, str] | None = None,
    ) -> "AppConfig":
        env = os.environ if environ is None else environ
        if path.exists():
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                raise ValueError(f"Invalid configuration file {path}: {exc}") from exc
            if not isinstance(payload, dict):
                raise ValueError(f"Invalid configuration file {path}: expected a JSON object")
        else:
            payload = {}

        host = env.get("APP_HOST", payload.get("host", cls.host))
        port = env.get("APP_PORT", payload.get("port", cls.port))
        https = env.get("APP_SSL", payload.get("https", cls.https))
        config = cls(
            host=cls._validate_host(host),
            port=cls._validate_port(port),
            https=cls._validate_bool(https),
        )

        if not path.exists():
            config.write(path)
        return config

    def write(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path = path.with_suffix(path.suffix + ".tmp")
        temporary_path.write_text(
            json.dumps(
                {"host": self.host, "port": self.port, "https": self.https},
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        temporary_path.replace(path)

    def browser_urls(self) -> list[str]:
        scheme = "https" if self.https else "http"
        if self.host not in {"0.0.0.0", "::"}:
            display_host = "localhost" if self.host in {"127.0.0.1", "::1"} else self.host
            return [f"{scheme}://{display_host}:{self.port}"]

        addresses = discover_lan_addresses()
        urls = [f"{scheme}://localhost:{self.port}"]
        urls.extend(f"{scheme}://{address}:{self.port}" for address in addresses)
        return urls

    @staticmethod
    def _validate_host(value: object) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError("host must be a non-empty string")
        return value.strip()

    @staticmethod
    def _validate_port(value: object) -> int:
        if isinstance(value, bool):
            raise ValueError("port must be an integer between 1 and 65535")
        try:
            port = int(value)
        except (TypeError, ValueError) as exc:
            raise ValueError("port must be an integer between 1 and 65535") from exc
        if not 1 <= port <= 65535:
            raise ValueError("port must be an integer between 1 and 65535")
        return port

    @staticmethod
    def _validate_bool(value: object) -> bool:
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"1", "true", "yes", "on"}:
                return True
            if normalized in {"0", "false", "no", "off"}:
                return False
        raise ValueError("https must be a boolean")


def discover_lan_addresses() -> list[str]:
    try:
        records = socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET)
    except OSError:
        return []
    return sorted(
        {
            record[4][0]
            for record in records
            if record[4][0] and not record[4][0].startswith("127.")
        }
    )
