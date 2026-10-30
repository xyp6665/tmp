# CSV Analysis Skill

一个通过独立 Python 脚本分析 CSV 文件的 Skill 示例。

## 目录

```text
csv-analysis-skill/
├── SKILL.md
├── README.md
├── scripts/
│   └── csv_analyzer.py
├── examples/
│   └── sample_sales.csv
├── tests/
│   └── test_csv_analyzer.py
└── output/
```

## 环境要求

- Python 3.9+
- 仅使用 Python 标准库，无需 `pip install`

## 快速运行

在项目根目录执行：

```bash
python scripts/csv_analyzer.py --input examples/sample_sales.csv
```

指定分组字段和指标：

```bash
python scripts/csv_analyzer.py \
  --input examples/sample_sales.csv \
  --group-by region \
  --metric sales_amount \
  --top-n 5
```

保存 JSON 报告：

```bash
python scripts/csv_analyzer.py \
  --input examples/sample_sales.csv \
  --group-by region \
  --metric sales_amount \
  --output output/analysis_report.json
```

## 独立工具函数

` scripts/csv_analyzer.py ` 暴露以下函数：

```python
from scripts.csv_analyzer import analyze_csv

result = analyze_csv(
    input_path="examples/sample_sales.csv",
    group_by="region",
    metric="sales_amount",
    top_n=5,
    output_path="output/analysis_report.json",
)
```

如果你的执行模块是通过脚本隔离执行，可直接运行 CLI；如果 Agno 工具层支持 Python 函数注册，也可以导入 `analyze_csv` 并在工具包装函数中调用它。

## 测试

```bash
python -m unittest discover -s tests -v
```

## 分析范围

- CSV 行数、列数、字段名
- 每列缺失数量和比例
- 完全重复行数量
- 数值列：计数、总和、均值、中位数、标准差、最小值、最大值
- 分类列：类别数和 Top N
- 日期列：最早日期、最晚日期
- 分组指标：记录数、指标有效值数量、总和、均值

## 说明

- 原始 CSV 不会被修改。
- 空字符串按缺失值统计。
- 名称以 `_id` 结尾的字段按标识符处理，不纳入数值统计和普通分类 Top N。
- 脚本会尝试识别逗号、分号、制表符和竖线分隔的 CSV。
- 统计结果是描述性分析，不自动推断因果关系。
