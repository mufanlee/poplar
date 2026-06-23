# 工具结果内联到 ASSISTANT 消息 — 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 一次 USER 消息对应一个 ASSISTANT widget，工具结果和后续 LLM 回复实时追加到同一块中。

**Architecture:** 纯渲染层修改——`_show_tool_result` 和 `_update_streaming` 操作 ChatView 中已有的 MessageWidget 的 `_msg.content`，不创建新 widget。session 数据不动。

**Tech Stack:** Python 3.12, Textual, Rich

---

## 文件变更

- 修改: `src/poplar/tui/app.py` — `_show_tool_result`、`_fetch_response`、`_update_streaming`

---

### Task 1: 修改 `_show_tool_result`——内联追加到已有 ASSISTANT widget

**文件:** `src/poplar/tui/app.py:505-510`

当前创建独立 SYSTEM widget。改为找最后一个 ASSISTANT widget 追加内容。

- [ ] **Step 1: 替换 `_show_tool_result` 实现**

将现有：

```python
    def _show_tool_result(self, name: str, content: str):
        """Show tool execution result as a system message (mount directly, no reactive)."""
        chat_view = self.query_one(ChatView)
        preview = content[:TOOL_RESULT_PREVIEW_CHARS] + "..." if len(content) > TOOL_RESULT_PREVIEW_CHARS else content
        tool_msg = Message(role=Role.SYSTEM, content=f"{t('tool_result_prefix', name=name)}\n{preview}")
        w = MessageWidget(tool_msg)
        chat_view.mount(w)
        chat_view.scroll_end(animate=False)
```

替换为：

```python
    def _show_tool_result(self, name: str, content: str):
        """Append tool result inline to the most recent assistant widget."""
        preview = content[:TOOL_RESULT_PREVIEW_CHARS] + "..." if len(content) > TOOL_RESULT_PREVIEW_CHARS else content
        tool_text = f"\n\n🔧 {name}\n  {preview}"

        chat_view = self.query_one(ChatView)
        # Find the most recent assistant widget and append tool result
        for child in reversed(chat_view.children):
            if isinstance(child, MessageWidget) and child._msg.role == Role.ASSISTANT:
                child._msg.content += tool_text
                for cw in child.query(MessageContent):
                    cw._build()
                chat_view.scroll_end(animate=False)
                return
        # Fallback: mount as temp widget
        tool_msg = Message(role=Role.SYSTEM, content=f"🔧 {name}\n  {preview}")
        chat_view.mount(MessageWidget(tool_msg))
        chat_view.scroll_end(animate=False)
```

- [ ] **Step 2: 运行测试**

```bash
cd /home/lipeng/workspace/poplar && source .venv/bin/activate && python -m pytest tests/ -q
```

预期: 125 passed

- [ ] **Step 3: 提交**

```bash
git add src/poplar/tui/app.py
git commit -m "fix: inline tool results into last assistant widget"
```

---

### Task 2: 保留 `_streaming_msg` 引用——工具调用后不清除

**文件:** `src/poplar/tui/app.py:463`

工具调用后 `self._streaming_msg = None` 会断开引用，导致下轮 LLM 回复创建新 widget。改为保留引用。

- [ ] **Step 1: 删除 `_streaming_msg = None`**

将：

```python
                self.session.add_message(assistant_msg)
                self.store.save_message(self.session.id, assistant_msg)
                self._streaming_msg = None
```

改为：

```python
                self.session.add_message(assistant_msg)
                self.store.save_message(self.session.id, assistant_msg)
                # Keep _streaming_msg reference — next turn appends to same widget
```

- [ ] **Step 2: 运行测试**

```bash
cd /home/lipeng/workspace/poplar && source .venv/bin/activate && python -m pytest tests/ -q
```

预期: 125 passed

- [ ] **Step 3: 提交**

```bash
git add src/poplar/tui/app.py
git commit -m "fix: keep _streaming_msg reference after tool calls"
```

---

### Task 3: `_update_streaming`——已有 widget 时替换内容

**文件:** `src/poplar/tui/app.py:547`

当前当 `_streaming_msg is not None` 时做 `self._streaming_msg.content = content`（替换）。工具调用后下一轮 LLM 的流式输出需要**覆盖**（不含之前内容），当前已是替换逻辑，无需修改。确认即可。

- [ ] **Step 1: 验证当前代码**

当前代码（行 547-548）：
```python
            if self._streaming_msg is not None:
                self._streaming_msg.content = content
```

这是 REPLACE 逻辑——正确的。不修改。

- [ ] **Step 2: 运行测试确认**

```bash
cd /home/lipeng/workspace/poplar && source .venv/bin/activate && python -m pytest tests/ -q
```

预期: 125 passed

---

### Task 4: 端到端验证

- [ ] **Step 1: 全量测试**

```bash
cd /home/lipeng/workspace/poplar && source .venv/bin/activate && python -m pytest tests/ -v --tb=short
```

预期: 125 passed, 2 skipped

- [ ] **Step 2: 验证导入**

```bash
cd /home/lipeng/workspace/poplar && source .venv/bin/activate && python -c "
from poplar.tui.app import PoplarApp
print('Import OK')
"
```

- [ ] **Step 3: 提交**

```bash
git add -A && git commit -m "feat: inline tool results into single assistant block"
```
