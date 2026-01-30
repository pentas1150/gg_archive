"""
UI state management for global state persistence across views.

This module provides a singleton class to manage UI state that should
persist when navigating between different views/screens.
"""
from dataclasses import dataclass, field
from typing import Optional

from common.const import TypeOrderColumn, TypeOrderDirection


@dataclass
class AllStatsState:
    """State for AllStatsWidget."""
    search_game_id: str = ""
    order_column: TypeOrderColumn = TypeOrderColumn.LAST_PLAYED_AT
    order_direction: TypeOrderDirection = TypeOrderDirection.DESC


@dataclass
class UIState:
    """
    Global UI state manager (singleton).

    Stores UI state that should persist across view navigation,
    such as search filters, sort settings, etc.
    """

    _instance: Optional["UIState"] = field(default=None, repr=False)

    # AllStatsWidget state
    all_stats: AllStatsState = field(default_factory=AllStatsState)

    @classmethod
    def get_instance(cls) -> "UIState":
        """Get the singleton instance of UIState."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        """Reset the singleton instance (useful for testing)."""
        cls._instance = None
