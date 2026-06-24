"""Tests for stats.py — StatsCollector metrics collection."""

from poplar.core.stats import StatsCollector


class TestStatsCollector:
    def test_defaults_zero(self):
        s = StatsCollector()
        assert s.api_calls == 0
        assert s.api_errors == 0
        assert s.tokens_prompt == 0
        assert s.tokens_completion == 0
        assert s.cache_hits == 0
        assert s.cache_misses == 0
        assert s.tool_calls == 0
        assert s.messages_sent == 0
        assert s.messages_received == 0

    def test_record_api_success(self):
        s = StatsCollector()
        s.record_api_success(prompt_tokens=100, completion_tokens=50)
        assert s.api_calls == 1
        assert s.tokens_prompt == 100
        assert s.tokens_completion == 50

    def test_record_api_error(self):
        s = StatsCollector()
        s.record_api_error()
        assert s.api_calls == 1
        assert s.api_errors == 1

    def test_record_tool_call(self):
        s = StatsCollector()
        s.record_tool_call()
        s.record_tool_call()
        assert s.tool_calls == 2

    def test_record_user_message(self):
        s = StatsCollector()
        s.record_user_message()
        s.record_user_message()
        assert s.messages_sent == 2

    def test_record_assistant_message(self):
        s = StatsCollector()
        s.record_assistant_message()
        assert s.messages_received == 1

    def test_cache_hit_rate_zero_when_no_hits(self):
        s = StatsCollector()
        assert s.cache_hit_rate == 0.0

    def test_cache_hit_rate(self):
        s = StatsCollector()
        s.cache_hits = 3
        s.cache_misses = 7
        assert s.cache_hit_rate == 0.3

    def test_cache_hit_rate_perfect(self):
        s = StatsCollector()
        s.cache_hits = 5
        s.cache_misses = 0
        assert s.cache_hit_rate == 1.0

    def test_total_tokens(self):
        s = StatsCollector()
        s.tokens_prompt = 200
        s.tokens_completion = 300
        assert s.total_tokens == 500

    def test_report_contains_expected_sections(self):
        s = StatsCollector()
        s.api_calls = 5
        s.api_errors = 1
        s.tool_calls = 3
        s.messages_sent = 10
        s.messages_received = 8
        report = s.report()
        assert "API calls" in report
        assert "5" in report
        assert "1 errors" in report or "(1" in report
        assert "Tool calls" in report
        assert "3" in report

    def test_report_cache_line(self):
        s = StatsCollector()
        s.cache_hits = 5
        s.cache_misses = 5
        report = s.report()
        assert "Cache" in report
        assert "50" in report  # 50% hit rate

    def test_multiple_success_calls(self):
        s = StatsCollector()
        for _ in range(3):
            s.record_api_success(prompt_tokens=10, completion_tokens=20)
        assert s.api_calls == 3
        assert s.api_errors == 0
        assert s.tokens_prompt == 30
        assert s.tokens_completion == 60
