import time
from pathlib import Path

from PySide6.QtCore import QObject, Signal
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from common.event_bus import EventBus
from common.uow.replay_watch import replay_watch_uow

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

    def on_modified(self, event):
        if event.is_directory:
            return
        if Path(event.src_path) == self._target_file:
            self._handle_event()

    def on_created(self, event):
        if event.is_directory:
            return
        if Path(event.src_path) == self._target_file:
            self._handle_event()

    def _handle_event(self):
        """Handle file event with debouncing."""
        current_time = time.time()
        if current_time - self._last_modified < self._debounce_seconds:
            return
        self._last_modified = current_time
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

        # Connect signal to handler (ensures main thread execution)
        self._replay_file_changed.connect(self._on_last_replay_file_changed)

    def start(self):
        """Start watching for replay file changes."""
        replay_file = self.app_config.replay_file
        watch_dir = replay_file.parent

        if not watch_dir.exists():
            print(f"[ReplayWatchService] Watch directory does not exist: {watch_dir}")
            return

        handler = ReplayFileHandler(
            target_file=replay_file,
            callback=self._replay_file_changed.emit
        )

        self._observer = Observer()
        self._observer.schedule(handler, str(watch_dir), recursive=False)
        self._observer.start()
        print(f"[ReplayWatchService] Started watching: {replay_file}")

    def stop(self):
        """Stop watching for file changes."""
        if self._observer:
            self._observer.stop()
            self._observer.join(timeout=5)
            self._observer = None
            print("[ReplayWatchService] Stopped watching")

    def analyze_replay_and_upsert(self, replay_file: Path) -> MatchHistoryDTO | None:
        with replay_watch_uow() as uow:
            analysis_info: ReplayAnalysisDTO | None = uow.replay_service.analyze_replay(replay_file, self.app_config.player_id)
            if analysis_info is None:
                print(f"[ReplayWatchService] Failed to analyze replay: {replay_file}")
                return None

            opponent_player: Player | None = uow.players.upsert(analysis_info.opponent_id)
            if opponent_player is None:
                print(f"[ReplayWatchService] Failed to upsert opponent player: {analysis_info.opponent_id}")
                return None
            res = uow.players.update_with_stats(analysis_info.opponent_id, analysis_info.is_win, analysis_info.played_at)
            if res == 0:
                print(f"[ReplayWatchService] Failed to update with stats: {analysis_info.opponent_id} {analysis_info.is_win} {analysis_info.played_at}")
                return None

            game_map: Map | None = uow.maps.upsert(analysis_info.map_name)
            if game_map is None:
                print(f"[ReplayWatchService] Failed to upsert game map: {analysis_info.map_name}")
                return None

            stat_res: int = uow.stats.upsert(analysis_info.opponent_id, analysis_info.map_name, analysis_info.is_win)
            if stat_res == 0:
                print(f"[ReplayWatchService] Failed to upsert stat: {analysis_info.opponent_id} {analysis_info.map_name} {analysis_info.is_win}")
                return None

            match_history: MatchHistory | None = uow.match_histories.insert(
                MatchHistory(
                    player_id=opponent_player.id,
                    opponent_id=analysis_info.opponent_id,
                    race=analysis_info.race,
                    map_id=game_map.id,
                    map_name=analysis_info.map_name,
                    is_win=analysis_info.is_win,
                    playtime=analysis_info.playtime,
                    played_at=analysis_info.played_at
                )
            )
            if match_history is None:
                print(f"[ReplayWatchService] Failed to insert match history: {analysis_info.opponent_id} {analysis_info.map_name} {analysis_info.is_win} {analysis_info.playtime} {analysis_info.played_at}")
                return None

            return MatchHistoryDTO(
                opponent_id=analysis_info.opponent_id,
                race=analysis_info.race,
                map_name=analysis_info.map_name,
                is_win=analysis_info.is_win,
                playtime=analysis_info.playtime,
                played_at=analysis_info.played_at
            )

    def _on_last_replay_file_changed(self):
        last_replay_file = self.app_config.replay_file
        if not last_replay_file.exists():
            print(f"[ReplayWatchService] {last_replay_file} not found")
            return

        match_history = self.analyze_replay_and_upsert(last_replay_file)
        if match_history is None:
            print(f"[ReplayWatchService] Failed to analyze replay: {last_replay_file}")
            return

        # Emit event to update the UI
        self.event_bus.replay_added.emit(match_history)
