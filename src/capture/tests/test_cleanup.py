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


def test_local_files_stay_until_dispatch_has_settled(tmp_path: Path, caplog) -> None:
    caplog.set_level("INFO", logger="capture")
    landing = tmp_path / "landing"
    trading = "2026-11-10"
    final_path = f"final_energy/{trading.replace('-', '')}_FinalEnergyPrices.csv"
    interim_path = f"final_energy/{trading.replace('-', '')}_FinalEnergyPrices_I.csv"
    dispatch_path = f"dispatch_energy/{trading.replace('-', '')}_DispatchEnergyPrices.csv"
    for relative in (final_path, interim_path, dispatch_path):
        destination = landing / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(b"csv")
    manifest = Manifest(
        files={
            final_path: _record(final_path, trading, "final"),
            interim_path: _record(interim_path, trading, "interim"),
            dispatch_path: _record(dispatch_path, trading, "final", digest="dispatch"),
        }
    )
    inside = datetime(2026, 11, 12, 18, 30, tzinfo=AUCKLAND)
    assert delete_closed_files(manifest, landing, inside) == []
    assert (landing / final_path).exists()

    manifest.files[dispatch_path].observations.append(
        {"at": "2026-11-13T15:30:00+13:00", "sha256": "dispatch"}
    )
    settled = datetime(2026, 11, 13, 15, 30, tzinfo=AUCKLAND)
    removed = delete_closed_files(manifest, landing, settled)
    assert f"deleted relative_path={final_path} trading_date={trading}" in caplog.text
    assert final_path in removed
    assert interim_path in removed
    assert dispatch_path in removed
    assert not (landing / final_path).exists()


def test_files_stay_when_dispatch_is_not_tracked_yet(tmp_path: Path, caplog) -> None:
    landing = tmp_path / "landing"
    final_path = "final_energy/20261110_FinalEnergyPrices.csv"
    destination = landing / final_path
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(b"csv")
    caplog.set_level("INFO", logger="capture")
    manifest = Manifest(files={final_path: _record(final_path, "2026-11-10", "final")})
    now = datetime(2026, 11, 20, 9, 30, tzinfo=AUCKLAND)
    assert delete_closed_files(manifest, landing, now) == []
    assert destination.exists()
    assert "kept trading_date=2026-11-10 reason=dispatch_not_tracked" in caplog.text


def test_files_are_kept_when_the_final_has_not_been_uploaded(tmp_path: Path) -> None:
    landing = tmp_path / "landing"
    trading = "2026-11-10"
    final_path = "final_energy/20261110_FinalEnergyPrices.csv"
    destination = landing / final_path
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(b"csv")
    record = _record(final_path, trading, "final")
    record.uploaded = False
    manifest = Manifest(files={final_path: record})
    now = datetime(2026, 11, 20, 9, 30, tzinfo=AUCKLAND)
    assert delete_closed_files(manifest, landing, now) == []
    assert destination.exists()
