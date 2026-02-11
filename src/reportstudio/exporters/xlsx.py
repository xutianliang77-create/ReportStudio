from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


@dataclass(frozen=True, slots=True)
class XlsxArtifact:
    path: str


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
    from openpyxl.styles import Font

    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    path = out / file_name

    wb = Workbook()
    ws = wb.active
    ws.title = "Summary"

    ws.append(["generated_at", datetime.now(UTC).isoformat()])
    ws.append(["time_range", spec.get("time_range", "")])
    ws.append(["topn", spec.get("topn", "")])
    ws.append([])
    ws.append(["KPI", "Value"])
    for k, v in kpis.items():
        ws.append([k, v])

    ws.append([])
    ws.append(["Warnings"])
    for w in warnings:
        ws.append([w])

    # trend sheet
    if trend_rows:
        ts = wb.create_sheet("Trend")
        if trend_rows:
            cols = list(trend_rows[0].keys())
            ts.append(cols)
            for r in trend_rows[:5000]:
                ts.append([r.get(c) for c in cols])

    # breakdown sheet
    if breakdowns:
        bs = wb.create_sheet("Breakdowns")
        for b in breakdowns:
            bs.append(["dim", b.get("dim"), "measure", b.get("measure")])

            # TopN by value
            bs.append(["section", "top_by_value"])
            rows = b.get("rows") or []
            if rows:
                cols = list(rows[0].keys())
                bs.append(cols)
                for r in rows[:2000]:
                    bs.append([r.get(c) for c in cols])
            else:
                bs.append(["(no rows)"])

            # Contribution-to-change
            change = b.get("change")
            if isinstance(change, dict):
                bs.append([])
                bs.append(
                    [
                        "section",
                        "contribution_to_change",
                        "period_prev",
                        change.get("period_prev"),
                        "period_last",
                        change.get("period_last"),
                    ]
                )
                bs.append(
                    [
                        "totals",
                        "total_prev",
                        change.get("total_prev"),
                        "total_last",
                        change.get("total_last"),
                        "total_delta",
                        change.get("total_delta"),
                    ]
                )

                pos_rows = change.get("top_positive") or []
                neg_rows = change.get("top_negative") or []

                bs.append([])
                bs.append(["top_positive_contributors"])
                if pos_rows:
                    cols = list(pos_rows[0].keys())
                    bs.append(cols)
                    for r in pos_rows[:2000]:
                        bs.append([r.get(c) for c in cols])
                else:
                    bs.append(["(none)"])

                bs.append([])
                bs.append(["top_negative_contributors"])
                if neg_rows:
                    cols = list(neg_rows[0].keys())
                    bs.append(cols)
                    for r in neg_rows[:2000]:
                        bs.append([r.get(c) for c in cols])
                else:
                    bs.append(["(none)"])

            bs.append([])

    # style
    for cell in ws[5]:
        cell.font = Font(bold=True)

    wb.save(path)
    return XlsxArtifact(path=str(path))
