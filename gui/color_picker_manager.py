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

MAX_SAVED_COLORS = 16 # 2 rows of 8
CONFIG_FILE_NAME = "fire_controller_config.json" 
CONFIG_KEY_SAVED_COLORS = "color_picker_swatches"

class ColorPickerManager(QGroupBox):
    # --- Class Attributes for Icons (used for buttons, can be used for QAction icons if desired) ---
    ICON_ADD_SWATCH_COLOR = "➕" # For the main "Add" button to swatches
    ICON_CLEAR_ALL_SWATCHES = "🗑️" # For the "Clear All" swatches button
    ICON_MENU_DELETE = "🗑️"      # For "Clear This Swatch" in context menu
    ICON_MENU_SET_COLOR = "🎨"   # For "Set to Current Picker Color" in context menu

    final_color_selected = pyqtSignal(QColor)
    status_message_requested = pyqtSignal(str, int)

    def __init__(self, initial_color=QColor("red"), parent_group_title="🎨 Advanced Color Picker", config_save_path_func=None):
        super().__init__(parent_group_title)
        self._current_color = QColor(initial_color)
        self.config_save_path_func = config_save_path_func 
    
        self.sv_picker = SVPicker()
        self.hue_slider = HueSlider()
        
        self.r_input = QLineEdit(); self.g_input = QLineEdit(); self.b_input = QLineEdit()
        self.hex_input = QLineEdit()
        self.preview_box = QFrame()
    
        self.saved_color_buttons: list['ColorSwatchButton'] = [] # Forward reference
        self.saved_colors_hex: list[str | None] = [None] * MAX_SAVED_COLORS
    
        self._init_ui()
        self._connect_signals()
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
                fallback_dir = os.path.join(project_root, "user_settings_fallback_cpm")
                os.makedirs(fallback_dir, exist_ok=True)
                return os.path.join(fallback_dir, CONFIG_FILE_NAME)

    def _init_ui(self):
        main_layout = QVBoxLayout(self)

        pickers_layout = QHBoxLayout()
        pickers_layout.addWidget(self.sv_picker, 3) 
        pickers_layout.addWidget(self.hue_slider, 1)
        main_layout.addLayout(pickers_layout)

        inputs_preview_layout = QHBoxLayout()
        rgb_hex_group = QGroupBox("Numeric Input")
        rgb_hex_layout = QGridLayout(rgb_hex_group)

        int_validator = QIntValidator(0, 255, self)
        for i, (label_text, line_edit_widget) in enumerate([("R:", self.r_input), ("G:", self.g_input), ("B:", self.b_input)]):
            line_edit_widget.setValidator(int_validator); line_edit_widget.setFixedWidth(45)
            line_edit_widget.setAlignment(Qt.AlignmentFlag.AlignCenter)
            rgb_hex_layout.addWidget(QLabel(label_text), i, 0)
            rgb_hex_layout.addWidget(line_edit_widget, i, 1)
        
        rgb_hex_layout.addWidget(QLabel("Hex:"), 0, 2)
        self.hex_input.setFixedWidth(80); self.hex_input.setMaxLength(7)
        rgb_hex_layout.addWidget(self.hex_input, 0, 3, 1, 2)
        inputs_preview_layout.addWidget(rgb_hex_group, 2)

        self.preview_box.setFrameShape(QFrame.Shape.StyledPanel)
        self.preview_box.setFrameShadow(QFrame.Shadow.Sunken)
        self.preview_box.setFixedSize(60, 60)
        self.preview_box.setAutoFillBackground(True)
        inputs_preview_layout.addWidget(self.preview_box, 1, Qt.AlignmentFlag.AlignCenter)
        main_layout.addLayout(inputs_preview_layout)

        my_colors_group = QGroupBox("My Colors")
        my_colors_layout = QVBoxLayout(my_colors_group)
        
        swatches_grid_layout = QGridLayout()
        swatches_grid_layout.setSpacing(5)
        for i in range(MAX_SAVED_COLORS):
            row, col = divmod(i, MAX_SAVED_COLORS // 2) 
            swatch = ColorSwatchButton(parent=self) # Pass parent
            swatch.clicked.connect(lambda checked=False, s=swatch: self._on_swatch_clicked(s))
            swatch.rightClicked.connect(lambda pos, s=swatch, idx=i: self._show_swatch_context_menu(s, idx, pos))
            self.saved_color_buttons.append(swatch)
            swatches_grid_layout.addWidget(swatch, row, col)
        my_colors_layout.addLayout(swatches_grid_layout)

        my_colors_buttons_layout = QHBoxLayout()
        self.add_saved_color_button = QPushButton(f"{self.ICON_ADD_SWATCH_COLOR} Add") 
        self.add_saved_color_button.setToolTip("Add current color to an empty swatch or overwrite selected.")
        self.add_saved_color_button.setStatusTip("Save the currently selected color to your personal swatches.")
        my_colors_buttons_layout.addWidget(self.add_saved_color_button)

        self.clear_swatches_button = QPushButton(f"{self.ICON_CLEAR_ALL_SWATCHES} Clear All") 
        self.clear_swatches_button.setToolTip("Clear all saved color swatches.")
        self.clear_swatches_button.setStatusTip("Remove all colors from your personal swatches.")
        my_colors_buttons_layout.addWidget(self.clear_swatches_button)
        my_colors_layout.addLayout(my_colors_buttons_layout)
        main_layout.addWidget(my_colors_group)

    def _connect_signals(self):
        self.sv_picker.sv_changed.connect(self._on_sv_changed)
        self.hue_slider.hue_changed.connect(self._on_hue_changed)
        self.r_input.editingFinished.connect(self._on_rgb_input_changed)
        self.g_input.editingFinished.connect(self._on_rgb_input_changed)
        self.b_input.editingFinished.connect(self._on_rgb_input_changed)
        self.hex_input.editingFinished.connect(self._on_hex_input_changed)
        self.add_saved_color_button.clicked.connect(self._add_current_color_to_swatches)
        self.clear_swatches_button.clicked.connect(self._clear_all_swatches)

    def _on_sv_changed(self, s, v):
        h = self.hue_slider.get_hue() / 360.0
        # Ensure we use the correct current alpha when setting HSV
        _h_ignored, _s_ignored, _v_ignored, current_alpha = self._current_color.getHsvF() # Get current alpha
        self._current_color.setHsvF(h, s, v, current_alpha) # <<< USE current_alpha
        self._update_ui_from_color(self._current_color, source="sv_picker")
        self.final_color_selected.emit(self._current_color)

    def _on_hue_changed(self, hue_degrees):
        h_float = hue_degrees / 360.0
        # Unpack all four: hue (which we're ignoring here as we get it from slider), saturation, value, alpha
        _h_ignored, s, v, a = self._current_color.getHsvF() # <<< CORRECTED
        self._current_color.setHsvF(h_float, s, v, a) # Use the current alpha 'a'
        self.sv_picker.setHue(hue_degrees) 
        self._update_ui_from_color(self._current_color, source="hue_slider")
        self.final_color_selected.emit(self._current_color)

    def _on_rgb_input_changed(self):
        try:
            r = int(self.r_input.text() or "0"); g = int(self.g_input.text() or "0"); b = int(self.b_input.text() or "0")
            r, g, b = [max(0, min(val, 255)) for val in (r,g,b)]
            new_color = QColor(r, g, b)
            if new_color != self._current_color:
                self._current_color = new_color
                self._update_ui_from_color(self._current_color, source="rgb_input")
                self.final_color_selected.emit(self._current_color)
        except ValueError: pass

    def _on_hex_input_changed(self):
        hex_val = self.hex_input.text()
        if not hex_val.startswith("#"): hex_val = "#" + hex_val
        new_color = QColor(hex_val)
        if new_color.isValid() and new_color != self._current_color:
            self._current_color = new_color
            self._update_ui_from_color(self._current_color, source="hex_input")
            self.final_color_selected.emit(self._current_color)
        elif not new_color.isValid(): self.hex_input.setText(self._current_color.name())

    def _update_ui_from_color(self, color: QColor, source: str):
        print(f"DEBUG CPM: _update_ui_from_color CALLED. Source: '{source}', Color: {color.name()}") # 1. Is method called with correct color?

        # Update preview box
        # ... (this part seems to work if your main preview box updates)

        # Update RGB inputs
        if source != "rgb_input":
            r_text = str(color.red())
            g_text = str(color.green())
            b_text = str(color.blue())
            print(f"DEBUG CPM: Preparing to set RGB text: R='{r_text}', G='{g_text}', B='{b_text}'") # 2. Are correct strings prepared?
            
            self.r_input.setText(r_text)
            self.g_input.setText(g_text)
            self.b_input.setText(b_text)
            print(f"DEBUG CPM: AFTER setText - R.text()='{self.r_input.text()}', G.text()='{self.g_input.text()}', B.text()='{self.b_input.text()}'") # 3. What's their text immediately after?
        else:
            print(f"DEBUG CPM: Skipping RGB input update because source is '{source}'")

        # Update Hex input
        if source != "hex_input":
            hex_text = color.name().upper()
            print(f"DEBUG CPM: Preparing to set Hex text: HEX='{hex_text}'") # 4. Is correct string prepared?

            self.hex_input.setText(hex_text)
            print(f"DEBUG CPM: AFTER setText - HEX.text()='{self.hex_input.text()}'") # 5. What's its text immediately after?
        else:
            print(f"DEBUG CPM: Skipping Hex input update because source is '{source}'")

        # ... (rest of the method updating SV/Hue pickers - this seems to work if sliders move correctly)
        
    def _on_swatch_clicked(self, swatch_button: 'ColorSwatchButton'):
        color_hex = swatch_button.get_color_hex()
        is_placeholder_empty_color = color_hex.upper() == "#000000" or color_hex.upper() == "#1C1C1C"
        if color_hex and QColor(color_hex).isValid() and not is_placeholder_empty_color:
            self.set_current_selected_color(QColor(color_hex), "swatch_click")

    def _show_swatch_context_menu(self, swatch_button: 'ColorSwatchButton', swatch_index: int, global_pos: QPoint):
        menu = QMenu(self)
        current_swatch_color_hex = self.saved_colors_hex[swatch_index]
        is_swatch_set_meaningfully = current_swatch_color_hex is not None and \
                                     QColor(current_swatch_color_hex).isValid() and \
                                     current_swatch_color_hex.upper() != "#000000" and \
                                     current_swatch_color_hex.upper() != "#1C1C1C"

        if is_swatch_set_meaningfully:
            select_action = QAction(f"Select Color ({current_swatch_color_hex.upper()})", self)
            select_action.triggered.connect(lambda: self._on_swatch_clicked(swatch_button))
            menu.addAction(select_action)
            
            # Use the class attribute for the icon/emoji prefix
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
            self._update_swatch_buttons_display() # Update all swatches to reflect change
            self.save_color_picker_swatches_to_config()
            self.status_message_requested.emit(f"Swatch {swatch_index + 1} cleared.", 1500)

    def _add_current_color_to_specific_swatch(self, swatch_index: int):
        if 0 <= swatch_index < MAX_SAVED_COLORS:
            color_to_add = self._current_color.name()
            self.saved_colors_hex[swatch_index] = color_to_add
            self._update_swatch_buttons_display() # Update all swatches
            self.save_color_picker_swatches_to_config()
            self.status_message_requested.emit(f"Color {color_to_add.upper()} added to swatch {swatch_index + 1}.", 2000)

    def _add_current_color_to_swatches(self):
        try_index = -1
        for i, color_hex in enumerate(self.saved_colors_hex):
            is_placeholder_empty_color = color_hex is None or \
                                         color_hex.upper() == "#000000" or \
                                         color_hex.upper() == "#1C1C1C"
            if is_placeholder_empty_color:
                try_index = i; break
        if try_index == -1: try_index = 0; self.status_message_requested.emit("All swatches full. Overwriting first swatch.", 2000)
        self._add_current_color_to_specific_swatch(try_index)

    def _clear_all_swatches(self):
        for i in range(MAX_SAVED_COLORS): self.saved_colors_hex[i] = None
        self._update_swatch_buttons_display()
        self.save_color_picker_swatches_to_config()
        self.status_message_requested.emit("All color swatches cleared.", 2000)

    def set_current_selected_color(self, color: QColor, source="external"):
        if color.isValid() and color != self._current_color:
            self._current_color = QColor(color); self._update_ui_from_color(self._current_color, source=source)
            self.final_color_selected.emit(self._current_color)

    def get_current_color(self) -> QColor: return QColor(self._current_color)
    def set_enabled(self, enabled:bool): super().setEnabled(enabled)

    def load_color_picker_swatches_from_config(self):
        config_file = self._get_config_file_path()
        if not os.path.exists(config_file): self._update_swatch_buttons_display(); return
        try:
            with open(config_file, "r") as f: data = json.load(f)
            loaded_swatches = data.get(CONFIG_KEY_SAVED_COLORS, [])
            for i in range(MAX_SAVED_COLORS):
                if i < len(loaded_swatches) and loaded_swatches[i] and QColor(loaded_swatches[i]).isValid():
                    self.saved_colors_hex[i] = QColor(loaded_swatches[i]).name()
                else: self.saved_colors_hex[i] = None
            self._update_swatch_buttons_display()
        except Exception as e:
            print(f"ColorPickerManager: Error loading/parsing swatches from {config_file}: {e}")
            self._update_swatch_buttons_display() # Ensure UI shows default/empty state

    def save_color_picker_swatches_to_config(self):
        config_file = self._get_config_file_path()
        os.makedirs(os.path.dirname(config_file), exist_ok=True)
        swatches_to_save = [s if s is not None else "#000000" for s in self.saved_colors_hex] # Save None as black
        try:
            full_config_data = {}
            if os.path.exists(config_file):
                with open(config_file, "r") as f:
                    try: full_config_data = json.load(f)
                    except json.JSONDecodeError: full_config_data = {}
            if not isinstance(full_config_data, dict): full_config_data = {}
            full_config_data[CONFIG_KEY_SAVED_COLORS] = swatches_to_save
            with open(config_file, "w") as f: json.dump(full_config_data, f, indent=4)
        except Exception as e:
            print(f"ColorPickerManager: Error saving swatches to {config_file}: {e}")
            if hasattr(self, 'status_message_requested'): # Check if signal exists (for standalone test)
                self.status_message_requested.emit("Error saving color swatches.", 3000)

    def _update_swatch_buttons_display(self):
        for i, swatch_button in enumerate(self.saved_color_buttons):
            color_hex = self.saved_colors_hex[i]
            is_valid_color_for_display = color_hex and QColor(color_hex).isValid() and \
                                         color_hex.upper() != "#000000" and \
                                         color_hex.upper() != "#1C1C1C" # Visual empty
            if is_valid_color_for_display:
                swatch_button.set_color(color_hex)
                swatch_button.setToolTip(f"{color_hex.upper()}. Click to select, Right-click to manage.")
            else:
                swatch_button.set_color("#1C1C1C") 
                swatch_button.setToolTip("Empty swatch. Right-click to set, or use 'Add' button.")

class ColorSwatchButton(QPushButton): # Definition moved here for forward reference
    rightClicked = pyqtSignal(QPoint) 

    def __init__(self, initial_color_hex="#1C1C1C", parent=None): # Default to visual empty
        super().__init__(parent)
        self.setFixedSize(30, 30)
        self._hex_color = "#1C1C1C" # Initialize internal hex
        self.set_color(initial_color_hex) # Apply initial color (might be different)
        self.setToolTip("Empty swatch. Right-click to set, or use 'Add' button.")

    def set_color(self, hex_color_str):
        q_color = QColor(hex_color_str)
        self._hex_color = q_color.name() if q_color.isValid() else "#1C1C1C" # Fallback to visual empty
        
        # Directly set stylesheet for background color
        # Add other base styles you want for these buttons if they are lost
        self.setStyleSheet(f"QPushButton {{ background-color: {self._hex_color}; border: 1px solid #555; /* Add other base styles if needed */ }}")
        # self.setAutoFillBackground(False) # May not be needed if stylesheet sets background
        self.update()

    def get_color_hex(self):
        return self._hex_color

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.RightButton:
            self.rightClicked.emit(event.globalPosition().toPoint())
        else:
            super().mousePressEvent(event)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    def _get_dev_config_path_cpm(filename): return os.path.join(os.getcwd(), filename) 
    picker_manager = ColorPickerManager(config_save_path_func=_get_dev_config_path_cpm)
    picker_manager.final_color_selected.connect(lambda c: print(f"Test: Color selected: {c.name()}"))
    picker_manager.status_message_requested.connect(lambda msg, time: print(f"Test: Status - {msg} ({time}ms)"))
    picker_manager.show()
    app.aboutToQuit.connect(picker_manager.save_color_picker_swatches_to_config) 
    sys.exit(app.exec())
