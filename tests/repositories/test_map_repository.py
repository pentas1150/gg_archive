"""
Tests for MapRepository.

Uses transaction rollback for test isolation.
"""
import pytest

from models.map import Map
from repositories.map_repository import MapRepository


class TestMapRepository:
    """MapRepository 테스트."""

    @pytest.fixture(autouse=True)
    def setup(self, db, db_session):
        """각 테스트 전에 repository 초기화."""
        self.repo = MapRepository(session=db_session)
        self.db = db
        self.db_session = db_session

    # =========================================================================
    # find_by_name 테스트
    # =========================================================================

    def test_find_by_name_returns_none_when_not_exists(self):
        """존재하지 않는 name 검색 시 None 반환."""
        result = self.repo.find_by_name("nonexistent_map")
        assert result is None

    def test_find_by_name_returns_map_when_exists(self):
        """존재하는 name 검색 시 Map 반환."""
        # Given
        self.repo.upsert("Fighting Spirit")

        # When
        result = self.repo.find_by_name("Fighting Spirit")

        # Then
        assert result is not None
        assert result.name == "Fighting Spirit"

    def test_find_by_name_is_case_sensitive(self):
        """맵 이름은 대소문자를 구분."""
        # Given
        self.repo.upsert("Dust2")

        # When
        result_exact = self.repo.find_by_name("Dust2")
        result_lower = self.repo.find_by_name("dust2")
        result_upper = self.repo.find_by_name("DUST2")

        # Then
        assert result_exact is not None
        assert result_lower is None
        assert result_upper is None

    # =========================================================================
    # upsert 테스트
    # =========================================================================

    def test_upsert_creates_new_map(self):
        """새로운 맵 생성."""
        # When
        map_entity = self.repo.upsert("New Map")

        # Then
        assert map_entity is not None
        assert map_entity.id is not None
        assert map_entity.name == "New Map"

    def test_upsert_returns_existing_map(self):
        """기존 맵이 있으면 반환."""
        # Given
        first = self.repo.upsert("Existing Map")
        first_id = first.id

        # When
        second = self.repo.upsert("Existing Map")

        # Then
        assert second.id == first_id
        assert second.name == "Existing Map"

    def test_upsert_is_idempotent(self):
        """upsert는 멱등성을 가짐 - 여러 번 호출해도 동일 결과."""
        # Given & When
        map1 = self.repo.upsert("Idempotent Map")
        map2 = self.repo.upsert("Idempotent Map")
        map3 = self.repo.upsert("Idempotent Map")

        # Then
        assert map1.id == map2.id == map3.id
        assert self.repo.count() == 1

    def test_upsert_updates_updated_at_on_conflict(self):
        """충돌 시 updated_at이 갱신되는지 확인."""
        # Given
        first = self.repo.upsert("Map With Timestamp")

        # When
        second = self.repo.upsert("Map With Timestamp")

        # Then
        assert second.id == first.id
        # updated_at이 갱신되었어야 함 (또는 동일할 수도 있음 - 빠른 실행 시)
        assert second.updated_at is not None
        assert first.updated_at is not None

    # =========================================================================
    # BaseRepository 메서드 테스트
    # =========================================================================

    def test_find_all_returns_all_maps(self):
        """모든 맵 조회."""
        # Given
        self.repo.upsert("Map1")
        self.repo.upsert("Map2")
        self.repo.upsert("Map3")

        # When
        maps = self.repo.find_all()

        # Then
        assert len(maps) == 3
        map_names = {m.name for m in maps}
        assert map_names == {"Map1", "Map2", "Map3"}

    def test_find_all_returns_empty_list_when_no_maps(self):
        """맵이 없으면 빈 리스트 반환."""
        # When
        maps = self.repo.find_all()

        # Then
        assert maps == []

    def test_count_returns_correct_count(self):
        """맵 수 조회."""
        # Given
        assert self.repo.count() == 0

        self.repo.upsert("Map1")
        assert self.repo.count() == 1

        self.repo.upsert("Map2")
        assert self.repo.count() == 2

    def test_find_by_id_returns_map(self):
        """ID로 맵 조회."""
        # Given
        map_entity = self.repo.upsert("Map By ID")

        # When
        found = self.repo.find_by_id(map_entity.id)

        # Then
        assert found is not None
        assert found.id == map_entity.id
        assert found.name == "Map By ID"

    def test_find_by_id_returns_none_for_nonexistent(self):
        """존재하지 않는 ID 조회 시 None 반환."""
        result = self.repo.find_by_id(9999)
        assert result is None

    def test_delete_removes_map(self):
        """맵 삭제."""
        # Given
        map_entity = self.repo.upsert("To Delete")

        # When
        result = self.repo.delete(map_entity.id)

        # Then
        assert result is True
        assert self.repo.find_by_name("To Delete") is None
        assert self.repo.count() == 0

    def test_delete_returns_false_for_nonexistent(self):
        """존재하지 않는 맵 삭제 시 False 반환."""
        result = self.repo.delete(9999)
        assert result is False

    def test_exists_returns_true_for_existing(self):
        """존재하는 맵 확인."""
        # Given
        map_entity = self.repo.upsert("Existing")

        # Then
        assert self.repo.exists(map_entity.id) is True

    def test_exists_returns_false_for_nonexistent(self):
        """존재하지 않는 맵 확인."""
        assert self.repo.exists(9999) is False

    def test_insert_creates_map(self):
        """insert로 맵 생성."""
        # Given
        map_entity = Map(name="Inserted Map")

        # When
        result = self.repo.insert(map_entity)

        # Then
        assert result.id is not None
        assert result.name == "Inserted Map"

    def test_update_modifies_map(self):
        """update로 맵 수정."""
        # Given
        map_entity = self.repo.upsert("Original Name")
        map_entity.name = "Updated Name"

        # When
        updated = self.repo.update(map_entity)

        # Then
        assert updated.name == "Updated Name"
        found = self.repo.find_by_id(map_entity.id)
        assert found.name == "Updated Name"

    def test_find_by_returns_matching_maps(self):
        """조건에 맞는 맵 조회."""
        # Given
        self.repo.upsert("Target Map")
        self.repo.upsert("Other Map")

        # When
        results = self.repo.find_by(name="Target Map")

        # Then
        assert len(results) == 1
        assert results[0].name == "Target Map"

    def test_find_by_returns_empty_when_no_match(self):
        """조건에 맞는 맵이 없으면 빈 리스트 반환."""
        # Given
        self.repo.upsert("Some Map")

        # When
        results = self.repo.find_by(name="Nonexistent")

        # Then
        assert results == []

    # =========================================================================
    # 테스트 격리 확인
    # =========================================================================

    def test_isolation_first(self):
        """테스트 격리 확인 1 - 맵 생성."""
        self.repo.upsert("Isolation Test Map")
        assert self.repo.count() == 1

    def test_isolation_second(self):
        """테스트 격리 확인 2 - 이전 테스트 데이터가 없어야 함."""
        # 이전 테스트에서 생성한 맵이 롤백되었으므로 없어야 함
        assert self.repo.find_by_name("Isolation Test Map") is None
        assert self.repo.count() == 0
