# AKAI_Fire_RGB_Controller/animator/model.py
import json
import os
import copy
from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtGui import QColor

DEFAULT_FRAME_DELAY_MS = 200 # Default 5 FPS
MAX_UNDO_STEPS = 50

class AnimationFrame:
    """Represents a single frame's color data for all pads."""
    def __init__(self, colors=None): # colors is a list of 64 hex strings
        if colors and isinstance(colors, list) and len(colors) == 64:
            self.colors = list(colors) # Store a copy
        else:
            # Ensure all default colors are valid hex strings
            self.colors = [QColor("black").name()] * 64

    def set_pad_color(self, pad_index, color_hex: str):
        if 0 <= pad_index < 64:
            # Ensure saved color is in #RRGGBB format
            q_color = QColor(color_hex)
            if q_color.isValid():
                self.colors[pad_index] = q_color.name()
            else: # Fallback for invalid color string
                self.colors[pad_index] = QColor("black").name()

    def get_pad_color(self, pad_index):
        if 0 <= pad_index < 64:
            return self.colors[pad_index]
        return QColor("black").name()

    def get_all_colors(self) -> list: # Explicitly list of strings
        return list(self.colors)

    def __eq__(self, other):
        if isinstance(other, AnimationFrame):
            return self.colors == other.colors
        return False

class SequenceModel(QObject):
    """Manages sequence data (frames), properties, and undo/redo."""
    frames_changed = pyqtSignal()
    frame_content_updated = pyqtSignal(int)
    current_edit_frame_changed = pyqtSignal(int)
    properties_changed = pyqtSignal()
    playback_state_changed = pyqtSignal(bool) # True if playing, False if stopped/paused

    def __init__(self, name="New Sequence", parent=None):
        super().__init__(parent)
        self.name = name
        self.description = "A cool sequence of pad layouts."
        self.frame_delay_ms = DEFAULT_FRAME_DELAY_MS
        self.loop = True
        
        self.frames = [] # List of AnimationFrame objects
        self._current_edit_frame_index = -1 

        self._undo_stack = []
        self._redo_stack = []

        # Playback related attributes
        self._is_playing = False
        self._playback_frame_index = 0 # Current index for playback stepping

        self.loaded_filepath = None # Store path if loaded from file

    def _push_undo_state(self):
        if len(self._undo_stack) >= MAX_UNDO_STEPS:
            self._undo_stack.pop(0)
        
        frames_copy = [AnimationFrame(colors=frame.get_all_colors()) for frame in self.frames]
        self._undo_stack.append({
            "frames": frames_copy,
            "current_edit_frame_index": self._current_edit_frame_index,
            "name": self.name, # Also track name for undo/redo if it changes
            "frame_delay_ms": self.frame_delay_ms
        })
        self._redo_stack.clear()

    def _apply_state(self, state_dict):
        self.frames = state_dict["frames"]
        self.name = state_dict.get("name", self.name)
        self.frame_delay_ms = state_dict.get("frame_delay_ms", self.frame_delay_ms)

        new_edit_index = state_dict["current_edit_frame_index"]
        if not self.frames:
            self._current_edit_frame_index = -1
        elif not (0 <= new_edit_index < len(self.frames)):
             self._current_edit_frame_index = 0 if self.frames else -1
        else:
            self._current_edit_frame_index = new_edit_index

        self.frames_changed.emit()
        self.properties_changed.emit() # Name or delay might have changed
        self.current_edit_frame_changed.emit(self._current_edit_frame_index)
        # if self._current_edit_frame_index != -1: # This was possibly too broad
        #     self.frame_content_updated.emit(self._current_edit_frame_index)


    def undo(self):
        if not self._undo_stack: return False
        
        current_frames_copy = [AnimationFrame(colors=frame.get_all_colors()) for frame in self.frames]
        self._redo_stack.append({
            "frames": current_frames_copy,
            "current_edit_frame_index": self._current_edit_frame_index,
            "name": self.name,
            "frame_delay_ms": self.frame_delay_ms
        })

        previous_state = self._undo_stack.pop()
        self._apply_state(previous_state)
        return True

    def redo(self):
        if not self._redo_stack: return False

        current_frames_copy = [AnimationFrame(colors=frame.get_all_colors()) for frame in self.frames]
        self._undo_stack.append({
            "frames": current_frames_copy,
            "current_edit_frame_index": self._current_edit_frame_index,
            "name": self.name,
            "frame_delay_ms": self.frame_delay_ms
        })
        if len(self._undo_stack) > MAX_UNDO_STEPS: self._undo_stack.pop(0)

        redone_state = self._redo_stack.pop()
        self._apply_state(redone_state)
        return True

    def add_frame_snapshot(self, snapshot_colors, at_index=None):
        self._push_undo_state()
        return self._add_frame_internal(AnimationFrame(colors=snapshot_colors), at_index)

    def add_blank_frame(self, at_index=None):
        self._push_undo_state()
        return self._add_frame_internal(AnimationFrame(), at_index)

    def duplicate_selected_frame(self):
        if not (0 <= self._current_edit_frame_index < len(self.frames)):
            return -1
        
        self._push_undo_state()
        frame_to_copy = self.frames[self._current_edit_frame_index]
        new_frame_colors = list(frame_to_copy.get_all_colors())
        return self._add_frame_internal(AnimationFrame(colors=new_frame_colors), self._current_edit_frame_index + 1)

    def _add_frame_internal(self, frame_object: AnimationFrame, at_index=None):
        if at_index is None or not (0 <= at_index <= len(self.frames)):
            self.frames.append(frame_object)
            new_index = len(self.frames) - 1
        else:
            self.frames.insert(at_index, frame_object)
            new_index = at_index
        
        self.set_current_edit_frame_index(new_index)
        self.frames_changed.emit()
        return new_index

    def delete_selected_frame(self):
        if not (0 <= self._current_edit_frame_index < len(self.frames)):
            return False
        
        self._push_undo_state()
        del self.frames[self._current_edit_frame_index]
        
        new_index = -1
        if not self.frames:
            new_index = -1
        elif self._current_edit_frame_index >= len(self.frames):
            new_index = len(self.frames) - 1
        else:
            new_index = self._current_edit_frame_index
        
        self.set_current_edit_frame_index(new_index) # This will emit current_edit_frame_changed
        self.frames_changed.emit() # Also emit frames_changed for timeline update
        return True

    def get_frame_count(self):
        return len(self.frames)

    def get_frame_colors(self, index) -> list | None:
        if 0 <= index < len(self.frames):
            return self.frames[index].get_all_colors()
        return None
        
    def get_frame_object(self, index) -> AnimationFrame | None:
        """Returns the AnimationFrame object at the given index."""
        if 0 <= index < len(self.frames):
            return self.frames[index]
        return None

    def get_current_edit_frame_object(self) -> AnimationFrame | None:
        """Returns the current AnimationFrame object being edited."""
        return self.get_frame_object(self._current_edit_frame_index)

    def set_current_edit_frame_index(self, index):
        target_index = -1
        if not self.frames:
            target_index = -1
        elif 0 <= index < len(self.frames):
            target_index = index
        elif self.frames: # If index is out of bounds but frames exist, select first or last
            target_index = 0 # Default to first
            # Or: target_index = max(0, min(index, len(self.frames) -1))
        
        if self._current_edit_frame_index != target_index:
            self._current_edit_frame_index = target_index
            self.current_edit_frame_changed.emit(self._current_edit_frame_index)

    def get_current_edit_frame_index(self):
        return self._current_edit_frame_index

    def update_pad_in_current_edit_frame(self, pad_index_0_63, color_hex: str):
        current_frame_obj = self.get_current_edit_frame_object()
        if current_frame_obj:
            # Ensure color_hex is in #RRGGBB format for comparison and storage
            q_color = QColor(color_hex)
            valid_hex = QColor("black").name() # default for safety
            if q_color.isValid():
                valid_hex = q_color.name()

            if current_frame_obj.get_pad_color(pad_index_0_63) != valid_hex:
                self._push_undo_state()
                current_frame_obj.set_pad_color(pad_index_0_63, valid_hex)
                self.frame_content_updated.emit(self._current_edit_frame_index)
            return True
        return False

    def set_name(self, name):
        if self.name != name:
            # self._push_undo_state() # Decided against making name changes undoable for now to simplify
            self.name = name
            self.properties_changed.emit()

    def set_frame_delay_ms(self, delay_ms):
        delay_ms = max(20, int(delay_ms)) 
        if self.frame_delay_ms != delay_ms:
            # self._push_undo_state() # Also not making delay changes undoable via main stack for now
            self.frame_delay_ms = delay_ms
            self.properties_changed.emit()

    # --- Playback Methods ---
    def start_playback(self, start_index=None):
        if self.get_frame_count() > 0:
            self._is_playing = True
            if start_index is not None and 0 <= start_index < self.get_frame_count():
                self._playback_frame_index = start_index
            # else, it continues from where it was, or from 0 if freshly started
            self.playback_state_changed.emit(True)
            return True
        self.playback_state_changed.emit(False)
        return False

    def pause_playback(self):
        if self._is_playing:
            self._is_playing = False
            self.playback_state_changed.emit(False)

    def stop_playback(self):
        if self._is_playing or self._playback_frame_index != 0: # If it was playing or not at start
            self._is_playing = False
            self._playback_frame_index = 0 # Reset on stop
            self.playback_state_changed.emit(False)


    def get_is_playing(self) -> bool:
        return self._is_playing

    def get_current_playback_frame_index(self) -> int:
        return self._playback_frame_index

    def step_and_get_playback_frame_colors(self) -> list | None:
        """Advances playback index and returns colors for the new current playback frame."""
        if not self._is_playing or self.get_frame_count() == 0:
            self.stop_playback() # Ensure state is consistent if called inappropriately
            return None

        # Colors are for the frame we are *about to show* or *are currently on*
        # If _playback_frame_index is current, get its colors then advance.
        colors = self.get_frame_colors(self._playback_frame_index)

        if colors is None: # Should not happen if frame_count > 0 and index is managed
            self.stop_playback()
            return None

        self._playback_frame_index += 1
        if self._playback_frame_index >= self.get_frame_count():
            if self.loop:
                self._playback_frame_index = 0
            else:
                # Reached end, not looping. Stop playback.
                # The current `colors` are the last frame's. Playback will stop *after* this frame.
                self._is_playing = False # Mark as not playing for the *next* cycle
                # self.playback_state_changed.emit(False) # Emit when truly stopped
        return colors

    # --- Serialization ---
    def to_dict(self):
        return {
            "name": self.name,
            "description": self.description,
            "frame_delay_ms": self.frame_delay_ms,
            "loop": self.loop,
            "frames": [frame.get_all_colors() for frame in self.frames]
        }

    @classmethod
    def from_dict(cls, data, name_override=None):
        name_to_use = name_override if name_override else data.get("name", "Untitled Sequence")
        model = cls(name=name_to_use)
        model.description = data.get("description", "")
        model.frame_delay_ms = data.get("frame_delay_ms", DEFAULT_FRAME_DELAY_MS)
        model.loop = data.get("loop", True)
        
        loaded_frames_data = data.get("frames", [])
        for frame_colors in loaded_frames_data:
            if isinstance(frame_colors, list) and len(frame_colors) == 64:
                 # Ensure colors are valid hex before creating AnimationFrame
                valid_frame_colors = []
                for hex_color in frame_colors:
                    qc = QColor(hex_color)
                    valid_frame_colors.append(qc.name() if qc.isValid() else QColor("black").name())
                model.frames.append(AnimationFrame(colors=valid_frame_colors))
        
        if model.frames: model._current_edit_frame_index = 0
        else: model._current_edit_frame_index = -1
        return model

    def load_from_file(self, filepath):
        try:
            with open(filepath, "r") as f: data = json.load(f)
            
            filename_name = os.path.splitext(os.path.basename(filepath))[0].replace("_", " ").replace("-", " ")
            self.name = data.get("name", filename_name)
            self.description = data.get("description", "")
            self.frame_delay_ms = data.get("frame_delay_ms", DEFAULT_FRAME_DELAY_MS)
            self.loop = data.get("loop", True)
            
            self.frames.clear()
            loaded_frames_data = data.get("frames", [])
            for frame_colors in loaded_frames_data:
                if isinstance(frame_colors, list) and len(frame_colors) == 64:
                    valid_frame_colors = []
                    for hex_color in frame_colors:
                        qc = QColor(hex_color)
                        valid_frame_colors.append(qc.name() if qc.isValid() else QColor("black").name())
                    self.frames.append(AnimationFrame(colors=valid_frame_colors))
            
            self._undo_stack.clear(); self._redo_stack.clear()
            self._current_edit_frame_index = 0 if self.frames else -1
            self.loaded_filepath = filepath # Store the path
            
            print(f"SequenceModel: Sequence '{self.name}' loaded from {filepath}")
            self.frames_changed.emit()
            self.properties_changed.emit()
            self.current_edit_frame_changed.emit(self._current_edit_frame_index) # Ensure UI updates
            return True
        except Exception as e:
            print(f"SequenceModel: Error loading sequence from {filepath}: {e}")
            self.loaded_filepath = None
            return False

    def save_to_file(self, filepath):
        try:
            data_to_save = self.to_dict()
            data_to_save["name"] = self.name 

            with open(filepath, "w") as f:
                json.dump(data_to_save, f, indent=4)
            self.loaded_filepath = filepath # Update path on successful save
            print(f"SequenceModel: Sequence '{self.name}' saved to {filepath}")
            return True
        except Exception as e:
            print(f"SequenceModel: Error saving sequence to {filepath}: {e}")
            return False

    def clear_all_frames(self):
        """Clears all frames and resets edit index. Pushes undo state."""
        if not self.frames: return # Nothing to clear

        self._push_undo_state()
        self.frames.clear()
        self.set_current_edit_frame_index(-1) # No frame selected
        self.frames_changed.emit()