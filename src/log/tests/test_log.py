from pathlib import Path
import logging

from log import configure_logging
from log.log import DEFAULT_CONFIG


def test_packaged_yaml_sets_the_root_level() -> None:
    configure_logging()
    assert DEFAULT_CONFIG.is_file()
    assert logging.getLogger().level == logging.INFO


def test_configure_logging_reads_an_override_file(tmp_path: Path) -> None:
    path = tmp_path / "logging.yaml"
    path.write_text(
        "\n".join(
            [
                "version: 1",
                "disable_existing_loggers: false",
                "root:",
                "  level: ERROR",
                "  handlers: []",
            ]
        ),
        encoding="utf-8",
    )
    configure_logging(path)
    assert logging.getLogger().level == logging.ERROR
    configure_logging()
