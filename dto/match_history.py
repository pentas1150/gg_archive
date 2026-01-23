from datetime import datetime
from pydantic import BaseModel, Field


class MatchHistoryDTO(BaseModel):
    opponent_id: str = Field(description="Opponent ID")
    race: str = Field(description="Race")
    map_name: str = Field(description="Map Name")
    is_win: bool = Field(description="Is Win")
    playtime: int = Field(description="Playtime")
    played_at: datetime = Field(description="Played At")
