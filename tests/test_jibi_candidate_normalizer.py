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
