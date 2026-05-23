"""Render jibi scored candidates into a daily Markdown digest and CSV preview."""

from __future__ import annotations

import csv
import hashlib
from collections import Counter
from datetime import date
from pathlib import Path
from typing import Annotated, Any

import typer
from rich.console import Console

from luddite import paths
from luddite.agents.jibi.append_to_sheet import (
    BUNDLE_REVIEW_SHEET_COLUMNS,
    SHEET_COLUMNS,
)
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
}
DEFAULT_TOP_MIN_SCORE = 35
DEFAULT_SOURCE_ROLE_TOP_CAPS = {
    "research_note": 3,
    "policy_release": 2,
    "public_wire": 3,
    "academic_explainer": 2,
    "market_wire": 1,
    "section_news": 3,
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
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = BUNDLE_REVIEW_SHEET_COLUMNS
    candidate_by_id = {
        str(candidate.get("candidate_id")): candidate
        for candidate in candidates
        if candidate.get("candidate_id")
    }
    bundle_records = _story_bundle_records(candidates, top, near_miss_limit=0)
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
            primary_title = record.get("primary_title") or representative.get("title") or ""
            writer.writerow(
                _bundle_review_row(
                    digest_date=digest_date,
                    review_item_id=f"{digest_date}:{record['story_bundle_id']}",
                    review_title=str(record["bundle_title"]),
                    candidate=representative,
                    candidate_title=primary_title,
                    jibi_judgment=_bundle_judgment(record, fit),
                    reason=_join_distinct_reason(str(record["why_bundle"]), reason),
                    sub_links=_related_bundle_links(record, candidate_by_id),
                    related_titles=_related_bundle_titles(record),
                )
            )


def _bundle_judgment(record: dict[str, Any], fit: str) -> str:
    values = [
        str(record.get("bundle_type") or ""),
        fit,
        str(record.get("suggested_operator_action") or ""),
    ]
    return " / ".join(value for value in values if value)


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
    return " | ".join(links)


def _bundle_review_row(
    *,
    digest_date: str,
    review_item_id: str,
    review_title: str,
    candidate: dict[str, Any],
    candidate_title: str,
    jibi_judgment: str,
    reason: str,
    sub_links: str,
    related_titles: str,
) -> dict[str, Any]:
    why = str(candidate.get("why_interesting") or "").strip()
    description_parts = [
        f"{jibi_judgment}: {reason}".strip(": "),
        f"자료 요약: {why}" if why else "",
        f"같이 볼 후보: {related_titles}" if related_titles else "",
    ]
    return {
        "날짜": digest_date,
        "제목": review_title or candidate_title,
        "메인 링크": candidate.get("seed_url", ""),
        "서브 링크": sub_links,
        "설명": " ".join(part for part in description_parts if part),
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
) -> tuple[Path, Path, list[dict[str, Any]]]:
    date_value = _digest_date(digest_date)
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
    )
    write_quality_report(
        paths.REPORTS_DIR / f"jibi_quality_{date_value}.md",
        candidates,
        top,
        limit=limit,
        max_per_source=max_per_source,
    )
    return md_path, csv_path, top


def write_quality_report(
    path: Path,
    candidates: list[dict[str, Any]],
    top: list[dict[str, Any]],
    limit: int = 10,
    max_per_source: int = 3,
    min_score: float = DEFAULT_TOP_MIN_SCORE,
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
    storyline_fit_rows = _storyline_fit_audit_rows(
        candidates,
        top,
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
        "## Storyline Fit Audit",
        "",
        (
            "| role | title | source | seed_type | storyline_fit | merge_or_reason | "
            "suggested_operator_action |"
        ),
        "| --- | --- | --- | --- | --- | --- | --- |",
        *storyline_fit_rows,
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


def _story_bundle_hash(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:10]


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
) -> None:
    md_path, csv_path, top = render_daily_digest(
        input_path=input_path,
        output_dir=output_dir,
        digest_date=digest_date,
        limit=limit,
        max_per_source=max_per_source,
    )
    bundle_review_csv_path = output_dir / f"{_digest_date(digest_date)}_bundle_review_sheet.csv"
    console.print(
        "[green]Rendered "
        f"{len(top)} candidates to {md_path}, {csv_path}, and "
        f"{bundle_review_csv_path}.[/green]"
    )


if __name__ == "__main__":
    app()
