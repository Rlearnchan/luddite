import json
from pathlib import Path

from jsonschema import Draft202012Validator

from luddite import paths
from luddite.agents.piti import build_deck_plan_from_storyline, render_deck_storyboard


def _sample_storyline() -> dict:
    long_body = "이 문장은 PPT 한 장에 바로 넣기에는 길어서 edit warning을 남겨야 한다. " * 5
    return {
        "storyline_id": "storyline_test",
        "title": "테스트 스토리라인",
        "risk_flags": ["single_source_dependency"],
        "required_fact_checks": ["원문 확인"],
        "sections": [
            {
                "section_title": "첫 번째 섹션",
                "purpose": "도입",
                "slides": [
                    {
                        "slide_no": 1,
                        "slide_type": "title",
                        "headline": "테스트 제목",
                        "body": ["질문 하나"],
                        "source_urls": [],
                        "image_urls": [],
                        "notes": "제목 슬라이드",
                        "needs_source": False,
                        "needs_fact_check": False,
                    },
                    {
                        "slide_no": 2,
                        "slide_type": "explainer",
                        "headline": "근거가 붙은 설명",
                        "body": [long_body],
                        "source_urls": ["https://example.com/source"],
                        "image_urls": [],
                        "notes": "설명 슬라이드",
                        "needs_source": False,
                        "needs_fact_check": True,
                        "required_before_broadcast": True,
                    },
                    {
                        "slide_no": 3,
                        "slide_type": "production_checklist",
                        "headline": "제작 체크리스트",
                        "body": ["추가 확인"],
                        "source_urls": ["https://example.com/check"],
                        "image_urls": [],
                        "notes": "내부 체크리스트",
                        "needs_source": True,
                        "needs_fact_check": True,
                    },
                ],
            },
            {
                "section_title": "두 번째 섹션",
                "purpose": "마무리",
                "slides": [
                    {
                        "slide_no": 4,
                        "slide_type": "closing_question",
                        "headline": "마지막 질문",
                        "body": ["무엇을 남길까"],
                        "source_urls": [],
                        "image_urls": [],
                        "notes": "마무리",
                        "needs_source": False,
                        "needs_fact_check": False,
                    }
                ],
            },
        ],
    }


def test_build_deck_plan_from_storyline_schema_valid() -> None:
    deck_plan = build_deck_plan_from_storyline.build_deck_plan_from_storyline(
        _sample_storyline(),
        deck_id="test",
        source_storyline_path=Path("storyline.json"),
    )
    schema = json.loads((paths.SPECS_DIR / "deck_schema.json").read_text(encoding="utf-8"))
    errors = list(Draft202012Validator(schema).iter_errors(deck_plan))

    assert not errors
    assert deck_plan["source_storyline_id"] == "storyline_test"
    assert len(deck_plan["sections"]) == 2
    assert deck_plan["target_slide_count"] == 4


def test_deck_plan_validation_preserves_notes_and_overlap_hygiene() -> None:
    deck_plan = build_deck_plan_from_storyline.build_deck_plan_from_storyline(
        _sample_storyline(),
        deck_id="test",
    )
    result = build_deck_plan_from_storyline.validate_deck_plan(deck_plan)

    assert result["passed"]
    assert result["source_image_overlap_count"] == 0
    assert not result["speaker_notes_missing"]
    assert result["production_checklist_count"] == 1
    assert deck_plan["slides"][2]["layout_type"] == "appendix_checklist"
    assert "[내용] https://example.com/source" in deck_plan["slides"][1]["speaker_notes"]


def test_long_body_generates_edit_warning() -> None:
    deck_plan = build_deck_plan_from_storyline.build_deck_plan_from_storyline(
        _sample_storyline(),
        deck_id="test",
    )

    assert any("warning" in note for note in deck_plan["slides"][1]["edit_notes"])


def test_render_deck_storyboard_markdown() -> None:
    deck_plan = build_deck_plan_from_storyline.build_deck_plan_from_storyline(
        _sample_storyline(),
        deck_id="test",
    )
    markdown = render_deck_storyboard.render_deck_storyboard_markdown(deck_plan)

    assert "# 테스트 스토리라인" in markdown
    assert "## Summary" in markdown
    assert "### 01. 테스트 제목" in markdown
    assert "Internal appendix/checklist slide" in markdown


def test_build_and_render_files(tmp_path) -> None:
    storyline_path = tmp_path / "storyline.json"
    deck_path = tmp_path / "deck.json"
    storyboard_path = tmp_path / "storyboard.md"
    storyline_path.write_text(
        json.dumps(_sample_storyline(), ensure_ascii=False),
        encoding="utf-8",
    )

    storyline = json.loads(storyline_path.read_text(encoding="utf-8"))
    deck_plan = build_deck_plan_from_storyline.build_deck_plan_from_storyline(
        storyline,
        deck_id="test",
        source_storyline_path=storyline_path,
    )
    deck_path.write_text(json.dumps(deck_plan, ensure_ascii=False), encoding="utf-8")
    render_deck_storyboard.render_deck_storyboard(
        input_path=deck_path,
        output_path=storyboard_path,
    )

    assert deck_path.exists()
    assert storyboard_path.exists()
    assert "PPT 완성본이 아니라 deck storyboard" in storyboard_path.read_text(
        encoding="utf-8"
    )
