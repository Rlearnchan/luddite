"""Build a JSONL manifest over local corpus sources."""

from __future__ import annotations

import hashlib
import unicodedata
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Any

import typer

from luddite import paths
from luddite.utils.jsonl import write_jsonl
from luddite.utils.schemas import validate_with_schema

app = typer.Typer(no_args_is_help=False)


def _relative(path: Path) -> str:
    try:
        return str(path.relative_to(paths.REPO_ROOT))
    except ValueError:
        return str(path)


def _stable_id(prefix: str, path: Path) -> str:
    digest = hashlib.sha1(_relative(path).encode("utf-8")).hexdigest()[:12]
    return f"{prefix}_{digest}"


def _iso_from_timestamp(timestamp: float) -> str:
    return datetime.fromtimestamp(timestamp, UTC).isoformat()


def _item(
    path: Path,
    item_type: str,
    title: str,
    used_by: list[str],
    risk_flags: list[str] | None = None,
) -> dict[str, Any]:
    stat = path.stat()
    return {
        "corpus_id": _stable_id(item_type, path),
        "type": item_type,
        "title": title,
        "source": "local",
        "local_path": _relative(path),
        "remote_url": None,
        "created_at": _iso_from_timestamp(stat.st_ctime),
        "modified_at": _iso_from_timestamp(stat.st_mtime),
        "parsed_at": None,
        "used_by": used_by,
        "risk_flags": risk_flags or [],
    }


def build_manifest() -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []

    for path in sorted(paths.STORYLINE_RAW_DIR.glob("*.rtf")):
        items.append(
            _item(
                path=path,
                item_type="rtf",
                title=unicodedata.normalize("NFC", path.stem),
                used_by=["anny", "eval"],
            )
        )

    for path in sorted(paths.LATEST_PPT_RAW_DIR.glob("*.pptx")):
        items.append(
            _item(
                path=path,
                item_type="pptx",
                title=unicodedata.normalize("NFC", path.stem),
                used_by=["piti", "eval"],
                risk_flags=["copyright_image_risk"],
            )
        )

    for path in sorted(paths.LEGACY_PPT_RAW_DIR.glob("*.pptx")):
        items.append(
            _item(
                path=path,
                item_type="pptx",
                title=unicodedata.normalize("NFC", path.stem),
                used_by=["piti"],
                risk_flags=["copyright_image_risk", "needs_human_review"],
            )
        )

    for pattern in ("*.csv", "*.tsv", "*.xlsx"):
        for path in sorted(paths.SHEETS_RAW_DIR.glob(pattern)):
            items.append(
                _item(
                    path=path,
                    item_type="sheet",
                    title=unicodedata.normalize("NFC", path.stem),
                    used_by=["jibi"],
                    risk_flags=["needs_human_review"],
                )
            )

    return items


def validate_manifest_items(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    validated: list[dict[str, Any]] = []
    for item in items:
        errors = validate_with_schema(item, "corpus_manifest_schema.json")
        if errors:
            item = {
                **item,
                "validation_status": "failed",
                "validation_errors": errors,
            }
        else:
            item = {**item, "validation_status": "passed"}
        validated.append(item)
    return validated


def build_and_write_manifest(output: Path) -> list[dict[str, Any]]:
    items = validate_manifest_items(build_manifest())
    write_jsonl(output, items)
    return items


@app.callback(invoke_without_command=True)
def main(
    output: Annotated[
        Path,
        typer.Option("--output", help="Corpus manifest JSONL output path."),
    ] = paths.CORPUS_MANIFEST_JSONL,
) -> None:
    items = build_and_write_manifest(output)
    failed = sum(1 for item in items if item["validation_status"] != "passed")
    typer.echo(f"Wrote {len(items)} manifest items to {output} ({failed} validation failures)")


if __name__ == "__main__":
    app()
