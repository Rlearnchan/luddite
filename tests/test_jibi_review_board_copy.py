from luddite.agents.jibi.review_board_copy import build_review_board_copy


def _copy(record, candidate):
    return build_review_board_copy(
        record=record,
        candidate=candidate,
        candidate_title=str(candidate.get("title", "")),
        related_titles="",
        history_status="new",
    )


def test_review_board_copy_youth_labor_matches_editorial_baseline() -> None:
    copy = _copy(
        {
            "bundle_title": "청년 노동시장 이탈 / 쉬었음 / 경제활동참가율",
            "bundle_type": "merged_seed",
        },
        {
            "title": "BOK '쉬었음' 청년층의 특징 및 평가",
            "source": "한국은행",
            "source_role_class": "research_note",
            "seed_type": "macro_research_note",
            "why_interesting": "청년 노동시장 밖 인구를 설명하는 연구노트",
        },
    )

    assert copy.title == "일하지도, 구직하지도 않는 청년들: '쉬었음'의 경제학"
    assert copy.description.startswith("청년 실업률이 낮아도")
    assert "실업률만 보면 안 보이는 노동시장 밖 청년" in copy.description
    assert "경제활동참가율" in copy.description


def test_review_board_copy_handles_public_ai_and_platform_fee() -> None:
    public_ai = _copy(
        {"bundle_title": "공공/현장 AI 도입과 책임"},
        {
            "title": "'AI 드론', 범인 붙잡는데도 쓰이네",
            "source": "연합뉴스 산업",
            "source_role_class": "public_wire",
            "seed_type": "public_ai_enforcement",
        },
    )
    platform = _copy(
        {"bundle_title": "플랫폼 무료배달 / 수수료 비용 배분"},
        {
            "title": "쿠팡이츠, 무료 배달비 업주 전가 논란",
            "source": "연합뉴스 산업",
            "source_role_class": "public_wire",
            "seed_type": "platform_labor_market",
        },
    )

    assert public_ai.title == "AI가 공무원 보고서와 현장 치안에 들어올 때"
    assert "책임은 누가 지는가" in public_ai.description
    assert platform.title == "무료배달은 누가 내나: 배달앱 수수료와 업주 부담"
    assert "비용이 플랫폼·점주·배달노동자 사이에서 어떻게 나뉘는지" in platform.description


def test_review_board_copy_handles_editorial_override_story_types() -> None:
    examples = [
        (
            {"bundle_title": "candidate"},
            {
                "title": "SpaceX is poised to go public and test Starship",
                "source": "The Conversation",
                "seed_type": "academic_explainer",
            },
            "스페이스X 스타십: 민간 우주개발의 돈과 환경 갈등",
            "돈·허가·환경 갈등",
        ),
        (
            {"bundle_title": "candidate"},
            {
                "title": "고양시, 개발제한구역 생활비용 보조사업 추진",
                "source": "연합뉴스 경제",
            },
            "그린벨트에 사는 사람들은 왜 생활비 보조를 받나",
            "도시를 위해 누가 비용을 부담하는가",
        ),
        (
            {"bundle_title": "candidate"},
            {
                "title": "글로벌 PF 대출 5년새 2배…日메가뱅크",
                "source": "연합뉴스 경제",
            },
            "글로벌 PF 대출 5년새 2배: 일본 메가뱅크는 왜 큰손이 됐나",
            "어떤 은행 돈으로 굴러가는지",
        ),
        (
            {"bundle_title": "candidate"},
            {
                "title": "스노우피크 어패럴 반바지",
                "source": "연합뉴스 경제",
                "risk_flags": ["corporate_promo_risk"],
            },
            "반바지가 복지가 되는 시대: 폭염과 회사 복장문화",
            "홍보성 리스크",
        ),
        (
            {"bundle_title": "candidate"},
            {
                "title": "日, 역대급 불볕더위 앞두고 산업현장 열사병 대책 '비상'",
                "summary": "일본 정부와 기업들이 폭염 속 산업현장 열사병 예방 대책을 강화한다.",
                "source": "연합뉴스 세계",
                "possible_expansions": ["일본 산업현장 열사병 대책", "폭염과 산재·작업중지권"],
            },
            "폭염은 산업현장의 새 안전 규칙이 될까",
            "사무실 복장문화보다",
        ),
    ]

    for record, candidate, expected_title, expected_phrase in examples:
        copy = _copy(record, candidate)
        assert copy.title == expected_title
        assert expected_phrase in copy.description


def test_review_board_copy_does_not_treat_underwater_as_rwa() -> None:
    copy = _copy(
        {"bundle_title": "The network watching the world’s oceans is under pressure"},
        {
            "title": "The network watching the world’s oceans is under pressure",
            "summary": "Underwater gliders feed data to ocean scientists.",
            "source": "The Conversation",
            "source_role_class": "academic_explainer",
            "seed_type": "academic_explainer",
        },
    )

    assert copy.title == "해외 후보, 한 가지 질문으로 더 좁혀볼 소재"
    assert "자산 토큰화" not in copy.title
    assert "부동산·채권" not in copy.description


def test_review_board_copy_ignores_generated_why_for_template_triggers() -> None:
    copy = _copy(
        {"bundle_title": "candidate"},
        {
            "title": "日, 역대급 불볕더위 앞두고 산업현장 열사병 대책 '비상'",
            "summary": "일본 정부와 기업들이 폭염 속 산업현장 열사병 예방 대책을 강화한다.",
            "why_interesting": "한국 기업 쿨비즈/반바지 문화로 이어질 수 있음",
            "source": "연합뉴스 세계",
            "seed_type": "life_change",
        },
    )

    assert copy.title == "폭염은 산업현장의 새 안전 규칙이 될까"
    assert "반바지" not in copy.title
    assert "반바지" not in copy.description


def test_review_board_copy_does_not_treat_generic_platform_as_delivery() -> None:
    copy = _copy(
        {"bundle_title": "candidate"},
        {
            "title": "[AI픽] 노션, 개발자 플랫폼 공개…AI 업무자동화 본격화",
            "summary": "노션이 개발자 플랫폼을 공개하고 업무자동화 기능을 강화했다.",
            "source": "연합뉴스 산업",
            "seed_type": "industry_disruption",
        },
    )

    assert "무료배달" not in copy.title
    assert "배달앱" not in copy.description


def test_review_board_copy_does_not_treat_generic_support_as_oil_support() -> None:
    copy = _copy(
        {"bundle_title": "candidate"},
        {
            "title": "청년 월세 지원금 신청 시작",
            "summary": "지자체가 청년 주거비 부담을 줄이기 위한 지원금을 접수한다.",
            "source": "연합뉴스 사회",
            "seed_type": "policy_release_evidence",
        },
    )

    assert "고유가" not in copy.title
    assert "에너지 가격" not in copy.description


def test_review_board_copy_makes_tokenization_question_first() -> None:
    copy = _copy(
        {"bundle_title": "국내외 자산 토큰화 현황 및 향후 정책 과제"},
        {
            "title": "[제2026-11호] 국내외 자산 토큰화 현황 및 향후 정책 과제",
            "source": "한국은행",
            "source_role_class": "research_note",
            "seed_type": "policy_research_note",
            "story_role": "seed_with_supporting_links",
            "why_interesting": "RWA와 STO 제도권 금융 인프라",
        },
    )

    assert copy.title == "집도, 채권도 쪼개 사고파는 시대: 자산 토큰화"
    assert copy.description.startswith("코인 가격이 아니라")
    assert "누가 책임질까" in copy.description
    assert "최신 뉴스 hook" in copy.description
    assert "BOK는 핵심 근거" in copy.description


def test_review_board_copy_fallback_uses_story_role_research_action() -> None:
    copy = _copy(
        {
            "bundle_title": "낯선 정책 후보",
            "suggested_operator_action": "collect_second_source",
        },
        {
            "title": "새로운 생활 규제 후보",
            "source": "연합뉴스 경제",
            "story_role": "seed_with_supporting_links",
        },
    )

    assert copy.description.startswith("연합뉴스 경제")
    assert "핵심 질문은 '이 후보를 단독 주제로" in copy.description
    assert "최신 뉴스와 두 번째 출처" in copy.description
    assert "두 번째 출처와 숫자" in copy.description


def test_review_board_copy_ai_patent_platform_uses_specific_frame() -> None:
    copy = _copy(
        {"bundle_title": "AI 특허 분석 플랫폼"},
        {
            "title": "AI로 특허·기술정보 쉽게 분석…지식재산정보분석플랫폼 구축",
            "summary": "AI가 특허와 기술 정보를 쉽게 분석하도록 돕는 플랫폼을 구축한다.",
            "source": "연합뉴스 경제",
            "source_role_class": "public_wire",
            "seed_type": "public_ai_governance",
        },
    )

    assert copy.title == "특허 검색도 AI가 하면 무엇이 달라지나"
    assert "중소기업이나 연구자가 기술 지형을 읽는 비용" in copy.description
    assert "이 후보를 단독 주제로" not in copy.description


def test_review_board_copy_ai_history_vlog_uses_casual_use_case_frame() -> None:
    copy = _copy(
        {"bundle_title": "AI generated time-travellers"},
        {
            "title": (
                "We can stitch together our past: the AI-generated "
                "time-travellers vlogging from history"
            ),
            "summary": "AI-generated historical characters make travel vlog style videos.",
            "source": "The Guardian Technology",
            "source_role_class": "section_news",
            "seed_type": "ai_consumer_use_case",
        },
    )

    assert copy.title == "AI가 역사를 브이로그로 만들기 시작했다"
    assert "재미있어서 보는데 어디까지 믿어야 하나" in copy.description
    assert "거대 저작권 논쟁" in copy.description


def test_review_board_copy_samsung_memory_bonus_uses_profit_sharing_frame() -> None:
    copy = _copy(
        {"bundle_title": "Samsung memory chip staff bonuses"},
        {
            "title": "Samsung memory chip staff in line for bonuses after AI profit-sharing deal",
            "summary": "AI demand lifts profit sharing for memory chip workers.",
            "source": "The Guardian Business",
            "source_role_class": "section_news",
            "seed_type": "ai_labor_market",
        },
    )

    assert copy.title == "AI 반도체 호황의 보너스는 누구에게 가나"
    assert "주주·회사·직원 사이에서 어떻게 나뉘는지" in copy.description


def test_review_board_copy_lawnmower_noise_uses_sub_block_frame() -> None:
    copy = _copy(
        {"bundle_title": "Lawnmower hum"},
        {
            "title": "Lawnmower hum: why the sound of the summer could cost you £5,000",
            "summary": "Local councils may fine residents over summer lawnmower noise.",
            "source": "The Guardian Environment",
            "source_role_class": "section_news",
            "seed_type": "life_change",
        },
    )

    assert copy.title == "잔디깎이 소음에도 비용이 붙는 시대"
    assert "짧은 서브 소재" in copy.description


def test_review_board_copy_global_datacentre_uses_specific_frame() -> None:
    copy = _copy(
        {"bundle_title": "Scotland green datacentres and AI emissions"},
        {
            "title": (
                "Scotland’s ‘green datacentres’ policy ignores emissions impact "
                "of AI, analysis shows"
            ),
            "summary": "AI datacentres increase electricity demand and emissions.",
            "source": "The Guardian Technology",
            "source_id": "guardian_technology",
            "source_role_class": "section_news",
            "seed_type": "policy_market_shock",
            "story_role": "seed_with_supporting_links",
        },
    )

    assert copy.title == "AI 데이터센터는 전력 먹는 공장인가"
    assert copy.description.startswith("AI 데이터센터는")
    assert "전력수요와 탄소회계" in copy.description
    assert "최신 뉴스와 두 번째 출처" not in copy.description
    assert "AI가 실제 조직 안으로" not in copy.description


def test_review_board_copy_global_energy_story_does_not_false_ai_on_straight() -> None:
    copy = _copy(
        {"bundle_title": "energy bills"},
        {
            "title": (
                "Ofgem should tell it straight: electricity prices are set to stay "
                "high for years"
            ),
            "summary": "The regulator says household energy bills will stay high.",
            "source": "The Guardian Business",
            "source_id": "guardian_business",
            "source_role_class": "section_news",
            "seed_type": "life_change",
        },
    )

    assert copy.title == "중동 전쟁이 전기요금으로 번지는 길"
    assert copy.description.startswith("전기요금이 오래 비싸지면")
    assert "가계 지출, 기업 비용, 전력망 투자" in copy.description
    assert "AI가 실제 조직 안으로" not in copy.description


def test_review_board_copy_global_work_placement_uses_labor_frame() -> None:
    copy = _copy(
        {"bundle_title": "Manchester work placements"},
        {
            "title": "Manchester University to offer work placements to all undergraduates",
            "summary": (
                "A university promises meaningful real-world experience for all "
                "students before the job market."
            ),
            "source": "The Guardian Business",
            "source_id": "guardian_business",
            "source_role_class": "section_news",
            "seed_type": "workplace_transition",
        },
    )

    assert copy.title == "첫 경력은 왜 점점 비싼 관문이 됐나"
    assert copy.description.startswith("청년의 첫 경력은")
    assert "대학·기업·노동시장" in copy.description
    assert "최신 뉴스와 두 번째 출처" not in copy.description


def test_review_board_copy_global_public_wire_energy_uses_global_not_korea_bridge() -> None:
    copy = _copy(
        {"bundle_title": "Iran war and energy bills"},
        {
            "title": "Iran war impact to hit household energy bills for the first time",
            "summary": (
                "Energy prices and household electricity bills may rise as war "
                "pressure reaches global markets."
            ),
            "source": "BBC News",
            "source_id": "bbc_rss_candidate",
            "source_role_class": "public_wire",
            "seed_type": "policy_market_shock",
        },
    )

    assert copy.title == "중동 전쟁이 전기요금으로 번지는 길"
    assert copy.description.startswith("전기요금이 오래 비싸지면")
    assert "에너지 가격 충격" in copy.description
    assert "한국 시청자" not in copy.description


def test_review_board_copy_global_ai_ethics_uses_specific_frame() -> None:
    copy = _copy(
        {"bundle_title": "Pope Leo and AI risk"},
        {
            "title": "Pope Leo warns of AI’s risks to humanity in his first encyclical",
            "summary": "The pope warns about artificial intelligence and human dignity.",
            "source": "The Conversation",
            "source_id": "the_conversation",
            "source_role_class": "academic_explainer",
            "seed_type": "academic_explainer",
            "story_role": "seed_with_supporting_links",
        },
    )

    assert copy.title == "교황은 왜 AI 위험을 먼저 꺼냈나"
    assert copy.description.startswith("AI가 콘텐츠와 신뢰의 규칙을")
    assert "창작자 권리, 목소리 소유권, 교육 현장" in copy.description
    assert "최신 뉴스와 두 번째 출처" not in copy.description


def test_review_board_copy_weather_retail_uses_consumer_frame() -> None:
    copy = _copy(
        {"bundle_title": "B&Q weather and sales"},
        {
            "title": "B&Q blames sales dip on wet Easter but predicts heatwave gain",
            "summary": "The retailer says weather changed DIY and garden sales.",
            "source": "The Guardian Business",
            "source_id": "guardian_business",
            "source_role_class": "section_news",
            "seed_type": "life_change",
            "story_role": "seed_with_supporting_links",
        },
    )

    assert copy.title == "날씨가 바꾸는 소비와 기업 실적"
    assert copy.description.startswith("날씨가 달라지면")
    assert "생활 소비를 바꾸는 장면" in copy.description
    assert "최신 뉴스와 두 번째 출처" not in copy.description


def test_review_board_copy_heatwave_cooling_prices_uses_specific_frame() -> None:
    copy = _copy(
        {"bundle_title": "UK heatwave price rises"},
        {
            "title": "UK heatwave triggers price rises for hot tubs and air conditioning units",
            "summary": "Retailers report higher prices for air conditioning units.",
            "source": "The Guardian Business",
            "source_role_class": "section_news",
            "seed_type": "life_change",
        },
    )

    assert copy.title == "폭염이 에어컨과 물놀이 물가를 올릴 때"
    assert "제품 추천이나 쇼핑 정보로 가면 안 되고" in copy.description
    assert "냉방기기 가격 추이" in copy.description


def test_review_board_copy_current_board_candidates_use_specific_frames() -> None:
    examples = [
        (
            {
                "title": "스마트폰 시장, 메모리 부족 여파 사상 최악 조짐…삼성전자 비중↑",
                "source": "연합인포맥스",
                "source_role_class": "market_wire",
            },
            "AI 서버가 스마트폰 부품까지 빨아들이나",
            "부품 수급과 AI 투자 쏠림",
        ),
        (
            {
                "title": 'CJ온스타일 "대화형AI 통한 유입 4배 늘어…데이터 최적화 효과"',
                "source": "연합뉴스 산업",
                "source_role_class": "public_wire",
            },
            "쇼핑몰 유입도 AI와 대화하며 들어오는 시대",
            "검색 광고·쇼핑 추천·상담 챗봇",
        ),
        (
            {
                "title": "메타, AI 유료 구독 도입…월 7.99달러부터",
                "source": "연합뉴스 세계",
                "source_role_class": "public_wire",
            },
            "AI도 월 구독료를 받기 시작했다",
            "누가 돈을 내느냐",
        ),
        (
            {
                "title": '김정관 산업장관 "올해 수출 9천억불 넘을 듯…반도체 외에도 숫자 좋아"',
                "source": "연합인포맥스",
                "source_role_class": "market_wire",
            },
            "반도체 말고도 수출 숫자가 좋아진다는 말",
            "한국 수출 지형을 점검하는 근거",
        ),
    ]

    for candidate, expected_title, expected_phrase in examples:
        copy = _copy({"bundle_title": candidate["title"]}, candidate)
        assert copy.title == expected_title
        assert expected_phrase in copy.description
        assert "원문 하나만으로는 아직 결론" not in copy.description


def test_review_board_copy_corporate_cash_reallocation_avoids_investment_frame() -> None:
    copy = _copy(
        {"bundle_title": "두나무 지분 팔아 1.6조 손에 쥔 카카오"},
        {
            "title": "두나무 지분 팔아 1.6조 손에 쥔 카카오…다음 행보는",
            "summary": "카카오가 두나무 지분 매각대금으로 현금을 확보했다.",
            "source": "연합인포맥스",
            "source_role_class": "market_wire",
            "seed_type": "single_company_financing",
            "story_role": "seed_with_supporting_links",
        },
    )

    assert copy.title == "기업은 현금을 어디로 옮기나"
    assert "현금을 확보하고 다음 투자처를 고르는 장면" in copy.description
    assert "투자 기사처럼 보이므로" in copy.description
    assert "단일 회사 전망으로 끝나면 evidence" in copy.description
    assert "AI가 실제 조직 안으로" not in copy.description


def test_review_board_copy_factory_capex_rebalance_uses_industry_frame() -> None:
    copy = _copy(
        {"bundle_title": "LG엔솔 미국 배터리공장 건물 처분"},
        {
            "title": "LG엔솔, 혼다 합작 미국 배터리공장 건물 3조7천억원에 처분",
            "summary": "전기차 수요 둔화 속 배터리 합작공장 건물을 처분했다.",
            "source": "연합뉴스 산업",
            "source_role_class": "public_wire",
            "seed_type": "industry_disruption",
        },
    )

    assert copy.title == "전기차 공장 붐 이후 누가 비용을 떠안나"
    assert "보조금, 합작공장, 공급과잉" in copy.description
    assert "단일 기업 기사로만 남으면 evidence" in copy.description
    assert "핵심은 주가가 아니라" in copy.description


def test_review_board_copy_market_note_marks_evidence_not_seed() -> None:
    copy = _copy(
        {"bundle_title": "KB증권 AI 기판 목표가"},
        {
            "title": 'KB증권 "LG이노텍, AI 기판 공급 부족 수혜…목표가 160만원"',
            "summary": "증권사가 AI 기판 수혜와 목표가를 제시했다.",
            "source": "연합뉴스 경제",
            "source_role_class": "public_wire",
            "seed_type": "market_note",
        },
    )

    assert copy.title == "시장 반응 메모: 단독 seed인지 근거인지"
    assert "방송 seed라기보다" in copy.description
    assert "보조 근거" in copy.description
    assert "리뷰보드에서는 seed 후보보다 evidence 후보" in copy.description


def test_review_board_copy_equity_financing_marks_dilution_cost() -> None:
    copy = _copy(
        {"bundle_title": "아모텍 유상증자"},
        {
            "title": "아모텍, 350억원 주주배정 유상증자 결정",
            "summary": "회사가 신주를 발행해 투자자금을 조달한다.",
            "source": "연합뉴스 경제",
            "source_role_class": "public_wire",
            "seed_type": "single_company_financing",
        },
    )

    assert copy.title == "회사가 주주에게 다시 돈을 구할 때"
    assert "기존 주주의 희석 부담" in copy.description
    assert "특정 종목보다 산업 전체" in copy.description
    assert "evidence" in copy.description


def test_review_board_copy_mou_bulletin_defaults_to_evidence() -> None:
    copy = _copy(
        {"bundle_title": "신용회복위원회 NH농협은행 MOU"},
        {
            "title": "[게시판] 신용회복위원회-NH농협은행, 금융취약계층 금융 지원 MOU",
            "summary": "두 기관이 금융취약계층 지원 업무협약을 맺었다.",
            "source": "연합뉴스 경제",
            "source_role_class": "public_wire",
            "seed_type": "policy_release_evidence",
        },
    )

    assert copy.title == "근거 자료: 더 큰 이야기 안에서 볼 후보"
    assert "행사·협약·모집 공지" in copy.description
    assert "공식 근거로 붙이면" in copy.description
    assert "단독 seed로 올리기보다 evidence" in copy.description


def test_review_board_copy_mou_bundle_does_not_override_unrelated_candidate_title() -> None:
    copy = _copy(
        {"bundle_title": "순천향대-싸이티바 AI 바이오 인재 양성 협약"},
        {
            "title": "Iran war impact to hit household energy bills for the first time",
            "summary": (
                "Energy prices and household electricity bills may rise as war "
                "pressure reaches global markets."
            ),
            "source": "BBC News",
            "source_id": "bbc_rss_candidate",
            "source_role_class": "public_wire",
            "seed_type": "policy_market_shock",
        },
    )

    assert copy.title == "중동 전쟁이 전기요금으로 번지는 길"
    assert "근거 자료" not in copy.title
    assert copy.description.startswith("전기요금이 오래 비싸지면")


def test_review_board_copy_generic_machine_title_does_not_override_candidate_title() -> None:
    copy = _copy(
        {"bundle_title": "근거 자료: 더 큰 이야기 안에서 볼 후보"},
        {
            "title": "Iran war impact to hit household energy bills for the first time",
            "summary": (
                "Energy prices and household electricity bills may rise as war "
                "pressure reaches global markets."
            ),
            "source": "BBC News",
            "source_id": "bbc_rss_candidate",
            "source_role_class": "public_wire",
            "seed_type": "policy_market_shock",
        },
    )

    assert copy.title == "중동 전쟁이 전기요금으로 번지는 길"
    assert copy.description.startswith("전기요금이 오래 비싸지면")


def test_review_board_copy_does_not_treat_amount_as_mou() -> None:
    copy = _copy(
        {"bundle_title": "Iran war impact to hit household energy bills for the first time"},
        {
            "title": "Iran war impact to hit household energy bills for the first time",
            "summary": (
                "A household using a typical amount of gas and electricity is forecast "
                "to pay about £200 more a year."
            ),
            "source": "BBC News",
            "source_id": "bbc_rss_candidate",
            "source_role_class": "public_wire",
            "seed_type": "policy_market_shock",
        },
    )

    assert copy.title == "중동 전쟁이 전기요금으로 번지는 길"
    assert "근거 자료" not in copy.title
    assert copy.description.startswith("전기요금이 오래 비싸지면")


def test_review_board_copy_excludes_internal_labels() -> None:
    copy = _copy(
        {
            "bundle_title": "generic_why merged_seed story_bundle",
            "bundle_type": "needs_external_sources",
        },
        {
            "title": "알 수 없는 후보",
            "source": "example",
            "why_interesting": "review_primary generic_why",
        },
    )

    for label in [
        "merged_seed",
        "review_primary",
        "generic_why",
        "needs_external_sources",
        "story_bundle",
    ]:
        assert label not in copy.title
        assert label not in copy.description
