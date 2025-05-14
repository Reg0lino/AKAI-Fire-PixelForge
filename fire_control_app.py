# AKAI_Fire_RGB_Controller/fire_control_app.py
import sys
import os

# --- Ensure project root is in sys.path ---
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)
# ------------------------------------------

from PyQt6.QtWidgets import QApplication
from gui.main_window import MainWindow # Import our main window class

def main():
    app = QApplication(sys.argv)

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