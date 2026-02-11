from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Any

import pandas as pd

from reportstudio.core.aggregate import build_trend, compute_period_deltas
from reportstudio.core.breakdown import build_topn_breakdown
from reportstudio.core.insights import generate_insights
from reportstudio.core.load import load_table
from reportstudio.core.metrics import compute_kpis
from reportstudio.core.schema import guess_schema
from reportstudio.core.time_range import default_time_range, parse_time_range
from reportstudio.core.types import Artifact, RunRequest, RunResult, Spec, Summary, Tables
from reportstudio.exporters.pdf import export_pdf
from reportstudio.exporters.pptx import export_pptx
from reportstudio.exporters.xlsx import export_xlsx


def _jsonable(v: object) -> object:
    if isinstance(v, pd.Timestamp):
        return v.isoformat()
    return v


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

    # Trend
    trend_rows: list[dict[str, Any]] = []
    if schema.date_column is not None:
        trend = build_trend(df, schema.date_column, schema.number_columns, grain=req.grain)
        warnings.extend(trend.warnings)
        deltas, delta_w = compute_period_deltas(trend)
        warnings.extend(delta_w)
    else:
        deltas = {}

    kpi = compute_kpis(df, schema.number_columns)
    # merge deltas into kpis for reporting
    kpis = {**kpi.kpis, **deltas}

    insight_pack = generate_insights(kpis, warnings)

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

    # Tables for JSON (stable)
    if schema.date_column is not None:
        raw_rows = (
            trend.df.reset_index()
            .rename(columns={"__period__": "period"})
            .rename(columns={trend.df.index.name or "__period__": "period"})
            .to_dict(orient="records")
        )
        trend_rows = [{str(k): _jsonable(v) for k, v in r.items()} for r in raw_rows]

    breakdowns: list[dict[str, Any]] = []
    if schema.dimension_columns and schema.number_columns:
        dim = req.dim or schema.dimension_columns[0]
        measure = req.measure or schema.number_columns[0]

        if dim not in schema.dimension_columns:
            warnings.append(
                f"Requested dim={dim} not in detected dimensions; "
                f"defaulting to {schema.dimension_columns[0]}"
            )
            dim = schema.dimension_columns[0]
        if measure not in schema.number_columns:
            warnings.append(
                f"Requested measure={measure} not in detected numeric columns; "
                f"defaulting to {schema.number_columns[0]}"
            )
            measure = schema.number_columns[0]

        bd = build_topn_breakdown(
            df,
            dim=dim,
            measure=measure,
            topn=req.topn,
            date_col=schema.date_column,
            grain=req.grain,
        )
        warnings.extend(bd.warnings)

        b: dict[str, Any] = {
            "dim": dim,
            "measure": measure,
            "rows": bd.df.to_dict(orient="records"),
        }
        if bd.change is not None:
            b["change"] = {
                "period_prev": _jsonable(bd.change.period_prev),
                "period_last": _jsonable(bd.change.period_last),
                "total_prev": bd.change.total_prev,
                "total_last": bd.change.total_last,
                "total_delta": bd.change.total_delta,
                "top_positive": bd.change.df_pos.to_dict(orient="records"),
                "top_negative": bd.change.df_neg.to_dict(orient="records"),
            }
        breakdowns.append(b)

    formats = [f for f in req.formats if f in {"xlsx", "pdf", "pptx"}]
    if not formats:
        formats = ["xlsx", "pdf", "pptx"]
        warnings.append("No valid formats specified; defaulted to xlsx,pdf,pptx")

    # Exporters: best-effort; add warnings rather than crashing
    if "xlsx" in formats:
        x = export_xlsx(
            out_dir,
            "reportstudio_summary.xlsx",
            kpis,
            warnings,
            spec=asdict(spec),
            trend_rows=trend_rows,
            breakdowns=breakdowns,
        )
        artifacts.append(Artifact(format="xlsx", path=x.path))

    if "pdf" in formats:
        try:
            p = export_pdf(
                out_dir,
                "reportstudio_brief.pdf",
                title=title,
                spec=asdict(spec),
                kpis=kpis,
                trend_rows=trend_rows,
                breakdowns=breakdowns,
                highlights=insight_pack.highlights,
                risks=insight_pack.risks,
                actions=insight_pack.actions,
                warnings=warnings,
            )
            artifacts.append(Artifact(format="pdf", path=p.path))
        except Exception as exc:
            warnings.append(f"PDF export skipped: {type(exc).__name__}: {exc}")

    if "pptx" in formats:
        try:
            ppt = export_pptx(
                out_dir,
                "reportstudio_deck.pptx",
                title=title,
                spec=asdict(spec),
                kpis=kpis,
                trend_rows=trend_rows,
                breakdowns=breakdowns,
                highlights=insight_pack.highlights,
                risks=insight_pack.risks,
                actions=insight_pack.actions,
            )
            artifacts.append(Artifact(format="pptx", path=ppt.path))
        except Exception as exc:
            warnings.append(f"PPTX export skipped: {type(exc).__name__}: {exc}")

    summary = Summary(
        highlights=insight_pack.highlights,
        risks=insight_pack.risks,
        actions=insight_pack.actions,
    )

    tables = Tables(trend=trend_rows, breakdowns=breakdowns)

    return RunResult(
        artifacts=artifacts,
        summary=summary,
        spec=spec,
        warnings=warnings,
        tables=tables,
        meta={
            "kpis": kpis,
            "grain": req.grain,
        },
    )
