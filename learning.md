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

## Configuration & Persistence Patterns
- **Separate config location from data location**: config in OS user data dir (always findable), DB inside root folder (travels with data)
  - Windows config: `%LOCALAPPDATA%\jdocs\config.json`
  - macOS/Linux config: `~/.config/jdocs/config.json`
  - DB: `<root_folder>/.jdocs/jdocs.db`
- **Always merge loaded config with defaults**: ensures forward compatibility when new config keys are added in future versions (`merged = _defaults(); merged.update(loaded_data)`)
- **Graceful recovery from corrupt config**: catch `json.JSONDecodeError` and return defaults instead of crashing
- **`is_configured()` should check directory exists, not just non-empty string**: handles edge case where user deletes root folder after setup
- **Use `shutil.copy2` over `shutil.copy`**: preserves file timestamps and permissions, important for document management
- **Duplicate filename handling**: append `_1`, `_2` suffix rather than overwriting or prompting (simple, predictable, no user interruption)

## Environment Gotchas
- **macOS: use `python3` not `python`** — `python` points to system Python 2.7/3.7, `python3` points to 3.10.4. Use `.venv/bin/python3` or `python3 -m pytest` for testing.
- **Use a venv for testing** — created `.venv/` at project root to isolate dependencies (already in `.gitignore`). Activate with `.venv/bin/python3` or source `.venv/bin/activate`.
- **pytest is not installed in Termux** — use `python -m unittest tests.test_module -v` instead. Tests use `sys.path.insert(0, ...)` to find src modules, which works with both runners.
- **`platform.system()` returns `"Windows"`, `"Darwin"`, `"Linux"`** — use this for OS detection, not `sys.platform` (which returns `"win32"`, `"darwin"`, `"linux"`)
- **python-docx 1.2.0 changed error behavior** — corrupt `.docx` files now raise `Exception("Package not found")` instead of `BadZipFile`. The extractor handles both cases.

## What to Avoid
- Always check ALL type hints when fixing compatibility, not just the first one found
- Keep production builds lightweight: pytest and other dev tools must NOT be bundled in PyInstaller — only runtime deps (PyQt5, python-docx, openpyxl, python-pptx, Pillow)
- Don't load entire large files into memory for preview — cap rows (CSV: 100 rows, Excel: 100 rows per sheet)
- Don't put action buttons inside scroll areas — users shouldn't have to scroll past long content to find Cancel/Approve
- **Don't hot-swap database connections at runtime** — too many widgets depend on the DB reference. Prefer restart for config changes that affect the DB path.
- **Never delete user's source files on approve** — copy, don't move. If the organized root folder is lost, user still has originals.
