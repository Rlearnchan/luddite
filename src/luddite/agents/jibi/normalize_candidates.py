"""Normalize raw articles into jibi candidate drafts."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated, Any

import typer
from rich.console import Console

from luddite import paths
from luddite.agents.jibi.heuristics import (
    NUMBER_TERMS,
    STRUCTURAL_TERMS,
    WEIRD_TERMS,
    contains_any,
    infer_risk_flags,
    infer_seed_type,
    text_blob,
)
from luddite.collectors.source_registry import source_by_id
from luddite.utils.jsonl import read_jsonl, write_jsonl

app = typer.Typer(no_args_is_help=False)
console = Console()


def _evidence_needed(seed_type: str, risk_flags: list[str]) -> list[str]:
    evidence = ["원문 기사 링크", "추가 독립 출처 1개 이상"]
    if seed_type in {"policy_market_shock", "industry_disruption", "cost_asymmetry"}:
        evidence.append("숫자/통계 또는 공식 자료")
    if "investment_advice_risk" in risk_flags:
        evidence.append("투자 조언으로 읽히지 않도록 반대 근거와 리스크")
    if "medical_claim_risk" in risk_flags:
        evidence.append("의학적 주장 검증용 공식/전문 출처")
    return evidence


def normalize_article(article: dict[str, Any]) -> dict[str, Any]:
    title = article["title"]
    summary = article.get("raw_summary") or ""
    tags = article.get("tags", [])
    seed_type = infer_seed_type(title, summary, tags)
    risk_flags = infer_risk_flags(title, summary, tags)
    registry = source_by_id()
    source = registry.get(article.get("source_id") or "")
    if source and source.subscription and "subscription_source_only" not in risk_flags:
        risk_flags.append("subscription_source_only")
    text = text_blob(title, summary, " ".join(tags))
    weird_hook = contains_any(text, WEIRD_TERMS)
    structural = contains_any(text, STRUCTURAL_TERMS)
    numbers = contains_any(text, NUMBER_TERMS) or any(char.isdigit() for char in text)
    why_bits = []
    if weird_hook:
        why_bits.append("제목에서 바로 엥? 하는 hook이 생김")
    if structural:
        why_bits.append("시장/규제/산업 구조로 확장 가능")
    if numbers:
        why_bits.append("숫자나 통계로 증명할 여지가 있음")
    why_interesting = "; ".join(why_bits) or "수동 후보로 들어온 방송 소재"
    return {
        "candidate_id": f"jibi_{article['article_id'].removeprefix('article_')}",
        "article_id": article["article_id"],
        "title": title,
        "seed_url": article["url"],
        "source": article["source"],
        "source_id": article.get("source_id"),
        "published_at": article.get("published_at"),
        "collected_at": article["collected_at"],
        "seed_type": seed_type,
        "summary": summary or title,
        "why_interesting": why_interesting,
        "possible_expansions": [],
        "korea_bridge": None,
        "punchline_candidate": None,
        "evidence_needed": _evidence_needed(seed_type, risk_flags),
        "risk_flags": risk_flags,
        "subscription_source_only": "subscription_source_only" in risk_flags,
        "evidence_depth_hint": "medium" if structural or numbers else "low",
        "numbers_strength_hint": "medium" if numbers else "low",
        "title_hook_hint": "high" if weird_hook else "medium",
        "scores": {},
        "status": "candidate",
    }


def normalize_candidates(
    input_path: Path = paths.RAW_ARTICLES_JSONL,
    output_path: Path = paths.JIBI_CANDIDATES_JSONL,
) -> list[dict[str, Any]]:
    articles = read_jsonl(input_path) if input_path.exists() else []
    candidates = [normalize_article(article) for article in articles]
    write_jsonl(output_path, candidates)
    return candidates


@app.callback(invoke_without_command=True)
def main(
    input_path: Annotated[
        Path,
        typer.Option("--input", help="Raw article JSONL input path."),
    ] = paths.RAW_ARTICLES_JSONL,
    output: Annotated[
        Path,
        typer.Option("--output", help="Jibi candidate JSONL output path."),
    ] = paths.JIBI_CANDIDATES_JSONL,
) -> None:
    candidates = normalize_candidates(input_path=input_path, output_path=output)
    console.print(f"[green]Wrote {len(candidates)} jibi candidates to {output}.[/green]")


if __name__ == "__main__":
    app()
