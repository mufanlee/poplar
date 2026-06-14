# Session Export/Import — Design

## Goal
Allow users to export conversations to JSON files and import them back, enabling backup, sharing, and migration between instances.

## Commands

- `/export <path>` — Export current session to a JSON file
- `/import <path>` — Import a session from a JSON file (as a new session)

## Export Format

```json
{
  "poplar_session": true,
  "version": 1,
  "exported_at": "2026-06-17T10:30:00",
  "session": {
    "title": "Chat about caching",
    "created_at": "2026-06-17T09:00:00",
    "messages": [
      {"role": "user", "content": "hello"},
      {"role": "assistant", "content": "hi there", "tool_calls": null}
    ]
  }
}
```

## Implementation

### New method in app.py
- `action_export_session(path)` — serializes session to JSON, writes file, notifies
- `action_import_session(path)` — reads JSON, creates new session in store, refreshes sidebar

### Key details
- File written to cwd or absolute path (whichever specified)
- Imported sessions get a new UUID id (don't overwrite existing)
- Messages are re-created via `Message.from_dict()`
- Errors shown as notifications

## Files Changed
- `src/poplar/tui/app.py` — add /export and /import commands
- No new files needed
