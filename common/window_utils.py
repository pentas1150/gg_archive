"""창을 강제로 전면에 띄우는 유틸.

Windows는 포그라운드 프로세스가 아닌 앱의 SetForegroundWindow 호출을 거부하고
작업표시줄 깜빡임으로 대체한다. Qt API만으로는 우회할 수 없어 ctypes로 Win32를 직접 호출한다.
"""
import ctypes
import sys

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QWidget

from common.logger import get_logger

# Win32 상수
_SWP_NOSIZE = 0x0001
_SWP_NOMOVE = 0x0002
_SWP_NOACTIVATE = 0x0010
_SWP_SHOWWINDOW = 0x0040
_HWND_TOPMOST = -1
_HWND_NOTOPMOST = -2
_SW_RESTORE = 9

_IS_WINDOWS = sys.platform == "win32"


def bring_to_front(window: QWidget, keep_on_top_ms: int = 0) -> None:
    """창을 최소화/트레이/가려짐 상태에서 꺼내 최상위로 올린다.

    Args:
        window: 전면에 띄울 창
        keep_on_top_ms: 0보다 크면 해당 시간(ms) 동안 always-on-top 유지 후 자동 해제
    """
    # Qt 레벨: 최소화 플래그를 먼저 제거해야 show/raise/activate가 의미를 갖는다
    window.setWindowState(
        (window.windowState() & ~Qt.WindowState.WindowMinimized) | Qt.WindowState.WindowActive
    )
    window.show()
    window.raise_()
    window.activateWindow()

    if not _IS_WINDOWS:
        return

    try:
        hwnd = int(window.winId())
        _force_foreground(hwnd)
    except Exception as e:
        # Qt 레벨 처리는 이미 끝났으므로 기존 동작으로 degrade
        get_logger("window_utils").debug("Win32 force foreground failed: %s", e)
        return

    if keep_on_top_ms > 0:
        QTimer.singleShot(keep_on_top_ms, lambda: _clear_topmost(hwnd))


def _user32():
    """argtypes/restype이 설정된 user32 핸들 반환.

    64비트에서 HWND는 포인터라 argtypes를 지정하지 않으면 핸들이 32비트로 잘려 조용히 실패한다.
    """
    from ctypes import wintypes

    user32 = ctypes.windll.user32
    user32.IsIconic.argtypes = [wintypes.HWND]
    user32.IsIconic.restype = wintypes.BOOL
    user32.IsWindow.argtypes = [wintypes.HWND]
    user32.IsWindow.restype = wintypes.BOOL
    user32.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
    user32.ShowWindow.restype = wintypes.BOOL
    user32.SetWindowPos.argtypes = [
        wintypes.HWND, wintypes.HWND,
        ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int,
        ctypes.c_uint,
    ]
    user32.SetWindowPos.restype = wintypes.BOOL
    user32.GetForegroundWindow.argtypes = []
    user32.GetForegroundWindow.restype = wintypes.HWND
    user32.SetForegroundWindow.argtypes = [wintypes.HWND]
    user32.SetForegroundWindow.restype = wintypes.BOOL
    user32.BringWindowToTop.argtypes = [wintypes.HWND]
    user32.BringWindowToTop.restype = wintypes.BOOL
    user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, wintypes.LPDWORD]
    user32.GetWindowThreadProcessId.restype = wintypes.DWORD
    user32.AttachThreadInput.argtypes = [wintypes.DWORD, wintypes.DWORD, wintypes.BOOL]
    user32.AttachThreadInput.restype = wintypes.BOOL
    return user32


def _force_foreground(hwnd: int) -> None:
    """포그라운드 잠금을 우회해 창을 최상위로 올린다 (Windows 전용)."""
    from ctypes import wintypes

    user32 = _user32()

    if user32.IsIconic(hwnd):
        user32.ShowWindow(hwnd, _SW_RESTORE)

    # topmost 승격: SetForegroundWindow가 거부돼도 전체화면 창 위에 보이게 된다
    user32.SetWindowPos(
        hwnd, wintypes.HWND(_HWND_TOPMOST), 0, 0, 0, 0,
        _SWP_NOMOVE | _SWP_NOSIZE | _SWP_SHOWWINDOW,
    )

    # 현재 포그라운드 스레드에 입력 큐를 붙여야 SetForegroundWindow가 허용된다
    foreground_hwnd = user32.GetForegroundWindow()
    current_tid = ctypes.windll.kernel32.GetCurrentThreadId()
    foreground_tid = (
        user32.GetWindowThreadProcessId(foreground_hwnd, None) if foreground_hwnd else 0
    )
    attached = bool(
        foreground_tid
        and foreground_tid != current_tid
        and user32.AttachThreadInput(foreground_tid, current_tid, True)
    )
    try:
        user32.SetForegroundWindow(hwnd)
        user32.BringWindowToTop(hwnd)
    finally:
        if attached:
            user32.AttachThreadInput(foreground_tid, current_tid, False)


def _clear_topmost(hwnd: int) -> None:
    """always-on-top 해제. 창이 이미 파괴됐으면 아무것도 하지 않는다."""
    from ctypes import wintypes

    try:
        user32 = _user32()
        if not user32.IsWindow(hwnd):
            return
        user32.SetWindowPos(
            hwnd, wintypes.HWND(_HWND_NOTOPMOST), 0, 0, 0, 0,
            _SWP_NOMOVE | _SWP_NOSIZE | _SWP_NOACTIVATE,
        )
    except Exception as e:
        get_logger("window_utils").debug("Clear topmost failed: %s", e)
