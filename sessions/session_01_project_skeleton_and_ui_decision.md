# Session 01 — Project Skeleton & UI Framework Decision

**Date:** 2026-02-09
**Goal:** Choose the UI framework, set up project dependencies, create the app entry point with a basic window.

## TODOs
- [x] Decide: PyQt5 vs CustomTkinter
- [x] Create `requirements.txt` with all planned dependencies
- [x] Create `src/main.py` — app entry point with basic window
- [x] Create basic layout skeleton (drag zone placeholder, search bar placeholder, sidebar placeholder)
- [ ] Verify the app launches and displays the window (needs testing on Windows/Mac)

## Decisions
- **UI Framework: PyQt5** — Better drag & drop support (built-in), more flexible layouts, mature widget ecosystem. Tradeoff is larger exe size (~80-150MB vs ~30-50MB) but worth it for jDocs' needs.

## Notes
- Syntax verified on Android/Termux — no GUI display available here
- User should test on macOS or Windows: `pip install -r requirements.txt && python src/main.py`
- Layout structure: search bar (top) > sidebar (left, 200px fixed) + main panel (drop zone + file info placeholder)
- All placeholders are ready to be replaced with real functionality in later sessions
