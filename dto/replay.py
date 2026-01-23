from datetime import datetime
from pydantic import BaseModel, Field


class ReplayAnalysisDTO(BaseModel):
    opponent_id: str = Field(description="상대방 아이디")
    race: str = Field(description="상대방 종족")
    map_name: str = Field(description="맵 이름")
    is_win: bool = Field(description="승리 여부")
    playtime: int = Field(description="총 게임 시간(단위: sec)")
    played_at: datetime = Field(description="게임 시작 시간")
