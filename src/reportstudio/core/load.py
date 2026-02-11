from __future__ import annotations

from pathlib import Path

import pandas as pd


def _detect_header_row_xlsx(df_preview: pd.DataFrame) -> int | None:
    """Heuristic header-row detection for template-like XLSX.

    We scan the first ~50 rows for a row that looks like a table header.
    """

    header_keywords = {"序号", "数量", "单位", "单价", "总价"}
    max_rows = min(len(df_preview), 60)

    for i in range(max_rows):
        hits = 0
        for v in df_preview.iloc[i].values.tolist():
            s = str(v).strip()
            if s in header_keywords:
                hits += 1
        if hits >= 2:
            return i

    return None


def load_table(path: str) -> pd.DataFrame:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(str(p))

    suffix = p.suffix.lower()
    if suffix == ".csv":
        return pd.read_csv(p)
    if suffix in {".xlsx", ".xls"}:
        # First read a preview without header to detect where the actual header is.
        preview = pd.read_excel(p, header=None, nrows=60)
        header_row = _detect_header_row_xlsx(preview)
        if header_row is None:
            return pd.read_excel(p)

        df = pd.read_excel(p, header=header_row)
        # Drop fully-empty rows
        df = df.dropna(how="all")
        return df

    raise ValueError(f"Unsupported input file type: {suffix}")
