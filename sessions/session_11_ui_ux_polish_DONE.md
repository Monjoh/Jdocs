# Session 11 — UI/UX Polish

**Date:** 2026-02-11
**Status:** DONE

## Objectives

1. Fix dark/light theme live switching (sidebar + search bar don't update on OS theme change)
2. Tag chip UI with easy free-text entry
3. Sidebar folder click → show files in main panel
4. Open file OR folder from file detail panel
5. Collapsible sidebar

## What Was Built

### 1. Live Theme Switching
**Problem:** Sidebar (project/folder tree) and search bar colors were computed once in `__init__` using palette colors. When the user toggled macOS dark/light mode while the app was open, the sidebar and search bar kept their stale colors, making text unreadable.

**Fix:**
- Extracted all sidebar color computation into `Sidebar._apply_theme()` method
- Added `Sidebar.changeEvent()` override that detects `QEvent.PaletteChange` and calls `_apply_theme()`
- Widget creation (labels, tree, hint) now happens in `__init__` without inline styles — `_apply_theme()` is called at the end of `__init__` and again on every palette change
- Added `MainWindow._apply_search_bar_theme()` that reads palette `Base`, `WindowText`, and `Mid` colors for background, text, and border
- Added `MainWindow.changeEvent()` to re-apply search bar theme on palette change
- Imported `QEvent` from `PyQt5.QtCore`

**How it works:** Qt fires a `PaletteChange` event whenever the OS theme changes. Both `Sidebar` and `MainWindow` listen for this event and recompute their styles from the new palette.

### 2. Open File + Open Folder Buttons
**Problem:** FileDetailPanel only had "Open File Location" which opened the parent folder. User wanted the option to open the file itself too.

**Fix:**
- Replaced single `open_location_btn` with two buttons in a horizontal row:
  - **"Open File"** — `QDesktopServices.openUrl(QUrl.fromLocalFile(file_path))` opens the file in the system's default application (e.g. Word for .docx, Preview for .png)
  - **"Open Folder"** — same as before, opens parent directory in Finder/Explorer
- Both buttons warn if the file no longer exists at the stored path
- Buttons are in a `QHBoxLayout` with stretch at the end so they stay left-aligned

### 3. Collapsible Sidebar
**Design:** Added a thin toggle button (`<` / `>`) between the sidebar and the main content area.

**Implementation:**
- `sidebar_toggle` QPushButton with fixed width of 20px, positioned in the content layout between sidebar and main panel
- Clicking toggles `sidebar.setVisible()` and swaps the button text between `<` (collapse) and `>` (expand)
- Tooltip updates to "Collapse sidebar" / "Expand sidebar"
- Main panel automatically expands to fill the space when sidebar is hidden (handled by Qt layout stretch)

### 4. Tag Chip UI (Hybrid Input + Chips)
**Problem:** Tags were a plain comma-separated QLineEdit. Works for typing but bad for visualizing what tags exist and removing individual ones.

**Design decision — hybrid approach:** Keep a text input for easy free-text entry, but render committed tags as visual chips below. This preserves the speed of typing while giving clear visual feedback.

**New widgets:**
- **`TagChipInput`** — main widget combining a QLineEdit and a chips area:
  - User types a tag and presses **Enter** or **comma** to commit it as a chip
  - Comma auto-commit: if user types "finance, Q1" the comma triggers immediate commit of "finance" and keeps "Q1" in the input
  - Each chip is a rounded blue badge (`#e8f0fe` background, `#1a73e8` text) with an "x" button
  - Clicking "x" removes the tag
  - Duplicate tags prevented (case-insensitive check)
  - `get_tags() -> list[str]` returns only committed chips (ignores uncommitted input text)
  - `set_tags(tags)` replaces all chips (used when loading existing file tags in FileDetailPanel)
  - `clear()` removes all chips and clears input
  - Emits `tags_changed` signal when tags are added or removed

- **`FlowLayout`** — simple layout helper that arranges chips in a horizontal row with stretch. Used internally by `TagChipInput`.

- **`TagSuggestionBar`** — updated to work with `TagChipInput` instead of `QLineEdit`:
  - Now listens to `tags_changed` signal instead of `textChanged`
  - Reads current tags via `get_tags()` instead of parsing comma text
  - Clicking a suggestion calls `_add_tag()` directly on the `TagChipInput`

**Integration:**
- `PostDropPanel`: replaced `QLineEdit` tags_input with `TagChipInput`. Updated `clear_inputs()` and `get_tags()` to use the new API.
- `FileDetailPanel`: replaced `QLineEdit` tags_input with `TagChipInput`. Updated `populate()` to use `set_tags()` and `_on_save()` to use `get_tags()`.

### 5. Sidebar Folder Click → Show Files
**Problem:** Sidebar tree was display-only. Clicking a project or folder did nothing useful.

**Implementation:**
- Added `folder_clicked(int, str)` signal to `Sidebar` (emits folder_id and folder_name)
- `load_from_database()` now stores folder IDs as `Qt.UserRole` data on each tree item (`None` for project items, folder ID for folder items)
- `_on_tree_item_clicked()` checks if the clicked item has a folder_id and emits the signal
- Added `SearchResultsPanel.show_folder_files()` method — same rendering as search results but with header showing folder name and file count instead of search query
- `MainWindow._on_folder_clicked()` handler:
  - Calls `db.list_files(folder_id)` to get files
  - Enriches each file record with tags, folder name, and project name (same pattern as search results enrichment)
  - Displays in the search results panel via `show_folder_files()`
  - Clicking a file in the list navigates to FileDetailPanel (reuses existing `result_clicked` signal)

**Note:** Clicking a project item (parent node) does nothing — only folder items trigger the file list. This is intentional: projects are containers for folders, not for files directly.

## Files Modified
| File | Changes |
|------|---------|
| `src/main.py` | All 5 features. New: `FlowLayout`, `TagChipInput` classes. Modified: `Sidebar` (theme + folder click), `TagSuggestionBar` (works with TagChipInput), `FileDetailPanel` (Open File/Folder, TagChipInput), `PostDropPanel` (TagChipInput), `SearchResultsPanel` (show_folder_files), `MainWindow` (theme change, toggle sidebar, folder click handler) |

## New Imports Added
- `QEvent` from `PyQt5.QtCore`

## Tests
- 120 tests passing (no new tests added — all changes are UI/widget code)
- No database or extractor changes in this session

## Issues & Gotchas
- **CRITICAL: `setStyleSheet()` inside `changeEvent(PaletteChange)` causes infinite recursion** — Setting a stylesheet triggers Qt to fire another `PaletteChange` event, which calls `_apply_theme()` again, ad infinitum. Crash manifests as "Abort trap 6" on macOS with no useful traceback in the terminal (only visible by catching `RecursionError`). **Fix:** Added `_applying_theme` boolean guard — `changeEvent` skips `_apply_theme()` if the flag is already set. This pattern is needed on *both* `Sidebar` and `MainWindow`.
- **`QPalette.PlaceholderText` returns white on macOS dark theme** — discovered during dark theme work (pre-session fix). Cannot use it for muted text. Solution: derive muted color by averaging foreground and background RGB values (`(fg + bg) / 2`).
- **`QEvent.PaletteChange` fires on both theme directions** — works for both dark→light and light→dark transitions. No special handling needed.
- **Tag chip "x" button sizing** — needed `setFixedSize(16, 16)` and zero padding to keep chips compact. Without this, the remove button added too much height.
- **Comma auto-commit edge case** — when user types "tag1, tag2, " (trailing comma), the split logic keeps empty string after last comma. Handled by stripping and checking `if tag` before adding.
- **FlowLayout simplification** — initially considered a proper flow layout that wraps to multiple rows, but for the typical number of tags (< 10), a single `QHBoxLayout` with stretch is sufficient. Can be upgraded later if users add many tags.

### Post-testing UI polish (5 fixes from user feedback)

**1. Sidebar toggle moved to search bar row:**
- Previously a full-height strip between sidebar and main panel — took too much space
- Moved to a 28x28 button on the left of the search bar in a `QHBoxLayout` row
- Toggle text `<` / `>` with tooltip

**2. Tag chips shown above input + "Suggested:" label:**
- Chips container moved above QLineEdit in `TagChipInput` — selected tags are now clearly visible at the top
- `TagSuggestionBar.set_suggestions()` now prepends a `QLabel("Suggested:")` with muted gray 10px text
- Bar hides itself when no suggestions are available

**3. "Back to Results" moved to top-right of FileDetailPanel:**
- Added header row in FileDetailPanel: filename (left) + "Back to Results" button (right)
- Matches the position of "Clear Search" in SearchResultsPanel for consistent navigation
- Removed duplicate "Back to Results" from bottom button bar (only Save Changes remains there)

**4. DropZone dark mode support:**
- Removed hardcoded `DROPZONE_NORMAL` / `DROPZONE_HOVER` constants
- DropZone now computes colors from palette via `_apply_theme()` + `changeEvent(PaletteChange)`
- Background slightly offset from window color (+/-15 lightness) for visual distinction
- Muted text label color derived by blending fg+bg
- Hover color adapts: `#e3f0ff` in light mode, `#1a3050` in dark mode
- Uses `_is_hovering` flag to avoid overwriting hover state during theme changes

**5. Search results hover/selected readable in dark mode:**
- `SearchResultsPanel` now has `_apply_theme()` + `changeEvent(PaletteChange)`
- In dark mode: hover/selected use semi-transparent `rgba()` based on the system highlight color
- In light mode: keeps the original `#e8f0fe` / `#d2e3fc` colors
- Border between items uses `#444` in dark, `#eee` in light
- No-results label uses derived muted color

## Decisions
- **Hybrid tag input over pure chip-only**: Pure chip-only (no text input, popup to add) would be slower for power users. The hybrid keeps typing fast while giving visual feedback.
- **Sidebar toggle as `<`/`>` button**: Simpler than a hamburger menu or splitter handle. Minimal visual footprint. Moved to search bar row after testing.
- **Folder click only (not project click)**: Projects don't contain files directly — they contain folders which contain files. Showing "all files in project" would require a different query and could be a future enhancement.
- **Reuse SearchResultsPanel for folder files**: Avoids creating a separate panel. The `show_folder_files()` method just changes the header text.
- **`rgba()` for dark mode hover**: Better than computing a hex color — lets the underlying content partially show through, which looks natural.
