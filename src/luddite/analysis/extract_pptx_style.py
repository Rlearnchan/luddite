"""Extract approximate style profiles from existing PPTX decks.

This module reads PPTX XML directly for geometry, text style, image placement,
and speaker notes. Some PowerPoint values are inherited from theme/master
styles; when explicit run or paragraph properties are absent, the corresponding
record field is left null and ``inherited_style`` is marked true.
"""

from __future__ import annotations

import json
import re
import statistics
import zipfile
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Any
from xml.etree import ElementTree as ET

import typer
from rich.console import Console

from luddite import paths
from luddite.parsers.parse_pptx import _relationships
from luddite.utils.jsonl import write_jsonl
from luddite.utils.security import extract_source_notes, redact_sensitive_text
from luddite.utils.urls import extract_urls

app = typer.Typer(no_args_is_help=False)
console = Console()

EMU_PER_INCH = 914400
EMU_PER_CM = 360000

P_NS = "http://schemas.openxmlformats.org/presentationml/2006/main"
A_NS = "http://schemas.openxmlformats.org/drawingml/2006/main"
R_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
NS = {"p": P_NS, "a": A_NS, "r": R_NS}

DEFAULT_INPUT = paths.LATEST_PPT_RAW_DIR / "전당포 주식회사_배형찬.pptx"
DEFAULT_SAMPLES_JSONL = paths.STYLE_PROFILES_DIR / "syukaworld_ppt_shape_samples.jsonl"
DEFAULT_PROFILE_JSON = paths.STYLE_PROFILES_DIR / "syukaworld_ppt_style_profile.json"
DEFAULT_REPORT = paths.REPORTS_DIR / "piti_style_profile_report.md"

SLIDE_TYPE_GUESSES = {
    "title",
    "section_title",
    "big_headline",
    "headline_body",
    "quote",
    "question",
    "chart",
    "image_heavy",
    "checklist",
    "closing",
}


@dataclass(frozen=True)
class ExtractOutputs:
    samples_jsonl: Path
    profile_json: Path
    report_md: Path


def _load_xml(deck: zipfile.ZipFile, name: str) -> ET.Element:
    return ET.fromstring(deck.read(name).decode("utf-8", errors="ignore"))


def _read_zip_text(deck: zipfile.ZipFile, name: str) -> str:
    return deck.read(name).decode("utf-8", errors="ignore")


def _display_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(paths.REPO_ROOT))
    except ValueError:
        return str(path)


def _emu_to_cm(value: int | None) -> float | None:
    if value is None:
        return None
    return round(value / EMU_PER_CM, 3)


def _emu_to_in(value: int | None) -> float | None:
    if value is None:
        return None
    return round(value / EMU_PER_INCH, 3)


def _int_attr(node: ET.Element | None, attr: str) -> int | None:
    if node is None:
        return None
    value = node.attrib.get(attr)
    if value is None:
        return None
    try:
        return int(value)
    except ValueError:
        return None


def _shape_geometry(shape: ET.Element) -> dict[str, int | None]:
    xfrm = shape.find(".//a:xfrm", NS)
    off = xfrm.find("a:off", NS) if xfrm is not None else None
    ext = xfrm.find("a:ext", NS) if xfrm is not None else None
    return {
        "x_emu": _int_attr(off, "x"),
        "y_emu": _int_attr(off, "y"),
        "w_emu": _int_attr(ext, "cx"),
        "h_emu": _int_attr(ext, "cy"),
    }


def _shape_meta(shape: ET.Element) -> tuple[str | None, str | None]:
    c_nv_pr = shape.find(".//p:cNvPr", NS)
    if c_nv_pr is None:
        return None, None
    return c_nv_pr.attrib.get("id"), c_nv_pr.attrib.get("name")


def _shape_type(shape: ET.Element) -> str:
    tag = shape.tag.split("}")[-1]
    if tag == "sp":
        return "text_or_shape"
    if tag == "pic":
        return "image"
    if tag == "graphicFrame":
        return "graphic_frame"
    if tag == "grpSp":
        return "group"
    return tag


def _paragraph_text(paragraph: ET.Element) -> str:
    parts = [node.text or "" for node in paragraph.findall(".//a:t", NS)]
    return "".join(parts).strip()


def _shape_text(shape: ET.Element) -> str:
    paragraphs = [_paragraph_text(paragraph) for paragraph in shape.findall(".//a:p", NS)]
    return redact_sensitive_text("\n".join(item for item in paragraphs if item).strip())


def _font_family_from_rpr(rpr: ET.Element | None) -> str | None:
    if rpr is None:
        return None
    for path in ["a:latin", "a:ea", "a:cs"]:
        node = rpr.find(path, NS)
        if node is not None and node.attrib.get("typeface"):
            return node.attrib["typeface"]
    return None


def _font_size_from_rpr(rpr: ET.Element | None) -> float | None:
    if rpr is None or "sz" not in rpr.attrib:
        return None
    try:
        return round(int(rpr.attrib["sz"]) / 100, 2)
    except ValueError:
        return None


def _font_color_from_rpr(rpr: ET.Element | None) -> str | None:
    if rpr is None:
        return None
    srgb = rpr.find(".//a:srgbClr", NS)
    if srgb is not None and srgb.attrib.get("val"):
        return f"#{srgb.attrib['val'].upper()}"
    scheme = rpr.find(".//a:schemeClr", NS)
    if scheme is not None and scheme.attrib.get("val"):
        return f"scheme:{scheme.attrib['val']}"
    return None


def _run_style_values(shape: ET.Element) -> dict[str, Any]:
    families: list[str] = []
    sizes: list[float] = []
    colors: list[str] = []
    bold_values: list[bool] = []
    italic_values: list[bool] = []
    explicit_count = 0
    for rpr in shape.findall(".//a:rPr", NS):
        family = _font_family_from_rpr(rpr)
        size = _font_size_from_rpr(rpr)
        color = _font_color_from_rpr(rpr)
        if family:
            families.append(family)
            explicit_count += 1
        if size is not None:
            sizes.append(size)
            explicit_count += 1
        if color:
            colors.append(color)
            explicit_count += 1
        if "b" in rpr.attrib:
            bold_values.append(rpr.attrib["b"] in {"1", "true"})
            explicit_count += 1
        if "i" in rpr.attrib:
            italic_values.append(rpr.attrib["i"] in {"1", "true"})
            explicit_count += 1
    return {
        "font_family": _most_common(families),
        "font_size_pt": _median(sizes),
        "font_color": _most_common(colors),
        "bold": _most_common_bool(bold_values),
        "italic": _most_common_bool(italic_values),
        "explicit_text_style_count": explicit_count,
    }


def _paragraph_style_values(shape: ET.Element) -> dict[str, Any]:
    alignments: list[str] = []
    bullets: list[bool] = []
    indents: list[int] = []
    margins: list[int] = []
    line_spacings: list[str] = []
    for ppr in shape.findall(".//a:pPr", NS):
        if ppr.attrib.get("algn"):
            alignments.append(ppr.attrib["algn"])
        bullets.append(
            ppr.find("a:buChar", NS) is not None
            or ppr.find("a:buAutoNum", NS) is not None
            or ppr.find("a:buBlip", NS) is not None
        )
        if ppr.attrib.get("indent"):
            indents.append(int(ppr.attrib["indent"]))
        if ppr.attrib.get("marL"):
            margins.append(int(ppr.attrib["marL"]))
        line_spacing = _line_spacing(ppr)
        if line_spacing:
            line_spacings.append(line_spacing)
    return {
        "alignment": _most_common(alignments),
        "bullet": any(bullets),
        "indent_emu": _median_int(indents),
        "margin_left_emu": _median_int(margins),
        "line_spacing": _most_common(line_spacings),
    }


def _line_spacing(ppr: ET.Element) -> str | None:
    ln_spc = ppr.find("a:lnSpc", NS)
    if ln_spc is None:
        return None
    pct = ln_spc.find("a:spcPct", NS)
    if pct is not None and pct.attrib.get("val"):
        return f"pct:{pct.attrib['val']}"
    pts = ln_spc.find("a:spcPts", NS)
    if pts is not None and pts.attrib.get("val"):
        return f"pt:{round(int(pts.attrib['val']) / 100, 2)}"
    return None


def _most_common(values: list[str]) -> str | None:
    if not values:
        return None
    return Counter(values).most_common(1)[0][0]


def _most_common_bool(values: list[bool]) -> bool | None:
    if not values:
        return None
    return Counter(values).most_common(1)[0][0]


def _median(values: list[float]) -> float | None:
    if not values:
        return None
    return round(float(statistics.median(values)), 2)


def _median_int(values: list[int]) -> int | None:
    if not values:
        return None
    return int(statistics.median(values))


def _slide_size(deck: zipfile.ZipFile) -> dict[str, Any]:
    root = _load_xml(deck, "ppt/presentation.xml")
    slide_size = root.find("p:sldSz", NS)
    width = _int_attr(slide_size, "cx")
    height = _int_attr(slide_size, "cy")
    return {
        "width_emu": width,
        "height_emu": height,
        "width_in": _emu_to_in(width),
        "height_in": _emu_to_in(height),
        "width_cm": _emu_to_cm(width),
        "height_cm": _emu_to_cm(height),
    }


def _slide_paths(deck: zipfile.ZipFile) -> list[str]:
    slide_re = re.compile(r"ppt/slides/slide(\d+)\.xml$")
    paths_found = [name for name in deck.namelist() if slide_re.match(name)]
    return sorted(paths_found, key=lambda name: int(slide_re.match(name).group(1)))  # type: ignore[union-attr]


def _slide_number(slide_path: str) -> int:
    match = re.search(r"slide(\d+)\.xml$", slide_path)
    return int(match.group(1)) if match else 0


def _rels_path_for_slide(slide_no: int) -> str:
    return f"ppt/slides/_rels/slide{slide_no}.xml.rels"


def _notes_text(deck: zipfile.ZipFile, slide_no: int) -> str:
    rels = _relationships(deck, _rels_path_for_slide(slide_no))
    notes_path = None
    for rel in rels:
        if rel["type"].endswith("/notesSlide"):
            target = rel["target"].replace("../", "")
            notes_path = f"ppt/{target}" if not target.startswith("ppt/") else target
            break
    if not notes_path or notes_path not in deck.namelist():
        return ""
    root = ET.fromstring(_read_zip_text(deck, notes_path))
    paragraphs = []
    for paragraph in root.findall(".//a:p", NS):
        text = _paragraph_text(paragraph)
        if text:
            paragraphs.append(text)
    return redact_sensitive_text("\n".join(paragraphs).strip())


def _media_count(deck: zipfile.ZipFile, slide_no: int) -> int:
    rels = _relationships(deck, _rels_path_for_slide(slide_no))
    return sum(1 for rel in rels if "/image" in rel["type"] or "/chart" in rel["type"])


def _slide_type_guess(
    *,
    slide_no: int,
    slide_count: int,
    text: str,
    shape_count: int,
    image_count: int,
    notes_url_count: int,
) -> str:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    compact = " ".join(lines)
    if slide_no == 1:
        return "title"
    if image_count >= max(1, shape_count // 2):
        return "image_heavy"
    if notes_url_count >= 4 or len(lines) >= 7:
        return "checklist"
    if slide_no >= slide_count - 1 and "?" in compact:
        return "closing"
    if len(lines) <= 2 and len(compact) <= 90:
        return "section_title"
    if "?" in compact and len(compact) <= 180:
        return "question"
    if any(token in compact for token in ["“", "”", "\"", "발언", "원문"]):
        return "quote"
    if re.search(r"[0-9][0-9,.]*(%|원|달러|배|조|억|만|개)", compact):
        return "chart"
    if len(lines) <= 3 and len(compact) <= 160:
        return "big_headline"
    return "headline_body"


def _extract_slide_records(
    *,
    deck: zipfile.ZipFile,
    pptx_path: Path,
    slide_path: str,
    slide_count: int,
) -> list[dict[str, Any]]:
    slide_no = _slide_number(slide_path)
    root = _load_xml(deck, slide_path)
    shapes = [
        node
        for node in root.findall(".//p:cSld/p:spTree/*", NS)
        if node.tag.split("}")[-1] in {"sp", "pic", "graphicFrame", "grpSp"}
    ]
    slide_text = "\n".join(_shape_text(shape) for shape in shapes if _shape_text(shape))
    notes = _notes_text(deck, slide_no)
    source_notes = extract_source_notes(notes)
    notes_urls = extract_urls(notes)
    image_urls = [url for note in source_notes if note["is_image"] for url in note["urls"]]
    source_urls = [url for note in source_notes if not note["is_image"] for url in note["urls"]]
    image_count = _media_count(deck, slide_no)
    slide_type_guess = _slide_type_guess(
        slide_no=slide_no,
        slide_count=slide_count,
        text=slide_text,
        shape_count=len(shapes),
        image_count=image_count,
        notes_url_count=len(notes_urls),
    )
    records: list[dict[str, Any]] = []
    for index, shape in enumerate(shapes, start=1):
        shape_id, shape_name = _shape_meta(shape)
        geometry = _shape_geometry(shape)
        text = _shape_text(shape)
        run_style = _run_style_values(shape)
        para_style = _paragraph_style_values(shape)
        explicit_style_count = run_style.pop("explicit_text_style_count")
        font_family_inherited = bool(text) and run_style.get("font_family") is None
        font_size_inherited = bool(text) and run_style.get("font_size_pt") is None
        font_color_inherited = bool(text) and run_style.get("font_color") is None
        records.append(
            {
                "deck_name": pptx_path.name,
                "deck_path": _display_path(pptx_path),
                "slide_no": slide_no,
                "slide_type_guess": slide_type_guess,
                "shape_id": shape_id or str(index),
                "shape_name": shape_name,
                "shape_type": _shape_type(shape),
                **geometry,
                "x_cm": _emu_to_cm(geometry["x_emu"]),
                "y_cm": _emu_to_cm(geometry["y_emu"]),
                "w_cm": _emu_to_cm(geometry["w_emu"]),
                "h_cm": _emu_to_cm(geometry["h_emu"]),
                "text": text,
                "text_length": len(text),
                **run_style,
                **para_style,
                "font_family_inherited": font_family_inherited,
                "font_size_inherited": font_size_inherited,
                "font_color_inherited": font_color_inherited,
                "inherited_style": bool(text)
                and (
                    explicit_style_count == 0
                    or font_family_inherited
                    or font_size_inherited
                    or font_color_inherited
                ),
                "notes_url_count": len(notes_urls),
                "source_url_count": len(source_urls) if source_urls else len(notes_urls),
                "image_url_count": len(image_urls),
                "slide_shape_count": len(shapes),
                "slide_image_count": image_count,
            }
        )
    return records


def extract_shape_samples(pptx_paths: list[Path]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    all_records: list[dict[str, Any]] = []
    slide_sizes: list[dict[str, Any]] = []
    for pptx_path in pptx_paths:
        with zipfile.ZipFile(pptx_path) as deck:
            slide_size = _slide_size(deck)
            slide_sizes.append({"deck_name": pptx_path.name, **slide_size})
            slide_paths = _slide_paths(deck)
            for slide_path in slide_paths:
                all_records.extend(
                    _extract_slide_records(
                        deck=deck,
                        pptx_path=pptx_path,
                        slide_path=slide_path,
                        slide_count=len(slide_paths),
                    )
                )
    return all_records, {"slide_sizes": slide_sizes}


def aggregate_style_profile(
    records: list[dict[str, Any]],
    *,
    meta: dict[str, Any],
) -> dict[str, Any]:
    text_records = [record for record in records if record.get("text")]
    size_record = (meta.get("slide_sizes") or [{}])[0]
    by_layout: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in text_records:
        if record.get("w_cm") and record.get("h_cm"):
            by_layout[record.get("slide_type_guess", "unknown")].append(record)
    layout_patterns = {
        layout: _layout_pattern(layout_records)
        for layout, layout_records in sorted(by_layout.items())
        if layout in SLIDE_TYPE_GUESSES
    }
    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "deck_names": sorted({record["deck_name"] for record in records}),
        "slide_size": {
            "width_in": size_record.get("width_in"),
            "height_in": size_record.get("height_in"),
            "width_cm": size_record.get("width_cm"),
            "height_cm": size_record.get("height_cm"),
        },
        "shape_count": len(records),
        "text_shape_count": len(text_records),
        "common_fonts": _counter_values(record.get("font_family") for record in text_records),
        "common_font_sizes": _counter_values(record.get("font_size_pt") for record in text_records),
        "common_colors": _counter_values(record.get("font_color") for record in text_records),
        "inherited_style_records": sum(
            1 for record in text_records if record.get("inherited_style")
        ),
        "font_family_inherited_records": sum(
            1 for record in text_records if record.get("font_family_inherited")
        ),
        "font_size_inherited_records": sum(
            1 for record in text_records if record.get("font_size_inherited")
        ),
        "font_color_inherited_records": sum(
            1 for record in text_records if record.get("font_color_inherited")
        ),
        "slide_type_counts": _counter_values(record.get("slide_type_guess") for record in records),
        "layout_patterns": layout_patterns,
        "notes_label_patterns": _notes_label_patterns(records),
        "limits_and_caveats": [
            "Theme/master inherited font values are not fully resolved; "
            "inherited_style marks likely inherited text.",
            "Rendered line breaks can differ by OS font substitution and PowerPoint layout engine.",
            "Group shapes and complex SmartArt/chart internals are summarized at container level.",
            "Color values using theme scheme colors are reported as scheme:<name> "
            "unless explicit RGB is present.",
        ],
    }


def _counter_values(values: Any) -> list[dict[str, Any]]:
    clean = [value for value in values if value not in {None, ""}]
    return [
        {"value": value, "count": count}
        for value, count in Counter(clean).most_common(12)
    ]


def _layout_pattern(records: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "shape_count": len(records),
        "x_cm_median": _median_field(records, "x_cm"),
        "y_cm_median": _median_field(records, "y_cm"),
        "w_cm_median": _median_field(records, "w_cm"),
        "h_cm_median": _median_field(records, "h_cm"),
        "font_size_pt_median": _median_field(records, "font_size_pt"),
        "font_family_top": _top_field(records, "font_family"),
        "font_color_top": _top_field(records, "font_color"),
    }


def _median_field(records: list[dict[str, Any]], field: str) -> float | None:
    values = [record.get(field) for record in records if isinstance(record.get(field), int | float)]
    if not values:
        return None
    return round(float(statistics.median(values)), 3)


def _top_field(records: list[dict[str, Any]], field: str) -> Any:
    values = [record.get(field) for record in records if record.get(field)]
    if not values:
        return None
    return Counter(values).most_common(1)[0][0]


def _notes_label_patterns(records: list[dict[str, Any]]) -> dict[str, int]:
    labels: Counter[str] = Counter()
    for record in records:
        if record.get("notes_url_count", 0) > 0:
            labels["notes_with_urls"] += 1
        if record.get("source_url_count", 0) > 0:
            labels["source_url_present"] += 1
        if record.get("image_url_count", 0) > 0:
            labels["image_url_present"] += 1
    return dict(labels)


def write_profile_json(path: Path, profile: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(profile, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def write_report(path: Path, records: list[dict[str, Any]], profile: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Piti Style Profile Report",
        "",
        f"- Generated at: {profile.get('generated_at')}",
        f"- Analyzed decks: {', '.join(profile.get('deck_names', []))}",
        f"- Shape records: {profile.get('shape_count')}",
        f"- Text shape records: {profile.get('text_shape_count')}",
        f"- Slide size: {profile.get('slide_size')}",
        "",
        "## Common Fonts",
        "",
    ]
    lines.extend(_bullet_counter(profile.get("common_fonts", [])))
    lines.extend(["", "## Common Font Sizes", ""])
    lines.extend(_bullet_counter(profile.get("common_font_sizes", []), suffix=" pt"))
    lines.extend(["", "## Common Colors", ""])
    lines.extend(_bullet_counter(profile.get("common_colors", [])))
    lines.extend(
        [
            "",
            "## Theme / Master Inheritance Signals",
            "",
            f"- likely inherited style records: {profile.get('inherited_style_records')}",
            "- font family inherited/implicit records: "
            f"{profile.get('font_family_inherited_records')}",
            f"- font size inherited/implicit records: {profile.get('font_size_inherited_records')}",
            "- font color inherited/implicit records: "
            f"{profile.get('font_color_inherited_records')}",
        ]
    )
    lines.extend(["", "## Layout Patterns", ""])
    for layout, pattern in profile.get("layout_patterns", {}).items():
        lines.extend(
            [
                f"### {layout}",
                "",
                f"- shape_count: {pattern.get('shape_count')}",
                f"- x/y/w/h cm median: {pattern.get('x_cm_median')} / "
                f"{pattern.get('y_cm_median')} / {pattern.get('w_cm_median')} / "
                f"{pattern.get('h_cm_median')}",
                f"- font_size_pt_median: {pattern.get('font_size_pt_median')}",
                f"- font_family_top: {pattern.get('font_family_top')}",
                f"- font_color_top: {pattern.get('font_color_top')}",
                "",
            ]
        )
    lines.extend(
        [
            "## Notes / Source Patterns",
            "",
            f"- {profile.get('notes_label_patterns')}",
            "",
            "## Piti Renderer Recommendations",
            "",
            *_renderer_recommendations(profile),
            "",
            "## Extraction Caveats",
            "",
        ]
    )
    lines.extend(f"- {item}" for item in profile.get("limits_and_caveats", []))
    lines.extend(
        [
            "- Manual visual QA is still required before applying these values to renderer output.",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _bullet_counter(items: list[dict[str, Any]], *, suffix: str = "") -> list[str]:
    if not items:
        return ["- none detected"]
    return [f"- {item['value']}{suffix}: {item['count']}" for item in items]


def _renderer_recommendations(profile: dict[str, Any]) -> list[str]:
    font = (profile.get("common_fonts") or [{"value": "Malgun Gothic"}])[0]["value"]
    sizes = [item["value"] for item in profile.get("common_font_sizes", [])[:5]]
    layout_patterns = profile.get("layout_patterns", {})
    recommendations = [
        f"- Start with `{font}` as the first explicit font candidate, "
        "while noting theme inheritance.",
        f"- Use observed common font sizes as candidates: {sizes}.",
    ]
    for key in ["title", "section_title", "headline_body", "image_heavy", "question"]:
        pattern = layout_patterns.get(key)
        if not pattern:
            continue
        recommendations.append(
            "- {key}: median box x/y/w/h cm {x}/{y}/{w}/{h}, font {font_size} pt.".format(
                key=key,
                x=pattern.get("x_cm_median"),
                y=pattern.get("y_cm_median"),
                w=pattern.get("w_cm_median"),
                h=pattern.get("h_cm_median"),
                font_size=pattern.get("font_size_pt_median"),
            )
        )
    recommendations.append("- Preserve speaker notes/source labels before visual tuning.")
    recommendations.append(
        "- Do not apply image placement automatically until copyright workflow exists."
    )
    return recommendations


def run_extraction(
    pptx_paths: list[Path],
    *,
    samples_jsonl: Path = DEFAULT_SAMPLES_JSONL,
    profile_json: Path = DEFAULT_PROFILE_JSON,
    report_md: Path = DEFAULT_REPORT,
) -> ExtractOutputs:
    records, meta = extract_shape_samples(pptx_paths)
    profile = aggregate_style_profile(records, meta=meta)
    write_jsonl(samples_jsonl, records)
    write_profile_json(profile_json, profile)
    write_report(report_md, records, profile)
    return ExtractOutputs(
        samples_jsonl=samples_jsonl,
        profile_json=profile_json,
        report_md=report_md,
    )


@app.callback(invoke_without_command=True)
def main(
    input_path: Annotated[
        list[Path] | None,
        typer.Option("--input", help="PPTX file to analyze. Can be repeated."),
    ] = None,
    samples_jsonl: Annotated[
        Path,
        typer.Option("--samples-jsonl", help="Shape sample JSONL output path."),
    ] = DEFAULT_SAMPLES_JSONL,
    profile_json: Annotated[
        Path,
        typer.Option("--profile-json", help="Aggregate style profile JSON output path."),
    ] = DEFAULT_PROFILE_JSON,
    report_md: Annotated[
        Path,
        typer.Option("--report", help="Markdown report output path."),
    ] = DEFAULT_REPORT,
) -> None:
    """Extract a Syukaworld PPTX style profile from one or more PPTX files."""
    pptx_paths = input_path or [DEFAULT_INPUT]
    missing = [path for path in pptx_paths if not path.exists()]
    if missing:
        raise typer.BadParameter(f"Missing PPTX input(s): {missing}")
    outputs = run_extraction(
        pptx_paths,
        samples_jsonl=samples_jsonl,
        profile_json=profile_json,
        report_md=report_md,
    )
    console.print(
        "[green]Extracted PPTX style profile: "
        f"{outputs.samples_jsonl}, {outputs.profile_json}, {outputs.report_md}[/green]"
    )


if __name__ == "__main__":
    app()
