import ctypes
import time

import win32con
import win32gui
from PyQt6.QtCore import QObject, pyqtSignal


class WindowMonitor(QObject):
    windows_updated = pyqtSignal(list)

    def __init__(self):
        super().__init__()
        self.running = True
        self.current_windows = set()
        self.dwmapi = ctypes.windll.dwmapi

    def stop(self):
        self.running = False

    def run(self):
        while self.running:
            windows = []
            win32gui.EnumWindows(self._enum_windows_callback, windows)
            window_set = set(tuple(item) for item in windows)
            if window_set != self.current_windows:
                self.current_windows = window_set
                self.windows_updated.emit([list(item) for item in window_set])
            time.sleep(1)

    def _enum_windows_callback(self, hwnd, windows):
        if not win32gui.IsWindowVisible(hwnd):
            return True
        if not win32gui.GetWindowText(hwnd):
            return True
        if win32gui.GetParent(hwnd) != 0:
            return True
        style = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
        if not (style & win32con.WS_EX_APPWINDOW):
            if style & win32con.WS_EX_TOOLWINDOW:
                return True
        is_cloaked = ctypes.c_int(0)
        self.dwmapi.DwmGetWindowAttribute(hwnd, 14, ctypes.byref(is_cloaked), ctypes.sizeof(is_cloaked))
        if is_cloaked.value != 0:
            return True
        is_foreground = hwnd == win32gui.GetForegroundWindow()
        if is_foreground:
            return True
        title = win32gui.GetWindowText(hwnd)
        windows.append([hwnd, title])
        return True
