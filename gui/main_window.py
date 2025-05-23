# AKAI_Fire_RGB_Controller/gui/main_window.py
import sys
import json
import os
# import mss # Not directly used in MainWindow, but ScreenSamplerManager uses it
import glob
import re
import time
from appdirs import user_config_dir # For platform-specific user config paths

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, 
    QStatusBar, QGroupBox, QComboBox, QSizePolicy, QMessageBox, QMenu, QSpacerItem # Added QSpacerItem
)
from PyQt6.QtCore import Qt, pyqtSignal, QPoint, QTimer # QTimer is used extensively
from PyQt6.QtGui import QColor, QPalette, QAction, QMouseEvent, QKeySequence, QIcon # QIcon for window icon
# from PIL import Image # Not directly used in MainWindow, but oled_renderer and others might.

# --- Project-specific Imports ---
# Assuming utils.py is at the project root (AKAI_Fire_RGB_Controller/)
from utils import get_resource_path
from oled_utils import oled_renderer # For startup animation generation

# Import manager and hardware classes
from .color_picker_manager import ColorPickerManager
from .static_layouts_manager import StaticLayoutsManager
# from .capture_preview_dialog import CapturePreviewDialog # Not directly instantiated in MW __init__
from .interactive_pad_grid import InteractivePadGridFrame
from .screen_sampler_manager import ScreenSamplerManager
from .animator_manager_widget import AnimatorManagerWidget 
from hardware.akai_fire_controller import AkaiFireController
from managers.oled_display_manager import OLEDDisplayManager
from managers.hardware_input_manager import HardwareInputManager
# Import for QAction icons if they are defined in controls_widget
from animator.controls_widget import ICON_COPY, ICON_CUT, ICON_DUPLICATE, ICON_DELETE, ICON_ADD_BLANK 


# --- Constants ---
INITIAL_WINDOW_WIDTH = 1050
INITIAL_WINDOW_HEIGHT = 900
PRESETS_BASE_DIR_NAME = "presets" 
APP_NAME = "AKAI_Fire_RGB_Controller" # Used for appdirs
APP_AUTHOR = "YourProjectAuthorName"  # Used for appdirs, consider changing
USER_PRESETS_APP_FOLDER_NAME = "Akai Fire RGB Controller User Presets" # For user's Documents folder
DEFAULT_OLED_WELCOME_MESSAGE = "Fire CTRL Ready!" # Editable default OLED welcome message

# --- Helper Functions (Module-Level) ---
def get_user_documents_presets_path(app_specific_folder_name: str = USER_PRESETS_APP_FOLDER_NAME) -> str:
    """Determines the path to the user's Documents subfolder for this application's presets."""
    try:
        documents_path = ""
        if sys.platform == "win32":
            import ctypes.wintypes
            CSIDL_PERSONAL = 5       # My Documents
            SHGFP_TYPE_CURRENT = 0   # Get current path
            buf = ctypes.create_unicode_buffer(ctypes.wintypes.MAX_PATH)
            ctypes.windll.shell32.SHGetFolderPathW(None, CSIDL_PERSONAL, None, SHGFP_TYPE_CURRENT, buf)
            documents_path = buf.value
            if not documents_path: # Fallback if SHGetFolderPathW fails
                 documents_path = os.path.join(os.path.expanduser("~"), "Documents")
        elif sys.platform == "darwin": # macOS
            documents_path = os.path.join(os.path.expanduser("~"), "Documents")
        else: # Linux and other XDG-compliant systems
            documents_path = os.environ.get('XDG_DOCUMENTS_DIR', os.path.join(os.path.expanduser("~"), "Documents"))
            if not os.path.isdir(documents_path): # Fallback if XDG_DOCUMENTS_DIR isn't set or valid
                 documents_path = os.path.join(os.path.expanduser("~"), "Documents")
        
        if not os.path.isdir(documents_path): # Final fallback if "Documents" doesn't exist
            print(f"WARNING: Standard Documents folder not found at '{documents_path}'. Using user home directory as base.")
            documents_path = os.path.expanduser("~")
            
        app_presets_dir = os.path.join(documents_path, app_specific_folder_name)
        os.makedirs(app_presets_dir, exist_ok=True) # Ensure the directory exists
        return app_presets_dir
    except Exception as e:
        print(f"WARNING: Error determining user presets storage path in Documents (using CWD fallback): {e}")
        # Fallback to a directory in the current working directory if all else fails
        fallback_dir = os.path.join(os.getcwd(), "user_presets_fallback_mw")
        os.makedirs(fallback_dir, exist_ok=True)
        return fallback_dir

def get_user_config_file_path(filename: str) -> str:
    """
    Determines the platform-specific user config directory for packaged app,
    or a local 'user_settings' folder for development.
    """
    config_dir_to_use = ""
    try:
        # Check if the application is bundled by PyInstaller
        is_packaged = getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS')
        
        if is_packaged:
            # Packaged app: Use platform-specific user config directory
            config_dir_to_use = user_config_dir(APP_NAME, APP_AUTHOR, roaming=True) # roaming=True for Windows
        else:
            # Development mode: Use a 'user_settings' subfolder in the project root
            try:
                # __file__ is the path to the current script (e.g., .../gui/main_window.py)
                current_file_dir = os.path.dirname(os.path.abspath(__file__))
                # project_root should be one level up from 'gui' directory
                project_root = os.path.dirname(current_file_dir) 
            except NameError: # Fallback if __file__ is not defined (e.g. interactive console)
                project_root = os.getcwd() 
            config_dir_to_use = os.path.join(project_root, "user_settings")
            
        os.makedirs(config_dir_to_use, exist_ok=True) # Ensure the directory exists
        return os.path.join(config_dir_to_use, filename)
    except Exception as e:
        print(f"WARNING: Error determining config path for '{filename}' (using CWD fallback): {e}")
        # Fallback to a directory in the current working directory if all else fails
        fallback_dir = os.path.join(os.getcwd(), "user_settings_fallback_mw")
        os.makedirs(fallback_dir, exist_ok=True)
        return os.path.join(fallback_dir, filename)


class MainWindow(QMainWindow):
    # Class attribute for OLED navigation focus options
    OLED_NAVIGATION_FOCUS_OPTIONS = ["animator", "static_layouts"] # Order matters for cycling

    def __init__(self):
        super().__init__()
        self.setWindowTitle("🎛️ AKAI Fire RGB Controller - Visual Sampler")
        # Consider setting initial size based on screen size or last saved state later
        self.setGeometry(100, 100, INITIAL_WINDOW_WIDTH, INITIAL_WINDOW_HEIGHT)
        self._set_window_icon() # Set window icon early
        
        # --- Initialize Core Controller ---
        self.akai_controller = AkaiFireController(auto_connect=False)

        # --- Initialize State Variables ---
        self.selected_qcolor = QColor("#FF0000") # Default painting color (e.g., red)
        self.is_eyedropper_mode_active: bool = False
        self._has_played_initial_startup_animation = False 
        
        # Navigation state variables
        self.current_oled_nav_target_name: str = self.OLED_NAVIGATION_FOCUS_OPTIONS[0] # Default focus
        self.current_oled_nav_target_widget: QWidget | None = None 
        self.current_oled_nav_item_logical_index: int = 0 
        self._oled_nav_item_count: int = 0 
        self._oled_nav_interaction_active: bool = False 
        self._oled_nav_debounce_timer = QTimer(self) 
        self._oled_nav_debounce_timer.setSingleShot(True)
        self._oled_nav_debounce_timer.setInterval(300) # ms debounce for GRID L/R presses
        self._is_hardware_nav_action_in_progress = False

        # --- Path Initializations ---
        # Path for bundled prefab presets (e.g., inside _MEIPASS or ./presets for dev)
        self.bundled_presets_base_path = self._get_presets_base_dir_path() 
        # Path for user-savable presets (e.g., Documents/AppName User Presets/)
        self.user_documents_presets_path = get_user_documents_presets_path()
        # print(f"DEBUG MW: Bundled presets base: {self.bundled_presets_base_path}") # Optional
        # print(f"DEBUG MW: User documents presets: {self.user_documents_presets_path}") # Optional

        # --- Initialize UI Component References (to be populated by _init_ methods) ---
        self.pad_grid_frame: InteractivePadGridFrame | None = None
        self.animator_manager: AnimatorManagerWidget | None = None            
        self.color_picker_manager: ColorPickerManager | None = None
        self.static_layouts_manager: StaticLayoutsManager | None = None
        self.screen_sampler_manager: ScreenSamplerManager | None = None # Added for completeness
        
        # Direct references for some UI elements if needed across methods
        self.port_combo_direct_ref: QComboBox | None = None
        self.input_port_combo_direct_ref: QComboBox | None = None
        self.connect_button_direct_ref: QPushButton | None = None
        self.quick_tools_group_ref: QGroupBox | None = None # For eyedropper button enabling
        self.eyedropper_button: QPushButton | None = None
        # ... (add other specific UI element references if you need them at self level)

        # QAction references for global shortcuts/menu
        self.undo_action: QAction | None = None; self.redo_action: QAction | None = None
        self.copy_action: QAction | None = None; self.cut_action: QAction | None = None
        self.paste_action: QAction | None = None; self.duplicate_action: QAction | None = None
        self.delete_action: QAction | None = None
        self.new_sequence_action: QAction | None = None; self.save_sequence_as_action: QAction | None = None
        self.play_pause_action: QAction | None = None
        self.eyedropper_action: QAction | None = None
        self.add_blank_global_action: QAction | None = None


        # --- Create User Directories ---
        self.ensure_user_dirs_exist()

        # --- Initialize Main UI Structure & Managers ---
        self._init_ui_layout() # Sets up central widget, main HBoxLayout, status bar
        
        # Managers that populate the right panel
        self._init_managers_right_panel() 
        # Managers/Widgets that populate the left panel (Animator, Sampler)
        self._init_animator_and_sampler_ui_left_panel() 

        # --- Instantiate Core Functional Managers (OLED, Hardware Input) ---
        # These depend on self.akai_controller.
        if self.akai_controller:
            self.oled_display_manager = OLEDDisplayManager(akai_fire_controller_ref=self.akai_controller, parent=self)
            self.hardware_input_manager = HardwareInputManager(akai_fire_controller_ref=self.akai_controller, parent=self)
        else:
            print("CRITICAL MW __init__: AkaiFireController was not initialized prior to OLED/Hardware managers!")
            self.oled_display_manager = None 
            self.hardware_input_manager = None

        # Connect startup animation finished signal (actual animation play is moved to on_connect)
        if self.oled_display_manager:
            self.oled_display_manager.startup_animation_finished.connect(self._on_oled_startup_animation_finished)
            # print("MW INFO __init__: Connected startup_animation_finished signal.") # Optional
        else:
            print("MW WARNING __init__: OLEDManager not available, OLED features will be limited.")

        # Set initial navigation target after all relevant managers (animator, static layouts) are created
        self._update_current_oled_nav_target_widget() # Sets the first navigation target

        # --- Final Setup Steps ---
        self._connect_signals() # Connect signals from all UI components and managers
        self._create_edit_actions() # Create global QActions for menu items & shortcuts
        
        self.populate_midi_ports() # Populate MIDI output port dropdown
        self.populate_midi_input_ports() # Populate MIDI input port dropdown
        
        self.update_connection_status() # Update UI based on initial (disconnected) state
        
        # Defer one tick to ensure all UI elements are constructed before initial state update
        QTimer.singleShot(0, self._update_global_ui_interaction_states) 
        # print("DEBUG MW __init__: Full initialization sequence complete.") # Optional
    # 
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

    def _init_ui_layout(self):
        """Initializes the main window layout structure (panels, status bar)."""
        self.central_widget_main = QWidget()
        self.setCentralWidget(self.central_widget_main)
        self.main_app_layout = QHBoxLayout(self.central_widget_main) # Main Horizontal Layout
        self.main_app_layout.setSpacing(10) # Spacing between left and right panels

        # --- Left Panel (Animator, Sampler, Pad Grid) ---
        self.left_panel_widget = QWidget()
        self.left_panel_layout = QVBoxLayout(self.left_panel_widget)
        self.left_panel_layout.setContentsMargins(5, 5, 5, 5) # Small margins for content within left panel
        self.left_panel_layout.setSpacing(10)      
        
        pad_grid_outer_container = self._create_pad_grid_section() # Pad grid goes at the top of left panel
        self.left_panel_layout.addWidget(pad_grid_outer_container) # Pad grid takes its natural size
        
        # Animator and Sampler UIs will be added to left_panel_layout by _init_animator_and_sampler_ui_left_panel
        
        self.main_app_layout.addWidget(self.left_panel_widget, 2) # Left panel takes 2/3 of horizontal space

        # --- Right Panel (Controls, Config) ---
        self.right_panel_widget = QWidget()
        self.right_panel_layout_v = QVBoxLayout(self.right_panel_widget) # Main vertical layout for right panel
        self.right_panel_widget.setMinimumWidth(380) # Ensure right panel has enough space
        self.right_panel_widget.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
        
        # Managers will add their group boxes to right_panel_layout_v in _init_managers_right_panel
        
        self.main_app_layout.addWidget(self.right_panel_widget, 1) # Right panel takes 1/3 of horizontal space

        # --- Status Bar ---
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready. Please connect to AKAI Fire.")

    def _create_pad_grid_section(self) -> QWidget:
        """Creates the pad grid widget and its immediate container."""
        pad_grid_outer_container = QWidget() # Container to help with alignment/spacing if needed
        pad_grid_container_layout = QVBoxLayout(pad_grid_outer_container)
        pad_grid_container_layout.setContentsMargins(0, 0, 0, 0) # No margins for the direct container
        
        self.pad_grid_frame = InteractivePadGridFrame(parent=self) # Create the actual grid
        # Add the grid, allowing it to align top and center horizontally within its allotted space
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
    
    def _init_managers_right_panel(self):
        """Initializes and adds manager UIs to the right panel layout."""
        # --- MIDI Connection Group (Output) ---
        connection_group = QGroupBox("🔌 MIDI Output (to Fire)")
        connection_layout = QHBoxLayout(connection_group)    
        self.port_combo_direct_ref = QComboBox()
        # print(f"DEBUG MW: _init_managers_right_panel - port_combo_direct_ref ID: {id(self.port_combo_direct_ref)}") # Optional
        self.port_combo_direct_ref.setPlaceholderText("Select MIDI Output")
        # self.port_combo_direct_ref.clear() # Done by populate_midi_ports
        self.port_combo_direct_ref.currentIndexChanged.connect(self._on_port_combo_changed) # Connect state change for button
        
        self.connect_button_direct_ref = QPushButton("Connect")
        self.connect_button_direct_ref.clicked.connect(self.toggle_connection)
        self.connect_button_direct_ref.setEnabled(False) # Enabled when a port is selected

        connection_layout.addWidget(QLabel("Output Port:"))
        connection_layout.addWidget(self.port_combo_direct_ref, 1) # ComboBox takes available space
        connection_layout.addWidget(self.connect_button_direct_ref)
        self.right_panel_layout_v.addWidget(connection_group)

        # --- MIDI Input Group ---
        self.right_panel_layout_v.addWidget(self._create_midi_input_section()) # Add input selection UI

        # --- Color Picker Manager ---
        self.color_picker_manager = ColorPickerManager(
            initial_color=self.selected_qcolor, # Pass initial default color
            parent_group_title="🎨 Advanced Color Picker",
            config_save_path_func=get_user_config_file_path # Pass helper function for path
        )
        self.right_panel_layout_v.addWidget(self.color_picker_manager)

        # --- Quick Tools (Set Black, Clear, Eyedropper) ---
        self.quick_tools_group_ref = self._init_direct_controls_right_panel()
        if self.quick_tools_group_ref: # Should always be true
            self.right_panel_layout_v.addWidget(self.quick_tools_group_ref)

        # --- Static Layouts Manager ---
        self.static_layouts_manager = StaticLayoutsManager(
            user_static_layouts_path=os.path.join(self.user_documents_presets_path, "static", "user"),
            prefab_static_layouts_path=os.path.join(self.bundled_presets_base_path, "static", "prefab"),
            group_box_title="▦ Static Pad Layouts"
            # parent=self # QGroupBox parent is handled by addWidget
        )
        self.right_panel_layout_v.addWidget(self.static_layouts_manager)      
        
        self.right_panel_layout_v.addStretch(1) # Add stretch at the end to push content up

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

    # --- Core Signal Connection Method ---

    # In class MainWindow(QMainWindow):

    def _connect_signals(self):
        """Connects signals from various UI components and managers to their handlers in MainWindow."""
        print("MW TRACE: _connect_signals CALLED.") # Keep for debugging signal issues

        # InteractivePadGridFrame signals
        if self.pad_grid_frame:
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
        else:
            print("MW TRACE WARNING: self.animator_manager is None during _connect_signals.")

        # HardwareInputManager Signals
        if self.hardware_input_manager:
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
        
        # OLEDDisplayManager Signal to AkaiFireController
        if self.oled_display_manager and self.akai_controller:
            try:
                # Try to disconnect first to prevent multiple connections if this method is ever called again
                self.oled_display_manager.request_send_bitmap_to_fire.disconnect(self.akai_controller.oled_send_full_bitmap) 
            except TypeError: # Raised if not connected, which is fine.
                pass 
            except Exception as e_disc_oled: # Catch any other potential errors during disconnect
                 print(f"MW WARNING _connect_signals: Error disconnecting OLED signal (might be harmless): {e_disc_oled}")
            try:
                self.oled_display_manager.request_send_bitmap_to_fire.connect(self.akai_controller.oled_send_full_bitmap)
                # print("MW TRACE _connect_signals: SUCCESSFULLY connected OLEDManager.request_send_bitmap_to_fire to AkaiFireController.oled_send_full_bitmap") # Optional
            except Exception as e_connect_oled:
                print(f"MW ERROR _connect_signals: FAILED to connect OLED signal request_send_bitmap_to_fire: {e_connect_oled}")
        elif not self.oled_display_manager:
            print("MW TRACE WARNING: self.oled_display_manager is None during OLED signal connection attempt.")
        elif not self.akai_controller:
            print("MW TRACE WARNING: self.akai_controller is None during OLED signal connection attempt.")
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


    # --- Slots for Signals from Managers & UI Elements ---

    def _handle_request_sampler_disable(self):
        if self.screen_sampler_manager and self.screen_sampler_manager.is_sampling_active():
            self.screen_sampler_manager.stop_sampling_thread() 
            # self.status_bar.showMessage("Sampler deactivated by other component.", 2000) # Optional

    def _on_oled_startup_animation_finished(self):
        # print("MW INFO: OLED startup animation finished. Setting default OLED text.") # Optional
        if self.oled_display_manager:
            self.oled_display_manager.set_default_scrolling_text_after_startup(DEFAULT_OLED_WELCOME_MESSAGE)
        # else: # Optional
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

    def _on_animator_playback_activity_changed(self, is_animator_playing: bool):
        """Called by AnimatorManagerWidget when its playback state (playing/paused/stopped) changes."""
        self._update_global_ui_interaction_states() # Refresh UI enabled states
        # Note: Fire's Play/Stop LEDs are updated by _update_fire_transport_leds
        # which is directly connected to animator_playback_active_status_changed.

        if is_animator_playing: # If animator starts playing, ensure sampler is off
            if self.screen_sampler_manager and self.screen_sampler_manager.is_sampling_active():
                self.screen_sampler_manager.stop_sampling_thread()
                self.status_bar.showMessage("Screen sampler stopped due to animation playback.", 2000)

    def _update_oled_and_title_on_sequence_change(self, is_modified: bool, sequence_name: str | None):
        # print(f"DEBUG MW: _update_oled_and_title_on_sequence_change - Mod: {is_modified}, Name: '{sequence_name}'") # Optional
        base_title = "🎛️ AKAI Fire RGB Controller - Visual Sampler"
        effective_title_sequence_name = sequence_name if sequence_name and sequence_name.strip() and sequence_name != "New Sequence" else "Untitled"
        
        title = f"{base_title} - {effective_title_sequence_name}"
        if is_modified: title += "*" 
        self.setWindowTitle(title)

        if self.oled_display_manager:
            text_for_oled = None 
            if sequence_name and sequence_name.strip() and sequence_name != "New Sequence":
                text_for_oled = sequence_name
            if text_for_oled and is_modified: text_for_oled += "*"
            self.oled_display_manager.set_display_text(text_for_oled) 
            # print(f"DEBUG MW: Called OLEDManager.set_display_text with: '{text_for_oled}'") # Optional

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
            self.animator_manager.action_play_pause_toggle() # This will change state and eventually call _update_fire_transport_leds
            self.clear_led_suppression_and_update() # Ensure LEDs are now allowed to update and do so


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

    def apply_colors_to_main_pad_grid(self, colors_hex: list | None, update_hw=True):
        if not colors_hex or len(colors_hex) != 64:
            self.clear_main_pad_grid_ui(update_hw=update_hw); return
        hw_batch = []
        for i, hex_str in enumerate(colors_hex):
            r, c = divmod(i, 16)
            color = QColor(hex_str if hex_str else "#000000")
            if not color.isValid(): color = QColor("black")            
            if self.pad_grid_frame: self.pad_grid_frame.update_pad_gui_color(r, c, color.red(), color.green(), color.blue())            
            if update_hw: hw_batch.append((r, c, color.red(), color.green(), color.blue()))        
        if update_hw and self.akai_controller.is_connected() and hw_batch:
            self.akai_controller.set_multiple_pads_color(hw_batch)

    def clear_main_pad_grid_ui(self, update_hw=True):
        self.apply_colors_to_main_pad_grid([QColor("black").name()] * 64, update_hw=update_hw)

    def clear_all_hardware_and_gui_pads(self):
        if not self.akai_controller.is_connected():
            self.status_bar.showMessage("Connect to device first.", 2000); return       
        if self.screen_sampler_manager and self.screen_sampler_manager.is_sampling_active():
             self.screen_sampler_manager.stop_sampling_thread()
        if self.animator_manager: self.animator_manager.action_stop()
        self.clear_main_pad_grid_ui(update_hw=True)
        if self.animator_manager and self.animator_manager.active_sequence_model: 
            self.animator_manager.active_sequence_model.clear_pads_in_current_edit_frame()
        self.status_bar.showMessage("All pads and current view cleared.", 2000)

    def _handle_final_color_selection_from_manager(self, color: QColor):
        if isinstance(color, QColor) and color.isValid():
            self.selected_qcolor = color
            self.status_bar.showMessage(f"Active painting color: {color.name().upper()}", 3000)
        # else: print(f"MW WARNING: Invalid color from ColorPickerManager: {color}") # Optional

    def _handle_apply_static_layout_data(self, colors_hex: list):
        if not self.akai_controller.is_connected():
            self.status_bar.showMessage("Connect to device first.", 2000); return
        if self.screen_sampler_manager and self.screen_sampler_manager.is_sampling_active():
            self.screen_sampler_manager.stop_sampling_thread() 
        if self.animator_manager: self.animator_manager.action_stop()
        # Apply to animator's current frame if model exists, otherwise directly to grid
        if self.animator_manager and self.animator_manager.active_sequence_model:
            self.animator_manager.active_sequence_model.update_all_pads_in_current_edit_frame(colors_hex)
        else: 
            self.apply_colors_to_main_pad_grid(colors_hex, update_hw=True)     
        self.status_bar.showMessage("Static layout applied.", 2000)

    def _provide_grid_colors_for_static_save(self):
        if self.static_layouts_manager and self.pad_grid_frame:
            current_colors_hex = self.pad_grid_frame.get_current_grid_colors_hex()
            self.static_layouts_manager.save_layout_with_colors(current_colors_hex)
        # else: self.status_bar.showMessage("Cannot save layout: UI components missing.", 3000) # Optional
    
    def _handle_paint_black_button(self):
        if self.screen_sampler_manager and self.screen_sampler_manager.is_sampling_active():
            self.screen_sampler_manager.stop_sampling_thread()
        black_color = QColor("black")
        self.selected_qcolor = black_color
        if self.color_picker_manager:
            self.color_picker_manager.set_current_selected_color(black_color, source="paint_black_button")
        self.status_bar.showMessage("Active color: Black (Off)", 2000)
    
    # --- Global UI State Management ---
    def _update_global_ui_interaction_states(self):
        is_connected = self.akai_controller.is_connected()
        is_anim_playing = self.animator_manager.active_sequence_model.get_is_playing() if self.animator_manager and self.animator_manager.active_sequence_model else False
        is_sampler_on = self.screen_sampler_manager.is_sampling_active() if self.screen_sampler_manager else False
        
        can_use_animator = is_connected and not is_sampler_on
        can_paint_direct = is_connected and not is_sampler_on and not is_anim_playing # Can't paint if animator is playing
        can_toggle_sampler = is_connected and not is_anim_playing

        if self.animator_manager: 
            self.animator_manager.set_overall_enabled_state(can_use_animator)
            # Update global QActions based on animator state
            has_frames = self.animator_manager.active_sequence_model.get_frame_count() > 0 if self.animator_manager.active_sequence_model else False
            has_sel = len(self.animator_manager.sequence_timeline_widget.get_selected_item_indices()) > 0 if self.animator_manager.sequence_timeline_widget else False
            can_undo = bool(self.animator_manager.active_sequence_model._undo_stack) if self.animator_manager.active_sequence_model else False
            can_redo = bool(self.animator_manager.active_sequence_model._redo_stack) if self.animator_manager.active_sequence_model else False
            has_clip = bool(self.animator_manager.frame_clipboard)

            if self.new_sequence_action: self.new_sequence_action.setEnabled(can_use_animator)
            if self.save_sequence_as_action: self.save_sequence_as_action.setEnabled(can_use_animator and has_frames)
            if self.undo_action: self.undo_action.setEnabled(can_use_animator and can_undo)
            if self.redo_action: self.redo_action.setEnabled(can_use_animator and can_redo)
            if self.copy_action: self.copy_action.setEnabled(can_use_animator and has_sel)
            if self.cut_action: self.cut_action.setEnabled(can_use_animator and has_sel)
            if self.paste_action: self.paste_action.setEnabled(can_use_animator and has_clip)
            if self.duplicate_action: self.duplicate_action.setEnabled(can_use_animator and has_sel)
            if self.delete_action: self.delete_action.setEnabled(can_use_animator and has_sel)
            if self.play_pause_action: self.play_pause_action.setEnabled(can_use_animator and has_frames)
            if self.add_blank_global_action: self.add_blank_global_action.setEnabled(can_use_animator)

        if self.screen_sampler_manager:
            self.screen_sampler_manager.update_ui_for_global_state(is_connected, can_toggle_sampler)
        
        if self.pad_grid_frame: self.pad_grid_frame.setEnabled(can_paint_direct)
        if self.color_picker_manager: self.color_picker_manager.set_enabled(can_paint_direct)
        if self.quick_tools_group_ref: self.quick_tools_group_ref.setEnabled(can_paint_direct)
        if self.eyedropper_button: self.eyedropper_button.setEnabled(can_paint_direct)
        if self.eyedropper_action: self.eyedropper_action.setEnabled(can_paint_direct and not self.is_eyedropper_mode_active) # Action enables mode
        if self.static_layouts_manager: self.static_layouts_manager.set_enabled_state(can_paint_direct)

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
        
        nav_target_display_name = "Sequences" if self.current_oled_nav_target_name == "animator" else \
                                  "Layouts" if self.current_oled_nav_target_name == "static_layouts" else "None"
        
        if self.oled_display_manager:
            if hasattr(self.oled_display_manager, 'show_temporary_message'):
                self.oled_display_manager.show_temporary_message(f"Focus: {nav_target_display_name}", duration_ms=1500, scroll_if_needed=False)
            else: 
                self.oled_display_manager.set_display_text(f"Focus: {nav_target_display_name}", scroll_if_needed=False)
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
    # --- END NEW Slots ---

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
            # --- END MODIFICATION ---

            self.oled_display_manager.set_display_text(oled_text, scroll_if_needed=True)
        # print(f"MW TRACE: Select encoder turned. New logical index: {self.current_oled_nav_item_logical_index}, OLED Text: {oled_text}") # Optional

    def _handle_select_encoder_pressed(self):
        # print("MW TRACE: Select encoder pressed.") # Optional
        if self.akai_controller and self.akai_controller.is_connected():
            self.akai_controller.set_play_led(False)
            self.akai_controller.set_stop_led(False)

        # --- SET NAVIGATION ACTION FLAG ---
        self._is_hardware_nav_action_in_progress = True
        # --- END FLAG ---

        item_text_to_apply_raw = self.current_oled_nav_target_widget.get_navigation_item_text_at_logical_index(
            self.current_oled_nav_item_logical_index
        ) or "Selected Item"
        
        item_text_to_apply = item_text_to_apply_raw
        prefixes_to_strip = ["[Prefab] ", "[Sampler] ", "[User] "] 
        for prefix in prefixes_to_strip:
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
        # print("MW TRACE: _finalize_navigation_action_ui_feedback called.") # Optional

        # --- RESET NAVIGATION ACTION FLAG ---
        self._is_hardware_nav_action_in_progress = False
        # --- END FLAG RESET ---

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
        # ... (This method was updated in the previous step to include startup animation logic) ...
        # ... (Ensure it's the version from Step 1B of "Okay, this is a great plan!")
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



