# Session 06 — Search Functionality

**Date:** 2026-02-09
**Goal:** Make the search bar functional — user types a query and sees matching files across filenames, extracted text/metadata, and tags.
**Deliverable:** Working search with results displayed as clickable cards, file detail view with back navigation.

## Context & Dependencies

The search bar existed since Session 01 but did nothing. The database has files with `original_name`, `metadata_text` (extracted content), and tags stored via the `file_tags` junction table. This session wires the search bar to query across all of these and display results.

**Data flow:** User types query + presses Enter → `db.search_files(query)` → SearchResultsPanel shows clickable cards → clicking a card opens FileDetailPanel with full file info → "Back to Results" returns to the result list → "Clear Search" returns to DropZone.

**Modules modified:**
- `src/database.py` — added `search_files()` method
- `src/main.py` — added SearchResultsPanel, FileDetailPanel, search signal wiring
- `tests/test_database.py` — added 8 search tests

## TODOs

### 1. Add search_files() method to database
- [x] Searches across `files.original_name`, `files.metadata_text`, `files.file_type`, and `tags.name`
- [x] Uses SQL LIKE with `%query%` wildcards, `COLLATE NOCASE` for case-insensitive matching
- [x] JOINs through folders → projects to include `project_name` and `folder_name` in results
- [x] LEFT JOINs through `file_tags` → `tags` to match on tag names
- [x] Uses `SELECT DISTINCT` to deduplicate files that match on multiple criteria
- [x] Orders results by `created_at DESC` (most recently added first)
- [x] Each result is enriched with its tags list via `get_file_tags()`
- [x] Empty/whitespace queries return empty list (no accidental "match everything")

### 2. Build SearchResultsPanel
- [x] Header bar with result count ("3 matches for 'finance'") and "Clear Search" button
- [x] Scrollable area with clickable result cards
- [x] Each card shows: filename (bold), file type + size + project/folder path, tags (in blue)
- [x] Cards have hover effect (light blue background, blue border) for visual feedback
- [x] Clicking a card emits `result_clicked(dict)` signal with the file record
- [x] Empty results show centered "No results found for [query]" message

### 3. Build FileDetailPanel
- [x] Read-only panel showing full file details: name, type, size, project/folder location, tags, comments
- [x] Stored text content preview (first 500 chars of `metadata_text`) in a styled box
- [x] Sections hidden when empty (no tags → hide tags label, no comments → hide comments, no text → hide preview)
- [x] "Back to Results" button pinned at bottom (outside scroll area, same pattern as PostDropPanel)

### 4. Connect search bar and wire navigation
- [x] Search triggers on Enter key press (`returnPressed` signal) — not on every keystroke
- [x] Empty search bar + Enter returns to DropZone (clears search)
- [x] QStackedWidget now has 4 pages: DropZone (0), PostDropPanel (1), SearchResultsPanel (2), FileDetailPanel (3)
- [x] Status label updates to show search state ("Found 3 results for 'finance'", "Viewing: report.xlsx")

### 5. Testing
- [x] 8 new search tests added to `tests/test_database.py`
- [x] Full test suite: 54 tests passing (26 database + 28 extractor)
- [x] App launches successfully

## Test Coverage for search_files()

| Test | What's Verified |
|------|-----------------|
| `test_search_by_filename` | Matches on `original_name` substring, case-insensitive (both "quarterly" and "QUARTERLY" find the same file) |
| `test_search_by_metadata_text` | Matches on `metadata_text` content (e.g. "Engineering" found in CSV extracted text) |
| `test_search_by_tag` | Matches on tag names, result includes the matching tag in the `tags` list |
| `test_search_by_file_type` | Matches on `file_type` extension (e.g. ".py" finds Python files but not .md files) |
| `test_search_deduplication` | File matching on filename + metadata_text + tag for same query appears only once (DISTINCT) |
| `test_search_includes_project_and_folder` | Results include `project_name` and `folder_name` from joined tables |
| `test_search_empty_query` | Empty string and whitespace-only queries return empty list |
| `test_search_no_matches` | Query with no matches returns empty list (not an error) |

## Decisions

- **SQL LIKE instead of FTS5:** For the current scale (desktop app, hundreds to low thousands of files), `LIKE '%query%'` with `COLLATE NOCASE` is fast enough and requires no additional setup. SQLite FTS5 (Full-Text Search) would be faster for large datasets and support ranked results — added to backlog for later if needed.

- **Search on Enter, not on every keystroke:** Avoids excessive DB queries while typing. The user presses Enter to execute the search. This is the standard pattern for search bars in desktop apps.

- **Results enriched with tags via N+1 queries:** Each result calls `get_file_tags()` individually. For the expected result set size (tens of results at most), this is fast enough. If it becomes slow, we can batch-fetch tags in a single query.

- **QStackedWidget expanded to 4 pages:** Rather than destroying/recreating panels, we keep all 4 views in the stack and switch between them. This makes navigation fast (no widget reconstruction) and allows "Back to Results" to return to the exact state the user left.

- **FileDetailPanel shows metadata_text, not re-extracted metadata:** Since the file detail is accessed from search results (database records), we show the stored `metadata_text` rather than calling the extractor again. This is faster and works even if the original file has been moved or deleted.

- **Card-based result layout with hover effects:** Each result is a QFrame styled as a card with hover highlighting. This gives clear visual affordance that results are clickable without needing explicit buttons.

## Notes

- **Search is across ALL columns simultaneously:** A single query like "finance" will match files named "finance_report.xlsx", files containing "finance" in their extracted text, AND files tagged with "finance". This gives the broadest useful results from a single search.

- **Clear Search returns to DropZone:** The "Clear Search" button and pressing Enter with an empty search bar both return to the default DropZone view, ready for new file input.

- **No search history or recent searches:** Kept simple for now. Search is stateless — each Enter press runs a fresh query. Search history could be added later.
