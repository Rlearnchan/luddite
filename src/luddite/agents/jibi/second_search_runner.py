"""Local second-search execution against already collected Jibi article pools."""

from __future__ import annotations

import json
import re
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Any

import typer
from rich.console import Console

from luddite import paths
from luddite.utils.jsonl import read_jsonl
from luddite.utils.urls import canonicalize_url

app = typer.Typer(no_args_is_help=False)
console = Console()

DEFAULT_POOL_PATHS = [
    paths.DATA_DIR / "candidates" / "raw_articles.jsonl",
    paths.DATA_DIR / "candidates" / "jibi_scored_candidates.jsonl",
]

STOPWORDS = {
    "2026",
    "case",
    "news",
    "latest",
    "recent",
    "최신",
    "뉴스",
    "최근",
    "정책",
    "발표",
    "통계",
    "사례",
    "영향",
    "반론",
    "리스크",
    "논란",
    "현장",
    "구조",
    "변화",
    "한국",
    "산업",
    "시장",
    "전체",
    "제도",
    "규제",
    "정책",
    "비용",
    "개최",
    "줄이는",
    "영향",
    "생활비",
    "실물경제",
    "자료",
    "문제",
}
SHORT_ALLOWED_TERMS = {"AI", "RWA", "STO", "PF"}


def compact_text(value: object) -> str:
    return " ".join(str(value or "").split())


def _norm(value: object) -> str:
    return re.sub(r"\s+", "", compact_text(value).lower())


def _default_plan_path(run_date: str) -> Path:
    return paths.REPORTS_DIR / f"jibi_second_search_plan_{run_date}.json"


def _default_markdown_path(run_date: str) -> Path:
    return paths.REPORTS_DIR / f"jibi_second_search_results_{run_date}.md"


def _default_json_path(run_date: str) -> Path:
    return paths.REPORTS_DIR / f"jibi_second_search_results_{run_date}.json"


def _load_plan(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _url(record: dict[str, Any]) -> str:
    return compact_text(
        record.get("url")
        or record.get("seed_url")
        or record.get("source_url_canonical")
        or record.get("link")
    )


def _article_id(record: dict[str, Any]) -> str:
    return compact_text(
        record.get("article_id")
        or record.get("candidate_id")
        or record.get("duplicate_key")
        or canonicalize_url(_url(record))
    )


def _article_text(record: dict[str, Any]) -> str:
    parts = [
        record.get("title"),
        record.get("summary"),
        record.get("raw_summary"),
        record.get("why_interesting"),
        record.get("source"),
        record.get("source_id"),
        " ".join(str(item) for item in record.get("source_sections", []) or []),
        " ".join(str(item) for item in record.get("tags", []) or []),
        " ".join(str(item) for item in record.get("possible_expansions", []) or []),
        " ".join(str(item) for item in record.get("evidence_needed", []) or []),
    ]
    return compact_text(" ".join(compact_text(part) for part in parts))


def _dedupe_articles(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    output: list[dict[str, Any]] = []
    for record in records:
        key = canonicalize_url(_url(record)) or _article_id(record)
        if not key or key in seen:
            continue
        seen.add(key)
        output.append(record)
    return output


def load_article_pool(paths_in: list[Path]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for path in paths_in:
        if not path.exists():
            continue
        records.extend(read_jsonl(path))
    return _dedupe_articles(records)


def _terms_from_query(query: str) -> list[str]:
    tokens = [
        token.strip("\"'‘’“”.,:;()[]{}")
        for token in re.split(r"\s+", compact_text(query))
    ]
    return [
        token
        for token in tokens
        if _useful_term(token)
    ]


def _useful_term(term: str) -> bool:
    token = compact_text(term).strip("\"'‘’“”.,:;()[]{}")
    if not token:
        return False
    if token in SHORT_ALLOWED_TERMS:
        return True
    if token.lower() in STOPWORDS or token in STOPWORDS:
        return False
    if len(token) < 2:
        return False
    return True


def _specific_term(term: str) -> bool:
    token = compact_text(term)
    if token in SHORT_ALLOWED_TERMS:
        return True
    if " " in token:
        return True
    if re.search(r"\d", token):
        return True
    if len(token) >= 4:
        return True
    if token in {"스벅", "양파", "유가"}:
        return True
    return False


def _plan_terms(plan: dict[str, Any]) -> list[str]:
    terms: list[str] = []
    terms.extend(str(item) for item in plan.get("topic_terms", []) if _useful_term(str(item)))
    for task in plan.get("query_plan", []):
        for query in task.get("queries", []) or []:
            terms.extend(_terms_from_query(str(query)))
    return list(dict.fromkeys(terms))


def _excluded_urls(plan: dict[str, Any]) -> set[str]:
    urls = {canonicalize_url(str(plan.get("main_link") or ""))}
    urls.update(canonicalize_url(str(item)) for item in plan.get("sub_links", []) or [])
    return {url for url in urls if url}


def _match_terms(article_text: str, terms: list[str]) -> list[str]:
    lower = article_text.lower()
    matches = []
    for term in terms:
        term_text = compact_text(term)
        if not term_text:
            continue
        if _term_in_text(term_text, lower):
            matches.append(term_text)
    return list(dict.fromkeys(matches))


def _term_in_text(term: str, lower_text: str) -> bool:
    term_lower = term.lower()
    if term in SHORT_ALLOWED_TERMS or re.fullmatch(r"[a-zA-Z]{2,3}", term):
        return bool(re.search(rf"\b{re.escape(term_lower)}\b", lower_text))
    if re.fullmatch(r"[가-힣]{2}", term):
        return bool(re.search(rf"(?<![가-힣]){re.escape(term)}(?![가-힣])", lower_text))
    return term_lower in lower_text


def _score_match(
    record: dict[str, Any],
    terms: list[str],
    *,
    preferred_sources: list[str],
) -> tuple[int, list[str]]:
    text = _article_text(record)
    title = compact_text(record.get("title"))
    title_lower = title.lower()
    matches = _match_terms(text, terms)
    if not matches:
        return 0, []
    if not any(_specific_term(term) for term in matches):
        return 0, []
    score = 0
    for term in matches:
        if term.lower() in title_lower:
            score += 4
        elif len(term) >= 4:
            score += 2
        else:
            score += 1
    source = compact_text(record.get("source"))
    if source and any(source in preferred or preferred in source for preferred in preferred_sources):
        score += 2
    if record.get("published_at"):
        score += 1
    return score, matches


def _snippet(record: dict[str, Any], matches: list[str]) -> str:
    text = compact_text(record.get("summary") or record.get("raw_summary") or record.get("why_interesting"))
    if not text:
        text = compact_text(record.get("title"))
    if len(text) <= 220:
        return text
    lowered = text.lower()
    positions = [
        lowered.find(term.lower())
        for term in matches
        if term and lowered.find(term.lower()) >= 0
    ]
    start = max(0, min(positions) - 60) if positions else 0
    return ("..." if start else "") + text[start : start + 220].strip() + "..."


def run_local_second_search(
    *,
    run_date: str,
    plan_payload: dict[str, Any],
    article_pool: list[dict[str, Any]],
    per_plan_limit: int = 5,
    min_score: int = 6,
) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for plan in plan_payload.get("plans", []):
        terms = _plan_terms(plan)
        excluded = _excluded_urls(plan)
        plan_title_norm = _norm(plan.get("title"))
        preferred_sources = [str(item) for item in plan.get("source_suggestions", [])]
        matches: list[dict[str, Any]] = []
        for article in article_pool:
            url = canonicalize_url(_url(article))
            if url and url in excluded:
                continue
            if plan_title_norm and _norm(article.get("title")) == plan_title_norm:
                continue
            score, matched_terms = _score_match(
                article,
                terms,
                preferred_sources=preferred_sources,
            )
            if score < min_score:
                continue
            matches.append(
                {
                    "match_score": score,
                    "matched_terms": matched_terms,
                    "title": compact_text(article.get("title")),
                    "source": compact_text(article.get("source")),
                    "published_at": compact_text(article.get("published_at")),
                    "url": _url(article),
                    "snippet": _snippet(article, matched_terms),
                    "article_id": _article_id(article),
                }
            )
        matches.sort(
            key=lambda item: (
                -int(item["match_score"]),
                str(item.get("source")),
                str(item.get("title")),
            )
        )
        rows.append(
            {
                "id": plan.get("id", ""),
                "title": plan.get("title", ""),
                "priority": plan.get("priority", ""),
                "actions": plan.get("actions", []),
                "topic_terms": terms,
                "match_count": len(matches),
                "top_matches": matches[:per_plan_limit],
            }
        )
    match_count_total = sum(int(row["match_count"]) for row in rows)
    priority_counts = Counter(str(row.get("priority") or "unknown") for row in rows)
    return {
        "run_date": run_date,
        "generated_at": datetime.now(UTC).isoformat(),
        "plan_rows": len(plan_payload.get("plans", [])),
        "article_pool_count": len(article_pool),
        "matched_rows": sum(1 for row in rows if row["match_count"]),
        "match_count_total": match_count_total,
        "priority_counts": dict(priority_counts),
        "rows": rows,
    }


def _table_cell(value: object) -> str:
    return compact_text(value).replace("|", "\\|") or "-"


def render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        f"# Jibi Local Second-Search Results — {payload['run_date']}",
        "",
        f"- Generated at: `{payload['generated_at']}`",
        f"- Plan rows: {payload['plan_rows']}",
        f"- Article pool: {payload['article_pool_count']}",
        f"- Rows with matches: {payload['matched_rows']}",
        f"- Total matches: {payload['match_count_total']}",
        "",
        "## Match Summary",
        "",
        "| priority | title | matches | top match |",
        "| --- | --- | ---: | --- |",
    ]
    for row in payload["rows"]:
        top = row["top_matches"][0] if row["top_matches"] else {}
        top_label = (
            f"{top.get('source', '')}: {top.get('title', '')}"
            if top
            else "none"
        )
        lines.append(
            "| "
            + " | ".join(
                [
                    _table_cell(row["priority"]),
                    _table_cell(row["title"]),
                    str(row["match_count"]),
                    _table_cell(top_label),
                ]
            )
            + " |"
        )
    lines.extend(["", "## Detail", ""])
    for row in payload["rows"]:
        lines.append(f"### {row['title'] or row['id']}")
        lines.append("")
        lines.append(f"- ID: `{row['id']}`")
        lines.append(f"- priority: `{row['priority']}`")
        lines.append(f"- actions: `{', '.join(row['actions']) or 'none'}`")
        lines.append(f"- topic_terms: `{', '.join(row['topic_terms'][:10]) or 'none'}`")
        if not row["top_matches"]:
            lines.append("- local_matches: none")
            lines.append("")
            continue
        for match in row["top_matches"]:
            lines.append(
                f"- {match['source']} / score {match['match_score']}: "
                f"[{match['title']}]({match['url']})"
            )
            lines.append(
                f"  - matched_terms: `{', '.join(match['matched_terms']) or 'none'}`"
            )
            if match.get("published_at"):
                lines.append(f"  - published_at: `{match['published_at']}`")
            if match.get("snippet"):
                lines.append(f"  - snippet: {match['snippet']}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def write_local_second_search_results(
    *,
    run_date: str,
    plan_path: Path,
    article_paths: list[Path],
    markdown_path: Path,
    json_path: Path,
    per_plan_limit: int = 5,
    min_score: int = 3,
) -> tuple[Path, Path, dict[str, Any]]:
    plan = _load_plan(plan_path)
    article_pool = load_article_pool(article_paths)
    payload = run_local_second_search(
        run_date=run_date,
        plan_payload=plan,
        article_pool=article_pool,
        per_plan_limit=per_plan_limit,
        min_score=min_score,
    )
    payload["plan_path"] = str(plan_path)
    payload["article_paths"] = [str(path) for path in article_paths]
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.write_text(render_markdown(payload), encoding="utf-8")
    json_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return markdown_path, json_path, payload


@app.command("main")
def main(
    date: Annotated[str, typer.Option("--date", help="Jibi run date YYYY-MM-DD.")] = "",
    plan: Annotated[
        Path | None,
        typer.Option("--plan", help="Second-search plan JSON."),
    ] = None,
    article_pool: Annotated[
        list[Path] | None,
        typer.Option("--article-pool", help="JSONL article/candidate pool. Repeatable."),
    ] = None,
    markdown: Annotated[
        Path | None,
        typer.Option("--markdown", help="Output markdown path."),
    ] = None,
    output_json: Annotated[
        Path | None,
        typer.Option("--json", help="Output JSON path."),
    ] = None,
    per_plan_limit: Annotated[
        int,
        typer.Option("--per-plan-limit", help="Max matches per plan row."),
    ] = 5,
    min_score: Annotated[
        int,
        typer.Option("--min-score", help="Minimum local match score."),
    ] = 6,
) -> None:
    run_date = date or datetime.now().strftime("%Y-%m-%d")
    md_path, json_path, payload = write_local_second_search_results(
        run_date=run_date,
        plan_path=plan or _default_plan_path(run_date),
        article_paths=article_pool or DEFAULT_POOL_PATHS,
        markdown_path=markdown or _default_markdown_path(run_date),
        json_path=output_json or _default_json_path(run_date),
        per_plan_limit=per_plan_limit,
        min_score=min_score,
    )
    console.print(
        "[green]Wrote Jibi local second-search results "
        f"({payload['matched_rows']} matched rows): {md_path} / {json_path}[/green]"
    )


if __name__ == "__main__":
    typer.run(main)
