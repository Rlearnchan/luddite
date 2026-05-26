"""External second-search adapter for Jibi review follow-up."""

from __future__ import annotations

import hashlib
import html
import json
import os
import re
import urllib.parse
import urllib.request
from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Any, Protocol
from urllib.parse import urlparse

import typer
from rich.console import Console

from luddite import paths
from luddite.utils.jsonl import write_jsonl
from luddite.utils.urls import canonicalize_url

app = typer.Typer(no_args_is_help=False)
console = Console()

DEFAULT_PRIORITY_FILTER = ["high"]
DEFAULT_CATEGORIES = ["news"]
DEFAULT_ENV_FILE = Path(".env.local")
RELEVANCE_STOPWORDS = {
    "2026",
    "case",
    "news",
    "latest",
    "recent",
    "한국",
    "국내",
    "통계",
    "사례",
    "최신",
    "뉴스",
    "최근",
    "정책",
    "발표",
    "영향",
    "반론",
    "리스크",
    "논란",
    "자료",
    "구조",
}
NAVER_ENDPOINTS = {
    "news": "https://openapi.naver.com/v1/search/news.json",
    "webkr": "https://openapi.naver.com/v1/search/webkr.json",
}


@dataclass(frozen=True)
class SearchResult:
    title: str
    url: str
    snippet: str = ""
    source: str = ""
    published_at: str = ""
    provider: str = ""
    category: str = ""
    rank: int = 0
    raw: dict[str, Any] | None = None


class SearchProvider(Protocol):
    name: str

    def search(
        self,
        query: str,
        *,
        category: str,
        max_results: int,
    ) -> list[SearchResult]:
        ...


def compact_text(value: object) -> str:
    return " ".join(str(value or "").split())


def _default_plan_path(run_date: str) -> Path:
    return paths.REPORTS_DIR / f"jibi_second_search_plan_{run_date}.json"


def _default_inbox_path(run_date: str) -> Path:
    return paths.ARTICLE_INBOX_DIR / f"second_search_{run_date}.jsonl"


def _default_markdown_path(run_date: str) -> Path:
    return paths.REPORTS_DIR / f"jibi_second_search_web_{run_date}.md"


def _default_json_path(run_date: str) -> Path:
    return paths.REPORTS_DIR / f"jibi_second_search_web_{run_date}.json"


def _strip_html(value: object) -> str:
    text = re.sub(r"<[^>]+>", " ", str(value or ""))
    return compact_text(html.unescape(text))


def _domain(value: str) -> str:
    parsed = urlparse(value)
    return parsed.netloc.lower().removeprefix("www.") or "unknown"


def _result_url(item: dict[str, Any]) -> str:
    return compact_text(item.get("originallink") or item.get("link") or item.get("url"))


def load_env_file(path: Path | None = DEFAULT_ENV_FILE) -> list[str]:
    """Load KEY=VALUE pairs without overriding already exported env vars."""
    if path is None or not path.exists():
        return []
    loaded = []
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip("\"'")
        if not key or key in os.environ:
            continue
        os.environ[key] = value
        loaded.append(key)
    return loaded


class MockSearchProvider:
    name = "mock"

    def search(
        self,
        query: str,
        *,
        category: str,
        max_results: int,
    ) -> list[SearchResult]:
        return []


class NaverSearchProvider:
    name = "naver"

    def __init__(
        self,
        *,
        client_id: str,
        client_secret: str,
        sort: str = "date",
        timeout: float = 10.0,
        http_get_json: Callable[[str, dict[str, str], float], dict[str, Any]] | None = None,
    ) -> None:
        if not client_id or not client_secret:
            raise ValueError(
                "Naver Search credentials are missing. Set "
                "NAVER_SEARCH_CLIENT_ID/NAVER_SEARCH_CLIENT_SECRET "
                "or NAVER_CLIENT_ID/NAVER_CLIENT_SECRET."
            )
        self.client_id = client_id
        self.client_secret = client_secret
        self.sort = sort
        self.timeout = timeout
        self._http_get_json = http_get_json or self._urllib_get_json

    @classmethod
    def from_env(cls) -> NaverSearchProvider:
        return cls(
            client_id=os.environ.get("NAVER_SEARCH_CLIENT_ID")
            or os.environ.get("NAVER_CLIENT_ID", ""),
            client_secret=os.environ.get("NAVER_SEARCH_CLIENT_SECRET")
            or os.environ.get("NAVER_CLIENT_SECRET", ""),
        )

    @staticmethod
    def _urllib_get_json(
        url: str,
        headers: dict[str, str],
        timeout: float,
    ) -> dict[str, Any]:
        request = urllib.request.Request(url, headers=headers, method="GET")
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))

    def search(
        self,
        query: str,
        *,
        category: str,
        max_results: int,
    ) -> list[SearchResult]:
        endpoint = NAVER_ENDPOINTS.get(category)
        if not endpoint:
            raise ValueError(f"Unsupported Naver search category: {category}")
        display = max(1, min(int(max_results), 100))
        params = {
            "query": query,
            "display": str(display),
            "start": "1",
            "sort": self.sort,
        }
        url = endpoint + "?" + urllib.parse.urlencode(params)
        headers = {
            "X-Naver-Client-Id": self.client_id,
            "X-Naver-Client-Secret": self.client_secret,
        }
        payload = self._http_get_json(url, headers, self.timeout)
        results = []
        for index, item in enumerate(payload.get("items", []), start=1):
            result_url = _result_url(item)
            if not result_url:
                continue
            results.append(
                SearchResult(
                    title=_strip_html(item.get("title")),
                    url=result_url,
                    snippet=_strip_html(item.get("description")),
                    source=_domain(result_url),
                    published_at=compact_text(item.get("pubDate")),
                    provider=self.name,
                    category=category,
                    rank=index,
                    raw=item,
                )
            )
        return results


def _provider_from_name(name: str) -> SearchProvider:
    normalized = name.strip().lower()
    if normalized == "mock":
        return MockSearchProvider()
    if normalized == "naver":
        return NaverSearchProvider.from_env()
    raise ValueError(f"Unsupported second-search provider: {name}")


def _load_plan(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _split_csv(value: str, default: list[str]) -> list[str]:
    items = [item.strip() for item in str(value or "").split(",") if item.strip()]
    return items or list(default)


def _query_specs_for_plan(plan: dict[str, Any], limit: int) -> list[dict[str, str]]:
    queries: list[dict[str, str]] = []
    for task in plan.get("query_plan", []):
        action = str(task.get("action") or "")
        if action == "demote_to_evidence_or_background":
            continue
        query_type = compact_text(task.get("query_type")) or "fallback"
        for query in task.get("queries", []) or []:
            query_text = compact_text(query)
            if query_text:
                queries.append({"query": query_text, "query_type": query_type})
    if not queries:
        topic_terms = [
            compact_text(item)
            for item in plan.get("topic_terms", [])
            if compact_text(item)
        ]
        if topic_terms:
            queries.append(
                {
                    "query": " ".join(topic_terms[:3]),
                    "query_type": "fallback",
                }
            )
    deduped: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for item in queries:
        key = (item["query"], item["query_type"])
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    selected: list[dict[str, str]] = []
    for query_type in ["precision", "broader_system", "fallback"]:
        for item in deduped:
            if item["query_type"] != query_type or item in selected:
                continue
            selected.append(item)
            break
    for item in deduped:
        if item not in selected:
            selected.append(item)
    return selected[:limit]


def _queries_for_plan(plan: dict[str, Any], limit: int) -> list[str]:
    return [item["query"] for item in _query_specs_for_plan(plan, limit)]


def _amount_variants(term: str) -> list[str]:
    variants = [term]
    normalized = term.replace(",", "")
    if normalized != term:
        variants.append(normalized)
    match = re.fullmatch(r"(\d+)천(\d+)(억(?:원)?)", normalized)
    if match:
        value = int(match.group(1)) * 1000 + int(match.group(2))
        variants.append(f"{value}{match.group(3)}")
    reverse = re.fullmatch(r"(\d{4,})(억(?:원)?)", normalized)
    if reverse:
        digits = reverse.group(1)
        variants.append(f"{digits[:-3]}천{int(digits[-3:])}{reverse.group(2)}")
    return list(dict.fromkeys(variants))


def _term_variants(term: str) -> list[str]:
    text = compact_text(term).strip("\"'‘’“”.,:;()[]{}")
    if not text:
        return []
    variants = [text, re.sub(r"\s+", "", text)]
    if text == "스벅":
        variants.append("스타벅스")
    if text == "스타벅스":
        variants.append("스벅")
    variants.extend(_amount_variants(text))
    return list(dict.fromkeys(item for item in variants if item))


def _query_relevance_terms(query: str) -> list[str]:
    tokens = [
        token.strip("\"'‘’“”.,:;()[]{}")
        for token in re.split(r"\s+", compact_text(query))
    ]
    terms = []
    for token in tokens:
        if not token or token.lower() in RELEVANCE_STOPWORDS or token in RELEVANCE_STOPWORDS:
            continue
        if len(token) < 2 and not re.search(r"\d", token):
            continue
        terms.append(token)
    return list(dict.fromkeys(terms))


def _match_relevance_terms(result: SearchResult, query: str) -> list[str]:
    title = compact_text(result.title)
    body = compact_text(f"{result.title} {result.snippet} {result.source}")
    title_norm = re.sub(r"\s+", "", title.lower())
    body_norm = re.sub(r"\s+", "", body.lower())
    matched = []
    for term in _query_relevance_terms(query):
        for variant in _term_variants(term):
            variant_norm = re.sub(r"\s+", "", variant.lower())
            if not variant_norm:
                continue
            if variant_norm in title_norm or variant_norm in body_norm:
                matched.append(term)
                break
    return list(dict.fromkeys(matched))


def _result_is_relevant(result: SearchResult, query: str) -> tuple[bool, list[str]]:
    terms = _query_relevance_terms(query)
    if not terms:
        return True, []
    matched = _match_relevance_terms(result, query)
    required = 1 if len(terms) <= 1 else 2
    if len(matched) >= required:
        return True, matched
    return False, matched


def _result_id(url: str, query: str) -> str:
    digest = hashlib.sha1(f"{canonicalize_url(url)}|{query}".encode()).hexdigest()[:12]
    return f"article_second_search_{digest}"


def _article_record(
    *,
    result: SearchResult,
    query: str,
    query_type: str,
    plan: dict[str, Any],
    collected_at: str,
) -> dict[str, Any]:
    url = result.url
    article_id = _result_id(url, query)
    return {
        "article_id": article_id,
        "collected_at": collected_at,
        "collector": "second_search_web",
        "duplicate_key": article_id.removeprefix("article_"),
        "evidence_role": "supporting_link_candidate",
        "language": "ko" if result.category in {"news", "webkr"} else None,
        "published_at": result.published_at,
        "raw_summary": result.snippet,
        "region": "kr" if result.provider == "naver" else "global",
        "source": result.source or result.provider,
        "source_count": 1,
        "source_id": f"{result.provider}_{result.category}",
        "source_sections": [result.category],
        "source_url_canonical": canonicalize_url(url) or url,
        "supporting_source_ids": [],
        "tags": [
            "second_search",
            f"provider:{result.provider}",
            f"category:{result.category}",
            f"priority:{plan.get('priority', '')}",
        ],
        "title": result.title,
        "url": url,
        "search_query": query,
        "query_type": query_type,
        "matched_terms": result.raw.get("_jibi_relevance_terms", [])
        if isinstance(result.raw, dict)
        else [],
        "relevance_status": "accepted",
        "search_relevance_terms": result.raw.get("_jibi_relevance_terms", [])
        if isinstance(result.raw, dict)
        else [],
        "search_provider": result.provider,
        "search_category": result.category,
        "search_rank": result.rank,
        "review_item_id": plan.get("id", ""),
        "review_title": plan.get("title", ""),
        "review_actions": plan.get("actions", []),
    }


def run_web_second_search(
    *,
    run_date: str,
    plan_payload: dict[str, Any],
    provider: SearchProvider,
    categories: list[str] | None = None,
    priority_filter: list[str] | None = None,
    queries_per_plan: int = 2,
    results_per_query: int = 5,
    max_queries: int = 10,
) -> dict[str, Any]:
    categories = categories or DEFAULT_CATEGORIES
    priority_filter = priority_filter or DEFAULT_PRIORITY_FILTER
    collected_at = datetime.now(UTC).isoformat()
    records: list[dict[str, Any]] = []
    query_runs: list[dict[str, Any]] = []
    seen_urls: set[str] = set()
    calls_used = 0
    rejected_low_relevance = 0
    for plan in plan_payload.get("plans", []):
        if priority_filter and str(plan.get("priority") or "") not in priority_filter:
            continue
        excluded = {
            canonicalize_url(str(plan.get("main_link") or "")),
            *[canonicalize_url(str(item)) for item in plan.get("sub_links", []) or []],
        }
        excluded = {url for url in excluded if url}
        for query_spec in _query_specs_for_plan(plan, queries_per_plan):
            query = query_spec["query"]
            query_type = query_spec["query_type"]
            for category in categories:
                if calls_used >= max_queries:
                    break
                results = provider.search(
                    query,
                    category=category,
                    max_results=results_per_query,
                )
                calls_used += 1
                accepted = 0
                rejected_for_relevance = 0
                for result in results:
                    canonical = canonicalize_url(result.url) or result.url
                    if not canonical or canonical in excluded or canonical in seen_urls:
                        continue
                    relevant, matched_terms = _result_is_relevant(result, query)
                    if not relevant:
                        rejected_for_relevance += 1
                        rejected_low_relevance += 1
                        continue
                    seen_urls.add(canonical)
                    raw = dict(result.raw or {})
                    raw["_jibi_relevance_terms"] = matched_terms
                    enriched_result = SearchResult(
                        title=result.title,
                        url=result.url,
                        snippet=result.snippet,
                        source=result.source,
                        published_at=result.published_at,
                        provider=result.provider,
                        category=result.category,
                        rank=result.rank,
                        raw=raw,
                    )
                    records.append(
                        _article_record(
                            result=enriched_result,
                            query=query,
                            query_type=query_type,
                            plan=plan,
                            collected_at=collected_at,
                        )
                    )
                    accepted += 1
                query_runs.append(
                    {
                        "review_item_id": plan.get("id", ""),
                        "review_title": plan.get("title", ""),
                        "priority": plan.get("priority", ""),
                        "query": query,
                        "query_type": query_type,
                        "provider": provider.name,
                        "category": category,
                        "returned": len(results),
                        "accepted": accepted,
                        "rejected_low_relevance": rejected_for_relevance,
                    }
                )
            if calls_used >= max_queries:
                break
        if calls_used >= max_queries:
            break
    return {
        "run_date": run_date,
        "generated_at": collected_at,
        "provider": provider.name,
        "categories": categories,
        "priority_filter": priority_filter,
        "queries_per_plan": queries_per_plan,
        "results_per_query": results_per_query,
        "max_queries": max_queries,
        "calls_used": calls_used,
        "rejected_low_relevance": rejected_low_relevance,
        "records_written": len(records),
        "records": records,
        "query_runs": query_runs,
        "accepted_by_review_item": dict(
            Counter(str(record.get("review_item_id") or "") for record in records)
        ),
    }


def _table_cell(value: object) -> str:
    return compact_text(value).replace("|", "\\|") or "-"


def render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        f"# Jibi Web Second-Search — {payload['run_date']}",
        "",
        f"- Generated at: `{payload['generated_at']}`",
        f"- Provider: `{payload['provider']}`",
        f"- Categories: `{', '.join(payload['categories'])}`",
        f"- Priority filter: `{', '.join(payload['priority_filter'])}`",
        f"- Calls used: {payload['calls_used']}/{payload['max_queries']}",
        f"- Records written: {payload['records_written']}",
        f"- Rejected low relevance: {payload.get('rejected_low_relevance', 0)}",
        "",
        "## Query Runs",
        "",
        "| priority | title | query_type | query | category | returned | accepted | rejected |",
        "| --- | --- | --- | --- | --- | ---: | ---: | ---: |",
    ]
    for run in payload["query_runs"]:
        lines.append(
            "| "
            + " | ".join(
                [
                    _table_cell(run["priority"]),
                    _table_cell(run["review_title"]),
                    _table_cell(run.get("query_type", "fallback")),
                    _table_cell(run["query"]),
                    _table_cell(run["category"]),
                    str(run["returned"]),
                    str(run["accepted"]),
                    str(run.get("rejected_low_relevance", 0)),
                ]
            )
            + " |"
        )
    lines.extend(["", "## Accepted Results", ""])
    if not payload["records"]:
        lines.append("- none")
    for record in payload["records"]:
        lines.append(
            f"- {record['source']} / {record['search_category']}: "
            f"[{record['title']}]({record['url']})"
        )
        lines.append(f"  - query: `{record['search_query']}`")
        lines.append(f"  - query_type: `{record.get('query_type', 'fallback')}`")
        if record.get("search_relevance_terms"):
            lines.append(
                f"  - matched_terms: `{', '.join(record['search_relevance_terms'])}`"
            )
        if record.get("published_at"):
            lines.append(f"  - published_at: `{record['published_at']}`")
        if record.get("raw_summary"):
            lines.append(f"  - summary: {record['raw_summary']}")
    return "\n".join(lines).rstrip() + "\n"


def write_web_second_search_outputs(
    *,
    run_date: str,
    plan_path: Path,
    provider: SearchProvider,
    inbox_path: Path,
    markdown_path: Path,
    json_path: Path,
    categories: list[str],
    priority_filter: list[str],
    queries_per_plan: int,
    results_per_query: int,
    max_queries: int,
) -> tuple[Path, Path, Path, dict[str, Any]]:
    plan_payload = _load_plan(plan_path)
    payload = run_web_second_search(
        run_date=run_date,
        plan_payload=plan_payload,
        provider=provider,
        categories=categories,
        priority_filter=priority_filter,
        queries_per_plan=queries_per_plan,
        results_per_query=results_per_query,
        max_queries=max_queries,
    )
    payload["plan_path"] = str(plan_path)
    payload["inbox_path"] = str(inbox_path)
    write_jsonl(inbox_path, payload["records"])
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.write_text(render_markdown(payload), encoding="utf-8")
    json_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return inbox_path, markdown_path, json_path, payload


@app.command("main")
def main(
    date: Annotated[str, typer.Option("--date", help="Jibi run date YYYY-MM-DD.")] = "",
    plan: Annotated[
        Path | None,
        typer.Option("--plan", help="Second-search plan JSON."),
    ] = None,
    provider_name: Annotated[
        str,
        typer.Option("--provider", help="Search provider: mock or naver."),
    ] = "naver",
    categories_csv: Annotated[
        str,
        typer.Option("--categories", help="Comma-separated provider categories."),
    ] = "news",
    priorities_csv: Annotated[
        str,
        typer.Option("--priorities", help="Comma-separated priority filter."),
    ] = "high",
    queries_per_plan: Annotated[
        int,
        typer.Option("--queries-per-plan", help="Max queries per review item."),
    ] = 2,
    results_per_query: Annotated[
        int,
        typer.Option("--results-per-query", help="Max search results per query."),
    ] = 5,
    max_queries: Annotated[
        int,
        typer.Option("--max-queries", help="Max provider calls in this run."),
    ] = 10,
    inbox: Annotated[
        Path | None,
        typer.Option("--inbox", help="Output article JSONL path."),
    ] = None,
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
    run_date = date or datetime.now().strftime("%Y-%m-%d")
    load_env_file(env_file)
    provider = _provider_from_name(provider_name)
    inbox_path, md_path, json_path, payload = write_web_second_search_outputs(
        run_date=run_date,
        plan_path=plan or _default_plan_path(run_date),
        provider=provider,
        inbox_path=inbox or _default_inbox_path(run_date),
        markdown_path=markdown or _default_markdown_path(run_date),
        json_path=output_json or _default_json_path(run_date),
        categories=_split_csv(categories_csv, DEFAULT_CATEGORIES),
        priority_filter=_split_csv(priorities_csv, DEFAULT_PRIORITY_FILTER),
        queries_per_plan=queries_per_plan,
        results_per_query=results_per_query,
        max_queries=max_queries,
    )
    console.print(
        "[green]Wrote Jibi web second-search results "
        f"({payload['records_written']} records): "
        f"{inbox_path} / {md_path} / {json_path}[/green]"
    )


if __name__ == "__main__":
    typer.run(main)
