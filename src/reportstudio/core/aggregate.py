from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True, slots=True)
class TrendTable:
    # index is period start
    df: pd.DataFrame
    grain: str  # day|week|month
    warnings: list[str]


def _to_period_start(series: pd.Series, grain: str) -> pd.Series:
    dt = pd.to_datetime(series, errors="coerce", format="mixed")
    if grain == "day":
        return dt.dt.floor("D")
    if grain == "week":
        # Monday-start week
        return (dt.dt.to_period("W-MON").dt.start_time).dt.floor("D")
    if grain == "month":
        return (dt.dt.to_period("M").dt.start_time).dt.floor("D")
    raise ValueError(f"Unsupported grain: {grain}")


def build_trend(
    df: pd.DataFrame,
    date_col: str,
    number_cols: list[str],
    grain: str,
) -> TrendTable:
    warnings: list[str] = []

    if not number_cols:
        warnings.append("No numeric columns for trend.")
        return TrendTable(df=pd.DataFrame(), grain=grain, warnings=warnings)

    period = _to_period_start(df[date_col], grain)
    if period.notna().sum() < 3:
        warnings.append("Too few valid dates for trend.")
        return TrendTable(df=pd.DataFrame(), grain=grain, warnings=warnings)

    work = df.copy()
    work["__period__"] = period

    grouped = work.groupby("__period__", dropna=True)
    agg = grouped[number_cols].sum(min_count=1).sort_index()

    return TrendTable(df=agg, grain=grain, warnings=warnings)


def pct_change(current: float, previous: float) -> float | None:
    if previous == 0:
        return None
    return (current - previous) / previous


def compute_period_deltas(trend: TrendTable) -> tuple[dict[str, float], list[str]]:
    """Compute MoM/WoW/YoY for each numeric column based on the last 2 points.

    Returns flat dict like {"momo_sum_revenue": 0.12} and warnings.
    """

    warnings: list[str] = []
    if trend.df.empty:
        return {}, warnings

    if len(trend.df) < 2:
        warnings.append("Not enough history for period-over-period deltas.")
        return {}, warnings

    last = trend.df.iloc[-1]
    prev = trend.df.iloc[-2]

    out: dict[str, float] = {}
    label = {"day": "DoD", "week": "WoW", "month": "MoM"}.get(trend.grain, trend.grain)

    for c in trend.df.columns:
        cur = float(last[c]) if pd.notna(last[c]) else 0.0
        pre = float(prev[c]) if pd.notna(prev[c]) else 0.0
        ch = pct_change(cur, pre)
        if ch is None:
            warnings.append(f"{label} skipped for {c}: previous is 0")
            continue
        out[f"{label.lower()}_{c}"] = float(ch)

    # YoY only makes sense on month grain and at least 13 points (or same month last year)
    if trend.grain == "month":
        # find same month last year
        last_idx = trend.df.index[-1]
        target = (pd.Timestamp(last_idx) - pd.DateOffset(years=1)).to_period("M").start_time
        if target not in trend.df.index:
            warnings.append("YoY skipped: not enough history for same month last year.")
            return out, warnings

        yoy_prev = trend.df.loc[target]
        for c in trend.df.columns:
            cur = float(last[c]) if pd.notna(last[c]) else 0.0
            pre = float(yoy_prev[c]) if pd.notna(yoy_prev[c]) else 0.0
            ch = pct_change(cur, pre)
            if ch is None:
                warnings.append(f"YoY skipped for {c}: previous is 0")
                continue
            out[f"yoy_{c}"] = float(ch)

    return out, warnings
