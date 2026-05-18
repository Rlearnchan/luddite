"""Plan evidence enrichment for anny manual dry-run storylines."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Any

import typer
from rich.console import Console

from luddite import paths
from luddite.utils.schemas import validate_with_schema

app = typer.Typer(no_args_is_help=False)
console = Console()

TOPIC_SLUG = "ai_knowledge_institution"
DEFAULT_BUNDLE_PATH = (
    paths.ANNY_STORYLINE_DRY_RUN_DIR / "ai_knowledge_institution_input_bundle.json"
)
DEFAULT_STORYLINE_PATH = (
    paths.ANNY_STORYLINE_DRY_RUN_DIR / "ai_knowledge_institution_gpt_pro_storyline.json"
)
DEFAULT_EVIDENCE_PACK_PATH = paths.ANNY_EVIDENCE_PACK_AI_KNOWLEDGE_JSON
DEFAULT_NEEDS_REPORT = paths.REPORTS_DIR / "anny_evidence_needs_ai_knowledge_institution.md"
DEFAULT_PLAN_REPORT = (
    paths.REPORTS_DIR / "anny_evidence_enrichment_plan_ai_knowledge_institution.md"
)


def _load_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as source:
        return json.load(source)


def build_evidence_pack(bundle: dict[str, Any], *, created_at: str) -> dict[str, Any]:
    candidate_articles = bundle.get("candidate_articles", [])
    primary = candidate_articles[0] if candidate_articles else {}
    return {
        "pack_id": f"evidence_pack_{TOPIC_SLUG}",
        "story_seed_title": str(bundle.get("story_seed_title") or "AI 즉답 시대의 지식기관 역할"),
        "topic_slug": TOPIC_SLUG,
        "primary_article": _evidence_item(
            title=str(primary.get("title") or "BBC / Royal Observatory 원문 전문 확인"),
            url=primary.get("url"),
            source=str(primary.get("source") or "BBC News"),
            source_type="primary_article",
            summary=str(primary.get("summary") or "Royal Observatory 관계자 발언 맥락 확인"),
            role="primary_seed",
            reliability="medium",
            needs_manual_check=False,
        ),
        "supporting_articles": [
            _evidence_item(
                title="From Searchable to Non-Searchable: Generative AI and Information Diversity",
                url=(
                    "https://www.microsoft.com/en-us/research/publication/"
                    "from-searchable-to-non-searchable-generative-ai-and-information-diversity"
                    "-in-online-information-seeking/"
                ),
                source="Microsoft Research",
                source_type="research_summary",
                summary=(
                    "Generative-AI-mediated inquiry may reshape the diversity of knowledge "
                    "encountered in online information seeking."
                ),
                role="supporting_article",
                reliability="high",
                needs_manual_check=False,
            ),
            _evidence_item(
                title="AI and education: Protecting the rights of learners",
                url="https://www.unesco.org/en/articles/ai-and-education-protecting-rights-learners",
                source="UNESCO",
                source_type="policy_brief",
                summary=(
                    "UNESCO frames AI in education as both a rights/safety issue and a source "
                    "of opportunities such as access and personalized learning."
                ),
                role="counterpoint_article",
                reliability="high",
                needs_manual_check=False,
            ),
        ],
        "expert_quotes": [
            _placeholder_item(
                "교육/인지/정보탐색 전문가 quote",
                "expert_quote",
                "전문가 인터뷰 또는 연구자 발언",
            )
        ],
        "institution_examples": [
            _evidence_item(
                title="AI Competency Framework for Students",
                url="https://www.unesco.org/en/articles/ai-competency-framework-students",
                source="UNESCO",
                source_type="framework",
                summary=(
                    "Framework for integrating AI learning objectives into school curricula "
                    "and preparing students as responsible, creative AI users."
                ),
                role="institution_example",
                reliability="high",
                needs_manual_check=False,
            ),
            _evidence_item(
                title="National Science Museum Future Tech exhibition: Artificial Intelligence",
                url="https://www.science.go.kr/eps/cntnts/772/moveCntnts.do",
                source="National Science Museum, Republic of Korea",
                source_type="institution_page",
                summary=(
                    "Korean science museum exhibition page describing AI-centered future-life "
                    "experiences such as smart city, home, mobility, and factory scenarios."
                ),
                role="institution_example",
                reliability="high",
                needs_manual_check=False,
            ),
        ],
        "research_or_survey": [
            _evidence_item(
                title="OECD Digital Education Outlook 2026",
                url="https://www.oecd.org/en/publications/oecd-digital-education-outlook-2026_062a7394-en.html",
                source="OECD",
                source_type="research_report",
                summary=(
                    "Synthesizes evidence on GenAI as tutor, partner, and assistant, while "
                    "noting that benefits depend on clear teaching principles."
                ),
                role="research_or_survey",
                reliability="high",
                needs_manual_check=False,
            )
        ],
        "counterpoints": [
            _evidence_item(
                title="AI and education: Protecting the rights of learners",
                url="https://www.unesco.org/en/articles/ai-and-education-protecting-rights-learners",
                source="UNESCO",
                source_type="policy_brief",
                summary=(
                    "Counterpoint source for AI's potential to increase access to education "
                    "and personalized learning when rights and safeguards are respected."
                ),
                role="counterpoint",
                reliability="high",
                needs_manual_check=False,
            )
        ],
        "korea_bridge": [
            _evidence_item(
                title="2025년부터 학교현장에 AI 디지털교과서 도입",
                url="https://www.korea.kr/news/policyNewsView.do?newsId=148912089",
                source="대한민국 정책브리핑",
                source_type="official_policy",
                summary=(
                    "Korea policy item on introducing AI digital textbooks in schools from 2025."
                ),
                role="korea_bridge",
                reliability="high",
                needs_manual_check=False,
            ),
            _evidence_item(
                title="국립광주과학관 인공지능관",
                url="https://www.sciencecenter.or.kr/kor/menu/sub.do?menuId=17_275",
                source="국립광주과학관",
                source_type="institution_page",
                summary="AI 체험·전시 공간을 소개하는 국내 과학관 공식 페이지.",
                role="korea_bridge",
                reliability="high",
                needs_manual_check=False,
            ),
        ],
        "visual_candidates": [
            _placeholder_item("AI 검색창 vs 기존 검색 결과", "visual_candidate", "직접 제작/캡처"),
            _placeholder_item(
                "천문관/박물관/과학관 이미지",
                "visual_candidate",
                "기관/공개 이미지",
            ),
            _placeholder_item("학생과 AI 학습 도구", "visual_candidate", "공개 이미지/연출 이미지"),
            _placeholder_item("질문-답변 구조 도식", "visual_candidate", "직접 제작"),
        ],
        "manual_research_checklist": [
            "BBC / Royal Observatory 원문 전문 확인",
            "Royal Observatory 관계자 발언 맥락 확인",
            "AI 즉답/검색 사용이 학습 습관에 미치는 영향 관련 보조 자료 확인",
            "학교/박물관/천문관/과학관의 AI 활용 또는 AI 리터러시 사례 확인",
            "AI가 학습 접근성을 높인다는 반대 관점 확인",
            "국내 학교 AI 교육 정책 확인",
            "국내 과학관/박물관 AI 교육/전시 사례 확인",
        ],
        "created_at": created_at,
    }


def _evidence_item(
    *,
    title: str,
    url: str | None,
    source: str,
    source_type: str,
    summary: str,
    role: str,
    reliability: str,
    needs_manual_check: bool = True,
) -> dict[str, Any]:
    return {
        "title": title,
        "url": url,
        "source": source,
        "source_type": source_type,
        "summary": summary,
        "role": role,
        "reliability": reliability,
        "needs_manual_check": needs_manual_check,
    }


def _placeholder_item(title: str, role: str, source: str) -> dict[str, Any]:
    return _evidence_item(
        title=title,
        url=None,
        source=source,
        source_type="manual_research_needed",
        summary="아직 자동 수집하지 않음. 1.5.2 enriched dry run 전 사람이 확인할 evidence task.",
        role=role,
        reliability="unknown",
    )


def collect_slide_needs(storyline: dict[str, Any]) -> list[dict[str, Any]]:
    needs: list[dict[str, Any]] = []
    global_order = 0
    for section in storyline.get("sections", []):
        for local_order, slide in enumerate(section.get("slides", []), start=1):
            global_order += 1
            if not (slide.get("needs_fact_check") or slide.get("needs_source")):
                continue
            evidence_type, suggested_source_type = _classify_slide_need(slide)
            source_priority = _source_priority(evidence_type, slide)
            needs.append(
                {
                    "slide_no": slide.get("slide_no") or global_order,
                    "local_order": slide.get("local_order") or local_order,
                    "section_title": section.get("section_title"),
                    "headline": slide.get("headline"),
                    "needs_source": bool(slide.get("needs_source")),
                    "needs_fact_check": bool(slide.get("needs_fact_check")),
                    "reason": slide.get("notes") or "",
                    "evidence_type": evidence_type,
                    "suggested_source_type": suggested_source_type,
                    "priority": _priority(slide),
                    "source_priority": source_priority,
                }
            )
    return needs


def _classify_slide_need(slide: dict[str, Any]) -> tuple[str, str]:
    text = f"{slide.get('headline', '')}\n{slide.get('notes', '')}"
    if _is_rhetorical_bridge(text):
        return "rhetorical_bridge", "방송용 브릿지/질문, 별도 출처 강요하지 않음"
    if (
        "Royal Observatory" in text
        or "왕립천문대" in text
        or "BBC" in text
        or "천문대" in text
    ):
        return "primary_article_context", "BBC 원문 / Royal Observatory 공식 맥락"
    if "천문학" in text or "천문관" in text:
        return "institution_example", "Royal Observatory / 천문관 / 과학관 교육 맥락"
    if "박물관" in text or "과학관" in text:
        return "institution_example", "박물관/천문관/과학관 공식 사례"
    if "한국" in text:
        return "korea_bridge", "국내 정책/기관 사례"
    if "이미지" in text:
        return "visual_candidate", "이미지/도식 후보"
    if "학교" in text or "교육" in text or "학습" in text:
        return "education_research_or_policy", "교육부/학교/교육 연구"
    return "supporting_article", "보조 기사 또는 전문가 자료"


def _is_rhetorical_bridge(text: str) -> bool:
    rhetorical_markers = [
        "그러면 이제 공부는 무엇이 되는가",
        "검색왕의 시대에서 질문왕의 시대로",
        "AI 시대의 공부는 정답을 맞히는 일이 아니라",
        "AI가 답을 해주면, 사람은 질문을 해야 한다",
        "무엇을 가르쳐야 하는가",
        "정답을 맞히는 일이 아니라",
        "질문왕",
    ]
    return any(marker in text for marker in rhetorical_markers)


def _priority(slide: dict[str, Any]) -> str:
    if slide.get("needs_fact_check") and slide.get("needs_source"):
        return "high"
    if slide.get("needs_fact_check"):
        return "medium"
    return "low"


def _source_priority(evidence_type: str, slide: dict[str, Any]) -> str:
    if evidence_type == "rhetorical_bridge":
        return "low"
    if evidence_type == "visual_candidate":
        return "medium"
    return _priority(slide)


def apply_evidence_coverage(
    slide_needs: list[dict[str, Any]], pack: dict[str, Any]
) -> list[dict[str, Any]]:
    for item in slide_needs:
        status, ref, remaining_gap = _evidence_coverage_for_need(item["evidence_type"], pack)
        item["evidence_status"] = status
        item["evidence_ref"] = ref
        item["remaining_gap"] = remaining_gap
    return slide_needs


def _evidence_coverage_for_need(
    evidence_type: str, pack: dict[str, Any]
) -> tuple[str, str, str]:
    if evidence_type == "rhetorical_bridge":
        return "covered", "rhetorical_bridge", "별도 출처를 강제하지 않는 전개용 질문/브릿지."

    category = _coverage_category(evidence_type)
    evidence = _first_real_evidence(pack, category)
    if evidence:
        status = "partial" if evidence.get("needs_manual_check") else "covered"
        remaining_gap = (
            "원문 맥락 수동 확인 필요."
            if evidence.get("needs_manual_check")
            else "현재 evidence pack으로 1차 커버."
        )
        return status, _evidence_ref(category, evidence), remaining_gap

    if evidence_type == "visual_candidate":
        return (
            "partial",
            "visual_candidate:직접 제작/캡처 후보",
            "실제 이미지 URL 또는 제작 asset 필요.",
        )
    return "missing", "", "실제 URL이 있는 evidence item 필요."


def _coverage_category(evidence_type: str) -> str:
    return {
        "primary_article_context": "primary_article",
        "supporting_article": "supporting_articles",
        "education_research_or_policy": "research_or_survey",
        "institution_example": "institution_examples",
        "korea_bridge": "korea_bridge",
        "visual_candidate": "visual_candidates",
    }.get(evidence_type, "supporting_articles")


def _first_real_evidence(pack: dict[str, Any], category: str) -> dict[str, Any] | None:
    values = pack.get(category)
    items = [values] if isinstance(values, dict) else list(values or [])
    for item in items:
        if item.get("url") and item.get("reliability") != "unknown":
            return item
    return None


def _evidence_ref(category: str, evidence: dict[str, Any]) -> str:
    return f"{category}:{evidence.get('source')} — {evidence.get('title')}"


def _real_evidence_count(pack: dict[str, Any]) -> int:
    count = 0
    for category in [
        "primary_article",
        "supporting_articles",
        "expert_quotes",
        "institution_examples",
        "research_or_survey",
        "counterpoints",
        "korea_bridge",
        "visual_candidates",
    ]:
        values = pack.get(category)
        items = [values] if isinstance(values, dict) else list(values or [])
        count += sum(
            1
            for item in items
            if item.get("url")
            and item.get("reliability") != "unknown"
            and not item.get("needs_manual_check")
        )
    return count


def _readiness_summary(pack: dict[str, Any], slide_needs: list[dict[str, Any]]) -> dict[str, Any]:
    primary_covered = bool(_first_real_evidence(pack, "primary_article"))
    supporting_count = len(_real_items(pack, "supporting_articles"))
    research_count = len(_real_items(pack, "research_or_survey"))
    counterpoint_count = len(_real_items(pack, "counterpoints"))
    institution_count = len(_real_items(pack, "institution_examples"))
    korea_count = len(_real_items(pack, "korea_bridge"))
    must_have_missing = [
        item
        for item in slide_needs
        if item["source_priority"] in {"high", "medium"}
        and item.get("evidence_status") == "missing"
        and item["evidence_type"] != "visual_candidate"
    ]
    ready = (
        primary_covered
        and (supporting_count >= 2 or supporting_count + research_count >= 2)
        and counterpoint_count >= 1
        and institution_count >= 1
        and not must_have_missing
    )
    return {
        "primary_article_covered": primary_covered,
        "supporting_articles_count": supporting_count,
        "research_or_survey_count": research_count,
        "counterpoint_count": counterpoint_count,
        "institution_example_count": institution_count,
        "korea_bridge_count": korea_count,
        "remaining_must_have_gaps": must_have_missing,
        "ready_for_enriched_dry_run": ready,
    }


def _real_items(pack: dict[str, Any], category: str) -> list[dict[str, Any]]:
    values = pack.get(category)
    items = [values] if isinstance(values, dict) else list(values or [])
    return [
        item
        for item in items
        if item.get("url")
        and item.get("reliability") != "unknown"
        and not item.get("needs_manual_check")
    ]


def build_evidence_enrichment_plan(
    *,
    bundle_path: Path = DEFAULT_BUNDLE_PATH,
    storyline_path: Path = DEFAULT_STORYLINE_PATH,
    evidence_pack_path: Path = DEFAULT_EVIDENCE_PACK_PATH,
    needs_report_path: Path = DEFAULT_NEEDS_REPORT,
    plan_report_path: Path = DEFAULT_PLAN_REPORT,
    now: datetime | None = None,
) -> dict[str, Any]:
    bundle = _load_json(bundle_path)
    storyline = _load_json(storyline_path)
    created_at = (now or datetime.now(UTC)).isoformat()
    pack = build_evidence_pack(bundle, created_at=created_at)
    errors = validate_with_schema(pack, "evidence_pack_schema.json")
    if errors:
        raise ValueError(f"evidence pack schema errors: {'; '.join(errors)}")
    slide_needs = apply_evidence_coverage(collect_slide_needs(storyline), pack)
    evidence_pack_path.parent.mkdir(parents=True, exist_ok=True)
    evidence_pack_path.write_text(
        json.dumps(pack, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    write_needs_report(needs_report_path, slide_needs)
    write_plan_report(plan_report_path, bundle, storyline, pack, slide_needs)
    return {
        "evidence_pack_path": str(evidence_pack_path),
        "needs_report_path": str(needs_report_path),
        "plan_report_path": str(plan_report_path),
        "slide_needs_count": len(slide_needs),
    }


def write_needs_report(path: Path, slide_needs: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Anny Evidence Needs — AI Knowledge Institution",
        "",
        (
            "| Slide | Local | Headline | Needs | Evidence Type | Source Type | Priority | "
            "Source Priority | Evidence Status | Evidence Ref | Remaining Gap |"
        ),
        "|---:|---:|---|---|---|---|---|---|---|---|---|",
    ]
    for item in slide_needs:
        needs = []
        if item["needs_source"]:
            needs.append("source")
        if item["needs_fact_check"]:
            needs.append("fact_check")
        lines.append(
            "| {slide_no} | {local_order} | {headline} | {needs} | {evidence_type} | "
            "{source_type} | {priority} | {source_priority} | {evidence_status} | "
            "{evidence_ref} | {remaining_gap} |".format(
                slide_no=item["slide_no"],
                local_order=item["local_order"],
                headline=str(item["headline"]).replace("|", "/"),
                needs=", ".join(needs),
                evidence_type=item["evidence_type"],
                source_type=item["suggested_source_type"],
                priority=item["priority"],
                source_priority=item["source_priority"],
                evidence_status=item.get("evidence_status", "missing"),
                evidence_ref=str(item.get("evidence_ref") or "").replace("|", "/"),
                remaining_gap=str(item.get("remaining_gap") or "").replace("|", "/"),
            )
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_plan_report(
    path: Path,
    bundle: dict[str, Any],
    storyline: dict[str, Any],
    pack: dict[str, Any],
    slide_needs: list[dict[str, Any]],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    sections = storyline.get("sections", [])
    section_titles = [str(section.get("section_title")) for section in sections]
    high_priority = [item for item in slide_needs if item["priority"] == "high"]
    readiness = _readiness_summary(pack, slide_needs)
    coverage_by_section = _coverage_by_section(slide_needs)
    slide_count = sum(len(section.get("slides", [])) for section in sections)
    lines = [
        "# Anny Evidence Enrichment Plan — AI Knowledge Institution",
        "",
        "## Current Storyline Summary",
        "",
        f"- title: {storyline.get('title')}",
        f"- sections: {len(section_titles)}",
        f"- slides: {slide_count}",
        f"- source bundle: {bundle.get('bundle_id')}",
        f"- filled evidence count: {_real_evidence_count(pack)}",
        f"- ready_for_enriched_dry_run: {readiness['ready_for_enriched_dry_run']}",
        "- interpretation: story-structure dry run sample, not a completed research packet.",
        "- next step: enrich evidence before another manual anny dry run.",
        "",
        "## Sections",
        "",
        *[f"- {title}" for title in section_titles],
        "",
        "## Missing Evidence By Section",
        "",
    ]
    for section in section_titles:
        count = sum(1 for item in slide_needs if item["section_title"] == section)
        lines.append(f"- {section}: {count} evidence task(s)")
    lines.extend(
        [
            "",
            "## Evidence Coverage By Section",
            "",
            *[
                "- {section}: covered={covered}, partial={partial}, missing={missing}".format(
                    section=section,
                    covered=counts.get("covered", 0),
                    partial=counts.get("partial", 0),
                    missing=counts.get("missing", 0),
                )
                for section, counts in coverage_by_section.items()
            ],
            "",
            "## Remaining Must-Have Gaps",
            "",
        ]
    )
    if readiness["remaining_must_have_gaps"]:
        lines.extend(
            [
                f"- slide {item['slide_no']}: {item['headline']} -> {item['remaining_gap']}"
                for item in readiness["remaining_must_have_gaps"]
            ]
        )
    else:
        lines.append("- 치명적인 must-have evidence gap 없음.")
    lines.extend(
        [
            "",
            "## Must-Have Evidence",
            "",
            *[f"- {item}" for item in pack["manual_research_checklist"][:5]],
            "",
            "## Nice-To-Have Evidence",
            "",
            "- AI 검색창 vs 기존 검색 결과 비교 이미지/도식",
            "- 한국 학교/과학관/박물관 사례 1개 이상",
            "- AI가 학습 접근성을 높인다는 반대 관점",
            "",
            "## Official / Korea Bridge Evidence",
            "",
            "- 국내 학교 AI 교육 정책",
            "- 국내 과학관/박물관 AI 교육/전시 사례",
            "- 교육부/과기정통부 AI 리터러시 관련 자료",
            "",
            "## Counterpoints",
            "",
            "- AI가 학습 접근성을 높일 수 있다는 주장",
            "- AI 도구 사용이 질문 능력을 보완할 수 있다는 관점",
            f"- counterpoint_coverage: {readiness['counterpoint_count']} item(s)",
            f"- korea_bridge_coverage: {readiness['korea_bridge_count']} item(s)",
            "",
            "## Visual Candidates",
            "",
            *[f"- {item['title']}" for item in pack["visual_candidates"]],
            "",
            "## High Priority Slide Needs",
            "",
            *[
                f"- slide {item['slide_no']}: {item['headline']} -> {item['suggested_source_type']}"
                for item in high_priority
            ],
            "",
            "## Manual Research Checklist",
            "",
            *[f"- [ ] {item}" for item in pack["manual_research_checklist"]],
            "",
            "## 1.5.2b Readiness Gate",
            "",
            (
                "- primary_article: "
                f"{'covered' if readiness['primary_article_covered'] else 'missing'}"
            ),
            (
                "- supporting_or_research: "
                f"{readiness['supporting_articles_count']} supporting + "
                f"{readiness['research_or_survey_count']} research"
            ),
            f"- counterpoint: {readiness['counterpoint_count']}",
            f"- institution_example: {readiness['institution_example_count']}",
            f"- korea_bridge: {readiness['korea_bridge_count']}",
            (
                "- recommendation: ready_for_enriched_dry_run="
                f"{readiness['ready_for_enriched_dry_run']}"
            ),
            "",
            "## Next Milestone",
            "",
            "Milestone 1.5.2 — Enriched Manual Anny Storyline Dry Run",
            "",
            "- Attach the evidence pack manually.",
            "- Rewrite the same topic with stronger source coverage.",
            "- Still do not build production anny or call an LLM API from Codex.",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _coverage_by_section(slide_needs: list[dict[str, Any]]) -> dict[str, dict[str, int]]:
    coverage: dict[str, dict[str, int]] = {}
    for item in slide_needs:
        section = str(item.get("section_title") or "unknown")
        status = str(item.get("evidence_status") or "missing")
        coverage.setdefault(section, {"covered": 0, "partial": 0, "missing": 0})
        coverage[section][status] = coverage[section].get(status, 0) + 1
    return coverage


@app.callback(invoke_without_command=True)
def main(
    bundle_path: Annotated[
        Path,
        typer.Option("--bundle", help="Single anny input bundle JSON path."),
    ] = DEFAULT_BUNDLE_PATH,
    storyline_path: Annotated[
        Path,
        typer.Option("--storyline", help="Manual dry-run storyline JSON path."),
    ] = DEFAULT_STORYLINE_PATH,
    evidence_pack_path: Annotated[
        Path,
        typer.Option("--evidence-pack", help="Evidence pack JSON output path."),
    ] = DEFAULT_EVIDENCE_PACK_PATH,
    needs_report_path: Annotated[
        Path,
        typer.Option("--needs-report", help="Slide evidence needs Markdown path."),
    ] = DEFAULT_NEEDS_REPORT,
    plan_report_path: Annotated[
        Path,
        typer.Option("--plan-report", help="Evidence enrichment plan Markdown path."),
    ] = DEFAULT_PLAN_REPORT,
) -> None:
    result = build_evidence_enrichment_plan(
        bundle_path=bundle_path,
        storyline_path=storyline_path,
        evidence_pack_path=evidence_pack_path,
        needs_report_path=needs_report_path,
        plan_report_path=plan_report_path,
    )
    console.print(
        "[green]Wrote anny evidence enrichment plan "
        f"({result['slide_needs_count']} slide needs).[/green]"
    )


if __name__ == "__main__":
    app()
