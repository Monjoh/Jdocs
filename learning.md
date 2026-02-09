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
- Update session file and plan.md with detailed decisions/notes before committing
- Be detailed in session docs: explain *what* was done, *what* was tested, and *why* each decision was made — serves as future reference

## What Works Well
- pyqtSignal for decoupling widgets (DropZone doesn't know about extractor or database)
- Providing multiple input methods (drag & drop + click-to-browse) for better UX across different setups
- Dedicated extractors per file type instead of one-size-fits-all — allows type-specific optimizations (e.g. CSV row capping)
- Pinning action buttons outside scroll areas so they're always accessible

## What to Avoid
- Always check ALL type hints when fixing compatibility, not just the first one found
- Keep production builds lightweight: pytest and other dev tools must NOT be bundled in PyInstaller — only runtime deps (PyQt5, python-docx, openpyxl, python-pptx, Pillow)
- Don't load entire large files into memory for preview — cap rows (CSV: 100 rows, Excel: 100 rows per sheet)
- Don't put action buttons inside scroll areas — users shouldn't have to scroll past long content to find Cancel/Approve
