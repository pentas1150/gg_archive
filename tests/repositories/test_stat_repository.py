"""
Tests for StatRepository.

Uses transaction rollback for test isolation.
"""
import pytest

from repositories.stat_repository import StatRepository
from repositories.player_repository import PlayerRepository
from repositories.map_repository import MapRepository


class TestStatRepository:
    """StatRepository 테스트."""

    @pytest.fixture(autouse=True)
    def setup(self, db):
        """각 테스트 전에 repository 초기화."""
        self.repo = StatRepository()
        self.player_repo = PlayerRepository()
        self.map_repo = MapRepository()
        self.db = db

    @pytest.fixture
    def sample_player(self):
        """테스트용 플레이어 생성."""
        return self.player_repo.upsert("test_player")

    @pytest.fixture
    def sample_map(self):
        """테스트용 맵 생성."""
        from models.map import Map
        map_entity = Map(name="Dust2")
        return self.map_repo.insert(map_entity)

    # =========================================================================
    # find_by_player_id_and_map_id 테스트
    # =========================================================================

    def test_find_by_player_id_and_map_id_returns_none_when_not_exists(self):
        """존재하지 않는 stat 조회 시 None 반환."""
        result = self.repo.find_by_player_id_and_map_id(9999, 9999)
        assert result is None

    def test_find_by_player_id_and_map_id_returns_stat(
        self, sample_player, sample_map
    ):
        """존재하는 stat 조회."""
        # Given
        self.repo.upsert(sample_player.game_id, sample_map.name, is_win=True)

        # When
        result = self.repo.find_by_player_id_and_map_id(
            sample_player.id, sample_map.id
        )

        # Then
        assert result is not None
        assert result.player_id == sample_player.id
        assert result.map_id == sample_map.id

    # =========================================================================
    # find_by_player_id_and_map_name 테스트 (비정규화된 map_name 사용)
    # =========================================================================

    def test_find_by_player_id_and_map_name_returns_none_when_not_exists(self):
        """존재하지 않는 stat 조회 시 None 반환."""
        result = self.repo.find_by_player_id_and_map_name(9999, "NonExistent")
        assert result is None

    def test_find_by_player_id_and_map_name_returns_stat(
        self, sample_player, sample_map
    ):
        """map_name으로 stat 조회 (JOIN 없이)."""
        # Given
        self.repo.upsert(sample_player.game_id, sample_map.name, is_win=True)

        # When
        result = self.repo.find_by_player_id_and_map_name(
            sample_player.id, sample_map.name
        )

        # Then
        assert result is not None
        assert result.player_id == sample_player.id
        assert result.map_name == sample_map.name

    # =========================================================================
    # find_by_player_id_sorted_by_map 테스트
    # =========================================================================

    def test_find_by_player_id_sorted_by_map_returns_sorted_stats(
        self, sample_player
    ):
        """플레이어의 stat을 map_name으로 정렬하여 반환."""
        # Given
        from models.map import Map
        self.map_repo.insert(Map(name="Zzz_Last"))
        self.map_repo.insert(Map(name="Aaa_First"))
        self.map_repo.insert(Map(name="Mmm_Middle"))

        self.repo.upsert(sample_player.game_id, "Zzz_Last", is_win=True)
        self.repo.upsert(sample_player.game_id, "Aaa_First", is_win=True)
        self.repo.upsert(sample_player.game_id, "Mmm_Middle", is_win=True)

        # When
        stats = self.repo.find_by_player_id_sorted_by_map(sample_player.id)

        # Then
        assert len(stats) == 3
        assert stats[0].map_name == "Aaa_First"
        assert stats[1].map_name == "Mmm_Middle"
        assert stats[2].map_name == "Zzz_Last"

    def test_find_by_player_id_sorted_by_map_returns_empty_for_new_player(self):
        """stat이 없는 플레이어는 빈 리스트 반환."""
        stats = self.repo.find_by_player_id_sorted_by_map(9999)
        assert stats == []

    # =========================================================================
    # upsert 테스트 - map_name 저장 확인
    # =========================================================================

    def test_upsert_stores_map_name(self, sample_player, sample_map):
        """upsert 시 map_name이 저장되는지 확인."""
        # When
        self.repo.upsert(sample_player.game_id, sample_map.name, is_win=True)

        # Then
        stat = self.repo.find_by_player_id_and_map_id(
            sample_player.id, sample_map.id
        )
        assert stat.map_name == sample_map.name

    # =========================================================================
    # upsert 테스트 - INSERT (새 레코드)
    # =========================================================================

    def test_upsert_creates_new_stat_on_win(self, sample_player, sample_map):
        """첫 승리 시 새 stat 생성."""
        # When
        self.repo.upsert(sample_player.game_id, sample_map.name, is_win=True)

        # Then
        stat = self.repo.find_by_player_id_and_map_id(
            sample_player.id, sample_map.id
        )
        assert stat is not None
        assert stat.total_games == 1
        assert stat.wins == 1
        assert stat.losses == 0
        assert stat.win_rate == 100.0
        assert stat.map_name == sample_map.name

    def test_upsert_creates_new_stat_on_loss(self, sample_player, sample_map):
        """첫 패배 시 새 stat 생성."""
        # When
        self.repo.upsert(sample_player.game_id, sample_map.name, is_win=False)

        # Then
        stat = self.repo.find_by_player_id_and_map_id(
            sample_player.id, sample_map.id
        )
        assert stat is not None
        assert stat.total_games == 1
        assert stat.wins == 0
        assert stat.losses == 1
        assert stat.win_rate == 0.0

    # =========================================================================
    # upsert 테스트 - UPDATE (기존 레코드)
    # =========================================================================

    def test_upsert_updates_stat_on_subsequent_wins(
        self, sample_player, sample_map
    ):
        """연속 승리 시 stat 업데이트."""
        # Given
        self.repo.upsert(sample_player.game_id, sample_map.name, is_win=True)

        # When
        self.repo.upsert(sample_player.game_id, sample_map.name, is_win=True)

        # Then
        stat = self.repo.find_by_player_id_and_map_id(
            sample_player.id, sample_map.id
        )
        assert stat.total_games == 2
        assert stat.wins == 2
        assert stat.losses == 0
        assert stat.win_rate == 100.0

    def test_upsert_updates_stat_on_subsequent_losses(
        self, sample_player, sample_map
    ):
        """연속 패배 시 stat 업데이트."""
        # Given
        self.repo.upsert(sample_player.game_id, sample_map.name, is_win=False)

        # When
        self.repo.upsert(sample_player.game_id, sample_map.name, is_win=False)

        # Then
        stat = self.repo.find_by_player_id_and_map_id(
            sample_player.id, sample_map.id
        )
        assert stat.total_games == 2
        assert stat.wins == 0
        assert stat.losses == 2
        assert stat.win_rate == 0.0

    def test_upsert_calculates_win_rate_correctly(
        self, sample_player, sample_map
    ):
        """win_rate 계산 정확성 테스트."""
        # Given: 10게임 중 7승 3패
        for _ in range(7):
            self.repo.upsert(sample_player.game_id, sample_map.name, is_win=True)
        for _ in range(3):
            self.repo.upsert(sample_player.game_id, sample_map.name, is_win=False)

        # Then
        stat = self.repo.find_by_player_id_and_map_id(
            sample_player.id, sample_map.id
        )
        assert stat.total_games == 10
        assert stat.wins == 7
        assert stat.losses == 3
        assert stat.win_rate == 70.0  # 7/10 * 100

    def test_upsert_win_rate_with_mixed_results(self, sample_player, sample_map):
        """승패 혼합 시 win_rate 계산."""
        # W, L, W, L, W = 3승 2패
        results = [True, False, True, False, True]
        for is_win in results:
            self.repo.upsert(sample_player.game_id, sample_map.name, is_win=is_win)

        stat = self.repo.find_by_player_id_and_map_id(
            sample_player.id, sample_map.id
        )
        assert stat.total_games == 5
        assert stat.wins == 3
        assert stat.losses == 2
        assert stat.win_rate == 60.0  # 3/5 * 100

    # =========================================================================
    # 여러 맵에 대한 stat 테스트
    # =========================================================================

    def test_upsert_creates_separate_stats_per_map(self, sample_player):
        """맵별로 별도 stat 생성."""
        # Given
        from models.map import Map
        map1 = self.map_repo.insert(Map(name="Dust2"))
        map2 = self.map_repo.insert(Map(name="Mirage"))

        # When
        self.repo.upsert(sample_player.game_id, "Dust2", is_win=True)
        self.repo.upsert(sample_player.game_id, "Dust2", is_win=True)
        self.repo.upsert(sample_player.game_id, "Mirage", is_win=False)

        # Then
        stat1 = self.repo.find_by_player_id_and_map_id(sample_player.id, map1.id)
        stat2 = self.repo.find_by_player_id_and_map_id(sample_player.id, map2.id)

        assert stat1.total_games == 2
        assert stat1.wins == 2
        assert stat1.win_rate == 100.0
        assert stat1.map_name == "Dust2"

        assert stat2.total_games == 1
        assert stat2.losses == 1
        assert stat2.win_rate == 0.0
        assert stat2.map_name == "Mirage"

    def test_upsert_creates_separate_stats_per_player(self, sample_map):
        """플레이어별로 별도 stat 생성."""
        # Given
        player1 = self.player_repo.upsert("player1")
        player2 = self.player_repo.upsert("player2")

        # When
        self.repo.upsert("player1", sample_map.name, is_win=True)
        self.repo.upsert("player2", sample_map.name, is_win=False)

        # Then
        stat1 = self.repo.find_by_player_id_and_map_id(player1.id, sample_map.id)
        stat2 = self.repo.find_by_player_id_and_map_id(player2.id, sample_map.id)

        assert stat1.wins == 1
        assert stat1.win_rate == 100.0

        assert stat2.losses == 1
        assert stat2.win_rate == 0.0

    # =========================================================================
    # BaseRepository 메서드 테스트
    # =========================================================================

    def test_find_all_returns_all_stats(self, sample_player):
        """모든 stat 조회."""
        # Given
        from models.map import Map
        self.map_repo.insert(Map(name="Map1"))
        self.map_repo.insert(Map(name="Map2"))
        self.map_repo.insert(Map(name="Map3"))

        self.repo.upsert(sample_player.game_id, "Map1", is_win=True)
        self.repo.upsert(sample_player.game_id, "Map2", is_win=True)
        self.repo.upsert(sample_player.game_id, "Map3", is_win=True)

        # When
        stats = self.repo.find_all()

        # Then
        assert len(stats) == 3

    def test_count_returns_correct_count(self, sample_player, sample_map):
        """stat 개수 조회."""
        assert self.repo.count() == 0

        self.repo.upsert(sample_player.game_id, sample_map.name, is_win=True)
        assert self.repo.count() == 1

    def test_delete_removes_stat(self, sample_player, sample_map):
        """stat 삭제."""
        # Given
        self.repo.upsert(sample_player.game_id, sample_map.name, is_win=True)
        stat = self.repo.find_by_player_id_and_map_id(
            sample_player.id, sample_map.id
        )

        # When
        result = self.repo.delete(stat.id)

        # Then
        assert result is True
        assert self.repo.find_by_player_id_and_map_id(
            sample_player.id, sample_map.id
        ) is None

    # =========================================================================
    # 테스트 격리 확인
    # =========================================================================

    def test_isolation_first(self, sample_player, sample_map):
        """테스트 격리 확인 1 - stat 생성."""
        self.repo.upsert(sample_player.game_id, sample_map.name, is_win=True)
        assert self.repo.count() == 1

    def test_isolation_second(self):
        """테스트 격리 확인 2 - 이전 테스트 데이터가 없어야 함."""
        assert self.repo.count() == 0
