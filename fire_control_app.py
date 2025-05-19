# AKAI_Fire_RGB_Controller/fire_control_app.py
import sys
import os
import sys; print(sys.path)

# --- Ensure project root is in sys.path ---
# This assumes fire_control_app.py is in the project root.
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)
# ------------------------------------------

from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QIcon
from gui.main_window import MainWindow # Import our main window class

# print(f"DEBUG APP START: Available MIDI outputs: {AkaiFireController.get_available_ports()}")

def get_project_root():
    """Gets the absolute path to the project's root directory."""
    # Assumes fire_control_app.py is in the project root
    try:
        return os.path.dirname(os.path.abspath(__file__))
    except NameError:
        return os.path.dirname(os.path.abspath(sys.argv[0]))

def main():
    app = QApplication(sys.argv)

    project_root_path = get_project_root()

    # Set Application Icon
    icon_path = os.path.join(project_root_path, "resources", "icons", "app_icon.png")
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))
        # print(f"INFO: Application icon set from '{icon_path}'")
    else:
        print(f"WARNING: Application icon not found at '{icon_path}'")

    # Load the global stylesheet
    style_sheet_path = os.path.join(project_root_path, "resources", "styles", "style.qss")
    try:
        with open(style_sheet_path, "r") as f:
            app.setStyleSheet(f.read())
            # print("INFO: Stylesheet loaded successfully.")
    except FileNotFoundError:
        print(f"WARNING: Main stylesheet '{style_sheet_path}' not found. Using default styles.")
    except Exception as e:
        print(f"ERROR: Could not load stylesheet: {e}")

    # Create and show the main window
    try:
        main_window = MainWindow()
        main_window.show()
    except Exception as e:
        print(f"FATAL: Could not initialize or show MainWindow: {e}")
        sys.exit(1) 

    sys.exit(app.exec())

if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(f"FATAL ERROR in main(): {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)