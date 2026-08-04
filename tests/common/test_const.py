"""
Tests for enums in common.const.
"""
import pytest

from common.const import TypeLeaveReason


class TestTypeLeaveReason:
    """Tests for TypeLeaveReason."""

    @pytest.mark.parametrize("name", ["Quit", "Defeat", "Dropped"])
    def test_lose_reasons(self, name):
        """Quit / Defeat / Dropped 로 나간 플레이어는 패배자다."""
        assert TypeLeaveReason(name).is_lose() is True

    @pytest.mark.parametrize("name", ["Victory", "Finished", "Draw", "Unknown"])
    def test_non_lose_reasons(self, name):
        """나머지 사유는 패배 판정에 쓰지 않는다."""
        assert TypeLeaveReason(name).is_lose() is False

    @pytest.mark.parametrize("value", ["Unknown 0x07", "", None])
    def test_unknown_value_is_absorbed(self, value):
        """screp 이 모르는 사유를 내려줘도 예외 없이 UNKNOWN 으로 흡수한다."""
        assert TypeLeaveReason(value) is TypeLeaveReason.UNKNOWN
