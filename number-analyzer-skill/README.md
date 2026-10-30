# Number Analyzer Skill

接收一组数字，调用独立 Python 函数完成统计分析和 IQR 潜在异常值检测，最终输出严格 JSON。

## 目录结构

```text
number-analyzer-skill/
├── SKILL.md
├── README.md
├── scripts/
│   └── number_analyzer.py
├── examples/
│   └── test_prompt.md
└── tests/
    └── test_number_analyzer.py
```

## 环境要求

- Python 3.10+
- 仅使用标准库，无需安装第三方依赖
- 不需要文件上传、网络或 Docker

## Python 函数调用

```python
from scripts.number_analyzer import analyze_numbers

result = analyze_numbers([12, 15, 14, 10, 18, 100, 16, 13, 15, 17])
print(result)
```

## CLI 调用

```bash
python scripts/number_analyzer.py \
  --input-json '{"numbers":[12,15,14,10,18,100,16,13,15,17]}'
```

或通过标准输入：

```bash
echo '{"numbers":[1,2,3,4,5]}' | python scripts/number_analyzer.py
```

## 测试

```bash
python -m unittest discover -s tests -v
```

## 统计说明

- 总体方差/标准差以全部输入数字为总体计算。
- 样本方差/标准差使用 n-1 作为分母；只有 n≥2 时计算。
- 四分位数使用线性插值法，位置为 `(n - 1) * p`。
- IQR 异常值检测使用 1.5 × IQR fences；少于 4 个数字时不进行检测。
- 异常值仅表示潜在统计异常，不代表数据错误。
- 所有浮点数结果四舍五入至 6 位小数。
