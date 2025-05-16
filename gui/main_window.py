# AKAI_Fire_RGB_Controller/gui/main_window.py
import sys
import json
import os
import mss 
import glob  # <<< ADD THIS IMPORT
import re    # <<< ADD THIS IMPORT
from appdirs import user_config_dir
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QStatusBar, QGridLayout, QFrame,
    QGroupBox, QMenu, QSizePolicy,
    QMessageBox, QComboBox, QSpacerItem, QListWidget, QInputDialog
)
from PyQt6.QtCore import Qt, pyqtSignal, QPoint, QTimer
from PyQt6.QtGui import QColor, QPalette, QAction, QMouseEvent, QKeySequence, QIcon # Added QIcon
from PIL import Image 

# --- Project-Specific Imports ---
from .color_picker_manager import ColorPickerManager
from .static_layouts_manager import StaticLayoutsManager
# from .sequence_file_manager import SequenceFileManager, SEQUENCES_BASE_SUBDIR, PREFAB_SEQUENCES_DIR_NAME
from .capture_preview_dialog import CapturePreviewDialog 

from animator.timeline_widget import SequenceTimelineWidget
from animator.controls_widget import SequenceControlsWidget
from animator.model import SequenceModel, AnimationFrame

from hardware.akai_fire_controller import AkaiFireController

from features.screen_sampler_core import ScreenSamplerCore
from features.screen_sampler_thread import ScreenSamplerThread
from gui.screen_sampler_ui_manager import ScreenSamplerUIManager
from animator.controls_widget import ICON_COPY, ICON_CUT, ICON_DUPLICATE


# --- Constants ---
INITIAL_WINDOW_WIDTH = 1050 # User can resize later
INITIAL_WINDOW_HEIGHT = 900 
PAD_BUTTON_WIDTH = 40
PAD_BUTTON_HEIGHT = 50
PAD_GRID_SPACING = 3
PRESETS_BASE_DIR_NAME = "presets"
APP_NAME = "AKAI_Fire_RGB_Controller"
APP_AUTHOR = "YourProjectAuthorName" # Replace with your actual author/project name
SAMPLER_PREFS_FILENAME = "sampler_user_prefs.json"
# If you decide to move the main config too:
MAIN_CONFIG_FILENAME = "fire_controller_config.json"


class PadButton(QPushButton):
    request_paint_on_press = pyqtSignal(int, int)
    def __init__(self, row, col, parent=None):
        super().__init__(parent)
        self.row = row; self.col = col; self.setObjectName("PadButton")
        self.setFixedSize(PAD_BUTTON_WIDTH, PAD_BUTTON_HEIGHT)
        self.setCheckable(False); self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton: self.request_paint_on_press.emit(self.row, self.col)
        super().mousePressEvent(event)
    

def get_user_config_file_path(filename: str) -> str:
    """
    Determines the appropriate path for a user config file.
    Prioritizes AppData if packaged, falls back to a local 'user_settings' directory.
    """
    config_dir_to_use = ""
    try:
        # PyInstaller sets 'frozen' and '_MEIPASS'. Nuitka might need different check or compile-time flag.
        is_packaged = getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS')
        
        if is_packaged:
            config_dir_to_use = user_config_dir(APP_NAME, APP_AUTHOR)
            # print(f"DEBUG: Packaged app, using AppData config dir: {config_dir_to_use}")
        else: # Development mode
            # Try to go up from gui/ to project root, then user_settings/
            try:
                current_file_dir = os.path.dirname(os.path.abspath(__file__)) # gui/
                project_root = os.path.dirname(current_file_dir) # AKAI_Fire_RGB_Controller/
            except NameError: # Fallback if __file__ is not defined (e.g. interactive script execution)
                project_root = os.getcwd()
            config_dir_to_use = os.path.join(project_root, "user_settings")
            # print(f"DEBUG: Development mode, using local config dir: {config_dir_to_use}")

        os.makedirs(config_dir_to_use, exist_ok=True)
        return os.path.join(config_dir_to_use, filename)
    
    except Exception as e:
        print(f"WARNING: Error determining config path (will use CWD): {e}")
        # Absolute fallback if everything else fails (less ideal)
        fallback_dir = os.path.join(os.getcwd(), "user_settings_fallback")
        os.makedirs(fallback_dir, exist_ok=True)
        print(f"WARNING: Using CWD fallback config directory: {fallback_dir}")
        return os.path.join(fallback_dir, filename)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("🎛️ AKAI Fire RGB Controller - Visual Sampler")
        self.setGeometry(100, 100, INITIAL_WINDOW_WIDTH, INITIAL_WINDOW_HEIGHT)
        self._set_window_icon() # Call to set application icon

        self.quick_tools_group_ref: QGroupBox | None = None
        self.akai_controller = AkaiFireController(auto_connect=False)
        self.pad_buttons = {}
        self.selected_qcolor = QColor("red")
        self.is_drawing_with_left_button_down = False
        self._last_painted_pad_on_drag = None
        self.frame_clipboard: list[AnimationFrame] = []
        self.presets_base_dir_path = self._get_presets_base_dir_path()
        self.sampler_prefs_file_path = get_user_config_file_path(SAMPLER_PREFS_FILENAME)
        self.sampler_monitor_prefs = {}
        self.screen_sampler_thread = ScreenSamplerThread(parent=self)
        self.is_screen_sampling_active = False
        self.screen_sampler_monitor_list_cache = []
        self.animator_sequence_selection_combo: QComboBox = None
        self.current_sampler_params = { 
            'monitor_id': 1, 
            'region_rect_percentage': {'x': 0.4, 'y': 0.4, 'width': 0.2, 'height': 0.2}, 
            'adjustments': { 
                'saturation': 2.0, 'contrast': 1.5, 
                'brightness': 1.0, 'hue_shift': 0 
            },
            'frequency_ms': 200 
        }
        self.is_recording_sampler = False
        self.recorded_sampler_frames = [] 
        self.current_recording_frame_count = 0
        self.captured_sampler_frequency_ms = 200 
        self.MAX_RECORDING_FRAMES = 200 
        self.capture_preview_dialog: CapturePreviewDialog | None = None
        self._last_processed_sampler_image: Image.Image | None = None

        # UI Managers
        self.color_picker_manager: ColorPickerManager = None
        self.static_layouts_manager: StaticLayoutsManager = None
        self.screen_sampler_ui_manager: ScreenSamplerUIManager = None
        self.sequence_timeline_widget: SequenceTimelineWidget = None
        self.sequence_controls_widget: SequenceControlsWidget = None
        self.active_sequence_model = SequenceModel() # Initialize with a default model
        self.playback_timer = QTimer(self); self.playback_timer.timeout.connect(self.advance_and_play_next_frame)

        # UI Elements for Integrated Sequence File Management (initially None)
        self.animator_sequence_selection_combo: QComboBox = None
        self.animator_load_sequence_button: QPushButton = None
        self.animator_new_sequence_button: QPushButton = None
        self.animator_save_as_button: QPushButton = None
        self.animator_delete_sequence_button: QPushButton = None
        self.animator_studio_group_box_ref: QGroupBox = None
        
        # QActions (initially None)
        self.undo_action: QAction = None; self.redo_action: QAction = None
        self.copy_action: QAction = None; self.cut_action: QAction = None
        self.paste_action: QAction = None; self.duplicate_action: QAction = None
        self.delete_action: QAction = None
        self.new_sequence_action: QAction = None; self.save_sequence_as_action: QAction = None
        self.play_pause_action: QAction = None # For global spacebar

        self.pad_grid_frame: QFrame = None
        self.port_combo_direct_ref = None; self.connect_button_direct_ref = None
        self.clear_all_button: QPushButton | None = None
        self.color_button_off: QPushButton | None = None
        self.record_sampler_button: QPushButton | None = None
        self.recording_status_label: QLabel | None = None
        
        self.ensure_user_dirs_exist()

        # --- STEP 1: Build all UI Widgets ---
        self._init_ui_layout()  # Creates main layout structure
        self._init_managers_right_panel() # Creates right panel widgets
        self._init_animator_and_sampler_ui_left_panel() # << THIS CREATES self.animator_sequence_selection_combo

        # --- STEP 2: Load Preferences (might influence UI defaults if any were set before widget creation) ---
        self._load_sampler_preferences() 

        # --- STEP 3: Connect Signals for ALL created UI elements and Create QActions ---
        self._connect_signals()

        # --- STEP 4: Populate Data-Driven UI Elements (like ComboBoxes) NOW THAT THEY EXIST ---
        QTimer.singleShot(0, self.animator_refresh_sequences_list_and_select) # Populate sequence list

        # --- STEP 5: Initial MIDI Port Population & Connection Status Update ---
        self.populate_midi_ports() # This might call update_connection_status
        self.update_connection_status() # This calls _update_animator_controls_enabled_state

        # --- STEP 6: Final UI State Updates based on model and connection ---
        self._update_animator_ui_for_current_sequence() # Updates timeline based on active_sequence_model
        # _update_animator_controls_enabled_state is called by update_connection_status, 
        # and also by _update_animator_ui_for_current_sequence.
        # A final call here can be redundant but ensures states if other calls didn't cover everything.
        self._update_animator_controls_enabled_state()
### END OF MainWindow.__init__ ###

    def _generate_monitor_key(self, monitor_id: int) -> str | None:
        """Generates a stable key string for a given monitor_id using its geometry."""
        if not self.screen_sampler_monitor_list_cache:
            self._populate_sampler_monitor_list_ui() # Ensure cache is populated

        monitor_info = next((m for m in self.screen_sampler_monitor_list_cache if m['id'] == monitor_id), None)
        if monitor_info:
            # Key based on geometry for stability
            return f"{monitor_info['width']}x{monitor_info['height']}_{monitor_info['left']}_{monitor_info['top']}"
        print(f"MainWindow Warning: Could not find monitor info for ID {monitor_id} to generate key.")
        return None

    def _load_sampler_preferences(self):
        """Loads sampler preferences from the JSON file."""
        if os.path.exists(self.sampler_prefs_file_path):
            try:
                with open(self.sampler_prefs_file_path, 'r') as f:
                    loaded_prefs = json.load(f)
                    self.sampler_monitor_prefs = loaded_prefs.get("monitor_configurations", {})
                    
                    # Optional: Load last active monitor and update current_sampler_params if needed
                    last_active_key = loaded_prefs.get("last_active_monitor_key")
                    if last_active_key and last_active_key in self.sampler_monitor_prefs:
                        # Find the monitor_id that corresponds to this key
                        for mon_info in self.screen_sampler_monitor_list_cache: # May need to populate cache first
                            key_check = f"{mon_info['width']}x{mon_info['height']}_{mon_info['left']}_{mon_info['top']}"
                            if key_check == last_active_key:
                                self.current_sampler_params['monitor_id'] = mon_info['id']
                                saved_data_for_monitor = self.sampler_monitor_prefs[last_active_key]
                                if 'region_rect_percentage' in saved_data_for_monitor:
                                    self.current_sampler_params['region_rect_percentage'] = saved_data_for_monitor['region_rect_percentage']
                                if 'adjustments' in saved_data_for_monitor:
                                    self.current_sampler_params['adjustments'] = saved_data_for_monitor['adjustments']
                                print(f"MainWindow: Loaded last active sampler monitor ({mon_info['id']}) prefs.")
                                break
                print(f"MainWindow: Sampler preferences loaded from {self.sampler_prefs_file_path}")
            except json.JSONDecodeError:
                print(f"MainWindow Error: Could not decode JSON from {self.sampler_prefs_file_path}. Using defaults.")
                self.sampler_monitor_prefs = {}
            except Exception as e:
                print(f"MainWindow Error: Could not load sampler preferences: {e}")
                self.sampler_monitor_prefs = {}
        else:
            print(f"MainWindow: Sampler preferences file not found ({self.sampler_prefs_file_path}). Will use defaults and create on save.")
            self.sampler_monitor_prefs = {}

    def _save_sampler_preferences(self):
        """Saves the current sampler preferences to the JSON file."""
        try:
            # Prepare data to save
            data_to_save = {
                "monitor_configurations": self.sampler_monitor_prefs,
                # Optional: Save the key of the currently active monitor
                "last_active_monitor_key": self._generate_monitor_key(self.current_sampler_params['monitor_id'])
            }
            with open(self.sampler_prefs_file_path, 'w') as f:
                json.dump(data_to_save, f, indent=4)
            # print(f"MainWindow: Sampler preferences saved to {self.sampler_prefs_file_path}")
        except Exception as e:
            print(f"MainWindow Error: Could not save sampler preferences: {e}")


    def _set_window_icon(self):
        try:
            # Consistent way to get project root, assuming main_window.py is in gui/
            gui_dir_path = os.path.dirname(os.path.abspath(__file__))
            project_root_path = os.path.dirname(gui_dir_path)
        except NameError: # Fallback if __file__ is not defined
            project_root_path = os.path.dirname(os.path.abspath(sys.argv[0]))
            # If running fire_control_app.py from project root, this path needs adjustment
            # This assumes fire_control_app.py sets the app icon, which is better.
            # For MainWindow specific icon, this is fine.

        icon_path = os.path.join(project_root_path, "resources", "icons", "app_icon.png")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        else:
            print(f"MainWindow WARNING: Window icon not found at '{icon_path}'")


    def _on_port_combo_changed(self, index: int):
        # ... (content as before) ...
        if not self.connect_button_direct_ref or not self.port_combo_direct_ref: return
        is_connected = self.akai_controller.is_connected()
        if not is_connected:
            current_text = self.port_combo_direct_ref.itemText(index)
            can_connect = bool(current_text and current_text != "No MIDI output ports found")
            self.connect_button_direct_ref.setEnabled(can_connect)
        else:
            self.connect_button_direct_ref.setEnabled(True)

    def _get_presets_base_dir_path(self) -> str:
        # ... (content as before) ...
        try:
            gui_dir_path = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.dirname(gui_dir_path)
        except NameError:
            project_root = os.path.dirname(os.path.abspath(sys.argv[0]))
        return os.path.join(project_root, PRESETS_BASE_DIR_NAME)

    def ensure_user_dirs_exist(self):
        # ... (content as before) ...
        paths = [
            os.path.join(self.presets_base_dir_path, "static", "user"),
            os.path.join(self.presets_base_dir_path, "static", "prefab"),
            os.path.join(self.presets_base_dir_path, "sequences", "user"),
            os.path.join(self.presets_base_dir_path, "sequences", "prefab"),
        ]
        for path in paths:
            os.makedirs(path, exist_ok=True)
    def _on_record_sampler_button_clicked(self):
        # print(f"DEBUG MAINWINDOW: _on_record_sampler_button_clicked called. self.is_recording_sampler: {self.is_recording_sampler}, self.is_screen_sampling_active: {self.is_screen_sampling_active}")
        # print(f"DEBUG: _on_record_sampler_button_clicked called. self.is_recording_sampler: {self.is_recording_sampler}") 
        if self.is_recording_sampler:
            self._stop_sampler_recording()
        else:
            print(f"DEBUG: Attempting to start recording. Current self.is_screen_sampling_active: {self.is_screen_sampling_active}")
            # Check for unsaved changes in the current animator sequence
            if self.active_sequence_model and self.active_sequence_model.is_modified:
                reply = QMessageBox.question(self, "Unsaved Animator Sequence",
                                             "The current animation has unsaved changes.\n"
                                             "Starting a new recording will discard these changes.\n\n"
                                             "Discard unsaved animation and start recording?",
                                             QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
                                             QMessageBox.StandardButton.Cancel)
                if reply == QMessageBox.StandardButton.Cancel:
                    self.status_bar.showMessage("Recording cancelled.", 2000)
                    return
                else: # User chose to discard
                    # Effectively create a new blank sequence before starting recording setup
                    self.new_sequence(prompt_save=False) # prompt_save=False to avoid double prompt

            if not self.is_screen_sampling_active:
                reply = QMessageBox.question(self, "Sampler Inactive",
                                             "Screen sampler is not currently active.\n"
                                             "Start screen sampling to begin recording?",
                                             QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                             QMessageBox.StandardButton.No)
                if reply == QMessageBox.StandardButton.Yes:
                    if self.screen_sampler_ui_manager:
                        self.screen_sampler_ui_manager.enable_sampling_button.setChecked(True)
                        print(f"DEBUG: Set 'Toggle Ambient Sampling' to ON. Scheduling _start_sampler_recording via timer.")
                        QTimer.singleShot(200, self._start_sampler_recording) 
                    else:
                        self.status_bar.showMessage("Sampler UI not available.", 3000)
                else:
                    self.status_bar.showMessage("Recording cancelled; sampler not started.", 2000)
                return # Return whether sampler started or not, _start_sampler_recording is called via timer if yes.
            
            # If sampler is already active, start recording immediately
            self._start_sampler_recording()

    def _start_sampler_recording(self):
        print(f"DEBUG: _start_sampler_recording called. Current self.is_screen_sampling_active: {self.is_screen_sampling_active}")
        if not self.is_screen_sampling_active: # Double check if auto-start failed or was too slow
            self.status_bar.showMessage("Cannot start recording: Screen Sampler is not active.", 3000)
            if self.record_sampler_button: self.record_sampler_button.setText("🎬 Record Sample")
            if self.recording_status_label: self.recording_status_label.setText("Error: Sampler off")
            return

        self.is_recording_sampler = True
        self.recorded_sampler_frames.clear()
        self.current_recording_frame_count = 0
        self.captured_sampler_frequency_ms = self.current_sampler_params.get('frequency_ms', 200) # Get current live frequency

        if self.record_sampler_button: self.record_sampler_button.setText("🔴 Stop Recording")
        if self.recording_status_label: self.recording_status_label.setText(f"REC 0/{self.MAX_RECORDING_FRAMES}")
        self.status_bar.showMessage("Sampler recording started...", 0) # Persistent message

    def _stop_sampler_recording(self):
        self.is_recording_sampler = False
        if self.record_sampler_button: self.record_sampler_button.setText("🎬 Record Sample")
        
        final_frame_count = self.current_recording_frame_count
        if self.recording_status_label: self.recording_status_label.setText(f"Idle. {final_frame_count} frames recorded.")
        self.status_bar.showMessage(f"Recording stopped. {final_frame_count} frames captured.", 5000)

        if not self.recorded_sampler_frames:
            self.status_bar.showMessage("No frames were recorded.", 2000)
            return
        
        self._process_and_load_recorded_frames()

    # --- DEBUG: Check record_sampler_button connection in _connect_signals ---
    def _debug_check_record_sampler_button_connection(self):
        if self.record_sampler_button:  # Ensure self.record_sampler_button is not None
            self.record_sampler_button.clicked.connect(self._on_record_sampler_button_clicked)
            print("DEBUG MAINWINDOW: Connected record_sampler_button.clicked signal.")  # Add this temporary print
        else:
            print("DEBUG MAINWINDOW ERROR: self.record_sampler_button is None during _connect_signals!")

    def _process_and_load_recorded_frames(self):
        num_frames = len(self.recorded_sampler_frames)
        if num_frames == 0: return

        default_name = f"Sampled Sequence ({num_frames}f)"
        name, ok = QInputDialog.getText(self, "Name Recorded Sequence", 
                                        "Enter name for the new sequence:", text=default_name)
        
        if not ok or not name.strip():
            reply = QMessageBox.question(self, "Discard Recording?", 
                                         "Recording not named. Discard recorded frames?",
                                         QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                         QMessageBox.StandardButton.Yes) # Default to Yes to discard if unnamed
            if reply == QMessageBox.StandardButton.Yes:
                self.recorded_sampler_frames.clear()
                self.current_recording_frame_count = 0
                if self.recording_status_label: self.recording_status_label.setText("Idle. Recording discarded.")
                self.status_bar.showMessage("Recorded frames discarded.", 3000)
            # If No, user can try interacting with record button again if they wish, data is still there.
            return

        new_sequence = SequenceModel(name=name.strip())
        # recorded_sampler_frames already stores hex strings
        new_sequence.frames = [AnimationFrame(colors=frame_hex_data) for frame_hex_data in self.recorded_sampler_frames]
        
        new_sequence.frame_delay_ms = self.captured_sampler_frequency_ms 
        new_sequence.loop = True # Default to loop for recorded sequences
        new_sequence.is_modified = True # It's new and unsaved

        self.stop_current_animation() # Stop any existing animation playback
        self.active_sequence_model = new_sequence
        self._connect_signals_for_active_sequence_model()
        self._update_animator_ui_for_current_sequence() # This loads the first frame to grid
        self._update_animator_controls_enabled_state()
        
        self.status_bar.showMessage(f"Recorded sequence '{name}' loaded. Use 'Save Seq As...' to save.", 7000)
        
        # Clear the recording buffer
        self.recorded_sampler_frames.clear()
        self.current_recording_frame_count = 0

    def _init_ui_layout(self):
        # ... (content as before) ...
        self.central_widget_main = QWidget()
        self.setCentralWidget(self.central_widget_main)
        self.main_app_layout = QHBoxLayout(self.central_widget_main)
        self.main_app_layout.setSpacing(10)

        self.left_panel_widget = QWidget()
        self.left_panel_layout = QVBoxLayout(self.left_panel_widget) 
        self.left_panel_layout.setContentsMargins(5,5,5,5)
        self.left_panel_layout.setSpacing(10)
        
        pad_grid_outer_container = self._create_pad_grid_section()
        self.left_panel_layout.addWidget(pad_grid_outer_container)
        self.main_app_layout.addWidget(self.left_panel_widget, 2) 

        self.right_panel_widget = QWidget()
        self.right_panel_layout_v = QVBoxLayout(self.right_panel_widget)
        self.right_panel_widget.setMinimumWidth(380) 
        self.right_panel_widget.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
        self.main_app_layout.addWidget(self.right_panel_widget, 1)

        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready. Please connect to AKAI Fire.")


    def _create_pad_grid_section(self) -> QWidget:
        # ... (content as before, with corrected context menu lambda) ...
        pad_grid_outer_container = QWidget()
        pad_grid_container_layout = QVBoxLayout(pad_grid_outer_container)
        pad_grid_container_layout.setContentsMargins(0,0,0,0)
        self.pad_grid_frame = QFrame(); self.pad_grid_frame.setObjectName("PadGridFrame")
        pad_grid_layout = QGridLayout(); pad_grid_layout.setSpacing(PAD_GRID_SPACING)
        for r_idx in range(4):
            for c_idx in range(16):
                pad_button = PadButton(row=r_idx, col=c_idx)
                pad_button.request_paint_on_press.connect(self.handle_pad_press_for_drawing)
                pad_button.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
                pad_button.customContextMenuRequested.connect(
                    lambda local_pos, btn=pad_button: self.show_pad_context_menu(btn, btn.row, btn.col, local_pos)
                )
                self.pad_buttons[(r_idx, c_idx)] = pad_button
                pad_grid_layout.addWidget(pad_button, r_idx, c_idx)
                self.update_gui_pad_color(r_idx, c_idx, 0,0,0)
        self.pad_grid_frame.setLayout(pad_grid_layout)
        margins = self.pad_grid_frame.layout().contentsMargins()
        grid_width = (16 * PAD_BUTTON_WIDTH) + (15 * PAD_GRID_SPACING) + margins.left() + margins.right()
        grid_height = (4 * PAD_BUTTON_HEIGHT) + (3 * PAD_GRID_SPACING) + margins.top() + margins.bottom()
        self.pad_grid_frame.setFixedSize(grid_width, grid_height)
        pad_grid_container_layout.addWidget(self.pad_grid_frame, 0, Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)
        return pad_grid_outer_container

 ### START OF METHOD MainWindow._init_managers_right_panel ###
    def _init_managers_right_panel(self):
        # MIDI Connection (Stays at the top)
        connection_group = QGroupBox("🔌 MIDI Connection")
        connection_layout = QHBoxLayout(connection_group)
        self.port_combo_direct_ref = QComboBox()
        print(f"DIAGNOSTIC_MAINWINDOW: self.port_combo_direct_ref CREATED, bool is {bool(self.port_combo_direct_ref)}")
        self.port_combo_direct_ref.setPlaceholderText("Select MIDI Port")
        self.port_combo_direct_ref.currentIndexChanged.connect(self._on_port_combo_changed)
        self.connect_button_direct_ref = QPushButton("Connect")
        self.connect_button_direct_ref.clicked.connect(self.toggle_connection)
        self.connect_button_direct_ref.setEnabled(False)
        connection_layout.addWidget(QLabel("Port:"))
        connection_layout.addWidget(self.port_combo_direct_ref, 1)
        connection_layout.addWidget(self.connect_button_direct_ref)
        self.right_panel_layout_v.addWidget(connection_group)

        # Color Picker (Comes before Quick Tools in this corrected order)
        self.color_picker_manager = ColorPickerManager(
            initial_color=self.selected_qcolor, 
            parent_group_title="🎨 Advanced Color Picker",
            config_save_path_func=get_user_config_file_path 
        )
        self.right_panel_layout_v.addWidget(self.color_picker_manager)

        # Quick Tools (Created ONCE and added ONCE)
        self.quick_tools_group_ref = self._init_direct_controls_right_panel() 
        if self.quick_tools_group_ref: 
            self.right_panel_layout_v.addWidget(self.quick_tools_group_ref)
        # else:
            # print("DEBUG MAINWINDOW ERROR: _init_direct_controls_right_panel returned None!") # Should not happen

        # Static Layouts
        self.static_layouts_manager = StaticLayoutsManager(presets_base_path=self.presets_base_dir_path, group_box_title="▦ Static Pad Layouts")
        self.right_panel_layout_v.addWidget(self.static_layouts_manager)

        # --- Sequence File Manager section is now intentionally REMOVED from this panel ---
        
        self.right_panel_layout_v.addStretch(1)
### END OF METHOD MainWindow._init_managers_right_panel ###   


    def _init_direct_controls_right_panel(self):
        tool_buttons_group = QGroupBox("🛠️ Quick Tools")
        tool_buttons_layout = QHBoxLayout(tool_buttons_group)
        
        self.color_button_off = QPushButton("Paint: Black (Off)")
        # print(f"DEBUG MAINWINDOW INIT: Created self.color_button_off (id: {id(self.color_button_off)})") # <<< ADD
        self.color_button_off.setToolTip("Set current painting color to Black (Off)")
        self.color_button_off.setStatusTip("Set the active painting color to black (all LEDs off).")
        self.color_button_off.clicked.connect(self._handle_paint_black_button)
        tool_buttons_layout.addWidget(self.color_button_off)
        
        self.clear_all_button = QPushButton("Clear Device Pads")
        # print(f"DEBUG MAINWINDOW INIT: Created self.clear_all_button (id: {id(self.clear_all_button)})") # <<< ADD
        self.clear_all_button.setToolTip("Set all pads to Black & clear current GUI/Frame.")
        self.clear_all_button.setStatusTip("Turn off all pads on the Akai Fire and clear the current display/animator frame.")
        self.clear_all_button.clicked.connect(self.clear_all_hardware_and_gui_pads)
        tool_buttons_layout.addWidget(self.clear_all_button)
        
        return tool_buttons_group
    
    ### START OF METHOD MainWindow._init_animator_and_sampler_ui_left_panel (MODIFIED - Unconditional Creation) ###
    def _init_animator_and_sampler_ui_left_panel(self):
        self.animator_studio_group_box_ref = QGroupBox("🎬 Animator Studio")
        animator_studio_layout = QVBoxLayout(self.animator_studio_group_box_ref)

        # Sequence File Management UI
        seq_file_management_widget = QWidget()
        seq_file_layout_v = QVBoxLayout(seq_file_management_widget)
        seq_file_layout_v.setContentsMargins(0,0,0,0)
        seq_file_layout_v.setSpacing(4)

        # Row 1: ComboBox and Load Button
        combo_load_layout = QHBoxLayout()
        combo_load_layout.addWidget(QLabel("Sequence:"))

        # --- Ensure UNCONDITIONAL CREATION and remove fallback ---
        self.animator_sequence_selection_combo = QComboBox()  # Always create here
        print(f"DEBUG TRACE: animator_sequence_selection_combo CREATED in _init_panel: {self.animator_sequence_selection_combo}")
        self.animator_sequence_selection_combo.setPlaceholderText("--- Select Sequence ---")
        self.animator_sequence_selection_combo.setToolTip("Select a saved animation sequence to load or manage.")
        self.animator_sequence_selection_combo.setStatusTip("Lists available prefab, user-saved, and sampled sequences.")
        combo_load_layout.addWidget(self.animator_sequence_selection_combo, 1)

        self.animator_load_sequence_button = QPushButton("📲 Load")
        self.animator_load_sequence_button.setToolTip("Load the sequence selected in the dropdown.")
        self.animator_load_sequence_button.setStatusTip("Loads the selected animation, replacing the current one. Prompts to save unsaved changes.")
        combo_load_layout.addWidget(self.animator_load_sequence_button)

        animator_studio_layout.addLayout(combo_load_layout)

        # Row 2: New, Save As, Delete Buttons
        action_buttons_layout = QHBoxLayout()
        self.animator_new_sequence_button = QPushButton("✨ New")
        action_buttons_layout.addWidget(self.animator_new_sequence_button)

        self.animator_save_as_button = QPushButton("💾 Save As...")
        action_buttons_layout.addWidget(self.animator_save_as_button)

        self.animator_delete_sequence_button = QPushButton("🗑️ Delete")
        action_buttons_layout.addWidget(self.animator_delete_sequence_button)
        action_buttons_layout.addSpacerItem(QSpacerItem(10, 0, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))

        animator_studio_layout.addLayout(action_buttons_layout)

        separator_line = QFrame()
        separator_line.setFrameShape(QFrame.Shape.HLine)
        separator_line.setFrameShadow(QFrame.Shadow.Sunken)
        animator_studio_layout.addWidget(separator_line)

        self.sequence_timeline_widget = SequenceTimelineWidget()
        animator_studio_layout.addWidget(self.sequence_timeline_widget)

        self.sequence_controls_widget = SequenceControlsWidget()
        animator_studio_layout.addWidget(self.sequence_controls_widget)

        self.left_panel_layout.addWidget(self.animator_studio_group_box_ref)

        # Screen Sampler UI Manager
        self.screen_sampler_ui_manager = ScreenSamplerUIManager(parent=self)
        self.left_panel_layout.addWidget(self.screen_sampler_ui_manager)

        # Sampler Recording Controls GroupBox (as before)
        # ... (sampler recording UI setup) ...

        self.left_panel_layout.addStretch(1)
    ### END OF METHOD MainWindow._init_animator_and_sampler_ui_left_panel (MODIFIED - Unconditional Creation) ###

    # --- Animator Sequence File Management Logic (Ported from SequenceFileManager) ---
    def _animator_get_sequence_dir_path(self, dir_type: str = "user") -> str:
        """Gets absolute path to user, prefab, or sampler sequence directory."""
        # Constants from SequenceFileManager, now defined/used here
        _PREFAB_SEQUENCES_DIR_NAME = "prefab"
        _USER_SEQUENCES_DIR_NAME = "user"
        _SAMPLER_RECORDINGS_DIR_NAME = "sampler_recordings" 
        _SEQUENCES_BASE_SUBDIR = "sequences" 

        dir_name_map = {
            "user": _USER_SEQUENCES_DIR_NAME,
            "prefab": _PREFAB_SEQUENCES_DIR_NAME,
            "sampler": _SAMPLER_RECORDINGS_DIR_NAME
        }
        target_dir_name = dir_name_map.get(dir_type, _USER_SEQUENCES_DIR_NAME)
        return os.path.join(self.presets_base_dir_path, _SEQUENCES_BASE_SUBDIR, target_dir_name)

    def _animator_load_all_sequences_metadata(self) -> dict:
        # print("DEBUG SFM: _animator_load_all_sequences_metadata CALLED") # <<< ADD
        """
        Loads metadata for all sequences (prefab, user, sampler).
        Returns: dict {display_name_with_prefix: {"path": ..., "type": ..., "raw_name": ...}}
        """
        # Constants for prefixes, can be class members or local
        PREFIX_SAMPLER = "[Sampler] "
        PREFIX_PREFAB = "[Prefab] "
        PREFIX_USER = "" # No prefix for user by default

        loaded_sequences_metadata = {}
        seq_sources_config = [
            {"id": "sampler", "prefix": PREFIX_SAMPLER},
            {"id": "user", "prefix": PREFIX_USER},
            {"id": "prefab", "prefix": PREFIX_PREFAB}
        ]
        
        for source_config in seq_sources_config:
            type_id = source_config["id"]
            prefix = source_config["prefix"]
            abs_dir = self._animator_get_sequence_dir_path(type_id)
            # print(f"DEBUG SFM: Scanning for type '{type_id}' in dir: {abs_dir}") # <<< ADD DEBUG PRINT
            
            try:
                os.makedirs(abs_dir, exist_ok=True)
            except OSError as e:
                # print(f"DEBUG SFM Error: Could not create/access dir {abs_dir}: {e}") # <<< DEBUG PRINT
                continue

            if not os.path.isdir(abs_dir): continue
            
            for filepath in glob.glob(os.path.join(abs_dir, "*.json")):
                # print(f"DEBUG SFM: Found file: {filepath}") # <<< ADD DEBUG PRINT
                data = None
                try:
                    with open(filepath, "r", encoding='utf-8') as f: 
                        data = json.load(f) 
                    
                    if not isinstance(data, dict) or \
                       "name" not in data or \
                       "frames" not in data or \
                       not isinstance(data.get("frames"), list):
                        # print(f"MainWindow Info: Skipped malformed sequence (missing keys or frames not list): {filepath}")
                        continue 

                    raw_name_from_file = data.get("name", os.path.splitext(os.path.basename(filepath))[0])
                    # Clean up raw name for display part
                    display_part = str(raw_name_from_file).replace("_", " ").replace("-", " ")
                    display_name_with_prefix = prefix + display_part
                    
                    if display_name_with_prefix: # Ensure not empty
                        loaded_sequences_metadata[display_name_with_prefix] = {
                            "path": filepath, "type": type_id, "raw_name": raw_name_from_file
                        }
                except json.JSONDecodeError:
                    # print(f"MainWindow Warning: JSONDecodeError for sequence file {filepath}. Skipping.")
                    pass # Silently skip problematic files for now
                except Exception as e: 
                    # print(f"MainWindow Error: General error processing sequence file {filepath}: {type(e).__name__} - {e}")
                    pass
        # print(f"DEBUG SFM: Loaded metadata for {len(loaded_sequences_metadata)} sequences.") # <<< ADD DEBUG PRINT
        return loaded_sequences_metadata

### START OF METHOD MainWindow._animator_update_sequences_combobox ###
    def _animator_update_sequences_combobox(self, active_sequence_raw_name: str = None, 
                                           active_sequence_type_id: str = None):
        """Populates the animator sequence combobox."""
        # print("DEBUG SFM: _animator_update_sequences_combobox CALLED")
        
        # Check if the attribute itself is Python None (i.e., never assigned a QComboBox instance yet)
        if self.animator_sequence_selection_combo is None:
            # print("DEBUG SFM: self.animator_sequence_selection_combo is Python None - returning early.")
            return

        # At this point, self.animator_sequence_selection_combo should be a QComboBox instance,
        # even if bool(self.animator_sequence_selection_combo) might be False.
        # We proceed assuming its methods (.clear, .addItem, .count, .setCurrentIndex) work.
        # print(f"DEBUG TRACE: animator_sequence_selection_combo object in _update_combo: {self.animator_sequence_selection_combo}, bool() is {bool(self.animator_sequence_selection_combo)}")

        self.animator_sequence_selection_combo.blockSignals(True)
        current_text_before_clear = self.animator_sequence_selection_combo.currentText()
        self.animator_sequence_selection_combo.clear()
        self.animator_sequence_selection_combo.addItem("--- Select Sequence ---")

        all_metadata = self._animator_load_all_sequences_metadata() # This should have prints now
        
        if not all_metadata:
            self.animator_sequence_selection_combo.addItem("No sequences found")
            # print("DEBUG SFM: No sequence metadata found.")
        else:
            # print(f"DEBUG SFM: Populating combo with {len(all_metadata)} sequences.")
            sorted_display_names = sorted(
                all_metadata.keys(), 
                key=lambda k: (
                    0 if all_metadata[k]['type'] == 'prefab' else
                    1 if all_metadata[k]['type'] == 'sampler' else
                    2 if all_metadata[k]['type'] == 'user' else 3, 
                    k.lower()
                )
            )
            for display_name in sorted_display_names:
                self.animator_sequence_selection_combo.addItem(display_name, userData=all_metadata[display_name])

        target_select_idx = 0
        # ... (rest of selection logic as before) ...
        if active_sequence_raw_name and active_sequence_type_id:
            prefix_map = {"prefab": "[Prefab] ", "sampler": "[Sampler] ", "user": ""}
            prefix = prefix_map.get(active_sequence_type_id, "")
            text_to_find = prefix + str(active_sequence_raw_name).replace("_", " ").replace("-", " ")
            idx = self.animator_sequence_selection_combo.findText(text_to_find, Qt.MatchFlag.MatchFixedString)
            if idx != -1:
                target_select_idx = idx
        elif current_text_before_clear not in ["--- Select Sequence ---", "No sequences found", "Populating..."]: # Added Populating...
            idx = self.animator_sequence_selection_combo.findText(current_text_before_clear, Qt.MatchFlag.MatchFixedString)
            if idx != -1:
                target_select_idx = idx
        
        if self.animator_sequence_selection_combo.count() > target_select_idx :
             self.animator_sequence_selection_combo.setCurrentIndex(target_select_idx)
        
        self.animator_sequence_selection_combo.blockSignals(False)
        # Crucially, call _on_animator_sequence_combo_changed AFTER population and setting index
        # to correctly update button states based on the actual (possibly placeholder) selection.
        self._on_animator_sequence_combo_changed(self.animator_sequence_selection_combo.currentIndex())
### END OF METHOD MainWindow._animator_update_sequences_combobox ###


    def animator_refresh_sequences_list_and_select(self, active_sequence_raw_name: str = None, 
                                                   active_sequence_type_id: str = None):
        """Refreshes the list and attempts to select the specified sequence."""
        # print("DEBUG SFM: animator_refresh_sequences_list_and_select CALLED") # <<< ADD
        self._animator_update_sequences_combobox(active_sequence_raw_name, active_sequence_type_id)
        # Further enabling/disabling of controls is handled by _update_animator_controls_enabled_state


### START OF METHOD MainWindow._on_animator_sequence_combo_changed (WITH FORCED UPDATE) ###
    def _on_animator_sequence_combo_changed(self, index: int):
        """Handles selection change in the animator's sequence combobox."""
        print(f"DEBUG HANDLER: _on_animator_sequence_combo_changed called, index: {index}")
        if not self.animator_sequence_selection_combo: 
            print("DEBUG HANDLER: animator_sequence_selection_combo is None, returning.")
            return

        is_valid_item_selected = False
        can_delete_selected = False
        
        current_text = self.animator_sequence_selection_combo.itemText(index)
        item_data = self.animator_sequence_selection_combo.itemData(index)
        print(f"DEBUG HANDLER: current_text: '{current_text}', item_data: {item_data}") 

        if index > 0 and current_text != "No sequences found" and item_data and isinstance(item_data, dict) and "path" in item_data:
            is_valid_item_selected = True
            print("DEBUG HANDLER: Item considered valid for selection.")
            if item_data.get("type") in ["user", "sampler"]:
                can_delete_selected = True
                print("DEBUG HANDLER: Item considered deletable.")
        else:
            print("DEBUG HANDLER: Item NOT considered valid for selection or not deletable.")
        
        is_connected = self.akai_controller.is_connected()
        can_interact_directly_with_animator = is_connected and not self.is_screen_sampling_active
        print(f"DEBUG HANDLER: is_valid_item_selected: {is_valid_item_selected}, can_interact: {can_interact_directly_with_animator}, can_delete: {can_delete_selected}")

        if self.animator_load_sequence_button:
            new_load_enabled_state = can_interact_directly_with_animator and is_valid_item_selected
            self.animator_load_sequence_button.setEnabled(new_load_enabled_state)
            print(f"DEBUG HANDLER: Load button .setEnabled({new_load_enabled_state}) called.")
            
            # --- TRY FORCING UPDATE ---
            self.animator_load_sequence_button.style().unpolish(self.animator_load_sequence_button)
            self.animator_load_sequence_button.style().polish(self.animator_load_sequence_button)
            self.animator_load_sequence_button.update() # Request a repaint
            QApplication.processEvents() # Process pending events, including paint events
            print(f"DEBUG HANDLER: Load button is NOW enabled (checked property): {self.animator_load_sequence_button.isEnabled()}")
            # --- END FORCING UPDATE ---

        if self.animator_delete_sequence_button:
            new_delete_enabled_state = can_interact_directly_with_animator and can_delete_selected
            self.animator_delete_sequence_button.setEnabled(new_delete_enabled_state)
            print(f"DEBUG HANDLER: Delete button .setEnabled({new_delete_enabled_state}) called.")
            # --- TRY FORCING UPDATE (Optional, apply if load button fix works) ---
            self.animator_delete_sequence_button.style().unpolish(self.animator_delete_sequence_button)
            self.animator_delete_sequence_button.style().polish(self.animator_delete_sequence_button)
            self.animator_delete_sequence_button.update()
            QApplication.processEvents()
            print(f"DEBUG HANDLER: Delete button is NOW enabled (checked property): {self.animator_delete_sequence_button.isEnabled()}")
            # --- END FORCING UPDATE ---
### END OF METHOD MainWindow._on_animator_sequence_combo_changed (WITH FORCED UPDATE) ###

    def _on_animator_load_selected_sequence_button_clicked(self):
        """Handles click on the 'Load Selected' button for animator sequences."""
        if not self.animator_sequence_selection_combo: return
        index = self.animator_sequence_selection_combo.currentIndex()
        if index > 0:
            item_data = self.animator_sequence_selection_combo.itemData(index)
            if item_data and isinstance(item_data, dict) and "path" in item_data:
                self._handle_load_sequence_request(item_data["path"]) # Use existing main handler
            else:
                self.status_bar.showMessage("Sequence info not found for selection.", 2000)
        else:
            self.status_bar.showMessage("No valid sequence selected to load.", 2000)


    def _animator_sanitize_filename(self, name: str) -> str:
        name = str(name)
        name = re.sub(r'[^\w\s-]', '', name).strip() # Allow alphanumeric, whitespace, hyphen
        name = re.sub(r'[-\s]+', '_', name)      # Replace whitespace/hyphens with underscore
        return name if name else "untitled_sequence"

    def _on_animator_save_sequence_as_button_clicked(self):
        """Handles 'Save As...' button click for animator sequences."""
        if not self.active_sequence_model or self.active_sequence_model.get_frame_count() == 0:
            QMessageBox.information(self, "Save Sequence", "Cannot save: No frames in current sequence.")
            return

        # Prompt for name
        suggested_name = self.active_sequence_model.name if self.active_sequence_model.name != "New Sequence" else ""
        text, ok = QInputDialog.getText(self, "Save Sequence As...", "Sequence Name:", text=suggested_name)
        if not (ok and text and text.strip()):
            self.status_bar.showMessage("Save As cancelled or name empty.", 2000)
            return
        
        raw_name = text.strip()
        filename_base = self._animator_sanitize_filename(raw_name)
        filename = f"{filename_base}.json"
        
        # Forbid saving with names that would visually clash with [Prefab] or [Sampler] if user manually adds prefix
        if raw_name.lower().startswith(("[prefab]", "[sampler]")):
             QMessageBox.warning(self, "Save Error", "Sequence name cannot start with '[Prefab]' or '[Sampler]'. Please choose a different name.")
             return

        abs_user_dir = self._animator_get_sequence_dir_path("user")
        os.makedirs(abs_user_dir, exist_ok=True)
        filepath = os.path.join(abs_user_dir, filename)
        
        if os.path.exists(filepath):
            reply = QMessageBox.question(self, "Overwrite Confirmation", 
                                         f"File '{filename}' already exists. Overwrite?",
                                         QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, 
                                         QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.No:
                self.status_bar.showMessage("Save As cancelled (did not overwrite).", 2000)
                return
        
        # Update model name before saving, so it's stored in the JSON correctly
        self.active_sequence_model.set_name(raw_name) 
        if self.active_sequence_model.save_to_file(filepath):
            self.status_bar.showMessage(f"Sequence '{raw_name}' saved.", 2000)
            self.animator_refresh_sequences_list_and_select(raw_name, "user") # Refresh list and select new
        else:
            QMessageBox.critical(self, "Save Error", f"Could not save sequence to '{filepath}'.")
        self._update_animator_controls_enabled_state()


    def _on_animator_delete_selected_sequence_button_clicked(self):
        """Handles 'Delete' button click for animator sequences."""
        if not self.animator_sequence_selection_combo: return
        
        index = self.animator_sequence_selection_combo.currentIndex()
        if index <= 0: # Nothing valid selected
            self.status_bar.showMessage("No sequence selected to delete.", 2000)
            return

        item_data = self.animator_sequence_selection_combo.itemData(index)
        selected_display_name = self.animator_sequence_selection_combo.itemText(index)

        if not item_data or not isinstance(item_data, dict) or "path" not in item_data:
            self.status_bar.showMessage(f"Internal error: Selected sequence '{selected_display_name}' has no data.", 3000)
            self.animator_refresh_sequences_list_and_select()
            return

        seq_type = item_data.get("type")
        seq_path = item_data.get("path")
        
        if seq_type not in ["user", "sampler"]:
            QMessageBox.warning(self, "Delete Error", "Only user-saved or sampler-recorded sequences can be deleted via this UI."); return
        
        reply = QMessageBox.question(self, "Confirm Deletion", 
                                     f"Are you sure you want to permanently delete the sequence file for:\n'{selected_display_name}'?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, 
                                     QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            # Use the existing _handle_delete_sequence_request, which expects display_name, path, type_id
            self._handle_delete_sequence_request(selected_display_name, seq_path, seq_type)
            # _handle_delete_sequence_request should then call animator_refresh_sequences_list_and_select
            # and potentially new_sequence if the active one was deleted.

    # We still need _handle_load_sequence_request (called by Load button and SequenceFileManager)
    # And _handle_delete_sequence_request (called by _on_animator_delete_selected_sequence_button_clicked and SequenceFileManager)
    # The `new_sequence` method is already in MainWindow and is fine.
    # The `_handle_save_sequence_as_request` (called by SequenceFileManager) can be removed if SFM is fully removed.
    # For now, _on_animator_save_sequence_as_button_clicked is the new primary save UI trigger.

### END OF NEW/PORTED METHODS in MainWindow ###
### START OF METHOD MainWindow._connect_signals (MODIFIED - Debug Connection) ###
    def _connect_signals(self):
        # Color Picker
        if self.color_picker_manager:
            self.color_picker_manager.final_color_selected.connect(self._handle_final_color_selection_from_manager)
            self.color_picker_manager.status_message_requested.connect(self.status_bar.showMessage)
        
        # Static Layouts
        if self.static_layouts_manager:
            self.static_layouts_manager.apply_layout_data_requested.connect(self._handle_apply_static_layout_data)
            self.static_layouts_manager.request_current_grid_colors.connect(self._provide_grid_colors_for_static_save)
            self.static_layouts_manager.status_message_requested.connect(self.status_bar.showMessage)
        

        # Sampler Recording Button
        if self.record_sampler_button:
            try: self.record_sampler_button.clicked.disconnect(self._on_record_sampler_button_clicked)
            except TypeError: pass
            self.record_sampler_button.clicked.connect(self._on_record_sampler_button_clicked)

        # Screen Sampler UIManager and Thread
        if self.screen_sampler_ui_manager:
            try: self.screen_sampler_ui_manager.sampling_control_changed.disconnect(self._handle_sampler_basic_params_changed)
            except TypeError: pass
            self.screen_sampler_ui_manager.sampling_control_changed.connect(self._handle_sampler_basic_params_changed)
            self.screen_sampler_ui_manager.status_message_requested.connect(self.status_bar.showMessage)
            self.screen_sampler_ui_manager.request_monitor_list_population.connect(self._populate_sampler_monitor_list_ui)
            self.screen_sampler_ui_manager.show_capture_preview_requested.connect(self._show_capture_preview_dialog)

        if self.screen_sampler_thread:
            try: self.screen_sampler_thread.pad_colors_sampled.disconnect(self._handle_screen_sampled_colors_list)
            except TypeError: pass
            self.screen_sampler_thread.pad_colors_sampled.connect(self._handle_screen_sampled_colors_list)
            try: self.screen_sampler_thread.processed_image_ready.disconnect(self._handle_sampler_processed_image)
            except TypeError: pass
            self.screen_sampler_thread.processed_image_ready.connect(self._handle_sampler_processed_image)
            try: self.screen_sampler_thread.error_occurred.disconnect(self._handle_screen_sampler_error)
            except TypeError: pass
            self.screen_sampler_thread.error_occurred.connect(self._handle_screen_sampler_error)

        # Animator Components (Timeline and Controls Widgets)
        if self.sequence_timeline_widget:
            self.sequence_timeline_widget.frame_selected.connect(self.on_animator_frame_selected_in_timeline)
            self.sequence_timeline_widget.add_frame_action_triggered.connect(self.on_animator_add_frame_action_from_timeline_menu)
            self.sequence_timeline_widget.copy_frames_action_triggered.connect(self.on_animator_copy_frames)
            self.sequence_timeline_widget.cut_frames_action_triggered.connect(self.on_animator_cut_frames)
            self.sequence_timeline_widget.paste_frames_action_triggered.connect(self.on_animator_paste_frames)
            self.sequence_timeline_widget.duplicate_selected_action_triggered.connect(self.on_animator_duplicate_selected_frames_generic)
            self.sequence_timeline_widget.delete_selected_action_triggered.connect(self.on_animator_delete_selected_frames_generic)
            self.sequence_timeline_widget.select_all_action_triggered.connect(self.on_animator_select_all_frames)
            self.sequence_timeline_widget.insert_blank_frame_before_action_triggered.connect(
                lambda index: self.on_animator_add_frame_action_from_controls("blank", at_index=index))
            self.sequence_timeline_widget.insert_blank_frame_after_action_triggered.connect(
                lambda index: self.on_animator_add_frame_action_from_controls("blank", at_index=index + 1))

        if self.sequence_controls_widget:
            self.sequence_controls_widget.add_frame_requested.connect(self.on_animator_add_frame_action_from_controls)
            self.sequence_controls_widget.delete_selected_frame_requested.connect(self.on_animator_delete_selected_frames_generic)
            self.sequence_controls_widget.duplicate_selected_frame_requested.connect(self.on_animator_duplicate_selected_frames_generic)
            self.sequence_controls_widget.copy_frames_requested.connect(self.on_animator_copy_frames)
            self.sequence_controls_widget.cut_frames_requested.connect(self.on_animator_cut_frames)
            self.sequence_controls_widget.paste_frames_requested.connect(self.on_animator_paste_frames)
            self.sequence_controls_widget.navigate_first_requested.connect(self.on_animator_navigate_first)
            self.sequence_controls_widget.navigate_prev_requested.connect(self.on_animator_navigate_prev)
            self.sequence_controls_widget.navigate_next_requested.connect(self.on_animator_navigate_next)
            self.sequence_controls_widget.navigate_last_requested.connect(self.on_animator_navigate_last)
            self.sequence_controls_widget.play_requested.connect(self.on_animator_play)
            self.sequence_controls_widget.pause_requested.connect(self.on_animator_pause)
            self.sequence_controls_widget.stop_requested.connect(self.on_animator_stop)
            self.sequence_controls_widget.frame_delay_changed.connect(self.on_animator_frame_delay_changed)

        # --- Connect Signals for Integrated Animator File Management UI ---
        if self.animator_sequence_selection_combo is not None: # Check it's not Python None
            print(f"DEBUG CONNECT: Connecting currentIndexChanged for {self.animator_sequence_selection_combo}") # <<< ADD
            self.animator_sequence_selection_combo.currentIndexChanged.connect(self._on_animator_sequence_combo_changed)
        else:
            print("DEBUG CONNECT: animator_sequence_selection_combo IS NONE at connection time!") # <<< ADD

        if self.animator_load_sequence_button:
            self.animator_load_sequence_button.clicked.connect(self._on_animator_load_selected_sequence_button_clicked)
        if self.animator_new_sequence_button:
            self.animator_new_sequence_button.clicked.connect(lambda: self.new_sequence(prompt_save=True))
        if self.animator_save_as_button:
            self.animator_save_as_button.clicked.connect(self._on_animator_save_sequence_as_button_clicked)
        if self.animator_delete_sequence_button:
            self.animator_delete_sequence_button.clicked.connect(self._on_animator_delete_selected_sequence_button_clicked)
        # ---

        self._connect_signals_for_active_sequence_model()
        self._create_edit_actions() 
### END OF METHOD MainWindow._connect_signals (MODIFIED - Debug Connection) ###
    def _create_edit_actions(self):
        # ... (content as before) ...
        self.undo_action = QAction("Undo Sequence Edit", self); self.undo_action.setShortcut(QKeySequence.StandardKey.Undo)
        self.undo_action.setToolTip(f"Undo ({QKeySequence(QKeySequence.StandardKey.Undo).toString(QKeySequence.SequenceFormat.NativeText)})")
        self.undo_action.triggered.connect(self.on_animator_undo); self.addAction(self.undo_action)
        self.redo_action = QAction("Redo Sequence Edit", self); self.redo_action.setShortcut(QKeySequence.StandardKey.Redo)
        self.redo_action.setToolTip(f"Redo ({QKeySequence(QKeySequence.StandardKey.Redo).toString(QKeySequence.SequenceFormat.NativeText)})")
        self.redo_action.triggered.connect(self.on_animator_redo); self.addAction(self.redo_action)

         # --- New Animator Actions for Copy/Cut/Paste ---
        # --- Import ICON constants from animator.controls_widget ---
        # These are used for QAction labels for Copy/Cut/Paste/Delete/Duplicate
        from animator.controls_widget import ICON_COPY, ICON_CUT, ICON_DUPLICATE, ICON_DELETE
        copy_shortcut = QKeySequence.StandardKey.Copy
        self.copy_action = QAction(ICON_COPY + " Copy Frame(s)", self) # ICON_COPY from controls_widget
        self.copy_action.setShortcut(copy_shortcut)
        copy_shortcut_str = QKeySequence(copy_shortcut).toString(QKeySequence.SequenceFormat.NativeText)
        self.copy_action.setToolTip(f"Copy selected frame(s) to clipboard ({copy_shortcut_str})")
        self.copy_action.setStatusTip(f"Copies the currently selected animation frame(s) to the internal clipboard. Shortcut: {copy_shortcut_str}")
        self.copy_action.triggered.connect(self.on_animator_copy_frames)
        self.addAction(self.copy_action)

        cut_shortcut = QKeySequence.StandardKey.Cut
        self.cut_action = QAction(ICON_CUT + " Cut Frame(s)", self) # ICON_CUT from controls_widget
        self.cut_action.setShortcut(cut_shortcut)
        cut_shortcut_str = QKeySequence(cut_shortcut).toString(QKeySequence.SequenceFormat.NativeText)
        self.cut_action.setToolTip(f"Cut selected frame(s) to clipboard ({cut_shortcut_str})")
        self.cut_action.setStatusTip(f"Cuts the currently selected animation frame(s) to the internal clipboard and removes them from the sequence. Shortcut: {cut_shortcut_str}")
        self.cut_action.triggered.connect(self.on_animator_cut_frames)
        self.addAction(self.cut_action)

        paste_shortcut = QKeySequence.StandardKey.Paste
        self.paste_action = QAction(ICON_DUPLICATE + " Paste Frame(s)", self) # ICON_DUPLICATE is like clipboard icon
        self.paste_action.setShortcut(paste_shortcut)
        paste_shortcut_str = QKeySequence(paste_shortcut).toString(QKeySequence.SequenceFormat.NativeText)
        self.paste_action.setToolTip(f"Paste frame(s) from clipboard ({paste_shortcut_str})")
        self.paste_action.setStatusTip(f"Pastes frame(s) from the internal clipboard after the current selection or at the end of the sequence. Shortcut: {paste_shortcut_str}")
        self.paste_action.triggered.connect(self.on_animator_paste_frames)
        self.addAction(self.paste_action)
        
        # --- Global Play/Pause Action ---
        play_pause_shortcut = QKeySequence(Qt.Key.Key_Space) # Spacebar
        self.play_pause_action = QAction("Play/Pause Sequence", self)
        self.play_pause_action.setShortcut(play_pause_shortcut)
        play_pause_shortcut_str = play_pause_shortcut.toString(QKeySequence.SequenceFormat.NativeText)
        self.play_pause_action.setToolTip(f"Play or Pause the current animation sequence ({play_pause_shortcut_str})")
        self.play_pause_action.setStatusTip(f"Toggles playback of the animation sequence. Shortcut: {play_pause_shortcut_str}")
        self.play_pause_action.triggered.connect(self._on_global_play_pause_action_triggered)
        self.addAction(self.play_pause_action)

        # --- ADD DUPLICATE ACTION ---
        duplicate_shortcut = QKeySequence(Qt.Modifier.CTRL | Qt.Key.Key_D)
        self.duplicate_action = QAction(ICON_DUPLICATE + " Duplicate Frame(s)", self) # ICON_DUPLICATE from controls_widget
        self.duplicate_action.setShortcut(duplicate_shortcut)
        duplicate_shortcut_str = duplicate_shortcut.toString(QKeySequence.SequenceFormat.NativeText)
        self.duplicate_action.setToolTip(f"Duplicate selected frame(s) ({duplicate_shortcut_str})")
        self.duplicate_action.setStatusTip(f"Creates copies of the currently selected animation frame(s) after them. Shortcut: {duplicate_shortcut_str}")
        self.duplicate_action.triggered.connect(self.on_animator_duplicate_selected_frames_generic) # Connect to existing generic handler
        self.addAction(self.duplicate_action)
        # --- END ADD DUPLICATE ACTION ---

        # --- ADD DELETE ACTION ---
        from animator.controls_widget import ICON_DELETE # Ensure icon is imported if used

        delete_standard_key = QKeySequence.StandardKey.Delete # This is the enum member
        self.delete_action = QAction(ICON_DELETE + " Delete Frame(s)", self) 
        self.delete_action.setShortcut(delete_standard_key) # setShortcut can take the enum directly

        # To get the string representation for tooltips/status tips:
        # Create a QKeySequence object from the standard key
        delete_qkeysequence = QKeySequence(delete_standard_key) 
        delete_shortcut_str = delete_qkeysequence.toString(QKeySequence.SequenceFormat.NativeText) # Call toString on the QKeySequence object

        self.delete_action.setToolTip(f"Delete selected frame(s) ({delete_shortcut_str})")
        self.delete_action.setStatusTip(f"Removes the currently selected animation frame(s) from the sequence. Shortcut: {delete_shortcut_str}")
        self.delete_action.triggered.connect(self.on_animator_delete_selected_frames_generic)
        self.addAction(self.delete_action)
        # --- END ADD DELETE ACTION ---

        # --- Animator File QActions ---
        new_seq_shortcut = QKeySequence.StandardKey.New # Ctrl+N
        self.new_sequence_action = QAction("✨ New Sequence", self)
        self.new_sequence_action.setShortcut(new_seq_shortcut)
        new_seq_shortcut_str = QKeySequence(new_seq_shortcut).toString(QKeySequence.SequenceFormat.NativeText)
        self.new_sequence_action.setToolTip(f"Create a new, empty animation sequence ({new_seq_shortcut_str})")
        self.new_sequence_action.setStatusTip(f"Clears the animator and starts a new blank sequence. Shortcut: {new_seq_shortcut_str}.")
        self.new_sequence_action.triggered.connect(lambda: self.new_sequence(prompt_save=True)) # Connect to existing new_sequence method
        self.addAction(self.new_sequence_action)

        save_as_shortcut = QKeySequence(Qt.Modifier.CTRL | Qt.Modifier.SHIFT | Qt.Key.Key_S) # Ctrl+Shift+S
        self.save_sequence_as_action = QAction("💾 Save Sequence As...", self)
        self.save_sequence_as_action.setShortcut(save_as_shortcut)
        save_as_shortcut_str = save_as_shortcut.toString(QKeySequence.SequenceFormat.NativeText)
        self.save_sequence_as_action.setToolTip(f"Save the current animation sequence to a new file ({save_as_shortcut_str})")
        self.save_sequence_as_action.setStatusTip(f"Saves the current animation sequence, allowing you to choose a name and location. Shortcut: {save_as_shortcut_str}.")
        self.save_sequence_as_action.triggered.connect(self._on_animator_save_sequence_as_button_clicked) # Connect to existing save_as handler
        self.addAction(self.save_sequence_as_action)
        # ---

        # Initial state of actions will be updated in _update_animator_controls_enabled_state

    def _connect_signals_for_active_sequence_model(self):
        # Disconnect previous signals if any
        if self.active_sequence_model:
            try: self.active_sequence_model.frames_changed.disconnect()
            except TypeError: pass
            try: self.active_sequence_model.frame_content_updated.disconnect()
            except TypeError: pass
            try: self.active_sequence_model.current_edit_frame_changed.disconnect()
            except TypeError: pass
            try: self.active_sequence_model.properties_changed.disconnect()
            except TypeError: pass
            try: self.active_sequence_model.playback_state_changed.disconnect()
            except TypeError: pass

            self.active_sequence_model.frames_changed.connect(self._update_animator_ui_for_current_sequence)
            self.active_sequence_model.frame_content_updated.connect(self.on_animator_model_frame_content_updated)
            self.active_sequence_model.current_edit_frame_changed.connect(self.on_animator_model_edit_frame_changed)
            self.active_sequence_model.properties_changed.connect(self._update_animator_ui_for_current_sequence_properties)
            self.active_sequence_model.playback_state_changed.connect(self.on_animator_model_playback_state_changed)

    def _on_global_play_pause_action_triggered(self):
        """ Handles the global play/pause action (e.g., Spacebar). """
        if not self.akai_controller.is_connected() or not self.active_sequence_model or self.active_sequence_model.get_frame_count() == 0:
            self.status_bar.showMessage("Cannot play/pause: No sequence loaded or device not connected.", 2000)
            return
        
        if self.is_screen_sampling_active and self.screen_sampler_ui_manager:
            # If sampling is active, pressing space probably shouldn't control animator
            # Or, it could be a global "stop everything" action. For now, let's prioritize sampler.
            self.status_bar.showMessage("Screen sampler is active. Play/Pause disabled for animator.", 2000)
            return

        if self.active_sequence_model.get_is_playing():
            self.on_animator_pause() # Uses existing pause logic
        else:
            self.on_animator_play()  # Uses existing play logic

    def on_animator_copy_frames(self):
        if not self.active_sequence_model or not self.sequence_timeline_widget:
            self.status_bar.showMessage("Cannot copy: No active sequence or timeline.", 2000)
            return

        selected_indices = self.sequence_timeline_widget.get_selected_item_indices() # We'll need to add this method to SequenceTimelineWidget
        if not selected_indices:
            self.status_bar.showMessage("No frames selected to copy.", 2000)
            return

        self.frame_clipboard.clear()
        copied_frames_count = 0
        for index in sorted(selected_indices): # Process in order
            frame_obj = self.active_sequence_model.get_frame_object(index)
            if frame_obj:
                # Create a deep copy for the clipboard
                copied_colors = list(frame_obj.get_all_colors()) # Get a copy of the color list
                self.frame_clipboard.append(AnimationFrame(colors=copied_colors))
                copied_frames_count += 1
        
        if copied_frames_count > 0:
            self.status_bar.showMessage(f"{copied_frames_count} frame(s) copied to clipboard.", 2000)
        else:
            self.status_bar.showMessage("Could not copy selected frames.", 2000)
        self._update_animator_controls_enabled_state() # To update paste action enabled state

    def on_animator_cut_frames(self):
        if not self.active_sequence_model or not self.sequence_timeline_widget:
            self.status_bar.showMessage("Cannot cut: No active sequence or timeline.", 2000)
            return

        selected_indices = self.sequence_timeline_widget.get_selected_item_indices()
        if not selected_indices:
            self.status_bar.showMessage("No frames selected to cut.", 2000)
            return
        
        self.stop_current_animation() # Stop playback before modifying frames

        # Copy first
        self.frame_clipboard.clear()
        copied_frames_count = 0
        # Sort indices for copying, as the model expects sorted indices if it were to use them directly
        # For cutting, we just need to iterate them to get objects, then delete them.
        for index in sorted(selected_indices):
            frame_obj = self.active_sequence_model.get_frame_object(index)
            if frame_obj:
                copied_colors = list(frame_obj.get_all_colors())
                self.frame_clipboard.append(AnimationFrame(colors=copied_colors))
                copied_frames_count += 1
        
        if copied_frames_count == 0:
            self.status_bar.showMessage("Could not prepare frames for cutting.", 2000)
            self._update_animator_controls_enabled_state()
            return

        # Then delete (SequenceModel.delete_frames_at_indices handles sorting internally for deletion)
        if self.active_sequence_model.delete_frames_at_indices(selected_indices):
            self.status_bar.showMessage(f"{copied_frames_count} frame(s) cut to clipboard.", 2000)
        else:
            # Deletion failed, clear clipboard as cut was not complete
            self.frame_clipboard.clear()
            self.status_bar.showMessage("Error cutting frames (deletion part failed).", 3000)
            
        self._update_animator_controls_enabled_state() # Updates timeline, edit frame, and paste action

    def on_animator_paste_frames(self):
        if not self.active_sequence_model:
            self.status_bar.showMessage("Cannot paste: No active sequence.", 2000)
            return
        if not self.frame_clipboard:
            self.status_bar.showMessage("Clipboard is empty. Nothing to paste.", 2000)
            return

        self.stop_current_animation()

        # Determine insertion point: after current selection, or at end if no selection
        # Or if multiple items selected, after the last selected item.
        insertion_index = -1
        selected_indices = []
        if self.sequence_timeline_widget:
            selected_indices = self.sequence_timeline_widget.get_selected_item_indices()

        if selected_indices:
            insertion_index = max(selected_indices) + 1
        elif self.active_sequence_model.get_current_edit_frame_index() != -1:
            insertion_index = self.active_sequence_model.get_current_edit_frame_index() + 1
        else: # No selection, paste at the end
            insertion_index = self.active_sequence_model.get_frame_count()

        # Let SequenceModel handle the actual paste logic
        pasted_indices = self.active_sequence_model.paste_frames(self.frame_clipboard, at_index=insertion_index)

        if pasted_indices:
            self.status_bar.showMessage(f"{len(pasted_indices)} frame(s) pasted.", 2000)
            # MainWindow.on_animator_model_edit_frame_changed will be triggered by model,
            # which should update the grid and timeline selection.
            # We might want to explicitly select the newly pasted frames in the timeline here.
            if self.sequence_timeline_widget:
                 QTimer.singleShot(0, lambda: self.sequence_timeline_widget.select_items_by_indices(pasted_indices))

        else:
            self.status_bar.showMessage("Error pasting frames.", 3000)
        
        self._update_animator_controls_enabled_state() # Model changes will also trigger this via signals

    def on_animator_duplicate_selected_frames_generic(self):
        """Handles duplicate request, getting selection from timeline."""
        if not self.akai_controller.is_connected() or not self.active_sequence_model or not self.sequence_timeline_widget:
            self.status_bar.showMessage("Cannot duplicate: System not ready.", 2000)
            return
        if self.is_screen_sampling_active and self.screen_sampler_ui_manager:
            self.screen_sampler_ui_manager.force_disable_sampling_ui() # Stop sampling if active
        
        self.stop_current_animation()
        selected_indices = self.sequence_timeline_widget.get_selected_item_indices()
        if not selected_indices:
            self.status_bar.showMessage("No frames selected to duplicate.", 1500)
            return

        newly_created_indices = self.active_sequence_model.duplicate_frames_at_indices(selected_indices)
        if newly_created_indices:
            self.status_bar.showMessage(f"{len(newly_created_indices)} frame(s) duplicated.", 1500)
            # Model change should trigger UI update via signals, including selection of new frames.
            # If explicit selection is needed:
            QTimer.singleShot(0, lambda: self.sequence_timeline_widget.select_items_by_indices(newly_created_indices))
        else:
            self.status_bar.showMessage("Duplication failed or no valid frames selected.", 1500)
        # _update_animator_controls_enabled_state will be called via model signals

    def on_animator_delete_selected_frames_generic(self):
        """Handles delete request, getting selection from timeline."""
        if not self.akai_controller.is_connected() or not self.active_sequence_model or not self.sequence_timeline_widget:
            self.status_bar.showMessage("Cannot delete: System not ready.", 2000)
            return
        if self.is_screen_sampling_active and self.screen_sampler_ui_manager:
            self.screen_sampler_ui_manager.force_disable_sampling_ui()

        self.stop_current_animation()
        selected_indices = self.sequence_timeline_widget.get_selected_item_indices()
        if not selected_indices:
            self.status_bar.showMessage("No frames selected to delete.", 1500)
            return

        if self.active_sequence_model.delete_frames_at_indices(selected_indices):
            self.status_bar.showMessage(f"{len(selected_indices)} frame(s) delete_frames_at_indices.", 1500)
             # Model change should trigger UI update via signals.
        else:
            self.status_bar.showMessage("Deletion failed or no valid frames selected for deletion.", 1500)
        # _update_animator_controls_enabled_state will be called via model signals
    
    def on_animator_select_all_frames(self):
        """Handles select all request for the timeline."""
        if not self.active_sequence_model or not self.sequence_timeline_widget:
            return
        if self.is_screen_sampling_active: return # Don't interfere with sampler

        if self.active_sequence_model.get_frame_count() > 0:
            all_indices = list(range(self.active_sequence_model.get_frame_count()))
            self.sequence_timeline_widget.select_items_by_indices(all_indices)
            self.status_bar.showMessage(f"All {len(all_indices)} frames selected.", 1500)
        else:
            self.status_bar.showMessage("No frames to select.", 1500)
        self._update_animator_controls_enabled_state()


    # --- Modify existing generic handlers to use new selection method ---
    # The on_animator_delete_frame_action and on_animator_duplicate_frame_action methods
    # that took frame_index_override are now superseded by the generic versions above
    # that get selection directly from the timeline.
    # We can remove or comment out the older specific ones if they are no longer used
    # by context menus that pass specific indices. The timeline context menu was updated
    # to emit generic signals.

    # Example: Comment out old specific handlers if no longer directly called
    # def on_animator_delete_frame_action(self, frame_index_override: int = None):
    #     # ... (Old implementation) ... -> Now superseded by on_animator_delete_selected_frames_generic

    # def on_animator_duplicate_frame_action(self, frame_index_override: int = None):
    #     # ... (Old implementation) ... -> Now superseded by on_animator_duplicate_selected_frames_generic
### END OF NEW HANDLER METHODS in MainWindow ###


    # --- Screen Sampler Logic & Dialog Management ---
    def _populate_sampler_monitor_list_ui(self):
        if not self.screen_sampler_ui_manager:
            print("MainWindow: Sampler UI Manager not ready for monitor list.")
            return

        if not self.screen_sampler_monitor_list_cache:
            print("MainWindow: Fetching monitor list for sampler UI...")
            try:
                with mss.mss() as sct: 
                    self.screen_sampler_monitor_list_cache = ScreenSamplerCore.get_available_monitors(sct)
                print(f"MainWindow: Fetched {len(self.screen_sampler_monitor_list_cache)} monitors.")
                if not self.screen_sampler_monitor_list_cache: # Still empty after trying
                    self.status_bar.showMessage("No monitors detected for screen sampler.", 3000)
            except Exception as e:
                self.status_bar.showMessage(f"Error getting monitor list: {str(e)[:100]}", 5000)
                print(f"MainWindow: Error fetching monitor list: {e}")
                self.screen_sampler_monitor_list_cache = [] 
        
        self.screen_sampler_ui_manager.populate_monitors_combo_external(self.screen_sampler_monitor_list_cache)
        
        # If capture preview dialog exists and is visible, also update its monitor data
        if self.capture_preview_dialog and self.capture_preview_dialog.isVisible():
            current_target_id = self.current_sampler_params.get('monitor_id', 
                                 self.screen_sampler_monitor_list_cache[0]['id'] if self.screen_sampler_monitor_list_cache else 1)
            self.capture_preview_dialog.set_initial_monitor_data(self.screen_sampler_monitor_list_cache, current_target_id)

    def _show_capture_preview_dialog(self):
        if not self.screen_sampler_monitor_list_cache:
            self._populate_sampler_monitor_list_ui()
            if not self.screen_sampler_monitor_list_cache:
                QMessageBox.warning(self, "Monitor Information", "Cannot open sampler configuration: No monitor data available.")
                return

        if not self.capture_preview_dialog:
            self.capture_preview_dialog = CapturePreviewDialog(parent=self)
            self.capture_preview_dialog.sampling_parameters_changed.connect(self._handle_sampler_full_params_changed)
            self.capture_preview_dialog.dialog_closed.connect(self._on_capture_preview_dialog_closed)
        
        # Determine current target monitor ID for the dialog
        target_monitor_id_for_dialog = self.current_sampler_params.get('monitor_id', 1)
        if self.screen_sampler_ui_manager and self.screen_sampler_ui_manager.monitor_combo.count() > 0:
            current_ui_manager_mon_id = self.screen_sampler_ui_manager.monitor_combo.currentData()
            if current_ui_manager_mon_id is not None:
                target_monitor_id_for_dialog = current_ui_manager_mon_id
        
        # Prepare parameters to send to the dialog
        params_for_dialog = {'monitor_id': target_monitor_id_for_dialog} # Must include monitor_id
        
        monitor_key = self._generate_monitor_key(target_monitor_id_for_dialog)
        if monitor_key and monitor_key in self.sampler_monitor_prefs:
            saved_prefs = self.sampler_monitor_prefs[monitor_key]
            params_for_dialog['region_rect_percentage'] = saved_prefs.get('region_rect_percentage', 
                                                                          self.current_sampler_params['region_rect_percentage']) # Fallback to current if missing
            params_for_dialog['adjustments'] = saved_prefs.get('adjustments', 
                                                               self.current_sampler_params['adjustments']) # Fallback to current if missing
            print(f"MainWindow: Found saved prefs for monitor key {monitor_key} to send to dialog.")
        else:
            # No saved prefs for this monitor, send current_sampler_params which has dialog defaults
            # or could be params from a previously configured (but not yet saved for *this* key) monitor
            print(f"MainWindow: No saved prefs for monitor key {monitor_key}. Sending current_sampler_params to dialog.")
            params_for_dialog['region_rect_percentage'] = self.current_sampler_params['region_rect_percentage']
            params_for_dialog['adjustments'] = self.current_sampler_params['adjustments']

        # Pass all available monitor data and the specific parameters for the target monitor
        self.capture_preview_dialog.set_initial_monitor_data(
            self.screen_sampler_monitor_list_cache,
            target_monitor_id_for_dialog # Tell dialog which monitor it's focusing on
        )
        self.capture_preview_dialog.set_current_parameters_from_main(params_for_dialog)
        
        if self._last_processed_sampler_image:
            self.capture_preview_dialog.update_preview_image(self._last_processed_sampler_image)

        self.capture_preview_dialog.show()
        self.capture_preview_dialog.activateWindow()
        self.capture_preview_dialog.raise_()

    def _on_capture_preview_dialog_closed(self):
        # print("MainWindow: Capture Preview Dialog closed signal received.")
        # If we want to destroy the dialog instance:
         if self.capture_preview_dialog:
             self.capture_preview_dialog.deleteLater()
             self.capture_preview_dialog = None
        # For now, just keeping it hidden is fine, it will be reused.

    def _handle_sampler_basic_params_changed(self, enable_toggle: bool, basic_ui_params: dict):
        print(f"DEBUG MAINWINDOW: _handle_sampler_basic_params_changed called. enable_toggle: {enable_toggle}, basic_ui_params: {basic_ui_params}")
        """ UIManager changed: enable_toggle, monitor_id, frequency_ms """
        
        newly_selected_monitor_id = basic_ui_params.get('monitor_capture_id', self.current_sampler_params['monitor_id'])
        
        # If monitor selection changed via UIManager, try to load its specific prefs
        if newly_selected_monitor_id != self.current_sampler_params.get('monitor_id'):
            self.current_sampler_params['monitor_id'] = newly_selected_monitor_id
            monitor_key = self._generate_monitor_key(newly_selected_monitor_id)
            if monitor_key and monitor_key in self.sampler_monitor_prefs:
                saved_prefs = self.sampler_monitor_prefs[monitor_key]
                self.current_sampler_params['region_rect_percentage'] = saved_prefs.get('region_rect_percentage', self.current_sampler_params['region_rect_percentage'])
                self.current_sampler_params['adjustments'] = saved_prefs.get('adjustments', self.current_sampler_params['adjustments'])
                print(f"MainWindow: Loaded prefs for monitor {monitor_key} due to UIManager change.")
            else:
                # No saved prefs for this new monitor, reset to dialog's current defaults
                # These are already set in CapturePreviewDialog, so current_sampler_params' existing values
                # for region/adjustments (potentially from a *previous* monitor or initial defaults)
                # will be used, and then dialog will show its own defaults if it's opened.
                # This is okay, as opening dialog for this new monitor will establish its settings.
                # For now, just ensure 'monitor_id' is updated.
                # Let's reset region and adjustments to some base defaults for consistency when monitor changes and no prefs found.
                self.current_sampler_params['region_rect_percentage'] = {'x': 0.4, 'y': 0.4, 'width': 0.2, 'height': 0.2} # A safe default region
                self.current_sampler_params['adjustments'] = { # Dialog's current boosted defaults
                    'saturation': 2.0, 'contrast': 1.5, 
                    'brightness': 1.0, 'hue_shift': 0 
                }
                print(f"MainWindow: No saved prefs for new UIManager monitor {monitor_key}. Using dialog defaults.")

        self.current_sampler_params['frequency_ms'] = basic_ui_params.get('frequency_ms', self.current_sampler_params['frequency_ms'])
        
        # If dialog is open, sync its target monitor and tell it to use existing/loaded region/adjustments
        if self.capture_preview_dialog and self.capture_preview_dialog.isVisible():
            # We need to pass the potentially updated current_sampler_params to the dialog
            self.capture_preview_dialog.set_current_parameters_from_main(self.current_sampler_params)

        self._synchronize_and_control_sampler_thread(enable_toggle)

    def _handle_sampler_full_params_changed(self, full_dialog_params: dict):
        """ CapturePreviewDialog changed: monitor_id, region_rect_percentage, adjustments S/C/B/H """
        
        # Update MainWindow's central store of current parameters
        new_monitor_id = full_dialog_params.get('monitor_id', self.current_sampler_params['monitor_id'])
        self.current_sampler_params['monitor_id'] = new_monitor_id
        self.current_sampler_params['region_rect_percentage'] = full_dialog_params.get('region_rect_percentage', self.current_sampler_params['region_rect_percentage'])
        self.current_sampler_params['adjustments'] = full_dialog_params.get('adjustments', self.current_sampler_params['adjustments'])
        
        # Save these specific params for this monitor
        monitor_key = self._generate_monitor_key(new_monitor_id)
        if monitor_key:
            self.sampler_monitor_prefs[monitor_key] = {
                'region_rect_percentage': self.current_sampler_params['region_rect_percentage'].copy(),
                'adjustments': self.current_sampler_params['adjustments'].copy()
            }
            self._save_sampler_preferences() # Save immediately on change from dialog
            # print(f"MainWindow: Saved prefs for monitor key {monitor_key} after dialog change.")

        # Sync back to UIManager's monitor combo if it was changed via dialog
        if self.screen_sampler_ui_manager:
            self.screen_sampler_ui_manager.monitor_combo.blockSignals(True)
            idx = self.screen_sampler_ui_manager.monitor_combo.findData(self.current_sampler_params['monitor_id'])
            if idx != -1: self.screen_sampler_ui_manager.monitor_combo.setCurrentIndex(idx)
            self.screen_sampler_ui_manager.monitor_combo.blockSignals(False)
            # Frequency is not set by dialog, so no need to sync UIManager's frequency slider here.

        if self.is_screen_sampling_active: 
            self._synchronize_and_control_sampler_thread(True)

    def _synchronize_and_control_sampler_thread(self, should_be_enabled: bool):
        print(f"DEBUG: _synchronize_and_control_sampler_thread called with should_be_enabled: {should_be_enabled}")
        if not self.screen_sampler_thread:
            if should_be_enabled and self.screen_sampler_ui_manager: self.screen_sampler_ui_manager.force_disable_sampling_ui()
            self.status_bar.showMessage("Sampler thread error.", 3000); return

        if not self.akai_controller.is_connected() and should_be_enabled:
            if self.screen_sampler_ui_manager: self.screen_sampler_ui_manager.force_disable_sampling_ui()
            self.status_bar.showMessage("Connect device for sampling.", 3000); return

        if should_be_enabled:
            if not self.is_screen_sampling_active: # Transitioning to active
                # self.stop_current_animation() # This was here, might be too aggressive if sampler is just toggled
                self.is_screen_sampling_active = True
                print(f"DEBUG: Set self.is_screen_sampling_active = True")
            
            print(f"DEBUG: Calling screen_sampler_thread.start_sampling() with params: {self.current_sampler_params}")
            self.screen_sampler_thread.start_sampling(
                monitor_capture_id=self.current_sampler_params['monitor_id'],
                region_rect_percentage=self.current_sampler_params['region_rect_percentage'],
                frequency_ms=self.current_sampler_params['frequency_ms'],
                adjustments=self.current_sampler_params['adjustments']
            )
        else: 
            if self.is_screen_sampling_active: # Transitioning to inactive
                self.is_screen_sampling_active = False
                print(f"DEBUG: Set self.is_screen_sampling_active = False")
                if self.screen_sampler_thread.isRunning(): self.screen_sampler_thread.stop_sampling()
        
        self._update_animator_controls_enabled_state()

    def _handle_screen_sampled_colors_list(self, colors_list: list):
        # print(f"DEBUG: _handle_screen_sampled_colors_list called. self.is_recording_sampler: {self.is_recording_sampler}, Frame Count: {self.current_recording_frame_count}") # Can be very noisy
        if self.is_recording_sampler:  # Check if recording is active
            if self.current_recording_frame_count < self.MAX_RECORDING_FRAMES:
                # Convert RGB tuples to hex strings for storage
                # The incoming colors_list from thread is list of (r,g,b) tuples
                if colors_list and all(isinstance(c, tuple) and len(c) == 3 for c in colors_list):
                    hex_frame = [QColor(r, g, b).name() for r, g, b in colors_list]
                    self.recorded_sampler_frames.append(hex_frame)
                    self.current_recording_frame_count += 1
                    if self.recording_status_label:
                        self.recording_status_label.setText(f"REC🔴 {self.current_recording_frame_count}/{self.MAX_RECORDING_FRAMES}")
                else:
                    print("MainWindow Warning: Invalid data in colors_list during recording, frame skipped.")

            else:  # Max frames reached
                if self.is_recording_sampler:  # Ensure stop is only called once
                    self._stop_sampler_recording()
                    # self.status_bar.showMessage(f"Max recording frames ({self.MAX_RECORDING_FRAMES}) reached. Recording stopped.", 3000)
                    # Status bar message is now handled in _stop_sampler_recording
        # <<< END BLOCK FOR _handle_screen_sampled_colors_list MODIFICATION >>>
        if not self.is_screen_sampling_active or not self.akai_controller.is_connected():
            return
        
        if not colors_list or len(colors_list) != (ScreenSamplerCore.NUM_GRID_ROWS * ScreenSamplerCore.NUM_GRID_COLS):
            # print(f"MainWindow: Received invalid colors_list (len {len(colors_list) if colors_list else 0}). Skipping update.")
            # Optionally, clear pads or do nothing
            return

        hardware_batch_update = []
        gui_updates = []

        for i, color_tuple in enumerate(colors_list):
            if not (isinstance(color_tuple, tuple) and len(color_tuple) == 3):
                # print(f"MainWindow: Invalid color_tuple at index {i}: {color_tuple}")
                r, g, b = 0, 0, 0 # Default to black if data is malformed
            else:
                r, g, b = color_tuple
            
            row, col = divmod(i, ScreenSamplerCore.NUM_GRID_COLS) # Akai Fire is 4 rows, 16 cols per row for main pads
            
            # Prepare for hardware update
            hardware_batch_update.append((row, col, r, g, b))
            
            # Prepare for GUI update (can be done directly or batched if GUI update is slow)
            # For now, let's update GUI directly. If it causes lag, we can batch QSS updates.
            self.update_gui_pad_color(row, col, r, g, b) # update_gui_pad_color should be efficient enough

        if hardware_batch_update:
            self.akai_controller.set_multiple_pads_color(hardware_batch_update)

    def _handle_sampler_processed_image(self, pil_image: Image.Image):
        self._last_processed_sampler_image = pil_image 
        if self.capture_preview_dialog and self.capture_preview_dialog.isVisible():
            self.capture_preview_dialog.update_preview_image(pil_image)

    def _handle_screen_sampler_error(self, error_message: str):
        # ... (content as before)
        self.status_bar.showMessage(f"Sampler Error: {error_message}", 7000)
        if "FATAL: mss library init failed" in error_message and self.screen_sampler_ui_manager:
            self.screen_sampler_ui_manager.force_disable_sampling_ui()
            self.screen_sampler_ui_manager.setEnabled(False)
            if self.capture_preview_dialog: self.capture_preview_dialog.close()
            QMessageBox.critical(self, "Screen Sampler Critical Error", 
                                 "Failed to initialize screen capture library (mss).\n"
                                 "Screen sampling will be disabled. Please check console.")


    # --- Signal Handlers from Other Managers ---
    def _handle_final_color_selection_from_manager(self, color: QColor):
        # ... (content as before)
        self.selected_qcolor = color
        self.status_bar.showMessage(f"Active color: {color.name().upper()}", 3000)

    def _handle_paint_black_button(self):
        # ... (content as before, including sampler disable)
        if self.is_screen_sampling_active and self.screen_sampler_ui_manager:
            self.screen_sampler_ui_manager.force_disable_sampling_ui()
        black_color = QColor("black")
        self.selected_qcolor = black_color 
        if self.color_picker_manager: 
            self.color_picker_manager.set_current_selected_color(black_color, source="paint_black_button")
        self.status_bar.showMessage("Active color: Black (Off)", 2000)

    def _handle_apply_static_layout_data(self, colors_hex: list):
        # ... (content as before, including sampler disable)
        if not self.akai_controller.is_connected():
            self.status_bar.showMessage("Connect to device first.", 2000); return
        if self.is_screen_sampling_active and self.screen_sampler_ui_manager:
            self.screen_sampler_ui_manager.force_disable_sampling_ui()
        self.stop_current_animation()
        self.apply_colors_to_main_pad_grid(colors_hex, update_hw=True)
        if colors_hex and colors_hex[0] and self.color_picker_manager:
            first_color = QColor(colors_hex[0])
            if first_color.isValid():
                self.color_picker_manager.set_current_selected_color(first_color, source="static_layout_apply")

    def _provide_grid_colors_for_static_save(self):
        if self.static_layouts_manager:
            current_colors = self.get_current_main_pad_grid_colors()
            self.static_layouts_manager.save_layout_with_colors(current_colors)

### START OF METHOD MainWindow._handle_load_sequence_request ###
    def _handle_load_sequence_request(self, filepath: str):
        """Loads a sequence from the given filepath. Now updates new animator combo."""

        if self.active_sequence_model and \
           self.active_sequence_model.loaded_filepath and \
           os.path.normpath(self.active_sequence_model.loaded_filepath) == os.path.normpath(filepath):
            print(f"MainWindow: Sequence '{os.path.basename(filepath)}' is already active. Load skipped.")
            # Ensure the new combo reflects this if called externally
            if self.animator_sequence_selection_combo:
                 self.animator_refresh_sequences_list_and_select(
                    self.active_sequence_model.name,
                    self.active_sequence_model.loaded_filepath_type_id if hasattr(self.active_sequence_model, 'loaded_filepath_type_id') else "user" # Assuming a way to get type
                )
            return

        if self.active_sequence_model and self.active_sequence_model.is_modified:
            reply = QMessageBox.question(self, "Unsaved Changes",
                                         "The current animation has unsaved changes. Save now before loading a new sequence?",
                                         QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel,
                                         QMessageBox.StandardButton.Cancel)
            if reply == QMessageBox.StandardButton.Save:
                # Use the new save handler
                self._on_animator_save_sequence_as_button_clicked() 
                if self.active_sequence_model.is_modified: 
                    self.status_bar.showMessage("Load cancelled due to unsaved changes.", 3000)
                    # Revert combo if it changed prematurely (more complex if old combo is gone)
                    # For now, rely on user re-selecting if save is cancelled.
                    return 
            elif reply == QMessageBox.StandardButton.Cancel:
                self.status_bar.showMessage("Load cancelled.", 2000)
                return
        
        if self.is_screen_sampling_active and self.screen_sampler_ui_manager:
            self.screen_sampler_ui_manager.force_disable_sampling_ui()
            
        self.stop_current_animation()
        new_model_instance = SequenceModel()
        
        if new_model_instance.load_from_file(filepath):
            self.active_sequence_model = new_model_instance
            # Store type_id if possible (e.g., by parsing filepath or if SequenceFileManager passed it)
            # For simplicity, we'll try to guess from path for now
            path_lower = filepath.lower()
            type_id_guess = "user"
            if "prefab" in path_lower: type_id_guess = "prefab"
            elif "sampler_recordings" in path_lower: type_id_guess = "sampler"
            
            # A better way would be if SequenceModel stored this upon load or if the loading mechanism provided it.
            # For now, we add a temporary attribute for this refresh call:
            self.active_sequence_model.loaded_filepath_type_id = type_id_guess


            self._connect_signals_for_active_sequence_model()
            self._update_animator_ui_for_current_sequence() 
            self.status_bar.showMessage(f"Sequence '{self.active_sequence_model.name}' loaded.", 2000)
            
            self.animator_refresh_sequences_list_and_select(
                self.active_sequence_model.name, 
                type_id_guess
            )
        else:
            QMessageBox.warning(self, "Load Error", f"Failed to load sequence from: {os.path.basename(filepath)}")
            self.animator_refresh_sequences_list_and_select() # Refresh to previous or default state
        
        self._update_animator_controls_enabled_state()
### END OF METHOD MainWindow._handle_load_sequence_request ###

    def _handle_save_sequence_as_request(self):
        # ... (content as before)
        if not self.active_sequence_model or self.active_sequence_model.get_frame_count() == 0:
            QMessageBox.information(self, "Save Sequence", "Cannot save: No frames in current sequence.")
            return
        save_info = self.sequence_file_manager.get_save_path_for_new_sequence(self.active_sequence_model.name)
        if save_info:
            filepath, raw_name = save_info
            self.active_sequence_model.set_name(raw_name) 
            if self.active_sequence_model.save_to_file(filepath):
                self.status_bar.showMessage(f"Sequence '{raw_name}' saved.", 2000)
                self.sequence_file_manager.refresh_sequences_list_and_select(raw_name, False)
            else:
                QMessageBox.critical(self, "Save Error", f"Could not save sequence to '{filepath}'.")
        self._update_animator_controls_enabled_state()

### START OF METHOD MainWindow._handle_delete_sequence_request ###
    def _handle_delete_sequence_request(self, display_name: str, filepath: str, type_id: str): # Added type_id
        try:
            if os.path.exists(filepath):
                os.remove(filepath)
                self.status_bar.showMessage(f"Sequence '{display_name}' deleted.", 2000)
            
                # If the deleted sequence was the active one, create a new blank sequence
                if self.active_sequence_model and \
                   self.active_sequence_model.loaded_filepath and \
                   os.path.normpath(self.active_sequence_model.loaded_filepath) == os.path.normpath(filepath):
                    self.new_sequence(prompt_save=False) 
            
            # Refresh the (new) animator sequence list combobox
                self.animator_refresh_sequences_list_and_select()
            else:
                QMessageBox.warning(self, "Delete Error", "Sequence file not found on disk for deletion.")
            self.animator_refresh_sequences_list_and_select() # Still refresh if file was already gone
        except Exception as e:
            QMessageBox.critical(self, "Delete Error", f"Could not delete sequence file: {e}")
    
        self._update_animator_controls_enabled_state()
### END OF METHOD MainWindow._handle_delete_sequence_request ###

    # --- Drag Drawing, Pad Interaction ---
    def mousePressEvent(self, event: QMouseEvent):
        # ... (content as before, including sampler disable)
        super().mousePressEvent(event) 
        if event.button() == Qt.MouseButton.LeftButton:
            self.is_drawing_with_left_button_down = True 
            global_pos = event.globalPosition().toPoint()
            if self.pad_grid_frame.rect().contains(self.pad_grid_frame.mapFromGlobal(global_pos)):
                pos_in_grid_frame = self.pad_grid_frame.mapFromGlobal(global_pos)
                child_widget = self.pad_grid_frame.childAt(pos_in_grid_frame)
                if isinstance(child_widget, PadButton):
                    if self.is_screen_sampling_active and self.screen_sampler_ui_manager:
                        self.screen_sampler_ui_manager.force_disable_sampling_ui()
                    self._last_painted_pad_on_drag = (child_widget.row, child_widget.col)
                    self.apply_paint_to_pad(child_widget.row, child_widget.col, update_model=True)
                    event.accept()

    def mouseMoveEvent(self, event: QMouseEvent):
        # ... (content as before, including sampler disable)
        super().mouseMoveEvent(event)
        if self.is_drawing_with_left_button_down and (event.buttons() & Qt.MouseButton.LeftButton):
            global_pos = event.globalPosition().toPoint()
            if self.pad_grid_frame.rect().contains(self.pad_grid_frame.mapFromGlobal(global_pos)):
                pos_in_grid_frame = self.pad_grid_frame.mapFromGlobal(global_pos)
                child_widget = self.pad_grid_frame.childAt(pos_in_grid_frame)
                if isinstance(child_widget, PadButton):
                    current_drag_pad = (child_widget.row, child_widget.col)
                    if current_drag_pad != self._last_painted_pad_on_drag:
                        if self.is_screen_sampling_active and self.screen_sampler_ui_manager:
                            self.screen_sampler_ui_manager.force_disable_sampling_ui()
                        self.apply_paint_to_pad(child_widget.row, child_widget.col, update_model=True)
                        self._last_painted_pad_on_drag = current_drag_pad
                    event.accept()

    def mouseReleaseEvent(self, event: QMouseEvent):
        # ... (content as before)
        super().mouseReleaseEvent(event)
        if event.button() == Qt.MouseButton.LeftButton:
            self.is_drawing_with_left_button_down = False
            self._last_painted_pad_on_drag = None

    def handle_pad_press_for_drawing(self, row, col):
        # ... (content as before, including sampler disable)
        if self.is_screen_sampling_active and self.screen_sampler_ui_manager:
            self.screen_sampler_ui_manager.force_disable_sampling_ui()
        self.is_drawing_with_left_button_down = True 
        self._last_painted_pad_on_drag = (row, col)
        self.apply_paint_to_pad(row, col, update_model=True)

    def apply_paint_to_pad(self, row, col, update_model=False):
        # ... (content as before, including sampler disable)
        if not self.akai_controller.is_connected(): return
        if self.is_screen_sampling_active and self.screen_sampler_ui_manager:
             self.screen_sampler_ui_manager.force_disable_sampling_ui()
        r, g, b, _ = self.selected_qcolor.getRgb()
        self.akai_controller.set_pad_color(row, col, r, g, b)
        self.update_gui_pad_color(row, col, r, g, b)
        if update_model and self.active_sequence_model and \
           self.active_sequence_model.get_current_edit_frame_index() != -1:
            pad_index = row * 16 + col
            self.active_sequence_model.update_pad_in_current_edit_frame(pad_index, self.selected_qcolor.name())
    
    def show_pad_context_menu(self, pad_button_widget: PadButton, row: int, col: int, local_pos_to_button: QPoint):
        # ... (content as before with corrected global_pos)
        menu = QMenu(self)
        action_set_off = QAction("Set Pad to Black (Off)", self)
        action_set_off.triggered.connect(lambda: self.set_single_pad_black_and_update_model(row, col))
        menu.addAction(action_set_off)
        global_pos = pad_button_widget.mapToGlobal(local_pos_to_button)
        menu.exec(global_pos)

    def set_single_pad_black_and_update_model(self, row, col):
        # ... (content as before, including sampler disable)
        if not self.akai_controller.is_connected(): return
        if self.is_screen_sampling_active and self.screen_sampler_ui_manager:
            self.screen_sampler_ui_manager.force_disable_sampling_ui()
        black_color = QColor("black")
        self.akai_controller.set_pad_color(row, col, 0,0,0)
        self.update_gui_pad_color(row, col, 0,0,0)
        if self.active_sequence_model and \
           self.active_sequence_model.get_current_edit_frame_index() != -1:
            pad_index = row * 16 + col
            self.active_sequence_model.update_pad_in_current_edit_frame(pad_index, black_color.name())
        self.status_bar.showMessage(f"Pad ({row+1},{col+1}) set to Off.", 1500)

    def update_gui_pad_color(self, row: int, col: int, r_val: int, g_val: int, b_val: int):
        # ... (content as before)
        button = self.pad_buttons.get((row, col))
        if button:
            current_color = QColor(r_val, g_val, b_val)
            style_parts = ["border-radius:2px;"]
            is_off = (r_val == 0 and g_val == 0 and b_val == 0)
            if is_off:
                style_parts.append("background-color: #1C1C1C; border: 1px solid #404040; color: transparent;")
                hover_border_color = "#666666"
            else:
                style_parts.append(f"background-color: {current_color.name()};")
                border_color_dark = current_color.darker(110).name(); border_color_light = current_color.lighter(110).name()
                style_parts.append(f"border: 1px solid qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 {border_color_dark}, stop:1 {border_color_light});")
                luminance = 0.299 * r_val + 0.587 * g_val + 0.114 * b_val
                text_color = "#E0E0E0" if luminance < 128 else "#1C1C1C"
                style_parts.append(f"color: {text_color};"); hover_border_color = text_color
            final_style = f"QPushButton#PadButton {{{';'.join(style_parts)}}}" \
                          f"QPushButton#PadButton:hover {{border: 1px solid {hover_border_color};}}"
            button.setStyleSheet(final_style)

    def get_current_main_pad_grid_colors(self) -> list:
        # ... (content as before)
        colors_hex = []
        for r_idx in range(4):
            for c_idx in range(16):
                button = self.pad_buttons.get((r_idx, c_idx))
                hex_color_str = QColor("black").name()
                if button:
                    style = button.styleSheet()
                    try:
                        if "background-color:" in style:
                            bg_part = style.split("background-color:")[1].split(";")[0].strip()
                            temp_color = QColor(bg_part)
                            if temp_color.isValid(): hex_color_str = temp_color.name()
                    except Exception: pass 
                colors_hex.append(hex_color_str)
        return colors_hex
    
    def apply_colors_to_main_pad_grid(self, colors_hex: list, update_hw=True):
        if not colors_hex or len(colors_hex) != 64:
            self.clear_main_pad_grid_ui(update_hw=update_hw); return
        hardware_batch_update = []
        for i, hex_color_str in enumerate(colors_hex):
            row, col = divmod(i, 16)
            color = QColor(hex_color_str if hex_color_str else "#000000")
            if not color.isValid(): color = QColor("black")
            self.update_gui_pad_color(row, col, color.red(), color.green(), color.blue())
            if update_hw: hardware_batch_update.append((row, col, color.red(), color.green(), color.blue()))
        if update_hw and self.akai_controller.is_connected() and hardware_batch_update:
            self.akai_controller.set_multiple_pads_color(hardware_batch_update)

    def clear_main_pad_grid_ui(self, update_hw=True):
        blank_colors_hex = [QColor("black").name()] * 64
        self.apply_colors_to_main_pad_grid(blank_colors_hex, update_hw=update_hw)

    def clear_all_hardware_and_gui_pads(self):
        if not self.akai_controller.is_connected():
            self.status_bar.showMessage("Connect to device first.", 2000); return
        if self.is_screen_sampling_active and self.screen_sampler_ui_manager:
            self.screen_sampler_ui_manager.force_disable_sampling_ui() # This triggers sampler stop via signals
        self.stop_current_animation()
        blank_colors_hex = [QColor("black").name()] * 64
        self.apply_colors_to_main_pad_grid(blank_colors_hex, update_hw=True)
        if self.active_sequence_model:
            current_frame_obj = self.active_sequence_model.get_current_edit_frame_object()
            if current_frame_obj:
                self.active_sequence_model._push_undo_state()
                for i in range(64): current_frame_obj.set_pad_color(i, QColor("black").name())
                self.active_sequence_model.frame_content_updated.emit(
                    self.active_sequence_model.get_current_edit_frame_index())
        self.status_bar.showMessage("All device pads and current view cleared.", 2000)

    # --- Animator Methods ---
    def stop_current_animation(self):
        if self.playback_timer.isActive(): self.playback_timer.stop()
        if self.active_sequence_model: self.active_sequence_model.stop_playback()
        # UI update for play button is handled by model's playback_state_changed signal

### START OF METHOD MainWindow._update_animator_ui_for_current_sequence ###
    def _update_animator_ui_for_current_sequence(self):
        # This method is called when frames are added/deleted or when a new sequence is loaded.
        # It updates the timeline display and the speed controls.
        if self.active_sequence_model and self.sequence_timeline_widget and self.sequence_controls_widget:
            all_frames_colors = [] 
            if self.active_sequence_model: # Ensure model exists
                for i in range(self.active_sequence_model.get_frame_count()):
                    frame_data = self.active_sequence_model.get_frame_colors(i)
                    if frame_data: 
                        all_frames_colors.append(frame_data)
                    else: 
                        # Fallback for safety, though get_frame_colors should return valid list or None
                        all_frames_colors.append([QColor("black").name()] * 64) 
            
            current_edit_idx = -1
            current_playback_idx = -1
            if self.active_sequence_model: # Check again before accessing model properties
                current_edit_idx = self.active_sequence_model.get_current_edit_frame_index()
                if self.active_sequence_model.get_is_playing():
                    current_playback_idx = self.active_sequence_model.get_current_playback_frame_index()

            self.sequence_timeline_widget.update_frames_display(
                all_frames_colors,
                current_edit_idx,
                current_playback_idx
            )
            
            # Update speed/delay display from model
            self.sequence_controls_widget.set_frame_delay_ui(self.active_sequence_model.frame_delay_ms)
        
        # Always update general control states
        self._update_animator_controls_enabled_state()
### END OF METHOD MainWindow._update_animator_ui_for_current_sequence ###


### START OF METHOD MainWindow._update_animator_ui_for_current_sequence_properties ###
    def _update_animator_ui_for_current_sequence_properties(self):
        if self.active_sequence_model and self.sequence_controls_widget:
            self.sequence_controls_widget.set_frame_delay_ui(self.active_sequence_model.frame_delay_ms)
        
        # Update the NEW animator sequence combo
        if self.animator_sequence_selection_combo and self.active_sequence_model:
            type_id_guess = "user" # Default
            if self.active_sequence_model.loaded_filepath:
                path_lower = self.active_sequence_model.loaded_filepath.lower()
                if "prefab" in path_lower: type_id_guess = "prefab"
                elif "sampler_recordings" in path_lower: type_id_guess = "sampler"
            
            self.animator_refresh_sequences_list_and_select(
                self.active_sequence_model.name, 
                type_id_guess
            )
### END OF METHOD MainWindow._update_animator_ui_for_current_sequence_properties ###


### START OF METHOD MainWindow._update_animator_controls_enabled_state (FIX UnboundLocalError) ###
    def _update_animator_controls_enabled_state(self):
        is_connected = self.akai_controller.is_connected()
        can_interact_directly_with_animator = is_connected and not self.is_screen_sampling_active

        has_frames = False
        num_selected_frames = 0
        can_undo, can_redo = False, False
        can_operate_on_selection = False # <<< INITIALIZE TO A DEFAULT VALUE

        if self.active_sequence_model:
            has_frames = self.active_sequence_model.get_frame_count() > 0
            if self.sequence_timeline_widget: 
                num_selected_frames = len(self.sequence_timeline_widget.get_selected_item_indices())
            can_undo = bool(self.active_sequence_model._undo_stack)
            can_redo = bool(self.active_sequence_model._redo_stack)
            # Now define/update it based on current state if model exists
            can_operate_on_selection = can_interact_directly_with_animator and num_selected_frames > 0 and has_frames

        clipboard_has_content = bool(self.frame_clipboard)
        
        # --- Integrated Animator File Management Button States ---
        is_valid_combo_item_selected_for_load = False
        can_delete_selected_combo_item = False

        if self.animator_sequence_selection_combo: 
            self.animator_sequence_selection_combo.setEnabled(
                can_interact_directly_with_animator and self.animator_sequence_selection_combo.count() > 1
            )
            current_combo_idx = self.animator_sequence_selection_combo.currentIndex()
            current_combo_text = self.animator_sequence_selection_combo.itemText(current_combo_idx)
            item_data = self.animator_sequence_selection_combo.itemData(current_combo_idx)
            if current_combo_idx > 0 and \
               current_combo_text != "No sequences found" and \
               item_data and isinstance(item_data, dict) and "path" in item_data:
                is_valid_combo_item_selected_for_load = True
                if item_data.get("type") in ["user", "sampler"]:
                    can_delete_selected_combo_item = True
        
        if self.animator_load_sequence_button:
            self.animator_load_sequence_button.setEnabled(
                can_interact_directly_with_animator and is_valid_combo_item_selected_for_load
            )
        if self.animator_delete_sequence_button:
            self.animator_delete_sequence_button.setEnabled(
                can_interact_directly_with_animator and can_delete_selected_combo_item
            )
        if self.animator_new_sequence_button: 
            self.animator_new_sequence_button.setEnabled(can_interact_directly_with_animator)
        if self.new_sequence_action: 
            self.new_sequence_action.setEnabled(can_interact_directly_with_animator)
        if self.animator_save_as_button: 
            self.animator_save_as_button.setEnabled(can_interact_directly_with_animator and has_frames)
        if self.save_sequence_as_action: 
            self.save_sequence_as_action.setEnabled(can_interact_directly_with_animator and has_frames)
        # ---

        if self.sequence_controls_widget:
            self.sequence_controls_widget.set_controls_enabled_state(
                enabled=can_interact_directly_with_animator, 
                frame_selected=(num_selected_frames > 0),
                has_frames=has_frames,
                clipboard_has_content=clipboard_has_content
            )
        
        if self.sequence_timeline_widget:
            self.sequence_timeline_widget.setEnabled(can_interact_directly_with_animator)
        
        if self.undo_action: self.undo_action.setEnabled(can_interact_directly_with_animator and can_undo)
        if self.redo_action: self.redo_action.setEnabled(can_interact_directly_with_animator and can_redo)
        
        # can_operate_on_selection is now guaranteed to be defined
        if self.copy_action: self.copy_action.setEnabled(can_operate_on_selection)
        if self.cut_action: self.cut_action.setEnabled(can_operate_on_selection)
        if self.delete_action: self.delete_action.setEnabled(can_operate_on_selection) # For the QAction
        
        if self.paste_action: self.paste_action.setEnabled(can_interact_directly_with_animator and clipboard_has_content)
        if self.duplicate_action: self.duplicate_action.setEnabled(can_operate_on_selection) # For the QAction
        
        if self.play_pause_action:
            self.play_pause_action.setEnabled(is_connected and has_frames and not self.is_screen_sampling_active)

        self.pad_grid_frame.setEnabled(can_interact_directly_with_animator)
        if self.clear_all_button: self.clear_all_button.setEnabled(can_interact_directly_with_animator)
        if self.color_button_off: self.color_button_off.setEnabled(can_interact_directly_with_animator)
        
        if self.color_picker_manager: self.color_picker_manager.set_enabled(can_interact_directly_with_animator)
        if self.static_layouts_manager: self.static_layouts_manager.set_enabled_state(can_interact_directly_with_animator)
        
        if self.screen_sampler_ui_manager:
            self.screen_sampler_ui_manager.set_overall_enabled_state(is_connected)

        if hasattr(self, 'sampler_recording_group_box_ref') and self.sampler_recording_group_box_ref:
            self.sampler_recording_group_box_ref.setEnabled(is_connected)
### END OF METHOD MainWindow._update_animator_controls_enabled_state (FIX UnboundLocalError) ###

    def on_animator_frame_selected_in_timeline(self, frame_index: int):
        if self.is_screen_sampling_active: return 
        if self.active_sequence_model: self.active_sequence_model.set_current_edit_frame_index(frame_index)

    def on_animator_model_edit_frame_changed(self, frame_index: int):
        if self.is_screen_sampling_active: return 
        if self.active_sequence_model and self.active_sequence_model.get_is_playing(): self.on_animator_pause()
        if self.sequence_timeline_widget: self.sequence_timeline_widget.set_selected_frame_by_index(frame_index)
        colors_hex = None
        if self.active_sequence_model and frame_index != -1:
            colors_hex = self.active_sequence_model.get_frame_colors(frame_index)
        if colors_hex: self.apply_colors_to_main_pad_grid(colors_hex, update_hw=True)
        else: self.clear_main_pad_grid_ui(update_hw=True)
        self._update_animator_controls_enabled_state()

    def on_animator_model_frame_content_updated(self, frame_index: int):
        if self.is_screen_sampling_active: return 
        if self.active_sequence_model and frame_index == self.active_sequence_model.get_current_edit_frame_index():
            colors_hex = self.active_sequence_model.get_frame_colors(frame_index)
            if colors_hex: self.apply_colors_to_main_pad_grid(colors_hex, update_hw=True)
            else: self.clear_main_pad_grid_ui(update_hw=True)

    def on_animator_model_playback_state_changed(self, is_playing: bool):
        if self.sequence_controls_widget: self.sequence_controls_widget.update_playback_button_state(is_playing)
        self.status_bar.showMessage("Sequence playing..." if is_playing else "Sequence stopped/paused.", 0 if is_playing else 3000)
        self._update_animator_controls_enabled_state()

    def on_animator_add_frame_action_from_timeline_menu(self, frame_type: str):
        if self.is_screen_sampling_active and self.screen_sampler_ui_manager:
            self.screen_sampler_ui_manager.force_disable_sampling_ui()
        insert_at_index = None # ... (rest of method as before)
        if self.active_sequence_model:
            current_idx = self.active_sequence_model.get_current_edit_frame_index()
            if current_idx != -1: insert_at_index = current_idx + 1
        self.on_animator_add_frame_action_from_controls(frame_type, at_index=insert_at_index)

    def on_animator_add_frame_action_from_controls(self, frame_type: str, at_index: int = None):
        if not self.akai_controller.is_connected() or not self.active_sequence_model: return
        if self.is_screen_sampling_active and self.screen_sampler_ui_manager:
            self.screen_sampler_ui_manager.force_disable_sampling_ui()
        self.stop_current_animation() # ... (rest of method as before)
        if frame_type == "snapshot":
            self.active_sequence_model.add_frame_snapshot(self.get_current_main_pad_grid_colors(), at_index)
            self.status_bar.showMessage("Snapshot frame added.", 1500)
        elif frame_type == "blank":
            self.active_sequence_model.add_blank_frame(at_index)
            self.status_bar.showMessage("Blank frame added.", 1500)

    def on_animator_delete_selected_frame_from_controls(self): self.on_animator_delete_frame_action()
    # def on_animator_delete_frame_action(self, frame_index_override: int = None):
    #    if not self.akai_controller.is_connected() or not self.active_sequence_model: return
    #    if self.is_screen_sampling_active and self.screen_sampler_ui_manager:
    #        self.screen_sampler_ui_manager.force_disable_sampling_ui()
        # ... (rest of method content as before)
    #    self.stop_current_animation()
    ##    original_edit_index = self.active_sequence_model.get_current_edit_frame_index()
    #    target_delete_index = frame_index_override if frame_index_override is not None else original_edit_index
    #    if 0 <= target_delete_index < self.active_sequence_model.get_frame_count():
     #       if target_delete_index != original_edit_index: self.active_sequence_model.set_current_edit_frame_index(target_delete_index)
    #        if self.active_sequence_model.delete_selected_frame(): self.status_bar.showMessage("Frame deleted.", 1500)
    #        if frame_index_override is not None and frame_index_override != original_edit_index:
    #            adjusted_original_index = original_edit_index if original_edit_index < target_delete_index else original_edit_index -1
    #            if 0 <= adjusted_original_index < self.active_sequence_model.get_frame_count():
    #                self.active_sequence_model.set_current_edit_frame_index(adjusted_original_index)
    #    else: self.status_bar.showMessage("No frame selected or invalid index to delete.", 1500)


    def on_animator_duplicate_selected_frame_from_controls(self): self.on_animator_duplicate_frame_action()
    def on_animator_duplicate_frame_action(self, frame_index_override: int = None):
        if not self.akai_controller.is_connected() or not self.active_sequence_model: return
        if self.is_screen_sampling_active and self.screen_sampler_ui_manager:
            self.screen_sampler_ui_manager.force_disable_sampling_ui()
        # ... (rest of method content as before)
        self.stop_current_animation()
        original_edit_index = self.active_sequence_model.get_current_edit_frame_index()
        target_duplicate_index = frame_index_override if frame_index_override is not None else original_edit_index
        if 0 <= target_duplicate_index < self.active_sequence_model.get_frame_count():
            if target_duplicate_index != original_edit_index: self.active_sequence_model.set_current_edit_frame_index(target_duplicate_index)
            new_frame_idx = self.active_sequence_model.duplicate_selected_frame()
            if new_frame_idx != -1: self.status_bar.showMessage(f"Frame duplicated to position {new_frame_idx + 1}.", 1500)
            if frame_index_override is not None and frame_index_override != original_edit_index:
                adjusted_original_index = original_edit_index
                if original_edit_index >= new_frame_idx : adjusted_original_index +=1
                if 0 <= adjusted_original_index < self.active_sequence_model.get_frame_count():
                    self.active_sequence_model.set_current_edit_frame_index(adjusted_original_index)
        else: self.status_bar.showMessage("No frame selected or invalid index to duplicate.", 1500)


    def on_animator_navigate_first(self): # ... (all nav methods check is_screen_sampling_active)
        if self.is_screen_sampling_active: return
        if self.active_sequence_model and self.active_sequence_model.get_frame_count() > 0: self.active_sequence_model.set_current_edit_frame_index(0)
    def on_animator_navigate_prev(self):
        if self.is_screen_sampling_active: return; # ... (rest as before)
        if not self.active_sequence_model or self.active_sequence_model.get_frame_count() == 0: return
        idx, count = self.active_sequence_model.get_current_edit_frame_index(), self.active_sequence_model.get_frame_count()
        self.active_sequence_model.set_current_edit_frame_index(count - 1 if idx <= 0 else idx - 1)
    def on_animator_navigate_next(self):
        if self.is_screen_sampling_active: return; # ... (rest as before)
        if not self.active_sequence_model or self.active_sequence_model.get_frame_count() == 0: return
        idx, count = self.active_sequence_model.get_current_edit_frame_index(), self.active_sequence_model.get_frame_count()
        self.active_sequence_model.set_current_edit_frame_index(0 if idx >= count - 1 else idx + 1)
    def on_animator_navigate_last(self):
        if self.is_screen_sampling_active: return; # ... (rest as before)
        if self.active_sequence_model:
            count = self.active_sequence_model.get_frame_count()
            if count > 0: self.active_sequence_model.set_current_edit_frame_index(count - 1)

    def on_animator_play(self):
        if not self.akai_controller.is_connected() or not self.active_sequence_model or self.active_sequence_model.get_frame_count() == 0:
            if self.sequence_controls_widget: self.sequence_controls_widget.update_playback_button_state(False)
            self.status_bar.showMessage("Cannot play: No frames or not connected.", 2000); return
        if self.is_screen_sampling_active and self.screen_sampler_ui_manager:
            self.screen_sampler_ui_manager.force_disable_sampling_ui() # This triggers sampler stop
        start_idx = self.active_sequence_model.get_current_edit_frame_index()
        if start_idx == -1 or start_idx >= self.active_sequence_model.get_frame_count(): start_idx = 0
        self.active_sequence_model._playback_frame_index = start_idx 
        if self.active_sequence_model.start_playback(): self.playback_timer.start(self.active_sequence_model.frame_delay_ms)

    def on_animator_pause(self): # ... (content as before)
        if self.active_sequence_model: self.active_sequence_model.pause_playback()
        self.playback_timer.stop(); self.status_bar.showMessage("Sequence paused.", 3000)

    def on_animator_stop(self): # ... (content as before, respects is_screen_sampling_active for clear)
        self.stop_current_animation()
        if self.active_sequence_model:
            idx = self.active_sequence_model.get_current_edit_frame_index()
            if idx != -1: self.on_animator_model_edit_frame_changed(idx) 
            elif self.active_sequence_model.get_frame_count() > 0: self.on_animator_model_edit_frame_changed(0)
            elif not self.is_screen_sampling_active: self.clear_main_pad_grid_ui(update_hw=True)
        self.status_bar.showMessage("Sequence stopped.", 3000)


    def advance_and_play_next_frame(self):
        if not self.active_sequence_model or \
           not self.active_sequence_model.get_is_playing() or \
           not self.akai_controller.is_connected() or \
           self.is_screen_sampling_active: 
            self.stop_current_animation(); return
        # ... (rest of method as before) ...
        colors_hex = self.active_sequence_model.step_and_get_playback_frame_colors()
        if colors_hex:
            self.apply_colors_to_main_pad_grid(colors_hex, update_hw=True)
            all_frames_colors_for_timeline = []
            if self.active_sequence_model:
                for i in range(self.active_sequence_model.get_frame_count()):
                    frame_data = self.active_sequence_model.get_frame_colors(i)
                    if frame_data: all_frames_colors_for_timeline.append(frame_data)
                    else: all_frames_colors_for_timeline.append([QColor("black").name()] * 64)
            idx_just_played = self.active_sequence_model.get_current_playback_frame_index() -1 
            if idx_just_played < 0 and self.active_sequence_model.loop: 
                idx_just_played = self.active_sequence_model.get_frame_count() -1
            if 0 <= idx_just_played < self.active_sequence_model.get_frame_count() and self.sequence_timeline_widget :
                 self.sequence_timeline_widget.update_frames_display(
                    all_frames_colors_for_timeline, 
                    self.active_sequence_model.get_current_edit_frame_index(), 
                    idx_just_played )
        if not self.active_sequence_model.get_is_playing(): self.stop_current_animation() 

    def on_animator_frame_delay_changed(self, delay_ms: int): # ... (content as before)
        if self.active_sequence_model:
            self.active_sequence_model.set_frame_delay_ms(delay_ms)
            if self.playback_timer.isActive(): self.playback_timer.start(delay_ms)
            self.status_bar.showMessage(f"Frame delay set to {delay_ms} ms.", 1500)

    def on_animator_undo(self): # ... (checks is_screen_sampling_active)
        if self.is_screen_sampling_active: return
        if self.active_sequence_model and self.active_sequence_model.undo(): self.status_bar.showMessage("Undo.", 1500)
        else: self.status_bar.showMessage("Nothing to undo.", 1500)
        self._update_animator_controls_enabled_state()
    def on_animator_redo(self): # ... (checks is_screen_sampling_active)
        if self.is_screen_sampling_active: return
        if self.active_sequence_model and self.active_sequence_model.redo(): self.status_bar.showMessage("Redo.", 1500)
        else: self.status_bar.showMessage("Nothing to redo.", 1500)
        self._update_animator_controls_enabled_state()

### START OF METHOD MainWindow.new_sequence ###
    def new_sequence(self, prompt_save=True): 
        if not self.akai_controller.is_connected():
            self.status_bar.showMessage("Connect to device first.", 2000); return

        if prompt_save and self.active_sequence_model and self.active_sequence_model.is_modified:
            reply = QMessageBox.question(self, "Unsaved Changes",
                                         "The current animation has unsaved changes. Save now before creating a new sequence?",
                                         QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel,
                                         QMessageBox.StandardButton.Cancel)
            if reply == QMessageBox.StandardButton.Save:
                self._on_animator_save_sequence_as_button_clicked() # Use new save handler
                if self.active_sequence_model.is_modified: 
                    self.status_bar.showMessage("New sequence cancelled due to unsaved changes.", 3000)
                    return
            elif reply == QMessageBox.StandardButton.Cancel:
                self.status_bar.showMessage("New sequence cancelled.", 2000)
                return
        
        if self.is_screen_sampling_active and self.screen_sampler_ui_manager:
            self.screen_sampler_ui_manager.force_disable_sampling_ui()
        
        self.stop_current_animation()
        self.active_sequence_model = SequenceModel() 
        self.active_sequence_model.is_modified = False 
        self._connect_signals_for_active_sequence_model() 
        self._update_animator_ui_for_current_sequence() 
        
        if not self.is_screen_sampling_active:
            self.clear_main_pad_grid_ui(update_hw=True)
        
        self.status_bar.showMessage("New sequence created.", 2000)
        self.animator_refresh_sequences_list_and_select() # Refresh new combo to "--- Select Sequence ---"
        
        self._update_animator_controls_enabled_state()
### END OF METHOD MainWindow.new_sequence ###

    # --- MIDI Connection Management ---
    def populate_midi_ports(self): # ... (content as before) ...
        self.port_combo_direct_ref.blockSignals(True); self.port_combo_direct_ref.clear()
        ports = AkaiFireController.get_available_ports()
        if ports:
            self.port_combo_direct_ref.addItems(ports); self.port_combo_direct_ref.setEnabled(True)
            idx = next((i for i,n in enumerate(ports) if("fire"in n.lower()or"akai"in n.lower())and"midiin"not in n.lower()),-1)
            if idx != -1: self.port_combo_direct_ref.setCurrentIndex(idx)
            elif self.port_combo_direct_ref.count() > 0: self.port_combo_direct_ref.setCurrentIndex(0)
        else:
            self.port_combo_direct_ref.addItem("No MIDI output ports found"); self.port_combo_direct_ref.setEnabled(False)
        self.port_combo_direct_ref.blockSignals(False)
        self._on_port_combo_changed(self.port_combo_direct_ref.currentIndex())
        
    def toggle_connection(self): # ... (content as before) ...
        if self.akai_controller.is_connected(): self.akai_controller.disconnect()
        else:
            port = self.port_combo_direct_ref.currentText()
            if port and port != "No MIDI output ports found":
                if not self.akai_controller.connect(port): QMessageBox.warning(self, "Connection Failed", f"Could not connect to {port}.")
            else: self.status_bar.showMessage("Please select a valid MIDI port.", 3000)
        self.update_connection_status()
    
    def update_connection_status(self):
        """Update the connection status of the AKAI controller and related UI elements."""
        is_connected = self.akai_controller.is_connected()
        if self.connect_button_direct_ref:
            self.connect_button_direct_ref.setText("Disconnect" if is_connected else "Connect")
            if is_connected: self.connect_button_direct_ref.setEnabled(True)
            else: self._on_port_combo_changed(self.port_combo_direct_ref.currentIndex() if self.port_combo_direct_ref else -1)
        self.status_bar.showMessage(f"Connected to: {self.akai_controller.port_name_used}" if is_connected else "Disconnected.")
        if self.port_combo_direct_ref: self.port_combo_direct_ref.setEnabled(not is_connected)
        
        if self.screen_sampler_ui_manager:
            self.screen_sampler_ui_manager.set_overall_enabled_state(is_connected)
            if is_connected : # If just connected, ensure monitor list is populated for sampler UI
                self._populate_sampler_monitor_list_ui() 
            elif self.is_screen_sampling_active : # If disconnected while sampling
                self.screen_sampler_ui_manager.force_disable_sampling_ui() # This will stop thread via signals
        
        self._update_animator_controls_enabled_state() # This handles all other UI enable states
        if is_connected and self.connect_button_direct_ref : self.connect_button_direct_ref.setEnabled(True)

    def closeEvent(self, event):
        if self.capture_preview_dialog: self.capture_preview_dialog.close()
        self.stop_current_animation()
        if self.screen_sampler_thread and self.screen_sampler_thread.isRunning():
            print("MainWindow: Stopping screen sampler thread on close..."); self.screen_sampler_thread.stop_sampling()
            if not self.screen_sampler_thread.wait(1000): print("MainWindow: Screen sampler thread did not stop gracefully.")
        
        # Save color picker swatches (if you move its config saving here)
        # config_path_swatches = get_user_config_file_path("fire_controller_config.json") # Example
        # self.color_picker_manager.save_color_picker_swatches_to_config(config_path_swatches)
        # For now, assuming ColorPickerManager handles its own saving to its default path
        if self.color_picker_manager: 
            self.color_picker_manager.save_color_picker_swatches_to_config()  # No argument needed

        # NEW: Save sampler preferences on exit
        self._save_sampler_preferences()
        print("MainWindow: Saved sampler preferences on exit.")
        
        if self.akai_controller.is_connected(): self.akai_controller.disconnect()
        event.accept()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    # Application icon is set in fire_control_app.py
    # Stylesheet loading also moved to fire_control_app.py for consistency
    # This __main__ block assumes those are handled by the entry script.
    try:
        gui_dir_path = os.path.dirname(os.path.abspath(__file__)) 
        project_root_path = os.path.dirname(gui_dir_path) 
        style_sheet_path_abs = os.path.join(project_root_path, "resources", "styles", "style.qss")
        if os.path.exists(style_sheet_path_abs):
            with open(style_sheet_path_abs, "r") as f: app.setStyleSheet(f.read())
            print(f"INFO: MainWindow local test - Stylesheet '{style_sheet_path_abs}' loaded.")
        else: print(f"WARNING: MainWindow local test - Stylesheet '{style_sheet_path_abs}' not found.")
    except Exception as e: print(f"ERROR: MainWindow local test - Error loading stylesheet: {e}")

    main_win = MainWindow()
    main_win.show()
    sys.exit(app.exec())