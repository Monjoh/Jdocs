# jDocs

A lightweight cross-platform desktop app for organizing files with tagging, categorization, metadata extraction, and search.

## Features
- Drag & drop file input (single or batch up to 10 files)
- Automatic metadata extraction for Word, Excel, PowerPoint, images, CSV, and code files
- Tag files with chip-based UI and project-scoped suggestions
- Categorize and comment on files
- Search across filenames, metadata, tags, and categories
- Dark/light theme switching
- Scan for untracked files in your root folder
- Fully local — no cloud, no external APIs

## Platform Support
- Windows (user-level install, no admin rights needed)
- macOS

## Installation

### Pre-built (recommended)
Download the latest release for your platform:
- **macOS:** `jDocs.app` — right-click > Open on first launch (unsigned app)
- **Windows:** `jDocs/` folder — run `jDocs.exe` directly (no install needed)

### From Source
```bash
# Clone and set up
git clone <repo-url>
cd Jdocs
python3 -m venv .venv
source .venv/bin/activate   # macOS/Linux
# .venv\Scripts\activate    # Windows

# Install dependencies
pip install -r requirements.txt

# Run
python3 src/main.py
```

## Building from Source

### Prerequisites
- Python 3.10+
- All dependencies from `requirements.txt`
- PyInstaller (`pip install pyinstaller`)

### Build
```bash
# Standard build
python3 build.py

# Clean build (removes previous artifacts)
python3 build.py --clean
```

Output will be in `dist/`:
- **macOS:** `dist/jDocs.app`
- **Windows:** `dist/jDocs/jDocs.exe`

### Windows-specific notes
- No admin rights needed — the built `jDocs.exe` runs from any folder
- Windows antivirus may flag unsigned PyInstaller executables — add an exception if needed
- On Windows, use `python` instead of `python3` in the commands above
- Use `python build.py --clean` for a fresh build

### macOS-specific notes
- The build produces a `jDocs.app` bundle in `dist/`
- First launch: right-click > Open to bypass Gatekeeper (unsigned app)

### Build size
Approximately 95-100MB (includes PyQt5 and all dependencies).

## Running Tests
```bash
pip install pytest
python3 -m pytest tests/ -v
```

## Project Structure
See `CLAUDE.md` for full structure and context.
