"""Report-only second-search plans for reviewed Jibi candidates."""

from __future__ import annotations

import json
import re
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Any

import typer
from rich.console import Console

from luddite import paths
from luddite.agents.jibi.review_feedback import infer_review_feedback

app = typer.Typer(no_args_is_help=False)
console = Console()

ACTION_PURPOSES = {
    "find_supporting_links": "보강 출처 찾기",
    "find_current_news_hook": "최신 뉴스 hook 찾기",
    "narrow_to_concrete_question": "구체 질문으로 좁히기",
    "find_specific_case_or_odd_hook": "특정 사례나 의외성 찾기",
    "check_past_topic_differentiation": "과거 주제와 차별점 확인",
    "reframe_around_stronger_real_economy_angle": "더 강한 실물경제 프레임 찾기",
    "demote_to_evidence_or_background": "근거/배경 자료로 낮추기",
    "avoid_market_advice_frame": "투자 조언 프레임 회피",
    "keep_question_as_editorial_anchor": "좋은 질문을 편집 축으로 유지",
}

ACTION_EXPECTED_EVIDENCE = {
    "find_supporting_links": "독립 기사 2개, 숫자, 사례, 반대 근거",
    "find_current_news_hook": "최근 뉴스, 정책 발표, 시장/생활 변화 신호",
    "narrow_to_concrete_question": "가장 설명력이 큰 원인 1개와 검증 가능한 수치",
    "find_specific_case_or_odd_hook": "시청자가 바로 이해할 수 있는 특정 사례",
    "check_past_topic_differentiation": "과거 슈카월드 주제와 다른 새 각도",
    "reframe_around_stronger_real_economy_angle": "생활비, 노동, 산업, 금융 흐름으로 옮길 근거",
    "demote_to_evidence_or_background": "큰 이야기 안에서 쓸 수 있는 공식 근거",
    "avoid_market_advice_frame": "개별 종목/투자 판단을 피할 산업·제도 프레임",
    "keep_question_as_editorial_anchor": "리뷰어가 반응한 질문을 뒷받침할 자료",
}

STOPWORDS = {
    "그리고",
    "그러나",
    "위한",
    "관련",
    "후보",
    "자료",
    "설명",
    "선정",
    "이유",
    "다음",
    "조사",
    "핵심",
    "질문",
    "입니다",
    "합니다",
    "가능",
    "확인",
}


def compact_text(value: object) -> str:
    return " ".join(str(value or "").split())


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _default_feedback_path(run_date: str) -> Path:
    return paths.REPORTS_DIR / f"jibi_review_feedback_{run_date}.json"


def _default_metadata_path(run_date: str) -> Path:
    return paths.OUTPUTS_DIR / "daily_digest" / f"{run_date}_bundle_review_sheet_metadata.json"


def _default_markdown_path(run_date: str) -> Path:
    return paths.REPORTS_DIR / f"jibi_second_search_plan_{run_date}.md"


def _default_json_path(run_date: str) -> Path:
    return paths.REPORTS_DIR / f"jibi_second_search_plan_{run_date}.json"


def _index_by_id(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {
        compact_text(row.get("ID") or row.get("id") or row.get("review_item_id")): row
        for row in rows
        if compact_text(row.get("ID") or row.get("id") or row.get("review_item_id"))
    }


def _topic_signals(text: str) -> list[str]:
    lower = text.lower()
    signals: list[str] = []
    if "청년" in text and any(term in text for term in ("쉬었음", "경제활동", "노동시장")):
        signals.extend(["청년 쉬었음", "경제활동참가율", "비경제활동인구"])
    if "토큰화" in text or "조각투자" in text or re.search(r"\brwa\b", lower):
        signals.extend(["자산 토큰화", "RWA", "STO", "조각투자"])
    if "ai" in lower or "인공지능" in text:
        signals.extend(["공공 AI", "AI 활용 가이드라인", "AI 책임"])
    if any(term in text for term in ("무료배달", "배달비", "수수료", "플랫폼")):
        signals.extend(["무료배달", "배달앱 수수료", "자영업자 부담"])
    if "양파" in text:
        signals.extend(["양파 산지 가격", "농산물 가격", "소비촉진"])
    if any(term in text for term in ("유가", "고유가", "에너지")):
        signals.extend(["유가", "에너지 가격", "물류비"])
    if any(term in text for term in ("pf", "프로젝트 파이낸스", "메가뱅크")):
        signals.extend(["프로젝트 파이낸스", "미국 제조업", "데이터센터 투자"])
    return list(dict.fromkeys(signals))


def _keyword_candidates(text: str) -> list[str]:
    tokens = [
        re.sub(r"^[^\w가-힣]+|[^\w가-힣]+$", "", token)
        for token in re.split(r"\s+", text)
    ]
    cleaned = [
        token
        for token in tokens
        if len(token) >= 2 and token.lower() not in STOPWORDS and token not in STOPWORDS
    ]
    return list(dict.fromkeys(cleaned))[:6]


def _topic_terms(row: dict[str, Any], metadata: dict[str, Any]) -> list[str]:
    title = compact_text(row.get("title") or metadata.get("title"))
    text = " ".join(
        compact_text(value)
        for value in [
            title,
            metadata.get("description"),
            metadata.get("auto_description"),
            metadata.get("source"),
            metadata.get("seed_type"),
            " ".join(str(item) for item in metadata.get("story_role_reasons", [])),
        ]
    )
    signals = _topic_signals(text)
    if signals:
        return signals[:5]
    return _keyword_candidates(title or text)


def _source_suggestions(metadata: dict[str, Any]) -> list[str]:
    source_role = compact_text(metadata.get("source_role") or metadata.get("source_role_class"))
    seed_type = compact_text(metadata.get("seed_type"))
    if source_role == "research_note":
        return ["연합뉴스", "관련 부처/기관 원자료", "통계청·한국은행 통계", "해외/국내 해설 기사"]
    if source_role == "policy_release":
        return ["연합뉴스", "부처 원자료", "통계·예산 자료", "현장/업계 반응 기사"]
    if source_role == "public_wire":
        return ["원문 기관", "두 번째 언론 기사", "통계·보고서", "반대/우려 사례"]
    if source_role == "market_wire" or "market" in seed_type:
        return ["공시/회사 원자료", "산업 지표", "규제·제도 자료", "개별 종목 판단을 피할 비교 기사"]
    if source_role == "academic_explainer":
        return ["원문 연구/논문", "최근 뉴스 사례", "한국 연결 자료", "반론 또는 한계"]
    return ["독립 언론 기사", "원자료", "통계 자료", "반대 사례"]


def _reviewer_payloads(row: dict[str, Any]) -> list[dict[str, Any]]:
    reviewers = row.get("reviewers")
    if not isinstance(reviewers, dict):
        return []
    payloads: list[dict[str, Any]] = []
    for payload in reviewers.values():
        if not isinstance(payload, dict):
            continue
        note = compact_text(payload.get("raw_note") or payload.get("note"))
        if note:
            payloads.append(infer_review_feedback(note))
    return payloads


def _row_signal(row: dict[str, Any]) -> str:
    direct = compact_text(row.get("row_review_signal"))
    if direct:
        return direct
    signals = [
        compact_text(payload.get("review_signal"))
        for payload in _reviewer_payloads(row)
        if compact_text(payload.get("review_signal")) != "unlabeled"
    ]
    if not signals:
        return "unreviewed"
    decisive = set(signals)
    if "reject" in decisive and decisive.intersection({"strong", "conditional"}):
        return "mixed"
    if "strong" in decisive and decisive.intersection({"weak", "conditional"}):
        return "conditional"
    for signal in ["strong", "conditional", "weak", "reject"]:
        if signal in decisive:
            return signal
    return "unreviewed"


def _row_list_field(row: dict[str, Any], field: str) -> list[str]:
    direct = row.get(field)
    if isinstance(direct, list):
        return [str(item) for item in direct if str(item).strip()]
    values: list[str] = []
    for payload in _reviewer_payloads(row):
        values.extend(str(item) for item in payload.get(field.replace("row_", ""), []))
    return list(dict.fromkeys(value for value in values if value))


def _operator_lesson(row: dict[str, Any], title: str) -> str:
    direct = compact_text(row.get("operator_lesson"))
    if direct:
        return direct
    failures = set(_row_list_field(row, "row_failure_modes"))
    positives = set(_row_list_field(row, "row_positive_signals"))
    if "wrong_frame" in failures:
        return f"{title}: 현재 프레임이 빗나갔습니다. 더 강한 실물경제/생활 질문으로 초점을 옮기세요."
    if failures.intersection({"evidence_not_seed", "needs_news_hook"}):
        return f"{title}: 자료 자체보다 최신 뉴스나 현상 hook을 먼저 찾아야 합니다."
    if "needs_supporting_links" in failures:
        return f"{title}: 이 자료 하나로는 약합니다. 숫자, 사례, 독립 출처를 보강하세요."
    if "too_broad" in failures:
        return f"{title}: 범위가 너무 큽니다. 구체 사례와 좁은 질문으로 다시 잡으세요."
    if "good_question" in positives:
        return f"{title}: 좋은 질문이 잡혀 있습니다. 이 질문을 중심으로 후속 조사를 이어가세요."
    signal = _row_signal(row)
    if signal == "reject":
        return f"{title}: 현재 형태로는 낮추거나 제외하는 편이 안전합니다."
    if signal in {"strong", "conditional", "mixed"}:
        return f"{title}: 리뷰 신호가 있습니다. 보강 검색 후 seed/evidence 역할을 다시 판단하세요."
    return ""


def _priority(row: dict[str, Any]) -> str:
    signal = _row_signal(row)
    failures = set(_row_list_field(row, "row_failure_modes"))
    positives = set(_row_list_field(row, "row_positive_signals"))
    actions = set(_row_list_field(row, "row_next_research_actions"))
    if signal == "reject" and "good_question" not in positives:
        return "low"
    if failures.intersection({"needs_supporting_links", "needs_news_hook", "wrong_frame"}):
        return "high"
    if actions.intersection({"find_supporting_links", "find_current_news_hook"}):
        return "high"
    if signal in {"strong", "conditional", "mixed"}:
        return "medium"
    return "low"


def _default_actions(row: dict[str, Any], metadata: dict[str, Any]) -> list[str]:
    actions = _row_list_field(row, "row_next_research_actions")
    story_role = compact_text(metadata.get("story_role"))
    if not actions and story_role == "seed_with_supporting_links":
        actions = ["find_supporting_links", "find_current_news_hook"]
    if not actions and story_role in {"evidence_for_larger_story", "background_reference"}:
        actions = ["demote_to_evidence_or_background"]
    if not actions and row.get("row_review_signal") in {"strong", "conditional"}:
        actions = ["keep_question_as_editorial_anchor", "find_supporting_links"]
    return list(dict.fromkeys(actions))


def _query_for_action(action: str, terms: list[str], title: str) -> list[str]:
    topic = terms[0] if terms else title
    secondary = terms[1] if len(terms) > 1 else ""
    if action == "find_supporting_links":
        return [
            f"{topic} 통계 사례",
            f"{topic} {secondary} 한국 영향".strip(),
            f"{topic} 반론 리스크",
        ]
    if action == "find_current_news_hook":
        return [f"{topic} 최신 뉴스", f"{topic} 2026", f"{topic} 최근 정책 발표"]
    if action == "narrow_to_concrete_question":
        return [f"{topic} 원인 쟁점", f"{topic} 숫자 통계", f"{topic} 사례"]
    if action == "find_specific_case_or_odd_hook":
        return [f"{topic} 특이 사례", f"{topic} 논란", f"{topic} 현장 사례"]
    if action == "check_past_topic_differentiation":
        return [f"{topic} 슈카월드", f"{topic} 과거 방송", f"{topic} 유사 주제"]
    if action == "reframe_around_stronger_real_economy_angle":
        return [f"{topic} 실물경제 영향", f"{topic} 생활비 노동 산업", f"{topic} 구조 변화"]
    if action == "avoid_market_advice_frame":
        return [f"{topic} 산업 구조", f"{topic} 제도 리스크", f"{topic} 시장 전체 영향"]
    if action == "keep_question_as_editorial_anchor":
        return [f"{topic} 왜 중요한가", f"{topic} 생활 영향", f"{topic} 숫자"]
    return [topic] if topic else [title]


def _query_plan(
    actions: list[str],
    terms: list[str],
    title: str,
) -> list[dict[str, Any]]:
    tasks: list[dict[str, Any]] = []
    for action in actions:
        if action == "demote_to_evidence_or_background":
            tasks.append(
                {
                    "action": action,
                    "purpose": ACTION_PURPOSES[action],
                    "queries": [],
                    "expected_evidence": ACTION_EXPECTED_EVIDENCE[action],
                    "note": "검색보다 큰 story bundle에 붙일 위치를 먼저 정한다.",
                }
            )
            continue
        queries = list(dict.fromkeys(_query_for_action(action, terms, title)))[:3]
        tasks.append(
            {
                "action": action,
                "purpose": ACTION_PURPOSES.get(action, action),
                "queries": queries,
                "expected_evidence": ACTION_EXPECTED_EVIDENCE.get(action, "보강 자료"),
            }
        )
    return tasks


def _why_search(row: dict[str, Any], metadata: dict[str, Any], actions: list[str]) -> str:
    lesson = _operator_lesson(row, compact_text(row.get("title") or metadata.get("title")))
    if lesson:
        return lesson
    if metadata.get("story_role") == "seed_with_supporting_links":
        return "seed 가능성은 있지만 두 번째 출처와 최신 hook이 필요합니다."
    if "demote_to_evidence_or_background" in actions:
        return "단독 seed보다 큰 이야기의 evidence로 쓰는 편이 안전합니다."
    return "리뷰 피드백을 바탕으로 추가 판단 자료가 필요합니다."


def build_second_search_plan(
    *,
    run_date: str,
    feedback_summary: dict[str, Any],
    metadata_payload: dict[str, Any],
    limit: int | None = None,
) -> dict[str, Any]:
    metadata_by_id = _index_by_id(metadata_payload.get("rows", []))
    rows = feedback_summary.get("rows", [])
    plans: list[dict[str, Any]] = []
    for row in rows:
        row_id = compact_text(row.get("id"))
        metadata = metadata_by_id.get(row_id, {})
        actions = _default_actions(row, metadata)
        if not actions:
            continue
        title = compact_text(row.get("title") or metadata.get("title"))
        terms = _topic_terms(row, metadata)
        query_plan = _query_plan(actions, terms, title)
        plans.append(
            {
                "id": row_id,
                "title": title,
                "priority": _priority(row),
                "review_signal": _row_signal(row),
                "source": compact_text(metadata.get("source")),
                "source_role": compact_text(
                    metadata.get("source_role") or metadata.get("source_role_class")
                ),
                "seed_type": compact_text(metadata.get("seed_type")),
                "story_role": compact_text(metadata.get("story_role")),
                "failure_modes": _row_list_field(row, "row_failure_modes"),
                "positive_signals": _row_list_field(row, "row_positive_signals"),
                "actions": actions,
                "topic_terms": terms,
                "source_suggestions": _source_suggestions(metadata),
                "why_search": _why_search(row, metadata, actions),
                "query_plan": query_plan,
            }
        )
    priority_rank = {"high": 0, "medium": 1, "low": 2}
    plans.sort(
        key=lambda item: (
            priority_rank.get(str(item.get("priority")), 9),
            str(item.get("title")),
        )
    )
    if limit is not None:
        plans = plans[:limit]
    action_counts = Counter(action for plan in plans for action in plan["actions"])
    priority_counts = Counter(str(plan["priority"]) for plan in plans)
    return {
        "run_date": run_date,
        "generated_at": datetime.now(UTC).isoformat(),
        "feedback_path": compact_text(feedback_summary.get("source_path")),
        "metadata_path": compact_text(metadata_payload.get("source_path")),
        "total_feedback_rows": len(rows),
        "planned_rows": len(plans),
        "priority_counts": dict(priority_counts),
        "action_counts": dict(action_counts),
        "plans": plans,
    }


def _table_cell(value: object) -> str:
    return compact_text(value).replace("|", "\\|") or "-"


def render_markdown(plan: dict[str, Any]) -> str:
    lines = [
        f"# Jibi Second-Search Plan — {plan['run_date']}",
        "",
        f"- Generated at: `{plan['generated_at']}`",
        f"- Feedback rows: {plan['total_feedback_rows']}",
        f"- Planned rows: {plan['planned_rows']}",
        "",
        "## Operator Summary",
        "",
    ]
    if not plan["plans"]:
        lines.append("- 추가 검색이 필요한 행이 없습니다.")
    else:
        lines.append(
            "- 우선순위 high는 바로 보강 검색 대상, medium은 질문/프레임 보존 대상, low는 evidence 보관 또는 후순위입니다."
        )
    lines.extend(["", "## Priority Counts", ""])
    for key in ["high", "medium", "low"]:
        lines.append(f"- {key}: {plan.get('priority_counts', {}).get(key, 0)}")
    lines.extend(["", "## Action Counts", ""])
    for action, count in sorted(plan.get("action_counts", {}).items()):
        lines.append(f"- {action}: {count}")
    lines.extend(["", "## Search Queue", ""])
    lines.append(
        "| priority | title | why | actions | first queries | source suggestions |"
    )
    lines.append("| --- | --- | --- | --- | --- | --- |")
    for item in plan["plans"]:
        queries: list[str] = []
        for task in item["query_plan"]:
            queries.extend(task.get("queries", []))
        lines.append(
            "| "
            + " | ".join(
                [
                    _table_cell(item["priority"]),
                    _table_cell(item["title"]),
                    _table_cell(item["why_search"]),
                    _table_cell(", ".join(item["actions"])),
                    _table_cell(" / ".join(queries[:4])),
                    _table_cell(", ".join(item["source_suggestions"][:4])),
                ]
            )
            + " |"
        )
    lines.extend(["", "## Detail", ""])
    for item in plan["plans"]:
        lines.append(f"### {item['title'] or item['id']}")
        lines.append("")
        lines.append(f"- ID: `{item['id']}`")
        lines.append(f"- priority: `{item['priority']}`")
        lines.append(f"- review_signal: `{item['review_signal'] or 'unknown'}`")
        lines.append(f"- story_role: `{item['story_role'] or 'unknown'}`")
        lines.append(f"- topic_terms: `{', '.join(item['topic_terms']) or 'none'}`")
        lines.append(f"- why_search: {item['why_search']}")
        for task in item["query_plan"]:
            lines.append(f"- {task['purpose']}:")
            if task.get("queries"):
                for query in task["queries"]:
                    lines.append(f"  - `{query}`")
            else:
                lines.append(f"  - {task.get('note', '검색 쿼리 없음')}")
            lines.append(f"  - expected: {task['expected_evidence']}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def write_second_search_plan(
    *,
    run_date: str,
    feedback_path: Path,
    metadata_path: Path,
    markdown_path: Path,
    json_path: Path,
    limit: int | None = None,
) -> tuple[Path, Path, dict[str, Any]]:
    feedback_summary = _load_json(feedback_path)
    metadata_payload = _load_json(metadata_path)
    feedback_summary["source_path"] = str(feedback_path)
    metadata_payload["source_path"] = str(metadata_path)
    plan = build_second_search_plan(
        run_date=run_date,
        feedback_summary=feedback_summary,
        metadata_payload=metadata_payload,
        limit=limit,
    )
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.write_text(render_markdown(plan), encoding="utf-8")
    json_path.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
    return markdown_path, json_path, plan


@app.command("main")
def main(
    date: Annotated[str, typer.Option("--date", help="Jibi run date YYYY-MM-DD.")] = "",
    feedback: Annotated[
        Path | None,
        typer.Option("--feedback", help="Review feedback JSON report."),
    ] = None,
    metadata: Annotated[
        Path | None,
        typer.Option("--metadata", help="Bundle review board metadata JSON."),
    ] = None,
    markdown: Annotated[
        Path | None,
        typer.Option("--markdown", help="Output markdown path."),
    ] = None,
    output_json: Annotated[
        Path | None,
        typer.Option("--json", help="Output JSON path."),
    ] = None,
    limit: Annotated[
        int | None,
        typer.Option("--limit", help="Optional max planned rows."),
    ] = None,
) -> None:
    run_date = date or datetime.now().strftime("%Y-%m-%d")
    md_path, json_path, plan = write_second_search_plan(
        run_date=run_date,
        feedback_path=feedback or _default_feedback_path(run_date),
        metadata_path=metadata or _default_metadata_path(run_date),
        markdown_path=markdown or _default_markdown_path(run_date),
        json_path=output_json or _default_json_path(run_date),
        limit=limit,
    )
    console.print(
        "[green]Wrote Jibi second-search plan "
        f"({plan['planned_rows']} rows): {md_path} / {json_path}[/green]"
    )


if __name__ == "__main__":
    typer.run(main)
