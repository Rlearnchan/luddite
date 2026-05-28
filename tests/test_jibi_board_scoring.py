import unittest

from luddite.agents.jibi.board_scoring import compute_board_score


class JibiBoardScoringTests(unittest.TestCase):
    def test_board_score_report_fields_remain_backward_compatible(self) -> None:
        record = {
            "story_bundle_id": "story_bundle_ai_public",
            "bundle_title": "공공기관 AI 보고서 책임 논란",
            "story_fingerprint": "ai_public_responsibility",
        }
        representative = {
            "candidate_id": "ai_public",
            "title": "공공기관 AI 보고서 책임 논란",
            "summary": "공무원 보고서와 현장 행정에 AI가 들어오며 책임 소재가 쟁점이다.",
            "source": "연합뉴스 산업",
            "source_role_class": "public_wire",
            "seed_type": "public_ai_governance",
            "story_role": "standalone_seed",
            "seed_quality_classification": "standalone_seed",
            "quality_flags": [],
            "risk_flags": [],
            "scores": {"total_score": 70, "broadcast_potential_proxy": 4},
        }

        result = compute_board_score(
            record=record,
            representative=representative,
            history_rows=[],
            mismatch_reasons=[],
            syuka_similarity=None,
            second_search=None,
        )

        for field in [
            "total_score",
            "board_score",
            "reasons",
            "generic_frame_risk",
            "angle_shift_score",
            "frame_options",
            "topic_families",
            "primary_topic_family",
            "review_adjustments",
        ]:
            self.assertIn(field, result)
        self.assertGreater(result["board_score"], result["total_score"])


if __name__ == "__main__":
    unittest.main()
