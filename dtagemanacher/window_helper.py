import ctypes
from ctypes import wintypes
import win32gui
import win32con
import win32ui
import win32process
from PIL import Image

dwmapi = ctypes.windll.dwmapi

def is_window_cloaked(hwnd):
    is_cloaked = ctypes.c_int(0)
    try:
        dwmapi.DwmGetWindowAttribute(hwnd, 14, ctypes.byref(is_cloaked), ctypes.sizeof(is_cloaked))
        return is_cloaked.value != 0
    except:
        return False

def get_real_windows():
    windows = []
    
    def enum_cb(hwnd, results):
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
                
        if is_window_cloaked(hwnd):
            return True
            
        title = win32gui.GetWindowText(hwnd)
        try:
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            results.append((hwnd, title, pid))
        except:
            pass
        return True

    win32gui.EnumWindows(enum_cb, windows)
    return windows

def capture_window(hwnd, width=None, height=None):
    try:
        if not win32gui.IsWindow(hwnd):
            return None

        # Get window dimensions
        rect = win32gui.GetWindowRect(hwnd)
        w = rect[2] - rect[0]
        h = rect[3] - rect[1]
        
        if w <= 0 or h <= 0:
            return None

        hwnd_dc = win32gui.GetWindowDC(hwnd)
        mfc_dc = win32ui.CreateDCFromHandle(hwnd_dc)
        save_dc = mfc_dc.CreateCompatibleDC()
        
        save_bitmap = win32ui.CreateBitmap()
        save_bitmap.CreateCompatibleBitmap(mfc_dc, w, h)
        save_dc.SelectObject(save_bitmap)
        
        # MODIFICADO: Se usa el flag 3 (PW_CLIENTONLY | PW_RENDERFULLCONTENT) 
        # como se vio en thumbnail_widget.py para capturar contenido real de minimizadas.
        result = ctypes.windll.user32.PrintWindow(hwnd, save_dc.GetSafeHdc(), 3)
        
        if result != 1:
            # Fallback to BitBlt
            save_dc.BitBlt((0, 0), (w, h), mfc_dc, (0, 0), win32con.SRCCOPY)

        bmpinfo = save_bitmap.GetInfo()
        bmpstr = save_bitmap.GetBitmapBits(True)
        
        im = Image.frombuffer(
            'RGB',
            (bmpinfo['bmWidth'], bmpinfo['bmHeight']),
            bmpstr, 'raw', 'BGRX', 0, 1
        )

        win32gui.DeleteObject(save_bitmap.GetHandle())
        save_dc.DeleteDC()
        mfc_dc.DeleteDC()
        win32gui.ReleaseDC(hwnd, hwnd_dc)
        
        # Resize if requested (optimization)
        if width and height:
            im.thumbnail((width, height), Image.Resampling.LANCZOS)
            
        return im
        
    except Exception:
        return None