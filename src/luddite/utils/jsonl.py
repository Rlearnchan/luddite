"""Small JSONL helpers used by parser modules."""

from __future__ import annotations

import json
from collections.abc import Iterable
from pathlib import Path
from typing import Any


def write_jsonl(path: Path, records: Iterable[dict[str, Any]]) -> int:
    """Write records as UTF-8 JSONL and return the number written."""
    path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with path.open("w", encoding="utf-8") as output:
        for record in records:
            output.write(json.dumps(record, ensure_ascii=False, sort_keys=True))
            output.write("\n")
            count += 1
    return count


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    """Read a UTF-8 JSONL file."""
    with path.open(encoding="utf-8") as source:
        return [json.loads(line) for line in source if line.strip()]
