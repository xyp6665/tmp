# Smart Task Planner Skill

自然语言任务规划与管理 Skill。用户输入任务描述，Agent 拆解任务并调用独立 Python 函数；Python 函数负责计算时间、持久化任务、检查冲突和统计进度。

## 项目结构

```text
smart-task-planner/
├── SKILL.md
├── README.md
├── scripts/
│   └── task_planner.py
├── examples/
│   └── test_prompt.md
├── tests/
│   └── test_task_planner.py
└── data/
    └── .gitkeep
```

## 环境要求

- Python 3.9+
- 仅使用 Python 标准库
- 不需要 Docker、网络或文件上传

## 可调用函数

```python
from scripts.task_planner import (
    create_task,
    calculate_deadline,
    check_conflicts,
    summarize_tasks,
    list_tasks,
    update_task,
)
```

## 快速示例

```python
from scripts.task_planner import (
    calculate_deadline,
    create_task,
    check_conflicts,
    summarize_tasks,
)

# 计算计划结束时间
end = calculate_deadline(
    start_at="2026-11-02T09:00:00",
    duration=2,
    unit="hours",
)

# 创建任务并保存
created = create_task(
    title="收集市场数据",
    priority="high",
    start_at="2026-11-02T09:00:00",
    end_at=end["deadline"],
    deadline="2026-11-06T18:00:00",
    estimated_hours=2,
)

# 检查冲突、统计进度
conflicts = check_conflicts()
summary = summarize_tasks()
```

## CLI 示例

```bash
python scripts/task_planner.py \
  --action calculate_deadline \
  --input-json '{"start_at":"2026-11-02T09:00:00","duration":2,"unit":"hours"}'
```

创建任务：

```bash
python scripts/task_planner.py \
  --action create_task \
  --input-json '{"title":"收集市场数据","priority":"high","start_at":"2026-11-02T09:00:00","estimated_hours":2,"deadline":"2026-11-06T18:00:00"}'
```

指定任务库：

```bash
python scripts/task_planner.py \
  --action summarize_tasks \
  --store ./data/my_tasks.json
```

## 数据持久化

默认存储位置为当前工作目录下的 `data/tasks.json`。也可以设置环境变量 `TASK_PLANNER_STORE`，或在函数参数中传入 `store_path`。

每条任务保存 task_id、标题、描述、优先级、开始/结束时间、截止时间、预计耗时、状态、依赖、标签、创建时间和完成时间。

建议测试时使用独立的 `store_path`，避免测试数据污染正式任务库。

## 运行测试

```bash
python -m unittest discover -s tests -v
```

## 重要约定

- `calculate_deadline()` 只计算时间，不保存任务。
- `create_task()` 会持久化任务；提供 start_at 和 estimated_hours 时，可自动推算 end_at。
- `check_conflicts()` 只检查有 start_at 和 end_at 的活动任务；不会自动调整日程。
- `summarize_tasks()` 统计所有已保存任务。
- 日期时间使用 ISO 8601；同一任务库不要混用带时区与不带时区的时间。
- 工具返回的 task_id 必须原样用于 dependencies。
- 任务完成状态只有在用户明确说明已完成或确认后才设置为 done。
