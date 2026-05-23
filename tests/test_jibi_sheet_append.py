import csv

from luddite import paths
from luddite.agents.jibi.append_to_sheet import (
    BUNDLE_REVIEW_SHEET_COLUMNS,
    SHEET_COLUMNS,
    GoogleSheetAppendConfig,
    append_jibi_sheet,
    load_append_config,
)
from luddite.integrations.google_sheets import AppendResult

OLD_SHEET_COLUMNS = [
    "digest_date",
    "collected_at",
    "last_seen_at",
    "jibi_id",
    "duplicate_key",
    "source_url_canonical",
    "rank",
    "status",
    "주제명",
    "링크",
    "출처",
    "source_type",
    "jibi_grade",
    "total_score",
    "recommended_action",
    "risk_level",
    "risk_flags",
    "why_interesting",
    "possible_expansions",
    "evidence_needed",
    "중복후보",
    "reviewer",
    "review_result",
    "promoted_to_topic_finding",
    "notes",
]
SLIDEABILITY_COLUMNS = [
    "slideability_score",
    "slideability",
    "first_slide_idea",
    "likely_proof_object_types",
    "visual_risks",
]


class FakeGoogleSheetsClient:
    def __init__(self, *, sheet_id=None, values=None):
        self.sheet_id = sheet_id
        self.values = values or []
        self.created = False
        self.header_updates = []
        self.cleared = False
        self.appended = []
        self.formatted = []
        self.review_board_formats = []

    def get_sheet_id(self, spreadsheet_id: str, sheet_name: str) -> int | None:
        return self.sheet_id

    def create_sheet(self, spreadsheet_id: str, sheet_name: str) -> int:
        self.created = True
        self.sheet_id = 123
        return self.sheet_id

    def get_values(self, spreadsheet_id: str, sheet_name: str) -> list[list[str]]:
        return [list(row) for row in self.values]

    def update_values(
        self,
        spreadsheet_id: str,
        sheet_name: str,
        start_cell: str,
        values: list[list[str]],
    ) -> None:
        self.header_updates.append((start_cell, values))
        if len(values) > 1:
            self.values = [list(row) for row in values]
        else:
            self.values = [values[0], *self.values[1:]] if self.values else [values[0]]

    def clear_values(self, spreadsheet_id: str, sheet_name: str) -> None:
        self.cleared = True
        self.values = []

    def append_rows(
        self,
        spreadsheet_id: str,
        sheet_name: str,
        rows: list[list[str]],
    ) -> AppendResult:
        start = len(self.values) + 1
        self.appended.extend(rows)
        self.values.extend(rows)
        return AppendResult(start_row=start, end_row=start + len(rows) - 1)

    def format_rows(
        self,
        spreadsheet_id: str,
        sheet_id: int,
        start_row: int,
        end_row: int,
    ) -> None:
        self.formatted.append((sheet_id, start_row, end_row))

    def format_review_board(
        self,
        spreadsheet_id: str,
        sheet_id: int,
        *,
        row_count: int,
        column_count: int,
    ) -> None:
        self.review_board_formats.append((sheet_id, row_count, column_count))


def _write_preview(path, rows):
    with path.open("w", encoding="utf-8-sig", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=SHEET_COLUMNS)
        writer.writeheader()
        for row in rows:
            payload = {column: "" for column in SHEET_COLUMNS}
            payload.update(row)
            writer.writerow(payload)


def _write_bundle_review_preview(path, rows):
    with path.open("w", encoding="utf-8-sig", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=BUNDLE_REVIEW_SHEET_COLUMNS)
        writer.writeheader()
        for row in rows:
            payload = {column: "" for column in BUNDLE_REVIEW_SHEET_COLUMNS}
            payload.update(row)
            writer.writerow(payload)


def _sheet_values(row, columns=None):
    output_columns = columns or SHEET_COLUMNS
    return [
        {**{column: "" for column in output_columns}, **row}.get(column, "")
        for column in output_columns
    ]


def _row(title, duplicate_key, source_url):
    return {
        "digest_date": "2026-05-18",
        "collected_at": "2026-05-18T00:00:00+00:00",
        "last_seen_at": "2026-05-18T00:00:00+00:00",
        "jibi_id": f"jibi_{duplicate_key}",
        "duplicate_key": duplicate_key,
        "source_url_canonical": source_url,
        "rank": "1",
        "status": "new",
        "주제명": title,
        "링크": source_url,
        "출처": "Manual Input",
        "source_type": "manual",
        "jibi_grade": "B",
        "total_score": "71.4",
        "recommended_action": "gather_more_evidence",
        "risk_level": "low",
        "why_interesting": title,
        "possible_expansions": "확장 A | 확장 B | 확장 C",
        "evidence_needed": "추가 독립 출처",
    }


def test_sheet_columns_preserve_old_schema_prefix() -> None:
    assert SHEET_COLUMNS[:25] == OLD_SHEET_COLUMNS
    assert SHEET_COLUMNS[25:] == SLIDEABILITY_COLUMNS


def test_append_creates_sheet_header_and_appends_rows(tmp_path) -> None:
    preview = tmp_path / "2026-05-18_sheet_append_preview.csv"
    report_path = tmp_path / "report.md"
    _write_preview(preview, [_row("드론 비용 역전", "drone", "https://example.com/drone")])
    client = FakeGoogleSheetsClient(sheet_id=None)

    report = append_jibi_sheet(
        config=GoogleSheetAppendConfig(
            spreadsheet_id="spreadsheet",
            source_preview_csv=preview,
            dry_run=False,
            styling_enabled=True,
        ),
        client=client,
        report_path=report_path,
    )

    assert client.created is True
    assert client.header_updates == [("A1", [SHEET_COLUMNS])]
    assert len(client.appended) == 1
    assert client.formatted == [(123, 2, 2)]
    assert report.rows_appended == 1
    assert "Rows appended: 1" in report_path.read_text(encoding="utf-8")


def test_current_header_status_ok_does_not_update_header(tmp_path) -> None:
    preview = tmp_path / "2026-05-18_sheet_append_preview.csv"
    _write_preview(preview, [_row("신규 후보", "fresh", "https://example.com/fresh")])
    client = FakeGoogleSheetsClient(sheet_id=99, values=[SHEET_COLUMNS])

    report = append_jibi_sheet(
        config=GoogleSheetAppendConfig(
            spreadsheet_id="spreadsheet",
            source_preview_csv=preview,
            dry_run=False,
        ),
        client=client,
    )

    assert client.header_updates == []
    assert len(client.appended) == 1
    assert report.header_status == "ok"
    assert report.header_reason == "ok"
    assert report.header_safe_to_update is True
    assert report.header_updated is False


def test_real_append_upgrades_old_header(tmp_path) -> None:
    preview = tmp_path / "2026-05-18_sheet_append_preview.csv"
    _write_preview(preview, [_row("신규 후보", "fresh", "https://example.com/fresh")])
    existing_row = _row("기존", "old-key", "https://example.com/old")
    client = FakeGoogleSheetsClient(
        sheet_id=99,
        values=[OLD_SHEET_COLUMNS, _sheet_values(existing_row, OLD_SHEET_COLUMNS)],
    )

    report = append_jibi_sheet(
        config=GoogleSheetAppendConfig(
            spreadsheet_id="spreadsheet",
            source_preview_csv=preview,
            dry_run=False,
        ),
        client=client,
    )

    assert client.header_updates == [("A1", [SHEET_COLUMNS])]
    assert client.values[0] == SHEET_COLUMNS
    assert len(client.appended) == 1
    assert report.header_created is True
    assert report.header_status == "legacy_25_upgraded"
    assert report.header_reason == "legacy_25_known_schema"
    assert report.header_safe_to_update is True
    assert report.header_updated is True
    assert report.rows_appended == 1


def test_real_append_preserves_old_review_columns_when_header_upgrades(tmp_path) -> None:
    preview = tmp_path / "2026-05-18_sheet_append_preview.csv"
    _write_preview(preview, [_row("신규 후보", "fresh", "https://example.com/fresh")])
    existing_row = {
        **_row("기존 검토 후보", "old-key", "https://example.com/old"),
        "중복후보": "duplicate_of_123",
        "reviewer": "bae",
        "review_result": "keep",
        "promoted_to_topic_finding": "FALSE",
        "notes": "기존 사람이 남긴 메모",
    }
    old_values = _sheet_values(existing_row, OLD_SHEET_COLUMNS)
    client = FakeGoogleSheetsClient(sheet_id=99, values=[OLD_SHEET_COLUMNS, old_values])

    report = append_jibi_sheet(
        config=GoogleSheetAppendConfig(
            spreadsheet_id="spreadsheet",
            source_preview_csv=preview,
            dry_run=False,
        ),
        client=client,
    )

    upgraded_header = client.values[0]
    preserved_row = client.values[1]
    assert upgraded_header == SHEET_COLUMNS
    assert preserved_row[:25] == old_values
    assert preserved_row[upgraded_header.index("중복후보")] == "duplicate_of_123"
    assert preserved_row[upgraded_header.index("reviewer")] == "bae"
    assert preserved_row[upgraded_header.index("review_result")] == "keep"
    assert preserved_row[upgraded_header.index("promoted_to_topic_finding")] == "FALSE"
    assert preserved_row[upgraded_header.index("notes")] == "기존 사람이 남긴 메모"
    assert report.header_status == "legacy_25_upgraded"


def test_dry_run_reports_old_header_without_updating(tmp_path) -> None:
    preview = tmp_path / "2026-05-18_sheet_append_preview.csv"
    report_path = tmp_path / "report.md"
    _write_preview(preview, [_row("신규 후보", "fresh", "https://example.com/fresh")])
    client = FakeGoogleSheetsClient(sheet_id=99, values=[OLD_SHEET_COLUMNS])

    report = append_jibi_sheet(
        config=GoogleSheetAppendConfig(
            spreadsheet_id="spreadsheet",
            source_preview_csv=preview,
            dry_run=True,
        ),
        client=client,
        report_path=report_path,
    )

    assert client.header_updates == []
    assert client.values[0] == OLD_SHEET_COLUMNS
    assert client.appended == []
    assert report.header_created is True
    assert report.header_status == "legacy_25_upgrade_planned"
    assert report.header_reason == "legacy_25_known_schema"
    assert report.header_safe_to_update is True
    assert report.header_update_planned is True
    assert report.rows_appended == 1
    report_text = report_path.read_text(encoding="utf-8")
    assert "Header status: `legacy_25_upgrade_planned`" in report_text
    assert "Header safe to update: True" in report_text
    assert "Header reason: `legacy_25_known_schema`" in report_text
    assert "Header update planned: True" in report_text
    assert "Header updated: False" in report_text


def test_dry_run_unsafe_swapped_header_reports_error_without_writes(tmp_path) -> None:
    preview = tmp_path / "2026-05-18_sheet_append_preview.csv"
    report_path = tmp_path / "report.md"
    _write_preview(preview, [_row("신규 후보", "fresh", "https://example.com/fresh")])
    swapped_header = list(OLD_SHEET_COLUMNS)
    reviewer_index = swapped_header.index("reviewer")
    review_result_index = swapped_header.index("review_result")
    swapped_header[reviewer_index], swapped_header[review_result_index] = (
        swapped_header[review_result_index],
        swapped_header[reviewer_index],
    )
    client = FakeGoogleSheetsClient(sheet_id=99, values=[swapped_header])

    report = append_jibi_sheet(
        config=GoogleSheetAppendConfig(
            spreadsheet_id="spreadsheet",
            source_preview_csv=preview,
            dry_run=True,
        ),
        client=client,
        report_path=report_path,
    )

    assert client.header_updates == []
    assert client.appended == []
    assert report.header_status == "unsafe_mismatch"
    assert report.header_reason == "unknown_header_shape"
    assert report.header_safe_to_update is False
    assert report.rows_appended == 0
    assert len(report.errors) == 1
    report_text = report_path.read_text(encoding="utf-8")
    assert "Header status: `unsafe_mismatch`" in report_text
    assert "Header safe to update: False" in report_text
    assert "Header reason: `unknown_header_shape`" in report_text


def test_real_append_blocks_unsafe_missing_core_column(tmp_path) -> None:
    preview = tmp_path / "2026-05-18_sheet_append_preview.csv"
    _write_preview(preview, [_row("신규 후보", "fresh", "https://example.com/fresh")])
    unsafe_header = [
        "dedupe_key" if column == "duplicate_key" else column for column in OLD_SHEET_COLUMNS
    ]
    client = FakeGoogleSheetsClient(sheet_id=99, values=[unsafe_header])

    report = append_jibi_sheet(
        config=GoogleSheetAppendConfig(
            spreadsheet_id="spreadsheet",
            source_preview_csv=preview,
            dry_run=False,
        ),
        client=client,
    )

    assert client.header_updates == []
    assert client.appended == []
    assert report.header_status == "unsafe_mismatch"
    assert report.header_safe_to_update is False
    assert report.rows_appended == 0
    assert len(report.errors) == 1


def test_slideability_columns_survive_append(tmp_path) -> None:
    preview = tmp_path / "2026-05-18_sheet_append_preview.csv"
    _write_preview(
        preview,
        [
            {
                **_row("슬라이드 좋은 후보", "visual", "https://example.com/visual"),
                "slideability_score": "4",
                "slideability": "high / chart+map",
                "first_slide_idea": "지도 위에 비용 역전 한 장",
                "likely_proof_object_types": "chart | map",
                "visual_risks": "source image rights | overclaim",
            }
        ],
    )
    client = FakeGoogleSheetsClient(sheet_id=99, values=[SHEET_COLUMNS])

    report = append_jibi_sheet(
        config=GoogleSheetAppendConfig(
            spreadsheet_id="spreadsheet",
            source_preview_csv=preview,
            dry_run=False,
        ),
        client=client,
    )

    appended = client.appended[0]
    assert SHEET_COLUMNS.index("slideability_score") == 25
    assert appended[SHEET_COLUMNS.index("slideability_score")] == "4"
    assert appended[SHEET_COLUMNS.index("slideability")] == "high / chart+map"
    first_slide_index = SHEET_COLUMNS.index("first_slide_idea")
    assert appended[first_slide_index] == "지도 위에 비용 역전 한 장"
    assert appended[SHEET_COLUMNS.index("likely_proof_object_types")] == "chart | map"
    assert appended[SHEET_COLUMNS.index("visual_risks")] == "source image rights | overclaim"
    assert report.rows_appended == 1


def test_append_skips_duplicate_key_and_source_url(tmp_path) -> None:
    preview = tmp_path / "2026-05-18_sheet_append_preview.csv"
    _write_preview(
        preview,
        [
            _row("드론 비용 역전", "dupe-key", "https://example.com/new"),
            _row("폭염 반바지", "new-key", "https://example.com/dupe-url"),
            _row("F88", "fresh-key", "https://example.com/fresh"),
        ],
    )
    existing = [
        SHEET_COLUMNS,
        _sheet_values(_row("기존", "dupe-key", "https://example.com/old")),
        _sheet_values(_row("기존 URL", "old-key", "https://example.com/dupe-url")),
    ]
    client = FakeGoogleSheetsClient(sheet_id=99, values=[list(row) for row in existing])

    report = append_jibi_sheet(
        config=GoogleSheetAppendConfig(
            spreadsheet_id="spreadsheet",
            source_preview_csv=preview,
            dry_run=False,
        ),
        client=client,
    )

    assert len(client.appended) == 1
    assert report.rows_appended == 1
    assert report.duplicates_skipped == 2


def test_legacy_header_upgrade_still_skips_duplicates(tmp_path) -> None:
    preview = tmp_path / "2026-05-18_sheet_append_preview.csv"
    _write_preview(
        preview,
        [
            _row("기존 후보", "dupe-key", "https://example.com/new"),
            _row("기존 URL 후보", "fresh-key", "https://example.com/dupe-url"),
            _row("새 후보", "fresh-key-2", "https://example.com/fresh"),
        ],
    )
    existing = [
        OLD_SHEET_COLUMNS,
        _sheet_values(_row("기존", "dupe-key", "https://example.com/old"), OLD_SHEET_COLUMNS),
        _sheet_values(
            _row("기존 URL", "old-key", "https://example.com/dupe-url"),
            OLD_SHEET_COLUMNS,
        ),
    ]
    client = FakeGoogleSheetsClient(sheet_id=99, values=existing)

    report = append_jibi_sheet(
        config=GoogleSheetAppendConfig(
            spreadsheet_id="spreadsheet",
            source_preview_csv=preview,
            dry_run=False,
        ),
        client=client,
    )

    assert client.header_updates == [("A1", [SHEET_COLUMNS])]
    assert len(client.appended) == 1
    assert report.header_status == "legacy_25_upgraded"
    assert report.rows_appended == 1
    assert report.duplicates_skipped == 2


def test_dry_run_reports_without_append(tmp_path) -> None:
    preview = tmp_path / "2026-05-18_sheet_append_preview.csv"
    report_path = tmp_path / "report.md"
    _write_preview(preview, [_row("드론 비용 역전", "drone", "https://example.com/drone")])
    client = FakeGoogleSheetsClient(sheet_id=99, values=[SHEET_COLUMNS])

    report = append_jibi_sheet(
        config=GoogleSheetAppendConfig(
            spreadsheet_id="spreadsheet",
            source_preview_csv=preview,
            dry_run=True,
        ),
        client=client,
        report_path=report_path,
    )

    assert client.appended == []
    assert report.rows_appended == 1
    assert report.dry_run is True
    assert "Dry run: True" in report_path.read_text(encoding="utf-8")


def test_dry_run_missing_sheet_reports_create_without_fetching_values(tmp_path) -> None:
    preview = tmp_path / "2026-05-18_sheet_append_preview.csv"
    _write_preview(preview, [_row("드론 비용 역전", "drone", "https://example.com/drone")])
    client = FakeGoogleSheetsClient(sheet_id=None)

    report = append_jibi_sheet(
        config=GoogleSheetAppendConfig(
            spreadsheet_id="spreadsheet",
            source_preview_csv=preview,
            dry_run=True,
        ),
        client=client,
    )

    assert client.created is False
    assert client.appended == []
    assert report.sheet_created is True
    assert report.header_created is True
    assert report.rows_appended == 1


def test_example_config_has_no_real_spreadsheet_id(monkeypatch) -> None:
    monkeypatch.delenv("LUDDITE_GOOGLE_SPREADSHEET_ID", raising=False)
    config = load_append_config(
        config_path=paths.GOOGLE_SHEETS_EXAMPLE_CONFIG_YAML,
        local_config_path=paths.REPO_ROOT / "missing-google-sheets-local.yaml",
    )

    assert config.spreadsheet_id is None


def test_env_vars_override_config_values(tmp_path, monkeypatch) -> None:
    example_config = tmp_path / "google_sheets.example.yaml"
    local_config = tmp_path / "google_sheets.local.yaml"
    example_config.write_text(
        "\n".join(
            [
                "spreadsheet_id: null",
                'target_sheet_name: "Jibi"',
                "dry_run_default: true",
                "auth_mode: service_account",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    local_config.write_text(
        "\n".join(
            [
                'spreadsheet_id: "local-id"',
                'target_sheet_name: "local sheet"',
                'service_account_json_path: "/local/secret.json"',
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("LUDDITE_GOOGLE_SPREADSHEET_ID", "env-id")
    monkeypatch.setenv("LUDDITE_GOOGLE_TARGET_SHEET", "env sheet")
    monkeypatch.setenv("LUDDITE_GOOGLE_SERVICE_ACCOUNT_JSON", "/env/secret.json")

    config = load_append_config(
        config_path=example_config,
        local_config_path=local_config,
    )

    assert config.spreadsheet_id == "env-id"
    assert config.target_sheet_name == "env sheet"
    assert config.service_account_json_path == "/env/secret.json"


def test_missing_spreadsheet_id_dry_run_reports_planned_rows(tmp_path) -> None:
    preview = tmp_path / "2026-05-18_sheet_append_preview.csv"
    report_path = tmp_path / "report.md"
    _write_preview(preview, [_row("드론 비용 역전", "drone", "https://example.com/drone")])

    report = append_jibi_sheet(
        config=GoogleSheetAppendConfig(
            spreadsheet_id=None,
            source_preview_csv=preview,
            dry_run=True,
        ),
        client=None,
        report_path=report_path,
    )

    assert report.errors == []
    assert report.rows_appended == 1
    assert "Rows appended: 1" in report_path.read_text(encoding="utf-8")


def test_missing_spreadsheet_id_real_append_reports_error(tmp_path) -> None:
    preview = tmp_path / "2026-05-18_sheet_append_preview.csv"
    report_path = tmp_path / "report.md"
    _write_preview(preview, [_row("드론 비용 역전", "drone", "https://example.com/drone")])

    report = append_jibi_sheet(
        config=GoogleSheetAppendConfig(
            spreadsheet_id=None,
            source_preview_csv=preview,
            dry_run=False,
        ),
        client=None,
        report_path=report_path,
    )

    assert report.rows_appended == 0
    assert report.errors == ["spreadsheet_id is required when dry_run is false."]
    assert "spreadsheet_id is required" in report_path.read_text(encoding="utf-8")


def test_report_does_not_expose_local_credential_path(tmp_path) -> None:
    preview = tmp_path / "2026-05-18_sheet_append_preview.csv"
    report_path = tmp_path / "report.md"
    secret_path = "/very/local/service-account-secret.json"
    _write_preview(preview, [_row("드론 비용 역전", "drone", "https://example.com/drone")])

    append_jibi_sheet(
        config=GoogleSheetAppendConfig(
            spreadsheet_id=None,
            source_preview_csv=preview,
            dry_run=True,
            service_account_json_path=secret_path,
        ),
        client=None,
        report_path=report_path,
    )

    assert secret_path not in report_path.read_text(encoding="utf-8")


def test_bundle_review_replace_dry_run_allows_existing_candidate_header(tmp_path) -> None:
    preview = tmp_path / "2026-05-23_bundle_review_sheet.csv"
    report_path = tmp_path / "report.md"
    _write_bundle_review_preview(
        preview,
        [
            {
                "날짜": "2026-05-23",
                "제목": "청년 노동시장 이탈",
                "메인 링크": "https://example.com/bok",
                "서브 링크": "https://example.com/bok2",
                "설명": "BOK 청년 노동시장 후보들이 같은 질문을 공유함",
                "리뷰-성원": "",
                "리뷰-동찬": "",
                "리뷰-형찬": "",
                "ID": "2026-05-23:story_bundle_youth",
            }
        ],
    )
    client = FakeGoogleSheetsClient(sheet_id=99, values=[SHEET_COLUMNS])

    report = append_jibi_sheet(
        config=GoogleSheetAppendConfig(
            spreadsheet_id="spreadsheet",
            source_preview_csv=preview,
            sheet_schema="bundle_review",
            dry_run=True,
            replace_existing=True,
        ),
        client=client,
        report_path=report_path,
    )

    assert client.cleared is False
    assert client.header_updates == []
    assert report.header_status == "unsafe_mismatch_replace_planned"
    assert report.header_safe_to_update is True
    assert report.sheet_replace_planned is True
    assert report.rows_appended == 1
    report_text = report_path.read_text(encoding="utf-8")
    assert "Sheet schema: `bundle_review`" in report_text
    assert "Sheet replace planned: True" in report_text


def test_bundle_review_replace_writes_header_and_rows(tmp_path) -> None:
    preview = tmp_path / "2026-05-23_bundle_review_sheet.csv"
    _write_bundle_review_preview(
        preview,
        [
            {
                "날짜": "2026-05-23",
                "제목": "청년 노동시장 이탈",
                "메인 링크": "https://example.com/bok",
                "서브 링크": "https://example.com/bok2",
                "설명": "BOK 청년 노동시장 후보들이 같은 질문을 공유함",
                "리뷰-성원": "좋음",
                "리뷰-동찬": "",
                "리뷰-형찬": "",
                "ID": "2026-05-23:story_bundle_youth",
            }
        ],
    )
    client = FakeGoogleSheetsClient(sheet_id=99, values=[SHEET_COLUMNS])

    report = append_jibi_sheet(
        config=GoogleSheetAppendConfig(
            spreadsheet_id="spreadsheet",
            source_preview_csv=preview,
            sheet_schema="bundle-review",
            dry_run=False,
            replace_existing=True,
        ),
        client=client,
    )

    assert client.cleared is True
    assert client.values[0] == BUNDLE_REVIEW_SHEET_COLUMNS
    assert client.values[1][BUNDLE_REVIEW_SHEET_COLUMNS.index("제목")] == "청년 노동시장 이탈"
    assert client.review_board_formats == [(99, 2, 9)]
    assert report.styling_applied is True
    assert client.appended == []
    assert report.sheet_replaced is True
    assert report.header_updated is True
    assert report.rows_appended == 1
