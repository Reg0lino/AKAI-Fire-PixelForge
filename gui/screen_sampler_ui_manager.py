### START OF FILE screen_sampler_ui_manager.py ###
# AKAI_Fire_RGB_Controller/gui/screen_sampler_ui_manager.py
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QComboBox,
    QGroupBox, QLabel, QSlider, QSizePolicy
)
from PyQt6.QtCore import pyqtSignal, Qt

try:
    from features.screen_sampler_core import ScreenSamplerCore
    VALID_QUADRANTS_LIST = ScreenSamplerCore.VALID_QUADRANTS_FOR_DEFAULT_REGIONS
except ImportError:
    VALID_QUADRANTS_LIST = ["top-left", "top-right", "bottom-left", "bottom-right", "center", "full-screen"]
    print("ScreenSamplerUIManager: Warning - Could not import ScreenSamplerCore for VALID_QUADRANTS. Using fallback.")

MIN_SAMPLING_FPS = 1
MAX_SAMPLING_FPS = 30
DEFAULT_SAMPLING_FPS = 10

# --- NEW ICONS (can be adjusted) ---
ICON_RECORD = "🎬" # Or "⏺️"
ICON_STOP_RECORDING = "🔴" # Or "⏹️"
ICON_SETTINGS = "⚙️" # For "Set Max"

class ScreenSamplerUIManager(QGroupBox):
    # Existing signals
    sampling_control_changed = pyqtSignal(bool, dict) # Emits: is_sampling_active, basic_sampler_params
    status_message_requested = pyqtSignal(str, int)
    request_monitor_list_population = pyqtSignal()
    show_capture_preview_requested = pyqtSignal()

    # --- NEW SIGNALS for Sampler Recording ---
    record_button_clicked = pyqtSignal() # Emitted when the record/stop button is clicked
    set_max_frames_button_clicked = pyqtSignal() # Emitted when "Set Max" is clicked
    # ---

    def __init__(self, parent: QWidget | None = None):
        super().__init__("🖥️ Screen Sampler (Ambient)", parent)

        # --- NEW UI ELEMENT DECLARATIONS for Sampler Recording ---
        self.record_button: QPushButton | None = None
        self.set_max_frames_button: QPushButton | None = None
        self.recording_status_label: QLabel | None = None
        # ---

        self._init_ui()
        self._connect_signals()

        self.set_controls_interaction_enabled(False)
        self.set_overall_enabled_state(False)
        self.update_record_button_ui(is_recording=False, can_record=False) # Initial state
        if self.recording_status_label: self.recording_status_label.setText("Idle.")


    ### START OF METHOD ScreenSamplerUIManager._init_ui (MODIFIED) ###
    def _init_ui(self):
        main_layout = QVBoxLayout(self)

        top_controls_layout = QHBoxLayout()
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

        # --- NEW: Sampler Recording Controls Layout ---
        recording_controls_layout = QHBoxLayout()
        recording_controls_layout.setSpacing(6)

        self.record_button = QPushButton(f"{ICON_RECORD} Record")
        self.record_button.setToolTip("Start or Stop recording the screen sampler output.")
        recording_controls_layout.addWidget(self.record_button)

        self.set_max_frames_button = QPushButton(f"{ICON_SETTINGS} Max")
        self.set_max_frames_button.setToolTip("Set maximum number of frames for sampler recording (Default: 200).")
        self.set_max_frames_button.setFixedWidth(self.set_max_frames_button.fontMetrics().horizontalAdvance(f"{ICON_SETTINGS} Max") + 20) # Make it a bit smaller
        recording_controls_layout.addWidget(self.set_max_frames_button)

        self.recording_status_label = QLabel("Idle.")
        self.recording_status_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.recording_status_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.recording_status_label.setToolTip("Status of the sampler recording.")
        recording_controls_layout.addWidget(self.recording_status_label, 1) # Allow label to expand

        settings_layout.addLayout(recording_controls_layout) # Add to settings_layout
        # --- END NEW: Sampler Recording Controls Layout ---

        main_layout.addWidget(self.settings_container_widget)
        main_layout.addStretch(1)
    ### END OF METHOD ScreenSamplerUIManager._init_ui (MODIFIED) ###

    ### START OF METHOD ScreenSamplerUIManager._connect_signals (MODIFIED) ###
    def _connect_signals(self):
        self.enable_sampling_button.toggled.connect(self._on_enable_button_toggled)
        self.configure_preview_button.clicked.connect(self.show_capture_preview_requested)
        self.monitor_combo.currentIndexChanged.connect(self._on_setting_changed)
        self.frequency_slider.valueChanged.connect(self._on_frequency_slider_changed)

        # --- NEW: Connect signals for recording controls ---
        if self.record_button:
            self.record_button.clicked.connect(self.record_button_clicked)
        if self.set_max_frames_button:
            self.set_max_frames_button.clicked.connect(self.set_max_frames_button_clicked)
        # ---
    ### END OF METHOD ScreenSamplerUIManager._connect_signals (MODIFIED) ###

    def populate_monitors_combo_external(self, monitors_data: list[dict]):
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
        if self.enable_sampling_button.isChecked():
            self._emit_sampling_control_changed()

    def _fps_to_ms(self, fps: int) -> int:
        if fps <= 0: return 1000
        return int(1000.0 / fps)

    def _update_frequency_display_label(self, fps: int):
        ms = self._fps_to_ms(fps)
        self.frequency_display_label.setText(f"{fps} FPS ({ms}ms)")

    def _on_enable_button_toggled(self, checked: bool):
        self.set_controls_interaction_enabled(checked) # This will enable/disable sub-controls including new recording ones
        if checked and self.monitor_combo.count() > 0 and self.monitor_combo.itemText(0) == "Populating...":
            self.request_monitor_list_population.emit()
        self._emit_sampling_control_changed()

        if checked:
            self.status_message_requested.emit("Ambient sampling toggled ON.", 2000)
        else:
            self.status_message_requested.emit("Ambient sampling toggled OFF.", 2000)
            # If sampling is turned off, ensure record button text is reset (MainWindow handles actual stopping)
            # self.update_record_button_ui(is_recording=False, can_record=False) # MainWindow will manage this more directly

    def _on_frequency_slider_changed(self, fps_value: int):
        self._update_frequency_display_label(fps_value)
        if self.enable_sampling_button.isChecked():
            self._emit_sampling_control_changed()

    def _on_setting_changed(self):
        if self.enable_sampling_button.isChecked():
            self._emit_sampling_control_changed()

    def _emit_sampling_control_changed(self):
        is_enabled = self.enable_sampling_button.isChecked()
        monitor_capture_id = self.monitor_combo.currentData()
        if monitor_capture_id is None:
            monitor_capture_id = 1
            if self.monitor_combo.count() > 0 and self.monitor_combo.itemData(0) is not None:
                 monitor_capture_id = self.monitor_combo.itemData(0)

        base_params = {
            "monitor_capture_id": monitor_capture_id,
            "frequency_ms": self._fps_to_ms(self.frequency_slider.value())
        }
        self.sampling_control_changed.emit(is_enabled, base_params)

    ### START OF METHOD ScreenSamplerUIManager.set_controls_interaction_enabled (MODIFIED) ###
    def set_controls_interaction_enabled(self, enabled: bool):
        """Enable/disable child controls when sampling is toggled ON/OFF."""
        can_enable_monitor_combo = enabled and self.monitor_combo.count() > 0 and \
                                   self.monitor_combo.itemText(0) not in ["Populating...", "No Monitors Found"]
        self.monitor_combo.setEnabled(can_enable_monitor_combo)
        self.frequency_slider.setEnabled(enabled)
        self.frequency_display_label.setEnabled(enabled)

        # Sampler recording controls are enabled if general sampling controls are,
        # but the Record button's own state (text, specific enable) is managed by MainWindow.
        # We just enable/disable the container elements here.
        # If 'enabled' is True, MainWindow will then decide if the Record button itself can be active.
        if self.record_button:
            self.record_button.setEnabled(enabled) # Basic enable based on sampler activity
        if self.set_max_frames_button:
            self.set_max_frames_button.setEnabled(enabled)
        if self.recording_status_label:
            self.recording_status_label.setEnabled(enabled)
            if not enabled: self.recording_status_label.setText("Idle.") # Reset label if sampler off
    ### END OF METHOD ScreenSamplerUIManager.set_controls_interaction_enabled (MODIFIED) ###

    ### START OF METHOD ScreenSamplerUIManager.set_overall_enabled_state (MODIFIED) ###
    def set_overall_enabled_state(self, enabled: bool):
        """Enable/disable the entire group box (e.g., based on MIDI connection)."""
        self.setEnabled(enabled)
        monitors_seem_available = self.monitor_combo.count() > 0 and \
                                 self.monitor_combo.itemText(0) not in ["Populating...", "No Monitors Found"]
        self.configure_preview_button.setEnabled(enabled and monitors_seem_available)

        if not enabled: # If the whole group is disabled
            if self.enable_sampling_button.isChecked():
                self.enable_sampling_button.setChecked(False) # This will trigger _on_enable_button_toggled
            # Also ensure recording controls are visually reset if the whole group is disabled
            self.update_record_button_ui(is_recording=False, can_record=False)
            if self.recording_status_label: self.recording_status_label.setText("Idle.")

        elif enabled and self.monitor_combo.count() > 0 and self.monitor_combo.itemText(0) == "Populating...":
            self.request_monitor_list_population.emit()
    ### END OF METHOD ScreenSamplerUIManager.set_overall_enabled_state (MODIFIED) ###

    def force_disable_sampling_ui(self):
        """Called by MainWindow if sampling needs to be stopped externally (e.g., MIDI disconnect)."""
        if self.enable_sampling_button.isChecked():
            self.enable_sampling_button.setChecked(False) # This triggers internal logic and signal

    ### START OF NEW METHOD ScreenSamplerUIManager.update_record_button_ui ###
    def update_record_button_ui(self, is_recording: bool, can_record: bool):
        """
        Updates the Record button's text and enabled state.
        Called by MainWindow to reflect the actual recording state.
        Args:
            is_recording (bool): True if recording is currently active.
            can_record (bool): True if conditions allow starting a new recording.
        """
        if not self.record_button:
            return

        if is_recording:
            self.record_button.setText(f"{ICON_STOP_RECORDING} Stop")
            self.record_button.setEnabled(True) # Always allow stopping
            self.record_button.setToolTip("Stop recording the screen sampler output.")
        else:
            self.record_button.setText(f"{ICON_RECORD} Record")
            self.record_button.setEnabled(can_record) # Enable based on whether conditions are met
            self.record_button.setToolTip("Start recording the screen sampler output. (Sampler must be active)")
    ### END OF NEW METHOD ScreenSamplerUIManager.update_record_button_ui ###

    ### START OF NEW METHOD ScreenSamplerUIManager.set_recording_status_text ###
    def set_recording_status_text(self, text: str):
        """Sets the text of the recording status label. Called by MainWindow."""
        if self.recording_status_label:
            self.recording_status_label.setText(text)
    ### END OF NEW METHOD ScreenSamplerUIManager.set_recording_status_text ###

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
        # Simulate MainWindow enabling record button if sampler is on
        ui_manager.update_record_button_ui(is_recording=False, can_record=is_enabled)
        if not is_enabled:
            ui_manager.set_recording_status_text("Idle (Sampler Off)")


    ui_manager.sampling_control_changed.connect(handle_sampling_change_main_test_uim)
    ui_manager.status_message_requested.connect(lambda msg,t: print(f"UI Manager Test: Status - '{msg}'"))

    # --- Test new signals ---
    ui_manager.record_button_clicked.connect(lambda: print("UI Manager Test: Record Button Clicked!"))
    ui_manager.set_max_frames_button_clicked.connect(lambda: print("UI Manager Test: Set Max Frames Button Clicked!"))
    # ---

    test_window = QWidget()
    test_layout = QVBoxLayout(test_window)
    test_layout.addWidget(ui_manager)
    test_window.setWindowTitle("Screen Sampler UI Manager Test (Integrated Recording Controls)")
    test_window.show()

    ui_manager.set_overall_enabled_state(True)

    sys.exit(app.exec())
### END OF FILE screen_sampler_ui_manager.py ###