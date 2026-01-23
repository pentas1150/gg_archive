"""
Application class - QApplication setup and lifecycle management.
"""
from PySide6.QtWidgets import QApplication

from config.settings import Settings
from database.connection import DatabaseManager
from database.migrations import init_database, seed_test_data
from services.background.backup_service import BackupService
from services.background.replay_watch_service import ReplayWatchService
from services.player_service import PlayerService
from services.match_history_service import MatchHistoryService
from views.main_window import MainWindow


class Application:
    """Main application class managing app lifecycle."""

    def __init__(self, argv: list, dev_mode: bool = False):
        self.dev_mode = dev_mode
        self.settings = Settings()
        self.qapp = QApplication(argv)
        self.qapp.setApplicationName("GG Archive")
        self.qapp.setApplicationVersion("1.0.0")

        # Initialize database manager
        self.db_manager = DatabaseManager.get_instance()

        # Dev mode: skip backup restore, use test data instead
        if self.dev_mode:
            print("[DEV] Running in development mode")
            print("[DEV] Skipping backup restore, using test data instead")
            init_database()
            seed_test_data()
        else:
            # Production: restore from disk backup if exists
            if self.settings.backup_path.exists():
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
            match_history_service=self.match_history_service
        )

        # Connect backup signals to UI
        self.backup_service.backup_completed.connect(
            self.main_window.update_backup_status
        )

        # Start automatic backups (skip in dev mode)
        if not self.dev_mode:
            self.backup_service.start()
        else:
            print("[DEV] Automatic backups disabled in development mode")

        # Start replay file watching
        self.replay_watch_service.start()

    def run(self) -> int:
        """Run the application event loop."""
        self.main_window.show()

        # Perform final backup on exit
        result = self.qapp.exec()
        self._on_exit()
        return result

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
