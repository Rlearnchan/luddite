"""Build rule-based anny input bundles from jibi story seed handoff."""

from __future__ import annotations

import hashlib
from collections import Counter
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Annotated, Any

import typer
from rich.console import Console

from luddite import paths
from luddite.utils.jsonl import read_jsonl, write_jsonl
from luddite.utils.schemas import validate_with_schema

app = typer.Typer(no_args_is_help=False)
console = Console()

STRUCTURE_TEMPLATES = {
    "productive_finance_policy": [
        "담보·단기수익 중심 금융의 한계",
        "AI/반도체 투자와 장기 위험자본 필요",
        "국민성장펀드/정책금융 논쟁",
        "금융권은 어디까지 위험을 나눠질 수 있는가?",
    ],
    "industrial_policy_rnd": [
        "정부가 휴머노이드 R&D에 돈을 넣기 시작했다",
        "AI가 소프트웨어에서 로봇/제조로 확장된다",
        "한국형 휴머노이드가 필요한 산업 현장",
        "정부 R&D와 실제 양산 사이의 간극",
    ],
    "ai_knowledge_institution": [
        "AI가 즉답을 주는 시대",
        "편리함과 사고 과정의 생략",
        "학교/박물관/천문관의 역할 변화",
        "지식기관은 무엇을 가르쳐야 하는가?",
    ],
    "infrastructure_project_failure": [
        "HS2 실패의 표면적 원인",
        "대형 인프라의 비용 폭증과 정치 압력",
        "지역균형 논리와 사업성의 충돌",
        "한국 SOC와 비교 가능한 실패 패턴",
    ],
    "market_rate_stress": [
        "금리·환율·자산가격 스트레스의 현재 신호",
        "기업 자금조달과 AI 투자 비용으로 번지는 경로",
        "투자 조언이 아니라 거시 구조로 읽어야 하는 이유",
        "공식 통계와 반대 사례로 확인할 지점",
    ],
    "single_company_financing": [
        "단일 기업 자금조달 뉴스의 한계",
        "AI 반도체 공급망 투자라는 broader bridge",
        "증자·투자 수요와 주주/시장 리스크",
        "기업 홍보가 아니라 산업 자금조달 구조로 볼 수 있는가?",
    ],
    "climate_policy_conflict": [
        "기후 재난 대응의 현장 변화",
        "정책·이민·문화전쟁 프레임이 끼어드는 지점",
        "재난 관리와 정치 논쟁을 분리해 봐야 하는 이유",
        "공식 재난 통계와 지역 사례로 확인할 지점",
    ],
}

CORE_QUESTIONS = {
    "productive_finance_policy": (
        "금융은 안전하게 돈을 빌려주는 산업인가, 성장 위험을 나눠지는 산업인가?"
    ),
    "industrial_policy_rnd": "AI 산업정책은 소프트웨어를 넘어 로봇과 제조 현장을 어떻게 바꾸는가?",
    "ai_knowledge_institution": (
        "AI가 답을 즉시 주는 시대에 학교와 지식기관은 무엇을 가르쳐야 하는가?"
    ),
    "infrastructure_project_failure": (
        "대형 인프라 사업은 왜 정치 압력과 비용 폭증 앞에서 반복적으로 흔들리는가?"
    ),
    "market_rate_stress": (
        "금리와 자산가격 스트레스는 AI 투자와 기업 자금조달에 어떤 압력을 주는가?"
    ),
    "single_company_financing": "단일 기업 자금조달 뉴스가 AI 공급망 투자 구조로 확장될 수 있는가?",
    "climate_policy_conflict": "기후 재난 대응은 왜 이민·문화전쟁·정책 갈등과 충돌하는가?",
}

RISK_DO_NOT_CLAIM = {
    "investment_advice_risk": [
        "특정 자산/주식 매수·매도 의견처럼 쓰지 말 것",
        "가격 전망을 단정하지 말 것",
    ],
    "corporate_promo_risk": [
        "특정 기업 홍보처럼 쓰지 말 것",
        "기업의 성공을 단정하지 말 것",
    ],
    "political_sensitivity": [
        "특정 정당/정치인 호불호 평가처럼 쓰지 말 것",
        "국내 정치 프레임으로 단정하지 말 것",
    ],
}
VISUALIZABILITY_LEVELS = {"low", "medium", "high"}
LIKELY_PROOF_OBJECT_TYPES = {"diagram", "chart", "source_card"}
VISUAL_RISK_TYPES = {
    "too_abstract",
    "single_source",
    "needs_official_data",
    "policy_claim_risk",
    "market_claim_risk",
    "no_clear_visual",
}

CATEGORY_DO_NOT_CLAIM = {
    "productive_finance_policy": [
        "정책 효과를 단정하지 말 것",
        "특정 금융회사/정책상품 홍보처럼 쓰지 말 것",
        "투자 조언처럼 쓰지 말 것",
        "가격/수익률/주가 전망을 단정하지 말 것",
    ],
    "industrial_policy_rnd": [
        "정부 R&D가 상용화 성공을 보장한다고 쓰지 말 것",
        "특정 기업 수혜를 단정하지 말 것",
    ],
    "ai_knowledge_institution": [
        "교육 효과나 인지 저하를 단정하지 말 것",
        "AI 비판/찬양으로 단순화하지 말 것",
    ],
    "infrastructure_project_failure": [
        "영국 사례가 한국에 그대로 적용된다고 단정하지 말 것",
        "정치인 비판으로 흐르지 말 것",
    ],
    "market_rate_stress": [
        "금리/환율/자산가격 전망을 단정하지 말 것",
        "투자 조언처럼 쓰지 말 것",
    ],
    "single_company_financing": [
        "특정 기업 홍보처럼 쓰지 말 것",
        "증자/상장/주가 판단처럼 쓰지 말 것",
    ],
}


def build_anny_input_bundles(
    handoff_path: Path = paths.ANNY_STORY_SEED_HANDOFF_JSONL,
    candidates_path: Path = paths.JIBI_SCORED_CANDIDATES_JSONL,
    output_path: Path = paths.ANNY_INPUT_BUNDLES_JSONL,
    report_path: Path | None = None,
    run_date: str | None = None,
    now: datetime | None = None,
) -> list[dict[str, Any]]:
    date_text = run_date or date.today().isoformat()
    report_path = report_path or paths.REPORTS_DIR / f"anny_input_bundles_{date_text}.md"
    handoff_records = read_jsonl(handoff_path) if handoff_path.exists() else []
    candidates = read_jsonl(candidates_path) if candidates_path.exists() else []
    candidates_by_id = {str(item["candidate_id"]): item for item in candidates}
    timestamp = (now or datetime.now(UTC)).isoformat()

    bundles = [
        build_bundle(seed, candidates_by_id, created_at=timestamp)
        for seed in handoff_records
    ]
    for bundle in bundles:
        errors = validate_with_schema(bundle, "anny_input_bundle_schema.json")
        if errors:
            raise ValueError(f"{bundle['bundle_id']} schema errors: {'; '.join(errors)}")
    write_jsonl(output_path, bundles)
    write_bundle_report(report_path, bundles, output_path=output_path)
    return bundles


def build_bundle(
    seed: dict[str, Any],
    candidates_by_id: dict[str, dict[str, Any]],
    *,
    created_at: str,
) -> dict[str, Any]:
    category = str(seed.get("editorial_category") or seed.get("seed_type") or "other")
    candidate_articles = [
        _candidate_article(candidates_by_id[candidate_id])
        for candidate_id in seed.get("candidate_ids", [])
        if candidate_id in candidates_by_id
    ]
    risk_flags = sorted(
        {
            str(flag)
            for flag in [
                *seed.get("risk_flags", []),
                *(flag for item in candidate_articles for flag in item.get("risk_flags", [])),
                *_category_risk_flags(category, seed),
            ]
            if str(flag).strip()
        }
    )
    quality_flags = _quality_flags(seed)
    evidence_tasks = _evidence_tasks(seed, candidate_articles)
    missing_evidence = evidence_tasks["missing_evidence"]
    do_not_claim = _do_not_claim(
        category,
        risk_flags=risk_flags,
        missing_evidence=missing_evidence,
    )
    bundle_id = _bundle_id(str(seed["cluster_id"]))
    bundle = {
        "bundle_id": bundle_id,
        "story_seed_id": str(seed["cluster_id"]),
        "story_seed_title": str(seed["story_seed_title"]),
        "editorial_category": category,
        "seed_type": str(seed.get("seed_type") or category),
        "readiness": str(seed["readiness"]),
        "handoff_priority": str(seed["handoff_priority"]),
        "core_question": _core_question(category, seed),
        "why_story": str(seed["why_story"]),
        "known_facts": list(seed.get("known_facts", [])),
        "candidate_articles": candidate_articles,
        "missing_evidence": missing_evidence,
        "required_evidence": evidence_tasks["required_evidence"],
        "nice_to_have_evidence": evidence_tasks["nice_to_have_evidence"],
        "fact_check_tasks": evidence_tasks["fact_check_tasks"],
        "official_source_tasks": evidence_tasks["official_source_tasks"],
        "suggested_official_sources": list(seed.get("suggested_official_sources", [])),
        "possible_story_angles": list(seed.get("possible_story_angles", [])),
        "suggested_story_structure": _story_structure(category, seed),
        "opening_hook": _opening_hook(seed, candidate_articles),
        "audience_question": _audience_question(category, seed),
        "slide_count_target": _slide_count_target(seed),
        "tone_notes": _tone_notes(category, risk_flags),
        "must_include": _must_include(seed, candidate_articles),
        "avoid": _avoid(category, risk_flags, quality_flags),
        "risk_flags": risk_flags,
        "risk_level": str(seed.get("risk_level") or "low"),
        "quality_flags": quality_flags,
        "do_not_claim": do_not_claim,
        "needs_fact_check": _needs_fact_check(seed, missing_evidence, risk_flags),
        "llm_enrichment_needed": bool(seed.get("llm_enrichment_needed", True)),
        "created_at": created_at,
    }
    visual_planning_hint = _visual_planning_hint(seed)
    if visual_planning_hint:
        bundle["visual_planning_hint"] = visual_planning_hint
    return bundle


def _visual_planning_hint(seed: dict[str, Any]) -> dict[str, Any]:
    slideability = seed.get("slideability")
    slideability = slideability if isinstance(slideability, dict) else {}
    score = _bounded_score(slideability.get("score", seed.get("slideability_score", 0.0)))
    visualizability = str(slideability.get("visualizability") or "low")
    if visualizability not in VISUALIZABILITY_LEVELS:
        visualizability = "low"
    first_slide_idea = str(
        slideability.get("first_slide_idea") or seed.get("first_slide_idea") or ""
    ).strip()
    proof_types = _unique(
        item
        for item in [
            *slideability.get("likely_proof_object_types", []),
            *seed.get("likely_proof_object_types", []),
        ]
        if str(item) in LIKELY_PROOF_OBJECT_TYPES
    )
    visual_risks = _unique(
        item
        for item in [*slideability.get("risks", []), *seed.get("visual_risks", [])]
        if str(item) in VISUAL_RISK_TYPES
    )
    reason = str(slideability.get("reason") or "").strip()
    if not first_slide_idea and not proof_types and not visual_risks and score == 0.0:
        return {}
    return {
        "slideability_score": score,
        "visualizability": visualizability,
        "first_slide_idea": first_slide_idea,
        "likely_proof_object_types": proof_types,
        "visual_risks": visual_risks,
        "reason": reason,
        "planning_note": (
            "Jibi slideability is a planning hint only; it is not evidence and "
            "must not override source/fact-check guardrails."
        ),
    }


def _bounded_score(value: Any) -> float:
    try:
        score = float(value)
    except (TypeError, ValueError):
        return 0.0
    return round(max(0.0, min(1.0, score)), 2)


def _candidate_article(candidate: dict[str, Any]) -> dict[str, Any]:
    return {
        "candidate_id": str(candidate.get("candidate_id") or ""),
        "title": str(candidate.get("title") or ""),
        "url": candidate.get("seed_url") or candidate.get("source_url_canonical"),
        "source": candidate.get("source"),
        "source_id": candidate.get("source_id"),
        "published_at": candidate.get("published_at"),
        "summary": candidate.get("summary") or candidate.get("raw_summary"),
        "risk_flags": [str(flag) for flag in candidate.get("risk_flags", [])],
        "source_url_canonical": candidate.get("source_url_canonical"),
        "duplicate_key": candidate.get("duplicate_key"),
        "why_interesting": candidate.get("why_interesting"),
        "possible_expansions": [
            str(item) for item in candidate.get("possible_expansions", [])
        ],
        "evidence_needed": [
            _normalize_candidate_evidence_needed(str(item))
            for item in candidate.get("evidence_needed", [])
        ],
        "final_grade": candidate.get("final_grade"),
        "recommended_action": candidate.get("recommended_action"),
        "editorial_category": candidate.get("editorial_category"),
        "quality_flags": [str(flag) for flag in candidate.get("quality_flags", [])],
    }


def _normalize_candidate_evidence_needed(task: str) -> str:
    if task == "원문 기사 링크":
        return "원문 전문 확인"
    return task


def _bundle_id(story_seed_id: str) -> str:
    digest = hashlib.sha1(story_seed_id.encode("utf-8")).hexdigest()[:12]
    return f"anny_bundle_{digest}"


def _core_question(category: str, seed: dict[str, Any]) -> str:
    if category in CORE_QUESTIONS:
        return CORE_QUESTIONS[category]
    title = str(seed.get("story_seed_title") or "이 story seed")
    return f"{title}를 단일 사건이 아니라 구조적 이야기로 확장할 수 있는가?"


def _story_structure(category: str, seed: dict[str, Any]) -> list[str]:
    if category in STRUCTURE_TEMPLATES:
        return STRUCTURE_TEMPLATES[category]
    angles = [str(item) for item in seed.get("possible_story_angles", []) if str(item).strip()]
    if angles:
        return angles[:4]
    return [
        "표면 사건 또는 뉴스 hook",
        "배경 구조와 이해관계자",
        "한국 시청자에게 닿는 연결고리",
        "추가 근거로 확인해야 할 쟁점",
    ]


def _evidence_tasks(
    seed: dict[str, Any],
    candidate_articles: list[dict[str, Any]],
) -> dict[str, list[str]]:
    has_url = any(article.get("url") for article in candidate_articles)
    raw_tasks = [str(item) for item in seed.get("missing_evidence", [])]
    normalized = [_normalize_evidence_task(task, has_url=has_url) for task in raw_tasks]
    normalized = [task for task in normalized if task]
    if seed.get("official_evidence_needed"):
        normalized.append("공식 보도자료/세미나 자료 확인")
    required = _unique(
        task
        for task in normalized
        if any(marker in task for marker in ("원문", "공식", "숫자", "통계", "보조 기사"))
    )
    if not required:
        required = ["보조 기사 1개 이상", "공식 보도자료/세미나 자료 확인"]
    fact_check = _unique(
        [
            "원문 전문 확인",
            *[task for task in required if "숫자" in task or "통계" in task or "공식" in task],
            "반대 사례 또는 리스크 자료 확인",
        ]
    )
    official = _unique(
        [
            task for task in required if "공식" in task or "자료" in task or "원자료" in task
        ]
    )
    nice = _unique(
        [
            "배경 설명용 보조 기사 1개 이상",
            "한국 비교 사례 또는 과거 유사 사례",
        ]
    )
    missing = _unique([*required, *nice])
    return {
        "missing_evidence": missing,
        "required_evidence": required,
        "nice_to_have_evidence": nice,
        "fact_check_tasks": fact_check,
        "official_source_tasks": official,
    }


def _normalize_evidence_task(task: str, *, has_url: bool) -> str | None:
    if task == "원문 기사 링크":
        return None if has_url else "원문 기사 링크 확보"
    source_tasks = {
        "추가 독립 출처 1개 이상",
        "추가 독립 후보/출처 1개 이상",
        "다른 source의 보조 기사",
    }
    if task in source_tasks:
        return "보조 기사 1개 이상"
    if task in {"숫자/통계 또는 공식 자료", "공식 자료 또는 숫자/통계 확인"}:
        return "숫자/통계 원자료 확인"
    return task


def _quality_flags(seed: dict[str, Any]) -> list[str]:
    flags = [str(flag) for flag in seed.get("quality_flags", [])]
    if seed.get("editorial_category") == "single_company_financing":
        flags.append("loose_cluster_bridge")
    return _unique(flags)


def _category_risk_flags(category: str, seed: dict[str, Any]) -> list[str]:
    flags: list[str] = []
    if category == "productive_finance_policy":
        flags.extend(
            [
                "policy_effect_uncertainty",
                "investment_advice_risk",
                "single_source_dependency",
            ]
        )
        if seed.get("official_evidence_needed") or "official_evidence_missing" in seed.get(
            "quality_flags", []
        ):
            flags.append("official_evidence_missing")
    return flags


def _opening_hook(seed: dict[str, Any], candidate_articles: list[dict[str, Any]]) -> str:
    if candidate_articles:
        return str(candidate_articles[0].get("title") or seed.get("story_seed_title"))
    return str(seed.get("story_seed_title") or "")


def _audience_question(category: str, seed: dict[str, Any]) -> str:
    return _core_question(category, seed)


def _slide_count_target(seed: dict[str, Any]) -> str:
    if seed.get("handoff_priority") == "high":
        return "standard: 45-65 eventual slides; dry-run은 representative outline"
    return "short_or_standard: evidence 확인 후 25-65 slides"


def _tone_notes(category: str, risk_flags: list[str]) -> list[str]:
    notes = ["방송용 구조 설명 중심", "단일 기사 요약이 아니라 질문-근거-구조로 전환"]
    if category in {"market_rate_stress", "single_company_financing"}:
        notes.append("투자 코멘트가 아니라 구조/리스크 설명으로 유지")
    if "political_sensitivity" in risk_flags:
        notes.append("정치 호불호가 아니라 제도/경제 구조 중심")
    return notes


def _must_include(seed: dict[str, Any], candidate_articles: list[dict[str, Any]]) -> list[str]:
    items = [
        str(seed.get("core_question") or ""),
        *[str(item) for item in seed.get("known_facts", [])[:3]],
        *[str(item) for item in seed.get("suggested_official_sources", [])[:3]],
    ]
    if candidate_articles:
        items.append("후보 기사 URL과 source를 명시")
    return [item for item in _unique(items) if item]


def _avoid(category: str, risk_flags: list[str], quality_flags: list[str]) -> list[str]:
    items = [
        *CATEGORY_DO_NOT_CLAIM.get(category, []),
        *(claim for flag in risk_flags for claim in RISK_DO_NOT_CLAIM.get(flag, [])),
    ]
    if "loose_cluster_bridge" in quality_flags:
        items.append("서로 약하게 연결된 단일 기업 뉴스를 하나의 확정 서사로 묶지 말 것")
    return _unique(items)


def _do_not_claim(
    category: str,
    *,
    risk_flags: list[str],
    missing_evidence: list[str],
) -> list[str]:
    claims: list[str] = []
    claims.extend(CATEGORY_DO_NOT_CLAIM.get(category, []))
    for flag in risk_flags:
        claims.extend(RISK_DO_NOT_CLAIM.get(flag, []))
    if missing_evidence:
        claims.extend(
            [
                "현재 단일 기사 기반임을 잊지 말 것",
                "공식자료 확인 전 수치/정책효과를 단정하지 말 것",
            ]
        )
    return _unique(claims)


def _unique(items: Any) -> list[str]:
    return list(dict.fromkeys(str(item) for item in items if str(item).strip()))


def _needs_fact_check(
    seed: dict[str, Any],
    missing_evidence: list[str],
    risk_flags: list[str],
) -> bool:
    if seed.get("readiness") in {"needs_more_evidence", "editorial_review"}:
        return True
    return bool(missing_evidence or risk_flags)


def write_bundle_report(
    path: Path,
    bundles: list[dict[str, Any]],
    *,
    output_path: Path,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    readiness_counts = Counter(str(item["readiness"]) for item in bundles)
    priority_counts = Counter(str(item["handoff_priority"]) for item in bundles)
    lines = [
        "# Anny Input Bundle Report",
        "",
        "## Summary",
        "",
        f"- total bundles: {len(bundles)}",
        f"- output: {output_path}",
        "",
        "## By Readiness",
        "",
        *[f"- {key}: {count}" for key, count in readiness_counts.most_common()],
        "",
        "## By Handoff Priority",
        "",
        *[f"- {key}: {count}" for key, count in priority_counts.most_common()],
        "",
        "## High Priority Bundles",
        "",
    ]
    for bundle in [item for item in bundles if item["handoff_priority"] == "high"]:
        lines.extend(_bundle_lines(bundle))
    medium = [item for item in bundles if item["handoff_priority"] == "medium"]
    if medium:
        lines.extend(["## Medium Priority Bundles", ""])
        for bundle in medium:
            lines.extend(_bundle_lines(bundle))
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _bundle_lines(bundle: dict[str, Any]) -> list[str]:
    lines = [
        f"### {bundle['story_seed_title']}",
        "",
        f"- bundle_id: {bundle['bundle_id']}",
        f"- readiness: {bundle['readiness']}",
        f"- priority: {bundle['handoff_priority']}",
        f"- risk: {bundle['risk_level']} ({', '.join(bundle['risk_flags']) or '-'})",
        f"- needs_fact_check: {bundle['needs_fact_check']}",
        f"- core_question: {bundle['core_question']}",
        f"- opening_hook: {bundle['opening_hook']}",
        f"- audience_question: {bundle['audience_question']}",
        f"- slide_count_target: {bundle['slide_count_target']}",
        f"- Visual planning hint: {_visual_planning_label(bundle)}",
        f"- First slide idea: {_visual_first_slide_idea(bundle)}",
        f"- Visual risks: {_visual_risks(bundle)}",
        "",
        "Why story:",
        f"- {bundle['why_story']}",
        "",
        "Candidate articles:",
    ]
    for article in bundle["candidate_articles"]:
        lines.append(f"- {article['title']} ({article['source'] or 'unknown source'})")
    lines.extend(
        [
            "",
            "Required evidence:",
            *[f"- {item}" for item in bundle["required_evidence"][:5]],
            "",
            "Fact-check tasks:",
            *[f"- {item}" for item in bundle["fact_check_tasks"][:5]],
            "",
            "Suggested story structure:",
            *[
                f"- {index}. {item}"
                for index, item in enumerate(bundle["suggested_story_structure"], start=1)
            ],
            "",
            "Do not claim:",
            *[f"- {item}" for item in bundle["do_not_claim"]],
            "",
            "Must include:",
            *[f"- {item}" for item in bundle["must_include"][:5]],
            "",
            "Avoid:",
            *[f"- {item}" for item in bundle["avoid"][:5]],
            "",
            "Next action:",
            "- 근거를 보강한 뒤 anny storyline generation 입력으로 넘길지 판단",
            "",
        ]
    )
    return lines


def _visual_planning_label(bundle: dict[str, Any]) -> str:
    hint = bundle.get("visual_planning_hint")
    if not isinstance(hint, dict):
        return "-"
    proof_types = "+".join(str(item) for item in hint.get("likely_proof_object_types", []))
    proof_types = proof_types or "-"
    return f"{hint.get('visualizability', 'low')} / {proof_types}"


def _visual_first_slide_idea(bundle: dict[str, Any]) -> str:
    hint = bundle.get("visual_planning_hint")
    if not isinstance(hint, dict):
        return "-"
    return str(hint.get("first_slide_idea") or "-")


def _visual_risks(bundle: dict[str, Any]) -> str:
    hint = bundle.get("visual_planning_hint")
    if not isinstance(hint, dict):
        return "-"
    return ", ".join(str(item) for item in hint.get("visual_risks", [])) or "-"


@app.callback(invoke_without_command=True)
def main(
    handoff_path: Annotated[
        Path,
        typer.Option("--handoff", help="Anny story seed handoff JSONL input path."),
    ] = paths.ANNY_STORY_SEED_HANDOFF_JSONL,
    candidates_path: Annotated[
        Path,
        typer.Option("--candidates", help="Scored jibi candidates JSONL input path."),
    ] = paths.JIBI_SCORED_CANDIDATES_JSONL,
    output: Annotated[
        Path,
        typer.Option("--output", help="Anny input bundle JSONL output path."),
    ] = paths.ANNY_INPUT_BUNDLES_JSONL,
    report: Annotated[
        Path | None,
        typer.Option("--report", help="Markdown report path."),
    ] = None,
    run_date: Annotated[
        str | None,
        typer.Option("--date", help="Output date stamp YYYY-MM-DD."),
    ] = None,
) -> None:
    bundles = build_anny_input_bundles(
        handoff_path=handoff_path,
        candidates_path=candidates_path,
        output_path=output,
        report_path=report,
        run_date=run_date,
    )
    console.print(f"[green]Wrote {len(bundles)} anny input bundles to {output}.[/green]")


if __name__ == "__main__":
    app()
