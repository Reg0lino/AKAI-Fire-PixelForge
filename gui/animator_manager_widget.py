# AKAI_Fire_RGB_Controller/gui/animator_manager_widget.py
import os
import re
import json 
import glob 
import time 
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QApplication,
    QGroupBox, QComboBox, QSpacerItem, QMessageBox, QInputDialog, QSizePolicy, QFrame, QFileDialog, QLineEdit, QMenu
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
    request_gif_import_dialog = pyqtSignal()

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

    def __init__(self, user_sequences_base_path: str, sampler_recordings_path: str, prefab_sequences_base_path: str, parent=None):
        super().__init__(parent)
        self.user_sequences_base_path = user_sequences_base_path
        self.sampler_recordings_path = sampler_recordings_path
        self.prefab_sequences_base_path = prefab_sequences_base_path
        self.active_sequence_model: SequenceModel | None = None
        self._playback_timer = QTimer(self)
        self._clipboard: list[AnimationFrame] = []
        self.is_playing_override_for_ui = False
        self._last_emitted_is_modified = None
        self._last_emitted_sequence_name = None
        # This will hold {'name': 'path'} for all discovered sequences
        self.available_sequences: list[dict] = []
        # --- Instantiate Child Widgets ---
        self.sequence_controls_widget = SequenceControlsWidget(self)
        self.sequence_timeline_widget = SequenceTimelineWidget(self)
        # --- Correct Initialization Order ---
        self._init_ui()
        self._connect_signals()
        # --- Final Setup ---
        self._populate_sequence_dropdown()
        # Create an initial blank sequence instead of loading one from the dropdown
        self.create_new_sequence(prompt_save=False)

    def _init_ui(self):
        """Initializes the new two-row UI layout for the Animator Studio."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(5)
        # --- Main GroupBox Container ---
        top_bar_group = QGroupBox("Animator Studio")
        top_bar_container_layout = QVBoxLayout(top_bar_group) # Vertical layout for the two rows
        top_bar_container_layout.setContentsMargins(8, 4, 8, 8)
        top_bar_container_layout.setSpacing(8)
        # --- ROW 1: Sequence Selection and Loading ---
        row1_layout = QHBoxLayout()
        row1_layout.addWidget(QLabel("Sequence:"))
        self.sequence_selection_combo = QComboBox()
        self.sequence_selection_combo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.sequence_selection_combo.setToolTip("Select a sequence to load")
        row1_layout.addWidget(self.sequence_selection_combo)
        self.load_button = QPushButton("📂 Load")
        self.load_button.setToolTip("Load the selected sequence from the dropdown")
        row1_layout.addWidget(self.load_button)
        top_bar_container_layout.addLayout(row1_layout)
        # --- ROW 2: New, Save, Delete, and GIF Import ---
        row2_layout = QHBoxLayout()
        self.new_button = QPushButton("✨ New")
        self.new_button.setToolTip("Create a new, empty animation sequence (Ctrl+N)")
        row2_layout.addWidget(self.new_button)
        self.save_button = QPushButton("💾 Save As...")
        self.save_button.setToolTip("Save the current animation sequence to a file (Ctrl+Shift+S)")
        row2_layout.addWidget(self.save_button)
        self.delete_button = QPushButton("🗑️ Delete")
        self.delete_button.setToolTip("Delete the selected sequence from the disk")
        row2_layout.addWidget(self.delete_button)
        row2_layout.addStretch() # This pushes the GIF Import button to the right
        self.gif_import_button = QPushButton("📥 GIF Import")
        self.gif_import_button.setToolTip("Import an animated GIF as a new sequence")
        row2_layout.addWidget(self.gif_import_button)
        top_bar_container_layout.addLayout(row2_layout)
        # --- Add components to the main layout ---
        main_layout.addWidget(top_bar_group)
        main_layout.addWidget(self.sequence_timeline_widget)
        main_layout.addWidget(self.sequence_controls_widget)

    def _connect_signals(self):
        # Top Bar Buttons
        self.new_button.clicked.connect(lambda: self.create_new_sequence(prompt_save=True))
        self.load_button.clicked.connect(self._on_load_button_pressed)
        self.save_button.clicked.connect(self.action_save_sequence_as)
        self.delete_button.clicked.connect(self.action_delete_sequence)
        # The gif_import_button click is connected in MainWindow
        # Dropdown selection change - connected to the single, correct handler
        self.sequence_selection_combo.currentIndexChanged.connect(self._on_dropdown_selection_changed)
        # Timeline and Controls Widget signals (no changes here)
        self.sequence_timeline_widget.selection_changed.connect(self._on_timeline_selection_changed)
        self.sequence_timeline_widget.copy_frames_action_triggered.connect(self.action_copy_frames)
        self.sequence_timeline_widget.cut_frames_action_triggered.connect(self.action_cut_frames)
        self.sequence_timeline_widget.paste_frames_action_triggered.connect(self.action_paste_frames)
        self.sequence_timeline_widget.duplicate_selected_action_triggered.connect(self.action_duplicate_selected_frames)
        self.sequence_timeline_widget.delete_selected_action_triggered.connect(self.action_delete_selected_frames)
        self.sequence_timeline_widget.add_frame_action_triggered.connect(self.action_add_frame)
        self.sequence_timeline_widget.select_all_action_triggered.connect(self.action_select_all_frames)
        self.sequence_timeline_widget.insert_blank_frame_before_action_triggered.connect(self._handle_insert_blank_frame_before_request)
        self.sequence_timeline_widget.insert_blank_frame_after_action_triggered.connect(self._handle_insert_blank_frame_after_request)
        self.sequence_controls_widget.add_frame_requested.connect(self.action_add_frame)
        self.sequence_controls_widget.duplicate_selected_frame_requested.connect(self.action_duplicate_selected_frames)
        self.sequence_controls_widget.delete_selected_frame_requested.connect(self.action_delete_selected_frames)
        self.sequence_controls_widget.copy_frames_requested.connect(self.action_copy_frames)
        self.sequence_controls_widget.cut_frames_requested.connect(self.action_cut_frames)
        self.sequence_controls_widget.paste_frames_requested.connect(self.action_paste_frames)
        self.sequence_controls_widget.navigate_first_requested.connect(self.action_navigate_first)
        self.sequence_controls_widget.navigate_prev_requested.connect(self.action_navigate_prev)
        self.sequence_controls_widget.navigate_next_requested.connect(self.action_navigate_next)
        self.sequence_controls_widget.navigate_last_requested.connect(self.action_navigate_last)
        self.sequence_controls_widget.play_stop_clicked.connect(self.action_play_pause_toggle)
        self.sequence_controls_widget.frame_delay_changed.connect(self._on_frame_delay_changed)
        
        self._playback_timer.timeout.connect(self._on_playback_timer_tick)

    def _on_frame_delay_changed(self, delay_ms: int):
        """
        Handles the frame_delay_changed signal from the controls widget.
        Updates the active model and the playback timer if necessary.
        """
        if self.active_sequence_model:
            # Update the data model with the new delay
            self.active_sequence_model.set_frame_delay_ms(delay_ms)
            # If playback is active, update the timer's interval immediately
            if self.active_sequence_model.get_is_playing():
                self._playback_timer.setInterval(delay_ms)

    def _on_playback_timer_tick(self):
        """
        The main playback loop handler. Called by the QTimer on every frame step.
        """
        if not self.active_sequence_model or not self.active_sequence_model.get_is_playing():
            # Safety check: if playback stopped unexpectedly, ensure the timer is also stopped.
            self._playback_timer.stop()
            return
        # Ask the model for the next frame's data and advance its internal counter.
        colors = self.active_sequence_model.step_and_get_playback_frame_colors()
        if colors:
            # Send the new frame's colors to MainWindow to display on the hardware/GUI grid.
            self.active_frame_data_for_display.emit(colors)
            # Update the visual indicator on the timeline widget.
            playback_idx = self.active_sequence_model.get_current_playback_frame_index()
            edit_idx = self.active_sequence_model.get_current_edit_frame_index()
            self.sequence_timeline_widget.update_delegate_visual_state(edit_idx, playback_idx)
        # Check if the model has stopped playback (e.g., end of a non-looping sequence).
        if not self.active_sequence_model.get_is_playing():
            # Call the model's stop method to finalize the state and emit the necessary signals.
            self.active_sequence_model.stop_playback()

    def add_extra_button(self, button: QPushButton):
        """Adds an external button (like GIF Import) to the buttons layout."""
        if self.buttons_layout:  # This is the QHBoxLayout holding Load/Save/Delete
            # Add it to the end of the existing buttons layout
            self.buttons_layout.addWidget(button)
            # Remove any stretch that might be at the end of the button layout
            # to make sure the new button doesn't get pushed too far.
            for i in reversed(range(self.buttons_layout.count())):
                item = self.buttons_layout.itemAt(i)
                if isinstance(item, QSpacerItem):
                    self.buttons_layout.removeItem(item)
            self.buttons_layout.addStretch(1)  # Re-add stretch at the end

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

    def import_sequence_from_gif_data(self, frames: list, delay_ms: int, name: str):
        """
        Receives processed GIF data, creates a new sequence model, and loads it.
        This method handles the unsaved changes prompt for the current sequence.
        """
        def _load_new_gif_sequence():
            """Helper function to perform the actual model creation and loading."""
            new_sequence = SequenceModel(name=name)
            new_sequence.frames = frames
            new_sequence.set_frame_delay_ms(delay_ms)
            new_sequence.is_modified = True
            
            self._set_active_sequence_model(new_sequence)
            
            # Manually trigger selection of the first frame
            if new_sequence.get_frame_count() > 0:
                self.active_sequence_model.set_current_edit_frame_index(0)
            
            print(f"AnimatorManager: Successfully imported and loaded GIF sequence '{name}' with {len(frames)} frames.")
        if self._is_current_sequence_worth_saving():
            self._handle_save_prompt(on_confirm_or_discard=_load_new_gif_sequence)
        else:
            _load_new_gif_sequence()

    def _handle_insert_blank_frame_before_request(self, index: int):
        """Handles context menu action to insert a blank frame before the specified index."""
        if not self.active_sequence_model:
            return
        # The model's add_blank_frame method handles the insertion and returns the new index
        new_index = self.active_sequence_model.add_blank_frame(at_index=index)
        # The model emits frames_changed, which triggers _update_ui_for_current_sequence.
        # We just need to ensure the new frame is selected.
        self.sequence_timeline_widget.select_items_by_indices([new_index])

    def _handle_insert_blank_frame_after_request(self, index: int):
        """Handles context menu action to insert a blank frame after the specified index."""
        if not self.active_sequence_model:
            return
        # Insert at index + 1
        new_index = self.active_sequence_model.add_blank_frame(at_index=index + 1)
        self.sequence_timeline_widget.select_items_by_indices([new_index])

    def set_active_sequence_model(self, model: SequenceModel | None):
        """
        Sets the active sequence model and updates the UI accordingly.
        This is a central method for managing the currently loaded animation.
        """
        print(f"AMW DEBUG: set_active_sequence_model called for: {model.name if model else 'None'}") # For debugging
        # Stop any active playback if a new model is being set
        if self.active_sequence_model and self.active_sequence_model.get_is_playing():
            self.action_stop() # This will stop playback cleanly
        self.active_sequence_model = model
        
        if self.active_sequence_model:
            # Connect the model's signals to the UI manager for updates
            self.active_sequence_model.frame_data_changed.connect(self._on_frame_data_changed)
            self.active_sequence_model.frame_added_or_removed.connect(self._on_frame_count_changed)
            self.active_sequence_model.playback_position_changed.connect(self._on_playback_position_changed)
            self.active_sequence_model.current_edit_frame_changed.connect(self._on_current_edit_frame_changed)
            self.active_sequence_model.sequence_modified_status_changed.connect(self.sequence_modified_status_changed)
            # Update UI to reflect the new sequence
            self.sequence_title_label.setText(self.active_sequence_model.name)
            self.sequence_timeline_widget.set_sequence_model(self.active_sequence_model)
            # Set timeline to the current edit frame, ensuring UI updates
            self.sequence_timeline_widget.set_current_edit_frame_index(self.active_sequence_model.get_current_edit_frame_index())
            # Update undo/redo state for new sequence
            self._update_undo_redo_actions_state()
            # Initial frame display for the new sequence
            current_edit_index = self.active_sequence_model.get_current_edit_frame_index()
            colors = self.active_sequence_model.get_frame_colors(current_edit_index)
            self.active_frame_data_for_display.emit(colors) # Emit to MainWindow for display
            # Update save button state
            self.save_button.setEnabled(True)
        else:
            # No active sequence: reset UI
            self.sequence_title_label.setText("--- Select Sequence ---")
            self.sequence_timeline_widget.clear_sequence()
            self.active_frame_data_for_display.emit([QColor("black").name()] * 64) # Clear pads
            self.new_button.setEnabled(True)
            self.save_button.setEnabled(False)
            self.delete_button.setEnabled(False)
            self._update_undo_redo_actions_state() # Disable undo/redo
        # Update button enabled states based on new sequence model
        self._update_button_enabled_states() # Centralized button state update

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
        """
        Returns the number of items available for hardware navigation.
        This is the number of actual sequences in the dropdown, excluding the placeholder.
        """
        # The number of navigable items is the total count minus the placeholder item.
        count = self.sequence_selection_combo.count()
        return count - 1 if count > 0 else 0

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

    def set_navigation_current_item_by_logical_index(self, index: int) -> str | None:
        """
        Sets the dropdown's selected item by a 0-based logical index for hardware navigation.
        """
        navigable_item_count = self.get_navigation_item_count()
        if not (0 <= index < navigable_item_count):
            return None
        # The actual QComboBox index is the logical index + 1 (to skip the placeholder)
        combo_box_index = index + 1
        self.sequence_selection_combo.setCurrentIndex(combo_box_index)
        # Return the clean text for the OLED display
        display_text = self.sequence_selection_combo.itemText(combo_box_index)
        for prefix in ["[User] ", "[Sampler] ", "[Prefab] "]:
            if display_text.startswith(prefix):
                display_text = display_text[len(prefix):]
                break
        return display_text

    def trigger_navigation_current_item_action(self):
        """
        Handles the press action of the hardware SELECT knob. This simulates
        a click on the "Load" button for the currently selected sequence.
        """
        self._on_load_button_pressed()

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
        """
        Updates the enabled state of all buttons and controls based on the current
        model state and playback status.
        """
        # Determine the current state
        has_model = self.active_sequence_model is not None
        has_frames = has_model and self.active_sequence_model.get_frame_count() > 0
        has_selection = has_frames and bool(self.sequence_timeline_widget.get_selected_item_indices())
        has_clipboard = bool(self._clipboard)
        is_playing = self.is_playing_override_for_ui
        can_edit = self.isEnabled() and not is_playing
        # --- Update Top Bar Buttons ---
        self.new_button.setEnabled(can_edit)
        self.load_button.setEnabled(can_edit)
        self.save_button.setEnabled(can_edit and has_frames)
        self.gif_import_button.setEnabled(can_edit)
        self.delete_button.setEnabled(can_edit)
        # --- Update the child controls widget ---
        self.sequence_controls_widget.set_controls_enabled_state(
            enabled=can_edit,
            frame_selected=has_selection,
            has_frames=has_frames,
            clipboard_has_content=has_clipboard
        )
        self.sequence_controls_widget.play_stop_button.setEnabled(has_frames and self.isEnabled())

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

    def refresh_sequences_list_and_select(self, active_seq_raw_name: str | None = None, active_seq_type_id: str | None = None):
        """
        Refreshes the entire sequence list from the filesystem and attempts to re-select
        the specified sequence. This is the new, consolidated version.
        """
        # Block signals to prevent premature triggers
        self.sequence_selection_combo.blockSignals(True)
        # Repopulate the entire list
        self._populate_sequence_dropdown()
        # Now, try to find and select the correct item
        target_idx = 0 # Default to "--- Select Sequence ---"
        if active_seq_raw_name and active_seq_type_id:
            # Construct the full display name to search for, e.g., "[User] My Sequence"
            prefix_map = {"User": "[User] ", "Sampler": "[Sampler] ", "Prefab": "[Prefab] "}
            prefix = prefix_map.get(active_seq_type_id, "")
            text_to_find = f"{prefix}{active_seq_raw_name}"
            # Use findText to locate the item
            found_idx = self.sequence_selection_combo.findText(text_to_find, Qt.MatchFlag.MatchFixedString)
            if found_idx != -1:
                target_idx = found_idx
        # Set the final index
        self.sequence_selection_combo.setCurrentIndex(target_idx)
        # Unblock signals and manually call the handler for the new state
        self.sequence_selection_combo.blockSignals(False)
        self._on_dropdown_selection_changed(target_idx)

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
        """Creates a new, blank sequence, prompting to save the current one if modified."""
        def _create():
            """The actual creation logic, called after any prompts."""
            new_model = SequenceModel()
            new_model.add_blank_frame()
            # Use the new master method to safely set the active sequence
            self._set_active_sequence_model(new_model)
        # Check if the current sequence is modified and worth saving
        if prompt_save and self._is_current_sequence_worth_saving():
            # The save prompt will call the `_create` function if the user proceeds
            self._handle_save_prompt(on_confirm_or_discard=_create)
        else:
            # If no save is needed, just create the new sequence directly
            _create()

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

    def action_new_sequence(self, prompt_save=True):
        """
        Public action called by UI buttons or MainWindow to create a new sequence.
        The 'prompt_save' argument allows MainWindow to handle the prompt centrally.
        """
        self.request_sampler_disable.emit()
        self.create_new_sequence(prompt_save=prompt_save)

    def action_load_sequence(self):
        """
        Handles the "Load" button click. Opens a file dialog and, if a file is
        selected, it initiates the loading process which includes handling
        any unsaved changes in the current sequence.
        """
        # Start the file dialog in the user's saved sequences directory
        filepath, _ = QFileDialog.getOpenFileName(
            self, 
            "Load Animation Sequence",
            self.user_sequences_base_path,
            "JSON Files (*.json)"
        )
        if filepath:
            # Don't load directly. Call the helper that handles the "Save Changes?" prompt.
            self._handle_load_sequence_request(filepath)

    def _set_active_sequence_model(self, model: SequenceModel | None):
        """
        Safely sets a new SequenceModel as the active one.
        This is the single entry point for changing the animator's sequence,
        ensuring old signals are disconnected and new ones are connected.
        """
        # --- Stop any active processes related to the OLD model ---
        if self.active_sequence_model:
            # Stop playback if it's running
            if self.active_sequence_model.get_is_playing():
                self.active_sequence_model.stop_playback()
            # Disconnect all signals from the old model to prevent memory leaks
            try:
                self.active_sequence_model.frame_content_updated.disconnect(self._on_model_frame_content_updated)
                self.active_sequence_model.current_edit_frame_changed.disconnect(self._on_model_edit_frame_changed)
                self.active_sequence_model.playback_state_changed.disconnect(self._on_model_playback_state_changed)
                self.active_sequence_model.properties_changed.disconnect(self._on_model_properties_changed)
                self.active_sequence_model.frames_changed.disconnect(self._on_model_frames_changed)
            except (TypeError, RuntimeError):
                pass  # Ignore errors if signals were not connected or object is gone
        # --- Assign the NEW model ---
        self.active_sequence_model = model
        # --- Configure for the NEW model ---
        if self.active_sequence_model:
            # Connect signals from the new model
            self.active_sequence_model.frame_content_updated.connect(self._on_model_frame_content_updated)
            self.active_sequence_model.current_edit_frame_changed.connect(self._on_model_edit_frame_changed)
            self.active_sequence_model.playback_state_changed.connect(self._on_model_playback_state_changed)
            self.active_sequence_model.properties_changed.connect(self._on_model_properties_changed)
            self.active_sequence_model.frames_changed.connect(self._on_model_frames_changed)
        # --- Update the entire UI to reflect the new state ---
        self._update_ui_for_current_sequence()

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

    def _on_model_frame_content_updated(self, frame_index: int):
        """Handles when a single frame's content changes in the model."""
        if not self.active_sequence_model: return
        colors = self.active_sequence_model.get_frame_colors(frame_index)
        if colors:
            self.sequence_timeline_widget.update_single_frame_thumbnail_data(frame_index, colors)
            if frame_index == self.active_sequence_model.get_current_edit_frame_index():
                self.active_frame_data_for_display.emit(colors)
        self._emit_state_updates()

    def _on_model_edit_frame_changed(self, new_edit_index: int):
        """Handles when the model's 'current edit frame' pointer changes."""
        self.sequence_timeline_widget.select_items_by_indices([new_edit_index] if new_edit_index != -1 else [])
        self.sequence_timeline_widget.update_delegate_visual_state(new_edit_index, -1)
        if self.active_sequence_model:
            frame_colors = self.active_sequence_model.get_frame_colors(new_edit_index)
            self.active_frame_data_for_display.emit(frame_colors if frame_colors else [])
        self._update_animator_controls_enabled_state()

    def _on_model_playback_state_changed(self, is_playing: bool):
        """Handles when the model's playback state (playing/paused/stopped) changes."""
        self.is_playing_override_for_ui = is_playing
        self.sequence_controls_widget.update_playback_button_state(is_playing)
        if is_playing and self.active_sequence_model:
            self._playback_timer.start(self.active_sequence_model.frame_delay_ms)
            self.playback_status_update.emit("Playback Started...", 2000)
        else:
            self._playback_timer.stop()
            self.playback_status_update.emit("Playback Stopped.", 2000)
            # When playback stops, revert display to the edit frame
            if self.active_sequence_model:
                self._on_model_edit_frame_changed(self.active_sequence_model.get_current_edit_frame_index())
        self._update_ui_for_current_sequence()

    def _on_model_properties_changed(self):
        """Handles when model properties like name or delay change."""
        self._update_ui_for_current_sequence()

    def _on_model_frames_changed(self):
        """Handles when the entire list of frames changes (e.g., after undo, paste, delete)."""
        self._update_ui_for_current_sequence()

    def _populate_sequence_dropdown(self):
        """Scans sequence directories and populates the dropdown."""
        self.sequence_selection_combo.blockSignals(True)
        self.sequence_selection_combo.clear()
        self.available_sequences.clear()
        # Add a placeholder first
        self.sequence_selection_combo.addItem(
            "--- Select Sequence ---", userData=None)
        # Scan directories
        for category, path in [("[User]", self.user_sequences_base_path), ("[Sampler]", self.sampler_recordings_path), ("[Prefab]", self.prefab_sequences_base_path)]:
            if not os.path.isdir(path):
                continue
            # Add a non-selectable separator for categories
            # self.sequence_selection_combo.insertSeparator(self.sequence_selection_combo.count())
            for file in sorted(os.listdir(path)):
                if file.lower().endswith(".json"):
                    filepath = os.path.join(path, file)
                    try:
                        with open(filepath, 'r') as f:
                            data = json.load(f)
                        seq_name = data.get("name", os.path.splitext(file)[0])
                        display_name = f"{category} {seq_name}"
                        item_data = {
                            'name': display_name, 'path': filepath, 'category': category.strip("[]")}
                        self.available_sequences.append(item_data)
                        self.sequence_selection_combo.addItem(
                            display_name, userData=item_data)
                    except (json.JSONDecodeError, KeyError):
                        print(
                            f"Warning: Could not read sequence name from {file}")
        self.sequence_selection_combo.blockSignals(False)

    def _on_load_button_pressed(self):
        """Handles the 'Load' button click, loading the selected sequence from the dropdown."""
        current_data = self.sequence_selection_combo.currentData()
        if current_data and 'path' in current_data:
            filepath_to_load = current_data['path']
            # Delegate to the method that handles the unsaved changes prompt
            self._handle_load_sequence_request(filepath_to_load)
        else:
            self.playback_status_update.emit(
                "Please select a sequence from the dropdown to load.", 2000)

    def _handle_save_prompt(self, on_confirm_or_discard=None):
        """
        Shows the 'Save Changes?' dialog for the current sequence.
        Executes the on_confirm_or_discard callback if the user chooses to proceed (Save/Discard).
        """
        if not self.active_sequence_model:
            if on_confirm_or_discard:
                on_confirm_or_discard()
            return
        reply = QMessageBox.question(self, "Unsaved Changes",
                                    f"Sequence '{self.active_sequence_model.name}' has unsaved changes. Save now?",
                                    QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel,
                                    QMessageBox.StandardButton.Cancel)
        if reply == QMessageBox.StandardButton.Save:
            # action_save_sequence_as returns True on success, False on cancel
            if self.action_save_sequence_as():
                if on_confirm_or_discard:
                    on_confirm_or_discard()
        elif reply == QMessageBox.StandardButton.Discard:
            if on_confirm_or_discard:
                on_confirm_or_discard()
        # If user clicks Cancel, the on_confirm_or_discard callback is not executed.

    def refresh_display(self):
        """
        Forces a refresh of the main pad grid display based on the
        currently selected edit frame in the active model.
        """
        if not self.active_sequence_model:
            # If no model, emit empty colors to clear the grid
            self.active_frame_data_for_display.emit(['#000000'] * 64)
            return
        edit_idx = self.active_sequence_model.get_current_edit_frame_index()
        colors = self.active_sequence_model.get_frame_colors(edit_idx)
        # Emit the colors of the current frame to be displayed
        self.active_frame_data_for_display.emit(colors if colors else ['#000000'] * 64)

    def action_delete_sequence(self):
        """Handles deleting the currently selected sequence file."""
        current_data = self.sequence_selection_combo.currentData()
        if not (current_data and current_data.get('category') == "User"):
            QMessageBox.warning(
                self, "Delete Error", "Only sequences in the '[User]' category can be deleted.")
            return
        filepath_to_delete = current_data['path']
        seq_name = os.path.basename(filepath_to_delete)
        reply = QMessageBox.question(self, "Confirm Delete",
                                    f"Are you sure you want to permanently delete the file?\n\n<b>{seq_name}</b>\n\nThis action cannot be undone.",
                                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                    QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            try:
                os.remove(filepath_to_delete)
                self.playback_status_update.emit(
                    f"Deleted sequence: {seq_name}", 3000)
                # If the deleted sequence was the one currently loaded, create a new blank one
                if self.active_sequence_model and self.active_sequence_model.loaded_filepath == filepath_to_delete:
                    self.create_new_sequence(prompt_save=False)
                # Refresh the dropdown list
                self._populate_sequence_dropdown()
            except OSError as e:
                QMessageBox.critical(self, "Delete Failed",
                                    f"Could not delete file:\n{e}")

    def _on_dropdown_selection_changed(self, index: int):
        """
        Handles the currentIndexChanged signal from the sequence dropdown.
        Enables/disables the Load and Delete buttons based on the selection.
        This is the single source of truth for this widget's state.
        """
        is_loadable = index > 0  # Anything other than the "--- Select ---" placeholder
        self.load_button.setEnabled(is_loadable)
        current_data = self.sequence_selection_combo.currentData()
        # The 'category' key is added by our new _populate_sequence_dropdown method
        is_deletable = is_loadable and current_data and current_data.get('category') in ["User", "Sampler"]
        self.delete_button.setEnabled(is_deletable)

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