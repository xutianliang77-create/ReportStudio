from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True, slots=True)
class PptxArtifact:
    path: str


def export_pptx(
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
) -> PptxArtifact:
    """Export a Community v1 structured PPTX deck.

    Slides:
      1) Cover
      2) KPI
      3) Trend
      4) Breakdown
      5) Risks / Actions
    """

    from pptx import Presentation
    from pptx.chart.data import CategoryChartData
    from pptx.enum.chart import XL_CHART_TYPE
    from pptx.util import Inches, Pt

    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    path = out / file_name

    prs = Presentation()

    def fmt(v: Any) -> str:
        if isinstance(v, float):
            return f"{v:,.2f}"
        return str(v)

    # Slide 1: cover
    s1 = prs.slides.add_slide(prs.slide_layouts[0])
    s1.shapes.title.text = title
    subtitle = s1.placeholders[1]
    subtitle.text = "ReportStudio Community v1"

    # Slide 2: KPI
    s2 = prs.slides.add_slide(prs.slide_layouts[5])  # title only
    s2.shapes.title.text = "KPI Summary"

    rows = min(12, max(1, len(kpis)))
    table_shape = s2.shapes.add_table(
        rows + 1,
        2,
        Inches(0.8),
        Inches(1.6),
        Inches(8.2),
        Inches(4.6),
    )
    table = table_shape.table
    table.cell(0, 0).text = "KPI"
    table.cell(0, 1).text = "Value"

    for i, (k, v) in enumerate(list(kpis.items())[:rows], start=1):
        table.cell(i, 0).text = str(k)
        table.cell(i, 1).text = fmt(v)

    # Slide 3: Trend
    s3 = prs.slides.add_slide(prs.slide_layouts[5])
    s3.shapes.title.text = "Trend Summary"

    if trend_rows:
        cols = list(trend_rows[0].keys())
        period_col = "period" if "period" in cols else cols[0]
        value_cols = [c for c in cols if c != period_col]

        categories = [str(r.get(period_col, "")) for r in trend_rows[:12]]
        if value_cols:
            chart_data = CategoryChartData()  # type: ignore[no-untyped-call]
            chart_data.categories = categories
            for vc in value_cols[:2]:
                series_vals: list[float] = []
                for r in trend_rows[:12]:
                    try:
                        series_vals.append(float(r.get(vc, 0.0)))
                    except Exception:
                        series_vals.append(0.0)
                chart_data.add_series(vc, series_vals)  # type: ignore[no-untyped-call]

            s3.shapes.add_chart(
                XL_CHART_TYPE.LINE,
                Inches(0.8),
                Inches(1.4),
                Inches(8.2),
                Inches(3.2),
                chart_data,
            )

        # small table under chart
        t_rows = min(6, len(trend_rows))
        colnames = [period_col] + value_cols[:2]
        t = s3.shapes.add_table(
            t_rows + 1,
            len(colnames),
            Inches(0.8),
            Inches(4.8),
            Inches(8.2),
            Inches(1.4),
        ).table
        for j, cn in enumerate(colnames):
            t.cell(0, j).text = cn
        for i in range(t_rows):
            r = trend_rows[i]
            for j, cn in enumerate(colnames):
                t.cell(i + 1, j).text = fmt(r.get(cn, ""))
    else:
        tx = s3.shapes.add_textbox(Inches(0.8), Inches(1.6), Inches(8.2), Inches(1.0))
        tx.text_frame.text = "No trend table available (missing date column)."

    # Slide 4: Breakdown
    s4 = prs.slides.add_slide(prs.slide_layouts[5])
    s4.shapes.title.text = "Breakdown Summary"

    if breakdowns and isinstance(breakdowns[0].get("rows", None), list):
        b0 = breakdowns[0]
        dim = str(b0.get("dim", "dimension"))
        measure = str(b0.get("measure", "measure"))
        rows_any: list[dict[str, Any]] = list(b0.get("rows", []))

        cap = s4.shapes.add_textbox(Inches(0.8), Inches(1.3), Inches(8.2), Inches(0.6))
        cap.text_frame.text = f"Top breakdown by {dim} (measure: {measure})"

        if rows_any:
            cols = list(rows_any[0].keys())
            cols = cols[:3] if len(cols) > 3 else cols
            n = min(10, len(rows_any))
            t = s4.shapes.add_table(
                n + 1,
                len(cols),
                Inches(0.8),
                Inches(1.9),
                Inches(8.2),
                Inches(3.6),
            ).table
            for j, cn in enumerate(cols):
                t.cell(0, j).text = cn
            for i in range(n):
                r = rows_any[i]
                for j, cn in enumerate(cols):
                    t.cell(i + 1, j).text = fmt(r.get(cn, ""))
        else:
            tx = s4.shapes.add_textbox(Inches(0.8), Inches(1.9), Inches(8.2), Inches(1.0))
            tx.text_frame.text = "No breakdown rows available."
    else:
        tx = s4.shapes.add_textbox(Inches(0.8), Inches(1.6), Inches(8.2), Inches(1.0))
        tx.text_frame.text = "No breakdowns available (missing dimension/measure columns)."

    # Slide 5: Risks / Actions
    s5 = prs.slides.add_slide(prs.slide_layouts[5])
    s5.shapes.title.text = "Risks & Actions"

    box = s5.shapes.add_textbox(Inches(0.8), Inches(1.4), Inches(8.2), Inches(5.0))
    tf = box.text_frame
    tf.clear()

    p = tf.paragraphs[0]
    p.text = "Highlights"
    p.font.bold = True
    p.font.size = Pt(16)

    for t in highlights[:5]:
        q = tf.add_paragraph()
        q.text = f"• {t}"
        q.level = 1

    r0 = tf.add_paragraph()
    r0.text = "Risks"
    r0.level = 0
    r0.font.bold = True
    r0.font.size = Pt(16)

    for t in risks[:6]:
        q = tf.add_paragraph()
        q.text = f"• {t}"
        q.level = 1

    a0 = tf.add_paragraph()
    a0.text = "Actions"
    a0.level = 0
    a0.font.bold = True
    a0.font.size = Pt(16)

    for t in actions[:6]:
        q = tf.add_paragraph()
        q.text = f"• {t}"
        q.level = 1

    # (Spec is kept in the PDF; include minimally in speaker notes via slide notes.)
    notes = s5.notes_slide.notes_text_frame
    notes.text = f"Spec: time_range={spec.get('time_range')} topn={spec.get('topn')}"

    prs.save(str(path))
    return PptxArtifact(path=str(path))
