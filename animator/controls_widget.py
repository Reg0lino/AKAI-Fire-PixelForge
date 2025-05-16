# AKAI_Fire_RGB_Controller/animator/controls_widget.py
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
                             QSlider, QSpinBox, QFrame, QMenu, QSpacerItem, QSizePolicy) # Added QSpacerItem, QSizePolicy
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QAction, QKeySequence # For status tip shortcuts

try:
    from .model import DEFAULT_FRAME_DELAY_MS
except ImportError:
    DEFAULT_FRAME_DELAY_MS = 200 

MIN_SPEED_VALUE = 1
MAX_SPEED_VALUE = 100 
DEFAULT_SPEED_VALUE = 50 

MIN_FRAME_DELAY_MS = 5     
MAX_FRAME_DELAY_MS = 1667  

# --- Icons (Unicode Emojis) ---
ICON_ADD_FRAME = "➕" # Main button for adding
ICON_ADD_SNAPSHOT = "📷"
ICON_ADD_BLANK = "⬛"
ICON_DUPLICATE = "📋"
ICON_DELETE = "🗑️"

ICON_NAV_FIRST = "|◀"
ICON_NAV_PREV = "◀"
ICON_NAV_NEXT = "▶"
ICON_NAV_LAST = "▶|"

ICON_PLAY = "▶️"
ICON_PAUSE = "⏸️"
ICON_STOP = "⏹️"

class SequenceControlsWidget(QWidget):
    add_frame_requested = pyqtSignal(str) # "snapshot" or "blank"
    delete_selected_frame_requested = pyqtSignal()
    duplicate_selected_frame_requested = pyqtSignal()
    
    navigate_first_requested = pyqtSignal()
    navigate_prev_requested = pyqtSignal()
    navigate_next_requested = pyqtSignal()
    navigate_last_requested = pyqtSignal()
    
    play_requested = pyqtSignal()
    pause_requested = pyqtSignal()
    stop_requested = pyqtSignal()
    
    frame_delay_changed = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self_main_layout = QVBoxLayout(self)
        self_main_layout.setContentsMargins(5, 5, 5, 5) # Keep some overall margins
        self_main_layout.setSpacing(8) # Spacing between the two main bars

        # --- Bar 1: Frame Editing & Navigation ---
        bar1_layout = QHBoxLayout()
        bar1_layout.setSpacing(6)

        # Frame Editing Section
        self.add_frame_button = QPushButton(f"{ICON_ADD_FRAME} Add")
        self.add_frame_button.setToolTip("Add new frame (Click for Snapshot, Right-click for Blank)")
        self.add_frame_button.setStatusTip("Add a new frame to the sequence. Default: Snapshot of current grid. Right-click for options.")
        self.add_frame_button.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.add_frame_button.customContextMenuRequested.connect(self._show_add_frame_menu)
        self.add_frame_button.clicked.connect(lambda: self.add_frame_requested.emit("snapshot")) # Default click is snapshot
        bar1_layout.addWidget(self.add_frame_button)

        self.duplicate_frame_button = QPushButton(ICON_DUPLICATE) # Icon only
        self.duplicate_frame_button.setToolTip("Duplicate Selected Frame")
        self.duplicate_frame_button.setStatusTip("Create a copy of the currently selected frame after it.")
        self.duplicate_frame_button.clicked.connect(self.duplicate_selected_frame_requested)
        bar1_layout.addWidget(self.duplicate_frame_button)

        self.delete_frame_button = QPushButton(ICON_DELETE) # Icon only
        self.delete_frame_button.setToolTip("Delete Selected Frame")
        self.delete_frame_button.setStatusTip("Remove the currently selected frame from the sequence.")
        self.delete_frame_button.clicked.connect(self.delete_selected_frame_requested)
        bar1_layout.addWidget(self.delete_frame_button)

        bar1_layout.addSpacerItem(QSpacerItem(20, 10, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)) # Spacer

        # Frame Navigation Section
        self.first_frame_button = QPushButton(ICON_NAV_FIRST)
        self.first_frame_button.setToolTip("Go to First Frame")
        self.first_frame_button.setStatusTip("Jump to the first frame of the animation.")
        self.first_frame_button.clicked.connect(self.navigate_first_requested)
        bar1_layout.addWidget(self.first_frame_button)

        self.prev_frame_button = QPushButton(ICON_NAV_PREV)
        self.prev_frame_button.setToolTip("Go to Previous Frame")
        self.prev_frame_button.setStatusTip("Move to the previous frame.")
        self.prev_frame_button.clicked.connect(self.navigate_prev_requested)
        bar1_layout.addWidget(self.prev_frame_button)

        self.next_frame_button = QPushButton(ICON_NAV_NEXT)
        self.next_frame_button.setToolTip("Go to Next Frame")
        self.next_frame_button.setStatusTip("Move to the next frame.")
        self.next_frame_button.clicked.connect(self.navigate_next_requested)
        bar1_layout.addWidget(self.next_frame_button)

        self.last_frame_button = QPushButton(ICON_NAV_LAST)
        self.last_frame_button.setToolTip("Go to Last Frame")
        self.last_frame_button.setStatusTip("Jump to the last frame of the animation.")
        self.last_frame_button.clicked.connect(self.navigate_last_requested)
        bar1_layout.addWidget(self.last_frame_button)
        
        self_main_layout.addLayout(bar1_layout)

        # --- Bar 2: Playback & Speed ---
        bar2_layout = QHBoxLayout()
        bar2_layout.setSpacing(6)

        # Playback Section
        self.play_pause_button = QPushButton(ICON_PLAY + " Play") # Text for clarity, icon helps
        self.play_pause_button.setCheckable(True)
        self.play_pause_button.setToolTip("Play/Pause Sequence")
        self.play_pause_button.setStatusTip(f"Play or Pause the animation sequence (Shortcut: {QKeySequence(Qt.Key.Key_Space).toString(QKeySequence.SequenceFormat.NativeText)} - *Not yet implemented*)") # Placeholder for shortcut
        self.play_pause_button.toggled.connect(self._on_play_pause_toggled)
        bar2_layout.addWidget(self.play_pause_button)

        self.stop_button = QPushButton(ICON_STOP + " Stop")
        self.stop_button.setToolTip("Stop Sequence and Reset")
        self.stop_button.setStatusTip("Stop the animation and return to the first frame (or selected edit frame).")
        self.stop_button.clicked.connect(self.stop_requested)
        bar2_layout.addWidget(self.stop_button)

        bar2_layout.addSpacerItem(QSpacerItem(20, 10, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))


        # Animation Speed Section
        bar2_layout.addWidget(QLabel("Speed:"))
        self.speed_slider = QSlider(Qt.Orientation.Horizontal)
        self.speed_slider.setRange(MIN_SPEED_VALUE, MAX_SPEED_VALUE)
        initial_slider_val = self._delay_to_slider_value(DEFAULT_FRAME_DELAY_MS)
        self.speed_slider.setValue(initial_slider_val)
        self.speed_slider.setSingleStep(1); self.speed_slider.setPageStep(10)
        self.speed_slider.setTickInterval((MAX_SPEED_VALUE - MIN_SPEED_VALUE) // 10 if MAX_SPEED_VALUE > MIN_SPEED_VALUE else 1)
        self.speed_slider.setTickPosition(QSlider.TickPosition.NoTicks) # Cleaner look
        self.speed_slider.valueChanged.connect(self._on_speed_slider_changed)
        self.speed_slider.setStatusTip("Adjust animation playback speed (frames per second).")
        bar2_layout.addWidget(self.speed_slider, 1) # Give slider some stretch factor

        self.current_speed_display_label = QLabel()
        self.current_speed_display_label.setMinimumWidth(80) # Adjusted width
        self.current_speed_display_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.current_speed_display_label.setStatusTip("Current animation speed in Frames Per Second (FPS) and milliseconds per frame (ms).")
        self._update_speed_display_label(initial_slider_val)
        bar2_layout.addWidget(self.current_speed_display_label)
        
        self_main_layout.addLayout(bar2_layout)
        
        # Hidden spinbox for precise delay value (not directly shown but used by slider logic)
        self.delay_ms_spinbox = QSpinBox() 
        self.delay_ms_spinbox.setRange(MIN_FRAME_DELAY_MS, MAX_FRAME_DELAY_MS * 2) # Allow larger max if needed
        self.delay_ms_spinbox.setValue(DEFAULT_FRAME_DELAY_MS)
        self.delay_ms_spinbox.valueChanged.connect(self._on_delay_spinbox_changed)
        self.delay_ms_spinbox.setVisible(False)


    def _show_add_frame_menu(self, position):
        menu = QMenu(self)
        snapshot_action = QAction(ICON_ADD_SNAPSHOT + " Snapshot Current Grid", self)
        snapshot_action.setStatusTip("Add a new frame by capturing the current colors on the main pad grid.")
        snapshot_action.triggered.connect(lambda: self.add_frame_requested.emit("snapshot"))
        menu.addAction(snapshot_action)

        blank_action = QAction(ICON_ADD_BLANK + " Blank Frame (All Off)", self)
        blank_action.setStatusTip("Add a new frame with all pads set to black (off).")
        blank_action.triggered.connect(lambda: self.add_frame_requested.emit("blank"))
        menu.addAction(blank_action)
        menu.exec(self.add_frame_button.mapToGlobal(position))

    def _on_play_pause_toggled(self, checked):
        if checked:
            self.play_pause_button.setText(ICON_PAUSE + " Pause")
            self.play_pause_button.setToolTip("Pause Sequence")
            # Status tip already set, could update it here if shortcut changed or state info added
            self.play_requested.emit()
        else:
            self.play_pause_button.setText(ICON_PLAY + " Play")
            self.play_pause_button.setToolTip("Play Sequence")
            self.pause_requested.emit()

    def update_playback_button_state(self, is_playing: bool):
        self.play_pause_button.blockSignals(True)
        self.play_pause_button.setChecked(is_playing)
        if is_playing:
            self.play_pause_button.setText(ICON_PAUSE + " Pause")
            self.play_pause_button.setToolTip("Pause Sequence")
        else:
            self.play_pause_button.setText(ICON_PLAY + " Play")
            self.play_pause_button.setToolTip("Play Sequence")
        self.play_pause_button.blockSignals(False)

    def set_controls_enabled_state(self, enabled: bool, frame_selected: bool = False, has_frames: bool = False):
        self.add_frame_button.setEnabled(enabled)
        self.duplicate_frame_button.setEnabled(enabled and frame_selected and has_frames)
        self.delete_frame_button.setEnabled(enabled and frame_selected and has_frames)
        
        self.first_frame_button.setEnabled(enabled and has_frames)
        self.prev_frame_button.setEnabled(enabled and has_frames and frame_selected) # Can only go prev if a frame is selected
        self.next_frame_button.setEnabled(enabled and has_frames and frame_selected) # Can only go next if a frame is selected
        self.last_frame_button.setEnabled(enabled and has_frames)
        
        self.play_pause_button.setEnabled(enabled and has_frames)
        self.stop_button.setEnabled(enabled and has_frames) # Enable stop if playing OR if not on first frame
        
        self.speed_slider.setEnabled(enabled and has_frames)
        self.current_speed_display_label.setEnabled(enabled and has_frames)
        # self.delay_ms_spinbox.setEnabled(enabled and has_frames) # It's hidden

    # --- Speed Slider/Spinbox Logic (Unchanged) ---
    def _slider_value_to_delay(self, slider_value: int) -> int:
        s_val = max(MIN_SPEED_VALUE, min(slider_value, MAX_SPEED_VALUE))
        if MAX_SPEED_VALUE == MIN_SPEED_VALUE: return MIN_FRAME_DELAY_MS
        normalized_speed = (s_val - MIN_SPEED_VALUE) / (MAX_SPEED_VALUE - MIN_SPEED_VALUE)
        delay_range = MAX_FRAME_DELAY_MS - MIN_FRAME_DELAY_MS
        delay = MAX_FRAME_DELAY_MS - (normalized_speed * delay_range)
        return int(max(MIN_FRAME_DELAY_MS, min(round(delay), MAX_FRAME_DELAY_MS)))

    def _delay_to_slider_value(self, delay_ms: int) -> int:
        if MAX_FRAME_DELAY_MS == MIN_FRAME_DELAY_MS: return MIN_SPEED_VALUE
        clamped_delay_ms = max(MIN_FRAME_DELAY_MS, min(delay_ms, MAX_FRAME_DELAY_MS))
        delay_range = MAX_FRAME_DELAY_MS - MIN_FRAME_DELAY_MS
        if delay_range == 0: return MIN_SPEED_VALUE
        normalized_delay_pos_inverted = (MAX_FRAME_DELAY_MS - clamped_delay_ms) / delay_range
        slider_range = MAX_SPEED_VALUE - MIN_SPEED_VALUE
        slider_value = MIN_SPEED_VALUE + (normalized_delay_pos_inverted * slider_range)
        return int(round(slider_value))

    def _update_speed_display_label(self, speed_slider_val_for_calc: int):
        delay_ms = self._slider_value_to_delay(speed_slider_val_for_calc)
        fps = 1000.0 / delay_ms if delay_ms > 0 else 0
        self.current_speed_display_label.setText(f"{fps:.1f} FPS ({delay_ms}ms)")

    def _on_speed_slider_changed(self, slider_logical_value: int):
        delay_ms = self._slider_value_to_delay(slider_logical_value)
        self._update_speed_display_label(slider_logical_value)
        self.delay_ms_spinbox.blockSignals(True)
        self.delay_ms_spinbox.setValue(delay_ms)
        self.delay_ms_spinbox.blockSignals(False)
        self.frame_delay_changed.emit(delay_ms)

    def _on_delay_spinbox_changed(self, delay_ms_from_spinbox: int):
        slider_val_to_set = self._delay_to_slider_value(delay_ms_from_spinbox)
        self.speed_slider.blockSignals(True)
        self.speed_slider.setValue(slider_val_to_set)
        self.speed_slider.blockSignals(False)
        self._update_speed_display_label(slider_val_to_set) 
        self.frame_delay_changed.emit(delay_ms_from_spinbox)

    def set_frame_delay_ui(self, delay_ms: int):
        slider_val = self._delay_to_slider_value(delay_ms)
        self.speed_slider.blockSignals(True); self.delay_ms_spinbox.blockSignals(True)
        self.speed_slider.setValue(slider_val)
        self.delay_ms_spinbox.setValue(delay_ms)
        self._update_speed_display_label(slider_val)
        self.speed_slider.blockSignals(False); self.delay_ms_spinbox.blockSignals(False)
