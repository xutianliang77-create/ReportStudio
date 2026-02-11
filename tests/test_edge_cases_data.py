from __future__ import annotations

from pathlib import Path

import pandas as pd

from reportstudio.core.aggregate import TrendTable, compute_period_deltas
from reportstudio.core.breakdown import build_topn_breakdown
from reportstudio.core.pipeline import run_pipeline
from reportstudio.core.types import RunRequest


def test_compute_period_deltas_warns_when_previous_is_zero() -> None:
    trend = TrendTable(
        df=pd.DataFrame(
            {"revenue": [0.0, 10.0]},
            index=pd.to_datetime(["2026-01-01", "2026-01-02"]),
        ),
        grain="day",
        warnings=[],
    )
    deltas, w = compute_period_deltas(trend)
    assert deltas == {}
    assert any("previous is 0" in x for x in w)


def test_breakdown_warns_when_total_change_is_zero() -> None:
    # Two months, totals are equal => total_delta=0
    df = pd.DataFrame(
        {
            "dt": ["2026-01-01", "2026-01-02", "2026-02-01", "2026-02-02"],
            "region": ["A", "B", "A", "B"],
            "revenue": [10, 20, 10, 20],
        }
    )

    bd = build_topn_breakdown(
        df,
        dim="region",
        measure="revenue",
        topn=10,
        date_col="dt",
        grain="month",
    )

    assert bd.change is not None
    assert float(bd.change.total_delta) == 0.0
    assert any("Total change is 0" in w for w in bd.warnings)


def test_pipeline_warns_when_missing_date_and_numeric(tmp_path: Path) -> None:
    # Missing date, missing numeric => schema warnings should surface.
    df = pd.DataFrame({"region": ["A", "B", "C"], "channel": ["x", "y", "z"]})
    inp = tmp_path / "nodate_nonum.csv"
    df.to_csv(inp, index=False)

    res = run_pipeline(
        RunRequest(
            file=str(inp),
            prompt="edge",
            out_dir=str(tmp_path / "out"),
            grain="month",
            topn=5,
            formats=["xlsx"],
            time_range=None,
            dim=None,
            measure=None,
        )
    )

    assert any("No numeric columns detected" in w for w in res.warnings)
    assert any("No date column detected" in w for w in res.warnings)
