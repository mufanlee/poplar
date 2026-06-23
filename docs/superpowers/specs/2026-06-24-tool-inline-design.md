# 工具结果内联到 ASSISTANT 消息

> 目标：一次 USER 消息对应一个 ASSISTANT 块，工具结果和后续 LLM 回复都在同一块中实时追加显示。

**架构：** 纯渲染层修改。session 数据不动（API 调用不受影响），只改 widget 的 `_msg.content` 和 `_build()` 重渲染。

**参考：** Claude Code——工具调用和结果作为 ASSISTANT 回复的一部分内联展示。

---

## 设计

### 流程

```
USER 发送 "列出文件"
  │
  ▼
ASSISTANT widget 创建（_update_streaming）  →  "> 🤖 Assistant\nCalled tool: list_directory"
  │
  ▼ 工具执行
_show_tool_result 追加到同一 widget       →  "...\n\n🔧 list_directory\n  src/ tests/"
  │
  ▼ LLM 下一轮回复
_update_streaming 继续写同一 widget       →  "...\n\n目录包含 src、tests 两个文件夹"
  │
  ▼ _finalize_streaming
widget 成为最终 ASSISTANT 块，存入 session
```

### 关键修改

1. **`_show_tool_result`**：找 ChatView 中最后一个 `MessageWidget(ASSISTANT)`，追加工具文本到 `._msg.content`，调 `_build()` 重渲染。不创建新 widget。

2. **`_update_streaming`**：当 `_streaming_msg is not None` 时，REPLACE 内容（不追加）。新轮 LLM 的流式回复覆盖已有的 `_streaming_msg.content`。

3. **`_fetch_response`**：工具调用后**不**设 `_streaming_msg = None`，保留引用让下一轮的流式输出继续写同一 widget。

4. **session 数据不动**：`self.session.messages` 中 ASSISTANT(tool_calls) 和 TOOL 消息保持不变——仅用于 API 调用。display widget 是副本。

### 不修改

- `chat_view.py` `_build()` / `_rebuild()` 不变
- `core/session.py` 不变
- `core/agent_loop.py` 不变
- 不调 `save_message` 对已持久化的消息做二次写入

## 测试

125 现有测试全部通过。手动验证：发一条触发工具的请求，观察只有一个 ASSISTANT 块。
