"""Checksums for EMI files. Callers pass the bytes; this module does not read the clock or the network."""

import hashlib


def sha256_hex(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()
