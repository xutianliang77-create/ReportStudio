from __future__ import annotations

import argparse
import json
from dataclasses import asdict

from reportstudio.core.pipeline import run_pipeline
from reportstudio.core.types import RunRequest


def _parse_args() -> RunRequest:
    p = argparse.ArgumentParser(prog="reportstudio")
    p.add_argument("--file", required=True, help="Input file path (.csv/.xlsx)")
    p.add_argument("--prompt", required=True, help="User intent/prompt for the report")
    p.add_argument("--out-dir", default="./artifacts", help="Output directory")
    p.add_argument(
        "--formats",
        default="xlsx,pdf,pptx",
        help="Comma-separated formats: xlsx,pdf,pptx",
    )
    p.add_argument("--topn", type=int, default=10, help="TopN for breakdown sections")
    p.add_argument(
        "--dim",
        default=None,
        help=(
            "Optional dimension column to use for TopN breakdown "
            "(default: first detected dimension)"
        ),
    )
    p.add_argument(
        "--measure",
        default=None,
        help=(
            "Optional numeric column to use for TopN breakdown (default: first detected numeric)"
        ),
    )
    p.add_argument(
        "--grain",
        default="month",
        choices=["day", "week", "month"],
        help="Trend aggregation grain (default: month)",
    )
    p.add_argument(
        "--time-range",
        default=None,
        help="Optional time range override: YYYY-MM-DD..YYYY-MM-DD",
    )

    ns = p.parse_args()
    formats = [f.strip().lower() for f in ns.formats.split(",") if f.strip()]

    return RunRequest(
        file=ns.file,
        prompt=ns.prompt,
        out_dir=ns.out_dir,
        formats=formats,
        topn=ns.topn,
        grain=ns.grain,
        time_range=ns.time_range,
        dim=ns.dim,
        measure=ns.measure,
    )


def main() -> None:
    req = _parse_args()
    result = run_pipeline(req)
    print(json.dumps(asdict(result), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
