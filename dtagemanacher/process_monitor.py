import psutil
from typing import List, Callable, Optional, Set
from types_def import ProcessInfo, ProcessType
import threading
import time
import os
import sys
import window_helper

PROCESS_ICONS = {
    "python": "🐍", "code": "💻", "chrome": "🌐", "firefox": "🦊",
    "spotify": "🎵", "vlc": "🎬", "discord": "💬", "explorer": "📁",
    "notepad": "📝", "calculator": "🔢"
}

def get_process_icon(name: str) -> str:
    name_lower = name.lower()
    for key, icon in PROCESS_ICONS.items():
        if key in name_lower:
            return icon
    return "📱"

def get_process_type(name: str) -> ProcessType:
    name_lower = name.lower()
    if any(x in name_lower for x in ["chrome", "firefox", "edge", "opera"]):
        return ProcessType.WEB
    if any(x in name_lower for x in ["word", "excel", "notepad", "pdf"]):
        return ProcessType.DOCUMENT
    return ProcessType.APP

class ProcessMonitor:
    _instance: Optional['ProcessMonitor'] = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized: return
        self._processes: List[ProcessInfo] = []
        self._listeners: List[Callable[[List[ProcessInfo]], None]] = []
        self._blacklist: Set[str] = set()
        self._refresh_interval: float = 3.0
        self._running: bool = False
        self._monitor_thread: Optional[threading.Thread] = None
        self._initialized = True
        self._own_pid = os.getpid()
        
    @classmethod
    def get_instance(cls) -> 'ProcessMonitor':
        return cls()
    
    def refresh_processes(self):
        new_processes: List[ProcessInfo] = []
        
        windows = window_helper.get_real_windows()
        script_name = os.path.basename(sys.argv[0])
        
        for hwnd, title, pid in windows:
            if pid == self._own_pid:
                continue
                
            if "Visual Settings" in title:
                continue
            
            # Heuristic to avoid showing the console window running this script
            # Checks if title contains python and the script name
            if "python" in title.lower() and script_name in title:
                continue

            try:
                proc = psutil.Process(pid)
                name = proc.name()
                
                if name.lower() in self._blacklist:
                    continue

                try:
                    mem_info = proc.memory_info()
                    memory_mb = mem_info.rss / (1024 * 1024)
                except:
                    memory_mb = 0.0
                
                screenshot = window_helper.capture_window(hwnd, width=400, height=300)
                
                p_info = ProcessInfo(
                    pid=pid,
                    hwnd=hwnd,
                    name=name,
                    title=title,
                    memory_mb=round(memory_mb, 1),
                    process_type=get_process_type(name),
                    icon=get_process_icon(name),
                    image=screenshot,
                    cpu_percent=0.0
                )
                new_processes.append(p_info)
                
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
                
        self._processes = new_processes
        self._notify_listeners()
    
    def get_processes(self) -> List[ProcessInfo]:
        return self._processes
    
    def subscribe(self, listener):
        self._listeners.append(listener)
        return lambda: self._listeners.remove(listener) if listener in self._listeners else None
    
    def _notify_listeners(self):
        for listener in self._listeners:
            try:
                listener(self._processes)
            except Exception:
                pass
    
    def kill_process(self, pid: int) -> bool:
        try:
            psutil.Process(pid).terminate()
            time.sleep(0.5)
            self.refresh_processes()
            return True
        except:
            return False
    
    def start_auto_refresh(self, interval: float = 3.0):
        if self._running: return
        self._refresh_interval = interval
        self._running = True
        
        def refresh_loop():
            while self._running:
                self.refresh_processes()
                for _ in range(int(self._refresh_interval * 10)):
                    if not self._running: break
                    time.sleep(0.1)
        
        self._monitor_thread = threading.Thread(target=refresh_loop, daemon=True)
        self._monitor_thread.start()
    
    def stop_auto_refresh(self):
        self._running = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=1.0)

def get_process_monitor() -> ProcessMonitor:
    return ProcessMonitor.get_instance()