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
    group: str | None = None
    role: str | None = None
    region: str | None = None
    category_hint: str | None = None
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
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.split("#", 1)[0].rstrip()
        stripped = line.strip()
        if not stripped or stripped == "sources:":
            continue
        if stripped.startswith("- "):
            if current:
                sources.append(current)
            current = {}
            stripped = stripped[2:].strip()
            if stripped and ":" in stripped:
                key, value = stripped.split(":", 1)
                current[key.strip()] = _parse_scalar(value)
            continue
        if current is not None and ":" in stripped:
            key, value = stripped.split(":", 1)
            current[key.strip()] = _parse_scalar(value)
    if current:
        sources.append(current)

    return [
        Source(
            id=str(item["id"]),
            name=str(item.get("name", item["id"])),
            type=str(item.get("type", "manual")),
            group=item.get("group") if isinstance(item.get("group"), str) else None,
            role=item.get("role") if isinstance(item.get("role"), str) else None,
            region=item.get("region") if isinstance(item.get("region"), str) else None,
            category_hint=(
                item.get("category_hint") if isinstance(item.get("category_hint"), str) else None
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
