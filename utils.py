# AKAI_Fire_RGB_Controller/utils.py
import sys
import os
# --- Determine project root based on the location of this utils.py file ---
PROJECT_DIRECTORY_FROM_UTILS = os.path.dirname(os.path.abspath(__file__))
# print(
#     f"DEBUG (utils.py): PROJECT_DIRECTORY_FROM_UTILS initialized to: {PROJECT_DIRECTORY_FROM_UTILS}")

def get_resource_path(relative_path_from_project_root: str) -> str:
    """
    Get absolute path to a resource file.
    Works for development (running from source) and for PyInstaller-bundled apps.
    The relative_path_from_project_root should be relative to the project's root directory.
    """
    # print(
    #     f"DEBUG (get_resource_path called): Received relative_path_from_project_root: '{relative_path_from_project_root}'")
    try:
        base_path = sys._MEIPASS
    #     print(
    #         f"DEBUG (get_resource_path): Running bundled. _MEIPASS='{base_path}'")
        resource_full_path = os.path.join(
            base_path, relative_path_from_project_root)
    except AttributeError:  # Not bundled, running from source
        base_path = PROJECT_DIRECTORY_FROM_UTILS
    #     print(
    #         f"DEBUG (get_resource_path): Running from source. Using base_path (PROJECT_DIRECTORY_FROM_UTILS): '{base_path}'")
        resource_full_path = os.path.join(
            base_path, relative_path_from_project_root)
    # print(
    #     f"DEBUG (get_resource_path): Constructed full path: '{resource_full_path}'")
    return resource_full_path

if __name__ == "__main__":
    # Test cases
    # print(f"--- Testing get_resource_path from utils.py ---")
    # Simulate running from source (assuming utils.py is in project root)
    # print(f"Dev mode (utils.py in root, CWD is project root):")
    # print(
    #     f"  resources/fonts/TomThumb.ttf -> {get_resource_path('resources/fonts/TomThumb.ttf')}")
    # print(
    #     f"  resources/icons/app_icon.png -> {get_resource_path('resources/icons/app_icon.png')}")
    # Simulate PyInstaller one-file bundle (_MEIPASS)
    # print(f"\nSimulating PyInstaller one-file (_MEIPASS):")
    original_frozen = getattr(sys, "frozen", False)
    original_meipass = getattr(sys, "_MEIPASS", None)
    sys.frozen = True
    # Create a temporary directory that simulates _MEIPASS
    # Ensure this path is something writeable for the test
    temp_meipass_dir = os.path.join(os.getcwd(), "_MEIPASS_test_dir_temp")
    sys._MEIPASS = temp_meipass_dir
    os.makedirs(sys._MEIPASS, exist_ok=True)
    dummy_meipass_font_path_rel = os.path.join(
        "resources", "fonts", "TomThumb.ttf")
    dummy_meipass_font_path_abs = os.path.join(
        sys._MEIPASS, dummy_meipass_font_path_rel)
    os.makedirs(os.path.dirname(dummy_meipass_font_path_abs), exist_ok=True)
    with open(dummy_meipass_font_path_abs, "w") as f:
        f.write("dummy font")
    # print(f"  (MEIPASS is {sys._MEIPASS})")
    # print(
    #     f"  resources/fonts/TomThumb.ttf -> {get_resource_path('resources/fonts/TomThumb.ttf')}")
    if os.path.exists(dummy_meipass_font_path_abs):
        os.remove(dummy_meipass_font_path_abs)
    if os.path.exists(os.path.dirname(dummy_meipass_font_path_abs)):
        try:
            os.rmdir(os.path.dirname(dummy_meipass_font_path_abs))
        except OSError:
            pass
    if os.path.exists(sys._MEIPASS):
        try:
            os.rmdir(sys._MEIPASS)
        except OSError:
            pass
    sys.frozen = original_frozen
    if original_meipass is not None:
        sys._MEIPASS = original_meipass
    elif hasattr(sys, "_MEIPASS"): del sys._MEIPASS