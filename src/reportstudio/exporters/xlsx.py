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

    # style
    for cell in ws[5]:
        cell.font = Font(bold=True)

    wb.save(path)
    return XlsxArtifact(path=str(path))
