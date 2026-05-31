import csv
import json

from luddite.agents.jibi.append_to_sheet import BUNDLE_REVIEW_SHEET_COLUMNS
from luddite.agents.jibi.review_feedback import (
    _rows_from_values,
    historical_broadcast_usage_status,
    historical_production_status,
    historical_selection_label,
    infer_review_feedback,
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


def test_rows_from_values_finds_review_board_header_below_intro() -> None:
    values = [
        ["안녕하세요. Jibi입니다."],
        ["오늘 후보 안내"],
        [""],
        BUNDLE_REVIEW_SHEET_COLUMNS,
        [
            "2026-05-27 09:00",
            "AI가 공무원 보고서와 현장 치안에 들어올 때",
            "B · 68점",
            "https://example.com/main",
            "",
            "공공 현장 AI 후보",
            "",
            "",
            "",
            "좋음",
            "2026-05-27:story_bundle_ai",
        ],
    ]

    rows = _rows_from_values(values)

    assert len(rows) == 1
    assert rows[0]["제목"] == "AI가 공무원 보고서와 현장 치안에 들어올 때"
    assert rows[0]["리뷰-형찬"] == "좋음"


def test_infer_review_feedback_understands_natural_korean_notes() -> None:
    good = infer_review_feedback(
        "좋은 자료 선정. 다만 이미 과거 영상에서 다룬 바 있어 겹침 확인 필요"
    )
    assert good["explicit_tag"] == "unlabeled"
    assert good["inferred_label"] == "past_topic_overlap"
    assert good["primary_inferred_label"] == "seed"
    assert "past_topic_overlap" in good["modifiers"]
    assert good["tag"] == "seed"
    assert good["raw_note"].startswith("좋은 자료 선정")

    conditional = infer_review_feedback(
        "가능성 있음. 선불충전금 제도의 문제로 풀면 좋지만 단일기업이라 묶으면 좋겠음"
    )
    assert conditional["inferred_label"] == "conditional_seed"
    assert conditional["primary_inferred_label"] == "conditional_seed"
    assert {"bundle_needed", "single_company_case", "system_issue"}.issubset(
        set(conditional["modifiers"])
    )
    assert conditional["tag"] == "seed"

    reject = infer_review_feedback("그래서 뭐? 사람들이 안 궁금해할 것 같고 seed로 약함")
    assert reject["inferred_label"] == "reject"
    assert reject["tag"] == "reject"

    neutral = infer_review_feedback("조금 더 생각해보겠습니다")
    assert neutral["inferred_label"] in {"unlabeled", "unclear"}

    not_overlap = infer_review_feedback("이미 자료를 조금 봤는데 아직 판단은 어려움")
    assert "past_topic_overlap" not in not_overlap["modifiers"]


def test_infer_review_feedback_extracts_operator_failure_modes() -> None:
    needs_links = infer_review_feedback(
        "이거 하나만 가져오면 자료로 만들 수가 없다. "
        "관련된 실제 사례 중 뭐라도 참신한 것을 가져와야 한다."
    )
    assert "needs_supporting_links" in needs_links["failure_modes"]
    assert "specific_case_needed" in needs_links["positive_signals"]
    assert needs_links["review_signal"] in {"weak", "conditional"}
    assert "find_supporting_links" in needs_links["next_research_actions"]

    textbook = infer_review_feedback(
        "이것만 가져오면 그냥 한국은행 선생님들의 강의가 되어버린다. "
        "교과서같은 이론 공부 말고 최신 기사가 필요하다."
    )
    assert "evidence_not_seed" in textbook["failure_modes"]
    assert "needs_news_hook" in textbook["failure_modes"]
    assert "find_current_news_hook" in textbook["next_research_actions"]

    concrete = infer_review_feedback(
        "원인을 두루두루 설명하지 말고 가장 신기한 원인 하나를 뽑아 집중적으로 얘기해줘야 한다."
    )
    assert "needs_concrete_question" in concrete["failure_modes"]
    assert "narrow_to_concrete_question" in concrete["next_research_actions"]

    wrong_frame = infer_review_feedback(
        "초점은 일본 메가뱅크의 해외 투자가 아니라 미국 제조업 부흥으로 옮겨져야 한다."
    )
    assert "wrong_frame" in wrong_frame["failure_modes"]
    assert "reframe_around_stronger_real_economy_angle" in wrong_frame[
        "next_research_actions"
    ]

    good_question = infer_review_feedback(
        "좋다. 이런 질문거리를 던지는 것이 제일 좋다. GOOD!"
    )
    assert "good_question" in good_question["positive_signals"]
    assert good_question["review_signal"] == "strong"
    assert "keep_question_as_editorial_anchor" in good_question[
        "next_research_actions"
    ]


def test_historical_selection_keeps_production_and_usage_separate() -> None:
    row = {
        "제작 여부": "제작",
        "방송 활용 여부": "미사용",
        "이유": "제작은 했지만 방송 흐름에서 사용되지 않음",
    }

    assert historical_production_status(row) == "produced"
    assert historical_broadcast_usage_status(row) == "not_used"
    assert historical_selection_label(row) == "produced_not_used"


def test_historical_production_status_handles_korean_negative_phrases() -> None:
    for phrase in ["제작하지 않았다", "제작 못함", "제작 불발"]:
        row = {"제작 여부": phrase, "이유": phrase}
        assert historical_production_status(row) == "not_produced"


def test_historical_broadcast_usage_status_handles_korean_negative_phrases() -> None:
    for phrase in ["사용하지 않았다", "활용하지 않았다", "방송에서 쓰지 않았다"]:
        row = {"방송 활용 여부": phrase, "이유": phrase}
        assert historical_broadcast_usage_status(row) == "not_used"


def test_historical_production_status_does_not_treat_planned_as_produced() -> None:
    row = {"제작 여부": "제작 예정", "이유": "다음 주 제작 예정"}

    assert historical_production_status(row) == "unknown"
    assert historical_selection_label(row) == "unknown"


def test_infer_review_feedback_extracts_today_editorial_roles() -> None:
    hook = infer_review_feedback("기사 자체는 나쁘지 않음. 초반 후킹용으로 한 단 정도 가능")
    assert hook["review_signal"] == "conditional"
    assert "hook_only" in hook["review_adjustments"]
    assert hook["editorial_role"] == "hook_only"

    sports = infer_review_feedback(
        "스포츠는 되도록 가져오지 말자. 축구 관심 없는 사람에게는 조회수 나쁜 편."
    )
    assert "weak_audience_bridge" in sports["failure_modes"]
    assert "sports_primary_downrank" in sports["review_adjustments"]
    assert sports["editorial_role"] == "suppress"

    ai_casual = infer_review_feedback(
        "AI 거대담론이나 저작권 논쟁으로 몰고가지 말라. 그냥 편하게 즐긴다 쪽이 좋음."
    )
    assert "ai_grand_discourse_downrank" in ai_casual["review_adjustments"]
    assert "casual_ai_use_case_bonus" in ai_casual["review_adjustments"]
    assert ai_casual["editorial_role"] == "sub_block"

    sub_block = infer_review_feedback("한 페이지 예시로 넣을 수 있음. 나쁘지 않다.")
    assert "sub_block" in sub_block["review_adjustments"]
    assert sub_block["editorial_role"] == "sub_block"

    old = infer_review_feedback("뒷북이고 이미 했던 내용이라 novelty 없다. 새 각도 필요")
    assert "too_familiar" in old["failure_modes"]
    assert "past_topic_overlap_downrank" in old["review_adjustments"]
    assert "needs_new_angle" in old["review_adjustments"]


def test_explicit_tag_wins_over_inferred_review_text() -> None:
    payload = infer_review_feedback("seed — 홍보성이라 약하지만 구조로 풀면 가능")

    assert payload["explicit_tag"] == "seed"
    assert payload["inferred_label"] == "seed"
    assert payload["tag"] == "seed"


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


def test_summarize_review_feedback_counts_inferred_disagreements() -> None:
    rows = [
        {
            "일시": "2026-05-25 09:30",
            "제목": "스타벅스 선불충전금",
            "리뷰-성원": "가능성 있음. 제도의 문제로 풀면 좋은데 단일기업이라 묶으면 좋겠음",
            "리뷰-형찬": "그래서 뭐? 단발성 회사 기사로는 약함",
            "ID": "2026-05-25:story_bundle_starbucks",
        }
    ]

    summary = summarize_review_feedback(rows, run_date="2026-05-25")

    assert summary["tag_counts"]["seed"] == 1
    assert summary["tag_counts"]["reject"] == 1
    assert summary["inferred_label_counts"]["conditional_seed"] == 1
    assert summary["inferred_label_counts"]["reject"] == 1
    assert summary["primary_label_counts"]["conditional_seed"] == 1
    assert summary["modifier_counts"]["single_company_case"] >= 1
    assert summary["disagreement_rows"][0]["inferred"] is True


def test_summarize_review_feedback_adds_row_operator_lessons() -> None:
    rows = [
        {
            "일시": "2026-05-25 21:42",
            "제목": "전기·가스요금 지원에 72% 찬성",
            "리뷰-동찬": (
                "좋다. '정부는 요금을 깎아줘야 하나' "
                "이런 질문거리를 던지는 것이 제일 좋다. GOOD!"
            ),
            "리뷰-형찬": "새로운 게 별로 없어보임. 살짝 언급할 정도로 사용?",
            "ID": "2026-05-25:story_bundle_energy",
        },
        {
            "일시": "2026-05-25 21:42",
            "제목": "글로벌 PF 대출 5년새 2배",
            "리뷰-동찬": (
                "초점은 일본 메가뱅크의 해외 투자 아닌 미국 제조업 부흥으로 옮겨져야 한다."
            ),
            "ID": "2026-05-25:story_bundle_pf",
        },
    ]

    summary = summarize_review_feedback(rows, run_date="2026-05-25")

    assert summary["failure_mode_counts"]["wrong_frame"] == 1
    assert summary["positive_signal_counts"]["good_question"] == 1
    assert summary["next_research_action_counts"][
        "reframe_around_stronger_real_economy_angle"
    ] == 1
    assert summary["rows"][0]["row_review_signal"] == "conditional"
    assert "good_question" in summary["rows"][0]["row_positive_signals"]
    assert "keep_question_as_editorial_anchor" in summary["rows"][0][
        "row_next_research_actions"
    ]
    assert summary["rows"][1]["row_review_signal"] == "weak"
    assert "wrong_frame" in summary["rows"][1]["row_failure_modes"]
    assert "초점" in summary["rows"][1]["operator_lesson"]


def test_summarize_review_feedback_adds_today_editorial_role_counts() -> None:
    rows = [
        {
            "일시": "2026-05-27 09:00",
            "제목": "축구 이벤트 경제",
            "리뷰-형찬": "스포츠는 되도록 가져오지 말자. 조회수 나쁜 편.",
            "ID": "2026-05-27:story_bundle_sports",
        },
        {
            "일시": "2026-05-27 09:00",
            "제목": "AI 영상 여행",
            "리뷰-동찬": "AI 거대담론으로 몰고가지 말고 그냥 편하게 즐긴다 사례로 한 페이지 예시.",
            "ID": "2026-05-27:story_bundle_ai_video",
        },
    ]

    summary = summarize_review_feedback(rows, run_date="2026-05-27")

    assert summary["review_adjustment_counts"]["sports_primary_downrank"] == 1
    assert summary["review_adjustment_counts"]["ai_grand_discourse_downrank"] == 1
    assert summary["review_adjustment_counts"]["casual_ai_use_case_bonus"] == 1
    assert summary["editorial_role_counts"]["suppress"] == 1
    assert summary["editorial_role_counts"]["sub_block"] == 1
    assert summary["rows"][0]["editorial_role"] == "suppress"
    assert summary["rows"][1]["editorial_role"] == "sub_block"


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
    report = output_md.read_text(encoding="utf-8")
    assert "## Operator Lessons" in report
    assert "## Failure Mode Counts" in report
    assert "## Next Research Actions" in report
    payload = json.loads(output_json.read_text(encoding="utf-8"))
    assert payload["rows"][0]["id"] == "2026-05-23:story_bundle_onion"
    assert "row_review_signal" in payload["rows"][0]


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
                    "제작 여부": "미제작",
                    "이유": "단일 기사라 확장성 부족",
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
                    "제작 여부": "제작",
                    "방송 활용 여부": "활용됨",
                    "이유": "플랫폼 숨은 비용은 슈카월드 래퍼토리와 맞음",
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
    assert summary["historical_outcome_counts"]["not_produced"] == 1
    assert summary["historical_outcome_counts"]["produced_and_used"] == 1
    assert summary["historical_production_status_counts"]["produced"] == 1
    assert summary["historical_production_status_counts"]["not_produced"] == 1
    assert summary["historical_broadcast_usage_status_counts"]["used"] == 1
    assert summary["historical_reason_counts"]["failed_because_no_story_expansion"] >= 1
    assert (
        summary["historical_reason_counts"]["worked_because_syuka_core_repertoire"]
        == 1
    )
    report = outputs.markdown_path.read_text(encoding="utf-8")
    assert "Source-Level Feedback Summary" in report
    assert "Historical Selection Outcomes" in report
    assert "Historical Production Status" in report
    assert "Historical Broadcast Usage Status" in report
    assert "Report-Only Recommendations" in report


def test_review_history_calibration_prefers_durable_row_metadata(tmp_path) -> None:
    history_path = tmp_path / "jibi_review_board_history.jsonl"
    candidates_path = tmp_path / "missing_candidates.jsonl"
    history_path.write_text(
        json.dumps(
            {
                "run_date": "2026-05-24",
                "created_at": "2026-05-24T00:00:00+00:00",
                "rows": [
                    {
                        "일시": "2026-05-24 09:30",
                        "제목": "공공 AI 도입",
                        "메인 링크": "https://www.yna.co.kr/view/AKR202605240001",
                        "리뷰-성원": "seed — 현장 사례로 좋음",
                        "ID": "2026-05-24:story_bundle_ai",
                        "story_fingerprint": "public_ai_adoption",
                        "source": "연합뉴스 산업",
                        "source_id": "yonhap_industry",
                        "source_role": "public_wire",
                        "seed_type": "public_ai_governance",
                        "bundle_type": "needs_external_sources",
                    }
                ],
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    _outputs, summary = render_review_history_calibration(
        history_path=history_path,
        candidates_path=candidates_path,
        run_date="2026-05-24",
        markdown_path=tmp_path / "calibration.md",
        json_path=tmp_path / "calibration.json",
    )

    assert summary["source_feedback"][0]["key"] == "연합뉴스 산업"
    assert summary["source_role_feedback"][0]["key"] == "public_wire"
    assert summary["seed_type_feedback"][0]["key"] == "public_ai_governance"
    assert summary["rows"][0]["source_role"] == "public_wire"
