import json

from luddite.agents.jibi.llm_client import jibi_llm_model
from luddite.agents.jibi.llm_editorial_judge import (
    judge_evidence_item,
    normalize_judge_payload,
    run_llm_editorial_judge,
)


class FakeJudgeClient:
    model = "gpt-5-mini"

    def json_response(
        self,
        prompt: str,
        *,
        timeout_seconds: int = 120,
        max_output_tokens: int = 1200,
    ):
        assert "report-only editorial judge" in prompt
        return (
            json.dumps(
                {
                    "llm_editorial_role": "main_seed_candidate",
                    "llm_confidence": "medium",
                    "opening_question": "전기요금은 왜 전쟁을 따라 움직이나?",
                    "why_it_could_work": "본문에 요금, 가스값, 전력망 비용 구조가 있다.",
                    "why_it_might_fail": "한국 보강 출처가 더 필요하다.",
                    "required_evidence": ["공식 요금 자료"],
                    "missing_evidence": ["두 번째 독립 출처"],
                    "suggested_second_search_queries": ["전기요금 가스값 전력망 투자"],
                    "syuka_style_fit": {
                        "daily_life_bridge": True,
                        "hidden_cost_or_owner": True,
                        "institutional_absurdity": False,
                        "known_brand_hook": False,
                        "too_moral_or_generic": False,
                    },
                    "rule_disagreement": {
                        "disagrees_with_rule": True,
                        "reasons": ["rule saw generic energy, body has concrete cost mechanism"],
                    },
                },
                ensure_ascii=False,
            ),
            {"id": "resp_test"},
        )


def _evidence_item():
    return {
        "story_bundle_id": "bundle_1",
        "visible_title": "전기요금은 왜 전쟁과 가스값을 따라 움직이나",
        "editorial_role": "sub_block",
        "board_score": 88,
        "rule_diagnostics": {"main_seed_candidate": True},
        "article_bodies": [
            {
                "fetch_status": "ok",
                "body_excerpt": "전기요금과 가스값, 전력망 투자 비용 구조 설명",
                "numbers": ["12.5%"],
                "entities": ["한국전력"],
            }
        ],
    }


def test_jibi_llm_model_defaults_to_gpt5_mini(monkeypatch) -> None:
    monkeypatch.delenv("JIBI_LLM_JUDGE_MODEL", raising=False)
    monkeypatch.delenv("LUDDITE_ANNY_API_MODEL", raising=False)

    assert jibi_llm_model() == "gpt-5-mini"


def test_normalize_judge_payload_rejects_unknown_role() -> None:
    payload = normalize_judge_payload(
        {
            "llm_editorial_role": "surely_main",
            "llm_confidence": "certain",
            "syuka_style_fit": {},
            "rule_disagreement": {},
        }
    )

    assert payload["llm_editorial_role"] == "reject"
    assert payload["llm_confidence"] == "low"


def test_judge_evidence_item_parses_structured_response() -> None:
    result = judge_evidence_item(_evidence_item(), llm_client=FakeJudgeClient())

    assert result["judge_status"] == "ok"
    assert result["llm_model"] == "gpt-5-mini"
    assert result["llm_editorial_role"] == "main_seed_candidate"
    assert result["rule_disagreement"]["disagrees_with_rule"] is True


def test_run_llm_editorial_judge_writes_report_only_outputs(tmp_path) -> None:
    evidence_pack_path = tmp_path / "evidence.json"
    output_json = tmp_path / "judge.json"
    output_md = tmp_path / "judge.md"
    evidence_pack_path.write_text(
        json.dumps(
            {
                "run_date": "2026-06-01",
                "items": [_evidence_item()],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    payload = run_llm_editorial_judge(
        evidence_pack_path=evidence_pack_path,
        output_json=output_json,
        output_md=output_md,
        enabled=True,
        llm_client=FakeJudgeClient(),
    )

    assert payload["llm_judge_enabled"] is True
    assert payload["judged_item_count"] == 1
    assert output_json.exists()
    assert "전기요금" in output_md.read_text(encoding="utf-8")
