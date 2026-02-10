import shutil
import sys
from pathlib import Path

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import (
    QAction,
    QApplication,
    QComboBox,
    QDialog,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
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
from settings import derive_db_path, is_configured, load_settings, save_settings
from utils import format_metadata, format_size, sanitize_name, scan_untracked_files


# -- Styles ------------------------------------------------------------------

DROPZONE_NORMAL = (
    "DropZone { background-color: #f0f0f0; border: 2px dashed #aaa; border-radius: 8px; }"
)
DROPZONE_HOVER = (
    "DropZone { background-color: #e3f0ff; border: 2px dashed #4a90d9; border-radius: 8px; }"
)


# -- First Launch Dialog -------------------------------------------------------


class FirstLaunchDialog(QDialog):
    """Dialog shown on first launch to select the root folder."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Welcome to jDocs")
        self.setMinimumWidth(450)
        self.selected_folder = ""

        layout = QVBoxLayout(self)

        welcome = QLabel("Welcome to jDocs!")
        welcome.setStyleSheet("font-size: 18px; font-weight: bold;")
        layout.addWidget(welcome)

        explanation = QLabel(
            "Choose a root folder where jDocs will organize your files.\n\n"
            "All projects and folders will be created inside this directory.\n"
            "A hidden .jdocs folder will store the database."
        )
        explanation.setWordWrap(True)
        explanation.setStyleSheet("font-size: 13px; color: #444; margin: 8px 0;")
        layout.addWidget(explanation)

        # Folder picker row
        folder_row = QHBoxLayout()
        self.folder_label = QLabel("No folder selected")
        self.folder_label.setStyleSheet(
            "padding: 8px; background-color: #f5f5f5; border: 1px solid #ddd; border-radius: 4px;"
        )
        folder_row.addWidget(self.folder_label, stretch=1)

        browse_btn = QPushButton("Browse...")
        browse_btn.setStyleSheet("padding: 8px 16px;")
        browse_btn.clicked.connect(self._browse)
        folder_row.addWidget(browse_btn)
        layout.addLayout(folder_row)

        layout.addSpacing(12)

        # Confirm button
        self.confirm_btn = QPushButton("Set Root Folder && Start")
        self.confirm_btn.setEnabled(False)
        self.confirm_btn.setStyleSheet(
            "padding: 10px 24px; background-color: #4a90d9; color: white; "
            "border: none; border-radius: 4px; font-weight: bold; font-size: 14px;"
        )
        self.confirm_btn.clicked.connect(self._confirm)
        layout.addWidget(self.confirm_btn, alignment=Qt.AlignCenter)

    def _browse(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Root Folder")
        if folder:
            self.selected_folder = folder
            self.folder_label.setText(folder)
            self.confirm_btn.setEnabled(True)

    def _confirm(self):
        if self.selected_folder:
            self.accept()


# -- Widgets ------------------------------------------------------------------


MAX_BATCH_FILES = 10


class DropZone(QFrame):
    """Drag & drop area that accepts files and emits their paths."""

    files_dropped = pyqtSignal(list)

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
        paths, _ = QFileDialog.getOpenFileNames(self, "Select files")
        if paths:
            self.files_dropped.emit(paths)

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
        """Capture all dropped file paths and emit signal."""
        self.setStyleSheet(DROPZONE_NORMAL)
        urls = event.mimeData().urls()
        paths = [u.toLocalFile() for u in urls if u.toLocalFile()]
        if paths:
            self.files_dropped.emit(paths)
        event.acceptProposedAction()


class PostDropPanel(QFrame):
    """Panel shown after files are dropped — displays metadata and project/folder selection."""

    cancel_clicked = pyqtSignal()
    approve_clicked = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setFrameStyle(QFrame.StyledPanel)

        # Store extraction results and source paths (lists for batch support)
        self.extraction_results = []
        self.source_paths = []

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

        # -- Batch file list (hidden in single-file mode) ---------------------
        self.batch_list_label = QLabel()
        self.batch_list_label.setWordWrap(True)
        self.batch_list_label.setStyleSheet(
            "font-size: 11px; color: #555; background-color: #fafafa; "
            "padding: 8px; border: 1px solid #ddd; border-radius: 4px;"
        )
        self.batch_list_label.hide()
        self.content_layout.addWidget(self.batch_list_label)

        self._add_separator()

        # -- Project / Folder selection ---------------------------------------
        project_label = QLabel("Project:")
        project_label.setStyleSheet("font-weight: bold; margin-top: 8px;")
        self.content_layout.addWidget(project_label)

        project_row = QHBoxLayout()
        self.project_combo = QComboBox()
        project_row.addWidget(self.project_combo, stretch=1)
        self.new_project_btn = QPushButton("+")
        self.new_project_btn.setFixedWidth(30)
        self.new_project_btn.setToolTip("Create new project")
        project_row.addWidget(self.new_project_btn)
        self.content_layout.addLayout(project_row)

        folder_label = QLabel("Folder:")
        folder_label.setStyleSheet("font-weight: bold; margin-top: 4px;")
        self.content_layout.addWidget(folder_label)

        folder_row = QHBoxLayout()
        self.folder_combo = QComboBox()
        folder_row.addWidget(self.folder_combo, stretch=1)
        self.new_folder_btn = QPushButton("+")
        self.new_folder_btn.setFixedWidth(30)
        self.new_folder_btn.setToolTip("Create new folder in selected project")
        folder_row.addWidget(self.new_folder_btn)
        self.content_layout.addLayout(folder_row)

        self._add_separator()

        # -- Tags, Category, Comment ------------------------------------------
        tags_label = QLabel("Tags:")
        tags_label.setStyleSheet("font-weight: bold; margin-top: 8px;")
        self.content_layout.addWidget(tags_label)

        self.tags_input = QLineEdit()
        self.tags_input.setPlaceholderText("Enter tags separated by commas (e.g. finance, Q1, report)")
        self.content_layout.addWidget(self.tags_input)

        comment_label = QLabel("Comment:")
        comment_label.setStyleSheet("font-weight: bold; margin-top: 4px;")
        self.content_layout.addWidget(comment_label)

        self.comment_input = QLineEdit()
        self.comment_input.setPlaceholderText("Optional note about this file")
        self.content_layout.addWidget(self.comment_input)

        self._add_separator()

        # -- Metadata preview (single-file mode only) -------------------------
        self.meta_header = QLabel("Extracted Metadata")
        self.meta_header.setStyleSheet("font-weight: bold; font-size: 13px; margin-top: 8px;")
        self.content_layout.addWidget(self.meta_header)

        self.metadata_label = QLabel()
        self.metadata_label.setWordWrap(True)
        self.metadata_label.setStyleSheet("font-size: 12px; color: #444; padding: 4px;")
        self.content_layout.addWidget(self.metadata_label)

        # -- Text preview (single-file mode only) -----------------------------
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

        self.approve_btn = QPushButton("Approve && Copy")
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

    def is_batch(self) -> bool:
        """Return True if multiple files are loaded."""
        return len(self.extraction_results) > 1

    def populate(self, file_paths: list[str], results: list[dict]):
        """Fill the panel with extraction data for dropped file(s)."""
        self.extraction_results = results
        self.source_paths = file_paths

        if len(results) == 1:
            # -- Single-file mode --
            result = results[0]
            self.file_name_label.setText(result["file_name"])
            size_str = format_size(result["size_bytes"])
            self.file_info_label.setText(f'{result["file_type"]}  |  {size_str}')
            self.batch_list_label.hide()

            # Metadata preview
            self.metadata_label.setText(format_metadata(result))
            self.meta_header.show()
            self.metadata_label.show()

            # Text preview
            text = result.get("text", "")
            if text.strip():
                preview = text[:200] + "..." if len(text) > 200 else text
                self.text_preview_label.setText(preview)
                self.text_preview_header.show()
                self.text_preview_label.show()
            else:
                self.text_preview_header.hide()
                self.text_preview_label.hide()
        else:
            # -- Batch mode --
            total_size = sum(r["size_bytes"] for r in results)
            self.file_name_label.setText(f"{len(results)} files selected")
            self.file_info_label.setText(f"Total size: {format_size(total_size)}")

            # Build file list
            lines = []
            for r in results:
                lines.append(f'  {r["file_name"]}  ({format_size(r["size_bytes"])})')
            self.batch_list_label.setText("\n".join(lines))
            self.batch_list_label.show()

            # Hide single-file metadata/text previews
            self.meta_header.hide()
            self.metadata_label.hide()
            self.text_preview_header.hide()
            self.text_preview_label.hide()

    def clear_inputs(self):
        """Reset tag/comment fields for new files."""
        self.tags_input.clear()
        self.comment_input.clear()

    def get_tags(self) -> list[str]:
        """Parse comma-separated tags from the input field."""
        raw = self.tags_input.text().strip()
        if not raw:
            return []
        return [t.strip() for t in raw.split(",") if t.strip()]

    def get_comment(self) -> str:
        """Get the comment text."""
        return self.comment_input.text().strip()

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


class SearchResultsPanel(QFrame):
    """Panel displaying search results as clickable cards."""

    result_clicked = pyqtSignal(dict)  # emits the file record dict
    back_clicked = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setFrameStyle(QFrame.StyledPanel)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        # Header with result count and back button
        header_bar = QHBoxLayout()
        self.header_label = QLabel("Search Results")
        self.header_label.setStyleSheet("font-weight: bold; font-size: 14px; padding: 8px;")
        header_bar.addWidget(self.header_label)
        header_bar.addStretch()
        back_btn = QPushButton("Clear Search")
        back_btn.setStyleSheet("padding: 6px 14px;")
        back_btn.clicked.connect(self.back_clicked.emit)
        header_bar.addWidget(back_btn)
        outer.addLayout(header_bar)

        # Scrollable results area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        self.results_widget = QWidget()
        self.results_layout = QVBoxLayout(self.results_widget)
        self.results_layout.setAlignment(Qt.AlignTop)
        scroll.setWidget(self.results_widget)
        outer.addWidget(scroll, stretch=1)

    def show_results(self, results: list[dict], query: str):
        """Display search results as clickable cards."""
        # Clear previous results
        while self.results_layout.count():
            child = self.results_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        count = len(results)
        self.header_label.setText(f'Search Results — {count} match{"es" if count != 1 else ""} for "{query}"')

        if not results:
            no_results = QLabel(f'No results found for "{query}"')
            no_results.setAlignment(Qt.AlignCenter)
            no_results.setStyleSheet("color: #888; font-size: 14px; padding: 40px;")
            self.results_layout.addWidget(no_results)
            return

        for file_record in results:
            card = self._make_result_card(file_record)
            self.results_layout.addWidget(card)

    def _make_result_card(self, file_record: dict) -> QFrame:
        """Build a compact single-line clickable card for a search result."""
        card = QFrame()
        card.setFrameStyle(QFrame.StyledPanel)
        card.setStyleSheet(
            "QFrame { background-color: #fafafa; border: 1px solid #ddd; "
            "border-radius: 4px; padding: 4px 8px; margin: 1px; }"
            "QFrame:hover { background-color: #e8f0fe; border-color: #4a90d9; }"
        )
        card.setCursor(Qt.PointingHandCursor)

        layout = QHBoxLayout(card)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(8)

        # Filename (bold)
        name_label = QLabel(f'<b>{file_record["original_name"]}</b>')
        name_label.setStyleSheet("font-size: 12px;")
        layout.addWidget(name_label)

        # Project / Folder
        path_text = f'{file_record.get("project_name", "?")} / {file_record.get("folder_name", "?")}'
        path_label = QLabel(path_text)
        path_label.setStyleSheet("color: #666; font-size: 11px;")
        layout.addWidget(path_label)

        # Tags (if any)
        tags = file_record.get("tags", [])
        if tags:
            tags_label = QLabel(", ".join(tags))
            tags_label.setStyleSheet("color: #4a90d9; font-size: 11px;")
            layout.addWidget(tags_label)

        layout.addStretch()

        # Click handler — emit the file record
        card.mousePressEvent = lambda event, r=file_record: self.result_clicked.emit(r)

        return card


class FileDetailPanel(QFrame):
    """Read-only panel showing full details of a file from search results."""

    back_clicked = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setFrameStyle(QFrame.StyledPanel)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        # Scrollable content
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        content = QWidget()
        self.content_layout = QVBoxLayout(content)
        self.content_layout.setAlignment(Qt.AlignTop)

        self.file_name_label = QLabel()
        self.file_name_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        self.content_layout.addWidget(self.file_name_label)

        self.file_info_label = QLabel()
        self.file_info_label.setStyleSheet("color: #666; font-size: 12px;")
        self.content_layout.addWidget(self.file_info_label)

        self.location_label = QLabel()
        self.location_label.setStyleSheet("font-size: 12px; margin-top: 4px;")
        self.content_layout.addWidget(self.location_label)

        self.tags_label = QLabel()
        self.tags_label.setStyleSheet("color: #4a90d9; font-size: 12px; margin-top: 4px;")
        self.content_layout.addWidget(self.tags_label)

        self.comments_label = QLabel()
        self.comments_label.setWordWrap(True)
        self.comments_label.setStyleSheet("font-size: 12px; color: #555; margin-top: 4px;")
        self.content_layout.addWidget(self.comments_label)

        # Metadata text preview
        self.meta_header = QLabel("Stored Text Content")
        self.meta_header.setStyleSheet("font-weight: bold; font-size: 13px; margin-top: 12px;")
        self.content_layout.addWidget(self.meta_header)

        self.meta_preview = QLabel()
        self.meta_preview.setWordWrap(True)
        self.meta_preview.setStyleSheet(
            "font-size: 11px; color: #555; background-color: #fafafa; "
            "padding: 8px; border: 1px solid #ddd; border-radius: 4px;"
        )
        self.content_layout.addWidget(self.meta_preview)

        scroll.setWidget(content)
        outer.addWidget(scroll, stretch=1)

        # Back button pinned at bottom
        button_bar = QFrame()
        button_bar.setStyleSheet("border-top: 1px solid #ddd; padding: 8px;")
        button_layout = QHBoxLayout(button_bar)
        button_layout.setContentsMargins(8, 8, 8, 8)
        back_btn = QPushButton("Back to Results")
        back_btn.setStyleSheet("padding: 8px 20px;")
        back_btn.clicked.connect(self.back_clicked.emit)
        button_layout.addWidget(back_btn)
        button_layout.addStretch()
        outer.addWidget(button_bar)

    def populate(self, file_record: dict, comments: list[dict]):
        """Fill the detail panel with file data from the database."""
        self.file_name_label.setText(file_record["original_name"])
        size_str = format_size(file_record.get("size_bytes", 0) or 0)
        self.file_info_label.setText(f'{file_record.get("file_type", "")}  |  {size_str}')

        project = file_record.get("project_name", "?")
        folder = file_record.get("folder_name", "?")
        self.location_label.setText(f'Location: {project} / {folder}')

        tags = file_record.get("tags", [])
        if tags:
            self.tags_label.setText("Tags: " + ", ".join(tags))
            self.tags_label.show()
        else:
            self.tags_label.hide()

        if comments:
            comment_lines = [f'- {c["comment"]}' for c in comments]
            self.comments_label.setText("Comments:\n" + "\n".join(comment_lines))
            self.comments_label.show()
        else:
            self.comments_label.hide()

        meta_text = file_record.get("metadata_text", "")
        if meta_text and meta_text.strip():
            preview = meta_text[:500] + "..." if len(meta_text) > 500 else meta_text
            self.meta_preview.setText(preview)
            self.meta_header.show()
            self.meta_preview.show()
        else:
            self.meta_header.hide()
            self.meta_preview.hide()


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

        # Hint shown when no projects exist yet
        self.hint_label = QLabel("Create a project with the\n'+' button to get started")
        self.hint_label.setAlignment(Qt.AlignCenter)
        self.hint_label.setStyleSheet("color: #999; font-size: 11px; padding: 12px;")
        self.hint_label.hide()
        layout.addWidget(self.hint_label)

        layout.addStretch()

        # Root folder path indicator
        self.root_label = QLabel("")
        self.root_label.setStyleSheet("color: #777; font-size: 10px; padding: 4px;")
        self.root_label.setWordWrap(True)
        layout.addWidget(self.root_label)

    def set_root_folder_label(self, root_path: str):
        """Show the active root folder path at the bottom of the sidebar."""
        display = root_path
        if len(display) > 28:
            display = "..." + display[-25:]
        self.root_label.setText(display)
        self.root_label.setToolTip(root_path)

    def load_from_database(self, db: Database):
        """Populate the sidebar tree from the database."""
        self.tree.clear()
        projects = db.list_projects()
        if not projects:
            self.hint_label.show()
        else:
            self.hint_label.hide()
            for project in projects:
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

        # -- Settings & Database --
        self.settings = load_settings()
        if not is_configured(self.settings):
            if not self._run_first_launch():
                sys.exit(0)

        self.root_folder = Path(self.settings["root_folder"])
        db_path = self.settings["db_path"]
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.db = Database(db_path)

        # -- Menu bar --
        menu_bar = self.menuBar()
        settings_menu = menu_bar.addMenu("Settings")
        change_root_action = QAction("Change Root Folder...", self)
        change_root_action.triggered.connect(self._on_change_root_folder)
        settings_menu.addAction(change_root_action)

        scan_action = QAction("Scan for Untracked Files...", self)
        scan_action.triggered.connect(self._on_scan_untracked)
        settings_menu.addAction(scan_action)

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
        self.sidebar.set_root_folder_label(str(self.root_folder))
        self.sidebar.load_from_database(self.db)
        content_layout.addWidget(self.sidebar)

        # Main panel: stacked widget switching between DropZone and PostDropPanel
        main_panel = QVBoxLayout()

        self.stack = QStackedWidget()
        self.drop_zone = DropZone()
        self.post_drop_panel = PostDropPanel()
        self.search_results_panel = SearchResultsPanel()
        self.file_detail_panel = FileDetailPanel()
        self.stack.addWidget(self.drop_zone)           # index 0
        self.stack.addWidget(self.post_drop_panel)      # index 1
        self.stack.addWidget(self.search_results_panel)  # index 2
        self.stack.addWidget(self.file_detail_panel)     # index 3
        main_panel.addWidget(self.stack)

        # Status label below the main panel
        self.file_info = QLabel("Drop a file to get started")
        self.file_info.setAlignment(Qt.AlignCenter)
        self.file_info.setStyleSheet("color: #aaa; padding: 20px;")
        main_panel.addWidget(self.file_info)

        content_layout.addLayout(main_panel, stretch=1)
        root_layout.addLayout(content_layout, stretch=1)

        # -- Connect signals --
        self.drop_zone.files_dropped.connect(self._on_files_dropped)
        self.post_drop_panel.cancel_clicked.connect(self._on_cancel)
        self.post_drop_panel.approve_clicked.connect(self._on_approve)
        self.post_drop_panel.project_combo.currentIndexChanged.connect(
            self._on_project_changed
        )
        self.post_drop_panel.new_project_btn.clicked.connect(self._on_new_project)
        self.post_drop_panel.new_folder_btn.clicked.connect(self._on_new_folder)
        self.search_bar.returnPressed.connect(self._on_search)
        self.search_results_panel.result_clicked.connect(self._on_result_clicked)
        self.search_results_panel.back_clicked.connect(self._on_clear_search)
        self.file_detail_panel.back_clicked.connect(self._on_back_to_results)

    def _run_first_launch(self) -> bool:
        """Show first-launch dialog. Returns True if user selected a folder."""
        dialog = FirstLaunchDialog()
        if dialog.exec_() != QDialog.Accepted:
            return False
        root = dialog.selected_folder
        db_path = derive_db_path(root)
        self.settings["root_folder"] = root
        self.settings["db_path"] = db_path
        # Create .jdocs directory
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        save_settings(self.settings)
        return True

    def _on_change_root_folder(self):
        """Allow user to change the root folder via a dialog."""
        folder = QFileDialog.getExistingDirectory(self, "Select New Root Folder")
        if not folder:
            return
        reply = QMessageBox.question(
            self,
            "Change Root Folder",
            f"Change root folder to:\n{folder}\n\n"
            "This will create a new database in the new location.\n"
            "Your current data will remain in the old location.\n\nProceed?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return
        db_path = derive_db_path(folder)
        self.settings["root_folder"] = folder
        self.settings["db_path"] = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        save_settings(self.settings)
        QMessageBox.information(
            self, "Restart Required", "Please restart jDocs to use the new root folder."
        )

    def _on_scan_untracked(self):
        """Scan root folder for files not tracked in the database."""
        tracked = self.db.get_all_stored_paths()
        untracked = scan_untracked_files(self.root_folder, tracked)

        if not untracked:
            QMessageBox.information(
                self, "Scan Complete", "All files in the root folder are tracked by jDocs."
            )
            return

        # Build a summary message
        lines = [f"Found {len(untracked)} untracked file(s):\n"]
        for f in untracked[:50]:
            lines.append(f'  {f["relative_path"]}  ({format_size(f["size_bytes"])})')
        if len(untracked) > 50:
            lines.append(f"\n  ... and {len(untracked) - 50} more")
        lines.append("\nThese files exist in the root folder but are not tracked by jDocs.")

        QMessageBox.information(self, "Scan Complete", "\n".join(lines))

    def _on_files_dropped(self, file_paths: list[str]):
        """Called when file(s) are dropped — extract metadata and show the post-drop panel."""
        # Enforce batch limit
        if len(file_paths) > MAX_BATCH_FILES:
            QMessageBox.warning(
                self,
                "Too Many Files",
                f"You can drop up to {MAX_BATCH_FILES} files at once.\n"
                f"You selected {len(file_paths)} files.",
            )
            return

        # Extract metadata for each file, collect successes and errors
        results = []
        valid_paths = []
        errors = []
        for fp in file_paths:
            result = extract(fp)
            if result["error"]:
                errors.append(f'{result["file_name"]}: {result["error"]}')
            else:
                results.append(result)
                valid_paths.append(fp)

        # If all files failed, show errors and abort
        if not results:
            error_msg = "\n".join(errors)
            QMessageBox.warning(self, "Extraction Error", error_msg)
            self.file_info.setText("Extraction failed for all files")
            self.file_info.setStyleSheet("color: #cc3333; padding: 20px;")
            return

        # If some files failed, warn but continue with the rest
        if errors:
            error_msg = "The following files could not be processed and were skipped:\n\n"
            error_msg += "\n".join(errors)
            QMessageBox.warning(self, "Some Files Skipped", error_msg)

        # Populate the panel with extraction results and reset input fields
        self.post_drop_panel.populate(valid_paths, results)
        self.post_drop_panel.clear_inputs()

        # Populate project dropdown from database
        self.post_drop_panel.set_projects(self.db.list_projects())

        # Switch to post-drop panel
        self.stack.setCurrentIndex(1)
        if len(results) == 1:
            self.file_info.setText(f'Reviewing: {results[0]["file_name"]}')
        else:
            self.file_info.setText(f'Reviewing {len(results)} files')
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

    def _on_search(self):
        """Run search query and display results."""
        query = self.search_bar.text().strip()
        if not query:
            self._on_clear_search()
            return
        results = self.db.search_files(query)
        self.search_results_panel.show_results(results, query)
        self.stack.setCurrentIndex(2)
        count = len(results)
        self.file_info.setText(f'Found {count} result{"s" if count != 1 else ""} for "{query}"')
        self.file_info.setStyleSheet("color: #4a90d9; padding: 20px;")

    def _on_clear_search(self):
        """Clear search and return to DropZone."""
        self.search_bar.clear()
        self.stack.setCurrentIndex(0)
        self.file_info.setText("Drop a file to get started")
        self.file_info.setStyleSheet("color: #aaa; padding: 20px;")

    def _on_result_clicked(self, file_record: dict):
        """Show file detail panel for a clicked search result."""
        comments = self.db.get_file_comments(file_record["id"])
        self.file_detail_panel.populate(file_record, comments)
        self.stack.setCurrentIndex(3)
        self.file_info.setText(f'Viewing: {file_record["original_name"]}')
        self.file_info.setStyleSheet("color: #4a90d9; padding: 20px;")

    def _on_back_to_results(self):
        """Return to search results from file detail view."""
        self.stack.setCurrentIndex(2)
        self.file_info.setStyleSheet("color: #4a90d9; padding: 20px;")

    def _on_new_project(self):
        """Prompt user for a new project name, create it in DB, refresh dropdown."""
        name, ok = QInputDialog.getText(self, "New Project", "Project name:")
        if ok and name.strip():
            name = sanitize_name(name)
            if not name:
                QMessageBox.warning(self, "Invalid Name", "Project name contains only invalid characters.")
                return
            try:
                self.db.create_project(name)
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Could not create project: {e}")
                return
            # Refresh dropdown and select the new project
            self.post_drop_panel.set_projects(self.db.list_projects())
            idx = self.post_drop_panel.project_combo.findText(name)
            if idx >= 0:
                self.post_drop_panel.project_combo.setCurrentIndex(idx)
            # Refresh sidebar
            self.sidebar.load_from_database(self.db)

    def _on_new_folder(self):
        """Prompt user for a new folder name under the selected project."""
        project_id = self.post_drop_panel.project_combo.currentData()
        if project_id is None:
            QMessageBox.warning(self, "No Project", "Please select a project first.")
            return
        name, ok = QInputDialog.getText(self, "New Folder", "Folder name:")
        if ok and name.strip():
            name = sanitize_name(name)
            if not name:
                QMessageBox.warning(self, "Invalid Name", "Folder name contains only invalid characters.")
                return
            try:
                self.db.create_folder(project_id, name)
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Could not create folder: {e}")
                return
            # Refresh folder dropdown and select the new folder
            folders = self.db.list_folders(project_id)
            self.post_drop_panel.set_folders(folders)
            idx = self.post_drop_panel.folder_combo.findText(name)
            if idx >= 0:
                self.post_drop_panel.folder_combo.setCurrentIndex(idx)
            # Refresh sidebar
            self.sidebar.load_from_database(self.db)

    def _on_approve(self):
        """Save file record(s), copy to root folder, and persist to database."""
        panel = self.post_drop_panel

        # Validate project and folder selection
        project_id = panel.project_combo.currentData()
        folder_id = panel.folder_combo.currentData()
        if project_id is None:
            QMessageBox.warning(self, "Missing Project", "Please select a project before approving.")
            return
        if folder_id is None:
            QMessageBox.warning(self, "Missing Folder", "Please select a folder before approving.")
            return

        # Build target directory
        project = self.db.get_project(project_id)
        folder = self.db.get_folder(folder_id)
        target_dir = self.root_folder / project["name"] / folder["name"]
        target_dir.mkdir(parents=True, exist_ok=True)

        tags = panel.get_tags()
        comment = panel.get_comment()

        saved_count = 0
        errors = []

        for source_path, result in zip(panel.source_paths, panel.extraction_results):
            source = Path(source_path)

            # Validate source file still exists
            if not source.exists():
                errors.append(f'{result["file_name"]}: original file no longer exists')
                continue

            # Determine target path with duplicate handling
            target = target_dir / source.name
            if target.exists():
                stem = source.stem
                suffix = source.suffix
                counter = 1
                while target.exists():
                    target = target_dir / f"{stem}_{counter}{suffix}"
                    counter += 1

            # Copy file
            try:
                shutil.copy2(str(source), str(target))
            except OSError as e:
                errors.append(f'{result["file_name"]}: copy failed — {e}')
                continue

            # Register in database — clean up copied file if DB write fails
            try:
                file_id = self.db.add_file(
                    original_name=result["file_name"],
                    stored_path=str(target),
                    folder_id=folder_id,
                    size_bytes=result["size_bytes"],
                    file_type=result["file_type"],
                    metadata_text=result.get("text", ""),
                )
                for tag in tags:
                    self.db.add_tag_to_file(file_id, tag)
                if comment:
                    self.db.add_comment(file_id, comment)
                saved_count += 1
            except Exception as e:
                try:
                    target.unlink(missing_ok=True)
                except OSError:
                    pass
                errors.append(f'{result["file_name"]}: database error — {e}')

        # Show results
        if errors:
            error_msg = f"Saved {saved_count} file(s). The following failed:\n\n"
            error_msg += "\n".join(errors)
            QMessageBox.warning(self, "Some Files Failed", error_msg)

        # Refresh sidebar and return to DropZone
        self.sidebar.load_from_database(self.db)
        self.stack.setCurrentIndex(0)
        if saved_count > 0:
            if saved_count == 1 and len(panel.extraction_results) == 1:
                self.file_info.setText(f'Saved: {panel.extraction_results[0]["file_name"]}')
            else:
                self.file_info.setText(f'Saved {saved_count} file(s)')
            self.file_info.setStyleSheet("color: #2e7d32; padding: 20px;")
        else:
            self.file_info.setText("No files were saved")
            self.file_info.setStyleSheet("color: #cc3333; padding: 20px;")



def main():
    app = QApplication(sys.argv)
    app.setApplicationName("jDocs")
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
