import shutil
import sys
from pathlib import Path

import os

from PyQt5.QtCore import QEvent, Qt, QSortFilterProxyModel, QUrl, pyqtSignal
from PyQt5.QtGui import QDesktopServices
from PyQt5.QtWidgets import (
    QAction,
    QApplication,
    QComboBox,
    QCompleter,
    QDialog,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
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
        self._applying_theme = False
        self._is_hovering = False
        self.setFrameStyle(QFrame.StyledPanel | QFrame.Sunken)
        self.setMinimumHeight(200)
        self.setAcceptDrops(True)

        layout = QVBoxLayout(self)
        self._label = QLabel("Drop files here\nor click to browse")
        self._label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self._label)
        self.setCursor(Qt.PointingHandCursor)
        self._apply_theme()

    def _apply_theme(self):
        """Apply theme-aware colors for normal state."""
        palette = QApplication.palette()
        bg = palette.color(palette.Window)
        fg = palette.color(palette.WindowText)
        # Slightly offset background from window color for visual distinction
        r = min(255, max(0, bg.red() + (15 if bg.lightness() > 128 else -15)))
        g = min(255, max(0, bg.green() + (15 if bg.lightness() > 128 else -15)))
        b = min(255, max(0, bg.blue() + (15 if bg.lightness() > 128 else -15)))
        self._normal_bg = f"#{r:02x}{g:02x}{b:02x}"
        # Muted foreground
        mr = (fg.red() + bg.red()) // 2
        mg = (fg.green() + bg.green()) // 2
        mb = (fg.blue() + bg.blue()) // 2
        self._muted_fg = f"#{mr:02x}{mg:02x}{mb:02x}"
        # Border
        self._border_color = self._muted_fg
        # Hover colors
        self._hover_bg = "#e3f0ff" if bg.lightness() > 128 else "#1a3050"

        self._label.setStyleSheet(f"color: {self._muted_fg}; font-size: 18px; border: none;")
        if not self._is_hovering:
            self._set_normal_style()

    def _set_normal_style(self):
        self.setStyleSheet(
            f"DropZone {{ background-color: {self._normal_bg}; "
            f"border: 2px dashed {self._border_color}; border-radius: 8px; }}"
        )

    def _set_hover_style(self):
        self.setStyleSheet(
            f"DropZone {{ background-color: {self._hover_bg}; "
            f"border: 2px dashed #4a90d9; border-radius: 8px; }}"
        )

    def changeEvent(self, event):
        if event.type() == QEvent.PaletteChange and not self._applying_theme:
            self._applying_theme = True
            self._apply_theme()
            self._applying_theme = False
        super().changeEvent(event)

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
            self._is_hovering = True
            self._set_hover_style()
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
        self._is_hovering = False
        self._set_normal_style()

    def dropEvent(self, event):
        """Capture all dropped file paths and emit signal."""
        self._is_hovering = False
        self._set_normal_style()
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
        self.project_combo.setEditable(True)
        self.project_combo.setInsertPolicy(QComboBox.NoInsert)
        self._setup_filter_completer(self.project_combo, "Search or select a project...")
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
        self.folder_combo.setEditable(True)
        self.folder_combo.setInsertPolicy(QComboBox.NoInsert)
        self._setup_filter_completer(self.folder_combo, "Search or select a folder...")
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

        self.tags_input = TagChipInput()
        self.content_layout.addWidget(self.tags_input)

        self.tag_suggestions = TagSuggestionBar(self.tags_input)
        self.content_layout.addWidget(self.tag_suggestions)

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

    def _setup_filter_completer(self, combo: QComboBox, placeholder: str):
        """Attach a substring-matching completer to an editable QComboBox."""
        completer = QCompleter(combo.model(), combo)
        completer.setFilterMode(Qt.MatchContains)
        completer.setCaseSensitivity(Qt.CaseInsensitive)
        completer.setCompletionMode(QCompleter.PopupCompletion)
        combo.setCompleter(completer)
        combo.lineEdit().setPlaceholderText(placeholder)

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
        """Return the list of tags from the chip input."""
        return self.tags_input.get_tags()

    def get_comment(self) -> str:
        """Get the comment text."""
        return self.comment_input.text().strip()

    def set_projects(self, projects: list[dict]):
        """Populate the project dropdown. Each item stores the project ID as user data."""
        self.project_combo.clear()
        for p in projects:
            self.project_combo.addItem(p["name"], p["id"])
        self.project_combo.setCurrentIndex(-1)

    def set_folders(self, folders: list[dict]):
        """Populate the folder dropdown with nested breadcrumb display.

        Accepts either flat folders (with "name") or nested folders (with "display" and "depth").
        """
        self.folder_combo.clear()
        for f in folders:
            display = f.get("display", f["name"])
            self.folder_combo.addItem(display, f["id"])
        self.folder_combo.setCurrentIndex(-1)


class FlowLayout(QVBoxLayout):
    """Simple flow layout that wraps widgets into horizontal rows."""

    def __init__(self):
        super().__init__()
        self.setContentsMargins(0, 0, 0, 0)
        self.setSpacing(4)
        self._rows: list[QHBoxLayout] = []
        self._widgets: list[QWidget] = []

    def add_widget(self, widget: QWidget):
        """Add a widget to the flow (appends to last row or creates new)."""
        self._widgets.append(widget)
        self._rebuild()

    def remove_widget(self, widget: QWidget):
        """Remove a widget from the flow."""
        if widget in self._widgets:
            self._widgets.remove(widget)
            widget.deleteLater()
            self._rebuild()

    def clear_all(self):
        """Remove all widgets."""
        for w in self._widgets:
            w.deleteLater()
        self._widgets.clear()
        self._rebuild()

    def _rebuild(self):
        """Rebuild the row layouts from the widget list."""
        # Remove old rows
        while self.count():
            child = self.takeAt(0)
            if child.layout():
                while child.layout().count():
                    child.layout().takeAt(0)

        if not self._widgets:
            return

        # Build rows — simple approach: one horizontal layout wrapping widgets
        row = QHBoxLayout()
        row.setSpacing(6)
        for w in self._widgets:
            row.addWidget(w)
        row.addStretch()
        self.addLayout(row)


class TagChipInput(QWidget):
    """Tag input with text field and visual chips below.

    User types in the QLineEdit and presses Enter or comma to add a tag chip.
    Each chip has an 'x' button to remove it. get_tags() returns the list.
    """

    tags_changed = pyqtSignal()  # emitted when tags are added or removed

    def __init__(self):
        super().__init__()
        self._tags: list[str] = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        # Chips area (above input so selected tags are clearly visible)
        self._chips_container = QWidget()
        self._chips_layout = FlowLayout()
        self._chips_container.setLayout(self._chips_layout)
        self._chips_container.hide()
        layout.addWidget(self._chips_container)

        # Text input for typing new tags
        self.input = QLineEdit()
        self.input.setPlaceholderText("Type a tag and press Enter")
        self.input.returnPressed.connect(self._on_commit)
        self.input.textChanged.connect(self._on_text_changed)
        layout.addWidget(self.input)

    def _on_text_changed(self, text: str):
        """Auto-commit when user types a comma."""
        if "," in text:
            parts = text.split(",")
            for part in parts[:-1]:
                tag = part.strip()
                if tag:
                    self._add_tag(tag)
            # Keep whatever is after the last comma in the input
            self.input.setText(parts[-1].strip())

    def _on_commit(self):
        """Commit the current text as a tag."""
        tag = self.input.text().strip().rstrip(",").strip()
        if tag:
            self._add_tag(tag)
            self.input.clear()

    def _add_tag(self, tag: str):
        """Add a tag if not already present (case-insensitive check)."""
        if tag.lower() in {t.lower() for t in self._tags}:
            return
        self._tags.append(tag)
        self._add_chip(tag)
        self._chips_container.show()
        self.tags_changed.emit()

    def _add_chip(self, tag: str):
        """Create a visual chip widget for a tag."""
        chip = QFrame()
        chip.setStyleSheet(
            "QFrame { background-color: #e8f0fe; border: 1px solid #b0cffe; "
            "border-radius: 10px; padding: 2px 4px; }"
        )
        chip_layout = QHBoxLayout(chip)
        chip_layout.setContentsMargins(8, 2, 4, 2)
        chip_layout.setSpacing(4)

        label = QLabel(tag)
        label.setStyleSheet("color: #1a73e8; font-size: 11px; border: none; background: transparent;")
        chip_layout.addWidget(label)

        remove_btn = QPushButton("x")
        remove_btn.setFixedSize(16, 16)
        remove_btn.setCursor(Qt.PointingHandCursor)
        remove_btn.setStyleSheet(
            "QPushButton { color: #1a73e8; font-size: 10px; font-weight: bold; "
            "border: none; background: transparent; padding: 0; }"
            "QPushButton:hover { color: #cc3333; }"
        )
        remove_btn.clicked.connect(lambda: self._remove_tag(tag, chip))
        chip_layout.addWidget(remove_btn)

        self._chips_layout.add_widget(chip)

    def _remove_tag(self, tag: str, chip: QFrame):
        """Remove a tag and its chip."""
        self._tags = [t for t in self._tags if t.lower() != tag.lower()]
        self._chips_layout.remove_widget(chip)
        if not self._tags:
            self._chips_container.hide()
        self.tags_changed.emit()

    def get_tags(self) -> list[str]:
        """Return the current list of tags (from chips only, ignores uncommitted input)."""
        return list(self._tags)

    def set_tags(self, tags: list[str]):
        """Set the tag list (replaces all current tags)."""
        self._chips_layout.clear_all()
        self._tags.clear()
        for tag in tags:
            if tag.strip():
                self._tags.append(tag.strip())
                self._add_chip(tag.strip())
        self._chips_container.setVisible(bool(self._tags))
        self.tags_changed.emit()

    def clear(self):
        """Remove all tags and clear input."""
        self._chips_layout.clear_all()
        self._tags.clear()
        self.input.clear()
        self._chips_container.hide()


class TagSuggestionBar(QWidget):
    """Horizontal bar of clickable tag chips that add to a TagChipInput."""

    def __init__(self, tag_input: TagChipInput):
        super().__init__()
        self._tag_input = tag_input
        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(0, 4, 0, 0)
        self._layout.setSpacing(6)
        self._layout.addStretch()

        # Re-check dimming when tags change
        self._tag_input.tags_changed.connect(self._update_chip_states)

    def set_suggestions(self, tags: list[str]):
        """Replace all suggestion chips with a new set."""
        while self._layout.count():
            child = self._layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        if not tags:
            self.hide()
            return

        label = QLabel("Suggested:")
        label.setStyleSheet("color: #888; font-size: 10px;")
        self._layout.addWidget(label)

        for tag in tags:
            chip = QPushButton(tag)
            chip.setCursor(Qt.PointingHandCursor)
            chip.setFixedHeight(24)
            chip.clicked.connect(lambda checked, t=tag: self._on_chip_clicked(t))
            self._layout.addWidget(chip)

        self._layout.addStretch()
        self._update_chip_states()
        self.show()

    def _current_tags_lower(self) -> set[str]:
        """Get current tags from the linked TagChipInput (lowercased)."""
        return {t.lower() for t in self._tag_input.get_tags()}

    def _on_chip_clicked(self, tag: str):
        """Add the suggested tag to the input if not already present."""
        if tag.lower() in self._current_tags_lower():
            return
        self._tag_input._add_tag(tag)

    def _update_chip_states(self):
        """Dim suggestion chips that are already added as tags."""
        current = self._current_tags_lower()
        for i in range(self._layout.count()):
            item = self._layout.itemAt(i)
            widget = item.widget()
            if not isinstance(widget, QPushButton):
                continue
            tag = widget.text()
            if tag.lower() in current:
                widget.setStyleSheet(
                    "QPushButton { background-color: #e0e0e0; color: #aaa; "
                    "border: 1px solid #ccc; border-radius: 10px; padding: 2px 10px; "
                    "font-size: 11px; }"
                )
            else:
                widget.setStyleSheet(
                    "QPushButton { background-color: #e8f0fe; color: #1a73e8; "
                    "border: 1px solid #b0cffe; border-radius: 10px; padding: 2px 10px; "
                    "font-size: 11px; }"
                    "QPushButton:hover { background-color: #d2e3fc; }"
                )


BADGE_COLORS = {
    ".xlsx": "#217346", ".xls": "#217346",
    ".docx": "#2b579a", ".doc": "#2b579a",
    ".pptx": "#d24726", ".ppt": "#d24726",
    ".pdf": "#e44d26",
    ".png": "#6d4c9f", ".jpg": "#6d4c9f", ".jpeg": "#6d4c9f",
    ".csv": "#1a73e8",
    ".py": "#3572a5", ".js": "#f1e05a", ".ts": "#3178c6",
}


class SearchResultsPanel(QFrame):
    """Panel displaying search results as a styled list."""

    result_clicked = pyqtSignal(dict)  # emits the file record dict
    back_clicked = pyqtSignal()

    def __init__(self):
        super().__init__()
        self._applying_theme = False
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

        # List widget for results
        self.list_widget = QListWidget()
        self.list_widget.setAlternatingRowColors(True)
        self.list_widget.setCursor(Qt.PointingHandCursor)
        self.list_widget.itemClicked.connect(self._on_item_clicked)
        outer.addWidget(self.list_widget, stretch=1)

        # No-results label (hidden by default)
        self.no_results_label = QLabel()
        self.no_results_label.setAlignment(Qt.AlignCenter)
        self.no_results_label.hide()
        outer.addWidget(self.no_results_label)

        self._apply_theme()

    def _apply_theme(self):
        """Apply theme-aware colors for list hover/selected states."""
        palette = QApplication.palette()
        bg = palette.color(palette.Window)
        fg = palette.color(palette.WindowText)
        highlight = palette.color(palette.Highlight)
        is_dark = bg.lightness() < 128

        # Derive subtle hover/selected colors from the highlight
        if is_dark:
            hover_bg = f"rgba({highlight.red()}, {highlight.green()}, {highlight.blue()}, 60)"
            selected_bg = f"rgba({highlight.red()}, {highlight.green()}, {highlight.blue()}, 100)"
            border_color = "#444"
        else:
            hover_bg = "#e8f0fe"
            selected_bg = "#d2e3fc"
            border_color = "#eee"

        # Muted color for no-results
        mr = (fg.red() + bg.red()) // 2
        mg = (fg.green() + bg.green()) // 2
        mb = (fg.blue() + bg.blue()) // 2
        muted = f"#{mr:02x}{mg:02x}{mb:02x}"

        self.list_widget.setStyleSheet(
            f"QListWidget {{ border: none; }}"
            f"QListWidget::item {{ border-bottom: 1px solid {border_color}; padding: 2px; }}"
            f"QListWidget::item:hover {{ background-color: {hover_bg}; }}"
            f"QListWidget::item:selected {{ background-color: {selected_bg}; }}"
        )
        self.no_results_label.setStyleSheet(f"color: {muted}; font-size: 14px; padding: 40px;")

    def changeEvent(self, event):
        if event.type() == QEvent.PaletteChange and not self._applying_theme:
            self._applying_theme = True
            self._apply_theme()
            self._applying_theme = False
        super().changeEvent(event)

    def show_results(self, results: list[dict], query: str):
        """Display search results in the list widget."""
        self.list_widget.clear()

        count = len(results)
        self.header_label.setText(f'Search Results — {count} match{"es" if count != 1 else ""} for "{query}"')

        if not results:
            self.list_widget.hide()
            self.no_results_label.setText(f'No results found for "{query}"')
            self.no_results_label.show()
            return

        self.no_results_label.hide()
        self.list_widget.show()

        for file_record in results:
            item = QListWidgetItem(self.list_widget)
            widget = self._make_result_widget(file_record)
            size = widget.sizeHint()
            size.setHeight(max(size.height(), 40))
            item.setSizeHint(size)
            item.setData(Qt.UserRole, file_record)
            self.list_widget.setItemWidget(item, widget)

    def show_folder_files(self, results: list[dict], folder_name: str):
        """Display files from a folder (reuses same layout as search results)."""
        self.list_widget.clear()

        count = len(results)
        self.header_label.setText(f'{folder_name} — {count} file{"s" if count != 1 else ""}')

        if not results:
            self.list_widget.hide()
            self.no_results_label.setText(f'No files in "{folder_name}"')
            self.no_results_label.show()
            return

        self.no_results_label.hide()
        self.list_widget.show()

        for file_record in results:
            item = QListWidgetItem(self.list_widget)
            widget = self._make_result_widget(file_record)
            size = widget.sizeHint()
            size.setHeight(max(size.height(), 40))
            item.setSizeHint(size)
            item.setData(Qt.UserRole, file_record)
            self.list_widget.setItemWidget(item, widget)

    def _on_item_clicked(self, item: QListWidgetItem):
        """Emit the file record when a list item is clicked."""
        file_record = item.data(Qt.UserRole)
        if file_record:
            self.result_clicked.emit(file_record)

    def _make_result_widget(self, file_record: dict) -> QWidget:
        """Build a compact row widget for a search result."""
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(10)

        # File type badge
        ext = file_record.get("file_type", "")
        color = BADGE_COLORS.get(ext, "#888")
        badge = QLabel(ext)
        badge.setFixedWidth(48)
        badge.setAlignment(Qt.AlignCenter)
        badge.setStyleSheet(
            f"background-color: {color}; color: white; font-size: 10px; "
            "font-weight: bold; border-radius: 3px; padding: 2px 4px;"
        )
        layout.addWidget(badge)

        # Filename (bold)
        name_label = QLabel(f'<b>{file_record["original_name"]}</b>')
        name_label.setStyleSheet("font-size: 13px;")
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

        # File size (right-aligned)
        size = file_record.get("size_bytes", 0) or 0
        size_label = QLabel(format_size(size))
        size_label.setStyleSheet("color: #999; font-size: 11px;")
        layout.addWidget(size_label)

        return widget


class FileDetailPanel(QFrame):
    """Panel showing full details of a file with editable tags and comments."""

    back_clicked = pyqtSignal()
    save_clicked = pyqtSignal(int, list, str)  # file_id, new_tags_list, new_comment_text
    delete_comment_clicked = pyqtSignal(int)  # comment_id

    def __init__(self):
        super().__init__()
        self.setFrameStyle(QFrame.StyledPanel)
        self._file_id = None
        self._stored_path = None
        self._original_tags = []

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        # Scrollable content
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        content = QWidget()
        self.content_layout = QVBoxLayout(content)
        self.content_layout.setAlignment(Qt.AlignTop)

        # Header row: filename (left) + back button (right)
        header_row = QHBoxLayout()
        self.file_name_label = QLabel()
        self.file_name_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        header_row.addWidget(self.file_name_label)
        header_row.addStretch()
        self.top_back_btn = QPushButton("Back to Results")
        self.top_back_btn.setStyleSheet("padding: 6px 14px;")
        self.top_back_btn.clicked.connect(self.back_clicked.emit)
        header_row.addWidget(self.top_back_btn)
        self.content_layout.addLayout(header_row)

        self.file_info_label = QLabel()
        self.file_info_label.setStyleSheet("color: #666; font-size: 12px;")
        self.content_layout.addWidget(self.file_info_label)

        self.location_label = QLabel()
        self.location_label.setStyleSheet("font-size: 12px; margin-top: 4px;")
        self.content_layout.addWidget(self.location_label)

        # Open File / Open Folder buttons
        open_btns_row = QHBoxLayout()
        self.open_file_btn = QPushButton("Open File")
        self.open_file_btn.setStyleSheet("padding: 6px 14px; margin-top: 4px;")
        self.open_file_btn.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.open_file_btn.clicked.connect(self._on_open_file)
        open_btns_row.addWidget(self.open_file_btn)

        self.open_folder_btn = QPushButton("Open Folder")
        self.open_folder_btn.setStyleSheet("padding: 6px 14px; margin-top: 4px;")
        self.open_folder_btn.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.open_folder_btn.clicked.connect(self._on_open_folder)
        open_btns_row.addWidget(self.open_folder_btn)

        open_btns_row.addStretch()
        self.content_layout.addLayout(open_btns_row)

        # -- Editable Tags --
        self._add_separator()
        tags_header = QLabel("Tags:")
        tags_header.setStyleSheet("font-weight: bold; margin-top: 8px;")
        self.content_layout.addWidget(tags_header)

        self.tags_input = TagChipInput()
        self.content_layout.addWidget(self.tags_input)

        self.tag_suggestions = TagSuggestionBar(self.tags_input)
        self.content_layout.addWidget(self.tag_suggestions)

        # -- Editable Comments --
        self._add_separator()
        comments_header = QLabel("Comments:")
        comments_header.setStyleSheet("font-weight: bold; margin-top: 8px;")
        self.content_layout.addWidget(comments_header)

        # Container for existing comments (each with delete button)
        self.comments_container = QWidget()
        self.comments_layout = QVBoxLayout(self.comments_container)
        self.comments_layout.setContentsMargins(0, 0, 0, 0)
        self.comments_layout.setSpacing(4)
        self.content_layout.addWidget(self.comments_container)

        # New comment input row
        comment_row = QHBoxLayout()
        self.new_comment_input = QLineEdit()
        self.new_comment_input.setPlaceholderText("Add a new comment...")
        comment_row.addWidget(self.new_comment_input, stretch=1)
        add_comment_btn = QPushButton("Add")
        add_comment_btn.setStyleSheet("padding: 6px 14px;")
        add_comment_btn.clicked.connect(self._on_add_comment)
        comment_row.addWidget(add_comment_btn)
        self.content_layout.addLayout(comment_row)

        # Metadata text preview
        self._add_separator()
        self.meta_header = QLabel("Stored Text Content")
        self.meta_header.setStyleSheet("font-weight: bold; font-size: 13px; margin-top: 8px;")
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

        # Bottom button bar
        button_bar = QFrame()
        button_bar.setStyleSheet("border-top: 1px solid #ddd; padding: 8px;")
        button_layout = QHBoxLayout(button_bar)
        button_layout.setContentsMargins(8, 8, 8, 8)

        button_layout.addStretch()

        save_btn = QPushButton("Save Changes")
        save_btn.setStyleSheet(
            "padding: 8px 20px; background-color: #4a90d9; color: white; "
            "border: none; border-radius: 4px; font-weight: bold;"
        )
        save_btn.clicked.connect(self._on_save)
        button_layout.addWidget(save_btn)

        outer.addWidget(button_bar)

    def _add_separator(self):
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet("color: #ddd;")
        self.content_layout.addWidget(line)

    def populate(self, file_record: dict, comments: list[dict]):
        """Fill the detail panel with file data from the database."""
        self._file_id = file_record["id"]
        self._stored_path = file_record.get("stored_path", "")

        self.file_name_label.setText(file_record["original_name"])
        size_str = format_size(file_record.get("size_bytes", 0) or 0)
        self.file_info_label.setText(f'{file_record.get("file_type", "")}  |  {size_str}')

        project = file_record.get("project_name", "?")
        folder = file_record.get("folder_name", "?")
        self.location_label.setText(f'Location: {project} / {folder}')

        # Tags — editable
        tags = file_record.get("tags", [])
        self._original_tags = list(tags)
        self.tags_input.set_tags(tags)

        # Comments — existing with delete buttons
        self._populate_comments(comments)

        # New comment input — clear
        self.new_comment_input.clear()

        # Metadata text preview
        meta_text = file_record.get("metadata_text", "")
        if meta_text and meta_text.strip():
            preview = meta_text[:500] + "..." if len(meta_text) > 500 else meta_text
            self.meta_preview.setText(preview)
            self.meta_header.show()
            self.meta_preview.show()
        else:
            self.meta_header.hide()
            self.meta_preview.hide()

    def _populate_comments(self, comments: list[dict]):
        """Build the list of existing comments with delete buttons."""
        # Clear existing comment widgets
        while self.comments_layout.count():
            child = self.comments_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        for c in comments:
            row = QHBoxLayout()
            label = QLabel(f'- {c["comment"]}')
            label.setWordWrap(True)
            label.setStyleSheet("font-size: 12px; color: #555;")
            row.addWidget(label, stretch=1)

            del_btn = QPushButton("x")
            del_btn.setFixedSize(22, 22)
            del_btn.setStyleSheet(
                "color: #cc3333; font-weight: bold; border: 1px solid #ddd; border-radius: 3px;"
            )
            del_btn.setToolTip("Delete this comment")
            comment_id = c["id"]
            del_btn.clicked.connect(lambda checked, cid=comment_id: self.delete_comment_clicked.emit(cid))
            row.addWidget(del_btn)

            container = QWidget()
            container.setLayout(row)
            self.comments_layout.addWidget(container)

        if not comments:
            hint = QLabel("No comments yet.")
            hint.setStyleSheet("color: #999; font-size: 11px;")
            self.comments_layout.addWidget(hint)

    def _on_open_file(self):
        """Open the file itself in the default application."""
        if not self._stored_path:
            return
        path = Path(self._stored_path)
        if not path.exists():
            QMessageBox.warning(
                self, "File Not Found",
                f"The file no longer exists at:\n{self._stored_path}"
            )
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))

    def _on_open_folder(self):
        """Open the file's containing folder in the system file browser."""
        if not self._stored_path:
            return
        path = Path(self._stored_path)
        if not path.exists():
            QMessageBox.warning(
                self, "File Not Found",
                f"The file no longer exists at:\n{self._stored_path}"
            )
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(path.parent)))

    def _on_save(self):
        """Emit save signal with current tags and new comment."""
        if self._file_id is None:
            return
        new_tags = self.tags_input.get_tags()
        new_comment = self.new_comment_input.text().strip()
        self.save_clicked.emit(self._file_id, new_tags, new_comment)

    def _on_add_comment(self):
        """Convenience: trigger save to add the new comment immediately."""
        self._on_save()


class Sidebar(QFrame):
    """Sidebar with expandable/collapsible project & folder tree."""

    folder_clicked = pyqtSignal(int, str)  # folder_id, folder_name
    create_project_requested = pyqtSignal()
    create_folder_requested = pyqtSignal(int)  # project_id
    create_subfolder_requested = pyqtSignal(int, int)  # project_id, parent_folder_id

    def __init__(self):
        super().__init__()
        self._applying_theme = False
        self.setFrameStyle(QFrame.StyledPanel)
        self.setFixedWidth(220)

        layout = QVBoxLayout(self)
        self.header = QLabel("Projects")
        self.header.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(self.header)

        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.itemClicked.connect(self._on_tree_item_clicked)
        self.tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self._on_context_menu)
        layout.addWidget(self.tree)

        # Hint shown when no projects exist yet
        self.hint_label = QLabel("Create a project with the\n'+' button to get started")
        self.hint_label.setAlignment(Qt.AlignCenter)
        self.hint_label.hide()
        layout.addWidget(self.hint_label)

        layout.addStretch()

        # Root folder path indicator
        self.root_label = QLabel("")
        self.root_label.setWordWrap(True)
        layout.addWidget(self.root_label)

        self._apply_theme()

    def _apply_theme(self):
        """Apply theme-aware colors from the current system palette."""
        palette = QApplication.palette()
        bg = palette.color(palette.Window).name()
        fg = palette.color(palette.WindowText).name()
        base_bg = palette.color(palette.Base).name()
        highlight = palette.color(palette.Highlight).name()
        highlight_text = palette.color(palette.HighlightedText).name()
        # Derive a muted color by blending foreground toward background
        fg_c = palette.color(palette.WindowText)
        bg_c = palette.color(palette.Window)
        r = (fg_c.red() + bg_c.red()) // 2
        g = (fg_c.green() + bg_c.green()) // 2
        b = (fg_c.blue() + bg_c.blue()) // 2
        muted = f"#{r:02x}{g:02x}{b:02x}"

        self.setStyleSheet(
            f"background-color: {bg}; color: {fg}; border-radius: 4px;"
        )
        self.header.setStyleSheet(f"font-weight: bold; font-size: 14px; color: {fg};")
        self.tree.setStyleSheet(
            f"QTreeWidget {{ background-color: {base_bg}; color: {fg};"
            f" border: none; font-size: 13px; }}"
            f" QTreeWidget::item:selected {{ background-color: {highlight};"
            f" color: {highlight_text}; }}"
        )
        self.hint_label.setStyleSheet(f"color: {muted}; font-size: 11px; padding: 12px;")
        self.root_label.setStyleSheet(f"color: {muted}; font-size: 10px; padding: 4px;")

    def changeEvent(self, event):
        """Re-apply theme when system palette changes (dark/light mode switch)."""
        if event.type() == QEvent.PaletteChange and not self._applying_theme:
            self._applying_theme = True
            self._apply_theme()
            self._applying_theme = False
        super().changeEvent(event)

    def set_root_folder_label(self, root_path: str):
        """Show the active root folder path at the bottom of the sidebar."""
        display = root_path
        if len(display) > 28:
            display = "..." + display[-25:]
        self.root_label.setText(display)
        self.root_label.setToolTip(root_path)

    def _on_tree_item_clicked(self, item: QTreeWidgetItem, column: int):
        """Emit folder_clicked when a folder (child item) is clicked."""
        folder_id = item.data(0, Qt.UserRole)
        if folder_id is not None:
            self.folder_clicked.emit(folder_id, item.text(0))

    def _on_context_menu(self, position):
        """Show context menu for creating projects/folders/subfolders."""
        item = self.tree.itemAt(position)
        menu = QMenu(self)

        if item is None:
            # Right-clicked on empty space
            action = menu.addAction("New Project")
            action.triggered.connect(self.create_project_requested.emit)
        else:
            folder_id = item.data(0, Qt.UserRole)
            project_id = item.data(0, Qt.UserRole + 1)

            if folder_id is None and project_id is not None:
                # Right-clicked on a project
                action = menu.addAction("New Folder")
                action.triggered.connect(lambda: self.create_folder_requested.emit(project_id))
                menu.addSeparator()
                action2 = menu.addAction("New Project")
                action2.triggered.connect(self.create_project_requested.emit)
            elif folder_id is not None and project_id is not None:
                # Right-clicked on a folder
                action = menu.addAction("New Subfolder")
                action.triggered.connect(
                    lambda: self.create_subfolder_requested.emit(project_id, folder_id)
                )
                menu.addSeparator()
                action2 = menu.addAction("New Project")
                action2.triggered.connect(self.create_project_requested.emit)

        if menu.actions():
            menu.exec_(self.tree.viewport().mapToGlobal(position))

    def load_from_database(self, db: Database):
        """Populate the sidebar tree from the database (with nested subfolders)."""
        self.tree.clear()
        projects = db.list_projects()
        if not projects:
            self.hint_label.show()
        else:
            self.hint_label.hide()
            for project in projects:
                project_item = QTreeWidgetItem(self.tree, [project["name"]])
                project_item.setData(0, Qt.UserRole, None)  # projects have no folder_id
                project_item.setData(0, Qt.UserRole + 1, project["id"])  # store project_id
                self._add_folder_children(db, project_item, project["id"], None)
        self.tree.expandAll()

    def _add_folder_children(self, db: Database, parent_item: QTreeWidgetItem,
                             project_id: int, parent_folder_id):
        """Recursively add folder children to a tree item."""
        folders = db.list_folders(project_id, parent_folder_id=parent_folder_id)
        for folder in folders:
            folder_item = QTreeWidgetItem(parent_item, [folder["name"]])
            folder_item.setData(0, Qt.UserRole, folder["id"])
            folder_item.setData(0, Qt.UserRole + 1, project_id)
            self._add_folder_children(db, folder_item, project_id, folder["id"])


class MainWindow(QMainWindow):
    """Main application window for jDocs."""

    def __init__(self):
        super().__init__()
        self._applying_theme = False
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

        # Search bar row: toggle + search input
        search_row = QHBoxLayout()

        self.sidebar_toggle = QPushButton("<")
        self.sidebar_toggle.setFixedSize(28, 28)
        self.sidebar_toggle.setToolTip("Collapse sidebar")
        self.sidebar_toggle.setStyleSheet(
            "QPushButton { border: none; font-weight: bold; color: #888; font-size: 14px; }"
            "QPushButton:hover { color: #333; }"
        )
        self.sidebar_toggle.clicked.connect(self._on_toggle_sidebar)
        search_row.addWidget(self.sidebar_toggle)

        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("Search files, tags, metadata...")
        self._apply_search_bar_theme()
        search_row.addWidget(self.search_bar)
        root_layout.addLayout(search_row)

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
        self.file_detail_panel.save_clicked.connect(self._on_file_save)
        self.file_detail_panel.delete_comment_clicked.connect(self._on_delete_comment)
        self.sidebar.folder_clicked.connect(self._on_folder_clicked)
        self.sidebar.create_project_requested.connect(self._on_sidebar_new_project)
        self.sidebar.create_folder_requested.connect(self._on_sidebar_new_folder)
        self.sidebar.create_subfolder_requested.connect(self._on_sidebar_new_subfolder)

    def _apply_search_bar_theme(self):
        """Apply theme-aware styling to the search bar."""
        palette = QApplication.palette()
        bg = palette.color(palette.Base).name()
        fg = palette.color(palette.WindowText).name()
        border = palette.color(palette.Mid).name()
        self.search_bar.setStyleSheet(
            f"padding: 8px; font-size: 14px; border-radius: 4px;"
            f" background-color: {bg}; color: {fg}; border: 1px solid {border};"
        )

    def changeEvent(self, event):
        """Re-apply theme-dependent styles when system palette changes."""
        if event.type() == QEvent.PaletteChange and not self._applying_theme:
            self._applying_theme = True
            self._apply_search_bar_theme()
            self._applying_theme = False
        super().changeEvent(event)

    def _on_toggle_sidebar(self):
        """Toggle sidebar visibility."""
        visible = self.sidebar.isVisible()
        self.sidebar.setVisible(not visible)
        self.sidebar_toggle.setText(">" if visible else "<")
        self.sidebar_toggle.setToolTip("Expand sidebar" if visible else "Collapse sidebar")

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

        # Load tag suggestions (global since no project selected yet)
        self.post_drop_panel.tag_suggestions.set_suggestions(
            self.db.get_popular_tags(limit=10)
        )

        # Switch to post-drop panel
        self.stack.setCurrentIndex(1)
        if len(results) == 1:
            self.file_info.setText(f'Reviewing: {results[0]["file_name"]}')
        else:
            self.file_info.setText(f'Reviewing {len(results)} files')
        self.file_info.setStyleSheet("color: #4a90d9; padding: 20px;")

    def _on_project_changed(self, index: int):
        """When project selection changes, update the folder dropdown and tag suggestions."""
        project_id = self.post_drop_panel.project_combo.currentData()
        if project_id is not None:
            folders = self.db.get_all_folders_nested(project_id)
            self.post_drop_panel.set_folders(folders)
            suggestions = self.db.get_popular_tags(project_id=project_id, limit=10)
        else:
            self.post_drop_panel.set_folders([])
            suggestions = self.db.get_popular_tags(limit=10)
        self.post_drop_panel.tag_suggestions.set_suggestions(suggestions)

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

    def _on_folder_clicked(self, folder_id: int, folder_name: str):
        """Show files in the clicked sidebar folder."""
        files = self.db.list_files(folder_id)
        # Enrich each file record with tags and project/folder names
        folder = self.db.get_folder(folder_id)
        project = self.db.get_project(folder["project_id"]) if folder else None
        for f in files:
            f["tags"] = self.db.get_file_tags(f["id"])
            f["folder_name"] = folder["name"] if folder else "?"
            f["project_name"] = project["name"] if project else "?"
        self.search_results_panel.show_folder_files(files, folder_name)
        self.stack.setCurrentIndex(2)
        count = len(files)
        self.file_info.setText(f'{folder_name}: {count} file{"s" if count != 1 else ""}')
        self.file_info.setStyleSheet("color: #4a90d9; padding: 20px;")

    def _on_result_clicked(self, file_record: dict):
        """Show file detail panel for a clicked search result."""
        self._refresh_file_detail(file_record["id"])
        self.stack.setCurrentIndex(3)
        self.file_info.setText(f'Viewing: {file_record["original_name"]}')
        self.file_info.setStyleSheet("color: #4a90d9; padding: 20px;")

    def _on_back_to_results(self):
        """Return to search results from file detail view."""
        self.stack.setCurrentIndex(2)
        self.file_info.setStyleSheet("color: #4a90d9; padding: 20px;")

    def _on_file_save(self, file_id: int, new_tags: list, new_comment: str):
        """Handle save from FileDetailPanel — diff tags, add comment, refresh."""
        original_tags = set(self.file_detail_panel._original_tags)
        current_tags = set(new_tags)

        # Remove tags that were deleted
        for tag in original_tags - current_tags:
            self.db.remove_tag_from_file(file_id, tag)

        # Add tags that are new
        for tag in current_tags - original_tags:
            self.db.add_tag_to_file(file_id, tag)

        # Add new comment if provided
        if new_comment:
            self.db.add_comment(file_id, new_comment)

        # Refresh the detail panel with updated data
        self._refresh_file_detail(file_id)

        self.file_info.setText("Changes saved")
        self.file_info.setStyleSheet("color: #2e7d32; padding: 20px;")

    def _on_delete_comment(self, comment_id: int):
        """Delete a comment and refresh the detail panel."""
        self.db.delete_comment(comment_id)
        file_id = self.file_detail_panel._file_id
        if file_id is not None:
            self._refresh_file_detail(file_id)

    def _refresh_file_detail(self, file_id: int):
        """Reload file data from DB and re-populate the detail panel."""
        file_record = self.db.get_file(file_id)
        if not file_record:
            return
        # Enrich with project/folder names and tags (like search_files does)
        folder = self.db.get_folder(file_record["folder_id"])
        if folder:
            project = self.db.get_project(folder["project_id"])
            # Build breadcrumb folder path for display
            folder_chain = self.db.get_folder_path(file_record["folder_id"])
            folder_display = " > ".join(f["name"] for f in folder_chain)
            file_record["folder_name"] = folder_display
            file_record["project_name"] = project["name"] if project else "?"
        else:
            file_record["folder_name"] = "?"
            file_record["project_name"] = "?"
        file_record["tags"] = self.db.get_file_tags(file_id)
        comments = self.db.get_file_comments(file_id)
        self.file_detail_panel.populate(file_record, comments)
        # Refresh tag suggestions for this file's project
        project_id = folder["project_id"] if folder else None
        self.file_detail_panel.tag_suggestions.set_suggestions(
            self.db.get_popular_tags(project_id=project_id, limit=10)
        )

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
        """Prompt user for a new folder name. Creates as subfolder if a folder is selected."""
        # Sync editable combo text to matching item
        proj_idx = self.post_drop_panel.project_combo.findText(
            self.post_drop_panel.project_combo.currentText())
        if proj_idx >= 0:
            self.post_drop_panel.project_combo.setCurrentIndex(proj_idx)
        project_id = self.post_drop_panel.project_combo.currentData()
        if project_id is None:
            QMessageBox.warning(self, "No Project", "Please select a project first.")
            return

        # If a folder is currently selected, create as subfolder
        fold_idx = self.post_drop_panel.folder_combo.findText(
            self.post_drop_panel.folder_combo.currentText())
        if fold_idx >= 0:
            self.post_drop_panel.folder_combo.setCurrentIndex(fold_idx)
        parent_folder_id = self.post_drop_panel.folder_combo.currentData()
        if parent_folder_id is not None:
            parent_display = self.post_drop_panel.folder_combo.currentText()
            title = "New Subfolder"
            prompt = f"Subfolder name (inside {parent_display}):"
        else:
            title = "New Folder"
            prompt = "Folder name:"

        name, ok = QInputDialog.getText(self, title, prompt)
        if ok and name.strip():
            name = sanitize_name(name)
            if not name:
                QMessageBox.warning(self, "Invalid Name", "Folder name contains only invalid characters.")
                return
            try:
                new_id = self.db.create_folder(project_id, name, parent_folder_id=parent_folder_id)
            except ValueError as e:
                QMessageBox.warning(self, "Depth Limit", str(e))
                return
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Could not create folder: {e}")
                return
            # Refresh folder dropdown with nested display and select the new folder
            folders = self.db.get_all_folders_nested(project_id)
            self.post_drop_panel.set_folders(folders)
            # Find and select the newly created folder by id
            for i in range(self.post_drop_panel.folder_combo.count()):
                if self.post_drop_panel.folder_combo.itemData(i) == new_id:
                    self.post_drop_panel.folder_combo.setCurrentIndex(i)
                    break
            # Refresh sidebar
            self.sidebar.load_from_database(self.db)

    def _on_sidebar_new_project(self):
        """Create a new project from the sidebar context menu."""
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
            self.sidebar.load_from_database(self.db)

    def _on_sidebar_new_folder(self, project_id: int):
        """Create a new root-level folder from the sidebar context menu."""
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
            self.sidebar.load_from_database(self.db)

    def _on_sidebar_new_subfolder(self, project_id: int, parent_folder_id: int):
        """Create a subfolder from the sidebar context menu."""
        name, ok = QInputDialog.getText(self, "New Subfolder", "Subfolder name:")
        if ok and name.strip():
            name = sanitize_name(name)
            if not name:
                QMessageBox.warning(self, "Invalid Name", "Folder name contains only invalid characters.")
                return
            try:
                self.db.create_folder(project_id, name, parent_folder_id=parent_folder_id)
            except ValueError as e:
                QMessageBox.warning(self, "Depth Limit", str(e))
                return
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Could not create subfolder: {e}")
                return
            self.sidebar.load_from_database(self.db)

    def _on_approve(self):
        """Save file record(s), copy to root folder, and persist to database."""
        panel = self.post_drop_panel

        # Validate project and folder selection
        # With editable combos, ensure typed text matches the selected item
        project_idx = panel.project_combo.findText(panel.project_combo.currentText())
        if project_idx >= 0:
            panel.project_combo.setCurrentIndex(project_idx)
        project_id = panel.project_combo.currentData()
        folder_idx = panel.folder_combo.findText(panel.folder_combo.currentText())
        if folder_idx >= 0:
            panel.folder_combo.setCurrentIndex(folder_idx)
        folder_id = panel.folder_combo.currentData()
        if project_id is None:
            QMessageBox.warning(self, "Missing Project", "Please select a project before approving.")
            return
        if folder_id is None:
            QMessageBox.warning(self, "Missing Folder", "Please select a folder before approving.")
            return

        # Build target directory using nested folder path
        project = self.db.get_project(project_id)
        folder_chain = self.db.get_folder_path(folder_id)
        folder_parts = [f["name"] for f in folder_chain]
        target_dir = self.root_folder / project["name"] / Path(*folder_parts)
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
