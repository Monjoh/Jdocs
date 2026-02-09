# Backlog

Ideas, tech debt, considerations, and unscheduled items.

## Future Features
- [ ] PDF support (python-pdfplumber or PyMuPDF)
- [ ] Duplicate file detection
- [ ] Bulk import/organize existing folders
- [ ] Export metadata/tags to CSV
- [ ] File preview panel

## Tech Debt
_(None yet — project hasn't started coding)_

## Considerations
- PyInstaller executable size — may need to optimize included libraries
- Cross-platform file path handling — use `pathlib.Path` everywhere, avoid hardcoded separators
- SQLite performance with large file counts — monitor and index appropriately
- File permissions on work PC — test early that move/copy operations work in user-space
