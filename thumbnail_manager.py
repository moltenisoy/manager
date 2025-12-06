import os
import subprocess
import psutil
import win32process
from PyQt6.QtCore import QObject, pyqtSlot, QPoint, QRect
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QFont
from thumbnail_widget import ThumbnailWidget
from settings_panel import SettingsPanel

class ThumbnailManager(QObject):
    def __init__(self, hook_manager):
        super().__init__()
        self.hook_manager = hook_manager
        self.thumbnails = {}
        self.is_visible = False
        self.y_spacing = 15
        self.x_offset = 15
        self.render_method = 1
        self.base_thumbnail_width = 220
        self.animations_enabled = True
        self.border_enabled = False
        self.border_width = 2
        self.border_color = "#0078D7"
        self.exclusive_hwnd = None

        # Hover zoom animation
        self.hover_animation_enabled = True
        self.hover_animation_intensity = 1.15

        # Nombre flotante independiente (global)
        self.name_enabled = False
        self.name_position = "right"  # right | top | bottom
        self.name_font = QFont("Arial", 10)
        self.name_color = "#FFFFFF"
        self.name_text_size = 10      # pt
        self.name_distance = 15       # px
        self.name_horizontal_offset = 0  # NUEVO: desplazamiento horizontal para top/bottom
        self.name_content_mode = "full"  # NUEVO: "full" | "app"

        self.ignored_exe_names = set()
        
        self.settings_panel = SettingsPanel()
        self.settings_panel.closeApp.connect(self.force_quit_app)
        self.settings_panel.distanceChanged.connect(self._set_screen_distance)
        self.settings_panel.spacingChanged.connect(self._set_vertical_spacing)
        self.settings_panel.thumbnailSizeChanged.connect(self._set_thumbnail_size)
        self.settings_panel.animationsEnabledChanged.connect(self._set_animations_enabled)
        self.settings_panel.borderEnabledChanged.connect(self._set_border_enabled)
        self.settings_panel.borderWidthChanged.connect(self._set_border_width)
        self.settings_panel.borderColorChanged.connect(self._set_border_color)
        self.settings_panel.autostartChanged.connect(self._set_autostart)

        # Hover (solo zoom)
        self.settings_panel.hoverAnimationEnabledChanged.connect(self._set_hover_animation_enabled)
        self.settings_panel.hoverAnimationIntensityChanged.connect(self._set_hover_animation_intensity)

        # Configuración de nombre flotante
        self.settings_panel.labelEnabledChanged.connect(self._set_label_enabled)
        self.settings_panel.labelPositionChanged.connect(self._set_label_position)
        self.settings_panel.labelFontChanged.connect(self._set_label_font)
        self.settings_panel.labelColorChanged.connect(self._set_label_color)
        self.settings_panel.labelTextSizeChanged.connect(self._set_label_text_size)
        self.settings_panel.labelDistanceChanged.connect(self._set_label_distance)
        self.settings_panel.labelHorizontalOffsetChanged.connect(self._set_label_horizontal_offset)  # NUEVO
        self.settings_panel.labelContentModeChanged.connect(self._set_label_content_mode)            # NUEVO

        self.settings_panel.ignoreListChanged.connect(self._set_ignore_list)

    @pyqtSlot()
    def force_quit_app(self):
        os._exit(0)

    @pyqtSlot()
    def toggle_visibility(self):
        self.is_visible = not self.is_visible
        if self.is_visible:
            if self.exclusive_hwnd is None:
                self._update_layout(is_appearing=True)
            self._raise_thumbnails()
            if self.exclusive_hwnd is not None:
                sel = self.thumbnails.get(self.exclusive_hwnd)
                if sel:
                    if hasattr(sel, "ensure_visible_geometry"):
                        sel.ensure_visible_geometry()
                    sel.show()
                    sel.raise_()
        else:
            pinned_widget = self.thumbnails.get(self.exclusive_hwnd) if self.exclusive_hwnd is not None else None
            for widget in self.thumbnails.values():
                if widget.isVisible():
                    if pinned_widget is not None and widget is pinned_widget:
                        widget.hide()
                        continue
                    if self.animations_enabled and hasattr(widget, "animate_exit_left"):
                        start_pos = widget.pos()
                        end_pos = QPoint(-widget.width(), start_pos.y())
                        widget.animate_exit_left(start_pos, end_pos, on_finish=widget.hide)
                    else:
                        widget.hide()

    def _raise_thumbnails(self):
        for w in self.thumbnails.values():
            if w.isVisible():
                w.raise_()

    def _get_exe_name_for_hwnd(self, hwnd):
        try:
            pid = win32process.GetWindowThreadProcessId(hwnd)[1]
            return psutil.Process(pid).name().lower()
        except:
            return ""

    @pyqtSlot(list)
    def update_windows(self, windows):
        filtered = []
        for hwnd, title in windows:
            if not title:
                continue
            ex = self._get_exe_name_for_hwnd(hwnd)
            if ex in self.ignored_exe_names:
                continue
            filtered.append([hwnd, title])

        new_hwnds = {hwnd for hwnd, title in filtered}
        current_hwnds = set(self.thumbnails.keys())
        to_add = new_hwnds - current_hwnds
        to_remove = current_hwnds - new_hwnds

        # Crear las nuevas miniaturas
        for hwnd, title in filtered:
            if hwnd in to_add:
                widget = ThumbnailWidget(hwnd, title, method=self.render_method)
                widget.set_base_size(self.base_thumbnail_width)
                widget.set_border(self.border_enabled, self.border_width, self.border_color)

                # Hover (solo zoom)
                widget.set_hover_animation_enabled(self.hover_animation_enabled)
                widget.set_hover_animation_intensity(self.hover_animation_intensity)

                # Nombre flotante (independiente)
                widget.set_name_enabled(self.name_enabled)
                widget.set_name_position(self.name_position)
                widget.set_name_font(self.name_font, self.name_text_size)
                widget.set_name_color(self.name_color)
                widget.set_name_distance(self.name_distance)
                widget.set_name_horizontal_offset(self.name_horizontal_offset)     # NUEVO
                widget.set_name_content_mode(self.name_content_mode)               # NUEVO

                widget.wants_to_be_removed.connect(self._on_widget_removed)
                widget.rightClicked.connect(self.settings_panel.show)
                widget.requestExclusiveMode.connect(self._on_exclusive_requested)
                widget.requestExitExclusiveMode.connect(self._exit_exclusive_mode)
                self.thumbnails[hwnd] = widget

        # Actualizar títulos de ventanas existentes y eliminar las que ya no están
        remaining_hwnds = new_hwnds & current_hwnds
        for hwnd, title in filtered:
            if hwnd in remaining_hwnds:
                w = self.thumbnails.get(hwnd)
                if w:
                    w.set_title(title)

        for hwnd in list(to_remove):
            if hwnd in self.thumbnails:
                if self.exclusive_hwnd == hwnd:
                    self.exclusive_hwnd = None
                self.thumbnails[hwnd].close()
                del self.thumbnails[hwnd]

        if self.is_visible and self.exclusive_hwnd is None:
            self._update_layout()

    @pyqtSlot(int)
    def _on_widget_removed(self, hwnd):
        if hwnd in self.thumbnails:
            if self.exclusive_hwnd == hwnd:
                self.exclusive_hwnd = None
            w = self.thumbnails[hwnd]
            w.close()
            del self.thumbnails[hwnd]
            if self.is_visible and self.exclusive_hwnd is None:
                self._update_layout()

    def _update_layout(self, is_appearing=False):
        if self.exclusive_hwnd is not None:
            return
        items = [w for w in self.thumbnails.values() if not w.is_pinned]
        if not items:
            return
        screen_rect = QApplication.primaryScreen().geometry()
        screen_height = screen_rect.height()
        base_sizes = [w.sizeHint() for w in items]
        total_base_height = sum(sz.height() for sz in base_sizes)
        n = len(base_sizes)
        total_spacing = self.y_spacing * (n - 1) if n > 0 else 0
        available_height = max(1, screen_height - total_spacing)
        fit_scale = min(1.0, available_height / max(1, total_base_height))
        if fit_scale <= 0:
            fit_scale = 0.1
        scaled_heights = [int(sz.height() * fit_scale) for sz in base_sizes]
        scaled_widths = [int(sz.width() * fit_scale) for sz in base_sizes]
        total_list_height = sum(scaled_heights) + total_spacing
        top_y = int((screen_height - total_list_height) / 2)
        current_y = top_y
        for idx, widget in enumerate(items):
            new_w = max(1, scaled_widths[idx])
            new_h = max(1, scaled_heights[idx])
            target_geometry = QRect(self.x_offset, current_y, new_w, new_h)
            if hasattr(widget, "set_layout_target_geometry"):
                widget.set_layout_target_geometry(target_geometry)
            if is_appearing:
                widget.setGeometry(QRect(target_geometry.x(), target_geometry.y(), target_geometry.width(), target_geometry.height()))
                start_pos = QPoint(-target_geometry.width(), max(0, target_geometry.y() - 60))
                widget.move(start_pos)
                widget.show()
                if self.animations_enabled and hasattr(widget, "animate_enter_diagonal"):
                    widget.animate_enter_diagonal(start_pos, target_geometry.topLeft())
                else:
                    widget.move(target_geometry.topLeft())
            elif self.is_visible:
                widget.show()
                if self.animations_enabled and hasattr(widget, "animate_geometry"):
                    widget.animate_geometry(widget.geometry(), target_geometry)
                else:
                    widget.setGeometry(target_geometry)
            current_y += new_h + self.y_spacing

    @pyqtSlot(int)
    def _on_exclusive_requested(self, hwnd):
        if hwnd not in self.thumbnails:
            return
        self._enter_exclusive_mode(hwnd)

    def _enter_exclusive_mode(self, hwnd):
        self.exclusive_hwnd = hwnd
        for h, w in self.thumbnails.items():
            if h != hwnd:
                w.hide()
        sel = self.thumbnails.get(hwnd)
        if sel:
            sel.enter_exclusive_mode()
            sel.raise_()
            sel.show()
        self.is_visible = True

    @pyqtSlot()
    def _exit_exclusive_mode(self):
        if self.exclusive_hwnd is None:
            return
        sel = self.thumbnails.get(self.exclusive_hwnd)
        if sel:
            sel.exit_exclusive_mode()
        self.exclusive_hwnd = None
        for h, w in self.thumbnails.items():
            w.show() if self.is_visible else w.hide()
        if self.is_visible:
            self._update_layout()

    @pyqtSlot(int)
    def _set_screen_distance(self, value):
        self.x_offset = value
        if self.exclusive_hwnd is None:
            self._update_layout()

    @pyqtSlot(int)
    def _set_vertical_spacing(self, value):
        self.y_spacing = value
        if self.exclusive_hwnd is None:
            self._update_layout()

    @pyqtSlot(int)
    def _set_thumbnail_size(self, width):
        self.base_thumbnail_width = width
        for widget in self.thumbnails.values():
            widget.set_base_size(width)
        if self.exclusive_hwnd is None:
            self._update_layout()

    @pyqtSlot(bool)
    def _set_animations_enabled(self, enabled):
        self.animations_enabled = enabled

    @pyqtSlot(bool)
    def _set_border_enabled(self, enabled):
        self.border_enabled = enabled
        for widget in self.thumbnails.values():
            widget.set_border(enabled, self.border_width, self.border_color)

    @pyqtSlot(int)
    def _set_border_width(self, width):
        self.border_width = width
        for widget in self.thumbnails.values():
            widget.set_border(self.border_enabled, width, self.border_color)

    @pyqtSlot(str)
    def _set_border_color(self, color):
        self.border_color = color
        for widget in self.thumbnails.values():
            widget.set_border(self.border_enabled, self.border_width, color)

    @pyqtSlot(bool)
    def _set_autostart(self, enabled):
        import sys
        script_path = os.path.abspath(sys.argv[0])
        python_path = sys.executable
        if enabled:
            cmd = f'schtasks /create /tn "ThumbnailManager" /tr "\\\"{python_path}\\\" \\\"{script_path}\\\"" /sc onlogon /rl highest /f'
        else:
            cmd = 'schtasks /delete /tn "ThumbnailManager" /f'
        subprocess.run(cmd, shell=True)

    @pyqtSlot(bool)
    def _set_hover_animation_enabled(self, enabled):
        self.hover_animation_enabled = enabled
        for w in self.thumbnails.values():
            w.set_hover_animation_enabled(enabled)

    @pyqtSlot(float)
    def _set_hover_animation_intensity(self, intensity):
        self.hover_animation_intensity = intensity
        for w in self.thumbnails.values():
            w.set_hover_animation_intensity(intensity)

    # Nombre flotante: setters globales que aplican a todas las miniaturas
    @pyqtSlot(bool)
    def _set_label_enabled(self, enabled):
        self.name_enabled = enabled
        for w in self.thumbnails.values():
            w.set_name_enabled(enabled)

    @pyqtSlot(str)
    def _set_label_position(self, position):
        self.name_position = position
        for w in self.thumbnails.values():
            w.set_name_position(position)

    @pyqtSlot(QFont)
    def _set_label_font(self, font):
        self.name_font = font
        for w in self.thumbnails.values():
            w.set_name_font(font, self.name_text_size)

    @pyqtSlot(str)
    def _set_label_color(self, color):
        self.name_color = color
        for w in self.thumbnails.values():
            w.set_name_color(color)

    @pyqtSlot(int)
    def _set_label_text_size(self, size):
        self.name_text_size = size
        for w in self.thumbnails.values():
            w.set_name_font(self.name_font, size)

    @pyqtSlot(int)
    def _set_label_distance(self, distance):
        self.name_distance = distance
        for w in self.thumbnails.values():
            w.set_name_distance(distance)

    @pyqtSlot(int)
    def _set_label_horizontal_offset(self, offset):
        self.name_horizontal_offset = offset
        for w in self.thumbnails.values():
            w.set_name_horizontal_offset(offset)

    @pyqtSlot(str)
    def _set_label_content_mode(self, mode):
        # mode: "full" | "app"
        self.name_content_mode = mode
        for w in self.thumbnails.values():
            w.set_name_content_mode(mode)

    @pyqtSlot(list)
    def _set_ignore_list(self, names):
        self.ignored_exe_names = set(n.lower() for n in names)
        for hwnd, w in list(self.thumbnails.items()):
            ex = w.get_process_name().lower()
            if ex in self.ignored_exe_names:
                if self.exclusive_hwnd == hwnd:
                    self.exclusive_hwnd = None
                w.close()
                del self.thumbnails[hwnd]
        if self.is_visible and self.exclusive_hwnd is None:
            self._update_layout()