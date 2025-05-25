# AKAI_Fire_RGB_Controller/gui/main_window.py
import sys
import json
import os
import glob
import re
import time
from appdirs import user_config_dir

# --- Qt Imports - CONSOLIDATED AND CORRECTED ---
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,QGroupBox, QLabel, QPushButton, QComboBox, QSizePolicy, QSpacerItem,QStatusBar, QMenu, QMessageBox, QDial, QFrame)
from PyQt6.QtCore import (Qt, QTimer, QSize, pyqtSignal, QPoint, QEvent)
from PyQt6.QtGui import (QColor, QPalette, QAction, QMouseEvent, QKeySequence, QIcon, QPixmap, QImage, QPainter, QCloseEvent )
# --- End Qt Imports ---

# --- Project-specific Imports ---
from utils import get_resource_path
from oled_utils import oled_renderer 

from .color_picker_manager import ColorPickerManager
from .static_layouts_manager import StaticLayoutsManager
from .interactive_pad_grid import InteractivePadGridFrame
from .screen_sampler_manager import ScreenSamplerManager
from .animator_manager_widget import AnimatorManagerWidget 
from hardware.akai_fire_controller import AkaiFireController
from managers.oled_display_manager import OLEDDisplayManager
from managers.hardware_input_manager import HardwareInputManager

from animator.controls_widget import ICON_COPY, ICON_CUT, ICON_DUPLICATE, ICON_DELETE, ICON_ADD_BLANK 

try:
    from features.screen_sampler_core import ScreenSamplerCore
except ImportError:
    print("MainWindow FATAL: Could not import ScreenSamplerCore. Some defaults may be missing.")
    class ScreenSamplerCore: # Minimal fallback
        DEFAULT_ADJUSTMENTS = {'brightness': 1.0, 'contrast': 1.0, 'saturation': 1.0, 'hue_shift': 0}

from .screen_sampler_manager import ScreenSamplerCore

from .oled_customizer_dialog import OLEDCustomizerDialog # Assuming it's in the same 'gui' package
try:
    from features.screen_sampler_core import ScreenSamplerCore # For DEFAULT_ADJUSTMENTS
except ImportError:
    # Fallback if ScreenSamplerCore can't be imported here
    print("MainWindow WARNING: Could not import ScreenSamplerCore for default adjustments.")
    class ScreenSamplerCore: DEFAULT_ADJUSTMENTS = {'brightness': 1.0, 'contrast': 1.0, 'saturation': 1.0, 'hue_shift': 0}

# --- Constants ---
INITIAL_WINDOW_WIDTH = 1050 # Reverted to original size for now
INITIAL_WINDOW_HEIGHT = 900
PRESETS_BASE_DIR_NAME = "presets" 
APP_NAME = "AKAI_Fire_RGB_Controller"
APP_AUTHOR = "Reg0lino" 
USER_PRESETS_APP_FOLDER_NAME = "Akai Fire RGB Controller User Presets"
DEFAULT_OLED_WELCOME_MESSAGE = "FIRE  RGB  Controller  by  Reg0lino    =^_^=   "
OLED_MIRROR_WIDTH = 128 
OLED_MIRROR_HEIGHT = 64
OLED_MIRROR_SCALE = 1.2
OLED_CONFIG_FILENAME = "oled_config.json" # For startup text and font settings
# --- ADDED: Default OLED Startup Settings (used if config file is missing/corrupt) ---
DEFAULT_OLED_STARTUP_TEXT = "FIRE  RGB  Controller  by  Reg0lino    =^_^=   " 
DEFAULT_OLED_FONT_FAMILY = "Arial" # A common system font as a safe default
DEFAULT_OLED_FONT_SIZE_PX = 10     # A reasonable small default size
DEFAULT_OLED_SCROLL_DELAY_MS = 180 


def get_user_documents_presets_path(app_specific_folder_name: str = USER_PRESETS_APP_FOLDER_NAME) -> str:
    try:
        documents_path = ""
        if sys.platform == "win32":
            import ctypes.wintypes; CSIDL_PERSONAL=5; SHGFP_TYPE_CURRENT=0
            buf = ctypes.create_unicode_buffer(ctypes.wintypes.MAX_PATH)
            ctypes.windll.shell32.SHGetFolderPathW(None, CSIDL_PERSONAL, None, SHGFP_TYPE_CURRENT, buf)
            documents_path = buf.value or os.path.join(os.path.expanduser("~"),"Documents")
        elif sys.platform == "darwin": documents_path = os.path.join(os.path.expanduser("~"),"Documents")

        else:
            documents_path = os.environ.get('XDG_DOCUMENTS_DIR',os.path.join(os.path.expanduser("~"),"Documents"))
            if not os.path.isdir(documents_path): documents_path = os.path.join(os.path.expanduser("~"),"Documents")
        if not os.path.isdir(documents_path): documents_path = os.path.expanduser("~")
        app_presets_dir = os.path.join(documents_path, app_specific_folder_name)
        os.makedirs(app_presets_dir, exist_ok=True); return app_presets_dir
    except Exception as e:
        print(f"WARNING: User presets path error (CWD fallback): {e}")
        fallback_dir = os.path.join(os.getcwd(), "user_presets_fallback_mw_hr1"); os.makedirs(fallback_dir,exist_ok=True); return fallback_dir


def get_user_config_file_path(filename: str) -> str:
    config_dir_to_use = "" 
    try:
        is_packaged = getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS')
        if is_packaged:
            config_dir_to_use = user_config_dir(APP_NAME, APP_AUTHOR, roaming=True)
        else:
            try: current_file_dir = os.path.dirname(os.path.abspath(__file__)); project_root = os.path.dirname(current_file_dir)
            except NameError: project_root = os.getcwd() 
            config_dir_to_use = os.path.join(project_root, "user_settings")
        os.makedirs(config_dir_to_use, exist_ok=True)
        return os.path.join(config_dir_to_use, filename)
    except Exception as e:
        print(f"WARNING: Config path error for '{filename}' (CWD fallback): {e}")
        fallback_dir=os.path.join(os.getcwd(),"user_settings_fallback_mw_hr1"); os.makedirs(fallback_dir,exist_ok=True); return os.path.join(fallback_dir,filename)

class MainWindow(QMainWindow):
    # Class attribute for OLED navigation focus options
    OLED_NAVIGATION_FOCUS_OPTIONS = ["animator", "static_layouts"] # Order matters for cycling

    # Define sampler adjustment knob ranges (can be class constants or defined here)
    SAMPLER_BRIGHTNESS_KNOB_MIN, SAMPLER_BRIGHTNESS_KNOB_MAX = 0, 400 
    SAMPLER_SATURATION_KNOB_MIN, SAMPLER_SATURATION_KNOB_MAX = 0, 400 
    SAMPLER_CONTRAST_KNOB_MIN, SAMPLER_CONTRAST_KNOB_MAX = 0, 400   
    SAMPLER_HUE_KNOB_MIN, SAMPLER_HUE_KNOB_MAX = -180, 180

     # Define step sizes for physical knob control when sampler is ON
    SAMPLER_FACTOR_KNOB_STEP = 4 # For 0-400 range, 4 means 0.04x per physical tick
    SAMPLER_HUE_KNOB_STEP = 2    # For -180 to 180 range, 2 degrees per physical tick
    GLOBAL_BRIGHTNESS_KNOB_STEP = 1 # For 0-100 range (global brightness), 1% per physical tick

    ANIMATOR_SPEED_KNOB_STEP = 1 # 1 FPS per physical tick, adjust as desired

    def __init__(self):
        super().__init__()
        # WINDOW TITLE: Updated to reflect the new name
        self.setWindowTitle("AKAI Fire RGB Customizer") # Updated Title
        # WINDOW SIZE: Set to initial size
        self.setGeometry(100, 100, INITIAL_WINDOW_WIDTH, INITIAL_WINDOW_HEIGHT)
        self._set_window_icon() 
        
        self.oled_startup_text: str = DEFAULT_OLED_STARTUP_TEXT
        self.oled_startup_font_family: str = DEFAULT_OLED_FONT_FAMILY
        self.oled_startup_font_size_px: int = DEFAULT_OLED_FONT_SIZE_PX
        self.oled_global_scroll_delay_ms: int = DEFAULT_OLED_SCROLL_DELAY_MS
        self._load_oled_config() # Load saved OLED settings

        self.akai_controller = AkaiFireController(auto_connect=False)
        self.selected_qcolor = QColor("#04FF00") 
        self.is_eyedropper_mode_active: bool = False
        self._has_played_initial_startup_animation = False
        self.current_oled_nav_target_name: str = self.OLED_NAVIGATION_FOCUS_OPTIONS[0]
        self.current_oled_nav_target_widget: QWidget | None = None 
        self.current_oled_nav_item_logical_index: int = 0 
        self._oled_nav_item_count: int = 0 
        self._oled_nav_interaction_active: bool = False 
        self._oled_nav_debounce_timer = QTimer(self); self._oled_nav_debounce_timer.setSingleShot(True); self._oled_nav_debounce_timer.setInterval(300) 
        self._is_hardware_nav_action_in_progress = False

        self.bundled_presets_base_path = self._get_presets_base_dir_path() 
        self.user_documents_presets_path = get_user_documents_presets_path()

        # --- Instantiate All Managers (Logic instances) ---
        self.color_picker_manager = ColorPickerManager(initial_color=self.selected_qcolor, config_save_path_func=get_user_config_file_path)
        self.static_layouts_manager = StaticLayoutsManager(
            user_static_layouts_path=os.path.join(self.user_documents_presets_path, "static", "user"),
            prefab_static_layouts_path=os.path.join(self.bundled_presets_base_path, "static", "prefab")
        )
        self.animator_manager = AnimatorManagerWidget(
            user_sequences_base_path=os.path.join(self.user_documents_presets_path, "sequences", "user"),
            sampler_recordings_path=os.path.join(self.user_documents_presets_path, "sequences", "sampler_recordings"),
            prefab_sequences_base_path=os.path.join(self.bundled_presets_base_path, "sequences", "prefab"),
            parent=self 
        )
        self.screen_sampler_manager = ScreenSamplerManager( 
            presets_base_path=self.bundled_presets_base_path, 
            animator_manager_ref=self.animator_manager, 
            parent=self 
        )
        if self.akai_controller:
            self.oled_display_manager = OLEDDisplayManager(akai_fire_controller_ref=self.akai_controller, parent=self)
            self.hardware_input_manager = HardwareInputManager(akai_fire_controller_ref=self.akai_controller, parent=self)
        else:
            QMessageBox.critical(self, "Fatal Error", "AkaiFireController failed. Exiting."); sys.exit(1)
            
        # --- Initialize UI Element References for Hardware Replica (Top Strip) ---
        # These are initialized to None, actual QWidget creation happens in helper methods.
        self.pad_grid_frame: InteractivePadGridFrame | None = None # Crucial for pad interactions
        self.knob_volume_top_right: QDial | None = None
        self.knob_pan_top_right: QDial | None = None
        self.knob_filter_top_right: QDial | None = None
        self.knob_resonance_top_right: QDial | None = None
        self.oled_display_mirror_widget: QLabel | None = None 
        self.knob_select_top_right: QDial | None = None


        self.button_pattern_song_top_right: QPushButton | None = None
        self.button_browser_top_right: QPushButton | None = None
        self.button_pattern_up_top_right: QPushButton | None = None
        self.button_pattern_down_top_right: QPushButton | None = None
        self.button_grid_nav_focus_prev_top_right: QPushButton | None = None 
        self.button_grid_nav_focus_next_top_right: QPushButton | None = None
        self.mute_solo_buttons: list[QPushButton] = []
        self.mode_buttons: dict[str, QPushButton] = {}
        self.button_shift: QPushButton|None=None; self.button_alt: QPushButton|None=None
        self.transport_buttons: dict[str, QPushButton] = {}
        self.utility_buttons_bottom: dict[str, QPushButton] = {}

        self.is_animator_playing: bool = False

        # References for right panel UI elements
        self.port_combo_direct_ref: QComboBox | None = None
        self.input_port_combo_direct_ref: QComboBox | None = None
        self.connect_button_direct_ref: QPushButton | None = None
        self.quick_tools_group_ref: QGroupBox | None = None 
        self.eyedropper_button: QPushButton | None = None

        self.ensure_user_dirs_exist()
        
        # --- Main UI Layout Initialization ---
        self._init_ui_layout()  # Set up layouts and widgets

        # --- Populate panels (order is important!) ---
        # print("MW __init__: Populating BOTH panels.") # Optional debug
        self._populate_left_panel()   # This sets self.pad_grid_frame
        self._populate_right_panel()

        self.global_pad_brightness: float = 1.0
        # References to the top 4 GUI knobs
        self.gui_knob1: QDial | None = None
        self.gui_knob2: QDial | None = None
        self.gui_knob3: QDial | None = None
        self.gui_knob4: QDial | None = None

        # --- OLED Manager Signal Connection (if applicable after UI creation) ---
        if self.oled_display_manager:
            # Pass initial startup text settings to OLEDDisplayManager
            self.oled_display_manager.update_default_text_settings(
                self.oled_startup_text,
                self.oled_startup_font_family,
                self.oled_startup_font_size_px
            )
            self.oled_display_manager.update_scroll_speed(self.oled_global_scroll_delay_ms)
            self.oled_display_manager.startup_animation_finished.connect(self._on_oled_startup_animation_finished)

        self._oled_knob_feedback_timer = QTimer(self)
        self._oled_knob_feedback_timer.setSingleShot(True)
        self._oled_knob_feedback_timer.timeout.connect(self._revert_oled_after_knob_feedback)
        self._KNOB_FEEDBACK_OLED_DURATION_MS = 1500 
        self._stop_action_issued_for_oled: bool = False

        self._update_current_oled_nav_target_widget()
        self._connect_signals()  # pad_grid_frame and layouts are now guaranteed to exist
        self._create_edit_actions()
        self.populate_midi_ports()
        self.populate_midi_input_ports()
        self.update_connection_status()
        QTimer.singleShot(0, self._update_global_ui_interaction_states)

        if hasattr(self, 'knob_volume_top_right'): self.gui_knob1 = self.knob_volume_top_right
        if hasattr(self, 'knob_pan_top_right'): self.gui_knob2 = self.knob_pan_top_right
        if hasattr(self, 'knob_filter_top_right'): self.gui_knob3 = self.knob_filter_top_right
        if hasattr(self, 'knob_resonance_top_right'): self.gui_knob4 = self.knob_resonance_top_right

        self._setup_global_brightness_knob()

    def _get_presets_base_dir_path(self) -> str:
        """
        Determines the base path for bundled presets.
        Uses get_resource_path for PyInstaller compatibility.
        """
        # print(f"DEBUG MW: _get_presets_base_dir_path() called.") # Optional
        return get_resource_path(PRESETS_BASE_DIR_NAME)

    def _set_window_icon(self):
        """Sets the main application window icon."""
        try:
            icon_path = get_resource_path(os.path.join("resources", "icons", "app_icon.png"))
            if os.path.exists(icon_path):
                self.setWindowIcon(QIcon(icon_path))
            else:
                print(f"MW WARNING: Window icon not found at '{icon_path}'")
        except Exception as e:
            print(f"MW ERROR: Could not set window icon: {e}")

    def ensure_user_dirs_exist(self):
        """Creates user-specific directories for presets and recordings if they don't exist."""
        # print("MW INFO: Ensuring user directories exist.") # Optional
        # Prefab paths are for reference; actual creation is for user paths.
        # prefab_static_dir = os.path.join(self.bundled_presets_base_path, "static", "prefab")
        # prefab_sequences_dir = os.path.join(self.bundled_presets_base_path, "sequences", "prefab")
        
        user_static_layouts_base = os.path.join(self.user_documents_presets_path, "static")
        user_sequences_base = os.path.join(self.user_documents_presets_path, "sequences")
        
        paths_to_create = [
            # os.path.join(prefab_static_dir), # No need to create bundled paths, they should exist
            # os.path.join(prefab_sequences_dir),
            os.path.join(user_static_layouts_base, "user"), # User static layouts
            os.path.join(user_sequences_base, "user"),      # User animation sequences
            os.path.join(user_sequences_base, "sampler_recordings") # Sampler recordings
        ]
        for path in paths_to_create:
            try:
                os.makedirs(path, exist_ok=True)
            except Exception as e:
                print(f"MW WARNING: Could not create user directory '{path}': {e}")

    def _get_oled_config_filepath(self) -> str:
        """Returns the full path to the oled_config.json file."""
        # get_user_config_file_path is defined at module level or imported
        return get_user_config_file_path(OLED_CONFIG_FILENAME)

    def _load_oled_config(self):
        """Loads OLED startup text and font settings from JSON file."""
        filepath = self._get_oled_config_filepath()
        print(f"MW TRACE: Attempting to load OLED config from: {filepath}") # Debug
        try:
            if os.path.exists(filepath):
                with open(filepath, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                self.oled_startup_text = config.get("startup_text", DEFAULT_OLED_STARTUP_TEXT)
                self.oled_startup_font_family = config.get("startup_font_family", DEFAULT_OLED_FONT_FAMILY)
                self.oled_startup_font_size_px = config.get("startup_font_size_px", DEFAULT_OLED_FONT_SIZE_PX)
                self.oled_global_scroll_delay_ms = config.get("global_scroll_delay_ms", DEFAULT_OLED_SCROLL_DELAY_MS)
                print(f"MW INFO: Loaded OLED config: Text='{self.oled_startup_text}', Font='{self.oled_startup_font_family} {self.oled_startup_font_size_px}px'")
            else:
                print(f"MW INFO: OLED config file not found at '{filepath}'. Using defaults and creating file.")
                # Initialize with defaults if file doesn't exist
                self.oled_startup_text = DEFAULT_OLED_STARTUP_TEXT
                self.oled_startup_font_family = DEFAULT_OLED_FONT_FAMILY
                self.oled_startup_font_size_px = DEFAULT_OLED_FONT_SIZE_PX
                self._save_oled_config() # Save defaults to create the file
        except json.JSONDecodeError as e:
            print(f"MW WARNING: Error decoding OLED config JSON from '{filepath}': {e}. Using defaults and attempting to overwrite with valid JSON.")
            self.oled_startup_text = DEFAULT_OLED_STARTUP_TEXT; self.oled_startup_font_family = DEFAULT_OLED_FONT_FAMILY; self.oled_startup_font_size_px = DEFAULT_OLED_FONT_SIZE_PX
            self._save_oled_config() # Attempt to save a clean default file
        except Exception as e:
            print(f"MW WARNING: Generic error loading OLED config from '{filepath}': {e}. Using defaults.")
            self.oled_startup_text = DEFAULT_OLED_STARTUP_TEXT
            self.oled_startup_font_family = DEFAULT_OLED_FONT_FAMILY
            self.oled_startup_font_size_px = DEFAULT_OLED_FONT_SIZE_PX

    def _save_oled_config(self):
        """Saves current OLED startup text, font, and global scroll speed settings to JSON file."""
        filepath = self._get_oled_config_filepath()
        config = {
            "startup_text": self.oled_startup_text,
            "startup_font_family": self.oled_startup_font_family,
            "startup_font_size_px": self.oled_startup_font_size_px,
            "global_scroll_delay_ms": self.oled_global_scroll_delay_ms
            
        }
        print(f"MW TRACE: Attempting to save OLED config to: {filepath} with data: {config}")
        try:
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=4)
            print(f"MW INFO: Saved OLED config to '{filepath}'")
        except Exception as e:
            print(f"MW ERROR: Could not save OLED config to '{filepath}': {e}")


    def _setup_oled_mirror_clickable(self):
        """Makes the OLED mirror QLabel clickable to open the customizer."""
        if hasattr(self, 'oled_display_mirror_widget') and self.oled_display_mirror_widget:
            # To make QLabel clickable, we can install an event filter on it
            # or promote it to a custom clickable QLabel subclass.
            # Event filter is simpler for now.
            self.oled_display_mirror_widget.setToolTip("Click to customize OLED display")
            self.oled_display_mirror_widget.installEventFilter(self) # MainWindow will handle its events
            print("MW TRACE: OLED mirror configured for click.")
        else:
            print("MW WARNING: oled_display_mirror_widget not found during _setup_oled_mirror_clickable.")

    def eventFilter(self, obj, event):
        """
        Event filter to catch clicks on the oled_display_mirror_widget.
        """
        if hasattr(self, 'oled_display_mirror_widget') and obj == self.oled_display_mirror_widget:
            if event.type() == QEvent.Type.MouseButtonPress: # Corrected from QEvent.MouseButtonPress
                if event.button() == Qt.MouseButton.LeftButton:
                    self._open_oled_customizer_dialog()
                    return True # Event handled
        return super().eventFilter(obj, event) # Pass on other events

    def _open_oled_customizer_dialog(self):
        """Opens the OLED Customizer Dialog."""
        # print("MW TRACE: Opening OLED Customizer Dialog...") # Optional
        dialog = OLEDCustomizerDialog(
            current_text=self.oled_startup_text,
            current_font_family=self.oled_startup_font_family,
            current_font_size_px=self.oled_startup_font_size_px,
            # --- ADD: Pass current global scroll delay ---
            current_global_scroll_delay_ms=self.oled_global_scroll_delay_ms,
            # --- END ADD ---
            parent=self
        )
        # The dialog's signal now emits 4 arguments
        try: dialog.startup_settings_changed.disconnect(self._on_oled_startup_settings_changed)
        except: pass
        dialog.startup_settings_changed.connect(self._on_oled_startup_settings_changed)
        
        if dialog.exec():
            print("MW INFO: OLED Customizer Dialog accepted (saved).")
        else:
            print("MW INFO: OLED Customizer Dialog cancelled.")
        
        dialog.deleteLater()

    def _on_oled_startup_settings_changed(self, new_text: str, new_font_family: str, new_font_size_px: int, new_scroll_delay_ms: int):
        self.oled_startup_text = new_text
        self.oled_startup_font_family = new_font_family
        self.oled_startup_font_size_px = new_font_size_px
        self.oled_global_scroll_delay_ms = new_scroll_delay_ms # Update attribute
        
        self._save_oled_config() # Save all new settings

        if self.oled_display_manager:
            # Update text and font settings
            self.oled_display_manager.update_default_text_settings(
                self.oled_startup_text,
                self.oled_startup_font_family,
                self.oled_startup_font_size_px
            )
            # --- THIS CALL WAS MISSING OR NEEDS TO BE ENSURED ---
            self.oled_display_manager.update_scroll_speed(self.oled_global_scroll_delay_ms)
            # --- END ENSURE ---
        
        print(f"MW INFO: OLED settings updated: Text='{new_text}', Font='{new_font_family} {new_font_size_px}px', ScrollDelay={new_scroll_delay_ms}ms")


    def _initial_knob_setup_based_on_sampler_state(self):
        """Called shortly after startup to set initial knob configs."""
        if self.screen_sampler_manager:
            self._on_sampler_activity_changed_for_knobs(self.screen_sampler_manager.is_sampling_active())
        else:
            self._on_sampler_activity_changed_for_knobs(False) # Default to global mode

    def _revert_oled_after_knob_feedback(self):
        """
        Called by the _oled_knob_feedback_timer timeout.
        Tells OLEDDisplayManager to restore its display after knob feedback.
        """
        if self.oled_display_manager:
            # print(f"MW TRACE: Reverting OLED from knob feedback.") # Optional
            self.oled_display_manager.revert_after_knob_feedback()
        # _oled_previous_intended_text is now managed within OLEDDisplayManager if needed,
        # or simply by its state logic. MainWindow doesn't need to store it.
        # Let's remove self._oled_previous_intended_text attribute from MainWindow.
        # The OLEDDisplayManager.get_current_intended_display_text() is what matters before showing knob value.

    def _show_knob_feedback_on_oled(self, feedback_text: str):
        """
        Helper to display temporary knob feedback on the OLED.
        Manages storing previous OLED state and starting the revert timer.
        """
        if self.oled_display_manager:
            # If the timer is not already active, it means this is the "first" knob turn
            # in a potential sequence of turns. We don't need to store previous text anymore
            # as OLEDDisplayManager.revert_after_knob_feedback() will handle it.
            
            self.oled_display_manager.show_temporary_knob_value(feedback_text)
            self._oled_knob_feedback_timer.start(self._KNOB_FEEDBACK_OLED_DURATION_MS)


    def _create_hardware_top_strip(self) -> QGroupBox:
        """
        Creates a QGroupBox containing replicas of the Akai Fire's top control strip elements.
        PHASE 1.I: Increase triangle font size for clarity.
        """
        print("MW TRACE: _create_hardware_top_strip - PHASE 1.I: INCREASE TRIANGLE FONT - START")
        top_strip_group = QGroupBox("Device Controls")
        top_strip_main_layout = QHBoxLayout(top_strip_group)
        top_strip_main_layout.setContentsMargins(8, 8, 8, 8) 
        top_strip_main_layout.setSpacing(10)

        knob_size = 45
        # --- CHANGE: Increase font size for all triangle labels ---
        triangle_label_style = "font-size: 11pt; color: #E0E0E0; font-weight: bold;" # Was 9pt, try 11pt
        
        flat_button_width = 40
        flat_button_height = 12 
        flat_button_size = QSize(flat_button_width, flat_button_height)

        # --- Section 1: Four Main Knobs (No changes) ---
        # ... (code for section 1 as before) ...
        section1_knobs_widget = QWidget()
        section1_knobs_layout = QHBoxLayout(section1_knobs_widget)
        section1_knobs_layout.setContentsMargins(0, 0, 0, 0); section1_knobs_layout.setSpacing(10)
        knob_info = [("knob_volume_top_right", "Volume"), ("knob_pan_top_right", "Pan"), ("knob_filter_top_right", "Filter"), ("knob_resonance_top_right", "Resonance")]
        for attr_name, tooltip_text in knob_info:
            knob_container_vbox = QVBoxLayout(); knob_container_vbox.setAlignment(Qt.AlignmentFlag.AlignCenter)
            knob = QDial(); knob.setFixedSize(QSize(knob_size, knob_size)); knob.setNotchesVisible(True)
            knob.setObjectName(attr_name); knob.setRange(0, 127); knob.setValue(64); knob.setToolTip(tooltip_text)
            setattr(self, attr_name, knob)
            knob_container_vbox.addWidget(knob); section1_knobs_layout.addLayout(knob_container_vbox)
        top_strip_main_layout.addWidget(section1_knobs_widget, 0, Qt.AlignmentFlag.AlignVCenter)

        # --- Section 2: PATTERN UP/DOWN Buttons (Style applied to triangles) ---
        pattern_buttons_widget = QWidget()
        pattern_buttons_layout = QVBoxLayout(pattern_buttons_widget)
        pattern_buttons_layout.setContentsMargins(0,0,0,0); pattern_buttons_layout.setSpacing(3)
        pattern_buttons_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        triangle_up_label = QLabel("▲"); triangle_up_label.setStyleSheet(triangle_label_style); triangle_up_label.setObjectName("TrianglePatternUp"); triangle_up_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        pattern_buttons_layout.addWidget(triangle_up_label)
        self.button_pattern_up_top_right = QPushButton(""); self.button_pattern_up_top_right.setObjectName("PatternUpButton"); self.button_pattern_up_top_right.setFixedSize(flat_button_size); self.button_pattern_up_top_right.setToolTip("Pattern Up")
        pattern_buttons_layout.addWidget(self.button_pattern_up_top_right)
        self.button_pattern_down_top_right = QPushButton(""); self.button_pattern_down_top_right.setObjectName("PatternDownButton"); self.button_pattern_down_top_right.setFixedSize(flat_button_size); self.button_pattern_down_top_right.setToolTip("Pattern Down")
        pattern_buttons_layout.addWidget(self.button_pattern_down_top_right)
        triangle_down_label = QLabel("▼"); triangle_down_label.setStyleSheet(triangle_label_style); triangle_down_label.setObjectName("TrianglePatternDown"); triangle_down_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        pattern_buttons_layout.addWidget(triangle_down_label)
        top_strip_main_layout.addWidget(pattern_buttons_widget, 0, Qt.AlignmentFlag.AlignCenter)

        # --- Section 3: OLED Display (No changes) ---
        # ... (code for section 3 as before) ...
        self.oled_display_mirror_widget = QLabel()
        oled_w, oled_h = OLED_MIRROR_WIDTH, OLED_MIRROR_HEIGHT; display_scale = OLED_MIRROR_SCALE
        self.oled_display_mirror_widget.setFixedSize(QSize(int(oled_w * display_scale), int(oled_h * display_scale)))
        self.oled_display_mirror_widget.setObjectName("OLEDMirror"); self.oled_display_mirror_widget.setStyleSheet("QLabel#OLEDMirror { background-color: black; border: 1px solid #444444; }")
        self.oled_display_mirror_widget.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._setup_oled_mirror_clickable()

        blank_pixmap = QPixmap(self.oled_display_mirror_widget.size()); blank_pixmap.fill(Qt.GlobalColor.black); self.oled_display_mirror_widget.setPixmap(blank_pixmap)
        top_strip_main_layout.addWidget(self.oled_display_mirror_widget, 0, Qt.AlignmentFlag.AlignCenter)


        # --- Section 4: BROWSER Button (No changes) ---
        # ... (code for section 4 as before) ...
        self.button_browser_top_right = QPushButton(""); self.button_browser_top_right.setObjectName("BrowserButton"); self.button_browser_top_right.setFixedSize(QSize(30, 30)); self.button_browser_top_right.setToolTip("Browser / Toggle Sampler")
        top_strip_main_layout.addWidget(self.button_browser_top_right, 0, Qt.AlignmentFlag.AlignCenter)
        
        # --- Section 5: SELECT Knob (No changes) ---
        # ... (code for section 5 as before) ...
        select_knob_container_vbox = QVBoxLayout(); select_knob_container_vbox.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.knob_select_top_right = QDial(); self.knob_select_top_right.setFixedSize(QSize(knob_size, knob_size)); self.knob_select_top_right.setNotchesVisible(True); self.knob_select_top_right.setObjectName("SelectKnobTopRight"); self.knob_select_top_right.setToolTip("Select Item / Press to Apply")
        select_knob_container_vbox.addWidget(self.knob_select_top_right)
        top_strip_main_layout.addLayout(select_knob_container_vbox, 0)

        # --- Section 6: GRID L/R Buttons ---
        grid_buttons_widget = QWidget()
        grid_buttons_widget.setSizePolicy(QSizePolicy.Policy.MinimumExpanding, QSizePolicy.Policy.Preferred)
        grid_buttons_layout = QHBoxLayout(grid_buttons_widget)
        grid_buttons_layout.setContentsMargins(0,0,0,0); grid_buttons_layout.setSpacing(2) 
        grid_buttons_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        triangle_left_label = QLabel("◀"); triangle_left_label.setStyleSheet(triangle_label_style)
        triangle_left_label.setObjectName("TriangleGridLeft")
        # --- CHANGE: Adjust fixed width if needed for new font size ---
        triangle_left_label.setFixedWidth(20) # Was 18, try 20 for 11pt font
        triangle_left_label.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight) 
        grid_buttons_layout.addWidget(triangle_left_label, 0, Qt.AlignmentFlag.AlignVCenter)

        self.button_grid_nav_focus_prev_top_right = QPushButton("")
        self.button_grid_nav_focus_prev_top_right.setObjectName("GridLeftButton") 
        self.button_grid_nav_focus_prev_top_right.setFixedSize(flat_button_size)
        self.button_grid_nav_focus_prev_top_right.setToolTip("Cycle Navigation Focus (Prev)")
        grid_buttons_layout.addWidget(self.button_grid_nav_focus_prev_top_right, 0, Qt.AlignmentFlag.AlignVCenter)

        grid_buttons_layout.addSpacing(8) 

        self.button_grid_nav_focus_next_top_right = QPushButton("")
        self.button_grid_nav_focus_next_top_right.setObjectName("GridRightButton") 
        self.button_grid_nav_focus_next_top_right.setFixedSize(flat_button_size)
        self.button_grid_nav_focus_next_top_right.setToolTip("Cycle Navigation Focus (Next)")
        grid_buttons_layout.addWidget(self.button_grid_nav_focus_next_top_right, 0, Qt.AlignmentFlag.AlignVCenter)

        triangle_right_label = QLabel("▶"); triangle_right_label.setStyleSheet(triangle_label_style)
        triangle_right_label.setObjectName("TriangleGridRight")
        # --- CHANGE: Adjust fixed width if needed for new font size ---
        triangle_right_label.setFixedWidth(20) # Was 18, try 20 for 11pt font
        triangle_right_label.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
        grid_buttons_layout.addWidget(triangle_right_label, 0, Qt.AlignmentFlag.AlignVCenter)
        
        top_strip_main_layout.addWidget(grid_buttons_widget, 0, Qt.AlignmentFlag.AlignVCenter)

        top_strip_main_layout.addStretch(1)
        top_strip_group.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        print("MW TRACE: _create_hardware_top_strip - PHASE 1.I: INCREASE TRIANGLE FONT - FINISHED")
        return top_strip_group

    def _populate_right_panel(self):
        """Populates the right panel with MIDI controls, Color Picker, Tools, and Layouts."""
        # --- MODIFIED GUARD: Check for actual None, not just truthiness ---
        if self.right_panel_layout_v is None:
        # --- END MODIFIED GUARD ---
            print("MW CRITICAL ERROR: _populate_right_panel - self.right_panel_layout_v is LITERALLY None! CANNOT POPULATE.")
            return
        # If we reach here, self.right_panel_layout_v is a valid (even if 'falsy' when empty) layout object.
        # print(f"MW TRACE: _populate_right_panel - START - Layout object IS: {self.right_panel_layout_v} (ID: {id(self.right_panel_layout_v)})")


        # --- MIDI Connection Group (Output) ---
        connection_group = QGroupBox("🔌 MIDI Output") 
        connection_layout = QHBoxLayout(connection_group) # This should be fine as QGroupBox becomes parent
        self.port_combo_direct_ref = QComboBox()
        self.port_combo_direct_ref.setPlaceholderText("Select MIDI Output")
        if hasattr(self, '_on_port_combo_changed'): # Check if method exists before connecting
            self.port_combo_direct_ref.currentIndexChanged.connect(self._on_port_combo_changed)
        self.connect_button_direct_ref = QPushButton("Connect")
        if hasattr(self, 'toggle_connection'): # Check if method exists
            self.connect_button_direct_ref.clicked.connect(self.toggle_connection)
        self.connect_button_direct_ref.setEnabled(False) 
        connection_layout.addWidget(QLabel("Port:"))
        connection_layout.addWidget(self.port_combo_direct_ref, 1) 
        connection_layout.addWidget(self.connect_button_direct_ref)
        self.right_panel_layout_v.addWidget(connection_group)

        # --- MIDI Input Group ---
        if hasattr(self, '_create_midi_input_section'):
             midi_input_gb = self._create_midi_input_section()
             if midi_input_gb:
                self.right_panel_layout_v.addWidget(midi_input_gb)
             else:
                print("MW WARNING: _create_midi_input_section returned None.")
        else: 
            # self.right_panel_layout_v.addWidget(QLabel("Error: MIDI Input UI Missing")) # Avoid adding error labels to UI for now
            print("MW WARNING: _create_midi_input_section method missing.")

        # --- Color Picker Manager UI ---
        if self.color_picker_manager:
            self.right_panel_layout_v.addWidget(self.color_picker_manager)
        else:
            print("MW WARNING: ColorPickerManager not available to add to right panel.")

        # --- Quick Tools Group Box ---
        if hasattr(self, '_init_direct_controls_right_panel'):
            quick_tools_widget = self._init_direct_controls_right_panel()
            if quick_tools_widget:
                self.quick_tools_group_ref = quick_tools_widget # Assignment
                self.right_panel_layout_v.addWidget(self.quick_tools_group_ref)
            else:
                print("MW WARNING: _init_direct_controls_right_panel returned None.")
        else:
            # self.right_panel_layout_v.addWidget(QLabel("Error: Quick Tools UI Missing"))
            print("MW WARNING: _init_direct_controls_right_panel method missing.")

        # --- Static Layouts Manager UI ---
        if self.static_layouts_manager:
            self.right_panel_layout_v.addWidget(self.static_layouts_manager)
        else:
            print("MW WARNING: StaticLayoutsManager not available to add to right panel.")
        
        self.right_panel_layout_v.addStretch(1)
        print(f"MW TRACE: _populate_right_panel - FINISHED")
        # --- END OF _populate_right_panel ---


    def _populate_left_panel(self):
        """Populates the left panel with the hardware top strip, pad grid, animator UI, and sampler UI."""
        if self.left_panel_layout is None:
            print("MW CRITICAL ERROR: _populate_left_panel - self.left_panel_layout is LITERALLY None! CANNOT POPULATE.")
            return
        print(f"MW TRACE: _populate_left_panel - START - Layout object IS: {self.left_panel_layout} (ID: {id(self.left_panel_layout)})")

        # 1. Add Hardware Top Strip
        if hasattr(self, '_create_hardware_top_strip'):
            hardware_top_strip_widget = self._create_hardware_top_strip()
            if hardware_top_strip_widget:
                # Stretch factor 0: takes its preferred size
                self.left_panel_layout.addWidget(hardware_top_strip_widget, 0) 
            else:
                print("MW WARNING: _create_hardware_top_strip did not return a widget.")
        else:
            print("MW ERROR: _create_hardware_top_strip method is missing.")
            self.left_panel_layout.addWidget(QLabel("Error: Hardware Top Strip Missing"))

        # 2. Add Pad Grid Section
        if hasattr(self, '_create_pad_grid_section'):
            pad_grid_container = self._create_pad_grid_section() 
            if pad_grid_container:
                # Stretch factor 0: takes its preferred size
                self.left_panel_layout.addWidget(pad_grid_container, 0) 
            else:
                print("MW WARNING: _create_pad_grid_section did not return a widget.")
        else:
            print("MW ERROR: _create_pad_grid_section method is missing.")
            self.left_panel_layout.addWidget(QLabel("Error: Pad Grid Section Missing"))
        
        # 3. Add AnimatorManagerWidget UI
        if self.animator_manager: 
            self.left_panel_layout.addWidget(self.animator_manager, 1) # Stretch factor 1 (IMPORTANT)
        else:
            print("MW WARNING: AnimatorManager not instantiated, cannot add its UI to left panel.")
            self.left_panel_layout.addWidget(QLabel("Error: Animator UI Missing"))

        # 4. Add ScreenSamplerManager UI
        if self.screen_sampler_manager: 
            sampler_ui_widget = self.screen_sampler_manager.get_ui_widget()
            if sampler_ui_widget:
                # Stretch factor 0: takes its preferred size
                self.left_panel_layout.addWidget(sampler_ui_widget, 0)
            else:
                print("MW WARNING: ScreenSamplerManager UI widget (from get_ui_widget()) is None.")
                self.left_panel_layout.addWidget(QLabel("Error: Sampler UI Widget Missing"))
        else:
            print("MW WARNING: ScreenSamplerManager not instantiated, cannot add its UI to left panel.")
            self.left_panel_layout.addWidget(QLabel("Error: Sampler Manager Missing"))

        # Removed addStretch(1) to allow AnimatorManagerWidget to take all remaining space.
        print(f"MW TRACE: _populate_left_panel - FINISHED")
    # In class MainWindow(QMainWindow):

    def _init_ui_layout(self):
        """
        Initializes the main window layout structure.
        CLEANUP VERSION: Removes test borders and test labels.
        - Create central widget.
        - Create main QHBoxLayout, SET it on central_widget.
        - Create left_panel_widget (QWidget) and left_panel_layout (QVBoxLayout).
        - SET left_panel_layout on left_panel_widget.
        - ADD left_panel_widget to main_app_layout.
        - Create right_panel_widget (QWidget) and right_panel_layout_v (QVBoxLayout).
        - SET right_panel_layout_v on right_panel_widget.
        - ADD right_panel_widget to main_app_layout.
        - Set status bar.
        Goal: Clean UI structure ready for actual content population.
        """
        # print("MW TRACE: _init_ui_layout - CLEANUP VERSION START")

        # 1. Create the central widget
        self.central_widget_main = QWidget()
        self.setCentralWidget(self.central_widget_main)
        # print(f"MW TRACE: _init_ui_layout - Central widget set: {self.central_widget_main}") # Optional

        # 2. Create and set the main application layout (QHBoxLayout)
        # print("MW TRACE: _init_ui_layout - Creating self.main_app_layout = QHBoxLayout()") # Optional
        self.main_app_layout = QHBoxLayout()
        # print(f"MW TRACE: _init_ui_layout - Setting layout on central_widget_main. Layout obj: {self.main_app_layout}") # Optional
        self.central_widget_main.setLayout(self.main_app_layout)
        self.main_app_layout.setSpacing(10)
        self.main_app_layout.setContentsMargins(5, 5, 5, 5)
        # print(f"MW TRACE: _init_ui_layout - main_app_layout configured and set on central_widget.") # Optional

        # 3. --- Left Panel ---
        # print("\nMW TRACE: _init_ui_layout - --- Processing Left Panel Structure ---") # Optional
        self.left_panel_widget = QWidget()
        self.left_panel_widget.setObjectName("LeftPanelWidget") # Generic name now
        # print(f"MW TRACE: _init_ui_layout - self.left_panel_widget created: {self.left_panel_widget}") # Optional

        # print("MW TRACE: _init_ui_layout - Creating self.left_panel_layout = QVBoxLayout()") # Optional
        self.left_panel_layout = QVBoxLayout()
        # print(f"MW TRACE: _init_ui_layout - Setting layout on left_panel_widget. Layout obj: {self.left_panel_layout}") # Optional
        self.left_panel_widget.setLayout(self.left_panel_layout)
        self.left_panel_layout.setContentsMargins(0, 0, 0, 0)
        self.left_panel_layout.setSpacing(8)
        # print(f"MW TRACE: _init_ui_layout - left_panel_layout configured and set on left_panel_widget.") # Optional

        
        if self.main_app_layout is not None:
            self.main_app_layout.addWidget(self.left_panel_widget, 2) # Stretch factor 2
            # print(f"MW TRACE: _init_ui_layout - Added left_panel_widget to main_app_layout.") # Optional
        # else: # Optional
            # print("MW CRITICAL _init_ui_layout: self.main_app_layout IS None before adding left_panel_widget.")


        # 4. --- Right Panel ---
        # print("\nMW TRACE: _init_ui_layout - --- Processing Right Panel Structure ---") # Optional
        self.right_panel_widget = QWidget()
        self.right_panel_widget.setObjectName("RightPanelWidget") # Generic name now
        # print(f"MW TRACE: _init_ui_layout - self.right_panel_widget created: {self.right_panel_widget}") # Optional

        # print("MW TRACE: _init_ui_layout - Creating self.right_panel_layout_v = QVBoxLayout()") # Optional
        self.right_panel_layout_v = QVBoxLayout()
        # print(f"MW TRACE: _init_ui_layout - Setting layout on right_panel_widget. Layout obj: {self.right_panel_layout_v}") # Optional
        self.right_panel_widget.setLayout(self.right_panel_layout_v)
        # Restore original sizing for right panel
        self.right_panel_widget.setMinimumWidth(360) 
        self.right_panel_widget.setMaximumWidth(400) 
        self.right_panel_widget.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)
        # print(f"MW TRACE: _init_ui_layout - right_panel_layout_v configured and set on right_panel_widget.") # Optional


        if self.main_app_layout is not None:
            self.main_app_layout.addWidget(self.right_panel_widget, 1) # Stretch factor 1
            # print(f"MW TRACE: _init_ui_layout - Added right_panel_widget to main_app_layout.") # Optional
        else: # Optional
            print("MW CRITICAL _init_ui_layout: self.main_app_layout IS None before adding right_panel_widget.")

        # --- Status Bar ---
        # print("\nMW TRACE: _init_ui_layout - Setting up Status Bar") # Optional
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready. Please connect to AKAI Fire.") # Restore original status message
        # print(f"MW TRACE: _init_ui_layout - Status bar set.") # Optional

    def _update_oled_and_title_on_sequence_change(self, is_modified: bool, sequence_name: str | None):
        """
        Updates the main window title and sends the sequence name/status
        to the OLEDDisplayManager when the animator's sequence status changes.
        """
        # print(f"DEBUG MW: _update_oled_and_title_on_sequence_change - Mod: {is_modified}, Name: '{sequence_name}'") # Optional
        
        base_title = "AKAI Fire Customizer Interface" # Simpler title for replica view
        effective_title_name = sequence_name if sequence_name and sequence_name.strip() and sequence_name != "New Sequence" else "Untitled"        
        title = f"{base_title} - {effective_title_name}"
        if is_modified:
            title += "*" 
        self.setWindowTitle(title)
        if self.oled_display_manager:
            text_for_oled = None 
            if sequence_name and sequence_name.strip() and sequence_name != "New Sequence":
                text_for_oled = sequence_name            
            if text_for_oled and is_modified: # Add asterisk only if there's a base name
                text_for_oled += "*"       
            self.oled_display_manager.set_display_text(text_for_oled) 
            # print(f"DEBUG MW: Called OLEDManager.set_display_text with: '{text_for_oled}' for sequence change.") # Optional
   
    def _create_pad_grid_section(self) -> QWidget:
        """Creates the pad grid widget and its immediate container."""
        pad_grid_outer_container = QWidget() 
        pad_grid_container_layout = QVBoxLayout(pad_grid_outer_container)
        pad_grid_container_layout.setContentsMargins(0, 0, 0, 0) 
        
        self.pad_grid_frame = InteractivePadGridFrame(parent=self) 
        pad_grid_container_layout.addWidget(self.pad_grid_frame, 0, Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)        
        return pad_grid_outer_container   

    def _create_midi_input_section(self) -> QGroupBox:
        """Creates the QGroupBox for MIDI Input selection."""
        input_connection_group = QGroupBox("🔌 MIDI Input (from Fire)")
        input_layout = QHBoxLayout(input_connection_group)
        
        self.input_port_combo_direct_ref = QComboBox()
        # print(f"DEBUG MW: _create_midi_input_section - input_port_combo ID: {id(self.input_port_combo_direct_ref)}") # Optional
        self.input_port_combo_direct_ref.setPlaceholderText("Select MIDI Input")
        # input_port_combo_direct_ref.currentIndexChanged.connect(...) # Connect in _connect_signals or if specific logic needed here
        
        input_layout.addWidget(QLabel("Input Port:"))
        input_layout.addWidget(self.input_port_combo_direct_ref, 1) # ComboBox takes available space
        return input_connection_group
    
    def _handle_paint_black_button(self):
        """
        Handles the 'Set Black' button click from Quick Tools.
        Sets the current painting color to black.
        """
        if self.screen_sampler_manager and self.screen_sampler_manager.is_sampling_active():
            # Optional: Decide if this button should also stop the sampler
            # self.screen_sampler_manager.stop_sampling_thread() 
            # self.status_bar.showMessage("Sampler stopped by 'Set Black' action.", 2000)
            pass # For now, let it just change the color, user can stop sampler separately
        black_color = QColor("black")
        self.selected_qcolor = black_color # Update MainWindow's selected color
        if self.color_picker_manager:
            # Tell ColorPickerManager to update its UI to reflect black is now selected
            self.color_picker_manager.set_current_selected_color(black_color, source="paint_black_button")        
        self.status_bar.showMessage("Active painting color set to: Black (Off)", 2500)

    def _init_direct_controls_right_panel(self) -> QGroupBox:
        """Initializes the 'Quick Tools' QGroupBox for direct pad/color operations."""
        tool_buttons_group = QGroupBox("🛠️ Quick Tools")
        tool_buttons_layout = QHBoxLayout(tool_buttons_group) # Horizontal layout for buttons
        # Button to set current painting color to black
        color_button_off = QPushButton("Set Black") # Local var, assign to self if needed elsewhere
        color_button_off.setToolTip("Set current painting color to Black (Off).")
        color_button_off.clicked.connect(self._handle_paint_black_button)
        tool_buttons_layout.addWidget(color_button_off)        
        # Button to clear all pads (hardware and current GUI/Animator frame)
        clear_all_button = QPushButton("Clear Pads") # Local var
        clear_all_button.setToolTip("Clear all hardware pads and the current GUI/Animator frame to Black.")
        clear_all_button.clicked.connect(self.clear_all_hardware_and_gui_pads)
        tool_buttons_layout.addWidget(clear_all_button)
        # Eyedropper toggle button
        self.eyedropper_button = QPushButton("💧 Eyedropper") # Assign to self for QAction sync
        self.eyedropper_button.setToolTip("Toggle Eyedropper mode (I): Click a pad to pick its color.")
        self.eyedropper_button.setCheckable(True)
        self.eyedropper_button.toggled.connect(self._on_eyedropper_button_toggled)
        tool_buttons_layout.addWidget(self.eyedropper_button)                
        return tool_buttons_group
    
    def _init_animator_and_sampler_ui_left_panel(self):
        """Initializes and adds Animator and Screen Sampler UIs to the left panel."""
        # --- Animator Manager Widget ---
        self.animator_manager = AnimatorManagerWidget(
            user_sequences_base_path=os.path.join(self.user_documents_presets_path, "sequences", "user"),
            sampler_recordings_path=os.path.join(self.user_documents_presets_path, "sequences", "sampler_recordings"),
            prefab_sequences_base_path=os.path.join(self.bundled_presets_base_path, "sequences", "prefab"),
            parent=self # Pass parent if AnimatorManagerWidget is QWidget
        )
        self.left_panel_layout.addWidget(self.animator_manager) # Add to left panel
        # --- ScreenSamplerManager ---
        self.screen_sampler_manager = ScreenSamplerManager( 
            presets_base_path=self.bundled_presets_base_path, # For potential future sampler prefabs
            animator_manager_ref=self.animator_manager, # For saving recordings
            parent=self # Pass parent if ScreenSamplerManager is QObject/QWidget based for its UI
        )
        self.left_panel_layout.addWidget(self.screen_sampler_manager.get_ui_widget()) # Add its UI part        
        self.left_panel_layout.addStretch(1) # Push animator/sampler UI up if space allows

    # --- MIDI Port Population Methods ---
    def populate_midi_ports(self):
        """Populates the MIDI output port selection QComboBox."""
        if self.port_combo_direct_ref is None: 
            print("MW ERROR: Output port combo is None, cannot populate.")
            return           
        self.port_combo_direct_ref.blockSignals(True) # Avoid triggering changed signal during repopulation
        self.port_combo_direct_ref.clear()     
        ports = []
        try:
            ports = AkaiFireController.get_available_output_ports()
        except Exception as e:
            print(f"MW ERROR: Failed to get MIDI output ports: {e}")        
        if ports: # Check if list is not None and not empty
            self.port_combo_direct_ref.addItems(ports)
            self.port_combo_direct_ref.setEnabled(True) # Enable if ports found            
            fire_port_idx = -1
            for i, port_name in enumerate(ports): # Find "Fire" or "Akai" port
                if isinstance(port_name, str) and \
                   ("fire" in port_name.lower() or "akai" in port_name.lower()) and \
                   "midiin" not in port_name.lower(): # Exclude input ports
                    fire_port_idx = i
                    break                                
            if fire_port_idx != -1:
                self.port_combo_direct_ref.setCurrentIndex(fire_port_idx)
            elif self.port_combo_direct_ref.count() > 0: # If no Fire port, select first available
                self.port_combo_direct_ref.setCurrentIndex(0)
            # If count is 0 after attempting to add, it remains empty (handled by else below)        
        if self.port_combo_direct_ref.count() == 0: # If still empty after trying
            self.port_combo_direct_ref.addItem("No MIDI output ports found")
            self.port_combo_direct_ref.setEnabled(False) # Disable if no ports            
        self.port_combo_direct_ref.blockSignals(False)
        # Manually trigger handler for current selection to update button state
        self._on_port_combo_changed(self.port_combo_direct_ref.currentIndex())

    def populate_midi_input_ports(self):
        """Populates the MIDI input port selection QComboBox."""
        # print("DEBUG MW: populate_midi_input_ports CALLED") # Optional
        if self.input_port_combo_direct_ref is None:
            print("MW CRITICAL ERROR: Input port combo is None. Cannot populate.")
            return
        self.input_port_combo_direct_ref.blockSignals(True)
        self.input_port_combo_direct_ref.clear()
        ports = []
        try:
            ports = AkaiFireController.get_available_input_ports()
        except Exception as e:
            print(f"MW ERROR: Failed to get MIDI input ports: {e}")
        if ports:
            self.input_port_combo_direct_ref.addItems(ports)
            fire_port_idx = -1
            for i, port_name in enumerate(ports):
                if isinstance(port_name, str) and ("fire" in port_name.lower() or "akai" in port_name.lower()):
                    # No need to check for "midiin" as these are already input ports
                    fire_port_idx = i
                    break
            if fire_port_idx != -1:
                self.input_port_combo_direct_ref.setCurrentIndex(fire_port_idx)
            elif self.input_port_combo_direct_ref.count() > 0:
                self.input_port_combo_direct_ref.setCurrentIndex(0)
            self.input_port_combo_direct_ref.setEnabled(True)        
        if self.input_port_combo_direct_ref.count() == 0:
            self.input_port_combo_direct_ref.addItem("No MIDI input ports found")
            self.input_port_combo_direct_ref.setEnabled(False)            
        self.input_port_combo_direct_ref.blockSignals(False)
        # print("DEBUG MW: populate_midi_input_ports FINISHED.") # Optional

    def _provide_grid_colors_for_static_save(self):
        """
        Handles the request_current_grid_colors signal from StaticLayoutsManager.
        Provides the current colors from the main pad grid to the manager for saving.
        """
        if self.static_layouts_manager and self.pad_grid_frame:
            current_colors_hex = self.pad_grid_frame.get_current_grid_colors_hex()
            # Tell StaticLayoutsManager to proceed with saving these colors
            # The StaticLayoutsManager will then handle the "Save As" dialog.
            self.static_layouts_manager.save_layout_with_colors(current_colors_hex)
            # print(f"MW DEBUG: Provided grid colors to StaticLayoutsManager for saving.") # Optional
        else: # Optional
            if self.status_bar:
                self.status_bar.showMessage("Cannot save layout: UI components missing or not ready.", 3000)

    def _setup_global_brightness_knob(self):
        """Configures Knob 1 (gui_knob1) for its default global pad brightness role."""
        if self.gui_knob1:
            # Disconnect any previous connections first to be safe during re-configuration
            try: self.gui_knob1.valueChanged.disconnect()
            except TypeError: pass # No connections or already disconnected
            self.gui_knob1.setToolTip(f"Global Pad Brightness ({int(self.global_pad_brightness * 100)}%)")
            self.gui_knob1.setRange(0, 100)
            self.gui_knob1.setValue(int(self.global_pad_brightness * 100))
            self.gui_knob1.valueChanged.connect(self._on_global_brightness_knob_changed)
            # print("MW TRACE: Knob 1 configured for Global Brightness.") # Optional
        else: # Optional
            print("MW WARNING: gui_knob1 not found during _setup_global_brightness_knob.")

    def _handle_apply_static_layout_data(self, colors_hex: list):
        """
        Handles the apply_layout_data_requested signal from StaticLayoutsManager.
        Applies the given color data to the main pad grid and hardware.
        Also updates the current animator frame if an animator sequence is active.
        """
        if not self.akai_controller or not self.akai_controller.is_connected():
            self.status_bar.showMessage("Connect to Akai Fire first to apply layout.", 2500)
            return

        # Stop any ongoing processes like sampler or animator playback
        if self.screen_sampler_manager and self.screen_sampler_manager.is_sampling_active():
            self.screen_sampler_manager.stop_sampling_thread()
            self.status_bar.showMessage("Sampler stopped by applying static layout.", 2000)       
        if self.animator_manager and self.animator_manager.active_sequence_model and \
           self.animator_manager.active_sequence_model.get_is_playing():
            self.animator_manager.action_stop() # Stop animator playback
            self.status_bar.showMessage("Animation stopped by applying static layout.", 2000)
        # Apply colors to the main GUI grid and hardware
        # When applying a static layout, it should not bypass global brightness by default
        self.apply_colors_to_main_pad_grid(colors_hex, update_hw=True, is_sampler_output=False)        
        # If an animator sequence is currently active, also update its current edit frame
        # with this static layout. This makes the static layout the content of the current frame.
        if self.animator_manager and self.animator_manager.active_sequence_model:
            # This updates the model, which should then emit signals to update the timeline display
            # and mark the sequence as modified.
            self.animator_manager.active_sequence_model.update_all_pads_in_current_edit_frame(colors_hex)
            self.status_bar.showMessage("Static layout applied to pads and current animator frame.", 2500)
        else:
            self.status_bar.showMessage("Static layout applied to pads.", 2500)

    def _connect_signals(self):
        """Connects signals from various UI components and managers to their handlers in MainWindow."""
        # print("MW TRACE: _connect_signals CALLED.") # Keep for debugging signal issues
        # InteractivePadGridFrame signals
        if self.pad_grid_frame: # <<<< THIS LINE AND THE NEXT THREE
           self.pad_grid_frame.pad_action_requested.connect(self._handle_grid_pad_action)
           self.pad_grid_frame.pad_context_menu_requested_from_button.connect(self.show_pad_context_menu)
           self.pad_grid_frame.pad_single_left_click_action_requested.connect(self._handle_grid_pad_single_left_click)
        else:
            print("MW TRACE WARNING: self.pad_grid_frame is None during _connect_signals.")               
        # Color Picker Manager signals
        if self.color_picker_manager:
           self.color_picker_manager.final_color_selected.connect(self._handle_final_color_selection_from_manager)
           self.color_picker_manager.status_message_requested.connect(self.status_bar.showMessage)       
        else:
            print("MW TRACE WARNING: self.color_picker_manager is None during _connect_signals.")               
            # Static Layouts Manager signals
        if self.static_layouts_manager:
            self.static_layouts_manager.apply_layout_data_requested.connect(self._handle_apply_static_layout_data)
            self.static_layouts_manager.request_current_grid_colors.connect(self._provide_grid_colors_for_static_save)
            self.static_layouts_manager.status_message_requested.connect(self.status_bar.showMessage)
        else:
            print("MW TRACE WARNING: self.static_layouts_manager is None during _connect_signals.")            
        # Screen Sampler Manager signals
        if self.screen_sampler_manager:
            self.screen_sampler_manager.sampled_colors_for_display.connect(
                lambda colors: self.apply_colors_to_main_pad_grid(
                    [QColor(r, g, b).name() for r, g, b in colors], update_hw=True
                )
            )
            self.screen_sampler_manager.sampler_status_update.connect(self.status_bar.showMessage)
            self.screen_sampler_manager.sampling_activity_changed.connect(self._on_sampler_activity_changed)
            self.screen_sampler_manager.new_sequence_from_recording_ready.connect(self._handle_load_sequence_request)
            # NEW Connection for Monitor Cycle OLED Feedback from ScreenSamplerManager
            self.screen_sampler_manager.sampler_monitor_changed.connect(self._on_sampler_monitor_cycled_for_oled)
        else:
            print("MW TRACE WARNING: self.screen_sampler_manager is None during _connect_signals.")
        try:
            self.animator_manager.animator_playback_active_status_changed.disconnect(self._on_animator_playback_status_for_oled)
        except TypeError: pass
        self.animator_manager.animator_playback_active_status_changed.connect(self._on_animator_playback_status_for_oled)
        print("MW TRACE: Connected animator_playback_active_status_changed for OLED feedback.")
        # AnimatorManagerWidget Signals
        if self.animator_manager:
            self.animator_manager.active_frame_data_for_display.connect(self._on_animator_frame_data_for_display)
            self.animator_manager.playback_status_update.connect(self.status_bar.showMessage)
            self.animator_manager.sequence_modified_status_changed.connect(self._update_oled_and_title_on_sequence_change)
            self.animator_manager.animator_playback_active_status_changed.connect(self._update_fire_transport_leds)
            self.animator_manager.undo_redo_state_changed.connect(self._on_animator_undo_redo_state_changed)
            self.animator_manager.clipboard_state_changed.connect(self._on_animator_clipboard_state_changed)
            self.animator_manager.request_sampler_disable.connect(self._handle_request_sampler_disable)
            self.animator_manager.request_load_sequence_with_prompt.connect(self._handle_animator_request_load_prompt)
            self.animator_manager.animator_playback_active_status_changed.connect(self._on_animator_playback_status_changed_for_knobs)
        else:
            print("MW TRACE WARNING: self.animator_manager is None during _connect_signals.")
        # screen_sampler_manager signals for knobs
        if self.screen_sampler_manager:
            try: # Disconnect first if re-running this logic
                self.screen_sampler_manager.sampling_activity_changed.disconnect(self._on_sampler_activity_changed_for_knobs)
                self.screen_sampler_manager.sampler_adjustments_changed.disconnect(self._on_sampler_adjustments_updated_for_knobs)
            except TypeError:
                pass # Not connected yet            
            self.screen_sampler_manager.sampling_activity_changed.connect(self._on_sampler_activity_changed_for_knobs)
            self.screen_sampler_manager.sampler_adjustments_changed.connect(self._on_sampler_adjustments_updated_for_knobs)
            print("MW TRACE: Connected to ScreenSamplerManager activity & adjustments signals.")            
        # HardwareInputManager Signals
        if self.hardware_input_manager:
            # Disconnect old physical_encoder_1_rotated if it exists
            try: self.hardware_input_manager.physical_encoder_1_rotated.disconnect()
            except (TypeError, AttributeError): pass 
            # Connect to the new generic physical_encoder_rotated signal
            try: self.hardware_input_manager.physical_encoder_rotated.disconnect(self._on_physical_encoder_rotated)
            except (TypeError, AttributeError): pass # Not connected or signal doesn't exist yet in HIM            
            # Ensure HIM actually has this signal defined: physical_encoder_rotated = pyqtSignal(int, int)
            if hasattr(self.hardware_input_manager, 'physical_encoder_rotated'):
                self.hardware_input_manager.physical_encoder_rotated.connect(self._on_physical_encoder_rotated)
                print("MW TRACE: Connected to generic physical_encoder_rotated signal.")
            else:
                print("MW WARNING: HardwareInputManager missing 'physical_encoder_rotated' signal.")
            # Animator actions
            if self.animator_manager:
                self.hardware_input_manager.request_animator_play_pause.connect(self.animator_manager.action_play_pause_toggle)
                self.hardware_input_manager.request_animator_stop.connect(self.animator_manager.action_stop)                
            # Navigation actions
            self.hardware_input_manager.grid_left_pressed.connect(self._handle_grid_left_pressed)
            self.hardware_input_manager.grid_right_pressed.connect(self._handle_grid_right_pressed)
            self.hardware_input_manager.select_encoder_turned.connect(self._handle_select_encoder_turned)
            self.hardware_input_manager.select_encoder_pressed.connect(self._handle_select_encoder_pressed)                
            # Sampler control actions
            self.hardware_input_manager.request_toggle_screen_sampler.connect(self._on_request_toggle_screen_sampler)
            self.hardware_input_manager.request_cycle_sampler_monitor.connect(self._on_request_cycle_sampler_monitor)                
            # print("MW TRACE: Connected HardwareInputManager signals (animator, navigation, sampler).") # Optional
        else:
            print("MW TRACE WARNING: self.hardware_input_manager is None during _connect_signals.")            
        # OLEDDisplayManager Signal to AkaiFireController AND to GUI Mirror
        if self.oled_display_manager:
            if self.akai_controller: # Connection to physical device
                try:
                    self.oled_display_manager.request_send_bitmap_to_fire.disconnect(self.akai_controller.oled_send_full_bitmap)
                except: pass 
                try:
                    self.oled_display_manager.request_send_bitmap_to_fire.connect(self.akai_controller.oled_send_full_bitmap)
                except Exception as e: print(f"MW ERROR: Connect OLED to AkaiCtrl: {e}")                
            # --- Connection to GUI OLED Mirror ---
            if self.oled_display_mirror_widget: # Check if mirror widget exists
                try:
                    self.oled_display_manager.request_send_bitmap_to_fire.disconnect(self._update_oled_mirror)
                except: pass
                try:
                    self.oled_display_manager.request_send_bitmap_to_fire.connect(self._update_oled_mirror)
                    # print("MW TRACE: Connected OLEDManager signal to GUI mirror.") # Optional
                except Exception as e_mirror: print(f"MW ERROR: Connect OLED to GUI mirror: {e_mirror}")
        elif not self.oled_display_manager:
            print("MW TRACE WARNING: self.oled_display_manager is None during OLED signal connection attempt.")
        elif not self.akai_controller:
            print("MW TRACE WARNING: self.akai_controller is None during OLED signal connection attempt.")

    def _on_physical_encoder_rotated(self, encoder_id: int, delta: int):
        """
        Handles rotation from any of the physical encoders 1-4.
        Dispatches to global brightness, sampler adjustment, or animator speed logic.
        """
        # print(f"MW TRACE: _on_physical_encoder_rotated - Encoder ID: {encoder_id}, Delta: {delta}, AnimatorPlaying: {self.is_animator_playing}, SamplerActive: {self.screen_sampler_manager.is_sampling_active() if self.screen_sampler_manager else False}") # Optional

        target_knob: QDial | None = None
        step: int = 0
        handler_to_call = None # Stores the method to call after updating GUI knob

        # Determine context and target knob/handler
        if self.is_animator_playing:
            if encoder_id == 4: # Knob 4 -> Animator Speed
                target_knob = self.gui_knob4
                step = self.ANIMATOR_SPEED_KNOB_STEP
                handler_to_call = self._on_animator_speed_knob_changed        
        elif self.screen_sampler_manager and self.screen_sampler_manager.is_sampling_active():
            # Sampler is active, Animator is NOT playing
            if encoder_id == 1: # Knob 1 -> Sampler Brightness
                target_knob = self.gui_knob1
                step = self.SAMPLER_FACTOR_KNOB_STEP
                handler_to_call = self._on_sampler_brightness_knob_changed
            elif encoder_id == 2: # Knob 2 -> Sampler Saturation
                target_knob = self.gui_knob2
                step = self.SAMPLER_FACTOR_KNOB_STEP
                handler_to_call = self._on_sampler_saturation_knob_changed
            elif encoder_id == 3: # Knob 3 -> Sampler Contrast
                target_knob = self.gui_knob3
                step = self.SAMPLER_FACTOR_KNOB_STEP
                handler_to_call = self._on_sampler_contrast_knob_changed
            elif encoder_id == 4: # Knob 4 -> Sampler Hue Shift
                target_knob = self.gui_knob4
                step = self.SAMPLER_HUE_KNOB_STEP
                handler_to_call = self._on_sampler_hue_knob_changed        
        else: # Global mode (Neither Animator playing nor Sampler active)
            if encoder_id == 1: # Knob 1 -> Global Pad Brightness
                target_knob = self.gui_knob1
                step = self.GLOBAL_BRIGHTNESS_KNOB_STEP
                handler_to_call = self._on_global_brightness_knob_changed
            # Knobs 2, 3, 4 are unassigned in global mode for now
        # If a target knob and action were determined
        if target_knob and handler_to_call and step != 0:
            current_gui_value = target_knob.value()
            new_gui_value = current_gui_value + (delta * step)            
            # Clamp to the target knob's current min/max range
            # These ranges are set by _update_contextual_knob_configs
            new_gui_value = max(target_knob.minimum(), min(new_gui_value, target_knob.maximum()))
            if new_gui_value != current_gui_value:
                # Block signals on the GUI knob, set its value, then unblock
                target_knob.blockSignals(True)
                target_knob.setValue(new_gui_value)
                target_knob.blockSignals(False)
                # Manually call the appropriate handler with the new GUI knob value
                # This handler will then update the model (SamplerManager, AnimatorManager, or global_brightness)
                # and also handle its own OLED feedback.
                handler_to_call(new_gui_value)                
                # print(f"MW TRACE: Physical Enc {encoder_id} (delta {delta}) -> GUI Knob new value {new_gui_value} for handler {handler_to_call.__name__}") # Optional
        else: # Optional
            print(f"MW TRACE: No action for physical encoder {encoder_id} in current context.")


    def _on_global_brightness_knob_changed(self, gui_knob_value: int):
        """
        Handles changes to the global brightness knob (Knob 1) in GLOBAL mode.
        Updates the global_pad_brightness, tooltip, AkaiFireController, and re-applies current grid colors.
        Also shows OLED feedback.
        """
        self.global_pad_brightness = gui_knob_value / 100.0
        tooltip_text = f"Global Pad Brightness ({gui_knob_value}%)"
        if self.gui_knob1:
            self.gui_knob1.setToolTip(tooltip_text)
        # --- OLED FEEDBACK ---
        oled_feedback_text = f"GlbBr: {gui_knob_value}%"
        self._show_knob_feedback_on_oled(oled_feedback_text)
        if self.akai_controller:
            self.akai_controller.set_global_brightness_factor(self.global_pad_brightness)
        sampler_is_active = self.screen_sampler_manager and self.screen_sampler_manager.is_sampling_active()
        animator_is_playing = (
            self.animator_manager and
            self.animator_manager.active_sequence_model and
            self.animator_manager.active_sequence_model.get_is_playing()
        )
        if not sampler_is_active and not animator_is_playing and self.pad_grid_frame:
            current_colors_hex = self.pad_grid_frame.get_current_grid_colors_hex()
            self.apply_colors_to_main_pad_grid(current_colors_hex, update_hw=True, is_sampler_output=False)

    def _on_sampler_brightness_knob_changed(self, gui_knob_value: int): # Value is 0-400
        if self.screen_sampler_manager:
            # Map GUI knob value (0-400) to sampler factor (e.g., 0.0 to 4.0)
            # Sampler factor = GUI knob value / 100.0
            sampler_factor = gui_knob_value / 100.0 
            # Clamp to typical sampler range if necessary, e.g., min 0.1 or 0.0
            sampler_factor = max(0.0, sampler_factor) # Ensure non-negative            
            self.screen_sampler_manager.update_sampler_adjustment('brightness', sampler_factor)
            if self.gui_knob1:
                self.gui_knob1.setToolTip(f"Sampler: Brightness ({sampler_factor:.2f}x)")

    # Implement similarly for _on_sampler_saturation_knob_changed, _on_sampler_contrast_knob_changed
    def _on_sampler_saturation_knob_changed(self, gui_knob_value: int): # Value is 0-400
        if self.screen_sampler_manager:
            sampler_factor = gui_knob_value / 100.0
            sampler_factor = max(0.0, sampler_factor)
            self.screen_sampler_manager.update_sampler_adjustment('saturation', sampler_factor)
            if self.gui_knob2:
                self.gui_knob2.setToolTip(f"Sampler: Saturation ({sampler_factor:.2f}x)")

    def _on_sampler_contrast_knob_changed(self, gui_knob_value: int): # Value is 0-400
        if self.screen_sampler_manager:
            sampler_factor = gui_knob_value / 100.0
            sampler_factor = max(0.0, sampler_factor)
            self.screen_sampler_manager.update_sampler_adjustment('contrast', sampler_factor)
            if self.gui_knob3:
                self.gui_knob3.setToolTip(f"Sampler: Contrast ({sampler_factor:.2f}x)")

    def _on_sampler_hue_knob_changed(self, gui_knob_value: int): # Value is -180 to 180
        if self.screen_sampler_manager:
            # Value is already in degrees
            self.screen_sampler_manager.update_sampler_adjustment('hue_shift', float(gui_knob_value))
            if self.gui_knob4:
                self.gui_knob4.setToolTip(f"Sampler: Hue Shift ({gui_knob_value:+d}°)")

    # _on_sampler_activity_changed_for_knobs needs to use the correct mapping when setting initial knob values
    def _on_sampler_activity_changed_for_knobs(self, sampler_is_active: bool):
        """
        Reconfigures the top 4 GUI knobs based on sampler active state.
        Disconnects old signals, sets new ranges, values, tooltips, and connects new signals.
        """
        print(f"MW TRACE: _on_sampler_activity_changed_for_knobs: Sampler active = {sampler_is_active}")
        knobs_to_reconfigure = [self.gui_knob1, self.gui_knob2, self.gui_knob3, self.gui_knob4]
        for knob in knobs_to_reconfigure:
            if knob:
                try: knob.valueChanged.disconnect()
                except TypeError: pass 
        if sampler_is_active and self.screen_sampler_manager:
            adj = self.screen_sampler_manager.current_sampler_params.get('adjustments', 
            ScreenSamplerCore.DEFAULT_ADJUSTMENTS.copy())            
            if self.gui_knob1: # Brightness
                brightness_factor = adj.get('brightness', 1.0)
                self.gui_knob1.setRange(self.SAMPLER_BRIGHTNESS_KNOB_MIN, self.SAMPLER_BRIGHTNESS_KNOB_MAX)
                self.gui_knob1.setValue(int(round(brightness_factor * 100)))
                self.gui_knob1.setToolTip(f"Sampler: Brightness ({brightness_factor:.2f}x)")
                self.gui_knob1.valueChanged.connect(self._on_sampler_brightness_knob_changed)
            if self.gui_knob2: # Saturation
                saturation_factor = adj.get('saturation', 1.0)
                self.gui_knob2.setRange(self.SAMPLER_SATURATION_KNOB_MIN, self.SAMPLER_SATURATION_KNOB_MAX)
                self.gui_knob2.setValue(int(round(saturation_factor * 100)))
                self.gui_knob2.setToolTip(f"Sampler: Saturation ({saturation_factor:.2f}x)")
                self.gui_knob2.valueChanged.connect(self._on_sampler_saturation_knob_changed)
            if self.gui_knob3: # Contrast
                contrast_factor = adj.get('contrast', 1.0)
                self.gui_knob3.setRange(self.SAMPLER_CONTRAST_KNOB_MIN, self.SAMPLER_CONTRAST_KNOB_MAX)
                self.gui_knob3.setValue(int(round(contrast_factor * 100)))
                self.gui_knob3.setToolTip(f"Sampler: Contrast ({contrast_factor:.2f}x)")
                self.gui_knob3.valueChanged.connect(self._on_sampler_contrast_knob_changed)
            if self.gui_knob4: # Hue Shift
                hue_val_float = adj.get('hue_shift', 0) 
                hue_val_int_for_knob_and_tooltip = int(round(hue_val_float))
                self.gui_knob4.setRange(self.SAMPLER_HUE_KNOB_MIN, self.SAMPLER_HUE_KNOB_MAX)
                self.gui_knob4.setValue(hue_val_int_for_knob_and_tooltip) 
                self.gui_knob4.setToolTip(f"Sampler: Hue Shift ({hue_val_int_for_knob_and_tooltip:+d})") # Removed °
                self.gui_knob4.valueChanged.connect(self._on_sampler_hue_knob_changed)            
            print("MW TRACE: Knobs configured for SAMPLER mode.")
        else: # Sampler is OFF - Configure for Global mode
            self._setup_global_brightness_knob() 
            if self.gui_knob2: 
                self.gui_knob2.setToolTip("Pan (Global - Unassigned)")
                self.gui_knob2.setRange(0,127); self.gui_knob2.setValue(64)
            if self.gui_knob3: 
                self.gui_knob3.setToolTip("Filter (Global - Unassigned)")
                self.gui_knob3.setRange(0,127); self.gui_knob3.setValue(64)
            if self.gui_knob4: 
                self.gui_knob4.setToolTip("Resonance (Global - Unassigned)")
                self.gui_knob4.setRange(0,127); self.gui_knob4.setValue(64)
            print("MW TRACE: Knobs configured for GLOBAL mode.")

    # _on_sampler_adjustments_updated_for_knobs should also use the correct mapping
    def _on_sampler_adjustments_updated_for_knobs(self, adjustments: dict):
        """
        Called when ScreenSamplerManager reports its adjustments have changed
        (e.g., from its dialog). Updates the GUI knobs if sampler is active.
        """
        if not (self.screen_sampler_manager and self.screen_sampler_manager.is_sampling_active()):
            return 
        # print(f"MW TRACE: _on_sampler_adjustments_updated_for_knobs: Received new adjustments: {adjustments}") # Optional
        if self.gui_knob1:
            self.gui_knob1.blockSignals(True)
            brightness_factor = adjustments.get('brightness', 1.0)
            self.gui_knob1.setValue(int(round(brightness_factor * 100))) 
            self.gui_knob1.setToolTip(f"Sampler: Brightness ({brightness_factor:.2f}x)")
            self.gui_knob1.blockSignals(False)        
        if self.gui_knob2:
            self.gui_knob2.blockSignals(True)
            saturation_factor = adjustments.get('saturation', 1.0)
            self.gui_knob2.setValue(int(round(saturation_factor * 100)))
            self.gui_knob2.setToolTip(f"Sampler: Saturation ({saturation_factor:.2f}x)")
            self.gui_knob2.blockSignals(False)
        if self.gui_knob3:
            self.gui_knob3.blockSignals(True)
            contrast_factor = adjustments.get('contrast', 1.0)
            self.gui_knob3.setValue(int(round(contrast_factor * 100)))
            self.gui_knob3.setToolTip(f"Sampler: Contrast ({contrast_factor:.2f}x)")
            self.gui_knob3.blockSignals(False)
        if self.gui_knob4: 
            self.gui_knob4.blockSignals(True)
            hue_val_float_adj = adjustments.get('hue_shift', 0)
            hue_val_int_for_knob_and_tooltip = int(round(hue_val_float_adj))
            self.gui_knob4.setValue(hue_val_int_for_knob_and_tooltip)
            self.gui_knob4.setToolTip(f"Sampler: Hue Shift ({hue_val_int_for_knob_and_tooltip:+d})")
            self.gui_knob4.blockSignals(False)
    def _update_contextual_knob_configs(self):
        sampler_is_active = self.screen_sampler_manager and self.screen_sampler_manager.is_sampling_active()
        # self.is_animator_playing is updated by the signal from AnimatorManagerWidget
        # Disconnect all current valueChanged signals from knobs 1-4 first
        for knob in [self.gui_knob1, self.gui_knob2, self.gui_knob3, self.gui_knob4]:
            if knob:
                try: knob.valueChanged.disconnect()
                except TypeError: pass
        # Configure Knob 1 (Global Brightness or Sampler Brightness)
        if sampler_is_active:
            # Setup Knob 1 for Sampler Brightness
            adj_s = self.screen_sampler_manager.current_sampler_params.get('adjustments', ScreenSamplerCore.DEFAULT_ADJUSTMENTS.copy())
            if self.gui_knob1:
                val_b = int(adj_s.get('brightness', 1.0) * 100)
                self.gui_knob1.setRange(self.SAMPLER_BRIGHTNESS_KNOB_MIN, self.SAMPLER_BRIGHTNESS_KNOB_MAX)
                self.gui_knob1.setValue(val_b)
                self.gui_knob1.setToolTip(f"Sampler: Brightness ({adj_s.get('brightness', 1.0):.2f}x)")
                self.gui_knob1.valueChanged.connect(self._on_sampler_brightness_knob_changed)
        else:
            # Setup Knob 1 for Global Pad Brightness
            self._setup_global_brightness_knob() # This already connects its signal
        # Configure Knobs 2 & 3 (Sampler Saturation/Contrast or Global Unassigned)
        if sampler_is_active:
            adj_s = self.screen_sampler_manager.current_sampler_params.get('adjustments', ScreenSamplerCore.DEFAULT_ADJUSTMENTS.copy())
            if self.gui_knob2: # Sampler Saturation
                val_s = int(adj_s.get('saturation', 1.0) * 100)
                self.gui_knob2.setRange(self.SAMPLER_SATURATION_KNOB_MIN, self.SAMPLER_SATURATION_KNOB_MAX)
                self.gui_knob2.setValue(val_s)
                self.gui_knob2.setToolTip(f"Sampler: Saturation ({adj_s.get('saturation', 1.0):.2f}x)")
                self.gui_knob2.valueChanged.connect(self._on_sampler_saturation_knob_changed)
            if self.gui_knob3: # Sampler Contrast
                val_c = int(adj_s.get('contrast', 1.0) * 100)
                self.gui_knob3.setRange(self.SAMPLER_CONTRAST_KNOB_MIN, self.SAMPLER_CONTRAST_KNOB_MAX)
                self.gui_knob3.setValue(val_c)
                self.gui_knob3.setToolTip(f"Sampler: Contrast ({adj_s.get('contrast', 1.0):.2f}x)")
                self.gui_knob3.valueChanged.connect(self._on_sampler_contrast_knob_changed)
        else: # Sampler OFF - Global mode for Knobs 2 & 3
            if self.gui_knob2: self.gui_knob2.setToolTip("Pan (Global - Unassigned)"); self.gui_knob2.setRange(0,127); self.gui_knob2.setValue(64)
            if self.gui_knob3: self.gui_knob3.setToolTip("Filter (Global - Unassigned)"); self.gui_knob3.setRange(0,127); self.gui_knob3.setValue(64)
        # Configure Knob 4 (Animator Speed OR Sampler Hue OR Global Unassigned)
        if self.is_animator_playing and self.animator_manager and self.animator_manager.active_sequence_model:
            # Animator is PLAYING - Knob 4 controls Animator Speed
            current_fps = self.animator_manager.get_current_sequence_fps() # New method needed in AMW
            # Define FPS range for the knob, e.g., 1 to 60 FPS
            # These should be constants in MainWindow
            ANIMATOR_FPS_KNOB_MIN, ANIMATOR_FPS_KNOB_MAX = 1, 60 
            if self.gui_knob4:
                self.gui_knob4.setRange(ANIMATOR_FPS_KNOB_MIN, ANIMATOR_FPS_KNOB_MAX)
                self.gui_knob4.setValue(int(round(current_fps)))
                self.gui_knob4.setToolTip(f"Anim Speed: {current_fps:.1f} FPS")
                self.gui_knob4.valueChanged.connect(self._on_animator_speed_knob_changed)
                print("MW TRACE: Knob 4 configured for ANIMATOR SPEED.")
        elif sampler_is_active and self.screen_sampler_manager:
            # Sampler is ACTIVE, Animator is NOT PLAYING - Knob 4 controls Sampler Hue
            adj_s = self.screen_sampler_manager.current_sampler_params.get('adjustments', ScreenSamplerCore.DEFAULT_ADJUSTMENTS.copy())
            if self.gui_knob4:
                hue_val_float = adj_s.get('hue_shift', 0)
                hue_val_int = int(round(hue_val_float))
                self.gui_knob4.setRange(self.SAMPLER_HUE_KNOB_MIN, self.SAMPLER_HUE_KNOB_MAX)
                self.gui_knob4.setValue(hue_val_int)
                self.gui_knob4.setToolTip(f"Sampler: Hue Shift ({hue_val_int:+d})")
                self.gui_knob4.valueChanged.connect(self._on_sampler_hue_knob_changed)
                print("MW TRACE: Knob 4 configured for SAMPLER HUE.")
        else:
            # NEITHER Animator Playing NOR Sampler Active - Knob 4 is Global Resonance (or Unassigned)
            if self.gui_knob4:
                self.gui_knob4.setToolTip("Resonance (Global - Unassigned)")
                self.gui_knob4.setRange(0,127); self.gui_knob4.setValue(64)
                # self.gui_knob4.valueChanged.connect(self._on_global_resonance_knob_changed) # Future
                print("MW TRACE: Knob 4 configured for GLOBAL RESONANCE/UNASSIGNED.")

    def _on_animator_speed_knob_changed(self, knob_value: int): # knob_value is FPS (e.g., 1-60)
        if self.is_animator_playing and self.animator_manager:
            new_fps = float(knob_value)
            self.animator_manager.set_playback_fps(new_fps) # New method needed in AMW
            if self.gui_knob4:
                self.gui_knob4.setToolTip(f"Anim Speed: {new_fps:.1f} FPS")        
            # OLED Feedback for Animator Speed
            oled_feedback_text = f"Spd: {new_fps:.1f}"
            self._show_knob_feedback_on_oled(oled_feedback_text)

    def _on_animator_playback_status_changed_for_knobs(self, is_playing: bool):
        """
        Slot connected to AnimatorManagerWidget's animator_playback_active_status_changed signal.
        Updates the internal flag and reconfigures knob functions if needed.
        """
        # print(f"MW TRACE: _on_animator_playback_status_changed_for_knobs: Animator playing = {is_playing}") # Optional
        self.is_animator_playing = is_playing
        self._update_contextual_knob_configs() # Re-evaluate and set knob functions   

    def _create_edit_actions(self):
        """Creates global QActions for menu items and keyboard shortcuts."""
        # Undo/Redo (Connected to AnimatorManagerWidget)
        self.undo_action = QAction("Undo Sequence Edit", self)
        self.undo_action.setShortcut(QKeySequence.StandardKey.Undo)
        self.undo_action.setToolTip(f"Undo last sequence edit ({QKeySequence(QKeySequence.StandardKey.Undo).toString(QKeySequence.SequenceFormat.NativeText)})")
        self.undo_action.triggered.connect(self.action_animator_undo)
        self.addAction(self.undo_action) # Add to window for global shortcut context
        self.redo_action = QAction("Redo Sequence Edit", self)
        self.redo_action.setShortcut(QKeySequence.StandardKey.Redo)
        self.redo_action.setToolTip(f"Redo last undone sequence edit ({QKeySequence(QKeySequence.StandardKey.Redo).toString(QKeySequence.SequenceFormat.NativeText)})")
        self.redo_action.triggered.connect(self.action_animator_redo)
        self.addAction(self.redo_action)
        # Animator Frame Operations (using icons from animator.controls_widget)
        self.copy_action = QAction(ICON_COPY + " Copy Frame(s)", self)
        self.copy_action.setShortcut(QKeySequence.StandardKey.Copy)
        self.copy_action.setToolTip(f"Copy selected frame(s) ({QKeySequence(QKeySequence.StandardKey.Copy).toString(QKeySequence.SequenceFormat.NativeText)})")
        self.copy_action.triggered.connect(self.action_animator_copy_frames)
        self.addAction(self.copy_action)
        # Cut, Paste, Duplicate, Delete
        self.cut_action = QAction(ICON_CUT + " Cut Frame(s)", self)
        self.cut_action.setShortcut(QKeySequence.StandardKey.Cut)
        self.cut_action.setToolTip(f"Cut selected frame(s) ({QKeySequence(QKeySequence.StandardKey.Cut).toString(QKeySequence.SequenceFormat.NativeText)})")
        self.cut_action.triggered.connect(self.action_animator_cut_frames)
        self.addAction(self.cut_action)
        self.paste_action = QAction(ICON_DUPLICATE + " Paste Frame(s)", self) # Icon might need review if it's for duplicate
        self.paste_action.setShortcut(QKeySequence.StandardKey.Paste)
        self.paste_action.setToolTip(f"Paste frame(s) from clipboard ({QKeySequence(QKeySequence.StandardKey.Paste).toString(QKeySequence.SequenceFormat.NativeText)})")
        self.paste_action.triggered.connect(self.action_animator_paste_frames)
        self.addAction(self.paste_action)
        self.duplicate_action = QAction(ICON_DUPLICATE + " Duplicate Frame(s)", self)
        self.duplicate_action.setShortcut(QKeySequence(Qt.Modifier.CTRL | Qt.Key.Key_D)) # Ctrl+D
        self.duplicate_action.setToolTip(f"Duplicate selected frame(s) (Ctrl+D)")
        self.duplicate_action.triggered.connect(self.action_animator_duplicate_frames)
        self.addAction(self.duplicate_action)
        self.delete_action = QAction(ICON_DELETE + " Delete Frame(s)", self)
        self.delete_action.setShortcut(QKeySequence.StandardKey.Delete)
        self.delete_action.setToolTip(f"Delete selected frame(s) (Del)")
        self.delete_action.triggered.connect(self.action_animator_delete_frames)
        self.addAction(self.delete_action)
        self.add_blank_global_action = QAction(ICON_ADD_BLANK + " Add Blank Frame", self)
        self.add_blank_global_action.setShortcut(QKeySequence(Qt.Modifier.CTRL | Qt.Modifier.SHIFT | Qt.Key.Key_B))
        self.add_blank_global_action.setToolTip("Add a new blank frame to the current sequence (Ctrl+Shift+B).")
        self.add_blank_global_action.triggered.connect(self.action_animator_add_blank_frame)
        self.addAction(self.add_blank_global_action)       
        # Sequence File Operations
        self.new_sequence_action = QAction("✨ New Sequence", self)
        self.new_sequence_action.setShortcut(QKeySequence.StandardKey.New)
        self.new_sequence_action.setToolTip(f"Create a new animation sequence ({QKeySequence(QKeySequence.StandardKey.New).toString(QKeySequence.SequenceFormat.NativeText)})")
        self.new_sequence_action.triggered.connect(lambda: self.action_animator_new_sequence(prompt_save=True))
        self.addAction(self.new_sequence_action)       
        self.save_sequence_as_action = QAction("💾 Save Sequence As...", self)
        # StandardKey.SaveAs often Ctrl+Shift+S, StandardKey.Save is Ctrl+S
        self.save_sequence_as_action.setShortcut(QKeySequence.StandardKey.SaveAs) 
        self.save_sequence_as_action.setToolTip(f"Save current sequence to a new file ({QKeySequence(QKeySequence.StandardKey.SaveAs).toString(QKeySequence.SequenceFormat.NativeText)})")
        self.save_sequence_as_action.triggered.connect(self.action_animator_save_sequence_as)
        self.addAction(self.save_sequence_as_action)
        # Eyedropper Toggle
        self.eyedropper_action = QAction("💧 Eyedropper Mode", self)
        self.eyedropper_action.setShortcut(QKeySequence(Qt.Key.Key_I)) # 'I' for eyedropper
        self.eyedropper_action.setToolTip("Toggle Eyedropper mode to pick color from a pad (I).")
        self.eyedropper_action.setCheckable(True) # Make it a toggle action
        self.eyedropper_action.triggered.connect(self.toggle_eyedropper_mode) # Connect to main toggle method
        self.addAction(self.eyedropper_action)
        # Animator Play/Pause Global Shortcut
        self.play_pause_action = QAction("Play/Pause Sequence", self)
        self.play_pause_action.setShortcut(QKeySequence(Qt.Key.Key_Space)) # Spacebar
        self.play_pause_action.setToolTip("Play or Pause the current animation sequence (Space).")
        self.play_pause_action.triggered.connect(self.action_animator_play_pause_toggle)
        self.addAction(self.play_pause_action)
        # Initial UI state update for actions (many will be disabled initially)
        self._update_global_ui_interaction_states()

    def clear_all_hardware_and_gui_pads(self):
        """
        Clears all hardware pads to black and also clears the current
        GUI pad grid representation (e.g., current animator frame).
        Stops active sampler or animator playback.
        """
        if not self.akai_controller or not self.akai_controller.is_connected():
            self.status_bar.showMessage("Connect to Akai Fire first to clear pads.", 2500)
            return        
        # Stop any ongoing processes that might interfere or immediately repaint
        if self.screen_sampler_manager and self.screen_sampler_manager.is_sampling_active():
             self.screen_sampler_manager.stop_sampling_thread()
             self.status_bar.showMessage("Sampler stopped by Clear Pads action.", 2000)        
        if self.animator_manager and self.animator_manager.active_sequence_model and \
           self.animator_manager.active_sequence_model.get_is_playing():
            self.animator_manager.action_stop() # Stop animator playback
            self.status_bar.showMessage("Animation stopped by Clear Pads action.", 2000)
        # Clear the GUI pad grid (this also sends black to hardware if update_hw=True)
        # When clearing all, we don't need to consider it "sampler_output" for brightness bypass
        self.clear_main_pad_grid_ui(update_hw=True, is_sampler_output=False) 
        # If an animator sequence is active, also clear the pads in its current edit frame
        if self.animator_manager and self.animator_manager.active_sequence_model:
            # This makes the current animator frame visually blank in the timeline
            self.animator_manager.active_sequence_model.clear_pads_in_current_edit_frame()
            # The active_frame_data_for_display signal from the model should then update the main grid,
            # but clear_main_pad_grid_ui already did that. This ensures model consistency.
        self.status_bar.showMessage("All pads and current GUI view cleared to black.", 2500)

    # --- Slots for Signals from Managers & UI Elements ---
    def _handle_request_sampler_disable(self):
        if self.screen_sampler_manager and self.screen_sampler_manager.is_sampling_active():
            self.screen_sampler_manager.stop_sampling_thread() 
            # self.status_bar.showMessage("Sampler deactivated by other component.", 2000) # Optional

    def _on_oled_startup_animation_finished(self):
        if self.oled_display_manager:
            # The default text and font are now managed by OLEDDisplayManager's
            # internal state, updated via update_default_text_settings.
            # We just need to tell it to display its "normal" text.
            # If a persistent override is active (e.g. sampler), it will show that instead.
            # If not, it shows self.oled_display_manager.normal_display_text (which should be startup_text)
            
            # This call will ensure the correct text (startup or persistent) is displayed
            # with the correct font and scrolling behavior.
            current_intended_text = self.oled_display_manager.get_current_intended_display_text()
            if current_intended_text is None: # If nothing specific, use the loaded startup text
                current_intended_text = self.oled_startup_text

            self.oled_display_manager.set_display_text(current_intended_text, scroll_if_needed=True)
            print(f"MW INFO: OLED startup animation finished. Displaying: '{current_intended_text}'")
        # else:
            # print("MW WARNING: OLEDManager not available to set default text after animation.")


    def _on_sampler_activity_changed(self, is_active: bool):
        """Handles sampler start/stop to update UI, OLED, and animator state."""
        # print(f"MW TRACE: _on_sampler_activity_changed - Sampler Active: {is_active}") # Optional
        if is_active: # Sampler just started
            if self.animator_manager:
                self.animator_manager.action_stop() # Stop animator playback if sampler starts
            
            if self.oled_display_manager:
                # Construct the persistent message for the OLED
                monitor_name_part = "Mon: ?" # Default
                if self.screen_sampler_manager and self.screen_sampler_manager.screen_sampler_monitor_list_cache:
                    current_mon_id = self.screen_sampler_manager.current_sampler_params.get('monitor_id', 1)
                    mon_info = next((m for m in self.screen_sampler_manager.screen_sampler_monitor_list_cache if m['id'] == current_mon_id), None)
                    if mon_info:
                        name_part = mon_info.get('name_for_ui', f"ID {current_mon_id}")
                        if "Monitor" in name_part and "(" in name_part: 
                            try: name_part = name_part.split("(")[0].strip()
                            except: pass
                        monitor_name_part = f"Mon: {name_part}"                
                override_text = f"SAMPLING ({monitor_name_part})"
                self.oled_display_manager.set_persistent_override(override_text, scroll_if_needed=True)
                # print(f"MW TRACE: Set OLED persistent override: '{override_text}'") # Optional        
        else: # Sampler just stopped
            if self.oled_display_manager:
                self.oled_display_manager.clear_persistent_override()
                # print("MW TRACE: Cleared OLED persistent override.") # Optional
                # OLEDDisplayManager will now revert to its normal_display_text 
                # (which should be current sequence name or default welcome message).
            # Restore animator's current frame to the grid if animator is not playing
            if self.animator_manager and self.animator_manager.active_sequence_model and \
               not self.animator_manager.active_sequence_model.get_is_playing():
                edit_idx = self.animator_manager.active_sequence_model.get_current_edit_frame_index()
                colors = self.animator_manager.active_sequence_model.get_frame_colors(edit_idx) 
                self._on_animator_frame_data_for_display(colors) 
            elif not self.animator_manager or not self.animator_manager.active_sequence_model:
                self._on_animator_frame_data_for_display(None) # Clear grid if no active sequence       
        self._update_global_ui_interaction_states()

    def _handle_final_color_selection_from_manager(self, color: QColor):
        """
        Handles the final_color_selected signal from the ColorPickerManager.
        Updates the main window's currently active painting color.
        """
        if isinstance(color, QColor) and color.isValid():
            self.selected_qcolor = color
            # print(f"MW DEBUG: Final color selected from manager: {color.name()}") # Optional debug
            if self.status_bar: # Check if status_bar exists
                 self.status_bar.showMessage(f"Active painting color set to: {color.name().upper()}", 3000)
        # else: # Optional
            # print(f"MW WARNING: Invalid color received from ColorPickerManager: {color}")
            # if self.status_bar:
            #     self.status_bar.showMessage(f"Invalid color selected.", 2000)

    def _on_animator_playback_status_for_oled(self, is_playing: bool):
        if not self.oled_display_manager:
            return
        oled_message = None
        # Use a short duration for these messages, e.g., 1 second
        message_duration_ms = 1000 
        if is_playing:
            oled_message = "▶ PLAY" # Or just "Play"
        else:
            # If is_playing is False, it could be a pause or a stop.
            # The _stop_action_issued_for_oled flag helps distinguish.
            if self._stop_action_issued_for_oled:
                # This case will be handled by action_animator_stop directly setting "Stopped"
                # So, if we reach here and stop_action_issued is true, it means the stop message
                # was already (or is about to be) displayed. We can simply reset the flag.
                self._stop_action_issued_for_oled = False 
                return # Avoid double-messaging "Paused" then "Stopped"
            else:
                oled_message = "❚❚ PAUSE" # Or just "Paused"        
        if oled_message:
            # Temporarily store current intended text, show message, then schedule revert
            # We can use the same timer mechanism as knob feedback, or simpler set_display_text with duration
            
            # Option 1: Using existing knob feedback helper (if you want consistent revert timing)
            # self._show_knob_feedback_on_oled(oled_message) # Reuses the 1.5s timer

            # Option 2: Using OLEDDisplayManager's temporary message feature (simpler for one-offs)
            # Ensure OLEDDisplayManager.set_display_text correctly handles reverting after temporary_duration_ms
            # and doesn't mess up persistent overrides if they were active.
            # The current OLEDDisplayManager set_display_text handles reverting to normal_display_text
            # or persistent_override_text correctly.
            
            current_intended_text = self.oled_display_manager.get_current_intended_display_text()
            self.oled_display_manager.set_display_text(oled_message, 
                                                       scroll_if_needed=False, # Short messages don't need scroll
                                                       temporary_duration_ms=message_duration_ms)
            # The _revert_from_temporary_text in OLEDDisplayManager will be called,
            # which should restore current_intended_text (or what normal_display_text became).

            # If we want to be absolutely sure it reverts to the exact text that was there:
            # (This is more like the knob feedback mechanism)
            # if not self._oled_knob_feedback_timer.isActive(): # Check if already showing knob value
            #     self._oled_previous_intended_text_for_revert = self.oled_display_manager.get_current_intended_display_text()
            # self.oled_display_manager.show_temporary_knob_value(oled_message) # Re-use this method
            # self._oled_knob_feedback_timer.start(message_duration_ms) # Use desired duration
    
    def _update_oled_mirror(self, packed_bitmap_data_7bit: bytearray):
        """
        Updates the on-screen OLED mirror widget with the content being sent
        to the physical OLED.
        """
        if not self.oled_display_mirror_widget:
            return
        if not hasattr(oled_renderer, '_unpack_fire_7bit_stream_to_logical_image'):
            # print("MW WARNING: oled_renderer missing _unpack_fire_7bit_stream_to_logical_image for mirror.") # Optional
            return
        try:
            # 1. Unpack the 7-bit stream to a logical PIL Image
            #    (This function needs to exist in oled_renderer.py)
            pil_image_logical = oled_renderer._unpack_fire_7bit_stream_to_logical_image(
                packed_bitmap_data_7bit, 
                OLED_MIRROR_WIDTH, # Use base dimensions for unpacking
                OLED_MIRROR_HEIGHT
            )
            if pil_image_logical:
                # 2. Convert PIL Image to QImage, then to QPixmap
                #    Requires Pillow to be installed and QImage.Format_Mono
                from PyQt6.QtGui import QImage # Import locally to method for clarity                
                # Convert PIL '1' mode image to QImage.Format_Mono
                # Data for QImage.Format_Mono is tricky: needs to be byte-aligned.
                # Pillow's tobytes() might give raw pixel data.
                # A common way is to iterate pixels or use an intermediate format.                
                # Simpler: Convert to RGB first then to QImage (less efficient but easier)
                pil_image_rgb = pil_image_logical.convert("RGB")
                data = pil_image_rgb.tobytes("raw", "RGB")
                qimage = QImage(data, pil_image_rgb.width, pil_image_rgb.height, QImage.Format.Format_RGB888)
                if not qimage.isNull():
                    q_pixmap = QPixmap.fromImage(qimage)
                    # Scale the pixmap to fit the QLabel mirror widget
                    scaled_pixmap = q_pixmap.scaled(
                        self.oled_display_mirror_widget.size(), # Scale to the QLabel's size
                        Qt.AspectRatioMode.KeepAspectRatio, # Or IgnoreAspectRatio if you want it to fill
                        Qt.TransformationMode.FastTransformation # Or SmoothTransformation
                    )
                    self.oled_display_mirror_widget.setPixmap(scaled_pixmap)
                else: # Optional
                    print("MW WARNING: OLED mirror QImage conversion failed.")
            else: # Optional
                print("MW WARNING: OLED mirror PIL image unpacking failed.")
        except Exception as e:
            print(f"MW ERROR: Updating OLED mirror: {e}")
            # Fallback: display a black pixmap or error message on the mirror
            fallback_pixmap = QPixmap(self.oled_display_mirror_widget.size())
            fallback_pixmap.fill(Qt.GlobalColor.black)
            # Could draw "Error" on this pixmap
            # painter = QPainter(fallback_pixmap)
            # painter.setPen(Qt.GlobalColor.red)
            # painter.drawText(fallback_pixmap.rect(), Qt.AlignmentFlag.AlignCenter, "Mirror Error")
            # painter.end()
            self.oled_display_mirror_widget.setPixmap(fallback_pixmap)

    def _on_animator_undo_redo_state_changed(self, can_undo: bool, can_redo: bool):
        if self.undo_action: self.undo_action.setEnabled(can_undo)
        if self.redo_action: self.redo_action.setEnabled(can_redo)
        self._update_global_ui_interaction_states() # Might affect other dependent actions

    def _update_fire_transport_leds(self, is_animator_playing: bool):
        """
        This method is called when animator playback state changes.
        Play/Stop LED control is now overridden in AkaiFireController to keep them OFF.
        This method can be left empty or log, as direct calls to set_play_led/set_stop_led
        will be forced to OFF by AkaiFireController.
        """
        # print(f"DEBUG MW: _update_fire_transport_leds - Animator playing: {is_animator_playing}. (Play/Stop LEDs are forced OFF by AkaiFireController)") # Optional        
        # No explicit calls to self.akai_controller.set_play_led() or set_stop_led() needed here
        # if AkaiFireController is forcing them off.
        # If you had other LEDs to control based on playback, that logic would go here.
        pass

    # --- Delegating Methods for QActions to AnimatorManagerWidget ---
    def action_animator_undo(self):
        if self.animator_manager: self.animator_manager.action_undo()
    def action_animator_redo(self):
        if self.animator_manager: self.animator_manager.action_redo()
    def action_animator_copy_frames(self):
        if self.animator_manager: self.animator_manager.action_copy_frames()
    def action_animator_cut_frames(self):
        if self.animator_manager: self.animator_manager.action_cut_frames()
    def action_animator_paste_frames(self):
        if self.animator_manager: self.animator_manager.action_paste_frames()
    def action_animator_duplicate_frames(self):
        if self.animator_manager: self.animator_manager.action_duplicate_selected_frames()
    def action_animator_delete_frames(self):
        if self.animator_manager: self.animator_manager.action_delete_selected_frames()
    def action_animator_add_blank_frame(self): # For global QAction
        if self.animator_manager: self.animator_manager.action_add_frame("blank") # Default add
    def action_animator_new_sequence(self, prompt_save=True): # For global QAction
        if self.animator_manager:
            # Handle "save current modified" prompt here in MainWindow
            if prompt_save and self.animator_manager.active_sequence_model and \
               self.animator_manager.active_sequence_model.is_modified:
                reply = QMessageBox.question(self, "Unsaved Changes",
                                             f"Animation '{self.animator_manager.active_sequence_model.name}' has unsaved changes. Save now?",
                                             QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel,
                                             QMessageBox.StandardButton.Cancel)
                if reply == QMessageBox.StandardButton.Save:
                    save_successful = self.animator_manager.action_save_sequence_as() # AMW handles dialog
                    if not save_successful: # User might cancel Save As dialog
                        self.status_bar.showMessage("New sequence creation cancelled.", 2000)
                        return # Don't proceed if save failed or was cancelled
                elif reply == QMessageBox.StandardButton.Cancel:
                    self.status_bar.showMessage("New sequence creation cancelled.", 2000)
                    return           
            # If Discard or if not modified, or if save was successful, proceed
            self.animator_manager.action_new_sequence(prompt_save=False) # Tell AMW not to prompt again

    def action_animator_save_sequence_as(self): # For global QAction
        if self.animator_manager: self.animator_manager.action_save_sequence_as()

    def action_animator_play_pause_toggle(self):
        if self.animator_manager:
            self.animator_manager.action_play_pause_toggle() 
            # --- REMOVE OR COMMENT OUT THIS LINE ---
            # self.clear_led_suppression_and_update() 
            # --- END REMOVE/COMMENT ---
            
            # If _update_fire_transport_leds has other side effects beyond just LEDs
            # (which it currently doesn't seem to), you might call it directly.
            # But if its only job was LED control and LEDs are forced off, this isn't strictly needed.
            # For robustness, let's call it, as animator_playback_active_status_changed is connected to it
            # and this ensures state consistency if its role expands.
            if self.animator_manager.active_sequence_model:
                 self._update_fire_transport_leds(self.animator_manager.active_sequence_model.get_is_playing())
            else:
                 self._update_fire_transport_leds(False)

        
    def _handle_animator_request_load_prompt(self, filepath_to_load: str):
        """Handles AnimatorManager's request to load, prompting for save if needed."""
        if not self.animator_manager: return
        proceed_with_load = True 
        if self.animator_manager.active_sequence_model and \
           self.animator_manager.active_sequence_model.is_modified:
            reply = QMessageBox.question(self, "Unsaved Animator Changes",
                                         f"Animation '{self.animator_manager.active_sequence_model.name}' has unsaved changes.\nSave before loading new sequence?",
                                         QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel,
                                         QMessageBox.StandardButton.Cancel) 
            if reply == QMessageBox.StandardButton.Save:
                if not self.animator_manager.action_save_sequence_as(): proceed_with_load = False
            elif reply == QMessageBox.StandardButton.Cancel: proceed_with_load = False 
            elif reply == QMessageBox.StandardButton.Discard: self.status_bar.showMessage("Changes discarded.",1500)
            else: proceed_with_load = False       
        if proceed_with_load:
            self.animator_manager._handle_load_sequence_request(filepath_to_load) # Tell AMW to do the actual load

    def _handle_load_sequence_request(self, filepath_to_load: str):
        """Handles loading a sequence (e.g., from sampler recording), prompting if needed."""
        # This is similar to _handle_animator_request_load_prompt but might have different context/messages.
        if not self.animator_manager: return
        proceed_with_load = True
        if self.animator_manager.active_sequence_model and \
           self.animator_manager.active_sequence_model.is_modified:
            reply = QMessageBox.question(self, "Unsaved Animator Changes",
                                         f"Current animation has unsaved changes. Save before loading '{os.path.basename(filepath_to_load)}'?",
                                         QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel,
                                         QMessageBox.StandardButton.Cancel)
            if reply == QMessageBox.StandardButton.Save:
                if not self.animator_manager.action_save_sequence_as(): proceed_with_load = False
            elif reply == QMessageBox.StandardButton.Cancel: proceed_with_load = False        
        if proceed_with_load:
            self.animator_manager._handle_load_sequence_request(filepath_to_load)
            self.status_bar.showMessage(f"Sequence '{os.path.basename(filepath_to_load)}' loaded.", 2500)

    # --- Eyedropper Methods ---
    def _on_eyedropper_button_toggled(self, checked: bool):
        self.set_eyedropper_mode(checked) # source is implicitly "button_toggle"

    def toggle_eyedropper_mode(self, checked: bool | None = None): # From QAction
        new_state = not self.is_eyedropper_mode_active if checked is None else checked
        self.set_eyedropper_mode(new_state)

    def set_eyedropper_mode(self, active: bool):
        if self.is_eyedropper_mode_active == active: return
        self.is_eyedropper_mode_active = active
        cursor_shape = Qt.CursorShape.CrossCursor if active else Qt.CursorShape.ArrowCursor
        if self.pad_grid_frame: self.pad_grid_frame.setCursor(cursor_shape)
        status_msg = "Eyedropper active: Click a pad." if active else "Eyedropper deactivated."
        self.status_bar.showMessage(status_msg, 0 if active else 2000)
        if self.eyedropper_button and self.eyedropper_button.isChecked() != active:
            self.eyedropper_button.setChecked(active)
        if self.eyedropper_action and self.eyedropper_action.isChecked() != active:
            self.eyedropper_action.setChecked(active)        
        self._update_global_ui_interaction_states()

    def _pick_color_from_pad(self, row: int, col: int):
        if not self.color_picker_manager or not self.pad_grid_frame: return
        # Assuming pad_grid_frame stores colors in a way that can be retrieved by row/col
        # For now, let's assume _get_current_main_pad_grid_colors returns a flat list
        all_grid_colors = self.pad_grid_frame.get_current_grid_colors_hex() 
        pad_1d_index = row * 16 + col 
        if 0 <= pad_1d_index < len(all_grid_colors):
            hex_color_str = all_grid_colors[pad_1d_index]
            picked_qcolor = QColor(hex_color_str)
            if picked_qcolor.isValid():
                self.color_picker_manager.set_current_selected_color(picked_qcolor, source="eyedropper")
                self.status_bar.showMessage(f"Color picked: {picked_qcolor.name().upper()}", 3000)
                self.set_eyedropper_mode(False) # Deactivate after pick
            else: self.status_bar.showMessage("Eyedropper: Invalid pad color.", 2000)
        else: self.status_bar.showMessage("Eyedropper: Invalid pad index.", 2000)

    # --- Pad Grid Interaction Handlers & Paint Logic ---
    def _handle_grid_pad_action(self, row: int, col: int, mouse_button: Qt.MouseButton):
        if mouse_button == Qt.MouseButton.LeftButton and self.is_eyedropper_mode_active:
            self._pick_color_from_pad(row, col); return 
        if self.screen_sampler_manager and self.screen_sampler_manager.is_sampling_active():
            self.screen_sampler_manager.stop_sampling_thread()
            self.status_bar.showMessage("Sampler stopped by pad interaction.", 2000)
        if self.animator_manager and self.animator_manager.active_sequence_model and \
           self.animator_manager.active_sequence_model.get_is_playing():
            self.animator_manager.action_stop()
            self.status_bar.showMessage("Animation stopped by pad interaction.", 2000)
        if mouse_button == Qt.MouseButton.LeftButton:
            self.apply_paint_to_pad(row, col, update_model=True)
        elif mouse_button == Qt.MouseButton.RightButton:
            self.apply_erase_to_pad(row, col, update_model=True)

    def apply_colors_to_main_pad_grid(self, colors_hex: list | None, update_hw: bool = True, is_sampler_output: bool = False):
        """
        Applies a list of 64 hex color strings to the main GUI pad grid.
        Optionally updates the hardware pads as well.
        'is_sampler_output' flag is used by AkaiFireController to potentially bypass global brightness.
        """
        if not hasattr(self, 'pad_grid_frame') or not self.pad_grid_frame:
            # print("MW WARNING: apply_colors_to_main_pad_grid - pad_grid_frame is None.") # Optional
            return
        if not colors_hex or not isinstance(colors_hex, list) or len(colors_hex) != 64:
            # print(f"MW DEBUG: apply_colors_to_main_pad_grid called with invalid colors_hex, clearing grid. update_hw={update_hw}, is_sampler_output={is_sampler_output}") # Optional
            self.clear_main_pad_grid_ui(update_hw=update_hw, is_sampler_output=is_sampler_output)
            return           
        hw_batch = []
        for i, hex_str in enumerate(colors_hex):
            r, c = divmod(i, 16) # Convert 1D index to 2D row/col          
            # Ensure hex_str is valid, default to black if not
            current_color = QColor(hex_str if (hex_str and isinstance(hex_str, str)) else "#000000")
            if not current_color.isValid():
                current_color = QColor("black") # Fallback to black for invalid hex           
            # Update GUI pad color
            self.pad_grid_frame.update_pad_gui_color(r, c, current_color.red(), current_color.green(), current_color.blue())            
            # Prepare batch for hardware update
            if update_hw:
                hw_batch.append((r, c, current_color.red(), current_color.green(), current_color.blue()))       
        # Update hardware pads if requested and controller is connected
        if update_hw and self.akai_controller and self.akai_controller.is_connected() and hw_batch:
            # The 'is_sampler_output' flag tells the controller whether to apply global brightness
            # (bypass_global_brightness = is_sampler_output)
            self.akai_controller.set_multiple_pads_color(hw_batch, bypass_global_brightness=is_sampler_output)
            # print(f"MW DEBUG: Sent {len(hw_batch)} pad colors to hardware. is_sampler_output={is_sampler_output}") # Optional

    # Ensure clear_main_pad_grid_ui is also present and correctly passes the flag
    def clear_main_pad_grid_ui(self, update_hw=True, is_sampler_output: bool = False):
        if not hasattr(self, 'pad_grid_frame') or not self.pad_grid_frame:
             # print("MW WARNING: clear_main_pad_grid_ui - pad_grid_frame is None.") # Optional
             return
        self.apply_colors_to_main_pad_grid(
            [QColor("black").name()] * 64, 
            update_hw=update_hw,
            is_sampler_output=is_sampler_output # Propagate flag
        )

    def _handle_grid_pad_single_left_click(self, row: int, col: int): # Primarily for eyedropper
        if self.is_eyedropper_mode_active: self._pick_color_from_pad(row, col)

    def apply_paint_to_pad(self, row: int, col: int, update_model: bool = True):
        if not self.akai_controller.is_connected(): return
        r, g, b, _ = self.selected_qcolor.getRgb()
        self.akai_controller.set_pad_color(row, col, r, g, b)
        if self.pad_grid_frame: self.pad_grid_frame.update_pad_gui_color(row, col, r, g, b)
        if update_model and self.animator_manager and self.animator_manager.active_sequence_model:
            self.animator_manager.active_sequence_model.update_pad_in_current_edit_frame(
                row * 16 + col, self.selected_qcolor.name()
            )

    def apply_erase_to_pad(self, row: int, col: int, update_model: bool = True):
        if not self.akai_controller.is_connected(): return
        self.akai_controller.set_pad_color(row, col, 0, 0, 0)
        if self.pad_grid_frame: self.pad_grid_frame.update_pad_gui_color(row, col, 0, 0, 0)
        if update_model and self.animator_manager and self.animator_manager.active_sequence_model: 
            self.animator_manager.active_sequence_model.update_pad_in_current_edit_frame(
                row * 16 + col, QColor("black").name()
            )

    def show_pad_context_menu(self, pad_button_widget: QPushButton, row: int, col: int, local_pos_to_button: QPoint):
        menu = QMenu(self)
        action_set_off = QAction("Set Pad to Black (Off)", self)
        action_set_off.triggered.connect(lambda: self.set_single_pad_black_and_update_model(row, col))
        menu.addAction(action_set_off)
        # ... (add other context menu actions for pads later if needed) ...
        menu.exec(pad_button_widget.mapToGlobal(local_pos_to_button))

    def set_single_pad_black_and_update_model(self, row: int, col: int):
        if self.screen_sampler_manager and self.screen_sampler_manager.is_sampling_active():
             self.screen_sampler_manager.stop_sampling_thread()
        self.apply_erase_to_pad(row, col, update_model=True)
        self.status_bar.showMessage(f"Pad ({row+1},{col+1}) set to Off.", 1500)

    def _on_animator_frame_data_for_display(self, colors_hex_list: list | None):
        if colors_hex_list and isinstance(colors_hex_list, list) and len(colors_hex_list) == 64:
            self.apply_colors_to_main_pad_grid(colors_hex_list, update_hw=True)
        else: 
            self.clear_main_pad_grid_ui(update_hw=True)

    def _on_animator_clipboard_state_changed(self, has_content: bool):
        if self.paste_action: self.paste_action.setEnabled(has_content)
        self._update_global_ui_interaction_states()

# --- Handler for GUI Brightness Knob Change ---
    def _on_sampler_brightness_knob_changed(self, gui_knob_value: int):
        if self.screen_sampler_manager:
            sampler_factor = gui_knob_value / 100.0
            sampler_factor = max(0.0, sampler_factor)
            self.screen_sampler_manager.update_sampler_adjustment('brightness', sampler_factor)
            tooltip_text = f"Sampler: Brightness ({sampler_factor:.2f}x)"
            if self.gui_knob1:
                self.gui_knob1.setToolTip(tooltip_text)
            # --- ADD OLED FEEDBACK ---
            oled_feedback_text = f"Br: {sampler_factor:.2f}x"
            self._show_knob_feedback_on_oled(oled_feedback_text)

    def _on_sampler_saturation_knob_changed(self, gui_knob_value: int):
        if self.screen_sampler_manager:
            sampler_factor = gui_knob_value / 100.0
            sampler_factor = max(0.0, sampler_factor)
            self.screen_sampler_manager.update_sampler_adjustment('saturation', sampler_factor)
            tooltip_text = f"Sampler: Saturation ({sampler_factor:.2f}x)"
            if self.gui_knob2:
                self.gui_knob2.setToolTip(tooltip_text)

            # --- ADD OLED FEEDBACK ---
            oled_feedback_text = f"Sat: {sampler_factor:.2f}x"  # Or "S: ..."
            self._show_knob_feedback_on_oled(oled_feedback_text)
            # --- END ADD ---

    def _on_sampler_contrast_knob_changed(self, gui_knob_value: int):
        if self.screen_sampler_manager:
            sampler_factor = gui_knob_value / 100.0
            sampler_factor = max(0.0, sampler_factor)
            self.screen_sampler_manager.update_sampler_adjustment('contrast', sampler_factor)
            tooltip_text = f"Sampler: Contrast ({sampler_factor:.2f}x)"
            if self.gui_knob3:
                self.gui_knob3.setToolTip(tooltip_text)
            # --- ADD OLED FEEDBACK ---
            oled_feedback_text = f"Con: {sampler_factor:.2f}x"  # Or "C: ..."
            self._show_knob_feedback_on_oled(oled_feedback_text)

    def _on_sampler_hue_knob_changed(self, gui_knob_value: int):  # gui_knob_value is -180 to 180 (int)
        if self.screen_sampler_manager:
            self.screen_sampler_manager.update_sampler_adjustment('hue_shift', float(gui_knob_value))
            tooltip_text = f"Sampler: Hue Shift ({gui_knob_value:+d}°)"  # Keep degree for tooltip
            if self.gui_knob4:
                self.gui_knob4.setToolTip(tooltip_text)
            # --- ADD OLED FEEDBACK ---
            oled_feedback_text = f"Hue: {gui_knob_value:+d}"  # No degree symbol for OLED
            self._show_knob_feedback_on_oled(oled_feedback_text)
    
    # --- Global UI State Management ---
    def _update_global_ui_interaction_states(self):
        is_connected = self.akai_controller.is_connected() if self.akai_controller else False # Defensive        
        is_anim_playing = False
        if self.animator_manager and self.animator_manager.active_sequence_model:
            is_anim_playing = self.animator_manager.active_sequence_model.get_is_playing()       
        is_sampler_on = False
        if self.screen_sampler_manager:
            is_sampler_on = self.screen_sampler_manager.is_sampling_active()        
        can_use_animator = is_connected and not is_sampler_on
        can_paint_direct = is_connected and not is_sampler_on and not is_anim_playing # Can't paint if animator is playing
        can_toggle_sampler = is_connected and not is_anim_playing

        # Animator Manager and related QActions
        if self.animator_manager: 
            self.animator_manager.set_overall_enabled_state(can_use_animator)
            has_frames = False
            has_sel = False
            can_undo_anim = False # Renamed to avoid conflict if self.undo_action is None
            can_redo_anim = False # Renamed
            if self.animator_manager.active_sequence_model:
                has_frames = self.animator_manager.active_sequence_model.get_frame_count() > 0
                can_undo_anim = bool(self.animator_manager.active_sequence_model._undo_stack)
                can_redo_anim = bool(self.animator_manager.active_sequence_model._redo_stack)
            if self.animator_manager.sequence_timeline_widget: # Check if timeline widget exists
                 has_sel = len(self.animator_manager.sequence_timeline_widget.get_selected_item_indices()) > 0
            has_clip = bool(self.animator_manager.frame_clipboard)
            if hasattr(self, 'new_sequence_action') and self.new_sequence_action: self.new_sequence_action.setEnabled(can_use_animator)
            if hasattr(self, 'save_sequence_as_action') and self.save_sequence_as_action: self.save_sequence_as_action.setEnabled(can_use_animator and has_frames)
            if hasattr(self, 'undo_action') and self.undo_action: self.undo_action.setEnabled(can_use_animator and can_undo_anim)
            if hasattr(self, 'redo_action') and self.redo_action: self.redo_action.setEnabled(can_use_animator and can_redo_anim)
            if hasattr(self, 'copy_action') and self.copy_action: self.copy_action.setEnabled(can_use_animator and has_sel)
            if hasattr(self, 'cut_action') and self.cut_action: self.cut_action.setEnabled(can_use_animator and has_sel)
            if hasattr(self, 'paste_action') and self.paste_action: self.paste_action.setEnabled(can_use_animator and has_clip)
            if hasattr(self, 'duplicate_action') and self.duplicate_action: self.duplicate_action.setEnabled(can_use_animator and has_sel)
            if hasattr(self, 'delete_action') and self.delete_action: self.delete_action.setEnabled(can_use_animator and has_sel)
            if hasattr(self, 'play_pause_action') and self.play_pause_action: self.play_pause_action.setEnabled(can_use_animator and has_frames)
            if hasattr(self, 'add_blank_global_action') and self.add_blank_global_action: self.add_blank_global_action.setEnabled(can_use_animator)

        # Screen Sampler Manager
        if self.screen_sampler_manager:
            self.screen_sampler_manager.update_ui_for_global_state(is_connected, can_toggle_sampler)
        if hasattr(self, 'pad_grid_frame') and self.pad_grid_frame: 
            self.pad_grid_frame.setEnabled(can_paint_direct)
        else:
            # print("MW TRACE _update_global_ui_interaction_states: pad_grid_frame not available (EXPECTED FOR STEP 2.5).") # Optional
            pass
        if hasattr(self, 'color_picker_manager') and self.color_picker_manager: # Already defensive
            self.color_picker_manager.set_enabled(can_paint_direct)            
        if hasattr(self, 'quick_tools_group_ref') and self.quick_tools_group_ref: 
            self.quick_tools_group_ref.setEnabled(can_paint_direct)
        else:
            # print("MW TRACE _update_global_ui_interaction_states: quick_tools_group_ref not available.") # Optional
            pass            
        if hasattr(self, 'eyedropper_button') and self.eyedropper_button: 
            self.eyedropper_button.setEnabled(can_paint_direct)
        else:
            # print("MW TRACE _update_global_ui_interaction_states: eyedropper_button not available.") # Optional
            pass
        is_eyedropper_active = hasattr(self, 'is_eyedropper_mode_active') and self.is_eyedropper_mode_active
        if hasattr(self, 'eyedropper_action') and self.eyedropper_action: 
            # Original logic: self.eyedropper_action.setEnabled(can_paint_direct and not self.is_eyedropper_mode_active)
            # Simpler for now if is_eyedropper_mode_active might not be set:
            self.eyedropper_action.setEnabled(can_paint_direct and not is_eyedropper_active) 
        else:
            # print("MW TRACE _update_global_ui_interaction_states: eyedropper_action not available.") # Optional
            pass            
        if hasattr(self, 'static_layouts_manager') and self.static_layouts_manager: # Already defensive
            self.static_layouts_manager.set_enabled_state(can_paint_direct)

    # --- NEW Methods for OLED Navigation and Hardware Control ---
    def _update_current_oled_nav_target_widget(self):
        if self.current_oled_nav_target_name == "animator":
            self.current_oled_nav_target_widget = self.animator_manager
        elif self.current_oled_nav_target_name == "static_layouts":
            self.current_oled_nav_target_widget = self.static_layouts_manager
        else:
            self.current_oled_nav_target_widget = None         
        self.current_oled_nav_item_logical_index = 0 
        self._oled_nav_item_count = 0 
        if self.current_oled_nav_target_widget and hasattr(self.current_oled_nav_target_widget, 'get_navigation_item_count'):
            self._oled_nav_item_count = self.current_oled_nav_target_widget.get_navigation_item_count()

    def _cycle_oled_nav_target(self, direction: int):
        if self._oled_nav_debounce_timer.isActive(): return
        self._oled_nav_debounce_timer.start()
        current_focus_idx = self.OLED_NAVIGATION_FOCUS_OPTIONS.index(self.current_oled_nav_target_name)
        new_focus_idx = (current_focus_idx + direction) % len(self.OLED_NAVIGATION_FOCUS_OPTIONS)
        self.current_oled_nav_target_name = self.OLED_NAVIGATION_FOCUS_OPTIONS[new_focus_idx]
        self._update_current_oled_nav_target_widget()        
        # --- CHANGE 2.1: Simplified display name for OLED ---
        if self.current_oled_nav_target_name == "animator":
            nav_target_display_name = "Animator" # Or "Sequences"
        elif self.current_oled_nav_target_name == "static_layouts":
            nav_target_display_name = "Static Layouts" # Or "Layouts"
        else:
            nav_target_display_name = "No Target" 
        
        if self.oled_display_manager:
            if hasattr(self.oled_display_manager, 'show_temporary_message'):
                # Display only the target name, no "Focus:" prefix
                self.oled_display_manager.show_temporary_message(
                    text=nav_target_display_name, 
                    duration_ms=1500, 
                    scroll_if_needed=True # Allow scrolling if name is long
                )
            else: 
                 self.oled_display_manager.set_display_text(nav_target_display_name, scroll_if_needed=True)
        self._oled_nav_interaction_active = False

    def _handle_grid_left_pressed(self):
        self._cycle_oled_nav_target(1)

    def _on_request_toggle_screen_sampler(self):
        """Handles hardware button press to toggle screen sampler ON/OFF."""
        if not self.screen_sampler_manager or not self.akai_controller.is_connected():
            self.status_bar.showMessage("Sampler unavailable or controller disconnected.", 2000)
            return
        # print("MW TRACE: _on_request_toggle_screen_sampler calling toggle_sampling_state.") # Optional
        self.screen_sampler_manager.toggle_sampling_state()
        # The sampling_activity_changed signal from ScreenSamplerManager will trigger
        # _on_sampler_activity_changed, which now handles setting/clearing the
        # persistent OLED override. No need for a QTimer here to call _update_sampler_oled_feedback.

    def _on_request_cycle_sampler_monitor(self):
        """Handles hardware button press to cycle to the next sampler monitor."""
        if not self.screen_sampler_manager or not self.akai_controller.is_connected():
            self.status_bar.showMessage("Sampler unavailable or controller disconnected.", 2000)
            return        
        if not self.screen_sampler_manager.is_sampling_active():
            # Optionally, provide feedback that sampler needs to be on first
            if self.oled_display_manager and hasattr(self.oled_display_manager, 'show_temporary_message'):
                self.oled_display_manager.show_temporary_message("Enable Sampler", "to cycle monitors", 1500)
            else:
                 self.status_bar.showMessage("Enable sampler first to cycle monitors.", 2000)
            return
        # print("MW TRACE: _on_request_cycle_sampler_monitor called.") # Optional
        self.screen_sampler_manager.cycle_target_monitor()
        # OLED feedback will be handled by connecting to screen_sampler_manager.sampler_monitor_changed

    def _on_sampler_monitor_cycled_for_oled(self, new_monitor_name: str):
        """Updates OLED when sampler monitor is changed, especially if sampler is active."""
        if self.oled_display_manager and self.screen_sampler_manager and \
           self.screen_sampler_manager.is_sampling_active(): # Only update persistent if sampler is ON
            # print(f"MW TRACE: Updating OLED persistent override for monitor cycle: {new_monitor_name}") # Optional            
            display_name_part = new_monitor_name
            if "Monitor" in display_name_part and "(" in display_name_part: 
                try: display_name_part = display_name_part.split("(")[0].strip() 
                except: pass            
            override_text = f"SAMPLING (Mon: {display_name_part})"
            self.oled_display_manager.set_persistent_override(override_text, scroll_if_needed=True)
        # If sampler is not active, we could show a temporary message, but typically
        # cycling monitors without the sampler on doesn't need prominent OLED feedback.
        # The sampler_status_update signal from ScreenSamplerManager might still update the status bar.
        # else:
            # print(f"MW TRACE: Sampler not active, _on_sampler_monitor_cycled_for_oled not updating persistent OLED text.") # Optional

    def _update_sampler_oled_feedback(self):
        """
        This method was for temporary sampler ON/OFF feedback.
        Its role is now largely handled by _on_sampler_activity_changed setting a
        persistent override message. It can be safely commented out or removed if
        _on_request_toggle_screen_sampler no longer relies on it for direct feedback.
        """
        # print("MW TRACE: _update_sampler_oled_feedback called - content is now handled by persistent override logic.") # Optional
        pass # Content is now managed by the persistent override in _on_sampler_activity_changed

    def _handle_grid_right_pressed(self):
        self._cycle_oled_nav_target(-1)

    def _handle_select_encoder_turned(self, delta: int):
        if not self.current_oled_nav_target_widget or not self.akai_controller.is_connected() or \
           not hasattr(self.current_oled_nav_target_widget, 'set_navigation_current_item_by_logical_index') or \
           not hasattr(self.current_oled_nav_target_widget, 'get_navigation_item_text_at_logical_index'):
            return
        if self._oled_nav_item_count == 0:
             nav_target_display_name = "Sequences" if self.current_oled_nav_target_name == "animator" else "Layouts"
             if self.oled_display_manager:
                 self.oled_display_manager.set_display_text(f"{nav_target_display_name}: (empty)", scroll_if_needed=False)
             return
        self._oled_nav_interaction_active = True        
        new_logical_index = (self.current_oled_nav_item_logical_index + delta)
        if new_logical_index < 0:
            new_logical_index = self._oled_nav_item_count - 1 
        elif new_logical_index >= self._oled_nav_item_count:
            new_logical_index = 0 
        self.current_oled_nav_item_logical_index = new_logical_index            
        selected_item_text_with_prefix = self.current_oled_nav_target_widget.set_navigation_current_item_by_logical_index(
            self.current_oled_nav_item_logical_index
        )
        if selected_item_text_with_prefix and self.oled_display_manager:
            # --- MODIFICATION FOR CLEAN TITLE, NO TRUNCATION ---
            clean_item_text = selected_item_text_with_prefix
            prefixes_to_strip = ["[Prefab] ", "[Sampler] ", "[User] "] 
            for prefix in prefixes_to_strip:
                if clean_item_text.startswith(prefix):
                    clean_item_text = clean_item_text[len(prefix):]
                    break             
            # Display only the cleaned item text, allow it to scroll if long.
            oled_text = clean_item_text 
            self.oled_display_manager.set_display_text(oled_text, scroll_if_needed=True)
        # print(f"MW TRACE: Select encoder turned. New logical index: {self.current_oled_nav_item_logical_index}, OLED Text: {oled_text}") # Optional

    def _handle_select_encoder_pressed(self):
        # print("MW TRACE: Select encoder pressed.") # Optional
        if self.akai_controller and self.akai_controller.is_connected():
            self.akai_controller.set_play_led(False)
            self.akai_controller.set_stop_led(False)
        # --- SET NAVIGATION ACTION FLAG ---
        self._is_hardware_nav_action_in_progress = True
        item_text_to_apply_raw = self.current_oled_nav_target_widget.get_navigation_item_text_at_logical_index(
            self.current_oled_nav_item_logical_index
        ) or "Selected Item"       
        item_text_to_apply = item_text_to_apply_raw
        prefixes = ["[Prefab] ", "[Sampler] ", "[User] "] 
        for prefix in prefixes:
            if item_text_to_apply.startswith(prefix):
                item_text_to_apply = item_text_to_apply[len(prefix):]
                break
        action_verb = "Loading" if self.current_oled_nav_target_name == "animator" else "Applying"        
        if self.oled_display_manager:
            confirm_item_name_part = item_text_to_apply[:15] + "..." if len(item_text_to_apply) > 15 else item_text_to_apply
            full_confirmation_message = f"{action_verb}: {confirm_item_name_part}"
            if hasattr(self.oled_display_manager, 'show_temporary_message'):
                self.oled_display_manager.show_temporary_message(
                    text=full_confirmation_message, 
                    duration_ms=1800, 
                    scroll_if_needed=True 
                )
            else: 
                 self.oled_display_manager.set_display_text(full_confirmation_message, scroll_if_needed=True)
        # Explicitly turn off transport LEDs before triggering action
        if self.akai_controller and self.akai_controller.is_connected():
            self.akai_controller.set_play_led(False)
            self.akai_controller.set_stop_led(False)
        # Trigger the action (load/apply)
        self.current_oled_nav_target_widget.trigger_navigation_current_item_action()        
        self._oled_nav_interaction_active = False        
        # Schedule final UI feedback (which will reset flag and then update LEDs)
        QTimer.singleShot(2000, self._finalize_navigation_action_ui_feedback)

    def _finalize_navigation_action_ui_feedback(self):
        # print("MW TRACE: _finalize_navigation_action_ui_feedback called.") # Optional-
        self._is_hardware_nav_action_in_progress = False
        is_playing = False
        if self.animator_manager and self.animator_manager.active_sequence_model:
            is_playing = self.animator_manager.active_sequence_model.get_is_playing()
        self._update_fire_transport_leds(is_playing) 
        self._check_and_set_default_oled_text_if_idle()

    def _check_and_set_default_oled_text_if_idle(self):
        if self._oled_nav_interaction_active: return # Still actively navigating with encoder
        if self.oled_display_manager:
            # If a sequence is active, its name should be shown. Otherwise, default.
            if self.animator_manager and self.animator_manager.active_sequence_model and \
               self.animator_manager.active_sequence_model.name and \
               self.animator_manager.active_sequence_model.name != "New Sequence":
                is_mod = self.animator_manager.active_sequence_model.is_modified
                seq_name = self.animator_manager.active_sequence_model.name
                self._update_oled_and_title_on_sequence_change(is_mod, seq_name) # Let this handle "Untitled"
            else: # No active sequence name, revert to default
                self.oled_display_manager.set_display_text(None) # Triggers default in OLEDManager

    # --- Connection Management & Status Update ---
    def _on_port_combo_changed(self, index: int):
        """Enables connect button if a valid port is selected and not already connected."""
        if not self.connect_button_direct_ref or not self.port_combo_direct_ref: return
        if not self.akai_controller.is_connected(): # Only change if not connected
            current_text = self.port_combo_direct_ref.itemText(index)
            can_connect = bool(current_text and current_text != "No MIDI output ports found")
            self.connect_button_direct_ref.setEnabled(can_connect)
        # else: self.connect_button_direct_ref.setEnabled(True) # If connected, button is "Disconnect"

    def toggle_connection(self):    
        """Toggles MIDI connection state based on current connection status."""
        if self.akai_controller.is_connected() or self.akai_controller.is_input_connected():
            if self.oled_display_manager and self.akai_controller.is_connected():
                self.oled_display_manager.clear_display_content() 
            self.akai_controller.disconnect()
        else:
            out_port = self.port_combo_direct_ref.currentText() if self.port_combo_direct_ref else None
            in_port = self.input_port_combo_direct_ref.currentText() if self.input_port_combo_direct_ref else None
            can_connect_out = bool(out_port and out_port != "No MIDI output ports found")
            can_connect_in = bool(in_port and in_port != "No MIDI input ports found") if self.input_port_combo_direct_ref else False
            if not can_connect_out:
                self.status_bar.showMessage("Please select a valid MIDI output port.", 3000)
                self.update_connection_status(); return
            if self.akai_controller.connect(out_port, in_port if can_connect_in else None):
                self.status_bar.showMessage(f"Successfully connected to {out_port}.", 2500)
                if self.oled_display_manager:
                    if not self._has_played_initial_startup_animation:
                        try:
                            # print("MW INFO: First MIDI Connect. Generating & playing OLED startup animation...") # Optional
                            startup_frames = oled_renderer.generate_fire_startup_animation(
                                width=oled_renderer.OLED_WIDTH, height=oled_renderer.OLED_HEIGHT
                            )
                            if startup_frames:
                                self.oled_display_manager.play_startup_animation(startup_frames, frame_duration_ms=60)
                                self._has_played_initial_startup_animation = True
                            else: self._on_oled_startup_animation_finished() 
                        except Exception as e_anim:
                            print(f"MW ERROR: Could not generate/start OLED startup animation: {e_anim}"); import traceback; traceback.print_exc()
                            self._on_oled_startup_animation_finished() 
                    else: 
                        # print("MW INFO: MIDI (Re)Connected. Startup animation played. Setting text.") # Optional
                        if self.animator_manager and self.animator_manager.active_sequence_model and \
                           self.animator_manager.active_sequence_model.name != "New Sequence":
                            self._update_oled_and_title_on_sequence_change(
                                self.animator_manager.active_sequence_model.is_modified,
                                self.animator_manager.active_sequence_model.name
                            )
                        else: self._on_oled_startup_animation_finished() 
            else:
                QMessageBox.warning(self, "Connection Failed", f"Could not connect MIDI output to {out_port}.")
        self.update_connection_status()

    def update_connection_status(self):
        """Updates UI elements based on MIDI connection state."""
        is_out_conn = self.akai_controller.is_connected()
        is_in_conn = self.akai_controller.is_input_connected()
        is_any_conn = is_out_conn or is_in_conn
        if self.connect_button_direct_ref:
            self.connect_button_direct_ref.setText("Disconnect" if is_any_conn else "Connect")
            can_attempt_connect = False
            if self.port_combo_direct_ref and not is_out_conn : # Only enable connect if output not connected
                current_out_text = self.port_combo_direct_ref.currentText()
                if current_out_text and current_out_text != "No MIDI output ports found":
                    can_attempt_connect = True
            self.connect_button_direct_ref.setEnabled(is_any_conn or can_attempt_connect)
        status_parts = []
        if is_out_conn: status_parts.append(f"Output: {self.akai_controller.port_name_used}")
        if is_in_conn: status_parts.append(f"Input: {self.akai_controller.in_port_name_used}")
        self.status_bar.showMessage("Connected. " + " | ".join(status_parts) if status_parts else "Disconnected.")        
        if self.port_combo_direct_ref: self.port_combo_direct_ref.setEnabled(not is_out_conn)
        if self.input_port_combo_direct_ref: self.input_port_combo_direct_ref.setEnabled(not is_in_conn)        
        if self.screen_sampler_manager: # Enable/disable sampler UI based on connection
             self.screen_sampler_manager.set_overall_enabled_state(is_out_conn, is_out_conn) # Base enable, specific button enable also in global states
        QTimer.singleShot(0, self._update_global_ui_interaction_states) # Refresh all UI element states

    # --- Application Exit ---
    def closeEvent(self, event: QMouseEvent): # QMouseEvent is not correct, should be QCloseEvent
                                            # from PyQt6.QtGui import QCloseEvent (at top)
                                            # and change signature to event: QCloseEvent
        # Prompt to save unsaved animator changes
        if self.animator_manager and self.animator_manager.active_sequence_model and \
           self.animator_manager.active_sequence_model.is_modified:
            reply = QMessageBox.question(self, "Unsaved Animator Changes",
                                         f"Animation '{self.animator_manager.active_sequence_model.name}' has unsaved changes. Save before exiting?",
                                         QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel,
                                         QMessageBox.StandardButton.Cancel)
            if reply == QMessageBox.StandardButton.Save:
                save_success = self.animator_manager.action_save_sequence_as()
                if not save_success: event.ignore(); return 
            elif reply == QMessageBox.StandardButton.Cancel: event.ignore(); return        
        if self.screen_sampler_manager: self.screen_sampler_manager.on_application_exit()
        if self.animator_manager: self.animator_manager.stop_current_animation_playback()
        if self.color_picker_manager: self.color_picker_manager.save_color_picker_swatches_to_config()        
        if self.oled_display_manager:
            self.oled_display_manager.stop_all_activity() 
            if self.akai_controller.is_connected():
                 self.oled_display_manager.clear_display_content() 
                 # time.sleep(0.05) # Optional for MIDI message to clear       
        if self.akai_controller.is_connected() or self.akai_controller.is_input_connected():
            self.akai_controller.disconnect()        
        # print("MW INFO: Application close event accepted.") # Optional
        event.accept()

# --- Main Execution Guard (for testing MainWindow directly if needed) ---
if __name__ == '__main__':
    # This block is for testing MainWindow.py independently.
    # fire_control_app.py is the main entry point for the full application.
    app = QApplication(sys.argv)    
    # Attempt to load stylesheet (similar to fire_control_app.py)
    try:
        # Construct path to stylesheet relative to this file's location (gui directory)
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root_dir = os.path.dirname(current_dir) # Up one level to project root
        style_file_path = os.path.join(project_root_dir, "resources", "styles", "style.qss")
        if os.path.exists(style_file_path):
            with open(style_file_path, "r") as f_style:
                app.setStyleSheet(f_style.read())
        else:
            print(f"WARNING (MainWindow test): Stylesheet not found at {style_file_path}")
    except Exception as e_style:
        print(f"ERROR (MainWindow test): Could not load stylesheet: {e_style}")
        
    main_win = MainWindow()
    main_win.show()
    sys.exit(app.exec())