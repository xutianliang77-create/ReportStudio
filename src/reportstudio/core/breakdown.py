from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True, slots=True)
class BreakdownTable:
    # columns: dim, value, share, contribution
    df: pd.DataFrame
    dim: str
    measure: str
    warnings: list[str]


def build_topn_breakdown(
    df: pd.DataFrame,
    dim: str,
    measure: str,
    topn: int,
) -> BreakdownTable:
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
            df=pd.DataFrame(), dim=dim, measure=measure, warnings=["measure not found"]
        )

    s = pd.to_numeric(df[measure], errors="coerce")
    grouped = df.assign(__m__=s).groupby(dim, dropna=False)["__m__"].sum(min_count=1)
    grouped = grouped.sort_values(ascending=False)

    total = float(grouped.sum()) if pd.notna(grouped.sum()) else 0.0

    out = grouped.head(topn).reset_index().rename(columns={"__m__": "value"})
    out["share"] = out["value"].apply(lambda v: float(v) / total if total else 0.0)
    out["contribution"] = out["value"]  # for now equals value; extended later for deltas

    if len(grouped) > topn:
        others = grouped.iloc[topn:]
        other_val = float(others.sum())
        other_row = pd.DataFrame([{dim: "(others)", "value": other_val}])
        other_row["share"] = other_val / total if total else 0.0
        other_row["contribution"] = other_val
        out = pd.concat([out, other_row], ignore_index=True)

    return BreakdownTable(df=out, dim=dim, measure=measure, warnings=warnings)
