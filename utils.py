# AKAI_Fire_RGB_Controller/utils.py
import sys
import os


def get_resource_path(relative_path: str) -> str:
    """
    Get absolute path to a resource.
    - If bundled by PyInstaller and it's a one-file exe, PyInstaller unpacks to _MEIPASS.
    - If running from source or a PyInstaller one-dir bundle, or if installed traditionally,
      this tries to find resources relative to the main script's/executable's directory.
    """
    if getattr(sys, "frozen", False):
        # Application is bundled (e.g., by PyInstaller)
        if hasattr(sys, "_MEIPASS"):
            # This is the PyInstaller temp directory for bundled data files.
            # If your resources (like fonts/icons) are bundled *into* the PyInstaller package,
            # this is where they will be.
            application_path = sys._MEIPASS
        else:
            # Bundled, but not a one-file exe, or _MEIPASS not set for some reason.
            # The executable directory is a good starting point.
            application_path = os.path.dirname(sys.executable)
    else:
        # Application is not bundled (running from source)
        # Assume project root is one level up from 'utils.py' if utils.py is in root,
        # or two levels up if utils.py is in a 'utils' subfolder.
        # For simplicity, if utils.py is at the project root:
        application_path = os.path.abspath(".")
        # If you are sure utils.py is ALWAYS at the project root, os.path.abspath(".") is fine for dev.
        # If fire_control_app.py (your main entry) is at project root, a more robust way to find
        # project root from anywhere during development:
        # current_script_path = os.path.dirname(os.path.abspath(__file__)) # Path to utils.py
        # application_path = os.path.dirname(current_script_path) # If utils.py is in a 'utils' folder
        # application_path = current_script_path # If utils.py is in project root

        # Let's assume the structure where fire_control_app.py is in the root,
        # and it adds the root to sys.path. When running from source,
        # os.path.abspath(".") from where fire_control_app.py is run is the project root.
        # If fire_control_app.py is in a subfolder, this needs to be more robust.

        # A common pattern for finding the main script's directory during development:
        try:
            # __main__ module's file attribute if available
            main_script_path = os.path.dirname(
                os.path.abspath(sys.modules["__main__"].__file__)
            )
            application_path = main_script_path
        except (KeyError, AttributeError):
            # Fallback to current working directory if __main__ trick fails
            application_path = os.path.abspath(".")

    resource_full_path = os.path.join(application_path, relative_path)

    # print(f"DEBUG utils.py get_resource_path: Relative='{relative_path}', AppPath='{application_path}', Full='{resource_full_path}', Frozen={getattr(sys, 'frozen', False)}")

    # Fallback for PyInstaller one-file mode if resource wasn't found next to exe
    # and _MEIPASS was expected but perhaps not used above initially.
    if (
        getattr(sys, "frozen", False)
        and hasattr(sys, "_MEIPASS")
        and not os.path.exists(resource_full_path)
    ):
        meipass_path = os.path.join(sys._MEIPASS, relative_path)
        if os.path.exists(meipass_path):
            # print(f"DEBUG utils.py get_resource_path: Using _MEIPASS fallback: {meipass_path}")
            return meipass_path
        else:
            # print(f"DEBUG utils.py get_resource_path: _MEIPASS fallback also not found: {meipass_path}")
            pass  # Will return the initially constructed resource_full_path which might be wrong

    return resource_full_path


if __name__ == "__main__":
    # Test cases
    print(f"--- Testing get_resource_path from utils.py ---")

    # Simulate running from source (assuming utils.py is in project root)
    print(f"Dev mode (utils.py in root, CWD is project root):")
    print(
        f"  resources/fonts/TomThumb.ttf -> {get_resource_path('resources/fonts/TomThumb.ttf')}"
    )
    print(
        f"  resources/icons/app_icon.png -> {get_resource_path('resources/icons/app_icon.png')}"
    )

    # Simulate PyInstaller one-file bundle (_MEIPASS)
    print(f"\nSimulating PyInstaller one-file (_MEIPASS):")
    original_frozen = getattr(sys, "frozen", False)
    original_meipass = getattr(sys, "_MEIPASS", None)
    sys.frozen = True
    sys._MEIPASS = "/tmp/_MEIPASS_test_dir"  # Example MEIPASS
    # Create dummy files for testing this scenario
    dummy_meipass_font_path = os.path.join(sys._MEIPASS, "resources/fonts/TomThumb.ttf")
    os.makedirs(os.path.dirname(dummy_meipass_font_path), exist_ok=True)
    with open(dummy_meipass_font_path, "w") as f:
        f.write("dummy font")

    print(f"  (MEIPASS is {sys._MEIPASS})")
    print(
        f"  resources/fonts/TomThumb.ttf -> {get_resource_path('resources/fonts/TomThumb.ttf')}"
    )  # Should resolve to MEIPASS here

    # Clean up dummy
    if os.path.exists(dummy_meipass_font_path):
        os.remove(dummy_meipass_font_path)
    if os.path.exists(os.path.dirname(dummy_meipass_font_path)):
        try:
            os.rmdir(os.path.dirname(dummy_meipass_font_path))  # only if empty
        except OSError:
            pass
        try:
            os.rmdir(sys._MEIPASS)  # only if empty
        except OSError:
            pass

    # Simulate PyInstaller one-dir bundle (frozen=True, no _MEIPASS, exe_dir)
    print(f"\nSimulating PyInstaller one-dir (frozen, no _MEIPASS):")
    sys.frozen = True
    if hasattr(sys, "_MEIPASS"):
        del sys._MEIPASS  # Ensure no _MEIPASS
    # For this test, sys.executable needs to be a path where resources would be relative to.
    # This is harder to perfectly simulate without actually bundling.
    # Let's assume sys.executable points to a 'dist/AppName' folder and resources are in 'dist/AppName/resources'
    original_executable = sys.executable
    # sys.executable = os.path.join(os.getcwd(), "dist", "YourApp") # Hypothetical
    # For a more direct test, let's assume sys.executable IS the project root for this test case
    sys.executable = os.path.join(
        os.getcwd(), "fire_control_app.py"
    )  # A file in project root

    print(f"  (sys.executable is {sys.executable})")
    # Assuming resources folder is directly in os.getcwd() for this test structure
    print(
        f"  resources/fonts/TomThumb.ttf -> {get_resource_path('resources/fonts/TomThumb.ttf')}"
    )

    # Restore original sys attributes
    
    sys.frozen = original_frozen
    if original_meipass is not None:
        sys._MEIPASS = original_meipass
    elif hasattr(sys, "_MEIPASS"):
        del sys._MEIPASS
    sys.executable = original_executable
