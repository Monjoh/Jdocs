# Session 09 — PyInstaller Packaging & Distribution

**Date:** TBD
**Status:** Planned

## Context & Motivation

Sessions 01–08 built a fully functional, well-tested desktop app. The next step is packaging it into standalone executables so it can run on Windows and macOS without requiring Python to be installed. This is the key step to making jDocs usable as a real desktop application.

The user has no admin rights on their Windows work PC, so the .exe must run from user-space (no system-level install required). macOS has full access and is used for development/testing.

---

## Objectives

### 1. PyInstaller Configuration

#### 1a. Create `jdocs.spec` file
**Goal:** A PyInstaller spec file that bundles the app correctly.
**Details:**
- Entry point: `src/main.py`
- Include all source modules: `database.py`, `extractor.py`, `settings.py`, `utils.py`
- Hidden imports: PyQt5 submodules, `openpyxl`, `python-docx`, `python-pptx`, `PIL`
- Data files: any assets (icons, etc.) if present
- One-folder mode first (easier to debug), then attempt one-file mode

#### 1b. Handle hidden imports
**Problem:** PyInstaller's static analysis often misses dynamically imported modules. Libraries like `openpyxl`, `python-docx`, and `PIL` have submodules that may not be detected.
**Fix:** Test the build and add missing modules to `hiddenimports` in the spec file iteratively.

#### 1c. Exclude unnecessary modules
**Goal:** Keep the executable size manageable.
**Details:** Exclude test frameworks, unused Qt modules (QtWebEngine, QtMultimedia, etc.), and development tools. Document the final exe size.

### 2. Build Script

#### 2a. Create `build.py` or `build.sh`
**Goal:** A simple script that runs PyInstaller with the correct options.
**Details:**
- Cross-platform build command
- Clean build directory before rebuilding
- Print final exe location and size

### 3. Testing the Build

#### 3a. Smoke test checklist
Manual testing of the packaged app:
- [ ] App launches without errors
- [ ] First-launch wizard appears (fresh config)
- [ ] Root folder selection works
- [ ] Drag & drop accepts files
- [ ] File metadata extraction works for all supported types (.docx, .xlsx, .pptx, .png, .jpg, .csv, .py)
- [ ] Approve & Copy creates the file in the right location
- [ ] Search returns results
- [ ] Settings menu works (Change Root Folder)
- [ ] App closes cleanly

#### 3b. Error scenarios
- [ ] Launch from a path with spaces in the name
- [ ] Launch from a network/USB drive (if applicable)
- [ ] Drop a very large file (50MB+)
- [ ] Drop an unsupported file type

### 4. Platform-Specific Considerations

#### 4a. Windows
- No admin install — the exe must run directly from any folder
- Test on user's work PC (no admin rights)
- File path length limits (260 chars) — ensure root folder path + project + folder + filename stays within bounds
- `.exe` icon (optional, nice-to-have)

#### 4b. macOS
- Build `.app` bundle
- Test Gatekeeper behavior (unsigned app — may need right-click > Open)
- Retina display compatibility (PyQt5 handles this, but verify)

### 5. Documentation

#### 5a. Update README.md
- Add "Installation" section with download/build instructions
- Add "Building from Source" section

---

## Files to Create/Modify

| File | Action | Scope |
|---|---|---|
| `jdocs.spec` | **Create** | PyInstaller spec file |
| `build.py` | **Create** | Build script |
| `README.md` | Modify | Add installation and build instructions |
| `requirements.txt` | Modify | Add pyinstaller as dev dependency (or separate `requirements-dev.txt`) |

## Priority Order
1. **High:** Get a working one-folder build on the current platform (1a, 1b)
2. **Medium:** Trim size with excludes (1c), build script (2a)
3. **Low:** Icon, README updates (4a, 5a)
4. **Verify:** Smoke test checklist (3a, 3b)

## Dependencies
- `pyinstaller` must be installed (`pip install pyinstaller`)
- All existing tests should pass before packaging
- Build can only be tested on the target platform (Windows exe on Windows, macOS app on macOS)

## Known Risks
- PyInstaller exe size with PyQt5 can be 80-150MB — acceptable for a desktop app but worth monitoring
- Hidden import issues are common and require iterative debugging
- The user's Termux environment cannot build Windows .exe directly — the Windows build must happen on a Windows machine
- Antivirus on Windows may flag unsigned PyInstaller executables — document workaround (add exception)

## Estimated Scope
~1 hour session. Most time will be spent debugging hidden imports and testing the build. If the build works quickly, use remaining time for size optimization and documentation.
