"""Session performance statistics collector."""

import time
from dataclasses import dataclass, field


@dataclass
class StatsCollector:
    """Collects session-level performance metrics."""

    api_calls: int = 0
    api_total_latency_ms: float = 0.0
    api_errors: int = 0
    tokens_prompt: int = 0
    tokens_completion: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    tool_calls: int = 0
    messages_sent: int = 0
    messages_received: int = 0
    _current_api_start: float = field(default=0.0, repr=False)

    def start_api_call(self):
        self._current_api_start = time.monotonic()

    def record_api_success(self, prompt_tokens: int = 0, completion_tokens: int = 0):
        self.api_calls += 1
        elapsed = (time.monotonic() - self._current_api_start) * 1000
        self.api_total_latency_ms += elapsed
        self.tokens_prompt += prompt_tokens
        self.tokens_completion += completion_tokens

    def record_api_error(self):
        self.api_calls += 1
        self.api_errors += 1

    def record_cache_hit(self):
        self.cache_hits += 1

    def record_cache_miss(self):
        self.cache_misses += 1

    def record_tool_call(self):
        self.tool_calls += 1

    def record_user_message(self):
        self.messages_sent += 1

    def record_assistant_message(self):
        self.messages_received += 1

    @property
    def avg_latency_ms(self) -> float:
        successful = self.api_calls - self.api_errors
        return self.api_total_latency_ms / successful if successful > 0 else 0.0

    @property
    def cache_hit_rate(self) -> float:
        total = self.cache_hits + self.cache_misses
        return self.cache_hits / total if total > 0 else 0.0

    @property
    def total_tokens(self) -> int:
        return self.tokens_prompt + self.tokens_completion

    def report(self) -> str:
        """Generate a formatted stats report."""
        success = self.api_calls - self.api_errors
        rate = self.cache_hit_rate * 100

        return (
            f"[bold]📊 Session Stats[/bold]\n\n"
            f"API calls: {self.api_calls} ({success} success, {self.api_errors} errors)\n"
            f"Avg latency: {self.avg_latency_ms:.0f} ms\n"
            f"Tokens: {self.total_tokens} total ({self.tokens_prompt} prompt, {self.tokens_completion} completion)\n"
            f"Cache: {self.cache_hits + self.cache_misses} total ({self.cache_hits} hits, {self.cache_misses} misses, {rate:.0f}% hit)\n"
            f"Tool calls: {self.tool_calls}\n"
            f"Messages: {self.messages_sent} sent, {self.messages_received} received\n"
        )


# Global session stats instance
stats = StatsCollector()