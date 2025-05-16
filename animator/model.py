# AKAI_Fire_RGB_Controller/animator/model.py
import json
import os
import copy
from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtGui import QColor

DEFAULT_FRAME_DELAY_MS = 200 
MAX_UNDO_STEPS = 50

class AnimationFrame:
    def __init__(self, colors=None): 
        if colors and isinstance(colors, list) and len(colors) == 64:
            self.colors = list(colors) 
        else:
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
        return list(self.colors)

    def __eq__(self, other):
        if isinstance(other, AnimationFrame):
            return self.colors == other.colors
        return False

class SequenceModel(QObject):
    frames_changed = pyqtSignal()
    frame_content_updated = pyqtSignal(int)
    current_edit_frame_changed = pyqtSignal(int)
    properties_changed = pyqtSignal()
    playback_state_changed = pyqtSignal(bool)

    def __init__(self, name="New Sequence", parent=None):
        super().__init__(parent)
        self.name = name
        self.description = "A cool sequence of pad layouts."
        self.frame_delay_ms = DEFAULT_FRAME_DELAY_MS
        self.loop = True
        
        self.frames = [] 
        self._current_edit_frame_index = -1 

        self._undo_stack = []
        self._redo_stack = []

        self._is_playing = False
        self._playback_frame_index = 0

        self.loaded_filepath = None
        self.is_modified = False # NEW: Flag to track unsaved changes

    def _mark_modified(self):
        """Sets the modified flag to True."""
        if not self.is_modified:
            self.is_modified = True
            # print(f"DEBUG: SequenceModel '{self.name}' marked as modified.") # Optional debug

    def _push_undo_state(self):
        if len(self.frames) == 0 and not self._undo_stack : # Don't push initial empty state if nothing to undo yet
             # Or, only push if there was a previous state in undo_stack, signifying an actual change from a non-empty state
            pass # Or consider if an initial "blank" state should be pushable for an undo to "new"

        # Only mark modified if an actual change is being recorded for undo
        # This is tricky because _push_undo_state is called *before* the change.
        # The methods calling _push_undo_state should call _mark_modified *after* making the change.
        # However, for simplicity, let's assume any operation that warrants an undo also modifies.
        # self._mark_modified() # Let's move this to individual action methods

        if len(self._undo_stack) >= MAX_UNDO_STEPS:
            self._undo_stack.pop(0)
        
        frames_copy = [AnimationFrame(colors=frame.get_all_colors()) for frame in self.frames]
        self._undo_stack.append({
            "frames": frames_copy,
            "current_edit_frame_index": self._current_edit_frame_index,
            "name": self.name,
            "frame_delay_ms": self.frame_delay_ms
        })
        self._redo_stack.clear()

    def _apply_state(self, state_dict):
        self.frames = state_dict["frames"]
        self.name = state_dict.get("name", self.name) # Name change during undo/redo IS a modification
        self.frame_delay_ms = state_dict.get("frame_delay_ms", self.frame_delay_ms) # Also a modification

        new_edit_index = state_dict["current_edit_frame_index"]
        if not self.frames: self._current_edit_frame_index = -1
        elif not (0 <= new_edit_index < len(self.frames)): self._current_edit_frame_index = 0 if self.frames else -1
        else: self._current_edit_frame_index = new_edit_index

        self.frames_changed.emit()
        self.properties_changed.emit()
        self.current_edit_frame_changed.emit(self._current_edit_frame_index)
        self._mark_modified() # Applying an undo/redo state means it's now different from saved

    def undo(self):
        if not self._undo_stack: return False
        # Current state becomes a redo state
        current_frames_copy = [AnimationFrame(colors=frame.get_all_colors()) for frame in self.frames]
        self._redo_stack.append({
            "frames": current_frames_copy, "current_edit_frame_index": self._current_edit_frame_index,
            "name": self.name, "frame_delay_ms": self.frame_delay_ms
        })
        previous_state = self._undo_stack.pop()
        self._apply_state(previous_state) # _apply_state will call _mark_modified
        return True

    def redo(self):
        if not self._redo_stack: return False
        # Current state becomes an undo state
        current_frames_copy = [AnimationFrame(colors=frame.get_all_colors()) for frame in self.frames]
        self._undo_stack.append({
            "frames": current_frames_copy, "current_edit_frame_index": self._current_edit_frame_index,
            "name": self.name, "frame_delay_ms": self.frame_delay_ms
        })
        if len(self._undo_stack) > MAX_UNDO_STEPS: self._undo_stack.pop(0)
        redone_state = self._redo_stack.pop()
        self._apply_state(redone_state) # _apply_state will call _mark_modified
        return True

    def add_frame_snapshot(self, snapshot_colors, at_index=None):
        self._push_undo_state()
        result_index = self._add_frame_internal(AnimationFrame(colors=snapshot_colors), at_index)
        self._mark_modified()
        return result_index

    def add_blank_frame(self, at_index=None):
        self._push_undo_state()
        result_index = self._add_frame_internal(AnimationFrame(), at_index)
        self._mark_modified()
        return result_index

    def duplicate_selected_frame(self):
        if not (0 <= self._current_edit_frame_index < len(self.frames)): return -1
        self._push_undo_state()
        frame_to_copy = self.frames[self._current_edit_frame_index]
        new_frame_colors = list(frame_to_copy.get_all_colors())
        result_index = self._add_frame_internal(AnimationFrame(colors=new_frame_colors), self._current_edit_frame_index + 1)
        self._mark_modified()
        return result_index
        
    def _add_frame_internal(self, frame_object: AnimationFrame, at_index=None):
        # ... (content as before) ...
        if at_index is None or not (0 <= at_index <= len(self.frames)):
            self.frames.append(frame_object)
            new_index = len(self.frames) - 1
        else:
            self.frames.insert(at_index, frame_object)
            new_index = at_index
        self.set_current_edit_frame_index(new_index) # This emits current_edit_frame_changed
        self.frames_changed.emit() # This signals timeline to update
        return new_index


    def delete_selected_frame(self):
        if not (0 <= self._current_edit_frame_index < len(self.frames)): return False
        self._push_undo_state()
        del self.frames[self._current_edit_frame_index]
        new_index = -1
        if not self.frames: new_index = -1
        elif self._current_edit_frame_index >= len(self.frames): new_index = len(self.frames) - 1
        else: new_index = self._current_edit_frame_index
        self.set_current_edit_frame_index(new_index)
        self.frames_changed.emit()
        self._mark_modified()
        return True

    # ... (get_frame_count, get_frame_colors, get_frame_object, get_current_edit_frame_object as before) ...
    def get_frame_count(self): return len(self.frames)
    def get_frame_colors(self, index) -> list | None:
        if 0 <= index < len(self.frames): return self.frames[index].get_all_colors()
        return None
    def get_frame_object(self, index) -> AnimationFrame | None:
        if 0 <= index < len(self.frames): return self.frames[index]
        return None
    def get_current_edit_frame_object(self) -> AnimationFrame | None:
        return self.get_frame_object(self._current_edit_frame_index)

    def set_current_edit_frame_index(self, index):
        target_index = -1
        if not self.frames: target_index = -1
        elif 0 <= index < len(self.frames): target_index = index
        elif self.frames: target_index = 0 
        if self._current_edit_frame_index != target_index:
            self._current_edit_frame_index = target_index
            self.current_edit_frame_changed.emit(self._current_edit_frame_index)

    def get_current_edit_frame_index(self): return self._current_edit_frame_index

    def update_pad_in_current_edit_frame(self, pad_index_0_63, color_hex: str):
        current_frame_obj = self.get_current_edit_frame_object()
        if current_frame_obj:
            q_color = QColor(color_hex)
            valid_hex = q_color.name() if q_color.isValid() else QColor("black").name()
            if current_frame_obj.get_pad_color(pad_index_0_63) != valid_hex:
                self._push_undo_state()
                current_frame_obj.set_pad_color(pad_index_0_63, valid_hex)
                self.frame_content_updated.emit(self._current_edit_frame_index)
                self._mark_modified() # Pad painting is a modification
            return True
        return False

    def set_name(self, name):
        if self.name != name:
            # self._push_undo_state() # Decide if name/property changes are on main undo stack
            self.name = name
            self.properties_changed.emit()
            self._mark_modified() # Name change is a modification

    def set_frame_delay_ms(self, delay_ms):
        delay_ms = max(20, int(delay_ms)) 
        if self.frame_delay_ms != delay_ms:
            self.frame_delay_ms = delay_ms
            self.properties_changed.emit()
            self._mark_modified() # Delay change is a modification
            
    # ... (Playback Methods as before: start_playback, pause_playback, stop_playback, get_is_playing, etc.)
    def start_playback(self, start_index=None):
        if self.get_frame_count() > 0:
            self._is_playing = True
            if start_index is not None and 0 <= start_index < self.get_frame_count(): self._playback_frame_index = start_index
            self.playback_state_changed.emit(True); return True
        self.playback_state_changed.emit(False); return False
    def pause_playback(self):
        if self._is_playing: self._is_playing = False; self.playback_state_changed.emit(False)
    def stop_playback(self):
        if self._is_playing or self._playback_frame_index != 0:
            self._is_playing = False; self._playback_frame_index = 0; self.playback_state_changed.emit(False)
    def get_is_playing(self) -> bool: return self._is_playing
    def get_current_playback_frame_index(self) -> int: return self._playback_frame_index
    def step_and_get_playback_frame_colors(self) -> list | None:
        if not self._is_playing or self.get_frame_count() == 0: self.stop_playback(); return None
        colors = self.get_frame_colors(self._playback_frame_index)
        if colors is None: self.stop_playback(); return None
        self._playback_frame_index += 1
        if self._playback_frame_index >= self.get_frame_count():
            if self.loop: self._playback_frame_index = 0
            else: self._is_playing = False # Will stop after this frame
        return colors

    # --- Serialization ---
    def to_dict(self): # ... (as before)
        return {
            "name": self.name, "description": self.description, "frame_delay_ms": self.frame_delay_ms,
            "loop": self.loop, "frames": [frame.get_all_colors() for frame in self.frames]
        }

    @classmethod
    def from_dict(cls, data, name_override=None): # ... (as before)
        name_to_use = name_override if name_override else data.get("name", "Untitled Sequence")
        model = cls(name=name_to_use)
        model.description = data.get("description", ""); model.frame_delay_ms = data.get("frame_delay_ms", DEFAULT_FRAME_DELAY_MS)
        model.loop = data.get("loop", True)
        loaded_frames_data = data.get("frames", [])
        for frame_colors in loaded_frames_data:
            if isinstance(frame_colors, list) and len(frame_colors) == 64:
                valid_frame_colors = []
                for hex_color in frame_colors: qc = QColor(hex_color); valid_frame_colors.append(qc.name() if qc.isValid() else QColor("black").name())
                model.frames.append(AnimationFrame(colors=valid_frame_colors))
        if model.frames: model._current_edit_frame_index = 0
        else: model._current_edit_frame_index = -1
        model.is_modified = False # Freshly loaded from dict is not modified from that dict's state
        return model

    def load_from_file(self, filepath):
        try:
            with open(filepath, "r") as f: data = json.load(f)
            
            # Basic validation of top-level keys
            if not all(k in data for k in ["name", "frames"]) or not isinstance(data["frames"], list):
                print(f"SequenceModel: File {filepath} missing 'name' or 'frames' list.")
                return False

            filename_name = os.path.splitext(os.path.basename(filepath))[0].replace("_", " ").replace("-", " ")
            self.name = data.get("name", filename_name)
            self.description = data.get("description", "")
            self.frame_delay_ms = data.get("frame_delay_ms", DEFAULT_FRAME_DELAY_MS)
            self.loop = data.get("loop", True)
            
            self.frames.clear()
            loaded_frames_data = data.get("frames", [])
            for frame_idx, frame_colors in enumerate(loaded_frames_data):
                if isinstance(frame_colors, list) and len(frame_colors) == 64:
                    valid_frame_colors = []
                    for color_idx, hex_color in enumerate(frame_colors):
                        if not isinstance(hex_color, str): # Ensure hex_color is a string
                            print(f"SequenceModel Warning: Invalid color type (expected str) at frame {frame_idx}, color {color_idx} in {filepath}. Using black.")
                            hex_color = "#000000"
                        qc = QColor(hex_color)
                        valid_frame_colors.append(qc.name() if qc.isValid() else QColor("black").name())
                    self.frames.append(AnimationFrame(colors=valid_frame_colors))
                else:
                    print(f"SequenceModel Warning: Invalid frame data (not list of 64) at frame {frame_idx} in {filepath}. Skipping frame.")

            self._undo_stack.clear(); self._redo_stack.clear()
            self._current_edit_frame_index = 0 if self.frames else -1
            self.loaded_filepath = filepath
            self.is_modified = False # Freshly loaded is not modified
            
            print(f"SequenceModel: Sequence '{self.name}' loaded from {filepath}, Frames: {len(self.frames)}")
            self.frames_changed.emit()
            self.properties_changed.emit()
            self.current_edit_frame_changed.emit(self._current_edit_frame_index)
            return True
        except json.JSONDecodeError as e:
            print(f"SequenceModel: JSON Decode Error loading sequence from {filepath}: {e}")
        except Exception as e:
            print(f"SequenceModel: General Error loading sequence from {filepath}: {e}")
        self.loaded_filepath = None; self.is_modified = False
        return False

    def save_to_file(self, filepath):
        try:
            data_to_save = self.to_dict()
            # data_to_save["name"] = self.name # to_dict() already includes name
            with open(filepath, "w") as f: json.dump(data_to_save, f, indent=4)
            self.loaded_filepath = filepath
            self.is_modified = False # Successfully saved, no longer modified from file
            print(f"SequenceModel: Sequence '{self.name}' saved to {filepath}")
            return True
        except Exception as e:
            print(f"SequenceModel: Error saving sequence to {filepath}: {e}")
            return False

    def clear_all_frames(self):
        if not self.frames: return
        self._push_undo_state()
        self.frames.clear()
        self.set_current_edit_frame_index(-1)
        self.frames_changed.emit()
        self._mark_modified()