"""
Settings widget for configuration.
"""
from pathlib import Path
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QFormLayout,
    QLabel,
    QLineEdit,
    QSpinBox,
    QPushButton,
    QFileDialog,
    QGroupBox,
    QMessageBox,
    QComboBox,
)
from PySide6.QtCore import Signal

from common.const import TypeTimeZone

from config.app_config import AppConfig


class SettingsWidget(QWidget):
    """Widget for editing application settings."""

    settings_saved = Signal()  # Emitted when settings are saved

    def __init__(self, parent=None):
        super().__init__(parent)
        self.config = AppConfig.get_instance()
        self._setup_ui()
        self._load_values()

    def _setup_ui(self):
        """Setup the UI layout."""
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(40, 40, 40, 40)

        # Title
        title = QLabel("설정")
        title.setStyleSheet("""
            QLabel {
                font-size: 28px;
                font-weight: bold;
                color: #2c3e50;
                padding: 10px 0 20px 0;
            }
        """)
        layout.addWidget(title)

        # Settings group
        group = QGroupBox("기본 설정")
        group.setStyleSheet("""
            QGroupBox {
                font-size: 16px;
                font-weight: bold;
                color: #34495e;
                border: 2px solid #bdc3c7;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 20px;
                padding: 0 10px;
            }
        """)
        group_layout = QFormLayout(group)
        group_layout.setSpacing(20)
        group_layout.setContentsMargins(30, 30, 30, 30)

        # Common style for labels
        label_style = """
            QLabel {
                font-size: 14px;
                color: #2c3e50;
                min-width: 150px;
            }
        """

        # Common style for inputs
        input_style = """
            QLineEdit, QSpinBox, QComboBox {
                font-size: 14px;
                padding: 8px 12px;
                border: 1px solid #bdc3c7;
                border-radius: 4px;
                background: white;
                color: #2c3e50;
            }
            QLineEdit:focus, QSpinBox:focus, QComboBox:focus {
                border: 2px solid #3498db;
            }
            QSpinBox::up-button, QSpinBox::down-button {
                background: #ecf0f1;
                border: 1px solid #bdc3c7;
                width: 20px;
            }
            QSpinBox::up-button:hover, QSpinBox::down-button:hover {
                background: #d5dbdb;
            }
            QSpinBox::up-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-bottom: 5px solid #2c3e50;
                width: 0;
                height: 0;
            }
            QSpinBox::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid #2c3e50;
                width: 0;
                height: 0;
            }
            QComboBox::drop-down {
                border: none;
                width: 30px;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid #2c3e50;
                width: 0;
                height: 0;
            }
            QComboBox QAbstractItemView {
                background: white;
                color: #2c3e50;
                selection-background-color: #3498db;
                selection-color: white;
                border: 1px solid #bdc3c7;
            }
        """

        # Player ID
        player_label = QLabel("Player ID:")
        player_label.setStyleSheet(label_style)

        self.player_id_input = QLineEdit()
        self.player_id_input.setPlaceholderText("게임 ID를 입력하세요")
        self.player_id_input.setMinimumWidth(300)
        self.player_id_input.setStyleSheet(input_style)
        group_layout.addRow(player_label, self.player_id_input)

        # Playtime Threshold (분:초)
        playtime_label = QLabel("Playtime Threshold:")
        playtime_label.setStyleSheet(label_style)

        playtime_widget = QWidget()
        playtime_layout = QHBoxLayout(playtime_widget)
        playtime_layout.setContentsMargins(0, 0, 0, 0)
        playtime_layout.setSpacing(10)

        self.minutes_input = QSpinBox()
        self.minutes_input.setRange(0, 999)
        self.minutes_input.setSuffix(" min")
        self.minutes_input.setMinimumWidth(100)
        self.minutes_input.setStyleSheet(input_style)

        self.seconds_input = QSpinBox()
        self.seconds_input.setRange(0, 59)
        self.seconds_input.setSuffix(" sec")
        self.seconds_input.setMinimumWidth(100)
        self.seconds_input.setStyleSheet(input_style)

        playtime_layout.addWidget(self.minutes_input)
        playtime_layout.addWidget(self.seconds_input)
        playtime_layout.addStretch()

        group_layout.addRow(playtime_label, playtime_widget)

        # Replay Directory
        replay_label = QLabel("Replay Directory:")
        replay_label.setStyleSheet(label_style)

        replay_widget = QWidget()
        replay_layout = QHBoxLayout(replay_widget)
        replay_layout.setContentsMargins(0, 0, 0, 0)
        replay_layout.setSpacing(10)

        self.replay_dir_input = QLineEdit()
        self.replay_dir_input.setPlaceholderText("리플레이 디렉토리 경로")
        self.replay_dir_input.setReadOnly(True)
        self.replay_dir_input.setStyleSheet(input_style)

        browse_btn = QPushButton("찾아보기...")
        browse_btn.setStyleSheet("""
            QPushButton {
                font-size: 14px;
                padding: 8px 16px;
                background: #ecf0f1;
                color: #2c3e50;
                border: 1px solid #bdc3c7;
                border-radius: 4px;
            }
            QPushButton:hover {
                background: #d5dbdb;
            }
            QPushButton:pressed {
                background: #bdc3c7;
            }
        """)
        browse_btn.clicked.connect(self._on_browse_clicked)

        replay_layout.addWidget(self.replay_dir_input, 1)
        replay_layout.addWidget(browse_btn)

        group_layout.addRow(replay_label, replay_widget)

        # Time Zone
        time_zone_label = QLabel("Time Zone:")
        time_zone_label.setStyleSheet(label_style)

        time_zone_widget = QWidget()
        time_zone_layout = QHBoxLayout(time_zone_widget)
        time_zone_layout.setContentsMargins(0, 0, 0, 0)
        time_zone_layout.setSpacing(10)

        self.time_zone_input = QComboBox()
        self.time_zone_input.addItems([tz.value for tz in TypeTimeZone])
        self.time_zone_input.setCurrentText(self.config.time_zone.value)
        self.time_zone_input.setStyleSheet(input_style)
        time_zone_layout.addWidget(self.time_zone_input)
        group_layout.addRow(time_zone_label, time_zone_widget)

        layout.addWidget(group)

        # Buttons
        button_widget = QWidget()
        button_layout = QHBoxLayout(button_widget)
        button_layout.setContentsMargins(0, 20, 0, 0)
        button_layout.addStretch()

        button_style_primary = """
            QPushButton {
                font-size: 14px;
                font-weight: bold;
                padding: 10px 30px;
                background: #3498db;
                color: white;
                border: none;
                border-radius: 4px;
                min-width: 100px;
            }
            QPushButton:hover {
                background: #2980b9;
            }
            QPushButton:pressed {
                background: #21618c;
            }
        """

        button_style_secondary = """
            QPushButton {
                font-size: 14px;
                padding: 10px 30px;
                background: #ecf0f1;
                color: #2c3e50;
                border: 1px solid #bdc3c7;
                border-radius: 4px;
                min-width: 100px;
            }
            QPushButton:hover {
                background: #d5dbdb;
            }
            QPushButton:pressed {
                background: #bdc3c7;
            }
        """

        reset_btn = QPushButton("초기화")
        reset_btn.setStyleSheet(button_style_secondary)
        reset_btn.clicked.connect(self._on_reset_clicked)

        save_btn = QPushButton("저장")
        save_btn.setStyleSheet(button_style_primary)
        save_btn.clicked.connect(self._on_save_clicked)

        button_layout.addWidget(reset_btn)
        button_layout.addWidget(save_btn)

        layout.addWidget(button_widget)
        layout.addStretch()

    def _load_values(self):
        """Load values from config."""
        self.player_id_input.setText(self.config.player_id)
        self.minutes_input.setValue(self.config.playtime_minutes)
        self.seconds_input.setValue(self.config.playtime_seconds)
        self.replay_dir_input.setText(self.config.replay_dir)

    def _on_browse_clicked(self):
        """Open directory picker dialog."""
        directory = QFileDialog.getExistingDirectory(
            self,
            "Replay 디렉토리 선택",
            self.replay_dir_input.text() or "",
            QFileDialog.Option.ShowDirsOnly
        )
        if directory:
            self.replay_dir_input.setText(directory)

    def _on_save_clicked(self):
        """Save settings to config.json."""
        # Validate
        if not self.player_id_input.text().strip():
            QMessageBox.warning(self, "경고", "Player ID를 입력해주세요.")
            self.player_id_input.setFocus()
            return

        replay_dir_str = self.replay_dir_input.text().strip()
        if not replay_dir_str:
            QMessageBox.warning(self, "경고", "리플레이 디렉토리를 선택해주세요.")
            self.replay_dir_input.setFocus()
            return
        replay_dir = Path(replay_dir_str)
        replay_file = replay_dir / "LastReplay.rep"
        if not replay_dir.exists() or not replay_file.exists():
            QMessageBox.warning(self, "경고", "리플레이 디렉토리 또는 리플레이 파일이 존재하지 않습니다.")
            self.replay_dir_input.setFocus()
            return

        # Update config
        self.config.player_id = self.player_id_input.text().strip()
        self.config.set_playtime(
            self.minutes_input.value(),
            self.seconds_input.value()
        )
        self.config.replay_dir = replay_dir_str
        self.config.time_zone = TypeTimeZone(self.time_zone_input.currentText())

        # Save
        self.config.save()

        QMessageBox.information(self, "저장 완료", "설정이 저장되었습니다.")
        self.settings_saved.emit()

    def _on_reset_clicked(self):
        """Reset to saved values."""
        self.config = AppConfig.get_instance()
        self._load_values()

    def get_config(self) -> AppConfig:
        """Get the current configuration."""
        return self.config
