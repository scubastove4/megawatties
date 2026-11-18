"""Local record of captured files. An unchanged checksum is not written again."""

from dataclasses import dataclass, field
from datetime import datetime
import json
from pathlib import Path

from log import get_logger
from shared.checksums import sha256_hex

logger = get_logger(__name__)


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


def observe(record: FileRecord, now: datetime, digest: str) -> None:
    record.observations.append({"at": now.isoformat(), "sha256": digest})


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
    """Write `content` unless the manifest already has this checksum.

    Returns `downloaded`, `unchanged`, or `replaced`.
    """
    digest = sha256_hex(content)
    current = manifest.files.get(relative_path)
    if current is not None and current.sha256 == digest:
        observe(current, now, digest)
        current.local_exists = destination.exists()
        logger.info(
            "unchanged relative_path=%s bytes=%s sha256=%s",
            relative_path,
            len(content),
            digest,
        )
        return "unchanged"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(content)
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
    observe(record, now, digest)
    manifest.files[relative_path] = record
    outcome = "replaced" if current is not None else "downloaded"
    logger.info(
        "%s relative_path=%s bytes=%s sha256=%s",
        outcome,
        relative_path,
        record.size,
        digest,
    )
    return outcome
