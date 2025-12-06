import os
import ctypes
from ctypes import wintypes
import win32gui
import win32con
import win32ui
import win32process
import psutil
from PyQt6.QtWidgets import QWidget, QLabel, QVBoxLayout, QApplication
from PyQt6.QtCore import Qt, QTimer, QPoint, QPropertyAnimation, QEasingCurve, QRect, pyqtSignal, QSize
from PyQt6.QtGui import QPixmap, QImage, QMouseEvent, QFont, QPainter, QColor
from PIL import Image

class RECT(wintypes.RECT):
    pass

class DWM_THUMBNAIL_PROPERTIES(ctypes.Structure):
    _fields_ = [
        ('dwFlags', wintypes.DWORD),
        ('rcDestination', RECT),
        ('rcSource', RECT),
        ('opacity', ctypes.c_ubyte),
        ('fVisible', wintypes.BOOL),
        ('fSourceClientAreaOnly', wintypes.BOOL)
    ]

class FloatingNameLabel(QWidget):
    def __init__(self, text="", parent=None):
        super().__init__(parent=None)  # top-level, independiente
        self._text = text
        self._font = QFont("Arial", 10)
        self._color = "#FFFFFF"
        self._position = "right"  # right | top | bottom
        self._distance = 15
        self._horizontal_offset = 0  # NUEVO: desplazamiento horizontal para top/bottom
        self._anchor_widget = parent  # widget de miniatura a seguir
        self._label = QLabel(self)
        self._label.setStyleSheet("background: transparent;")
        self._label.setText(self._text)
        self._label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._label.setFont(self._font)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self._apply_color()
        self._update_size()

    def _apply_color(self):
        self._label.setStyleSheet(f"color: {self._color}; background: transparent;")

    def _update_size(self):
        # Ajuste al contenido
        self._label.adjustSize()
        pad_w = 8
        pad_h = 4
        self.resize(self._label.width() + pad_w, self._label.height() + pad_h)
        self._label.move((self.width() - self._label.width()) // 2, (self.height() - self._label.height()) // 2)

    def set_text(self, text):
        self._text = text
        self._label.setText(text)
        self._update_size()
        self.update_position()

    def set_font(self, font: QFont, size_pt: int | None = None):
        f = QFont(font)
        if size_pt is not None and size_pt > 0:
            f.setPointSize(size_pt)
        self._font = f
        self._label.setFont(self._font)
        self._update_size()
        self.update_position()

    def set_color(self, color: str):
        self._color = color
        self._apply_color()
        self.update()

    def set_position(self, position: str):
        # "right" | "top" | "bottom"
        self._position = position
        self.update_position()

    def set_distance(self, distance: int):
        self._distance = max(0, int(distance))
        self.update_position()

    def set_horizontal_offset(self, offset: int):
        self._horizontal_offset = int(offset)
        self.update_position()

    def set_anchor(self, widget: QWidget | None):
        self._anchor_widget = widget
        self.update_position()

    def update_position(self):
        if not self._anchor_widget or not self._anchor_widget.isVisible():
            return
        geom = self._anchor_widget.geometry()
        gp = self._anchor_widget.mapToGlobal(QPoint(0, 0))
        anchor_rect = QRect(gp.x(), gp.y(), geom.width(), geom.height())

        x = anchor_rect.x()
        y = anchor_rect.y()

        if self._position == "right":
            x = anchor_rect.right() + 1 + self._distance
            y = anchor_rect.center().y() - (self.height() // 2)
        elif self._position == "top":
            x = anchor_rect.center().x() - (self.width() // 2) + self._horizontal_offset
            y = anchor_rect.top() - self.height() - self._distance
        else:  # "bottom"
            x = anchor_rect.center().x() - (self.width() // 2) + self._horizontal_offset
            y = anchor_rect.bottom() + 1 + self._distance

        self.move(x, y)

class ThumbnailWidget(QWidget):
    wants_to_be_removed = pyqtSignal(int)
    rightClicked = pyqtSignal()
    requestExclusiveMode = pyqtSignal(int)
    requestExitExclusiveMode = pyqtSignal()

    def __init__(self, hwnd, title, method=1, parent=None):
        super().__init__(parent)
        self.hwnd = hwnd
        self.title_text = title
        self.method = method
        self.is_setup = False
        self.thumbnail_handle = ctypes.c_void_p()
        self.dwmapi = ctypes.windll.dwmapi
        self.user32 = ctypes.windll.user32
        self.enter_animation = None
        self.exit_animation = None
        self.geometry_animation = None
        self.hover_animation = None
        self.is_pinned = False
        self._original_size = QSize(220, 165)
        self._border_enabled = False
        self._border_width = 2
        self._border_color = "#0078D7"
        self.exclusive_mode = False
        self._moving = False
        self._press_pos = QPoint()
        self._press_geo = QRect()
        self.long_press_timer = QTimer(self)
        self.long_press_timer.setSingleShot(True)
        self.long_press_timer.setInterval(700)
        self.long_press_timer.timeout.connect(self._on_long_press_timeout)

        # Geometría base para hover-zoom robusto
        self._layout_target_geometry = QRect()
        self._base_geometry = QRect()
        self._hovering = False

        # Hover zoom
        self._hover_animation_enabled = True
        self._hover_animation_intensity = 1.15

        # Nombre flotante independiente
        self._name_enabled = False
        self._name_position = "right"
        self._name_font = QFont("Arial", 10)
        self._name_color = "#FFFFFF"
        self._name_text_size = 10
        self._name_distance = 15
        self._name_horizontal_offset = 0          # NUEVO
        self._name_content_mode = "full"          # NUEVO: "full" | "app"
        self._name_widget = FloatingNameLabel(self.title_text, parent=self)
        self._name_widget.hide()

        try:
            self.pid = win32process.GetWindowThreadProcessId(self.hwnd)[1]
            self.process = psutil.Process(self.pid)
        except:
            self.pid = 0
            self.process = None
        
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setMouseTracking(True)
        
        # Contenedor de miniatura
        self.thumbnail_container = QWidget(self)
        self.thumbnail_layout = QVBoxLayout(self.thumbnail_container)
        self.thumbnail_layout.setContentsMargins(0, 0, 0, 0)
        
        self.thumbnail_label = QLabel()
        self.thumbnail_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.thumbnail_layout.addWidget(self.thumbnail_label)

        # Layout externo
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.addWidget(self.thumbnail_container)
        
        # Estilo de borde
        self._update_border_style()
        
        self.close_button = None

    # ---- Helpers nombre/app ----
    def get_process_name(self):
        if self.process:
            return self.process.name()
        return "Unknown"

    def _get_app_short_name(self) -> str:
        # "notepad.exe" -> "notepad"
        name = self.get_process_name()
        base = os.path.splitext(name)[0]
        return base or name or (self.title_text or "")

    def _resolve_label_text(self) -> str:
        return self.title_text if self._name_content_mode == "full" else self._get_app_short_name()

    # ---- Nombre flotante API (globalmente ajustado por el Manager) ----
    def set_name_enabled(self, enabled: bool):
        self._name_enabled = enabled
        if enabled and self.isVisible():
            self._name_widget.set_text(self._resolve_label_text())
            self._name_widget.show()
            self._name_widget.update_position()
        else:
            self._name_widget.hide()

    def set_name_position(self, position: str):
        # "right" | "top" | "bottom"
        self._name_position = position
        self._name_widget.set_position(position)
        if self._name_enabled:
            self._name_widget.update_position()

    def set_name_font(self, font: QFont, size_pt: int):
        self._name_font = QFont(font)
        self._name_text_size = size_pt
        self._name_widget.set_font(self._name_font, self._name_text_size)
        if self._name_enabled:
            self._name_widget.update_position()

    def set_name_color(self, color: str):
        self._name_color = color
        self._name_widget.set_color(color)

    def set_name_distance(self, distance: int):
        self._name_distance = distance
        self._name_widget.set_distance(distance)

    def set_name_horizontal_offset(self, offset: int):
        self._name_horizontal_offset = int(offset)
        self._name_widget.set_horizontal_offset(self._name_horizontal_offset)

    def set_name_content_mode(self, mode: str):
        # mode: "full" | "app"
        self._name_content_mode = mode if mode in ("full", "app") else "full"
        if self._name_enabled:
            self._name_widget.set_text(self._resolve_label_text())

    def set_title(self, title: str):
        self.title_text = title or ""
        # Actualizar texto solo si el modo es "full"
        if self._name_content_mode == "full":
            self._name_widget.set_text(self.title_text)

    # ---------------------------------------------------------------

    def set_border(self, enabled, width, color):
        self._border_enabled = enabled
        self._border_width = width
        self._border_color = color
        self._update_border_style()

    def _update_border_style(self):
        if not hasattr(self, 'thumbnail_container'):
            return
        if self._border_enabled:
            self.thumbnail_container.setStyleSheet(f"background-color: rgba(1, 2, 3, 1); border: {self._border_width}px solid {self._border_color};")
        else:
            self.thumbnail_container.setStyleSheet("background-color: rgba(1, 2, 3, 1);")

    def set_base_size(self, width):
        ar = 0.75
        height = int(width * ar)
        self._original_size = QSize(width, height)

    def sizeHint(self):
        # El nombre flotante no afecta el tamaño de la miniatura
        return QSize(self._original_size)

    def set_layout_target_geometry(self, geom: QRect):
        self._layout_target_geometry = QRect(geom)
        self._base_geometry = QRect(geom)
        # Si no hay hover activo, actualizamos geometría
        if not self._hovering:
            self.setGeometry(geom)
        # Asegurar actualización de la posición del nombre
        if self._name_enabled:
            self._name_widget.update_position()

    def enter_exclusive_mode(self):
        self.exclusive_mode = True
        self.is_pinned = True
        self._moving = False
        # En modo exclusivo, desactivar hover para evitar que fuerce retorno de geometría
        self._hovering = False
        # Guardar la geometría base actual para poder restaurar correctamente
        if not self.geometry().isNull():
            self._base_geometry = QRect(self.geometry())

    def exit_exclusive_mode(self):
        self.exclusive_mode = False
        self.is_pinned = False
        self._moving = False
        self.setCursor(Qt.CursorShape.ArrowCursor)

    # ----------------- Eventos de widget -----------------
    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.isVisible() and self.method == 1:
            self.update_dwm_thumbnail()
        if self._name_enabled:
            self._name_widget.update_position()

    def moveEvent(self, event):
        super().moveEvent(event)
        if self._name_enabled:
            self._name_widget.update_position()

    def showEvent(self, event):
        super().showEvent(event)
        if not self.is_setup:
            if self.method == 1:
                self._setup_dwm_thumbnail()
            else:
                self.timer = QTimer(self)
                self.timer.timeout.connect(self.update_thumbnail_capture)
                self.timer.start(100)
            self.is_setup = True
        if self.method == 1:
            self.update_dwm_thumbnail()
        # Mostrar/posicionar nombre flotante si corresponde
        self._name_widget.set_anchor(self)
        if self._name_enabled:
            self._name_widget.set_text(self._resolve_label_text())
            self._name_widget.update_position()
            self._name_widget.show()

    def hideEvent(self, event):
        # Ocultar nombre flotante también
        if self._name_widget.isVisible():
            self._name_widget.hide()
        super().hideEvent(event)

    def closeEvent(self, event):
        if self.method == 1 and self.thumbnail_handle.value:
            self.dwmapi.DwmUnregisterThumbnail(self.thumbnail_handle)
        elif self.method in [2, 3] and hasattr(self, 'timer'):
            self.timer.stop()
        if self.hover_animation is not None:
            self.hover_animation.stop()
        super().closeEvent(event)

    # ----------------- Interacción de ratón -----------------
    def mouseDoubleClickEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            if self.exclusive_mode:
                self.requestExitExclusiveMode.emit()
                event.accept()
                return
            if win32gui.IsIconic(self.hwnd):
                win32gui.ShowWindow(self.hwnd, win32con.SW_RESTORE)
            win32gui.SetForegroundWindow(self.hwnd)
            self.wants_to_be_removed.emit(self.hwnd)
            event.accept()

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            if self.exclusive_mode:
                self._press_pos = event.globalPosition().toPoint()
                self._press_geo = self.geometry()
                self._moving = True
            else:
                self.long_press_timer.start()
        event.accept()

    def mouseMoveEvent(self, event: QMouseEvent):
        if self.exclusive_mode and self._moving:
            pos_global = event.globalPosition().toPoint()
            delta = pos_global - self._press_pos
            self.move(self._press_geo.topLeft() + delta)
            event.accept()
            return
        event.accept()

    def mouseReleaseEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.RightButton:
            self.rightClicked.emit()
            event.accept()
            return
        if event.button() == Qt.MouseButton.LeftButton:
            self.long_press_timer.stop()
            if self.exclusive_mode and self._moving:
                self._moving = False
                # Fijar la nueva geometría como base para que no vuelva a la anterior
                self._base_geometry = QRect(self.geometry())
            event.accept()

    def _on_long_press_timeout(self):
        self.requestExclusiveMode.emit(self.hwnd)

    # ----------------- Hover zoom robusto -----------------
    def set_hover_animation_enabled(self, enabled):
        self._hover_animation_enabled = enabled

    def set_hover_animation_intensity(self, intensity):
        self._hover_animation_intensity = max(1.0, float(intensity))

    def enterEvent(self, event):
        super().enterEvent(event)
        # En modo exclusivo no aplicamos hover para no alterar la posición fijada
        if self.exclusive_mode or not self._hover_animation_enabled:
            return
        self._start_hover_zoom()

    def leaveEvent(self, event):
        super().leaveEvent(event)
        if self.exclusive_mode or not self._hover_animation_enabled:
            return
        self._stop_hover_zoom_to_base()

    def _start_hover_zoom(self):
        # Asegurar base geom bien definida
        if not self._layout_target_geometry.isNull():
            self._base_geometry = QRect(self._layout_target_geometry)
        else:
            self._base_geometry = QRect(self.geometry())

        factor = float(self._hover_animation_intensity)
        base = self._base_geometry
        nw = int(base.width() * factor)
        nh = int(base.height() * factor)
        cx = base.center().x()
        cy = base.center().y()
        target = QRect(int(cx - nw / 2), int(cy - nh / 2), nw, nh)

        if self.hover_animation is None:
            self.hover_animation = QPropertyAnimation(self, b"geometry")
            self.hover_animation.setDuration(160)
            self.hover_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.hover_animation.stop()
        self._hovering = True
        self.raise_()
        self.hover_animation.setStartValue(self.geometry())
        self.hover_animation.setEndValue(target)
        self.hover_animation.start()

    def _stop_hover_zoom_to_base(self):
        # Volver SIEMPRE a la geometría base conocida
        target = QRect(self._base_geometry) if not self._base_geometry.isNull() else QRect(self.geometry())

        if self.hover_animation is None:
            self.hover_animation = QPropertyAnimation(self, b"geometry")
            self.hover_animation.setDuration(140)
            self.hover_animation.setEasingCurve(QEasingCurve.Type.InOutQuad)
        else:
            self.hover_animation.stop()
            self.hover_animation.setDuration(140)
            self.hover_animation.setEasingCurve(QEasingCurve.Type.InOutQuad)

        self.hover_animation.setStartValue(self.geometry())
        self.hover_animation.setEndValue(target)
        self.hover_animation.finished.connect(self._on_hover_return_finished)
        self.hover_animation.start()

    def _on_hover_return_finished(self):
        # Garantiza estado coherente post-retorno
        self._hovering = False
        # Limpiar conexiones duplicadas
        try:
            self.hover_animation.finished.disconnect(self._on_hover_return_finished)
        except Exception:
            pass
        # Alinear exactamente a la base
        if not self._base_geometry.isNull():
            self.setGeometry(self._base_geometry)

    # Método para que el manager garantice que no queda fuera de pantalla al volver a mostrar
    def ensure_visible_geometry(self):
        if not self._base_geometry.isNull():
            self.setGeometry(self._base_geometry)

    # ----------------- Métodos de captura/render -----------------
    def _setup_dwm_thumbnail(self):
        if self.dwmapi.DwmRegisterThumbnail(int(self.winId()), self.hwnd, ctypes.byref(self.thumbnail_handle)) != 0:
            self.method = 2
            self.timer = QTimer(self)
            self.timer.timeout.connect(self.update_thumbnail_capture)
            self.timer.start(100)

    def update_dwm_thumbnail(self):
        if self.thumbnail_handle.value:
            dest_rect = self.thumbnail_label.rect()
            props = DWM_THUMBNAIL_PROPERTIES()
            props.dwFlags = 0x00000001 | 0x00000004 | 0x00000008 | 0x00000010
            props.rcDestination = RECT(dest_rect.left(), dest_rect.top(), dest_rect.right(), dest_rect.bottom())
            props.fVisible = True
            props.opacity = 255
            props.fSourceClientAreaOnly = wintypes.BOOL(True)
            self.dwmapi.DwmUpdateThumbnailProperties(self.thumbnail_handle, ctypes.byref(props))

    def update_thumbnail_capture(self):
        if self.method == 2:
            self._update_with_printwindow()
        elif self.method == 3:
            self._update_with_bitblt()

    def _capture_window(self, method_func):
        if not win32gui.IsWindow(self.hwnd):
            return
        rect = win32gui.GetClientRect(self.hwnd)
        w = rect[2] - rect[0]
        h = rect[3] - rect[1]
        if w <= 0 or h <= 0:
            return
        hwnd_dc = win32gui.GetWindowDC(self.hwnd)
        mfc_dc = win32ui.CreateDCFromHandle(hwnd_dc)
        save_dc = mfc_dc.CreateCompatibleDC()
        save_bitmap = win32ui.CreateBitmap()
        save_bitmap.CreateCompatibleBitmap(mfc_dc, w, h)
        save_dc.SelectObject(save_bitmap)
        method_func(save_dc, w, h)
        bmpinfo = save_bitmap.GetInfo()
        bmpstr = save_bitmap.GetBitmapBits(True)
        im = Image.frombuffer('RGB', (bmpinfo['bmWidth'], bmpinfo['bmHeight']), bmpstr, 'raw', 'BGRX', 0, 1)
        qimage = QImage(im.tobytes(), im.width, im.height, QImage.Format.Format_RGB888).rgbSwapped()
        pixmap = QPixmap.fromImage(qimage)
        self.thumbnail_label.setPixmap(pixmap.scaled(self.thumbnail_label.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        win32gui.DeleteObject(save_bitmap.GetHandle())
        save_dc.DeleteDC()
        mfc_dc.DeleteDC()
        win32gui.ReleaseDC(self.hwnd, hwnd_dc)

    def _update_with_printwindow(self):
        self._capture_window(lambda save_dc, w, h: self.user32.PrintWindow(self.hwnd, save_dc.GetSafeHdc(), 3))

    def _update_with_bitblt(self):
        self._capture_window(lambda save_dc, w, h: save_dc.BitBlt((0, 0), (w, h), win32ui.CreateDCFromHandle(win32gui.GetWindowDC(self.hwnd)), (0, 0), win32con.SRCCOPY))

    # ----------------- Animaciones de entrada/geometría/salida -----------------
    def animate_enter_diagonal(self, start_pos, end_pos):
        if self.enter_animation is None:
            self.enter_animation = QPropertyAnimation(self, b"pos")
            self.enter_animation.setDuration(320)
            self.enter_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.enter_animation.stop()
        self.enter_animation.setStartValue(start_pos)
        self.enter_animation.setEndValue(end_pos)
        self.enter_animation.start()

    def animate_exit_left(self, start_pos, end_pos, on_finish=None):
        if self.exit_animation is None:
            self.exit_animation = QPropertyAnimation(self, b"pos")
            self.exit_animation.setDuration(300)
            self.exit_animation.setEasingCurve(QEasingCurve.Type.OutQuad)
        self.exit_animation.stop()
        self.exit_animation.setStartValue(start_pos)
        self.exit_animation.setEndValue(end_pos)
        if on_finish:
            try:
                self.exit_animation.finished.disconnect(on_finish)
            except Exception:
                pass
            self.exit_animation.finished.connect(on_finish)
        self.exit_animation.start()

    def animate_geometry(self, start_geometry, end_geometry):
        self._layout_target_geometry = QRect(end_geometry)
        self._base_geometry = QRect(end_geometry)
        if self.geometry_animation is None:
            self.geometry_animation = QPropertyAnimation(self, b"geometry")
            self.geometry_animation.setDuration(120)
            self.geometry_animation.setEasingCurve(QEasingCurve.Type.InOutQuad)
        self.geometry_animation.stop()
        if start_geometry == end_geometry:
            self.setGeometry(end_geometry)
            return
        self.geometry_animation.setStartValue(start_geometry)
        self.geometry_animation.setEndValue(end_geometry)
        self.geometry_animation.start()