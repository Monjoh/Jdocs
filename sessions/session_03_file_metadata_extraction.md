# Session 03 — File Metadata Extraction Engine

**Date:** 2026-02-09
**Goal:** Build a module that extracts text and metadata from supported file types.
**Deliverable:** Working `src/extractor.py` module that returns extracted text and metadata for .docx, .xlsx, .pptx, and image files, with passing tests.

## Files
- `src/extractor.py` — new, extraction logic
- `tests/test_extractor.py` — new, tests with sample files
- `tests/samples/` — new, small test files for each supported type (sample.docx, sample.xlsx, sample.pptx, sample.png, sample.jpg, sample.py)

## TODOs
- [x] Create `src/extractor.py` with a common interface (`extract(file_path) -> dict`)
- [x] Implement Word (.docx) extraction — text content, author, title, paragraph count
- [x] Implement Excel (.xlsx) extraction — sheet names, row counts, cell content sample (first 50 rows per sheet)
- [x] Implement PowerPoint (.pptx) extraction — slide count, text from slides, author
- [x] Implement image (.png, .jpg) extraction — dimensions, format, mode, EXIF data if available
- [x] Implement code file (.py, .js, .java, etc.) extraction — raw text content, line/char counts
- [x] Create small sample test files in `tests/samples/`
- [x] Write tests for each file type (21 tests total)
- [x] Verify all tests pass (39/39 including database tests)

## Decisions

- **Common return format:** `extract()` always returns a dict with keys: `file_name`, `file_type`, `size_bytes`, `text`, `metadata`, `error`. This makes it predictable for downstream consumers — they can always check `error` first, then access `text` and `metadata` without guessing the shape.

- **paragraph_count instead of page_count for .docx:** python-docx doesn't expose page count (that depends on rendering/layout). We use `paragraph_count` instead, which is available directly from the document structure.

- **Excel text sampling capped at 50 rows per sheet:** To avoid loading huge spreadsheets entirely into memory. The extracted text is meant for search indexing, not full content display. 50 rows gives enough content for meaningful search results.

- **EXIF filtering to simple types only:** Only `str`, `int`, `float` EXIF values are kept. Complex EXIF entries (bytes, tuples, IFD references) are skipped to keep the metadata dict cleanly serializable for storage in SQLite.

- **Unsupported files don't error:** They return a normal result with a `note` in metadata. This way the app can still track and organize files it can't extract from, without treating them as failures.

- **Code file extensions defined as a set constant (`CODE_EXTENSIONS`):** Easy to extend later. Covers common languages plus config/data formats (.json, .yaml, .csv, .md, .txt).

## Test Coverage Details

| Test Class | Tests | What's Verified |
|-----------|-------|-----------------|
| TestDocxExtraction | 4 | Paragraph text present, author/title/paragraph_count from core properties, file_name/file_type/size_bytes populated, no error |
| TestXlsxExtraction | 4 | Cell values in text (product names, numbers), sheet_count=2, per-sheet name and row_count (Sales=3 rows, Inventory=2 rows), no error |
| TestPptxExtraction | 4 | Slide title/body in text, slide_count=2, author/title from core properties, no error |
| TestImageExtraction | 4 | PNG dimensions 200x150 + format="PNG", JPG dimensions 200x150 + format="JPEG", images return empty text, no error |
| TestCodeExtraction | 3 | Full source content in text, line_count and char_count > 0, no error |
| TestEdgeCases | 2 | Non-existent file returns error="File not found" with size_bytes=0, unsupported .xyz extension returns metadata note without crashing |

## Notes

- **Python version updated:** Mac upgraded from 3.7 to 3.10.4. Updated `learning.md` — we can now use `X | Y` union syntax and `list[dict]` lowercase generics. Minimum supported version is now 3.10+.

- **venv setup:** Created project venv with all dependencies (PyQt5, python-docx, openpyxl, python-pptx, Pillow, pytest). Already in `.gitignore`.

- **Backlog items added this session:**
  - Dark theme support (sidebar/drop zone have hardcoded light backgrounds)
  - Root folder definition and file resilience (handle external moves/renames/deletes)
