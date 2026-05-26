from luddite.agents.jibi.normalize_candidates import (
    classify_freshness,
    infer_story_specificity,
    normalize_article,
    normalize_candidates,
)
from luddite.utils.jsonl import write_jsonl


def test_normalize_article_sets_risk_and_hints() -> None:
    article = {
        "article_id": "article_abc",
        "title": "콜롬비아 마약왕의 하마, 살처분 대신 인도행?",
        "url": "https://example.com/hippo",
        "source": "Manual Input",
        "source_id": "manual",
        "published_at": None,
        "collected_at": "2026-05-17T00:00:00+00:00",
        "language": "ko",
        "region": "global",
        "raw_summary": "이상한 동물 뉴스 hook",
        "collector": "manual",
        "tags": ["하마", "마약"],
    }

    candidate = normalize_article(article)

    assert candidate["candidate_id"] == "jibi_abc"
    assert candidate["seed_type"] == "absurd_foreign"
    assert "crime_or_drug_sensitivity" in candidate["risk_flags"]
    assert candidate["title_hook_hint"] == "high"
    assert len(candidate["possible_expansions"]) >= 3
    assert "코카인 하마" in candidate["why_interesting"]
    assert "제목에서 바로 엥?" not in candidate["why_interesting"]
    assert any("제목에서 바로 엥?" in reason for reason in candidate["score_reason"])
    assert candidate["story_specificity"]["level"] in {"low", "medium", "high"}


def test_normalize_article_does_not_overclassify_industry_disruption() -> None:
    article = {
        "article_id": "article_generic",
        "title": "Footballer recalls train stabbing attack",
        "url": "https://www.bbc.com/sport/football/articles/example",
        "source": "BBC News",
        "source_id": "bbc_rss_candidate",
        "published_at": "2026-05-18",
        "collected_at": "2026-05-18T00:00:00+00:00",
        "raw_summary": "A single personal recollection after an attack.",
        "tags": ["rss", "primary_wire", "seed_discovery"],
    }

    candidate = normalize_article(article)

    assert candidate["seed_type"] != "industry_disruption"
    assert "sports_only" in candidate["quality_flags"]


def test_normalize_article_keeps_real_drone_cost_asymmetry() -> None:
    article = {
        "article_id": "article_drone",
        "title": "Cheap drones force armies to use expensive interceptor missiles",
        "url": "https://example.com/drone",
        "source": "Manual",
        "source_id": "manual",
        "published_at": "2026-05-18",
        "collected_at": "2026-05-18T00:00:00+00:00",
        "raw_summary": "Low-cost attack drones are changing high-cost defense budgets.",
        "tags": ["rss"],
    }

    candidate = normalize_article(article)

    assert candidate["seed_type"] == "cost_asymmetry"


def test_classify_freshness_recent_stale_unknown() -> None:
    assert classify_freshness("2026-05-20T00:00:00Z", "2026-05-23T00:00:00Z") == (
        "recent",
        72.0,
    )
    assert classify_freshness("2026-05-01T00:00:00Z", "2026-05-23T00:00:00Z") == (
        "stale",
        528.0,
    )
    assert classify_freshness(None, "2026-05-23T00:00:00Z") == ("unknown", None)


def test_manual_unknown_freshness_is_not_quality_blocked() -> None:
    candidate = normalize_article(
        {
            "article_id": "article_manual_unknown",
            "title": "300달러 드론을 수백만 달러 미사일로 막는 비용 역전",
            "url": "https://example.com/drone",
            "source": "Manual Input",
            "source_id": "manual",
            "published_at": None,
            "collected_at": "2026-05-23T00:00:00+00:00",
            "raw_summary": "값싼 드론과 비싼 방공 미사일의 비용 구조",
            "collector": "manual",
            "tags": ["manual"],
        }
    )

    assert candidate["freshness_status"] == "unknown"
    assert candidate["age_hours"] is None
    assert "stale_item" not in candidate["quality_flags"]


def test_stale_rss_item_gets_quality_flag() -> None:
    candidate = normalize_article(
        {
            "article_id": "article_stale",
            "title": "Old local incident resurfaces in RSS",
            "url": "https://example.com/stale",
            "source": "BBC News",
            "source_id": "bbc_rss_candidate",
            "published_at": "2026-05-01T00:00:00Z",
            "collected_at": "2026-05-23T00:00:00+00:00",
            "raw_summary": "A thin old item with limited structure.",
            "collector": "rss",
            "tags": ["rss"],
        }
    )

    assert candidate["freshness_status"] == "stale"
    assert candidate["age_hours"] == 528.0
    assert "stale_item" in candidate["quality_flags"]


def test_bok_issue_note_uses_low_frequency_research_freshness_window() -> None:
    candidate = normalize_article(
        {
            "article_id": "article_bok_issue_note",
            "title": "[제2026-11호] 국내외 자산 토큰화 현황 및 향후 정책 과제",
            "url": "https://www.bok.or.kr/portal/bbs/P0002353/view.do?nttId=10097981",
            "source": "한국은행",
            "source_id": "bok",
            "published_at": "2026-05-14T03:00:00Z",
            "collected_at": "2026-05-23T00:00:00+00:00",
            "raw_summary": (
                "글로벌 자산 토큰화 시장 규모는 503.7억달러이며 "
                "제도적 기반이 마련되었다."
            ),
            "collector": "rss",
            "tags": ["rss", "official_evidence", "seed_and_numbers_evidence"],
        }
    )

    assert candidate["source_freshness_policy"] == "low_frequency_research"
    assert candidate["source_freshness_window_days"] == 90
    assert candidate["source_role_class"] == "research_note"
    assert candidate["freshness_status"] == "recent"
    assert candidate["research_publication_age_days"] == 8.9
    assert candidate["seed_type"] == "policy_research_note"
    assert "연구노트" in candidate["why_interesting"]
    assert "stale_item" not in candidate["quality_flags"]
    assert candidate["story_specificity"]["generic_why_detected"] is False


def test_conversation_spacex_explainer_is_not_single_company_financing() -> None:
    candidate = normalize_article(
        {
            "article_id": "article_conversation_spacex",
            "title": (
                "SpaceX is poised to go public and test Starship amid criticism "
                "about its environmental impact"
            ),
            "url": "https://theconversation.com/spacex-starship-environment-example",
            "source": "The Conversation",
            "source_id": "the_conversation",
            "published_at": "2026-05-23T00:00:00Z",
            "collected_at": "2026-05-23T01:00:00+00:00",
            "raw_summary": (
                "University researchers explain rocket launches, coastal ecology, "
                "public scrutiny, and environmental policy risk."
            ),
            "collector": "rss",
            "tags": ["rss", "weird_hook"],
        }
    )

    assert candidate["source_role_class"] == "academic_explainer"
    assert candidate["seed_type"] == "academic_explainer"
    assert candidate["seed_type"] != "single_company_financing"
    assert "single_company_frame" not in candidate["quality_flags"]


def test_conversation_rare_earth_explainer_is_not_single_company_financing() -> None:
    candidate = normalize_article(
        {
            "article_id": "article_conversation_rare_earth",
            "title": "Why rare earth export controls are reshaping geopolitics",
            "url": "https://theconversation.com/rare-earth-controls-example",
            "source": "The Conversation",
            "source_id": "the_conversation",
            "published_at": "2026-05-23T00:00:00Z",
            "collected_at": "2026-05-23T01:00:00+00:00",
            "raw_summary": (
                "Researchers explain China policy, supply chains, magnets, and "
                "industrial risk without focusing on a single company."
            ),
            "collector": "rss",
            "tags": ["rss"],
        }
    )

    assert candidate["source_role_class"] == "academic_explainer"
    assert candidate["seed_type"] in {"academic_explainer", "geopolitical_prequel"}
    assert candidate["seed_type"] != "single_company_financing"


def test_yonhap_trade_minister_title_does_not_match_listing_substring() -> None:
    candidate = normalize_article(
        {
            "article_id": "article_yonhap_rare_earth",
            "title": '日경제산업상, 中 겨냥 "희토류 수출규제 시정해야"',
            "url": "https://www.yna.co.kr/view/AKR20260523037800073",
            "source": "연합뉴스 세계",
            "source_id": "yonhap_international_rss_candidate",
            "published_at": "2026-05-23T00:00:00Z",
            "collected_at": "2026-05-23T01:00:00+00:00",
            "raw_summary": (
                "일본 경제산업상이 중국에서 열린 APEC 통상장관회의에서 "
                "희토류 수출규제 시정을 요구했다."
            ),
            "collector": "rss",
            "tags": ["rss", "domestic_bridge"],
        }
    )

    assert candidate["source_role_class"] == "public_wire"
    assert candidate["seed_type"] != "single_company_financing"
    assert "investment_advice_risk" not in candidate["risk_flags"]


def test_policy_briefing_without_seed_signals_defaults_to_evidence() -> None:
    candidate = normalize_article(
        {
            "article_id": "article_policy_plain",
            "title": "[문화체육관광부] 국제문화교류 활성화 방안 논의",
            "url": "https://www.korea.kr/briefing/pressReleaseView.do?newsId=example",
            "source": "정책브리핑",
            "source_id": "korea_policy_briefing",
            "published_at": "2026-05-23T00:00:00Z",
            "collected_at": "2026-05-23T01:00:00+00:00",
            "raw_summary": "관계기관 회의에서 향후 협력 방향을 논의했다.",
            "collector": "rss",
            "tags": ["rss", "official_evidence"],
        }
    )

    assert candidate["source_role_class"] == "policy_release"
    assert candidate["seed_type"] == "policy_release_evidence"
    assert "policy_release_evidence_default" in candidate["quality_flags"]


def test_policy_briefing_date_only_number_is_evidence_default() -> None:
    candidate = normalize_article(
        {
            "article_id": "article_policy_date_only",
            "title": "[행정안전부] 2026년 5월 23일 제3차 관계기관 회의 개최",
            "url": "https://www.korea.kr/briefing/pressReleaseView.do?newsId=date",
            "source": "정책브리핑",
            "source_id": "korea_policy_briefing",
            "published_at": "2026-05-23T00:00:00Z",
            "collected_at": "2026-05-23T01:00:00+00:00",
            "raw_summary": "2026년 6월 1일 후속 회의를 열고 향후 일정을 논의한다.",
            "collector": "rss",
            "tags": ["rss", "official_evidence"],
        }
    )

    assert candidate["seed_type"] == "policy_release_evidence"
    assert "policy_release_evidence_default" in candidate["quality_flags"]
    assert "policy_release_date_only_number" in candidate["quality_flags"]
    assert "policy_release_announcement_only" in candidate["quality_flags"]


def test_policy_briefing_budget_life_impact_can_be_seed() -> None:
    candidate = normalize_article(
        {
            "article_id": "article_policy_household_budget",
            "title": "[기획재정부] 2조원 규모 가계 요금 지원으로 소비자 부담 완화",
            "url": "https://www.korea.kr/briefing/pressReleaseView.do?newsId=budget",
            "source": "정책브리핑",
            "source_id": "korea_policy_briefing",
            "published_at": "2026-05-23T00:00:00Z",
            "collected_at": "2026-05-23T01:00:00+00:00",
            "raw_summary": "가구별 전기요금과 물가 부담을 낮추는 지원 예산을 발표했다.",
            "collector": "rss",
            "tags": ["rss", "official_evidence"],
        }
    )

    assert candidate["seed_type"] == "policy_release_seed"
    assert "policy_release_evidence_default" not in candidate["quality_flags"]
    assert "policy_release_seed_signals=material_number,life_impact" in candidate[
        "quality_flags"
    ]


def test_policy_briefing_regulation_and_industry_mechanism_can_be_seed() -> None:
    candidate = normalize_article(
        {
            "article_id": "article_policy_regulation_industry",
            "title": "[산업부] 공급망 규제 갈등에 대응한 산업 구조 전환 방안",
            "url": "https://www.korea.kr/briefing/pressReleaseView.do?newsId=reg",
            "source": "정책브리핑",
            "source_id": "korea_policy_briefing",
            "published_at": "2026-05-23T00:00:00Z",
            "collected_at": "2026-05-23T01:00:00+00:00",
            "raw_summary": "제재와 시장 구조 변화에 대응해 인프라와 생산 체계를 바꾼다.",
            "collector": "rss",
            "tags": ["rss", "official_evidence"],
        }
    )

    assert candidate["seed_type"] == "policy_release_seed"
    assert "policy_release_evidence_default" not in candidate["quality_flags"]


def test_policy_briefing_many_dates_only_is_not_seed() -> None:
    candidate = normalize_article(
        {
            "article_id": "article_policy_many_dates",
            "title": "[국토부] 2026년 5월 23일 설명회 및 6월 2일 공모 안내",
            "url": "https://www.korea.kr/briefing/pressReleaseView.do?newsId=dates",
            "source": "정책브리핑",
            "source_id": "korea_policy_briefing",
            "published_at": "2026-05-23T00:00:00Z",
            "collected_at": "2026-05-23T01:00:00+00:00",
            "raw_summary": "7월 1일 접수하고 8월 15일 결과를 발표한다.",
            "collector": "rss",
            "tags": ["rss", "official_evidence"],
        }
    )

    assert candidate["seed_type"] == "policy_release_evidence"
    assert "policy_release_date_only_number" in candidate["quality_flags"]


def test_policy_briefing_with_unusual_industry_signal_can_be_seed() -> None:
    candidate = normalize_article(
        {
            "article_id": "article_policy_goat",
            "title": "[농림축산식품부] 염소 산업 육성으로 농가 소득과 식품 시장 확대",
            "url": "https://www.korea.kr/briefing/pressReleaseView.do?newsId=goat",
            "source": "정책브리핑",
            "source_id": "korea_policy_briefing",
            "published_at": "2026-05-23T00:00:00Z",
            "collected_at": "2026-05-23T01:00:00+00:00",
            "raw_summary": "농가 소득, 식품 시장, 유통 구조를 함께 다룬 보도자료.",
            "collector": "rss",
            "tags": ["rss", "official_evidence"],
        }
    )

    assert candidate["source_role_class"] == "policy_release"
    assert candidate["seed_type"] == "policy_release_seed"
    assert "policy_release_evidence_default" not in candidate["quality_flags"]
    assert "공식 보도자료" in candidate["why_interesting"]


def test_policy_briefing_meeting_coordination_stays_evidence_default() -> None:
    candidate = normalize_article(
        {
            "article_id": "article_policy_apec",
            "title": "[산업통상자원부] APEC 통상장관회의 AI·디지털·녹색산업 협력 논의",
            "url": "https://www.korea.kr/briefing/pressReleaseView.do?newsId=apec",
            "source": "정책브리핑",
            "source_id": "korea_policy_briefing",
            "published_at": "2026-05-23T00:00:00Z",
            "collected_at": "2026-05-23T01:00:00+00:00",
            "raw_summary": "장관회의에서 다자 협력방안과 향후 일정을 논의했다.",
            "collector": "rss",
            "tags": ["rss", "official_evidence"],
        }
    )

    assert candidate["seed_type"] == "policy_release_evidence"
    assert "policy_release_meeting_only" in candidate["quality_flags"]
    assert "policy_release_evidence_default" in candidate["quality_flags"]


def test_policy_briefing_emergency_coordination_without_mechanism_stays_evidence() -> None:
    candidate = normalize_article(
        {
            "article_id": "article_policy_middle_east",
            "title": "[외교부] 중동전쟁 비상경제 대응 공관 담당관회의 개최",
            "url": "https://www.korea.kr/briefing/pressReleaseView.do?newsId=middle-east",
            "source": "정책브리핑",
            "source_id": "korea_policy_briefing",
            "published_at": "2026-05-23T00:00:00Z",
            "collected_at": "2026-05-23T01:00:00+00:00",
            "raw_summary": (
                "총 10개 공관과 정유·석유화학업계 관계자들이 대체 수급선 "
                "확보 가능성과 정부 지원방안을 논의했다."
            ),
            "collector": "rss",
            "tags": ["rss", "official_evidence"],
        }
    )

    assert candidate["seed_type"] == "policy_release_evidence"
    assert "policy_release_meeting_only" in candidate["quality_flags"]
    assert "policy_release_evidence_default" in candidate["quality_flags"]


def test_policy_briefing_procedural_number_only_is_evidence() -> None:
    candidate = normalize_article(
        {
            "article_id": "article_policy_status_report",
            "title": "[행정안전부] 제4차 추진현황 보고서 접수 결과 발표",
            "url": "https://www.korea.kr/briefing/pressReleaseView.do?newsId=status",
            "source": "정책브리핑",
            "source_id": "korea_policy_briefing",
            "published_at": "2026-05-23T00:00:00Z",
            "collected_at": "2026-05-23T01:00:00+00:00",
            "raw_summary": "2026년 기준 보고서와 신청 절차를 안내했다.",
            "collector": "rss",
            "tags": ["rss", "official_evidence"],
        }
    )

    assert candidate["seed_type"] == "policy_release_evidence"
    assert "policy_release_procedural_number_only" in candidate["quality_flags"]


def test_policy_briefing_onion_life_impact_can_be_candidate_seed() -> None:
    candidate = normalize_article(
        {
            "article_id": "article_policy_onion",
            "title": "[농림축산식품부] 양파 소비촉진 특판행사로 농가 소득과 물가 부담 완화",
            "url": "https://www.korea.kr/briefing/pressReleaseView.do?newsId=onion",
            "source": "정책브리핑",
            "source_id": "korea_policy_briefing",
            "published_at": "2026-05-23T00:00:00Z",
            "collected_at": "2026-05-23T01:00:00+00:00",
            "raw_summary": "양파 가격 하락과 소비자 가격 부담을 함께 다루는 행사다.",
            "collector": "rss",
            "tags": ["rss", "official_evidence"],
        }
    )

    assert candidate["seed_type"] == "policy_release_seed"
    assert "policy_release_evidence_default" not in candidate["quality_flags"]


def test_yonhap_public_ai_governance_template_is_specific() -> None:
    candidate = normalize_article(
        {
            "article_id": "article_yonhap_ai_report",
            "title": "공무원 해외교육 결과보고서 1천385건 중 11건 AI 부적절 활용",
            "url": "https://www.yna.co.kr/view/AKR20260523000100001",
            "source": "연합뉴스 산업",
            "source_id": "yonhap_industry",
            "published_at": "2026-05-23T00:00:00Z",
            "collected_at": "2026-05-23T01:00:00+00:00",
            "raw_summary": "공공기관 보고서 작성 과정에서 인공지능 사용 기준 문제가 드러났다.",
            "collector": "rss",
            "tags": ["rss", "domestic_bridge"],
        }
    )

    assert candidate["source_role_class"] == "public_wire"
    assert candidate["seed_type"] == "public_ai_governance"
    assert candidate["story_specificity"]["generic_why_detected"] is False
    assert "공공기관" in candidate["why_interesting"]


def test_yonhap_ai_drone_enforcement_template_beats_governance() -> None:
    candidate = normalize_article(
        {
            "article_id": "article_yonhap_ai_drone",
            "title": "'AI 드론', 범인 붙잡는데도 쓰이네…경찰 실증 확대",
            "url": "https://www.yna.co.kr/view/AKR20260523000200001",
            "source": "연합뉴스 산업",
            "source_id": "yonhap_industry",
            "published_at": "2026-05-23T00:00:00Z",
            "collected_at": "2026-05-23T01:00:00+00:00",
            "raw_summary": "AI 드론을 치안과 공공안전 현장에 활용하는 사례다.",
            "collector": "rss",
            "tags": ["rss", "domestic_bridge"],
        }
    )

    assert candidate["seed_type"] == "public_ai_enforcement"
    assert "공공안전" in candidate["why_interesting"]


def test_yonhap_ai_fake_article_is_governance_not_enforcement() -> None:
    candidate = normalize_article(
        {
            "article_id": "article_yonhap_ai_fake_news",
            "title": "경찰, '5·18은 北지령' AI가짜기사 작성자 추적…무관용 수사",
            "url": "https://www.yna.co.kr/view/AKR20260523000600001",
            "source": "연합뉴스 산업",
            "source_id": "yonhap_industry",
            "published_at": "2026-05-23T00:00:00Z",
            "collected_at": "2026-05-23T01:00:00+00:00",
            "raw_summary": "AI 가짜기사와 허위 정보 유통에 대한 공공 대응 사례다.",
            "collector": "rss",
            "tags": ["rss", "domestic_bridge"],
        }
    )

    assert candidate["seed_type"] == "public_ai_governance"
    assert candidate["seed_type"] != "public_ai_enforcement"


def test_yonhap_workplace_ai_transition_template() -> None:
    candidate = normalize_article(
        {
            "article_id": "article_yonhap_ai_labor",
            "title": "경사노위 AI 노사상생위 출범…직무 재설계 논의",
            "url": "https://www.yna.co.kr/view/AKR20260523000300001",
            "source": "연합뉴스 산업",
            "source_id": "yonhap_industry",
            "published_at": "2026-05-23T00:00:00Z",
            "collected_at": "2026-05-23T01:00:00+00:00",
            "raw_summary": "노사정이 AI 도입과 일자리 변화, 직무교육 방안을 다룬다.",
            "collector": "rss",
            "tags": ["rss", "domestic_bridge"],
        }
    )

    assert candidate["seed_type"] == "workplace_ai_transition"
    assert "직무 재설계" in candidate["why_interesting"]


def test_yonhap_public_wire_product_launch_does_not_get_ai_template() -> None:
    candidate = normalize_article(
        {
            "article_id": "article_yonhap_product",
            "title": "신제품·스노우피크 어패럴 반바지 출시",
            "url": "https://www.yna.co.kr/view/AKR20260523000400001",
            "source": "연합뉴스 경제",
            "source_id": "yonhap_economy",
            "published_at": "2026-05-23T00:00:00Z",
            "collected_at": "2026-05-23T01:00:00+00:00",
            "raw_summary": "여름 의류 신제품을 소개하는 기사다.",
            "collector": "rss",
            "tags": ["rss"],
        }
    )

    assert candidate["seed_type"] not in {
        "public_ai_governance",
        "public_ai_enforcement",
        "workplace_ai_transition",
    }


def test_heatstroke_article_does_not_import_office_shorts_frame() -> None:
    candidate = normalize_article(
        {
            "article_id": "article_yonhap_heatstroke",
            "title": "日, 역대급 불볕더위 앞두고 산업현장 열사병 대책 '비상'",
            "url": "https://www.yna.co.kr/view/AKR20260526055900009",
            "source": "연합뉴스 세계",
            "source_id": "yonhap_international",
            "published_at": "2026-05-26T00:00:00Z",
            "collected_at": "2026-05-26T01:00:00+00:00",
            "raw_summary": "일본 정부와 기업들이 폭염 속 산업현장 열사병 예방 대책을 강화한다.",
            "collector": "rss",
            "tags": ["rss"],
        }
    )

    combined = " ".join(
        [
            str(candidate.get("why_interesting") or ""),
            " ".join(candidate.get("possible_expansions") or []),
        ]
    )
    assert "열사병" in combined
    assert "산업현장" in combined
    assert "반바지" not in combined
    assert "쿨비즈" not in combined


def test_broad_ppt_terms_do_not_import_specific_past_deck_frames() -> None:
    dinosaur = normalize_article(
        {
            "article_id": "article_dinosaur_fossil",
            "title": "신종 공룡 화석 발견…백악기 생태계 단서",
            "url": "https://example.com/dinosaur-fossil",
            "source": "manual",
            "published_at": "2026-05-26T00:00:00Z",
            "collected_at": "2026-05-26T01:00:00+00:00",
            "raw_summary": "연구진이 새 공룡 화석을 분석해 이동 방식과 생태를 설명했다.",
            "collector": "manual",
            "tags": [],
        }
    )
    hippo = normalize_article(
        {
            "article_id": "article_hippo_zoo",
            "title": "동물원 하마, 새 보전센터로 이송",
            "url": "https://example.com/hippo-zoo",
            "source": "manual",
            "published_at": "2026-05-26T00:00:00Z",
            "collected_at": "2026-05-26T01:00:00+00:00",
            "raw_summary": "동물원이 하마 복지와 시설 개선을 위해 이송 계획을 밝혔다.",
            "collector": "manual",
            "tags": [],
        }
    )
    pawnshop = normalize_article(
        {
            "article_id": "article_pawnshop_local",
            "title": "불황에 전당포 이용 늘어…소액 담보대출 주의",
            "url": "https://example.com/pawnshop-local",
            "source": "manual",
            "published_at": "2026-05-26T00:00:00Z",
            "collected_at": "2026-05-26T01:00:00+00:00",
            "raw_summary": "소비자단체가 담보 평가와 연체 수수료 문제를 지적했다.",
            "collector": "manual",
            "tags": [],
        }
    )

    dinosaur_text = " ".join(
        [str(dinosaur.get("why_interesting") or ""), *dinosaur.get("possible_expansions", [])]
    )
    hippo_text = " ".join(
        [str(hippo.get("why_interesting") or ""), *hippo.get("possible_expansions", [])]
    )
    pawnshop_text = " ".join(
        [str(pawnshop.get("why_interesting") or ""), *pawnshop.get("possible_expansions", [])]
    )
    assert "취향" not in dinosaur_text
    assert "T-Rex가 공룡 대표 이미지" not in dinosaur_text
    assert "코카인" not in hippo_text
    assert "암바니" not in hippo_text
    assert "F88" not in pawnshop_text
    assert "베트남" not in pawnshop_text


def test_yonhap_accident_only_public_safety_story_stays_guarded() -> None:
    candidate = normalize_article(
        {
            "article_id": "article_yonhap_accident",
            "title": "도로 추돌사고 발생…경찰 조사",
            "url": "https://www.yna.co.kr/view/AKR20260523000500001",
            "source": "연합뉴스 사회",
            "source_id": "yonhap_society",
            "published_at": "2026-05-23T00:00:00Z",
            "collected_at": "2026-05-23T01:00:00+00:00",
            "raw_summary": "단일 사고 발생 내용을 전하는 기사다.",
            "collector": "rss",
            "tags": ["rss"],
        }
    )

    assert "accident_single_event" in candidate["quality_flags"]
    assert candidate["seed_type"] not in {
        "public_ai_governance",
        "public_ai_enforcement",
    }


def test_normalize_preserves_cross_feed_source_metadata() -> None:
    candidate = normalize_article(
        {
            "article_id": "article_yonhap_cross_feed",
            "title": "AI 드론 산업 규제와 공급망 논쟁",
            "url": "https://www.yna.co.kr/view/AKR20260523000100001",
            "source": "연합뉴스 경제",
            "source_id": "yonhap_economy",
            "published_at": "2026-05-23T00:00:00Z",
            "collected_at": "2026-05-23T01:00:00+00:00",
            "raw_summary": "산업과 경제 섹션에 함께 걸린 기사.",
            "collector": "rss",
            "tags": ["rss", "domestic_bridge"],
            "source_count": 2,
            "source_sections": ["economy", "industry"],
            "supporting_source_ids": ["yonhap_industry"],
        }
    )

    assert candidate["source_count"] == 2
    assert candidate["source_sections"] == ["economy", "industry"]
    assert candidate["supporting_source_ids"] == ["yonhap_industry"]


def test_story_specificity_generic_fallback_is_low() -> None:
    specificity = infer_story_specificity(
        title="AI stocks rise",
        summary="",
        why_interesting="사건 자체보다 배경, 이해관계자 연결고리가 있는지 확인",
        possible_expansions=["배경 설명"],
    )

    assert specificity["level"] == "low"
    assert specificity["generic_why_detected"] is True


def test_story_specificity_concrete_actor_number_mechanism_is_high() -> None:
    specificity = infer_story_specificity(
        title="Google invests $2B as AI search costs pressure publishers",
        summary="The deal reveals a platform funding mechanism and market tension.",
        why_interesting="AI 검색 비용과 지식기관의 수익 구조 변화",
        possible_expansions=["한국 플랫폼과 언론 수익배분 비교"],
    )

    assert specificity["level"] == "high"
    assert "has_named_actor" in specificity["signals"]
    assert "has_number" in specificity["signals"]
    assert "has_mechanism" in specificity["signals"]
    assert "has_tension" in specificity["signals"]


def test_story_specificity_korean_concrete_story_gets_medium_or_high() -> None:
    specificity = infer_story_specificity(
        title="한국 정부, 2030년까지 휴머노이드 로봇 예산 투입",
        summary="제조 현장 인력난과 산업정책 충돌 속에서 로봇 투자가 늘어난다.",
        why_interesting="로봇·제조 산업정책의 구조 변화",
        possible_expansions=["한국 제조업과 인력난"],
    )

    assert specificity["level"] in {"medium", "high"}
    assert "has_named_actor" in specificity["signals"]
    assert "has_number" in specificity["signals"]


def test_normalize_skc_like_single_company_financing_risk() -> None:
    article = {
        "article_id": "article_skc",
        "title": "SKC, 1.2조 유상증자 초과 청약…글라스기판 투자 실탄 확보",
        "url": "https://news.einfomax.co.kr/news/articleView.html?idxno=1",
        "source": "연합인포맥스",
        "source_id": "infomax_manual",
        "published_at": "2026-05-18",
        "collected_at": "2026-05-18T00:00:00+00:00",
        "raw_summary": "AI 반도체용 글라스기판 투자와 재무개선 자금 조달.",
        "tags": ["rss", "korea_business"],
    }

    candidate = normalize_article(article)

    assert candidate["source_role_class"] == "market_wire"
    assert candidate["seed_type"] == "single_company_financing"
    assert "corporate_promo_risk" in candidate["risk_flags"]
    assert "investment_advice_risk" in candidate["risk_flags"]
    assert "single_company_frame" in candidate["quality_flags"]
    assert "단일 기업 유상증자" in candidate["why_interesting"]


def test_normalize_trump_wildfire_policy_risk() -> None:
    article = {
        "article_id": "article_wildfire",
        "title": "Trump's battle with immigration and DEI is impacting forest fires",
        "url": "https://www.npr.org/example",
        "source": "NPR",
        "source_id": "npr_rss_candidate",
        "published_at": "2026-05-18",
        "collected_at": "2026-05-18T00:00:00+00:00",
        "raw_summary": "New burn bans and federal policy fights affect wildfire prevention.",
        "tags": ["rss", "primary_wire"],
    }

    candidate = normalize_article(article)

    assert candidate["seed_type"] == "climate_policy_conflict"
    assert "political_sensitivity" in candidate["risk_flags"]
    assert "live_politics_or_statement" in candidate["quality_flags"]


def test_normalize_specific_editorial_categories() -> None:
    finance = normalize_article(
        {
            "article_id": "article_finance",
            "title": "이억원 담보 및 단기수익 중심 금융 경쟁 앞서가기 어려워",
            "url": "https://news.einfomax.co.kr/news/articleView.html?idxno=2",
            "source": "연합인포맥스",
            "source_id": "infomax_manual",
            "published_at": "2026-05-18",
            "collected_at": "2026-05-18T00:00:00+00:00",
            "raw_summary": "정책금융과 생산적 투자 전환 필요성을 강조.",
            "tags": ["rss"],
        }
    )
    rnd = normalize_article(
        {
            "article_id": "article_rnd",
            "title": "한국형 AI 휴머노이드 개발 착수…2030년까지 예산 투입",
            "url": "https://news.einfomax.co.kr/news/articleView.html?idxno=3",
            "source": "연합인포맥스",
            "source_id": "infomax_manual",
            "published_at": "2026-05-18",
            "collected_at": "2026-05-18T00:00:00+00:00",
            "raw_summary": "정부 R&D 예산으로 로봇 제조 기반을 만든다.",
            "tags": ["rss"],
        }
    )
    ai = normalize_article(
        {
            "article_id": "article_ai",
            "title": (
                "Instant AI answers can trivialise human intelligence, "
                "warns Royal Observatory"
            ),
            "url": "https://www.bbc.com/news/articles/example",
            "source": "BBC News",
            "source_id": "bbc_rss_candidate",
            "published_at": "2026-05-18",
            "collected_at": "2026-05-18T00:00:00+00:00",
            "raw_summary": "AI answers may change how people learn and think.",
            "tags": ["rss"],
        }
    )

    assert finance["seed_type"] == "productive_finance_policy"
    assert "생산적 투자" in finance["why_interesting"]
    assert rnd["seed_type"] == "industrial_policy_rnd"
    assert "로봇·제조" in rnd["why_interesting"]
    assert ai["seed_type"] == "ai_knowledge_institution"
    assert "지식기관" in ai["why_interesting"]


def test_normalize_guardian_technology_product_review_is_flagged() -> None:
    candidate = normalize_article(
        {
            "article_id": "article_guardian_sony_review",
            "title": (
                "Sony 1000XX the Collexion headphones review: supreme comfort "
                "and quiet luxury for your ears"
            ),
            "url": "https://www.theguardian.com/technology/2026/may/27/sony-headphones-review",
            "source": "The Guardian Technology",
            "source_id": "guardian_technology",
            "published_at": "2026-05-27T00:00:00Z",
            "collected_at": "2026-05-27T01:00:00+00:00",
            "raw_summary": "A product review of premium headphones.",
            "collector": "rss",
            "tags": ["rss"],
        }
    )

    assert "product_or_certification_promo" in candidate["quality_flags"]


def test_normalize_candidates_writes_jsonl(tmp_path) -> None:
    input_path = tmp_path / "raw_articles.jsonl"
    output_path = tmp_path / "candidates.jsonl"
    write_jsonl(
        input_path,
        [
            {
                "article_id": "article_abc",
                "title": "전력 수요 급증",
                "url": "https://example.com/power",
                "source": "Manual Input",
                "source_id": "manual",
                "published_at": None,
                "collected_at": "2026-05-17T00:00:00+00:00",
                "language": "ko",
                "region": "global",
                "raw_summary": "시장과 산업 구조",
                "collector": "manual",
                "tags": ["전력", "산업"],
            }
        ],
    )

    candidates = normalize_candidates(input_path=input_path, output_path=output_path)

    assert len(candidates) == 1
    assert output_path.exists()
