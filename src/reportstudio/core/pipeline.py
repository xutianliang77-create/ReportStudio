from __future__ import annotations

from dataclasses import asdict
from pathlib import Path

from reportstudio.core.insights import generate_insights
from reportstudio.core.load import load_table
from reportstudio.core.metrics import compute_kpis
from reportstudio.core.schema import guess_schema
from reportstudio.core.time_range import default_time_range, parse_time_range
from reportstudio.core.types import Artifact, RunRequest, RunResult, Spec, Summary
from reportstudio.exporters.pdf import export_pdf
from reportstudio.exporters.pptx import export_pptx
from reportstudio.exporters.xlsx import export_xlsx


def run_pipeline(req: RunRequest) -> RunResult:
    warnings: list[str] = []

    df = load_table(req.file)

    schema = guess_schema(df)
    warnings.extend(schema.warnings)

    # time range
    tr = None
    if req.time_range:
        tr = parse_time_range(req.time_range)
        warnings.append(f"Using explicit time_range={tr.to_spec()}")
    else:
        tr, tr_w = default_time_range(df, schema.date_column)
        warnings.extend(tr_w)
        if tr is not None:
            warnings.append(f"Default time_range={tr.to_spec()}")

    if tr is not None and schema.date_column is not None:
        # filter
        d = df[schema.date_column]
        df = df[(d.dt.date >= tr.start) & (d.dt.date < tr.end)]

    kpi = compute_kpis(df, schema.number_columns)
    insight_pack = generate_insights(kpi.kpis, warnings)

    out_dir = str(Path(req.out_dir))

    artifacts: list[Artifact] = []
    title = f"ReportStudio: {Path(req.file).name}"

    spec = Spec(
        time_range=tr.to_spec() if tr is not None else "(none)",
        topn=req.topn,
        date_column=schema.date_column,
        number_columns=schema.number_columns,
        dimension_columns=schema.dimension_columns,
    )

    formats = [f for f in req.formats if f in {"xlsx", "pdf", "pptx"}]
    if not formats:
        formats = ["xlsx", "pdf", "pptx"]
        warnings.append("No valid formats specified; defaulted to xlsx,pdf,pptx")

    # Exporters: best-effort; add warnings rather than crashing
    if "xlsx" in formats:
        x = export_xlsx(
            out_dir,
            "reportstudio_summary.xlsx",
            kpi.kpis,
            warnings,
            spec=asdict(spec),
        )
        artifacts.append(Artifact(format="xlsx", path=x.path))

    if "pdf" in formats:
        try:
            p = export_pdf(
                out_dir,
                "reportstudio_brief.pdf",
                title=title,
                highlights=insight_pack.highlights,
                risks=insight_pack.risks,
            )
            artifacts.append(Artifact(format="pdf", path=p.path))
        except Exception as exc:
            warnings.append(f"PDF export skipped: {type(exc).__name__}: {exc}")

    if "pptx" in formats:
        try:
            ppt = export_pptx(out_dir, "reportstudio_deck.pptx", title=title, kpis=kpi.kpis)
            artifacts.append(Artifact(format="pptx", path=ppt.path))
        except Exception as exc:
            warnings.append(f"PPTX export skipped: {type(exc).__name__}: {exc}")

    summary = Summary(
        highlights=insight_pack.highlights,
        risks=insight_pack.risks,
        actions=insight_pack.actions,
    )

    return RunResult(artifacts=artifacts, summary=summary, spec=spec, warnings=warnings)
