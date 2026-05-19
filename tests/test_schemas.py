import json

from jsonschema import Draft202012Validator

from luddite import paths


def test_specs_are_valid_json_schemas() -> None:
    schema_names = [
        "jibi_candidate_schema.json",
        "evidence_cluster_schema.json",
        "anny_storyline_schema.json",
        "piti_slide_schema.json",
        "piti_slide_spec_schema.json",
        "deck_schema.json",
        "corpus_manifest_schema.json",
        "article_schema.json",
        "anny_run_input_schema.json",
        "anny_run_manifest_schema.json",
        "anny_failure_mode_schema.json",
    ]

    for schema_name in schema_names:
        schema_path = paths.SPECS_DIR / schema_name
        with schema_path.open(encoding="utf-8") as source:
            schema = json.load(source)
        Draft202012Validator.check_schema(schema)
