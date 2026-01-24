from enum import Enum
from typing import TYPE_CHECKING
from zoneinfo import ZoneInfo

if TYPE_CHECKING:
    from sqlalchemy.orm import InstrumentedAttribute


class TypeOrderColumn(Enum):
    """정렬 가능한 컬럼 목록.

    value는 모델의 실제 속성명과 일치해야 합니다.
    """
    # Player
    GAME_ID = "game_id"
    TOTAL_GAMES = "total_games"
    TOTAL_WINS = "total_wins"
    TOTAL_LOSSES = "total_losses"
    TOTAL_WIN_RATE = "total_win_rate"
    LAST_PLAYED_AT = "last_played_at"

    # MatchHistory
    OPPONENT_ID = "opponent_id"
    RACE = "race"
    MAP_NAME = "map_name"
    IS_WIN = "is_win"
    PLAYTIME = "playtime"
    PLAYED_AT = "played_at"

    def get_column(self, model) -> "InstrumentedAttribute":
        """모델에서 해당 컬럼을 안전하게 반환.

        Args:
            model: SQLAlchemy 모델 클래스

        Returns:
            해당 컬럼의 InstrumentedAttribute

        Raises:
            ValueError: 컬럼이 모델에 존재하지 않을 경우
        """
        column = getattr(model, self.value, None)
        if column is None:
            raise ValueError(
                f"Column '{self.value}' not found in {model.__name__}. "
                f"Available columns: {[c.key for c in model.__table__.columns]}"
            )
        return column


class TypeOrderDirection(Enum):
    ASC = "asc"
    DESC = "desc"


class TypeTimeZone(Enum):
    KOREA = "Asia/Seoul"
    CHINA = "Asia/Shanghai"
    JAPAN = "Asia/Tokyo"
    TAIWAN = "Asia/Taipei"
    USA = "America/New_York"

    def get_timezone(self) -> ZoneInfo:
        return ZoneInfo(self.value)


class TypeErrorCode(Enum):
    """리플레이 분석 에러 코드."""

    # 정상 스킵 (사용자에게 간략히 표시하거나 표시 안 함)
    DUPLICATE = "duplicate"
    PLAYTIME_TOO_SHORT = "playtime_too_short"
    NOT_1VS1 = "not_1vs1"
    NOT_MY_REPLAY = "not_my_replay"

    # 실제 에러
    PLAYER_UPSERT_FAILED = "player_upsert_failed"
    PLAYER_UPDATE_FAILED = "player_update_failed"
    MAP_UPSERT_FAILED = "map_upsert_failed"
    STAT_UPSERT_FAILED = "stat_upsert_failed"
    ANALYSIS_FAILED = "analysis_failed"

    def is_skip(self) -> bool:
        """정상 스킵인지 확인."""
        return self in (
            TypeErrorCode.DUPLICATE,
            TypeErrorCode.PLAYTIME_TOO_SHORT,
            TypeErrorCode.NOT_1VS1,
            TypeErrorCode.NOT_MY_REPLAY,
        )

    def get_user_message(self) -> str:
        """사용자 친화적 메시지 반환."""
        messages = {
            TypeErrorCode.DUPLICATE: "이미 불러온 리플레이",
            TypeErrorCode.PLAYTIME_TOO_SHORT: "게임 시간 부족",
            TypeErrorCode.NOT_1VS1: "1vs1 게임 아님",
            TypeErrorCode.NOT_MY_REPLAY: "내 리플레이 아님",
            TypeErrorCode.PLAYER_UPSERT_FAILED: "플레이어 저장 실패",
            TypeErrorCode.PLAYER_UPDATE_FAILED: "플레이어 업데이트 실패",
            TypeErrorCode.MAP_UPSERT_FAILED: "맵 저장 실패",
            TypeErrorCode.STAT_UPSERT_FAILED: "통계 저장 실패",
            TypeErrorCode.ANALYSIS_FAILED: "분석 실패",
        }
        return messages.get(self, "알 수 없는 오류")
