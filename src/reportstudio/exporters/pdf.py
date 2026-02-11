from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class PdfArtifact:
    path: str


def export_pdf(
    out_dir: str,
    file_name: str,
    title: str,
    highlights: list[str],
    risks: list[str],
) -> PdfArtifact:
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.pdfgen import canvas

    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    path = out / file_name

    c = canvas.Canvas(str(path), pagesize=A4)
    w, h = A4

    # Best-effort font: fall back to default if missing
    try:
        # macOS common
        font_path = "/System/Library/Fonts/PingFang.ttc"
        pdfmetrics.registerFont(TTFont("PingFang", font_path))
        c.setFont("PingFang", 16)
    except Exception:
        c.setFont("Helvetica", 16)

    y = h - 60
    c.drawString(40, y, title)
    y -= 30

    c.setFont(c._fontname, 12)
    c.drawString(40, y, "Highlights")
    y -= 18
    for t in highlights[:10]:
        c.drawString(50, y, f"- {t}")
        y -= 16

    y -= 8
    c.drawString(40, y, "Risks")
    y -= 18
    for t in risks[:10]:
        c.drawString(50, y, f"- {t}")
        y -= 16

    c.showPage()
    c.save()
    return PdfArtifact(path=str(path))
