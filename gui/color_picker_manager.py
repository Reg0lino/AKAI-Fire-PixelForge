# AKAI_Fire_RGB_Controller/gui/color_picker_manager.py
import json
import os
import sys
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QGridLayout,
    QGroupBox, QLineEdit, QFrame, QMenu, QApplication # Added QMenu, QApplication
)
from PyQt6.QtGui import QColor, QPalette, QIntValidator, QMouseEvent, QAction, QIcon # Added QAction, QIcon
from PyQt6.QtCore import Qt, pyqtSignal, QPoint

from .sv_picker import SVPicker
from .hue_slider import HueSlider
from PyQt6.QtWidgets import QSizePolicy

MAX_SAVED_COLORS = 24 # 2 rows of 8
CONFIG_FILE_NAME = "fire_controller_config.json"
CONFIG_KEY_SAVED_COLORS = "color_picker_swatches"

class ColorPickerManager(QGroupBox):
    ICON_ADD_SWATCH_COLOR = "➕"
    ICON_CLEAR_ALL_SWATCHES = "🗑️"
    ICON_MENU_DELETE = "🗑️"
    ICON_MENU_SET_COLOR = "🎨"

    final_color_selected = pyqtSignal(QColor)
    status_message_requested = pyqtSignal(str, int)
    ICON_ADD_SWATCH_COLOR = "➕"
    ICON_CLEAR_ALL_SWATCHES = "🗑️"
    ICON_MENU_DELETE = "🗑️"
    ICON_MENU_SET_COLOR = "🎨"

    final_color_selected = pyqtSignal(QColor)
    status_message_requested = pyqtSignal(str, int)

    # --- ADDED NEW SIGNALS ---
    request_clear_all_pads = pyqtSignal()
    # To sync with MainWindow's eyedropper state
    eyedropper_button_toggled = pyqtSignal(bool)
    # --- END ADDED NEW SIGNALS ---


    def __init__(self, initial_color=QColor("red"), parent_group_title="🎨 Color Picker", config_save_path_func=None):
        super().__init__(parent_group_title)
        self._current_color = QColor(initial_color)
        self.config_save_path_func = config_save_path_func

        self.sv_picker = SVPicker()
        self.hue_slider = HueSlider()

        self.r_input = QLineEdit()
        self.g_input = QLineEdit()
        self.b_input = QLineEdit()
        self.hex_input = QLineEdit()
        self.hex_input.setObjectName("HexColorInputLineEdit")

        self.saved_color_buttons: list['ColorSwatchButton'] = []
        # self.saved_colors_hex is initialized using the NEW MAX_SAVED_COLORS
        self.saved_colors_hex: list[str | None] = [None] * MAX_SAVED_COLORS

        self.eyedropper_button: QPushButton | None = None
        self.set_black_button: QPushButton | None = None
        self.clear_pads_button: QPushButton | None = None

        self.setObjectName("ColorPickerManagerGroup")

        self._init_ui()
        self._connect_signals()
        # This will now correctly handle 24 slots
        self.load_color_picker_swatches_from_config()
        self._update_ui_from_color(self._current_color, source="init")


    def _get_config_file_path(self):
        if self.config_save_path_func:
            return self.config_save_path_func(CONFIG_FILE_NAME)
        else:
            try:
                current_file_dir = os.path.dirname(os.path.abspath(__file__))
                project_root = os.path.dirname(current_file_dir)
            except NameError:
                project_root = os.getcwd()
            # Fallback if no config_save_path_func and __file__ is problematic
            fallback_dir = os.path.join(project_root, "user_settings_fallback_cpm")
            os.makedirs(fallback_dir, exist_ok=True)
            return os.path.join(fallback_dir, CONFIG_FILE_NAME)


    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(8)

        # --- Top line for RGB, Hex, and Eyedropper inputs ---
        top_input_line_layout = QHBoxLayout()
        top_input_line_layout.setContentsMargins(0, 0, 0, 0)

        rgb_group_layout = QHBoxLayout()
        rgb_group_layout.setSpacing(3)
        rgb_group_layout.setContentsMargins(0, 0, 0, 0)
        int_validator = QIntValidator(0, 255, self)

        rgb_group_layout.addWidget(QLabel("R:"))
        self.r_input.setValidator(int_validator)
        self.r_input.setFixedWidth(38)
        self.r_input.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.r_input.setToolTip("Red component (0-255)")
        rgb_group_layout.addWidget(self.r_input)
        rgb_group_layout.addSpacing(10)

        rgb_group_layout.addWidget(QLabel("G:"))
        self.g_input.setValidator(int_validator)
        self.g_input.setFixedWidth(38)
        self.g_input.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.g_input.setToolTip("Green component (0-255)")
        rgb_group_layout.addWidget(self.g_input)
        rgb_group_layout.addSpacing(10)

        rgb_group_layout.addWidget(QLabel("B:"))
        self.b_input.setValidator(int_validator)
        self.b_input.setFixedWidth(38)
        self.b_input.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.b_input.setToolTip("Blue component (0-255)")
        rgb_group_layout.addWidget(self.b_input)

        top_input_line_layout.addLayout(rgb_group_layout)
        top_input_line_layout.addStretch(1)

        hex_eyedropper_group_layout = QHBoxLayout()
        hex_eyedropper_group_layout.setSpacing(3)
        hex_eyedropper_group_layout.setContentsMargins(0, 0, 0, 0)

        hex_eyedropper_group_layout.addWidget(QLabel("Hex:"))
        self.hex_input.setFixedWidth(70)
        self.hex_input.setMaxLength(7)
        self.hex_input.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.hex_input.setToolTip("Hexadecimal color code (#RRGGBB)")
        hex_eyedropper_group_layout.addWidget(self.hex_input)
        hex_eyedropper_group_layout.addSpacing(5)

        self.eyedropper_button = QPushButton("💧")
        self.eyedropper_button.setObjectName("EyedropperToolButton")
        self.eyedropper_button.setToolTip(
            "Toggle Eyedropper mode (I): Click a pad to pick its color.")
        self.eyedropper_button.setCheckable(True)
        hex_eyedropper_group_layout.addWidget(self.eyedropper_button)

        top_input_line_layout.addLayout(hex_eyedropper_group_layout)
        main_layout.addLayout(top_input_line_layout)

        # --- SV Picker and Hue Slider ---
        pickers_layout = QHBoxLayout()
        pickers_layout.setSpacing(6)
        pickers_layout.addWidget(self.sv_picker, 3)
        pickers_layout.addWidget(self.hue_slider, 1)
        main_layout.addLayout(pickers_layout)

        # --- "My Colors" Swatches Group ---
        my_colors_group = QGroupBox("My Colors")
        my_colors_layout = QVBoxLayout(my_colors_group)
        my_colors_layout.setSpacing(4)  # Spacing between grid and button row

        swatches_grid_layout = QGridLayout()
        swatches_grid_layout.setSpacing(5)

        NUM_SWATCH_COLUMNS = 8  # Define number of columns for swatches

        self.saved_color_buttons.clear()  # Clear existing buttons before repopulating
        for i in range(MAX_SAVED_COLORS):  # MAX_SAVED_COLORS is now 24
            row, col = divmod(i, NUM_SWATCH_COLUMNS)  # Use NUM_SWATCH_COLUMNS
            swatch = ColorSwatchButton(parent=self)
            swatch.clicked.connect(lambda checked=False,
                                   s=swatch: self._on_swatch_clicked(s))
            swatch.rightClicked.connect(
                lambda pos, s=swatch, idx=i: self._show_swatch_context_menu(s, idx, pos))
            self.saved_color_buttons.append(swatch)
            swatches_grid_layout.addWidget(swatch, row, col)
        my_colors_layout.addLayout(swatches_grid_layout)

        # --- ADDED: Vertical spacing between swatches and buttons ---
        # Adjust this value (e.g., 8 or 10) for desired gap
        my_colors_layout.addSpacing(8)
        # --- END ADDED ---

        my_colors_buttons_layout = QHBoxLayout()
        self.add_saved_color_button = QPushButton(
            f"{self.ICON_ADD_SWATCH_COLOR} Add")
        self.add_saved_color_button.setObjectName("SwatchAddButton")
        self.add_saved_color_button.setToolTip(
            "Add current color to an empty swatch.")
        self.add_saved_color_button.setSizePolicy(
            QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed)

        self.clear_swatches_button = QPushButton(
            f"{self.ICON_CLEAR_ALL_SWATCHES} Clear All")
        self.clear_swatches_button.setObjectName("SwatchClearAllButton")
        self.clear_swatches_button.setToolTip(
            "Clear all saved color swatches.")
        self.clear_swatches_button.setSizePolicy(
            QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed)

        my_colors_buttons_layout.addStretch(1)
        my_colors_buttons_layout.addWidget(self.add_saved_color_button)
        my_colors_buttons_layout.addSpacing(5)
        my_colors_buttons_layout.addWidget(self.clear_swatches_button)

        my_colors_layout.addLayout(my_colors_buttons_layout)
        main_layout.addWidget(my_colors_group)

        # --- Integrated "Set Black" and "Clear Pads" buttons ---
        action_tools_layout = QHBoxLayout()
        action_tools_layout.setSpacing(6)
        action_tools_layout.setContentsMargins(0, 4, 0, 0)

        self.set_black_button = QPushButton("Set Black")
        self.set_black_button.setToolTip(
            "Set current painting color to Black (Off).")
        action_tools_layout.addWidget(self.set_black_button)

        action_tools_layout.addStretch(1)

        self.clear_pads_button = QPushButton("Clear Pads")
        self.clear_pads_button.setToolTip(
            "Clear all hardware pads and the current GUI/Animator frame to Black.")
        action_tools_layout.addWidget(self.clear_pads_button)

        main_layout.addLayout(action_tools_layout)


    def _connect_signals(self):
        # Existing picker signals
        self.sv_picker.sv_changed.connect(self._on_sv_changed)
        self.hue_slider.hue_changed.connect(self._on_hue_changed)
        self.r_input.editingFinished.connect(self._on_rgb_input_changed)
        self.g_input.editingFinished.connect(self._on_rgb_input_changed)
        self.b_input.editingFinished.connect(self._on_rgb_input_changed)
        self.hex_input.editingFinished.connect(self._on_hex_input_changed)
        # My Colors swatch management signals
        self.add_saved_color_button.clicked.connect(self._add_current_color_to_swatches)
        self.clear_swatches_button.clicked.connect(self._clear_all_swatches)
        # --- ADDED: Connect signals for new integrated tool buttons ---
        if self.eyedropper_button: # Check if button was created
            self.eyedropper_button.toggled.connect(self.eyedropper_button_toggled) # Emit signal
        if self.set_black_button:
            self.set_black_button.clicked.connect(self._handle_set_black_request)
        if self.clear_pads_button:
            self.clear_pads_button.clicked.connect(self.request_clear_all_pads) # Emit signal

    def _handle_set_black_request(self):
        """Sets the color picker's current color to black."""
        black_color = QColor("black")
        # Call set_current_selected_color to update UI and emit final_color_selected
        self.set_current_selected_color(black_color, source="set_black_button")
        # Status message for this action can be emitted by MainWindow when it receives the black color.
        # Or, if ColorPickerManager handles its own status:
        # self.status_message_requested.emit("Active painting color set to: Black (Off)", 2000)

    def _on_sv_changed(self, s, v):
        h = self.hue_slider.get_hue() / 360.0
        _h_ignored, _s_ignored, _v_ignored, current_alpha = self._current_color.getHsvF()
        self._current_color.setHsvF(h, s, v, current_alpha)
        self._update_ui_from_color(self._current_color, source="sv_picker")
        self.final_color_selected.emit(self._current_color)

    def _on_hue_changed(self, hue_degrees):
        h_float = hue_degrees / 360.0
        _h_ignored, s, v, a = self._current_color.getHsvF()
        self._current_color.setHsvF(h_float, s, v, a)
        self.sv_picker.setHue(hue_degrees)
        self._update_ui_from_color(self._current_color, source="hue_slider")
        self.final_color_selected.emit(self._current_color)

    def _on_rgb_input_changed(self):
        try:
            r = int(self.r_input.text() or "0"); g = int(self.g_input.text() or "0"); b = int(self.b_input.text() or "0")
            r, g, b = [max(0, min(val, 255)) for val in (r,g,b)]
            new_color = QColor(r, g, b)
            if new_color.isValid() and new_color != self._current_color: # Check isValid
                self._current_color = new_color
                self._update_ui_from_color(self._current_color, source="rgb_input")
                self.final_color_selected.emit(self._current_color)
        except ValueError:
            # Optionally revert to current color if input is invalid
            self.r_input.setText(str(self._current_color.red()))
            self.g_input.setText(str(self._current_color.green()))
            self.b_input.setText(str(self._current_color.blue()))


    def _on_hex_input_changed(self):
        hex_val = self.hex_input.text()
        if not hex_val.startswith("#"): hex_val = "#" + hex_val
        new_color = QColor(hex_val)
        if new_color.isValid() and new_color != self._current_color:
            self._current_color = new_color
            self._update_ui_from_color(self._current_color, source="hex_input")
            self.final_color_selected.emit(self._current_color)
        elif not new_color.isValid():
            self.hex_input.setText(self._current_color.name().upper()) # Revert to valid hex


    def _update_ui_from_color(self, color: QColor, source: str):
        # Update RGB inputs (if not the source)
        if source != "rgb_input":
            self.r_input.blockSignals(True)
            self.g_input.blockSignals(True)
            self.b_input.blockSignals(True)
            self.r_input.setText(str(color.red()))
            self.g_input.setText(str(color.green()))
            self.b_input.setText(str(color.blue()))
            self.r_input.blockSignals(False)
            self.g_input.blockSignals(False)
            self.b_input.blockSignals(False)

        # Update Hex input text (if not the source) and its dynamic style
        current_hex_for_display = color.name().upper()
        if source != "hex_input":
            self.hex_input.blockSignals(True)
            self.hex_input.setText(current_hex_for_display)
            self.hex_input.blockSignals(False)

        # Always update hex_input style based on the 'color' parameter,
        # which represents the new authoritative color.
        if self.hex_input and color.isValid():  # Ensure color is valid for styling
            luminance = (0.299 * color.redF() + 0.587 *
                         color.greenF() + 0.114 * color.blueF())
            text_color_for_hex = "#000000" if luminance > 0.5 else "#FFFFFF"

            # Base style parts from your QSS to maintain consistency
            base_border = "1px solid #4D4D4D"       # From general QLineEdit
            base_radius = "3px"                     # From general QLineEdit
            base_padding = "1px 3px"                # Matching reduced QLineEdit padding
            base_min_height = "18px"                # Matching reduced QLineEdit min-height

            # If you have a specific QSS for QLineEdit#HexColorInputLineEdit that defines these,
            # it's better. Otherwise, we reconstruct a compatible style.
            # The objectName selector in QSS is more robust than setting full style here.

            # If QLineEdit#HexColorInputLineEdit is styled in QSS, we only need to override
            # background-color and color. Otherwise, include all necessary base styles.
            hex_input_style = f"""
                QLineEdit#HexColorInputLineEdit {{
                    background-color: {color.name()};
                    color: {text_color_for_hex};
                    border: {base_border};
                    border-radius: {base_radius};
                    padding: {base_padding};
                    min-height: {base_min_height};
                    font-weight: bold;
                    text-align: center;
                }}
                QLineEdit#HexColorInputLineEdit:focus {{
                    border: 1px solid #60a0ff; /* Brighter focus */
                }}
            """
            self.hex_input.setStyleSheet(hex_input_style)
        elif self.hex_input:  # Color is invalid, reset hex_input style
            # Revert to QSS default for QLineEdit or QLineEdit#HexColorInputLineEdit
            self.hex_input.setStyleSheet("")

        # Update SV Picker and Hue Slider (if not the source of the change)
        if source != "sv_picker" and source != "hue_slider":
            h, s, v, _a = color.getHsvF()
            if source != "hue_slider":
                self.hue_slider.blockSignals(True)
                self.hue_slider.set_hue(int(h * 359.99), emit_signal=False)
                self.hue_slider.blockSignals(False)

            self.sv_picker.setHue(int(h * 359.99))
            if source != "sv_picker":
                # sv_picker.setSV internally checks if values changed before emitting,
                # but blocking can be an extra precaution if strict avoidance of re-emission is needed.
                # self.sv_picker.blockSignals(True)
                self.sv_picker.setSV(s, v)
                # self.sv_picker.blockSignals(False)


    def _on_swatch_clicked(self, swatch_button: 'ColorSwatchButton'):
        color_hex = swatch_button.get_color_hex()
        # Define what constitutes a visually empty/placeholder color
        placeholder_colors = {"#000000", "#1C1C1C"}
        if color_hex and QColor(color_hex).isValid() and color_hex.upper() not in placeholder_colors:
            self.set_current_selected_color(QColor(color_hex), "swatch_click")

    def _show_swatch_context_menu(self, swatch_button: 'ColorSwatchButton', swatch_index: int, global_pos: QPoint):
        menu = QMenu(self)
        current_swatch_color_hex = self.saved_colors_hex[swatch_index]
        
        placeholder_colors = {"#000000", "#1C1C1C"}
        is_swatch_set_meaningfully = current_swatch_color_hex is not None and \
                                     QColor(current_swatch_color_hex).isValid() and \
                                     current_swatch_color_hex.upper() not in placeholder_colors

        if is_swatch_set_meaningfully:
            select_action = QAction(f"Select Color ({current_swatch_color_hex.upper()})", self)
            select_action.triggered.connect(lambda: self._on_swatch_clicked(swatch_button))
            menu.addAction(select_action)
            
            delete_action_text = f"{ColorPickerManager.ICON_MENU_DELETE} Clear This Swatch"
            delete_action = QAction(delete_action_text, self)
            delete_action.setStatusTip(f"Clear the color from swatch {swatch_index + 1}.")
            delete_action.triggered.connect(lambda: self._clear_single_swatch(swatch_index))
            menu.addAction(delete_action)
        else:
            set_action_text = f"{ColorPickerManager.ICON_MENU_SET_COLOR} Set to Current Picker Color"
            set_action = QAction(set_action_text, self)
            set_action.setStatusTip("Set this empty swatch to the currently selected color in the picker.")
            set_action.triggered.connect(lambda: self._add_current_color_to_specific_swatch(swatch_index))
            menu.addAction(set_action)
        menu.exec(global_pos)

    def _clear_single_swatch(self, swatch_index: int):
        if 0 <= swatch_index < MAX_SAVED_COLORS:
            self.saved_colors_hex[swatch_index] = None
            self._update_swatch_buttons_display()
            self.save_color_picker_swatches_to_config()
            self.status_message_requested.emit(f"Swatch {swatch_index + 1} cleared.", 1500)

    def _add_current_color_to_specific_swatch(self, swatch_index: int):
        if 0 <= swatch_index < MAX_SAVED_COLORS:
            color_to_add = self._current_color.name()
            self.saved_colors_hex[swatch_index] = color_to_add
            self._update_swatch_buttons_display()
            self.save_color_picker_swatches_to_config()
            self.status_message_requested.emit(f"Color {color_to_add.upper()} added to swatch {swatch_index + 1}.", 2000)

    def _add_current_color_to_swatches(self):
        try_index = -1
        placeholder_colors = {"#000000", "#1C1C1C"}
        for i, color_hex in enumerate(self.saved_colors_hex):
            is_placeholder_empty_color = color_hex is None or color_hex.upper() in placeholder_colors
            if is_placeholder_empty_color:
                try_index = i; break
        if try_index == -1:
            try_index = 0
            self.status_message_requested.emit("All swatches full. Overwriting first swatch.", 2000)
        self._add_current_color_to_specific_swatch(try_index)

    def _clear_all_swatches(self):
        for i in range(MAX_SAVED_COLORS): self.saved_colors_hex[i] = None
        self._update_swatch_buttons_display()
        self.save_color_picker_swatches_to_config()
        self.status_message_requested.emit("All color swatches cleared.", 2000)

    def set_current_selected_color(self, color: QColor, source="external"):
        if color.isValid() and color != self._current_color:
            self._current_color = QColor(color) # Ensure it's a new QColor object
            self._update_ui_from_color(self._current_color, source=source)
            self.final_color_selected.emit(self._current_color)

    def get_current_color(self) -> QColor: return QColor(self._current_color) # Return a copy
    def set_enabled(self, enabled:bool): super().setEnabled(enabled)

    def load_color_picker_swatches_from_config(self):
        config_file = self._get_config_file_path()
        if not os.path.exists(config_file):
            self._update_swatch_buttons_display(); return
        try:
            with open(config_file, "r") as f: data = json.load(f)
            loaded_swatches = data.get(CONFIG_KEY_SAVED_COLORS, [])
            # Ensure saved_colors_hex is padded to MAX_SAVED_COLORS
            self.saved_colors_hex = [None] * MAX_SAVED_COLORS
            for i in range(min(len(loaded_swatches), MAX_SAVED_COLORS)):
                if loaded_swatches[i] and QColor(loaded_swatches[i]).isValid():
                    # Don't treat pure black from file as None, unless it's also a placeholder
                    if loaded_swatches[i].upper() == "#000000" and (len(loaded_swatches[i]) == 7 or len(loaded_swatches[i]) == 9) : # Check if it's actual black not a placeholder string
                         self.saved_colors_hex[i] = QColor(loaded_swatches[i]).name() # Store valid black
                    elif QColor(loaded_swatches[i]).isValid(): # Any other valid color
                         self.saved_colors_hex[i] = QColor(loaded_swatches[i]).name()
                    # else remains None
            self._update_swatch_buttons_display()
        except Exception as e:
            print(f"ColorPickerManager: Error loading/parsing swatches from {config_file}: {e}")
            self.saved_colors_hex = [None] * MAX_SAVED_COLORS # Reset on error
            self._update_swatch_buttons_display()

    def save_color_picker_swatches_to_config(self):
        config_file = self._get_config_file_path()
        os.makedirs(os.path.dirname(config_file), exist_ok=True)
        
        # Save None as a specific placeholder string, or ensure saved_colors_hex always has valid hex or None
        swatches_to_save = []
        placeholder_colors = {"#000000", "#1C1C1C"} # Define visual empty / placeholders
        for hex_val in self.saved_colors_hex:
            if hex_val is None or hex_val.upper() in placeholder_colors : # If it's None or a placeholder
                swatches_to_save.append(None) # Save as actual None in JSON, or choose a string like "EMPTY"
            elif QColor(hex_val).isValid():
                swatches_to_save.append(QColor(hex_val).name()) # Save valid colors
            else: # Fallback for invalid hex strings not caught earlier
                swatches_to_save.append(None)
        
        # Pad to MAX_SAVED_COLORS if shorter
        if len(swatches_to_save) < MAX_SAVED_COLORS:
            swatches_to_save.extend([None] * (MAX_SAVED_COLORS - len(swatches_to_save)))
        elif len(swatches_to_save) > MAX_SAVED_COLORS:
            swatches_to_save = swatches_to_save[:MAX_SAVED_COLORS]


        try:
            full_config_data = {}
            if os.path.exists(config_file):
                with open(config_file, "r") as f:
                    try: full_config_data = json.load(f)
                    except json.JSONDecodeError: full_config_data = {}
            if not isinstance(full_config_data, dict): full_config_data = {} # Ensure it's a dict

            full_config_data[CONFIG_KEY_SAVED_COLORS] = swatches_to_save
            with open(config_file, "w") as f: json.dump(full_config_data, f, indent=4)
        except Exception as e:
            print(f"ColorPickerManager: Error saving swatches to {config_file}: {e}")
            if hasattr(self, 'status_message_requested'):
                self.status_message_requested.emit("Error saving color swatches.", 3000)

    def _update_swatch_buttons_display(self):
        placeholder_colors_display = {"#000000", "#1C1C1C"} # Colors that look empty
        for i, swatch_button in enumerate(self.saved_color_buttons):
            color_hex = self.saved_colors_hex[i]
            is_meaningful_color = color_hex and QColor(color_hex).isValid() and \
                                   color_hex.upper() not in placeholder_colors_display
            
            if is_meaningful_color:
                swatch_button.set_color(color_hex)
                swatch_button.setToolTip(f"{color_hex.upper()}. Click to select, Right-click to manage.")
            else:
                swatch_button.set_color("#1C1C1C") # Visually empty
                swatch_button.setToolTip("Empty swatch. Right-click to set, or use 'Add' button.")

# --- ColorSwatchButton Class Definition ---
# (Moved within ColorPickerManager file for simplicity if not used elsewhere, or keep as is if used by other modules)
class ColorSwatchButton(QPushButton):
    rightClicked = pyqtSignal(QPoint)

    def __init__(self, initial_color_hex="#1C1C1C", parent=None):
        super().__init__(parent)
        self.setObjectName("CustomSwatchButton") # For QSS styling
        self.setFixedSize(30, 30)
        self._hex_color = "#1C1C1C" # Initialize internal hex for visual empty
        self.set_color(initial_color_hex)
        self.setToolTip("Empty swatch. Right-click to set, or use 'Add' button.")

    def set_color(self, hex_color_str: str | None):
        # Ensure hex_color_str is a string if it's None for QColor constructor
        valid_hex_for_qcolor = hex_color_str if hex_color_str is not None else "#000000"
        q_color = QColor(valid_hex_for_qcolor)

        if hex_color_str is None or not q_color.isValid():
            self._hex_color = "#1C1C1C" # Visually empty placeholder
        else:
            self._hex_color = q_color.name() # Store the valid color's name (#RRGGBB)

        # Define base style for the button, allowing background to be overridden
        # This uses a more specific QSS selector to override general QPushButton styles.
        # It also respects the dashed border for empty swatches defined in style.qss.
        is_empty_placeholder = self._hex_color == "#1C1C1C"

        if is_empty_placeholder:
            # Let the QSS for QPushButton#CustomSwatchButton handle the empty look
            # We just need to ensure no specific background is set here that overrides it
            self.setStyleSheet(f"""
                QPushButton#CustomSwatchButton {{
                    /* background-color will be from main QSS for empty */
                    border: 1px dashed #666666; 
                    border-radius: 2px;
                }}
                QPushButton#CustomSwatchButton:hover {{
                    border: 1px solid #999999;
                }}
            """)
        else:
            self.setStyleSheet(f"""
                QPushButton#CustomSwatchButton {{
                    background-color: {self._hex_color};
                    border: 1px solid #555555; /* Solid border for filled swatches */
                    border-radius: 2px;
                }}
                QPushButton#CustomSwatchButton:hover {{
                    border: 1px solid #999999;
                }}
            """)
        self.update()

    def get_color_hex(self) -> str:
        return self._hex_color

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.RightButton:
            self.rightClicked.emit(event.globalPosition().toPoint())
        else:
            super().mousePressEvent(event)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    # Load the main stylesheet for standalone testing
    try:
        style_path = os.path.join(os.path.dirname(__file__), "..", "resources", "styles", "style.qss")
        if os.path.exists(style_path):
            with open(style_path, "r") as f:
                app.setStyleSheet(f.read())
                print("Test CPM: Stylesheet loaded.")
        else:
            print(f"Test CPM: Stylesheet not found at {style_path}")
    except Exception as e:
        print(f"Test CPM: Error loading stylesheet: {e}")


    def _get_dev_config_path_cpm(filename):
        # Create a 'user_settings_test' directory in the current script's directory for standalone test
        test_config_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "user_settings_test_cpm")
        os.makedirs(test_config_dir, exist_ok=True)
        return os.path.join(test_config_dir, filename)

    picker_manager = ColorPickerManager(config_save_path_func=_get_dev_config_path_cpm)
    picker_manager.final_color_selected.connect(lambda c: print(f"Test: Color selected: {c.name()}"))
    picker_manager.status_message_requested.connect(lambda msg, time: print(f"Test: Status - {msg} ({time}ms)"))
    picker_manager.show()
    # app.aboutToQuit.connect(picker_manager.save_color_picker_swatches_to_config) # Save on quit
    sys.exit(app.exec())