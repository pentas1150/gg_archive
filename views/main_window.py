"""
Main application window.
"""
from PySide6.QtWidgets import (
    QMainWindow,
    QLabel,
    QStatusBar,
    QStackedWidget,
    QMessageBox,
    QSystemTrayIcon,
    QMenu,
    QApplication,
)
from PySide6.QtCore import Slot
from PySide6.QtGui import QAction, QIcon

from resources import get_icon_path
from services.player_service import PlayerService
from services.match_history_service import MatchHistoryService
from services.background.replay_watch_service import ReplayWatchService
from .settings_widget import SettingsWidget
from .all_stats_widget import AllStatsWidget
from .player_detail_widget import PlayerDetailWidget
from .autosave_replay_dialog import AutoSaveReplayDialog
from config.settings import Settings
from config.app_config import AppConfig
from config.version_config import VersionConfig


class MainWindow(QMainWindow):
    """
    Main application window.

    Contains the primary UI layout and menu bar.
    """

    def __init__(
        self,
        player_service: PlayerService | None = None,
        match_history_service: MatchHistoryService | None = None,
        replay_watch_service: ReplayWatchService | None = None,
        parent=None
    ):
        super().__init__(parent)

        self.settings = Settings()
        self.player_service = player_service
        self.match_history_service = match_history_service
        self.replay_watch_service = replay_watch_service

        self._setup_ui()
        self._setup_menu_bar()
        self._setup_status_bar()
        self._setup_system_tray()
        self._determine_initial_view()

    def _setup_ui(self):
        """Initialize the main UI layout."""
        self.setWindowTitle("GG Archive")
        self.setWindowIcon(self._get_app_icon())
        self.resize(self.settings.window_width, self.settings.window_height)

        # Set window style
        self.setStyleSheet("""
            QMainWindow {
                background: #f5f6fa;
            }
        """)

        # Stacked widget for switching between views
        self.stacked_widget = QStackedWidget()
        self.setCentralWidget(self.stacked_widget)

        # Settings widget (index 0)
        self.settings_widget = SettingsWidget()
        self.settings_widget.settings_saved.connect(self._on_settings_saved)
        self.stacked_widget.addWidget(self.settings_widget)

        # All Stats widget (index 1)
        self.all_stats_widget = AllStatsWidget(self.player_service)
        self.all_stats_widget.player_selected.connect(self._on_player_selected)
        self.stacked_widget.addWidget(self.all_stats_widget)

        # Player Detail widget (index 2)
        self.player_detail_widget = PlayerDetailWidget(self.match_history_service)
        self.player_detail_widget.back_clicked.connect(self._on_back_to_stats)
        self.player_detail_widget.description_updated.connect(self._on_description_updated)
        self.stacked_widget.addWidget(self.player_detail_widget)

    def _determine_initial_view(self):
        """Determine initial view based on config validity."""
        config = AppConfig.get_instance()
        if config.is_valid():
            # 정상 → All Stats 화면 (index 1)
            self._load_and_show_stats()
        else:
            # 비정상 → Settings 화면 (index 0)
            self.stacked_widget.setCurrentIndex(0)

    def _setup_menu_bar(self):
        """Setup the application menu bar."""
        menu_bar = self.menuBar()

        # File menu
        file_menu = menu_bar.addMenu("파일(&F)")

        backup_action = QAction("지금 백업(&B)", self)
        backup_action.setShortcut("Ctrl+S")
        backup_action.triggered.connect(self._on_backup_now)
        file_menu.addAction(backup_action)

        autosave_import_action = QAction("AutoSave 리플레이 불러오기(&A)", self)
        autosave_import_action.triggered.connect(self._on_autosave_import)
        file_menu.addAction(autosave_import_action)

        file_menu.addSeparator()

        exit_action = QAction("종료(&X)", self)
        exit_action.setShortcut("Alt+F4")
        exit_action.triggered.connect(self._quit_app)
        file_menu.addAction(exit_action)

        # Help menu
        help_menu = menu_bar.addMenu("도움말(&H)")

        about_action = QAction("GG Archive 정보(&A)", self)
        about_action.triggered.connect(self._on_about)
        help_menu.addAction(about_action)

    def _setup_status_bar(self):
        """Setup the status bar."""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

        # Backup status label
        self.backup_status_label = QLabel("백업 대기 중")
        self.status_bar.addPermanentWidget(self.backup_status_label)

        self.status_bar.showMessage("준비됨")

    def _get_app_icon(self) -> QIcon:
        """Get the application icon from resources."""
        icon_path = get_icon_path("gg_icon.png")
        if icon_path.exists():
            return QIcon(str(icon_path))
        # 아이콘 파일이 없을 경우 빈 아이콘 반환
        return QIcon()

    def _setup_system_tray(self):
        """Setup system tray icon and menu."""
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(self._get_app_icon())
        self.tray_icon.setToolTip("GG Archive - 리플레이 감시 중")

        # Tray context menu
        tray_menu = QMenu()

        show_action = QAction("열기", self)
        show_action.triggered.connect(self._show_window)
        tray_menu.addAction(show_action)

        tray_menu.addSeparator()

        quit_action = QAction("종료", self)
        quit_action.triggered.connect(self._quit_app)
        tray_menu.addAction(quit_action)

        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self._on_tray_activated)
        self.tray_icon.show()

    def _show_window(self):
        """Show and activate the main window."""
        self.show()
        self.raise_()
        self.activateWindow()

    def _on_tray_activated(self, reason):
        """Handle tray icon activation."""
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self._show_window()

    def _quit_app(self):
        """Quit the application completely."""
        self.tray_icon.hide()
        QApplication.quit()

    def closeEvent(self, event):
        """Override close event to minimize to tray instead of quitting."""
        if self.tray_icon.isVisible():
            self.hide()
            event.ignore()
            self.tray_icon.showMessage(
                "GG Archive",
                "백그라운드에서 리플레이를 감시하고 있습니다.",
                QSystemTrayIcon.MessageIcon.Information,
                2000
            )
        else:
            event.accept()

    @Slot()
    def _on_backup_now(self):
        """Handle manual backup request."""
        self.status_bar.showMessage("백업 중...")

    @Slot()
    def _on_autosave_import(self):
        """Handle AutoSave replay import request."""
        if not self.replay_watch_service:
            # Create a temporary replay watch service if not provided
            self.replay_watch_service = ReplayWatchService()

        dialog = AutoSaveReplayDialog(self.replay_watch_service, self)
        dialog.import_completed.connect(self._on_autosave_import_completed)
        dialog.exec()

    @Slot()
    def _on_autosave_import_completed(self):
        """Handle AutoSave replay import completion."""
        self._load_and_show_stats()
        self.status_bar.showMessage("AutoSave 리플레이 불러오기 완료", 3000)

    @Slot()
    def _on_about(self):
        """Show about dialog."""
        QMessageBox.about(
            self,
            "GG Archive 정보",
            f"GG Archive v{VersionConfig.version}\n\n"
            "SQLite in-memory 데이터베이스를 사용하는\n"
            "데스크톱 애플리케이션입니다.\n\n"
            f"© 2026 GG Archive v{VersionConfig.version}"
            "Developed by pentas1150"
        )

    @Slot()
    def _on_settings_saved(self):
        """Handle settings saved - switch to All Stats view."""
        self._load_and_show_stats()

    def _load_and_show_stats(self):
        """Load player data and show the All Stats view."""
        if self.player_service:
            players = self.player_service.get_all_players()
            self.all_stats_widget.set_players(players)
        self.stacked_widget.setCurrentIndex(1)
        self.status_bar.showMessage("플레이어 통계를 불러왔습니다", 3000)

    @Slot()
    def _on_player_selected(self, player):
        """Handle player selection - show player detail view."""
        # set_player now handles loading match histories with current sort settings
        self.player_detail_widget.set_player(player)
        self.stacked_widget.setCurrentIndex(2)

    @Slot()
    def _on_back_to_stats(self):
        """Handle back button - return to All Stats view."""
        # Refresh stats in case description was updated
        self._load_and_show_stats()

    @Slot(str, str)
    def _on_description_updated(self, game_id: str, description: str):
        """Handle description update."""
        if self.player_service:
            try:
                self.player_service.update_description(game_id, description)
                self.status_bar.showMessage("설명이 저장되었습니다", 3000)
            except Exception as e:
                QMessageBox.warning(self, "오류", f"설명 저장 중 오류가 발생했습니다: {e}")

    def update_backup_status(self, success: bool, message: str):
        """Update the backup status in the status bar."""
        self.backup_status_label.setText(message)
        if success:
            self.status_bar.showMessage("백업 완료", 3000)
        else:
            self.status_bar.showMessage("백업 실패", 3000)
