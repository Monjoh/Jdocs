# Backlog

Ideas, tech debt, considerations, and unscheduled items.

## Future Features
- [ ] PDF support (python-pdfplumber or PyMuPDF) — *scheduled: Session 13*
- [ ] Duplicate file detection
- [x] Bulk import/organize existing folders — *scheduled: Session 09 (folder scanning)*
- [ ] Export metadata/tags to CSV
- [ ] File preview panel
- [ ] "Create new project" / "Create new folder" actions from sidebar (right-click or button)
- [x] Multi-file batch upload — *scheduled: Session 09*
- [x] Open file location from file details — *scheduled: Session 10*
- [x] Edit tags/comments on existing files — *scheduled: Session 10*
- [x] Search results UI redesign (table/list layout) — *scheduled: Session 10*

## UX Improvements
- [x] Tag badge/chip UI — *scheduled: Session 11*
- [x] Left pane split layout: file list when folder selected — *scheduled: Session 11*
- [x] Open file from app — *scheduled: Session 11*
- [x] Collapsible sidebar — *done: Session 11*
- [x] Sidebar folder click → show files — *done: Session 11*
- [ ] Subfolder depth: support creating sub-subfolders, possibly auto-organize into subfolders based on tags
- [ ] Categories removed (Session 05) — tags alone are sufficient. If categories are needed later, re-add as a special "pinned tag" or separate concept

## Tech Debt
- [x] Dark theme support (including live switching) — *done: Session 11*

## Smart Features
- [ ] Keyword extraction from file content: analyze extracted text to surface relevant keywords (not just row/cell counts) — useful for understanding what a file is about
- [ ] Tag/category suggestions: match extracted keywords against existing tags and categories to auto-suggest during file input workflow
- [ ] Could leverage TF-IDF or simple frequency analysis on extracted text to rank keywords

## Design Topics
- [x] Root folder definition: first-launch setup to select the root folder where all projects live *(done in Session 07)*
- [ ] File resilience: handle cases where root folder or files inside it are moved/renamed/deleted outside the app (avoid broken references, detect changes, decide whether to re-process or prompt user)

## Considerations
- PyInstaller executable size — may need to optimize included libraries
- Cross-platform file path handling — use `pathlib.Path` everywhere, avoid hardcoded separators
- SQLite performance with large file counts — monitor and index appropriately
- File permissions on work PC — test early that move/copy operations work in user-space
