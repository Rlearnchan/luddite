import json
from pathlib import Path

from luddite.agents.anny.render_storyline_sample import (
    render_storyline_markdown,
    render_storyline_sample,
)


def _sample_storyline() -> dict:
    return {
        "title": "샘플 스토리라인",
        "risk_flags": ["thin_evidence"],
        "required_fact_checks": ["방송 전 원문 확인"],
        "sections": [
            {
                "section_title": "도입",
                "slides": [
                    {
                        "slide_no": 1,
                        "slide_type": "hook",
                        "headline": "AI 즉답의 편리함",
                        "body": ["AI 즉답의 편리함을 도입부에서 보여준다."],
                        "source_urls": ["https://example.com/source"],
                        "needs_source": False,
                        "needs_fact_check": True,
                        "fact_check_kind": "education_research_claim",
                        "fact_check_priority": "medium",
                        "required_before_broadcast": True,
                        "covers_key_beats": ["kb_ai_convenience"],
                        "key_beat_anchors_used": [
                            {
                                "key_beat_id": "kb_ai_convenience",
                                "anchor_phrase": "AI 즉답의 편리함",
                            }
                        ],
                        "source_refs": [
                            {
                                "url": "https://example.com/source",
                                "role": "supporting_article",
                                "use": "source context",
                                "confidence": "medium",
                                "manual_check_required": True,
                            }
                        ],
                        "notes": "source attached is not fact-check complete.",
                    },
                    {
                        "slide_no": 2,
                        "slide_type": "production_checklist",
                        "headline": "방송 전 확인 리스트",
                        "body": ["원문 전문 확인."],
                        "needs_source": True,
                        "needs_fact_check": True,
                        "fact_check_kind": "production_checklist",
                    },
                ],
            }
        ],
    }


def test_render_storyline_markdown_includes_hygiene_metadata() -> None:
    markdown = render_storyline_markdown(
        _sample_storyline(),
        label="sample",
        description="Rendered test sample.",
        manifest={"failure_modes": ["unsupported_claim"], "schema_valid": True},
    )

    assert "production Anny output이 아니라" in markdown
    assert "source attached는 fact-check complete" in markdown
    assert "AI 즉답의 편리함" in markdown
    assert "covers_key_beats" in markdown
    assert "key_beat_anchors_used" in markdown
    assert "needs_fact_check: True" in markdown
    assert "supporting_article" in markdown
    assert "Internal production checklist" in markdown


def test_render_storyline_sample_writes_markdown(tmp_path: Path) -> None:
    input_path = tmp_path / "storyline.json"
    output_path = tmp_path / "storyline.md"
    input_path.write_text(
        json.dumps(_sample_storyline(), ensure_ascii=False),
        encoding="utf-8",
    )

    rendered = render_storyline_sample(
        input_path=input_path,
        output_path=output_path,
        label="sample",
        description="Rendered test sample.",
    )

    assert rendered == output_path
    assert output_path.exists()
    assert "샘플 스토리라인" in output_path.read_text(encoding="utf-8")
