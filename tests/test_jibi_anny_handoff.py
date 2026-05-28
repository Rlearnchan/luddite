import csv
import json
import tempfile
import unittest
from pathlib import Path

from luddite.agents.jibi.anny_handoff import (
    build_anny_handoff_payload,
    handoff_item,
    normalize_editorial_role,
)
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
            "review_role_constraints",
        ]:
            self.assertIn(field, item)
        self.assertEqual(item["past_video_context"]["match_type"], "none")

    def test_reviewer_objections_are_negative_only(self) -> None:
        item = handoff_item(
            run_date="2026-05-28",
            record={
                "story_bundle_id": "story_bundle_ai_video",
                "story_fingerprint": "ai_video_trip",
                "bundle_title": "AI 여행 영상",
            },
            representative={
                "candidate_id": "ai_video",
                "title": "AI 영상으로 방구석 여행을 즐기는 사람들",
                "source_role_class": "section_news",
                "story_role": "standalone_seed",
                "seed_quality_classification": "standalone_seed",
            },
            board_score={
                "total_score": 80,
                "board_score": 72,
                "review_adjustments": [
                    "casual_ai_use_case_bonus",
                    "hook_only",
                    "needs_new_angle",
                    "ai_grand_discourse_downrank",
                ],
                "review_editorial_roles": ["sub_block"],
                "review_failure_modes": ["too_familiar", "weak_audience_bridge"],
                "review_positive_signals": ["specific_case_needed"],
            },
            selection_metadata={"selection_bucket": "primary_fit"},
            syuka_similarity=None,
        )

        self.assertNotIn("adjustment:casual_ai_use_case_bonus", item["reviewer_objections"])
        self.assertNotIn("adjustment:hook_only", item["reviewer_objections"])
        self.assertIn("adjustment:needs_new_angle", item["reviewer_objections"])
        self.assertIn("adjustment:ai_grand_discourse_downrank", item["reviewer_objections"])
        self.assertIn("failure:too_familiar", item["reviewer_objections"])
        self.assertIn("failure:weak_audience_bridge", item["reviewer_objections"])
        self.assertEqual(item["review_role_constraints"], ["hook_only", "sub_block"])
        self.assertEqual(item["review_positive_signals"], ["specific_case_needed"])

    def test_main_seed_requires_score_primary_fit_and_no_history_or_syuka_risk(self) -> None:
        record = {
            "story_bundle_id": "story_bundle_standalone",
            "bundle_title": "독립 후보",
        }
        representative = {
            "source_role_class": "public_wire",
            "story_role": "standalone_seed",
            "seed_quality_classification": "standalone_seed",
        }

        low_score = normalize_editorial_role(
            record=record,
            representative=representative,
            board_score={"board_score": 54, "history_statuses": []},
            selection_metadata={"selection_bucket": "primary_fit"},
            syuka_similarity=None,
        )
        self.assertEqual(low_score["editorial_role"], "sub_block")

        role_cap = normalize_editorial_role(
            record=record,
            representative=representative,
            board_score={"board_score": 90, "history_statuses": []},
            selection_metadata={"selection_bucket": "role_cap_backfill"},
            syuka_similarity=None,
        )
        self.assertEqual(role_cap["editorial_role"], "sub_block")

        duplicate = normalize_editorial_role(
            record=record,
            representative=representative,
            board_score={"board_score": 90, "history_statuses": []},
            selection_metadata={"selection_bucket": "primary_fit"},
            syuka_similarity={"recommendation": "duplicate"},
        )
        self.assertEqual(duplicate["editorial_role"], "sub_block")

        history_risk = normalize_editorial_role(
            record=record,
            representative=representative,
            board_score={"board_score": 90, "history_statuses": ["rejected_before"]},
            selection_metadata={"selection_bucket": "primary_fit"},
            syuka_similarity=None,
        )
        self.assertEqual(history_risk["editorial_role"], "sub_block")

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

    def test_use_board_score_false_preserves_existing_selection_order(self) -> None:
        campaign = {
            "candidate_id": "knewdeal_campaign",
            "title": "K뉴딜 아카데미 참여청년 모집",
            "seed_url": "https://example.com/knewdeal",
            "source": "정책브리핑",
            "source_role_class": "policy_release",
            "seed_type": "policy_release_seed",
            "story_role": "standalone_seed",
            "seed_quality_classification": "standalone_seed",
            "quality_flags": ["contest_or_campaign_bulletin", "weak_audience_bridge"],
            "risk_flags": [],
            "recommended_action": "gather_more_evidence",
            "final_grade": "B",
            "scores": {"total_score": 82, "broadcast_potential_proxy": 4},
        }
        stronger_board_candidate = {
            "candidate_id": "ai_hospital_ops",
            "title": "AI가 병원 연락 업무를 바꾸는 이유",
            "summary": "병원 예약과 상담 업무에 AI가 들어오며 책임과 비용 구조가 바뀐다",
            "seed_url": "https://example.com/ai-hospital",
            "source": "연합뉴스 산업",
            "source_role_class": "public_wire",
            "seed_type": "healthcare_operations_ai",
            "story_role": "standalone_seed",
            "seed_quality_classification": "standalone_seed",
            "so_what": {
                "so_what_label": "strong",
                "weakness_signals": [],
                "seed_quality_classification": "standalone_seed",
                "story_role": "standalone_seed",
            },
            "quality_flags": [],
            "risk_flags": [],
            "recommended_action": "gather_more_evidence",
            "final_grade": "B",
            "scores": {"total_score": 70, "broadcast_potential_proxy": 4},
        }

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            csv_path = tmp_path / "2026-05-28_bundle_review_sheet.csv"
            write_bundle_review_sheet_preview(
                csv_path,
                [campaign, stronger_board_candidate],
                [campaign, stronger_board_candidate],
                "2026-05-28",
                review_history_path=tmp_path / "missing_history.jsonl",
                review_board_limit=1,
                use_board_score=False,
            )

            with csv_path.open(encoding="utf-8-sig", newline="") as source:
                rows = list(csv.DictReader(source))
            self.assertEqual(len(rows), 1)
            metadata = json.loads(
                (tmp_path / "2026-05-28_bundle_review_sheet_metadata.json").read_text(
                    encoding="utf-8"
                )
            )
            selected_metadata = metadata["rows"][0]
            self.assertIn(
                "knewdeal_campaign",
                [
                    selected_metadata.get("primary_candidate_id"),
                    *selected_metadata.get("supporting_candidate_ids", []),
                    *selected_metadata.get("evidence_candidate_ids", []),
                ],
            )

            report = json.loads(
                (tmp_path / "reports" / "jibi_board_score_2026-05-28.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertFalse(report["use_board_score"])
            selected = report["selected"][0]
            suppressed_ai = next(
                row
                for row in report["suppressed_high_total_score_candidates"]
                if row["primary_title"] == stronger_board_candidate["title"]
            )
            self.assertIn("K뉴딜", selected["title"])
            self.assertGreater(suppressed_ai["board_score"], selected["board_score"])


if __name__ == "__main__":
    unittest.main()
