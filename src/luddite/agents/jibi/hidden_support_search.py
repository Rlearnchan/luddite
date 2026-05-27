"""Hidden support evidence search for pre-review Jibi board calibration."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Any
from urllib.parse import urlparse

import typer
from rich.console import Console

from luddite import paths
from luddite.agents.jibi.board_support_search import (
    NOISY_SUPPORT_HINTS,
    TRUSTED_SUPPORT_DOMAINS,
)
from luddite.agents.jibi.second_search_web import (
    DEFAULT_ENV_FILE,
    NaverSearchProvider,
    SearchProvider,
    _result_is_relevant,
    load_env_file,
)
from luddite.utils.urls import canonicalize_url

app = typer.Typer(no_args_is_help=False)
console = Console()

DEFAULT_CATEGORIES = ["news", "webkr"]
GENERIC_TERMS = {
    "ai",
    "AI",
    "jibi",
    "자료",
    "기사",
    "후보",
    "설명",
    "선정",
    "이유",
    "한국",
    "뉴스",
    "정책",
    "통계",
    "사례",
    "구조",
    "문제",
    "원문",
}


@dataclass(frozen=True)
class HiddenSupportResult:
    title: str
    url: str
    source: str
    snippet: str
    query: str
    query_type: str
    category: str
    rank: int
    matched_terms: list[str]
    usefulness_score: int
    usefulness_reason: str


def default_metadata_path(run_date: str) -> Path:
    return paths.OUTPUTS_DIR / "daily_digest" / f"{run_date}_bundle_review_sheet_metadata.json"


def default_markdown_path(run_date: str) -> Path:
    return paths.REPORTS_DIR / f"jibi_hidden_support_search_{run_date}.md"


def default_json_path(run_date: str) -> Path:
    return paths.REPORTS_DIR / f"jibi_hidden_support_search_{run_date}.json"


def provider_from_env(env_file: Path | None = DEFAULT_ENV_FILE) -> NaverSearchProvider:
    load_env_file(env_file)
    return NaverSearchProvider.from_env()


def compact_text(value: object) -> str:
    return " ".join(str(value or "").split())


def run_hidden_support_search(
    *,
    run_date: str,
    metadata_payload: dict[str, Any],
    provider: SearchProvider,
    categories: list[str] | None = None,
    max_links_per_row: int = 3,
    results_per_query: int = 5,
    max_provider_calls: int = 60,
) -> dict[str, Any]:
    categories = categories or DEFAULT_CATEGORIES
    generated_at = datetime.now(UTC).isoformat()
    calls_used = 0
    rows = []
    for metadata in metadata_payload.get("rows", []):
        if not isinstance(metadata, dict):
            continue
        if calls_used >= max_provider_calls:
            break
        row_id = compact_text(metadata.get("ID") or metadata.get("review_item_id"))
        if not row_id:
            continue
        excluded = _excluded_urls(metadata)
        accepted: list[HiddenSupportResult] = []
        rejected_low_relevance = 0
        query_runs: list[dict[str, Any]] = []
        seen_for_row: set[str] = set()
        for query_spec in _queries_for_metadata(metadata):
            if calls_used >= max_provider_calls:
                break
            query = query_spec["query"]
            query_type = query_spec["query_type"]
            for category in categories:
                if calls_used >= max_provider_calls:
                    break
                results = provider.search(
                    query,
                    category=category,
                    max_results=results_per_query,
                )
                calls_used += 1
                accepted_count = 0
                rejected_count = 0
                for result in results:
                    canonical = canonicalize_url(result.url) or result.url
                    if not canonical or canonical in excluded or canonical in seen_for_row:
                        continue
                    relevant, matched_terms = _result_is_relevant(result, query)
                    if not relevant:
                        rejected_low_relevance += 1
                        rejected_count += 1
                        continue
                    score, reason = _support_usefulness(
                        metadata=metadata,
                        result=result,
                        query_type=query_type,
                        matched_terms=matched_terms,
                    )
                    if score < 8:
                        rejected_low_relevance += 1
                        rejected_count += 1
                        continue
                    seen_for_row.add(canonical)
                    accepted.append(
                        HiddenSupportResult(
                            title=result.title,
                            url=result.url,
                            source=result.source or result.provider,
                            snippet=result.snippet,
                            query=query,
                            query_type=query_type,
                            category=category,
                            rank=result.rank,
                            matched_terms=matched_terms,
                            usefulness_score=score,
                            usefulness_reason=reason,
                        )
                    )
                    accepted_count += 1
                query_runs.append(
                    {
                        "query": query,
                        "query_type": query_type,
                        "category": category,
                        "returned": len(results),
                        "accepted": accepted_count,
                        "rejected_low_relevance": rejected_count,
                    }
                )
        selected = _best_items(accepted, limit=max_links_per_row)
        rows.append(
            {
                "review_item_id": row_id,
                "review_title": compact_text(metadata.get("title")),
                "origin_title": _origin_title(metadata),
                "source": compact_text(metadata.get("source")),
                "source_role": compact_text(
                    metadata.get("source_role") or metadata.get("source_role_class")
                ),
                "seed_type": compact_text(metadata.get("seed_type")),
                "main_link": compact_text(metadata.get("main_link")),
                "board_score": metadata.get("board_score"),
                "story_role": compact_text(metadata.get("story_role")),
                "query_basis": "origin_metadata_only",
                "queries": query_runs,
                "accepted_count": len(accepted),
                "rejected_low_relevance_count": rejected_low_relevance,
                "hidden_support_status": _hidden_support_status(selected, rejected_low_relevance),
                "selected_links": [item.url for item in selected],
                "selected_link_details": [_result_payload(item) for item in selected],
                "accepted_links": [_result_payload(item) for item in accepted],
            }
        )
    payload = {
        "run_date": run_date,
        "generated_at": generated_at,
        "provider": provider.name,
        "categories": categories,
        "max_links_per_row": max_links_per_row,
        "results_per_query": results_per_query,
        "max_provider_calls": max_provider_calls,
        "calls_used": calls_used,
        "rows": rows,
        "rows_with_hidden_support": sum(1 for row in rows if row["selected_links"]),
        "accepted_links_total": sum(len(row["accepted_links"]) for row in rows),
        "selected_links_total": sum(len(row["selected_links"]) for row in rows),
    }
    return payload


def write_hidden_support_search(
    *,
    run_date: str,
    metadata_path: Path,
    provider: SearchProvider,
    markdown_path: Path,
    json_path: Path,
    categories: list[str],
    max_links_per_row: int,
    results_per_query: int,
    max_provider_calls: int,
) -> tuple[Path, Path, dict[str, Any]]:
    metadata_payload = _load_metadata(metadata_path)
    payload = run_hidden_support_search(
        run_date=run_date,
        metadata_payload=metadata_payload,
        provider=provider,
        categories=categories,
        max_links_per_row=max_links_per_row,
        results_per_query=results_per_query,
        max_provider_calls=max_provider_calls,
    )
    payload["metadata_path"] = str(metadata_path)
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.write_text(render_markdown(payload), encoding="utf-8")
    json_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return markdown_path, json_path, payload


def render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        f"# Jibi Hidden Support Search — {payload['run_date']}",
        "",
        f"- Generated at: `{payload['generated_at']}`",
        f"- Provider: `{payload['provider']}`",
        f"- Categories: `{', '.join(payload['categories'])}`",
        f"- Calls used: {payload['calls_used']}/{payload['max_provider_calls']}",
        f"- Rows with hidden support: {payload['rows_with_hidden_support']}",
        f"- Selected links total: {payload['selected_links_total']}",
        "",
        "## Operator Note",
        "",
        (
            "- 이 report는 리뷰 전 숨은 보강자료 후보를 준비하기 위한 것입니다. "
            "Google Sheet의 `서브 링크`나 `설명`은 수정하지 않습니다."
        ),
        "- Query basis: 원문/metadata 중심. 사람이 다듬은 설명문은 query trigger로 쓰지 않습니다.",
        "",
        "## Rows",
        "",
        "| status | title | origin title | selected | rejected | first selected link |",
        "| --- | --- | --- | ---: | ---: | --- |",
    ]
    for row in payload["rows"]:
        selected = row.get("selected_link_details") or []
        first_link = "-"
        if selected:
            first = selected[0]
            first_link = f"[{_table_cell(first.get('title'))}]({first.get('url')})"
        lines.append(
            "| "
            + " | ".join(
                [
                    _table_cell(row.get("hidden_support_status")),
                    _table_cell(row.get("review_title")),
                    _table_cell(row.get("origin_title")),
                    str(len(row.get("selected_links") or [])),
                    str(row.get("rejected_low_relevance_count", 0)),
                    first_link,
                ]
            )
            + " |"
        )
    lines.extend(["", "## Detail", ""])
    for row in payload["rows"]:
        lines.append(f"### {row.get('review_title') or row.get('review_item_id')}")
        lines.append("")
        lines.append(f"- ID: `{row.get('review_item_id')}`")
        lines.append(f"- origin_title: `{row.get('origin_title')}`")
        lines.append(f"- status: `{row.get('hidden_support_status')}`")
        lines.append(f"- accepted_count: {row.get('accepted_count', 0)}")
        lines.append(f"- rejected_low_relevance: {row.get('rejected_low_relevance_count', 0)}")
        lines.append("- queries:")
        for query in row.get("queries", []):
            lines.append(
                "  - "
                f"{query.get('query_type')} / {query.get('category')}: "
                f"`{query.get('query')}` "
                f"(returned={query.get('returned')}, accepted={query.get('accepted')}, "
                f"rejected={query.get('rejected_low_relevance')})"
            )
        if row.get("selected_link_details"):
            lines.append("- selected:")
            for item in row["selected_link_details"]:
                lines.append(f"  - [{item['title']}]({item['url']})")
                lines.append(
                    f"    - source: `{item['source']}`, score: {item['usefulness_score']}, "
                    f"query_type: `{item['query_type']}`"
                )
                lines.append(f"    - reason: {item['usefulness_reason']}")
        else:
            lines.append("- selected: none")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _load_metadata(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"rows": []}
    return json.loads(path.read_text(encoding="utf-8"))


def _excluded_urls(metadata: dict[str, Any]) -> set[str]:
    urls = [metadata.get("main_link"), *(metadata.get("sub_links") or [])]
    return {canonicalize_url(str(url)) for url in urls if canonicalize_url(str(url))}


def _origin_title(metadata: dict[str, Any]) -> str:
    return compact_text(
        metadata.get("auto_title")
        or metadata.get("origin_title")
        or metadata.get("primary_title")
        or metadata.get("title")
    )


def _queries_for_metadata(metadata: dict[str, Any]) -> list[dict[str, str]]:
    origin_title = _origin_title(metadata)
    source = compact_text(metadata.get("source"))
    seed_type = compact_text(metadata.get("seed_type"))
    source_role = compact_text(metadata.get("source_role") or metadata.get("source_role_class"))
    terms = _keyword_terms(" ".join([origin_title, source, seed_type, source_role]))
    queries = [
        {
            "query_type": "origin_title",
            "query": _compact_query(" ".join(part for part in [origin_title, source] if part)),
        },
        {
            "query_type": "origin_precision",
            "query": _compact_query(" ".join([*terms[:5], source])),
        },
    ]
    system_query = _system_query(origin_title, seed_type, source_role, terms)
    if system_query:
        queries.append({"query_type": "system_context", "query": system_query})
    output: list[dict[str, str]] = []
    seen = set()
    for item in queries:
        query = compact_text(item.get("query"))
        if not query or query in seen:
            continue
        seen.add(query)
        output.append({"query_type": item["query_type"], "query": query})
    return output[:3]


def _system_query(
    origin_title: str,
    seed_type: str,
    source_role: str,
    terms: list[str],
) -> str:
    text = " ".join([origin_title, seed_type, source_role, " ".join(terms)])
    if any(term in text for term in ("열사병", "불볕더위", "산업현장")):
        return "폭염 산업현장 열사병 산재 작업중지권"
    if _has_ai_signal(text):
        return "AI 도입 책임 노동시장 규제 사례"
    if "실질임금" in text or "임금" in text:
        return "실질임금 물가 생활수준 통계"
    if "생산적" in text or "자금 흐름" in text or "금융시장" in text:
        return "생산적 금융 기업 투자 성장률 자금 흐름"
    if "전세" in text or "비아파트" in text or "오피스텔" in text:
        return "비아파트 공급 전세사기 주택시장"
    if "스타벅스" in text or "선불충전금" in text:
        return "선불충전금 환불 규제 사각지대 소비자 보호"
    if "전기차" in text or "페라리" in text:
        return "전기차 고급차 배터리 충전 인프라 시장"
    if source_role == "research_note":
        return _compact_query(" ".join([*terms[:3], "최신 뉴스 사례"]))
    if source_role == "public_wire":
        return _compact_query(" ".join([*terms[:3], "통계 사례"]))
    return _compact_query(" ".join([*terms[:3], "구조 사례"]))


def _keyword_terms(text: str) -> list[str]:
    terms = []
    for token in re.findall(r"[가-힣A-Za-z0-9][가-힣A-Za-z0-9·+.-]{1,}", text):
        cleaned = token.strip(".,:;()[]{}'\"‘’“”")
        if not cleaned or cleaned in GENERIC_TERMS or cleaned.lower() in GENERIC_TERMS:
            continue
        if _is_low_signal_token(cleaned):
            continue
        terms.append(cleaned)
    return list(dict.fromkeys(terms))[:8]


def _has_ai_signal(text: str) -> bool:
    if "인공지능" in text or "artificial intelligence" in text.lower():
        return True
    return bool(re.search(r"(?<![A-Za-z0-9])AI(?![A-Za-z0-9])", text))


def _is_low_signal_token(token: str) -> bool:
    return bool(re.fullmatch(r"20\d{2}|제\d+호|\d+호", token))


def _compact_query(value: str) -> str:
    return compact_text(value).strip(" -:|")


def _support_usefulness(
    *,
    metadata: dict[str, Any],
    result: Any,
    query_type: str,
    matched_terms: list[str],
) -> tuple[int, str]:
    score = 0
    reasons = []
    title = compact_text(result.title)
    body = compact_text(f"{result.title} {result.snippet}")
    title_matches = _matched_in_text(matched_terms, title)
    body_matches = _matched_in_text(matched_terms, body)
    domain = _domain(result.url)
    if len(matched_terms) >= 3:
        score += 4
        reasons.append("핵심어가 여러 개 겹침")
    elif len(matched_terms) >= 2:
        score += 2
        reasons.append("검색어와 직접 관련")
    if title_matches:
        score += min(4, len(title_matches) * 2)
        reasons.append("제목에서 주제어 확인")
    elif len(body_matches) >= 3:
        score += 2
        reasons.append("요약에서 보강 맥락 확인")
    if domain in TRUSTED_SUPPORT_DOMAINS or domain.endswith(".go.kr"):
        score += 4
        reasons.append("신뢰 가능한 출처")
    elif _is_major_domain_family(domain):
        score += 2
        reasons.append("대중 매체 출처")
    if query_type in {"origin_title", "origin_precision"}:
        score += 2
        reasons.append("원문 제목 기반 검색")
    if query_type == "system_context":
        score += 2
        reasons.append("구조/제도 맥락 보강")
    if int(getattr(result, "rank", 0) or 0) <= 2:
        score += 1
    if _same_topic_as_metadata(metadata, result):
        score += 2
        reasons.append("후보 원문과 주제어 공유")
    if _has_noisy_hint(title) or _has_noisy_hint(str(getattr(result, "snippet", ""))):
        score -= 5
    if not reasons:
        reasons.append("보강 자료 후보")
    return score, ", ".join(dict.fromkeys(reasons))


def _matched_in_text(terms: list[str], text: str) -> list[str]:
    normalized = re.sub(r"\s+", "", text.lower())
    matched = []
    for term in terms:
        term_normalized = re.sub(r"\s+", "", term.lower())
        if term_normalized and term_normalized in normalized:
            matched.append(term)
    return list(dict.fromkeys(matched))


def _domain(url: str) -> str:
    return urlparse(url).netloc.lower().removeprefix("www.")


def _is_major_domain_family(domain: str) -> bool:
    return any(domain == item or domain.endswith(f".{item}") for item in TRUSTED_SUPPORT_DOMAINS)


def _has_noisy_hint(text: str) -> bool:
    return any(hint in text for hint in NOISY_SUPPORT_HINTS)


def _same_topic_as_metadata(metadata: dict[str, Any], result: Any) -> bool:
    base = " ".join(
        [
            _origin_title(metadata),
            compact_text(metadata.get("source")),
            compact_text(metadata.get("seed_type")),
        ]
    )
    base_terms = set(_keyword_terms(base)[:8])
    result_terms = set(_keyword_terms(f"{result.title} {result.snippet}")[:12])
    return len(base_terms & result_terms) >= 2


def _best_items(
    items: list[HiddenSupportResult],
    *,
    limit: int,
) -> list[HiddenSupportResult]:
    ranked = sorted(
        items,
        key=lambda item: (
            item.usefulness_score,
            item.query_type == "origin_title",
            item.query_type == "system_context",
            -item.rank,
        ),
        reverse=True,
    )
    return ranked[: max(0, limit)]


def _hidden_support_status(
    selected: list[HiddenSupportResult],
    rejected_low_relevance: int,
) -> str:
    if len(selected) >= 2:
        return "hidden_support_ready"
    if len(selected) == 1:
        return "one_hidden_support_link"
    if rejected_low_relevance:
        return "needs_better_query"
    return "no_hidden_support_found"


def _result_payload(item: HiddenSupportResult) -> dict[str, Any]:
    return {
        "title": item.title,
        "url": item.url,
        "source": item.source,
        "snippet": item.snippet,
        "query": item.query,
        "query_type": item.query_type,
        "category": item.category,
        "rank": item.rank,
        "matched_terms": item.matched_terms,
        "usefulness_score": item.usefulness_score,
        "usefulness_reason": item.usefulness_reason,
    }


def _table_cell(value: object) -> str:
    return compact_text(value).replace("|", "\\|") or "-"


def _split_csv(value: str, default: list[str]) -> list[str]:
    items = [item.strip() for item in str(value or "").split(",") if item.strip()]
    return items or list(default)


@app.command("main")
def main(
    date: Annotated[str, typer.Option("--date", help="Jibi run date YYYY-MM-DD.")] = "",
    metadata: Annotated[
        Path | None,
        typer.Option("--metadata", help="Bundle review board metadata JSON."),
    ] = None,
    provider_name: Annotated[
        str,
        typer.Option("--provider", help="Search provider: naver."),
    ] = "naver",
    categories_csv: Annotated[
        str,
        typer.Option("--categories", help="Comma-separated provider categories."),
    ] = "news,webkr",
    max_links_per_row: Annotated[
        int,
        typer.Option("--max-links-per-row", help="Hidden links to keep per row."),
    ] = 3,
    results_per_query: Annotated[
        int,
        typer.Option("--results-per-query", help="Max search results per query."),
    ] = 5,
    max_calls: Annotated[
        int,
        typer.Option("--max-calls", help="Max provider calls in this run."),
    ] = 60,
    markdown: Annotated[
        Path | None,
        typer.Option("--markdown", help="Output markdown path."),
    ] = None,
    output_json: Annotated[
        Path | None,
        typer.Option("--json", help="Output JSON path."),
    ] = None,
    env_file: Annotated[
        Path | None,
        typer.Option("--env-file", help="Optional KEY=VALUE env file for provider credentials."),
    ] = DEFAULT_ENV_FILE,
) -> None:
    if provider_name != "naver":
        raise ValueError(f"Unsupported hidden support provider: {provider_name}")
    run_date = date or datetime.now().strftime("%Y-%m-%d")
    provider = provider_from_env(env_file)
    md_path, json_path, payload = write_hidden_support_search(
        run_date=run_date,
        metadata_path=metadata or default_metadata_path(run_date),
        provider=provider,
        markdown_path=markdown or default_markdown_path(run_date),
        json_path=output_json or default_json_path(run_date),
        categories=_split_csv(categories_csv, DEFAULT_CATEGORIES),
        max_links_per_row=max_links_per_row,
        results_per_query=results_per_query,
        max_provider_calls=max_calls,
    )
    console.print(
        "[green]Wrote Jibi hidden support search "
        f"({payload['selected_links_total']} selected links): {md_path} / {json_path}[/green]"
    )


if __name__ == "__main__":
    typer.run(main)
