import json

from typer.testing import CliRunner

from luddite.agents.jibi.board_triage import (
    build_board_triage_payload,
    build_source_experiment_payload,
    source_experiment_app,
    triage_app,
    triage_board_row,
    write_board_triage_outputs,
    write_source_experiment_outputs,
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
    assert "reviewer_overlap_and_syuka_duplicate" in result["reasons"]


def test_adjacent_and_good_so_what_creates_conditional_update_angle() -> None:
    result = triage_board_row(_row(syuka="adjacent", so_what="strong"), {})

    assert result["triage_label"] == "conditional_update_angle"


def test_safe_new_angle_alone_does_not_promote() -> None:
    result = triage_board_row(_row(syuka="safe_new_angle", so_what="strong"), {})

    assert result["triage_label"] == "needs_more_sources"
    assert result["triage_label"] != "promote_candidate"


def test_promo_bulletin_and_weak_so_what_rejects() -> None:
    result = triage_board_row(
        _row(so_what="weak", seed_quality="conditional_seed"),
        _feedback("conditional_seed", ["promo_or_bulletin"]),
    )

    assert result["triage_label"] == "reject_or_downrank"


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
    assert payload["source_recommendations"]["The Guardian Business"] in {
        "keep_but_cap",
        "keep_candidate_source",
    }


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

    assert payload["source_recommendations"]["Nikkei Asia"] == "manual_only"
