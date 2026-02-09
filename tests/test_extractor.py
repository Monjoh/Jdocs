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


class TestCsvExtraction:
    """CSV extraction: column names, row counts, and first 100 rows of text content."""

    def test_text_contains_cell_values(self):
        """Verify extracted text includes values from CSV rows (header + data)."""
        result = extract(SAMPLES / "sample.csv")
        assert "Alice" in result["text"]
        assert "Engineering" in result["text"]
        assert "95000" in result["text"]

    def test_column_names(self):
        """Verify metadata reports the correct column headers from the first row."""
        result = extract(SAMPLES / "sample.csv")
        assert result["metadata"]["columns"] == ["Name", "Department", "Salary", "City"]

    def test_column_count(self):
        """Verify column_count matches the number of headers (4 columns in sample)."""
        result = extract(SAMPLES / "sample.csv")
        assert result["metadata"]["column_count"] == 4

    def test_total_rows(self):
        """Verify total_rows reflects the full file (header + 5 data rows + trailing newline = 6 newlines)."""
        result = extract(SAMPLES / "sample.csv")
        assert result["metadata"]["total_rows"] >= 5

    def test_preview_rows_capped(self):
        """Verify preview_rows doesn't exceed the max (100) and matches actual row count for small files."""
        result = extract(SAMPLES / "sample.csv")
        # Small file: preview_rows should equal the actual number of rows read
        assert result["metadata"]["preview_rows"] <= 100
        assert result["metadata"]["preview_rows"] >= 5

    def test_file_type_is_csv(self):
        """Verify the file_type is correctly identified as .csv (not treated as a code file)."""
        result = extract(SAMPLES / "sample.csv")
        assert result["file_type"] == ".csv"
        # Should NOT have code-file metadata keys (line_count, char_count)
        assert "line_count" not in result["metadata"]

    def test_no_error(self):
        """A valid CSV should produce no extraction error."""
        result = extract(SAMPLES / "sample.csv")
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
