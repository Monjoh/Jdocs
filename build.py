"""
jDocs build script — packages the app using PyInstaller.

Usage:
    python3 build.py          # Build for current platform
    python3 build.py --clean  # Clean build (remove previous artifacts first)
"""

import shutil
import subprocess
import sys
from pathlib import Path


def get_size_str(path: Path) -> str:
    """Get human-readable size of a directory."""
    total = sum(f.stat().st_size for f in path.rglob('*') if f.is_file())
    if total >= 1_000_000_000:
        return f"{total / 1_000_000_000:.1f} GB"
    elif total >= 1_000_000:
        return f"{total / 1_000_000:.1f} MB"
    elif total >= 1_000:
        return f"{total / 1_000:.1f} KB"
    return f"{total} bytes"


def main():
    root = Path(__file__).parent
    spec_file = root / "jdocs.spec"
    dist_dir = root / "dist"
    build_dir = root / "build"

    if not spec_file.exists():
        print(f"Error: {spec_file} not found.")
        sys.exit(1)

    clean = "--clean" in sys.argv

    if clean:
        print("Cleaning previous build artifacts...")
        for d in [dist_dir, build_dir]:
            if d.exists():
                shutil.rmtree(d)
                print(f"  Removed {d}")

    print(f"Building jDocs with PyInstaller...")
    cmd = [
        sys.executable, "-m", "PyInstaller",
        str(spec_file),
        "--noconfirm",
    ]
    if clean:
        cmd.append("--clean")

    result = subprocess.run(cmd, cwd=str(root))
    if result.returncode != 0:
        print(f"\nBuild FAILED (exit code {result.returncode})")
        sys.exit(result.returncode)

    # Report results
    print("\n" + "=" * 50)
    print("BUILD SUCCESSFUL")
    print("=" * 50)

    if sys.platform == "darwin":
        app_path = dist_dir / "jDocs.app"
        if app_path.exists():
            print(f"  macOS app:  {app_path}")
            print(f"  Size:       {get_size_str(app_path)}")
    else:
        exe_path = dist_dir / "jDocs" / ("jDocs.exe" if sys.platform == "win32" else "jDocs")
        folder_path = dist_dir / "jDocs"
        if folder_path.exists():
            print(f"  Output:     {folder_path}")
            print(f"  Executable: {exe_path}")
            print(f"  Size:       {get_size_str(folder_path)}")

    print()


if __name__ == "__main__":
    main()
