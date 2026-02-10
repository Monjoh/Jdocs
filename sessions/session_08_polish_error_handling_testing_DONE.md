# Session 08 — Polish, Error Handling & Testing

**Date:** TBD
**Status:** Planned

## Context & Motivation

Sessions 01–07 built a fully functional app: drag & drop input, metadata extraction, tagging, search, persistent database, first-launch wizard, and physical file copy on approve. The app works for the happy path, but has gaps in error handling, edge cases, and test coverage that need to be addressed before packaging (Session 09).

This session focuses on making the app robust and reliable — handling what happens when things go wrong, when users do unexpected things, and ensuring every module has thorough test coverage.

---

## Objectives

### 1. Error Handling in `src/main.py`

#### 1a. Source file validation on approve
**Problem:** If the user drops a file, then deletes or moves the original before clicking Approve, `shutil.copy2` will raise `FileNotFoundError`. Currently this is caught as a generic `OSError`, but the error message isn't user-friendly.
**Fix:** Before copying, check `source.exists()` and show a specific message: "The original file no longer exists at its original location. It may have been moved or deleted."

#### 1b. Project/folder name sanitization
**Problem:** Users can create projects/folders with names containing characters that are invalid in file paths on Windows (`< > : " / \ | ? *`) or that cause issues (leading/trailing spaces, just dots, empty after strip). These names get used as directory names during file copy.
**Fix:** Add a `_sanitize_folder_name(name: str) -> str` helper that strips invalid characters and warns the user if the name was modified. Reject empty names after sanitization.

#### 1c. Database write errors during approve
**Problem:** If `db.add_file()` fails (e.g. duplicate `stored_path` from a race condition, or disk full), the file has already been copied but isn't tracked in the DB — orphaned file.
**Fix:** Wrap the approve flow in a try/except. If DB write fails, attempt to delete the copied file (cleanup), and show the user a clear error message.

#### 1d. Extractor errors on file drop
**Problem:** If extraction fails for a truly corrupt file, the error is shown in the status label but only as small gray text. Easy to miss.
**Fix:** Use `QMessageBox.warning()` for extraction errors, not just a status label update. Keep the status label update too, but make the error more visible.

#### 1e. Dropping directories
**Problem:** If a user drags a folder (not a file) onto the drop zone, `extract()` receives a directory path. `Path.stat().st_size` works on directories, but the extraction will fail oddly.
**Fix:** Check `Path.is_file()` at the start of `extract()` and return an error result for directories.

#### 1f. `QMenuBar` unused import
**Problem:** `QMenuBar` is imported but `self.menuBar()` is inherited from `QMainWindow` — the import is unused.
**Fix:** Remove it.

### 2. Error Handling in `src/extractor.py`

#### 2a. Encoding errors in code/CSV files
**Problem:** `_extract_code` and `_extract_csv` both use `errors="replace"`, which is correct. But if a binary file has a code extension (e.g. a compiled `.py` file renamed), the result could be huge garbled text.
**Fix:** Add a file size cap: if the file is larger than 10MB, only read the first 10MB for text extraction. Add a metadata note indicating truncation.

#### 2b. Empty files
**Problem:** Empty `.docx`, `.xlsx`, `.pptx` files may raise unexpected exceptions from the document libraries.
**Fix:** Add defensive checks: if a `.docx` has 0 paragraphs, `.xlsx` has 0 sheets, etc., return valid but empty results (not errors). Write tests with empty sample files.

#### 2c. Password-protected Office files
**Problem:** python-docx, openpyxl, and python-pptx will raise exceptions on password-protected files. The generic `except Exception` catches this, but the error message is cryptic (e.g. `BadZipFile`).
**Fix:** Catch the specific exceptions (`BadZipFile`, `InvalidFileException`) and return a user-friendly message: "This file appears to be password-protected or corrupted."

### 3. Error Handling in `src/database.py`

#### 3a. `stored_path` uniqueness conflict
**Problem:** The `files` table has `UNIQUE` on `stored_path`. If two files end up with the same path (shouldn't happen with duplicate handling, but could in edge cases), `add_file()` raises `sqlite3.IntegrityError` which propagates up as a generic Python exception.
**Fix:** Catch `IntegrityError` in `add_file()` and raise a clear custom error or return a meaningful message.

#### 3b. Connection handling
**Problem:** If the DB file becomes inaccessible (e.g. USB drive removed, permissions changed), all operations will fail with `sqlite3.OperationalError`. No current handling.
**Fix:** Consider adding a `is_connected()` health check method. Not critical for Session 08, but document as a consideration.

### 4. Test Coverage Expansion

#### 4a. `tests/test_main.py` — new file
Test the non-UI logic in `main.py`:
- `_format_size()`: test 0 bytes, bytes, KB boundary, MB boundary, large files
- `_format_metadata()`: test each file type branch (docx, xlsx, pptx, image, csv, code, unsupported)
- `_sanitize_folder_name()`: test invalid characters stripped, spaces trimmed, rejection of empty names (if implemented in objective 1b)

#### 4b. `tests/test_extractor.py` — additions
- Test directory path → error result (objective 2a)
- Test file size cap behavior (objective 2a)
- Test empty/minimal files (objective 2b)
- Test corrupt/invalid files → graceful error (not crash)

#### 4c. `tests/test_database.py` — additions
- Test `add_file` with duplicate `stored_path` → clear error behavior
- Test `search_files` with special SQL characters (%, _, ') — ensure no SQL injection
- Test `search_files` ordering (multi-word queries, relevance sorting)

#### 4d. `tests/test_settings.py` — additions (if needed)
- Current 13 tests are solid. May add:
  - Test `is_configured` when directory is removed between save and check
  - Test concurrent save operations (unlikely in practice, but good to know behavior)

### 5. UI Polish

#### 5a. Status bar for root folder
**Problem:** User has no visual indicator of which root folder is active.
**Fix:** Add a small label at the bottom of the sidebar or in the status bar showing the current root folder path (truncated if long).

#### 5b. Approve button text
**Problem:** Button says "Approve & Move" but the file is actually copied, not moved.
**Fix:** Change button text to "Approve & Copy" to match actual behavior.

#### 5c. Empty state in sidebar
**Problem:** When the app launches fresh (no projects yet), the sidebar is empty with no guidance.
**Fix:** Show a subtle hint like "Create a project to get started" when the project tree is empty.

---

## Files to Modify

| File | Action | Scope |
|---|---|---|
| `src/main.py` | Modify | Error handling in approve flow, name sanitization, button text fix, root folder indicator, empty sidebar hint, remove unused import |
| `src/extractor.py` | Modify | Directory check, file size cap, empty file handling, password-protected file messages |
| `src/database.py` | Modify | IntegrityError handling in add_file, SQL special character escaping in search |
| `tests/test_main.py` | **Create** | Tests for helper functions and sanitization |
| `tests/test_extractor.py` | Modify | Tests for directories, empty files, large files, corrupt files |
| `tests/test_database.py` | Modify | Tests for duplicate paths, SQL injection, search ordering |

## Priority Order
1. **High:** Source file validation (1a), directory drop check (1e), approve button text (5b) — these are user-facing bugs
2. **Medium:** Name sanitization (1b), DB error during approve (1c), encoding/size cap (2a), password-protected files (2c)
3. **Low:** Root folder indicator (5a), empty sidebar hint (5c), connection health check (3b)
4. **Tests:** Should cover everything implemented above

## Estimated Scope
This is a larger session. If it runs long, split into:
- **8A:** Error handling (objectives 1–3)
- **8B:** Test coverage (objective 4) + UI polish (objective 5)

## Dependencies
- No new dependencies needed
- All changes are internal to existing modules
- Existing 39 tests must continue to pass
