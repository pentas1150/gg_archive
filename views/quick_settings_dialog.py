"""
Quick Settings Dialog - simplified settings for Player ID and Playtime only.
"""
from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QFormLayout,
    QLineEdit,
    QSpinBox,
    QHBoxLayout,
    QPushButton,
    QWidget,
    QLabel,
    QMessageBox,
)
from PySide6.QtCore import Signal

from config.app_config import AppConfig
from resources import get_icon_path


class QuickSettingsDialog(QDialog):
    """간소화된 설정 다이얼로그 - Player ID와 Playtime만 수정"""

    settings_changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.config = AppConfig.get_instance()
        self.setWindowTitle("설정")
        self.setMinimumWidth(400)
        self._setup_ui()
        self._load_values()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(24, 24, 24, 24)

        # Set dialog background to match All Stats widget
        self.setStyleSheet("""
            QDialog {
                background: #f5f6fa;
            }
            QLabel {
                color: #2c3e50;
            }
        """)

        # Title
        title = QLabel("빠른 설정")
        title.setStyleSheet("""
            QLabel {
                font-size: 18px;
                font-weight: bold;
                color: #2c3e50;
                background: transparent;
            }
        """)
        layout.addWidget(title)

        # Form layout
        form = QFormLayout()
        form.setSpacing(16)

        # Common style for labels
        label_style = """
            QLabel {
                font-size: 13px;
                color: #2c3e50;
                min-width: 130px;
            }
        """

        # Arrow icon paths for SpinBox (absolute path, forward slashes for QSS url())
        _arrow_up = get_icon_path("arrow_up.svg").resolve().as_posix()
        _arrow_down = get_icon_path("arrow_down.svg").resolve().as_posix()

        # Common style for inputs
        input_style = f"""
            QLineEdit, QSpinBox {{
                font-size: 13px;
                padding: 8px 12px;
                border: 1px solid #bdc3c7;
                border-radius: 4px;
                background: white;
                color: #2c3e50;
            }}
            QLineEdit:focus, QSpinBox:focus {{
                border: 2px solid #3498db;
            }}
            QSpinBox::up-button, QSpinBox::down-button {{
                background: #ecf0f1;
                border: 1px solid #bdc3c7;
                width: 20px;
            }}
            QSpinBox::up-button:hover, QSpinBox::down-button:hover {{
                background: #d5dbdb;
            }}
            QSpinBox::up-arrow {{
                image: url({_arrow_up});
                width: 10px;
                height: 10px;
            }}
            QSpinBox::down-arrow {{
                image: url({_arrow_down});
                width: 10px;
                height: 10px;
            }}
        """

        # Player ID
        player_label = QLabel("Player ID:")
        player_label.setStyleSheet(label_style)

        self.player_id_input = QLineEdit()
        self.player_id_input.setPlaceholderText("게임 ID를 입력하세요")
        self.player_id_input.setStyleSheet(input_style)
        form.addRow(player_label, self.player_id_input)

        # Playtime Threshold
        playtime_label = QLabel("Playtime Threshold:")
        playtime_label.setStyleSheet(label_style)

        playtime_widget = QWidget()
        playtime_layout = QHBoxLayout(playtime_widget)
        playtime_layout.setContentsMargins(0, 0, 0, 0)
        playtime_layout.setSpacing(10)

        self.minutes_input = QSpinBox()
        self.minutes_input.setRange(0, 999)
        self.minutes_input.setSuffix(" min")
        self.minutes_input.setMinimumWidth(90)
        self.minutes_input.setStyleSheet(input_style)

        self.seconds_input = QSpinBox()
        self.seconds_input.setRange(0, 59)
        self.seconds_input.setSuffix(" sec")
        self.seconds_input.setMinimumWidth(90)
        self.seconds_input.setStyleSheet(input_style)

        playtime_layout.addWidget(self.minutes_input)
        playtime_layout.addWidget(self.seconds_input)
        playtime_layout.addStretch()

        form.addRow(playtime_label, playtime_widget)
        layout.addLayout(form)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setContentsMargins(0, 10, 0, 0)
        btn_layout.addStretch()

        cancel_btn = QPushButton("취소")
        cancel_btn.setStyleSheet("""
            QPushButton {
                font-size: 13px;
                padding: 8px 20px;
                background: #ecf0f1;
                color: #2c3e50;
                border: 1px solid #bdc3c7;
                border-radius: 4px;
                min-width: 80px;
            }
            QPushButton:hover {
                background: #d5dbdb;
            }
            QPushButton:pressed {
                background: #bdc3c7;
            }
        """)
        cancel_btn.clicked.connect(self.reject)

        save_btn = QPushButton("저장")
        save_btn.setStyleSheet("""
            QPushButton {
                font-size: 13px;
                font-weight: bold;
                padding: 8px 20px;
                background: #3498db;
                color: white;
                border: none;
                border-radius: 4px;
                min-width: 80px;
            }
            QPushButton:hover {
                background: #2980b9;
            }
            QPushButton:pressed {
                background: #21618c;
            }
        """)
        save_btn.clicked.connect(self._on_save)

        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(save_btn)
        layout.addLayout(btn_layout)

    def _load_values(self):
        """Load values from config."""
        self.player_id_input.setText(self.config.player_id)
        self.minutes_input.setValue(self.config.playtime_minutes)
        self.seconds_input.setValue(self.config.playtime_seconds)

    def _on_save(self):
        """Save settings to config.json."""
        # Validate
        if not self.player_id_input.text().strip():
            QMessageBox.warning(self, "경고", "Player ID를 입력해주세요.")
            self.player_id_input.setFocus()
            return

        # Update config
        self.config.player_id = self.player_id_input.text().strip()
        self.config.set_playtime(
            self.minutes_input.value(),
            self.seconds_input.value()
        )

        # Save
        self.config.save()

        self.settings_changed.emit()
        self.accept()
