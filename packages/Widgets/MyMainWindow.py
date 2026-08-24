import ctypes
import sys

from PySide6.QtWidgets import QMainWindow

from packages.Widgets.WindowsDarkMode import (
    immersive_dark_mode_attribute,
    load_dwm_set_window_attribute,
    set_immersive_dark_mode,
)


class MyMainWindow(QMainWindow):
    def __init__(self, args, parent=None):
        super().__init__()
        self.is_dark_mode_supported = False
        self.is_os_windows = (sys.platform == "win32")
        if self.is_os_windows:
            try:
                self.dwm_set_window_attribute = load_dwm_set_window_attribute()
            except (AttributeError, OSError):
                self.dwm_set_window_attribute = None
            self.dwnwa_use_immersive_dark_mode = immersive_dark_mode_attribute()
            self.is_dark_mode_supported = self.dwm_set_window_attribute is not None

    def set_dark_mode(self, on):
        if self.is_os_windows and self.is_dark_mode_supported:
            try:
                self.is_dark_mode_supported = set_immersive_dark_mode(
                    window=self,
                    function=self.dwm_set_window_attribute,
                    attribute=self.dwnwa_use_immersive_dark_mode,
                    enabled=on,
                )
            except (ctypes.ArgumentError, OSError, OverflowError, ValueError):
                # Native title-bar theming is cosmetic and must never block startup.
                self.is_dark_mode_supported = False
            # to force redraw of title bar
            self.resize(self.width(), self.height() + 1)
            self.resize(self.width(), self.height() - 1)
