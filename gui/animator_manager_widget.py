# AKAI_Fire_RGB_Controller/gui/animator_manager_widget.py
import os
import re
import json 
import glob 
import time 
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QGroupBox, QComboBox, QSpacerItem, QMessageBox, QInputDialog, QSizePolicy, QFrame
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QColor

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


class AnimatorManagerWidget(QWidget):
    # Signals to MainWindow
    active_frame_data_for_display = pyqtSignal(list)
    playback_status_update = pyqtSignal(str, int)
    sequence_modified_status_changed = pyqtSignal(bool, str)
    undo_redo_state_changed = pyqtSignal(bool, bool)  # can_undo, can_redo
    clipboard_state_changed = pyqtSignal(bool)
    animator_playback_active_status_changed = pyqtSignal(bool)
    request_load_sequence_with_prompt = pyqtSignal(str)

    request_sampler_disable = pyqtSignal()

    def __init__(self,
                 user_sequences_base_path: str,
                 sampler_recordings_path: str,
                 prefab_sequences_base_path: str,
                 parent: QWidget | None = None):
        super().__init__(parent)
        self.user_sequences_path = user_sequences_base_path
        self.sampler_recordings_path = sampler_recordings_path
        self.prefab_sequences_path = prefab_sequences_base_path

        self.active_sequence_model = SequenceModel()
        self._connect_signals_for_active_sequence_model()

        self.playback_timer = QTimer(self)
        self.playback_timer.timeout.connect(self.advance_and_play_next_frame)

        self.frame_clipboard: list[AnimationFrame] = []

        self.animator_studio_group_box: QGroupBox | None = None
        self.sequence_selection_combo: QComboBox | None = None
        self.load_sequence_button: QPushButton | None = None
        self.new_sequence_button: QPushButton | None = None
        self.save_sequence_as_button: QPushButton | None = None
        self.delete_sequence_button: QPushButton | None = None
        self.sequence_timeline_widget: SequenceTimelineWidget | None = None
        self.sequence_controls_widget: SequenceControlsWidget | None = None

        self._last_emitted_is_modified: bool | None = None
        self._last_emitted_sequence_name: str | None = None

        self._init_ui()
        self._connect_ui_signals()

        QTimer.singleShot(0, self.refresh_sequences_list_and_select)
        QTimer.singleShot(0, self._update_ui_for_current_sequence)

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(10)

        self.animator_studio_group_box = QGroupBox("🎬 Animator Studio")
        self.animator_studio_group_box.setSizePolicy(
            QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        animator_studio_layout = QVBoxLayout(self.animator_studio_group_box)

        combo_load_layout = QHBoxLayout()
        combo_load_layout.addWidget(QLabel("Sequence:"))
        self.sequence_selection_combo = QComboBox()
        self.sequence_selection_combo.setPlaceholderText(
            "--- Select Sequence ---")
        combo_load_layout.addWidget(self.sequence_selection_combo, 1)
        self.load_sequence_button = QPushButton("🗀 Load")
        combo_load_layout.addWidget(self.load_sequence_button)
        animator_studio_layout.addLayout(combo_load_layout)

        action_buttons_layout = QHBoxLayout()
        self.new_sequence_button = QPushButton("✚ New")
        action_buttons_layout.addWidget(self.new_sequence_button)
        self.save_sequence_as_button = QPushButton("💾 Save As...")
        action_buttons_layout.addWidget(self.save_sequence_as_button)
        self.delete_sequence_button = QPushButton("☠ Delete")
        action_buttons_layout.addWidget(self.delete_sequence_button)
        action_buttons_layout.addSpacerItem(QSpacerItem(
            10, 0, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))
        animator_studio_layout.addLayout(action_buttons_layout)
        main_layout.addWidget(self.animator_studio_group_box)

        separator_line = QFrame()
        separator_line.setFrameShape(QFrame.Shape.HLine)
        separator_line.setFrameShadow(QFrame.Shadow.Sunken)
        main_layout.addWidget(separator_line)

        self.sequence_timeline_widget = SequenceTimelineWidget()
        self.sequence_timeline_widget.setSizePolicy(
            QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
        desired_min_timeline_height = 120
        self.sequence_timeline_widget.setMinimumHeight(
            desired_min_timeline_height)
        main_layout.addWidget(self.sequence_timeline_widget)

        self.sequence_controls_widget = SequenceControlsWidget()
        self.sequence_controls_widget.setSizePolicy(
            QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        main_layout.addWidget(self.sequence_controls_widget)

        self.setSizePolicy(QSizePolicy.Policy.Preferred,
                           QSizePolicy.Policy.Expanding)

    def _connect_ui_signals(self):
        self.sequence_selection_combo.currentIndexChanged.connect(
            self._on_sequence_combo_changed)
        self.load_sequence_button.clicked.connect(
            self._request_load_selected_sequence_from_main)
        self.new_sequence_button.clicked.connect(
            lambda: self.action_new_sequence(prompt_save=True))
        self.save_sequence_as_button.clicked.connect(
            self.action_save_sequence_as)
        self.delete_sequence_button.clicked.connect(
            self._on_delete_selected_sequence_button_clicked)

        self.sequence_controls_widget.add_frame_requested.connect(
            self.action_add_frame)
        self.sequence_controls_widget.delete_selected_frame_requested.connect(
            self.action_delete_selected_frames)
        self.sequence_controls_widget.duplicate_selected_frame_requested.connect(
            self.action_duplicate_selected_frames)
        self.sequence_controls_widget.copy_frames_requested.connect(
            self.action_copy_frames)
        self.sequence_controls_widget.cut_frames_requested.connect(
            self.action_cut_frames)
        self.sequence_controls_widget.paste_frames_requested.connect(
            self.action_paste_frames)
        self.sequence_controls_widget.undo_requested.connect(
            self.action_undo)  # <<< CONNECT NEW
        self.sequence_controls_widget.redo_requested.connect(
            self.action_redo)  # <<< CONNECT NEW
        self.sequence_controls_widget.navigate_first_requested.connect(
            self.action_navigate_first)
        self.sequence_controls_widget.navigate_prev_requested.connect(
            self.action_navigate_prev)
        self.sequence_controls_widget.navigate_next_requested.connect(
            self.action_navigate_next)
        self.sequence_controls_widget.navigate_last_requested.connect(
            self.action_navigate_last)
        self.sequence_controls_widget.play_requested.connect(self.action_play)
        self.sequence_controls_widget.pause_requested.connect(
            self.action_pause)
        self.sequence_controls_widget.stop_requested.connect(self.action_stop)
        self.sequence_controls_widget.frame_delay_changed.connect(
            self.on_controls_frame_delay_changed)

        self.sequence_timeline_widget.add_frame_action_triggered.connect(
            self.on_timeline_add_frame_action)
        self.sequence_timeline_widget.frame_selected.connect(
            self.on_timeline_frame_selected)
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
        self.sequence_timeline_widget.insert_blank_frame_before_action_triggered.connect(
            lambda index: self.action_add_frame("blank", at_index=index)
        )
        self.sequence_timeline_widget.insert_blank_frame_after_action_triggered.connect(
            lambda index: self.action_add_frame("blank", at_index=index + 1)
        )

    def _connect_signals_for_active_sequence_model(self):
        try:
            self.active_sequence_model.frames_changed.disconnect()
        except TypeError:
            pass
        try:
            self.active_sequence_model.frame_content_updated.disconnect()
        except TypeError:
            pass
        try:
            self.active_sequence_model.current_edit_frame_changed.disconnect()
        except TypeError:
            pass
        try:
            self.active_sequence_model.properties_changed.disconnect()
        except TypeError:
            pass
        try:
            self.active_sequence_model.playback_state_changed.disconnect()
        except TypeError:
            pass

        self.active_sequence_model.frames_changed.connect(
            self._update_ui_for_current_sequence)
        self.active_sequence_model.frame_content_updated.connect(
            self.on_model_frame_content_updated)
        self.active_sequence_model.current_edit_frame_changed.connect(
            self.on_model_edit_frame_changed)
        self.active_sequence_model.properties_changed.connect(
            self._update_ui_for_current_sequence_properties)
        self.active_sequence_model.playback_state_changed.connect(
            self.on_model_playback_state_changed)

    def _emit_state_updates(self):
        current_is_modified = self.active_sequence_model.is_modified
        current_sequence_name = self.active_sequence_model.name

        if (current_is_modified != self._last_emitted_is_modified) or \
           (current_sequence_name != self._last_emitted_sequence_name):
            self.sequence_modified_status_changed.emit(
                current_is_modified, current_sequence_name)
            self._last_emitted_is_modified = current_is_modified
            self._last_emitted_sequence_name = current_sequence_name

        can_undo = bool(self.active_sequence_model._undo_stack)
        can_redo = bool(self.active_sequence_model._redo_stack)
        self.undo_redo_state_changed.emit(can_undo, can_redo)
        self.clipboard_state_changed.emit(bool(self.frame_clipboard))
        self._update_animator_controls_enabled_state(
            can_undo, can_redo)  # Pass new states

    def on_paint_stroke_started(self, row: int, col: int, mouse_button: Qt.MouseButton):
        if self.active_sequence_model and hasattr(self.active_sequence_model, 'begin_paint_stroke'):
            self.active_sequence_model.begin_paint_stroke()

    def on_paint_stroke_ended(self, mouse_button: Qt.MouseButton):
        if self.active_sequence_model and hasattr(self.active_sequence_model, 'end_paint_stroke'):
            self.active_sequence_model.end_paint_stroke()

    def get_current_sequence_fps(self) -> float:
        if self.active_sequence_model and self.active_sequence_model.frame_delay_ms > 0:
            return 1000.0 / self.active_sequence_model.frame_delay_ms
        elif self.active_sequence_model and self.active_sequence_model.frame_delay_ms == 0:
            return 60.0
        if hasattr(self, 'sequence_controls_widget') and self.sequence_controls_widget:
            initial_delay_ms = self.sequence_controls_widget.get_current_delay_ms()
            if initial_delay_ms > 0:
                return 1000.0 / initial_delay_ms
        return 10.0

    def set_playback_fps(self, fps: float):
        if not self.active_sequence_model:
            return
        min_fps = 0.1
        max_fps = 100.0
        clamped_fps = max(min_fps, min(fps, max_fps))
        new_delay_ms = int(round(1000.0 / clamped_fps)
                           ) if clamped_fps > 0 else 1000
        actual_delay_ms = max(10, new_delay_ms)
        self.active_sequence_model.set_frame_delay_ms(actual_delay_ms)
        if self.playback_timer.isActive():
            self.playback_timer.start(actual_delay_ms)
        if hasattr(self, 'sequence_controls_widget') and self.sequence_controls_widget:
            self.sequence_controls_widget.set_frame_delay_ui(actual_delay_ms)
        self._emit_state_updates()

    def get_navigation_item_count(self) -> int:
        if self.sequence_selection_combo:
            count = 0
            for i in range(self.sequence_selection_combo.count()):
                if self.sequence_selection_combo.itemData(i) is not None:
                    count += 1
            return count
        return 0

    def get_navigation_item_text_at_logical_index(self, logical_index: int) -> str | None:
        if self.sequence_selection_combo:
            actual_combo_index = -1
            current_logical_idx = -1
            for i in range(self.sequence_selection_combo.count()):
                if self.sequence_selection_combo.itemData(i) is not None:
                    current_logical_idx += 1
                    if current_logical_idx == logical_index:
                        actual_combo_index = i
                        break
            if actual_combo_index != -1:
                return self.sequence_selection_combo.itemText(actual_combo_index)
        return None

    def set_navigation_current_item_by_logical_index(self, logical_index: int) -> str | None:
        if self.sequence_selection_combo:
            actual_combo_index_to_set = -1
            current_logical_idx = -1
            for i in range(self.sequence_selection_combo.count()):
                if self.sequence_selection_combo.itemData(i) is not None:
                    current_logical_idx += 1
                    if current_logical_idx == logical_index:
                        actual_combo_index_to_set = i
                        break
            if actual_combo_index_to_set != -1:
                current_gui_index = self.sequence_selection_combo.currentIndex()
                if current_gui_index != actual_combo_index_to_set:
                    self.sequence_selection_combo.setCurrentIndex(
                        actual_combo_index_to_set)
                return self.sequence_selection_combo.itemText(actual_combo_index_to_set)
        return None

    def trigger_navigation_current_item_action(self):
        self._request_load_selected_sequence_from_main()

    def action_undo(self):
        self.request_sampler_disable.emit()
        if self.active_sequence_model.undo():
            self.playback_status_update.emit("Undo.", 1500)
        else:
            self.playback_status_update.emit("Nothing to undo.", 1500)
        self._emit_state_updates()  # Will update button states

    def action_redo(self):
        self.request_sampler_disable.emit()
        if self.active_sequence_model.redo():
            self.playback_status_update.emit("Redo.", 1500)
        else:
            self.playback_status_update.emit("Nothing to redo.", 1500)
        self._emit_state_updates()  # Will update button states

    def action_copy_frames(self):
        self.request_sampler_disable.emit()
        selected_indices = self.sequence_timeline_widget.get_selected_item_indices()
        if not selected_indices:
            self.playback_status_update.emit(
                "No frames selected to copy.", 2000)
            return
        self.frame_clipboard.clear()
        copied_frames_count = 0
        for index in sorted(selected_indices):
            frame_obj = self.active_sequence_model.get_frame_object(index)
            if frame_obj:
                self.frame_clipboard.append(AnimationFrame(
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
        self.frame_clipboard.clear()
        copied_frames_count = 0
        for index in sorted(selected_indices):
            frame_obj = self.active_sequence_model.get_frame_object(index)
            if frame_obj:
                self.frame_clipboard.append(AnimationFrame(
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
            self.frame_clipboard.clear()
            self.playback_status_update.emit("Error cutting frames.", 3000)
        self._emit_state_updates()

    def action_paste_frames(self):
        self.request_sampler_disable.emit()
        self.stop_current_animation_playback()
        if not self.frame_clipboard:
            self.playback_status_update.emit("Clipboard is empty.", 2000)
            return
        selected_indices = self.sequence_timeline_widget.get_selected_item_indices()
        insertion_index = max(selected_indices) + 1 if selected_indices else \
            (self.active_sequence_model.get_current_edit_frame_index() + 1
             if self.active_sequence_model.get_current_edit_frame_index() != -1
             else self.active_sequence_model.get_frame_count())
        pasted_indices = self.active_sequence_model.paste_frames(
            self.frame_clipboard, at_index=insertion_index)
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
            self.playback_status_update.emit(
                "No frames selected to duplicate.", 1500)
            return
        newly_created_indices = self.active_sequence_model.duplicate_frames_at_indices(
            selected_indices)
        if newly_created_indices:
            self.playback_status_update.emit(
                f"{len(newly_created_indices)} frame(s) duplicated.", 1500)
            QTimer.singleShot(0, lambda: self.sequence_timeline_widget.select_items_by_indices(
                newly_created_indices))
        else:
            self.playback_status_update.emit("Duplication failed.", 1500)

    def action_delete_selected_frames(self):
        self.request_sampler_disable.emit()
        self.stop_current_animation_playback()
        selected_indices = self.sequence_timeline_widget.get_selected_item_indices()
        if not selected_indices:
            self.playback_status_update.emit(
                "No frames selected to delete.", 1500)
            return
        if self.active_sequence_model.delete_frames_at_indices(selected_indices):
            self.playback_status_update.emit(
                f"{len(selected_indices)} frame(s) deleted.", 1500)
        else:
            self.playback_status_update.emit("Deletion failed.", 1500)

    def action_select_all_frames(self):
        self.request_sampler_disable.emit()
        if self.active_sequence_model.get_frame_count() > 0:
            all_indices = list(
                range(self.active_sequence_model.get_frame_count()))
            self.sequence_timeline_widget.select_items_by_indices(all_indices)
            self.playback_status_update.emit(
                f"All {len(all_indices)} frames selected.", 1500)
        else:
            self.playback_status_update.emit("No frames to select.", 1500)
        self._update_animator_controls_enabled_state()

    def action_play_pause_toggle(self):
        self.request_sampler_disable.emit()
        if self.active_sequence_model.get_frame_count() == 0:
            self.playback_status_update.emit(
                "Cannot play: No frames in sequence.", 2000)
            return
        if self.active_sequence_model.get_is_playing():
            self.action_pause()
        else:
            self.action_play()

    def get_current_grid_colors_from_main_window(self) -> list[str]:
        print("WARN AnimatorManager: get_current_grid_colors_from_main_window needs implementation or alternative.")
        return [QColor("black").name()] * 64

    def _update_ui_for_current_sequence(self):
        all_frames_colors = [self.active_sequence_model.get_frame_colors(i) or [QColor("black").name()] * 64
                             for i in range(self.active_sequence_model.get_frame_count())]
        current_edit_idx = self.active_sequence_model.get_current_edit_frame_index()
        current_playback_idx = self.active_sequence_model.get_current_playback_frame_index(
        ) if self.active_sequence_model.get_is_playing() else -1
        self.sequence_timeline_widget.update_frames_display(
            all_frames_colors, current_edit_idx, current_playback_idx)
        self.sequence_controls_widget.set_frame_delay_ui(
            self.active_sequence_model.frame_delay_ms)
        self._emit_state_updates()

    def _update_ui_for_current_sequence_properties(self):
        self.sequence_controls_widget.set_frame_delay_ui(
            self.active_sequence_model.frame_delay_ms)
        self.refresh_sequences_list_and_select(
            self.active_sequence_model.name,
            self._get_type_id_from_filepath(
                self.active_sequence_model.loaded_filepath)
        )
        self._emit_state_updates()

    # Add can_undo, can_redo
    def _update_animator_controls_enabled_state(self, can_undo: bool = False, can_redo: bool = False):
        has_frames = self.active_sequence_model.get_frame_count() > 0
        num_selected_frames = len(self.sequence_timeline_widget.get_selected_item_indices(
        )) if self.sequence_timeline_widget else 0
        can_operate_on_selection = num_selected_frames > 0
        self.sequence_controls_widget.set_controls_enabled_state(
            enabled=True,
            frame_selected=can_operate_on_selection,
            has_frames=has_frames,
            clipboard_has_content=bool(self.frame_clipboard),
            can_undo=can_undo,  # Pass to controls widget
            can_redo=can_redo  # Pass to controls widget
        )
        self.sequence_timeline_widget.setEnabled(True)
        is_valid_combo_selection = self.sequence_selection_combo.currentIndex() > 0 and \
            self.sequence_selection_combo.currentText() != "No sequences found"
        self.load_sequence_button.setEnabled(is_valid_combo_selection)
        item_data = self.sequence_selection_combo.currentData()
        can_delete_combo_item = is_valid_combo_selection and item_data and item_data.get(
            "type") in ["user", "sampler"]
        self.delete_sequence_button.setEnabled(can_delete_combo_item)
        self.new_sequence_button.setEnabled(True)
        self.save_sequence_as_button.setEnabled(has_frames)

    def on_model_frame_content_updated(self, frame_index: int):
        current_edit_idx = self.active_sequence_model.get_current_edit_frame_index()
        if frame_index == current_edit_idx:
            colors_hex_for_main_grid = self.active_sequence_model.get_frame_colors(
                frame_index)
            if colors_hex_for_main_grid:
                self.active_frame_data_for_display.emit(
                    colors_hex_for_main_grid)
        if self.sequence_timeline_widget:
            frame_colors_for_thumbnail = self.active_sequence_model.get_frame_colors(
                frame_index)
            if frame_colors_for_thumbnail:
                self.sequence_timeline_widget.update_single_frame_thumbnail_data(
                    frame_index, frame_colors_for_thumbnail)
        self._emit_state_updates()

    def on_model_edit_frame_changed(self, frame_index: int):
        if self.sequence_timeline_widget:
            self.sequence_timeline_widget.set_selected_frame_by_index(
                frame_index)
        current_colors_hex = None
        if frame_index != -1 and self.active_sequence_model:
            current_colors_hex = self.active_sequence_model.get_frame_colors(
                frame_index)
        final_data_to_emit = current_colors_hex if current_colors_hex else [
            QColor("black").name()] * 64
        self.active_frame_data_for_display.emit(final_data_to_emit)
        self._emit_state_updates()

    def on_model_playback_state_changed(self, is_playing: bool):
        self.sequence_controls_widget.update_playback_button_state(is_playing)
        if is_playing:
            self.playback_status_update.emit("Sequence playing...", 0)
            self.playback_timer.start(
                self.active_sequence_model.frame_delay_ms)
        else:
            self.playback_timer.stop()
            is_at_start_after_stop = self.active_sequence_model.get_current_playback_frame_index() == 0 and \
                not self.active_sequence_model.loop
            if is_at_start_after_stop or not self.playback_timer.isActive():
                self.playback_status_update.emit("Sequence stopped.", 3000)
                edit_idx = self.active_sequence_model.get_current_edit_frame_index()
                current_frame_colors = self.active_sequence_model.get_frame_colors(
                    edit_idx) if edit_idx != -1 else None
                self.active_frame_data_for_display.emit(
                    current_frame_colors if current_frame_colors else [QColor("black").name()] * 64)
            else:
                self.playback_status_update.emit("Sequence paused.", 3000)
        self.animator_playback_active_status_changed.emit(is_playing)
        self._update_ui_for_current_sequence()
        self._emit_state_updates()

    def stop_current_animation_playback(self):
        if self.playback_timer.isActive():
            self.playback_timer.stop()
        if self.active_sequence_model.get_is_playing():
            self.active_sequence_model.stop_playback()

    def on_timeline_frame_selected(self, frame_index: int):
        self.request_sampler_disable.emit()
        if self.active_sequence_model:
            current_model_edit_idx = self.active_sequence_model.get_current_edit_frame_index()
            if current_model_edit_idx != frame_index:
                self.active_sequence_model.set_current_edit_frame_index(
                    frame_index)
        self._emit_state_updates()

    def on_timeline_add_frame_action(self, frame_type: str):
        self.request_sampler_disable.emit()
        current_edit_idx = self.active_sequence_model.get_current_edit_frame_index()
        insert_at = current_edit_idx + 1 if current_edit_idx != -1 else None
        if frame_type == "blank":
            self.action_add_frame("blank", at_index=insert_at)

    def action_add_frame(self, frame_type: str, at_index: int | None = None, snapshot_data: list[str] | None = None):
        self.request_sampler_disable.emit()
        self.stop_current_animation_playback()
        if frame_type == "blank":
            self.active_sequence_model.add_blank_frame(at_index)
            self.playback_status_update.emit("Blank frame added.", 1500)
        elif frame_type == "snapshot":
            if snapshot_data:
                new_frame_idx = self.active_sequence_model.add_blank_frame(
                    at_index)
                if new_frame_idx == self.active_sequence_model.get_current_edit_frame_index() and new_frame_idx != -1:
                    self.active_sequence_model.update_all_pads_in_current_edit_frame(
                        snapshot_data)
                    self.playback_status_update.emit(
                        "Snapshot applied to new frame.", 1500)
                else:
                    self.playback_status_update.emit(
                        "Snapshot data received, but couldn't apply to new frame.", 3000)
            else:
                self.playback_status_update.emit(
                    "Snapshot type called without data; adding blank frame instead.", 2500)
                self.active_sequence_model.add_blank_frame(at_index)
        else:
            self.active_sequence_model.add_blank_frame(at_index)

    def action_navigate_first(self):
        self.request_sampler_disable.emit()
        if self.active_sequence_model.get_frame_count() > 0:
            self.active_sequence_model.set_current_edit_frame_index(0)

    def action_navigate_prev(self):
        self.request_sampler_disable.emit()
        idx, count = self.active_sequence_model.get_current_edit_frame_index(
        ), self.active_sequence_model.get_frame_count()
        if count > 0:
            self.active_sequence_model.set_current_edit_frame_index(
                (idx - 1 + count) % count)

    def action_navigate_next(self):
        self.request_sampler_disable.emit()
        idx, count = self.active_sequence_model.get_current_edit_frame_index(
        ), self.active_sequence_model.get_frame_count()
        if count > 0:
            self.active_sequence_model.set_current_edit_frame_index(
                (idx + 1) % count)

    def action_navigate_last(self):
        self.request_sampler_disable.emit()
        count = self.active_sequence_model.get_frame_count()
        if count > 0:
            self.active_sequence_model.set_current_edit_frame_index(count - 1)

    def action_play(self):
        self.request_sampler_disable.emit()
        if self.active_sequence_model.get_frame_count() == 0:
            self.playback_status_update.emit("Cannot play: No frames.", 2000)
            self.sequence_controls_widget.update_playback_button_state(False)
            return
        start_idx = self.active_sequence_model.get_current_edit_frame_index()
        if start_idx == -1 or start_idx >= self.active_sequence_model.get_frame_count():
            start_idx = 0
        self.active_sequence_model._playback_frame_index = start_idx
        self.active_sequence_model.start_playback()

    def action_pause(self): self.active_sequence_model.pause_playback()
    def action_stop(self): self.active_sequence_model.stop_playback()

    def on_controls_frame_delay_changed(self, delay_ms: int):
        self.active_sequence_model.set_frame_delay_ms(delay_ms)
        if self.playback_timer.isActive():
            self.playback_timer.start(delay_ms)
        self.playback_status_update.emit(
            f"Frame delay set to {delay_ms} ms.", 1500)

    def advance_and_play_next_frame(self):
        if not self.active_sequence_model.get_is_playing():
            self.stop_current_animation_playback()
            return
        colors_hex = self.active_sequence_model.step_and_get_playback_frame_colors()
        if colors_hex:
            self.active_frame_data_for_display.emit(colors_hex)
        if not self.active_sequence_model.get_is_playing():
            self.stop_current_animation_playback()

    def _get_sequence_dir_path(self, dir_type: str = "user") -> str:
        if dir_type == "user":
            return self.user_sequences_path
        elif dir_type == "prefab":
            return self.prefab_sequences_path
        elif dir_type == "sampler":
            return self.sampler_recordings_path
        return self.user_sequences_path

    def _load_all_sequences_metadata(self) -> dict:
        PREFIX_SAMPLER = "[Sampler] "
        PREFIX_PREFAB = "[Prefab] "
        PREFIX_USER = ""
        loaded_meta = {}
        sources = [{"id": "sampler", "prefix": PREFIX_SAMPLER}, {
            "id": "user", "prefix": PREFIX_USER}, {"id": "prefab", "prefix": PREFIX_PREFAB}]
        for src_cfg in sources:
            type_id, prefix = src_cfg["id"], src_cfg["prefix"]
            abs_dir = self._get_sequence_dir_path(type_id)
            os.makedirs(abs_dir, exist_ok=True)
            if not os.path.isdir(abs_dir):
                continue
            for filepath in glob.glob(os.path.join(abs_dir, "*.json")):
                try:
                    with open(filepath, "r", encoding='utf-8') as f:
                        data = json.load(f)
                    if not isinstance(data, dict) or "name" not in data or "frames" not in data:
                        continue
                    raw_name = data.get("name", os.path.splitext(
                        os.path.basename(filepath))[0])
                    display_name = prefix + \
                        str(raw_name).replace("_", " ").replace("-", " ")
                    if display_name:
                        loaded_meta[display_name] = {
                            "path": filepath, "type": type_id, "raw_name": raw_name}
                except Exception:
                    pass
        return loaded_meta

    def _update_sequences_combobox(self, active_seq_raw_name: str | None = None, active_seq_type_id: str | None = None):
        self.sequence_selection_combo.blockSignals(True)
        current_text_before = self.sequence_selection_combo.currentText()
        self.sequence_selection_combo.clear()
        self.sequence_selection_combo.addItem("--- Select Sequence ---")
        all_meta = self._load_all_sequences_metadata()
        if not all_meta:
            self.sequence_selection_combo.addItem("No sequences found")
        else:
            sorted_names = sorted(all_meta.keys(), key=lambda k: (
                0 if all_meta[k]['type'] == 'prefab' else 1 if all_meta[k]['type'] == 'sampler' else 2, k.lower(
                )
            ))
            for name in sorted_names:
                self.sequence_selection_combo.addItem(
                    name, userData=all_meta[name])
        target_idx = 0
        if active_seq_raw_name and active_seq_type_id:
            prefix_map = {"prefab": "[Prefab] ",
                          "sampler": "[Sampler] ", "user": ""}
            text_to_find = prefix_map.get(
                active_seq_type_id, "") + str(active_seq_raw_name).replace("_", " ").replace("-", " ")
            idx = self.sequence_selection_combo.findText(
                text_to_find, Qt.MatchFlag.MatchFixedString)
            if idx != -1:
                target_idx = idx
        elif current_text_before not in ["--- Select Sequence ---", "No sequences found"]:
            idx = self.sequence_selection_combo.findText(
                current_text_before, Qt.MatchFlag.MatchFixedString)
            if idx != -1:
                target_idx = idx
        if self.sequence_selection_combo.count() > target_idx:
            self.sequence_selection_combo.setCurrentIndex(target_idx)
        self.sequence_selection_combo.blockSignals(False)
        self._on_sequence_combo_changed(
            self.sequence_selection_combo.currentIndex())

    def refresh_sequences_list_and_select(self, active_seq_raw_name: str | None = None, active_seq_type_id: str | None = None):
        self._update_sequences_combobox(
            active_seq_raw_name, active_seq_type_id)

    def _on_sequence_combo_changed(self, index: int):
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
        if self.active_sequence_model.loaded_filepath and \
           os.path.normpath(self.active_sequence_model.loaded_filepath) == os.path.normpath(filepath):
            self.playback_status_update.emit(
                f"Sequence '{os.path.basename(filepath)}' already active.", 2000)
            return
        self.stop_current_animation_playback()
        new_model = SequenceModel()
        if new_model.load_from_file(filepath):
            self.active_sequence_model = new_model
            self._connect_signals_for_active_sequence_model()
            self._update_ui_for_current_sequence()
            self.playback_status_update.emit(
                f"Sequence '{self.active_sequence_model.name}' loaded.", 2000)
            self.refresh_sequences_list_and_select(
                self.active_sequence_model.name, self._get_type_id_from_filepath(
                    filepath)
            )
        else:
            parent_widget_for_dialog = self.parent() if self.parent() else self
            QMessageBox.warning(parent_widget_for_dialog, "Load Error",
                                f"Failed to load: {os.path.basename(filepath)}")
            self.refresh_sequences_list_and_select()
        self._emit_state_updates()

    def _request_load_selected_sequence_from_main(self):
        index = self.sequence_selection_combo.currentIndex()
        if index > 0:
            item_data = self.sequence_selection_combo.itemData(index)
            if item_data and "path" in item_data:
                self.request_load_sequence_with_prompt.emit(item_data["path"])
            else:
                self.playback_status_update.emit(
                    "Sequence info not found.", 2000)
        else:
            self.playback_status_update.emit(
                "No sequence selected to load.", 2000)

    def _sanitize_filename(self, name: str) -> str:
        name = str(name)
        name = re.sub(r'[^\w\s-]', '', name).strip()
        name = re.sub(r'[-\s]+', '_', name)
        return name if name else "untitled_sequence"

    def _get_type_id_from_filepath(self, filepath: str | None) -> str:
        if not filepath:
            return "user"
        path_lower = filepath.lower()
        if "prefab" in path_lower:
            return "prefab"
        if "sampler_recordings" in path_lower:
            return "sampler"
        return "user"

    def action_new_sequence(self, prompt_save=True):
        self.request_sampler_disable.emit()
        self.stop_current_animation_playback()
        self.active_sequence_model = SequenceModel()
        self._connect_signals_for_active_sequence_model()
        self._update_ui_for_current_sequence()
        self.active_frame_data_for_display.emit([QColor("black").name()] * 64)
        self.playback_status_update.emit("New sequence created.", 2000)
        self.refresh_sequences_list_and_select()
        self._emit_state_updates()

    def action_save_sequence_as(self):
        self.request_sampler_disable.emit()
        if self.active_sequence_model.get_frame_count() == 0:
            self.playback_status_update.emit(
                "Cannot save: No frames in sequence.", 3000)
            return False
        self.stop_current_animation_playback()
        suggested_name = self.active_sequence_model.name if self.active_sequence_model.name != "New Sequence" else ""
        text, ok = QInputDialog.getText(
            self, "Save Sequence As...", "Sequence Name:", text=suggested_name)
        if not (ok and text and text.strip()):
            self.playback_status_update.emit("Save As cancelled.", 2000)
            return False
        raw_name = text.strip()
        filename_base = self._sanitize_filename(raw_name)
        if raw_name.lower().startswith(("[prefab]", "[sampler]")):
            self.playback_status_update.emit(
                "Save Error: Invalid name prefix.", 3000)
            return False
        abs_user_dir = self._get_sequence_dir_path("user")
        os.makedirs(abs_user_dir, exist_ok=True)
        filepath = os.path.join(abs_user_dir, f"{filename_base}.json")
        self.active_sequence_model.set_name(raw_name)
        if self.active_sequence_model.save_to_file(filepath):
            self.playback_status_update.emit(
                f"Sequence '{raw_name}' saved.", 2000)
            self.refresh_sequences_list_and_select(raw_name, "user")
            self._emit_state_updates()
            return True
        else:
            self.playback_status_update.emit(f"Error saving sequence.", 3000)
            return False

    def _on_delete_selected_sequence_button_clicked(self):
        self.request_sampler_disable.emit()
        index = self.sequence_selection_combo.currentIndex()
        if index <= 0:
            self.playback_status_update.emit(
                "No sequence selected to delete.", 2000)
            return
        item_data = self.sequence_selection_combo.itemData(index)
        display_name = self.sequence_selection_combo.itemText(index)
        if not item_data or "path" not in item_data or item_data.get("type") not in ["user", "sampler"]:
            self.playback_status_update.emit(
                "Cannot delete selected item.", 3000)
            return
        filepath = item_data["path"]
        try:
            if os.path.exists(filepath):
                os.remove(filepath)
            self.playback_status_update.emit(
                f"Sequence '{display_name}' deleted.", 2000)
            if self.active_sequence_model.loaded_filepath and \
               os.path.normpath(self.active_sequence_model.loaded_filepath) == os.path.normpath(filepath):
                self.action_new_sequence(prompt_save=False)
            self.refresh_sequences_list_and_select()
        except Exception as e:
            self.playback_status_update.emit(
                f"Error deleting sequence: {e}", 4000)
        self._emit_state_updates()

    def set_overall_enabled_state(self, enabled: bool):
        self.setEnabled(enabled)
        if enabled:
            self._update_animator_controls_enabled_state()
    # Signals to MainWindow
    active_frame_data_for_display = pyqtSignal(list) # list of hex color strings for the grid
    playback_status_update = pyqtSignal(str, int)    # message, duration_ms (0 for persistent)
    sequence_modified_status_changed = pyqtSignal(bool, str) # is_modified, sequence_name
    undo_redo_state_changed = pyqtSignal(bool, bool)      # can_undo, can_redo
    clipboard_state_changed = pyqtSignal(bool)            # has_clipboard_content
    animator_playback_active_status_changed = pyqtSignal(bool) # <<< ADD THIS NEW SIGNAL (is_playing)
    request_load_sequence_with_prompt = pyqtSignal(str) # filepath of sequence to load

    # Signal to MainWindow if sampler needs to be disabled due to animator interaction
    request_sampler_disable = pyqtSignal()

    def __init__(self,
                 user_sequences_base_path: str,
                 sampler_recordings_path: str,
                 prefab_sequences_base_path: str,
                 parent: QWidget | None = None):
        super().__init__(parent)
        self.user_sequences_path = user_sequences_base_path
        self.sampler_recordings_path = sampler_recordings_path
        self.prefab_sequences_path = prefab_sequences_base_path

        self.active_sequence_model = SequenceModel()
        self._connect_signals_for_active_sequence_model()

        self.playback_timer = QTimer(self)
        self.playback_timer.timeout.connect(self.advance_and_play_next_frame)

        self.frame_clipboard: list[AnimationFrame] = []

        # UI Elements (will be initialized in _init_ui)
        self.animator_studio_group_box: QGroupBox | None = None
        self.sequence_selection_combo: QComboBox | None = None
        self.load_sequence_button: QPushButton | None = None
        self.new_sequence_button: QPushButton | None = None
        self.save_sequence_as_button: QPushButton | None = None
        self.delete_sequence_button: QPushButton | None = None
        self.sequence_timeline_widget: SequenceTimelineWidget | None = None
        self.sequence_controls_widget: SequenceControlsWidget | None = None

        # <<< NEW: Attributes to track last emitted status for sequence_modified_status_changed
        self._last_emitted_is_modified: bool | None = None
        self._last_emitted_sequence_name: str | None = None
        # --- END NEW ---

        self._init_ui()
        self._connect_ui_signals()

        # Initial state updates
        # Defer refresh_sequences_list_and_select to ensure UI elements it might affect are fully constructed.
        QTimer.singleShot(0, self.refresh_sequences_list_and_select)

        # _update_ui_for_current_sequence also calls _emit_state_updates.
        # Call it once after _init_ui ensures UI elements are ready for state updates.
        # _emit_state_updates will now be smarter.
        # Ensure this is called after UI is built
        QTimer.singleShot(0, self._update_ui_for_current_sequence)

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0,0,0,0)
        main_layout.setSpacing(10)

        # --- Animator Studio GroupBox (Sequence Selection & Actions) ---
        self.animator_studio_group_box = QGroupBox("🎬 Animator Studio")
        # Set a size policy that allows it to take preferred height but not expand excessively
        self.animator_studio_group_box.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed) # Fixed vertical
        animator_studio_layout = QVBoxLayout(self.animator_studio_group_box)
        # ... (rest of combo_load_layout and action_buttons_layout as before) ...
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

        # Separator
        separator_line = QFrame()
        separator_line.setFrameShape(QFrame.Shape.HLine)
        separator_line.setFrameShadow(QFrame.Shadow.Sunken)
        main_layout.addWidget(separator_line)

        # --- Timeline and Controls Widgets ---
        self.sequence_timeline_widget = SequenceTimelineWidget()
        # --- CRITICAL CHANGES FOR TIMELINE WIDGET ---
        # 1. Set a vertical size policy that allows it to expand.
        self.sequence_timeline_widget.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
        # 2. Set a minimum height. This is an estimate.
        #    Height of one frame item (guesstimate from your timeline code or inspection) ~40-50px?
        #    Spacing between items ~5px?
        #    Scrollbar height if visible?
        #    Let's aim for roughly 2 rows + spacing. If one row is ~50px high with its preview and label,
        #    two rows would be ~100px. Add some for margins/padding within the timeline widget.
        #    This value might need tuning.
        desired_min_timeline_height = 120 # Try this first (e.g., 2 rows * 50px/row + 20px padding/spacing)
        self.sequence_timeline_widget.setMinimumHeight(desired_min_timeline_height)
        # --- END CRITICAL CHANGES ---
        main_layout.addWidget(self.sequence_timeline_widget) # Stretch factor for this widget is handled by its size policy now

        self.sequence_controls_widget = SequenceControlsWidget()
        # Controls widget usually has a fixed height based on its buttons
        self.sequence_controls_widget.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        main_layout.addWidget(self.sequence_controls_widget)

        # --- Ensure AnimatorManagerWidget itself can expand vertically ---
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)

    def _connect_ui_signals(self):
        # Animator Studio Buttons
        self.sequence_selection_combo.currentIndexChanged.connect(self._on_sequence_combo_changed)
        # self.load_sequence_button.clicked.connect(self._on_load_selected_sequence_button_clicked)
        self.load_sequence_button.clicked.connect(self._request_load_selected_sequence_from_main)
        self.new_sequence_button.clicked.connect(lambda: self.action_new_sequence(prompt_save=True))
        self.save_sequence_as_button.clicked.connect(self.action_save_sequence_as)
        self.delete_sequence_button.clicked.connect(self._on_delete_selected_sequence_button_clicked)

        # Controls Widget
        self.sequence_controls_widget.add_frame_requested.connect(self.action_add_frame) # Handles "blank" from controls
        # self.sequence_controls_widget.default_add_button_clicked.connect(self.handle_default_add_button_click) # REMOVED
        self.sequence_controls_widget.delete_selected_frame_requested.connect(self.action_delete_selected_frames)
        self.sequence_controls_widget.duplicate_selected_frame_requested.connect(self.action_duplicate_selected_frames)
        self.sequence_controls_widget.copy_frames_requested.connect(self.action_copy_frames)
        self.sequence_controls_widget.cut_frames_requested.connect(self.action_cut_frames)
        self.sequence_controls_widget.paste_frames_requested.connect(self.action_paste_frames)
        self.sequence_controls_widget.navigate_first_requested.connect(self.action_navigate_first)
        self.sequence_controls_widget.navigate_prev_requested.connect(self.action_navigate_prev)
        self.sequence_controls_widget.navigate_next_requested.connect(self.action_navigate_next)
        self.sequence_controls_widget.navigate_last_requested.connect(self.action_navigate_last)
        self.sequence_controls_widget.play_requested.connect(self.action_play)
        self.sequence_controls_widget.pause_requested.connect(self.action_pause)
        self.sequence_controls_widget.stop_requested.connect(self.action_stop)
        self.sequence_controls_widget.frame_delay_changed.connect(self.on_controls_frame_delay_changed)

        # Timeline Widget
        self.sequence_timeline_widget.add_frame_action_triggered.connect(self.on_timeline_add_frame_action) # Connects to revised method
        self.sequence_timeline_widget.frame_selected.connect(self.on_timeline_frame_selected)
        self.sequence_timeline_widget.copy_frames_action_triggered.connect(self.action_copy_frames)
        self.sequence_timeline_widget.cut_frames_action_triggered.connect(self.action_cut_frames)
        self.sequence_timeline_widget.paste_frames_action_triggered.connect(self.action_paste_frames)
        self.sequence_timeline_widget.duplicate_selected_action_triggered.connect(self.action_duplicate_selected_frames)
        self.sequence_timeline_widget.delete_selected_action_triggered.connect(self.action_delete_selected_frames)
        self.sequence_timeline_widget.select_all_action_triggered.connect(self.action_select_all_frames)
        
        self.sequence_timeline_widget.insert_blank_frame_before_action_triggered.connect(
            lambda index: self.action_add_frame("blank", at_index=index)
        )
        self.sequence_timeline_widget.insert_blank_frame_after_action_triggered.connect(
            lambda index: self.action_add_frame("blank", at_index=index + 1)
        )

    def _connect_signals_for_active_sequence_model(self):
        # Disconnect previous model's signals first if any
        try: self.active_sequence_model.frames_changed.disconnect()
        except TypeError: pass
        try: self.active_sequence_model.frame_content_updated.disconnect()
        except TypeError: pass
        try: self.active_sequence_model.current_edit_frame_changed.disconnect()
        except TypeError: pass
        try: self.active_sequence_model.properties_changed.disconnect()
        except TypeError: pass
        try: self.active_sequence_model.playback_state_changed.disconnect()
        except TypeError: pass

        # Connect to new model's signals
        self.active_sequence_model.frames_changed.connect(self._update_ui_for_current_sequence)
        self.active_sequence_model.frame_content_updated.connect(self.on_model_frame_content_updated)
        self.active_sequence_model.current_edit_frame_changed.connect(self.on_model_edit_frame_changed)
        self.active_sequence_model.properties_changed.connect(self._update_ui_for_current_sequence_properties)
        self.active_sequence_model.playback_state_changed.connect(self.on_model_playback_state_changed)

    def _emit_state_updates(self):
        """Emits signals to MainWindow to update its state based on current model,
           but only emits sequence_modified_status_changed if there's an actual change
           in the sequence's name or modified status since the last emission.
        """
        current_is_modified = self.active_sequence_model.is_modified
        current_sequence_name = self.active_sequence_model.name

        # <<< MODIFIED: Conditional emission for sequence_modified_status_changed
        if (current_is_modified != self._last_emitted_is_modified) or \
           (current_sequence_name != self._last_emitted_sequence_name):
            # print(f"AMW DEBUG: Emitting sequence_modified_status_changed. PrevMod: {self._last_emitted_is_modified}, CurrMod: {current_is_modified}, PrevName: '{self._last_emitted_sequence_name}', CurrName: '{current_sequence_name}'") # Optional debug
            self.sequence_modified_status_changed.emit(current_is_modified, current_sequence_name)
            self._last_emitted_is_modified = current_is_modified
            self._last_emitted_sequence_name = current_sequence_name
        # else: # Optional debug
            # print(f"AMW DEBUG: SKIPPING sequence_modified_status_changed. PrevMod: {self._last_emitted_is_modified}, CurrMod: {current_is_modified}, PrevName: '{self._last_emitted_sequence_name}', CurrName: '{current_sequence_name}'")
        # --- END MODIFIED ---
            
        self.undo_redo_state_changed.emit(bool(self.active_sequence_model._undo_stack), bool(self.active_sequence_model._redo_stack))
        self.clipboard_state_changed.emit(bool(self.frame_clipboard))
        self._update_animator_controls_enabled_state() # Local UI update

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
        # The model's set_frame_delay_ms should emit properties_changed,
        # which _update_ui_for_current_sequence_properties connects to,
        # which then calls self.sequence_controls_widget.set_frame_delay_ui.

        if self.playback_timer.isActive():
            self.playback_timer.start(actual_delay_ms) # Restart timer with new interval

        # Optionally, emit a signal if other parts of UI need to know FPS changed directly
        # self.playback_speed_changed.emit(1000.0 / actual_delay_ms if actual_delay_ms > 0 else 0)
        
        # Update controls widget UI (redundant if model signal already does this, but safe)
        if hasattr(self, 'sequence_controls_widget') and self.sequence_controls_widget:
            self.sequence_controls_widget.set_frame_delay_ui(actual_delay_ms)

        # Notify MainWindow that properties (including potentially unsaved speed) changed
        self._emit_state_updates()

    def get_navigation_item_count(self) -> int:
        """Returns the number of actual items in the sequence combo box (excluding placeholder)."""
        if self.sequence_selection_combo:
            # If the first item is a placeholder like "--- Select ---", don't count it.
            # Or, count all and let MainWindow handle index adjustments if placeholder is always at index 0.
            # For simplicity, let's assume we only care about actual sequence items.
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
        if self.sequence_selection_combo:
            actual_combo_index_to_set = -1
            current_logical_idx = -1
            for i in range(self.sequence_selection_combo.count()):
                if self.sequence_selection_combo.itemData(i) is not None: 
                    current_logical_idx += 1
                    if current_logical_idx == logical_index:
                        actual_combo_index_to_set = i
                        break
            
            if actual_combo_index_to_set != -1:
                # --- ADD DEBUG PRINTS ---
                current_gui_index = self.sequence_selection_combo.currentIndex()
                current_gui_text = self.sequence_selection_combo.currentText()
                text_at_new_index = self.sequence_selection_combo.itemText(actual_combo_index_to_set)
                print(f"AMW TRACE: Nav: Current GUI index={current_gui_index} ('{current_gui_text}')")
                print(f"AMW TRACE: Nav: Trying to set GUI index to {actual_combo_index_to_set} ('{text_at_new_index}') for logical_index {logical_index}")
                # --- END DEBUG PRINTS ---

                if current_gui_index != actual_combo_index_to_set:
                    self.sequence_selection_combo.setCurrentIndex(actual_combo_index_to_set)
                    print(f"AMW TRACE: Nav: setCurrentIndex({actual_combo_index_to_set}) CALLED.") # Confirm call
                    # _on_sequence_combo_changed will be called by Qt if index truly changed.
                # else: # Optional
                    # print(f"AMW TRACE: Nav: GUI index {actual_combo_index_to_set} already selected.")
                return self.sequence_selection_combo.itemText(actual_combo_index_to_set) # Return text of (now) current item
        return None
    
    def trigger_navigation_current_item_action(self):
        """
        Triggers the action for the currently selected item in the sequence combo box,
        which is typically loading it.
        """
        # print("AMW TRACE: trigger_navigation_current_item_action called.") # Optional
        # This reuses the logic from the "Load" button.
        # Ensure _request_load_selected_sequence_from_main handles the current selection correctly.
        self._request_load_selected_sequence_from_main()

    # --- Public Methods for MainWindow to call (e.g., from QActions) ---
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
            self.playback_status_update.emit("No frames selected to copy.", 2000)
            return
        self.frame_clipboard.clear()
        copied_frames_count = 0
        for index in sorted(selected_indices):
            frame_obj = self.active_sequence_model.get_frame_object(index)
            if frame_obj:
                self.frame_clipboard.append(AnimationFrame(colors=list(frame_obj.get_all_colors())))
                copied_frames_count += 1
        if copied_frames_count > 0:
            self.playback_status_update.emit(f"{copied_frames_count} frame(s) copied.", 2000)
        else:
            self.playback_status_update.emit("Could not copy selected frames.", 2000)
        self._emit_state_updates()

    def action_cut_frames(self):
        self.request_sampler_disable.emit()
        self.stop_current_animation_playback()
        selected_indices = self.sequence_timeline_widget.get_selected_item_indices()
        if not selected_indices:
            self.playback_status_update.emit("No frames selected to cut.", 2000); return
        
        self.frame_clipboard.clear(); copied_frames_count = 0
        for index in sorted(selected_indices): # Copy first
            frame_obj = self.active_sequence_model.get_frame_object(index)
            if frame_obj:
                self.frame_clipboard.append(AnimationFrame(colors=list(frame_obj.get_all_colors())))
                copied_frames_count += 1
        if copied_frames_count == 0:
            self.playback_status_update.emit("Could not prepare frames for cutting.", 2000); return

        if self.active_sequence_model.delete_frames_at_indices(selected_indices): # Then delete
            self.playback_status_update.emit(f"{copied_frames_count} frame(s) cut.", 2000)
        else:
            self.frame_clipboard.clear()
            self.playback_status_update.emit("Error cutting frames.", 3000)
        self._emit_state_updates()

    def action_paste_frames(self):
        self.request_sampler_disable.emit()
        if not self.frame_clipboard:
            self.playback_status_update.emit("Clipboard is empty.", 2000); return
        self.stop_current_animation_playback()
        selected_indices = self.sequence_timeline_widget.get_selected_item_indices()
        insertion_index = max(selected_indices) + 1 if selected_indices else \
                          (self.active_sequence_model.get_current_edit_frame_index() + 1
                           if self.active_sequence_model.get_current_edit_frame_index() != -1
                           else self.active_sequence_model.get_frame_count())
        
        pasted_indices = self.active_sequence_model.paste_frames(self.frame_clipboard, at_index=insertion_index)
        if pasted_indices:
            self.playback_status_update.emit(f"{len(pasted_indices)} frame(s) pasted.", 2000)
            QTimer.singleShot(0, lambda: self.sequence_timeline_widget.select_items_by_indices(pasted_indices))
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
        # Model signals will trigger UI updates and _emit_state_updates

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
        # Model signals will trigger UI updates and _emit_state_updates

    def action_select_all_frames(self):
        self.request_sampler_disable.emit()
        if self.active_sequence_model.get_frame_count() > 0:
            all_indices = list(range(self.active_sequence_model.get_frame_count()))
            self.sequence_timeline_widget.select_items_by_indices(all_indices)
            self.playback_status_update.emit(f"All {len(all_indices)} frames selected.", 1500)
        else:
            self.playback_status_update.emit("No frames to select.", 1500)
        self._update_animator_controls_enabled_state() # Update local button states based on selection

    def action_play_pause_toggle(self): # For global spacebar if MainWindow routes it here
        self.request_sampler_disable.emit()
        if self.active_sequence_model.get_frame_count() == 0:
            self.playback_status_update.emit("Cannot play: No frames in sequence.", 2000)
            return
        if self.active_sequence_model.get_is_playing():
            self.action_pause()
        else:
            self.action_play()
            
    # --- Internal Logic & Slots ---
    def get_current_grid_colors_from_main_window(self) -> list[str]:
        print("WARN AnimatorManager: get_current_grid_colors_from_main_window needs implementation or alternative.")
        return [QColor("black").name()] * 64 # Placeholder

    def _update_ui_for_current_sequence(self):
        print(f"DEBUG AMW._update_ui_for_current_sequence: Called. Frame count: {self.active_sequence_model.get_frame_count()}") # ADD THIS
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
        # MainWindow will handle global enabling based on connection/sampler state
        has_frames = self.active_sequence_model.get_frame_count() > 0
        num_selected_frames = len(self.sequence_timeline_widget.get_selected_item_indices()) if self.sequence_timeline_widget else 0
        can_operate_on_selection = num_selected_frames > 0

        self.sequence_controls_widget.set_controls_enabled_state(
            enabled=True, # Assume this widget is enabled by MainWindow if animator can be used
            frame_selected=can_operate_on_selection,
            has_frames=has_frames,
            clipboard_has_content=bool(self.frame_clipboard)
        )
        self.sequence_timeline_widget.setEnabled(True)

        # File management buttons
        is_valid_combo_selection = self.sequence_selection_combo.currentIndex() > 0 and \
                                   self.sequence_selection_combo.currentText() != "No sequences found"
        self.load_sequence_button.setEnabled(is_valid_combo_selection)
        # The delete button is enabled only for user/sampler sequences
        item_data = self.sequence_selection_combo.currentData()
        can_delete_combo_item = is_valid_combo_selection and item_data and item_data.get("type") in ["user", "sampler"]
        self.delete_sequence_button.setEnabled(can_delete_combo_item)
        # The new sequence button is always enabled
        self.new_sequence_button.setEnabled(True) # Always possible to start new
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

# In class AnimatorManagerWidget(QWidget):

    # frame_index is the model's new current_edit_frame_index
    def on_model_edit_frame_changed(self, frame_index: int):
        # print(f"DEBUG AMW: on_model_edit_frame_changed CALLED with NEW model_frame_index: {frame_index}")

        if self.sequence_timeline_widget:
            # print(f"DEBUG AMW: on_model_edit_frame_changed - Calling timeline_widget.set_selected_frame_by_index({frame_index})")
            self.sequence_timeline_widget.set_selected_frame_by_index(
                frame_index)

        current_colors_hex = None
        if frame_index != -1 and self.active_sequence_model:
            current_colors_hex = self.active_sequence_model.get_frame_colors(
                frame_index)

        final_data_to_emit = current_colors_hex if current_colors_hex else [
            QColor("black").name()] * 64
        self.active_frame_data_for_display.emit(final_data_to_emit)

        self._emit_state_updates()

        
    def on_model_playback_state_changed(self, is_playing: bool):
        self.sequence_controls_widget.update_playback_button_state(is_playing)
        if is_playing:
            self.playback_status_update.emit("Sequence playing...", 0)
            self.playback_timer.start(self.active_sequence_model.frame_delay_ms)
        else:
            self.playback_timer.stop()
            # Check if it was a natural stop or a pause
            is_at_start_after_stop = self.active_sequence_model.get_current_playback_frame_index() == 0 and \
                                     not self.active_sequence_model.loop # Simplified: if at start and not looping, it's a full stop
            
            if is_at_start_after_stop or not self.playback_timer.isActive(): # If timer stopped fully
                self.playback_status_update.emit("Sequence stopped.", 3000)
                # Restore edit frame view after stop
                edit_idx = self.active_sequence_model.get_current_edit_frame_index()
                current_frame_colors = self.active_sequence_model.get_frame_colors(edit_idx) if edit_idx !=-1 else None
                self.active_frame_data_for_display.emit(current_frame_colors if current_frame_colors else [QColor("black").name()] * 64)
            else: # It was a pause
                self.playback_status_update.emit("Sequence paused.", 3000) 
        self.animator_playback_active_status_changed.emit(is_playing) # <<< ADD THIS LINE to emit the new signal       
        self._update_ui_for_current_sequence() # Refresh timeline playback indicator
        self._emit_state_updates()

    # --- UI Action Handlers (called by signals from child widgets or public methods) ---
    def stop_current_animation_playback(self):
        if self.playback_timer.isActive(): self.playback_timer.stop()
        if self.active_sequence_model.get_is_playing(): self.active_sequence_model.stop_playback()

    # frame_index is from the timeline widget UI
    def on_timeline_frame_selected(self, frame_index: int):
        print(
            f"DEBUG AMW: on_timeline_frame_selected CALLED with frame_index from timeline: {frame_index}")

        self.request_sampler_disable.emit()

        # Tell the model about the new intended edit frame from the UI selection.
        if self.active_sequence_model:
            # Only proceed if the timeline's selection is different from the model's current edit frame,
            # or if the model currently has no selection (-1) and the timeline selects a valid one.
            # This helps prevent re-processing if the model already knows this is the edit frame.
            current_model_edit_idx = self.active_sequence_model.get_current_edit_frame_index()
            if current_model_edit_idx != frame_index:
                print(
                    f"DEBUG AMW: on_timeline_frame_selected - Model's edit_idx ({current_model_edit_idx}) differs from timeline's ({frame_index}). Updating model.")
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

    def action_pause(self): self.active_sequence_model.pause_playback()
    def action_stop(self): self.active_sequence_model.stop_playback()

    def on_controls_frame_delay_changed(self, delay_ms: int):
        self.active_sequence_model.set_frame_delay_ms(delay_ms)
        if self.playback_timer.isActive(): self.playback_timer.start(delay_ms)
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
    # --- Sequence File Management ---
    def _get_sequence_dir_path(self, dir_type: str = "user") -> str:
        if dir_type == "user":
            return self.user_sequences_path
        elif dir_type == "prefab":
            return self.prefab_sequences_path
        elif dir_type == "sampler":
            return self.sampler_recordings_path
        else:
            print(f"Warning: Unknown sequence dir_type '{dir_type}' in AnimatorManagerWidget. Defaulting to user path.")
            return self.user_sequences_path # Fallback

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

    def _update_sequences_combobox(self, active_seq_raw_name: str | None = None, active_seq_type_id: str | None = None):
        self.sequence_selection_combo.blockSignals(True)
        current_text_before = self.sequence_selection_combo.currentText()
        self.sequence_selection_combo.clear()
        self.sequence_selection_combo.addItem("--- Select Sequence ---")
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
        
        if self.active_sequence_model.loaded_filepath and \
           os.path.normpath(self.active_sequence_model.loaded_filepath) == os.path.normpath(filepath):
            self.playback_status_update.emit(f"Sequence '{os.path.basename(filepath)}' already active.", 2000)
            return

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
            # This QMessageBox should ideally be handled by MainWindow if it initiates the load.
            # For now, assuming AMW shows its own modal dialogs.
            parent_widget_for_dialog = self.parent() if self.parent() else self
            QMessageBox.warning(parent_widget_for_dialog, "Load Error", f"Failed to load: {os.path.basename(filepath)}")
            self.refresh_sequences_list_and_select() # Refresh combo even on fail
        
        self._emit_state_updates()

    def _on_load_selected_sequence_button_clicked(self):
        # This method is now effectively replaced by _request_load_selected_sequence_from_main
        # and the logic it triggers in MainWindow.
        # We can keep it simple or remove it if _request_load_selected_sequence_from_main is connected directly.
        # For clarity, let's have _request_load_selected_sequence_from_main handle it.
        pass # Or remove if you connect _request_load_selected_sequence_from_main directly

    def _request_load_selected_sequence_from_main(self):
        index = self.sequence_selection_combo.currentIndex()
        if index > 0:
            item_data = self.sequence_selection_combo.itemData(index)
            if item_data and "path" in item_data:
                filepath_to_load = item_data["path"]
                # Emit signal to MainWindow to handle the prompt and conditional load
                self.request_load_sequence_with_prompt.emit(filepath_to_load)
            else:
                self.playback_status_update.emit("Sequence info not found.", 2000)
        else:
            self.playback_status_update.emit("No sequence selected to load.", 2000)

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

    def action_new_sequence(self, prompt_save=True):  # For global QAction
        self.request_sampler_disable.emit()
        # MainWindow now handles this prompt via request_load_sequence_with_prompt if needed
        # if prompt_save and self.active_sequence_model.is_modified:
        #     pass

        self.stop_current_animation_playback()
        self.active_sequence_model = SequenceModel()
        self._connect_signals_for_active_sequence_model()
        # This will set edit_idx to -1 if no frames
        self._update_ui_for_current_sequence()
        self.active_frame_data_for_display.emit([QColor("black").name()] * 64)
        self.playback_status_update.emit("New sequence created.", 2000)
        self.refresh_sequences_list_and_select()
        self._emit_state_updates()

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
        if index <= 0:
            self.playback_status_update.emit("No sequence selected to delete.", 2000); return
        item_data = self.sequence_selection_combo.itemData(index)
        display_name = self.sequence_selection_combo.itemText(index)
        if not item_data or "path" not in item_data or item_data.get("type") not in ["user", "sampler"]:
            self.playback_status_update.emit("Cannot delete selected item.", 3000); return

        # reply = QMessageBox.question(...) # Needs MW parent
        # Assuming Yes for now
        
        filepath = item_data["path"]
        try:
            if os.path.exists(filepath): os.remove(filepath)
            self.playback_status_update.emit(f"Sequence '{display_name}' deleted.", 2000)
            if self.active_sequence_model.loaded_filepath and \
               os.path.normpath(self.active_sequence_model.loaded_filepath) == os.path.normpath(filepath):
                self.action_new_sequence(prompt_save=False) # Create new if active was deleted
            self.refresh_sequences_list_and_select()
        except Exception as e:
            # QMessageBox.critical(self, "Delete Error", f"Could not delete: {e}") # Needs MW parent
            self.playback_status_update.emit(f"Error deleting sequence: {e}", 4000)
        self._emit_state_updates()

    def set_overall_enabled_state(self, enabled: bool):
        """Called by MainWindow to enable/disable this entire animator panel."""
        self.setEnabled(enabled)
        if enabled:
            self._update_animator_controls_enabled_state() # Refresh internal states