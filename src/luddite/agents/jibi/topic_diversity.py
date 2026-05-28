"""Topic family inference and diversity adjustments for Jibi board selection."""

from __future__ import annotations

import re
from collections import Counter
from typing import Any

SPORTS_PRIMARY_TERMS = {
    "스포츠",
    "축구",
    "야구",
    "농구",
    "football",
    "premier league",
    "manchester united",
    "fifa",
    "f1",
    "formula 1",
    "formula one",
    "포뮬러",
    "모터스포츠",
    "월드컵",
    "올림픽",
    "챔피언스리그",
    "epl",
}

TOPIC_FAMILY_TERMS = {
    "ai_tech": {
        "ai",
        "인공지능",
        "챗봇",
        "대화형ai",
        "대화형 ai",
        "데이터센터",
        "datacentre",
        "datacenter",
        "automation",
        "업무자동화",
    },
    "macro_economy": {
        "경제성장",
        "성장률",
        "물가",
        "금리",
        "환율",
        "수출",
        "gdp",
        "inflation",
        "한국은행",
        "bok",
    },
    "markets_finance": {
        "주가",
        "증시",
        "ipo",
        "상장",
        "채권",
        "은행",
        "금융",
        "pf",
        "투자",
        "market",
        "shares",
        "stocks",
    },
    "policy_government": {
        "정부",
        "정책",
        "장관",
        "규제",
        "지원",
        "공공",
        "공무원",
        "회의",
        "보도자료",
        "수행기관",
    },
    "global_conflict": {
        "war",
        "전쟁",
        "iran",
        "middle east",
        "ukraine",
        "tariff",
        "관세",
        "중동",
    },
    "energy_climate": {
        "energy",
        "electricity",
        "전기요금",
        "전력",
        "가스",
        "폭염",
        "냉방",
        "heatwave",
        "climate",
        "emissions",
        "탄소",
    },
    "labor_work": {
        "노동",
        "고용",
        "청년",
        "임금",
        "직원",
        "성과급",
        "workplace",
        "worker",
        "staff",
        "jobs",
        "bonus",
    },
    "consumer_life": {
        "가격",
        "요금",
        "생활비",
        "소비",
        "쇼핑",
        "배달",
        "구독",
        "소음",
        "스마트폰",
        "household",
        "lawnmower",
        "subscription",
    },
    "industry_supply_chain": {
        "반도체",
        "메모리",
        "공급",
        "수급",
        "산업",
        "수출",
        "배터리",
        "공장",
        "chip",
        "memory",
        "supply",
        "factory",
    },
    "culture_media": {
        "콘텐츠",
        "영상",
        "음악",
        "브이로그",
        "저작권",
        "media",
        "spotify",
        "vlog",
        "copyright",
    },
    "sports_entertainment": SPORTS_PRIMARY_TERMS,
    "odd_hook": {
        "양파",
        "소음",
        "잔디깎이",
        "lawnmower",
        "odd",
    },
}

TOPIC_PRIMARY_PRIORITY = [
    "energy_climate",
    "industry_supply_chain",
    "labor_work",
    "consumer_life",
    "policy_government",
    "macro_economy",
    "markets_finance",
    "global_conflict",
    "culture_media",
    "sports_entertainment",
    "odd_hook",
    "ai_tech",
]

TOPIC_DIVERSITY_RANK_PENALTIES = {
    3: -8,
    4: -18,
    5: -30,
}

TOPIC_DIVERSITY_CONSTRAINED_FAMILIES = {"ai_tech"}


def topic_term_in_text(term: str, text: str) -> bool:
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


def infer_topic_profile(
    record: dict[str, Any],
    representative: dict[str, Any],
) -> dict[str, Any]:
    text = " ".join(
        [
            str(representative.get("title") or ""),
            str(representative.get("summary") or ""),
            str(representative.get("why_interesting") or ""),
            " ".join(str(item) for item in representative.get("possible_expansions") or []),
            str(record.get("bundle_title") or ""),
            str(record.get("why_bundle") or ""),
            str(record.get("story_fingerprint") or ""),
            str(representative.get("seed_type") or ""),
            str(representative.get("source_role_class") or ""),
        ]
    ).lower()
    signals_by_family: dict[str, list[str]] = {}
    for family, terms in TOPIC_FAMILY_TERMS.items():
        matches = [
            str(term)
            for term in sorted(terms)
            if topic_term_in_text(str(term), text)
        ]
        if matches:
            signals_by_family[family] = matches[:5]
    families = sorted(signals_by_family)
    if not families:
        families = ["other"]
        signals_by_family["other"] = []
    primary = _primary_topic_family(families, text)
    signal_count = sum(len(items) for items in signals_by_family.values())
    confidence = "low"
    if signal_count >= 4 or len(families) >= 3:
        confidence = "high"
    elif signal_count >= 2 or families != ["other"]:
        confidence = "medium"
    return {
        "topic_families": families,
        "primary_topic_family": primary,
        "topic_confidence": confidence,
        "topic_signals": signals_by_family,
    }


def _primary_topic_family(families: list[str], text: str) -> str:
    family_set = set(families)
    if "energy_climate" in family_set and any(
        term in text
        for term in (
            "전기요금",
            "전력",
            "energy",
            "electricity",
            "heatwave",
            "폭염",
            "냉방",
            "emissions",
            "탄소",
        )
    ):
        return "energy_climate"
    if "industry_supply_chain" in family_set and any(
        term in text
        for term in (
            "반도체",
            "메모리",
            "수급",
            "수출",
            "스마트폰",
            "chip",
            "memory",
            "supply",
        )
    ):
        return "industry_supply_chain"
    if "consumer_life" in family_set and any(
        term in text
        for term in ("생활비", "구독", "쇼핑", "배달", "소음", "household", "subscription")
    ):
        return "consumer_life"
    for family in TOPIC_PRIMARY_PRIORITY:
        if family in family_set:
            return family
    return families[0] if families else "other"


def _topic_rank_penalty(rank: int, *, softened: bool) -> int:
    if rank <= 2:
        return 0
    if rank >= 5:
        penalty = TOPIC_DIVERSITY_RANK_PENALTIES[5]
    else:
        penalty = TOPIC_DIVERSITY_RANK_PENALTIES.get(rank, 0)
    if softened and penalty < 0:
        return int(round(penalty / 2))
    return penalty


def apply_topic_diversity_adjustments(
    scored_records: list[tuple[dict[str, Any], dict[str, Any]]],
    score_rows: list[dict[str, Any]],
    *,
    use_topic_diversity: bool,
) -> None:
    """Mutate board scores with report-only rank fields and opt-in penalties."""

    row_by_id = {str(row.get("story_bundle_id") or ""): row for row in score_rows}
    ranked_by_family: dict[str, list[tuple[str, dict[str, Any]]]] = {}
    for record, board_score in scored_records:
        record_id = str(record.get("story_bundle_id") or "")
        for family in board_score.get("topic_families") or ["other"]:
            ranked_by_family.setdefault(str(family), []).append((record_id, board_score))
    family_ranks: dict[str, dict[str, int]] = {}
    for family, items in ranked_by_family.items():
        sorted_items = sorted(
            items,
            key=lambda item: float(item[1].get("board_score") or 0),
            reverse=True,
        )
        family_ranks[family] = {
            record_id: index
            for index, (record_id, _board_score) in enumerate(sorted_items, start=1)
        }

    for record, board_score in scored_records:
        record_id = str(record.get("story_bundle_id") or "")
        families = [str(item) for item in board_score.get("topic_families") or ["other"]]
        primary = str(board_score.get("primary_topic_family") or "other")
        rank_by_family = {
            family: family_ranks.get(family, {}).get(record_id, 0)
            for family in families
        }
        penalty_candidates: list[tuple[int, str, int, bool]] = []
        for family, rank in rank_by_family.items():
            if not rank or family not in TOPIC_DIVERSITY_CONSTRAINED_FAMILIES:
                continue
            softened = False
            penalty = _topic_rank_penalty(rank, softened=softened)
            if penalty:
                penalty_candidates.append((penalty, family, rank, softened))
        penalty, family, rank, softened = min(
            penalty_candidates,
            default=(0, "", 0, False),
            key=lambda item: item[0],
        )
        base_score = float(board_score.get("board_score") or 0)
        board_score["board_score_before_topic_diversity"] = round(base_score, 1)
        board_score["topic_diversity_rank_by_family"] = rank_by_family
        board_score["topic_diversity_potential_penalty"] = penalty
        board_score["topic_diversity_penalty"] = penalty if use_topic_diversity else 0
        if penalty:
            reason = f"{penalty} topic_diversity_{family}_rank_{rank}"
            if softened:
                reason += "_softened_cross_family"
            board_score["topic_diversity_reason"] = reason
            if use_topic_diversity:
                board_score["board_score"] = round(max(0.0, base_score + penalty), 1)
                board_score.setdefault("reasons", []).append(reason)
        else:
            board_score["topic_diversity_reason"] = ""
        row = row_by_id.get(record_id)
        if row is None:
            continue
        row["board_score"] = board_score.get("board_score", 0)
        row["board_score_before_topic_diversity"] = board_score.get(
            "board_score_before_topic_diversity",
            0,
        )
        row["board_score_reasons"] = board_score.get("reasons", [])
        row["topic_families"] = families
        row["primary_topic_family"] = primary
        row["topic_confidence"] = board_score.get("topic_confidence", "")
        row["topic_signals"] = board_score.get("topic_signals", {})
        row["topic_diversity_rank_by_family"] = rank_by_family
        row["topic_diversity_potential_penalty"] = board_score.get(
            "topic_diversity_potential_penalty",
            0,
        )
        row["topic_diversity_penalty"] = board_score.get("topic_diversity_penalty", 0)
        row["topic_diversity_reason"] = board_score.get("topic_diversity_reason", "")


def topic_family_counts(rows: list[dict[str, Any]]) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for row in rows:
        for family in row.get("topic_families") or ["other"]:
            counts[str(family)] += 1
    return dict(sorted(counts.items(), key=lambda item: (-item[1], item[0])))


def primary_topic_counts(rows: list[dict[str, Any]]) -> dict[str, int]:
    counts = Counter(str(row.get("primary_topic_family") or "other") for row in rows)
    return dict(sorted(counts.items(), key=lambda item: (-item[1], item[0])))


def topic_diversity_warnings(rows: list[dict[str, Any]]) -> list[str]:
    if not rows:
        return []
    warnings: list[str] = []
    total = len(rows)
    for family, count in topic_family_counts(rows).items():
        share = count / total
        if count >= 4 or share >= 0.4:
            warnings.append(f"topic_overconcentration:{family}={count}/{total}")
    for family, count in primary_topic_counts(rows).items():
        if count >= 4:
            warnings.append(f"primary_topic_overconcentration:{family}={count}/{total}")
    return warnings


def topic_diversity_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "title": str(row.get("title") or ""),
            "board_score": row.get("board_score", 0),
            "board_score_before_topic_diversity": row.get(
                "board_score_before_topic_diversity",
                row.get("board_score", 0),
            ),
            "topic_families": row.get("topic_families") or [],
            "primary_topic_family": row.get("primary_topic_family") or "other",
            "topic_diversity_potential_penalty": row.get(
                "topic_diversity_potential_penalty",
                0,
            ),
            "topic_diversity_penalty": row.get("topic_diversity_penalty", 0),
            "topic_diversity_reason": row.get("topic_diversity_reason", ""),
        }
        for row in rows
    ]
