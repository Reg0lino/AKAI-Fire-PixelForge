# AKAI_Fire_RGB_Controller/hardware/akai_fire_controller.py
import mido
import time

class AkaiFireController:
    def __init__(self, port_name=None, auto_connect=True):
        self.out_port = None
        self.port_name_used = None

        self.NON_GRID_BUTTON_CCS = [
            0x23, 0x22, 0x21, 0x20, 0x1F, 0x28, 0x29, 0x2A, 0x2B, 0x2C,
            0x2D, 0x2E, 0x2F, 0x30, 0x31, 0x32, 0x33, 0x34, 0x35
        ]
        self.BANK_LED_CC = 0x1B
        self.BANK_LED_OFF_VALUE = 0x10

        if auto_connect:
            if port_name:
                try:
                    self.out_port = mido.open_output(port_name)
                    self.port_name_used = port_name
                    # print(f"AkaiFireController: Successfully opened AKAI Fire on port: {port_name}") # Debug
                except Exception as e:
                    print(f"AkaiFireController: Error opening AKAI Fire port '{port_name}': {e}")
            else:
                available_ports = self.get_available_ports()
                fire_ports = [p for p in available_ports if ('fire' in p.lower() or 'akai' in p.lower()) and 'midiin' not in p.lower()]
                if fire_ports:
                    try:
                        self.out_port = mido.open_output(fire_ports[0])
                        self.port_name_used = fire_ports[0]
                        # print(f"AkaiFireController: Auto-detected and opened AKAI Fire on port: {fire_ports[0]}") # Debug
                    except Exception as e:
                        print(f"AkaiFireController: Error auto-opening AKAI Fire port '{fire_ports[0]}': {e}")
                # else:
                    # print("AkaiFireController: AKAI Fire port not auto-detected for connection.")

            if self.out_port:
                self._initialize_device_leds()
        # else:
            # print("AkaiFireController initialized without auto-connecting.")

    @staticmethod
    def get_available_ports():
        try:
            return mido.get_output_names()
        except Exception as e:
            print(f"AkaiFireController: Error getting MIDI output names: {e}")
            return []

    def _send_cc(self, control, value, channel=0):
        if not self.is_connected():
            return
        try:
            msg = mido.Message('control_change', channel=channel, control=control, value=value)
            self.out_port.send(msg)
            time.sleep(0.001) 
        except Exception as e:
            print(f"AkaiFireController: Error sending CC message: {e}")

    def _initialize_device_leds(self):
        if not self.is_connected():
            return
        
        # print("AkaiFireController: Initializing AKAI Fire LEDs (turning off pads and buttons)...") # Debug
        
        self.clear_all_pads() 
        time.sleep(0.05) 

        for cc_num in self.NON_GRID_BUTTON_CCS:
            self._send_cc(control=cc_num, value=0)

        self._send_cc(control=self.BANK_LED_CC, value=self.BANK_LED_OFF_VALUE)
        
        # print("AkaiFireController: Device LED initialization complete.") # Debug

    def connect(self, port_name):
        if self.out_port:
            # print(f"AkaiFireController: Already connected to {self.port_name_used}. Please disconnect first.") # Debug
            return False
        try:
            self.out_port = mido.open_output(port_name)
            self.port_name_used = port_name
            print(f"AkaiFireController: Successfully connected to AKAI Fire on port: {port_name}")
            self._initialize_device_leds()
            return True
        except Exception as e:
            print(f"AkaiFireController: Error connecting to AKAI Fire port '{port_name}': {e}")
            self.out_port = None
            self.port_name_used = None
            return False

    def disconnect(self):
        if self.out_port:
            # print(f"AkaiFireController: Disconnecting from {self.port_name_used}...") # Debug
            self._initialize_device_leds() 
            time.sleep(0.05)
            self.out_port.close()
            self.out_port = None
            self.port_name_used = None
            print("AkaiFireController: AKAI Fire connection closed.")
        # else:
            # print("AkaiFireController: Not currently connected.") # Debug

    def is_connected(self):
        return self.out_port is not None and not self.out_port.closed

    def _send_sysex(self, data_bytes):
        if not self.is_connected():
            return
        sysex_message_bytes = [0xF0, 0x47, 0x7F, 0x43] + data_bytes + [0xF7]
        try:
            msg = mido.Message.from_bytes(sysex_message_bytes)
            self.out_port.send(msg)
            time.sleep(0.001)
        except Exception as e:
            print(f"AkaiFireController: Error sending SysEx: {e}")

    def set_pad_color(self, row, col, r8, g8, b8):
        if not self.is_connected(): return
        if not (0 <= row <= 3 and 0 <= col <= 15):
            # print(f"AkaiFireController: Error - Pad ({row},{col}) out of bounds.") # Debug
            return

        pad_index = (row * 16) + col
        r7 = max(0, min(r8, 255)) >> 1
        g7 = max(0, min(g8, 255)) >> 1
        b7 = max(0, min(b8, 255)) >> 1

        data_payload = [
            0x65, 0x00, 0x04, 
            pad_index, r7, g7, b7
        ]
        self._send_sysex(data_payload)

    def set_multiple_pads_color(self, pad_data_list):
        if not self.is_connected() or not pad_data_list:
            return

        payload_bytes = []
        valid_pads_count = 0

        for item in pad_data_list:
            pad_index, r8, g8, b8 = -1, 0, 0, 0 # Initialize
            if len(item) == 4: 
                pad_index, r8, g8, b8 = item
            elif len(item) == 5: 
                row, col, r8_val, g8_val, b8_val = item
                if not (0 <= row <= 3 and 0 <= col <= 15):
                    continue
                pad_index = (row * 16) + col
                r8, g8, b8 = r8_val, g8_val, b8_val
            else:
                continue 
            
            if pad_index == -1: continue # Should not happen if logic above is correct

            r7 = max(0, min(r8, 255)) >> 1
            g7 = max(0, min(g8, 255)) >> 1
            b7 = max(0, min(b8, 255)) >> 1
            payload_bytes.extend([pad_index, r7, g7, b7])
            valid_pads_count += 1
        
        if not payload_bytes:
            return

        total_payload_length = valid_pads_count * 4
        sysex_data_payload = [
            0x65,                              
            (total_payload_length >> 7) & 0x7F, 
            total_payload_length & 0x7F,       
        ] + payload_bytes
        self._send_sysex(sysex_data_payload)

    def clear_all_pads(self):
        if not self.is_connected(): return
        all_pads_off_data = []
        for r_idx in range(4):
            for c_idx in range(16):
                all_pads_off_data.append((r_idx, c_idx, 0, 0, 0))
        self.set_multiple_pads_color(all_pads_off_data)
        # print("AkaiFireController: All grid pads cleared (hardware signal sent).") # Debug

# --- Example Usage (for testing this module directly if needed) ---
if __name__ == "__main__":
    print("AkaiFireController: Direct module test initiated.")
    
    available_ports = AkaiFireController.get_available_ports()
    print(f"AkaiFireController: Available MIDI output ports: {available_ports}")

    # Find a port that looks like the Fire for testing
    test_port_name = None
    for port in available_ports:
        if ("fire" in port.lower() or "akai" in port.lower()) and "midiin" not in port.lower():
            test_port_name = port
            break
    
    if not test_port_name:
        print("AkaiFireController: No suitable AKAI Fire port found for direct test. Exiting.")
        exit()

    print(f"AkaiFireController: Attempting to connect to '{test_port_name}' for test...")
    controller = AkaiFireController(port_name=test_port_name, auto_connect=True) 
    
    if controller.is_connected():
        print(f"AkaiFireController: Successfully connected to {controller.port_name_used} for test.")
        
        print("AkaiFireController: Test - Setting Pad (0,0) to Red")
        controller.set_pad_color(0, 0, 255, 0, 0)
        time.sleep(1)

        print("AkaiFireController: Test - Setting Pad (0,1) to Green")
        controller.set_pad_color(0, 1, 0, 255, 0)
        time.sleep(1)
        
        print("AkaiFireController: Test - Clearing all pads again.")
        controller.clear_all_pads()
        time.sleep(1)
        
        controller.disconnect()
    else:
        print(f"AkaiFireController: Direct test connection to '{test_port_name}' failed.")
        
    print("AkaiFireController: Direct module test finished.")