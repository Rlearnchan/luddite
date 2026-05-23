#!/usr/bin/env python3
"""Audit syuka-ops DB for policy/official-source usage signals."""

from __future__ import annotations

import argparse
import sqlite3
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from statistics import median

DEFAULT_DB_PATH = Path("/Users/bae/Documents/code/syuka-gpt/syuka-ops/data/db/syuka_ops.db")

TERMS = [
    "보도자료",
    "정책브리핑",
    "금융위원회",
    "금융감독원",
    "기획재정부",
    "한국은행",
    "통계청",
    "국토교통부",
    "산업통상자원부",
    "중소벤처기업부",
    "농림축산식품부",
    "해양수산부",
    "환경부",
    "고용노동부",
    "교육부",
    "과학기술정보통신부",
    "질병관리청",
    "공정거래위원회",
    "방위사업청",
    "개인정보보호위원회",
    "국민성장펀드",
    "염소",
]


@dataclass(frozen=True)
class Match:
    video_id: str
    title: str
    upload_date: str
    view_count: int
    source_url: str
    title_match: bool
    analysis_match: bool
    transcript_match: bool

    @property
    def transcript_only(self) -> bool:
        return self.transcript_match and not self.title_match and not self.analysis_match

    @property
    def analysis_or_title(self) -> bool:
        return self.title_match or self.analysis_match


def connect_readonly(path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def matches_for_term(conn: sqlite3.Connection, term: str) -> list[Match]:
    pattern = f"%{term}%"
    rows = conn.execute(
        """
        SELECT
            v.video_id,
            v.title,
            v.upload_date,
            COALESCE(v.view_count, 0) AS view_count,
            COALESCE(v.source_url, '') AS source_url,
            COALESCE(a.summary, '') AS summary,
            COALESCE(a.keywords_json, '') AS keywords_json,
            COALESCE(t.dialogue, '') AS dialogue
        FROM videos v
        LEFT JOIN video_analysis a ON a.video_id = v.video_id
        LEFT JOIN transcripts t ON t.video_id = v.video_id
        WHERE
            COALESCE(v.title, '') LIKE ?
            OR COALESCE(a.summary, '') LIKE ?
            OR COALESCE(a.keywords_json, '') LIKE ?
            OR COALESCE(t.dialogue, '') LIKE ?
        """,
        (pattern, pattern, pattern, pattern),
    ).fetchall()
    return [
        Match(
            video_id=str(row["video_id"]),
            title=str(row["title"] or ""),
            upload_date=str(row["upload_date"] or ""),
            view_count=int(row["view_count"] or 0),
            source_url=str(row["source_url"] or ""),
            title_match=term in str(row["title"] or ""),
            analysis_match=term in f"{row['summary'] or ''} {row['keywords_json'] or ''}",
            transcript_match=term in str(row["dialogue"] or ""),
        )
        for row in rows
    ]


def table_cell(value: object) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ").strip()


def sample_list(matches: list[Match], *, limit: int = 3) -> str:
    if not matches:
        return "-"
    parts = [
        f"{match.upload_date} {match.title} ({match.view_count:,})"
        for match in matches[:limit]
    ]
    return "<br>".join(table_cell(part) for part in parts)


def render_report(conn: sqlite3.Connection) -> str:
    lines = [
        "# Jibi Policy Source Audit from syuka-ops",
        "",
        "Read-only scan of syuka-ops video metadata, analysis, and transcripts.",
        "",
        "## Term Summary",
        "",
        "| term | total videos | title/analysis matches | transcript-only | "
        "max views | median views | recent samples |",
        "| --- | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    detailed_sections: list[str] = []
    for term in TERMS:
        matches = matches_for_term(conn, term)
        title_or_analysis = [match for match in matches if match.analysis_or_title]
        transcript_only = [match for match in matches if match.transcript_only]
        view_counts = [match.view_count for match in matches if match.view_count]
        recent = sorted(matches, key=lambda item: item.upload_date, reverse=True)
        lines.append(
            "| "
            f"{table_cell(term)} | "
            f"{len(matches)} | "
            f"{len(title_or_analysis)} | "
            f"{len(transcript_only)} | "
            f"{max(view_counts) if view_counts else 0:,} | "
            f"{int(median(view_counts)) if view_counts else 0:,} | "
            f"{sample_list(recent)} |"
        )
        detailed_sections.extend(term_detail(term, matches, title_or_analysis, transcript_only))
    lines.extend(["", "## Interpretation Notes", ""])
    lines.extend(
        [
            "- `title/analysis matches` are more likely to indicate seed-level usage "
            "or a named topic.",
            "- `transcript-only` matches are more likely to indicate evidence/source "
            "citation usage.",
            "- High-count official sources should not automatically pass Jibi gates; "
            "they need role-specific filters.",
            "- Low-count unusual terms can still matter when the story itself is strange "
            "enough to become a seed.",
        ]
    )
    lines.extend(["", "## Term Details", ""])
    lines.extend(detailed_sections)
    return "\n".join(lines) + "\n"


def term_detail(
    term: str,
    matches: list[Match],
    title_or_analysis: list[Match],
    transcript_only: list[Match],
) -> list[str]:
    top_viewed = sorted(matches, key=lambda item: item.view_count, reverse=True)
    recent_seedish = sorted(title_or_analysis, key=lambda item: item.upload_date, reverse=True)
    recent_evidence = sorted(transcript_only, key=lambda item: item.upload_date, reverse=True)
    return [
        f"### {term}",
        "",
        f"- total videos: {len(matches)}",
        f"- title/analysis matches: {len(title_or_analysis)}",
        f"- transcript-only matches: {len(transcript_only)}",
        f"- top viewed: {sample_list(top_viewed, limit=5)}",
        f"- recent title/analysis samples: {sample_list(recent_seedish, limit=5)}",
        f"- recent transcript-only samples: {sample_list(recent_evidence, limit=5)}",
        "",
    ]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db-path", type=Path, default=DEFAULT_DB_PATH)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(f"/tmp/jibi_syuka_policy_source_audit_{date.today().isoformat()}.md"),
    )
    args = parser.parse_args()

    if not args.db_path.exists():
        raise SystemExit(f"syuka-ops DB not found: {args.db_path}")

    conn = connect_readonly(args.db_path)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(render_report(conn), encoding="utf-8")
    print(args.output)


if __name__ == "__main__":
    main()
