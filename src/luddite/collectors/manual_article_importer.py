"""Import local/manual article candidates into normalized article JSONL."""

from __future__ import annotations

import csv
import hashlib
import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Any

import typer
from rich.console import Console

from luddite import paths
from luddite.collectors.source_registry import match_source
from luddite.utils.jsonl import write_jsonl
from luddite.utils.schemas import validate_with_schema
from luddite.utils.urls import canonicalize_url

app = typer.Typer(no_args_is_help=False)
console = Console()


@dataclass
class ImportReport:
    input_mode: str = "input_dir"
    input_files: int = 0
    imported: int = 0
    duplicates: int = 0
    failures: list[str] = field(default_factory=list)


def stable_article_id(url: str, title: str = "") -> str:
    key = canonicalize_url(url) or title.strip()
    digest = hashlib.sha1(key.encode("utf-8")).hexdigest()[:12]
    return f"article_{digest}"


def _split_tags(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if not value:
        return []
    return [item.strip() for item in str(value).replace(";", ",").split(",") if item.strip()]


def _split_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if not value:
        return []
    return [item.strip() for item in str(value).replace(";", ",").split(",") if item.strip()]


def _read_jsonl(path: Path) -> tuple[list[dict[str, Any]], list[str]]:
    records: list[dict[str, Any]] = []
    failures: list[str] = []
    with path.open(encoding="utf-8") as source:
        for line_no, line in enumerate(source, start=1):
            if not line.strip():
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError as exc:
                failures.append(f"{path}:{line_no}: invalid JSONL ({exc})")
                continue
            if not isinstance(payload, dict):
                failures.append(f"{path}:{line_no}: record must be object")
                continue
            records.append(payload)
    return records, failures


def _read_csv(path: Path) -> tuple[list[dict[str, Any]], list[str]]:
    with path.open(encoding="utf-8-sig", newline="") as source:
        return list(csv.DictReader(source)), []


def read_input_records(
    input_dir: Path,
    input_files: list[Path] | None = None,
) -> tuple[list[tuple[Path, dict[str, Any]]], ImportReport]:
    report = ImportReport(input_mode="input_file" if input_files else "input_dir")
    records: list[tuple[Path, dict[str, Any]]] = []
    paths_to_read = (
        [Path(path) for path in input_files]
        if input_files
        else sorted([*input_dir.glob("*.jsonl"), *input_dir.glob("*.csv")])
    )
    for path in paths_to_read:
        report.input_files += 1
        if path.suffix not in {".jsonl", ".csv"}:
            report.failures.append(f"{path}: unsupported input file type")
            continue
        if not path.exists():
            report.failures.append(f"{path}: input file does not exist")
            continue
        if path.suffix == ".jsonl":
            loaded, failures = _read_jsonl(path)
        else:
            loaded, failures = _read_csv(path)
        report.failures.extend(failures)
        records.extend((path, record) for record in loaded)
    return records, report


def normalize_article_record(
    raw: dict[str, Any],
    *,
    collected_at: str,
    registry_path: Path = paths.SOURCE_REGISTRY_YAML,
) -> dict[str, Any]:
    title = str(raw.get("title") or raw.get("headline") or "").strip()
    url = canonicalize_url(str(raw.get("url") or raw.get("source_url") or "").strip())
    source_value = str(raw.get("source") or raw.get("source_name") or "").strip()
    source = match_source(source_value=source_value, url=url, registry_path=registry_path)
    article = {
        "article_id": str(raw.get("article_id") or stable_article_id(url, title)),
        "title": title,
        "url": url,
        "source": source.name,
        "source_id": source.id,
        "source_url_canonical": raw.get("source_url_canonical") or url,
        "duplicate_key": raw.get("duplicate_key") or stable_article_id(url, title),
        "published_at": raw.get("published_at") or None,
        "collected_at": str(raw.get("collected_at") or collected_at),
        "language": raw.get("language") or None,
        "region": raw.get("region") or source.region,
        "raw_summary": raw.get("raw_summary") or raw.get("summary") or None,
        "collector": str(raw.get("collector") or source.type or "manual"),
        "tags": _split_tags(raw.get("tags")),
        "source_count": int(raw.get("source_count") or 1),
        "source_sections": _split_list(raw.get("source_sections")),
        "supporting_source_ids": _split_list(raw.get("supporting_source_ids")),
    }
    return article


def import_articles(
    input_dir: Path = paths.ARTICLE_INBOX_DIR,
    input_files: list[Path] | None = None,
    output_path: Path = paths.RAW_ARTICLES_JSONL,
    report_path: Path = paths.REPORTS_DIR / "article_import_report.md",
    registry_path: Path = paths.SOURCE_REGISTRY_YAML,
) -> tuple[list[dict[str, Any]], ImportReport]:
    collected_at = datetime.now(UTC).isoformat()
    raw_records, report = read_input_records(input_dir, input_files=input_files)
    seen_urls: set[str] = set()
    articles: list[dict[str, Any]] = []
    for path, raw in raw_records:
        article = normalize_article_record(
            raw,
            collected_at=collected_at,
            registry_path=registry_path,
        )
        if not article["title"] or not article["url"]:
            report.failures.append(f"{path}: missing title or url")
            continue
        if article["url"] in seen_urls:
            report.duplicates += 1
            continue
        errors = validate_with_schema(article, "article_schema.json")
        if errors:
            report.failures.append(f"{path}: schema errors: {'; '.join(errors)}")
            continue
        seen_urls.add(article["url"])
        articles.append(article)
    write_jsonl(output_path, articles)
    report.imported = len(articles)
    write_import_report(report_path, report, output_path)
    return articles, report


def write_import_report(path: Path, report: ImportReport, output_path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Article Import Report",
        "",
        f"- Input mode: `{report.input_mode}`",
        f"- Input files: {report.input_files}",
        f"- Imported: {report.imported}",
        f"- Duplicate URLs skipped: {report.duplicates}",
        f"- Failures: {len(report.failures)}",
        f"- Output: `{output_path}`",
        "",
        "## Failures",
        "",
    ]
    if report.failures:
        lines.extend(f"- {failure}" for failure in report.failures)
    else:
        lines.append("- none")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


@app.callback(invoke_without_command=True)
def main(
    input_dir: Annotated[
        Path,
        typer.Option("--input-dir", help="Directory containing article JSONL/CSV files."),
    ] = paths.ARTICLE_INBOX_DIR,
    input_file: Annotated[
        list[Path] | None,
        typer.Option("--input-file", help="Specific article JSONL/CSV file to import."),
    ] = None,
    output: Annotated[
        Path,
        typer.Option("--output", help="Output raw article JSONL path."),
    ] = paths.RAW_ARTICLES_JSONL,
) -> None:
    articles, report = import_articles(
        input_dir=input_dir,
        input_files=input_file,
        output_path=output,
    )
    console.print(
        f"[green]Imported {len(articles)} articles to {output} "
        f"({report.duplicates} duplicates, {len(report.failures)} failures).[/green]"
    )


if __name__ == "__main__":
    app()
