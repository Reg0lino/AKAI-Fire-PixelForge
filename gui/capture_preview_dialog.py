# AKAI_Fire_RGB_Controller/gui/capture_preview_dialog.py
import sys
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QSlider, QPushButton, QWidget,
    QSizePolicy, QSpacerItem, QSplitter, QApplication, QCheckBox
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QImage, QPixmap
from PIL import Image # Keep PIL import


try:
    from .monitor_view_widget import MonitorViewWidget
except ImportError:
    print("CapturePreviewDialog FATAL: Could not import .monitor_view_widget")
    class MonitorViewWidget(QWidget): # Minimal placeholder
        region_selection_changed = pyqtSignal(int, dict)
        def __init__(self, parent=None): super().__init__(parent)
        def set_monitors_data(self, monitors, target_mss_id_to_focus=None): pass
        def set_target_monitor_and_update_view(self, monitor_id): pass
        def set_current_selection_from_params(self, monitor_id, region_rect_percentage): pass

try:
    from features.screen_sampler_core import ScreenSamplerCore
except ImportError:
    print("CapturePreviewDialog WARNING: Could not import ScreenSamplerCore from features. Using fallback defaults.")
    class ScreenSamplerCore: # Minimal placeholder
        DEFAULT_ADJUSTMENTS = {'brightness': 1.0, 'contrast': 1.0, 'saturation': 1.0, 'hue_shift': 0}


# Slider value interpretation constants (as defined in your original file)
SLIDER_MIN_FACTOR_VAL = 0    # Represents 0.0x
SLIDER_MAX_FACTOR_VAL = 400  # Represents 4.0x (e.g. for Brightness, Contrast, Saturation)

DEFAULT_SATURATION_FACTOR = 1.0 # Default to 1.0x for S, C, B
DEFAULT_CONTRAST_FACTOR = 1.0
DEFAULT_BRIGHTNESS_FACTOR = 1.0
DEFAULT_HUE_SHIFT = 0          # Degrees

# Calculate default slider integer values from factors
SLIDER_DEFAULT_SAT_VAL = int(round(DEFAULT_SATURATION_FACTOR * 100.0))
SLIDER_DEFAULT_CON_VAL = int(round(DEFAULT_CONTRAST_FACTOR * 100.0))
SLIDER_DEFAULT_BRI_VAL = int(round(DEFAULT_BRIGHTNESS_FACTOR * 100.0))

SLIDER_MIN_HUE = -180
SLIDER_MAX_HUE = 180
SLIDER_DEFAULT_HUE_VAL = DEFAULT_HUE_SHIFT


class CapturePreviewDialog(QDialog):
    sampling_parameters_changed = pyqtSignal(dict) # monitor_id, region_rect_percentage, adjustments
    dialog_closed = pyqtSignal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setWindowTitle("👁️ Visual Sampler Configuration")
        self.setMinimumSize(750, 600)

        self._all_monitors_info_cache: list[dict] = []
        self.current_params = {
            'monitor_id': 1,
            'region_rect_percentage': {'x': 0.4, 'y': 0.4, 'width': 0.2, 'height': 0.2},
            'adjustments': ScreenSamplerCore.DEFAULT_ADJUSTMENTS.copy() # Use defined default
        }
        self._init_ui()
        self._connect_signals()
        self._update_all_slider_value_labels() # Initial update based on defaults

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        main_layout.addWidget(splitter, 1)
        self.monitor_view_widget = MonitorViewWidget()
        splitter.addWidget(self.monitor_view_widget)
        right_panel_widget = QWidget()
        right_panel_layout = QVBoxLayout(right_panel_widget)
        right_panel_layout.setContentsMargins(5, 5, 5, 5)
        self.preview_image_label = QLabel("Waiting for preview...")
        self.preview_image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_image_label.setMinimumSize(300, 180)
        self.preview_image_label.setSizePolicy(
            QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Ignored)
        self.preview_image_label.setStyleSheet(
            "background-color: #282828; border: 1px solid #444;")
        right_panel_layout.addWidget(self.preview_image_label, 1)
        controls_widget = QWidget()
        controls_layout = QVBoxLayout(controls_widget)
        controls_layout.setSpacing(10)
        adj_label_min_width = 70
        val_label_min_width = 55
        # --- REORDERED SLIDERS ---
        # 1. Brightness
        bri_layout = QHBoxLayout()
        bri_label = QLabel("Brightness:")
        bri_label.setMinimumWidth(adj_label_min_width)
        bri_layout.addWidget(bri_label)
        self.brightness_slider = QSlider(Qt.Orientation.Horizontal)
        self.brightness_slider.setRange(
            SLIDER_MIN_FACTOR_VAL, SLIDER_MAX_FACTOR_VAL)
        self.brightness_slider.setValue(self._factor_to_slider(
            self.current_params['adjustments']['brightness']))
        bri_layout.addWidget(self.brightness_slider)
        self.brightness_value_label = QLabel()
        self.brightness_value_label.setMinimumWidth(val_label_min_width)
        bri_layout.addWidget(self.brightness_value_label)
        controls_layout.addLayout(bri_layout)
        # 2. Saturation
        sat_layout = QHBoxLayout()
        sat_label = QLabel("Saturation:")
        sat_label.setMinimumWidth(adj_label_min_width)
        sat_layout.addWidget(sat_label)
        self.saturation_slider = QSlider(Qt.Orientation.Horizontal)
        self.saturation_slider.setRange(
            SLIDER_MIN_FACTOR_VAL, SLIDER_MAX_FACTOR_VAL)
        self.saturation_slider.setValue(self._factor_to_slider(
            self.current_params['adjustments']['saturation']))
        sat_layout.addWidget(self.saturation_slider)
        self.saturation_value_label = QLabel()
        self.saturation_value_label.setMinimumWidth(val_label_min_width)
        sat_layout.addWidget(self.saturation_value_label)
        controls_layout.addLayout(sat_layout)
        # 3. Contrast
        con_layout = QHBoxLayout()
        con_label = QLabel("Contrast:")
        con_label.setMinimumWidth(adj_label_min_width)
        con_layout.addWidget(con_label)
        self.contrast_slider = QSlider(Qt.Orientation.Horizontal)
        self.contrast_slider.setRange(SLIDER_MIN_FACTOR_VAL, SLIDER_MAX_FACTOR_VAL)
        self.contrast_slider.setValue(self._factor_to_slider(
            self.current_params['adjustments']['contrast']))
        con_layout.addWidget(self.contrast_slider)
        self.contrast_value_label = QLabel()
        self.contrast_value_label.setMinimumWidth(val_label_min_width)
        con_layout.addWidget(self.contrast_value_label)
        controls_layout.addLayout(con_layout)
        # 4. Hue Shift
        hue_layout = QHBoxLayout()
        hue_label = QLabel("Hue Shift:")
        hue_label.setMinimumWidth(adj_label_min_width)
        hue_layout.addWidget(hue_label)
        self.hue_slider = QSlider(Qt.Orientation.Horizontal)
        self.hue_slider.setRange(SLIDER_MIN_HUE, SLIDER_MAX_HUE)
        self.hue_slider.setValue(int(
            # Initial value as int
            round(self.current_params['adjustments']['hue_shift'])))
        hue_layout.addWidget(self.hue_slider)
        self.hue_value_label = QLabel()
        self.hue_value_label.setMinimumWidth(val_label_min_width)
        hue_layout.addWidget(self.hue_value_label)
        controls_layout.addLayout(hue_layout)
        # --- NEW: Live Sync Checkbox ---
        self.sync_checkbox = QCheckBox("Live Sync with Main Window Knobs")
        self.sync_checkbox.setToolTip(
            "When checked, these sliders will update in real-time if the\n"
            "main window's knobs are adjusted while this dialog is open.\n"
            "Uncheck to prevent sliders from moving unexpectedly while you adjust them."
        )
        self.sync_checkbox.setChecked(True)  # Default to ON
        controls_layout.addWidget(self.sync_checkbox, 0,
                                Qt.AlignmentFlag.AlignCenter)
        self.reset_button = QPushButton("Reset Adjustments")
        controls_layout.addWidget(self.reset_button, 0,
                                Qt.AlignmentFlag.AlignCenter)
        right_panel_layout.addWidget(controls_widget)
        right_panel_layout.addStretch(0)
        right_panel_widget.setLayout(right_panel_layout)
        splitter.addWidget(right_panel_widget)
        splitter.setSizes([self.width() * 3 // 5, self.width()
                        * 2 // 5])  # Initial split ratio

    def _connect_signals(self):
        self.monitor_view_widget.region_selection_changed.connect(self._on_region_or_monitor_changed_in_view)
        self.saturation_slider.valueChanged.connect(self._on_adjustment_slider_changed)
        self.contrast_slider.valueChanged.connect(self._on_adjustment_slider_changed)
        self.brightness_slider.valueChanged.connect(self._on_adjustment_slider_changed)
        self.hue_slider.valueChanged.connect(self._on_adjustment_slider_changed)
        self.reset_button.clicked.connect(self._on_reset_clicked)

    def _slider_to_factor(self, slider_int_val: int) -> float:
        return float(slider_int_val) / 100.0

    def _factor_to_slider(self, factor_float_val: float) -> int:
        return int(round(factor_float_val * 100.0))

    def _update_all_slider_value_labels(self):
        # Ensure 'adjustments' key exists and use defaults if specific keys are missing
        adj = self.current_params.get('adjustments', ScreenSamplerCore.DEFAULT_ADJUSTMENTS.copy())
        
        sat_val = adj.get('saturation', DEFAULT_SATURATION_FACTOR)
        con_val = adj.get('contrast', DEFAULT_CONTRAST_FACTOR)
        bri_val = adj.get('brightness', DEFAULT_BRIGHTNESS_FACTOR)
        hue_val_float = adj.get('hue_shift', DEFAULT_HUE_SHIFT) # This is a float

        if hasattr(self, 'saturation_value_label') and self.saturation_value_label:
            self.saturation_value_label.setText(f"{sat_val:.2f}x")
        if hasattr(self, 'contrast_value_label') and self.contrast_value_label:
            self.contrast_value_label.setText(f"{con_val:.2f}x")
        if hasattr(self, 'brightness_value_label') and self.brightness_value_label:
            self.brightness_value_label.setText(f"{bri_val:.2f}x")
        
        if hasattr(self, 'hue_value_label') and self.hue_value_label:
            # --- CORRECTED: Convert hue_val (float) to int for display with '%+d' ---
            self.hue_value_label.setText(f"{int(round(hue_val_float)):+d}°")
            # --- END CORRECTION ---

    def _on_region_or_monitor_changed_in_view(self, monitor_id: int, region_rect_percentage: dict):
        self.current_params['monitor_id'] = monitor_id
        self.current_params['region_rect_percentage'] = region_rect_percentage.copy() # Ensure it's a copy
        self._emit_sampling_parameters_changed()

    def _on_adjustment_slider_changed(self):
        # This method is called when ANY slider value changes.
        # It reads all slider values, updates self.current_params, then emits.
        self.current_params['adjustments']['saturation'] = self._slider_to_factor(self.saturation_slider.value())
        self.current_params['adjustments']['contrast'] = self._slider_to_factor(self.contrast_slider.value())
        self.current_params['adjustments']['brightness'] = self._slider_to_factor(self.brightness_slider.value())
        self.current_params['adjustments']['hue_shift'] = float(self.hue_slider.value()) # Slider provides int, store as float
        
        self._update_all_slider_value_labels() # Update text displays
        self._emit_sampling_parameters_changed() # Emit all params

    def _on_reset_clicked(self):
        # Block signals to prevent multiple emissions of sampling_parameters_changed
        self.saturation_slider.blockSignals(True); self.contrast_slider.blockSignals(True)
        self.brightness_slider.blockSignals(True); self.hue_slider.blockSignals(True)

        # Set sliders to default integer values
        self.brightness_slider.setValue(SLIDER_DEFAULT_BRI_VAL) # Set Brightness first
        self.saturation_slider.setValue(SLIDER_DEFAULT_SAT_VAL)
        self.contrast_slider.setValue(SLIDER_DEFAULT_CON_VAL)
        self.hue_slider.setValue(SLIDER_DEFAULT_HUE_VAL) # Hue slider default is int

        # Unblock signals
        self.saturation_slider.blockSignals(False); self.contrast_slider.blockSignals(False)
        self.brightness_slider.blockSignals(False); self.hue_slider.blockSignals(False)
        
        # Manually trigger one update cycle after all sliders are reset
        self._on_adjustment_slider_changed()

    def _emit_sampling_parameters_changed(self):
        # Make a deep copy to send, especially for nested dicts like 'adjustments'
        params_to_emit = self.current_params.copy()
        if 'adjustments' in params_to_emit:
            params_to_emit['adjustments'] = params_to_emit['adjustments'].copy()
        if 'region_rect_percentage' in params_to_emit:
             params_to_emit['region_rect_percentage'] = params_to_emit['region_rect_percentage'].copy()

        self.sampling_parameters_changed.emit(params_to_emit)

    def set_initial_monitor_data(self, monitors_data: list[dict], current_monitor_id: int):
        self._all_monitors_info_cache = monitors_data 
        # self.current_params['monitor_id'] = current_monitor_id # Set by set_current_parameters_from_main
        
        if hasattr(self.monitor_view_widget, 'blockSignals'):
            self.monitor_view_widget.blockSignals(True)
        self.monitor_view_widget.set_monitors_data(monitors_data, target_mss_id_to_focus=current_monitor_id)
        if hasattr(self.monitor_view_widget, 'blockSignals'):
            self.monitor_view_widget.blockSignals(False)
        
    def set_current_parameters_from_main(self, params: dict):
        """
        Called by ScreenSamplerManager to update the dialog with current sampling parameters
        when the dialog is opened or when the manager's state indicates a change.
        This is the SINGLE CORRECT version of this method.
        """
        # print(f"DEBUG CPD.set_current_parameters_from_main: Received params: {params}") # Keep for debugging
        
        self.current_params = params.copy() 
        if 'adjustments' in self.current_params:
            self.current_params['adjustments'] = self.current_params['adjustments'].copy()

        target_monitor_id = self.current_params.get('monitor_id')
        region_rect_percentage = self.current_params.get('region_rect_percentage')
        # Ensure adjustments is always a dict, defaulting to ScreenSamplerCore's defaults if missing
        adjustments = self.current_params.get('adjustments', ScreenSamplerCore.DEFAULT_ADJUSTMENTS.copy()).copy()

        if self.monitor_view_widget and target_monitor_id is not None and region_rect_percentage:
            if hasattr(self.monitor_view_widget, 'blockSignals'):
                self.monitor_view_widget.blockSignals(True)
            self.monitor_view_widget.set_target_monitor_and_update_view(target_monitor_id) 
            self.monitor_view_widget.set_current_selection_from_params(
                target_monitor_id,
                region_rect_percentage
            )
            if hasattr(self.monitor_view_widget, 'blockSignals'):
                self.monitor_view_widget.blockSignals(False)
        
        self.saturation_slider.blockSignals(True); self.contrast_slider.blockSignals(True)
        self.brightness_slider.blockSignals(True); self.hue_slider.blockSignals(True)
        
        # Set sliders based on the order: Brightness, Saturation, Contrast, Hue
        self.brightness_slider.setValue(self._factor_to_slider(adjustments.get('brightness', DEFAULT_BRIGHTNESS_FACTOR)))
        self.saturation_slider.setValue(self._factor_to_slider(adjustments.get('saturation', DEFAULT_SATURATION_FACTOR)))
        self.contrast_slider.setValue(self._factor_to_slider(adjustments.get('contrast', DEFAULT_CONTRAST_FACTOR)))
        
        hue_val_from_params = adjustments.get('hue_shift', DEFAULT_HUE_SHIFT)
        self.hue_slider.setValue(int(round(hue_val_from_params))) # CORRECTED CAST
        
        self.saturation_slider.blockSignals(False); self.contrast_slider.blockSignals(False)
        self.brightness_slider.blockSignals(False); self.hue_slider.blockSignals(False)
        
        self._update_all_slider_value_labels() # Update display labels

    def update_sliders_from_external_adjustments(self, new_adjustments: dict):
        """
        Updates the dialog's sliders and value labels from an external source
        (e.g., when MainWindow knobs change sampler parameters).
        Checks the sync checkbox before applying changes.
        """
        if self.sync_checkbox and not self.sync_checkbox.isChecked():
            return  # Do not update sliders if live sync is disabled by the user.
        # print(f"CPD TRACE: update_sliders_from_external_adjustments called with: {new_adjustments}") # Optional
        self.current_params['adjustments'] = new_adjustments.copy()
        self.saturation_slider.blockSignals(True)
        self.contrast_slider.blockSignals(True)
        self.brightness_slider.blockSignals(True)
        self.hue_slider.blockSignals(True)
        self.brightness_slider.setValue(self._factor_to_slider(
            new_adjustments.get('brightness', DEFAULT_BRIGHTNESS_FACTOR)))
        self.saturation_slider.setValue(self._factor_to_slider(
            new_adjustments.get('saturation', DEFAULT_SATURATION_FACTOR)))
        self.contrast_slider.setValue(self._factor_to_slider(
            new_adjustments.get('contrast', DEFAULT_CONTRAST_FACTOR)))
        hue_val = new_adjustments.get('hue_shift', DEFAULT_HUE_SHIFT)
        self.hue_slider.setValue(int(round(hue_val)))  # CORRECTED CAST
        self.saturation_slider.blockSignals(False)
        self.contrast_slider.blockSignals(False)
        self.brightness_slider.blockSignals(False)
        self.hue_slider.blockSignals(False)
        self._update_all_slider_value_labels()

    def update_preview_image(self, pil_image: Image.Image | None):
        if pil_image is None:
            self.preview_image_label.setText("No image preview.")
            self.preview_image_label.setPixmap(QPixmap()); return
        try:
            pil_image_rgb = pil_image.convert("RGB") if pil_image.mode != "RGB" else pil_image
            image_data_bytes = pil_image_rgb.tobytes("raw", "RGB")
            q_image = QImage(image_data_bytes, pil_image_rgb.width, pil_image_rgb.height,
                             pil_image_rgb.width * 3, QImage.Format.Format_RGB888)
            if q_image.isNull(): self.preview_image_label.setText("Preview Image Error (QImage Null)"); self.preview_image_label.setPixmap(QPixmap()); return
            pixmap = QPixmap.fromImage(q_image)
            scaled_pixmap = pixmap.scaled(self.preview_image_label.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            self.preview_image_label.setPixmap(scaled_pixmap)
        except Exception as e:
            print(f"CapturePreviewDialog: Error updating preview: {e}")
            self.preview_image_label.setText("Preview Error."); self.preview_image_label.setPixmap(QPixmap())

    def closeEvent(self, event):
        self.dialog_closed.emit()
        super().closeEvent(event)

    def reject(self): 
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
    loaded_params_from_manager_test = {
        'monitor_id': 1,
        'region_rect_percentage': {'x': 0.1, 'y': 0.15, 'width': 0.3, 'height': 0.25},
        'adjustments': {'saturation': 2.5, 'contrast': 1.2, 'brightness': 0.9, 'hue_shift': -15.0 } # Hue as float
    }
    dialog.set_current_parameters_from_main(loaded_params_from_manager_test)
    print(f"Dialog Adjustments after set_current_parameters_from_main: {dialog.current_params['adjustments']}")
    def handle_params_changed_test(params): print(f"Dialog Test: Params Changed: {params}")
    dialog.sampling_parameters_changed.connect(handle_params_changed_test)
    dialog.dialog_closed.connect(lambda: print("Dialog Test: Closed"))
    try: test_img = Image.new('RGB', (320, 180), color = 'darkgrey'); dialog.update_preview_image(test_img)
    except Exception as e: print(f"Error dummy image: {e}")
    dialog.show()
    sys.exit(app.exec())