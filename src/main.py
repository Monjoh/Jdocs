import sys
from pathlib import Path

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import (
    QApplication,
    QComboBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QScrollArea,
    QStackedWidget,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from database import Database
from extractor import extract


# -- Styles ------------------------------------------------------------------

DROPZONE_NORMAL = (
    "DropZone { background-color: #f0f0f0; border: 2px dashed #aaa; border-radius: 8px; }"
)
DROPZONE_HOVER = (
    "DropZone { background-color: #e3f0ff; border: 2px dashed #4a90d9; border-radius: 8px; }"
)


# -- Widgets ------------------------------------------------------------------


class DropZone(QFrame):
    """Drag & drop area that accepts files and emits their path."""

    file_dropped = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.setFrameStyle(QFrame.StyledPanel | QFrame.Sunken)
        self.setMinimumHeight(200)
        self.setAcceptDrops(True)
        self.setStyleSheet(DROPZONE_NORMAL)

        layout = QVBoxLayout(self)
        label = QLabel("Drop files here\nor click to browse")
        label.setAlignment(Qt.AlignCenter)
        label.setStyleSheet("color: #888; font-size: 18px; border: none;")
        layout.addWidget(label)
        self.setCursor(Qt.PointingHandCursor)

    # -- Click to browse ------------------------------------------------------

    def mousePressEvent(self, event):
        """Open a file dialog when the drop zone is clicked."""
        file_path, _ = QFileDialog.getOpenFileName(self, "Select a file")
        if file_path:
            self.file_dropped.emit(file_path)

    # -- Drag & drop event handlers -------------------------------------------

    def dragEnterEvent(self, event):
        """Accept the drag if it contains file URLs; show hover feedback."""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self.setStyleSheet(DROPZONE_HOVER)
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        """Allow the drag to continue over the widget."""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragLeaveEvent(self, event):
        """Restore normal styling when drag exits."""
        self.setStyleSheet(DROPZONE_NORMAL)

    def dropEvent(self, event):
        """Capture the first dropped file path and emit signal."""
        self.setStyleSheet(DROPZONE_NORMAL)
        urls = event.mimeData().urls()
        if urls:
            file_path = urls[0].toLocalFile()
            if file_path:
                self.file_dropped.emit(file_path)
        event.acceptProposedAction()


class PostDropPanel(QFrame):
    """Panel shown after a file is dropped — displays metadata and project/folder selection."""

    cancel_clicked = pyqtSignal()
    approve_clicked = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setFrameStyle(QFrame.StyledPanel)

        # Store current extraction result and source path
        self.extraction_result = None
        self.source_path = None

        # Outer layout: scrollable content on top, buttons pinned at bottom
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        # -- Scrollable content area ------------------------------------------
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        content = QWidget()
        self.content_layout = QVBoxLayout(content)
        self.content_layout.setAlignment(Qt.AlignTop)

        # -- File header ------------------------------------------------------
        self.file_name_label = QLabel()
        self.file_name_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        self.content_layout.addWidget(self.file_name_label)

        self.file_info_label = QLabel()
        self.file_info_label.setStyleSheet("color: #666; font-size: 12px;")
        self.content_layout.addWidget(self.file_info_label)

        self._add_separator()

        # -- Project / Folder selection ---------------------------------------
        project_label = QLabel("Project:")
        project_label.setStyleSheet("font-weight: bold; margin-top: 8px;")
        self.content_layout.addWidget(project_label)

        self.project_combo = QComboBox()
        self.content_layout.addWidget(self.project_combo)

        folder_label = QLabel("Folder:")
        folder_label.setStyleSheet("font-weight: bold; margin-top: 4px;")
        self.content_layout.addWidget(folder_label)

        self.folder_combo = QComboBox()
        self.content_layout.addWidget(self.folder_combo)

        self._add_separator()

        # -- Metadata preview -------------------------------------------------
        meta_header = QLabel("Extracted Metadata")
        meta_header.setStyleSheet("font-weight: bold; font-size: 13px; margin-top: 8px;")
        self.content_layout.addWidget(meta_header)

        self.metadata_label = QLabel()
        self.metadata_label.setWordWrap(True)
        self.metadata_label.setStyleSheet("font-size: 12px; color: #444; padding: 4px;")
        self.content_layout.addWidget(self.metadata_label)

        # -- Text preview -----------------------------------------------------
        self.text_preview_header = QLabel("Text Preview")
        self.text_preview_header.setStyleSheet("font-weight: bold; font-size: 13px; margin-top: 8px;")
        self.content_layout.addWidget(self.text_preview_header)

        self.text_preview_label = QLabel()
        self.text_preview_label.setWordWrap(True)
        self.text_preview_label.setStyleSheet(
            "font-size: 11px; color: #555; background-color: #fafafa; "
            "padding: 8px; border: 1px solid #ddd; border-radius: 4px;"
        )
        self.content_layout.addWidget(self.text_preview_label)

        scroll.setWidget(content)
        outer.addWidget(scroll, stretch=1)

        # -- Buttons (pinned at bottom, outside scroll area) ------------------
        button_bar = QFrame()
        button_bar.setStyleSheet("border-top: 1px solid #ddd; padding: 8px;")
        button_layout = QHBoxLayout(button_bar)
        button_layout.setContentsMargins(8, 8, 8, 8)
        button_layout.addStretch()

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setStyleSheet("padding: 8px 20px;")
        self.cancel_btn.clicked.connect(self.cancel_clicked.emit)
        button_layout.addWidget(self.cancel_btn)

        self.approve_btn = QPushButton("Approve && Move")
        self.approve_btn.setStyleSheet(
            "padding: 8px 20px; background-color: #4a90d9; color: white; "
            "border: none; border-radius: 4px; font-weight: bold;"
        )
        self.approve_btn.clicked.connect(self.approve_clicked.emit)
        button_layout.addWidget(self.approve_btn)

        outer.addWidget(button_bar)

    def _add_separator(self):
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet("color: #ddd;")
        self.content_layout.addWidget(line)

    def populate(self, file_path: str, result: dict):
        """Fill the panel with extraction data for the dropped file."""
        self.extraction_result = result
        self.source_path = file_path

        # -- File header --
        self.file_name_label.setText(result["file_name"])
        size_str = _format_size(result["size_bytes"])
        self.file_info_label.setText(f'{result["file_type"]}  |  {size_str}')

        # -- Metadata preview (type-specific) --
        self.metadata_label.setText(_format_metadata(result))

        # -- Text preview --
        text = result.get("text", "")
        if text.strip():
            preview = text[:200] + "..." if len(text) > 200 else text
            self.text_preview_label.setText(preview)
            self.text_preview_header.show()
            self.text_preview_label.show()
        else:
            self.text_preview_header.hide()
            self.text_preview_label.hide()

    def set_projects(self, projects: list[dict]):
        """Populate the project dropdown. Each item stores the project ID as user data."""
        self.project_combo.clear()
        self.project_combo.addItem("(No project selected)", None)
        for p in projects:
            self.project_combo.addItem(p["name"], p["id"])

    def set_folders(self, folders: list[dict]):
        """Populate the folder dropdown. Each item stores the folder ID as user data."""
        self.folder_combo.clear()
        self.folder_combo.addItem("(No folder selected)", None)
        for f in folders:
            self.folder_combo.addItem(f["name"], f["id"])


class Sidebar(QFrame):
    """Sidebar with expandable/collapsible project & folder tree."""

    def __init__(self):
        super().__init__()
        self.setFrameStyle(QFrame.StyledPanel)
        self.setFixedWidth(220)
        self.setStyleSheet("background-color: #e8e8e8; border-radius: 4px;")

        layout = QVBoxLayout(self)
        header = QLabel("Projects")
        header.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(header)

        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.setStyleSheet(
            "QTreeWidget { background-color: #e8e8e8; border: none; font-size: 13px; }"
        )
        layout.addWidget(self.tree)

    def load_from_database(self, db: Database):
        """Populate the sidebar tree from the database."""
        self.tree.clear()
        for project in db.list_projects():
            project_item = QTreeWidgetItem(self.tree, [project["name"]])
            for folder in db.list_folders(project["id"]):
                QTreeWidgetItem(project_item, [folder["name"]])
        self.tree.expandAll()


class MainWindow(QMainWindow):
    """Main application window for jDocs."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("jDocs")
        self.setMinimumSize(700, 500)
        self.resize(750, 550)

        # -- Database (in-memory for now, Session 07 will add persistent path) --
        self.db = Database(":memory:")
        self._seed_sample_data()

        central = QWidget()
        self.setCentralWidget(central)

        # Top-level vertical layout: search bar on top, content below
        root_layout = QVBoxLayout(central)

        # Search bar
        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("Search files, tags, metadata...")
        self.search_bar.setStyleSheet("padding: 8px; font-size: 14px; border-radius: 4px;")
        root_layout.addWidget(self.search_bar)

        # Content area: sidebar + main panel
        content_layout = QHBoxLayout()

        self.sidebar = Sidebar()
        self.sidebar.load_from_database(self.db)
        content_layout.addWidget(self.sidebar)

        # Main panel: stacked widget switching between DropZone and PostDropPanel
        main_panel = QVBoxLayout()

        self.stack = QStackedWidget()
        self.drop_zone = DropZone()
        self.post_drop_panel = PostDropPanel()
        self.stack.addWidget(self.drop_zone)       # index 0
        self.stack.addWidget(self.post_drop_panel)  # index 1
        main_panel.addWidget(self.stack)

        # Status label below the main panel
        self.file_info = QLabel("Drop a file to get started")
        self.file_info.setAlignment(Qt.AlignCenter)
        self.file_info.setStyleSheet("color: #aaa; padding: 20px;")
        main_panel.addWidget(self.file_info)

        content_layout.addLayout(main_panel, stretch=1)
        root_layout.addLayout(content_layout, stretch=1)

        # -- Connect signals --
        self.drop_zone.file_dropped.connect(self._on_file_dropped)
        self.post_drop_panel.cancel_clicked.connect(self._on_cancel)
        self.post_drop_panel.approve_clicked.connect(self._on_approve)
        self.post_drop_panel.project_combo.currentIndexChanged.connect(
            self._on_project_changed
        )

    def _seed_sample_data(self):
        """Add sample projects and folders so dropdowns have data to show."""
        p1 = self.db.create_project("Work Documents")
        self.db.create_folder(p1, "Reports")
        self.db.create_folder(p1, "Presentations")

        p2 = self.db.create_project("Personal")
        self.db.create_folder(p2, "Photos")
        self.db.create_folder(p2, "Code Snippets")

    def _on_file_dropped(self, file_path: str):
        """Called when a file is dropped — extract metadata and show the post-drop panel."""
        result = extract(file_path)

        # If extraction returned an error, show it in the status label and stay on DropZone
        if result["error"]:
            self.file_info.setText(f'Error: {result["error"]}')
            self.file_info.setStyleSheet("color: #cc3333; padding: 20px;")
            return

        # Populate the panel with extraction results
        self.post_drop_panel.populate(file_path, result)

        # Populate project dropdown from database
        self.post_drop_panel.set_projects(self.db.list_projects())

        # Switch to post-drop panel
        self.stack.setCurrentIndex(1)
        self.file_info.setText(f'Reviewing: {result["file_name"]}')
        self.file_info.setStyleSheet("color: #4a90d9; padding: 20px;")

    def _on_project_changed(self, index: int):
        """When project selection changes, update the folder dropdown."""
        project_id = self.post_drop_panel.project_combo.currentData()
        if project_id is not None:
            folders = self.db.list_folders(project_id)
            self.post_drop_panel.set_folders(folders)
        else:
            self.post_drop_panel.set_folders([])

    def _on_cancel(self):
        """Return to the DropZone view."""
        self.stack.setCurrentIndex(0)
        self.file_info.setText("Drop a file to get started")
        self.file_info.setStyleSheet("color: #aaa; padding: 20px;")

    def _on_approve(self):
        """Placeholder — Session 05 will implement file move + DB save."""
        result = self.post_drop_panel.extraction_result
        project_name = self.post_drop_panel.project_combo.currentText()
        folder_name = self.post_drop_panel.folder_combo.currentText()
        print(f'[Approve] File: {result["file_name"]} -> Project: {project_name}, Folder: {folder_name}')
        self.stack.setCurrentIndex(0)
        self.file_info.setText("Drop a file to get started")
        self.file_info.setStyleSheet("color: #aaa; padding: 20px;")


# -- Helpers ------------------------------------------------------------------


def _format_size(size_bytes: int) -> str:
    """Format a byte count into a human-readable string."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    else:
        return f"{size_bytes / (1024 * 1024):.1f} MB"


def _format_metadata(result: dict) -> str:
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


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("jDocs")
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
