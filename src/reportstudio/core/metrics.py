from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True, slots=True)
class KpiResult:
    kpis: dict[str, float]


def compute_kpis(df: pd.DataFrame, number_cols: list[str]) -> KpiResult:
    kpis: dict[str, float] = {}
    for c in number_cols:
        s = df[c]
        # keep stable numeric types
        total = float(pd.to_numeric(s, errors="coerce").sum())
        kpis[f"sum_{c}"] = total
        kpis[f"avg_{c}"] = float(pd.to_numeric(s, errors="coerce").mean()) if len(s) else 0.0

    kpis["row_count"] = float(len(df))
    return KpiResult(kpis=kpis)
