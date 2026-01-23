"""
Backup service - Handles periodic database backup to disk.
"""
from PySide6.QtCore import QObject, QTimer, Signal
from datetime import datetime
from typing import Optional

from database.connection import DatabaseManager
from database.backup import backup_database, get_backup_info


class BackupService(QObject):
    """
    Service for managing periodic database backups.

    Uses QTimer to schedule automatic backups at specified intervals.
    Emits signals to notify about backup status.
    """

    # Signals
    backup_started = Signal()
    backup_completed = Signal(bool, str)  # success, message
    backup_error = Signal(str)  # error message

    def __init__(
        self,
        backup_path: str,
        interval_ms: int = 60_000,
        keep_versions: int = 5,
        parent: Optional[QObject] = None
    ):
        """
        Initialize the backup service.

        Args:
            backup_path: Path to save the backup file
            interval_ms: Backup interval in milliseconds (default: 1 minute)
            keep_versions: Number of backup versions to keep
            parent: Parent QObject
        """
        super().__init__(parent)

        self.backup_path = backup_path
        self.keep_versions = keep_versions
        self.db = DatabaseManager.get_instance()

        self._last_backup_time: Optional[datetime] = None
        self._backup_count = 0

        # Setup timer
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._do_backup)
        self._timer.setInterval(interval_ms)

    def start(self) -> None:
        """Start the automatic backup timer."""
        if not self._timer.isActive():
            self._timer.start()

    def stop(self) -> None:
        """Stop the automatic backup timer."""
        if self._timer.isActive():
            self._timer.stop()

    def set_interval(self, interval_ms: int) -> None:
        """Change the backup interval."""
        was_active = self._timer.isActive()
        self._timer.stop()
        self._timer.setInterval(interval_ms)
        if was_active:
            self._timer.start()

    def backup_now(self) -> bool:
        """
        Perform an immediate backup.

        Returns:
            True if backup was successful
        """
        return self._do_backup()

    def _do_backup(self) -> bool:
        """
        Internal method to perform the backup.

        Returns:
            True if backup was successful
        """
        self.backup_started.emit()

        try:
            # Get raw SQLite connection from SQLAlchemy engine
            raw_conn = self.db.get_raw_connection()

            success = backup_database(
                source_conn=raw_conn,
                backup_path=self.backup_path,
                keep_versions=self.keep_versions
            )

            if success:
                self._last_backup_time = datetime.now()
                self._backup_count += 1
                time_str = self._last_backup_time.strftime('%H:%M:%S')
                self.backup_completed.emit(True, f"백업 완료: {time_str}")
            else:
                self.backup_completed.emit(False, "백업 실패")

            return success

        except Exception as e:
            error_msg = f"백업 오류: {str(e)}"
            self.backup_error.emit(error_msg)
            return False

    @property
    def last_backup_time(self) -> Optional[datetime]:
        """Get the time of the last successful backup."""
        return self._last_backup_time

    @property
    def backup_count(self) -> int:
        """Get the total number of backups performed in this session."""
        return self._backup_count

    @property
    def is_running(self) -> bool:
        """Check if automatic backups are running."""
        return self._timer.isActive()

    def get_backup_info(self) -> Optional[dict]:
        """Get information about the current backup file."""
        return get_backup_info(self.backup_path)
