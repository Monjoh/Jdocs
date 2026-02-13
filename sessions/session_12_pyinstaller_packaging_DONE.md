# Session 12 — PyInstaller Packaging & Distribution

**Date:** 2026-02-12
**Status:** In Progress

## Context & Motivation

Sessions 01–11 built a fully functional, well-tested desktop app (120 tests passing). The next step is packaging it into standalone executables so it can run on Windows and macOS without requiring Python to be installed.

The user has no admin rights on their Windows work PC, so the .exe must run from user-space (no system-level install required). macOS has full access and is used for development/testing.

---

## Completed

### 1a. Created `jdocs.spec`
- Entry point: `src/main.py` with `pathex=['src']` so sibling modules resolve
- Hidden imports: docx, openpyxl, pptx, PIL (with submodules), lxml, sqlite3, csv, json, etc.
- Excludes: 20+ unused Qt modules (WebEngine, Multimedia, Bluetooth, etc.), test frameworks, tkinter, numpy/pandas/matplotlib
- macOS: BUNDLE block creates `jDocs.app` with `NSHighResolutionCapable` and bundle identifier
- `console=False` — no terminal window on launch

### 1b. Hidden imports — worked on first try
No iterative debugging needed. PyInstaller 6.18.0 + pyinstaller-hooks-contrib handled all imports correctly.

### 1c. Size optimization
- Excluded 20+ unused Qt modules and dev tools
- Final build size: **~98 MB** (within expected 80-150MB range for PyQt5)

### 2a. Created `build.py`
- Cross-platform build script
- `--clean` flag for clean builds
- Reports output location and human-readable size

### 3a. Smoke test — app launches successfully
- Packaged app starts without import errors or crashes
- Exit code 143 (SIGTERM) confirms clean launch/shutdown

### 5a. Documentation
- Updated `README.md` with Installation, Building from Source, and Running Tests sections
- Created `requirements-dev.txt` (pytest + pyinstaller)
- Updated `.gitignore` to track `jdocs.spec`

## Files Created/Modified

| File | Action | Notes |
|---|---|---|
| `jdocs.spec` | Created | PyInstaller spec file |
| `build.py` | Created | Cross-platform build script |
| `requirements-dev.txt` | Created | Dev dependencies (pytest, pyinstaller) |
| `README.md` | Updated | Added install/build/test instructions |
| `.gitignore` | Updated | Allow tracking of jdocs.spec |

## Build Details
- PyInstaller 6.18.0
- macOS output: `dist/jDocs.app` (~98 MB)
- One-folder mode (COLLECT + BUNDLE)
- Build time: ~35 seconds

## Remaining
- Manual smoke testing by user (drag-drop, search, themes, etc.)
- Windows build must be done on Windows machine
- Optional: app icon (.icns for macOS, .ico for Windows)

## Known Issues
- macOS Gatekeeper: unsigned app requires right-click > Open on first launch
- Windows antivirus may flag unsigned PyInstaller executables
