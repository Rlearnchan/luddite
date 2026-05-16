from luddite.utils.urls import canonicalize_url, extract_urls


def test_canonicalize_url_removes_tracking() -> None:
    url = "https://Example.com/path/?utm_source=chatgpt.com&fbclid=abc&id=42#frag"
    assert canonicalize_url(url) == "https://example.com/path?id=42"


def test_extract_urls_deduplicates_after_canonicalization() -> None:
    text = "https://example.com/a?utm_source=x and https://example.com/a"
    assert extract_urls(text) == ["https://example.com/a"]
