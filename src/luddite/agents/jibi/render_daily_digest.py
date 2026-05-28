"""Render jibi scored candidates into a daily Markdown digest and CSV preview."""

from __future__ import annotations

import csv
import hashlib
import json
import os
import re
from collections import Counter
from datetime import date, datetime
from pathlib import Path
from typing import Annotated, Any
from urllib.parse import urlparse
from zoneinfo import ZoneInfo

import typer
from rich.console import Console

from luddite import paths
from luddite.agents.jibi.append_to_sheet import (
    BUNDLE_REVIEW_SHEET_COLUMNS,
    REVIEWER_COLUMNS,
    SHEET_COLUMNS,
)
from luddite.agents.jibi.review_board_copy import (
    build_review_board_copy,
    review_board_title,
)
from luddite.agents.jibi.review_feedback import infer_review_feedback
from luddite.agents.jibi.seed_quality import analyze_so_what
from luddite.utils.jsonl import read_jsonl
from luddite.utils.urls import canonicalize_url

app = typer.Typer(no_args_is_help=False)
console = Console()

ACTION_LABELS = {
    "send_to_anny": "즉시 스토리라인 후보",
    "gather_more_evidence": "자료 보강 필요",
    "editorial_review": "사람 검토 필요",
    "keep_for_later": "킵 후보",
    "reject": "제외/거절",
    "blocked_policy": "제외/거절",
}
TOP_ACTIONS = {"send_to_anny", "gather_more_evidence", "editorial_review", "keep_for_later"}
EXCLUDED_ACTIONS = {"reject", "blocked_policy"}
TOP_EXCLUDED_QUALITY_FLAGS = {
    "sports_only",
    "accident_single_event",
    "pure_place_listing",
    "generic_local_incident",
    "stale_item",
    "policy_release_evidence_default",
    "contest_or_campaign_bulletin",
    "event_or_demonstration_only",
    "narrow_market_track_record",
}
DEFAULT_TOP_MIN_SCORE = 35
DEFAULT_REVIEW_BOARD_LIMIT = 10
DEFAULT_BUNDLE_NEAR_MISS_LIMIT = 10
KST = ZoneInfo("Asia/Seoul")
DEFAULT_SOURCE_ROLE_TOP_CAPS = {
    "research_note": 3,
    "policy_release": 2,
    "public_wire": 3,
    "academic_explainer": 2,
    "market_wire": 1,
    "section_news": 3,
}
BOARD_SCORE_PROMO_FLAGS = {
    "contest_or_campaign_bulletin",
    "event_or_demonstration_only",
    "meeting_or_coordination_only",
    "product_or_certification_promo",
    "narrow_market_track_record",
    "policy_release_announcement_only",
}
BOARD_SCORE_MISMATCH_WARNING_TERMS = {
    "mismatch",
    "source mismatch",
    "cluster mismatch",
    "매칭이 흔들",
    "원문 매칭",
    "source/cluster",
}
BOARD_SCORE_TOPIC_GROUPS = {
    "delivery_fee": {"무료배달", "배달앱", "배달비", "수수료", "업주", "점주"},
    "notion_ai": {"노션", "notion", "업무자동화", "개발자 플랫폼"},
    "asset_tokenization": {"자산 토큰화", "토큰화", "rwa", "sto", "조각투자"},
}
BOARD_SCORE_MARKET_RISK_TERMS = {
    "단일종목",
    "레버리지",
    "etf",
    "ipo",
    "주주배정",
    "유상증자",
    "공모주",
    "수요예측",
    "상장",
    "주가",
}
BOARD_SCORE_PROMO_TEXT_TERMS = {
    "모집",
    "운영계획",
    "소개",
    "출시",
    "공개",
    "협력",
    "업무협약",
    "mou",
    "양성",
    "인증",
    "수상",
    "신제품",
}
BOARD_SCORE_SYSTEM_TOPIC_TERMS = {
    "고용",
    "임금",
    "노동",
    "보험",
    "주거",
    "부동산",
    "공급",
    "우주산업",
    "규제",
    "사각지대",
    "물가",
    "전력",
    "교육",
    "의료",
}
BOARD_SCORE_SPORTS_PRIMARY_TERMS = {
    "스포츠",
    "축구",
    "야구",
    "농구",
    "football",
    "premier league",
    "manchester united",
    "fifa",
    "월드컵",
    "올림픽",
    "챔피언스리그",
    "epl",
}
BOARD_SCORE_SPORTS_HOOK_TERMS = {
    "가격",
    "티켓",
    "중계권",
    "광고",
    "스폰서",
    "수수료",
    "이벤트",
    "관광",
    "도시",
    "경제",
}
BOARD_SCORE_AI_GRAND_DISCOURSE_TERMS = {
    "ai 저작권",
    "저작권 논쟁",
    "허위 정보",
    "허위정보",
    "거대 담론",
    "거대담론",
}
BOARD_SCORE_CASUAL_AI_TERMS = {
    "방구석 여행",
    "여행 브이로그",
    "편하게 즐",
    "ai 영상",
}
BOARD_SCORE_PRODUCT_REVIEW_TERMS = {
    "best fans",
    "tried and tested",
    "best air conditioners",
    "best air conditioning",
    "product review",
    "shopping guide",
    "buying guide",
}
BOARD_SCORE_GRADE_CUTS = {
    "A": 90,
    "B": 60,
    "C": 40,
}
GENERIC_WHY_PATTERNS = {
    "수동 후보로 들어온 소재",
    "공급망, 인프라, 규제, 산업 전환 중 어느 축",
    "사건 자체보다 배경",
}
SPECIFIC_TOP_SEED_TYPES = {
    "productive_finance_policy",
    "industrial_policy_rnd",
    "single_company_financing",
    "market_rate_stress",
    "ai_knowledge_institution",
    "infrastructure_project_failure",
    "climate_policy_conflict",
    "cost_asymmetry",
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
PUBLIC_AI_SEED_TYPES = {
    "public_ai_governance",
    "public_ai_enforcement",
    "workplace_ai_transition",
    "healthcare_operations_ai",
}
PLATFORM_FEE_TERMS = {
    "쿠팡이츠",
    "무료배달",
    "무료 배달",
    "배달비",
    "수수료",
    "업주",
    "가맹점",
    "플랫폼",
}
PLATFORM_FEE_STRONG_TERMS = PLATFORM_FEE_TERMS - {"플랫폼"}
POLICY_STATUS_EVIDENCE_TERMS = {
    "현황",
    "신청·지급",
    "신청 지급",
    "지급 현황",
    "보도참고자료",
    "기준",
}


def _digest_date(value: str | None = None) -> str:
    return value or date.today().isoformat()


def _review_board_registered_at(value: str | None = None) -> str:
    env_value = os.environ.get("JIBI_REVIEW_BOARD_REGISTERED_AT")
    if value and value.strip():
        return value.strip()
    if env_value and env_value.strip():
        return env_value.strip()
    return datetime.now(KST).strftime("%Y-%m-%d %H:%M")


def _env_int(name: str, default: int) -> int:
    value = os.environ.get(name)
    if value is None or not value.strip():
        return default
    try:
        parsed = int(value)
    except ValueError:
        return default
    return max(parsed, 0)


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.environ.get(name)
    if value is None or not value.strip():
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def _score_band(candidate: dict[str, Any]) -> str:
    return str(candidate.get("final_grade") or "C")


def top_candidates(
    candidates: list[dict[str, Any]],
    limit: int = 10,
    max_per_source: int = 3,
    min_score: float = DEFAULT_TOP_MIN_SCORE,
    source_role_caps: dict[str, int] | None = DEFAULT_SOURCE_ROLE_TOP_CAPS,
) -> list[dict[str, Any]]:
    eligible = _top_eligible_candidates(candidates, min_score=min_score)
    details = _select_top_with_role_cap_details(
        eligible,
        limit=limit,
        max_per_source=max_per_source,
        source_role_caps=source_role_caps,
    )
    return details["selected"]


def _ranked_eligible(eligible: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        eligible,
        key=lambda item: (
            item.get("scores", {}).get("total_score", 0),
            item.get("scores", {}).get("broadcast_potential_proxy", 0),
        ),
        reverse=True,
    )


def _candidate_source(candidate: dict[str, Any]) -> str:
    return str(candidate.get("source") or candidate.get("source_id") or "unknown")


def _candidate_role(candidate: dict[str, Any]) -> str:
    return str(candidate.get("source_role_class") or "unknown")


def _select_top_with_role_cap_details(
    eligible: list[dict[str, Any]],
    *,
    limit: int = 10,
    max_per_source: int = 3,
    source_role_caps: dict[str, int] | None = DEFAULT_SOURCE_ROLE_TOP_CAPS,
) -> dict[str, Any]:
    ranked = _ranked_eligible(eligible)
    selected: list[dict[str, Any]] = []
    selected_ids: set[str] = set()
    source_counts: dict[str, int] = {}
    role_counts: dict[str, int] = {}
    role_cap_blocked: list[tuple[dict[str, Any], str]] = []
    backfilled: list[dict[str, Any]] = []
    for candidate in ranked:
        candidate_id = str(candidate.get("candidate_id"))
        source = _candidate_source(candidate)
        if max_per_source > 0 and source_counts.get(source, 0) >= max_per_source:
            continue
        role = _candidate_role(candidate)
        cap = source_role_caps.get(role) if source_role_caps else None
        if cap is not None and cap > 0 and role_counts.get(role, 0) >= cap:
            role_cap_blocked.append(
                (candidate, f"source_role_cap_reached={role}:{cap}")
            )
            continue
        selected.append(candidate)
        selected_ids.add(candidate_id)
        source_counts[source] = source_counts.get(source, 0) + 1
        role_counts[role] = role_counts.get(role, 0) + 1
        if len(selected) >= limit:
            break
    if len(selected) < limit and role_cap_blocked:
        for candidate, _reason in role_cap_blocked:
            candidate_id = str(candidate.get("candidate_id"))
            if candidate_id in selected_ids:
                continue
            source = _candidate_source(candidate)
            if max_per_source > 0 and source_counts.get(source, 0) >= max_per_source:
                continue
            role = _candidate_role(candidate)
            selected.append(candidate)
            selected_ids.add(candidate_id)
            source_counts[source] = source_counts.get(source, 0) + 1
            role_counts[role] = role_counts.get(role, 0) + 1
            backfilled.append(candidate)
            if len(selected) >= limit:
                break
    return {
        "selected": selected,
        "role_cap_blocked": [
            (candidate, reason)
            for candidate, reason in role_cap_blocked
            if str(candidate.get("candidate_id")) not in selected_ids
        ],
        "backfilled": backfilled,
        "cap_backfill_used": bool(backfilled),
        "source_role_caps": source_role_caps or {},
    }


def _select_top_from_eligible(
    eligible: list[dict[str, Any]],
    *,
    limit: int = 10,
    max_per_source: int = 3,
    source_role_caps: dict[str, int] | None = DEFAULT_SOURCE_ROLE_TOP_CAPS,
) -> list[dict[str, Any]]:
    details = _select_top_with_role_cap_details(
        eligible,
        limit=limit,
        max_per_source=max_per_source,
        source_role_caps=source_role_caps,
    )
    return details["selected"]


def _passes_top_quality_gate(candidate: dict[str, Any]) -> bool:
    return not _top_quality_gate_failures(candidate)


def _top_quality_gate_failures(
    candidate: dict[str, Any],
    *,
    ignore_excluded_quality_flags: set[str] | None = None,
) -> list[str]:
    failures: list[str] = []
    flags = set(candidate.get("quality_flags", []))
    failure_modes = set(candidate.get("failure_modes", []))
    ignored_flags = ignore_excluded_quality_flags or set()
    excluded_flags = sorted(TOP_EXCLUDED_QUALITY_FLAGS.intersection(flags - ignored_flags))
    if excluded_flags:
        failures.append(f"excluded_quality_flags={','.join(excluded_flags)}")
    if candidate.get("near_duplicate_role") in {"duplicate", "supporting_source"}:
        failures.append(f"near_duplicate_role={candidate.get('near_duplicate_role')}")
    if "single_company_frame" in flags and "broader_industry_bridge" not in flags:
        failures.append("single_company_without_broader_bridge")
    if "market_rate_stress" in flags and "broader_macro_angle" not in flags:
        failures.append("market_rate_without_macro_bridge")
    story_role = str(candidate.get("story_role") or "")
    if story_role in {
        "evidence_for_larger_story",
        "background_reference",
        "demote_or_reject",
    }:
        failures.append(f"story_role_not_top_seed={story_role}")
    seed_quality = str(candidate.get("seed_quality_classification") or "")
    if not story_role and seed_quality in {"evidence_only", "reject_or_downrank"}:
        failures.append(f"seed_quality_not_top_seed={seed_quality}")
    seed_type = str(candidate.get("seed_type") or "other")
    if seed_type not in SPECIFIC_TOP_SEED_TYPES and _has_generic_why(candidate):
        failures.append("generic_why_for_unspecific_seed_type")
    if (
        "political_sensitivity" in candidate.get("risk_flags", [])
        and "live_news_volatility" in failure_modes
    ):
        failures.append("live_political_volatility")
    return failures


def _total_score(candidate: dict[str, Any]) -> float:
    return float(candidate.get("scores", {}).get("total_score", 0) or 0)


def _top_eligible_candidates(
    candidates: list[dict[str, Any]],
    min_score: float = DEFAULT_TOP_MIN_SCORE,
) -> list[dict[str, Any]]:
    return [
        candidate
        for candidate in candidates
        if candidate.get("recommended_action", "keep_for_later") in TOP_ACTIONS
        and _passes_top_quality_gate(candidate)
        and candidate.get("final_grade") != "D"
        and _total_score(candidate) >= min_score
    ]


def _has_generic_why(candidate: dict[str, Any]) -> bool:
    specificity = candidate.get("story_specificity")
    if isinstance(specificity, dict) and specificity.get("generic_why_detected"):
        return True
    why = str(candidate.get("why_interesting") or "")
    return any(pattern in why for pattern in GENERIC_WHY_PATTERNS)


def excluded_candidates(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        [
            candidate
            for candidate in candidates
            if candidate.get("recommended_action") in EXCLUDED_ACTIONS
        ],
        key=lambda item: item.get("scores", {}).get("total_score", 0),
        reverse=True,
    )


def _action_counts(candidates: list[dict[str, Any]]) -> dict[str, int]:
    counts = {action: 0 for action in ACTION_LABELS}
    for candidate in candidates:
        action = candidate.get("recommended_action", "keep_for_later")
        counts[action] = counts.get(action, 0) + 1
    return counts


def _bullet_lines(values: list[str] | None, fallback: list[str]) -> list[str]:
    items = [str(value).strip() for value in values or [] if str(value).strip()]
    return items or fallback


def _slideability_label(candidate: dict[str, Any]) -> str:
    slideability = candidate.get("slideability")
    if not isinstance(slideability, dict):
        return "low / -"
    proof = "+".join(slideability.get("likely_proof_object_types", [])[:3]) or "-"
    return f"{slideability.get('visualizability', 'low')} / {proof}"


def _slideability_risks(candidate: dict[str, Any]) -> str:
    slideability = candidate.get("slideability")
    if not isinstance(slideability, dict):
        return "-"
    return ", ".join(slideability.get("risks", [])) or "-"


def _bundle_title_list(
    records: list[dict[str, Any]],
    *,
    max_titles: int = 4,
) -> list[str]:
    lines: list[str] = []
    for index, record in enumerate(records, start=1):
        primary = record.get("primary_title") or "primary 없음"
        supporting_titles = record.get("supporting_titles") or []
        evidence_titles = record.get("evidence_titles") or []
        extras = [*supporting_titles, *evidence_titles]
        extra_text = "; ".join(str(title) for title in extras[:max_titles]) or "-"
        lines.extend(
            [
                f"### Bundle {index}. {record['bundle_title']}",
                "",
                (
                    f"- type: {record['bundle_type']} / "
                    f"action: {record['suggested_operator_action']}"
                ),
                f"- primary: {primary}",
                f"- supporting/evidence: {extra_text}",
                f"- why: {record['why_bundle']}",
                "",
            ]
        )
    return lines


def render_markdown(
    candidates: list[dict[str, Any]],
    digest_date: str,
    excluded: list[dict[str, Any]] | None = None,
    all_candidates: list[dict[str, Any]] | None = None,
) -> str:
    excluded = excluded or []
    counts = _action_counts(all_candidates or [*candidates, *excluded])
    excluded_count = counts.get("reject", 0) + counts.get("blocked_policy", 0)
    lines = [
        f"# Luddite Daily Digest — {digest_date}",
        "",
        (
            "Local/manual + RSS-ingest MVP digest. No LLM, 24/7 RSS collector, "
            "Google Sheet append, or Slack bot was used."
        ),
        "",
        "## 오늘의 추천",
        "",
        f"- Top Candidates: {len(candidates)}개",
        f"- 즉시 스토리라인 후보: {counts.get('send_to_anny', 0)}개",
        f"- 자료 보강 후보: {counts.get('gather_more_evidence', 0)}개",
        f"- 사람 검토 후보: {counts.get('editorial_review', 0)}개",
        f"- 킵 후보: {counts.get('keep_for_later', 0)}개",
        f"- 제외/거절: {excluded_count}개",
        "",
        "## Story Bundles",
        "",
        *_bundle_title_list(
            _story_bundle_records(
                all_candidates or candidates,
                candidates,
                near_miss_limit=0,
            )
        ),
        "",
        "## Top Candidates",
        "",
    ]
    if not candidates:
        lines.append("No top candidates available.")
        if excluded:
            lines.extend(["", "## Excluded / Rejected", ""])
            for candidate in excluded:
                reason = candidate.get("blocked_reason") or ", ".join(
                    candidate.get("risk_flags", [])
                )
                lines.append(
                    f"- {candidate['title']}: {candidate.get('recommended_action', 'reject')} "
                    f"({reason or 'not suitable for digest'})"
                )
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
                    f"`{_score_band(candidate)} · "
                    f"{candidate.get('recommended_action', 'keep_for_later')} · "
                    f"{candidate.get('risk_level', 'medium')} risk · "
                    f"{scores.get('total_score', 0)}`"
                ),
                "",
                f"Source / Link: {candidate['source']} / {candidate['seed_url']}",
                "",
                "왜 보나:",
                f"  - {candidate.get('why_interesting', '')}",
                "",
                "확장:",
                *[f"  - {item}" for item in expansions[:3]],
                "",
                "필요:",
                *[f"  - {item}" for item in evidence_needed[:3]],
                "",
                f"Slideability: {_slideability_label(candidate)}",
                "First slide idea: "
                f"{candidate.get('slideability', {}).get('first_slide_idea', '-')}",
                f"Visual risks: {_slideability_risks(candidate)}",
                "",
                f"Risk flags: {risk_flags}",
                "",
            ]
        )
    if excluded:
        lines.extend(["## Excluded / Rejected", ""])
        for candidate in excluded:
            reason = candidate.get("blocked_reason") or ", ".join(candidate.get("risk_flags", []))
            lines.append(
                f"- {candidate['title']}: {candidate.get('recommended_action', 'reject')} "
                f"({reason or 'not suitable for digest'})"
            )
    return "\n".join(lines)


def write_sheet_preview(path: Path, candidates: list[dict[str, Any]], digest_date: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = SHEET_COLUMNS
    with path.open("w", encoding="utf-8-sig", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        for rank, candidate in enumerate(candidates, start=1):
            source_url_canonical = candidate.get("source_url_canonical") or canonicalize_url(
                str(candidate.get("seed_url", ""))
            )
            slideability = candidate.get("slideability") or {}
            writer.writerow(
                {
                    "digest_date": digest_date,
                    "collected_at": candidate.get("collected_at", ""),
                    "last_seen_at": candidate.get("last_seen_at")
                    or candidate.get("collected_at", ""),
                    "jibi_id": candidate["candidate_id"],
                    "duplicate_key": candidate.get("duplicate_key") or source_url_canonical,
                    "source_url_canonical": source_url_canonical,
                    "rank": rank,
                    "status": "new",
                    "주제명": candidate["title"],
                    "링크": candidate["seed_url"],
                    "출처": candidate["source"],
                    "source_type": candidate.get("source_type", ""),
                    "jibi_grade": _score_band(candidate),
                    "total_score": candidate.get("scores", {}).get("total_score", 0),
                    "recommended_action": candidate.get("recommended_action", "keep_for_later"),
                    "risk_level": candidate.get("risk_level", "medium"),
                    "risk_flags": ",".join(candidate.get("risk_flags", [])),
                    "why_interesting": candidate.get("why_interesting", ""),
                    "possible_expansions": " | ".join(candidate.get("possible_expansions", [])),
                    "evidence_needed": " | ".join(candidate.get("evidence_needed", [])),
                    "slideability_score": slideability.get("score", ""),
                    "slideability": _slideability_label(candidate),
                    "first_slide_idea": slideability.get("first_slide_idea", ""),
                    "likely_proof_object_types": " | ".join(
                        slideability.get("likely_proof_object_types", [])
                    ),
                    "visual_risks": " | ".join(slideability.get("risks", [])),
                    "중복후보": "",
                    "reviewer": "",
                    "review_result": "",
                    "promoted_to_topic_finding": "",
                    "notes": candidate.get("blocked_reason") or "",
                }
            )


def write_bundle_review_sheet_preview(
    path: Path,
    candidates: list[dict[str, Any]],
    top: list[dict[str, Any]],
    digest_date: str,
    *,
    review_board_limit: int = DEFAULT_REVIEW_BOARD_LIMIT,
    bundle_near_miss_limit: int = DEFAULT_BUNDLE_NEAR_MISS_LIMIT,
    review_history_path: Path = paths.JIBI_REVIEW_BOARD_HISTORY_JSONL,
    registered_at: str | None = None,
    syuka_similarity_report_path: Path | None = None,
    editorial_overrides_path: Path | None = None,
    allow_reviewed_candidates: bool | None = None,
    use_board_score: bool | None = None,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = BUNDLE_REVIEW_SHEET_COLUMNS
    candidate_by_id = {
        str(candidate.get("candidate_id")): candidate
        for candidate in candidates
        if candidate.get("candidate_id")
    }
    resolved_review_history_path = _effective_review_history_path(
        board_csv_path=path,
        review_history_path=review_history_path,
    )
    history_index = _load_review_history_index(resolved_review_history_path)
    syuka_similarity_index = _load_syuka_similarity_index(syuka_similarity_report_path)
    resolved_editorial_overrides_path = _effective_editorial_overrides_path(
        board_csv_path=path,
        run_date=digest_date,
        editorial_overrides_path=editorial_overrides_path,
    )
    editorial_overrides = _load_editorial_overrides(resolved_editorial_overrides_path)
    registered_at_value = _review_board_registered_at(registered_at)
    allow_reviewed = (
        allow_reviewed_candidates
        if allow_reviewed_candidates is not None
        else _env_bool("JIBI_ALLOW_REVIEWED_CANDIDATES", False)
    )
    use_board_score_value = (
        use_board_score
        if use_board_score is not None
        else _env_bool("JIBI_USE_BOARD_SCORE", False)
    )
    second_search_index = _load_second_search_intake_index(paths.REPORTS_DIR)
    all_bundle_records = _story_bundle_records(
        candidates,
        top,
        near_miss_limit=max(bundle_near_miss_limit, review_board_limit * 5),
    )
    bundle_records, suppressed_records, board_selection_report = _select_review_board_records(
        all_bundle_records,
        history_index,
        candidate_by_id=candidate_by_id,
        editorial_overrides=editorial_overrides,
        syuka_similarity_index=syuka_similarity_index,
        second_search_index=second_search_index,
        digest_date=digest_date,
        review_board_limit=review_board_limit,
        allow_reviewed_candidates=allow_reviewed,
        use_board_score=use_board_score_value,
    )
    metadata_rows: list[dict[str, Any]] = []
    with path.open("w", encoding="utf-8-sig", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        for record in bundle_records:
            primary_id = str(record.get("primary_candidate_id") or "")
            representative_id = primary_id
            if not representative_id:
                representative_id = next(
                    iter(
                        [
                            *record.get("supporting_candidate_ids", []),
                            *record.get("evidence_candidate_ids", []),
                        ]
                    ),
                    "",
                )
            representative = candidate_by_id.get(representative_id, {})
            fit = ""
            reason = str(record["why_bundle"])
            if representative:
                fit, reason, _action = _storyline_fit_classification(
                    representative,
                    candidates,
                )
            history_status = _record_history_status(record, history_index)
            primary_title = record.get("primary_title") or representative.get("title") or ""
            review_item_id = f"{digest_date}:{record['story_bundle_id']}"
            review_title = _human_review_title(
                record,
                representative,
                str(primary_title),
            )
            sub_links = _related_bundle_links(record, candidate_by_id, limit=3)
            jibi_judgment = _bundle_judgment(record, fit)
            joined_reason = _join_distinct_reason(str(record["why_bundle"]), reason)
            syuka_similarity = _syuka_similarity_for_record(
                record,
                representative,
                syuka_similarity_index,
            )
            override = _editorial_override_for_row(
                editorial_overrides,
                review_item_id=review_item_id,
                story_fingerprint=str(record.get("story_fingerprint") or ""),
            )
            mismatch_reasons = _board_mismatch_reasons(record, representative, override)
            board_score = _board_score_info(
                record=record,
                representative=representative,
                history_rows=_reviewed_history_rows_for_record(record, history_index),
                mismatch_reasons=mismatch_reasons,
                syuka_similarity=syuka_similarity,
                second_search=_second_search_for_record(record, second_search_index),
            )
            row = _bundle_review_row(
                digest_date=digest_date,
                registered_at=registered_at_value,
                review_item_id=review_item_id,
                review_title=review_title,
                candidate=representative,
                candidate_title=primary_title,
                jibi_judgment=jibi_judgment,
                reason=joined_reason,
                sub_links=sub_links,
                related_titles=_related_bundle_titles(record),
                record=record,
                history_status=history_status,
                syuka_similarity=syuka_similarity,
                board_score=board_score,
            )
            auto_title = str(row.get("제목") or "")
            auto_description = str(row.get("설명") or "")
            _apply_editorial_override(row, override)
            writer.writerow(row)
            metadata_rows.append(
                _bundle_review_metadata_row(
                    row=row,
                    record=record,
                    candidate=representative,
                    review_item_id=review_item_id,
                    registered_at=registered_at_value,
                    run_date=digest_date,
                    sub_links=sub_links,
                    syuka_similarity=syuka_similarity,
                    auto_title=auto_title,
                    auto_description=auto_description,
                    editorial_override=override,
                    board_score=board_score,
                )
            )
    _write_reviewed_candidate_guard_report(
        digest_date=digest_date,
        selected=bundle_records,
        suppressed=suppressed_records,
        allow_reviewed_candidates=allow_reviewed,
        history_index=history_index,
        path=_reviewed_candidate_guard_report_path(path, digest_date),
    )
    _write_board_score_report(
        digest_date=digest_date,
        selected=bundle_records,
        candidates=candidates,
        candidate_by_id=candidate_by_id,
        selection_report=board_selection_report,
        history_index=history_index,
        syuka_similarity_index=syuka_similarity_index,
        second_search_index=second_search_index,
        path=_board_score_report_path(path, digest_date),
    )
    _write_bundle_review_metadata(
        _bundle_review_metadata_path(path),
        rows=metadata_rows,
        digest_date=digest_date,
        registered_at=registered_at_value,
    )
    _write_editorial_override_template(
        _editorial_override_template_path(digest_date),
        rows=metadata_rows,
        digest_date=digest_date,
    )


def write_alternate_review_board_outputs(
    path: Path,
    report_path: Path,
    candidates: list[dict[str, Any]],
    top: list[dict[str, Any]],
    digest_date: str,
    *,
    review_board_limit: int = DEFAULT_REVIEW_BOARD_LIMIT,
    bundle_near_miss_limit: int = 50,
    review_history_path: Path = paths.JIBI_REVIEW_BOARD_HISTORY_JSONL,
    current_board_csv_path: Path | None = None,
    include_reviewed: bool = False,
    registered_at: str | None = None,
    syuka_similarity_report_path: Path | None = None,
) -> tuple[Path, Path, Path]:
    """Write a second review-board batch without touching the live Jibi sheet."""

    path.parent.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    candidate_by_id = {
        str(candidate.get("candidate_id")): candidate
        for candidate in candidates
        if candidate.get("candidate_id")
    }
    history_index = _load_review_history_index(review_history_path)
    syuka_similarity_index = _load_syuka_similarity_index(syuka_similarity_report_path)
    current_csv = current_board_csv_path or path.with_name(
        f"{digest_date}_bundle_review_sheet.csv"
    )
    current_keys = _current_board_exclusion_keys(current_csv)
    reviewed_keys = set() if include_reviewed else _reviewed_history_exclusion_keys(history_index)
    registered_at_value = _review_board_registered_at(registered_at)
    records = _story_bundle_records(
        candidates,
        [],
        near_miss_limit=max(bundle_near_miss_limit, review_board_limit * 5),
    )
    selected: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    for record in records:
        keys = _record_exclusion_keys(record)
        reasons: list[str] = []
        if keys.intersection(current_keys):
            reasons.append("current_board")
        if keys.intersection(reviewed_keys):
            reasons.append("reviewed_history")
        if reasons:
            skipped.append({"record": record, "reasons": reasons})
            continue
        selected.append(record)
        if len(selected) >= review_board_limit:
            break

    metadata_rows: list[dict[str, Any]] = []
    with path.open("w", encoding="utf-8-sig", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=BUNDLE_REVIEW_SHEET_COLUMNS)
        writer.writeheader()
        for record in selected:
            representative = _record_representative_candidate(record, candidate_by_id) or {}
            fit, reason, _action = ("", str(record["why_bundle"]), "")
            if representative:
                fit, reason, _action = _storyline_fit_classification(
                    representative,
                    candidates,
                )
            review_item_id = f"{digest_date}:alt:{record['story_bundle_id']}"
            primary_title = record.get("primary_title") or representative.get("title") or ""
            syuka_similarity = _syuka_similarity_for_record(
                record,
                representative,
                syuka_similarity_index,
            )
            row = _bundle_review_row(
                digest_date=digest_date,
                registered_at=registered_at_value,
                review_item_id=review_item_id,
                review_title=_human_review_title(record, representative, str(primary_title)),
                candidate=representative,
                candidate_title=str(primary_title),
                jibi_judgment=_bundle_judgment(record, fit),
                reason=_join_distinct_reason(str(record["why_bundle"]), reason),
                sub_links=_related_bundle_links(record, candidate_by_id, limit=3),
                related_titles=_related_bundle_titles(record),
                record=record,
                history_status="alternate_batch",
                syuka_similarity=syuka_similarity,
            )
            writer.writerow(row)
            metadata = _bundle_review_metadata_row(
                row=row,
                record=record,
                candidate=representative,
                review_item_id=review_item_id,
                registered_at=registered_at_value,
                run_date=digest_date,
                sub_links=str(row.get("서브 링크") or ""),
                syuka_similarity=syuka_similarity,
            )
            metadata["alternate_selection_reason"] = "excluded_current_or_reviewed_primary_batch"
            metadata["why_not_primary_board"] = _alternate_why_not_primary(
                representative,
                top,
            )
            metadata_rows.append(metadata)

    metadata_path = _bundle_review_metadata_path(path)
    _write_bundle_review_metadata(
        metadata_path,
        rows=metadata_rows,
        digest_date=digest_date,
        registered_at=registered_at_value,
    )
    report_path.write_text(
        _alternate_review_board_markdown(
            digest_date=digest_date,
            selected=selected,
            skipped=skipped,
            candidate_by_id=candidate_by_id,
            top=top,
            current_keys=current_keys,
            reviewed_keys=reviewed_keys,
            include_reviewed=include_reviewed,
        ),
        encoding="utf-8",
    )
    return path, metadata_path, report_path


def _bundle_review_metadata_path(path: Path) -> Path:
    return path.with_name(f"{path.stem}_metadata.json")


def _reviewed_candidate_guard_report_path(board_csv_path: Path, digest_date: str) -> Path:
    try:
        board_csv_path.resolve().relative_to(paths.DAILY_DIGEST_DIR.resolve())
    except ValueError:
        return board_csv_path.parent / "reports" / (
            f"jibi_reviewed_candidate_guard_{digest_date}.md"
        )
    return paths.REPORTS_DIR / f"jibi_reviewed_candidate_guard_{digest_date}.md"


def _board_score_report_path(board_csv_path: Path, digest_date: str) -> Path:
    try:
        board_csv_path.resolve().relative_to(paths.DAILY_DIGEST_DIR.resolve())
    except ValueError:
        return board_csv_path.parent / "reports" / f"jibi_board_score_{digest_date}.md"
    return paths.REPORTS_DIR / f"jibi_board_score_{digest_date}.md"


def _effective_review_history_path(
    *,
    board_csv_path: Path,
    review_history_path: Path,
) -> Path:
    if review_history_path != paths.JIBI_REVIEW_BOARD_HISTORY_JSONL:
        return review_history_path
    try:
        board_csv_path.resolve().relative_to(paths.DAILY_DIGEST_DIR.resolve())
    except ValueError:
        return board_csv_path.parent / "reports" / paths.JIBI_REVIEW_BOARD_HISTORY_JSONL.name
    return review_history_path


def _effective_editorial_overrides_path(
    *,
    board_csv_path: Path,
    run_date: str,
    editorial_overrides_path: Path | None,
) -> Path:
    if editorial_overrides_path is not None:
        return editorial_overrides_path
    env_value = os.environ.get("JIBI_REVIEW_BOARD_EDITORIAL_OVERRIDES")
    if env_value:
        return Path(env_value)
    try:
        board_csv_path.resolve().relative_to(paths.DAILY_DIGEST_DIR.resolve())
    except ValueError:
        return board_csv_path.parent / "editorial_overrides" / (
            f"jibi_review_board_{run_date}.json"
        )
    return _default_editorial_overrides_path(run_date)


def _write_bundle_review_metadata(
    path: Path,
    *,
    rows: list[dict[str, Any]],
    digest_date: str,
    registered_at: str,
) -> None:
    payload = {
        "run_date": digest_date,
        "registered_at": registered_at,
        "visible_columns": BUNDLE_REVIEW_SHEET_COLUMNS,
        "rows": rows,
    }
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _default_syuka_similarity_report_path(run_date: str) -> Path:
    return paths.REPORTS_DIR / f"jibi_syuka_snapshot_matches_{run_date}.json"


def _default_editorial_overrides_path(run_date: str) -> Path:
    return paths.JIBI_EDITORIAL_OVERRIDES_DIR / f"jibi_review_board_{run_date}.json"


def _editorial_override_template_path(run_date: str) -> Path:
    return paths.JIBI_EDITORIAL_OVERRIDES_DIR / f"jibi_review_board_{run_date}.template.json"


def _resolve_editorial_overrides_path(
    run_date: str,
    editorial_overrides_path: Path | None,
) -> Path:
    if editorial_overrides_path is not None:
        return editorial_overrides_path
    env_value = os.environ.get("JIBI_REVIEW_BOARD_EDITORIAL_OVERRIDES")
    if env_value:
        return Path(env_value)
    return _default_editorial_overrides_path(run_date)


def _load_editorial_overrides(path: Path | None) -> dict[str, dict[str, Any]]:
    if path is None or not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    if not isinstance(payload, dict):
        return {}
    raw_items = payload.get("items", payload)
    if not isinstance(raw_items, dict):
        return {}
    items: dict[str, dict[str, Any]] = {}
    for key, value in raw_items.items():
        if isinstance(value, dict):
            items[str(key)] = value
    return items


def _editorial_override_for_row(
    overrides: dict[str, dict[str, Any]],
    *,
    review_item_id: str,
    story_fingerprint: str,
) -> dict[str, Any] | None:
    for key in [review_item_id, story_fingerprint]:
        if key and key in overrides:
            return overrides[key]
    return None


def _apply_editorial_override(
    row: dict[str, Any],
    override: dict[str, Any] | None,
) -> None:
    if not override:
        return
    title = str(override.get("title") or "").strip()
    description = str(override.get("description") or "").strip()
    reference = str(
        override.get("past_video")
        or override.get("과거 영상")
        or override.get("reference")
        or override.get("참고")
        or ""
    ).strip()
    if title:
        row["제목"] = title
    if description:
        row["설명"] = description
    if reference:
        row["과거 영상"] = reference


def _write_editorial_override_template(
    path: Path,
    *,
    rows: list[dict[str, Any]],
    digest_date: str,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    items: dict[str, dict[str, Any]] = {}
    for row in rows:
        review_item_id = str(row.get("review_item_id") or row.get("ID") or "")
        if not review_item_id:
            continue
        items[review_item_id] = {
            "story_fingerprint": str(row.get("story_fingerprint") or ""),
            "title": str(row.get("title") or ""),
            "description": str(row.get("description") or ""),
            "reason": "",
        }
    payload = {
        "run_date": digest_date,
        "editor": "codex",
        "items": items,
    }
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _normalize_syuka_similarity_result(result: dict[str, Any]) -> dict[str, Any]:
    top_match = (result.get("matches") or [{}])[0]
    recommendation = str(result.get("recommendation") or "safe_new_angle")
    display = _syuka_match_display_controls(recommendation, top_match)
    if result.get("match_confidence"):
        display = {
            "match_confidence": str(result.get("match_confidence") or ""),
            "match_reason": str(result.get("match_reason") or ""),
            "display_on_board": bool(result.get("display_on_board")),
        }
    return {
        "story_fingerprint": str(result.get("story_fingerprint") or ""),
        "query_title": str(result.get("query_title") or ""),
        "recommendation": recommendation,
        "top_match_title": str(top_match.get("title") or ""),
        "top_match_score": int(top_match.get("match_score") or 0),
        "matched_terms": list(top_match.get("matched_terms") or []),
        "matched_fields": list(top_match.get("matched_fields") or []),
        "matched_core_terms": list(top_match.get("matched_core_terms") or []),
        "matched_context_terms": list(top_match.get("matched_context_terms") or []),
        "past_video_url": str(top_match.get("url") or ""),
        "past_video_channel_name": str(top_match.get("channel_name") or ""),
        "past_video_channel_key": str(top_match.get("channel_key") or ""),
        "view_count": top_match.get("view_count"),
        "like_count": top_match.get("like_count"),
        "upload_date": str(top_match.get("upload_date") or ""),
        "match_confidence": display["match_confidence"],
        "match_reason": display["match_reason"],
        "display_on_board": display["display_on_board"],
        "past_video_response_signal": str(
            result.get("past_video_response_signal") or result.get("recommendation") or ""
        ),
    }


def _syuka_match_display_controls(
    recommendation: str,
    top_match: dict[str, Any],
) -> dict[str, Any]:
    fields = set(top_match.get("matched_fields") or [])
    score = int(top_match.get("match_score") or 0)
    core_terms = set(top_match.get("matched_core_terms") or [])
    context_terms = set(top_match.get("matched_context_terms") or [])
    if recommendation == "safe_new_angle" or not top_match:
        return {
            "match_confidence": "low",
            "match_reason": "no_local_match",
            "display_on_board": False,
        }
    if fields == {"transcript"}:
        return {
            "match_confidence": "low",
            "match_reason": "transcript_only",
            "display_on_board": False,
        }
    if "title" in fields and (core_terms or recommendation == "duplicate"):
        return {
            "match_confidence": "high" if recommendation == "duplicate" else "medium",
            "match_reason": "core_title_match",
            "display_on_board": recommendation in {"duplicate", "adjacent"},
        }
    if "analysis" in fields and (core_terms or recommendation in {"duplicate", "adjacent"}):
        confidence = "high" if recommendation == "duplicate" and score >= 10 else "medium"
        return {
            "match_confidence": confidence,
            "match_reason": "core_analysis_match",
            "display_on_board": recommendation in {"duplicate", "adjacent"},
        }
    if context_terms or fields:
        confidence = "medium" if score >= 4 and recommendation == "adjacent" else "low"
        return {
            "match_confidence": confidence,
            "match_reason": "context_only",
            "display_on_board": confidence == "medium" and recommendation == "adjacent",
        }
    return {
        "match_confidence": "low",
        "match_reason": "generic_filtered",
        "display_on_board": False,
    }


def _load_syuka_similarity_index(path: Path | None) -> dict[str, dict[str, Any]]:
    if path is None or not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    index: dict[str, dict[str, Any]] = {}
    for result in payload.get("results", []):
        if not isinstance(result, dict):
            continue
        normalized = _normalize_syuka_similarity_result(result)
        for key in [
            str(result.get("story_fingerprint") or "").strip(),
            str(result.get("query_title") or "").strip(),
        ]:
            if key:
                index.setdefault(key, normalized)
    return index


def _syuka_similarity_for_record(
    record: dict[str, Any],
    candidate: dict[str, Any],
    index: dict[str, dict[str, Any]],
) -> dict[str, Any] | None:
    for key in [
        str(record.get("story_fingerprint") or "").strip(),
        str(record.get("bundle_title") or "").strip(),
        str(record.get("primary_title") or "").strip(),
        str(candidate.get("title") or "").strip(),
    ]:
        if key and key in index:
            return index[key]
    return None


def _syuka_similarity_rows(
    similarities: list[dict[str, Any]],
    recommendation: str,
) -> list[str]:
    rows: list[str] = []
    for item in similarities:
        if item.get("recommendation") != recommendation:
            continue
        rows.append(
            "| "
            + " | ".join(
                [
                    _table_cell(item.get("query_title", "")),
                    _table_cell(item.get("top_match_title", "")),
                    str(item.get("top_match_score", 0)),
                    _table_cell(", ".join(item.get("matched_terms", []))),
                    _table_cell(", ".join(item.get("matched_fields", []))),
                    _table_cell(item.get("past_video_response_signal", "")),
                ]
            )
            + " |"
        )
    return rows or ["| none | none | 0 | none | none | none |"]


def _syuka_similarity_summary_lines(index: dict[str, dict[str, Any]]) -> list[str]:
    seen: set[tuple[str, str]] = set()
    similarities: list[dict[str, Any]] = []
    for item in index.values():
        key = (
            str(item.get("story_fingerprint") or ""),
            str(item.get("query_title") or ""),
        )
        if key in seen:
            continue
        seen.add(key)
        similarities.append(item)
    counts = Counter(str(item.get("recommendation") or "unknown") for item in similarities)
    lines = [
        "- report_status: " + ("available" if similarities else "missing_or_empty"),
        *[f"- {key}: {value}" for key, value in sorted(counts.items())],
        "",
        "### High-confidence Duplicate Rows",
        "",
        "| query | top_match | score | terms | fields | response_signal |",
        "| --- | --- | ---: | --- | --- | --- |",
        *_syuka_similarity_rows(similarities, "duplicate"),
        "",
        "### Adjacent / Context Rows",
        "",
        "| query | top_match | score | terms | fields | response_signal |",
        "| --- | --- | ---: | --- | --- | --- |",
        *_syuka_similarity_rows(similarities, "adjacent"),
        "",
        "### Needs Human Check Rows",
        "",
        "| query | top_match | score | terms | fields | response_signal |",
        "| --- | --- | ---: | --- | --- | --- |",
        *_syuka_similarity_rows(similarities, "needs_human_check"),
        "",
        "### Safe New Angle / No Local Match Rows",
        "",
        "| query | top_match | score | terms | fields | response_signal |",
        "| --- | --- | ---: | --- | --- | --- |",
        *_syuka_similarity_rows(similarities, "safe_new_angle"),
    ]
    return lines


def _current_board_exclusion_keys(path: Path) -> set[str]:
    keys: set[str] = set()
    metadata_path = _bundle_review_metadata_path(path)
    if metadata_path.exists():
        try:
            payload = json.loads(metadata_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            payload = {}
        for row in payload.get("rows", []):
            if not isinstance(row, dict):
                continue
            keys.update(
                str(row.get(key) or "").strip()
                for key in [
                    "ID",
                    "review_item_id",
                    "story_fingerprint",
                    "story_bundle_id",
                    "primary_candidate_id",
                ]
            )
            keys.update(str(item).strip() for item in row.get("supporting_candidate_ids", []))
            keys.update(str(item).strip() for item in row.get("evidence_candidate_ids", []))
    if path.exists():
        with path.open(encoding="utf-8-sig", newline="") as source:
            for row in csv.DictReader(source):
                review_id = str(row.get("ID") or "").strip()
                if review_id:
                    keys.add(review_id)
                    keys.add(review_id.rsplit(":", 1)[-1])
    return {key for key in keys if key}


def _reviewed_history_exclusion_keys(
    history_index: dict[str, list[dict[str, Any]]],
) -> set[str]:
    keys: set[str] = set()
    for key, rows in history_index.items():
        if any(str(row.get("history_status") or "") != "seen_before" for row in rows):
            keys.add(key)
    return keys


def _record_exclusion_keys(record: dict[str, Any]) -> set[str]:
    keys = {
        str(record.get("story_fingerprint") or "").strip(),
        str(record.get("story_bundle_id") or "").strip(),
        str(record.get("primary_candidate_id") or "").strip(),
    }
    keys.update(str(item).strip() for item in record.get("supporting_candidate_ids", []))
    keys.update(str(item).strip() for item in record.get("evidence_candidate_ids", []))
    return {key for key in keys if key}


def _reviewed_history_rows_for_record(
    record: dict[str, Any],
    history_index: dict[str, list[dict[str, Any]]],
) -> list[dict[str, Any]]:
    reviewed_rows: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for key in _record_exclusion_keys(record):
        for row in history_index.get(key, []):
            status = str(row.get("history_status") or "seen_before")
            if status == "seen_before":
                continue
            row_id = str(row.get("ID") or row.get("id") or "")
            marker = (key, row_id or str(id(row)))
            if marker in seen:
                continue
            seen.add(marker)
            reviewed_rows.append(row)
    return reviewed_rows


def _select_review_board_records(
    records: list[dict[str, Any]],
    history_index: dict[str, list[dict[str, Any]]],
    *,
    candidate_by_id: dict[str, dict[str, Any]],
    editorial_overrides: dict[str, dict[str, Any]],
    syuka_similarity_index: dict[str, dict[str, Any]],
    second_search_index: dict[str, dict[str, Any]],
    digest_date: str,
    review_board_limit: int,
    allow_reviewed_candidates: bool,
    use_board_score: bool,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    selected_ids: set[str] = set()
    suppressed: list[dict[str, Any]] = []
    role_counts: Counter[str] = Counter()
    role_cap_blocked: list[dict[str, Any]] = []
    evidence_backfill: list[dict[str, Any]] = []
    hard_blocked: list[dict[str, Any]] = []
    mismatch_blocked: list[dict[str, Any]] = []
    score_rows: list[dict[str, Any]] = []
    override_by_record_id: dict[str, dict[str, Any]] = {}

    scored_records: list[tuple[dict[str, Any], dict[str, Any]]] = []
    for record in records:
        representative = _record_representative_candidate(record, candidate_by_id) or {}
        reviewed_rows = _reviewed_history_rows_for_record(record, history_index)
        override = _editorial_override_for_row(
            editorial_overrides,
            review_item_id=_record_review_item_id(digest_date, record),
            story_fingerprint=str(record.get("story_fingerprint") or ""),
        )
        record_id = str(record.get("story_bundle_id") or "")
        if override and record_id:
            override_by_record_id[record_id] = override
        mismatch_reasons = _board_mismatch_reasons(record, representative, override)
        syuka_similarity = _syuka_similarity_for_record(
            record,
            representative,
            syuka_similarity_index,
        )
        second_search = _second_search_for_record(record, second_search_index)
        board_score = _board_score_info(
            record=record,
            representative=representative,
            history_rows=reviewed_rows,
            mismatch_reasons=mismatch_reasons,
            syuka_similarity=syuka_similarity,
            second_search=second_search,
        )
        scored_records.append((record, board_score))
        score_rows.append(
            _board_score_report_row(
                record=record,
                representative=representative,
                board_score=board_score,
                history_rows=reviewed_rows,
                mismatch_reasons=mismatch_reasons,
                second_search=second_search,
                override=override,
            )
        )

    if use_board_score:
        scored_records.sort(
            key=lambda item: (
                float(item[1].get("board_score") or 0),
                _total_score(_record_representative_candidate(item[0], candidate_by_id) or {}),
            ),
            reverse=True,
        )

    for record, board_score in scored_records:
        representative = _record_representative_candidate(record, candidate_by_id) or {}
        reviewed_rows = _reviewed_history_rows_for_record(record, history_index)
        mismatch_reasons = list(board_score.get("mismatch_reasons") or [])
        record_id = str(record.get("story_bundle_id") or "")
        if reviewed_rows and not allow_reviewed_candidates:
            suppressed.append(
                {
                    "record": record,
                    "history_rows": reviewed_rows,
                    "suppressed_reason": "reviewed_history",
                    "board_score": board_score,
                }
            )
            continue
        board_status = _record_board_quality_status(
            record,
            representative,
            mismatch_reasons=mismatch_reasons,
        )
        if board_status == "hard_blocked":
            item = {
                "record": record,
                "board_score": board_score,
                "override": override_by_record_id.get(record_id, {}),
                "reasons": _hard_block_reasons(record, representative, mismatch_reasons),
            }
            hard_blocked.append(item)
            if mismatch_reasons:
                mismatch_blocked.append(item)
            continue
        if board_status == "evidence_backfill":
            evidence_backfill.append(record)
            continue
        role = _record_source_role(record, candidate_by_id)
        cap = DEFAULT_SOURCE_ROLE_TOP_CAPS.get(role)
        if cap is not None and role_counts[role] >= cap:
            role_cap_blocked.append(record)
            continue
        selected.append(record)
        selected_ids.add(record_id)
        role_counts[role] += 1
        if len(selected) >= review_board_limit:
            break
    if len(selected) < review_board_limit:
        for record in role_cap_blocked:
            record_id = str(record.get("story_bundle_id") or "")
            if record_id in selected_ids:
                continue
            selected.append(record)
            selected_ids.add(record_id)
            if len(selected) >= review_board_limit:
                break
    if len(selected) < review_board_limit:
        for record in evidence_backfill:
            record_id = str(record.get("story_bundle_id") or "")
            if record_id in selected_ids:
                continue
            selected.append(record)
            selected_ids.add(record_id)
            if len(selected) >= review_board_limit:
                break
    return selected, suppressed, {
        "use_board_score": use_board_score,
        "score_rows": score_rows,
        "hard_blocked": hard_blocked,
        "mismatch_blocked": mismatch_blocked,
        "reviewed_suppressed": suppressed,
        "role_cap_blocked": role_cap_blocked,
        "evidence_backfill": evidence_backfill,
        "selected_ids": [str(record.get("story_bundle_id") or "") for record in selected],
    }


def _record_review_item_id(digest_date: str, record: dict[str, Any]) -> str:
    return f"{digest_date}:{record['story_bundle_id']}"


def _record_board_quality_status(
    record: dict[str, Any],
    representative: dict[str, Any],
    *,
    mismatch_reasons: list[str] | None = None,
) -> str:
    if mismatch_reasons:
        return "hard_blocked"
    title_text = _source_text(representative) + " " + str(record.get("bundle_title") or "")
    if any(term in title_text for term in ("[부고]", "부친상", "모친상", "별세", "씨 별세")):
        return "hard_blocked"
    lowered_title_text = title_text.lower()
    if any(term in lowered_title_text for term in BOARD_SCORE_PRODUCT_REVIEW_TERMS):
        return "hard_blocked"
    story_role = str(representative.get("story_role") or "")
    seed_quality = str(representative.get("seed_quality_classification") or "")
    if story_role == "demote_or_reject" or seed_quality == "reject_or_downrank":
        return "hard_blocked"
    if story_role == "evidence_for_larger_story" or seed_quality == "evidence_only":
        return "evidence_backfill"
    return "ok"


def _hard_block_reasons(
    record: dict[str, Any],
    representative: dict[str, Any],
    mismatch_reasons: list[str],
) -> list[str]:
    reasons = list(mismatch_reasons)
    title_text = _source_text(representative) + " " + str(record.get("bundle_title") or "")
    if any(term in title_text for term in ("[부고]", "부친상", "모친상", "별세", "씨 별세")):
        reasons.append("obituary_or_personnel_notice")
    lowered_title_text = title_text.lower()
    if any(term in lowered_title_text for term in BOARD_SCORE_PRODUCT_REVIEW_TERMS):
        reasons.append("product_review_or_shopping_guide")
    story_role = str(representative.get("story_role") or "")
    seed_quality = str(representative.get("seed_quality_classification") or "")
    if story_role == "demote_or_reject":
        reasons.append("story_role=demote_or_reject")
    if seed_quality == "reject_or_downrank":
        reasons.append("seed_quality=reject_or_downrank")
    return list(dict.fromkeys(reasons or ["hard_blocked"]))


def _board_mismatch_reasons(
    record: dict[str, Any],
    representative: dict[str, Any],
    override: dict[str, Any] | None,
) -> list[str]:
    reasons: list[str] = []
    if not representative:
        return reasons
    override_text = " ".join(
        str((override or {}).get(key) or "")
        for key in ["title", "description", "reason"]
    ).lower()
    if any(term in override_text for term in BOARD_SCORE_MISMATCH_WARNING_TERMS):
        reasons.append("editorial_override_source_mismatch_warning")

    visible_text = " ".join(
        [
            str((override or {}).get("title") or record.get("bundle_title") or ""),
            str((override or {}).get("description") or record.get("why_bundle") or ""),
        ]
    ).lower()
    source_text = _source_text(representative)
    for group_name, terms in BOARD_SCORE_TOPIC_GROUPS.items():
        visible_has_group = any(_topic_term_in_text(term, visible_text) for term in terms)
        source_has_group = any(_topic_term_in_text(term, source_text) for term in terms)
        if visible_has_group and not source_has_group:
            reasons.append(f"visible_primary_topic_mismatch={group_name}")
    return list(dict.fromkeys(reasons))


def _topic_term_in_text(term: str, text: str) -> bool:
    normalized_term = term.lower().strip()
    if not normalized_term:
        return False
    if re.fullmatch(r"[a-z0-9_+-]+", normalized_term):
        return bool(
            re.search(
                rf"(?<![a-z0-9]){re.escape(normalized_term)}(?![a-z0-9])",
                text,
            )
        )
    return normalized_term in text


def _history_review_context(history_rows: list[dict[str, Any]]) -> dict[str, list[str]]:
    adjustments: list[str] = []
    roles: list[str] = []
    failure_modes: list[str] = []
    positive_signals: list[str] = []
    for row in history_rows:
        for column in REVIEWER_COLUMNS:
            note = str(row.get(column) or "").strip()
            if not note:
                continue
            payload = infer_review_feedback(note)
            adjustments.extend(str(item) for item in payload.get("review_adjustments", []))
            roles.append(str(payload.get("editorial_role") or ""))
            failure_modes.extend(str(item) for item in payload.get("failure_modes", []))
            positive_signals.extend(str(item) for item in payload.get("positive_signals", []))
    return {
        "review_adjustments": sorted({item for item in adjustments if item}),
        "review_editorial_roles": sorted({item for item in roles if item}),
        "review_failure_modes": sorted({item for item in failure_modes if item}),
        "review_positive_signals": sorted({item for item in positive_signals if item}),
    }


def _board_score_review_lesson_adjustments(
    *,
    source_text: str,
    seed_type: str,
    quality_flags: set[str],
    review_context: dict[str, list[str]],
) -> tuple[float, list[str], list[str], list[str]]:
    score_delta = 0.0
    reasons: list[str] = []
    adjustments = set(review_context.get("review_adjustments") or [])
    roles = set(review_context.get("review_editorial_roles") or [])
    failure_modes = set(review_context.get("review_failure_modes") or [])
    positive_signals = set(review_context.get("review_positive_signals") or [])

    sports_primary = (
        "sports_primary_downrank" in adjustments
        or "sports_only" in quality_flags
        or seed_type == "sports"
        or (
            any(_topic_term_in_text(term, source_text) for term in BOARD_SCORE_SPORTS_PRIMARY_TERMS)
            and not any(
                _topic_term_in_text(term, source_text)
                for term in BOARD_SCORE_SPORTS_HOOK_TERMS
            )
        )
    )
    sports_hook = sports_primary and any(
        _topic_term_in_text(term, source_text) for term in BOARD_SCORE_SPORTS_HOOK_TERMS
    )
    if sports_primary:
        adjustments.add("sports_primary_downrank")
        if sports_hook or roles.intersection({"hook_only", "sub_block"}):
            roles.add("hook_only")
            score_delta -= 25
            reasons.append("-25 review_sports_hook_only_not_primary")
        else:
            roles.add("suppress")
            score_delta -= 45
            reasons.append("-45 review_sports_primary_downrank")

    ai_grand = "ai_grand_discourse_downrank" in adjustments or any(
        _topic_term_in_text(term, source_text)
        for term in BOARD_SCORE_AI_GRAND_DISCOURSE_TERMS
    )
    casual_ai = "casual_ai_use_case_bonus" in adjustments or any(
        _topic_term_in_text(term, source_text)
        for term in BOARD_SCORE_CASUAL_AI_TERMS
    )
    if ai_grand:
        adjustments.add("ai_grand_discourse_downrank")
        score_delta -= 18
        reasons.append("-18 review_ai_grand_discourse_downrank")
    if casual_ai:
        adjustments.add("casual_ai_use_case_bonus")
        roles.add("sub_block")
        score_delta += 8
        reasons.append("+8 review_casual_ai_use_case_sub_block")

    if "past_topic_overlap_downrank" in adjustments or "too_familiar" in failure_modes:
        adjustments.add("past_topic_overlap_downrank")
        score_delta -= 25
        reasons.append("-25 review_past_topic_overlap")
    if "needs_new_angle" in adjustments:
        score_delta -= 12
        reasons.append("-12 review_needs_new_angle")

    if "hook_only" in adjustments or "hook_only" in roles:
        roles.add("hook_only")
        score_delta -= 10
        reasons.append("-10 review_hook_only_not_primary")
    elif "sub_block" in adjustments or "sub_block" in roles:
        roles.add("sub_block")
        score_delta -= 6
        reasons.append("-6 review_sub_block_not_primary")

    if "specific_case_needed" in positive_signals and "sub_block" in roles:
        score_delta += 2
        reasons.append("+2 review_specific_case_sub_block")

    return (
        score_delta,
        reasons,
        sorted(adjustments),
        sorted(item for item in roles if item),
    )


def _board_score_info(
    *,
    record: dict[str, Any],
    representative: dict[str, Any],
    history_rows: list[dict[str, Any]],
    mismatch_reasons: list[str],
    syuka_similarity: dict[str, Any] | None,
    second_search: dict[str, Any] | None,
) -> dict[str, Any]:
    total_score = _total_score(representative)
    score = total_score
    reasons: list[str] = [f"base_total_score={total_score:g}"]

    story_role = str(representative.get("story_role") or "")
    seed_quality = str(representative.get("seed_quality_classification") or "")
    seed_type = str(representative.get("seed_type") or "")
    source_role = _candidate_role(representative)
    source_text = _source_text(representative)
    so_what = _candidate_so_what(representative)
    so_what_label = str(so_what.get("so_what_label") or "")
    quality_flags = set(str(flag) for flag in representative.get("quality_flags") or [])
    weakness = set(str(flag) for flag in so_what.get("weakness_signals") or [])
    review_context = _history_review_context(history_rows)

    if story_role == "standalone_seed" or seed_quality == "standalone_seed":
        score += 8
        reasons.append("+8 standalone_seed")
    if story_role == "seed_with_supporting_links":
        score += 5
        reasons.append("+5 seed_with_supporting_links")
    if seed_quality in {"conditional_seed", "bundle_needed"}:
        score += 3
        reasons.append("+3 conditional_or_bundle_seed")
    if so_what_label == "strong":
        score += 6
        reasons.append("+6 strong_so_what")
    elif so_what_label == "conditional":
        score += 2
        reasons.append("+2 conditional_so_what")

    if second_search:
        accepted_count = len(second_search.get("accepted_links") or [])
        query_types = {
            str(link.get("query_type") or "")
            for link in second_search.get("accepted_links") or []
            if isinstance(link, dict)
        }
        if accepted_count >= 2:
            score += 5
            reasons.append("+5 second_search_links>=2")
        if "broader_system" in query_types:
            score += 3
            reasons.append("+3 broader_system_second_search")

    syuka_recommendation = str((syuka_similarity or {}).get("recommendation") or "")
    if syuka_recommendation == "duplicate":
        score -= 25
        reasons.append("-25 syuka_duplicate")
    elif syuka_recommendation == "adjacent":
        score += 2
        reasons.append("+2 syuka_adjacent_context")

    if story_role == "evidence_for_larger_story" or seed_quality == "evidence_only":
        score -= 18
        reasons.append("-18 evidence_only")
    if story_role == "demote_or_reject" or seed_quality == "reject_or_downrank":
        score -= 60
        reasons.append("-60 demote_or_reject")
    if "weak_audience_bridge" in quality_flags or "weak_audience_bridge" in weakness:
        score -= 18
        reasons.append("-18 weak_audience_bridge")
    if quality_flags.intersection(BOARD_SCORE_PROMO_FLAGS):
        score -= 15
        reasons.append("-15 promo_or_program_bulletin")
    if any(_topic_term_in_text(term, source_text) for term in BOARD_SCORE_MARKET_RISK_TERMS):
        score -= 22
        reasons.append("-22 market_or_security_specific_frame")
    if (
        source_role in {"public_wire", "policy_release"}
        and any(_topic_term_in_text(term, source_text) for term in BOARD_SCORE_PROMO_TEXT_TERMS)
    ):
        score -= 15
        reasons.append("-15 promo_or_announcement_text")
    if (
        source_role == "public_wire"
        and seed_type == "other"
        and not any(
            _topic_term_in_text(term, source_text)
            for term in BOARD_SCORE_SYSTEM_TOPIC_TERMS
        )
    ):
        score -= 8
        reasons.append("-8 public_wire_other_needs_clear_system_frame")
    if "single_company_frame" in quality_flags:
        score -= 10
        reasons.append("-10 single_company_frame")
    if mismatch_reasons:
        score -= 100
        reasons.append("-100 source_cluster_title_mismatch")

    review_delta, review_reasons, review_adjustments, review_editorial_roles = (
        _board_score_review_lesson_adjustments(
            source_text=source_text,
            seed_type=seed_type,
            quality_flags=quality_flags,
            review_context=review_context,
        )
    )
    if review_delta:
        score += review_delta
    reasons.extend(review_reasons)

    history_statuses = {
        str(row.get("history_status") or "reviewed_before") for row in history_rows
    }
    if "rejected_before" in history_statuses:
        score -= 80
        reasons.append("-80 rejected_before")
    elif "promoted_before" in history_statuses:
        score -= 35
        reasons.append("-35 promoted_before")
    elif history_statuses:
        score -= 25
        reasons.append("-25 reviewed_before")

    return {
        "total_score": total_score,
        "board_score": round(max(0.0, score), 1),
        "reasons": reasons,
        "mismatch_reasons": mismatch_reasons,
        "history_statuses": sorted(history_statuses),
        "review_adjustments": review_adjustments,
        "review_editorial_roles": review_editorial_roles,
        "review_failure_modes": review_context.get("review_failure_modes", []),
        "review_positive_signals": review_context.get("review_positive_signals", []),
    }


def _board_score_report_row(
    *,
    record: dict[str, Any],
    representative: dict[str, Any],
    board_score: dict[str, Any],
    history_rows: list[dict[str, Any]],
    mismatch_reasons: list[str],
    second_search: dict[str, Any] | None,
    override: dict[str, Any] | None = None,
) -> dict[str, Any]:
    title = str(record.get("bundle_title") or record.get("primary_title") or "")
    return {
        "story_bundle_id": str(record.get("story_bundle_id") or ""),
        "story_fingerprint": str(record.get("story_fingerprint") or ""),
        "title": title,
        "visible_title": str((override or {}).get("title") or title),
        "primary_title": str(representative.get("title") or ""),
        "source": str(representative.get("source") or ""),
        "source_role": _candidate_role(representative),
        "story_role": str(representative.get("story_role") or ""),
        "seed_quality_classification": str(
            representative.get("seed_quality_classification") or ""
        ),
        "total_score": board_score.get("total_score", 0),
        "board_score": board_score.get("board_score", 0),
        "board_score_reasons": board_score.get("reasons", []),
        "review_adjustments": board_score.get("review_adjustments", []),
        "review_editorial_roles": board_score.get("review_editorial_roles", []),
        "review_failure_modes": board_score.get("review_failure_modes", []),
        "review_positive_signals": board_score.get("review_positive_signals", []),
        "history_statuses": board_score.get("history_statuses", []),
        "reviewers": list(
            dict.fromkeys(
                reviewer for row in history_rows for reviewer in _history_reviewers(row)
            )
        ),
        "mismatch_reasons": mismatch_reasons,
        "second_search_follow_up_status": str(
            (second_search or {}).get("follow_up_status") or ""
        ),
        "second_search_accepted_links_count": len(
            (second_search or {}).get("accepted_links") or []
        ),
        "second_search_query_types": sorted(
            {
                str(link.get("query_type") or "")
                for link in (second_search or {}).get("accepted_links") or []
                if isinstance(link, dict) and str(link.get("query_type") or "").strip()
            }
        ),
    }


def _load_second_search_intake_index(reports_dir: Path) -> dict[str, dict[str, Any]]:
    index: dict[str, dict[str, Any]] = {}
    for path in sorted(reports_dir.glob("jibi_second_search_intake_*.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        for row in payload.get("rows", []):
            if not isinstance(row, dict):
                continue
            keys = {
                str(row.get("review_item_id") or "").strip(),
                str(row.get("review_title") or "").strip(),
            }
            review_id = str(row.get("review_item_id") or "").strip()
            if ":" in review_id:
                keys.add(review_id.rsplit(":", 1)[-1])
            for key in keys:
                if key:
                    index.setdefault(key, row)
    return index


def _second_search_for_record(
    record: dict[str, Any],
    second_search_index: dict[str, dict[str, Any]],
) -> dict[str, Any] | None:
    for key in [
        str(record.get("story_bundle_id") or "").strip(),
        str(record.get("story_fingerprint") or "").strip(),
        str(record.get("bundle_title") or "").strip(),
        str(record.get("primary_title") or "").strip(),
    ]:
        if key and key in second_search_index:
            return second_search_index[key]
    return None


def _record_source_role(
    record: dict[str, Any],
    candidate_by_id: dict[str, dict[str, Any]],
) -> str:
    representative = _record_representative_candidate(record, candidate_by_id)
    if representative:
        return _candidate_role(representative)
    return "unknown"


def _history_reviewers(row: dict[str, Any]) -> list[str]:
    reviewers: list[str] = []
    reviewer_payloads = row.get("reviewers")
    if isinstance(reviewer_payloads, dict):
        for reviewer, payload in reviewer_payloads.items():
            if isinstance(payload, dict) and str(payload.get("raw_note") or "").strip():
                reviewers.append(str(reviewer))
    for column in REVIEWER_COLUMNS:
        if str(row.get(column) or "").strip():
            reviewers.append(column.replace("리뷰-", ""))
    return list(dict.fromkeys(reviewers))


def _history_review_excerpt(row: dict[str, Any]) -> str:
    reviewer_payloads = row.get("reviewers")
    if isinstance(reviewer_payloads, dict):
        for payload in reviewer_payloads.values():
            if isinstance(payload, dict):
                note = str(payload.get("raw_note") or payload.get("note") or "").strip()
                if note:
                    return _short_review_excerpt(note)
    for column in REVIEWER_COLUMNS:
        note = str(row.get(column) or "").strip()
        if note:
            return _short_review_excerpt(note)
    return ""


def _history_review_date(row: dict[str, Any]) -> str:
    for key in ["run_date", "date", "_snapshot_created_at", "created_at"]:
        value = str(row.get(key) or "").strip()
        if value:
            return value[:10]
    review_id = str(row.get("ID") or row.get("id") or "").strip()
    if ":" in review_id:
        return review_id.split(":", 1)[0]
    return ""


def _guard_followup_action(history_rows: list[dict[str, Any]]) -> str:
    statuses = {str(row.get("history_status") or "") for row in history_rows}
    if "rejected_before" in statuses:
        return "do_not_repost_without_new_hook_or_explicit_override"
    if "promoted_before" in statuses:
        return "avoid_duplicate_review_unless_followup_news_changed"
    return "use_second_search_or_new_frame_before_reposting"


def _guard_report_payload(
    *,
    digest_date: str,
    selected: list[dict[str, Any]],
    suppressed: list[dict[str, Any]],
    allow_reviewed_candidates: bool,
    history_index: dict[str, list[dict[str, Any]]],
) -> dict[str, Any]:
    selected_rows = []
    for record in selected:
        history_rows = _reviewed_history_rows_for_record(record, history_index)
        selected_rows.append(
            {
                "story_bundle_id": str(record.get("story_bundle_id") or ""),
                "story_fingerprint": str(record.get("story_fingerprint") or ""),
                "title": str(record.get("bundle_title") or record.get("primary_title") or ""),
                "history_status": "reviewed_allowed" if history_rows else "new",
            }
        )
    suppressed_rows = []
    for item in suppressed:
        record = item["record"]
        history_rows = item["history_rows"]
        suppressed_rows.append(
            {
                "story_bundle_id": str(record.get("story_bundle_id") or ""),
                "story_fingerprint": str(record.get("story_fingerprint") or ""),
                "title": str(record.get("bundle_title") or record.get("primary_title") or ""),
                "suppressed_reason": item.get("suppressed_reason", "reviewed_history"),
                "previous_review_dates": list(
                    dict.fromkeys(
                        date
                        for row in history_rows
                        if (date := _history_review_date(row))
                    )
                ),
                "reviewers": list(
                    dict.fromkeys(
                        reviewer
                        for row in history_rows
                        for reviewer in _history_reviewers(row)
                    )
                ),
                "history_statuses": list(
                    dict.fromkeys(
                        str(row.get("history_status") or "reviewed_before")
                        for row in history_rows
                    )
                ),
                "review_excerpt": _history_review_excerpt(history_rows[0])
                if history_rows
                else "",
                "required_action": _guard_followup_action(history_rows),
            }
        )
    return {
        "run_date": digest_date,
        "allow_reviewed_candidates": allow_reviewed_candidates,
        "selected_count": len(selected_rows),
        "suppressed_count": len(suppressed_rows),
        "selected": selected_rows,
        "suppressed": suppressed_rows,
    }


def _write_reviewed_candidate_guard_report(
    *,
    digest_date: str,
    selected: list[dict[str, Any]],
    suppressed: list[dict[str, Any]],
    allow_reviewed_candidates: bool,
    history_index: dict[str, list[dict[str, Any]]],
    path: Path,
) -> tuple[Path, Path]:
    payload = _guard_report_payload(
        digest_date=digest_date,
        selected=selected,
        suppressed=suppressed,
        allow_reviewed_candidates=allow_reviewed_candidates,
        history_index=history_index,
    )
    json_path = path.with_suffix(".json")
    path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
    lines = [
        f"# Jibi Reviewed Candidate Guard — {digest_date}",
        "",
        "Report-only guard for suppressing candidates that already received human review.",
        "",
        f"- allow_reviewed_candidates: {str(allow_reviewed_candidates).lower()}",
        f"- selected_count: {payload['selected_count']}",
        f"- suppressed_count: {payload['suppressed_count']}",
        "",
        "## New Candidates",
        "",
        "| title | story_fingerprint | history_status |",
        "| --- | --- | --- |",
    ]
    for row in payload["selected"]:
        lines.append(
            "| "
            + " | ".join(
                [
                    _table_cell(row["title"]),
                    _table_cell(row["story_fingerprint"]),
                    _table_cell(row["history_status"]),
                ]
            )
            + " |"
        )
    if not payload["selected"]:
        lines.append("| none | none | none |")
    lines.extend(
        [
            "",
            "## Suppressed Reviewed Candidates",
            "",
            "| title | previous_review_dates | reviewers | status | required_action | excerpt |",
            "| --- | --- | --- | --- | --- | --- |",
        ]
    )
    for row in payload["suppressed"]:
        lines.append(
            "| "
            + " | ".join(
                [
                    _table_cell(row["title"]),
                    _table_cell(", ".join(row["previous_review_dates"]) or "unknown"),
                    _table_cell(", ".join(row["reviewers"]) or "unknown"),
                    _table_cell(", ".join(row["history_statuses"]) or "reviewed_before"),
                    _table_cell(row["required_action"]),
                    _table_cell(row["review_excerpt"]),
                ]
            )
            + " |"
        )
    if not payload["suppressed"]:
        lines.append("| none | none | none | none | none | none |")
    lines.extend(
        [
            "",
            "## Reconsideration Rule",
            "",
            "- Default: reviewed candidates are excluded from the next visible Jibi board.",
            "- Override only with `JIBI_ALLOW_REVIEWED_CANDIDATES=1` after a new hook, "
            "new supporting links, or a clearly changed frame exists.",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path, json_path


def _selection_report_ids(
    items: list[dict[str, Any]] | list[dict[str, Any] | tuple[Any, ...]],
) -> set[str]:
    ids: set[str] = set()
    for item in items:
        record = item.get("record") if isinstance(item, dict) else item
        if isinstance(record, dict):
            value = str(record.get("story_bundle_id") or "").strip()
            if value:
                ids.add(value)
    return ids


def _suppressed_review_payload(
    *,
    digest_date: str,
    suppressed: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for item in suppressed:
        record = item.get("record") or {}
        history_rows = item.get("history_rows") or []
        rows.append(
            {
                "story_bundle_id": str(record.get("story_bundle_id") or ""),
                "story_fingerprint": str(record.get("story_fingerprint") or ""),
                "title": str(record.get("bundle_title") or record.get("primary_title") or ""),
                "previous_review_dates": list(
                    dict.fromkeys(
                        value
                        for row in history_rows
                        if (value := _history_review_date(row))
                    )
                ),
                "reviewers": list(
                    dict.fromkeys(
                        reviewer
                        for row in history_rows
                        for reviewer in _history_reviewers(row)
                    )
                ),
                "history_statuses": list(
                    dict.fromkeys(
                        str(row.get("history_status") or "reviewed_before")
                        for row in history_rows
                    )
                ),
                "review_excerpt": _history_review_excerpt(history_rows[0])
                if history_rows
                else "",
                "required_action": _guard_followup_action(history_rows),
                "run_date": digest_date,
            }
        )
    return rows


def _record_from_selection_item(item: dict[str, Any]) -> dict[str, Any]:
    record = item.get("record")
    return record if isinstance(record, dict) else {}


def _selection_reason_index(selection_report: dict[str, Any]) -> dict[str, list[str]]:
    reasons: dict[str, list[str]] = {}
    for item in selection_report.get("hard_blocked", []):
        record = _record_from_selection_item(item)
        record_id = str(record.get("story_bundle_id") or "")
        if not record_id:
            continue
        reasons.setdefault(record_id, []).extend(
            str(reason) for reason in item.get("reasons", []) if str(reason).strip()
        )
    for item in selection_report.get("mismatch_blocked", []):
        record = _record_from_selection_item(item)
        record_id = str(record.get("story_bundle_id") or "")
        if record_id:
            reasons.setdefault(record_id, []).append("source_cluster_title_mismatch")
    for item in selection_report.get("reviewed_suppressed", []):
        record = _record_from_selection_item(item)
        record_id = str(record.get("story_bundle_id") or "")
        if record_id:
            reasons.setdefault(record_id, []).append("reviewed_history_suppressed")
    for record in selection_report.get("role_cap_blocked", []):
        if isinstance(record, dict):
            record_id = str(record.get("story_bundle_id") or "")
            if record_id:
                reasons.setdefault(record_id, []).append("source_role_cap_overflow")
    for record in selection_report.get("evidence_backfill", []):
        if isinstance(record, dict):
            record_id = str(record.get("story_bundle_id") or "")
            if record_id:
                reasons.setdefault(record_id, []).append("evidence_or_background_backfill")
    return {key: list(dict.fromkeys(value)) for key, value in reasons.items()}


def _reconsideration_status(
    row: dict[str, Any],
    suppressed_row: dict[str, Any],
) -> str:
    statuses = set(suppressed_row.get("history_statuses") or row.get("history_statuses") or [])
    accepted_count = int(row.get("second_search_accepted_links_count") or 0)
    query_types = set(row.get("second_search_query_types") or [])
    if "rejected_before" in statuses and accepted_count < 2:
        return "not_reconsidered_rejected_before_without_new_hook"
    if accepted_count >= 2 and "broader_system" in query_types:
        return "reconsideration_candidate_report_only"
    if accepted_count >= 2:
        return "possible_reconsideration_needs_new_frame"
    if "promoted_before" in statuses:
        return "not_reconsidered_promoted_before_wait_for_followup_news"
    return "not_reconsidered_needs_second_search_or_new_hook"


def _write_board_score_report(
    *,
    digest_date: str,
    selected: list[dict[str, Any]],
    candidates: list[dict[str, Any]],
    candidate_by_id: dict[str, dict[str, Any]],
    selection_report: dict[str, Any],
    history_index: dict[str, list[dict[str, Any]]],
    syuka_similarity_index: dict[str, dict[str, Any]],
    second_search_index: dict[str, dict[str, Any]],
    path: Path,
) -> tuple[Path, Path]:
    del candidates, candidate_by_id, history_index, syuka_similarity_index, second_search_index
    score_rows = list(selection_report.get("score_rows") or [])
    selected_ids = {
        str(record.get("story_bundle_id") or "")
        for record in selected
        if record.get("story_bundle_id")
    }
    score_by_id = {str(row.get("story_bundle_id") or ""): row for row in score_rows}
    selected_rows = [
        score_by_id.get(str(record.get("story_bundle_id") or ""), {})
        for record in selected
    ]
    selected_rows = [row for row in selected_rows if row]
    reason_index = _selection_reason_index(selection_report)
    suppressed_review_rows = _suppressed_review_payload(
        digest_date=digest_date,
        suppressed=list(selection_report.get("reviewed_suppressed") or []),
    )
    selected_board_floor = min(
        (float(row.get("board_score") or 0) for row in selected_rows),
        default=0,
    )
    high_total_rows: list[dict[str, Any]] = []
    sorted_score_rows = sorted(
        score_rows,
        key=lambda item: float(item.get("total_score") or 0),
        reverse=True,
    )
    for row in sorted_score_rows:
        record_id = str(row.get("story_bundle_id") or "")
        if record_id in selected_ids:
            continue
        reasons = list(reason_index.get(record_id) or [])
        if row.get("mismatch_reasons"):
            reasons.append("source_cluster_title_mismatch")
        if not reasons and float(row.get("board_score") or 0) < selected_board_floor:
            reasons.append("board_score_downranked_below_selected_floor")
        if not reasons:
            reasons.append("outside_review_board_limit")
        high_total_rows.append({**row, "why_excluded": list(dict.fromkeys(reasons))})
    mismatch_by_id: dict[str, dict[str, Any]] = {}
    hard_blocked_rows: list[dict[str, Any]] = []
    for item in selection_report.get("mismatch_blocked", []):
        record = _record_from_selection_item(item)
        override = item.get("override") if isinstance(item.get("override"), dict) else {}
        row = score_by_id.get(str(record.get("story_bundle_id") or ""), {})
        record_id = str(record.get("story_bundle_id") or "")
        mismatch_by_id[record_id] = {
            "visible_title": str(
                row.get("visible_title")
                or override.get("title")
                or record.get("bundle_title")
                or ""
            ),
            "primary_metadata_title": str(row.get("primary_title") or ""),
            "source": str(row.get("source") or ""),
            "story_fingerprint": str(record.get("story_fingerprint") or ""),
            "mismatch_reason": list(
                dict.fromkeys(
                    [
                        *[str(reason) for reason in item.get("reasons", [])],
                        *[str(reason) for reason in row.get("mismatch_reasons", [])],
                    ]
                )
            ),
            "required_action": "fix_override_or_suppress",
        }
    for row in score_rows:
        if not row.get("mismatch_reasons"):
            continue
        record_id = str(row.get("story_bundle_id") or "")
        mismatch_by_id.setdefault(
            record_id,
            {
                "visible_title": str(row.get("visible_title") or row.get("title") or ""),
                "primary_metadata_title": str(row.get("primary_title") or ""),
                "source": str(row.get("source") or ""),
                "story_fingerprint": str(row.get("story_fingerprint") or ""),
                "mismatch_reason": list(row.get("mismatch_reasons") or []),
                "required_action": "fix_override_or_suppress",
            },
        )
    mismatch_rows = list(mismatch_by_id.values())
    for item in selection_report.get("hard_blocked", []):
        record = _record_from_selection_item(item)
        row = score_by_id.get(str(record.get("story_bundle_id") or ""), {})
        hard_blocked_rows.append(
            {
                "title": str(row.get("visible_title") or row.get("title") or ""),
                "primary_metadata_title": str(row.get("primary_title") or ""),
                "source": str(row.get("source") or ""),
                "story_fingerprint": str(record.get("story_fingerprint") or ""),
                "reasons": list(dict.fromkeys(str(reason) for reason in item.get("reasons", []))),
            }
        )
    reconsideration_rows = []
    for row in suppressed_review_rows:
        score_row = score_by_id.get(str(row.get("story_bundle_id") or ""), {})
        reconsideration_rows.append(
            {
                **row,
                "board_score": score_row.get("board_score", 0),
                "total_score": score_row.get("total_score", 0),
                "second_search_accepted_links_count": score_row.get(
                    "second_search_accepted_links_count", 0
                ),
                "second_search_query_types": score_row.get("second_search_query_types", []),
                "reconsideration_status": _reconsideration_status(score_row, row),
            }
        )
    hard_blocked_ids = {
        str(_record_from_selection_item(item).get("story_bundle_id") or "")
        for item in selection_report.get("hard_blocked", [])
    }
    eligible_score_rows = [
        row
        for row in score_rows
        if str(row.get("story_bundle_id") or "") not in hard_blocked_ids
        and str(row.get("story_bundle_id") or "") not in mismatch_by_id
        and not row.get("mismatch_reasons")
    ]
    top_board_score_rows = sorted(
        eligible_score_rows,
        key=lambda item: float(item.get("board_score") or 0),
        reverse=True,
    )[:15]
    downranked_rows = [
        row
        for row in high_total_rows
        if "board_score_downranked_below_selected_floor" in row.get("why_excluded", [])
    ][:15]
    review_adjustment_rows = [
        row
        for row in score_rows
        if row.get("review_adjustments") or row.get("review_editorial_roles")
    ]
    hook_subblock_rows = [
        row
        for row in review_adjustment_rows
        if set(row.get("review_editorial_roles") or []).intersection(
            {"hook_only", "sub_block"}
        )
        or set(row.get("review_adjustments") or []).intersection({"hook_only", "sub_block"})
    ]
    do_not_rescue_rows = [
        row
        for row in review_adjustment_rows
        if set(row.get("review_adjustments") or []).intersection(
            {
                "sports_primary_downrank",
                "ai_grand_discourse_downrank",
                "past_topic_overlap_downrank",
            }
        )
        or set(row.get("review_failure_modes") or []).intersection(
            {"weak_audience_bridge", "too_familiar"}
        )
    ]
    needs_new_angle_rows = [
        row
        for row in review_adjustment_rows
        if "needs_new_angle" in set(row.get("review_adjustments") or [])
    ]
    payload = {
        "run_date": digest_date,
        "use_board_score": bool(selection_report.get("use_board_score")),
        "selected_count": len(selected_rows),
        "score_rows_count": len(score_rows),
        "mismatch_guarded_count": len(mismatch_rows),
        "reviewed_suppressed_count": len(suppressed_review_rows),
        "hard_blocked_count": len(selection_report.get("hard_blocked") or []),
        "selected": selected_rows,
        "suppressed_high_total_score_candidates": high_total_rows[:25],
        "reviewed_candidate_suppression": suppressed_review_rows,
        "reviewed_candidate_reconsideration_queue": reconsideration_rows,
        "board_mismatch_guard": mismatch_rows,
        "hard_blocked": hard_blocked_rows,
        "review_derived_board_adjustments": review_adjustment_rows[:25],
        "hook_subblock_queue": hook_subblock_rows[:25],
        "do_not_rescue_with_links": do_not_rescue_rows[:25],
        "needs_new_angle": needs_new_angle_rows[:25],
        "board_score_distribution": {
            "total_candidate_count": len(score_rows),
            "eligible_count": len(eligible_score_rows),
            "selected_count": len(selected_rows),
            "selected_board_score_floor": selected_board_floor,
            "board_score_top_candidates": top_board_score_rows,
            "total_score_top_but_board_score_downranked": downranked_rows,
        },
    }
    json_path = path.with_suffix(".json")
    path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    lines = [
        f"# Jibi Board Score Report — {digest_date}",
        "",
        "Report-only review-board scoring layer. This does not change the visible sheet schema.",
        "",
        f"- use_board_score: {str(payload['use_board_score']).lower()}",
        f"- selected_count: {payload['selected_count']}",
        f"- mismatch_guarded_count: {payload['mismatch_guarded_count']}",
        f"- reviewed_suppressed_count: {payload['reviewed_suppressed_count']}",
        f"- hard_blocked_count: {payload['hard_blocked_count']}",
        "",
        "## Selected Board Candidates",
        "",
        (
            "| title | total_score | board_score | source_role | story_role | "
            "seed_quality | selected reasons | risks |"
        ),
        "| --- | ---: | ---: | --- | --- | --- | --- | --- |",
    ]
    for row in selected_rows:
        lines.append(
            "| "
            + " | ".join(
                [
                    _table_cell(row.get("title", "")),
                    f"{float(row.get('total_score') or 0):g}",
                    f"{float(row.get('board_score') or 0):g}",
                    _table_cell(row.get("source_role", "")),
                    _table_cell(row.get("story_role", "")),
                    _table_cell(row.get("seed_quality_classification", "")),
                    _table_cell("; ".join(row.get("board_score_reasons", [])[:6])),
                    _table_cell("; ".join(row.get("mismatch_reasons", [])) or "-"),
                ]
            )
            + " |"
        )
    if not selected_rows:
        lines.append("| none | 0 | 0 | none | none | none | none | none |")

    lines.extend(
        [
            "",
            "## Suppressed High Total Score Candidates",
            "",
            "| title | total_score | board_score | why excluded | reviewed history |",
            "| --- | ---: | ---: | --- | --- |",
        ]
    )
    for row in high_total_rows[:20]:
        lines.append(
            "| "
            + " | ".join(
                [
                    _table_cell(row.get("title", "")),
                    f"{float(row.get('total_score') or 0):g}",
                    f"{float(row.get('board_score') or 0):g}",
                    _table_cell(", ".join(row.get("why_excluded", []))),
                    _table_cell(", ".join(row.get("history_statuses", [])) or "-"),
                ]
            )
            + " |"
        )
    if not high_total_rows:
        lines.append("| none | 0 | 0 | none | none |")

    lines.extend(
        [
            "",
            "## Reviewed Candidate Suppression",
            "",
            "| title | previous date | status | reviewers | required action | excerpt |",
            "| --- | --- | --- | --- | --- | --- |",
        ]
    )
    for row in suppressed_review_rows:
        lines.append(
            "| "
            + " | ".join(
                [
                    _table_cell(row.get("title", "")),
                    _table_cell(", ".join(row.get("previous_review_dates", [])) or "unknown"),
                    _table_cell(", ".join(row.get("history_statuses", [])) or "reviewed_before"),
                    _table_cell(", ".join(row.get("reviewers", [])) or "unknown"),
                    _table_cell(row.get("required_action", "")),
                    _table_cell(row.get("review_excerpt", "")),
                ]
            )
            + " |"
        )
    if not suppressed_review_rows:
        lines.append("| none | none | none | none | none | none |")

    lines.extend(
        [
            "",
            "## Reviewed Candidate Reconsideration Queue",
            "",
            "| title | total_score | board_score | second-search links | query types | status |",
            "| --- | ---: | ---: | ---: | --- | --- |",
        ]
    )
    for row in reconsideration_rows:
        lines.append(
            "| "
            + " | ".join(
                [
                    _table_cell(row.get("title", "")),
                    f"{float(row.get('total_score') or 0):g}",
                    f"{float(row.get('board_score') or 0):g}",
                    str(row.get("second_search_accepted_links_count", 0)),
                    _table_cell(", ".join(row.get("second_search_query_types", [])) or "-"),
                    _table_cell(row.get("reconsideration_status", "")),
                ]
            )
            + " |"
        )
    if not reconsideration_rows:
        lines.append("| none | 0 | 0 | 0 | none | none |")

    lines.extend(
        [
            "",
            "## Board Mismatch Guard",
            "",
            (
                "| visible title | primary metadata title | source | story_fingerprint | "
                "mismatch reason | required action |"
            ),
            "| --- | --- | --- | --- | --- | --- |",
        ]
    )
    for row in mismatch_rows:
        lines.append(
            "| "
            + " | ".join(
                [
                    _table_cell(row.get("visible_title", "")),
                    _table_cell(row.get("primary_metadata_title", "")),
                    _table_cell(row.get("source", "")),
                    _table_cell(row.get("story_fingerprint", "")),
                    _table_cell(", ".join(row.get("mismatch_reason", []))),
                    _table_cell(row.get("required_action", "")),
                ]
            )
            + " |"
        )
    if not mismatch_rows:
        lines.append("| none | none | none | none | none | none |")

    lines.extend(
        [
            "",
            "## Hard Blocked",
            "",
            "| title | source | reasons |",
            "| --- | --- | --- |",
        ]
    )
    for row in hard_blocked_rows[:20]:
        lines.append(
            "| "
            + " | ".join(
                [
                    _table_cell(row.get("title", "")),
                    _table_cell(row.get("source", "")),
                    _table_cell(", ".join(row.get("reasons", [])) or "hard_blocked"),
                ]
            )
            + " |"
        )
    if not hard_blocked_rows:
        lines.append("| none | none | none |")

    lines.extend(
        [
            "",
            "## Review-Derived Board Adjustments",
            "",
            "| title | total_score | board_score | roles | adjustments | reasons |",
            "| --- | ---: | ---: | --- | --- | --- |",
        ]
    )
    for row in review_adjustment_rows[:20]:
        lines.append(
            "| "
            + " | ".join(
                [
                    _table_cell(row.get("title", "")),
                    f"{float(row.get('total_score') or 0):g}",
                    f"{float(row.get('board_score') or 0):g}",
                    _table_cell(", ".join(row.get("review_editorial_roles", [])) or "-"),
                    _table_cell(", ".join(row.get("review_adjustments", [])) or "-"),
                    _table_cell("; ".join(row.get("board_score_reasons", [])[-5:])),
                ]
            )
            + " |"
        )
    if not review_adjustment_rows:
        lines.append("| none | 0 | 0 | none | none | none |")

    lines.extend(
        [
            "",
            "## Hook/Sub-block Queue",
            "",
            "| title | board_score | role | suggested use |",
            "| --- | ---: | --- | --- |",
        ]
    )
    for row in hook_subblock_rows[:20]:
        roles = set(row.get("review_editorial_roles") or [])
        suggested = "opening_hook_only" if "hook_only" in roles else "one_page_sub_block"
        lines.append(
            "| "
            + " | ".join(
                [
                    _table_cell(row.get("title", "")),
                    f"{float(row.get('board_score') or 0):g}",
                    _table_cell(", ".join(row.get("review_editorial_roles", [])) or "-"),
                    suggested,
                ]
            )
            + " |"
        )
    if not hook_subblock_rows:
        lines.append("| none | 0 | none | none |")

    lines.extend(
        [
            "",
            "## Do Not Rescue With Links",
            "",
            "| title | board_score | reason |",
            "| --- | ---: | --- |",
        ]
    )
    for row in do_not_rescue_rows[:20]:
        reason = ", ".join(
            [
                *[str(item) for item in row.get("review_adjustments", [])],
                *[str(item) for item in row.get("review_failure_modes", [])],
            ]
        )
        lines.append(
            "| "
            + " | ".join(
                [
                    _table_cell(row.get("title", "")),
                    f"{float(row.get('board_score') or 0):g}",
                    _table_cell(reason or "review_downrank"),
                ]
            )
            + " |"
        )
    if not do_not_rescue_rows:
        lines.append("| none | 0 | none |")

    lines.extend(
        [
            "",
            "## Needs New Angle",
            "",
            "| title | board_score | action |",
            "| --- | ---: | --- |",
        ]
    )
    for row in needs_new_angle_rows[:20]:
        lines.append(
            "| "
            + " | ".join(
                [
                    _table_cell(row.get("title", "")),
                    f"{float(row.get('board_score') or 0):g}",
                    "find_new_angle_before_reposting",
                ]
            )
            + " |"
        )
    if not needs_new_angle_rows:
        lines.append("| none | 0 | none |")

    lines.extend(
        [
            "",
            "## Board Score Distribution",
            "",
            f"- total_candidate_count: {len(score_rows)}",
            f"- eligible_count: {len(score_rows)}",
            f"- selected_count: {len(selected_rows)}",
            f"- selected_board_score_floor: {selected_board_floor:g}",
            "",
            "### Top Board Score Candidates",
            "",
            "| title | total_score | board_score | reasons |",
            "| --- | ---: | ---: | --- |",
        ]
    )
    for row in top_board_score_rows[:10]:
        lines.append(
            "| "
            + " | ".join(
                [
                    _table_cell(row.get("title", "")),
                    f"{float(row.get('total_score') or 0):g}",
                    f"{float(row.get('board_score') or 0):g}",
                    _table_cell("; ".join(row.get("board_score_reasons", [])[:5])),
                ]
            )
            + " |"
        )
    if not top_board_score_rows:
        lines.append("| none | 0 | 0 | none |")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path, json_path


def _alternate_why_not_primary(
    candidate: dict[str, Any],
    top: list[dict[str, Any]],
) -> str:
    if not candidate:
        return "evidence_cluster_or_no_primary_candidate"
    candidate_id = str(candidate.get("candidate_id") or "")
    top_ids = {str(item.get("candidate_id") or "") for item in top}
    if candidate_id in top_ids:
        return "top_candidate_but_excluded_from_alternate_selection_scope"
    reasons = _top_exclusion_reasons(
        candidate,
        top_ids,
        Counter(str(item.get("source") or "unknown") for item in top),
        rendered_top_count=len(top),
        limit=DEFAULT_REVIEW_BOARD_LIMIT,
        max_per_source=3,
        min_score=DEFAULT_TOP_MIN_SCORE,
    )
    return ", ".join(reasons) if reasons else "high_score_near_miss_or_story_bundle_backfill"


def _alternate_review_board_markdown(
    *,
    digest_date: str,
    selected: list[dict[str, Any]],
    skipped: list[dict[str, Any]],
    candidate_by_id: dict[str, dict[str, Any]],
    top: list[dict[str, Any]],
    current_keys: set[str],
    reviewed_keys: set[str],
    include_reviewed: bool,
) -> str:
    lines = [
        f"# Jibi Alternate Review Board — {digest_date}",
        "",
        "Dry-run/report-only alternate batch. The live `Jibi` sheet was not replaced.",
        "",
        f"- selected_rows: {len(selected)}",
        f"- skipped_current_or_reviewed: {len(skipped)}",
        f"- current_board_exclusion_keys: {len(current_keys)}",
        f"- reviewed_history_exclusion_keys: {len(reviewed_keys)}",
        f"- include_reviewed: {str(include_reviewed).lower()}",
        "",
        "## Alternate Rows",
        "",
        "| title | source | score | bundle_type | why_not_primary_board | suggested_action |",
        "| --- | --- | ---: | --- | --- | --- |",
    ]
    for record in selected:
        candidate = _record_representative_candidate(record, candidate_by_id) or {}
        lines.append(
            "| "
            + " | ".join(
                [
                    _table_cell(record.get("bundle_title") or candidate.get("title") or ""),
                    _table_cell(candidate.get("source", "unknown")),
                    f"{_total_score(candidate):g}",
                    _table_cell(record.get("bundle_type", "")),
                    _table_cell(_alternate_why_not_primary(candidate, top)),
                    _table_cell(record.get("suggested_operator_action", "")),
                ]
            )
            + " |"
        )
    if not selected:
        lines.append("| none | unknown | 0 | none | no alternate candidates | none |")
    lines.extend(
        [
            "",
            "## Exclusion Notes",
            "",
            "- current_board: already visible on the current primary review board.",
            "- reviewed_history: reviewer comments already exist in local review history.",
            "",
            "## Skipped Examples",
            "",
            "| title | reasons |",
            "| --- | --- |",
        ]
    )
    for item in skipped[:20]:
        record = item["record"]
        lines.append(
            f"| {_table_cell(record.get('bundle_title', ''))} | "
            f"{_table_cell(', '.join(item['reasons']))} |"
        )
    if not skipped:
        lines.append("| none | none |")
    return "\n".join(lines) + "\n"


def _bundle_review_metadata_row(
    *,
    row: dict[str, Any],
    record: dict[str, Any],
    candidate: dict[str, Any],
    review_item_id: str,
    registered_at: str,
    run_date: str,
    sub_links: str,
    syuka_similarity: dict[str, Any] | None = None,
    auto_title: str = "",
    auto_description: str = "",
    editorial_override: dict[str, Any] | None = None,
    board_score: dict[str, Any] | None = None,
) -> dict[str, Any]:
    so_what = _candidate_so_what(candidate)
    metadata = {
        "ID": review_item_id,
        "review_item_id": review_item_id,
        "registered_at": registered_at,
        "run_date": run_date,
        "story_fingerprint": str(record.get("story_fingerprint") or ""),
        "story_bundle_id": str(record.get("story_bundle_id") or ""),
        "title": str(row.get("제목") or record.get("bundle_title") or ""),
        "description": str(row.get("설명") or ""),
        "past_video": str(row.get("과거 영상") or ""),
        "reference": str(row.get("과거 영상") or row.get("참고") or ""),
        "auto_title": auto_title or str(row.get("제목") or ""),
        "auto_description": auto_description or str(row.get("설명") or ""),
        "editorial_override_applied": bool(editorial_override),
        "editorial_override_reason": (
            str(editorial_override.get("reason") or "") if editorial_override else ""
        ),
        "score": row.get("점수", ""),
        "total_score": _total_score(candidate),
        "main_link": str(row.get("메인 링크") or ""),
        "sub_links": [link.strip() for link in sub_links.split("|") if link.strip()],
        "source": str(candidate.get("source") or ""),
        "source_id": str(candidate.get("source_id") or ""),
        "source_role": str(candidate.get("source_role_class") or "unknown"),
        "source_role_class": str(candidate.get("source_role_class") or "unknown"),
        "seed_type": str(candidate.get("seed_type") or "unknown"),
        "so_what": so_what,
        "seed_quality_classification": str(
            candidate.get("seed_quality_classification")
            or so_what.get("seed_quality_classification")
            or ""
        ),
        "seed_quality_reasons": candidate.get("seed_quality_reasons")
        or so_what.get("seed_quality_reasons")
        or [],
        "story_role": str(candidate.get("story_role") or so_what.get("story_role") or ""),
        "story_role_reasons": candidate.get("story_role_reasons")
        or so_what.get("story_role_reasons")
        or [],
        "bundle_type": str(record.get("bundle_type") or ""),
        "suggested_operator_action": str(record.get("suggested_operator_action") or ""),
        "primary_candidate_id": str(record.get("primary_candidate_id") or ""),
        "supporting_candidate_ids": [
            str(item) for item in record.get("supporting_candidate_ids", [])
        ],
        "evidence_candidate_ids": [
            str(item) for item in record.get("evidence_candidate_ids", [])
        ],
        "candidate_count": int(record.get("candidate_count") or 0),
    }
    if board_score:
        metadata["board_score"] = board_score.get("board_score")
        metadata["board_score_base"] = board_score.get("total_score")
        metadata["board_score_reasons"] = board_score.get("reasons", [])
    if syuka_similarity:
        metadata["syuka_similarity"] = syuka_similarity
    return metadata


def _bundle_judgment(record: dict[str, Any], fit: str) -> str:
    bundle_type = _human_bundle_type(str(record.get("bundle_type") or "")) or (
        _human_storyline_fit(fit)
    )
    next_step = _human_operator_action(str(record.get("suggested_operator_action") or ""))
    if bundle_type and next_step:
        return f"{bundle_type}. 다음: {next_step}"
    return bundle_type or next_step


def _compact_text(value: object) -> str:
    return " ".join(str(value or "").split())


def _clean_review_title(value: object) -> str:
    title = _compact_text(value)
    title = re.sub(r"^\[[^\]]+\]\s*", "", title)
    title = re.sub(r"^\([^)]*(?:보도자료|보도참고자료)[^)]*\)\s*", "", title)
    title = re.sub(r"^\S+·", "", title)
    return title.strip(" -:") or _compact_text(value)


def _human_review_title(
    record: dict[str, Any],
    candidate: dict[str, Any],
    candidate_title: str,
) -> str:
    return review_board_title(record, candidate, candidate_title)


def _human_bundle_type(value: str) -> str:
    return {
        "merged_seed": "묶어서 볼 핵심 주제",
        "standalone_seed": "단독 검토 후보",
        "needs_external_sources": "보강하면 살아날 후보",
        "evidence_cluster": "큰 이야기의 근거 자료",
    }.get(value, "")


def _human_storyline_fit(value: str) -> str:
    return {
        "standalone_seed": "방송 주제로 키울 수 있음",
        "merge_with_other_candidate": "비슷한 후보와 합쳐서 검토",
        "evidence_only": "단독 주제보다는 근거 자료",
        "needs_external_sources": "외부 자료가 붙으면 살아남",
        "demote_or_reject": "단독 후보로는 약함",
    }.get(value, "")


def _human_operator_action(value: str) -> str:
    return {
        "review_primary_and_bundle_supporting": "대표 후보만 보고 나머지는 보조 자료로 묶기",
        "review_as_core_seed": "핵심 후보로 우선 검토",
        "review_as_explainer_seed": "설명형 후보로 검토",
        "split_or_bundle_after_human_review": "같은 이야기인지 사람이 나눠 보기",
        "collect_second_source_and_numbers": "숫자와 두 번째 출처를 보강",
        "collect_price_life_or_industry_data": "가격·생활 영향·산업 자료를 보강",
        "attach_to_larger_story": "큰 기획의 근거로 붙이기",
        "use_only_inside_market_structure_story": "시장 구조 이야기 안에서만 사용",
        "reject_as_standalone_seed": "단독 후보에서는 내리기",
        "find_brand_or_market_structure_angle": "투자 얘기가 아닌 구조·브랜드 각도 찾기",
        "bundle_before_sheet_review": "같은 주제 후보와 먼저 합치기",
        "manual_editorial_review": "사람이 맥락 확인",
    }.get(value, "")


def _human_reason(value: str) -> str:
    parts = [
        part.strip()
        for part in _compact_text(value).replace(" / ", "|").split("|")
        if part.strip()
    ]
    translated: list[str] = []
    for part in parts:
        if part.startswith("merge_target="):
            translated.append("같은 큰 질문을 다루는 후보와 묶어 검토하면 좋습니다.")
            continue
        translated.append(
            {
                "BOK 청년 노동시장 후보들이 같은 큰 질문을 공유함": (
                    "한국은행 청년 노동시장 자료들이 같은 문제를 다른 각도에서 봅니다."
                ),
                "무료배달, 수수료, 업주 부담이 같은 플랫폼 비용 배분 이야기로 묶임": (
                    "무료배달, 수수료, 업주 부담이 같은 비용 배분 문제로 이어집니다."
                ),
                "공공 AI 활용, 치안, 행정 보고서, 직무 전환 후보를 함께 검토": (
                    "공공 AI 활용과 책임 문제를 한 묶음으로 볼 수 있습니다."
                ),
                "회의/현황/절차성 보도자료는 단독 seed보다 큰 이야기의 근거로 검토": (
                    "회의나 현황 보도자료라 단독 주제보다는 큰 이야기의 근거로 적합합니다."
                ),
                "research_note_has_structural_numbers": (
                    "연구노트라 숫자와 구조 설명이 있어 단독 주제로 키우기 좋습니다."
                ),
                "official_release_meeting_or_evidence_default": (
                    "공식 보도자료지만 회의·현황 성격이 강해 근거 자료에 가깝습니다."
                ),
                "official_release_seed_needs_independent_context": (
                    "공식자료만으로는 부족해 독립 기사나 통계가 더 필요합니다."
                ),
                "market_schedule_or_ipo_context": (
                    "시장 일정 정보라 단독 후보보다는 맥락 자료에 가깝습니다."
                ),
                "single_company_or_investment_frame": (
                    "단일 기업·투자 프레임이 강해 단독 후보로는 위험합니다."
                ),
                "finance_story_needs_non_investment_frame": (
                    "투자 판단이 아니라 산업 구조나 자금 조달 이야기로 바꿔야 합니다."
                ),
                "public_wire_story_has_concrete_broadcast_hook": (
                    "생활·현장 장면이 있어 숫자와 두 번째 출처가 붙으면 살아날 수 있습니다."
                ),
                "academic_explainer_has_mechanism": (
                    "원리를 설명하는 구조가 있어 설명형 후보로 볼 수 있습니다."
                ),
                "story_fit_uncertain": (
                    "방송 주제로 자랄 수 있는지 사람이 한 번 더 봐야 합니다."
                ),
                "generic why without specific template": (
                    "아직 구체 템플릿이 약해 사람이 각도를 확인해야 합니다."
                ),
                "generic_why_without_specific_template": (
                    "아직 구체 템플릿이 약해 사람이 각도를 확인해야 합니다."
                ),
                "lifestyle hook but source is promotional": (
                    "생활 hook은 있지만 원문이 홍보성이라 보강이 필요합니다."
                ),
                "lifestyle_hook_but_source_is_promotional": (
                    "생활 hook은 있지만 원문이 홍보성이라 보강이 필요합니다."
                ),
            }.get(part, part.replace("_", " "))
        )
    deduped: list[str] = []
    for part in translated:
        if part and part not in deduped:
            deduped.append(part)
    return " ".join(deduped)


def _humanize_review_text(value: object) -> str:
    text = _compact_text(value)
    replacements = {
        "seed 후보": "방송 후보",
        "seed로": "방송 소재로",
        "seed": "방송 소재",
        "evidence를": "근거 자료를",
        "evidence": "근거 자료",
    }
    for source, replacement in replacements.items():
        text = text.replace(source, replacement)
    return text


def _source_cue(candidate: dict[str, Any]) -> str:
    source = _compact_text(candidate.get("source"))
    title = _clean_review_title(candidate.get("title"))
    if source and title:
        return f"출처/원문: {source} — {title}"
    if source:
        return f"출처: {source}"
    if title:
        return f"원문 제목: {title}"
    return ""


def _board_score_grade(score: float) -> str:
    if score >= BOARD_SCORE_GRADE_CUTS["A"]:
        return "A"
    if score >= BOARD_SCORE_GRADE_CUTS["B"]:
        return "B"
    if score >= BOARD_SCORE_GRADE_CUTS["C"]:
        return "C"
    return "D"


def _score_display(
    candidate: dict[str, Any],
    *,
    board_score: dict[str, Any] | None = None,
) -> str:
    if not candidate:
        return ""
    if board_score:
        score = round(float(board_score.get("board_score") or 0))
        grade = _board_score_grade(score)
        return f"{grade} · {score}점"
    score = round(_total_score(candidate))
    grade = _compact_text(candidate.get("final_grade")) or _board_score_grade(score)
    return f"{grade} · {score}점"


def _board_text(record: dict[str, Any], candidate: dict[str, Any]) -> str:
    return " ".join(
        [
            str(record.get("bundle_title") or ""),
            str(record.get("why_bundle") or ""),
            str(candidate.get("title") or ""),
            str(candidate.get("summary") or ""),
            str(candidate.get("why_interesting") or ""),
            str(candidate.get("seed_type") or ""),
            str(candidate.get("source_role_class") or ""),
        ]
    ).lower()


def _board_why_sentence(
    record: dict[str, Any],
    candidate: dict[str, Any],
    reason: str,
) -> str:
    text = _board_text(record, candidate)
    if "청년" in text and any(term in text for term in ("쉬었음", "경제활동참가율", "노동시장")):
        return "한국은행 청년 노동시장 자료들이 같은 문제를 다른 지표로 보고 있습니다."
    if _has_tokenization_bridge_signal(text):
        return "자산 토큰화가 제도권 금융 인프라로 들어오는 흐름을 보여주는 후보입니다."
    if any(term in text for term in ("public_ai", "공공 ai", "ai 드론", "ai 노사", "ai 도입")):
        return "공공기관과 현장에서 AI가 실제 업무에 들어오는 사례입니다."
    if "양파" in text:
        return (
            "작아 보이는 양파 특판 보도자료지만 농산물 가격과 정부 개입을 "
            "볼 수 있는 생활경제 후보입니다."
        )
    if any(term in text for term in ("무료배달", "배달비", "수수료", "플랫폼")):
        return "무료배달과 수수료 부담이 플랫폼 비용 배분 문제로 이어지는 후보입니다."
    if any(term in text for term in ("고유가", "유가", "피해지원금", "지원금")):
        return "고유가 지원 현황을 통해 에너지 가격 충격의 생활 영향을 볼 수 있는 근거 자료입니다."
    if str(record.get("bundle_type")) == "evidence_cluster":
        return "공식자료 성격이 강해 단독 주제보다는 큰 이야기의 근거로 쓰기 좋은 후보입니다."
    if str(candidate.get("source_role_class")) == "academic_explainer":
        return "해외 해설 기사라 사건 자체보다 작동 원리를 설명하는 데 강점이 있습니다."
    readable_reason = _human_reason(reason)
    return readable_reason or (
        "Jibi가 오늘 후보군 안에서 비교적 방송 소재 가능성이 있다고 본 항목입니다."
    )


def _board_growth_sentence(record: dict[str, Any], candidate: dict[str, Any]) -> str:
    text = _board_text(record, candidate)
    if "청년" in text and any(term in text for term in ("쉬었음", "경제활동참가율", "노동시장")):
        return (
            "실업자가 아닌 '쉬었음'과 경제활동참가율을 묶으면 "
            "청년 노동시장 이탈 이야기로 커질 수 있습니다."
        )
    if _has_tokenization_bridge_signal(text):
        return (
            "부동산·채권·권리를 잘게 쪼개 거래하는 구조로 풀면 "
            "금융 제도와 코인 이후의 변화를 함께 설명할 수 있습니다."
        )
    if any(term in text for term in ("public_ai", "공공 ai", "ai 드론", "ai 노사", "ai 도입")):
        return "행정 효율이 올라가는 만큼 보고서 책임, 오판, 감시 기준 문제가 같이 생깁니다."
    if "양파" in text:
        return (
            "산지 가격, 마트 가격, 소비촉진 예산을 붙이면 "
            "농산물 가격의 정치경제학으로 키울 수 있습니다."
        )
    if any(term in text for term in ("무료배달", "배달비", "수수료", "플랫폼")):
        return (
            "소비자 편의 뒤에서 누가 비용을 내는지 보여주면 "
            "앱 경제와 자영업 부담 이야기로 자랄 수 있습니다."
        )
    if any(term in text for term in ("고유가", "유가", "피해지원금", "지원금")):
        return (
            "유가, 물류비, 지원금 지급 경로를 붙이면 "
            "멀리 있는 가격 충격이 생활비가 되는 과정을 설명할 수 있습니다."
        )
    if str(record.get("bundle_type")) == "evidence_cluster":
        return "다른 기사나 통계와 붙을 때 정책 대응의 공식 확인 자료로 가치가 있습니다."
    if str(candidate.get("source_role_class")) == "academic_explainer":
        return "한국 시청자가 아는 사례와 연결하면 설명형 소재로 검토할 수 있습니다."
    return "숫자, 현장 사례, 한국 연결고리가 붙으면 하나의 설명형 이야기로 키울 수 있습니다."


def _board_need_sentence(
    record: dict[str, Any],
    candidate: dict[str, Any],
    evidence_text: str,
    related_titles: str,
    history_status: str,
) -> str:
    needs: list[str] = []
    if evidence_text:
        needs.append(evidence_text)
    action = str(record.get("suggested_operator_action") or "")
    if "collect_second_source" in action:
        needs.append("숫자와 두 번째 출처")
    elif "collect_price" in action:
        needs.append("가격·생활 영향·산업 자료")
    elif "attach_to_larger_story" in action:
        needs.append("이 자료를 붙일 더 큰 주제")
    if related_titles:
        needs.append("서브 링크의 관련 후보")
    status_text = _history_sentence(history_status)
    base = " / ".join(dict.fromkeys(item for item in needs if item))
    if base and status_text:
        return f"확인할 것: {base}. {status_text}"
    if base:
        return f"확인할 것: {base}."
    return status_text or "추가 출처를 붙여 실제 방송 소재인지 확인하면 좋습니다."


def _history_sentence(status: str) -> str:
    return {
        "seen_before": "이전에 보드에 올라온 적이 있어 새 각도인지 확인하세요.",
        "reviewed_before": "이전에 사람이 리뷰한 주제라 지난 의견과 비교하세요.",
        "rejected_before": "이전에 reject 의견이 있던 주제라 다시 올릴 이유가 있는지 확인하세요.",
        "promoted_before": "이전에 seed 의견이 있던 주제라 후속 업데이트인지 확인하세요.",
    }.get(status, "")


def _human_description(
    *,
    candidate: dict[str, Any],
    record: dict[str, Any],
    jibi_judgment: str,
    reason: str,
    related_titles: str,
    history_status: str,
) -> str:
    del jibi_judgment, reason
    return build_review_board_copy(
        record=record,
        candidate=candidate,
        candidate_title=str(record.get("primary_title") or candidate.get("title") or ""),
        related_titles=related_titles,
        history_status=history_status,
    ).description


def _syuka_similarity_reference(syuka_similarity: dict[str, Any] | None) -> str:
    if not syuka_similarity:
        return ""
    recommendation = str(syuka_similarity.get("recommendation") or "")
    display_on_board = bool(syuka_similarity.get("display_on_board"))
    title = str(syuka_similarity.get("top_match_title") or "").strip()
    if not title or recommendation not in {
        "duplicate",
        "adjacent",
        "needs_human_check",
    }:
        return ""
    if recommendation != "duplicate" and not display_on_board:
        return ""
    date_text = _format_video_date(syuka_similarity.get("upload_date"))
    view_text = _format_metric_count(syuka_similarity.get("view_count"), "조회")
    like_text = _format_metric_count(syuka_similarity.get("like_count"), "좋아요")
    metrics = ", ".join(item for item in [date_text, view_text, like_text] if item)
    note = {
        "duplicate": "강한 중복 가능",
        "adjacent": "배경/인접 주제",
        "needs_human_check": "약한 유사도",
    }.get(recommendation, "")
    if metrics and note:
        return f"{title} ({metrics}) · {note}"
    if metrics:
        return f"{title} ({metrics})"
    if note:
        return f"{title} · {note}"
    return title


def _format_video_date(value: object) -> str:
    text = str(value or "").strip()
    if re.fullmatch(r"\d{8}", text):
        return f"{text[:4]}-{text[4:6]}-{text[6:]}"
    return text


def _format_metric_count(value: object, label: str) -> str:
    if value in {None, ""}:
        return ""
    try:
        count = int(value)
    except (TypeError, ValueError):
        return ""
    if count >= 10_000:
        number = count / 10_000
        if number >= 100 or number.is_integer():
            return f"{label} {number:.0f}만"
        return f"{label} {number:.1f}만"
    return f"{label} {count:,}"


def _join_distinct_reason(primary: str, secondary: str) -> str:
    if not secondary or secondary == primary:
        return primary
    return f"{primary} / {secondary}"


def _related_bundle_titles(record: dict[str, Any]) -> str:
    related = [
        *[f"묶인: {title}" for title in record.get("supporting_titles", [])],
        *[f"근거: {title}" for title in record.get("evidence_titles", [])],
    ]
    return " | ".join(related)


def _related_bundle_links(
    record: dict[str, Any],
    candidate_by_id: dict[str, dict[str, Any]],
    *,
    limit: int | None = None,
) -> str:
    links: list[str] = []
    for item_id in [
        *record.get("supporting_candidate_ids", []),
        *record.get("evidence_candidate_ids", []),
    ]:
        candidate = candidate_by_id.get(str(item_id))
        if not candidate:
            continue
        link = str(candidate.get("seed_url") or "").strip()
        if link and link not in links:
            links.append(link)
        if limit is not None and len(links) >= limit:
            break
    return " | ".join(links)


def _bundle_review_row(
    *,
    digest_date: str,
    registered_at: str,
    review_item_id: str,
    review_title: str,
    candidate: dict[str, Any],
    candidate_title: str,
    jibi_judgment: str,
    reason: str,
    sub_links: str,
    related_titles: str,
    record: dict[str, Any],
    history_status: str,
    syuka_similarity: dict[str, Any] | None = None,
    board_score: dict[str, Any] | None = None,
) -> dict[str, Any]:
    description = _human_description(
        candidate=candidate,
        record=record,
        jibi_judgment=jibi_judgment,
        reason=reason,
        related_titles=related_titles,
        history_status=history_status,
    )
    return {
        "일시": registered_at,
        "제목": review_title or candidate_title,
        "점수": _score_display(candidate, board_score=board_score),
        "메인 링크": candidate.get("seed_url", ""),
        "서브 링크": sub_links,
        "설명": description,
        "과거 영상": _syuka_similarity_reference(syuka_similarity),
        "리뷰-성원": "",
        "리뷰-동찬": "",
        "리뷰-형찬": "",
        "ID": review_item_id,
    }


def render_daily_digest(
    input_path: Path = paths.JIBI_SCORED_CANDIDATES_JSONL,
    output_dir: Path = paths.DAILY_DIGEST_DIR,
    digest_date: str | None = None,
    limit: int = 10,
    max_per_source: int = 3,
    review_board_limit: int | None = None,
    bundle_near_miss_limit: int | None = None,
    review_history_path: Path = paths.JIBI_REVIEW_BOARD_HISTORY_JSONL,
    editorial_overrides_path: Path | None = None,
    allow_reviewed_candidates: bool | None = None,
    use_board_score: bool | None = None,
) -> tuple[Path, Path, list[dict[str, Any]]]:
    date_value = _digest_date(digest_date)
    resolved_review_board_limit = (
        review_board_limit
        if review_board_limit is not None
        else _env_int("JIBI_REVIEW_BOARD_LIMIT", DEFAULT_REVIEW_BOARD_LIMIT)
    )
    resolved_bundle_near_miss_limit = (
        bundle_near_miss_limit
        if bundle_near_miss_limit is not None
        else _env_int("JIBI_BUNDLE_NEAR_MISS_LIMIT", DEFAULT_BUNDLE_NEAR_MISS_LIMIT)
    )
    candidates = read_jsonl(input_path) if input_path.exists() else []
    top = top_candidates(candidates, limit=limit, max_per_source=max_per_source)
    excluded = excluded_candidates(candidates)
    excluded_to_render = excluded if len(top) < limit else []
    md_path = output_dir / f"{date_value}.md"
    csv_path = output_dir / f"{date_value}_sheet_append_preview.csv"
    bundle_review_csv_path = output_dir / f"{date_value}_bundle_review_sheet.csv"
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text(
        render_markdown(top, date_value, excluded_to_render, all_candidates=candidates),
        encoding="utf-8",
    )
    write_sheet_preview(csv_path, top, date_value)
    write_bundle_review_sheet_preview(
        bundle_review_csv_path,
        candidates,
        top,
        date_value,
        review_board_limit=resolved_review_board_limit,
        bundle_near_miss_limit=resolved_bundle_near_miss_limit,
        review_history_path=review_history_path,
        syuka_similarity_report_path=_default_syuka_similarity_report_path(date_value),
        editorial_overrides_path=editorial_overrides_path,
        allow_reviewed_candidates=allow_reviewed_candidates,
        use_board_score=use_board_score,
    )
    write_quality_report(
        paths.REPORTS_DIR / f"jibi_quality_{date_value}.md",
        candidates,
        top,
        limit=limit,
        max_per_source=max_per_source,
        review_history_path=review_history_path,
        syuka_similarity_report_path=_default_syuka_similarity_report_path(date_value),
    )
    write_syuka_bridge_query_reports(
        run_date=date_value,
        candidates=candidates,
        top=top,
        review_history_path=review_history_path,
    )
    return md_path, csv_path, top


def render_alternate_review_board(
    input_path: Path = paths.JIBI_SCORED_CANDIDATES_JSONL,
    output_dir: Path = paths.DAILY_DIGEST_DIR,
    digest_date: str | None = None,
    limit: int = 10,
    max_per_source: int = 3,
    review_board_limit: int | None = None,
    bundle_near_miss_limit: int | None = None,
    review_history_path: Path = paths.JIBI_REVIEW_BOARD_HISTORY_JSONL,
    include_reviewed: bool | None = None,
) -> tuple[Path, Path, Path]:
    date_value = _digest_date(digest_date)
    resolved_review_board_limit = (
        review_board_limit
        if review_board_limit is not None
        else _env_int("JIBI_REVIEW_BOARD_LIMIT", DEFAULT_REVIEW_BOARD_LIMIT)
    )
    resolved_bundle_near_miss_limit = (
        bundle_near_miss_limit
        if bundle_near_miss_limit is not None
        else _env_int("JIBI_BUNDLE_NEAR_MISS_LIMIT", 50)
    )
    include_reviewed_value = (
        include_reviewed
        if include_reviewed is not None
        else _env_bool("JIBI_ALTERNATE_INCLUDE_REVIEWED")
    )
    candidates = read_jsonl(input_path) if input_path.exists() else []
    top = top_candidates(candidates, limit=limit, max_per_source=max_per_source)
    alt_csv_path = output_dir / f"{date_value}_bundle_review_alt_sheet.csv"
    report_path = paths.REPORTS_DIR / f"jibi_alternate_review_board_{date_value}.md"
    current_csv_path = output_dir / f"{date_value}_bundle_review_sheet.csv"
    return write_alternate_review_board_outputs(
        alt_csv_path,
        report_path,
        candidates,
        top,
        date_value,
        review_board_limit=resolved_review_board_limit,
        bundle_near_miss_limit=resolved_bundle_near_miss_limit,
        review_history_path=review_history_path,
        current_board_csv_path=current_csv_path,
        include_reviewed=include_reviewed_value,
        syuka_similarity_report_path=_default_syuka_similarity_report_path(date_value),
    )


def write_quality_report(
    path: Path,
    candidates: list[dict[str, Any]],
    top: list[dict[str, Any]],
    limit: int = 10,
    max_per_source: int = 3,
    min_score: float = DEFAULT_TOP_MIN_SCORE,
    review_history_path: Path = paths.JIBI_REVIEW_BOARD_HISTORY_JSONL,
    syuka_similarity_report_path: Path | None = None,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    source_counts = Counter(str(item.get("source") or "unknown") for item in top)
    seed_counts = Counter(str(item.get("seed_type") or "unknown") for item in top)
    action_counts = Counter(str(item.get("recommended_action") or "unknown") for item in candidates)
    raw_source_counts = Counter(str(item.get("source") or "unknown") for item in candidates)
    raw_role_counts = Counter(
        str(item.get("source_role_class") or "unknown") for item in candidates
    )
    top_role_counts = Counter(str(item.get("source_role_class") or "unknown") for item in top)
    quality_gate_pass = [item for item in candidates if _passes_top_quality_gate(item)]
    after_gate_source_counts = Counter(
        str(item.get("source") or "unknown") for item in quality_gate_pass
    )
    top_eligible = _top_eligible_candidates(candidates, min_score=min_score)
    selection_details = _select_top_with_role_cap_details(
        top_eligible,
        limit=limit,
        max_per_source=max_per_source,
    )
    source_role_cap_rows = _source_role_cap_status_rows(selection_details)
    cap_blocked_rows = _source_role_cap_blocked_rows(selection_details)
    top_eligible_source_counts = Counter(
        str(item.get("source") or "unknown") for item in top_eligible
    )
    top_ids = {str(item.get("candidate_id")) for item in top}
    quality_gated = [
        item for item in candidates if item.get("quality_flags") or item.get("failure_modes")
    ]
    quality_flagged = [item for item in candidates if item.get("quality_flags")]
    quality_flagged_source_counts = Counter(
        str(item.get("source") or "unknown") for item in quality_flagged
    )
    duplicate_grouped = [
        item for item in candidates if int(item.get("near_duplicate_count") or 1) > 1
    ]
    duplicate_primary = [
        item for item in candidates if item.get("near_duplicate_role") == "primary"
    ]
    failure_modes = Counter(
        mode
        for item in candidates
        for mode in item.get("failure_modes", [])
        if str(mode).strip()
    )
    empty_summary_counts = Counter(
        str(item.get("source") or "unknown")
        for item in candidates
        if "empty_summary" in item.get("quality_flags", [])
        or "empty_summary_domestic_business" in item.get("quality_flags", [])
    )
    freshness_by_source: dict[str, Counter[str]] = {}
    quality_flags_by_source: dict[str, Counter[str]] = {}
    source_policy_by_source: dict[str, str] = {}
    for item in candidates:
        source = str(item.get("source") or "unknown")
        freshness = str(item.get("freshness_status") or "unknown")
        freshness_by_source.setdefault(source, Counter())[freshness] += 1
        if item.get("source_freshness_policy"):
            source_policy_by_source[source] = str(item["source_freshness_policy"])
        flag_counter = quality_flags_by_source.setdefault(source, Counter())
        for flag in item.get("quality_flags", []):
            if str(flag).strip():
                flag_counter[str(flag)] += 1
    source_warning_codes = _source_warning_codes(
        raw_source_counts=raw_source_counts,
        source_counts=source_counts,
        top_eligible_source_counts=top_eligible_source_counts,
        freshness_by_source=freshness_by_source,
        empty_summary_counts=empty_summary_counts,
    )
    near_duplicate_groups = _near_duplicate_groups(candidates)
    calibration_warnings = _calibration_warnings(candidates, top)
    skew_warnings = _source_skew_warnings(source_counts, len(top))
    source_survival_rows = _source_survival_table(
        raw_source_counts=raw_source_counts,
        source_counts=source_counts,
        top_eligible_source_counts=top_eligible_source_counts,
        freshness_by_source=freshness_by_source,
        quality_flagged_source_counts=quality_flagged_source_counts,
        quality_flags_by_source=quality_flags_by_source,
        empty_summary_counts=empty_summary_counts,
        source_warning_codes=source_warning_codes,
    )
    near_miss_queue = _near_miss_queue(
        candidates,
        top_ids,
        top,
        limit=limit,
        max_per_source=max_per_source,
        min_score=min_score,
    )
    what_if_rows = _what_if_gate_simulation(
        candidates,
        top,
        limit=limit,
        max_per_source=max_per_source,
        min_score=min_score,
    )
    gate_reason_distribution = _top_gate_reason_distribution(
        candidates,
        top_ids,
        top,
        limit=limit,
        max_per_source=max_per_source,
        min_score=min_score,
    )
    calibration_summary = _calibration_summary(
        candidates=candidates,
        top=top,
        source_warning_codes=source_warning_codes,
        gate_reason_distribution=gate_reason_distribution,
        top_eligible_count=len(top_eligible),
        quality_flagged_count=len(quality_flagged),
        duplicate_grouped_count=len(duplicate_grouped),
    )
    source_recommendation_records = _source_recommendation_records(
        raw_source_counts=raw_source_counts,
        source_counts=source_counts,
        top_eligible_source_counts=top_eligible_source_counts,
        quality_flags_by_source=quality_flags_by_source,
        source_warning_codes=source_warning_codes,
        source_policy_by_source=source_policy_by_source,
    )
    source_recommendation_rows = _source_recommendation_table(
        source_recommendation_records,
    )
    source_allowlist_review_rows = _source_allowlist_review_queue(
        source_recommendation_records,
        raw_source_counts=raw_source_counts,
        source_counts=source_counts,
        top_eligible_source_counts=top_eligible_source_counts,
        quality_flags_by_source=quality_flags_by_source,
    )
    generic_specificity_examples = _generic_specificity_examples(
        candidates,
        top_ids,
        top,
        limit=limit,
        max_per_source=max_per_source,
        min_score=min_score,
    )
    generic_template_queue = _generic_template_improvement_queue(
        candidates,
        top_ids,
        top,
        limit=limit,
        max_per_source=max_per_source,
        min_score=min_score,
    )
    operator_summary = _operator_summary(
        candidates=candidates,
        top=top,
        top_eligible_count=len(top_eligible),
        quality_flagged_count=len(quality_flagged),
        duplicate_grouped_count=len(duplicate_grouped),
        source_warning_codes=source_warning_codes,
        gate_reason_distribution=gate_reason_distribution,
    )
    source_mix_review = _source_mix_experiment_review(
        candidates=candidates,
        top=top,
        raw_role_counts=raw_role_counts,
        top_role_counts=top_role_counts,
        raw_source_counts=raw_source_counts,
        source_counts=source_counts,
    )
    story_bundle_records = _story_bundle_records(candidates, top)
    story_bundle_rows = _story_bundle_review_rows(story_bundle_records)
    syuka_similarity_index = _load_syuka_similarity_index(syuka_similarity_report_path)
    syuka_similarity_lines = _syuka_similarity_summary_lines(syuka_similarity_index)
    review_history_index = _load_review_history_index(review_history_path)
    cross_run_story_rows = _cross_run_story_review_rows(
        story_bundle_records,
        review_history_index,
    )
    review_board_experiment_lines = _review_board_experiment_snapshot(
        story_bundle_records[:limit],
        candidates,
        review_history_index,
    )
    storyline_fit_rows = _storyline_fit_audit_rows(
        candidates,
        top,
    )
    so_what_summary = _so_what_summary_lines(candidates, top)
    promo_bulletin_rows = _promo_bulletin_downrank_rows(candidates)
    conditional_seed_rows = _conditional_seed_queue_rows(candidates)
    weak_audience_rows = _seed_quality_queue_rows(
        candidates,
        required_flags={"weak_audience_bridge"},
    )
    interesting_not_seed_rows = _seed_quality_queue_rows(
        candidates,
        classifications={"reject_or_downrank", "evidence_only"},
        required_so_what_labels={"conditional", "weak"},
    )
    conditional_system_issue_rows = _seed_quality_queue_rows(
        candidates,
        classifications={"conditional_seed"},
    )
    evidence_only_rows = _seed_quality_queue_rows(
        candidates,
        classifications={"evidence_only"},
    )
    downranked_examples = [
        item for item in candidates if item.get("quality_flags")
    ][:10]
    raw_top = candidates[:10]
    removed_from_top = [item for item in raw_top if str(item.get("candidate_id")) not in top_ids]
    generic_why_examples = [
        item
        for item in candidates
        if any(pattern in str(item.get("why_interesting", "")) for pattern in GENERIC_WHY_PATTERNS)
    ][:10]
    single_company_count = sum(
        1
        for item in candidates
        if "single_company_frame" in item.get("quality_flags", [])
        or "single_company_frame" in item.get("failure_modes", [])
    )
    political_count = sum(
        1 for item in candidates if "political_sensitivity" in item.get("risk_flags", [])
    )
    lines = [
        "# Jibi Candidate Quality Report",
        "",
        "## Summary",
        "",
        f"- candidates scored: {len(candidates)}",
        f"- top candidates: {len(top)}",
        f"- quality-gated candidates: {len(quality_gated)}",
        f"- single_company_frame count: {single_company_count}",
        f"- political_sensitivity count: {political_count}",
        "",
        "## Operator Summary",
        "",
        *operator_summary,
        "",
        "## Source Mix Experiment Review",
        "",
        *source_mix_review,
        "",
        "## Review Board Experiment Snapshot",
        "",
        *review_board_experiment_lines,
        "",
        "## Source Role Cap Status",
        "",
        *source_role_cap_rows,
        "",
        "## Source Role Cap-blocked Candidates",
        "",
        (
            "| title | source | source_role_class | score | reason |"
        ),
        "| --- | --- | --- | ---: | --- |",
        *cap_blocked_rows,
        "",
        "## Story Bundle Review",
        "",
        "| bundle | primary | supporting/evidence | bundle_type | suggested_action |",
        "| --- | --- | --- | --- | --- |",
        *story_bundle_rows,
        "",
        "## Syuka Similarity Summary",
        "",
        *syuka_similarity_lines,
        "",
        "## Cross-run Duplicate / Reappearing Story Review",
        "",
        "| story_fingerprint | title | status | note |",
        "| --- | --- | --- | --- |",
        *cross_run_story_rows,
        "",
        "## Storyline Fit Audit",
        "",
        (
            "| role | title | source | seed_type | storyline_fit | merge_or_reason | "
            "suggested_operator_action |"
        ),
        "| --- | --- | --- | --- | --- | --- | --- |",
        *storyline_fit_rows,
        "",
        "## So-What / Audience Interest Summary",
        "",
        *so_what_summary,
        "",
        "## Weak Audience Bridge Examples",
        "",
        "| title | source | score | classification | so_what | so_what_gap | "
        "audience_bridge_signals | quality_flags |",
        "| --- | --- | ---: | --- | --- | --- | --- | --- |",
        *weak_audience_rows,
        "",
        "## Interesting But Not Seed Queue",
        "",
        "| title | source | score | classification | so_what | so_what_gap | "
        "audience_bridge_signals | quality_flags |",
        "| --- | --- | ---: | --- | --- | --- | --- | --- |",
        *interesting_not_seed_rows,
        "",
        "## Conditional System-Issue Queue",
        "",
        "| title | source | score | classification | so_what | so_what_gap | "
        "audience_bridge_signals | quality_flags |",
        "| --- | --- | ---: | --- | --- | --- | --- | --- |",
        *conditional_system_issue_rows,
        "",
        "## Promo-Bulletin Suppression Queue",
        "",
        "| title | source | score | guard_flags | so_what | action |",
        "| --- | --- | ---: | --- | --- | --- |",
        *promo_bulletin_rows,
        "",
        "## Evidence-Only Candidate Queue",
        "",
        "| title | source | score | classification | so_what | so_what_gap | "
        "audience_bridge_signals | quality_flags |",
        "| --- | --- | ---: | --- | --- | --- | --- | --- |",
        *evidence_only_rows,
        "",
        "## Conditional Seed / Bundle-needed Queue",
        "",
        (
            "| title | source | score | classification | so_what | "
            "audience_bridge_signals | weakness_signals |"
        ),
        "| --- | --- | ---: | --- | --- | --- | --- |",
        *conditional_seed_rows,
        "",
        "## Candidate Funnel",
        "",
        f"- raw_candidates: {len(candidates)}",
        f"- recent_candidates: {_freshness_count(candidates, 'recent')}",
        f"- unknown_freshness_candidates: {_freshness_count(candidates, 'unknown')}",
        f"- stale_candidates: {_freshness_count(candidates, 'stale')}",
        f"- quality_flagged_candidates: {len(quality_flagged)}",
        f"- quality_gate_pass_candidates: {len(quality_gate_pass)}",
        f"- duplicate_grouped_candidates: {len(duplicate_grouped)}",
        f"- duplicate_primary_candidates: {len(duplicate_primary)}",
        f"- top_eligible_candidates: {len(top_eligible)}",
        f"- rendered_top_candidates: {len(top)}",
        "",
        "## Calibration Warnings",
        "",
        *(calibration_warnings or ["- none"]),
        "",
        "## Calibration Summary",
        "",
        *(calibration_summary or ["- none"]),
        "",
        "## Top Gate Reason Distribution",
        "",
        "### All Non-top Candidates",
        "",
        *(
            _reason_distribution_lines(gate_reason_distribution["all"])
            or ["- none"]
        ),
        "",
        "### Top 20 Non-top Candidates By Score",
        "",
        *(
            _reason_distribution_lines(gate_reason_distribution["top20"])
            or ["- none"]
        ),
        "",
        "## What-if Gate Simulation",
        "",
        "| scenario | top_eligible_count | projected_top_count | added_candidate_examples |",
        "| --- | ---: | ---: | --- |",
        *what_if_rows,
        "",
        "## Slideability Summary",
        "",
        *[
            f"- {level}: {count}"
            for level, count in Counter(
                str((item.get("slideability") or {}).get("visualizability", "low"))
                for item in candidates
            ).most_common()
        ],
        "",
        "## Top Candidates Detail",
        "",
        *[
            (
                f"- {item.get('title')}: seed_type={item.get('seed_type')}, "
                f"risk_flags={item.get('risk_flags', [])}, "
                f"quality_flags={item.get('quality_flags', [])}, "
                f"slideability={_slideability_label(item)}"
            )
            for item in top
        ],
        "",
        "## Source Freshness Summary",
        "",
        *[
            (
                f"- {source}: raw={raw_source_counts.get(source, 0)}, "
                f"top={source_counts.get(source, 0)}, "
                f"recent={freshness_by_source.get(source, Counter()).get('recent', 0)}, "
                f"stale={freshness_by_source.get(source, Counter()).get('stale', 0)}, "
                f"unknown={freshness_by_source.get(source, Counter()).get('unknown', 0)}, "
                f"empty_summary={empty_summary_counts.get(source, 0)}"
            )
            for source, _count in raw_source_counts.most_common()
        ],
        "",
        "## Source Survival Table",
        "",
        (
            "| source | raw | recent | unknown | stale | quality_flagged | "
            "top_eligible | top | dominant_flags | warning |"
        ),
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |",
        *source_survival_rows,
        "",
        "## Source Recommendations",
        "",
        "| source | recommendation | reason |",
        "| --- | --- | --- |",
        *source_recommendation_rows,
        "",
        "## Source Allowlist Review Queue",
        "",
        (
            "| source | recommendation | reason | dominant_flags | raw_count | "
            "top_eligible_count | top_count | suggested_manual_action |"
        ),
        "| --- | --- | --- | --- | ---: | ---: | ---: | --- |",
        *source_allowlist_review_rows,
        "",
        "## Source Quality Flags",
        "",
        *[
            (
                f"- {source}: "
                + (
                    ", ".join(
                        f"{flag}={count}"
                        for flag, count in quality_flags_by_source.get(
                            source,
                            Counter(),
                        ).most_common()
                    )
                    or "none"
                )
            )
            for source, _count in raw_source_counts.most_common()
        ],
        "",
        "## Source Skew Warnings",
        "",
        *(skew_warnings or ["- none"]),
        "",
        "## Near Duplicate Groups",
        "",
        *(near_duplicate_groups or ["- none"]),
        "",
        "## Top Candidates Source Distribution",
        "",
        *[f"- {source}: {count}" for source, count in source_counts.most_common()],
        "",
        "## Top Candidates Seed Type Distribution",
        "",
        *[f"- {seed_type}: {count}" for seed_type, count in seed_counts.most_common()],
        "",
        "## Action Distribution",
        "",
        *[f"- {action}: {count}" for action, count in action_counts.most_common()],
        "",
        "## Source Candidate Count",
        "",
        *[f"- {source}: {count}" for source, count in raw_source_counts.most_common()],
        "",
        "## Source Count After Quality Gate",
        "",
        *[f"- {source}: {count}" for source, count in after_gate_source_counts.most_common()],
        "",
        "## Top 10 Raw Score Before Gate",
        "",
        *[
            (
                f"- {item.get('title')}: {item.get('scores', {}).get('total_score', 0)} / "
                f"{item.get('recommended_action')} / flags={item.get('quality_flags', [])}"
            )
            for item in raw_top
        ],
        "",
        "## Top After Gate",
        "",
        *[
            (
                f"- {item.get('title')}: {item.get('scores', {}).get('total_score', 0)} / "
                f"{item.get('recommended_action')}"
            )
            for item in top
        ],
        "",
        "## Removed From Raw Top By Gate/Balance",
        "",
        *[
            (
                f"- {item.get('title')}: flags={item.get('quality_flags', [])}, "
                f"failure_modes={item.get('failure_modes', [])}"
            )
            for item in removed_from_top
        ],
        "",
        "## Generic Why Template Improvement Queue",
        "",
        *generic_template_queue,
        "",
        "## Near Miss Review Queue",
        "",
        *(near_miss_queue or ["- none"]),
        "",
        "## Empty Summary Count By Source",
        "",
        *[f"- {source}: {count}" for source, count in empty_summary_counts.most_common()],
        "",
        "## Top Failure Modes",
        "",
        *[f"- {mode}: {count}" for mode, count in failure_modes.most_common(10)],
        "",
        "## Generic Why Examples",
        "",
        *[
            f"- {item.get('title')}: {item.get('why_interesting')}"
            for item in generic_why_examples
        ],
        "",
        "## Generic Why / Specificity Examples",
        "",
        *(generic_specificity_examples or ["- none"]),
        "",
        "## Downranked Examples",
        "",
    ]
    if downranked_examples:
        for item in downranked_examples:
            lines.append(
                f"- {item.get('title')}: {', '.join(item.get('quality_flags', []))} "
                f"-> {item.get('recommended_action')} / {item.get('final_grade')}"
            )
    else:
        lines.append("- none")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _counter_lines(counter: Counter[str]) -> list[str]:
    return [f"- {key}: {count}" for key, count in counter.most_common()] or ["- none"]


def _source_role_cap_warnings(top_role_counts: Counter[str]) -> list[str]:
    warnings = [
        f"- source_role_cap_warning: {role} has {count} top candidates (suggested <= {cap})"
        for role, cap in DEFAULT_SOURCE_ROLE_TOP_CAPS.items()
        if (count := top_role_counts.get(role, 0)) > cap
    ]
    return warnings or ["- none"]


def _source_role_cap_status_rows(selection_details: dict[str, Any]) -> list[str]:
    caps: dict[str, int] = selection_details.get("source_role_caps") or {}
    selected: list[dict[str, Any]] = selection_details.get("selected") or []
    selected_counts = Counter(_candidate_role(item) for item in selected)
    backfill_used = str(bool(selection_details.get("cap_backfill_used"))).lower()
    lines = [f"- cap_backfill_used: {backfill_used}"]
    for role, cap in caps.items():
        lines.append(f"- {role}: selected={selected_counts.get(role, 0)} cap={cap}")
    backfilled = selection_details.get("backfilled") or []
    if backfilled:
        lines.append(
            "- cap_backfill_candidates: "
            + "; ".join(
                f"{item.get('title')} ({_candidate_role(item)})"
                for item in backfilled[:5]
            )
        )
    else:
        lines.append("- cap_backfill_candidates: none")
    return lines


def _source_role_cap_blocked_rows(selection_details: dict[str, Any]) -> list[str]:
    rows: list[str] = []
    for candidate, reason in selection_details.get("role_cap_blocked") or []:
        rows.append(
            "| "
            + " | ".join(
                [
                    _table_cell(candidate.get("title", "")),
                    _table_cell(candidate.get("source", "unknown")),
                    _candidate_role(candidate),
                    f"{_total_score(candidate):g}",
                    reason,
                ]
            )
            + " |"
        )
    return rows or ["| none | unknown | unknown | 0 | none |"]


def _source_mix_focus_line(
    label: str,
    candidates: list[dict[str, Any]],
    *,
    limit: int = 5,
) -> str:
    if not candidates:
        return f"- {label}: none"
    examples = "; ".join(
        f"{item.get('title')} ({item.get('source')}, {item.get('seed_type')})"
        for item in sorted(candidates, key=_total_score, reverse=True)[:limit]
    )
    return f"- {label}: {examples}"


def _source_mix_experiment_review(
    *,
    candidates: list[dict[str, Any]],
    top: list[dict[str, Any]],
    raw_role_counts: Counter[str],
    top_role_counts: Counter[str],
    raw_source_counts: Counter[str],
    source_counts: Counter[str],
) -> list[str]:
    official_roles = {"research_note", "policy_release"}
    public_roles = {"public_wire", "section_news"}
    academic_roles = {"academic_explainer"}
    market_roles = {"market_wire"}

    def count_roles(items: list[dict[str, Any]], roles: set[str]) -> int:
        return sum(1 for item in items if str(item.get("source_role_class")) in roles)

    research_candidates = [
        item for item in candidates if item.get("source_role_class") == "research_note"
    ]
    policy_candidates = [
        item for item in candidates if item.get("source_role_class") == "policy_release"
    ]
    academic_candidates = [
        item for item in candidates if item.get("source_role_class") == "academic_explainer"
    ]
    yonhap_candidates = [
        item
        for item in candidates
        if str(item.get("source_id") or "").startswith("yonhap_")
        and str(item.get("source_id")) not in {"yonhap_rss_candidate"}
    ]

    lines = [
        "### Source Role Distribution",
        "",
        "Raw candidates:",
        *_counter_lines(raw_role_counts),
        "",
        "Top candidates:",
        *_counter_lines(top_role_counts),
        "",
        "### Exact Source Distribution",
        "",
        "Raw candidates:",
        *_counter_lines(raw_source_counts),
        "",
        "Top candidates:",
        *_counter_lines(source_counts),
        "",
        "### Source Role Balance",
        "",
        f"- official/research raw: {count_roles(candidates, official_roles)}",
        f"- official/research top: {count_roles(top, official_roles)}",
        f"- public/section raw: {count_roles(candidates, public_roles)}",
        f"- public/section top: {count_roles(top, public_roles)}",
        f"- academic raw: {count_roles(candidates, academic_roles)}",
        f"- academic top: {count_roles(top, academic_roles)}",
        f"- market raw: {count_roles(candidates, market_roles)}",
        f"- market top: {count_roles(top, market_roles)}",
        "",
        "### Source Role Cap Warnings",
        "",
        *_source_role_cap_warnings(top_role_counts),
        "",
        "### Recommended Human Review Focus",
        "",
        _source_mix_focus_line("BOK research-note candidates", research_candidates),
        _source_mix_focus_line("Policy Briefing seed/evidence candidates", policy_candidates),
        _source_mix_focus_line("The Conversation academic explainers", academic_candidates),
        _source_mix_focus_line(
            "Yonhap economy/industry/international seeds",
            yonhap_candidates,
        ),
    ]
    return lines


def _audit_text(candidate: dict[str, Any]) -> str:
    return " ".join(
        str(candidate.get(key) or "")
        for key in ("title", "summary", "why_interesting", "seed_type")
    ).lower()


def _source_text(candidate: dict[str, Any]) -> str:
    return " ".join(
        str(candidate.get(key) or "")
        for key in ("title", "summary", "source", "source_id")
    ).lower()


def _youth_labor_merge_target(
    candidate: dict[str, Any],
    candidates: list[dict[str, Any]],
) -> str | None:
    text = _audit_text(candidate)
    if "청년" not in text or not any(
        term in text for term in ("쉬었음", "경제활동참가율", "노동시장")
    ):
        return None
    candidate_id = str(candidate.get("candidate_id"))
    for other in candidates:
        if str(other.get("candidate_id")) == candidate_id:
            continue
        other_text = _audit_text(other)
        if "청년" in other_text and any(
            term in other_text for term in ("쉬었음", "경제활동참가율", "노동시장")
        ):
            return str(
                other.get("title") or other.get("candidate_id") or "related_candidate"
            )
    return None


def _storyline_fit_classification(
    candidate: dict[str, Any],
    candidates: list[dict[str, Any]],
) -> tuple[str, str, str]:
    seed_type = str(candidate.get("seed_type") or "other")
    role = _candidate_role(candidate)
    flags = set(candidate.get("quality_flags") or [])
    risk_flags = set(candidate.get("risk_flags") or [])
    text = _audit_text(candidate)
    merge_target = _youth_labor_merge_target(candidate, candidates)
    if merge_target:
        return (
            "merge_with_other_candidate",
            f"merge_target={merge_target}",
            "bundle_before_sheet_review",
        )
    if role == "research_note":
        return (
            "standalone_seed",
            "research_note_has_structural_numbers",
            "review_as_core_seed",
        )
    if role == "policy_release":
        evidence_flags = {
            "policy_release_evidence_default",
            "policy_release_announcement_only",
            "policy_release_meeting_only",
            "policy_release_procedural_number_only",
        }
        if (
            seed_type != "policy_release_seed"
            or evidence_flags.intersection(flags)
            or _policy_status_or_meeting_release(candidate)
        ):
            return (
                "evidence_only",
                "official_release_meeting_or_evidence_default",
                "attach_to_larger_story",
            )
        return (
            "needs_external_sources",
            "official_release_seed_needs_independent_context",
            "collect_price_life_or_industry_data",
        )
    if seed_type in {"single_company_financing", "market_rate_stress"}:
        if "ipo" in text or "청약" in text or "수요예측" in text:
            return (
                "evidence_only",
                "market_schedule_or_ipo_context",
                "use_only_inside_market_structure_story",
            )
        if "유상증자" in text or "주주배정" in text or risk_flags.intersection(
            {"investment_advice_risk", "corporate_promo_risk"}
        ):
            return (
                "demote_or_reject",
                "single_company_or_investment_frame",
                "reject_as_standalone_seed",
            )
        return (
            "needs_external_sources",
            "finance_story_needs_non_investment_frame",
            "find_brand_or_market_structure_angle",
        )
    if seed_type in {
        "public_ai_governance",
        "public_ai_enforcement",
        "workplace_ai_transition",
        "healthcare_operations_ai",
        "platform_labor_market",
        "industrial_labor_conflict",
    }:
        return (
            "needs_external_sources",
            "public_wire_story_has_concrete_broadcast_hook",
            "collect_second_source_and_numbers",
        )
    if role == "academic_explainer":
        return (
            "standalone_seed",
            "academic_explainer_has_mechanism",
            "review_as_explainer_seed",
        )
    if seed_type == "life_change" and risk_flags.intersection({"corporate_promo_risk"}):
        return (
            "needs_external_sources",
            "lifestyle_hook_but_source_is_promotional",
            "bundle_with_climate_labor_or_power_data",
        )
    if _has_generic_why(candidate):
        return (
            "demote_or_reject",
            "generic_why_without_specific_template",
            "review_template_queue",
        )
    return (
        "needs_external_sources",
        "story_fit_uncertain",
        "manual_editorial_review",
    )


def _storyline_fit_audit_rows(
    candidates: list[dict[str, Any]],
    top: list[dict[str, Any]],
    *,
    near_miss_limit: int = 10,
) -> list[str]:
    top_ids = {str(item.get("candidate_id")) for item in top}
    near_misses = sorted(
        [item for item in candidates if str(item.get("candidate_id")) not in top_ids],
        key=_total_score,
        reverse=True,
    )[:near_miss_limit]
    rows: list[str] = []
    for role, item in [
        *[("top", candidate) for candidate in top],
        *[("near_miss", candidate) for candidate in near_misses],
    ]:
        fit, reason, action = _storyline_fit_classification(item, candidates)
        rows.append(
            "| "
            + " | ".join(
                [
                    role,
                    _table_cell(item.get("title", "")),
                    _table_cell(item.get("source", "unknown")),
                    _table_cell(item.get("seed_type", "unknown")),
                    fit,
                    _table_cell(reason),
                    action,
                ]
            )
            + " |"
        )
    return rows or ["| none | none | unknown | unknown | demote_or_reject | none | none |"]


def _candidate_so_what(candidate: dict[str, Any]) -> dict[str, Any]:
    so_what = candidate.get("so_what")
    if isinstance(so_what, dict) and so_what.get("so_what_label"):
        return so_what
    return {
        key: value
        for key, value in analyze_so_what(candidate).items()
        if key != "quality_flags"
    }


def _so_what_summary_lines(
    candidates: list[dict[str, Any]],
    top: list[dict[str, Any]],
) -> list[str]:
    all_counts = Counter(
        str(_candidate_so_what(item).get("so_what_label") or "unknown")
        for item in candidates
    )
    top_counts = Counter(
        str(_candidate_so_what(item).get("so_what_label") or "unknown") for item in top
    )
    return [
        "- all_candidates: "
        + (", ".join(f"{key}={value}" for key, value in all_counts.most_common()) or "none"),
        "- top_candidates: "
        + (", ".join(f"{key}={value}" for key, value in top_counts.most_common()) or "none"),
    ]


def _promo_bulletin_downrank_rows(candidates: list[dict[str, Any]]) -> list[str]:
    promo_flags = {
        "contest_or_campaign_bulletin",
        "event_or_demonstration_only",
        "meeting_or_coordination_only",
        "product_or_certification_promo",
        "narrow_market_track_record",
    }
    rows: list[str] = []
    for item in sorted(candidates, key=_total_score, reverse=True):
        flags = [flag for flag in item.get("quality_flags", []) if flag in promo_flags]
        if not flags:
            continue
        so_what = _candidate_so_what(item)
        rows.append(
            "| "
            + " | ".join(
                [
                    _table_cell(item.get("title", "")),
                    _table_cell(item.get("source", "unknown")),
                    f"{_total_score(item):g}",
                    _table_cell(", ".join(flags)),
                    _table_cell(str(so_what.get("so_what_label") or "unknown")),
                    _table_cell(item.get("recommended_action", "")),
                ]
            )
            + " |"
        )
        if len(rows) >= 10:
            break
    return rows or ["| none | unknown | 0 | none | unknown | none |"]


def _conditional_seed_queue_rows(candidates: list[dict[str, Any]]) -> list[str]:
    rows: list[str] = []
    for item in sorted(candidates, key=_total_score, reverse=True):
        classification = str(
            item.get("seed_quality_classification")
            or _candidate_so_what(item).get("seed_quality_classification")
            or ""
        )
        if classification not in {"conditional_seed", "bundle_needed", "evidence_only"}:
            continue
        so_what = _candidate_so_what(item)
        rows.append(
            "| "
            + " | ".join(
                [
                    _table_cell(item.get("title", "")),
                    _table_cell(item.get("source", "unknown")),
                    f"{_total_score(item):g}",
                    classification,
                    _table_cell(str(so_what.get("so_what_label") or "")),
                    _table_cell(_format_list(so_what.get("audience_bridge_signals") or [])),
                    _table_cell(_format_list(so_what.get("weakness_signals") or [])),
                ]
            )
            + " |"
        )
        if len(rows) >= 15:
            break
    return rows or ["| none | unknown | 0 | unclear | weak | none | none |"]


def _seed_quality_queue_rows(
    candidates: list[dict[str, Any]],
    *,
    classifications: set[str] | None = None,
    required_flags: set[str] | None = None,
    required_so_what_labels: set[str] | None = None,
    limit: int = 10,
) -> list[str]:
    rows: list[str] = []
    for item in sorted(candidates, key=_total_score, reverse=True):
        so_what = _candidate_so_what(item)
        classification = str(
            item.get("seed_quality_classification")
            or so_what.get("seed_quality_classification")
            or ""
        )
        flags = set(str(flag) for flag in item.get("quality_flags", []))
        if classifications and classification not in classifications:
            continue
        if required_flags and not flags.intersection(required_flags):
            continue
        if (
            required_so_what_labels
            and str(so_what.get("so_what_label")) not in required_so_what_labels
        ):
            continue
        rows.append(
            "| "
            + " | ".join(
                [
                    _table_cell(item.get("title", "")),
                    _table_cell(item.get("source", "unknown")),
                    f"{_total_score(item):g}",
                    _table_cell(classification or "unknown"),
                    _table_cell(str(so_what.get("so_what_label") or "unknown")),
                    _table_cell(str(so_what.get("so_what_gap") or "")),
                    _table_cell(_format_list(so_what.get("audience_bridge_signals") or [])),
                    _table_cell(_format_list(item.get("quality_flags") or [])),
                ]
            )
            + " |"
        )
        if len(rows) >= limit:
            break
    return rows or ["| none | unknown | 0 | none | unknown | none | none | none |"]


def _story_bundle_hash(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:10]


def _normalized_for_fingerprint(value: object) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip().lower())


def _domain(value: object) -> str:
    url = str(value or "").strip()
    if not url:
        return ""
    return urlparse(url).netloc.lower().removeprefix("www.")


def _story_fingerprint(rule: dict[str, str], primary: dict[str, Any] | None) -> str:
    key = str(rule.get("key") or "").strip()
    if key and not key.startswith("candidate_"):
        return key
    if not primary:
        return key or "story_" + _story_bundle_hash(str(rule.get("title") or "unknown"))
    source_role = _normalized_for_fingerprint(primary.get("source_role_class"))
    seed_type = _normalized_for_fingerprint(primary.get("seed_type"))
    title = _normalized_for_fingerprint(rule.get("title") or primary.get("title"))
    domain = _domain(primary.get("source_url_canonical") or primary.get("seed_url"))
    canonical = canonicalize_url(str(primary.get("seed_url") or ""))
    raw = "|".join([title, source_role, seed_type, domain, canonical])
    return "story_" + _story_bundle_hash(raw)


def _review_history_tag(note: str) -> str:
    return str(infer_review_feedback(note).get("tag") or "unlabeled")


def _history_row_status(row: dict[str, Any]) -> str:
    notes = [
        str(row.get(column) or "").strip()
        for column in REVIEWER_COLUMNS
        if str(row.get(column) or "").strip()
    ]
    if not notes:
        return "seen_before"
    tags = {_review_history_tag(note) for note in notes}
    if "reject" in tags:
        return "rejected_before"
    if "seed" in tags:
        return "promoted_before"
    return "reviewed_before"


def _history_key_from_row(row: dict[str, Any]) -> str:
    fingerprint = str(row.get("story_fingerprint") or "").strip()
    if fingerprint:
        return fingerprint
    review_id = str(row.get("ID") or row.get("id") or "").strip()
    if ":" in review_id:
        return review_id.rsplit(":", 1)[1]
    return review_id


def _load_review_history_index(path: Path) -> dict[str, list[dict[str, Any]]]:
    if not path.exists():
        return {}
    index: dict[str, list[dict[str, Any]]] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        for row in payload.get("rows", []):
            if not isinstance(row, dict):
                continue
            row = dict(row)
            row["history_status"] = _history_row_status(row)
            key = _history_key_from_row(row)
            if key:
                index.setdefault(key, []).append(row)
    return index


def _rank_history_status(status: str) -> int:
    return {
        "rejected_before": 4,
        "promoted_before": 3,
        "reviewed_before": 2,
        "seen_before": 1,
        "new": 0,
    }.get(status, 0)


def _record_history_status(
    record: dict[str, Any],
    history_index: dict[str, list[dict[str, Any]]],
) -> str:
    keys = [
        str(record.get("story_fingerprint") or ""),
        str(record.get("story_bundle_id") or ""),
    ]
    statuses = [
        str(item.get("history_status") or "seen_before")
        for key in keys
        for item in history_index.get(key, [])
        if key
    ]
    if not statuses:
        return "new"
    return max(statuses, key=_rank_history_status)


def _policy_status_or_meeting_release(candidate: dict[str, Any]) -> bool:
    if _candidate_role(candidate) != "policy_release":
        return False
    flags = set(candidate.get("quality_flags") or [])
    text = _source_text(candidate)
    if flags.intersection(
        {
            "policy_release_evidence_default",
            "policy_release_announcement_only",
            "policy_release_meeting_only",
            "policy_release_procedural_number_only",
        }
    ):
        return True
    return any(term in text for term in POLICY_STATUS_EVIDENCE_TERMS)


def _energy_living_cost_bundle_signal(text: str) -> bool:
    lowered = text.lower()
    has_energy_price = any(
        term in lowered
        for term in (
            "energy bills",
            "energy bill",
            "energy price cap",
            "electricity prices",
            "electricity bills",
            "gas prices",
            "ofgem",
            "전기요금",
            "전력요금",
            "에너지 요금",
            "가스요금",
        )
    )
    has_living_cost_or_shock = any(
        term in lowered
        for term in (
            "iran war",
            "middle east",
            "household",
            "cost of living",
            "생활비",
            "가계",
            "전쟁",
            "중동",
            "요금",
        )
    )
    return has_energy_price and has_living_cost_or_shock


def _story_bundle_rule(candidate: dict[str, Any]) -> dict[str, str]:
    text = _source_text(candidate)
    seed_type = str(candidate.get("seed_type") or "other")
    if "청년" in text and any(
        term in text for term in ("쉬었음", "경제활동참가율", "노동시장")
    ):
        return {
            "key": "youth_labor_exit",
            "title": "청년 노동시장 이탈 / 쉬었음 / 경제활동참가율",
            "type": "merged_seed",
            "why": "BOK 청년 노동시장 후보들이 같은 큰 질문을 공유함",
            "action": "review_primary_and_bundle_supporting",
        }
    has_platform_fee_signal = any(term in text for term in PLATFORM_FEE_STRONG_TERMS)
    if has_platform_fee_signal:
        return {
            "key": "platform_fee_allocation",
            "title": "플랫폼 무료배달 / 수수료 비용 배분",
            "type": "needs_external_sources",
            "why": "무료배달, 수수료, 업주 부담이 같은 플랫폼 비용 배분 이야기로 묶임",
            "action": "collect_second_source_and_numbers",
        }
    if seed_type in PUBLIC_AI_SEED_TYPES:
        return {
            "key": "public_ai_adoption",
            "title": "공공/현장 AI 도입과 책임",
            "type": "needs_external_sources",
            "why": "공공 AI 활용, 치안, 행정 보고서, 직무 전환 후보를 함께 검토",
            "action": "split_or_bundle_after_human_review",
        }
    if _energy_living_cost_bundle_signal(text):
        return {
            "key": "energy_price_living_cost",
            "title": "에너지 가격 충격 / 전기요금 / 생활비",
            "type": "merged_seed",
            "why": "전쟁, 가스·전력 가격, 규제기관 전망이 생활비로 번지는 같은 이야기",
            "action": "review_primary_and_bundle_supporting",
        }
    if _policy_status_or_meeting_release(candidate):
        if any(term in text for term in ("고유가", "유가", "피해지원금", "지원금")):
            key = "policy_oil_support_evidence"
            title = "고유가 지원금 / 에너지 가격 충격 evidence"
        elif any(term in text for term in ("중동", "공관", "원유", "수급선")):
            key = "policy_middle_east_evidence"
            title = "중동 리스크 / 대체 수급선 official evidence"
        else:
            key = "policy_release_evidence_" + _story_bundle_hash(
                str(candidate.get("candidate_id") or candidate.get("title") or "")
            )
            title = "정책브리핑 evidence-only 후보"
        return {
            "key": key,
            "title": title,
            "type": "evidence_cluster",
            "why": "회의/현황/절차성 보도자료는 단독 seed보다 큰 이야기의 근거로 검토",
            "action": "attach_to_larger_story",
        }
    fit, reason, action = _storyline_fit_classification(candidate, [candidate])
    if fit == "standalone_seed":
        bundle_type = "standalone_seed"
    elif fit == "evidence_only":
        bundle_type = "evidence_cluster"
    elif fit == "merge_with_other_candidate":
        bundle_type = "merged_seed"
    else:
        bundle_type = "needs_external_sources"
    candidate_id = str(candidate.get("candidate_id") or _story_bundle_hash(text))
    return {
        "key": "candidate_" + candidate_id,
        "title": str(candidate.get("title") or candidate_id),
        "type": bundle_type,
        "why": reason,
        "action": action,
    }


def _bundle_candidate_pool(
    candidates: list[dict[str, Any]],
    top: list[dict[str, Any]],
    *,
    near_miss_limit: int,
) -> list[dict[str, Any]]:
    top_ids = {str(item.get("candidate_id")) for item in top}
    near_misses = sorted(
        [
            item
            for item in candidates
            if str(item.get("candidate_id")) not in top_ids
            and item.get("recommended_action", "keep_for_later") in TOP_ACTIONS
        ],
        key=_total_score,
        reverse=True,
    )[:near_miss_limit]
    seen: set[str] = set()
    pool: list[dict[str, Any]] = []
    for item in [*top, *near_misses]:
        candidate_id = str(item.get("candidate_id"))
        if candidate_id in seen:
            continue
        seen.add(candidate_id)
        pool.append(item)
    return pool


def _bundle_primary(
    items: list[dict[str, Any]],
    *,
    bundle_type: str,
) -> dict[str, Any] | None:
    if bundle_type == "evidence_cluster":
        return None
    return sorted(
        items,
        key=lambda item: (
            _total_score(item),
            item.get("scores", {}).get("broadcast_potential_proxy", 0),
        ),
        reverse=True,
    )[0]


def _story_bundle_records(
    candidates: list[dict[str, Any]],
    top: list[dict[str, Any]],
    *,
    near_miss_limit: int = 10,
) -> list[dict[str, Any]]:
    pool = _bundle_candidate_pool(candidates, top, near_miss_limit=near_miss_limit)
    grouped: dict[str, list[dict[str, Any]]] = {}
    metadata: dict[str, dict[str, str]] = {}
    for candidate in pool:
        rule = _story_bundle_rule(candidate)
        key = rule["key"]
        grouped.setdefault(key, []).append(candidate)
        metadata.setdefault(key, rule)
    records: list[dict[str, Any]] = []
    for key, items in grouped.items():
        rule = metadata[key]
        bundle_type = rule["type"]
        if len(items) > 1 and bundle_type == "standalone_seed":
            bundle_type = "merged_seed"
        primary = _bundle_primary(items, bundle_type=bundle_type)
        primary_id = str(primary.get("candidate_id")) if primary else ""
        primary_title = str(primary.get("title")) if primary else ""
        evidence_ids: list[str] = []
        supporting_ids: list[str] = []
        evidence_titles: list[str] = []
        supporting_titles: list[str] = []
        for item in sorted(items, key=_total_score, reverse=True):
            item_id = str(item.get("candidate_id") or "")
            if item_id == primary_id:
                continue
            fit, _reason, _action = _storyline_fit_classification(item, candidates)
            if bundle_type == "evidence_cluster" or fit == "evidence_only":
                target_ids = evidence_ids
                target_titles = evidence_titles
            else:
                target_ids = supporting_ids
                target_titles = supporting_titles
            target_ids.append(item_id)
            target_titles.append(str(item.get("title") or item_id))
        records.append(
            {
                "story_bundle_id": "story_bundle_" + _story_bundle_hash(key),
                "story_fingerprint": _story_fingerprint(rule, primary),
                "bundle_title": rule["title"],
                "primary_candidate_id": primary_id,
                "primary_title": primary_title,
                "supporting_candidate_ids": supporting_ids,
                "supporting_titles": supporting_titles,
                "evidence_candidate_ids": evidence_ids,
                "evidence_titles": evidence_titles,
                "bundle_type": bundle_type,
                "why_bundle": rule["why"],
                "suggested_operator_action": rule["action"],
                "candidate_count": len(items),
            }
        )
    records.sort(
        key=lambda item: (
            {"merged_seed": 0, "standalone_seed": 1, "needs_external_sources": 2}.get(
                str(item["bundle_type"]),
                3,
            ),
            -int(item["candidate_count"]),
            str(item["bundle_title"]),
        )
    )
    return records


def _story_bundle_review_rows(records: list[dict[str, Any]]) -> list[str]:
    rows: list[str] = []
    for record in records:
        primary = record.get("primary_title") or "none"
        supporting = [
            *[f"supporting: {title}" for title in record.get("supporting_titles", [])],
            *[f"evidence: {title}" for title in record.get("evidence_titles", [])],
        ]
        rows.append(
            "| "
            + " | ".join(
                [
                    _table_cell(
                        f"{record['story_bundle_id']} — {record['bundle_title']}"
                    ),
                    _table_cell(primary),
                    _table_cell("; ".join(supporting) or "none"),
                    str(record["bundle_type"]),
                    str(record["suggested_operator_action"]),
                ]
            )
            + " |"
        )
    return rows or ["| none | none | none | needs_external_sources | none |"]


def _cross_run_story_review_rows(
    records: list[dict[str, Any]],
    history_index: dict[str, list[dict[str, Any]]],
) -> list[str]:
    rows: list[str] = []
    for record in records:
        status = _record_history_status(record, history_index)
        if status == "new":
            continue
        note = _history_sentence(status) or "previously seen"
        rows.append(
            "| "
            + " | ".join(
                [
                    _table_cell(record.get("story_fingerprint", "")),
                    _table_cell(record.get("bundle_title", "")),
                    status,
                    _table_cell(note),
                ]
            )
            + " |"
        )
    return rows or ["| none | none | new | no cross-run matches |"]


def _candidate_by_id(candidates: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {
        str(candidate.get("candidate_id")): candidate
        for candidate in candidates
        if candidate.get("candidate_id")
    }


def _record_representative_candidate(
    record: dict[str, Any],
    candidate_by_id: dict[str, dict[str, Any]],
) -> dict[str, Any] | None:
    for key in [
        "primary_candidate_id",
        "supporting_candidate_ids",
        "evidence_candidate_ids",
    ]:
        value = record.get(key)
        if isinstance(value, list):
            for item in value:
                candidate = candidate_by_id.get(str(item))
                if candidate:
                    return candidate
        else:
            candidate = candidate_by_id.get(str(value or ""))
            if candidate:
                return candidate
    return None


def _dedupe_terms(terms: list[str]) -> list[str]:
    output: list[str] = []
    for term in terms:
        normalized = str(term or "").strip()
        if normalized and normalized not in output:
            output.append(normalized)
    return output


def _bridge_query_term_groups(
    candidate: dict[str, Any],
    record: dict[str, Any],
) -> dict[str, list[str]]:
    text = _board_text(record, candidate)
    core_terms: list[str] = []
    context_terms: list[str] = []
    if "청년" in text and any(term in text for term in ("쉬었음", "경제활동참가율", "노동시장")):
        core_terms.extend(["쉬었음", "비경제활동", "경제활동참가율", "청년 노동시장"])
        context_terms.extend(["근로소득", "청년"])
    elif (
        any(term in text for term in ("열사병", "불볕더위", "산업현장", "작업중지권"))
        and "폭염" in text
    ):
        core_terms.extend(["폭염", "열사병", "산업현장", "작업중지권", "노동안전"])
        context_terms.extend(["휴식", "냉방", "산재", "기업 책임"])
    elif any(term in text for term in ("반바지", "쿨비즈", "회사 복장", "여름 근무")):
        core_terms.extend(["반바지", "폭염", "쿨비즈", "회사 복장", "여름 근무"])
        context_terms.extend(["회사", "복장", "전력", "냉방"])
    elif any(term in text for term in ("선불", "충전금", "스타벅스", "환불")):
        core_terms.extend(["선불충전금", "예치금", "충전금", "환불", "머지포인트"])
        context_terms.extend(["스타벅스", "규제 사각지대", "소비자 자금"])
    elif _has_tokenization_bridge_signal(text):
        core_terms.extend(["자산 토큰화", "RWA", "STO", "조각투자"])
        context_terms.extend(["CBDC", "디지털 화폐", "토큰증권"])
    elif any(term in text for term in ("공공 ai", "ai 도입", "ai 드론", "ai 노사")):
        core_terms.extend(["공공 AI", "AI 도입", "AI 행정", "AI 노사"])
        context_terms.extend(["AI 책임", "보고서", "드론", "직무 전환"])
    else:
        title_terms = re.findall(r"[가-힣A-Za-z0-9]{2,}", str(candidate.get("title") or ""))
        core_terms.extend(title_terms[:3])
        context_terms.extend(title_terms[3:6])
    core_terms = _dedupe_terms(core_terms)
    context_terms = [term for term in _dedupe_terms(context_terms) if term not in core_terms]
    return {
        "core_terms": core_terms,
        "context_terms": context_terms,
        "query_terms": _dedupe_terms([*core_terms, *context_terms]),
    }


def _bridge_query_terms(candidate: dict[str, Any], record: dict[str, Any]) -> list[str]:
    return _bridge_query_term_groups(candidate, record)["query_terms"]


def _has_tokenization_bridge_signal(text: str) -> bool:
    return (
        "토큰화" in text
        or "tokenization" in text
        or bool(re.search(r"\brwa\b", text, flags=re.IGNORECASE))
    )


def _bridge_priority(candidate: dict[str, Any], record: dict[str, Any], trigger: str) -> str:
    if trigger.startswith("review_modifier:") or trigger == "already_used_live":
        return "high"
    if trigger == "board_reappearance":
        return "high"
    text = _board_text(record, candidate)
    if any(term in text for term in ("쉬었음", "경제활동참가율", "반바지", "폭염")):
        return "high"
    so_what = _candidate_so_what(candidate)
    if so_what.get("so_what_label") == "strong":
        return "high"
    if so_what.get("so_what_label") == "conditional":
        return "medium"
    return "low"


def _history_rows_for_record(
    record: dict[str, Any],
    history_index: dict[str, list[dict[str, Any]]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for key in [
        str(record.get("story_fingerprint") or ""),
        str(record.get("story_bundle_id") or ""),
    ]:
        if key:
            rows.extend(history_index.get(key, []))
    return rows


def _short_review_excerpt(value: str, *, limit: int = 120) -> str:
    normalized = re.sub(r"\s+", " ", value.strip())
    if len(normalized) <= limit:
        return normalized
    return normalized[: limit - 1].rstrip() + "..."


def _bridge_review_context(rows: list[dict[str, Any]]) -> dict[str, Any]:
    modifiers: list[str] = []
    excerpt = ""
    for row in rows:
        reviewer_payloads = row.get("reviewers")
        if isinstance(reviewer_payloads, dict):
            notes = [
                str(payload.get("raw_note") or payload.get("note") or "").strip()
                for payload in reviewer_payloads.values()
                if isinstance(payload, dict)
            ]
        else:
            notes = [str(row.get(reviewer) or "").strip() for reviewer in REVIEWER_COLUMNS]
        for note in notes:
            if note:
                inferred = infer_review_feedback(note)
                modifiers.extend(str(item) for item in inferred.get("modifiers", []))
                if not excerpt:
                    excerpt = _short_review_excerpt(note)
    return {
        "modifiers": list(dict.fromkeys(modifiers)),
        "excerpt": excerpt,
    }


def _bridge_trigger(
    *,
    candidate: dict[str, Any],
    record: dict[str, Any],
    review_context: dict[str, Any],
    history_rows: list[dict[str, Any]],
) -> str:
    modifiers = set(review_context.get("modifiers") or [])
    if "already_used_live" in modifiers:
        return "review_modifier:already_used_live"
    if "past_topic_overlap" in modifiers:
        return "review_modifier:past_topic_overlap"
    if history_rows:
        return "board_reappearance"
    text = _board_text(record, candidate)
    if any(term in text for term in ("쉬었음", "경제활동참가율", "반바지", "폭염")):
        return "heuristic"
    return "heuristic"


def _bridge_expected_match_type(
    *,
    text: str,
    trigger: str,
    review_excerpt: str,
) -> str:
    if trigger == "review_modifier:already_used_live" or any(
        term in review_excerpt.lower() for term in ("라이브", "pptx", "대본", "transcript")
    ):
        return "transcript"
    if any(term in text for term in ("쉬었음", "반바지", "폭염")):
        return "title"
    return "analysis"


def _syuka_bridge_query_records(
    records: list[dict[str, Any]],
    candidates: list[dict[str, Any]],
    history_index: dict[str, list[dict[str, Any]]] | None = None,
    review_rows_by_key: dict[str, list[dict[str, Any]]] | None = None,
) -> list[dict[str, Any]]:
    candidate_by_id = _candidate_by_id(candidates)
    history_index = history_index or {}
    review_rows_by_key = review_rows_by_key or {}
    output: list[dict[str, Any]] = []
    for record in records:
        candidate = _record_representative_candidate(record, candidate_by_id)
        if not candidate:
            continue
        text = _board_text(record, candidate)
        history_rows = _history_rows_for_record(record, history_index)
        for key in _record_exclusion_keys(record):
            history_rows.extend(review_rows_by_key.get(key, []))
        review_context = _bridge_review_context(history_rows)
        trigger = _bridge_trigger(
            candidate=candidate,
            record=record,
            review_context=review_context,
            history_rows=history_rows,
        )
        review_excerpt = str(review_context.get("excerpt") or "")
        term_groups = _bridge_query_term_groups(candidate, record)
        output.append(
            {
                "story_fingerprint": str(record.get("story_fingerprint") or ""),
                "title": str(record.get("bundle_title") or candidate.get("title") or ""),
                "query_terms": term_groups["query_terms"],
                "core_terms": term_groups["core_terms"],
                "context_terms": term_groups["context_terms"],
                "negative_terms": ["주가", "매수", "매도"]
                if "investment_advice_risk" in candidate.get("risk_flags", [])
                else [],
                "why_check_past_video": (
                    "review or heuristics suggest possible past-topic overlap"
                    if any(term in text for term in ("쉬었음", "경제활동참가율", "반바지", "폭염"))
                    else "compare with past videos before promoting repeated themes"
                ),
                "expected_match_type": _bridge_expected_match_type(
                    text=text,
                    trigger=trigger,
                    review_excerpt=review_excerpt,
                ),
                "priority": _bridge_priority(candidate, record, trigger),
                "trigger": trigger,
                "source_review_note_excerpt": review_excerpt,
            }
        )
    return output


def _load_review_feedback_rows(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    return [row for row in payload.get("rows", []) if isinstance(row, dict)]


def _review_feedback_rows_by_key(rows: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    output: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        keys = {
            str(row.get("id") or "").strip(),
            str(row.get("story_fingerprint") or "").strip(),
        }
        review_id = str(row.get("id") or "").strip()
        if ":" in review_id:
            keys.add(review_id.rsplit(":", 1)[-1])
        for key in keys:
            if key:
                output.setdefault(key, []).append(row)
    return output


def write_syuka_bridge_query_reports(
    *,
    run_date: str,
    candidates: list[dict[str, Any]],
    top: list[dict[str, Any]],
    output_dir: Path = paths.REPORTS_DIR,
    review_history_path: Path = paths.JIBI_REVIEW_BOARD_HISTORY_JSONL,
    review_feedback_path: Path | None = None,
) -> tuple[Path, Path]:
    records = _story_bundle_records(candidates, top)
    history_index = _load_review_history_index(review_history_path)
    feedback_path = review_feedback_path or output_dir / f"jibi_review_feedback_{run_date}.json"
    review_rows_by_key = _review_feedback_rows_by_key(
        _load_review_feedback_rows(feedback_path)
    )
    queries = _syuka_bridge_query_records(
        records[:DEFAULT_REVIEW_BOARD_LIMIT],
        candidates,
        history_index=history_index,
        review_rows_by_key=review_rows_by_key,
    )
    md_path = output_dir / f"jibi_syuka_bridge_queries_{run_date}.md"
    json_path = output_dir / f"jibi_syuka_bridge_queries_{run_date}.json"
    md_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        f"# Jibi Syuka Bridge Query Contract — {run_date}",
        "",
        "Report-only query terms for later Windows Codex / syuka-ops past-video checks.",
        "No syuka-ops DB was queried by luddite.",
        "",
        "## Syuka Bridge Handoff Notes",
        "",
        "- Send the JSON package to Windows Codex / syuka-ops for read-only past-video checks.",
        "- Expected downstream labels: duplicate, adjacent, safe_new_angle, needs_human_check.",
        "- Triggers from reviewer modifiers are high priority; "
        "luddite still does not inspect the DB.",
        "",
        "## Query Records",
        "",
        "| priority | trigger | title | core_terms | context_terms | expected_match_type | "
        "why_check_past_video | review_excerpt |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for item in queries:
        lines.append(
            "| "
            + " | ".join(
                [
                    item["priority"],
                    _table_cell(item["trigger"]),
                    _table_cell(item["title"]),
                    _table_cell(", ".join(item.get("core_terms", []))),
                    _table_cell(", ".join(item.get("context_terms", []))),
                    item["expected_match_type"],
                    _table_cell(item["why_check_past_video"]),
                    _table_cell(item.get("source_review_note_excerpt", "")),
                ]
            )
            + " |"
        )
    if not queries:
        lines.append("| low | heuristic | none | none | none | analysis | no board rows | none |")
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    json_path.write_text(
        json.dumps({"run_date": run_date, "queries": queries}, ensure_ascii=False, indent=2)
        + "\n",
        encoding="utf-8",
    )
    return md_path, json_path


def _review_board_experiment_snapshot(
    records: list[dict[str, Any]],
    candidates: list[dict[str, Any]],
    history_index: dict[str, list[dict[str, Any]]],
) -> list[str]:
    candidate_by_id = _candidate_by_id(candidates)
    source_counts: Counter[str] = Counter()
    sublink_counts: Counter[str] = Counter()
    score_buckets: Counter[str] = Counter()
    reappearance_counts: Counter[str] = Counter()
    for record in records:
        representative = _record_representative_candidate(record, candidate_by_id)
        source_counts[str((representative or {}).get("source") or "unknown")] += 1
        sublink_count = min(
            3,
            len(record.get("supporting_candidate_ids", []))
            + len(record.get("evidence_candidate_ids", [])),
        )
        sublink_counts[str(sublink_count)] += 1
        score = _total_score(representative or {})
        if score >= 70:
            score_buckets["70+"] += 1
        elif score >= 50:
            score_buckets["50-69"] += 1
        elif score > 0:
            score_buckets["1-49"] += 1
        else:
            score_buckets["unknown"] += 1
        reappearance_counts[_record_history_status(record, history_index)] += 1
    lines = [
        f"- board_row_count: {len(records)}",
        "- source_mix: "
        + (
            ", ".join(f"{source}={count}" for source, count in source_counts.most_common())
            or "none"
        ),
        "- story_reappearance_status: "
        + (
            ", ".join(
                f"{status}={count}" for status, count in reappearance_counts.most_common()
            )
            or "none"
        ),
        "- sublink_count_distribution: "
        + (
            ", ".join(
                f"{count}_links={value}"
                for count, value in sorted(sublink_counts.items(), key=lambda item: item[0])
            )
            or "none"
        ),
        "- score_distribution: "
        + (
            ", ".join(f"{bucket}={count}" for bucket, count in score_buckets.items())
            or "none"
        ),
    ]
    if records and source_counts:
        source, count = source_counts.most_common(1)[0]
        if len(records) >= 5 and count / len(records) >= 0.6:
            lines.append(
                f"- source_mix_warning: {source} is {count}/{len(records)} rows; "
                "review source-role balance before enabling more of the same source"
            )
        else:
            lines.append("- source_mix_warning: none")
    return lines


def _freshness_count(candidates: list[dict[str, Any]], status: str) -> int:
    return sum(1 for item in candidates if str(item.get("freshness_status") or "unknown") == status)


def _format_list(values: list[Any] | tuple[Any, ...] | set[Any]) -> str:
    cleaned = [str(value) for value in values if str(value).strip()]
    return ", ".join(cleaned) if cleaned else "none"


def _table_cell(value: object) -> str:
    return str(value).replace("|", "/")


def _source_warning_codes(
    *,
    raw_source_counts: Counter[str],
    source_counts: Counter[str],
    top_eligible_source_counts: Counter[str],
    freshness_by_source: dict[str, Counter[str]],
    empty_summary_counts: Counter[str],
) -> dict[str, list[str]]:
    total_top = sum(source_counts.values())
    warnings: dict[str, list[str]] = {}
    for source, raw_count in raw_source_counts.items():
        source_warnings: list[str] = []
        freshness = freshness_by_source.get(source, Counter())
        stale = freshness.get("stale", 0)
        unknown = freshness.get("unknown", 0)
        if raw_count > 0 and stale == raw_count:
            source_warnings.append("source_all_stale")
        if raw_count >= 5 and empty_summary_counts.get(source, 0) / raw_count >= 0.5:
            source_warnings.append("source_many_empty_summary")
        if raw_count > 0 and top_eligible_source_counts.get(source, 0) == 0:
            source_warnings.append("source_zero_survivors")
        if raw_count >= 5 and unknown / raw_count >= 0.5:
            source_warnings.append("source_unknown_freshness_high")
        if total_top >= 3 and source_counts.get(source, 0) / total_top >= 0.6:
            source_warnings.append("source_top_skew")
        warnings[source] = source_warnings
    return warnings


def _source_survival_table(
    *,
    raw_source_counts: Counter[str],
    source_counts: Counter[str],
    top_eligible_source_counts: Counter[str],
    freshness_by_source: dict[str, Counter[str]],
    quality_flagged_source_counts: Counter[str],
    quality_flags_by_source: dict[str, Counter[str]],
    empty_summary_counts: Counter[str],
    source_warning_codes: dict[str, list[str]],
) -> list[str]:
    rows: list[str] = []
    for source, raw_count in raw_source_counts.most_common():
        freshness = freshness_by_source.get(source, Counter())
        dominant_flags = ", ".join(
            f"{flag}={count}"
            for flag, count in quality_flags_by_source.get(source, Counter()).most_common(3)
        ) or "none"
        warnings = ", ".join(source_warning_codes.get(source, [])) or "ok"
        rows.append(
            "| "
            + " | ".join(
                [
                    _table_cell(source),
                    str(raw_count),
                    str(freshness.get("recent", 0)),
                    str(freshness.get("unknown", 0)),
                    str(freshness.get("stale", 0)),
                    str(quality_flagged_source_counts.get(source, 0)),
                    str(top_eligible_source_counts.get(source, 0)),
                    str(source_counts.get(source, 0)),
                    _table_cell(dominant_flags),
                    _table_cell(warnings),
                ]
            )
            + " |"
        )
    return rows or ["| none | 0 | 0 | 0 | 0 | 0 | 0 | 0 | none | ok |"]


def _calibration_warnings(
    candidates: list[dict[str, Any]],
    top: list[dict[str, Any]],
) -> list[str]:
    warnings: list[str] = []
    if len(candidates) >= 30 and len(top) < 5:
        warnings.append(
            "- top_count_too_low: "
            f"raw_candidates={len(candidates)}, rendered_top_candidates={len(top)} (<5)"
        )
    return warnings


def _reason_distribution_lines(counter: Counter[str]) -> list[str]:
    return [f"- {reason}: {count}" for reason, count in counter.most_common()]


def _top_gate_reason_distribution(
    candidates: list[dict[str, Any]],
    top_ids: set[str],
    top: list[dict[str, Any]],
    *,
    limit: int,
    max_per_source: int,
    min_score: float,
) -> dict[str, Counter[str]]:
    top_source_counts = Counter(str(item.get("source") or "unknown") for item in top)
    non_top = [
        item for item in candidates if str(item.get("candidate_id")) not in top_ids
    ]
    ranked_non_top = sorted(non_top, key=_total_score, reverse=True)

    def count_reasons(items: list[dict[str, Any]]) -> Counter[str]:
        counter: Counter[str] = Counter()
        for item in items:
            counter.update(
                _top_exclusion_reasons(
                    item,
                    top_ids,
                    top_source_counts,
                    rendered_top_count=len(top),
                    limit=limit,
                    max_per_source=max_per_source,
                    min_score=min_score,
                )
            )
        return counter

    return {
        "all": count_reasons(non_top),
        "top20": count_reasons(ranked_non_top[:20]),
    }


def _calibration_summary(
    *,
    candidates: list[dict[str, Any]],
    top: list[dict[str, Any]],
    source_warning_codes: dict[str, list[str]],
    gate_reason_distribution: dict[str, Counter[str]],
    top_eligible_count: int,
    quality_flagged_count: int,
    duplicate_grouped_count: int,
) -> list[str]:
    labels: list[str] = []
    top20 = gate_reason_distribution.get("top20", Counter())
    all_reasons = gate_reason_distribution.get("all", Counter())
    warning_values = [warning for warnings in source_warning_codes.values() for warning in warnings]
    if candidates and (
        quality_flagged_count / len(candidates) >= 0.5
        or warning_values.count("source_zero_survivors")
        >= max(1, len(source_warning_codes) // 2)
    ):
        labels.append("likely_source_quality_issue")
    if top20.get("generic_why_for_unspecific_seed_type", 0) >= 3:
        labels.append("likely_generic_why_gate_pressure")
    if top20.get("generic_why_for_unspecific_seed_type", 0) >= 3 or (
        len(candidates) >= 30 and 0 < top_eligible_count < 5
    ):
        labels.append("likely_gate_too_strict")
    duplicate_reasons = sum(
        count for reason, count in all_reasons.items() if reason.startswith("near_duplicate_role")
    )
    if duplicate_reasons >= 3 or (
        candidates and duplicate_grouped_count / len(candidates) >= 0.2
    ):
        labels.append("likely_duplicate_collapse")
    if "source_top_skew" in warning_values:
        labels.append("likely_source_skew")
    weak_quality_reasons = sum(
        count
        for reason, count in top20.items()
        if reason.startswith("action_not_top")
        or reason.startswith("score_below")
        or reason == "final_grade=D"
    )
    if top20 and weak_quality_reasons / sum(top20.values()) >= 0.4:
        labels.append("likely_low_raw_quality")
    if not labels:
        labels.append("no_clear_bottleneck")
    return [
        "- summary_labels: " + " + ".join(dict.fromkeys(labels)),
        f"- top_eligible_candidates: {top_eligible_count}",
        f"- rendered_top_candidates: {len(top)}",
    ]


def _operator_summary(
    *,
    candidates: list[dict[str, Any]],
    top: list[dict[str, Any]],
    top_eligible_count: int,
    quality_flagged_count: int,
    duplicate_grouped_count: int,
    source_warning_codes: dict[str, list[str]],
    gate_reason_distribution: dict[str, Counter[str]],
) -> list[str]:
    raw_count = len(candidates)
    top20 = gate_reason_distribution.get("top20", Counter())
    all_reasons = gate_reason_distribution.get("all", Counter())
    warning_values = [warning for warnings in source_warning_codes.values() for warning in warnings]
    source_quality_pressure = bool(
        raw_count
        and (
            quality_flagged_count / raw_count >= 0.5
            or warning_values.count("source_zero_survivors")
            >= max(1, len(source_warning_codes) // 2)
        )
    )
    generic_pressure = top20.get("generic_why_for_unspecific_seed_type", 0) >= 3
    stale_pressure = bool(
        raw_count
        and (
            _freshness_count(candidates, "stale") / raw_count >= 0.4
            or "source_all_stale" in warning_values
        )
    )
    duplicate_pressure = bool(
        sum(
            count
            for reason, count in all_reasons.items()
            if reason.startswith("near_duplicate_role")
        )
        >= 3
        or (raw_count and duplicate_grouped_count / raw_count >= 0.2)
    )
    weak_quality_reasons = sum(
        count
        for reason, count in top20.items()
        if reason.startswith("action_not_top")
        or reason.startswith("score_below")
        or reason == "final_grade=D"
    )
    low_raw_quality = bool(top20 and weak_quality_reasons / sum(top20.values()) >= 0.4)
    if len(top) >= 5 and top_eligible_count >= len(top):
        primary_bottleneck = "no_clear_bottleneck"
    elif stale_pressure:
        primary_bottleneck = "stale_sources"
    elif source_quality_pressure:
        primary_bottleneck = "source_quality"
    elif duplicate_pressure:
        primary_bottleneck = "duplicate_collapse"
    elif generic_pressure:
        primary_bottleneck = "generic_why"
    elif low_raw_quality:
        primary_bottleneck = "low_raw_quality"
    else:
        primary_bottleneck = "no_clear_bottleneck"
    run_health = {
        "source_quality": "source_quality_issue",
        "stale_sources": "review",
        "duplicate_collapse": "gate_pressure",
        "generic_why": "gate_pressure",
        "low_raw_quality": "weak_pool",
        "no_clear_bottleneck": "ok" if len(top) >= 5 else "review",
    }[primary_bottleneck]
    recommended_action = {
        "source_quality": "review_source_allowlist_candidates",
        "stale_sources": "review_source_allowlist_candidates",
        "duplicate_collapse": "review_near_miss_queue_before_append",
        "generic_why": "review_generic_why_template_queue",
        "low_raw_quality": "manual_seed_input_needed",
        "no_clear_bottleneck": (
            "ok_to_append_if_digest_looks_good"
            if run_health == "ok"
            else "review_near_miss_queue_before_append"
        ),
    }[primary_bottleneck]
    return [
        f"- run_health: {run_health}",
        f"- primary_bottleneck: {primary_bottleneck}",
        f"- rendered_top_candidates: {len(top)}",
        f"- top_eligible_candidates: {top_eligible_count}",
        f"- raw_candidates: {raw_count}",
        f"- recommended_operator_action: {recommended_action}",
        "- do_not_change_thresholds_yet: true",
    ]


def _source_recommendation_records(
    *,
    raw_source_counts: Counter[str],
    source_counts: Counter[str],
    top_eligible_source_counts: Counter[str],
    quality_flags_by_source: dict[str, Counter[str]],
    source_warning_codes: dict[str, list[str]],
    source_policy_by_source: dict[str, str] | None = None,
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    source_policy_by_source = source_policy_by_source or {}
    for source, raw_count in raw_source_counts.most_common():
        recommendation, reason = _source_recommendation(
            raw_count=raw_count,
            top_count=source_counts.get(source, 0),
            top_eligible_count=top_eligible_source_counts.get(source, 0),
            quality_flags=quality_flags_by_source.get(source, Counter()),
            warnings=source_warning_codes.get(source, []),
            source_freshness_policy=source_policy_by_source.get(source),
        )
        records.append(
            {
                "source": source,
                "recommendation": recommendation,
                "reason": reason,
            }
        )
    return records


def _source_recommendation_table(records: list[dict[str, Any]]) -> list[str]:
    rows: list[str] = []
    for record in records:
        rows.append(
            "| "
            f"{_table_cell(record['source'])} | "
            f"{record['recommendation']} | "
            f"{_table_cell(record['reason'])} |"
        )
    return rows or ["| none | review | no source candidates |"]


def _source_recommendation(
    *,
    raw_count: int,
    top_count: int,
    top_eligible_count: int,
    quality_flags: Counter[str],
    warnings: list[str],
    source_freshness_policy: str | None = None,
) -> tuple[str, str]:
    dominant_flag, dominant_count = quality_flags.most_common(1)[0] if quality_flags else ("", 0)
    dominant_share = dominant_count / raw_count if raw_count else 0
    if top_count > 0:
        return "keep", "has rendered top candidates"
    if top_eligible_count > 0:
        if dominant_share >= 0.5:
            return "review", f"has eligible candidates but dominant flag {dominant_flag}"
        return "keep", "has top eligible candidates"
    if dominant_share >= 0.4 and dominant_flag in {
        "single_stock_or_asset_frame",
        "market_rate_stress",
        "single_company_frame",
    }:
        return "evidence_only", f"{dominant_flag} dominant; use as evidence/manual source"
    if dominant_share >= 0.5 and dominant_flag in {"pure_place_listing"}:
        return "manual_only", "pure_place_listing dominant; not daily seed discovery"
    if dominant_share >= 0.5 and dominant_flag in {
        "empty_summary",
        "empty_summary_domestic_business",
    }:
        return "manual_only", "many empty summaries; needs manual curation"
    if "source_all_stale" in warnings:
        return "review", "source_all_stale; verify feed freshness before holding"
    if "source_unknown_freshness_high" in warnings:
        return "review", "source_unknown_freshness_high"
    if source_freshness_policy == "low_frequency_research" and raw_count >= 5:
        return (
            "review",
            "low_frequency_research; review research-template queue before holding",
        )
    if raw_count >= 5 and "source_zero_survivors" in warnings:
        return "hold_daily_fetch", "source_zero_survivors"
    return "review", "insufficient survival signal"


def _source_manual_action(recommendation: str, reason: str) -> str:
    if recommendation == "keep":
        return "keep_enabled"
    if recommendation == "hold_daily_fetch":
        return "consider_hold_daily_fetch"
    if recommendation == "evidence_only":
        return "use_as_manual_evidence_source"
    if recommendation == "manual_only":
        return "manual_curation_only"
    if "low_frequency_research" in reason:
        return "review_research_template_queue"
    if "stale" in reason or "freshness" in reason:
        return "review_feed_freshness"
    return "consider_hold_daily_fetch"


def _source_allowlist_review_queue(
    records: list[dict[str, Any]],
    *,
    raw_source_counts: Counter[str],
    source_counts: Counter[str],
    top_eligible_source_counts: Counter[str],
    quality_flags_by_source: dict[str, Counter[str]],
) -> list[str]:
    rows: list[str] = []
    for record in records:
        source = str(record["source"])
        dominant_flags = ", ".join(
            f"{flag}={count}"
            for flag, count in quality_flags_by_source.get(source, Counter()).most_common(3)
        ) or "none"
        recommendation = str(record["recommendation"])
        reason = str(record["reason"])
        rows.append(
            "| "
            + " | ".join(
                [
                    _table_cell(source),
                    recommendation,
                    _table_cell(reason),
                    _table_cell(dominant_flags),
                    str(raw_source_counts.get(source, 0)),
                    str(top_eligible_source_counts.get(source, 0)),
                    str(source_counts.get(source, 0)),
                    _source_manual_action(recommendation, reason),
                ]
            )
            + " |"
        )
    return rows or ["| none | review | no source candidates | none | 0 | 0 | 0 | keep_enabled |"]


def _passes_top_gate_for_scenario(candidate: dict[str, Any], scenario: str) -> bool:
    if scenario == "allow_high_specificity_generic_why":
        failures = _top_quality_gate_failures(candidate)
        specificity = _story_specificity(candidate)
        flags = set(candidate.get("quality_flags") or [])
        return (
            failures == ["generic_why_for_unspecific_seed_type"]
            and specificity.get("level") == "high"
            and not TOP_EXCLUDED_QUALITY_FLAGS.intersection(flags)
        ) or not failures
    if scenario == "allow_stale_editorial_categories":
        specificity = _story_specificity(candidate)
        seed_type = str(candidate.get("seed_type") or candidate.get("editorial_category") or "")
        can_ignore_stale = (
            "stale_item" in set(candidate.get("quality_flags") or [])
            and seed_type in SPECIFIC_TOP_SEED_TYPES
            and specificity.get("level") in {"medium", "high"}
        )
        ignored = {"stale_item"} if can_ignore_stale else set()
        return not _top_quality_gate_failures(
            candidate,
            ignore_excluded_quality_flags=ignored,
        )
    return _passes_top_quality_gate(candidate)


def _scenario_top_eligible_candidates(
    candidates: list[dict[str, Any]],
    *,
    scenario: str,
    min_score: float,
) -> list[dict[str, Any]]:
    scenario_min_score = 30 if scenario == "lower_min_score_30" else min_score
    return [
        candidate
        for candidate in candidates
        if candidate.get("recommended_action", "keep_for_later") in TOP_ACTIONS
        and candidate.get("final_grade") != "D"
        and _total_score(candidate) >= scenario_min_score
        and _passes_top_gate_for_scenario(candidate, scenario)
    ]


def _format_candidate_examples(candidates: list[dict[str, Any]], limit: int = 3) -> str:
    examples = []
    for item in candidates[:limit]:
        examples.append(
            f"{item.get('title')} ({item.get('source', 'unknown')}, {_total_score(item):g})"
        )
    return "; ".join(examples) if examples else "none"


def _what_if_gate_simulation(
    candidates: list[dict[str, Any]],
    top: list[dict[str, Any]],
    *,
    limit: int,
    max_per_source: int,
    min_score: float,
) -> list[str]:
    scenarios = [
        "current",
        "allow_high_specificity_generic_why",
        "allow_stale_editorial_categories",
        "lower_min_score_30",
    ]
    current_eligible = _scenario_top_eligible_candidates(
        candidates,
        scenario="current",
        min_score=min_score,
    )
    current_ids = {str(item.get("candidate_id")) for item in current_eligible}
    rows: list[str] = []
    for scenario in scenarios:
        eligible = _scenario_top_eligible_candidates(
            candidates,
            scenario=scenario,
            min_score=min_score,
        )
        projected_top = _select_top_from_eligible(
            eligible,
            limit=limit,
            max_per_source=max_per_source,
        )
        added = sorted(
            [item for item in eligible if str(item.get("candidate_id")) not in current_ids],
            key=_total_score,
            reverse=True,
        )
        if scenario == "current":
            added = []
        rows.append(
            "| "
            + " | ".join(
                [
                    scenario,
                    str(len(eligible)),
                    str(len(projected_top)),
                    _table_cell(_format_candidate_examples(added)),
                ]
            )
            + " |"
        )
    return rows


def _story_specificity(candidate: dict[str, Any]) -> dict[str, Any]:
    specificity = candidate.get("story_specificity")
    if isinstance(specificity, dict):
        return specificity
    return {
        "score": 0.0,
        "level": "low",
        "signals": [],
        "generic_why_detected": _has_generic_why(candidate),
    }


def _specificity_suggested_action(candidate: dict[str, Any]) -> str:
    specificity = _story_specificity(candidate)
    level = str(specificity.get("level") or "low")
    flags = set(candidate.get("quality_flags") or [])
    if TOP_EXCLUDED_QUALITY_FLAGS.intersection(flags):
        return "keep_gate"
    if level == "high":
        return "improve_template"
    if level == "medium":
        return "manual_review"
    return "keep_gate"


def _generic_specificity_examples(
    candidates: list[dict[str, Any]],
    top_ids: set[str],
    top: list[dict[str, Any]],
    *,
    limit: int,
    max_per_source: int,
    min_score: float,
) -> list[str]:
    top_source_counts = Counter(str(item.get("source") or "unknown") for item in top)
    examples: list[dict[str, Any]] = []
    for item in sorted(candidates, key=_total_score, reverse=True):
        if str(item.get("candidate_id")) in top_ids:
            continue
        reasons = _top_exclusion_reasons(
            item,
            top_ids,
            top_source_counts,
            rendered_top_count=len(top),
            limit=limit,
            max_per_source=max_per_source,
            min_score=min_score,
        )
        if "generic_why_for_unspecific_seed_type" in reasons:
            examples.append({**item, "_top_exclusion_reasons": reasons})
        if len(examples) >= 10:
            break
    lines: list[str] = []
    for item in examples:
        specificity = _story_specificity(item)
        signals = _format_list(specificity.get("signals") or [])
        lines.append(
            f"- {item.get('title')}: score={_total_score(item):g}; "
            f"specificity={specificity.get('score')} "
            f"({specificity.get('level')}); signals={signals}; "
            f"generic_why_detected={specificity.get('generic_why_detected')}; "
            f"suggested_action={_specificity_suggested_action(item)}; "
            f"reason={_format_list(item.get('_top_exclusion_reasons') or [])}"
        )
    return lines


def _template_direction(candidate: dict[str, Any]) -> str:
    specificity = _story_specificity(candidate)
    signals = set(specificity.get("signals") or [])
    if specificity.get("level") == "low":
        return "not_enough_specificity_keep_gate"
    if "has_number" in signals and ("has_tension" in signals or "has_mechanism" in signals):
        return "number_tension_bridge"
    if "has_named_actor" in signals and "has_mechanism" in signals:
        return "actor_mechanism_result"
    if "has_korea_bridge" in signals:
        return "korea_bridge_needed"
    if "has_visual_hook" in signals:
        return "visual_hook_first"
    return "actor_mechanism_result" if "has_named_actor" in signals else "manual_review"


def _generic_template_improvement_queue(
    candidates: list[dict[str, Any]],
    top_ids: set[str],
    top: list[dict[str, Any]],
    *,
    limit: int,
    max_per_source: int,
    min_score: float,
) -> list[str]:
    rows = [
        (
            "| title | source | score | story_specificity | why_interesting | "
            "suggested_template_direction |"
        ),
        "| --- | --- | ---: | --- | --- | --- |",
    ]
    top_source_counts = Counter(str(item.get("source") or "unknown") for item in top)
    queued: list[dict[str, Any]] = []
    for item in sorted(candidates, key=_total_score, reverse=True):
        if str(item.get("candidate_id")) in top_ids:
            continue
        reasons = _top_exclusion_reasons(
            item,
            top_ids,
            top_source_counts,
            rendered_top_count=len(top),
            limit=limit,
            max_per_source=max_per_source,
            min_score=min_score,
        )
        specificity = _story_specificity(item)
        if (
            "generic_why_for_unspecific_seed_type" in reasons
            and specificity.get("level") in {"medium", "high"}
        ):
            queued.append(item)
        if len(queued) >= 10:
            break
    for item in queued:
        specificity = _story_specificity(item)
        specificity_text = (
            f"{specificity.get('level')}:{_format_list(specificity.get('signals') or [])}"
        )
        rows.append(
            "| "
            + " | ".join(
                [
                    _table_cell(item.get("title", "")),
                    _table_cell(item.get("source", "unknown")),
                    f"{_total_score(item):g}",
                    _table_cell(specificity_text),
                    _table_cell(item.get("why_interesting", "")),
                    _template_direction(item),
                ]
            )
            + " |"
        )
    if len(rows) == 2:
        rows.append("| none | unknown | 0 | low:none | none | not_enough_specificity_keep_gate |")
    return rows


def _top_exclusion_reasons(
    candidate: dict[str, Any],
    top_ids: set[str],
    top_source_counts: Counter[str],
    *,
    rendered_top_count: int,
    limit: int,
    max_per_source: int,
    min_score: float,
) -> list[str]:
    candidate_id = str(candidate.get("candidate_id"))
    if candidate_id in top_ids:
        return ["included"]
    reasons: list[str] = []
    action = str(candidate.get("recommended_action") or "keep_for_later")
    if action not in TOP_ACTIONS:
        reasons.append(f"action_not_top={action}")
    if str(candidate.get("final_grade") or "") == "D":
        reasons.append("final_grade=D")
    score = _total_score(candidate)
    if score < min_score:
        reasons.append(f"score_below_{min_score:g}")
    reasons.extend(_top_quality_gate_failures(candidate))
    if not reasons:
        source = str(candidate.get("source") or candidate.get("source_id") or "unknown")
        if max_per_source > 0 and top_source_counts.get(source, 0) >= max_per_source:
            reasons.append(f"source_cap_reached={max_per_source}")
        elif rendered_top_count >= limit:
            reasons.append(f"below_render_limit={limit}")
        else:
            reasons.append("not_selected_after_balance")
    return reasons


def _near_miss_queue(
    candidates: list[dict[str, Any]],
    top_ids: set[str],
    top: list[dict[str, Any]],
    *,
    limit: int,
    max_per_source: int,
    min_score: float,
) -> list[str]:
    top_source_counts = Counter(str(item.get("source") or "unknown") for item in top)
    near_misses = sorted(
        [item for item in candidates if str(item.get("candidate_id")) not in top_ids],
        key=_total_score,
        reverse=True,
    )[:10]
    lines: list[str] = []
    for item in near_misses:
        reasons = _top_exclusion_reasons(
            item,
            top_ids,
            top_source_counts,
            rendered_top_count=len(top),
            limit=limit,
            max_per_source=max_per_source,
            min_score=min_score,
        )
        age_hours = item.get("age_hours")
        freshness = str(item.get("freshness_status") or "unknown")
        age_text = "unknown" if age_hours is None else f"{age_hours}h"
        duplicate_role = str(item.get("near_duplicate_role") or "none")
        duplicate_reason = str(item.get("near_duplicate_reason") or "none")
        lines.append(
            f"- {item.get('title')}: source={item.get('source', 'unknown')}; "
            f"total_score={_total_score(item):g}; "
            f"action={item.get('recommended_action')}; grade={item.get('final_grade')}; "
            f"freshness={freshness}/{age_text}; "
            f"quality_flags={_format_list(item.get('quality_flags') or [])}; "
            f"failure_modes={_format_list(item.get('failure_modes') or [])}; "
            f"near_duplicate={duplicate_role} ({duplicate_reason}); "
            f"reason={_format_list(reasons)}"
        )
    return lines


def _source_skew_warnings(source_counts: Counter[str], top_count: int) -> list[str]:
    if top_count < 3:
        return []
    warnings: list[str] = []
    for source, count in source_counts.most_common():
        share = count / top_count
        if share >= 0.6:
            warnings.append(
                f"- source_top_skew: {source} has {count}/{top_count} "
                f"top candidates ({share:.0%})"
            )
    return warnings


def _near_duplicate_groups(candidates: list[dict[str, Any]]) -> list[str]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for item in candidates:
        group_id = str(item.get("near_duplicate_group_id") or "")
        if group_id and int(item.get("near_duplicate_count") or 1) > 1:
            grouped.setdefault(group_id, []).append(item)
    lines: list[str] = []
    for group_id, items in grouped.items():
        primary = next(
            (item for item in items if item.get("near_duplicate_role") == "primary"),
            items[0],
        )
        lines.append(
            f"- `{group_id}` primary=`{primary.get('title')}` "
            f"source={primary.get('source')} score={_total_score(primary):g} "
            f"count={len(items)}"
        )
        for item in sorted(items, key=_total_score, reverse=True):
            lines.append(
                f"  - {item.get('near_duplicate_role')}: {item.get('source')} / "
                f"{item.get('title')} score={_total_score(item):g}; "
                f"reason={item.get('near_duplicate_reason')}; "
                f"shared_tokens={item.get('near_duplicate_shared_tokens', 0)}; "
                f"overlap={item.get('near_duplicate_title_overlap', 0)}"
            )
    return lines


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
    max_per_source: Annotated[
        int,
        typer.Option("--max-per-source", min=1, help="Max top candidates per source."),
    ] = 3,
    review_board_limit: Annotated[
        int | None,
        typer.Option("--review-board-limit", help="Max rows in bundle review board."),
    ] = None,
    bundle_near_miss_limit: Annotated[
        int | None,
        typer.Option(
            "--bundle-near-miss-limit",
            help="High-score near misses available for bundle support links.",
        ),
    ] = None,
    review_history_path: Annotated[
        Path,
        typer.Option("--review-history", help="Local review-board history JSONL."),
    ] = paths.JIBI_REVIEW_BOARD_HISTORY_JSONL,
    alternate_review_board_only: Annotated[
        bool,
        typer.Option(
            "--alternate-review-board-only",
            help="Write alternate review-board CSV/report only; do not touch live sheet.",
        ),
    ] = False,
    alternate_include_reviewed: Annotated[
        bool,
        typer.Option(
            "--alternate-include-reviewed",
            help="Allow already reviewed story fingerprints in the alternate batch.",
        ),
    ] = False,
    editorial_overrides_path: Annotated[
        Path | None,
        typer.Option(
            "--editorial-overrides",
            help="Optional bundle review title/description override JSON.",
        ),
    ] = None,
    allow_reviewed_candidates: Annotated[
        bool | None,
        typer.Option(
            "--allow-reviewed-candidates/--suppress-reviewed-candidates",
            help="Allow candidates that already have local human review comments.",
        ),
    ] = None,
    use_board_score: Annotated[
        bool | None,
        typer.Option(
            "--use-board-score/--use-total-score-order",
            help="Use internal review-board score ordering for bundle review rows.",
        ),
    ] = None,
) -> None:
    if alternate_review_board_only:
        alt_csv_path, metadata_path, report_path = render_alternate_review_board(
            input_path=input_path,
            output_dir=output_dir,
            digest_date=digest_date,
            limit=limit,
            max_per_source=max_per_source,
            review_board_limit=review_board_limit,
            bundle_near_miss_limit=bundle_near_miss_limit,
            review_history_path=review_history_path,
            include_reviewed=alternate_include_reviewed,
        )
        console.print(
            "[green]Rendered alternate review board to "
            f"{alt_csv_path}, {metadata_path}, and {report_path}. "
            "The live Jibi sheet was not replaced.[/green]"
        )
        return
    md_path, csv_path, top = render_daily_digest(
        input_path=input_path,
        output_dir=output_dir,
        digest_date=digest_date,
        limit=limit,
        max_per_source=max_per_source,
        review_board_limit=review_board_limit,
        bundle_near_miss_limit=bundle_near_miss_limit,
        review_history_path=review_history_path,
        editorial_overrides_path=editorial_overrides_path,
        allow_reviewed_candidates=allow_reviewed_candidates,
        use_board_score=use_board_score,
    )
    bundle_review_csv_path = output_dir / f"{_digest_date(digest_date)}_bundle_review_sheet.csv"
    console.print(
        "[green]Rendered "
        f"{len(top)} candidates to {md_path}, {csv_path}, and "
        f"{bundle_review_csv_path}.[/green]"
    )


if __name__ == "__main__":
    app()
