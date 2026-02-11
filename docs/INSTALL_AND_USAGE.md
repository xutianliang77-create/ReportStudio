# ReportStudio Community v1.0 — 安装与使用说明

> 目标：把 CSV/XLSX 变成可汇报的静态交付物（默认导出 **xlsx + pdf + pptx**）。
>
> 安全边界（社区版）：**只读**、不写数据库、**不修改源文件**、默认不做外网请求。

---

## 1) 环境要求

- Python：**>= 3.11**
- OS：macOS / Linux / Windows 均可（建议在虚拟环境运行）

---

## 2) 安装（开发者模式 / 本地运行）

在仓库根目录执行：

```bash
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -e '.[dev]'
```

验证：

```bash
python -m reportstudio.cli.main --help
```

> 注：当前 Community 版本以仓库内模块方式运行（`python -m reportstudio.cli.main`）。如果你希望安装成系统命令 `reportstudio ...`，需要后续做一次 packaging/entrypoint 发布（可以再安排）。

---

## 3) 快速开始

### 3.1 最小命令

```bash
python -m reportstudio.cli.main \
  --file ./data.xlsx \
  --prompt "生成月报" \
  --out-dir ./artifacts
```

默认会在 `--out-dir` 下生成：
- `reportstudio_summary.xlsx`
- `reportstudio_report.pdf`
- `reportstudio_deck.pptx`

并在 stdout 输出一份 JSON（用于机器验收/流水线集成）。

### 3.2 指定输出格式

```bash
python -m reportstudio.cli.main \
  --file ./data.csv \
  --prompt "生成周报" \
  --formats xlsx,pdf
```

> `--formats` 支持：`xlsx,pdf,pptx`（逗号分隔）。如果传入无效值，会回退为默认三件套并给 warning。

---

## 4) 常用参数说明

### 4.1 趋势粒度（grain）

```bash
--grain {day|week|month}
```

- `day`：输出 DoD（day-over-day）
- `week`：输出 WoW（week-over-week）
- `month`：输出 MoM（month-over-month，默认）

> YoY（同比）只在 `month` 且存在“同月去年”数据点时计算；否则会给出明确 warning，不会硬算。

### 4.2 拆解维度与指标（dim / measure）

```bash
--dim <列名>
--measure <列名>
```

- 不指定时：默认使用“自动识别的第一个维度列 / 第一个数值列”。
- 指定但不存在时：会 warning，并回退到默认值（不中断）。

拆解输出包含：
- TopN by value（含 share）
- Contribution-to-change（按最近两期的变化，列出 top positive/negative contributors；当总变化为 0 会 warning）

### 4.3 时间范围（time-range）

```bash
--time-range YYYY-MM-DD..YYYY-MM-DD
```

用于覆盖默认时间范围（默认策略：若有日期列，则取 min..max；否则为“(none)”）。

### 4.4 TopN

```bash
--topn 10
```

控制 TopN 拆解输出的默认规模。

---

## 5) 输出 JSON 结构（简述）

程序会输出一份 JSON，关键字段：

- `artifacts[]`: 导出的文件列表（format/path）
- `summary`: 执行摘要（highlights/risks/actions）
- `spec`: 口径（time_range、topn、识别到的 date/number/dimension 列）
- `tables`:
  - `tables.trend[]`: 趋势表行（period + 指标列）
  - `tables.breakdowns[]`: 拆解与贡献结构
- `warnings[]`: 所有保守提示（字段识别、历史不足、截断等）
- `meta`: 便于验收的元信息（目前包含 `kpis`、`grain`）

---

## 6) 导出治理（大数据/文件大小控制）

为了避免 XLSX 过大/不可控，社区版默认：

- **只导出聚合结果**（不做 raw 明细 dump）
- 趋势表默认 **最多导出前 5000 行**
  - 超过会在 `warnings` 中提示
  - 同时在 XLSX 的 `Trend` sheet 顶部写入 NOTE，说明截断

---

## 7) 常见问题

### Q1：为什么我没有趋势/环比？

- 数据未识别到日期列（或日期解析失败）
- 历史期数不足（不足 2 期无法算 DoD/WoW/MoM；不足同月去年无法算 YoY）

这些情况都会在 `warnings` 中明确提示。

### Q2：如何把输出集成到 CI/流水线验收？

- 解析 stdout JSON
- 断言：`artifacts` 文件存在、`warnings` 可接受、`tables/meta` 的关键字段出现

---
