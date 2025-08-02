# AKAI_Fire_RGB_Controller/gui/color_picker_manager.py
import json
import os
import sys
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QGridLayout,
    QGroupBox, QLineEdit, QMenu, QApplication, QSizePolicy, QToolTip
)
from PyQt6.QtGui import QColor, QIntValidator, QMouseEvent, QAction, QIcon, QPainter
from PyQt6.QtCore import Qt, pyqtSignal, QPoint, QEvent

from .sv_picker import SVPicker
from .hue_slider import HueSlider

# --- Constants ---
MAX_SAVED_COLORS = 16 # 2 rows of 8 --- MY_COLORS "My Colors"
CONFIG_FILE_NAME = "fire_controller_config.json"
CONFIG_KEY_SAVED_COLORS = "color_picker_swatches"

# =================================================================================
#  HELPER WIDGET: ClickableColorLabel
# =================================================================================


class ClickableColorLabel(QLabel):
    """A QLabel that emits a 'clicked' signal and can display a color background."""
    clicked = pyqtSignal()

    def __init__(self, color_name: str, parent=None):
        super().__init__(parent)
        self.setObjectName(f"ColorWellLabel_{color_name}")
        self.setFixedSize(32, 32)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)

# =================================================================================
#  HELPER WIDGET: PrimarySecondaryColorWell
# =================================================================================


class PrimarySecondaryColorWell(QWidget):
    """
    A widget to display and manage the primary/secondary color selection wells,
    inspired by the Paint.NET color picker.
    """
    active_well_changed = pyqtSignal(str)
    swap_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._active_well = 'primary'
        self._init_ui()
        self._connect_signals()
        self.update_active_border()

    def _init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        well_container = QWidget()
        well_container.setFixedSize(48, 48)
        self.secondary_well = ClickableColorLabel(
            'secondary', parent=well_container)
        self.secondary_well.move(12, 12)
        self.secondary_well.setToolTip(
            "Secondary Color (for Right-Click painting)")
        self.primary_well = ClickableColorLabel(
            'primary', parent=well_container)
        self.primary_well.move(4, 4)
        self.primary_well.setToolTip("Primary Color (for Left-Click painting)")
        self.swap_button = QPushButton("⇄")
        self.swap_button.setObjectName("ColorSwapButton")
        self.swap_button.setStyleSheet("font-size: 14pt;")
        self.swap_button.setFixedSize(32, 24)
        self.swap_button.setToolTip("Swap Colors")
        # Install the event filter on the button we want to control
        self.swap_button.installEventFilter(self)
        layout.addWidget(well_container)
        layout.addWidget(self.swap_button, 0, Qt.AlignmentFlag.AlignVCenter)

    def eventFilter(self, obj, event: QEvent) -> bool:
        """
        Catches the ToolTip event for the swap button to show a custom-styled tooltip.
        """
        if obj == self.swap_button and event.type() == QEvent.Type.ToolTip:
            # Create a rich-text tooltip with forced styling
            tooltip_html = f"<div style='font-size: 9pt; background-color: #383838; color: #E0E0E0; border: 1px solid #505050; padding: 4px; border-radius: 3px;'>{self.swap_button.toolTip()}</div>"
            QToolTip.showText(event.globalPos(),
                                tooltip_html, self.swap_button)
            return True  # Event handled, don't show the default tooltip
        return super().eventFilter(obj, event)

    def _connect_signals(self):
        self.primary_well.clicked.connect(
            lambda: self.active_well_changed.emit('primary'))
        self.secondary_well.clicked.connect(
            lambda: self.active_well_changed.emit('secondary'))
        self.swap_button.clicked.connect(self.swap_requested)

    def set_primary_color(self, color: QColor):
        self.primary_well.setStyleSheet(
            f"background-color: {color.name()}; border: 1px solid #111;")

    def set_secondary_color(self, color: QColor):
        self.secondary_well.setStyleSheet(
            f"background-color: {color.name()}; border: 1px solid #111;")

    def set_active_well(self, well_name: str):
        if well_name in ['primary', 'secondary']:
            self._active_well = well_name
            self.update_active_border()

    def update_active_border(self):
        """Applies a highlight border to the active color well."""
        active_style = "border: 2px solid #60a0ff;"
        inactive_style = "border: 1px solid #777;"
        # Get the current stylesheet but remove any previous border rules
        # to prevent them from stacking up.
        primary_base_style = self.primary_well.styleSheet().split('border:')[0]
        secondary_base_style = self.secondary_well.styleSheet().split('border:')[
            0]
        if self._active_well == 'primary':
            self.primary_well.setStyleSheet(primary_base_style + active_style)
            self.secondary_well.setStyleSheet(
                secondary_base_style + inactive_style)
        else:
            self.primary_well.setStyleSheet(
                primary_base_style + inactive_style)
            self.secondary_well.setStyleSheet(
                secondary_base_style + active_style)

# =================================================================================
#  MAIN CLASS: ColorPickerManager
# =================================================================================

class ColorPickerManager(QGroupBox):
    # --- Class Icons & Constants ---
    ICON_ADD_SWATCH_COLOR = "➕"
    ICON_CLEAR_ALL_SWATCHES = "🗑️"
    ICON_MENU_DELETE = "🗑️"
    ICON_MENU_SET_COLOR = "🎨"
    # --- Signals ---
    primary_color_changed = pyqtSignal(QColor)
    secondary_color_changed = pyqtSignal(QColor)
    status_message_requested = pyqtSignal(str, int)
    request_clear_all_pads = pyqtSignal()
    eyedropper_button_toggled = pyqtSignal(bool)

    # --- Initialization ---

    def __init__(self, initial_color=QColor("#04FF00"), parent_group_title="🎨 Color Picker", config_save_path_func=None):
        super().__init__(parent_group_title)
        self.config_save_path_func = config_save_path_func
        self.setObjectName("ColorPickerManagerGroup")

        # State Attributes
        self._primary_color = QColor(initial_color)
        self._secondary_color = QColor("black")
        self._active_well = 'primary'
        self.saved_colors_hex: list[str | None] = [None] * MAX_SAVED_COLORS

        # UI Widget Attributes
        self.color_well = PrimarySecondaryColorWell()
        self.sv_picker = SVPicker()
        self.hue_slider = HueSlider()
        self.r_input = QLineEdit()
        self.g_input = QLineEdit()
        self.b_input = QLineEdit()
        self.hex_input = QLineEdit(objectName="HexColorInputLineEdit")
        self.eyedropper_button = QPushButton("💧")
        self.set_black_button = QPushButton("Set to Black")
        self.clear_pads_button = QPushButton("Clear All Pads")
        self.add_saved_color_button = QPushButton(
            f"{self.ICON_ADD_SWATCH_COLOR} Add")
        self.clear_swatches_button = QPushButton(
            f"{self.ICON_CLEAR_ALL_SWATCHES} Clear All")
        self.saved_color_buttons: list['ColorSwatchButton'] = []
        # Initialize
        self._init_ui()
        self._connect_signals()
        self.load_color_picker_swatches_from_config()
        # On startup, update all UI components to reflect the initial active color.
        self._update_text_inputs_from_color(self._primary_color)
        self._update_color_wells_display()
        self._update_pickers_from_color(self._primary_color)


    # --- UI Creation ---
    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(10)
        # --- Top Row: Color Wells & Input Fields ---
        top_controls_layout = QHBoxLayout()
        top_controls_layout.setSpacing(10)
        # Left side: Primary/Secondary color wells
        top_controls_layout.addWidget(self.color_well)
        # Right side: RGB/Hex/Eyedropper inputs in a vertical group
        input_fields_layout = QVBoxLayout()
        input_fields_layout.setSpacing(6)
        # RGB Inputs
        rgb_group_layout = QHBoxLayout()
        rgb_group_layout.setSpacing(5)
        int_validator = QIntValidator(0, 255, self)
        for label, qle in [("R:", self.r_input), ("G:", self.g_input), ("B:", self.b_input)]:
            rgb_group_layout.addWidget(QLabel(label))
            qle.setValidator(int_validator)
            qle.setFixedWidth(38)
            qle.setAlignment(Qt.AlignmentFlag.AlignCenter)
            rgb_group_layout.addWidget(qle)
            if label != "B:":
                rgb_group_layout.addStretch()
        self.r_input.setToolTip("Red component (0-255)")
        self.g_input.setToolTip("Green component (0-255)")
        self.b_input.setToolTip("Blue component (0-255)")
        input_fields_layout.addLayout(rgb_group_layout)
        # Hex Input & Eyedropper
        hex_eyedropper_layout = QHBoxLayout()
        hex_eyedropper_layout.setSpacing(5)
        hex_eyedropper_layout.addWidget(QLabel("Hex:"))
        self.hex_input.setFixedWidth(75)
        self.hex_input.setMaxLength(7)
        self.hex_input.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.hex_input.setToolTip("Hexadecimal color code (#RRGGBB)")
        self.eyedropper_button.setObjectName("EyedropperToolButton")
        self.eyedropper_button.setToolTip(
            "Toggle Eyedropper mode (I): Click a pad to pick its color.")
        self.eyedropper_button.setCheckable(True)
        hex_eyedropper_layout.addWidget(self.hex_input)
        hex_eyedropper_layout.addStretch()  # <-- MOVED STRETCH HERE
        hex_eyedropper_layout.addWidget(self.eyedropper_button)
        input_fields_layout.addLayout(hex_eyedropper_layout)
        top_controls_layout.addLayout(input_fields_layout, 1)
        main_layout.addLayout(top_controls_layout)
        # --- Middle Row: SV Picker and Hue Slider ---
        pickers_layout = QHBoxLayout()
        pickers_layout.setSpacing(6)
        pickers_layout.addWidget(self.sv_picker, 3)
        pickers_layout.addWidget(self.hue_slider, 1)
        main_layout.addLayout(pickers_layout)
        # --- "My Colors" Swatches Group ---
        my_colors_group = QGroupBox("My Colors")
        my_colors_layout = QVBoxLayout(my_colors_group)
        my_colors_layout.setSpacing(8)
        swatches_grid_layout = QGridLayout()
        swatches_grid_layout.setSpacing(5)
        for i in range(MAX_SAVED_COLORS):
            row, col = divmod(i, 8)
            swatch = ColorSwatchButton(parent=self)
            swatch.clicked.connect(
                lambda _, s=swatch: self._on_swatch_clicked(s))
            swatch.rightClicked.connect(
                lambda pos, s=swatch, idx=i: self._show_swatch_context_menu(s, idx, pos))
            self.saved_color_buttons.append(swatch)
            swatches_grid_layout.addWidget(swatch, row, col)
        my_colors_layout.addLayout(swatches_grid_layout)
        my_colors_layout.addSpacing(10)  # Adds pixels of vertical padding
        my_colors_buttons_layout = QHBoxLayout()
        self.add_saved_color_button.setToolTip(
            "Add active color to an empty swatch.")
        self.clear_swatches_button.setToolTip(
            "Clear all saved color swatches.")
        my_colors_buttons_layout.addStretch()
        my_colors_buttons_layout.addWidget(self.add_saved_color_button)
        my_colors_buttons_layout.addWidget(self.clear_swatches_button)
        my_colors_layout.addLayout(my_colors_buttons_layout)
        main_layout.addWidget(my_colors_group)
        # --- Bottom Section: Tool Buttons ---
        action_tools_layout = QHBoxLayout()
        action_tools_layout.setSpacing(6)
        self.set_black_button.setToolTip("Set active color to Black (Off).")
        self.clear_pads_button.setToolTip("Clear all pads to Black.")
        action_tools_layout.addWidget(self.set_black_button)
        action_tools_layout.addStretch()
        action_tools_layout.addWidget(self.clear_pads_button)
        main_layout.addLayout(action_tools_layout)

    # --- Signal Connections ---
    def _connect_signals(self):
        # Primary/Secondary color well signals
        self.color_well.active_well_changed.connect(
            self._handle_active_well_changed)
        self.color_well.swap_requested.connect(self._handle_swap_requested)
        self.sv_picker.sv_changed.connect(self._on_sv_changed)
        self.hue_slider.hue_changed.connect(self._on_hue_changed)
        # Input field signals
        self.r_input.editingFinished.connect(self._on_rgb_hex_input_changed)
        self.g_input.editingFinished.connect(self._on_rgb_hex_input_changed)
        self.b_input.editingFinished.connect(self._on_rgb_hex_input_changed)
        self.hex_input.editingFinished.connect(self._on_rgb_hex_input_changed)
        # Tool button signals
        self.eyedropper_button.toggled.connect(self.eyedropper_button_toggled)
        self.set_black_button.clicked.connect(self._handle_set_black_request)
        self.clear_pads_button.clicked.connect(self.request_clear_all_pads)
        # Swatch management signals
        self.add_saved_color_button.clicked.connect(
            self._add_current_color_to_swatches)
        self.clear_swatches_button.clicked.connect(self._clear_all_swatches)

    # --- Core Logic & Event Handlers (Final Architecture) ---

    def _on_sv_changed(self, s: float, v: float):
        """Handles changes from the SV-Picker. Updates text inputs but not other pickers."""
        # Get hue from the slider to build the complete color
        h = self.hue_slider.get_hue() / 360.0
        new_color = QColor.fromHsvF(h, s, v, 1.0)

        # Update the internal color state and emit the signal for MainWindow
        if self._active_well == 'primary':
            self._primary_color = new_color
            self.primary_color_changed.emit(new_color)
        else:
            self._secondary_color = new_color
            self.secondary_color_changed.emit(new_color)

        # Update only the dependent UI elements, NOT the source (sv_picker) or the hue_slider
        self._update_text_inputs_from_color(new_color)
        self._update_color_wells_display()

    def _on_hue_changed(self, hue_degrees: int):
        """Handles changes from the Hue Slider. Updates the SV-Picker's gradient and text inputs."""
        # Get S and V from the picker to build the complete color
        s = self.sv_picker.saturation()
        v = self.sv_picker.value()
        new_color = QColor.fromHsvF(hue_degrees / 360.0, s, v, 1.0)

        # Update the internal color state and emit the signal
        if self._active_well == 'primary':
            self._primary_color = new_color
            self.primary_color_changed.emit(new_color)
        else:
            self._secondary_color = new_color
            self.secondary_color_changed.emit(new_color)

        # Update the SV-Picker's background gradient to the new hue
        self.sv_picker.setHue(hue_degrees)

        # Update other dependent UI elements
        self._update_text_inputs_from_color(new_color)
        self._update_color_wells_display()

    def _on_rgb_hex_input_changed(self):
        """Handles changes from text inputs. This is a master override for the pickers."""
        new_color = QColor()
        current_active_color = self._primary_color if self._active_well == 'primary' else self._secondary_color
        if self.sender() == self.hex_input:
            hex_val = self.hex_input.text()
            if not hex_val.startswith("#"):
                hex_val = "#" + hex_val
            new_color.setNamedColor(hex_val)
        else:  # RGB input
            try:
                r = int(self.r_input.text() or "0")
                g = int(self.g_input.text() or "0")
                b = int(self.b_input.text() or "0")
                new_color.setRgb(max(0, min(r, 255)), max(
                    0, min(g, 255)), max(0, min(b, 255)))
            except ValueError:
                self._update_text_inputs_from_color(current_active_color)
                return
        if not new_color.isValid():
            self._update_text_inputs_from_color(current_active_color)
            return
        # Set internal color and emit
        if self._active_well == 'primary':
            self._primary_color = new_color
            self.primary_color_changed.emit(new_color)
        else:
            self._secondary_color = new_color
            self.secondary_color_changed.emit(new_color)
        # Update all other UI elements, including the pickers
        self._update_text_inputs_from_color(new_color)
        self._update_color_wells_display()
        self._update_pickers_from_color(new_color)

    def _handle_active_well_changed(self, well_name: str):
        """Handles user clicking on the primary or secondary color well."""
        if self._active_well != well_name:
            self._active_well = well_name
            self.color_well.set_active_well(well_name)
            # Update all controls to reflect the newly active color
            active_color = self._primary_color if self._active_well == 'primary' else self._secondary_color
            self._update_text_inputs_from_color(active_color)
            self._update_pickers_from_color(active_color)
            self.status_message_requested.emit(
                f"Active color set to: {well_name.capitalize()}", 2000)

    def _handle_swap_requested(self):
        """Swaps the primary and secondary colors and updates all UI."""
        self._primary_color, self._secondary_color = self._secondary_color, self._primary_color
        self.primary_color_changed.emit(self._primary_color)
        self.secondary_color_changed.emit(self._secondary_color)
        # Force a full UI refresh based on the now-active color
        active_color = self._primary_color if self._active_well == 'primary' else self._secondary_color
        self._update_text_inputs_from_color(active_color)
        self._update_color_wells_display()
        self._update_pickers_from_color(active_color)
        self.status_message_requested.emit(
            "Swapped primary and secondary colors.", 2000)

    def _handle_set_black_request(self):
        """Sets the currently active color to black and updates all UI."""
        black_color = QColor("black")
        if self._active_well == 'primary':
            self._primary_color = black_color
            self.primary_color_changed.emit(black_color)
        else:
            self._secondary_color = black_color
            self.secondary_color_changed.emit(black_color)
        self._update_text_inputs_from_color(black_color)
        self._update_color_wells_display()
        self._update_pickers_from_color(black_color)

    def _update_color_wells_display(self):
        """Helper to update the primary/secondary color wells."""
        self.color_well.set_primary_color(self._primary_color)
        self.color_well.set_secondary_color(self._secondary_color)
        self.color_well.update_active_border()

    def _update_text_inputs_from_color(self, color: QColor):
        """Helper to update RGB/Hex inputs with signal blocking."""
        self.r_input.blockSignals(True)
        self.g_input.blockSignals(True)
        self.b_input.blockSignals(True)
        self.hex_input.blockSignals(True)
        self.r_input.setText(str(color.red()))
        self.g_input.setText(str(color.green()))
        self.b_input.setText(str(color.blue()))
        self.hex_input.setText(color.name().upper())
        self._style_hex_input(color)
        self.r_input.blockSignals(False)
        self.g_input.blockSignals(False)
        self.b_input.blockSignals(False)
        self.hex_input.blockSignals(False)

    def _update_pickers_from_color(self, color: QColor):
        """Helper to update the SV-Picker and Hue Slider with signal blocking."""
        h, s, v, _ = color.getHsvF()
        self.hue_slider.blockSignals(True)
        self.sv_picker.blockSignals(True)
        self.hue_slider.set_hue(int(h * 359.99), emit_signal=False)
        self.sv_picker.setHue(int(h * 359.99))
        self.sv_picker.setSV(s, v)
        self.hue_slider.blockSignals(False)
        self.sv_picker.blockSignals(False)

    def _style_hex_input(self, color: QColor):
        """Sets the background/foreground color of the Hex input field for readability."""
        if not self.hex_input or not color.isValid():
            return
        luminance = (0.299 * color.redF() + 0.587 *
                     color.greenF() + 0.114 * color.blueF())
        text_color = "#000000" if luminance > 0.5 else "#FFFFFF"
        self.hex_input.setStyleSheet(
            f"background-color: {color.name()}; color: {text_color};")

    # --- Swatch Management ---
    def _on_swatch_clicked(self, swatch_button: 'ColorSwatchButton'):
        """Sets the active color to the one clicked in the swatch."""
        color_hex = swatch_button.get_color_hex()
        if not QColor(color_hex).isValid() or swatch_button.is_empty:
            return
        new_color = QColor(color_hex)
        # Update the internal color state and emit the signal directly,
        # just like the other event handlers do.
        if self._active_well == 'primary':
            if self._primary_color == new_color:
                return
            self._primary_color = new_color
            self.primary_color_changed.emit(new_color)
        else:  # 'secondary'
            if self._secondary_color == new_color:
                return
            self._secondary_color = new_color
            self.secondary_color_changed.emit(new_color)
        # Manually update all other dependent UI controls to reflect the change.
        self._update_text_inputs_from_color(new_color)
        self._update_color_wells_display()
        self._update_pickers_from_color(new_color)

    def _show_swatch_context_menu(self, swatch_button: 'ColorSwatchButton', swatch_index: int, global_pos: QPoint):
        menu = QMenu(self)
        if not swatch_button.is_empty:
            color_hex = self.saved_colors_hex[swatch_index]
            select_action = QAction(
                f"Select Color ({color_hex.upper()})", self)
            select_action.triggered.connect(
                lambda: self._on_swatch_clicked(swatch_button))
            menu.addAction(select_action)

            delete_action = QAction(
                f"{self.ICON_MENU_DELETE} Clear This Swatch", self)
            delete_action.triggered.connect(
                lambda: self._clear_single_swatch(swatch_index))
            menu.addAction(delete_action)
        else:
            set_action = QAction(
                f"{self.ICON_MENU_SET_COLOR} Set to Active Color", self)
            set_action.triggered.connect(
                lambda: self._add_current_color_to_specific_swatch(swatch_index))
            menu.addAction(set_action)
        menu.exec(global_pos)

    def _clear_single_swatch(self, swatch_index: int):
        self.saved_colors_hex[swatch_index] = None
        self._update_swatch_buttons_display()
        self.save_color_picker_swatches_to_config()
        self.status_message_requested.emit(
            f"Swatch {swatch_index + 1} cleared.", 1500)

    def _add_current_color_to_specific_swatch(self, swatch_index: int):
        active_color = self._primary_color if self._active_well == 'primary' else self._secondary_color
        self.saved_colors_hex[swatch_index] = active_color.name()
        self._update_swatch_buttons_display()
        self.save_color_picker_swatches_to_config()
        self.status_message_requested.emit(
            f"Color {active_color.name().upper()} added to swatch {swatch_index + 1}.", 2000)

    def _add_current_color_to_swatches(self):
        """Adds the active color to the first available swatch."""
        try:
            # Find the first index that is None
            first_empty_index = self.saved_colors_hex.index(None)
            self._add_current_color_to_specific_swatch(first_empty_index)
        except ValueError:
            self.status_message_requested.emit(
                "All color swatches are full.", 2000)

    def _clear_all_swatches(self):
        self.saved_colors_hex = [None] * MAX_SAVED_COLORS
        self._update_swatch_buttons_display()
        self.save_color_picker_swatches_to_config()
        self.status_message_requested.emit("All color swatches cleared.", 2000)

    def _update_swatch_buttons_display(self):
        for i, swatch_button in enumerate(self.saved_color_buttons):
            color_hex = self.saved_colors_hex[i]
            if color_hex and QColor(color_hex).isValid():
                swatch_button.set_color(color_hex)
            else:
                swatch_button.set_empty()

    # --- Configuration Management ---
    def _get_config_file_path(self):
        # This helper function for determining the config path remains unchanged.
        if self.config_save_path_func:
            return self.config_save_path_func(CONFIG_FILE_NAME)
        else:
            try:
                current_file_dir = os.path.dirname(os.path.abspath(__file__))
                project_root = os.path.dirname(current_file_dir)
            except NameError:
                project_root = os.getcwd()
            fallback_dir = os.path.join(
                project_root, "user_settings_fallback_cpm")
            os.makedirs(fallback_dir, exist_ok=True)
            return os.path.join(fallback_dir, CONFIG_FILE_NAME)

    def load_color_picker_swatches_from_config(self):
        config_file = self._get_config_file_path()
        if not os.path.exists(config_file):
            self._update_swatch_buttons_display()
            return
        try:
            with open(config_file, "r") as f:
                data = json.load(f)
            loaded_swatches = data.get(CONFIG_KEY_SAVED_COLORS, [])
            num_to_load = min(len(loaded_swatches), MAX_SAVED_COLORS)
            self.saved_colors_hex = [None] * MAX_SAVED_COLORS
            for i in range(num_to_load):
                if loaded_swatches[i] and QColor(loaded_swatches[i]).isValid():
                    self.saved_colors_hex[i] = QColor(
                        loaded_swatches[i]).name()
            self._update_swatch_buttons_display()
        except Exception as e:
            print(f"ColorPickerManager: Error loading swatches: {e}")
            self.saved_colors_hex = [None] * MAX_SAVED_COLORS
            self._update_swatch_buttons_display()

    def save_color_picker_swatches_to_config(self):
        config_file = self._get_config_file_path()
        os.makedirs(os.path.dirname(config_file), exist_ok=True)
        try:
            full_config_data = {}
            if os.path.exists(config_file):
                with open(config_file, "r") as f:
                    try:
                        full_config_data = json.load(f)
                    except json.JSONDecodeError:
                        full_config_data = {}
            if not isinstance(full_config_data, dict):
                full_config_data = {}
            full_config_data[CONFIG_KEY_SAVED_COLORS] = self.saved_colors_hex
            with open(config_file, "w") as f:
                json.dump(full_config_data, f, indent=4)
        except Exception as e:
            print(f"ColorPickerManager: Error saving swatches: {e}")

    # --- Public API for MainWindow ---
    def get_primary_color(self) -> QColor:
        return QColor(self._primary_color)

    def get_secondary_color(self) -> QColor:
        return QColor(self._secondary_color)

    def set_active_color_from_eyedropper(self, color: QColor):
        """Public method for MainWindow's eyedropper to set the active color."""
        if not color.isValid():
            return
        # Update the internal color state and emit the signal directly.
        if self._active_well == 'primary':
            if self._primary_color == color: return
            self._primary_color = color
            self.primary_color_changed.emit(color)
        else: # 'secondary'
            if self._secondary_color == color: return
            self._secondary_color = color
            self.secondary_color_changed.emit(color)
        # Manually update all other dependent UI controls to reflect the change.
        self._update_text_inputs_from_color(color)
        self._update_color_wells_display()
        self._update_pickers_from_color(color)

    def set_enabled(self, enabled: bool):
        super().setEnabled(enabled)

# =================================================================================
#  HELPER WIDGET: ColorSwatchButton
# =================================================================================

class ColorSwatchButton(QPushButton):
    rightClicked = pyqtSignal(QPoint)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("CustomSwatchButton")
        self.setFixedSize(28, 28)
        self.is_empty = True
        self.hex_color = "#1C1C1C"
        self.set_empty()
        # Install the event filter on the button itself
        self.installEventFilter(self)

    def eventFilter(self, obj, event: QEvent) -> bool:
        """
        Catches the ToolTip event for this swatch to show a custom-styled tooltip.
        """
        if event.type() == QEvent.Type.ToolTip:
            # Create a rich-text tooltip with forced styling
            tooltip_html = f"<div style='font-size: 9pt; background-color: #383838; color: #E0E0E0; border: 1px solid #505050; padding: 4px; border-radius: 3px;'>{self.toolTip()}</div>"
            QToolTip.showText(event.globalPos(), tooltip_html, self)
            return True  # Event handled, don't show the default tooltip
        return super().eventFilter(obj, event)

    def set_color(self, hex_color_str: str):
        self.is_empty = False
        self.hex_color = QColor(hex_color_str).name()
        self.setToolTip(
            f"{self.hex_color.upper()}. Click to select, Right-click to manage.")
        self.setStyleSheet(
            f"background-color: {self.hex_color}; border: 1px solid #555;")

    def set_empty(self):
        self.is_empty = True
        self.hex_color = "#1C1C1C"
        self.setToolTip(
            "Empty swatch. Right-click to set, or use 'Add' button.")
        self.setStyleSheet(
            "background-color: #1C1C1C; border: 1px dashed #666;")

    def get_color_hex(self) -> str:
        return self.hex_color

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.RightButton:
            self.rightClicked.emit(event.globalPosition().toPoint())
        else:
            super().mousePressEvent(event)
