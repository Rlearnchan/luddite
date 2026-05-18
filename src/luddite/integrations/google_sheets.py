"""Google Sheets client abstractions for append-only jibi staging writes."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(frozen=True)
class AppendResult:
    start_row: int | None
    end_row: int | None


class GoogleSheetsClient(Protocol):
    """Small client surface used by the jibi appender.

    Tests should use a fake implementation of this protocol. The real API
    implementation is optional at import time so local test runs do not require
    Google credentials or Google client libraries.
    """

    def get_sheet_id(self, spreadsheet_id: str, sheet_name: str) -> int | None: ...

    def create_sheet(self, spreadsheet_id: str, sheet_name: str) -> int: ...

    def get_values(self, spreadsheet_id: str, sheet_name: str) -> list[list[str]]: ...

    def update_values(
        self,
        spreadsheet_id: str,
        sheet_name: str,
        start_cell: str,
        values: list[list[str]],
    ) -> None: ...

    def append_rows(
        self,
        spreadsheet_id: str,
        sheet_name: str,
        rows: list[list[str]],
    ) -> AppendResult: ...

    def format_rows(
        self,
        spreadsheet_id: str,
        sheet_id: int,
        start_row: int,
        end_row: int,
    ) -> None: ...


class GoogleSheetsApiClient:
    """Thin wrapper around Google Sheets API v4.

    The implementation supports service account credentials via
    `GOOGLE_APPLICATION_CREDENTIALS` or an explicit credentials path. OAuth can
    be added later behind the same protocol without changing jibi append logic.
    """

    def __init__(self, *, credentials_path: str | None = None, auth_mode: str = "service_account"):
        if auth_mode != "service_account":
            raise ValueError("Only service_account auth is implemented for Milestone 1.0.")
        try:
            from google.oauth2 import service_account
            from googleapiclient.discovery import build
        except ImportError as exc:  # pragma: no cover - depends on local optional deps
            raise RuntimeError(
                "Google Sheets API dependencies are not installed. Install "
                "`google-api-python-client` and `google-auth`, or run with --dry-run."
            ) from exc

        scopes = ["https://www.googleapis.com/auth/spreadsheets"]
        if credentials_path:
            credentials = service_account.Credentials.from_service_account_file(
                credentials_path,
                scopes=scopes,
            )
        else:
            credentials = service_account.Credentials.from_service_account_file(
                os.environ["GOOGLE_APPLICATION_CREDENTIALS"],
                scopes=scopes,
            )
        self.service = build("sheets", "v4", credentials=credentials)

    def get_sheet_id(self, spreadsheet_id: str, sheet_name: str) -> int | None:
        metadata = (
            self.service.spreadsheets()
            .get(spreadsheetId=spreadsheet_id, fields="sheets.properties")
            .execute()
        )
        for sheet in metadata.get("sheets", []):
            props = sheet.get("properties", {})
            if props.get("title") == sheet_name:
                return int(props["sheetId"])
        return None

    def create_sheet(self, spreadsheet_id: str, sheet_name: str) -> int:
        response = (
            self.service.spreadsheets()
            .batchUpdate(
                spreadsheetId=spreadsheet_id,
                body={"requests": [{"addSheet": {"properties": {"title": sheet_name}}}]},
            )
            .execute()
        )
        return int(response["replies"][0]["addSheet"]["properties"]["sheetId"])

    def get_values(self, spreadsheet_id: str, sheet_name: str) -> list[list[str]]:
        response = (
            self.service.spreadsheets()
            .values()
            .get(spreadsheetId=spreadsheet_id, range=f"'{sheet_name}'")
            .execute()
        )
        return response.get("values", [])

    def update_values(
        self,
        spreadsheet_id: str,
        sheet_name: str,
        start_cell: str,
        values: list[list[str]],
    ) -> None:
        (
            self.service.spreadsheets()
            .values()
            .update(
                spreadsheetId=spreadsheet_id,
                range=f"'{sheet_name}'!{start_cell}",
                valueInputOption="RAW",
                body={"values": values},
            )
            .execute()
        )

    def append_rows(
        self,
        spreadsheet_id: str,
        sheet_name: str,
        rows: list[list[str]],
    ) -> AppendResult:
        response = (
            self.service.spreadsheets()
            .values()
            .append(
                spreadsheetId=spreadsheet_id,
                range=f"'{sheet_name}'!A1",
                valueInputOption="RAW",
                insertDataOption="INSERT_ROWS",
                body={"values": rows},
            )
            .execute()
        )
        updated_range = response.get("updates", {}).get("updatedRange", "")
        return _parse_updated_range(updated_range)

    def format_rows(
        self,
        spreadsheet_id: str,
        sheet_id: int,
        start_row: int,
        end_row: int,
    ) -> None:
        requests: list[dict[str, Any]] = [
            {
                "repeatCell": {
                    "range": {
                        "sheetId": sheet_id,
                        "startRowIndex": start_row - 1,
                        "endRowIndex": end_row,
                    },
                    "cell": {
                        "userEnteredFormat": {
                            "backgroundColor": {"red": 0.91, "green": 0.96, "blue": 1.0}
                        }
                    },
                    "fields": "userEnteredFormat.backgroundColor",
                }
            }
        ]
        (
            self.service.spreadsheets()
            .batchUpdate(spreadsheetId=spreadsheet_id, body={"requests": requests})
            .execute()
        )


def _parse_updated_range(value: str) -> AppendResult:
    # Example: "'jibi 후보'!A2:Y9"
    if "!" not in value:
        return AppendResult(start_row=None, end_row=None)
    cell_range = value.split("!", 1)[1]
    rows: list[int] = []
    for cell in cell_range.replace(":", " ").split():
        digits = "".join(char for char in cell if char.isdigit())
        if digits:
            rows.append(int(digits))
    if not rows:
        return AppendResult(start_row=None, end_row=None)
    return AppendResult(start_row=min(rows), end_row=max(rows))
