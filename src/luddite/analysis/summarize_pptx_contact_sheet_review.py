"""Summarize human review notes from PPTX contact sheet QA reports."""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console

from luddite import paths
from luddite.analysis.render_pptx_contact_sheet import DEFAULT_OUTPUT_DIR

app = typer.Typer(no_args_is_help=False)
console = Console()

DEFAULT_INPUT_DIR = DEFAULT_OUTPUT_DIR
DEFAULT_REVIEW_SUMMARY_PATH = DEFAULT_OUTPUT_DIR / "pptx_contact_sheet_review_summary.md"
DEFAULT_REVIEW_PACK_PATH = DEFAULT_OUTPUT_DIR / "pptx_contact_sheet_review_pack.md"
DEFAULT_DOCS_REVIEW_SUMMARY_PATH = (
    paths.DOCS_DIR / "reviews" / "pptx_contact_sheet_review_summary.md"
)

STATUS_VALUES = {"unchecked", "ok", "review", "fail"}
STATUS_ORDER = ["unchecked", "ok", "review", "fail"]
DIMENSION_FIELDS = [
    "readability_status",
    "layout_status",
    "broadcast_fit_status",
    "style_fit_status",
]
NOTE_FIELDS = [
    "readability_note",
    "layout_note",
    "broadcast_note",
    "style_note",
    "fix_request",
]

ISSUE_CATEGORY_OWNERS = {
    "copy_too_long": "Anny slide spec / screen copy",
    "layout_cluttered": "Piti layout",
    "diagram_too_generic": "Anny diagram generation",
    "chart_table_overloaded": "Piti chart/table template or Anny proof_object",
    "source_card_weak": "Anny source metadata / evidence title",
    "speaker_beat_unclear": "Anny storyline",
    "style_not_syukaworld": "style profile / Piti rendering",
    "needs_manual_asset": "human editor",
    "other": "manual review",
}

ISSUE_KEYWORDS = {
    "copy_too_long": [
        "too much text",
        "too long",
        "trim",
        "copy",
        "body",
        "paragraph",
        "글자",
        "본문",
        "문장",
        "줄이",
        "축약",
    ],
    "layout_cluttered": [
        "layout",
        "clutter",
        "overlap",
        "spacing",
        "align",
        "레이아웃",
        "겹",
        "복잡",
        "정렬",
        "여백",
    ],
    "diagram_too_generic": [
        "diagram",
        "generic",
        "node",
        "actor",
        "mechanism",
        "result",
        "다이어그램",
        "노드",
        "추상",
        "구체",
        "행위자",
        "메커니즘",
    ],
    "chart_table_overloaded": [
        "chart",
        "table",
        "axis",
        "data",
        "number",
        "차트",
        "표",
        "데이터",
        "수치",
        "축",
    ],
    "source_card_weak": [
        "source",
        "card",
        "title",
        "url",
        "reference",
        "출처",
        "소스",
        "제목",
        "기관",
    ],
    "speaker_beat_unclear": [
        "beat",
        "speaker",
        "talk",
        "narrative",
        "spoken",
        "말문",
        "발표",
        "비트",
        "흐름",
    ],
    "style_not_syukaworld": [
        "style",
        "template",
        "syuka",
        "shuka",
        "슈카",
        "그림 반",
        "말 반",
        "스타일",
        "템플릿",
    ],
    "needs_manual_asset": [
        "asset",
        "image",
        "screenshot",
        "manual",
        "insert",
        "editor",
        "이미지",
        "스크린샷",
        "삽입",
        "수동",
        "에셋",
    ],
}


@dataclass(frozen=True)
class ContactSheetReviewSlide:
    deck_id: str
    slide_no: int
    thumbnail: str
    screen_headline: str
    visual_qa_flags: str
    contact_sheet_review_status: str
    readability_status: str
    layout_status: str
    broadcast_fit_status: str
    style_fit_status: str
    readability_note: str
    layout_note: str
    broadcast_note: str
    style_note: str
    fix_request: str

    @property
    def note_text(self) -> str:
        return " ".join(
            value for value in [str(getattr(self, field)) for field in NOTE_FIELDS]
            if value
        )

    @property
    def dimension_statuses(self) -> list[str]:
        return [
            self.readability_status,
            self.layout_status,
            self.broadcast_fit_status,
            self.style_fit_status,
        ]

    @property
    def should_enter_review_pack(self) -> bool:
        return (
            self.contact_sheet_review_status in {"review", "fail"}
            or any(status in {"review", "fail"} for status in self.dimension_statuses)
            or bool(self.fix_request)
        )


@dataclass(frozen=True)
class ContactSheetReviewSummary:
    generated_at: str
    input_dir: Path
    report_paths: list[Path]
    slides: list[ContactSheetReviewSlide]
    summary_path: Path
    review_pack_path: Path


def _display_path(path: Path | None) -> str:
    if path is None:
        return "-"
    try:
        return str(path.resolve().relative_to(paths.REPO_ROOT))
    except ValueError:
        return str(path)


def _normalize_status(value: str) -> str:
    normalized = value.strip().lower().replace(" ", "_")
    if not normalized:
        return "unchecked"
    if normalized in STATUS_VALUES:
        return normalized
    return "review"


def _split_markdown_row(line: str) -> list[str]:
    stripped = line.strip()
    if stripped.startswith("|"):
        stripped = stripped[1:]
    if stripped.endswith("|"):
        stripped = stripped[:-1]
    cells: list[str] = []
    current = ""
    escaped = False
    for character in stripped:
        if escaped:
            current += character
            escaped = False
        elif character == "\\":
            escaped = True
        elif character == "|":
            cells.append(current.strip())
            current = ""
        else:
            current += character
    cells.append(current.strip())
    return cells


def _is_separator_row(cells: list[str]) -> bool:
    return all(cell.replace(":", "").replace("-", "").strip() == "" for cell in cells)


def _extract_deck_id(lines: list[str], path: Path) -> str:
    for line in lines:
        prefix = "# PPTX Contact Sheet QA:"
        if line.startswith(prefix):
            return line.removeprefix(prefix).strip()
    return path.name.removesuffix("_contact_sheet.md")


def _parse_slide_no(value: str) -> int:
    stripped = value.strip()
    return int(stripped) if stripped.isdigit() else 0


def _row_value(row: dict[str, str], key: str) -> str:
    return row.get(key, "").strip()


def parse_contact_sheet_report(path: Path) -> list[ContactSheetReviewSlide]:
    lines = path.read_text(encoding="utf-8").splitlines()
    deck_id = _extract_deck_id(lines, path)
    header: list[str] | None = None
    slides: list[ContactSheetReviewSlide] = []
    for index, line in enumerate(lines):
        if line.startswith("| slide_no |"):
            header = _split_markdown_row(line)
            data_start = index + 2
            break
    else:
        return []

    if header is None:
        return []
    for line in lines[data_start:]:
        if not line.startswith("|"):
            break
        cells = _split_markdown_row(line)
        if _is_separator_row(cells):
            continue
        row = dict(zip(header, cells, strict=False))
        slides.append(
            ContactSheetReviewSlide(
                deck_id=deck_id,
                slide_no=_parse_slide_no(_row_value(row, "slide_no")),
                thumbnail=_row_value(row, "thumbnail"),
                screen_headline=_row_value(row, "screen_headline"),
                visual_qa_flags=_row_value(row, "visual QA flags"),
                contact_sheet_review_status=_normalize_status(
                    _row_value(row, "contact_sheet_review_status")
                ),
                readability_status=_normalize_status(
                    _row_value(row, "readability_status")
                ),
                layout_status=_normalize_status(_row_value(row, "layout_status")),
                broadcast_fit_status=_normalize_status(
                    _row_value(row, "broadcast_fit_status")
                ),
                style_fit_status=_normalize_status(_row_value(row, "style_fit_status")),
                readability_note=_row_value(row, "readability_note"),
                layout_note=_row_value(row, "layout_note"),
                broadcast_note=_row_value(row, "broadcast_note"),
                style_note=_row_value(row, "style_note"),
                fix_request=_row_value(row, "fix_request"),
            )
        )
    return slides


def _classify_issue(text: str) -> str | None:
    if not text.strip():
        return None
    lowered = text.lower()
    for category, keywords in ISSUE_KEYWORDS.items():
        if any(keyword.lower() in lowered for keyword in keywords):
            return category
    return "other"


def _status_counts(slides: list[ContactSheetReviewSlide]) -> Counter[str]:
    counter: Counter[str] = Counter({status: 0 for status in STATUS_ORDER})
    counter.update(slide.contact_sheet_review_status for slide in slides)
    return counter


def _dimension_counts(
    slides: list[ContactSheetReviewSlide],
) -> dict[str, Counter[str]]:
    counts: dict[str, Counter[str]] = {
        field: Counter({status: 0 for status in STATUS_ORDER})
        for field in DIMENSION_FIELDS
    }
    for slide in slides:
        counts["readability_status"].update([slide.readability_status])
        counts["layout_status"].update([slide.layout_status])
        counts["broadcast_fit_status"].update([slide.broadcast_fit_status])
        counts["style_fit_status"].update([slide.style_fit_status])
    return counts


def _review_started(slides: list[ContactSheetReviewSlide]) -> bool:
    return any(
        slide.contact_sheet_review_status != "unchecked"
        or any(status != "unchecked" for status in slide.dimension_statuses)
        or bool(slide.note_text)
        for slide in slides
    )


def _slides_by_deck(
    slides: list[ContactSheetReviewSlide],
) -> dict[str, list[ContactSheetReviewSlide]]:
    grouped: dict[str, list[ContactSheetReviewSlide]] = defaultdict(list)
    for slide in slides:
        grouped[slide.deck_id].append(slide)
    return dict(grouped)


def _category_counts(slides: list[ContactSheetReviewSlide]) -> Counter[str]:
    counter: Counter[str] = Counter()
    for slide in slides:
        category = _classify_issue(slide.note_text)
        if category:
            counter.update([category])
    return counter


def _owner_counts(slides: list[ContactSheetReviewSlide]) -> Counter[str]:
    counter: Counter[str] = Counter()
    for slide in slides:
        category = _classify_issue(slide.note_text)
        if category:
            counter.update([ISSUE_CATEGORY_OWNERS[category]])
    return counter


def _markdown_escape(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ").strip()


def _write_summary(summary: ContactSheetReviewSummary, output_path: Path) -> None:
    slides = summary.slides
    status_counts = _status_counts(slides)
    dimension_counts = _dimension_counts(slides)
    category_counts = _category_counts(slides)
    owner_counts = _owner_counts(slides)
    fix_request_count = sum(1 for slide in slides if slide.fix_request)
    review_started = _review_started(slides)
    deck_groups = _slides_by_deck(slides)

    lines = [
        "# PPTX Contact Sheet Human Review Summary",
        "",
        f"- generated_at: {summary.generated_at}",
        f"- input_dir: {_display_path(summary.input_dir)}",
        f"- report_count: {len(summary.report_paths)}",
        f"- total_slides: {len(slides)}",
        f"- unchecked_slides: {status_counts['unchecked']}",
        f"- ok_slides: {status_counts['ok']}",
        f"- review_slides: {status_counts['review']}",
        f"- fail_slides: {status_counts['fail']}",
        f"- fix_request_count: {fix_request_count}",
        (
            "- manual_review_status: "
            f"{'in_progress' if review_started else 'manual review not started'}"
        ),
        "- This report summarizes human-entered contact sheet review notes only.",
        "- No PPT content was modified.",
        "- No LLM/API calls.",
        "- Production readiness remains false.",
        "- Broadcast readiness remains false.",
        "",
        "## Dimension Status Counts",
        "",
        "| dimension | unchecked | ok | review | fail |",
        "|---|---:|---:|---:|---:|",
    ]
    for field in DIMENSION_FIELDS:
        counts = dimension_counts[field]
        lines.append(
            "| {field} | {unchecked} | {ok} | {review} | {fail} |".format(
                field=field,
                unchecked=counts["unchecked"],
                ok=counts["ok"],
                review=counts["review"],
                fail=counts["fail"],
            )
        )

    lines.extend(
        [
            "",
            "## Deck Status Counts",
            "",
            "| deck | total | unchecked | ok | review | fail | fix_requests |",
            "|---|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for deck_id, deck_slides in sorted(deck_groups.items()):
        deck_counts = _status_counts(deck_slides)
        deck_fix_count = sum(1 for slide in deck_slides if slide.fix_request)
        lines.append(
            "| {deck} | {total} | {unchecked} | {ok} | {review} | {fail} | "
            "{fix_requests} |".format(
                deck=_markdown_escape(deck_id),
                total=len(deck_slides),
                unchecked=deck_counts["unchecked"],
                ok=deck_counts["ok"],
                review=deck_counts["review"],
                fail=deck_counts["fail"],
                fix_requests=deck_fix_count,
            )
        )

    lines.extend(["", "## Issue Category Counts", ""])
    if category_counts:
        lines.extend(["| issue_category | count | suggested_owner |", "|---|---:|---|"])
        for category, count in sorted(category_counts.items()):
            lines.append(
                f"| {category} | {count} | {ISSUE_CATEGORY_OWNERS[category]} |"
            )
    else:
        lines.append("- No human note/fix_request issues have been classified yet.")

    lines.extend(["", "## Suggested Owner Counts", ""])
    if owner_counts:
        lines.extend(["| suggested_owner | count |", "|---|---:|"])
        for owner, count in sorted(owner_counts.items()):
            lines.append(f"| {_markdown_escape(owner)} | {count} |")
    else:
        lines.append("- No suggested owners yet.")

    if not review_started:
        lines.extend(
            [
                "",
                "## Manual Review Not Started",
                "",
                (
                    "- All slides are still `unchecked`, and no human notes or "
                    "`fix_request` values were found."
                ),
            ]
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_review_pack(summary: ContactSheetReviewSummary, output_path: Path) -> None:
    review_slides = [slide for slide in summary.slides if slide.should_enter_review_pack]
    lines = [
        "# PPTX Contact Sheet Review Pack",
        "",
        f"- generated_at: {summary.generated_at}",
        f"- review_or_fail_slides: {len(review_slides)}",
        "- This pack lists human-marked review/fail slides and fix requests only.",
        "- No PPT content was modified.",
        "- No LLM/API calls.",
        "",
    ]
    if not review_slides:
        lines.extend(
            [
                "## No Review/Fail Slides Yet",
                "",
                "- Manual contact sheet review has not marked any slide for review/fail.",
            ]
        )
    else:
        lines.extend(
            [
                "## Slides",
                "",
                (
                    "| deck_id | slide_no | thumbnail | screen_headline | statuses | "
                    "notes | fix_request | issue_category | suggested_owner |"
                ),
                "|---|---:|---|---|---|---|---|---|---|",
            ]
        )
        for slide in review_slides:
            category = _classify_issue(slide.note_text) or "-"
            owner = ISSUE_CATEGORY_OWNERS.get(category, "-")
            statuses = ", ".join(
                [
                    f"contact={slide.contact_sheet_review_status}",
                    f"readability={slide.readability_status}",
                    f"layout={slide.layout_status}",
                    f"broadcast={slide.broadcast_fit_status}",
                    f"style={slide.style_fit_status}",
                ]
            )
            lines.append(
                f"| {_markdown_escape(slide.deck_id)} | {slide.slide_no} | "
                f"{_markdown_escape(slide.thumbnail)} | "
                f"{_markdown_escape(slide.screen_headline)} | "
                f"{_markdown_escape(statuses)} | {_markdown_escape(slide.note_text)} | "
                f"{_markdown_escape(slide.fix_request)} | {category} | "
                f"{_markdown_escape(owner)} |"
            )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def summarize_contact_sheet_review(
    *,
    input_dir: Path = DEFAULT_INPUT_DIR,
    summary_output_path: Path = DEFAULT_REVIEW_SUMMARY_PATH,
    review_pack_output_path: Path = DEFAULT_REVIEW_PACK_PATH,
    docs_summary_output_path: Path | None = DEFAULT_DOCS_REVIEW_SUMMARY_PATH,
) -> ContactSheetReviewSummary:
    report_paths = sorted(input_dir.glob("*_contact_sheet.md"))
    slides = [
        slide for report_path in report_paths for slide in parse_contact_sheet_report(report_path)
    ]
    summary = ContactSheetReviewSummary(
        generated_at=datetime.now(UTC).isoformat(),
        input_dir=input_dir,
        report_paths=report_paths,
        slides=slides,
        summary_path=summary_output_path,
        review_pack_path=review_pack_output_path,
    )
    _write_summary(summary, summary_output_path)
    _write_review_pack(summary, review_pack_output_path)
    if docs_summary_output_path is not None:
        _write_summary(summary, docs_summary_output_path)
    return summary


@app.callback(invoke_without_command=True)
def main(
    input_dir: Annotated[
        Path,
        typer.Option("--input-dir", help="Directory containing *_contact_sheet.md files."),
    ] = DEFAULT_INPUT_DIR,
    summary_output_path: Annotated[
        Path,
        typer.Option("--summary-output", help="Markdown review summary output path."),
    ] = DEFAULT_REVIEW_SUMMARY_PATH,
    review_pack_output_path: Annotated[
        Path,
        typer.Option("--review-pack-output", help="Markdown review/fail slide pack path."),
    ] = DEFAULT_REVIEW_PACK_PATH,
    docs_summary_output_path: Annotated[
        Path | None,
        typer.Option("--docs-summary-output", help="GitHub-visible review summary mirror."),
    ] = DEFAULT_DOCS_REVIEW_SUMMARY_PATH,
) -> None:
    """Summarize human contact sheet review statuses and notes."""
    summary = summarize_contact_sheet_review(
        input_dir=input_dir,
        summary_output_path=summary_output_path,
        review_pack_output_path=review_pack_output_path,
        docs_summary_output_path=docs_summary_output_path,
    )
    console.print(
        "[green]Wrote PPTX contact sheet human review summary for "
        f"{len(summary.slides)} slide(s) to {summary_output_path}.[/green]"
    )


if __name__ == "__main__":
    app()
