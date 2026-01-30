"""
Tests for UIState singleton class.
"""
import pytest

from common.const import TypeOrderColumn, TypeOrderDirection
from common.ui_state import UIState, AllStatsState


class TestUIState:
    """Tests for UIState singleton."""

    def setup_method(self):
        """Reset UIState before each test."""
        UIState.reset()

    def teardown_method(self):
        """Reset UIState after each test."""
        UIState.reset()

    def test_singleton_returns_same_instance(self):
        """UIState.get_instance() should return the same instance."""
        instance1 = UIState.get_instance()
        instance2 = UIState.get_instance()

        assert instance1 is instance2

    def test_reset_creates_new_instance(self):
        """UIState.reset() should create a new instance on next get_instance()."""
        instance1 = UIState.get_instance()
        instance1.all_stats.search_game_id = "test"

        UIState.reset()
        instance2 = UIState.get_instance()

        assert instance1 is not instance2
        assert instance2.all_stats.search_game_id == ""

    def test_default_all_stats_state(self):
        """AllStatsState should have correct default values."""
        state = UIState.get_instance()

        assert state.all_stats.search_game_id == ""
        assert state.all_stats.order_column == TypeOrderColumn.LAST_PLAYED_AT
        assert state.all_stats.order_direction == TypeOrderDirection.DESC

    def test_all_stats_state_persistence(self):
        """AllStatsState changes should persist across get_instance() calls."""
        state = UIState.get_instance()

        # Modify state
        state.all_stats.search_game_id = "TestPlayer"
        state.all_stats.order_column = TypeOrderColumn.GAME_ID
        state.all_stats.order_direction = TypeOrderDirection.ASC

        # Get instance again
        state2 = UIState.get_instance()

        assert state2.all_stats.search_game_id == "TestPlayer"
        assert state2.all_stats.order_column == TypeOrderColumn.GAME_ID
        assert state2.all_stats.order_direction == TypeOrderDirection.ASC


class TestAllStatsState:
    """Tests for AllStatsState dataclass."""

    def test_default_values(self):
        """AllStatsState should have correct default values."""
        state = AllStatsState()

        assert state.search_game_id == ""
        assert state.order_column == TypeOrderColumn.LAST_PLAYED_AT
        assert state.order_direction == TypeOrderDirection.DESC

    def test_custom_values(self):
        """AllStatsState should accept custom values."""
        state = AllStatsState(
            search_game_id="Player123",
            order_column=TypeOrderColumn.TOTAL_WINS,
            order_direction=TypeOrderDirection.ASC
        )

        assert state.search_game_id == "Player123"
        assert state.order_column == TypeOrderColumn.TOTAL_WINS
        assert state.order_direction == TypeOrderDirection.ASC

    def test_mutable_fields(self):
        """AllStatsState fields should be mutable."""
        state = AllStatsState()

        state.search_game_id = "UpdatedPlayer"
        state.order_column = TypeOrderColumn.TOTAL_GAMES
        state.order_direction = TypeOrderDirection.ASC

        assert state.search_game_id == "UpdatedPlayer"
        assert state.order_column == TypeOrderColumn.TOTAL_GAMES
        assert state.order_direction == TypeOrderDirection.ASC
