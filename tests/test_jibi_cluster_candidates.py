from datetime import UTC, datetime

from luddite.agents.jibi.cluster_candidates import cluster_candidates
from luddite.utils.jsonl import read_jsonl, write_jsonl
from luddite.utils.schemas import validate_with_schema


def _candidate(
    candidate_id: str,
    *,
    title: str,
    source: str,
    source_id: str,
    seed_type: str = "productive_finance_policy",
    editorial_category: str = "productive_finance_policy",
    risk_flags: list[str] | None = None,
    risk_level: str = "low",
    action: str = "gather_more_evidence",
    score: float = 60,
    story_key: str | None = None,
    why_interesting: str = "정책금융이 생산적 투자로 이동하는 구조",
    quality_flags: list[str] | None = None,
) -> dict:
    return {
        "candidate_id": candidate_id,
        "title": title,
        "seed_url": f"https://example.com/{candidate_id}",
        "source": source,
        "source_id": source_id,
        "seed_type": seed_type,
        "editorial_category": editorial_category,
        "why_interesting": why_interesting,
        "possible_expansions": ["정책금융 역할", "위험분담", "성장 투자"],
        "evidence_needed": ["공식 자료 또는 숫자/통계 확인"],
        "risk_flags": risk_flags or [],
        "quality_flags": quality_flags or [],
        "risk_level": risk_level,
        "recommended_action": action,
        "story_key": story_key,
        "scores": {"total_score": score, "broadcast_potential_proxy": 4},
        "status": "scored",
    }


def test_cluster_candidates_groups_same_story_key_and_validates_schema(tmp_path) -> None:
    input_path = tmp_path / "scored.jsonl"
    output_path = tmp_path / "clusters.jsonl"
    report_path = tmp_path / "clusters.md"
    digest_path = tmp_path / "clusters_digest.md"
    handoff_path = tmp_path / "handoff.jsonl"
    handoff_digest_path = tmp_path / "handoff.md"
    write_jsonl(
        input_path,
        [
            _candidate(
                "one",
                title="생산적 금융 전환",
                source="연합인포맥스",
                source_id="infomax_manual",
                story_key="productive_finance",
            ),
            _candidate(
                "two",
                title="국민성장펀드와 정책금융",
                source="한국경제",
                source_id="hankyung_manual",
                story_key="productive_finance",
            ),
        ],
    )

    clusters = cluster_candidates(
        input_path=input_path,
        output_path=output_path,
        report_path=report_path,
        digest_path=digest_path,
        handoff_path=handoff_path,
        handoff_digest_path=handoff_digest_path,
        now=datetime(2026, 5, 18, tzinfo=UTC),
    )

    assert len(clusters) == 1
    cluster = clusters[0]
    assert cluster["candidate_ids"] == ["one", "two"]
    assert len(cluster["source_ids"]) == 2
    assert cluster["readiness"] in {"ready_for_anny", "needs_more_evidence"}
    assert validate_with_schema(cluster, "story_seed_schema.json") == []
    assert "slideability" in cluster
    assert cluster["slideability"]["likely_proof_object_types"]
    assert output_path.exists()
    assert report_path.exists()
    assert digest_path.exists()
    assert handoff_path.exists()
    assert handoff_digest_path.exists()
    assert read_jsonl(output_path)[0]["cluster_id"] == cluster["cluster_id"]
    handoff = read_jsonl(handoff_path)[0]
    assert handoff["handoff_priority"] == "high"
    assert "slideability_score" in handoff
    assert handoff["first_slide_idea"]
    assert "Slideability:" in report_path.read_text(encoding="utf-8")
    assert "First slide idea:" in digest_path.read_text(encoding="utf-8")


def test_high_risk_cluster_goes_to_editorial_review(tmp_path) -> None:
    input_path = tmp_path / "scored.jsonl"
    write_jsonl(
        input_path,
        [
            _candidate(
                "politics",
                title="Trump policy conflict",
                source="NPR",
                source_id="npr_rss_candidate",
                seed_type="climate_policy_conflict",
                editorial_category="climate_policy_conflict",
                risk_flags=["political_sensitivity"],
                risk_level="high",
                action="editorial_review",
            )
        ],
    )

    clusters = cluster_candidates(
        input_path=input_path,
        output_path=tmp_path / "clusters.jsonl",
        report_path=tmp_path / "clusters.md",
        digest_path=tmp_path / "clusters_digest.md",
        handoff_path=tmp_path / "handoff.jsonl",
        handoff_digest_path=tmp_path / "handoff.md",
        now=datetime(2026, 5, 18, tzinfo=UTC),
    )

    assert clusters[0]["readiness"] == "editorial_review"
    assert clusters[0]["risk_level"] == "high"


def test_single_thin_candidate_needs_more_evidence_or_keep(tmp_path) -> None:
    input_path = tmp_path / "scored.jsonl"
    write_jsonl(
        input_path,
        [
            _candidate(
                "single",
                title="AI 지식기관 변화",
                source="BBC News",
                source_id="bbc_rss_candidate",
                seed_type="ai_knowledge_institution",
                editorial_category="ai_knowledge_institution",
            )
        ],
    )

    clusters = cluster_candidates(
        input_path=input_path,
        output_path=tmp_path / "clusters.jsonl",
        report_path=tmp_path / "clusters.md",
        digest_path=tmp_path / "clusters_digest.md",
        handoff_path=tmp_path / "handoff.jsonl",
        handoff_digest_path=tmp_path / "handoff.md",
        now=datetime(2026, 5, 18, tzinfo=UTC),
    )

    assert clusters[0]["readiness"] in {"needs_more_evidence", "keep_for_later"}
    assert "추가 독립 후보/출처 1개 이상" in clusters[0]["missing_evidence"]


def test_generic_other_cluster_hidden_from_handoff_but_kept_in_report(tmp_path) -> None:
    input_path = tmp_path / "scored.jsonl"
    report_path = tmp_path / "clusters.md"
    digest_path = tmp_path / "clusters_digest.md"
    handoff_path = tmp_path / "handoff.jsonl"
    handoff_digest_path = tmp_path / "handoff.md"
    write_jsonl(
        input_path,
        [
            _candidate(
                "other",
                title="Odd local item",
                source="BBC News",
                source_id="bbc_rss_candidate",
                seed_type="other",
                editorial_category="other",
                action="keep_for_later",
                why_interesting=(
                    "이 이슈를 단일 기사로 소비하지 않고 "
                    "구조적 연결고리를 확인할 필요가 있음"
                ),
            )
        ],
    )

    clusters = cluster_candidates(
        input_path=input_path,
        output_path=tmp_path / "clusters.jsonl",
        report_path=report_path,
        digest_path=digest_path,
        handoff_path=handoff_path,
        handoff_digest_path=handoff_digest_path,
        now=datetime(2026, 5, 18, tzinfo=UTC),
    )

    assert clusters[0]["generic_story_reason"] is True
    assert "singleton_thin_evidence" in clusters[0]["quality_flags"]
    assert clusters[0]["anny_handoff_ready"] is False
    assert read_jsonl(handoff_path) == []
    assert "generic_story_reason" in report_path.read_text(encoding="utf-8")
    assert "Odd local item" not in digest_path.read_text(encoding="utf-8")


def test_source_roundup_item_is_hidden_from_handoff(tmp_path) -> None:
    input_path = tmp_path / "scored.jsonl"
    handoff_path = tmp_path / "handoff.jsonl"
    write_jsonl(
        input_path,
        [
            _candidate(
                "papers",
                title="The Papers: ministers clash over budget",
                source="BBC News",
                source_id="bbc_rss_candidate",
                seed_type="political_fracture",
                editorial_category="other",
                risk_flags=["political_sensitivity"],
                risk_level="medium",
                action="editorial_review",
                story_key="papers",
            )
        ],
    )

    clusters = cluster_candidates(
        input_path=input_path,
        output_path=tmp_path / "clusters.jsonl",
        report_path=tmp_path / "clusters.md",
        digest_path=tmp_path / "clusters_digest.md",
        handoff_path=handoff_path,
        handoff_digest_path=tmp_path / "handoff.md",
        now=datetime(2026, 5, 18, tzinfo=UTC),
    )

    assert "source_roundup_item" in clusters[0]["quality_flags"]
    assert clusters[0]["handoff_priority"] == "low"
    assert read_jsonl(handoff_path) == []


def test_named_category_candidate_specific_story_appears_in_handoff(tmp_path) -> None:
    input_path = tmp_path / "scored.jsonl"
    handoff_path = tmp_path / "handoff.jsonl"
    handoff_digest_path = tmp_path / "handoff.md"
    write_jsonl(
        input_path,
        [
            _candidate(
                "ai",
                title="AI answers challenge observatory education",
                source="BBC News",
                source_id="bbc_rss_candidate",
                seed_type="ai_knowledge_institution",
                editorial_category="ai_knowledge_institution",
                why_interesting=(
                    "AI 즉답이 편리함을 주는 동시에 생각하는 과정을 건너뛰게 만든다는 "
                    "경고라, 교육·박물관·천문관 같은 지식기관 역할 변화로 확장 가능하다."
                ),
            )
        ],
    )

    clusters = cluster_candidates(
        input_path=input_path,
        output_path=tmp_path / "clusters.jsonl",
        report_path=tmp_path / "clusters.md",
        digest_path=tmp_path / "clusters_digest.md",
        handoff_path=handoff_path,
        handoff_digest_path=handoff_digest_path,
        now=datetime(2026, 5, 18, tzinfo=UTC),
    )

    assert clusters[0]["anny_handoff_ready"] is True
    assert read_jsonl(handoff_path)[0]["story_seed_title"] == "AI 즉답 시대의 지식기관 역할"
    assert "AI 즉답 시대의 지식기관 역할" in handoff_digest_path.read_text(encoding="utf-8")
