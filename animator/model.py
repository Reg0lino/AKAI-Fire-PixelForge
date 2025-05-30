# AKAI_Fire_RGB_Controller/animator/model.py
import json
import os
import copy # Ensure copy is imported for deep copies
from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtGui import QColor

DEFAULT_FRAME_DELAY_MS = 200 
MAX_UNDO_STEPS = 50

class AnimationFrame:
    def __init__(self, colors=None): 
        if colors and isinstance(colors, list) and len(colors) == 64:
            self.colors = list(colors) # Ensure it's a copy
        else:
            # If colors is None or invalid, initialize with black
            self.colors = [QColor("black").name()] * 64

    def set_pad_color(self, pad_index, color_hex: str):
        if 0 <= pad_index < 64:
            q_color = QColor(color_hex)
            self.colors[pad_index] = q_color.name() if q_color.isValid() else QColor("black").name()

    def get_pad_color(self, pad_index):
        if 0 <= pad_index < 64:
            return self.colors[pad_index]
        return QColor("black").name()

    def get_all_colors(self) -> list:
        return list(self.colors) # Return a copy

    def __eq__(self, other):
        if isinstance(other, AnimationFrame):
            return self.colors == other.colors
        return False

class SequenceModel(QObject):
    frames_changed = pyqtSignal()
    frame_content_updated = pyqtSignal(int) # Parameter is frame_index
    current_edit_frame_changed = pyqtSignal(int) # Parameter is new_edit_frame_index (-1 if none)
    properties_changed = pyqtSignal()
    playback_state_changed = pyqtSignal(bool) # Parameter is is_playing

    def __init__(self, name="New Sequence", parent=None):
        super().__init__(parent)
        self.name = name
        self.description = "A cool sequence of pad layouts."
        self.frame_delay_ms = DEFAULT_FRAME_DELAY_MS
        self.loop = True
        
        self.frames: list[AnimationFrame] = [] # Explicitly type hint
        self._current_edit_frame_index = -1 # -1 means no frame is selected for editing

        self._undo_stack = []
        self._redo_stack = []

        self._is_playing = False
        self._playback_frame_index = 0 # Current frame index during playback

        self.loaded_filepath = None # Path if loaded from/saved to a file
        self.is_modified = False # Flag to track unsaved changes
        # <<< NEW ATTRIBUTE for managing paint stroke undo >>>
        self._paint_action_in_progress = False

    def _mark_modified(self):
        """Sets the modified flag to True."""
        if not self.is_modified:
            self.is_modified = True
            # print(f"DEBUG: SequenceModel '{self.name}' marked as modified.")

    def _push_undo_state(self):
        # if len(self.frames) == 0 and not self._undo_stack :
        #      pass

        if len(self._undo_stack) >= MAX_UNDO_STEPS:
            self._undo_stack.pop(0)  # Remove the oldest state

        # --- START OF DETAILED LOGGING FOR UNDO STATE ---
        print(
            f"MODEL_UNDO_DEBUG: _push_undo_state called. Current edit frame index: {self._current_edit_frame_index}")
        if 0 <= self._current_edit_frame_index < len(self.frames):
            current_edit_frame_for_log = self.frames[self._current_edit_frame_index]
            frame_colors_for_log = current_edit_frame_for_log.get_all_colors()
            # Log first few and last few colors to get an idea of its content
            if len(frame_colors_for_log) >= 64:
                log_sample = frame_colors_for_log[:5] + \
                    ["..."] + frame_colors_for_log[-5:]
                is_blank_log = all(c == QColor("black").name()
                                   for c in frame_colors_for_log)
                print(
                    f"MODEL_UNDO_DEBUG:   Content of current edit frame (idx {self._current_edit_frame_index}) being snapshotted: {log_sample}, IsBlank: {is_blank_log}")
            else:
                print(
                    f"MODEL_UNDO_DEBUG:   Current edit frame (idx {self._current_edit_frame_index}) has unexpected color count: {len(frame_colors_for_log)}")
        elif self.frames:  # Edit index is -1 but frames exist
            print(
                f"MODEL_UNDO_DEBUG:   No current edit frame selected (index {self._current_edit_frame_index}), but frames exist. Logging first frame content if available.")
            if len(self.frames) > 0:
                first_frame_for_log = self.frames[0]
                first_frame_colors_log = first_frame_for_log.get_all_colors()
                if len(first_frame_colors_log) >= 64:
                    log_sample_first = first_frame_colors_log[:5] + [
                        "..."] + first_frame_colors_log[-5:]
                    is_blank_first_log = all(c == QColor(
                        "black").name() for c in first_frame_colors_log)
                    print(
                        f"MODEL_UNDO_DEBUG:     Content of first frame (idx 0) in sequence: {log_sample_first}, IsBlank: {is_blank_first_log}")
        else:  # No frames in sequence
            print(
                f"MODEL_UNDO_DEBUG:   No frames in sequence. Pushing current state (name, delay).")
        # --- END OF DETAILED LOGGING FOR UNDO STATE ---

        # Create deep copies of frames for the undo state
        frames_copy = [AnimationFrame(
            colors=frame.get_all_colors()) for frame in self.frames]

        self._undo_stack.append({
            "frames": frames_copy,
            "current_edit_frame_index": self._current_edit_frame_index,
            "name": self.name,  # Also track name/properties if they are undoable
            "frame_delay_ms": self.frame_delay_ms
            # Add other properties like 'loop', 'description' if they should be part of undo
        })
        # Log stack size
        print(
            f"MODEL_UNDO_DEBUG:   Pushed state to undo_stack. New stack size: {len(self._undo_stack)}")
        self._redo_stack.clear()  # Any new action clears the redo stack

    def _apply_state(self, state_dict):
        """Applies a previously saved state (from undo/redo stack)."""
        self.frames = state_dict["frames"] # These are already AnimationFrame objects
        self.name = state_dict.get("name", self.name) 
        self.frame_delay_ms = state_dict.get("frame_delay_ms", self.frame_delay_ms)

        new_edit_index = state_dict["current_edit_frame_index"]
        
        # Validate and set the current_edit_frame_index
        if not self.frames:
            self._current_edit_frame_index = -1
        elif not (0 <= new_edit_index < len(self.frames)):
            # If index is out of bounds, select first frame if available, else -1
            self._current_edit_frame_index = 0 if self.frames else -1
        else:
            self._current_edit_frame_index = new_edit_index

        self.frames_changed.emit()
        self.properties_changed.emit() # If name/delay changed
        self.current_edit_frame_changed.emit(self._current_edit_frame_index)
        self._mark_modified() # Applying an undo/redo state means it's now different from saved (or its previous state)
        
        
    def begin_paint_stroke(self):
        # print(f"MODEL DEBUG: begin_paint_stroke() called. Current _paint_action_in_progress: {self._paint_action_in_progress}") # <<< ADD DEBUG
        if not self._paint_action_in_progress:
            # print("MODEL DEBUG: ---> Pushing undo state because stroke is starting.") # <<< ADD DEBUG
            self._push_undo_state()
            self._paint_action_in_progress = True
        # else:
            # print("MODEL DEBUG: ---> Stroke already in progress, NOT pushing undo state.") # <<< ADD DEBUG

    def end_paint_stroke(self):
        # print(f"MODEL DEBUG: end_paint_stroke() called. Setting _paint_action_in_progress to False.") # <<< ADD DEBUG
        self._paint_action_in_progress = False
        
        
    def undo(self):
        if not self._undo_stack:
            return False
        
        # Current state becomes a redo state (deep copy frames)
        current_frames_copy = [AnimationFrame(colors=frame.get_all_colors()) for frame in self.frames]
        self._redo_stack.append({
            "frames": current_frames_copy, 
            "current_edit_frame_index": self._current_edit_frame_index,
            "name": self.name, 
            "frame_delay_ms": self.frame_delay_ms
        })
        
        previous_state = self._undo_stack.pop()
        self._apply_state(previous_state)
        # self._mark_modified() is called by _apply_state
        return True

    def redo(self):
        if not self._redo_stack:
            return False
            
        # Current state becomes an undo state (deep copy frames)
        current_frames_copy = [AnimationFrame(colors=frame.get_all_colors()) for frame in self.frames]
        self._undo_stack.append({
            "frames": current_frames_copy, 
            "current_edit_frame_index": self._current_edit_frame_index,
            "name": self.name, 
            "frame_delay_ms": self.frame_delay_ms
        })
        if len(self._undo_stack) > MAX_UNDO_STEPS: # Manage undo stack size
            self._undo_stack.pop(0)

        redone_state = self._redo_stack.pop()
        self._apply_state(redone_state)
        # self._mark_modified() is called by _apply_state
        return True

    def _add_frame_internal(self, frame_object: AnimationFrame, at_index=None) -> int:
        print(f"DEBUG Model._add_frame_internal: Called. Current frame count before add: {len(self.frames)}, at_index={at_index}") # ADD THIS
        if at_index is None or not (0 <= at_index <= len(self.frames)):
            # Append to the end
            self.frames.append(frame_object)
            new_index = len(self.frames) - 1
        else:
            # Insert at the specified index
            self.frames.insert(at_index, frame_object)
            new_index = at_index
        
        # After adding, set current edit frame to the newly added one
        self.set_current_edit_frame_index(new_index) # This emits current_edit_frame_changed
        self.frames_changed.emit() # This signals timeline to update its display
        print(f"DEBUG Model._add_frame_internal: New index: {new_index}, Frame count after add: {len(self.frames)}") # ADD THIS
        return new_index

    def add_blank_frame(self, at_index: int = None) -> int:
        print("DEBUG Model.add_blank_frame: Called") # ADD THIS
        self._push_undo_state()
        new_frame = AnimationFrame() # Default constructor creates a blank frame
        result_index = self._add_frame_internal(new_frame, at_index)
        self._mark_modified()
        return result_index

    def duplicate_frames_at_indices(self, indices_to_duplicate: list[int]) -> list[int]:
        if not indices_to_duplicate or not self.frames:
            return []

        # Sort indices to process them in order, and remove duplicates
        sorted_unique_indices = sorted(list(set(indices_to_duplicate)))

        frames_to_add_copies = []
        for index_val in sorted_unique_indices:
            if 0 <= index_val < len(self.frames):
                frame_to_copy = self.frames[index_val]
                # Create a deep copy of the colors for the new AnimationFrame
                copied_colors = list(frame_to_copy.get_all_colors()) # Ensures a new list instance
                frames_to_add_copies.append(AnimationFrame(colors=copied_colors))
            # else:
                # print(f"DEBUG SM DFAI (dup): Index {index_val} out of bounds for duplication.")

        if not frames_to_add_copies:
            return []

        self._push_undo_state() 

        # Determine the insertion point: after the last item in the original selection block
        valid_original_indices = [idx for idx in sorted_unique_indices if 0 <= idx < len(self.frames)]
        if not valid_original_indices: 
            if self._undo_stack: self._undo_stack.pop() 
            return []

        insertion_point_index = max(valid_original_indices) + 1
        newly_created_indices = []

        for i, new_frame_copy in enumerate(frames_to_add_copies):
            actual_insert_index = insertion_point_index + i
            # self.frames.insert will handle bounds correctly if actual_insert_index > len(self.frames) by appending
            self.frames.insert(actual_insert_index, new_frame_copy)
            newly_created_indices.append(actual_insert_index)
        
        if newly_created_indices:
            # Set current edit frame to the first of the newly duplicated frames
            self.set_current_edit_frame_index(min(newly_created_indices)) # This emits signals
            self.frames_changed.emit()
            self._mark_modified()
        else: 
            if self._undo_stack: self._undo_stack.pop()

        return newly_created_indices

    def delete_frames_at_indices(self, indices_to_delete: list[int]) -> bool:
        if not indices_to_delete or not self.frames:
            return False

        # Sort indices in descending order to avoid shifting issues during deletion
        # Also remove duplicates to process each index only once.
        sorted_indices_desc = sorted(list(set(indices_to_delete)), reverse=True)

        valid_deletions_occurred = False
        self._push_undo_state()

        original_edit_index_at_start = self._current_edit_frame_index
        current_edit_index_tracker = self._current_edit_frame_index # Will be adjusted

        for index_val in sorted_indices_desc:
            if 0 <= index_val < len(self.frames):
                del self.frames[index_val]
                valid_deletions_occurred = True
                # Adjust current_edit_index_tracker if the deleted item affects its position
                if current_edit_index_tracker == index_val:
                    current_edit_index_tracker = -1 # Mark that the selected item was deleted
                elif current_edit_index_tracker > index_val:
                    current_edit_index_tracker -= 1
            # else:
                # print(f"DEBUG SM DFAI (del): Index {index_val} out of bounds for deletion.")


        if not valid_deletions_occurred:
            if self._undo_stack: self._undo_stack.pop() # Pop undo if nothing actually changed
            return False

        # Determine the new current_edit_frame_index
        new_potential_edit_index = -1
        if not self.frames:
            new_potential_edit_index = -1
        elif current_edit_index_tracker != -1 and 0 <= current_edit_index_tracker < len(self.frames):
            # If the tracked original selection (after adjustments) is still valid
            new_potential_edit_index = current_edit_index_tracker
        else:
            # Original selection was deleted or list is now shorter.
            # Try to select the item at the position of the *first* item that was intended for deletion
            # from the original (ascending) input list.
            if indices_to_delete: # Ensure there was something intended for deletion
                # Use the smallest index from the original, unsorted input list for consistency.
                min_original_deleted_index_from_input = min(indices_to_delete)
                if min_original_deleted_index_from_input < len(self.frames):
                    new_potential_edit_index = min_original_deleted_index_from_input
                elif self.frames: # If list not empty, select last item
                    new_potential_edit_index = len(self.frames) - 1
                # else: list is empty, new_potential_edit_index remains -1
            elif self.frames: # Should not be reached if indices_to_delete was empty, but defensive
                 new_potential_edit_index = len(self.frames) - 1
            # else: list is empty, new_potential_edit_index remains -1
        
        # print(f"DEBUG SM DFAI: original_edit_index_at_start: {original_edit_index_at_start}, current_edit_index_tracker (after deletes): {current_edit_index_tracker}, new_potential_edit_index: {new_potential_edit_index}")
        
        self.set_current_edit_frame_index(new_potential_edit_index) # Emits signals
        self.frames_changed.emit()
        self._mark_modified()
        return True

    def paste_frames(self, frames_to_paste: list[AnimationFrame], at_index: int) -> list[int]:
        """
        Pastes copies of the provided AnimationFrame objects into the sequence.
        Args:
            frames_to_paste: A list of AnimationFrame objects to paste.
            at_index: The index at which to start inserting the pasted frames.
                      If out of bounds, frames will be appended.
        Returns:
            A list of indices where the new frames were inserted.
        """
        if not frames_to_paste:
            return []

        self._push_undo_state()

        # Create deep copies of the frames from the clipboard to ensure they are independent
        copied_frames_for_pasting = []
        for frame_to_copy in frames_to_paste:
            if isinstance(frame_to_copy, AnimationFrame):
                # AnimationFrame constructor already takes care of copying the 'colors' list
                copied_frames_for_pasting.append(AnimationFrame(colors=frame_to_copy.get_all_colors()))
            # else:
                # print(f"Warning: Item in frames_to_paste is not an AnimationFrame: {type(frame_to_copy)}")

        if not copied_frames_for_pasting: # Should not happen if frames_to_paste was valid
            if self._undo_stack: self._undo_stack.pop()
            return []

        # Validate at_index, default to appending if out of range
        if not (0 <= at_index <= len(self.frames)):
            at_index = len(self.frames) 

        newly_created_indices = []
        for i, new_frame_copy in enumerate(copied_frames_for_pasting):
            actual_insert_index = at_index + i
            self.frames.insert(actual_insert_index, new_frame_copy)
            newly_created_indices.append(actual_insert_index)
        
        if newly_created_indices:
            # Set current edit frame to the first of the newly pasted frames
            self.set_current_edit_frame_index(min(newly_created_indices)) # This emits signals
            self.frames_changed.emit()
            self._mark_modified()
        else: # If for some reason no frames were actually inserted (e.g., clipboard was empty after filtering)
            if self._undo_stack: self._undo_stack.pop()

        return newly_created_indices

    def get_frame_count(self):
        return len(self.frames)

    def get_frame_colors(self, index) -> list | None: # list[str]
        if 0 <= index < len(self.frames):
            return self.frames[index].get_all_colors()
        return None

    def get_frame_object(self, index) -> AnimationFrame | None:
        if 0 <= index < len(self.frames):
            return self.frames[index]
        return None

    def get_current_edit_frame_object(self) -> AnimationFrame | None:
        return self.get_frame_object(self._current_edit_frame_index)

    def set_current_edit_frame_index(self, index: int):
        print(f"DEBUG Model: set_current_edit_frame_index CALLED with requested_index: {index}") # ADD THIS
        target_index = -1 # Default if no frames or index invalid
        if not self.frames:
            target_index = -1
        elif 0 <= index < len(self.frames):
            target_index = index
        elif self.frames: # If index is out of bounds but frames exist, select first frame
            target_index = 0 
        print(f"DEBUG Model: set_current_edit_frame_index - Old _current_edit_frame_index: {self._current_edit_frame_index}, Target new index: {target_index}") # ADD THIS
        if self._current_edit_frame_index != target_index:
            self._current_edit_frame_index = target_index
            print(f"DEBUG Model: set_current_edit_frame_index - Index CHANGED to: {self._current_edit_frame_index}. Emitting current_edit_frame_changed.") # ADD THIS
            self.current_edit_frame_changed.emit(self._current_edit_frame_index)
        else:
            print(f"DEBUG Model: set_current_edit_frame_index - Index NOT changed (was already {self._current_edit_frame_index}). Signal NOT emitted.") # ADD THIS

    def get_current_edit_frame_index(self) -> int:
        return self._current_edit_frame_index


    def update_pad_in_current_edit_frame(self, pad_index_0_63: int, color_hex: str) -> bool:
        current_frame_obj = self.get_current_edit_frame_object()
        if current_frame_obj:
            q_color = QColor(color_hex) 
            valid_hex = q_color.name() if q_color.isValid() else QColor("black").name()
            
            if current_frame_obj.get_pad_color(pad_index_0_63) != valid_hex:
                # <<< MODIFIED: _push_undo_state() is NO LONGER CALLED HERE DIRECTLY >>>
                # It's now called by begin_paint_stroke() at the start of a stroke.
                
                current_frame_obj.set_pad_color(pad_index_0_63, valid_hex)
                self.frame_content_updated.emit(self._current_edit_frame_index)
                self._mark_modified() # Still mark sequence as modified
            return True
        return False
    
    def set_name(self, name: str):
        if self.name != name:
            # self._push_undo_state() # Decide if name/property changes are on main undo stack or separate
            self.name = name
            self.properties_changed.emit()
            self._mark_modified()

    def set_frame_delay_ms(self, delay_ms: int):
        delay_ms = max(20, int(delay_ms)) # Ensure minimum delay (e.g., 20ms for 50 FPS max)
        if self.frame_delay_ms != delay_ms:
            # self._push_undo_state() # Decide for properties
            self.frame_delay_ms = delay_ms
            self.properties_changed.emit()
            self._mark_modified()

    def update_all_pads_in_current_edit_frame(self, colors_hex_list: list[str]) -> bool:
        current_frame_obj = self.get_current_edit_frame_object()
        if current_frame_obj and isinstance(colors_hex_list, list) and len(colors_hex_list) == 64:
            changed = False
            new_colors_normalized = []
            for i, hex_color in enumerate(colors_hex_list):
                q_color = QColor(hex_color) # Ensure QColor is imported at the top of model.py
                normalized_hex = q_color.name() if q_color.isValid() else QColor("black").name()
                new_colors_normalized.append(normalized_hex)
                # Directly access AnimationFrame.colors for comparison
                if i < len(current_frame_obj.colors) and current_frame_obj.colors[i] != normalized_hex:
                    changed = True
                elif i >= len(current_frame_obj.colors): # Should not happen if frame.colors is always 64
                    changed = True 
            
            if changed:
                self._push_undo_state()
                current_frame_obj.colors = new_colors_normalized # Assign the whole new list
                self.frame_content_updated.emit(self._current_edit_frame_index)
                self._mark_modified()
            return True
        return False

    def clear_pads_in_current_edit_frame(self):
        current_frame_obj = self.get_current_edit_frame_object()
        if current_frame_obj:
            blank_colors = [QColor("black").name()] * 64 # Ensure QColor is imported
            if current_frame_obj.colors != blank_colors: # Check if already blank
                self._push_undo_state()
                current_frame_obj.colors = blank_colors # Assign the blank list
                self.frame_content_updated.emit(self._current_edit_frame_index)
                self._mark_modified()
            return True
        return False
            
    # --- Playback Methods ---
    def start_playback(self, start_index: int = None):
        if self.get_frame_count() > 0:
            self._is_playing = True
            if start_index is not None and 0 <= start_index < self.get_frame_count():
                self._playback_frame_index = start_index
            # If start_index is not provided or invalid, playback continues from current _playback_frame_index
            # or starts from 0 if it was reset (e.g., by stop_playback)
            self.playback_state_changed.emit(True)
            return True
        self.playback_state_changed.emit(False) # Ensure state is correct if playback cannot start
        return False

    def pause_playback(self):
        if self._is_playing:
            self._is_playing = False
            self.playback_state_changed.emit(False)

    def stop_playback(self):
        # Stop playback and reset playback index to 0
        if self._is_playing or self._playback_frame_index != 0: # Check if change is needed
            self._is_playing = False
            self._playback_frame_index = 0 
            self.playback_state_changed.emit(False)

    def get_is_playing(self) -> bool:
        return self._is_playing

    def get_current_playback_frame_index(self) -> int:
        """Returns the index of the frame that *will be* played next or *is currently* displayed during pause."""
        return self._playback_frame_index

    def step_and_get_playback_frame_colors(self) -> list | None: # list[str]
        if not self._is_playing or self.get_frame_count() == 0:
            self.stop_playback() # Ensure consistency
            return None

        colors = self.get_frame_colors(self._playback_frame_index)
        if colors is None: # Should not happen if frame count > 0 and index is managed
            self.stop_playback()
            return None
        
        # Advance playback index for the *next* call
        self._playback_frame_index += 1
        if self._playback_frame_index >= self.get_frame_count():
            if self.loop:
                self._playback_frame_index = 0
            else:
                # Reached end, not looping. Playback will stop after this frame is processed by caller.
                # We set _is_playing to False here, so get_is_playing() will be False on next check.
                self._is_playing = False 
                # The playback_state_changed signal will be emitted by the timer loop in MainWindow
                # or by the next call to start/stop/pause.

        return colors

    # --- Serialization ---
    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "frame_delay_ms": self.frame_delay_ms,
            "loop": self.loop,
            "frames": [frame.get_all_colors() for frame in self.frames] # Store list of hex colors
        }

    @classmethod
    def from_dict(cls, data: dict, name_override: str = None) -> 'SequenceModel':
        name_to_use = name_override if name_override else data.get("name", "Untitled Sequence")
        model = cls(name=name_to_use)
        model.description = data.get("description", "")
        model.frame_delay_ms = data.get("frame_delay_ms", DEFAULT_FRAME_DELAY_MS)
        model.loop = data.get("loop", True)
        
        loaded_frames_data = data.get("frames", [])
        for frame_colors_hex_list in loaded_frames_data:
            if isinstance(frame_colors_hex_list, list) and len(frame_colors_hex_list) == 64:
                # Validate each color string in the list
                valid_frame_colors = []
                for hex_color in frame_colors_hex_list:
                    qc = QColor(hex_color)
                    valid_frame_colors.append(qc.name() if qc.isValid() else QColor("black").name())
                model.frames.append(AnimationFrame(colors=valid_frame_colors))
            # else: print("Warning: Invalid frame data in from_dict, skipping frame.")

        if model.frames:
            model._current_edit_frame_index = 0
        else:
            model._current_edit_frame_index = -1
        
        model.is_modified = False # Freshly loaded from dict is not modified from that dict's state
        return model

    def load_from_file(self, filepath: str) -> bool:
        try:
            with open(filepath, "r") as f:
                data = json.load(f)
            
            # Basic validation of top-level keys
            if not all(k in data for k in ["name", "frames"]) or not isinstance(data["frames"], list):
                # print(f"SequenceModel: File {filepath} missing 'name' or 'frames' list or 'frames' is not a list.")
                return False

            # Use filename as a fallback for name if not in JSON, or override with filename-derived name
            filename_name = os.path.splitext(os.path.basename(filepath))[0].replace("_", " ").replace("-", " ")
            self.name = data.get("name", filename_name) # Prefer name from file, fallback to filename
            self.description = data.get("description", "")
            self.frame_delay_ms = data.get("frame_delay_ms", DEFAULT_FRAME_DELAY_MS)
            self.loop = data.get("loop", True)
            
            self.frames.clear() # Clear existing frames
            loaded_frames_data = data.get("frames", [])
            for frame_idx, frame_colors_hex_list in enumerate(loaded_frames_data):
                if isinstance(frame_colors_hex_list, list) and len(frame_colors_hex_list) == 64:
                    valid_frame_colors = []
                    for color_idx, hex_color in enumerate(frame_colors_hex_list):
                        if not isinstance(hex_color, str): # Ensure hex_color is a string
                            # print(f"SequenceModel Warning: Invalid color type (expected str) at frame {frame_idx}, color {color_idx} in {filepath}. Using black.")
                            hex_color = "#000000" # Default to black if type is wrong
                        qc = QColor(hex_color)
                        valid_frame_colors.append(qc.name() if qc.isValid() else QColor("black").name())
                    self.frames.append(AnimationFrame(colors=valid_frame_colors))
                # else:
                    # print(f"SequenceModel Warning: Invalid frame data (not list of 64) at frame {frame_idx} in {filepath}. Skipping frame.")

            self._undo_stack.clear() # Reset undo/redo history for newly loaded sequence
            self._redo_stack.clear()
            self._current_edit_frame_index = 0 if self.frames else -1 # Select first frame or none
            
            self.loaded_filepath = filepath
            self.is_modified = False # Freshly loaded is not modified relative to the file
            
            # print(f"SequenceModel: Sequence '{self.name}' loaded from {filepath}, Frames: {len(self.frames)}")
            self.frames_changed.emit()
            self.properties_changed.emit()
            self.current_edit_frame_changed.emit(self._current_edit_frame_index)
            return True
        except json.JSONDecodeError as e:
            # print(f"SequenceModel: JSON Decode Error loading sequence from {filepath}: {e}")
            pass
        except Exception as e:
            # print(f"SequenceModel: General Error loading sequence from {filepath}: {e}")
            pass
        
        # If loading failed, reset to a clean state or ensure partial load doesn't corrupt
        self.loaded_filepath = None
        self.is_modified = False # Or True if you want to prompt save for a failed load attempt
        return False

    def save_to_file(self, filepath: str) -> bool:
        try:
            data_to_save = self.to_dict()
            # Ensure the name in the data matches the current model name, especially if it was changed
            # after a load or if saving a "New Sequence" for the first time.
            # self.to_dict() already uses self.name.
            
            with open(filepath, "w") as f:
                json.dump(data_to_save, f, indent=4)
            
            self.loaded_filepath = filepath # Update loaded path
            self.is_modified = False      # Successfully saved, no longer modified from file
            # print(f"SequenceModel: Sequence '{self.name}' saved to {filepath}")
            
            # Emit properties_changed in case the name was formally set (e.g. from "New Sequence")
            # and needs to be reflected in UI (like a combo box managed by SequenceFileManager)
            self.properties_changed.emit()
            return True
        except Exception as e:
            # print(f"SequenceModel: Error saving sequence to {filepath}: {e}")
            return False

    def clear_all_frames(self):
        """Clears all frames from the sequence."""
        if not self.frames: # No frames to clear
            return

        self._push_undo_state()
        self.frames.clear()
        self.set_current_edit_frame_index(-1) # No frame selected
        self.frames_changed.emit()
        self._mark_modified()