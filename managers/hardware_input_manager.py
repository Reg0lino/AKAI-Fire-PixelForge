# AKAI_Fire_RGB_Controller/managers/hardware_input_manager.py
from PyQt6.QtCore import QObject, pyqtSignal

# Define relevant Note and CC numbers for clarity
FIRE_BUTTON_PLAY = 0x33
FIRE_BUTTON_STOP = 0x34
FIRE_BUTTON_GRID_LEFT = 0x22  
FIRE_BUTTON_GRID_RIGHT = 0x23 
FIRE_ENCODER_SELECT_PRESS = 0x19
FIRE_ENCODER_SELECT_TURN_CC = 0x76

# --- CORRECTED Hardware Button Definitions for Sampler Control ---
# Using your confirmed desired mappings:
# - PERFORM button (Note 0x2F) to toggle sampler.
# - DRUM button (Note 0x2E) to cycle monitors.
HW_BUTTON_SAMPLER_TOGGLE = 0x2F  # Physical "PERFORM" button
HW_BUTTON_MONITOR_CYCLE = 0x2E   # Physical "DRUM" button
# --- END CORRECTIONS ---

class HardwareInputManager(QObject):
    # Existing signals
    request_animator_play_pause = pyqtSignal()
    request_animator_stop = pyqtSignal()
    grid_left_pressed = pyqtSignal()
    grid_right_pressed = pyqtSignal()
    select_encoder_pressed = pyqtSignal()
    select_encoder_turned = pyqtSignal(int) 

    # Signals for Sampler Control
    request_toggle_screen_sampler = pyqtSignal()
    request_cycle_sampler_monitor = pyqtSignal()
    
    def __init__(self, akai_fire_controller_ref, parent=None):
        super().__init__(parent)
        self.akai_fire_controller = akai_fire_controller_ref

        if self.akai_fire_controller:
            self.akai_fire_controller.play_button_pressed.connect(self._on_fire_play_pressed)
            self.akai_fire_controller.stop_button_pressed.connect(self._on_fire_stop_pressed)
            self.akai_fire_controller.fire_button_event.connect(self._handle_generic_button_event)
            
            if hasattr(self.akai_fire_controller, 'control_change_event'):
                 self.akai_fire_controller.control_change_event.connect(self._handle_control_change_event)
            else:
                 print("HIM WARNING: AkaiFireController does not have 'control_change_event' signal. SELECT encoder turn will not work.")
        else:
            print("HIM CRITICAL: AkaiFireController reference not provided!")

    def _on_fire_play_pressed(self):
        self.request_animator_play_pause.emit()

    def _on_fire_stop_pressed(self):
        self.request_animator_stop.emit()

    def _handle_generic_button_event(self, note_number: int, is_pressed: bool):
        if not is_pressed: return 

        # print(f"HIM TRACE: Generic button: Note {hex(note_number)}") # Optional

        if note_number == FIRE_BUTTON_GRID_LEFT:
            self.grid_left_pressed.emit()
        elif note_number == FIRE_BUTTON_GRID_RIGHT:
            self.grid_right_pressed.emit()
        elif note_number == FIRE_ENCODER_SELECT_PRESS:
            self.select_encoder_pressed.emit()
        elif note_number == HW_BUTTON_SAMPLER_TOGGLE: # Now correctly 0x2F for PERFORM
            print(f"HIM INFO: SAMPLER TOGGLE button (PERFORM, Note {hex(HW_BUTTON_SAMPLER_TOGGLE)}) pressed.")
            self.request_toggle_screen_sampler.emit()
        elif note_number == HW_BUTTON_MONITOR_CYCLE: # Correctly 0x2E for DRUM
            print(f"HIM INFO: MONITOR CYCLE button (DRUM, Note {hex(HW_BUTTON_MONITOR_CYCLE)}) pressed.")
            self.request_cycle_sampler_monitor.emit()

    def _handle_control_change_event(self, control_cc: int, value: int):
        if control_cc == FIRE_ENCODER_SELECT_TURN_CC:
            delta = 0
            if value == 1: delta = 1
            elif value == 127: delta = -1
            elif value == 2: delta = 2 
            elif value == 126: delta = -2
            
            if delta != 0:
                self.select_encoder_turned.emit(delta)