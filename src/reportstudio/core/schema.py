from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True, slots=True)
class SchemaGuess:
    date_column: str | None
    number_columns: list[str]
    dimension_columns: list[str]
    warnings: list[str]


def guess_schema(df: pd.DataFrame) -> SchemaGuess:
    warnings: list[str] = []

    # Normalize column names
    df_cols = [str(c) for c in df.columns]

    # Heuristic: find date-like column
    date_col: str | None = None
    for c in df_cols:
        s = df[c]
        if pd.api.types.is_datetime64_any_dtype(s):
            date_col = c
            break

    def _date_looks_reasonable(dt: pd.Series) -> bool:
        nn = dt.dropna()
        if nn.empty:
            return False
        years = nn.dt.year
        # Avoid false-positives from numeric IDs coerced into Unix epoch-ish dates.
        if years.min() < 1990:
            return False
        return not years.max() > 2100

    if date_col is None:
        for c in df_cols:
            s = df[c]
            if s.dtype == object or pd.api.types.is_string_dtype(s):
                converted = pd.to_datetime(s, errors="coerce", format="mixed")
                enough = int(converted.notna().sum()) >= max(3, int(0.8 * len(s.dropna())))
                if enough and _date_looks_reasonable(converted):
                    date_col = c
                    df[c] = converted
                    warnings.append(f"Auto-detected date column: {c}")
                    break

    # Numeric columns
    number_cols: list[str] = []
    for c in df_cols:
        if c == date_col:
            continue
        s = df[c]
        if pd.api.types.is_numeric_dtype(s):
            number_cols.append(c)
            continue
        converted = pd.to_numeric(s, errors="coerce")
        if int(converted.notna().sum()) >= max(3, int(0.9 * len(s.dropna()))):
            df[c] = converted
            number_cols.append(c)

    # Dimension columns: string-ish non-date non-number
    dim_cols: list[str] = []
    for c in df_cols:
        if c == date_col or c in number_cols:
            continue
        dim_cols.append(c)

    if not number_cols:
        warnings.append("No numeric columns detected; KPI section may be empty.")

    if date_col is None:
        warnings.append("No date column detected; trend/WoW/MoM/YoY will be skipped.")

    return SchemaGuess(
        date_column=date_col,
        number_columns=number_cols,
        dimension_columns=dim_cols,
        warnings=warnings,
    )
