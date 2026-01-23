"""
All Stats Widget - displays player statistics table.
"""
from datetime import UTC
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QAbstractItemView,
)
from PySide6.QtCore import Signal, Qt

from common.const import TypeOrderColumn, TypeOrderDirection
from common.event_bus import EventBus

from models.player import Player
from services.player_service import PlayerService
from dto.match_history import MatchHistoryDTO
from config.app_config import AppConfig


# Column index to TypeOrderColumn mapping
COLUMN_TO_ORDER = {
    0: TypeOrderColumn.GAME_ID,
    1: TypeOrderColumn.TOTAL_GAMES,
    2: TypeOrderColumn.TOTAL_WINS,
    3: TypeOrderColumn.TOTAL_LOSSES,
    4: TypeOrderColumn.TOTAL_WIN_RATE,
    5: TypeOrderColumn.LAST_PLAYED_AT,
}


class NumericTableWidgetItem(QTableWidgetItem):
    """Table item that sorts numerically instead of alphabetically."""

    def __init__(self, value, display_text: str = None):
        super().__init__(display_text if display_text else str(value))
        self._sort_value = value

    def __lt__(self, other):
        if isinstance(other, NumericTableWidgetItem):
            return self._sort_value < other._sort_value
        return super().__lt__(other)


class AllStatsWidget(QWidget):
    """Widget displaying all player statistics in a table."""

    player_selected = Signal(Player)  # Emitted when a player row is clicked

    def __init__(self, player_service: PlayerService, parent=None):
        super().__init__(parent)
        self._config: AppConfig = AppConfig.get_instance()
        self._player_service: PlayerService = player_service
        self._players: list[Player] = []
        self._search_game_id: str = ""
        self._order_column: TypeOrderColumn = TypeOrderColumn.LAST_PLAYED_AT
        self._order_direction: TypeOrderDirection = TypeOrderDirection.DESC
        self._setup_ui()
        self._subscribe_events()

    def _setup_ui(self):
        """Load player data and setup the UI."""
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(24, 24, 24, 24)

        # Header with title and search
        header_layout = QHBoxLayout()

        # Title
        title = QLabel("All Stats")
        title.setStyleSheet("""
            QLabel {
                font-size: 20px;
                font-weight: bold;
                color: #2c3e50;
            }
        """)
        header_layout.addWidget(title)
        header_layout.addStretch()

        # Search box
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Player ID 검색...")
        self.search_input.setFixedWidth(200)
        self.search_input.setStyleSheet("""
            QLineEdit {
                font-size: 12px;
                padding: 6px 10px;
                border: 1px solid #bdc3c7;
                border-radius: 4px;
                background: white;
                color: #2c3e50;
            }
            QLineEdit:focus {
                border: 1px solid #3498db;
            }
        """)
        self.search_input.returnPressed.connect(self._on_search)
        header_layout.addWidget(self.search_input)

        # Search button
        self.search_btn = QPushButton("검색")
        self.search_btn.setStyleSheet("""
            QPushButton {
                font-size: 12px;
                padding: 6px 16px;
                background: #3498db;
                color: white;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover {
                background: #2980b9;
            }
            QPushButton:pressed {
                background: #21618c;
            }
        """)
        self.search_btn.clicked.connect(self._on_search)
        header_layout.addWidget(self.search_btn)

        layout.addLayout(header_layout)

        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            "Player ID", "Total", "Win", "Lose", "Win Rate", "Last Played At"
        ])

        # Table styling
        self.table.setStyleSheet("""
            QTableWidget {
                background: white;
                border: 1px solid #bdc3c7;
                border-radius: 4px;
                gridline-color: #ecf0f1;
                font-size: 12px;
            }
            QTableWidget::item {
                padding: 4px 8px;
                color: #2c3e50;
            }
            QTableWidget::item:selected {
                background: #3498db;
                color: white;
            }
            QTableWidget::item:hover {
                background: #e8f6ff;
            }
            QHeaderView::section {
                background: #ecf0f1;
                color: #2c3e50;
                font-weight: bold;
                font-size: 11px;
                padding: 6px 8px;
                border: none;
                border-bottom: 1px solid #bdc3c7;
                border-right: 1px solid #d5d8dc;
            }
            QHeaderView::section:last {
                border-right: none;
            }
            QHeaderView::section:hover {
                background: #d5dbdb;
            }
        """)

        # Table behavior
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(True)

        # Disable Qt internal sorting - we use DB-level sorting
        self.table.setSortingEnabled(False)

        # Column resizing
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
        self.table.setColumnWidth(0, 120)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)

        # Enable sort indicator and handle header clicks
        header.setSortIndicatorShown(True)
        header.setSectionsClickable(True)
        header.sectionClicked.connect(self._on_header_clicked)

        # Set initial sort indicator
        header.setSortIndicator(0, Qt.SortOrder.AscendingOrder)

        # Row double-click handler for detail page
        self.table.cellDoubleClicked.connect(self._on_row_double_clicked)

        layout.addWidget(self.table)

        # Footer with settings button
        footer_layout = QHBoxLayout()
        footer_layout.setContentsMargins(0, 8, 0, 0)
        footer_layout.addStretch()

        self.settings_btn = QPushButton("⚙ 설정")
        self.settings_btn.setStyleSheet("""
            QPushButton {
                font-size: 12px;
                padding: 6px 16px;
                background: #95a5a6;
                color: white;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover {
                background: #7f8c8d;
            }
            QPushButton:pressed {
                background: #566573;
            }
        """)
        self.settings_btn.clicked.connect(self._on_settings_clicked)
        footer_layout.addWidget(self.settings_btn)

        layout.addLayout(footer_layout)

        # Initial data load
        self._refresh()

    def _subscribe_events(self):
        """Subscribe to EventBus events."""
        event_bus = EventBus.instance()
        event_bus.replay_added.connect(self._on_replay_added)
        event_bus.player_updated.connect(self._on_player_updated)
        event_bus.data_refresh_requested.connect(self._on_data_refresh_requested)

    def _on_replay_added(self, match_history: MatchHistoryDTO):
        """Handle replay added event."""
        # Refresh table to show updated stats
        self._refresh()

    def _on_player_updated(self, game_id: str):
        """Handle player updated event."""
        self._refresh()

    def _on_data_refresh_requested(self):
        """Handle data refresh request."""
        self._refresh()

    def _on_search(self):
        """Handle search action."""
        self._search_game_id = self.search_input.text().strip()
        self._refresh()

    def _on_header_clicked(self, column_index: int):
        """Handle header click for sorting."""
        order_column = COLUMN_TO_ORDER.get(column_index)
        if order_column is None:
            return

        # Toggle direction if same column, otherwise default to ASC
        if self._order_column == order_column:
            self._order_direction = (
                TypeOrderDirection.DESC
                if self._order_direction == TypeOrderDirection.ASC
                else TypeOrderDirection.ASC
            )
        else:
            self._order_column = order_column
            self._order_direction = TypeOrderDirection.ASC

        # Update sort indicator
        header = self.table.horizontalHeader()
        sort_order = (
            Qt.SortOrder.AscendingOrder
            if self._order_direction == TypeOrderDirection.ASC
            else Qt.SortOrder.DescendingOrder
        )
        header.setSortIndicator(column_index, sort_order)

        # Refresh with new sort
        self._refresh()

    def _refresh(self):
        """Refresh data from database with current search/sort settings."""
        self._players = self._player_service.get_all_players(
            search_game_id=self._search_game_id,
            order_by=self._order_column,
            order_direction=self._order_direction
        )
        self._refresh_table()

    def set_players(self, players: list[Player]):
        """Set the player data and refresh the table."""
        self._players = players
        self._refresh_table()

    def _refresh_table(self):
        """Refresh the table with current player data."""
        time_zone = self._config.time_zone.get_timezone()
        self.table.setRowCount(len(self._players))

        for row, player in enumerate(self._players):
            # Player ID
            id_item = QTableWidgetItem(player.game_id)
            id_item.setData(Qt.ItemDataRole.UserRole, player)
            self.table.setItem(row, 0, id_item)

            # Total (total games)
            total_item = NumericTableWidgetItem(player.total_games)
            total_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 1, total_item)

            # Win
            wins_item = NumericTableWidgetItem(player.total_wins)
            wins_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 2, wins_item)

            # Lose
            losses_item = NumericTableWidgetItem(player.total_losses)
            losses_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 3, losses_item)

            # Win Rate
            win_rate_text = f"{player.total_win_rate:.1f}%"
            win_rate_item = NumericTableWidgetItem(player.total_win_rate, win_rate_text)
            win_rate_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 4, win_rate_item)

            # Last Played At
            if player.last_played_at:
                last_played = (
                    player.last_played_at
                    .replace(tzinfo=UTC)
                    .astimezone(time_zone)
                    .strftime("%Y-%m-%d %H:%M")
                )
                timestamp = (
                    player.last_played_at
                    .replace(tzinfo=UTC)
                    .astimezone(time_zone)
                    .timestamp()
                )
            else:
                last_played = "-"
                timestamp = 0
            last_played_item = NumericTableWidgetItem(timestamp, last_played)
            self.table.setItem(row, 5, last_played_item)

            # Set row height
            self.table.setRowHeight(row, 32)

    def _on_row_double_clicked(self, row: int, column: int):
        """Handle row double-click - emit selected player."""
        item = self.table.item(row, 0)
        if item:
            player = item.data(Qt.ItemDataRole.UserRole)
            if player:
                self.player_selected.emit(player)

    def _on_settings_clicked(self):
        """Open quick settings dialog."""
        from .quick_settings_dialog import QuickSettingsDialog

        dialog = QuickSettingsDialog(self)
        dialog.exec()
