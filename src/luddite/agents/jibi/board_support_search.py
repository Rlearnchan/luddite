"""Naver-backed supporting link search for the visible Jibi review board."""

from __future__ import annotations

import csv
import json
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from luddite import paths
from luddite.agents.jibi.append_to_sheet import BUNDLE_REVIEW_SHEET_COLUMNS
from luddite.agents.jibi.second_search_web import (
    DEFAULT_ENV_FILE,
    NaverSearchProvider,
    SearchProvider,
    _result_is_relevant,
    load_env_file,
)
from luddite.utils.urls import canonicalize_url

BOARD_SUPPORT_STOPWORDS = {
    "ai",
    "AI",
    "jibi",
    "seed",
    "follow",
    "up",
    "자료",
    "기사",
    "후보",
    "단순",
    "추가",
    "근거",
    "설명",
    "보면",
    "있습니다",
    "좋습니다",
    "합니다",
    "됩니다",
    "보입니다",
    "문제",
    "이야기",
    "한국",
    "뉴스",
    "정책",
    "자료가",
}
TRUSTED_SUPPORT_DOMAINS = {
    "bok.or.kr",
    "korea.kr",
    "kdi.re.kr",
    "yna.co.kr",
    "newsis.com",
    "news1.kr",
    "kbs.co.kr",
    "ytn.co.kr",
    "hani.co.kr",
    "khan.co.kr",
    "donga.com",
    "joongang.co.kr",
    "chosun.com",
    "mk.co.kr",
    "hankyung.com",
    "sedaily.com",
    "edaily.co.kr",
    "etnews.com",
    "zdnet.co.kr",
    "seoul.co.kr",
}
NOISY_SUPPORT_HINTS = {
    "스포츠",
    "연예",
    "맛집",
    "여행",
    "쿠폰",
    "특가",
    "이벤트",
    "경품",
    "운세",
}


@dataclass(frozen=True)
class SupportSearchResult:
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


def default_markdown_path(run_date: str) -> Path:
    return paths.REPORTS_DIR / f"jibi_board_support_search_{run_date}.md"


def default_json_path(run_date: str) -> Path:
    return paths.REPORTS_DIR / f"jibi_board_support_search_{run_date}.json"


def provider_from_env(env_file: Path | None = DEFAULT_ENV_FILE) -> NaverSearchProvider:
    load_env_file(env_file)
    return NaverSearchProvider.from_env()


def enrich_review_board_support_links(
    *,
    run_date: str,
    board_csv_path: Path,
    metadata_path: Path,
    provider: SearchProvider,
    markdown_path: Path | None = None,
    json_path: Path | None = None,
    categories: list[str] | None = None,
    max_links_per_row: int = 1,
    results_per_query: int = 5,
    max_provider_calls: int = 60,
) -> dict[str, Any]:
    categories = categories or ["news", "webkr"]
    rows = _read_board_rows(board_csv_path)
    metadata_payload = _read_metadata(metadata_path)
    metadata_index = _metadata_index(metadata_payload)
    generated_at = datetime.now(UTC).isoformat()
    calls_used = 0
    seen_global: set[str] = set()
    report_rows: list[dict[str, Any]] = []

    for row in rows:
        row_id = str(row.get("ID") or "").strip()
        metadata = metadata_index.get(row_id, {})
        main_link = str(row.get("메인 링크") or metadata.get("main_link") or "")
        excluded = {
            canonicalize_url(main_link),
        }
        excluded = {item for item in excluded if item}
        accepted: list[SupportSearchResult] = []
        rejected_low_relevance = 0
        query_runs: list[dict[str, Any]] = []

        for query_spec in _queries_for_row(row, metadata):
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
                    if not canonical or canonical in excluded or canonical in seen_global:
                        continue
                    relevant, matched_terms = _result_is_relevant(result, query)
                    if not relevant:
                        rejected_low_relevance += 1
                        rejected_count += 1
                        continue
                    score, reason = _support_result_usefulness(
                        row=row,
                        metadata=metadata,
                        result=result,
                        query=query,
                        query_type=query_type,
                        matched_terms=matched_terms,
                    )
                    if score < 8:
                        rejected_low_relevance += 1
                        rejected_count += 1
                        continue
                    seen_global.add(canonical)
                    accepted.append(
                        SupportSearchResult(
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
            if calls_used >= max_provider_calls:
                break

        selected_items = _best_support_items(accepted, limit=max_links_per_row)
        selected_links = [item.url for item in selected_items]
        row["서브 링크"] = _format_sub_links(selected_links)
        if selected_items:
            row["설명"] = _append_support_reason(row.get("설명"), selected_items[0])
        report_row = {
            "review_item_id": row_id,
            "title": str(row.get("제목") or ""),
            "main_link": main_link,
            "queries": query_runs,
            "accepted_count": len(accepted),
            "rejected_low_relevance": rejected_low_relevance,
            "selected_links": selected_links,
            "selected_link_details": [
                {
                    "title": item.title,
                    "url": item.url,
                    "source": item.source,
                    "score": item.usefulness_score,
                    "reason": item.usefulness_reason,
                    "query": item.query,
                    "query_type": item.query_type,
                    "matched_terms": item.matched_terms,
                }
                for item in selected_items
            ],
            "accepted_links": [
                {
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
                for item in accepted
            ],
        }
        report_rows.append(report_row)
        metadata_row = metadata_index.get(row_id)
        if metadata_row is not None:
            metadata_row["sub_links"] = selected_links
            metadata_row["board_support_search"] = report_row
        if calls_used >= max_provider_calls:
            break

    _write_board_rows(board_csv_path, rows)
    _write_metadata(metadata_path, metadata_payload)
    payload = {
        "run_date": run_date,
        "generated_at": generated_at,
        "provider": provider.name,
        "categories": categories,
        "max_links_per_row": max_links_per_row,
        "results_per_query": results_per_query,
        "max_provider_calls": max_provider_calls,
        "calls_used": calls_used,
        "rows": report_rows,
        "rows_with_support_links": sum(1 for row in report_rows if row["selected_links"]),
        "accepted_links_total": sum(len(row["accepted_links"]) for row in report_rows),
        "selected_links_total": sum(len(row["selected_links"]) for row in report_rows),
    }
    md_path = markdown_path or default_markdown_path(run_date)
    json_report_path = json_path or default_json_path(run_date)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    json_report_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text(render_markdown(payload), encoding="utf-8")
    json_report_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    payload["markdown_path"] = str(md_path)
    payload["json_path"] = str(json_report_path)
    return payload


def _read_board_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as source:
        return list(csv.DictReader(source))


def _write_board_rows(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=BUNDLE_REVIEW_SHEET_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def _read_metadata(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"rows": []}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"rows": []}


def _write_metadata(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _metadata_index(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    index = {}
    for row in payload.get("rows", []):
        if not isinstance(row, dict):
            continue
        for key in [
            str(row.get("ID") or ""),
            str(row.get("review_item_id") or ""),
            str(row.get("story_bundle_id") or ""),
            str(row.get("story_fingerprint") or ""),
        ]:
            if key:
                index.setdefault(key, row)
    return index


def _split_sub_links(value: object) -> list[str]:
    raw = str(value or "")
    if not raw.strip():
        return []
    links = []
    for chunk in re.split(r"\s*\|\s*|\n+", raw):
        cleaned = re.sub(r"^\s*(?:[-*•]|\d+[.)])\s*", "", chunk).strip()
        if cleaned:
            links.append(cleaned)
    return _dedupe_links(links)


def _format_sub_links(links: list[str]) -> str:
    return "\n".join(f"{index}. {link}" for index, link in enumerate(links, start=1))


def _best_support_items(
    items: list[SupportSearchResult],
    *,
    limit: int,
) -> list[SupportSearchResult]:
    ranked = sorted(
        items,
        key=lambda item: (
            item.usefulness_score,
            -item.rank,
            item.query_type == "supporting_context",
        ),
        reverse=True,
    )
    return ranked[: max(0, limit)]


def _append_support_reason(description: object, item: SupportSearchResult) -> str:
    base = _compact(description)
    source = _compact(item.source)
    source_text = f"{source}의 " if source else ""
    sentence = (
        f"서브 링크는 {source_text}보강 자료 1개만 남겼습니다. "
        f"{item.usefulness_reason}"
    )
    if sentence in base:
        return base
    return f"{base} {sentence}".strip()


def _dedupe_links(links: list[str]) -> list[str]:
    seen = set()
    output = []
    for link in links:
        canonical = canonicalize_url(link) or link
        if canonical in seen:
            continue
        seen.add(canonical)
        output.append(link)
    return output


def _support_result_usefulness(
    *,
    row: dict[str, str],
    metadata: dict[str, Any],
    result: Any,
    query: str,
    query_type: str,
    matched_terms: list[str],
) -> tuple[int, str]:
    del metadata
    score = 0
    reasons = []
    title = _compact(result.title)
    body = _compact(f"{result.title} {result.snippet}")
    title_matches = _matched_in_text(matched_terms, title)
    body_matches = _matched_in_text(matched_terms, body)
    domain = _domain(result.url)
    if len(matched_terms) >= 3:
        score += 4
        reasons.append("핵심어가 여러 개 겹칩니다")
    elif len(matched_terms) >= 2:
        score += 2
        reasons.append("검색어와 직접 관련이 있습니다")
    if title_matches:
        score += min(4, len(title_matches) * 2)
        reasons.append("제목에서 주제어가 확인됩니다")
    elif len(body_matches) >= 3:
        score += 2
        reasons.append("요약에서 보강 맥락이 확인됩니다")
    if domain in TRUSTED_SUPPORT_DOMAINS or domain.endswith(".go.kr"):
        score += 4
        reasons.append("출처 신뢰도가 비교적 높습니다")
    elif _is_major_domain_family(domain):
        score += 2
        reasons.append("대중 매체 보강 자료로 볼 수 있습니다")
    if query_type == "supporting_context":
        score += 2
        reasons.append("메인 링크의 배경을 넓혀줍니다")
    year = _result_year(result)
    current_year = datetime.now(UTC).year
    if year >= current_year - 1:
        score += 3
        reasons.append("최근 자료입니다")
    elif year and year < current_year - 3:
        score -= 6
    if int(getattr(result, "rank", 0) or 0) <= 2:
        score += 1
    if _has_noisy_hint(title) or _has_noisy_hint(str(getattr(result, "snippet", ""))):
        score -= 5
    if _same_topic_as_row(row, result):
        score += 2
    if not reasons:
        reasons.append("보강 자료 후보입니다")
    return score, "선택 이유: " + ", ".join(dict.fromkeys(reasons)) + "."


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
    return any(
        domain == item or domain.endswith(f".{item}")
        for item in TRUSTED_SUPPORT_DOMAINS
    )


def _has_noisy_hint(text: str) -> bool:
    return any(hint in text for hint in NOISY_SUPPORT_HINTS)


def _same_topic_as_row(row: dict[str, str], result: Any) -> bool:
    row_terms = set(_keyword_terms(f"{row.get('제목', '')} {row.get('설명', '')}")[:8])
    result_terms = set(_keyword_terms(f"{result.title} {result.snippet}")[:12])
    return len(row_terms & result_terms) >= 2


def _result_year(result: Any) -> int:
    published_at = _compact(getattr(result, "published_at", ""))
    match = re.search(r"\b(20\d{2})\b", published_at)
    if match:
        return int(match.group(1))
    url = _compact(getattr(result, "url", ""))
    match = re.search(r"(20\d{2})", url)
    if match:
        return int(match.group(1))
    return 0


def _queries_for_row(row: dict[str, str], metadata: dict[str, Any]) -> list[dict[str, str]]:
    title = _compact(row.get("제목"))
    description = _compact(row.get("설명"))
    auto_title = _compact(metadata.get("auto_title"))
    source = _compact(metadata.get("source"))
    seed_type = _compact(metadata.get("seed_type"))
    precision_title = auto_title if auto_title and auto_title != title else title
    precision = _compact_query(" ".join(part for part in [precision_title, source] if part))
    terms = _keyword_terms(" ".join([title, description, seed_type]))
    broader = _compact_query(" ".join([*terms[:6], "통계", "사례"]))
    queries = []
    for query_type, query in [
        *_topic_query_specs(title, description, auto_title),
        ("source_title", precision),
        ("seed_precision", precision),
        ("supporting_context", broader),
    ]:
        if query and query not in {item["query"] for item in queries}:
            queries.append({"query_type": query_type, "query": query})
    return queries


def _topic_query_specs(
    title: str,
    description: str,
    auto_title: str,
) -> list[tuple[str, str]]:
    text = f"{title} {description} {auto_title}"
    specs: list[tuple[str, str]] = []
    if "금융시장" in text or "생산적 금융" in text or "자금 흐름" in text:
        specs.append(("supporting_context", "생산적 금융 기업 투자 성장률 자금 흐름"))
    if "AI 인재" in text or "전문인력" in text:
        specs.append(("supporting_context", "AI 인재 부족 임금 이동성 수급 불균형"))
    if "실질임금" in text or "월급" in text:
        specs.append(("supporting_context", "실질임금 물가 임금 상승 생활수준"))
    if "우주산업" in text or "우주보험" in text:
        specs.append(("supporting_context", "우주보험 발사 실패 위성 보험 한국"))
    if "청년 일자리" in text or "청년고용" in text:
        specs.append(("supporting_context", "AI 청년고용 일자리 자동화 노동시장"))
    if "비아파트" in text or "오피스텔" in text or "전세사기" in text:
        specs.append(("supporting_context", "비아파트 공급 전세사기 오피스텔 빌라 주택시장"))
    if "스타벅스" in text or "스벅" in text:
        specs.append(("supporting_context", "스타벅스 선불충전금 환불 AI 문구 책임"))
    if "페라리" in text or "슈퍼카" in text:
        specs.append(("supporting_context", "페라리 전기차 가격 전동화 슈퍼카 시장"))
    heat_safety_terms = ("열사병", "산업현장", "작업중지권", "노동안전")
    if ("폭염" in text and any(term in text for term in heat_safety_terms)) or "열사병" in text:
        specs.append(("supporting_context", "폭염 산업현장 열사병 대책 노동 안전 작업중지권"))
    elif "폭염" in text or "반바지" in text:
        specs.append(("supporting_context", "폭염 직장 복장 규정 반바지 쿨비즈"))
    if "교육 프로그램" in text or "아카데미" in text:
        specs.append(("supporting_context", "청년 교육 프로그램 취업 연계 K뉴딜 아카데미"))
    return specs


def _keyword_terms(text: str) -> list[str]:
    terms = []
    for token in re.findall(r"[가-힣A-Za-z0-9][가-힣A-Za-z0-9·+.-]{1,}", text):
        token = token.strip(".-")
        if not token or token in BOARD_SUPPORT_STOPWORDS:
            continue
        if token.lower() in BOARD_SUPPORT_STOPWORDS:
            continue
        if len(token) < 2 and not re.search(r"\d", token):
            continue
        terms.append(token)
    return list(dict.fromkeys(terms))


def _compact(value: object) -> str:
    return " ".join(str(value or "").split())


def _compact_query(value: str, *, max_chars: int = 80) -> str:
    text = _compact(re.sub(r"[\"'“”‘’?:,]", " ", value))
    if len(text) <= max_chars:
        return text
    parts = text.split()
    output = []
    total = 0
    for part in parts:
        if total + len(part) + (1 if output else 0) > max_chars:
            break
        output.append(part)
        total += len(part) + (1 if output else 0)
    return " ".join(output)


def render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        f"# Jibi Board Support Search — {payload['run_date']}",
        "",
        f"- Generated at: `{payload['generated_at']}`",
        f"- Provider: `{payload['provider']}`",
        f"- Categories: `{', '.join(payload['categories'])}`",
        f"- Calls used: {payload['calls_used']}/{payload['max_provider_calls']}",
        f"- Rows with support links: {payload['rows_with_support_links']}",
        f"- Selected links total: {payload['selected_links_total']}",
        "",
        "## Rows",
        "",
    ]
    for row in payload.get("rows", []):
        lines.extend(
            [
                f"### {row['title']}",
                "",
                f"- review_item_id: `{row['review_item_id']}`",
                f"- accepted_count: {row['accepted_count']}",
                f"- rejected_low_relevance: {row['rejected_low_relevance']}",
                "- selected_links:",
            ]
        )
        if row.get("selected_links"):
            lines.extend(f"  - {link}" for link in row["selected_links"])
        else:
            lines.append("  - none")
        lines.append("- queries:")
        for query in row.get("queries", []):
            lines.append(
                "  - "
                f"{query['query_type']} / {query['category']}: "
                f"`{query['query']}` "
                f"(returned={query['returned']}, accepted={query['accepted']}, "
                f"rejected_low_relevance={query['rejected_low_relevance']})"
            )
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"
