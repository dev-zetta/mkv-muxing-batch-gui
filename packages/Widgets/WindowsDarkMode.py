import ctypes
import platform
import sys


if sys.platform == "win32":
    from ctypes import wintypes


def immersive_dark_mode_attribute():
    try:
        windows_build = int(platform.version().split(".")[2])
    except (IndexError, TypeError, ValueError):
        windows_build = 1
    return 19 if windows_build < 19041 else 20


def load_dwm_set_window_attribute():
    if sys.platform != "win32":
        return None

    function = ctypes.WinDLL("dwmapi", use_last_error=True).DwmSetWindowAttribute
    function.argtypes = (
        wintypes.HWND,
        wintypes.DWORD,
        ctypes.c_void_p,
        wintypes.DWORD,
    )
    function.restype = ctypes.HRESULT
    return function


def set_immersive_dark_mode(window, function, attribute, enabled):
    """Apply optional Windows title-bar theming using pointer-sized handles."""
    if function is None or sys.platform != "win32":
        return False

    dark_mode_enabled = wintypes.BOOL(bool(enabled))
    result = function(
        wintypes.HWND(int(window.winId())),
        wintypes.DWORD(attribute),
        ctypes.byref(dark_mode_enabled),
        wintypes.DWORD(ctypes.sizeof(dark_mode_enabled)),
    )
    return result == 0
