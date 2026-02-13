import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from database import Database


class TestDatabase(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.tmp.close()
        self.db = Database(self.tmp.name)

    def tearDown(self):
        self.db.close()
        os.unlink(self.tmp.name)

    # --- Projects ---

    def test_create_and_get_project(self):
        pid = self.db.create_project("Work")
        project = self.db.get_project(pid)
        self.assertEqual(project["name"], "Work")

    def test_list_projects(self):
        self.db.create_project("Beta")
        self.db.create_project("Alpha")
        projects = self.db.list_projects()
        self.assertEqual([p["name"] for p in projects], ["Alpha", "Beta"])

    def test_delete_project(self):
        pid = self.db.create_project("Temp")
        self.db.delete_project(pid)
        self.assertIsNone(self.db.get_project(pid))

    # --- Folders ---

    def test_create_and_list_folders(self):
        pid = self.db.create_project("Work")
        fid = self.db.create_folder(pid, "Reports")
        folders = self.db.list_folders(pid)
        self.assertEqual(len(folders), 1)
        self.assertEqual(folders[0]["name"], "Reports")

    def test_nested_folders(self):
        pid = self.db.create_project("Work")
        parent = self.db.create_folder(pid, "Documents")
        child = self.db.create_folder(pid, "Q1 Reports", parent_folder_id=parent)
        children = self.db.list_folders(pid, parent_folder_id=parent)
        self.assertEqual(len(children), 1)
        self.assertEqual(children[0]["name"], "Q1 Reports")

    def test_delete_folder(self):
        pid = self.db.create_project("Work")
        fid = self.db.create_folder(pid, "Old")
        self.db.delete_folder(fid)
        self.assertIsNone(self.db.get_folder(fid))

    # --- Files ---

    def test_add_and_get_file(self):
        pid = self.db.create_project("Work")
        fid = self.db.create_folder(pid, "Reports")
        file_id = self.db.add_file("report.xlsx", "/root/Work/Reports/report.xlsx", fid,
                                   size_bytes=1024, file_type=".xlsx")
        f = self.db.get_file(file_id)
        self.assertEqual(f["original_name"], "report.xlsx")
        self.assertEqual(f["size_bytes"], 1024)

    def test_list_files(self):
        pid = self.db.create_project("Work")
        fid = self.db.create_folder(pid, "Reports")
        self.db.add_file("b.docx", "/path/b.docx", fid)
        self.db.add_file("a.xlsx", "/path/a.xlsx", fid)
        files = self.db.list_files(fid)
        self.assertEqual([f["original_name"] for f in files], ["a.xlsx", "b.docx"])

    def test_update_file(self):
        pid = self.db.create_project("Work")
        fid = self.db.create_folder(pid, "Reports")
        file_id = self.db.add_file("report.xlsx", "/path/report.xlsx", fid)
        self.db.update_file(file_id, metadata_text="some extracted text")
        f = self.db.get_file(file_id)
        self.assertEqual(f["metadata_text"], "some extracted text")

    def test_delete_file(self):
        pid = self.db.create_project("Work")
        fid = self.db.create_folder(pid, "Reports")
        file_id = self.db.add_file("old.docx", "/path/old.docx", fid)
        self.db.delete_file(file_id)
        self.assertIsNone(self.db.get_file(file_id))

    # --- Tags ---

    def test_tag_file(self):
        pid = self.db.create_project("Work")
        fid = self.db.create_folder(pid, "Reports")
        file_id = self.db.add_file("report.xlsx", "/path/report.xlsx", fid)
        self.db.add_tag_to_file(file_id, "quarterly")
        self.db.add_tag_to_file(file_id, "finance")
        tags = self.db.get_file_tags(file_id)
        self.assertEqual(tags, ["finance", "quarterly"])

    def test_remove_tag(self):
        pid = self.db.create_project("Work")
        fid = self.db.create_folder(pid, "Reports")
        file_id = self.db.add_file("report.xlsx", "/path/report.xlsx", fid)
        self.db.add_tag_to_file(file_id, "temp")
        self.db.remove_tag_from_file(file_id, "temp")
        self.assertEqual(self.db.get_file_tags(file_id), [])

    def test_duplicate_tag_ignored(self):
        pid = self.db.create_project("Work")
        fid = self.db.create_folder(pid, "Reports")
        file_id = self.db.add_file("report.xlsx", "/path/report.xlsx", fid)
        self.db.add_tag_to_file(file_id, "quarterly")
        self.db.add_tag_to_file(file_id, "quarterly")
        self.assertEqual(self.db.get_file_tags(file_id), ["quarterly"])

    # --- Categories ---

    def test_categorize_file(self):
        pid = self.db.create_project("Work")
        fid = self.db.create_folder(pid, "Reports")
        file_id = self.db.add_file("report.xlsx", "/path/report.xlsx", fid)
        self.db.add_category_to_file(file_id, "Report")
        self.db.add_category_to_file(file_id, "Financial")
        cats = self.db.get_file_categories(file_id)
        self.assertEqual(cats, ["Financial", "Report"])

    def test_remove_category(self):
        pid = self.db.create_project("Work")
        fid = self.db.create_folder(pid, "Reports")
        file_id = self.db.add_file("report.xlsx", "/path/report.xlsx", fid)
        self.db.add_category_to_file(file_id, "Old")
        self.db.remove_category_from_file(file_id, "Old")
        self.assertEqual(self.db.get_file_categories(file_id), [])

    # --- Comments ---

    def test_add_and_get_comments(self):
        pid = self.db.create_project("Work")
        fid = self.db.create_folder(pid, "Reports")
        file_id = self.db.add_file("report.xlsx", "/path/report.xlsx", fid)
        self.db.add_comment(file_id, "First draft")
        self.db.add_comment(file_id, "Needs review")
        comments = self.db.get_file_comments(file_id)
        self.assertEqual(len(comments), 2)
        self.assertEqual(comments[0]["comment"], "First draft")

    def test_delete_comment(self):
        pid = self.db.create_project("Work")
        fid = self.db.create_folder(pid, "Reports")
        file_id = self.db.add_file("report.xlsx", "/path/report.xlsx", fid)
        cid = self.db.add_comment(file_id, "Remove me")
        self.db.delete_comment(cid)
        self.assertEqual(self.db.get_file_comments(file_id), [])

    # --- Search ---

    def test_search_by_filename(self):
        """search_files() should match against files.original_name (case-insensitive)."""
        pid = self.db.create_project("Work")
        fid = self.db.create_folder(pid, "Reports")
        self.db.add_file("quarterly_report.xlsx", "/path/quarterly_report.xlsx", fid,
                         file_type=".xlsx", metadata_text="revenue data")
        results = self.db.search_files("quarterly")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["original_name"], "quarterly_report.xlsx")
        # Case-insensitive
        results_upper = self.db.search_files("QUARTERLY")
        self.assertEqual(len(results_upper), 1)

    def test_search_by_metadata_text(self):
        """search_files() should match against files.metadata_text content."""
        pid = self.db.create_project("Work")
        fid = self.db.create_folder(pid, "Reports")
        self.db.add_file("data.csv", "/path/data.csv", fid,
                         file_type=".csv", metadata_text="Alice,Engineering,95000")
        results = self.db.search_files("Engineering")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["original_name"], "data.csv")

    def test_search_by_tag(self):
        """search_files() should match against tag names associated with a file."""
        pid = self.db.create_project("Work")
        fid = self.db.create_folder(pid, "Reports")
        file_id = self.db.add_file("notes.txt", "/path/notes.txt", fid, file_type=".txt")
        self.db.add_tag_to_file(file_id, "finance")
        self.db.add_tag_to_file(file_id, "Q1")
        results = self.db.search_files("finance")
        self.assertEqual(len(results), 1)
        self.assertIn("finance", results[0]["tags"])

    def test_search_by_file_type(self):
        """search_files() should match against files.file_type (extension)."""
        pid = self.db.create_project("Work")
        fid = self.db.create_folder(pid, "Code")
        self.db.add_file("app.py", "/path/app.py", fid, file_type=".py")
        self.db.add_file("readme.md", "/path/readme.md", fid, file_type=".md")
        results = self.db.search_files(".py")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["original_name"], "app.py")

    def test_search_deduplication(self):
        """A file matching on both filename and tag should appear only once."""
        pid = self.db.create_project("Work")
        fid = self.db.create_folder(pid, "Reports")
        file_id = self.db.add_file("finance_report.xlsx", "/path/finance_report.xlsx", fid,
                                   file_type=".xlsx", metadata_text="finance data")
        self.db.add_tag_to_file(file_id, "finance")
        # "finance" matches filename, metadata_text, AND tag — should still return 1 result
        results = self.db.search_files("finance")
        self.assertEqual(len(results), 1)

    def test_search_includes_project_and_folder(self):
        """Search results should include project_name and folder_name."""
        pid = self.db.create_project("Personal")
        fid = self.db.create_folder(pid, "Photos")
        self.db.add_file("sunset.jpg", "/path/sunset.jpg", fid, file_type=".jpg")
        results = self.db.search_files("sunset")
        self.assertEqual(results[0]["project_name"], "Personal")
        self.assertEqual(results[0]["folder_name"], "Photos")

    def test_search_empty_query(self):
        """Empty or whitespace query should return empty list."""
        self.assertEqual(self.db.search_files(""), [])
        self.assertEqual(self.db.search_files("   "), [])

    def test_search_no_matches(self):
        """Query with no matches should return empty list."""
        pid = self.db.create_project("Work")
        fid = self.db.create_folder(pid, "Reports")
        self.db.add_file("report.xlsx", "/path/report.xlsx", fid)
        results = self.db.search_files("nonexistent_xyz_123")
        self.assertEqual(results, [])

    # --- Cascade deletes ---

    def test_delete_project_cascades(self):
        pid = self.db.create_project("Work")
        fid = self.db.create_folder(pid, "Reports")
        file_id = self.db.add_file("r.xlsx", "/path/r.xlsx", fid)
        self.db.add_tag_to_file(file_id, "important")
        self.db.add_comment(file_id, "test")
        self.db.delete_project(pid)
        self.assertIsNone(self.db.get_folder(fid))
        self.assertIsNone(self.db.get_file(file_id))
        self.assertEqual(self.db.get_file_tags(file_id), [])
        self.assertEqual(self.db.get_file_comments(file_id), [])

    # --- Duplicate stored_path ---

    def test_duplicate_stored_path_raises_value_error(self):
        """Adding two files with the same stored_path should raise ValueError."""
        pid = self.db.create_project("Work")
        fid = self.db.create_folder(pid, "Reports")
        self.db.add_file("a.xlsx", "/same/path.xlsx", fid)
        with self.assertRaises(ValueError) as ctx:
            self.db.add_file("b.xlsx", "/same/path.xlsx", fid)
        self.assertIn("already exists", str(ctx.exception))

    # --- Search edge cases ---

    def test_search_with_sql_special_chars(self):
        """Search with SQL wildcards (%, _) should not cause unexpected matches or errors."""
        pid = self.db.create_project("Work")
        fid = self.db.create_folder(pid, "Reports")
        self.db.add_file("100%_report.xlsx", "/path/100pct.xlsx", fid,
                         metadata_text="100% complete")
        # Searching for literal "%" should match the file, not act as wildcard
        results = self.db.search_files("100%")
        self.assertTrue(len(results) >= 1)

    def test_search_with_single_quote(self):
        """Search with apostrophe should not cause SQL injection."""
        pid = self.db.create_project("Work")
        fid = self.db.create_folder(pid, "Reports")
        self.db.add_file("john's_file.docx", "/path/johns.docx", fid)
        results = self.db.search_files("john's")
        self.assertEqual(len(results), 1)

    def test_search_multi_word_relevance_order(self):
        """Multi-word query should rank files matching more words higher."""
        pid = self.db.create_project("Work")
        fid = self.db.create_folder(pid, "Reports")
        # File matching 1 word
        self.db.add_file("budget.xlsx", "/path/budget.xlsx", fid,
                         metadata_text="annual budget data")
        # File matching 2 words
        self.db.add_file("annual_report.xlsx", "/path/annual_report.xlsx", fid,
                         metadata_text="annual budget report")
        results = self.db.search_files("annual budget")
        # Both should match, but annual_report matches both words
        self.assertTrue(len(results) >= 2)
        # The one matching more words should come first
        self.assertEqual(results[0]["original_name"], "annual_report.xlsx")

    # --- Scanning ---

    def test_get_all_stored_paths_empty(self):
        """get_all_stored_paths() should return empty set when no files exist."""
        self.assertEqual(self.db.get_all_stored_paths(), set())

    def test_get_all_stored_paths(self):
        """get_all_stored_paths() should return all stored_path values."""
        pid = self.db.create_project("Work")
        fid = self.db.create_folder(pid, "Reports")
        self.db.add_file("a.xlsx", "/root/Work/Reports/a.xlsx", fid)
        self.db.add_file("b.docx", "/root/Work/Reports/b.docx", fid)
        paths = self.db.get_all_stored_paths()
        self.assertEqual(paths, {"/root/Work/Reports/a.xlsx", "/root/Work/Reports/b.docx"})

    def test_search_by_comment(self):
        """search_files() should match against file comment text."""
        pid = self.db.create_project("Work")
        fid = self.db.create_folder(pid, "Reports")
        file_id = self.db.add_file("data.csv", "/path/data2.csv", fid)
        self.db.add_comment(file_id, "needs review by manager")
        results = self.db.search_files("manager")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["original_name"], "data.csv")


    # --- Popular Tags ---

    def test_popular_tags_global(self):
        """get_popular_tags returns tags sorted by usage count descending."""
        pid = self.db.create_project("Work")
        fid = self.db.create_folder(pid, "Reports")
        f1 = self.db.add_file("a.txt", "/a.txt", fid)
        f2 = self.db.add_file("b.txt", "/b.txt", fid)
        f3 = self.db.add_file("c.txt", "/c.txt", fid)
        self.db.add_tag_to_file(f1, "finance")
        self.db.add_tag_to_file(f2, "finance")
        self.db.add_tag_to_file(f3, "finance")
        self.db.add_tag_to_file(f1, "Q1")
        self.db.add_tag_to_file(f2, "Q1")
        self.db.add_tag_to_file(f1, "draft")
        tags = self.db.get_popular_tags()
        self.assertEqual(tags[0], "finance")  # 3 uses
        self.assertEqual(tags[1], "Q1")       # 2 uses
        self.assertEqual(tags[2], "draft")    # 1 use

    def test_popular_tags_by_project(self):
        """get_popular_tags filters by project when project_id is given."""
        p1 = self.db.create_project("Work")
        p2 = self.db.create_project("Personal")
        f1 = self.db.create_folder(p1, "Reports")
        f2 = self.db.create_folder(p2, "Photos")
        wf1 = self.db.add_file("a.txt", "/a.txt", f1)
        wf2 = self.db.add_file("b.txt", "/b.txt", f1)
        pf1 = self.db.add_file("c.txt", "/c.txt", f2)
        self.db.add_tag_to_file(wf1, "finance")
        self.db.add_tag_to_file(wf2, "finance")
        self.db.add_tag_to_file(pf1, "vacation")
        self.db.add_tag_to_file(pf1, "finance")
        # Project 1 (Work): finance=2
        work_tags = self.db.get_popular_tags(project_id=p1)
        self.assertEqual(work_tags, ["finance"])
        # Project 2 (Personal): finance=1, vacation=1
        personal_tags = self.db.get_popular_tags(project_id=p2)
        self.assertIn("finance", personal_tags)
        self.assertIn("vacation", personal_tags)

    def test_popular_tags_limit(self):
        """get_popular_tags respects the limit parameter."""
        pid = self.db.create_project("Work")
        fid = self.db.create_folder(pid, "Reports")
        f1 = self.db.add_file("a.txt", "/a.txt", fid)
        for i in range(20):
            self.db.add_tag_to_file(f1, f"tag{i}")
        tags = self.db.get_popular_tags(limit=5)
        self.assertEqual(len(tags), 5)

    def test_popular_tags_empty(self):
        """get_popular_tags returns empty list when no tags exist."""
        tags = self.db.get_popular_tags()
        self.assertEqual(tags, [])


    # --- Subfolder / Nesting ---

    def test_get_folder_depth_root(self):
        """Root-level folder has depth 1."""
        pid = self.db.create_project("Work")
        fid = self.db.create_folder(pid, "Reports")
        self.assertEqual(self.db.get_folder_depth(fid), 1)

    def test_get_folder_depth_nested(self):
        """Nested folders report correct depth."""
        pid = self.db.create_project("Work")
        f1 = self.db.create_folder(pid, "Reports")
        f2 = self.db.create_folder(pid, "Q1", parent_folder_id=f1)
        f3 = self.db.create_folder(pid, "January", parent_folder_id=f2)
        self.assertEqual(self.db.get_folder_depth(f1), 1)
        self.assertEqual(self.db.get_folder_depth(f2), 2)
        self.assertEqual(self.db.get_folder_depth(f3), 3)

    def test_get_folder_path_root(self):
        """Root folder path is a single-element list."""
        pid = self.db.create_project("Work")
        fid = self.db.create_folder(pid, "Reports")
        path = self.db.get_folder_path(fid)
        self.assertEqual(len(path), 1)
        self.assertEqual(path[0]["name"], "Reports")

    def test_get_folder_path_nested(self):
        """Nested folder path returns correct chain from root to leaf."""
        pid = self.db.create_project("Work")
        f1 = self.db.create_folder(pid, "Reports")
        f2 = self.db.create_folder(pid, "Q1", parent_folder_id=f1)
        f3 = self.db.create_folder(pid, "January", parent_folder_id=f2)
        path = self.db.get_folder_path(f3)
        self.assertEqual(len(path), 3)
        self.assertEqual(path[0]["name"], "Reports")
        self.assertEqual(path[1]["name"], "Q1")
        self.assertEqual(path[2]["name"], "January")

    def test_get_folder_path_nonexistent(self):
        """Nonexistent folder returns empty path."""
        path = self.db.get_folder_path(9999)
        self.assertEqual(path, [])

    def test_get_all_folders_nested(self):
        """get_all_folders_nested returns flat list with correct depth and display."""
        pid = self.db.create_project("Work")
        f1 = self.db.create_folder(pid, "Reports")
        f2 = self.db.create_folder(pid, "Q1", parent_folder_id=f1)
        f3 = self.db.create_folder(pid, "January", parent_folder_id=f2)
        f4 = self.db.create_folder(pid, "Slides")  # root sibling
        result = self.db.get_all_folders_nested(pid)
        self.assertEqual(len(result), 4)
        # Check tree order: Reports, Q1, January, Slides
        self.assertEqual(result[0]["name"], "Reports")
        self.assertEqual(result[0]["depth"], 0)
        self.assertEqual(result[0]["display"], "Reports")
        self.assertEqual(result[1]["name"], "Q1")
        self.assertEqual(result[1]["depth"], 1)
        self.assertEqual(result[1]["display"], "Reports > Q1")
        self.assertEqual(result[2]["name"], "January")
        self.assertEqual(result[2]["depth"], 2)
        self.assertEqual(result[2]["display"], "Reports > Q1 > January")
        self.assertEqual(result[3]["name"], "Slides")
        self.assertEqual(result[3]["depth"], 0)

    def test_create_folder_depth_limit(self):
        """Creating a folder beyond MAX_FOLDER_DEPTH raises ValueError."""
        from database import MAX_FOLDER_DEPTH
        pid = self.db.create_project("Work")
        parent_id = None
        # Create folders up to max depth
        for i in range(MAX_FOLDER_DEPTH):
            parent_id = self.db.create_folder(pid, f"Level{i+1}", parent_folder_id=parent_id)
        # Next one should fail
        with self.assertRaises(ValueError) as ctx:
            self.db.create_folder(pid, "TooDeep", parent_folder_id=parent_id)
        self.assertIn("maximum nesting depth", str(ctx.exception))

    def test_create_folder_at_max_depth_succeeds(self):
        """Creating a folder at exactly MAX_FOLDER_DEPTH should succeed."""
        from database import MAX_FOLDER_DEPTH
        pid = self.db.create_project("Work")
        parent_id = None
        for i in range(MAX_FOLDER_DEPTH - 1):
            parent_id = self.db.create_folder(pid, f"Level{i+1}", parent_folder_id=parent_id)
        # This should be exactly at max depth — should succeed
        fid = self.db.create_folder(pid, "AtMax", parent_folder_id=parent_id)
        self.assertIsNotNone(fid)
        self.assertEqual(self.db.get_folder_depth(fid), MAX_FOLDER_DEPTH)


if __name__ == "__main__":
    unittest.main()
