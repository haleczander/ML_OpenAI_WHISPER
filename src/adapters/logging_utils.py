from __future__ import annotations

import logging
import os
from pathlib import Path


def get_adapter_logger(adapter_name: str) -> logging.Logger:
    logger = logging.getLogger(f"adapter.{adapter_name}")
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)
    logger.propagate = False

    formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
    try:
        log_dir = Path(os.getenv("APP_ADAPTER_LOG_DIR", "data/logs/adapters"))
        log_dir.mkdir(parents=True, exist_ok=True)
        log_path = log_dir / f"{adapter_name}.log"
        file_handler = logging.FileHandler(log_path, encoding="utf-8")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    except OSError:
        # Never fail app startup because log file cannot be created.
        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(formatter)
        logger.addHandler(stream_handler)
    return logger
