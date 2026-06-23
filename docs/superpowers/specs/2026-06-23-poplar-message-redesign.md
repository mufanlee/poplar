# Poplar 消息布局重设计

> 目标：去掉消息四边 Panel 边框，改用左侧色条 + 角色标签，提升终端空间利用率和视觉简洁度。

**架构：** 修改 `chat_view.py` 中 `MessageContent._build()` 的 Rich 渲染逻辑，将 `Panel` 替换为 `Table`/`Columns` 组合实现色条布局。CSS 调整 `MessageWidget` 间距。

**参考：** Claude Code 无边框纯文本流 + 表格内联风格。

---

## 设计

### 消息渲染

```
│ 👤 You
│ 用户消息内容，纯文本
│
│ 🔧 list_directory
│   .venv/  src/  tests/  docs/
│
│ 🤖 Assistant                                    [copy]
│ 回复内容，Markdown 渲染
│ 支持代码块、列表、表格
```

- 左侧：1 列宽色条（`│` 字符），颜色按角色区分
- 色条右侧：角色标签 + 消息内容
- Copy 按钮保留在右上角

### 角色颜色

| 角色 | 色条颜色 | 标签 | 内容样式 |
|---|---|---|---|
| USER | cyan | `👤 You` | 纯文本 |
| ASSISTANT | green | `🤖 Assistant` | Markdown 渲染 |
| TOOL | dim | `🔧 {name}` | dim 样式，截断显示 |
| SYSTEM | 无色条 | 无标签 | dim yellow（当前保持一致） |

### CSS 调整

- `MessageWidget` 增加 `margin-top: 1`，消息之间呼吸感
- `MessageContent` 保持 `width: 1fr`
- 删除当前 `Panel` 导入（如不再使用）

### 不修改的部分

- ChatView 外框保持 `border: round $secondary`
- Welcome 页面保持不变
- Composer / StatusFooter 不变
- CopyButton 功能不变，文案改为 `[copy]`

### 实现要点

`MessageContent._build()` 用 Rich 的 `Table` 或 `Columns` 实现左色条：

```python
from rich.table import Table
from rich.columns import Columns

# 构建一个无边框的 table，第一列 1 字符宽为色条
table = Table.grid(expand=True)
table.add_column("bar", width=1, style=color)
table.add_column("content")
table.add_row("│", f"{label}\n{markdown_or_text}")
```

或者直接用 `Text` + 缩进拼接（更简洁）：

```python
content = Text()
content.append("│ ", style=color)
content.append(f"{label}\n", style="bold")
content.append(body)
```

---

## 测试

现有 125 测试应全部通过。`chat_view.py` 的修改不影响业务逻辑，仅改变渲染方式。

## 非目标

- 不修改消息数据模型
- 不修改 Agent 循环或工具执行
- 不添加新功能
