"""Small OpenAI Responses API client helpers for report-only Jibi workflows."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from luddite import paths

OPENAI_RESPONSES_URL = "https://api.openai.com/v1/responses"
DEFAULT_JIBI_LLM_MODEL = "gpt-5-mini"


def _env_files() -> list[Path]:
    roots = [paths.REPO_ROOT]
    env_dir = os.environ.get("LUDDITE_ENV_DIR")
    if env_dir:
        roots.append(Path(env_dir))
    files: list[Path] = []
    seen: set[Path] = set()
    for root in roots:
        for name in (".env", ".env.local"):
            path = root / name
            if path in seen:
                continue
            seen.add(path)
            files.append(path)
    return files


def load_env_files() -> None:
    """Load repo-local env files without overriding an already exported value."""
    for env_path in _env_files():
        if not env_path.exists():
            continue
        for line in env_path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or "=" not in stripped:
                continue
            key, value = stripped.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = value


def jibi_llm_model(model: str | None = None) -> str:
    """Return the Jibi LLM model, defaulting to the low-cost GPT-5 mini lane."""
    load_env_files()
    return (
        model
        or os.environ.get("JIBI_LLM_JUDGE_MODEL")
        or os.environ.get("LUDDITE_ANNY_API_MODEL")
        or DEFAULT_JIBI_LLM_MODEL
    )


def openai_api_key() -> str:
    load_env_files()
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("Missing required env var: OPENAI_API_KEY")
    return api_key


def is_jibi_llm_enabled() -> bool:
    load_env_files()
    return os.environ.get("JIBI_LLM_JUDGE", "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def extract_response_text(response_payload: dict[str, Any]) -> str:
    texts: list[str] = []
    for item in response_payload.get("output") or []:
        if not isinstance(item, dict):
            continue
        for content in item.get("content") or []:
            if not isinstance(content, dict):
                continue
            if content.get("type") in {"output_text", "text"} and content.get("text"):
                texts.append(str(content["text"]))
    return "\n".join(texts).strip()


class OpenAIResponsesClient:
    """Tiny urllib-backed client so Jibi does not require the OpenAI SDK."""

    def __init__(
        self,
        *,
        api_key: str | None = None,
        model: str | None = None,
        url: str = OPENAI_RESPONSES_URL,
    ) -> None:
        self.api_key = api_key or openai_api_key()
        self.model = jibi_llm_model(model)
        self.url = url

    def json_response(
        self,
        prompt: str,
        *,
        timeout_seconds: int = 120,
        max_output_tokens: int = 1200,
    ) -> tuple[str, dict[str, Any]]:
        payload: dict[str, Any] = {
            "model": self.model,
            "input": prompt,
            "text": {"format": {"type": "json_object"}},
            "max_output_tokens": max_output_tokens,
        }
        if self.model.startswith("gpt-5"):
            payload["reasoning"] = {"effort": "minimal"}
        request = urllib.request.Request(
            self.url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
                response_payload = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            error_body = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"OpenAI API HTTP {exc.code}: {error_body}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"OpenAI API request failed: {exc.reason}") from exc
        return extract_response_text(response_payload), response_payload


def parse_json_object(text: str) -> dict[str, Any]:
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise RuntimeError("LLM response was not valid JSON") from exc
    if not isinstance(payload, dict):
        raise RuntimeError("LLM response must be a JSON object")
    return payload
