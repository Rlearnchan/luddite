"""Fixture-based anny API experiment validation.

This module does not call an LLM API. It validates raw output fixtures as if
they came from a future API experiment, preserving the raw text and classifying
failure modes before any production agent exists.
"""

from __future__ import annotations

import json
import os
import shutil
import urllib.error
import urllib.request
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Any

import typer
from rich.console import Console

from luddite import paths
from luddite.eval.anny_dry_run_eval import (
    DO_NOT_CLAIM_PATTERNS,
    _source_image_overlap_count,
)
from luddite.eval.anny_reconstruction_eval import key_beat_recall
from luddite.utils.schemas import validate_with_schema
from luddite.utils.urls import canonicalize_url

app = typer.Typer(no_args_is_help=False)
run_app = typer.Typer(no_args_is_help=False)
console = Console()

DEFAULT_CASE_ID = "anny_api_experiment_ai_knowledge_institution_v1"
DEFAULT_INPUT_BUNDLE = (
    paths.ANNY_STORYLINE_DRY_RUN_DIR / "ai_knowledge_institution_input_bundle.json"
)
DEFAULT_EVIDENCE_PACK = paths.ANNY_EVIDENCE_PACK_AI_KNOWLEDGE_JSON
DEFAULT_OUTPUT_ROOT = paths.OUTPUTS_DIR / "eval" / "anny_api_experiment"
DEFAULT_EXPERIMENT_ROOT = paths.MODEL_DRY_RUNS_DIR / "anny_api_experiments"
DEFAULT_API_EXPERIMENT_RUN_ID = "anny_api_experiment_ai_knowledge_institution_v1"
DEFAULT_SECOND_API_EXPERIMENT_RUN_ID = "anny_api_experiment_ai_knowledge_institution_v2"
DEFAULT_API_COMPARISON_REPORT = (
    paths.REPORTS_DIR / "anny_api_experiment_ai_knowledge_institution_comparison.md"
)
DEFAULT_API_V1_V2_COMPARISON_REPORT = (
    paths.REPORTS_DIR / "anny_api_experiment_ai_knowledge_institution_v1_v2_comparison.md"
)
DEFAULT_MANUAL_ENRICHED_STORYLINE = (
    paths.ANNY_STORYLINE_DRY_RUN_DIR
    / "ai_knowledge_institution_gpt_pro_storyline_enriched.json"
)
DEFAULT_PROMPT_FILE = paths.PROMPTS_DIR / "anny" / "storyline_writer.md"
OPENAI_RESPONSES_URL = "https://api.openai.com/v1/responses"
ENV_FILES = [paths.REPO_ROOT / ".env", paths.REPO_ROOT / ".env.local"]
RHETORICAL_SLIDE_TYPES = {
    "title",
    "section_title",
    "rhetorical",
    "bridge",
    "closing_question",
    "production_checklist",
}
RHETORICAL_FACT_CHECK_KINDS = {
    "rhetorical_caution",
    "production_checklist",
}
FACTUAL_CLAIM_MARKERS = [
    "%",
    "원",
    "명",
    "년",
    "월",
    "입증",
    "연구",
    "조사",
    "보고서",
    "OECD",
    "UNESCO",
    "BBC",
    "Microsoft",
    "Royal Observatory",
    "교육 효과",
    "인지",
    "정책 효과",
    "공식",
    "발언",
    "도입",
    "확인",
]


@dataclass(frozen=True)
class ApiExperimentResult:
    fixture_name: str
    parse_status: str
    schema_valid: bool
    hygiene_passed: bool
    failure_modes: list[str]
    allowed_url_count: int
    used_url_count: int
    hallucinated_urls: list[str]
    repair_attempted: bool
    ready_for_api_experiment: bool
    report_path: Path
    manifest_path: Path
    experiment_dir: Path


def _load_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as source:
        return json.load(source)


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _extract_response_text(response_payload: dict[str, Any]) -> str:
    output_text = response_payload.get("output_text")
    if isinstance(output_text, str) and output_text.strip():
        return output_text
    parts: list[str] = []
    for item in response_payload.get("output", []):
        if item.get("type") != "message":
            continue
        for content in item.get("content", []):
            if content.get("type") == "output_text" and isinstance(content.get("text"), str):
                parts.append(content["text"])
    if parts:
        return "\n".join(parts)
    return json.dumps(response_payload, ensure_ascii=False)


def _walk_values(value: Any) -> Iterable[Any]:
    if isinstance(value, dict):
        for item in value.values():
            yield from _walk_values(item)
    elif isinstance(value, list):
        for item in value:
            yield from _walk_values(item)
    else:
        yield value


def _collect_allowed_urls(*payloads: dict[str, Any]) -> set[str]:
    urls: set[str] = set()
    for payload in payloads:
        for value in _walk_values(payload):
            if isinstance(value, str) and value.startswith(("http://", "https://")):
                urls.add(canonicalize_url(value))
    return urls


def _allowed_url_markdown(allowed_urls: set[str]) -> str:
    return "\n".join(f"- {url}" for url in sorted(allowed_urls))


def build_api_experiment_prompt(
    *,
    input_bundle: dict[str, Any],
    evidence_pack: dict[str, Any],
    prompt_text: str,
    schema: dict[str, Any],
    allowed_urls: set[str],
) -> str:
    return "\n\n".join(
        [
            prompt_text,
            "## Controlled API Experiment Instructions",
            "This is a single non-production API experiment. Return JSON only.",
            "Do not call tools. Do not browse. Do not invent sources.",
            "Use only the input bundle, evidence pack, and allowed URL list.",
            "Keep needs_fact_check / needs_source when evidence is thin.",
            "Include a counterpoint slide.",
            "Target 20-30 representative slides across 3-4 sections.",
            "The output must satisfy the anny storyline JSON schema.",
            "## Allowed Source URLs",
            _allowed_url_markdown(allowed_urls),
            "## Input Bundle JSON",
            json.dumps(input_bundle, ensure_ascii=False, indent=2),
            "## Evidence Pack JSON",
            json.dumps(evidence_pack, ensure_ascii=False, indent=2),
            "## Output Schema JSON",
            json.dumps(schema, ensure_ascii=False, indent=2),
        ]
    )


def _all_slides(storyline: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        slide
        for section in storyline.get("sections", [])
        for slide in section.get("slides", [])
    ]


def _section_count(storyline: dict[str, Any]) -> int:
    return len(storyline.get("sections", []))


def _slide_count(storyline: dict[str, Any]) -> int:
    return len(_all_slides(storyline))


def _source_url_count(storyline: dict[str, Any]) -> int:
    return sum(len(slide.get("source_urls", [])) for slide in _all_slides(storyline))


def _needs_source_count(storyline: dict[str, Any]) -> int:
    return sum(1 for slide in _all_slides(storyline) if slide.get("needs_source"))


def _needs_fact_check_count(storyline: dict[str, Any]) -> int:
    return sum(1 for slide in _all_slides(storyline) if slide.get("needs_fact_check"))


def _used_source_urls(storyline: dict[str, Any]) -> set[str]:
    urls: set[str] = set()
    for slide in _all_slides(storyline):
        for url in slide.get("source_urls", []):
            if url:
                urls.add(canonicalize_url(url))
        for source_ref in slide.get("source_refs", []):
            url = source_ref.get("url")
            if url:
                urls.add(canonicalize_url(url))
    return urls


def _empty_source_errors(storyline: dict[str, Any]) -> list[str]:
    errors = []
    for index, slide in enumerate(_all_slides(storyline), start=1):
        if (
            not slide.get("source_urls")
            and not slide.get("needs_source")
            and not _source_optional_without_claim(slide)
        ):
            errors.append(f"slide {index} has empty source_urls without needs_source=true")
    return errors


def _source_optional_without_claim(slide: dict[str, Any]) -> bool:
    if slide.get("slide_type") == "production_checklist":
        return True
    if slide.get("slide_type") not in RHETORICAL_SLIDE_TYPES:
        return False
    if _fact_check_kind(slide) in RHETORICAL_FACT_CHECK_KINDS:
        return True
    return not _has_factual_claim_marker(slide)


def _fact_check_kind(slide: dict[str, Any]) -> str | None:
    kind = slide.get("fact_check_kind")
    if isinstance(kind, str):
        return kind
    notes = str(slide.get("notes") or "")
    marker = "fact_check_kind:"
    if marker not in notes:
        return None
    after = notes.split(marker, 1)[1].strip()
    return after.split("|", 1)[0].strip() or None


def _has_factual_claim_marker(slide: dict[str, Any]) -> bool:
    text = "\n".join(
        [
            str(slide.get("headline") or ""),
            *[str(item) for item in slide.get("body", [])],
        ]
    )
    return any(marker in text for marker in FACTUAL_CLAIM_MARKERS)


def _education_ai_fact_check_errors(storyline: dict[str, Any]) -> list[str]:
    errors = []
    markers = ["교육 효과", "인지", "지능", "학습 습관", "기관 역할", "사고훈련"]
    for index, slide in enumerate(_all_slides(storyline), start=1):
        if _source_optional_without_claim(slide):
            continue
        text = "\n".join(
            [
                str(slide.get("headline") or ""),
                *[str(item) for item in slide.get("body", [])],
            ]
        )
        if any(marker in text for marker in markers) and not slide.get("needs_fact_check"):
            errors.append(f"slide {index} education/AI effect claim missing needs_fact_check")
    return errors


def _text_blob(storyline: dict[str, Any]) -> str:
    parts = [storyline.get("title", ""), storyline.get("one_liner", "")]
    for section in storyline.get("sections", []):
        parts.append(section.get("section_title", ""))
        for slide in section.get("slides", []):
            parts.append(slide.get("slide_type", ""))
            parts.append(slide.get("headline", ""))
            parts.extend(slide.get("body", []))
            parts.append(slide.get("notes", ""))
    return "\n".join(str(part) for part in parts if part)


def _counterpoint_included(storyline: dict[str, Any]) -> bool:
    text = _text_blob(storyline)
    return any(
        marker in text
        for marker in ["counterpoint", "반대 관점", "반론", "리스크", "접근성", "맞춤형"]
    )


def _do_not_claim_violations(storyline: dict[str, Any], input_bundle: dict[str, Any]) -> list[str]:
    text = _text_blob(storyline)
    patterns = list(DO_NOT_CLAIM_PATTERNS)
    patterns.extend(str(item) for item in input_bundle.get("do_not_claim", []))
    return [pattern for pattern in patterns if pattern and pattern in text]


def validate_api_experiment_raw_output(
    *,
    raw_output_path: Path,
    input_bundle_path: Path = DEFAULT_INPUT_BUNDLE,
    evidence_pack_path: Path = DEFAULT_EVIDENCE_PACK,
    experiment_dir: Path,
    report_path: Path,
    case_id: str = DEFAULT_CASE_ID,
    display_name: str | None = None,
    model_source: str = "fixture",
    llm_api_called: bool = False,
) -> ApiExperimentResult:
    fixture_name = display_name or raw_output_path.stem
    experiment_dir.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    raw_copy_path = experiment_dir / "raw_model_output.txt"
    parsed_path = experiment_dir / "parsed_storyline.json"
    manifest_path = experiment_dir / "manifest.json"
    if raw_output_path.resolve() != raw_copy_path.resolve():
        shutil.copyfile(raw_output_path, raw_copy_path)

    input_bundle = _load_json(input_bundle_path)
    evidence_pack = _load_json(evidence_pack_path)
    allowed_urls = _collect_allowed_urls(input_bundle, evidence_pack)
    raw_text = raw_copy_path.read_text(encoding="utf-8")

    parse_status = "parsed"
    schema_valid = False
    hygiene_passed = False
    failure_modes: list[str] = []
    used_urls: set[str] = set()
    hallucinated_urls: list[str] = []
    schema_errors: list[str] = []
    empty_source_errors: list[str] = []
    fact_check_errors: list[str] = []
    key_beat_coverage_errors: list[str] = []
    do_not_claim_violations: list[str] = []
    source_image_overlap_count = 0
    counterpoint_included = False
    key_beat_recall_value: float | None = None

    try:
        storyline = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        storyline = None
        parse_status = f"invalid_json:{exc.msg}"
        failure_modes.append("invalid_json")

    if isinstance(storyline, dict):
        _write_json(parsed_path, storyline)
        schema_errors = validate_with_schema(storyline, "anny_storyline_schema.json")
        schema_valid = not schema_errors
        if schema_errors:
            failure_modes.append("schema_error")
        used_urls = _used_source_urls(storyline)
        hallucinated_urls = sorted(used_urls - allowed_urls)
        if hallucinated_urls:
            failure_modes.append("source_hallucination")
        source_image_overlap_count = _source_image_overlap_count(storyline)
        if source_image_overlap_count:
            failure_modes.append("source_image_overlap")
        empty_source_errors = _empty_source_errors(storyline)
        if empty_source_errors:
            failure_modes.append("unsupported_claim")
        fact_check_errors = _education_ai_fact_check_errors(storyline)
        if fact_check_errors:
            failure_modes.append("needs_fact_check_removed_too_aggressively")
        counterpoint_included = _counterpoint_included(storyline)
        if not counterpoint_included:
            failure_modes.append("counterpoint_missing")
        do_not_claim_violations = _do_not_claim_violations(storyline, input_bundle)
        if do_not_claim_violations:
            failure_modes.append("do_not_claim_violation")
        key_beat_recall_value = _api_key_beat_recall(storyline, case_id)
        if key_beat_recall_value is not None and key_beat_recall_value < 0.85:
            failure_modes.append("key_beat_drift")
        key_beat_coverage_errors = _key_beat_coverage_errors(storyline, case_id)
        if key_beat_coverage_errors:
            failure_modes.append("key_beat_drift")

    failure_modes = list(dict.fromkeys(failure_modes))
    hygiene_passed = not failure_modes
    ready_for_api_experiment = hygiene_passed and schema_valid
    manifest = {
        "run_id": fixture_name,
        "case_id": case_id,
        "status": "passed" if ready_for_api_experiment else "failed",
        "input_bundle_path": str(input_bundle_path),
        "evidence_pack_path": str(evidence_pack_path),
        "raw_model_output_path": str(raw_copy_path),
        "parsed_storyline_path": str(parsed_path) if parsed_path.exists() else None,
        "api_experiment_dir": str(experiment_dir),
        "validation_report_path": str(report_path),
        "model_source": model_source,
        "parse_status": parse_status,
        "schema_valid": schema_valid,
        "hygiene_passed": hygiene_passed,
        "failure_modes": failure_modes,
        "allowed_url_count": len(allowed_urls),
        "used_url_count": len(used_urls),
        "hallucinated_urls": hallucinated_urls,
        "do_not_claim_violations": do_not_claim_violations,
        "repair_attempted": False,
        "key_beat_recall": key_beat_recall_value,
        "key_beat_coverage_errors": key_beat_coverage_errors,
        "ready_for_api_experiment_prep": True,
        "ready_for_api_experiment": ready_for_api_experiment,
        "ready_for_production_agent": False,
        "ready_for_broadcast": False,
        "created_at": datetime.now(UTC).isoformat(),
    }
    _write_json(manifest_path, manifest)
    report_path.write_text(
        _report_markdown(
            fixture_name=fixture_name,
            manifest=manifest,
            schema_errors=schema_errors,
            empty_source_errors=empty_source_errors,
            fact_check_errors=fact_check_errors,
            do_not_claim_violations=do_not_claim_violations,
            key_beat_coverage_errors=key_beat_coverage_errors,
            counterpoint_included=counterpoint_included,
            key_beat_recall_value=key_beat_recall_value,
            llm_api_called=llm_api_called,
        ),
        encoding="utf-8",
    )
    return ApiExperimentResult(
        fixture_name=fixture_name,
        parse_status=parse_status,
        schema_valid=schema_valid,
        hygiene_passed=hygiene_passed,
        failure_modes=failure_modes,
        allowed_url_count=len(allowed_urls),
        used_url_count=len(used_urls),
        hallucinated_urls=hallucinated_urls,
        repair_attempted=False,
        ready_for_api_experiment=ready_for_api_experiment,
        report_path=report_path,
        manifest_path=manifest_path,
        experiment_dir=experiment_dir,
    )


def _api_key_beat_recall(storyline: dict[str, Any], case_id: str) -> float | None:
    case = _api_case(case_id)
    if not case:
        return None
    recall, _, _ = key_beat_recall(storyline, case.get("expected_key_beats", []))
    return recall


def _api_case(case_id: str) -> dict[str, Any] | None:
    cases_payload = _load_json(paths.EVAL_DIR / "golden_cases" / "anny_dry_run_cases.json")
    case = next((item for item in cases_payload["cases"] if item["case_id"] == case_id), None)
    if not case and case_id.endswith("_v2"):
        case = next(
            (
                item
                for item in cases_payload["cases"]
                if item["case_id"] == DEFAULT_API_EXPERIMENT_RUN_ID
            ),
            None,
        )
    return case


def _key_beat_coverage_errors(storyline: dict[str, Any], case_id: str) -> list[str]:
    case = _api_case(case_id)
    if not case:
        return []
    expected_beats = case.get("expected_key_beats", [])
    if not expected_beats:
        return []

    coverage = storyline.get("key_beat_coverage")
    if not isinstance(coverage, list):
        return [
            f"missing_key_beat:{_beat_label(beat)}:key_beat_coverage_absent"
            for beat in expected_beats
        ]

    slide_map = _slide_ref_map(storyline)
    records = {
        str(item.get("key_beat", "")).strip(): item
        for item in coverage
        if isinstance(item, dict)
    }
    errors: list[str] = []
    for beat in expected_beats:
        label = _beat_label(beat)
        record = records.get(label)
        if not record:
            errors.append(f"missing_key_beat:{label}")
            continue
        if record.get("covered") is not True:
            errors.append(f"missing_key_beat:{label}:covered_false")
            continue
        slide_refs = record.get("slide_refs")
        if not isinstance(slide_refs, list) or not slide_refs:
            errors.append(f"weak_key_beat_mapping:{label}:empty_slide_refs")
            continue
        aliases = _beat_aliases(beat)
        matched = False
        for ref in slide_refs:
            try:
                slide_ref = int(ref)
            except (TypeError, ValueError):
                errors.append(f"invalid_key_beat_slide_ref:{label}:{ref}")
                continue
            slide = slide_map.get(slide_ref)
            if not slide:
                errors.append(f"invalid_key_beat_slide_ref:{label}:{ref}")
                continue
            if _slide_matches_beat(slide, aliases):
                matched = True
        if not matched:
            errors.append(f"key_beat_covered_but_not_in_slide_text:{label}")
    return errors


def _beat_label(beat: dict[str, Any] | str) -> str:
    if isinstance(beat, dict):
        return str(beat.get("label", "")).strip()
    return str(beat).strip()


def _beat_aliases(beat: dict[str, Any] | str) -> list[str]:
    label = _beat_label(beat)
    aliases = [label]
    if isinstance(beat, dict):
        aliases.extend(str(alias) for alias in beat.get("aliases", []))
    return [alias.strip() for alias in aliases if alias and alias.strip()]


def _slide_ref_map(storyline: dict[str, Any]) -> dict[int, dict[str, Any]]:
    refs: dict[int, dict[str, Any]] = {}
    order = 0
    for section in storyline.get("sections", []):
        for slide in section.get("slides", []):
            if not isinstance(slide, dict):
                continue
            order += 1
            refs.setdefault(order, slide)
            slide_no = slide.get("slide_no")
            if isinstance(slide_no, int):
                refs[slide_no] = slide
    return refs


def _slide_matches_beat(slide: dict[str, Any], aliases: list[str]) -> bool:
    body = slide.get("body", [])
    body_text = " ".join(str(item) for item in body) if isinstance(body, list) else str(body)
    text = " ".join(
        [
            str(slide.get("headline", "")),
            body_text,
        ]
    ).lower()
    return any(alias.lower() in text for alias in aliases)


def _run_openai_responses_api(
    *,
    api_key: str,
    model: str,
    prompt: str,
    temperature: float,
    timeout_seconds: int,
    url: str = OPENAI_RESPONSES_URL,
) -> tuple[str, dict[str, Any]]:
    payload = {
        "model": model,
        "input": prompt,
        "text": {"format": {"type": "json_object"}},
    }
    if not model.startswith("gpt-5"):
        payload["temperature"] = temperature
    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=data,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            response_payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        error_body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"OpenAI API HTTP {exc.code}: {error_body}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"OpenAI API request failed: {exc.reason}") from exc
    return _extract_response_text(response_payload), response_payload


def _env_model() -> str:
    _load_env_files()
    model = os.environ.get("LUDDITE_ANNY_API_MODEL")
    if not model:
        raise RuntimeError("Missing required env var: LUDDITE_ANNY_API_MODEL")
    return model


def _env_api_key() -> str:
    _load_env_files()
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("Missing required env var: OPENAI_API_KEY")
    return api_key


def _env_temperature() -> float:
    _load_env_files()
    raw = os.environ.get("LUDDITE_ANNY_API_TEMPERATURE", "0.2")
    try:
        temperature = float(raw)
    except ValueError as exc:
        raise RuntimeError(f"Invalid LUDDITE_ANNY_API_TEMPERATURE: {raw}") from exc
    if not 0 <= temperature <= 0.2:
        raise RuntimeError("LUDDITE_ANNY_API_TEMPERATURE must be between 0 and 0.2")
    return temperature


def _load_env_files() -> None:
    for env_path in ENV_FILES:
        if not env_path.exists():
            continue
        for line in env_path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or "=" not in stripped:
                continue
            key, value = stripped.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = value


def run_api_experiment(
    *,
    run_id: str = DEFAULT_API_EXPERIMENT_RUN_ID,
    input_bundle_path: Path = DEFAULT_INPUT_BUNDLE,
    evidence_pack_path: Path = DEFAULT_EVIDENCE_PACK,
    prompt_file_path: Path = DEFAULT_PROMPT_FILE,
    manual_storyline_path: Path = DEFAULT_MANUAL_ENRICHED_STORYLINE,
    comparison_report_path: Path = DEFAULT_API_COMPARISON_REPORT,
    experiment_root: Path = DEFAULT_EXPERIMENT_ROOT,
    model: str | None = None,
    temperature: float | None = None,
    timeout_seconds: int = 120,
    api_caller: Any | None = None,
) -> dict[str, Any]:
    api_key = _env_api_key()
    model = model or _env_model()
    temperature = _env_temperature() if temperature is None else temperature
    experiment_dir = experiment_root / run_id
    experiment_dir.mkdir(parents=True, exist_ok=True)

    input_bundle = _load_json(input_bundle_path)
    evidence_pack = _load_json(evidence_pack_path)
    schema = _load_json(paths.SPECS_DIR / "anny_storyline_schema.json")
    prompt_text = prompt_file_path.read_text(encoding="utf-8")
    allowed_urls = _collect_allowed_urls(input_bundle, evidence_pack)
    prompt = build_api_experiment_prompt(
        input_bundle=input_bundle,
        evidence_pack=evidence_pack,
        prompt_text=prompt_text,
        schema=schema,
        allowed_urls=allowed_urls,
    )

    shutil.copyfile(input_bundle_path, experiment_dir / "input_bundle.json")
    shutil.copyfile(evidence_pack_path, experiment_dir / "evidence_pack.json")
    (experiment_dir / "prompt.md").write_text(prompt, encoding="utf-8")

    caller = api_caller or _run_openai_responses_api
    try:
        raw_text, response_payload = caller(
            api_key=api_key,
            model=model,
            prompt=prompt,
            temperature=temperature,
            timeout_seconds=timeout_seconds,
        )
    except Exception as exc:
        raw_path = experiment_dir / "raw_model_output.txt"
        raw_path.write_text("", encoding="utf-8")
        manifest = _api_request_failure_manifest(
            run_id=run_id,
            model=model,
            temperature=temperature,
            input_bundle_path=experiment_dir / "input_bundle.json",
            evidence_pack_path=experiment_dir / "evidence_pack.json",
            experiment_dir=experiment_dir,
            error=str(exc),
        )
        _write_json(experiment_dir / "manifest.json", manifest)
        (experiment_dir / "validation_report.md").write_text(
            _api_request_failure_report(manifest),
            encoding="utf-8",
        )
        comparison = write_api_manual_comparison_report(
            api_storyline_path=experiment_dir / "parsed_storyline.json",
            manual_storyline_path=manual_storyline_path,
            comparison_report_path=comparison_report_path,
            api_validation_manifest=manifest,
            case_id=run_id,
        )
        return {
            "run_id": run_id,
            "model": model,
            "experiment_dir": str(experiment_dir),
            "manifest_path": str(experiment_dir / "manifest.json"),
            "validation_report_path": str(experiment_dir / "validation_report.md"),
            "comparison_report_path": str(comparison_report_path),
            "failure_modes": manifest["failure_modes"],
            "schema_valid": manifest["schema_valid"],
            "hygiene_passed": manifest["hygiene_passed"],
            "comparison": comparison,
        }
    (experiment_dir / "raw_model_output.txt").write_text(raw_text, encoding="utf-8")
    _write_json(experiment_dir / "response_metadata.json", response_payload)

    validation = validate_api_experiment_raw_output(
        raw_output_path=experiment_dir / "raw_model_output.txt",
        input_bundle_path=experiment_dir / "input_bundle.json",
        evidence_pack_path=experiment_dir / "evidence_pack.json",
        experiment_dir=experiment_dir,
        report_path=experiment_dir / "validation_report.md",
        case_id=run_id,
        display_name=run_id,
        model_source="openai_api",
        llm_api_called=True,
    )
    manifest = _load_json(validation.manifest_path)
    manifest["run_id"] = run_id
    manifest["model_source"] = "openai_api"
    manifest["model"] = model
    manifest["temperature"] = temperature
    manifest["ready_for_production_agent"] = False
    manifest["ready_for_broadcast"] = False
    _write_json(validation.manifest_path, manifest)

    comparison = write_api_manual_comparison_report(
        api_storyline_path=experiment_dir / "parsed_storyline.json",
        manual_storyline_path=manual_storyline_path,
        comparison_report_path=comparison_report_path,
        api_validation_manifest=manifest,
        case_id=run_id,
    )
    return {
        "run_id": run_id,
        "model": model,
        "experiment_dir": str(experiment_dir),
        "manifest_path": str(validation.manifest_path),
        "validation_report_path": str(experiment_dir / "validation_report.md"),
        "comparison_report_path": str(comparison_report_path),
        "failure_modes": manifest["failure_modes"],
        "schema_valid": manifest["schema_valid"],
        "hygiene_passed": manifest["hygiene_passed"],
        "comparison": comparison,
    }


def _api_request_failure_manifest(
    *,
    run_id: str,
    model: str,
    temperature: float,
    input_bundle_path: Path,
    evidence_pack_path: Path,
    experiment_dir: Path,
    error: str,
) -> dict[str, Any]:
    return {
        "run_id": run_id,
        "case_id": run_id,
        "status": "failed",
        "input_bundle_path": str(input_bundle_path),
        "evidence_pack_path": str(evidence_pack_path),
        "raw_model_output_path": str(experiment_dir / "raw_model_output.txt"),
        "parsed_storyline_path": None,
        "api_experiment_dir": str(experiment_dir),
        "validation_report_path": str(experiment_dir / "validation_report.md"),
        "model_source": "openai_api",
        "model": model,
        "temperature": temperature,
        "parse_status": "no_model_output",
        "schema_valid": False,
        "hygiene_passed": False,
        "failure_modes": ["api_request_failed"],
        "allowed_url_count": None,
        "used_url_count": 0,
        "hallucinated_urls": [],
        "do_not_claim_violations": [],
        "api_error": error,
        "repair_attempted": False,
        "ready_for_api_experiment_prep": True,
        "ready_for_api_experiment": False,
        "ready_for_production_agent": False,
        "ready_for_broadcast": False,
        "created_at": datetime.now(UTC).isoformat(),
    }


def _api_request_failure_report(manifest: dict[str, Any]) -> str:
    lines = [
        "# Anny API Experiment Validation Report",
        "",
        f"- run_id: {manifest['run_id']}",
        f"- model: {manifest['model']}",
        "- status: failed",
        "- parse_status: no_model_output",
        "- schema_valid: false",
        "- hygiene_passed: false",
        "- failure_modes: ['api_request_failed']",
        f"- api_error: {manifest['api_error']}",
        "- repair_attempted: false",
        "- raw_model_output_retained: true",
        "- ready_for_production_agent: false",
        "- ready_for_broadcast: false",
    ]
    return "\n".join(lines) + "\n"


def _storyline_metrics(
    storyline_path: Path,
    *,
    case_id: str | None = None,
) -> dict[str, Any]:
    if not storyline_path.exists():
        return {
            "exists": False,
            "section_count": None,
            "slide_count": None,
            "source_url_count": None,
            "needs_source_count": None,
            "needs_fact_check_count": None,
            "counterpoint_included": False,
            "source_image_overlap_count": None,
            "key_beat_recall": None,
        }
    storyline = _load_json(storyline_path)
    recall = None
    if case_id:
        cases_payload = _load_json(paths.EVAL_DIR / "golden_cases" / "anny_dry_run_cases.json")
        case = next(
            (item for item in cases_payload["cases"] if item["case_id"] == case_id),
            None,
        )
        if case:
            recall, _, _ = key_beat_recall(storyline, case.get("expected_key_beats", []))
    return {
        "exists": True,
        "section_count": _section_count(storyline),
        "slide_count": _slide_count(storyline),
        "source_url_count": _source_url_count(storyline),
        "needs_source_count": _needs_source_count(storyline),
        "needs_fact_check_count": _needs_fact_check_count(storyline),
        "counterpoint_included": _counterpoint_included(storyline),
        "source_image_overlap_count": _source_image_overlap_count(storyline),
        "key_beat_recall": recall,
    }


def _manifest_metrics(manifest_path: Path) -> dict[str, Any]:
    if not manifest_path.exists():
        return {
            "model": None,
            "failure_modes": ["missing_manifest"],
            "schema_valid": False,
            "hygiene_passed": False,
            "source_hallucination_count": None,
            "do_not_claim_violations": [],
        }
    manifest = _load_json(manifest_path)
    return {
        "model": manifest.get("model"),
        "failure_modes": manifest.get("failure_modes", []),
        "schema_valid": manifest.get("schema_valid"),
        "hygiene_passed": manifest.get("hygiene_passed"),
        "source_hallucination_count": len(manifest.get("hallucinated_urls", [])),
        "do_not_claim_violations": manifest.get("do_not_claim_violations", []),
    }


def write_api_manual_comparison_report(
    *,
    api_storyline_path: Path,
    manual_storyline_path: Path,
    comparison_report_path: Path,
    api_validation_manifest: dict[str, Any],
    case_id: str,
) -> dict[str, Any]:
    api_metrics = _storyline_metrics(api_storyline_path, case_id=case_id)
    manual_metrics = _storyline_metrics(
        manual_storyline_path,
        case_id="anny_dry_run_ai_knowledge_institution_v1",
    )
    comparison_report_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Anny API Experiment Comparison — AI Knowledge Institution",
        "",
        f"- generated_at: {datetime.now(UTC).isoformat()}",
        f"- case_id: {case_id}",
        f"- api_storyline_path: {api_storyline_path}",
        f"- manual_storyline_path: {manual_storyline_path}",
        f"- model: {api_validation_manifest.get('model')}",
        f"- failure_modes: {api_validation_manifest.get('failure_modes', [])}",
        f"- schema_valid: {api_validation_manifest.get('schema_valid')}",
        f"- hygiene_passed: {api_validation_manifest.get('hygiene_passed')}",
        (
            "- source_hallucination_count: "
            f"{len(api_validation_manifest.get('hallucinated_urls', []))}"
        ),
        f"- do_not_claim_violations: {api_validation_manifest.get('do_not_claim_violations', [])}",
        "",
        "## Metrics",
        "",
        (
            "| Output | Sections | Slides | Source URLs | Needs Source | Needs Fact Check | "
            "Counterpoint | Source/Image Overlap | Key Beat Recall |"
        ),
        "|---|---:|---:|---:|---:|---:|---|---:|---:|",
        _metrics_row("Manual enriched", manual_metrics),
        _metrics_row("API experiment", api_metrics),
        "",
        "## Qualitative Notes",
        "",
        "- This is a controlled API experiment, not a production anny agent.",
        "- Failure is acceptable if failure modes are recorded and raw output is retained.",
        "- API output must remain evidence-bound to the input bundle/evidence pack.",
        "- ready_for_production_agent: false",
    ]
    comparison_report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"api": api_metrics, "manual": manual_metrics}


def write_api_v1_v2_comparison_report(
    *,
    v1_dir: Path,
    v2_dir: Path,
    comparison_report_path: Path = DEFAULT_API_V1_V2_COMPARISON_REPORT,
) -> dict[str, Any]:
    v1_manifest = _manifest_metrics(v1_dir / "manifest.json")
    v2_manifest = _manifest_metrics(v2_dir / "manifest.json")
    v1_metrics = _storyline_metrics(
        v1_dir / "parsed_storyline.json",
        case_id=DEFAULT_API_EXPERIMENT_RUN_ID,
    )
    v2_metrics = _storyline_metrics(
        v2_dir / "parsed_storyline.json",
        case_id=DEFAULT_API_EXPERIMENT_RUN_ID,
    )
    comparison_report_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Anny API Experiment v1/v2 Comparison — AI Knowledge Institution",
        "",
        f"- generated_at: {datetime.now(UTC).isoformat()}",
        f"- v1_dir: {v1_dir}",
        f"- v2_dir: {v2_dir}",
        "",
        "## Summary Table",
        "",
        (
            "| Run | Model | Schema | Hygiene | Sections | Slides | Source URLs | "
            "Needs Source | Needs Fact Check | Key Beat Recall | Failure Modes | "
            "Source Hallucinations | Do-not-claim Violations | Counterpoint |"
        ),
        "|---|---|---|---|---:|---:|---:|---:|---:|---:|---|---:|---:|---|",
        _api_version_row("v1", v1_manifest, v1_metrics),
        _api_version_row("v2", v2_manifest, v2_metrics),
        "",
        "## Qualitative Notes",
        "",
        "- v2 is a second controlled API experiment, not a production anny agent.",
        "- The main observation is whether needs_fact_check conservatism improves.",
        "- `unsupported_claim` should not recur after the 1.9.1 validator patch.",
        "- `ready_for_production_agent=false` remains in force.",
    ]
    comparison_report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {
        "v1": {"manifest": v1_manifest, "metrics": v1_metrics},
        "v2": {"manifest": v2_manifest, "metrics": v2_metrics},
    }


def _api_version_row(
    label: str,
    manifest: dict[str, Any],
    metrics: dict[str, Any],
) -> str:
    recall = metrics["key_beat_recall"]
    recall_text = "n/a" if recall is None else f"{recall:.2f}"
    return (
        f"| {label} | {manifest['model']} | {manifest['schema_valid']} | "
        f"{manifest['hygiene_passed']} | {metrics['section_count']} | "
        f"{metrics['slide_count']} | {metrics['source_url_count']} | "
        f"{metrics['needs_source_count']} | {metrics['needs_fact_check_count']} | "
        f"{recall_text} | {manifest['failure_modes']} | "
        f"{manifest['source_hallucination_count']} | "
        f"{len(manifest['do_not_claim_violations'])} | "
        f"{metrics['counterpoint_included']} |"
    )


def _metrics_row(label: str, metrics: dict[str, Any]) -> str:
    recall = metrics["key_beat_recall"]
    recall_text = "n/a" if recall is None else f"{recall:.2f}"
    return (
        f"| {label} | {metrics['section_count']} | {metrics['slide_count']} | "
        f"{metrics['source_url_count']} | {metrics['needs_source_count']} | "
        f"{metrics['needs_fact_check_count']} | {metrics['counterpoint_included']} | "
        f"{metrics['source_image_overlap_count']} | {recall_text} |"
    )


def _report_markdown(
    *,
    fixture_name: str,
    manifest: dict[str, Any],
    schema_errors: list[str],
    empty_source_errors: list[str],
    fact_check_errors: list[str],
    do_not_claim_violations: list[str],
    key_beat_coverage_errors: list[str],
    counterpoint_included: bool,
    key_beat_recall_value: float | None,
    llm_api_called: bool,
) -> str:
    lines = [
        f"# Anny API Experiment Fixture Report — {fixture_name}",
        "",
        f"- fixture_name: {fixture_name}",
        f"- parse_status: {manifest['parse_status']}",
        f"- schema_valid: {manifest['schema_valid']}",
        f"- hygiene_passed: {manifest['hygiene_passed']}",
        f"- failure_modes: {manifest['failure_modes']}",
        f"- allowed_url_count: {manifest['allowed_url_count']}",
        f"- used_url_count: {manifest['used_url_count']}",
        f"- hallucinated_urls: {manifest['hallucinated_urls']}",
        f"- repair_attempted: {str(manifest['repair_attempted']).lower()}",
        f"- counterpoint_included: {counterpoint_included}",
        f"- key_beat_recall: {key_beat_recall_value}",
        f"- ready_for_api_experiment_prep: {manifest['ready_for_api_experiment_prep']}",
        f"- ready_for_api_experiment: {manifest['ready_for_api_experiment']}",
        f"- ready_for_production_agent: {manifest['ready_for_production_agent']}",
        f"- ready_for_broadcast: {manifest['ready_for_broadcast']}",
        "",
        "## Error Detail",
        "",
        f"- schema_errors: {schema_errors or []}",
        f"- empty_source_errors: {empty_source_errors or []}",
        f"- fact_check_errors: {fact_check_errors or []}",
        f"- key_beat_coverage_errors: {key_beat_coverage_errors or []}",
        f"- do_not_claim_violations: {do_not_claim_violations or []}",
        "",
        "## Policy",
        "",
        f"- llm_api_called: {str(llm_api_called).lower()}",
        "- repair_attempted: false",
        "- raw_model_output_retained: true",
    ]
    return "\n".join(lines) + "\n"


@app.callback(invoke_without_command=True)
def main(
    raw_output_path: Annotated[
        Path,
        typer.Option("--raw-output", help="Raw model output text fixture."),
    ],
    input_bundle_path: Annotated[
        Path,
        typer.Option("--input-bundle", help="Anny input bundle JSON."),
    ] = DEFAULT_INPUT_BUNDLE,
    evidence_pack_path: Annotated[
        Path,
        typer.Option("--evidence-pack", help="Evidence pack JSON."),
    ] = DEFAULT_EVIDENCE_PACK,
    output_root: Annotated[
        Path,
        typer.Option("--output-root", help="Validation report root."),
    ] = DEFAULT_OUTPUT_ROOT,
    experiment_root: Annotated[
        Path,
        typer.Option("--experiment-root", help="API experiment artifact root."),
    ] = DEFAULT_EXPERIMENT_ROOT,
    case_id: Annotated[str, typer.Option("--case-id")] = DEFAULT_CASE_ID,
) -> None:
    fixture_name = raw_output_path.stem
    result = validate_api_experiment_raw_output(
        raw_output_path=raw_output_path,
        input_bundle_path=input_bundle_path,
        evidence_pack_path=evidence_pack_path,
        experiment_dir=experiment_root / fixture_name,
        report_path=output_root / f"{fixture_name}.md",
        case_id=case_id,
    )
    if result.ready_for_api_experiment:
        console.print(f"[green]{fixture_name}: passed[/green]")
    else:
        console.print(f"[yellow]{fixture_name}: failed {result.failure_modes}[/yellow]")


@run_app.callback(invoke_without_command=True)
def run_main(
    ctx: typer.Context,
    run_id: Annotated[
        str,
        typer.Option("--run-id", help="Controlled API experiment run id."),
    ] = DEFAULT_API_EXPERIMENT_RUN_ID,
    model: Annotated[
        str | None,
        typer.Option(
            "--model",
            help="OpenAI model override. Defaults to LUDDITE_ANNY_API_MODEL.",
        ),
    ] = None,
    timeout_seconds: Annotated[
        int,
        typer.Option("--timeout", help="OpenAI API timeout in seconds."),
    ] = 120,
) -> None:
    if ctx.invoked_subcommand:
        return
    try:
        result = run_api_experiment(
            run_id=run_id,
            model=model,
            timeout_seconds=timeout_seconds,
        )
    except RuntimeError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(1) from exc
    console.print(
        "[green]Wrote anny API experiment artifacts "
        f"for {result['run_id']} using {result['model']}.[/green]"
    )
    if result["failure_modes"]:
        console.print(f"[yellow]failure_modes={result['failure_modes']}[/yellow]")


@run_app.command("compare-v1-v2")
def compare_v1_v2(
    v1_run_id: Annotated[str, typer.Option("--v1-run-id")] = DEFAULT_API_EXPERIMENT_RUN_ID,
    v2_run_id: Annotated[
        str,
        typer.Option("--v2-run-id"),
    ] = DEFAULT_SECOND_API_EXPERIMENT_RUN_ID,
) -> None:
    write_api_v1_v2_comparison_report(
        v1_dir=DEFAULT_EXPERIMENT_ROOT / v1_run_id,
        v2_dir=DEFAULT_EXPERIMENT_ROOT / v2_run_id,
    )
    console.print("[green]Wrote anny API experiment v1/v2 comparison.[/green]")


if __name__ == "__main__":
    app()
