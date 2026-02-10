# Backlog

Ideas, tech debt, considerations, and unscheduled items.

## Future Features
- [ ] PDF support (python-pdfplumber or PyMuPDF)
- [ ] Duplicate file detection
- [ ] Bulk import/organize existing folders
- [ ] Export metadata/tags to CSV
- [ ] File preview panel
- [ ] "Create new project" / "Create new folder" actions from sidebar (right-click or button)

## UX Improvements
- [ ] Tag badge/chip UI: type a tag + press Enter to add it as a visual badge below the input field, with "x" to remove — better than plain comma-separated text
- [ ] Left pane split layout: upper section for project/folder tree, lower section shows file list when a folder is selected
- [ ] Open file from left pane: double-click a file to open it in Finder/Explorer or open directly — offer both options (context menu or choice dialog)
- [ ] Subfolder depth: support creating sub-subfolders, possibly auto-organize into subfolders based on tags
- [ ] Categories removed (Session 05) — tags alone are sufficient. If categories are needed later, re-add as a special "pinned tag" or separate concept

## Tech Debt
- [ ] Dark theme support: sidebar and drop zone have hardcoded light backgrounds — should respect system theme

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
