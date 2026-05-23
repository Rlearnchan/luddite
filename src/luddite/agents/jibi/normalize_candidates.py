"""Normalize raw articles into jibi candidate drafts."""

from __future__ import annotations

import re
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
    "상장 추진",
    "상장사",
    "기업공개",
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
    "macro_research_note",
    "policy_research_note",
    "academic_explainer",
    "policy_release_seed",
    "public_ai_governance",
    "public_ai_enforcement",
    "workplace_ai_transition",
    "healthcare_operations_ai",
    "platform_labor_market",
    "industrial_labor_conflict",
}
FRESHNESS_RECENT_HOURS = 24 * 7
LOW_FREQUENCY_RESEARCH_POLICY = "low_frequency_research"
SOURCE_ROLE_RESEARCH_NOTE = "research_note"
SOURCE_ROLE_POLICY_RELEASE = "policy_release"
SOURCE_ROLE_ACADEMIC_EXPLAINER = "academic_explainer"
SOURCE_ROLE_PUBLIC_WIRE = "public_wire"
SOURCE_ROLE_MARKET_WIRE = "market_wire"
SOURCE_ROLE_SECTION_NEWS = "section_news"
GENERIC_SPECIFICITY_WHY_PATTERNS = {
    "수동 후보로 들어온 소재",
    "공급망, 인프라, 규제, 산업 전환 중 어느 축",
    "사건 자체보다 배경",
}
MECHANISM_TERMS = {
    "cost",
    "budget",
    "supply chain",
    "regulation",
    "policy",
    "market",
    "infrastructure",
    "insurance",
    "funding",
    "fund",
    "구조",
    "비용",
    "예산",
    "공급망",
    "규제",
    "정책",
    "시장",
    "인프라",
    "보험",
    "투자",
    "자금",
}
POLICY_TERMS = {
    "policy",
    "regulation",
    "rules",
    "law",
    "government",
    "public",
    "정책",
    "규제",
    "제도",
    "법",
    "정부",
    "공공",
    "과제",
}
ACADEMIC_EXPLAINER_TERMS = {
    "research",
    "study",
    "science",
    "scientists",
    "climate",
    "environment",
    "university",
    "analysis",
    "explains",
    "연구",
    "분석",
    "과학",
    "기후",
    "환경",
    "대학",
}
FINANCING_DOMINANT_TERMS = SINGLE_COMPANY_FINANCING_TERMS | {
    "funding",
    "valuation",
    "investor",
    "investors",
    "public listing",
    "go public",
    "ipo",
    "자금조달",
    "기업공개",
    "투자자",
}
TENSION_TERMS = {
    "vs",
    "versus",
    "battle",
    "conflict",
    "clash",
    "risk",
    "pressure",
    "ban",
    "backlash",
    "논쟁",
    "충돌",
    "갈등",
    "리스크",
    "압박",
    "반발",
    "금지",
    "딜레마",
}
KOREA_BRIDGE_TERMS = {
    "korea",
    "korean",
    "한국",
    "국내",
    "우리나라",
}
VISUAL_HOOK_TERMS = WEIRD_TERMS | {
    "chart",
    "map",
    "diagram",
    "before and after",
    "차트",
    "지도",
    "도표",
    "그래프",
    "비교",
    "전후",
}
POLICY_RELEASE_ANNOUNCEMENT_TERMS = {
    "회의",
    "간담회",
    "논의",
    "개최",
    "참석",
    "업무협약",
    "협약",
    "보고회",
    "설명회",
    "공모",
    "모집",
    "안내",
    "발표",
}
POLICY_RELEASE_MEETING_TERMS = {
    "회의",
    "장관회의",
    "담당관회의",
    "공관 담당관회의",
    "간담회",
    "논의",
    "개최",
    "참석",
    "협력방안",
    "활성화 방안",
    "업무협약",
    "협약",
}
POLICY_RELEASE_PROCEDURAL_NUMBER_TERMS = {
    "제",
    "차",
    "회의",
    "보고서",
    "현황",
    "기준",
    "신청",
    "지급",
    "접수",
    "공모",
    "모집",
}
POLICY_RELEASE_MATERIAL_NUMBER_TERMS = {
    "예산",
    "투자",
    "지원",
    "보조금",
    "가구",
    "가계",
    "청년",
    "노인",
    "근로자",
    "소상공인",
    "중소기업",
    "물가",
    "요금",
    "임금",
    "일자리",
    "budget",
    "investment",
    "household",
    "consumer",
    "jobs",
    "wage",
}
POLICY_RELEASE_NON_NUMBER_SIGNALS = {
    "odd_hook",
    "life_impact",
    "regulatory_conflict",
    "industry_mechanism",
    "visual_proof_object",
}
POLICY_RELEASE_MATERIAL_NUMBER_RE = re.compile(
    r"\d[\d,.]*\s*(조|억|만|명|가구|건|개|원|달러|%|퍼센트|배|톤|ha|㎢|km|mwh|gw|mw)",
    re.IGNORECASE,
)
POLICY_RELEASE_DATE_RE = re.compile(
    r"(20\d{2}\s*년|\d{1,2}\s*월\s*\d{1,2}\s*일|"
    r"\d{4}[.-]\d{1,2}[.-]\d{1,2}|제\s*\d+\s*차)"
)
KOREAN_NAMED_ACTOR_TERMS = {
    "정부",
    "은행",
    "기업",
    "회사",
    "대통령",
    "총리",
    "구글",
    "스타벅스",
    "삼성",
    "skc",
    "f88",
}
ENGLISH_NAMED_ACTOR_TERMS = {
    "amazon",
    "bbc",
    "google",
    "microsoft",
    "npr",
    "openai",
    "starbucks",
    "tesla",
    "trump",
}


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
        "public_ai_governance",
        "public_ai_enforcement",
        "workplace_ai_transition",
        "healthcare_operations_ai",
        "platform_labor_market",
        "industrial_labor_conflict",
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
        "macro_research_note": (
            (
                "한국은행 이슈노트형 연구자료라 단발 뉴스보다 숫자, 작동 메커니즘, "
                "한국 경제/생활과 이어지는 정책 함의를 함께 볼 수 있음"
            ),
            [
                "보고서가 제시한 핵심 숫자와 추세",
                "그 숫자가 생긴 경제/산업 메커니즘",
                "한국 정책·가계·기업 의사결정으로 이어지는 지점",
            ],
        ),
        "policy_research_note": (
            (
                "연구노트가 현상 진단에서 정책 과제까지 이어지는 구조라, "
                "숫자 근거와 제도 설계를 한 장의 설명 카드로 만들 수 있음"
            ),
            [
                "연구노트의 문제 진단과 핵심 통계",
                "제도/정책 변화가 필요한 메커니즘",
                "한국 시청자가 체감할 수 있는 비용·기회·리스크",
            ],
        ),
        "academic_explainer": (
            (
                "학술/해설형 기사라 단일 기업 뉴스로 소비하기보다 과학, 사회, 정책, "
                "환경 리스크가 왜 생겼는지를 구조적으로 설명하는 seed로 볼 수 있음"
            ),
            [
                "기사의 설명 대상이 되는 과학/사회 메커니즘",
                "정책·시장·생활 리스크로 이어지는 연결고리",
                "한국 사례와 비교할 수 있는 증거 카드",
            ],
        ),
        "policy_release_seed": (
            (
                "공식 보도자료지만 숫자, 생활 영향, 산업 메커니즘, 규제 갈등 중 "
                "하나 이상이 있어 evidence를 넘어 seed 후보로 검토할 가치가 있음"
            ),
            [
                "보도자료의 핵심 수치 또는 정책 변화",
                "산업/가계/시장에 실제로 닿는 메커니즘",
                "공식자료를 시각화할 수 있는 표·지도·전후 비교",
            ],
        ),
        "policy_release_evidence": (
            (
                "공식 보도자료로 근거 가치는 있지만 아직 방송 seed로 커질 숫자, "
                "생활 영향, 갈등 구조가 약해 evidence/manual 후보로 두는 편이 안전함"
            ),
            [
                "공식 근거로 붙일 수 있는 문장",
                "추가 기사나 통계가 필요한 지점",
                "seed로 승격하려면 필요한 생활/산업/숫자 hook",
            ],
        ),
        "public_ai_governance": (
            (
                "공공기관의 AI 활용이 효율화와 책임 문제를 동시에 보여주는 사례라, "
                "AI 도입 기준, 감사/보고서, 사람의 판단 영역을 함께 설명할 수 있음"
            ),
            [
                "공공기관 AI 활용 실태와 부적절 사용 사례",
                "AI가 행정 효율과 책임 소재를 동시에 바꾸는 지점",
                "교육·감사·가이드라인이 필요한 이유",
            ],
        ),
        "public_ai_enforcement": (
            (
                "AI/드론이 실제 단속·검거·안전 현장에 들어온 사례라, 기술이 공공안전의 "
                "방식을 어떻게 바꾸는지 보여주는 생활형 공공기술 소재"
            ),
            [
                "AI/드론이 치안·단속 현장에 들어온 장면",
                "공공안전 효율과 감시/오판 리스크",
                "한국 지자체·경찰의 기술 도입 기준",
            ],
        ),
        "workplace_ai_transition": (
            (
                "AI 도입이 일자리와 노사관계의 의제가 되는 장면이라, 기술 변화가 "
                "생산성뿐 아니라 협상·교육·직무 재설계를 요구한다는 구조로 확장 가능"
            ),
            [
                "AI 도입과 직무 재설계",
                "노사 협상에서 AI가 새 의제가 되는 이유",
                "생산성 향상과 일자리 불안의 균형",
            ],
        ),
        "healthcare_operations_ai": (
            (
                "의학적 치료 주장보다 병원 운영·연락·배정 같은 workflow를 AI가 바꾸는 "
                "사례라, 의료 리스크를 조심하면서도 현장 운영 혁신으로 설명 가능"
            ),
            [
                "병원 연락·배정·예약 workflow 자동화",
                "의료 인력 부족과 운영 병목",
                "의학적 효능 주장을 피하는 운영 개선 프레임",
            ],
        ),
        "platform_labor_market": (
            (
                "플랫폼의 수수료·배달비·상인/노동자 부담 논쟁이라, 앱 편의성 뒤의 "
                "비용 배분과 노동시장 구조를 보여줄 수 있음"
            ),
            [
                "플랫폼 무료/할인 경쟁의 비용 전가 구조",
                "가맹점·노동자·소비자 사이의 부담 배분",
                "한국 배달/플랫폼 시장의 수수료 논쟁",
            ],
        ),
        "industrial_labor_conflict": (
            (
                "단일 기업 노사 뉴스로 끝내면 약하지만, 산업 전환·성과급·직무 변화와 "
                "맞물리면 한국 제조업/테크 기업의 일터 구조를 설명하는 소재가 될 수 있음"
            ),
            [
                "성과급·임금·직무를 둘러싼 기업 내부 갈등",
                "산업 전환기 노동시장과 조직 내부 세대/직군 차이",
                "단일 기업 투자 조언으로 보이지 않게 산업 구조로 확장",
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


def _source_role_class(source: Any, source_id: str | None) -> str:
    if source and source.role_class:
        return source.role_class
    if source and source.freshness_policy == LOW_FREQUENCY_RESEARCH_POLICY:
        return SOURCE_ROLE_RESEARCH_NOTE
    if source_id == "korea_policy_briefing" or (
        source and source.category_hint == "policy_release"
    ):
        return SOURCE_ROLE_POLICY_RELEASE
    if source_id == "the_conversation":
        return SOURCE_ROLE_ACADEMIC_EXPLAINER
    if source_id == "yonhap_market":
        return SOURCE_ROLE_MARKET_WIRE
    if source_id and source_id.startswith("yonhap_"):
        return SOURCE_ROLE_PUBLIC_WIRE
    if source_id == "infomax_manual":
        return SOURCE_ROLE_MARKET_WIRE
    if source_id and source_id.startswith("guardian_"):
        return SOURCE_ROLE_SECTION_NEWS
    return "unknown"


def _research_note_seed_type(text: str) -> str:
    if contains_any(text, POLICY_TERMS):
        return "policy_research_note"
    return "macro_research_note"


def _has_research_note_signals(text: str) -> bool:
    return contains_any(text, MECHANISM_TERMS | POLICY_TERMS) or contains_any(
        text,
        NUMBER_TERMS,
    ) or any(char.isdigit() for char in text)


def _academic_explainer_terms_dominate(text: str) -> bool:
    explainer_hits = sum(
        int(contains_any(text, {term}))
        for term in ACADEMIC_EXPLAINER_TERMS | POLICY_TERMS | {"space", "rocket", "starship"}
    )
    finance_hits = sum(int(contains_any(text, {term})) for term in FINANCING_DOMINANT_TERMS)
    return explainer_hits >= max(finance_hits, 1)


def _policy_release_has_material_number(text: str) -> bool:
    return bool(POLICY_RELEASE_MATERIAL_NUMBER_RE.search(text)) or (
        contains_any(text, POLICY_RELEASE_MATERIAL_NUMBER_TERMS)
        and (contains_any(text, NUMBER_TERMS) or any(char.isdigit() for char in text))
    )


def _policy_release_raw_seed_signals(text: str) -> list[str]:
    signals: list[str] = []
    if contains_any(text, WEIRD_TERMS | {"염소", "goat"}):
        signals.append("odd_hook")
    if _policy_release_has_material_number(text):
        signals.append("material_number")
    if contains_any(
        text,
        {
            "생활",
            "가계",
            "소비자",
            "요금",
            "임금",
            "일자리",
            "주거",
            "부동산",
            "식품",
            "물가",
            "household",
            "consumer",
            "jobs",
            "housing",
            "prices",
        },
    ):
        signals.append("life_impact")
    if contains_any(text, TENSION_TERMS | {"규제", "제재", "법안", "regulation"}):
        signals.append("regulatory_conflict")
    if contains_any(
        text,
        {
            "산업 구조",
            "산업 전환",
            "산업 육성",
            "공급망",
            "생산",
            "시장 구조",
            "인프라",
            "industrial",
            "supply chain",
            "production",
            "market structure",
            "infrastructure",
        },
    ):
        signals.append("industry_mechanism")
    if contains_any(text, VISUAL_HOOK_TERMS | {"도표", "통계", "지도", "map", "chart"}):
        signals.append("visual_proof_object")
    return list(dict.fromkeys(signals))


def _policy_release_seed_signals(text: str) -> list[str]:
    signals = _policy_release_raw_seed_signals(text)
    is_meeting_or_coordination = contains_any(text, POLICY_RELEASE_MEETING_TERMS)
    if "odd_hook" in signals:
        return signals
    if "life_impact" in signals:
        return signals
    if is_meeting_or_coordination:
        return []
    if "industry_mechanism" in signals and "material_number" in signals:
        return signals
    if "regulatory_conflict" in signals and (
        "material_number" in signals or "industry_mechanism" in signals
    ):
        return signals
    if "visual_proof_object" in signals and (
        "material_number" in signals
        or "life_impact" in signals
        or "industry_mechanism" in signals
        or "regulatory_conflict" in signals
    ):
        return signals
    return []


def _policy_release_date_only_number(text: str) -> bool:
    if not any(char.isdigit() for char in text):
        return False
    if _policy_release_has_material_number(text):
        return False
    return bool(POLICY_RELEASE_DATE_RE.search(text)) or contains_any(
        text,
        POLICY_RELEASE_ANNOUNCEMENT_TERMS,
    )


def _policy_release_announcement_only(text: str, seed_signals: list[str]) -> bool:
    if seed_signals:
        return False
    return contains_any(text, POLICY_RELEASE_ANNOUNCEMENT_TERMS)


def _policy_release_meeting_only(text: str, seed_signals: list[str]) -> bool:
    if seed_signals:
        return False
    return contains_any(text, POLICY_RELEASE_MEETING_TERMS)


def _policy_release_procedural_number_only(text: str) -> bool:
    if not any(char.isdigit() for char in text):
        return False
    if _policy_release_seed_signals(text):
        return False
    return contains_any(
        text,
        POLICY_RELEASE_PROCEDURAL_NUMBER_TERMS,
    ) or _policy_release_date_only_number(text)


def _public_wire_editorial_category(text: str, source_role_class: str) -> str | None:
    if source_role_class != SOURCE_ROLE_PUBLIC_WIRE:
        return None
    has_ai = contains_any(text, {"ai", "인공지능", "챗봇", "자동화"})
    if contains_any(text, {"드론", "drone"}) and contains_any(
        text,
        {"경찰", "검거", "단속", "수배", "치안", "범인", "공공안전"},
    ):
        return "public_ai_enforcement"
    if has_ai and contains_any(
        text,
        {"병원", "의료", "응급", "환자", "연락", "섭외", "예약", "진료"},
    ):
        return "healthcare_operations_ai"
    if has_ai and contains_any(
        text,
        {"노사", "노동", "상생위", "경사노위", "직무", "일자리", "근로", "직장"},
    ):
        return "workplace_ai_transition"
    if has_ai and contains_any(
        text,
        {
            "공무원",
            "공공",
            "기관",
            "보고서",
            "교육",
            "행정",
            "부적절",
            "가짜기사",
            "가짜뉴스",
            "허위",
            "조작",
            "감사",
            "가이드라인",
        },
    ):
        return "public_ai_governance"
    if contains_any(
        text,
        {
            "쿠팡이츠",
            "배달비",
            "배달",
            "업주",
            "수수료",
            "플랫폼",
            "라이더",
            "상인",
            "가맹점",
        },
    ):
        return "platform_labor_market"
    if contains_any(text, {"노노갈등", "노조", "노사", "성과급", "임금"}) and contains_any(
        text,
        {"삼성전자", "반도체", "제조", "공장", "직군", "산업"},
    ):
        return "industrial_labor_conflict"
    return None


def _infer_editorial_category(
    title: str,
    summary: str,
    source_id: str | None,
    source_role_class: str = "unknown",
) -> str | None:
    text = text_blob(title, summary)
    if source_role_class == SOURCE_ROLE_RESEARCH_NOTE and _has_research_note_signals(text):
        return _research_note_seed_type(text)
    if source_role_class == SOURCE_ROLE_POLICY_RELEASE:
        return "policy_release_seed" if _policy_release_seed_signals(text) else None
    public_wire_category = _public_wire_editorial_category(text, source_role_class)
    if public_wire_category:
        return public_wire_category
    if contains_any(text, {"담보", "단기수익", "생산적", "정책금융", "국민성장펀드"}):
        return "productive_finance_policy"
    if contains_any(text, {"휴머노이드", "ai 로봇", "robotics r&d"}):
        return "industrial_policy_rnd"
    if contains_any(text, SINGLE_COMPANY_FINANCING_TERMS):
        if (
            source_role_class == SOURCE_ROLE_ACADEMIC_EXPLAINER
            and _academic_explainer_terms_dominate(text)
        ):
            return "academic_explainer"
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


def _has_named_actor(text: str) -> bool:
    lower_text = text.lower()
    if contains_any(lower_text, KOREAN_NAMED_ACTOR_TERMS | ENGLISH_NAMED_ACTOR_TERMS):
        return True
    if re.search(r"\b(?!AI\b)[A-Z]{3,}\b", text):
        return True
    return bool(re.search(r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+\b", text))


def infer_story_specificity(
    *,
    title: str,
    summary: str,
    why_interesting: str = "",
    possible_expansions: list[str] | None = None,
) -> dict[str, Any]:
    article_text = text_blob(title, summary)
    signals: list[str] = []
    if _has_named_actor(f"{title} {summary}"):
        signals.append("has_named_actor")
    if any(char.isdigit() for char in article_text) or contains_any(article_text, NUMBER_TERMS):
        signals.append("has_number")
    if contains_any(article_text, MECHANISM_TERMS):
        signals.append("has_mechanism")
    if contains_any(article_text, TENSION_TERMS):
        signals.append("has_tension")
    if contains_any(article_text, KOREA_BRIDGE_TERMS):
        signals.append("has_korea_bridge")
    if contains_any(article_text, VISUAL_HOOK_TERMS):
        signals.append("has_visual_hook")
    score = round(len(signals) / 6, 2)
    if score >= 0.67:
        level = "high"
    elif score >= 0.34:
        level = "medium"
    else:
        level = "low"
    return {
        "score": score,
        "level": level,
        "signals": signals,
        "generic_why_detected": any(
            pattern in str(why_interesting or "")
            for pattern in GENERIC_SPECIFICITY_WHY_PATTERNS
        ),
    }


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
    source_role_class: str,
    source_url: str,
    seed_type: str,
    risk_flags: list[str],
) -> tuple[str, list[str], list[str]]:
    text = text_blob(title, summary, source_url)
    quality_flags: list[str] = []
    if not summary.strip():
        quality_flags.append("empty_summary")
    has_structure = contains_any(text, BROADER_STRUCTURE_TERMS)
    has_accident_structure = contains_any(text, BROADER_STRUCTURE_TERMS - set(NUMBER_TERMS))
    if source_id == "bbc_rss_candidate" and contains_any(text, SPORT_TERMS) and not has_structure:
        quality_flags.append("sports_only")
    if contains_any(text, ACCIDENT_TERMS) and not has_accident_structure:
        quality_flags.append("accident_single_event")
    if source_id == "atlas_obscura" and contains_any(text, PLACE_LISTING_TERMS):
        quality_flags.append("pure_place_listing")
    if source_role_class == SOURCE_ROLE_POLICY_RELEASE and seed_type == "policy_release_evidence":
        quality_flags.append("policy_release_evidence_default")
    if source_role_class == SOURCE_ROLE_POLICY_RELEASE:
        raw_seed_signals = _policy_release_raw_seed_signals(text)
        seed_signals = _policy_release_seed_signals(text)
        if raw_seed_signals:
            quality_flags.append(
                "policy_release_seed_signals=" + ",".join(raw_seed_signals)
            )
        if "material_number" in seed_signals:
            quality_flags.append("policy_release_material_seed_signal")
        if _policy_release_date_only_number(text):
            quality_flags.append("policy_release_date_only_number")
        if _policy_release_announcement_only(text, seed_signals):
            quality_flags.append("policy_release_announcement_only")
        if _policy_release_meeting_only(text, seed_signals):
            quality_flags.append("policy_release_meeting_only")
        if _policy_release_procedural_number_only(text):
            quality_flags.append("policy_release_procedural_number_only")
    if seed_type == "healthcare_operations_ai" and "medical_claim_risk" not in risk_flags:
        risk_flags.append("medical_claim_risk")
    if contains_any(text, POLITICAL_POLICY_TERMS):
        if "political_sensitivity" not in risk_flags:
            risk_flags.append("political_sensitivity")
    if source_id == "npr_rss_candidate" and contains_any(text, POLITICAL_POLICY_TERMS):
        quality_flags.append("live_politics_or_statement")
    market_wire_like = source_role_class == SOURCE_ROLE_MARKET_WIRE or source_id in {
        "infomax_manual",
        "hankyung_manual",
    }
    if market_wire_like and (
        "investment_advice_risk" in risk_flags
        or contains_any(text, SINGLE_COMPANY_FINANCING_TERMS | MARKET_RATE_STRESS_TERMS)
    ):
        quality_flags.append("single_stock_or_asset_frame")
        if contains_any(text, {"거시", "경기", "산업", "정책", "macro", "industry", "policy"}):
            quality_flags.append("broader_macro_angle")
        if "investment_advice_risk" not in risk_flags:
            risk_flags.append("investment_advice_risk")
    if market_wire_like and contains_any(
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
    source_role_class = _source_role_class(source, article.get("source_id"))
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
    editorial_category = _infer_editorial_category(
        title,
        summary,
        article.get("source_id"),
        source_role_class,
    )
    if editorial_category:
        seed_type = editorial_category
    if (
        source_role_class == SOURCE_ROLE_ACADEMIC_EXPLAINER
        and seed_type == "single_company_financing"
        and _academic_explainer_terms_dominate(text)
    ):
        seed_type = "academic_explainer"
        editorial_category = "academic_explainer"
    if (
        source_role_class == SOURCE_ROLE_ACADEMIC_EXPLAINER
        and seed_type in {"other", "policy_market_shock", "science_technology"}
        and _academic_explainer_terms_dominate(text)
    ):
        seed_type = "academic_explainer"
        editorial_category = "academic_explainer"
    if (
        source_role_class == SOURCE_ROLE_RESEARCH_NOTE
        and seed_type == "other"
        and _has_research_note_signals(text)
    ):
        seed_type = _research_note_seed_type(text)
        editorial_category = seed_type
    if source_role_class == SOURCE_ROLE_POLICY_RELEASE and not _policy_release_seed_signals(text):
        seed_type = "policy_release_evidence"
        editorial_category = "policy_release_evidence"
    quality_hint, quality_flags, risk_flags = _rss_quality_hints(
        title=title,
        summary=summary,
        source_id=article.get("source_id"),
        source_role_class=source_role_class,
        source_url=source_url_canonical,
        seed_type=seed_type,
        risk_flags=risk_flags,
    )
    freshness_window_days = source.freshness_window_days if source else None
    freshness_policy = source.freshness_policy if source else None
    freshness_status, age_hours = classify_freshness(
        article.get("published_at"),
        article.get("collected_at"),
        recent_hours=(
            int(freshness_window_days) * 24
            if freshness_policy == LOW_FREQUENCY_RESEARCH_POLICY and freshness_window_days
            else FRESHNESS_RECENT_HOURS
        ),
    )
    research_publication_age_days = (
        round(age_hours / 24, 1)
        if freshness_policy == LOW_FREQUENCY_RESEARCH_POLICY and age_hours is not None
        else None
    )
    if (
        freshness_status == "stale"
        and source_type != "manual"
        and freshness_policy != LOW_FREQUENCY_RESEARCH_POLICY
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
    story_specificity = infer_story_specificity(
        title=title,
        summary=summary,
        why_interesting=why_interesting,
        possible_expansions=possible_expansions,
    )
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
        "source_role_class": source_role_class,
        "source_freshness_policy": freshness_policy,
        "source_freshness_window_days": freshness_window_days,
        "published_at": article.get("published_at"),
        "collected_at": article["collected_at"],
        "freshness_status": freshness_status,
        "age_hours": age_hours,
        "research_publication_age_days": research_publication_age_days,
        "first_seen_at": article.get("first_seen_at") or article["collected_at"],
        "last_seen_at": article.get("last_seen_at") or article["collected_at"],
        "source_count": int(article.get("source_count") or 1),
        "source_sections": article.get("source_sections") or [],
        "supporting_source_ids": article.get("supporting_source_ids") or [],
        "mode": article.get("mode") or "normal",
        "seed_type": seed_type,
        "editorial_category": editorial_category or seed_type,
        "summary": summary,
        "why_interesting": why_interesting,
        "story_specificity": story_specificity,
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
