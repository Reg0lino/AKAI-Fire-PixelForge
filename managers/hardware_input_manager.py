from PyQt6.QtCore import QObject, pyqtSignal

# Define relevant Note and CC numbers
FIRE_BUTTON_PLAY = 0x33
FIRE_BUTTON_STOP = 0x34
FIRE_BUTTON_GRID_LEFT = 0x22  
FIRE_BUTTON_GRID_RIGHT = 0x23 
FIRE_ENCODER_SELECT_PRESS_NOTE = 0x19 # Note value for select encoder press (renamed for clarity)
FIRE_ENCODER_SELECT_TURN_CC = 0x76 

FIRE_BUTTON_BROWSER = 0x21 # For toggling sampler

HW_BUTTON_SAMPLER_TOGGLE = 0x2F  # Physical "PERFORM" button
HW_BUTTON_MONITOR_CYCLE = 0x2E   # Physical "DRUM" button

# --- ADD CCs for the top four encoders ---
FIRE_ENCODER_1_CC = 0x10 # Physical Knob 1 (Volume/Brightness)
FIRE_ENCODER_2_CC = 0x11 # Physical Knob 2 (Pan/Saturation)
FIRE_ENCODER_3_CC = 0x12 # Physical Knob 3 (Filter/Contrast)
FIRE_ENCODER_4_CC = 0x13 # Physical Knob 4 (Resonance/Hue)

class HardwareInputManager(QObject):
    # Signals for animator/navigation
    request_animator_play_pause = pyqtSignal()
    request_animator_stop = pyqtSignal()
    grid_left_pressed = pyqtSignal()
    grid_right_pressed = pyqtSignal()
    select_encoder_pressed = pyqtSignal()
    select_encoder_turned = pyqtSignal(int) # delta: +1, -1, +2, -2 for select encoder

    # Signals for Sampler Control
    request_toggle_screen_sampler = pyqtSignal()
    request_cycle_sampler_monitor = pyqtSignal()
    
    # --- CHANGE: Generic signal for top 4 physical encoders ---
    physical_encoder_rotated = pyqtSignal(int, int) # encoder_id (1-4), delta (+1 or -1)
    # REMOVE: physical_encoder_1_rotated = pyqtSignal(int) 

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
                 print("HIM WARNING: AkaiFireController does not have 'control_change_event' signal.")
        else:
            print("HIM CRITICAL: AkaiFireController reference not provided!")

    def _on_fire_play_pressed(self):
        self.request_animator_play_pause.emit()

    def _on_fire_stop_pressed(self):
        self.request_animator_stop.emit()

    def _handle_generic_button_event(self, note_number: int, is_pressed: bool):
        if not is_pressed: return 

        if note_number == FIRE_BUTTON_GRID_LEFT:
            self.grid_left_pressed.emit()
        elif note_number == FIRE_BUTTON_GRID_RIGHT:
            self.grid_right_pressed.emit()
        elif note_number == FIRE_ENCODER_SELECT_PRESS_NOTE: # Changed constant name
            self.select_encoder_pressed.emit()
        elif note_number == HW_BUTTON_SAMPLER_TOGGLE: 
            self.request_toggle_screen_sampler.emit()
        # --- ADD BROWSER button to also toggle sampler ---
        elif note_number == FIRE_BUTTON_BROWSER:
            # print(f"HIM INFO: BROWSER button (Note {hex(FIRE_BUTTON_BROWSER)}) pressed, toggling sampler.")
            self.request_toggle_screen_sampler.emit()
        # --- END ADD ---
        elif note_number == HW_BUTTON_MONITOR_CYCLE: 
            self.request_cycle_sampler_monitor.emit()
        # Add other note-based button presses here if needed

    def _handle_control_change_event(self, control_cc: int, value: int):
        delta = 0
        # Determine delta for standard encoders (value 1 for increment, 127 for decrement)
        if value == 1: delta = 1
        elif value == 127: delta = -1
        
        # Handle SELECT encoder (which has different delta values for speed)
        if control_cc == FIRE_ENCODER_SELECT_TURN_CC:
            select_delta = 0 # Use a separate delta for select encoder due to different values
            if value == 1: select_delta = 1
            elif value == 127: select_delta = -1
            elif value == 2: select_delta = 2 
            elif value == 126: select_delta = -2
            if select_delta != 0:
                self.select_encoder_turned.emit(select_delta)
        
        # --- ADD Logic for Physical Encoders 1-4 ---
        elif control_cc == FIRE_ENCODER_1_CC:
            if delta != 0: self.physical_encoder_rotated.emit(1, delta)
        elif control_cc == FIRE_ENCODER_2_CC:
            if delta != 0: self.physical_encoder_rotated.emit(2, delta)
        elif control_cc == FIRE_ENCODER_3_CC:
            if delta != 0: self.physical_encoder_rotated.emit(3, delta)
        elif control_cc == FIRE_ENCODER_4_CC:
            if delta != 0: self.physical_encoder_rotated.emit(4, delta)
        # --- END ADD ---
        
        # if delta != 0 and control_cc in [FIRE_ENCODER_1_CC, FIRE_ENCODER_2_CC, FIRE_ENCODER_3_CC, FIRE_ENCODER_4_CC]:
        #     print(f"HIM TRACE: Physical Encoder CC {hex(control_cc)} rotated, delta: {delta}")