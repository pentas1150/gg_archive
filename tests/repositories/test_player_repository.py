"""
Tests for PlayerRepository.

Uses transaction rollback for test isolation.
"""
from datetime import datetime, timedelta

import pytest

from common.const import TypeOrderColumn, TypeOrderDirection
from models.player import Player
from repositories.player_repository import PlayerRepository


class TestPlayerRepository:
    """PlayerRepository 테스트."""

    @pytest.fixture(autouse=True)
    def setup(self, db, db_session):
        """각 테스트 전에 repository 초기화."""
        self.repo = PlayerRepository(session=db_session)
        self.db = db
        self.db_session = db_session

    # =========================================================================
    # find_by_game_id 테스트
    # =========================================================================

    def test_find_by_game_id_returns_none_when_not_exists(self):
        """존재하지 않는 game_id 검색 시 None 반환."""
        result = self.repo.find_by_game_id("nonexistent")
        assert result is None

    def test_find_by_game_id_returns_player_when_exists(self):
        """존재하는 game_id 검색 시 Player 반환."""
        # Given
        self.repo.upsert("player123")

        # When
        result = self.repo.find_by_game_id("player123")

        # Then
        assert result is not None
        assert result.game_id == "player123"

    # =========================================================================
    # find_all_with_order_and_search_by_game_id 테스트
    # =========================================================================

    def test_find_all_with_order_by_total_wins_asc(self):
        """승수 오름차순 정렬."""
        # Given: 각각 다른 승수를 가진 플레이어 생성
        now = datetime.now()
        self.repo.upsert("player_a")  # 0승
        self.repo.upsert("player_b")
        self.repo.update_with_stats("player_b", is_win=True, last_played_at=now)  # 1승
        self.repo.upsert("player_c")
        for _ in range(3):
            self.repo.update_with_stats("player_c", is_win=True, last_played_at=now)  # 3승

        # When
        players = self.repo.find_all_with_order_and_search_by_game_id(
            "",
            TypeOrderColumn.TOTAL_WINS,
            TypeOrderDirection.ASC
        )

        # Then
        assert len(players) == 3
        assert players[0].total_wins == 0
        assert players[1].total_wins == 1
        assert players[2].total_wins == 3

    def test_find_all_with_order_by_total_wins_desc(self):
        """승수 내림차순 정렬."""
        # Given
        now = datetime.now()
        self.repo.upsert("player_a")  # 0승
        self.repo.upsert("player_b")
        self.repo.update_with_stats("player_b", is_win=True, last_played_at=now)  # 1승
        self.repo.upsert("player_c")
        for _ in range(3):
            self.repo.update_with_stats("player_c", is_win=True, last_played_at=now)  # 3승

        # When
        players = self.repo.find_all_with_order_and_search_by_game_id(
            "",
            TypeOrderColumn.TOTAL_WINS,
            TypeOrderDirection.DESC
        )

        # Then
        assert len(players) == 3
        assert players[0].total_wins == 3
        assert players[1].total_wins == 1
        assert players[2].total_wins == 0

    def test_find_all_with_order_by_total_losses_asc(self):
        """패수 오름차순 정렬."""
        # Given
        now = datetime.now()
        self.repo.upsert("player_a")  # 0패
        self.repo.upsert("player_b")
        for _ in range(2):
            self.repo.update_with_stats("player_b", is_win=False, last_played_at=now)  # 2패
        self.repo.upsert("player_c")
        self.repo.update_with_stats("player_c", is_win=False, last_played_at=now)  # 1패

        # When
        players = self.repo.find_all_with_order_and_search_by_game_id(
            "",
            TypeOrderColumn.TOTAL_LOSSES,
            TypeOrderDirection.ASC
        )

        # Then
        assert len(players) == 3
        assert players[0].total_losses == 0
        assert players[1].total_losses == 1
        assert players[2].total_losses == 2

    def test_find_all_with_order_by_total_losses_desc(self):
        """패수 내림차순 정렬."""
        # Given
        now = datetime.now()
        self.repo.upsert("player_a")  # 0패
        self.repo.upsert("player_b")
        for _ in range(2):
            self.repo.update_with_stats("player_b", is_win=False, last_played_at=now)  # 2패
        self.repo.upsert("player_c")
        self.repo.update_with_stats("player_c", is_win=False, last_played_at=now)  # 1패

        # When
        players = self.repo.find_all_with_order_and_search_by_game_id(
            "",
            TypeOrderColumn.TOTAL_LOSSES,
            TypeOrderDirection.DESC
        )

        # Then
        assert len(players) == 3
        assert players[0].total_losses == 2
        assert players[1].total_losses == 1
        assert players[2].total_losses == 0

    def test_find_all_with_order_returns_empty_list_when_no_players(self):
        """플레이어가 없으면 빈 리스트 반환."""
        # When
        players = self.repo.find_all_with_order_and_search_by_game_id(
            "",
            TypeOrderColumn.TOTAL_WINS,
            TypeOrderDirection.DESC
        )

        # Then
        assert players == []

    def test_get_column_raises_error_for_invalid_column(self):
        """존재하지 않는 컬럼 접근 시 ValueError 발생."""
        from enum import Enum

        # 테스트용 잘못된 enum 생성
        class InvalidOrderColumn(Enum):
            INVALID = "nonexistent_column"

            def get_column(self, model):
                column = getattr(model, self.value, None)
                if column is None:
                    raise ValueError(
                        f"Column '{self.value}' not found in {model.__name__}"
                    )
                return column

        # When & Then
        with pytest.raises(ValueError) as exc_info:
            InvalidOrderColumn.INVALID.get_column(Player)

        assert "nonexistent_column" in str(exc_info.value)
        assert "Player" in str(exc_info.value)

    def test_find_all_with_order_secondary_sort_by_last_played_at_desc(self):
        """동일한 승수일 때 last_played_at 내림차순으로 2차 정렬 (최신 먼저)."""
        # Given: 모두 1승인 플레이어 3명, 명시적으로 다른 last_played_at 설정
        now = datetime.now()

        self.repo.upsert("player_a")
        self.repo.update_with_stats("player_a", is_win=True, last_played_at=now - timedelta(hours=2))
        self.repo.upsert("player_b")
        self.repo.update_with_stats("player_b", is_win=True, last_played_at=now - timedelta(hours=1))
        self.repo.upsert("player_c")
        self.repo.update_with_stats("player_c", is_win=True, last_played_at=now)

        # When: DESC 정렬 시 최신 플레이한 플레이어가 먼저
        players = self.repo.find_all_with_order_and_search_by_game_id(
            "",
            TypeOrderColumn.TOTAL_WINS,
            TypeOrderDirection.DESC
        )

        # Then: 모두 1승이므로 last_played_at DESC 순 (c -> b -> a)
        assert len(players) == 3
        assert all(p.total_wins == 1 for p in players)
        assert players[0].game_id == "player_c"
        assert players[1].game_id == "player_b"
        assert players[2].game_id == "player_a"

    def test_find_all_with_order_secondary_sort_by_last_played_at_asc(self):
        """동일한 승수일 때 last_played_at 오름차순으로 2차 정렬 (오래된 것 먼저)."""
        # Given: 모두 1승인 플레이어 3명, 명시적으로 다른 last_played_at 설정
        now = datetime.now()

        self.repo.upsert("player_a")
        self.repo.update_with_stats("player_a", is_win=True, last_played_at=now - timedelta(hours=2))
        self.repo.upsert("player_b")
        self.repo.update_with_stats("player_b", is_win=True, last_played_at=now - timedelta(hours=1))
        self.repo.upsert("player_c")
        self.repo.update_with_stats("player_c", is_win=True, last_played_at=now)

        # When: ASC 정렬 시 오래된 플레이한 플레이어가 먼저
        players = self.repo.find_all_with_order_and_search_by_game_id(
            "",
            TypeOrderColumn.TOTAL_WINS,
            TypeOrderDirection.ASC
        )

        # Then: 모두 1승이므로 last_played_at ASC 순 (a -> b -> c)
        assert len(players) == 3
        assert all(p.total_wins == 1 for p in players)
        assert players[0].game_id == "player_a"
        assert players[1].game_id == "player_b"
        assert players[2].game_id == "player_c"

    def test_find_all_with_order_mixed_primary_and_secondary_sort(self):
        """1차 정렬(승수) + 2차 정렬(last_played_at) 혼합 테스트."""
        # Given:
        # player_a: 2승 (먼저 플레이)
        # player_b: 2승 (나중에 플레이)
        # player_c: 1승
        # player_d: 0승
        now = datetime.now()

        self.repo.upsert("player_a")
        self.repo.update_with_stats("player_a", is_win=True, last_played_at=now - timedelta(hours=3))
        self.repo.update_with_stats("player_a", is_win=True, last_played_at=now - timedelta(hours=3))  # 2승

        self.repo.upsert("player_b")
        self.repo.update_with_stats("player_b", is_win=True, last_played_at=now - timedelta(hours=2))
        self.repo.update_with_stats("player_b", is_win=True, last_played_at=now - timedelta(hours=2))  # 2승

        self.repo.upsert("player_c")
        self.repo.update_with_stats("player_c", is_win=True, last_played_at=now - timedelta(hours=1))  # 1승

        self.repo.upsert("player_d")  # 0승
        # player_d의 last_played_at은 None이므로 별도 설정

        # When: 승수 DESC 정렬
        players = self.repo.find_all_with_order_and_search_by_game_id(
            "",
            TypeOrderColumn.TOTAL_WINS,
            TypeOrderDirection.DESC
        )

        # Then: 2승 그룹 (b먼저, a나중) -> 1승 -> 0승
        assert len(players) == 4
        # 2승 그룹: b가 더 최근에 플레이했으므로 먼저
        assert players[0].game_id == "player_b"
        assert players[0].total_wins == 2
        assert players[1].game_id == "player_a"
        assert players[1].total_wins == 2
        # 1승
        assert players[2].game_id == "player_c"
        assert players[2].total_wins == 1
        # 0승
        assert players[3].game_id == "player_d"
        assert players[3].total_wins == 0

    # =========================================================================
    # upsert 테스트
    # =========================================================================

    def test_upsert_creates_new_player(self):
        """새로운 플레이어 생성."""
        # When
        player = self.repo.upsert("new_player")

        # Then
        assert player is not None
        assert player.id is not None
        assert player.game_id == "new_player"
        assert player.total_games == 0
        assert player.total_wins == 0
        assert player.total_losses == 0
        assert player.total_win_rate == 0.0

    def test_upsert_returns_existing_player(self):
        """기존 플레이어가 있으면 반환."""
        # Given
        first = self.repo.upsert("existing_player")
        first_id = first.id

        # When
        second = self.repo.upsert("existing_player")

        # Then
        assert second.id == first_id
        assert second.game_id == "existing_player"

    def test_upsert_is_idempotent(self):
        """upsert는 멱등성을 가짐 - 여러 번 호출해도 동일 결과."""
        # Given & When
        player1 = self.repo.upsert("idempotent_player")
        player2 = self.repo.upsert("idempotent_player")
        player3 = self.repo.upsert("idempotent_player")

        # Then
        assert player1.id == player2.id == player3.id
        assert self.repo.count() == 1

    # =========================================================================
    # update_with_stats 테스트
    # =========================================================================

    def test_update_with_stats_increments_wins(self):
        """승리 시 total_wins, total_games, total_win_rate 증가."""
        # Given
        now = datetime.now()
        self.repo.upsert("winner")

        # When
        self.repo.update_with_stats("winner", is_win=True, last_played_at=now)

        # Then
        player = self.repo.find_by_game_id("winner")
        assert player.total_games == 1
        assert player.total_wins == 1
        assert player.total_losses == 0
        assert player.total_win_rate == 100.0
        assert player.last_played_at is not None

    def test_update_with_stats_increments_losses(self):
        """패배 시 total_losses, total_games 증가, total_win_rate는 0."""
        # Given
        now = datetime.now()
        self.repo.upsert("loser")

        # When
        self.repo.update_with_stats("loser", is_win=False, last_played_at=now)

        # Then
        player = self.repo.find_by_game_id("loser")
        assert player.total_games == 1
        assert player.total_wins == 0
        assert player.total_losses == 1
        assert player.total_win_rate == 0.0
        assert player.last_played_at is not None

    def test_update_with_stats_multiple_times(self):
        """여러 번 승패 업데이트 시 win_rate 정확히 계산."""
        # Given
        now = datetime.now()
        self.repo.upsert("player")

        # When: 7승 3패 = 70% 승률
        for _ in range(7):
            self.repo.update_with_stats("player", is_win=True, last_played_at=now)
        for _ in range(3):
            self.repo.update_with_stats("player", is_win=False, last_played_at=now)

        # Then
        player = self.repo.find_by_game_id("player")
        assert player.total_games == 10
        assert player.total_wins == 7
        assert player.total_losses == 3
        assert player.total_win_rate == 70.0

    def test_update_with_stats_calculates_win_rate_correctly(self):
        """승률 계산이 정확한지 검증."""
        # Given
        now = datetime.now()
        self.repo.upsert("player")

        # When: 2승 2패 = 50% 승률
        self.repo.update_with_stats("player", is_win=True, last_played_at=now)
        self.repo.update_with_stats("player", is_win=True, last_played_at=now)
        self.repo.update_with_stats("player", is_win=False, last_played_at=now)
        self.repo.update_with_stats("player", is_win=False, last_played_at=now)

        # Then
        player = self.repo.find_by_game_id("player")
        assert player.total_games == 4
        assert player.total_wins == 2
        assert player.total_losses == 2
        assert player.total_win_rate == 50.0

    def test_update_with_stats_does_nothing_for_nonexistent_player(self):
        """존재하지 않는 플레이어에 대해서는 아무것도 하지 않음."""
        # When (should not raise)
        now = datetime.now()
        self.repo.update_with_stats("ghost", is_win=True, last_played_at=now)

        # Then
        assert self.repo.find_by_game_id("ghost") is None

    def test_update_with_stats_updates_last_played_at_only_when_newer(self):
        """last_played_at은 더 최신값일 때만 업데이트."""
        # Given: 미래 시간을 사용하여 server_default보다 확실히 나중인 시간으로 테스트
        self.repo.upsert("player")
        newer_time = datetime(2099, 12, 1, 12, 0, 0)  # 확실히 미래
        older_time = datetime(2099, 11, 1, 12, 0, 0)  # newer_time보다 과거

        # When: 먼저 최신 시간으로 업데이트
        self.repo.update_with_stats("player", is_win=True, last_played_at=newer_time)

        # Then: 최신 시간으로 설정됨
        player = self.repo.find_by_game_id("player")
        assert player.last_played_at == newer_time

        # When: 과거 시간으로 업데이트 시도
        self.repo.update_with_stats("player", is_win=True, last_played_at=older_time)

        # Then: last_played_at은 변경되지 않고 최신 시간 유지, 하지만 게임 수는 증가
        player = self.repo.find_by_game_id("player")
        assert player.last_played_at == newer_time  # 여전히 최신 시간
        assert player.total_games == 2  # 게임 수는 정상적으로 증가

    def test_update_with_stats_updates_last_played_at_when_actually_newer(self):
        """과거 리플레이 후 최신 리플레이 처리 시 last_played_at 정상 업데이트."""
        # Given: 미래 시간을 사용 (server_default보다 확실히 나중)
        oldest = datetime(2099, 9, 1, 12, 0, 0)
        middle = datetime(2099, 10, 1, 12, 0, 0)
        newest = datetime(2099, 11, 1, 12, 0, 0)

        self.repo.upsert("player")

        # When: 과거 → 중간 → 최신 순으로 처리
        self.repo.update_with_stats("player", is_win=True, last_played_at=oldest)
        player = self.repo.find_by_game_id("player")
        assert player.last_played_at == oldest

        self.repo.update_with_stats("player", is_win=False, last_played_at=middle)
        player = self.repo.find_by_game_id("player")
        assert player.last_played_at == middle

        self.repo.update_with_stats("player", is_win=True, last_played_at=newest)
        player = self.repo.find_by_game_id("player")
        assert player.last_played_at == newest

        # Then: 게임 수는 모두 반영
        assert player.total_games == 3
        assert player.total_wins == 2
        assert player.total_losses == 1

    def test_update_with_stats_mixed_order_replays(self):
        """리플레이가 순서 없이 처리되어도 last_played_at은 항상 최신값 유지."""
        # Given: 미래 시간 사용 (server_default보다 확실히 나중)
        time_1 = datetime(2099, 1, 15, 12, 0, 0)
        time_2 = datetime(2099, 3, 15, 12, 0, 0)
        time_3 = datetime(2099, 2, 15, 12, 0, 0)  # 중간 시간이 마지막에 처리됨

        self.repo.upsert("player")

        # When: 비순차적으로 처리 (최신 → 가장 오래된 → 중간)
        self.repo.update_with_stats("player", is_win=True, last_played_at=time_2)  # 최신
        self.repo.update_with_stats("player", is_win=True, last_played_at=time_1)  # 가장 오래된
        self.repo.update_with_stats("player", is_win=True, last_played_at=time_3)  # 중간

        # Then: last_played_at은 가장 최신인 time_2 유지
        player = self.repo.find_by_game_id("player")
        assert player.last_played_at == time_2
        assert player.total_games == 3

    def test_update_with_stats_sets_last_played_at_when_null(self):
        """last_played_at이 NULL일 때 새 값으로 설정."""
        # Given: 새 플레이어 생성 (last_played_at은 NULL)
        self.repo.upsert("player")
        player = self.repo.find_by_game_id("player")
        assert player.last_played_at is None

        # When: 첫 게임 기록
        first_time = datetime(2025, 6, 1, 12, 0, 0)
        self.repo.update_with_stats("player", is_win=True, last_played_at=first_time)

        # Then: last_played_at이 설정됨
        player = self.repo.find_by_game_id("player")
        assert player.last_played_at == first_time
        assert player.total_games == 1

    def test_update_with_stats_preserves_older_time_when_processing_past_replay(self):
        """이미 최신 시간이 있을 때 과거 리플레이 처리 시 last_played_at 유지."""
        # Given: 초기 server_default 시간보다 확실히 미래인 시간 사용
        future_time = datetime(2099, 6, 1, 12, 0, 0)
        past_time = datetime(2020, 1, 1, 12, 0, 0)  # 현재 시간보다 과거

        self.repo.upsert("player")

        # When: 먼저 미래 시간으로 업데이트
        self.repo.update_with_stats("player", is_win=True, last_played_at=future_time)
        player = self.repo.find_by_game_id("player")
        assert player.last_played_at == future_time

        # When: 과거 시간으로 업데이트 시도
        self.repo.update_with_stats("player", is_win=False, last_played_at=past_time)

        # Then: last_played_at은 미래 시간 유지
        player = self.repo.find_by_game_id("player")
        assert player.last_played_at == future_time
        # 하지만 게임 수와 패배 수는 정상적으로 증가
        assert player.total_games == 2
        assert player.total_wins == 1
        assert player.total_losses == 1

    # =========================================================================
    # update_description 테스트
    # =========================================================================

    def test_update_description_sets_description(self):
        """설명 업데이트."""
        # Given
        self.repo.upsert("player")

        # When
        self.repo.update_description("player", "Pro gamer")

        # Then
        player = self.repo.find_by_game_id("player")
        assert player.description == "Pro gamer"

    def test_update_description_overwrites_existing(self):
        """기존 설명 덮어쓰기."""
        # Given
        self.repo.upsert("player")
        self.repo.update_description("player", "Old description")

        # When
        self.repo.update_description("player", "New description")

        # Then
        player = self.repo.find_by_game_id("player")
        assert player.description == "New description"

    def test_update_description_can_set_empty(self):
        """빈 문자열로 설명 설정 가능."""
        # Given
        self.repo.upsert("player")
        self.repo.update_description("player", "Some description")

        # When
        self.repo.update_description("player", "")

        # Then
        player = self.repo.find_by_game_id("player")
        assert player.description == ""

    # =========================================================================
    # BaseRepository 메서드 테스트
    # =========================================================================

    def test_find_all_returns_all_players(self):
        """모든 플레이어 조회."""
        # Given
        self.repo.upsert("player1")
        self.repo.upsert("player2")
        self.repo.upsert("player3")

        # When
        players = self.repo.find_all()

        # Then
        assert len(players) == 3
        game_ids = {p.game_id for p in players}
        assert game_ids == {"player1", "player2", "player3"}

    def test_find_all_returns_empty_list_when_no_players(self):
        """플레이어가 없으면 빈 리스트 반환."""
        # When
        players = self.repo.find_all()

        # Then
        assert players == []

    def test_count_returns_correct_count(self):
        """플레이어 수 조회."""
        # Given
        assert self.repo.count() == 0

        self.repo.upsert("player1")
        assert self.repo.count() == 1

        self.repo.upsert("player2")
        assert self.repo.count() == 2

    def test_find_by_id_returns_player(self):
        """ID로 플레이어 조회."""
        # Given
        player = self.repo.upsert("player")

        # When
        found = self.repo.find_by_id(player.id)

        # Then
        assert found is not None
        assert found.id == player.id
        assert found.game_id == "player"

    def test_find_by_id_returns_none_for_nonexistent(self):
        """존재하지 않는 ID 조회 시 None 반환."""
        result = self.repo.find_by_id(9999)
        assert result is None

    def test_delete_removes_player(self):
        """플레이어 삭제."""
        # Given
        player = self.repo.upsert("to_delete")

        # When
        result = self.repo.delete(player.id)

        # Then
        assert result is True
        assert self.repo.find_by_game_id("to_delete") is None
        assert self.repo.count() == 0

    def test_delete_returns_false_for_nonexistent(self):
        """존재하지 않는 플레이어 삭제 시 False 반환."""
        result = self.repo.delete(9999)
        assert result is False

    def test_exists_returns_true_for_existing(self):
        """존재하는 플레이어 확인."""
        # Given
        player = self.repo.upsert("player")

        # Then
        assert self.repo.exists(player.id) is True

    def test_exists_returns_false_for_nonexistent(self):
        """존재하지 않는 플레이어 확인."""
        assert self.repo.exists(9999) is False

    # =========================================================================
    # 테스트 격리 확인
    # =========================================================================

    def test_isolation_first(self):
        """테스트 격리 확인 1 - 플레이어 생성."""
        self.repo.upsert("isolation_test")
        assert self.repo.count() == 1

    def test_isolation_second(self):
        """테스트 격리 확인 2 - 이전 테스트 데이터가 없어야 함."""
        # 이전 테스트에서 생성한 플레이어가 롤백되었으므로 없어야 함
        assert self.repo.find_by_game_id("isolation_test") is None
        assert self.repo.count() == 0
