import json
from pathlib import Path

from luddite.analysis.compare_slideability_visual_qa import (
    compare_slideability_visual_qa,
)
from luddite.utils.jsonl import write_jsonl


def _proof(proof_type: str, **extra: object) -> dict:
    payload = {
        "type": proof_type,
        "screen_position": "center_large" if proof_type != "none" else "none",
        "manual_insert_required": False,
        "copyright_risk": False,
    }
    payload.update(extra)
    return payload


def _slide(
    slide_no: int,
    *,
    proof_type: str,
    generic_diagram: bool = False,
    needs_fact_check: bool = False,
    required_before_broadcast: bool = False,
    source_refs: list[dict] | None = None,
    do_not_claim: list[str] | None = None,
) -> dict:
    proof = _proof(proof_type)
    if proof_type == "diagram":
        nodes = [
            "AI 즉답",
            "검증",
            "맥락",
        ] if generic_diagram else [
            "정부가 정책자금을 공급함",
            "기업의 장기 투자 위험을 나눔",
            "손실 분담 논쟁이 생김",
        ]
        proof.update(
            {
                "diagram_nodes": nodes,
                "diagram_edges": [
                    {
                        "from": nodes[0],
                        "to": nodes[1],
                        "label": "위험을 나눔",
                    },
                    {
                        "from": nodes[1],
                        "to": nodes[2],
                        "label": "쟁점을 만듦",
                    },
                ],
            }
        )
    if proof_type == "source_card":
        proof.update({"display_title": "Official policy briefing"})
    return {
        "slide_id": f"slide_{slide_no:03d}",
        "slide_no": slide_no,
        "section_id": "section_01",
        "layout_intent": "diagram" if proof_type == "diagram" else "headline_body",
        "screen_headline": f"Slide {slide_no}",
        "screen_body": ["short body"],
        "speaker_notes_expanded": "notes",
        "overflow_notes": [],
        "proof_object": proof,
        "editor_instruction": None,
        "source_refs": source_refs or [],
        "risk_flags": [],
        "needs_source": False,
        "needs_fact_check": needs_fact_check,
        "required_before_broadcast": required_before_broadcast,
        "do_not_claim": do_not_claim or [],
    }


def _slide_spec(title: str, slides: list[dict]) -> dict:
    return {
        "deck_id": f"{title.lower().replace(' ', '_')}_deck",
        "story_seed_title": title,
        "source_storyline_id": "fixture",
        "sections": [
            {
                "section_id": "section_01",
                "section_no": 1,
                "section_title": "Section",
                "purpose": "Test",
                "slides": slides,
            }
        ],
        "slides": slides,
        "readiness": {
            "ready_for_piti_renderer": True,
            "ready_for_production_piti_agent": False,
            "ready_for_broadcast": False,
        },
        "notes": "fixture",
    }


def _write_spec(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def _write_manifest(path: Path) -> None:
    path.write_text(
        json.dumps(
            {
                "schema_valid": True,
                "render_passed": True,
                "section_mapping_complete": True,
                "experiment_outcome": "success",
                "source_hallucination_count": 0,
                "do_not_claim_violation_count": 0,
                "unsupported_claim_count": 0,
                "visible_url_count": 0,
                "comparison_deltas": {"safety_regression_detected": False},
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


def test_compare_reports_proof_and_risk_alignment(tmp_path: Path) -> None:
    bundles_path = tmp_path / "bundles.jsonl"
    specs_dir = tmp_path / "specs"
    specs_dir.mkdir()
    output_path = tmp_path / "comparison.md"
    review_path = tmp_path / "review.md"
    write_jsonl(
        bundles_path,
        [
            {
                "story_seed_title": "Diagram Case",
                "visual_planning_hint": {
                    "slideability_score": 0.9,
                    "visualizability": "high",
                    "first_slide_idea": "diagram first",
                    "likely_proof_object_types": ["diagram", "source_card"],
                    "visual_risks": ["needs_official_data", "policy_claim_risk"],
                    "reason": "fixture",
                    "planning_note": "planning only",
                },
            }
        ],
    )
    source_ref = {"url": "https://example.com", "role": "official", "use": "fact"}
    slides = [
        _slide(
            1,
            proof_type="diagram",
            needs_fact_check=True,
            required_before_broadcast=True,
            source_refs=[source_ref],
            do_not_claim=["정책 효과를 단정하지 말 것"],
        ),
        _slide(2, proof_type="source_card", source_refs=[source_ref]),
    ]
    _write_spec(specs_dir / "diagram_case.json", _slide_spec("Diagram Case", slides))

    compare_slideability_visual_qa(
        bundles_path=bundles_path,
        slide_specs_dir=specs_dir,
        output_path=output_path,
        review_output_path=review_path,
    )

    report = output_path.read_text(encoding="utf-8")
    assert "proof_type_match: strong" in report
    assert "diagramability_alignment: hit" in report
    assert "source_card_alignment: hit" in report
    assert "risk_alignment: good" in report
    assert review_path.exists()


def test_compare_reports_chart_miss_and_missing_hint(tmp_path: Path) -> None:
    bundles_path = tmp_path / "bundles.jsonl"
    specs_dir = tmp_path / "specs"
    specs_dir.mkdir()
    output_path = tmp_path / "comparison.md"
    write_jsonl(
        bundles_path,
        [
            {
                "story_seed_title": "Chart Miss Case",
                "visual_planning_hint": {
                    "slideability_score": 0.7,
                    "visualizability": "medium",
                    "first_slide_idea": "chart first",
                    "likely_proof_object_types": ["chart"],
                    "visual_risks": [],
                    "reason": "fixture",
                    "planning_note": "planning only",
                },
            },
            {"story_seed_title": "No Hint Case"},
        ],
    )
    _write_spec(
        specs_dir / "chart_miss.json",
        _slide_spec("Chart Miss Case", [_slide(1, proof_type="diagram")]),
    )
    _write_spec(
        specs_dir / "no_hint.json",
        _slide_spec("No Hint Case", [_slide(1, proof_type="source_card")]),
    )

    compare_slideability_visual_qa(
        bundles_path=bundles_path,
        slide_specs_dir=specs_dir,
        output_path=output_path,
        review_output_path=None,
    )

    report = output_path.read_text(encoding="utf-8")
    assert "chartability_alignment: miss" in report
    assert "proof_type_match: missing_hint" in report


def test_compare_handles_missing_slide_specs_dir_with_warning(tmp_path: Path) -> None:
    bundles_path = tmp_path / "bundles.jsonl"
    output_path = tmp_path / "comparison.md"
    write_jsonl(bundles_path, [{"story_seed_title": "No Spec Case"}])

    compare_slideability_visual_qa(
        bundles_path=bundles_path,
        slide_specs_dir=tmp_path / "missing_specs",
        output_path=output_path,
        review_output_path=None,
    )

    report = output_path.read_text(encoding="utf-8")
    assert "Slide spec directory not found" in report


def test_compare_reports_adapter_and_direct_alignment(tmp_path: Path) -> None:
    bundles_path = tmp_path / "bundles.jsonl"
    specs_dir = tmp_path / "specs"
    specs_dir.mkdir()
    direct_root = tmp_path / "direct_runs"
    direct_case_dir = direct_root / "run_1" / "diagram_case"
    direct_case_dir.mkdir(parents=True)
    output_path = tmp_path / "comparison.md"
    write_jsonl(
        bundles_path,
        [
            {
                "story_seed_title": "Direct Diagram Case",
                "visual_planning_hint": {
                    "slideability_score": 0.9,
                    "visualizability": "high",
                    "first_slide_idea": "diagram first",
                    "likely_proof_object_types": ["diagram"],
                    "visual_risks": [],
                    "reason": "fixture",
                    "planning_note": "planning only",
                },
            }
        ],
    )
    adapter = _slide_spec(
        "Direct Diagram Case",
        [_slide(1, proof_type="diagram", generic_diagram=True)],
    )
    direct = _slide_spec(
        "Direct Diagram Case",
        [_slide(1, proof_type="diagram", generic_diagram=False)],
    )
    _write_spec(specs_dir / "diagram_case_slide_spec.json", adapter)
    _write_spec(direct_case_dir / "parsed_piti_slide_spec.json", direct)
    _write_manifest(direct_case_dir / "manifest.json")

    compare_slideability_visual_qa(
        bundles_path=bundles_path,
        slide_specs_dir=specs_dir,
        output_path=output_path,
        review_output_path=None,
        include_direct=True,
        direct_run_id="run_1",
        direct_output_root=direct_root,
    )

    report = output_path.read_text(encoding="utf-8")
    assert "adapter_diagramability_alignment: low_quality_hit" in report
    assert "direct_diagramability_alignment: hit" in report
    assert "did_direct_reduce_diagram_generic: true" in report
    assert "did_direct_preserve_predicted_proof_types: true" in report
    assert "did_direct_improve_prediction_quality: true" in report


def test_compare_missing_direct_run_id_is_warning(tmp_path: Path) -> None:
    bundles_path = tmp_path / "bundles.jsonl"
    specs_dir = tmp_path / "specs"
    specs_dir.mkdir()
    output_path = tmp_path / "comparison.md"
    write_jsonl(bundles_path, [{"story_seed_title": "Missing Direct Case"}])
    _write_spec(
        specs_dir / "missing_direct_case_slide_spec.json",
        _slide_spec("Missing Direct Case", [_slide(1, proof_type="diagram")]),
    )

    compare_slideability_visual_qa(
        bundles_path=bundles_path,
        slide_specs_dir=specs_dir,
        output_path=output_path,
        review_output_path=None,
        include_direct=True,
        direct_run_id="missing_run",
        direct_output_root=tmp_path / "direct_runs",
    )

    report = output_path.read_text(encoding="utf-8")
    assert "Direct run root not found" in report
