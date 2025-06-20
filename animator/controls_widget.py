# AKAI_Fire_RGB_Controller/animator/controls_widget.py
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
                             QSlider, QSpinBox, QFrame, QMenu, QSpacerItem, QSizePolicy)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QAction, QKeySequence

FPS_MIN_DISCRETE_VALUES = [0.5, 1.0, 2.0,
                           3.0, 4.0, 5.0]  # Desired low FPS steps
FPS_LINEAR_START_VALUE = 6.0  # FPS from which linear steps begin
FPS_MAX_TARGET_VALUE = 90.0  # New maximum FPS
DEFAULT_START_FPS_VALUE = 20.0
_NUM_DISCRETE_FPS_STEPS = len(FPS_MIN_DISCRETE_VALUES)
_SLIDER_IDX_FOR_LINEAR_START = _NUM_DISCRETE_FPS_STEPS
SLIDER_MIN_RAW_VALUE = 0
SLIDER_MAX_RAW_VALUE = _SLIDER_IDX_FOR_LINEAR_START + \
    int(FPS_MAX_TARGET_VALUE - FPS_LINEAR_START_VALUE)
MIN_FRAME_DELAY_MS_LIMIT = int(
    1000.0 / FPS_MAX_TARGET_VALUE) if FPS_MAX_TARGET_VALUE > 0 else 10
MAX_FRAME_DELAY_MS_LIMIT = int(
    1000.0 / FPS_MIN_DISCRETE_VALUES[0]) if FPS_MIN_DISCRETE_VALUES else 2000
DEFAULT_FRAME_DELAY_MS_FALLBACK = int(1000.0 / DEFAULT_START_FPS_VALUE)

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
ICON_PLAY = "⏯"
ICON_PAUSE = "⏯"
ICON_STOP = "🛑"

class SequenceControlsWidget(QWidget):
    # --- Signals ---
    add_frame_requested = pyqtSignal(str)
    delete_selected_frame_requested = pyqtSignal()
    duplicate_selected_frame_requested = pyqtSignal()
    copy_frames_requested = pyqtSignal()
    cut_frames_requested = pyqtSignal()
    paste_frames_requested = pyqtSignal()
    navigate_first_requested = pyqtSignal()
    navigate_prev_requested = pyqtSignal()
    navigate_next_requested = pyqtSignal()
    navigate_last_requested = pyqtSignal()
    play_stop_clicked = pyqtSignal()  # NEW Simplified Signal
    frame_delay_changed = pyqtSignal(int)  # Emits delay in MS

    # --- Helper Methods (Unchanged) ---
    def _slider_raw_value_to_fps(self, slider_raw_value: int) -> float:
        clamped_slider_val = max(SLIDER_MIN_RAW_VALUE, min(
            slider_raw_value, SLIDER_MAX_RAW_VALUE))
        if clamped_slider_val < _NUM_DISCRETE_FPS_STEPS:
            return FPS_MIN_DISCRETE_VALUES[clamped_slider_val]
        else:
            linear_offset_from_discrete_end = clamped_slider_val - _NUM_DISCRETE_FPS_STEPS
            return FPS_LINEAR_START_VALUE + linear_offset_from_discrete_end

    def _fps_to_slider_raw_value(self, fps_value: float) -> int:
        clamped_fps = max(FPS_MIN_DISCRETE_VALUES[0], min(
            fps_value, FPS_MAX_TARGET_VALUE))
        for i, discrete_fps in enumerate(FPS_MIN_DISCRETE_VALUES):
            if abs(clamped_fps - discrete_fps) < 0.01:
                return i
        if clamped_fps >= FPS_LINEAR_START_VALUE:
            slider_val = _SLIDER_IDX_FOR_LINEAR_START + \
                int(round(clamped_fps - FPS_LINEAR_START_VALUE))
            return max(_SLIDER_IDX_FOR_LINEAR_START, min(slider_val, SLIDER_MAX_RAW_VALUE))
        closest_discrete_idx = 0
        min_diff = float('inf')
        for i, discrete_fps in enumerate(FPS_MIN_DISCRETE_VALUES):
            diff = abs(clamped_fps - discrete_fps)
            if diff < min_diff:
                min_diff = diff
                closest_discrete_idx = i
        return closest_discrete_idx

    def _fps_to_delay_ms(self, fps: float) -> int:
        if fps <= 0:
            return MAX_FRAME_DELAY_MS_LIMIT
        delay_ms = 1000.0 / fps
        return int(max(MIN_FRAME_DELAY_MS_LIMIT, min(round(delay_ms), MAX_FRAME_DELAY_MS_LIMIT)))

    def _delay_ms_to_fps(self, delay_ms: int) -> float:
        clamped_delay = max(MIN_FRAME_DELAY_MS_LIMIT, min(
            delay_ms, MAX_FRAME_DELAY_MS_LIMIT))
        if clamped_delay <= 0:
            return FPS_MIN_DISCRETE_VALUES[0]
        return 1000.0 / clamped_delay

    def _update_speed_display_label(self, current_fps: float, current_delay_ms: int):
        if self.current_speed_display_label:
            self.current_speed_display_label.setText(
                f"{current_fps:.1f} FPS ({current_delay_ms}ms)")

    # --- UI Initialization ---
    def __init__(self, parent=None):
        super().__init__(parent)
        self_main_layout = QVBoxLayout(self)
        self_main_layout.setContentsMargins(5, 5, 5, 5)
        self_main_layout.setSpacing(8)
        bar1_layout = QHBoxLayout()
        bar1_layout.setSpacing(6)
        self.add_frame_button = QPushButton(f"{ICON_ADD_BLANK} Add Blank")
        self.add_frame_button.setToolTip("Add New Blank Frame (Ctrl+Shift+B)")
        self.add_frame_button.clicked.connect(
            lambda: self.add_frame_requested.emit("blank"))
        bar1_layout.addWidget(self.add_frame_button)
        self.duplicate_frame_button = QPushButton(ICON_DUPLICATE)
        self.duplicate_frame_button.setToolTip(
            "Duplicate Selected Frame(s) (Ctrl+D)")
        self.duplicate_frame_button.clicked.connect(
            self.duplicate_selected_frame_requested)
        bar1_layout.addWidget(self.duplicate_frame_button)
        self.delete_frame_button = QPushButton(ICON_DELETE)
        self.delete_frame_button.setToolTip(
            "Delete Selected Frame(s) (Delete)")
        self.delete_frame_button.clicked.connect(
            self.delete_selected_frame_requested)
        bar1_layout.addWidget(self.delete_frame_button)
        self.copy_frames_button = QPushButton(ICON_COPY)
        self.copy_frames_button.setToolTip(f"Copy Selected Frame(s) (Ctrl+C)")
        self.copy_frames_button.clicked.connect(self.copy_frames_requested)
        bar1_layout.addWidget(self.copy_frames_button)
        self.cut_frames_button = QPushButton(ICON_CUT)
        self.cut_frames_button.setToolTip(f"Cut Selected Frame(s) (Ctrl+X)")
        self.cut_frames_button.clicked.connect(self.cut_frames_requested)
        bar1_layout.addWidget(self.cut_frames_button)
        self.paste_frames_button = QPushButton(ICON_PASTE)
        self.paste_frames_button.setToolTip(
            f"Paste Frame(s) from Clipboard (Ctrl+V)")
        self.paste_frames_button.clicked.connect(self.paste_frames_requested)
        bar1_layout.addWidget(self.paste_frames_button)
        bar1_layout.addSpacerItem(QSpacerItem(
            20, 10, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))
        self.first_frame_button = QPushButton(ICON_NAV_FIRST)
        self.first_frame_button.clicked.connect(self.navigate_first_requested)
        bar1_layout.addWidget(self.first_frame_button)
        self.prev_frame_button = QPushButton(ICON_NAV_PREV)
        self.prev_frame_button.clicked.connect(self.navigate_prev_requested)
        bar1_layout.addWidget(self.prev_frame_button)
        self.next_frame_button = QPushButton(ICON_NAV_NEXT)
        self.next_frame_button.clicked.connect(self.navigate_next_requested)
        bar1_layout.addWidget(self.next_frame_button)
        self.last_frame_button = QPushButton(ICON_NAV_LAST)
        self.last_frame_button.clicked.connect(self.navigate_last_requested)
        bar1_layout.addWidget(self.last_frame_button)
        self_main_layout.addLayout(bar1_layout)
        bar2_layout = QHBoxLayout()
        bar2_layout.setSpacing(6)
        self.play_stop_button = QPushButton("▶️ Animation")
        # <<< CHANGED: No longer checkable
        self.play_stop_button.setCheckable(False)
        self.play_stop_button.setToolTip("Play/Stop Sequence (Spacebar)")
        self.play_stop_button.clicked.connect(
            self.play_stop_clicked.emit)  # <<< CHANGED: Emits simple signal
        self.play_stop_button.setObjectName("AnimatorPlayButton")
        bar2_layout.addWidget(self.play_stop_button)
        bar2_layout.addSpacerItem(QSpacerItem(
            20, 10, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))
        bar2_layout.addWidget(QLabel("Speed:"))
        self.speed_slider = QSlider(Qt.Orientation.Horizontal)
        self.speed_slider.setRange(SLIDER_MIN_RAW_VALUE, SLIDER_MAX_RAW_VALUE)
        self.speed_slider.valueChanged.connect(self._on_speed_slider_changed)
        bar2_layout.addWidget(self.speed_slider, 1)
        self.current_speed_display_label = QLabel()
        self.current_speed_display_label.setMinimumWidth(85)
        self.current_speed_display_label.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        bar2_layout.addWidget(self.current_speed_display_label)
        self_main_layout.addLayout(bar2_layout)
        self.delay_ms_spinbox = QSpinBox()
        self.delay_ms_spinbox.setVisible(False)
        initial_slider_raw_val = self._fps_to_slider_raw_value(
            DEFAULT_START_FPS_VALUE)
        self.speed_slider.setValue(initial_slider_raw_val)
        initial_delay_ms = self._fps_to_delay_ms(DEFAULT_START_FPS_VALUE)
        self.delay_ms_spinbox.setValue(initial_delay_ms)
        self._update_speed_display_label(
            DEFAULT_START_FPS_VALUE, initial_delay_ms)

    # --- Public Methods for Manager ---
    def update_playback_button_state(self, is_playing: bool):
        if is_playing:
            self.play_stop_button.setText("🛑 Animation")
        else:
            self.play_stop_button.setText("▶️ Animation")
        self.play_stop_button.setProperty("active", is_playing)
        self.style().unpolish(self.play_stop_button)
        self.style().polish(self.play_stop_button)

    def set_controls_enabled_state(self, enabled: bool,
                                    frame_selected: bool = False,
                                    has_frames: bool = False,
                                    clipboard_has_content: bool = False):
        self.add_frame_button.setEnabled(enabled)
        can_operate_on_selection = enabled and frame_selected and has_frames
        self.duplicate_frame_button.setEnabled(can_operate_on_selection)
        self.delete_frame_button.setEnabled(can_operate_on_selection)
        self.copy_frames_button.setEnabled(can_operate_on_selection)
        self.cut_frames_button.setEnabled(can_operate_on_selection)
        self.paste_frames_button.setEnabled(enabled and clipboard_has_content)
        self.first_frame_button.setEnabled(enabled and has_frames)
        self.prev_frame_button.setEnabled(enabled and has_frames)
        self.next_frame_button.setEnabled(enabled and has_frames)
        self.last_frame_button.setEnabled(enabled and has_frames)
        self.play_stop_button.setEnabled(enabled and has_frames)
        self.speed_slider.setEnabled(enabled and has_frames)
        self.current_speed_display_label.setEnabled(enabled and has_frames)

    def _on_speed_slider_changed(self, slider_raw_value: int):
        current_fps = self._slider_raw_value_to_fps(slider_raw_value)
        current_delay_ms = self._fps_to_delay_ms(current_fps)
        self._update_speed_display_label(current_fps, current_delay_ms)
        self.delay_ms_spinbox.blockSignals(True)
        self.delay_ms_spinbox.setValue(current_delay_ms)
        self.delay_ms_spinbox.blockSignals(False)
        self.frame_delay_changed.emit(current_delay_ms)

    def set_frame_delay_ui(self, delay_ms: int):
        target_fps = self._delay_ms_to_fps(delay_ms)
        slider_raw_val = self._fps_to_slider_raw_value(target_fps)
        self.speed_slider.blockSignals(True)
        self.delay_ms_spinbox.blockSignals(True)
        self.speed_slider.setValue(slider_raw_val)
        self.delay_ms_spinbox.setValue(delay_ms)
        self._update_speed_display_label(target_fps, delay_ms)
        self.speed_slider.blockSignals(False)
        self.delay_ms_spinbox.blockSignals(False)

    def get_current_delay_ms(self) -> int:
        if self.speed_slider:
            current_fps = self._slider_raw_value_to_fps(
                self.speed_slider.value())
            return self._fps_to_delay_ms(current_fps)
        return DEFAULT_FRAME_DELAY_MS_FALLBACK
