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
    """Placeholder sidebar for projects/folders navigation."""

    def __init__(self):
        super().__init__()
        self.setFrameStyle(QFrame.StyledPanel)
        self.setFixedWidth(200)
        self.setStyleSheet("background-color: #e8e8e8; border-radius: 4px;")

        layout = QVBoxLayout(self)
        header = QLabel("Projects")
        header.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(header)

        placeholder = QLabel("No projects yet")
        placeholder.setStyleSheet("color: #999; font-size: 12px;")
        layout.addWidget(placeholder)
        layout.addStretch()


class MainWindow(QMainWindow):
    """Main application window for jDocs."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("jDocs")
        self.setMinimumSize(900, 600)

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
