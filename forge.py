# AKAI_Fire_RGB_Controller/forge.py
from PyQt6.QtGui import QIcon, QFontDatabase
from PyQt6.QtWidgets import QApplication
import sys
import os
import time
from utils import get_resource_path
import resources_rc
os.environ['MIDO_BACKEND'] = 'mido.backends.rtmidi'
project_root_for_path = os.path.dirname(os.path.abspath(__file__))
if project_root_for_path not in sys.path:
    sys.path.insert(0, project_root_for_path)

def get_resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    resource_full_path = os.path.join(base_path, relative_path)
    return resource_full_path

def register_application_fonts():
    """Scans the resources/fonts directory and registers .ttf/.otf files with QFontDatabase."""
    print("APP INFO: Attempting to register application fonts...")
    fonts_dir = get_resource_path(os.path.join("resources", "fonts"))
    if os.path.isdir(fonts_dir):
        for filename in os.listdir(fonts_dir):
            if filename.lower().endswith((".ttf", ".otf")):
                font_path = os.path.join(fonts_dir, filename)
                font_id = QFontDatabase.addApplicationFont(font_path)
                if font_id != -1:
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

def get_project_root_for_config():
    """Gets the absolute path to the project's root directory for config/data loading."""
    try:
        return os.path.dirname(os.path.abspath(__file__))
    except NameError:
        return os.path.dirname(os.path.abspath(sys.argv[0]))

def main():
    app = QApplication(sys.argv)
    register_application_fonts()
    try:
        from gui.main_window import MainWindow
        from hardware.akai_fire_controller import AkaiFireController
    except ImportError as e:
        print(f"FATAL: Failed to import core application modules: {e}")
        sys.exit(1)
    except Exception as e_gen:
        print(
            f"FATAL: An unexpected error occurred during core imports: {e_gen}")
        sys.exit(1)
    app_icon_path_runtime = get_resource_path(os.path.join(
        "resources", "icons", "app_icon.ico"))
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
                stylesheet = f.read()
            # Append a more forceful, global tooltip style to the main stylesheet.
            # This overrides OS-level styles and inheritance from individual widgets.
            tooltip_style = """
            QToolTip {
                background-color: #383838;
                color: #E0E0E0;
                border: 1px solid #505050;
                padding: 4px;
                border-radius: 3px;
                font-size: 9pt;
            }
            """
            app.setStyleSheet(stylesheet + tooltip_style)
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
    log_file_path = os.path.join(os.path.abspath("."), "app_crash_log.txt")
    try:
        if os.path.exists(log_file_path):
            os.remove(log_file_path)
        print("APP_LAUNCH: fire_control_app.py __main__ block entered.")
        main()
    except Exception as e_top:
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
            print(f"Original error was: {e_top}")
            traceback.print_exc()
        sys.exit(1)
