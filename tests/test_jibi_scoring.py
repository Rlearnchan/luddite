from luddite.agents.jibi.normalize_candidates import normalize_article
from luddite.agents.jibi.score_candidates import (
    annotate_near_duplicates,
    score_candidate,
    score_candidates,
)
from luddite.utils.jsonl import write_jsonl


def test_score_candidate_rejects_direct_president_party_evaluation() -> None:
    candidate = {
        "candidate_id": "jibi_1",
        "title": "대통령 발언 직후 증시 급등락",
        "summary": "속보성 정치/시장 뉴스",
        "why_interesting": "숫자는 있지만 정치 민감도 높음",
        "risk_flags": ["political_sensitivity", "investment_advice_risk"],
        "published_at": "2026-05-17",
        "evidence_depth_hint": "medium",
    }

    scored = score_candidate(candidate)

    assert scored["recommended_action"] == "reject"
    assert scored["blocked_reason"] == "direct_president_party_evaluation"
    assert scored["risk_level"] == "high"
    assert "total_score" in scored["scores"]
    assert scored["scores"]["weights"]["broadcast_potential_proxy"] == 25
    assert "political_direct_eval" in scored["failure_modes"]


def test_score_candidate_keeps_overseas_political_fracture_out_of_hard_reject() -> None:
    candidate = {
        "candidate_id": "jibi_uk_reform",
        "title": "영국 양당 지지율 동반 하락과 개혁당 부상",
        "summary": "포퓰리즘, 지역 격차, 이민, 노동자 계층 이동으로 확장 가능",
        "why_interesting": "해외 정치 균열을 경제/사회 구조로 볼 수 있음",
        "risk_flags": ["political_sensitivity"],
        "published_at": "2026-05-17",
        "evidence_depth_hint": "medium",
        "possible_expansions": [
            "포퓰리즘과 지역 격차",
            "이민 이슈와 노동자 계층 이동",
            "채권시장과 정책 불확실성",
        ],
    }

    scored = score_candidate(candidate)

    assert scored["blocked_reason"] is None
    assert scored["final_grade"] in {"B", "C"}
    assert scored["recommended_action"] in {"editorial_review", "gather_more_evidence"}
    assert "political_direct_eval" not in scored["failure_modes"]


def test_score_candidate_sends_strong_sensitive_nonpolitical_to_editorial_review() -> None:
    candidate = {
        "candidate_id": "jibi_hippo",
        "title": "콜롬비아 마약왕의 하마, 살처분 대신 인도행?",
        "summary": "이상한 동물 뉴스 hook과 인도 소비재 시장 확장",
        "why_interesting": "엥? hook과 구조 확장",
        "risk_flags": ["crime_or_drug_sensitivity"],
        "published_at": "2026-05-17",
        "evidence_depth_hint": "medium",
    }

    scored = score_candidate(candidate)

    assert scored["final_grade"] in {"A", "B", "C"}
    assert scored["risk_level"] == "high"
    assert scored["recommended_action"] == "editorial_review"


def test_score_candidate_gathers_more_evidence_for_strong_hook_with_weak_evidence() -> None:
    candidate = {
        "candidate_id": "jibi_need_sources",
        "title": "이상한 전당포 밈이 갑자기 유행",
        "summary": "엥? hook은 강하지만 근거가 부족",
        "why_interesting": "엥? hook",
        "risk_flags": [],
        "published_at": "2026-05-17",
        "evidence_depth_hint": "low",
    }

    scored = score_candidate(candidate)

    assert scored["recommended_action"] == "gather_more_evidence"
    assert scored["recommended_action"] != "send_to_anny"
    assert "thin_evidence" in scored["failure_modes"]


def test_score_candidate_gathers_more_evidence_for_investment_risk() -> None:
    candidate = {
        "candidate_id": "jibi_f88",
        "title": "베트남 전당포 F88, 메인 증시 이전 상장 추진",
        "summary": "전당포 상장과 신흥국 금융시장 구조",
        "why_interesting": "엥? hook과 구조 확장",
        "risk_flags": ["investment_advice_risk"],
        "published_at": "2026-05-17",
        "evidence_depth_hint": "medium",
    }

    scored = score_candidate(candidate)

    assert scored["recommended_action"] == "gather_more_evidence"


def test_score_candidate_only_sends_to_anny_when_evidence_is_ready() -> None:
    candidate = {
        "candidate_id": "jibi_drone_ready",
        "title": "300달러 드론을 수백만 달러 미사일로 막는 비용 역전",
        "seed_url": "https://example.com/drone-cost",
        "summary": "우크라이나 전장과 방공 비용 구조를 숫자로 비교",
        "why_interesting": "값싼 드론과 비싼 방어 수단의 비용 교환비가 핵심",
        "risk_flags": [],
        "published_at": "2026-05-17",
        "evidence_depth_hint": "high",
        "source_count": 2,
        "possible_expansions": [
            "우크라이나/중동 전장에서 드론이 비용 구조를 바꾼 사례",
            "싼 공격 수단을 비싼 미사일로 막는 방어자 딜레마",
            "레이저/전자전/그물총 같은 저비용 대응책 경쟁",
        ],
        "evidence_needed": ["방산 지출 비교 수치의 최신 연도 확인"],
    }

    scored = score_candidate(candidate)

    assert scored["recommended_action"] == "send_to_anny"


def test_score_candidate_keeps_no_ai_label_out_of_hard_reject() -> None:
    candidate = {
        "candidate_id": "jibi_no_ai_label",
        "title": "AI 미사용 라벨을 붙이는 브랜드들",
        "seed_url": "https://example.com/no-ai",
        "summary": "AI slop 피로감과 진정성 마케팅",
        "why_interesting": "AI 표기 규제와 창작자 반발로 확장 가능",
        "risk_flags": ["corporate_promo_risk"],
        "published_at": "2026-05-17",
        "evidence_depth_hint": "medium",
        "possible_expansions": [
            "AI slop 범람과 소비자 피로감",
            "진정성 마케팅과 AI 미사용 라벨",
            "AI 표기 규제와 창작자 반발",
        ],
    }

    scored = score_candidate(candidate)

    assert scored["blocked_reason"] is None
    assert scored["recommended_action"] in {"gather_more_evidence", "keep_for_later"}


def test_score_candidate_fills_empty_possible_expansions() -> None:
    candidate = {
        "candidate_id": "jibi_heat",
        "title": "5월 폭염에 회사 반바지 논쟁",
        "summary": "오피스 복장과 전력 수요 변화",
        "why_interesting": "생활 체감형 소재",
        "risk_flags": [],
        "published_at": "2026-05-17",
        "evidence_depth_hint": "medium",
        "possible_expansions": [],
    }

    scored = score_candidate(candidate)

    assert len(scored["possible_expansions"]) >= 3


def test_policy_release_evidence_default_is_kept_for_later() -> None:
    candidate = normalize_article(
        {
            "article_id": "article_policy_plain_scoring",
            "title": "[문화체육관광부] 국제문화교류 활성화 방안 논의",
            "url": "https://www.korea.kr/briefing/pressReleaseView.do?newsId=plain",
            "source": "정책브리핑",
            "source_id": "korea_policy_briefing",
            "published_at": "2026-05-23T00:00:00Z",
            "collected_at": "2026-05-23T01:00:00+00:00",
            "raw_summary": "관계기관 회의에서 향후 협력 방향을 논의했다.",
            "collector": "rss",
            "tags": ["rss", "official_evidence"],
        }
    )

    scored = score_candidate(candidate)

    assert "policy_release_evidence_default" in scored["quality_flags"]
    assert scored["recommended_action"] == "keep_for_later"
    assert "policy_release_evidence_default" in scored["failure_modes"]


def test_score_candidates_sorts_by_total_score(tmp_path) -> None:
    input_path = tmp_path / "candidates.jsonl"
    output_path = tmp_path / "scored.jsonl"
    write_jsonl(
        input_path,
        [
            {
                "candidate_id": "low",
                "title": "단순 신제품 출시",
                "summary": "",
                "why_interesting": "",
                "risk_flags": ["corporate_promo_risk"],
            },
            {
                "candidate_id": "high",
                "title": "300달러 드론을 수백만 달러 미사일로 막는 비용 역전",
                "summary": "시장 구조와 숫자",
                "why_interesting": "엥? hook과 구조 확장",
                "risk_flags": [],
            },
        ],
    )

    scored = score_candidates(input_path=input_path, output_path=output_path)

    assert scored[0]["candidate_id"] == "high"
    assert output_path.exists()


def test_score_candidate_adds_story_specificity_when_missing() -> None:
    scored = score_candidate(
        {
            "candidate_id": "specific",
            "title": "Google spends $2B as AI search costs pressure schools",
            "summary": "A concrete funding mechanism creates tension for education.",
            "why_interesting": "사건 자체보다 배경, 이해관계자 연결고리가 있는지 확인",
            "risk_flags": [],
            "quality_flags": [],
            "evidence_depth_hint": "medium",
        }
    )

    assert scored["story_specificity"]["level"] in {"medium", "high"}
    assert scored["story_specificity"]["generic_why_detected"] is True


def test_near_duplicate_same_source_title_groups_as_duplicate() -> None:
    candidates = [
        {
            "candidate_id": "primary",
            "title": "Drone defense costs surge as cheap drones spread",
            "source": "BBC News",
            "scores": {"total_score": 80},
        },
        {
            "candidate_id": "duplicate",
            "title": "Drone defense costs surge as cheap drones spread",
            "source": "BBC News",
            "scores": {"total_score": 70},
        },
    ]

    grouped = annotate_near_duplicates(candidates)

    assert grouped[0]["near_duplicate_role"] == "primary"
    assert grouped[1]["near_duplicate_role"] == "duplicate"
    assert grouped[0]["near_duplicate_group_id"] == grouped[1]["near_duplicate_group_id"]


def test_near_duplicate_cross_source_groups_as_supporting_source() -> None:
    candidates = [
        {
            "candidate_id": "primary",
            "title": "Drone defense costs surge as cheap drones spread",
            "source": "BBC News",
            "scores": {"total_score": 80},
        },
        {
            "candidate_id": "supporting",
            "title": "Cheap drones spread as drone defense costs surge",
            "source": "NPR",
            "scores": {"total_score": 70},
        },
    ]

    grouped = annotate_near_duplicates(candidates)

    assert grouped[0]["near_duplicate_role"] == "primary"
    assert grouped[1]["near_duplicate_role"] == "supporting_source"
    assert grouped[1]["near_duplicate_shared_tokens"] >= 3
    assert grouped[1]["near_duplicate_title_overlap"] >= 0.8


def test_broad_generic_titles_do_not_collapse() -> None:
    candidates = [
        {
            "candidate_id": "ai_market",
            "title": "AI stocks rise",
            "source": "BBC News",
            "scores": {"total_score": 80},
        },
        {
            "candidate_id": "ai_school",
            "title": "AI changes schools",
            "source": "NPR",
            "scores": {"total_score": 70},
        },
    ]

    grouped = annotate_near_duplicates(candidates)

    assert grouped[0]["near_duplicate_role"] == "none"
    assert grouped[1]["near_duplicate_role"] == "none"


def test_korean_reordered_high_overlap_titles_collapse_when_strong() -> None:
    candidates = [
        {
            "candidate_id": "primary",
            "title": "AI 학교 현장 비용 변화",
            "source": "한국경제",
            "scores": {"total_score": 80},
        },
        {
            "candidate_id": "supporting",
            "title": "학교 현장 비용 변화 AI",
            "source": "연합뉴스",
            "scores": {"total_score": 70},
        },
    ]

    grouped = annotate_near_duplicates(candidates)

    assert grouped[0]["near_duplicate_role"] == "primary"
    assert grouped[1]["near_duplicate_role"] == "supporting_source"
    assert grouped[1]["near_duplicate_shared_tokens"] == 5
    assert grouped[1]["near_duplicate_title_overlap"] == 1.0


def test_korean_broad_same_topic_titles_do_not_collapse() -> None:
    candidates = [
        {
            "candidate_id": "school_ai",
            "title": "AI 학교 수업 변화",
            "source": "한국경제",
            "scores": {"total_score": 80},
        },
        {
            "candidate_id": "finance_ai",
            "title": "AI 금융 시장 변화",
            "source": "연합뉴스",
            "scores": {"total_score": 70},
        },
    ]

    grouped = annotate_near_duplicates(candidates)

    assert grouped[0]["near_duplicate_role"] == "none"
    assert grouped[1]["near_duplicate_role"] == "none"


def test_near_duplicate_primary_is_highest_scoring_candidate() -> None:
    candidates = [
        {
            "candidate_id": "lower_first",
            "title": "Drone defense costs surge as cheap drones spread",
            "source": "BBC News",
            "scores": {"total_score": 70},
        },
        {
            "candidate_id": "higher_second",
            "title": "Cheap drones spread as drone defense costs surge",
            "source": "NPR",
            "scores": {"total_score": 90},
        },
    ]

    grouped = annotate_near_duplicates(candidates)
    by_id = {item["candidate_id"]: item for item in grouped}

    assert by_id["higher_second"]["near_duplicate_role"] == "primary"
    assert by_id["lower_first"]["near_duplicate_role"] == "supporting_source"


def test_rss_bbc_sport_item_is_quality_gated() -> None:
    candidate = {
        "candidate_id": "bbc_sport",
        "source_id": "bbc_rss_candidate",
        "source": "BBC News",
        "seed_url": "https://www.bbc.com/sport/golf/articles/abc",
        "title": "Golfer wins championship",
        "summary": "A match report from the tournament.",
        "risk_flags": [],
        "quality_flags": ["sports_only"],
        "evidence_depth_hint": "medium",
    }

    scored = score_candidate(candidate)

    assert scored["recommended_action"] == "reject"
    assert "rss_sports_only" in scored["failure_modes"]
    assert scored["scores"]["total_score"] < 35


def test_atlas_pure_place_listing_is_downranked() -> None:
    candidate = {
        "candidate_id": "atlas_place",
        "source_id": "atlas_obscura",
        "source": "Atlas Obscura",
        "title": "Old Walking Trail in Somewhere",
        "summary": "A short place listing.",
        "risk_flags": [],
        "quality_flags": ["pure_place_listing"],
        "evidence_depth_hint": "medium",
    }

    scored = score_candidate(candidate)

    assert scored["recommended_action"] == "keep_for_later"
    assert scored["final_grade"] in {"C", "D"}
    assert "pure_place_listing" in scored["failure_modes"]


def test_accident_single_event_is_not_top_candidate_material() -> None:
    candidate = {
        "candidate_id": "accident",
        "title": "Train stabbing injures passengers",
        "summary": "A single event accident report.",
        "risk_flags": [],
        "quality_flags": ["accident_single_event"],
        "evidence_depth_hint": "medium",
    }

    scored = score_candidate(candidate)

    assert scored["recommended_action"] == "reject"
    assert "single_event_accident" in scored["failure_modes"]


def test_empty_summary_lowers_evidence_depth() -> None:
    candidate = {
        "candidate_id": "empty_summary",
        "title": "AI infrastructure investment expands",
        "summary": "",
        "risk_flags": [],
        "quality_flags": ["empty_summary"],
        "evidence_depth_hint": "medium",
    }

    scored = score_candidate(candidate)

    assert scored["scores"]["evidence_depth"] == 1
    assert "thin_evidence" in scored["failure_modes"]


def test_stale_rss_item_is_downranked_and_not_top_material() -> None:
    candidate = {
        "candidate_id": "stale_rss",
        "title": "Old RSS item about an infrastructure dispute",
        "summary": "A stale feed item with limited current relevance.",
        "risk_flags": [],
        "quality_flags": ["stale_item"],
        "freshness_status": "stale",
        "evidence_depth_hint": "medium",
    }

    scored = score_candidate(candidate)

    assert scored["recommended_action"] == "keep_for_later"
    assert scored["scores"]["timeliness"] == 1
    assert "stale_rss_item" in scored["failure_modes"]


def test_single_company_financing_is_not_low_risk_b() -> None:
    candidate = {
        "candidate_id": "skc_like",
        "title": "SKC, 1.2조 유상증자 초과 청약",
        "summary": "글라스기판 투자와 재무개선 실탄 확보.",
        "seed_type": "single_company_financing",
        "risk_flags": ["corporate_promo_risk", "investment_advice_risk"],
        "quality_flags": ["single_company_frame", "single_stock_or_asset_frame"],
        "evidence_depth_hint": "medium",
        "why_interesting": "단일 기업 유상증자 뉴스로 끝내면 약함",
    }

    scored = score_candidate(candidate)

    assert scored["recommended_action"] in {"editorial_review", "keep_for_later"}
    assert scored["risk_level"] == "medium"
    assert scored["final_grade"] in {"C", "D"}
    assert "single_company_frame" in scored["failure_modes"]


def test_trump_policy_item_has_political_risk() -> None:
    candidate = {
        "candidate_id": "wildfire_policy",
        "title": "Trump's battle with immigration and DEI is impacting forest fires",
        "summary": "Federal wildfire policy is being reshaped by political conflict.",
        "seed_type": "climate_policy_conflict",
        "risk_flags": ["political_sensitivity"],
        "quality_flags": ["live_politics_or_statement"],
        "evidence_depth_hint": "medium",
    }

    scored = score_candidate(candidate)

    assert scored["recommended_action"] == "editorial_review"
    assert scored["risk_level"] in {"medium", "high"}
    assert "live_news_volatility" in scored["failure_modes"]


def test_promo_bulletin_guard_flags_ai_shortform_contest() -> None:
    candidate = normalize_article(
        {
            "article_id": "article_ai_shortform_contest",
            "title": "중진공, 전 국민 대상 '청렴한 중진공 AI+ 숏폼 공모전'",
            "url": "https://www.korea.kr/briefing/pressReleaseView.do?newsId=contest",
            "source": "정책브리핑",
            "source_id": "korea_policy_briefing",
            "published_at": "2026-05-25T00:00:00Z",
            "collected_at": "2026-05-25T01:00:00+00:00",
            "raw_summary": "공모전을 개최한다고 밝혔다.",
            "collector": "rss",
            "tags": ["rss"],
        }
    )

    scored = score_candidate(candidate)

    assert "contest_or_campaign_bulletin" in scored["quality_flags"]
    assert scored["so_what"]["so_what_label"] == "weak"
    assert scored["seed_quality_classification"] == "reject_or_downrank"
    assert scored["recommended_action"] == "keep_for_later"


def test_starbucks_prepaid_balance_is_conditional_not_reject() -> None:
    candidate = normalize_article(
        {
            "article_id": "article_starbucks_prepaid",
            "title": "'환불요구' 스벅 선불충전금…4천200억원 넘어도 규제 사각지대",
            "url": "https://www.yna.co.kr/view/AKR20260525000100002",
            "source": "연합뉴스 경제",
            "source_id": "yonhap_economy",
            "published_at": "2026-05-25T00:00:00Z",
            "collected_at": "2026-05-25T01:00:00+00:00",
            "raw_summary": "소비자 선불충전금과 환불, 규제 사각지대 문제가 제기됐다.",
            "collector": "rss",
            "tags": ["rss"],
        }
    )

    scored = score_candidate(candidate)

    assert scored["so_what"]["so_what_label"] in {"strong", "conditional"}
    assert scored["seed_quality_classification"] == "conditional_seed"
    assert "consumer_funds_or_regulation_gap" in scored["so_what"]["audience_bridge_signals"]
    assert scored["recommended_action"] != "reject"


def test_bok_youth_labor_has_strong_so_what() -> None:
    candidate = normalize_article(
        {
            "article_id": "article_bok_youth",
            "title": "‘쉬었음’ 청년층의 특징 및 평가",
            "url": "https://www.bok.or.kr/portal/bbs/P0002353/view.do?nttId=youth",
            "source": "한국은행",
            "source_id": "bok",
            "published_at": "2026-05-25T00:00:00Z",
            "collected_at": "2026-05-25T01:00:00+00:00",
            "raw_summary": "청년 노동시장 이탈과 경제활동참가율 변화를 통계로 분석한다.",
            "collector": "rss",
            "tags": ["rss"],
        }
    )

    scored = score_candidate(candidate)

    assert scored["so_what"]["so_what_label"] == "strong"
    assert scored["seed_quality_classification"] == "standalone_seed"
    assert scored["story_role"] == "standalone_seed"
    assert "job_workplace_labor_change" in scored["so_what"]["audience_bridge_signals"]


def test_asset_tokenization_is_conditional_audience_bridge() -> None:
    candidate = normalize_article(
        {
            "article_id": "article_bok_tokenization",
            "title": "국내외 자산 토큰화 현황 및 향후 정책 과제",
            "url": "https://www.bok.or.kr/portal/bbs/P0002353/view.do?nttId=token",
            "source": "한국은행",
            "source_id": "bok",
            "published_at": "2026-05-25T00:00:00Z",
            "collected_at": "2026-05-25T01:00:00+00:00",
            "raw_summary": "현실 자산 권리를 디지털 토큰으로 기록하고 거래하는 제도 과제를 다룬다.",
            "collector": "rss",
            "tags": ["rss"],
        }
    )

    scored = score_candidate(candidate)

    assert scored["so_what"]["so_what_label"] in {"conditional", "strong"}
    assert scored["seed_quality_classification"] == "conditional_seed"
    assert scored["story_role"] == "seed_with_supporting_links"
    assert "research_note_needs_current_news_hook" in scored["seed_quality_reasons"]
    assert "distinctive_mechanism" in scored["so_what"]["audience_bridge_signals"]
