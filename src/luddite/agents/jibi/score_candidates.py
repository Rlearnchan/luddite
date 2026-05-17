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
DIRECT_POLITICAL_EVAL_TERMS = {
    "대통령",
    "정당",
    "양당",
    "지지율",
    "선거",
    "party approval",
    "president",
}

SCORING_WEIGHTS = {
    "broadcast_potential_proxy": 25,
    "evidence_depth": 20,
    "numbers_strength": 15,
    "weird_hook": 12,
    "structural_expansion": 12,
    "punchline_potential": 8,
    "timeliness": 5,
    "risk_penalty": -30,
}


def _bounded(value: int, low: int = 0, high: int = 5) -> int:
    return max(low, min(high, value))


def _score_band(total_score: int, risk_penalty: int) -> str:
    if risk_penalty >= 4 and total_score < 70:
        return "D"
    if total_score >= 75:
        return "A"
    if total_score >= 55:
        return "B"
    if total_score >= 35:
        return "C"
    return "D"


def _risk_level(risk_flags: list[str], risk_penalty: int) -> str:
    if risk_penalty >= 4 or any(flag in HIGH_RISK_FLAGS for flag in risk_flags):
        return "high"
    if risk_penalty >= 2 or risk_flags:
        return "medium"
    return "low"


def _recommended_action(
    *,
    final_grade: str,
    risk_level: str,
    risk_flags: list[str],
    evidence_depth: int,
    numbers_strength: int,
    broadcast_potential_proxy: int,
    blocked_reason: str | None = None,
) -> str:
    if blocked_reason:
        return "reject"
    if "political_sensitivity" in risk_flags:
        return "editorial_review"
    if risk_level == "high" and final_grade in {"A", "B", "C"}:
        return "editorial_review"
    if broadcast_potential_proxy >= 3 and (evidence_depth < 3 or numbers_strength < 3):
        return "gather_more_evidence"
    if (
        "investment_advice_risk" in risk_flags
        and evidence_depth >= 3
        and final_grade in {"A", "B", "C"}
    ):
        return "gather_more_evidence"
    if final_grade in {"A", "B"} and evidence_depth >= 3 and risk_level in {"low", "medium"}:
        return "send_to_anny"
    if final_grade == "C":
        return "keep_for_later"
    return "reject"


def _weighted_score(value: int, weight: int) -> float:
    return (value / 5) * weight


def score_candidate(candidate: dict[str, Any]) -> dict[str, Any]:
    text = text_blob(
        candidate.get("title"),
        candidate.get("summary"),
        candidate.get("why_interesting"),
        " ".join(candidate.get("risk_flags", [])),
    )
    risk_flags = list(candidate.get("risk_flags", []))
    blocked_reason = None
    if "political_sensitivity" in risk_flags and contains_any(text, DIRECT_POLITICAL_EVAL_TERMS):
        blocked_reason = "direct_president_party_evaluation"
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
    score_components = {
        "broadcast_potential_proxy": round(
            _weighted_score(
                broadcast_potential_proxy,
                SCORING_WEIGHTS["broadcast_potential_proxy"],
            ),
            1,
        ),
        "evidence_depth": round(
            _weighted_score(evidence_depth, SCORING_WEIGHTS["evidence_depth"]),
            1,
        ),
        "numbers_strength": round(
            _weighted_score(numbers_strength, SCORING_WEIGHTS["numbers_strength"]),
            1,
        ),
        "weird_hook": round(_weighted_score(weird_hook, SCORING_WEIGHTS["weird_hook"]), 1),
        "structural_expansion": round(
            _weighted_score(structural_expansion, SCORING_WEIGHTS["structural_expansion"]),
            1,
        ),
        "punchline_potential": round(
            _weighted_score(punchline_potential, SCORING_WEIGHTS["punchline_potential"]),
            1,
        ),
        "timeliness": round(_weighted_score(timeliness, SCORING_WEIGHTS["timeliness"]), 1),
        "risk_penalty": -round(
            _weighted_score(risk_penalty, abs(SCORING_WEIGHTS["risk_penalty"])),
            1,
        ),
    }
    total_score = round(sum(score_components.values()), 1)
    if contains_any(text, {"단발성", "single source"}) or "single_source_dependency" in risk_flags:
        total_score -= 8
    if "corporate_promo_risk" in risk_flags and broadcast_potential_proxy <= 2:
        total_score -= 10
    if blocked_reason:
        total_score = min(total_score, 20)
    total_score = round(max(0, total_score), 1)
    final_grade = _score_band(int(total_score), risk_penalty)
    risk_level = _risk_level(risk_flags, risk_penalty)
    recommended_action = _recommended_action(
        final_grade=final_grade,
        risk_level=risk_level,
        risk_flags=risk_flags,
        evidence_depth=evidence_depth,
        numbers_strength=numbers_strength,
        broadcast_potential_proxy=broadcast_potential_proxy,
        blocked_reason=blocked_reason,
    )
    scored = {
        **candidate,
        "scores": {
            "weights": SCORING_WEIGHTS,
            "components": score_components,
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
        "recommended_action": recommended_action,
        "blocked_reason": blocked_reason,
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
