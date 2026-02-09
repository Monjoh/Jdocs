# Session 02 — Database Schema & Core Data Layer

**Date:** 2026-02-09
**Goal:** Design the SQLite database schema and build the core data access layer for jDocs.
**Deliverable:** Working `src/database.py` module with CRUD operations and passing tests.

## TODOs
- [x] Design database schema (tables: files, projects, folders, tags, categories) — see plan.md ER diagram
- [x] Create `src/database.py` — DB initialization and connection management
- [x] Implement CRUD operations for projects and folders
- [x] Implement CRUD operations for files (register, update, delete)
- [x] Implement tagging and category assignment
- [x] Write basic tests for the data layer (18 tests, all passing)

## Decisions
- **Foreign keys with CASCADE deletes** — deleting a project removes all its folders, files, tags, and comments automatically
- **Tags & categories use INSERT OR IGNORE** — creating a duplicate tag/category is a no-op, returns existing ID
- **Folder uniqueness** — UNIQUE constraint on (project_id, name, parent_folder_id) prevents duplicate folder names at the same level
- **Row factory = sqlite3.Row** — allows dict-like access to query results

## Notes
- `metadata_text` column is TEXT (will store extracted content from Session 03)
- Indexes added on files(folder_id), files(file_type), folders(project_id) for search performance
- DB path is passed in at init — the app will decide where to store it (Session 07)
- All 18 tests run against temp DB files that are cleaned up after each test
