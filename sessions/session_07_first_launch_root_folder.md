# Session 07 — First Launch Setup & Root Folder Config

**Date:** 2026-02-10
**Status:** In Progress

## Objectives
1. Create `src/settings.py` — config persistence module (JSON, cross-platform)
2. Add `FirstLaunchDialog` to `src/main.py` — first-run wizard
3. Switch to persistent database (`<root>/.jdocs/jdocs.db`)
4. Physical file copy on approve (`shutil.copy2` to root/project/folder/)
5. Add "Change Root Folder" menu option
6. Create `tests/test_settings.py`

## Context & Motivation
Before this session, the app used `Database(":memory:")` — all data was lost on exit. Session 05 explicitly deferred physical file moves: "stored_path records original file location — physical move deferred to Session 07 root folder setup." This session makes jDocs a real, persistent file organizer for the first time.

---

## What Was Built

### `src/settings.py` — Config persistence (new file)

A standalone module with no UI dependencies. Handles reading/writing a JSON config file in the platform-appropriate user data directory.

**Functions:**
- `get_config_dir() -> Path` — Returns where config lives:
  - **Windows:** `Path.home() / "AppData" / "Local" / "jdocs"` (i.e. `%LOCALAPPDATA%\jdocs`)
  - **macOS/Linux:** `Path.home() / ".config" / "jdocs"`
  - Uses `platform.system()` to detect OS, not `sys.platform` (cleaner string matching: `"Windows"` vs `"win32"`)
- `load_settings() -> dict` — Reads `config.json` from config dir. If file missing, returns defaults (`{"root_folder": "", "db_path": ""}`). If file is corrupt JSON, also returns defaults (graceful recovery). Merges loaded data with defaults so new config keys added in future versions are always present.
- `save_settings(settings: dict)` — Writes dict to `config.json` with `indent=2` for human readability. Creates parent directories with `mkdir(parents=True, exist_ok=True)`.
- `derive_db_path(root_folder: str) -> str` — Returns `<root_folder>/.jdocs/jdocs.db`. The `.jdocs/` hidden directory keeps the database out of the user's way. This is auto-called during first launch setup.
- `is_configured(settings: dict) -> bool` — Returns True only if `root_folder` is non-empty AND the directory actually exists on disk. This is the check that triggers the first-launch wizard.

**Design notes:**
- Config and DB are separate locations by design. Config is in the OS user data dir (so the app always knows where to find it). DB is inside the root folder (so it travels with the data if the user moves the root folder to a USB drive, different machine, etc.).
- `_defaults()` is a private function that returns a fresh dict each time (not a module-level constant) to avoid accidental mutation.

### `src/main.py` — Major changes (modified file)

**New imports:** `shutil` (for file copy), `QAction`/`QDialog`/`QMenuBar` (for menu bar and dialog), `settings` module functions.

#### 1. `FirstLaunchDialog(QDialog)` — new class
- Shown when `is_configured()` returns False (no config file, or root folder doesn't exist)
- UI: welcome label, explanation text (what root folder is for), folder picker row (label + Browse button), confirm button
- Browse button calls `QFileDialog.getExistingDirectory()` — native OS folder picker
- Confirm button is disabled until a folder is selected (prevents empty selection)
- Dialog is modal — `dialog.exec_()` blocks the app. If user closes/cancels, the app exits (`sys.exit(0)`)
- Located in `main.py` above the widget classes, before `DropZone`

#### 2. `MainWindow.__init__` — persistent DB flow
Old flow: `Database(":memory:")` → `_seed_sample_data()` → hardcoded projects/folders
New flow:
1. `load_settings()` — read config from disk
2. `is_configured(settings)` — check if root folder exists
3. If not configured → `_run_first_launch()` → show `FirstLaunchDialog`
4. On dialog accept: `derive_db_path()`, save settings, create `.jdocs/` dir
5. `Database(db_path)` — open persistent SQLite file
6. Sidebar loads from DB (empty on first launch, populated on subsequent launches)

Added a **menu bar** with `Settings > Change Root Folder...` action.

#### 3. `_run_first_launch() -> bool` — new method
- Instantiates `FirstLaunchDialog`, calls `exec_()`
- On accept: derives DB path, saves settings, creates `.jdocs/` directory
- Returns True if user selected a folder, False if they cancelled (app exits)

#### 4. `_on_change_root_folder()` — new method
- Opens `QFileDialog.getExistingDirectory()` for new root
- Shows `QMessageBox.question()` confirmation: warns that this creates a new DB and old data stays in old location
- On confirm: updates settings, creates new `.jdocs/` dir, shows "restart required" info box
- Does NOT hot-swap the DB connection (would require re-initializing all widgets, too complex for the benefit)

#### 5. `_on_approve()` — updated method (file copy logic)
Old: saved `stored_path` as the original source path (the file wasn't actually moved)
New:
1. Looks up project name and folder name from DB (`db.get_project()`, `db.get_folder()`)
2. Builds target directory: `root_folder / project_name / folder_name`
3. Creates directory tree with `Path.mkdir(parents=True, exist_ok=True)`
4. Checks for duplicate filenames at target. If `report.xlsx` exists, tries `report_1.xlsx`, `report_2.xlsx`, etc.
5. Copies file with `shutil.copy2()` (preserves timestamps, permissions). Original stays in place.
6. On copy failure (e.g. permission denied, disk full): shows `QMessageBox.warning()` and returns without saving to DB
7. Saves `stored_path` as the **destination** path (inside root folder), not the original source

#### 6. Removed `_seed_sample_data()` — deleted method
No longer needed. The app starts with an empty database. Users create projects/folders via the "+" buttons.

### `tests/test_settings.py` — 13 tests (new file)

Uses `unittest.mock.patch` to override `get_config_dir()` and `platform.system()` so tests don't touch real config directories.

**TestGetConfigDir (3 tests):**
- `test_windows_path` — patches `platform.system` to `"Windows"`, verifies path ends with `AppData/Local/jdocs`
- `test_macos_path` — patches to `"Darwin"`, verifies `.config/jdocs`
- `test_linux_path` — patches to `"Linux"`, verifies `.config/jdocs`

**TestLoadSaveSettings (5 tests):**
- `test_load_returns_defaults_when_no_file` — no config file → returns `{"root_folder": "", "db_path": ""}`
- `test_save_and_load_roundtrip` — save then load, values preserved
- `test_save_creates_directories` — config dir doesn't exist, save creates it
- `test_load_handles_corrupt_json` — writes broken JSON to config, load returns defaults (no crash)
- `test_load_merges_with_defaults` — config file with only `root_folder` set, `db_path` still present after load

**TestDeriveDbPath (2 tests):**
- `test_derives_path` — Unix-style path
- `test_windows_style_path` — Windows-style path with backslashes

**TestIsConfigured (3 tests):**
- `test_empty_root_is_not_configured` — empty string → False
- `test_nonexistent_dir_is_not_configured` — path doesn't exist → False
- `test_existing_dir_is_configured` — real temp directory → True

---

## Decisions & Rationale

| Decision | Why |
|---|---|
| **Copy, not move** | Never delete user's source files. The original stays where it was. If the root folder is lost, the user still has originals. |
| **DB inside root folder** (`<root>/.jdocs/jdocs.db`) | DB travels with the data. User can move root folder to USB/cloud/new machine and everything works. Config file just points to the root. |
| **Config in OS user data dir** | App always knows where to find config regardless of root folder location. Standard OS convention. |
| **Duplicate filenames get `_1`, `_2` suffix** | Prevents silent overwrites. User can see both versions. Simpler than prompting the user each time. |
| **Change root = restart** | Hot-swapping the DB would require reinitializing MainWindow, sidebar, all panels. Not worth the complexity for a rare operation. |
| **`is_configured()` checks directory exists** | Handles edge case where user deletes the root folder — app re-shows the wizard instead of crashing. |
| **JSON config (not SQLite, not INI)** | Human-readable, easy to debug, standard Python `json` module, no extra dependencies. Only 2 fields right now. |
| **`shutil.copy2` not `shutil.copy`** | `copy2` preserves file metadata (timestamps, permissions). Important for document organization. |

## Challenges & Notes
- **pytest not installed in Termux environment** — had to use `python -m unittest` instead. Tests import path is set via `sys.path.insert(0, ...)` in each test file. This pattern works with both pytest and unittest.
- **No `QAction` or `QDialog` in original imports** — had to add them when introducing the menu bar and first-launch dialog. The import block in `main.py` is growing; future sessions should watch for unused imports during cleanup.

## File Inventory

| File | Action | Lines changed |
|---|---|---|
| `src/settings.py` | **Created** | 59 lines — config persistence module |
| `src/main.py` | **Modified** | ~80 lines changed — new imports, FirstLaunchDialog class, persistent DB init, file copy in approve, menu bar, removed seed data |
| `tests/test_settings.py` | **Created** | 93 lines — 13 tests for settings module |
| `sessions/session_07_first_launch_root_folder.md` | **Created** | This file |

## Test Results
- 13 new settings tests: **all pass**
- 26 existing database tests: **all pass** (unchanged, still use `:memory:` DB independently)
- **39 total tests passing**

## Manual Testing Checklist
- [ ] Delete `~/.config/jdocs/config.json`, launch app → first-launch dialog should appear
- [ ] Select a root folder → `.jdocs/` dir created with `jdocs.db` inside
- [ ] Relaunch → app starts directly (no wizard), data from previous session persists
- [ ] Create project + folder via "+" buttons → directories appear under root folder
- [ ] Drop a file, approve → file physically copied to `root/project/folder/`
- [ ] Drop same file again → copied as `filename_1.ext` (no overwrite)
- [ ] Search finds the saved file by name, tags, or metadata
- [ ] Settings > Change Root Folder → confirmation dialog, restart prompt
