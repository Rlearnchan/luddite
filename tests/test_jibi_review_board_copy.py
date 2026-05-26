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
    assert copy.description.startswith("'청년 실업률이 낮아도")
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

    assert copy.title == "The network watching the world’s oceans is under pressure"
    assert "자산 토큰화" not in copy.title
    assert "부동산·채권" not in copy.description


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
    assert copy.description.startswith("'코인 가격이 아니라")
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

    assert copy.description.startswith("'이 후보를 단독 주제로")
    assert "최신 뉴스와 두 번째 출처" in copy.description
    assert "두 번째 출처와 숫자" in copy.description


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
