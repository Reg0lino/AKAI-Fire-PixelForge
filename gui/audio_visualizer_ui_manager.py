# AKAI_Fire_RGB_Controller/gui/audio_visualizer_ui_manager.py
import os
from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QLabel, QComboBox, QPushButton, QGroupBox, QGridLayout,
    QSizePolicy, QFrame
)
from PyQt6.QtCore import pyqtSignal, QSize, Qt
from PyQt6.QtGui import QIcon

# --- Project-specific Imports for get_resource_path ---
try:
    from ..utils import get_resource_path
except ImportError:
    try:
        from utils import get_resource_path
    except ImportError:
        def get_resource_path(relative_path):
            return relative_path

class AudioVisualizerUIManager(QGroupBox):
    device_selection_changed = pyqtSignal(int)
    mode_selection_changed = pyqtSignal(str)
    configure_button_clicked = pyqtSignal()
    enable_visualizer_toggled = pyqtSignal(
        bool)  # True to enable, False to disable

    def __init__(self, parent=None):
        super().__init__("🎵 Audio Visualizer", parent)
        # --- UI Element Declarations ---
        self.audio_source_combo: QComboBox | None = None
        self.visualization_mode_combo: QComboBox | None = None
        self.setup_button: QPushButton | None = None
        self.start_stop_button: QPushButton | None = None
        self.is_active = False  # Internal state to track if visualizer is running
        self._init_ui()

    def _init_ui(self):
        # The main layout for the groupbox will be a QGridLayout
        grid_layout = QGridLayout(self)
        grid_layout.setSpacing(8)
        # Allow the controls column to expand
        grid_layout.setColumnStretch(1, 1)
        # --- Row 0: Audio Source ---
        source_label = QLabel("🎧 Source:")
        source_label.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.audio_source_combo = QComboBox()
        self.audio_source_combo.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.audio_source_combo.setToolTip(
            "Select the audio loopback device to visualize.")
        self.audio_source_combo.currentIndexChanged.connect(
            self._on_device_selection_changed)
        grid_layout.addWidget(source_label, 0, 0)
        grid_layout.addWidget(self.audio_source_combo, 0, 1)
        # --- Row 1: Mode ---
        mode_label = QLabel("✨ Mode:")
        mode_label.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.visualization_mode_combo = QComboBox()
        self.visualization_mode_combo.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.visualization_mode_combo.setToolTip(
            "Select the visualization style.")
        self.visualization_mode_combo.currentIndexChanged.connect(
            self._on_mode_selection_changed)
        grid_layout.addWidget(mode_label, 1, 0)
        grid_layout.addWidget(self.visualization_mode_combo, 1, 1)
        # --- Row 2: Action Buttons ---
        # Use a nested QHBoxLayout to group buttons and align them to the right
        action_button_layout = QHBoxLayout()
        action_button_layout.setContentsMargins(
            0, 4, 0, 0)  # A little top margin for spacing
        action_button_layout.setSpacing(10)
        action_button_layout.addStretch(1)  # Pushes buttons to the right
        self.setup_button = QPushButton(" Setup...")
        try:
            icon_path = get_resource_path(os.path.join(
                "resources", "icons", "settings_gear.png"))
            if os.path.exists(icon_path):
                self.setup_button.setIcon(QIcon(icon_path))
        except:
            pass
        self.setup_button.setToolTip(
            "Open detailed settings for the current visualizer mode.")
        self.setup_button.clicked.connect(self.configure_button_clicked.emit)
        action_button_layout.addWidget(self.setup_button)
        self.start_stop_button = QPushButton()
        self.start_stop_button.setObjectName("VisualizerToggleButton")
        self.start_stop_button.setCheckable(True)
        self.start_stop_button.toggled.connect(self._on_start_stop_toggled)
        self.start_stop_button.setMinimumWidth(140)
        self.update_start_stop_button_appearance(False)
        action_button_layout.addWidget(self.start_stop_button)
        # Add the button layout to the grid, spanning column 1
        grid_layout.addLayout(action_button_layout, 2, 1)
        # Populate modes
        self.populate_visualization_modes()

    def populate_audio_devices(self, devices_list: list, default_index_to_select: int | None):
        self.audio_source_combo.blockSignals(True)
        self.audio_source_combo.clear()
        found_selection = False
        if devices_list:
            for device in devices_list:
                # Add device name and store its index in userData
                self.audio_source_combo.addItem(
                    device['name'], userData=device['index'])
                if default_index_to_select is not None and device['index'] == default_index_to_select:
                    self.audio_source_combo.setCurrentIndex(
                        self.audio_source_combo.count() - 1)
                    found_selection = True
        else:
            self.audio_source_combo.addItem("No loopback devices found")
            self.audio_source_combo.setEnabled(False)
        if not found_selection and self.audio_source_combo.count() > 0:
            self.audio_source_combo.setCurrentIndex(0)
        self.audio_source_combo.blockSignals(False)
        self._on_device_selection_changed(
            self.audio_source_combo.currentIndex())

    def populate_visualization_modes(self):
        self.visualization_mode_combo.clear()
        modes = {
            "Classic Spectrum Bars": "classic_spectrum_bars",
            "Dual VU + Spectrum": "dual_vu_spectrum",
            "Pulse Wave": "pulse_wave_matrix"
        }
        for display_name, mode_key in modes.items():
            self.visualization_mode_combo.addItem(
                display_name, userData=mode_key)

    def _on_device_selection_changed(self, index: int):
        device_index = self.audio_source_combo.itemData(index)
        if device_index is not None:
            self.device_selection_changed.emit(device_index)

    def _on_mode_selection_changed(self, index: int):
        mode_key = self.visualization_mode_combo.itemData(index)
        if mode_key:
            self.mode_selection_changed.emit(mode_key)

    def _on_start_stop_toggled(self, checked: bool):
        # This slot is connected to the button's `toggled` signal.
        # It emits our own custom signal to MainWindow.
        self.update_start_stop_button_appearance(checked)
        self.enable_visualizer_toggled.emit(checked)

    def update_start_stop_button_appearance(self, is_active: bool):
        self.is_active = is_active  # Update internal state tracker
        # Ensure button's checked state matches
        self.start_stop_button.setChecked(is_active)
        if is_active:
            self.start_stop_button.setText("⏹️ Disable Visualizer")
            self.start_stop_button.setToolTip("Stop the audio visualizer.")
            self.start_stop_button.setProperty(
                "active", True)  # For QSS styling
        else:
            self.start_stop_button.setText("▶️ Enable Visualizer")
            self.start_stop_button.setToolTip("Start the audio visualizer.")
            self.start_stop_button.setProperty(
                "active", False)  # For QSS styling
        # Refresh style to apply property changes
        self.start_stop_button.style().unpolish(self.start_stop_button)
        self.start_stop_button.style().polish(self.start_stop_button)

    def set_interactive_elements_enabled(self, enabled: bool):
        """
        Enables/disables controls that should not be changed while the visualizer is active.
        The main start/stop button is handled separately.
        The Setup button state is handled by MainWindow.
        """
        self.audio_source_combo.setEnabled(enabled)
        self.visualization_mode_combo.setEnabled(enabled)

    def toggle_visualization(self):
        """
        Public slot to allow external widgets (like the main menu bar)
        to toggle the visualizer's enabled state.
        """
        # --- Use the correct button attribute name 'enable_visualizer_button' ---
        if hasattr(self, 'enable_visualizer_button') and self.enable_visualizer_button:
            self.enable_visualizer_button.click()
