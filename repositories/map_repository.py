from typing import Type, Optional

from sqlalchemy import func
from sqlalchemy.dialects.sqlite import insert

from .base_repository import BaseRepository
from models.map import Map


class MapRepository(BaseRepository[Map]):
    @property
    def model_class(self) -> Type[Map]:
        return Map

    def find_by_name(self, name: str) -> Optional[Map]:
        res = self.find_by(name=name)
        return res[0] if res else None

    def upsert(self, name: str) -> Optional[Map]:
        with self._get_session() as session:
            stmt = (
                insert(Map)
                .values(name=name)
                .on_conflict_do_update(
                    index_elements=[Map.name],
                    set_={Map.updated_at: func.now()}
                )
                .returning(Map)
                .prefix_with("/* MapRepository.upsert */")
            )

            res = session.scalar(stmt)
            if self._should_expunge():
                session.expunge(res)
            return res
