import json
import sqlite3

from luddite.agents.jibi.syuka_snapshot_probe import probe_syuka_snapshot


def _write_queries(path, queries):
    path.write_text(
        json.dumps({"run_date": "2026-05-25", "queries": queries}, ensure_ascii=False),
        encoding="utf-8",
    )


def _make_syuka_db(path):
    conn = sqlite3.connect(path)
    conn.execute(
        """
        CREATE TABLE videos (
            video_id TEXT PRIMARY KEY,
            title TEXT,
            upload_date TEXT,
            view_count INTEGER,
            like_count INTEGER,
            source_url TEXT
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE video_analysis (
            video_id TEXT,
            summary TEXT,
            keywords_json TEXT
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE transcripts (
            video_id TEXT,
            dialogue TEXT
        )
        """
    )
    conn.execute(
        "INSERT INTO videos VALUES (?, ?, ?, ?, ?, ?)",
        (
            "vid_youth",
            "83~95년생의 삶을 추적해봤습니다 - 청년 노동시장",
            "20260501",
            1500000,
            32000,
            "https://youtu.be/youth",
        ),
    )
    conn.execute(
        "INSERT INTO video_analysis VALUES (?, ?, ?)",
        (
            "vid_youth",
            "쉬었음 청년과 경제활동참가율 하락을 다룬 영상",
            '["쉬었음", "경제활동참가율"]',
        ),
    )
    conn.execute(
        "INSERT INTO transcripts VALUES (?, ?)",
        ("vid_youth", "오늘은 청년 노동시장 이야기를 해보겠습니다."),
    )
    conn.execute(
        "INSERT INTO videos VALUES (?, ?, ?, ?, ?, ?)",
        (
            "vid_transcript",
            "여름 직장 문화",
            "20260512",
            900000,
            12000,
            "https://youtu.be/shorts",
        ),
    )
    conn.execute(
        "INSERT INTO video_analysis VALUES (?, ?, ?)",
        ("vid_transcript", "회사 생활 변화", '["회사"]'),
    )
    conn.execute(
        "INSERT INTO transcripts VALUES (?, ?)",
        ("vid_transcript", "반바지와 쿨비즈, 폭염에 대해 시청자들이 질문했습니다."),
    )
    conn.commit()
    conn.close()


def test_probe_syuka_snapshot_no_db_found_exits_with_report(tmp_path) -> None:
    queries = tmp_path / "queries.json"
    _write_queries(
        queries,
        [{"title": "새 후보", "query_terms": ["없는단어"], "priority": "high"}],
    )

    md_path, json_path, payload = probe_syuka_snapshot(
        run_date="2026-05-25",
        queries_json=queries,
        syuka_data_dir=tmp_path / "missing",
        output_md=tmp_path / "matches.md",
        output_json=tmp_path / "matches.json",
    )

    assert md_path.exists()
    assert json_path.exists()
    assert payload["snapshot_status"]["status"] == "no_db_found"
    assert payload["results"][0]["recommendation"] == "safe_new_angle"


def test_probe_syuka_snapshot_title_and_analysis_match(tmp_path) -> None:
    data_dir = tmp_path / "data" / "db"
    data_dir.mkdir(parents=True)
    _make_syuka_db(data_dir / "syuka_ops.db")
    queries = tmp_path / "queries.json"
    _write_queries(
        queries,
        [
            {
                "story_fingerprint": "youth_labor_exit",
                "title": "청년 노동시장 이탈",
                "priority": "high",
                "core_terms": ["쉬었음", "경제활동참가율", "청년 노동시장"],
                "context_terms": ["청년"],
                "negative_terms": [],
            }
        ],
    )

    _md, _json, payload = probe_syuka_snapshot(
        run_date="2026-05-25",
        queries_json=queries,
        syuka_data_dir=tmp_path / "data",
        output_md=tmp_path / "matches.md",
        output_json=tmp_path / "matches.json",
    )

    result = payload["results"][0]
    assert result["matches"][0]["video_id"] == "vid_youth"
    assert result["matches"][0]["like_count"] == 32000
    assert "title" in result["matches"][0]["matched_fields"]
    assert result["matches"][0]["recommendation"] == "duplicate"
    assert result["match_confidence"] == "high"
    assert result["match_reason"] == "core_title_match"
    assert result["display_on_board"] is True
    assert result["past_video_response_signal"] == "duplicate_do_not_repeat"


def test_probe_syuka_snapshot_transcript_only_needs_human_check(tmp_path) -> None:
    data_dir = tmp_path / "data" / "db"
    data_dir.mkdir(parents=True)
    _make_syuka_db(data_dir / "syuka_ops.db")
    queries = tmp_path / "queries.json"
    _write_queries(
        queries,
        [
            {
                "title": "반바지와 폭염",
                "priority": "high",
                "query_terms": ["쿨비즈", "폭염"],
                "negative_terms": [],
            }
        ],
    )

    _md, _json, payload = probe_syuka_snapshot(
        run_date="2026-05-25",
        queries_json=queries,
        syuka_data_dir=tmp_path / "data",
        output_md=tmp_path / "matches.md",
        output_json=tmp_path / "matches.json",
    )

    match = payload["results"][0]["matches"][0]
    assert match["video_id"] == "vid_transcript"
    assert match["matched_fields"] == ["transcript"]
    assert match["recommendation"] == "needs_human_check"
    assert payload["results"][0]["match_confidence"] == "low"
    assert payload["results"][0]["match_reason"] == "transcript_only"
    assert payload["results"][0]["display_on_board"] is False


def test_probe_syuka_snapshot_no_match_is_safe_new_angle(tmp_path) -> None:
    data_dir = tmp_path / "data" / "db"
    data_dir.mkdir(parents=True)
    _make_syuka_db(data_dir / "syuka_ops.db")
    queries = tmp_path / "queries.json"
    _write_queries(
        queries,
        [
            {
                "title": "낸드업체 매출",
                "priority": "low",
                "query_terms": ["1분기", "매출", "낸드업체"],
            }
        ],
    )

    _md, _json, payload = probe_syuka_snapshot(
        run_date="2026-05-25",
        queries_json=queries,
        syuka_data_dir=tmp_path / "data",
        output_md=tmp_path / "matches.md",
        output_json=tmp_path / "matches.json",
    )

    assert payload["results"][0]["matches"] == []
    assert payload["results"][0]["effective_query_terms"] == ["낸드업체"]
    assert payload["results"][0]["recommendation"] == "safe_new_angle"


def test_probe_syuka_snapshot_negative_terms_reduce_recommendation(tmp_path) -> None:
    data_dir = tmp_path / "data" / "db"
    data_dir.mkdir(parents=True)
    _make_syuka_db(data_dir / "syuka_ops.db")
    queries = tmp_path / "queries.json"
    _write_queries(
        queries,
        [
            {
                "title": "청년 노동시장",
                "priority": "high",
                "query_terms": ["청년 노동시장", "쉬었음"],
                "negative_terms": ["쉬었음"],
            }
        ],
    )

    _md, _json, payload = probe_syuka_snapshot(
        run_date="2026-05-25",
        queries_json=queries,
        syuka_data_dir=tmp_path / "data",
        output_md=tmp_path / "matches.md",
        output_json=tmp_path / "matches.json",
    )

    match = payload["results"][0]["matches"][0]
    assert match["negative_terms_matched"] == ["쉬었음"]
    assert match["recommendation"] == "needs_human_check"


def test_probe_syuka_snapshot_context_only_match_does_not_duplicate(tmp_path) -> None:
    data_dir = tmp_path / "data" / "db"
    data_dir.mkdir(parents=True)
    _make_syuka_db(data_dir / "syuka_ops.db")
    queries = tmp_path / "queries.json"
    _write_queries(
        queries,
        [
            {
                "title": "새로운 청년 이야기",
                "priority": "high",
                "core_terms": ["없는핵심"],
                "context_terms": ["청년 노동시장"],
                "negative_terms": [],
            }
        ],
    )

    _md, _json, payload = probe_syuka_snapshot(
        run_date="2026-05-25",
        queries_json=queries,
        syuka_data_dir=tmp_path / "data",
        output_md=tmp_path / "matches.md",
        output_json=tmp_path / "matches.json",
    )

    result = payload["results"][0]
    assert result["matches"][0]["recommendation"] == "adjacent"
    assert result["recommendation"] == "adjacent"


def test_probe_syuka_snapshot_alias_expansion_improves_expected_match(tmp_path) -> None:
    data_dir = tmp_path / "data" / "db"
    data_dir.mkdir(parents=True)
    _make_syuka_db(data_dir / "syuka_ops.db")
    queries = tmp_path / "queries.json"
    _write_queries(
        queries,
        [
            {
                "title": "비경제활동 청년",
                "priority": "high",
                "core_terms": ["비경제활동"],
                "context_terms": [],
                "negative_terms": [],
            }
        ],
    )

    _md, _json, payload = probe_syuka_snapshot(
        run_date="2026-05-25",
        queries_json=queries,
        syuka_data_dir=tmp_path / "data",
        output_md=tmp_path / "matches.md",
        output_json=tmp_path / "matches.json",
    )

    result = payload["results"][0]
    assert "쉬었음" in result["effective_core_terms"]
    assert result["matches"][0]["video_id"] == "vid_youth"
