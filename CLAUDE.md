# jDocs - Claude Context File

## Project Overview
**jDocs** — a lightweight cross-platform desktop app for organizing files (Excel, PowerPoint, Word, images, code files) with tagging, categorization, metadata extraction, and search. Runs locally with no external APIs.

## Platform Support
- **Windows PC** (primary target) — no admin rights, user-level install only
- **macOS** (secondary) — full admin access, used for testing
- Code must work on both platforms (file paths, packaging, UI)

## Tech Stack
- **Language:** Python
- **UI:** PyQt5
- **Database:** SQLite (metadata, tags, search index)
- **Libraries:** python-docx, openpyxl, python-pptx, Pillow
- **Distribution:** Standalone executable via PyInstaller (.exe on Windows, .app on macOS)
- **Future:** PDF support

## Core Use Cases
1. **Input New File:** Drag file > extract text/metadata > suggest folder > user tags/categorizes > approve > file moves
2. **Search:** Search bar with filters across filename, metadata, tags, categories

## Key Constraints
- No admin rights on Windows PC (macOS has full access)
- Cross-platform: must work on both Windows and macOS
- Local-only, no external APIs or cloud services
- Root folder selected on first launch (contains all organized projects/subfolders)
- User has ~30min daily; sessions planned for ~1hr of work

## Session Workflow
1. At session start: read `plan.md` for current state, then open the active session file in `sessions/`
2. Work through the session's TODOs sequentially
3. Log decisions and notes in the session file as we go
4. Update `learning.md` with any new patterns or preferences discovered
5. When session is complete: rename session file with `_DONE` suffix, update `plan.md`
6. If new ideas/tech debt arise mid-session: add to `backlog/backlog.md`

## Project-Level Instructions
- Claude does the coding; user provides direction and reviews
- Keep code simple and iterative — avoid over-engineering
- Prefer editing existing files over creating new ones
- Each session has clear objectives and deliverables
- All context lives in markdown files, not in conversation memory

## File Structure
```
jdocs/
├── CLAUDE.md              # This file - main context for Claude
├── plan.md                # Roadmap, current state, session overview
├── learning.md            # Accumulated preferences and patterns
├── README.md              # Project overview and setup instructions
├── backlog/
│   └── backlog.md         # Ideas, tech debt, unscheduled items
├── sessions/
│   └── session_XX_*.md    # Individual session files (renamed _DONE when complete)
├── src/                   # Application source code
├── tests/                 # Test files
├── docs/                  # Additional documentation if needed
└── assets/                # Icons, images, etc.
```
