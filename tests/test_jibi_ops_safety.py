import pytest

from luddite.agents.jibi.ops_safety import (
    DEFAULT_APPEND_MODE,
    JIBI_STAGING_SHEET,
    STAGING_APPEND_MODE,
    validate_ops_safety,
)


def test_default_append_mode_is_dry_run() -> None:
    config = validate_ops_safety()

    assert config.append_mode == DEFAULT_APPEND_MODE
    assert config.dry_run is True
    assert config.target_sheet_name == JIBI_STAGING_SHEET


def test_invalid_append_mode_errors() -> None:
    with pytest.raises(ValueError, match="JIBI_APPEND_MODE"):
        validate_ops_safety(append_mode="append_now")


def test_staging_append_requires_exact_staging_sheet() -> None:
    with pytest.raises(ValueError, match="jibi 후보"):
        validate_ops_safety(
            append_mode=STAGING_APPEND_MODE,
            target_sheet_name="jibi 후보 복사본",
        )


def test_ops_guard_never_targets_topic_finding_sheet() -> None:
    with pytest.raises(ValueError, match="주제 찾기"):
        validate_ops_safety(
            append_mode=DEFAULT_APPEND_MODE,
            target_sheet_name="주제 찾기",
        )
