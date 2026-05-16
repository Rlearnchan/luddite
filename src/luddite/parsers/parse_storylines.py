"""Parse local RTF/TXT storyline files into corpus JSONL."""

from __future__ import annotations

import hashlib
import re
import unicodedata
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Any

import typer
from striprtf.striprtf import rtf_to_text

from luddite import paths
from luddite.utils.jsonl import write_jsonl
from luddite.utils.security import detect_risk_flags, redact_sensitive_text
from luddite.utils.urls import extract_urls

app = typer.Typer(no_args_is_help=False)

SECTION_RE = re.compile(r"(?<!\d)(?P<num>\d{1,2})[.)]\s+(?P<title>[^\n]{0,80})")
HEADING_RE = re.compile(r"^\s*(?:#+\s+|<)(?P<title>[^>\n]{2,80})(?:>)?\s*$")


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _relative(path: Path) -> str:
    try:
        return str(path.relative_to(paths.REPO_ROOT))
    except ValueError:
        return str(path)


def _stable_id(prefix: str, path: Path) -> str:
    digest = hashlib.sha1(_relative(path).encode("utf-8")).hexdigest()[:12]
    return f"{prefix}_{digest}"


def _normalize_text(text: str) -> str:
    text = unicodedata.normalize("NFC", text)
    text = text.replace("\xa0", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def normalize_title(path: Path, plain_text: str = "") -> str:
    title = unicodedata.normalize("NFC", path.stem).strip()
    if title.startswith("무제") and plain_text:
        first_line = next((line.strip() for line in plain_text.splitlines() if line.strip()), "")
        if first_line:
            title = first_line[:80]
    return title


def parse_storyline_text(path: Path) -> str:
    raw = path.read_text(encoding="utf-8", errors="ignore")
    if path.suffix.lower() == ".rtf":
        raw = rtf_to_text(raw)
    return _normalize_text(redact_sensitive_text(raw))


def estimate_sections(text: str) -> list[dict[str, Any]]:
    sections: list[dict[str, Any]] = []
    for match in SECTION_RE.finditer(text):
        preview = text[match.start() : match.start() + 160].replace("\n", " ").strip()
        sections.append(
            {
                "marker": match.group("num"),
                "start_char": match.start(),
                "title_guess": match.group("title").strip(),
                "preview": preview,
            }
        )

    if sections:
        return sections

    for index, line in enumerate(text.splitlines(), start=1):
        match = HEADING_RE.match(line)
        if match:
            sections.append(
                {
                    "marker": str(len(sections) + 1),
                    "line_no": index,
                    "title_guess": match.group("title").strip(),
                    "preview": line.strip(),
                }
            )
    return sections


def _source_density(url_count: int, word_count: int) -> float:
    if word_count == 0:
        return 0.0
    return round(url_count / word_count * 1000, 2)


def parse_storyline_file(path: Path) -> dict[str, Any]:
    text = parse_storyline_text(path)
    urls = extract_urls(text)
    words = re.findall(r"\S+", text)
    title = normalize_title(path, text)
    risk_flags = detect_risk_flags(text, {"file_name": path.name})

    return {
        "corpus_id": _stable_id("storyline", path),
        "type": path.suffix.lower().lstrip("."),
        "title": title,
        "file_name": path.name,
        "local_path": _relative(path),
        "parse_status": "parsed",
        "parsed_at": _now_iso(),
        "plain_text": text,
        "char_count": len(text),
        "word_count": len(words),
        "url_count": len(urls),
        "urls": urls,
        "source_density_per_1000_words": _source_density(len(urls), len(words)),
        "estimated_sections": estimate_sections(text),
        "estimated_section_count": len(estimate_sections(text)),
        "has_korea_bridge": any(token in text for token in ["한국", "국내", "우리나라"]),
        "has_punchline_hint": any(token in text for token in ["농담", "회수", "ㅋㅋ", "?", "슈카"]),
        "risk_flags": risk_flags,
    }


def iter_storyline_files(input_dir: Path) -> list[Path]:
    if not input_dir.exists():
        return []
    files = [
        *input_dir.glob("*.rtf"),
        *input_dir.glob("*.txt"),
    ]
    return sorted(files, key=lambda path: unicodedata.normalize("NFC", path.name))


def parse_directory(input_dir: Path, output_path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for file_path in iter_storyline_files(input_dir):
        try:
            records.append(parse_storyline_file(file_path))
        except Exception as exc:  # pragma: no cover - defensive corpus reporting
            records.append(
                {
                    "corpus_id": _stable_id("storyline", file_path),
                    "type": file_path.suffix.lower().lstrip("."),
                    "title": normalize_title(file_path),
                    "file_name": file_path.name,
                    "local_path": _relative(file_path),
                    "parse_status": "failed",
                    "parsed_at": _now_iso(),
                    "error": str(exc),
                    "risk_flags": ["needs_human_review"],
                }
            )

    write_jsonl(output_path, records)
    return records


@app.callback(invoke_without_command=True)
def main(
    input_dir: Annotated[
        Path,
        typer.Option("--input-dir", help="Directory containing raw .rtf/.txt storyline files."),
    ] = paths.STORYLINE_RAW_DIR,
    output: Annotated[
        Path,
        typer.Option("--output", help="JSONL output path."),
    ] = paths.STORYLINE_PARSED_JSONL,
) -> None:
    records = parse_directory(input_dir, output)
    typer.echo(f"Wrote {len(records)} storyline records to {output}")


if __name__ == "__main__":
    app()
