import csv
import json

from luddite.agents.jibi.append_to_sheet import BUNDLE_REVIEW_SHEET_COLUMNS
from luddite.agents.jibi.review_feedback import (
    parse_review_tag,
    render_review_feedback_summary,
    render_review_history_calibration,
    summarize_review_feedback,
)


def _write_review_board(path, rows):
    with path.open("w", encoding="utf-8-sig", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=BUNDLE_REVIEW_SHEET_COLUMNS)
        writer.writeheader()
        for row in rows:
            payload = {column: "" for column in BUNDLE_REVIEW_SHEET_COLUMNS}
            payload.update(
                {key: value for key, value in row.items() if key in payload}
            )
            writer.writerow(payload)


def test_parse_review_tag_accepts_lightweight_aliases() -> None:
    assert parse_review_tag("seed — 방송 소재 가능") == "seed"
    assert parse_review_tag("방송 - 바로 가능") == "seed"
    assert parse_review_tag("근거: 큰 주제에 붙이기") == "evidence"
    assert parse_review_tag("묶기 청년 후보와 합치기") == "merge"
    assert parse_review_tag("보강 — 가격 데이터 필요") == "needs"
    assert parse_review_tag("별로 — 홍보성") == "reject"
    assert parse_review_tag("애매 — 왜 올라왔는지 모르겠음") == "unclear"
    assert parse_review_tag("좋아 보임") == "unlabeled"


def test_summarize_review_feedback_counts_tags_and_disagreements() -> None:
    rows = [
        {
            "날짜": "2026-05-23",
            "제목": "청년 노동시장",
            "리뷰-성원": "seed — 가능",
            "리뷰-동찬": "needs — 통계 보강",
            "ID": "2026-05-23:story_bundle_youth",
        },
        {
            "날짜": "2026-05-23",
            "제목": "단일기업 유상증자",
            "리뷰-성원": "seed — 구조로 풀면 가능",
            "리뷰-형찬": "reject — 투자 이야기라 위험",
            "ID": "2026-05-23:story_bundle_market",
        },
    ]

    summary = summarize_review_feedback(rows, run_date="2026-05-23")

    assert summary["total_rows"] == 2
    assert summary["reviewer_completion"] == {
        "리뷰-성원": 2,
        "리뷰-동찬": 1,
        "리뷰-형찬": 1,
    }
    assert summary["tag_counts"]["seed"] == 2
    assert summary["tag_counts"]["needs"] == 1
    assert summary["tag_counts"]["reject"] == 1
    assert summary["disagreement_rows"][0]["reason"] == "seed_vs_reject"


def test_render_review_feedback_summary_from_local_csv(tmp_path) -> None:
    input_csv = tmp_path / "review_board.csv"
    output_md = tmp_path / "feedback.md"
    output_json = tmp_path / "feedback.json"
    _write_review_board(
        input_csv,
        [
            {
                "날짜": "2026-05-23",
                "제목": "양파가 너무 많으면 정부는 무엇을 하나",
                "리뷰-성원": "needs — 가격 데이터 필요",
                "리뷰-동찬": "evidence — 보도자료 느낌",
                "ID": "2026-05-23:story_bundle_onion",
            }
        ],
    )

    outputs, summary = render_review_feedback_summary(
        input_csv=input_csv,
        markdown_path=output_md,
        json_path=output_json,
    )

    assert outputs.markdown_path == output_md
    assert summary["tag_counts"]["needs"] == 1
    assert summary["tag_counts"]["evidence"] == 1
    assert "양파가 너무 많으면 정부는 무엇을 하나" in output_md.read_text(
        encoding="utf-8"
    )
    payload = json.loads(output_json.read_text(encoding="utf-8"))
    assert payload["rows"][0]["id"] == "2026-05-23:story_bundle_onion"


def test_render_review_feedback_summary_accepts_old_nine_column_board(tmp_path) -> None:
    input_csv = tmp_path / "old_review_board.csv"
    fieldnames = [
        "날짜",
        *[
            column
            for column in BUNDLE_REVIEW_SHEET_COLUMNS
            if column not in {"일시", "점수"}
        ],
    ]
    with input_csv.open("w", encoding="utf-8-sig", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerow(
            {
                "날짜": "2026-05-23",
                "제목": "기존 9컬럼 보드",
                "메인 링크": "https://example.com",
                "리뷰-성원": "seed — 가능",
                "ID": "2026-05-23:story_bundle_old",
            }
        )

    _outputs, summary = render_review_feedback_summary(
        input_csv=input_csv,
        markdown_path=tmp_path / "feedback.md",
        json_path=tmp_path / "feedback.json",
    )

    assert summary["total_rows"] == 1
    assert summary["rows"][0]["score"] == ""


def test_render_review_history_calibration_aggregates_multiday_feedback(tmp_path) -> None:
    history_path = tmp_path / "jibi_review_board_history.jsonl"
    candidates_path = tmp_path / "candidates.jsonl"
    onion_url = "https://www.korea.kr/briefing/pressReleaseView.do?newsId=156763248"
    platform_url = "https://www.yna.co.kr/view/AKR20260522000100017"
    payloads = [
        {
            "run_date": "2026-05-22",
            "created_at": "2026-05-22T00:00:00+00:00",
            "rows": [
                {
                    "날짜": "2026-05-22",
                    "제목": "양파가 너무 많으면 정부는 무엇을 하나",
                    "메인 링크": onion_url,
                    "리뷰-성원": "reject — 보도자료 느낌",
                    "ID": "2026-05-22:story_bundle_onion",
                    "story_fingerprint": "onion_story",
                }
            ],
        },
        {
            "run_date": "2026-05-23",
            "created_at": "2026-05-23T00:00:00+00:00",
            "rows": [
                {
                    "날짜": "2026-05-23",
                    "제목": "양파가 너무 많으면 정부는 무엇을 하나",
                    "메인 링크": onion_url,
                    "리뷰-동찬": "needs — 가격 데이터 필요",
                    "ID": "2026-05-23:story_bundle_onion",
                    "story_fingerprint": "onion_story",
                },
                {
                    "날짜": "2026-05-23",
                    "제목": "무료배달은 누가 내나",
                    "메인 링크": platform_url,
                    "리뷰-성원": "seed — 업주 부담 구조 가능",
                    "리뷰-형찬": "reject — 아직 단일 기사",
                    "ID": "2026-05-23:story_bundle_platform",
                    "story_fingerprint": "platform_story",
                },
            ],
        },
    ]
    history_path.write_text(
        "\n".join(json.dumps(item, ensure_ascii=False) for item in payloads) + "\n",
        encoding="utf-8",
    )
    candidates_path.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "seed_url": onion_url,
                        "source": "정책브리핑",
                        "source_role_class": "policy_release",
                        "seed_type": "policy_release_seed",
                    },
                    ensure_ascii=False,
                ),
                json.dumps(
                    {
                        "seed_url": platform_url,
                        "source": "연합뉴스 산업",
                        "source_role_class": "public_wire",
                        "seed_type": "platform_labor_market",
                    },
                    ensure_ascii=False,
                ),
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    outputs, summary = render_review_history_calibration(
        history_path=history_path,
        candidates_path=candidates_path,
        run_date="2026-05-23",
        markdown_path=tmp_path / "calibration.md",
        json_path=tmp_path / "calibration.json",
    )

    assert outputs.markdown_path.exists()
    assert summary["total_rows"] == 3
    assert summary["tag_counts"]["reject"] == 2
    assert summary["tag_counts"]["needs"] == 1
    assert summary["tag_counts"]["seed"] == 1
    source_keys = {item["key"] for item in summary["source_feedback"]}
    assert {"정책브리핑", "연합뉴스 산업"}.issubset(source_keys)
    seed_type_keys = {item["key"] for item in summary["seed_type_feedback"]}
    assert {"policy_release_seed", "platform_labor_market"}.issubset(seed_type_keys)
    onion = next(
        item
        for item in summary["story_reappearance"]
        if item["story_fingerprint"] == "onion_story"
    )
    assert onion["appearances"] == 2
    assert summary["strong_disagreement_rows"][0]["reason"] == "seed_vs_reject"
    report = outputs.markdown_path.read_text(encoding="utf-8")
    assert "Source-Level Feedback Summary" in report
    assert "Report-Only Recommendations" in report
