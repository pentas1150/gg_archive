"""
Application settings and configuration.
"""
from pathlib import Path
from dataclasses import dataclass, field


def get_default_data_dir() -> Path:
    """Get the default data directory for the application."""
    # Use user's home directory for data storage
    data_dir = Path.home() / ".gg_archive"
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


@dataclass
class Settings:
    """Application settings container."""

    # Database settings
    data_dir: Path = field(default_factory=get_default_data_dir)
    db_filename: str = "gg_archive.db"

    # Backup settings
    backup_interval_ms: int = 60_000  # 1 minute default
    backup_on_exit: bool = True

    # UI settings
    window_width: int = 750
    window_height: int = 800

    @property
    def backup_path(self) -> Path:
        """Full path to the backup database file."""
        return self.data_dir / self.db_filename

    def update(self, **kwargs):
        """Update settings with provided values."""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
