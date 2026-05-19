"""Build Piti-ready slide specs from existing Anny storyline JSON artifacts."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Any
from urllib.parse import urlparse

import typer
from jsonschema import Draft202012Validator
from rich.console import Console

from luddite import paths
from luddite.utils.urls import canonicalize_url

build_app = typer.Typer(no_args_is_help=False)
validate_app = typer.Typer(no_args_is_help=False)
console = Console()


@dataclass(frozen=True)
class SlideSpecCase:
    deck_id: str
    source_storyline_path: Path
    output_path: Path
    priority: int


DEFAULT_CASES = [
    SlideSpecCase(
        deck_id="ai_knowledge_institution",
        source_storyline_path=(
            paths.ANNY_STORYLINE_DRY_RUN_DIR
            / "ai_knowledge_institution_gpt_pro_storyline_enriched.json"
        ),
        output_path=(
            paths.PITI_SLIDE_SPECS_DIR / "ai_knowledge_institution_slide_spec.json"
        ),
        priority=1,
    ),
    SlideSpecCase(
        deck_id="productive_finance_policy",
        source_storyline_path=(
            paths.ANNY_STORYLINE_DRY_RUN_DIR
            / "productive_finance_policy_gpt_pro_storyline_enriched.json"
        ),
        output_path=(
            paths.PITI_SLIDE_SPECS_DIR / "productive_finance_policy_slide_spec.json"
        ),
        priority=2,
    ),
]

DEFAULT_VALIDATION_REPORT = (
    paths.REPORTS_DIR / f"piti_slide_spec_validation_{datetime.now(UTC).date()}.md"
)

EXPLANATORY_MARKERS = (
    "다만",
    "하지만",
    "그러나",
    "공식자료",
    "자료는",
    "단정",
    "보수적으로",
    "확인 필요",
    "needs_",
)

CONCEPTUAL_DIAGRAM_MARKERS = (
    "검색",
    "즉답",
    "답안지",
    "질문",
    "검증",
    "과정",
    "맥락",
    "역할",
    "학교",
    "박물관",
    "천문관",
    "과학관",
    "도서관",
    "AI 정답",
    "AI 검산",
    "금지",
    "다루",
    "담보",
    "단기",
    "장기",
    "위험",
    "손실",
    "분담",
    "정책금융",
    "국민성장펀드",
    "은행",
    "건전성",
    "예금자",
)

SOURCE_CARD_TYPES = {"quote", "source_heavy"}

EDITOR_MARKERS = (
    "[수동",
    "[이미지",
    "[차트",
    "[도식",
    "[기사",
    "needs_fact_check",
    "needs_source",
    "before_broadcast",
    "split_recommended",
    "edit_notes",
    "copyright_risk",
    "manual_check_required",
    "draft",
    "scaffold",
)


def _load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as source:
        payload = json.load(source)
    if not isinstance(payload, dict):
        raise ValueError(f"Expected JSON object at {path}")
    return payload


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _display_path(path: Path | None) -> str | None:
    if path is None:
        return None
    try:
        return str(path.resolve().relative_to(paths.REPO_ROOT))
    except ValueError:
        return str(path)


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _body_lines(slide: dict[str, Any]) -> list[str]:
    body = slide.get("body")
    if isinstance(body, list):
        return [str(item).strip() for item in body if str(item).strip()]
    if body is None:
        return []
    text = str(body).strip()
    return [text] if text else []


def _short_text(value: str, limit: int = 44) -> str:
    text = re.sub(r"\s+", " ", value).strip()
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"


def _normalize_for_compare(value: str) -> str:
    return re.sub(r"\s+", "", value).strip().lower()


def _first_url(slide: dict[str, Any], key: str) -> str | None:
    for url in _as_list(slide.get(key)):
        text = str(url).strip()
        if text:
            return text
    return None


def _source_name_from_url(url: str | None) -> str | None:
    if not url:
        return None
    host = (urlparse(url).netloc or url).removeprefix("www.")
    known = {
        "bbc.com": "BBC",
        "bbc.co.uk": "BBC",
        "microsoft.com": "Microsoft Research",
        "unesco.org": "UNESCO",
        "oecd.org": "OECD",
        "fsc.go.kr": "금융위원회",
        "kdb.co.kr": "산업은행",
        "korea.kr": "정책브리핑",
        "bis.org": "BIS",
        "ft.com": "Financial Times",
        "reuters.com": "Reuters",
        "einfomax.co.kr": "연합인포맥스",
    }
    for domain, label in known.items():
        if domain in host:
            return label
    root = host.split("/")[0].split(".")[0]
    return root.title() if root else "Source"


def _is_english_line(line: str) -> bool:
    if _is_korean_line(line):
        return False
    letters = re.findall(r"[A-Za-z]", line)
    return bool(letters) and len(letters) >= max(4, len(line) * 0.25)


def _is_korean_line(line: str) -> bool:
    return bool(re.search(r"[가-힣]", line))


def _has_actual_quote_text(slide: dict[str, Any]) -> bool:
    lines = _body_lines(slide)
    if any(_is_english_line(line) for line in lines) and any(
        _is_korean_line(line) for line in lines
    ):
        return True
    if str(slide.get("slide_type") or "") != "quote":
        return False
    quote_markers = ('"', "'", "“", "”", "‘", "’", "라고", "says", "warns")
    return any(marker in line for line in lines for marker in quote_markers)


def _source_refs(slide: dict[str, Any]) -> list[dict[str, Any]]:
    refs = []
    for ref in _as_list(slide.get("source_refs")):
        if not isinstance(ref, dict) or not str(ref.get("url") or "").strip():
            continue
        refs.append(
            {
                "url": str(ref.get("url")),
                "role": str(ref.get("role") or "source_context"),
                "use": str(ref.get("use") or "Source attached from Anny storyline."),
                "confidence": str(ref.get("confidence") or "medium"),
                "manual_check_required": bool(ref.get("manual_check_required")),
            }
        )
    existing_urls = {canonicalize_url(ref["url"]) for ref in refs}
    for url in _as_list(slide.get("source_urls")):
        text = str(url).strip()
        if not text or canonicalize_url(text) in existing_urls:
            continue
        refs.append(
            {
                "url": text,
                "role": "source_context",
                "use": "Source URL carried from Anny storyline.",
                "confidence": "medium",
                "manual_check_required": bool(
                    slide.get("needs_source") or slide.get("needs_fact_check")
                ),
            }
        )
    return refs


def _source_display_title(slide: dict[str, Any], source_name: str | None) -> str:
    headline = str(slide.get("headline") or "")
    for ref in _source_refs(slide):
        use = str(ref.get("use") or "").strip()
        if use and _normalize_for_compare(use) != _normalize_for_compare(headline):
            return _short_text(use, 48)
    notes = str(slide.get("notes") or "")
    for line in notes.splitlines():
        if "http://" in line or "https://" in line:
            continue
        cleaned = re.sub(r"\[[^\]]+\]\s*", "", line).strip(" .:-—")
        if source_name and cleaned.lower().startswith(source_name.lower()):
            cleaned = cleaned[len(source_name) :].strip(" .:-—")
        if cleaned and _normalize_for_compare(cleaned) != _normalize_for_compare(headline):
            return _short_text(cleaned, 48)
    return "Reference material"


def _screen_position(proof_type: str) -> str:
    if proof_type in {"chart", "table"}:
        return "full_width_chart"
    if proof_type in {"source_card", "article_quote", "image", "screenshot", "logo"}:
        return "left_half"
    if proof_type in {"diagram", "person_photo"}:
        return "center_large"
    return "none"


def _diagram_payload(slide: dict[str, Any]) -> tuple[list[str], list[dict[str, str | None]]]:
    text = " ".join([str(slide.get("headline") or ""), *_body_lines(slide)])
    if any(token in text for token in ["검색", "즉답", "답안지"]):
        nodes = ["기존 검색", "AI 즉답", "비교·검증", "바로 답"]
        edges = [
            {"from": "기존 검색", "to": "비교·검증", "label": "여러 결과를 확인"},
            {"from": "AI 즉답", "to": "바로 답", "label": "과정 압축"},
        ]
        return nodes, edges
    if any(token in text for token in ["학교", "박물관", "천문관", "과학관", "지식기관"]):
        nodes = ["답 제공", "질문 훈련", "검증", "맥락"]
        edges = [
            {"from": "답 제공", "to": "질문 훈련", "label": "역할 변화"},
            {"from": "질문 훈련", "to": "검증", "label": "확인"},
            {"from": "검증", "to": "맥락", "label": "이해"},
        ]
        return nodes, edges
    if any(token in text for token in ["질문", "검증", "출처", "AI 검산"]):
        nodes = ["질문", "검증", "맥락"]
        edges = [
            {"from": "질문", "to": "검증", "label": "출처 확인"},
            {"from": "검증", "to": "맥락", "label": "다른 자료와 비교"},
        ]
        return nodes, edges
    if any(token in text for token in ["금융", "펀드", "담보", "위험", "손실"]):
        nodes = ["안전한 금융", "성장 금융", "담보·단기", "장기·위험분담"]
        edges = [
            {"from": "안전한 금융", "to": "담보·단기", "label": "낮은 위험"},
            {"from": "성장 금융", "to": "장기·위험분담", "label": "불확실성"},
        ]
        return nodes, edges
    nodes = ["기존 검색", "AI 즉답"]
    edges = [{"from": "기존 검색", "to": "AI 즉답", "label": "비교·검증"}]
    return nodes, edges


def _chart_source_label(slide: dict[str, Any]) -> str | None:
    url = _first_url(slide, "source_urls")
    source_name = _source_name_from_url(url)
    return f"(출처: {source_name})" if source_name else None


def _has_numeric_chart_signal(slide: dict[str, Any]) -> bool:
    body = _body_lines(slide)
    text = " ".join(body)
    if str(slide.get("slide_type") or "") == "data":
        return True
    if not re.search(r"\d", text):
        return False
    chart_markers = (
        "규모",
        "원",
        "%",
        "비율",
        "순위",
        "금액",
        "조",
        "억",
        "기간",
        "수치",
        "체크리스트",
    )
    return any(marker in text for marker in chart_markers)


def _is_source_card_candidate(slide: dict[str, Any]) -> bool:
    slide_type = str(slide.get("slide_type") or "")
    if slide_type in SOURCE_CARD_TYPES:
        return True
    text = " ".join([str(slide.get("headline") or ""), *_body_lines(slide)])
    markers = (
        "BBC",
        "Royal Observatory",
        "보도",
        "원문",
        "보고서",
        "체크리스트",
    )
    return any(marker in text for marker in markers)


def _is_conceptual_diagram_candidate(slide: dict[str, Any]) -> bool:
    slide_type = str(slide.get("slide_type") or "")
    if slide_type in {
        "comparison",
        "risk",
        "counterpoint",
        "bridge",
        "rhetorical",
        "closing_question",
        "punchline",
    }:
        return True
    text = " ".join([str(slide.get("headline") or ""), *_body_lines(slide)])
    return any(marker in text for marker in CONCEPTUAL_DIAGRAM_MARKERS)


def _proof_object(slide: dict[str, Any]) -> dict[str, Any]:
    slide_type = str(slide.get("slide_type") or "explainer")
    source_url = _first_url(slide, "source_urls")
    image_url = _first_url(slide, "image_urls")
    body = _body_lines(slide)
    proof_type = "none"
    if slide_type in {"production_checklist", "title", "section_title"}:
        proof_type = "none"
    elif _has_numeric_chart_signal(slide):
        proof_type = "chart"
    elif image_url:
        proof_type = "image"
    elif _has_actual_quote_text(slide) and source_url:
        proof_type = "article_quote"
    elif _is_conceptual_diagram_candidate(slide) and not _is_source_card_candidate(slide):
        proof_type = "diagram"
    elif source_url:
        proof_type = "source_card"
    elif _is_conceptual_diagram_candidate(slide):
        proof_type = "diagram"
    proof_source_url = source_url if proof_type != "none" else None
    source_name = _source_name_from_url(proof_source_url)
    english_lines = [line for line in body if _is_english_line(line)]
    korean_lines = [line for line in body if _is_korean_line(line)]
    diagram_nodes, diagram_edges = _diagram_payload(slide) if proof_type == "diagram" else ([], [])
    return {
        "type": proof_type,
        "screen_position": _screen_position(proof_type),
        "source_name": source_name,
        "display_title": (
            _source_display_title(slide, source_name)
            if proof_type in {"source_card", "article_quote"}
            else None
        ),
        "quote_text": english_lines[0] if proof_type == "article_quote" and english_lines else None,
        "quote_translation": (
            korean_lines[0] if proof_type == "article_quote" and korean_lines else None
        ),
        "source_url": proof_source_url,
        "image_url": image_url,
        "chart_title": str(slide.get("headline") or "") if proof_type == "chart" else None,
        "chart_source_label": _chart_source_label(slide) if proof_type == "chart" else None,
        "data_hint": "; ".join(body[:3]) if proof_type in {"chart", "table"} else None,
        "diagram_nodes": diagram_nodes,
        "diagram_edges": diagram_edges,
        "placeholder_reason": (
            "Diagram nodes/edges provided for editable scaffold."
            if proof_type == "diagram"
            else None
        ),
        "manual_insert_required": proof_type not in {"none", "source_card"},
        "copyright_risk": bool(image_url),
    }


def _is_explanatory_line(line: str) -> bool:
    lowered = line.lower()
    return any(marker.lower() in lowered for marker in EXPLANATORY_MARKERS)


def _rewrite_screen_body(slide: dict[str, Any], proof_type: str) -> list[str] | None:
    if proof_type in {"chart", "table", "diagram"}:
        return []
    text = " ".join([str(slide.get("headline") or ""), *_body_lines(slide)])
    if "바로 답" in text or "즉답" in text or "답안지" in text:
        return ["검색창을 열기도 전에", "답안지가 먼저 나온다"]
    if "검색어" in text and ("비교" in text or "검증" in text):
        return ["예전 검색은 느렸지만", "비교하고 검증하는 흔적이 남았다"]
    if "질문" in text and "검증" in text:
        return ["답보다 남겨야 할 것", "질문하고 검증하는 습관"]
    if "학교" in text and "정답" in text:
        return ["정답을 외웠나보다", "어떻게 확인했나를 묻는다"]
    if "박물관" in text or "천문관" in text:
        return ["설명보다 중요한 건", "보고 묻고 연결하는 경험"]
    if "담보" in text and "단기" in text:
        return ["안전한 대출은 쉽지만", "긴 위험은 잘 담기 어렵다"]
    if "위험" in text and any(token in text for token in ["분담", "손실", "금융권"]):
        return ["돈이 필요한 곳은 길고", "위험은 누가 나눌 것인가"]
    if "국민성장펀드" in text:
        return ["성장이라는 이름 뒤에", "손실을 나누는 규칙이 있다"]
    return None


def _screen_body(slide: dict[str, Any], proof_type: str) -> list[str]:
    rewritten = _rewrite_screen_body(slide, proof_type)
    if rewritten is not None:
        return rewritten[:2]
    if proof_type == "source_card":
        return []
    limit = 1 if proof_type == "source_card" else 3
    candidates = [line for line in _body_lines(slide) if not _is_explanatory_line(line)]
    if not candidates and _body_lines(slide):
        candidates = [_body_lines(slide)[0]]
    return [_short_text(line, 34) for line in candidates[: min(limit, 2)]]


def _overflow_notes(slide: dict[str, Any], screen_body: list[str]) -> list[str]:
    screen_norm = {_normalize_for_compare(line) for line in screen_body}
    return [
        line
        for line in _body_lines(slide)
        if _normalize_for_compare(_short_text(line, 42)) not in screen_norm
    ]


def _speaker_notes(slide: dict[str, Any], overflow_notes: list[str]) -> str:
    lines: list[str] = []
    notes = str(slide.get("notes") or "").strip()
    if notes:
        lines.append(notes)
    if overflow_notes:
        lines.append("[overflow_notes]")
        lines.extend(overflow_notes)
    for ref in _source_refs(slide):
        lines.append(f"[source_ref] {ref['role']} | {ref['use']} | {ref['url']}")
    for url in _as_list(slide.get("image_urls")):
        if url:
            lines.append(f"[image] {url}")
    if slide.get("needs_source"):
        lines.append("[check] needs_source=true")
    if slide.get("needs_fact_check"):
        lines.append("[check] needs_fact_check=true")
    if slide.get("required_before_broadcast"):
        lines.append("[check] required_before_broadcast=true")
    return "\n".join(lines)


def _layout_intent(slide: dict[str, Any], proof_type: str) -> str:
    slide_type = str(slide.get("slide_type") or "explainer")
    if slide_type == "title":
        return "title"
    if slide_type == "section_title":
        return "section_title"
    if slide_type == "production_checklist":
        return "appendix_checklist"
    if proof_type in {"chart", "table"}:
        return "chart_table_reference"
    if proof_type in {"source_card", "article_quote"}:
        return "source_card_or_article_quote"
    if proof_type in {"image", "screenshot", "logo", "person_photo"}:
        return "image_left_quote_right"
    if proof_type == "diagram":
        return "diagram"
    if slide_type == "closing_question":
        return "closing_question"
    if slide_type in {"bridge", "rhetorical", "punchline"}:
        return "text_only_calculation"
    return "headline_body"


def _editor_instruction(slide: dict[str, Any], proof_type: str) -> str | None:
    instructions: list[str] = []
    if proof_type in {"chart", "table"}:
        instructions.append("Chart/table data must be manually designed before broadcast.")
    if proof_type in {"image", "screenshot", "logo", "person_photo"}:
        instructions.append("Insert or license visual asset manually.")
    if slide.get("needs_source"):
        instructions.append("Confirm or add source before using this slide.")
    if slide.get("needs_fact_check"):
        instructions.append("Manual fact-check required before broadcast.")
    return " ".join(instructions) if instructions else None


def _slide_spec(
    slide: dict[str, Any],
    *,
    deck_id: str,
    global_slide_no: int,
    section_id: str,
) -> dict[str, Any]:
    proof = _proof_object(slide)
    screen_body = _screen_body(slide, str(proof["type"]))
    overflow_notes = _overflow_notes(slide, screen_body)
    return {
        "slide_id": f"{deck_id}_slide_{global_slide_no:02}",
        "slide_no": global_slide_no,
        "section_id": section_id,
        "source_slide_refs": [slide.get("slide_no") or global_slide_no],
        "layout_intent": _layout_intent(slide, str(proof["type"])),
        "screen_headline": _short_text(str(slide.get("headline") or "(untitled)"), 56),
        "screen_body": screen_body,
        "speaker_notes_expanded": _speaker_notes(slide, overflow_notes),
        "overflow_notes": overflow_notes,
        "proof_object": proof,
        "editor_instruction": _editor_instruction(slide, str(proof["type"])),
        "source_refs": _source_refs(slide),
        "risk_flags": [str(flag) for flag in _as_list(slide.get("risk_flags"))],
        "needs_source": bool(slide.get("needs_source")),
        "needs_fact_check": bool(slide.get("needs_fact_check")),
        "required_before_broadcast": bool(slide.get("required_before_broadcast")),
        "do_not_claim": [str(item) for item in _as_list(slide.get("do_not_claim"))],
        "fact_check_kind": slide.get("fact_check_kind"),
        "fact_check_priority": slide.get("fact_check_priority"),
    }


def build_piti_slide_spec_from_storyline(
    storyline: dict[str, Any],
    *,
    deck_id: str,
    source_storyline_path: Path | None = None,
) -> dict[str, Any]:
    sections: list[dict[str, Any]] = []
    flat_slides: list[dict[str, Any]] = []
    global_slide_no = 0
    for section_no, section in enumerate(storyline.get("sections", []), start=1):
        section_id = f"section_{section_no:02}"
        section_slides: list[dict[str, Any]] = []
        for slide in _as_list(section.get("slides")):
            if not isinstance(slide, dict):
                continue
            global_slide_no += 1
            spec_slide = _slide_spec(
                slide,
                deck_id=deck_id,
                global_slide_no=global_slide_no,
                section_id=section_id,
            )
            flat_slides.append(spec_slide)
            section_slides.append(spec_slide)
        sections.append(
            {
                "section_id": section_id,
                "section_no": section_no,
                "section_title": str(section.get("section_title") or f"Section {section_no}"),
                "purpose": section.get("purpose"),
                "slides": section_slides,
            }
        )
    return {
        "deck_id": f"piti_slide_spec_{deck_id}",
        "story_seed_title": str(storyline.get("title") or deck_id),
        "source_storyline_id": storyline.get("storyline_id"),
        "source_storyline_path": _display_path(source_storyline_path),
        "sections": sections,
        "slides": flat_slides,
        "risk_flags": [str(flag) for flag in _as_list(storyline.get("risk_flags"))],
        "required_fact_checks": [
            str(item) for item in _as_list(storyline.get("required_fact_checks"))
        ],
        "readiness": {
            "ready_for_piti_renderer": True,
            "ready_for_production_piti_agent": False,
            "ready_for_broadcast": False,
        },
        "notes": (
            "Temporary adapter output from Anny storyline to Piti-ready slide spec. "
            "Long-term Anny should emit this contract directly."
        ),
        "created_at": datetime.now(UTC).isoformat(),
    }


def _schema_validator() -> Draft202012Validator:
    return Draft202012Validator(_load_json(paths.SPECS_DIR / "piti_slide_spec_schema.json"))


def _source_urls(slide: dict[str, Any]) -> set[str]:
    return {canonicalize_url(str(ref.get("url"))) for ref in slide.get("source_refs", [])}


def _proof_type(slide: dict[str, Any]) -> str:
    proof = slide.get("proof_object")
    return str(proof.get("type") or "none") if isinstance(proof, dict) else "none"


def _max_consecutive_proof_type(slides: list[dict[str, Any]], proof_type: str) -> int:
    max_run = 0
    current = 0
    for slide in slides:
        if _proof_type(slide) == proof_type:
            current += 1
            max_run = max(max_run, current)
        else:
            current = 0
    return max_run


def _source_card_run_warnings(slides: list[dict[str, Any]]) -> list[str]:
    warnings = []
    run: list[int] = []
    for slide in slides:
        if _proof_type(slide) == "source_card":
            run.append(int(slide.get("slide_no") or 0))
            continue
        if len(run) >= 3:
            warnings.append(f"source_card_run_length_warning: slides {run}")
        run = []
    if len(run) >= 3:
        warnings.append(f"source_card_run_length_warning: slides {run}")
    return warnings


def _screen_body_explanatory_slides(slides: list[dict[str, Any]]) -> list[int]:
    return [
        int(slide.get("slide_no") or 0)
        for slide in slides
        if any(_is_explanatory_line(str(line)) for line in _as_list(slide.get("screen_body")))
    ]


def _screen_body_overflow_slides(slides: list[dict[str, Any]]) -> list[int]:
    return [
        int(slide.get("slide_no") or 0)
        for slide in slides
        if _as_list(slide.get("overflow_notes"))
    ]


def _has_conceptual_topic(spec: dict[str, Any]) -> bool:
    text = " ".join(
        [
            str(spec.get("story_seed_title") or ""),
            *[str(slide.get("screen_headline") or "") for slide in spec.get("slides", [])],
        ]
    )
    return any(marker in text for marker in CONCEPTUAL_DIAGRAM_MARKERS)


def _has_numeric_topic(spec: dict[str, Any]) -> bool:
    text = " ".join(
        [
            str(spec.get("story_seed_title") or ""),
            *[
                str(line)
                for slide in spec.get("slides", [])
                for line in _as_list(slide.get("overflow_notes"))
            ],
            *[
                str(slide.get("speaker_notes_expanded") or "")
                for slide in spec.get("slides", [])
            ],
        ]
    )
    return bool(re.search(r"\d", text)) and any(
        marker in text for marker in ["규모", "원", "%", "비율", "수치", "순위", "조", "억"]
    )


def validate_piti_slide_spec(spec: dict[str, Any]) -> dict[str, Any]:
    schema_errors = [error.message for error in _schema_validator().iter_errors(spec)]
    slides = spec.get("slides", [])
    slide_numbers = [slide.get("slide_no") for slide in slides]
    slide_no_integrity = slide_numbers == list(range(1, len(slide_numbers) + 1))
    issues: list[str] = []
    warnings: list[str] = []
    for slide in slides:
        slide_no = slide.get("slide_no")
        headline = str(slide.get("screen_headline") or "")
        body = [str(line) for line in slide.get("screen_body", [])]
        proof = slide.get("proof_object", {})
        proof_type = str(proof.get("type") or "none")
        if not headline:
            issues.append(f"slide {slide_no}: screen_headline missing")
        if len(body) > 3:
            issues.append(f"slide {slide_no}: screen_body exceeds 3 lines")
        if slide.get("overflow_notes") and not str(
            slide.get("speaker_notes_expanded") or ""
        ).strip():
            issues.append(f"slide {slide_no}: overflow exists without expanded notes")
        if proof_type == "article_quote" and not (
            proof.get("quote_text") or proof.get("quote_translation")
        ):
            issues.append(f"slide {slide_no}: article_quote requires quote text")
        if proof_type == "source_card":
            title = str(proof.get("display_title") or "")
            if _normalize_for_compare(title) == _normalize_for_compare(headline):
                issues.append(f"slide {slide_no}: source_card repeats screen_headline")
        if proof_type in {"chart", "table"} and len(body) > 1:
            issues.append(f"slide {slide_no}: chart/table screen_body is too long")
        if proof_type == "diagram" and not (
            proof.get("diagram_nodes") and proof.get("diagram_edges")
        ):
            issues.append(f"slide {slide_no}: diagram requires nodes and edges")
        if any(any(marker in line for marker in EDITOR_MARKERS) for line in body):
            issues.append(f"slide {slide_no}: editor instruction leaked into screen_body")
        if slide.get("source_refs") and not _source_urls(slide):
            issues.append(f"slide {slide_no}: source_refs did not preserve URL")
        if not isinstance(slide.get("needs_fact_check"), bool):
            issues.append(f"slide {slide_no}: needs_fact_check must be boolean")
        if (
            proof_type == "none"
            and slide.get("source_refs")
            and slide.get("layout_intent") != "appendix_checklist"
        ):
            warnings.append(f"slide {slide_no}: source-backed slide has no proof object")
    source_card_count = sum(1 for slide in slides if _proof_type(slide) == "source_card")
    diagram_count = sum(1 for slide in slides if _proof_type(slide) == "diagram")
    chart_table_count = sum(1 for slide in slides if _proof_type(slide) in {"chart", "table"})
    source_card_ratio = source_card_count / len(slides) if slides else 0.0
    max_source_card_run_length = _max_consecutive_proof_type(slides, "source_card")
    warnings.extend(_source_card_run_warnings(slides))
    if source_card_ratio >= 0.6:
        warnings.append(
            f"source_card_ratio_warning: {source_card_count}/{len(slides)} "
            "slides use source_card"
        )
    if _has_conceptual_topic(spec) and diagram_count == 0:
        warnings.append("diagram_missing_for_conceptual_topic_warning")
    if _has_numeric_topic(spec) and chart_table_count == 0:
        warnings.append("chart_missing_for_numeric_topic_warning")
    explanatory_slides = _screen_body_explanatory_slides(slides)
    for slide_no in explanatory_slides:
        warnings.append(f"screen_body_explanatory_warning: slide {slide_no}")
    overflow_slides = _screen_body_overflow_slides(slides)
    if overflow_slides:
        warnings.append(f"screen_body_overflow_warning: slides {overflow_slides}")
    passed = not schema_errors and not issues and slide_no_integrity
    return {
        "deck_id": spec.get("deck_id"),
        "schema_valid": not schema_errors,
        "schema_errors": schema_errors,
        "slide_count": len(slides),
        "section_count": len(spec.get("sections", [])),
        "slide_no_integrity": slide_no_integrity,
        "issues": issues,
        "warnings": warnings,
        "source_card_count": source_card_count,
        "article_quote_count": sum(
            1 for slide in slides if slide.get("proof_object", {}).get("type") == "article_quote"
        ),
        "diagram_count": diagram_count,
        "chart_table_count": chart_table_count,
        "source_card_ratio": round(source_card_ratio, 3),
        "max_source_card_run_length": max_source_card_run_length,
        "screen_body_explanatory_warning_count": len(explanatory_slides),
        "screen_body_explanatory_slides": explanatory_slides,
        "screen_body_overflow_warning_count": len(overflow_slides),
        "screen_body_overflow_slides": overflow_slides,
        "needs_source_count": sum(1 for slide in slides if slide.get("needs_source")),
        "needs_fact_check_count": sum(
            1 for slide in slides if slide.get("needs_fact_check")
        ),
        "passed": passed,
    }


def write_validation_report(path: Path, results: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    passed_count = sum(1 for result in results if result.get("passed"))
    lines = [
        "# Piti Slide Spec Validation Report",
        "",
        f"- Generated at: {datetime.now(UTC).isoformat()}",
        f"- Specs: {len(results)}",
        f"- Passed: {passed_count}",
        f"- Failed: {len(results) - passed_count}",
        "- Production Anny agent: not implemented",
        "- Production Piti agent: not implemented",
        "- LLM/API calls: none",
        "",
        "## Specs",
        "",
        (
            "| Deck | Slides | Sections | Schema | Source Cards | Quotes | Diagrams | "
            "Charts/Tables | Source Card Ratio | Max Source Run | Screen Copy Warnings | "
            "Overflow Warnings | Needs Source | Needs Fact Check | Issues | Warnings | Passed |"
        ),
        (
            "|---|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"
            "---:|---|"
        ),
    ]
    for result in results:
        lines.append(
            "| {deck} | {slides} | {sections} | {schema} | {source_cards} | "
            "{quotes} | {diagrams} | {charts} | {ratio} | {max_run} | "
            "{screen_warnings} | {overflow_warnings} | {needs_source} | "
            "{needs_fact_check} | {issues} | {warnings} | {passed} |".format(
                deck=result.get("deck_id"),
                slides=result.get("slide_count"),
                sections=result.get("section_count"),
                schema="yes" if result.get("schema_valid") else "no",
                source_cards=result.get("source_card_count"),
                quotes=result.get("article_quote_count"),
                diagrams=result.get("diagram_count"),
                charts=result.get("chart_table_count"),
                ratio=result.get("source_card_ratio"),
                max_run=result.get("max_source_card_run_length"),
                screen_warnings=result.get("screen_body_explanatory_warning_count"),
                overflow_warnings=result.get("screen_body_overflow_warning_count"),
                needs_source=result.get("needs_source_count"),
                needs_fact_check=result.get("needs_fact_check_count"),
                issues=len(result.get("issues", [])),
                warnings=len(result.get("warnings", [])),
                passed="yes" if result.get("passed") else "no",
            )
        )
    lines.extend(["", "## Issues", ""])
    for result in results:
        issues = result.get("issues", [])
        if issues:
            lines.extend(f"- {result.get('deck_id')}: {issue}" for issue in issues[:20])
        else:
            lines.append(f"- {result.get('deck_id')}: none")
    lines.extend(["", "## Warnings", ""])
    for result in results:
        warnings = result.get("warnings", [])
        if warnings:
            lines.extend(f"- {result.get('deck_id')}: {warning}" for warning in warnings[:20])
        else:
            lines.append(f"- {result.get('deck_id')}: none")
    lines.extend(
        [
            "",
            "## Readiness",
            "",
            "- ready_for_piti_renderer_contract: true",
            "- ready_for_production_piti_agent: false",
            "- ready_for_broadcast: false",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_default_slide_specs(
    *,
    report_path: Path = DEFAULT_VALIDATION_REPORT,
) -> list[Path]:
    output_paths: list[Path] = []
    results: list[dict[str, Any]] = []
    for case in DEFAULT_CASES:
        storyline = _load_json(case.source_storyline_path)
        spec = build_piti_slide_spec_from_storyline(
            storyline,
            deck_id=case.deck_id,
            source_storyline_path=case.source_storyline_path,
        )
        _write_json(case.output_path, spec)
        output_paths.append(case.output_path)
        result = validate_piti_slide_spec(spec)
        result["priority"] = case.priority
        results.append(result)
    write_validation_report(report_path, results)
    output_paths.append(report_path)
    return output_paths


def validate_default_slide_specs(
    *,
    report_path: Path = DEFAULT_VALIDATION_REPORT,
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for case in DEFAULT_CASES:
        spec = _load_json(case.output_path)
        result = validate_piti_slide_spec(spec)
        result["priority"] = case.priority
        results.append(result)
    write_validation_report(report_path, results)
    return results


@build_app.callback(invoke_without_command=True)
def build_main(
    input_path: Annotated[
        Path | None,
        typer.Option("--input", help="Single Anny storyline JSON to convert."),
    ] = None,
    output_path: Annotated[
        Path | None,
        typer.Option("--output", help="Piti slide spec JSON output path."),
    ] = None,
    deck_id: Annotated[
        str | None,
        typer.Option("--deck-id", help="Deck id for single conversion."),
    ] = None,
    report_path: Annotated[
        Path,
        typer.Option("--report", help="Markdown validation report path."),
    ] = DEFAULT_VALIDATION_REPORT,
) -> None:
    """Build Piti slide spec JSON from Anny storyline JSON."""
    if input_path:
        if output_path is None:
            raise typer.BadParameter("--output is required with --input")
        storyline = _load_json(input_path)
        spec = build_piti_slide_spec_from_storyline(
            storyline,
            deck_id=deck_id or input_path.stem,
            source_storyline_path=input_path,
        )
        _write_json(output_path, spec)
        result = validate_piti_slide_spec(spec)
        console.print(
            f"[green]Wrote {output_path} "
            f"(schema_valid={result['schema_valid']}, passed={result['passed']}).[/green]"
        )
        raise typer.Exit(0 if result["passed"] else 1)
    rendered = build_default_slide_specs(report_path=report_path)
    console.print(f"[green]Built {len(rendered)} Piti slide spec artifacts.[/green]")


@validate_app.callback(invoke_without_command=True)
def validate_main(
    input_path: Annotated[
        Path | None,
        typer.Option("--input", help="Single Piti slide spec JSON to validate."),
    ] = None,
    report_path: Annotated[
        Path,
        typer.Option("--report", help="Markdown validation report path."),
    ] = DEFAULT_VALIDATION_REPORT,
) -> None:
    """Validate Piti slide spec JSON contracts without rendering PPTX."""
    if input_path:
        spec = _load_json(input_path)
        result = validate_piti_slide_spec(spec)
        write_validation_report(report_path, [result])
        console.print(
            f"[green]Validated {input_path} "
            f"(schema_valid={result['schema_valid']}, passed={result['passed']}).[/green]"
        )
        raise typer.Exit(0 if result["passed"] else 1)
    results = validate_default_slide_specs(report_path=report_path)
    console.print(f"[green]Validated {len(results)} Piti slide specs.[/green]")
    raise typer.Exit(0 if all(result["passed"] for result in results) else 1)


if __name__ == "__main__":
    build_app()
