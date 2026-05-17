"""Rule-based hints for the jibi Daily Digest MVP."""

from __future__ import annotations

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
    "우버이츠",
    "이상",
    "weird",
    "hippo",
    "dinosaur",
    "pawn",
}
STRUCTURAL_TERMS = {
    "시장",
    "규제",
    "산업",
    "공급망",
    "인플레이션",
    "신용",
    "energy",
    "market",
    "regulation",
    "industry",
}
PUNCHLINE_TERMS = {"밈", "농담", "웃", "meme", "joke", "콜라", "반바지"}
NUMBER_TERMS = {"%", "배", "억", "조", "million", "billion", "trillion", "percent"}


def text_blob(*values: object) -> str:
    return " ".join(str(value or "") for value in values).lower()


def contains_any(text: str, terms: Iterable[str]) -> bool:
    lowered = text.lower()
    return any(term.lower() in lowered for term in terms)


def count_any(text: str, terms: Iterable[str]) -> int:
    lowered = text.lower()
    return sum(1 for term in terms if term.lower() in lowered)


def infer_seed_type(title: str, summary: str | None = None, tags: list[str] | None = None) -> str:
    text = text_blob(title, summary, " ".join(tags or []))
    if contains_any(text, {"하마", "공룡", "돼지", "전당포", "hippo", "dinosaur", "pawn"}):
        return "absurd_foreign"
    if contains_any(text, {"반바지", "폭염", "회사", "학교", "생활", "heat", "office"}):
        return "life_change"
    if contains_any(text, {"드론", "미사일", "비용", "cost", "cheap", "expensive"}):
        return "cost_asymmetry"
    if contains_any(text, {"정책", "세제", "코스피", "금리", "policy", "tax", "market"}):
        return "policy_market_shock"
    if contains_any(text, {"정당", "선거", "영국", "election", "party"}):
        return "political_fracture"
    if contains_any(text, {"미중", "중국", "트럼프", "지정학", "china", "geopolitical"}):
        return "geopolitical_prequel"
    if contains_any(text, {"ai", "반도체", "전력", "산업", "technology"}):
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
