"""Tests for the file metadata extraction engine.

Each test group validates that extract() correctly handles a specific file type,
returning the expected text content, metadata fields, and no errors.
Edge cases cover missing files and unsupported extensions.
"""

from pathlib import Path

import pytest

from src.extractor import extract

SAMPLES = Path(__file__).parent / "samples"


class TestDocxExtraction:
    """Word .docx extraction: text paragraphs + core properties (author, title, paragraph_count)."""

    def test_text_contains_paragraphs(self):
        """Verify extracted text includes the paragraph content we wrote to the sample."""
        result = extract(SAMPLES / "sample.docx")
        assert "Hello from jDocs" in result["text"]
        assert "test document for metadata extraction" in result["text"]

    def test_metadata_fields(self):
        """Verify author, title, and paragraph_count are extracted from core properties."""
        result = extract(SAMPLES / "sample.docx")
        assert result["metadata"]["author"] == "Test Author"
        assert result["metadata"]["title"] == "Test Document"
        assert result["metadata"]["paragraph_count"] == 2

    def test_no_error(self):
        """A valid .docx should produce no extraction error."""
        result = extract(SAMPLES / "sample.docx")
        assert result["error"] is None

    def test_file_info(self):
        """Verify basic file info fields (name, type, size) are populated."""
        result = extract(SAMPLES / "sample.docx")
        assert result["file_name"] == "sample.docx"
        assert result["file_type"] == ".docx"
        assert result["size_bytes"] > 0


class TestXlsxExtraction:
    """Excel .xlsx extraction: cell text content + sheet metadata (count, names, row counts)."""

    def test_text_contains_cell_values(self):
        """Verify extracted text includes values from spreadsheet cells."""
        result = extract(SAMPLES / "sample.xlsx")
        assert "Widget A" in result["text"]
        assert "250" in result["text"]

    def test_sheet_count(self):
        """Verify the workbook reports exactly 2 sheets."""
        result = extract(SAMPLES / "sample.xlsx")
        assert result["metadata"]["sheet_count"] == 2

    def test_sheet_details(self):
        """Verify each sheet entry has the correct name and row count.
        Sales has 3 rows (header + 2 data), Inventory has 2 rows (header + 1 data)."""
        result = extract(SAMPLES / "sample.xlsx")
        sheets = result["metadata"]["sheets"]
        sales = next(s for s in sheets if s["name"] == "Sales")
        inventory = next(s for s in sheets if s["name"] == "Inventory")
        assert sales["row_count"] == 3
        assert inventory["row_count"] == 2

    def test_no_error(self):
        result = extract(SAMPLES / "sample.xlsx")
        assert result["error"] is None


class TestPptxExtraction:
    """PowerPoint .pptx extraction: slide text + core properties (author, title, slide_count)."""

    def test_text_contains_slide_content(self):
        """Verify extracted text includes title and body text from slides."""
        result = extract(SAMPLES / "sample.pptx")
        assert "Welcome to jDocs" in result["text"]
        assert "A test presentation" in result["text"]

    def test_slide_count(self):
        """Verify metadata reports exactly 2 slides."""
        result = extract(SAMPLES / "sample.pptx")
        assert result["metadata"]["slide_count"] == 2

    def test_author_and_title(self):
        """Verify author and title are extracted from presentation core properties."""
        result = extract(SAMPLES / "sample.pptx")
        assert result["metadata"]["author"] == "Slide Author"
        assert result["metadata"]["title"] == "Test Presentation"

    def test_no_error(self):
        result = extract(SAMPLES / "sample.pptx")
        assert result["error"] is None


class TestImageExtraction:
    """Image extraction: dimensions, format, mode. No text content expected."""

    def test_png_dimensions(self):
        """Verify PNG reports correct width=200 and height=150 matching creation params."""
        result = extract(SAMPLES / "sample.png")
        assert result["metadata"]["width"] == 200
        assert result["metadata"]["height"] == 150
        assert result["metadata"]["format"] == "PNG"

    def test_jpg_dimensions(self):
        """Verify JPG reports same dimensions and JPEG format."""
        result = extract(SAMPLES / "sample.jpg")
        assert result["metadata"]["width"] == 200
        assert result["metadata"]["height"] == 150
        assert result["metadata"]["format"] == "JPEG"

    def test_no_text_for_images(self):
        """Images should return empty text since they have no textual content."""
        result = extract(SAMPLES / "sample.png")
        assert result["text"] == ""

    def test_no_error(self):
        result = extract(SAMPLES / "sample.png")
        assert result["error"] is None


class TestCodeExtraction:
    """Code file extraction: full raw text + line/char counts."""

    def test_text_is_full_content(self):
        """Verify the entire file content is returned as text."""
        result = extract(SAMPLES / "sample.py")
        assert "def hello():" in result["text"]
        assert 'return "Hello from jDocs"' in result["text"]

    def test_line_and_char_count(self):
        """Verify line_count and char_count reflect the actual file content."""
        result = extract(SAMPLES / "sample.py")
        assert result["metadata"]["line_count"] > 0
        assert result["metadata"]["char_count"] > 0

    def test_no_error(self):
        result = extract(SAMPLES / "sample.py")
        assert result["error"] is None


class TestEdgeCases:
    """Edge cases: missing files and unsupported file types should not crash."""

    def test_nonexistent_file(self):
        """A path that doesn't exist should return an error message, not raise an exception."""
        result = extract(SAMPLES / "does_not_exist.docx")
        assert result["error"] == "File not found"
        assert result["size_bytes"] == 0

    def test_unsupported_extension(self):
        """An unsupported extension should return a result with a note, not crash."""
        # Create a temporary file with an unknown extension
        tmp = SAMPLES / "temp_test.xyz"
        tmp.write_text("some content")
        try:
            result = extract(tmp)
            assert result["error"] is None
            assert "Unsupported" in result["metadata"].get("note", "")
            assert result["text"] == ""
        finally:
            tmp.unlink()
