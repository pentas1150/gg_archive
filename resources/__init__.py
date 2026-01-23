"""
Resources package - Icons, styles, and other assets.
"""
import sys
from pathlib import Path


def _get_resources_dir() -> Path:
    """Get the resources directory, handling PyInstaller packaging."""
    if getattr(sys, 'frozen', False):
        # PyInstaller로 패키징된 경우
        return Path(sys._MEIPASS) / "resources"
    else:
        # 개발 환경
        return Path(__file__).parent


# Resource directory paths
RESOURCES_DIR = _get_resources_dir()
ICONS_DIR = RESOURCES_DIR / "icons"
STYLES_DIR = RESOURCES_DIR / "styles"


def get_icon_path(icon_name: str) -> Path:
    """Get the full path to an icon file."""
    return ICONS_DIR / icon_name


def get_style_path(style_name: str) -> Path:
    """Get the full path to a stylesheet file."""
    return STYLES_DIR / style_name


def load_stylesheet(style_name: str) -> str:
    """
    Load a QSS stylesheet file.

    Args:
        style_name: Name of the stylesheet file

    Returns:
        Stylesheet content as string
    """
    style_path = get_style_path(style_name)
    if style_path.exists():
        return style_path.read_text(encoding="utf-8")
    return ""
