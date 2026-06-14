"""Poplar - AI Agent TUI Application"""

import sys
import os
import traceback
from datetime import datetime
from pathlib import Path


def setup_crash_handler():
    """Install a crash handler that logs unhandled exceptions."""
    # Find a writable directory for crash logs
    for base in (Path.home() / ".poplar", Path.cwd() / ".poplar"):
        log_dir = base / "logs"
        try:
            log_dir.mkdir(parents=True, exist_ok=True)
            test = log_dir / ".write_test"
            test.touch()
            test.unlink()
            break
        except (OSError, PermissionError):
            continue
    else:
        import tempfile
        log_dir = Path(tempfile.mkdtemp(prefix="poplar-")) / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
    crash_log = log_dir / "crash.log"

    def crash_handler(exc_type, exc_value, exc_tb):
        tb_text = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
        with open(crash_log, "a", encoding="utf-8") as f:
            f.write(f"\n{'=' * 60}\n")
            f.write(f"Crash at {datetime.now().isoformat()}\n")
            f.write(tb_text)
            f.write(f"{'=' * 60}\n")
        sys.__excepthook__(exc_type, exc_value, exc_tb)

    sys.excepthook = crash_handler


def main():
    """Main entry point for Poplar."""
    setup_crash_handler()

    from poplar.tui.app import PoplarApp

    # Check for API key
    if not os.getenv("DEEPSEEK_API_KEY"):
        print("Warning: DEEPSEEK_API_KEY environment variable not set.")
        print("Set it or edit src/poplar/tui/app.py to add your API key.")

    try:
        app = PoplarApp()
        app.run()
        return 0
    except Exception:
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
