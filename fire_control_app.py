# AKAI_Fire_RGB_Controller/fire_control_app.py
import sys
import os

# --- Ensure project root is in sys.path ---
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)
# ------------------------------------------

from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QIcon # <<< ADD THIS IMPORT
from gui.main_window import MainWindow # Import our main window class

from hardware.akai_fire_controller import AkaiFireController
print(f"DEBUG APP START: Available MIDI outputs: {AkaiFireController.get_available_ports()}")

def get_project_root():
    try:
        # Assumes fire_control_app.py is in the project root
        return os.path.dirname(os.path.abspath(__file__))
    except NameError:
        # Fallback if __file__ is not defined (e.g. interactive console)
        return os.path.dirname(os.path.abspath(sys.argv[0]))

def main():
    app = QApplication(sys.argv)

    project_root_path = get_project_root()
    icon_path = os.path.join(project_root_path, "resources", "icons", "app_icon.png")
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))
        print(f"INFO: Application icon set from '{icon_path}'")
    else:
        print(f"WARNING: Application icon not found at '{icon_path}'")

    # Load the stylesheet
    style_sheet_path = os.path.join(project_root, "resources", "styles", "style.qss")
    try:
        with open(style_sheet_path, "r") as f:
            app.setStyleSheet(f.read())
            print("Stylesheet loaded successfully.")
    except FileNotFoundError:
        print(f"Warning: Main stylesheet '{style_sheet_path}' not found. Using default styles.")
    except Exception as e:
        print(f"Error loading stylesheet: {e}")

    main_window = MainWindow()
    main_window.show()

    sys.exit(app.exec())

if __name__ == '__main__':
    main()