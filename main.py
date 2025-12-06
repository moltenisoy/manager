import sys

from PyQt6.QtCore import QThread
from PyQt6.QtWidgets import QApplication

from hook_manager import HookManager
from thumbnail_manager import ThumbnailManager
from window_monitor import WindowMonitor


def main():
    app = QApplication(sys.argv)
    hook_manager = HookManager()
    thumbnail_manager = ThumbnailManager(hook_manager)
    hook_manager.toggle_visibility.connect(thumbnail_manager.toggle_visibility)
    hook_manager.enable()
    monitor_thread = QThread()
    window_monitor = WindowMonitor()
    window_monitor.moveToThread(monitor_thread)
    monitor_thread.started.connect(window_monitor.run)
    window_monitor.windows_updated.connect(thumbnail_manager.update_windows)
    app.aboutToQuit.connect(window_monitor.stop)
    app.aboutToQuit.connect(monitor_thread.quit)
    app.aboutToQuit.connect(monitor_thread.wait)
    app.aboutToQuit.connect(hook_manager.disable)
    monitor_thread.start()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
