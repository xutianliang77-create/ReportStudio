from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


@dataclass(frozen=True, slots=True)
class XlsxArtifact:
    path: str


# ----------------------------
# Formatting / governance knobs
# ----------------------------


def _get_limits(spec: Mapping[str, Any]) -> dict[str, int]:
    defaults: dict[str, int] = {
        "trend_max_rows": 5000,
        "breakdown_max_rows": 200,
        "contributors_max_rows": 200,
        "max_width_probe_rows": 200,
    }

    # Allow tests / callers to override without changing the public function signature.
    raw = spec.get("xlsx_limits")
    if isinstance(raw, dict):
        for k, v in raw.items():
            if isinstance(k, str) and isinstance(v, int) and v > 0:
                defaults[k] = v

    return defaults


def _looks_percent_col(name: str) -> bool:
    n = name.strip().lower()
    return any(tok in n for tok in ("rate", "pct", "percent", "share", "%"))


# (removed unused helper)


def _set_header_style(ws: Any, header_row: int = 1) -> None:
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side

    fill = PatternFill("solid", fgColor="1F4E79")  # dark blue
    font = Font(bold=True, color="FFFFFF")
    align = Alignment(horizontal="center", vertical="center", wrap_text=True)
    thin = Side(style="thin", color="D9D9D9")
    border = Border(left=thin, right=thin, top=thin, bottom=thin)

    for cell in ws[header_row]:
        cell.fill = fill
        cell.font = font
        cell.alignment = align
        cell.border = border

    ws.row_dimensions[header_row].height = 20


def _set_column_formats(ws: Any, header_row: int, *, percent_cols: set[int]) -> None:
    from openpyxl.styles import numbers

    for col_idx in range(1, ws.max_column + 1):
        fmt = "0.00%" if col_idx in percent_cols else numbers.FORMAT_NUMBER_COMMA_SEPARATED1

        for row_idx in range(header_row + 1, ws.max_row + 1):
            cell = ws.cell(row=row_idx, column=col_idx)
            if isinstance(cell.value, (int, float)):
                cell.number_format = fmt


def _auto_column_width(ws: Any, *, probe_rows: int) -> None:
    # Reasonable auto-width that doesn't explode on huge sheets.
    from openpyxl.utils import get_column_letter

    max_row = min(ws.max_row, probe_rows)
    for col_idx in range(1, ws.max_column + 1):
        max_len = 0
        for row_idx in range(1, max_row + 1):
            v = ws.cell(row=row_idx, column=col_idx).value
            if v is None:
                continue
            s = str(v)
            if len(s) > max_len:
                max_len = len(s)

        # clamp
        width = max(10, min(42, max_len + 2))
        ws.column_dimensions[get_column_letter(col_idx)].width = width


def _truncate_rows(
    rows: Sequence[Mapping[str, Any]],
    *,
    limit: int,
    what: str,
    warnings_out: list[str],
) -> list[Mapping[str, Any]]:
    if len(rows) <= limit:
        return list(rows)
    warnings_out.append(f"{what}: exported first {limit} rows (truncated from {len(rows)}).")
    return list(rows[:limit])


def export_xlsx(
    out_dir: str,
    file_name: str,
    kpis: dict[str, float],
    warnings: list[str],
    spec: dict[str, Any],
    trend_rows: list[dict[str, Any]] | None = None,
    breakdowns: list[dict[str, Any]] | None = None,
) -> XlsxArtifact:
    from openpyxl import Workbook
    from openpyxl.chart import BarChart, LineChart, Reference
    from openpyxl.chart.label import DataLabelList
    from openpyxl.styles import Alignment, Font, PatternFill

    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    path = out / file_name

    limits = _get_limits(spec)
    xlsx_warnings: list[str] = list(warnings)
    xlsx_warnings.append("XLSX export contains aggregates only (no raw detail dump).")

    wb = Workbook()

    # ----------------
    # Summary sheet
    # ----------------
    ws = wb.active
    ws.title = "Summary"

    title = spec.get("title") or "Report Summary"
    tr = spec.get("time_range", "")
    topn = spec.get("topn", "")
    generated_at = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")

    # Title block
    ws.merge_cells("A1:D1")
    ws["A1"] = title
    ws["A1"].font = Font(size=18, bold=True)
    ws["A1"].alignment = Alignment(horizontal="left", vertical="center")

    ws["A2"] = "Generated"
    ws["B2"] = generated_at
    ws["A3"] = "Date range"
    ws["B3"] = tr
    ws["A4"] = "TopN"
    ws["B4"] = topn

    for row_idx in range(2, 5):
        ws[f"A{row_idx}"].font = Font(bold=True, color="595959")

    ws.append([])

    # KPI block
    kpi_header_row = ws.max_row + 1
    ws.append(["Key KPIs", "Value", "Notes", ""])
    _set_header_style(ws, header_row=kpi_header_row)

    # Stable ordering for readability
    for k in sorted(kpis.keys()):
        ws.append([k, kpis[k], "", ""])

    ws.append([])

    # Warnings block
    warn_header_row = ws.max_row + 1
    ws.append(["Warnings / Notes", "", "", ""])
    _set_header_style(ws, header_row=warn_header_row)
    ws.merge_cells(start_row=warn_header_row, start_column=1, end_row=warn_header_row, end_column=4)

    warn_fill = PatternFill("solid", fgColor="FFF2CC")  # light yellow
    for w in xlsx_warnings:
        ws.append([w, "", "", ""])
        row = ws.max_row
        ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=4)
        ws[f"A{row}"].fill = warn_fill
        ws[f"A{row}"].alignment = Alignment(wrap_text=True, vertical="top")

    ws.freeze_panes = "A6"
    _auto_column_width(ws, probe_rows=limits["max_width_probe_rows"])

    # -------------
    # Trend sheet
    # -------------
    if trend_rows:
        ts = wb.create_sheet("Trend")
        # Note: new worksheets may include an initial blank row; we avoid relying on
        # Worksheet.append() when writing tables to keep header/freeze panes stable.
        cols = list(trend_rows[0].keys())

        # governance: truncate
        trend_limit = limits["trend_max_rows"]
        trows = _truncate_rows(
            trend_rows,
            limit=trend_limit,
            what="Trend table",
            warnings_out=xlsx_warnings,
        )

        # Write the table with explicit coordinates.
        # (New worksheets start with a default blank row; relying on .append() tends to
        # leave a leading empty row, shifting header/freeze panes and breaking charts.)
        row_cursor = 1
        if len(trend_rows) > trend_limit:
            ts.cell(row=row_cursor, column=1, value="NOTE")
            ts.cell(
                row=row_cursor,
                column=2,
                value=(
                    f"Trend table truncated to first {trend_limit} rows "
                    f"(input had {len(trend_rows)} rows)."
                ),
            )
            row_cursor += 2  # + one empty spacer row

        header_row = row_cursor
        for j, c in enumerate(cols, start=1):
            ts.cell(row=header_row, column=j, value=c)

        for i, row_map in enumerate(trows, start=header_row + 1):
            for j, c in enumerate(cols, start=1):
                ts.cell(row=i, column=j, value=row_map.get(c))

        _set_header_style(ts, header_row=header_row)
        ts.freeze_panes = ts.cell(row=header_row + 1, column=1).coordinate

        percent_cols: set[int] = {i + 1 for i, c in enumerate(cols) if _looks_percent_col(str(c))}
        _set_column_formats(ts, header_row, percent_cols=percent_cols)
        _auto_column_width(ts, probe_rows=limits["max_width_probe_rows"])

        # chart: line chart for first numeric series (besides period)
        # Expect a column named "period" (from pipeline), but fall back to first column.
        cat_col = cols.index("period") + 1 if "period" in cols else 1

        # Find first numeric column among remaining columns
        numeric_col: int | None = None
        for idx, _c in enumerate(cols, start=1):
            if idx == cat_col:
                continue
            # check first non-null value
            for row_idx in range(header_row + 1, ts.max_row + 1):
                v = ts.cell(row=row_idx, column=idx).value
                if v is None:
                    continue
                if isinstance(v, (int, float)):
                    numeric_col = idx
                break
            if numeric_col is not None:
                break

        if numeric_col is not None and ts.max_row >= header_row + 2:
            chart = LineChart()
            chart.title = "Trend"
            chart.y_axis.title = str(cols[numeric_col - 1])
            chart.x_axis.title = str(cols[cat_col - 1])

            data = Reference(ts, min_col=numeric_col, min_row=header_row, max_row=ts.max_row)
            cats = Reference(ts, min_col=cat_col, min_row=header_row + 1, max_row=ts.max_row)
            chart.add_data(data, titles_from_data=True)
            chart.set_categories(cats)
            chart.height = 10
            chart.width = 22
            chart.dataLabels = DataLabelList(showVal=False)
            ts.add_chart(chart, "H2")

    # -----------------
    # Breakdowns sheet
    # -----------------
    if breakdowns:
        bs = wb.create_sheet("Breakdowns")
        if bs.max_row == 1 and bs.max_column == 1 and bs["A1"].value is None:
            bs.delete_rows(1)
        bs.freeze_panes = "A2"

        # We'll keep a consistent "table" structure per section:
        # - a section header row
        # - a table header row
        # - data rows
        sec_fill = PatternFill("solid", fgColor="E7E6E6")

        chart_placed = False

        for b in breakdowns:
            dim = str(b.get("dim", ""))
            measure = str(b.get("measure", ""))

            # section header
            bs.append([f"Breakdown: {dim} by {measure}"])
            bs.merge_cells(start_row=bs.max_row, start_column=1, end_row=bs.max_row, end_column=6)
            bs.cell(row=bs.max_row, column=1).font = Font(bold=True)
            bs.cell(row=bs.max_row, column=1).fill = sec_fill

            # TopN by value
            rows = b.get("rows") or []
            if rows:
                brows = _truncate_rows(
                    rows,
                    limit=limits["breakdown_max_rows"],
                    what=f"Breakdown({dim}) top_by_value",
                    warnings_out=xlsx_warnings,
                )

                cols = list(brows[0].keys())
                header_row = bs.max_row + 1
                bs.append(cols)
                for row_map in brows:
                    bs.append([row_map.get(c) for c in cols])
                _set_header_style(bs, header_row=header_row)

                percent_cols = {i + 1 for i, c in enumerate(cols) if _looks_percent_col(str(c))}
                _set_column_formats(bs, header_row, percent_cols=percent_cols)

                # chart: pick first string-like column as category and first numeric as value
                if not chart_placed:
                    bd_cat_col: int | None = None
                    bd_val_col: int | None = None
                    for idx, c in enumerate(cols, start=1):
                        # category heuristic
                        if bd_cat_col is None and (
                            "dim" in str(c).lower() or "name" in str(c).lower()
                        ):
                            bd_cat_col = idx
                    # fallback: first col
                    if bd_cat_col is None:
                        bd_cat_col = 1

                    for idx in range(1, len(cols) + 1):
                        if idx == bd_cat_col:
                            continue
                        for row_idx in range(header_row + 1, bs.max_row + 1):
                            v = bs.cell(row=row_idx, column=idx).value
                            if isinstance(v, (int, float)):
                                bd_val_col = idx
                                break
                        if bd_val_col is not None:
                            break

                    if bd_val_col is not None and bs.max_row - header_row >= 2:
                        bar = BarChart()
                        bar.title = "TopN"
                        bar.y_axis.title = str(cols[bd_val_col - 1])
                        bar.x_axis.title = str(cols[bd_cat_col - 1])
                        data = Reference(
                            bs,
                            min_col=bd_val_col,
                            min_row=header_row,
                            max_row=bs.max_row,
                        )
                        cats = Reference(
                            bs,
                            min_col=bd_cat_col,
                            min_row=header_row + 1,
                            max_row=bs.max_row,
                        )
                        bar.add_data(data, titles_from_data=True)
                        bar.set_categories(cats)
                        bar.height = 12
                        bar.width = 22
                        bs.add_chart(bar, "H2")
                        chart_placed = True

            else:
                bs.append(["(no rows)"])

            # Contribution-to-change
            change = b.get("change")
            if isinstance(change, dict):
                bs.append([])
                bs.append(
                    [
                        "Contribution to change",
                        "period_prev",
                        change.get("period_prev"),
                        "period_last",
                        change.get("period_last"),
                    ]
                )
                bs.append(
                    [
                        "Totals",
                        "total_prev",
                        change.get("total_prev"),
                        "total_last",
                        change.get("total_last"),
                        "total_delta",
                        change.get("total_delta"),
                    ]
                )

                for label, key in (
                    ("Top positive contributors", "top_positive"),
                    ("Top negative contributors", "top_negative"),
                ):
                    bs.append([])
                    bs.append([label])
                    rows2 = change.get(key) or []
                    if rows2:
                        crows = _truncate_rows(
                            rows2,
                            limit=limits["contributors_max_rows"],
                            what=f"Breakdown({dim}) {key}",
                            warnings_out=xlsx_warnings,
                        )
                        cols2 = list(crows[0].keys())
                        header_row = bs.max_row + 1
                        bs.append(cols2)
                        for row_map in crows:
                            bs.append([row_map.get(c) for c in cols2])
                        _set_header_style(bs, header_row=header_row)
                        percent_cols2 = {
                            i + 1 for i, c in enumerate(cols2) if _looks_percent_col(str(c))
                        }
                        _set_column_formats(bs, header_row, percent_cols=percent_cols2)
                    else:
                        bs.append(["(none)"])

            bs.append([])

        _auto_column_width(bs, probe_rows=limits["max_width_probe_rows"])

    # Refresh warnings block if exporter added governance warnings
    # (we append after writing; ensure the workbook contains those notes)
    # Note: write-back only if we actually added extra warnings.
    if len(xlsx_warnings) != len(warnings) + 1:
        # Clear and rewrite the warnings section is complex; instead we add a final block.
        ws.append([])
        ws.append(["Export warnings (XLSX)", "", "", ""])
        row = ws.max_row
        _set_header_style(ws, header_row=row)
        ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=4)
        warn_fill = PatternFill("solid", fgColor="FFF2CC")
        for w in xlsx_warnings[len(warnings) + 1 :]:
            ws.append([w, "", "", ""])
            r = ws.max_row
            ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=4)
            ws[f"A{r}"].fill = warn_fill
            ws[f"A{r}"].alignment = Alignment(wrap_text=True, vertical="top")

    wb.save(path)
    return XlsxArtifact(path=str(path))
