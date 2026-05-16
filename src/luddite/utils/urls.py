"""URL extraction and canonicalization."""

from __future__ import annotations

import re
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

TRACKING_PARAMS = {
    "fbclid",
    "gclid",
    "igshid",
    "mc_cid",
    "mc_eid",
}

URL_RE = re.compile(r"https?://[^\s<>'\"“”‘’\]\}]+", re.IGNORECASE)
TRAILING_PUNCTUATION = ".,;:!?)]}》」』”’"


def _strip_url_punctuation(url: str) -> str:
    return url.rstrip(TRAILING_PUNCTUATION)


def canonicalize_url(url: str) -> str:
    """Normalize tracking-noisy URLs while preserving meaningful query params."""
    url = _strip_url_punctuation(url.strip())
    if not url:
        return url

    parts = urlsplit(url)
    query_pairs = []
    for key, value in parse_qsl(parts.query, keep_blank_values=True):
        lower_key = key.lower()
        if lower_key.startswith("utm_") or lower_key in TRACKING_PARAMS:
            continue
        query_pairs.append((key, value))

    query = urlencode(query_pairs, doseq=True)
    path = parts.path
    if path != "/" and path.endswith("/"):
        path = path.rstrip("/")

    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), path, query, ""))


def extract_urls(text: str | None) -> list[str]:
    """Extract canonical, de-duplicated URLs in first-seen order."""
    if not text:
        return []

    urls: list[str] = []
    seen: set[str] = set()
    for match in URL_RE.finditer(text):
        canonical = canonicalize_url(match.group(0))
        if canonical and canonical not in seen:
            seen.add(canonical)
            urls.append(canonical)
    return urls
