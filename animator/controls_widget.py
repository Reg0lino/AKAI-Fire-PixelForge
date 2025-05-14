# AKAI_Fire_RGB_Controller/animator/controls_widget.py
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, 
                             QSlider, QSpinBox, QFrame, QGroupBox, QMenu)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QAction # For context menu for +Add Frame
from .model import DEFAULT_FRAME_DELAY_MS

# Unicode/Emoji constants for buttons
ICON_ADD_SNAPSHOT = "📷" # Camera
ICON_ADD_BLANK = "⬛"    # Black Square
ICON_DUPLICATE = "📋"   # Clipboard
ICON_DELETE = "🗑️"     # Trash Can
ICON_PLAY = "▶️"
ICON_PAUSE = "⏸️"
ICON_STOP = "⏹️"
ICON_FIRST = "|◀" # Using text as unicode arrows can be small
ICON_PREV = "◀"
ICON_NEXT = "▶"
ICON_LAST = "▶|"


class SequenceControlsWidget(QWidget):
    # Frame manipulation signals
    add_frame_requested = pyqtSignal(str) # "snapshot", "blank"
    delete_selected_frame_requested = pyqtSignal()
    duplicate_selected_frame_requested = pyqtSignal()
    
    # Navigation signals
    navigate_first_requested = pyqtSignal()
    navigate_prev_requested = pyqtSignal()
    navigate_next_requested = pyqtSignal()
    navigate_last_requested = pyqtSignal()

    # Playback signals
    play_requested = pyqtSignal()
    pause_requested = pyqtSignal()
    stop_requested = pyqtSignal()
    frame_delay_changed = pyqtSignal(int) # emits new delay in ms

    def __init__(self, parent=None):
        super().__init__(parent)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(5,5,5,5)

        # --- Frame Editing Controls ---
        editing_group = QGroupBox("Frame Editing")
        editing_layout = QHBoxLayout(editing_group)

        self.add_frame_button = QPushButton("+ Add Frame") # Context menu for options
        self.add_frame_button.setToolTip("Add a new frame (Snapshot, Blank, or Duplicate)")
        self.add_frame_button.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.add_frame_button.customContextMenuRequested.connect(self.show_add_frame_menu)
        # We can also make left-click default to "Add Snapshot"
        self.add_frame_button.clicked.connect(lambda: self.add_frame_requested.emit("snapshot"))


        self.delete_frame_button = QPushButton(ICON_DELETE + " Delete")
        self.delete_frame_button.setToolTip("Delete Selected Frame")
        self.delete_frame_button.clicked.connect(self.delete_selected_frame_requested)

        self.duplicate_frame_button = QPushButton(ICON_DUPLICATE + " Duplicate")
        self.duplicate_frame_button.setToolTip("Duplicate Selected Frame")
        self.duplicate_frame_button.clicked.connect(self.duplicate_selected_frame_requested)

        editing_layout.addWidget(self.add_frame_button)
        editing_layout.addWidget(self.duplicate_frame_button)
        editing_layout.addWidget(self.delete_frame_button)
        editing_layout.addStretch()
        main_layout.addWidget(editing_group)

        # --- Navigation Controls ---
        nav_group = QGroupBox("Frame Navigation")
        nav_layout = QHBoxLayout(nav_group)
        self.first_frame_button = QPushButton(ICON_FIRST)
        self.first_frame_button.setToolTip("Go to First Frame")
        self.first_frame_button.clicked.connect(self.navigate_first_requested)
        self.prev_frame_button = QPushButton(ICON_PREV)
        self.prev_frame_button.setToolTip("Go to Previous Frame")
        self.prev_frame_button.clicked.connect(self.navigate_prev_requested)
        self.next_frame_button = QPushButton(ICON_NEXT)
        self.next_frame_button.setToolTip("Go to Next Frame")
        self.next_frame_button.clicked.connect(self.navigate_next_requested)
        self.last_frame_button = QPushButton(ICON_LAST)
        self.last_frame_button.setToolTip("Go to Last Frame")
        self.last_frame_button.clicked.connect(self.navigate_last_requested)
        
        nav_layout.addWidget(self.first_frame_button)
        nav_layout.addWidget(self.prev_frame_button)
        nav_layout.addWidget(self.next_frame_button)
        nav_layout.addWidget(self.last_frame_button)
        nav_layout.addStretch()
        main_layout.addWidget(nav_group)

        # --- Playback Controls ---
        playback_group = QGroupBox("Playback")
        playback_layout = QVBoxLayout(playback_group)
        
        play_stop_layout = QHBoxLayout()
        self.play_pause_button = QPushButton(ICON_PLAY + " Play")
        self.play_pause_button.setToolTip("Play/Pause Sequence")
        self.play_pause_button.setCheckable(True) # To toggle between Play/Pause state
        self.play_pause_button.toggled.connect(self.on_play_pause_toggled)
        
        self.stop_button = QPushButton(ICON_STOP + " Stop")
        self.stop_button.setToolTip("Stop Sequence and Reset")
        self.stop_button.clicked.connect(self.stop_requested)

        play_stop_layout.addWidget(self.play_pause_button,1)
        play_stop_layout.addWidget(self.stop_button,1)
        playback_layout.addLayout(play_stop_layout)

        # Speed Control (Frame Delay)
        speed_layout = QHBoxLayout()
        speed_layout.addWidget(QLabel("Speed (Delay ms):"))
        
        self.delay_spinbox = QSpinBox()
        self.delay_spinbox.setRange(20, 5000) # Min 20ms (50 FPS) to 5s
        self.delay_spinbox.setValue(DEFAULT_FRAME_DELAY_MS) # Use constant from model or define here
        self.delay_spinbox.setSingleStep(10)
        self.delay_spinbox.setSuffix(" ms")
        self.delay_spinbox.valueChanged.connect(self.frame_delay_changed)
        
        # Optional: A slider for speed too, synced with spinbox
        # self.speed_slider = QSlider(Qt.Orientation.Horizontal)
        # self.speed_slider.setRange(20, 1000) # map to ms
        # self.speed_slider.setValue(DEFAULT_FRAME_DELAY_MS)
        # self.speed_slider.invertedControls = True # Higher value = slower (more delay)
        # self.speed_slider.valueChanged.connect(self.delay_spinbox.setValue)
        # self.delay_spinbox.valueChanged.connect(self.speed_slider.setValue)

        speed_layout.addWidget(self.delay_spinbox,1)
        # speed_layout.addWidget(self.speed_slider,2)
        playback_layout.addLayout(speed_layout)
        main_layout.addWidget(playback_group)

        main_layout.addStretch(1) # Push all groups up

    def show_add_frame_menu(self, position):
        menu = QMenu()
        snapshot_action = QAction(ICON_ADD_SNAPSHOT + " Snapshot Current Grid", self)
        snapshot_action.triggered.connect(lambda: self.add_frame_requested.emit("snapshot"))
        menu.addAction(snapshot_action)

        blank_action = QAction(ICON_ADD_BLANK + " Blank Frame", self)
        blank_action.triggered.connect(lambda: self.add_frame_requested.emit("blank"))
        menu.addAction(blank_action)

        # Duplicate option could also be here, or as a separate button
        # if self.can_duplicate_frame_be_enabled_logic(): # Check if a frame is selected
        #     duplicate_action_in_menu = QAction(ICON_DUPLICATE + " Duplicate Selected Frame", self)
        #     duplicate_action_in_menu.triggered.connect(self.duplicate_selected_frame_requested)
        #     menu.addAction(duplicate_action_in_menu)

        self.add_frame_button.menu = menu # Keep a reference to prevent garbage collection if needed immediately
        menu.exec(self.add_frame_button.mapToGlobal(position))


    def on_play_pause_toggled(self, checked):
        if checked: # Button is now in "checked" state, meaning "Pause" is shown, so we were playing
            self.play_pause_button.setText(ICON_PAUSE + " Pause")
            self.play_pause_button.setToolTip("Pause Sequence")
            self.play_requested.emit()
        else: # Button is "unchecked", meaning "Play" is shown, so we were paused or stopped
            self.play_pause_button.setText(ICON_PLAY + " Play")
            self.play_pause_button.setToolTip("Play Sequence")
            self.pause_requested.emit()

    def update_playback_button_state(self, is_playing: bool):
        """Called by MainWindow to sync button if playback starts/stops elsewhere."""
        self.play_pause_button.setChecked(is_playing) # This will trigger on_play_pause_toggled
        if is_playing:
            self.play_pause_button.setText(ICON_PAUSE + " Pause")
        else:
            self.play_pause_button.setText(ICON_PLAY + " Play")


    def set_controls_enabled_state(self, enabled: bool, frame_selected: bool = False, has_frames:bool = False):
        """Enable/disable controls based on overall state."""
        # Add Frame button is always enabled if overall controls are enabled
        self.add_frame_button.setEnabled(enabled)

        # These depend on having frames and/or a frame being selected
        self.delete_frame_button.setEnabled(enabled and frame_selected and has_frames)
        self.duplicate_frame_button.setEnabled(enabled and frame_selected and has_frames)
        
        self.first_frame_button.setEnabled(enabled and has_frames)
        self.prev_frame_button.setEnabled(enabled and frame_selected and has_frames) # or just has_frames and not first
        self.next_frame_button.setEnabled(enabled and frame_selected and has_frames) # or just has_frames and not last
        self.last_frame_button.setEnabled(enabled and has_frames)

        self.play_pause_button.setEnabled(enabled and has_frames)
        self.stop_button.setEnabled(enabled and has_frames) # Can stop if playing or paused
        self.delay_spinbox.setEnabled(enabled and has_frames)


    def set_frame_delay_ui(self, delay_ms: int):
        """Updates the delay spinbox without emitting its own signal."""
        self.delay_spinbox.blockSignals(True)
        self.delay_spinbox.setValue(delay_ms)
        self.delay_spinbox.blockSignals(False)