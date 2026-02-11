from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pandas as pd
import pytest


@pytest.mark.parametrize(
    ("grain", "expected_key"),
    [
        ("day", "dod_revenue"),
        ("week", "wow_revenue"),
        ("month", "mom_revenue"),
    ],
)
def test_grain_controls_delta_key(tmp_path: Path, grain: str, expected_key: str) -> None:
    # Ensure we have 2 periods for the selected grain
    if grain == "month":
        dts = ["2026-01-01", "2026-01-02", "2026-02-01", "2026-02-02"]
    else:
        dts = ["2026-01-01", "2026-01-02", "2026-01-08", "2026-01-09"]

    df = pd.DataFrame(
        {
            "dt": dts,
            "revenue": [10, 20, 30, 40],
            "region": ["A", "A", "A", "A"],
        }
    )
    inp = tmp_path / "data.csv"
    df.to_csv(inp, index=False)

    out_dir = tmp_path / "out"
    time_range = "2026-01-01..2026-03-01" if grain == "month" else "2026-01-01..2026-02-01"

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
        "--grain",
        grain,
        "--time-range",
        time_range,
    ]
    p = subprocess.run(cmd, check=True, capture_output=True, text=True)
    payload = json.loads(p.stdout)

    # summary artifact exists
    assert payload["artifacts"]

    assert payload["meta"]["grain"] == grain
    kpis = payload["meta"]["kpis"]
    assert expected_key in kpis
