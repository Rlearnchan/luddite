"""Small source registry loader for jibi local/manual collection."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit

from luddite import paths


@dataclass(frozen=True)
class Source:
    id: str
    name: str
    type: str
    status: str | None = None
    group: str | None = None
    role: str | None = None
    role_class: str | None = None
    region: str | None = None
    category_hint: str | None = None
    homepage_url: str | None = None
    rss_index_url: str | None = None
    desired_feed: str | None = None
    feed_url: str | None = None
    feed_url_candidates: tuple[str, ...] = ()
    verified_feed_url: str | None = None
    freshness_policy: str | None = None
    freshness_window_days: int | None = None
    terms_check_required: bool = False
    collection_enabled: bool = False
    last_probe_status: str | None = None
    last_probe_at: str | None = None
    failure_reason: str | None = None
    priority: int = 3
    subscription: bool = False
    auto_fetch: bool = False


def _parse_scalar(value: str) -> str | int | bool | None:
    value = value.strip()
    if value in {"", "null", "None"}:
        return None
    if value.lower() == "true":
        return True
    if value.lower() == "false":
        return False
    if value.isdigit():
        return int(value)
    return value.strip('"').strip("'")


def load_sources(path: Path = paths.SOURCE_REGISTRY_YAML) -> list[Source]:
    """Load the simple repo-local YAML source registry.

    This intentionally supports only the small list-of-dicts shape used in
    `config/sources.yaml`, avoiding a runtime dependency on PyYAML for now.
    """
    if not path.exists():
        return []

    sources: list[dict[str, object]] = []
    current: dict[str, object] | None = None
    list_key: str | None = None
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.split("#", 1)[0].rstrip()
        stripped = line.strip()
        if not stripped or stripped == "sources:":
            continue
        if (
            current is not None
            and list_key
            and raw_line.startswith("    ")
            and stripped.startswith("- ")
        ):
            if not isinstance(current.get(list_key), list):
                current[list_key] = []
            values = current[list_key]
            if isinstance(values, list):
                values.append(str(_parse_scalar(stripped[2:].strip()) or ""))
            continue
        if stripped.startswith("- "):
            if current:
                sources.append(current)
            current = {}
            stripped = stripped[2:].strip()
            if stripped and ":" in stripped:
                key, value = stripped.split(":", 1)
                current[key.strip()] = _parse_scalar(value)
                list_key = None
            continue
        if current is not None and ":" in stripped:
            key, value = stripped.split(":", 1)
            key = key.strip()
            parsed = _parse_scalar(value)
            current[key] = parsed
            list_key = key if parsed is None else None
    if current:
        sources.append(current)

    return [
        Source(
            id=str(item["id"]),
            name=str(item.get("name", item["id"])),
            type=str(item.get("type", "manual")),
            status=item.get("status") if isinstance(item.get("status"), str) else None,
            group=item.get("group") if isinstance(item.get("group"), str) else None,
            role=item.get("role") if isinstance(item.get("role"), str) else None,
            role_class=(
                item.get("role_class") if isinstance(item.get("role_class"), str) else None
            ),
            region=item.get("region") if isinstance(item.get("region"), str) else None,
            category_hint=(
                item.get("category_hint") if isinstance(item.get("category_hint"), str) else None
            ),
            homepage_url=(
                item.get("homepage_url") if isinstance(item.get("homepage_url"), str) else None
            ),
            rss_index_url=(
                item.get("rss_index_url") if isinstance(item.get("rss_index_url"), str) else None
            ),
            desired_feed=(
                item.get("desired_feed") if isinstance(item.get("desired_feed"), str) else None
            ),
            feed_url=item.get("feed_url") if isinstance(item.get("feed_url"), str) else None,
            feed_url_candidates=tuple(
                value for value in item.get("feed_url_candidates", []) if isinstance(value, str)
            )
            if isinstance(item.get("feed_url_candidates"), list)
            else (),
            verified_feed_url=(
                item.get("verified_feed_url")
                if isinstance(item.get("verified_feed_url"), str)
                else None
            ),
            freshness_policy=(
                item.get("freshness_policy")
                if isinstance(item.get("freshness_policy"), str)
                else None
            ),
            freshness_window_days=(
                int(item["freshness_window_days"])
                if isinstance(item.get("freshness_window_days"), int)
                else None
            ),
            terms_check_required=bool(item.get("terms_check_required", False)),
            collection_enabled=bool(item.get("collection_enabled", False)),
            last_probe_status=(
                item.get("last_probe_status")
                if isinstance(item.get("last_probe_status"), str)
                else None
            ),
            last_probe_at=(
                item.get("last_probe_at") if isinstance(item.get("last_probe_at"), str) else None
            ),
            failure_reason=(
                item.get("failure_reason") if isinstance(item.get("failure_reason"), str) else None
            ),
            priority=int(item.get("priority", 3) or 3),
            subscription=bool(item.get("subscription", False)),
            auto_fetch=bool(item.get("auto_fetch", False)),
        )
        for item in sources
        if item.get("id")
    ]


def source_by_id(path: Path = paths.SOURCE_REGISTRY_YAML) -> dict[str, Source]:
    return {source.id: source for source in load_sources(path)}


def match_source(
    *,
    source_value: str | None,
    url: str | None,
    registry_path: Path = paths.SOURCE_REGISTRY_YAML,
) -> Source:
    """Return the best registry source for a user-provided source/url pair."""
    sources = load_sources(registry_path)
    if not sources:
        return Source(id="manual", name=source_value or "Manual Input", type="manual")

    normalized = (source_value or "").strip().lower()
    for source in sources:
        if normalized in {source.id.lower(), source.name.lower()}:
            return source

    host = urlsplit(url or "").netloc.lower()
    for source in sources:
        compact_id = source.id.replace("_", "")
        compact_name = source.name.replace(" ", "").lower()
        if compact_id and compact_id in host.replace(".", ""):
            return source
        if compact_name and compact_name in host.replace(".", ""):
            return source

    return next((source for source in sources if source.id == "manual"), sources[0])
