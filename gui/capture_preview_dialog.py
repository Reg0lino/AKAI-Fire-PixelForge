from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QSlider, QPushButton, QWidget, 
    QSizePolicy, QSpacerItem, QSplitter, QApplication
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QImage, QPixmap
from PIL import Image 

from .monitor_view_widget import MonitorViewWidget

# Slider value interpretation: value / 100.0 = actual factor
SLIDER_MIN_FACTOR_VAL = 0    # Represents 0.0x
SLIDER_MAX_FACTOR_VAL = 400  # Represents 4.0x (Increased range for more boost)
# SLIDER_DEFAULT_FACTOR_VAL = 100 # Represents 1.0x (Original default)

# NEW DEFAULTS FOR PADS (AND THUS PREVIEW)
DEFAULT_SATURATION_FACTOR = 2.0  # Desired default saturation
DEFAULT_CONTRAST_FACTOR = 1.5    # Desired default contrast
DEFAULT_BRIGHTNESS_FACTOR = 1.0  # Brightness default remains 1.0x
DEFAULT_HUE_SHIFT = 0

# Convert factor defaults to slider integer values
SLIDER_DEFAULT_SAT_VAL = int(round(DEFAULT_SATURATION_FACTOR * 100.0))
SLIDER_DEFAULT_CON_VAL = int(round(DEFAULT_CONTRAST_FACTOR * 100.0))
SLIDER_DEFAULT_BRI_VAL = int(round(DEFAULT_BRIGHTNESS_FACTOR * 100.0))

# Hue slider range remains the same
SLIDER_MIN_HUE = -180
SLIDER_MAX_HUE = 180
SLIDER_DEFAULT_HUE_VAL = DEFAULT_HUE_SHIFT


class CapturePreviewDialog(QDialog):
    sampling_parameters_changed = pyqtSignal(dict)
    dialog_closed = pyqtSignal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setWindowTitle("👁️ Visual Sampler Configuration")
        self.setMinimumSize(750, 600)

        # Initialize current_params with NEW defaults
        self.current_params = {
            'monitor_id': 1, 
            'region_rect_percentage': {'x': 0.4, 'y': 0.4, 'width': 0.2, 'height': 0.2},
            'adjustments': {
                'saturation': DEFAULT_SATURATION_FACTOR, 
                'contrast': DEFAULT_CONTRAST_FACTOR, 
                'brightness': DEFAULT_BRIGHTNESS_FACTOR, 
                'hue_shift': DEFAULT_HUE_SHIFT
            }
        }
        self._init_ui() # UI will now use these defaults from current_params for slider init
        self._connect_signals()
        self._update_all_slider_value_labels() # Update labels to reflect new defaults

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        main_layout.addWidget(splitter, 1)

        self.monitor_view_widget = MonitorViewWidget()
        splitter.addWidget(self.monitor_view_widget)

        right_panel_widget = QWidget()
        right_panel_layout = QVBoxLayout(right_panel_widget)

        self.preview_image_label = QLabel("Waiting for preview...")
        self.preview_image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_image_label.setMinimumSize(300, 180)
        self.preview_image_label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Ignored)
        self.preview_image_label.setStyleSheet("background-color: #282828; border: 1px solid #444;")
        right_panel_layout.addWidget(self.preview_image_label, 1)

        controls_widget = QWidget()
        controls_layout = QVBoxLayout(controls_widget)
        controls_layout.setSpacing(8)

        # Saturation
        sat_layout = QHBoxLayout(); controls_layout.addLayout(sat_layout)
        sat_layout.addWidget(QLabel("Saturation:"))
        self.saturation_slider = QSlider(Qt.Orientation.Horizontal)
        self.saturation_slider.setRange(SLIDER_MIN_FACTOR_VAL, SLIDER_MAX_FACTOR_VAL) # Use updated range
        self.saturation_slider.setValue(self._factor_to_slider(self.current_params['adjustments']['saturation'])) # Init with new default
        sat_layout.addWidget(self.saturation_slider)
        self.saturation_value_label = QLabel(); self.saturation_value_label.setMinimumWidth(45)
        sat_layout.addWidget(self.saturation_value_label)

        # Contrast
        con_layout = QHBoxLayout(); controls_layout.addLayout(con_layout)
        con_layout.addWidget(QLabel("Contrast:"))
        self.contrast_slider = QSlider(Qt.Orientation.Horizontal)
        self.contrast_slider.setRange(SLIDER_MIN_FACTOR_VAL, SLIDER_MAX_FACTOR_VAL) # Use updated range
        self.contrast_slider.setValue(self._factor_to_slider(self.current_params['adjustments']['contrast'])) # Init with new default
        con_layout.addWidget(self.contrast_slider)
        self.contrast_value_label = QLabel(); self.contrast_value_label.setMinimumWidth(45)
        con_layout.addWidget(self.contrast_value_label)

        # Brightness
        bri_layout = QHBoxLayout(); controls_layout.addLayout(bri_layout)
        bri_layout.addWidget(QLabel("Brightness:"))
        self.brightness_slider = QSlider(Qt.Orientation.Horizontal)
        self.brightness_slider.setRange(SLIDER_MIN_FACTOR_VAL, SLIDER_MAX_FACTOR_VAL) # Use updated range
        self.brightness_slider.setValue(self._factor_to_slider(self.current_params['adjustments']['brightness'])) # Init with default
        bri_layout.addWidget(self.brightness_slider)
        self.brightness_value_label = QLabel(); self.brightness_value_label.setMinimumWidth(45)
        bri_layout.addWidget(self.brightness_value_label)

        # Hue Shift
        hue_layout = QHBoxLayout(); controls_layout.addLayout(hue_layout)
        hue_layout.addWidget(QLabel("Hue Shift:"))
        self.hue_slider = QSlider(Qt.Orientation.Horizontal)
        self.hue_slider.setRange(SLIDER_MIN_HUE, SLIDER_MAX_HUE)
        self.hue_slider.setValue(self.current_params['adjustments']['hue_shift']) # Init with default
        hue_layout.addWidget(self.hue_slider)
        self.hue_value_label = QLabel(); self.hue_value_label.setMinimumWidth(45)
        hue_layout.addWidget(self.hue_value_label)

        self.reset_button = QPushButton("Reset Adjustments")
        controls_layout.addWidget(self.reset_button, 0, Qt.AlignmentFlag.AlignCenter)
        
        right_panel_layout.addWidget(controls_widget)
        right_panel_widget.setLayout(right_panel_layout)
        splitter.addWidget(right_panel_widget)
        splitter.setSizes([self.width() * 3 // 5, self.width() * 2 // 5]) 

    def _connect_signals(self):
        self.monitor_view_widget.region_selection_changed.connect(self._on_region_or_monitor_changed_in_view)
        self.saturation_slider.valueChanged.connect(self._on_adjustment_slider_changed)
        self.contrast_slider.valueChanged.connect(self._on_adjustment_slider_changed)
        self.brightness_slider.valueChanged.connect(self._on_adjustment_slider_changed)
        self.hue_slider.valueChanged.connect(self._on_adjustment_slider_changed)
        self.reset_button.clicked.connect(self._on_reset_clicked)

    def _slider_to_factor(self, val: int) -> float: return float(val) / 100.0
    def _factor_to_slider(self, factor: float) -> int: return int(round(factor * 100.0))
    
    def _update_all_slider_value_labels(self):
        adj = self.current_params['adjustments']
        self.saturation_value_label.setText(f"{adj['saturation']:.2f}x")
        self.contrast_value_label.setText(f"{adj['contrast']:.2f}x")
        self.brightness_value_label.setText(f"{adj['brightness']:.2f}x")
        self.hue_value_label.setText(f"{adj['hue_shift']:+d}°")

    def _on_region_or_monitor_changed_in_view(self, monitor_id: int, region_rect_percentage: dict):
        self.current_params['monitor_id'] = monitor_id
        self.current_params['region_rect_percentage'] = region_rect_percentage
        self._emit_sampling_parameters_changed()

    def _on_adjustment_slider_changed(self):
        self.current_params['adjustments']['saturation'] = self._slider_to_factor(self.saturation_slider.value())
        self.current_params['adjustments']['contrast'] = self._slider_to_factor(self.contrast_slider.value())
        self.current_params['adjustments']['brightness'] = self._slider_to_factor(self.brightness_slider.value())
        self.current_params['adjustments']['hue_shift'] = self.hue_slider.value()
        self._update_all_slider_value_labels()
        self._emit_sampling_parameters_changed()

    def _on_reset_clicked(self):
        self.saturation_slider.blockSignals(True); self.contrast_slider.blockSignals(True)
        self.brightness_slider.blockSignals(True); self.hue_slider.blockSignals(True)

        # Reset sliders to the NEW default factor values
        self.saturation_slider.setValue(SLIDER_DEFAULT_SAT_VAL)
        self.contrast_slider.setValue(SLIDER_DEFAULT_CON_VAL)
        self.brightness_slider.setValue(SLIDER_DEFAULT_BRI_VAL)
        self.hue_slider.setValue(SLIDER_DEFAULT_HUE_VAL)

        self.saturation_slider.blockSignals(False); self.contrast_slider.blockSignals(False)
        self.brightness_slider.blockSignals(False); self.hue_slider.blockSignals(False)
        
        self._on_adjustment_slider_changed() # Trigger update and emit

    def _emit_sampling_parameters_changed(self):
        if self.current_params['monitor_id'] is None or self.current_params['region_rect_percentage'] is None:
            return
        self.sampling_parameters_changed.emit(self.current_params.copy())

    def set_initial_monitor_data(self, monitors_data: list[dict], current_monitor_id: int):
        self.monitor_view_widget.set_monitors_data(monitors_data, target_mss_id_to_focus=current_monitor_id)

    def update_preview_image(self, pil_image: Image.Image | None):
        if pil_image is None:
            self.preview_image_label.setText("No image preview.")
            self.preview_image_label.setPixmap(QPixmap())
            return
        try:
            pil_image_rgb = None
            if pil_image.mode == "RGB": pil_image_rgb = pil_image
            elif pil_image.mode == "RGBA": pil_image_rgb = pil_image.convert("RGB")
            else: pil_image_rgb = pil_image.convert("RGB")

            if pil_image_rgb is None:
                self.preview_image_label.setText("Preview Image Format Error."); self.preview_image_label.setPixmap(QPixmap()); return

            image_data_bytes = pil_image_rgb.tobytes("raw", "RGB")
            q_image = QImage(image_data_bytes, pil_image_rgb.width, pil_image_rgb.height,
                             pil_image_rgb.width * 3, QImage.Format.Format_RGB888)

            if q_image.isNull():
                self.preview_image_label.setText("Preview Image Error (QImage Null)."); self.preview_image_label.setPixmap(QPixmap()); return
            
            pixmap = QPixmap.fromImage(q_image)
            scaled_pixmap = pixmap.scaled(self.preview_image_label.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            self.preview_image_label.setPixmap(scaled_pixmap)
        except Exception as e:
            print(f"CapturePreviewDialog: Error updating preview: {e}")
            self.preview_image_label.setText("Preview Error."); self.preview_image_label.setPixmap(QPixmap())

    def set_current_parameters_from_main(self, params: dict):
        # When MainWindow sets params (e.g., on dialog open, or if loading a config),
        # these params will override the dialog's initial defaults.
        self.current_params.update(params) 
        
        self.saturation_slider.blockSignals(True); self.contrast_slider.blockSignals(True)
        self.brightness_slider.blockSignals(True); self.hue_slider.blockSignals(True)
        
        adj = self.current_params['adjustments']
        # Sliders are set based on whatever is in `params` or the initial defaults if `params` doesn't have these keys.
        self.saturation_slider.setValue(self._factor_to_slider(adj.get('saturation', DEFAULT_SATURATION_FACTOR)))
        self.contrast_slider.setValue(self._factor_to_slider(adj.get('contrast', DEFAULT_CONTRAST_FACTOR)))
        self.brightness_slider.setValue(self._factor_to_slider(adj.get('brightness', DEFAULT_BRIGHTNESS_FACTOR)))
        self.hue_slider.setValue(adj.get('hue_shift', DEFAULT_HUE_SHIFT))
        
        self.saturation_slider.blockSignals(False); self.contrast_slider.blockSignals(False)
        self.brightness_slider.blockSignals(False); self.hue_slider.blockSignals(False)
        
        self._update_all_slider_value_labels()
        
        if self.monitor_view_widget and self.current_params.get('monitor_id') is not None:
            self.monitor_view_widget.set_current_selection_from_params(
                self.current_params['monitor_id'],
                self.current_params['region_rect_percentage'] 
            )

    def closeEvent(self, event):
        self.dialog_closed.emit()
        super().closeEvent(event)

    def reject(self): 
        self.dialog_closed.emit()
        super().reject()

if __name__ == '__main__':
    import sys
    app = QApplication(sys.argv)
    dialog = CapturePreviewDialog() # Dialog will now init with new defaults
    
    print(f"Dialog Initial Adjustments: {dialog.current_params['adjustments']}") # Should show new defaults

    mock_monitors = [{'id': 1, 'name': 'Monitor 1 (Primary)', 'top': 0, 'left': 0, 'width': 1920, 'height': 1080, 'monitor_dict': {}}]
    dialog.set_initial_monitor_data(mock_monitors, current_monitor_id=1)
    
    def handle_params_changed_test(params): print(f"Dialog Test: Params Changed: {params}")
    dialog.sampling_parameters_changed.connect(handle_params_changed_test)
    dialog.dialog_closed.connect(lambda: print("Dialog Test: Closed"))
    
    try:
        test_img = Image.new('RGB', (320, 180), color = 'darkgrey') # Use a neutral color
        dialog.update_preview_image(test_img)
    except Exception as e: print(f"Error dummy image: {e}")
    
    dialog.show()
    sys.exit(app.exec())