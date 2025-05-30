# AKAI_Fire_RGB_Controller/animator/controls_widget.py
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
                             QSlider, QSpinBox, QFrame, QMenu, QSpacerItem, QSizePolicy)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QAction, QKeySequence

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
ICON_ADD_FRAME = "✚"
ICON_ADD_SNAPSHOT = "📷"
ICON_ADD_BLANK = "⬛"
ICON_DUPLICATE = "⿻"  
ICON_DELETE = "🗑"
ICON_COPY = "🗐"
ICON_CUT = "✂"
ICON_PASTE = "⤵" 
ICON_NAV_FIRST = "|◀"
ICON_NAV_PREV = "◀"
ICON_NAV_NEXT = "▶"
ICON_NAV_LAST = "▶|"
ICON_PLAY = "🎬"
ICON_PAUSE = "❚❚"
ICON_STOP = "🛑"


class SequenceControlsWidget(QWidget):
    add_frame_requested = pyqtSignal(str)
    delete_selected_frame_requested = pyqtSignal()
    duplicate_selected_frame_requested = pyqtSignal()
    copy_frames_requested = pyqtSignal()
    cut_frames_requested = pyqtSignal()
    paste_frames_requested = pyqtSignal()
    # REMOVED: undo_requested and redo_requested signals

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
        self_main_layout.setContentsMargins(5, 5, 5, 5)
        self_main_layout.setSpacing(8)

        bar1_layout = QHBoxLayout()
        bar1_layout.setSpacing(6)

        self.add_frame_button = QPushButton(f"{ICON_ADD_BLANK} Add Blank")
        self.add_frame_button.setToolTip("Add New Blank Frame (Ctrl+Shift+B)")
        self.add_frame_button.setStatusTip(
            "Adds a new blank frame to the sequence.")
        self.add_frame_button.clicked.connect(
            lambda: self.add_frame_requested.emit("blank"))
        bar1_layout.addWidget(self.add_frame_button)

        self.duplicate_frame_button = QPushButton(ICON_DUPLICATE)
        self.duplicate_frame_button.setToolTip(
            "Duplicate Selected Frame(s) (Ctrl+D)")
        self.duplicate_frame_button.setStatusTip(
            f"Create copies of the currently selected frame(s) after them (Shortcut: Ctrl+D).")
        self.duplicate_frame_button.clicked.connect(
            self.duplicate_selected_frame_requested)
        bar1_layout.addWidget(self.duplicate_frame_button)

        self.delete_frame_button = QPushButton(ICON_DELETE)
        self.delete_frame_button.setToolTip(
            "Delete Selected Frame(s) (Delete)")
        self.delete_frame_button.setStatusTip(
            f"Remove the currently selected frame(s) from the sequence (Shortcut: Delete).")
        self.delete_frame_button.clicked.connect(
            self.delete_selected_frame_requested)
        bar1_layout.addWidget(self.delete_frame_button)

        self.copy_frames_button = QPushButton(ICON_COPY)
        self.copy_frames_button.setToolTip(f"Copy Selected Frame(s) (Ctrl+C)")
        self.copy_frames_button.setStatusTip(
            f"Copy the selected frame(s) to the internal clipboard (Shortcut: Ctrl+C).")
        self.copy_frames_button.clicked.connect(self.copy_frames_requested)
        bar1_layout.addWidget(self.copy_frames_button)

        self.cut_frames_button = QPushButton(ICON_CUT)
        self.cut_frames_button.setToolTip(f"Cut Selected Frame(s) (Ctrl+X)")
        self.cut_frames_button.setStatusTip(
            f"Cut the selected frame(s) to the internal clipboard (Shortcut: Ctrl+X).")
        self.cut_frames_button.clicked.connect(self.cut_frames_requested)
        bar1_layout.addWidget(self.cut_frames_button)

        self.paste_frames_button = QPushButton(ICON_PASTE)
        self.paste_frames_button.setToolTip(
            f"Paste Frame(s) from Clipboard (Ctrl+V)")
        self.paste_frames_button.setStatusTip(
            f"Paste frame(s) from the internal clipboard after the current selection (Shortcut: Ctrl+V).")
        self.paste_frames_button.clicked.connect(self.paste_frames_requested)
        bar1_layout.addWidget(self.paste_frames_button)

        # REMOVED: self.undo_button and self.redo_button creation and addWidget calls

        bar1_layout.addSpacerItem(QSpacerItem(
            20, 10, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))

        self.first_frame_button = QPushButton(ICON_NAV_FIRST)
        self.first_frame_button.setToolTip("Go to First Frame")
        self.first_frame_button.setStatusTip(
            "Jump to the first frame of the animation.")
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
        self.last_frame_button.setStatusTip(
            "Jump to the last frame of the animation.")
        self.last_frame_button.clicked.connect(self.navigate_last_requested)
        bar1_layout.addWidget(self.last_frame_button)

        self_main_layout.addLayout(bar1_layout)

        bar2_layout = QHBoxLayout()
        bar2_layout.setSpacing(6)

        self.play_pause_button = QPushButton(ICON_PLAY + " Play")
        self.play_pause_button.setCheckable(True)
        self.play_pause_button.setToolTip("Play/Pause Sequence (Spacebar)")
        self.play_pause_button.setStatusTip(
            f"Play or Pause the animation sequence (Shortcut: Spacebar).")
        self.play_pause_button.toggled.connect(self._on_play_pause_toggled)
        bar2_layout.addWidget(self.play_pause_button)

        self.stop_button = QPushButton(ICON_STOP + " Stop")
        self.stop_button.setToolTip("Stop Sequence and Reset")
        self.stop_button.setStatusTip(
            "Stop the animation and return to the first frame (or selected edit frame).")
        self.stop_button.clicked.connect(self.stop_requested)
        bar2_layout.addWidget(self.stop_button)

        bar2_layout.addSpacerItem(QSpacerItem(
            20, 10, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))

        bar2_layout.addWidget(QLabel("Speed:"))
        self.speed_slider = QSlider(Qt.Orientation.Horizontal)
        self.speed_slider.setRange(MIN_SPEED_VALUE, MAX_SPEED_VALUE)
        initial_slider_val = self._delay_to_slider_value(
            DEFAULT_FRAME_DELAY_MS)
        self.speed_slider.setValue(initial_slider_val)
        self.speed_slider.setSingleStep(1)
        self.speed_slider.setPageStep(10)
        self.speed_slider.setTickInterval(
            (MAX_SPEED_VALUE - MIN_SPEED_VALUE) // 10 if MAX_SPEED_VALUE > MIN_SPEED_VALUE else 1)
        self.speed_slider.setTickPosition(QSlider.TickPosition.NoTicks)
        self.speed_slider.valueChanged.connect(self._on_speed_slider_changed)
        self.speed_slider.setStatusTip(
            "Adjust animation playback speed (frames per second).")
        bar2_layout.addWidget(self.speed_slider, 1)

        self.current_speed_display_label = QLabel()
        self.current_speed_display_label.setMinimumWidth(80)
        self.current_speed_display_label.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.current_speed_display_label.setStatusTip(
            "Current animation speed in Frames Per Second (FPS) and milliseconds per frame (ms).")
        self._update_speed_display_label(initial_slider_val)
        bar2_layout.addWidget(self.current_speed_display_label)

        self_main_layout.addLayout(bar2_layout)

        self.delay_ms_spinbox = QSpinBox()
        self.delay_ms_spinbox.setRange(
            MIN_FRAME_DELAY_MS, MAX_FRAME_DELAY_MS * 2)
        self.delay_ms_spinbox.setValue(DEFAULT_FRAME_DELAY_MS)
        self.delay_ms_spinbox.valueChanged.connect(
            self._on_delay_spinbox_changed)
        self.delay_ms_spinbox.setVisible(False)

    def _on_play_pause_toggled(self, checked):
        if checked:
            self.play_pause_button.setText(ICON_PAUSE + " Pause")
            self.play_pause_button.setToolTip("Pause Sequence (Spacebar)")
            self.play_requested.emit()
        else:
            self.play_pause_button.setText(ICON_PLAY + " Play")
            self.play_pause_button.setToolTip("Play Sequence (Spacebar)")
            self.pause_requested.emit()

    def update_playback_button_state(self, is_playing: bool):
        self.play_pause_button.blockSignals(True)
        self.play_pause_button.setChecked(is_playing)
        if is_playing:
            self.play_pause_button.setText(ICON_PAUSE + " Pause")
            self.play_pause_button.setToolTip("Pause Sequence (Spacebar)")
        else:
            self.play_pause_button.setText(ICON_PLAY + " Play")
            self.play_pause_button.setToolTip("Play Sequence (Spacebar)")
        self.play_pause_button.blockSignals(False)

    def set_controls_enabled_state(self, enabled: bool,
                                   frame_selected: bool = False,
                                   has_frames: bool = False,
                                   clipboard_has_content: bool = False,
                                   can_undo: bool = False,  # Parameter still received
                                   can_redo: bool = False):  # Parameter still received
        self.add_frame_button.setEnabled(enabled)

        can_operate_on_selection = enabled and frame_selected and has_frames

        self.duplicate_frame_button.setEnabled(can_operate_on_selection)
        self.delete_frame_button.setEnabled(can_operate_on_selection)
        self.copy_frames_button.setEnabled(can_operate_on_selection)
        self.cut_frames_button.setEnabled(can_operate_on_selection)

        self.paste_frames_button.setEnabled(enabled and clipboard_has_content)

        # REMOVED: self.undo_button.setEnabled(...)
        # REMOVED: self.redo_button.setEnabled(...)

        self.first_frame_button.setEnabled(enabled and has_frames)
        self.prev_frame_button.setEnabled(enabled and has_frames)
        self.next_frame_button.setEnabled(enabled and has_frames)
        self.last_frame_button.setEnabled(enabled and has_frames)

        self.play_pause_button.setEnabled(enabled and has_frames)
        self.stop_button.setEnabled(enabled and has_frames)

        self.speed_slider.setEnabled(enabled and has_frames)
        self.current_speed_display_label.setEnabled(enabled and has_frames)

    def _slider_value_to_delay(self, slider_value: int) -> int:
        s_val = max(MIN_SPEED_VALUE, min(slider_value, MAX_SPEED_VALUE))
        if MAX_SPEED_VALUE == MIN_SPEED_VALUE:
            return MIN_FRAME_DELAY_MS
        normalized_speed = (s_val - MIN_SPEED_VALUE) / \
            (MAX_SPEED_VALUE - MIN_SPEED_VALUE)
        delay_range = MAX_FRAME_DELAY_MS - MIN_FRAME_DELAY_MS
        delay = MAX_FRAME_DELAY_MS - (normalized_speed * delay_range)
        return int(max(MIN_FRAME_DELAY_MS, min(round(delay), MAX_FRAME_DELAY_MS)))

    def _delay_to_slider_value(self, delay_ms: int) -> int:
        if MAX_FRAME_DELAY_MS == MIN_FRAME_DELAY_MS:
            return MIN_SPEED_VALUE
        clamped_delay_ms = max(MIN_FRAME_DELAY_MS, min(
            delay_ms, MAX_FRAME_DELAY_MS))
        delay_range = MAX_FRAME_DELAY_MS - MIN_FRAME_DELAY_MS
        if delay_range == 0:
            return MIN_SPEED_VALUE
        normalized_delay_pos_inverted = (
            MAX_FRAME_DELAY_MS - clamped_delay_ms) / delay_range
        slider_range = MAX_SPEED_VALUE - MIN_SPEED_VALUE
        slider_value = MIN_SPEED_VALUE + \
            (normalized_delay_pos_inverted * slider_range)
        return int(round(slider_value))

    def _update_speed_display_label(self, speed_slider_val_for_calc: int):
        delay_ms = self._slider_value_to_delay(speed_slider_val_for_calc)
        fps = 1000.0 / delay_ms if delay_ms > 0 else 0
        self.current_speed_display_label.setText(
            f"{fps:.1f} FPS ({delay_ms}ms)")

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
        self.speed_slider.blockSignals(True)
        self.delay_ms_spinbox.blockSignals(True)
        self.speed_slider.setValue(slider_val)
        self.delay_ms_spinbox.setValue(delay_ms)
        self._update_speed_display_label(slider_val)
        self.speed_slider.blockSignals(False)
        self.delay_ms_spinbox.blockSignals(False)

    def get_current_delay_ms(self) -> int:
        if self.delay_ms_spinbox:
            return self.delay_ms_spinbox.value()
        if self.speed_slider:
            return self._slider_value_to_delay(self.speed_slider.value())
        return DEFAULT_FRAME_DELAY_MS