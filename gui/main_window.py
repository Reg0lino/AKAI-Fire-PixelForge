# AKAI_Fire_RGB_Controller/gui/main_window.py
import sys
import json
import os
import glob
import re
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QComboBox, QLabel, QStatusBar, QGridLayout, QFrame,
    QLineEdit, QFormLayout, QGroupBox, QMenu, QSizePolicy,
    QInputDialog, QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal, QRegularExpression, QPoint, QTimer
from PyQt6.QtGui import QColor, QPalette, QRegularExpressionValidator, QAction, QMouseEvent, QKeySequence

# Assuming these are in the same 'gui' package or Python path is set up
from .hue_slider import HueSlider
from .sv_picker import SVPicker

# Project-level imports
from hardware.akai_fire_controller import AkaiFireController
from animator.model import SequenceModel # AnimationFrame is used internally by SequenceModel
from animator.timeline_widget import SequenceTimelineWidget
from animator.controls_widget import SequenceControlsWidget


# --- Constants ---
INITIAL_WINDOW_WIDTH = 1050
INITIAL_WINDOW_HEIGHT = 850
PAD_BUTTON_WIDTH = 40
PAD_BUTTON_HEIGHT = 50
PAD_GRID_SPACING = 3 # Spacing between pad buttons in the grid
CUSTOM_SWATCH_SIZE = 32 # For "My Colors" swatches

CONFIG_FILE_NAME = "fire_controller_config.json"
# Using os.path.join for robust path construction
PREFAB_STATIC_PRESETS_DIR = os.path.join("presets", "static", "prefab") # Corrected, was 'static'
USER_PRESETS_DIR = os.path.join("presets", "static", "user") # Corrected, was 'user'
PREFAB_SEQUENCES_DIR = os.path.join("presets", "sequences", "prefab")
USER_SEQUENCES_DIR = os.path.join("presets", "sequences", "user")


class PadButton(QPushButton):
    """Custom QPushButton for grid pads, emits signal for painting."""
    request_paint_on_press = pyqtSignal(int, int) # row, col

    def __init__(self, row, col, parent=None):
        super().__init__(parent)
        self.row = row
        self.col = col
        self.setObjectName("PadButton") # For QSS styling
        self.setFixedSize(PAD_BUTTON_WIDTH, PAD_BUTTON_HEIGHT)
        self.setCheckable(False) # Not a toggle button
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        # Initial style will be set by update_gui_pad_color

    def mousePressEvent(self, event: QMouseEvent):
        """Handles mouse press events for the pad button."""
        if event.button() == Qt.MouseButton.LeftButton:
            # Emit signal for drawing logic in MainWindow when left-clicked
            self.request_paint_on_press.emit(self.row, self.col)
        super().mousePressEvent(event) # Propagate event for other uses (like context menu)


class MainWindow(QMainWindow):
    """Main application window."""
    final_color_selected_signal = pyqtSignal(QColor) # Emitted when the color picker finalizes a color

    def __init__(self):
        super().__init__()
        self.setWindowTitle("AKAI Fire RGB Controller - Animator")
        self.setGeometry(100, 100, INITIAL_WINDOW_WIDTH, INITIAL_WINDOW_HEIGHT)

        # Hardware Controller
        self.akai_controller = AkaiFireController(auto_connect=False) # Auto-connect can be true if preferred
        self.pad_buttons = {} # Dict to store [ (row, col) : PadButton ]

        # Color Picker State (HSV is primary internal model)
        self._current_h_int = 0     # Hue: 0-359
        self._current_s_float = 1.0  # Saturation: 0.0-1.0
        self._current_v_float = 1.0  # Value: 0.0-1.0
        self.selected_qcolor = QColor.fromHsvF(self._current_h_int / 360.0, self._current_s_float, self._current_v_float)

        # UI Element References (initialized in init_ui)
        self.hue_slider_widget, self.sv_picker_widget = None, None
        self.r_input, self.g_input, self.b_input = None, None, None
        self.h_input, self.s_input, self.v_input = None, None, None
        self.hex_input_lineedit = None
        self.main_color_preview_swatch = None
        self.custom_swatch_buttons = []
        self.num_custom_swatches = 16
        self.swatches_per_row = 8
        self.add_cp_swatch_button = None # Reference to the "+ Add Current Color" button

        self._block_ui_updates = False # Flag to prevent signal recursion in color picker
        self.is_drawing_with_left_button_down = False # For drag-drawing on pad grid
        self._last_painted_pad_on_drag = None # Tracks the last pad painted during a drag

        # Static Presets UI
        self.static_presets_combo = None
        self.apply_layout_button, self.save_layout_button, self.delete_layout_button = None, None, None
        self.loaded_static_presets = {} # Stores loaded static preset data

        # Animator UI & Model
        self.sequence_timeline_widget = None
        self.sequence_controls_widget = None
        self.active_sequence_model = SequenceModel() # Start with a default empty sequence
        self.loaded_sequences = {} # Stores loaded sequence metadata {display_name: {path, type}}
        self.sequences_combo = None
        self.new_seq_button, self.save_seq_button, self.delete_seq_button = None, None, None

        # Animator Playback
        self.playback_timer = QTimer(self)
        self.playback_timer.timeout.connect(self.advance_and_play_next_frame)

        # Undo/Redo Actions
        self.undo_action, self.redo_action = None, None

        # Initialization
        self.ensure_user_dirs_exist()
        self.init_ui() # Create all UI elements
        
        self.update_connection_status() # Reflects initial disconnected state
        self.populate_midi_ports()      # Fill MIDI port combobox
        
        # Connect signals after UI is initialized
        self.final_color_selected_signal.connect(self.handle_final_color_selection)
        self._connect_animator_signals() # Connect animator model and widget signals
        self._create_edit_actions()      # Create Undo/Redo QActions

        # Load persistent data and initial states
        self.load_color_picker_swatches_from_config()
        self.load_all_static_pad_layouts()
        self.load_all_sequences()
        
        # Set initial UI states
        self._update_all_color_ui_elements(self.selected_qcolor, "init")
        self._update_animator_ui_for_current_sequence() # Update timeline, controls based on initial empty model
        self._update_animator_controls_enabled_state()  # Enable/disable animator controls

    def ensure_user_dirs_exist(self):
        """Creates necessary user preset directories if they don't exist."""
        # Get base path of the running script/executable
        # Using __file__ is more robust if this script is run directly or imported.
        # If running as part of a frozen app, sys.executable might be better.
        try:
            base_path = os.path.dirname(os.path.abspath(__file__)) # gui directory
            project_root = os.path.dirname(base_path) # AKAI_Fire_RGB_Controller directory
        except NameError: # __file__ is not defined (e.g. in interactive interpreter)
            project_root = os.path.dirname(os.path.abspath(sys.argv[0]))


        paths_to_ensure = [
            os.path.join(project_root, PREFAB_STATIC_PRESETS_DIR),
            os.path.join(project_root, USER_PRESETS_DIR),
            os.path.join(project_root, PREFAB_SEQUENCES_DIR),
            os.path.join(project_root, USER_SEQUENCES_DIR)
        ]
        for path in paths_to_ensure:
            if not os.path.exists(path):
                try:
                    os.makedirs(path, exist_ok=True)
                    # print(f"DEBUG: Created directory {path}")
                except Exception as e:
                    print(f"Warning: Could not create directory {path}: {e}")

    def init_ui(self):
        """Initializes the main UI layout and widgets."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_app_layout = QHBoxLayout(central_widget)
        main_app_layout.setSpacing(10) # Spacing between left and right panels

        # --- Left Panel (Pad Grid & Animator) ---
        left_panel = QWidget()
        left_panel_layout = QVBoxLayout(left_panel)
        left_panel_layout.setContentsMargins(0,0,0,0)
        left_panel_layout.setSpacing(10)

        # Pad Grid Section (top-centered)
        pad_grid_outer_container = QWidget() # Container to help with centering
        pad_grid_container_layout = QVBoxLayout(pad_grid_outer_container)
        pad_grid_container_layout.setContentsMargins(0,0,0,0)
        
        self.pad_grid_frame = QFrame()
        self.pad_grid_frame.setObjectName("PadGridFrame") # For potential QSS targeting
        pad_grid_layout = QGridLayout()
        pad_grid_layout.setSpacing(PAD_GRID_SPACING)
        # Make columns and rows non-stretchable initially
        for i in range(16): pad_grid_layout.setColumnStretch(i, 0)
        for i in range(4): pad_grid_layout.setRowStretch(i, 0)

        for r_idx in range(4): # Rows
            for c_idx in range(16): # Columns
                pad_button = PadButton(row=r_idx, col=c_idx)
                pad_button.request_paint_on_press.connect(self.handle_pad_press_for_drawing)
                # pad_button.clicked.connect(lambda checked=False, r=r_idx, c=c_idx: self.on_pad_single_clicked(r, c)) # Simple click
                pad_button.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
                pad_button.customContextMenuRequested.connect(
                    lambda pos, r=r_idx, c=c_idx: self.show_pad_context_menu(self.pad_buttons[(r,c)], r, c, pos))
                
                self.pad_buttons[(r_idx, c_idx)] = pad_button
                pad_grid_layout.addWidget(pad_button, r_idx, c_idx)
                self.update_gui_pad_color(r_idx, c_idx, 0,0,0) # Initialize to black

        self.pad_grid_frame.setLayout(pad_grid_layout)
        # Calculate fixed size for the grid frame based on content
        grid_width = (16 * PAD_BUTTON_WIDTH) + (15 * PAD_GRID_SPACING) + (2 * pad_grid_layout.contentsMargins().left()) # Add margins
        grid_height = (4 * PAD_BUTTON_HEIGHT) + (3 * PAD_GRID_SPACING) + (2 * pad_grid_layout.contentsMargins().top())
        self.pad_grid_frame.setFixedSize(grid_width, grid_height)
        
        pad_grid_container_layout.addWidget(self.pad_grid_frame, 0, Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)
        left_panel_layout.addWidget(pad_grid_outer_container)

        # Animator Section
        animator_group = QGroupBox("Animator Sequencer")
        animator_group_layout = QVBoxLayout(animator_group)
        self.sequence_timeline_widget = SequenceTimelineWidget()
        animator_group_layout.addWidget(self.sequence_timeline_widget)
        self.sequence_controls_widget = SequenceControlsWidget()
        animator_group_layout.addWidget(self.sequence_controls_widget)
        left_panel_layout.addWidget(animator_group)
        left_panel_layout.addStretch(1) # Push animator group up if space allows

        main_app_layout.addWidget(left_panel, 2) # Left panel takes 2/3 of space

        # --- Right Panel (Controls, Color Picker, Presets) ---
        controls_container = QWidget()
        controls_layout_main_v = QVBoxLayout(controls_container)
        controls_container.setMinimumWidth(420) # Ensure enough space for controls
        controls_container.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)

        # Connection Group
        connection_group = QGroupBox("MIDI Connection")
        connection_layout = QHBoxLayout(connection_group)
        self.port_combo = QComboBox()
        self.port_combo.setPlaceholderText("Select MIDI Port")
        self.connect_button = QPushButton("Connect")
        self.connect_button.clicked.connect(self.toggle_connection)
        connection_layout.addWidget(QLabel("Port:"))
        connection_layout.addWidget(self.port_combo, 1) # Combobox takes available space
        connection_layout.addWidget(self.connect_button)
        controls_layout_main_v.addWidget(connection_group)

        # Advanced Color Picker Group
        adv_color_picker_group = QGroupBox("Advanced Color Picker")
        adv_color_picker_layout = QHBoxLayout(adv_color_picker_group) # Main layout for this group
        
        self.sv_picker_widget = SVPicker()
        self.sv_picker_widget.setMinimumSize(150,150) # Ensure it's reasonably sized
        self.sv_picker_widget.sv_changed.connect(self.sv_picker_value_changed)
        adv_color_picker_layout.addWidget(self.sv_picker_widget, 1) # SV picker takes available space
        
        self.hue_slider_widget = HueSlider(orientation=Qt.Orientation.Vertical)
        self.hue_slider_widget.setMinimumWidth(35) # Fixed width for vertical slider
        self.hue_slider_widget.hue_changed.connect(self.hue_slider_value_changed)
        adv_color_picker_layout.addWidget(self.hue_slider_widget)
        controls_layout_main_v.addWidget(adv_color_picker_group)

        # Numeric Color Values & Preview Group
        numeric_preview_group = QGroupBox("Color Values & Preview")
        numeric_preview_layout = QGridLayout(numeric_preview_group)
        # HSV Inputs
        self.h_input = QLineEdit(); self.h_input.setValidator(QRegularExpressionValidator(QRegularExpression("[0-9]{1,3}"))); self.h_input.editingFinished.connect(self.hsv_inputs_edited)
        self.s_input = QLineEdit(); self.s_input.setValidator(QRegularExpressionValidator(QRegularExpression("[0-9]{1,3}"))); self.s_input.editingFinished.connect(self.hsv_inputs_edited)
        self.v_input = QLineEdit(); self.v_input.setValidator(QRegularExpressionValidator(QRegularExpression("[0-9]{1,3}"))); self.v_input.editingFinished.connect(self.hsv_inputs_edited)
        numeric_preview_layout.addWidget(QLabel("H (0-359):"),0,0); numeric_preview_layout.addWidget(self.h_input,0,1)
        numeric_preview_layout.addWidget(QLabel("S (0-100%):"),1,0); numeric_preview_layout.addWidget(self.s_input,1,1)
        numeric_preview_layout.addWidget(QLabel("V (0-100%):"),2,0); numeric_preview_layout.addWidget(self.v_input,2,1)
        # RGB Inputs
        self.r_input = QLineEdit(); self.r_input.setValidator(QRegularExpressionValidator(QRegularExpression("[0-9]{1,3}"))); self.r_input.editingFinished.connect(self.rgb_inputs_edited)
        self.g_input = QLineEdit(); self.g_input.setValidator(QRegularExpressionValidator(QRegularExpression("[0-9]{1,3}"))); self.g_input.editingFinished.connect(self.rgb_inputs_edited)
        self.b_input = QLineEdit(); self.b_input.setValidator(QRegularExpressionValidator(QRegularExpression("[0-9]{1,3}"))); self.b_input.editingFinished.connect(self.rgb_inputs_edited)
        numeric_preview_layout.addWidget(QLabel("R (0-255):"),0,2); numeric_preview_layout.addWidget(self.r_input,0,3)
        numeric_preview_layout.addWidget(QLabel("G (0-255):"),1,2); numeric_preview_layout.addWidget(self.g_input,1,3)
        numeric_preview_layout.addWidget(QLabel("B (0-255):"),2,2); numeric_preview_layout.addWidget(self.b_input,2,3)
        # HEX Input
        self.hex_input_lineedit = QLineEdit()
        hex_validator = QRegularExpressionValidator(QRegularExpression("#?[0-9A-Fa-f]{0,6}"))
        self.hex_input_lineedit.setValidator(hex_validator); self.hex_input_lineedit.setMaxLength(7)
        self.hex_input_lineedit.setPlaceholderText("#RRGGBB"); self.hex_input_lineedit.editingFinished.connect(self.hex_input_edited_handler)
        numeric_preview_layout.addWidget(QLabel("HEX:"),3,0); numeric_preview_layout.addWidget(self.hex_input_lineedit,3,1,1,3) # Span 3 columns
        # Main Color Preview Swatch
        self.main_color_preview_swatch = QLabel()
        self.main_color_preview_swatch.setMinimumHeight(40); self.main_color_preview_swatch.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.main_color_preview_swatch.setAutoFillBackground(True); self.main_color_preview_swatch.setObjectName("MainColorPreview") # For QSS
        numeric_preview_layout.addWidget(self.main_color_preview_swatch,4,0,1,4) # Span 4 columns
        controls_layout_main_v.addWidget(numeric_preview_group)

        # "My Colors" Custom Swatches Group
        my_colors_group = QGroupBox("My Colors")
        my_colors_layout = QVBoxLayout(my_colors_group)
        self.add_cp_swatch_button = QPushButton("💾 Add Current Color") # Using save icon
        self.add_cp_swatch_button.setToolTip("Save the current color to an empty swatch or the last one.")
        self.add_cp_swatch_button.clicked.connect(self.add_current_color_to_color_picker_swatches)
        my_colors_layout.addWidget(self.add_cp_swatch_button,0,Qt.AlignmentFlag.AlignRight)
        
        custom_swatches_grid_widget = QWidget() # Container for the grid
        custom_swatches_grid_layout = QGridLayout(custom_swatches_grid_widget)
        custom_swatches_grid_layout.setSpacing(3)
        custom_swatches_grid_layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        for i in range(self.num_custom_swatches):
            # Using QPushButton for better hover/click feedback and context menu
            swatch_button = QPushButton() 
            swatch_button.setFixedSize(CUSTOM_SWATCH_SIZE, CUSTOM_SWATCH_SIZE)
            swatch_button.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
            swatch_button.setObjectName(f"CustomSwatchButton_{i}") # Unique name for potential individual QSS
            swatch_button.setProperty("isEmpty", True) # Custom property for styling
            swatch_button.clicked.connect(lambda checked=False, idx=i: self.apply_color_picker_swatch(idx))
            swatch_button.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
            swatch_button.customContextMenuRequested.connect(lambda pos, button_idx=i: self.show_color_picker_swatch_context_menu(self.custom_swatch_buttons[button_idx], button_idx, pos))
            self.custom_swatch_buttons.append(swatch_button)
            r, c = divmod(i, self.swatches_per_row)
            custom_swatches_grid_layout.addWidget(swatch_button, r, c)
        # Ensure columns don't stretch unnecessarily
        for c_idx in range(self.swatches_per_row): custom_swatches_grid_layout.setColumnStretch(c_idx,0)
        custom_swatches_grid_layout.setColumnStretch(self.swatches_per_row,1) # Allow stretch after last column
        my_colors_layout.addWidget(custom_swatches_grid_widget)
        my_colors_layout.addStretch(1) # Push swatches up
        controls_layout_main_v.addWidget(my_colors_group)

        # Static Pad Layouts Group
        static_presets_group = QGroupBox("Static Pad Layouts")
        static_presets_layout = QVBoxLayout(static_presets_group)
        self.static_presets_combo = QComboBox()
        static_presets_layout.addWidget(self.static_presets_combo)
        preset_buttons_layout = QHBoxLayout()
        self.apply_layout_button = QPushButton("Apply Layout"); self.apply_layout_button.clicked.connect(self.apply_selected_static_pad_layout)
        self.save_layout_button = QPushButton("Save Current As..."); self.save_layout_button.clicked.connect(self.save_current_layout_as_user_pad_layout)
        self.delete_layout_button = QPushButton("Delete Layout"); self.delete_layout_button.clicked.connect(self.delete_selected_user_pad_layout)
        preset_buttons_layout.addWidget(self.apply_layout_button); preset_buttons_layout.addWidget(self.save_layout_button); preset_buttons_layout.addWidget(self.delete_layout_button)
        static_presets_layout.addLayout(preset_buttons_layout)
        controls_layout_main_v.addWidget(static_presets_group)

        # Animator Sequences Group
        sequences_group = QGroupBox("Animator Sequences")
        sequences_layout_v = QVBoxLayout(sequences_group)
        self.sequences_combo = QComboBox()
        self.sequences_combo.currentIndexChanged.connect(self.on_selected_sequence_changed)
        sequences_layout_v.addWidget(self.sequences_combo)
        seq_manage_layout_h = QHBoxLayout()
        self.new_seq_button = QPushButton("✨ New Sequence"); self.new_seq_button.clicked.connect(self.new_sequence)
        self.save_seq_button = QPushButton("💾 Save Seq As..."); self.save_seq_button.clicked.connect(self.save_current_sequence_as)
        self.delete_seq_button = QPushButton("🗑️ Delete Seq"); self.delete_seq_button.clicked.connect(self.delete_selected_sequence)
        seq_manage_layout_h.addWidget(self.new_seq_button); seq_manage_layout_h.addWidget(self.save_seq_button); seq_manage_layout_h.addWidget(self.delete_seq_button)
        sequences_layout_v.addLayout(seq_manage_layout_h)
        controls_layout_main_v.addWidget(sequences_group)

        # Tool Buttons (Quick Color, Clear All)
        tool_buttons_layout = QHBoxLayout()
        self.color_button_off = QPushButton("Paint: Black (Off)")
        self.color_button_off.setToolTip("Set current painting color to Black (Off)")
        self.color_button_off.clicked.connect(lambda: self.final_color_selected_signal.emit(QColor("black")))
        tool_buttons_layout.addWidget(self.color_button_off)
        self.clear_all_button = QPushButton("Clear Device Pads")
        self.clear_all_button.setToolTip("Set all hardware pads to Black (Off) and clear current GUI/Frame.")
        self.clear_all_button.clicked.connect(self.clear_all_hardware_and_gui_pads)
        tool_buttons_layout.addLayout(tool_buttons_layout)

        controls_layout_main_v.addStretch(1) # Push all control groups to the top
        main_app_layout.addWidget(controls_container, 1) # Right panel takes 1/3 of space

        # Status Bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready. Please connect to AKAI Fire.")

    def _connect_animator_signals(self):
        """Connect signals for animator components and the active sequence model."""
        # Timeline Widget Signals
        self.sequence_timeline_widget.frame_selected.connect(self.on_animator_frame_selected_in_timeline)
        self.sequence_timeline_widget.add_frame_action_triggered.connect(self.on_animator_add_frame_action_from_timeline_menu)
        # Corrected: Connect to the generic duplicate/delete handlers
        self.sequence_timeline_widget.duplicate_frame_action_triggered.connect(self.on_animator_duplicate_frame_action) 
        self.sequence_timeline_widget.delete_frame_action_triggered.connect(self.on_animator_delete_frame_action)
        self.sequence_timeline_widget.insert_blank_frame_before_action_triggered.connect(
            lambda index: self.on_animator_add_frame_action_from_controls("blank", at_index=index)
        )
        self.sequence_timeline_widget.insert_blank_frame_after_action_triggered.connect(
            lambda index: self.on_animator_add_frame_action_from_controls("blank", at_index=index + 1) # Insert after current
        )

        # Controls Widget Signals
        self.sequence_controls_widget.add_frame_requested.connect(self.on_animator_add_frame_action_from_controls)
        self.sequence_controls_widget.delete_selected_frame_requested.connect(self.on_animator_delete_selected_frame_from_controls)
        self.sequence_controls_widget.duplicate_selected_frame_requested.connect(self.on_animator_duplicate_selected_frame_from_controls)
        self.sequence_controls_widget.navigate_first_requested.connect(self.on_animator_navigate_first)
        self.sequence_controls_widget.navigate_prev_requested.connect(self.on_animator_navigate_prev)
        self.sequence_controls_widget.navigate_next_requested.connect(self.on_animator_navigate_next)
        self.sequence_controls_widget.navigate_last_requested.connect(self.on_animator_navigate_last)
        self.sequence_controls_widget.play_requested.connect(self.on_animator_play)
        self.sequence_controls_widget.pause_requested.connect(self.on_animator_pause)
        self.sequence_controls_widget.stop_requested.connect(self.on_animator_stop)
        self.sequence_controls_widget.frame_delay_changed.connect(self.on_animator_frame_delay_changed)

        # Connect signals for the initial active_sequence_model
        self._connect_signals_for_active_sequence_model()

    def _connect_signals_for_active_sequence_model(self):
        """Connects signals for the *current* active_sequence_model.
           Call this whenever self.active_sequence_model is replaced.
        """
        # It's good practice to disconnect old signals if the model instance can change,
        # but if we always create a new model instance and assign it,
        # the old one might get garbage collected along with its connections if not referenced elsewhere.
        # For simplicity here, we assume self.active_sequence_model is the single source of truth.
        if self.active_sequence_model:
            # Disconnect any previous connections to be safe, though often not strictly necessary
            # if the old model is truly gone. This is more robust.
            try: self.active_sequence_model.frames_changed.disconnect(self._update_animator_ui_for_current_sequence)
            except TypeError: pass # Signal was not connected
            try: self.active_sequence_model.frame_content_updated.disconnect(self.on_animator_model_frame_content_updated)
            except TypeError: pass
            try: self.active_sequence_model.current_edit_frame_changed.disconnect(self.on_animator_model_edit_frame_changed)
            except TypeError: pass
            try: self.active_sequence_model.properties_changed.disconnect(self._update_animator_ui_for_current_sequence_properties)
            except TypeError: pass
            try: self.active_sequence_model.playback_state_changed.disconnect(self.on_animator_model_playback_state_changed)
            except TypeError: pass


            # Connect new signals
            self.active_sequence_model.frames_changed.connect(self._update_animator_ui_for_current_sequence)
            self.active_sequence_model.frame_content_updated.connect(self.on_animator_model_frame_content_updated)
            self.active_sequence_model.current_edit_frame_changed.connect(self.on_animator_model_edit_frame_changed)
            self.active_sequence_model.properties_changed.connect(self._update_animator_ui_for_current_sequence_properties)
            self.active_sequence_model.playback_state_changed.connect(self.on_animator_model_playback_state_changed)


    def _create_edit_actions(self):
        """Creates Undo and Redo QActions and adds them to the main window."""
        self.undo_action = QAction("Undo Sequence Edit", self)
        self.undo_action.setShortcut(QKeySequence.StandardKey.Undo)
        self.undo_action.setToolTip(f"Undo Sequence Change ({QKeySequence(QKeySequence.StandardKey.Undo).toString(QKeySequence.SequenceFormat.NativeText)})")
        self.undo_action.triggered.connect(self.on_animator_undo)
        self.addAction(self.undo_action) # Add to window for shortcut to work globally

        self.redo_action = QAction("Redo Sequence Edit", self)
        self.redo_action.setShortcut(QKeySequence.StandardKey.Redo)
        self.redo_action.setToolTip(f"Redo Sequence Change ({QKeySequence(QKeySequence.StandardKey.Redo).toString(QKeySequence.SequenceFormat.NativeText)})")
        self.redo_action.triggered.connect(self.on_animator_redo)
        self.addAction(self.redo_action)

    # --- Drag Drawing Logic on Pad Grid ---
    def mousePressEvent(self, event: QMouseEvent):
        """Handles mouse press for initiating drag-drawing on the pad grid."""
        super().mousePressEvent(event) # Call super first
        if event.button() == Qt.MouseButton.LeftButton:
            # Check if the press is within the pad_grid_frame
            global_pos = event.globalPosition().toPoint()
            pos_in_grid_frame = self.pad_grid_frame.mapFromGlobal(global_pos)
            
            if self.pad_grid_frame.rect().contains(pos_in_grid_frame):
                child_widget = self.pad_grid_frame.childAt(pos_in_grid_frame)
                if isinstance(child_widget, PadButton):
                    self.is_drawing_with_left_button_down = True
                    self._last_painted_pad_on_drag = (child_widget.row, child_widget.col)
                    self.apply_paint_to_pad(child_widget.row, child_widget.col, update_model=True)
                    event.accept() # Consume event if handled by grid
                    return
        self.is_drawing_with_left_button_down = False # Reset if not on grid

    def mouseMoveEvent(self, event: QMouseEvent):
        """Handles mouse move for drag-drawing on the pad grid."""
        super().mouseMoveEvent(event)
        if self.is_drawing_with_left_button_down and (event.buttons() & Qt.MouseButton.LeftButton):
            global_pos = event.globalPosition().toPoint()
            pos_in_grid_frame = self.pad_grid_frame.mapFromGlobal(global_pos)

            if self.pad_grid_frame.rect().contains(pos_in_grid_frame):
                child_widget = self.pad_grid_frame.childAt(pos_in_grid_frame)
                if isinstance(child_widget, PadButton):
                    current_drag_pad = (child_widget.row, child_widget.col)
                    if current_drag_pad != self._last_painted_pad_on_drag:
                        self.apply_paint_to_pad(child_widget.row, child_widget.col, update_model=True)
                        self._last_painted_pad_on_drag = current_drag_pad
                    event.accept()

    def mouseReleaseEvent(self, event: QMouseEvent):
        """Handles mouse release to stop drag-drawing."""
        super().mouseReleaseEvent(event)
        if event.button() == Qt.MouseButton.LeftButton:
            self.is_drawing_with_left_button_down = False
            self._last_painted_pad_on_drag = None

    def handle_pad_press_for_drawing(self, row, col):
        """Slot connected to PadButton's request_paint_on_press signal."""
        # This is an alternative to handling mousePressEvent directly in MainWindow
        # if PadButton consumes the event.
        self.is_drawing_with_left_button_down = True 
        self._last_painted_pad_on_drag = (row, col)
        self.apply_paint_to_pad(row, col, update_model=True)

    def apply_paint_to_pad(self, row, col, update_model=False):
        """Applies the selected_qcolor to a pad (GUI, Hardware, Model)."""
        if not self.akai_controller.is_connected(): # Don't paint if not connected
            # self.status_bar.showMessage("Connect to device to paint pads.", 1500)
            return

        r, g, b, _ = self.selected_qcolor.getRgb()
        
        # Update Hardware (if connected)
        self.akai_controller.set_pad_color(row, col, r, g, b)
        
        # Update GUI
        self.update_gui_pad_color(row, col, r, g, b)
        
        # Update Animator Model (if applicable)
        if update_model and self.active_sequence_model and \
           self.active_sequence_model.get_current_edit_frame_index() != -1:
            pad_index = row * 16 + col
            # Ensure color is passed as hex string to model
            self.active_sequence_model.update_pad_in_current_edit_frame(pad_index, self.selected_qcolor.name())

    # def on_pad_single_clicked(self, row, col):
    #     """Handles a simple click event on a pad (if not drag-painting)."""
    #     # This might be redundant if request_paint_on_press handles the primary action.
    #     # Could be used for alternative actions if needed.
    #     print(f"DEBUG: Pad ({row},{col}) single clicked.")
    #     pass

    # --- Color Model & UI Synchronization ---
    def _set_internal_hsv(self, h_param, s_param, v_param, source_widget_id=None):
        """
        Core HSV update logic. Normalizes inputs and updates the internal HSV state.
        Then updates self.selected_qcolor and all UI elements.
        h_param: Can be float (0.0-1.0 for QColor) or int/float (0-359 for display).
        s_param: Float (0.0-1.0).
        v_param: Float (0.0-1.0).
        """
        # print(f"DEBUG: _set_internal_hsv called by '{source_widget_id}'. Input H:{h_param}, S:{s_param}, V:{v_param}")

        h_display = 0  # For 0-359 display
        h_normalized_for_qcolor = 0.0 # For 0.0-1.0 QColor

        if isinstance(h_param, float) and -0.0001 <= h_param <= 1.0001: # Typically from QColor.getHsvF()
            h_normalized_for_qcolor = max(0.0, min(1.0, h_param))
            # Handle -0.0 from getHsvF for red
            h_display = int(round(h_normalized_for_qcolor * 359)) if h_normalized_for_qcolor > 0 else 0
            if h_normalized_for_qcolor == 0.0 and self._current_h_int !=0 and source_widget_id in ["rgb_inputs", "hex_input", "swatch_apply"]:
                 pass # If color is black/grey/white, hue can be 0, don't force it from a previous non-zero hue
            elif h_normalized_for_qcolor == 0.0 and self._current_h_int == 0:
                 pass # Already red/achromatic
            elif h_normalized_for_qcolor == 0.0: # True red from RGB/HEX, keep hue at 0
                 h_display = 0
        elif isinstance(h_param, (int, float)): # Typically from Hue Slider or H input field (0-359)
            h_display = int(max(0, min(359, float(h_param))))
            h_normalized_for_qcolor = h_display / 360.0 if h_display > 0 else 0.0 # Avoid 360/360=1.0 if h=0 is desired
            if h_display == 359 : h_normalized_for_qcolor = 359.0/360.0 # Max hue is slightly less than 1.0 for QColor
        else: # Fallback, should not happen with proper inputs
            h_display = self._current_h_int
            h_normalized_for_qcolor = self._current_h_int / 360.0

        s_float = float(max(0.0, min(1.0, s_param)))
        v_float = float(max(0.0, min(1.0, v_param)))

        # Update internal HSV state
        self._current_h_int = h_display
        self._current_s_float = s_float
        self._current_v_float = v_float
        
        # Create new QColor from normalized HSV
        new_qcolor = QColor.fromHsvF(h_normalized_for_qcolor, self._current_s_float, self._current_v_float)
        
        # print(f"DEBUG: _set_internal_hsv: Normalized H F:{h_normalized_for_qcolor:.3f}, S F:{self._current_s_float:.3f}, V F:{self._current_v_float:.3f}")
        # print(f"DEBUG: _set_internal_hsv: Display H:{self._current_h_int}, S %:{int(self._current_s_float*100)}, V %:{int(self._current_v_float*100)}")
        # print(f"DEBUG: _set_internal_hsv: New QColor: {new_qcolor.name()}, Prev QColor: {self.selected_qcolor.name()}")

        color_changed_from_model = (new_qcolor.rgb() != self.selected_qcolor.rgb()) # Compare RGB values for actual change
        
        self.selected_qcolor = new_qcolor
        self._update_all_color_ui_elements(self.selected_qcolor, source_widget_id)

        if color_changed_from_model or source_widget_id == "init": # Emit if color truly changed or during init
            self.final_color_selected_signal.emit(self.selected_qcolor)

    def _update_all_color_ui_elements(self, color: QColor, originating_widget_id=None):
        """Updates all color picker UI elements based on the provided QColor."""
        if self._block_ui_updates and originating_widget_id not in ["init", "final_selection_handler", "hsv_inputs_error", "rgb_inputs_error", "hex_input_error"]:
            print(f"DEBUG: _update_all_color_ui_elements blocked for source '{originating_widget_id}'")
            return
        
        # print(f"DEBUG: _update_all_color_ui_elements called by '{originating_widget_id}'. Updating with color: {color.name()}")
        self._block_ui_updates = True

        # Temporarily block signals from widgets we are about to update
        widgets_to_block_signals = []
        if originating_widget_id != "hue_slider": widgets_to_block_signals.append(self.hue_slider_widget)
        if originating_widget_id != "sv_picker": widgets_to_block_signals.append(self.sv_picker_widget)
        if originating_widget_id != "h_input": widgets_to_block_signals.append(self.h_input)
        if originating_widget_id != "s_input": widgets_to_block_signals.append(self.s_input)
        if originating_widget_id != "v_input": widgets_to_block_signals.append(self.v_input)
        if originating_widget_id != "rgb_inputs": widgets_to_block_signals.extend([self.r_input, self.g_input, self.b_input])
        if originating_widget_id != "hex_input": widgets_to_block_signals.append(self.hex_input_lineedit)
        
        for w in widgets_to_block_signals:
            if w: w.blockSignals(True)

        # Update UI elements
        # Use self._current_h_int, self._current_s_float, self._current_v_float for HSV elements
        # and color.red/green/blue/name for RGB/HEX elements
        if originating_widget_id != "hue_slider" and self.hue_slider_widget:
            self.hue_slider_widget.setHue(self._current_h_int)
        if originating_widget_id != "sv_picker" and self.sv_picker_widget:
            self.sv_picker_widget.setHue(self._current_h_int) # Update hue first
            self.sv_picker_widget.setSV(self._current_s_float, self._current_v_float)

        if originating_widget_id != "h_input" and self.h_input: self.h_input.setText(str(self._current_h_int))
        if originating_widget_id != "s_input" and self.s_input: self.s_input.setText(str(int(round(self._current_s_float * 100))))
        if originating_widget_id != "v_input" and self.v_input: self.v_input.setText(str(int(round(self._current_v_float * 100))))
        
        if originating_widget_id != "rgb_inputs" and self.r_input: # Check if r_input exists (it should)
            self.r_input.setText(str(color.red()))
            self.g_input.setText(str(color.green()))
            self.b_input.setText(str(color.blue()))
        
        if originating_widget_id != "hex_input" and self.hex_input_lineedit:
            self.hex_input_lineedit.setText(color.name().upper())

        self.update_main_color_preview_swatch_ui(color)

        # Unblock signals
        for w in widgets_to_block_signals:
            if w: w.blockSignals(False)
        
        self._block_ui_updates = False
        # print(f"DEBUG: _update_all_color_ui_elements finished for '{originating_widget_id}'.")


    def hue_slider_value_changed(self, hue_val_int): # hue_val_int is 0-359
        # print(f"DEBUG: hue_slider_value_changed: H_int={hue_val_int}")
        self._set_internal_hsv(hue_val_int, self._current_s_float, self._current_v_float, "hue_slider")

    def sv_picker_value_changed(self, saturation_float, value_float): # S, V are 0.0-1.0
        # print(f"DEBUG: sv_picker_value_changed: S_float={saturation_float:.3f}, V_float={value_float:.3f}")
        self._set_internal_hsv(self._current_h_int, saturation_float, value_float, "sv_picker")

    def hsv_inputs_edited(self):
        # print(f"DEBUG: hsv_inputs_edited triggered.")
        try:
            h = int(self.h_input.text())
            s_percent = int(self.s_input.text())
            v_percent = int(self.v_input.text())
            
            s_float = max(0.0, min(100.0, float(s_percent))) / 100.0
            v_float = max(0.0, min(100.0, float(v_percent))) / 100.0
            h_int = max(0, min(359, h))

            self._set_internal_hsv(h_int, s_float, v_float, "hsv_inputs")
        except ValueError:
            # print("DEBUG: ValueError in hsv_inputs_edited. Reverting UI.")
            self._update_all_color_ui_elements(self.selected_qcolor, "hsv_inputs_error") # Revert to last valid color

    def rgb_inputs_edited(self):
        # print(f"DEBUG: rgb_inputs_edited triggered.")
        try:
            r = int(self.r_input.text())
            g = int(self.g_input.text())
            b = int(self.b_input.text())

            color = QColor(max(0,min(255,r)), max(0,min(255,g)), max(0,min(255,b)))
            if color.isValid():
                # Convert RGB to HSV and then set internal state
                # QColor.getHsvF() returns h_float (0.0-1.0, -1 for achromatic)
                h_float, s_float, v_float, _ = color.getHsvF()
                if h_float < 0: h_float = 0.0 # If achromatic, hue is undefined (-1), treat as 0.0 for consistency
                
                print(f"DEBUG: rgb_inputs_edited: R:{r} G:{g} B:{b} -> H_F:{h_float:.3f} S_F:{s_float:.3f} V_F:{v_float:.3f}")
                self._set_internal_hsv(h_float, s_float, v_float, "rgb_inputs")
        except ValueError:
            print("DEBUG: ValueError in rgb_inputs_edited. Reverting UI.")
            self._update_all_color_ui_elements(self.selected_qcolor, "rgb_inputs_error")

    def hex_input_edited_handler(self):
        # print(f"DEBUG: hex_input_edited_handler triggered.")
        hex_text = self.hex_input_lineedit.text()
        if not hex_text.startswith("#"):
            hex_text = "#" + hex_text
        
        color = QColor(hex_text)
        if color.isValid():
            h_float, s_float, v_float, _ = color.getHsvF()
            if h_float < 0: h_float = 0.0
            
            # print(f"DEBUG: hex_input_edited_handler: HEX:{hex_text} -> H_F:{h_float:.3f} S_F:{s_float:.3f} V_F:{v_float:.3f}")
            self._set_internal_hsv(h_float, s_float, v_float, "hex_input")
        else:
            # print(f"DEBUG: Invalid HEX '{hex_text}'. Reverting UI.")
            self.status_bar.showMessage("Invalid HEX color format.", 2000)
            # Revert to last valid color in hex input
            self.hex_input_lineedit.setText(self.selected_qcolor.name().upper())


    def update_main_color_preview_swatch_ui(self, color: QColor):
        """Updates the main color preview swatch UI."""
        if self.main_color_preview_swatch:
            palette = self.main_color_preview_swatch.palette()
            palette.setColor(QPalette.ColorRole.Window, color)
            self.main_color_preview_swatch.setPalette(palette)
            
            # Determine good contrast text color
            luminance = 0.299 * color.red() + 0.587 * color.green() + 0.114 * color.blue()
            text_color_hex = "#1C1C1C" if luminance > 128 else "#E0E0E0"
            
            self.main_color_preview_swatch.setStyleSheet(
                f"background-color: {color.name()};"
                f"color: {text_color_hex};"
                f"border: 1px solid #777777;" # From QSS: QLabel#MainColorPreview
                f"border-radius: 3px;"       # From QSS
                f"font-weight: bold;"        # From QSS
            )
            self.main_color_preview_swatch.setText(color.name().upper())

    def handle_final_color_selection(self, color: QColor):
        """Slot for final_color_selected_signal. Ensures model and UI are truly in sync."""
        # print(f"DEBUG: handle_final_color_selection: Color: {color.name()}")
        
        # This can be simplified if _set_internal_hsv is robust
        # Re-affirm the color to ensure all components are perfectly aligned
        h_float, s_float, v_float, _ = color.getHsvF()
        if h_float < 0: h_float = 0.0 # Handle achromatic case

        # Check if internal HSV state already matches this color
        # This helps prevent redundant updates if called multiple times with same color
        current_color_from_hsv = QColor.fromHsvF(self._current_h_int / 360.0 if self._current_h_int > 0 else 0.0,
                                                  self._current_s_float, self._current_v_float)
        
        if current_color_from_hsv.rgb() != color.rgb():
            # print(f"DEBUG: handle_final_color_selection detected mismatch, calling _set_internal_hsv for {color.name()}")
            self._set_internal_hsv(h_float, s_float, v_float, "final_selection_handler")
        else:
            # print(f"DEBUG: handle_final_color_selection - color already matches internal HSV. No new update needed.")
            pass

        self.status_bar.showMessage(f"Active color: {color.name().upper()}", 3000)


    # --- Custom Color Picker Swatches Logic ---
    def add_current_color_to_color_picker_swatches(self):
        """Adds the current selected color to an empty swatch or overwrites the last one."""
        empty_idx = -1
        for i, button in enumerate(self.custom_swatch_buttons):
            if button.property("isEmpty"): # Check custom property
                empty_idx = i
                break
        
        if empty_idx != -1:
            self.save_color_to_color_picker_swatch(empty_idx, self.selected_qcolor)
            self.status_bar.showMessage(f"Color saved to swatch {empty_idx + 1}.", 2000)
        else:
            # Overwrite the last swatch if all are full
            self.save_color_to_color_picker_swatch(self.num_custom_swatches - 1, self.selected_qcolor)
            self.status_bar.showMessage("Color swatches full. Last swatch overwritten.", 2000)

    def apply_color_picker_swatch(self, index):
        """Applies the color from a clicked 'My Colors' swatch to the main color picker."""
        button = self.custom_swatch_buttons[index]
        if not button.property("isEmpty"):
            # Retrieve color from button's style or a stored property
            # For now, assume styleSheet has the color
            style = button.styleSheet()
            if "background-color:" in style:
                color_str = style.split("background-color:")[1].split(";")[0].strip()
                color = QColor(color_str)
                if color.isValid():
                    # print(f"DEBUG: apply_color_picker_swatch: Index {index}, Color {color.name()}")
                    h_float, s_float, v_float, _ = color.getHsvF()
                    if h_float < 0: h_float = 0.0 # Handle achromatic from swatch
                    
                    # Use source_widget_id to differentiate from other updates
                    self._set_internal_hsv(h_float, s_float, v_float, source_widget_id=f"swatch_apply_{index}")
                


    def show_color_picker_swatch_context_menu(self, button_widget, index, position):
        """Shows context menu for a 'My Colors' swatch."""
        menu = QMenu(self) # Parent to self (MainWindow)
        save_action = menu.addAction("💾 Save Current Color Here")
        clear_action = menu.addAction("❌ Clear This Swatch")
        clear_action.setEnabled(not button_widget.property("isEmpty")) # Only enable if not empty

        action = menu.exec(button_widget.mapToGlobal(position))

        if action == save_action:
            self.save_color_to_color_picker_swatch(index, self.selected_qcolor)
        elif action == clear_action:
            self.clear_color_picker_swatch(index)

    def _update_single_swatch_ui(self, index, color: QColor = None):
        """Helper to update a single swatch button's appearance."""
        button = self.custom_swatch_buttons[index]
        if color and color.isValid():
            button.setStyleSheet(f"background-color: {color.name()}; border: 1px solid #888888; border-radius: 2px;")
            button.setProperty("isEmpty", False)
            button.setToolTip(f"Color: {color.name().upper()}")
        else: # Empty swatch
            button.setStyleSheet(f"QPushButton#{button.objectName()} {{ background-color: #333333; border: 1px dashed #666666; border-radius: 2px; }}")
            button.setProperty("isEmpty", True)
            button.setToolTip("Empty swatch")


    def save_color_to_color_picker_swatch(self, index, color: QColor):
        """Saves a color to a specific swatch and updates config."""
        if 0 <= index < self.num_custom_swatches:
            self._update_single_swatch_ui(index, color)
            self.save_color_picker_swatches_to_config() # Persist changes

    def clear_color_picker_swatch(self, index):
        """Clears a specific swatch and updates config."""
        if 0 <= index < self.num_custom_swatches:
            self._update_single_swatch_ui(index, None) # None signifies empty
            self.save_color_picker_swatches_to_config() # Persist changes

    def update_all_color_picker_swatch_buttons_ui(self, colors_hex_list):
        """Updates all 'My Colors' swatch buttons from a list of hex color strings."""
        for i in range(self.num_custom_swatches):
            color = None
            if i < len(colors_hex_list) and colors_hex_list[i]:
                q_color_candidate = QColor(colors_hex_list[i])
                if q_color_candidate.isValid():
                    color = q_color_candidate
            self._update_single_swatch_ui(i, color)

    def get_config_path(self):
        """Gets the full path to the configuration file."""
        try:
            base_path = os.path.dirname(os.path.abspath(__file__)) # gui directory
            project_root = os.path.dirname(base_path)
        except NameError:
            project_root = os.path.dirname(os.path.abspath(sys.argv[0]))
        return os.path.join(project_root, CONFIG_FILE_NAME)

    def save_color_picker_swatches_to_config(self):
        """Saves the current 'My Colors' swatches to the config file."""
        swatch_colors_hex = []
        for button in self.custom_swatch_buttons:
            if not button.property("isEmpty"):
                style = button.styleSheet()
                if "background-color:" in style:
                    color_part = style.split("background-color:")[1].split(";")[0].strip()
                    q_color_obj = QColor(color_part)
                    if q_color_obj.isValid():
                        swatch_colors_hex.append(q_color_obj.name())
                    else: # Should not happen if UI is updated correctly
                        swatch_colors_hex.append(None)
                else: # Should not happen
                    swatch_colors_hex.append(None)
            else:
                swatch_colors_hex.append(None) # Store None for empty swatches
        
        config_path = self.get_config_path()
        config_data = {}
        if os.path.exists(config_path):
            try:
                with open(config_path, "r") as f:
                    config_data = json.load(f)
            except json.JSONDecodeError:
                print(f"Warning: Config file {config_path} is corrupted. Will be overwritten.")
                config_data = {} # Reset if corrupted
            except Exception as e:
                print(f"Error reading config file {config_path}: {e}")
                config_data = {} # Fallback

        config_data["color_picker_swatches"] = swatch_colors_hex
        try:
            with open(config_path, "w") as f:
                json.dump(config_data, f, indent=4)
            # print(f"DEBUG: Color picker swatches saved to {config_path}")
        except Exception as e:
            print(f"Error saving color picker swatches to {config_path}: {e}")
            self.status_bar.showMessage(f"Error saving swatches: {e}", 3000)

    def load_color_picker_swatches_from_config(self):
        """Loads 'My Colors' swatches from the config file."""
        config_path = self.get_config_path()
        default_swatches = [None] * self.num_custom_swatches # List of Nones
        loaded_swatches = default_swatches[:] # Make a copy

        if os.path.exists(config_path):
            try:
                with open(config_path, "r") as f:
                    config_data = json.load(f)
                loaded_hex_from_config = config_data.get("color_picker_swatches", [])
                # Ensure we have exactly num_custom_swatches, padding with None if necessary
                for i in range(self.num_custom_swatches):
                    if i < len(loaded_hex_from_config):
                        loaded_swatches[i] = loaded_hex_from_config[i]
                    else:
                        loaded_swatches[i] = None # Explicitly None if config is short
            except json.JSONDecodeError:
                print(f"Warning: Config file {config_path} corrupted. Using default swatches.")
            except Exception as e:
                print(f"Error loading color picker swatches from {config_path}: {e}")
        
        self.update_all_color_picker_swatch_buttons_ui(loaded_swatches)
        # print(f"DEBUG: Color picker swatches loaded. First item: {loaded_swatches[0] if loaded_swatches else 'N/A'}")

    # --- Static Pad Layout Presets ---
    def sanitize_filename(self, name: str) -> str:
        """Sanitizes a string to be suitable for a filename."""
        name = re.sub(r'[^\w\s-]', '', name).strip() # Remove invalid chars
        name = re.sub(r'[-\s]+', '_', name)         # Replace spaces/hyphens with underscore
        return name if name else "untitled_layout"

    def get_presets_base_dir(self):
        """Returns the 'presets' directory path."""
        try:
            base_path = os.path.dirname(os.path.abspath(__file__)) # gui directory
            project_root = os.path.dirname(base_path)
        except NameError:
            project_root = os.path.dirname(os.path.abspath(sys.argv[0]))
        return os.path.join(project_root, "presets")

    def load_all_static_pad_layouts(self):
        """Loads all static pad layouts from prefab and user directories."""
        self.loaded_static_presets.clear()
        presets_base_dir = self.get_presets_base_dir()
        
        # Define structure: (type_id, relative_dir_segment, display_prefix)
        layout_sources = [
            ("prefab", os.path.join("static", "prefab"), "[Prefab] "),
            ("user", os.path.join("static", "user"), "")
        ]

        for type_id, dir_segment, prefix in layout_sources:
            abs_dir = os.path.join(presets_base_dir, dir_segment)
            if os.path.isdir(abs_dir):
                for filepath in glob.glob(os.path.join(abs_dir, "*.json")):
                    try:
                        with open(filepath, "r") as f:
                            data = json.load(f)
                        # Sanitize name from file or use filename
                        raw_name = data.get("name", os.path.splitext(os.path.basename(filepath))[0])
                        display_name = prefix + raw_name.replace("_", " ").replace("-", " ")
                        
                        if display_name and data.get("colors") and \
                           isinstance(data["colors"], list) and len(data["colors"]) == 64:
                            self.loaded_static_presets[display_name] = {
                                "path": filepath,
                                "data": data, # Store raw data
                                "type": type_id
                            }
                    except Exception as e:
                        print(f"Error loading static layout {filepath}: {e}")
        self.update_static_presets_combo()

    def update_static_presets_combo(self):
        """Updates the QComboBox for static pad layouts."""
        self.static_presets_combo.blockSignals(True)
        current_text = self.static_presets_combo.currentText()
        self.static_presets_combo.clear()

        if not self.loaded_static_presets:
            self.static_presets_combo.addItem("No layouts found")
            self.static_presets_combo.setEnabled(False)
            self.apply_layout_button.setEnabled(False)
            self.delete_layout_button.setEnabled(False)
        else:
            # Sort keys: user presets first, then prefab, then alphabetically
            sorted_keys = sorted(
                self.loaded_static_presets.keys(),
                key=lambda k: (self.loaded_static_presets[k]['type'] == 'prefab', k.lower())
            )
            self.static_presets_combo.addItems(sorted_keys)
            self.static_presets_combo.setEnabled(True)
            # Try to restore selection
            idx = self.static_presets_combo.findText(current_text)
            if idx != -1:
                self.static_presets_combo.setCurrentIndex(idx)
            elif self.static_presets_combo.count() > 0:
                self.static_presets_combo.setCurrentIndex(0)
            self._on_static_preset_combo_changed() # Update button states

        self.static_presets_combo.blockSignals(False)
        # Connect after populating, if not already connected
        try:
            self.static_presets_combo.currentIndexChanged.disconnect(self._on_static_preset_combo_changed)
        except TypeError: pass # Not connected
        self.static_presets_combo.currentIndexChanged.connect(self._on_static_preset_combo_changed)


    def _on_static_preset_combo_changed(self):
        """Enables/disables preset buttons based on current selection."""
        selected_text = self.static_presets_combo.currentText()
        is_valid_selection = selected_text and selected_text != "No layouts found"
        self.apply_layout_button.setEnabled(is_valid_selection and self.akai_controller.is_connected())
        
        can_delete = False
        if is_valid_selection and selected_text in self.loaded_static_presets:
            can_delete = self.loaded_static_presets[selected_text]['type'] == 'user'
        self.delete_layout_button.setEnabled(can_delete and self.akai_controller.is_connected())


    def apply_selected_static_pad_layout(self):
        """Applies the selected static layout to the pads."""
        if not self.akai_controller.is_connected():
            self.status_bar.showMessage("Connect to device first.", 2000)
            return

        self.stop_current_animation() # Stop any running animation
        
        layout_name = self.static_presets_combo.currentText()
        if layout_name in self.loaded_static_presets:
            layout_data = self.loaded_static_presets[layout_name]["data"]
            colors_hex = layout_data.get("colors")

            if colors_hex and isinstance(colors_hex, list) and len(colors_hex) == 64:
                self.apply_colors_to_main_pad_grid(colors_hex, update_hw=True)
                self.status_bar.showMessage(f"Applied static layout: {layout_name}", 2000)
                # Optionally, set the first color of the layout as the active painting color
                if colors_hex[0]:
                    first_color = QColor(colors_hex[0])
                    if first_color.isValid():
                        self.final_color_selected_signal.emit(first_color)
            else:
                QMessageBox.warning(self, "Layout Error", f"Layout '{layout_name}' has invalid color data.")
        else:
            self.status_bar.showMessage("No valid layout selected to apply.", 2000)


    def save_current_layout_as_user_pad_layout(self):
        """Saves the current pad grid configuration as a new user static layout."""
        if not self.akai_controller.is_connected():
            self.status_bar.showMessage("Connect to device first.", 2000)
            return

        self.stop_current_animation() # Stop animation if running

        text, ok = QInputDialog.getText(self, "Save Static Layout", "Enter Layout Name:")
        if not (ok and text):
            return # User cancelled or entered empty name

        raw_name = text.strip()
        if not raw_name:
            QMessageBox.warning(self, "Save Error", "Layout name cannot be empty.")
            return

        # Check for name clashes with prefabs
        if f"[Prefab] {raw_name}" in self.loaded_static_presets:
            QMessageBox.warning(self, "Save Error", f"Name '{raw_name}' clashes with a prefab layout name.")
            return
        
        # Check if user preset with this name (without prefix) already exists
        if raw_name in [k for k, v in self.loaded_static_presets.items() if v['type'] == 'user']:
             reply = QMessageBox.question(self, "Overwrite Confirmation",
                                         f"A user layout named '{raw_name}' already exists. Overwrite it?",
                                         QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                         QMessageBox.StandardButton.No)
             if reply == QMessageBox.StandardButton.No:
                 return

        filename_base = self.sanitize_filename(raw_name)
        filename = f"{filename_base}.json"
        user_dir = os.path.join(self.get_presets_base_dir(), "static", "user")
        if not os.path.exists(user_dir): os.makedirs(user_dir, exist_ok=True) # Ensure dir exists
        filepath = os.path.join(user_dir, filename)

        current_grid_colors_hex = self.get_current_main_pad_grid_colors()
        layout_data = {
            "name": raw_name, # Store the user-friendly name
            "description": "User-saved static pad layout.",
            "colors": current_grid_colors_hex
        }

        try:
            with open(filepath, "w") as f:
                json.dump(layout_data, f, indent=4)
            self.status_bar.showMessage(f"Static layout '{raw_name}' saved successfully.", 2000)
            self.load_all_static_pad_layouts() # Refresh the list
            self.static_presets_combo.setCurrentText(raw_name) # Select the newly saved layout
        except Exception as e:
            QMessageBox.critical(self, "Save Error", f"Could not save static layout: {e}")


    def delete_selected_user_pad_layout(self):
        """Deletes the selected user static layout."""
        if not self.akai_controller.is_connected():
            self.status_bar.showMessage("Connect to device first.", 2000)
            return

        selected_display_name = self.static_presets_combo.currentText()
        if not selected_display_name or selected_display_name == "No layouts found":
            self.status_bar.showMessage("No layout selected to delete.", 2000)
            return

        layout_info = self.loaded_static_presets.get(selected_display_name)
        if not layout_info or layout_info["type"] != "user":
            QMessageBox.warning(self, "Delete Error", "Only user-saved static layouts can be deleted.")
            return

        reply = QMessageBox.question(self, "Confirm Deletion",
                                     f"Are you sure you want to delete the static layout '{selected_display_name}'?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                     QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            try:
                if os.path.exists(layout_info["path"]):
                    os.remove(layout_info["path"])
                    self.status_bar.showMessage(f"Layout '{selected_display_name}' deleted.", 2000)
                    self.load_all_static_pad_layouts() # Refresh list and combo
                else:
                    QMessageBox.warning(self, "Delete Error", "Layout file not found on disk.")
                    self.load_all_static_pad_layouts() # Refresh anyway
            except Exception as e:
                QMessageBox.critical(self, "Delete Error", f"Could not delete layout file: {e}")

    # --- Animator Methods ---
    def stop_current_animation(self):
        """Stops the current animation playback."""
        print("DEBUG: stop_current_animation called")
        if self.playback_timer.isActive():
            self.playback_timer.stop()
        
        if self.active_sequence_model:
            self.active_sequence_model.stop_playback() # Uses new model method
            # Playback state change signal from model should update UI
        
        # Fallback UI update if model signal doesn't cover it or for immediate effect
        if self.sequence_controls_widget:
             self.sequence_controls_widget.update_playback_button_state(False)
        # self.status_bar.showMessage("Animation stopped.", 2000) # Optional status


    def _update_animator_ui_for_current_sequence(self):
        """Updates animator UI (timeline, controls) based on the active sequence model."""
        if self.active_sequence_model:
            # Update timeline display
            self.sequence_timeline_widget.update_frames_display(
                self.active_sequence_model.get_frame_count(),
                self.active_sequence_model.get_current_edit_frame_index(),
                self.active_sequence_model.get_current_playback_frame_index() if self.active_sequence_model.get_is_playing() else -1
            )
            # Update delay control
            self.sequence_controls_widget.set_frame_delay_ui(self.active_sequence_model.frame_delay_ms)
            # Apply current edit frame's colors to grid if one is selected
            self.on_animator_model_edit_frame_changed(self.active_sequence_model.get_current_edit_frame_index())

        self._update_animator_controls_enabled_state() # General enable/disable state


    def _update_animator_ui_for_current_sequence_properties(self):
        """Updates UI elements related to sequence properties like name or delay."""
        if self.active_sequence_model and self.sequence_controls_widget:
            self.sequence_controls_widget.set_frame_delay_ui(self.active_sequence_model.frame_delay_ms)
        
        # Update sequence combo if name changed
        # This is tricky: if name changes, combo needs to reflect it.
        # Simplest is to reload sequences if name changes significantly (not just "New Sequence")
        # Or, find and update the item text in sequences_combo.
        # For now, properties_changed mainly handles delay. Name changes via Save As will refresh combo.


    def _update_animator_controls_enabled_state(self):
        """Updates the enabled state of animator controls and undo/redo actions."""
        is_connected = self.akai_controller.is_connected()
        has_frames = False
        frame_selected = False
        can_undo = False
        can_redo = False

        if self.active_sequence_model:
            has_frames = self.active_sequence_model.get_frame_count() > 0
            frame_selected = self.active_sequence_model.get_current_edit_frame_index() != -1
            can_undo = bool(self.active_sequence_model._undo_stack) # Accessing internal for now
            can_redo = bool(self.active_sequence_model._redo_stack)

        # Animator Controls Widget
        if self.sequence_controls_widget:
            self.sequence_controls_widget.set_controls_enabled_state(
                enabled=is_connected, # Overall enabled state tied to connection
                frame_selected=frame_selected,
                has_frames=has_frames
            )

        # Undo/Redo Actions
        if self.undo_action: self.undo_action.setEnabled(is_connected and can_undo)
        if self.redo_action: self.redo_action.setEnabled(is_connected and can_redo)

        # Sequence Management Buttons (New, Save As, Delete)
        if self.sequences_combo: self.sequences_combo.setEnabled(is_connected)
        if self.new_seq_button: self.new_seq_button.setEnabled(is_connected)
        if self.save_seq_button: self.save_seq_button.setEnabled(is_connected and has_frames) # Can save if frames exist
        
        can_delete_seq = False
        if is_connected and self.sequences_combo and self.sequences_combo.currentIndex() > 0: # Not "---Select---"
            current_seq_name = self.sequences_combo.currentText()
            if current_seq_name in self.loaded_sequences:
                can_delete_seq = self.loaded_sequences[current_seq_name].get("type") == "user"
        if self.delete_seq_button: self.delete_seq_button.setEnabled(can_delete_seq)


    def on_animator_frame_selected_in_timeline(self, frame_index: int):
        """Handles frame selection from the timeline widget."""
        if self.active_sequence_model:
            self.active_sequence_model.set_current_edit_frame_index(frame_index)
            # The model's current_edit_frame_changed signal will trigger UI updates (like pad grid)

    def on_animator_model_edit_frame_changed(self, frame_index: int):
        """Handles when the model's current edit frame changes."""
        print(f"DEBUG: on_animator_model_edit_frame_changed: Index {frame_index}")
        if self.active_sequence_model and self.active_sequence_model.get_is_playing():
            self.on_animator_pause() # Pause playback if editing a new frame

        if self.sequence_timeline_widget:
            self.sequence_timeline_widget.set_selected_frame_by_index(frame_index) # Sync timeline selection
        
        # Apply the selected frame's colors to the main pad grid
        colors_hex = None
        if self.active_sequence_model and frame_index != -1:
            colors_hex = self.active_sequence_model.get_frame_colors(frame_index)
        
        if colors_hex: # Ensure colors_hex is not None and not empty
            self.apply_colors_to_main_pad_grid(colors_hex, update_hw=True) # Update hardware too
        else:
            self.clear_main_pad_grid_ui(update_hw=True) # Clear grid if no frame or empty frame selected

        self._update_animator_controls_enabled_state()


    def on_animator_model_frame_content_updated(self, frame_index: int):
        """Handles when the content of a specific frame in the model is updated."""
        # If the updated frame is the currently displayed edit frame, refresh the grid.
        if self.active_sequence_model and frame_index == self.active_sequence_model.get_current_edit_frame_index():
            colors_hex = self.active_sequence_model.get_frame_colors(frame_index)
            if colors_hex:
                self.apply_colors_to_main_pad_grid(colors_hex, update_hw=True)
            else: # Should not happen if frame_content_updated means it has content
                self.clear_main_pad_grid_ui(update_hw=True)
        # Could also update timeline thumbnail here in the future.

    def on_animator_model_playback_state_changed(self, is_playing: bool):
        """Updates UI based on model's playback state changes."""
        if self.sequence_controls_widget:
            self.sequence_controls_widget.update_playback_button_state(is_playing)
        if is_playing:
            self.status_bar.showMessage("Sequence playing...", 0) # Persistent while playing
        else:
            # If timer is not also stopped, status might be "Paused" or "Stopped"
            if not self.playback_timer.isActive(): # Check if truly stopped vs paused
                 self.status_bar.showMessage("Sequence stopped.", 3000)
            else: # Timer still active implies it was likely a pause from model's perspective (e.g. end of non-loop)
                 self.status_bar.showMessage("Sequence paused or ended.", 3000)

        self._update_animator_controls_enabled_state()


    def on_animator_add_frame_action_from_timeline_menu(self, frame_type: str):
        """Handles 'Add Frame' actions (Snapshot, Blank) triggered from timeline context menu."""
        # The timeline menu might not have a "current selection" if right-clicked on empty space.
        # Default to adding at the end or after current selection if available.
        insert_at_index = None
        if self.active_sequence_model:
            current_idx = self.active_sequence_model.get_current_edit_frame_index()
            if current_idx != -1:
                insert_at_index = current_idx + 1 # Insert after current
            # else, it will append (default for _add_frame_internal if index is None)
        self.on_animator_add_frame_action_from_controls(frame_type, at_index=insert_at_index)


    def on_animator_add_frame_action_from_controls(self, frame_type: str, at_index: int = None):
        """Handles 'Add Frame' actions (Snapshot, Blank) from controls widget or timeline."""
        if not self.akai_controller.is_connected() or not self.active_sequence_model:
            self.status_bar.showMessage("Connect to device and ensure a sequence is active.", 2000)
            return
        
        self.stop_current_animation() # Stop playback before modifying frames

        if frame_type == "snapshot":
            current_grid_colors = self.get_current_main_pad_grid_colors()
            self.active_sequence_model.add_frame_snapshot(current_grid_colors, at_index)
            self.status_bar.showMessage("Snapshot frame added.", 1500)
        elif frame_type == "blank":
            self.active_sequence_model.add_blank_frame(at_index)
            self.status_bar.showMessage("Blank frame added.", 1500)
        
        # _update_animator_ui_for_current_sequence will be called by model's frames_changed signal
        # _update_animator_controls_enabled_state is also called by that

    def on_animator_delete_selected_frame_from_controls(self):
        """Handles 'Delete Selected Frame' from the controls widget."""
        self.on_animator_delete_frame_action() # Calls the generic delete handler

    def on_animator_delete_frame_action(self, frame_index_override: int = None):
        """Generic handler for deleting a frame, usable by timeline or controls."""
        if not self.akai_controller.is_connected() or not self.active_sequence_model:
            return
        
        self.stop_current_animation()

        original_edit_index = self.active_sequence_model.get_current_edit_frame_index()
        target_delete_index = frame_index_override if frame_index_override is not None else original_edit_index

        if 0 <= target_delete_index < self.active_sequence_model.get_frame_count():
            # If deleting a frame different from current edit, select it first for deletion
            if target_delete_index != original_edit_index:
                self.active_sequence_model.set_current_edit_frame_index(target_delete_index)
            
            if self.active_sequence_model.delete_selected_frame():
                self.status_bar.showMessage("Frame deleted.", 1500)
            else: # Should not happen if index is valid
                self.status_bar.showMessage("Failed to delete frame.", 1500)

            # If we overrode the index, try to restore original selection if still valid,
            # otherwise the model's delete logic handles new selection.
            if frame_index_override is not None and frame_index_override != original_edit_index:
                if 0 <= original_edit_index < self.active_sequence_model.get_frame_count():
                    # Adjust original_edit_index if it was after the deleted frame
                    adjusted_original_index = original_edit_index if original_edit_index < target_delete_index else original_edit_index -1
                    if 0 <= adjusted_original_index < self.active_sequence_model.get_frame_count():
                         self.active_sequence_model.set_current_edit_frame_index(adjusted_original_index)
        else:
            self.status_bar.showMessage("No frame selected or invalid index to delete.", 1500)
        
        # UI updates are handled by model signals

    def on_animator_duplicate_selected_frame_from_controls(self):
        """Handles 'Duplicate Selected Frame' from the controls widget."""
        self.on_animator_duplicate_frame_action() # Calls the generic duplicate handler

    def on_animator_duplicate_frame_action(self, frame_index_override: int = None):
        """Generic handler for duplicating a frame."""
        if not self.akai_controller.is_connected() or not self.active_sequence_model:
            return
        
        self.stop_current_animation()

        original_edit_index = self.active_sequence_model.get_current_edit_frame_index()
        target_duplicate_index = frame_index_override if frame_index_override is not None else original_edit_index

        if 0 <= target_duplicate_index < self.active_sequence_model.get_frame_count():
            if target_duplicate_index != original_edit_index:
                 self.active_sequence_model.set_current_edit_frame_index(target_duplicate_index)

            new_frame_idx = self.active_sequence_model.duplicate_selected_frame()
            if new_frame_idx != -1:
                self.status_bar.showMessage(f"Frame duplicated to position {new_frame_idx + 1}.", 1500)
            else:
                self.status_bar.showMessage("Failed to duplicate frame.", 1500)
            
            # If we overrode index, restore original selection if it's not the duplicated one
            if frame_index_override is not None and frame_index_override != original_edit_index:
                if 0 <= original_edit_index < self.active_sequence_model.get_frame_count() and \
                   original_edit_index != new_frame_idx: # Don't reselect if original was what got duplicated
                     # Adjust original_edit_index if it was after the duplicated frame's new position
                    adjusted_original_index = original_edit_index
                    if original_edit_index >= new_frame_idx : adjusted_original_index +=1 # Shift if original was at or after new frame
                    if 0 <= adjusted_original_index < self.active_sequence_model.get_frame_count():
                        self.active_sequence_model.set_current_edit_frame_index(adjusted_original_index)
        else:
            self.status_bar.showMessage("No frame selected or invalid index to duplicate.", 1500)

    # --- Animator Navigation and Playback Control Handlers ---
    def on_animator_navigate_first(self):
        if self.active_sequence_model and self.active_sequence_model.get_frame_count() > 0:
            self.active_sequence_model.set_current_edit_frame_index(0)

    def on_animator_navigate_prev(self):
        if not self.active_sequence_model or self.active_sequence_model.get_frame_count() == 0: return
        current_idx = self.active_sequence_model.get_current_edit_frame_index()
        if current_idx > 0:
            self.active_sequence_model.set_current_edit_frame_index(current_idx - 1)
        elif current_idx == 0: # Wrap to last frame
            self.active_sequence_model.set_current_edit_frame_index(self.active_sequence_model.get_frame_count() - 1)

    def on_animator_navigate_next(self):
        if not self.active_sequence_model or self.active_sequence_model.get_frame_count() == 0: return
        current_idx = self.active_sequence_model.get_current_edit_frame_index()
        count = self.active_sequence_model.get_frame_count()
        if current_idx < count - 1:
            self.active_sequence_model.set_current_edit_frame_index(current_idx + 1)
        elif current_idx == count - 1: # Wrap to first frame
            self.active_sequence_model.set_current_edit_frame_index(0)

    def on_animator_navigate_last(self):
        if self.active_sequence_model:
            count = self.active_sequence_model.get_frame_count()
            if count > 0:
                self.active_sequence_model.set_current_edit_frame_index(count - 1)

    def on_animator_play(self):
        if not self.akai_controller.is_connected() or not self.active_sequence_model or \
           self.active_sequence_model.get_frame_count() == 0:
            if self.sequence_controls_widget:
                self.sequence_controls_widget.update_playback_button_state(False) # Ensure button reflects non-playing state
            self.status_bar.showMessage("Cannot play: No frames or not connected.", 2000)
            return

        # Start playback from current edit frame, or from beginning if no frame selected/at end
        start_playback_idx = self.active_sequence_model.get_current_edit_frame_index()
        if start_playback_idx == -1 or \
           start_playback_idx >= self.active_sequence_model.get_frame_count(): # If edit index is invalid or past end
            start_playback_idx = 0
        
        # Important: set the model's internal playback index before starting timer
        self.active_sequence_model._playback_frame_index = start_playback_idx

        if self.active_sequence_model.start_playback(): # Model handles its internal state
            self.playback_timer.start(self.active_sequence_model.frame_delay_ms)
            # Model's playback_state_changed signal will update UI via on_animator_model_playback_state_changed
        else: # Should not happen if frame_count > 0
            if self.sequence_controls_widget: self.sequence_controls_widget.update_playback_button_state(False)

    def on_animator_pause(self):
        if self.active_sequence_model:
            self.active_sequence_model.pause_playback() # Model handles its state
        self.playback_timer.stop()
        self.status_bar.showMessage("Sequence paused.", 3000)
        # Model's playback_state_changed signal updates UI

    def on_animator_stop(self):
        self.stop_current_animation() # Calls model's stop_playback
        # Reset view to current edit frame (or first frame if none selected)
        if self.active_sequence_model:
            edit_idx = self.active_sequence_model.get_current_edit_frame_index()
            if edit_idx != -1:
                self.on_animator_model_edit_frame_changed(edit_idx) # Reload edit frame
            elif self.active_sequence_model.get_frame_count() > 0:
                self.on_animator_model_edit_frame_changed(0) # Go to first frame
            else:
                self.clear_main_pad_grid_ui(update_hw=True) # No frames, clear grid
        self.status_bar.showMessage("Sequence stopped.", 3000)


    def advance_and_play_next_frame(self):
        """Called by playback_timer to advance and display the next frame."""
        if not self.active_sequence_model or \
           not self.active_sequence_model.get_is_playing() or \
           not self.akai_controller.is_connected():
            self.stop_current_animation() # Stop if state is inconsistent
            return

        colors_hex = self.active_sequence_model.step_and_get_playback_frame_colors()

        if colors_hex:
            self.apply_colors_to_main_pad_grid(colors_hex, update_hw=True)
            # Update timeline to show current playback frame (visual feedback)
            current_playback_idx = self.active_sequence_model.get_current_playback_frame_index()
            # If loop just happened, playback_idx is 0, but we just showed last frame before advancing
            # The timeline needs to highlight the frame whose colors were *just sent*.
            # step_and_get_playback_frame_colors returns colors THEN advances. So index *before* advance.
            # This logic is tricky. Let's assume _playback_frame_index in model points to *next* frame to be played.
            # So, the frame *just played* was _playback_frame_index - 1 (with wrap around).
            
            idx_just_played = self.active_sequence_model.get_current_playback_frame_index() -1
            if idx_just_played < 0 and self.active_sequence_model.loop: # Wrapped around
                idx_just_played = self.active_sequence_model.get_frame_count() -1
            
            if 0 <= idx_just_played < self.active_sequence_model.get_frame_count():
                 self.sequence_timeline_widget.update_frames_display(
                    self.active_sequence_model.get_frame_count(),
                    self.active_sequence_model.get_current_edit_frame_index(), # Keep edit selection distinct
                    idx_just_played # Highlight this frame as playing
                )

        if not self.active_sequence_model.get_is_playing(): # If step_and_get caused playback to stop (e.g. end of non-looped sequence)
            self.stop_current_animation() # Ensure timer stops and UI updates

    def on_animator_frame_delay_changed(self, delay_ms: int):
        """Handles frame delay changes from the controls widget."""
        if self.active_sequence_model:
            self.active_sequence_model.set_frame_delay_ms(delay_ms)
            if self.playback_timer.isActive(): # If playing, restart timer with new delay
                self.playback_timer.start(delay_ms)
            self.status_bar.showMessage(f"Frame delay set to {delay_ms} ms.", 1500)

    def on_animator_undo(self):
        if self.active_sequence_model and self.active_sequence_model.undo():
            self.status_bar.showMessage("Sequence: Undo successful.", 1500)
            # Model signals (frames_changed, current_edit_frame_changed) should update UI
        else:
            self.status_bar.showMessage("Nothing to undo in sequence.", 1500)
        self._update_animator_controls_enabled_state() # Update undo/redo button states

    def on_animator_redo(self):
        if self.active_sequence_model and self.active_sequence_model.redo():
            self.status_bar.showMessage("Sequence: Redo successful.", 1500)
        else:
            self.status_bar.showMessage("Nothing to redo in sequence.", 1500)
        self._update_animator_controls_enabled_state()

    # --- Pad Grid Utility Methods ---
    def get_current_main_pad_grid_colors(self) -> list:
        """Returns a list of 64 hex color strings from the current GUI pad grid."""
        colors_hex = []
        for r_idx in range(4):
            for c_idx in range(16):
                button = self.pad_buttons.get((r_idx, c_idx))
                hex_color_str = QColor("black").name() # Default to black
                if button:
                    # A more robust way to get color is if PadButton stores its QColor
                    # For now, parsing styleSheet (can be fragile)
                    style = button.styleSheet()
                    try:
                        if "background-color:" in style:
                            bg_part = style.split("background-color:")[1].split(";")[0].strip()
                            temp_color = QColor(bg_part)
                            if temp_color.isValid():
                                hex_color_str = temp_color.name()
                    except Exception: # Fallback if parsing fails
                        pass 
                colors_hex.append(hex_color_str)
        return colors_hex

    def apply_colors_to_main_pad_grid(self, colors_hex: list, update_hw=True):
        """Applies a list of 64 hex color strings to the GUI and optionally hardware pads."""
        if not colors_hex or len(colors_hex) != 64:
            print(f"Warning: apply_colors_to_main_pad_grid received invalid colors_hex list (length {len(colors_hex) if colors_hex else 0}). Clearing grid instead.")
            self.clear_main_pad_grid_ui(update_hw=update_hw)
            return

        hardware_batch_update = []
        for i, hex_color_str in enumerate(colors_hex):
            row, col = divmod(i, 16)
            color = QColor(hex_color_str if hex_color_str else "#000000") # Default to black if None/empty
            if not color.isValid(): color = QColor("black") # Ensure valid color object

            self.update_gui_pad_color(row, col, color.red(), color.green(), color.blue())
            if update_hw:
                hardware_batch_update.append((row, col, color.red(), color.green(), color.blue()))
        
        if update_hw and self.akai_controller.is_connected() and hardware_batch_update:
            self.akai_controller.set_multiple_pads_color(hardware_batch_update)

    def clear_main_pad_grid_ui(self, update_hw=True):
        """Clears the main pad grid UI to black, optionally updates hardware."""
        blank_colors_hex = [QColor("black").name()] * 64
        self.apply_colors_to_main_pad_grid(blank_colors_hex, update_hw=update_hw)


    # --- Sequence File Management ---
    def get_sequences_dir_path(self, sequence_type="user") -> str:
        """Gets the directory path for user or prefab sequences."""
        base_dir = self.get_presets_base_dir() # Gets "presets" directory
        if sequence_type == "user":
            return os.path.join(base_dir, "sequences", "user")
        else: # prefab
            return os.path.join(base_dir, "sequences", "prefab")

    def load_all_sequences(self):
        """Loads metadata for all available sequences (prefab and user)."""
        self.loaded_sequences.clear()
        
        seq_sources = [
            ("prefab", self.get_sequences_dir_path("prefab"), "[Prefab] "),
            ("user", self.get_sequences_dir_path("user"), "")
        ]

        for type_id, abs_dir, prefix in seq_sources:
            if os.path.isdir(abs_dir):
                for filepath in glob.glob(os.path.join(abs_dir, "*.json")):
                    try:
                        # For speed, only load name from JSON, not full sequence data yet
                        with open(filepath, "r") as f:
                            data = json.load(f) 
                        raw_name = data.get("name", os.path.splitext(os.path.basename(filepath))[0])
                        display_name = prefix + raw_name.replace("_", " ").replace("-", " ")
                        if display_name:
                            self.loaded_sequences[display_name] = {"path": filepath, "type": type_id}
                    except Exception as e:
                        print(f"Error reading sequence metadata from {filepath}: {e}")
        self.update_sequences_combo()


    def update_sequences_combo(self):
        """Updates the QComboBox for animator sequences."""
        self.sequences_combo.blockSignals(True)
        current_selection_text = self.sequences_combo.currentText() # Save current selection
        self.sequences_combo.clear()
        self.sequences_combo.addItem("--- Select Sequence ---") # Placeholder

        if not self.loaded_sequences:
            self.sequences_combo.addItem("No sequences found")
            # self.sequences_combo.setEnabled(False) # Enable/disable handled by _update_animator_controls
        else:
            # Sort: user sequences first, then prefab, then alphabetically
            sorted_keys = sorted(
                self.loaded_sequences.keys(),
                key=lambda k: (self.loaded_sequences[k]['type'] == 'prefab', k.lower())
            )
            self.sequences_combo.addItems(sorted_keys)
            # self.sequences_combo.setEnabled(True)

        # Try to restore previous selection or select active model's sequence
        restored_idx = self.sequences_combo.findText(current_selection_text)
        if restored_idx != -1:
            self.sequences_combo.setCurrentIndex(restored_idx)
        elif self.active_sequence_model and self.active_sequence_model.name != "New Sequence":
            # Try to find the active model's name in the combo
            active_model_display_name = self.active_sequence_model.name
            # Check if it's a known prefab to add prefix
            if self.active_sequence_model.loaded_filepath:
                for k, v in self.loaded_sequences.items():
                    if os.path.samefile(v['path'], self.active_sequence_model.loaded_filepath):
                        active_model_display_name = k # Use the display name from combo
                        break
            
            idx_for_active_model = self.sequences_combo.findText(active_model_display_name)
            if idx_for_active_model != -1:
                self.sequences_combo.setCurrentIndex(idx_for_active_model)
            elif self.sequences_combo.count() > 0:
                 self.sequences_combo.setCurrentIndex(0) # Default to "---Select---"
        elif self.sequences_combo.count() > 0 :
            self.sequences_combo.setCurrentIndex(0) # Default to "---Select---"

        self.sequences_combo.blockSignals(False)
        self._update_animator_controls_enabled_state() # Update button states


    def on_selected_sequence_changed(self, index: int):
        """Handles selection changes in the sequences QComboBox."""
        if index <= 0: # "--- Select Sequence ---" or "No sequences found"
            # If user explicitly selects this, and current model has unsaved changes,
            # they might expect a prompt or for nothing to happen.
            # For now, if they select the placeholder, we don't automatically create a new one
            # unless the current one is pristine ("New Sequence" with no frames).
            if self.active_sequence_model and \
               self.active_sequence_model.name == "New Sequence" and \
               self.active_sequence_model.get_frame_count() == 0:
                # It's already like a new sequence, do nothing further.
                pass
            return

        selected_display_name = self.sequences_combo.itemText(index)
        if selected_display_name in self.loaded_sequences:
            # TODO: Prompt to save current sequence if modified
            # if self.active_sequence_model.is_modified(): ...
            
            self.stop_current_animation()
            seq_info = self.loaded_sequences[selected_display_name]
            
            new_model_instance = SequenceModel() # Create a new instance
            if new_model_instance.load_from_file(seq_info["path"]):
                self.active_sequence_model = new_model_instance # Replace active model
                self._connect_signals_for_active_sequence_model() # Re-wire signals for the new model
                self._update_animator_ui_for_current_sequence() # Update UI fully
                self.status_bar.showMessage(f"Sequence '{self.active_sequence_model.name}' loaded.", 2000)
            else:
                QMessageBox.warning(self, "Load Error", f"Failed to load sequence: {selected_display_name}")
                self.sequences_combo.setCurrentIndex(0) # Revert to placeholder
        self._update_animator_controls_enabled_state()


    def new_sequence(self, prompt_save=True): # prompt_save is placeholder for future
        """Creates a new, empty sequence."""
        if not self.akai_controller.is_connected():
            self.status_bar.showMessage("Connect to device first.", 2000)
            return

        # TODO: Prompt to save current sequence if modified
        # if prompt_save and self.active_sequence_model.is_modified(): ...

        self.stop_current_animation()
        self.active_sequence_model = SequenceModel() # Create a fresh model instance
        self._connect_signals_for_active_sequence_model() # Wire its signals
        self._update_animator_ui_for_current_sequence() # Update UI (will show empty state)
        self.clear_main_pad_grid_ui(update_hw=True) # Clear pads for new sequence
        
        self.status_bar.showMessage("New sequence created. Add some frames!", 2000)
        self.sequences_combo.setCurrentIndex(0) # Set combo to "--- Select ---"
        self._update_animator_controls_enabled_state()


    def save_current_sequence_as(self):
        """Saves the current active sequence to a new file or overwrites."""
        if not self.akai_controller.is_connected() or not self.active_sequence_model:
            self.status_bar.showMessage("No active sequence or not connected.", 2000)
            return
        if self.active_sequence_model.get_frame_count() == 0:
            QMessageBox.information(self, "Save Sequence", "Cannot save an empty sequence. Add some frames first.")
            return

        self.stop_current_animation()
        
        suggested_name = self.active_sequence_model.name
        if suggested_name == "New Sequence": # Don't suggest "New Sequence"
            suggested_name = "" 

        text, ok = QInputDialog.getText(self, "Save Sequence As...", "Sequence Name:", text=suggested_name)
        if not (ok and text):
            return # User cancelled

        raw_name = text.strip()
        if not raw_name:
            QMessageBox.warning(self, "Save Error", "Sequence name cannot be empty.")
            return

        # Check for name clashes with prefabs (display name, not filename)
        if f"[Prefab] {raw_name}" in self.loaded_sequences:
            QMessageBox.warning(self, "Save Error", f"Name '{raw_name}' clashes with a prefab sequence name.")
            return
        
        filename_base = self.sanitize_filename(raw_name)
        filename = f"{filename_base}.json"
        user_sequences_dir = self.get_sequences_dir_path("user")
        if not os.path.exists(user_sequences_dir): os.makedirs(user_sequences_dir, exist_ok=True)
        filepath = os.path.join(user_sequences_dir, filename)

        # Check for overwrite, but be smart: if it's the *same file* the sequence was loaded from,
        # it's a "Save" not "Save As Overwrite".
        is_direct_save_overwrite = False
        if self.active_sequence_model.loaded_filepath and \
           os.path.exists(filepath) and \
           os.path.samefile(filepath, self.active_sequence_model.loaded_filepath):
            is_direct_save_overwrite = True # Saving over the file it was loaded from

        if os.path.exists(filepath) and not is_direct_save_overwrite:
            reply = QMessageBox.question(self, "Overwrite Confirmation",
                                         f"A sequence file named '{filename}' already exists. Overwrite it?",
                                         QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                         QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.No:
                return
        
        self.active_sequence_model.set_name(raw_name) # Update model's name
        if self.active_sequence_model.save_to_file(filepath):
            self.status_bar.showMessage(f"Sequence '{raw_name}' saved.", 2000)
            self.load_all_sequences() # Refresh sequence list
            # Try to select the newly saved/overwritten sequence in the combo
            # Construct display name (it's a user sequence, so no prefix)
            self.sequences_combo.setCurrentText(raw_name) 
        else:
            QMessageBox.critical(self, "Save Error", f"Could not save sequence to '{filepath}'. Check console for details.")
        self._update_animator_controls_enabled_state()


    def delete_selected_sequence(self):
        """Deletes the sequence selected in the QComboBox."""
        if not self.akai_controller.is_connected():
            self.status_bar.showMessage("Connect to device first.", 2000)
            return

        selected_display_name = self.sequences_combo.currentText()
        if not selected_display_name or selected_display_name == "--- Select Sequence ---" or \
           selected_display_name == "No sequences found":
            self.status_bar.showMessage("No sequence selected to delete.", 2000)
            return

        seq_info = self.loaded_sequences.get(selected_display_name)
        if not seq_info or seq_info["type"] != "user":
            QMessageBox.warning(self, "Delete Error", "Only user-saved sequences can be deleted.")
            return

        reply = QMessageBox.question(self, "Confirm Deletion",
                                     f"Are you sure you want to delete the sequence '{selected_display_name}'?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                     QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            try:
                if os.path.exists(seq_info["path"]):
                    os.remove(seq_info["path"])
                    self.status_bar.showMessage(f"Sequence '{selected_display_name}' deleted.", 2000)
                    
                    # If the deleted sequence was the active one, create a new empty sequence
                    if self.active_sequence_model and self.active_sequence_model.loaded_filepath and \
                       os.path.samefile(self.active_sequence_model.loaded_filepath, seq_info["path"]):
                        self.new_sequence(prompt_save=False) # Create new without prompting to save deleted one
                    
                    self.load_all_sequences() # Refresh list (will also update combo selection)
                else:
                    QMessageBox.warning(self, "Delete Error", "Sequence file not found on disk.")
                    self.load_all_sequences() # Refresh anyway
            except Exception as e:
                QMessageBox.critical(self, "Delete Error", f"Could not delete sequence file: {e}")
        self._update_animator_controls_enabled_state()

    # --- Pad Context Menu & Actions ---
    def show_pad_context_menu(self, pad_button_widget, row, col, position_global):
        """Shows context menu for a pad button."""
        menu = QMenu(self)
        action_set_off = QAction("Set Pad to Black (Off)", self)
        action_set_off.triggered.connect(lambda: self.set_single_pad_black_and_update_model(row, col))
        menu.addAction(action_set_off)
        menu.exec(position_global) # mapToGlobal not needed if position is already global from customContextMenuRequested

    def set_single_pad_black_and_update_model(self, row, col):
        """Sets a single pad to black on GUI, HW, and updates the animator model."""
        if not self.akai_controller.is_connected(): return

        black_color = QColor("black")
        # Update Hardware
        self.akai_controller.set_pad_color(row, col, 0,0,0)
        # Update GUI
        self.update_gui_pad_color(row, col, 0,0,0)
        
        # Update Animator Model
        if self.active_sequence_model and \
           self.active_sequence_model.get_current_edit_frame_index() != -1:
            pad_index = row * 16 + col
            self.active_sequence_model.update_pad_in_current_edit_frame(pad_index, black_color.name())
        self.status_bar.showMessage(f"Pad ({row+1},{col+1}) set to Off.", 1500)

    # --- GUI Update Helpers ---
    def update_gui_pad_color(self, row: int, col: int, r_val: int, g_val: int, b_val: int):
        """Updates the visual style of a single PadButton."""
        button = self.pad_buttons.get((row, col))
        if button:
            current_color = QColor(r_val, g_val, b_val)
            style_parts = ["border-radius:2px;"] # Base style from QSS for PadButton
            
            is_off = (r_val == 0 and g_val == 0 and b_val == 0)
            
            if is_off:
                # Use QSS-defined "off" style, or a default dark style
                # Assuming QSS QPushButton#PadButton handles base unlit state
                style_parts.append("background-color: #1C1C1C;") # Dark, almost black
                style_parts.append("border: 1px solid #404040;")
                style_parts.append("color: transparent;") # No text on off pads
                hover_border_color = "#666666" # From QSS
            else:
                style_parts.append(f"background-color: {current_color.name()};")
                # Create a subtle border slightly darker/lighter than the pad color
                border_color_dark = current_color.darker(110).name()
                border_color_light = current_color.lighter(110).name()
                style_parts.append(f"border: 1px solid qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 {border_color_dark}, stop:1 {border_color_light});")
                
                # Text color for contrast
                luminance = 0.299 * r_val + 0.587 * g_val + 0.114 * b_val
                text_color = "#E0E0E0" if luminance < 128 else "#1C1C1C"
                style_parts.append(f"color: {text_color};") # Show text if pad is lit (e.g., for debug)
                # button.setText(f"{row},{col}") # Optional: display row/col on lit pads
                hover_border_color = text_color # Hover border matches text for contrast

            final_style = f"QPushButton#PadButton {{{';'.join(style_parts)}}}" \
                          f"QPushButton#PadButton:hover {{border: 1px solid {hover_border_color};}}"
            button.setStyleSheet(final_style)

    def clear_all_hardware_and_gui_pads(self):
        """Clears all pads on hardware and GUI, and updates current animator frame if active."""
        if not self.akai_controller.is_connected():
            self.status_bar.showMessage("Connect to device first.", 2000)
            return
            
        self.stop_current_animation()
        
        blank_colors_hex = [QColor("black").name()] * 64
        self.apply_colors_to_main_pad_grid(blank_colors_hex, update_hw=True) # Clears GUI and HW

        # If an animator frame is being edited, set all its pads to black too
        if self.active_sequence_model:
            current_frame_obj = self.active_sequence_model.get_current_edit_frame_object()
            if current_frame_obj:
                # This operation should be undoable
                self.active_sequence_model._push_undo_state() # Manually push state before batch update
                for i in range(64):
                    current_frame_obj.set_pad_color(i, QColor("black").name())
                self.active_sequence_model.frame_content_updated.emit(
                    self.active_sequence_model.get_current_edit_frame_index()
                )
        self.status_bar.showMessage("All device pads and current view cleared.", 2000)


    # --- MIDI Connection Management ---
    def populate_midi_ports(self):
        """Populates the MIDI port selection QComboBox."""
        self.port_combo.blockSignals(True)
        self.port_combo.clear()
        available_ports = AkaiFireController.get_available_ports()
        
        if available_ports:
            self.port_combo.addItems(available_ports)
            # Try to pre-select a port that looks like the AKAI Fire
            fire_port_index = -1
            for i, name in enumerate(available_ports):
                if ("fire" in name.lower() or "akai" in name.lower()) and \
                   "midiin" not in name.lower(): # Exclude input ports
                    fire_port_index = i
                    break
            if fire_port_index != -1:
                self.port_combo.setCurrentIndex(fire_port_index)
            elif self.port_combo.count() > 0:
                self.port_combo.setCurrentIndex(0) # Default to first available
            self.port_combo.setEnabled(True)
        else:
            self.port_combo.addItem("No MIDI output ports found")
            self.port_combo.setEnabled(False)
        self.port_combo.blockSignals(False)

    def toggle_connection(self):
        """Connects to or disconnects from the selected MIDI port."""
        if self.akai_controller.is_connected():
            self.akai_controller.disconnect()
        else:
            port_to_connect = self.port_combo.currentText() # 'port' is now defined in this scope
            if port_to_connect and port_to_connect != "No MIDI output ports found":
                if not self.akai_controller.connect(port_to_connect): # connect() returns True/False
                    QMessageBox.warning(self, "Connection Failed", 
                                        f"Could not connect to {port_to_connect}.\n"
                                        "Ensure device is available and not in use by other software.")
            else:
                self.status_bar.showMessage("Please select a valid MIDI port.", 3000)
        
        self.update_connection_status() # Update UI based on new connection state

    def update_connection_status(self):
        """Updates UI elements based on the MIDI connection state."""
        is_connected = self.akai_controller.is_connected()
        self.connect_button.setText("Disconnect" if is_connected else "Connect")
        self.status_bar.showMessage(
            f"Connected to: {self.akai_controller.port_name_used}" if is_connected else "Disconnected. Select port to connect."
        )

        # Enable/disable port combo
        self.port_combo.setEnabled(not is_connected)

        # Enable/disable main functional areas
        self.pad_grid_frame.setEnabled(is_connected)
        self.clear_all_button.setEnabled(is_connected)
        
        # Color Picker elements
        color_picker_widgets = [
            self.sv_picker_widget, self.hue_slider_widget,
            self.r_input, self.g_input, self.b_input,
            self.h_input, self.s_input, self.v_input,
            self.hex_input_lineedit, self.main_color_preview_swatch,
            self.add_cp_swatch_button, self.color_button_off
        ]
        for w in color_picker_widgets:
            if w: w.setEnabled(is_connected)
        for swatch_btn in self.custom_swatch_buttons:
            swatch_btn.setEnabled(is_connected)

        # Static Presets elements
        static_preset_widgets = [
            self.static_presets_combo, self.apply_layout_button,
            self.save_layout_button, self.delete_layout_button
        ]
        for w in static_preset_widgets:
            if w: w.setEnabled(is_connected)
        if is_connected: self._on_static_preset_combo_changed() # Re-evaluate button states

        # Animator elements are handled by _update_animator_controls_enabled_state,
        # which itself considers is_connected.
        self._update_animator_controls_enabled_state()

        if not is_connected:
            self.populate_midi_ports() # Refresh port list if disconnected (e.g. device unplugged)


    def closeEvent(self, event):
        """Handles the main window close event."""
        print("INFO: Close event triggered. Shutting down...")
        self.stop_current_animation() # Stop any animations
        self.save_color_picker_swatches_to_config() # Save custom colors

        if self.akai_controller.is_connected():
            print("INFO: Disconnecting from AKAI Fire...")
            self.akai_controller.disconnect() # Cleanly disconnect and turn off LEDs
        
        print("INFO: Application shutdown complete.")
        event.accept()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    
    # Determine project root to load stylesheet correctly
    try:
        gui_dir_path = os.path.dirname(os.path.abspath(__file__)) 
        project_root_path = os.path.dirname(gui_dir_path) 
    except NameError: # Fallback if __file__ is not defined (e.g. interactive)
        project_root_path = os.path.dirname(os.path.abspath(sys.argv[0]))
        
    style_sheet_path_abs = os.path.join(project_root_path, "resources", "styles", "style.qss")
    
    try:
        with open(style_sheet_path_abs, "r") as f:
            app.setStyleSheet(f.read())
            print(f"INFO: Stylesheet '{style_sheet_path_abs}' loaded successfully.")
    except FileNotFoundError:
        print(f"Warning: Main stylesheet '{style_sheet_path_abs}' not found. Using default styles.")
    except Exception as e:
        print(f"Error loading stylesheet '{style_sheet_path_abs}': {e}")
        
    main_win = MainWindow()
    main_win.show()
    sys.exit(app.exec())