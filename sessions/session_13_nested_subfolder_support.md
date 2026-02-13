# Session 13 — Nested Subfolder Support

**Date:** 2026-02-13
**Status:** Complete

## Context & Motivation

The database already supports nested folders via `parent_folder_id` on the `folders` table (with a passing test). However, the UI was completely flat — the sidebar only showed root-level folders, the folder dropdown only listed root folders, and file placement built a flat `ROOT/Project/Folder/` path. This session adds true nested subfolder support end-to-end.

**Before:** `Project > Folder > Files` (one level only)
**After:** `Project > Folder > Subfolder > ... > Files` (up to 5 levels deep)

---

## Completed

### 1. Database layer: `get_folder_path()`, `get_folder_depth()`, `get_all_folders_nested()`
**File:** `src/database.py`

- Added `MAX_FOLDER_DEPTH = 5` constant
- `get_folder_depth(folder_id)` — walks `parent_folder_id` chain upward, returns integer depth (root = 1)
- `get_folder_path(folder_id)` — returns ordered list of `{"id", "name"}` dicts from root to target folder. Used by filesystem path builder and display logic.
- `get_all_folders_nested(project_id)` — returns flat list of all folders in tree order with `depth` and `display` (breadcrumb format: `"Reports > Q1 > January"`). Uses recursive `_collect_folders()` helper.
- `create_folder()` — now checks depth before creating. Raises `ValueError` if parent is already at `MAX_FOLDER_DEPTH`.

### 2. Sidebar: Recursive tree display
**File:** `src/main.py` — `Sidebar.load_from_database()`, `Sidebar._add_folder_children()`

- Replaced flat `for folder in db.list_folders(project_id)` with recursive `_add_folder_children()` that:
  - Fetches children for each parent via `db.list_folders(project_id, parent_folder_id=...)`
  - Creates nested `QTreeWidgetItem` hierarchy
  - Stores both `folder_id` (UserRole) and `project_id` (UserRole + 1) on each item
- `expandAll()` still expands the full tree by default

### 3. Sidebar: Right-click context menu
**File:** `src/main.py` — `Sidebar._on_context_menu()`

- Added `QMenu`-based context menu via `setContextMenuPolicy(Qt.CustomContextMenu)`
- Three signal types emitted based on click target:
  - **Empty space** → "New Project" → `create_project_requested` signal
  - **Project item** → "New Folder" + "New Project" → `create_folder_requested(project_id)` signal
  - **Folder item** → "New Subfolder" + "New Project" → `create_subfolder_requested(project_id, parent_folder_id)` signal
- Three new MainWindow handlers: `_on_sidebar_new_project()`, `_on_sidebar_new_folder()`, `_on_sidebar_new_subfolder()` — each uses `QInputDialog`, `sanitize_name()`, creates via DB, refreshes sidebar
- Subfolder handler catches `ValueError` for depth limit and shows user-friendly warning

### 4. Folder dropdown: Breadcrumb hierarchy
**File:** `src/main.py` — `PostDropPanel.set_folders()`, `MainWindow._on_project_changed()`

- `_on_project_changed()` now calls `db.get_all_folders_nested(project_id)` instead of `db.list_folders(project_id)`
- `set_folders()` uses `f.get("display", f["name"])` to show breadcrumb paths in dropdown
- Dropdown now shows all folders at all depths: `"Reports"`, `"Reports > Q1"`, `"Reports > Q1 > January"`, etc.

### 5. PostDropPanel "+" folder button: Context-aware subfolder creation
**File:** `src/main.py` — `MainWindow._on_new_folder()`

- If no folder is selected → creates root-level folder (existing behavior)
- If a folder is selected → creates subfolder inside it, with prompt showing parent name
- After creation, refreshes dropdown with `get_all_folders_nested()` and selects the new folder by ID
- Catches `ValueError` for depth limit

### 6. File placement: Nested filesystem paths
**File:** `src/main.py` — `MainWindow._on_approve()`

- Replaced flat `target_dir = self.root_folder / project["name"] / folder["name"]` with:
  ```python
  folder_chain = self.db.get_folder_path(folder_id)
  folder_parts = [f["name"] for f in folder_chain]
  target_dir = self.root_folder / project["name"] / Path(*folder_parts)
  ```
- `mkdir(parents=True, exist_ok=True)` creates all intermediate directories automatically

### 7. File detail panel: Breadcrumb location display
**File:** `src/main.py` — `MainWindow._refresh_file_detail()`

- Location now shows full breadcrumb path: `"Location: Work / Reports > Q1 > January"` instead of just the leaf folder name

### 8. Tests
**File:** `tests/test_database.py` — 8 new tests (128 total, all passing)

| Test | Description |
|---|---|
| `test_get_folder_depth_root` | Root-level folder has depth 1 |
| `test_get_folder_depth_nested` | 3-level nesting returns correct depths (1, 2, 3) |
| `test_get_folder_path_root` | Single folder returns 1-element path list |
| `test_get_folder_path_nested` | 3-level nesting returns correct root-to-leaf chain |
| `test_get_folder_path_nonexistent` | Nonexistent folder returns empty list |
| `test_get_all_folders_nested` | Verifies tree order, depth, and breadcrumb display |
| `test_create_folder_depth_limit` | Creating folder beyond MAX_FOLDER_DEPTH raises ValueError |
| `test_create_folder_at_max_depth_succeeds` | Creating at exactly MAX_FOLDER_DEPTH works |

---

## Files Modified

| File | Action | Details |
|---|---|---|
| `src/database.py` | Modified | Added `MAX_FOLDER_DEPTH`, `get_folder_depth()`, `get_folder_path()`, `get_all_folders_nested()`, depth check in `create_folder()` |
| `src/main.py` | Modified | Recursive sidebar, context menu (3 signals + 3 handlers), breadcrumb dropdown, nested file paths, breadcrumb in file detail |
| `tests/test_database.py` | Modified | 8 new tests for subfolder logic |

## Key Decisions (Confirmed)
- **Max nesting depth:** 5 levels, enforced in `create_folder()` with `get_folder_depth()` check
- **Folder dropdown style:** Breadcrumb (`"Reports > Q1"`) — clear hierarchy at a glance
- **New subfolder creation:** Both sidebar context menu AND PostDropPanel "+" button (context-aware)
- **Sidebar context menu also handles:** New Project (from empty space or any item), New Folder (from project item)
- **Backward compatible:** Existing flat folders remain at root level, no migration needed

## Risks / Notes
- Deep nesting could make sidebar unwieldy — mitigated by collapsible tree (Session 11)
- Folder rename/move not in scope — keep for backlog
- Windows build should be re-tested with subfolder paths (long path edge cases)
