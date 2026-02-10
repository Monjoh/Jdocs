"""Tests for utility helper functions (src/utils.py).

Tests the pure utility functions: format_size, format_metadata, sanitize_name.
These are extracted to utils.py so they can be tested without PyQt5.
"""

import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from utils import format_size, format_metadata, sanitize_name, scan_untracked_files


class TestFormatSize(unittest.TestCase):
    """Test human-readable file size formatting."""

    def test_zero_bytes(self):
        self.assertEqual(format_size(0), "0 B")

    def test_bytes_range(self):
        self.assertEqual(format_size(512), "512 B")

    def test_one_byte(self):
        self.assertEqual(format_size(1), "1 B")

    def test_just_under_1kb(self):
        self.assertEqual(format_size(1023), "1023 B")

    def test_exactly_1kb(self):
        self.assertEqual(format_size(1024), "1.0 KB")

    def test_kilobytes(self):
        self.assertEqual(format_size(5120), "5.0 KB")

    def test_just_under_1mb(self):
        result = format_size(1024 * 1024 - 1)
        self.assertIn("KB", result)

    def test_exactly_1mb(self):
        self.assertEqual(format_size(1024 * 1024), "1.0 MB")

    def test_megabytes(self):
        self.assertEqual(format_size(10 * 1024 * 1024), "10.0 MB")

    def test_large_file(self):
        result = format_size(500 * 1024 * 1024)
        self.assertEqual(result, "500.0 MB")


class TestFormatMetadata(unittest.TestCase):
    """Test metadata string formatting for each file type."""

    def test_docx_with_author_and_title(self):
        result = format_metadata({
            "file_type": ".docx",
            "metadata": {"author": "John", "title": "Report", "paragraph_count": 10},
        })
        self.assertIn("Author: John", result)
        self.assertIn("Title: Report", result)
        self.assertIn("Paragraphs: 10", result)

    def test_docx_without_optional_fields(self):
        result = format_metadata({
            "file_type": ".docx",
            "metadata": {"author": "", "title": "", "paragraph_count": 5},
        })
        self.assertNotIn("Author:", result)
        self.assertNotIn("Title:", result)
        self.assertIn("Paragraphs: 5", result)

    def test_xlsx(self):
        result = format_metadata({
            "file_type": ".xlsx",
            "metadata": {"sheet_count": 2, "sheets": [
                {"name": "Data", "row_count": 100},
                {"name": "Summary", "row_count": 10},
            ]},
        })
        self.assertIn("Sheets: 2", result)
        self.assertIn("Data: 100 rows", result)
        self.assertIn("Summary: 10 rows", result)

    def test_pptx(self):
        result = format_metadata({
            "file_type": ".pptx",
            "metadata": {"author": "Jane", "title": "Deck", "slide_count": 15},
        })
        self.assertIn("Slides: 15", result)
        self.assertIn("Author: Jane", result)

    def test_image_png(self):
        result = format_metadata({
            "file_type": ".png",
            "metadata": {"width": 1920, "height": 1080, "format": "PNG", "mode": "RGB"},
        })
        self.assertIn("1920 x 1080", result)
        self.assertIn("Format: PNG", result)

    def test_csv(self):
        result = format_metadata({
            "file_type": ".csv",
            "metadata": {"total_rows": 500, "column_count": 4, "columns": ["A", "B", "C", "D"], "preview_rows": 100},
        })
        self.assertIn("Rows: 500", result)
        self.assertIn("Columns: 4", result)
        self.assertIn("A, B, C, D", result)

    def test_csv_many_columns_truncated(self):
        cols = [f"col_{i}" for i in range(15)]
        result = format_metadata({
            "file_type": ".csv",
            "metadata": {"total_rows": 10, "column_count": 15, "columns": cols, "preview_rows": 10},
        })
        self.assertIn("+5 more", result)

    def test_code_file(self):
        result = format_metadata({
            "file_type": ".py",
            "metadata": {"line_count": 200, "char_count": 5000},
        })
        self.assertIn("Lines: 200", result)
        self.assertIn("Characters: 5000", result)

    def test_unsupported_type(self):
        result = format_metadata({
            "file_type": ".xyz",
            "metadata": {"note": "Unsupported file type"},
        })
        self.assertIn("Unsupported", result)

    def test_empty_metadata(self):
        result = format_metadata({"file_type": ".xyz", "metadata": {}})
        self.assertEqual(result, "No metadata available for this file type.")


class TestSanitizeName(unittest.TestCase):
    """Test folder/project name sanitization for cross-platform safety."""

    def test_normal_name_unchanged(self):
        self.assertEqual(sanitize_name("My Project"), "My Project")

    def test_strips_invalid_windows_chars(self):
        self.assertEqual(sanitize_name('Report<>:"/\\|?*2024'), "Report2024")

    def test_strips_leading_trailing_spaces(self):
        self.assertEqual(sanitize_name("  Reports  "), "Reports")

    def test_strips_leading_trailing_dots(self):
        self.assertEqual(sanitize_name("...hidden..."), "hidden")

    def test_empty_after_sanitize(self):
        """A name made entirely of invalid characters should return empty string."""
        self.assertEqual(sanitize_name('<>:"/\\|?*'), "")

    def test_dots_and_spaces_only(self):
        self.assertEqual(sanitize_name("  ... "), "")

    def test_mixed_valid_and_invalid(self):
        self.assertEqual(sanitize_name("Q1: Reports / Summary"), "Q1 Reports  Summary")

    def test_unicode_preserved(self):
        """Non-ASCII characters should be kept (they're valid on both platforms)."""
        self.assertEqual(sanitize_name("Projets été"), "Projets été")


class TestScanUntrackedFiles(unittest.TestCase):
    """Test the folder scanning utility function."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir)

    def _create_file(self, relative_path, content="test"):
        """Helper to create a file inside tmpdir."""
        full = os.path.join(self.tmpdir, relative_path)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "w") as f:
            f.write(content)
        return full

    def test_empty_folder_returns_empty(self):
        result = scan_untracked_files(self.tmpdir, set())
        self.assertEqual(result, [])

    def test_finds_untracked_files(self):
        path_a = self._create_file("Project/Reports/a.xlsx")
        path_b = self._create_file("Project/Reports/b.docx")
        result = scan_untracked_files(self.tmpdir, set())
        names = {f["name"] for f in result}
        self.assertEqual(names, {"a.xlsx", "b.docx"})

    def test_excludes_tracked_files(self):
        path_a = self._create_file("Project/Reports/a.xlsx")
        path_b = self._create_file("Project/Reports/b.docx")
        tracked = {path_a}
        result = scan_untracked_files(self.tmpdir, tracked)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["name"], "b.docx")

    def test_skips_jdocs_directory(self):
        self._create_file(".jdocs/jdocs.db", "sqlite data")
        self._create_file("Project/file.txt")
        result = scan_untracked_files(self.tmpdir, set())
        names = {f["name"] for f in result}
        self.assertNotIn("jdocs.db", names)
        self.assertIn("file.txt", names)

    def test_includes_relative_path(self):
        self._create_file("Work/Reports/q1.xlsx")
        result = scan_untracked_files(self.tmpdir, set())
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["relative_path"], os.path.join("Work", "Reports", "q1.xlsx"))

    def test_includes_size(self):
        self._create_file("file.txt", "hello world")
        result = scan_untracked_files(self.tmpdir, set())
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["size_bytes"], 11)

    def test_all_tracked_returns_empty(self):
        path = self._create_file("tracked.txt")
        result = scan_untracked_files(self.tmpdir, {path})
        self.assertEqual(result, [])


if __name__ == "__main__":
    unittest.main()
