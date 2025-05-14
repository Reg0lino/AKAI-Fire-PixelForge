import sys
import os

# Add project root to sys.path (same as in fire_control_app.py)
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

print("Attempting to import HueSlider...")
try:
    from gui.hue_slider import HueSlider
    print("HueSlider imported successfully!")
    # You could even try to instantiate it if it doesn't require QApplication yet
    # slider = HueSlider() 
    # print("HueSlider instantiated (if possible without app).")
except ImportError as e:
    print(f"ImportError for HueSlider: {e}")
    import traceback
    traceback.print_exc()
except Exception as e:
    print(f"Some other error occurred during HueSlider import: {e}")
    import traceback
    traceback.print_exc()

print("\nAttempting to import SVPicker...")
try:
    from gui.sv_picker import SVPicker
    print("SVPicker imported successfully!")
except ImportError as e:
    print(f"ImportError for SVPicker: {e}")
    import traceback
    traceback.print_exc()
except Exception as e:
    print(f"Some other error occurred during SVPicker import: {e}")
    import traceback
    traceback.print_exc()