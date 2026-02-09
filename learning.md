# jDocs - Learning & Preferences

Accumulated patterns and preferences from working on this project. Updated as we go.

## Workflow Preferences
- Session-based work structure (~1hr per session)
- Claude codes, user reviews and directs
- Markdown files for all tracking and context
- Keep things simple and iterative

## Technical Preferences
- Mac has Python 3.10.4, Windows has Python 3.13 — code must be compatible with 3.10+
- `X | Y` union syntax is now OK (3.10+)
- `list[dict]`, `list[str]` lowercase generics are now OK (3.9+)

## Workflow Habits
- Always launch the app at the end of each session to verify it runs
- Run full test suite before committing

## What Works Well
_(To be filled based on session feedback)_

## What to Avoid
- Always check ALL type hints when fixing compatibility, not just the first one found
- Keep production builds lightweight: pytest and other dev tools must NOT be bundled in PyInstaller — only runtime deps (PyQt5, python-docx, openpyxl, python-pptx, Pillow)
