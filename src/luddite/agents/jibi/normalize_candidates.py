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
from luddite.utils.urls import canonicalize_url

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


def _template_insights(seed_type: str) -> tuple[str, list[str]]:
    templates = {
        "cost_asymmetry": (
            (
                "싼 공격수단과 비싼 방어수단의 비용 역전이 핵심이라 예산 고갈, "
                "전쟁 경제학, 방산/기술 패러다임 변화로 확장 가능"
            ),
            [
                "우크라이나/중동 전장에서 드론이 비용 구조를 바꾼 사례",
                "싼 공격 수단을 비싼 미사일로 막는 방어자 딜레마",
                "레이저/전자전/그물총 같은 저비용 대응책 경쟁",
            ],
        ),
        "life_change": (
            (
                "날씨/생활 체감에서 출발해 제도, 복장, 직장문화 변화와 "
                "한국 회사식 회수로 이어질 수 있음"
            ),
            [
                "폭염과 계절 감각 변화",
                "에너지 가격과 오피스 복장 변화",
                "한국 기업 쿨비즈/반바지 문화",
            ],
        ),
        "absurd_foreign": (
            (
                "이상한 해외 뉴스 hook이 강하고 배경 설명을 거쳐 시장/사회 구조로 "
                "확장 가능하지만 드립과 리스크가 동시에 존재"
            ),
            [
                "이상한 해외 뉴스가 나온 배경",
                "현지 시장/사회 구조로 확장되는 지점",
                "한국 시청자가 이해할 수 있는 비유와 회수",
            ],
        ),
        "industry_disruption": (
            (
                "기업 단일 이슈보다 공급망/전력/인프라 병목 같은 산업 구조 변화로 "
                "풀 수 있고 숫자/그래프/공식자료가 필요"
            ),
            [
                "공급망/전력/인프라 병목",
                "기업 단일 이슈가 아니라 산업 구조 변화로 확장",
                "숫자/그래프/공식자료로 확인할 포인트",
            ],
        ),
        "political_fracture": (
            (
                "단순 정치 뉴스가 아니라 제도/지역/경제 균열로 풀어야 하며 "
                "직접 정당/대통령 평가는 피해야 함"
            ),
            [
                "정당 지지율보다 제도/지역 균열 중심으로 재구성",
                "경제 불만과 시장/정책 영향",
                "직접 정치 평가를 피하는 안전한 설명 프레임",
            ],
        ),
    }
    return templates.get(
        seed_type,
        (
            "수동 후보로 들어온 소재이며 hook, 근거, 한국 연결 가능성을 추가로 확인해야 함",
            ["배경 설명", "구조적 확장", "한국 시청자 연결 지점"],
        ),
    )


def _specific_insights(title: str, summary: str) -> tuple[str, list[str]] | None:
    text = text_blob(title, summary)
    if ("드론" in text or "drone" in text) and (
        "미사일" in text or "비용" in text or "cost" in text
    ):
        return (
            (
                "값싼 드론 하나를 막기 위해 수백만 달러짜리 미사일을 태우는 구조라, "
                "전쟁이 무기 성능보다 비용 교환비 싸움으로 바뀌는 장면을 보여줌"
            ),
            [
                "우크라이나/중동 전장에서 드론이 비용 구조를 바꾼 사례",
                "싼 공격 수단을 비싼 미사일로 막는 방어자 딜레마",
                "레이저/전자전/그물총 같은 저비용 대응책 경쟁",
            ],
        )
    if any(term in text for term in ["반바지", "폭염", "heatwave", "shorts"]):
        return (
            (
                "5월 폭염이 단순 날씨 뉴스가 아니라 회사 복장 규정, 전력 수요, "
                "에어컨 비용, 쿨비즈 문화로 이어질 수 있음"
            ),
            [
                "5월 폭염과 일본 40도 용어",
                "에너지 가격과 오피스 복장 변화",
                "한국 기업 쿨비즈/반바지 문화",
            ],
        )
    if any(term in text for term in ["공룡", "티라노", "t-rex", "dinosaur"]):
        return (
            (
                "공룡 취향이라는 가벼운 질문에서 어른들의 낭만, 과학 대중문화, "
                "세대별 캐릭터 소비 방식으로 자연스럽게 넓어질 수 있음"
            ),
            [
                "T-Rex가 공룡 대표 이미지가 된 문화적 배경",
                "어른이 되며 사라지는 취향/낭만 설문",
                "영화/완구/박물관이 만든 공룡 인기 지도",
            ],
        )
    if ("영국" in text or "britain" in text or "uk" in text) and (
        "개혁당" in text or "양당" in text or "reform party" in text
    ):
        return (
            (
                "영국 양당제 균열에서 시작해 지역 격차, 포퓰리즘, 경제 불만, "
                "채권시장/정책 리스크, 노동자 계층 이동까지 이어지는 해외 정치 구조 이슈"
            ),
            [
                "양당제 균열과 지역 격차",
                "포퓰리즘과 경제 불만",
                "채권시장/정책 리스크",
                "노동자 계층 이동과 이민 이슈",
            ],
        )
    if "f88" in text or "전당포" in text:
        return (
            (
                "베트남 전당포 F88의 상장 도전에서 시작해 한국의 전당포 이미지, "
                "베트남 금융 접근성, 오토바이 담보대출, 제도권화/추심 리스크로 확장 가능"
            ),
            [
                "베트남 전당포 F88의 상장 도전",
                "한국의 전당포 이미지와 급전 수요 변화",
                "베트남 금융 접근성과 오토바이 담보대출",
                "제도권화와 추심 리스크",
            ],
        )
    if "하마" in text or "hippo" in text:
        return (
            (
                "파블로 에스코바르의 코카인 하마라는 강한 hook에서 처리 난점, "
                "안락사 논란, 암바니/릴라이언스의 인도 소비재 이야기로 넘어갈 수 있음"
            ),
            [
                "파블로 에스코바르의 코카인 하마",
                "콜롬비아의 처리 난점과 안락사 논란",
                "암바니 가문의 동물센터 제안",
                "릴라이언스/캄파콜라/인도 소비재 시장으로 확장",
            ],
        )
    if "ai 미사용" in text or "ai 슬롭" in text:
        return (
            (
                "AI slop 피로감에서 출발해 진정성 마케팅, AI 표기 규제, "
                "창작자 반발, 브랜드 신뢰 경쟁으로 확장 가능"
            ),
            [
                "AI slop 범람과 소비자 피로감",
                "진정성 마케팅과 AI 미사용 라벨",
                "AI 표기 규제와 창작자 반발",
            ],
        )
    return None


def normalize_article(article: dict[str, Any]) -> dict[str, Any]:
    title = article["title"]
    source_url_canonical = canonicalize_url(article["url"])
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
    specific_insights = _specific_insights(title, summary)
    template_rationale, possible_expansions = specific_insights or _template_insights(seed_type)
    score_reason: list[str] = []
    if weird_hook:
        score_reason.append("제목에서 바로 엥? 하는 hook이 생김")
    if structural:
        score_reason.append("시장/규제/산업 구조로 확장 가능")
    if numbers:
        score_reason.append("숫자나 통계로 증명할 여지가 있음")
    why_interesting = template_rationale or "수동 후보로 들어온 방송 소재"
    return {
        "candidate_id": f"jibi_{article['article_id'].removeprefix('article_')}",
        "article_id": article["article_id"],
        "title": title,
        "seed_url": source_url_canonical,
        "source_url_canonical": source_url_canonical,
        "duplicate_key": article.get("duplicate_key") or source_url_canonical,
        "source": article["source"],
        "source_id": article.get("source_id"),
        "source_type": source.type if source else article.get("collector", "manual"),
        "published_at": article.get("published_at"),
        "collected_at": article["collected_at"],
        "first_seen_at": article.get("first_seen_at") or article["collected_at"],
        "last_seen_at": article.get("last_seen_at") or article["collected_at"],
        "source_count": int(article.get("source_count") or 1),
        "mode": article.get("mode") or "normal",
        "seed_type": seed_type,
        "summary": summary or title,
        "why_interesting": why_interesting,
        "score_reason": score_reason,
        "possible_expansions": possible_expansions,
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
