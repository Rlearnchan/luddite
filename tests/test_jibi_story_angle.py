import unittest

from luddite.agents.jibi.story_angle import analyze_story_angle


class JibiStoryAngleTests(unittest.TestCase):
    def test_angle_lab_ignores_generated_wrong_frame_text(self) -> None:
        record = {
            "bundle_title": "메타, AI 유료 구독 도입",
            "story_fingerprint": "meta_ai_subscription",
        }
        representative = {
            "title": "메타, AI 유료 구독 도입…월 7.99달러부터",
            "summary": "메타가 인공지능 서비스 유료 구독 모델을 도입한다.",
            "seed_type": "platform_labor_market",
            "source_role_class": "public_wire",
            "why_interesting": "플랫폼의 수수료·배달비·상인 부담 논쟁",
            "possible_expansions": ["무료배달 경쟁의 비용 전가 구조"],
        }

        profile = analyze_story_angle(record, representative)

        frames = profile["frame_options"]
        self.assertTrue(frames)
        self.assertTrue(frames[0]["frame"].startswith("무료 기능이 월 구독"))
        self.assertTrue(all("배달비" not in frame["frame"] for frame in frames))


if __name__ == "__main__":
    unittest.main()
