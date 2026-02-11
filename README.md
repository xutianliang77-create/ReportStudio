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
  --topn 10
```

输出为一个 JSON：
- `artifacts`: 生成文件列表
- `summary`: 执行摘要（亮点/风险/建议）
- `spec`: 数据口径（时间范围/字段映射/默认参数）
- `warnings`: 字段自动识别、默认参数等警告

> 社区版默认只读，不做外网请求，不写数据库。
