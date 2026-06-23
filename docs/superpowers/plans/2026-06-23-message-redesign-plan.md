# Poplar 消息布局重设计 — 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 去掉消息 Panel 四边框，改用左侧色条 + 角色标签。

**Architecture:** MessageWidget.__init__ 中用 `self.styles.border_left = ("thick", Color.parse("#hex"))` 设置色条——无需额外 widget，无布局问题。MessageContent 去掉 Panel，纯 Text/Markdown。CopyButton 文案 `[copy]`。

**关键点:** 之前 `border_left` 失败是因为传了 `"$accent"` 字符串（CSS 变量），`Rich Color.parse()` 只接受 hex/rgb/颜色名。

**Tech Stack:** Python 3.12, Textual, Rich

---

### Task 1: 清理当前文件残留 + 实现色条

**文件:** `src/poplar/tui/chat_view.py`

- [ ] **Step 1: 删除 MessageBar 类（99-113行），简化 MessageWidget**

替换整个 `MessageBar` + `MessageWidget` 为：

```python
from rich.color import Color


class MessageWidget(Horizontal):
    """A single chat message: [colored left bar] [content] [copy]."""

    _BAR_COLORS = {
        Role.USER: "#2ac3de",
        Role.ASSISTANT: "#9ece6a", 
        Role.TOOL: "#565f89",
    }

    def __init__(self, message: Message):
        super().__init__()
        self._msg = message
        bar_hex = self._BAR_COLORS.get(message.role, "#e0af68")
        self.styles.border_left = ("thick", Color.parse(bar_hex))

    def compose(self):
        yield MessageContent(self._msg)
        yield CopyButton(self._msg)

    DEFAULT_CSS = """
    MessageWidget {
        height: auto;
        margin: 1 0 0 0;
        padding: 0 0 0 1;
    }
    MessageContent {
        width: 1fr;
        height: auto;
    }
    """
```

删除第二个重复的 `DEFAULT_CSS` 块（如存在）。

- [ ] **Step 2: 删除未使用的 `from rich.panel import Panel`（如只用于 welcome）**

保留——welcome 页面仍使用 Panel。

- [ ] **Step 3: 运行测试**

```bash
cd /home/lipeng/workspace/poplar && source .venv/bin/activate && python -m pytest tests/ -q
```

预期: 125 passed

- [ ] **Step 4: 提交**

```bash
git add src/poplar/tui/chat_view.py
git commit -m "fix: remove MessageBar widget, use border_left with Color.parse

Replace the separate MessageBar widget (which had height issues) with
self.styles.border_left using parsed hex colors. No extra widget, no
layout dependency. Also remove duplicate DEFAULT_CSS block."
```

---

### Task 2: 确认消息内容格式

**文件:** `src/poplar/tui/chat_view.py:56-70`

当前 `_build()` 已去掉 Panel：

```python
USER:      Text(f"👤 You\n\n{msg.content}")
ASSISTANT: Markdown(msg.content)
SYSTEM:    Text(f"  {msg.content}", style="dim yellow")
TOOL:      Text(f"🔧 {name}\n  {line1}\n  ...", style="dim")
```

无需修改。运行测试确认：

- [ ] **Step 1: 运行测试**

```bash
cd /home/lipeng/workspace/poplar && source .venv/bin/activate && python -m pytest tests/ -q
```

预期: 125 passed

---

### Task 3: 端到端验证

- [ ] **Step 1: 全量测试**

```bash
cd /home/lipeng/workspace/poplar && source .venv/bin/activate && python -m pytest tests/ -v --tb=short
```

预期: 125 passed, 2 skipped

- [ ] **Step 2: 导入验证**

```bash
cd /home/lipeng/workspace/poplar && source .venv/bin/activate && python -c "
from poplar.tui.chat_view import MessageWidget
from poplar.core.session import Message, Role
w = MessageWidget(Message(role=Role.USER, content='test'))
print('OK:', type(w).__name__)
"
```

- [ ] **Step 3: 提交**

```bash
git add -A && git commit -m "feat: borderless messages — border_left color bar, no Panel"
```
