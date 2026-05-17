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

ACTION_LABELS = {
    "send_to_anny": "바로 볼 만한 후보",
    "gather_more_evidence": "자료 보강 필요",
    "editorial_review": "사람 검토 필요",
    "keep_for_later": "킵 후보",
    "reject": "제외/거절",
}


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


def _action_counts(candidates: list[dict[str, Any]]) -> dict[str, int]:
    counts = {action: 0 for action in ACTION_LABELS}
    for candidate in candidates:
        action = candidate.get("recommended_action", "keep_for_later")
        counts[action] = counts.get(action, 0) + 1
    return counts


def _bullet_lines(values: list[str] | None, fallback: list[str]) -> list[str]:
    items = [str(value).strip() for value in values or [] if str(value).strip()]
    return items or fallback


def render_markdown(candidates: list[dict[str, Any]], digest_date: str) -> str:
    counts = _action_counts(candidates)
    lines = [
        f"# Luddite Daily Digest — {digest_date}",
        "",
        (
            "Local/manual-input MVP digest. No LLM, RSS collector, Google Sheet "
            "append, or Slack bot was used."
        ),
        "",
        "## 오늘의 추천",
        "",
        f"- 바로 볼 만한 후보: {counts.get('send_to_anny', 0)}개",
        f"- 자료 보강 필요: {counts.get('gather_more_evidence', 0)}개",
        f"- 사람 검토 필요: {counts.get('editorial_review', 0)}개",
        f"- 킵 후보: {counts.get('keep_for_later', 0)}개",
        f"- 제외/거절: {counts.get('reject', 0)}개",
        "",
        "## Top 10",
        "",
    ]
    if not candidates:
        lines.append("No candidates available.")
        return "\n".join(lines) + "\n"

    for rank, candidate in enumerate(candidates, start=1):
        scores = candidate.get("scores", {})
        risk_flags = ", ".join(candidate.get("risk_flags", [])) or "-"
        evidence_needed = _bullet_lines(
            candidate.get("evidence_needed"),
            ["추가 독립 출처 확인"],
        )
        expansions = _bullet_lines(
            candidate.get("possible_expansions"),
            ["배경 설명", "구조적 확장", "한국 시청자 연결 지점"],
        )
        lines.extend(
            [
                f"### {rank}. {candidate['title']}",
                "",
                (
                    f"- Grade / Action / Risk: {_score_band(candidate)} "
                    f"({scores.get('total_score', 0)}) / "
                    f"{candidate.get('recommended_action', 'keep_for_later')} / "
                    f"{candidate.get('risk_level', 'medium')}"
                ),
                f"- Source / Link: {candidate['source']} / {candidate['seed_url']}",
                f"- Risk flags: {risk_flags}",
                "- 왜 볼 만한가:",
                f"  - {candidate.get('why_interesting', '')}",
                "- 확장 가능성:",
                *[f"  - {item}" for item in expansions[:3]],
                "- 필요한 추가자료:",
                *[f"  - {item}" for item in evidence_needed[:3]],
                "",
            ]
        )
    return "\n".join(lines)


def write_sheet_preview(path: Path, candidates: list[dict[str, Any]], digest_date: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "수집일",
        "주제명",
        "링크",
        "제작 여부",
        "방송 활용 여부",
        "이유(채택/사용/미사용)",
        "작성자/source",
        "jibi_grade",
        "recommended_action",
        "risk_level",
        "risk_flags",
        "why_interesting",
        "possible_expansions",
        "evidence_needed",
    ]
    with path.open("w", encoding="utf-8-sig", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        for candidate in candidates:
            writer.writerow(
                {
                    "수집일": digest_date,
                    "주제명": candidate["title"],
                    "링크": candidate["seed_url"],
                    "제작 여부": "",
                    "방송 활용 여부": "",
                    "이유(채택/사용/미사용)": candidate.get("why_interesting", ""),
                    "작성자/source": "jibi",
                    "jibi_grade": _score_band(candidate),
                    "recommended_action": candidate.get("recommended_action", "keep_for_later"),
                    "risk_level": candidate.get("risk_level", "medium"),
                    "risk_flags": ",".join(candidate.get("risk_flags", [])),
                    "why_interesting": candidate.get("why_interesting", ""),
                    "possible_expansions": " | ".join(candidate.get("possible_expansions", [])),
                    "evidence_needed": " | ".join(candidate.get("evidence_needed", [])),
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
