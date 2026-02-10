"""Config persistence for jDocs — stores settings as JSON in a platform-appropriate location."""

import json
import platform
from pathlib import Path


def get_config_dir() -> Path:
    """Return the platform-appropriate config directory for jDocs."""
    system = platform.system()
    if system == "Windows":
        base = Path.home() / "AppData" / "Local"
    else:
        base = Path.home() / ".config"
    return base / "jdocs"


def _config_path() -> Path:
    return get_config_dir() / "config.json"


def _defaults() -> dict:
    return {"root_folder": "", "db_path": ""}


def load_settings() -> dict:
    """Load settings from config file. Returns defaults if file doesn't exist."""
    path = _config_path()
    if not path.exists():
        return _defaults()
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        # Merge with defaults so new keys are always present
        merged = _defaults()
        merged.update(data)
        return merged
    except (json.JSONDecodeError, OSError):
        return _defaults()


def save_settings(settings: dict):
    """Save settings dict to config file, creating directories as needed."""
    path = _config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(settings, f, indent=2)


def derive_db_path(root_folder: str) -> str:
    """Derive the database path from a root folder: <root>/.jdocs/jdocs.db"""
    return str(Path(root_folder) / ".jdocs" / "jdocs.db")


def is_configured(settings: dict) -> bool:
    """Check if settings have a valid root folder configured."""
    root = settings.get("root_folder", "")
    return bool(root) and Path(root).is_dir()
