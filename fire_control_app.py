# AKAI_Fire_RGB_Controller/fire_control_app.py
import sys
import os
from utils import get_resource_path # <<< NEW IMPORT
# --- Set MIDO_BACKEND very early ---
os.environ['MIDO_BACKEND'] = 'mido.backends.rtmidi'
# ------------------------------------

# --- Ensure project root is in sys.path ---
# This assumes fire_control_app.py is in the project root.
project_root_for_path = os.path.dirname(os.path.abspath(__file__))
if project_root_for_path not in sys.path:
    sys.path.insert(0, project_root_for_path)
# Print sys.path for debugging bundled app path issues
# print("DEBUG fire_control_app.py: sys.path is now:", sys.path)
# ------------------------------------------

from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QIcon
# MainWindow import is deferred to main() to allow MIDO_BACKEND to be set first
# and to ensure QApplication exists before Qt modules are heavily used.

# --- Resource Path Function ---
def get_resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        # Not bundled, running from source
        # Assuming this function is in fire_control_app.py at the project root
        base_path = os.path.abspath(".")
    
    resource_full_path = os.path.join(base_path, relative_path)
    # print(f"DEBUG get_resource_path: Relative='{relative_path}', Base='{base_path}', Full='{resource_full_path}'")
    return resource_full_path
# --- End Resource Path Function ---

def get_project_root_for_config(): # Renamed to avoid confusion with path for imports
    """Gets the absolute path to the project's root directory for config/data loading."""
    try:
        return os.path.dirname(os.path.abspath(__file__))
    except NameError: # Fallback if __file__ is not defined (e.g. interactive console)
        return os.path.dirname(os.path.abspath(sys.argv[0]))

def main():
    # Create QApplication instance FIRST
    app = QApplication(sys.argv)

    # --- Import MainWindow and AkaiFireController AFTER QApplication is created ---
    # This is also after MIDO_BACKEND is set.
    try:
        from gui.main_window import MainWindow
        from hardware.akai_fire_controller import AkaiFireController # For initial MIDI port check
        # print(f"DEBUG APP START (in main): Available MIDI outputs: {AkaiFireController.get_available_ports()}")
    except ImportError as e:
        print(f"FATAL: Failed to import core application modules: {e}")
        # If running bundled, a QMessageBox might not work yet if PyQt6 itself failed partially.
        # For bundled app, errors here are better seen on console.
        sys.exit(1)
    except Exception as e_gen:
        print(f"FATAL: An unexpected error occurred during core imports: {e_gen}")
        sys.exit(1)


    # Set Application Icon (uses get_resource_path)
    # For the application icon shown in taskbar etc., set on QApplication
    app_icon_path_runtime = get_resource_path(os.path.join("resources", "icons", "app_icon.ico"))
    if os.path.exists(app_icon_path_runtime):
        app.setWindowIcon(QIcon(app_icon_path_runtime))
        # print(f"INFO: Application icon set from '{app_icon_path_runtime}'")
    else:
        print(f"WARNING: Application icon for runtime not found at '{app_icon_path_runtime}' (used by QApplication.setWindowIcon)")

    # Load the global stylesheet (uses get_resource_path)
    style_sheet_path_runtime = get_resource_path(os.path.join("resources", "styles", "style.qss"))
    try:
        if os.path.exists(style_sheet_path_runtime):
            with open(style_sheet_path_runtime, "r") as f:
                app.setStyleSheet(f.read())
                # print(f"INFO: Stylesheet loaded successfully from '{style_sheet_path_runtime}'.")
        else:
            print(f"WARNING: Main stylesheet not found at '{style_sheet_path_runtime}'. Using default styles.")
    except Exception as e:
        print(f"ERROR: Could not load stylesheet from '{style_sheet_path_runtime}': {e}")

    # Create and show the main window
    try:
        main_window = MainWindow() # MainWindow will use get_resource_path for its *own* icon if needed
        main_window.show()
    except Exception as e:
        print(f"FATAL: Could not initialize or show MainWindow: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1) 

    sys.exit(app.exec())

if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(f"FATAL ERROR in top-level main execution: {e}")
        import traceback
        traceback.print_exc()
        # input("Press Enter to exit...") # Optional: to keep console open on error
        sys.exit(1)