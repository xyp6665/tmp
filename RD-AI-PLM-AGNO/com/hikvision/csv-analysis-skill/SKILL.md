---
name: csv-analysis
description: 分析用户提供的 CSV 文件，完成数据概况、缺失值、重复记录、数值统计、分类分布、日期范围和分组汇总。用户要求统计、检查、汇总或分析 CSV/表格数据时使用。
---

# CSV Analysis Skill

## 目标

读取用户指定的 CSV 文件，调用 `scripts/csv_analyzer.py` 中的 `analyze_csv()` 工具函数，生成结构化分析结果。根据用户需要，可将报告保存为 JSON 文件。

## 工具位置

- Python 脚本：`scripts/csv_analyzer.py`
- 对外工具函数：`analyze_csv(input_path, group_by=None, metric=None, top_n=10, output_path=None)`
- CLI 入口：`python scripts/csv_analyzer.py --input <csv_path>`

该脚本仅依赖 Python 标准库，无需安装 pandas 或其他第三方库。

## 何时使用

适用于：
- 统计 CSV 文件有多少行、多少列。
- 检查缺失值和完全重复记录。
- 计算数值字段的总和、均值、中位数、最小值、最大值和标准差。
- 查看分类字段的类别数量和高频类别。
- 识别日期字段的日期范围。
- 按地区、产品、渠道等字段分组汇总指标。
- 将分析结果保存为 JSON 报告。

## 执行规则

1. 确认用户提供的 CSV 文件路径；如果当前没有文件，询问用户上传文件或提供可访问路径。
2. 调用 `scripts/csv_analyzer.py`，不要在 Agent 内手工模拟统计结果。
3. 默认自动选择分组字段和指标：优先使用 `region` 作为分组字段、`sales_amount` 作为指标；如果不存在，则从可用字段中选择合适字段。
4. 用户明确指定 `group_by` 或 `metric` 时，必须使用用户指定的字段；字段不存在或指标不是数值列时，说明原因，不要擅自替换。
5. 将脚本返回的 JSON 作为事实来源。不得编造行数、统计值或分组结果。
6. 如果用户要求保存报告，传入 `output_path`，并确认工具执行成功后再提供文件路径。
7. 区分“脚本成功执行”和“数据本身没有质量问题”。存在缺失值或重复记录时，仍可能是成功完成分析。

## 调用参数

```json
{
  "input_path": "examples/sample_sales.csv",
  "group_by": "region",
  "metric": "sales_amount",
  "top_n": 5,
  "output_path": "output/analysis_report.json"
}
```

参数说明：

| 参数 | 必填 | 说明 |
|---|---|---|
| `input_path` | 是 | CSV 文件路径 |
| `group_by` | 否 | 分组字段；不传则自动选择 |
| `metric` | 否 | 数值汇总字段；不传则自动选择 |
| `top_n` | 否 | 分类字段展示的高频类别数量，默认 10 |
| `output_path` | 否 | JSON 报告保存路径 |

## CLI 调用示例

```bash
python scripts/csv_analyzer.py \
  --input examples/sample_sales.csv \
  --group-by region \
  --metric sales_amount \
  --top-n 5 \
  --output output/analysis_report.json
```

也可以只输出到 stdout：

```bash
python scripts/csv_analyzer.py --input examples/sample_sales.csv
```

## 返回结构

成功时：

```json
{
  "status": "success",
  "data": {
    "file": "sample_sales.csv",
    "overview": {},
    "missing_values": [],
    "duplicate_rows": {},
    "numeric_summary": {},
    "categorical_summary": {},
    "date_summary": {},
    "grouped_summary": {}
  },
  "error": null
}
```

失败时：

```json
{
  "status": "error",
  "data": null,
  "error": {
    "type": "FileNotFoundError",
    "message": "..."
  }
}
```

## 面向用户的结果呈现

分析完成后，优先用简洁中文总结：

1. 数据规模：行数、列数。
2. 数据质量：缺失值较多的字段、完全重复记录数。
3. 核心数值：主要数值字段的均值、总和、范围。
4. 分类洞察：主要类别及其记录数。
5. 分组结果：按指定维度汇总指标，列出排名靠前的组别。
6. 日期范围：数据覆盖的起止日期（若识别到日期字段）。
7. 文件输出：仅当报告确实成功写入时，告知保存路径。

不要把相关性、因果关系或业务原因从描述性统计中直接推断出来。对于缺失值和重复记录，指出其可能影响分析，但不要自行删除或修改原始 CSV。
