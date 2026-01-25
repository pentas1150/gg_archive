"""
Application class - QApplication setup and lifecycle management.
"""
import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication, QStyleFactory
from PySide6.QtGui import QPalette, QColor

from config.settings import Settings
from common.logger import setup_logger, get_logger
from database.connection import DatabaseManager
from database.migrations import init_database, seed_test_data, run_migrations
from services.background.backup_service import BackupService
from services.background.replay_watch_service import ReplayWatchService
from services.player_service import PlayerService
from services.match_history_service import MatchHistoryService
from views.main_window import MainWindow
from views.screp_download_dialog import ScrepDownloadDialog


class Application:
    """Main application class managing app lifecycle."""

    def __init__(self, argv: list, dev_mode: bool = False):
        self.dev_mode = dev_mode
        self.settings = Settings()

        # Initialize logger with settings
        setup_logger(self.settings.log_file_path)
        self.logger = get_logger("app")

        self.qapp = QApplication(argv)
        self.qapp.setApplicationName("GG Archive")
        self.qapp.setApplicationVersion("1.0.0")

        # Use Fusion style for consistent cross-platform appearance
        # This ensures CSS styling works properly on macOS
        self.qapp.setStyle(QStyleFactory.create("Fusion"))

        # Set palette for Fusion style to ensure proper colors
        palette = QPalette()
        palette.setColor(QPalette.ColorRole.Window, QColor("#f5f6fa"))
        palette.setColor(QPalette.ColorRole.WindowText, QColor("#2c3e50"))
        palette.setColor(QPalette.ColorRole.Base, QColor("#ffffff"))
        palette.setColor(QPalette.ColorRole.AlternateBase, QColor("#f5f6fa"))
        palette.setColor(QPalette.ColorRole.Text, QColor("#2c3e50"))
        palette.setColor(QPalette.ColorRole.Button, QColor("#ecf0f1"))
        palette.setColor(QPalette.ColorRole.ButtonText, QColor("#2c3e50"))
        palette.setColor(QPalette.ColorRole.Highlight, QColor("#3498db"))
        palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#ffffff"))
        # Dark/Mid colors for spinbox/combobox arrows
        palette.setColor(QPalette.ColorRole.Dark, QColor("#2c3e50"))
        palette.setColor(QPalette.ColorRole.Mid, QColor("#7f8c8d"))
        palette.setColor(QPalette.ColorRole.Light, QColor("#ecf0f1"))
        palette.setColor(QPalette.ColorRole.Midlight, QColor("#d5dbdb"))
        self.qapp.setPalette(palette)

        # Initialize database manager
        self.db_manager = DatabaseManager.get_instance()

        # Dev mode: skip backup restore, use test data instead
        if self.dev_mode:
            self.logger.info("Running in development mode")
            self.logger.info("Skipping backup restore, using test data instead")
            init_database()
            seed_test_data()
        else:
            # Production: restore from disk backup if exists
            if self.settings.backup_path.exists():
                # Run Alembic migrations on backup file before restoring
                self._migrate_backup_database()
                self.db_manager.restore_from_disk(str(self.settings.backup_path))
            init_database()

        # Initialize services (using Unit of Work internally)
        self.player_service = PlayerService()
        self.match_history_service = MatchHistoryService()

        # Initialize backup service
        self.backup_service = BackupService(
            backup_path=str(self.settings.backup_path),
            interval_ms=self.settings.backup_interval_ms
        )

        # Initialize replay watch service
        self.replay_watch_service = ReplayWatchService()

        # Create main window with services
        self.main_window = MainWindow(
            player_service=self.player_service,
            match_history_service=self.match_history_service,
            replay_watch_service=self.replay_watch_service
        )

        # Connect backup signals to UI
        self.backup_service.backup_completed.connect(
            self.main_window.update_backup_status
        )

        # Start automatic backups (skip in dev mode)
        if not self.dev_mode:
            self.backup_service.start()
        else:
            self.logger.info("Automatic backups disabled in development mode")

        # Start replay file watching
        self.replay_watch_service.start()

    def run(self) -> int:
        """Run the application event loop."""
        # Check for screp executable before showing main window
        self._check_screp_executable()

        self.main_window.show()

        # Perform final backup on exit
        result = self.qapp.exec()
        self._on_exit()
        return result

    def _get_app_directory(self) -> Path:
        """Get the application's root directory."""
        # When running as frozen executable (PyInstaller)
        if getattr(sys, 'frozen', False):
            return Path(sys.executable).parent
        # When running as script
        return Path(__file__).parent

    def _check_screp_executable(self) -> bool:
        """
        Check if screp executable exists in the application directory.
        Shows download dialog if not found.

        Returns:
            True if screp is found, False otherwise.
        """
        app_dir = self._get_app_directory()
        screp_path = app_dir / "screp"
        screp_exe_path = app_dir / "screp.exe"

        if screp_path.exists() or screp_exe_path.exists():
            return True

        # Show download dialog
        dialog = ScrepDownloadDialog()
        dialog.exec()
        return False

    def _migrate_backup_database(self) -> None:
        """
        Run Alembic migrations on the backup database file.

        This ensures the backup file schema is up-to-date before
        restoring it to the in-memory database.
        """
        backup_path = self.settings.backup_path

        if not backup_path.exists():
            return

        try:
            success = run_migrations(backup_path)
            if success:
                self.logger.info(f"Database migrations applied to {backup_path}")
            else:
                self.logger.warning("No migrations needed or migration check failed")
        except Exception as e:
            self.logger.error(f"Migration failed: {e}")
            # Continue anyway - the backup will be restored as-is
            # init_database() will create any missing tables

    def _on_exit(self):
        """Cleanup on application exit."""
        # Stop replay watch service
        self.replay_watch_service.stop()

        # Stop backup timer
        self.backup_service.stop()

        # Final backup before exit (skip in dev mode)
        if not self.dev_mode:
            self.backup_service.backup_now()

        # Close database
        self.db_manager.close()
