"""
Views package - UI components.
"""
from .main_window import MainWindow
from .settings_widget import SettingsWidget
from .all_stats_widget import AllStatsWidget
from .player_detail_widget import PlayerDetailWidget
from .screp_download_dialog import ScrepDownloadDialog

__all__ = [
    "MainWindow",
    "SettingsWidget",
    "AllStatsWidget",
    "PlayerDetailWidget",
    "ScrepDownloadDialog",
]
