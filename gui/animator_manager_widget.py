# AKAI_Fire_RGB_Controller/gui/animator_manager_widget.py
import os
import re
import json 
import glob 
import time 
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QApplication,
    QGroupBox, QComboBox, QSpacerItem, QMessageBox, QInputDialog, QSizePolicy, QFrame
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QColor
from PIL import Image, ImageDraw

# --- Animator-specific project imports ---
try:
    from animator.timeline_widget import SequenceTimelineWidget
    from animator.controls_widget import SequenceControlsWidget
    from animator.model import SequenceModel, AnimationFrame # AnimationFrame is used in frame_clipboard
except ImportError as e:
    print(f"FATAL ERROR in AnimatorManagerWidget: Could not import critical animator components: {e}")
    print("This usually means there's an issue with the project structure, sys.path, or missing __init__.py files.")
    print("Ensure 'AKAI_Fire_RGB_Controller' is the root and contains 'animator' and 'gui' packages.")
    class SequenceTimelineWidget(QWidget): pass
    class SequenceControlsWidget(QWidget): pass
    class SequenceModel(object): pass
    class AnimationFrame(object): pass
FPS_MIN_DISCRETE_VALUES_AMW = [0.5, 1.0, 2.0, 3.0, 4.0, 5.0]
FPS_MAX_TARGET_VALUE_AMW = 90.0
MIN_FRAME_DELAY_MS_LIMIT_AMW = int(1000.0 / FPS_MAX_TARGET_VALUE_AMW) if FPS_MAX_TARGET_VALUE_AMW > 0 else 10 # e.g., 11ms
MAX_FRAME_DELAY_MS_LIMIT_AMW = int(1000.0 / FPS_MIN_DISCRETE_VALUES_AMW[0]) if FPS_MIN_DISCRETE_VALUES_AMW else 2000 # e.g., 2000ms
# Default FPS if no model or other info available
DEFAULT_FALLBACK_FPS_AMW = 13.0
DEFAULT_FALLBACK_DELAY_AMW = int(770.0 / DEFAULT_FALLBACK_FPS_AMW)

class AnimatorManagerWidget(QWidget):
    # Signals to MainWindow
    selection_changed = pyqtSignal(list)
    active_frame_data_for_display = pyqtSignal(list) # list of hex color strings for the grid
    playback_status_update = pyqtSignal(str, int)    # message, duration_ms (0 for persistent)
    sequence_modified_status_changed = pyqtSignal(bool, str) # is_modified, sequence_name
    undo_redo_state_changed = pyqtSignal(bool, bool)      # can_undo, can_redo
    clipboard_state_changed = pyqtSignal(bool)            # has_clipboard_content
    animator_playback_active_status_changed = pyqtSignal(bool) # is_playing
    request_load_sequence_with_prompt = pyqtSignal(str) # filepath of sequence to load
    # Signal to MainWindow if sampler needs to be disabled due to animator interaction
    request_sampler_disable = pyqtSignal()

    def set_interactive(self, enabled: bool):
        """Enables or disables main interactive UI elements of the animator."""
        # Disable/Enable timeline interaction (if it's a custom widget with such a method)
        if hasattr(self.sequence_timeline_widget, 'setInteractionEnabled'):  # Example
            self.sequence_timeline_widget.setInteractionEnabled(enabled)
        elif hasattr(self.sequence_timeline_widget, 'setEnabled'):  # Standard QListWidget
            self.sequence_timeline_widget.setEnabled(enabled)
        # Disable/Enable frame operation buttons
        if hasattr(self, 'frame_ops_widget') and self.frame_ops_widget:
            self.frame_ops_widget.setEnabled(enabled)
        # Disable/Enable playback controls
        if hasattr(self, 'playback_controls_widget') and self.playback_controls_widget:
            self.playback_controls_widget.setEnabled(enabled)
        # Disable/Enable sequence management controls
        if hasattr(self, 'sequence_management_widget') and self.sequence_management_widget:
            self.sequence_management_widget.setEnabled(enabled)
        # Add any other top-level UI groups/widgets specific to animator interaction
        print(f"AnimatorManagerWidget interactive state set to: {enabled}")

    def set_interactive_state_for_playback(self, is_playing: bool):
        """
        A more granular state controller specifically for playback.
        When playing, this disables everything EXCEPT the playback controls.
        """
        # The main timeline should not be interactive during playback
        if self.sequence_timeline_widget:
            self.sequence_timeline_widget.setEnabled(not is_playing)
        # The controls widget itself can remain enabled, as it contains the stop button
        if self.sequence_controls_widget:
            self.sequence_controls_widget.setEnabled(
                True)  # Keep the container enabled
            # But disable specific buttons within it
            controls_to_disable = [
                self.sequence_controls_widget.add_frame_button,
                self.sequence_controls_widget.duplicate_frame_button,
                self.sequence_controls_widget.delete_frame_button,
                self.sequence_controls_widget.copy_frames_button,
                self.sequence_controls_widget.cut_frames_button,
                self.sequence_controls_widget.paste_frames_button,
                self.sequence_controls_widget.first_frame_button,
                self.sequence_controls_widget.prev_frame_button,
                self.sequence_controls_widget.next_frame_button,
                self.sequence_controls_widget.last_frame_button
            ]
            for button in controls_to_disable:
                if button:
                    button.setEnabled(not is_playing)
            # The play/stop button and speed slider should always reflect the playback state
            # This is handled by other methods, but we ensure they stay enabled here.
            self.sequence_controls_widget.play_stop_button.setEnabled(True)
            self.sequence_controls_widget.speed_slider.setEnabled(True)
            self.sequence_controls_widget.current_speed_display_label.setEnabled(
                True)

    def __init__(self, user_sequences_base_path, sampler_recordings_path, prefab_sequences_base_path, parent=None):
        super().__init__(parent)
        self.setObjectName("AnimatorManager")
        # Paths
        self.user_sequences_base_path = user_sequences_base_path
        self.sampler_recordings_path = sampler_recordings_path
        self.prefab_sequences_base_path = prefab_sequences_base_path
        # --- Renamed self.frame_clipboard to self._clipboard for consistency ---
        self.active_sequence_model: SequenceModel | None = None
        self._clipboard: list[AnimationFrame] = []
        self._playback_timer = QTimer(self)
        self._last_emitted_is_modified: bool | None = None
        self._last_emitted_sequence_name: str | None = None
        # UI Widget placeholders
        self.animator_studio_group_box: QGroupBox | None = None
        self.sequence_selection_combo: QComboBox | None = None
        self.sequence_timeline_widget: SequenceTimelineWidget | None = None
        self.sequence_controls_widget: SequenceControlsWidget | None = None
        # Initialization logic
        self.active_sequence_model = SequenceModel()
        self._init_ui()
        self._connect_ui_signals()
        self._connect_signals_for_active_sequence_model()
        self._update_sequences_combobox()
        self._update_ui_for_current_sequence()
        self._update_animator_controls_enabled_state()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0,0,0,0)
        main_layout.setSpacing(10)
        self.animator_studio_group_box = QGroupBox("🎬 Animator Studio")
        self.animator_studio_group_box.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed) # Fixed vertical
        animator_studio_layout = QVBoxLayout(self.animator_studio_group_box)
        combo_load_layout = QHBoxLayout()
        combo_load_layout.addWidget(QLabel("Sequence:"))
        self.sequence_selection_combo = QComboBox()
        self.sequence_selection_combo.setPlaceholderText("--- Select Sequence ---")
        combo_load_layout.addWidget(self.sequence_selection_combo, 1)
        self.load_sequence_button = QPushButton("📲 Load")
        combo_load_layout.addWidget(self.load_sequence_button)
        animator_studio_layout.addLayout(combo_load_layout)
        action_buttons_layout = QHBoxLayout()
        self.new_sequence_button = QPushButton("✨ New")
        action_buttons_layout.addWidget(self.new_sequence_button)
        self.save_sequence_as_button = QPushButton("💾 Save As...")
        action_buttons_layout.addWidget(self.save_sequence_as_button)
        self.delete_sequence_button = QPushButton("🗑️ Delete")
        action_buttons_layout.addWidget(self.delete_sequence_button)
        action_buttons_layout.addSpacerItem(QSpacerItem(10, 0, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))
        animator_studio_layout.addLayout(action_buttons_layout)        
        main_layout.addWidget(self.animator_studio_group_box) # Add the groupbox to the main layout
        separator_line = QFrame()
        separator_line.setFrameShape(QFrame.Shape.HLine)
        separator_line.setFrameShadow(QFrame.Shadow.Sunken)
        main_layout.addWidget(separator_line)
        self.sequence_timeline_widget = SequenceTimelineWidget()
        self.sequence_timeline_widget.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
        desired_min_timeline_height = 80 # Try this first (e.g., 2 rows * 50px/row + 20px padding/spacing)
        self.sequence_timeline_widget.setMinimumHeight(desired_min_timeline_height)
        main_layout.addWidget(self.sequence_timeline_widget) # Stretch factor for this widget is handled by its size policy now
        self.sequence_controls_widget = SequenceControlsWidget()
        # Controls widget usually has a fixed height based on its buttons
        self.sequence_controls_widget.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        main_layout.addWidget(self.sequence_controls_widget)
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)

    def _connect_ui_signals(self):
        """Connects all UI component signals to their handler slots."""
        # Sequence Combobox / Management Buttons
        self.sequence_selection_combo.currentIndexChanged.connect(self._on_sequence_combo_changed)
        self.load_sequence_button.clicked.connect(self._request_load_selected_sequence_from_main)
        self.new_sequence_button.clicked.connect(self.action_new_sequence)
        self.save_sequence_as_button.clicked.connect(self.action_save_sequence_as)
        self.delete_sequence_button.clicked.connect(self._on_delete_selected_sequence_button_clicked)
        # Controls Widget signals
        self.sequence_controls_widget.play_stop_clicked.connect(self.action_play_pause_toggle) # <<< THE FIX
        self.sequence_controls_widget.add_frame_requested.connect(self.action_add_frame)
        self.sequence_controls_widget.delete_selected_frame_requested.connect(self.action_delete_selected_frames)
        self.sequence_controls_widget.duplicate_selected_frame_requested.connect(self.action_duplicate_selected_frames)
        self.sequence_controls_widget.copy_frames_requested.connect(self.action_copy_frames)
        self.sequence_controls_widget.cut_frames_requested.connect(self.action_cut_frames)
        self.sequence_controls_widget.paste_frames_requested.connect(self.action_paste_frames)
        self.sequence_controls_widget.navigate_first_requested.connect(self.action_navigate_first)
        self.sequence_controls_widget.navigate_prev_requested.connect(self.action_navigate_prev)
        self.sequence_controls_widget.navigate_next_requested.connect(self.action_navigate_next)
        self.sequence_controls_widget.navigate_last_requested.connect(self.action_navigate_last)
        self.sequence_controls_widget.frame_delay_changed.connect(self.on_controls_frame_delay_changed)
        # Timeline Widget signals
        self.sequence_timeline_widget.selection_changed.connect(self._on_timeline_selection_changed)
        self.sequence_timeline_widget.add_frame_action_triggered.connect(self.on_timeline_add_frame_action)
        self.sequence_timeline_widget.copy_frames_action_triggered.connect(self.action_copy_frames)
        self.sequence_timeline_widget.cut_frames_action_triggered.connect(self.action_cut_frames)
        self.sequence_timeline_widget.paste_frames_action_triggered.connect(self.action_paste_frames)
        self.sequence_timeline_widget.duplicate_selected_action_triggered.connect(self.action_duplicate_selected_frames)
        self.sequence_timeline_widget.delete_selected_action_triggered.connect(self.action_delete_selected_frames)
        self.sequence_timeline_widget.select_all_action_triggered.connect(self.action_select_all_frames)
        self.sequence_timeline_widget.insert_blank_frame_before_action_triggered.connect(
            lambda index: self.action_add_frame("blank", at_index=index))
        self.sequence_timeline_widget.insert_blank_frame_after_action_triggered.connect(
            lambda index: self.action_add_frame("blank", at_index=index + 1))

    def _connect_signals(self):
        """Connects all component signals to their handler slots."""
        # Timeline Widget signals
        self.sequence_timeline_widget.selection_changed.connect(
            self._on_timeline_selection_changed)
        self.sequence_timeline_widget.copy_frames_action_triggered.connect(
            self.action_copy_frames)
        self.sequence_timeline_widget.cut_frames_action_triggered.connect(
            self.action_cut_frames)
        self.sequence_timeline_widget.paste_frames_action_triggered.connect(
            self.action_paste_frames)
        self.sequence_timeline_widget.duplicate_selected_action_triggered.connect(
            self.action_duplicate_selected_frames)
        self.sequence_timeline_widget.delete_selected_action_triggered.connect(
            self.action_delete_selected_frames)
        self.sequence_timeline_widget.select_all_action_triggered.connect(
            self.action_select_all_frames)
        self.sequence_timeline_widget.add_frame_action_triggered.connect(
            self.action_add_frame)
        self.sequence_timeline_widget.insert_blank_frame_before_action_triggered.connect(
            self._handle_insert_blank_frame_before_request)
        self.sequence_timeline_widget.insert_blank_frame_after_action_triggered.connect(
            self._handle_insert_blank_frame_after_request)

        # Controls Widget signals
        self.controls_widget.play_requested.connect(self.action_play)
        self.controls_widget.stop_requested.connect(self.action_stop)
        self.controls_widget.frame_delay_changed.connect(
            self._on_frame_delay_changed)
        self.controls_widget.add_frame_requested.connect(self.action_add_frame)
        self.controls_widget.delete_selected_frame_requested.connect(
            self.action_delete_selected_frames)
        self.controls_widget.duplicate_selected_frame_requested.connect(
            self.action_duplicate_selected_frames)
        self.controls_widget.copy_frames_requested.connect(
            self.action_copy_frames)
        self.controls_widget.cut_frames_requested.connect(
            self.action_cut_frames)
        self.controls_widget.paste_frames_requested.connect(
            self.action_paste_frames)
        self.controls_widget.navigate_first_requested.connect(
            self.action_navigate_first)
        self.controls_widget.navigate_prev_requested.connect(
            self.action_navigate_prev)
        self.controls_widget.navigate_next_requested.connect(
            self.action_navigate_next)
        self.controls_widget.navigate_last_requested.connect(
            self.action_navigate_last)

        # Sequence Combobox / Management Buttons
        self.sequence_selector_combo.currentIndexChanged.connect(
            self._on_sequence_combo_selection_changed)
        self.new_sequence_button.clicked.connect(
            lambda: self.create_and_load_new_sequence(prompt_save=True))
        self.save_as_button.clicked.connect(self.action_save_sequence_as)
        self.delete_sequence_button.clicked.connect(
            self._handle_delete_sequence_button_pressed)
        self.load_button.clicked.connect(
            lambda: self._handle_load_from_file_dialog(sequence_type='user'))

        # Playback Timer
        self._playback_timer.timeout.connect(self._on_playback_timer_tick)

    def _emit_state_updates(self):
        """Emits signals to MainWindow to update its state based on current model."""
        if self.active_sequence_model:
            current_is_modified = self.active_sequence_model.is_modified
            current_sequence_name = self.active_sequence_model.name
            if (current_is_modified != self._last_emitted_is_modified) or \
                (current_sequence_name != self._last_emitted_sequence_name):
                self.sequence_modified_status_changed.emit(current_is_modified, current_sequence_name)
                self._last_emitted_is_modified = current_is_modified
                self._last_emitted_sequence_name = current_sequence_name
            self.undo_redo_state_changed.emit(bool(self.active_sequence_model._undo_stack), bool(self.active_sequence_model._redo_stack))
            self.clipboard_state_changed.emit(bool(self._clipboard))
            self._update_animator_controls_enabled_state()

    def _on_timeline_selection_changed(self, selected_indices: list[int]):
        """
        Handles the new signal from the timeline. Updates the model's edit index
        and then tells the timeline delegate to repaint borders, avoiding a full refresh.
        """
        self.selection_changed.emit(
            selected_indices)  # Inform MainWindow of the change
        if not self.active_sequence_model:
            return
        new_edit_index = -1
        if selected_indices:
            # The "edit" frame is always the first one in the selection list.
            new_edit_index = selected_indices[0]
        # Tell the model which frame is the "current" one for editing.
        # This will emit a signal from the model if the index actually changes.
        self.active_sequence_model.set_current_edit_frame_index(new_edit_index)
        # Manually update the delegate's visual state since we are not doing a full refresh.
        current_playback_idx = self.active_sequence_model.get_current_playback_frame_index()
        self.sequence_timeline_widget.update_delegate_visual_state(new_edit_index, current_playback_idx)
        # Update the main pad grid to show the content of the new edit frame.
        self._display_current_edit_frame()
        self._update_animator_controls_enabled_state()

    def on_paint_stroke_started(self, row: int, col: int, mouse_button: Qt.MouseButton):
        """
        Called when a paint stroke starts on the main pad grid.
        Relays this information to the active sequence model.
        """
        if self.active_sequence_model and hasattr(self.active_sequence_model, 'begin_paint_stroke'):
            # print(f"AMW DEBUG: Paint stroke started on pad ({row},{col}), button: {mouse_button}. Relaying to model.") # Optional
            self.active_sequence_model.begin_paint_stroke()
        # else:
            # print("AMW WARNING: on_paint_stroke_started - No active model or model missing begin_paint_stroke.")

    def on_paint_stroke_ended(self, mouse_button: Qt.MouseButton):
        """
        Called when a paint stroke ends on the main pad grid.
        Relays this information to the active sequence model.
        """
        if self.active_sequence_model and hasattr(self.active_sequence_model, 'end_paint_stroke'):
            # print(f"AMW DEBUG: Paint stroke ended with button: {mouse_button}. Relaying to model.") # Optional
            self.active_sequence_model.end_paint_stroke()
        # else:
            # print("AMW WARNING: on_paint_stroke_ended - No active model or model missing end_paint_stroke.")

    def get_current_sequence_fps(self) -> float:
        """
        Calculates and returns the current sequence's playback speed in FPS.
        Returns a default (e.g., 10 FPS) if delay is zero or model is unavailable.
        """
        if self.active_sequence_model and self.active_sequence_model.frame_delay_ms > 0:
            return 1000.0 / self.active_sequence_model.frame_delay_ms
        elif self.active_sequence_model and self.active_sequence_model.frame_delay_ms == 0:
            # Handle case where delay is 0 (could mean max speed or undefined)
            # For FPS display, a very high number or a practical cap might be suitable.
            # Let's return a high practical FPS or a default if delay is 0.
            return 60.0 # Or some other defined maximum sensible FPS
        # Fallback if no model or invalid delay
        # Default FPS from SequenceControlsWidget or a general default
        if hasattr(self, 'sequence_controls_widget') and self.sequence_controls_widget:
            # Attempt to get it from the UI if it has a default
            initial_delay_ms = self.sequence_controls_widget.get_current_delay_ms()
            if initial_delay_ms > 0:
                return 1000.0 / initial_delay_ms
        return 10.0 # General fallback FPS

    def set_playback_fps(self, fps: float):
        """
        Sets the playback speed of the current sequence based on FPS.
        Updates the model's frame_delay_ms and the playback timer if active.
        """
        if not self.active_sequence_model:
            return
        min_fps = 0.1  # Avoid division by zero and ridiculously slow speeds
        max_fps = 100.0 # Practical upper limit for sanity
        clamped_fps = max(min_fps, min(fps, max_fps))
        if clamped_fps <= 0: # Should be caught by min_fps, but safety
            new_delay_ms = 1000 # Default to 1 FPS
        else:
            new_delay_ms = int(round(1000.0 / clamped_fps))
        # Prevent extremely short delays that might overwhelm
        min_delay_ms = 10 # Corresponds to 100 FPS
        actual_delay_ms = max(min_delay_ms, new_delay_ms)
        # print(f"AMW DEBUG: set_playback_fps: target_fps={fps}, clamped_fps={clamped_fps}, new_delay_ms={actual_delay_ms}") # Optional
        self.active_sequence_model.set_frame_delay_ms(actual_delay_ms)
        if self.playback_timer.isActive():
            self.playback_timer.start(actual_delay_ms) # Restart timer with new interval
        if hasattr(self, 'sequence_controls_widget') and self.sequence_controls_widget:
            self.sequence_controls_widget.set_frame_delay_ui(actual_delay_ms)
        # Notify MainWindow that properties (including potentially unsaved speed) changed
        self._emit_state_updates()

    def _on_model_current_edit_frame_changed(self, new_edit_index: int):
        """
        Handles the model changing the edit frame. Updates the timeline's
        selection and the main pad display.
        """
        # Sync the timeline's visual selection to match the model's new state.
        self.sequence_timeline_widget.select_items_by_indices([new_edit_index] if new_edit_index >= 0 else [])
        self._display_current_edit_frame()
        self._update_controls_enabled_state()

    def get_navigation_item_count(self) -> int:
        """Returns the number of actual items in the sequence combo box (excluding placeholder)."""
        if self.sequence_selection_combo:
            count = 0
            for i in range(self.sequence_selection_combo.count()):
                # Check if itemData exists, as placeholder might not have it
                if self.sequence_selection_combo.itemData(i) is not None:
                    count += 1
            return count
        return 0

    def get_navigation_item_text_at_logical_index(self, logical_index: int) -> str | None:
        """
        Returns the display text of the sequence at the given logical_index.
        Logical_index is 0-based for actual sequence items, skipping placeholder.
        """
        if self.sequence_selection_combo:
            actual_combo_index = -1
            current_logical_idx = -1
            for i in range(self.sequence_selection_combo.count()):
                if self.sequence_selection_combo.itemData(i) is not None: # This is an actual item
                    current_logical_idx += 1
                    if current_logical_idx == logical_index:
                        actual_combo_index = i
                        break
            if actual_combo_index != -1:
                return self.sequence_selection_combo.itemText(actual_combo_index)
        return None

    def set_navigation_current_item_by_logical_index(self, logical_index: int) -> str | None:
        """
        Sets the current item in the sequence combo box by its logical index (0-based, skipping placeholders).
        Also updates the internal logical index tracker for the next turn.
        """
        if self.sequence_selection_combo:
            item_count = self.get_navigation_item_count()
            if item_count == 0:
                return None
            # --- Ensure the logical index wraps around correctly ---
            wrapped_logical_index = logical_index % item_count
            if wrapped_logical_index < 0:
                wrapped_logical_index += item_count
            # This is the new internal logical index for the next turn
            # self.current_oled_nav_item_logical_index = wrapped_logical_index # This state belongs in MainWindow
            actual_combo_index_to_set = -1
            current_logical_idx = -1
            for i in range(self.sequence_selection_combo.count()):
                current_text = self.sequence_selection_combo.itemText(i)
                item_data = self.sequence_selection_combo.itemData(i)
                if item_data: # A more reliable check for an actual item
                    current_logical_idx += 1
                    if current_logical_idx == wrapped_logical_index:
                        actual_combo_index_to_set = i
                        break
            if actual_combo_index_to_set != -1:
                if self.sequence_selection_combo.currentIndex() != actual_combo_index_to_set:
                    self.sequence_selection_combo.setCurrentIndex(actual_combo_index_to_set)
                return self.sequence_selection_combo.itemText(actual_combo_index_to_set)
        return None

    def trigger_navigation_current_item_action(self):
        """
        Triggers the action for the currently selected item in the sequence combo box,
        which is typically loading it.
        """
        # print("AMW TRACE: trigger_navigation_current_item_action called.") # Optional
        self._request_load_selected_sequence_from_main()

    def action_undo(self):
        self.request_sampler_disable.emit()
        if self.active_sequence_model.undo():
            self.playback_status_update.emit("Undo.", 1500)
        else:
            self.playback_status_update.emit("Nothing to undo.", 1500)
        self._emit_state_updates()

    def action_redo(self):
        self.request_sampler_disable.emit()
        if self.active_sequence_model.redo():
            self.playback_status_update.emit("Redo.", 1500)
        else:
            self.playback_status_update.emit("Nothing to redo.", 1500)
        self._emit_state_updates()

    def action_copy_frames(self):
        self.request_sampler_disable.emit()
        selected_indices = self.sequence_timeline_widget.get_selected_item_indices()
        if not selected_indices:
            self.playback_status_update.emit(
                "No frames selected to copy.", 2000)
            return
        self._clipboard.clear()
        copied_frames_count = 0
        for index in sorted(selected_indices):
            frame_obj = self.active_sequence_model.get_frame_object(index)
            if frame_obj:
                self._clipboard.append(AnimationFrame(
                    colors=list(frame_obj.get_all_colors())))
                copied_frames_count += 1
        if copied_frames_count > 0:
            self.playback_status_update.emit(
                f"{copied_frames_count} frame(s) copied.", 2000)
        else:
            self.playback_status_update.emit(
                "Could not copy selected frames.", 2000)
        self._emit_state_updates()

    def action_cut_frames(self):
        self.request_sampler_disable.emit()
        self.stop_current_animation_playback()
        selected_indices = self.sequence_timeline_widget.get_selected_item_indices()
        if not selected_indices:
            self.playback_status_update.emit(
                "No frames selected to cut.", 2000)
            return
        self._clipboard.clear()
        copied_frames_count = 0
        for index in sorted(selected_indices):
            frame_obj = self.active_sequence_model.get_frame_object(index)
            if frame_obj:
                self._clipboard.append(AnimationFrame(
                    colors=list(frame_obj.get_all_colors())))
                copied_frames_count += 1
        if copied_frames_count == 0:
            self.playback_status_update.emit(
                "Could not prepare frames for cutting.", 2000)
            return
        if self.active_sequence_model.delete_frames_at_indices(selected_indices):
            self.playback_status_update.emit(
                f"{copied_frames_count} frame(s) cut.", 2000)
        else:
            self._clipboard.clear()
            self.playback_status_update.emit("Error cutting frames.", 3000)
        self._emit_state_updates()

    def action_paste_frames(self):
        self.request_sampler_disable.emit()
        if not self._clipboard:
            self.playback_status_update.emit("Clipboard is empty.", 2000)
            return
        self.stop_current_animation_playback()
        selected_indices = self.sequence_timeline_widget.get_selected_item_indices()
        insertion_index = max(selected_indices) + 1 if selected_indices else \
            (self.active_sequence_model.get_current_edit_frame_index() + 1
            if self.active_sequence_model.get_current_edit_frame_index() != -1
            else self.active_sequence_model.get_frame_count())
        pasted_indices = self.active_sequence_model.paste_frames(
            self._clipboard, at_index=insertion_index)
        if pasted_indices:
            self.playback_status_update.emit(
                f"{len(pasted_indices)} frame(s) pasted.", 2000)
            QTimer.singleShot(
                0, lambda: self.sequence_timeline_widget.select_items_by_indices(pasted_indices))
        else:
            self.playback_status_update.emit("Error pasting frames.", 3000)
        self._emit_state_updates()

    def action_duplicate_selected_frames(self):
        self.request_sampler_disable.emit()
        self.stop_current_animation_playback()
        selected_indices = self.sequence_timeline_widget.get_selected_item_indices()
        if not selected_indices:
            self.playback_status_update.emit("No frames selected to duplicate.", 1500); return
        newly_created_indices = self.active_sequence_model.duplicate_frames_at_indices(selected_indices)
        if newly_created_indices:
            self.playback_status_update.emit(f"{len(newly_created_indices)} frame(s) duplicated.", 1500)
            QTimer.singleShot(0, lambda: self.sequence_timeline_widget.select_items_by_indices(newly_created_indices))
        else:
            self.playback_status_update.emit("Duplication failed.", 1500)

    def action_delete_selected_frames(self):
        self.request_sampler_disable.emit()
        self.stop_current_animation_playback()
        selected_indices = self.sequence_timeline_widget.get_selected_item_indices()
        if not selected_indices:
            self.playback_status_update.emit("No frames selected to delete.", 1500); return
        if self.active_sequence_model.delete_frames_at_indices(selected_indices):
            self.playback_status_update.emit(f"{len(selected_indices)} frame(s) deleted.", 1500)
        else:
            self.playback_status_update.emit("Deletion failed.", 1500)

    def action_select_all_frames(self):
        self.request_sampler_disable.emit()
        if self.active_sequence_model.get_frame_count() > 0:
            all_indices = list(range(self.active_sequence_model.get_frame_count()))
            self.sequence_timeline_widget.select_items_by_indices(all_indices)
            self.playback_status_update.emit(f"All {len(all_indices)} frames selected.", 1500)
        else:
            self.playback_status_update.emit("No frames to select.", 1500)
        self._update_animator_controls_enabled_state() # Update local button states based on selection

    def action_play_pause_toggle(self):
        """
        Authoritative method to toggle animation playback. This is called by
        UI buttons and global shortcuts.
        """
        self.request_sampler_disable.emit() # Ensure other modes are off
        if self.active_sequence_model.get_frame_count() == 0:
            self.playback_status_update.emit("Cannot play: No frames in sequence.", 2000)
            return
        if self.active_sequence_model.get_is_playing():
            self.action_stop()
        else:
            self.action_play()

    def _on_apply_fx_to_frames_clicked(self):
        """
        Handles the click of the 'Apply to Selected Frames' button.
        """
        if not self.animator_manager:
            return
        reply = QMessageBox.question(self, "Apply FX to Frames",
                                    "This will permanently modify the selected frames with the current color grading settings.\n\n"
                                    "This action can be undone with Ctrl+Z.\n\n"
                                    "Do you want to continue?",
                                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                    QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            # Gather current FX parameters
            fx_params = {
                'brightness': self.fx_brightness_slider.value(),
                'saturation': self.fx_saturation_slider.value(),
                'contrast': self.fx_contrast_slider.value(),
                'hue_shift': self.fx_hue_slider.value()
            }
            # Tell the animator manager to perform the action
            self.animator_manager.apply_fx_to_selected_frames(fx_params)

    def apply_fx_to_selected_frames(self, fx_params: dict):
        """
        Applies the given FX parameters permanently to the currently selected frames in the model.
        """
        if not self.active_sequence_model or not self.sequence_timeline_widget:
            return
        selected_indices = self.sequence_timeline_widget.get_selected_item_indices()
        if not selected_indices:
            self.playback_status_update.emit(
                "No frames selected to apply FX.", 2000)
            return
        # Delegate the core logic to the model
        self.active_sequence_model.apply_fx_to_frames(
            selected_indices, fx_params)
        self.playback_status_update.emit(
            f"FX applied to {len(selected_indices)} frames.", 2000)

    def apply_fx_to_frames(self, indices: list, fx_params: dict):
        """
        Permanently applies color grading FX to the specified frames.
        This is an undoable action.
        """
        if not indices:
            return
        # 1. Save the state of the entire sequence BEFORE making changes.
        self._push_undo_state()
        # 2. Apply the filter to each selected frame
        for index in indices:
            if 0 <= index < len(self.frames):
                frame = self.frames[index]
                original_colors = frame.get_all_colors()
                # We need a filter function here. Let's assume it exists in a utils module for now.
                # from utils import color_utils
                # modified_colors = color_utils.apply_fx_filter(original_colors, fx_params)
                # For now, let's put the logic directly here.
                # This logic is duplicated from MainWindow._apply_live_fx_filter
                brightness_adj = fx_params.get('brightness', 0)
                saturation_adj = fx_params.get('saturation', 0)
                contrast_adj = fx_params.get('contrast', 0)
                hue_shift = fx_params.get('hue_shift', 0.0)
                brightness_factor = 1.0 + (brightness_adj / 100.0)
                saturation_factor = 1.0 + (saturation_adj / 100.0)
                contrast_factor = 1.0 + (contrast_adj / 100.0)
                modified_colors = []
                for hex_str in original_colors:
                    try:
                        import colorsys  # Local import
                        color = QColor(hex_str)
                        r, g, b, a_val = color.redF(), color.greenF(), color.blueF(), color.alphaF()
                        r, g, b = r * brightness_factor, g * brightness_factor, b * brightness_factor
                        if contrast_factor != 1.0:
                            r, g, b = 0.5 + contrast_factor * \
                                (r - 0.5), 0.5 + contrast_factor * \
                                (g - 0.5), 0.5 + contrast_factor * (b - 0.5)
                        r, g, b = max(0.0, min(1.0, r)), max(
                            0.0, min(1.0, g)), max(0.0, min(1.0, b))
                        h, s, v = colorsys.rgb_to_hsv(r, g, b)
                        s *= saturation_factor
                        s = max(0.0, min(1.0, s))
                        if hue_shift != 0:
                            h = (h + (hue_shift / 360.0)) % 1.0
                        final_r, final_g, final_b = colorsys.hsv_to_rgb(
                            h, s, v)
                        final_color = QColor.fromRgbF(
                            final_r, final_g, final_b, a_val)
                        modified_colors.append(final_color.name())
                    except Exception:
                        modified_colors.append(hex_str)
                # Update the frame's data with the new colors
                frame.colors = modified_colors
        # 3. Emit a signal to tell the UI that the frames have fundamentally changed.
        self.frames_changed.emit()
        # Ensure the sequence is marked as needing a save.
        self._mark_modified()

    def get_current_grid_colors_from_main_window(self) -> list[str]:
        print("WARN AnimatorManager: get_current_grid_colors_from_main_window needs implementation or alternative.")
        return [QColor("black").name()] * 64 # Placeholder

    def _update_ui_for_current_sequence(self):
        # print(f"DEBUG AMW._update_ui_for_current_sequence: Called. Frame count: {self.active_sequence_model.get_frame_count()}") # ADD THIS
        # Updates timeline, controls widget properties based on the active_sequence_model
        all_frames_colors = [self.active_sequence_model.get_frame_colors(i) or [QColor("black").name()] * 64
                            for i in range(self.active_sequence_model.get_frame_count())]
        current_edit_idx = self.active_sequence_model.get_current_edit_frame_index()
        current_playback_idx = self.active_sequence_model.get_current_playback_frame_index() if self.active_sequence_model.get_is_playing() else -1
        self.sequence_timeline_widget.update_frames_display(all_frames_colors, current_edit_idx, current_playback_idx)
        self.sequence_controls_widget.set_frame_delay_ui(self.active_sequence_model.frame_delay_ms)
        # Loop toggle is usually handled by its own signal/slot if SequenceControlsWidget has one for loop
        self._emit_state_updates() # This also calls local _update_animator_controls_enabled_state

    def _update_ui_for_current_sequence_properties(self):
        # Called when model properties like name, delay, loop change
        self.sequence_controls_widget.set_frame_delay_ui(self.active_sequence_model.frame_delay_ms)
        # Update combo box if name changed
        self.refresh_sequences_list_and_select(
            self.active_sequence_model.name,
            self._get_type_id_from_filepath(self.active_sequence_model.loaded_filepath)
        )
        self._emit_state_updates()

    def _update_animator_controls_enabled_state(self):
        # This enables/disables controls *within* this AnimatorManagerWidget
        has_frames = self.active_sequence_model.get_frame_count() > 0 if self.active_sequence_model else False
        num_selected_frames = len(self.sequence_timeline_widget.get_selected_item_indices()) if self.sequence_timeline_widget else 0
        can_operate_on_selection = num_selected_frames > 0
        self.sequence_controls_widget.set_controls_enabled_state(
            enabled=True,
            frame_selected=can_operate_on_selection,
            has_frames=has_frames,
            clipboard_has_content=bool(self._clipboard)
        )
        self.sequence_timeline_widget.setEnabled(True)
        is_valid_combo_selection = self.sequence_selection_combo.currentIndex() > 0 and \
                                    self.sequence_selection_combo.currentText() != "No sequences found"
        self.load_sequence_button.setEnabled(is_valid_combo_selection)
        item_data = self.sequence_selection_combo.currentData()
        can_delete_combo_item = is_valid_combo_selection and item_data and item_data.get("type") in ["user", "sampler"]
        self.delete_sequence_button.setEnabled(can_delete_combo_item)
        self.new_sequence_button.setEnabled(True)
        self.save_sequence_as_button.setEnabled(has_frames)

    def on_model_frame_content_updated(self, frame_index: int):
        # This slot is called when SequenceModel emits frame_content_updated,
        # typically after a pad color changes in the current edit frame.
        current_edit_idx = self.active_sequence_model.get_current_edit_frame_index()
        # 1. Update the main hardware/GUI pad grid IF the updated frame IS the current edit frame.
        #    This ensures live painting is reflected on the main grid.
        if frame_index == current_edit_idx:
            colors_hex_for_main_grid = self.active_sequence_model.get_frame_colors(frame_index)
            if colors_hex_for_main_grid:
                self.active_frame_data_for_display.emit(colors_hex_for_main_grid)
            # else: # Optional: handle case where getting colors failed, maybe emit blank
                # self.active_frame_data_for_display.emit([QColor("black").name()] * 64)
        # <<< MODIFIED BEHAVIOR: Update ONLY the specific thumbnail in the timeline. >>>
        # Do NOT call self._update_ui_for_current_sequence() here, as that rebuilds the entire timeline.
        if self.sequence_timeline_widget: # Check if timeline widget exists
            frame_colors_for_thumbnail = self.active_sequence_model.get_frame_colors(frame_index)
            if frame_colors_for_thumbnail:
                # Call the new method in SequenceTimelineWidget
                self.sequence_timeline_widget.update_single_frame_thumbnail_data(frame_index, frame_colors_for_thumbnail)
            # else:
                # print(f"AMW WARNING: on_model_frame_content_updated - Could not get colors for frame {frame_index} to update thumbnail.")
        # else:
            # print("AMW WARNING: on_model_frame_content_updated - sequence_timeline_widget is None, cannot update thumbnail.")
        # 3. Emit general state updates (undo/redo, modified status for title/OLED, animator controls).
        #    This is still necessary because painting a pad does change the modified state (once)
        #    and can affect undo/redo availability.
        self._emit_state_updates()

    def _connect_signals_for_active_sequence_model(self):
        """Connects the active sequence model's signals and internal timers."""
        if self.active_sequence_model:
            try:
                self.active_sequence_model.frames_changed.disconnect()
                self.active_sequence_model.frame_content_updated.disconnect()
                self.active_sequence_model.current_edit_frame_changed.disconnect()
                self.active_sequence_model.properties_changed.disconnect()
                self.active_sequence_model.playback_state_changed.disconnect()
            except TypeError: pass
            self.active_sequence_model.frames_changed.connect(self._update_ui_for_current_sequence)
            self.active_sequence_model.frame_content_updated.connect(self.on_model_frame_content_updated)
            self.active_sequence_model.current_edit_frame_changed.connect(self.on_model_edit_frame_changed)
            self.active_sequence_model.properties_changed.connect(self._update_ui_for_current_sequence_properties)
            self.active_sequence_model.playback_state_changed.connect(self.on_model_playback_state_changed)
        # Connect the playback timer tick
        try:
            self._playback_timer.timeout.disconnect()
        except TypeError: pass
        self._playback_timer.timeout.connect(self.advance_and_play_next_frame)

    def _display_current_edit_frame(self):
        """
        Gets the color data for the currently selected edit frame from the model
        and emits it to the main window for display.
        """
        if not self.active_sequence_model:
            self.active_frame_data_for_display.emit([QColor("black").name()] * 64)
            return
        edit_idx = self.active_sequence_model.get_current_edit_frame_index()
        colors_hex = None
        if edit_idx != -1:
            colors_hex = self.active_sequence_model.get_frame_colors(edit_idx)
        
        # Ensure we always emit a valid 64-color list
        final_colors = colors_hex if colors_hex else [QColor("black").name()] * 64
        self.active_frame_data_for_display.emit(final_colors)

    def on_model_edit_frame_changed(self, frame_index: int):
        # This method is called when the MODEL dictates the edit frame has changed
        # (e.g., after a frame deletion).
        # Visually update the selection in the timeline widget to match the model.
        self.sequence_timeline_widget.select_items_by_indices([frame_index] if frame_index >= 0 else [])
        # The rest of the logic remains the same.
        self._display_current_edit_frame()
        self._emit_state_updates() # This will update controls

    def on_model_playback_state_changed(self, is_playing: bool):
        # Update the button's visual state (text, icon)
        self.sequence_controls_widget.update_playback_button_state(is_playing)
        # Update the interactivity of the UI based on the new playback state
        self.set_interactive_state_for_playback(is_playing)  # <<< THE FIX
        if is_playing:
            self.playback_status_update.emit("Sequence playing...", 0)
            if self.active_sequence_model.frame_delay_ms > 0:
                self._playback_timer.start(
                    self.active_sequence_model.frame_delay_ms)
        else:
            self._playback_timer.stop()
            self.playback_status_update.emit("Sequence stopped.", 3000)
            # When stopping, restore the main grid to the current edit frame
            edit_idx = self.active_sequence_model.get_current_edit_frame_index()
            current_frame_colors = self.active_sequence_model.get_frame_colors(
                edit_idx) if edit_idx != -1 else None
            self.active_frame_data_for_display.emit(
                current_frame_colors if current_frame_colors else [QColor("black").name()] * 64)
        # Notify MainWindow of the state change for global UI updates
        self.animator_playback_active_status_changed.emit(is_playing)

    def stop_current_animation_playback(self):
        if self._playback_timer.isActive(): self._playback_timer.stop()
        if self.active_sequence_model.get_is_playing(): self.active_sequence_model.stop_playback()

    def on_timeline_frame_selected(self, frame_index: int):
        # print(
            # f"DEBUG AMW: on_timeline_frame_selected CALLED with frame_index from timeline: {frame_index}")
        self.request_sampler_disable.emit()
        # Tell the model about the new intended edit frame from the UI selection.
        if self.active_sequence_model:
            # Only proceed if the timeline's selection is different from the model's current edit frame,
            # or if the model currently has no selection (-1) and the timeline selects a valid one.
            # This helps prevent re-processing if the model already knows this is the edit frame.
            current_model_edit_idx = self.active_sequence_model.get_current_edit_frame_index()
            if current_model_edit_idx != frame_index:
                # print(
                    # f"DEBUG AMW: on_timeline_frame_selected - Model's edit_idx ({current_model_edit_idx}) differs from timeline's ({frame_index}). Updating model.")
                self.active_sequence_model.set_current_edit_frame_index(
                    frame_index)
                # When set_current_edit_frame_index is called and it *actually changes* the index in the model,
                # the model will emit current_edit_frame_changed.
                # Our slot on_model_edit_frame_changed will then handle updating the main display
                # and ensuring the timeline's selection is synced.
            # else: # Optional Debug
                # print(f"DEBUG AMW: on_timeline_frame_selected - Model's edit_idx ({current_model_edit_idx}) already matches timeline's ({frame_index}). No model update needed from here.")
        # else: # Optional Debug
            # print("DEBUG AMW: on_timeline_frame_selected - No active sequence model.")
        # No direct emission of active_frame_data_for_display here.
        # Let on_model_edit_frame_changed handle that when the model confirms the change.
        # We still need to emit general state updates as selection can affect enabled states of controls.
        self._emit_state_updates()

    def on_timeline_add_frame_action(self, frame_type: str): # frame_type will now only be "blank" from timeline menu
        # print(f"DEBUG AMW.on_timeline_add_frame_action: type='{frame_type}'") # Optional debug
        self.request_sampler_disable.emit()
        current_edit_idx = self.active_sequence_model.get_current_edit_frame_index()
        insert_at = current_edit_idx + 1 if current_edit_idx != -1 else None
        if frame_type == "blank":
            self.action_add_frame("blank", at_index=insert_at)
        # The "snapshot" case is removed here as the timeline menu will no longer offer it.
        # If timeline somehow still sent "snapshot", action_add_frame would handle it (likely as a blank).

    def action_add_frame(self, frame_type: str, at_index: int | None = None, snapshot_data: list[str] | None = None):
        # print(f"DEBUG AMW.action_add_frame: Called with type='{frame_type}', at_index={at_index}, snapshot_data_present={snapshot_data is not None}") # Optional debug
        self.request_sampler_disable.emit()
        self.stop_current_animation_playback()
        if frame_type == "blank":
            self.active_sequence_model.add_blank_frame(at_index)
            self.playback_status_update.emit("Blank frame added.", 1500)
        elif frame_type == "snapshot":
            # This case would only be hit if some other part of the code calls it with "snapshot" AND data.
            # UI elements are being changed to not call this directly without data.
            if snapshot_data:
                # To handle a "true" snapshot request (if it ever comes with data):
                # 1. Add a blank frame where the snapshot will be.
                new_frame_idx = self.active_sequence_model.add_blank_frame(at_index)
                # 2. If a frame was added and selected, update its content.
                if new_frame_idx == self.active_sequence_model.get_current_edit_frame_index() and new_frame_idx != -1:
                    self.active_sequence_model.update_all_pads_in_current_edit_frame(snapshot_data)
                    self.playback_status_update.emit("Snapshot applied to new frame.", 1500)
                else:
                    self.playback_status_update.emit("Snapshot data received, but couldn't apply to new frame.", 3000)
            else:
                self.playback_status_update.emit("Snapshot type called without data; adding blank frame instead.", 2500)
                self.active_sequence_model.add_blank_frame(at_index) # Fallback to blank
        else:
            print(f"Warning AMW.action_add_frame: Unknown frame_type '{frame_type}', adding blank frame.")
            self.active_sequence_model.add_blank_frame(at_index) # Fallback to blank

    def action_navigate_first(self):
        self.request_sampler_disable.emit()
        if self.active_sequence_model.get_frame_count() > 0: self.active_sequence_model.set_current_edit_frame_index(0)

    def action_navigate_prev(self):
        self.request_sampler_disable.emit()
        idx, count = self.active_sequence_model.get_current_edit_frame_index(), self.active_sequence_model.get_frame_count()
        if count > 0: self.active_sequence_model.set_current_edit_frame_index((idx - 1 + count) % count)

    def action_navigate_next(self):
        self.request_sampler_disable.emit()
        idx, count = self.active_sequence_model.get_current_edit_frame_index(), self.active_sequence_model.get_frame_count()
        if count > 0: self.active_sequence_model.set_current_edit_frame_index((idx + 1) % count)

    def action_navigate_last(self):
        self.request_sampler_disable.emit()
        count = self.active_sequence_model.get_frame_count()
        if count > 0: self.active_sequence_model.set_current_edit_frame_index(count - 1)

    def action_play(self):
        self.request_sampler_disable.emit()
        if self.active_sequence_model.get_frame_count() == 0:
            self.playback_status_update.emit("Cannot play: No frames.", 2000)
            self.sequence_controls_widget.update_playback_button_state(False)
            return
        start_idx = self.active_sequence_model.get_current_edit_frame_index()
        if start_idx == -1 or start_idx >= self.active_sequence_model.get_frame_count(): start_idx = 0
        self.active_sequence_model._playback_frame_index = start_idx # Directly set for start
        self.active_sequence_model.start_playback() # This will emit playback_state_changed

    def action_stop(self):
        self.active_sequence_model.stop_playback()

    def on_controls_frame_delay_changed(self, delay_ms: int):
        self.active_sequence_model.set_frame_delay_ms(delay_ms)
        if self._playback_timer.isActive(): self._playback_timer.start(delay_ms)
        self.playback_status_update.emit(f"Frame delay set to {delay_ms} ms.", 1500)

    def advance_and_play_next_frame(self):
        if not self.active_sequence_model.get_is_playing():
            self.stop_current_animation_playback(); return

        colors_hex = self.active_sequence_model.step_and_get_playback_frame_colors()
        if colors_hex:
            self.active_frame_data_for_display.emit(colors_hex)
            # Timeline update will happen via _update_ui_for_current_sequence triggered by model's playback state
        
        if not self.active_sequence_model.get_is_playing(): # Playback might have ended
            self.stop_current_animation_playback()
            # on_model_playback_state_changed will handle further UI updates

    def _load_all_sequences_metadata(self) -> dict:
        PREFIX_SAMPLER = "[Sampler] "
        PREFIX_PREFAB = "[Prefab] "
        PREFIX_USER = ""
        loaded_meta = {}
        sources = [
            {"id": "sampler", "prefix": PREFIX_SAMPLER},
            {"id": "user", "prefix": PREFIX_USER},
            {"id": "prefab", "prefix": PREFIX_PREFAB}
        ]
        for src_cfg in sources:
            type_id, prefix = src_cfg["id"], src_cfg["prefix"]
            abs_dir = self._get_sequence_dir_path(type_id)
            os.makedirs(abs_dir, exist_ok=True)
            if not os.path.isdir(abs_dir): continue
            for filepath in glob.glob(os.path.join(abs_dir, "*.json")):
                try:
                    with open(filepath, "r", encoding='utf-8') as f: data = json.load(f)
                    if not isinstance(data, dict) or "name" not in data or "frames" not in data: continue
                    raw_name = data.get("name", os.path.splitext(os.path.basename(filepath))[0])
                    display_name = prefix + str(raw_name).replace("_", " ").replace("-", " ")
                    if display_name: loaded_meta[display_name] = {"path": filepath, "type": type_id, "raw_name": raw_name}
                except Exception: pass # Ignore malformed files
        return loaded_meta

    def _get_sequence_dir_path(self, dir_type: str = "user") -> str:
        if dir_type == "user":
            return self.user_sequences_base_path
        elif dir_type == "prefab":
            return self.prefab_sequences_base_path
        elif dir_type == "sampler":
            return self.sampler_recordings_path
        else:
            print(f"Warning: Unknown sequence dir_type '{dir_type}' in AnimatorManagerWidget. Defaulting to user path.")
            return self.user_sequences_base_path

    def _update_sequences_combobox(self, active_seq_raw_name: str | None = None, active_seq_type_id: str | None = None):
        self.sequence_selection_combo.blockSignals(True)
        current_text_before = self.sequence_selection_combo.currentText()
        self.sequence_selection_combo.clear()
        self.sequence_selection_combo.addItem("--- Select Sequence ---")
        
        # --- FIX: Correctly call the helper method to get the data ---
        all_meta = self._load_all_sequences_metadata()
        
        if not all_meta:
            self.sequence_selection_combo.addItem("No sequences found")
        else:
            sorted_names = sorted(all_meta.keys(), key=lambda k: (
                0 if all_meta[k]['type'] == 'prefab' else 1 if all_meta[k]['type'] == 'sampler' else 2, k.lower()
            ))
            for name in sorted_names: self.sequence_selection_combo.addItem(name, userData=all_meta[name])
        
        target_idx = 0
        if active_seq_raw_name and active_seq_type_id:
            prefix_map = {"prefab": "[Prefab] ", "sampler": "[Sampler] ", "user": ""}
            text_to_find = prefix_map.get(active_seq_type_id, "") + str(active_seq_raw_name).replace("_", " ").replace("-", " ")
            idx = self.sequence_selection_combo.findText(text_to_find, Qt.MatchFlag.MatchFixedString)
            if idx != -1: target_idx = idx
        elif current_text_before not in ["--- Select Sequence ---", "No sequences found"]:
            idx = self.sequence_selection_combo.findText(current_text_before, Qt.MatchFlag.MatchFixedString)
            if idx != -1: target_idx = idx
        
        if self.sequence_selection_combo.count() > target_idx:
            self.sequence_selection_combo.setCurrentIndex(target_idx)
            
        self.sequence_selection_combo.blockSignals(False)
        self._on_sequence_combo_changed(self.sequence_selection_combo.currentIndex())

    def refresh_sequences_list_and_select(self, active_seq_raw_name: str | None = None, active_seq_type_id: str | None = None):
        self._update_sequences_combobox(active_seq_raw_name, active_seq_type_id)

    def _on_sequence_combo_changed(self, index: int):
        # This method now primarily updates the enabled state of its own load/delete buttons
        is_valid_item = False
        can_delete_selected = False
        item_data = self.sequence_selection_combo.itemData(index)
        if index > 0 and self.sequence_selection_combo.itemText(index) != "No sequences found" and item_data:
            is_valid_item = True
            if item_data.get("type") in ["user", "sampler"]:
                can_delete_selected = True
        self.load_sequence_button.setEnabled(is_valid_item)
        self.delete_sequence_button.setEnabled(can_delete_selected)

    def _handle_load_sequence_request(self, filepath: str):
        self.request_sampler_disable.emit()
        # --- Use the new intelligent check ---
        if self._is_current_sequence_worth_saving():
            # This logic is now handled by MainWindow's _handle_animator_request_load_prompt
            # But we keep a fallback here just in case. The prompt in MainWindow is better.
            self.request_load_sequence_with_prompt.emit(filepath)
            return
        # If not worth saving, proceed directly with the load.
        self.stop_current_animation_playback()
        new_model = SequenceModel()
        if new_model.load_from_file(filepath):
            self.active_sequence_model = new_model
            self._connect_signals_for_active_sequence_model()
            self._update_ui_for_current_sequence()
            self.playback_status_update.emit(f"Sequence '{self.active_sequence_model.name}' loaded.", 2000)
            self.refresh_sequences_list_and_select(
                self.active_sequence_model.name,
                self._get_type_id_from_filepath(filepath)
            )
        else:
            parent_widget_for_dialog = self.parent() if self.parent() else self
            QMessageBox.warning(parent_widget_for_dialog, "Load Error", f"Failed to load: {os.path.basename(filepath)}")
            self.refresh_sequences_list_and_select()
        self._emit_state_updates()

    def _on_load_selected_sequence_button_clicked(self):
        # This method is now effectively replaced by _request_load_selected_sequence_from_main
        # and the logic it triggers in MainWindow.
        # We can keep it simple or remove it if _request_load_selected_sequence_from_main is connected directly.
        # For clarity, let's have _request_load_selected_sequence_from_main handle it.
        pass # Or remove if you connect _request_load_selected_sequence_from_main directly

    def _is_current_sequence_worth_saving(self) -> bool:
        """
        Determines if the current sequence has meaningful, unsaved changes.
        This prevents save prompts for a pristine, untouched "New Sequence".
        """
        if not self.active_sequence_model:
            return False
        # If the sequence isn't marked as modified at all, it's not worth saving.
        if not self.active_sequence_model.is_modified:
            return False
        # At this point, is_modified is True. We need to check if it's the edge case
        # of a single, blank, default "New Sequence".
        if not self.active_sequence_model.loaded_filepath and self.active_sequence_model.name == "New Sequence":
            if self.active_sequence_model.get_frame_count() == 1:
                frame_colors = self.active_sequence_model.get_frame_colors(0)
                if frame_colors and all(color == QColor("black").name() for color in frame_colors):
                    # It's a single black frame on a default new sequence. Not worth saving.
                    return False
        # If any of the above checks failed, it means there are real changes worth saving.
        return True

    def _sanitize_filename(self, name: str) -> str:
        name = str(name)
        name = re.sub(r'[^\w\s-]', '', name).strip()
        name = re.sub(r'[-\s]+', '_', name)
        return name if name else "untitled_sequence"

    def _get_type_id_from_filepath(self, filepath: str | None) -> str:
        if not filepath: return "user" # Default
        path_lower = filepath.lower()
        if "prefab" in path_lower: return "prefab"
        if "sampler_recordings" in path_lower: return "sampler"
        return "user"

    def create_new_sequence(self, prompt_save=True):
        """Creates a new, empty sequence, prompting to save the old one if necessary."""
        if prompt_save and self._is_current_sequence_worth_saving():
            reply = QMessageBox.question(self, "Unsaved Animator Changes",
                                        f"Animation '{self.active_sequence_model.name}' has unsaved changes.\nSave before creating a new sequence?",
                                        QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel,
                                        QMessageBox.StandardButton.Cancel)
            if reply == QMessageBox.StandardButton.Save:
                if not self.action_save_sequence_as():
                    return
            elif reply == QMessageBox.StandardButton.Cancel:
                return
        self.stop_current_animation_playback()
        self.active_sequence_model = SequenceModel()
        self.active_sequence_model.add_blank_frame()
        self._connect_signals_for_active_sequence_model()
        self._update_ui_for_current_sequence()
        # --- FIX: Select the initial frame and update the main display ---
        self.active_sequence_model.set_current_edit_frame_index(0)
        self._display_current_edit_frame()  # This updates the pads
        self.playback_status_update.emit("New sequence created.", 2000)
        self.refresh_sequences_list_and_select()

    def load_sequence_from_file(self, filepath: str):
        """Internal method to load a sequence from a file, bypassing any prompts."""
        self.stop_current_animation_playback()
        new_model = SequenceModel()
        if new_model.load_from_file(filepath):
            self.active_sequence_model = new_model
            self._connect_signals_for_active_sequence_model()
            self._update_ui_for_current_sequence()
            self.playback_status_update.emit(
                f"Sequence '{self.active_sequence_model.name}' loaded.", 2000)
            self.refresh_sequences_list_and_select(
                self.active_sequence_model.name,
                self._get_type_id_from_filepath(filepath)
            )
        else:
            QMessageBox.warning(
                self, "Load Error", f"Failed to load: {os.path.basename(filepath)}")
            self.refresh_sequences_list_and_select()
        self._emit_state_updates()

    def action_new_sequence(self):
        """Public action called by UI buttons to create a new sequence."""
        self.request_sampler_disable.emit()
        self.create_new_sequence(prompt_save=True)

    def _request_load_selected_sequence_from_main(self):
        """Sends a signal to MainWindow to handle the prompt and load process."""
        index = self.sequence_selection_combo.currentIndex()
        if index > 0:
            item_data = self.sequence_selection_combo.itemData(index)
            if item_data and "path" in item_data:
                self.request_load_sequence_with_prompt.emit(item_data["path"])

    def action_save_sequence_as(self):
        self.request_sampler_disable.emit()
        if self.active_sequence_model.get_frame_count() == 0:
            # QMessageBox.information(self, "Save", "No frames to save.") # Needs parent from MW
            self.playback_status_update.emit("Cannot save: No frames in sequence.", 3000)
            return False # Indicate save failed or was not possible
        self.stop_current_animation_playback()
        suggested_name = self.active_sequence_model.name if self.active_sequence_model.name != "New Sequence" else ""
        text, ok = QInputDialog.getText(self, "Save Sequence As...", "Sequence Name:", text=suggested_name) # Problematic: self is not QMainWindow
        if not (ok and text and text.strip()):
            self.playback_status_update.emit("Save As cancelled.", 2000)
            return False
        raw_name = text.strip()
        filename_base = self._sanitize_filename(raw_name)
        if raw_name.lower().startswith(("[prefab]", "[sampler]")):
            # QMessageBox.warning(self, "Save Error", "Cannot start with '[Prefab]' or '[Sampler]'.") # Needs MW parent
            self.playback_status_update.emit("Save Error: Invalid name prefix.", 3000)
            return False
        abs_user_dir = self._get_sequence_dir_path("user")
        os.makedirs(abs_user_dir, exist_ok=True)
        filepath = os.path.join(abs_user_dir, f"{filename_base}.json")
        if os.path.exists(filepath):
            # reply = QMessageBox.question(...) # Needs MW parent
            # For now, assume overwrite or unique name
            pass
        self.active_sequence_model.set_name(raw_name)
        if self.active_sequence_model.save_to_file(filepath):
            self.playback_status_update.emit(f"Sequence '{raw_name}' saved.", 2000)
            self.refresh_sequences_list_and_select(raw_name, "user")
            self._emit_state_updates()
            return True
        else:
            # QMessageBox.critical(self, "Save Error", f"Could not save to '{filepath}'.") # Needs MW parent
            self.playback_status_update.emit(f"Error saving sequence.", 3000)
            return False

    def _on_delete_selected_sequence_button_clicked(self):
        self.request_sampler_disable.emit()
        index = self.sequence_selection_combo.currentIndex()
        if index <= 0: # No valid item selected (index 0 is placeholder)
            self.playback_status_update.emit("No sequence selected to delete.", 2000)
            # print("AMW_DELETE_DEBUG: Exiting early - index <= 0") # Debug
            return
        item_data = self.sequence_selection_combo.itemData(index)
        display_name = self.sequence_selection_combo.itemText(index) 
        if not item_data or "path" not in item_data:
            self.playback_status_update.emit(f"Error: Could not get data for '{display_name}'.", 3000)
            # print(f"AMW_DELETE_DEBUG: Exiting early - no item_data or no path for '{display_name}'") # Debug
            self.refresh_sequences_list_and_select() 
            return
        sequence_type = item_data.get("type")
        if sequence_type not in ["user", "sampler"]:
            # print(f"AMW_DELETE_DEBUG: Attempt to delete non-user/sampler type: '{sequence_type}' for '{display_name}'") # Debug
            QMessageBox.warning(self, "Delete Error", 
                                f"Cannot delete '{display_name}'.\nOnly user-saved or sampler-recorded sequences can be deleted via this UI.")
            return
        print(f"AMW_DELETE_DEBUG: Preparing to show QMessageBox.question for '{display_name}', type: '{sequence_type}'")
        # --- Confirmation Dialog ---
        reply = QMessageBox.question(self, "Confirm Deletion",
                                    f"Are you sure you want to permanently delete the sequence:\n'{display_name}'?",
                                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                    QMessageBox.StandardButton.No) 
        if reply == QMessageBox.StandardButton.No:
            self.playback_status_update.emit(f"Deletion of '{display_name}' cancelled.", 1500)
            # print(f"AMW_DELETE_DEBUG: User cancelled deletion for '{display_name}'") # Debug
            return
        # --- End Confirmation Dialog ---
        # print(f"AMW_DELETE_DEBUG: User confirmed YES to delete '{display_name}'") # Debug
        filepath_to_delete = item_data["path"]
        try:
            if os.path.exists(filepath_to_delete):
                os.remove(filepath_to_delete)
                self.playback_status_update.emit(f"Sequence '{display_name}' deleted successfully.", 2000)
                if self.active_sequence_model and self.active_sequence_model.loaded_filepath and \
                    os.path.normpath(self.active_sequence_model.loaded_filepath) == os.path.normpath(filepath_to_delete):
                    # print(f"AMW_DELETE_DEBUG: Deleted active sequence, creating new.") # Debug
                    self.action_new_sequence(prompt_save=False) 
                self.refresh_sequences_list_and_select() 
            else:
                self.playback_status_update.emit(f"Error: File for '{display_name}' not found. Already deleted?", 3000)
                # print(f"AMW_DELETE_DEBUG: File not found for deletion: '{filepath_to_delete}'") # Debug
                self.refresh_sequences_list_and_select() 
        except Exception as e:
            # print(f"AMW_DELETE_DEBUG: Exception during deletion of '{filepath_to_delete}': {e}") # Debug
            QMessageBox.critical(self, "Delete Error", f"Could not delete sequence '{display_name}':\n{e}")
            self.playback_status_update.emit(f"Error deleting sequence: {e}", 4000)
        self._emit_state_updates()

    def set_overall_enabled_state(self, enabled: bool):
        """
        Called by MainWindow to enable/disable this entire animator panel.
        Now delegates to a more specific playback state handler if playback is active.
        """
        is_currently_playing = self.active_sequence_model.get_is_playing() if self.active_sequence_model else False
        if not enabled:
            # If the entire panel is being disabled from the outside, just disable it.
            self.setEnabled(False)
        else:
            # If it's being enabled, turn the widget on, then let the specific
            # playback handler fine-tune which sub-widgets are interactive.
            self.setEnabled(True)
            self.set_interactive_state_for_playback(is_currently_playing)
        """Called by MainWindow to enable/disable this entire animator panel."""
        self.setEnabled(enabled)
        if enabled:
            self._update_animator_controls_enabled_state() # Refresh internal states
            
    def export_current_sequence_as_gif(self, export_path: str, options: dict):
        """
        Renders the current animation sequence to an animated GIF file using the Pillow library.
        Args:
            export_path: The full path (including filename) to save the GIF to.
            options: A dictionary from GifExportDialog with 'pixel_size', 'spacing',
                    'delay', and 'loop' keys.
        """
        if not self.active_sequence_model or not self.active_sequence_model.frames:
            self.playback_status_update.emit("Cannot export: No frames in sequence.", 3000)
            return
        # Extract options with defaults
        pixel_size = options.get('pixel_size', 20)
        spacing = options.get('spacing', 2)
        delay_ms = options.get('delay', 100)
        loop = options.get('loop', 0)  # 0 for infinite loop
        # Constants for the grid
        GRID_COLS = 16
        GRID_ROWS = 4
        # Calculate the total size of one frame image
        frame_width = (GRID_COLS * pixel_size) + ((GRID_COLS - 1) * spacing)
        frame_height = (GRID_ROWS * pixel_size) + ((GRID_ROWS - 1) * spacing)
        # --- Main Rendering Loop ---
        try:
            pil_frames = []
            for i, frame_model in enumerate(self.active_sequence_model.frames):
                self.playback_status_update.emit(f"Rendering GIF frame {i+1}/{len(self.active_sequence_model.frames)}...", 0)
                QApplication.processEvents() # Keep UI responsive during render
                # Create a new blank image for this frame
                pil_image = Image.new('RGB', (frame_width, frame_height), color='#181818') # Use app bg color
                draw = ImageDraw.Draw(pil_image)
                frame_colors = frame_model.get_all_colors()
                # Iterate over each pad in the frame
                for pad_index, hex_color in enumerate(frame_colors):
                    row = pad_index // GRID_COLS
                    col = pad_index % GRID_COLS
                    # Calculate the top-left corner of the rectangle for this pad
                    x0 = col * (pixel_size + spacing)
                    y0 = row * (pixel_size + spacing)
                    x1 = x0 + pixel_size
                    y1 = y0 + pixel_size
                    # Draw the colored rectangle
                    draw.rectangle([x0, y0, x1, y1], fill=hex_color)
                
                pil_frames.append(pil_image)
            # Save the collected frames as an animated GIF
            if pil_frames:
                self.playback_status_update.emit("Saving GIF file...", 0)
                QApplication.processEvents()
                pil_frames[0].save(
                    export_path,
                    save_all=True,
                    append_images=pil_frames[1:],
                    duration=delay_ms,
                    loop=loop,
                    optimize=True # Use Pillow's optimization
                )
                self.playback_status_update.emit(f"Successfully exported GIF to {os.path.basename(export_path)}", 5000)
            else:
                self.playback_status_update.emit("Export failed: No frames were rendered.", 4000)
        except Exception as e:
            error_message = f"GIF export failed: {e}"
            print(f"ERROR: {error_message}")
            self.playback_status_update.emit(error_message, 8000)
            # Show a more detailed error dialog to the user
            QMessageBox.critical(self, "GIF Export Error", error_message)
        finally:
            # Clear any persistent status message
            QTimer.singleShot(5100, lambda: self.playback_status_update.emit("", 0))