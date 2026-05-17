"""Rule-based pre-score for jibi candidate drafts."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated, Any

import typer
from rich.console import Console

from luddite import paths
from luddite.agents.jibi.heuristics import (
    NUMBER_TERMS,
    POLITICAL_TERMS,
    PUNCHLINE_TERMS,
    STRUCTURAL_TERMS,
    WEIRD_TERMS,
    contains_any,
    count_any,
    text_blob,
)
from luddite.utils.jsonl import read_jsonl, write_jsonl

app = typer.Typer(no_args_is_help=False)
console = Console()

HIGH_RISK_FLAGS = {
    "political_sensitivity",
    "medical_claim_risk",
    "crime_or_drug_sensitivity",
    "live_news_volatility",
}


def _bounded(value: int, low: int = 0, high: int = 5) -> int:
    return max(low, min(high, value))


def _score_band(total_score: int, risk_penalty: int) -> str:
    if risk_penalty >= 4:
        return "C" if total_score >= 12 else "D"
    if total_score >= 20:
        return "A"
    if total_score >= 14:
        return "B"
    if total_score >= 8:
        return "C"
    return "D"


def _risk_level(risk_flags: list[str], risk_penalty: int) -> str:
    if risk_penalty >= 4 or any(flag in HIGH_RISK_FLAGS for flag in risk_flags):
        return "high"
    if risk_penalty >= 2 or risk_flags:
        return "medium"
    return "low"


def _recommended_action(final_grade: str, risk_level: str, risk_flags: list[str]) -> str:
    if "political_sensitivity" in risk_flags:
        return "editorial_review"
    if risk_level == "high" and final_grade in {"A", "B"}:
        return "editorial_review"
    if final_grade == "A" and risk_level == "low":
        return "send_to_anny"
    if final_grade in {"A", "B"} and risk_level in {"low", "medium"}:
        return "gather_more_evidence"
    if final_grade == "C":
        return "keep_for_later"
    return "reject"


def score_candidate(candidate: dict[str, Any]) -> dict[str, Any]:
    text = text_blob(
        candidate.get("title"),
        candidate.get("summary"),
        candidate.get("why_interesting"),
        " ".join(candidate.get("risk_flags", [])),
    )
    risk_flags = list(candidate.get("risk_flags", []))
    weird_hook = _bounded(1 + count_any(text, WEIRD_TERMS), high=5)
    structural_expansion = _bounded(1 + count_any(text, STRUCTURAL_TERMS), high=5)
    numbers_strength = _bounded(
        1 + count_any(text, NUMBER_TERMS) + int(any(c.isdigit() for c in text))
    )
    punchline_potential = _bounded(1 + count_any(text, PUNCHLINE_TERMS), high=5)
    evidence_depth = {"low": 1, "medium": 3, "high": 5}.get(
        candidate.get("evidence_depth_hint"),
        2,
    )
    timeliness = 3 if candidate.get("published_at") else 2
    broadcast_potential_proxy = _bounded(
        weird_hook + structural_expansion + punchline_potential - 3,
        high=5,
    )
    risk_penalty = min(5, len(risk_flags) + (2 if contains_any(text, POLITICAL_TERMS) else 0))
    total_score = (
        broadcast_potential_proxy * 3
        + evidence_depth * 2
        + numbers_strength * 2
        + weird_hook * 2
        + structural_expansion * 2
        + punchline_potential
        + timeliness
        - risk_penalty * 2
    )
    final_grade = _score_band(total_score, risk_penalty)
    risk_level = _risk_level(risk_flags, risk_penalty)
    scored = {
        **candidate,
        "scores": {
            "broadcast_potential_proxy": broadcast_potential_proxy,
            "evidence_depth": evidence_depth,
            "numbers_strength": numbers_strength,
            "weird_hook": weird_hook,
            "structural_expansion": structural_expansion,
            "punchline_potential": punchline_potential,
            "timeliness": timeliness,
            "risk_penalty": risk_penalty,
            "total_score": total_score,
        },
        "final_grade": final_grade,
        "risk_level": risk_level,
        "recommended_action": _recommended_action(final_grade, risk_level, risk_flags),
        "status": "scored",
    }
    return scored


def score_candidates(
    input_path: Path = paths.JIBI_CANDIDATES_JSONL,
    output_path: Path = paths.JIBI_SCORED_CANDIDATES_JSONL,
) -> list[dict[str, Any]]:
    candidates = read_jsonl(input_path) if input_path.exists() else []
    scored = [score_candidate(candidate) for candidate in candidates]
    scored.sort(
        key=lambda item: (
            item.get("scores", {}).get("total_score", 0),
            item.get("scores", {}).get("broadcast_potential_proxy", 0),
        ),
        reverse=True,
    )
    write_jsonl(output_path, scored)
    return scored


@app.callback(invoke_without_command=True)
def main(
    input_path: Annotated[
        Path,
        typer.Option("--input", help="Jibi candidate JSONL input path."),
    ] = paths.JIBI_CANDIDATES_JSONL,
    output: Annotated[
        Path,
        typer.Option("--output", help="Scored candidate JSONL output path."),
    ] = paths.JIBI_SCORED_CANDIDATES_JSONL,
) -> None:
    scored = score_candidates(input_path=input_path, output_path=output)
    console.print(f"[green]Wrote {len(scored)} scored candidates to {output}.[/green]")


if __name__ == "__main__":
    app()
