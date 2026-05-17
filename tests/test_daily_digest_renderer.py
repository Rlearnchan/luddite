import csv

from luddite.agents.jibi.render_daily_digest import render_daily_digest, top_candidates
from luddite.utils.jsonl import write_jsonl


def test_daily_digest_renderer_writes_markdown_and_csv(tmp_path) -> None:
    input_path = tmp_path / "scored.jsonl"
    output_dir = tmp_path / "daily_digest"
    write_jsonl(
        input_path,
        [
            {
                "candidate_id": "jibi_1",
                "title": "전당포 주식회사",
                "seed_url": "https://example.com/f88",
                "source_url_canonical": "https://example.com/f88",
                "duplicate_key": "https://example.com/f88",
                "source": "Manual Input",
                "final_grade": "A",
                "recommended_action": "send_to_anny",
                "risk_level": "medium",
                "risk_flags": ["investment_advice_risk"],
                "why_interesting": "엥? hook과 구조 확장",
                "evidence_needed": ["추가 출처"],
                "possible_expansions": ["베트남 신용시장"],
                "scores": {"total_score": 30, "broadcast_potential_proxy": 5},
                "source_type": "manual",
                "collected_at": "2026-05-17T00:00:00+00:00",
                "last_seen_at": "2026-05-17T00:00:00+00:00",
            },
            {
                "candidate_id": "jibi_reject",
                "title": "속보: 대통령 발언 직후 증시 급등락",
                "seed_url": "https://example.com/politics",
                "source": "Manual Input",
                "source_type": "manual",
                "final_grade": "D",
                "recommended_action": "reject",
                "risk_level": "high",
                "risk_flags": ["political_sensitivity"],
                "why_interesting": "직접 정치 평가",
                "evidence_needed": ["검증 부담"],
                "possible_expansions": ["정책상 제외"],
                "scores": {"total_score": 99, "broadcast_potential_proxy": 5},
                "blocked_reason": "direct_president_party_evaluation",
            }
        ],
    )

    md_path, csv_path, top = render_daily_digest(
        input_path=input_path,
        output_dir=output_dir,
        digest_date="2026-05-17",
    )

    assert len(top) == 1
    markdown = md_path.read_text(encoding="utf-8")
    assert "Luddite Daily Digest" in markdown
    assert "오늘의 추천" in markdown
    assert "전당포 주식회사" in markdown
    assert "## Excluded / Rejected" in markdown
    assert "속보: 대통령 발언 직후 증시 급등락" in markdown
    with csv_path.open(encoding="utf-8-sig", newline="") as source:
        rows = list(csv.DictReader(source))
    assert len(rows) == 1
    assert rows[0]["status"] == "new"
    assert rows[0]["recommended_action"] == "send_to_anny"
    assert rows[0]["주제명"] == "전당포 주식회사"
    assert rows[0]["digest_date"] == "2026-05-17"
    assert rows[0]["collected_at"] == "2026-05-17T00:00:00+00:00"
    assert rows[0]["last_seen_at"] == "2026-05-17T00:00:00+00:00"
    assert rows[0]["duplicate_key"] == "https://example.com/f88"
    assert rows[0]["source_url_canonical"] == "https://example.com/f88"


def test_top_candidates_excludes_rejects() -> None:
    candidates = [
        {
            "candidate_id": "reject",
            "recommended_action": "reject",
            "scores": {"total_score": 100, "broadcast_potential_proxy": 5},
        },
        {
            "candidate_id": "good",
            "recommended_action": "send_to_anny",
            "scores": {"total_score": 50, "broadcast_potential_proxy": 3},
        },
    ]

    assert [candidate["candidate_id"] for candidate in top_candidates(candidates)] == ["good"]
