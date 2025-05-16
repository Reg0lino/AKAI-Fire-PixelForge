# AKAI_Fire_RGB_Controller/fire_control_app.py
import sys
import os

# --- Ensure project root is in sys.path ---
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)
# ------------------------------------------

# Only import QApplication and QIcon from PyQt here at the top level for app setup
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QIcon

# Other non-Qt, non-application-specific imports are generally fine here if needed by get_project_root
# For a clean test, we defer application-specific imports into main()

def get_project_root():
    try:
        # Assumes fire_control_app.py is in the project root
        return os.path.dirname(os.path.abspath(__file__))
    except NameError:
        # Fallback if __file__ is not defined (e.g. interactive console)
        return os.path.dirname(os.path.abspath(sys.argv[0]))

def main():
    # --- Step 1: Create QApplication instance FIRST ---
    app = QApplication(sys.argv)

    # --- Step 2: DIAGNOSTIC MINIMAL QWIDGET TESTS ---
    # Import necessary Qt Widgets specifically for this diagnostic block
    from PyQt6.QtWidgets import QPushButton as DiagnosticQPushButton
    from PyQt6.QtWidgets import QComboBox as DiagnosticQComboBox
    
    print("-" * 30)
    print("DIAGNOSTIC_APP: Starting minimal widget tests...")

    # Test QPushButton
    print("DIAGNOSTIC_APP: Testing QPushButton...")
    test_button_instance = None
    try:
        test_button_instance = DiagnosticQPushButton("Test Button")
        print(f"  DIAGNOSTIC_APP: test_button_instance created: {test_button_instance}")
        bool_test_button = bool(test_button_instance)
        print(f"  DIAGNOSTIC_APP: bool(test_button_instance) is: {bool_test_button}")
        if test_button_instance is not None and bool_test_button: # Check both Python None and boolean value
            print(f"  DIAGNOSTIC_APP: test_button_instance.text() is: '{test_button_instance.text()}'")
        elif test_button_instance is not None and not bool_test_button:
            print(f"  DIAGNOSTIC_APP: test_button_instance exists but bool() is False. Attempting .text(): '{test_button_instance.text()}'")
        else:
            print(f"  DIAGNOSTIC_APP: test_button_instance is Python None.")
    except Exception as e_button_create:
        print(f"  DIAGNOSTIC_APP: ERROR DURING QPushButton TEST: {e_button_create}")
    
    print("-" * 10)

    # Test QComboBox
    print("DIAGNOSTIC_APP: Testing QComboBox...")
    test_combo_instance = None
    try:
        test_combo_instance = DiagnosticQComboBox()
        print(f"  DIAGNOSTIC_APP: test_combo_instance created: {test_combo_instance}")
        bool_test_combo = bool(test_combo_instance)
        print(f"  DIAGNOSTIC_APP: bool(test_combo_instance) is: {bool_test_combo}")
        if test_combo_instance is not None and bool_test_combo: # Check both
            print(f"  DIAGNOSTIC_APP: test_combo_instance.count() is: {test_combo_instance.count()}")
        elif test_combo_instance is not None and not bool_test_combo: # Exists, but bool is False
            print(f"  DIAGNOSTIC_APP: test_combo_instance exists but bool() is False. Attempting .count(): {test_combo_instance.count()}")
        else:
            print(f"  DIAGNOSTIC_APP: test_combo_instance is Python None.")
            
    except Exception as e_combo_create:
        print(f"  DIAGNOSTIC_APP: ERROR DURING QComboBox TEST: {e_combo_create}")
    
    print("DIAGNOSTIC_APP: Minimal widget tests finished.")
    print("-" * 30)
    # --- END DIAGNOSTIC MINIMAL QWIDGET TESTS ---

    # --- Step 3: Import your application's main window and other components ---
    # These imports happen AFTER QApplication is created and AFTER minimal Qt tests.
    from gui.main_window import MainWindow
    from hardware.akai_fire_controller import AkaiFireController # Assuming this doesn't init Qt widgets at import time
    
    print(f"DEBUG APP START: Available MIDI outputs: {AkaiFireController.get_available_ports()}")

    # --- Step 4: Application Setup (Icon, Stylesheet) ---
    project_root_path = get_project_root()
    icon_path = os.path.join(project_root_path, "resources", "icons", "app_icon.png")
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))
        print(f"INFO: Application icon set from '{icon_path}'")
    else:
        print(f"WARNING: Application icon not found at '{icon_path}'")

    # Stylesheet loading (temporarily skipped in previous diagnostic, can be re-enabled if desired,
    # but for this specific bool() issue, better to keep it simple first).
    style_sheet_path = os.path.join(project_root_path, "resources", "styles", "style.qss")
    try:
        with open(style_sheet_path, "r") as f:
            app.setStyleSheet(f.read())
            print("Stylesheet loaded successfully.")
    except FileNotFoundError:
        print(f"Warning: Main stylesheet '{style_sheet_path}' not found. Using default styles.")
    except Exception as e:
        print(f"Error loading stylesheet: {e}")
    print("INFO: Stylesheet loading SKIPPED for this diagnostic run (can be re-enabled).")


    # --- Step 5: Create and Show MainWindow ---
    print("INFO: About to create MainWindow instance.")
    main_window = MainWindow()
    print("INFO: MainWindow instance created. About to show.")
    main_window.show()
    print("INFO: MainWindow shown. Starting app.exec().")
    
    # --- Step 6: Start Event Loop ---
    sys.exit(app.exec())

if __name__ == '__main__':
    main()