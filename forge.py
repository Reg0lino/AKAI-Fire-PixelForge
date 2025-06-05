# AKAI_Fire_RGB_Controller/fire_control_app.py
import sys
import os
import time
from utils import get_resource_path 
os.environ['MIDO_BACKEND'] = 'mido.backends.rtmidi'

# --- Ensure project root is in sys.path ---
# This assumes fire_control_app.py is in the project root.
project_root_for_path = os.path.dirname(os.path.abspath(__file__))
if project_root_for_path not in sys.path:
    sys.path.insert(0, project_root_for_path)
# Print sys.path for debugging bundled app path issues
# print("DEBUG fire_control_app.py: sys.path is now:", sys.path)

from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QIcon, QFontDatabase

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

def register_application_fonts():
    """Scans the resources/fonts directory and registers .ttf/.otf files with QFontDatabase."""
    print("APP INFO: Attempting to register application fonts...")
    # Ensure get_resource_path is defined above
    fonts_dir = get_resource_path(os.path.join("resources", "fonts"))
    if os.path.isdir(fonts_dir):
        # No need to create an instance: font_db = QFontDatabase()
        for filename in os.listdir(fonts_dir):
            if filename.lower().endswith((".ttf", ".otf")):
                font_path = os.path.join(fonts_dir, filename)
                # Call addApplicationFont statically on the QFontDatabase class
                font_id = QFontDatabase.addApplicationFont(font_path)
                if font_id != -1:
                    # Call applicationFontFamilies statically on the QFontDatabase class
                    families = QFontDatabase.applicationFontFamilies(font_id)
                    if families:
                        print(
                            f"APP INFO: Registered '{filename}' with families: {families}. Use first family name for QFont.")
                    else:
                        print(
                            f"APP WARNING: Registered '{filename}' but no font families reported by QFontDatabase.")
                else:
                    print(
                        f"APP WARNING: Failed to register application font: '{font_path}' (font_id was -1). Check font validity.")
    else:
        print(
            f"APP WARNING: Application fonts directory not found: '{fonts_dir}'")

def get_project_root_for_config(): # Renamed to avoid confusion with path for imports
    """Gets the absolute path to the project's root directory for config/data loading."""
    try:
        return os.path.dirname(os.path.abspath(__file__))
    except NameError: # Fallback if __file__ is not defined (e.g. interactive console)
        return os.path.dirname(os.path.abspath(sys.argv[0]))

def main():
    # Create QApplication instance FIRST
    app = QApplication(sys.argv)
    
    register_application_fonts()  # <<< ADD THIS CALL

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
    app_icon_path_runtime = get_resource_path(os.path.join(
        "resources", "icons", "app_icon.ico"))  # or .png
    if os.path.exists(app_icon_path_runtime):
        app.setWindowIcon(QIcon(app_icon_path_runtime))
    else:
        print(
            f"WARNING: Application icon for runtime not found at '{app_icon_path_runtime}'")

    style_sheet_path_runtime = get_resource_path(
        os.path.join("resources", "styles", "style.qss"))
    try:
        if os.path.exists(style_sheet_path_runtime):
            with open(style_sheet_path_runtime, "r") as f:
                app.setStyleSheet(f.read())
        else:
            print(
                f"WARNING: Main stylesheet not found at '{style_sheet_path_runtime}'.")
    except Exception as e:
        print(
            f"ERROR: Could not load stylesheet from '{style_sheet_path_runtime}': {e}")

    main_window = None
    try:
        print("INFO: Attempting to initialize MainWindow...")
        main_window = MainWindow()
        print("INFO: MainWindow initialized. Attempting to show...")
        main_window.show()
        print("INFO: MainWindow shown. Starting application event loop.")
        sys.exit(app.exec())
    except Exception as e:
        print("FATAL: Could not initialize or show MainWindow. Original error below:")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    # Log in same dir as EXE for bundled app
    log_file_path = os.path.join(os.path.abspath("."), "app_crash_log.txt")
    try:
        # Clear previous log file if it exists, to ensure we only see the latest crash
        if os.path.exists(log_file_path):
            os.remove(log_file_path)

        # Will go to console if visible
        print("APP_LAUNCH: fire_control_app.py __main__ block entered.")
        main()

    except Exception as e_top:
        # This block will catch any unhandled exception from main()
        # To console if visible
        print(
            f"APP_CRASH: A fatal error occurred in top-level main execution: {e_top}")
        import traceback

        error_message = f"Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}\n"
        error_message += f"Error Type: {type(e_top).__name__}\n"
        error_message += f"Error Message: {str(e_top)}\n"
        error_message += "Traceback:\n"
        error_message += traceback.format_exc()
        error_message += "\n\nSys.Path:\n" + "\n".join(sys.path)
        error_message += "\n\nEnvironment Variables (selected):\n"
        selected_env_vars = ['PATH', 'PYTHONHOME',
                             'PYTHONPATH', 'MIDO_BACKEND', 'QT_PLUGIN_PATH']
        for var in selected_env_vars:
            error_message += f"  {var}: {os.environ.get(var)}\n"

        try:
            with open(log_file_path, "w", encoding="utf-8") as f_log:
                f_log.write(error_message)
            print(
                f"APP_CRASH: Detailed error information written to: {log_file_path}")
        except Exception as e_log:
            print(
                f"APP_CRASH_LOGGING_ERROR: Could not write crash log to file: {e_log}")
            # Print original error to console as fallback
            print(f"Original error was: {e_top}")
            traceback.print_exc()  # Print original traceback to console as fallback

        sys.exit(1)  # Ensure the process exits with an error code
