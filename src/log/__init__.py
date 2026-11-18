"""Shared logging setup. Import this package from capture, orchestration, and ingestion."""

from log.log import configure_logging, get_logger

__all__ = ["configure_logging", "get_logger"]
