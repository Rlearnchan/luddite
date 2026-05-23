import csv

from luddite.agents.jibi.render_daily_digest import (
    render_daily_digest,
    top_candidates,
    write_quality_report,
)
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
                "slideability": {
                    "score": 0.78,
                    "visualizability": "high",
                    "chartability": "weak",
                    "diagramability": "strong",
                    "screenshotability": "weak",
                    "source_card_fit": "strong",
                    "first_slide_idea": "전당포 금융 구조 diagram",
                    "likely_proof_object_types": ["diagram", "chart", "source_card"],
                    "risks": ["market_claim_risk"],
                    "reason": "chart=weak; diagram=strong",
                },
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
    assert "Slideability: high / diagram+chart+source_card" in markdown
    assert "First slide idea: 전당포 금융 구조 diagram" in markdown
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
    assert rows[0]["slideability_score"] == "0.78"
    assert rows[0]["first_slide_idea"] == "전당포 금융 구조 diagram"


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


def test_top_candidates_uses_only_near_duplicate_primary() -> None:
    candidates = [
        {
            "candidate_id": "primary",
            "recommended_action": "gather_more_evidence",
            "final_grade": "B",
            "scores": {"total_score": 80, "broadcast_potential_proxy": 5},
            "near_duplicate_role": "primary",
        },
        {
            "candidate_id": "supporting",
            "recommended_action": "gather_more_evidence",
            "final_grade": "B",
            "scores": {"total_score": 79, "broadcast_potential_proxy": 5},
            "near_duplicate_role": "supporting_source",
        },
    ]

    assert [candidate["candidate_id"] for candidate in top_candidates(candidates)] == ["primary"]


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


def test_quality_report_contains_source_freshness_and_duplicate_sections(tmp_path) -> None:
    report_path = tmp_path / "quality.md"
    candidates = [
        {
            "candidate_id": "primary",
            "title": "Drone defense costs surge as cheap drones spread",
            "source": "BBC News",
            "seed_type": "cost_asymmetry",
            "risk_flags": [],
            "quality_flags": [],
            "freshness_status": "recent",
            "recommended_action": "gather_more_evidence",
            "scores": {"total_score": 80},
            "slideability": {"visualizability": "high"},
            "near_duplicate_group_id": "nd_abc",
            "near_duplicate_count": 2,
            "near_duplicate_role": "primary",
            "near_duplicate_reason": "highest_scoring_title_overlap_primary",
        },
        {
            "candidate_id": "supporting",
            "title": "Cheap drones spread as drone defense costs surge",
            "source": "NPR",
            "seed_type": "cost_asymmetry",
            "risk_flags": [],
            "quality_flags": ["empty_summary", "stale_item"],
            "freshness_status": "stale",
            "recommended_action": "keep_for_later",
            "scores": {"total_score": 30},
            "slideability": {"visualizability": "medium"},
            "near_duplicate_group_id": "nd_abc",
            "near_duplicate_count": 2,
            "near_duplicate_role": "supporting_source",
            "near_duplicate_reason": "cross_source_title_overlap_0.82",
        },
    ]

    write_quality_report(report_path, candidates, [candidates[0]])

    report = report_path.read_text(encoding="utf-8")
    assert "## Source Freshness Summary" in report
    assert "BBC News: raw=1, top=1, recent=1" in report
    assert "NPR: raw=1, top=0, recent=0, stale=1" in report
    assert "## Near Duplicate Groups" in report
    assert "`nd_abc`" in report
    assert "shared_tokens=" in report


def test_quality_report_contains_candidate_funnel_and_near_miss_queue(tmp_path) -> None:
    report_path = tmp_path / "quality.md"
    top_candidate = {
        "candidate_id": "top",
        "title": "AI search changes how people verify facts",
        "source": "NPR",
        "seed_type": "ai_knowledge_institution",
        "risk_flags": [],
        "quality_flags": [],
        "freshness_status": "recent",
        "recommended_action": "gather_more_evidence",
        "final_grade": "B",
        "scores": {"total_score": 60, "broadcast_potential_proxy": 4},
        "slideability": {"visualizability": "high"},
    }
    generic_specific_candidate = {
        "candidate_id": "generic_specific",
        "title": "Google spends $2B as AI search costs pressure schools",
        "source": "NPR",
        "seed_type": "other",
        "risk_flags": [],
        "quality_flags": [],
        "freshness_status": "recent",
        "why_interesting": "사건 자체보다 배경, 이해관계자 연결고리가 있는지 확인",
        "story_specificity": {
            "score": 0.83,
            "level": "high",
            "signals": [
                "has_named_actor",
                "has_number",
                "has_mechanism",
                "has_tension",
                "has_visual_hook",
            ],
            "generic_why_detected": True,
        },
        "recommended_action": "gather_more_evidence",
        "final_grade": "B",
        "scores": {"total_score": 75, "broadcast_potential_proxy": 4},
        "slideability": {"visualizability": "high"},
    }
    stale_candidates = [
        {
            "candidate_id": f"stale_{index}",
            "title": (
                "Stale but high scoring infrastructure story"
                if index == 0
                else f"Old story {index}"
            ),
            "source": "BBC News",
            "seed_type": "other",
            "risk_flags": [],
            "quality_flags": ["stale_item"],
            "failure_modes": ["stale_rss_item"],
            "freshness_status": "stale",
            "age_hours": 240 + index,
            "recommended_action": "keep_for_later",
            "final_grade": "B",
            "scores": {"total_score": 90 - index, "broadcast_potential_proxy": 3},
            "slideability": {"visualizability": "medium"},
        }
        for index in range(30)
    ]
    empty_summary_candidates = [
        {
            "candidate_id": f"empty_{index}",
            "title": f"Domestic market note {index}",
            "source": "Empty Source",
            "seed_type": "other",
            "risk_flags": [],
            "quality_flags": ["empty_summary"],
            "failure_modes": ["thin_evidence"],
            "freshness_status": "recent",
            "recommended_action": "keep_for_later",
            "final_grade": "D",
            "scores": {"total_score": 20 - index, "broadcast_potential_proxy": 1},
            "slideability": {"visualizability": "low"},
        }
        for index in range(5)
    ]

    write_quality_report(
        report_path,
        [top_candidate, generic_specific_candidate, *stale_candidates, *empty_summary_candidates],
        [top_candidate],
    )

    report = report_path.read_text(encoding="utf-8")
    assert "## Operator Summary" in report
    assert "- run_health:" in report
    assert "- do_not_change_thresholds_yet: true" in report
    assert "## Candidate Funnel" in report
    assert "- raw_candidates: 37" in report
    assert "- stale_candidates: 30" in report
    assert "- top_eligible_candidates: 1" in report
    assert "- rendered_top_candidates: 1" in report
    assert "top_count_too_low" in report
    assert "## Calibration Summary" in report
    assert "likely_source_quality_issue" in report
    assert "## Top Gate Reason Distribution" in report
    assert "excluded_quality_flags=stale_item: 30" in report
    assert "generic_why_for_unspecific_seed_type" in report
    assert "## What-if Gate Simulation" in report
    assert "allow_high_specificity_generic_why" in report
    assert "## Source Survival Table" in report
    assert "source_all_stale" in report
    assert "source_zero_survivors" in report
    assert "## Source Recommendations" in report
    assert "| NPR | keep | has rendered top candidates |" in report
    assert "| BBC News | review | source_all_stale" in report
    assert "| Empty Source | manual_only | many empty summaries" in report
    assert "## Source Allowlist Review Queue" in report
    assert "review_feed_freshness" in report
    assert "## Near Miss Review Queue" in report
    assert "Stale but high scoring infrastructure story" in report
    assert "reason=excluded_quality_flags=stale_item" in report
    assert "## Generic Why / Specificity Examples" in report
    assert "Google spends $2B" in report
    assert "suggested_action=improve_template" in report
    assert "## Generic Why Template Improvement Queue" in report
    assert "number_tension_bridge" in report


def test_operator_summary_primary_bottlenecks(tmp_path) -> None:
    stale_report = tmp_path / "stale.md"
    stale_candidates = [
        {
            "candidate_id": f"stale_{index}",
            "title": f"Stale editorial story {index}",
            "source": "Old Feed",
            "seed_type": "other",
            "quality_flags": ["stale_item"],
            "freshness_status": "stale",
            "recommended_action": "keep_for_later",
            "final_grade": "B",
            "scores": {"total_score": 60 - index, "broadcast_potential_proxy": 3},
        }
        for index in range(6)
    ]
    write_quality_report(stale_report, stale_candidates, [])
    assert "- primary_bottleneck: stale_sources" in stale_report.read_text(encoding="utf-8")

    generic_report = tmp_path / "generic.md"
    top = {
        "candidate_id": "top",
        "title": "Specific top",
        "source": "Mixed Source",
        "seed_type": "ai_knowledge_institution",
        "quality_flags": [],
        "recommended_action": "gather_more_evidence",
        "final_grade": "B",
        "scores": {"total_score": 80, "broadcast_potential_proxy": 4},
    }
    generic_candidates = [
        {
            "candidate_id": f"generic_{index}",
            "title": f"Generic why candidate {index}",
            "source": "Mixed Source",
            "seed_type": "other",
            "quality_flags": [],
            "why_interesting": "사건 자체보다 배경, 이해관계자 연결고리가 있는지 확인",
            "story_specificity": {
                "level": "high",
                "score": 0.8,
                "signals": ["has_number"],
                "generic_why_detected": True,
            },
            "recommended_action": "gather_more_evidence",
            "final_grade": "B",
            "scores": {"total_score": 70 - index, "broadcast_potential_proxy": 3},
        }
        for index in range(4)
    ]
    write_quality_report(generic_report, [top, *generic_candidates], [top])
    assert "- primary_bottleneck: generic_why" in generic_report.read_text(encoding="utf-8")

    weak_report = tmp_path / "weak.md"
    weak_candidates = [
        {
            "candidate_id": f"weak_{index}",
            "title": f"Weak item {index}",
            "source": "Mixed Source",
            "quality_flags": [],
            "recommended_action": "reject",
            "final_grade": "D",
            "scores": {"total_score": 20 - index, "broadcast_potential_proxy": 1},
        }
        for index in range(8)
    ]
    write_quality_report(weak_report, [top, *weak_candidates], [top])
    assert "- primary_bottleneck: low_raw_quality" in weak_report.read_text(encoding="utf-8")

    ok_report = tmp_path / "ok.md"
    ok_candidates = [
        {
            "candidate_id": f"ok_{index}",
            "title": f"Good candidate {index}",
            "source": f"Source {index}",
            "quality_flags": [],
            "recommended_action": "gather_more_evidence",
            "final_grade": "B",
            "scores": {"total_score": 80 - index, "broadcast_potential_proxy": 4},
        }
        for index in range(6)
    ]
    write_quality_report(ok_report, ok_candidates, ok_candidates)
    ok_text = ok_report.read_text(encoding="utf-8")
    assert "- run_health: ok" in ok_text
    assert "- recommended_operator_action: ok_to_append_if_digest_looks_good" in ok_text


def test_what_if_gate_simulation_is_report_only(tmp_path) -> None:
    report_path = tmp_path / "what_if.md"
    current_top = {
        "candidate_id": "current",
        "title": "Current top",
        "source": "BBC News",
        "seed_type": "ai_knowledge_institution",
        "quality_flags": [],
        "recommended_action": "gather_more_evidence",
        "final_grade": "B",
        "scores": {"total_score": 70, "broadcast_potential_proxy": 4},
    }
    high_specificity_generic = {
        "candidate_id": "generic",
        "title": "High specificity generic why story",
        "source": "NPR",
        "seed_type": "other",
        "quality_flags": [],
        "why_interesting": "사건 자체보다 배경, 이해관계자 연결고리가 있는지 확인",
        "story_specificity": {
            "score": 0.83,
            "level": "high",
            "signals": ["has_named_actor", "has_number", "has_mechanism"],
            "generic_why_detected": True,
        },
        "recommended_action": "gather_more_evidence",
        "final_grade": "B",
        "scores": {"total_score": 65, "broadcast_potential_proxy": 4},
    }
    stale_sport = {
        "candidate_id": "stale_sport",
        "title": "Stale sports editorial category",
        "source": "Sports Feed",
        "seed_type": "ai_knowledge_institution",
        "quality_flags": ["stale_item", "sports_only"],
        "freshness_status": "stale",
        "story_specificity": {"score": 0.8, "level": "high", "signals": ["has_number"]},
        "recommended_action": "gather_more_evidence",
        "final_grade": "B",
        "scores": {"total_score": 64, "broadcast_potential_proxy": 4},
    }
    low_score = {
        "candidate_id": "low_score",
        "title": "Low score but viable",
        "source": "BBC News",
        "seed_type": "ai_knowledge_institution",
        "quality_flags": [],
        "recommended_action": "gather_more_evidence",
        "final_grade": "C",
        "scores": {"total_score": 32, "broadcast_potential_proxy": 3},
    }
    candidates = [current_top, high_specificity_generic, stale_sport, low_score]

    assert [item["candidate_id"] for item in top_candidates(candidates)] == ["current"]

    write_quality_report(report_path, candidates, [current_top])
    report = report_path.read_text(encoding="utf-8")
    high_specificity_line = next(
        line for line in report.splitlines() if line.startswith("| allow_high_specificity")
    )
    stale_line = next(
        line for line in report.splitlines() if line.startswith("| allow_stale_editorial")
    )
    lower_line = next(line for line in report.splitlines() if line.startswith("| lower_min_score"))
    assert "High specificity generic why story" in high_specificity_line
    assert "Stale sports editorial category" not in stale_line
    assert "Low score but viable" in lower_line


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
