from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pandas as pd


def test_cli_smoke_generates_three_artifacts(tmp_path: Path) -> None:
    df = pd.DataFrame(
        {
            "dt": ["2026-01-01", "2026-01-02"],
            "revenue": [10, 20],
            "region": ["A", "B"],
        }
    )
    inp = tmp_path / "data.csv"
    df.to_csv(inp, index=False)

    out_dir = tmp_path / "out"
    cmd = [
        sys.executable,
        "-m",
        "reportstudio.cli.main",
        "--file",
        str(inp),
        "--prompt",
        "生成月报",
        "--out-dir",
        str(out_dir),
    ]
    p = subprocess.run(cmd, check=True, capture_output=True, text=True)
    payload = json.loads(p.stdout)

    artifacts = payload["artifacts"]
    formats = {a["format"] for a in artifacts}
    assert formats == {"xlsx", "pdf", "pptx"}

    for a in artifacts:
        assert Path(a["path"]).exists()

    # tables should exist for month grain trend and one breakdown
    assert "tables" in payload
    assert isinstance(payload["tables"].get("trend"), list)
    assert isinstance(payload["tables"].get("breakdowns"), list)
    assert payload["tables"]["breakdowns"]


def test_cli_allows_dim_and_measure_override(tmp_path: Path) -> None:
    df = pd.DataFrame(
        {
            "dt": ["2026-01-01", "2026-02-01"],
            "region": ["A", "A"],
            "channel": ["X", "Y"],
            "revenue": [10, 20],
            "cost": [3, 4],
        }
    )
    inp = tmp_path / "data.csv"
    df.to_csv(inp, index=False)

    out_dir = tmp_path / "out"
    cmd = [
        sys.executable,
        "-m",
        "reportstudio.cli.main",
        "--file",
        str(inp),
        "--prompt",
        "生成月报",
        "--out-dir",
        str(out_dir),
        "--dim",
        "channel",
        "--measure",
        "cost",
        "--time-range",
        "2026-01-01..2026-03-01",
    ]
    p = subprocess.run(cmd, check=True, capture_output=True, text=True)
    payload = json.loads(p.stdout)

    bds = payload["tables"]["breakdowns"]
    assert bds
    assert bds[0]["dim"] == "channel"
    assert bds[0]["measure"] == "cost"
