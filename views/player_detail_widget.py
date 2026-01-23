"""
Player Detail Widget - displays match history and player description.
"""
from datetime import UTC
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QAbstractItemView,
    QPushButton,
    QTextEdit,
    QGroupBox,
)
from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QColor

from common.event_bus import EventBus
from common.const import TypeOrderColumn, TypeOrderDirection

from models.player import Player
from models.match_history import MatchHistory
from dto.match_history import MatchHistoryDTO
from services.match_history_service import MatchHistoryService
from config.app_config import AppConfig


# Column index to TypeOrderColumn mapping for MatchHistory
COLUMN_TO_ORDER = {
    0: TypeOrderColumn.RACE,
    1: TypeOrderColumn.MAP_NAME,
    2: TypeOrderColumn.IS_WIN,
    3: TypeOrderColumn.PLAYTIME,
    4: TypeOrderColumn.PLAYED_AT,
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


class PlayerDetailWidget(QWidget):
    """Widget displaying match history for a specific player."""

    back_clicked = Signal()  # Emitted when back button is clicked
    description_updated = Signal(str, str)  # Emitted with (game_id, description)

    def __init__(self, match_history_service: MatchHistoryService, parent=None):
        super().__init__(parent)
        self._match_history_service: MatchHistoryService = match_history_service
        self._player: Player | None = None
        self._match_histories: list[MatchHistory] = []
        self._is_editing: bool = False
        self._config: AppConfig = AppConfig.get_instance()

        # Sort state
        self._order_column: TypeOrderColumn = TypeOrderColumn.PLAYED_AT
        self._order_direction: TypeOrderDirection = TypeOrderDirection.DESC
        self._setup_ui()
        self._subscribe_events()

    def _setup_ui(self):
        """Setup the UI layout."""
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(24, 24, 24, 24)

        # Header with back button and title
        header_layout = QHBoxLayout()

        self.back_btn = QPushButton("← 뒤로")
        self.back_btn.setStyleSheet("""
            QPushButton {
                font-size: 12px;
                padding: 6px 12px;
                background: #ecf0f1;
                border: 1px solid #bdc3c7;
                border-radius: 4px;
                color: #2c3e50;
            }
            QPushButton:hover {
                background: #d5dbdb;
            }
            QPushButton:pressed {
                background: #bdc3c7;
            }
        """)
        self.back_btn.clicked.connect(self._on_back_clicked)
        header_layout.addWidget(self.back_btn)

        self.title_label = QLabel("Match History")
        self.title_label.setStyleSheet("""
            QLabel {
                font-size: 20px;
                font-weight: bold;
                color: #2c3e50;
                padding-left: 12px;
            }
        """)
        header_layout.addWidget(self.title_label)
        header_layout.addStretch()

        layout.addLayout(header_layout)

        # Match history table
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels([
            "Race", "Map", "Win", "Play Time", "Played At"
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
            }
            QTableWidget::item:selected {
                background: #3498db;
                color: white;
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
        self.table.setSortingEnabled(False)  # Disable Qt internal sorting, use DB-level sorting

        # Column resizing
        header = self.table.horizontalHeader()
        # Race - fixed small width
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        # Map
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Interactive)
        self.table.setColumnWidth(1, 90)
        # Win
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        # PlayTime
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        # Played At - stretch to fill
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)

        # Enable sorting click indicator and header click handler
        header.setSortIndicatorShown(True)
        header.setSectionsClickable(True)
        header.sectionClicked.connect(self._on_header_clicked)

        layout.addWidget(self.table)

        # Description section
        desc_group = QGroupBox("Player Description")
        desc_group.setStyleSheet("""
            QGroupBox {
                font-size: 13px;
                font-weight: bold;
                color: #34495e;
                border: 1px solid #bdc3c7;
                border-radius: 4px;
                margin-top: 8px;
                padding-top: 8px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 6px;
            }
        """)
        desc_layout = QVBoxLayout(desc_group)
        desc_layout.setSpacing(10)
        desc_layout.setContentsMargins(12, 20, 12, 12)

        # Description text area
        self.description_text = QTextEdit()
        self.description_text.setReadOnly(True)
        self.description_text.setMinimumHeight(60)
        self.description_text.setMaximumHeight(100)
        self.description_text.setStyleSheet("""
            QTextEdit {
                font-size: 12px;
                padding: 8px;
                border: 1px solid #bdc3c7;
                border-radius: 4px;
                background: #fafafa;
                color: #2c3e50;
            }
            QTextEdit:focus {
                border: 2px solid #3498db;
                background: white;
            }
        """)
        desc_layout.addWidget(self.description_text)

        # Edit/Save button
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self.edit_btn = QPushButton("수정")
        self.edit_btn.setStyleSheet("""
            QPushButton {
                font-size: 12px;
                font-weight: bold;
                padding: 6px 20px;
                background: #3498db;
                color: white;
                border: none;
                border-radius: 4px;
                min-width: 70px;
            }
            QPushButton:hover {
                background: #2980b9;
            }
            QPushButton:pressed {
                background: #21618c;
            }
        """)
        self.edit_btn.clicked.connect(self._on_edit_clicked)

        self.cancel_btn = QPushButton("취소")
        self.cancel_btn.setStyleSheet("""
            QPushButton {
                font-size: 12px;
                padding: 6px 20px;
                background: #ecf0f1;
                color: #2c3e50;
                border: 1px solid #bdc3c7;
                border-radius: 4px;
                min-width: 70px;
            }
            QPushButton:hover {
                background: #d5dbdb;
            }
            QPushButton:pressed {
                background: #bdc3c7;
            }
        """)
        self.cancel_btn.clicked.connect(self._on_cancel_clicked)
        self.cancel_btn.hide()

        btn_layout.addWidget(self.cancel_btn)
        btn_layout.addWidget(self.edit_btn)
        desc_layout.addLayout(btn_layout)

        layout.addWidget(desc_group)

    def set_player(self, player: Player):
        """Set the current player and load match histories."""
        self._player = player
        self.title_label.setText(f"Match History - {player.game_id}")
        self.description_text.setText(player.description or "")
        self._is_editing = False
        self._update_edit_state()
        # Load match histories with current sort settings
        self._refresh()

    def set_match_histories(self, histories: list[MatchHistory]):
        """Set match histories and refresh table (legacy, for backward compatibility)."""
        # Filter histories for the current player
        if self._player:
            self._match_histories = [
                h for h in histories
                if h.player_id == self._player.id
            ]
        else:
            self._match_histories = []
        self._refresh_table()

    def _refresh(self):
        """Refresh data from DB with current sort settings."""
        if self._player and self._match_history_service:
            self._match_histories = self._match_history_service.get_match_histories_by_player(
                player_id=self._player.id,
                order_by=self._order_column,
                order_direction=self._order_direction
            )
        self._refresh_table()
        self._update_sort_indicator()

    def _refresh_table(self):
        """Refresh the table with current match history data."""
        time_zone = self._config.time_zone.get_timezone()
        # Disable sorting while populating
        self.table.setSortingEnabled(False)
        self.table.setRowCount(len(self._match_histories))

        default_color = QColor("#2c3e50")
        win_color = QColor("#27ae60")
        lose_color = QColor("#e74c3c")

        for row, history in enumerate(self._match_histories):
            # Race
            race_item = QTableWidgetItem(history.race)
            race_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            race_item.setForeground(default_color)
            self.table.setItem(row, 0, race_item)

            # Map
            map_item = QTableWidgetItem(history.map_name)
            map_item.setForeground(default_color)
            self.table.setItem(row, 1, map_item)

            # Win (sortable text instead of checkbox)
            win_value = 1 if history.is_win else 0
            win_text = "✓" if history.is_win else "✗"
            win_item = NumericTableWidgetItem(win_value, win_text)
            win_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            if history.is_win:
                win_item.setForeground(win_color)
            else:
                win_item.setForeground(lose_color)
            self.table.setItem(row, 2, win_item)

            # PlayTime (mm:ss format)
            minutes = history.playtime // 60
            seconds = history.playtime % 60
            playtime_str = f"{minutes:02d}:{seconds:02d}"
            playtime_item = NumericTableWidgetItem(history.playtime, playtime_str)
            playtime_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            playtime_item.setForeground(default_color)
            self.table.setItem(row, 3, playtime_item)

            # Played At
            if history.played_at:
                played_at = (
                    history.played_at
                    .replace(tzinfo=UTC)
                    .astimezone(time_zone)
                    .strftime("%Y-%m-%d %H:%M")
                )
                timestamp = (
                    history.played_at
                    .replace(tzinfo=UTC)
                    .astimezone(time_zone)
                    .timestamp()
                )
            else:
                played_at = "-"
                timestamp = 0
            played_at_item = NumericTableWidgetItem(timestamp, played_at)
            played_at_item.setForeground(default_color)
            self.table.setItem(row, 4, played_at_item)

            # Set row height
            self.table.setRowHeight(row, 28)

    def _on_header_clicked(self, column_index: int):
        """Handle header column click for sorting."""
        order_column = COLUMN_TO_ORDER.get(column_index)
        if order_column is None:
            return

        # Toggle direction if same column, otherwise default to DESC
        if self._order_column == order_column:
            self._order_direction = (
                TypeOrderDirection.DESC
                if self._order_direction == TypeOrderDirection.ASC
                else TypeOrderDirection.ASC
            )
        else:
            self._order_column = order_column
            self._order_direction = TypeOrderDirection.DESC

        self._refresh()

    def _update_sort_indicator(self):
        """Update the sort indicator on the header."""
        header = self.table.horizontalHeader()
        # Find column index for current order column
        column_index = None
        for idx, col in COLUMN_TO_ORDER.items():
            if col == self._order_column:
                column_index = idx
                break

        if column_index is not None:
            sort_order = (
                Qt.SortOrder.AscendingOrder
                if self._order_direction == TypeOrderDirection.ASC
                else Qt.SortOrder.DescendingOrder
            )
            header.setSortIndicator(column_index, sort_order)

    def _update_edit_state(self):
        """Update UI based on editing state."""
        self.description_text.setReadOnly(not self._is_editing)
        if self._is_editing:
            self.edit_btn.setText("저장")
            self.cancel_btn.show()
            self.description_text.setStyleSheet("""
                QTextEdit {
                    font-size: 12px;
                    padding: 8px;
                    border: 2px solid #3498db;
                    border-radius: 4px;
                    background: white;
                    color: #2c3e50;
                }
            """)
        else:
            self.edit_btn.setText("수정")
            self.cancel_btn.hide()
            self.description_text.setStyleSheet("""
                QTextEdit {
                    font-size: 12px;
                    padding: 8px;
                    border: 1px solid #bdc3c7;
                    border-radius: 4px;
                    background: #fafafa;
                    color: #2c3e50;
                }
            """)

    def _subscribe_events(self):
        """Subscribe to events."""
        self.event_bus = EventBus.instance()
        self.event_bus.replay_added.connect(self._on_replay_added)

    def _on_replay_added(self, match_history: MatchHistoryDTO):
        """Handle replay added event."""
        # Refresh table to show updated stats with current sort settings
        if self._player and match_history.opponent_id == self._player.game_id:
            self._refresh()

    def _on_edit_clicked(self):
        """Handle edit/save button click."""
        if self._is_editing:
            # Save mode - save the description
            if self._player:
                new_description = self.description_text.toPlainText()
                self.description_updated.emit(self._player.game_id, new_description)
                self._player.description = new_description
            self._is_editing = False
        else:
            # Edit mode - enable editing
            self._is_editing = True

        self._update_edit_state()

    def _on_cancel_clicked(self):
        """Handle cancel button click."""
        # Restore original description
        if self._player:
            self.description_text.setText(self._player.description or "")
        self._is_editing = False
        self._update_edit_state()

    def _on_back_clicked(self):
        """Handle back button click."""
        self.back_clicked.emit()
