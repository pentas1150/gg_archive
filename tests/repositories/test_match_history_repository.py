"""
Tests for MatchHistoryRepository.

Uses transaction rollback for test isolation.
"""
from datetime import datetime, timedelta, UTC

import pytest

from common.const import TypeOrderColumn, TypeOrderDirection
from models.match_history import MatchHistory
from repositories.match_history_repository import MatchHistoryRepository
from repositories.player_repository import PlayerRepository
from repositories.map_repository import MapRepository


class TestMatchHistoryRepository:
    """MatchHistoryRepository 테스트."""

    @pytest.fixture(autouse=True)
    def setup(self, db, db_session):
        """각 테스트 전에 repository 초기화."""
        self.repo = MatchHistoryRepository(session=db_session)
        self.player_repo = PlayerRepository(session=db_session)
        self.map_repo = MapRepository(session=db_session)
        self.db = db
        self.db_session = db_session

    @pytest.fixture
    def sample_player(self):
        """테스트용 플레이어 생성."""
        return self.player_repo.upsert("test_player")

    @pytest.fixture
    def sample_map(self):
        """테스트용 맵 생성."""
        return self.map_repo.upsert("Fighting Spirit")

    @pytest.fixture
    def sample_match_history(self, sample_player, sample_map):
        """테스트용 매치 히스토리 생성."""
        match = MatchHistory(
            player_id=sample_player.id,
            opponent_id="opponent_1",
            race="Terran",
            map_id=sample_map.id,
            map_name=sample_map.name,
            is_win=True,
            playtime=300,
            played_at=datetime.now(UTC)
        )
        return self.repo.insert(match)

    # =========================================================================
    # insert 테스트
    # =========================================================================

    def test_insert_creates_match_history(self, sample_player, sample_map):
        """새로운 매치 히스토리 생성."""
        # Given
        played_at = datetime.now(UTC)
        match = MatchHistory(
            player_id=sample_player.id,
            opponent_id="opponent_1",
            race="Zerg",
            map_id=sample_map.id,
            map_name=sample_map.name,
            is_win=True,
            playtime=600,
            played_at=played_at
        )

        # When
        result = self.repo.insert(match)

        # Then
        assert result is not None
        assert result.id is not None
        assert result.player_id == sample_player.id
        assert result.opponent_id == "opponent_1"
        assert result.race == "Zerg"
        assert result.map_id == sample_map.id
        assert result.map_name == sample_map.name
        assert result.is_win is True
        assert result.playtime == 600

    def test_insert_returns_none_on_duplicate(self, sample_player, sample_map):
        """중복 삽입 시 None 반환 (UniqueConstraint: played_at + player_id)."""
        # Given
        played_at = datetime.now(UTC)
        match1 = MatchHistory(
            player_id=sample_player.id,
            opponent_id="opponent_1",
            race="Protoss",
            map_id=sample_map.id,
            map_name=sample_map.name,
            is_win=True,
            playtime=300,
            played_at=played_at
        )
        self.repo.insert(match1)

        # When - 동일한 played_at과 player_id로 다시 삽입 시도
        match2 = MatchHistory(
            player_id=sample_player.id,
            opponent_id="opponent_2",  # 다른 상대
            race="Zerg",
            map_id=sample_map.id,
            map_name=sample_map.name,
            is_win=False,
            playtime=400,
            played_at=played_at  # 동일한 시간
        )
        result = self.repo.insert(match2)

        # Then
        assert result is None
        assert self.repo.count() == 1

    def test_insert_allows_different_played_at(self, sample_player, sample_map):
        """다른 played_at으로는 동일 player_id도 삽입 가능."""
        # Given
        now = datetime.now(UTC)
        match1 = MatchHistory(
            player_id=sample_player.id,
            opponent_id="opponent_1",
            race="Terran",
            map_id=sample_map.id,
            map_name=sample_map.name,
            is_win=True,
            playtime=300,
            played_at=now
        )
        self.repo.insert(match1)

        # When
        match2 = MatchHistory(
            player_id=sample_player.id,
            opponent_id="opponent_2",
            race="Zerg",
            map_id=sample_map.id,
            map_name=sample_map.name,
            is_win=False,
            playtime=400,
            played_at=now + timedelta(hours=1)  # 다른 시간
        )
        result = self.repo.insert(match2)

        # Then
        assert result is not None
        assert self.repo.count() == 2

    def test_insert_allows_different_player_id(self, sample_map):
        """다른 player_id로는 동일 played_at도 삽입 가능."""
        # Given
        player1 = self.player_repo.upsert("player_1")
        player2 = self.player_repo.upsert("player_2")
        now = datetime.now(UTC)

        match1 = MatchHistory(
            player_id=player1.id,
            opponent_id="opponent",
            race="Terran",
            map_id=sample_map.id,
            map_name=sample_map.name,
            is_win=True,
            playtime=300,
            played_at=now
        )
        self.repo.insert(match1)

        # When
        match2 = MatchHistory(
            player_id=player2.id,
            opponent_id="opponent",
            race="Terran",
            map_id=sample_map.id,
            map_name=sample_map.name,
            is_win=False,
            playtime=400,
            played_at=now  # 동일한 시간, 다른 플레이어
        )
        result = self.repo.insert(match2)

        # Then
        assert result is not None
        assert self.repo.count() == 2

    # =========================================================================
    # find_all_with_order 테스트
    # =========================================================================

    def test_find_all_with_order_by_played_at_desc(self, sample_player, sample_map):
        """played_at 내림차순 정렬."""
        # Given
        now = datetime.now(UTC)
        for i in range(3):
            match = MatchHistory(
                player_id=sample_player.id,
                opponent_id=f"opponent_{i}",
                race="Terran",
                map_id=sample_map.id,
                map_name=sample_map.name,
                is_win=True,
                playtime=300,
                played_at=now - timedelta(hours=i)
            )
            self.repo.insert(match)

        # When
        results = self.repo.find_all_with_order(
            TypeOrderColumn.PLAYED_AT,
            TypeOrderDirection.DESC
        )

        # Then
        assert len(results) == 3
        # 최신 순서 (now, now-1h, now-2h)
        assert results[0].opponent_id == "opponent_0"
        assert results[1].opponent_id == "opponent_1"
        assert results[2].opponent_id == "opponent_2"

    def test_find_all_with_order_by_played_at_asc(self, sample_player, sample_map):
        """played_at 오름차순 정렬."""
        # Given
        now = datetime.now(UTC)
        for i in range(3):
            match = MatchHistory(
                player_id=sample_player.id,
                opponent_id=f"opponent_{i}",
                race="Terran",
                map_id=sample_map.id,
                map_name=sample_map.name,
                is_win=True,
                playtime=300,
                played_at=now - timedelta(hours=i)
            )
            self.repo.insert(match)

        # When
        results = self.repo.find_all_with_order(
            TypeOrderColumn.PLAYED_AT,
            TypeOrderDirection.ASC
        )

        # Then
        assert len(results) == 3
        # 오래된 순서 (now-2h, now-1h, now)
        assert results[0].opponent_id == "opponent_2"
        assert results[1].opponent_id == "opponent_1"
        assert results[2].opponent_id == "opponent_0"

    def test_find_all_with_order_returns_empty_when_no_data(self):
        """데이터가 없으면 빈 리스트 반환."""
        # When
        results = self.repo.find_all_with_order(
            TypeOrderColumn.PLAYED_AT,
            TypeOrderDirection.DESC
        )

        # Then
        assert results == []

    def test_find_all_with_order_raises_for_invalid_column(self):
        """잘못된 order_by 값에 대해 ValueError 발생."""
        # When & Then
        with pytest.raises(ValueError):
            self.repo.find_all_with_order("invalid_column", TypeOrderDirection.DESC)

    # =========================================================================
    # find_all_by_player_with_order 테스트
    # =========================================================================

    def test_find_all_by_player_with_order_returns_only_player_matches(
        self, sample_map
    ):
        """특정 플레이어의 매치만 반환."""
        # Given
        player1 = self.player_repo.upsert("player_1")
        player2 = self.player_repo.upsert("player_2")
        now = datetime.now(UTC)

        # player1의 매치 2개
        for i in range(2):
            match = MatchHistory(
                player_id=player1.id,
                opponent_id=f"opponent_{i}",
                race="Terran",
                map_id=sample_map.id,
                map_name=sample_map.name,
                is_win=True,
                playtime=300,
                played_at=now - timedelta(hours=i)
            )
            self.repo.insert(match)

        # player2의 매치 3개
        for i in range(3):
            match = MatchHistory(
                player_id=player2.id,
                opponent_id=f"opponent_{i}",
                race="Zerg",
                map_id=sample_map.id,
                map_name=sample_map.name,
                is_win=False,
                playtime=400,
                played_at=now - timedelta(hours=i + 10)
            )
            self.repo.insert(match)

        # When
        results = self.repo.find_all_by_player_with_order(
            player1.id,
            TypeOrderColumn.PLAYED_AT,
            TypeOrderDirection.DESC
        )

        # Then
        assert len(results) == 2
        for result in results:
            assert result.player_id == player1.id

    def test_find_all_by_player_with_order_sorted_desc(
        self, sample_player, sample_map
    ):
        """플레이어 매치를 내림차순 정렬."""
        # Given
        now = datetime.now(UTC)
        for i in range(3):
            match = MatchHistory(
                player_id=sample_player.id,
                opponent_id=f"opponent_{i}",
                race="Protoss",
                map_id=sample_map.id,
                map_name=sample_map.name,
                is_win=i % 2 == 0,
                playtime=300 + i * 100,
                played_at=now - timedelta(hours=i)
            )
            self.repo.insert(match)

        # When
        results = self.repo.find_all_by_player_with_order(
            sample_player.id,
            TypeOrderColumn.PLAYED_AT,
            TypeOrderDirection.DESC
        )

        # Then
        assert len(results) == 3
        assert results[0].opponent_id == "opponent_0"  # 가장 최근
        assert results[2].opponent_id == "opponent_2"  # 가장 오래됨

    def test_find_all_by_player_with_order_sorted_asc(
        self, sample_player, sample_map
    ):
        """플레이어 매치를 오름차순 정렬."""
        # Given
        now = datetime.now(UTC)
        for i in range(3):
            match = MatchHistory(
                player_id=sample_player.id,
                opponent_id=f"opponent_{i}",
                race="Protoss",
                map_id=sample_map.id,
                map_name=sample_map.name,
                is_win=i % 2 == 0,
                playtime=300 + i * 100,
                played_at=now - timedelta(hours=i)
            )
            self.repo.insert(match)

        # When
        results = self.repo.find_all_by_player_with_order(
            sample_player.id,
            TypeOrderColumn.PLAYED_AT,
            TypeOrderDirection.ASC
        )

        # Then
        assert len(results) == 3
        assert results[0].opponent_id == "opponent_2"  # 가장 오래됨
        assert results[2].opponent_id == "opponent_0"  # 가장 최근

    def test_find_all_by_player_with_order_returns_empty_for_no_matches(
        self, sample_player
    ):
        """플레이어의 매치가 없으면 빈 리스트 반환."""
        # When
        results = self.repo.find_all_by_player_with_order(
            sample_player.id,
            TypeOrderColumn.PLAYED_AT,
            TypeOrderDirection.DESC
        )

        # Then
        assert results == []

    def test_find_all_by_player_with_order_returns_empty_for_nonexistent_player(self):
        """존재하지 않는 플레이어 ID로 조회 시 빈 리스트 반환."""
        # When
        results = self.repo.find_all_by_player_with_order(
            9999,
            TypeOrderColumn.PLAYED_AT,
            TypeOrderDirection.DESC
        )

        # Then
        assert results == []

    def test_find_all_by_player_with_order_raises_for_invalid_column(
        self, sample_player
    ):
        """잘못된 order_by 값에 대해 ValueError 발생."""
        # When & Then
        with pytest.raises(ValueError):
            self.repo.find_all_by_player_with_order(
                sample_player.id,
                "invalid_column",
                TypeOrderDirection.DESC
            )

    # =========================================================================
    # BaseRepository 메서드 테스트
    # =========================================================================

    def test_find_all_returns_all_matches(self, sample_player, sample_map):
        """모든 매치 히스토리 조회."""
        # Given
        now = datetime.now(UTC)
        for i in range(3):
            match = MatchHistory(
                player_id=sample_player.id,
                opponent_id=f"opponent_{i}",
                race="Terran",
                map_id=sample_map.id,
                map_name=sample_map.name,
                is_win=True,
                playtime=300,
                played_at=now - timedelta(hours=i)
            )
            self.repo.insert(match)

        # When
        results = self.repo.find_all()

        # Then
        assert len(results) == 3

    def test_find_all_returns_empty_when_no_matches(self):
        """매치가 없으면 빈 리스트 반환."""
        # When
        results = self.repo.find_all()

        # Then
        assert results == []

    def test_count_returns_correct_count(self, sample_player, sample_map):
        """매치 수 조회."""
        # Given
        assert self.repo.count() == 0

        now = datetime.now(UTC)
        match1 = MatchHistory(
            player_id=sample_player.id,
            opponent_id="opponent_1",
            race="Terran",
            map_id=sample_map.id,
            map_name=sample_map.name,
            is_win=True,
            playtime=300,
            played_at=now
        )
        self.repo.insert(match1)
        assert self.repo.count() == 1

        match2 = MatchHistory(
            player_id=sample_player.id,
            opponent_id="opponent_2",
            race="Zerg",
            map_id=sample_map.id,
            map_name=sample_map.name,
            is_win=False,
            playtime=400,
            played_at=now + timedelta(hours=1)
        )
        self.repo.insert(match2)
        assert self.repo.count() == 2

    def test_find_by_id_returns_match(self, sample_match_history):
        """ID로 매치 조회."""
        # When
        found = self.repo.find_by_id(sample_match_history.id)

        # Then
        assert found is not None
        assert found.id == sample_match_history.id

    def test_find_by_id_returns_none_for_nonexistent(self):
        """존재하지 않는 ID 조회 시 None 반환."""
        result = self.repo.find_by_id(9999)
        assert result is None

    def test_delete_removes_match(self, sample_match_history):
        """매치 삭제."""
        # When
        result = self.repo.delete(sample_match_history.id)

        # Then
        assert result is True
        assert self.repo.find_by_id(sample_match_history.id) is None
        assert self.repo.count() == 0

    def test_delete_returns_false_for_nonexistent(self):
        """존재하지 않는 매치 삭제 시 False 반환."""
        result = self.repo.delete(9999)
        assert result is False

    def test_exists_returns_true_for_existing(self, sample_match_history):
        """존재하는 매치 확인."""
        assert self.repo.exists(sample_match_history.id) is True

    def test_exists_returns_false_for_nonexistent(self):
        """존재하지 않는 매치 확인."""
        assert self.repo.exists(9999) is False

    def test_find_by_returns_matching_matches(self, sample_player, sample_map):
        """조건에 맞는 매치 조회."""
        # Given
        now = datetime.now(UTC)
        match1 = MatchHistory(
            player_id=sample_player.id,
            opponent_id="target_opponent",
            race="Terran",
            map_id=sample_map.id,
            map_name=sample_map.name,
            is_win=True,
            playtime=300,
            played_at=now
        )
        self.repo.insert(match1)

        match2 = MatchHistory(
            player_id=sample_player.id,
            opponent_id="other_opponent",
            race="Zerg",
            map_id=sample_map.id,
            map_name=sample_map.name,
            is_win=False,
            playtime=400,
            played_at=now + timedelta(hours=1)
        )
        self.repo.insert(match2)

        # When
        results = self.repo.find_by(opponent_id="target_opponent")

        # Then
        assert len(results) == 1
        assert results[0].opponent_id == "target_opponent"

    def test_find_by_is_win_filter(self, sample_player, sample_map):
        """승리 여부로 필터링."""
        # Given
        now = datetime.now(UTC)
        # 승리 2개
        for i in range(2):
            match = MatchHistory(
                player_id=sample_player.id,
                opponent_id=f"win_opponent_{i}",
                race="Terran",
                map_id=sample_map.id,
                map_name=sample_map.name,
                is_win=True,
                playtime=300,
                played_at=now + timedelta(hours=i)
            )
            self.repo.insert(match)

        # 패배 3개
        for i in range(3):
            match = MatchHistory(
                player_id=sample_player.id,
                opponent_id=f"loss_opponent_{i}",
                race="Zerg",
                map_id=sample_map.id,
                map_name=sample_map.name,
                is_win=False,
                playtime=400,
                played_at=now + timedelta(hours=i + 10)
            )
            self.repo.insert(match)

        # When
        wins = self.repo.find_by(is_win=True)
        losses = self.repo.find_by(is_win=False)

        # Then
        assert len(wins) == 2
        assert len(losses) == 3

    # =========================================================================
    # 테스트 격리 확인
    # =========================================================================

    def test_isolation_first(self, sample_player, sample_map):
        """테스트 격리 확인 1 - 매치 히스토리 생성."""
        match = MatchHistory(
            player_id=sample_player.id,
            opponent_id="isolation_test",
            race="Terran",
            map_id=sample_map.id,
            map_name=sample_map.name,
            is_win=True,
            playtime=300,
            played_at=datetime.now(UTC)
        )
        self.repo.insert(match)
        assert self.repo.count() == 1

    def test_isolation_second(self):
        """테스트 격리 확인 2 - 이전 테스트 데이터가 없어야 함."""
        # 이전 테스트에서 생성한 매치가 롤백되었으므로 없어야 함
        results = self.repo.find_by(opponent_id="isolation_test")
        assert results == []
        assert self.repo.count() == 0
