from luddite.agents.jibi.normalize_candidates import normalize_article, normalize_candidates
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
