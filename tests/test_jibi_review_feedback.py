import csv
import json

from luddite.agents.jibi.append_to_sheet import BUNDLE_REVIEW_SHEET_COLUMNS
from luddite.agents.jibi.review_feedback import (
    parse_review_tag,
    render_review_feedback_summary,
    summarize_review_feedback,
)


def _write_review_board(path, rows):
    with path.open("w", encoding="utf-8-sig", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=BUNDLE_REVIEW_SHEET_COLUMNS)
        writer.writeheader()
        for row in rows:
            payload = {column: "" for column in BUNDLE_REVIEW_SHEET_COLUMNS}
            payload.update(row)
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
