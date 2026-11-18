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
    final_path = "daily/2026-11-11/20261111_FinalEnergyPrices.csv"
    interim_path = "daily/2026-11-11/20261111_FinalEnergyPrices_I.csv"
    files = {
        "20261111_FinalEnergyPrices.csv": body,
        "20261111_FinalEnergyPrices_I.csv": b"interim\n",
    }
    now = datetime(2026, 11, 12, 9, 30, tzinfo=AUCKLAND)
    first = download_prices(
        start=date(2026, 11, 11),
        end=date(2026, 11, 11),
        today=date(2026, 11, 18),
        now=now,
        landing=landing,
        fetcher=_fetcher(files),
    )
    assert first.downloaded == [final_path, interim_path]
    saved = landing / final_path
    assert sha256_hex(saved.read_bytes()) == sha256_hex(body)

    second = download_prices(
        start=date(2026, 11, 11),
        end=date(2026, 11, 11),
        today=date(2026, 11, 18),
        now=datetime(2026, 11, 12, 15, 30, tzinfo=AUCKLAND),
        landing=landing,
        fetcher=_fetcher(files),
    )
    assert second.downloaded == []
    assert second.replaced == []
    assert final_path in second.unchanged
    assert f"downloaded relative_path={final_path}" in caplog.text
    assert f"unchanged relative_path={final_path}" in caplog.text
    assert "download finished downloaded=0 replaced=0 unchanged=2 missing=0" in caplog.text
    record = Manifest.load(landing / "daily/2026-11-11/manifest.json").files[final_path]
    assert len(record.observations) == 2
    assert record.sha256 == sha256_hex(body)


def test_changed_checksum_replaces_the_local_file(tmp_path: Path) -> None:
    landing = tmp_path / "landing"
    relative = "daily/2026-11-12/20261112_FinalEnergyPrices_I.csv"
    now = datetime(2026, 11, 12, 9, 30, tzinfo=AUCKLAND)
    download_prices(
        start=date(2026, 11, 12),
        end=date(2026, 11, 12),
        today=date(2026, 11, 18),
        now=now,
        landing=landing,
        fetcher=_fetcher({"20261112_FinalEnergyPrices_I.csv": b"first\n"}),
    )
    manifest_path = landing / "daily/2026-11-12/manifest.json"
    manifest = Manifest.load(manifest_path)
    manifest.files[relative].uploaded = True
    manifest.save(manifest_path)
    replaced = download_prices(
        start=date(2026, 11, 12),
        end=date(2026, 11, 12),
        today=date(2026, 11, 18),
        now=datetime(2026, 11, 12, 15, 30, tzinfo=AUCKLAND),
        landing=landing,
        fetcher=_fetcher({"20261112_FinalEnergyPrices_I.csv": b"second\n"}),
    )
    record = Manifest.load(manifest_path).files[relative]
    assert replaced.replaced == [relative]
    assert record.uploaded is False
    assert (landing / relative).read_bytes() == b"second\n"


def test_each_trading_date_has_its_own_manifest(tmp_path: Path) -> None:
    landing = tmp_path / "landing"
    download_prices(
        start=date(2026, 11, 11),
        end=date(2026, 11, 12),
        today=date(2026, 11, 18),
        now=datetime(2026, 11, 12, 9, 30, tzinfo=AUCKLAND),
        landing=landing,
        fetcher=_fetcher(
            {
                "20261111_FinalEnergyPrices.csv": b"a\n",
                "20261112_FinalEnergyPrices.csv": b"b\n",
            }
        ),
    )
    first = Manifest.load(landing / "daily/2026-11-11/manifest.json")
    second = Manifest.load(landing / "daily/2026-11-12/manifest.json")
    assert set(first.files) == {"daily/2026-11-11/20261111_FinalEnergyPrices.csv"}
    assert set(second.files) == {"daily/2026-11-12/20261112_FinalEnergyPrices.csv"}
