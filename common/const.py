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


class TypeLeaveReason(Enum):
    """screp LeaveGameCmd 의 Reason.Name 값.

    screp `rep/repcmd/leavereasons.go` 의 LeaveReasons 와 1:1 대응.
    screp 은 미지의 ID 에 "Unknown 0x07" 같은 이름을 동적으로 만들어 내려주므로
    등록되지 않은 값은 모두 UNKNOWN 으로 흡수한다.
    """

    QUIT = "Quit"
    DEFEAT = "Defeat"
    VICTORY = "Victory"
    FINISHED = "Finished"
    DRAW = "Draw"
    DROPPED = "Dropped"
    UNKNOWN = "Unknown"

    @classmethod
    def _missing_(cls, value) -> "TypeLeaveReason":
        """screp 이 새 사유를 내려줘도 예외 대신 UNKNOWN 으로 처리."""
        return cls.UNKNOWN

    def is_lose(self) -> bool:
        """이 사유로 게임을 떠난 플레이어가 패배자인지."""
        return self in (
            TypeLeaveReason.QUIT,
            TypeLeaveReason.DEFEAT,
            TypeLeaveReason.DROPPED,
        )


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
