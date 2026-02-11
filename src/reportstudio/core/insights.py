from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class InsightPack:
    highlights: list[str]
    risks: list[str]
    actions: list[str]


def generate_insights(kpis: dict[str, float], warnings: list[str]) -> InsightPack:
    # Rule-driven, conservative. No causal claims.
    highlights: list[str] = []
    risks: list[str] = []
    actions: list[str] = []

    row_count = kpis.get("row_count")
    if isinstance(row_count, float) and row_count == 0:
        risks.append("数据为空，无法生成有效报表。")
        actions.append("检查输入文件与筛选时间范围。")

    if warnings:
        risks.append("存在字段/默认参数警告，部分分析可能被跳过。")
        actions.append("确认日期列与数值列识别是否正确。")

    if not highlights and row_count and row_count > 0:
        highlights.append(f"已处理 {int(row_count)} 行数据。")

    if not actions:
        actions.append("如需更精确结论，请指定时间范围、核心指标与维度。")

    return InsightPack(highlights=highlights, risks=risks, actions=actions)
