"""Review source hygiene and fact-check priorities for enriched anny dry runs."""

from __future__ import annotations

import json
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Any

import typer
from rich.console import Console

from luddite import paths
from luddite.utils.jsonl import write_jsonl
from luddite.utils.urls import canonicalize_url

app = typer.Typer(no_args_is_help=False)
console = Console()

DEFAULT_STORYLINE_PATH = (
    paths.ANNY_STORYLINE_DRY_RUN_DIR
    / "ai_knowledge_institution_gpt_pro_storyline_enriched.json"
)
DEFAULT_EVIDENCE_PACK_PATH = paths.ANNY_EVIDENCE_PACK_AI_KNOWLEDGE_JSON
DEFAULT_HYGIENE_JSONL = (
    paths.ANNY_STORYLINE_DRY_RUN_DIR
    / "ai_knowledge_institution_source_hygiene.jsonl"
)
DEFAULT_REPORT = paths.REPORTS_DIR / "anny_fact_check_review_ai_knowledge_institution.md"

ROLE_BY_PACK_CATEGORY = {
    "primary_article": "primary_article",
    "supporting_articles": "supporting_article",
    "research_or_survey": "research_or_survey",
    "counterpoints": "counterpoint",
    "institution_examples": "institution_example",
    "korea_bridge": "korea_bridge",
    "visual_candidates": "visual_context",
}


def _load_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as source:
        return json.load(source)


def _all_slides(storyline: dict[str, Any]) -> list[dict[str, Any]]:
    slides: list[dict[str, Any]] = []
    for section_index, section in enumerate(storyline.get("sections", []), start=1):
        for local_order, slide in enumerate(section.get("slides", []), start=1):
            copied = dict(slide)
            copied["_section_index"] = section_index
            copied["_section_title"] = section.get("section_title")
            copied["_local_order"] = slide.get("local_order") or local_order
            slides.append(copied)
    return slides


def build_source_role_map(evidence_pack: dict[str, Any]) -> dict[str, list[str]]:
    role_map: dict[str, list[str]] = {}
    for category, role in ROLE_BY_PACK_CATEGORY.items():
        values = evidence_pack.get(category)
        items = [values] if isinstance(values, dict) else list(values or [])
        for item in items:
            url = item.get("url")
            if not url:
                continue
            key = canonicalize_url(url)
            role_map.setdefault(key, [])
            if role not in role_map[key]:
                role_map[key].append(role)
            item_role = str(item.get("role") or "")
            if item_role == "counterpoint_article" and "counterpoint" not in role_map[key]:
                role_map[key].append("counterpoint")
            if item_role == "korea_bridge" and "korea_bridge" not in role_map[key]:
                role_map[key].append("korea_bridge")
    return role_map


def build_hygiene_records(
    storyline: dict[str, Any], evidence_pack: dict[str, Any]
) -> list[dict[str, Any]]:
    source_role_map = build_source_role_map(evidence_pack)
    records = []
    for index, slide in enumerate(_all_slides(storyline), start=1):
        priority, reason, required_broadcast = classify_fact_check(slide)
        fact_check_kind = classify_fact_check_kind(slide)
        required_storyline = requires_before_storyline(slide, fact_check_kind)
        source_refs = build_source_refs(slide, source_role_map)
        records.append(
            {
                "slide_no": slide.get("slide_no") or index,
                "local_order": slide.get("_local_order"),
                "section_title": slide.get("_section_title"),
                "headline": slide.get("headline"),
                "slide_type": slide.get("slide_type"),
                "needs_fact_check": bool(slide.get("needs_fact_check")),
                "needs_source": bool(slide.get("needs_source")),
                "fact_check_priority": priority,
                "fact_check_kind": fact_check_kind,
                "fact_check_reason": reason,
                "required_before_storyline": required_storyline,
                "required_before_broadcast": required_broadcast,
                "source_refs": source_refs,
                "source_roles": [
                    {"url": item["url"], "roles": [item["role"]]} for item in source_refs
                ],
            }
        )
    return records


def build_source_refs(
    slide: dict[str, Any], source_role_map: dict[str, list[str]]
) -> list[dict[str, Any]]:
    refs = []
    for url in slide.get("source_urls", []):
        key = canonicalize_url(url)
        roles = source_role_map.get(key) or [_fallback_source_role(url)]
        role = _slide_specific_role(slide, url, roles)
        refs.append(
            {
                "url": url,
                "role": role,
                "use": _source_use(slide, role),
                "confidence": _source_confidence(role, slide),
                "manual_check_required": _source_manual_check_required(slide, role),
            }
        )
    return refs


def label_source_roles(
    source_urls: list[str], source_role_map: dict[str, list[str]]
) -> list[dict[str, Any]]:
    slide = {"source_urls": source_urls, "headline": "", "notes": "", "body": []}
    return [
        {"url": item["url"], "roles": [item["role"]]}
        for item in build_source_refs(slide, source_role_map)
    ]


def _slide_specific_role(slide: dict[str, Any], url: str, roles: list[str]) -> str:
    text = _slide_text(slide)
    if "counterpoint" in roles and (
        "반대" in text or "접근성" in text or "personalized" in text or "맞춤형" in text
    ):
        return "counterpoint"
    if "primary_article" in roles and (
        "Royal Observatory" in text or "왕립천문대" in text or "BBC" in text
    ):
        return "primary_article"
    if "korea_bridge" in roles and (
        "한국" in text or "국내" in text or "정책브리핑" in text
    ):
        return "korea_bridge"
    if "research_or_survey" in roles and (
        "OECD" in text or "연구" in text or "교육 효과" in text
    ):
        return "research_or_survey"
    if "institution_example" in roles and (
        "기관" in text or "박물관" in text or "과학관" in text or "프레임워크" in text
    ):
        return "institution_example"
    if "checklist_reference" in roles:
        return "checklist_reference"
    return roles[0]


def _source_use(slide: dict[str, Any], role: str) -> str:
    text = _slide_text(slide)
    if role == "primary_article":
        return "Royal Observatory 발언 및 BBC 원문 맥락"
    if role == "counterpoint":
        return "AI가 접근성/개인화 학습을 높일 수 있다는 반대 관점"
    if role == "research_or_survey":
        return "AI 교육/정보탐색 관련 연구·조사 맥락"
    if role == "institution_example":
        return "학교·박물관·천문관·과학관 역할 변화 사례/프레임워크"
    if role == "korea_bridge":
        return "한국 정책·기관 사례를 후반 보조 연결로 사용"
    if "방송 전 꼭 채워야 할 자료" in text:
        return "production 전 확인할 source checklist"
    return "slide 주장 보조 근거"


def _source_confidence(role: str, slide: dict[str, Any]) -> str:
    if role in {"primary_article", "korea_bridge"}:
        return "medium" if slide.get("needs_fact_check") else "high"
    if role in {"research_or_survey", "counterpoint", "institution_example"}:
        return "medium"
    return "low"


def _source_manual_check_required(slide: dict[str, Any], role: str) -> bool:
    if role == "checklist_reference":
        return True
    return bool(slide.get("needs_fact_check"))


def _fallback_source_role(url: str) -> str:
    if "bbc.com" in url:
        return "primary_article"
    if "microsoft.com" in url:
        return "supporting_article"
    if "oecd.org" in url:
        return "research_or_survey"
    if "unesco.org" in url and "rights-learners" in url:
        return "counterpoint"
    if "unesco.org" in url:
        return "institution_example"
    if "korea.kr" in url or "sciencecenter.or.kr" in url:
        return "korea_bridge"
    if "science.go.kr" in url:
        return "institution_example"
    return "supporting_article"


def classify_fact_check(slide: dict[str, Any]) -> tuple[str, str, bool]:
    if not slide.get("needs_fact_check"):
        return "low", "fact-check marker 없음. 구조/전환용 slide로 취급.", False

    text = _slide_text(slide)
    high_markers = [
        "수치",
        "숫자",
        "통계",
        "정책",
        "발언",
        "원문",
        "교육 효과",
        "인지",
        "학습 저하",
        "AI 디지털교과서",
    ]
    medium_markers = [
        "역할",
        "기관",
        "박물관",
        "과학관",
        "천문관",
        "한국",
        "사례",
        "방향",
        "일반화",
    ]
    if any(marker in text for marker in high_markers):
        return (
            "high",
            "수치/정책/기관 발언/교육·인지 효과처럼 틀리면 위험한 주장.",
            True,
        )
    if any(marker in text for marker in medium_markers):
        return (
            "medium",
            "기관 역할 변화, AI 활용 방향성, 사례 일반화에 해당.",
            True,
        )
    return "medium", "근거는 붙었지만 방송 전 수동 확인이 필요한 해석.", True


def classify_fact_check_kind(slide: dict[str, Any]) -> str:
    text = _slide_text(slide)
    if "방송 전 꼭 채워야 할 자료" in text:
        return "production_checklist"
    if not slide.get("needs_fact_check"):
        if (
            "rhetorical_bridge" in text
            or "질문" in text
            or "비유" in text
            or slide.get("slide_type") in {"punchline", "closing_question", "bridge"}
        ):
            return "rhetorical_caution"
        return "source_context"
    if (
        "정책 효과" in text
        or "정책금융" in text
        or "국민성장펀드" in text
        or "금융위원회" in text
        or "정부 정책" in text
    ):
        return "policy_effect_claim"
    if (
        "투자" in text
        or "금융상품" in text
        or "수익률" in text
        or "주가" in text
    ):
        return "investment_risk_claim"
    if "Royal Observatory" in text or "왕립천문대" in text or "BBC" in text or "발언" in text:
        return "institution_quote_context"
    if "교육 효과" in text or "인지" in text or "학습" in text or "학교" in text:
        return "education_research_claim"
    if "한국" in text or "국내" in text or "정책브리핑" in text or "AI 디지털교과서" in text:
        return "korea_bridge_claim"
    if "기관" in text or "박물관" in text or "과학관" in text or "천문관" in text:
        return "source_context"
    return "factual_claim"


def requires_before_storyline(slide: dict[str, Any], fact_check_kind: str) -> bool:
    if slide.get("needs_source") and not slide.get("source_urls"):
        return True
    return fact_check_kind == "production_checklist"


def _slide_text(slide: dict[str, Any]) -> str:
    return "\n".join(
        [
            str(slide.get("headline") or ""),
            *[str(item) for item in slide.get("body", [])],
            str(slide.get("notes") or ""),
        ]
    )


def build_fact_check_review(
    *,
    storyline_path: Path = DEFAULT_STORYLINE_PATH,
    evidence_pack_path: Path = DEFAULT_EVIDENCE_PACK_PATH,
    hygiene_jsonl_path: Path = DEFAULT_HYGIENE_JSONL,
    report_path: Path = DEFAULT_REPORT,
    now: datetime | None = None,
) -> dict[str, Any]:
    storyline = _load_json(storyline_path)
    evidence_pack = _load_json(evidence_pack_path)
    records = build_hygiene_records(storyline, evidence_pack)
    write_jsonl(hygiene_jsonl_path, records)
    result = summarize_records(storyline, records)
    result["generated_at"] = (now or datetime.now(UTC)).isoformat()
    result["storyline_path"] = str(storyline_path)
    result["hygiene_jsonl_path"] = str(hygiene_jsonl_path)
    write_report(report_path, result, records)
    return result


def summarize_records(storyline: dict[str, Any], records: list[dict[str, Any]]) -> dict[str, Any]:
    priority_counts = Counter(record["fact_check_priority"] for record in records)
    role_counts: Counter[str] = Counter()
    for record in records:
        for source in record["source_refs"]:
            role_counts.update([source["role"]])
    needs_fact_check = [record for record in records if record["needs_fact_check"]]
    high_priority = [
        record for record in records if record["fact_check_priority"] == "high"
    ]
    required = [record for record in records if record["required_before_broadcast"]]
    required_storyline = [
        record for record in records if record["required_before_storyline"]
    ]
    kind_counts = Counter(record["fact_check_kind"] for record in records)
    return {
        "title": storyline.get("title"),
        "total_slides": len(records),
        "needs_fact_check_count": len(needs_fact_check),
        "fact_check_priority_distribution": dict(sorted(priority_counts.items())),
        "source_role_distribution": dict(sorted(role_counts.items())),
        "fact_check_kind_distribution": dict(sorted(kind_counts.items())),
        "high_priority_gap_count": len(high_priority),
        "required_before_storyline_count": len(required_storyline),
        "required_before_broadcast_count": len(required),
        "ready_for_prompt_design": True,
        "ready_for_production_agent": False,
        "ready_for_broadcast": False,
        "production_readiness_reason": (
            "structure and evidence mapping are good, but fact-check and evidence "
            "validation still require manual review"
        ),
    }


def write_report(
    path: Path, result: dict[str, Any], records: list[dict[str, Any]]
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    high_priority = [record for record in records if record["fact_check_priority"] == "high"]
    checklist = [
        record for record in records if record["fact_check_kind"] == "production_checklist"
    ]
    storyline_required = [
        record for record in records if record["required_before_storyline"]
    ]
    storyline_required_lines = [
        "- slide {slide_no}: {headline} ({kind})".format(
            slide_no=record["slide_no"],
            headline=record["headline"],
            kind=record["fact_check_kind"],
        )
        for record in storyline_required
    ] or ["- none"]
    required = [record for record in records if record["required_before_broadcast"]]
    safe = [record for record in records if not record["required_before_broadcast"]]
    lines = [
        "# Anny Fact-Check / Source Hygiene Review — AI Knowledge Institution",
        "",
        f"- generated_at: {result['generated_at']}",
        f"- storyline_path: {result['storyline_path']}",
        f"- hygiene_jsonl_path: {result['hygiene_jsonl_path']}",
        f"- total_slides: {result['total_slides']}",
        f"- needs_fact_check_count: {result['needs_fact_check_count']}",
        f"- required_before_storyline_count: {result['required_before_storyline_count']}",
        f"- required_before_broadcast_count: {result['required_before_broadcast_count']}",
        f"- ready_for_prompt_design: {result['ready_for_prompt_design']}",
        f"- ready_for_production_agent: {result['ready_for_production_agent']}",
        f"- ready_for_broadcast: {result['ready_for_broadcast']}",
        f"- production_readiness_reason: {result['production_readiness_reason']}",
        "",
        "## Fact-Check Priority Distribution",
        "",
        *[
            f"- {priority}: {count}"
            for priority, count in result["fact_check_priority_distribution"].items()
        ],
        "",
        "## Fact-Check Kind Distribution",
        "",
        *[
            f"- {kind}: {count}"
            for kind, count in result["fact_check_kind_distribution"].items()
        ],
        "",
        "## Source Role Distribution",
        "",
        *[
            f"- {role}: {count}"
            for role, count in result["source_role_distribution"].items()
        ],
        "",
        "## High Priority Gaps",
        "",
        *[
            "- slide {slide_no}: {headline} — {reason}".format(
                slide_no=record["slide_no"],
                headline=record["headline"],
                reason=record["fact_check_reason"],
            )
            for record in high_priority
        ],
        "",
        "## Production Checklist Slides",
        "",
        *[
            "- slide {slide_no}: {headline} — {reason}".format(
                slide_no=record["slide_no"],
                headline=record["headline"],
                reason=record["fact_check_reason"],
            )
            for record in checklist
        ],
        "",
        "## Required Before Storyline",
        "",
        *storyline_required_lines,
        "",
        "## Slides Requiring Manual Verification Before Broadcast",
        "",
        *[
            "- slide {slide_no}: {headline} ({priority})".format(
                slide_no=record["slide_no"],
                headline=record["headline"],
                priority=record["fact_check_priority"],
            )
            for record in required
        ],
        "",
        "## Slides Safe For Dry Run",
        "",
        *[
            "- slide {slide_no}: {headline}".format(
                slide_no=record["slide_no"], headline=record["headline"]
            )
            for record in safe
        ],
        "",
        "## Prompt Design Rules To Carry Forward",
        "",
        "- enriched evidence가 있어도 교육/인지 효과를 단정하지 말 것",
        "- source가 붙은 slide와 fact-check 완료 slide를 구분할 것",
        "- counterpoint를 반드시 포함할 것",
        "- korea_bridge는 보조 연결로 사용할 것",
        "- rhetorical slide에 과도한 source 요구를 하지 말 것",
        "- fact_check_priority와 fact_check_kind를 표시할 것",
        "- required_before_storyline과 required_before_broadcast를 분리할 것",
        "- source_refs는 slide-specific role/use/confidence/manual_check_required로 남길 것",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


@app.callback(invoke_without_command=True)
def main(
    storyline_path: Annotated[
        Path,
        typer.Option("--storyline", help="Enriched anny storyline JSON path."),
    ] = DEFAULT_STORYLINE_PATH,
    evidence_pack_path: Annotated[
        Path,
        typer.Option("--evidence-pack", help="Evidence pack JSON path."),
    ] = DEFAULT_EVIDENCE_PACK_PATH,
    hygiene_jsonl_path: Annotated[
        Path,
        typer.Option("--output-jsonl", help="Source hygiene sidecar JSONL path."),
    ] = DEFAULT_HYGIENE_JSONL,
    report_path: Annotated[
        Path,
        typer.Option("--report", help="Fact-check/source hygiene Markdown report path."),
    ] = DEFAULT_REPORT,
) -> None:
    result = build_fact_check_review(
        storyline_path=storyline_path,
        evidence_pack_path=evidence_pack_path,
        hygiene_jsonl_path=hygiene_jsonl_path,
        report_path=report_path,
    )
    console.print(
        "[green]Wrote anny fact-check/source hygiene review "
        f"({result['needs_fact_check_count']} fact-check slide(s)).[/green]"
    )


if __name__ == "__main__":
    app()
