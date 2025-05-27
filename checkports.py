import mido
import time
import os
os.environ['MIDO_BACKEND'] = 'mido.backends.rtmidi'

fire_input_name = None
print("Available MIDI Inputs:")
try:
    inputs = mido.get_input_names()
    if inputs:
        for port_name in inputs:
            print(f"- {port_name}")
            if "fire" in port_name.lower(): # Or be more specific to your port name
                fire_input_name = port_name
    else:
        print("No MIDI input ports found.")
except Exception as e:
    print(f"Error getting MIDI input names: {e}")

if not fire_input_name:
    print("Could not find Akai Fire input port. Exiting.")
    exit()

print(f"\nMonitoring Akai Fire input on: {fire_input_name}")
print("Press buttons or turn encoders on the Akai Fire. Press Ctrl+C to quit.")

try:
    with mido.open_input(fire_input_name) as inport:
        for msg in inport:
            print(msg)
except KeyboardInterrupt:
    print("\nStopped monitoring.")
except Exception as e:
    print(f"Error during MIDI monitoring: {e}")