"""Keep a pytest run from writing the capture logs beside real poll runs."""

from pathlib import Path

import pytest

_REPO_CAPTURE_LOGS = Path(__file__).resolve().parents[1] / "logs" / "capture"


@pytest.fixture(autouse=True)
def _keep_pytest_out_of_capture_logs(monkeypatch: pytest.MonkeyPatch) -> None:
    import log.log as log_module

    original = log_module.configure_logging

    def configure_logging(path: Path | None = None, *, now=None):
        if path is None and now is not None:
            destination = log_module.run_log_path(now)
            resolved = destination if destination.is_absolute() else Path.cwd() / destination
            try:
                resolved.resolve().relative_to(_REPO_CAPTURE_LOGS.resolve())
            except ValueError:
                pass
            else:
                raise RuntimeError(
                    "pytest must not write logs/capture run logs; use a temporary directory"
                )
        return original(path, now=now)

    monkeypatch.setattr(log_module, "configure_logging", configure_logging)
