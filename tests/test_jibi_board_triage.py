import json
from pathlib import Path

from typer.testing import CliRunner

from luddite.agents.jibi.board_triage import (
    build_board_triage_payload,
    build_source_experiment_payload,
    build_source_experiment_plan,
    source_experiment_app,
    source_runner_app,
    triage_app,
    triage_board_row,
    write_board_triage_outputs,
    write_source_experiment_outputs,
    write_source_experiment_plan_outputs,
)


def _row(
    *,
    title="후보",
    row_id="2026-05-25:story",
    source="연합뉴스",
    source_role="public_wire",
    so_what="conditional",
    seed_quality="conditional_seed",
    syuka="safe_new_angle",
    reasons=None,
):
    return {
        "ID": row_id,
        "review_item_id": row_id,
        "title": title,
        "source": source,
        "source_role_class": source_role,
        "seed_quality_classification": seed_quality,
        "seed_quality_reasons": reasons or [],
        "so_what": {"so_what_label": so_what},
        "syuka_similarity": {
            "recommendation": syuka,
            "top_match_title": "",
            "top_match_score": 0,
            "past_video_response_signal": syuka,
        },
    }


def _feedback(label, modifiers=None):
    return {
        "reviewers": {
            "리뷰-형찬": {
                "primary_inferred_label": label,
                "modifiers": modifiers or [],
            }
        }
    }


def _write_metadata(path, rows):
    path.write_text(
        json.dumps({"run_date": "2026-05-25", "rows": rows}, ensure_ascii=False),
        encoding="utf-8",
    )


def _write_feedback(path, rows):
    path.write_text(
        json.dumps({"run_date": "2026-05-25", "rows": rows}, ensure_ascii=False),
        encoding="utf-8",
    )


def test_duplicate_and_reviewer_overlap_creates_past_overlap_check() -> None:
    result = triage_board_row(
        _row(syuka="duplicate", so_what="strong"),
        _feedback("seed", ["past_topic_overlap"]),
    )

    assert result["triage_label"] == "past_overlap_check"
    assert result["triage_display_label"] == "check_past_overlap"
    assert result["triage_confidence"] == "high"
    assert result["next_action"] == "check_past_overlap"
    assert result["review_sample_size"] == 1
    assert result["reviewer_label_distribution"] == {"seed": 1}
    assert "reviewer_overlap_and_syuka_duplicate" in result["reasons"]


def test_adjacent_and_good_so_what_creates_conditional_update_angle() -> None:
    result = triage_board_row(_row(syuka="adjacent", so_what="strong"), {})

    assert result["triage_label"] == "conditional_update_angle"
    assert result["triage_confidence"] == "medium"
    assert result["next_action"] == "collect_sources"


def test_safe_new_angle_alone_does_not_promote() -> None:
    result = triage_board_row(_row(syuka="safe_new_angle", so_what="strong"), {})

    assert result["triage_label"] == "needs_more_sources"
    assert result["triage_label"] != "promote_candidate"


def test_promo_bulletin_and_weak_so_what_rejects() -> None:
    result = triage_board_row(
        _row(so_what="weak", seed_quality="conditional_seed"),
        _feedback("unlabeled", ["promo_or_bulletin"]),
    )

    assert result["triage_label"] == "reject_or_downrank"
    assert result["triage_display_label"] == "weak_or_downrank_candidate"


def test_promo_bulletin_with_positive_reviewer_signal_does_not_auto_reject() -> None:
    result = triage_board_row(
        _row(so_what="weak", seed_quality="conditional_seed"),
        _feedback("conditional_seed", ["promo_or_bulletin"]),
    )

    assert result["triage_label"] == "conditional_update_angle"
    assert result["triage_label"] != "reject_or_downrank"


def test_reviewer_disagreement_lowers_confidence() -> None:
    feedback = {
        "reviewers": {
            "리뷰-형찬": {"primary_inferred_label": "seed", "modifiers": []},
            "리뷰-성원": {"primary_inferred_label": "reject", "modifiers": []},
        }
    }

    result = triage_board_row(_row(so_what="strong"), feedback)

    assert result["triage_label"] == "reject_or_downrank"
    assert result["triage_confidence"] == "low"
    assert result["review_sample_size"] == 2
    assert result["reviewer_label_distribution"] == {"seed": 1, "reject": 1}


def test_prepaid_system_issue_becomes_conditional_update_angle() -> None:
    result = triage_board_row(
        _row(
            title="선불충전금 환불 규제 사각지대",
            so_what="conditional",
            seed_quality="conditional_seed",
        ),
        _feedback("unlabeled", ["system_issue"]),
    )

    assert result["triage_label"] == "conditional_update_angle"


def test_board_triage_outputs_report_and_json(tmp_path) -> None:
    metadata = tmp_path / "metadata.json"
    feedback = tmp_path / "feedback.json"
    _write_metadata(metadata, [_row(row_id="row1", syuka="adjacent", so_what="strong")])
    _write_feedback(
        feedback,
        [
            {
                "id": "row1",
                "title": "후보",
                "reviewers": {
                    "리뷰-형찬": {
                        "primary_inferred_label": "conditional_seed",
                        "modifiers": [],
                    }
                },
            }
        ],
    )

    md_path, json_path, payload = write_board_triage_outputs(
        run_date="2026-05-25",
        metadata_path=metadata,
        feedback_path=feedback,
        output_md=tmp_path / "triage.md",
        output_json=tmp_path / "triage.json",
    )

    assert md_path.exists()
    assert json_path.exists()
    assert payload["triage_label_counts"]["conditional_update_angle"] == 1
    assert payload["next_action_counts"]["collect_sources"] == 1
    assert payload["review_sample_size_total"] == 1
    assert "visible Google Sheet schema" in md_path.read_text(encoding="utf-8")


def test_source_experiment_report_compares_baseline_and_experiment(tmp_path) -> None:
    baseline = tmp_path / "baseline.json"
    experiment = tmp_path / "experiment.json"
    _write_metadata(baseline, [_row(source="한국은행", source_role="research_note")])
    _write_metadata(
        experiment,
        [
            _row(source="한국은행", source_role="research_note"),
            _row(source="The Guardian Business", source_role="section_news"),
            _row(source="The Guardian Technology", source_role="section_news"),
            _row(source="The Guardian Environment", source_role="section_news"),
        ],
    )

    md_path, json_path, payload = write_source_experiment_outputs(
        run_date="2026-05-25",
        baseline_metadata_path=baseline,
        experiment_metadata_path=experiment,
        output_md=tmp_path / "experiment.md",
        output_json=tmp_path / "experiment.json",
    )

    assert md_path.exists()
    assert json_path.exists()
    assert payload["delta"]["board_row_count"] == 3
    assert payload["source_recommendations"]["The Guardian Business"]["recommendation"] in {
        "keep_but_cap",
        "keep_candidate_source",
    }
    assert payload["source_recommendations"]["The Guardian Business"]["confidence"] == "low"


def test_source_experiment_cli_smoke(tmp_path) -> None:
    baseline = tmp_path / "baseline.json"
    experiment = tmp_path / "experiment.json"
    _write_metadata(baseline, [_row(source="한국은행", source_role="research_note")])
    _write_metadata(experiment, [_row(source="YouGov", source_role="manual")])
    runner = CliRunner()

    result = runner.invoke(
        source_experiment_app,
        [
            "--date",
            "2026-05-25",
            "--baseline-metadata",
            str(baseline),
            "--experiment-metadata",
            str(experiment),
            "--output-md",
            str(tmp_path / "out.md"),
            "--output-json",
            str(tmp_path / "out.json"),
        ],
    )

    assert result.exit_code == 0


def test_source_experiment_comparison_uses_triage_metadata(tmp_path) -> None:
    baseline = tmp_path / "baseline.json"
    experiment = tmp_path / "experiment.json"
    experiment_triage = tmp_path / "experiment_triage.json"
    _write_metadata(baseline, [_row(source="한국은행", source_role="research_note")])
    _write_metadata(
        experiment,
        [
            _row(source="The Guardian Business", source_role="section_news"),
            _row(source="The Guardian Business", source_role="section_news", syuka="duplicate"),
        ],
    )
    experiment_triage.write_text(
        json.dumps(
            {
                "rows": [
                    {
                        "source": "The Guardian Business",
                        "triage_label": "past_overlap_check",
                        "triage_display_label": "check_past_overlap",
                        "triage_confidence": "medium",
                        "next_action": "check_past_overlap",
                        "review_sample_size": 1,
                    }
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    payload = build_source_experiment_payload(
        run_date="2026-05-25",
        baseline_metadata_path=baseline,
        experiment_metadata_path=experiment,
        experiment_triage_path=experiment_triage,
    )

    assert payload["experiment"]["triage_label_distribution"] == {"past_overlap_check": 1}
    assert payload["experiment"]["reviewed_rows"] == 1
    recommendation = payload["source_recommendations"]["The Guardian Business"]
    assert "syuka_duplicate_heavy" in recommendation["reasons"]
    assert recommendation["confidence"] == "medium"


def test_board_triage_cli_smoke(tmp_path) -> None:
    metadata = tmp_path / "metadata.json"
    _write_metadata(metadata, [_row(row_id="row1")])
    runner = CliRunner()

    result = runner.invoke(
        triage_app,
        [
            "--date",
            "2026-05-25",
            "--metadata",
            str(metadata),
            "--output-md",
            str(tmp_path / "out.md"),
            "--output-json",
            str(tmp_path / "out.json"),
        ],
    )

    assert result.exit_code == 0


def test_build_board_triage_payload_handles_missing_feedback(tmp_path) -> None:
    metadata = tmp_path / "metadata.json"
    _write_metadata(metadata, [_row(row_id="row1")])

    payload = build_board_triage_payload(
        run_date="2026-05-25",
        metadata_path=metadata,
        feedback_path=tmp_path / "missing.json",
    )

    assert payload["row_count"] == 1


def test_source_experiment_plan_writes_temp_guardian_allowlist(tmp_path) -> None:
    config = tmp_path / "rss_guardian_sections.yaml"
    config.write_text(
        """
experiment_id: guardian_sections_v1
guardrails:
  no_default_allowlist_edit: true
temporary_allowlist_sources:
  - source_id: guardian_business
    collection_enabled: true
    fetch_limit: 40
    reason: controlled_business_section_mix_test
  - source_id: guardian_technology
    collection_enabled: true
    fetch_limit: 40
    reason: controlled_technology_section_mix_test
  - source_id: guardian_environment
    collection_enabled: true
    fetch_limit: 40
    reason: controlled_environment_section_mix_test
explicitly_excluded:
  - source_id: guardian_rss_candidate
    reason: broad_international_feed_hold
""",
        encoding="utf-8",
    )
    default_allowlist = Path("config/rss_collection_allowlist.yaml")
    default_allowlist_before = default_allowlist.read_text(encoding="utf-8")

    md_path, json_path, allowlist_path, payload = write_source_experiment_plan_outputs(
        run_date="2026-05-25",
        experiment="guardian_sections_v1",
        config_path=config,
        output_md=tmp_path / "plan.md",
        output_json=tmp_path / "plan.json",
        experiment_dir=tmp_path / "guardian_sections_v1",
    )

    allowlist = allowlist_path.read_text(encoding="utf-8")
    assert md_path.exists()
    assert json_path.exists()
    assert payload["notes"] == [
        "default_allowlist_unchanged",
        "no_google_sheet_write",
        "compare_experiment_board_to_baseline_before_source_default_changes",
    ]
    assert "guardian_business" in allowlist
    assert "guardian_technology" in allowlist
    assert "guardian_environment" in allowlist
    assert "guardian_rss_candidate" not in allowlist
    assert default_allowlist.read_text(encoding="utf-8") == default_allowlist_before


def test_source_experiment_plan_cli_smoke(tmp_path) -> None:
    config = tmp_path / "rss_guardian_sections.yaml"
    config.write_text(
        """
experiment_id: guardian_sections_v1
guardrails:
  no_default_allowlist_edit: true
temporary_allowlist_sources:
  - source_id: guardian_business
    collection_enabled: true
    fetch_limit: 40
    reason: controlled_business_section_mix_test
explicitly_excluded:
  - source_id: guardian_rss_candidate
    reason: broad_international_feed_hold
""",
        encoding="utf-8",
    )
    runner = CliRunner()

    result = runner.invoke(
        source_runner_app,
        [
            "--date",
            "2026-05-25",
            "--experiment",
            "guardian_sections_v1",
            "--config",
            str(config),
            "--experiment-dir",
            str(tmp_path / "guardian_sections_v1"),
            "--output-md",
            str(tmp_path / "plan.md"),
            "--output-json",
            str(tmp_path / "plan.json"),
        ],
    )

    assert result.exit_code == 0
    plan = build_source_experiment_plan(
        run_date="2026-05-25",
        experiment="guardian_sections_v1",
        config_path=config,
        experiment_dir=tmp_path / "guardian_sections_v1",
    )
    assert "--allowlist-path" in plan["commands"][0]


def test_build_source_experiment_payload_manual_source_recommendation(tmp_path) -> None:
    baseline = tmp_path / "baseline.json"
    experiment = tmp_path / "experiment.json"
    _write_metadata(baseline, [])
    _write_metadata(experiment, [_row(source="Nikkei Asia", source_role="manual")])

    payload = build_source_experiment_payload(
        run_date="2026-05-25",
        baseline_metadata_path=baseline,
        experiment_metadata_path=experiment,
    )

    assert payload["source_recommendations"]["Nikkei Asia"]["recommendation"] == "manual_only"
    assert payload["source_recommendations"]["Nikkei Asia"]["confidence"] == "low"
