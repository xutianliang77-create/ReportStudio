from __future__ import annotations

import pandas as pd

from reportstudio.core.breakdown import build_topn_breakdown


def test_breakdown_includes_contribution_to_change_when_two_periods_exist() -> None:
    df = pd.DataFrame(
        {
            "dt": [
                "2026-01-01",
                "2026-01-02",
                "2026-02-01",
                "2026-02-02",
            ],
            "region": ["A", "B", "A", "B"],
            "revenue": [100, 50, 130, 20],
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

    assert not bd.df.empty
    assert bd.change is not None

    # Last period is Feb 2026, previous is Jan 2026
    assert str(bd.change.period_last.date()) == "2026-02-01"
    assert str(bd.change.period_prev.date()) == "2026-01-01"

    # Deltas per region: A +30, B -30
    pos = bd.change.df_pos
    neg = bd.change.df_neg

    assert len(pos) == 1
    assert pos.loc[0, "region"] == "A"
    assert float(pos.loc[0, "delta"]) == 30.0  # type: ignore[arg-type]

    assert len(neg) == 1
    assert neg.loc[0, "region"] == "B"
    assert float(neg.loc[0, "delta"]) == -30.0  # type: ignore[arg-type]


def test_breakdown_change_skips_with_insufficient_history() -> None:
    df = pd.DataFrame(
        {
            "dt": ["2026-01-01", "2026-01-02"],
            "region": ["A", "B"],
            "revenue": [10, 20],
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

    assert bd.change is None
    assert any("Not enough history" in w or "Too few" in w for w in bd.warnings)
