"""Render jibi scored candidates into a daily Markdown digest and CSV preview."""

from __future__ import annotations

import csv
from collections import Counter
from datetime import date
from pathlib import Path
from typing import Annotated, Any

import typer
from rich.console import Console

from luddite import paths
from luddite.agents.jibi.append_to_sheet import SHEET_COLUMNS
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
}
DEFAULT_TOP_MIN_SCORE = 35
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
) -> list[dict[str, Any]]:
    eligible = _top_eligible_candidates(candidates, min_score=min_score)
    ranked = sorted(
        eligible,
        key=lambda item: (
            item.get("scores", {}).get("total_score", 0),
            item.get("scores", {}).get("broadcast_potential_proxy", 0),
        ),
        reverse=True,
    )
    selected: list[dict[str, Any]] = []
    source_counts: dict[str, int] = {}
    for candidate in ranked:
        source = str(candidate.get("source") or candidate.get("source_id") or "unknown")
        if max_per_source > 0 and source_counts.get(source, 0) >= max_per_source:
            continue
        selected.append(candidate)
        source_counts[source] = source_counts.get(source, 0) + 1
        if len(selected) >= limit:
            break
    return selected


def _passes_top_quality_gate(candidate: dict[str, Any]) -> bool:
    return not _top_quality_gate_failures(candidate)


def _top_quality_gate_failures(candidate: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    flags = set(candidate.get("quality_flags", []))
    failure_modes = set(candidate.get("failure_modes", []))
    excluded_flags = sorted(TOP_EXCLUDED_QUALITY_FLAGS.intersection(flags))
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
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text(
        render_markdown(top, date_value, excluded_to_render, all_candidates=candidates),
        encoding="utf-8",
    )
    write_sheet_preview(csv_path, top, date_value)
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
    quality_gate_pass = [item for item in candidates if _passes_top_quality_gate(item)]
    after_gate_source_counts = Counter(
        str(item.get("source") or "unknown") for item in quality_gate_pass
    )
    top_eligible = _top_eligible_candidates(candidates, min_score=min_score)
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
    for item in candidates:
        source = str(item.get("source") or "unknown")
        freshness = str(item.get("freshness_status") or "unknown")
        freshness_by_source.setdefault(source, Counter())[freshness] += 1
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
    console.print(
        f"[green]Rendered {len(top)} candidates to {md_path} and {csv_path}.[/green]"
    )


if __name__ == "__main__":
    app()
