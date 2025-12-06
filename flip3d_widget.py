import math
import win32gui
import win32con
from PyQt6.QtWidgets import QWidget, QLabel
from PyQt6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, QRect, QPoint, pyqtSignal
from PyQt6.QtGui import QPainter, QColor, QPixmap, QImage, QPen, QPainterPath, QFont, QTransform
from PIL import Image

class ThumbnailCard:
    def __init__(self, hwnd, title, pixmap, memory_mb=0):
        self.hwnd = hwnd
        self.title = title
        self.pixmap = pixmap
        self.memory_mb = memory_mb
        self.x = 0
        self.y = 0
        self.width = 340
        self.height = 260
        self.rotation = 0
        self.scale = 1.0
        self.is_selected = False

class Flip3DWidget(QWidget):
    windowSelected = pyqtSignal(int)
    closeRequested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.cards = []
        self.current_index_float = 0.0
        self.target_index = 0
        self.animating = False
        self.spacing = 150
        self.card_scale = 1.0
        self.animation_speed = 0.1
        self.show_memory = True
        self.show_borders = True
        self.show_titles = True

        self.long_press_timer = QTimer(self)
        self.long_press_timer.setSingleShot(True)
        self.long_press_timer.setInterval(700)
        self.long_press_timer.timeout.connect(self._on_long_press)

        self.exclusive_hwnd = None
        self.exclusive_mode = False
        self.press_pos = QPoint()
        self.press_card_pos = QPoint()
        self.exclusive_geometry = QRect()

        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        self.animation_timer = QTimer(self)
        self.animation_timer.timeout.connect(self._animate_loop)
        self.animation_timer.start(16)

    def set_windows(self, windows_data):
        self.cards = []
        for hwnd, title, pixmap, memory_mb in windows_data:
            card = ThumbnailCard(hwnd, title, pixmap, memory_mb)
            self.cards.append(card)

        if self.target_index >= len(self.cards) and len(self.cards) > 0:
            self.target_index = len(self.cards) - 1
            self.current_index_float = float(self.target_index)
        elif len(self.cards) == 0:
            self.target_index = 0
            self.current_index_float = 0.0

        self.update()

    def set_settings(self, spacing, card_scale, animation_speed, show_memory, show_borders, show_titles):
        self.spacing = spacing
        self.card_scale = card_scale
        self.animation_speed = animation_speed
        self.show_memory = show_memory
        self.show_borders = show_borders
        self.show_titles = show_titles
        self.update()

    def navigate_delta(self, delta):
        if not self.cards or self.exclusive_mode:
            return

        new_idx = self.target_index + delta
        if new_idx < 0:
            new_idx = len(self.cards) - 1
        if new_idx >= len(self.cards):
            new_idx = 0

        self.target_index = new_idx

    def _animate_loop(self):
        diff = self.target_index - self.current_index_float

        if abs(diff) > 0.001:
            self.animating = True
            self.current_index_float += diff * self.animation_speed
            self.update()
        else:
            self.current_index_float = float(self.target_index)
            if self.animating:
                self.animating = False
                self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        painter.fillRect(self.rect(), QColor(0, 0, 0, 0))

        if self.exclusive_mode and self.exclusive_hwnd is not None:
            self._draw_exclusive_mode(painter)
        elif len(self.cards) > 0:
            self._draw_flip3d(painter)

    def _draw_flip3d(self, painter):
        cx = self.width() / 2
        cy = self.height() / 2
        base_w = 340
        base_h = 260

        draw_order = []
        total = len(self.cards)

        for i in range(total):
            dist = i - self.current_index_float
            abs_dist = abs(dist)

            if abs_dist > 6:
                continue

            z_depth = -abs_dist
            draw_order.append((i, dist, z_depth))

        draw_order.sort(key=lambda x: x[2])

        for i, dist, z in draw_order:
            card = self.cards[i]

            scale = max(0.5, 1.0 - (abs(dist) * 0.1)) * self.card_scale
            x = cx + (dist * self.spacing * 0.8)
            y = cy + (abs(dist) * 20)
            rot = -dist * 5
            is_sel = (int(round(self.current_index_float)) == i)

            self._draw_card(painter, card, x, y, base_w, base_h, scale, rot, is_sel)

    def _draw_card(self, painter, card, x, y, base_w, base_h, scale, rotation, is_selected):
        w = base_w * scale
        h = base_h * scale

        painter.save()
        painter.translate(x, y)
        painter.rotate(rotation)

        if self.show_borders:
            bg_color = QColor(45, 90, 123) if is_selected else QColor(26, 31, 58)
            border_color = QColor(77, 212, 232) if is_selected else QColor(58, 64, 112)
            border_width = 3 if is_selected else 1

            rect = QRect(-w/2, -h/2, w, h)
            path = QPainterPath()
            path.addRoundedRect(rect, 12 * scale, 12 * scale)

            painter.fillPath(path, bg_color)
            painter.setPen(QPen(border_color, border_width))
            painter.drawPath(path)

        if card.pixmap and not card.pixmap.isNull():
            img_w = int(w - (10 * scale if self.show_borders else 0))
            img_h = int(h - (40 * scale if self.show_borders else 0))

            if img_w > 10 and img_h > 10:
                scaled_pixmap = card.pixmap.scaled(img_w, img_h, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                painter.drawPixmap(-scaled_pixmap.width()/2, -scaled_pixmap.height()/2, scaled_pixmap)

        if self.show_titles:
            painter.setPen(QColor(255, 255, 255))
            font = QFont("Segoe UI", max(8, int(11 * scale)))
            font.setBold(True)
            painter.setFont(font)
            title_y = h/2 - 20*scale if self.show_borders else h/8
            title = card.title if len(card.title) <= 25 else card.title[:22] + "..."
            painter.drawText(QRect(-w/2, title_y - 15, w, 30), Qt.AlignmentFlag.AlignCenter, title)

        if self.show_memory and card.memory_mb > 0:
            mem_y = -h/2 - 10*scale if self.show_borders else -h/2 + 10*scale
            painter.setPen(QColor(170, 170, 170) if self.show_borders else QColor(255, 255, 0))
            font = QFont("Arial", max(7, int(9*scale)))
            painter.setFont(font)
            painter.drawText(QRect(-w/2, mem_y - 10, w, 20), Qt.AlignmentFlag.AlignCenter, f"{card.memory_mb:.0f} MB")

        painter.restore()

    def _draw_exclusive_mode(self, painter):
        for card in self.cards:
            if card.hwnd == self.exclusive_hwnd:
                x = self.exclusive_geometry.x() + self.exclusive_geometry.width() / 2
                y = self.exclusive_geometry.y() + self.exclusive_geometry.height() / 2
                w = self.exclusive_geometry.width()
                h = self.exclusive_geometry.height()

                painter.save()
                painter.translate(x, y)

                if self.show_borders:
                    bg_color = QColor(45, 90, 123)
                    border_color = QColor(77, 212, 232)

                    rect = QRect(-w/2, -h/2, w, h)
                    path = QPainterPath()
                    path.addRoundedRect(rect, 12, 12)

                    painter.fillPath(path, bg_color)
                    painter.setPen(QPen(border_color, 3))
                    painter.drawPath(path)

                if card.pixmap and not card.pixmap.isNull():
                    img_w = int(w - (10 if self.show_borders else 0))
                    img_h = int(h - (40 if self.show_borders else 0))

                    if img_w > 10 and img_h > 10:
                        scaled_pixmap = card.pixmap.scaled(img_w, img_h, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                        painter.drawPixmap(-scaled_pixmap.width()/2, -scaled_pixmap.height()/2, scaled_pixmap)

                if self.show_titles:
                    painter.setPen(QColor(255, 255, 255))
                    font = QFont("Segoe UI", 14)
                    font.setBold(True)
                    painter.setFont(font)
                    title_y = h/2 - 25
                    title = card.title if len(card.title) <= 40 else card.title[:37] + "..."
                    painter.drawText(QRect(-w/2, title_y - 15, w, 30), Qt.AlignmentFlag.AlignCenter, title)

                if self.show_memory and card.memory_mb > 0:
                    mem_y = -h/2 - 15 if self.show_borders else -h/2 + 15
                    painter.setPen(QColor(170, 170, 170) if self.show_borders else QColor(255, 255, 0))
                    font = QFont("Arial", 11)
                    painter.setFont(font)
                    painter.drawText(QRect(-w/2, mem_y - 10, w, 20), Qt.AlignmentFlag.AlignCenter, f"{card.memory_mb:.0f} MB")

                painter.restore()
                break

    def wheelEvent(self, event):
        if self.exclusive_mode:
            return

        delta = event.angleDelta().y()
        if delta < 0:
            self.navigate_delta(1)
        else:
            self.navigate_delta(-1)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Left:
            self.navigate_delta(-1)
        elif event.key() == Qt.Key.Key_Right:
            self.navigate_delta(1)
        elif event.key() == Qt.Key.Key_Return or event.key() == Qt.Key.Key_Enter:
            self._activate_selected()
        elif event.key() == Qt.Key.Key_Escape:
            if self.exclusive_mode:
                self._exit_exclusive_mode()
            else:
                self.closeRequested.emit()

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            if self.exclusive_mode:
                self._exit_exclusive_mode()
            else:
                self._activate_selected()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            if self.exclusive_mode:
                self.press_pos = event.globalPosition().toPoint()
                self.press_card_pos = self.exclusive_geometry.topLeft()
            else:
                self.long_press_timer.start()

    def mouseMoveEvent(self, event):
        if self.exclusive_mode and event.buttons() & Qt.MouseButton.LeftButton:
            delta = event.globalPosition().toPoint() - self.press_pos
            new_pos = self.press_card_pos + delta
            self.exclusive_geometry.moveTo(new_pos)
            self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.long_press_timer.stop()

    def _on_long_press(self):
        if not self.exclusive_mode and len(self.cards) > 0:
            idx = int(round(self.current_index_float))
            if 0 <= idx < len(self.cards):
                self._enter_exclusive_mode(self.cards[idx].hwnd)

    def _enter_exclusive_mode(self, hwnd):
        self.exclusive_hwnd = hwnd
        self.exclusive_mode = True

        cx = self.width() / 2
        cy = self.height() / 2
        w = min(800, self.width() - 100)
        h = min(600, self.height() - 100)

        self.exclusive_geometry = QRect(cx - w/2, cy - h/2, w, h)
        self.update()

    def _exit_exclusive_mode(self):
        self.exclusive_mode = False
        self.exclusive_hwnd = None
        self.update()

    def _activate_selected(self):
        if len(self.cards) == 0:
            return

        idx = int(round(self.current_index_float))
        if 0 <= idx < len(self.cards):
            hwnd = self.cards[idx].hwnd
            try:
                if win32gui.IsIconic(hwnd):
                    win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                win32gui.SetForegroundWindow(hwnd)
                self.windowSelected.emit(hwnd)
            except:
                pass

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.exclusive_mode:
            cx = self.width() / 2
            cy = self.height() / 2
            w = min(800, self.width() - 100)
            h = min(600, self.height() - 100)
            self.exclusive_geometry = QRect(cx - w/2, cy - h/2, w, h)
