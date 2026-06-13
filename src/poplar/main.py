"""Poplar - AI Agent TUI Application"""

import sys
import os


def main():
    """Main entry point for Poplar."""
    from poplar.tui.app import PoplarApp

    # Check for API key
    if not os.getenv("DEEPSEEK_API_KEY"):
        print("Warning: DEEPSEEK_API_KEY environment variable not set.")
        print("Set it or edit src/poplar/tui/app.py to add your API key.")

    app = PoplarApp()
    app.run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
