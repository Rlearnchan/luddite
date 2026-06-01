import json

from luddite.agents.jibi.rule_llm_disagreement import (
    build_rule_llm_disagreement_report,
    run_rule_llm_disagreement_report,
)


def _write_json(path, payload):
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def test_rule_llm_disagreement_classifies_rescued_and_lowered_rows(tmp_path) -> None:
    evidence_path = tmp_path / "evidence.json"
    judge_path = tmp_path / "judge.json"
    _write_json(
        evidence_path,
        {
            "run_date": "2026-06-01",
            "items": [
                {
                    "review_item_id": "2026-06-01:weak",
                    "story_bundle_id": "weak",
                    "visible_title": "AI 공공 도입",
                    "editorial_role": "sub_block",
                    "board_score": 63,
                    "rule_diagnostics": {"main_seed_candidate": False},
                },
                {
                    "review_item_id": "2026-06-01:strong",
                    "story_bundle_id": "strong",
                    "visible_title": "무료배달 비용",
                    "editorial_role": "sub_block",
                    "board_score": 89,
                    "rule_diagnostics": {"main_seed_candidate": True},
                },
                {
                    "review_item_id": "2026-06-01:main",
                    "story_bundle_id": "main",
                    "visible_title": "물가 충격",
                    "editorial_role": "main_seed",
                    "board_score": 80,
                    "rule_diagnostics": {"main_seed_candidate": False},
                },
            ],
        },
    )
    _write_json(
        judge_path,
        {
            "run_date": "2026-06-01",
            "items": [
                {
                    "story_bundle_id": "weak",
                    "visible_title": "AI 공공 도입",
                    "llm_editorial_role": "main_seed_candidate",
                    "llm_confidence": "low",
                    "opening_question": "공공 AI는 어디까지 왔나?",
                    "missing_evidence": ["계약 비용"],
                    "rule_disagreement": {
                        "disagrees_with_rule": True,
                        "reasons": ["LLM rescued"],
                    },
                },
                {
                    "story_bundle_id": "strong",
                    "visible_title": "무료배달 비용",
                    "llm_editorial_role": "sub_block",
                    "llm_confidence": "low",
                    "opening_question": "누가 내나?",
                    "missing_evidence": ["수수료율"],
                    "rule_disagreement": {
                        "disagrees_with_rule": True,
                        "reasons": ["LLM lowered"],
                    },
                },
                {
                    "story_bundle_id": "main",
                    "visible_title": "물가 충격",
                    "llm_editorial_role": "main_seed_candidate",
                    "llm_confidence": "low",
                    "opening_question": "물가로 어떻게 이어지나?",
                    "missing_evidence": ["국내 물가 영향"],
                    "rule_disagreement": {
                        "disagrees_with_rule": False,
                        "reasons": [],
                    },
                },
            ],
        },
    )

    payload = build_rule_llm_disagreement_report(
        evidence_pack_path=evidence_path,
        llm_judge_path=judge_path,
    )

    assert payload["category_counts"]["rule_rejected_llm_rescued"] == 1
    assert payload["category_counts"]["rule_promoted_llm_lowered"] == 1
    assert payload["category_counts"]["both_agree_main_candidate"] == 1
    assert payload["evidence_missing_but_salvageable_count"] == 3


def test_run_rule_llm_disagreement_writes_reports(tmp_path) -> None:
    evidence_path = tmp_path / "evidence.json"
    judge_path = tmp_path / "judge.json"
    output_json = tmp_path / "out.json"
    output_md = tmp_path / "out.md"
    _write_json(
        evidence_path,
        {
            "run_date": "2026-06-01",
            "items": [
                {
                    "story_bundle_id": "same",
                    "visible_title": "같은 판단",
                    "editorial_role": "sub_block",
                    "rule_diagnostics": {},
                }
            ],
        },
    )
    _write_json(
        judge_path,
        {
            "run_date": "2026-06-01",
            "items": [
                {
                    "story_bundle_id": "same",
                    "llm_editorial_role": "sub_block",
                    "llm_confidence": "low",
                    "rule_disagreement": {"disagrees_with_rule": False, "reasons": []},
                }
            ],
        },
    )

    _json_path, _md_path, payload = run_rule_llm_disagreement_report(
        run_date="2026-06-01",
        evidence_pack_path=evidence_path,
        llm_judge_path=judge_path,
        output_json=output_json,
        output_md=output_md,
    )

    assert payload["category_counts"]["both_agree_weak"] == 1
    assert "Both Agree Weak" in output_md.read_text(encoding="utf-8")
