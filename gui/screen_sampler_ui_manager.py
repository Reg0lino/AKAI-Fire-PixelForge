### START OF FILE screen_sampler_ui_manager.py ###
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
    VALID_QUADRANTS_LIST = ["top-left", "top-right", "bottom-left", "bottom-right", "center", "full-screen"]
    print("ScreenSamplerUIManager: Warning - Could not import ScreenSamplerCore for VALID_QUADRANTS. Using fallback.")
# Define constants used by this UI module
MIN_SAMPLING_FPS = 1
MAX_SAMPLING_FPS = 30 # Can be up to 60 or more, but 30 is reasonable for UI slider
DEFAULT_SAMPLING_FPS = 10
ICON_RECORD = "🎬"
ICON_STOP_RECORDING = "🔴"
ICON_SETTINGS = "⚙️"
# Screen Sampler UI Manager
class ScreenSamplerUIManager(QGroupBox):
    # Signals emitted by this UI manager for the main ScreenSamplerManager to handle
    sampling_control_changed = pyqtSignal(bool, dict) # Emits: is_sampling_active_toggle, basic_sampler_params
    status_message_requested = pyqtSignal(str, int)   # message, duration_ms
    request_monitor_list_population = pyqtSignal()    # When UI needs monitor list (e.g., on first enable)
    show_capture_preview_requested = pyqtSignal()     # When user clicks "Configure Region..."
    record_button_clicked = pyqtSignal()              # User clicked Record/Stop Record
    set_max_frames_button_clicked = pyqtSignal()      # User clicked "Set Max Frames"
    #initialization 
    def __init__(self, parent: QWidget | None = None):
        super().__init__("🖥️ Screen Sampler (Ambient)", parent)
        print(f"--- SSUI __init__ (VERSION: MY_SSUI_MARKER_JULY_22_A) ---")
        # --- UI Element Declarations ---
        self.enable_sampling_button: QPushButton | None = None
        self.configure_preview_button: QPushButton | None = None
        self.monitor_combo: QComboBox | None = None
        self.frequency_slider: QSlider | None = None
        self.frequency_display_label: QLabel | None = None    
        self.record_button: QPushButton | None = None
        self.set_max_frames_button: QPushButton | None = None
        self.recording_status_label: QLabel | None = None    
        self.settings_container_widget: QWidget | None = None # To hide/show optional settings
        self._init_ui()
        self._connect_signals()
        self.set_controls_interaction_enabled(False) # Affects children of settings_container_widget
        self.set_overall_enabled_state(False)       # Affects the whole group box and top-level buttons
        if self.recording_status_label:
            self.recording_status_label.setText("Idle.")
        self.update_record_button_ui(is_recording=False, can_record=False)

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        # --- Top Controls (Always Visible when group is enabled) ---
        top_controls_layout = QHBoxLayout()
        # Shortened button text and set preferred size policy <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<
        self.enable_sampling_button = QPushButton("Screen Sampling")
        self.enable_sampling_button.setObjectName("SamplingToggleButton")
        self.enable_sampling_button.setCheckable(True)
        self.enable_sampling_button.setToolTip(
            "Toggle screen color sampling for ambient light.")
        self.enable_sampling_button.setSizePolicy(
            QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        top_controls_layout.addWidget(self.enable_sampling_button)
        # Shortened button text and set preferred size policy
        self.configure_preview_button = QPushButton("Configure...")
        self.configure_preview_button.setToolTip(
            "Open visual region selector and color adjustments window.")
        self.configure_preview_button.setSizePolicy(
            QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        top_controls_layout.addWidget(self.configure_preview_button)
        main_layout.addLayout(top_controls_layout)
        # --- Settings Container (Can be toggled by enable_sampling_button) ---
        self.settings_container_widget = QWidget()
        settings_layout = QVBoxLayout(self.settings_container_widget)
        settings_layout.setContentsMargins(0, 8, 0, 0)
        settings_layout.setSpacing(8)
        # Monitor Selection
        monitor_layout = QHBoxLayout()
        monitor_layout.addWidget(QLabel("Target Monitor:"))
        self.monitor_combo = QComboBox()
        self.monitor_combo.setToolTip(
            "Select the monitor for screen sampling.")
        self.monitor_combo.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.monitor_combo.addItem("Populating monitors...")
        monitor_layout.addWidget(self.monitor_combo, 1)
        settings_layout.addLayout(monitor_layout)
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
        # Sampler Recording Controls
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
        # REMOVED: addStretch(1) to make the widget vertically compact

# signals
    def _connect_signals(self):
        if self.enable_sampling_button:
            self.enable_sampling_button.toggled.connect(self._on_enable_button_toggled)
        if self.configure_preview_button:
            self.configure_preview_button.clicked.connect(self.show_capture_preview_requested)
        if self.monitor_combo:
            self.monitor_combo.currentIndexChanged.connect(self._on_setting_changed)
        if self.frequency_slider:
            self.frequency_slider.valueChanged.connect(self._on_frequency_slider_changed)
        if self.record_button:
            self.record_button.clicked.connect(self.record_button_clicked)
        if self.set_max_frames_button:
            self.set_max_frames_button.clicked.connect(self.set_max_frames_button_clicked)

# FPS to ms and vice versa
    def _fps_to_ms(self, fps: int) -> int:
        if fps <= 0: return 1000 # Default to 1 FPS if input is invalid
        return int(1000.0 / fps)

# Convert milliseconds to FPS
    def _ms_to_fps(self, ms: int) -> int:
        if ms <= 0: return MIN_SAMPLING_FPS # Avoid division by zero, default to min FPS
        fps = round(1000.0 / ms)
        return max(MIN_SAMPLING_FPS, min(MAX_SAMPLING_FPS, fps)) # Clamp to slider range

# Update the frequency display label
    def _update_frequency_display_label(self, fps_value: int):
        if self.frequency_display_label:
            ms = self._fps_to_ms(fps_value)
            self.frequency_display_label.setText(f"{fps_value} FPS ({ms}ms)")

# --- Slot for the enable button toggle ---
    def _on_enable_button_toggled(self, checked: bool):
        self.set_controls_interaction_enabled(checked) # Enable/disable child settings
        if checked:
            # If enabling and monitor list is still at "Populating...", request population
            if self.monitor_combo and self.monitor_combo.count() > 0 and \
                self.monitor_combo.itemText(0) == "Populating monitors...":
                self.request_monitor_list_population.emit()
            self.status_message_requested.emit("Ambient sampling toggled ON.", 2000)
        else:
            self.status_message_requested.emit("Ambient sampling toggled OFF.", 2000)       
        self._emit_sampling_control_changed() # Emit current state regardless

# --- Slot for the frequency slider change ---
    def _on_frequency_slider_changed(self, fps_value: int):
        self._update_frequency_display_label(fps_value)
        if self.enable_sampling_button and self.enable_sampling_button.isChecked():
            self._emit_sampling_control_changed()

# --- Slot for other settings changes ---
    def _on_setting_changed(self): # For monitor_combo or other general settings
        if self.enable_sampling_button and self.enable_sampling_button.isChecked():
            self._emit_sampling_control_changed()

# --- Emit sampling control changed signal ---
    def _emit_sampling_control_changed(self):
        if not (self.enable_sampling_button and self.monitor_combo and self.frequency_slider):
            return # Not fully initialized
        # Get current state of the UI elements
        is_enabled_toggle = self.enable_sampling_button.isChecked()
        monitor_capture_id = self.monitor_combo.currentData() # UserData stores the mss ID
        # Fallback if currentData is None (e.g. "Populating..." or "No monitors")
        if monitor_capture_id is None:
            # Try to get first valid monitor ID if list is populated
            if self.monitor_combo.count() > 0 and self.monitor_combo.itemData(0) is not None:
                monitor_capture_id = self.monitor_combo.itemData(0)
            else:
                monitor_capture_id = 1 # Absolute fallback if no monitors listed/selectable
        base_params = {
            "monitor_capture_id": monitor_capture_id,
            "frequency_ms": self._fps_to_ms(self.frequency_slider.value())
        }
        self.sampling_control_changed.emit(is_enabled_toggle, base_params)

# --- Methods called by ScreenSamplerManager ---
    def populate_monitors_combo_external(self, monitors_data: list[dict]):
        if not self.monitor_combo: return
        # Clear the combo box and repopulate it with the provided monitor data
        self.monitor_combo.blockSignals(True)
        self.monitor_combo.clear()
        if not monitors_data:
            self.monitor_combo.addItem("No Monitors Found")
            self.monitor_combo.setEnabled(False)
            if self.configure_preview_button:
                self.configure_preview_button.setEnabled(False)
        else:
            for mon_info in monitors_data:
                # Store mss ID in userData for easy retrieval
                self.monitor_combo.addItem(mon_info["name"], userData=mon_info["id"])
            # Enable if sampling is generally allowed for these controls
            parent_enabled = self.settings_container_widget.isEnabled() if self.settings_container_widget else False
            self.monitor_combo.setEnabled(parent_enabled)
            if self.configure_preview_button:
                self.configure_preview_button.setEnabled(self.isEnabled()) # Preview button tied to groupbox state
            if self.monitor_combo.count() > 0:
                pass
        self.monitor_combo.blockSignals(False)

# --- Set the selected monitor in the combo box ---
    def set_selected_monitor_ui(self, monitor_id_to_select: int):
        """Selects a monitor in the combo box by its mss ID."""
        if not self.monitor_combo: return
        for i in range(self.monitor_combo.count()):
            if self.monitor_combo.itemData(i) == monitor_id_to_select:
                self.monitor_combo.setCurrentIndex(i)
                return
        # If not found, select first one if available, or do nothing
        if self.monitor_combo.count() > 0:
            self.monitor_combo.setCurrentIndex(0)

# --- Set the sampling frequency slider and label from a millisecond value ---
    def set_sampling_frequency_ui(self, frequency_ms: int):
        """Sets the sampling frequency slider and label from a millisecond value."""
        if self.frequency_slider and self.frequency_display_label:
            fps = self._ms_to_fps(frequency_ms)
            self.frequency_slider.blockSignals(True)
            self.frequency_slider.setValue(fps)
            self.frequency_slider.blockSignals(False)
            self._update_frequency_display_label(fps) # Update the FPS/ms label

# --- Set the recording status text ---
    def update_record_button_ui(self, is_recording: bool, can_record: bool):
        """Updates the Record button's text, icon, and enabled state."""
        if not self.record_button: return
        if is_recording:
            self.record_button.setText(f"{ICON_STOP_RECORDING} Stop")
            self.record_button.setEnabled(True) # Always allow stopping
            self.record_button.setToolTip("Stop recording the screen sampler output.")
        else:
            self.record_button.setText(f"{ICON_RECORD} Record")
            parent_controls_enabled = self.settings_container_widget.isEnabled() if self.settings_container_widget else False
            self.record_button.setEnabled(parent_controls_enabled and can_record)
            self.record_button.setToolTip("Start recording screen sampler. (Sampler must be active)")

# --- Set the recording status label text ---
    def set_recording_status_text(self, text: str):
        """Sets the text of the recording status label."""
        if self.recording_status_label:
            self.recording_status_label.setText(text)

# --- Set the controls interaction enabled state ---
    def set_controls_interaction_enabled(self, enabled: bool):
        # print(f"DEBUG SSUI.set_controls_interaction_enabled: called with enabled={enabled}")
        if self.settings_container_widget:
            self.settings_container_widget.setEnabled(enabled)
        #    print(f"DEBUG SSUI.set_controls_interaction_enabled: settings_container_widget.setEnabled({enabled})")
        # If the settings container is enabled, we need to check if the monitor combo is populated
        if self.monitor_combo:
            is_populated = self.monitor_combo.count() > 0 and self.monitor_combo.itemText(0) not in ["Populating monitors...", "No Monitors Found"]
            actual_combo_enable = enabled and is_populated
            self.monitor_combo.setEnabled(actual_combo_enable)
        #    print(f"DEBUG SSUI.set_controls_interaction_enabled: monitor_combo.setEnabled({actual_combo_enable}) (is_populated={is_populated})")

# --- Set the overall enabled state of the group box ---
    def set_overall_enabled_state(self, enabled: bool):
        """
        Enable/disable the entire group box and its top-level direct children.
        Called by manager based on global app state (e.g., MIDI connection).
        """
        self.setEnabled(enabled) # Enables/disables the QGroupBox itself
        # Top-level buttons within the group box
        if self.enable_sampling_button:
            self.enable_sampling_button.setEnabled(enabled)
        # Configure button depends on monitors being available (or at least fetchable)
        monitors_seem_available_or_fetchable = True # Assume fetchable if group is enabled
        if self.monitor_combo and self.monitor_combo.count() == 1 and \
            self.monitor_combo.itemText(0) == "No Monitors Found":
            monitors_seem_available_or_fetchable = False
        if self.configure_preview_button:
            self.configure_preview_button.setEnabled(enabled and monitors_seem_available_or_fetchable)
        if not enabled: # If the whole group is disabled by manager
            if self.enable_sampling_button and self.enable_sampling_button.isChecked():
                # This will trigger _on_enable_button_toggled(False), which calls
                # set_controls_interaction_enabled(False) and emits signal
                self.enable_sampling_button.setChecked(False)
            else:
                # If button wasn't checked, still ensure child controls are off
                self.set_controls_interaction_enabled(False)
            # Also ensure recording controls are visually reset if the whole group is disabled
            self.update_record_button_ui(is_recording=False, can_record=False)
            if self.recording_status_label:
                self.recording_status_label.setText("Sampler Disabled.")
        elif enabled and self.monitor_combo and self.monitor_combo.count() > 0 and \
            self.monitor_combo.itemText(0) == "Populating monitors...":
            # If group is enabled and monitors haven't been populated, request it.
            self.request_monitor_list_population.emit()

# --- Force disable sampling UI from external source ---
    def force_disable_sampling_ui(self):
        """Called by ScreenSamplerManager if sampling needs to be stopped externally."""
        if self.enable_sampling_button and self.enable_sampling_button.isChecked():
            self.enable_sampling_button.setChecked(False) # This triggers all necessary UI updates and signals

    def set_sampling_active_state(self, is_active: bool):
        """Sets the 'active' property on the 'Sampling' button for styling."""
        if not self.enable_sampling_button:
            return
        self.enable_sampling_button.setProperty("active", is_active)
        # Force Qt to re-evaluate the stylesheet for this specific widget
        self.style().unpolish(self.enable_sampling_button)
        self.style().polish(self.enable_sampling_button)

# --- For standalone testing of this UI Manager ---
if __name__ == '__main__':
    from PyQt6.QtWidgets import QApplication
    app = QApplication(sys.argv)
    test_ui_manager = ScreenSamplerUIManager()
    # Mock data and connections for testing
    mock_monitors = [
        {"id": 1, "name": "Mock Monitor 1 (1920x1080)", "top": 0, "left": 0, "width": 1920, "height": 1080},
        {"id": 2, "name": "Mock Monitor 2 (2560x1440)", "top": 0, "left": 1920, "width": 2560, "height": 1440},
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
        print(f"Test: sampling_control_changed: Toggled ON = {is_toggled_on}, Params = {params}")
        # Simulate manager enabling record button if sampler is on
        test_ui_manager.update_record_button_ui(is_recording=False, can_record=is_toggled_on)
        if not is_toggled_on:
            test_ui_manager.set_recording_status_text("Idle (Sampler Off)")
        else:
            test_ui_manager.set_recording_status_text("Idle (Sampler On)")
# --- Connect signals to test functions ---
    test_ui_manager.request_monitor_list_population.connect(handle_populate_request)
    test_ui_manager.sampling_control_changed.connect(handle_sampling_control)
    test_ui_manager.status_message_requested.connect(lambda msg, dur: print(f"Test: Status Message: '{msg}' for {dur}ms"))
    test_ui_manager.show_capture_preview_requested.connect(lambda: print("Test: Show Capture Preview Requested"))
    test_ui_manager.record_button_clicked.connect(lambda: print("Test: Record Button Clicked"))
    test_ui_manager.set_max_frames_button_clicked.connect(lambda: print("Test: Set Max Frames Clicked"))
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