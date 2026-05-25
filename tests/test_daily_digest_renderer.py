import csv
import json

from luddite import paths
from luddite.agents.jibi.render_daily_digest import (
    render_daily_digest,
    top_candidates,
    write_alternate_review_board_outputs,
    write_bundle_review_sheet_preview,
    write_quality_report,
    write_syuka_bridge_query_reports,
)
from luddite.agents.jibi.syuka_refresh import refresh_review_board_with_syuka
from luddite.utils.jsonl import write_jsonl


def test_daily_digest_renderer_writes_markdown_and_csv(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("JIBI_REVIEW_BOARD_REGISTERED_AT", "2026-05-17 09:30")
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
    assert "## Story Bundles" in markdown
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
    bundle_csv_path = output_dir / "2026-05-17_bundle_review_sheet.csv"
    with bundle_csv_path.open(encoding="utf-8-sig", newline="") as source:
        bundle_rows = list(csv.DictReader(source))
    assert len(bundle_rows) == 1
    assert list(bundle_rows[0].keys()) == [
        "일시",
        "제목",
        "점수",
        "메인 링크",
        "서브 링크",
        "설명",
        "리뷰-성원",
        "리뷰-동찬",
        "리뷰-형찬",
        "ID",
    ]
    assert bundle_rows[0]["일시"] == "2026-05-17 09:30"
    assert bundle_rows[0]["제목"] == "전당포 주식회사"
    assert bundle_rows[0]["점수"] == "55점 · A · 즉시 스토리라인 후보"
    assert bundle_rows[0]["메인 링크"] == "https://example.com/f88"
    assert bundle_rows[0]["리뷰-성원"] == ""
    assert "story_fit_uncertain" not in bundle_rows[0]["설명"]
    assert "manual_editorial_review" not in bundle_rows[0]["설명"]
    assert "Manual Input의 '전당포 주식회사'" in bundle_rows[0]["설명"]


def test_syuka_bridge_query_report_is_contract_only(tmp_path) -> None:
    candidate = {
        "candidate_id": "youth",
        "title": "‘쉬었음’ 청년층의 특징 및 평가",
        "summary": "청년 노동시장과 경제활동참가율 자료",
        "seed_url": "https://www.bok.or.kr/youth",
        "source": "한국은행",
        "source_role_class": "research_note",
        "seed_type": "macro_research_note",
        "recommended_action": "gather_more_evidence",
        "final_grade": "B",
        "quality_flags": [],
        "risk_flags": [],
        "scores": {"total_score": 70, "broadcast_potential_proxy": 4},
    }

    md_path, json_path = write_syuka_bridge_query_reports(
        run_date="2026-05-25",
        candidates=[candidate],
        top=[candidate],
        output_dir=tmp_path,
        review_history_path=tmp_path / "missing_history.jsonl",
    )

    report = md_path.read_text(encoding="utf-8")
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert "No syuka-ops DB was queried by luddite." in report
    assert payload["queries"][0]["priority"] == "high"
    assert "쉬었음" in payload["queries"][0]["query_terms"]
    assert "비경제활동" in payload["queries"][0]["core_terms"]
    assert "청년" in payload["queries"][0]["context_terms"]
    assert payload["queries"][0]["trigger"] == "heuristic"
    assert payload["queries"][0]["source_review_note_excerpt"] == ""
    assert "## Syuka Bridge Handoff Notes" in report


def test_alternate_review_board_excludes_current_board_fingerprint(tmp_path) -> None:
    current = {
        "candidate_id": "current",
        "title": "‘쉬었음’ 청년층의 특징 및 평가",
        "summary": "청년 노동시장과 경제활동참가율 자료",
        "seed_url": "https://www.bok.or.kr/youth",
        "source": "한국은행",
        "source_role_class": "research_note",
        "seed_type": "macro_research_note",
        "recommended_action": "gather_more_evidence",
        "final_grade": "B",
        "quality_flags": [],
        "risk_flags": [],
        "scores": {"total_score": 70, "broadcast_potential_proxy": 4},
    }
    alternate = {
        "candidate_id": "alternate",
        "title": "스타벅스 선불충전금 환불 사각지대",
        "summary": "소비자 선불충전금과 환불 규제 사각지대",
        "seed_url": "https://www.yna.co.kr/starbucks",
        "source": "연합뉴스 경제",
        "source_role_class": "public_wire",
        "seed_type": "consumer_regulation_gap",
        "recommended_action": "gather_more_evidence",
        "final_grade": "B",
        "quality_flags": [],
        "risk_flags": [],
        "scores": {"total_score": 60, "broadcast_potential_proxy": 4},
    }
    candidates = [current, alternate]
    current_csv = tmp_path / "2026-05-25_bundle_review_sheet.csv"
    write_bundle_review_sheet_preview(
        current_csv,
        candidates,
        [current],
        "2026-05-25",
        review_board_limit=1,
    )

    alt_csv, metadata_path, report_path = write_alternate_review_board_outputs(
        tmp_path / "2026-05-25_bundle_review_alt_sheet.csv",
        tmp_path / "jibi_alternate_review_board_2026-05-25.md",
        candidates,
        [current],
        "2026-05-25",
        review_board_limit=1,
        current_board_csv_path=current_csv,
    )

    with alt_csv.open(encoding="utf-8-sig", newline="") as source:
        rows = list(csv.DictReader(source))
    assert len(rows) == 1
    assert "스타벅스" in rows[0]["제목"]
    assert metadata_path.exists()
    assert "live `Jibi` sheet was not replaced" in report_path.read_text(encoding="utf-8")


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


def test_top_candidates_applies_source_role_caps_before_backfill() -> None:
    candidates = [
        {
            "candidate_id": f"policy_{index}",
            "source": f"Policy {index}",
            "source_role_class": "policy_release",
            "seed_type": "policy_release_seed",
            "final_grade": "B",
            "recommended_action": "gather_more_evidence",
            "quality_flags": [],
            "scores": {"total_score": 100 - index, "broadcast_potential_proxy": 5},
        }
        for index in range(3)
    ]
    candidates.extend(
        [
            {
                "candidate_id": f"research_{index}",
                "source": f"BOK {index}",
                "source_role_class": "research_note",
                "seed_type": "policy_research_note",
                "final_grade": "B",
                "recommended_action": "gather_more_evidence",
                "quality_flags": [],
                "scores": {"total_score": 90 - index, "broadcast_potential_proxy": 5},
            }
            for index in range(2)
        ]
    )
    candidates.extend(
        [
            {
                "candidate_id": f"public_{index}",
                "source": f"Yonhap {index}",
                "source_role_class": "public_wire",
                "seed_type": "public_ai_governance",
                "final_grade": "B",
                "recommended_action": "gather_more_evidence",
                "quality_flags": [],
                "scores": {"total_score": 80 - index, "broadcast_potential_proxy": 5},
            }
            for index in range(2)
        ]
    )

    selected = top_candidates(candidates, limit=6, max_per_source=10)

    selected_ids = [candidate["candidate_id"] for candidate in selected]
    assert selected_ids == [
        "policy_0",
        "policy_1",
        "research_0",
        "research_1",
        "public_0",
        "public_1",
    ]
    assert "policy_2" not in selected_ids


def test_top_candidates_backfills_when_role_caps_underfill() -> None:
    candidates = [
        {
            "candidate_id": f"policy_{index}",
            "source": f"Policy {index}",
            "source_role_class": "policy_release",
            "seed_type": "policy_release_seed",
            "final_grade": "B",
            "recommended_action": "gather_more_evidence",
            "quality_flags": [],
            "scores": {"total_score": 100 - index, "broadcast_potential_proxy": 5},
        }
        for index in range(5)
    ]

    selected = top_candidates(candidates, limit=5, max_per_source=10)

    assert [candidate["candidate_id"] for candidate in selected] == [
        "policy_0",
        "policy_1",
        "policy_2",
        "policy_3",
        "policy_4",
    ]


def test_quality_report_includes_source_role_cap_and_storyline_audit(tmp_path) -> None:
    report_path = tmp_path / "source_role_caps.md"
    candidates = [
        {
            "candidate_id": "bok_youth_rest",
            "title": "BOK '쉬었음' 청년층의 특징 및 평가",
            "source": "한국은행",
            "source_role_class": "research_note",
            "seed_type": "macro_research_note",
            "why_interesting": "청년 노동시장 밖 인구를 설명하는 연구노트",
            "quality_flags": [],
            "risk_flags": [],
            "recommended_action": "gather_more_evidence",
            "final_grade": "B",
            "scores": {"total_score": 100, "broadcast_potential_proxy": 5},
        },
        {
            "candidate_id": "bok_youth_male",
            "title": "BOK 남성 청년층 경제활동참가율 하락",
            "source": "한국은행",
            "source_role_class": "research_note",
            "seed_type": "macro_research_note",
            "why_interesting": "청년 노동시장 이탈을 다른 지표로 설명",
            "quality_flags": [],
            "risk_flags": [],
            "recommended_action": "gather_more_evidence",
            "final_grade": "B",
            "scores": {"total_score": 99, "broadcast_potential_proxy": 5},
        },
        {
            "candidate_id": "policy_apec",
            "title": "APEC 통상장관회의, AI·디지털·녹색산업 협력 논의",
            "source": "정책브리핑",
            "source_role_class": "policy_release",
            "seed_type": "policy_release_evidence",
            "quality_flags": [
                "policy_release_evidence_default",
                "policy_release_meeting_only",
            ],
            "risk_flags": [],
            "recommended_action": "gather_more_evidence",
            "final_grade": "B",
            "scores": {"total_score": 98, "broadcast_potential_proxy": 5},
        },
        {
            "candidate_id": "amotech",
            "title": "아모텍, 350억원 주주배정 유상증자 결정",
            "source": "연합뉴스 경제",
            "source_role_class": "public_wire",
            "seed_type": "single_company_financing",
            "quality_flags": ["single_company_frame"],
            "risk_flags": ["investment_advice_risk", "corporate_promo_risk"],
            "recommended_action": "gather_more_evidence",
            "final_grade": "B",
            "scores": {"total_score": 97, "broadcast_potential_proxy": 5},
        },
        *[
            {
                "candidate_id": f"policy_extra_{index}",
                "title": f"정책브리핑 추가 회의 보도자료 {index}",
                "source": f"정책브리핑 {index}",
                "source_role_class": "policy_release",
                "seed_type": "policy_release_seed",
                "quality_flags": [],
                "risk_flags": [],
                "recommended_action": "gather_more_evidence",
                "final_grade": "B",
                "scores": {"total_score": 70 - index, "broadcast_potential_proxy": 4},
            }
            for index in range(4)
        ],
        *[
            {
                "candidate_id": f"public_extra_{index}",
                "title": f"연합뉴스 AI 공공활용 후보 {index}",
                "source": f"연합뉴스 산업 {index}",
                "source_role_class": "public_wire",
                "seed_type": "public_ai_governance",
                "quality_flags": [],
                "risk_flags": [],
                "recommended_action": "gather_more_evidence",
                "final_grade": "B",
                "scores": {"total_score": 60 - index, "broadcast_potential_proxy": 4},
            }
            for index in range(6)
        ],
    ]
    top = top_candidates(candidates, limit=6, max_per_source=10)

    write_quality_report(report_path, candidates, top, limit=6, max_per_source=10)

    report = report_path.read_text(encoding="utf-8")
    assert "## Source Role Cap Status" in report
    assert "- policy_release: selected=2 cap=2" in report
    assert "## Source Role Cap-blocked Candidates" in report
    assert "source_role_cap_reached=policy_release:2" in report
    assert "## Storyline Fit Audit" in report
    assert "merge_with_other_candidate" in report
    assert "evidence_only" in report
    assert "demote_or_reject" in report


def test_story_bundle_review_groups_bok_youth_labor(tmp_path) -> None:
    report_path = tmp_path / "bundles.md"
    youth_rest = {
        "candidate_id": "bok_youth_rest",
        "title": "BOK '쉬었음' 청년층의 특징 및 평가",
        "source": "한국은행",
        "source_role_class": "research_note",
        "seed_type": "macro_research_note",
        "why_interesting": "청년 노동시장 밖 인구를 설명하는 연구노트",
        "quality_flags": [],
        "risk_flags": [],
        "recommended_action": "gather_more_evidence",
        "final_grade": "B",
        "scores": {"total_score": 80, "broadcast_potential_proxy": 5},
    }
    youth_male = {
        "candidate_id": "bok_youth_male",
        "title": "BOK 남성 청년층 경제활동참가율 하락",
        "source": "한국은행",
        "source_role_class": "research_note",
        "seed_type": "macro_research_note",
        "why_interesting": "청년 노동시장 이탈을 다른 지표로 설명",
        "quality_flags": [],
        "risk_flags": [],
        "recommended_action": "gather_more_evidence",
        "final_grade": "B",
        "scores": {"total_score": 75, "broadcast_potential_proxy": 5},
    }

    write_quality_report(report_path, [youth_rest, youth_male], [youth_rest, youth_male])

    report = report_path.read_text(encoding="utf-8")
    assert "## Story Bundle Review" in report
    assert "청년 노동시장 이탈 / 쉬었음 / 경제활동참가율" in report
    assert "merged_seed" in report
    assert "BOK '쉬었음' 청년층의 특징 및 평가" in report
    assert "supporting: BOK 남성 청년층 경제활동참가율 하락" in report

    csv_path = tmp_path / "2026-05-23_bundle_review_sheet.csv"
    write_bundle_review_sheet_preview(
        csv_path,
        [youth_rest, youth_male],
        [youth_rest],
        "2026-05-23",
    )
    with csv_path.open(encoding="utf-8-sig", newline="") as source:
        rows = list(csv.DictReader(source))
    metadata_path = csv_path.with_name(f"{csv_path.stem}_metadata.json")
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    assert rows[0]["제목"] == "일하지도, 구직하지도 않는 청년들: '쉬었음'의 경제학"
    assert "merged_seed" not in rows[0]["설명"]
    assert "review_primary_and_bundle_supporting" not in rows[0]["설명"]
    assert "실업률만 보면 안 보이는 노동시장 밖 청년" in rows[0]["설명"]
    assert rows[0]["점수"] == "80점 · B · 자료 보강 필요"
    assert metadata["rows"][0]["ID"] == rows[0]["ID"]
    assert metadata["rows"][0]["source"] == "한국은행"
    assert metadata["rows"][0]["source_role"] == "research_note"
    assert metadata["rows"][0]["seed_type"] == "macro_research_note"
    assert metadata["rows"][0]["bundle_type"] == "merged_seed"
    assert metadata["rows"][0]["run_date"] == "2026-05-23"


def test_bundle_review_editorial_override_by_id_preserves_auto_copy(tmp_path) -> None:
    candidate = {
        "candidate_id": "bok_youth_rest",
        "title": "BOK '쉬었음' 청년층의 특징 및 평가",
        "seed_url": "https://www.bok.or.kr/youth",
        "source": "한국은행",
        "source_role_class": "research_note",
        "seed_type": "macro_research_note",
        "why_interesting": "청년 노동시장 밖 인구를 설명하는 연구노트",
        "quality_flags": [],
        "risk_flags": [],
        "recommended_action": "gather_more_evidence",
        "final_grade": "B",
        "scores": {"total_score": 80, "broadcast_potential_proxy": 5},
    }
    csv_path = tmp_path / "2026-05-23_bundle_review_sheet.csv"
    write_bundle_review_sheet_preview(
        csv_path,
        [candidate],
        [candidate],
        "2026-05-23",
    )
    metadata_path = csv_path.with_name(f"{csv_path.stem}_metadata.json")
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    review_id = metadata["rows"][0]["ID"]
    override_path = tmp_path / "overrides.json"
    override_path.write_text(
        json.dumps(
            {
                "run_date": "2026-05-23",
                "editor": "codex",
                "items": {
                    review_id: {
                        "title": "청년 노동시장 밖으로 빠지는 사람들",
                        "description": "실업률만으로 안 보이는 청년 이탈을 설명하는 후보입니다.",
                        "reason": "reviewer-facing copy",
                    }
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    write_bundle_review_sheet_preview(
        csv_path,
        [candidate],
        [candidate],
        "2026-05-23",
        editorial_overrides_path=override_path,
    )

    with csv_path.open(encoding="utf-8-sig", newline="") as source:
        rows = list(csv.DictReader(source))
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    assert rows[0]["제목"] == "청년 노동시장 밖으로 빠지는 사람들"
    assert rows[0]["설명"] == "실업률만으로 안 보이는 청년 이탈을 설명하는 후보입니다."
    assert metadata["rows"][0]["auto_title"] != rows[0]["제목"]
    assert "실업률만 보면 안 보이는" in metadata["rows"][0]["auto_description"]
    assert metadata["rows"][0]["editorial_override_applied"] is True
    assert metadata["rows"][0]["editorial_override_reason"] == "reviewer-facing copy"


def test_bundle_review_editorial_override_by_story_fingerprint(tmp_path) -> None:
    candidate = {
        "candidate_id": "asset_tokenization",
        "title": "국내외 자산 토큰화 현황 및 향후 정책 과제",
        "seed_url": "https://www.bok.or.kr/rwa",
        "source": "한국은행",
        "source_role_class": "research_note",
        "seed_type": "policy_research_note",
        "why_interesting": "자산 토큰화 정책 과제",
        "quality_flags": [],
        "risk_flags": [],
        "recommended_action": "gather_more_evidence",
        "final_grade": "B",
        "scores": {"total_score": 75, "broadcast_potential_proxy": 4},
    }
    csv_path = tmp_path / "2026-05-23_bundle_review_sheet.csv"
    write_bundle_review_sheet_preview(csv_path, [candidate], [candidate], "2026-05-23")
    metadata = json.loads(
        csv_path.with_name(f"{csv_path.stem}_metadata.json").read_text(encoding="utf-8")
    )
    story_fingerprint = metadata["rows"][0]["story_fingerprint"]
    override_path = tmp_path / "overrides.json"
    override_path.write_text(
        json.dumps(
            {
                "items": {
                    story_fingerprint: {
                        "title": "집도, 채권도 쪼개 사고파는 시대",
                        "description": "RWA가 제도권 금융으로 들어오는 흐름을 보는 후보입니다.",
                    }
                }
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    write_bundle_review_sheet_preview(
        csv_path,
        [candidate],
        [candidate],
        "2026-05-23",
        editorial_overrides_path=override_path,
    )

    with csv_path.open(encoding="utf-8-sig", newline="") as source:
        rows = list(csv.DictReader(source))
    assert rows[0]["제목"] == "집도, 채권도 쪼개 사고파는 시대"
    assert rows[0]["설명"] == "RWA가 제도권 금융으로 들어오는 흐름을 보는 후보입니다."


def test_bundle_review_missing_editorial_override_is_harmless(tmp_path) -> None:
    candidate = {
        "candidate_id": "ocean",
        "title": "The network watching the world’s oceans",
        "seed_url": "https://theconversation.com/ocean",
        "source": "The Conversation",
        "source_role_class": "academic_explainer",
        "seed_type": "academic_explainer",
        "why_interesting": "해양 관측 네트워크 설명",
        "quality_flags": [],
        "risk_flags": [],
        "recommended_action": "gather_more_evidence",
        "final_grade": "B",
        "scores": {"total_score": 60, "broadcast_potential_proxy": 4},
    }
    csv_path = tmp_path / "2026-05-23_bundle_review_sheet.csv"

    write_bundle_review_sheet_preview(
        csv_path,
        [candidate],
        [candidate],
        "2026-05-23",
        editorial_overrides_path=tmp_path / "missing.json",
    )

    metadata = json.loads(
        csv_path.with_name(f"{csv_path.stem}_metadata.json").read_text(encoding="utf-8")
    )
    assert metadata["visible_columns"] == [
        "일시",
        "제목",
        "점수",
        "메인 링크",
        "서브 링크",
        "설명",
        "리뷰-성원",
        "리뷰-동찬",
        "리뷰-형찬",
        "ID",
    ]
    assert metadata["rows"][0]["editorial_override_applied"] is False


def test_bundle_review_adds_syuka_similarity_metadata_and_annotation(tmp_path) -> None:
    youth_rest = {
        "candidate_id": "bok_youth_rest",
        "title": "BOK '쉬었음' 청년층의 특징 및 평가",
        "seed_url": "https://www.bok.or.kr/youth",
        "source": "한국은행",
        "source_role_class": "research_note",
        "seed_type": "macro_research_note",
        "why_interesting": "청년 노동시장 밖 인구를 설명하는 연구노트",
        "quality_flags": [],
        "risk_flags": [],
        "recommended_action": "gather_more_evidence",
        "final_grade": "B",
        "scores": {"total_score": 80, "broadcast_potential_proxy": 5},
    }
    syuka_report = tmp_path / "jibi_syuka_snapshot_matches_2026-05-23.json"
    syuka_report.write_text(
        json.dumps(
            {
                "run_date": "2026-05-23",
                "results": [
                    {
                        "story_fingerprint": "youth_labor_exit",
                        "query_title": "청년 노동시장 이탈 / 쉬었음 / 경제활동참가율",
                        "recommendation": "duplicate",
                        "past_video_response_signal": "duplicate_do_not_repeat",
                        "matches": [
                            {
                                "title": "'쉬었음' 역대 최고인데, 실업률은 왜 최저인가?",
                                "match_score": 12,
                                "matched_terms": ["쉬었음", "경제활동참가율"],
                                "matched_fields": ["title", "analysis"],
                                "url": "https://youtu.be/youth",
                                "view_count": 1500000,
                                "like_count": 32000,
                                "upload_date": "20260501",
                            }
                        ],
                    }
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    csv_path = tmp_path / "2026-05-23_bundle_review_sheet.csv"

    write_bundle_review_sheet_preview(
        csv_path,
        [youth_rest],
        [youth_rest],
        "2026-05-23",
        syuka_similarity_report_path=syuka_report,
    )

    with csv_path.open(encoding="utf-8-sig", newline="") as source:
        rows = list(csv.DictReader(source))
    metadata = json.loads(
        csv_path.with_name(f"{csv_path.stem}_metadata.json").read_text(encoding="utf-8")
    )
    assert list(rows[0].keys()) == [
        "일시",
        "제목",
        "점수",
        "메인 링크",
        "서브 링크",
        "설명",
        "리뷰-성원",
        "리뷰-동찬",
        "리뷰-형찬",
        "ID",
    ]
    assert "과거 영상과 강하게 겹칠 수 있습니다" in rows[0]["설명"]
    assert "'쉬었음' 역대 최고인데, 실업률은 왜 최저인가?" in rows[0]["설명"]
    assert "2026-05-01" in rows[0]["설명"]
    assert "조회 150만" in rows[0]["설명"]
    assert "좋아요 3.2만" in rows[0]["설명"]
    assert metadata["rows"][0]["syuka_similarity"]["recommendation"] == "duplicate"
    assert metadata["rows"][0]["syuka_similarity"]["top_match_score"] == 12
    assert metadata["rows"][0]["syuka_similarity"]["like_count"] == 32000
    assert metadata["rows"][0]["syuka_similarity"]["match_confidence"] == "high"
    assert metadata["rows"][0]["syuka_similarity"]["match_reason"] == "core_title_match"
    assert metadata["rows"][0]["syuka_similarity"]["display_on_board"] is True


def test_bundle_review_keeps_low_confidence_syuka_metrics_out_of_description(
    tmp_path,
) -> None:
    candidate = {
        "candidate_id": "ai_religion",
        "title": "AI에게 위로받는 시대",
        "seed_url": "https://example.com/ai-religion",
        "source": "The Conversation",
        "source_role_class": "academic_explainer",
        "seed_type": "academic_explainer",
        "why_interesting": "AI와 종교 상담 변화",
        "quality_flags": [],
        "risk_flags": [],
        "recommended_action": "gather_more_evidence",
        "final_grade": "B",
        "scores": {"total_score": 60, "broadcast_potential_proxy": 4},
    }
    syuka_report = tmp_path / "jibi_syuka_snapshot_matches_2026-05-23.json"
    syuka_report.write_text(
        json.dumps(
            {
                "run_date": "2026-05-23",
                "results": [
                    {
                        "story_fingerprint": "story_737f849b3f",
                        "query_title": "AI에게 위로받는 시대",
                        "recommendation": "needs_human_check",
                        "past_video_response_signal": "needs_human_check",
                        "matches": [
                            {
                                "title": "AI가 바꾸는 주식시장",
                                "match_score": 2,
                                "matched_terms": ["AI"],
                                "matched_fields": ["transcript"],
                                "url": "https://youtu.be/ai",
                                "view_count": 2000000,
                                "like_count": 50000,
                                "upload_date": "20240101",
                            }
                        ],
                    }
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    csv_path = tmp_path / "2026-05-23_bundle_review_sheet.csv"

    write_bundle_review_sheet_preview(
        csv_path,
        [candidate],
        [candidate],
        "2026-05-23",
        syuka_similarity_report_path=syuka_report,
    )

    with csv_path.open(encoding="utf-8-sig", newline="") as source:
        rows = list(csv.DictReader(source))
    metadata = json.loads(
        csv_path.with_name(f"{csv_path.stem}_metadata.json").read_text(encoding="utf-8")
    )
    assert "과거 영상과 약하게 겹칠 수 있어" in rows[0]["설명"]
    assert "AI가 바꾸는 주식시장" not in rows[0]["설명"]
    assert "조회 200만" not in rows[0]["설명"]
    similarity = metadata["rows"][0]["syuka_similarity"]
    assert similarity["match_confidence"] == "low"
    assert similarity["match_reason"] == "transcript_only"
    assert similarity["display_on_board"] is False


def test_bundle_review_does_not_annotate_safe_new_angle(tmp_path) -> None:
    candidate = {
        "candidate_id": "ocean",
        "title": "The network watching the world’s oceans",
        "seed_url": "https://theconversation.com/ocean",
        "source": "The Conversation",
        "source_role_class": "academic_explainer",
        "seed_type": "academic_explainer",
        "why_interesting": "해양 관측 네트워크 설명",
        "quality_flags": [],
        "risk_flags": [],
        "recommended_action": "gather_more_evidence",
        "final_grade": "B",
        "scores": {"total_score": 60, "broadcast_potential_proxy": 4},
    }
    syuka_report = tmp_path / "jibi_syuka_snapshot_matches_2026-05-23.json"
    syuka_report.write_text(
        json.dumps(
            {
                "run_date": "2026-05-23",
                "results": [
                    {
                        "story_fingerprint": "story_57025461e7",
                        "query_title": "The network watching the world’s oceans",
                        "recommendation": "safe_new_angle",
                        "past_video_response_signal": "safe_new_angle",
                        "matches": [],
                    }
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    csv_path = tmp_path / "2026-05-23_bundle_review_sheet.csv"

    write_bundle_review_sheet_preview(
        csv_path,
        [candidate],
        [candidate],
        "2026-05-23",
        syuka_similarity_report_path=syuka_report,
    )

    with csv_path.open(encoding="utf-8-sig", newline="") as source:
        rows = list(csv.DictReader(source))
    assert "신규성" not in rows[0]["설명"]
    assert "로컬 snapshot" not in rows[0]["설명"]


def test_bundle_review_marks_reappearing_story_from_history(tmp_path) -> None:
    history_path = tmp_path / "jibi_review_board_history.jsonl"
    history_path.write_text(
        json.dumps(
            {
                "run_date": "2026-05-22",
                "rows": [
                    {
                        "ID": "2026-05-22:story_bundle_2bdd0b9bb3",
                        "제목": "청년 노동시장",
                        "리뷰-성원": "reject — 이미 다룬 소재",
                        "story_fingerprint": "story_bundle_2bdd0b9bb3",
                    }
                ],
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    youth_rest = {
        "candidate_id": "bok_youth_rest",
        "title": "BOK '쉬었음' 청년층의 특징 및 평가",
        "source": "한국은행",
        "source_role_class": "research_note",
        "seed_type": "macro_research_note",
        "why_interesting": "청년 노동시장 밖 인구를 설명하는 연구노트",
        "quality_flags": [],
        "risk_flags": [],
        "recommended_action": "gather_more_evidence",
        "final_grade": "B",
        "scores": {"total_score": 80, "broadcast_potential_proxy": 5},
    }
    csv_path = tmp_path / "2026-05-23_bundle_review_sheet.csv"

    write_bundle_review_sheet_preview(
        csv_path,
        [youth_rest],
        [youth_rest],
        "2026-05-23",
        review_history_path=history_path,
    )

    with csv_path.open(encoding="utf-8-sig", newline="") as source:
        rows = list(csv.DictReader(source))
    assert "이전에 reject 의견" in rows[0]["설명"]


def test_bundle_review_limit_and_near_miss_sublinks(tmp_path) -> None:
    top = {
        "candidate_id": "ai_primary",
        "title": "공공기관 AI 도입",
        "seed_url": "https://example.com/ai-primary",
        "source": "연합뉴스 산업",
        "source_role_class": "public_wire",
        "seed_type": "public_ai_governance",
        "recommended_action": "gather_more_evidence",
        "final_grade": "B",
        "scores": {"total_score": 90, "broadcast_potential_proxy": 5},
    }
    near_misses = [
        {
            "candidate_id": f"ai_support_{index}",
            "title": f"AI 드론 현장 사례 {index}",
            "seed_url": f"https://example.com/ai-support-{index}",
            "source": "연합뉴스 산업",
            "source_role_class": "public_wire",
            "seed_type": "public_ai_enforcement",
            "recommended_action": "gather_more_evidence",
            "final_grade": "B",
            "scores": {"total_score": 80 - index, "broadcast_potential_proxy": 5},
        }
        for index in range(4)
    ]
    csv_path = tmp_path / "2026-05-23_bundle_review_sheet.csv"

    write_bundle_review_sheet_preview(
        csv_path,
        [top, *near_misses],
        [top],
        "2026-05-23",
        review_board_limit=1,
        bundle_near_miss_limit=4,
        review_history_path=tmp_path / "missing_history.jsonl",
    )

    with csv_path.open(encoding="utf-8-sig", newline="") as source:
        rows = list(csv.DictReader(source))
    assert len(rows) == 1
    assert rows[0]["제목"] == "AI가 공무원 보고서와 현장 치안에 들어올 때"
    assert rows[0]["서브 링크"].count("https://example.com/ai-support-") == 3


def test_story_bundle_review_marks_policy_status_as_evidence(tmp_path) -> None:
    report_path = tmp_path / "policy_status_bundle.md"
    status_release = {
        "candidate_id": "policy_oil_status",
        "title": "[행정안전부](보도참고자료) 고유가 피해지원금 신청·지급 현황",
        "source": "정책브리핑",
        "source_role_class": "policy_release",
        "seed_type": "policy_release_seed",
        "quality_flags": ["policy_release_seed_signals=material_number,life_impact"],
        "risk_flags": [],
        "recommended_action": "gather_more_evidence",
        "final_grade": "B",
        "scores": {"total_score": 70, "broadcast_potential_proxy": 4},
    }

    write_quality_report(report_path, [status_release], [status_release])

    report = report_path.read_text(encoding="utf-8")
    assert "고유가 지원금 / 에너지 가격 충격 evidence" in report
    assert "evidence_cluster" in report
    assert "| none | evidence: [행정안전부](보도참고자료) 고유가 피해지원금" in report
    assert "official_release_meeting_or_evidence_default" in report


def test_story_bundle_review_keeps_platform_fee_as_needs_external_sources(
    tmp_path,
) -> None:
    report_path = tmp_path / "platform_bundle.md"
    platform = {
        "candidate_id": "platform_fee",
        "title": "쿠팡이츠, 무료 배달비 업주 전가 논란",
        "source": "연합뉴스 산업",
        "source_role_class": "public_wire",
        "seed_type": "platform_labor_market",
        "quality_flags": [],
        "risk_flags": [],
        "recommended_action": "gather_more_evidence",
        "final_grade": "B",
        "scores": {"total_score": 67, "broadcast_potential_proxy": 5},
    }

    before = [item["candidate_id"] for item in top_candidates([platform])]
    write_quality_report(report_path, [platform], [platform])
    after = [item["candidate_id"] for item in top_candidates([platform])]

    report = report_path.read_text(encoding="utf-8")
    assert before == after == ["platform_fee"]
    assert "플랫폼 무료배달 / 수수료 비용 배분" in report
    assert "needs_external_sources" in report
    assert "collect_second_source_and_numbers" in report


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
    assert "## Review Board Experiment Snapshot" in report
    assert "- board_row_count:" in report
    assert "- sublink_count_distribution:" in report
    assert "- score_distribution:" in report
    assert "## Source Mix Experiment Review" in report
    assert "BBC News: raw=1, top=1, recent=1" in report
    assert "NPR: raw=1, top=0, recent=0, stale=1" in report
    assert "## Near Duplicate Groups" in report
    assert "`nd_abc`" in report
    assert "shared_tokens=" in report


def test_quality_report_includes_syuka_similarity_summary_when_available(tmp_path) -> None:
    report_path = tmp_path / "quality.md"
    syuka_report = tmp_path / "jibi_syuka_snapshot_matches_2026-05-25.json"
    syuka_report.write_text(
        json.dumps(
            {
                "run_date": "2026-05-25",
                "results": [
                    {
                        "story_fingerprint": "youth_labor_exit",
                        "query_title": "청년 노동시장 이탈 / 쉬었음 / 경제활동참가율",
                        "recommendation": "duplicate",
                        "past_video_response_signal": "duplicate_do_not_repeat",
                        "matches": [
                            {
                                "title": "'쉬었음' 역대 최고인데, 실업률은 왜 최저인가?",
                                "match_score": 12,
                                "matched_terms": ["쉬었음"],
                                "matched_fields": ["title"],
                                "url": "https://youtu.be/youth",
                                "view_count": 1500000,
                                "like_count": 32000,
                                "upload_date": "20260501",
                            }
                        ],
                    },
                    {
                        "story_fingerprint": "story_ocean",
                        "query_title": "해양 관측 네트워크",
                        "recommendation": "safe_new_angle",
                        "past_video_response_signal": "safe_new_angle",
                        "matches": [],
                    },
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    candidate = {
        "candidate_id": "youth",
        "title": "BOK '쉬었음' 청년층의 특징 및 평가",
        "source": "한국은행",
        "source_role_class": "research_note",
        "seed_type": "macro_research_note",
        "quality_flags": [],
        "risk_flags": [],
        "recommended_action": "gather_more_evidence",
        "final_grade": "B",
        "scores": {"total_score": 80, "broadcast_potential_proxy": 5},
    }

    write_quality_report(
        report_path,
        [candidate],
        [candidate],
        syuka_similarity_report_path=syuka_report,
    )

    report = report_path.read_text(encoding="utf-8")
    assert "## Syuka Similarity Summary" in report
    assert "- duplicate: 1" in report
    assert "- safe_new_angle: 1" in report
    assert "duplicate_do_not_repeat" in report


def test_quality_report_handles_missing_syuka_similarity_report(tmp_path) -> None:
    report_path = tmp_path / "quality.md"
    candidate = {
        "candidate_id": "youth",
        "title": "BOK '쉬었음' 청년층의 특징 및 평가",
        "source": "한국은행",
        "source_role_class": "research_note",
        "seed_type": "macro_research_note",
        "quality_flags": [],
        "risk_flags": [],
        "recommended_action": "gather_more_evidence",
        "final_grade": "B",
        "scores": {"total_score": 80, "broadcast_potential_proxy": 5},
    }

    write_quality_report(
        report_path,
        [candidate],
        [candidate],
        syuka_similarity_report_path=tmp_path / "missing.json",
    )

    report = report_path.read_text(encoding="utf-8")
    assert "## Syuka Similarity Summary" in report
    assert "- report_status: missing_or_empty" in report


def test_syuka_refresh_writes_manifest_and_operating_log(tmp_path, monkeypatch) -> None:
    input_path = tmp_path / "scored.jsonl"
    output_dir = tmp_path / "daily_digest"
    reports_dir = tmp_path / "reports"
    overrides_dir = tmp_path / "editorial_overrides"
    inbox_dir = tmp_path / "inbox"
    inbox_dir.mkdir()
    (inbox_dir / "rss_2026-05-25.jsonl").write_text(
        json.dumps({"url": "https://example.com/youth"}, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(paths, "REPORTS_DIR", reports_dir)
    monkeypatch.setattr(paths, "JIBI_EDITORIAL_OVERRIDES_DIR", overrides_dir)
    monkeypatch.setattr(paths, "ARTICLE_INBOX_DIR", inbox_dir)
    write_jsonl(
        input_path,
        [
            {
                "candidate_id": "bok_youth_rest",
                "title": "BOK '쉬었음' 청년층의 특징 및 평가",
                "seed_url": "https://www.bok.or.kr/youth",
                "source": "한국은행",
                "source_role_class": "research_note",
                "seed_type": "macro_research_note",
                "why_interesting": "청년 노동시장 밖 인구를 설명하는 연구노트",
                "quality_flags": [],
                "risk_flags": [],
                "recommended_action": "gather_more_evidence",
                "final_grade": "B",
                "scores": {"total_score": 80, "broadcast_potential_proxy": 5},
            }
        ],
    )

    payload = refresh_review_board_with_syuka(
        run_date="2026-05-25",
        input_path=input_path,
        output_dir=output_dir,
        syuka_data_dir=tmp_path / "missing_syuka",
        review_history_path=tmp_path / "missing_history.jsonl",
    )

    assert payload["render_pass_1_status"] == "succeeded"
    assert payload["render_pass_2_status"] == "succeeded"
    assert payload["board_row_count"] == 1
    assert payload["syuka_probe_status"] == "no_db_found"
    assert payload["sheet_replace_status"] == "not_requested"
    assert (reports_dir / "jibi_syuka_refresh_2026-05-25.md").exists()
    log_path = reports_dir / "jibi_operating_experiment_log.jsonl"
    assert log_path.exists()
    log = json.loads(log_path.read_text(encoding="utf-8").strip())
    assert log["rss_raw_count"] == 1
    assert log["rss_unique_count"] == 1
    assert log["sheet_mode"] == "none"


def test_quality_report_contains_source_mix_review_focus(tmp_path) -> None:
    report_path = tmp_path / "quality_source_mix.md"
    candidates = [
        {
            "candidate_id": "bok",
            "title": "BOK 자산 토큰화 연구노트",
            "source": "한국은행",
            "source_id": "bok",
            "source_role_class": "research_note",
            "seed_type": "policy_research_note",
            "quality_flags": [],
            "recommended_action": "gather_more_evidence",
            "final_grade": "B",
            "scores": {"total_score": 75, "broadcast_potential_proxy": 4},
        },
        {
            "candidate_id": "policy",
            "title": "정책브리핑 가계 지원 보도자료",
            "source": "정책브리핑",
            "source_id": "korea_policy_briefing",
            "source_role_class": "policy_release",
            "seed_type": "policy_release_seed",
            "quality_flags": [],
            "recommended_action": "gather_more_evidence",
            "final_grade": "B",
            "scores": {"total_score": 70, "broadcast_potential_proxy": 4},
        },
        {
            "candidate_id": "conversation",
            "title": "SpaceX academic explainer",
            "source": "The Conversation",
            "source_id": "the_conversation",
            "source_role_class": "academic_explainer",
            "seed_type": "academic_explainer",
            "quality_flags": [],
            "recommended_action": "gather_more_evidence",
            "final_grade": "B",
            "scores": {"total_score": 68, "broadcast_potential_proxy": 4},
        },
        {
            "candidate_id": "yonhap",
            "title": "연합뉴스 산업 AI 드론",
            "source": "연합뉴스 산업",
            "source_id": "yonhap_industry",
            "source_role_class": "public_wire",
            "seed_type": "industry_disruption",
            "quality_flags": [],
            "recommended_action": "gather_more_evidence",
            "final_grade": "B",
            "scores": {"total_score": 66, "broadcast_potential_proxy": 4},
        },
    ]

    write_quality_report(report_path, candidates, candidates)

    report = report_path.read_text(encoding="utf-8")
    assert "### Source Role Distribution" in report
    assert "- research_note: 1" in report
    assert "- policy_release: 1" in report
    assert "### Source Role Balance" in report
    assert "### Source Role Cap Warnings" in report
    assert "BOK research-note candidates" in report
    assert "Policy Briefing seed/evidence candidates" in report
    assert "The Conversation academic explainers" in report
    assert "Yonhap economy/industry/international seeds" in report


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


def test_low_frequency_research_source_is_not_hold_daily_fetch(tmp_path) -> None:
    report_path = tmp_path / "quality.md"
    candidates = [
        {
            "candidate_id": f"bok_{index}",
            "title": f"BOK 이슈노트 {index}",
            "source": "한국은행",
            "source_freshness_policy": "low_frequency_research",
            "freshness_status": "recent",
            "quality_flags": [],
            "failure_modes": ["thin_evidence"],
            "recommended_action": "gather_more_evidence",
            "final_grade": "B",
            "scores": {"total_score": 20 - index, "broadcast_potential_proxy": 2},
        }
        for index in range(5)
    ]

    write_quality_report(report_path, candidates, [])

    report = report_path.read_text(encoding="utf-8")
    assert "| 한국은행 | review | low_frequency_research" in report
    assert "review_research_template_queue" in report


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


def test_top_candidates_excludes_policy_evidence_default_even_with_high_score() -> None:
    candidates = [
        {
            "candidate_id": "policy_date_only",
            "source": "정책브리핑",
            "seed_type": "policy_release_evidence",
            "final_grade": "B",
            "recommended_action": "gather_more_evidence",
            "quality_flags": [
                "policy_release_evidence_default",
                "policy_release_date_only_number",
            ],
            "scores": {"total_score": 90, "broadcast_potential_proxy": 5},
        },
        {
            "candidate_id": "yonhap_seed",
            "source": "연합뉴스 산업",
            "seed_type": "industry_disruption",
            "final_grade": "B",
            "recommended_action": "gather_more_evidence",
            "quality_flags": [],
            "why_interesting": "AI 산업정책의 구조 변화",
            "scores": {"total_score": 50, "broadcast_potential_proxy": 3},
        },
    ]

    assert [candidate["candidate_id"] for candidate in top_candidates(candidates)] == [
        "yonhap_seed"
    ]
