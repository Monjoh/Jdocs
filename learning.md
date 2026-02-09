# jDocs - Learning & Preferences

Accumulated patterns and preferences from working on this project. Updated as we go.

## Workflow Preferences
- Session-based work structure (~1hr per session)
- Claude codes, user reviews and directs
- Markdown files for all tracking and context
- Keep things simple and iterative

## Technical Preferences
- Mac has Python 3.7, Windows has Python 3.13 — code must be compatible with 3.7+
- Use `Union[X, Y]` from typing instead of `X | Y` syntax (requires 3.10+)
- Use `List[Dict]`, `List[str]` from typing — NOT `list[dict]`, `list[str]` (requires 3.9+)

## What Works Well
_(To be filled based on session feedback)_

## What to Avoid
- `str | Path` union syntax — breaks on Python < 3.10 (Mac has 3.7)
- `list[dict]` subscript syntax — breaks on Python < 3.9
- Always check ALL type hints when fixing compatibility, not just the first one found
