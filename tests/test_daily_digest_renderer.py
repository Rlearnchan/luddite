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
                "scores": {"total_score": 55, "broadcast_potential_proxy": 5},
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
    assert "- Top Candidates: 1개" in markdown
    assert "- 즉시 스토리라인 후보: 1개" in markdown
    assert "바로 볼 만한 후보" not in markdown
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


def test_top_candidates_limits_same_source() -> None:
    candidates = [
        {
            "candidate_id": f"same_{index}",
            "source": "Same Source",
            "final_grade": "B",
            "recommended_action": "gather_more_evidence",
            "scores": {"total_score": 100 - index, "broadcast_potential_proxy": 5},
        }
        for index in range(5)
    ]
    candidates.append(
        {
            "candidate_id": "other",
            "source": "Other Source",
            "final_grade": "B",
            "recommended_action": "gather_more_evidence",
            "scores": {"total_score": 35, "broadcast_potential_proxy": 1},
        }
    )

    selected = top_candidates(candidates, limit=10, max_per_source=3)

    assert [candidate["candidate_id"] for candidate in selected] == [
        "same_0",
        "same_1",
        "same_2",
        "other",
    ]


def test_top_candidates_excludes_single_company_thin_evidence() -> None:
    candidates = [
        {
            "candidate_id": "skc",
            "source": "연합인포맥스",
            "final_grade": "B",
            "recommended_action": "gather_more_evidence",
            "quality_flags": ["single_company_frame"],
            "failure_modes": ["thin_evidence"],
            "scores": {"total_score": 80, "broadcast_potential_proxy": 5},
        },
        {
            "candidate_id": "policy",
            "source": "연합인포맥스",
            "final_grade": "B",
            "recommended_action": "gather_more_evidence",
            "quality_flags": [],
            "failure_modes": ["thin_evidence"],
            "scores": {"total_score": 55, "broadcast_potential_proxy": 3},
        },
    ]

    assert [candidate["candidate_id"] for candidate in top_candidates(candidates)] == ["policy"]


def test_top_candidates_excludes_generic_other_rationale() -> None:
    candidates = [
        {
            "candidate_id": "generic",
            "source": "연합인포맥스",
            "seed_type": "other",
            "final_grade": "B",
            "recommended_action": "gather_more_evidence",
            "quality_flags": [],
            "why_interesting": "사건 자체보다 배경, 이해관계자 연결고리가 있는지 확인",
            "scores": {"total_score": 80, "broadcast_potential_proxy": 5},
        },
        {
            "candidate_id": "specific",
            "source": "BBC News",
            "seed_type": "ai_knowledge_institution",
            "final_grade": "B",
            "recommended_action": "gather_more_evidence",
            "quality_flags": [],
            "why_interesting": "AI 즉답과 지식기관의 역할 변화",
            "scores": {"total_score": 55, "broadcast_potential_proxy": 3},
        },
    ]

    assert [candidate["candidate_id"] for candidate in top_candidates(candidates)] == ["specific"]
