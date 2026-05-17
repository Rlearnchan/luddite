"""Render jibi scored candidates into a daily Markdown digest and CSV preview."""

from __future__ import annotations

import csv
from datetime import date
from pathlib import Path
from typing import Annotated, Any

import typer
from rich.console import Console

from luddite import paths
from luddite.utils.jsonl import read_jsonl

app = typer.Typer(no_args_is_help=False)
console = Console()


def _digest_date(value: str | None = None) -> str:
    return value or date.today().isoformat()


def _score_band(candidate: dict[str, Any]) -> str:
    return str(candidate.get("final_grade") or "C")


def top_candidates(candidates: list[dict[str, Any]], limit: int = 10) -> list[dict[str, Any]]:
    return sorted(
        candidates,
        key=lambda item: (
            item.get("scores", {}).get("total_score", 0),
            item.get("scores", {}).get("broadcast_potential_proxy", 0),
        ),
        reverse=True,
    )[:limit]


def render_markdown(candidates: list[dict[str, Any]], digest_date: str) -> str:
    lines = [
        f"# jibi Daily Digest - {digest_date}",
        "",
        (
            "Local/manual-input MVP digest. No LLM, RSS collector, Google Sheet "
            "append, or Slack bot was used."
        ),
        "",
        "## Top 10 Candidates",
        "",
    ]
    if not candidates:
        lines.append("No candidates available.")
        return "\n".join(lines) + "\n"

    for rank, candidate in enumerate(candidates, start=1):
        scores = candidate.get("scores", {})
        risk_flags = ", ".join(candidate.get("risk_flags", [])) or "-"
        evidence_needed = ", ".join(candidate.get("evidence_needed", [])) or "추가 근거 확인"
        expansions = ", ".join(candidate.get("possible_expansions", [])) or "추가 리서치 후 작성"
        lines.extend(
            [
                f"### {rank}. {candidate['title']}",
                "",
                f"- URL: {candidate['seed_url']}",
                f"- Source: {candidate['source']}",
                f"- Grade: {_score_band(candidate)} / score {scores.get('total_score', 0)}",
                f"- Recommended action: {candidate.get('recommended_action', 'keep_for_later')}",
                f"- Risk level: {candidate.get('risk_level', 'medium')}",
                f"- Risk flags: {risk_flags}",
                f"- Why interesting: {candidate.get('why_interesting', '')}",
                f"- Possible expansions: {expansions}",
                f"- Evidence needed: {evidence_needed}",
                "",
            ]
        )
    return "\n".join(lines)


def write_sheet_preview(path: Path, candidates: list[dict[str, Any]], digest_date: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "rank",
        "title",
        "url",
        "source",
        "source_marker",
        "final_grade",
        "recommended_action",
        "risk_level",
        "risk_flags",
        "why_interesting",
        "digest_date",
    ]
    with path.open("w", encoding="utf-8-sig", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        for rank, candidate in enumerate(candidates, start=1):
            writer.writerow(
                {
                    "rank": rank,
                    "title": candidate["title"],
                    "url": candidate["seed_url"],
                    "source": candidate["source"],
                    "source_marker": "jibi",
                    "final_grade": _score_band(candidate),
                    "recommended_action": candidate.get("recommended_action", "keep_for_later"),
                    "risk_level": candidate.get("risk_level", "medium"),
                    "risk_flags": ",".join(candidate.get("risk_flags", [])),
                    "why_interesting": candidate.get("why_interesting", ""),
                    "digest_date": digest_date,
                }
            )


def render_daily_digest(
    input_path: Path = paths.JIBI_SCORED_CANDIDATES_JSONL,
    output_dir: Path = paths.DAILY_DIGEST_DIR,
    digest_date: str | None = None,
    limit: int = 10,
) -> tuple[Path, Path, list[dict[str, Any]]]:
    date_value = _digest_date(digest_date)
    candidates = read_jsonl(input_path) if input_path.exists() else []
    top = top_candidates(candidates, limit=limit)
    md_path = output_dir / f"{date_value}.md"
    csv_path = output_dir / f"{date_value}_sheet_append_preview.csv"
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text(render_markdown(top, date_value), encoding="utf-8")
    write_sheet_preview(csv_path, top, date_value)
    return md_path, csv_path, top


@app.callback(invoke_without_command=True)
def main(
    input_path: Annotated[
        Path,
        typer.Option("--input", help="Scored candidate JSONL input path."),
    ] = paths.JIBI_SCORED_CANDIDATES_JSONL,
    output_dir: Annotated[
        Path,
        typer.Option("--output-dir", help="Daily digest output directory."),
    ] = paths.DAILY_DIGEST_DIR,
    digest_date: Annotated[
        str | None,
        typer.Option("--date", help="Digest date in YYYY-MM-DD."),
    ] = None,
    limit: Annotated[int, typer.Option("--limit", help="Number of candidates.")] = 10,
) -> None:
    md_path, csv_path, top = render_daily_digest(
        input_path=input_path,
        output_dir=output_dir,
        digest_date=digest_date,
        limit=limit,
    )
    console.print(
        f"[green]Rendered {len(top)} candidates to {md_path} and {csv_path}.[/green]"
    )


if __name__ == "__main__":
    app()
