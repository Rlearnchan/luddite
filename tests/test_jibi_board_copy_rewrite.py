import json

from luddite.agents.jibi.board_copy_rewrite import (
    build_board_copy_rewrite_preview,
    run_board_copy_rewrite_preview,
)


class FakeRewriteClient:
    model = "gpt-5-mini"

    def json_response(
        self,
        prompt: str,
        *,
        timeout_seconds: int = 120,
        max_output_tokens: int = 1200,
    ):
        assert "rewrite reviewer-board copy" in prompt.lower()
        return (
            json.dumps(
                {
                    "title": "공공 AI, 현장 안전을 바꿀까",
                    "description": (
                        "춘천 공사장 CCTV 사례로 AI 안전관리의 비용과 "
                        "책임 구조를 확인할 후보입니다."
                    ),
                    "why_rewrite": "generic copy replaced with concrete evidence",
                    "source_evidence_used": ["춘천시 AI CCTV 시범 운영"],
                },
                ensure_ascii=False,
            ),
            {"id": "resp_copy"},
        )


def _write_json(path, payload):
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def _evidence_payload():
    return {
        "run_date": "2026-06-01",
        "items": [
            {
                "review_item_id": "2026-06-01:bundle",
                "story_bundle_id": "bundle",
                "story_fingerprint": "fingerprint",
                "visible_title": "해외 후보, 한 가지 질문으로 더 좁혀볼 소재",
                "visible_description": "아직 좁혀야 합니다.",
                "board_score": 63,
                "article_bodies": [
                    {
                        "fetch_status": "ok",
                        "body_excerpt": "춘천시 공사장 AI CCTV 시범 운영과 안전관리 책임 구조",
                    }
                ],
            }
        ],
    }


def _judge_payload():
    return {
        "run_date": "2026-06-01",
        "items": [
            {
                "story_bundle_id": "bundle",
                "visible_title": "해외 후보, 한 가지 질문으로 더 좁혀볼 소재",
                "llm_editorial_role": "main_seed_candidate",
                "llm_confidence": "low",
                "opening_question": "공공 AI는 현장 안전을 실제로 바꿀까?",
                "why_it_could_work": "공사장 CCTV라는 구체 장면이 있습니다.",
                "missing_evidence": ["계약 비용"],
            }
        ],
    }


def test_copy_rewrite_preview_uses_renderer_compatible_item_keys(tmp_path) -> None:
    evidence_path = tmp_path / "evidence.json"
    judge_path = tmp_path / "judge.json"
    _write_json(evidence_path, _evidence_payload())
    _write_json(judge_path, _judge_payload())

    payload = build_board_copy_rewrite_preview(
        evidence_pack_path=evidence_path,
        llm_judge_path=judge_path,
        enabled=True,
        llm_client=FakeRewriteClient(),
    )

    assert payload["llm_copy_rewrite_enabled"] is True
    assert "2026-06-01:bundle" in payload["items"]
    rewrite = payload["items"]["2026-06-01:bundle"]
    assert rewrite["title"] == "공공 AI, 현장 안전을 바꿀까"
    assert rewrite["reason"] == "evidence_pack_llm_copy_preview"


def test_copy_rewrite_preview_default_output_is_preview_not_live_override(tmp_path) -> None:
    evidence_path = tmp_path / "evidence.json"
    judge_path = tmp_path / "judge.json"
    _write_json(evidence_path, _evidence_payload())
    _write_json(judge_path, _judge_payload())

    output_json, output_md, payload = run_board_copy_rewrite_preview(
        run_date="2026-06-01",
        evidence_pack_path=evidence_path,
        llm_judge_path=judge_path,
        output_md=tmp_path / "rewrite.md",
        enabled=False,
    )

    assert output_json.name == "jibi_review_board_2026-06-01.evidence_preview.json"
    assert output_md.exists()
    assert payload["item_count"] == 1
    assert payload["items"]["2026-06-01:bundle"]["title"].endswith("?")
