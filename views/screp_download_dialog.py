"""
Screp download dialog - shown when screp executable is not found.
"""
from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
)
from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices

from config.settings import Settings


class ScrepDownloadDialog(QDialog):
    """
    Dialog shown when screp executable is not found.

    Prompts user to download screp and place it in the application directory.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.settings = Settings()
        self._setup_ui()

    def _setup_ui(self):
        """Initialize the dialog UI."""
        self.setWindowTitle("screp 필요")
        self.setFixedSize(450, 200)
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 24, 24, 24)

        # Warning icon and title
        title_label = QLabel("⚠️ screp 실행 파일을 찾을 수 없습니다")
        title_label.setStyleSheet("""
            QLabel {
                font-size: 16px;
                font-weight: bold;
                color: #e74c3c;
            }
        """)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)

        # Description
        desc_label = QLabel(
            "GG Archive는 리플레이 파일 분석을 위해 screp이 필요합니다.\n"
            "아래 버튼을 클릭하여 screp을 다운로드한 후,\n"
            "압축을 풀고 screp.exe 파일을 프로그램 폴더에 넣어주세요."
        )
        desc_label.setStyleSheet("""
            QLabel {
                font-size: 13px;
                color: #2c3e50;
                line-height: 1.5;
            }
        """)
        desc_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        desc_label.setWordWrap(True)
        layout.addWidget(desc_label)

        layout.addStretch()

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.setSpacing(12)

        # Download button
        download_btn = QPushButton("screp 다운로드")
        download_btn.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 10px 24px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
            QPushButton:pressed {
                background-color: #21618c;
            }
        """)
        download_btn.clicked.connect(self._on_download_clicked)
        button_layout.addWidget(download_btn)

        # Close button
        close_btn = QPushButton("닫기")
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: #ecf0f1;
                color: #2c3e50;
                border: 1px solid #bdc3c7;
                border-radius: 6px;
                padding: 10px 24px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #d5dbdb;
            }
            QPushButton:pressed {
                background-color: #bdc3c7;
            }
        """)
        close_btn.clicked.connect(self.accept)
        button_layout.addWidget(close_btn)

        layout.addLayout(button_layout)

    def _on_download_clicked(self):
        """Open the screp download URL in the default browser."""
        QDesktopServices.openUrl(QUrl(self.settings.screp_download_url))
