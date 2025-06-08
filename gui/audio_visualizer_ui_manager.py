# AKAI_Fire_RGB_Controller/gui/audio_visualizer_ui_manager.py
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QComboBox, QSizePolicy,
    QFrame, QApplication  # Added QApplication for standalone testing
)
from PyQt6.QtCore import Qt, pyqtSignal
# QColor might not be directly used here anymore, but good to have for signals
from PyQt6.QtGui import QColor


class AudioVisualizerUIManager(QWidget):
    # Signals to MainWindow (or an intermediary)
    # Emits the actual device index for PyAudio
    device_selection_changed = pyqtSignal(int)
    # True if user requests enable, False for disable
    enable_visualizer_toggled = pyqtSignal(bool)
    # Key/ID of the selected mode (e.g., "classic_spectrum_bars")
    mode_selection_changed = pyqtSignal(str)
    # User wants to open the settings dialog
    configure_button_clicked = pyqtSignal()

# In class AudioVisualizerUIManager(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)

        # Initialize ALL attributes that will be assigned UI widgets in _init_ui
        self.audio_device_combo: QComboBox | None = None
        self.start_visualizer_button: QPushButton | None = None
        self.stop_visualizer_button: QPushButton | None = None
        self.visualization_mode_combo: QComboBox | None = None
        self.configure_mode_button: QPushButton | None = None
        # End Attribute Initialization

        # Call _init_ui to create the widgets and assign them to the attributes above
        self._init_ui()  # This method creates the UI elements like self.start_visualizer_button

        # Call _connect_signals to connect UI elements (now that they exist)
        self._connect_signals()

        # Set the initial button visibility based on visualizer being off
        # --- THIS LINE IS CORRECTED ---
        self.update_visualizer_action_buttons(False)
        # --- END OF CORRECTION ---


    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(2, 5, 2, 5)
        main_layout.setSpacing(8)  # Spacing between the three main rows

        # --- Row 1: Audio Source ---
        source_layout = QHBoxLayout()
        source_layout.setSpacing(6)
        source_layout.addWidget(QLabel("🎧 Audio Source:"))
        self.audio_device_combo = QComboBox()
        self.audio_device_combo.setToolTip(
            "Select the audio device for loopback capture.")
        self.audio_device_combo.addItem(
            "Scanning...", -1)  # Placeholder, -1 for data
        self.audio_device_combo.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        source_layout.addWidget(self.audio_device_combo, 1)
        main_layout.addLayout(source_layout)

        # --- Row 2: Mode Selection & Setup Button ---
        mode_setup_layout = QHBoxLayout()
        mode_setup_layout.setSpacing(6)

        mode_setup_layout.addWidget(QLabel("✨ Mode:"))
        self.visualization_mode_combo = QComboBox()
        self.visualization_mode_combo.setToolTip(
            "Select the visualization style.")
        # Add modes here - user data is the key for the mode
        self.visualization_mode_combo.addItem(
            "Spectrum Bars", "classic_spectrum_bars")
        self.visualization_mode_combo.addItem(
            "Pulse Wave", "pulse_wave_matrix")
        self.visualization_mode_combo.addItem(
            "Dual VU + Spectrum", "dual_vu_spectrum")
        self.visualization_mode_combo.setSizePolicy(
            QSizePolicy.Policy.MinimumExpanding, QSizePolicy.Policy.Fixed)
        mode_setup_layout.addWidget(self.visualization_mode_combo, 1)

        self.configure_mode_button = QPushButton("⚙️ Setup...")
        self.configure_mode_button.setToolTip(
            "Configure settings for the selected visualizer mode.")
        self.configure_mode_button.setSizePolicy(
            QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed)
        mode_setup_layout.addWidget(self.configure_mode_button)
        main_layout.addLayout(mode_setup_layout)

        # --- Row 3: Start/Stop Buttons ---
        action_buttons_layout = QHBoxLayout()
        action_buttons_layout.setContentsMargins(0, 4, 0, 0)
        action_buttons_layout.addStretch(1)  # Center the active button

        self.start_visualizer_button = QPushButton("▶️ Enable Visualizer")
        self.start_visualizer_button.setToolTip("Start the audio visualizer.")
        self.start_visualizer_button.setSizePolicy(
            QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        action_buttons_layout.addWidget(self.start_visualizer_button)

        self.stop_visualizer_button = QPushButton("⏹️ Disable Visualizer")
        self.stop_visualizer_button.setToolTip("Stop the audio visualizer.")
        self.stop_visualizer_button.setSizePolicy(
            QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        action_buttons_layout.addWidget(self.stop_visualizer_button)

        action_buttons_layout.addStretch(1)
        main_layout.addLayout(action_buttons_layout)
        # --- END Start/Stop Buttons ---

        main_layout.addStretch(1)
        self.setLayout(main_layout)
    def _connect_signals(self):
        if self.audio_device_combo:
            self.audio_device_combo.currentIndexChanged.connect(
                self._on_device_combo_changed)

        # --- NEW CONNECTIONS for start/stop buttons ---
        if self.start_visualizer_button:
            # We emit enable_visualizer_toggled(True) when start is clicked
            self.start_visualizer_button.clicked.connect(
                lambda: self.enable_visualizer_toggled.emit(True))
        if self.stop_visualizer_button:
            # We emit enable_visualizer_toggled(False) when stop is clicked
            self.stop_visualizer_button.clicked.connect(
                lambda: self.enable_visualizer_toggled.emit(False))
        # --- END NEW CONNECTIONS ---

        if self.visualization_mode_combo:
            self.visualization_mode_combo.currentIndexChanged.connect(
                self._on_mode_combo_changed)
        if self.configure_mode_button:
            self.configure_mode_button.clicked.connect(
                self.configure_button_clicked)



    def _on_device_combo_changed(self, index: int):
        # itemData will be the actual device index (int) or -1 for placeholder
        device_data_index = self.audio_device_combo.itemData(index)
        if device_data_index is not None and isinstance(device_data_index, int) and device_data_index != -1:
            self.device_selection_changed.emit(device_data_index)
        # else: ignore selection of "Scanning..." or "No devices..."

    def _on_mode_combo_changed(self, index: int):
        mode_data_key = self.visualization_mode_combo.itemData(
            index)  # This is the string key
        if mode_data_key:
            self.mode_selection_changed.emit(str(mode_data_key))
            # No QStackedWidget to switch here anymore


    def update_visualizer_action_buttons(self, is_visualizer_active: bool):
        """Shows/hides the Start or Stop button based on visualizer state."""
        if self.start_visualizer_button and self.stop_visualizer_button:
            if is_visualizer_active:
                self.start_visualizer_button.setVisible(False)
                self.stop_visualizer_button.setVisible(True)
                self.stop_visualizer_button.setEnabled(
                    True)  # Ensure stop is enabled if active
            else:
                self.start_visualizer_button.setVisible(True)
                self.stop_visualizer_button.setVisible(False)
                # Ensure start is enabled if inactive
                self.start_visualizer_button.setEnabled(True)

    def set_interactive_elements_enabled(self, enabled: bool):
        """
        Enables/disables controls that should typically be inactive while the visualizer is running.
        The main "Enable/Disable" button's enabled state is handled by _update_global_ui_interaction_states in MainWindow.
        """
        if self.audio_device_combo:
            self.audio_device_combo.setEnabled(enabled)
        if self.visualization_mode_combo:
            self.visualization_mode_combo.setEnabled(enabled)
        if self.configure_mode_button:
            self.configure_mode_button.setEnabled(enabled)

    def populate_audio_devices(self, devices: list[dict], default_device_index: int | None):
        """Populates the audio device QComboBox."""
        if not self.audio_device_combo:
            return

        self.audio_device_combo.blockSignals(True)
        self.audio_device_combo.clear()
        current_selection_combo_idx = -1  # This will be the index IN THE COMBOBOX

        if not devices:
            # UserData -1 for placeholder
            self.audio_device_combo.addItem("No input devices found", -1)
        else:
            for i, device_dict in enumerate(devices):
                name = device_dict.get('name', 'Unknown Device')
                actual_device_idx_for_pyaudio = device_dict.get('index', -1)

                display_name = name
                # Prefer a more explicit loopback indicator in the name if available from manager
                if device_dict.get('is_loopback_flag', False) or "loopback" in name.lower():
                    # Ensure "(Loopback)" isn't duplicated if already in name
                    if "(Loopback)" not in display_name and "[Loopback]" not in display_name:
                        display_name = f"{name} (Loopback)"

                self.audio_device_combo.addItem(
                    display_name, actual_device_idx_for_pyaudio)  # Store actual device index

                if default_device_index is not None and actual_device_idx_for_pyaudio == default_device_index:
                    current_selection_combo_idx = i

            if current_selection_combo_idx != -1:
                self.audio_device_combo.setCurrentIndex(
                    current_selection_combo_idx)
            elif self.audio_device_combo.count() > 0:
                # If default not found, select first actual device (that doesn't have -1 as data)
                for i_combo in range(self.audio_device_combo.count()):
                    if self.audio_device_combo.itemData(i_combo) != -1:
                        self.audio_device_combo.setCurrentIndex(i_combo)
                        break

        self.audio_device_combo.blockSignals(False)
        # Manually emit if a valid device is now selected to ensure manager gets initial state
        if self.audio_device_combo.currentIndex() != -1:
            selected_actual_device_idx = self.audio_device_combo.itemData(
                self.audio_device_combo.currentIndex())
            if selected_actual_device_idx is not None and isinstance(selected_actual_device_idx, int) and selected_actual_device_idx != -1:
                # print(f"AVM UI DEBUG: Populate devices - manually emitting device_selection_changed for index {selected_actual_device_idx}")
                self.device_selection_changed.emit(selected_actual_device_idx)
