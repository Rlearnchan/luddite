"""Read-only summaries for the Jibi bundle review board."""

from __future__ import annotations

import csv
import json
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Any
from urllib.parse import urlparse

import typer
from rich.console import Console

from luddite import paths
from luddite.agents.jibi.append_to_sheet import (
    BUNDLE_REVIEW_SHEET_COLUMNS,
    REVIEWER_COLUMNS,
    GoogleSheetAppendConfig,
    load_append_config,
)
from luddite.integrations.google_sheets import GoogleSheetsApiClient
from luddite.utils.jsonl import read_jsonl
from luddite.utils.urls import canonicalize_url

app = typer.Typer(no_args_is_help=False)
history_app = typer.Typer(no_args_is_help=False)
console = Console()

REVIEW_TAGS = ["seed", "evidence", "merge", "needs", "reject", "unclear", "unlabeled"]
PRIMARY_INFERRED_LABELS = [
    "seed",
    "conditional_seed",
    "evidence_only",
    "needs_more_sources",
    "merge_or_duplicate",
    "reject",
    "unclear",
    "unlabeled",
]
INFERRED_LABELS = [
    "seed",
    "conditional_seed",
    "evidence_only",
    "needs_more_sources",
    "merge_or_duplicate",
    "past_topic_overlap",
    "reject",
    "unclear",
    "unlabeled",
]
REVIEW_MODIFIERS = [
    "past_topic_overlap",
    "already_used_live",
    "bundle_needed",
    "weak_source",
    "single_company_case",
    "promo_or_bulletin",
    "good_hook",
    "system_issue",
    "audience_interest_weak",
    "evidence_useful",
    "textbook_explainer_risk",
    "weak_audience_bridge",
]
FAILURE_MODES = [
    "evidence_not_seed",
    "needs_news_hook",
    "too_broad",
    "too_familiar",
    "needs_supporting_links",
    "wrong_frame",
    "needs_concrete_question",
    "market_risk",
    "weak_audience_bridge",
]
POSITIVE_SIGNALS = [
    "good_question",
    "fresh_angle",
    "promising_hook",
    "useful_evidence",
    "specific_case_needed",
]
NEXT_RESEARCH_ACTIONS = [
    "find_supporting_links",
    "find_current_news_hook",
    "narrow_to_concrete_question",
    "find_specific_case_or_odd_hook",
    "check_past_topic_differentiation",
    "reframe_around_stronger_real_economy_angle",
    "demote_to_evidence_or_background",
    "avoid_market_advice_frame",
    "keep_question_as_editorial_anchor",
]
TAG_ALIASES = {
    "seed": "seed",
    "방송": "seed",
    "소재": "seed",
    "evidence": "evidence",
    "근거": "evidence",
    "merge": "merge",
    "묶기": "merge",
    "중복": "merge",
    "needs": "needs",
    "보강": "needs",
    "자료필요": "needs",
    "reject": "reject",
    "기각": "reject",
    "별로": "reject",
    "아님": "reject",
    "unclear": "unclear",
    "애매": "unclear",
    "모름": "unclear",
}
EXPLICIT_TAG_TO_INFERRED_LABEL = {
    "seed": "seed",
    "evidence": "evidence_only",
    "merge": "merge_or_duplicate",
    "needs": "needs_more_sources",
    "reject": "reject",
    "unclear": "unclear",
    "unlabeled": "unlabeled",
}
INFERRED_LABEL_TO_REVIEW_TAG = {
    "seed": "seed",
    "conditional_seed": "seed",
    "evidence_only": "evidence",
    "needs_more_sources": "needs",
    "merge_or_duplicate": "merge",
    "past_topic_overlap": "merge",
    "reject": "reject",
    "unclear": "unclear",
    "unlabeled": "unlabeled",
}
PAST_OVERLAP_STRONG_TERMS = {
    "과거 영상",
    "다룬 바",
    "겹침",
    "이번 주 라이브",
    "pptx",
    "라이브 소재",
}
PAST_OVERLAP_ALREADY_CONTEXT_TERMS = {
    "영상",
    "다룬",
    "라이브",
    "주제",
    "겹침",
}
MERGE_TERMS = {"묶", "bundle", "비슷한 사례", "같이", "합치"}
CONDITIONAL_TERMS = {
    "가능성 있음",
    "가능성이 있음",
    "조건부",
    "제도의 문제로 풀면",
    "시스템 문제",
    "단일기업",
    "보강하면",
}
SYSTEM_ISSUE_TERMS = {"제도", "규제", "사각지대", "시스템", "구조", "문제"}
WEAK_SOURCE_TERMS = {"약한 소스", "소스 약", "출처 약", "단문", "자료가 약", "내용도 단문"}
SINGLE_COMPANY_TERMS = {"단일기업", "단일 기업", "단일 회사", "회사 기사"}
PROMO_OR_BULLETIN_TERMS = {
    "홍보성",
    "공모전",
    "캠페인",
    "행사",
    "회의",
    "보도자료",
    "시연",
}
GOOD_HOOK_TERMS = {"hook", "후킹", "흥미", "재미", "좋은 소재", "좋은 자료", "가능성"}
AUDIENCE_WEAK_TERMS = {"안 궁금", "그래서 뭐", "시청자", "생활감 약", "연결 약"}
TEXTBOOK_RISK_TERMS = {"교과서", "원론", "설명형", "textbook"}
POSITIVE_TERMS = {
    "좋은 소재",
    "좋은 자료 선정",
    "좋은 자료",
    "방송에 쓰일",
    "주제로 가능",
    "가능성 있음",
    "가능성이 있음",
    "살릴 수",
    "긍정",
}
EVIDENCE_TERMS = {
    "근거",
    "자료로",
    "곁가지",
    "붙이면",
    "supporting",
    "큰 이야기",
    "맥락",
}
NEEDS_TERMS = {"자료 필요", "보강", "추가", "숫자", "독립 출처", "외부 자료"}
REJECT_TERMS = {
    "재미가 없",
    "약함",
    "seed로 보기에는 약",
    "나쁜 선택",
    "잘못 선정",
    "그래서 뭐",
    "안 궁금",
    "단발성",
    "홍보성",
    "단문",
    "부적절",
    "reject",
}
UNCLEAR_TERMS = {"애매", "모르겠", "불분명", "판단 어려"}
EVIDENCE_NOT_SEED_TERMS = {
    "자료로 만들 수가 없다",
    "자료로 만들 수 없다",
    "이거 하나만 가져오면",
    "이것만 가져오면",
    "주제로 할 수가 없",
    "주제로 할 수 없",
    "단독 seed",
    "단독 후보",
    "단독으로는",
    "그냥 자료",
    "1-2 슬라이드",
    "한두 슬라이드",
}
NEEDS_NEWS_HOOK_TERMS = {
    "최신 기사",
    "최신 뉴스를",
    "뉴스가 메인",
    "hooking 이슈",
    "후킹 이슈",
    "교과서",
    "강의",
    "원론",
    "이론 공부",
    "실생활에 밀접",
}
TOO_BROAD_TERMS = {
    "너무나 거대",
    "너무 거대",
    "커다란 이야기",
    "그래서 어쩌라고",
    "추상적",
    "심오한",
    "두루두루",
    "현상 소개",
}
TOO_FAMILIAR_TERMS = {
    "뻔하디 뻔",
    "뻔한",
    "이미 많이",
    "많이 했",
    "100번도 더",
    "차별점 없",
    "새로운 게 별로",
    "새로운 포인트",
    "맨날 하는",
    "반복",
}
WRONG_FRAME_TERMS = {
    "초점",
    "옮겨져야",
    "잘못",
    "프레임",
    "사고방식",
}
CONCRETE_QUESTION_TERMS = {
    "질문거리",
    "질문거리를",
    "가장 신기한 원인",
    "가장 강력한 원인",
    "가장 웃긴 원인",
    "한가지",
    "한 가지",
    "두가지",
    "두 가지",
    "집중적으로",
}
MARKET_RISK_TERMS = {
    "투자",
    "주가",
    "지수",
    "공모주",
    "업황",
    "삼성전자",
    "sk하이닉스",
    "sk 하이닉스",
}
GOOD_QUESTION_TERMS = {
    "질문거리를 던지는 것이 제일 좋",
    "질문거리를 던지는 작업",
    "이런 질문거리",
    "good",
    "당면한 현상",
    "각 경제 주체",
}
FRESH_ANGLE_TERMS = {"신선", "참신", "새 각도", "새로운 각도", "몰랐을 법"}
PROMISING_HOOK_TERMS = {"화두", "가능성", "살릴 수", "좋음", "괜찮음", "재밌"}
USEFUL_EVIDENCE_TERMS = {"자료로", "근거", "언급할 정도", "보강 링크", "같이 잘 엮"}
SPECIFIC_CASE_NEEDED_TERMS = {
    "실제 사례",
    "구체적인",
    "구체적",
    "뭐라도",
    "한가지",
    "한 가지",
    "사례",
}


@dataclass(frozen=True)
class ReviewFeedbackPaths:
    markdown_path: Path
    json_path: Path


@dataclass(frozen=True)
class ReviewHistoryCalibrationPaths:
    markdown_path: Path
    json_path: Path


def parse_review_tag(note: str) -> str:
    text = note.strip().lower()
    if not text:
        return "unlabeled"
    token = re.split(r"\s*(?:—|–|-|:)\s*|\s+", text, maxsplit=1)[0].strip()
    return TAG_ALIASES.get(token, "unlabeled")


def _contains_any(text: str, terms: set[str]) -> list[str]:
    return [term for term in terms if term.lower() in text]


def _failure_mode_matches(text: str) -> dict[str, list[str]]:
    supporting_link_terms = {
        "이거 하나만 가져오면",
        "이것만 가져오면",
        "자료로 만들 수 없다",
        "자료로 만들 수가 없다",
    }
    matches = {
        "evidence_not_seed": _contains_any(text, EVIDENCE_NOT_SEED_TERMS),
        "needs_news_hook": _contains_any(text, NEEDS_NEWS_HOOK_TERMS),
        "too_broad": _contains_any(text, TOO_BROAD_TERMS),
        "too_familiar": _contains_any(text, TOO_FAMILIAR_TERMS),
        "needs_supporting_links": _contains_any(text, NEEDS_TERMS)
        + _contains_any(text, supporting_link_terms)
        + _contains_any(text, SPECIFIC_CASE_NEEDED_TERMS),
        "wrong_frame": [],
        "needs_concrete_question": _contains_any(text, CONCRETE_QUESTION_TERMS),
        "market_risk": _contains_any(text, MARKET_RISK_TERMS),
        "weak_audience_bridge": _contains_any(text, AUDIENCE_WEAK_TERMS),
    }
    wrong_frame_hits = _contains_any(text, WRONG_FRAME_TERMS)
    if wrong_frame_hits and any(
        token in text for token in ("초점", "옮겨", "잘못", "아닌", "사고방식")
    ):
        matches["wrong_frame"] = wrong_frame_hits
    if matches["evidence_not_seed"] or matches["needs_news_hook"]:
        matches["needs_news_hook"] = list(
            dict.fromkeys([*matches["needs_news_hook"], "news_hook_needed"])
        )
    return {key: value for key, value in matches.items() if value}


def _positive_signal_matches(text: str) -> dict[str, list[str]]:
    return {
        key: value
        for key, value in {
            "good_question": _contains_any(text, GOOD_QUESTION_TERMS),
            "fresh_angle": _contains_any(text, FRESH_ANGLE_TERMS),
            "promising_hook": _contains_any(text, PROMISING_HOOK_TERMS),
            "useful_evidence": _contains_any(text, USEFUL_EVIDENCE_TERMS),
            "specific_case_needed": _contains_any(text, SPECIFIC_CASE_NEEDED_TERMS),
        }.items()
        if value
    }


def _past_overlap_matches(text: str) -> list[str]:
    matches = _contains_any(text, PAST_OVERLAP_STRONG_TERMS)
    if "이미" in text:
        context = _contains_any(text, PAST_OVERLAP_ALREADY_CONTEXT_TERMS)
        if context:
            matches.append("이미+" + ",".join(context[:2]))
    return matches


def _review_signal_matches(text: str) -> dict[str, list[str]]:
    return {
        "past_topic_overlap": _past_overlap_matches(text),
        "merge_or_duplicate": _contains_any(text, MERGE_TERMS),
        "conditional_seed": _contains_any(text, CONDITIONAL_TERMS),
        "seed": _contains_any(text, POSITIVE_TERMS),
        "evidence_only": _contains_any(text, EVIDENCE_TERMS),
        "needs_more_sources": _contains_any(text, NEEDS_TERMS),
        "reject": _contains_any(text, REJECT_TERMS),
        "unclear": _contains_any(text, UNCLEAR_TERMS),
        "system_issue": _contains_any(text, SYSTEM_ISSUE_TERMS),
        "weak_source": _contains_any(text, WEAK_SOURCE_TERMS),
        "single_company_case": _contains_any(text, SINGLE_COMPANY_TERMS),
        "promo_or_bulletin": _contains_any(text, PROMO_OR_BULLETIN_TERMS),
        "good_hook": _contains_any(text, GOOD_HOOK_TERMS),
        "audience_interest_weak": _contains_any(text, AUDIENCE_WEAK_TERMS),
        "textbook_explainer_risk": _contains_any(text, TEXTBOOK_RISK_TERMS),
    }


def _review_modifiers(matches: dict[str, list[str]]) -> list[str]:
    modifiers: list[str] = []
    for key in [
        "past_topic_overlap",
        "weak_source",
        "single_company_case",
        "promo_or_bulletin",
        "good_hook",
        "system_issue",
        "audience_interest_weak",
        "textbook_explainer_risk",
    ]:
        if matches.get(key):
            modifiers.append(key)
    if matches.get("past_topic_overlap") and any(
        term in ",".join(matches["past_topic_overlap"])
        for term in ("이번 주 라이브", "라이브 소재")
    ):
        modifiers.append("already_used_live")
    if matches.get("merge_or_duplicate") or matches.get("needs_more_sources"):
        modifiers.append("bundle_needed")
    if matches.get("evidence_only"):
        modifiers.append("evidence_useful")
    if matches.get("audience_interest_weak") or matches.get("weak_source"):
        modifiers.append("weak_audience_bridge")
    return list(dict.fromkeys(modifiers))


def _primary_label_from_matches(matches: dict[str, list[str]]) -> str:
    has_seed = bool(matches["seed"])
    has_conditional = bool(matches["conditional_seed"] or matches["system_issue"])
    has_evidence = bool(matches["evidence_only"])
    has_needs = bool(matches["needs_more_sources"])
    has_merge = bool(matches["merge_or_duplicate"])
    has_reject = bool(matches["reject"])
    has_past_overlap = bool(matches["past_topic_overlap"])

    if has_seed and (has_conditional or has_needs or matches["single_company_case"]):
        return "conditional_seed"
    if has_seed:
        return "seed"
    if has_reject and not (has_evidence or has_conditional or has_merge):
        return "reject"
    if has_conditional and (has_evidence or has_needs or matches["good_hook"]):
        return "conditional_seed"
    if has_evidence:
        return "evidence_only"
    if has_needs:
        return "needs_more_sources"
    if has_merge or has_past_overlap:
        return "merge_or_duplicate"
    if has_reject:
        return "reject"
    if matches["unclear"]:
        return "unclear"
    return "unlabeled"


def _legacy_inferred_label(primary_label: str, modifiers: list[str]) -> str:
    if "past_topic_overlap" in modifiers and primary_label in {
        "seed",
        "conditional_seed",
        "merge_or_duplicate",
        "evidence_only",
    }:
        return "past_topic_overlap"
    return primary_label


def _next_research_actions(
    failure_modes: list[str],
    positive_signals: list[str],
) -> list[str]:
    actions: list[str] = []
    if "needs_supporting_links" in failure_modes:
        actions.append("find_supporting_links")
    if "needs_news_hook" in failure_modes or "evidence_not_seed" in failure_modes:
        actions.append("find_current_news_hook")
    if "too_broad" in failure_modes or "needs_concrete_question" in failure_modes:
        actions.append("narrow_to_concrete_question")
    if "specific_case_needed" in positive_signals:
        actions.append("find_specific_case_or_odd_hook")
    if "too_familiar" in failure_modes:
        actions.append("check_past_topic_differentiation")
    if "wrong_frame" in failure_modes:
        actions.append("reframe_around_stronger_real_economy_angle")
    if "evidence_not_seed" in failure_modes:
        actions.append("demote_to_evidence_or_background")
    if "market_risk" in failure_modes:
        actions.append("avoid_market_advice_frame")
    if "good_question" in positive_signals:
        actions.append("keep_question_as_editorial_anchor")
    return [action for action in NEXT_RESEARCH_ACTIONS if action in set(actions)]


def _review_signal(
    primary_label: str,
    failure_modes: list[str],
    positive_signals: list[str],
) -> str:
    if primary_label == "unlabeled":
        return "unlabeled"
    if primary_label == "reject":
        return "reject"
    if "good_question" in positive_signals and not {
        "evidence_not_seed",
        "wrong_frame",
        "too_familiar",
    }.intersection(failure_modes):
        return "strong"
    if primary_label == "seed" and not failure_modes:
        return "strong"
    if primary_label in {"conditional_seed", "needs_more_sources", "evidence_only"}:
        return "conditional"
    if positive_signals and not failure_modes:
        return "conditional"
    if failure_modes:
        return "weak"
    return "unlabeled"


def _review_feedback_base_payload(
    *,
    raw_note: str,
    explicit_tag: str,
    primary_label: str,
    inferred_label: str,
    modifiers: list[str],
    confidence: str,
    reasons: list[str],
    failure_modes: list[str],
    positive_signals: list[str],
) -> dict[str, Any]:
    return {
        "tag": INFERRED_LABEL_TO_REVIEW_TAG[primary_label]
        if explicit_tag == "unlabeled"
        else explicit_tag,
        "explicit_tag": explicit_tag,
        "inferred_label": inferred_label,
        "primary_inferred_label": primary_label,
        "modifiers": modifiers,
        "failure_modes": failure_modes,
        "positive_signals": positive_signals,
        "review_signal": _review_signal(
            primary_label,
            failure_modes,
            positive_signals,
        ),
        "next_research_actions": _next_research_actions(
            failure_modes,
            positive_signals,
        ),
        "inferred_confidence": confidence,
        "inference_reasons": reasons,
        "raw_note": raw_note,
        "note": raw_note,
    }


def infer_review_feedback(note: str) -> dict[str, Any]:
    raw_note = note.strip()
    explicit_tag = parse_review_tag(raw_note)
    if not raw_note:
        return {
            "tag": "unlabeled",
            "explicit_tag": "unlabeled",
            "inferred_label": "unlabeled",
            "primary_inferred_label": "unlabeled",
            "modifiers": [],
            "failure_modes": [],
            "positive_signals": [],
            "review_signal": "unlabeled",
            "next_research_actions": [],
            "inferred_confidence": "low",
            "inference_reasons": [],
            "raw_note": "",
            "note": "",
        }
    text = raw_note.lower()
    matches = _review_signal_matches(text)
    modifiers = _review_modifiers(matches)
    failure_matches = _failure_mode_matches(text)
    positive_matches = _positive_signal_matches(text)
    failure_modes = [mode for mode in FAILURE_MODES if failure_matches.get(mode)]
    positive_signals = [
        signal for signal in POSITIVE_SIGNALS if positive_matches.get(signal)
    ]
    if explicit_tag != "unlabeled":
        primary_label = EXPLICIT_TAG_TO_INFERRED_LABEL[explicit_tag]
        inferred_label = _legacy_inferred_label(primary_label, modifiers)
        reasons = [f"explicit_tag:{explicit_tag}"] + [
            f"{key}:{','.join(value[:3])}"
            for key, value in matches.items()
            if value
        ]
        reasons.extend(
            f"failure_mode:{key}:{','.join(value[:3])}"
            for key, value in failure_matches.items()
        )
        reasons.extend(
            f"positive_signal:{key}:{','.join(value[:3])}"
            for key, value in positive_matches.items()
        )
        return _review_feedback_base_payload(
            raw_note=raw_note,
            explicit_tag=explicit_tag,
            primary_label=primary_label,
            inferred_label=inferred_label,
            modifiers=modifiers,
            confidence="high",
            reasons=reasons,
            failure_modes=failure_modes,
            positive_signals=positive_signals,
        )

    primary_label = _primary_label_from_matches(matches)
    if primary_label == "unlabeled" and "good_question" in positive_signals:
        primary_label = "seed"
    elif primary_label == "unlabeled" and failure_modes:
        primary_label = "unclear"
    label = _legacy_inferred_label(primary_label, modifiers)
    reasons = [
        f"{key}:{','.join(value[:3])}"
        for key, value in matches.items()
        if value
    ]
    reasons.extend(
        f"failure_mode:{key}:{','.join(value[:3])}"
        for key, value in failure_matches.items()
    )
    reasons.extend(
        f"positive_signal:{key}:{','.join(value[:3])}"
        for key, value in positive_matches.items()
    )
    if primary_label == "unlabeled":
        confidence = "low"
    elif len([value for value in matches.values() if value]) >= 2:
        confidence = "medium"
    else:
        confidence = "high"
    return _review_feedback_base_payload(
        raw_note=raw_note,
        explicit_tag="unlabeled",
        primary_label=primary_label,
        inferred_label=label,
        modifiers=modifiers,
        confidence=confidence,
        reasons=reasons,
        failure_modes=failure_modes,
        positive_signals=positive_signals,
    )


def _rows_from_values(values: list[list[str]]) -> list[dict[str, str]]:
    if not values:
        return []
    header = values[0]
    rows: list[dict[str, str]] = []
    for raw_row in values[1:]:
        row = {
            column: raw_row[index] if index < len(raw_row) else ""
            for index, column in enumerate(header)
        }
        if any(str(value).strip() for value in row.values()):
            rows.append(row)
    return rows


def _rows_from_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as source:
        return list(csv.DictReader(source))


def _reviewer_completion(rows: list[dict[str, str]]) -> dict[str, int]:
    return {
        column: sum(1 for row in rows if str(row.get(column, "")).strip())
        for column in REVIEWER_COLUMNS
    }


def _row_review_signal(reviewer_notes: dict[str, dict[str, Any]]) -> str:
    signals = [
        str(note.get("review_signal") or "")
        for note in reviewer_notes.values()
        if note.get("note")
    ]
    if not signals:
        return "unreviewed"
    decisive = {signal for signal in signals if signal != "unlabeled"}
    if not decisive:
        return "unreviewed"
    if "reject" in decisive and decisive.intersection({"strong", "conditional"}):
        return "mixed"
    if "strong" in decisive and decisive.intersection({"weak", "conditional"}):
        return "conditional"
    for signal in ["strong", "conditional", "weak", "reject"]:
        if signal in decisive:
            return signal
    return "unreviewed"


def _row_signal_values(
    reviewer_notes: dict[str, dict[str, Any]],
    field: str,
    allowed: list[str],
) -> list[str]:
    values: list[str] = []
    for note in reviewer_notes.values():
        values.extend(str(item) for item in note.get(field, []) if item)
    present = set(values)
    return [item for item in allowed if item in present]


def _operator_lesson(
    *,
    title: str,
    row_review_signal: str,
    failure_modes: list[str],
    positive_signals: list[str],
    next_actions: list[str],
) -> str:
    prefix = f"{title}: " if title else ""
    if row_review_signal == "unreviewed":
        return prefix + "리뷰가 아직 없어 판단 보류."
    if row_review_signal == "mixed":
        return prefix + "리뷰 판단이 갈립니다. seed 가능성과 탈락 사유를 함께 재검토하세요."
    if "wrong_frame" in failure_modes:
        return prefix + "현재 프레임이 빗나갔습니다. 더 강한 실물경제/생활 질문으로 초점을 옮기세요."
    if {"evidence_not_seed", "needs_news_hook"}.intersection(failure_modes):
        return prefix + "자료 자체보다 최신 뉴스나 현상 hook을 먼저 찾아야 합니다."
    if "too_familiar" in failure_modes:
        return prefix + "이미 익숙한 주제입니다. 새 각도나 차별점이 없으면 낮추세요."
    if "too_broad" in failure_modes:
        return prefix + "범위가 너무 큽니다. 구체 사례와 좁은 질문으로 다시 잡으세요."
    if "needs_supporting_links" in failure_modes:
        return prefix + "이 자료 하나로는 약합니다. 숫자, 사례, 독립 출처를 보강하세요."
    if "good_question" in positive_signals:
        return prefix + "생활 가까운 질문이 잡혀 있습니다. 이 질문을 중심으로 후속 조사를 이어가세요."
    if "find_supporting_links" in next_actions:
        return prefix + "보강 링크를 찾은 뒤 seed/evidence 역할을 다시 판정하세요."
    if row_review_signal == "strong":
        return prefix + "긍정 신호가 강합니다. 바로 확장 가능한 질문과 보강 자료를 확인하세요."
    if row_review_signal == "conditional":
        return prefix + "조건부 후보입니다. 보강 자료나 프레임 조정 후 다시 판단하세요."
    if row_review_signal == "reject":
        return prefix + "현재 형태로는 낮추거나 제외하는 편이 안전합니다."
    return prefix + "추가 판단이 필요합니다."


def _note_payload(note: str) -> dict[str, Any]:
    return infer_review_feedback(note)


def _row_registered_at(row: dict[str, Any]) -> str:
    return str(row.get("일시") or row.get("날짜") or "").strip()


def _row_date(row: dict[str, Any], fallback: str = "") -> str:
    value = _row_registered_at(row)
    if len(value) >= 10:
        return value[:10]
    return fallback


def summarize_review_feedback(
    rows: list[dict[str, str]],
    *,
    run_date: str,
) -> dict[str, Any]:
    tag_counts = Counter({tag: 0 for tag in REVIEW_TAGS})
    inferred_label_counts = Counter({label: 0 for label in INFERRED_LABELS})
    primary_label_counts = Counter({label: 0 for label in PRIMARY_INFERRED_LABELS})
    modifier_counts = Counter({modifier: 0 for modifier in REVIEW_MODIFIERS})
    modifier_examples: dict[str, list[dict[str, str]]] = {
        modifier: [] for modifier in REVIEW_MODIFIERS
    }
    failure_mode_counts = Counter({mode: 0 for mode in FAILURE_MODES})
    positive_signal_counts = Counter({signal: 0 for signal in POSITIVE_SIGNALS})
    next_research_action_counts = Counter(
        {action: 0 for action in NEXT_RESEARCH_ACTIONS}
    )
    row_payloads: list[dict[str, Any]] = []
    disagreement_rows: list[dict[str, Any]] = []
    for index, row in enumerate(rows, start=2):
        reviewer_notes = {
            column: _note_payload(str(row.get(column, "")))
            for column in REVIEWER_COLUMNS
        }
        for reviewer, note in reviewer_notes.items():
            if note["note"]:
                tag_counts[note["tag"]] += 1
                inferred_label_counts[note["inferred_label"]] += 1
                primary_label_counts[note["primary_inferred_label"]] += 1
                for failure_mode in note.get("failure_modes", []):
                    failure_mode_counts[failure_mode] += 1
                for positive_signal in note.get("positive_signals", []):
                    positive_signal_counts[positive_signal] += 1
                for action in note.get("next_research_actions", []):
                    next_research_action_counts[action] += 1
                for modifier in note["modifiers"]:
                    modifier_counts[modifier] += 1
                    if len(modifier_examples[modifier]) < 5:
                        modifier_examples[modifier].append(
                            {
                                "row": str(index),
                                "title": str(row.get("제목", "")),
                                "reviewer": reviewer,
                                "note": str(note["note"]),
                            }
                        )
        tags = {note["tag"] for note in reviewer_notes.values() if note["note"]}
        row_failure_modes = _row_signal_values(
            reviewer_notes,
            "failure_modes",
            FAILURE_MODES,
        )
        row_positive_signals = _row_signal_values(
            reviewer_notes,
            "positive_signals",
            POSITIVE_SIGNALS,
        )
        row_next_research_actions = _row_signal_values(
            reviewer_notes,
            "next_research_actions",
            NEXT_RESEARCH_ACTIONS,
        )
        row_review_signal = _row_review_signal(reviewer_notes)
        row_payload = {
            "row": index,
            "date": _row_date(row, run_date),
            "registered_at": _row_registered_at(row),
            "title": row.get("제목", ""),
            "score": row.get("점수", ""),
            "id": row.get("ID", ""),
            "reviewers": reviewer_notes,
            "row_review_signal": row_review_signal,
            "row_failure_modes": row_failure_modes,
            "row_positive_signals": row_positive_signals,
            "row_next_research_actions": row_next_research_actions,
            "operator_lesson": _operator_lesson(
                title=str(row.get("제목", "")),
                row_review_signal=row_review_signal,
                failure_modes=row_failure_modes,
                positive_signals=row_positive_signals,
                next_actions=row_next_research_actions,
            ),
        }
        row_payloads.append(row_payload)
        if "seed" in tags and "reject" in tags:
            inferred = any(
                note["explicit_tag"] == "unlabeled"
                and note["tag"] not in {"unlabeled", "unclear"}
                for note in reviewer_notes.values()
                if note["note"]
            )
            disagreement_rows.append(
                {
                    "row": index,
                    "title": row.get("제목", ""),
                    "id": row.get("ID", ""),
                    "tags": sorted(tags),
                    "reason": "seed_vs_reject",
                    "inferred": inferred,
                }
            )
    return {
        "run_date": run_date,
        "generated_at": datetime.now(UTC).isoformat(),
        "total_rows": len(rows),
        "reviewer_completion": _reviewer_completion(rows),
        "tag_counts": dict(tag_counts),
        "inferred_label_counts": dict(inferred_label_counts),
        "primary_label_counts": dict(primary_label_counts),
        "modifier_counts": dict(modifier_counts),
        "modifier_examples": modifier_examples,
        "failure_mode_counts": dict(failure_mode_counts),
        "positive_signal_counts": dict(positive_signal_counts),
        "next_research_action_counts": dict(next_research_action_counts),
        "rows": row_payloads,
        "disagreement_rows": disagreement_rows,
    }


def _markdown(summary: dict[str, Any]) -> str:
    lines = [
        f"# Jibi Review Feedback — {summary['run_date']}",
        "",
        f"- Total rows: {summary['total_rows']}",
        f"- Generated at: `{summary['generated_at']}`",
        "",
        "## Reviewer Completion",
        "",
    ]
    for reviewer, count in summary["reviewer_completion"].items():
        lines.append(f"- {reviewer}: {count}/{summary['total_rows']}")
    lines.extend(["", "## Operator Lessons", ""])
    for row in summary["rows"]:
        lines.append(
            f"- row {row['row']} `{row.get('row_review_signal', 'unreviewed')}`: "
            f"{row.get('operator_lesson', '')}"
        )
    lines.extend(["", "## Failure Mode Counts", ""])
    for mode in FAILURE_MODES:
        lines.append(f"- {mode}: {summary.get('failure_mode_counts', {}).get(mode, 0)}")
    lines.extend(["", "## Next Research Actions", ""])
    for action in NEXT_RESEARCH_ACTIONS:
        lines.append(
            f"- {action}: "
            f"{summary.get('next_research_action_counts', {}).get(action, 0)}"
        )
    lines.extend(["", "## Positive Signal Counts", ""])
    for signal in POSITIVE_SIGNALS:
        lines.append(
            f"- {signal}: {summary.get('positive_signal_counts', {}).get(signal, 0)}"
        )
    lines.extend(["", "## Tag Counts", ""])
    for tag in REVIEW_TAGS:
        lines.append(f"- {tag}: {summary['tag_counts'].get(tag, 0)}")
    lines.extend(["", "## Natural Review Inference Summary", ""])
    inferred_total = sum(summary.get("inferred_label_counts", {}).values())
    lines.append(f"- inferred_notes: {inferred_total}")
    lines.extend(["", "## Inferred Label Counts", ""])
    for label in INFERRED_LABELS:
        lines.append(f"- {label}: {summary.get('inferred_label_counts', {}).get(label, 0)}")
    lines.extend(["", "## Primary Label Counts", ""])
    for label in PRIMARY_INFERRED_LABELS:
        lines.append(f"- {label}: {summary.get('primary_label_counts', {}).get(label, 0)}")
    lines.extend(["", "## Modifier Counts", ""])
    for modifier in REVIEW_MODIFIERS:
        lines.append(f"- {modifier}: {summary.get('modifier_counts', {}).get(modifier, 0)}")
    lines.extend(["", "## Examples By Modifier", ""])
    modifier_examples = summary.get("modifier_examples", {})
    for modifier in REVIEW_MODIFIERS:
        examples = modifier_examples.get(modifier) or []
        if not examples:
            continue
        lines.append(f"### {modifier}")
        lines.append("")
        for item in examples:
            lines.append(
                f"- row {item['row']} {item['title']} / {item['reviewer']}: "
                f"{item['note']}"
            )
        lines.append("")
    lines.extend(["", "## Notes By Row", ""])
    for row in summary["rows"]:
        lines.append(f"### {row['title'] or 'untitled'}")
        lines.append("")
        lines.append(f"- ID: `{row['id']}`")
        if row.get("score"):
            lines.append(f"- 점수: {row['score']}")
        lines.append(f"- row_review_signal: `{row.get('row_review_signal', '')}`")
        lines.append(
            "- row_failure_modes: `"
            f"{','.join(row.get('row_failure_modes', [])) or 'none'}`"
        )
        lines.append(
            "- row_positive_signals: `"
            f"{','.join(row.get('row_positive_signals', [])) or 'none'}`"
        )
        lines.append(
            "- row_next_research_actions: `"
            f"{','.join(row.get('row_next_research_actions', [])) or 'none'}`"
        )
        lines.append(f"- operator_lesson: {row.get('operator_lesson', '')}")
        for reviewer in REVIEWER_COLUMNS:
            note = row["reviewers"][reviewer]
            note_text = note["note"] or "(blank)"
            lines.append(
                f"- {reviewer}: explicit=`{note['explicit_tag']}`, "
                f"primary=`{note['primary_inferred_label']}`, "
                f"legacy=`{note['inferred_label']}`, "
                f"signal=`{note.get('review_signal', 'unlabeled')}`, "
                f"failures=`{','.join(note.get('failure_modes', [])) or 'none'}`, "
                f"positives=`{','.join(note.get('positive_signals', [])) or 'none'}`, "
                f"modifiers=`{','.join(note['modifiers']) or 'none'}`/"
                f"{note['inferred_confidence']}, "
                f"tag=`{note['tag']}` — {note_text}"
            )
        lines.append("")
    lines.extend(["## Disagreement Rows", ""])
    if summary["disagreement_rows"]:
        for row in summary["disagreement_rows"]:
            lines.append(
                f"- row {row['row']}: {row['title']} "
                f"({row['id']}) — {', '.join(row['tags'])}; "
                f"inferred={str(row.get('inferred', False)).lower()}"
            )
    else:
        lines.append("- none")
    return "\n".join(lines) + "\n"


def _default_run_date(rows: list[dict[str, str]]) -> str:
    for row in rows:
        value = _row_registered_at(row)
        if value:
            return value[:10]
    return datetime.now(UTC).date().isoformat()


def _write_summary(
    summary: dict[str, Any],
    *,
    markdown_path: Path,
    json_path: Path,
) -> ReviewFeedbackPaths:
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.write_text(_markdown(summary), encoding="utf-8")
    json_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return ReviewFeedbackPaths(markdown_path=markdown_path, json_path=json_path)


def _read_sheet_rows(config: GoogleSheetAppendConfig) -> list[dict[str, str]]:
    if not config.spreadsheet_id:
        raise ValueError("spreadsheet_id is required when --input-csv is not provided.")
    client = GoogleSheetsApiClient(
        credentials_path=config.service_account_json_path,
        auth_mode=config.auth_mode,
    )
    return _rows_from_values(
        client.get_values(config.spreadsheet_id, config.target_sheet_name)
    )


def render_review_feedback_summary(
    *,
    input_csv: Path | None = None,
    run_date: str | None = None,
    markdown_path: Path | None = None,
    json_path: Path | None = None,
    config: GoogleSheetAppendConfig | None = None,
) -> tuple[ReviewFeedbackPaths, dict[str, Any]]:
    loaded = config or load_append_config()
    rows = _rows_from_csv(input_csv) if input_csv else _read_sheet_rows(loaded)
    required_columns = [
        column
        for column in BUNDLE_REVIEW_SHEET_COLUMNS
        if column not in {"점수", "일시"}
    ]
    missing = [column for column in required_columns if rows and column not in rows[0]]
    if rows and "일시" not in rows[0] and "날짜" not in rows[0]:
        missing.append("일시")
    if missing:
        raise ValueError("Review board is missing columns: " + ", ".join(missing))
    date_value = run_date or _default_run_date(rows)
    summary = summarize_review_feedback(rows, run_date=date_value)
    paths_out = _write_summary(
        summary,
        markdown_path=markdown_path
        or paths.REPORTS_DIR / f"jibi_review_feedback_{date_value}.md",
        json_path=json_path
        or paths.REPORTS_DIR / f"jibi_review_feedback_{date_value}.json",
    )
    return paths_out, summary


def _history_key_from_row(row: dict[str, Any]) -> str:
    fingerprint = str(row.get("story_fingerprint") or "").strip()
    if fingerprint:
        return fingerprint
    review_id = str(row.get("ID") or row.get("id") or "").strip()
    if ":" in review_id:
        return review_id.rsplit(":", 1)[1]
    return review_id


def _domain(value: str) -> str:
    url = str(value or "").strip()
    if not url:
        return "unknown"
    parsed = urlparse(url)
    return parsed.netloc.lower().removeprefix("www.") or "unknown"


def _candidate_metadata_index(path: Path) -> dict[str, dict[str, str]]:
    if not path.exists():
        return {}
    index: dict[str, dict[str, str]] = {}
    for candidate in read_jsonl(path):
        urls = {
            str(candidate.get("seed_url") or ""),
            str(candidate.get("source_url_canonical") or ""),
        }
        metadata = {
            "source": str(candidate.get("source") or "").strip(),
            "source_id": str(candidate.get("source_id") or ""),
            "source_role": str(candidate.get("source_role_class") or "unknown"),
            "seed_type": str(candidate.get("seed_type") or "unknown"),
            "candidate_id": str(candidate.get("candidate_id") or ""),
        }
        for url in urls:
            key = canonicalize_url(url)
            if key:
                index.setdefault(key, metadata)
    return index


def _metadata_for_row(
    row: dict[str, str],
    candidate_index: dict[str, dict[str, str]],
) -> dict[str, str]:
    link = str(row.get("메인 링크") or "").strip()
    metadata = candidate_index.get(canonicalize_url(link), {})
    return {
        "source": metadata.get("source") or _domain(link),
        "source_id": metadata.get("source_id") or "",
        "source_role": metadata.get("source_role") or "unknown",
        "seed_type": metadata.get("seed_type") or "unknown",
        "candidate_id": metadata.get("candidate_id") or "",
    }


def _history_payload_rows(history_path: Path) -> list[dict[str, Any]]:
    if not history_path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in history_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        run_date = str(payload.get("run_date") or "").strip()
        snapshot_created_at = str(payload.get("created_at") or "").strip()
        for row in payload.get("rows", []):
            if not isinstance(row, dict):
                continue
            item = {str(key): str(value) for key, value in row.items()}
            item["일시"] = item.get("일시") or item.get("날짜") or run_date
            item["story_fingerprint"] = _history_key_from_row(item)
            item["_snapshot_created_at"] = snapshot_created_at
            item["_source_kind"] = "history"
            rows.append(item)
    return rows


def _csv_payload_rows(path: Path, *, source_kind: str = "current_csv") -> list[dict[str, Any]]:
    rows = [dict(row) for row in _rows_from_csv(path)]
    for row in rows:
        row["story_fingerprint"] = _history_key_from_row(row)
        row["_source_kind"] = source_kind
    return rows


def _review_tags_for_row(row: dict[str, Any]) -> dict[str, dict[str, str]]:
    return {
        reviewer: _note_payload(str(row.get(reviewer, "")))
        for reviewer in REVIEWER_COLUMNS
    }


def _has_reviewer_note(row: dict[str, Any]) -> bool:
    return any(str(row.get(reviewer) or "").strip() for reviewer in REVIEWER_COLUMNS)


def _empty_tag_counter() -> Counter[str]:
    return Counter({tag: 0 for tag in REVIEW_TAGS})


def _empty_inferred_label_counter() -> Counter[str]:
    return Counter({label: 0 for label in INFERRED_LABELS})


def _empty_primary_label_counter() -> Counter[str]:
    return Counter({label: 0 for label in PRIMARY_INFERRED_LABELS})


def _empty_modifier_counter() -> Counter[str]:
    return Counter({modifier: 0 for modifier in REVIEW_MODIFIERS})


def _dimension_feedback_summary(
    rows: list[dict[str, Any]],
    key_name: str,
) -> list[dict[str, Any]]:
    summary: dict[str, dict[str, Any]] = {}
    for row in rows:
        key = str(row.get(key_name) or "unknown")
        item = summary.setdefault(
            key,
            {
                "key": key,
                "rows": 0,
                "reviewed_rows": 0,
                "tag_counts": _empty_tag_counter(),
            },
        )
        item["rows"] += 1
        if _has_reviewer_note(row):
            item["reviewed_rows"] += 1
        for note in _review_tags_for_row(row).values():
            if note["note"]:
                item["tag_counts"][note["tag"]] += 1
    payload = []
    for item in summary.values():
        tag_counts = dict(item["tag_counts"])
        payload.append(
            {
                "key": item["key"],
                "rows": item["rows"],
                "reviewed_rows": item["reviewed_rows"],
                "tag_counts": tag_counts,
            }
        )
    payload.sort(
        key=lambda item: (
            -int(item["reviewed_rows"]),
            -int(item["rows"]),
            str(item["key"]),
        )
    )
    return payload


def _story_reappearance_summary(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        key = str(row.get("story_fingerprint") or "").strip()
        if key:
            grouped[key].append(row)
    payload: list[dict[str, Any]] = []
    for key, items in grouped.items():
        tag_counts = _empty_tag_counter()
        for row in items:
            for note in _review_tags_for_row(row).values():
                if note["note"]:
                    tag_counts[note["tag"]] += 1
        dates = sorted(
            {
                _row_date(item)
                for item in items
                if _row_date(item)
            }
        )
        payload.append(
            {
                "story_fingerprint": key,
                "appearances": len(items),
                "dates": dates,
                "titles": sorted(
                    {str(item.get("제목") or "") for item in items if item.get("제목")}
                )[:3],
                "tag_counts": dict(tag_counts),
            }
        )
    payload.sort(key=lambda item: (-int(item["appearances"]), item["story_fingerprint"]))
    return payload


def _strong_disagreements(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    disagreements: list[dict[str, Any]] = []
    for row in rows:
        tags = {
            note["tag"]
            for note in _review_tags_for_row(row).values()
            if note["note"]
        }
        if "seed" in tags and "reject" in tags:
            reason = "seed_vs_reject"
        elif "evidence" in tags and "reject" in tags:
            reason = "evidence_vs_reject"
        else:
            continue
        inferred = any(
            note["explicit_tag"] == "unlabeled"
            and note["tag"] not in {"unlabeled", "unclear"}
            for note in _review_tags_for_row(row).values()
            if note["note"]
        )
        disagreements.append(
            {
                "date": _row_date(row),
                "registered_at": _row_registered_at(row),
                "title": row.get("제목", ""),
                "id": row.get("ID", ""),
                "story_fingerprint": row.get("story_fingerprint", ""),
                "tags": sorted(tags),
                "reason": reason,
                "inferred": inferred,
            }
        )
    return disagreements


def _recommendations_from_dimension(
    dimension: str,
    rows: list[dict[str, Any]],
) -> list[dict[str, str]]:
    recommendations: list[dict[str, str]] = []
    for item in rows:
        tags = item["tag_counts"]
        negative = tags.get("reject", 0) + tags.get("needs", 0) + tags.get("unclear", 0)
        positive = tags.get("seed", 0) + tags.get("evidence", 0)
        if item["reviewed_rows"] == 0:
            continue
        if positive >= 2 and positive > negative:
            recommendations.append(
                {
                    "type": f"{dimension}_to_promote",
                    "target": str(item["key"]),
                    "reason": "seed/evidence feedback is stronger than reject/needs",
                }
            )
        elif negative >= 2 and negative >= positive:
            recommendations.append(
                {
                    "type": f"{dimension}_to_watch",
                    "target": str(item["key"]),
                    "reason": "reject/needs/unclear feedback dominates",
                }
            )
    return recommendations


def _feedback_recommendations(summary: dict[str, Any]) -> list[dict[str, str]]:
    recommendations: list[dict[str, str]] = []
    recommendations.extend(
        _recommendations_from_dimension("source", summary["source_feedback"])
    )
    recommendations.extend(
        _recommendations_from_dimension("source_role", summary["source_role_feedback"])
    )
    recommendations.extend(
        _recommendations_from_dimension("seed_type", summary["seed_type_feedback"])
    )
    for story in summary["story_reappearance"]:
        tags = story["tag_counts"]
        if story["appearances"] < 2:
            continue
        if tags.get("reject", 0):
            recommendations.append(
                {
                    "type": "story_bundle_rule_to_adjust",
                    "target": story["story_fingerprint"],
                    "reason": "reappearing story has reject feedback",
                }
            )
        elif tags.get("seed", 0) or tags.get("merge", 0):
            recommendations.append(
                {
                    "type": "story_bundle_to_track",
                    "target": story["story_fingerprint"],
                    "reason": "reappearing story has seed/merge feedback",
                }
            )
    return recommendations or [
        {
            "type": "insufficient_feedback",
            "target": "review_board",
            "reason": "collect more one-line reviewer notes before tuning",
        }
    ]


def summarize_review_history_calibration(
    rows: list[dict[str, Any]],
    *,
    run_date: str,
) -> dict[str, Any]:
    tag_counts = _empty_tag_counter()
    inferred_label_counts = _empty_inferred_label_counter()
    primary_label_counts = _empty_primary_label_counter()
    modifier_counts = _empty_modifier_counter()
    reviewer_completion: dict[str, dict[str, int]] = defaultdict(
        lambda: {reviewer: 0 for reviewer in REVIEWER_COLUMNS}
    )
    rows_by_date: Counter[str] = Counter()
    normalized_rows: list[dict[str, Any]] = []
    for row in rows:
        date_value = _row_date(row, run_date)
        rows_by_date[date_value] += 1
        _ = reviewer_completion[date_value]
        reviewer_notes = _review_tags_for_row(row)
        for reviewer, note in reviewer_notes.items():
            if note["note"]:
                reviewer_completion[date_value][reviewer] += 1
                tag_counts[note["tag"]] += 1
                inferred_label_counts[note["inferred_label"]] += 1
                primary_label_counts[note["primary_inferred_label"]] += 1
                for modifier in note["modifiers"]:
                    modifier_counts[modifier] += 1
        normalized_rows.append(
            {
                "date": date_value,
                "title": row.get("제목", ""),
                "score": row.get("점수", ""),
                "id": row.get("ID", ""),
                "story_fingerprint": row.get("story_fingerprint", ""),
                "source": row.get("source", "unknown"),
                "source_role": row.get("source_role", "unknown"),
                "seed_type": row.get("seed_type", "unknown"),
                "reviewers": reviewer_notes,
            }
        )
    summary = {
        "run_date": run_date,
        "generated_at": datetime.now(UTC).isoformat(),
        "total_rows": len(rows),
        "rows_by_date": dict(sorted(rows_by_date.items())),
        "reviewer_completion_by_date": dict(sorted(reviewer_completion.items())),
        "tag_counts": dict(tag_counts),
        "inferred_label_counts": dict(inferred_label_counts),
        "primary_label_counts": dict(primary_label_counts),
        "modifier_counts": dict(modifier_counts),
        "source_feedback": _dimension_feedback_summary(rows, "source"),
        "source_role_feedback": _dimension_feedback_summary(rows, "source_role"),
        "seed_type_feedback": _dimension_feedback_summary(rows, "seed_type"),
        "story_reappearance": _story_reappearance_summary(rows),
        "strong_disagreement_rows": _strong_disagreements(rows),
        "rows": normalized_rows,
    }
    summary["recommendations"] = _feedback_recommendations(summary)
    return summary


def _metadata_enriched_rows(
    rows: list[dict[str, Any]],
    *,
    candidates_path: Path,
) -> list[dict[str, Any]]:
    candidate_index = _candidate_metadata_index(candidates_path)
    enriched: list[dict[str, Any]] = []
    for row in rows:
        item = dict(row)
        metadata = _metadata_for_row(
            {str(key): str(value) for key, value in item.items()},
            candidate_index,
        )
        for key, value in metadata.items():
            current = str(item.get(key) or "").strip()
            if not current or current == "unknown":
                item[key] = value
        if not str(item.get("source_role") or "").strip():
            item["source_role"] = item.get("source_role_class") or "unknown"
        if not str(item.get("source_role_class") or "").strip():
            item["source_role_class"] = item.get("source_role") or "unknown"
        enriched.append(item)
    return enriched


def _feedback_table(rows: list[dict[str, Any]], label: str) -> list[str]:
    if not rows:
        return ["| none | 0 | 0 | 0 | 0 | 0 | 0 | 0 |"]
    lines = []
    for item in rows:
        tags = item["tag_counts"]
        lines.append(
            "| "
            + " | ".join(
                [
                    str(item["key"]),
                    str(item["rows"]),
                    str(item["reviewed_rows"]),
                    str(tags.get("seed", 0)),
                    str(tags.get("evidence", 0)),
                    str(tags.get("needs", 0)),
                    str(tags.get("reject", 0)),
                    str(tags.get("unlabeled", 0)),
                ]
            )
            + " |"
        )
    return lines or [f"| {label} | 0 | 0 | 0 | 0 | 0 | 0 | 0 |"]


def _history_markdown(summary: dict[str, Any]) -> str:
    lines = [
        f"# Jibi Feedback Calibration — {summary['run_date']}",
        "",
        f"- Total rows: {summary['total_rows']}",
        f"- Generated at: `{summary['generated_at']}`",
        "",
        "## Reviewer Completion By Date",
        "",
    ]
    for date_value, completion in summary["reviewer_completion_by_date"].items():
        total = summary["rows_by_date"].get(date_value, 0)
        counts = ", ".join(
            f"{reviewer}: {completion.get(reviewer, 0)}/{total}"
            for reviewer in REVIEWER_COLUMNS
        )
        lines.append(f"- {date_value}: {counts}")
    lines.extend(["", "## Tag Counts", ""])
    for tag in REVIEW_TAGS:
        lines.append(f"- {tag}: {summary['tag_counts'].get(tag, 0)}")
    lines.extend(["", "## Natural Review Inference Summary", ""])
    inferred_total = sum(summary.get("inferred_label_counts", {}).values())
    lines.append(f"- inferred_notes: {inferred_total}")
    lines.extend(["", "## Inferred Label Counts", ""])
    for label in INFERRED_LABELS:
        lines.append(f"- {label}: {summary.get('inferred_label_counts', {}).get(label, 0)}")
    lines.extend(["", "## Primary Label Counts", ""])
    for label in PRIMARY_INFERRED_LABELS:
        lines.append(f"- {label}: {summary.get('primary_label_counts', {}).get(label, 0)}")
    lines.extend(["", "## Modifier Counts", ""])
    for modifier in REVIEW_MODIFIERS:
        lines.append(f"- {modifier}: {summary.get('modifier_counts', {}).get(modifier, 0)}")
    for heading, key in [
        ("Source-Level Feedback Summary", "source_feedback"),
        ("Source-Role Feedback Summary", "source_role_feedback"),
        ("Seed-Type / Template Feedback Summary", "seed_type_feedback"),
    ]:
        lines.extend(
            [
                "",
                f"## {heading}",
                "",
                "| key | rows | reviewed_rows | seed | evidence | needs | reject | unlabeled |",
                "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
                *_feedback_table(summary[key], key),
            ]
        )
    lines.extend(
        [
            "",
            "## Story-Fingerprint Reappearance Summary",
            "",
            "| story_fingerprint | appearances | dates | seed | merge | reject | titles |",
            "| --- | ---: | --- | ---: | ---: | ---: | --- |",
        ]
    )
    for story in summary["story_reappearance"]:
        tags = story["tag_counts"]
        lines.append(
            "| "
            + " | ".join(
                [
                    str(story["story_fingerprint"]),
                    str(story["appearances"]),
                    ", ".join(story["dates"]),
                    str(tags.get("seed", 0)),
                    str(tags.get("merge", 0)),
                    str(tags.get("reject", 0)),
                    "; ".join(story["titles"]),
                ]
            )
            + " |"
        )
    lines.extend(["", "## Rows With Strong Disagreement", ""])
    if summary["strong_disagreement_rows"]:
        for row in summary["strong_disagreement_rows"]:
            lines.append(
                f"- {row['date']} `{row['story_fingerprint']}` "
                f"{row['title']} — {row['reason']} ({', '.join(row['tags'])}); "
                f"inferred={str(row.get('inferred', False)).lower()}"
            )
    else:
        lines.append("- none")
    lines.extend(["", "## Report-Only Recommendations", ""])
    for item in summary["recommendations"]:
        lines.append(f"- {item['type']}: `{item['target']}` — {item['reason']}")
    return "\n".join(lines) + "\n"


def _write_history_calibration(
    summary: dict[str, Any],
    *,
    markdown_path: Path,
    json_path: Path,
) -> ReviewHistoryCalibrationPaths:
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.write_text(_history_markdown(summary), encoding="utf-8")
    json_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return ReviewHistoryCalibrationPaths(markdown_path=markdown_path, json_path=json_path)


def render_review_history_calibration(
    *,
    history_path: Path = paths.JIBI_REVIEW_BOARD_HISTORY_JSONL,
    current_csv: Path | None = None,
    include_current_sheet: bool = False,
    run_date: str | None = None,
    candidates_path: Path = paths.JIBI_SCORED_CANDIDATES_JSONL,
    markdown_path: Path | None = None,
    json_path: Path | None = None,
    config: GoogleSheetAppendConfig | None = None,
) -> tuple[ReviewHistoryCalibrationPaths, dict[str, Any]]:
    loaded = config or load_append_config()
    rows: list[dict[str, Any]] = _history_payload_rows(history_path)
    if current_csv:
        rows.extend(_csv_payload_rows(current_csv))
    if include_current_sheet:
        rows.extend(_rows_from_values(_read_sheet_values(loaded)))
        for row in rows:
            row.setdefault("story_fingerprint", _history_key_from_row(row))
            row.setdefault("_source_kind", "current_sheet")
    date_value = run_date or datetime.now(UTC).date().isoformat()
    enriched_rows = _metadata_enriched_rows(rows, candidates_path=candidates_path)
    summary = summarize_review_history_calibration(enriched_rows, run_date=date_value)
    paths_out = _write_history_calibration(
        summary,
        markdown_path=markdown_path
        or paths.REPORTS_DIR / f"jibi_feedback_calibration_{date_value}.md",
        json_path=json_path
        or paths.REPORTS_DIR / f"jibi_feedback_calibration_{date_value}.json",
    )
    return paths_out, summary


def _read_sheet_values(config: GoogleSheetAppendConfig) -> list[list[str]]:
    if not config.spreadsheet_id:
        raise ValueError("spreadsheet_id is required for current sheet readback.")
    client = GoogleSheetsApiClient(
        credentials_path=config.service_account_json_path,
        auth_mode=config.auth_mode,
    )
    return client.get_values(config.spreadsheet_id, config.target_sheet_name)


@app.callback(invoke_without_command=True)
def main(
    input_csv: Annotated[
        Path | None,
        typer.Option("--input-csv", help="Local Jibi bundle review CSV to summarize."),
    ] = None,
    run_date: Annotated[
        str | None,
        typer.Option("--date", help="Feedback report date in YYYY-MM-DD."),
    ] = None,
    spreadsheet_id: Annotated[
        str | None,
        typer.Option("--spreadsheet-id", help="Target Google spreadsheet id."),
    ] = None,
    sheet_name: Annotated[
        str | None,
        typer.Option("--sheet-name", help="Review board sheet name."),
    ] = None,
    markdown_path: Annotated[
        Path | None,
        typer.Option("--output-md", help="Markdown report path."),
    ] = None,
    json_path: Annotated[
        Path | None,
        typer.Option("--output-json", help="JSON report path."),
    ] = None,
) -> None:
    loaded = load_append_config()
    config = GoogleSheetAppendConfig(
        spreadsheet_id=spreadsheet_id or loaded.spreadsheet_id,
        target_sheet_name=sheet_name or loaded.target_sheet_name,
        sheet_schema=loaded.sheet_schema,
        dry_run=True,
        auth_mode=loaded.auth_mode,
        service_account_json_path=loaded.service_account_json_path,
    )
    try:
        outputs, summary = render_review_feedback_summary(
            input_csv=input_csv,
            run_date=run_date,
            markdown_path=markdown_path,
            json_path=json_path,
            config=config,
        )
    except ValueError as exc:
        console.print(f"[red]Jibi review feedback summary failed: {exc}[/red]")
        raise typer.Exit(1) from exc
    console.print(
        "[green]Wrote Jibi review feedback summary "
        f"for {summary['total_rows']} rows to {outputs.markdown_path} and "
        f"{outputs.json_path}.[/green]"
    )


@history_app.callback(invoke_without_command=True)
def history_main(
    history_path: Annotated[
        Path,
        typer.Option("--history", help="Local review board history JSONL."),
    ] = paths.JIBI_REVIEW_BOARD_HISTORY_JSONL,
    current_csv: Annotated[
        Path | None,
        typer.Option("--current-csv", help="Optional current review board CSV."),
    ] = None,
    include_current_sheet: Annotated[
        bool,
        typer.Option(
            "--include-current-sheet/--no-include-current-sheet",
            help="Read the live Jibi sheet and include it in the calibration report.",
        ),
    ] = False,
    run_date: Annotated[
        str | None,
        typer.Option("--date", help="Calibration report date in YYYY-MM-DD."),
    ] = None,
    candidates_path: Annotated[
        Path,
        typer.Option("--candidates", help="Scored candidates JSONL for source metadata."),
    ] = paths.JIBI_SCORED_CANDIDATES_JSONL,
    spreadsheet_id: Annotated[
        str | None,
        typer.Option("--spreadsheet-id", help="Target Google spreadsheet id."),
    ] = None,
    sheet_name: Annotated[
        str | None,
        typer.Option("--sheet-name", help="Review board sheet name."),
    ] = None,
    markdown_path: Annotated[
        Path | None,
        typer.Option("--output-md", help="Markdown report path."),
    ] = None,
    json_path: Annotated[
        Path | None,
        typer.Option("--output-json", help="JSON report path."),
    ] = None,
) -> None:
    loaded = load_append_config()
    config = GoogleSheetAppendConfig(
        spreadsheet_id=spreadsheet_id or loaded.spreadsheet_id,
        target_sheet_name=sheet_name or loaded.target_sheet_name,
        sheet_schema=loaded.sheet_schema,
        dry_run=True,
        auth_mode=loaded.auth_mode,
        service_account_json_path=loaded.service_account_json_path,
    )
    try:
        outputs, summary = render_review_history_calibration(
            history_path=history_path,
            current_csv=current_csv,
            include_current_sheet=include_current_sheet,
            run_date=run_date,
            candidates_path=candidates_path,
            markdown_path=markdown_path,
            json_path=json_path,
            config=config,
        )
    except ValueError as exc:
        console.print(f"[red]Jibi feedback calibration failed: {exc}[/red]")
        raise typer.Exit(1) from exc
    console.print(
        "[green]Wrote Jibi feedback calibration report "
        f"for {summary['total_rows']} rows to {outputs.markdown_path} and "
        f"{outputs.json_path}.[/green]"
    )


if __name__ == "__main__":
    app()
