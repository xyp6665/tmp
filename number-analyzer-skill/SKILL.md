---
name: number-analyzer
description: 接收用户输入的一组数字，调用 Python 工具进行描述性统计、分位数计算、离散程度分析、异常值检测、正负数分类和重复值识别，并以严格 JSON 格式返回结果。
---

# Number Analyzer Skill

## 1. 目标

当用户输入一组数字并要求统计、比较、分析或检测异常值时，使用本 Skill。

Agent 负责：
- 从自然语言中准确提取数字及其顺序。
- 判断用户是否提供了足够的数字。
- 调用 `scripts/number_analyzer.py` 中的 `analyze_numbers()`。
- 将工具真实返回的 JSON 结果直接整理为最终 JSON。

Python 工具负责：
- 参数校验。
- 基础统计。
- 分位数和离散程度计算。
- IQR 异常值检测。
- 正数、负数、零、整数和重复值统计。

不需要网络、文件上传或第三方 Python 依赖。

## 2. 工具函数

工具脚本：`scripts/number_analyzer.py`

核心函数：

```python
analyze_numbers(numbers: list[int | float]) -> dict
```

输入要求：
- `numbers` 必须是非空数字列表。
- 至少包含 1 个数字。
- 不接受布尔值、字符串、`NaN`、正无穷或负无穷。
- 保留用户输入顺序，但统计指标不依赖输入顺序。
- 不要擅自从文本中猜测或补充数字。

## 3. 分析项目

### 基础统计
- `count`：数字数量
- `sum`：总和
- `mean`：算术平均数
- `median`：中位数
- `min`：最小值
- `max`：最大值
- `range`：极差

### 离散程度
- `variance_population`：总体方差
- `std_dev_population`：总体标准差
- `variance_sample`：样本方差；只有至少 2 个数字时计算，否则为 null
- `std_dev_sample`：样本标准差；只有至少 2 个数字时计算，否则为 null

### 分位数
- `q1`：第一四分位数
- `q2`：第二四分位数，即中位数
- `q3`：第三四分位数
- `iqr`：四分位距，等于 q3 - q1

分位数采用线性插值法，位置为 `(n - 1) * p`。

### 异常值检测
采用 IQR 规则：
- 下界 = Q1 - 1.5 × IQR
- 上界 = Q3 + 1.5 × IQR
- 小于下界或大于上界的数字标记为异常值。
- 少于 4 个数字时，返回 `insufficient_data`，不作异常值判断。

注意：IQR 检测只表示统计意义上的潜在异常，不代表数据一定错误。

### 数字分类
- 正数数量
- 负数数量
- 零的数量
- 整数数量

### 重复值
返回重复出现的数字及各自出现次数，不重复列出相同数值。

## 4. 调用规则

1. 从用户消息中提取数字，按原顺序构造 `numbers` 列表。
2. 如果用户没有提供数字，询问用户输入数字。
3. 如果数字格式不明确或包含无法解析的值，先澄清，不要静默丢弃。
4. 调用 `analyze_numbers(numbers)`。
5. 以工具返回值作为唯一统计依据，不在 Agent 侧重新计算或修改结果。
6. 不要把统计异常值描述成确定的数据错误。
7. 如果工具返回 `status=error`，如实返回错误信息。

## 5. 最终输出格式

用户要求 JSON 输出，因此最终回答必须是合法 JSON：
- 不使用 Markdown 代码块。
- 不添加 JSON 之外的解释文字。
- 不添加注释或尾随逗号。
- 成功时遵循以下结构：

```json
{
  "status": "success",
  "data": {
    "count": 10,
    "sum": 230,
    "mean": 23,
    "median": 15,
    "min": 10,
    "max": 100,
    "range": 90,
    "dispersion": {},
    "quartiles": {},
    "outlier_detection": {},
    "number_categories": {},
    "duplicates": []
  },
  "error": null
}
```

以上数值仅为结构示意。实际输出必须使用工具真实返回的全部字段和值，不得复制示例数值。

失败时遵循：

```json
{
  "status": "error",
  "data": null,
  "error": {
    "type": "ValueError",
    "message": "错误说明"
  }
}
```
