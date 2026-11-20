"""Load logging.yaml and hand loggers to capture, orchestration, and ingestion."""

from logging.config import dictConfig
from pathlib import Path
import logging

import yaml

DEFAULT_CONFIG = Path(__file__).with_name("logging.yaml")


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)


def configure_logging(path: Path | None = None) -> None:
    config_path = DEFAULT_CONFIG if path is None else path
    payload = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"logging config must be a mapping: {config_path}")
    for handler in payload.get("handlers", {}).values():
        filename = handler.get("filename")
        if isinstance(filename, str) and filename:
            Path(filename).parent.mkdir(parents=True, exist_ok=True)
    dictConfig(payload)
