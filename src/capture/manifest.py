"""Local record of captured files. An unchanged checksum is not written again."""

from dataclasses import dataclass, field
from datetime import datetime
import json
from pathlib import Path

from log import get_logger
from shared.checksums import sha256_hex

logger = get_logger(__name__)


class IncompleteFile(Exception):
    """The bytes on disk do not match the bytes just downloaded."""

    def __init__(self, path: Path, expected: str, actual: str) -> None:
        self.path = path
        self.expected = expected
        self.actual = actual
        super().__init__(f"partial file at {path}: expected {expected}, got {actual}")


@dataclass
class FileRecord:
    relative_path: str
    sha256: str
    size: int
    url: str
    status: str
    trading_date: str | None
    uploaded: bool = False
    local_exists: bool = True
    observations: list[dict[str, str]] = field(default_factory=list)

    def to_json(self) -> dict:
        return {
            "relative_path": self.relative_path,
            "sha256": self.sha256,
            "bytes": self.size,
            "url": self.url,
            "status": self.status,
            "trading_date": self.trading_date,
            "uploaded": self.uploaded,
            "local_exists": self.local_exists,
            "observations": self.observations,
        }

    @classmethod
    def from_json(cls, payload: dict) -> "FileRecord":
        return cls(
            relative_path=payload["relative_path"],
            sha256=payload["sha256"],
            size=payload["bytes"],
            url=payload["url"],
            status=payload["status"],
            trading_date=payload.get("trading_date"),
            uploaded=payload.get("uploaded", False),
            local_exists=payload.get("local_exists", True),
            observations=list(payload.get("observations", [])),
        )


@dataclass
class Manifest:
    files: dict[str, FileRecord] = field(default_factory=dict)

    @classmethod
    def load(cls, path: Path) -> "Manifest":
        if not path.exists():
            return cls()
        payload = json.loads(path.read_text())
        files = {key: FileRecord.from_json(value) for key, value in payload.get("files", {}).items()}
        return cls(files=files)

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        body = {"files": {key: record.to_json() for key, record in sorted(self.files.items())}}
        temporary = path.with_suffix(path.suffix + ".tmp")
        temporary.write_text(json.dumps(body, indent=2) + "\n")
        temporary.replace(path)


def observe(record: FileRecord, now: datetime, digest: str, outcome: str) -> None:
    record.observations.append({"at": now.isoformat(), "sha256": digest, "outcome": outcome})


def _disk_matches(destination: Path, digest: str) -> bool:
    if not destination.is_file():
        return False
    return sha256_hex(destination.read_bytes()) == digest


def _write_verified(destination: Path, content: bytes, digest: str) -> None:
    """Write `content` beside `destination` and rename it only when the hash matches."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(destination.name + ".partial")
    try:
        temporary.write_bytes(content)
        written = temporary.read_bytes()
        actual = sha256_hex(written)
        if actual != digest or len(written) != len(content):
            logger.error(
                "partial file path=%s expected=%s actual=%s",
                temporary,
                digest,
                actual,
            )
            raise IncompleteFile(temporary, digest, actual)
        temporary.replace(destination)
    finally:
        if temporary.exists():
            temporary.unlink()


def store_bytes(
    manifest: Manifest,
    *,
    relative_path: str,
    content: bytes,
    url: str,
    status: str,
    trading_date: str | None,
    now: datetime,
    destination: Path,
) -> str:
    """Write `content` unless the manifest and the file on disk already have this checksum.

    Returns `downloaded`, `unchanged`, `replaced`, or `restored`.
    """
    digest = sha256_hex(content)
    current = manifest.files.get(relative_path)
    if current is not None and current.sha256 == digest:
        if _disk_matches(destination, digest):
            observe(current, now, digest, "unchanged")
            current.local_exists = True
            logger.info(
                "unchanged relative_path=%s bytes=%s sha256=%s",
                relative_path,
                len(content),
                digest,
            )
            return "unchanged"
        _write_verified(destination, content, digest)
        observe(current, now, digest, "restored")
        current.local_exists = True
        logger.info(
            "restored relative_path=%s bytes=%s sha256=%s",
            relative_path,
            len(content),
            digest,
        )
        return "restored"
    _write_verified(destination, content, digest)
    record = current or FileRecord(
        relative_path=relative_path,
        sha256=digest,
        size=len(content),
        url=url,
        status=status,
        trading_date=trading_date,
    )
    record.sha256 = digest
    record.size = len(content)
    record.url = url
    record.status = status
    record.trading_date = trading_date
    record.uploaded = False
    record.local_exists = True
    outcome = "replaced" if current is not None else "downloaded"
    observe(record, now, digest, outcome)
    manifest.files[relative_path] = record
    logger.info(
        "%s relative_path=%s bytes=%s sha256=%s",
        outcome,
        relative_path,
        record.size,
        digest,
    )
    return outcome
