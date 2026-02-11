# ReportStudio 示例数据与模板

这里放的是 **ReportStudio Community** 的“推荐输入模板”与可直接跑通的样例数据。

## 1) 通用业务数据模板（推荐）

### 字段建议

- **date**：日期列（ReportStudio 用它做趋势：day/week/month）
- **dimension**：维度列（例如 region/channel/product 等，用于 TopN 拆解）
- **numeric**：数值列（例如 revenue/orders/cost/profit 等，用于 KPI、趋势、贡献度）

最常见的可用字段组合：

- `date`（必备：想要趋势/环比/贡献度就需要）
- `region`（可选维度）
- `channel`（可选维度）
- `product`（可选维度）
- `revenue`（数值指标）
- `orders`（数值指标）
- `cost`、`profit`（数值指标）

### 样例数据

- `sample_sales_daily.csv`
- `sample_sales_daily.xlsx`

可直接运行：

```bash
python -m reportstudio.cli.main \
  --file ./examples/sample_sales_daily.xlsx \
  --prompt "生成月报" \
  --out-dir ./artifacts \
  --formats xlsx,pdf,pptx \
  --grain month \
  --dim region \
  --measure revenue
```

## 2) 仅月度趋势（更简化）

- `template_trend_month_region.csv`

字段：`date`（按月）、`region`、`revenue`、`orders`。

## 3) 预算/采购清单类（用于饼图）

- `template_budget_items.csv`
- `template_budget_items.xlsx`

字段：
- `category`：类别（用于饼图/占比）
- `item`：条目名称
- `quantity` / `unit_price` / `total`

可直接运行：

```bash
python -m reportstudio.cli.main \
  --file ./examples/template_budget_items.xlsx \
  --prompt "生成预算汇报" \
  --out-dir ./artifacts \
  --formats pdf \
  --grain month
```

> 注意：预算清单通常没有日期列，所以趋势会跳过，但 PDF 里会输出类别占比（饼图 + 表格）。
