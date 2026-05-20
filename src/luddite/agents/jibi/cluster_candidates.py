"""Cluster scored jibi candidates into rule-based story seeds."""

from __future__ import annotations

import hashlib
import re
from collections import Counter, defaultdict
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Annotated, Any

import typer
from rich.console import Console

from luddite import paths
from luddite.agents.jibi.heuristics import text_blob
from luddite.agents.jibi.slideability import merge_cluster_slideability
from luddite.utils.jsonl import read_jsonl, write_jsonl
from luddite.utils.schemas import validate_with_schema

app = typer.Typer(no_args_is_help=False)
console = Console()

READY_READINESS = {
    "ready_for_anny",
    "needs_more_evidence",
    "editorial_review",
    "keep_for_later",
}
STRONG_SEED_TYPES = {
    "productive_finance_policy",
    "industrial_policy_rnd",
    "infrastructure_project_failure",
    "ai_knowledge_institution",
    "climate_policy_conflict",
    "cost_asymmetry",
    "political_fracture",
}
CATEGORY_CLUSTER_KEYS = {
    "market_rate_stress",
    "single_company_financing",
    "productive_finance_policy",
    "industrial_policy_rnd",
    "infrastructure_project_failure",
    "ai_knowledge_institution",
    "climate_policy_conflict",
}
HIGH_RISK_FLAGS = {
    "political_sensitivity",
    "medical_claim_risk",
    "crime_or_drug_sensitivity",
    "investment_advice_risk",
    "corporate_promo_risk",
}
OFFICIAL_SOURCE_HINTS = {
    "productive_finance_policy": ["금융위원회", "한국은행", "기획재정부"],
    "industrial_policy_rnd": ["과학기술정보통신부", "산업통상자원부", "국가연구개발사업 자료"],
    "infrastructure_project_failure": ["감사보고서", "국회/의회 보고서", "교통부 예산자료"],
    "ai_knowledge_institution": ["교육부/학교 자료", "박물관/천문관 공식 설명", "AI 교육 연구"],
    "climate_policy_conflict": ["산림청/재난기관 자료", "기후 재난 통계", "정책 원문"],
    "market_rate_stress": ["한국은행", "미국 재무부/FRED", "금융시장 통계"],
}
STOPWORDS = {
    "the",
    "and",
    "with",
    "from",
    "into",
    "about",
    "that",
    "this",
    "news",
    "says",
    "will",
    "jibi",
}


def cluster_candidates(
    input_path: Path = paths.JIBI_SCORED_CANDIDATES_JSONL,
    output_path: Path = paths.JIBI_CANDIDATE_CLUSTERS_JSONL,
    report_path: Path | None = None,
    digest_path: Path | None = None,
    handoff_path: Path = paths.ANNY_STORY_SEED_HANDOFF_JSONL,
    handoff_digest_path: Path | None = None,
    run_date: str | None = None,
    now: datetime | None = None,
) -> list[dict[str, Any]]:
    date_text = run_date or date.today().isoformat()
    report_path = report_path or paths.REPORTS_DIR / f"jibi_clusters_{date_text}.md"
    digest_path = digest_path or paths.DAILY_DIGEST_DIR / f"{date_text}_clusters.md"
    handoff_digest_path = (
        handoff_digest_path
        or paths.DAILY_DIGEST_DIR / f"{date_text}_story_seed_handoff.md"
    )
    candidates = read_jsonl(input_path) if input_path.exists() else []
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for candidate in candidates:
        if candidate.get("recommended_action") == "reject":
            continue
        grouped[_cluster_key(candidate)].append(candidate)

    timestamp = (now or datetime.now(UTC)).isoformat()
    clusters = [
        build_cluster(key, group, created_at=timestamp)
        for key, group in grouped.items()
        if group
    ]
    clusters.sort(
        key=lambda item: (
            _readiness_rank(str(item["readiness"])),
            len(item["candidate_ids"]),
            _cluster_score(item),
        ),
        reverse=True,
    )
    for cluster in clusters:
        errors = validate_with_schema(cluster, "story_seed_schema.json")
        if errors:
            raise ValueError(f"{cluster['cluster_id']} schema errors: {'; '.join(errors)}")
    write_jsonl(output_path, clusters)
    write_cluster_report(report_path, clusters)
    write_cluster_digest(digest_path, clusters)
    handoff_clusters = [cluster for cluster in clusters if cluster["anny_handoff_ready"]]
    write_jsonl(handoff_path, [_handoff_record(cluster) for cluster in handoff_clusters])
    write_story_seed_handoff(handoff_digest_path, handoff_clusters)
    return clusters


def build_cluster(
    cluster_key: str,
    candidates: list[dict[str, Any]],
    *,
    created_at: str,
) -> dict[str, Any]:
    ranked = sorted(
        candidates,
        key=lambda item: (
            item.get("scores", {}).get("total_score", 0),
            item.get("scores", {}).get("broadcast_potential_proxy", 0),
        ),
        reverse=True,
    )
    primary = ranked[0]
    candidate_ids = [str(item["candidate_id"]) for item in ranked]
    source_ids = sorted(
        {
            str(item.get("source_id") or item.get("source") or "unknown")
            for item in ranked
            if item.get("source_id") or item.get("source")
        }
    )
    seed_type = _most_common_value(ranked, "seed_type")
    editorial_category = _most_common_value(ranked, "editorial_category") or seed_type
    risk_flags = sorted(
        {
            str(flag)
            for item in ranked
            for flag in item.get("risk_flags", [])
            if str(flag).strip()
        }
    )
    risk_level = _cluster_risk_level(ranked, risk_flags)
    missing_evidence = _missing_evidence(ranked, editorial_category)
    readiness = _readiness(
        ranked,
        source_ids=source_ids,
        seed_type=seed_type,
        risk_flags=risk_flags,
        risk_level=risk_level,
        missing_evidence=missing_evidence,
    )
    cluster_title = _cluster_title(primary, editorial_category)
    query_terms = _query_terms(ranked, editorial_category)
    cluster = {
        "cluster_id": f"cluster_{hashlib.sha1(cluster_key.encode('utf-8')).hexdigest()[:12]}",
        "cluster_title": cluster_title,
        "story_seed_title": cluster_title,
        "primary_seed_candidate_id": str(primary["candidate_id"]),
        "candidate_ids": candidate_ids,
        "source_ids": source_ids,
        "seed_type": seed_type,
        "editorial_category": editorial_category,
        "why_story": str(primary.get("why_interesting") or primary.get("title")),
        "known_facts": _known_facts(ranked),
        "missing_evidence": missing_evidence,
        "possible_story_angles": _story_angles(ranked, editorial_category),
        "risk_flags": risk_flags,
        "risk_level": risk_level,
        "slideability": merge_cluster_slideability(ranked),
        "readiness": readiness,
        "past_video_matches": [],
        "official_evidence_needed": bool(missing_evidence),
        "suggested_official_sources": OFFICIAL_SOURCE_HINTS.get(editorial_category, []),
        "syuka_ops_query_terms": query_terms,
        "llm_enrichment_needed": readiness in {"ready_for_anny", "needs_more_evidence"},
        "created_at": created_at,
        "updated_at": created_at,
    }
    quality_flags = _quality_flags(cluster, ranked)
    handoff_priority = _handoff_priority(cluster, quality_flags)
    cluster.update(
        {
            "quality_flags": quality_flags,
            "generic_story_reason": "generic_story_reason" in quality_flags,
            "handoff_priority": handoff_priority,
            "anny_handoff_ready": _is_handoff_ready(cluster, quality_flags, handoff_priority),
            "next_action": _next_action(handoff_priority),
        }
    )
    return cluster


def _cluster_key(candidate: dict[str, Any]) -> str:
    explicit = candidate.get("story_key") or candidate.get("cluster_hint")
    if explicit:
        return str(explicit)
    category = str(candidate.get("editorial_category") or candidate.get("seed_type") or "other")
    if category in CATEGORY_CLUSTER_KEYS:
        return category
    keywords = _query_terms([candidate], category)
    if category != "other":
        return "|".join([category, *keywords[:3]])
    domain = str(candidate.get("source_url_canonical") or candidate.get("seed_url") or "")
    return "|".join([category, domain.split("/")[2] if "://" in domain else domain, *keywords[:2]])


def _known_facts(candidates: list[dict[str, Any]]) -> list[str]:
    facts: list[str] = []
    for candidate in candidates[:5]:
        title = str(candidate.get("title") or "").strip()
        source = str(candidate.get("source") or "").strip()
        if title:
            facts.append(f"{title} ({source or 'unknown source'})")
    return facts


def _missing_evidence(
    candidates: list[dict[str, Any]],
    editorial_category: str,
) -> list[str]:
    missing: list[str] = []
    for candidate in candidates:
        missing.extend(str(item).strip() for item in candidate.get("evidence_needed", []))
    if len(candidates) < 2:
        missing.append("추가 독립 후보/출처 1개 이상")
    if len({item.get("source_id") or item.get("source") for item in candidates}) < 2:
        missing.append("다른 source의 보조 기사")
    if editorial_category in OFFICIAL_SOURCE_HINTS:
        missing.append("공식 자료 또는 숫자/통계 확인")
    return list(dict.fromkeys(item for item in missing if item))


def _story_angles(candidates: list[dict[str, Any]], editorial_category: str) -> list[str]:
    angles: list[str] = []
    for candidate in candidates:
        angles.extend(str(item).strip() for item in candidate.get("possible_expansions", []))
    if not angles:
        angles = [
            "핵심 사건의 배경과 이해관계자",
            "시장/사회/제도 구조로 확장되는 지점",
            "한국 시청자가 체감할 수 있는 비교 사례",
        ]
    if editorial_category == "productive_finance_policy":
        angles.append(
            "금융은 안전하게 돈을 빌려주는 산업인가, 위험을 나눠 성장에 베팅하는 산업인가?"
        )
    return list(dict.fromkeys(item for item in angles if item))[:5]


def _readiness(
    candidates: list[dict[str, Any]],
    *,
    source_ids: list[str],
    seed_type: str,
    risk_flags: list[str],
    risk_level: str,
    missing_evidence: list[str],
) -> str:
    actions = {str(item.get("recommended_action")) for item in candidates}
    if actions == {"reject"}:
        return "reject"
    if risk_level == "high" or HIGH_RISK_FLAGS.intersection(risk_flags):
        return "editorial_review"
    if seed_type not in STRONG_SEED_TYPES and len(candidates) < 2:
        return "keep_for_later"
    if (
        len(candidates) >= 2
        and len(source_ids) >= 2
        and seed_type in STRONG_SEED_TYPES
        and risk_level in {"low", "medium"}
        and len(missing_evidence) <= 2
    ):
        return "ready_for_anny"
    if seed_type in STRONG_SEED_TYPES or any(
        item.get("recommended_action") == "gather_more_evidence" for item in candidates
    ):
        return "needs_more_evidence"
    return "keep_for_later"


def _cluster_risk_level(candidates: list[dict[str, Any]], risk_flags: list[str]) -> str:
    if any(item.get("risk_level") == "high" for item in candidates):
        return "high"
    if risk_flags or any(item.get("risk_level") == "medium" for item in candidates):
        return "medium"
    return "low"


def _query_terms(candidates: list[dict[str, Any]], category: str) -> list[str]:
    words = [category]
    blob = text_blob(*(item.get("title") for item in candidates))
    words.extend(
        word
        for word in re.findall(r"[a-zA-Z가-힣0-9]{3,}", blob)
        if word.lower() not in STOPWORDS
    )
    counts = Counter(words)
    return [word for word, _ in counts.most_common(8)]


def _cluster_title(primary: dict[str, Any], editorial_category: str) -> str:
    titles = {
        "productive_finance_policy": "생산적 금융과 정책자금 전환",
        "industrial_policy_rnd": "AI 휴머노이드와 국가 산업정책",
        "infrastructure_project_failure": "대형 인프라 사업 실패의 정치경제학",
        "ai_knowledge_institution": "AI 즉답 시대의 지식기관 역할",
        "climate_policy_conflict": "기후 재난 정책과 문화전쟁 충돌",
        "single_company_financing": "AI 공급망 투자와 단일 기업 자금조달",
        "market_rate_stress": "금리/자산가격 스트레스와 거시 리스크",
    }
    return titles.get(editorial_category, str(primary.get("title") or "Story Seed"))


def _most_common_value(candidates: list[dict[str, Any]], key: str) -> str:
    values = [str(item.get(key) or "") for item in candidates if item.get(key)]
    if not values:
        return "other"
    return Counter(values).most_common(1)[0][0]


def _readiness_rank(readiness: str) -> int:
    return {
        "ready_for_anny": 5,
        "needs_more_evidence": 4,
        "editorial_review": 3,
        "keep_for_later": 2,
        "reject": 1,
    }.get(readiness, 0)


def _priority_rank(priority: str) -> int:
    return {"high": 3, "medium": 2, "low": 1}.get(priority, 0)


def _cluster_score(cluster: dict[str, Any]) -> float:
    return float(len(cluster.get("candidate_ids", []))) + len(cluster.get("source_ids", [])) * 0.5


def _slideability_summary(slideability: dict[str, Any] | None) -> str:
    if not isinstance(slideability, dict):
        return "score=0.0, visual=low, proof=-"
    proof_types = ", ".join(slideability.get("likely_proof_object_types", [])) or "-"
    risks = ", ".join(slideability.get("risks", [])) or "-"
    return (
        f"score={slideability.get('score', 0.0)}, "
        f"visual={slideability.get('visualizability', 'low')}, "
        f"proof={proof_types}, risks={risks}"
    )


def _first_slide_idea(cluster: dict[str, Any]) -> str:
    slideability = cluster.get("slideability", {})
    if not isinstance(slideability, dict):
        return "-"
    return str(slideability.get("first_slide_idea") or "-")


def _quality_flags(cluster: dict[str, Any], candidates: list[dict[str, Any]]) -> list[str]:
    flags: set[str] = set()
    why_story = str(cluster.get("why_story") or "")
    title_blob = text_blob(*(item.get("title") for item in candidates), why_story)
    candidate_flags = _candidate_flags(candidates)
    if _is_generic_story_reason(why_story):
        flags.add("generic_story_reason")
    if len(cluster.get("candidate_ids", [])) > 1:
        flags.add("multi_candidate_cluster")
    if len(cluster.get("candidate_ids", [])) == 1 and cluster.get("readiness") == "keep_for_later":
        flags.add("singleton_thin_evidence")
    if cluster.get("official_evidence_needed"):
        flags.add("official_evidence_missing")
    if "single_company_frame" in candidate_flags:
        flags.add("single_company_frame")
    if "investment_advice_risk" in cluster.get("risk_flags", []):
        flags.add("investment_risk_cluster")
    if _is_source_roundup(title_blob):
        flags.add("source_roundup_item")
    if _is_pure_politics_statement(cluster, title_blob):
        flags.add("pure_politics_statement")
    if cluster.get("editorial_category") == "other" and (
        "generic_story_reason" in flags or len(cluster.get("candidate_ids", [])) == 1
    ):
        flags.add("no_korea_or_structure_bridge")
    return sorted(flags)


def _candidate_flags(candidates: list[dict[str, Any]]) -> set[str]:
    flags: set[str] = set()
    for candidate in candidates:
        for key in ("quality_flags", "failure_modes", "risk_flags"):
            flags.update(str(item) for item in candidate.get(key, []) if str(item).strip())
    return flags


def _is_generic_story_reason(why_story: str) -> bool:
    generic_markers = [
        "구조적 연결고리",
        "단일 기사로 소비하지 않고",
        "어느 축으로 확장 가능한지",
        "시장/사회/제도 구조",
        "한국 시청자가 체감할 수 있는 비교 사례",
    ]
    return any(marker in why_story for marker in generic_markers)


def _is_source_roundup(blob: str) -> bool:
    markers = [
        "the papers",
        "what we know",
        "live updates",
        "morning briefing",
        "things to know",
        "roundup",
        "in pictures",
    ]
    return any(marker in blob for marker in markers)


def _is_pure_politics_statement(cluster: dict[str, Any], blob: str) -> bool:
    if "political_sensitivity" not in cluster.get("risk_flags", []):
        return False
    structural_terms = {
        "climate",
        "wildfire",
        "economy",
        "market",
        "bond",
        "migration",
        "labor",
        "infrastructure",
        "budget",
        "insurance",
        "기후",
        "경제",
        "시장",
        "채권",
        "이민",
        "노동",
        "인프라",
        "예산",
    }
    if any(term in blob for term in structural_terms):
        return False
    political_terms = {
        "trump",
        "president",
        "party",
        "minister",
        "cabinet",
        "election",
        "parliament",
        "대통령",
        "정당",
        "총리",
        "장관",
        "선거",
    }
    return any(term in blob for term in political_terms)


def _handoff_priority(cluster: dict[str, Any], quality_flags: list[str]) -> str:
    category = str(cluster.get("editorial_category") or "other")
    readiness = str(cluster.get("readiness") or "")
    risk_level = str(cluster.get("risk_level") or "low")
    weak_flags = {"generic_story_reason", "source_roundup_item", "pure_politics_statement"}
    if weak_flags.intersection(quality_flags):
        return "low"
    if category != "other" and readiness in {"needs_more_evidence", "ready_for_anny"}:
        if risk_level in {"low", "medium"}:
            return "high"
    if category != "other" and readiness == "editorial_review":
        return "medium"
    if "multi_candidate_cluster" in quality_flags:
        return "medium"
    return "low"


def _is_handoff_ready(
    cluster: dict[str, Any],
    quality_flags: list[str],
    handoff_priority: str,
) -> bool:
    handoff_readiness = {"ready_for_anny", "needs_more_evidence", "editorial_review"}
    if cluster.get("readiness") not in handoff_readiness:
        return False
    if handoff_priority == "low":
        return False
    if {"generic_story_reason", "source_roundup_item", "pure_politics_statement"}.intersection(
        quality_flags
    ):
        return False
    if (
        cluster.get("editorial_category") == "other"
        and "multi_candidate_cluster" not in quality_flags
    ):
        return False
    return True


def _next_action(handoff_priority: str) -> str:
    if handoff_priority == "high":
        return "공식자료/숫자 1개와 보조 기사 1개를 붙여 anny story seed로 검토"
    if handoff_priority == "medium":
        return "리스크 프레이밍을 확인한 뒤 보조 근거를 추가"
    return "감사용 cluster로 보존하고 당장 handoff하지 않음"


def _handoff_record(cluster: dict[str, Any]) -> dict[str, Any]:
    keys = [
        "cluster_id",
        "story_seed_title",
        "readiness",
        "handoff_priority",
        "primary_seed_candidate_id",
        "candidate_ids",
        "source_ids",
        "editorial_category",
        "seed_type",
        "why_story",
        "known_facts",
        "missing_evidence",
        "possible_story_angles",
        "risk_flags",
        "risk_level",
        "slideability",
        "quality_flags",
        "official_evidence_needed",
        "suggested_official_sources",
        "syuka_ops_query_terms",
        "llm_enrichment_needed",
        "next_action",
    ]
    record = {key: cluster[key] for key in keys}
    slideability = cluster.get("slideability") or {}
    record.update(
        {
            "slideability_score": slideability.get("score", 0.0),
            "first_slide_idea": slideability.get("first_slide_idea", ""),
            "likely_proof_object_types": slideability.get("likely_proof_object_types", []),
            "visual_risks": slideability.get("risks", []),
        }
    )
    return record


def write_cluster_report(path: Path, clusters: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    readiness_counts = Counter(str(item["readiness"]) for item in clusters)
    priority_counts = Counter(str(item.get("handoff_priority", "low")) for item in clusters)
    category_counts = Counter(str(item["editorial_category"]) for item in clusters)
    flag_counts = Counter(
        str(flag)
        for cluster in clusters
        for flag in cluster.get("quality_flags", [])
    )
    singletons = [item for item in clusters if len(item["candidate_ids"]) == 1]
    official_needed = [item for item in clusters if item.get("official_evidence_needed")]
    high_risk = [item for item in clusters if item.get("risk_level") == "high"]
    rejected = [item for item in clusters if item.get("readiness") == "reject"]
    handoff_clusters = [item for item in clusters if item.get("anny_handoff_ready")]
    hidden_from_handoff = [item for item in clusters if not item.get("anny_handoff_ready")]
    lines = [
        "# Jibi Story Seed Cluster Report",
        "",
        "## Summary",
        "",
        f"- total clusters: {len(clusters)}",
        f"- singleton clusters: {len(singletons)}",
        f"- official evidence needed: {len(official_needed)}",
        f"- high-risk clusters: {len(high_risk)}",
        f"- rejected clusters: {len(rejected)}",
        f"- handoff clusters: {len(handoff_clusters)}",
        f"- hidden from handoff: {len(hidden_from_handoff)}",
        f"- generic story reason: {flag_counts.get('generic_story_reason', 0)}",
        f"- singleton thin evidence: {flag_counts.get('singleton_thin_evidence', 0)}",
        "",
        "## Clusters By Readiness",
        "",
        *[f"- {readiness}: {count}" for readiness, count in readiness_counts.most_common()],
        "",
        "## Clusters By Handoff Priority",
        "",
        *[f"- {priority}: {count}" for priority, count in priority_counts.most_common()],
        "",
        "## Clusters By Category",
        "",
        *[f"- {category}: {count}" for category, count in category_counts.most_common()],
        "",
        "## Clusters By Quality Flag",
        "",
        *[f"- {flag}: {count}" for flag, count in flag_counts.most_common()],
        "",
        "## Top Handoff Clusters",
        "",
    ]
    for cluster in sorted(
        handoff_clusters,
        key=lambda item: (_priority_rank(str(item["handoff_priority"])), _cluster_score(item)),
        reverse=True,
    )[:10]:
        lines.extend(
            [
                f"### {cluster['cluster_title']}",
                "",
                f"- priority: {cluster['handoff_priority']}",
                f"- readiness: {cluster['readiness']}",
                f"- candidates: {len(cluster['candidate_ids'])}",
                f"- sources: {', '.join(cluster['source_ids']) or '-'}",
                f"- risk: {cluster['risk_level']}",
                f"- quality_flags: {', '.join(cluster['quality_flags']) or '-'}",
                f"- Slideability: {_slideability_summary(cluster.get('slideability'))}",
                f"- First slide idea: {_first_slide_idea(cluster)}",
                f"- why_story: {cluster['why_story']}",
                "",
            ]
        )
    lines.extend(
        [
            "## Top Clusters",
            "",
        ]
    )
    for cluster in clusters[:10]:
        lines.extend(
            [
                f"### {cluster['cluster_title']}",
                "",
                f"- readiness: {cluster['readiness']}",
                f"- candidates: {len(cluster['candidate_ids'])}",
                f"- sources: {', '.join(cluster['source_ids']) or '-'}",
                f"- risk: {cluster['risk_level']}",
                f"- category: {cluster['editorial_category']}",
                f"- priority: {cluster['handoff_priority']}",
                f"- quality_flags: {', '.join(cluster['quality_flags']) or '-'}",
                f"- Slideability: {_slideability_summary(cluster.get('slideability'))}",
                f"- First slide idea: {_first_slide_idea(cluster)}",
                f"- why_story: {cluster['why_story']}",
                f"- missing_evidence: {' | '.join(cluster['missing_evidence']) or '-'}",
                "",
            ]
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_cluster_digest(path: Path, clusters: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = ["# Jibi Story Seed Clusters", ""]
    visible_clusters = [cluster for cluster in clusters if _visible_in_cluster_digest(cluster)]
    for rank, cluster in enumerate(visible_clusters[:10], start=1):
        lines.extend(
            [
                f"## {rank}. {cluster['story_seed_title']}",
                "",
                f"- Readiness: {cluster['readiness']}",
                f"- Candidates: {len(cluster['candidate_ids'])}",
                f"- Sources: {', '.join(cluster['source_ids']) or '-'}",
                f"- Risk: {cluster['risk_level']}",
                f"- Handoff priority: {cluster['handoff_priority']}",
                f"- Quality flags: {', '.join(cluster['quality_flags']) or '-'}",
                f"- Slideability: {_slideability_summary(cluster.get('slideability'))}",
                f"- First slide idea: {_first_slide_idea(cluster)}",
                "",
                "Why story:",
                f"- {cluster['why_story']}",
                "",
                "Missing evidence:",
                *[f"- {item}" for item in cluster["missing_evidence"][:4]],
                "",
                "Possible angles:",
                *[f"- {item}" for item in cluster["possible_story_angles"][:4]],
                "",
            ]
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _visible_in_cluster_digest(cluster: dict[str, Any]) -> bool:
    quality_flags = set(cluster.get("quality_flags", []))
    if cluster.get("anny_handoff_ready"):
        return True
    if cluster.get("editorial_category") != "other" and "generic_story_reason" not in quality_flags:
        return True
    if len(cluster.get("candidate_ids", [])) > 1 and "source_roundup_item" not in quality_flags:
        return True
    return False


def write_story_seed_handoff(path: Path, clusters: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    priority_counts = Counter(str(item["handoff_priority"]) for item in clusters)
    readiness_counts = Counter(str(item["readiness"]) for item in clusters)
    date_text = path.name.split("_story_seed_handoff.md")[0]
    lines = [
        f"# Jibi Story Seed Handoff — {date_text}",
        "",
        "## Summary",
        "",
        f"- Handoff clusters: {len(clusters)}",
        f"- High priority: {priority_counts.get('high', 0)}",
        f"- Medium priority: {priority_counts.get('medium', 0)}",
        f"- Editorial review: {readiness_counts.get('editorial_review', 0)}",
        f"- Needs more evidence: {readiness_counts.get('needs_more_evidence', 0)}",
        "",
    ]
    for priority in ("high", "medium"):
        bucket = [item for item in clusters if item["handoff_priority"] == priority]
        if not bucket:
            continue
        lines.extend([f"## {priority.title()} Priority Story Seeds", ""])
        for rank, cluster in enumerate(bucket, start=1):
            lines.extend(
                [
                    f"### {rank}. {cluster['story_seed_title']}",
                    "",
                    f"- Readiness: {cluster['readiness']}",
                    f"- Priority: {cluster['handoff_priority']}",
                    f"- Sources: {', '.join(cluster['source_ids']) or '-'}",
                    f"- Candidate count: {len(cluster['candidate_ids'])}",
                    f"- Risk: {cluster['risk_level']} ({', '.join(cluster['risk_flags']) or '-'})",
                    f"- Quality flags: {', '.join(cluster['quality_flags']) or '-'}",
                    f"- Slideability: {_slideability_summary(cluster.get('slideability'))}",
                    f"- First slide idea: {_first_slide_idea(cluster)}",
                    f"- Next action: {cluster['next_action']}",
                    "",
                    "Why story:",
                    f"- {cluster['why_story']}",
                    "",
                    "Known facts:",
                    *[f"- {item}" for item in cluster["known_facts"][:4]],
                    "",
                    "Missing evidence:",
                    *[f"- {item}" for item in cluster["missing_evidence"][:4]],
                    "",
                    "Suggested official sources:",
                    *[f"- {item}" for item in cluster["suggested_official_sources"][:4]],
                    "",
                    "Possible story angles:",
                    *[f"- {item}" for item in cluster["possible_story_angles"][:4]],
                    "",
                ]
            )
    lines.extend(
        [
            "## Generated Bundle Target",
            "",
            f"- {paths.ANNY_INPUT_BUNDLES_JSONL}",
            "- Run `make build-anny-input-bundles` to refresh the structured anny input bundles.",
            "",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


@app.callback(invoke_without_command=True)
def main(
    input_path: Annotated[
        Path,
        typer.Option("--input", help="Scored candidate JSONL input path."),
    ] = paths.JIBI_SCORED_CANDIDATES_JSONL,
    output: Annotated[
        Path,
        typer.Option("--output", help="Cluster/story seed JSONL output path."),
    ] = paths.JIBI_CANDIDATE_CLUSTERS_JSONL,
    report: Annotated[
        Path | None,
        typer.Option("--report", help="Markdown cluster report path."),
    ] = None,
    digest: Annotated[
        Path | None,
        typer.Option("--digest", help="Markdown cluster digest path."),
    ] = None,
    handoff: Annotated[
        Path,
        typer.Option("--handoff", help="Anny story seed handoff JSONL output path."),
    ] = paths.ANNY_STORY_SEED_HANDOFF_JSONL,
    handoff_digest: Annotated[
        Path | None,
        typer.Option("--handoff-digest", help="Markdown story seed handoff path."),
    ] = None,
    run_date: Annotated[
        str | None,
        typer.Option("--date", help="Output date stamp YYYY-MM-DD."),
    ] = None,
) -> None:
    clusters = cluster_candidates(
        input_path=input_path,
        output_path=output,
        report_path=report,
        digest_path=digest,
        handoff_path=handoff,
        handoff_digest_path=handoff_digest,
        run_date=run_date,
    )
    console.print(f"[green]Wrote {len(clusters)} jibi story seed clusters to {output}.[/green]")


if __name__ == "__main__":
    app()
