"""Rule-based hints for the jibi Daily Digest MVP."""

from __future__ import annotations

import re
from collections.abc import Iterable

POLITICAL_TERMS = {
    "대통령",
    "정당",
    "국회",
    "선거",
    "탄핵",
    "president",
    "election",
    "party",
}
INVESTMENT_TERMS = {"주식", "증시", "상장", "코스피", "채권", "금리", "stock", "ipo", "bond"}
MEDICAL_TERMS = {"치료", "백신", "의학", "medical", "vaccine", "drug", "therapy"}
CRIME_TERMS = {"마약", "범죄", "교도소", "drug", "crime", "prison", "cocaine"}
PROMO_TERMS = {"출시", "신제품", "프로모션", "launches", "unveils"}
LIVE_TERMS = {"속보", "긴급", "breaking", "live"}
COPYRIGHT_TERMS = {"사진", "이미지", "짤", "meme", "photo"}
WEIRD_TERMS = {
    "하마",
    "공룡",
    "돼지",
    "전당포",
    "드론",
    "폭염",
    "반바지",
    "우버이츠",
    "이상",
    "비용 역전",
    "weird",
    "hippo",
    "dinosaur",
    "pawn",
    "drone",
    "heatwave",
}
STRUCTURAL_TERMS = {
    "ai",
    "시장",
    "규제",
    "산업",
    "라벨",
    "브랜드",
    "진정성",
    "창작자",
    "비용",
    "전력",
    "변압기",
    "데이터센터",
    "공급망",
    "인플레이션",
    "신용",
    "energy",
    "market",
    "regulation",
    "industry",
    "cost",
    "grid",
    "brand",
    "label",
}
PUNCHLINE_TERMS = {"밈", "농담", "웃", "meme", "joke", "콜라", "반바지", "레이저"}
NUMBER_TERMS = {"%", "배", "억", "조", "million", "billion", "trillion", "percent"}
COST_ASYMMETRY_TERMS = {
    "cheap",
    "expensive",
    "low-cost",
    "high-cost",
    "cost per kill",
    "interceptor",
    "missile",
    "drone",
    "budget exhaustion",
    "비용",
    "비용 역전",
    "드론",
    "미사일",
    "요격",
    "저비용",
    "고비용",
}
INDUSTRY_DISRUPTION_TERMS = {
    "supply chain",
    "energy",
    "power grid",
    "transformer",
    "data center",
    "ai infrastructure",
    "semiconductor",
    "battery",
    "logistics",
    "production bottleneck",
    "market structure",
    "regulation",
    "공급망",
    "전력",
    "전력망",
    "변압기",
    "데이터센터",
    "ai 인프라",
    "반도체",
    "배터리",
    "물류",
    "생산 병목",
    "시장 구조",
    "규제",
    "산업 전반",
}


def text_blob(*values: object) -> str:
    return " ".join(str(value or "") for value in values).lower()


def contains_any(text: str, terms: Iterable[str]) -> bool:
    lowered = text.lower()
    return any(_term_in_text(lowered, term) for term in terms)


def count_any(text: str, terms: Iterable[str]) -> int:
    lowered = text.lower()
    return sum(1 for term in terms if _term_in_text(lowered, term))


def _term_in_text(lowered_text: str, term: str) -> bool:
    lowered_term = term.lower()
    if lowered_term.isascii() and lowered_term.isalnum():
        return re.search(rf"\b{re.escape(lowered_term)}\b", lowered_text) is not None
    return lowered_term in lowered_text


def infer_seed_type(title: str, summary: str | None = None, tags: list[str] | None = None) -> str:
    text = text_blob(title, summary, " ".join(tags or []))
    if contains_any(text, {"하마", "공룡", "돼지", "전당포", "hippo", "dinosaur", "pawn"}):
        return "absurd_foreign"
    if contains_any(text, {"반바지", "폭염", "회사", "학교", "생활", "heat", "office"}):
        return "life_change"
    if contains_any(text, COST_ASYMMETRY_TERMS) and (
        contains_any(text, {"드론", "drone", "공격", "attack"})
        and contains_any(text, {"미사일", "missile", "요격", "interceptor", "defense"})
        or (
            contains_any(text, {"cheap", "low-cost", "저비용", "값싼"})
            and contains_any(text, {"expensive", "high-cost", "고비용", "비싼"})
        )
    ):
        return "cost_asymmetry"
    if contains_any(text, {"정책", "세제", "코스피", "금리", "policy", "tax", "market"}):
        return "policy_market_shock"
    if contains_any(text, {"정당", "선거", "영국", "election", "party"}):
        return "political_fracture"
    if contains_any(text, {"미중", "중국", "트럼프", "지정학", "china", "geopolitical"}):
        return "geopolitical_prequel"
    if contains_any(text, INDUSTRY_DISRUPTION_TERMS):
        return "industry_disruption"
    if contains_any(text, {"치료", "레이저", "드론", "우주", "science", "medical"}):
        return "science_technology"
    if contains_any(text, {"임금", "노동", "교사", "학교", "labor", "teacher"}):
        return "labor_society"
    return "other"


def infer_risk_flags(
    title: str,
    summary: str | None = None,
    tags: list[str] | None = None,
) -> list[str]:
    text = text_blob(title, summary, " ".join(tags or []))
    flags: list[str] = []
    if contains_any(text, POLITICAL_TERMS):
        flags.append("political_sensitivity")
    if contains_any(text, INVESTMENT_TERMS):
        flags.append("investment_advice_risk")
    if contains_any(text, MEDICAL_TERMS):
        flags.append("medical_claim_risk")
    if contains_any(text, CRIME_TERMS):
        flags.append("crime_or_drug_sensitivity")
    if contains_any(text, PROMO_TERMS):
        flags.append("corporate_promo_risk")
    if contains_any(text, LIVE_TERMS):
        flags.append("live_news_volatility")
    if contains_any(text, COPYRIGHT_TERMS):
        flags.append("copyright_image_risk")
    return flags
