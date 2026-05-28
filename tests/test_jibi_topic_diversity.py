import unittest

from luddite.agents.jibi.topic_diversity import (
    apply_topic_diversity_adjustments,
    infer_topic_profile,
    topic_family_counts,
)


class JibiTopicDiversityTests(unittest.TestCase):
    def test_ai_penalty_is_kept_and_all_family_counts_are_reported(self) -> None:
        scored_records = []
        score_rows = []
        fixtures = [
            ("r1", "AI 병원 예약 업무 자동화", 80),
            ("r2", "AI 데이터센터 전력 사용량 증가", 79),
            ("r3", "AI 공공 보고서 책임 논란", 78),
            ("r4", "Energy bills rise for households", 77),
        ]
        for record_id, title, score in fixtures:
            record = {"story_bundle_id": record_id, "bundle_title": title}
            representative = {"title": title, "summary": title, "seed_type": "other"}
            board_score = {
                "board_score": score,
                "reasons": [f"base_total_score={score}"],
                **infer_topic_profile(record, representative),
            }
            scored_records.append((record, board_score))
            score_rows.append(
                {
                    "story_bundle_id": record_id,
                    "title": title,
                    "board_score": score,
                }
            )

        apply_topic_diversity_adjustments(
            scored_records,
            score_rows,
            use_topic_diversity=True,
        )

        ai_third = next(row for row in score_rows if row["story_bundle_id"] == "r3")
        self.assertLess(ai_third["topic_diversity_penalty"], 0)
        counts = topic_family_counts(score_rows)
        self.assertGreaterEqual(counts["ai_tech"], 3)
        self.assertIn("energy_climate", counts)


if __name__ == "__main__":
    unittest.main()
