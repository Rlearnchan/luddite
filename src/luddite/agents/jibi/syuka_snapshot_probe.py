"""Read-only local syuka snapshot similarity probe for Jibi bridge queries."""

from __future__ import annotations

import json
import re
import sqlite3
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Annotated, Any

import typer
from rich.console import Console

from luddite import paths

app = typer.Typer(no_args_is_help=False)
console = Console()

DEFAULT_SYUKA_DATA_DIR = Path("/Users/bae/Documents/code/syuka-ops/data")
DEFAULT_MATCH_LIMIT = 5
TEXT_COLUMN_HINTS = {
    "title",
    "summary",
    "keywords",
    "keywords_json",
    "dialogue",
    "transcript",
    "caption",
    "content",
    "text",
    "description",
}
ENGLISH_STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "for",
    "from",
    "if",
    "in",
    "is",
    "it",
    "of",
    "on",
    "or",
    "the",
    "to",
    "will",
    "with",
}
GENERIC_QUERY_TERMS = {
    "ai",
    "ai에",
    "000선",
    "1분기",
    "2배",
    "5대",
    "5년새",
    "65",
    "72",
    "83",
    "the",
    "world",
    "글로벌",
    "국민",
    "농림축산식품부",
    "농촌진흥청",
    "매출",
    "온라인으로",
    "인간과",
    "전기",
    "신청",
    "시대",
    "여름",
    "얻는",
    "이제",
    "지원",
    "주요",
    "케이",
    "최초",
    "사상",
    "돌파",
}
ALIAS_TERM_GROUPS = [
    {
        "쉬었음",
        "비경제활동",
        "경제활동참가율",
        "청년 노동시장",
    },
    {
        "반바지",
        "폭염",
        "쿨비즈",
        "회사 복장",
        "여름 근무",
    },
    {
        "선불충전금",
        "예치금",
        "충전금",
        "환불",
        "머지포인트",
    },
    {
        "자산 토큰화",
        "rwa",
        "sto",
        "조각투자",
        "cbdc",
    },
]


@dataclass(frozen=True)
class SnapshotDb:
    path: Path
    tables: dict[str, list[str]]
    status: str
    reason: str = ""


@dataclass(frozen=True)
class VideoDocument:
    video_id: str
    title: str
    url: str
    upload_date: str
    view_count: int | None
    like_count: int | None
    fields: dict[str, str]


def _default_queries_json(run_date: str) -> Path:
    return paths.REPORTS_DIR / f"jibi_syuka_bridge_queries_{run_date}.json"


def _default_output_md(run_date: str) -> Path:
    return paths.REPORTS_DIR / f"jibi_syuka_snapshot_matches_{run_date}.md"


def _default_output_json(run_date: str) -> Path:
    return paths.REPORTS_DIR / f"jibi_syuka_snapshot_matches_{run_date}.json"


def discover_sqlite_dbs(data_dir: Path) -> list[Path]:
    if not data_dir.exists():
        return []
    files: list[Path] = []
    for pattern in ("*.db", "*.sqlite", "*.sqlite3"):
        files.extend(data_dir.rglob(pattern))
    return sorted(
        {path for path in files if path.is_file()},
        key=lambda path: (
            0 if path.name == "syuka_ops.db" else 1,
            0 if path.stat().st_size > 0 else 1,
            str(path),
        ),
    )


def _connect_readonly(db_path: Path) -> sqlite3.Connection:
    uri = f"file:{db_path.resolve()}?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def _table_columns(conn: sqlite3.Connection, table: str) -> list[str]:
    return [str(row[1]) for row in conn.execute(f'PRAGMA table_info("{table}")')]


def _inspect_db(db_path: Path) -> SnapshotDb:
    if not db_path.exists():
        return SnapshotDb(path=db_path, tables={}, status="missing", reason="db_path_missing")
    if db_path.stat().st_size == 0:
        return SnapshotDb(path=db_path, tables={}, status="empty", reason="zero_byte_db")
    try:
        with _connect_readonly(db_path) as conn:
            table_names = [
                str(row[0])
                for row in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
                )
            ]
            tables = {name: _table_columns(conn, name) for name in table_names}
    except sqlite3.Error as exc:
        return SnapshotDb(
            path=db_path,
            tables={},
            status="unreadable",
            reason=f"sqlite_error:{exc}",
        )
    if not tables:
        return SnapshotDb(path=db_path, tables={}, status="empty", reason="no_tables")
    usable = (
        "videos" in tables
        or any(_text_columns(columns) for columns in tables.values())
    )
    return SnapshotDb(
        path=db_path,
        tables=tables,
        status="usable" if usable else "unsupported_schema",
        reason="" if usable else "no_searchable_text_columns",
    )


def choose_snapshot_db(data_dir: Path) -> SnapshotDb | None:
    inspected = [_inspect_db(path) for path in discover_sqlite_dbs(data_dir)]
    for db in inspected:
        if db.status == "usable":
            return db
    return inspected[0] if inspected else None


def _text_columns(columns: Iterable[str]) -> list[str]:
    output: list[str] = []
    for column in columns:
        normalized = column.lower()
        if any(hint in normalized for hint in TEXT_COLUMN_HINTS):
            output.append(column)
    return output


def _safe_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _row_value(row: sqlite3.Row, column: str) -> str:
    if column not in row.keys():
        return ""
    value = row[column]
    return "" if value is None else str(value)


def _load_documents_from_standard_schema(
    conn: sqlite3.Connection,
    tables: dict[str, list[str]],
) -> list[VideoDocument]:
    video_columns = tables.get("videos")
    if not video_columns or "video_id" not in video_columns:
        return []
    rows = conn.execute('SELECT * FROM "videos"').fetchall()
    docs: dict[str, VideoDocument] = {}
    for row in rows:
        video_id = _row_value(row, "video_id")
        if not video_id:
            continue
        docs[video_id] = VideoDocument(
            video_id=video_id,
            title=_row_value(row, "title"),
            url=_row_value(row, "source_url"),
            upload_date=_row_value(row, "upload_date"),
            view_count=_safe_int(row["view_count"]) if "view_count" in row.keys() else None,
            like_count=_safe_int(row["like_count"]) if "like_count" in row.keys() else None,
            fields={
                "title": _row_value(row, "title"),
                "metadata": " ".join(
                    _row_value(row, column)
                    for column in [
                        "channel_name",
                        "channel_key",
                        "upload_date",
                    ]
                    if column in row.keys()
                ),
            },
        )
    if "video_analysis" in tables and "video_id" in tables["video_analysis"]:
        for row in conn.execute('SELECT * FROM "video_analysis"'):
            video_id = _row_value(row, "video_id")
            if video_id not in docs:
                continue
            fields = dict(docs[video_id].fields)
            fields["analysis"] = " ".join(
                _row_value(row, column)
                for column in ["summary", "keywords_json"]
                if column in row.keys()
            )
            docs[video_id] = VideoDocument(
                video_id=docs[video_id].video_id,
                title=docs[video_id].title,
                url=docs[video_id].url,
                upload_date=docs[video_id].upload_date,
                view_count=docs[video_id].view_count,
                like_count=docs[video_id].like_count,
                fields=fields,
            )
    if "transcripts" in tables and "video_id" in tables["transcripts"]:
        for row in conn.execute('SELECT * FROM "transcripts"'):
            video_id = _row_value(row, "video_id")
            if video_id not in docs:
                continue
            fields = dict(docs[video_id].fields)
            fields["transcript"] = _row_value(row, "dialogue")
            docs[video_id] = VideoDocument(
                video_id=docs[video_id].video_id,
                title=docs[video_id].title,
                url=docs[video_id].url,
                upload_date=docs[video_id].upload_date,
                view_count=docs[video_id].view_count,
                like_count=docs[video_id].like_count,
                fields=fields,
            )
    return list(docs.values())


def _load_documents_from_generic_schema(
    conn: sqlite3.Connection,
    tables: dict[str, list[str]],
) -> list[VideoDocument]:
    docs: list[VideoDocument] = []
    for table, columns in tables.items():
        text_columns = _text_columns(columns)
        if not text_columns:
            continue
        id_column = "video_id" if "video_id" in columns else columns[0]
        title_column = "title" if "title" in columns else text_columns[0]
        for index, row in enumerate(conn.execute(f'SELECT * FROM "{table}"'), start=1):
            video_id = _row_value(row, id_column) or f"{table}:{index}"
            fields = {
                "title": _row_value(row, title_column),
                "analysis": " ".join(_row_value(row, column) for column in text_columns),
            }
            docs.append(
                VideoDocument(
                    video_id=video_id,
                    title=_row_value(row, title_column) or video_id,
                    url=_row_value(row, "source_url") if "source_url" in columns else "",
                    upload_date=_row_value(row, "upload_date") if "upload_date" in columns else "",
                    view_count=_safe_int(row["view_count"]) if "view_count" in columns else None,
                    like_count=_safe_int(row["like_count"]) if "like_count" in columns else None,
                    fields=fields,
                )
            )
    return docs


def load_snapshot_documents(db: SnapshotDb) -> list[VideoDocument]:
    if db.status != "usable":
        return []
    with _connect_readonly(db.path) as conn:
        docs = _load_documents_from_standard_schema(conn, db.tables)
        return docs or _load_documents_from_generic_schema(conn, db.tables)


def _normalize_term(term: Any) -> str:
    return re.sub(r"\s+", " ", str(term or "").strip().lower())


def _usable_query_terms(terms: Iterable[Any]) -> list[str]:
    output: list[str] = []
    for term in terms:
        normalized = _normalize_term(term)
        if not normalized:
            continue
        if normalized in ENGLISH_STOPWORDS or normalized in GENERIC_QUERY_TERMS:
            continue
        if normalized.isdigit():
            continue
        if re.fullmatch(r"[a-z]{1,2}", normalized) and normalized not in {"pf"}:
            continue
        if len(normalized) < 2:
            continue
        output.append(normalized)
    return list(dict.fromkeys(output))


def _expanded_alias_terms(terms: Iterable[Any]) -> list[str]:
    normalized_terms = [_normalize_term(term) for term in terms]
    output: list[str] = []
    for term in normalized_terms:
        if not term:
            continue
        output.append(term)
        for group in ALIAS_TERM_GROUPS:
            normalized_group = {_normalize_term(item) for item in group}
            if term in normalized_group:
                output.extend(sorted(normalized_group))
    return list(dict.fromkeys(output))


def _term_set_for_query(query: dict[str, Any]) -> dict[str, Any]:
    raw_core_terms = query.get("core_terms")
    raw_context_terms = query.get("context_terms")
    using_groups = raw_core_terms is not None or raw_context_terms is not None
    if using_groups:
        core_source = list(raw_core_terms or [])
        context_source = list(raw_context_terms or [])
    else:
        core_source = list(query.get("query_terms") or [])
        context_source = []

    expanded_core = _expanded_alias_terms(core_source)
    expanded_context = _expanded_alias_terms(context_source)
    effective_core = _usable_query_terms(expanded_core)
    effective_context = [
        term for term in _usable_query_terms(expanded_context) if term not in effective_core
    ]
    effective_terms = list(dict.fromkeys([*effective_core, *effective_context]))
    raw_terms = [
        _normalize_term(term)
        for term in [*core_source, *context_source]
        if _normalize_term(term)
    ]
    filtered_terms = [
        term
        for term in raw_terms
        if term not in effective_terms
        and term not in _usable_query_terms(_expanded_alias_terms([term]))
    ]
    return {
        "core_terms": effective_core,
        "context_terms": effective_context,
        "effective_query_terms": effective_terms,
        "filtered_query_terms": list(dict.fromkeys(filtered_terms)),
    }


def _contains_term(text: str, term: str) -> bool:
    if not term:
        return False
    normalized = text.lower()
    if re.fullmatch(r"[a-z0-9]+", term):
        return bool(re.search(rf"\b{re.escape(term)}\b", normalized))
    return term in normalized


def _snippet(text: str, terms: list[str], *, limit: int = 180) -> str:
    compact = re.sub(r"\s+", " ", text.strip())
    if not compact:
        return ""
    lower = compact.lower()
    positions = [lower.find(term) for term in terms if term and term in lower]
    start = max(0, min([pos for pos in positions if pos >= 0] or [0]) - 45)
    excerpt = compact[start : start + limit].strip()
    if start > 0:
        excerpt = "..." + excerpt
    if start + limit < len(compact):
        excerpt += "..."
    return excerpt


def _recommendation(
    *,
    match_score: int,
    matched_fields: list[str],
    matched_terms: list[str],
    matched_core_terms: list[str],
    matched_context_terms: list[str],
    negative_terms: list[str],
) -> str:
    if not matched_terms:
        return "safe_new_angle"
    if negative_terms:
        return "needs_human_check"
    if set(matched_fields) == {"transcript"}:
        return "needs_human_check"
    if not matched_core_terms:
        return "adjacent" if match_score >= 4 and matched_context_terms else "needs_human_check"
    if match_score >= 10 and ("title" in matched_fields or "analysis" in matched_fields):
        return "duplicate" if "title" in matched_fields else "adjacent"
    if match_score >= 4:
        return "adjacent"
    return "needs_human_check"


def _parse_upload_date(value: Any) -> date | None:
    text = str(value or "").strip()
    for fmt in ("%Y%m%d", "%Y-%m-%d"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def _past_video_response_signal(
    *,
    recommendation: str,
    match: dict[str, Any] | None,
    run_date: str,
) -> str:
    if not match:
        return "safe_new_angle"
    if recommendation == "needs_human_check":
        return "needs_human_check"
    view_count = match.get("view_count")
    upload_date = _parse_upload_date(match.get("upload_date"))
    run_dt = _parse_upload_date(run_date)
    days_old = (run_dt - upload_date).days if upload_date and run_dt else None
    if recommendation == "duplicate" and days_old is not None and days_old <= 90:
        return "duplicate_do_not_repeat"
    if (
        recommendation in {"duplicate", "adjacent"}
        and isinstance(view_count, int)
        and view_count >= 1_000_000
        and days_old is not None
        and days_old >= 180
    ):
        return "popular_topic_update_candidate"
    if recommendation in {"duplicate", "adjacent"} and isinstance(view_count, int):
        if view_count >= 1_000_000:
            return "audience_proven_topic"
    return recommendation


def _match_display_controls(
    recommendation: str,
    match: dict[str, Any] | None,
) -> dict[str, Any]:
    if not match or recommendation == "safe_new_angle":
        return {
            "match_confidence": "low",
            "match_reason": "no_local_match",
            "display_on_board": False,
        }
    fields = set(match.get("matched_fields") or [])
    score = int(match.get("match_score") or 0)
    core_terms = set(match.get("matched_core_terms") or [])
    context_terms = set(match.get("matched_context_terms") or [])
    if fields == {"transcript"}:
        return {
            "match_confidence": "low",
            "match_reason": "transcript_only",
            "display_on_board": False,
        }
    if "title" in fields and (core_terms or recommendation == "duplicate"):
        return {
            "match_confidence": "high" if recommendation == "duplicate" else "medium",
            "match_reason": "core_title_match",
            "display_on_board": recommendation in {"duplicate", "adjacent"},
        }
    if "analysis" in fields and (core_terms or recommendation in {"duplicate", "adjacent"}):
        confidence = "high" if recommendation == "duplicate" and score >= 10 else "medium"
        return {
            "match_confidence": confidence,
            "match_reason": "core_analysis_match",
            "display_on_board": recommendation in {"duplicate", "adjacent"},
        }
    if context_terms or fields:
        confidence = "medium" if score >= 4 and recommendation == "adjacent" else "low"
        return {
            "match_confidence": confidence,
            "match_reason": "context_only",
            "display_on_board": confidence == "medium" and recommendation == "adjacent",
        }
    return {
        "match_confidence": "low",
        "match_reason": "generic_filtered",
        "display_on_board": False,
    }


def match_query_to_documents(
    query: dict[str, Any],
    documents: list[VideoDocument],
    *,
    limit: int = DEFAULT_MATCH_LIMIT,
    run_date: str = "",
) -> dict[str, Any]:
    term_sets = _term_set_for_query(query)
    terms = term_sets["effective_query_terms"]
    core_terms = term_sets["core_terms"]
    context_terms = term_sets["context_terms"]
    negative_terms = [
        _normalize_term(term) for term in query.get("negative_terms", []) if _normalize_term(term)
    ]
    matches: list[dict[str, Any]] = []
    for doc in documents:
        field_hits: dict[str, set[str]] = {"title": set(), "analysis": set(), "transcript": set()}
        core_hits: dict[str, set[str]] = {"title": set(), "analysis": set(), "transcript": set()}
        context_hits: dict[str, set[str]] = {"title": set(), "analysis": set(), "transcript": set()}
        negative_hits: set[str] = set()
        for field, weight in [("title", 4), ("analysis", 2), ("transcript", 1)]:
            text = doc.fields.get(field, "")
            for term in core_terms:
                if _contains_term(text, term):
                    field_hits[field].add(term)
                    core_hits[field].add(term)
            for term in context_terms:
                if _contains_term(text, term):
                    field_hits[field].add(term)
                    context_hits[field].add(term)
            for term in negative_terms:
                if _contains_term(text, term):
                    negative_hits.add(term)
            del weight
        matched_fields = [field for field, hits in field_hits.items() if hits]
        matched_terms = sorted(set().union(*field_hits.values())) if matched_fields else []
        matched_core_terms = sorted(set().union(*core_hits.values())) if matched_fields else []
        matched_context_terms = (
            sorted(set().union(*context_hits.values())) if matched_fields else []
        )
        raw_score = (
            len(field_hits["title"]) * 4
            + len(field_hits["analysis"]) * 2
            + len(field_hits["transcript"])
        )
        match_score = max(0, raw_score - len(negative_hits) * 3)
        if not matched_terms:
            continue
        snippet_field = "title"
        if field_hits["analysis"]:
            snippet_field = "analysis"
        if not field_hits["title"] and field_hits["transcript"]:
            snippet_field = "transcript"
        recommendation = _recommendation(
            match_score=match_score,
            matched_fields=matched_fields,
            matched_terms=matched_terms,
            matched_core_terms=matched_core_terms,
            matched_context_terms=matched_context_terms,
            negative_terms=sorted(negative_hits),
        )
        matches.append(
            {
                "video_id": doc.video_id,
                "title": doc.title,
                "upload_date": doc.upload_date,
                "view_count": doc.view_count,
                "like_count": doc.like_count,
                "matched_fields": matched_fields,
                "matched_terms": matched_terms,
                "matched_core_terms": matched_core_terms,
                "matched_context_terms": matched_context_terms,
                "negative_terms_matched": sorted(negative_hits),
                "match_score": match_score,
                "recommendation": recommendation,
                "url": doc.url,
                "snippet": _snippet(doc.fields.get(snippet_field, ""), matched_terms),
            }
        )
    matches.sort(
        key=lambda item: (
            -int(item["match_score"]),
            str(item["recommendation"]),
            str(item["title"]),
        )
    )
    top_match = matches[0] if matches else None
    recommendation = top_match["recommendation"] if top_match else "safe_new_angle"
    display_controls = _match_display_controls(recommendation, top_match)
    return {
        "story_fingerprint": str(query.get("story_fingerprint") or ""),
        "query_title": str(query.get("title") or ""),
        "priority": str(query.get("priority") or "low"),
        "trigger": str(query.get("trigger") or ""),
        "query_terms": query.get("query_terms") or [],
        "core_terms": query.get("core_terms") or [],
        "context_terms": query.get("context_terms") or [],
        "effective_query_terms": terms,
        "effective_core_terms": core_terms,
        "effective_context_terms": context_terms,
        "filtered_query_terms": term_sets["filtered_query_terms"],
        "negative_terms": query.get("negative_terms") or [],
        "matches": matches[:limit],
        "recommendation": recommendation,
        "match_confidence": display_controls["match_confidence"],
        "match_reason": display_controls["match_reason"],
        "display_on_board": display_controls["display_on_board"],
        "past_video_response_signal": _past_video_response_signal(
            recommendation=recommendation,
            match=top_match,
            run_date=run_date,
        ),
    }


def _load_bridge_queries(path: Path) -> tuple[str, list[dict[str, Any]]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    run_date = str(payload.get("run_date") or "")
    queries = [item for item in payload.get("queries", []) if isinstance(item, dict)]
    return run_date, queries


def _schema_summary(db: SnapshotDb | None) -> dict[str, Any]:
    if db is None:
        return {"status": "no_db_found", "db_path": "", "tables": {}}
    return {
        "status": db.status,
        "reason": db.reason,
        "db_path": str(db.path),
        "tables": db.tables,
    }


def probe_syuka_snapshot(
    *,
    run_date: str,
    queries_json: Path,
    syuka_data_dir: Path,
    output_md: Path,
    output_json: Path,
    match_limit: int = DEFAULT_MATCH_LIMIT,
) -> tuple[Path, Path, dict[str, Any]]:
    output_md.parent.mkdir(parents=True, exist_ok=True)
    output_json.parent.mkdir(parents=True, exist_ok=True)
    db = choose_snapshot_db(syuka_data_dir)
    schema = _schema_summary(db)
    if not queries_json.exists():
        payload = {
            "run_date": run_date,
            "generated_at": datetime.now(UTC).isoformat(),
            "snapshot_status": schema,
            "queries_json": str(queries_json),
            "error": "queries_json_missing",
            "results": [],
        }
        _write_outputs(output_md, output_json, payload)
        return output_md, output_json, payload

    source_run_date, queries = _load_bridge_queries(queries_json)
    documents = load_snapshot_documents(db) if db and db.status == "usable" else []
    results = [
        match_query_to_documents(query, documents, limit=match_limit, run_date=run_date)
        for query in queries
    ]
    payload = {
        "run_date": run_date or source_run_date,
        "generated_at": datetime.now(UTC).isoformat(),
        "queries_json": str(queries_json),
        "syuka_data_dir": str(syuka_data_dir),
        "snapshot_status": schema,
        "document_count": len(documents),
        "query_count": len(queries),
        "results": results,
    }
    _write_outputs(output_md, output_json, payload)
    return output_md, output_json, payload


def _write_outputs(md_path: Path, json_path: Path, payload: dict[str, Any]) -> None:
    md_path.write_text(_markdown(payload), encoding="utf-8")
    json_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _recommendation_counts(results: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for result in results:
        key = str(result.get("recommendation") or "unknown")
        counts[key] = counts.get(key, 0) + 1
    return counts


def _table_cell(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).replace("|", "\\|").strip()


def _markdown(payload: dict[str, Any]) -> str:
    status = payload["snapshot_status"]
    results = payload.get("results", [])
    counts = _recommendation_counts(results)
    lines = [
        f"# Jibi Syuka Snapshot Matches — {payload['run_date']}",
        "",
        "Report-only local snapshot probe. No syuka-ops repo, Windows Docker, "
        "or syuka DB writes were performed.",
        "",
        "## Snapshot Status",
        "",
        f"- status: {status.get('status')}",
        f"- reason: {status.get('reason', '')}",
        f"- db_path: `{status.get('db_path', '')}`",
        f"- syuka_data_dir: `{payload.get('syuka_data_dir', '')}`",
        f"- document_count: {payload.get('document_count', 0)}",
        f"- query_count: {payload.get('query_count', 0)}",
        "",
        "## Query Summary",
        "",
        *[f"- {key}: {value}" for key, value in sorted(counts.items())],
        "",
        "## High-priority Past-overlap Checks",
        "",
        "| query | recommendation | top_match | score | matched_terms |",
        "| --- | --- | --- | ---: | --- |",
    ]
    high_rows = [item for item in results if item.get("priority") == "high"]
    for result in high_rows:
        top = (result.get("matches") or [{}])[0]
        lines.append(
            "| "
            + " | ".join(
                [
                    _table_cell(result.get("query_title")),
                    _table_cell(result.get("recommendation")),
                    _table_cell(top.get("title", "")),
                    str(top.get("match_score", 0)),
                    _table_cell(", ".join(top.get("matched_terms", []))),
                ]
            )
            + " |"
        )
    if not high_rows:
        lines.append("| none | safe_new_angle | none | 0 | none |")
    lines.extend(["", "## Matches By Query", ""])
    for result in results:
        lines.extend(
            [
                f"### {_table_cell(result.get('query_title')) or 'untitled'}",
                "",
                f"- story_fingerprint: `{result.get('story_fingerprint', '')}`",
                f"- priority: {result.get('priority', 'low')}",
                f"- trigger: {result.get('trigger', '')}",
                f"- recommendation: {result.get('recommendation', 'safe_new_angle')}",
                f"- past_video_response_signal: {result.get('past_video_response_signal', '')}",
                f"- effective_query_terms: {', '.join(result.get('effective_query_terms', []))}",
                f"- filtered_query_terms: {', '.join(result.get('filtered_query_terms', []))}",
                "",
                (
                    "| score | recommendation | fields | title | date | views | likes | "
                    "core_terms | context_terms | snippet |"
                ),
                "| ---: | --- | --- | --- | --- | ---: | ---: | --- | --- | --- |",
            ]
        )
        matches = result.get("matches") or []
        for match in matches:
            lines.append(
                "| "
                + " | ".join(
                    [
                        str(match.get("match_score", 0)),
                        _table_cell(match.get("recommendation")),
                        _table_cell(", ".join(match.get("matched_fields", []))),
                        _table_cell(match.get("title")),
                        _table_cell(match.get("upload_date")),
                        str(match.get("view_count") or ""),
                        str(match.get("like_count") or ""),
                        _table_cell(", ".join(match.get("matched_core_terms", []))),
                        _table_cell(", ".join(match.get("matched_context_terms", []))),
                        _table_cell(match.get("snippet")),
                    ]
                )
                + " |"
            )
        if not matches:
            lines.append(
                "| 0 | safe_new_angle | none | none |  |  |  | none | none | no local match |"
            )
        lines.append("")
    no_match = [item for item in results if not item.get("matches")]
    no_match_lines = [
        f"- {item.get('query_title')} (`{item.get('story_fingerprint')}`)"
        for item in no_match
    ] or ["- none"]
    lines.extend(
        [
            "## No-match Queries",
            "",
            *no_match_lines,
            "",
            "## Suggested Human Follow-up",
            "",
            "- Treat `duplicate` as likely past-topic overlap before promotion.",
            "- Treat `adjacent` as useful context; check whether the new angle is fresh.",
            "- Treat `needs_human_check` as weak or transcript-only similarity.",
            "- Treat `safe_new_angle` as no obvious local snapshot match, not proof of novelty.",
        ]
    )
    return "\n".join(lines) + "\n"


@app.callback(invoke_without_command=True)
def main(
    date: Annotated[str, typer.Option("--date", help="Jibi run date YYYY-MM-DD.")],
    queries_json: Annotated[
        Path | None,
        typer.Option("--queries-json", help="Jibi syuka bridge query JSON."),
    ] = None,
    syuka_data_dir: Annotated[
        Path,
        typer.Option("--syuka-data-dir", help="Local syuka-ops data directory."),
    ] = DEFAULT_SYUKA_DATA_DIR,
    output_md: Annotated[
        Path | None,
        typer.Option("--output-md", help="Markdown report output path."),
    ] = None,
    output_json: Annotated[
        Path | None,
        typer.Option("--output-json", help="JSON report output path."),
    ] = None,
    match_limit: Annotated[int, typer.Option("--match-limit", min=1)] = DEFAULT_MATCH_LIMIT,
) -> None:
    md_path, json_path, payload = probe_syuka_snapshot(
        run_date=date,
        queries_json=queries_json or _default_queries_json(date),
        syuka_data_dir=syuka_data_dir,
        output_md=output_md or _default_output_md(date),
        output_json=output_json or _default_output_json(date),
        match_limit=match_limit,
    )
    status = payload["snapshot_status"]["status"]
    console.print(
        "[green]Wrote Jibi syuka snapshot probe "
        f"(status={status}) to {md_path} and {json_path}.[/green]"
    )


if __name__ == "__main__":
    app()
