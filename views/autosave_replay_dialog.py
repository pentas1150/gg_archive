"""
AutoSave Replay Import Dialog - Import replays from AutoSave directories.
"""
import re
from pathlib import Path
from datetime import datetime

from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QFormLayout,
    QPushButton,
    QLabel,
    QLineEdit,
    QFileDialog,
    QProgressBar,
    QTextEdit,
    QMessageBox,
    QDateEdit,
    QWidget,
    QGroupBox,
)
from PySide6.QtCore import Signal, Slot, QThread, QDate

from config.app_config import AppConfig
from common.const import TypeErrorCode
from common.exceptions import ReplayAnalysisError
from services.background.replay_watch_service import ReplayWatchService


class ReplayImportWorker(QThread):
    """Worker thread for importing replays."""

    progress_updated = Signal(int, int, str)  # current, total, message
    replay_processed = Signal(str, bool, str)  # file_path, success, message
    finished_import = Signal(int, int)  # success_count, total_count

    def __init__(self, directories: list[Path], replay_watch_service: ReplayWatchService):
        super().__init__()
        self.directories = directories
        self.replay_watch_service = replay_watch_service
        self._is_cancelled = False

    def cancel(self):
        self._is_cancelled = True

    def run(self):
        total_replays = []

        # Collect all .rep files from directories (descending order by directory name)
        for directory in sorted(self.directories, reverse=True):
            if self._is_cancelled:
                break
            rep_files = list(directory.glob("*.rep"))
            total_replays.extend(rep_files)

        total_count = len(total_replays)
        success_count = 0

        for i, rep_file in enumerate(total_replays):
            if self._is_cancelled:
                break

            self.progress_updated.emit(i + 1, total_count, f"처리 중: {rep_file.name}")

            try:
                self.replay_watch_service.analyze_replay_and_upsert(rep_file)
                success_count += 1
                self.replay_processed.emit(str(rep_file), True, "성공")
            except ReplayAnalysisError as e:
                # 커스텀 예외 - 에러 코드로 분기
                if e.error_code == TypeErrorCode.DUPLICATE:
                    # 중복은 성공으로 카운트하되 로그에 표시 안 함
                    success_count += 1
                elif e.error_code.is_skip():
                    # 정상 스킵 (시간 부족, 1vs1 아님 등)
                    self.replay_processed.emit(str(rep_file), False, e.error_code.get_user_message())
                else:
                    # 실제 에러
                    self.replay_processed.emit(str(rep_file), False, str(e))
            except Exception as e:
                # 예상치 못한 예외
                self.replay_processed.emit(str(rep_file), False, f"오류: {e}")

        self.finished_import.emit(success_count, total_count)


class AutoSaveReplayDialog(QDialog):
    """AutoSave 리플레이 불러오기 다이얼로그"""

    import_completed = Signal()

    def __init__(self, replay_watch_service: ReplayWatchService, parent=None):
        super().__init__(parent)
        self.config = AppConfig.get_instance()
        self.replay_watch_service = replay_watch_service
        self.date_directories: dict[str, Path] = {}  # date_str -> Path mapping
        self.worker: ReplayImportWorker | None = None

        self.setWindowTitle("AutoSave 리플레이 불러오기")
        self.setMinimumWidth(600)
        self.setMinimumHeight(500)
        self._setup_ui()

    def _setup_ui(self):
        # Set dialog background to match All Stats widget
        self.setStyleSheet("""
            QDialog {
                background: #f5f6fa;
            }
            QLabel {
                color: #2c3e50;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 24, 24, 24)

        # Title
        title = QLabel("AutoSave 리플레이 불러오기")
        title.setStyleSheet("""
            QLabel {
                font-size: 18px;
                font-weight: bold;
                color: #2c3e50;
            }
        """)
        layout.addWidget(title)

        # Description
        desc = QLabel("AutoSave 디렉토리를 선택하면 날짜별 폴더(YYYYMMDD)에서 리플레이를 불러옵니다.")
        desc.setStyleSheet("""
            QLabel {
                font-size: 12px;
                color: #7f8c8d;
            }
        """)
        desc.setWordWrap(True)
        layout.addWidget(desc)

        # Directory selection group
        dir_group = QGroupBox("디렉토리 선택")
        dir_group.setStyleSheet("""
            QGroupBox {
                font-size: 13px;
                font-weight: bold;
                color: #2c3e50;
                background: #f5f6fa;
                border: 1px solid #bdc3c7;
                border-radius: 4px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
                background: #f5f6fa;
            }
        """)
        dir_layout = QVBoxLayout(dir_group)

        # Directory path input
        path_layout = QHBoxLayout()
        self.path_input = QLineEdit()
        self.path_input.setPlaceholderText("AutoSave 디렉토리 경로를 선택하세요")
        self.path_input.setStyleSheet("""
            QLineEdit {
                font-size: 13px;
                padding: 8px 12px;
                border: 1px solid #bdc3c7;
                border-radius: 4px;
                background: white;
                color: #2c3e50;
            }
            QLineEdit:focus {
                border: 2px solid #3498db;
            }
        """)
        self.path_input.setReadOnly(True)

        browse_btn = QPushButton("찾아보기...")
        browse_btn.setStyleSheet("""
            QPushButton {
                font-size: 13px;
                padding: 8px 16px;
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
        browse_btn.clicked.connect(self._on_browse)

        path_layout.addWidget(self.path_input, 1)
        path_layout.addWidget(browse_btn)
        dir_layout.addLayout(path_layout)

        # Date range info and selection
        self.range_widget = QWidget()
        range_layout = QFormLayout(self.range_widget)
        range_layout.setSpacing(12)

        label_style = """
            QLabel {
                font-size: 13px;
                color: #2c3e50;
            }
        """

        # Found date range display
        self.date_range_label = QLabel("선택된 디렉토리 없음")
        self.date_range_label.setStyleSheet(label_style)
        found_range_label = QLabel("발견된 날짜 범위:")
        found_range_label.setStyleSheet(label_style)
        range_layout.addRow(found_range_label, self.date_range_label)

        # Date range selection
        date_edit_style = """
            QDateEdit {
                font-size: 13px;
                padding: 8px 12px;
                border: 1px solid #bdc3c7;
                border-radius: 4px;
                background: white;
                color: #2c3e50;
            }
            QDateEdit:focus {
                border: 2px solid #3498db;
            }
            QDateEdit::drop-down {
                border: none;
                width: 20px;
            }
        """

        date_range_widget = QWidget()
        date_range_layout = QHBoxLayout(date_range_widget)
        date_range_layout.setContentsMargins(0, 0, 0, 0)
        date_range_layout.setSpacing(10)

        self.start_date_edit = QDateEdit()
        self.start_date_edit.setCalendarPopup(True)
        self.start_date_edit.setStyleSheet(date_edit_style)
        self.start_date_edit.setEnabled(False)

        self.end_date_edit = QDateEdit()
        self.end_date_edit.setCalendarPopup(True)
        self.end_date_edit.setStyleSheet(date_edit_style)
        self.end_date_edit.setEnabled(False)

        start_label = QLabel("시작:")
        start_label.setStyleSheet(label_style)
        date_range_layout.addWidget(start_label)
        date_range_layout.addWidget(self.start_date_edit)

        end_label = QLabel("종료:")
        end_label.setStyleSheet(label_style)
        date_range_layout.addWidget(end_label)
        date_range_layout.addWidget(self.end_date_edit)
        date_range_layout.addStretch()

        import_range_label = QLabel("불러올 범위:")
        import_range_label.setStyleSheet(label_style)
        range_layout.addRow(import_range_label, date_range_widget)

        dir_layout.addWidget(self.range_widget)
        layout.addWidget(dir_group)

        # Progress group
        progress_group = QGroupBox("진행 상황")
        progress_group.setStyleSheet("""
            QGroupBox {
                font-size: 13px;
                font-weight: bold;
                color: #2c3e50;
                background: #f5f6fa;
                border: 1px solid #bdc3c7;
                border-radius: 4px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
                background: #f5f6fa;
            }
        """)
        progress_layout = QVBoxLayout(progress_group)

        self.progress_bar = QProgressBar()
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #bdc3c7;
                border-radius: 4px;
                text-align: center;
                height: 20px;
                background: white;
                color: #2c3e50;
            }
            QProgressBar::chunk {
                background: #3498db;
                border-radius: 3px;
            }
        """)
        self.progress_bar.setValue(0)
        progress_layout.addWidget(self.progress_bar)

        self.progress_label = QLabel("대기 중...")
        self.progress_label.setStyleSheet("""
            QLabel {
                font-size: 12px;
                color: #7f8c8d;
            }
        """)
        progress_layout.addWidget(self.progress_label)

        # Log output
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setMaximumHeight(150)
        self.log_output.setStyleSheet("""
            QTextEdit {
                font-size: 11px;
                font-family: monospace;
                background: #2c3e50;
                color: #ecf0f1;
                border: 1px solid #bdc3c7;
                border-radius: 4px;
                padding: 8px;
            }
        """)
        progress_layout.addWidget(self.log_output)

        layout.addWidget(progress_group)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setContentsMargins(0, 10, 0, 0)
        btn_layout.addStretch()

        self.cancel_btn = QPushButton("취소")
        self.cancel_btn.setStyleSheet("""
            QPushButton {
                font-size: 13px;
                padding: 8px 20px;
                background: #ecf0f1;
                color: #2c3e50;
                border: 1px solid #bdc3c7;
                border-radius: 4px;
                min-width: 80px;
            }
            QPushButton:hover {
                background: #d5dbdb;
            }
            QPushButton:pressed {
                background: #bdc3c7;
            }
        """)
        self.cancel_btn.clicked.connect(self._on_cancel)

        self.import_btn = QPushButton("불러오기 시작")
        self.import_btn.setStyleSheet("""
            QPushButton {
                font-size: 13px;
                font-weight: bold;
                padding: 8px 20px;
                background: #27ae60;
                color: white;
                border: none;
                border-radius: 4px;
                min-width: 120px;
            }
            QPushButton:hover {
                background: #219a52;
            }
            QPushButton:pressed {
                background: #1e8449;
            }
            QPushButton:disabled {
                background: #95a5a6;
            }
        """)
        self.import_btn.setEnabled(False)
        self.import_btn.clicked.connect(self._on_import)

        btn_layout.addWidget(self.cancel_btn)
        btn_layout.addWidget(self.import_btn)
        layout.addLayout(btn_layout)

    @Slot()
    def _on_browse(self):
        """Open directory selection dialog."""
        directory = QFileDialog.getExistingDirectory(
            self,
            "AutoSave 디렉토리 선택",
            str(Path.home()),
            QFileDialog.Option.ShowDirsOnly
        )

        if directory:
            self.path_input.setText(directory)
            self._scan_directory(Path(directory))

    def _scan_directory(self, base_dir: Path):
        """Scan directory for date-formatted subdirectories."""
        self.date_directories.clear()

        if not base_dir.exists():
            QMessageBox.warning(
                self,
                "경고",
                f"디렉토리가 존재하지 않습니다:\n{base_dir}"
            )
            self._reset_date_range()
            return

        if not base_dir.is_dir():
            QMessageBox.warning(
                self,
                "경고",
                f"유효한 디렉토리가 아닙니다:\n{base_dir}"
            )
            self._reset_date_range()
            return

        # Pattern for YYYYMMDD format
        date_pattern = re.compile(r"^\d{8}$")

        for item in base_dir.iterdir():
            if item.is_dir() and date_pattern.match(item.name):
                try:
                    # Validate it's a valid date
                    datetime.strptime(item.name, "%Y%m%d")
                    self.date_directories[item.name] = item
                except ValueError:
                    continue  # Invalid date format, skip

        if not self.date_directories:
            QMessageBox.warning(
                self,
                "경고",
                "선택한 디렉토리 하위에 날짜 형식(YYYYMMDD) 폴더가 없습니다.\n"
                "예: 20251101, 20251102 형식의 폴더가 필요합니다."
            )
            self._reset_date_range()
            return

        self._update_date_range()

    def _reset_date_range(self):
        """Reset date range UI to initial state."""
        self.date_range_label.setText("선택된 디렉토리 없음")
        self.start_date_edit.setEnabled(False)
        self.end_date_edit.setEnabled(False)
        self.import_btn.setEnabled(False)

    def _update_date_range(self):
        """Update date range UI with found directories."""
        sorted_dates = sorted(self.date_directories.keys())
        min_date_str = sorted_dates[0]
        max_date_str = sorted_dates[-1]

        min_date = datetime.strptime(min_date_str, "%Y%m%d")
        max_date = datetime.strptime(max_date_str, "%Y%m%d")

        self.date_range_label.setText(
            f"{min_date_str} ~ {max_date_str} (총 {len(sorted_dates)}개 폴더)"
        )

        # Set date edit ranges
        q_min_date = QDate(min_date.year, min_date.month, min_date.day)
        q_max_date = QDate(max_date.year, max_date.month, max_date.day)

        self.start_date_edit.setDateRange(q_min_date, q_max_date)
        self.start_date_edit.setDate(q_min_date)
        self.start_date_edit.setEnabled(True)

        self.end_date_edit.setDateRange(q_min_date, q_max_date)
        self.end_date_edit.setDate(q_max_date)
        self.end_date_edit.setEnabled(True)

        self.import_btn.setEnabled(True)

        self._log(f"[정보] {len(sorted_dates)}개의 날짜 폴더 발견: {min_date_str} ~ {max_date_str}")

    def _get_selected_directories(self) -> list[Path]:
        """Get directories within selected date range."""
        start_date = self.start_date_edit.date().toPython()
        end_date = self.end_date_edit.date().toPython()

        start_str = start_date.strftime("%Y%m%d")
        end_str = end_date.strftime("%Y%m%d")

        selected = []
        for date_str, path in self.date_directories.items():
            if start_str <= date_str <= end_str:
                selected.append(path)

        return selected

    @Slot()
    def _on_import(self):
        """Start importing replays."""
        if self.start_date_edit.date() > self.end_date_edit.date():
            QMessageBox.warning(
                self,
                "경고",
                "시작 날짜가 종료 날짜보다 클 수 없습니다."
            )
            return

        selected_dirs = self._get_selected_directories()
        if not selected_dirs:
            QMessageBox.warning(
                self,
                "경고",
                "선택된 범위에 해당하는 폴더가 없습니다."
            )
            return

        # Disable UI during import
        self.import_btn.setEnabled(False)
        self.start_date_edit.setEnabled(False)
        self.end_date_edit.setEnabled(False)
        self.cancel_btn.setText("중단")

        self._log(f"[시작] {len(selected_dirs)}개 폴더에서 리플레이 불러오기 시작...")

        self.worker = ReplayImportWorker(selected_dirs, self.replay_watch_service)
        self.worker.progress_updated.connect(self._on_progress_updated)
        self.worker.replay_processed.connect(self._on_replay_processed)
        self.worker.finished_import.connect(self._on_import_finished)
        self.worker.finished.connect(self._on_worker_finished)  # QThread 종료 시그널
        self.worker.start()

    @Slot(int, int, str)
    def _on_progress_updated(self, current: int, total: int, message: str):
        """Update progress bar."""
        self.progress_bar.setMaximum(total)
        self.progress_bar.setValue(current)
        self.progress_label.setText(f"{current}/{total} - {message}")

    @Slot(str, bool, str)
    def _on_replay_processed(self, file_path: str, success: bool, message: str):
        """Log replay processing result."""
        file_name = Path(file_path).name
        if not success:
            self._log(f"[불러오기 실패] {file_name}: {message}")

    @Slot(int, int)
    def _on_import_finished(self, success_count: int, total_count: int):
        """Handle import completion."""
        self._log(f"\n[완료] 총 {total_count}개 중 {success_count}개 성공")

        self.progress_label.setText(f"완료: {success_count}/{total_count} 성공")
        self.cancel_btn.setText("닫기")
        self.import_btn.setEnabled(True)
        self.start_date_edit.setEnabled(True)
        self.end_date_edit.setEnabled(True)

        # worker는 _on_worker_finished에서 정리됨 (QThread.finished 시그널)

        QMessageBox.information(
            self,
            "불러오기 완료",
            f"리플레이 불러오기가 완료되었습니다.\n\n"
            f"총 {total_count}개 중 {success_count}개 성공"
        )

        self.import_completed.emit()

    @Slot()
    def _on_worker_finished(self):
        """Handle worker thread finished - safe cleanup."""
        # QThread가 완전히 종료된 후에 호출됨
        self.worker = None

    @Slot()
    def _on_cancel(self):
        """Handle cancel/close button."""
        if self.worker and self.worker.isRunning():
            self.worker.cancel()
            self.worker.wait()
            self._log("[중단] 사용자에 의해 중단됨")
            self.cancel_btn.setText("닫기")
            self.import_btn.setEnabled(True)
            self.start_date_edit.setEnabled(True)
            self.end_date_edit.setEnabled(True)
            self.worker = None
        else:
            self.reject()

    def _log(self, message: str):
        """Append message to log output."""
        self.log_output.append(message)
        # Auto scroll to bottom
        scrollbar = self.log_output.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def closeEvent(self, event):
        """Handle dialog close."""
        if self.worker and self.worker.isRunning():
            reply = QMessageBox.question(
                self,
                "확인",
                "불러오기가 진행 중입니다. 중단하시겠습니까?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                self.worker.cancel()
                self.worker.wait()
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()
