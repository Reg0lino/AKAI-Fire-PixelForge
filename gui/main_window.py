# AKAI_Fire_RGB_Controller/gui/main_window.py
import sys
import json
import os
import mss
import glob
import re
import time
from appdirs import user_config_dir
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QStatusBar, QGridLayout, QFrame,
    QGroupBox, QMenu, QSizePolicy,
    QMessageBox, QComboBox, QSpacerItem, QListWidget, QInputDialog
)
from PyQt6.QtCore import Qt, pyqtSignal, QPoint, QTimer
from PyQt6.QtGui import QColor, QPalette, QAction, QMouseEvent, QKeySequence, QIcon
from PIL import Image
# --- Project-Specific Imports ---
from .color_picker_manager import ColorPickerManager
from .static_layouts_manager import StaticLayoutsManager
from .capture_preview_dialog import CapturePreviewDialog
from .interactive_pad_grid import InteractivePadGridFrame
from .screen_sampler_manager import ScreenSamplerManager
from .animator_manager_widget import AnimatorManagerWidget 
from hardware.akai_fire_controller import AkaiFireController
from utils import get_resource_path # <<< ADD THIS IMPORT
# --- Constants ---
INITIAL_WINDOW_WIDTH = 1050
INITIAL_WINDOW_HEIGHT = 900
PRESETS_BASE_DIR_NAME = "presets"
APP_NAME = "AKAI_Fire_RGB_Controller"
APP_AUTHOR = "YourProjectAuthorName"
SAMPLER_PREFS_FILENAME = "sampler_user_prefs.json"
MAIN_CONFIG_FILENAME = "fire_controller_config.json"
DEFAULT_SAMPLING_FPS = 10
# --- Global Functions ---
def get_resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        # Not bundled, running from source
        # Assume this function is in a file within 'gui' or similar, 
        # and 'resources' is at the project root.
        # Adjust if your get_resource_path is elsewhere.
        base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..")) # Goes up one level from current file's dir

    return os.path.join(base_path, relative_path)
# user config_dir
def get_user_config_file_path(filename: str) -> str:
    """
    Determines the appropriate path for a user config file.
    Prioritizes AppData if packaged, falls back to a local 'user_settings' directory.
    """
    config_dir_to_use = ""
    try:
        is_packaged = getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS')
        if is_packaged:
            config_dir_to_use = user_config_dir(APP_NAME, APP_AUTHOR)
        else:
            try:
                current_file_dir = os.path.dirname(os.path.abspath(__file__))
                project_root = os.path.dirname(current_file_dir)
            except NameError:
                project_root = os.getcwd()
            config_dir_to_use = os.path.join(project_root, "user_settings")
        os.makedirs(config_dir_to_use, exist_ok=True)
        return os.path.join(config_dir_to_use, filename)
    except Exception as e:
        print(f"WARNING: Error determining config path (will use CWD): {e}")
        fallback_dir = os.path.join(os.getcwd(), "user_settings_fallback")
        os.makedirs(fallback_dir, exist_ok=True)
        print(f"WARNING: Using CWD fallback config directory: {fallback_dir}")
        return os.path.join(fallback_dir, filename)
# --- MainWindow Class ---
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("🎛️ AKAI Fire RGB Controller - Visual Sampler")
        self.setGeometry(100, 100, INITIAL_WINDOW_WIDTH, INITIAL_WINDOW_HEIGHT)
        self._set_window_icon()
        self.quick_tools_group_ref: QGroupBox | None = None # For Quick Tools group on right panel
        self.akai_controller = AkaiFireController(auto_connect=False)
        self.selected_qcolor = QColor("red") # Current color for direct painting
        # Attributes related to direct pad interaction (eyedropper)
        self.is_eyedropper_mode_active: bool = False
        self.eyedropper_button: QPushButton | None = None # UI button in Quick Tools
        self.eyedropper_action: QAction | None = None   # Global QAction for eyedropper
        # Sampler related attributes
        self.presets_base_dir_path = self._get_presets_base_dir_path() # For sampler recordings too
        # UI Manager/Widget instances (some will be complex managers)
        self.pad_grid_frame: InteractivePadGridFrame = None # Now uses the new interactive grid
        self.animator_manager: AnimatorManagerWidget = None # <<< NEW Animator Manager instance              
        self.color_picker_manager: ColorPickerManager = None
        self.static_layouts_manager: StaticLayoutsManager = None
        # Direct references to some UI elements on the right panel (MIDI, Quick Tools)
        self.port_combo_direct_ref: QComboBox = None
        self.connect_button_direct_ref: QPushButton = None
        self.clear_all_button: QPushButton | None = None # From Quick Tools
        self.color_button_off: QPushButton | None = None # From Quick Tools                
        # QActions (Animator-specific ones will now trigger methods on animator_manager)
        self.undo_action: QAction = None; self.redo_action: QAction = None
        self.copy_action: QAction = None; self.cut_action: QAction = None
        self.paste_action: QAction = None; self.duplicate_action: QAction = None
        self.delete_action: QAction = None
        self.new_sequence_action: QAction = None; self.save_sequence_as_action: QAction = None
        self.play_pause_action: QAction = None # Global spacebar play/pause for animator
        self.ensure_user_dirs_exist()
        # --- UI Initialization Steps ---
        self._init_ui_layout()  # Creates main layout structure, calls _create_pad_grid_section
        # print(f"DEBUG MW __init__: BEFORE _init_managers_right_panel, port_combo is {getattr(self, 'port_combo_direct_ref', 'NOT YET DEFINED')}")
        self._init_managers_right_panel() # self.port_combo_direct_ref IS CREATED HERE
        # print(f"DEBUG MW __init__: AFTER _init_managers_right_panel, port_combo is {self.port_combo_direct_ref}, bool is {bool(self.port_combo_direct_ref)}")

        # print(f"DEBUG MW __init__: BEFORE _init_animator_and_sampler_ui_left_panel, port_combo is {self.port_combo_direct_ref}")
        self._init_animator_and_sampler_ui_left_panel()
        # print(f"DEBUG MW __init__: AFTER _init_animator_and_sampler_ui_left_panel, port_combo is {self.port_combo_direct_ref}")
        self._connect_signals()
        # print(f"DEBUG MW __init__: AFTER _connect_signals, port_combo is {self.port_combo_direct_ref}")
        self._create_edit_actions() # Creates QActions, connects them to delegating methods or animator_manager
        # print(f"DEBUG MW __init__: AFTER _create_edit_actions, port_combo is {self.port_combo_direct_ref}") 
        self.populate_midi_ports()
        self.update_connection_status() # This will call _update_animator_controls_enabled_state
        QTimer.singleShot(0, self._update_animator_controls_enabled_state) # Ensure initial state after all setup
        ### END OF MainWindow.__init__ ###
        # --- MIDI Connection Management ---    
    def populate_midi_ports(self):
        # print(f"DEBUG populate_midi_ports: ENTERING. self.port_combo_direct_ref is: {self.port_combo_direct_ref}")
        if self.port_combo_direct_ref is None:
            print("CRITICAL ERROR: populate_midi_ports: self.port_combo_direct_ref IS PYTHON NONE! Cannot proceed.")
            return   
        self.port_combo_direct_ref.blockSignals(True)
        self.port_combo_direct_ref.clear()     
        ports = AkaiFireController.get_available_ports()
        # print(f"DEBUG MW populate_midi_ports: AkaiFireController.get_available_ports() returned: {ports}")    
        if ports and isinstance(ports, list) and len(ports) > 0: # Ensure ports is a non-empty list
            # print(f"DEBUG MW populate_midi_ports: Adding items: {ports}")
            self.port_combo_direct_ref.addItems(ports)
            self.port_combo_direct_ref.setEnabled(True)        
            # Try to select a "Fire" or "Akai" port by default
            fire_port_idx = -1
            for i, port_name in enumerate(ports):
                if isinstance(port_name, str) and \
                   ("fire" in port_name.lower() or "akai" in port_name.lower()) and \
                   "midiin" not in port_name.lower():
                    fire_port_idx = i
                    break                    
            if fire_port_idx != -1:
                self.port_combo_direct_ref.setCurrentIndex(fire_port_idx)
                # print(f"DEBUG MW populate_midi_ports: Defaulted to Fire/Akai port: {ports[fire_port_idx]} at index {fire_port_idx}")
            elif self.port_combo_direct_ref.count() > 0: # If no Fire/Akai, select the first available
                self.port_combo_direct_ref.setCurrentIndex(0)
                # print(f"DEBUG MW populate_midi_ports: Defaulted to first available port: {self.port_combo_direct_ref.itemText(0)} at index 0")
            else:
                # This case should ideally not be reached if ports list was valid and addItems worked
                print("WARN MW populate_midi_ports: No items in combo after addItems, adding placeholder.")
                self.port_combo_direct_ref.addItem("No MIDI ports found")
                self.port_combo_direct_ref.setEnabled(False)
        else: # No ports found or ports is not a valid list
            # print("DEBUG MW populate_midi_ports: No valid MIDI ports found by controller, adding placeholder.")
            self.port_combo_direct_ref.addItem("No MIDI output ports found") # Consistent placeholder
            self.port_combo_direct_ref.setEnabled(False)
        self.port_combo_direct_ref.blockSignals(False)
        # Trigger update of connect button state based on current combo selection
        current_idx = self.port_combo_direct_ref.currentIndex()
        # print(f"DEBUG MW populate_midi_ports: Calling _on_port_combo_changed with index: {current_idx}")
        if hasattr(self, '_on_port_combo_changed'): # Ensure method exists
            self._on_port_combo_changed(current_idx)
        else:
            print("ERROR MW populate_midi_ports: _on_port_combo_changed method not found!")    

    # --- New Slot Methods for AnimatorManagerWidget Signals ---
    def _on_animator_frame_data_for_display(self, colors_hex_list: list | None):
        """Receives color data from AnimatorManager and updates grid/hardware."""
        if colors_hex_list:
            self.apply_colors_to_main_pad_grid(colors_hex_list, update_hw=True)
        else: # No data or empty/invalid frame selected
            self.clear_main_pad_grid_ui(update_hw=True)
    # --- Animator Manager Methods ---
    def _on_animator_sequence_modified_status_changed(self, is_modified: bool, sequence_name: str):
        """Updates the window title based on sequence modification status from AnimatorManager."""
        base_title = "🎛️ AKAI Fire RGB Controller - Visual Sampler"
        # Use a simple name if sequence_name is default or empty
        effective_sequence_name = sequence_name if sequence_name and sequence_name != "New Sequence" else "Untitled"
        title = f"{base_title} - {effective_sequence_name}"
        if is_modified:
            title += "*"
        self.setWindowTitle(title)
    # --- Animator Manager Methods ---
    def _on_animator_undo_redo_state_changed(self, can_undo: bool, can_redo: bool):
        """Updates the enabled state of global Undo/Redo QActions."""
        if self.undo_action: self.undo_action.setEnabled(can_undo)
        if self.redo_action: self.redo_action.setEnabled(can_redo)
        # This also implicitly calls for an update of general controls state
        self._update_animator_controls_enabled_state()
    # --- Animator Manager Methods ---
    def _on_animator_clipboard_state_changed(self, has_content: bool):
        """Updates the enabled state of the global Paste QAction."""
        if self.paste_action: self.paste_action.setEnabled(has_content)
        self._update_animator_controls_enabled_state()
    # disable sampler
    def _handle_request_sampler_disable(self):
        """Called when animator manager wants to ensure sampler is off."""
        if self.is_eyedropper_mode_active and self.screen_sampler_manager:
            self.screen_sampler_manager.force_disable_sampling_ui()
    # --- Delegating Methods for QActions to call AnimatorManagerWidget ---
    def action_animator_undo(self):
        if self.animator_manager: self.animator_manager.action_undo()
    # --- Animator Manager Methods ---
    def action_animator_redo(self):
        if self.animator_manager: self.animator_manager.action_redo()
    # --- Animator Manager Methods ---
    def action_animator_copy_frames(self):
        if self.animator_manager: self.animator_manager.action_copy_frames()
    # --- Animator Manager Methods ---
    def action_animator_cut_frames(self):
        if self.animator_manager: self.animator_manager.action_cut_frames()
    # --- Animator Manager Methods ---
    def action_animator_paste_frames(self):
        if self.animator_manager: self.animator_manager.action_paste_frames()
    # --- Animator Manager Methods ---
    def action_animator_duplicate_frames(self):
        if self.animator_manager: self.animator_manager.action_duplicate_selected_frames()
    # --- Animator Manager Methods ---
    def action_animator_delete_frames(self):
        if self.animator_manager: self.animator_manager.action_delete_selected_frames()
    # --- Animator Manager Methods ---
    def action_animator_new_sequence(self, prompt_save=True):
        if self.animator_manager:
            if prompt_save and self.animator_manager.active_sequence_model.is_modified: # Query AMW's model
                reply = QMessageBox.question(self, "Unsaved Changes",
                                             f"Animation '{self.animator_manager.active_sequence_model.name}' has unsaved changes. Save now?",
                                             QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel,
                                             QMessageBox.StandardButton.Cancel)
                if reply == QMessageBox.StandardButton.Save:
                    # Tell AMW to save, it will handle the dialog for now
                    save_successful = self.animator_manager.action_save_sequence_as() # AMW's save returns bool
                    if not save_successful or self.animator_manager.active_sequence_model.is_modified:
                        # Save was cancelled or failed, and model is still modified
                        self.status_bar.showMessage("New sequence cancelled due to unsaved changes.", 3000)
                        return
                elif reply == QMessageBox.StandardButton.Cancel:
                    self.status_bar.showMessage("New sequence cancelled.", 2000)
                    return           
            self.animator_manager.action_new_sequence(prompt_save=False) # AMW won't prompt again
    # --- Animator Manager Methods ---
    def action_animator_save_sequence_as(self):
        if self.animator_manager:
            # AMW's action_save_sequence_as currently shows QInputDialog.
            # Ideally, MainWindow shows QFileDialog and passes path to AMW.
            self.animator_manager.action_save_sequence_as()
    # --- Animator Manager Methods ---
    def action_animator_play_pause_toggle(self):
        if self.animator_manager: self.animator_manager.action_play_pause_toggle()
    # --- Animator Manager Methods ---
    def action_animator_add_snapshot_frame(self):
        if self.animator_manager and self.pad_grid_frame:
            current_grid_colors = self.pad_grid_frame.get_current_grid_colors_hex()
            self.animator_manager.action_add_frame("snapshot", snapshot_data=current_grid_colors)
    # --- Animator Manager Methods ---
    def action_animator_add_blank_frame(self):
        if self.animator_manager:
            self.animator_manager.action_add_frame("blank")
    # --- Pad Interaction Methods ---
    def _handle_grid_pad_action(self, row: int, col: int, mouse_button: Qt.MouseButton):
        """Handles paint/erase actions requested by the InteractivePadGridFrame."""
        if mouse_button == Qt.MouseButton.LeftButton and self.is_eyedropper_mode_active:
            self._pick_color_from_pad(row, col) # Assumes _pick_color_from_pad exists
            return
        if mouse_button == Qt.MouseButton.LeftButton:
            if self.is_eyedropper_mode_active and self.screen_sampler_manager:
                self.screen_sampler_manager.force_disable_sampling_ui()
            self.apply_paint_to_pad(row, col, update_model=True)
        elif mouse_button == Qt.MouseButton.RightButton:
            if self.is_eyedropper_mode_active and self.screen_sampler_manager:
                self.screen_sampler_manager.force_disable_sampling_ui()
            self.apply_erase_to_pad(row, col, update_model=True)
    # --- Pad Interaction Methods ---
    def _handle_grid_pad_single_left_click(self, row: int, col: int):
        """Handles specific single left-click actions from PadButton, primarily for eyedropper."""
        if self.is_eyedropper_mode_active:
            self._pick_color_from_pad(row, col) # Assumes _pick_color_from_pad exists
    # ick color from pad
    def _pick_color_from_pad(self, row: int, col: int):
        """Picks the color from the specified pad and sets it in the color picker."""
        if not self.color_picker_manager:
            return
        all_grid_colors = self.get_current_main_pad_grid_colors()
        pad_1d_index = row * 16 + col # Assuming 16 columns
        if 0 <= pad_1d_index < len(all_grid_colors):
            hex_color_str = all_grid_colors[pad_1d_index]
            picked_qcolor = QColor(hex_color_str)
            if picked_qcolor.isValid():
                self.color_picker_manager.set_current_selected_color(picked_qcolor, source="eyedropper")
                self.status_bar.showMessage(f"Color picked: {picked_qcolor.name().upper()}", 3000)
                self.set_eyedropper_mode(False, "auto_deactivate_after_pick") # Turn off eyedropper
            else:
                self.status_bar.showMessage("Eyedropper: Could not determine pad color.", 2000)
        else:
            self.status_bar.showMessage("Eyedropper: Invalid pad index.", 2000)
    # icon png path
    def _set_window_icon(self):
        icon_path = get_resource_path(os.path.join("resources", "icons", "app_icon.png"))
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        else:
            print(f"MainWindow WARNING: Window icon not found at '{icon_path}'")
    # --- Directory Management ---
    def _get_presets_base_dir_path(self) -> str:
        """Determines the base path for presets (static layouts, sequences)."""
        try:
            gui_dir_path = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.dirname(gui_dir_path)
        except NameError:
            project_root = os.path.dirname(os.path.abspath(sys.argv[0]))
        return os.path.join(project_root, PRESETS_BASE_DIR_NAME)
    # --- Directory Management ---
    def ensure_user_dirs_exist(self):
        """Ensures that user-specific subdirectories for presets and sequences exist."""
        paths = [
            os.path.join(self.presets_base_dir_path, "static", "user"),
            os.path.join(self.presets_base_dir_path, "static", "prefab"),
            os.path.join(self.presets_base_dir_path, "sequences", "user"),
            os.path.join(self.presets_base_dir_path, "sequences", "prefab"),
            os.path.join(self.presets_base_dir_path, "sequences", "sampler_recordings") # Ensure sampler dir exists
        ]
        for path in paths:
            os.makedirs(path, exist_ok=True)
    # --- UI Layout and Initialization Methods ---
    def _init_ui_layout(self):
        """Initializes the main window's central widget and top-level layout (left/right panels)."""
        self.central_widget_main = QWidget()
        self.setCentralWidget(self.central_widget_main)
        self.main_app_layout = QHBoxLayout(self.central_widget_main)
        self.main_app_layout.setSpacing(10)
        # Left Panel (Pad Grid, Animator, Sampler UI)
        self.left_panel_widget = QWidget()
        self.left_panel_layout = QVBoxLayout(self.left_panel_widget)
        self.left_panel_layout.setContentsMargins(5,5,5,5)
        self.left_panel_layout.setSpacing(10)      
        pad_grid_outer_container = self._create_pad_grid_section() # Creates InteractivePadGridFrame
        self.left_panel_layout.addWidget(pad_grid_outer_container)      
        self.main_app_layout.addWidget(self.left_panel_widget, 2) # Left panel takes more space
        # Right Panel (MIDI, Color Picker, Tools, Static Layouts)
        self.right_panel_widget = QWidget()
        self.right_panel_layout_v = QVBoxLayout(self.right_panel_widget)
        self.right_panel_widget.setMinimumWidth(380)
        self.right_panel_widget.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
        self.main_app_layout.addWidget(self.right_panel_widget, 1)
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready. Please connect to AKAI Fire.")
    # --- Pad Grid Section Initialization ---
    def _create_pad_grid_section(self) -> QWidget:
        """Creates the InteractivePadGridFrame and its container for the left panel."""
        pad_grid_outer_container = QWidget()
        pad_grid_container_layout = QVBoxLayout(pad_grid_outer_container)
        pad_grid_container_layout.setContentsMargins(0,0,0,0)
        self.pad_grid_frame = InteractivePadGridFrame(parent=self)
        pad_grid_container_layout.addWidget(self.pad_grid_frame, 0, Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)        
        return pad_grid_outer_container
   # --- Right Panel Initialization ---
    def _init_managers_right_panel(self):
        """Initializes and adds widgets to the right panel (MIDI, Color Picker, etc.)."""
        # MIDI Connection
        connection_group = QGroupBox("🔌 MIDI Connection")
        connection_layout = QHBoxLayout(connection_group)    
        self.port_combo_direct_ref = QComboBox()
        self.port_combo_direct_ref.addItem("Initializing...") # Add a temporary item
        print(f"DIAGNOSTIC_MAINWINDOW: self.port_combo_direct_ref CREATED, bool is {bool(self.port_combo_direct_ref)}")
        self.port_combo_direct_ref.clear() # Clear it before actual population
        self.port_combo_direct_ref.setPlaceholderText("Select MIDI Port")
        self.port_combo_direct_ref.currentIndexChanged.connect(self._on_port_combo_changed)
        self.connect_button_direct_ref = QPushButton("Connect")
        self.connect_button_direct_ref.clicked.connect(self.toggle_connection)
        self.connect_button_direct_ref.setEnabled(False)
        connection_layout.addWidget(QLabel("Port:"))
        connection_layout.addWidget(self.port_combo_direct_ref, 1)
        connection_layout.addWidget(self.connect_button_direct_ref)
        self.right_panel_layout_v.addWidget(connection_group)
        # Color Picker Manager
        self.color_picker_manager = ColorPickerManager(
            initial_color=self.selected_qcolor,
            parent_group_title="🎨 Advanced Color Picker",
            config_save_path_func=get_user_config_file_path
        )
        self.right_panel_layout_v.addWidget(self.color_picker_manager)
        # Quick Tools
        self.quick_tools_group_ref = self._init_direct_controls_right_panel()
        if self.quick_tools_group_ref:
            self.right_panel_layout_v.addWidget(self.quick_tools_group_ref)
        # Static Layouts Manager
        self.static_layouts_manager = StaticLayoutsManager(
            presets_base_path=self.presets_base_dir_path,
            group_box_title="▦ Static Pad Layouts"
        )
        self.right_panel_layout_v.addWidget(self.static_layouts_manager)      
        self.right_panel_layout_v.addStretch(1)
    # init right panel
    def _init_direct_controls_right_panel(self) -> QGroupBox:
        """Creates the 'Quick Tools' GroupBox with its buttons (Set Black, Clear, Eyedropper)."""
        tool_buttons_group = QGroupBox("🛠️ Quick Tools")
        tool_buttons_layout = QHBoxLayout(tool_buttons_group)
        self.color_button_off = QPushButton("Set Black")
        self.color_button_off.setToolTip("Set current painting color to Black (Off)")
        self.color_button_off.clicked.connect(self._handle_paint_black_button)
        tool_buttons_layout.addWidget(self.color_button_off)        
        self.clear_all_button = QPushButton("Clear Pads")
        self.clear_all_button.setToolTip("Set all pads to Black & clear current GUI/Frame.")
        self.clear_all_button.clicked.connect(self.clear_all_hardware_and_gui_pads)
        tool_buttons_layout.addWidget(self.clear_all_button)
        self.eyedropper_button = QPushButton("💧 Eyedropper")
        self.eyedropper_button.setToolTip("Toggle Eyedropper mode (I key) - Click a pad to pick its color.")
        self.eyedropper_button.setCheckable(True)
        self.eyedropper_button.toggled.connect(self._on_eyedropper_button_toggled)
        tool_buttons_layout.addWidget(self.eyedropper_button)        
        return tool_buttons_group
    # init left panel
    def _init_animator_and_sampler_ui_left_panel(self):
        # Animator Manager Widget
        self.animator_manager = AnimatorManagerWidget(
            presets_base_path=self.presets_base_dir_path,
            parent=self
        )
        self.left_panel_layout.addWidget(self.animator_manager)
        self.screen_sampler_manager = ScreenSamplerManager( 
            presets_base_path=self.presets_base_dir_path,
            animator_manager_ref=self.animator_manager, 
            parent=self 
        )
        # Add its UI widget to the layout
        self.left_panel_layout.addWidget(self.screen_sampler_manager.get_ui_widget())
        self.left_panel_layout.addStretch(1)
    # --- UI Interaction Methods ---
    def _handle_load_sequence_request(self, filepath: str):
        """
        Handles a request TO MainWindow to load a sequence (e.g., from a File > Open menu).
        It will prompt for saving current work if needed, then tell AnimatorManagerWidget to load.
        """
        if not self.animator_manager: return
        # Prompt to save current animation if modified (querying animator_manager)
        if self.animator_manager.active_sequence_model.is_modified:
            reply = QMessageBox.question(self, "Unsaved Changes",
                                         f"Animation '{self.animator_manager.active_sequence_model.name}' has unsaved changes. Save now?",
                                         QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel,
                                         QMessageBox.StandardButton.Cancel)
            if reply == QMessageBox.StandardButton.Save:
                save_success = self.animator_manager.action_save_sequence_as() # AMW handles save dialog for now
                if not save_success or self.animator_manager.active_sequence_model.is_modified:
                    self.status_bar.showMessage("Load cancelled due to unsaved changes.", 3000)
                    return
            elif reply == QMessageBox.StandardButton.Cancel:
                self.status_bar.showMessage("Load cancelled.", 2000)
                return      
        # Tell AnimatorManagerWidget to perform the load
        self.animator_manager._handle_load_sequence_request(filepath) # AMW internal load logic
    # --- Signal Connections ---
    def _connect_signals(self):
        """Connects signals from various components to their handlers."""
        # InteractivePadGridFrame signals
        if self.pad_grid_frame:
            self.pad_grid_frame.pad_action_requested.connect(self._handle_grid_pad_action)
            self.pad_grid_frame.pad_context_menu_requested_from_button.connect(self.show_pad_context_menu)
            self.pad_grid_frame.pad_single_left_click_action_requested.connect(self._handle_grid_pad_single_left_click)
        # Color Picker Manager
        if self.color_picker_manager:
            self.color_picker_manager.final_color_selected.connect(self._handle_final_color_selection_from_manager)
            self.color_picker_manager.status_message_requested.connect(self.status_bar.showMessage)       
        # Static Layouts Manager
        if self.static_layouts_manager:
            self.static_layouts_manager.apply_layout_data_requested.connect(self._handle_apply_static_layout_data)
            self.static_layouts_manager.request_current_grid_colors.connect(self._provide_grid_colors_for_static_save)
            self.static_layouts_manager.status_message_requested.connect(self.status_bar.showMessage)
        # Screen Sampler Manager (signals for sampled colors and status updates)
        if self.screen_sampler_manager:
            self.screen_sampler_manager.sampled_colors_for_display.connect(
                lambda colors: self.apply_colors_to_main_pad_grid(
                    [QColor(r, g, b).name() for r, g, b in colors], update_hw=True
                )
            )
            self.screen_sampler_manager.sampler_status_update.connect(self.status_bar.showMessage)
            self.screen_sampler_manager.sampling_activity_changed.connect(self._on_sampler_activity_changed) # This updates animator controls
            self.screen_sampler_manager.new_sequence_from_recording_ready.connect(self._handle_load_sequence_request)
        # AnimatorManagerWidget Signals
        if self.animator_manager:
            self.animator_manager.active_frame_data_for_display.connect(self._on_animator_frame_data_for_display)
            self.animator_manager.playback_status_update.connect(self.status_bar.showMessage)
            self.animator_manager.sequence_modified_status_changed.connect(self._on_animator_sequence_modified_status_changed)
            self.animator_manager.undo_redo_state_changed.connect(self._on_animator_undo_redo_state_changed)
            self.animator_manager.clipboard_state_changed.connect(self._on_animator_clipboard_state_changed)
            self.animator_manager.request_sampler_disable.connect(self._handle_request_sampler_disable)
        # AkaiFireController signals
    def _on_sampler_activity_changed(self, is_active: bool):
        self._update_animator_controls_enabled_state()
        # This will be called when the screen sampler starts/stops sampling
    def _create_edit_actions(self):
        """Creates global QActions for editing, menus, and shortcuts."""
        # Undo Action
        self.undo_action = QAction("Undo Sequence Edit", self) # Corrected
        self.undo_action.setShortcut(QKeySequence.StandardKey.Undo)
        self.undo_action.setToolTip(f"Undo ({QKeySequence(QKeySequence.StandardKey.Undo).toString(QKeySequence.SequenceFormat.NativeText)})")
        self.undo_action.triggered.connect(self.action_animator_undo) # Connects to new delegating method
        self.addAction(self.undo_action)
        # Redo Action
        self.redo_action = QAction("Redo Sequence Edit", self) # Corrected
        self.redo_action.setShortcut(QKeySequence.StandardKey.Redo)
        self.redo_action.setToolTip(f"Redo ({QKeySequence(QKeySequence.StandardKey.Redo).toString(QKeySequence.SequenceFormat.NativeText)})")
        self.redo_action.triggered.connect(self.action_animator_redo) # Connects to new delegating method
        self.addAction(self.redo_action)

        # Copy/Cut/Paste/Duplicate/Delete
        from animator.controls_widget import ICON_COPY, ICON_CUT, ICON_DUPLICATE, ICON_DELETE 
        # Copy Action
        self.copy_action = QAction(ICON_COPY + " Copy Frame(s)", self) # Corrected
        self.copy_action.setShortcut(QKeySequence.StandardKey.Copy)
        copy_shortcut_str = QKeySequence(QKeySequence.StandardKey.Copy).toString(QKeySequence.SequenceFormat.NativeText)
        self.copy_action.setToolTip(f"Copy selected frame(s) to clipboard ({copy_shortcut_str})")
        self.copy_action.triggered.connect(self.action_animator_copy_frames)
        self.addAction(self.copy_action)
        # Cut
        self.cut_action = QAction(ICON_CUT + " Cut Frame(s)", self) # Corrected
        self.cut_action.setShortcut(QKeySequence.StandardKey.Cut)
        cut_shortcut_str = QKeySequence(QKeySequence.StandardKey.Cut).toString(QKeySequence.SequenceFormat.NativeText)
        self.cut_action.setToolTip(f"Cut selected frame(s) to clipboard ({cut_shortcut_str})")
        self.cut_action.triggered.connect(self.action_animator_cut_frames)
        self.addAction(self.cut_action)
        # Paste Action
        self.paste_action = QAction(ICON_DUPLICATE + " Paste Frame(s)", self) # Corrected (using DUPLICATE icon for paste)
        self.paste_action.setShortcut(QKeySequence.StandardKey.Paste)
        paste_shortcut_str = QKeySequence(QKeySequence.StandardKey.Paste).toString(QKeySequence.SequenceFormat.NativeText)
        self.paste_action.setToolTip(f"Paste frame(s) from clipboard ({paste_shortcut_str})")
        self.paste_action.triggered.connect(self.action_animator_paste_frames)
        self.addAction(self.paste_action)
        # Duplicate Action
        self.duplicate_action = QAction(ICON_DUPLICATE + " Duplicate Frame(s)", self) # Corrected
        self.duplicate_action.setShortcut(QKeySequence(Qt.Modifier.CTRL | Qt.Key.Key_D))
        duplicate_shortcut_str = QKeySequence(Qt.Modifier.CTRL | Qt.Key.Key_D).toString(QKeySequence.SequenceFormat.NativeText)
        self.duplicate_action.setToolTip(f"Duplicate selected frame(s) ({duplicate_shortcut_str})")
        self.duplicate_action.triggered.connect(self.action_animator_duplicate_frames)
        self.addAction(self.duplicate_action)
        # Delete Action
        self.delete_action = QAction(ICON_DELETE + " Delete Frame(s)", self) # Corrected
        self.delete_action.setShortcut(QKeySequence.StandardKey.Delete)
        delete_shortcut_str = QKeySequence(QKeySequence.StandardKey.Delete).toString(QKeySequence.SequenceFormat.NativeText)
        self.delete_action.setToolTip(f"Delete selected frame(s) ({delete_shortcut_str})")
        self.delete_action.triggered.connect(self.action_animator_delete_frames)
        self.addAction(self.delete_action)
        # Animator File QActions
        self.new_sequence_action = QAction("✨ New Sequence", self) # Corrected
        self.new_sequence_action.setShortcut(QKeySequence.StandardKey.New)
        new_seq_shortcut_str = QKeySequence(QKeySequence.StandardKey.New).toString(QKeySequence.SequenceFormat.NativeText)
        self.new_sequence_action.setToolTip(f"Create a new, empty animation sequence ({new_seq_shortcut_str})")
        self.new_sequence_action.triggered.connect(lambda: self.action_animator_new_sequence(prompt_save=True))
        self.addAction(self.new_sequence_action)
        # Save Sequence As Action
        self.save_sequence_as_action = QAction("💾 Save Sequence As...", self) # Corrected
        self.save_sequence_as_action.setShortcut(QKeySequence(Qt.Modifier.CTRL | Qt.Modifier.SHIFT | Qt.Key.Key_S))
        save_as_shortcut_str = QKeySequence(Qt.Modifier.CTRL | Qt.Modifier.SHIFT | Qt.Key.Key_S).toString(QKeySequence.SequenceFormat.NativeText)
        self.save_sequence_as_action.setToolTip(f"Save the current animation sequence to a new file ({save_as_shortcut_str})")
        self.save_sequence_as_action.triggered.connect(self.action_animator_save_sequence_as)
        self.addAction(self.save_sequence_as_action)
        # Eyedropper Action
        self.eyedropper_action = QAction("💧 Eyedropper Mode", self) # Corrected
        self.eyedropper_action.setShortcut(QKeySequence(Qt.Key.Key_I))
        eyedropper_shortcut_str = QKeySequence(Qt.Key.Key_I).toString(QKeySequence.SequenceFormat.NativeText)
        self.eyedropper_action.setToolTip(f"Toggle Eyedropper mode to pick a color from a pad ({eyedropper_shortcut_str}).")
        self.eyedropper_action.setCheckable(True)
        self.eyedropper_action.triggered.connect(self.toggle_eyedropper_mode)
        self.addAction(self.eyedropper_action)
        # Global Play/Pause Action for Animator
        self.play_pause_action = QAction("Play/Pause Sequence", self) # Corrected
        self.play_pause_action.setShortcut(QKeySequence(Qt.Key.Key_Space))
        play_pause_shortcut_str = QKeySequence(Qt.Key.Key_Space).toString(QKeySequence.SequenceFormat.NativeText)
        self.play_pause_action.setToolTip(f"Play or Pause the current animation sequence ({play_pause_shortcut_str})")
        self.play_pause_action.triggered.connect(self.action_animator_play_pause_toggle)
        self.addAction(self.play_pause_action)
    # --- Eyedropper Logic ---
    def _on_eyedropper_button_toggled(self, checked: bool):
        """Handles the eyedropper UI button's toggled state, syncing with the QAction."""
        self.set_eyedropper_mode(checked, source="button_toggle")
    # Toggle Eyedropper Mode
    def toggle_eyedropper_mode(self, checked: bool | None = None, source: str = "action_trigger"):
        """Toggles eyedropper mode, or sets it if 'checked' is provided."""
        new_state = not self.is_eyedropper_mode_active if checked is None else checked
        self.set_eyedropper_mode(new_state, source)
    # --- Eyedropper Logic 
    def set_eyedropper_mode(self, active: bool, source: str = "unknown"):
        """Activates or deactivates eyedropper mode and updates related UI."""
        if self.is_eyedropper_mode_active == active:
            return
        self.is_eyedropper_mode_active = active
        if self.is_eyedropper_mode_active:
            self.status_bar.showMessage("Eyedropper active: Click a pad to pick its color.", 0)
            if self.pad_grid_frame: self.pad_grid_frame.setCursor(Qt.CursorShape.CrossCursor)
        else:
            self.status_bar.showMessage("Eyedropper deactivated.", 2000)
            if self.pad_grid_frame: self.pad_grid_frame.unsetCursor()
        # Sync button and action
        if self.eyedropper_button and self.eyedropper_button.isChecked() != self.is_eyedropper_mode_active:
            self.eyedropper_button.setChecked(self.is_eyedropper_mode_active)
        if self.eyedropper_action and self.eyedropper_action.isChecked() != self.is_eyedropper_mode_active:
            self.eyedropper_action.setChecked(self.is_eyedropper_mode_active)        
        self._update_animator_controls_enabled_state() # Update general UI enabled states
    # --- Eyedropper Logic End ---
    def _pick_color_from_pad(self, row: int, col: int):
        """Picks color from the specified pad and sets it in ColorPickerManager."""
        if not self.color_picker_manager or not self.pad_grid_frame:
            return        
        all_grid_colors = self.pad_grid_frame.get_current_grid_colors_hex()
        pad_1d_index = row * 16 + col # Assuming 16 columns (GRID_COLS from interactive_pad_grid)
        if 0 <= pad_1d_index < len(all_grid_colors):
            hex_color_str = all_grid_colors[pad_1d_index]
            picked_qcolor = QColor(hex_color_str)
            if picked_qcolor.isValid():
                self.color_picker_manager.set_current_selected_color(picked_qcolor, source="eyedropper")
                self.status_bar.showMessage(f"Color picked: {picked_qcolor.name().upper()}", 3000)
                self.set_eyedropper_mode(False, source="auto_deactivate_after_pick") # Turn off after pick
            else:
                self.status_bar.showMessage("Eyedropper: Could not determine pad color.", 2000)
        else:
            self.status_bar.showMessage("Eyedropper: Invalid pad index.", 2000)

    # --- Core Pad Interaction Methods (called by _handle_grid_pad_action or other UI) ---
    def apply_paint_to_pad(self, row: int, col: int, update_model: bool = True): # Parameter name now 'update_model'
        if not self.akai_controller.is_connected(): 
            return
        r, g, b, _ = self.selected_qcolor.getRgb()
        self.akai_controller.set_pad_color(row, col, r, g, b)
        if self.pad_grid_frame: 
             self.pad_grid_frame.update_pad_gui_color(row, col, r, g, b)
        if update_model and self.animator_manager: # Use 'update_model' here
            pad_1d_index = row * 16 + col 
            if self.animator_manager.active_sequence_model:
                self.animator_manager.active_sequence_model.update_pad_in_current_edit_frame(
                    pad_1d_index, self.selected_qcolor.name()
            )
        # Update the color picker to the selected color
    def apply_erase_to_pad(self, row: int, col: int, update_model: bool = True): # Parameter name now 'update_model'
        if not self.akai_controller.is_connected(): 
            return
        black_qcolor = QColor("black")
        r, g, b = 0,0,0
        self.akai_controller.set_pad_color(row, col, r, g, b)
        if self.pad_grid_frame:
            self.pad_grid_frame.update_pad_gui_color(row, col, r, g, b)
        if update_model and self.animator_manager: 
            pad_1d_index = row * 16 + col
            if self.animator_manager.active_sequence_model:
                self.animator_manager.active_sequence_model.update_pad_in_current_edit_frame(
                    pad_1d_index, black_qcolor.name()
            )
        # Update the color picker to black
    def show_pad_context_menu(self, pad_button_widget: QPushButton, row: int, col: int, local_pos_to_button: QPoint):
        """Shows context menu for a pad, typically for setting it to black."""
        menu = QMenu(self)
        action_set_off = QAction("Set Pad to Black (Off)", self)
        action_set_off.triggered.connect(lambda: self.set_single_pad_black_and_update_model(row, col))
        menu.addAction(action_set_off)
        global_pos = pad_button_widget.mapToGlobal(local_pos_to_button)
        menu.exec(global_pos)
    # --- Context Menu Action for Pad Button ---
    def set_single_pad_black_and_update_model(self, row: int, col: int):
        """Sets a single pad to black and updates animator model; used by context menu."""
        self._handle_request_sampler_disable() # Ensure sampler is off
        self.apply_erase_to_pad(row, col, update_model=True) # Use the main erase method
        self.status_bar.showMessage(f"Pad ({row+1},{col+1}) set to Off.", 1500)
    # --- Methods to update the main pad grid display ---
    #--- Get Current Main Pad Grid Colors ---
    def apply_colors_to_main_pad_grid(self, colors_hex: list | None, update_hw=True):
        """Applies a list of 64 hex color strings to the GUI grid and optionally hardware."""
        if not colors_hex or len(colors_hex) != 64: # 4 rows * 16 cols
            self.clear_main_pad_grid_ui(update_hw=update_hw)
            return
        hardware_batch_update = []
        for i, hex_color_str in enumerate(colors_hex):
            row, col = divmod(i, 16) # Assuming 16 columns
            color = QColor(hex_color_str if hex_color_str else "#000000")
            if not color.isValid(): color = QColor("black")            
            if self.pad_grid_frame: # Update GUI via InteractivePadGridFrame
                self.pad_grid_frame.update_pad_gui_color(row, col, color.red(), color.green(), color.blue())            
            if update_hw:
                hardware_batch_update.append((row, col, color.red(), color.green(), color.blue()))        
        if update_hw and self.akai_controller.is_connected() and hardware_batch_update:
            self.akai_controller.set_multiple_pads_color(hardware_batch_update)
    # --- Clear Main Pad Grid UI ---
    def clear_main_pad_grid_ui(self, update_hw=True):
        """Clears the GUI pad grid to black and optionally updates hardware."""
        blank_colors_hex = [QColor("black").name()] * 64
        self.apply_colors_to_main_pad_grid(blank_colors_hex, update_hw=update_hw)
    # --- Clear All Pads and Current Animator Frame ---
    def clear_all_hardware_and_gui_pads(self):
        """Clears GUI, hardware, and current animator frame to black."""
        if not self.akai_controller.is_connected():
            self.status_bar.showMessage("Connect to device first.", 2000); return       
        self._handle_request_sampler_disable() # Ensure sampler is off
        if self.animator_manager: self.animator_manager.action_stop() # Stop animator playback
        self.clear_main_pad_grid_ui(update_hw=True) # Clears GUI and HW
        if self.animator_manager: # Clear current frame in animator model via manager
            self.animator_manager.active_sequence_model.clear_pads_in_current_edit_frame()
            # AMW's model will emit frame_content_updated, which AMW handles and signals MW if needed.
        self.status_bar.showMessage("All pads and current view cleared.", 2000)

    # --- Signal Handlers from Other Managers (Color Picker, Static Layouts) ---
    def _handle_final_color_selection_from_manager(self, color: QColor):
        self.selected_qcolor = color
        self.status_bar.showMessage(f"Active color: {color.name().upper()}", 3000)
    # --- Request Sampler Disable ---
    def _handle_paint_black_button(self):
        self._handle_request_sampler_disable() # Ensure sampler off
        black_color = QColor("black")
        self.selected_qcolor = black_color
        if self.color_picker_manager:
            self.color_picker_manager.set_current_selected_color(black_color, source="paint_black_button")
        self.status_bar.showMessage("Active color: Black (Off)", 2000)
    # --- Request Sampler Disable ---
    def _handle_apply_static_layout_data(self, colors_hex: list):
        if not self.akai_controller.is_connected():
            self.status_bar.showMessage("Connect to device first.", 2000); return
        self._handle_request_sampler_disable()
        if self.animator_manager: self.animator_manager.action_stop() # Stop animation
        self.apply_colors_to_main_pad_grid(colors_hex, update_hw=True)
        # Also update current animator frame if one is selected
        if self.animator_manager and self.animator_manager.active_sequence_model.get_current_edit_frame_index() != -1:
            self.animator_manager.active_sequence_model.update_all_pads_in_current_edit_frame(colors_hex)
        if colors_hex and colors_hex[0] and self.color_picker_manager: # Set picker to first color
            first_color = QColor(colors_hex[0])
            if first_color.isValid():
                self.color_picker_manager.set_current_selected_color(first_color, source="static_layout_apply")
    # --- Static Layouts Manager ---
    def _provide_grid_colors_for_static_save(self):
        """Provides current grid colors to StaticLayoutsManager when it requests them."""
        if self.static_layouts_manager and self.pad_grid_frame:
            current_colors = self.pad_grid_frame.get_current_grid_colors_hex()
            self.static_layouts_manager.save_layout_with_colors(current_colors)   
    # --- UI State Management ---
    def _update_animator_controls_enabled_state(self):
        """Updates the enabled state of various UI groups based on global app state."""
        is_connected = self.akai_controller.is_connected()
        # Use manager's state
        is_screen_sampling_active = self.screen_sampler_manager.is_sampling_active() if self.screen_sampler_manager else False
        can_interact_with_direct_controls = is_connected and not is_screen_sampling_active
        # Animator Manager Widget
        if self.animator_manager:
            self.animator_manager.set_overall_enabled_state(can_interact_with_direct_controls)
            if self.new_sequence_action: self.new_sequence_action.setEnabled(can_interact_with_direct_controls)
            if self.save_sequence_as_action and self.animator_manager:
                 self.save_sequence_as_action.setEnabled(can_interact_with_direct_controls)
        # Eyedropper
        can_use_eyedropper = is_connected # Eyedropper can be used if connected
        if self.eyedropper_button: self.eyedropper_button.setEnabled(can_use_eyedropper)
        if self.eyedropper_action: self.eyedropper_action.setEnabled(can_use_eyedropper)
        # Sync checked states if needed (set_eyedropper_mode does this)
        # Global Play/Pause Action
        if self.play_pause_action:
            # Enable if animator can be interacted with and (ideally) has frames
            # AMW's action_play_pause_toggle will handle "no frames" case.
            self.play_pause_action.setEnabled(can_interact_with_direct_controls)
        # Pad Grid (InteractivePadGridFrame)
        if self.pad_grid_frame: self.pad_grid_frame.setEnabled(can_interact_with_direct_controls)        
        # Quick Tools & Other Right Panel Managers
        if self.clear_all_button: self.clear_all_button.setEnabled(can_interact_with_direct_controls)
        if self.color_button_off: self.color_button_off.setEnabled(can_interact_with_direct_controls)
        if self.color_picker_manager: self.color_picker_manager.set_enabled(can_interact_with_direct_controls)
        if self.static_layouts_manager: self.static_layouts_manager.set_enabled_state(can_interact_with_direct_controls)        
        # Screen Sampler UI
        if self.screen_sampler_manager:
            # MainWindow tells SSM the current connection status and general enable status.
            # SSM is then responsible for updating its own UI (ScreenSamplerUIManager)
            self.screen_sampler_manager.set_overall_enabled_state(is_connected, is_connected)
    # --- MIDI Connection Management ---
    def _on_port_combo_changed(self, index: int):
        """Handles selection change in MIDI port combo box."""
        if not self.connect_button_direct_ref or not self.port_combo_direct_ref: return
        if not self.akai_controller.is_connected():
            current_text = self.port_combo_direct_ref.itemText(index)
            can_connect = bool(current_text and current_text != "No MIDI output ports found")
            self.connect_button_direct_ref.setEnabled(can_connect)
        else: # Already connected, button should be "Disconnect" and enabled
            self.connect_button_direct_ref.setEnabled(True)
    #--- MIDI Connection Toggle ---
    def toggle_connection(self):
        """Connects to or disconnects from the selected MIDI port."""
        if self.akai_controller.is_connected():
            self.akai_controller.disconnect()
        else:
            port = self.port_combo_direct_ref.currentText()
            if port and port != "No MIDI output ports found":
                if not self.akai_controller.connect(port):
                    QMessageBox.warning(self, "Connection Failed", f"Could not connect to {port}.")
            else:
                self.status_bar.showMessage("Please select a valid MIDI port.", 3000)
        self.update_connection_status() # Updates UI based on new connection state
    #--- Update Connection Status ---
    def update_connection_status(self):
        """Updates UI elements to reflect MIDI connection status."""
        is_connected = self.akai_controller.is_connected()
        # print(f"DEBUG MW.update_connection_status: is_connected = {is_connected}")
        if self.connect_button_direct_ref:
            # print(f"DEBUG MW.update_connection_status: Calling SSM.set_overall_enabled_state({is_connected}, {is_connected})")
            self.connect_button_direct_ref.setText("Disconnect" if is_connected else "Connect")
            # Enable state handled by _on_port_combo_changed or if connected
            if is_connected: self.connect_button_direct_ref.setEnabled(True)
            else: self._on_port_combo_changed(self.port_combo_direct_ref.currentIndex() if self.port_combo_direct_ref else -1)
        self.status_bar.showMessage(f"Connected to: {self.akai_controller.port_name_used}" if is_connected else "Disconnected.")
        if self.port_combo_direct_ref: self.port_combo_direct_ref.setEnabled(not is_connected)
        if self.screen_sampler_manager:
            self.screen_sampler_manager.set_overall_enabled_state(is_connected, is_connected)
        #
        def final_update():
            print(f"DEBUG final_update: port_combo is {self.port_combo_direct_ref}")
            self._update_animator_controls_enabled_state()
        QTimer.singleShot(0, final_update)

    # --- Application Exit ---
    def closeEvent(self, event):
        """Handles window close event, prompting to save unsaved changes."""
        # Prompt to save animator changes if animator_manager exists and has unsaved changes
        if self.animator_manager and self.animator_manager.active_sequence_model.is_modified:
            reply = QMessageBox.question(self, "Unsaved Animator Changes",
                                         f"Animation '{self.animator_manager.active_sequence_model.name}' has unsaved changes. Save before exiting?",
                                         QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel,
                                         QMessageBox.StandardButton.Cancel)
            if reply == QMessageBox.StandardButton.Save:
                save_success = self.animator_manager.action_save_sequence_as() # AMW handles save dialog
                if not save_success: # If save was cancelled or failed
                    event.ignore(); return 
            elif reply == QMessageBox.StandardButton.Cancel:
                event.ignore(); return
        if self.screen_sampler_manager:
            self.screen_sampler_manager.on_application_exit()
        if self.animator_manager: self.animator_manager.stop_current_animation_playback()
        if self.color_picker_manager: self.color_picker_manager.save_color_picker_swatches_to_config()
        event.accept()
# --- Main Window Test ---
if __name__ == '__main__':
    app = QApplication(sys.argv)
    # Assuming fire_control_app.py sets global app icon and loads stylesheet.
    # For standalone MainWindow test:
    try:
        gui_dir = os.path.dirname(os.path.abspath(__file__))
        proj_root = os.path.dirname(gui_dir)
        style_file = os.path.join(proj_root, "resources", "styles", "style.qss")
        if os.path.exists(style_file):
            with open(style_file, "r") as f: app.setStyleSheet(f.read())
    except Exception as e: print(f"Error loading stylesheet for test: {e}")
# Create and show the main window
    main_win = MainWindow()
    main_win.show()
    sys.exit(app.exec())