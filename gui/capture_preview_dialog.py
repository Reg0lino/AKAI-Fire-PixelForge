### START OF FILE capture_preview_dialog.py ###
# AKAI_Fire_RGB_Controller/gui/capture_preview_dialog.py
import sys
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QSlider, QPushButton, QWidget,
    QSizePolicy, QSpacerItem, QSplitter, QApplication, QGroupBox
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QImage, QPixmap, QFont
from PIL import Image

try:
    from .monitor_view_widget import MonitorViewWidget
except ImportError:
    print("CapturePreviewDialog FATAL: Could not import .monitor_view_widget")
    class MonitorViewWidget(QWidget):
        region_selection_changed = pyqtSignal(int, dict)
        def __init__(self, parent=None): super().__init__(parent)
        def set_monitors_data(self, monitors, target_mss_id_to_focus=None): pass
        def set_target_monitor_and_update_view(self, monitor_id): pass
        def set_current_selection_from_params(self, monitor_id, region_rect_percentage): pass
        def cycle_to_next_monitor(self): pass


try:
    from features.screen_sampler_core import ScreenSamplerCore
except ImportError:
    print("CapturePreviewDialog WARNING: Could not import ScreenSamplerCore from features. Using fallback defaults.")
    class ScreenSamplerCore:
        DEFAULT_ADJUSTMENTS = {'brightness': 1.0, 'contrast': 1.0, 'saturation': 1.0, 'hue_shift': 0}

# --- Slider Constants ---
SLIDER_MIN_FACTOR_VAL = 0
SLIDER_MAX_FACTOR_VAL = 400
SLIDER_MIN_HUE = -180
SLIDER_MAX_HUE = 180

# --- NEW Default Values ---
DEFAULT_BRIGHTNESS_FACTOR = 1.0
DEFAULT_SATURATION_FACTOR = 1.75
DEFAULT_CONTRAST_FACTOR = 1.0
DEFAULT_HUE_SHIFT = 0

class CapturePreviewDialog(QDialog):
    sampling_parameters_changed = pyqtSignal(dict)
    dialog_closed = pyqtSignal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setWindowTitle("👁️ Visual Sampler Configuration")
        self.setMinimumSize(850, 600)
        # --- UI Element Declarations ---
        self.monitor_view_widget: MonitorViewWidget | None = None
        self.cycle_monitor_button: QPushButton | None = None
        self.preview_image_label: QLabel | None = None
        self.brightness_slider: QSlider | None = None
        self.brightness_value_label: QLabel | None = None
        self.brightness_reset_button: QPushButton | None = None
        self.saturation_slider: QSlider | None = None
        self.saturation_value_label: QLabel | None = None
        self.saturation_reset_button: QPushButton | None = None
        self.contrast_slider: QSlider | None = None
        self.contrast_value_label: QLabel | None = None
        self.contrast_reset_button: QPushButton | None = None
        self.hue_slider: QSlider | None = None
        self.hue_value_label: QLabel | None = None
        self.hue_reset_button: QPushButton | None = None
        self._all_monitors_info_cache: list[dict] = []
        self.current_params = {
            'monitor_id': 1,
            'region_rect_percentage': {'x': 0.4, 'y': 0.4, 'width': 0.2, 'height': 0.2},
            'adjustments': {
                'brightness': DEFAULT_BRIGHTNESS_FACTOR,
                'saturation': DEFAULT_SATURATION_FACTOR,
                'contrast': DEFAULT_CONTRAST_FACTOR,
                'hue_shift': DEFAULT_HUE_SHIFT
            },
        }
        self._init_ui()
        self._connect_signals()
        self._update_all_slider_value_labels()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        main_layout.addWidget(splitter, 1)
        # --- Left Panel ---
        left_panel_widget = QWidget()
        left_panel_layout = QVBoxLayout(left_panel_widget)
        left_panel_layout.setContentsMargins(5, 5, 5, 5)
        self.monitor_view_widget = MonitorViewWidget()
        left_panel_layout.addWidget(self.monitor_view_widget, 1)
        instructions_label = QLabel("Drag box to move. Drag handles to resize. Position saves on exit")
        instructions_label.setWordWrap(True)
        instructions_label.setStyleSheet("font-size: 8pt; color: #888888;")
        left_panel_layout.addWidget(instructions_label)
        self.cycle_monitor_button = QPushButton("🔄 Cycle Monitor")
        left_panel_layout.addWidget(self.cycle_monitor_button, 0, Qt.AlignmentFlag.AlignCenter)
        splitter.addWidget(left_panel_widget)
        # --- Right Panel ---
        right_panel_widget = QWidget()
        right_panel_layout = QVBoxLayout(right_panel_widget)
        right_panel_layout.setContentsMargins(5, 5, 5, 5)
        self.preview_image_label = QLabel("Waiting for preview...")
        self.preview_image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_image_label.setMinimumHeight(150)
        self.preview_image_label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.MinimumExpanding)
        self.preview_image_label.setStyleSheet("background-color: #282828; border: 1px solid #444;")
        right_panel_layout.addWidget(self.preview_image_label, 1)
        # Helper function to create a slider row

        def create_slider_row(label_text, min_val, max_val, initial_val):
            layout = QHBoxLayout()
            label = QLabel(label_text)
            label.setMinimumWidth(70)
            slider = QSlider(Qt.Orientation.Horizontal)
            slider.setRange(min_val, max_val)
            slider.setValue(initial_val)
            value_label = QLabel()
            value_label.setMinimumWidth(55)
            reset_button = QPushButton("⟳")
            reset_button.setFixedSize(24, 24)
            reset_button.setObjectName("ResetButton")
            layout.addWidget(label)
            layout.addWidget(slider)
            layout.addWidget(value_label)
            layout.addWidget(reset_button)
            return layout, slider, value_label, reset_button
        # Color Adjustments Group
        adjustments_group = QGroupBox("Color Adjustments")
        adjustments_layout = QVBoxLayout(adjustments_group)
        bri_row_layout, self.brightness_slider, self.brightness_value_label, self.brightness_reset_button = \
            create_slider_row("Brightness:", SLIDER_MIN_FACTOR_VAL, SLIDER_MAX_FACTOR_VAL, self._factor_to_slider(self.current_params['adjustments']['brightness']))
        adjustments_layout.addLayout(bri_row_layout)
        sat_row_layout, self.saturation_slider, self.saturation_value_label, self.saturation_reset_button = \
            create_slider_row("Saturation:", SLIDER_MIN_FACTOR_VAL, SLIDER_MAX_FACTOR_VAL, self._factor_to_slider(self.current_params['adjustments']['saturation']))
        adjustments_layout.addLayout(sat_row_layout)
        con_row_layout, self.contrast_slider, self.contrast_value_label, self.contrast_reset_button = \
            create_slider_row("Contrast:", SLIDER_MIN_FACTOR_VAL, SLIDER_MAX_FACTOR_VAL, self._factor_to_slider(self.current_params['adjustments']['contrast']))
        adjustments_layout.addLayout(con_row_layout)
        hue_row_layout, self.hue_slider, self.hue_value_label, self.hue_reset_button = \
            create_slider_row("Hue Shift:", SLIDER_MIN_HUE, SLIDER_MAX_HUE, int(round(self.current_params['adjustments']['hue_shift'])))
        adjustments_layout.addLayout(hue_row_layout)
        right_panel_layout.addWidget(adjustments_group)
        right_panel_layout.addStretch(0)
        splitter.addWidget(right_panel_widget)
        splitter.setSizes([self.width() * 3 // 5, self.width() * 2 // 5])

    def _connect_signals(self):
        # View signals
        self.monitor_view_widget.region_selection_changed.connect(
            self._on_region_or_monitor_changed_in_view)
        # --- MODIFIED: Connect button directly to the view widget's method ---
        self.cycle_monitor_button.clicked.connect(
            self.monitor_view_widget.cycle_to_next_monitor)
        # Slider signals (no snapping slider anymore)
        self.saturation_slider.valueChanged.connect(
            self._on_adjustment_slider_changed)
        self.contrast_slider.valueChanged.connect(
            self._on_adjustment_slider_changed)
        self.brightness_slider.valueChanged.connect(
            self._on_adjustment_slider_changed)
        self.hue_slider.valueChanged.connect(
            self._on_adjustment_slider_changed)
        # Reset button signals (no snapping reset anymore)
        self.brightness_reset_button.clicked.connect(
            self._on_reset_brightness_clicked)
        self.saturation_reset_button.clicked.connect(
            self._on_reset_saturation_clicked)
        self.contrast_reset_button.clicked.connect(
            self._on_reset_contrast_clicked)
        self.hue_reset_button.clicked.connect(self._on_reset_hue_clicked)

    # --- Value Conversion Helpers ---
    def _slider_to_factor(self, slider_int_val: int) -> float:
        return float(slider_int_val) / 100.0

    def _factor_to_slider(self, factor_float_val: float) -> int:
        return int(round(factor_float_val * 100.0))

    # --- UI Update Slots ---
    def _update_all_slider_value_labels(self):
        adj = self.current_params.get('adjustments', {})
        self.brightness_value_label.setText(f"{adj.get('brightness', DEFAULT_BRIGHTNESS_FACTOR):.2f}x")
        self.saturation_value_label.setText(f"{adj.get('saturation', DEFAULT_SATURATION_FACTOR):.2f}x")
        self.contrast_value_label.setText(f"{adj.get('contrast', DEFAULT_CONTRAST_FACTOR):.2f}x")
        self.hue_value_label.setText(f"{int(round(adj.get('hue_shift', DEFAULT_HUE_SHIFT))):+d}°")

    def _on_region_or_monitor_changed_in_view(self, monitor_id: int, region_rect_percentage: dict):
        self.current_params['monitor_id'] = monitor_id
        self.current_params['region_rect_percentage'] = region_rect_percentage.copy()
        self._emit_sampling_parameters_changed()

    def _on_adjustment_slider_changed(self):
        self.current_params['adjustments']['saturation'] = self._slider_to_factor(self.saturation_slider.value())
        self.current_params['adjustments']['contrast'] = self._slider_to_factor(self.contrast_slider.value())
        self.current_params['adjustments']['brightness'] = self._slider_to_factor(self.brightness_slider.value())
        self.current_params['adjustments']['hue_shift'] = float(self.hue_slider.value())
        
        self._update_all_slider_value_labels()
        self._emit_sampling_parameters_changed()

    # --- Reset Button Slots ---
    def _on_reset_brightness_clicked(self):
        self.brightness_slider.setValue(self._factor_to_slider(DEFAULT_BRIGHTNESS_FACTOR))

    def _on_reset_saturation_clicked(self):
        self.saturation_slider.setValue(self._factor_to_slider(DEFAULT_SATURATION_FACTOR))

    def _on_reset_contrast_clicked(self):
        self.contrast_slider.setValue(self._factor_to_slider(DEFAULT_CONTRAST_FACTOR))

    def _on_reset_hue_clicked(self):
        self.hue_slider.setValue(DEFAULT_HUE_SHIFT)

    # --- Signal Emission ---
    def _emit_sampling_parameters_changed(self):
        # Make a deep copy to send
        params_to_emit = {
            'monitor_id': self.current_params['monitor_id'],
            'region_rect_percentage': self.current_params['region_rect_percentage'].copy(),
            'adjustments': self.current_params['adjustments'].copy()
        }
        self.sampling_parameters_changed.emit(params_to_emit)

    # --- Public Methods for Manager Interaction ---
    def set_initial_monitor_data(self, monitors_data: list[dict], current_monitor_id: int):
        self._all_monitors_info_cache = monitors_data 
        if hasattr(self.monitor_view_widget, 'blockSignals'):
            self.monitor_view_widget.blockSignals(True)
        self.monitor_view_widget.set_monitors_data(monitors_data, target_mss_id_to_focus=current_monitor_id)
        if hasattr(self.monitor_view_widget, 'blockSignals'):
            self.monitor_view_widget.blockSignals(False)

    def set_current_parameters_from_main(self, params: dict):
        self.current_params.update(params)
        if 'adjustments' in self.current_params:
            self.current_params['adjustments'] = self.current_params['adjustments'].copy()
        if 'region_rect_percentage' in self.current_params:
            self.current_params['region_rect_percentage'] = self.current_params['region_rect_percentage'].copy()

        target_monitor_id = self.current_params.get('monitor_id')
        region_rect_percentage = self.current_params.get('region_rect_percentage')
        adjustments = self.current_params.get('adjustments', {})


        if self.monitor_view_widget:
            if hasattr(self.monitor_view_widget, 'blockSignals'):
                self.monitor_view_widget.blockSignals(True)
            self.monitor_view_widget.set_target_monitor_and_update_view(target_monitor_id) 
            self.monitor_view_widget.set_current_selection_from_params(target_monitor_id, region_rect_percentage)

            if hasattr(self.monitor_view_widget, 'blockSignals'):
                self.monitor_view_widget.blockSignals(False)
        
        # Block all slider signals during update
        all_sliders = [self.brightness_slider, self.saturation_slider, self.contrast_slider, self.hue_slider]
        for s in all_sliders: s.blockSignals(True)
        
        self.brightness_slider.setValue(self._factor_to_slider(adjustments.get('brightness', DEFAULT_BRIGHTNESS_FACTOR)))
        self.saturation_slider.setValue(self._factor_to_slider(adjustments.get('saturation', DEFAULT_SATURATION_FACTOR)))
        self.contrast_slider.setValue(self._factor_to_slider(adjustments.get('contrast', DEFAULT_CONTRAST_FACTOR)))
        self.hue_slider.setValue(int(round(adjustments.get('hue_shift', DEFAULT_HUE_SHIFT))))
        
        for s in all_sliders: s.blockSignals(False)
        
        self._update_all_slider_value_labels()

    def update_sliders_from_external_adjustments(self, new_adjustments: dict):
        self.current_params['adjustments'] = new_adjustments.copy()
        # Block color adjustment sliders only
        adj_sliders = [self.brightness_slider, self.saturation_slider, self.contrast_slider, self.hue_slider]
        for s in adj_sliders: s.blockSignals(True)
        self.brightness_slider.setValue(self._factor_to_slider(new_adjustments.get('brightness', DEFAULT_BRIGHTNESS_FACTOR)))
        self.saturation_slider.setValue(self._factor_to_slider(new_adjustments.get('saturation', DEFAULT_SATURATION_FACTOR)))
        self.contrast_slider.setValue(self._factor_to_slider(new_adjustments.get('contrast', DEFAULT_CONTRAST_FACTOR)))
        self.hue_slider.setValue(int(round(new_adjustments.get('hue_shift', DEFAULT_HUE_SHIFT))))
        for s in adj_sliders: s.blockSignals(False)
        self._update_all_slider_value_labels()

    def update_preview_image(self, pil_image: Image.Image | None):
        if pil_image is None or not self.preview_image_label:
            if self.preview_image_label:
                self.preview_image_label.setText("No image preview.")
                self.preview_image_label.setPixmap(QPixmap())
            return
        try:
            pil_image_rgb = pil_image.convert("RGB") if pil_image.mode != "RGB" else pil_image
            image_data_bytes = pil_image_rgb.tobytes("raw", "RGB")
            q_image = QImage(image_data_bytes, pil_image_rgb.width, pil_image_rgb.height,
                             pil_image_rgb.width * 3, QImage.Format.Format_RGB888)
            if q_image.isNull(): 
                self.preview_image_label.setText("Preview Image Error")
                self.preview_image_label.setPixmap(QPixmap())
                return
            pixmap = QPixmap.fromImage(q_image)
            scaled_pixmap = pixmap.scaled(self.preview_image_label.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            self.preview_image_label.setPixmap(scaled_pixmap)
        except Exception as e:
            print(f"CapturePreviewDialog: Error updating preview: {e}")
            self.preview_image_label.setText("Preview Error.")
            self.preview_image_label.setPixmap(QPixmap())

    # --- Window Event Handlers ---
    def closeEvent(self, event):
        self.dialog_closed.emit()
        super().closeEvent(event)

    def reject(self): 
        self.dialog_closed.emit()
        super().reject()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    dialog = CapturePreviewDialog()
    mock_monitors_data_test = [
        {'id': 1, 'name': 'Monitor 1 (Primary)', 'top': 0, 'left': 0, 'width': 1920, 'height': 1080, 'monitor_dict': {}},
        {'id': 2, 'name': 'Monitor 2 (Side)', 'top': 0, 'left': 1920, 'width': 1080, 'height': 1920, 'monitor_dict': {}}
    ]
    dialog.set_initial_monitor_data(mock_monitors_data_test, current_monitor_id=1)
    
    # Test `get_max_frames` static method (assuming you've moved it here or imported it)
    # This is just for demonstration if it were part of this dialog's test
    # from .set_max_frames_dialog import SetMaxFramesDialog
    # new_max, ok = SetMaxFramesDialog.get_max_frames(dialog, 150)
    # if ok: print(f"Test got max frames: {new_max}")
    
    dialog.show()
    sys.exit(app.exec())