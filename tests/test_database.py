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


if __name__ == "__main__":
    unittest.main()
