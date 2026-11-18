from datetime import date, datetime
from pathlib import Path

import pytest

from capture.download import IncompleteDownload, download_prices, require_content_length, urllib_fetcher
from capture.manifest import IncompleteFile, Manifest, store_bytes
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
    assert "download finished downloaded=0 replaced=0 unchanged=2 restored=0 missing=0" in caplog.text
    record = Manifest.load(landing / "daily/2026-11-11/manifest.json").files[final_path]
    assert [item["outcome"] for item in record.observations] == ["downloaded", "unchanged"]
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
    assert [item["outcome"] for item in record.observations] == ["downloaded", "replaced"]
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


def test_a_short_local_file_is_rewritten_when_the_checksum_matches(tmp_path: Path) -> None:
    landing = tmp_path / "landing"
    body = b"TradingDate,TradingPeriod\n2026-11-11,1\n"
    relative = "daily/2026-11-11/20261111_FinalEnergyPrices.csv"
    files = {"20261111_FinalEnergyPrices.csv": body}
    download_prices(
        start=date(2026, 11, 11),
        end=date(2026, 11, 11),
        today=date(2026, 11, 18),
        now=datetime(2026, 11, 12, 9, 30, tzinfo=AUCKLAND),
        landing=landing,
        fetcher=_fetcher(files),
    )
    manifest_path = landing / "daily/2026-11-11/manifest.json"
    manifest = Manifest.load(manifest_path)
    manifest.files[relative].uploaded = True
    manifest.save(manifest_path)
    (landing / relative).write_bytes(b"short")
    restored = download_prices(
        start=date(2026, 11, 11),
        end=date(2026, 11, 11),
        today=date(2026, 11, 18),
        now=datetime(2026, 11, 12, 15, 30, tzinfo=AUCKLAND),
        landing=landing,
        fetcher=_fetcher(files),
    )
    saved = Manifest.load(manifest_path).files[relative]
    assert restored.restored == [relative]
    assert [item["outcome"] for item in saved.observations] == ["downloaded", "restored"]
    assert (landing / relative).read_bytes() == body
    assert saved.uploaded is True
    assert saved.sha256 == sha256_hex(body)
    assert list((landing / "daily/2026-11-11").glob("*.partial")) == []


def test_a_partial_write_is_not_recorded(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    destination = tmp_path / "20261111_FinalEnergyPrices.csv"
    content = b"full-file\n"
    real_read = Path.read_bytes

    def short_read(self: Path) -> bytes:
        if self.name.endswith(".partial"):
            return b"x"
        return real_read(self)

    monkeypatch.setattr(Path, "read_bytes", short_read)
    manifest = Manifest()
    with pytest.raises(IncompleteFile):
        store_bytes(
            manifest,
            relative_path="daily/2026-11-11/20261111_FinalEnergyPrices.csv",
            content=content,
            url="https://example.test/20261111_FinalEnergyPrices.csv",
            status="final",
            trading_date="2026-11-11",
            now=datetime(2026, 11, 12, 9, 30, tzinfo=AUCKLAND),
            destination=destination,
        )
    assert manifest.files == {}
    assert not destination.exists()
    assert not destination.with_name(destination.name + ".partial").exists()


def test_content_length_must_match_the_body() -> None:
    url = "https://example.test/20261113_FinalEnergyPrices.csv"
    body = b"price,row\n"
    require_content_length(str(len(body)), len(body), url)
    with pytest.raises(IncompleteDownload, match="does not match"):
        require_content_length(str(len(body)), len(b"short"), url)
    with pytest.raises(IncompleteDownload, match="missing Content-Length"):
        require_content_length(None, 11, url)
    with pytest.raises(IncompleteDownload, match="empty file"):
        require_content_length("0", 0, url)


def test_urllib_fetcher_rejects_a_short_response(monkeypatch: pytest.MonkeyPatch) -> None:
    url = "https://example.test/20261113_FinalEnergyPrices.csv"

    class _Response:
        headers = {"Content-Length": "4"}

        def read(self) -> bytes:
            return b"ab"

        def __enter__(self) -> "_Response":
            return self

        def __exit__(self, *args: object) -> bool:
            return False

    monkeypatch.setattr("capture.download.urllib.request.urlopen", lambda *args, **kwargs: _Response())
    with pytest.raises(IncompleteDownload):
        urllib_fetcher(url)


def test_missing_interim_is_quiet_once_the_final_is_in_hand(tmp_path: Path, caplog) -> None:
    caplog.set_level("INFO", logger="capture")
    landing = tmp_path / "landing"
    requested: list[str] = []
    files = {
        "20261116_FinalEnergyPrices.csv": b"final\n",
        "20261117_FinalEnergyPrices_I.csv": b"interim\n",
    }

    def fetch(url: str) -> bytes | None:
        name = url.rsplit("/", 1)[-1]
        requested.append(name)
        return files.get(name)

    report = download_prices(
        start=date(2026, 11, 16),
        end=date(2026, 11, 17),
        today=date(2026, 11, 18),
        now=datetime(2026, 11, 18, 9, 30, tzinfo=AUCKLAND),
        landing=landing,
        fetcher=fetch,
    )
    assert "20261116_FinalEnergyPrices_I.csv" in requested
    assert "20261116_FinalEnergyPrices_I.csv" not in report.missing
    assert "missing name=20261116_FinalEnergyPrices_I.csv" not in caplog.text
    assert report.missing == ["20261117_FinalEnergyPrices.csv"]
    assert "missing name=20261117_FinalEnergyPrices.csv" in caplog.text
