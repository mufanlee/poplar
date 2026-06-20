"""Context window management — smart summarization for long conversations."""

import logging
from typing import List, Tuple, Callable
from poplar.core.session import Session, Message, Role

logger = logging.getLogger(__name__)

# Rough token estimation: 1 token ≈ 4 chars for English, ~2 chars for Chinese
# Use conservative estimate: chars / 4
def estimate_tokens(text: str) -> int:
    """Rough token estimation based on character count."""
    return max(1, len(text) // 4)


def messages_token_count(messages: List[Message]) -> int:
    """Estimate total tokens for a list of messages."""
    return sum(estimate_tokens(m.content) for m in messages)


# Maximum chars per summary message (to avoid eating up the context with summary text)
MAX_SUMMARY_CHARS = 2000


class ContextManager:
    """Manages conversation context through LLM-based summarization.

    When the conversation approaches the token limit, earlier messages are
    compressed into a concise summary, preserving the most recent exchanges
    intact for continuity.
    """

    def __init__(self, max_tokens: int = 32768,
                 auto_compress_at: float = 0.7,
                 keep_recent_exchanges: int = 3):
        self.max_tokens = max_tokens
        self.auto_compress_at = auto_compress_at
        self.keep_recent_exchanges = keep_recent_exchanges

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def should_compress(self, total_tokens: int) -> bool:
        """Check whether the conversation has exceeded the compression threshold."""
        threshold = int(self.max_tokens * self.auto_compress_at)
        return total_tokens >= threshold

    def get_summarizable_messages(self, messages: List[Message]
                                  ) -> Tuple[List[Message], List[Message]]:
        """Split messages into (old_msgs_to_summarize, recent_msgs_to_keep).

        The last *keep_recent_exchanges* user/assistant exchanges are preserved
        intact. Returns ([], messages) if there are too few messages to summarize.
        """
        # Count total user messages
        total_user_msgs = sum(1 for m in messages if m.role == Role.USER)
        if total_user_msgs <= self.keep_recent_exchanges:
            return [], messages

        # Find the split point: count back *keep_recent_exchanges* user messages.
        # The first exchange to KEEP starts at the (keep_recent)th user from the end.
        user_count = 0
        split_idx = len(messages)

        for i in range(len(messages) - 1, -1, -1):
            if messages[i].role == Role.USER:
                user_count += 1
                if user_count == self.keep_recent_exchanges:
                    # This user message is the first exchange to keep
                    split_idx = i
                    break

        old_msgs = messages[:split_idx]
        recent_msgs = messages[split_idx:]

        # Don't include messages that are already summaries
        old_msgs = [m for m in old_msgs if not (
            m.role == Role.SYSTEM and (m.content.startswith("[Summary") or m.content.startswith("*Summary"))
        )]

        return old_msgs, recent_msgs

    def build_summary_prompt(self, messages: List[Message]) -> str:
        """Build the prompt sent to the LLM for summarization."""
        conversation_text = "\n".join(
            f"[{m.role.value}]\n{m.content}" for m in messages
        )
        return (
            "Please summarize the following conversation concisely.\n"
            "Keep all important facts, decisions, code changes, and user preferences.\n"
            "Aim for 200-400 tokens. The summary will be used as context for "
            "the continuing conversation.\n\n"
            f"Conversation:\n{conversation_text}"
        )

    def summarize(self, summarizer_fn: Callable[[str], str],
                  old_messages: List[Message]) -> str:
        """Call the LLM to generate a summary.

        Args:
            summarizer_fn: A function that takes a prompt string and returns
                          the summary text (synchronous, blocking).
            old_messages: Messages to summarize.

        Returns:
            The summary text.
        """
        prompt = self.build_summary_prompt(old_messages)
        logger.info("Summarizing %d messages...", len(old_messages))
        summary = summarizer_fn(prompt)
        summary = summary.strip()
        # Truncate if too long to avoid eating tokens
        if len(summary) > MAX_SUMMARY_CHARS:
            summary = summary[:MAX_SUMMARY_CHARS] + "\n... (summary truncated)"
        logger.info("Summary generated (%d chars)", len(summary))
        return summary

    @staticmethod
    def format_summary_message(summary_text: str) -> Message:
        """Wrap summary text into an assistant message."""
        return Message(role=Role.ASSISTANT,
                       content=f"*Summary of earlier conversation*\n\n{summary_text}")

    def apply_compression(self, session: Session, summary_text: str,
                          recent_messages: List[Message]):
        """Replace old messages with a summary message in the session.

        The session.messages list is modified in-place.
        """
        summary_msg = self.format_summary_message(summary_text)
        session.messages = [summary_msg] + recent_messages
        logger.info("Compression applied: %d messages → 1 summary + %d recent",
                     len(recent_messages) + 1, len(recent_messages))

    @staticmethod
    def get_cumulative_token_count(session: Session) -> int:
        """Get the estimated token count for all messages in a session."""
        messages = session.messages or []
        meaningful = [m for m in messages
                      if m.role != Role.SYSTEM or m.content.startswith("[Summary") or m.content.startswith("*Summary")]
        return messages_token_count(meaningful)
