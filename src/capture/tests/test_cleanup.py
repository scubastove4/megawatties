from datetime import datetime
from pathlib import Path

from capture.cleanup import delete_closed_files
from capture.manifest import FileRecord, Manifest
from shared.calendar import AUCKLAND


def _record(relative_path: str, trading_date: str, status: str, digest: str = "abc") -> FileRecord:
    return FileRecord(
        relative_path=relative_path,
        sha256=digest,
        size=3,
        url="https://example.test/" + Path(relative_path).name,
        status=status,
        trading_date=trading_date,
        uploaded=True,
        local_exists=True,
        observations=[{"at": "2026-11-13T09:30:00+13:00", "sha256": digest}],
    )


def _write_day(landing: Path, trading: str, files: dict[str, FileRecord]) -> Path:
    manifest_path = landing / "daily" / trading / "manifest.json"
    for relative, record in files.items():
        destination = landing / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(b"csv")
        record.local_exists = True
    Manifest(files=files).save(manifest_path)
    return manifest_path


def test_local_files_stay_until_dispatch_has_settled(tmp_path: Path, caplog) -> None:
    caplog.set_level("INFO", logger="capture")
    landing = tmp_path / "landing"
    trading = "2026-11-10"
    final_path = f"daily/{trading}/{trading.replace('-', '')}_FinalEnergyPrices.csv"
    interim_path = f"daily/{trading}/{trading.replace('-', '')}_FinalEnergyPrices_I.csv"
    dispatch_path = f"daily/{trading}/{trading.replace('-', '')}_DispatchEnergyPrices.csv"
    manifest_path = _write_day(
        landing,
        trading,
        {
            final_path: _record(final_path, trading, "final"),
            interim_path: _record(interim_path, trading, "interim"),
            dispatch_path: _record(dispatch_path, trading, "final", digest="dispatch"),
        },
    )
    inside = datetime(2026, 11, 12, 18, 30, tzinfo=AUCKLAND)
    assert delete_closed_files(landing, inside) == []
    assert (landing / final_path).exists()

    manifest = Manifest.load(manifest_path)
    manifest.files[dispatch_path].observations.append(
        {"at": "2026-11-13T15:30:00+13:00", "sha256": "dispatch"}
    )
    manifest.save(manifest_path)
    settled = datetime(2026, 11, 13, 15, 30, tzinfo=AUCKLAND)
    removed = delete_closed_files(landing, settled)
    assert f"deleted relative_path={final_path} trading_date={trading}" in caplog.text
    assert final_path in removed
    assert interim_path in removed
    assert dispatch_path in removed
    assert not (landing / final_path).exists()
    assert manifest_path.is_file()
    saved = Manifest.load(manifest_path)
    assert saved.files[final_path].local_exists is False
    assert saved.files[dispatch_path].sha256 == "dispatch"


def test_files_stay_when_dispatch_is_not_tracked_yet(tmp_path: Path, caplog) -> None:
    landing = tmp_path / "landing"
    trading = "2026-11-10"
    final_path = f"daily/{trading}/20261110_FinalEnergyPrices.csv"
    manifest_path = _write_day(landing, trading, {final_path: _record(final_path, trading, "final")})
    caplog.set_level("INFO", logger="capture")
    now = datetime(2026, 11, 20, 9, 30, tzinfo=AUCKLAND)
    assert delete_closed_files(landing, now) == []
    assert (landing / final_path).exists()
    assert manifest_path.is_file()
    assert "kept trading_date=2026-11-10 reason=dispatch_not_tracked" in caplog.text


def test_files_are_kept_when_the_final_has_not_been_uploaded(tmp_path: Path) -> None:
    landing = tmp_path / "landing"
    trading = "2026-11-10"
    final_path = f"daily/{trading}/20261110_FinalEnergyPrices.csv"
    record = _record(final_path, trading, "final")
    record.uploaded = False
    _write_day(landing, trading, {final_path: record})
    now = datetime(2026, 11, 20, 9, 30, tzinfo=AUCKLAND)
    assert delete_closed_files(landing, now) == []
    assert (landing / final_path).exists()
