# Session 03 — File Metadata Extraction Engine

**Date:** TBD
**Goal:** Build a module that extracts text and metadata from supported file types.
**Deliverable:** Working `src/extractor.py` module that returns extracted text and metadata for .docx, .xlsx, .pptx, and image files, with passing tests.

## Files
- `src/extractor.py` — new, extraction logic
- `tests/test_extractor.py` — new, tests with sample files
- `tests/samples/` — new, small test files for each supported type

## TODOs
- [ ] Create `src/extractor.py` with a common interface (e.g. `extract(file_path) -> dict`)
- [ ] Implement Word (.docx) extraction — text content, author, title, page count
- [ ] Implement Excel (.xlsx) extraction — sheet names, row counts, cell content sample
- [ ] Implement PowerPoint (.pptx) extraction — slide count, text from slides, author
- [ ] Implement image (.png, .jpg) extraction — dimensions, EXIF data if available
- [ ] Implement code file (.py, .js, .java, etc.) extraction — raw text content
- [ ] Create small sample test files in `tests/samples/`
- [ ] Write tests for each file type
- [ ] Verify all tests pass

## Decisions
_(To be logged during the session)_

## Notes
_(To be logged during the session)_
