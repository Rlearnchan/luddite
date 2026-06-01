"""Evidence-based reviewer-board copy rewrite previews for Jibi."""

from __future__ import annotations

import json
import os
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Any, Protocol

import typer
from rich.console import Console

from luddite import paths
from luddite.agents.jibi.llm_client import (
    OpenAIResponsesClient,
    jibi_llm_model,
    parse_json_object,
)

app = typer.Typer(no_args_is_help=False)
console = Console()


class LlmJsonClient(Protocol):
    model: str

    def json_response(
        self,
        prompt: str,
        *,
        timeout_seconds: int = 120,
        max_output_tokens: int = 1200,
    ) -> tuple[str, dict[str, Any]]:
        """Return JSON text plus raw response payload."""


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def _by_bundle_id(items: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {str(item.get("story_bundle_id") or ""): item for item in items}


def _compact_json(value: Any, *, limit: int = 9000) -> str:
    text = json.dumps(value, ensure_ascii=False, sort_keys=True)
    if len(text) <= limit:
        return text
    return text[: limit - 3] + "..."


def _clip_text(text: str, limit: int) -> str:
    text = " ".join(str(text or "").split())
    if len(text) <= limit:
        return text
    return text[:limit].rstrip()


def _fallback_title(item: dict[str, Any], judge_row: dict[str, Any]) -> str:
    title = str(item.get("visible_title") or judge_row.get("visible_title") or "")
    if title and not title.startswith("해외 후보"):
        return _clip_text(title, 48)
    question = str(judge_row.get("opening_question") or "")
    if question:
        return _clip_text(question.rstrip("?？") + "?", 48)
    return _clip_text(title or "검토 후보", 48)


def _fallback_description(item: dict[str, Any], judge_row: dict[str, Any]) -> str:
    missing = judge_row.get("missing_evidence") or []
    why = str(judge_row.get("why_it_could_work") or "")
    if why:
        base = why
    else:
        article_bodies = item.get("article_bodies") or []
        first = next((body for body in article_bodies if body.get("body_excerpt")), {})
        base = str(first.get("body_excerpt") or item.get("visible_description") or "")
    if missing:
        base = f"{base} 보강 필요: {missing[0]}"
    return _clip_text(base, 140)


def build_rewrite_prompt(item: dict[str, Any], judge_row: dict[str, Any]) -> str:
    payload = {
        "candidate": item,
        "llm_judge": judge_row,
    }
    return f"""
You rewrite reviewer-board copy for Jibi, a Korean broadcast-topic triage tool.
This is report-only. Do not change selection. Do not invent facts, numbers,
quotes, source names, or URLs. Use only the supplied evidence pack and judge output.

Return exactly one Korean JSON object with:
title, description, why_rewrite, source_evidence_used.

Constraints:
- title: Korean, concrete, <= 38 Korean characters when possible.
- description: Korean, one sentence, <= 120 Korean characters when possible.
- If evidence is thin, keep the description honest and mention what still needs checking.
- Avoid generic labels like "해외 후보" or "한 가지 질문으로 더 좁혀볼 소재".
- Do not include markdown.

Input:
{_compact_json(payload)}
""".strip()


def normalize_rewrite_payload(
    payload: dict[str, Any],
    *,
    item: dict[str, Any],
    judge_row: dict[str, Any],
) -> dict[str, Any]:
    evidence = payload.get("source_evidence_used") or []
    if isinstance(evidence, str):
        evidence = [evidence]
    title = str(payload.get("title") or "").strip()
    description = str(payload.get("description") or "").strip()
    return {
        "title": _clip_text(title or _fallback_title(item, judge_row), 54),
        "description": _clip_text(
            description or _fallback_description(item, judge_row),
            150,
        ),
        "reason": "evidence_pack_llm_copy_preview",
        "why_rewrite": str(payload.get("why_rewrite") or "evidence_pack_based_preview"),
        "source_evidence_used": [str(value) for value in evidence][:6],
    }


def rewrite_copy_item(
    item: dict[str, Any],
    judge_row: dict[str, Any],
    *,
    llm_client: LlmJsonClient | None = None,
    timeout_seconds: int = 120,
) -> dict[str, Any]:
    if llm_client is None:
        return normalize_rewrite_payload({}, item=item, judge_row=judge_row)
    prompt = build_rewrite_prompt(item, judge_row)
    text, raw_payload = llm_client.json_response(
        prompt,
        timeout_seconds=timeout_seconds,
        max_output_tokens=900,
    )
    result = normalize_rewrite_payload(
        parse_json_object(text),
        item=item,
        judge_row=judge_row,
    )
    result["llm_response_id"] = raw_payload.get("id") if isinstance(raw_payload, dict) else None
    return result


def _env_enabled(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in {"1", "true", "yes", "on"}


def build_board_copy_rewrite_preview(
    *,
    evidence_pack_path: Path,
    llm_judge_path: Path,
    max_items: int = 10,
    enabled: bool | None = None,
    model: str | None = None,
    llm_client: LlmJsonClient | None = None,
    timeout_seconds: int = 120,
) -> dict[str, Any]:
    evidence_pack = _load_json(evidence_pack_path)
    llm_judge = _load_json(llm_judge_path)
    evidence_by_id = _by_bundle_id(
        [item for item in evidence_pack.get("items", []) if isinstance(item, dict)]
    )
    judge_items = [item for item in llm_judge.get("items", []) if isinstance(item, dict)]
    if max_items > 0:
        judge_items = judge_items[:max_items]
    active = _env_enabled("JIBI_LLM_COPY_REWRITE") if enabled is None else enabled
    active_model = jibi_llm_model(model)
    client = llm_client
    if active and client is None:
        client = OpenAIResponsesClient(model=active_model)
    items: dict[str, dict[str, Any]] = {}
    preview_rows: list[dict[str, Any]] = []
    for judge_row in judge_items:
        evidence_item = evidence_by_id.get(str(judge_row.get("story_bundle_id") or ""))
        if not evidence_item:
            continue
        rewrite = rewrite_copy_item(
            evidence_item,
            judge_row,
            llm_client=client if active else None,
            timeout_seconds=timeout_seconds,
        )
        review_item_id = str(evidence_item.get("review_item_id") or "")
        key = review_item_id or str(evidence_item.get("story_fingerprint") or "")
        if not key:
            key = str(evidence_item.get("story_bundle_id") or "")
        items[key] = rewrite
        preview_rows.append(
            {
                "key": key,
                "story_bundle_id": evidence_item.get("story_bundle_id") or "",
                "old_title": evidence_item.get("visible_title") or "",
                "new_title": rewrite["title"],
                "old_description": evidence_item.get("visible_description") or "",
                "new_description": rewrite["description"],
                "llm_role": judge_row.get("llm_editorial_role") or "",
                "llm_confidence": judge_row.get("llm_confidence") or "",
                "why_rewrite": rewrite.get("why_rewrite") or "",
            }
        )
    return {
        "run_date": evidence_pack.get("run_date") or llm_judge.get("run_date") or "",
        "evidence_pack_path": str(evidence_pack_path),
        "llm_judge_path": str(llm_judge_path),
        "llm_copy_rewrite_enabled": active,
        "llm_model": active_model,
        "item_count": len(items),
        "role_counts": dict(Counter(row["llm_role"] for row in preview_rows)),
        "items": items,
        "preview_rows": preview_rows,
    }


def _table_cell(value: object, *, limit: int = 140) -> str:
    text = " ".join(str(value or "").split())
    if len(text) > limit:
        text = text[: limit - 3].rstrip() + "..."
    return text.replace("|", "\\|")


def write_board_copy_rewrite_preview(
    *,
    payload: dict[str, Any],
    output_json: Path,
    output_md: Path,
) -> None:
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_md.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    lines = [
        f"# Jibi Evidence-Based Copy Rewrite Preview — {payload.get('run_date')}",
        "",
        "## Summary",
        "",
        f"- llm_copy_rewrite_enabled: {str(payload.get('llm_copy_rewrite_enabled')).lower()}",
        f"- llm_model: `{payload.get('llm_model')}`",
        f"- item_count: {payload.get('item_count', 0)}",
        "",
        "## Preview Rows",
        "",
        "| old title | new title | new description | llm role | why |",
        "| --- | --- | --- | --- | --- |",
    ]
    for row in payload.get("preview_rows", []):
        lines.append(
            "| "
            + " | ".join(
                [
                    _table_cell(row.get("old_title")),
                    _table_cell(row.get("new_title")),
                    _table_cell(row.get("new_description"), limit=180),
                    _table_cell(row.get("llm_role")),
                    _table_cell(row.get("why_rewrite")),
                ]
            )
            + " |"
        )
    if not payload.get("preview_rows"):
        lines.append("| none | none | none | none | none |")
    lines.extend(
        [
            "",
            "## Safety Note",
            "",
            (
                "This preview is renderer-compatible but not written to the default "
                "`jibi_review_board_YYYY-MM-DD.json` path unless explicitly requested."
            ),
            "",
        ]
    )
    output_md.write_text("\n".join(lines), encoding="utf-8")


def run_board_copy_rewrite_preview(
    *,
    run_date: str,
    evidence_pack_path: Path | None = None,
    llm_judge_path: Path | None = None,
    output_json: Path | None = None,
    output_md: Path | None = None,
    max_items: int = 10,
    enabled: bool | None = None,
    model: str | None = None,
    llm_client: LlmJsonClient | None = None,
) -> tuple[Path, Path, dict[str, Any]]:
    evidence_path = evidence_pack_path or paths.REPORTS_DIR / f"jibi_evidence_pack_{run_date}.json"
    judge_path = llm_judge_path or paths.REPORTS_DIR / f"jibi_llm_editorial_judge_{run_date}.json"
    payload = build_board_copy_rewrite_preview(
        evidence_pack_path=evidence_path,
        llm_judge_path=judge_path,
        max_items=max_items,
        enabled=enabled,
        model=model,
        llm_client=llm_client,
    )
    json_path = output_json or (
        paths.JIBI_EDITORIAL_OVERRIDES_DIR
        / f"jibi_review_board_{run_date}.evidence_preview.json"
    )
    md_path = output_md or paths.REPORTS_DIR / f"jibi_board_copy_rewrite_{run_date}.md"
    write_board_copy_rewrite_preview(payload=payload, output_json=json_path, output_md=md_path)
    return json_path, md_path, payload


@app.callback(invoke_without_command=True)
def main(
    date_text: Annotated[
        str | None,
        typer.Option("--date", help="Run date for default input/output filenames."),
    ] = None,
    evidence_pack_path: Annotated[
        Path | None,
        typer.Option("--evidence-pack", help="Jibi evidence pack JSON."),
    ] = None,
    llm_judge_path: Annotated[
        Path | None,
        typer.Option("--llm-judge", help="Jibi LLM editorial judge JSON."),
    ] = None,
    output_json: Annotated[
        Path | None,
        typer.Option("--output-json", help="Renderer-compatible preview JSON."),
    ] = None,
    output_md: Annotated[
        Path | None,
        typer.Option("--output-md", help="Markdown preview report."),
    ] = None,
    max_items: Annotated[
        int,
        typer.Option("--max-items", help="Maximum rows to rewrite; 0 means all."),
    ] = 10,
    model: Annotated[
        str | None,
        typer.Option("--model", help="OpenAI model override; defaults to gpt-5-mini lane."),
    ] = None,
    force: Annotated[
        bool,
        typer.Option("--force/--respect-env", help="Run LLM rewrites even if env is off."),
    ] = False,
) -> None:
    run_date = date_text or datetime.now(UTC).date().isoformat()
    json_path, md_path, payload = run_board_copy_rewrite_preview(
        run_date=run_date,
        evidence_pack_path=evidence_pack_path,
        llm_judge_path=llm_judge_path,
        output_json=output_json,
        output_md=output_md,
        max_items=max_items,
        enabled=True if force else None,
        model=model,
    )
    console.print(
        "[green]Wrote Jibi board copy rewrite preview "
        f"({payload['item_count']} rows) to {json_path} and {md_path}.[/green]"
    )


if __name__ == "__main__":
    app()

