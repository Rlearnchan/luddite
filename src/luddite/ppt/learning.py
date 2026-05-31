"""Rule-based PPT learning pipeline for sample Shukaworld decks."""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import sqlite3
import unicodedata
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import UTC, date, datetime
from difflib import SequenceMatcher
from html.parser import HTMLParser
from pathlib import Path
from typing import Annotated, Any, Protocol
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from urllib.request import Request, urlopen

import typer
from rich.console import Console

from luddite import paths
from luddite.analysis.render_pptx_contact_sheet import (
    ContactSheetResult,
    ContactSheetTarget,
    ThumbnailGenerator,
    render_contact_sheet_target,
)
from luddite.parsers.parse_pptx import parse_presentation
from luddite.utils.jsonl import read_jsonl, write_jsonl

try:  # pragma: no cover - exercised when the optional dependency is installed locally
    from tqdm.auto import tqdm as _tqdm
except ImportError:  # pragma: no cover - fallback keeps tests/lightweight installs working
    _tqdm = None

DEFAULT_MANIFEST = paths.DATA_DIR / "ppt_learning" / "sample_ppts.jsonl"
DRIVE_MANIFEST = paths.DATA_DIR / "ppt_learning" / "drive_ppts.jsonl"
DRIVE_NON_PPT_REPORT_MD = paths.REPORTS_DIR / "ppt_learning_drive_non_ppt_report.md"
PPT_LEARNING_OUTPUT_DIR = paths.OUTPUTS_DIR / "ppt_learning"
INVENTORY_JSONL = PPT_LEARNING_OUTPUT_DIR / "ppt_inventory.jsonl"
SLIDE_SOURCES_JSONL = PPT_LEARNING_OUTPUT_DIR / "ppt_slide_sources.jsonl"
BROADCAST_MATCHES_JSONL = PPT_LEARNING_OUTPUT_DIR / "ppt_broadcast_matches.jsonl"
SEED_LESSONS_JSONL = PPT_LEARNING_OUTPUT_DIR / "jibi_seed_lessons.jsonl"
SEED_LESSON_REVIEW_QUEUE_JSONL = PPT_LEARNING_OUTPUT_DIR / "drive_seed_lesson_review_queue.jsonl"
DRIVE_INVENTORY_JSONL = PPT_LEARNING_OUTPUT_DIR / "drive_ppt_inventory.jsonl"
DRIVE_SLIDE_SOURCES_JSONL = PPT_LEARNING_OUTPUT_DIR / "drive_ppt_slide_sources.jsonl"
DRIVE_BROADCAST_MATCHES_JSONL = PPT_LEARNING_OUTPUT_DIR / "drive_ppt_broadcast_matches.jsonl"
DRIVE_SEED_LESSONS_JSONL = PPT_LEARNING_OUTPUT_DIR / "drive_jibi_seed_lessons.jsonl"
PPT_ENRICHMENT_QUEUE_JSONL = PPT_LEARNING_OUTPUT_DIR / "drive_ppt_enrichment_queue.jsonl"
PPT_ENRICHMENT_URL_QUEUE_JSONL = PPT_LEARNING_OUTPUT_DIR / "drive_ppt_enrichment_url_queue.jsonl"
SOURCE_PAGE_MEMOS_JSONL = PPT_LEARNING_OUTPUT_DIR / "source_page_memos.jsonl"
SOURCE_FETCH_STATUS_JSONL = PPT_LEARNING_OUTPUT_DIR / "source_fetch_status.jsonl"
MANUAL_SOURCE_REQUESTS_JSONL = PPT_LEARNING_OUTPUT_DIR / "manual_source_requests.jsonl"
PPT_SLIDE_VISUAL_RENDER_DIR = PPT_LEARNING_OUTPUT_DIR / "slide_visual_render"
PPT_SLIDE_IMAGES_DIR = PPT_LEARNING_OUTPUT_DIR / "slide_images"
PPT_CONTACT_SHEETS_DIR = PPT_LEARNING_OUTPUT_DIR / "contact_sheets"
SLIDE_VISUAL_MEMOS_JSONL = PPT_LEARNING_OUTPUT_DIR / "slide_visual_memos.jsonl"
PPT_STORY_INPUTS_JSONL = PPT_LEARNING_OUTPUT_DIR / "ppt_story_inputs.jsonl"
PPT_STORY_ARC_MEMOS_JSONL = PPT_LEARNING_OUTPUT_DIR / "ppt_story_arc_memos.jsonl"
INVENTORY_REPORT_MD = paths.REPORTS_DIR / "ppt_learning_inventory_report.md"
BROADCAST_REPORT_MD = paths.REPORTS_DIR / "ppt_broadcast_match_report.md"
SEED_LESSON_REPORT_MD = paths.REPORTS_DIR / "ppt_seed_lesson_report.md"
SEED_LESSON_REVIEW_QUEUE_REPORT_MD = paths.REPORTS_DIR / "ppt_seed_lesson_review_queue.md"
PPT_ENRICHMENT_QUEUE_REPORT_MD = paths.REPORTS_DIR / "ppt_enrichment_queue_report.md"
SOURCE_FETCH_REPORT_MD = paths.REPORTS_DIR / "ppt_source_fetch_report.md"
SLIDE_VISUAL_REPORT_MD = paths.REPORTS_DIR / "ppt_slide_visual_report.md"
PPT_STORY_ARC_REPORT_MD = paths.REPORTS_DIR / "ppt_story_arc_report.md"
PPT_STORY_ARC_REPORT_DIR = paths.REPORTS_DIR / "ppt_story_arcs"
SAMPLE_REPORT_MD = paths.REPORTS_DIR / "ppt_learning_sample_report.md"
DRIVE_REPORT_MD = paths.REPORTS_DIR / "ppt_learning_drive_report.md"
QUALITY_REPORT_MD = paths.REPORTS_DIR / "ppt_learning_drive_quality_report.md"
DEFAULT_SYUKA_DATA_DIR = Path("/Users/bae/Documents/code/syuka-ops/data")

build_drive_manifest_app = typer.Typer(no_args_is_help=False)
build_inventory_app = typer.Typer(no_args_is_help=False)
extract_sources_app = typer.Typer(no_args_is_help=False)
match_broadcast_app = typer.Typer(no_args_is_help=False)
extract_lessons_app = typer.Typer(no_args_is_help=False)
combined_report_app = typer.Typer(no_args_is_help=False)
quality_report_app = typer.Typer(no_args_is_help=False)
enrichment_queue_app = typer.Typer(no_args_is_help=False)
source_fetch_app = typer.Typer(no_args_is_help=False)
slide_visual_app = typer.Typer(no_args_is_help=False)
story_arc_app = typer.Typer(no_args_is_help=False)
console = Console()

DATA_DOMAINS = {
    "data.worldbank.org",
    "documents1.worldbank.org",
    "ilostat.ilo.org",
    "population.un.org",
    "tradingeconomics.com",
    "www.ons.gov.uk",
    "www.nso.gov.vn",
    "www.index.go.kr",
    "fiingroup.vn",
}
OFFICIAL_DATA_DOMAINS = {
    "bok.or.kr",
    "data.worldbank.org",
    "ec.europa.eu",
    "fred.stlouisfed.org",
    "imf.org",
    "ilostat.ilo.org",
    "index.go.kr",
    "korea.kr",
    "oecd.org",
    "sec.gov",
    "statista.com",
    "un.org",
    "worldbank.org",
}
MEDIA_NEWS_DOMAINS = {
    "aljazeera.com",
    "apnews.com",
    "bbc.com",
    "bloomberg.com",
    "businessinsider.com",
    "cnbc.com",
    "cnn.com",
    "economist.com",
    "forbes.com",
    "ft.com",
    "guardian.com",
    "hankyung.com",
    "nikkei.com",
    "nytimes.com",
    "reuters.com",
    "scmp.com",
    "theguardian.com",
    "washingtonpost.com",
    "wsj.com",
    "yna.co.kr",
}
SOCIAL_VIDEO_DOMAINS = {
    "facebook.com",
    "instagram.com",
    "twitter.com",
    "x.com",
    "youtube.com",
}
REFERENCE_DOMAINS = {
    "google.com",
    "namu.wiki",
    "naver.com",
    "wikipedia.org",
}
LIKELY_PAYWALLED_DOMAINS = {
    "bloomberg.com",
    "economist.com",
    "ft.com",
    "nikkei.com",
    "nytimes.com",
    "scmp.com",
    "statista.com",
    "wsj.com",
    "washingtonpost.com",
}
PAYWALL_MARKERS = {
    "already a subscriber",
    "become a subscriber",
    "continue reading",
    "create a free account",
    "digital subscription",
    "login required",
    "log in to continue",
    "paywall",
    "premium article",
    "register for free",
    "sign in to continue",
    "subscribe",
    "subscriber-only",
    "subscription",
    "구독하고 무제한",
    "구독자 전용",
    "로그인 후 이용",
    "로그인 후 계속",
    "회원 전용",
    "유료 기사",
    "유료회원",
}
PAGE_BOILERPLATE_MARKERS = {
    "advertisement",
    "all rights reserved",
    "cookie policy",
    "copyright",
    "newsletter",
    "privacy policy",
    "read more",
    "related article",
    "sign up",
    "terms of service",
    "광고",
    "관련 기사",
    "구독",
    "기사제보",
    "뉴스레터",
    "무단 전재",
    "무단전재",
    "본문 바로가기",
    "저작권",
}
SOURCE_SOFT_ERROR_MARKERS = {
    "404",
    "access denied",
    "error |",
    "forbidden",
    "not found",
    "page not found",
    "page you requested was not found",
    "요청하신 페이지",
    "페이지를 찾을 수 없습니다",
}
SOURCE_VERIFICATION_MARKERS = {
    "captcha",
    "checking your browser",
    "cloudflare",
    "please enable cookies",
    "please wait for verification",
    "verify you are human",
    "verification",
    "로봇이 아닙니다",
    "보안 확인",
    "자동입력 방지",
}
SOURCE_MEMO_BAD_QUALITY_STATUSES = {
    "empty_page",
    "fetch_failed",
    "image_asset_only",
    "login_required",
    "manual_or_auth_required",
    "not_attempted_fetch_limit",
    "soft_error_page",
    "teaser_only",
    "unsupported_content_type",
    "verification_page",
}
IGNORED_MATCH_DOMAINS = {
    "facebook.com",
    "m.youtube.com",
    "www.facebook.com",
    "www.youtube.com",
    "x.com",
    "youtu.be",
    "youtube.com",
}
NUMBER_RE = re.compile(
    r"\b(?:\d[\d,.]*\s?(?:[%％원달러조억만개명건배세년p$]|trillion|million|bn|b)|\d{2,}[\d,.]*)",
    re.I,
)
TRACKING_QUERY_KEYS = {
    "fbclid",
    "gclid",
    "igshid",
    "mc_cid",
    "mc_eid",
}
SOURCE_MEMO_EXCERPT_LIMIT = 420
SOURCE_MEMO_META_LIMIT = 360
SOURCE_MEMO_BODY_READ_LIMIT = 1_200_000
SOURCE_CATEGORY_PRIORITY = {
    "official/data": 70,
    "company/primary": 60,
    "media/news": 50,
    "search/wiki/reference": 25,
    "social/video": 20,
    "other": 10,
}
SOURCE_KIND_PRIORITY = {
    "content_url": 15,
    "image_url": 10,
    "generated_image": 5,
    "unknown": 0,
}
EVIDENCE_TYPE_PRIORITY = {
    "number/statistic": 14,
    "institution/regulation": 13,
    "company": 12,
    "chart/table": 11,
    "quote": 10,
    "person/founder": 9,
    "risk/reversal": 9,
    "local_context": 8,
    "image/proof_object": 6,
    "everyday_object": 6,
    "unknown": 0,
}
REVIEW_BUCKET_PRIORITY = {
    "gold": 0,
    "review": 1,
    "weak": 2,
    "exclude_candidate": 3,
}
MEANINGFUL_NUMBER_UNIT_RE = re.compile(
    r"(?:[%％]|원|달러|조|억|만|개|명|건|배|세|년|p|trillion|million|bn|b|\\$)",
    re.I,
)
TOKEN_RE = re.compile(r"[가-힣A-Za-z][가-힣A-Za-z0-9&.-]{1,}")
ENGLISH_STOPWORDS = {
    "about",
    "after",
    "and",
    "are",
    "from",
    "into",
    "not",
    "the",
    "this",
    "that",
    "with",
}
GENERIC_TERMS = {
    "https",
    "http",
    "www",
    "com",
    "뉴스",
    "최근",
    "이번",
    "회사",
    "기업",
    "시장",
    "한국",
    "대한민국",
    "우리",
    "관련",
    "출처",
    "내용",
    "이미지",
    "자료",
    "것인가",
    "것만",
    "것이",
    "같은",
    "가장",
    "그도",
    "그런데",
    "그렇다면",
    "다른",
    "말하면",
    "문제를",
    "방법",
    "바로",
    "수도",
    "실제로",
    "아니라",
    "아닌",
    "아닐까",
    "역시",
    "요즘",
    "이야기",
    "이렇게",
    "이후",
    "일단",
    "있다",
    "없는",
    "있는",
    "정확히",
    "현재",
    "하면",
    "하는",
    "한다",
    "해서",
}
ALLOWED_SYUKA_CHANNEL_KEYS = {"syukaworld"}
ALLOWED_SYUKA_CHANNEL_NAMES = {"슈카월드"}
TEXT_COLUMN_HINTS = {
    "caption",
    "content",
    "description",
    "dialogue",
    "keywords",
    "keywords_json",
    "summary",
    "text",
    "title",
    "transcript",
}

EVIDENCE_PATTERNS: list[tuple[str, list[str]]] = [
    (
        "person/founder",
        [
            "창업자",
            "founder",
            "ceo",
            "대표",
            "회장",
            "일화",
            "인터뷰",
            "founding",
        ],
    ),
    (
        "company",
        [
            "주식회사",
            "상장",
            "ipo",
            "hose",
            "upcom",
            "기업",
            "회사",
            "체인",
            "매출",
            "f88",
            "inc",
            "corp",
            "ltd",
        ],
    ),
    (
        "institution/regulation",
        [
            "정부",
            "규제",
            "법",
            "제도",
            "감독",
            "거래소",
            "world bank",
            "ilo",
            "oecd",
            "sec",
            "통계청",
            "법원",
            "경찰",
            "금융위",
            "은행",
        ],
    ),
    ("quote", ["“", "”", "\"", "말했다", "발언", "인터뷰", "said", "quote"]),
    ("chart/table", ["차트", "그래프", "표", "table", "chart", "figure", "출처:"]),
    (
        "image/proof_object",
        ["이미지", "사진", "캡처", "스크린샷", "홈페이지", "지도", "로고", "영상"],
    ),
    (
        "everyday_object",
        [
            "오토바이",
            "등록증",
            "담보",
            "반바지",
            "콜라",
            "전당포",
            "휴대폰",
            "집",
            "차",
            "자전거",
            "우유",
            "라면",
            "편의점",
        ],
    ),
    (
        "risk/reversal",
        [
            "리스크",
            "위험",
            "반전",
            "그림자",
            "추심",
            "논란",
            "문제",
            "수사",
            "소송",
            "위기",
            "급락",
            "폭락",
            "채무",
        ],
    ),
    (
        "local_context",
        [
            "한국",
            "국내",
            "우리나라",
            "우리로 치면",
            "베트남",
            "일본",
            "영국",
            "미국",
            "중국",
            "인도",
            "호찌민",
        ],
    ),
]

EVERYDAY_OBJECT_TERMS = [
    "오토바이",
    "등록증",
    "담보",
    "반바지",
    "콜라",
    "전당포",
    "휴대폰",
    "집",
    "차",
    "자전거",
    "우유",
    "라면",
]
RISK_TERMS = ["리스크", "위험", "반전", "그림자", "추심", "논란", "문제", "수사", "소송"]
INSTITUTION_TERMS = [
    "World Bank",
    "ILO",
    "ILOSTAT",
    "정부",
    "규제",
    "법",
    "거래소",
    "통계청",
    "금융위",
    "은행",
    "경찰",
]
PERSON_TERMS = ["창업자", "Founder", "founder", "CEO", "대표", "회장", "일화", "인터뷰"]
KOREA_TERMS = ["한국", "국내", "우리나라", "우리로 치면", "우리도"]
KNOWN_RESEARCHERS = (
    "김동찬",
    "김성원",
    "배형찬",
    "박하눌",
    "유상빈",
    "김예중",
)
PPT_EXTENSIONS = {".pptx", ".ppt"}


@dataclass(frozen=True)
class BroadcastDocument:
    video_id: str
    title: str
    url: str
    upload_date: str
    view_count: int | None
    like_count: int | None
    channel_name: str
    channel_key: str
    fields: dict[str, str]


@dataclass(frozen=True)
class BroadcastDocumentIndex:
    document: BroadcastDocument
    lower_fields: dict[str, str]
    terms_by_field: dict[str, set[str]]
    domains: set[str]


@dataclass(frozen=True)
class SourcePageHttpResponse:
    url: str
    status: int | None
    content_type: str | None
    body: bytes


class SourcePageHttpClient(Protocol):
    def fetch(self, url: str, *, timeout: float) -> SourcePageHttpResponse:
        """Fetch one source URL for source-page memo extraction."""


class UrlLibSourcePageHttpClient:
    def fetch(self, url: str, *, timeout: float) -> SourcePageHttpResponse:
        request = Request(
            url,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (compatible; LudditePPTSourceMemo/1.0; "
                    "+https://github.com/Rlearnchan/luddite)"
                ),
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            },
        )
        try:
            with urlopen(request, timeout=timeout) as response:  # noqa: S310
                return SourcePageHttpResponse(
                    url=response.geturl(),
                    status=response.status,
                    content_type=response.headers.get("content-type"),
                    body=response.read(SOURCE_MEMO_BODY_READ_LIMIT),
                )
        except HTTPError as exc:
            return SourcePageHttpResponse(
                url=exc.url,
                status=exc.code,
                content_type=exc.headers.get("content-type") if exc.headers else None,
                body=exc.read(256_000),
            )
        except URLError as exc:
            raise RuntimeError(str(exc.reason)) from exc


class _SourcePageTextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.title_chunks: list[str] = []
        self.meta_descriptions: list[str] = []
        self.paragraphs: list[str] = []
        self._title_depth = 0
        self._skip_depth = 0
        self._paragraph_depth = 0
        self._current_paragraph: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        attr_map = {key.lower(): value or "" for key, value in attrs}
        if tag == "title":
            self._title_depth += 1
        if tag in {"script", "style", "noscript", "svg"}:
            self._skip_depth += 1
        if tag == "meta":
            key = (
                attr_map.get("name")
                or attr_map.get("property")
                or attr_map.get("itemprop")
                or ""
            ).lower()
            if key in {"description", "og:description", "twitter:description"}:
                self.meta_descriptions.append(_compact(attr_map.get("content", "")))
        if tag == "p" and not self._skip_depth:
            self._paragraph_depth += 1
            self._current_paragraph = []

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag == "p" and self._paragraph_depth:
            paragraph = _compact(" ".join(self._current_paragraph))
            if paragraph and not _is_source_page_boilerplate(paragraph):
                self.paragraphs.append(paragraph)
            self._current_paragraph = []
            self._paragraph_depth = max(0, self._paragraph_depth - 1)
        if tag == "title":
            self._title_depth = max(0, self._title_depth - 1)
        if tag in {"script", "style", "noscript", "svg"} and self._skip_depth:
            self._skip_depth = max(0, self._skip_depth - 1)

    def handle_data(self, data: str) -> None:
        if self._skip_depth:
            return
        if self._title_depth:
            self.title_chunks.append(data)
        if self._paragraph_depth:
            self._current_paragraph.append(data)

    @property
    def title(self) -> str:
        return _compact(" ".join(self.title_chunks))

    @property
    def meta_description(self) -> str:
        return _excerpt(next((item for item in self.meta_descriptions if item), ""), 320)


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _normalize_text(text: str | None) -> str:
    if not text:
        return ""
    text = unicodedata.normalize("NFC", str(text))
    text = text.replace("\xa0", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _compact(text: str | None) -> str:
    return re.sub(r"\s+", " ", _normalize_text(text)).strip()


def _excerpt(text: str | None, limit: int = 420) -> str:
    compact = _compact(text)
    return compact[:limit] + ("..." if len(compact) > limit else "")


def _table_cell(value: Any) -> str:
    return _compact(str(value or "")).replace("|", "\\|")


def _dedupe(values: list[str]) -> list[str]:
    output: list[str] = []
    for value in values:
        if value and value not in output:
            output.append(value)
    return output


def _progress(items: list[Any], *, desc: str, enabled: bool = True) -> Any:
    if not enabled or _tqdm is None:
        return items
    return _tqdm(items, desc=desc, unit="record")


def _repo_relative(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(paths.REPO_ROOT))
    except ValueError:
        return str(path)


def _resolve_local_path(path_text: str | None) -> Path:
    path = Path(path_text or "")
    if path.is_absolute():
        return path
    return paths.REPO_ROOT / path


def _slug(text: str) -> str:
    normalized = re.sub(r"[^A-Za-z0-9가-힣]+", "_", text.lower()).strip("_")
    return normalized or "ppt"


def _manifest_id(item: dict[str, Any]) -> str:
    if item.get("ppt_id"):
        return str(item["ppt_id"])
    title = str(item.get("title") or Path(str(item.get("local_path") or "")).stem)
    return _slug(title)


def _path_modified_iso(path: Path) -> str:
    try:
        return datetime.fromtimestamp(path.stat().st_mtime, UTC).isoformat()
    except OSError:
        return ""


def _folder_date_hint(path: Path) -> str:
    for part in path.parts:
        match = re.search(r"(20\d{2})(\d{2})(\d{2})", part)
        if not match:
            continue
        year, month, day = match.groups()
        return f"{year}-{month}-{day}"
    return ""


def _split_researcher_from_stem(stem: str) -> tuple[str, str]:
    title = re.sub(r"\s+", " ", unicodedata.normalize("NFC", stem)).strip()
    researcher = ""
    if "_" in title:
        left, right = [part.strip() for part in title.rsplit("_", 1)]
        right_names = [name for name in KNOWN_RESEARCHERS if name in right]
        left_names = [name for name in KNOWN_RESEARCHERS if name in left]
        if right_names:
            title = left.strip()
            researcher = " ".join(name for name in KNOWN_RESEARCHERS if name in right)
        elif left in KNOWN_RESEARCHERS:
            title = right.strip()
            researcher = left
        elif left_names and not right_names:
            researcher = " ".join(name for name in KNOWN_RESEARCHERS if name in left)
    if not researcher:
        trailing = re.search(r"\s[- ]\s*(" + "|".join(KNOWN_RESEARCHERS) + r")\b", title)
        if trailing:
            researcher = trailing.group(1)
            title = title[: trailing.start()].strip()
    return title or stem, researcher


def clean_ppt_title(title: str) -> dict[str, Any]:
    clean = _compact(title)
    flags: list[str] = []
    if re.match(r"^[OoＯ]\s+", clean):
        clean = re.sub(r"^[OoＯ]\s+", "", clean).strip()
        flags.append("leading_o")
    if "대표님 예시 자료" in clean:
        flags.append("internal_reference")
    if "재료용" in clean:
        flags.append("material")
    if "수정본" in clean or "수정" in clean:
        flags.append("revision")
    if "최종" in clean:
        flags.append("final_version")
    duplicate_pattern = re.compile(r"(?:\s*\(\d+\))+$")
    if duplicate_pattern.search(clean):
        clean = duplicate_pattern.sub("", clean).strip()
        flags.append("duplicate_copy")
    clean = re.sub(r"\s*[_-]\s*(최종|수정본|수정)$", "", clean).strip()
    clean = re.sub(r"\s+", " ", clean).strip()
    return {"clean_title": clean or _compact(title), "title_flags": _dedupe(flags)}


def _unique_ppt_id(base: str, seen: Counter[str]) -> str:
    seen[base] += 1
    if seen[base] == 1:
        return base
    return f"{base}_{seen[base]}"


def _manifest_row_for_ppt(
    path: Path,
    root: Path,
    source_root: str,
    seen: Counter[str],
) -> dict[str, Any]:
    relative = path.relative_to(root)
    title, researcher = _split_researcher_from_stem(path.stem)
    date_hint = _folder_date_hint(relative)
    path_slug = _slug("_".join(relative.with_suffix("").parts))
    ppt_id = _unique_ppt_id(f"drive_{source_root}_{path_slug}", seen)
    try:
        file_size = path.stat().st_size
    except OSError:
        file_size = 0
    return {
        "ppt_id": ppt_id,
        "title": title,
        "researcher": researcher,
        "local_path": _repo_relative(path),
        "folder_date_hint": date_hint,
        "source_root": source_root,
        "original_folder": str(relative.parent),
        "drive_path_hint": str(relative),
        "file_size_bytes": file_size,
        "modified_at": _path_modified_iso(path),
    }


def build_drive_manifest(
    *,
    latest_root: Path = paths.DATA_DIR / "ppt_learning" / "drive_raw" / "latest",
    past_root: Path = paths.DATA_DIR / "ppt_learning" / "drive_raw" / "past",
    output_jsonl: Path = DRIVE_MANIFEST,
    non_ppt_report_md: Path = DRIVE_NON_PPT_REPORT_MD,
) -> list[dict[str, Any]]:
    roots = [("latest", latest_root), ("past", past_root)]
    rows: list[dict[str, Any]] = []
    non_ppt_files: list[Path] = []
    seen: Counter[str] = Counter()
    for source_root, root in roots:
        if not root.exists():
            continue
        for path in sorted(root.rglob("*")):
            if not path.is_file():
                continue
            if path.suffix.lower() in PPT_EXTENSIONS:
                rows.append(_manifest_row_for_ppt(path, root, source_root, seen))
            else:
                non_ppt_files.append(path)
    write_jsonl(output_jsonl, rows)
    non_ppt_report_md.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# PPT Learning Drive Non-PPT Report",
        "",
        "Files under the Drive raw corpus that were excluded from PPT learning manifest.",
        "",
        f"- latest_root: `{_repo_relative(latest_root)}`",
        f"- past_root: `{_repo_relative(past_root)}`",
        f"- output_manifest: `{_repo_relative(output_jsonl)}`",
        f"- ppt_count: {len(rows)}",
        f"- non_ppt_count: {len(non_ppt_files)}",
        "",
        "## Excluded Files",
        "",
    ]
    if non_ppt_files:
        lines.extend(f"- `{_repo_relative(path)}`" for path in non_ppt_files)
    else:
        lines.append("- none")
    non_ppt_report_md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return rows


def load_sample_manifest(manifest: Path = DEFAULT_MANIFEST) -> list[dict[str, Any]]:
    """Load sample PPT manifest rows without touching Drive."""
    if not manifest.exists():
        return []
    rows: list[dict[str, Any]] = []
    with manifest.open(encoding="utf-8") as source:
        for line_no, line in enumerate(source, start=1):
            if not line.strip():
                continue
            row = json.loads(line)
            row.setdefault("ppt_id", _manifest_id(row))
            row["_manifest_line"] = line_no
            rows.append(row)
    return rows


def _inventory_record(item: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any] | None]:
    ppt_id = _manifest_id(item)
    local_path = _resolve_local_path(str(item.get("local_path") or ""))
    record = {
        "ppt_id": ppt_id,
        "title": str(item.get("title") or local_path.stem),
        "researcher": str(item.get("researcher") or ""),
        "local_path": str(item.get("local_path") or ""),
        "resolved_local_path": str(local_path),
        "drive_path_hint": str(item.get("drive_path_hint") or ""),
        "folder_date_hint": str(item.get("folder_date_hint") or ""),
        "slide_count": 0,
        "local_exists": local_path.exists(),
        "path_status": "local_exists" if local_path.exists() else "missing",
        "extracted_text_status": "missing" if not local_path.exists() else "not_attempted",
        "parsed_at": _now_iso(),
    }
    if not local_path.exists():
        return record, None
    try:
        parsed = parse_presentation(local_path)
    except Exception as exc:  # pragma: no cover - defensive local corpus reporting
        record.update(
            {
                "path_status": "local_exists",
                "extracted_text_status": "failed",
                "parse_error": str(exc),
            }
        )
        return record, None
    has_text = any(
        _compact(slide.get("visible_text")) or _compact(slide.get("notes"))
        for slide in parsed.get("slides", [])
    )
    record.update(
        {
            "slide_count": int(parsed.get("slide_count") or 0),
            "extracted_text_status": "parsed" if has_text else "no_text",
            "unique_url_count": int(parsed.get("unique_url_count") or 0),
            "media_count": int(parsed.get("media_count") or 0),
        }
    )
    return record, parsed


def build_inventory(
    *,
    manifest: Path = DEFAULT_MANIFEST,
    output_jsonl: Path = INVENTORY_JSONL,
    report_md: Path = INVENTORY_REPORT_MD,
) -> list[dict[str, Any]]:
    rows = load_sample_manifest(manifest)
    records = [_inventory_record(item)[0] for item in rows]
    write_jsonl(output_jsonl, records)
    report_md.parent.mkdir(parents=True, exist_ok=True)
    report_md.write_text(_inventory_markdown(records, manifest, output_jsonl), encoding="utf-8")
    return records


def _inventory_markdown(records: list[dict[str, Any]], manifest: Path, output_jsonl: Path) -> str:
    counts = Counter(str(item.get("path_status")) for item in records)
    lines = [
        "# PPT Learning Inventory Report",
        "",
        "Sample-manifest based inventory. No Google Drive traversal was performed.",
        "",
        "## Summary",
        "",
        f"- manifest: `{_repo_relative(manifest)}`",
        f"- output_jsonl: `{_repo_relative(output_jsonl)}`",
        f"- sample_ppt_count: {len(records)}",
        f"- local_exists: {counts.get('local_exists', 0)}",
        f"- missing: {counts.get('missing', 0)}",
        "",
        "## Inventory",
        "",
        "| ppt_id | title | researcher | status | slides | text_status | folder_date_hint |",
        "| --- | --- | --- | --- | ---: | --- | --- |",
    ]
    for item in records:
        lines.append(
            "| "
            + " | ".join(
                [
                    _table_cell(item.get("ppt_id")),
                    _table_cell(item.get("title")),
                    _table_cell(item.get("researcher")),
                    _table_cell(item.get("path_status")),
                    str(item.get("slide_count", 0)),
                    _table_cell(item.get("extracted_text_status")),
                    _table_cell(item.get("folder_date_hint")),
                ]
            )
            + " |"
        )
    missing = [item for item in records if not item.get("local_exists")]
    lines.extend(["", "## Missing Files", ""])
    if missing:
        lines.extend(f"- `{item.get('local_path')}`" for item in missing)
    else:
        lines.append("- none")
    return "\n".join(lines) + "\n"


def _domain(url: str | None) -> str:
    if not url:
        return ""
    return urlsplit(url).netloc.lower()


def canonical_domain(value: str | None) -> str:
    text = str(value or "").strip().lower()
    if not text:
        return ""
    domain = _domain(text) if "://" in text else text.split("/")[0]
    domain = domain.split("@")[-1].split(":")[0].strip(".")
    for prefix in ("www.", "m.", "mobile."):
        if domain.startswith(prefix):
            domain = domain[len(prefix) :]
    if domain == "youtu.be" or domain.endswith(".youtube.com"):
        return "youtube.com"
    if domain == "twitter.com":
        return "x.com"
    if domain.endswith(".wikipedia.org"):
        return "wikipedia.org"
    if domain.endswith(".worldbank.org"):
        return "worldbank.org"
    return domain


def source_domain_category(value: str | None) -> str:
    domain = canonical_domain(value)
    if not domain:
        return "unknown"
    if domain in SOCIAL_VIDEO_DOMAINS or any(
        domain.endswith(f".{item}") for item in SOCIAL_VIDEO_DOMAINS
    ):
        return "social/video"
    if domain in OFFICIAL_DATA_DOMAINS or any(
        token in domain for token in ["gov", "go.kr", "stat", "data.", "worldbank"]
    ):
        return "official/data"
    if domain in MEDIA_NEWS_DOMAINS or any(domain.endswith(f".{d}") for d in MEDIA_NEWS_DOMAINS):
        return "media/news"
    if domain in REFERENCE_DOMAINS or any(domain.endswith(f".{d}") for d in REFERENCE_DOMAINS):
        return "search/wiki/reference"
    return "company/primary" if "." in domain else "other"


def normalize_url_for_queue(url: str | None) -> str:
    text = str(url or "").strip()
    if not text:
        return ""
    if not re.match(r"^[a-z][a-z0-9+.-]*://", text, flags=re.I):
        text = f"https://{text}" if "." in text.split("/")[0] else text
    parts = urlsplit(text)
    if not parts.netloc:
        return text
    filtered_query = [
        (key, value)
        for key, value in parse_qsl(parts.query, keep_blank_values=True)
        if not key.lower().startswith("utm_") and key.lower() not in TRACKING_QUERY_KEYS
    ]
    path = parts.path.rstrip("/") if parts.path != "/" else parts.path
    return urlunsplit(
        (
            parts.scheme.lower() or "https",
            parts.netloc.lower(),
            path,
            urlencode(filtered_query, doseq=True),
            "",
        )
    )


def source_access_hint(domain: str | None, category: str | None = None) -> str:
    canonical = canonical_domain(domain)
    if not canonical:
        return "unknown"
    if canonical in LIKELY_PAYWALLED_DOMAINS or any(
        canonical.endswith(f".{item}") for item in LIKELY_PAYWALLED_DOMAINS
    ):
        return "likely_paywalled"
    category = category or source_domain_category(canonical)
    if category == "social/video":
        return "browser_or_manual_check"
    if category == "search/wiki/reference":
        return "public_fetch_low_priority"
    return "likely_public"


def source_collection_hint(access_hint: str) -> str:
    if access_hint == "likely_paywalled":
        return "manual_or_authenticated_session"
    if access_hint == "browser_or_manual_check":
        return "browser_or_manual_check"
    if access_hint == "public_fetch_low_priority":
        return "optional_public_fetch"
    if access_hint == "likely_public":
        return "public_fetch_first"
    return "manual_check"


def infer_source_kind(
    *,
    label: str = "",
    value: str = "",
    url: str = "",
    is_image: bool = False,
    is_generated: bool = False,
) -> str:
    lower_label = label.lower()
    lower_value = value.lower()
    domain = _domain(url)
    if is_generated or "gpt 생성" in lower_value or "generated" in lower_value:
        return "generated_image"
    if is_image or "이미지" in lower_label or "사진" in lower_label:
        return "image_url"
    if "데이터" in lower_label or "자료" in lower_label or "통계" in lower_label:
        return "data_url"
    if domain in DATA_DOMAINS or any(token in domain for token in ["data", "stat", "worldbank"]):
        return "data_url"
    if "내용" in label or "출처" in label or "source" in lower_label:
        return "content_url"
    if url:
        return "content_url"
    return "unknown"


def infer_evidence_types(
    text: str,
    *,
    source_kind: str = "",
    media_count: int = 0,
    slide_type: str = "",
    domains: list[str] | None = None,
) -> list[str]:
    compact = _compact(text)
    lower = compact.lower()
    evidence: list[str] = []
    if NUMBER_RE.search(compact):
        evidence.append("number/statistic")
    for evidence_type, patterns in EVIDENCE_PATTERNS:
        if any(pattern.lower() in lower for pattern in patterns):
            evidence.append(evidence_type)
    if source_kind in {"image_url", "generated_image"} or media_count > 0:
        evidence.append("image/proof_object")
    if slide_type in {"data", "source_heavy"}:
        evidence.append("number/statistic")
    if domains and any(domain in DATA_DOMAINS for domain in domains):
        evidence.append("number/statistic")
    return _dedupe(evidence) or ["unknown"]


def _source_entry(
    *,
    slide: dict[str, Any],
    label: str,
    value: str,
    url: str,
    is_image: bool,
    is_generated: bool,
) -> dict[str, Any]:
    source_kind = infer_source_kind(
        label=label,
        value=value,
        url=url,
        is_image=is_image,
        is_generated=is_generated,
    )
    domain = _domain(url)
    text = "\n".join(
        [
            str(slide.get("headline") or ""),
            str(slide.get("visible_text") or ""),
            str(value or ""),
            str(slide.get("notes") or ""),
        ]
    )
    evidence_types = infer_evidence_types(
        text,
        source_kind=source_kind,
        media_count=int(slide.get("media_count") or 0),
        slide_type=str(slide.get("slide_type") or ""),
        domains=[domain] if domain else [],
    )
    return {
        "source_kind": source_kind,
        "source_note_label": label,
        "source_note_value": _excerpt(value, 500),
        "source_note_group": (
            "image" if source_kind in {"image_url", "generated_image"} else "content"
        ),
        "url": url,
        "url_domain": domain,
        "evidence_type": evidence_types[0],
        "evidence_types": evidence_types,
    }


def slide_source_record(
    *,
    item: dict[str, Any],
    slide: dict[str, Any],
) -> dict[str, Any]:
    entries: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for note in slide.get("source_notes") or []:
        urls = note.get("urls") or [""]
        for url in urls:
            entry = _source_entry(
                slide=slide,
                label=str(note.get("label") or ""),
                value=str(note.get("value") or ""),
                url=str(url or ""),
                is_image=bool(note.get("is_image")),
                is_generated=bool(note.get("is_gpt_generated")),
            )
            key = (entry["source_note_label"], entry["url"])
            if key not in seen:
                seen.add(key)
                entries.append(entry)
    noted_urls = {entry["url"] for entry in entries if entry["url"]}
    extra_urls: list[str] = []
    for key in ["text_urls", "notes_urls", "relationship_urls", "all_urls"]:
        for url in slide.get(key) or []:
            if url and url not in noted_urls:
                extra_urls.append(str(url))
    for url in _dedupe(extra_urls):
        entry = _source_entry(
            slide=slide,
            label="",
            value=url,
            url=url,
            is_image=False,
            is_generated=False,
        )
        key = ("", entry["url"])
        if key not in seen:
            seen.add(key)
            entries.append(entry)

    urls = _dedupe([entry["url"] for entry in entries if entry["url"]])
    domains = _dedupe([entry["url_domain"] for entry in entries if entry["url_domain"]])
    evidence_types = _dedupe(
        [evidence for entry in entries for evidence in entry.get("evidence_types", [])]
    )
    if not evidence_types:
        evidence_types = infer_evidence_types(
            "\n".join([str(slide.get("visible_text") or ""), str(slide.get("notes") or "")]),
            media_count=int(slide.get("media_count") or 0),
            slide_type=str(slide.get("slide_type") or ""),
            domains=domains,
        )
    return {
        "ppt_id": _manifest_id(item),
        "ppt_title": str(item.get("title") or ""),
        "researcher": str(item.get("researcher") or ""),
        "local_path": str(item.get("local_path") or ""),
        "slide_number": int(slide.get("slide_no") or 0),
        "slide_title": str(slide.get("headline") or ""),
        "raw_text_excerpt": _excerpt(slide.get("visible_text"), 600),
        "notes_excerpt": _excerpt(slide.get("notes"), 600),
        "extracted_urls": urls,
        "url_domains": domains,
        "source_entries": entries,
        "evidence_type": evidence_types[0],
        "evidence_types": evidence_types,
        "media_count": int(slide.get("media_count") or 0),
        "slide_type": str(slide.get("slide_type") or ""),
        "extraction_status": "parsed",
    }


def extract_slide_sources_from_parsed(
    item: dict[str, Any],
    parsed: dict[str, Any],
) -> list[dict[str, Any]]:
    return [slide_source_record(item=item, slide=slide) for slide in parsed.get("slides", [])]


def extract_slide_sources(
    *,
    manifest: Path = DEFAULT_MANIFEST,
    output_jsonl: Path = SLIDE_SOURCES_JSONL,
) -> list[dict[str, Any]]:
    rows = load_sample_manifest(manifest)
    records: list[dict[str, Any]] = []
    for item in rows:
        local_path = _resolve_local_path(str(item.get("local_path") or ""))
        if not local_path.exists():
            records.append(_missing_slide_source_record(item, "missing"))
            continue
        try:
            parsed = parse_presentation(local_path)
        except Exception as exc:  # pragma: no cover - defensive local corpus reporting
            missing = _missing_slide_source_record(item, "failed")
            missing["parse_error"] = str(exc)
            records.append(missing)
            continue
        records.extend(extract_slide_sources_from_parsed(item, parsed))
    write_jsonl(output_jsonl, records)
    return records


def _missing_slide_source_record(item: dict[str, Any], status: str) -> dict[str, Any]:
    return {
        "ppt_id": _manifest_id(item),
        "ppt_title": str(item.get("title") or ""),
        "researcher": str(item.get("researcher") or ""),
        "local_path": str(item.get("local_path") or ""),
        "slide_number": None,
        "slide_title": "",
        "raw_text_excerpt": "",
        "notes_excerpt": "",
        "extracted_urls": [],
        "url_domains": [],
        "source_entries": [],
        "evidence_type": "unknown",
        "evidence_types": ["unknown"],
        "media_count": 0,
        "slide_type": "",
        "extraction_status": status,
    }


def _discover_sqlite_dbs(data_dir: Path) -> list[Path]:
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
    conn = sqlite3.connect(f"file:{db_path.resolve()}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def _table_columns(conn: sqlite3.Connection, table: str) -> list[str]:
    return [str(row[1]) for row in conn.execute(f'PRAGMA table_info("{table}")')]


def _inspect_tables(db_path: Path) -> dict[str, list[str]]:
    try:
        with _connect_readonly(db_path) as conn:
            tables = [
                str(row[0])
                for row in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
                )
            ]
            return {table: _table_columns(conn, table) for table in tables}
    except sqlite3.Error:
        return {}


def _choose_snapshot_db(data_dir: Path) -> tuple[Path | None, dict[str, list[str]], str]:
    dbs = _discover_sqlite_dbs(data_dir)
    if not dbs:
        return None, {}, "no_db_found"
    for db_path in dbs:
        tables = _inspect_tables(db_path)
        if tables:
            return db_path, tables, "usable"
    return dbs[0], {}, "unreadable"


def _row_value(row: sqlite3.Row, column: str) -> str:
    if column not in row.keys():
        return ""
    value = row[column]
    return "" if value is None else str(value)


def _safe_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _text_columns(columns: list[str]) -> list[str]:
    output: list[str] = []
    for column in columns:
        lower = column.lower()
        if any(hint in lower for hint in TEXT_COLUMN_HINTS):
            output.append(column)
    return output


def _load_broadcast_documents(
    db_path: Path | None,
    tables: dict[str, list[str]],
) -> list[BroadcastDocument]:
    if db_path is None or not tables:
        return []
    with _connect_readonly(db_path) as conn:
        docs = _load_standard_broadcast_documents(conn, tables)
        return docs or _load_generic_broadcast_documents(conn, tables)


def _load_standard_broadcast_documents(
    conn: sqlite3.Connection,
    tables: dict[str, list[str]],
) -> list[BroadcastDocument]:
    video_columns = tables.get("videos") or []
    if "video_id" not in video_columns:
        return []
    docs: dict[str, BroadcastDocument] = {}
    for row in conn.execute('SELECT * FROM "videos"'):
        video_id = _row_value(row, "video_id")
        if not video_id:
            continue
        docs[video_id] = BroadcastDocument(
            video_id=video_id,
            title=_row_value(row, "title"),
            url=_row_value(row, "source_url"),
            upload_date=_row_value(row, "upload_date"),
            view_count=_safe_int(row["view_count"]) if "view_count" in row.keys() else None,
            like_count=_safe_int(row["like_count"]) if "like_count" in row.keys() else None,
            channel_name=_row_value(row, "channel_name"),
            channel_key=_row_value(row, "channel_key"),
            fields={
                "title": _row_value(row, "title"),
                "metadata": " ".join(
                    _row_value(row, column)
                    for column in ["channel_name", "channel_key", "upload_date", "source_url"]
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
                for column in ["summary", "keywords_json", "description"]
                if column in row.keys()
            )
            docs[video_id] = _replace_document_fields(docs[video_id], fields)
    if "transcripts" in tables and "video_id" in tables["transcripts"]:
        transcript_columns = tables["transcripts"]
        for row in conn.execute('SELECT * FROM "transcripts"'):
            video_id = _row_value(row, "video_id")
            if video_id not in docs:
                continue
            fields = dict(docs[video_id].fields)
            fields["transcript"] = " ".join(
                _row_value(row, column)
                for column in ["dialogue", "transcript", "text", "caption"]
                if column in transcript_columns
            )
            docs[video_id] = _replace_document_fields(docs[video_id], fields)
    return list(docs.values())


def _replace_document_fields(
    document: BroadcastDocument,
    fields: dict[str, str],
) -> BroadcastDocument:
    return BroadcastDocument(
        video_id=document.video_id,
        title=document.title,
        url=document.url,
        upload_date=document.upload_date,
        view_count=document.view_count,
        like_count=document.like_count,
        channel_name=document.channel_name,
        channel_key=document.channel_key,
        fields=fields,
    )


def _load_generic_broadcast_documents(
    conn: sqlite3.Connection,
    tables: dict[str, list[str]],
) -> list[BroadcastDocument]:
    docs: list[BroadcastDocument] = []
    for table, columns in tables.items():
        text_columns = _text_columns(columns)
        if not text_columns:
            continue
        id_column = "video_id" if "video_id" in columns else columns[0]
        title_column = "title" if "title" in columns else text_columns[0]
        for index, row in enumerate(conn.execute(f'SELECT * FROM "{table}"'), start=1):
            video_id = _row_value(row, id_column) or f"{table}:{index}"
            fields = {"title": _row_value(row, title_column)}
            fields["analysis"] = " ".join(_row_value(row, column) for column in text_columns)
            docs.append(
                BroadcastDocument(
                    video_id=video_id,
                    title=_row_value(row, title_column) or video_id,
                    url=_row_value(row, "source_url") if "source_url" in columns else "",
                    upload_date=_row_value(row, "upload_date") if "upload_date" in columns else "",
                    view_count=_safe_int(row["view_count"]) if "view_count" in columns else None,
                    like_count=_safe_int(row["like_count"]) if "like_count" in columns else None,
                    channel_name=_row_value(row, "channel_name")
                    if "channel_name" in columns
                    else "",
                    channel_key=_row_value(row, "channel_key") if "channel_key" in columns else "",
                    fields=fields,
                )
            )
    return docs


def _is_syukaworld(document: BroadcastDocument) -> bool:
    channel_key = document.channel_key.strip().lower()
    channel_name = document.channel_name.strip()
    if not channel_key and not channel_name:
        return True
    return channel_key in ALLOWED_SYUKA_CHANNEL_KEYS or channel_name in ALLOWED_SYUKA_CHANNEL_NAMES


def _parse_date(value: Any) -> date | None:
    text = str(value or "").strip()
    for fmt in ("%Y-%m-%d", "%Y%m%d", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def _normalized_similarity(left: str, right: str) -> float:
    left_norm = re.sub(r"\s+", "", left.lower())
    right_norm = re.sub(r"\s+", "", right.lower())
    if not left_norm or not right_norm:
        return 0.0
    return SequenceMatcher(None, left_norm, right_norm).ratio()


def _terms_from_text(text: str, limit: int = 40) -> list[str]:
    counts: Counter[str] = Counter()
    for token in TOKEN_RE.findall(text):
        lower = token.lower().strip(".-")
        if len(lower) < 2:
            continue
        if lower in ENGLISH_STOPWORDS or lower in GENERIC_TERMS:
            continue
        if lower.isdigit():
            continue
        counts[lower] += 1
    return [term for term, _ in counts.most_common(limit)]


def _term_set_from_text(text: str) -> set[str]:
    terms: set[str] = set()
    for token in TOKEN_RE.findall(text):
        lower = token.lower().strip(".-")
        if len(lower) < 2:
            continue
        if lower in ENGLISH_STOPWORDS or lower in GENERIC_TERMS:
            continue
        if lower.isdigit():
            continue
        terms.add(lower)
    return terms


def _domains_from_text(text: str) -> set[str]:
    domains: set[str] = set()
    for url in re.findall(r"https?://[^\s)>\]]+", text):
        domain = _domain(url)
        if domain:
            domains.add(domain)
    return domains


def _index_broadcast_documents(documents: list[BroadcastDocument]) -> list[BroadcastDocumentIndex]:
    indexed: list[BroadcastDocumentIndex] = []
    for document in documents:
        lower_fields = {
            field: document.fields.get(field, "").lower()
            for field in ["title", "analysis", "transcript", "metadata"]
        }
        terms_by_field = {
            field: _term_set_from_text(text)
            for field, text in lower_fields.items()
        }
        domain_text = "\n".join([document.url, *document.fields.values()])
        domains = _domains_from_text(domain_text)
        document_domain = _domain(document.url)
        if document_domain:
            domains.add(document_domain)
        indexed.append(
            BroadcastDocumentIndex(
                document=document,
                lower_fields=lower_fields,
                terms_by_field=terms_by_field,
                domains=domains,
            )
        )
    return indexed


def _contains_term(text: str, term: str) -> bool:
    lower = text.lower()
    if re.fullmatch(r"[a-z0-9.-]+", term):
        return bool(re.search(rf"\b{re.escape(term)}\b", lower))
    return term in lower


def _keyword_profile(item: dict[str, Any], parsed: dict[str, Any]) -> dict[str, Any]:
    title = str(item.get("title") or parsed.get("title") or "")
    early_text = "\n".join(
        str(slide.get("visible_text") or "")
        for slide in parsed.get("slides", [])[:10]
    )
    all_text = "\n".join(
        [
            title,
            early_text,
            "\n".join(str(slide.get("headline") or "") for slide in parsed.get("slides", [])),
        ]
    )
    terms = _dedupe([*_terms_from_text(title, 12), *_terms_from_text(all_text, 40)])
    domains = _dedupe([_domain(url) for url in parsed.get("urls", []) if _domain(url)])
    return {"terms": terms, "domains": domains, "title": title, "early_text": early_text}


def _match_document(
    *,
    item: dict[str, Any],
    profile: dict[str, Any],
    document: BroadcastDocument,
) -> dict[str, Any]:
    title_similarity = _normalized_similarity(profile["title"], document.title)
    terms = profile["terms"]
    field_hits: dict[str, list[str]] = {}
    for field in ["title", "analysis", "transcript", "metadata"]:
        text = document.fields.get(field, "")
        hits = [term for term in terms if _contains_term(text, term)]
        if hits:
            field_hits[field] = hits
    domain_hits = [
        domain
        for domain in profile["domains"]
        if domain and domain not in IGNORED_MATCH_DOMAINS
    ]
    domain_hits = [
        domain
        for domain in domain_hits
        if domain and any(domain in value.lower() for value in document.fields.values())
    ]
    folder_date = _parse_date(item.get("folder_date_hint"))
    upload_date = _parse_date(document.upload_date)
    days_apart = abs((upload_date - folder_date).days) if upload_date and folder_date else None
    matched_signals: list[str] = []
    if title_similarity >= 0.42:
        matched_signals.append("title_similarity")
    if len(field_hits.get("transcript", [])) >= 2:
        matched_signals.append("transcript_overlap")
    if field_hits.get("analysis") or field_hits.get("title") or domain_hits:
        matched_signals.append("url_keyword_overlap")
    if days_apart is not None and days_apart <= 45:
        matched_signals.append("date_proximity")
    if _is_syukaworld(document):
        matched_signals.append("syukaworld_channel")
    else:
        matched_signals.append("non_syukaworld_channel")
    weighted_hits = (
        len(field_hits.get("title", [])) * 3
        + len(field_hits.get("analysis", [])) * 2
        + len(field_hits.get("transcript", []))
        + len(domain_hits) * 2
    )
    date_bonus = (
        2
        if days_apart is not None and days_apart <= 14
        else 1
        if days_apart is not None and days_apart <= 45
        else 0
    )
    score = title_similarity * 10 + weighted_hits + date_bonus
    return {
        "document": document,
        "score": round(score, 3),
        "title_similarity": round(title_similarity, 3),
        "matched_signals": matched_signals,
        "matched_fields": sorted(field_hits),
        "matched_terms": _dedupe([term for hits in field_hits.values() for term in hits])[:20],
        "matched_domains": domain_hits[:20],
        "days_apart": days_apart,
    }


def _match_indexed_document(
    *,
    item: dict[str, Any],
    profile: dict[str, Any],
    indexed: BroadcastDocumentIndex,
) -> dict[str, Any]:
    document = indexed.document
    title_similarity = _normalized_similarity(profile["title"], document.title)
    terms = profile["terms"]
    field_hits: dict[str, list[str]] = {}
    for field in ["title", "analysis", "transcript", "metadata"]:
        term_set = indexed.terms_by_field.get(field, set())
        hits = [term for term in terms if term in term_set]
        if field in {"title", "analysis", "metadata"}:
            lower_text = indexed.lower_fields.get(field, "")
            hits.extend(term for term in terms if term not in hits and term in lower_text)
        if hits:
            field_hits[field] = hits
    domain_hits = [
        domain
        for domain in profile["domains"]
        if domain and domain not in IGNORED_MATCH_DOMAINS and domain in indexed.domains
    ]
    folder_date = _parse_date(item.get("folder_date_hint"))
    upload_date = _parse_date(document.upload_date)
    days_apart = abs((upload_date - folder_date).days) if upload_date and folder_date else None
    matched_signals: list[str] = []
    if title_similarity >= 0.42:
        matched_signals.append("title_similarity")
    if len(field_hits.get("transcript", [])) >= 2:
        matched_signals.append("transcript_overlap")
    if field_hits.get("analysis") or field_hits.get("title") or domain_hits:
        matched_signals.append("url_keyword_overlap")
    if days_apart is not None and days_apart <= 45:
        matched_signals.append("date_proximity")
    if _is_syukaworld(document):
        matched_signals.append("syukaworld_channel")
    else:
        matched_signals.append("non_syukaworld_channel")
    weighted_hits = (
        len(field_hits.get("title", [])) * 3
        + len(field_hits.get("analysis", [])) * 2
        + len(field_hits.get("transcript", []))
        + len(domain_hits) * 2
    )
    date_bonus = (
        2
        if days_apart is not None and days_apart <= 14
        else 1
        if days_apart is not None and days_apart <= 45
        else 0
    )
    score = title_similarity * 10 + weighted_hits + date_bonus
    return {
        "document": document,
        "score": round(score, 3),
        "title_similarity": round(title_similarity, 3),
        "matched_signals": matched_signals,
        "matched_fields": sorted(field_hits),
        "matched_terms": _dedupe([term for hits in field_hits.values() for term in hits])[:20],
        "matched_domains": domain_hits[:20],
        "days_apart": days_apart,
    }


def _broadcast_label(candidate: dict[str, Any] | None) -> tuple[str, str]:
    if not candidate:
        return "not_found", "low"
    signals = set(candidate["matched_signals"])
    score = float(candidate["score"])
    title_similarity = float(candidate["title_similarity"])
    transcript_hits = "transcript_overlap" in signals
    date_hit = "date_proximity" in signals
    keyword_hit = "url_keyword_overlap" in signals
    days_apart = candidate.get("days_apart")
    stale_date = days_apart is not None and int(days_apart) > 90
    if title_similarity >= 0.82 and transcript_hits and date_hit:
        return "broadcast_confirmed", "high"
    strong_signals = {"title_similarity", "transcript_overlap", "date_proximity"}
    if date_hit and score >= 12 and len(signals & strong_signals) >= 2:
        return "likely_used", "high"
    if date_hit and (
        score >= 8 or (title_similarity >= 0.52 and (keyword_hit or transcript_hits))
    ):
        return "likely_used", "medium"
    if stale_date and title_similarity < 0.6:
        return "not_found", "low"
    if (
        title_similarity >= 0.42
        or (date_hit and keyword_hit)
        or (transcript_hits and score >= 14)
    ):
        return "maybe_used", "low"
    return "not_found", "low"


def match_ppt_to_broadcasts(
    item: dict[str, Any],
    parsed: dict[str, Any] | None,
    document_index: list[BroadcastDocumentIndex],
    *,
    snapshot_status: str,
) -> dict[str, Any]:
    ppt_id = _manifest_id(item)
    if parsed is None:
        return {
            "ppt_id": ppt_id,
            "ppt_title": str(item.get("title") or ""),
            "broadcast_label": "not_found",
            "matched_video_id": "",
            "matched_video_title": "",
            "upload_date": "",
            "view_count": 0,
            "like_count": 0,
            "matched_signals": [],
            "confidence": "low",
            "notes": "PPT missing or parse failed; broadcast matching skipped.",
            "snapshot_status": snapshot_status,
        }
    profile = _keyword_profile(item, parsed)
    candidates = [
        _match_indexed_document(item=item, profile=profile, indexed=indexed)
        for indexed in document_index
    ]
    candidates.sort(key=lambda candidate: float(candidate["score"]), reverse=True)
    syuka_candidates = [
        candidate for candidate in candidates if _is_syukaworld(candidate["document"])
    ]
    non_syuka_candidates = [
        candidate for candidate in candidates if not _is_syukaworld(candidate["document"])
    ]
    best_syuka = syuka_candidates[0] if syuka_candidates else None
    label, confidence = _broadcast_label(best_syuka)
    if label == "not_found" and non_syuka_candidates:
        non_label, _non_confidence = _broadcast_label(non_syuka_candidates[0])
        if non_label in {"broadcast_confirmed", "likely_used", "maybe_used"}:
            best_syuka = non_syuka_candidates[0]
            label = "excluded_non_syukaworld"
            confidence = "low"
    if not best_syuka or label == "not_found":
        return {
            "ppt_id": ppt_id,
            "ppt_title": profile["title"],
            "broadcast_label": "not_found",
            "matched_video_id": "",
            "matched_video_title": "",
            "upload_date": "",
            "view_count": 0,
            "like_count": 0,
            "matched_signals": [],
            "confidence": "low",
            "notes": "No meaningful local Syukaworld snapshot match.",
            "snapshot_status": snapshot_status,
            "query_terms": profile["terms"][:20],
        }
    document = best_syuka["document"]
    return {
        "ppt_id": ppt_id,
        "ppt_title": profile["title"],
        "broadcast_label": label,
        "matched_video_id": document.video_id,
        "matched_video_title": document.title,
        "upload_date": document.upload_date,
        "view_count": document.view_count or 0,
        "like_count": document.like_count or 0,
        "matched_signals": best_syuka["matched_signals"],
        "matched_terms": best_syuka["matched_terms"],
        "matched_domains": best_syuka["matched_domains"],
        "title_similarity": best_syuka["title_similarity"],
        "match_score": best_syuka["score"],
        "days_apart": best_syuka["days_apart"],
        "confidence": confidence,
        "notes": (
            "Non-Syukaworld match excluded from positive usage."
            if label == "excluded_non_syukaworld"
            else "Rule-based local snapshot estimate."
        ),
        "snapshot_status": snapshot_status,
        "query_terms": profile["terms"][:20],
    }


def match_broadcast_usage(
    *,
    manifest: Path = DEFAULT_MANIFEST,
    syuka_data_dir: Path = DEFAULT_SYUKA_DATA_DIR,
    output_jsonl: Path = BROADCAST_MATCHES_JSONL,
    report_md: Path = BROADCAST_REPORT_MD,
) -> list[dict[str, Any]]:
    db_path, tables, snapshot_status = _choose_snapshot_db(syuka_data_dir)
    documents = _load_broadcast_documents(db_path, tables)
    document_index = _index_broadcast_documents(documents)
    rows = load_sample_manifest(manifest)
    records: list[dict[str, Any]] = []
    for item in rows:
        local_path = _resolve_local_path(str(item.get("local_path") or ""))
        parsed = None
        if local_path.exists():
            try:
                parsed = parse_presentation(local_path)
            except Exception:  # pragma: no cover - defensive local corpus reporting
                parsed = None
        records.append(
            match_ppt_to_broadcasts(
                item,
                parsed,
                document_index,
                snapshot_status=snapshot_status,
            )
        )
    write_jsonl(output_jsonl, records)
    report_md.parent.mkdir(parents=True, exist_ok=True)
    report_md.write_text(
        _broadcast_markdown(
            records=records,
            manifest=manifest,
            output_jsonl=output_jsonl,
            syuka_data_dir=syuka_data_dir,
            db_path=db_path,
            snapshot_status=snapshot_status,
            document_count=len(documents),
        ),
        encoding="utf-8",
    )
    _maybe_write_sample_report()
    return records


def _broadcast_markdown(
    *,
    records: list[dict[str, Any]],
    manifest: Path,
    output_jsonl: Path,
    syuka_data_dir: Path,
    db_path: Path | None,
    snapshot_status: str,
    document_count: int,
) -> str:
    counts = Counter(str(item.get("broadcast_label") or "unknown") for item in records)
    lines = [
        "# PPT Broadcast Match Report",
        "",
        "Read-only local syuka snapshot estimate. Money Comics and other non-Syukaworld "
        "channels are excluded from positive matches.",
        "",
        "## Snapshot",
        "",
        f"- manifest: `{_repo_relative(manifest)}`",
        f"- output_jsonl: `{_repo_relative(output_jsonl)}`",
        f"- syuka_data_dir: `{syuka_data_dir}`",
        f"- db_path: `{db_path or ''}`",
        f"- snapshot_status: {snapshot_status}",
        f"- document_count: {document_count}",
        "",
        "## Label Distribution",
        "",
        *[f"- {label}: {count}" for label, count in sorted(counts.items())],
        "",
        "## Matches",
        "",
        "| ppt | label | confidence | matched video | date | score | signals |",
        "| --- | --- | --- | --- | --- | ---: | --- |",
    ]
    for item in records:
        lines.append(
            "| "
            + " | ".join(
                [
                    _table_cell(item.get("ppt_title")),
                    _table_cell(item.get("broadcast_label")),
                    _table_cell(item.get("confidence")),
                    _table_cell(item.get("matched_video_title")),
                    _table_cell(item.get("upload_date")),
                    str(item.get("match_score") or 0),
                    _table_cell(", ".join(item.get("matched_signals", []))),
                ]
            )
            + " |"
        )
    return "\n".join(lines) + "\n"


def _line_snippets(text: str, terms: list[str], limit: int = 8) -> list[str]:
    snippets: list[str] = []
    for line in _normalize_text(text).splitlines():
        compact = _compact(line)
        if not compact:
            continue
        lower = compact.lower()
        if any(term.lower() in lower for term in terms):
            snippets.append(_excerpt(compact, 180))
        if len(snippets) >= limit:
            break
    return _dedupe(snippets)


def clean_number_token(token: str) -> str:
    text = _compact(token)
    if not text:
        return ""
    text = text.replace("％", "%")
    text = re.sub(r"\s+", "", text)
    text = re.sub(r"(\d),만", r"\1만", text)
    text = text.strip(" ,.;:")
    digits = re.sub(r"\D", "", text)
    has_unit = bool(MEANINGFUL_NUMBER_UNIT_RE.search(text))
    if re.fullmatch(r"20\d{2}[%pP]", text):
        return ""
    if re.fullmatch(r"\d{1,2}(?:[.,]\d{1,2})+", text):
        return ""
    if len(digits) >= 12:
        return ""
    if re.fullmatch(r"20\d{8,}", digits):
        return ""
    if re.fullmatch(r"\d{1,2}", digits) and not has_unit:
        return ""
    if re.fullmatch(r"\d{3,}", digits) and not has_unit and "," not in text and "." not in text:
        return ""
    return text


def classify_number_token(token: str) -> str:
    cleaned = clean_number_token(token)
    if not cleaned:
        return "noise"
    if "%" in cleaned:
        return "ratio"
    money_units = ["원", "달러", "조", "억", "$", "trillion", "million", "bn", "b"]
    if any(unit in cleaned for unit in money_units):
        return "money"
    if "년" in cleaned or re.fullmatch(r"20\d{2}", cleaned):
        return "year"
    if "배" in cleaned:
        return "growth_multiple"
    if any(unit in cleaned for unit in ["개", "명", "건", "세"]):
        return "count"
    return "number"


def clean_number_tokens(tokens: list[str], limit: int = 16) -> tuple[list[str], list[str]]:
    clean: list[str] = []
    dropped: list[str] = []
    for token in tokens:
        cleaned = clean_number_token(str(token))
        if cleaned:
            clean.append(cleaned)
        else:
            dropped.append(str(token))
    return _dedupe(clean)[:limit], _dedupe(dropped)[:limit]


def _numbers_used(text: str, limit: int = 24) -> list[str]:
    return _dedupe([match.group(0).strip() for match in NUMBER_RE.finditer(text)])[:limit]


def _present_terms(text: str, terms: list[str]) -> list[str]:
    lower = text.lower()
    return [term for term in terms if term.lower() in lower]


def _source_entries_for_lessons(
    item: dict[str, Any],
    parsed: dict[str, Any],
) -> list[dict[str, Any]]:
    records = extract_slide_sources_from_parsed(item, parsed)
    entries: list[dict[str, Any]] = []
    for record in records:
        for entry in record.get("source_entries", []):
            enriched = dict(entry)
            enriched["slide_number"] = record.get("slide_number")
            enriched["slide_title"] = record.get("slide_title")
            entries.append(enriched)
    return entries


def _initial_seed_sources(entries: list[dict[str, Any]], limit: int = 8) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for entry in entries:
        if not entry.get("url"):
            continue
        output.append(
            {
                "slide_number": entry.get("slide_number"),
                "source_kind": entry.get("source_kind"),
                "url": entry.get("url"),
                "url_domain": entry.get("url_domain"),
                "evidence_type": entry.get("evidence_type"),
            }
        )
        if len(output) >= limit:
            break
    return output


def _infer_main_seed_hook(title: str, text: str) -> str:
    lower = text.lower()
    if ("f88" in lower or "전당포" in title) and "상장" in text:
        return "베트남 전당포 체인 F88이 상장을 추진한다"
    if "코카콜라" in title and ("인도" in text or "ambani" in lower or "릴라이언스" in text):
        return "인도 대기업이 코카콜라와 정면 경쟁하는 현지 음료 서사를 만든다"
    lines = [
        line.strip()
        for line in text.splitlines()
        if len(line.strip()) >= 8 and not line.strip().lower().startswith("http")
    ]
    if title and title not in {"", lines[0] if lines else ""}:
        return lines[0] if lines else title
    return title or (lines[0] if lines else "")


def _story_expansion_path(title: str, text: str, evidence_types: list[str]) -> list[str]:
    lower = text.lower()
    path: list[str] = []
    if ("f88" in lower or "전당포" in title) and "상장" in text:
        path.extend(
            [
                "낯선 상장 후보",
                "한국 전당포 이미지",
                "베트남 신용팽창",
                "은행 접근성 한계",
                "오토바이 담보대출",
                "창업자 일화",
                "추심 리스크와 제도권화",
            ]
        )
        return path
    if "company" in evidence_types:
        path.append("낯선 회사/산업 seed 소개")
    if "number/statistic" in evidence_types:
        path.append("숫자로 규모와 성장성 확인")
    if "local_context" in evidence_types:
        path.append("현지 맥락과 한국 시청자 bridge")
    if "everyday_object" in evidence_types:
        path.append("일상 사물로 낯선 구조를 시각화")
    if "person/founder" in evidence_types:
        path.append("인물/창업자 일화로 story화")
    if "institution/regulation" in evidence_types:
        path.append("제도/규제 구조로 확장")
    if "risk/reversal" in evidence_types:
        path.append("리스크/반전으로 긴장 형성")
    return path or ["seed headline", "context expansion", "evidence check"]


def _candidate_signals(
    text: str,
    entries: list[dict[str, Any]],
    evidence_types: list[str],
) -> list[str]:
    lower = text.lower()
    signals: list[str] = []
    if any(term in text for term in ["전당포", "낯선", "이색", "최초", "신세대"]) or "f88" in lower:
        signals.append("unfamiliar_industry")
    if "number/statistic" in evidence_types and any(
        term in text for term in ["성장", "증가", "매출", "10배", "%", "조", "억"]
    ):
        signals.append("fast_growth_numbers")
    if ("오토바이" in text and "담보" in text) or any(
        term in text for term in ["등록증", "반바지", "콜라", "휴대폰"]
    ):
        signals.append("everyday_collateral_object")
    if any(term in text for term in ["상장", "제도권", "메인스트림", "공식", "거래소"]) and any(
        term in text for term in ["전당포", "사금융", "비공식", "pawnshop"]
    ):
        signals.append("formalization_of_informal_market")
    if "person/founder" in evidence_types:
        signals.append("founder_anecdote")
    if "risk/reversal" in evidence_types or any(term in text for term in ["추심", "규제", "수사"]):
        signals.append("regulatory_or_collection_risk")
    if any(term in text for term in KOREA_TERMS):
        signals.append("korea_bridge_available")
    unique_domains = {entry.get("url_domain") for entry in entries if entry.get("url_domain")}
    if len(unique_domains) >= 3 and len(entries) >= 5:
        signals.append("primary_source_rich")
    if "image/proof_object" in evidence_types or any(
        entry.get("source_kind") in {"image_url", "generated_image"} for entry in entries
    ):
        signals.append("visual_proof_object")
    return _dedupe(signals)


def seed_lesson_from_parsed(item: dict[str, Any], parsed: dict[str, Any] | None) -> dict[str, Any]:
    ppt_id = _manifest_id(item)
    if parsed is None:
        return {
            "ppt_id": ppt_id,
            "ppt_title": str(item.get("title") or ""),
            "local_path": str(item.get("local_path") or ""),
            "initial_seed_sources": [],
            "main_seed_hook": "",
            "story_expansion_path": [],
            "evidence_object_types": [],
            "numbers_used": [],
            "everyday_objects": [],
            "people_or_founders": [],
            "institutions_or_regulation": [],
            "risks_or_reversals": [],
            "korea_bridge": [],
            "visual_proof_objects": [],
            "jibi_candidate_signals": [],
            "lesson_confidence": "low",
            "status": "missing_or_unparsed",
        }
    title = str(item.get("title") or parsed.get("title") or "")
    text = "\n".join(
        [
            title,
            "\n".join(
                "\n".join([str(slide.get("visible_text") or ""), str(slide.get("notes") or "")])
                for slide in parsed.get("slides", [])
            ),
        ]
    )
    entries = _source_entries_for_lessons(item, parsed)
    evidence_types = _dedupe(
        [
            evidence
            for slide in parsed.get("slides", [])
            for evidence in infer_evidence_types(
                "\n".join([str(slide.get("visible_text") or ""), str(slide.get("notes") or "")]),
                media_count=int(slide.get("media_count") or 0),
                slide_type=str(slide.get("slide_type") or ""),
                domains=[_domain(url) for url in slide.get("all_urls", []) if _domain(url)],
            )
        ]
    )
    signals = _candidate_signals(text, entries, evidence_types)
    confidence = (
        "high"
        if len(signals) >= 5 and len(entries) >= 5
        else "medium"
        if signals
        else "low"
    )
    visual_proofs = [
        {
            "slide_number": entry.get("slide_number"),
            "source_kind": entry.get("source_kind"),
            "url": entry.get("url"),
            "url_domain": entry.get("url_domain"),
        }
        for entry in entries
        if entry.get("source_kind") in {"image_url", "generated_image"}
    ][:12]
    return {
        "ppt_id": ppt_id,
        "ppt_title": title,
        "local_path": str(item.get("local_path") or ""),
        "initial_seed_sources": _initial_seed_sources(entries),
        "main_seed_hook": _infer_main_seed_hook(title, text),
        "story_expansion_path": _story_expansion_path(title, text, evidence_types),
        "evidence_object_types": evidence_types,
        "numbers_used": _numbers_used(text),
        "everyday_objects": _present_terms(text, EVERYDAY_OBJECT_TERMS),
        "people_or_founders": _line_snippets(text, PERSON_TERMS),
        "institutions_or_regulation": _line_snippets(text, INSTITUTION_TERMS),
        "risks_or_reversals": _line_snippets(text, RISK_TERMS),
        "korea_bridge": _line_snippets(text, KOREA_TERMS),
        "visual_proof_objects": visual_proofs,
        "jibi_candidate_signals": signals,
        "lesson_confidence": confidence,
        "status": "parsed",
    }


def extract_jibi_seed_lessons(
    *,
    manifest: Path = DEFAULT_MANIFEST,
    output_jsonl: Path = SEED_LESSONS_JSONL,
    report_md: Path = SEED_LESSON_REPORT_MD,
) -> list[dict[str, Any]]:
    rows = load_sample_manifest(manifest)
    records: list[dict[str, Any]] = []
    for item in rows:
        local_path = _resolve_local_path(str(item.get("local_path") or ""))
        parsed = None
        if local_path.exists():
            try:
                parsed = parse_presentation(local_path)
            except Exception:  # pragma: no cover - defensive local corpus reporting
                parsed = None
        records.append(seed_lesson_from_parsed(item, parsed))
    write_jsonl(output_jsonl, records)
    report_md.parent.mkdir(parents=True, exist_ok=True)
    report_md.write_text(_seed_lesson_markdown(records, manifest, output_jsonl), encoding="utf-8")
    _maybe_write_sample_report()
    return records


def _seed_lesson_markdown(
    records: list[dict[str, Any]],
    manifest: Path,
    output_jsonl: Path,
) -> str:
    signal_counts: Counter[str] = Counter(
        signal for record in records for signal in record.get("jibi_candidate_signals", [])
    )
    lines = [
        "# PPT Seed Lesson Report",
        "",
        "Rule-based PR1 extraction. No LLM calls were made.",
        "",
        "## Summary",
        "",
        f"- manifest: `{_repo_relative(manifest)}`",
        f"- output_jsonl: `{_repo_relative(output_jsonl)}`",
        f"- lesson_count: {len(records)}",
        "",
        "## Jibi Candidate Signals",
        "",
        *[f"- {signal}: {count}" for signal, count in signal_counts.most_common()],
        "",
        "## Lessons",
        "",
    ]
    for record in records:
        lines.extend(
            [
                f"### {_table_cell(record.get('ppt_title')) or record.get('ppt_id')}",
                "",
                f"- main_seed_hook: {record.get('main_seed_hook') or '(none)'}",
                f"- lesson_confidence: {record.get('lesson_confidence')}",
                f"- story_expansion_path: {', '.join(record.get('story_expansion_path', []))}",
                f"- jibi_candidate_signals: {', '.join(record.get('jibi_candidate_signals', []))}",
                "",
            ]
        )
    return "\n".join(lines) + "\n"


def _read_jsonl_if_exists(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return read_jsonl(path)


def _maybe_write_sample_report() -> None:
    inventory = _read_jsonl_if_exists(INVENTORY_JSONL)
    sources = _read_jsonl_if_exists(SLIDE_SOURCES_JSONL)
    matches = _read_jsonl_if_exists(BROADCAST_MATCHES_JSONL)
    lessons = _read_jsonl_if_exists(SEED_LESSONS_JSONL)
    if not any([inventory, sources, matches, lessons]):
        return
    SAMPLE_REPORT_MD.parent.mkdir(parents=True, exist_ok=True)
    SAMPLE_REPORT_MD.write_text(
        combined_sample_markdown(
            inventory=inventory,
            sources=sources,
            matches=matches,
            lessons=lessons,
        ),
        encoding="utf-8",
    )


def write_combined_report(
    *,
    inventory_jsonl: Path = INVENTORY_JSONL,
    sources_jsonl: Path = SLIDE_SOURCES_JSONL,
    matches_jsonl: Path = BROADCAST_MATCHES_JSONL,
    lessons_jsonl: Path = SEED_LESSONS_JSONL,
    report_md: Path = SAMPLE_REPORT_MD,
) -> str:
    markdown = combined_sample_markdown(
        inventory=_read_jsonl_if_exists(inventory_jsonl),
        sources=_read_jsonl_if_exists(sources_jsonl),
        matches=_read_jsonl_if_exists(matches_jsonl),
        lessons=_read_jsonl_if_exists(lessons_jsonl),
    )
    report_md.parent.mkdir(parents=True, exist_ok=True)
    report_md.write_text(markdown, encoding="utf-8")
    return markdown


def _records_by_id(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {str(row.get("ppt_id")): row for row in rows if row.get("ppt_id")}


def _source_summary_by_ppt(sources: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    summary: dict[str, dict[str, Any]] = defaultdict(
        lambda: {
            "url_count": 0,
            "canonical_domains": Counter(),
            "source_domain_categories": Counter(),
            "source_kinds": Counter(),
            "evidence_types_raw": Counter(),
            "image_source_count": 0,
        }
    )
    for record in sources:
        ppt_id = str(record.get("ppt_id") or "")
        if not ppt_id:
            continue
        item = summary[ppt_id]
        urls = record.get("extracted_urls", [])
        item["url_count"] += len(urls)
        for domain in record.get("url_domains", []):
            canonical = canonical_domain(str(domain))
            if canonical:
                item["canonical_domains"][canonical] += 1
                item["source_domain_categories"][source_domain_category(canonical)] += 1
        for evidence in record.get("evidence_types", []):
            item["evidence_types_raw"][str(evidence)] += 1
        for entry in record.get("source_entries", []):
            source_kind = str(entry.get("source_kind") or "unknown")
            item["source_kinds"][source_kind] += 1
            if source_kind in {"image_url", "generated_image"}:
                item["image_source_count"] += 1
            canonical = canonical_domain(str(entry.get("url_domain") or entry.get("url") or ""))
            if canonical:
                item["canonical_domains"][canonical] += 0
                item["source_domain_categories"][source_domain_category(canonical)] += 0
    return summary


def clean_everyday_objects(objects: list[str]) -> list[str]:
    vague = {"차", "집"}
    clear = [str(item) for item in objects if str(item) and str(item) not in vague]
    return _dedupe(clear)


def clean_evidence_types(
    *,
    raw_counts: Counter[str],
    clean_numbers: list[str],
    source_kinds: Counter[str],
    domain_categories: Counter[str],
    everyday_objects: list[str],
) -> list[str]:
    clean: list[str] = []
    if clean_numbers or domain_categories.get("official/data", 0) >= 2:
        clean.append("number/statistic")
    if source_kinds.get("image_url", 0) or source_kinds.get("generated_image", 0):
        clean.append("image/proof_object")
    for evidence in ["institution/regulation", "quote", "company", "chart/table", "person/founder"]:
        if raw_counts.get(evidence, 0):
            clean.append(evidence)
    if everyday_objects:
        clean.append("everyday_object")
    if raw_counts.get("risk/reversal", 0):
        clean.append("risk/reversal")
    if raw_counts.get("local_context", 0):
        clean.append("local_context")
    return clean or ["unknown"]


def _broadcast_review_label(match: dict[str, Any] | None) -> str:
    label = str((match or {}).get("broadcast_label") or "not_found")
    if label in {"broadcast_confirmed", "likely_used"}:
        return "review_priority_high"
    if label == "maybe_used":
        return "weak_candidate"
    if label == "excluded_non_syukaworld":
        return "do_not_use_as_positive"
    return "snapshot_not_matched"


def _review_bucket(
    *,
    lesson: dict[str, Any],
    match: dict[str, Any] | None,
    title_flags: list[str],
    url_count: int,
    slide_count: int,
    clean_numbers: list[str],
    clean_evidence: list[str],
) -> tuple[str, list[str]]:
    reasons: list[str] = []
    signals = set(lesson.get("jibi_candidate_signals", []))
    label = str((match or {}).get("broadcast_label") or "not_found")
    url_density = url_count / slide_count if slide_count else 0.0
    if title_flags and any(
        flag in title_flags
        for flag in ["internal_reference", "material", "revision", "duplicate_copy"]
    ):
        reasons.append("title_flag_exclude_candidate")
        return "exclude_candidate", reasons
    if label == "excluded_non_syukaworld":
        reasons.append("non_syukaworld_match_only")
        return "exclude_candidate", reasons
    if lesson.get("lesson_confidence") == "low" or url_count == 0 or url_density < 0.2:
        reasons.append("weak_source_or_lesson_confidence")
        return "weak", reasons
    if len(clean_numbers) < 1:
        reasons.append("clean_numbers_missing")
    if "primary_source_rich" not in signals:
        reasons.append("not_source_rich")
    if not ({"regulatory_or_collection_risk", "korea_bridge_available"} & signals):
        reasons.append("risk_or_korea_bridge_missing")
    if not ({"image/proof_object", "company", "institution/regulation"} & set(clean_evidence)):
        reasons.append("evidence_diversity_missing")
    if lesson.get("lesson_confidence") == "high" and not reasons:
        return "gold", ["high_confidence_clean_signals"]
    return "review", reasons or ["manual_review"]


def build_seed_lesson_review_queue(
    *,
    inventory_jsonl: Path = INVENTORY_JSONL,
    sources_jsonl: Path = SLIDE_SOURCES_JSONL,
    matches_jsonl: Path = BROADCAST_MATCHES_JSONL,
    lessons_jsonl: Path = SEED_LESSONS_JSONL,
    output_jsonl: Path = SEED_LESSON_REVIEW_QUEUE_JSONL,
    report_md: Path = SEED_LESSON_REVIEW_QUEUE_REPORT_MD,
    show_progress: bool = True,
) -> list[dict[str, Any]]:
    inventory = _records_by_id(_read_jsonl_if_exists(inventory_jsonl))
    matches = _records_by_id(_read_jsonl_if_exists(matches_jsonl))
    lessons = _read_jsonl_if_exists(lessons_jsonl)
    source_summary = _source_summary_by_ppt(_read_jsonl_if_exists(sources_jsonl))
    rows: list[dict[str, Any]] = []
    for lesson in _progress(lessons, desc="review queue", enabled=show_progress):
        ppt_id = str(lesson.get("ppt_id") or "")
        inventory_record = inventory.get(ppt_id, {})
        match = matches.get(ppt_id)
        summary = source_summary.get(ppt_id, {})
        raw_numbers = [str(item) for item in lesson.get("numbers_used", [])]
        clean_numbers, dropped_numbers = clean_number_tokens(raw_numbers)
        title = str(lesson.get("ppt_title") or inventory_record.get("title") or "")
        title_info = clean_ppt_title(title)
        clean_objects = clean_everyday_objects(
            [str(item) for item in lesson.get("everyday_objects", [])]
        )
        source_kinds = summary.get("source_kinds", Counter())
        domain_categories = summary.get("source_domain_categories", Counter())
        raw_evidence_counts = summary.get("evidence_types_raw", Counter())
        clean_evidence = clean_evidence_types(
            raw_counts=raw_evidence_counts,
            clean_numbers=clean_numbers,
            source_kinds=source_kinds,
            domain_categories=domain_categories,
            everyday_objects=clean_objects,
        )
        slide_count = int(inventory_record.get("slide_count") or 0)
        url_count = int(summary.get("url_count") or 0)
        bucket, reasons = _review_bucket(
            lesson=lesson,
            match=match,
            title_flags=title_info["title_flags"],
            url_count=url_count,
            slide_count=slide_count,
            clean_numbers=clean_numbers,
            clean_evidence=clean_evidence,
        )
        rows.append(
            {
                "ppt_id": ppt_id,
                "ppt_title": lesson.get("ppt_title") or inventory_record.get("title") or "",
                "clean_title": title_info["clean_title"],
                "title_flags": title_info["title_flags"],
                "review_bucket": bucket,
                "review_reasons": reasons,
                "lesson_confidence": lesson.get("lesson_confidence"),
                "main_seed_hook": lesson.get("main_seed_hook"),
                "story_expansion_path": lesson.get("story_expansion_path", []),
                "jibi_candidate_signals": lesson.get("jibi_candidate_signals", []),
                "numbers_used": raw_numbers,
                "numbers_used_clean": clean_numbers,
                "numbers_noise_dropped": dropped_numbers,
                "everyday_objects_clean": clean_objects,
                "evidence_types_raw": [
                    evidence for evidence, _count in raw_evidence_counts.most_common()
                ],
                "evidence_types_clean": clean_evidence,
                "source_domain_categories": dict(sorted(domain_categories.items())),
                "top_source_domains_clean": [
                    domain
                    for domain, _count in summary.get(
                        "canonical_domains",
                        Counter(),
                    ).most_common(8)
                ],
                "url_count": url_count,
                "slide_count": slide_count,
                "url_density": round(url_count / slide_count, 3) if slide_count else 0,
                "broadcast_label": (match or {}).get("broadcast_label", "not_found"),
                "broadcast_review_label": _broadcast_review_label(match),
                "matched_video_title": (match or {}).get("matched_video_title", ""),
                "title_similarity": (match or {}).get("title_similarity", 0),
                "match_score": (match or {}).get("match_score", 0),
            }
        )
    write_jsonl(output_jsonl, rows)
    report_md.parent.mkdir(parents=True, exist_ok=True)
    report_md.write_text(_review_queue_markdown(rows, output_jsonl), encoding="utf-8")
    return rows


def _review_queue_markdown(rows: list[dict[str, Any]], output_jsonl: Path) -> str:
    bucket_counts = Counter(str(row.get("review_bucket")) for row in rows)
    lines = [
        "# PPT Seed Lesson Review Queue",
        "",
        "Post-processed PR2 queue generated from existing PR1 JSONL outputs. No PPT reparsing.",
        "",
        "## Summary",
        "",
        f"- output_jsonl: `{_repo_relative(output_jsonl)}`",
        f"- queue_count: {len(rows)}",
        *[f"- {bucket}: {count}" for bucket, count in sorted(bucket_counts.items())],
        "",
    ]
    for bucket in ["gold", "review", "weak", "exclude_candidate"]:
        lines.extend([f"## {bucket}", ""])
        examples = [row for row in rows if row.get("review_bucket") == bucket][:30]
        if not examples:
            lines.append("- none")
            lines.append("")
            continue
        lines.extend(
            [
                "| title | hook | reasons | clean numbers | broadcast |",
                "| --- | --- | --- | --- | --- |",
            ]
        )
        for row in examples:
            lines.append(
                "| "
                + " | ".join(
                    [
                        _table_cell(row.get("clean_title")),
                        _table_cell(row.get("main_seed_hook")),
                        _table_cell(", ".join(row.get("review_reasons", []))),
                        _table_cell(", ".join(row.get("numbers_used_clean", [])[:5])),
                        _table_cell(row.get("broadcast_review_label")),
                    ]
                )
                + " |"
            )
        lines.append("")
    return "\n".join(lines) + "\n"


def _source_entries_for_queue(record: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
    entries: list[tuple[str, dict[str, Any]]] = []
    seen: set[str] = set()
    for entry in record.get("source_entries", []):
        url = str(entry.get("url") or "").strip()
        normalized = normalize_url_for_queue(url)
        if not normalized:
            continue
        entries.append((url, entry))
        seen.add(normalized)
    for url in record.get("extracted_urls", []):
        normalized = normalize_url_for_queue(str(url))
        if normalized and normalized not in seen:
            entries.append((str(url), {}))
            seen.add(normalized)
    return entries


def _source_url_candidates_by_ppt(
    sources: list[dict[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
    for record in sources:
        ppt_id = str(record.get("ppt_id") or "")
        if not ppt_id:
            continue
        slide_number = int(record.get("slide_number") or 0)
        record_evidence = [str(item) for item in record.get("evidence_types", []) if item]
        for url, entry in _source_entries_for_queue(record):
            normalized_url = normalize_url_for_queue(url)
            if not normalized_url:
                continue
            domain = canonical_domain(entry.get("url_domain") or url)
            category = source_domain_category(domain)
            candidate = grouped[ppt_id].setdefault(
                normalized_url,
                {
                    "url": url,
                    "normalized_url": normalized_url,
                    "domain": domain,
                    "source_category": category,
                    "slide_numbers": set(),
                    "source_kinds": Counter(),
                    "source_note_groups": Counter(),
                    "evidence_types": Counter(),
                    "notes_excerpts": [],
                    "raw_text_excerpts": [],
                    "slide_titles": [],
                    "occurrence_count": 0,
                },
            )
            if slide_number:
                candidate["slide_numbers"].add(slide_number)
            source_kind = str(entry.get("source_kind") or "content_url")
            candidate["source_kinds"][source_kind] += 1
            note_group = str(entry.get("source_note_group") or "content")
            candidate["source_note_groups"][note_group] += 1
            evidence_values = entry.get("evidence_types") or record_evidence
            for evidence in evidence_values:
                candidate["evidence_types"][str(evidence)] += 1
            if record.get("notes_excerpt"):
                candidate["notes_excerpts"].append(str(record.get("notes_excerpt")))
            if record.get("raw_text_excerpt"):
                candidate["raw_text_excerpts"].append(str(record.get("raw_text_excerpt")))
            if record.get("slide_title"):
                candidate["slide_titles"].append(str(record.get("slide_title")))
            candidate["occurrence_count"] += 1

    finalized: dict[str, list[dict[str, Any]]] = {}
    for ppt_id, candidates in grouped.items():
        rows: list[dict[str, Any]] = []
        for candidate in candidates.values():
            slide_numbers = sorted(candidate["slide_numbers"])
            evidence_types = [
                evidence for evidence, _count in candidate["evidence_types"].most_common()
            ]
            source_kinds = [
                source_kind for source_kind, _count in candidate["source_kinds"].most_common()
            ]
            note_groups = [
                note_group for note_group, _count in candidate["source_note_groups"].most_common()
            ]
            access_hint = source_access_hint(candidate["domain"], candidate["source_category"])
            row = {
                "url": candidate["url"],
                "normalized_url": candidate["normalized_url"],
                "domain": candidate["domain"],
                "source_category": candidate["source_category"],
                "access_hint": access_hint,
                "collection_hint": source_collection_hint(access_hint),
                "first_slide": slide_numbers[0] if slide_numbers else 0,
                "slide_numbers": slide_numbers,
                "occurrence_count": int(candidate["occurrence_count"]),
                "source_kinds": source_kinds,
                "source_note_groups": note_groups,
                "evidence_types": evidence_types,
                "notes_excerpt": _excerpt(" ".join(_dedupe(candidate["notes_excerpts"])), 320),
                "raw_text_excerpt": _excerpt(
                    " ".join(_dedupe(candidate["raw_text_excerpts"])), 240
                ),
                "representative_slide_title": _dedupe(candidate["slide_titles"])[:1][0]
                if candidate["slide_titles"]
                else "",
            }
            row["priority_score"] = _url_priority_score(row)
            rows.append(row)
        rows.sort(
            key=lambda row: (
                -float(row.get("priority_score") or 0),
                int(row.get("first_slide") or 9999),
                str(row.get("normalized_url") or ""),
            )
        )
        for rank, row in enumerate(rows, start=1):
            row["url_priority_rank"] = rank
        finalized[ppt_id] = rows
    return finalized


def _url_priority_score(candidate: dict[str, Any]) -> float:
    category_score = SOURCE_CATEGORY_PRIORITY.get(str(candidate.get("source_category")), 0)
    kind_score = max(
        [SOURCE_KIND_PRIORITY.get(str(kind), 0) for kind in candidate.get("source_kinds", [])]
        or [0]
    )
    evidence_score = max(
        [
            EVIDENCE_TYPE_PRIORITY.get(str(evidence), 0)
            for evidence in candidate.get("evidence_types", [])
        ]
        or [0]
    )
    note_groups = set(str(group) for group in candidate.get("source_note_groups", []))
    note_score = 8 if "content" in note_groups else 4 if "image" in note_groups else 0
    occurrence_score = min(max(int(candidate.get("occurrence_count") or 1) - 1, 0), 5) * 3
    first_slide = int(candidate.get("first_slide") or 9999)
    early_score = (
        5 if first_slide <= 5 else 3 if first_slide <= 15 else 1 if first_slide <= 30 else 0
    )
    access_score = 2 if candidate.get("access_hint") == "likely_public" else 0
    return round(
        category_score
        + kind_score
        + evidence_score
        + note_score
        + occurrence_score
        + early_score
        + access_score,
        3,
    )


def _enrichment_status(review_bucket: str, url_rows: list[dict[str, Any]]) -> str:
    if not url_rows:
        return "no_urls"
    if review_bucket in {"weak", "exclude_candidate"}:
        return "manual_review_before_enrichment"
    access_counts = Counter(str(row.get("access_hint") or "unknown") for row in url_rows)
    if access_counts.get("likely_public"):
        return "ready_public_fetch"
    if access_counts.get("likely_paywalled") or access_counts.get("browser_or_manual_check"):
        return "manual_or_browser_first"
    return "manual_check"


def build_ppt_enrichment_queue(
    *,
    inventory_jsonl: Path = DRIVE_INVENTORY_JSONL,
    sources_jsonl: Path = DRIVE_SLIDE_SOURCES_JSONL,
    matches_jsonl: Path = DRIVE_BROADCAST_MATCHES_JSONL,
    lessons_jsonl: Path = DRIVE_SEED_LESSONS_JSONL,
    review_queue_jsonl: Path = SEED_LESSON_REVIEW_QUEUE_JSONL,
    output_jsonl: Path = PPT_ENRICHMENT_QUEUE_JSONL,
    url_queue_jsonl: Path = PPT_ENRICHMENT_URL_QUEUE_JSONL,
    report_md: Path = PPT_ENRICHMENT_QUEUE_REPORT_MD,
    max_urls_per_ppt: int = 30,
    show_progress: bool = True,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    inventory = _records_by_id(_read_jsonl_if_exists(inventory_jsonl))
    matches = _records_by_id(_read_jsonl_if_exists(matches_jsonl))
    lessons = _records_by_id(_read_jsonl_if_exists(lessons_jsonl))
    review_rows = _records_by_id(_read_jsonl_if_exists(review_queue_jsonl))
    source_candidates = _source_url_candidates_by_ppt(_read_jsonl_if_exists(sources_jsonl))
    ppt_ids = list(inventory) or list(review_rows) or sorted(source_candidates)
    rows: list[dict[str, Any]] = []
    for ppt_id in _progress(ppt_ids, desc="enrichment queue", enabled=show_progress):
        inventory_record = inventory.get(ppt_id, {})
        review_record = review_rows.get(ppt_id, {})
        lesson = lessons.get(ppt_id, {})
        match = matches.get(ppt_id, {})
        title = (
            review_record.get("ppt_title")
            or lesson.get("ppt_title")
            or inventory_record.get("title")
            or ""
        )
        title_info = clean_ppt_title(str(title))
        all_urls = source_candidates.get(ppt_id, [])
        queued_urls = all_urls if max_urls_per_ppt <= 0 else all_urls[:max_urls_per_ppt]
        access_counts = Counter(str(row.get("access_hint") or "unknown") for row in all_urls)
        category_counts = Counter(str(row.get("source_category") or "unknown") for row in all_urls)
        domain_counts = Counter(str(row.get("domain") or "unknown") for row in all_urls)
        review_bucket = str(review_record.get("review_bucket") or "unreviewed")
        row = {
            "ppt_id": ppt_id,
            "ppt_title": title,
            "clean_title": review_record.get("clean_title") or title_info["clean_title"],
            "title_flags": review_record.get("title_flags") or title_info["title_flags"],
            "local_path": inventory_record.get("local_path", ""),
            "resolved_local_path": inventory_record.get("resolved_local_path", ""),
            "folder_date_hint": inventory_record.get("folder_date_hint", ""),
            "researcher": inventory_record.get("researcher", ""),
            "slide_count": int(inventory_record.get("slide_count") or 0),
            "review_bucket": review_bucket,
            "review_reasons": review_record.get("review_reasons", []),
            "broadcast_label": match.get(
                "broadcast_label", review_record.get("broadcast_label", "not_found")
            ),
            "broadcast_review_label": review_record.get(
                "broadcast_review_label", _broadcast_review_label(match)
            ),
            "matched_video_title": match.get(
                "matched_video_title", review_record.get("matched_video_title", "")
            ),
            "lesson_confidence": review_record.get(
                "lesson_confidence", lesson.get("lesson_confidence", "")
            ),
            "main_seed_hook": review_record.get(
                "main_seed_hook", lesson.get("main_seed_hook", "")
            ),
            "story_expansion_path": review_record.get(
                "story_expansion_path", lesson.get("story_expansion_path", [])
            ),
            "jibi_candidate_signals": review_record.get(
                "jibi_candidate_signals", lesson.get("jibi_candidate_signals", [])
            ),
            "evidence_types_clean": review_record.get("evidence_types_clean", []),
            "numbers_used_clean": review_record.get("numbers_used_clean", []),
            "top_source_domains_clean": [
                domain for domain, _count in domain_counts.most_common(10)
            ],
            "source_domain_categories": dict(sorted(category_counts.items())),
            "access_hint_counts": dict(sorted(access_counts.items())),
            "unique_url_count": len(all_urls),
            "queued_url_count": len(queued_urls),
            "max_urls_per_ppt": max_urls_per_ppt,
            "enrichment_status": _enrichment_status(review_bucket, all_urls),
            "priority_urls": queued_urls,
        }
        rows.append(row)

    rows.sort(
        key=lambda row: (
            REVIEW_BUCKET_PRIORITY.get(str(row.get("review_bucket")), 9),
            -int(row.get("queued_url_count") or 0),
            str(row.get("clean_title") or ""),
        )
    )
    flat_url_rows: list[dict[str, Any]] = []
    for batch_rank, row in enumerate(rows, start=1):
        row["batch_priority_rank"] = batch_rank
        for url_row in row.get("priority_urls", []):
            flat_url_rows.append(
                {
                    "batch_priority_rank": batch_rank,
                    "ppt_id": row.get("ppt_id"),
                    "ppt_title": row.get("ppt_title"),
                    "clean_title": row.get("clean_title"),
                    "review_bucket": row.get("review_bucket"),
                    "enrichment_status": row.get("enrichment_status"),
                    "main_seed_hook": row.get("main_seed_hook"),
                    **url_row,
                }
            )

    write_jsonl(output_jsonl, rows)
    write_jsonl(url_queue_jsonl, flat_url_rows)
    report_md.parent.mkdir(parents=True, exist_ok=True)
    report_md.write_text(
        _enrichment_queue_markdown(
            rows=rows,
            flat_url_rows=flat_url_rows,
            output_jsonl=output_jsonl,
            url_queue_jsonl=url_queue_jsonl,
        ),
        encoding="utf-8",
    )
    return rows, flat_url_rows


def _enrichment_queue_markdown(
    *,
    rows: list[dict[str, Any]],
    flat_url_rows: list[dict[str, Any]],
    output_jsonl: Path,
    url_queue_jsonl: Path,
) -> str:
    bucket_counts = Counter(str(row.get("review_bucket") or "unknown") for row in rows)
    status_counts = Counter(str(row.get("enrichment_status") or "unknown") for row in rows)
    access_counts = Counter(str(row.get("access_hint") or "unknown") for row in flat_url_rows)
    category_counts = Counter(str(row.get("source_category") or "unknown") for row in flat_url_rows)
    domain_counts = Counter(str(row.get("domain") or "unknown") for row in flat_url_rows)
    paywall_rows = [
        row for row in flat_url_rows if row.get("access_hint") == "likely_paywalled"
    ][:30]
    lines = [
        "# PPT Enrichment Queue",
        "",
        "Stage 1 queue for source-page traversal, slide-image review, and story-arc summarization.",
        "No URL fetching or paywall access was performed.",
        "",
        "## Outputs",
        "",
        f"- ppt_queue_jsonl: `{_repo_relative(output_jsonl)}`",
        f"- url_queue_jsonl: `{_repo_relative(url_queue_jsonl)}`",
        "",
        "## Summary",
        "",
        f"- ppt_count: {len(rows)}",
        f"- queued_url_count: {len(flat_url_rows)}",
        "- unique_url_count_before_per_ppt_cap: "
        f"{sum(int(row.get('unique_url_count') or 0) for row in rows)}",
        *[f"- review_bucket.{name}: {count}" for name, count in sorted(bucket_counts.items())],
        *[f"- enrichment_status.{name}: {count}" for name, count in sorted(status_counts.items())],
        "",
        "## URL Access Hints",
        "",
        *[f"- {name}: {count}" for name, count in access_counts.most_common()],
        "",
        "## Source Categories",
        "",
        *[f"- {name}: {count}" for name, count in category_counts.most_common()],
        "",
        "## Top Domains",
        "",
        *[f"- {name}: {count}" for name, count in domain_counts.most_common(20)],
        "",
        "## Recommended Pilot PPTs",
        "",
        "| rank | bucket | title | queued URLs | access hints | top domains | hook |",
        "| ---: | --- | --- | ---: | --- | --- | --- |",
    ]
    for row in rows[:25]:
        access_summary = ", ".join(
            f"{key}:{value}" for key, value in row.get("access_hint_counts", {}).items()
        )
        lines.append(
            "| "
            + " | ".join(
                [
                    str(row.get("batch_priority_rank")),
                    _table_cell(row.get("review_bucket")),
                    _table_cell(row.get("clean_title")),
                    str(row.get("queued_url_count")),
                    _table_cell(access_summary),
                    _table_cell(", ".join(row.get("top_source_domains_clean", [])[:5])),
                    _table_cell(row.get("main_seed_hook")),
                ]
            )
            + " |"
        )
    lines.extend(["", "## Paywall/Auth Candidates", ""])
    if not paywall_rows:
        lines.append("- none")
    else:
        lines.extend(
            [
                "| ppt | domain | slide | collection_hint | url |",
                "| --- | --- | ---: | --- | --- |",
            ]
        )
        for row in paywall_rows:
            lines.append(
                "| "
                + " | ".join(
                    [
                        _table_cell(row.get("clean_title")),
                        _table_cell(row.get("domain")),
                        str(row.get("first_slide") or ""),
                        _table_cell(row.get("collection_hint")),
                        _table_cell(row.get("normalized_url")),
                    ]
                )
                + " |"
            )
    lines.extend(
        [
            "",
            "## Next Stage",
            "",
            "- Start with `ready_public_fetch` rows and `public_fetch_first` URLs.",
            "- Keep `likely_paywalled` URLs in a manual/authenticated-session lane; "
            "do not store full article text.",
            "- Use `priority_urls[].slide_numbers` to connect fetched source memos back "
            "to slide-image review.",
        ]
    )
    return "\n".join(lines) + "\n"


def _source_page_id(url: str) -> str:
    normalized = normalize_url_for_queue(url)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:20]


def _decode_source_response(response: SourcePageHttpResponse) -> str:
    content_type = response.content_type or ""
    charset_match = re.search(r"charset=([^;]+)", content_type, flags=re.I)
    charset = charset_match.group(1).strip() if charset_match else "utf-8"
    try:
        return response.body.decode(charset, errors="ignore")
    except LookupError:
        return response.body.decode("utf-8", errors="ignore")


def _is_source_page_boilerplate(value: str) -> bool:
    text = _compact(value)
    if len(text) < 25:
        return True
    lowered = text.lower()
    return any(marker in lowered for marker in PAGE_BOILERPLATE_MARKERS)


def _has_paywall_marker(text: str) -> bool:
    lowered = text.lower()
    return any(marker.lower() in lowered for marker in PAYWALL_MARKERS)


def _has_marker(text: str, markers: set[str]) -> bool:
    lowered = text.lower()
    return any(marker.lower() in lowered for marker in markers)


def _parse_source_page_html(html_text: str) -> tuple[str, str, list[str]]:
    parser = _SourcePageTextParser()
    try:
        parser.feed(html_text)
        parser.close()
    except Exception:
        return "", "", []
    return parser.title, parser.meta_description, _dedupe(parser.paragraphs)


def _extract_source_signal_terms(text: str, terms: list[str]) -> list[str]:
    lowered = text.lower()
    return _dedupe([term for term in terms if term.lower() in lowered])


def _source_memo_quality(
    *,
    access_status: str,
    failure_reason: str,
    content_type: str,
    article_title: str,
    meta_description: str,
    paragraph_text: str,
    html_text: str,
) -> tuple[str, bool]:
    content_type_lower = content_type.lower()
    combined = " ".join([article_title, meta_description, paragraph_text, failure_reason])
    if content_type_lower.startswith("image/") or failure_reason.startswith("image/"):
        return "image_asset_only", False
    if _has_marker(combined, SOURCE_VERIFICATION_MARKERS) or _has_marker(
        html_text[:5000], SOURCE_VERIFICATION_MARKERS
    ):
        return "verification_page", False
    if access_status == "paywalled_manual_needed":
        return "teaser_only", False
    if access_status == "login_required":
        return "login_required", False
    if access_status == "unsupported_content_type":
        return "unsupported_content_type", False
    if access_status == "fetch_failed":
        if _has_marker(combined, SOURCE_SOFT_ERROR_MARKERS):
            return "soft_error_page", False
        return "fetch_failed", False
    if _has_marker(combined, SOURCE_SOFT_ERROR_MARKERS):
        return "soft_error_page", False
    if access_status == "empty":
        return "empty_page", False
    if access_status == "fetched_public":
        if len(paragraph_text) >= 250 or meta_description:
            return "usable_public_memo", True
        return "empty_page", False
    return access_status or "unknown", False


def _usable_as_story_evidence(memo: dict[str, Any]) -> bool:
    if "usable_as_story_evidence" in memo:
        return bool(memo.get("usable_as_story_evidence"))
    if memo.get("memo_quality_status"):
        return str(memo.get("memo_quality_status")) not in SOURCE_MEMO_BAD_QUALITY_STATUSES
    return str(memo.get("access_status") or "") == "fetched_public"


def _usable_source_memos(memos: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [memo for memo in memos if _usable_as_story_evidence(memo)]


def _source_attempt_status(
    *,
    response: SourcePageHttpResponse,
    html_text: str,
    paragraph_text: str,
    meta_description: str,
) -> tuple[str, str]:
    status = response.status
    if status in {401, 403}:
        return "login_required", f"http_{status}"
    if status is not None and status >= 400:
        return "fetch_failed", f"http_{status}"
    content_type = (response.content_type or "").lower()
    if content_type and not any(
        token in content_type for token in ["html", "xhtml", "xml", "text/plain"]
    ):
        return "unsupported_content_type", content_type.split(";", 1)[0]
    if _has_paywall_marker(html_text) and len(paragraph_text) < 800:
        return "paywalled_manual_needed", "paywall_marker_or_teaser"
    if len(paragraph_text) >= 250 or meta_description:
        return "fetched_public", ""
    if _has_paywall_marker(html_text):
        return "paywalled_manual_needed", "paywall_marker"
    return "empty", "no_extractable_article_body"


def _source_status_base(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "source_page_id": _source_page_id(str(row.get("normalized_url") or row.get("url") or "")),
        "ppt_id": row.get("ppt_id"),
        "ppt_title": row.get("ppt_title", ""),
        "clean_title": row.get("clean_title", ""),
        "batch_priority_rank": row.get("batch_priority_rank"),
        "url_priority_rank": row.get("url_priority_rank"),
        "url": row.get("url"),
        "normalized_url": row.get("normalized_url"),
        "domain": row.get("domain"),
        "source_category": row.get("source_category"),
        "access_hint": row.get("access_hint"),
        "collection_hint": row.get("collection_hint"),
        "first_slide": row.get("first_slide"),
        "slide_numbers": row.get("slide_numbers", []),
        "evidence_types": row.get("evidence_types", []),
        "source_kinds": row.get("source_kinds", []),
    }


def _source_memo_from_response(
    row: dict[str, Any],
    *,
    response: SourcePageHttpResponse,
    fetched_at: str,
) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    status_row = _source_status_base(row)
    status_row["fetched_at"] = fetched_at
    status_row["http_status"] = response.status
    status_row["content_type"] = response.content_type or ""
    status_row["fetched_url"] = response.url
    html_text = _decode_source_response(response)
    article_title, meta_description, paragraphs = _parse_source_page_html(html_text)
    paragraph_text = _compact(" ".join(paragraphs))
    access_status, reason = _source_attempt_status(
        response=response,
        html_text=html_text,
        paragraph_text=paragraph_text,
        meta_description=meta_description,
    )
    memo_quality_status, usable_as_story_evidence = _source_memo_quality(
        access_status=access_status,
        failure_reason=reason,
        content_type=response.content_type or "",
        article_title=article_title,
        meta_description=meta_description,
        paragraph_text=paragraph_text,
        html_text=html_text,
    )
    status_row["access_status"] = access_status
    status_row["failure_reason"] = reason
    status_row["memo_quality_status"] = memo_quality_status
    status_row["usable_as_story_evidence"] = usable_as_story_evidence
    if access_status not in {"fetched_public", "paywalled_manual_needed"} and not (
        article_title or meta_description
    ):
        return None, status_row

    signal_text = _compact(" ".join([article_title, meta_description, paragraph_text]))
    clean_numbers, dropped_numbers = clean_number_tokens(NUMBER_RE.findall(signal_text))
    memo = {
        **_source_status_base(row),
        "fetched_at": fetched_at,
        "access_status": access_status,
        "failure_reason": reason,
        "memo_quality_status": memo_quality_status,
        "usable_as_story_evidence": usable_as_story_evidence,
        "http_status": response.status,
        "content_type": response.content_type or "",
        "fetched_url": response.url,
        "article_title": _excerpt(article_title, 220),
        "meta_description": _excerpt(meta_description, SOURCE_MEMO_META_LIMIT),
        "source_summary": _excerpt(
            meta_description or " ".join(paragraphs[:2]), SOURCE_MEMO_EXCERPT_LIMIT
        ),
        "source_excerpt_short": _excerpt(" ".join(paragraphs[:2]), SOURCE_MEMO_EXCERPT_LIMIT),
        "body_chars_seen": len(paragraph_text),
        "paragraph_count": len(paragraphs),
        "numbers": clean_numbers[:20],
        "numbers_noise_dropped": dropped_numbers[:20],
        "institutions_regulation": _extract_source_signal_terms(signal_text, INSTITUTION_TERMS),
        "people_founders": _extract_source_signal_terms(signal_text, PERSON_TERMS),
        "risks_reversals": _extract_source_signal_terms(signal_text, RISK_TERMS),
        "korea_bridge": _extract_source_signal_terms(signal_text, KOREA_TERMS),
        "everyday_objects": _extract_source_signal_terms(signal_text, EVERYDAY_OBJECT_TERMS),
        "summary_method": "rule_based_extractive_short_memo",
        "copyright_note": (
            "Full article body not stored; memo keeps metadata, short excerpt, "
            "and rule-based signals only."
        ),
    }
    return memo, status_row


def _manual_source_request(
    row: dict[str, Any],
    *,
    reason: str | None = None,
    access_status: str | None = None,
    memo_quality_status: str | None = None,
) -> dict[str, Any]:
    access_hint = str(row.get("access_hint") or "unknown")
    collection_hint = str(row.get("collection_hint") or "manual_check")
    if reason is None:
        if access_hint == "likely_paywalled":
            reason = "likely_paywalled_domain"
        elif access_hint == "browser_or_manual_check":
            reason = "dynamic_or_social_source"
        elif collection_hint == "optional_public_fetch":
            reason = "low_priority_reference_source"
        else:
            reason = "manual_check"
    if access_status is None:
        access_status = "manual_or_auth_required"
    return {
        **_source_status_base(row),
        "access_status": access_status,
        "memo_quality_status": memo_quality_status or "manual_or_auth_required",
        "usable_as_story_evidence": False,
        "manual_reason": reason,
        "preferred_resolution": (
            "Provide a short source memo, authorized excerpt, PDF/screenshot, "
            "or use an authenticated browser session."
        ),
    }


def _selected_source_rows(
    url_queue: list[dict[str, Any]],
    *,
    ppt_limit: int,
) -> list[dict[str, Any]]:
    if ppt_limit <= 0:
        return url_queue
    selected_ids: list[str] = []
    seen_ids: set[str] = set()
    ordered_rows = sorted(
        url_queue,
        key=lambda row: (
            int(row.get("batch_priority_rank") or 999999),
            int(row.get("url_priority_rank") or 999999),
        ),
    )
    for row in ordered_rows:
        ppt_id = str(row.get("ppt_id") or "")
        if not ppt_id or ppt_id in seen_ids:
            continue
        selected_ids.append(ppt_id)
        seen_ids.add(ppt_id)
        if len(selected_ids) >= ppt_limit:
            break
    selected_set = set(selected_ids)
    return [row for row in ordered_rows if str(row.get("ppt_id") or "") in selected_set]


def fetch_ppt_source_memos(
    *,
    url_queue_jsonl: Path = PPT_ENRICHMENT_URL_QUEUE_JSONL,
    output_jsonl: Path = SOURCE_PAGE_MEMOS_JSONL,
    status_jsonl: Path = SOURCE_FETCH_STATUS_JSONL,
    manual_requests_jsonl: Path = MANUAL_SOURCE_REQUESTS_JSONL,
    report_md: Path = SOURCE_FETCH_REPORT_MD,
    http_client: SourcePageHttpClient | None = None,
    limit: int = 50,
    ppt_limit: int = 10,
    timeout: float = 12,
    include_optional: bool = False,
    show_progress: bool = True,
    fetched_at: str | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    url_queue = _read_jsonl_if_exists(url_queue_jsonl)
    selected_rows = _selected_source_rows(url_queue, ppt_limit=ppt_limit)
    fetchable_hints = {"public_fetch_first"}
    if include_optional:
        fetchable_hints.add("optional_public_fetch")
    fetchable_rows = [
        row for row in selected_rows if str(row.get("collection_hint")) in fetchable_hints
    ]
    fetch_rows = fetchable_rows if limit <= 0 else fetchable_rows[:limit]
    fetch_keys = {
        (str(row.get("ppt_id") or ""), str(row.get("normalized_url") or row.get("url") or ""))
        for row in fetch_rows
    }
    client = http_client or UrlLibSourcePageHttpClient()
    fetched_at = fetched_at or datetime.now(UTC).isoformat()
    memos: list[dict[str, Any]] = []
    status_rows: list[dict[str, Any]] = []
    manual_requests: list[dict[str, Any]] = []

    for row in _progress(selected_rows, desc="source memos", enabled=show_progress):
        row_key = (
            str(row.get("ppt_id") or ""),
            str(row.get("normalized_url") or row.get("url") or ""),
        )
        if row_key not in fetch_keys:
            if str(row.get("collection_hint")) in fetchable_hints:
                status = _source_status_base(row)
                status["access_status"] = "not_attempted_fetch_limit"
                status["memo_quality_status"] = "not_attempted_fetch_limit"
                status["usable_as_story_evidence"] = False
                status["failure_reason"] = "fetch_limit"
                status_rows.append(status)
            else:
                manual = _manual_source_request(row)
                manual_requests.append(manual)
                status_rows.append(manual)
            continue
        url = str(row.get("normalized_url") or row.get("url") or "")
        try:
            response = client.fetch(url, timeout=timeout)
        except Exception as exc:
            status = _source_status_base(row)
            status["access_status"] = "fetch_failed"
            status["memo_quality_status"] = "fetch_failed"
            status["usable_as_story_evidence"] = False
            status["failure_reason"] = type(exc).__name__
            status["fetched_at"] = fetched_at
            status_rows.append(status)
            continue
        memo, status = _source_memo_from_response(row, response=response, fetched_at=fetched_at)
        status_rows.append(status)
        if memo:
            memos.append(memo)
        if status.get("access_status") in {
            "login_required",
            "paywalled_manual_needed",
            "unsupported_content_type",
        }:
            manual_requests.append(
                _manual_source_request(
                    row,
                    reason=str(status.get("failure_reason") or status.get("access_status")),
                    access_status=str(status.get("access_status")),
                    memo_quality_status=str(status.get("memo_quality_status") or ""),
                )
            )

    write_jsonl(output_jsonl, memos)
    write_jsonl(status_jsonl, status_rows)
    write_jsonl(manual_requests_jsonl, manual_requests)
    report_md.parent.mkdir(parents=True, exist_ok=True)
    report_md.write_text(
        _source_fetch_report_markdown(
            memos=memos,
            status_rows=status_rows,
            manual_requests=manual_requests,
            url_queue_jsonl=url_queue_jsonl,
            output_jsonl=output_jsonl,
            status_jsonl=status_jsonl,
            manual_requests_jsonl=manual_requests_jsonl,
            limit=limit,
            ppt_limit=ppt_limit,
        ),
        encoding="utf-8",
    )
    return memos, status_rows, manual_requests


def _source_fetch_report_markdown(
    *,
    memos: list[dict[str, Any]],
    status_rows: list[dict[str, Any]],
    manual_requests: list[dict[str, Any]],
    url_queue_jsonl: Path,
    output_jsonl: Path,
    status_jsonl: Path,
    manual_requests_jsonl: Path,
    limit: int,
    ppt_limit: int,
) -> str:
    status_counts = Counter(str(row.get("access_status") or "unknown") for row in status_rows)
    quality_counts = Counter(
        str(row.get("memo_quality_status") or "unknown") for row in status_rows
    )
    usable_status_count = sum(1 for row in status_rows if row.get("usable_as_story_evidence"))
    manual_reason_counts = Counter(
        str(row.get("manual_reason") or "unknown") for row in manual_requests
    )
    memo_domain_counts = Counter(str(row.get("domain") or "unknown") for row in memos)
    manual_domain_counts = Counter(str(row.get("domain") or "unknown") for row in manual_requests)
    selected_ppt_count = len({str(row.get("ppt_id")) for row in status_rows if row.get("ppt_id")})
    lines = [
        "# PPT Source Fetch Report",
        "",
        "Stage 2 pilot for source-page memos. Full article bodies are not stored.",
        "",
        "## Outputs",
        "",
        f"- url_queue_jsonl: `{_repo_relative(url_queue_jsonl)}`",
        f"- source_page_memos_jsonl: `{_repo_relative(output_jsonl)}`",
        f"- source_fetch_status_jsonl: `{_repo_relative(status_jsonl)}`",
        f"- manual_source_requests_jsonl: `{_repo_relative(manual_requests_jsonl)}`",
        "",
        "## Run Scope",
        "",
        f"- ppt_limit: {ppt_limit}",
        f"- fetch_limit: {limit}",
        f"- selected_ppt_count: {selected_ppt_count}",
        f"- status_row_count: {len(status_rows)}",
        f"- source_memo_count: {len(memos)}",
        f"- usable_story_evidence_count: {usable_status_count}",
        f"- manual_request_count: {len(manual_requests)}",
        "",
        "## Access Status Distribution",
        "",
        *[f"- {name}: {count}" for name, count in status_counts.most_common()],
        "",
        "## Memo Quality Distribution",
        "",
        *[f"- {name}: {count}" for name, count in quality_counts.most_common()],
        "",
        "## Manual Request Reasons",
        "",
        *[f"- {name}: {count}" for name, count in manual_reason_counts.most_common()],
        "",
        "## Source Memo Domains",
        "",
        *[f"- {name}: {count}" for name, count in memo_domain_counts.most_common(15)],
        "",
        "## Manual/Auth Domains",
        "",
        *[f"- {name}: {count}" for name, count in manual_domain_counts.most_common(15)],
        "",
        "## Source Memo Examples",
        "",
    ]
    if not memos:
        lines.append("- none")
    else:
        lines.extend(
            [
                "| ppt | domain | status | quality | usable | title | numbers |",
                "| --- | --- | --- | --- | --- | --- | --- |",
            ]
        )
        for memo in memos[:20]:
            lines.append(
                "| "
                + " | ".join(
                    [
                        _table_cell(memo.get("clean_title")),
                        _table_cell(memo.get("domain")),
                        _table_cell(memo.get("access_status")),
                        _table_cell(memo.get("memo_quality_status")),
                        "yes" if memo.get("usable_as_story_evidence") else "no",
                        _table_cell(memo.get("article_title")),
                        _table_cell(", ".join(memo.get("numbers", [])[:5])),
                    ]
                )
                + " |"
            )
    lines.extend(["", "## Manual/Auth Request Examples", ""])
    if not manual_requests:
        lines.append("- none")
    else:
        lines.extend(
            [
                "| ppt | domain | reason | slide | url |",
                "| --- | --- | --- | ---: | --- |",
            ]
        )
        for request in manual_requests[:30]:
            lines.append(
                "| "
                + " | ".join(
                    [
                        _table_cell(request.get("clean_title")),
                        _table_cell(request.get("domain")),
                        _table_cell(request.get("manual_reason")),
                        str(request.get("first_slide") or ""),
                        _table_cell(request.get("normalized_url")),
                    ]
                )
                + " |"
            )
    lines.extend(
        [
            "",
            "## Guardrails",
            "",
            "- Paywalled URLs are not bypassed.",
            "- Authenticated-browser collection should use the user's legitimate access only.",
            "- Source memos keep metadata, short excerpts, and rule-based signals; "
            "no full article body.",
        ]
    )
    return "\n".join(lines) + "\n"


def _selected_enrichment_ppts(
    enrichment_queue: list[dict[str, Any]],
    *,
    ppt_limit: int,
) -> list[dict[str, Any]]:
    rows = sorted(
        enrichment_queue,
        key=lambda row: (
            int(row.get("batch_priority_rank") or 999999),
            REVIEW_BUCKET_PRIORITY.get(str(row.get("review_bucket")), 9),
            str(row.get("clean_title") or row.get("ppt_title") or ""),
        ),
    )
    return rows if ppt_limit <= 0 else rows[:ppt_limit]


def _slide_sources_by_ppt_slide(
    sources: list[dict[str, Any]],
) -> dict[str, dict[int, dict[str, Any]]]:
    grouped: dict[str, dict[int, dict[str, Any]]] = defaultdict(dict)
    for record in sources:
        ppt_id = str(record.get("ppt_id") or "")
        slide_no = int(record.get("slide_number") or 0)
        if not ppt_id or slide_no <= 0:
            continue
        grouped[ppt_id][slide_no] = record
    return grouped


def _source_memos_by_ppt_url(
    source_memos: list[dict[str, Any]],
) -> dict[tuple[str, str], dict[str, Any]]:
    output: dict[tuple[str, str], dict[str, Any]] = {}
    for memo in source_memos:
        ppt_id = str(memo.get("ppt_id") or "")
        normalized_url = str(memo.get("normalized_url") or memo.get("url") or "")
        if ppt_id and normalized_url:
            output[(ppt_id, normalize_url_for_queue(normalized_url))] = memo
    return output


def _slide_urls(record: dict[str, Any]) -> list[str]:
    urls: list[str] = []
    for entry in record.get("source_entries", []):
        if entry.get("url"):
            urls.append(str(entry.get("url")))
    urls.extend(str(url) for url in record.get("extracted_urls", []) if url)
    return _dedupe([normalize_url_for_queue(url) for url in urls if normalize_url_for_queue(url)])


def _slide_source_categories(record: dict[str, Any]) -> list[str]:
    domains = [
        canonical_domain(str(domain))
        for domain in record.get("url_domains", [])
        if canonical_domain(str(domain))
    ]
    for entry in record.get("source_entries", []):
        domain = canonical_domain(str(entry.get("url_domain") or entry.get("url") or ""))
        if domain:
            domains.append(domain)
    return _dedupe([source_domain_category(domain) for domain in domains if domain])


def _copy_render_outputs(
    *,
    result: ContactSheetResult,
    ppt_id: str,
    slide_images_dir: Path,
    contact_sheets_dir: Path,
) -> tuple[dict[int, Path], Path | None, Path | None]:
    copied_thumbnails: dict[int, Path] = {}
    ppt_slide_dir = slide_images_dir / ppt_id
    for slide in result.slides:
        if slide.thumbnail_path is None or not slide.thumbnail_path.exists():
            continue
        suffix = slide.thumbnail_path.suffix or ".png"
        destination = ppt_slide_dir / f"slide_{slide.slide_no:03d}{suffix}"
        destination.parent.mkdir(parents=True, exist_ok=True)
        if slide.thumbnail_path.resolve() != destination.resolve():
            shutil.copyfile(slide.thumbnail_path, destination)
        copied_thumbnails[slide.slide_no] = destination

    copied_sheet: Path | None = None
    if result.contact_sheet_path and result.contact_sheet_path.exists():
        contact_sheets_dir.mkdir(parents=True, exist_ok=True)
        copied_sheet = contact_sheets_dir / f"{ppt_id}{result.contact_sheet_path.suffix}"
        if result.contact_sheet_path.resolve() != copied_sheet.resolve():
            shutil.copyfile(result.contact_sheet_path, copied_sheet)

    copied_sheet_pdf: Path | None = None
    if result.contact_sheet_pdf_path and result.contact_sheet_pdf_path.exists():
        contact_sheets_dir.mkdir(parents=True, exist_ok=True)
        copied_sheet_pdf = contact_sheets_dir / f"{ppt_id}.pdf"
        if result.contact_sheet_pdf_path.resolve() != copied_sheet_pdf.resolve():
            shutil.copyfile(result.contact_sheet_pdf_path, copied_sheet_pdf)
    return copied_thumbnails, copied_sheet, copied_sheet_pdf


def infer_slide_visual_types(
    *,
    slide_source: dict[str, Any],
    source_memos: list[dict[str, Any]],
    thumbnail_path: Path | None,
) -> list[str]:
    evidence = set(str(item) for item in slide_source.get("evidence_types", []) if item)
    categories = set(_slide_source_categories(slide_source))
    slide_text = " ".join(
        [
            str(slide_source.get("slide_title") or ""),
            str(slide_source.get("raw_text_excerpt") or ""),
            str(slide_source.get("notes_excerpt") or ""),
            " ".join(str(memo.get("source_summary") or "") for memo in source_memos),
        ]
    )
    lowered = slide_text.lower()
    visual_types: list[str] = []
    if thumbnail_path is not None:
        visual_types.append("rendered_slide_thumbnail")
    if int(slide_source.get("media_count") or 0) > 0 or "image/proof_object" in evidence:
        visual_types.append("embedded_image_or_screenshot")
    if "chart/table" in evidence or any(term in lowered for term in ["chart", "table", "표"]):
        visual_types.append("chart_or_table")
    if "media/news" in categories:
        visual_types.append("article_or_news_page")
    if "official/data" in categories:
        visual_types.append("official_or_data_page")
    if "company/primary" in categories:
        visual_types.append("company_or_primary_page")
    if "social/video" in categories:
        visual_types.append("social_or_video")
    if any(term.lower() in lowered for term in PERSON_TERMS) or "person/founder" in evidence:
        visual_types.append("person_or_founder")
    if any(term.lower() in lowered for term in RISK_TERMS) or "risk/reversal" in evidence:
        visual_types.append("risk_or_reversal")
    if any(term.lower() in lowered for term in KOREA_TERMS) or "local_context" in evidence:
        visual_types.append("korea_bridge")
    if any(term.lower() in lowered for term in EVERYDAY_OBJECT_TERMS):
        visual_types.append("everyday_object")
    if any(term in lowered for term in ["map", "지도"]):
        visual_types.append("map_or_geography")
    if not visual_types:
        visual_types.append("text_or_unknown")
    return _dedupe(visual_types)


def infer_slide_story_role(
    *,
    slide_number: int,
    slide_source: dict[str, Any],
    visual_types: list[str],
) -> str:
    evidence = set(str(item) for item in slide_source.get("evidence_types", []) if item)
    slide_type = str(slide_source.get("slide_type") or "")
    if slide_number == 1 or slide_type == "title":
        return "title_or_hook"
    if "risk_or_reversal" in visual_types:
        return "risk_or_reversal"
    if "korea_bridge" in visual_types:
        return "korea_bridge"
    if "chart_or_table" in visual_types or "number/statistic" in evidence:
        return "number_or_data_evidence"
    if {"article_or_news_page", "official_or_data_page", "company_or_primary_page"} & set(
        visual_types
    ):
        return "source_evidence"
    if "embedded_image_or_screenshot" in visual_types:
        return "visual_proof_object"
    return "context_or_transition"


def _story_input_for_ppt(
    *,
    ppt_row: dict[str, Any],
    slide_rows: list[dict[str, Any]],
    render_result: ContactSheetResult,
    contact_sheet_path: Path | None,
    contact_sheet_pdf_path: Path | None,
) -> dict[str, Any]:
    role_counts = Counter(str(row.get("story_role") or "unknown") for row in slide_rows)
    visual_counts = Counter(
        visual_type
        for row in slide_rows
        for visual_type in row.get("visual_types", [])
    )
    memo_status_counts = Counter(
        status for row in slide_rows for status in row.get("source_access_statuses", [])
    )
    memo_quality_counts = Counter(
        status for row in slide_rows for status in row.get("source_memo_quality_statuses", [])
    )
    source_domains = Counter(
        domain
        for row in slide_rows
        for domain in row.get("source_domains", [])
        if domain
    )
    outline = [
        {
            "slide_number": row.get("slide_number"),
            "story_role": row.get("story_role"),
            "visual_types": row.get("visual_types", []),
            "slide_title": row.get("slide_title", ""),
            "source_domains": row.get("source_domains", [])[:5],
            "source_memo_titles": row.get("source_memo_titles", [])[:3],
            "usable_source_memo_titles": row.get("usable_source_memo_titles", [])[:3],
            "evidence_types": row.get("evidence_types", [])[:5],
        }
        for row in slide_rows
    ]
    return {
        "ppt_id": ppt_row.get("ppt_id"),
        "ppt_title": ppt_row.get("ppt_title"),
        "clean_title": ppt_row.get("clean_title"),
        "local_path": ppt_row.get("local_path", ""),
        "resolved_local_path": ppt_row.get("resolved_local_path", ""),
        "slide_count": int(ppt_row.get("slide_count") or len(slide_rows)),
        "review_bucket": ppt_row.get("review_bucket"),
        "main_seed_hook": ppt_row.get("main_seed_hook"),
        "story_expansion_path": ppt_row.get("story_expansion_path", []),
        "jibi_candidate_signals": ppt_row.get("jibi_candidate_signals", []),
        "contact_sheet_path": _repo_relative(contact_sheet_path) if contact_sheet_path else "",
        "contact_sheet_pdf_path": (
            _repo_relative(contact_sheet_pdf_path) if contact_sheet_pdf_path else ""
        ),
        "render_status": render_result.status,
        "thumbnail_count": render_result.thumbnail_count,
        "thumbnail_backend": render_result.backend,
        "render_warnings": render_result.warnings,
        "source_memo_count": sum(len(row.get("source_memo_ids", [])) for row in slide_rows),
        "usable_source_memo_count": sum(
            len(row.get("usable_source_memo_ids", [])) for row in slide_rows
        ),
        "source_access_status_counts": dict(sorted(memo_status_counts.items())),
        "source_memo_quality_counts": dict(sorted(memo_quality_counts.items())),
        "story_role_counts": dict(sorted(role_counts.items())),
        "visual_type_counts": dict(sorted(visual_counts.items())),
        "top_source_domains": [domain for domain, _count in source_domains.most_common(10)],
        "slide_outline": outline,
        "next_story_summary_task": (
            "Summarize seed hook, source expansion path, visual proof sequence, "
            "risk/reversal, Korea bridge, and Jibi-teachable signals from slide_outline."
        ),
    }


def build_ppt_slide_visual_memos(
    *,
    enrichment_queue_jsonl: Path = PPT_ENRICHMENT_QUEUE_JSONL,
    slide_sources_jsonl: Path = DRIVE_SLIDE_SOURCES_JSONL,
    source_memos_jsonl: Path = SOURCE_PAGE_MEMOS_JSONL,
    output_jsonl: Path = SLIDE_VISUAL_MEMOS_JSONL,
    story_inputs_jsonl: Path = PPT_STORY_INPUTS_JSONL,
    report_md: Path = SLIDE_VISUAL_REPORT_MD,
    render_output_dir: Path = PPT_SLIDE_VISUAL_RENDER_DIR,
    slide_images_dir: Path = PPT_SLIDE_IMAGES_DIR,
    contact_sheets_dir: Path = PPT_CONTACT_SHEETS_DIR,
    ppt_limit: int = 5,
    thumbnail_generator: ThumbnailGenerator | None = None,
    show_progress: bool = True,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    enrichment_queue = _read_jsonl_if_exists(enrichment_queue_jsonl)
    selected_ppts = _selected_enrichment_ppts(enrichment_queue, ppt_limit=ppt_limit)
    slide_sources = _slide_sources_by_ppt_slide(_read_jsonl_if_exists(slide_sources_jsonl))
    memo_by_url = _source_memos_by_ppt_url(_read_jsonl_if_exists(source_memos_jsonl))
    visual_rows: list[dict[str, Any]] = []
    story_rows: list[dict[str, Any]] = []

    for ppt_row in _progress(selected_ppts, desc="slide visuals", enabled=show_progress):
        ppt_id = str(ppt_row.get("ppt_id") or "")
        if not ppt_id:
            continue
        pptx_path = _resolve_local_path(
            str(ppt_row.get("resolved_local_path") or ppt_row.get("local_path") or "")
        )
        target = ContactSheetTarget(
            deck_id=ppt_id,
            pptx_path=pptx_path,
            slide_spec_path=None,
            source_kind="ppt_learning_drive",
        )
        render_result = render_contact_sheet_target(
            target=target,
            output_dir=render_output_dir,
            thumbnail_generator=thumbnail_generator,
        )
        thumbnails, contact_sheet, contact_sheet_pdf = _copy_render_outputs(
            result=render_result,
            ppt_id=ppt_id,
            slide_images_dir=slide_images_dir,
            contact_sheets_dir=contact_sheets_dir,
        )
        rows_for_ppt: list[dict[str, Any]] = []
        sources_by_slide = slide_sources.get(ppt_id, {})
        slide_count = max(
            int(ppt_row.get("slide_count") or 0),
            render_result.slide_count,
            max(sources_by_slide, default=0),
        )
        for slide_number in range(1, slide_count + 1):
            slide_source = sources_by_slide.get(slide_number, {})
            urls = _slide_urls(slide_source)
            source_memos = [
                memo_by_url[(ppt_id, url)] for url in urls if (ppt_id, url) in memo_by_url
            ]
            usable_source_memos = _usable_source_memos(source_memos)
            thumbnail = thumbnails.get(slide_number)
            visual_types = infer_slide_visual_types(
                slide_source=slide_source,
                source_memos=source_memos,
                thumbnail_path=thumbnail,
            )
            story_role = infer_slide_story_role(
                slide_number=slide_number,
                slide_source=slide_source,
                visual_types=visual_types,
            )
            source_domains = _dedupe(
                [
                    canonical_domain(str(domain))
                    for domain in slide_source.get("url_domains", [])
                    if canonical_domain(str(domain))
                ]
            )
            row = {
                "ppt_id": ppt_id,
                "ppt_title": ppt_row.get("ppt_title", ""),
                "clean_title": ppt_row.get("clean_title", ""),
                "slide_number": slide_number,
                "slide_title": slide_source.get("slide_title", ""),
                "slide_type": slide_source.get("slide_type", ""),
                "thumbnail_path": _repo_relative(thumbnail) if thumbnail else "",
                "contact_sheet_path": _repo_relative(contact_sheet) if contact_sheet else "",
                "media_count": int(slide_source.get("media_count") or 0),
                "source_url_count": len(urls),
                "source_urls": urls,
                "source_domains": source_domains,
                "source_categories": _slide_source_categories(slide_source),
                "source_memo_ids": [
                    str(memo.get("source_page_id") or "") for memo in source_memos
                ],
                "source_memo_titles": [
                    str(memo.get("article_title") or "") for memo in source_memos
                ],
                "source_access_statuses": [
                    str(memo.get("access_status") or "") for memo in source_memos
                ],
                "source_memo_quality_statuses": [
                    str(memo.get("memo_quality_status") or "") for memo in source_memos
                ],
                "usable_source_memo_ids": [
                    str(memo.get("source_page_id") or "") for memo in usable_source_memos
                ],
                "usable_source_memo_titles": [
                    str(memo.get("article_title") or "") for memo in usable_source_memos
                ],
                "evidence_types": [
                    str(item) for item in slide_source.get("evidence_types", []) if item
                ],
                "visual_types": visual_types,
                "story_role": story_role,
                "raw_text_excerpt": slide_source.get("raw_text_excerpt", ""),
                "notes_excerpt": slide_source.get("notes_excerpt", ""),
                "render_status": render_result.status,
            }
            rows_for_ppt.append(row)
            visual_rows.append(row)
        story_rows.append(
            _story_input_for_ppt(
                ppt_row=ppt_row,
                slide_rows=rows_for_ppt,
                render_result=render_result,
                contact_sheet_path=contact_sheet,
                contact_sheet_pdf_path=contact_sheet_pdf,
            )
        )

    write_jsonl(output_jsonl, visual_rows)
    write_jsonl(story_inputs_jsonl, story_rows)
    report_md.parent.mkdir(parents=True, exist_ok=True)
    report_md.write_text(
        _slide_visual_report_markdown(
            visual_rows=visual_rows,
            story_rows=story_rows,
            output_jsonl=output_jsonl,
            story_inputs_jsonl=story_inputs_jsonl,
            report_md=report_md,
        ),
        encoding="utf-8",
    )
    return visual_rows, story_rows


def _slide_visual_report_markdown(
    *,
    visual_rows: list[dict[str, Any]],
    story_rows: list[dict[str, Any]],
    output_jsonl: Path,
    story_inputs_jsonl: Path,
    report_md: Path,
) -> str:
    render_counts = Counter(str(row.get("render_status") or "unknown") for row in story_rows)
    role_counts = Counter(str(row.get("story_role") or "unknown") for row in visual_rows)
    visual_counts = Counter(
        visual_type for row in visual_rows for visual_type in row.get("visual_types", [])
    )
    access_counts = Counter(
        status for row in visual_rows for status in row.get("source_access_statuses", [])
    )
    quality_counts = Counter(
        status for row in visual_rows for status in row.get("source_memo_quality_statuses", [])
    )
    usable_memo_count = sum(
        len(row.get("usable_source_memo_ids", [])) for row in visual_rows
    )
    thumbnail_count = sum(1 for row in visual_rows if row.get("thumbnail_path"))
    contact_sheet_count = sum(1 for row in story_rows if row.get("contact_sheet_path"))
    lines = [
        "# PPT Slide Visual Report",
        "",
        "Stage 3 links rendered slide surfaces, extracted slide sources, and source memos.",
        "",
        "## Outputs",
        "",
        f"- slide_visual_memos_jsonl: `{_repo_relative(output_jsonl)}`",
        f"- ppt_story_inputs_jsonl: `{_repo_relative(story_inputs_jsonl)}`",
        f"- report_md: `{_repo_relative(report_md)}`",
        "",
        "## Summary",
        "",
        f"- ppt_count: {len(story_rows)}",
        f"- slide_visual_row_count: {len(visual_rows)}",
        f"- thumbnail_rows: {thumbnail_count}",
        f"- contact_sheet_count: {contact_sheet_count}",
        f"- usable_source_memo_count: {usable_memo_count}",
        *[f"- render_status.{name}: {count}" for name, count in sorted(render_counts.items())],
        "",
        "## Story Roles",
        "",
        *[f"- {name}: {count}" for name, count in role_counts.most_common()],
        "",
        "## Visual Types",
        "",
        *[f"- {name}: {count}" for name, count in visual_counts.most_common()],
        "",
        "## Source Memo Statuses",
        "",
        *[f"- {name}: {count}" for name, count in access_counts.most_common()],
        "",
        "## Source Memo Quality",
        "",
        *[f"- {name}: {count}" for name, count in quality_counts.most_common()],
        "",
        "## PPT Story Inputs",
        "",
        "| rank | title | render | slides | thumbnails | contact sheet | role mix | top domains |",
        "| ---: | --- | --- | ---: | ---: | --- | --- | --- |",
    ]
    for rank, row in enumerate(story_rows, start=1):
        role_mix = ", ".join(
            f"{key}:{value}" for key, value in row.get("story_role_counts", {}).items()
        )
        lines.append(
            "| "
            + " | ".join(
                [
                    str(rank),
                    _table_cell(row.get("clean_title")),
                    _table_cell(row.get("render_status")),
                    str(row.get("slide_count") or 0),
                    str(row.get("thumbnail_count") or 0),
                    _table_cell(row.get("contact_sheet_path")),
                    _table_cell(role_mix),
                    _table_cell(", ".join(row.get("top_source_domains", [])[:5])),
                ]
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "## Next Stage",
            "",
            "- Use `ppt_story_inputs_jsonl` as the input for rule-based story arc summaries.",
            "- Slides now connect thumbnail/contact-sheet paths, source URLs, and source memos.",
            "- Visual labels are heuristic; human review or multimodal inspection can refine them.",
        ]
    )
    return "\n".join(lines) + "\n"


def _group_by_ppt(rows: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        ppt_id = str(row.get("ppt_id") or "")
        if ppt_id:
            grouped[ppt_id].append(row)
    return grouped


def _source_memos_by_id(source_memos: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {
        str(memo.get("source_page_id")): memo
        for memo in source_memos
        if memo.get("source_page_id")
    }


def _first_nonempty(values: list[Any]) -> str:
    for value in values:
        text = _compact(str(value or ""))
        if text:
            return text
    return ""


def _slide_brief(row: dict[str, Any]) -> str:
    memo_titles = row.get("source_memo_titles")
    first_memo_title = memo_titles[0] if isinstance(memo_titles, list) and memo_titles else ""
    title = _first_nonempty(
        [
            row.get("slide_title"),
            row.get("raw_text_excerpt"),
            first_memo_title,
        ]
    )
    return _excerpt(title, 140)


def _source_memo_for_slide(
    row: dict[str, Any],
    memo_by_id: dict[str, dict[str, Any]],
    *,
    usable_only: bool = False,
) -> list[dict[str, Any]]:
    memos = [
        memo_by_id[memo_id]
        for memo_id in row.get("source_memo_ids", [])
        if memo_id in memo_by_id
    ]
    if usable_only:
        return _usable_source_memos(memos)
    return memos


def _pick_initial_seed_source(
    slide_rows: list[dict[str, Any]],
    memo_by_id: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    fallback: dict[str, Any] = {}
    for row in slide_rows:
        memos = _source_memo_for_slide(row, memo_by_id)
        usable_memos = [
            memo
            for memo in memos
            if memo.get("access_status") == "fetched_public"
            and _usable_as_story_evidence(memo)
        ]
        selected = usable_memos[0] if usable_memos else None
        if selected:
            return {
                "slide_number": row.get("slide_number"),
                "domain": selected.get("domain", ""),
                "title": selected.get("article_title", ""),
                "access_status": selected.get("access_status", ""),
                "memo_quality_status": selected.get("memo_quality_status", ""),
                "usable_as_story_evidence": True,
                "normalized_url": selected.get("normalized_url", ""),
                "evidence_types": row.get("evidence_types", []),
            }
        if memos and not fallback:
            selected = memos[0]
            fallback = {
                "slide_number": row.get("slide_number"),
                "domain": selected.get("domain", ""),
                "title": _slide_brief(row),
                "access_status": selected.get("access_status", ""),
                "memo_quality_status": selected.get("memo_quality_status", ""),
                "usable_as_story_evidence": False,
                "normalized_url": selected.get("normalized_url", ""),
                "evidence_types": row.get("evidence_types", []),
            }
        urls = row.get("source_urls", [])
        domains = row.get("source_domains", [])
        if urls and not fallback:
            fallback = {
                "slide_number": row.get("slide_number"),
                "domain": domains[0] if domains else canonical_domain(str(urls[0])),
                "title": _slide_brief(row),
                "access_status": "not_fetched",
                "memo_quality_status": "not_fetched",
                "usable_as_story_evidence": False,
                "normalized_url": urls[0],
                "evidence_types": row.get("evidence_types", []),
            }
    return fallback


def _compress_role_segments(slide_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    segments: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    for row in slide_rows:
        role = str(row.get("story_role") or "unknown")
        slide_no = int(row.get("slide_number") or 0)
        if current is None or current["story_role"] != role:
            current = {
                "story_role": role,
                "start_slide": slide_no,
                "end_slide": slide_no,
                "slide_count": 1,
                "sample_slide_titles": [],
                "sample_domains": [],
            }
            segments.append(current)
        else:
            current["end_slide"] = slide_no
            current["slide_count"] += 1
        brief = _slide_brief(row)
        if brief and len(current["sample_slide_titles"]) < 3:
            current["sample_slide_titles"].append(brief)
        for domain in row.get("source_domains", []):
            if domain and domain not in current["sample_domains"]:
                current["sample_domains"].append(domain)
            if len(current["sample_domains"]) >= 5:
                break
    return segments


def _top_visual_proof_sequence(
    slide_rows: list[dict[str, Any]],
    *,
    limit: int = 18,
) -> list[dict[str, Any]]:
    priority = {
        "title_or_hook": 5,
        "source_evidence": 5,
        "visual_proof_object": 5,
        "number_or_data_evidence": 4,
        "risk_or_reversal": 4,
        "korea_bridge": 3,
    }
    visual_rows = [
        row
        for row in slide_rows
        if {
            "embedded_image_or_screenshot",
            "article_or_news_page",
            "official_or_data_page",
            "company_or_primary_page",
            "chart_or_table",
            "social_or_video",
        }
        & set(row.get("visual_types", []))
    ]
    visual_rows.sort(
        key=lambda row: (
            -priority.get(str(row.get("story_role")), 0),
            int(row.get("slide_number") or 9999),
        )
    )
    selected = sorted(visual_rows[:limit], key=lambda row: int(row.get("slide_number") or 0))
    return [
        {
            "slide_number": row.get("slide_number"),
            "story_role": row.get("story_role"),
            "visual_types": row.get("visual_types", []),
            "thumbnail_path": row.get("thumbnail_path", ""),
            "source_domains": row.get("source_domains", [])[:5],
            "source_memo_titles": row.get("usable_source_memo_titles", [])[:3],
            "evidence_types": row.get("evidence_types", []),
            "slide_brief": _slide_brief(row),
        }
        for row in selected
    ]


def _number_sequence(
    slide_rows: list[dict[str, Any]],
    memo_by_id: dict[str, dict[str, Any]],
    *,
    limit: int = 20,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row in slide_rows:
        if not (
            row.get("story_role") == "number_or_data_evidence"
            or "number/statistic" in row.get("evidence_types", [])
            or "chart_or_table" in row.get("visual_types", [])
        ):
            continue
        memos = _source_memo_for_slide(row, memo_by_id, usable_only=True)
        numbers = _dedupe(
            [
                number
                for memo in memos
                for number in memo.get("numbers", [])
                if isinstance(number, str)
            ]
        )
        rows.append(
            {
                "slide_number": row.get("slide_number"),
                "slide_brief": _slide_brief(row),
                "numbers": numbers[:8],
                "source_domains": row.get("source_domains", [])[:5],
                "source_memo_titles": row.get("usable_source_memo_titles", [])[:3],
            }
        )
        if len(rows) >= limit:
            break
    return rows


def _aggregate_memo_terms(
    memos: list[dict[str, Any]],
    field: str,
    *,
    limit: int = 20,
) -> list[str]:
    counter: Counter[str] = Counter()
    for memo in memos:
        for value in memo.get(field, []):
            if value:
                counter[str(value)] += 1
    return [value for value, _count in counter.most_common(limit)]


def _manual_gaps_for_ppt(manual_rows: list[dict[str, Any]], *, limit: int = 12) -> dict[str, Any]:
    reason_counts = Counter(str(row.get("manual_reason") or "unknown") for row in manual_rows)
    domain_counts = Counter(str(row.get("domain") or "unknown") for row in manual_rows)
    examples = [
        {
            "slide_number": row.get("first_slide"),
            "domain": row.get("domain", ""),
            "reason": row.get("manual_reason", ""),
            "normalized_url": row.get("normalized_url", ""),
        }
        for row in manual_rows[:limit]
    ]
    return {
        "manual_request_count": len(manual_rows),
        "manual_reason_counts": dict(sorted(reason_counts.items())),
        "manual_domain_counts": dict(domain_counts.most_common(10)),
        "examples": examples,
    }


def _story_teachable_signals(
    *,
    story_input: dict[str, Any],
    slide_rows: list[dict[str, Any]],
    memos: list[dict[str, Any]],
    manual_gaps: dict[str, Any],
) -> list[str]:
    signals = [str(item) for item in story_input.get("jibi_candidate_signals", []) if item]
    role_counts = Counter(str(row.get("story_role") or "") for row in slide_rows)
    visual_types = Counter(
        visual_type for row in slide_rows for visual_type in row.get("visual_types", [])
    )
    source_statuses = Counter(str(memo.get("access_status") or "") for memo in memos)
    if role_counts.get("number_or_data_evidence", 0) >= 5:
        signals.append("number_ladder_story")
    if visual_types.get("embedded_image_or_screenshot", 0) >= 5:
        signals.append("screenshot_proof_sequence")
    if role_counts.get("korea_bridge", 0):
        signals.append("korea_bridge_sequence")
    if role_counts.get("risk_or_reversal", 0):
        signals.append("risk_reversal_sequence")
    if source_statuses.get("fetched_public", 0):
        signals.append("public_source_memos_available")
    if manual_gaps.get("manual_request_count", 0):
        signals.append("manual_or_auth_source_gap")
    return _dedupe(signals)


def _story_arc_summary_sentence(
    *,
    hook: str,
    role_segments: list[dict[str, Any]],
    top_domains: list[str],
    manual_gaps: dict[str, Any],
) -> str:
    roles = _dedupe([str(segment.get("story_role")) for segment in role_segments])
    role_text = " -> ".join(roles[:7]) if roles else "slide sequence"
    domain_text = ", ".join(top_domains[:4]) or "source mix"
    gap_text = (
        f"; manual/auth gaps {manual_gaps.get('manual_request_count')}"
        if manual_gaps.get("manual_request_count")
        else ""
    )
    return _excerpt(
        f"{hook or 'Seed'} expands through {role_text} using {domain_text}{gap_text}.",
        360,
    )


def story_arc_memo_from_inputs(
    *,
    story_input: dict[str, Any],
    slide_rows: list[dict[str, Any]],
    source_memos: list[dict[str, Any]],
    manual_rows: list[dict[str, Any]],
    lesson: dict[str, Any] | None = None,
    match: dict[str, Any] | None = None,
) -> dict[str, Any]:
    ppt_id = str(story_input.get("ppt_id") or "")
    slide_rows = sorted(slide_rows, key=lambda row: int(row.get("slide_number") or 0))
    memo_by_id = _source_memos_by_id(source_memos)
    usable_memo_by_id = {
        memo_id: memo for memo_id, memo in memo_by_id.items() if _usable_as_story_evidence(memo)
    }
    used_memo_ids = _dedupe(
        str(memo_id)
        for row in slide_rows
        for memo_id in row.get("source_memo_ids", [])
        if memo_id
    )
    raw_linked_memos = [
        memo_by_id[memo_id] for memo_id in used_memo_ids if memo_id in memo_by_id
    ]
    raw_reference_memos = raw_linked_memos if raw_linked_memos else source_memos
    linked_memos = _usable_source_memos(raw_reference_memos)
    if not linked_memos:
        linked_memos = _usable_source_memos(source_memos)
    manual_gaps = _manual_gaps_for_ppt(manual_rows)
    role_segments = _compress_role_segments(slide_rows)
    hook = str(
        story_input.get("main_seed_hook")
        or (lesson or {}).get("main_seed_hook")
        or story_input.get("clean_title")
        or story_input.get("ppt_title")
        or ""
    )
    opening = _first_nonempty(
        [
            hook,
            _slide_brief(slide_rows[1]) if len(slide_rows) > 1 else "",
            _slide_brief(slide_rows[0]) if slide_rows else "",
        ]
    )
    top_domains = list(story_input.get("top_source_domains", []))
    role_counts = Counter(str(row.get("story_role") or "unknown") for row in slide_rows)
    visual_counts = Counter(
        visual_type for row in slide_rows for visual_type in row.get("visual_types", [])
    )
    source_status_counts = Counter(
        str(memo.get("access_status") or "unknown") for memo in raw_reference_memos
    )
    source_quality_counts = Counter(
        str(memo.get("memo_quality_status") or "unknown") for memo in raw_reference_memos
    )
    arc_confidence = "high" if (
        story_input.get("render_status") == "contact_sheet_generated"
        and len(slide_rows) >= 3
        and linked_memos
    ) else "medium" if slide_rows and top_domains else "low"
    memo = {
        "ppt_id": ppt_id,
        "ppt_title": story_input.get("ppt_title", ""),
        "clean_title": story_input.get("clean_title", ""),
        "story_arc_confidence": arc_confidence,
        "main_hook": hook,
        "story_opening": opening,
        "initial_seed_source": _pick_initial_seed_source(slide_rows, memo_by_id),
        "story_arc_summary": _story_arc_summary_sentence(
            hook=hook,
            role_segments=role_segments,
            top_domains=top_domains,
            manual_gaps=manual_gaps,
        ),
        "source_expansion_path": story_input.get("story_expansion_path")
        or (lesson or {}).get("story_expansion_path", []),
        "role_segments": role_segments,
        "visual_proof_sequence": _top_visual_proof_sequence(slide_rows),
        "numbers_sequence": _number_sequence(slide_rows, usable_memo_by_id),
        "people_founders": _aggregate_memo_terms(linked_memos, "people_founders"),
        "institutions_regulation": _aggregate_memo_terms(
            linked_memos, "institutions_regulation"
        ),
        "risks_reversals": _aggregate_memo_terms(linked_memos, "risks_reversals"),
        "korea_bridge_terms": _aggregate_memo_terms(linked_memos, "korea_bridge"),
        "everyday_objects": _aggregate_memo_terms(linked_memos, "everyday_objects"),
        "manual_or_auth_gaps": manual_gaps,
        "jibi_teachable_signals": _story_teachable_signals(
            story_input=story_input,
            slide_rows=slide_rows,
            memos=linked_memos,
            manual_gaps=manual_gaps,
        ),
        "broadcast_label": (match or {}).get("broadcast_label", ""),
        "matched_video_title": (match or {}).get("matched_video_title", ""),
        "slide_count": int(story_input.get("slide_count") or len(slide_rows)),
        "thumbnail_count": int(story_input.get("thumbnail_count") or 0),
        "contact_sheet_path": story_input.get("contact_sheet_path", ""),
        "contact_sheet_pdf_path": story_input.get("contact_sheet_pdf_path", ""),
        "render_status": story_input.get("render_status", ""),
        "story_role_counts": dict(sorted(role_counts.items())),
        "visual_type_counts": dict(visual_counts.most_common()),
        "source_access_status_counts": dict(sorted(source_status_counts.items())),
        "source_memo_quality_counts": dict(sorted(source_quality_counts.items())),
        "top_source_domains": top_domains,
        "raw_source_memo_count": len(raw_reference_memos),
        "usable_source_memo_count": len(linked_memos),
        "unusable_source_memo_count": max(len(raw_reference_memos) - len(linked_memos), 0),
        "source_memo_count": len(linked_memos),
        "slide_by_slide_story_outline": [
            {
                "slide_number": row.get("slide_number"),
                "story_role": row.get("story_role"),
                "slide_brief": _slide_brief(row),
                "visual_types": row.get("visual_types", []),
                "source_domains": row.get("source_domains", [])[:5],
                "source_memo_titles": row.get("usable_source_memo_titles", [])[:3],
                "raw_source_memo_titles": row.get("source_memo_titles", [])[:3],
                "source_memo_quality_statuses": row.get("source_memo_quality_statuses", [])[:5],
                "thumbnail_path": row.get("thumbnail_path", ""),
            }
            for row in slide_rows
        ],
    }
    return memo


def build_ppt_story_arc_memos(
    *,
    story_inputs_jsonl: Path = PPT_STORY_INPUTS_JSONL,
    slide_visuals_jsonl: Path = SLIDE_VISUAL_MEMOS_JSONL,
    source_memos_jsonl: Path = SOURCE_PAGE_MEMOS_JSONL,
    manual_requests_jsonl: Path = MANUAL_SOURCE_REQUESTS_JSONL,
    lessons_jsonl: Path = DRIVE_SEED_LESSONS_JSONL,
    matches_jsonl: Path = DRIVE_BROADCAST_MATCHES_JSONL,
    output_jsonl: Path = PPT_STORY_ARC_MEMOS_JSONL,
    report_md: Path = PPT_STORY_ARC_REPORT_MD,
    report_dir: Path = PPT_STORY_ARC_REPORT_DIR,
    ppt_limit: int = 0,
    show_progress: bool = True,
) -> list[dict[str, Any]]:
    story_inputs = _read_jsonl_if_exists(story_inputs_jsonl)
    story_inputs = story_inputs if ppt_limit <= 0 else story_inputs[:ppt_limit]
    slide_rows_by_ppt = _group_by_ppt(_read_jsonl_if_exists(slide_visuals_jsonl))
    source_memos_by_ppt = _group_by_ppt(_read_jsonl_if_exists(source_memos_jsonl))
    manual_by_ppt = _group_by_ppt(_read_jsonl_if_exists(manual_requests_jsonl))
    lessons = _records_by_id(_read_jsonl_if_exists(lessons_jsonl))
    matches = _records_by_id(_read_jsonl_if_exists(matches_jsonl))
    memos: list[dict[str, Any]] = []
    report_dir.mkdir(parents=True, exist_ok=True)
    for story_input in _progress(story_inputs, desc="story arcs", enabled=show_progress):
        ppt_id = str(story_input.get("ppt_id") or "")
        memo = story_arc_memo_from_inputs(
            story_input=story_input,
            slide_rows=slide_rows_by_ppt.get(ppt_id, []),
            source_memos=source_memos_by_ppt.get(ppt_id, []),
            manual_rows=manual_by_ppt.get(ppt_id, []),
            lesson=lessons.get(ppt_id),
            match=matches.get(ppt_id),
        )
        memos.append(memo)
        (report_dir / f"{ppt_id}.md").write_text(
            _single_story_arc_markdown(memo),
            encoding="utf-8",
        )
    write_jsonl(output_jsonl, memos)
    report_md.parent.mkdir(parents=True, exist_ok=True)
    report_md.write_text(
        _story_arc_report_markdown(
            memos=memos,
            output_jsonl=output_jsonl,
            report_dir=report_dir,
        ),
        encoding="utf-8",
    )
    return memos


def _single_story_arc_markdown(memo: dict[str, Any]) -> str:
    lines = [
        f"# PPT Story Arc: {memo.get('clean_title') or memo.get('ppt_title')}",
        "",
        f"- ppt_id: `{memo.get('ppt_id')}`",
        f"- confidence: {memo.get('story_arc_confidence')}",
        f"- main_hook: {memo.get('main_hook')}",
        f"- story_opening: {memo.get('story_opening')}",
        f"- broadcast_label: {memo.get('broadcast_label') or '-'}",
        f"- matched_video_title: {memo.get('matched_video_title') or '-'}",
        f"- contact_sheet: `{memo.get('contact_sheet_path') or '-'}`",
        f"- usable_source_memo_count: {memo.get('usable_source_memo_count')}",
        f"- raw_source_memo_count: {memo.get('raw_source_memo_count')}",
        f"- unusable_source_memo_count: {memo.get('unusable_source_memo_count')}",
        "- manual_or_auth_gaps: "
        f"{memo.get('manual_or_auth_gaps', {}).get('manual_request_count', 0)}",
        "",
        "## Story Arc Summary",
        "",
        str(memo.get("story_arc_summary") or ""),
        "",
        "## Initial Seed Source",
        "",
    ]
    seed = memo.get("initial_seed_source") or {}
    if seed:
        lines.extend(
            [
                f"- slide: {seed.get('slide_number')}",
                f"- domain: {seed.get('domain') or '-'}",
                f"- title: {seed.get('title') or '-'}",
                f"- status: {seed.get('access_status') or '-'}",
                f"- url: {seed.get('normalized_url') or '-'}",
            ]
        )
    else:
        lines.append("- none")
    lines.extend(["", "## Source Memo Quality", ""])
    quality_counts = memo.get("source_memo_quality_counts", {})
    if quality_counts:
        lines.extend([f"- {name}: {count}" for name, count in quality_counts.items()])
    else:
        lines.append("- none")
    lines.extend(
        [
            "",
            "## Source Expansion Path",
            "",
            *([f"- {item}" for item in memo.get("source_expansion_path", [])] or ["- none"]),
            "",
            "## Role Segments",
            "",
            "| slides | role | count | sample | domains |",
            "| --- | --- | ---: | --- | --- |",
        ]
    )
    for segment in memo.get("role_segments", []):
        lines.append(
            "| "
            + " | ".join(
                [
                    f"{segment.get('start_slide')}-{segment.get('end_slide')}",
                    _table_cell(segment.get("story_role")),
                    str(segment.get("slide_count")),
                    _table_cell("; ".join(segment.get("sample_slide_titles", [])[:2])),
                    _table_cell(", ".join(segment.get("sample_domains", [])[:5])),
                ]
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "## Visual Proof Sequence",
            "",
            "| slide | role | visual types | domains | memo titles |",
            "| ---: | --- | --- | --- | --- |",
        ]
    )
    for row in memo.get("visual_proof_sequence", [])[:25]:
        lines.append(
            "| "
            + " | ".join(
                [
                    str(row.get("slide_number")),
                    _table_cell(row.get("story_role")),
                    _table_cell(", ".join(row.get("visual_types", [])[:5])),
                    _table_cell(", ".join(row.get("source_domains", [])[:5])),
                    _table_cell("; ".join(row.get("source_memo_titles", [])[:3])),
                ]
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "## Numbers Sequence",
            "",
            "| slide | numbers | source titles |",
            "| ---: | --- | --- |",
        ]
    )
    for row in memo.get("numbers_sequence", [])[:20]:
        lines.append(
            "| "
            + " | ".join(
                [
                    str(row.get("slide_number")),
                    _table_cell(", ".join(row.get("numbers", [])[:6])),
                    _table_cell("; ".join(row.get("source_memo_titles", [])[:3])),
                ]
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "## Signals For Jibi",
            "",
            *([f"- {item}" for item in memo.get("jibi_teachable_signals", [])] or ["- none"]),
            "",
            "## Manual/Auth Gaps",
            "",
        ]
    )
    gaps = memo.get("manual_or_auth_gaps", {})
    if gaps.get("examples"):
        for item in gaps["examples"][:12]:
            lines.append(
                f"- slide {item.get('slide_number')}: {item.get('domain')} "
                f"({item.get('reason')})"
            )
    else:
        lines.append("- none")
    lines.extend(
        [
            "",
            "## Slide Outline",
            "",
            "| slide | role | brief | domains | memo titles |",
            "| ---: | --- | --- | --- | --- |",
        ]
    )
    for row in memo.get("slide_by_slide_story_outline", [])[:120]:
        lines.append(
            "| "
            + " | ".join(
                [
                    str(row.get("slide_number")),
                    _table_cell(row.get("story_role")),
                    _table_cell(row.get("slide_brief")),
                    _table_cell(", ".join(row.get("source_domains", [])[:4])),
                    _table_cell("; ".join(row.get("source_memo_titles", [])[:2])),
                ]
            )
            + " |"
        )
    return "\n".join(lines) + "\n"


def _story_arc_report_markdown(
    *,
    memos: list[dict[str, Any]],
    output_jsonl: Path,
    report_dir: Path,
) -> str:
    confidence_counts = Counter(str(memo.get("story_arc_confidence")) for memo in memos)
    broadcast_counts = Counter(str(memo.get("broadcast_label") or "unknown") for memo in memos)
    signal_counts = Counter(
        signal for memo in memos for signal in memo.get("jibi_teachable_signals", [])
    )
    manual_total = sum(
        int(memo.get("manual_or_auth_gaps", {}).get("manual_request_count") or 0)
        for memo in memos
    )
    raw_memo_total = sum(int(memo.get("raw_source_memo_count") or 0) for memo in memos)
    usable_memo_total = sum(int(memo.get("usable_source_memo_count") or 0) for memo in memos)
    unusable_memo_total = sum(
        int(memo.get("unusable_source_memo_count") or 0) for memo in memos
    )
    quality_counts = Counter(
        quality
        for memo in memos
        for quality, count in memo.get("source_memo_quality_counts", {}).items()
        for _ in range(int(count or 0))
    )
    lines = [
        "# PPT Story Arc Report",
        "",
        "Stage 4 rule-based story arc memos from slide visuals and source memos.",
        "No LLM calls. Full article bodies are not stored.",
        "",
        "## Outputs",
        "",
        f"- story_arc_memos_jsonl: `{_repo_relative(output_jsonl)}`",
        f"- story_arc_report_dir: `{_repo_relative(report_dir)}`",
        "",
        "## Summary",
        "",
        f"- ppt_count: {len(memos)}",
        f"- slide_count: {sum(int(memo.get('slide_count') or 0) for memo in memos)}",
        f"- usable_source_memo_count: {usable_memo_total}",
        f"- raw_source_memo_count: {raw_memo_total}",
        f"- unusable_source_memo_count: {unusable_memo_total}",
        f"- manual_or_auth_gap_count: {manual_total}",
        *[f"- confidence.{name}: {count}" for name, count in sorted(confidence_counts.items())],
        *[f"- broadcast.{name}: {count}" for name, count in sorted(broadcast_counts.items())],
        "",
        "## Source Memo Quality",
        "",
        *[f"- {name}: {count}" for name, count in quality_counts.most_common()],
        "",
        "## Jibi Teachable Signals",
        "",
        *[f"- {name}: {count}" for name, count in signal_counts.most_common(20)],
        "",
        "## Story Arc Memos",
        "",
        "| title | confidence | hook | usable/raw source memos | manual gaps | "
        "contact sheet | report |",
        "| --- | --- | --- | ---: | ---: | --- | --- |",
    ]
    for memo in memos:
        report_path = report_dir / f"{memo.get('ppt_id')}.md"
        lines.append(
            "| "
            + " | ".join(
                [
                    _table_cell(memo.get("clean_title")),
                    _table_cell(memo.get("story_arc_confidence")),
                    _table_cell(memo.get("main_hook")),
                    f"{memo.get('usable_source_memo_count') or 0}/"
                    f"{memo.get('raw_source_memo_count') or 0}",
                    str(memo.get("manual_or_auth_gaps", {}).get("manual_request_count") or 0),
                    _table_cell(memo.get("contact_sheet_path")),
                    _table_cell(_repo_relative(report_path)),
                ]
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "## Next Stage",
            "",
            "- Review individual PPT markdown files for story-shape accuracy.",
            "- Feed high-confidence story arcs into Jibi/Anny/Piti lesson prompts.",
            "- Resolve manual/auth gaps before using paywalled articles as positive evidence.",
        ]
    )
    return "\n".join(lines) + "\n"


def build_ppt_learning_quality_report(
    *,
    inventory_jsonl: Path = INVENTORY_JSONL,
    sources_jsonl: Path = SLIDE_SOURCES_JSONL,
    matches_jsonl: Path = BROADCAST_MATCHES_JSONL,
    lessons_jsonl: Path = SEED_LESSONS_JSONL,
    review_queue_jsonl: Path = SEED_LESSON_REVIEW_QUEUE_JSONL,
    review_queue_report_md: Path = SEED_LESSON_REVIEW_QUEUE_REPORT_MD,
    report_md: Path = QUALITY_REPORT_MD,
    show_progress: bool = True,
) -> str:
    inventory = _read_jsonl_if_exists(inventory_jsonl)
    sources = _read_jsonl_if_exists(sources_jsonl)
    matches = _read_jsonl_if_exists(matches_jsonl)
    lessons = _read_jsonl_if_exists(lessons_jsonl)
    queue = build_seed_lesson_review_queue(
        inventory_jsonl=inventory_jsonl,
        sources_jsonl=sources_jsonl,
        matches_jsonl=matches_jsonl,
        lessons_jsonl=lessons_jsonl,
        output_jsonl=review_queue_jsonl,
        report_md=review_queue_report_md,
        show_progress=show_progress,
    )
    markdown = _quality_report_markdown(
        inventory=inventory,
        sources=sources,
        matches=matches,
        lessons=lessons,
        queue=queue,
        report_md=report_md,
        review_queue_jsonl=review_queue_jsonl,
    )
    report_md.parent.mkdir(parents=True, exist_ok=True)
    report_md.write_text(markdown, encoding="utf-8")
    return markdown


def _quality_report_markdown(
    *,
    inventory: list[dict[str, Any]],
    sources: list[dict[str, Any]],
    matches: list[dict[str, Any]],
    lessons: list[dict[str, Any]],
    queue: list[dict[str, Any]],
    report_md: Path,
    review_queue_jsonl: Path,
) -> str:
    source_summary = _source_summary_by_ppt(sources)
    bucket_counts = Counter(str(row.get("review_bucket")) for row in queue)
    label_counts = Counter(str(row.get("broadcast_label") or "not_found") for row in matches)
    canonical_domains = Counter(
        canonical_domain(domain)
        for record in sources
        for domain in record.get("url_domains", [])
        if canonical_domain(domain)
    )
    category_counts = Counter(
        source_domain_category(domain)
        for record in sources
        for domain in record.get("url_domains", [])
        if canonical_domain(domain)
    )
    url_by_ppt = {
        ppt_id: int(summary.get("url_count") or 0)
        for ppt_id, summary in source_summary.items()
    }
    zero_url = [row for row in inventory if url_by_ppt.get(str(row.get("ppt_id")), 0) == 0]
    low_density = []
    for row in inventory:
        slide_count = int(row.get("slide_count") or 0)
        url_count = url_by_ppt.get(str(row.get("ppt_id")), 0)
        if slide_count >= 30 and slide_count and url_count / slide_count < 0.2:
            low_density.append((url_count / slide_count, url_count, slide_count, row))
    noisy_number_rows = [
        row for row in queue if row.get("numbers_noise_dropped")
    ]
    title_mismatch = [
        row
        for row in queue
        if row.get("broadcast_label") in {"likely_used", "maybe_used"}
        and float(row.get("title_similarity") or 0) < 0.42
    ]
    lines = [
        "# PPT Learning Drive Quality Report",
        "",
        "PR2 visible cleanup report generated from existing PR1 JSONL outputs. No PPT reparsing.",
        "",
        "## Coverage",
        "",
        f"- report_md: `{_repo_relative(report_md)}`",
        f"- review_queue_jsonl: `{_repo_relative(review_queue_jsonl)}`",
        f"- ppt_count: {len(inventory)}",
        f"- slide_source_records: {len(sources)}",
        f"- extracted_url_count: {sum(len(row.get('extracted_urls', [])) for row in sources)}",
        f"- seed_lesson_count: {len(lessons)}",
        "",
        "## Review Queue Buckets",
        "",
        *[f"- {bucket}: {count}" for bucket, count in sorted(bucket_counts.items())],
        "",
        "## Source Mix",
        "",
        *[f"- {category}: {count}" for category, count in category_counts.most_common()],
        "",
        "## Top Clean Domains",
        "",
        *[f"- {domain}: {count}" for domain, count in canonical_domains.most_common(20)],
        "",
        "## Broadcast Match Caution",
        "",
        *[f"- {label}: {count}" for label, count in sorted(label_counts.items())],
        "",
        "Treat `likely_used` as review priority, `maybe_used` as weak candidate, and "
        "`excluded_non_syukaworld` as do-not-use-as-positive.",
        "",
        "## Best Clean Seed Lessons",
        "",
    ]
    gold = [row for row in queue if row.get("review_bucket") == "gold"][:20]
    if gold:
        for row in gold:
            lines.append(
                f"- {row.get('clean_title')}: {row.get('main_seed_hook')} "
                f"({', '.join(row.get('jibi_candidate_signals', [])[:6])})"
            )
    else:
        lines.append("- none")
    lines.extend(["", "## Zero URL PPTs", ""])
    lines.extend(
        [f"- {row.get('title')} ({row.get('slide_count')} slides)" for row in zero_url[:30]]
        or ["- none"]
    )
    lines.extend(["", "## Low URL Density PPTs", ""])
    if low_density:
        for density, url_count, slide_count, row in sorted(
            low_density,
            key=lambda item: (item[0], item[1], item[2], str(item[3].get("title") or "")),
        )[:30]:
            lines.append(
                f"- {row.get('title')}: {url_count} URLs / {slide_count} slides "
                f"({density:.3f})"
            )
    else:
        lines.append("- none")
    lines.extend(["", "## Noisy Number Examples", ""])
    if noisy_number_rows:
        for row in noisy_number_rows[:30]:
            lines.append(
                f"- {row.get('clean_title')}: dropped "
                f"{', '.join(row.get('numbers_noise_dropped', [])[:6])}; kept "
                f"{', '.join(row.get('numbers_used_clean', [])[:6])}"
            )
    else:
        lines.append("- none")
    lines.extend(["", "## Title Mismatch Broadcast Candidates", ""])
    if title_mismatch:
        for row in title_mismatch[:40]:
            lines.append(
                f"- {row.get('clean_title')} -> {row.get('matched_video_title')} "
                f"({row.get('broadcast_label')}, score={row.get('match_score')})"
            )
    else:
        lines.append("- none")
    return "\n".join(lines) + "\n"


def combined_sample_markdown(
    *,
    inventory: list[dict[str, Any]],
    sources: list[dict[str, Any]],
    matches: list[dict[str, Any]],
    lessons: list[dict[str, Any]],
) -> str:
    domain_counts: Counter[str] = Counter(
        domain for record in sources for domain in record.get("url_domains", [])
    )
    evidence_counts: Counter[str] = Counter(
        evidence for record in sources for evidence in record.get("evidence_types", [])
    )
    label_counts: Counter[str] = Counter(
        str(record.get("broadcast_label") or "unknown") for record in matches
    )
    signal_counts: Counter[str] = Counter(
        signal for record in lessons for signal in record.get("jibi_candidate_signals", [])
    )
    best_lessons = sorted(
        lessons,
        key=lambda record: (
            len(record.get("jibi_candidate_signals", [])),
            len(record.get("initial_seed_sources", [])),
        ),
        reverse=True,
    )[:5]
    near_misses = [
        record
        for record in matches
        if record.get("broadcast_label") in {"not_found", "maybe_used", "excluded_non_syukaworld"}
    ]
    lines = [
        "# PPT Learning Sample Report",
        "",
        "PR1 sample report generated from local manifest inputs only.",
        "",
        "## Sample Inventory",
        "",
        f"- sample_ppt_count: {len(inventory)}",
        f"- local_exists: {sum(1 for item in inventory if item.get('local_exists'))}",
        f"- missing: {sum(1 for item in inventory if not item.get('local_exists'))}",
        "",
        "| ppt | researcher | status | slides | urls |",
        "| --- | --- | --- | ---: | ---: |",
    ]
    url_by_ppt: Counter[str] = Counter()
    for source in sources:
        url_by_ppt[str(source.get("ppt_id"))] += len(source.get("extracted_urls", []))
    for item in inventory:
        lines.append(
            "| "
            + " | ".join(
                [
                    _table_cell(item.get("title")),
                    _table_cell(item.get("researcher")),
                    _table_cell(item.get("path_status")),
                    str(item.get("slide_count", 0)),
                    str(url_by_ppt.get(str(item.get("ppt_id")), 0)),
                ]
            )
            + " |"
        )
    lines.extend(["", "## Top Source Domains", ""])
    lines.extend(
        [f"- {domain}: {count}" for domain, count in domain_counts.most_common(15)]
        or ["- none"]
    )
    lines.extend(["", "## Evidence Type Distribution", ""])
    lines.extend(
        [f"- {evidence}: {count}" for evidence, count in evidence_counts.most_common()]
        or ["- none"]
    )
    lines.extend(["", "## Broadcast Match Label Distribution", ""])
    lines.extend(
        [f"- {label}: {count}" for label, count in sorted(label_counts.items())]
        or ["- none"]
    )
    lines.extend(["", "## Best Jibi Seed Lessons", ""])
    if best_lessons:
        for record in best_lessons:
            lines.append(
                f"- {record.get('ppt_title')}: {record.get('main_seed_hook')} "
                f"({', '.join(record.get('jibi_candidate_signals', [])[:6])})"
            )
    else:
        lines.append("- none")
    lines.extend(["", "## Near-miss / Not-found PPTs", ""])
    if near_misses:
        for record in near_misses:
            lines.append(
                f"- {record.get('ppt_title')}: {record.get('broadcast_label')} "
                f"({record.get('notes')})"
            )
    else:
        lines.append("- none")
    lines.extend(["", "## What To Teach Jibi Next", ""])
    lines.extend(
        [f"- {signal}: {count}" for signal, count in signal_counts.most_common(12)]
        or ["- Run seed lesson extraction to populate teaching signals."]
    )
    return "\n".join(lines) + "\n"


@build_drive_manifest_app.callback(invoke_without_command=True)
def build_drive_manifest_main(
    latest_root: Annotated[
        Path,
        typer.Option("--latest-root", help="Unzipped latest Drive PPT root."),
    ] = paths.DATA_DIR / "ppt_learning" / "drive_raw" / "latest",
    past_root: Annotated[
        Path,
        typer.Option("--past-root", help="Unzipped past Drive PPT root."),
    ] = paths.DATA_DIR / "ppt_learning" / "drive_raw" / "past",
    output_jsonl: Annotated[
        Path,
        typer.Option("--output-jsonl", help="Drive PPT manifest JSONL output path."),
    ] = DRIVE_MANIFEST,
    non_ppt_report_md: Annotated[
        Path,
        typer.Option("--non-ppt-report-md", help="Markdown report for excluded non-PPT files."),
    ] = DRIVE_NON_PPT_REPORT_MD,
) -> None:
    records = build_drive_manifest(
        latest_root=latest_root,
        past_root=past_root,
        output_jsonl=output_jsonl,
        non_ppt_report_md=non_ppt_report_md,
    )
    console.print(f"[green]Wrote {len(records)} Drive PPT manifest rows to {output_jsonl}[/green]")


@build_inventory_app.callback(invoke_without_command=True)
def build_inventory_main(
    manifest: Annotated[
        Path,
        typer.Option("--manifest", help="Sample PPT manifest JSONL."),
    ] = DEFAULT_MANIFEST,
    output_jsonl: Annotated[
        Path,
        typer.Option("--output-jsonl", help="Inventory JSONL output path."),
    ] = INVENTORY_JSONL,
    report_md: Annotated[
        Path,
        typer.Option("--report-md", help="Inventory Markdown report path."),
    ] = INVENTORY_REPORT_MD,
) -> None:
    records = build_inventory(manifest=manifest, output_jsonl=output_jsonl, report_md=report_md)
    console.print(f"[green]Wrote {len(records)} PPT inventory records to {output_jsonl}[/green]")


@extract_sources_app.callback(invoke_without_command=True)
def extract_sources_main(
    manifest: Annotated[
        Path,
        typer.Option("--manifest", help="Sample PPT manifest JSONL."),
    ] = DEFAULT_MANIFEST,
    output_jsonl: Annotated[
        Path,
        typer.Option("--output-jsonl", help="Slide source JSONL output path."),
    ] = SLIDE_SOURCES_JSONL,
) -> None:
    records = extract_slide_sources(manifest=manifest, output_jsonl=output_jsonl)
    url_count = sum(len(record.get("extracted_urls", [])) for record in records)
    console.print(
        f"[green]Wrote {len(records)} slide source records "
        f"({url_count} URLs) to {output_jsonl}[/green]"
    )


@match_broadcast_app.callback(invoke_without_command=True)
def match_broadcast_main(
    manifest: Annotated[
        Path,
        typer.Option("--manifest", help="Sample PPT manifest JSONL."),
    ] = DEFAULT_MANIFEST,
    syuka_data_dir: Annotated[
        Path,
        typer.Option("--syuka-data-dir", help="Local syuka-ops data directory, read-only."),
    ] = DEFAULT_SYUKA_DATA_DIR,
    output_jsonl: Annotated[
        Path,
        typer.Option("--output-jsonl", help="Broadcast match JSONL output path."),
    ] = BROADCAST_MATCHES_JSONL,
    report_md: Annotated[
        Path,
        typer.Option("--report-md", help="Broadcast match Markdown report path."),
    ] = BROADCAST_REPORT_MD,
) -> None:
    records = match_broadcast_usage(
        manifest=manifest,
        syuka_data_dir=syuka_data_dir,
        output_jsonl=output_jsonl,
        report_md=report_md,
    )
    counts = Counter(str(record.get("broadcast_label")) for record in records)
    console.print(
        f"[green]Wrote {len(records)} broadcast match records to {output_jsonl}: "
        f"{dict(sorted(counts.items()))}[/green]"
    )


@extract_lessons_app.callback(invoke_without_command=True)
def extract_lessons_main(
    manifest: Annotated[
        Path,
        typer.Option("--manifest", help="Sample PPT manifest JSONL."),
    ] = DEFAULT_MANIFEST,
    output_jsonl: Annotated[
        Path,
        typer.Option("--output-jsonl", help="Jibi seed lesson JSONL output path."),
    ] = SEED_LESSONS_JSONL,
    report_md: Annotated[
        Path,
        typer.Option("--report-md", help="Jibi seed lesson Markdown report path."),
    ] = SEED_LESSON_REPORT_MD,
) -> None:
    records = extract_jibi_seed_lessons(
        manifest=manifest,
        output_jsonl=output_jsonl,
        report_md=report_md,
    )
    console.print(f"[green]Wrote {len(records)} Jibi seed lessons to {output_jsonl}[/green]")


@combined_report_app.callback(invoke_without_command=True)
def combined_report_main(
    inventory_jsonl: Annotated[
        Path,
        typer.Option("--inventory-jsonl", help="Inventory JSONL input path."),
    ] = INVENTORY_JSONL,
    sources_jsonl: Annotated[
        Path,
        typer.Option("--sources-jsonl", help="Slide source JSONL input path."),
    ] = SLIDE_SOURCES_JSONL,
    matches_jsonl: Annotated[
        Path,
        typer.Option("--matches-jsonl", help="Broadcast match JSONL input path."),
    ] = BROADCAST_MATCHES_JSONL,
    lessons_jsonl: Annotated[
        Path,
        typer.Option("--lessons-jsonl", help="Seed lesson JSONL input path."),
    ] = SEED_LESSONS_JSONL,
    report_md: Annotated[
        Path,
        typer.Option("--report-md", help="Combined Markdown report output path."),
    ] = SAMPLE_REPORT_MD,
) -> None:
    markdown = write_combined_report(
        inventory_jsonl=inventory_jsonl,
        sources_jsonl=sources_jsonl,
        matches_jsonl=matches_jsonl,
        lessons_jsonl=lessons_jsonl,
        report_md=report_md,
    )
    console.print(f"[green]Wrote combined PPT learning report to {report_md}[/green]")
    console.print(f"[green]{len(markdown.splitlines())} report lines[/green]")


@quality_report_app.callback(invoke_without_command=True)
def quality_report_main(
    inventory_jsonl: Annotated[
        Path,
        typer.Option("--inventory-jsonl", help="Inventory JSONL input path."),
    ] = INVENTORY_JSONL,
    sources_jsonl: Annotated[
        Path,
        typer.Option("--sources-jsonl", help="Slide source JSONL input path."),
    ] = SLIDE_SOURCES_JSONL,
    matches_jsonl: Annotated[
        Path,
        typer.Option("--matches-jsonl", help="Broadcast match JSONL input path."),
    ] = BROADCAST_MATCHES_JSONL,
    lessons_jsonl: Annotated[
        Path,
        typer.Option("--lessons-jsonl", help="Seed lesson JSONL input path."),
    ] = SEED_LESSONS_JSONL,
    review_queue_jsonl: Annotated[
        Path,
        typer.Option("--review-queue-jsonl", help="Review queue JSONL output path."),
    ] = SEED_LESSON_REVIEW_QUEUE_JSONL,
    review_queue_report_md: Annotated[
        Path,
        typer.Option("--review-queue-report-md", help="Review queue Markdown output path."),
    ] = SEED_LESSON_REVIEW_QUEUE_REPORT_MD,
    report_md: Annotated[
        Path,
        typer.Option("--report-md", help="Quality Markdown report output path."),
    ] = QUALITY_REPORT_MD,
    progress: Annotated[
        bool,
        typer.Option("--progress/--no-progress", help="Show tqdm progress while post-processing."),
    ] = True,
) -> None:
    markdown = build_ppt_learning_quality_report(
        inventory_jsonl=inventory_jsonl,
        sources_jsonl=sources_jsonl,
        matches_jsonl=matches_jsonl,
        lessons_jsonl=lessons_jsonl,
        review_queue_jsonl=review_queue_jsonl,
        review_queue_report_md=review_queue_report_md,
        report_md=report_md,
        show_progress=progress,
    )
    queue = _read_jsonl_if_exists(review_queue_jsonl)
    counts = Counter(str(row.get("review_bucket")) for row in queue)
    console.print(
        f"[green]Wrote PPT learning quality report to {report_md}; "
        f"queue={dict(sorted(counts.items()))}[/green]"
    )
    console.print(f"[green]{len(markdown.splitlines())} report lines[/green]")


@enrichment_queue_app.callback(invoke_without_command=True)
def enrichment_queue_main(
    inventory_jsonl: Annotated[
        Path,
        typer.Option("--inventory-jsonl", help="Inventory JSONL input path."),
    ] = DRIVE_INVENTORY_JSONL,
    sources_jsonl: Annotated[
        Path,
        typer.Option("--sources-jsonl", help="Slide source JSONL input path."),
    ] = DRIVE_SLIDE_SOURCES_JSONL,
    matches_jsonl: Annotated[
        Path,
        typer.Option("--matches-jsonl", help="Broadcast match JSONL input path."),
    ] = DRIVE_BROADCAST_MATCHES_JSONL,
    lessons_jsonl: Annotated[
        Path,
        typer.Option("--lessons-jsonl", help="Seed lesson JSONL input path."),
    ] = DRIVE_SEED_LESSONS_JSONL,
    review_queue_jsonl: Annotated[
        Path,
        typer.Option("--review-queue-jsonl", help="Seed lesson review queue JSONL input path."),
    ] = SEED_LESSON_REVIEW_QUEUE_JSONL,
    output_jsonl: Annotated[
        Path,
        typer.Option("--output-jsonl", help="PPT enrichment queue JSONL output path."),
    ] = PPT_ENRICHMENT_QUEUE_JSONL,
    url_queue_jsonl: Annotated[
        Path,
        typer.Option("--url-queue-jsonl", help="Flat URL enrichment queue JSONL output path."),
    ] = PPT_ENRICHMENT_URL_QUEUE_JSONL,
    report_md: Annotated[
        Path,
        typer.Option("--report-md", help="Enrichment queue Markdown report output path."),
    ] = PPT_ENRICHMENT_QUEUE_REPORT_MD,
    max_urls_per_ppt: Annotated[
        int,
        typer.Option(
            "--max-urls-per-ppt",
            help="Maximum priority URLs retained per PPT; use 0 or negative to keep all.",
        ),
    ] = 30,
    progress: Annotated[
        bool,
        typer.Option("--progress/--no-progress", help="Show tqdm progress while building queue."),
    ] = True,
) -> None:
    ppt_rows, url_rows = build_ppt_enrichment_queue(
        inventory_jsonl=inventory_jsonl,
        sources_jsonl=sources_jsonl,
        matches_jsonl=matches_jsonl,
        lessons_jsonl=lessons_jsonl,
        review_queue_jsonl=review_queue_jsonl,
        output_jsonl=output_jsonl,
        url_queue_jsonl=url_queue_jsonl,
        report_md=report_md,
        max_urls_per_ppt=max_urls_per_ppt,
        show_progress=progress,
    )
    status_counts = Counter(str(row.get("enrichment_status")) for row in ppt_rows)
    console.print(
        f"[green]Wrote PPT enrichment queue to {output_jsonl}; "
        f"ppts={len(ppt_rows)}, urls={len(url_rows)}, "
        f"status={dict(sorted(status_counts.items()))}[/green]"
    )


@source_fetch_app.callback(invoke_without_command=True)
def source_fetch_main(
    url_queue_jsonl: Annotated[
        Path,
        typer.Option("--url-queue-jsonl", help="Flat URL enrichment queue JSONL input path."),
    ] = PPT_ENRICHMENT_URL_QUEUE_JSONL,
    output_jsonl: Annotated[
        Path,
        typer.Option("--output-jsonl", help="Source page memo JSONL output path."),
    ] = SOURCE_PAGE_MEMOS_JSONL,
    status_jsonl: Annotated[
        Path,
        typer.Option("--status-jsonl", help="Fetch status JSONL output path."),
    ] = SOURCE_FETCH_STATUS_JSONL,
    manual_requests_jsonl: Annotated[
        Path,
        typer.Option("--manual-requests-jsonl", help="Manual/auth request JSONL output path."),
    ] = MANUAL_SOURCE_REQUESTS_JSONL,
    report_md: Annotated[
        Path,
        typer.Option("--report-md", help="Source fetch Markdown report output path."),
    ] = SOURCE_FETCH_REPORT_MD,
    limit: Annotated[
        int,
        typer.Option("--limit", help="Maximum public/optional URL fetch attempts; 0 keeps all."),
    ] = 50,
    ppt_limit: Annotated[
        int,
        typer.Option("--ppt-limit", help="Number of top-ranked PPTs to include; 0 keeps all."),
    ] = 10,
    timeout: Annotated[
        float,
        typer.Option("--timeout", help="Per-URL fetch timeout in seconds."),
    ] = 12,
    include_optional: Annotated[
        bool,
        typer.Option(
            "--include-optional/--public-first-only",
            help="Also fetch optional low-priority public/reference URLs.",
        ),
    ] = False,
    progress: Annotated[
        bool,
        typer.Option("--progress/--no-progress", help="Show tqdm progress while fetching."),
    ] = True,
) -> None:
    memos, status_rows, manual_requests = fetch_ppt_source_memos(
        url_queue_jsonl=url_queue_jsonl,
        output_jsonl=output_jsonl,
        status_jsonl=status_jsonl,
        manual_requests_jsonl=manual_requests_jsonl,
        report_md=report_md,
        limit=limit,
        ppt_limit=ppt_limit,
        timeout=timeout,
        include_optional=include_optional,
        show_progress=progress,
    )
    status_counts = Counter(str(row.get("access_status") or "unknown") for row in status_rows)
    console.print(
        f"[green]Wrote PPT source memos to {output_jsonl}; "
        f"memos={len(memos)}, status={dict(sorted(status_counts.items()))}, "
        f"manual_requests={len(manual_requests)}[/green]"
    )


@slide_visual_app.callback(invoke_without_command=True)
def slide_visual_main(
    enrichment_queue_jsonl: Annotated[
        Path,
        typer.Option("--enrichment-queue-jsonl", help="PPT enrichment queue JSONL input path."),
    ] = PPT_ENRICHMENT_QUEUE_JSONL,
    slide_sources_jsonl: Annotated[
        Path,
        typer.Option("--slide-sources-jsonl", help="Slide source JSONL input path."),
    ] = DRIVE_SLIDE_SOURCES_JSONL,
    source_memos_jsonl: Annotated[
        Path,
        typer.Option("--source-memos-jsonl", help="Source page memo JSONL input path."),
    ] = SOURCE_PAGE_MEMOS_JSONL,
    output_jsonl: Annotated[
        Path,
        typer.Option("--output-jsonl", help="Slide visual memo JSONL output path."),
    ] = SLIDE_VISUAL_MEMOS_JSONL,
    story_inputs_jsonl: Annotated[
        Path,
        typer.Option("--story-inputs-jsonl", help="PPT story input JSONL output path."),
    ] = PPT_STORY_INPUTS_JSONL,
    report_md: Annotated[
        Path,
        typer.Option("--report-md", help="Slide visual Markdown report output path."),
    ] = SLIDE_VISUAL_REPORT_MD,
    render_output_dir: Annotated[
        Path,
        typer.Option("--render-output-dir", help="Internal contact-sheet render output directory."),
    ] = PPT_SLIDE_VISUAL_RENDER_DIR,
    slide_images_dir: Annotated[
        Path,
        typer.Option("--slide-images-dir", help="Copied per-slide thumbnail output directory."),
    ] = PPT_SLIDE_IMAGES_DIR,
    contact_sheets_dir: Annotated[
        Path,
        typer.Option("--contact-sheets-dir", help="Copied contact sheet output directory."),
    ] = PPT_CONTACT_SHEETS_DIR,
    ppt_limit: Annotated[
        int,
        typer.Option("--ppt-limit", help="Number of top-ranked PPTs to process; 0 keeps all."),
    ] = 5,
    progress: Annotated[
        bool,
        typer.Option("--progress/--no-progress", help="Show tqdm progress while processing PPTs."),
    ] = True,
) -> None:
    visual_rows, story_rows = build_ppt_slide_visual_memos(
        enrichment_queue_jsonl=enrichment_queue_jsonl,
        slide_sources_jsonl=slide_sources_jsonl,
        source_memos_jsonl=source_memos_jsonl,
        output_jsonl=output_jsonl,
        story_inputs_jsonl=story_inputs_jsonl,
        report_md=report_md,
        render_output_dir=render_output_dir,
        slide_images_dir=slide_images_dir,
        contact_sheets_dir=contact_sheets_dir,
        ppt_limit=ppt_limit,
        show_progress=progress,
    )
    render_counts = Counter(str(row.get("render_status") or "unknown") for row in story_rows)
    console.print(
        f"[green]Wrote PPT slide visual memos to {output_jsonl}; "
        f"ppts={len(story_rows)}, slides={len(visual_rows)}, "
        f"render={dict(sorted(render_counts.items()))}[/green]"
    )


@story_arc_app.callback(invoke_without_command=True)
def story_arc_main(
    story_inputs_jsonl: Annotated[
        Path,
        typer.Option("--story-inputs-jsonl", help="PPT story input JSONL input path."),
    ] = PPT_STORY_INPUTS_JSONL,
    slide_visuals_jsonl: Annotated[
        Path,
        typer.Option("--slide-visuals-jsonl", help="Slide visual memo JSONL input path."),
    ] = SLIDE_VISUAL_MEMOS_JSONL,
    source_memos_jsonl: Annotated[
        Path,
        typer.Option("--source-memos-jsonl", help="Source page memo JSONL input path."),
    ] = SOURCE_PAGE_MEMOS_JSONL,
    manual_requests_jsonl: Annotated[
        Path,
        typer.Option("--manual-requests-jsonl", help="Manual/auth request JSONL input path."),
    ] = MANUAL_SOURCE_REQUESTS_JSONL,
    lessons_jsonl: Annotated[
        Path,
        typer.Option("--lessons-jsonl", help="Seed lesson JSONL input path."),
    ] = DRIVE_SEED_LESSONS_JSONL,
    matches_jsonl: Annotated[
        Path,
        typer.Option("--matches-jsonl", help="Broadcast match JSONL input path."),
    ] = DRIVE_BROADCAST_MATCHES_JSONL,
    output_jsonl: Annotated[
        Path,
        typer.Option("--output-jsonl", help="Story arc memo JSONL output path."),
    ] = PPT_STORY_ARC_MEMOS_JSONL,
    report_md: Annotated[
        Path,
        typer.Option("--report-md", help="Story arc Markdown report output path."),
    ] = PPT_STORY_ARC_REPORT_MD,
    report_dir: Annotated[
        Path,
        typer.Option("--report-dir", help="Per-PPT story arc Markdown report directory."),
    ] = PPT_STORY_ARC_REPORT_DIR,
    ppt_limit: Annotated[
        int,
        typer.Option("--ppt-limit", help="Number of PPT story inputs to process; 0 keeps all."),
    ] = 0,
    progress: Annotated[
        bool,
        typer.Option("--progress/--no-progress", help="Show tqdm progress while building arcs."),
    ] = True,
) -> None:
    memos = build_ppt_story_arc_memos(
        story_inputs_jsonl=story_inputs_jsonl,
        slide_visuals_jsonl=slide_visuals_jsonl,
        source_memos_jsonl=source_memos_jsonl,
        manual_requests_jsonl=manual_requests_jsonl,
        lessons_jsonl=lessons_jsonl,
        matches_jsonl=matches_jsonl,
        output_jsonl=output_jsonl,
        report_md=report_md,
        report_dir=report_dir,
        ppt_limit=ppt_limit,
        show_progress=progress,
    )
    confidence_counts = Counter(str(row.get("story_arc_confidence")) for row in memos)
    console.print(
        f"[green]Wrote PPT story arc memos to {output_jsonl}; "
        f"ppts={len(memos)}, confidence={dict(sorted(confidence_counts.items()))}[/green]"
    )
