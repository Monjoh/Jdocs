"""Pure utility functions for jDocs — no Qt dependencies, safe to import anywhere."""

# Characters invalid in Windows file/folder names
_INVALID_PATH_CHARS = '<>:"/\\|?*'


def sanitize_name(name: str) -> str:
    """Strip characters that are invalid in file paths (Windows-safe).

    Returns the sanitized name, or empty string if nothing remains.
    """
    cleaned = name.strip()
    for ch in _INVALID_PATH_CHARS:
        cleaned = cleaned.replace(ch, "")
    # Remove leading/trailing dots and spaces (problematic on Windows)
    cleaned = cleaned.strip(". ")
    return cleaned


def format_size(size_bytes: int) -> str:
    """Format a byte count into a human-readable string."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    else:
        return f"{size_bytes / (1024 * 1024):.1f} MB"


def format_metadata(result: dict) -> str:
    """Build a human-readable string from type-specific metadata."""
    meta = result.get("metadata", {})
    file_type = result.get("file_type", "")
    lines = []

    if file_type == ".docx":
        if meta.get("author"):
            lines.append(f'Author: {meta["author"]}')
        if meta.get("title"):
            lines.append(f'Title: {meta["title"]}')
        lines.append(f'Paragraphs: {meta.get("paragraph_count", "?")}')

    elif file_type == ".xlsx":
        lines.append(f'Sheets: {meta.get("sheet_count", "?")}')
        for sheet in meta.get("sheets", []):
            lines.append(f'  - {sheet["name"]}: {sheet["row_count"]} rows')

    elif file_type == ".pptx":
        if meta.get("author"):
            lines.append(f'Author: {meta["author"]}')
        if meta.get("title"):
            lines.append(f'Title: {meta["title"]}')
        lines.append(f'Slides: {meta.get("slide_count", "?")}')

    elif file_type in {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tiff"}:
        w = meta.get("width", "?")
        h = meta.get("height", "?")
        lines.append(f'Dimensions: {w} x {h}')
        if meta.get("format"):
            lines.append(f'Format: {meta["format"]}')
        if meta.get("mode"):
            lines.append(f'Color mode: {meta["mode"]}')
        exif = meta.get("exif", {})
        if exif:
            lines.append("EXIF:")
            for key, val in list(exif.items())[:5]:
                lines.append(f'  {key}: {val}')

    elif file_type == ".csv":
        lines.append(f'Rows: {meta.get("total_rows", "?")}')
        lines.append(f'Columns: {meta.get("column_count", "?")}')
        columns = meta.get("columns", [])
        if columns:
            # Show up to 10 column names to avoid overflow
            shown = columns[:10]
            col_str = ", ".join(shown)
            if len(columns) > 10:
                col_str += f", ... (+{len(columns) - 10} more)"
            lines.append(f'Column names: {col_str}')
        lines.append(f'Preview: first {meta.get("preview_rows", "?")} rows')

    elif file_type in {".py", ".js", ".ts", ".java", ".c", ".cpp", ".md", ".txt", ".json"}:
        lines.append(f'Lines: {meta.get("line_count", "?")}')
        lines.append(f'Characters: {meta.get("char_count", "?")}')

    else:
        note = meta.get("note", "No metadata available for this file type.")
        lines.append(note)

    return "\n".join(lines) if lines else "No metadata extracted."
