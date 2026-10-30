# script-call-test

一个用于测试 Agent → Skill → Python 脚本 → Docker/执行工具 → Agent 返回链路的最小 Skill。

## 特点

- Python 标准库实现，无第三方依赖。
- 统一 JSON 输入、JSON 输出。
- 三个脚本：参数回显、计算、文件操作。
- 结构化错误返回，方便 Agent 解析。
- 文件操作限制在指定 workspace 内。
- 附带单元测试和示例输入。

## 目录

```text
script-call-test/
├── SKILL.md
├── README.md
├── scripts/
│   ├── common.py
│   ├── echo_params.py
│   ├── calculate.py
│   └── file_operation.py
├── examples/
│   ├── echo_input.json
│   ├── calculate_input.json
│   ├── file_write_input.json
│   ├── file_read_input.json
│   └── file_list_input.json
└── tests/
    └── test_scripts.py
```

## 环境要求

- Python 3.9+
- 无第三方依赖

## 快速运行

在项目根目录执行：

```bash
python scripts/echo_params.py --input-file examples/echo_input.json
python scripts/calculate.py --input-file examples/calculate_input.json
python scripts/file_operation.py --input-file examples/file_write_input.json
python scripts/file_operation.py --input-file examples/file_read_input.json
python scripts/file_operation.py --input-file examples/file_list_input.json
```

也可以通过标准输入传入 JSON：

```bash
echo '{"operation":"multiply","values":[128,36]}' | python scripts/calculate.py
```

## 运行测试

```bash
python -m unittest discover -s tests -v
```

## 脚本输入输出协议

所有脚本均返回：

```json
{
  "status": "success",
  "script": "calculate",
  "data": {
    "operation": "multiply",
    "values": [128, 36],
    "result": 4608
  },
  "error": null
}
```

失败时返回：

```json
{
  "status": "error",
  "script": "calculate",
  "data": null,
  "error": {
    "type": "ValueError",
    "message": "..."
  }
}
```

错误结果写入 stdout 的 JSON，进程退出码为 1。这样执行工具既能读取结构化错误，也能通过退出码判断执行是否成功。

## 接入 Agno / Docker 时的注意事项

`SKILL.md` 负责告诉 Agent 何时调用哪个脚本、传什么参数、如何判断结果；它本身不会自动获得 Python 或 Docker 执行能力。

宿主需要提供一个已授权的脚本执行工具，并确保：

1. Skill 文件和 `scripts/` 目录已挂载到执行容器。
2. 工具能够在容器内运行 `python <script_path>`。
3. 工具能传递 stdin 或创建临时 JSON 输入文件。
4. 工具能返回 stdout、stderr 和退出码。
5. 输出目录位于容器可写挂载目录。

建议工具接口至少包含：

```text
script_path: string
input_json: object
timeout_seconds: integer
```

工具返回：

```json
{
  "exit_code": 0,
  "stdout": "{\"status\":\"success\", ...}",
  "stderr": ""
}
```

上面是建议的接口契约，不代表你的 Agno 项目已经注册了这个工具。需要根据你现有的 Docker 执行模块接入。

## 安全说明

- `file_operation.py` 只允许在 workspace 内读写。
- 不支持删除文件。
- 不调用外部网络。
- 不执行用户输入的 Shell 命令。
- 不要把不可信输入直接拼接到 Shell 命令字符串中。
