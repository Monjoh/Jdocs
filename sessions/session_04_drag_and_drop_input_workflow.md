# Session 04 — Drag & Drop File Input Workflow

**Date:** 2026-02-09
**Goal:** Make the drop zone functional — when a user drops a file, extract its metadata and display a post-drop panel where they can select a project/folder, preview metadata, and approve or cancel.
**Deliverable:** Working drag & drop flow: file drop > extraction > post-drop UI panel with project/folder selection and metadata preview.

## Context & Dependencies

This session connects the UI (`src/main.py`) with the extraction engine (`src/extractor.py`) and the database layer (`src/database.py`). After this session, the user can drag a file into the app (or click to browse), see its extracted metadata, and choose where to organize it. The actual file move and database save will be wired up in Session 05.

**Modules involved:**
- `src/main.py` — modified DropZone to accept drops + clicks, added PostDropPanel widget, wired up MainWindow
- `src/extractor.py` — called on drop to get text/metadata; added dedicated CSV handler, optimized Excel loading
- `src/database.py` — queried to populate project/folder dropdown options (no changes to this file)

## TODOs

### 1. Enable drag & drop on the DropZone widget
- [x] Override `dragEnterEvent` to accept file drops (checks `event.mimeData().hasUrls()`)
- [x] Override `dragMoveEvent` to allow the drop to continue
- [x] Override `dropEvent` to capture the file path from the drop event
- [x] Add visual feedback: border turns blue (#4a90d9) and background changes to light blue (#e3f0ff) when hovering
- [x] Restore normal dashed gray styling when drag leaves or drop completes
- [x] Handle single file drops only (takes first URL, ignores rest)
- [x] Add click-to-browse: `mousePressEvent` opens `QFileDialog` as an alternative to drag & drop

### 2. Call the extractor on drop
- [x] `_on_file_dropped` calls `extract(file_path)` when a file is dropped or selected via file picker
- [x] If `extract()` returns an error, the error is shown in the status label (red text) and the app stays on the DropZone
- [x] Extraction result is stored in `PostDropPanel.extraction_result` for later use by Approve

### 3. Build the PostDropPanel widget
- [x] PostDropPanel QFrame replaces DropZone area after a file is dropped
- [x] Displays: file name (bold header), file type + human-readable size
- [x] Project dropdown (QComboBox) populated from `database.list_projects()`
- [x] Folder dropdown (QComboBox) populated from `database.list_folders(project_id)`, updates on project change
- [x] Metadata preview section with type-specific formatting:
  - .docx: author, title, paragraph count
  - .xlsx: sheet count, per-sheet names and row counts
  - .pptx: author, title, slide count
  - .csv: total rows, column count, column names (capped at 10 with "+N more")
  - Images: dimensions (WxH), format, color mode, EXIF highlights (up to 5 entries)
  - Code files: line count, character count
  - Unsupported types: "unsupported" note
- [x] Text preview: first 200 chars of extracted text, hidden for files with no text
- [x] Cancel button returns to DropZone, Approve button is a placeholder (prints to console)
- [x] Only the content area scrolls; buttons are pinned at bottom outside the scroll area

### 4. Wire up panel transitions
- [x] QStackedWidget switches between DropZone (index 0) and PostDropPanel (index 1)
- [x] Drop/browse → show PostDropPanel with data; Cancel → show DropZone; Approve → placeholder + show DropZone
- [x] Status label updates: "Drop a file to get started" / "Reviewing: filename.xlsx" / "Error: ..."

### 5. Project/folder dropdown population
- [x] In-memory database initialized at app startup with sample projects/folders
- [x] Sidebar loads from database (replaced hardcoded sample data)
- [x] Project dropdown populated from DB; folder dropdown updates on project change
- [x] "(No project selected)" and "(No folder selected)" as default options

### 6. Feedback improvements (mid-session)
- [x] Add dedicated CSV extractor — reads only first 100 rows, counts total rows via fast newline counting
- [x] Optimize Excel extractor — stream rows instead of loading all into memory, cap text preview at 100 rows
- [x] Pin Cancel/Approve buttons outside scroll area so they're always visible
- [x] Add file picker dialog on DropZone click as an alternative to drag & drop

### 7. Testing
- [x] App launches successfully
- [x] Full test suite: 46 tests passing (18 database + 28 extractor)
- [x] Added 7 new CSV extraction tests

## Decisions

- **QStackedWidget for panel switching:** Chosen over show/hide because it properly manages widget lifecycle and avoids layout recalculation issues. Index 0 is DropZone, index 1 is PostDropPanel — switching is a single `setCurrentIndex()` call.

- **pyqtSignal for decoupling:** DropZone emits `file_dropped(str)` without knowing about the panel or database. MainWindow connects signals. This keeps widgets independent and testable — DropZone doesn't need to import extractor or database.

- **In-memory database for now:** Using `:memory:` SQLite so the app runs without root folder setup. Session 07 will add persistent path. Sample data seeds the same projects/folders shown in the sidebar.

- **Click-to-browse added to DropZone:** Drag & drop can be awkward depending on window placement or when using a trackpad. `mousePressEvent` opens a native `QFileDialog` as a second input method. Both paths emit the same `file_dropped` signal so the downstream flow is identical.

- **CSV as its own extractor (not a code file):** CSV files can be very large and reading them entirely as raw text (like code files) is slow and not useful. A dedicated `_extract_csv()` handler reads only the first 100 rows via `csv.reader`, extracts column names from the header, and counts total rows via fast `str.count("\n")`. This gives useful structural metadata (columns, row count) instead of raw text dump.

- **Excel streaming optimization:** Previously `list(ws.iter_rows())` loaded ALL rows into a Python list before slicing. Changed to iterate with `enumerate()` and only collect text from the first 100 rows while still counting total rows. This avoids loading huge spreadsheets entirely into memory.

- **Buttons pinned outside scroll area:** Originally Cancel/Approve were inside the QScrollArea, meaning users had to scroll past long metadata to reach them. Moved to a separate QFrame below the scroll area with `border-top` separator. The scroll area gets `stretch=1` so it fills available space while the button bar stays fixed height.

- **CSV column names capped at 10 in display:** Files with many columns would overflow the metadata section. Column names beyond 10 are summarized as "+N more" to keep the UI compact while still showing the most important columns.

## Test Coverage Details

| Test Class | Tests | What's Verified |
|-----------|-------|-----------------|
| TestDocxExtraction | 4 | Paragraph text, author/title/paragraph_count, file info fields, no error |
| TestXlsxExtraction | 4 | Cell values in text, sheet_count=2, per-sheet name and row_count, no error |
| TestPptxExtraction | 4 | Slide title/body text, slide_count=2, author/title, no error |
| TestImageExtraction | 4 | PNG/JPG dimensions 200x150, correct format strings, empty text for images, no error |
| TestCsvExtraction | 7 | Cell values in text, column names match header, column_count=4, total_rows>=5, preview_rows<=100, file_type=".csv" (not code), no error |
| TestCodeExtraction | 3 | Full source content, line_count/char_count > 0, no error |
| TestEdgeCases | 2 | Non-existent file returns error, unsupported .xyz returns metadata note |

## Notes

- **File picker vs drag & drop:** Both input methods emit the same `file_dropped(str)` signal, so all downstream logic (extraction, panel display, project/folder selection) is shared. No code duplication.

- **Approve button is still a placeholder:** It prints `[Approve] File: ... -> Project: ..., Folder: ...` to console and returns to DropZone. Session 05 will implement the actual file move, database save, and sidebar refresh.

- **Sidebar now loads from database:** Replaced the hardcoded `_add_sample_projects()` with `load_from_database(db)` that queries `list_projects()` and `list_folders()`. This means the sidebar and dropdowns always show the same data.
