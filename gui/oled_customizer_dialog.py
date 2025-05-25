### START OF FILE gui/oled_customizer_dialog.py ###
import sys
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QDialogButtonBox, QFontComboBox, QSpinBox, QWidget, QSizePolicy, QFrame,
    QSlider, QGroupBox
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize, QTimer
from PyQt6.QtGui import QImage, QPixmap, QFont, QFontDatabase, QPainter, QColor, QFontMetrics

# Attempt to import oled_renderer for previewing
try:
    from oled_utils import oled_renderer
    OLED_RENDERER_AVAILABLE_FOR_DIALOG = True
except ImportError:
    print("OLEDCustomizerDialog WARNING: oled_renderer not found. Live preview will be basic.")
    OLED_RENDERER_AVAILABLE_FOR_DIALOG = False
    class oled_renderer: # Minimal placeholder
        OLED_WIDTH = 128; OLED_HEIGHT = 64

# --- Constants for this Dialog ---
DEFAULT_FONT_FAMILY = "Arial" 
DEFAULT_FONT_SIZE_PX = 10     

# --- Scroll Speed Configuration ---
# Slider will represent "Speed Level"
MIN_SPEED_LEVEL = 1
MAX_SPEED_LEVEL = 20 # e.g., 20 levels of speed

# Actual delay range these levels map to
# Higher "Speed Level" will map to MIN_ACTUAL_DELAY_MS
# Lower "Speed Level" will map to MAX_ACTUAL_DELAY_MS
MIN_ACTUAL_DELAY_MS = 20  # Fastest scroll (low delay)
MAX_ACTUAL_DELAY_MS = 500 # Slowest scroll (high delay)
DEFAULT_GLOBAL_SCROLL_DELAY_MS_FALLBACK = 180 # Fallback if mapping results in something odd initially

class OLEDCustomizerDialog(QDialog):
    startup_settings_changed = pyqtSignal(str, str, int, int) # text, family, size_px, scroll_delay_ms

    def __init__(self, current_text: str, 
                 current_font_family: str, current_font_size_px: int, 
                 current_global_scroll_delay_ms: int,
                 parent: QWidget | None = None):
        super().__init__(parent)
        self.setWindowTitle("⚙️ OLED Startup & Global Settings")
        self.setMinimumSize(550, 420) # Increased height slightly for new slider

        self._initial_text = current_text
        self._initial_font_family = current_font_family if current_font_family else self.DEFAULT_FONT_FAMILY
        self._initial_font_size_px = current_font_size_px if current_font_size_px > 0 else self.DEFAULT_FONT_SIZE_PX
        self._initial_global_scroll_delay_ms = current_global_scroll_delay_ms

        self._current_text = self._initial_text
        self._current_font_family = self._initial_font_family
        self._current_font_size_px = self._initial_font_size_px
        self._current_global_scroll_delay_ms = self._initial_global_scroll_delay_ms # This will store actual delay_ms
        
        self.startup_text_edit: QLineEdit | None = None
        self.font_family_combo: QFontComboBox | None = None
        self.font_size_spinbox: QSpinBox | None = None
        self.global_scroll_speed_level_slider: QSlider | None = None # Renamed for clarity
        self.global_scroll_speed_display_label: QLabel | None = None  # Renamed for clarity
        self.oled_preview_label: QLabel | None = None
        
        self._selected_font_object_for_preview: QFont | None = None

        self._preview_scroll_timer = QTimer(self)
        self._preview_scroll_timer.timeout.connect(self._scroll_preview_step)
        self._preview_current_scroll_offset: int = 0
        self._preview_text_pixel_width: int = 0
        self._preview_is_scrolling: bool = False

        self._init_ui()
        self._connect_signals()
        self._load_initial_settings() 
        self._update_preview() 

    def _speed_level_to_delay_ms(self, level: int) -> int:
        if level <= MIN_SPEED_LEVEL: return MAX_ACTUAL_DELAY_MS
        if level >= MAX_SPEED_LEVEL: return MIN_ACTUAL_DELAY_MS
        
        norm_level = (level - MIN_SPEED_LEVEL) / (MAX_SPEED_LEVEL - MIN_SPEED_LEVEL)
        delay = MAX_ACTUAL_DELAY_MS - norm_level * (MAX_ACTUAL_DELAY_MS - MIN_ACTUAL_DELAY_MS)
        return int(round(delay))

    def _delay_ms_to_speed_level(self, delay_ms: int) -> int:
        if delay_ms <= MIN_ACTUAL_DELAY_MS: return MAX_SPEED_LEVEL
        if delay_ms >= MAX_ACTUAL_DELAY_MS: return MIN_SPEED_LEVEL

        norm_delay = (delay_ms - MIN_ACTUAL_DELAY_MS) / (MAX_ACTUAL_DELAY_MS - MIN_ACTUAL_DELAY_MS)
        level = MAX_SPEED_LEVEL - norm_delay * (MAX_SPEED_LEVEL - MIN_SPEED_LEVEL)
        return int(round(level))

    def _init_ui(self):
        main_layout = QVBoxLayout(self)

        text_group = QGroupBox("Default Startup Text & Font")
        text_group_layout = QVBoxLayout(text_group)
        text_input_layout = QHBoxLayout()
        text_input_layout.addWidget(QLabel("Text:"))
        self.startup_text_edit = QLineEdit(self._current_text)
        text_input_layout.addWidget(self.startup_text_edit)
        text_group_layout.addLayout(text_input_layout)
        font_layout = QHBoxLayout()
        font_layout.addWidget(QLabel("Font:"))
        self.font_family_combo = QFontComboBox()
        self.font_family_combo.setFontFilters(QFontComboBox.FontFilter.ScalableFonts)
        font_layout.addWidget(self.font_family_combo, 1)
        font_layout.addWidget(QLabel("Size:"))
        self.font_size_spinbox = QSpinBox()
        self.font_size_spinbox.setRange(6, 60) 
        self.font_size_spinbox.setValue(self._current_font_size_px)
        self.font_size_spinbox.setSuffix(" px")
        font_layout.addWidget(self.font_size_spinbox)
        text_group_layout.addLayout(font_layout)
        main_layout.addWidget(text_group)

        scroll_group = QGroupBox("Global OLED Scroll Speed")
        scroll_group_layout = QVBoxLayout(scroll_group)
        scroll_slider_layout = QHBoxLayout()
        self.global_scroll_speed_level_slider = QSlider(Qt.Orientation.Horizontal)
        self.global_scroll_speed_level_slider.setRange(MIN_SPEED_LEVEL, MAX_SPEED_LEVEL) # Slider for Speed Level
        # Initial value will be set in _load_initial_settings
        self.global_scroll_speed_level_slider.setSingleStep(1)
        self.global_scroll_speed_level_slider.setPageStep(2) # Smaller page step for levels
        self.global_scroll_speed_level_slider.setTickInterval(max(1, (MAX_SPEED_LEVEL - MIN_SPEED_LEVEL) // 10))
        self.global_scroll_speed_level_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        scroll_slider_layout.addWidget(self.global_scroll_speed_level_slider, 1)
        self.global_scroll_speed_display_label = QLabel() # Renamed
        self.global_scroll_speed_display_label.setMinimumWidth(90) # For "Speed X (YYY ms)"
        self.global_scroll_speed_display_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        scroll_slider_layout.addWidget(self.global_scroll_speed_display_label)
        scroll_group_layout.addLayout(scroll_slider_layout)
        main_layout.addWidget(scroll_group)
        
        preview_group_outer = QGroupBox("Live Preview")
        preview_group_layout = QVBoxLayout(preview_group_outer)
        self.oled_preview_label = QLabel("Preview")
        self.oled_preview_label.setObjectName("OLEDPreviewDialogLabel")
        preview_label_width = oled_renderer.OLED_WIDTH * 2 if OLED_RENDERER_AVAILABLE_FOR_DIALOG else 256
        preview_label_height = oled_renderer.OLED_HEIGHT * 2 if OLED_RENDERER_AVAILABLE_FOR_DIALOG else 128
        self.oled_preview_label.setFixedSize(preview_label_width, preview_label_height)
        self.oled_preview_label.setStyleSheet("background-color: black; border: 1px solid #555555;")
        self.oled_preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        preview_group_layout.addWidget(self.oled_preview_label, 0, Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(preview_group_outer, 1) 

        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        main_layout.addWidget(self.button_box)

    def _connect_signals(self):
        self.startup_text_edit.textChanged.connect(self._on_setting_changed)
        self.font_family_combo.currentFontChanged.connect(self._on_setting_changed)
        self.font_size_spinbox.valueChanged.connect(self._on_setting_changed)
        if self.global_scroll_speed_level_slider:
            self.global_scroll_speed_level_slider.valueChanged.connect(self._on_scroll_speed_level_slider_changed) # Changed slot name

        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)

    def _load_initial_settings(self):
        self.startup_text_edit.setText(self._initial_text)
        self.font_size_spinbox.setValue(self._initial_font_size_px)
        
        if self.global_scroll_speed_level_slider:
            initial_speed_level = self._delay_ms_to_speed_level(self._initial_global_scroll_delay_ms)
            self.global_scroll_speed_level_slider.setValue(initial_speed_level)
            # Update label based on actual delay, not just speed level for clarity
            self._update_scroll_speed_display_label(initial_speed_level, self._initial_global_scroll_delay_ms) 

        if self.font_family_combo:
            initial_qfont = QFont(self._initial_font_family)
            self.font_family_combo.setCurrentFont(initial_qfont) 
            self._current_font_family = self.font_family_combo.currentFont().family()
        
        # Consolidate _current_ updates after all UI elements are set from _initial_ values
        self._current_text = self.startup_text_edit.text()
        self._current_font_family = self.font_family_combo.currentFont().family()
        self.current_font_size_px = self.font_size_spinbox.value() # Corrected attribute name
        # _current_global_scroll_delay_ms is already set from _initial_
        
        self._selected_font_object_for_preview = QFont(self._current_font_family, self._current_font_size_px)
        self._selected_font_object_for_preview.setPixelSize(self._current_font_size_px)


    def _on_setting_changed(self): 
        self._current_text = self.startup_text_edit.text()
        self._current_font_family = self.font_family_combo.currentFont().family()
        self._current_font_size_px = self.font_size_spinbox.value()
        self._selected_font_object_for_preview = QFont(self._current_font_family) # Create with family first
        self._selected_font_object_for_preview.setPixelSize(self._current_font_size_px) # Then set pixel size
        self._update_preview()

    def _on_scroll_speed_level_slider_changed(self, speed_level_value: int): # Renamed slot parameter
        self._current_global_scroll_delay_ms = self._speed_level_to_delay_ms(speed_level_value)
        self._update_scroll_speed_display_label(speed_level_value, self._current_global_scroll_delay_ms)
        if self._preview_is_scrolling:
            self._preview_scroll_timer.start(self._current_global_scroll_delay_ms)

    def _update_scroll_speed_display_label(self, speed_level: int, delay_ms: int): # Now takes both
        if self.global_scroll_speed_display_label:
            self.global_scroll_speed_display_label.setText(f"Lvl {speed_level} ({delay_ms}ms)")


    def _update_preview(self):
        if not self.oled_preview_label or not self.startup_text_edit: # Check essential UI
            return
        if not self._selected_font_object_for_preview: # Check if font object is created
             # Try to create it if settings changed before it was made
            self._selected_font_object_for_preview = QFont(self.font_family_combo.currentFont().family())
            self._selected_font_object_for_preview.setPixelSize(self.font_size_spinbox.value())
            if not self._selected_font_object_for_preview: return


        self._preview_scroll_timer.stop() 
        current_text_for_preview = self.startup_text_edit.text()
        
        fm = QFontMetrics(self._selected_font_object_for_preview)
        self._preview_text_pixel_width = fm.horizontalAdvance(current_text_for_preview)
        
        native_oled_width = oled_renderer.OLED_WIDTH if OLED_RENDERER_AVAILABLE_FOR_DIALOG else 128
        
        if self._preview_text_pixel_width > native_oled_width and current_text_for_preview.strip(): # Only scroll if text exists
            self._preview_is_scrolling = True
            self._preview_current_scroll_offset = native_oled_width # Start from right for QPainter
            self._render_preview_frame() 
            self._preview_scroll_timer.start(self._current_global_scroll_delay_ms)
        else:
            self._preview_is_scrolling = False
            self._preview_current_scroll_offset = 0 
            self._render_preview_frame() 

    def _render_preview_frame(self):
        if not self.oled_preview_label or not self._selected_font_object_for_preview or not self.startup_text_edit:
            return

        native_oled_width = oled_renderer.OLED_WIDTH if OLED_RENDERER_AVAILABLE_FOR_DIALOG else 128
        native_oled_height = oled_renderer.OLED_HEIGHT if OLED_RENDERER_AVAILABLE_FOR_DIALOG else 64
        current_text_for_preview = self.startup_text_edit.text()

        preview_pixmap_native = QPixmap(native_oled_width, native_oled_height)
        preview_pixmap_native.fill(Qt.GlobalColor.black)
        painter = QPainter(preview_pixmap_native)
        painter.setFont(self._selected_font_object_for_preview)
        painter.setPen(QColor("white"))
        
        fm = painter.fontMetrics()
        text_render_y = fm.ascent() + (native_oled_height - fm.height()) // 2
        text_render_x = 0
        if self._preview_is_scrolling:
            text_render_x = self._preview_current_scroll_offset 
        else: 
            if self._preview_text_pixel_width < native_oled_width:
                text_render_x = (native_oled_width - self._preview_text_pixel_width) // 2
        
        painter.drawText(text_render_x, text_render_y, current_text_for_preview)
        painter.end()

        scaled_preview = preview_pixmap_native.scaled(self.oled_preview_label.size(), 
                                             Qt.AspectRatioMode.KeepAspectRatio, 
                                             Qt.TransformationMode.FastTransformation)
        self.oled_preview_label.setPixmap(scaled_preview)

    def _scroll_preview_step(self):
        if not self._preview_is_scrolling:
            self._preview_scroll_timer.stop(); return

        self._preview_current_scroll_offset -= 2 
        native_oled_width = oled_renderer.OLED_WIDTH if OLED_RENDERER_AVAILABLE_FOR_DIALOG else 128
        if (self._preview_current_scroll_offset + self._preview_text_pixel_width) < 0:
            self._preview_current_scroll_offset = native_oled_width 
            self._preview_scroll_timer.setInterval(2000) 
        else:
            self._preview_scroll_timer.setInterval(self._current_global_scroll_delay_ms)
        self._render_preview_frame()

    def get_settings(self) -> tuple[str, str, int, int]:
        # Read directly from UI elements on get, ensure _current_global_scroll_delay_ms is up-to-date
        if self.global_scroll_speed_level_slider: # Ensure it exists
             self._current_global_scroll_delay_ms = self._speed_level_to_delay_ms(self.global_scroll_speed_level_slider.value())

        return self.startup_text_edit.text(), \
               self.font_family_combo.currentFont().family(), \
               self.font_size_spinbox.value(), \
               self._current_global_scroll_delay_ms # Return the calculated delay

    def accept(self):
        text, family, size, scroll_delay = self.get_settings()
        self.startup_settings_changed.emit(text, family, size, scroll_delay)
        self._preview_scroll_timer.stop()
        super().accept()

    def reject(self): 
        self._preview_scroll_timer.stop()
        self.dialog_closed.emit() 
        super().reject()

    def closeEvent(self, event):
        self._preview_scroll_timer.stop()
        self.dialog_closed.emit()
        super().closeEvent(event)

# (Keep the __main__ for standalone testing, update its constructor call for the new scroll delay param)
if __name__ == '__main__':
    from PyQt6.QtWidgets import QApplication
    app = QApplication(sys.argv)
    dialog = OLEDCustomizerDialog("Test Startup", "Arial", 12, 180) # Pass initial scroll delay
    def on_settings_changed(text, family, size, scroll_delay):
        print(f"Dialog Saved: Text='{text}', Family='{family}', Size={size}px, ScrollDelay={scroll_delay}ms")
    dialog.startup_settings_changed.connect(on_settings_changed)
    if dialog.exec(): print("Dialog accepted.")
    else: print("Dialog cancelled.")
    sys.exit()