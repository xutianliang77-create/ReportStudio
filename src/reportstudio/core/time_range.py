from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta

import pandas as pd


@dataclass(frozen=True, slots=True)
class TimeRange:
    start: date
    end: date  # exclusive

    def to_spec(self) -> str:
        return f"{self.start.isoformat()}..{self.end.isoformat()}"


def parse_time_range(raw: str) -> TimeRange:
    left, right = raw.split("..", 1)
    start = datetime.strptime(left.strip(), "%Y-%m-%d").date()
    end = datetime.strptime(right.strip(), "%Y-%m-%d").date()
    return TimeRange(start=start, end=end)


def default_time_range(
    df: pd.DataFrame,
    date_col: str | None,
) -> tuple[TimeRange | None, list[str]]:
    warnings: list[str] = []
    if date_col is None:
        return None, warnings

    series = pd.to_datetime(df[date_col], errors="coerce", format="mixed")
    if series.notna().sum() < 3:
        warnings.append("Date column has too few valid values; defaulting to no time filtering.")
        return None, warnings

    max_dt = series.max()
    if max_dt is None or pd.isna(max_dt):
        return None, warnings

    max_day = pd.Timestamp(max_dt).date()

    # Prefer most recent complete natural month.
    first_of_this_month = max_day.replace(day=1)
    end = first_of_this_month
    prev_month_end = end - timedelta(days=1)
    start = prev_month_end.replace(day=1)

    if start >= end:
        # fallback recent 30 days
        end = max_day + timedelta(days=1)
        start = end - timedelta(days=30)
        warnings.append("Could not infer full month; defaulted to last 30 days.")

    return TimeRange(start=start, end=end), warnings
