import csv

from luddite.agents.jibi.render_daily_digest import render_daily_digest
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
                "source": "Manual Input",
                "final_grade": "A",
                "recommended_action": "send_to_anny",
                "risk_level": "medium",
                "risk_flags": ["investment_advice_risk"],
                "why_interesting": "엥? hook과 구조 확장",
                "evidence_needed": ["추가 출처"],
                "possible_expansions": ["베트남 신용시장"],
                "scores": {"total_score": 30, "broadcast_potential_proxy": 5},
            }
        ],
    )

    md_path, csv_path, top = render_daily_digest(
        input_path=input_path,
        output_dir=output_dir,
        digest_date="2026-05-17",
    )

    assert len(top) == 1
    assert "전당포 주식회사" in md_path.read_text(encoding="utf-8")
    with csv_path.open(encoding="utf-8-sig", newline="") as source:
        rows = list(csv.DictReader(source))
    assert rows[0]["source_marker"] == "jibi"
    assert rows[0]["recommended_action"] == "send_to_anny"
