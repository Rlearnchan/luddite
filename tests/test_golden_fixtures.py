import json
from collections import Counter

from jsonschema import Draft202012Validator

from luddite import paths
from luddite.eval.validate_golden import validate_golden


def _load_json(path):
    with path.open(encoding="utf-8") as source:
        return json.load(source)


def test_golden_anny_storyline_fixtures_validate() -> None:
    schema = _load_json(paths.SPECS_DIR / "anny_storyline_schema.json")
    validator = Draft202012Validator(schema)
    fixture_dir = paths.EVAL_DIR / "golden_cases" / "anny_storylines"
    fixture_paths = sorted(fixture_dir.glob("*.json"))

    assert fixture_paths
    for fixture_path in fixture_paths:
        payload = _load_json(fixture_path)
        validator.validate(payload)
        assert len(payload["sections"]) >= 3
        for section in payload["sections"]:
            assert section["slides"]
            for slide in section["slides"]:
                assert not set(slide["source_urls"]) & set(slide["image_urls"])
                assert "needs_fact_check" in slide
                assert "needs_source" in slide


def test_golden_deck_plan_fixtures_validate() -> None:
    schema = _load_json(paths.SPECS_DIR / "deck_schema.json")
    validator = Draft202012Validator(schema)
    fixture_dir = paths.EVAL_DIR / "golden_cases" / "deck_plans"
    fixture_paths = sorted(fixture_dir.glob("*.json"))

    assert fixture_paths
    for fixture_path in fixture_paths:
        payload = _load_json(fixture_path)
        validator.validate(payload)
        assert payload["slides"]
        assert [slide["slide_no"] for slide in payload["slides"]] == list(
            range(1, len(payload["slides"]) + 1)
        )


def test_validate_golden_harness_passes() -> None:
    assert validate_golden() == []


def test_jibi_seed_eval_cases_have_expected_mix() -> None:
    path = paths.EVAL_DIR / "golden_cases" / "jibi_seed_eval_cases.jsonl"
    records = [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    labels = Counter(record["expected_label"] for record in records)

    assert len(records) == 30
    assert labels["positive"] == 10
    assert labels["produced_but_rejected"] == 8
    assert labels["pending_or_unknown"] == 7
    assert labels["rejected_or_not_pursued"] == 5
    assert Counter(record["case_type"] for record in records)["risk_probe"] == 2
    for record in records:
        assert set(record) == {
            "title",
            "source_url",
            "sheet_label",
            "expected_label",
            "expected_action",
            "case_type",
            "reason",
            "expected_strengths",
            "expected_weaknesses",
            "expected_risk_flags",
        }
