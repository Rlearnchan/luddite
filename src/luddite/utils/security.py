"""Redaction and lightweight source/risk helpers."""

from __future__ import annotations

import re
from typing import Any

from luddite.utils.urls import extract_urls

SENSITIVE_LABELS = [
    "아이디",
    "ID",
    "계정",
    "비번",
    "PW",
    "비밀번호",
    "전화",
    "전화번호",
    "연락처",
    "메일",
    "이메일",
    "인증 담당자",
]

LABEL_RE = re.compile(
    rf"({'|'.join(re.escape(label) for label in SENSITIVE_LABELS)})\s*[:：=]\s*[^\s,;|/]+",
    re.IGNORECASE,
)
EMAIL_RE = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
PHONE_RE = re.compile(r"\b(?:\+?82[-\s]?)?0?1[016789][-\s]?\d{3,4}[-\s]?\d{4}\b")

RISK_KEYWORDS = {
    "political_sensitivity": ["정당", "대선", "선거", "지지율", "국회", "대통령"],
    "medical_claim_risk": ["치료", "의료", "시술", "효과", "환자"],
    "investment_advice_risk": ["매수", "매도", "수익률", "원금", "투자 조언"],
    "crime_or_drug_sensitivity": ["마약", "코카인", "범죄", "추심"],
    "corporate_promo_risk": ["광고주", "협찬", "프로모션", "출시"],
}

SOURCE_NOTE_RE = re.compile(r"^\s*\[(?P<label>[^\]]+)\]\s*(?P<value>.+?)\s*$")


def redact_sensitive_text(text: str | None) -> str:
    """Mask credentials and personal contact patterns."""
    if not text:
        return ""
    redacted = LABEL_RE.sub(lambda m: f"{m.group(1)}: [REDACTED]", text)
    redacted = EMAIL_RE.sub("[REDACTED_EMAIL]", redacted)
    redacted = PHONE_RE.sub("[REDACTED_PHONE]", redacted)
    return redacted


def contains_sensitive_text(text: str | None) -> bool:
    if not text:
        return False
    return text != redact_sensitive_text(text)


def validate_no_credentials(payload: Any) -> bool:
    """Return False when a nested payload still appears to contain credentials."""
    if isinstance(payload, dict):
        return all(validate_no_credentials(value) for value in payload.values())
    if isinstance(payload, list):
        return all(validate_no_credentials(value) for value in payload)
    if isinstance(payload, str):
        return not contains_sensitive_text(payload)
    return True


def detect_risk_flags(text: str | None, metadata: dict[str, Any] | None = None) -> list[str]:
    """Lightweight parser-time risk hints using the schema risk vocabulary."""
    combined = f"{text or ''} {metadata or ''}"
    flags: list[str] = []
    for flag, keywords in RISK_KEYWORDS.items():
        if any(keyword.lower() in combined.lower() for keyword in keywords):
            flags.append(flag)
    if contains_sensitive_text(combined):
        flags.append("needs_human_review")
    return sorted(set(flags))


def extract_source_notes(notes: str | None) -> list[dict[str, Any]]:
    """Parse speaker-note source lines such as `[내용] https://...`."""
    if not notes:
        return []

    source_notes: list[dict[str, Any]] = []
    for line in notes.splitlines():
        match = SOURCE_NOTE_RE.match(line)
        if not match:
            continue
        label = match.group("label").strip()
        value = match.group("value").strip()
        source_notes.append(
            {
                "label": label,
                "value": redact_sensitive_text(value),
                "urls": extract_urls(value),
                "is_image": "이미지" in label,
                "is_todo": "TODO" in label.upper(),
                "is_gpt_generated": "GPT 생성" in value,
            }
        )
    return source_notes
