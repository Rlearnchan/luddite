import csv
import json
import tempfile
import unittest
from pathlib import Path

from luddite.agents.jibi.anny_handoff import build_anny_handoff_payload
from luddite.agents.jibi.append_to_sheet import BUNDLE_REVIEW_SHEET_COLUMNS
from luddite.agents.jibi.render_daily_digest import write_bundle_review_sheet_preview


class JibiAnnyHandoffTests(unittest.TestCase):
    def test_handoff_items_always_include_anny_contract_fields(self) -> None:
        record = {
            "story_bundle_id": "story_bundle_ai_public",
            "story_fingerprint": "ai_public_responsibility",
            "bundle_title": "공공기관 AI 보고서 책임 논란",
            "primary_candidate_id": "ai_public",
        }
        candidate = {
            "candidate_id": "ai_public",
            "title": "공공기관 AI 보고서 책임 논란",
            "source": "연합뉴스 산업",
            "seed_url": "https://example.com/ai-public",
            "source_role_class": "public_wire",
            "story_role": "standalone_seed",
            "seed_quality_classification": "standalone_seed",
        }
        board_score = {
            "total_score": 70,
            "board_score": 84,
            "reasons": ["base_total_score=70", "+8 standalone_seed"],
            "topic_families": ["ai_tech", "policy_government"],
            "primary_topic_family": "policy_government",
            "frame_options": [],
            "review_positive_signals": [],
        }

        payload = build_anny_handoff_payload(
            run_date="2026-05-28",
            records=[record],
            candidate_by_id={"ai_public": candidate},
            board_score_by_id={"story_bundle_ai_public": board_score},
            selection_metadata_by_id={},
            syuka_similarity_index={},
            representative_for_record=lambda item, index: index.get(
                item.get("primary_candidate_id")
            ),
            syuka_similarity_for_record=lambda _record, _candidate, _index: None,
        )

        item = payload["items"][0]
        for field in [
            "editorial_role",
            "angle_options",
            "required_evidence",
            "past_video_context",
        ]:
            self.assertIn(field, item)
        self.assertEqual(item["past_video_context"]["match_type"], "none")

    def test_backfill_metadata_report_and_visible_columns_are_stable(self) -> None:
        clean = {
            "candidate_id": "clean_greenbelt",
            "title": "개발제한구역 주민 생활비 보조 확대",
            "summary": "도시 규제가 주민 생활비 지원으로 이어진다.",
            "seed_url": "https://example.com/greenbelt",
            "source": "연합뉴스 경제",
            "source_role_class": "public_wire",
            "seed_type": "other",
            "story_role": "standalone_seed",
            "seed_quality_classification": "standalone_seed",
            "quality_flags": [],
            "risk_flags": [],
            "recommended_action": "gather_more_evidence",
            "final_grade": "B",
            "scores": {"total_score": 60, "broadcast_potential_proxy": 5},
        }
        evidence = {
            "candidate_id": "agreement",
            "title": "건설산업 상생협약 체결",
            "summary": "건설산업 관계자들이 상생협약을 체결했다.",
            "seed_url": "https://example.com/agreement",
            "source": "연합인포맥스",
            "source_role_class": "market_wire",
            "seed_type": "other",
            "story_role": "evidence_for_larger_story",
            "seed_quality_classification": "evidence_only",
            "quality_flags": [],
            "risk_flags": [],
            "recommended_action": "gather_more_evidence",
            "final_grade": "B",
            "scores": {"total_score": 58, "broadcast_potential_proxy": 4},
        }

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            csv_path = tmp_path / "2026-05-28_bundle_review_sheet.csv"
            write_bundle_review_sheet_preview(
                csv_path,
                [clean, evidence],
                [clean, evidence],
                "2026-05-28",
                review_history_path=tmp_path / "missing_history.jsonl",
                review_board_limit=2,
                use_board_score=True,
            )

            with csv_path.open(encoding="utf-8-sig", newline="") as source:
                rows = list(csv.DictReader(source))
            self.assertEqual(list(rows[0].keys()), BUNDLE_REVIEW_SHEET_COLUMNS)

            metadata = json.loads(
                (tmp_path / "2026-05-28_bundle_review_sheet_metadata.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertTrue(
                any(row["selection_bucket"] == "evidence_backfill" for row in metadata["rows"])
            )
            self.assertTrue(all(row.get("editorial_role") for row in metadata["rows"]))

            report = json.loads(
                (tmp_path / "reports" / "jibi_board_score_2026-05-28.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertTrue(report["fixed_10_backfill_used"])
            self.assertGreaterEqual(report["evidence_backfill_count"], 1)
            self.assertIn("recommended_visible_board_size", report)

            handoff = json.loads(
                (tmp_path / "reports" / "jibi_anny_handoff_2026-05-28.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(handoff["handoff_version"], "jibi_anny_seed_v0")
            self.assertTrue(all("editorial_role" in item for item in handoff["items"]))


if __name__ == "__main__":
    unittest.main()
