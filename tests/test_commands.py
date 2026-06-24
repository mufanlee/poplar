"""Tests for commands.py — command registry, find, dispatch."""

from poplar.tui.commands import (
    Command,
    COMMANDS,
    UI_ONLY_COMMANDS,
    find_command,
    dispatch_command,
)


class TestCommandDataclass:
    def test_create_command(self):
        cmd = Command("/test", "desc", "_handler", match="exact")
        assert cmd.pattern == "/test"
        assert cmd.description == "desc"
        assert cmd.handler == "_handler"
        assert cmd.match == "exact"

    def test_command_is_frozen(self):
        cmd = Command("/x", "d", "_h")
        try:
            cmd.pattern = "/y"  # type: ignore[misc]
            assert False, "Should have raised"
        except Exception:
            pass  # frozen is enforced


class TestCommandRegistry:
    def test_all_commands_have_slash_prefix(self):
        for cmd in COMMANDS:
            assert cmd.pattern.startswith("/"), f"'{cmd.pattern}' should start with /"

    def test_all_commands_have_handler(self):
        for cmd in COMMANDS:
            assert cmd.handler, f"'{cmd.pattern}' has empty handler"

    def test_all_commands_have_description(self):
        for cmd in COMMANDS:
            assert cmd.description, f"'{cmd.pattern}' has empty description"

    def test_no_duplicate_patterns(self):
        patterns = [c.pattern for c in COMMANDS]
        assert len(patterns) == len(set(patterns))

    def test_command_count(self):
        # Keep this up to date when adding/removing commands
        assert len(COMMANDS) == 11

    def test_ui_only_commands_not_echoed(self):
        assert "/help" in UI_ONLY_COMMANDS
        assert "/quit" in UI_ONLY_COMMANDS
        assert "/session" in UI_ONLY_COMMANDS
        assert "/clear" in UI_ONLY_COMMANDS
        assert "/compress" in UI_ONLY_COMMANDS

    def test_non_ui_commands_not_in_ui_only(self):
        assert "/context" not in UI_ONLY_COMMANDS
        assert "/stats" not in UI_ONLY_COMMANDS


class TestFindCommand:
    def test_exact_match(self):
        cmd = find_command("/help")
        assert cmd is not None
        assert cmd.pattern == "/help"

    def test_exact_no_match(self):
        assert find_command("/nonexistent") is None

    def test_prefix_match(self):
        cmd = find_command("/provider openai")
        assert cmd is not None
        assert cmd.pattern == "/provider"

    def test_prefix_match_no_match(self):
        assert find_command("/provid") is None  # partial prefix, not enough

    def test_export_prefix(self):
        cmd = find_command("/export /tmp/file.json")
        assert cmd is not None
        assert cmd.pattern == "/export "

    def test_not_a_slash_command(self):
        assert find_command("hello") is None


class TestDispatch:
    def test_dispatch_exact_handler(self):
        """Exact-match commands call handler() with no argument."""
        called = []

        class FakeApp:
            def _show_help(self):
                called.append(self)

        app = FakeApp()
        result = dispatch_command(app, "/help")
        assert result is True
        assert len(called) == 1
        assert called[0] is app

    def test_dispatch_prefix_handler(self):
        """Prefix-match commands call handler(text) with full text."""
        called_text = []

        class FakeApp:
            def _handle_provider_command(self, text):
                called_text.append(text)

        app = FakeApp()
        result = dispatch_command(app, "/provider switch deepseek")
        assert result is True
        assert called_text == ["/provider switch deepseek"]

    def test_dispatch_unknown_slash(self):
        """Unknown / commands call _show_unknown_command."""
        called = []

        class FakeApp:
            def _show_unknown_command(self, text):
                called.append(text)

        app = FakeApp()
        result = dispatch_command(app, "/unknowncmd")
        assert result is True
        assert called == ["/unknowncmd"]

    def test_dispatch_not_a_command(self):
        """Non-slash text returns False."""
        class FakeApp:
            pass

        app = FakeApp()
        result = dispatch_command(app, "hello world")
        assert result is False

    def test_dispatch_missing_handler_raises(self):
        """If handler method doesn't exist, should raise AttributeError."""
        class FakeApp:
            pass  # No _show_help

        # /help is exact match and tries to call _show_help which doesn't exist
        app = FakeApp()
        try:
            dispatch_command(app, "/help")
            assert False, "Should have raised AttributeError"
        except AttributeError:
            pass  # Expected
