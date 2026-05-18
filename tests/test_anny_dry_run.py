import json
from datetime import UTC, datetime

from luddite.agents.anny.prepare_dry_run import prepare_anny_dry_run
from luddite.eval.anny_dry_run_eval import (
    hygiene_contract_errors,
    validate_dry_run_storyline,
)
from luddite.utils.jsonl import write_jsonl


def _bundle() -> dict:
    return {
        "bundle_id": "anny_bundle_09277535430e",
        "story_seed_id": "cluster_ai",
        "story_seed_title": "AI 즉답 시대의 지식기관 역할",
        "editorial_category": "ai_knowledge_institution",
        "seed_type": "ai_knowledge_institution",
        "readiness": "needs_more_evidence",
        "handoff_priority": "high",
        "core_question": "AI가 답을 즉시 주는 시대에 학교와 지식기관은 무엇을 가르쳐야 하는가?",
        "why_story": "AI 즉답과 지식기관 역할 변화",
        "known_facts": ["Royal Observatory warning"],
        "candidate_articles": [],
        "missing_evidence": ["보조 기사 1개 이상"],
        "required_evidence": ["보조 기사 1개 이상"],
        "nice_to_have_evidence": [],
        "fact_check_tasks": ["원문 전문 확인"],
        "official_source_tasks": [],
        "suggested_official_sources": ["박물관/천문관 공식 설명"],
        "possible_story_angles": ["AI 검색", "지식기관"],
        "suggested_story_structure": ["AI 즉답", "사고 과정", "지식기관 역할"],
        "opening_hook": "Instant AI answers can trivialise human intelligence",
        "audience_question": "지식기관은 무엇을 가르쳐야 하는가?",
        "slide_count_target": "standard",
        "tone_notes": ["구조 설명 중심"],
        "must_include": ["후보 기사 URL과 source를 명시"],
        "avoid": ["교육 효과나 인지 저하를 단정하지 말 것"],
        "risk_flags": [],
        "risk_level": "low",
        "quality_flags": [],
        "do_not_claim": ["교육 효과나 인지 저하를 단정하지 말 것"],
        "needs_fact_check": True,
        "llm_enrichment_needed": True,
        "created_at": datetime(2026, 5, 18, tzinfo=UTC).isoformat(),
    }


def _cases() -> dict:
    return {
        "version": "v1.5",
        "input_bundle_path": "data/candidates/anny_input_bundles.jsonl",
        "cases": [
            {
                "case_id": "anny_dry_run_ai_knowledge_institution_v1",
                "bundle_id": "anny_bundle_09277535430e",
                "story_seed_title": "AI 즉답 시대의 지식기관 역할",
                "expected_length_mode": "standard_representative_outline",
                "expected_sections_min": 3,
                "expected_sections_max": 4,
                "expected_key_beats": [
                    "AI 즉답이 주는 편리함",
                    "생각하는 과정이 생략될 수 있다는 문제 제기",
                    "학교/박물관/천문관 같은 지식기관의 역할 변화",
                    "AI 비판/찬양이 아니라 무엇을 가르칠지에 대한 질문",
                ],
                "evaluation_notes": [],
            }
        ],
    }


def _storyline() -> dict:
    source_url = "https://www.bbc.com/news/articles/c2023l60370o"
    return {
        "storyline_id": "anny_dry_run_ai_knowledge_institution_v1",
        "title": "AI 즉답 시대의 지식기관 역할",
        "one_liner": "AI 즉답이 주는 편리함과 생각하는 과정의 생략을 묻는다.",
        "estimated_slide_count": 24,
        "risk_flags": ["single_source_dependency"],
        "required_fact_checks": ["교육 효과와 인지 저하 주장은 추가 근거 필요"],
        "sections": [
            {
                "section_title": "AI 즉답이 주는 편리함",
                "slides": [
                    {
                        "slide_type": "hook",
                        "headline": "AI가 바로 답을 주는 시대",
                        "body": ["검색보다 빠른 답이 일상이 됐다."],
                        "source_urls": [source_url],
                        "image_urls": [],
                        "notes": "원문 확인 필요",
                        "needs_fact_check": True,
                        "needs_source": False,
                    }
                ],
            },
            {
                "section_title": "생각하는 과정이 생략될 수 있다는 문제 제기",
                "slides": [
                    {
                        "slide_type": "explainer",
                        "headline": "문제는 답이 아니라 과정",
                        "body": ["AI 비판/찬양이 아니라 무엇을 가르칠지에 대한 질문이다."],
                        "source_urls": [source_url],
                        "image_urls": [],
                        "notes": "교육 효과 단정 금지",
                        "needs_fact_check": True,
                        "needs_source": False,
                    }
                ],
            },
            {
                "section_title": "학교/박물관/천문관 같은 지식기관의 역할 변화",
                "slides": [
                    {
                        "slide_type": "closing_question",
                        "headline": "지식기관은 무엇을 가르쳐야 하나",
                        "body": ["답을 찾는 법보다 질문을 만드는 법일 수 있다."],
                        "source_urls": [source_url],
                        "image_urls": [],
                        "notes": "보조 사례 필요",
                        "needs_fact_check": True,
                        "needs_source": False,
                    }
                ],
            },
        ],
    }


def test_prepare_anny_dry_run_extracts_single_bundle(tmp_path) -> None:
    cases_path = tmp_path / "cases.json"
    bundles_path = tmp_path / "bundles.jsonl"
    output_path = tmp_path / "input_bundle.json"
    expected_path = tmp_path / "storyline.json"
    cases_path.write_text(json.dumps(_cases(), ensure_ascii=False), encoding="utf-8")
    write_jsonl(bundles_path, [_bundle()])

    result = prepare_anny_dry_run(
        cases_path=cases_path,
        bundles_path=bundles_path,
        output_bundle_path=output_path,
        expected_storyline_path=expected_path,
    )

    assert result["bundle_id"] == "anny_bundle_09277535430e"
    assert json.loads(output_path.read_text(encoding="utf-8"))["story_seed_title"] == (
        "AI 즉답 시대의 지식기관 역할"
    )


def test_validate_anny_dry_run_storyline_passes(tmp_path) -> None:
    cases_path = tmp_path / "cases.json"
    storyline_path = tmp_path / "storyline.json"
    cases_path.write_text(json.dumps(_cases(), ensure_ascii=False), encoding="utf-8")
    storyline_path.write_text(
        json.dumps(_storyline(), ensure_ascii=False),
        encoding="utf-8",
    )

    result = validate_dry_run_storyline(
        storyline_path=storyline_path,
        cases_path=cases_path,
    )

    assert result["schema_valid"] is True
    assert result["section_count_ok"] is True
    assert result["slide_count_ok"] is False
    assert result["source_image_overlap_count"] == 0
    assert result["fact_check_marker_present"] is True
    assert result["passed"] is False


def test_validate_anny_dry_run_can_require_hygiene_contract(tmp_path) -> None:
    cases_path = tmp_path / "cases.json"
    storyline_path = tmp_path / "storyline.json"
    hygiene_path = tmp_path / "hygiene.jsonl"
    cases_path.write_text(json.dumps(_cases(), ensure_ascii=False), encoding="utf-8")
    storyline = _storyline()
    storyline_path.write_text(json.dumps(storyline, ensure_ascii=False), encoding="utf-8")
    slides = [slide for section in storyline["sections"] for slide in section["slides"]]
    write_jsonl(
        hygiene_path,
        [
            {
                "slide_no": index,
                "fact_check_priority": "high",
                "fact_check_kind": "factual_claim",
                "required_before_storyline": False,
                "required_before_broadcast": True,
                "source_refs": [
                    {
                        "url": slide["source_urls"][0],
                        "role": "primary_article",
                        "use": "test source",
                        "confidence": "medium",
                        "manual_check_required": True,
                    }
                ],
            }
            for index, slide in enumerate(slides, start=1)
        ],
    )

    result = validate_dry_run_storyline(
        storyline_path=storyline_path,
        cases_path=cases_path,
        hygiene_jsonl_path=hygiene_path,
        require_hygiene_contract=True,
    )

    assert result["hygiene_contract_passed"] is True
    assert result["hygiene_record_count"] == 3


def test_rhetorical_caution_hygiene_does_not_require_source_refs() -> None:
    errors = hygiene_contract_errors(
        [
            {
                "slide_no": 1,
                "fact_check_priority": "low",
                "fact_check_kind": "rhetorical_caution",
                "required_before_storyline": False,
                "required_before_broadcast": False,
                "source_refs": [],
            }
        ],
        expected_slide_count=1,
    )

    assert errors == []


def test_validate_policy_finance_guardrails_rejects_investment_advice(tmp_path) -> None:
    cases_path = tmp_path / "cases.json"
    storyline_path = tmp_path / "storyline.json"
    hygiene_path = tmp_path / "hygiene.jsonl"
    cases = _cases()
    cases["cases"][0]["case_id"] = "anny_dry_run_productive_finance_policy_v1"
    cases["cases"][0]["expected_key_beats"] = [
        "담보·단기수익 중심 금융의 한계",
        "AI/반도체 투자와 장기 위험자본 필요",
        "국민성장펀드/정책금융 논쟁",
        "금융권이 어디까지 위험을 나눌 수 있는가",
    ]
    cases_path.write_text(json.dumps(cases, ensure_ascii=False), encoding="utf-8")
    storyline = {
        "storyline_id": "finance_bad",
        "title": "생산적 금융과 정책자금 전환",
        "one_liner": "국민성장펀드와 정책금융 논쟁",
        "estimated_slide_count": 24,
        "risk_flags": ["investment_advice_risk"],
        "required_fact_checks": ["정책 효과 공식자료 확인"],
        "sections": [
            {
                "section_title": "담보·단기수익 중심 금융의 한계",
                "slides": [
                    {
                        "slide_type": "hook",
                        "headline": "정책금융이 바뀐다",
                        "body": ["정책 효과가 입증됐다", "주가가 오른다"],
                        "source_urls": ["https://example.com/a"],
                        "image_urls": [],
                        "notes": "투자 조언처럼 쓰면 안 됨",
                        "needs_fact_check": True,
                        "needs_source": False,
                    }
                ],
            },
            {
                "section_title": "AI/반도체 투자와 장기 위험자본 필요",
                "slides": [
                    {
                        "slide_type": "explainer",
                        "headline": "장기 위험자본",
                        "body": ["금융권이 어디까지 위험을 나눌 수 있는가"],
                        "source_urls": ["https://example.com/a"],
                        "image_urls": [],
                        "notes": "리스크 논의 필요",
                        "needs_fact_check": True,
                        "needs_source": False,
                    }
                ],
            },
            {
                "section_title": "국민성장펀드/정책금융 논쟁",
                "slides": [
                    {
                        "slide_type": "closing_question",
                        "headline": "정책자금은 어디까지 가야 하나",
                        "body": ["반론과 리스크도 같이 봐야 한다"],
                        "source_urls": ["https://example.com/a"],
                        "image_urls": [],
                        "notes": "counterpoint",
                        "needs_fact_check": True,
                        "needs_source": False,
                    }
                ],
            },
        ],
    }
    storyline_path.write_text(json.dumps(storyline, ensure_ascii=False), encoding="utf-8")
    write_jsonl(
        hygiene_path,
        [
            {
                "slide_no": index,
                "fact_check_priority": "high",
                "fact_check_kind": "policy_effect_claim",
                "required_before_storyline": False,
                "required_before_broadcast": True,
                "source_refs": [
                    {
                        "url": "https://example.com/a",
                        "role": "supporting_article",
                        "use": "test source",
                        "confidence": "medium",
                        "manual_check_required": True,
                    }
                ],
            }
            for index in range(1, 4)
        ],
    )

    result = validate_dry_run_storyline(
        storyline_path=storyline_path,
        cases_path=cases_path,
        case_id="anny_dry_run_productive_finance_policy_v1",
        hygiene_jsonl_path=hygiene_path,
        require_hygiene_contract=True,
    )

    assert result["policy_finance_topic"] is True
    assert result["policy_finance_guardrails_passed"] is False
    assert result["passed"] is False
