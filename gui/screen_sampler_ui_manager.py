# AKAI_Fire_RGB_Controller/gui/screen_sampler_ui_manager.py
import sys
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QComboBox,
    QGroupBox, QLabel, QSlider, QSizePolicy
)
from PyQt6.QtCore import pyqtSignal, Qt
import typing

# This import is for constants or core logic if SSUI needs it directly.
try:
    from features.screen_sampler_core import ScreenSamplerCore
    VALID_QUADRANTS_LIST = ScreenSamplerCore.VALID_QUADRANTS_FOR_DEFAULT_REGIONS
except ImportError:
    VALID_QUADRANTS_LIST = ["top-left", "top-right",
                            "bottom-left", "bottom-right", "center", "full-screen"]
    print("ScreenSamplerUIManager: Warning - Could not import ScreenSamplerCore for VALID_QUADRANTS. Using fallback.")
# Define constants used by this UI module
MIN_SAMPLING_FPS = 1
MAX_SAMPLING_FPS = 60  # Can be up to 60 or more, but 30 is reasonable for UI slider
DEFAULT_SAMPLING_FPS = 20
ICON_RECORD = "🎬"
ICON_STOP_RECORDING = "🔴"
ICON_SETTINGS = "⚙️"
# Screen Sampler UI Manager


class ScreenSamplerUIManager(QGroupBox):
    # Signals emitted by this UI manager for the main ScreenSamplerManager to handle
    # Emits: is_sampling_active_toggle, basic_sampler_params
    sampling_control_changed = pyqtSignal(bool, dict)
    status_message_requested = pyqtSignal(str, int)   # message, duration_ms
    # When UI needs monitor list (e.g., on first enable)
    request_monitor_list_population = pyqtSignal()
    # When user clicks "Configure Region..."
    show_capture_preview_requested = pyqtSignal()
    # User clicked Record/Stop Record
    record_button_clicked = pyqtSignal()
    set_max_frames_button_clicked = pyqtSignal()      # User clicked "Set Max Frames"
    request_cycle_monitor = pyqtSignal()

    # initialization

    def __init__(self, parent: QWidget | None = None):
        super().__init__("🖥️ Screen Sampler (Ambient)", parent)
        print(f"--- SSUI __init__ (VERSION: MY_SSUI_MARKER_JULY_22_A) ---")
        # --- UI Element Declarations ---
        self.enable_sampling_button: QPushButton | None = None
        self.configure_preview_button: QPushButton | None = None
        self.current_monitor_label: QLabel | None = None  # <<< NEW
        self.cycle_monitor_button: QPushButton | None = None  # <<< NEW
        self.sampling_mode_combo: QComboBox | None = None
        self.frequency_slider: QSlider | None = None
        self.frequency_display_label: QLabel | None = None
        self.record_button: QPushButton | None = None
        self.set_max_frames_button: QPushButton | None = None
        self.recording_status_label: QLabel | None = None
        # To hide/show optional settings
        self.settings_container_widget: QWidget | None = None
        self._init_ui()
        self._connect_signals()
        # Affects children of settings_container_widget
        self.set_controls_interaction_enabled(False)
        # Affects the whole group box and top-level buttons
        self.set_overall_enabled_state(False)
        if self.recording_status_label:
            self.recording_status_label.setText("Idle.")
        self.update_record_button_ui(is_recording=False, can_record=False)

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        top_controls_layout = QHBoxLayout()
        self.enable_sampling_button = QPushButton("Screen Sampling")
        self.enable_sampling_button.setObjectName("SamplingToggleButton")
        self.enable_sampling_button.setCheckable(True)
        self.enable_sampling_button.setToolTip(
            "Toggle screen color sampling for ambient light.")
        self.enable_sampling_button.setSizePolicy(
            QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        top_controls_layout.addWidget(self.enable_sampling_button)
        self.configure_preview_button = QPushButton("Configure...")
        self.configure_preview_button.setToolTip(
            "Open configuration window for the selected sampling mode.")
        self.configure_preview_button.setSizePolicy(
            QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        top_controls_layout.addWidget(self.configure_preview_button)
        main_layout.addLayout(top_controls_layout)
        self.settings_container_widget = QWidget()
        settings_layout = QVBoxLayout(self.settings_container_widget)
        settings_layout.setContentsMargins(0, 8, 0, 0)
        settings_layout.setSpacing(8)
        # --- NEW MONITOR DISPLAY & CYCLE BUTTON ---
        monitor_layout_row = QHBoxLayout()
        monitor_layout_row.addWidget(QLabel("Monitor:"))
        self.current_monitor_label = QLabel("Not Selected")  # <<< NEW LABEL
        self.current_monitor_label.setToolTip("Currently selected monitor.")
        self.current_monitor_label.setStyleSheet(
            "QLabel { background-color: #282828; border: 1px solid #444; padding: 4px; border-radius: 3px; }")
        self.current_monitor_label.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        monitor_layout_row.addWidget(self.current_monitor_label, 2)
        self.cycle_monitor_button = QPushButton("Cycle")  # <<< NEW BUTTON
        self.cycle_monitor_button.setToolTip(
            "Cycle to the next available monitor.")
        self.cycle_monitor_button.setFixedWidth(60)  # Compact button
        monitor_layout_row.addWidget(self.cycle_monitor_button)
        monitor_layout_row.addWidget(QLabel("Mode:"))
        self.sampling_mode_combo = QComboBox()
        self.sampling_mode_combo.setToolTip(
            "Select the algorithm for sampling screen colors.")
        self.sampling_mode_combo.addItems(
            ["Region Sampling", "Thumbnail (Fast)", "Palette (Creative)"])
        monitor_layout_row.addWidget(self.sampling_mode_combo, 1)
        settings_layout.addLayout(monitor_layout_row)
        # Sampling Speed/Frequency
        settings_layout.addWidget(QLabel("Sampling Speed:"))
        freq_display_layout = QHBoxLayout()
        self.frequency_slider = QSlider(Qt.Orientation.Horizontal)
        self.frequency_slider.setRange(MIN_SAMPLING_FPS, MAX_SAMPLING_FPS)
        self.frequency_slider.setValue(DEFAULT_SAMPLING_FPS)
        self.frequency_slider.setSingleStep(1)
        self.frequency_slider.setPageStep(5)
        self.frequency_slider.setTickInterval(
            (MAX_SAMPLING_FPS - MIN_SAMPLING_FPS) // 5 if MAX_SAMPLING_FPS > MIN_SAMPLING_FPS + 4 else 1)
        self.frequency_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        freq_display_layout.addWidget(self.frequency_slider, 1)
        self.frequency_display_label = QLabel()
        self.frequency_display_label.setMinimumWidth(90)
        self.frequency_display_label.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self._update_frequency_display_label(DEFAULT_SAMPLING_FPS)
        freq_display_layout.addWidget(self.frequency_display_label)
        settings_layout.addLayout(freq_display_layout)
        # Sampler Recording Controls (unchanged)
        recording_controls_layout = QHBoxLayout()
        recording_controls_layout.setSpacing(6)
        self.record_button = QPushButton(f"{ICON_RECORD} Record")
        self.record_button.setToolTip(
            "Start or Stop recording the screen sampler output.")
        self.record_button.setSizePolicy(
            QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        recording_controls_layout.addWidget(self.record_button)
        self.set_max_frames_button = QPushButton(f"{ICON_SETTINGS} Max")
        self.set_max_frames_button.setToolTip(
            "Set maximum number of frames for sampler recording.")
        self.set_max_frames_button.setSizePolicy(
            QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        recording_controls_layout.addWidget(self.set_max_frames_button)
        self.recording_status_label = QLabel("Idle.")
        self.recording_status_label.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.recording_status_label.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.recording_status_label.setToolTip(
            "Status of the sampler recording.")
        recording_controls_layout.addWidget(self.recording_status_label, 1)
        settings_layout.addLayout(recording_controls_layout)
        main_layout.addWidget(self.settings_container_widget)

# signals
    def _connect_signals(self):
        if self.enable_sampling_button:
            self.enable_sampling_button.toggled.connect(
                self._on_enable_button_toggled)
        if self.configure_preview_button:
            self.configure_preview_button.clicked.connect(
                self.show_capture_preview_requested)
        # self.monitor_combo removed, so no connection here.
        if self.sampling_mode_combo:  # Still connect the mode combo
            self.sampling_mode_combo.currentIndexChanged.connect(
                self._on_setting_changed)
        # Connect the new Cycle button
        if self.cycle_monitor_button:  # <<< NEW
            self.cycle_monitor_button.clicked.connect(
                self.request_cycle_monitor.emit)
        if self.frequency_slider:
            self.frequency_slider.valueChanged.connect(
                self._on_frequency_slider_changed)
        if self.record_button:
            self.record_button.clicked.connect(self.record_button_clicked)
        if self.set_max_frames_button:
            self.set_max_frames_button.clicked.connect(
                self.set_max_frames_button_clicked)


# FPS to ms and vice versa
    def _fps_to_ms(self, fps: int) -> int:
        if fps <= 0:
            return 1000  # Default to 1 FPS if input is invalid
        return int(1000.0 / fps)
# Convert milliseconds to FPS

    def _ms_to_fps(self, ms: int) -> int:
        if ms <= 0:
            return MIN_SAMPLING_FPS  # Avoid division by zero, default to min FPS
        fps = round(1000.0 / ms)
        # Clamp to slider range
        return max(MIN_SAMPLING_FPS, min(MAX_SAMPLING_FPS, fps))
# Update the frequency display label

    def _update_frequency_display_label(self, fps_value: int):
        if self.frequency_display_label:
            ms = self._fps_to_ms(fps_value)
            self.frequency_display_label.setText(f"{fps_value} FPS ({ms}ms)")

# --- Slot for the enable button toggle ---
    def _on_enable_button_toggled(self, checked: bool):
        self.set_controls_interaction_enabled(checked)
        if checked:
            # Removed obsolete monitor_combo check for "Populating..."
            self.status_message_requested.emit(
                "Ambient sampling toggled ON.", 2000)
        else:
            self.status_message_requested.emit(
                "Ambient sampling toggled OFF.", 2000)
        self._emit_sampling_control_changed()

    def _on_frequency_slider_changed(self, fps_value: int):
        self._update_frequency_display_label(fps_value)
        # We only need to emit the signal if the sampler is already running
        # to update its frequency live. The manager will pull the state when starting.
        if self.enable_sampling_button and self.enable_sampling_button.isChecked():
            self.sampling_control_changed.emit(
                True, self.get_current_ui_parameters())

    def _on_setting_changed(self):
        """
        Handles live changes to monitor/mode. Now always emits the signal
        so the manager can update its state even when the sampler is off.
        """
        # We always want the manager to know about the change.
        # The is_enabled state here is less important than the parameters themselves.
        is_enabled = self.enable_sampling_button.isChecked()
        self.sampling_control_changed.emit(
            is_enabled, self.get_current_ui_parameters())

    def _emit_sampling_control_changed(self):
        # This is now only called by the main toggle button.
        is_enabled = self.enable_sampling_button.isChecked()
        params = self.get_current_ui_parameters()
        self.sampling_control_changed.emit(is_enabled, params)

    def set_sampling_frequency_ui(self, frequency_ms: int):
        """Sets the sampling frequency slider and label from a millisecond value."""
        if self.frequency_slider and self.frequency_display_label:
            fps = self._ms_to_fps(frequency_ms)
            self.frequency_slider.blockSignals(True)
            self.frequency_slider.setValue(fps)
            self.frequency_slider.blockSignals(False)
            self._update_frequency_display_label(
                fps)  # Update the FPS/ms label

    def set_monitor_display_name(self, name: str):
        """Updates the QLabel displaying the current monitor name."""
        if self.current_monitor_label:
            self.current_monitor_label.setText(name)

# --- Set the recording status text ---
    def update_record_button_ui(self, is_recording: bool, can_record: bool):
        """Updates the Record button's text, icon, and enabled state."""
        if not self.record_button:
            return
        if is_recording:
            self.record_button.setText(f"{ICON_STOP_RECORDING} Stop")
            self.record_button.setEnabled(True)  # Always allow stopping
            self.record_button.setToolTip(
                "Stop recording the screen sampler output.")
        else:
            self.record_button.setText(f"{ICON_RECORD} Record")
            parent_controls_enabled = self.settings_container_widget.isEnabled(
            ) if self.settings_container_widget else False
            self.record_button.setEnabled(
                parent_controls_enabled and can_record)
            self.record_button.setToolTip(
                "Start recording screen sampler. (Sampler must be active)")
# --- Set the recording status label text ---

    def set_recording_status_text(self, text: str):
        """Sets the text of the recording status label."""
        if self.recording_status_label:
            self.recording_status_label.setText(text)

    def set_controls_interaction_enabled(self, enabled: bool):
        """
        Enables/disables child controls. The Monitor and Mode dropdowns
        are now EXCLUDED from this and are controlled by the parent group's state.
        """
        # These controls are tied to the sampler being active
        if self.frequency_slider:
            self.frequency_slider.setEnabled(enabled)
        if self.record_button:
            self.record_button.setEnabled(enabled)
        if self.set_max_frames_button:
            self.set_max_frames_button.setEnabled(enabled)
        # Update recording button state based on the new enabled state
        self.update_record_button_ui(is_recording=False, can_record=enabled)

    def set_overall_enabled_state(self, enabled: bool):
        """
        Enable/disable the entire group box. Now also handles the state
        of the Monitor Name label and Cycle button directly, without referring to the old combo.
        """
        self.setEnabled(enabled)
        if self.enable_sampling_button:
            self.enable_sampling_button.setEnabled(enabled)
        if self.configure_preview_button:
            self.configure_preview_button.setEnabled(enabled)
        # Explicitly control the monitor label and cycle button
        if self.current_monitor_label:
            self.current_monitor_label.setEnabled(enabled)
            # Ensure it shows "Not Selected" or similar if disabled
            if not enabled:
                self.current_monitor_label.setText("Disabled")
            else:
                # Temporarily set to loading when enabled
                self.current_monitor_label.setText("Loading...")
        if self.cycle_monitor_button:
            self.cycle_monitor_button.setEnabled(enabled)
        # Mode combo is already enabled/disabled by its own logic, no change needed here.
        if not enabled:
            if self.enable_sampling_button and self.enable_sampling_button.isChecked():
                self.enable_sampling_button.setChecked(False)
            else:
                self.set_controls_interaction_enabled(False)
            self.update_record_button_ui(is_recording=False, can_record=False)
            if self.recording_status_label:
                self.recording_status_label.setText("Sampler Disabled.")
        # Removed the `elif enabled and self.monitor_combo...` block as it's no longer needed.
        # Initial population is now strictly handled by main_window.py on connect.

    def force_disable_sampling_ui(self):
        """Called by ScreenSamplerManager if sampling needs to be stopped externally."""
        if self.enable_sampling_button and self.enable_sampling_button.isChecked():
            # This triggers all necessary UI updates and signals
            self.enable_sampling_button.setChecked(False)

    def set_sampling_active_state(self, is_active: bool):
        """Sets the 'active' property on the 'Sampling' button for styling."""
        if not self.enable_sampling_button:
            return
        self.enable_sampling_button.setProperty("active", is_active)
        # Force Qt to re-evaluate the stylesheet for this specific widget
        self.style().unpolish(self.enable_sampling_button)
        self.style().polish(self.enable_sampling_button)

    def set_sampling_mode_ui(self, mode_key: str):
        """Sets the sampling mode combo box from a mode key ('grid', 'thumbnail', 'palette')."""
        if not self.sampling_mode_combo:
            return
        text_to_find = "Grid"
        if mode_key == "thumbnail":
            text_to_find = "Thumbnail"
        elif mode_key == "palette":
            text_to_find = "Palette"
        for i in range(self.sampling_mode_combo.count()):
            if text_to_find in self.sampling_mode_combo.itemText(i):
                self.sampling_mode_combo.setCurrentIndex(i)
                return

    def get_current_ui_parameters(self) -> dict:
        """
        Pulls the current values from all UI controls and returns them
        in a dictionary. The monitor ID is now managed internally by the manager.
        """
        # The monitor_capture_id will be managed by the ScreenSamplerManager's
        # internal state, as it's updated via the "Cycle" button.
        # We'll provide a dummy value here, as the manager will use its own source of truth.
        monitor_capture_id = 1 
        mode_text = self.sampling_mode_combo.currentText()
        mode_key = "grid" # Default
        if "Thumbnail" in mode_text:
            mode_key = "thumbnail"
        elif "Palette" in mode_text:
            mode_key = "palette"
            
        params = {
            "monitor_capture_id": monitor_capture_id, # Manager will ignore this if it knows better
            "frequency_ms": self._fps_to_ms(self.frequency_slider.value()),
            "sampling_mode": mode_key
        }
        return params

# --- For standalone testing of this UI Manager ---
if __name__ == '__main__':
    from PyQt6.QtWidgets import QApplication
    app = QApplication(sys.argv)
    test_ui_manager = ScreenSamplerUIManager()
    # Mock data and connections for testing
    mock_monitors = [
        {"id": 1, "name": "Mock Monitor 1 (1920x1080)",
         "top": 0, "left": 0, "width": 1920, "height": 1080},
        {"id": 2, "name": "Mock Monitor 2 (2560x1440)", "top": 0,
         "left": 1920, "width": 2560, "height": 1440},
    ]
# --- Populate sampled monitors ---

    def handle_populate_request():
        print("Test: request_monitor_list_population received. Populating with mock data.")
        test_ui_manager.populate_monitors_combo_external(mock_monitors)
        # Simulate manager selecting the first monitor after populating
        if mock_monitors:
            test_ui_manager.set_selected_monitor_ui(mock_monitors[0]["id"])
# --- Simulate setting sampling frequency ---

    def handle_sampling_control(is_toggled_on, params):
        print(
            f"Test: sampling_control_changed: Toggled ON = {is_toggled_on}, Params = {params}")
        # Simulate manager enabling record button if sampler is on
        test_ui_manager.update_record_button_ui(
            is_recording=False, can_record=is_toggled_on)
        if not is_toggled_on:
            test_ui_manager.set_recording_status_text("Idle (Sampler Off)")
        else:
            test_ui_manager.set_recording_status_text("Idle (Sampler On)")
# --- Connect signals to test functions ---
    test_ui_manager.request_monitor_list_population.connect(
        handle_populate_request)
    test_ui_manager.sampling_control_changed.connect(handle_sampling_control)
    test_ui_manager.status_message_requested.connect(
        lambda msg, dur: print(f"Test: Status Message: '{msg}' for {dur}ms"))
    test_ui_manager.show_capture_preview_requested.connect(
        lambda: print("Test: Show Capture Preview Requested"))
    test_ui_manager.record_button_clicked.connect(
        lambda: print("Test: Record Button Clicked"))
    test_ui_manager.set_max_frames_button_clicked.connect(
        lambda: print("Test: Set Max Frames Clicked"))
    # --- Test Window Setup ---
    test_window = QWidget()
    test_layout = QVBoxLayout(test_window)
    test_layout.addWidget(test_ui_manager)
    test_window.setWindowTitle("Screen Sampler UI Manager Test")
    test_window.resize(400, 250)
    test_window.show()
    # Simulate enabling by MainWindow
    print("\nTest: Simulating manager enabling the UI overall.")
    test_ui_manager.set_overall_enabled_state(True)
    sys.exit(app.exec())
