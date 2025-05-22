# AKAI_Fire_RGB_Controller/utils.py
import sys
import os

def get_resource_path(relative_path: str) -> str:
    """
    Get absolute path to resource, works for dev and for PyInstaller.
    This version assumes utils.py is at the project root.
    """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except AttributeError: # More specific exception
        # Not bundled, running from source.
        # If utils.py is at the project root:
        base_path = os.path.abspath(".")
        # If utils.py was in a 'utils' subfolder, it would be:
        # base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    
    resource_full_path = os.path.join(base_path, relative_path)
    # print(f"DEBUG get_resource_path (utils.py): Relative='{relative_path}', Base='{base_path}', Full='{resource_full_path}'")
    return resource_full_path