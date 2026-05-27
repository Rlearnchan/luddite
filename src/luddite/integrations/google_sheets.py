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

    def clear_values(self, spreadsheet_id: str, sheet_name: str) -> None: ...

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

    def format_review_board(
        self,
        spreadsheet_id: str,
        sheet_id: int,
        *,
        row_count: int,
        column_count: int,
        header_row: int = 1,
        intro_row_count: int = 0,
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

    def clear_values(self, spreadsheet_id: str, sheet_name: str) -> None:
        (
            self.service.spreadsheets()
            .values()
            .clear(
                spreadsheetId=spreadsheet_id,
                range=f"'{sheet_name}'",
                body={},
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

    def format_review_board(
        self,
        spreadsheet_id: str,
        sheet_id: int,
        *,
        row_count: int,
        column_count: int,
        header_row: int = 1,
        intro_row_count: int = 0,
    ) -> None:
        column_widths = [90, 280, 95, 190, 220, 520, 360, 170, 170, 170, 230]
        header_row_index = max(header_row - 1, 0)
        data_start_row_index = min(header_row_index + 1, max(row_count, 1))
        description_column_index = 5 if column_count > 5 else 4
        wrap_end_column_index = min(description_column_index + 2, column_count)
        requests: list[dict[str, Any]] = [
            {
                "repeatCell": {
                    "range": {
                        "sheetId": sheet_id,
                        "startRowIndex": 0,
                        "endRowIndex": max(row_count, 1),
                        "startColumnIndex": 0,
                        "endColumnIndex": column_count,
                    },
                    "cell": {
                        "userEnteredFormat": {
                            "wrapStrategy": "CLIP",
                            "verticalAlignment": "TOP",
                        }
                    },
                    "fields": (
                        "userEnteredFormat.wrapStrategy,"
                        "userEnteredFormat.verticalAlignment"
                    ),
                }
            },
            {
                "repeatCell": {
                    "range": {
                        "sheetId": sheet_id,
                        "startRowIndex": data_start_row_index,
                        "endRowIndex": max(row_count, 1),
                        "startColumnIndex": description_column_index,
                        "endColumnIndex": wrap_end_column_index,
                    },
                    "cell": {
                        "userEnteredFormat": {
                            "wrapStrategy": "WRAP",
                        }
                    },
                    "fields": "userEnteredFormat.wrapStrategy",
                }
            },
            {
                "repeatCell": {
                    "range": {
                        "sheetId": sheet_id,
                        "startRowIndex": header_row_index,
                        "endRowIndex": header_row_index + 1,
                        "startColumnIndex": 0,
                        "endColumnIndex": column_count,
                    },
                    "cell": {
                        "userEnteredFormat": {
                            "backgroundColor": {
                                "red": 0.93,
                                "green": 0.96,
                                "blue": 1.0,
                            },
                            "textFormat": {"bold": True},
                        }
                    },
                    "fields": (
                        "userEnteredFormat.backgroundColor,"
                        "userEnteredFormat.textFormat.bold"
                    ),
                }
            },
            {
                "updateSheetProperties": {
                    "properties": {
                        "sheetId": sheet_id,
                        "gridProperties": {"frozenRowCount": 0 if intro_row_count else 1},
                    },
                    "fields": "gridProperties.frozenRowCount",
                }
            },
        ]
        if intro_row_count:
            requests.extend(
                [
                    {
                        "unmergeCells": {
                            "range": {
                                "sheetId": sheet_id,
                                "startRowIndex": 0,
                                "endRowIndex": intro_row_count,
                                "startColumnIndex": 0,
                                "endColumnIndex": column_count,
                            }
                        }
                    },
                    {
                        "repeatCell": {
                            "range": {
                                "sheetId": sheet_id,
                                "startRowIndex": 0,
                                "endRowIndex": intro_row_count,
                                "startColumnIndex": 0,
                                "endColumnIndex": column_count,
                            },
                            "cell": {
                                "userEnteredFormat": {
                                    "wrapStrategy": "WRAP",
                                    "verticalAlignment": "TOP",
                                    "backgroundColor": {
                                        "red": 0.98,
                                        "green": 0.99,
                                        "blue": 1.0,
                                    },
                                }
                            },
                            "fields": (
                                "userEnteredFormat.wrapStrategy,"
                                "userEnteredFormat.verticalAlignment,"
                                "userEnteredFormat.backgroundColor"
                            ),
                        }
                    },
                    {
                        "repeatCell": {
                            "range": {
                                "sheetId": sheet_id,
                                "startRowIndex": 0,
                                "endRowIndex": 1,
                                "startColumnIndex": 0,
                                "endColumnIndex": column_count,
                            },
                            "cell": {
                                "userEnteredFormat": {
                                    "textFormat": {"bold": True, "fontSize": 12}
                                }
                            },
                            "fields": (
                                "userEnteredFormat.textFormat.bold,"
                                "userEnteredFormat.textFormat.fontSize"
                            ),
                        }
                    },
                ]
            )
            for row_index in range(intro_row_count):
                requests.append(
                    {
                        "mergeCells": {
                            "range": {
                                "sheetId": sheet_id,
                                "startRowIndex": row_index,
                                "endRowIndex": row_index + 1,
                                "startColumnIndex": 0,
                                "endColumnIndex": column_count,
                            },
                            "mergeType": "MERGE_ALL",
                        }
                    }
                )
        for index, width in enumerate(column_widths[:column_count]):
            requests.append(
                {
                    "updateDimensionProperties": {
                        "range": {
                            "sheetId": sheet_id,
                            "dimension": "COLUMNS",
                            "startIndex": index,
                            "endIndex": index + 1,
                        },
                        "properties": {"pixelSize": width},
                        "fields": "pixelSize",
                    }
                }
            )
        (
            self.service.spreadsheets()
            .batchUpdate(spreadsheetId=spreadsheet_id, body={"requests": requests})
            .execute()
        )


def _parse_updated_range(value: str) -> AppendResult:
    # Example: "'jibi 후보'!A2:AD9"
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
