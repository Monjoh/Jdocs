# Session 09 — Multi-file Batch Upload & Folder Scanning

**Date:** 2026-02-10
**Status:** In Progress

## Context & Motivation

Sessions 01–08 built a fully functional single-file workflow. Two common real-world scenarios are missing:
1. **Batch upload:** Users often have multiple files to organize into the same project/folder with the same tags — doing them one-by-one is tedious.
2. **Folder scanning:** Users may copy files directly into the root folder without going through the app, leaving those files untracked in the database.

---

## Objectives

### 1. Multi-file Batch Upload

#### 1a. DropZone — accept multiple files
**Current:** `dropEvent` takes only `urls[0]`; `mousePressEvent` uses `getOpenFileName` (singular).
**Change:** Capture all dropped URLs; switch to `getOpenFileNames` (plural). New signal `files_dropped = pyqtSignal(list)` replaces `file_dropped`.

#### 1b. File count limit
**Cap:** 10 files per batch. If more are dropped, show a warning and reject the batch (don't silently truncate).

#### 1c. PostDropPanel — batch mode
**Change:** When multiple files are provided, show:
- "X files selected" header with a list of filenames and sizes
- Shared project/folder/tags/comment fields (same as today)
- Extraction runs on each file individually (for DB metadata_text) but detailed metadata preview is hidden in batch mode
- Approve button copies and registers all files

#### 1d. Approve flow — batch processing
**Change:** Loop through all files: copy each to target folder, register in DB, apply shared tags/comment. If one file fails (e.g. already deleted), continue with the rest and report failures at the end.

### 2. Folder Scanning

#### 2a. Database helper — get all tracked paths
**New method:** `get_all_stored_paths()` returns a set of all `stored_path` values for fast lookup.

#### 2b. Scan function
**New utility:** Walk the root folder tree, skip `.jdocs/` directory, compare each file path against tracked paths. Return list of untracked files with name, relative path, and size.

#### 2c. UI — scan action and results
**New:** "Scan for Untracked Files" menu item under Settings (or a dedicated button). Results shown in a dialog listing untracked files. Informational only for now (no import action from scan — that's a future enhancement).

---

## Files to Modify

| File | Action | Scope |
|---|---|---|
| `src/main.py` | Modify | DropZone multi-file, PostDropPanel batch mode, approve loop, scan menu item + dialog |
| `src/database.py` | Modify | Add `get_all_stored_paths()` |
| `src/utils.py` | Modify | Add `scan_untracked_files()` |
| `tests/test_database.py` | Modify | Test `get_all_stored_paths()` |
| `tests/test_main.py` | Modify | Test scan logic |

## Priority Order
1. **High:** Multi-file drop + batch approve (1a–1d) — core new feature
2. **Medium:** Folder scanning (2a–2c) — useful utility
3. **Tests:** Cover new functionality

## Dependencies
- No new dependencies needed
- All existing tests must continue to pass
