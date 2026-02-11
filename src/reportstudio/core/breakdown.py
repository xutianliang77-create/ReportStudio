from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True, slots=True)
class ChangeContribTable:
    """Contribution-to-change between two periods for one (dim, measure)."""

    df_pos: pd.DataFrame
    df_neg: pd.DataFrame
    period_prev: pd.Timestamp
    period_last: pd.Timestamp
    total_prev: float
    total_last: float
    total_delta: float


@dataclass(frozen=True, slots=True)
class BreakdownTable:
    # df columns: dim, value, share
    df: pd.DataFrame
    dim: str
    measure: str
    warnings: list[str]
    change: ChangeContribTable | None = None


def _to_period_start(series: pd.Series, grain: str) -> pd.Series:
    dt = pd.to_datetime(series, errors="coerce", format="mixed")
    if grain == "day":
        return dt.dt.floor("D")
    if grain == "week":
        return (dt.dt.to_period("W-MON").dt.start_time).dt.floor("D")
    if grain == "month":
        return (dt.dt.to_period("M").dt.start_time).dt.floor("D")
    raise ValueError(f"Unsupported grain: {grain}")


def _build_value_topn(
    df: pd.DataFrame,
    dim: str,
    measure: str,
    topn: int,
) -> pd.DataFrame:
    s = pd.to_numeric(df[measure], errors="coerce")
    grouped = df.assign(__m__=s).groupby(dim, dropna=False)["__m__"].sum(min_count=1)
    grouped = grouped.sort_values(ascending=False)

    total = float(grouped.sum()) if pd.notna(grouped.sum()) else 0.0

    out = grouped.head(topn).reset_index().rename(columns={"__m__": "value"})
    out["share"] = out["value"].apply(lambda v: float(v) / total if total else 0.0)

    if len(grouped) > topn:
        others = grouped.iloc[topn:]
        other_val = float(others.sum())
        other_row = pd.DataFrame([{dim: "(others)", "value": other_val}])
        other_row["share"] = other_val / total if total else 0.0
        out = pd.concat([out, other_row], ignore_index=True)

    return out


def _build_change_contrib(
    df: pd.DataFrame,
    date_col: str,
    dim: str,
    measure: str,
    topn: int,
    grain: str,
) -> tuple[ChangeContribTable | None, list[str]]:
    warnings: list[str] = []

    if date_col not in df.columns:
        warnings.append("date column not found; contribution-to-change skipped")
        return None, warnings

    period = _to_period_start(df[date_col], grain)
    if period.notna().sum() < 2:
        warnings.append("Too few valid dates for contribution-to-change.")
        return None, warnings

    work = df.copy()
    work["__period__"] = period
    work["__m__"] = pd.to_numeric(work[measure], errors="coerce")

    by_period = (
        work.dropna(subset=["__period__"])
        .groupby("__period__", dropna=True)["__m__"]
        .sum(min_count=1)
        .sort_index()
    )
    if len(by_period) < 2:
        warnings.append("Not enough history (need >=2 periods) for contribution-to-change.")
        return None, warnings

    period_last = pd.Timestamp(by_period.index[-1])
    period_prev = pd.Timestamp(by_period.index[-2])

    # dim x period pivot
    pivot = (
        work.dropna(subset=["__period__"])
        .groupby([dim, "__period__"], dropna=False)["__m__"]
        .sum(min_count=1)
        .unstack("__period__")
    )

    cur = pivot.get(period_last)
    prev = pivot.get(period_prev)
    if cur is None or prev is None:
        warnings.append(
            "Insufficient data for last/previous period; contribution-to-change skipped"
        )
        return None, warnings

    cur_f = cur.fillna(0.0).astype(float)
    prev_f = prev.fillna(0.0).astype(float)
    delta = cur_f - prev_f

    total_last = float(cur_f.sum())
    total_prev = float(prev_f.sum())
    total_delta = float(total_last - total_prev)

    denom_signed = total_delta
    denom_abs = float(delta.abs().sum())
    if denom_signed == 0.0:
        warnings.append("Total change is 0; signed share_of_change is undefined.")

    base = pd.DataFrame(
        {
            dim: delta.index,
            "value_last": cur_f.values,
            "value_prev": prev_f.values,
            "delta": delta.values,
        }
    )
    base["share_of_change"] = base["delta"].apply(
        lambda d: float(d) / denom_signed if denom_signed != 0.0 else None
    )
    base["share_of_abs_change"] = base["delta"].apply(
        lambda d: float(abs(d)) / denom_abs if denom_abs != 0.0 else 0.0
    )

    pos = base[base["delta"] > 0].sort_values("delta", ascending=False).head(topn)
    neg = base[base["delta"] < 0].sort_values("delta", ascending=True).head(topn)

    return (
        ChangeContribTable(
            df_pos=pos.reset_index(drop=True),
            df_neg=neg.reset_index(drop=True),
            period_prev=period_prev,
            period_last=period_last,
            total_prev=total_prev,
            total_last=total_last,
            total_delta=total_delta,
        ),
        warnings,
    )


def build_topn_breakdown(
    df: pd.DataFrame,
    dim: str,
    measure: str,
    topn: int,
    *,
    date_col: str | None = None,
    grain: str = "month",
) -> BreakdownTable:
    """Build TopN breakdown + (optionally) contribution-to-change.

    TopN is computed over the whole (already time-filtered) dataframe.
    Contribution-to-change is computed between the last two periods of `grain`.
    """

    warnings: list[str] = []
    if dim not in df.columns:
        return BreakdownTable(
            df=pd.DataFrame(),
            dim=dim,
            measure=measure,
            warnings=["dim not found"],
        )
    if measure not in df.columns:
        return BreakdownTable(
            df=pd.DataFrame(),
            dim=dim,
            measure=measure,
            warnings=["measure not found"],
        )

    top_df = _build_value_topn(df, dim=dim, measure=measure, topn=topn)

    change: ChangeContribTable | None = None
    if date_col is not None:
        change, w = _build_change_contrib(
            df,
            date_col=date_col,
            dim=dim,
            measure=measure,
            topn=topn,
            grain=grain,
        )
        warnings.extend(w)
    else:
        warnings.append("No date column; contribution-to-change skipped")

    return BreakdownTable(df=top_df, dim=dim, measure=measure, warnings=warnings, change=change)
