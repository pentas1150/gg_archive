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
