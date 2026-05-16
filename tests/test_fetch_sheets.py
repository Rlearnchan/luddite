from luddite.parsers.fetch_sheets import fetch_sheets
from luddite.utils.jsonl import read_jsonl


def test_fetch_sheets_redacts_sensitive_values(tmp_path) -> None:
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    source = raw_dir / "research.csv"
    source.write_text(
        "제목,메모\n"
        "좋은 후보,아이디: testuser 비번: secret phone 010-1234-5678\n",
        encoding="utf-8",
    )

    output = tmp_path / "parsed.jsonl"
    redacted_dir = tmp_path / "parsed"
    records = fetch_sheets(raw_dir, output, redacted_dir)

    assert len(records) == 1
    assert records[0]["credential_risk"] is True
    payload = read_jsonl(output)[0]
    memo = payload["row"]["메모"]
    assert "secret" not in memo
    assert "010-1234-5678" not in memo
    assert "[REDACTED]" in memo
    assert "[REDACTED_PHONE]" in memo
