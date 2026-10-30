---
name: simple-addition
description: 接收用户输入的两个或多个数字，调用内嵌 Python 脚本计算总和，并以 JSON 格式返回结果。用户要求数字相加、求和或计算一组数字的总计时使用。
---

# Simple Addition Skill

## 1. 功能目标

接收用户提供的两个或多个数字，使用本文件中内嵌的 Python 脚本计算总和，并返回标准 JSON。

- Agent 负责从用户输入中提取数字。
- Python 脚本负责校验数字并计算总和。
- 最终结果必须来自脚本的实际执行结果。
- 不需要单独的 `.py` 文件，也不需要第三方 Python 库。

## 2. 输入格式

将用户提供的数字整理为以下 JSON 对象：

```json
{
  "numbers": [12, 25, 8.5, 4]
}
```

规则：

1. `numbers` 必须是非空数组。
2. 数组元素必须是整数或浮点数。
3. 不接受布尔值、字符串、`NaN` 或无穷大。
4. 不要擅自补充、修改或遗漏用户输入的数字。
5. 如果用户输入不明确，先询问用户，不要猜测。

## 3. 内嵌 Python 执行脚本

执行时，使用可用的 Python 执行工具运行下面的完整代码。将第 4 节中的输入 JSON 传给 `main()`。

```python
import json
import math


def add_numbers(numbers):
    """Validate a list of numbers and return their sum."""
    if not isinstance(numbers, list) or len(numbers) == 0:
        raise ValueError("numbers must be a non-empty list.")

    validated = []

    for index, value in enumerate(numbers):
        # bool is a subclass of int in Python, so reject it explicitly.
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError(
                f"numbers[{index}] must be an integer or float."
            )

        number = float(value)

        if not math.isfinite(number):
            raise ValueError(
                f"numbers[{index}] must be a finite number."
            )

        validated.append(number)

    total = math.fsum(validated)

    if not math.isfinite(total):
        raise OverflowError("The sum is outside the supported numeric range.")

    if total.is_integer():
        total = int(total)
    else:
        total = round(total, 10)

    return {
        "count": len(validated),
        "numbers": numbers,
        "sum": total
    }


def main(payload):
    try:
        if not isinstance(payload, dict):
            raise ValueError("Input must be a JSON object.")

        result = add_numbers(payload.get("numbers"))

        response = {
            "status": "success",
            "data": result,
            "error": None
        }

    except Exception as exc:
        response = {
            "status": "error",
            "data": None,
            "error": {
                "type": type(exc).__name__,
                "message": str(exc)
            }
        }

    return json.dumps(
        response,
        ensure_ascii=False,
        allow_nan=False
    )


# Example:
# print(main({"numbers": [12, 25, 8.5, 4]}))
```

## 4. 工具调用流程

1. 从用户消息中提取所有需要相加的数字。
2. 将数字整理为 `{"numbers": [...]}`。
3. 执行第 3 节中的 Python 脚本，调用 `main(payload)`。
4. 解析 `main()` 返回的 JSON 字符串。
5. 将该 JSON 作为最终回答，不要在 Agent 侧重新计算或修改结果。

如果当前环境没有可用的 Python 执行工具，必须明确说明无法实际执行；不得声称已经调用脚本。

## 5. 输出格式

成功时：

```json
{
  "status": "success",
  "data": {
    "count": 4,
    "numbers": [12, 25, 8.5, 4],
    "sum": 49.5
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
    "type": "ValueError",
    "message": "numbers must be a non-empty list."
  }
}
```

## 6. 最终回答要求

- 只输出合法 JSON。
- 不使用 Markdown 代码块包裹最终 JSON。
- 不添加 JSON 之外的解释文字。
- 不添加注释或尾随逗号。
- 所有计算结果必须来自 Python 脚本的实际执行结果。
