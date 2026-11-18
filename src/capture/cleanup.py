"""Delete local CSVs only after they have been uploaded and the trading date is closed.

The download command does not call this. A later upload step marks files uploaded,
and orchestration calls `delete_closed_files` on a schedule.
"""

from datetime import date, datetime
from pathlib import Path

from log import get_logger
from capture.manifest import Manifest
from shared.calendar import dispatch_checksum_settled

logger = get_logger(__name__)


def delete_closed_files(manifest: Manifest, landing: Path, now: datetime) -> list[str]:
    removed: list[str] = []
    for relative_path in _closed_relative_paths(manifest, now):
        record = manifest.files[relative_path]
        destination = landing / relative_path
        if destination.exists():
            destination.unlink()
        record.local_exists = False
        removed.append(relative_path)
        logger.info("deleted relative_path=%s trading_date=%s", relative_path, record.trading_date)
    return removed


def _closed_relative_paths(manifest: Manifest, now: datetime) -> list[str]:
    by_date: dict[str, list[str]] = {}
    for relative_path, record in manifest.files.items():
        if record.trading_date is None or not record.local_exists:
            continue
        by_date.setdefault(record.trading_date, []).append(relative_path)
    closed: list[str] = []
    for trading_date, paths in sorted(by_date.items()):
        reason = _keep_reason(manifest, trading_date, paths, now)
        if reason is None:
            closed.extend(sorted(paths))
            continue
        logger.info("kept trading_date=%s reason=%s", trading_date, reason)
    return closed


def _keep_reason(manifest: Manifest, trading_date: str, paths: list[str], now: datetime) -> str | None:
    """Why the local files stay. ``None`` means the trading date is closed."""
    final_record = None
    for relative_path in paths:
        record = manifest.files[relative_path]
        if relative_path.startswith("final_energy/") and record.status == "final":
            final_record = record
    if final_record is None or not final_record.uploaded:
        return "final_not_uploaded"
    # Dispatch files are phase 3. Until one is tracked for this date, nothing is deleted.
    dispatch_paths = [
        path
        for path, record in manifest.files.items()
        if record.trading_date == trading_date and "dispatch_energy/" in path
    ]
    if not dispatch_paths:
        return "dispatch_not_tracked"
    for path in dispatch_paths:
        record = manifest.files[path]
        if not record.uploaded:
            return "dispatch_not_uploaded"
        dispatch_observations = [
            (datetime.fromisoformat(item["at"]), item["sha256"]) for item in record.observations
        ]
        trading = date.fromisoformat(trading_date)
        if not dispatch_checksum_settled(trading, now, dispatch_observations):
            return "dispatch_checksum_open"
    return None
