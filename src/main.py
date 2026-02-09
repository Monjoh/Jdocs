import sys
from pathlib import Path

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)


class DropZone(QFrame):
    """Placeholder for the drag & drop file input area."""

    def __init__(self):
        super().__init__()
        self.setFrameStyle(QFrame.StyledPanel | QFrame.Sunken)
        self.setMinimumHeight(200)
        self.setAcceptDrops(True)
        self.setStyleSheet(
            "DropZone { background-color: #f0f0f0; border: 2px dashed #aaa; border-radius: 8px; }"
        )

        layout = QVBoxLayout(self)
        label = QLabel("Drop files here")
        label.setAlignment(Qt.AlignCenter)
        label.setStyleSheet("color: #888; font-size: 18px; border: none;")
        layout.addWidget(label)


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

        self._add_sample_projects()

    def _add_sample_projects(self):
        """Add placeholder projects to show the tree structure."""
        project1 = QTreeWidgetItem(self.tree, ["Work Documents"])
        QTreeWidgetItem(project1, ["Reports"])
        QTreeWidgetItem(project1, ["Presentations"])

        project2 = QTreeWidgetItem(self.tree, ["Personal"])
        QTreeWidgetItem(project2, ["Photos"])
        QTreeWidgetItem(project2, ["Code Snippets"])

        self.tree.expandAll()


class MainWindow(QMainWindow):
    """Main application window for jDocs."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("jDocs")
        self.setMinimumSize(700, 500)
        self.resize(750, 550)

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
        content_layout.addWidget(self.sidebar)

        # Main panel with drop zone
        main_panel = QVBoxLayout()
        self.drop_zone = DropZone()
        main_panel.addWidget(self.drop_zone)

        # File info placeholder (will show metadata/tags after drop)
        self.file_info = QLabel("Select or drop a file to see details")
        self.file_info.setAlignment(Qt.AlignCenter)
        self.file_info.setStyleSheet("color: #aaa; padding: 20px;")
        main_panel.addWidget(self.file_info)

        content_layout.addLayout(main_panel, stretch=1)
        root_layout.addLayout(content_layout, stretch=1)


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("jDocs")
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
