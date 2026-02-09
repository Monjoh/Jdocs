# Session 04 — Drag & Drop File Input Workflow

**Date:** TBD
**Goal:** Make the drop zone functional — when a user drops a file, extract its metadata and display a post-drop panel where they can select a project/folder, preview metadata, and approve or cancel.
**Deliverable:** Working drag & drop flow: file drop > extraction > post-drop UI panel with project/folder selection and metadata preview.

## Context & Dependencies

This session connects the UI (`src/main.py`) with the extraction engine (`src/extractor.py`) and the database layer (`src/database.py`). After this session, the user will be able to drag a file into the app, see its extracted metadata, and choose where to organize it. The actual file move and database save will be wired up in Session 05.

**Modules involved:**
- `src/main.py` — modify DropZone to accept drops, add PostDropPanel widget
- `src/extractor.py` — called when a file is dropped to get text/metadata
- `src/database.py` — queried to populate project/folder dropdown options

## TODOs

### 1. Enable drag & drop on the DropZone widget
- [ ] Override `dragEnterEvent` to accept file drops (check MIME type for `application/x-qabstractitemmodeldatalist` or `text/uri-list`)
- [ ] Override `dragMoveEvent` to allow the drop
- [ ] Override `dropEvent` to capture the file path(s) from the drop event
- [ ] Add visual feedback: change DropZone border/background color when a file is being dragged over it (hover state)
- [ ] Restore normal DropZone styling when drag leaves or drop completes
- [ ] For now, handle single file drops only (if multiple files are dropped, take the first one and ignore the rest)

### 2. Call the extractor on drop
- [ ] When a file is dropped, call `extract(file_path)` from `src/extractor.py`
- [ ] Handle the case where `extract()` returns an error (e.g. display the error in the UI instead of the metadata panel)
- [ ] Store the extraction result so the PostDropPanel can display it

### 3. Build the PostDropPanel widget
- [ ] Create a new `PostDropPanel` QFrame widget that replaces the DropZone area after a file is dropped
- [ ] The panel should display:
  - **File name** — the original filename at the top as a header
  - **File type** — the extension (e.g. ".docx", ".xlsx")
  - **File size** — human-readable format (e.g. "24.5 KB", "1.2 MB")
  - **Project dropdown** — QComboBox populated from `database.list_projects()`
  - **Folder dropdown** — QComboBox populated from `database.list_folders(project_id)`, updates when project selection changes
  - **Metadata preview section** — displays type-specific metadata from the extraction result:
    - For .docx: author, title, paragraph count, text preview (first ~200 chars)
    - For .xlsx: sheet count, sheet names with row counts
    - For .pptx: author, title, slide count, text preview
    - For images: dimensions (WxH), format, EXIF highlights if any
    - For code files: line count, char count, text preview
    - For unsupported types: show the "unsupported" note
  - **Cancel button** — dismisses the panel and returns to the DropZone view
  - **Approve button** — placeholder for now (will wire up file move + DB save in Session 05)
- [ ] The panel should be scrollable if content overflows

### 4. Wire up panel transitions
- [ ] When a file is dropped: hide the DropZone, show the PostDropPanel with extraction data
- [ ] When Cancel is clicked: hide the PostDropPanel, show the DropZone again
- [ ] When Approve is clicked: for now, just print a message to console and return to DropZone (Session 05 will implement the actual save logic)
- [ ] Update the `file_info` label below the main panel to reflect the current state ("Drop a file to get started" vs "Reviewing: filename.xlsx")

### 5. Project/folder dropdown population
- [ ] Initialize the database at app startup (in-memory or temp file for now, since root folder config is Session 07)
- [ ] Populate the project dropdown from `database.list_projects()`
- [ ] When a project is selected, populate the folder dropdown with `database.list_folders(project_id)`
- [ ] Handle the empty state: if no projects exist yet, show a placeholder message or disabled dropdown
- [ ] Add a "(No project selected)" default option

### 6. Testing
- [ ] Manually test drag & drop with each supported file type (.docx, .xlsx, .pptx, .png, .jpg, .py)
- [ ] Verify metadata preview displays correctly for each type
- [ ] Verify unsupported file types show the appropriate note
- [ ] Verify Cancel returns to the DropZone cleanly
- [ ] Verify the app doesn't crash on edge cases: dropping a folder, dropping a very large file, dropping while panel is already open
- [ ] Run the full existing test suite (39 tests) to ensure nothing is broken

## Technical Notes

**Drag & drop in PyQt5:**
- DropZone already has `setAcceptDrops(True)` — we need to implement the event handlers
- File paths come from `event.mimeData().urls()` — each URL needs `.toLocalFile()` to get the path
- `dragEnterEvent` must call `event.acceptProposedAction()` to allow the drop

**Panel layout approach:**
- Use a QStackedWidget or simple show/hide to switch between DropZone and PostDropPanel in the main panel area
- This avoids destroying and recreating widgets on each drop

**Database initialization:**
- For this session, we'll use a temporary SQLite database (`:memory:` or temp file) so the app can run without root folder setup
- Session 07 will add proper first-launch config and persistent DB location

## Files
- `src/main.py` — modify extensively (DropZone events, new PostDropPanel widget, panel transitions)
- `tests/test_database.py` — no changes expected
- `tests/test_extractor.py` — no changes expected

## Decisions
_(To be logged during the session)_

## Notes
_(To be logged during the session)_
