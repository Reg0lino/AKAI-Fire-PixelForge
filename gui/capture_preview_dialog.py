import sys
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QSlider, QPushButton, QWidget,
    QSizePolicy, QSpacerItem, QSplitter, QApplication
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QImage, QPixmap
from PIL import Image

from .monitor_view_widget import MonitorViewWidget

# Slider value interpretation: value / 100.0 = actual factor
SLIDER_MIN_FACTOR_VAL = 0
SLIDER_MAX_FACTOR_VAL = 400

DEFAULT_SATURATION_FACTOR = 2.0
DEFAULT_CONTRAST_FACTOR = 1.5
DEFAULT_BRIGHTNESS_FACTOR = 1.0
DEFAULT_HUE_SHIFT = 0

SLIDER_DEFAULT_SAT_VAL = int(round(DEFAULT_SATURATION_FACTOR * 100.0))
SLIDER_DEFAULT_CON_VAL = int(round(DEFAULT_CONTRAST_FACTOR * 100.0))
SLIDER_DEFAULT_BRI_VAL = int(round(DEFAULT_BRIGHTNESS_FACTOR * 100.0))

SLIDER_MIN_HUE = -180
SLIDER_MAX_HUE = 180
SLIDER_DEFAULT_HUE_VAL = DEFAULT_HUE_SHIFT


class CapturePreviewDialog(QDialog):
    sampling_parameters_changed = pyqtSignal(dict)
    dialog_closed = pyqtSignal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setWindowTitle("👁️ Visual Sampler Configuration")
        self.setMinimumSize(750, 600) # Increased default size for better layout

        # Internal cache of all monitor data, set by set_initial_monitor_data
        self._all_monitors_info_cache: list[dict] = []

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
        self._init_ui()
        self._connect_signals()
        self._update_all_slider_value_labels()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        main_layout.addWidget(splitter, 1)

        self.monitor_view_widget = MonitorViewWidget()
        splitter.addWidget(self.monitor_view_widget)

        right_panel_widget = QWidget()
        right_panel_layout = QVBoxLayout(right_panel_widget)
        right_panel_layout.setContentsMargins(5,5,5,5) # Add some margins

        self.preview_image_label = QLabel("Waiting for preview...")
        self.preview_image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_image_label.setMinimumSize(300, 180) # Ensure it has a decent min size
        self.preview_image_label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Ignored)
        self.preview_image_label.setStyleSheet("background-color: #282828; border: 1px solid #444;")
        right_panel_layout.addWidget(self.preview_image_label, 1) # Allow it to stretch

        controls_widget = QWidget()
        controls_layout = QVBoxLayout(controls_widget)
        controls_layout.setSpacing(10) # Increased spacing

        adj_label_min_width = 70 # For "Saturation:", "Contrast:" etc.
        val_label_min_width = 50 # For "2.00x"

        # Saturation
        sat_layout = QHBoxLayout(); controls_layout.addLayout(sat_layout)
        sat_label = QLabel("Saturation:"); sat_label.setMinimumWidth(adj_label_min_width)
        sat_layout.addWidget(sat_label)
        self.saturation_slider = QSlider(Qt.Orientation.Horizontal)
        self.saturation_slider.setRange(SLIDER_MIN_FACTOR_VAL, SLIDER_MAX_FACTOR_VAL)
        self.saturation_slider.setValue(self._factor_to_slider(self.current_params['adjustments']['saturation']))
        sat_layout.addWidget(self.saturation_slider)
        self.saturation_value_label = QLabel(); self.saturation_value_label.setMinimumWidth(val_label_min_width)
        sat_layout.addWidget(self.saturation_value_label)

        # Contrast
        con_layout = QHBoxLayout(); controls_layout.addLayout(con_layout)
        con_label = QLabel("Contrast:"); con_label.setMinimumWidth(adj_label_min_width)
        con_layout.addWidget(con_label)
        self.contrast_slider = QSlider(Qt.Orientation.Horizontal)
        self.contrast_slider.setRange(SLIDER_MIN_FACTOR_VAL, SLIDER_MAX_FACTOR_VAL)
        self.contrast_slider.setValue(self._factor_to_slider(self.current_params['adjustments']['contrast']))
        con_layout.addWidget(self.contrast_slider)
        self.contrast_value_label = QLabel(); self.contrast_value_label.setMinimumWidth(val_label_min_width)
        con_layout.addWidget(self.contrast_value_label)

        # Brightness
        bri_layout = QHBoxLayout(); controls_layout.addLayout(bri_layout)
        bri_label = QLabel("Brightness:"); bri_label.setMinimumWidth(adj_label_min_width)
        bri_layout.addWidget(bri_label)
        self.brightness_slider = QSlider(Qt.Orientation.Horizontal)
        self.brightness_slider.setRange(SLIDER_MIN_FACTOR_VAL, SLIDER_MAX_FACTOR_VAL)
        self.brightness_slider.setValue(self._factor_to_slider(self.current_params['adjustments']['brightness']))
        bri_layout.addWidget(self.brightness_slider)
        self.brightness_value_label = QLabel(); self.brightness_value_label.setMinimumWidth(val_label_min_width)
        bri_layout.addWidget(self.brightness_value_label)

        # Hue Shift
        hue_layout = QHBoxLayout(); controls_layout.addLayout(hue_layout)
        hue_label = QLabel("Hue Shift:"); hue_label.setMinimumWidth(adj_label_min_width)
        hue_layout.addWidget(hue_label)
        self.hue_slider = QSlider(Qt.Orientation.Horizontal)
        self.hue_slider.setRange(SLIDER_MIN_HUE, SLIDER_MAX_HUE)
        self.hue_slider.setValue(self.current_params['adjustments']['hue_shift'])
        hue_layout.addWidget(self.hue_slider)
        self.hue_value_label = QLabel(); self.hue_value_label.setMinimumWidth(val_label_min_width)
        hue_layout.addWidget(self.hue_value_label)

        self.reset_button = QPushButton("Reset Adjustments")
        controls_layout.addWidget(self.reset_button, 0, Qt.AlignmentFlag.AlignCenter)
        
        right_panel_layout.addWidget(controls_widget)
        right_panel_layout.addStretch(0) # Prevent controls from stretching too much
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

        self.saturation_slider.setValue(SLIDER_DEFAULT_SAT_VAL)
        self.contrast_slider.setValue(SLIDER_DEFAULT_CON_VAL)
        self.brightness_slider.setValue(SLIDER_DEFAULT_BRI_VAL)
        self.hue_slider.setValue(SLIDER_DEFAULT_HUE_VAL)

        self.saturation_slider.blockSignals(False); self.contrast_slider.blockSignals(False)
        self.brightness_slider.blockSignals(False); self.hue_slider.blockSignals(False)
        
        self._on_adjustment_slider_changed()

    def _emit_sampling_parameters_changed(self):
        if self.current_params['monitor_id'] is None or self.current_params['region_rect_percentage'] is None:
            return
        self.sampling_parameters_changed.emit(self.current_params.copy())

    def set_initial_monitor_data(self, monitors_data: list[dict], current_monitor_id: int):
        self._all_monitors_info_cache = monitors_data 
        self.current_params['monitor_id'] = current_monitor_id
        
        # Block signals from monitor_view_widget during this programmatic setup
        # to prevent it from emitting its default/initial state and overwriting params in SSM.
        if hasattr(self.monitor_view_widget, 'blockSignals'): # Check if it's a QObject
            self.monitor_view_widget.blockSignals(True)
        
        self.monitor_view_widget.set_monitors_data(monitors_data, target_mss_id_to_focus=current_monitor_id)
        
        if hasattr(self.monitor_view_widget, 'blockSignals'):
            self.monitor_view_widget.blockSignals(False)
        
        # The actual region will be set by set_current_parameters_from_main subsequently.

    # ... (update_preview_image, _on_reset_clicked, etc. as before) ...

    def set_current_parameters_from_main(self, params: dict):
        """
        Called by ScreenSamplerManager to update the dialog with current sampling parameters
        when the dialog is opened or when the manager's state indicates a change.
        """
        print(f"DEBUG CPD.set_current_parameters_from_main: Received params: {params}")
        
        self.current_params = params.copy() 
        if 'adjustments' in self.current_params:
            self.current_params['adjustments'] = self.current_params['adjustments'].copy()

        target_monitor_id = self.current_params.get('monitor_id')
        region_rect_percentage = self.current_params.get('region_rect_percentage')
        adjustments = self.current_params.get('adjustments', {})

        if self.monitor_view_widget and target_monitor_id is not None and region_rect_percentage:
            # Block signals from monitor_view_widget during this programmatic setup
            if hasattr(self.monitor_view_widget, 'blockSignals'):
                self.monitor_view_widget.blockSignals(True)

            # Ensure MonitorViewWidget is focused on the correct monitor before setting region
            # This might be redundant if set_initial_monitor_data already did this and monitor_id hasn't changed,
            # but it's safer to ensure MVW's internal target_monitor_mss_id is correct.
            self.monitor_view_widget.set_target_monitor_and_update_view(target_monitor_id) 
            
            # Now set the specific region for that monitor
            self.monitor_view_widget.set_current_selection_from_params(
                target_monitor_id,
                region_rect_percentage
            )
            
            if hasattr(self.monitor_view_widget, 'blockSignals'):
                self.monitor_view_widget.blockSignals(False)
        
        # Update adjustment sliders
        self.saturation_slider.blockSignals(True); self.contrast_slider.blockSignals(True)
        self.brightness_slider.blockSignals(True); self.hue_slider.blockSignals(True)
        
        self.saturation_slider.setValue(self._factor_to_slider(adjustments.get('saturation', DEFAULT_SATURATION_FACTOR)))
        self.contrast_slider.setValue(self._factor_to_slider(adjustments.get('contrast', DEFAULT_CONTRAST_FACTOR)))
        self.brightness_slider.setValue(self._factor_to_slider(adjustments.get('brightness', DEFAULT_BRIGHTNESS_FACTOR)))
        self.hue_slider.setValue(adjustments.get('hue_shift', DEFAULT_HUE_SHIFT))
        
        self.saturation_slider.blockSignals(False); self.contrast_slider.blockSignals(False)
        self.brightness_slider.blockSignals(False); self.hue_slider.blockSignals(False)
        
        self._update_all_slider_value_labels()

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
            # Scale to fit the label while maintaining aspect ratio
            scaled_pixmap = pixmap.scaled(self.preview_image_label.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            self.preview_image_label.setPixmap(scaled_pixmap)
        except Exception as e:
            print(f"CapturePreviewDialog: Error updating preview: {e}")
            self.preview_image_label.setText("Preview Error."); self.preview_image_label.setPixmap(QPixmap())

    # ----- METHOD ADDED TO FIX AttributeError -----
    def set_current_parameters_from_main(self, params: dict):
        """
        Called by ScreenSamplerManager to update the dialog with current sampling parameters
        when the dialog is opened or when the manager's state indicates a change.
        """
        print(f"DEBUG CPD.set_current_parameters_from_main: Received params: {params}")
        
        # Deep copy to avoid modifying the manager's dictionary if self.current_params is updated elsewhere
        # Though typically, this dialog's current_params would be the source of truth after user interaction.
        self.current_params = params.copy() 
        # Ensure adjustments is a separate copy if it's nested
        if 'adjustments' in self.current_params:
            self.current_params['adjustments'] = self.current_params['adjustments'].copy()

        target_monitor_id = self.current_params.get('monitor_id')
        region_rect_percentage = self.current_params.get('region_rect_percentage')
        adjustments = self.current_params.get('adjustments', {})

        # Update MonitorViewWidget (which displays the region)
        # It needs to know which monitor these percentages apply to.
        if self.monitor_view_widget and target_monitor_id is not None and region_rect_percentage:
            # If the MonitorViewWidget needs the full list of monitors to correctly scale for the target_monitor_id,
            # ensure it has been set via set_initial_monitor_data or has its own cache.
            # For now, set_initial_monitor_data should have already provided all_monitors_info.
            self.monitor_view_widget.set_target_monitor_and_update_view(target_monitor_id) # Ensures MVW is focused on correct monitor
            self.monitor_view_widget.set_current_selection_from_params(
                target_monitor_id,
                region_rect_percentage
            )
        
        # Update adjustment sliders
        self.saturation_slider.blockSignals(True); self.contrast_slider.blockSignals(True)
        self.brightness_slider.blockSignals(True); self.hue_slider.blockSignals(True)
        
        self.saturation_slider.setValue(self._factor_to_slider(adjustments.get('saturation', DEFAULT_SATURATION_FACTOR)))
        self.contrast_slider.setValue(self._factor_to_slider(adjustments.get('contrast', DEFAULT_CONTRAST_FACTOR)))
        self.brightness_slider.setValue(self._factor_to_slider(adjustments.get('brightness', DEFAULT_BRIGHTNESS_FACTOR)))
        self.hue_slider.setValue(adjustments.get('hue_shift', DEFAULT_HUE_SHIFT))
        
        self.saturation_slider.blockSignals(False); self.contrast_slider.blockSignals(False)
        self.brightness_slider.blockSignals(False); self.hue_slider.blockSignals(False)
        
        self._update_all_slider_value_labels()
        # Do not emit sampling_parameters_changed here, as this is just setting the state from manager.
        # Changes initiated by user interaction within the dialog will emit the signal.

    def closeEvent(self, event):
        self.dialog_closed.emit()
        super().closeEvent(event)

    def reject(self): # Called when Esc is pressed or window X is clicked (if not overridden)
        self.dialog_closed.emit()
        super().reject()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    dialog = CapturePreviewDialog()
    
    print(f"Dialog Initial Adjustments: {dialog.current_params['adjustments']}")

    mock_monitors_data_test = [
        {'id': 1, 'name': 'Monitor 1 (Primary)', 'top': 0, 'left': 0, 'width': 1920, 'height': 1080, 'monitor_dict': {}},
        {'id': 2, 'name': 'Monitor 2 (Side)', 'top': 0, 'left': 1920, 'width': 1080, 'height': 1920, 'monitor_dict': {}}
    ]
    dialog.set_initial_monitor_data(mock_monitors_data_test, current_monitor_id=1)
    
    # Simulate params coming from ScreenSamplerManager after loading prefs
    loaded_params_from_manager_test = {
        'monitor_id': 1,
        'region_rect_percentage': {'x': 0.1, 'y': 0.15, 'width': 0.3, 'height': 0.25}, # Different from dialog default
        'adjustments': {
            'saturation': 2.5, 'contrast': 1.2, 'brightness': 0.9, 'hue_shift': 15
        }
    }
    # Call the newly added method
    dialog.set_current_parameters_from_main(loaded_params_from_manager_test)
    print(f"Dialog Adjustments after set_current_parameters_from_main: {dialog.current_params['adjustments']}")


    def handle_params_changed_test(params): print(f"Dialog Test: Params Changed: {params}")
    dialog.sampling_parameters_changed.connect(handle_params_changed_test)
    dialog.dialog_closed.connect(lambda: print("Dialog Test: Closed"))
    
    try:
        test_img = Image.new('RGB', (320, 180), color = 'darkgrey')
        dialog.update_preview_image(test_img)
    except Exception as e: print(f"Error dummy image: {e}")
    
    dialog.show()
    sys.exit(app.exec())