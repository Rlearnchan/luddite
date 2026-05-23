import os
import subprocess
import sys
from pathlib import Path

from luddite import paths


def test_manual_runner_does_not_remove_unowned_lock(tmp_path: Path) -> None:
    lock_dir = tmp_path / "manual-update.lock"
    lock_dir.mkdir()
    run_date = "2099-01-01"
    env = {
        **os.environ,
        "JIBI_DATE": run_date,
        "JIBI_LOCK_DIR": str(lock_dir),
        "JIBI_LOG_DIR": str(tmp_path / "logs"),
        "LUDDITE_GOOGLE_TARGET_SHEET": "Jibi",
        "PYTHONPATH": "src",
        "VENV_PYTHON": sys.executable,
        "JIBI_DISABLE_LOG_TEE": "1",
    }

    result = subprocess.run(
        ["bash", "scripts/run_jibi_manual_update.sh"],
        cwd=paths.REPO_ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    try:
        assert result.returncode == 42
        assert lock_dir.is_dir()
        assert "Another Jibi manual update is already running" in result.stderr
    finally:
        for suffix in [".md", ".json"]:
            (
                paths.REPORTS_DIR / f"jibi_manual_update_{run_date}{suffix}"
            ).unlink(missing_ok=True)
