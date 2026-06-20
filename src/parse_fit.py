"""Parse a .fit file into ride/summary/samples/laps records.

Stub: real implementation will use `fitparse` to extract session, record, and
lap messages. Kept minimal here so the repo scaffolds cleanly without a hard
dependency at init time.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class ParsedRide:
    file_hash: str
    summary: dict[str, Any] = field(default_factory=dict)
    samples: list[dict[str, Any]] = field(default_factory=list)
    laps: list[dict[str, Any]] = field(default_factory=list)


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def parse(path: Path) -> ParsedRide:
    """Parse a .fit file. Not yet implemented."""
    raise NotImplementedError(
        "fit parsing not implemented yet. Will use the `fitparse` library."
    )
