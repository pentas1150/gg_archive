"""
Application configuration from config.json.
"""
import sys
import json
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional

from common.const import TypeTimeZone


def _get_app_dir() -> Path:
    """Get the application directory, handling PyInstaller packaging."""
    if getattr(sys, 'frozen', False):
        # PyInstaller로 패키징된 경우 - 실행 파일이 있는 디렉토리
        return Path(sys.executable).parent
    else:
        # 개발 환경
        return Path(__file__).parent.parent


def _get_screp_path() -> str:
    """Get the screp executable path."""
    if getattr(sys, 'frozen', False):
        # PyInstaller로 패키징된 경우 - 실행 파일 옆
        return str(Path(sys.executable).parent / "screp")
    else:
        # 개발 환경
        return str(Path(__file__).parent.parent / "screp")


CONFIG_FILE = _get_app_dir() / "config.json"


@dataclass
class AppConfig:
    """Application configuration loaded from config.json."""

    _instance: Optional["AppConfig"] = None

    player_id: str = ""
    playtime_threshold: int = 180  # seconds
    replay_dir: str = ""
    time_zone: TypeTimeZone = TypeTimeZone.KOREA

    screp_path: str = field(default_factory=_get_screp_path)

    @classmethod
    def get_instance(cls) -> "AppConfig":
        """Get the singleton instance of AppConfig."""
        if cls._instance is None:
            cls._instance = cls._load_from_file()
        return cls._instance

    @classmethod
    def reload(cls) -> "AppConfig":
        """Reload configuration from file."""
        cls._instance = cls._load_from_file()
        return cls._instance

    @classmethod
    def _load_from_file(cls) -> "AppConfig":
        """Load configuration from config.json."""
        if CONFIG_FILE.exists():
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return cls(
                    player_id=data.get("player_id", ""),
                    playtime_threshold=data.get("playtime_threshold", 180),
                    replay_dir=data.get("replay_dir", ""),
                    time_zone=TypeTimeZone(data.get("time_zone", TypeTimeZone.KOREA.value)),
                )
        return cls()

    def save(self) -> None:
        """Save configuration to config.json."""
        data = {
            "player_id": self.player_id,
            "playtime_threshold": self.playtime_threshold,
            "replay_dir": self.replay_dir,
            "time_zone": self.time_zone.value,
        }
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)

    @property
    def playtime_minutes(self) -> int:
        """Get playtime threshold in minutes."""
        return self.playtime_threshold // 60

    @property
    def playtime_seconds(self) -> int:
        """Get remaining seconds of playtime threshold."""
        return self.playtime_threshold % 60

    def set_playtime(self, minutes: int, seconds: int) -> None:
        """Set playtime threshold from minutes and seconds."""
        self.playtime_threshold = minutes * 60 + seconds

    @property
    def replay_file(self) -> Path:
        return Path(self.replay_dir) / "LastReplay.rep"

    def is_valid(self) -> bool:
        """Check if configuration has all required valid values."""
        # player_id가 비어있으면 무효
        if not self.player_id or not self.player_id.strip():
            return False

        # replay_dir이 비어있거나 존재하지 않으면 무효
        if not self.replay_dir:
            return False

        replay_path = Path(self.replay_dir)
        if not replay_path.exists():
            return False

        if self.time_zone not in TypeTimeZone:
            return False

        return True
