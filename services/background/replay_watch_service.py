import time
from pathlib import Path

from PySide6.QtCore import QObject, Signal
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from common.event_bus import EventBus
from common.uow.replay_watch import replay_watch_uow
from common.const import TypeErrorCode
from common.exceptions import ReplayAnalysisError
from common.logger import get_logger

from models.player import Player
from models.map import Map
from models.match_history import MatchHistory
from dto.replay import ReplayAnalysisDTO
from dto.match_history import MatchHistoryDTO

from config.app_config import AppConfig


class ReplayFileHandler(FileSystemEventHandler):
    """Handler for replay file system events."""

    def __init__(self, target_file: Path, callback):
        super().__init__()
        self._target_file = target_file
        self._callback = callback
        self._last_modified = 0
        self._debounce_seconds = 1.0  # 디바운싱: 1초 내 중복 이벤트 무시
        self._logger = get_logger("replay_file_handler")

    def on_any_event(self, event):
        """Log all events for debugging."""
        self._logger.debug(f"File event: {event.event_type} - {event.src_path}")

    def on_modified(self, event):
        if event.is_directory:
            return
        event_path = Path(event.src_path)
        self._logger.debug(f"Modified event: {event_path} (target: {self._target_file})")
        if event_path == self._target_file:
            self._handle_event()

    def on_created(self, event):
        if event.is_directory:
            return
        event_path = Path(event.src_path)
        self._logger.debug(f"Created event: {event_path} (target: {self._target_file})")
        if event_path == self._target_file:
            self._handle_event()

    def _handle_event(self):
        """Handle file event with debouncing."""
        current_time = time.time()
        if current_time - self._last_modified < self._debounce_seconds:
            self._logger.debug("Event debounced (within 1 second)")
            return
        self._last_modified = current_time
        self._logger.info(f"Processing file change: {self._target_file}")
        self._callback()


class ReplayWatchService(QObject):
    """Service for watching replay file changes using watchdog."""

    # Signal to safely invoke callback on Qt main thread
    _replay_file_changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.app_config = AppConfig.get_instance()
        self.event_bus = EventBus.instance()
        self._observer: Observer | None = None
        self.logger = get_logger("replay_watch_service")

        # Connect signal to handler (ensures main thread execution)
        self._replay_file_changed.connect(self._on_last_replay_file_changed)

    def start(self):
        """Start watching for replay file changes."""
        # Reload config to get latest settings
        self.app_config = AppConfig.get_instance()

        # Check if config is valid before starting
        if not self.app_config.is_valid():
            self.logger.warning("Config is not valid. Skipping file watcher start.")
            self.logger.warning(f"  player_id: '{self.app_config.player_id}'")
            self.logger.warning(f"  replay_dir: '{self.app_config.replay_dir}'")
            return

        replay_file = self.app_config.replay_file
        watch_dir = replay_file.parent

        self.logger.info(f"Attempting to start file watcher for: {replay_file}")
        self.logger.info(f"Watch directory: {watch_dir}")

        if not watch_dir.exists():
            self.logger.warning(f"Watch directory does not exist: {watch_dir}")
            return

        try:
            handler = ReplayFileHandler(
                target_file=replay_file,
                callback=self._replay_file_changed.emit
            )

            self._observer = Observer()
            self.logger.info(f"Observer type: {type(self._observer).__name__}")

            self._observer.schedule(handler, str(watch_dir), recursive=False)
            self._observer.start()

            # Verify observer is actually running
            if self._observer.is_alive():
                self.logger.info(f"Started watching successfully: {replay_file}")
            else:
                self.logger.error("Observer failed to start - thread not alive")
        except Exception as e:
            self.logger.error(f"Failed to start file watcher: {e}", exc_info=True)

    def stop(self):
        """Stop watching for file changes."""
        if self._observer:
            self._observer.stop()
            self._observer.join(timeout=5)
            self._observer = None
            self.logger.info("Stopped watching")

    def restart(self):
        """Restart the file watcher with updated config."""
        self.logger.info("Restarting file watcher...")
        self.stop()
        # Reload config to pick up new settings
        self.app_config = AppConfig.reload()
        self.start()

    def analyze_replay_and_upsert(self, replay_file: Path) -> MatchHistoryDTO:
        with replay_watch_uow() as uow:
            analysis_info: ReplayAnalysisDTO = uow.replay_service.analyze_replay(replay_file, self.app_config.player_id)

            opponent_player: Player | None = uow.players.upsert(analysis_info.opponent_id)
            if opponent_player is None:
                self.logger.error(f"Failed to upsert opponent player: {analysis_info.opponent_id}")
                raise ReplayAnalysisError(TypeErrorCode.PLAYER_UPSERT_FAILED, analysis_info.opponent_id)

            res = uow.players.update_with_stats(analysis_info.opponent_id, analysis_info.is_win, analysis_info.played_at)
            if res == 0:
                self.logger.error(f"Failed to update with stats: {analysis_info.opponent_id}")
                raise ReplayAnalysisError(TypeErrorCode.PLAYER_UPDATE_FAILED, analysis_info.opponent_id)

            game_map: Map | None = uow.maps.upsert(analysis_info.map_name)
            if game_map is None:
                self.logger.error(f"Failed to upsert game map: {analysis_info.map_name}")
                raise ReplayAnalysisError(TypeErrorCode.MAP_UPSERT_FAILED, analysis_info.map_name)

            stat_res: int = uow.stats.upsert(analysis_info.opponent_id, analysis_info.map_name, analysis_info.is_win)
            if stat_res == 0:
                self.logger.error(f"Failed to upsert stat: {analysis_info.opponent_id} {analysis_info.map_name}")
                raise ReplayAnalysisError(TypeErrorCode.STAT_UPSERT_FAILED, f"{analysis_info.opponent_id} / {analysis_info.map_name}")

            match_history: MatchHistory | None = uow.match_histories.insert(
                MatchHistory(
                    player_id=opponent_player.id,
                    opponent_id=analysis_info.opponent_id,
                    race=analysis_info.race,
                    map_id=game_map.id,
                    map_name=analysis_info.map_name,
                    apm=analysis_info.apm,
                    eapm=analysis_info.eapm,
                    is_win=analysis_info.is_win,
                    playtime=analysis_info.playtime,
                    played_at=analysis_info.played_at
                )
            )
            if match_history is None:
                self.logger.warning(f"Duplicate match history: {analysis_info.opponent_id} {analysis_info.played_at}")
                raise ReplayAnalysisError(TypeErrorCode.DUPLICATE, f"{analysis_info.opponent_id}")

            return MatchHistoryDTO(
                opponent_id=analysis_info.opponent_id,
                race=analysis_info.race,
                map_name=analysis_info.map_name,
                apm=analysis_info.apm,
                eapm=analysis_info.eapm,
                is_win=analysis_info.is_win,
                playtime=analysis_info.playtime,
                played_at=analysis_info.played_at
            )

    def _on_last_replay_file_changed(self):
        last_replay_file = self.app_config.replay_file
        if not last_replay_file.exists():
            self.logger.warning(f"{last_replay_file} not found")
            return

        try:
            match_history = self.analyze_replay_and_upsert(last_replay_file)
        except Exception as e:
            self.logger.error(f"Failed to analyze replay: {last_replay_file} {e}")
            self.event_bus.replay_processing_error.emit(f"{last_replay_file}: {e}")
            return
        finally:
            # LastReplay.rep 처리 후 패킷 감시 다시 시작
            self.event_bus.start_packet_monitoring.emit()

        # Emit event to update the UI
        self.event_bus.replay_added.emit(match_history)
