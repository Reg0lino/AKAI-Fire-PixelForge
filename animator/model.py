# AKAI_Fire_RGB_Controller/animator/model.py
import json
import os
import copy
from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtGui import QColor # QTimer will be handled by MainWindow or a dedicated playback controller

DEFAULT_FRAME_DELAY_MS = 200 # Default 5 FPS
MAX_UNDO_STEPS = 50

class AnimationFrame: # Sticking with AnimationFrame as it clearly describes its content
    """Represents a single frame's color data for all pads."""
    def __init__(self, colors=None): # colors is a list of 64 hex strings
        if colors and isinstance(colors, list) and len(colors) == 64:
            self.colors = list(colors) # Store a copy
        else:
            self.colors = [QColor("black").name()] * 64

    def set_pad_color(self, pad_index, color_hex: str):
        if 0 <= pad_index < 64:
            self.colors[pad_index] = color_hex

    def get_pad_color(self, pad_index):
        if 0 <= pad_index < 64:
            return self.colors[pad_index]
        return QColor("black").name()

    def get_all_colors(self):
        return list(self.colors)

    def __eq__(self, other):
        if isinstance(other, AnimationFrame):
            return self.colors == other.colors
        return False

class SequenceModel(QObject):
    """Manages sequence data (frames), properties, and undo/redo."""
    frames_changed = pyqtSignal() # Emitted when frame list structure changes
    frame_content_updated = pyqtSignal(int) # Emitted when a specific frame's content changes (index)
    current_edit_frame_changed = pyqtSignal(int) # Emitted when active editing frame changes
    properties_changed = pyqtSignal() # For name, delay changes

    def __init__(self, name="New Sequence", parent=None):
        super().__init__(parent)
        self.name = name
        self.description = "A cool sequence of pad layouts."
        self.frame_delay_ms = DEFAULT_FRAME_DELAY_MS
        self.loop = True # Always looping for now
        
        self.frames = [] # List of AnimationFrame objects
        self._current_edit_frame_index = -1 

        self._undo_stack = []
        self._redo_stack = []

    def _push_undo_state(self):
        if len(self._undo_stack) >= MAX_UNDO_STEPS:
            self._undo_stack.pop(0)
        
        frames_copy = [AnimationFrame(colors=frame.get_all_colors()) for frame in self.frames]
        self._undo_stack.append({
            "frames": frames_copy,
            "current_edit_frame_index": self._current_edit_frame_index
            # Could also store frame_delay_ms if that becomes undoable
        })
        self._redo_stack.clear()
        # print(f"DEBUG (SequenceModel): Pushed undo state. Stack size: {len(self._undo_stack)}")

    def _apply_state(self, state_dict):
        self.frames = state_dict["frames"]
        # Ensure current_edit_frame_index is valid after state change
        new_edit_index = state_dict["current_edit_frame_index"]
        if not self.frames: # No frames
            self._current_edit_frame_index = -1
        elif new_edit_index >= len(self.frames) or new_edit_index < 0 : # Index out of bounds
             self._current_edit_frame_index = 0 # Default to first frame
        else:
            self._current_edit_frame_index = new_edit_index

        self.frames_changed.emit()
        self.current_edit_frame_changed.emit(self._current_edit_frame_index)
        if self._current_edit_frame_index != -1:
            self.frame_content_updated.emit(self._current_edit_frame_index)


    def undo(self):
        if not self._undo_stack: return False
        
        current_frames_copy = [AnimationFrame(colors=frame.get_all_colors()) for frame in self.frames]
        self._redo_stack.append({
            "frames": current_frames_copy,
            "current_edit_frame_index": self._current_edit_frame_index
        })

        previous_state = self._undo_stack.pop()
        self._apply_state(previous_state)
        # print(f"DEBUG (SequenceModel): Undone.")
        return True

    def redo(self):
        if not self._redo_stack: return False

        current_frames_copy = [AnimationFrame(colors=frame.get_all_colors()) for frame in self.frames]
        self._undo_stack.append({
            "frames": current_frames_copy,
            "current_edit_frame_index": self._current_edit_frame_index
        })
        if len(self._undo_stack) > MAX_UNDO_STEPS: self._undo_stack.pop(0)

        redone_state = self._redo_stack.pop()
        self._apply_state(redone_state)
        # print(f"DEBUG (SequenceModel): Redone.")
        return True

    def add_frame_snapshot(self, snapshot_colors, at_index=None): # snapshot_colors = list of 64 hex
        self._push_undo_state()
        return self._add_frame_internal(AnimationFrame(colors=snapshot_colors), at_index)

    def add_blank_frame(self, at_index=None):
        self._push_undo_state()
        return self._add_frame_internal(AnimationFrame(), at_index) # Default AnimationFrame is blank

    def duplicate_selected_frame(self):
        if self._current_edit_frame_index < 0 or self._current_edit_frame_index >= len(self.frames):
            return -1 # No frame selected or invalid index
        
        self._push_undo_state()
        frame_to_copy = self.frames[self._current_edit_frame_index]
        new_frame_colors = list(frame_to_copy.get_all_colors()) # Get a copy of colors
        # Insert after the current frame
        return self._add_frame_internal(AnimationFrame(colors=new_frame_colors), self._current_edit_frame_index + 1)

    def _add_frame_internal(self, frame_object: AnimationFrame, at_index=None):
        """Internal method to add a pre-constructed AnimationFrame object."""
        if at_index is None or not (0 <= at_index <= len(self.frames)):
            self.frames.append(frame_object)
            new_index = len(self.frames) - 1
        else:
            self.frames.insert(at_index, frame_object)
            new_index = at_index
        
        self.set_current_edit_frame_index(new_index) # Select the new frame
        self.frames_changed.emit() # Signal that the list of frames has changed
        return new_index


    def delete_selected_frame(self):
        if self._current_edit_frame_index < 0 or self._current_edit_frame_index >= len(self.frames):
            return False # No frame selected or invalid index
        
        self._push_undo_state()
        del self.frames[self._current_edit_frame_index]
        
        new_index = -1
        if not self.frames:
            new_index = -1
        elif self._current_edit_frame_index >= len(self.frames): # Was last frame
            new_index = len(self.frames) - 1
        else: # A frame in the middle or beginning
            new_index = self._current_edit_frame_index # Stays on the one that shifted into this position
        
        self.set_current_edit_frame_index(new_index)
        self.frames_changed.emit()
        return True


    def get_frame_count(self):
        return len(self.frames)

    def get_frame_colors(self, index) -> list | None: # Returns list of 64 hex strings
        if 0 <= index < len(self.frames):
            return self.frames[index].get_all_colors()
        return None

    def set_current_edit_frame_index(self, index):
        if not self.frames: # No frames, ensure index is -1
            index = -1
        elif not (-1 <= index < len(self.frames)): # Invalid index for current frames
            print(f"Warning (SequenceModel): Attempt to set invalid edit frame index {index} for {len(self.frames)} frames. Defaulting.")
            index = 0 # Default to first frame if invalid but frames exist

        if self._current_edit_frame_index != index:
            self._current_edit_frame_index = index
            self.current_edit_frame_changed.emit(index)

    def get_current_edit_frame_index(self):
        return self._current_edit_frame_index

    def update_pad_in_current_edit_frame(self, pad_index_0_63, color_hex: str):
        current_frame = self.get_frame(self._current_edit_frame_index)
        if current_frame:
            if current_frame.get_pad_color(pad_index_0_63) != color_hex: # Only update if different
                self._push_undo_state() # Save state before modification
                current_frame.set_pad_color(pad_index_0_63, color_hex)
                self.frame_content_updated.emit(self._current_edit_frame_index)
            return True
        return False

    def set_name(self, name):
        if self.name != name:
            self.name = name; self.properties_changed.emit()

    def set_frame_delay_ms(self, delay_ms):
        delay_ms = max(20, int(delay_ms)) 
        if self.frame_delay_ms != delay_ms:
            self.frame_delay_ms = delay_ms; self.properties_changed.emit()

    def to_dict(self):
        return {
            "name": self.name,
            "description": self.description,
            "frame_delay_ms": self.frame_delay_ms,
            "loop": self.loop,
            "frames": [frame.get_all_colors() for frame in self.frames]
        }

    @classmethod
    def from_dict(cls, data, name_override=None): # Allow name override from filename
        name_to_use = name_override if name_override else data.get("name", "Untitled Sequence")
        model = cls(name=name_to_use)
        model.description = data.get("description", "")
        model.frame_delay_ms = data.get("frame_delay_ms", DEFAULT_FRAME_DELAY_MS)
        model.loop = data.get("loop", True)
        
        loaded_frames_data = data.get("frames", [])
        for frame_colors in loaded_frames_data:
            if isinstance(frame_colors, list) and len(frame_colors) == 64:
                model.frames.append(AnimationFrame(colors=frame_colors))
        
        if model.frames: model._current_edit_frame_index = 0
        return model

    def load_from_file(self, filepath):
        try:
            with open(filepath, "r") as f: data = json.load(f)
            
            # Extract filename as default name if not in JSON
            filename_name = os.path.splitext(os.path.basename(filepath))[0].replace("_", " ")

            self.name = data.get("name", filename_name)
            self.description = data.get("description", "")
            self.frame_delay_ms = data.get("frame_delay_ms", DEFAULT_FRAME_DELAY_MS)
            self.loop = data.get("loop", True)
            
            self.frames.clear()
            loaded_frames_data = data.get("frames", [])
            for frame_colors in loaded_frames_data:
                if isinstance(frame_colors, list) and len(frame_colors) == 64:
                    self.frames.append(AnimationFrame(colors=frame_colors))
            
            self._undo_stack.clear(); self._redo_stack.clear()
            self._current_edit_frame_index = 0 if self.frames else -1
            
            print(f"Sequence '{self.name}' loaded from {filepath}")
            self.frames_changed.emit()
            self.properties_changed.emit()
            self.current_edit_frame_changed.emit(self._current_edit_frame_index)
            return True
        except Exception as e:
            print(f"Error loading sequence from {filepath}: {e}")
            return False

    def save_to_file(self, filepath):
        try:
            # Ensure the name in the data matches the filename expectation if desired,
            # or just use the model's current name.
            data_to_save = self.to_dict()
            data_to_save["name"] = self.name # Ensure current model name is saved

            with open(filepath, "w") as f:
                json.dump(data_to_save, f, indent=4)
            print(f"Sequence '{self.name}' saved to {filepath}")
            return True
        except Exception as e:
            print(f"Error saving sequence to {filepath}: {e}")
            return False