"""Poplar - AI Agent TUI Application"""

import sys
import os
import traceback
from datetime import datetime
from poplar.utils import get_writable_dir


def setup_crash_handler() -> None:
    """Install a crash handler that logs unhandled exceptions."""
    log_dir = get_writable_dir("logs")
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


def main() -> int:
    """Main entry point for Poplar."""
    setup_crash_handler()

    # Check for API key before starting
    from poplar.config import get_provider_config
    prov = get_provider_config()
    name = prov["name"]
    if name != "ollama":
        api_key = prov["config"].get("api_key") or os.getenv(f"{name.upper()}_API_KEY")
        if not api_key:
            print(f"Error: No API key for provider '{name}'.")
            print(f"Set in ~/.poplar/config.yaml: api_key under providers.{name}")
            print(f"Or export {name.upper()}_API_KEY=sk-xxxx")
            return 1

    from poplar.tui.app import PoplarApp

    try:
        app = PoplarApp()
        app.run()
        return 0
    except Exception:
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
