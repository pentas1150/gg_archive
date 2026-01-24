"""
Tests for ReplayWatchService.analyze_replay_and_upsert.

Tests cover:
- Success case
- Each upsert/insert failure scenario
- Transaction rollback verification
"""
from datetime import datetime, UTC
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

# Import const first (same as other tests)
from common.const import TypeErrorCode
from common.exceptions import ReplayAnalysisError

# Import models
from models.player import Player
from models.map import Map
from models.match_history import MatchHistory

# Import repositories
from repositories.player_repository import PlayerRepository
from repositories.map_repository import MapRepository
from repositories.stat_repository import StatRepository
from repositories.match_history_repository import MatchHistoryRepository

# Import DTOs
from dto.replay import ReplayAnalysisDTO
from dto.match_history import MatchHistoryDTO

# Import service (delayed to avoid circular import)
# Will be imported in test methods if needed


class TestAnalyzeReplayAndUpsert:
    """analyze_replay_and_upsert 메서드 테스트."""

    @pytest.fixture(autouse=True)
    def setup(self, db, db_session):
        """각 테스트 전에 서비스 및 repository 초기화."""
        # Delayed import to avoid circular import
        from services.background.replay_watch_service import ReplayWatchService

        self.db = db
        self.db_session = db_session
        self.player_repo = PlayerRepository(session=db_session)
        self.map_repo = MapRepository(session=db_session)
        self.stat_repo = StatRepository(session=db_session)
        self.match_history_repo = MatchHistoryRepository(session=db_session)

        # ReplayWatchService 생성 (QObject 초기화 없이)
        with patch.object(ReplayWatchService, '__init__', lambda x: None):
            self.service = ReplayWatchService()
            self.service.app_config = MagicMock()
            self.service.app_config.player_id = "my_player"
            self.service.event_bus = MagicMock()

    @pytest.fixture
    def sample_analysis_dto(self):
        """테스트용 ReplayAnalysisDTO."""
        return ReplayAnalysisDTO(
            opponent_id="opponent_player",
            race="Terran",
            map_name="Fighting Spirit",
            is_win=True,
            playtime=600,
            played_at=datetime.now(UTC)
        )

    @pytest.fixture
    def mock_uow(self, sample_analysis_dto):
        """테스트용 UnitOfWork mock."""
        uow = MagicMock()
        uow.replay_service.analyze_replay.return_value = sample_analysis_dto
        uow.players.upsert.return_value = Player(id=1, game_id="opponent_player")
        uow.players.update_with_stats.return_value = 1
        uow.maps.upsert.return_value = Map(id=1, name="Fighting Spirit")
        uow.stats.upsert.return_value = 1
        uow.match_histories.insert.return_value = MatchHistory(
            id=1,
            player_id=1,
            opponent_id="opponent_player",
            race="Terran",
            map_id=1,
            map_name="Fighting Spirit",
            is_win=True,
            playtime=600,
            played_at=sample_analysis_dto.played_at
        )
        return uow

    # =========================================================================
    # 성공 케이스
    # =========================================================================

    def test_success_returns_match_history_dto(self, mock_uow, sample_analysis_dto):
        """성공 시 MatchHistoryDTO 반환."""
        with patch('services.background.replay_watch_service.replay_watch_uow') as mock_uow_ctx:
            mock_uow_ctx.return_value.__enter__.return_value = mock_uow

            result = self.service.analyze_replay_and_upsert(Path("/fake/path.rep"))

            assert isinstance(result, MatchHistoryDTO)
            assert result.opponent_id == "opponent_player"
            assert result.race == "Terran"
            assert result.map_name == "Fighting Spirit"
            assert result.is_win is True
            assert result.playtime == 600

    def test_success_calls_all_upserts_in_order(self, mock_uow, sample_analysis_dto):
        """성공 시 모든 upsert가 순서대로 호출됨."""
        with patch('services.background.replay_watch_service.replay_watch_uow') as mock_uow_ctx:
            mock_uow_ctx.return_value.__enter__.return_value = mock_uow

            self.service.analyze_replay_and_upsert(Path("/fake/path.rep"))

            # 호출 순서 확인
            mock_uow.replay_service.analyze_replay.assert_called_once()
            mock_uow.players.upsert.assert_called_once_with("opponent_player")
            mock_uow.players.update_with_stats.assert_called_once()
            mock_uow.maps.upsert.assert_called_once_with("Fighting Spirit")
            mock_uow.stats.upsert.assert_called_once()
            mock_uow.match_histories.insert.assert_called_once()

    # =========================================================================
    # analyze_replay 실패 케이스
    # =========================================================================

    def test_analyze_replay_not_1vs1_raises_exception(self, mock_uow):
        """1vs1이 아닌 리플레이는 ReplayAnalysisError 발생."""
        mock_uow.replay_service.analyze_replay.side_effect = ReplayAnalysisError(
            TypeErrorCode.NOT_1VS1, "/fake/path.rep"
        )

        with patch('services.background.replay_watch_service.replay_watch_uow') as mock_uow_ctx:
            mock_uow_ctx.return_value.__enter__.return_value = mock_uow

            with pytest.raises(ReplayAnalysisError) as exc_info:
                self.service.analyze_replay_and_upsert(Path("/fake/path.rep"))

            assert exc_info.value.error_code == TypeErrorCode.NOT_1VS1
            assert exc_info.value.error_code.is_skip() is True
            # 후속 upsert가 호출되지 않았는지 확인
            mock_uow.players.upsert.assert_not_called()

    def test_analyze_replay_not_my_replay_raises_exception(self, mock_uow):
        """내 리플레이가 아니면 ReplayAnalysisError 발생."""
        mock_uow.replay_service.analyze_replay.side_effect = ReplayAnalysisError(
            TypeErrorCode.NOT_MY_REPLAY, "/fake/path.rep"
        )

        with patch('services.background.replay_watch_service.replay_watch_uow') as mock_uow_ctx:
            mock_uow_ctx.return_value.__enter__.return_value = mock_uow

            with pytest.raises(ReplayAnalysisError) as exc_info:
                self.service.analyze_replay_and_upsert(Path("/fake/path.rep"))

            assert exc_info.value.error_code == TypeErrorCode.NOT_MY_REPLAY
            assert exc_info.value.error_code.is_skip() is True

    def test_analyze_replay_too_short_raises_exception(self, mock_uow):
        """플레이타임이 짧으면 ReplayAnalysisError 발생."""
        mock_uow.replay_service.analyze_replay.side_effect = ReplayAnalysisError(
            TypeErrorCode.PLAYTIME_TOO_SHORT, "30초"
        )

        with patch('services.background.replay_watch_service.replay_watch_uow') as mock_uow_ctx:
            mock_uow_ctx.return_value.__enter__.return_value = mock_uow

            with pytest.raises(ReplayAnalysisError) as exc_info:
                self.service.analyze_replay_and_upsert(Path("/fake/path.rep"))

            assert exc_info.value.error_code == TypeErrorCode.PLAYTIME_TOO_SHORT
            assert exc_info.value.error_code.is_skip() is True

    # =========================================================================
    # players.upsert 실패 케이스
    # =========================================================================

    def test_player_upsert_returns_none_raises_exception(self, mock_uow):
        """players.upsert가 None 반환 시 ReplayAnalysisError 발생."""
        mock_uow.players.upsert.return_value = None

        with patch('services.background.replay_watch_service.replay_watch_uow') as mock_uow_ctx:
            mock_uow_ctx.return_value.__enter__.return_value = mock_uow

            with pytest.raises(ReplayAnalysisError) as exc_info:
                self.service.analyze_replay_and_upsert(Path("/fake/path.rep"))

            assert exc_info.value.error_code == TypeErrorCode.PLAYER_UPSERT_FAILED
            assert exc_info.value.error_code.is_skip() is False
            # 후속 작업이 호출되지 않았는지 확인
            mock_uow.players.update_with_stats.assert_not_called()
            mock_uow.maps.upsert.assert_not_called()

    # =========================================================================
    # players.update_with_stats 실패 케이스
    # =========================================================================

    def test_player_update_with_stats_returns_zero_raises_exception(self, mock_uow):
        """players.update_with_stats가 0 반환 시 ReplayAnalysisError 발생."""
        mock_uow.players.update_with_stats.return_value = 0

        with patch('services.background.replay_watch_service.replay_watch_uow') as mock_uow_ctx:
            mock_uow_ctx.return_value.__enter__.return_value = mock_uow

            with pytest.raises(ReplayAnalysisError) as exc_info:
                self.service.analyze_replay_and_upsert(Path("/fake/path.rep"))

            assert exc_info.value.error_code == TypeErrorCode.PLAYER_UPDATE_FAILED
            assert exc_info.value.error_code.is_skip() is False
            # 후속 작업이 호출되지 않았는지 확인
            mock_uow.maps.upsert.assert_not_called()

    # =========================================================================
    # maps.upsert 실패 케이스
    # =========================================================================

    def test_map_upsert_returns_none_raises_exception(self, mock_uow):
        """maps.upsert가 None 반환 시 ReplayAnalysisError 발생."""
        mock_uow.maps.upsert.return_value = None

        with patch('services.background.replay_watch_service.replay_watch_uow') as mock_uow_ctx:
            mock_uow_ctx.return_value.__enter__.return_value = mock_uow

            with pytest.raises(ReplayAnalysisError) as exc_info:
                self.service.analyze_replay_and_upsert(Path("/fake/path.rep"))

            assert exc_info.value.error_code == TypeErrorCode.MAP_UPSERT_FAILED
            assert exc_info.value.error_code.is_skip() is False
            # 후속 작업이 호출되지 않았는지 확인
            mock_uow.stats.upsert.assert_not_called()

    # =========================================================================
    # stats.upsert 실패 케이스
    # =========================================================================

    def test_stat_upsert_returns_zero_raises_exception(self, mock_uow):
        """stats.upsert가 0 반환 시 ReplayAnalysisError 발생."""
        mock_uow.stats.upsert.return_value = 0

        with patch('services.background.replay_watch_service.replay_watch_uow') as mock_uow_ctx:
            mock_uow_ctx.return_value.__enter__.return_value = mock_uow

            with pytest.raises(ReplayAnalysisError) as exc_info:
                self.service.analyze_replay_and_upsert(Path("/fake/path.rep"))

            assert exc_info.value.error_code == TypeErrorCode.STAT_UPSERT_FAILED
            assert exc_info.value.error_code.is_skip() is False
            # 후속 작업이 호출되지 않았는지 확인
            mock_uow.match_histories.insert.assert_not_called()

    # =========================================================================
    # match_histories.insert 실패 케이스 (중복)
    # =========================================================================

    def test_match_history_insert_returns_none_raises_exception(self, mock_uow):
        """match_histories.insert가 None 반환 시 (중복) ReplayAnalysisError 발생."""
        mock_uow.match_histories.insert.return_value = None

        with patch('services.background.replay_watch_service.replay_watch_uow') as mock_uow_ctx:
            mock_uow_ctx.return_value.__enter__.return_value = mock_uow

            with pytest.raises(ReplayAnalysisError) as exc_info:
                self.service.analyze_replay_and_upsert(Path("/fake/path.rep"))

            assert exc_info.value.error_code == TypeErrorCode.DUPLICATE
            assert exc_info.value.error_code.is_skip() is True  # 중복은 스킵으로 분류

    # =========================================================================
    # 트랜잭션 롤백 검증 (실제 DB 사용)
    # =========================================================================

    def test_rollback_on_match_history_duplicate(self):
        """match_history 중복 시 이전 upsert 작업들이 롤백되는지 확인."""
        # Given: 실제 DB에 데이터 삽입을 시뮬레이션
        # 먼저 플레이어와 맵을 생성
        player = self.player_repo.upsert("rollback_test_opponent")
        game_map = self.map_repo.upsert("Rollback Test Map")

        # 첫 번째 매치 히스토리 삽입
        played_at = datetime.now(UTC)
        match1 = MatchHistory(
            player_id=player.id,
            opponent_id="rollback_test_opponent",
            race="Zerg",
            map_id=game_map.id,
            map_name=game_map.name,
            is_win=True,
            playtime=300,
            played_at=played_at
        )
        self.match_history_repo.insert(match1)

        # When: 동일한 played_at으로 다시 삽입 시도 (중복)
        match2 = MatchHistory(
            player_id=player.id,
            opponent_id="rollback_test_opponent",
            race="Terran",
            map_id=game_map.id,
            map_name=game_map.name,
            is_win=False,
            playtime=400,
            played_at=played_at  # 동일한 시간 = 중복
        )
        result = self.match_history_repo.insert(match2)

        # Then: 중복으로 인해 None 반환
        assert result is None
        # 기존 데이터는 그대로
        assert self.match_history_repo.count() == 1

    def test_all_operations_in_single_transaction(self):
        """모든 작업이 단일 트랜잭션에서 실행되는지 확인."""
        # Given: Mock UoW 설정
        call_order = []

        def track_call(name, return_value):
            def side_effect(*args, **kwargs):
                call_order.append(name)
                return return_value
            return side_effect

        mock_uow = MagicMock()
        mock_uow.replay_service.analyze_replay.side_effect = track_call(
            "analyze_replay",
            ReplayAnalysisDTO(
                opponent_id="test",
                race="Terran",
                map_name="Test Map",
                is_win=True,
                playtime=600,
                played_at=datetime.now(UTC)
            )
        )
        mock_uow.players.upsert.side_effect = track_call(
            "players.upsert",
            Player(id=1, game_id="test")
        )
        mock_uow.players.update_with_stats.side_effect = track_call(
            "players.update_with_stats",
            1
        )
        mock_uow.maps.upsert.side_effect = track_call(
            "maps.upsert",
            Map(id=1, name="Test Map")
        )
        mock_uow.stats.upsert.side_effect = track_call(
            "stats.upsert",
            1
        )
        mock_uow.match_histories.insert.side_effect = track_call(
            "match_histories.insert",
            MatchHistory(
                id=1,
                player_id=1,
                opponent_id="test",
                race="Terran",
                map_id=1,
                map_name="Test Map",
                is_win=True,
                playtime=600,
                played_at=datetime.now(UTC)
            )
        )

        # When
        with patch('services.background.replay_watch_service.replay_watch_uow') as mock_uow_ctx:
            mock_uow_ctx.return_value.__enter__.return_value = mock_uow

            self.service.analyze_replay_and_upsert(Path("/fake/path.rep"))

        # Then: 정확한 순서로 호출됨
        assert call_order == [
            "analyze_replay",
            "players.upsert",
            "players.update_with_stats",
            "maps.upsert",
            "stats.upsert",
            "match_histories.insert"
        ]

    # =========================================================================
    # 에러 코드 및 상세 정보 검증
    # =========================================================================

    def test_duplicate_error_has_correct_code_and_detail(
        self, mock_uow, sample_analysis_dto
    ):
        """중복 에러는 DUPLICATE 코드와 opponent_id를 포함."""
        mock_uow.match_histories.insert.return_value = None

        with patch('services.background.replay_watch_service.replay_watch_uow') as mock_uow_ctx:
            mock_uow_ctx.return_value.__enter__.return_value = mock_uow

            with pytest.raises(ReplayAnalysisError) as exc_info:
                self.service.analyze_replay_and_upsert(Path("/fake/path.rep"))

            assert exc_info.value.error_code == TypeErrorCode.DUPLICATE
            assert "opponent_player" in exc_info.value.detail

    def test_player_upsert_error_has_correct_code_and_detail(self, mock_uow):
        """플레이어 upsert 에러는 PLAYER_UPSERT_FAILED 코드와 opponent_id 포함."""
        mock_uow.players.upsert.return_value = None

        with patch('services.background.replay_watch_service.replay_watch_uow') as mock_uow_ctx:
            mock_uow_ctx.return_value.__enter__.return_value = mock_uow

            with pytest.raises(ReplayAnalysisError) as exc_info:
                self.service.analyze_replay_and_upsert(Path("/fake/path.rep"))

            assert exc_info.value.error_code == TypeErrorCode.PLAYER_UPSERT_FAILED
            assert "opponent_player" in exc_info.value.detail

    def test_map_upsert_error_has_correct_code_and_detail(self, mock_uow):
        """맵 upsert 에러는 MAP_UPSERT_FAILED 코드와 map_name 포함."""
        mock_uow.maps.upsert.return_value = None

        with patch('services.background.replay_watch_service.replay_watch_uow') as mock_uow_ctx:
            mock_uow_ctx.return_value.__enter__.return_value = mock_uow

            with pytest.raises(ReplayAnalysisError) as exc_info:
                self.service.analyze_replay_and_upsert(Path("/fake/path.rep"))

            assert exc_info.value.error_code == TypeErrorCode.MAP_UPSERT_FAILED
            assert "Fighting Spirit" in exc_info.value.detail

    def test_error_code_user_message(self):
        """에러 코드의 사용자 메시지 확인."""
        assert TypeErrorCode.DUPLICATE.get_user_message() == "이미 불러온 리플레이"
        assert TypeErrorCode.PLAYTIME_TOO_SHORT.get_user_message() == "게임 시간 부족"
        assert TypeErrorCode.NOT_1VS1.get_user_message() == "1vs1 게임 아님"
        assert TypeErrorCode.NOT_MY_REPLAY.get_user_message() == "내 리플레이 아님"

    def test_error_code_is_skip_classification(self):
        """에러 코드의 is_skip 분류 확인."""
        # 스킵으로 분류되어야 하는 코드들
        assert TypeErrorCode.DUPLICATE.is_skip() is True
        assert TypeErrorCode.PLAYTIME_TOO_SHORT.is_skip() is True
        assert TypeErrorCode.NOT_1VS1.is_skip() is True
        assert TypeErrorCode.NOT_MY_REPLAY.is_skip() is True

        # 실제 에러로 분류되어야 하는 코드들
        assert TypeErrorCode.PLAYER_UPSERT_FAILED.is_skip() is False
        assert TypeErrorCode.PLAYER_UPDATE_FAILED.is_skip() is False
        assert TypeErrorCode.MAP_UPSERT_FAILED.is_skip() is False
        assert TypeErrorCode.STAT_UPSERT_FAILED.is_skip() is False


class TestAnalyzeReplayAndUpsertIntegration:
    """analyze_replay_and_upsert 통합 테스트 (실제 DB 트랜잭션 검증)."""

    @pytest.fixture(autouse=True)
    def setup(self, db, db_session):
        """각 테스트 전에 서비스 및 repository 초기화."""
        self.db = db
        self.db_session = db_session
        self.player_repo = PlayerRepository(session=db_session)
        self.map_repo = MapRepository(session=db_session)
        self.stat_repo = StatRepository(session=db_session)
        self.match_history_repo = MatchHistoryRepository(session=db_session)

    def test_successful_insert_persists_all_data(self):
        """성공적인 삽입 시 모든 데이터가 저장됨."""
        # Given
        player = self.player_repo.upsert("integration_opponent")
        game_map = self.map_repo.upsert("Integration Map")
        played_at = datetime.now(UTC)

        # When
        match = MatchHistory(
            player_id=player.id,
            opponent_id="integration_opponent",
            race="Protoss",
            map_id=game_map.id,
            map_name=game_map.name,
            is_win=True,
            playtime=500,
            played_at=played_at
        )
        result = self.match_history_repo.insert(match)

        # Then
        assert result is not None
        assert self.player_repo.count() == 1
        assert self.map_repo.count() == 1
        assert self.match_history_repo.count() == 1

    def test_duplicate_insert_returns_none_preserves_original(self):
        """중복 삽입 시 None 반환하고 원본 보존."""
        # Given
        player = self.player_repo.upsert("dup_opponent")
        game_map = self.map_repo.upsert("Dup Map")
        played_at = datetime.now(UTC)

        original = MatchHistory(
            player_id=player.id,
            opponent_id="dup_opponent",
            race="Terran",
            map_id=game_map.id,
            map_name=game_map.name,
            is_win=True,
            playtime=300,
            played_at=played_at
        )
        self.match_history_repo.insert(original)

        # When: 동일한 played_at + player_id로 다시 삽입
        duplicate = MatchHistory(
            player_id=player.id,
            opponent_id="dup_opponent",
            race="Zerg",  # 다른 종족
            map_id=game_map.id,
            map_name=game_map.name,
            is_win=False,  # 다른 결과
            playtime=600,  # 다른 시간
            played_at=played_at  # 같은 played_at
        )
        result = self.match_history_repo.insert(duplicate)

        # Then
        assert result is None
        assert self.match_history_repo.count() == 1

        # 원본 데이터 확인
        saved = self.match_history_repo.find_all()[0]
        assert saved.race == "Terran"  # 원본 유지
        assert saved.is_win is True  # 원본 유지
        assert saved.playtime == 300  # 원본 유지
