import json

from luddite.eval import anny_reconstruction_eval


def test_anny_reconstruction_eval_cases_load() -> None:
    cases = anny_reconstruction_eval.load_cases()

    assert {case["case_id"] for case in cases} == {"pawnshop_f88", "coca_cola_ambani"}
    assert all(case["key_beats"] for case in cases)
    assert all(case["critical_beats"] for case in cases)
    assert all(case["fixture_mode"] == "representative_reconstruction" for case in cases)


def test_key_beat_recall_calculation() -> None:
    storyline = {
        "title": "전당포 주식회사",
        "one_liner": "",
        "sections": [
            {
                "section_title": "F88 상장",
                "purpose": "",
                "slides": [
                    {
                        "headline": "오토바이 담보대출",
                        "body": ["추심 리스크"],
                    }
                ],
            }
        ],
    }
    beats = [
        {"label": "F88 상장", "aliases": ["F88", "상장"]},
        {"label": "오토바이 담보대출", "aliases": ["오토바이", "오담대"]},
        {"label": "창업자 일화", "aliases": ["창업자"]},
    ]

    recall, matched, missing = anny_reconstruction_eval.key_beat_recall(storyline, beats)

    assert recall == 2 / 3
    assert matched == ["F88 상장", "오토바이 담보대출"]
    assert missing == ["창업자 일화"]


def test_golden_pawnshop_case_evaluates() -> None:
    case = next(
        case for case in anny_reconstruction_eval.load_cases() if case["case_id"] == "pawnshop_f88"
    )
    storyline = anny_reconstruction_eval._load_json(
        anny_reconstruction_eval._repo_path(case["golden_storyline_path"])
    )

    result = anny_reconstruction_eval.evaluate_storyline(case, storyline)

    assert result["passed"]
    assert result["key_beat_recall"] >= 0.70
    assert result["critical_beat_recall"] >= 0.80
    assert result["source_image_overlap_count"] == 0


def test_golden_coca_cola_case_evaluates() -> None:
    case = next(
        case
        for case in anny_reconstruction_eval.load_cases()
        if case["case_id"] == "coca_cola_ambani"
    )
    storyline = anny_reconstruction_eval._load_json(
        anny_reconstruction_eval._repo_path(case["golden_storyline_path"])
    )

    result = anny_reconstruction_eval.evaluate_storyline(case, storyline)

    assert result["passed"]
    assert result["key_beat_recall"] >= 0.70
    assert result["critical_beat_recall"] >= 0.80
    assert result["source_image_overlap_count"] == 0


def test_source_image_overlap_detection() -> None:
    storyline = {
        "sections": [
            {
                "slides": [
                    {
                        "source_urls": ["https://example.com/a"],
                        "image_urls": ["https://example.com/a"],
                    }
                ]
            }
        ]
    }

    assert anny_reconstruction_eval._source_image_overlap_count(storyline) == 1


def test_anny_reconstruction_eval_writes_report(tmp_path) -> None:
    output_jsonl = tmp_path / "latest.jsonl"
    output_md = tmp_path / "latest.md"

    results = anny_reconstruction_eval.run_eval(
        output_jsonl=output_jsonl,
        output_md=output_md,
    )

    assert len(results) == 2
    assert all(result["passed"] for result in results)
    assert output_jsonl.exists()
    assert output_md.exists()
    assert "anny Reconstruction Eval Report" in output_md.read_text(encoding="utf-8")

    written = [
        json.loads(line)
        for line in output_jsonl.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert len(written) == 2
