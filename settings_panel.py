import getpass

import psutil
from PyQt6.QtCore import (QEasingCurve, QParallelAnimationGroup,
                          QPropertyAnimation, Qt, pyqtSignal)
from PyQt6.QtGui import QColor, QFont
from PyQt6.QtWidgets import (QCheckBox, QColorDialog, QComboBox, QFontDialog,
                             QGraphicsDropShadowEffect, QGridLayout, QGroupBox,
                             QHBoxLayout, QLabel, QListWidget, QListWidgetItem,
                             QPushButton, QSlider, QVBoxLayout, QWidget)

# Tema HALO 3 (alineado con gui.py)
THEME = {
    "display": "Halo 3",
    "bg": "#0a0f14",
    "panel": "#0f1620",
    "text": "#d3e3ff",
    "accent1": "#3fa7d6",
    "accent2": "#8fd14f",
    "accentWarn": "#ff6b6b",
    "glow1": "#3fa7d6",
    "glow2": "#8fd14f",
    "font_family": "Segoe UI",
}


def make_qt_stylesheet(theme: dict) -> str:
    # QSS ajustado a “elementos flotantes” (sin cajas de fondo ni bordes)
    bg = theme["bg"]
    text = theme["text"]
    a1 = theme["accent1"]
    a2 = theme["accent2"]
    warn = theme["accentWarn"]

    return f"""
    QWidget {{
        background-color: {bg};
        color: {text};
        font-family: {theme['font_family']};
    }}
    /* Sin caja de fondo ni borde para los grupos (flotantes) */
    QGroupBox {{
        background-color: transparent;
        border: none;
        margin-top: 22px;
        padding: 0px;
        font-weight: 600;
    }}
    QGroupBox::title {{
        subcontrol-origin: margin;
        subcontrol-position: top left;
        padding: 0 8px;
        color: {a2};
        letter-spacing: 1px;
    }}
    QLabel {{
        color: {text};
        font-size: 11pt;
    }}
    QListWidget {{
        background-color: rgba(255,255,255,0.03);
        border: 1px solid rgba(255,255,255,0.08);
        border-radius: 8px;
        padding: 6px;
        outline: none;
        selection-background-color: {a1};
        selection-color: #000000;
    }}
    QListWidget::item {{
        padding: 6px;
        border-radius: 6px;
    }}
    QListWidget::item:selected {{
        background-color: {a1};
        color: #000;
    }}
    QPushButton {{
        background-color: transparent;
        color: {text};
        border: 1px solid {a1};
        border-radius: 8px;
        padding: 8px 12px;
    }}
    QPushButton:hover {{
        border-color: {a2};
        color: {a2};
    }}
    QPushButton#danger {{
        border-color: {warn};
        color: {warn};
    }}
    QPushButton#danger:hover {{
        background-color: {warn};
        color: #000;
    }}
    QPushButton:disabled {{
        color: rgba(200,210,220,0.5);
        border-color: rgba(200,210,220,0.25);
    }}
    QCheckBox {{
        spacing: 8px;
        font-size: 10pt;
    }}
    /* Indicador de checkbox como cuadro con tilde */
    QCheckBox::indicator {{
        width: 18px;
        height: 18px;
        border: 1px solid {a1};
        border-radius: 3px;
        background: rgba(255,255,255,0.02);
    }}
    QCheckBox::indicator:hover {{
        border-color: {a2};
    }}
    QCheckBox::indicator:checked {{
        background-color: {a1};
        border-color: {a1};
    }}
    QComboBox {{
        background-color: #0d141c;
        color: {text};
        border: 1px solid {a1};
        border-radius: 6px;
        padding: 6px;
    }}
    QComboBox QAbstractItemView {{
        background-color: #0d141c;
        color: {text};
        selection-background-color: {a1};
        selection-color: #000000;
        outline: none;
        border: 1px solid rgba(255,255,255,0.08);
        border-radius: 6px;
    }}
    QSpinBox, QSlider, QLineEdit {{
        background-color: transparent;
        color: {text};
    }}
    /* Sliders */
    QSlider::groove:horizontal {{
        border: 1px solid rgba(255,255,255,0.08);
        height: 6px;
        background: rgba(255,255,255,0.04);
        border-radius: 3px;
    }}
    QSlider::handle:horizontal {{
        background: {a1};
        border: 1px solid {a1};
        width: 18px;
        margin: -7px 0;
        border-radius: 9px;
    }}
    QSlider::handle:horizontal:hover {{
        background: {a2};
        border-color: {a2};
    }}
    """


def pulsing_glow(widget, color1: str, color2: str, blur_min=12, blur_max=28, duration=4200):
    # Efecto opcional (con grupos “flotantes” sigue siendo válido)
    effect = QGraphicsDropShadowEffect(widget)
    effect.setOffset(0, 0)
    effect.setColor(QColor(color1))
    effect.setBlurRadius(blur_min)
    widget.setGraphicsEffect(effect)

    anim_blur = QPropertyAnimation(effect, b"blurRadius", widget)
    anim_blur.setDuration(duration)
    anim_blur.setEasingCurve(QEasingCurve.Type.InOutSine)
    anim_blur.setLoopCount(-1)
    anim_blur.setKeyValueAt(0.0, blur_min)
    anim_blur.setKeyValueAt(0.5, blur_max)
    anim_blur.setKeyValueAt(1.0, blur_min)

    anim_color = QPropertyAnimation(effect, b"color", widget)
    anim_color.setDuration(duration)
    anim_color.setEasingCurve(QEasingCurve.Type.InOutSine)
    anim_color.setLoopCount(-1)
    anim_color.setKeyValueAt(0.0, QColor(color1))
    anim_color.setKeyValueAt(0.5, QColor(color2))
    anim_color.setKeyValueAt(1.0, QColor(color1))

    grp = QParallelAnimationGroup(widget)
    grp.addAnimation(anim_blur)
    grp.addAnimation(anim_color)
    grp.start()

    if not hasattr(widget, "_glow_animations"):
        widget._glow_animations = []
    widget._glow_animations.append((effect, grp))


class SettingsPanel(QWidget):
    distanceChanged = pyqtSignal(int)
    spacingChanged = pyqtSignal(int)
    thumbnailSizeChanged = pyqtSignal(int)
    animationsEnabledChanged = pyqtSignal(bool)
    borderEnabledChanged = pyqtSignal(bool)
    borderWidthChanged = pyqtSignal(int)
    borderColorChanged = pyqtSignal(str)
    autostartChanged = pyqtSignal(bool)

    # Hover solo zoom
    hoverAnimationEnabledChanged = pyqtSignal(bool)
    hoverAnimationIntensityChanged = pyqtSignal(float)

    # Nombre flotante independiente
    labelEnabledChanged = pyqtSignal(bool)
    labelPositionChanged = pyqtSignal(str)      # "right" | "top" | "bottom"
    labelFontChanged = pyqtSignal(QFont)
    labelColorChanged = pyqtSignal(str)
    labelTextSizeChanged = pyqtSignal(int)      # pt
    labelDistanceChanged = pyqtSignal(int)      # px

    # NUEVO: desplazamiento horizontal y modo de contenido
    labelHorizontalOffsetChanged = pyqtSignal(int)
    labelContentModeChanged = pyqtSignal(str)

    viewModeChanged = pyqtSignal(str)
    flip3dSpacingChanged = pyqtSignal(int)
    flip3dCardScaleChanged = pyqtSignal(float)
    flip3dAnimationSpeedChanged = pyqtSignal(float)
    flip3dShowMemoryChanged = pyqtSignal(bool)
    flip3dShowBordersChanged = pyqtSignal(bool)
    flip3dShowTitlesChanged = pyqtSignal(bool)

    ignoreListChanged = pyqtSignal(list)
    closeApp = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)

        # Tema y estilo alineados con gui.py
        self.theme = THEME
        base_font = QFont(self.theme["font_family"], 10)
        self.setFont(base_font)

        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.setFixedSize(1300, 720)

        # Aplicar hoja de estilos Halo 3
        self.setStyleSheet(make_qt_stylesheet(self.theme))

        self.border_color = "#0078D7"
        self.label_color = "#FFFFFF"
        self.label_font = QFont("Arial", 10)
        self.ignored_names = set()

        self.main_layout = QHBoxLayout(self)

        # Columnas
        self.left_column = QVBoxLayout()
        self.left_column.setSpacing(15)
        self.right_column = QVBoxLayout()
        self.right_column.setSpacing(15)

        self._create_view_mode_group()
        self._create_basic_settings()
        self._create_animations_group()
        self._create_border_group()

        self._create_flip3d_settings()
        self._create_floating_name_group()
        self._create_process_group()
        self._create_autostart_and_buttons_group()

        self.left_column.addStretch()
        self.right_column.addStretch()

        self.main_layout.addLayout(self.left_column)
        self.main_layout.addLayout(self.right_column)

    def _create_basic_settings(self):
        g = QGroupBox("Configuración Básica", self)
        grid = QGridLayout(g)
        grid.setSpacing(15)

        # Distancia al borde
        dist_label = QLabel("Distancia del Borde", self)
        self.distance_slider = QSlider(Qt.Orientation.Horizontal, self)
        self.distance_slider.setRange(0, 100)
        self.distance_slider.setValue(15)
        self.distance_slider.valueChanged.connect(self.distanceChanged.emit)
        grid.addWidget(dist_label, 0, 0)
        grid.addWidget(self.distance_slider, 0, 1)

        # Espaciado vertical
        spacing_label = QLabel("Espaciado Vertical", self)
        self.spacing_slider = QSlider(Qt.Orientation.Horizontal, self)
        self.spacing_slider.setRange(0, 80)
        self.spacing_slider.setValue(15)
        self.spacing_slider.valueChanged.connect(self.spacingChanged.emit)
        grid.addWidget(spacing_label, 1, 0)
        grid.addWidget(self.spacing_slider, 1, 1)

        # Tamaño miniaturas
        size_label = QLabel("Tamaño de Miniaturas", self)
        self.size_slider = QSlider(Qt.Orientation.Horizontal, self)
        self.size_slider.setRange(150, 500)
        self.size_slider.setValue(220)
        self.size_slider.valueChanged.connect(self.thumbnailSizeChanged.emit)
        grid.addWidget(size_label, 2, 0)
        grid.addWidget(self.size_slider, 2, 1)

        self.left_column.addWidget(g)

    def _create_view_mode_group(self):
        g = QGroupBox("Modo de Visualización", self)
        v = QVBoxLayout(g)

        h = QHBoxLayout()
        mode_label = QLabel("Seleccionar Modo:", self)
        self.view_mode_combo = QComboBox(self)
        self.view_mode_combo.addItems(["Nativo (Sidebar)", "Flip3D"])
        self.view_mode_combo.currentTextChanged.connect(self._on_view_mode_changed)
        h.addWidget(mode_label)
        h.addWidget(self.view_mode_combo)
        v.addLayout(h)

        self.left_column.addWidget(g)

    def _on_view_mode_changed(self, text):
        mode = "native" if "Nativo" in text else "flip3d"
        self.viewModeChanged.emit(mode)

    def _create_flip3d_settings(self):
        g = QGroupBox("Configuración Flip3D", self)
        grid = QGridLayout(g)
        grid.setSpacing(15)

        spacing_label = QLabel("Separación de Tarjetas", self)
        self.flip3d_spacing_slider = QSlider(Qt.Orientation.Horizontal, self)
        self.flip3d_spacing_slider.setRange(50, 400)
        self.flip3d_spacing_slider.setValue(150)
        self.flip3d_spacing_slider.valueChanged.connect(self.flip3dSpacingChanged.emit)
        grid.addWidget(spacing_label, 0, 0)
        grid.addWidget(self.flip3d_spacing_slider, 0, 1)

        scale_label = QLabel("Escala de Tarjetas", self)
        self.flip3d_scale_slider = QSlider(Qt.Orientation.Horizontal, self)
        self.flip3d_scale_slider.setRange(50, 200)
        self.flip3d_scale_slider.setValue(100)
        self.flip3d_scale_value = QLabel("1.00", self)
        self.flip3d_scale_slider.valueChanged.connect(self._on_flip3d_scale_changed)
        grid.addWidget(scale_label, 1, 0)
        scale_h = QHBoxLayout()
        scale_h.addWidget(self.flip3d_scale_slider)
        scale_h.addWidget(self.flip3d_scale_value)
        grid.addLayout(scale_h, 1, 1)

        speed_label = QLabel("Velocidad de Animación", self)
        self.flip3d_speed_slider = QSlider(Qt.Orientation.Horizontal, self)
        self.flip3d_speed_slider.setRange(1, 50)
        self.flip3d_speed_slider.setValue(10)
        self.flip3d_speed_value = QLabel("0.10", self)
        self.flip3d_speed_slider.valueChanged.connect(self._on_flip3d_speed_changed)
        grid.addWidget(speed_label, 2, 0)
        speed_h = QHBoxLayout()
        speed_h.addWidget(self.flip3d_speed_slider)
        speed_h.addWidget(self.flip3d_speed_value)
        grid.addLayout(speed_h, 2, 1)

        self.flip3d_show_memory = QCheckBox("Mostrar uso de memoria", self)
        self.flip3d_show_memory.setChecked(True)
        self.flip3d_show_memory.toggled.connect(self.flip3dShowMemoryChanged.emit)
        grid.addWidget(self.flip3d_show_memory, 3, 0, 1, 2)

        self.flip3d_show_borders = QCheckBox("Mostrar bordes de tarjetas", self)
        self.flip3d_show_borders.setChecked(True)
        self.flip3d_show_borders.toggled.connect(self.flip3dShowBordersChanged.emit)
        grid.addWidget(self.flip3d_show_borders, 4, 0, 1, 2)

        self.flip3d_show_titles = QCheckBox("Mostrar títulos de ventanas", self)
        self.flip3d_show_titles.setChecked(True)
        self.flip3d_show_titles.toggled.connect(self.flip3dShowTitlesChanged.emit)
        grid.addWidget(self.flip3d_show_titles, 5, 0, 1, 2)

        self.right_column.addWidget(g)

    def _on_flip3d_scale_changed(self, value):
        scale = value / 100.0
        self.flip3d_scale_value.setText(f"{scale:.2f}")
        self.flip3dCardScaleChanged.emit(scale)

    def _on_flip3d_speed_changed(self, value):
        speed = value / 100.0
        self.flip3d_speed_value.setText(f"{speed:.2f}")
        self.flip3dAnimationSpeedChanged.emit(speed)

    def _create_animations_group(self):
        g = QGroupBox("Animaciones Generales", self)
        l = QVBoxLayout(g)

        self.animations_checkbox = QCheckBox("Habilitar Animaciones de Entrada/Salida", self)
        self.animations_checkbox.setChecked(True)
        self.animations_checkbox.toggled.connect(self.animationsEnabledChanged.emit)
        l.addWidget(self.animations_checkbox)

        hover_g = QGroupBox("Animación al Pasar el Cursor (Zoom)", self)
        hover_l = QVBoxLayout(hover_g)

        self.hover_animation_checkbox = QCheckBox("Activar zoom al pasar el cursor")
        self.hover_animation_checkbox.setChecked(True)
        self.hover_animation_checkbox.toggled.connect(self.hoverAnimationEnabledChanged.emit)
        hover_l.addWidget(self.hover_animation_checkbox)

        # Intensidad del zoom (factor 1.00 a 2.00)
        intensity_layout = QHBoxLayout()
        intensity_label = QLabel("Factor de zoom:", self)
        self.intensity_slider = QSlider(Qt.Orientation.Horizontal, self)
        self.intensity_slider.setRange(100, 200)
        self.intensity_slider.setValue(115)
        self.intensity_value_label = QLabel("1.15", self)
        self.intensity_value_label.setMinimumWidth(50)
        self.intensity_slider.valueChanged.connect(self._on_zoom_intensity_changed)
        intensity_layout.addWidget(intensity_label)
        intensity_layout.addWidget(self.intensity_slider)
        intensity_layout.addWidget(self.intensity_value_label)
        hover_l.addLayout(intensity_layout)

        l.addWidget(hover_g)
        self.left_column.addWidget(g)

    def _on_zoom_intensity_changed(self, value):
        factor = value / 100.0
        self.intensity_value_label.setText(f"{factor:.2f}")
        self.hoverAnimationIntensityChanged.emit(factor)

    def _create_border_group(self):
        g = QGroupBox("Bordes de Miniaturas", self)
        v = QVBoxLayout(g)

        self.border_checkbox = QCheckBox("Habilitar Bordes", self)
        self.border_checkbox.setChecked(False)
        self.border_checkbox.toggled.connect(self._on_border_enabled_changed)
        v.addWidget(self.border_checkbox)

        h = QHBoxLayout()
        wlbl = QLabel("Ancho del Borde", self)
        self.border_width_slider = QSlider(Qt.Orientation.Horizontal, self)
        self.border_width_slider.setRange(1, 10)
        self.border_width_slider.setValue(2)
        self.border_width_slider.valueChanged.connect(self.borderWidthChanged.emit)
        self.border_width_slider.setEnabled(False)
        h.addWidget(wlbl)
        h.addWidget(self.border_width_slider)
        v.addLayout(h)

        hc = QHBoxLayout()
        clbl = QLabel("Color del Borde", self)
        self.color_button = QPushButton("Seleccionar Color", self)
        self.color_button.clicked.connect(self._select_border_color)
        self.color_button.setEnabled(False)
        hc.addWidget(clbl)
        hc.addWidget(self.color_button)
        v.addLayout(hc)

        self.left_column.addWidget(g)

    def _create_floating_name_group(self):
        g = QGroupBox("Nombre Flotante (Independiente)", self)
        l = QVBoxLayout(g)

        self.label_checkbox = QCheckBox("Mostrar nombre (título de ventana)")
        self.label_checkbox.setChecked(False)
        self.label_checkbox.toggled.connect(self.labelEnabledChanged.emit)
        self.label_checkbox.toggled.connect(self._on_label_enabled_changed)
        l.addWidget(self.label_checkbox)

        # Contenido: información completa o solo nombre de la app
        mode_layout = QHBoxLayout()
        mode_label = QLabel("Contenido del texto:", self)
        self.label_content_combo = QComboBox(self)
        self.label_content_combo.addItems(["Información completa", "Solo nombre de la app"])
        self.label_content_combo.currentTextChanged.connect(self._on_label_content_changed)
        self.label_content_combo.setEnabled(False)
        mode_layout.addWidget(mode_label)
        mode_layout.addWidget(self.label_content_combo)
        l.addLayout(mode_layout)

        # Posición
        h1 = QHBoxLayout()
        pos_label = QLabel("Posición:", self)
        self.label_position_combo = QComboBox(self)
        self.label_position_combo.addItems(["Derecha", "Arriba", "Abajo"])
        self.label_position_combo.currentTextChanged.connect(self._on_label_position_changed)
        self.label_position_combo.setEnabled(False)
        h1.addWidget(pos_label)
        h1.addWidget(self.label_position_combo)
        l.addLayout(h1)

        # Tamaño de texto (slider)
        h2 = QHBoxLayout()
        size_label = QLabel("Tamaño de texto:", self)
        self.label_size_slider = QSlider(Qt.Orientation.Horizontal, self)
        self.label_size_slider.setRange(6, 48)
        self.label_size_slider.setValue(10)
        self.label_size_slider.valueChanged.connect(self.labelTextSizeChanged.emit)
        self.label_size_slider.setEnabled(False)
        h2.addWidget(size_label)
        h2.addWidget(self.label_size_slider)
        l.addLayout(h2)

        # Cercanía (distancia)
        h3 = QHBoxLayout()
        dist_label = QLabel("Cercanía (distancia):", self)
        self.label_distance_slider = QSlider(Qt.Orientation.Horizontal, self)
        self.label_distance_slider.setRange(0, 100)
        self.label_distance_slider.setValue(15)
        self.label_distance_slider.valueChanged.connect(self.labelDistanceChanged.emit)
        self.label_distance_slider.setEnabled(False)
        h3.addWidget(dist_label)
        h3.addWidget(self.label_distance_slider)
        l.addLayout(h3)

        # NUEVO: desplazamiento horizontal (solo para Arriba/Abajo)
        h3b = QHBoxLayout()
        hoff_label = QLabel("Desplazamiento horizontal:", self)
        self.label_horiz_offset_slider = QSlider(Qt.Orientation.Horizontal, self)
        self.label_horiz_offset_slider.setRange(-600, 600)   # amplio margen
        self.label_horiz_offset_slider.setValue(0)
        self.label_horiz_offset_slider.valueChanged.connect(self.labelHorizontalOffsetChanged.emit)
        self.label_horiz_offset_slider.setEnabled(False)
        self.label_horiz_offset_value = QLabel("0 px", self)
        self.label_horiz_offset_slider.valueChanged.connect(lambda v: self.label_horiz_offset_value.setText(f"{v} px"))
        h3b.addWidget(hoff_label)
        h3b.addWidget(self.label_horiz_offset_slider)
        h3b.addWidget(self.label_horiz_offset_value)
        l.addLayout(h3b)

        # Tipo de fuente
        h4 = QHBoxLayout()
        font_label = QLabel("Tipo de fuente:", self)
        self.font_button = QPushButton("Seleccionar Fuente", self)
        self.font_button.clicked.connect(self._select_label_font)
        self.font_button.setEnabled(False)
        h4.addWidget(font_label)
        h4.addWidget(self.font_button)
        l.addLayout(h4)

        # Color
        h5 = QHBoxLayout()
        color_label = QLabel("Color:", self)
        self.label_color_button = QPushButton("Seleccionar Color", self)
        self.label_color_button.clicked.connect(self._select_label_color)
        self.label_color_button.setEnabled(False)
        h5.addWidget(color_label)
        h5.addWidget(self.label_color_button)
        l.addLayout(h5)

        self.right_column.addWidget(g)

    def _on_label_enabled_changed(self, enabled):
        self.label_content_combo.setEnabled(enabled)
        self.label_position_combo.setEnabled(enabled)
        self.font_button.setEnabled(enabled)
        self.label_color_button.setEnabled(enabled)
        self.label_size_slider.setEnabled(enabled)
        self.label_distance_slider.setEnabled(enabled)
        # Solo habilitar offset horizontal si la posición es Arriba/Abajo
        pos_text = self.label_position_combo.currentText()
        allow_offset = enabled and (pos_text in ("Arriba", "Abajo"))
        self.label_horiz_offset_slider.setEnabled(allow_offset)

    def _on_label_position_changed(self, text):
        pos_map = {
            "Derecha": "right",
            "Arriba": "top",
            "Abajo": "bottom"
        }
        # Habilitar/Deshabilitar offset horizontal según posición
        self.label_horiz_offset_slider.setEnabled(text in ("Arriba", "Abajo") and self.label_checkbox.isChecked())
        self.labelPositionChanged.emit(pos_map.get(text, "right"))

    def _on_label_content_changed(self, text):
        mode = "full" if "completa" in text.lower() else "app"
        self.labelContentModeChanged.emit(mode)

    def _select_label_font(self):
        font, ok = QFontDialog.getFont(self.label_font, self)
        if ok:
            self.label_font = font
            # Mantener el tamaño del slider si es distinto
            self.label_font.setPointSize(self.label_size_slider.value())
            self.labelFontChanged.emit(self.label_font)

    def _select_label_color(self):
        color = QColorDialog.getColor(QColor(self.label_color), self)
        if color.isValid():
            self.label_color = color.name()
            self.labelColorChanged.emit(self.label_color)

    def _create_process_group(self):
        g = QGroupBox("Procesos del usuario", self)
        v = QVBoxLayout(g)

        hb = QHBoxLayout()
        self.refresh_btn = QPushButton("Actualizar")
        self.add_ignore_btn = QPushButton("Agregar a ignorados")
        self.remove_ignore_btn = QPushButton("Quitar de ignorados")
        hb.addWidget(self.refresh_btn)
        hb.addWidget(self.add_ignore_btn)
        hb.addWidget(self.remove_ignore_btn)
        v.addLayout(hb)

        hl = QHBoxLayout()
        self.process_list = QListWidget()
        self.ignored_list = QListWidget()
        hl.addWidget(self.process_list)
        hl.addWidget(self.ignored_list)
        v.addLayout(hl)

        self.refresh_btn.clicked.connect(self._refresh_processes)
        self.add_ignore_btn.clicked.connect(self._add_selected_to_ignored)
        self.remove_ignore_btn.clicked.connect(self._remove_selected_from_ignored)

        self.right_column.addWidget(g)
        self._refresh_processes()

    def _create_autostart_and_buttons_group(self):
        g = QGroupBox("Inicio y acciones", self)
        v = QVBoxLayout(g)

        # Fila con: [Guardar] [Cerrar Script] ... [Iniciar con Windows]
        row = QHBoxLayout()
        save_button = QPushButton("Guardar y Cerrar", self)
        save_button.clicked.connect(self.hide)
        save_button.setFixedWidth(200)

        close_button = QPushButton("Cerrar Script", self)
        close_button.setObjectName("danger")
        close_button.clicked.connect(self.closeApp.emit)
        close_button.setFixedWidth(200)

        self.autostart_checkbox = QCheckBox("Iniciar con Windows")
        self.autostart_checkbox.setChecked(False)
        self.autostart_checkbox.toggled.connect(self.autostartChanged.emit)

        row.addWidget(save_button)
        row.addWidget(close_button)
        row.addSpacing(16)
        row.addStretch()
        row.addWidget(self.autostart_checkbox)

        v.addLayout(row)

        self.right_column.addWidget(g)

    def _on_border_enabled_changed(self, enabled):
        self.border_width_slider.setEnabled(enabled)
        self.color_button.setEnabled(enabled)
        self.borderEnabledChanged.emit(enabled)

    def _select_border_color(self):
        color = QColorDialog.getColor(QColor(self.border_color), self)
        if color.isValid():
            self.border_color = color.name()
            self.borderColorChanged.emit(self.border_color)

    def _refresh_processes(self):
        self.process_list.clear()
        user = getpass.getuser().lower()
        system_processes = {
            'svchost.exe', 'system', 'registry', 'smss.exe', 'csrss.exe',
            'wininit.exe', 'services.exe', 'lsass.exe', 'winlogon.exe',
            'dwm.exe', 'fontdrvhost.exe', 'spoolsv.exe', 'taskhostw.exe',
            'searchindexer.exe', 'runtimebroker.exe', 'sihost.exe',
            'ctfmon.exe', 'conhost.exe', 'dllhost.exe', 'audiodg.exe',
            'wudfhost.exe', 'dashost.exe', 'sgrmbroker.exe', 'memory compression',
            'securityhealthservice.exe', 'securityhealthsystray.exe',
            'windows.security.exe', 'msmpeng.exe', 'nissrv.exe'
        }

        seen = set()
        for p in psutil.process_iter(["pid", "name", "username"]):
            try:
                u = p.info.get("username") or ""
                n = p.info.get("name") or ""
                if not n:
                    continue

                n_lower = n.lower()

                if n_lower in system_processes:
                    continue

                if user not in u.lower():
                    continue

                if n_lower in seen:
                    continue

                seen.add(n_lower)
                item = QListWidgetItem(f"{n}")
                item.setData(Qt.ItemDataRole.UserRole, n)
                self.process_list.addItem(item)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        self.ignored_list.clear()
        for n in sorted(self.ignored_names):
            it = QListWidgetItem(n)
            it.setData(Qt.ItemDataRole.UserRole, n)
            self.ignored_list.addItem(it)

    def _add_selected_to_ignored(self):
        for it in self.process_list.selectedItems():
            n = it.data(Qt.ItemDataRole.UserRole)
            self.ignored_names.add(n.lower())
        self.ignoreListChanged.emit(sorted(self.ignored_names))
        self._refresh_processes()

    def _remove_selected_from_ignored(self):
        for it in self.ignored_list.selectedItems():
            n = it.data(Qt.ItemDataRole.UserRole)
            if n.lower() in self.ignored_names:
                self.ignored_names.remove(n.lower())
        self.ignoreListChanged.emit(sorted(self.ignored_names))
        self._refresh_processes()

    def closeEvent(self, event):
        self.hide()
        event.ignore()
