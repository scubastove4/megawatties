from datetime import date, datetime
from pathlib import Path

from capture.download import download_prices
from capture.manifest import Manifest
from shared.calendar import AUCKLAND
from shared.checksums import sha256_hex


def _fetcher(files: dict[str, bytes]):
    def fetch(url: str) -> bytes | None:
        name = url.rsplit("/", 1)[-1]
        return files.get(name)

    return fetch


def test_download_skips_a_file_whose_checksum_is_unchanged(tmp_path: Path, caplog) -> None:
    caplog.set_level("INFO", logger="capture")
    landing = tmp_path / "landing"
    body = b"TradingDate,TradingPeriod\n2026-11-11,1\n"
    files = {
        "20261111_FinalEnergyPrices.csv": body,
        "20261111_FinalEnergyPrices_I.csv": b"interim\n",
    }
    manifest = Manifest()
    now = datetime(2026, 11, 12, 9, 30, tzinfo=AUCKLAND)
    first = download_prices(
        start=date(2026, 11, 11),
        end=date(2026, 11, 11),
        today=date(2026, 11, 18),
        now=now,
        landing=landing,
        manifest=manifest,
        fetcher=_fetcher(files),
    )
    assert first.downloaded == [
        "final_energy/20261111_FinalEnergyPrices.csv",
        "final_energy/20261111_FinalEnergyPrices_I.csv",
    ]
    saved = landing / "final_energy/20261111_FinalEnergyPrices.csv"
    assert sha256_hex(saved.read_bytes()) == sha256_hex(body)

    second = download_prices(
        start=date(2026, 11, 11),
        end=date(2026, 11, 11),
        today=date(2026, 11, 18),
        now=datetime(2026, 11, 12, 15, 30, tzinfo=AUCKLAND),
        landing=landing,
        manifest=manifest,
        fetcher=_fetcher(files),
    )
    assert second.downloaded == []
    assert second.replaced == []
    assert "final_energy/20261111_FinalEnergyPrices.csv" in second.unchanged
    assert "downloaded relative_path=final_energy/20261111_FinalEnergyPrices.csv" in caplog.text
    assert "unchanged relative_path=final_energy/20261111_FinalEnergyPrices.csv" in caplog.text
    assert "download finished downloaded=0 replaced=0 unchanged=2 missing=0" in caplog.text
    record = manifest.files["final_energy/20261111_FinalEnergyPrices.csv"]
    assert len(record.observations) == 2
    assert record.sha256 == sha256_hex(body)


def test_changed_checksum_replaces_the_local_file(tmp_path: Path) -> None:
    landing = tmp_path / "landing"
    manifest = Manifest()
    now = datetime(2026, 11, 12, 9, 30, tzinfo=AUCKLAND)
    download_prices(
        start=date(2026, 11, 12),
        end=date(2026, 11, 12),
        today=date(2026, 11, 18),
        now=now,
        landing=landing,
        manifest=manifest,
        fetcher=_fetcher({"20261112_FinalEnergyPrices_I.csv": b"first\n"}),
    )
    manifest.files["final_energy/20261112_FinalEnergyPrices_I.csv"].uploaded = True
    replaced = download_prices(
        start=date(2026, 11, 12),
        end=date(2026, 11, 12),
        today=date(2026, 11, 18),
        now=datetime(2026, 11, 12, 15, 30, tzinfo=AUCKLAND),
        landing=landing,
        manifest=manifest,
        fetcher=_fetcher({"20261112_FinalEnergyPrices_I.csv": b"second\n"}),
    )
    record = manifest.files["final_energy/20261112_FinalEnergyPrices_I.csv"]
    assert replaced.replaced == ["final_energy/20261112_FinalEnergyPrices_I.csv"]
    assert record.uploaded is False
    assert (landing / record.relative_path).read_bytes() == b"second\n"
