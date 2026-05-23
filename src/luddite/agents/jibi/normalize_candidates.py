"""Normalize raw articles into jibi candidate drafts."""

from __future__ import annotations

from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Annotated, Any

import typer
from rich.console import Console

from luddite import paths
from luddite.agents.jibi.heuristics import (
    COST_ASYMMETRY_TERMS,
    INDUSTRY_DISRUPTION_TERMS,
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

SPORT_TERMS = {
    "sport",
    "/sport/",
    "football",
    "golf",
    "tennis",
    "cricket",
    "rugby",
    "축구",
    "골프",
    "야구",
    "농구",
}
ACCIDENT_TERMS = {
    "accident",
    "air show",
    "crash",
    "collide",
    "collision",
    "fighter jet",
    "stabbing",
    "killed",
    "wounded",
    "사고",
    "충돌",
    "흉기",
    "사망",
    "부상",
}
PLACE_LISTING_TERMS = {
    "trail",
    "memorial",
    "museum",
    "restaurant",
    "cafe",
    "castle",
    "park",
    "in ",
    "에 있는",
}
BROADER_STRUCTURE_TERMS = (set(STRUCTURAL_TERMS) - {"ai"}) | set(NUMBER_TERMS) | {
    "labor",
    "media",
    "business",
    "insurance",
    "regulation",
    "safety",
    "tourism",
    "demographic",
    "economy",
    "history",
    "노동",
    "미디어",
    "사업",
    "보험",
    "안전",
    "관광",
    "인구",
    "경제",
    "역사",
}
SINGLE_COMPANY_FINANCING_TERMS = {
    "유상증자",
    "증자",
    "청약",
    "상장",
    "ipo",
    "실적",
    "공매도",
    "stock",
    "shares",
    "financing",
}
MARKET_RATE_STRESS_TERMS = {
    "국채",
    "채권",
    "금리",
    "환율",
    "비트코인",
    "코인",
    "crypto",
    "yield",
    "bond",
    "treasury",
    "rate",
}
POLITICAL_POLICY_TERMS = {
    "trump",
    "immigration",
    "dei",
    "election",
    "party",
    "president",
    "prime minister",
    "cabinet",
    "administration",
}
EDITORIAL_CATEGORY_TYPES = {
    "productive_finance_policy",
    "industrial_policy_rnd",
    "single_company_financing",
    "market_rate_stress",
    "ai_knowledge_institution",
    "infrastructure_project_failure",
    "climate_policy_conflict",
}
FRESHNESS_RECENT_HOURS = 24 * 7


def _evidence_needed(seed_type: str, risk_flags: list[str]) -> list[str]:
    evidence = ["원문 기사 링크", "추가 독립 출처 1개 이상"]
    if seed_type in {
        "policy_market_shock",
        "industry_disruption",
        "cost_asymmetry",
        "productive_finance_policy",
        "industrial_policy_rnd",
        "single_company_financing",
        "market_rate_stress",
        "infrastructure_project_failure",
        "climate_policy_conflict",
    }:
        evidence.append("숫자/통계 또는 공식 자료")
    if "investment_advice_risk" in risk_flags:
        evidence.append("투자 조언으로 읽히지 않도록 반대 근거와 리스크")
    if "medical_claim_risk" in risk_flags:
        evidence.append("의학적 주장 검증용 공식/전문 출처")
    return evidence


def _template_insights(seed_type: str) -> tuple[str, list[str]]:
    templates = {
        "productive_finance_policy": (
            (
                "정책금융이 담보·단기수익 중심에서 생산적 투자로 이동해야 한다는 문제라, "
                "국민성장펀드·AI/반도체 투자·금융권 위험분담 논쟁으로 확장할 수 있음"
            ),
            [
                "담보 중심 금융에서 생산적 투자 금융으로의 전환",
                "국민성장펀드와 AI/반도체 투자 재원",
                "금융권 위험분담과 정책금융의 역할",
            ],
        ),
        "industrial_policy_rnd": (
            (
                "휴머노이드 개발에 정부가 2030년까지 예산을 투입한다는 뉴스라, "
                "AI가 소프트웨어를 넘어 로봇·제조·국가 산업정책으로 번지는 장면을 보여줌"
            ),
            [
                "AI 산업정책이 로봇/제조로 확장되는 흐름",
                "정부 R&D 예산과 민간 양산 사이의 간극",
                "한국형 휴머노이드가 필요한 산업 현장",
            ],
        ),
        "single_company_financing": (
            (
                "단일 기업 유상증자 뉴스로 끝내면 약하지만, 글라스기판 투자와 "
                "AI 반도체 공급망 자금조달이라는 구조로 묶을 수 있는지 확인할 필요가 있음"
            ),
            [
                "글라스기판 투자와 AI 반도체 공급망",
                "신성장 설비투자 자금조달 부담",
                "단일 기업 홍보/투자 조언으로 읽히지 않는 안전한 프레임",
            ],
        ),
        "market_rate_stress": (
            (
                "금리·환율·자산가격 움직임 하나로 끝내면 투자 뉴스에 가깝지만, "
                "AI 투자 비용과 장기금리 압박이 맞물리는지 확인할 가치가 있음"
            ),
            [
                "장기금리 상승과 성장주/AI 투자 할인율",
                "채권시장 스트레스와 기업 자금조달 비용",
                "투자 조언을 피하는 거시 구조 설명",
            ],
        ),
        "ai_knowledge_institution": (
            (
                "AI 즉답이 편리함을 주는 동시에 생각하는 과정을 건너뛰게 만든다는 경고라, "
                "검색·교육·박물관/천문관 같은 지식기관의 역할 변화로 확장 가능"
            ),
            [
                "AI 검색이 사고 과정과 학습 습관을 바꾸는 지점",
                "학교/박물관/천문관 같은 지식기관의 역할 변화",
                "편리함과 지적 근육 약화 사이의 균형",
            ],
        ),
        "infrastructure_project_failure": (
            (
                "HS2 실패는 고속철 하나의 문제가 아니라 대형 인프라 사업이 정치 압력, "
                "비용 폭증, 지역균형 논리와 충돌하는 전형적인 사례로 볼 수 있음"
            ),
            [
                "대형 인프라의 비용 폭증과 정치 압력",
                "고속철/지역균형 논리와 실제 사업성",
                "한국 SOC 사업과 비교할 수 있는 실패 패턴",
            ],
        ),
        "climate_policy_conflict": (
            (
                "산불 대응이 기후 문제가 아니라 이민·DEI·연방 행정 논쟁과 엮이는 장면이라, "
                "재난 정책이 문화전쟁 프레임에 빨려 들어가는 구조를 보여줌"
            ),
            [
                "산불 예방 정책과 연방 행정의 충돌",
                "기후/재난 이슈가 문화전쟁으로 번지는 방식",
                "정치 프레임을 줄이고 제도 설계 중심으로 다루는 방법",
            ],
        ),
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


def _infer_editorial_category(title: str, summary: str, source_id: str | None) -> str | None:
    text = text_blob(title, summary)
    if contains_any(text, {"담보", "단기수익", "생산적", "정책금융", "국민성장펀드"}):
        return "productive_finance_policy"
    if contains_any(text, {"휴머노이드", "ai 로봇", "robotics r&d"}):
        return "industrial_policy_rnd"
    if contains_any(text, SINGLE_COMPANY_FINANCING_TERMS):
        return "single_company_financing"
    if contains_any(text, MARKET_RATE_STRESS_TERMS):
        return "market_rate_stress"
    if contains_any(text, {"royal observatory", "ai answers", "즉답", "human intelligence"}):
        return "ai_knowledge_institution"
    if contains_any(text, {"hs2", "high-speed", "고속철"}):
        return "infrastructure_project_failure"
    if source_id == "npr_rss_candidate" and contains_any(
        text,
        {"wildfire", "forest fire", "burn ban", "산불"},
    ):
        return "climate_policy_conflict"
    return None


def _parse_datetime(value: object) -> datetime | None:
    if not value:
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        parsed = parsedate_to_datetime(text)
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)
    except (TypeError, ValueError):
        pass
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)
    except ValueError:
        return None


def classify_freshness(
    published_at: object,
    collected_at: object,
    *,
    recent_hours: int = FRESHNESS_RECENT_HOURS,
) -> tuple[str, float | None]:
    published = _parse_datetime(published_at)
    collected = _parse_datetime(collected_at) or datetime.now(UTC)
    if not published:
        return "unknown", None
    age_hours = max(0.0, (collected - published).total_seconds() / 3600)
    status = "recent" if age_hours <= recent_hours else "stale"
    return status, round(age_hours, 1)


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


def _rss_quality_hints(
    *,
    title: str,
    summary: str,
    source_id: str | None,
    source_url: str,
    seed_type: str,
    risk_flags: list[str],
) -> tuple[str, list[str], list[str]]:
    text = text_blob(title, summary, source_url)
    quality_flags: list[str] = []
    if not summary.strip():
        quality_flags.append("empty_summary")
    has_structure = contains_any(text, BROADER_STRUCTURE_TERMS)
    if source_id == "bbc_rss_candidate" and contains_any(text, SPORT_TERMS) and not has_structure:
        quality_flags.append("sports_only")
    if contains_any(text, ACCIDENT_TERMS) and not has_structure:
        quality_flags.append("accident_single_event")
    if source_id == "atlas_obscura" and contains_any(text, PLACE_LISTING_TERMS):
        quality_flags.append("pure_place_listing")
    if contains_any(text, POLITICAL_POLICY_TERMS):
        if "political_sensitivity" not in risk_flags:
            risk_flags.append("political_sensitivity")
    if source_id == "npr_rss_candidate" and contains_any(text, POLITICAL_POLICY_TERMS):
        quality_flags.append("live_politics_or_statement")
    if source_id in {"infomax_manual", "hankyung_manual"} and (
        "investment_advice_risk" in risk_flags
        or contains_any(text, SINGLE_COMPANY_FINANCING_TERMS | MARKET_RATE_STRESS_TERMS)
    ):
        quality_flags.append("single_stock_or_asset_frame")
        if "investment_advice_risk" not in risk_flags:
            risk_flags.append("investment_advice_risk")
    if source_id in {"infomax_manual", "hankyung_manual"} and contains_any(
        text,
        SINGLE_COMPANY_FINANCING_TERMS,
    ):
        quality_flags.append("single_company_frame")
        if "corporate_promo_risk" not in risk_flags:
            risk_flags.append("corporate_promo_risk")
    if source_id == "hankyung_manual" and not summary.strip():
        quality_flags.append("empty_summary_domestic_business")
    return (
        "low" if quality_flags else "medium",
        quality_flags,
        risk_flags,
    )


def normalize_article(article: dict[str, Any]) -> dict[str, Any]:
    title = article["title"]
    source_url_canonical = canonicalize_url(article["url"])
    summary = article.get("raw_summary") or ""
    tags = article.get("tags", [])
    seed_type = infer_seed_type(title, summary, tags)
    risk_flags = infer_risk_flags(title, summary, tags)
    registry = source_by_id()
    source = registry.get(article.get("source_id") or "")
    source_type = source.type if source else article.get("collector", "manual")
    if source and source.subscription and "subscription_source_only" not in risk_flags:
        risk_flags.append("subscription_source_only")
    text = text_blob(title, summary, " ".join(tags))
    weird_hook = contains_any(text, WEIRD_TERMS)
    structural = contains_any(text, STRUCTURAL_TERMS)
    numbers = contains_any(text, NUMBER_TERMS) or any(char.isdigit() for char in text)
    if seed_type == "industry_disruption" and not contains_any(text, INDUSTRY_DISRUPTION_TERMS):
        seed_type = "other"
    if seed_type == "cost_asymmetry" and not contains_any(text, COST_ASYMMETRY_TERMS):
        seed_type = "other"
    editorial_category = _infer_editorial_category(title, summary, article.get("source_id"))
    if editorial_category:
        seed_type = editorial_category
    quality_hint, quality_flags, risk_flags = _rss_quality_hints(
        title=title,
        summary=summary,
        source_id=article.get("source_id"),
        source_url=source_url_canonical,
        seed_type=seed_type,
        risk_flags=risk_flags,
    )
    freshness_status, age_hours = classify_freshness(
        article.get("published_at"),
        article.get("collected_at"),
    )
    if (
        freshness_status == "stale"
        and source_type != "manual"
        and seed_type not in EDITORIAL_CATEGORY_TYPES
        and "stale_item" not in quality_flags
    ):
        quality_flags.append("stale_item")
    specific_insights = _specific_insights(title, summary)
    template_rationale, possible_expansions = specific_insights or _template_insights(seed_type)
    if specific_insights is None and seed_type not in EDITORIAL_CATEGORY_TYPES:
        if seed_type == "industry_disruption":
            template_rationale = (
                f"{title} 이슈를 단일 기사로 소비하지 않고 공급망, 인프라, 규제, "
                "산업 전환 중 어느 축으로 확장 가능한지 확인할 필요가 있음"
            )
        else:
            template_rationale = (
                f"{title}에서 출발해 사건 자체보다 배경, 이해관계자, 한국 시청자에게 "
                "닿는 구조적 연결고리가 있는지 추가 확인할 필요가 있음"
            )
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
        "source_type": source_type,
        "published_at": article.get("published_at"),
        "collected_at": article["collected_at"],
        "freshness_status": freshness_status,
        "age_hours": age_hours,
        "first_seen_at": article.get("first_seen_at") or article["collected_at"],
        "last_seen_at": article.get("last_seen_at") or article["collected_at"],
        "source_count": int(article.get("source_count") or 1),
        "mode": article.get("mode") or "normal",
        "seed_type": seed_type,
        "editorial_category": editorial_category or seed_type,
        "summary": summary,
        "why_interesting": why_interesting,
        "score_reason": score_reason,
        "possible_expansions": possible_expansions,
        "korea_bridge": None,
        "punchline_candidate": None,
        "evidence_needed": _evidence_needed(seed_type, risk_flags),
        "risk_flags": risk_flags,
        "subscription_source_only": "subscription_source_only" in risk_flags,
        "quality_flags": quality_flags,
        "evidence_depth_hint": (
            "low" if quality_hint == "low" else "medium" if structural or numbers else "low"
        ),
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
