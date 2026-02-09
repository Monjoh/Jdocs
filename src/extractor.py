"""File metadata extraction engine for jDocs.

Extracts text content and metadata from supported file types:
- Word (.docx)
- Excel (.xlsx)
- PowerPoint (.pptx)
- Images (.png, .jpg, .jpeg)
- Code files (.py, .js, .java, .ts, .c, .cpp, .html, .css, .json, .xml, .md, .txt)
"""

from pathlib import Path

from docx import Document as DocxDocument
from openpyxl import load_workbook
from PIL import Image
from PIL.ExifTags import TAGS
from pptx import Presentation


# File extensions recognized as plain-text code/config files
CODE_EXTENSIONS = {
    ".py", ".js", ".ts", ".java", ".c", ".cpp", ".h", ".hpp",
    ".html", ".css", ".json", ".xml", ".yaml", ".yml",
    ".md", ".txt", ".csv", ".sh", ".bat", ".ps1",
    ".rb", ".go", ".rs", ".swift", ".kt",
}


def extract(file_path: str | Path) -> dict:
    """Extract text and metadata from a file.

    Returns a dict with keys:
        - file_name: original filename
        - file_type: extension (e.g. ".docx")
        - size_bytes: file size
        - text: extracted text content
        - metadata: dict of type-specific metadata
        - error: error message if extraction failed, else None
    """
    path = Path(file_path)

    if not path.exists():
        return _error_result(path, "File not found")

    ext = path.suffix.lower()
    base = {
        "file_name": path.name,
        "file_type": ext,
        "size_bytes": path.stat().st_size,
        "text": "",
        "metadata": {},
        "error": None,
    }

    try:
        if ext == ".docx":
            _extract_docx(path, base)
        elif ext == ".xlsx":
            _extract_xlsx(path, base)
        elif ext == ".pptx":
            _extract_pptx(path, base)
        elif ext in {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tiff"}:
            _extract_image(path, base)
        elif ext in CODE_EXTENSIONS:
            _extract_code(path, base)
        else:
            base["metadata"]["note"] = "Unsupported file type — no extraction performed"
    except Exception as e:
        base["error"] = f"Extraction failed: {e}"

    return base


def _error_result(path: Path, message: str) -> dict:
    return {
        "file_name": path.name,
        "file_type": path.suffix.lower(),
        "size_bytes": 0,
        "text": "",
        "metadata": {},
        "error": message,
    }


def _extract_docx(path: Path, result: dict):
    doc = DocxDocument(str(path))
    paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
    result["text"] = "\n".join(paragraphs)

    props = doc.core_properties
    result["metadata"] = {
        "author": props.author or "",
        "title": props.title or "",
        "paragraph_count": len(paragraphs),
    }


def _extract_xlsx(path: Path, result: dict):
    wb = load_workbook(str(path), read_only=True, data_only=True)
    sheet_info = []
    all_text = []

    for sheet_name in wb.sheetnames:
        ws = wb[sheet_name]
        rows = list(ws.iter_rows(values_only=True))
        row_count = len(rows)
        sheet_info.append({"name": sheet_name, "row_count": row_count})

        # Collect text from first 50 rows as a sample
        for row in rows[:50]:
            for cell in row:
                if cell is not None:
                    all_text.append(str(cell))

    wb.close()
    result["text"] = "\n".join(all_text)
    result["metadata"] = {
        "sheet_count": len(wb.sheetnames),
        "sheets": sheet_info,
    }


def _extract_pptx(path: Path, result: dict):
    prs = Presentation(str(path))
    slide_texts = []

    for slide in prs.slides:
        parts = []
        for shape in slide.shapes:
            if shape.has_text_frame:
                for paragraph in shape.text_frame.paragraphs:
                    text = paragraph.text.strip()
                    if text:
                        parts.append(text)
        slide_texts.append("\n".join(parts))

    result["text"] = "\n\n".join(slide_texts)

    props = prs.core_properties
    result["metadata"] = {
        "author": props.author or "",
        "title": props.title or "",
        "slide_count": len(prs.slides),
    }


def _extract_image(path: Path, result: dict):
    img = Image.open(path)
    result["metadata"] = {
        "width": img.width,
        "height": img.height,
        "format": img.format,
        "mode": img.mode,
    }

    # Try to extract EXIF data
    exif_data = {}
    try:
        raw_exif = img.getexif()
        if raw_exif:
            for tag_id, value in raw_exif.items():
                tag_name = TAGS.get(tag_id, str(tag_id))
                # Only keep simple serializable values
                if isinstance(value, (str, int, float)):
                    exif_data[tag_name] = value
    except Exception:
        pass

    if exif_data:
        result["metadata"]["exif"] = exif_data

    img.close()


def _extract_code(path: Path, result: dict):
    text = path.read_text(encoding="utf-8", errors="replace")
    result["text"] = text
    result["metadata"] = {
        "line_count": text.count("\n") + 1 if text else 0,
        "char_count": len(text),
    }
