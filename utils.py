# AKAI_Fire_RGB_Controller/utils.py
import sys
import os

def get_resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        base_path = sys._MEIPASS
    except Exception:
        # Assumes utils.py is at the project root, or one level down.
        # If utils.py is at root:
        base_path = os.path.abspath(".")
        # If utils.py is in a 'utils' folder:
        # base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    
    resource_full_path = os.path.join(base_path, relative_path)
    # print(f"DEBUG get_resource_path (utils): Relative='{relative_path}', Base='{base_path}', Full='{resource_full_path}'")
    return resource_full_path