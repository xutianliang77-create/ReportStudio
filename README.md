# ReportStudio (Community)

> 从结构化数据到可汇报材料的最后一公里。

## Install (dev)

```bash
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -e '.[dev]'
```

## Usage

```bash
reportstudio --file ./data.xlsx --prompt "生成月报" \
  --out-dir ./artifacts \
  --formats xlsx,pdf,pptx \
  --topn 10 \
  --grain month \
  --dim region \
  --measure revenue
```

常用参数：
- `--grain {day|week|month}`：趋势聚合粒度（默认 month）
- `--dim <列名>`：指定 TopN 拆解维度（默认自动选第一个维度列）
- `--measure <列名>`：指定拆解指标（默认自动选第一个数值列）
- `--time-range YYYY-MM-DD..YYYY-MM-DD`：覆盖默认时间范围

输出为一个 JSON：
- `artifacts`: 生成文件列表（默认 xlsx+pdf+pptx）
- `summary`: 执行摘要（亮点/风险/建议）
- `spec`: 数据口径（时间范围/字段映射/默认参数）
- `tables`: 可复用的表格数据（`trend` / `breakdowns`）
- `warnings`: 字段自动识别、历史不足、截断导出等警告
- `meta`: 运行元信息（包含 `kpis`、`grain`，用于可测试/可验收）

导出治理（避免文件过大）：
- XLSX 默认只导出聚合结果，不做 raw 明细 dump
- 趋势表默认最多导出前 5000 行（超出会在 warnings 与 Trend sheet NOTE 中提示截断）

> 社区版默认只读，不做外网请求，不写数据库。
