from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True, slots=True)
class PdfArtifact:
    path: str


def export_pdf(
    out_dir: str,
    file_name: str,
    *,
    title: str,
    spec: dict[str, Any],
    kpis: dict[str, Any],
    trend_rows: list[dict[str, Any]],
    breakdowns: list[dict[str, Any]],
    highlights: list[str],
    risks: list[str],
    actions: list[str],
    warnings: list[str],
) -> PdfArtifact:
    """Export a Community v1 structured PDF brief.

    Pages:
      1) Cover / title
      2) Spec
      3) KPI table
      4) Trend summary (chart + table)
      5) Breakdown summary
      6) Warnings / limitations

    The exporter is best-effort and stays read-only: it renders provided spec/kpis/tables.
    """

    from reportlab.graphics.charts.lineplots import LinePlot
    from reportlab.graphics.shapes import Drawing
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.pdfgen import canvas

    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    path = out / file_name

    c = canvas.Canvas(str(path), pagesize=A4)
    c.setPageCompression(0)  # keep text markers visible for lightweight tests
    w, h = A4

    # Best-effort font: fall back to default if missing
    base_font = "Helvetica"
    try:
        font_path = "/System/Library/Fonts/PingFang.ttc"  # macOS common
        pdfmetrics.registerFont(TTFont("PingFang", font_path))
        base_font = "PingFang"
    except Exception:
        base_font = "Helvetica"

    def heading(text: str) -> None:
        c.setFont(base_font, 18)
        c.drawString(40, h - 60, text)
        c.setFont(base_font, 11)

    def bullet_list(items: list[str], *, y0: float, max_items: int = 12) -> float:
        y = y0
        for t in items[:max_items]:
            if y < 60:
                break
            c.drawString(50, y, f"- {t}")
            y -= 16
        return y

    def kv_block(rows: list[tuple[str, str]], *, y0: float) -> float:
        y = y0
        c.setFont(base_font, 11)
        for k, v in rows:
            if y < 60:
                break
            c.setFont(base_font, 11)
            c.drawString(40, y, f"{k}: ")
            c.setFont(base_font, 11)
            c.drawString(120, y, v)
            y -= 16
        return y

    def simple_table(
        header: list[str],
        rows: list[list[str]],
        *,
        x0: float,
        y0: float,
        col_widths: list[float],
        row_h: float = 16,
        max_rows: int = 18,
    ) -> None:
        # header
        c.setFont(base_font, 10)
        c.setFillColor(colors.black)
        y = y0
        c.setFillColor(colors.lightgrey)
        c.rect(x0, y - row_h + 4, sum(col_widths), row_h, fill=1, stroke=0)
        c.setFillColor(colors.black)
        x = x0
        for i, cell in enumerate(header):
            c.drawString(x + 4, y, cell)
            x += col_widths[i]
        y -= row_h

        # rows
        for r in rows[:max_rows]:
            x = x0
            for i, cell in enumerate(r):
                c.drawString(x + 4, y, cell)
                x += col_widths[i]
            y -= row_h
            if y < 70:
                break

    def fmt(v: Any) -> str:
        if isinstance(v, float):
            return f"{v:,.2f}"
        return str(v)

    # Page 1: cover/title
    heading("Community v1 Report")
    c.setFont(base_font, 22)
    c.drawString(40, h - 110, title)
    c.setFont(base_font, 12)
    y = h - 150
    c.drawString(40, y, "Highlights")
    y = bullet_list(highlights, y0=y - 20)
    y -= 10
    c.drawString(40, y, "Risks")
    bullet_list(risks, y0=y - 20)
    c.showPage()

    # Page 2: spec
    heading("Spec")
    kv = [
        ("Time range", str(spec.get("time_range", "(none)"))),
        ("TopN", str(spec.get("topn", ""))),
        ("Date column", str(spec.get("date_column", ""))),
        ("Number columns", ", ".join([str(x) for x in spec.get("number_columns", [])]) or "(none)"),
        (
            "Dimension columns",
            ", ".join([str(x) for x in spec.get("dimension_columns", [])]) or "(none)",
        ),
    ]
    kv_block(kv, y0=h - 110)
    c.showPage()

    # Page 3: KPI table
    heading("KPI Summary")
    kpi_items = list(kpis.items())
    kpi_rows = [[str(k), fmt(v)] for k, v in kpi_items[:24]]
    simple_table(
        ["KPI", "Value"],
        kpi_rows,
        x0=40,
        y0=h - 110,
        col_widths=[260.0, 240.0],
    )
    c.showPage()

    # Page 4: trend summary (chart + table)
    heading("Trend Summary")
    if trend_rows:
        cols = list(trend_rows[0])
        period_col = "period" if "period" in cols else cols[0]
        value_cols = [c1 for c1 in cols if c1 != period_col]
        # chart for first numeric value col, if present
        if value_cols:
            xs: list[int] = []
            ys: list[float] = []
            for i, r in enumerate(trend_rows[:24]):
                xs.append(i)
                try:
                    ys.append(float(r.get(value_cols[0], 0.0)))
                except Exception:
                    ys.append(0.0)

            d = Drawing(520, 180)
            lp = LinePlot()
            lp.x = 40
            lp.y = 20
            lp.height = 140
            lp.width = 460
            lp.data = [list(zip(xs, ys, strict=False))]
            lp.lines[0].strokeColor = colors.HexColor("#2b6cb0")
            lp.xValueAxis.valueMin = 0
            lp.xValueAxis.valueMax = max(xs) if xs else 1
            d.add(lp)
            d.drawOn(c, 40, h - 320)

        # table (period + up to 2 measures)
        table_cols = [period_col] + value_cols[:2]
        table_rows = [[str(r.get(col, ""))[:18] for col in table_cols] for r in trend_rows[:16]]
        widths = [160.0] + [170.0 for _ in table_cols[1:]]
        simple_table(table_cols, table_rows, x0=40, y0=h - 350, col_widths=widths)
    else:
        c.setFont(base_font, 11)
        c.drawString(40, h - 120, "No trend table available (missing date column).")
    c.showPage()

    # Page 5: breakdown summary
    heading("Breakdown Summary")
    if breakdowns:
        b0 = breakdowns[0]
        dim = str(b0.get("dim", "dimension"))
        measure = str(b0.get("measure", "measure"))
        rows_any = b0.get("rows", [])
        c.setFont(base_font, 11)
        c.drawString(40, h - 110, f"Top breakdown by {dim} (measure: {measure})")

        # If breakdown rows contain share, render a pie chart (best-effort).
        if isinstance(rows_any, list) and rows_any and any("share" in r for r in rows_any):
            from reportlab.graphics.charts.piecharts import Pie

            top = rows_any[:8]
            labels = [str(r.get("category") or r.get(dim) or r.get("dim") or "")[:18] for r in top]
            values = []
            for r in top:
                try:
                    values.append(float(r.get("value", 0.0)))
                except Exception:
                    values.append(0.0)

            d = Drawing(520, 240)
            pie = Pie()
            pie.x = 40
            pie.y = 20
            pie.width = 220
            pie.height = 220
            pie.data = values
            pie.labels = labels
            pie.slices.strokeWidth = 0.5
            pie.slices[0].fillColor = colors.HexColor("#2b6cb0")
            if len(values) > 1:
                pie.slices[1].fillColor = colors.HexColor("#ed8936")
            if len(values) > 2:
                pie.slices[2].fillColor = colors.HexColor("#38a169")
            d.add(pie)
            d.drawOn(c, 40, h - 360)

        if isinstance(rows_any, list) and rows_any:
            row0 = rows_any[0]
            cols = list(row0.keys())
            cols = cols[:4] if len(cols) > 4 else cols
            bd_rows = [[fmt(r.get(col, ""))[:22] for col in cols] for r in rows_any[:18]]
            widths = [160.0, 140.0, 120.0, 90.0][: len(cols)]
            simple_table(cols, bd_rows, x0=40, y0=h - 390, col_widths=widths)
        else:
            c.drawString(40, h - 140, "No breakdown rows available.")
    else:
        c.setFont(base_font, 11)
        c.drawString(40, h - 120, "No breakdowns available (missing dimension/measure columns).")
    c.showPage()

    # Page 6: warnings/limitations
    heading("Warnings & Limitations")
    c.setFont(base_font, 11)
    y = h - 110
    c.drawString(40, y, "Warnings")
    y = bullet_list([str(x) for x in warnings], y0=y - 20, max_items=18)
    y -= 10
    c.drawString(40, y, "Suggested Actions")
    y = bullet_list(actions, y0=y - 20, max_items=10)
    y -= 10
    c.drawString(40, y, "Notes")
    bullet_list(
        [
            "This is an automated summary generated by ReportStudio Community v1.",
            "Numbers are computed from the provided dataset and may require validation.",
        ],
        y0=y - 20,
        max_items=5,
    )

    c.showPage()
    c.save()
    return PdfArtifact(path=str(path))
