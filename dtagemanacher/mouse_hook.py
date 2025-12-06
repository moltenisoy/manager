import time
import threading
from pynput import mouse

class MouseHook:
    def __init__(self, on_double_click_callback):
        self.callback = on_double_click_callback
        self.last_click_time = 0
        self.listener = None
        self.running = False
        self._lock = threading.Lock()

    def start(self):
        if self.running: return
        self.running = True
        self.listener = mouse.Listener(on_click=self._on_click)
        self.listener.start()

    def stop(self):
        self.running = False
        if self.listener:
            self.listener.stop()

    def _on_click(self, x, y, button, pressed):
        if not self.running: return False
        
        if button == mouse.Button.middle and pressed:
            current_time = time.time()
            if current_time - self.last_click_time < 0.5:
                if self.callback:
                    self.callback()
                self.last_click_time = 0 
            else:
                self.last_click_time = current_time