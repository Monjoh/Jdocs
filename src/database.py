import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Union


class Database:
    """SQLite database layer for jDocs."""

    def __init__(self, db_path: Union[str, Path]):
        self.db_path = str(db_path)
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        self._create_tables()

    def _create_tables(self):
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS projects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS folders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                parent_folder_id INTEGER,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
                FOREIGN KEY (parent_folder_id) REFERENCES folders(id) ON DELETE CASCADE,
                UNIQUE(project_id, name, parent_folder_id)
            );

            CREATE TABLE IF NOT EXISTS files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                original_name TEXT NOT NULL,
                stored_path TEXT NOT NULL UNIQUE,
                folder_id INTEGER NOT NULL,
                size_bytes INTEGER,
                file_type TEXT,
                metadata_text TEXT,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                updated_at TEXT NOT NULL DEFAULT (datetime('now')),
                FOREIGN KEY (folder_id) REFERENCES folders(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS tags (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE
            );

            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE
            );

            CREATE TABLE IF NOT EXISTS file_tags (
                file_id INTEGER NOT NULL,
                tag_id INTEGER NOT NULL,
                PRIMARY KEY (file_id, tag_id),
                FOREIGN KEY (file_id) REFERENCES files(id) ON DELETE CASCADE,
                FOREIGN KEY (tag_id) REFERENCES tags(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS file_categories (
                file_id INTEGER NOT NULL,
                category_id INTEGER NOT NULL,
                PRIMARY KEY (file_id, category_id),
                FOREIGN KEY (file_id) REFERENCES files(id) ON DELETE CASCADE,
                FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS file_comments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_id INTEGER NOT NULL,
                comment TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                FOREIGN KEY (file_id) REFERENCES files(id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_files_folder ON files(folder_id);
            CREATE INDEX IF NOT EXISTS idx_files_type ON files(file_type);
            CREATE INDEX IF NOT EXISTS idx_folders_project ON folders(project_id);
        """)
        self.conn.commit()

    def close(self):
        self.conn.close()

    # --- Projects ---

    def create_project(self, name: str) -> int:
        cur = self.conn.execute(
            "INSERT INTO projects (name) VALUES (?)", (name,)
        )
        self.conn.commit()
        return cur.lastrowid

    def get_project(self, project_id: int) -> Optional[dict]:
        row = self.conn.execute(
            "SELECT * FROM projects WHERE id = ?", (project_id,)
        ).fetchone()
        return dict(row) if row else None

    def list_projects(self) -> List[Dict]:
        rows = self.conn.execute(
            "SELECT * FROM projects ORDER BY name"
        ).fetchall()
        return [dict(r) for r in rows]

    def delete_project(self, project_id: int):
        self.conn.execute("DELETE FROM projects WHERE id = ?", (project_id,))
        self.conn.commit()

    # --- Folders ---

    def create_folder(self, project_id: int, name: str, parent_folder_id: Optional[int] = None) -> int:
        cur = self.conn.execute(
            "INSERT INTO folders (project_id, name, parent_folder_id) VALUES (?, ?, ?)",
            (project_id, name, parent_folder_id),
        )
        self.conn.commit()
        return cur.lastrowid

    def get_folder(self, folder_id: int) -> Optional[dict]:
        row = self.conn.execute(
            "SELECT * FROM folders WHERE id = ?", (folder_id,)
        ).fetchone()
        return dict(row) if row else None

    def list_folders(self, project_id: int, parent_folder_id: Optional[int] = None) -> List[Dict]:
        if parent_folder_id is None:
            rows = self.conn.execute(
                "SELECT * FROM folders WHERE project_id = ? AND parent_folder_id IS NULL ORDER BY name",
                (project_id,),
            ).fetchall()
        else:
            rows = self.conn.execute(
                "SELECT * FROM folders WHERE project_id = ? AND parent_folder_id = ? ORDER BY name",
                (project_id, parent_folder_id),
            ).fetchall()
        return [dict(r) for r in rows]

    def delete_folder(self, folder_id: int):
        self.conn.execute("DELETE FROM folders WHERE id = ?", (folder_id,))
        self.conn.commit()

    # --- Files ---

    def add_file(self, original_name: str, stored_path: str, folder_id: int,
                 size_bytes: Optional[int] = None, file_type: Optional[str] = None,
                 metadata_text: Optional[str] = None) -> int:
        try:
            cur = self.conn.execute(
                """INSERT INTO files (original_name, stored_path, folder_id, size_bytes, file_type, metadata_text)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (original_name, stored_path, folder_id, size_bytes, file_type, metadata_text),
            )
            self.conn.commit()
            return cur.lastrowid
        except sqlite3.IntegrityError as e:
            self.conn.rollback()
            if "stored_path" in str(e).lower() or "unique" in str(e).lower():
                raise ValueError(f"A file already exists at this path: {stored_path}") from e
            raise

    def get_file(self, file_id: int) -> Optional[dict]:
        row = self.conn.execute(
            "SELECT * FROM files WHERE id = ?", (file_id,)
        ).fetchone()
        return dict(row) if row else None

    def list_files(self, folder_id: int) -> List[Dict]:
        rows = self.conn.execute(
            "SELECT * FROM files WHERE folder_id = ? ORDER BY original_name",
            (folder_id,),
        ).fetchall()
        return [dict(r) for r in rows]

    def update_file(self, file_id: int, **kwargs):
        allowed = {"original_name", "stored_path", "folder_id", "size_bytes", "file_type", "metadata_text"}
        updates = {k: v for k, v in kwargs.items() if k in allowed}
        if not updates:
            return
        updates["updated_at"] = datetime.now().isoformat()
        set_clause = ", ".join(f"{k} = ?" for k in updates)
        values = list(updates.values()) + [file_id]
        self.conn.execute(f"UPDATE files SET {set_clause} WHERE id = ?", values)
        self.conn.commit()

    def delete_file(self, file_id: int):
        self.conn.execute("DELETE FROM files WHERE id = ?", (file_id,))
        self.conn.commit()

    # --- Tags ---

    def list_tags(self) -> List[str]:
        rows = self.conn.execute(
            "SELECT name FROM tags ORDER BY name"
        ).fetchall()
        return [r["name"] for r in rows]

    def create_tag(self, name: str) -> int:
        cur = self.conn.execute(
            "INSERT OR IGNORE INTO tags (name) VALUES (?)", (name,)
        )
        self.conn.commit()
        if cur.lastrowid == 0:
            row = self.conn.execute("SELECT id FROM tags WHERE name = ?", (name,)).fetchone()
            return row["id"]
        return cur.lastrowid

    def add_tag_to_file(self, file_id: int, tag_name: str):
        tag_id = self.create_tag(tag_name)
        self.conn.execute(
            "INSERT OR IGNORE INTO file_tags (file_id, tag_id) VALUES (?, ?)",
            (file_id, tag_id),
        )
        self.conn.commit()

    def remove_tag_from_file(self, file_id: int, tag_name: str):
        self.conn.execute(
            """DELETE FROM file_tags WHERE file_id = ? AND tag_id =
               (SELECT id FROM tags WHERE name = ?)""",
            (file_id, tag_name),
        )
        self.conn.commit()

    def get_file_tags(self, file_id: int) -> List[str]:
        rows = self.conn.execute(
            """SELECT t.name FROM tags t
               JOIN file_tags ft ON t.id = ft.tag_id
               WHERE ft.file_id = ? ORDER BY t.name""",
            (file_id,),
        ).fetchall()
        return [r["name"] for r in rows]

    # --- Categories ---

    def list_categories(self) -> List[str]:
        rows = self.conn.execute(
            "SELECT name FROM categories ORDER BY name"
        ).fetchall()
        return [r["name"] for r in rows]

    def create_category(self, name: str) -> int:
        cur = self.conn.execute(
            "INSERT OR IGNORE INTO categories (name) VALUES (?)", (name,)
        )
        self.conn.commit()
        if cur.lastrowid == 0:
            row = self.conn.execute("SELECT id FROM categories WHERE name = ?", (name,)).fetchone()
            return row["id"]
        return cur.lastrowid

    def add_category_to_file(self, file_id: int, category_name: str):
        cat_id = self.create_category(category_name)
        self.conn.execute(
            "INSERT OR IGNORE INTO file_categories (file_id, category_id) VALUES (?, ?)",
            (file_id, cat_id),
        )
        self.conn.commit()

    def remove_category_from_file(self, file_id: int, category_name: str):
        self.conn.execute(
            """DELETE FROM file_categories WHERE file_id = ? AND category_id =
               (SELECT id FROM categories WHERE name = ?)""",
            (file_id, category_name),
        )
        self.conn.commit()

    def get_file_categories(self, file_id: int) -> List[str]:
        rows = self.conn.execute(
            """SELECT c.name FROM categories c
               JOIN file_categories fc ON c.id = fc.category_id
               WHERE fc.file_id = ? ORDER BY c.name""",
            (file_id,),
        ).fetchall()
        return [r["name"] for r in rows]

    # --- Comments ---

    def add_comment(self, file_id: int, comment: str) -> int:
        cur = self.conn.execute(
            "INSERT INTO file_comments (file_id, comment) VALUES (?, ?)",
            (file_id, comment),
        )
        self.conn.commit()
        return cur.lastrowid

    def get_file_comments(self, file_id: int) -> List[Dict]:
        rows = self.conn.execute(
            "SELECT * FROM file_comments WHERE file_id = ? ORDER BY created_at",
            (file_id,),
        ).fetchall()
        return [dict(r) for r in rows]

    def delete_comment(self, comment_id: int):
        self.conn.execute("DELETE FROM file_comments WHERE id = ?", (comment_id,))
        self.conn.commit()

    # --- Scanning ---

    def get_all_stored_paths(self) -> set[str]:
        """Return a set of all stored_path values for tracked files."""
        rows = self.conn.execute("SELECT stored_path FROM files").fetchall()
        return {r["stored_path"] for r in rows}

    # --- Search ---

    def search_files(self, query: str) -> List[Dict]:
        """Search files across filename, metadata_text, file_type, tags, and comments.

        Supports multi-word queries: splits into individual words, matches files
        containing ANY word, then sorts by number of words matched (most relevant first).
        Returns deduplicated file records enriched with project_name, folder_name, and tags.
        """
        if not query or not query.strip():
            return []

        words = [w for w in query.strip().split() if w]
        if not words:
            return []

        # For each word, find matching file IDs and count how many words each file matches
        file_scores: dict[int, int] = {}
        for word in words:
            pattern = f"%{word}%"
            rows = self.conn.execute(
                """SELECT DISTINCT f.id
                   FROM files f
                   LEFT JOIN file_tags ft ON f.id = ft.file_id
                   LEFT JOIN tags t ON ft.tag_id = t.id
                   LEFT JOIN file_comments fc ON f.id = fc.file_id
                   WHERE f.original_name LIKE ? COLLATE NOCASE
                      OR f.metadata_text LIKE ? COLLATE NOCASE
                      OR f.file_type LIKE ? COLLATE NOCASE
                      OR t.name LIKE ? COLLATE NOCASE
                      OR fc.comment LIKE ? COLLATE NOCASE""",
                (pattern, pattern, pattern, pattern, pattern),
            ).fetchall()
            for row in rows:
                file_scores[row["id"]] = file_scores.get(row["id"], 0) + 1

        if not file_scores:
            return []

        # Sort by match count descending (most relevant first), then by ID descending (recent first)
        sorted_ids = sorted(file_scores.keys(), key=lambda fid: (-file_scores[fid], -fid))

        results = []
        for fid in sorted_ids:
            row = self.conn.execute(
                """SELECT f.*, fo.name AS folder_name, p.name AS project_name
                   FROM files f
                   JOIN folders fo ON f.folder_id = fo.id
                   JOIN projects p ON fo.project_id = p.id
                   WHERE f.id = ?""",
                (fid,),
            ).fetchone()
            if row:
                entry = dict(row)
                entry["tags"] = self.get_file_tags(fid)
                entry["match_score"] = file_scores[fid]
                results.append(entry)
        return results
