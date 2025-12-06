import time

from pynput import mouse as pynput_mouse
from PyQt6.QtCore import QObject, pyqtSignal


class HookManager(QObject):
    toggle_visibility = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.last_click_time = 0
        self.double_click_threshold = 0.3
        self.listener = None

    def _on_click(self, x, y, button, pressed):
        # Cambiado: doble clic del botón central (rueda)
        if button == pynput_mouse.Button.middle and pressed:
            t = time.time()
            if t - self.last_click_time < self.double_click_threshold:
                self.toggle_visibility.emit()
                self.last_click_time = 0
            else:
                self.last_click_time = t

    def enable(self):
        if self.listener is None or not self.listener.is_alive():
            self.listener = pynput_mouse.Listener(on_click=self._on_click)
            self.listener.start()

    def disable(self):
        if self.listener and self.listener.is_alive():
            self.listener.stop()
            self.listener = None
