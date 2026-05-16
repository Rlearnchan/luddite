"""JSON Schema loading and validation helpers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from luddite import paths


def load_schema(name: str) -> dict[str, Any]:
    schema_path = paths.SPECS_DIR / name
    with schema_path.open(encoding="utf-8") as source:
        return json.load(source)


def validate_with_schema(record: dict[str, Any], schema_name: str) -> list[str]:
    schema = load_schema(schema_name)
    validator = Draft202012Validator(schema)
    return [error.message for error in sorted(validator.iter_errors(record), key=str)]


def schema_path(name: str) -> Path:
    return paths.SPECS_DIR / name
