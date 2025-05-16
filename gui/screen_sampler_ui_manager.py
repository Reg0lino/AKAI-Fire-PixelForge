# AKAI_Fire_RGB_Controller/gui/screen_sampler_ui_manager.py
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QComboBox,
    QGroupBox, QLabel, QSlider, QSizePolicy
)
from PyQt6.QtCore import pyqtSignal, Qt

try:
    from features.screen_sampler_core import ScreenSamplerCore
    VALID_QUADRANTS_LIST = ScreenSamplerCore.VALID_QUADRANTS_FOR_DEFAULT_REGIONS # Use the constant from core
except ImportError:
    VALID_QUADRANTS_LIST = ["top-left", "top-right", "bottom-left", "bottom-right", "center", "full-screen"]
    print("ScreenSamplerUIManager: Warning - Could not import ScreenSamplerCore for VALID_QUADRANTS. Using fallback.")

MIN_SAMPLING_FPS = 1
MAX_SAMPLING_FPS = 30 
DEFAULT_SAMPLING_FPS = 10

class ScreenSamplerUIManager(QGroupBox):
    sampling_control_changed = pyqtSignal(bool, dict)
    status_message_requested = pyqtSignal(str, int)
    request_monitor_list_population = pyqtSignal()
    show_capture_preview_requested = pyqtSignal() 

    def __init__(self, parent: QWidget | None = None):
        super().__init__("🖥️ Screen Sampler (Ambient)", parent) # Emoji already here
        
        self._init_ui()
        self._connect_signals()
            
        self.set_controls_interaction_enabled(False) 
        self.set_overall_enabled_state(False)

    def _init_ui(self):
        main_layout = QVBoxLayout(self)

        top_controls_layout = QHBoxLayout()
        # UPDATED BUTTON TEXT
        self.enable_sampling_button = QPushButton("Toggle Ambient Sampling") 
        self.enable_sampling_button.setCheckable(True)
        self.enable_sampling_button.setToolTip("Toggle screen color sampling for ambient light.")
        top_controls_layout.addWidget(self.enable_sampling_button)

        self.configure_preview_button = QPushButton("Configure Region && Adjustments...")
        self.configure_preview_button.setToolTip("Open visual region selector and color adjustments window.")
        top_controls_layout.addWidget(self.configure_preview_button)
        main_layout.addLayout(top_controls_layout)

        self.settings_container_widget = QWidget()
        settings_layout = QVBoxLayout(self.settings_container_widget)
        settings_layout.setContentsMargins(0,8,0,0)
        settings_layout.setSpacing(8)

        monitor_layout = QHBoxLayout()
        monitor_layout.addWidget(QLabel("Target Monitor:"))
        self.monitor_combo = QComboBox()
        self.monitor_combo.setToolTip("Select the primary monitor for visual sampling configuration.")
        self.monitor_combo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.monitor_combo.addItem("Populating...")
        monitor_layout.addWidget(self.monitor_combo, 1)
        settings_layout.addLayout(monitor_layout)

        # Quadrant (Region) ComboBox is REMOVED.

        settings_layout.addWidget(QLabel("Sampling Speed:"))
        freq_display_layout = QHBoxLayout()
        self.frequency_slider = QSlider(Qt.Orientation.Horizontal)
        self.frequency_slider.setRange(MIN_SAMPLING_FPS, MAX_SAMPLING_FPS)
        self.frequency_slider.setValue(DEFAULT_SAMPLING_FPS)
        self.frequency_slider.setSingleStep(1)
        self.frequency_slider.setPageStep(5)
        self.frequency_slider.setTickInterval((MAX_SAMPLING_FPS - MIN_SAMPLING_FPS) // 5 if MAX_SAMPLING_FPS > MIN_SAMPLING_FPS + 4 else 1)
        self.frequency_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        freq_display_layout.addWidget(self.frequency_slider, 1)

        self.frequency_display_label = QLabel()
        self.frequency_display_label.setMinimumWidth(85)
        self.frequency_display_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self._update_frequency_display_label(DEFAULT_SAMPLING_FPS)
        freq_display_layout.addWidget(self.frequency_display_label)
        settings_layout.addLayout(freq_display_layout)
        
        main_layout.addWidget(self.settings_container_widget)
        main_layout.addStretch(1)

    def _connect_signals(self):
        self.enable_sampling_button.toggled.connect(self._on_enable_button_toggled)
        self.configure_preview_button.clicked.connect(self.show_capture_preview_requested)
        self.monitor_combo.currentIndexChanged.connect(self._on_setting_changed)
        self.frequency_slider.valueChanged.connect(self._on_frequency_slider_changed)

    def populate_monitors_combo_external(self, monitors_data: list[dict]):
        # ... (content as before) ...
        self.monitor_combo.blockSignals(True)
        self.monitor_combo.clear()
        if not monitors_data:
            self.monitor_combo.addItem("No Monitors Found")
            self.monitor_combo.setEnabled(False)
            self.configure_preview_button.setEnabled(False)
        else:
            for mon_info in monitors_data:
                self.monitor_combo.addItem(mon_info["name"], userData=mon_info["id"])
            self.monitor_combo.setEnabled(True)
            self.configure_preview_button.setEnabled(True)
            if self.monitor_combo.count() > 0:
                 self.monitor_combo.setCurrentIndex(0)
        self.monitor_combo.blockSignals(False)
        if self.enable_sampling_button.isChecked(): # If sampling is active, emit change to update monitor if needed
            self._emit_sampling_control_changed()


    def _fps_to_ms(self, fps: int) -> int:
        if fps <= 0: return 1000 
        return int(1000.0 / fps)

    def _update_frequency_display_label(self, fps: int):
        ms = self._fps_to_ms(fps)
        self.frequency_display_label.setText(f"{fps} FPS ({ms}ms)")

    def _on_enable_button_toggled(self, checked: bool):
        self.set_controls_interaction_enabled(checked)
        if checked and self.monitor_combo.count() > 0 and self.monitor_combo.itemText(0) == "Populating...":
            self.request_monitor_list_population.emit()
        self._emit_sampling_control_changed() # This will signal MainWindow
        
        # UPDATED STATUS MESSAGES
        if checked:
            self.status_message_requested.emit("Ambient sampling toggled ON.", 2000)
        else:
            self.status_message_requested.emit("Ambient sampling toggled OFF.", 2000)

    def _on_frequency_slider_changed(self, fps_value: int):
        self._update_frequency_display_label(fps_value)
        if self.enable_sampling_button.isChecked():
            self._emit_sampling_control_changed()

    def _on_setting_changed(self): # Triggered by monitor_combo or frequency_slider
        if self.enable_sampling_button.isChecked(): 
            self._emit_sampling_control_changed()

    def _emit_sampling_control_changed(self):
        is_enabled = self.enable_sampling_button.isChecked()
        monitor_capture_id = self.monitor_combo.currentData()
        if monitor_capture_id is None: # Fallback
            monitor_capture_id = 1 
            if self.monitor_combo.count() > 0 and self.monitor_combo.itemData(0) is not None:
                 monitor_capture_id = self.monitor_combo.itemData(0)

        base_params = {
            "monitor_capture_id": monitor_capture_id,
            "frequency_ms": self._fps_to_ms(self.frequency_slider.value())
        }
        self.sampling_control_changed.emit(is_enabled, base_params)

    def set_controls_interaction_enabled(self, enabled: bool):
        can_enable_monitor_combo = enabled and self.monitor_combo.count() > 0 and \
                                   self.monitor_combo.itemText(0) not in ["Populating...", "No Monitors Found"]
        self.monitor_combo.setEnabled(can_enable_monitor_combo)
        self.frequency_slider.setEnabled(enabled)
        self.frequency_display_label.setEnabled(enabled)

    def set_overall_enabled_state(self, enabled: bool):
        self.setEnabled(enabled)
        monitors_seem_available = self.monitor_combo.count() > 0 and \
                                 self.monitor_combo.itemText(0) not in ["Populating...", "No Monitors Found"]
        self.configure_preview_button.setEnabled(enabled and monitors_seem_available)

        if not enabled and self.enable_sampling_button.isChecked():
            self.enable_sampling_button.setChecked(False) 
        
        if enabled and self.monitor_combo.count() > 0 and self.monitor_combo.itemText(0) == "Populating...":
            self.request_monitor_list_population.emit()

    def force_disable_sampling_ui(self):
        if self.enable_sampling_button.isChecked():
            self.enable_sampling_button.setChecked(False)

# __main__ remains unchanged, for brevity not repeated here.
# If you need it, let me know.
if __name__ == '__main__':
    from PyQt6.QtWidgets import QApplication
    import sys

    app = QApplication(sys.argv)
    ui_manager = ScreenSamplerUIManager()
    
    mock_monitors_list_test_uim = [
        {"id": 1, "name": "Mock Monitor 1 (Primary)"},
        {"id": 2, "name": "Mock Monitor 2 (Secondary)"},
    ]

    def do_populate_monitors_test_uim():
        print("UI Manager Test: Populating monitors now.")
        ui_manager.populate_monitors_combo_external(mock_monitors_list_test_uim)

    ui_manager.request_monitor_list_population.connect(do_populate_monitors_test_uim)
    ui_manager.show_capture_preview_requested.connect(lambda: print("UI Manager Test: Show Capture Preview Requested!"))

    def handle_sampling_change_main_test_uim(is_enabled, params):
        print(f"UI Manager Test: Sampling Control Changed (to MainWindow):")
        print(f"  Enabled: {is_enabled}")
        print(f"  Monitor ID (mss): {params['monitor_capture_id']}")
        print(f"  Frequency: {params['frequency_ms']}ms")

    ui_manager.sampling_control_changed.connect(handle_sampling_change_main_test_uim)
    ui_manager.status_message_requested.connect(lambda msg,t: print(f"UI Manager Test: Status - '{msg}'"))

    test_window = QWidget()
    test_layout = QVBoxLayout(test_window)
    test_layout.addWidget(ui_manager)
    test_window.setWindowTitle("Screen Sampler UI Manager Test (Region Dropdown Removed)")
    test_window.show()

    ui_manager.set_overall_enabled_state(True) 
    
    sys.exit(app.exec())