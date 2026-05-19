from luddite.agents.piti.build_slide_spec_from_storyline import (
    build_piti_slide_spec_from_storyline,
    validate_piti_slide_spec,
)


def _storyline(slides):
    return {
        "storyline_id": "storyline_test",
        "title": "테스트 스토리",
        "risk_flags": [],
        "required_fact_checks": [],
        "sections": [
            {
                "section_title": "섹션",
                "purpose": "테스트",
                "slides": slides,
            }
        ],
    }


def test_piti_slide_spec_builds_screen_copy_and_diagram_for_conceptual_slide() -> None:
    storyline = _storyline(
        [
            {
                "slide_no": 1,
                "slide_type": "explainer",
                "headline": "AI가 답을 바로 주는 건 편리하다",
                "body": [
                    "모르는 것을 물으면 바로 답이 나오고 검색 시간이 줄어든다.",
                    "다만 편리함이 곧 배움이라는 뜻은 아니다.",
                    "source/fact-check 설명은 화면이 아니라 notes로 내려간다.",
                ],
                "source_urls": ["https://www.microsoft.com/research/example"],
                "image_urls": [],
                "notes": "Microsoft Research — Generative AI and information diversity",
                "needs_source": False,
                "needs_fact_check": True,
                "required_before_broadcast": True,
                "source_refs": [
                    {
                        "url": "https://www.microsoft.com/research/example",
                        "role": "supporting_article",
                        "use": "Generative AI and information diversity",
                        "confidence": "medium",
                        "manual_check_required": True,
                    }
                ],
            }
        ]
    )

    spec = build_piti_slide_spec_from_storyline(storyline, deck_id="test")
    slide = spec["slides"][0]

    assert slide["screen_headline"] == "AI가 답을 바로 주는 건 편리하다"
    assert slide["screen_body"] == []
    assert "다만 편리함" not in "\n".join(slide["screen_body"])
    assert "다만 편리함" in "\n".join(slide["overflow_notes"])
    assert slide["proof_object"]["type"] == "diagram"
    assert "기존 검색" in slide["proof_object"]["diagram_nodes"]
    assert "AI 즉답" in slide["proof_object"]["diagram_nodes"]
    assert slide["source_refs"][0]["url"] == "https://www.microsoft.com/research/example"
    assert validate_piti_slide_spec(spec)["passed"] is True


def test_piti_slide_spec_keeps_source_card_for_source_identity_slide() -> None:
    storyline = _storyline(
        [
            {
                "slide_no": 1,
                "slide_type": "quote",
                "headline": "영국 왕립천문대 쪽에서 나온 경고",
                "body": [
                    (
                        "BBC 보도는 Royal Observatory 쪽 경고를 AI 의존과 "
                        "인간 지식의 역할이라는 맥락에서 소개한다"
                    ),
                    "단일 기관 사례이므로 모든 지식기관의 공식 입장처럼 일반화하지 않는다",
                ],
                "source_urls": ["https://www.bbc.com/news/example"],
                "image_urls": [],
                "notes": "BBC — Royal Observatory warning context",
                "needs_source": False,
                "needs_fact_check": True,
                "required_before_broadcast": True,
            }
        ]
    )

    spec = build_piti_slide_spec_from_storyline(storyline, deck_id="source")
    slide = spec["slides"][0]

    assert slide["proof_object"]["type"] == "source_card"
    assert slide["proof_object"]["source_name"] == "BBC"
    assert slide["proof_object"]["display_title"] != slide["screen_headline"]
    assert validate_piti_slide_spec(spec)["passed"] is True


def test_piti_slide_spec_validates_quote_and_diagram_contracts() -> None:
    storyline = _storyline(
        [
            {
                "slide_no": 1,
                "slide_type": "comparison",
                "headline": "검색과 즉답의 차이",
                "body": ["기존 검색은 비교하고 검증한다", "AI 즉답은 바로 답을 준다"],
                "source_urls": [],
                "image_urls": [],
                "notes": "diagram",
                "needs_source": False,
                "needs_fact_check": False,
                "required_before_broadcast": False,
            }
        ]
    )

    spec = build_piti_slide_spec_from_storyline(storyline, deck_id="diagram")
    slide = spec["slides"][0]
    assert slide["proof_object"]["type"] == "diagram"
    assert slide["proof_object"]["diagram_nodes"]
    assert slide["proof_object"]["diagram_edges"]
    assert validate_piti_slide_spec(spec)["passed"] is True

    slide["proof_object"] = {
        **slide["proof_object"],
        "type": "article_quote",
        "screen_position": "left_half",
        "quote_text": None,
        "quote_translation": None,
    }
    result = validate_piti_slide_spec(spec)
    assert result["passed"] is False
    assert any("article_quote requires quote text" in issue for issue in result["issues"])


def test_piti_slide_spec_validator_rejects_editor_copy_in_screen_body() -> None:
    spec = build_piti_slide_spec_from_storyline(
        _storyline(
            [
                {
                    "slide_no": 1,
                    "slide_type": "bridge",
                    "headline": "무엇을 볼 것인가",
                    "body": ["짧은 질문"],
                    "source_urls": [],
                    "image_urls": [],
                    "notes": "bridge",
                    "needs_source": False,
                    "needs_fact_check": False,
                    "required_before_broadcast": False,
                }
            ]
        ),
        deck_id="editor",
    )
    spec["slides"][0]["screen_body"] = ["[수동 삽입] 이미지를 골라야 함"]

    result = validate_piti_slide_spec(spec)

    assert result["passed"] is False
    assert any("editor instruction leaked" in issue for issue in result["issues"])
