"""
Global Event Bus for application-wide events.

Usage:
    # Subscribe to events
    EventBus.instance().replay_added.connect(self._on_replay_added)

    # Emit events
    EventBus.instance().replay_added.emit({"player_id": 1, "map_name": "Dust II"})
"""
from PySide6.QtCore import QObject, Signal

from dto.match_history import MatchHistoryDTO


class EventBus(QObject):
    """
    Singleton Event Bus for pub/sub pattern across the application.

    Similar to WebSocket events in web frontend.
    """

    _instance: "EventBus | None" = None

    # ==========================================================================
    # Event Definitions
    # ==========================================================================

    # Replay events
    replay_added = Signal(MatchHistoryDTO)          # New replay processed
    replay_processing_error = Signal(str)  # Error during replay processing

    # Player events
    player_updated = Signal(str)         # Player info updated (game_id)
    player_stats_changed = Signal(int)   # Player stats changed (player_id)

    # Data events
    data_refresh_requested = Signal()    # Request to refresh all data

    # ==========================================================================
    # Singleton Pattern
    # ==========================================================================

    def __init__(self, parent=None):
        super().__init__(parent)

    @classmethod
    def instance(cls) -> "EventBus":
        """Get the singleton instance of EventBus."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        """Reset the singleton instance (for testing)."""
        cls._instance = None
