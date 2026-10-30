---
name: script-call-test
description: 用于测试 Agent 对 Python 脚本的调用、JSON 参数传递、多脚本串联、文件读写和异常返回。用户提出测试脚本调用、验证沙箱执行或检查工具执行链路时使用。
---

# Script Call Test

## 目标

通过三个轻量级 Python 脚本，验证以下执行链路：

1. Agent 能否识别并调用本 Skill。
2. Agent 能否向脚本传递 JSON 参数。
3. 脚本能否在宿主提供的隔离执行环境（例如 Docker）中运行。
4. Agent 能否解析脚本的 JSON 输出，并将上一步结果传给下一步。
5. 文件写入、读取和目录清单功能是否正常。
6. 脚本失败时，错误状态能否返回 Agent。

本 Skill 仅使用 Python 标准库，不需要安装第三方依赖。

## 执行前检查

- 找到本 Skill 的实际根目录，确认 `scripts/` 下存在目标脚本。
- 必须通过宿主环境明确提供的、经过授权的 Python 或命令执行工具运行脚本。
- 不要假设宿主工具的名称，也不要虚构工具调用结果。
- 如果当前 Agent 没有可用的脚本执行工具，应明确告诉用户需要接入执行工具，并给出可复制的命令；不得声称脚本已经执行。
- 如果执行环境是 Docker，确认 Skill 目录或脚本文件已挂载到容器内，并使用容器内路径。
- 不执行用户提供的任意 Shell 命令；本 Skill 只调用自身 `scripts/` 目录中的三个固定脚本。

## 统一调用协议

每个脚本都接受一个 JSON 对象，并在标准输出（stdout）返回一个 JSON 对象。

成功格式：

```json
{
  "status": "success",
  "script": "脚本名称",
  "data": {},
  "error": null
}
```

失败格式：

```json
{
  "status": "error",
  "script": "脚本名称",
  "data": null,
  "error": {
    "type": "异常类型",
    "message": "错误说明"
  }
}
```

调用方式：

```bash
python <skill_root>/scripts/<script_name>.py --input-file <json_file>
```

也可以通过标准输入传递 JSON。不要把 JSON 参数拼接进未经转义的 Shell 命令。每次调用后：

1. 检查进程退出码。
2. 解析 stdout 中的 JSON。
3. 检查 `status` 是否为 `success`。
4. 只有上一步成功时，才继续后续步骤。
5. 将脚本返回的 `data` 作为下一步的输入依据，不要自行编造结果。

## 可用脚本

### 1. `echo_params.py`：参数回显

用途：验证字符串、数字、布尔值、列表、字典等 JSON 参数能否完整传递。

输入示例：

```json
{
  "request_id": "smoke-001",
  "name": "demo",
  "numbers": [1, 2, 3],
  "enabled": true,
  "metadata": {
    "source": "agent",
    "tags": ["test", "docker"]
  }
}
```

执行：

```bash
python scripts/echo_params.py --input-file examples/echo_input.json
```

预期：`data.received` 与输入对象完全一致，并返回字段类型信息。

### 2. `calculate.py`：计算器

用途：验证脚本执行、参数校验和异常返回。

支持操作：`add`、`subtract`、`multiply`、`divide`。

输入示例：

```json
{
  "operation": "multiply",
  "values": [128, 36]
}
```

执行：

```bash
python scripts/calculate.py --input-file examples/calculate_input.json
```

预期：计算结果为 `4608`。

限制：至少提供两个有限数值；除法过程中不能除以零。

### 3. `file_operation.py`：文件操作

用途：验证沙箱内的文件创建、读取和目录列举。

支持操作：

- `write`：写入 UTF-8 文本文件。
- `read`：读取 UTF-8 文本文件。
- `list`：列出工作目录某一层的文件和子目录。

输入示例：

```json
{
  "action": "write",
  "workspace": "./output",
  "filename": "test.txt",
  "content": "script call works"
}
```

执行：

```bash
python scripts/file_operation.py --input-file examples/file_write_input.json
```

安全约束：

- 文件路径必须是工作目录内的相对路径。
- 禁止绝对路径和 `..` 路径穿越。
- 解析符号链接后的目标路径也必须位于工作目录内。
- 脚本不会删除文件，也不会访问工作目录以外的文件。

## 推荐端到端测试流程

用户可以说：“运行一次完整的脚本调用测试。”

按以下顺序分别调用三个脚本：

### Step 1：测试参数传递

调用 `echo_params.py`，输入：

```json
{
  "request_id": "agent-docker-smoke-test",
  "text": "hello",
  "number": 42,
  "enabled": true,
  "items": [1, 2, 3],
  "metadata": {
    "source": "script-call-test",
    "environment": "docker"
  }
}
```

验证 `data.received` 是否与输入一致。

### Step 2：测试计算脚本

调用 `calculate.py`，输入：

```json
{
  "operation": "multiply",
  "values": [128, 36]
}
```

验证 `data.result` 是否等于 `4608`。

### Step 3：测试脚本结果落盘

将 Step 1 和 Step 2 的实际返回结果整理为 JSON 字符串，作为 `file_operation.py` 的 `content`，执行 `write`，文件名使用 `smoke-test-result.json`，工作目录使用 `./output`。

注意：写入内容必须来自前两步的真实执行结果，不得虚构。

### Step 4：读取并验证文件

调用 `file_operation.py`，输入：

```json
{
  "action": "read",
  "workspace": "./output",
  "filename": "smoke-test-result.json"
}
```

验证读取内容与写入内容一致。

### Step 5：列出文件

调用 `file_operation.py`，输入：

```json
{
  "action": "list",
  "workspace": "./output",
  "directory": "."
}
```

确认清单中存在 `smoke-test-result.json`。

### Step 6：测试异常处理

调用 `calculate.py`，输入：

```json
{
  "operation": "divide",
  "values": [10, 0]
}
```

预期：脚本返回非零退出码，stdout 中仍包含合法 JSON，`status` 为 `error`，错误类型和信息能够被 Agent 读取。

再调用 `file_operation.py`，尝试读取 `../outside.txt`，预期被路径安全校验拒绝。

## 最终报告要求

测试结束后，用简洁表格汇总：

| 测试项 | 结果 | 说明 |
|---|---|---|
| Skill 识别 | 成功/失败 | 是否正确进入本 Skill |
| 参数传递 | 成功/失败 | JSON 是否完整 |
| Python 执行 | 成功/失败 | 脚本是否实际运行 |
| 多步调用 | 成功/失败 | 是否使用上一步真实输出 |
| 文件写入 | 成功/失败 | 是否成功创建文件 |
| 文件读取 | 成功/失败 | 内容是否一致 |
| 异常返回 | 成功/失败 | 是否返回结构化错误 |
| Docker 隔离 | 已验证/未验证 | 只有确认执行发生在 Docker 内才可标记已验证 |

必须区分“脚本运行成功”和“Docker 隔离已验证”。如果没有容器侧证据，不得将 Docker 隔离标记为成功。
