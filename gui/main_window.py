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
from PyQt6.QtGui import QColor, QPalette, QRegularExpressionValidator, QAction, QMouseEvent

# Assuming hue_slider.py and sv_picker.py are in the same 'gui' directory
from .hue_slider import HueSlider
from .sv_picker import SVPicker
# Assuming akai_fire_controller.py is in 'hardware' subdirectory relative to project root
from hardware.akai_fire_controller import AkaiFireController

# --- Tweakable Constants ---
INITIAL_WINDOW_WIDTH = 1050
INITIAL_WINDOW_HEIGHT = 750 
PAD_BUTTON_WIDTH = 30
PAD_BUTTON_HEIGHT = 40
PAD_GRID_SPACING = 3
CUSTOM_SWATCH_SIZE = 32
# ---

CONFIG_FILE_NAME = "fire_controller_config.json" # For color picker custom swatches
PREFAB_STATIC_PRESETS_DIR = os.path.join("presets", "static")
USER_PRESETS_DIR = os.path.join("presets", "user")


# --- Custom PadButton Class ---
class PadButton(QPushButton):
    request_paint_on_press = pyqtSignal(int, int) 

    def __init__(self, row, col, parent=None):
        super().__init__(parent)
        self.row = row
        self.col = col
        self.setObjectName("PadButton")
        self.setFixedSize(PAD_BUTTON_WIDTH, PAD_BUTTON_HEIGHT)
        self.setCheckable(False)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed) # Explicitly Fixed

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self.request_paint_on_press.emit(self.row, self.col)
        super().mousePressEvent(event)
# --- END OF PadButton Class ---


class MainWindow(QMainWindow):
    final_color_selected_signal = pyqtSignal(QColor)

    def __init__(self):
        super().__init__()
        print("--- MainWindow __init__ STARTED ---") # DEBUG PRINT
        self.setWindowTitle("AKAI Fire RGB Controller - Refined UI v2")
        self.setGeometry(100, 100, INITIAL_WINDOW_WIDTH, INITIAL_WINDOW_HEIGHT)

        self.akai_controller = AkaiFireController(auto_connect=False)
        self.pad_buttons = {}

        self._current_h_int = 0     # 0-359 (authoritative internal hue for pickers)
        self._current_s_float = 1.0 # 0.0-1.0
        self._current_v_float = 1.0 # 0.0-1.0
        # selected_qcolor is the color to be applied to pads
        self.selected_qcolor = QColor.fromHsvF(self._current_h_int / 360.0, self._current_s_float, self._current_v_float)

        self.hue_slider_widget, self.sv_picker_widget = None, None
        self.r_input, self.g_input, self.b_input = None, None, None
        self.h_input, self.s_input, self.v_input = None, None, None
        self.hex_input_lineedit = None
        self.main_color_preview_swatch = None
        self.custom_swatch_buttons = []
        self.num_custom_swatches = 16 
        self.swatches_per_row = 8

        self._block_ui_updates = False
        self.is_drawing_with_left_button_down = False
        self._last_painted_pad_on_drag = None

        self.static_presets_combo = None
        self.loaded_static_presets = {}
        self.animation_timer = QTimer(self)
        self.animation_timer.timeout.connect(self.next_animation_frame_slot)
        self.current_animation_name = None
        self.current_animation_frames = []
        self.current_animation_frame_index = 0
        self.current_animation_delay = 100

        self.ensure_user_presets_dir_exists()
        self.init_ui()
        self.update_connection_status()
        self.populate_midi_ports()
        
        self.final_color_selected_signal.connect(self.handle_final_color_selection)
        self.load_color_picker_swatches_from_config() 
        self.load_all_static_pad_layouts()    
        
        print("--- MainWindow __init__: Initializing UI color picker ---")
        self._update_all_color_ui_elements(self.selected_qcolor, "init")
        print("--- MainWindow __init__ FINISHED ---")


    def ensure_user_presets_dir_exists(self):
        base_path = os.path.dirname(os.path.abspath(sys.argv[0])) 
        path_to_check = os.path.join(base_path, USER_PRESETS_DIR)
        if not os.path.exists(path_to_check):
            try:
                os.makedirs(path_to_check)
                # print(f"Created directory: {path_to_check}") 
            except Exception as e:
                print(f"Error creating user presets directory {path_to_check}: {e}")


    def init_ui(self):
        print("--- MainWindow init_ui STARTED ---") 
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_app_layout = QHBoxLayout(central_widget)
        main_app_layout.setSpacing(10)

        pad_grid_outer_container = QWidget() 
        pad_grid_container_layout = QVBoxLayout(pad_grid_outer_container) 
        pad_grid_container_layout.setContentsMargins(0,0,0,0)

        self.pad_grid_frame = QFrame() 
        self.pad_grid_frame.setObjectName("PadGridFrame")
        pad_grid_layout = QGridLayout()
        pad_grid_layout.setSpacing(PAD_GRID_SPACING) 
        pad_grid_layout.setContentsMargins(0, 0, 0, 0)  # Ensure no extra margins

        for i in range(16): pad_grid_layout.setColumnStretch(i, 0)
        for i in range(4): pad_grid_layout.setRowStretch(i, 0)
        for r_idx in range(4):
            for c_idx in range(16):
                pad_button = PadButton(row=r_idx, col=c_idx)
                pad_button.request_paint_on_press.connect(self.handle_pad_press_for_drawing)
                pad_button.clicked.connect(lambda checked=False, r=r_idx, c=c_idx: self.on_pad_single_clicked(r, c))
                pad_button.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
                pad_button.customContextMenuRequested.connect(
                    lambda pos, r=r_idx, c=c_idx: self.show_pad_context_menu(self.pad_buttons[(r,c)], r, c, pos)
                )
                self.pad_buttons[(r_idx, c_idx)] = pad_button
                pad_grid_layout.addWidget(pad_button, r_idx, c_idx)
                self.update_gui_pad_color(r_idx, c_idx, 0,0,0)
        
        self.pad_grid_frame.setLayout(pad_grid_layout)
        # --- Set fixed size for pad grid frame based on contents ---
        grid_width = (16 * PAD_BUTTON_WIDTH) + (15 * PAD_GRID_SPACING)
        grid_height = (4 * PAD_BUTTON_HEIGHT) + (3 * PAD_GRID_SPACING)
        self.pad_grid_frame.setFixedSize(grid_width, grid_height)
        # -----------------------------------------------------------
        self.pad_grid_frame.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Maximum)

        pad_grid_container_layout.addWidget(self.pad_grid_frame, 0, Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)
        pad_grid_container_layout.addStretch(1) 
        
        main_app_layout.addWidget(pad_grid_outer_container, 2) 

        controls_container = QWidget()
        controls_layout_main_v = QVBoxLayout(controls_container)
        controls_container.setMinimumWidth(420) 
        controls_container.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred) # Allow it to take preferred width

        connection_layout = QHBoxLayout()
        self.port_combo = QComboBox(); self.port_combo.setPlaceholderText("Select MIDI Port")
        self.connect_button = QPushButton("Connect"); self.connect_button.clicked.connect(self.toggle_connection)
        connection_layout.addWidget(QLabel("Port:")); connection_layout.addWidget(self.port_combo,1); connection_layout.addWidget(self.connect_button)
        controls_layout_main_v.addLayout(connection_layout)

        adv_color_picker_group = QGroupBox("Advanced Color Picker")
        adv_color_picker_group_layout = QHBoxLayout(adv_color_picker_group)
        self.sv_picker_widget = SVPicker(); self.sv_picker_widget.setMinimumSize(150,150)
        self.sv_picker_widget.sv_changed.connect(self.sv_picker_value_changed)
        adv_color_picker_group_layout.addWidget(self.sv_picker_widget, 1)
        self.hue_slider_widget = HueSlider(orientation=Qt.Orientation.Vertical)
        self.hue_slider_widget.setMinimumWidth(35)
        self.hue_slider_widget.hue_changed.connect(self.hue_slider_value_changed)
        adv_color_picker_group_layout.addWidget(self.hue_slider_widget)
        controls_layout_main_v.addWidget(adv_color_picker_group)

        numeric_preview_group = QGroupBox("Color Values & Preview")
        numeric_preview_layout = QGridLayout(numeric_preview_group)
        self.h_input = QLineEdit(); self.h_input.setValidator(QRegularExpressionValidator(QRegularExpression("[0-9]{1,3}")))
        self.s_input = QLineEdit(); self.s_input.setValidator(QRegularExpressionValidator(QRegularExpression("[0-9]{1,3}")))
        self.v_input = QLineEdit(); self.v_input.setValidator(QRegularExpressionValidator(QRegularExpression("[0-9]{1,3}")))
        self.h_input.editingFinished.connect(self.hsv_inputs_edited)
        self.s_input.editingFinished.connect(self.hsv_inputs_edited)
        self.v_input.editingFinished.connect(self.hsv_inputs_edited)
        numeric_preview_layout.addWidget(QLabel("H (0-359):"), 0, 0); numeric_preview_layout.addWidget(self.h_input, 0, 1)
        numeric_preview_layout.addWidget(QLabel("S (0-100%):"), 1, 0); numeric_preview_layout.addWidget(self.s_input, 1, 1)
        numeric_preview_layout.addWidget(QLabel("V (0-100%):"), 2, 0); numeric_preview_layout.addWidget(self.v_input, 2, 1)
        self.r_input = QLineEdit(); self.r_input.setValidator(QRegularExpressionValidator(QRegularExpression("[0-9]{1,3}")))
        self.g_input = QLineEdit(); self.g_input.setValidator(QRegularExpressionValidator(QRegularExpression("[0-9]{1,3}")))
        self.b_input = QLineEdit(); self.b_input.setValidator(QRegularExpressionValidator(QRegularExpression("[0-9]{1,3}")))
        self.r_input.editingFinished.connect(self.rgb_inputs_edited)
        self.g_input.editingFinished.connect(self.rgb_inputs_edited)
        self.b_input.editingFinished.connect(self.rgb_inputs_edited)
        numeric_preview_layout.addWidget(QLabel("R (0-255):"), 0, 2); numeric_preview_layout.addWidget(self.r_input, 0, 3)
        numeric_preview_layout.addWidget(QLabel("G (0-255):"), 1, 2); numeric_preview_layout.addWidget(self.g_input, 1, 3)
        numeric_preview_layout.addWidget(QLabel("B (0-255):"), 2, 2); numeric_preview_layout.addWidget(self.b_input, 2, 3)
        self.hex_input_lineedit = QLineEdit()
        hex_validator = QRegularExpressionValidator(QRegularExpression("#?[0-9A-Fa-f]{0,6}"))
        self.hex_input_lineedit.setValidator(hex_validator); self.hex_input_lineedit.setMaxLength(7); self.hex_input_lineedit.setPlaceholderText("#RRGGBB")
        self.hex_input_lineedit.editingFinished.connect(self.hex_input_edited_handler)
        numeric_preview_layout.addWidget(QLabel("HEX:"), 3, 0); numeric_preview_layout.addWidget(self.hex_input_lineedit, 3, 1, 1, 3)
        self.main_color_preview_swatch = QLabel()
        self.main_color_preview_swatch.setMinimumHeight(40); self.main_color_preview_swatch.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.main_color_preview_swatch.setAutoFillBackground(True); self.main_color_preview_swatch.setObjectName("MainColorPreview")
        numeric_preview_layout.addWidget(self.main_color_preview_swatch, 4, 0, 1, 4)
        controls_layout_main_v.addWidget(numeric_preview_group)

        my_colors_group = QGroupBox("My Colors")
        my_colors_layout = QVBoxLayout(my_colors_group)
        add_swatch_button = QPushButton("+ Add Current Color")
        add_swatch_button.clicked.connect(self.add_current_color_to_color_picker_swatches)
        my_colors_layout.addWidget(add_swatch_button, 0, Qt.AlignmentFlag.AlignRight)
        custom_swatches_grid_widget = QWidget()
        custom_swatches_grid_layout = QGridLayout(custom_swatches_grid_widget)
        custom_swatches_grid_layout.setSpacing(3)
        custom_swatches_grid_layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        for i in range(self.num_custom_swatches):
            swatch_button = QPushButton()
            swatch_button.setFixedSize(CUSTOM_SWATCH_SIZE, CUSTOM_SWATCH_SIZE)
            swatch_button.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
            swatch_button.setObjectName(f"CustomSwatchButton")
            swatch_button.clicked.connect(lambda checked=False, idx=i: self.apply_color_picker_swatch(idx))
            swatch_button.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
            swatch_button.customContextMenuRequested.connect(lambda pos, idx=i: self.show_color_picker_swatch_context_menu(self.custom_swatch_buttons[idx], idx, pos))
            self.custom_swatch_buttons.append(swatch_button)
            row, col = divmod(i, self.swatches_per_row)
            custom_swatches_grid_layout.addWidget(swatch_button, row, col)
        for c in range(self.swatches_per_row): custom_swatches_grid_layout.setColumnStretch(c,0)
        custom_swatches_grid_layout.setColumnStretch(self.swatches_per_row, 1)
        my_colors_layout.addWidget(custom_swatches_grid_widget)
        controls_layout_main_v.addWidget(my_colors_group)
        
        static_presets_group = QGroupBox("Static Pad Layouts")
        static_presets_layout = QVBoxLayout(static_presets_group)
        self.static_presets_combo = QComboBox()
        static_presets_layout.addWidget(self.static_presets_combo)
        preset_buttons_layout = QHBoxLayout()
        self.apply_layout_button = QPushButton("Apply Layout"); self.apply_layout_button.clicked.connect(self.apply_selected_static_pad_layout) # Store as self attribute
        preset_buttons_layout.addWidget(self.apply_layout_button)
        self.save_layout_button = QPushButton("Save Current As..."); self.save_layout_button.clicked.connect(self.save_current_layout_as_user_pad_layout) # Store as self attribute
        preset_buttons_layout.addWidget(self.save_layout_button)
        self.delete_layout_button = QPushButton("Delete Layout"); self.delete_layout_button.clicked.connect(self.delete_selected_user_pad_layout) # Store as self attribute
        preset_buttons_layout.addWidget(self.delete_layout_button)
        static_presets_layout.addLayout(preset_buttons_layout)
        controls_layout_main_v.addWidget(static_presets_group)

        tool_buttons_layout = QHBoxLayout()
        self.color_button_off = QPushButton("Active: Black"); 
        self.color_button_off.clicked.connect(lambda: self.final_color_selected_signal.emit(QColor("black")))
        tool_buttons_layout.addWidget(self.color_button_off)
        self.clear_all_button = QPushButton("Clear Device Pads")
        self.clear_all_button.clicked.connect(self.clear_all_hardware_and_gui_pads)
        tool_buttons_layout.addWidget(self.clear_all_button)
        controls_layout_main_v.addLayout(tool_buttons_layout)

        controls_layout_main_v.addStretch(1)
        
        main_app_layout.addWidget(controls_container, 1) # Controls panel gets a stretch factor of 1

        self.status_bar = QStatusBar(); self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready.")
        print("--- MainWindow init_ui FINISHED ---")

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self.is_drawing_with_left_button_down = True
            pos_in_grid_frame_global = self.pad_grid_frame.mapFromGlobal(event.globalPosition().toPoint())
            if self.pad_grid_frame.rect().contains(pos_in_grid_frame_global):
                child_widget = self.pad_grid_frame.childAt(pos_in_grid_frame_global)
                if isinstance(child_widget, PadButton):
                    self._last_painted_pad_on_drag = (child_widget.row, child_widget.col)
                    self.apply_paint_to_pad(child_widget.row, child_widget.col)
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent):
        if self.is_drawing_with_left_button_down:
            pos_in_grid_frame_global = self.pad_grid_frame.mapFromGlobal(event.globalPosition().toPoint()) # Use globalPosition
            if self.pad_grid_frame.rect().contains(pos_in_grid_frame_global):
                child_widget = self.pad_grid_frame.childAt(pos_in_grid_frame_global)
                if isinstance(child_widget, PadButton):
                    current_drag_pad = (child_widget.row, child_widget.col)
                    if current_drag_pad != self._last_painted_pad_on_drag:
                        self.apply_paint_to_pad(child_widget.row, child_widget.col)
                        self._last_painted_pad_on_drag = current_drag_pad
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self.is_drawing_with_left_button_down = False
            self._last_painted_pad_on_drag = None
        super().mouseReleaseEvent(event)

    def handle_pad_press_for_drawing(self, row, col):
        self.is_drawing_with_left_button_down = True 
        self._last_painted_pad_on_drag = (row, col)
        self.apply_paint_to_pad(row, col)

    def apply_paint_to_pad(self, row, col):
        if self.akai_controller.is_connected():
            r, g, b, _ = self.selected_qcolor.getRgb()
            self.akai_controller.set_pad_color(row, col, r, g, b)
            self.update_gui_pad_color(row, col, r, g, b)

    def on_pad_single_clicked(self, row, col):
        pass 

    def _set_internal_hsv(self, h_param, s_param, v_param, source_widget_id=None):
        # print(f"DEBUG: _set_internal_hsv CALLED from {source_widget_id} with H_in:{h_param} S_in:{s_param} V_in:{v_param}")
        h_display = 0
        h_normalized_for_qcolor = 0.0

        if isinstance(h_param, float) and -0.0001 <= h_param <= 1.0001: # If h is already normalized (0.0-1.0 from QColor.getHsvF, allow small tolerance)
            h_normalized_for_qcolor = max(0.0, min(1.0, h_param))
            h_display = int(h_normalized_for_qcolor * 359) if h_normalized_for_qcolor >= 0 else 0 
        elif isinstance(h_param, (int, float)): # If h is 0-359 (from HueSlider or inputs)
            h_display = int(max(0, min(359, float(h_param))))
            h_normalized_for_qcolor = h_display / 360.0
        else: # Fallback
            h_display = self._current_h_int
            h_normalized_for_qcolor = self._current_h_int / 360.0
            
        s_float = float(max(0.0, min(1.0, s_param)))
        v_float = float(max(0.0, min(1.0, v_param)))

        self._current_h_int = h_display
        self._current_s_float = s_float
        self._current_v_float = v_float
        
        new_qcolor = QColor.fromHsvF(h_normalized_for_qcolor, self._current_s_float, self._current_v_float)
        
        # print(f"DEBUG: _set_internal_hsv processed: new_qcolor={new_qcolor.name()}, current self.selected_qcolor was {self.selected_qcolor.name()}")
        
        color_changed_from_model = (new_qcolor != self.selected_qcolor)
        self.selected_qcolor = new_qcolor
        
        self._update_all_color_ui_elements(self.selected_qcolor, source_widget_id)
        
        if color_changed_from_model or source_widget_id == "init" or "swatch_apply" in str(source_widget_id) or "final_selection_handler" in str(source_widget_id) :
            # print(f"DEBUG: Emitting final_color_selected_signal with {self.selected_qcolor.name()} from _set_internal_hsv (source: {source_widget_id})")
            self.final_color_selected_signal.emit(self.selected_qcolor)

    def _update_all_color_ui_elements(self, color: QColor, originating_widget_id=None):
        if self._block_ui_updates and originating_widget_id not in ["init", "swatch_apply", "final_selection_handler", "hsv_inputs_error", "rgb_inputs_error"]:
            return
        self._block_ui_updates = True
        # print(f"DEBUG: _update_all_color_ui_elements for {color.name()} from {originating_widget_id} (Internal H={self._current_h_int} S={self._current_s_float:.2f} V={self._current_v_float:.2f})")

        widgets_to_block = []
        if originating_widget_id != "hue_slider": widgets_to_block.append(self.hue_slider_widget)
        if originating_widget_id != "sv_picker": widgets_to_block.append(self.sv_picker_widget)
        if originating_widget_id != "h_input": widgets_to_block.append(self.h_input)
        if originating_widget_id != "s_input": widgets_to_block.append(self.s_input)
        if originating_widget_id != "v_input": widgets_to_block.append(self.v_input)
        if originating_widget_id != "rgb_inputs": widgets_to_block.extend([self.r_input, self.g_input, self.b_input])
        if originating_widget_id != "hex_input": widgets_to_block.append(self.hex_input_lineedit)

        for w in widgets_to_block: 
            if w: w.blockSignals(True) # Check if widget exists

        if originating_widget_id != "hue_slider" and self.hue_slider_widget: self.hue_slider_widget.setHue(self._current_h_int)
        if originating_widget_id != "sv_picker" and self.sv_picker_widget: 
            self.sv_picker_widget.setHue(self._current_h_int) 
            self.sv_picker_widget.setSV(self._current_s_float, self._current_v_float)

        if originating_widget_id != "h_input" and self.h_input: self.h_input.setText(str(self._current_h_int))
        if originating_widget_id != "s_input" and self.s_input: self.s_input.setText(str(int(self._current_s_float * 100)))
        if originating_widget_id != "v_input" and self.v_input: self.v_input.setText(str(int(self._current_v_float * 100)))
        
        if originating_widget_id != "rgb_inputs" and self.r_input: # Check self.r_input etc.
            self.r_input.setText(str(color.red()))
            self.g_input.setText(str(color.green()))
            self.b_input.setText(str(color.blue()))
        
        if originating_widget_id != "hex_input" and self.hex_input_lineedit: self.hex_input_lineedit.setText(color.name())
        
        self.update_main_color_preview_swatch_ui(color)

        for w in widgets_to_block: 
            if w: w.blockSignals(False)
        self._block_ui_updates = False

    def hue_slider_value_changed(self, hue_val_int):
        # print(f"DEBUG: >>> Hue Slider Changed to: {hue_val_int}")
        self._set_internal_hsv(hue_val_int, self._current_s_float, self._current_v_float, "hue_slider")

    def sv_picker_value_changed(self, saturation_float, value_float):
        # print(f"DEBUG: >>> SV Picker Changed to: S={saturation_float:.2f}, V={value_float:.2f}")
        self._set_internal_hsv(self._current_h_int, saturation_float, value_float, "sv_picker")

    def hsv_inputs_edited(self):
        # print(f"DEBUG: >>> HSV Inputs Edited")
        try:
            h = int(self.h_input.text()); s = int(self.s_input.text()) / 100.0; v = int(self.v_input.text()) / 100.0
            self._set_internal_hsv(h,s,v, "hsv_inputs")
        except ValueError: self._update_all_color_ui_elements(self.selected_qcolor, "hsv_inputs_error")

    def rgb_inputs_edited(self):
        # print(f"DEBUG: >>> RGB Inputs Edited")
        try:
            r,g,b = int(self.r_input.text()), int(self.g_input.text()), int(self.b_input.text())
            color = QColor(r,g,b)
            if color.isValid():
                h_f, s_f, v_f, _ = color.getHsvF()
                self._set_internal_hsv(h_f, s_f, v_f, "rgb_inputs")
        except ValueError: self._update_all_color_ui_elements(self.selected_qcolor, "rgb_inputs_error")

    def hex_input_edited_handler(self):
        # print(f"DEBUG: >>> HEX Input Edited")
        color_name = self.hex_input_lineedit.text()
        if not color_name.startswith("#"): color_name = "#" + color_name
        color = QColor(color_name)
        if color.isValid():
            h_f, s_f, v_f, _ = color.getHsvF()
            self._set_internal_hsv(h_f, s_f, v_f, "hex_input")
        else:
            self.hex_input_lineedit.setText(self.selected_qcolor.name())
            self.status_bar.showMessage("Invalid HEX color.", 2000)

    def update_main_color_preview_swatch_ui(self, color: QColor):
        if self.main_color_preview_swatch:
            palette = self.main_color_preview_swatch.palette(); palette.setColor(QPalette.ColorRole.Window, color)
            self.main_color_preview_swatch.setPalette(palette)
            luminance = 0.299*color.red()+0.587*color.green()+0.114*color.blue()
            text_color = "#1C1C1C" if luminance > 128 else "#E0E0E0"
            self.main_color_preview_swatch.setStyleSheet(f"background-color: {color.name()}; color: {text_color}; border: 1px solid #777; font-weight: bold;")
            self.main_color_preview_swatch.setText(color.name().upper())

    def handle_final_color_selection(self, color: QColor):
        # print(f"DEBUG: handle_final_color_selection with {color.name()}, current self.selected_qcolor: {self.selected_qcolor.name()}")
        # This check is to prevent redundant UI updates if the color is already what the UI shows.
        # The authoritative `self.selected_qcolor` is already set by `_set_internal_hsv` before this signal is emitted.
        if color != self.selected_qcolor or \
           self._current_h_int != (int(color.getHsvF()[0]*359) if color.getHsvF()[0] >=0 else 0) or \
           abs(self._current_s_float - color.getHsvF()[1]) > 0.001 or \
           abs(self._current_v_float - color.getHsvF()[2]) > 0.001:
            
            self.selected_qcolor = color # Ensure it's definitively set
            self._update_all_color_ui_elements(self.selected_qcolor, "final_selection_handler") 
        
        self.status_bar.showMessage(f"Active color: {color.name()}", 3000)

    def add_current_color_to_color_picker_swatches(self):
        empty_idx = -1
        for i, button in enumerate(self.custom_swatch_buttons):
            style = button.styleSheet(); 
            if "dashed" in style or "#333333" in style.lower(): empty_idx = i; break
        if empty_idx != -1: self.save_color_to_color_picker_swatch(empty_idx, self.selected_qcolor)
        else: 
            self.save_color_to_color_picker_swatch(self.num_custom_swatches - 1, self.selected_qcolor)
            self.status_bar.showMessage("Color swatches full. Last overwritten.", 2000)

    def apply_color_picker_swatch(self, index):
        button = self.custom_swatch_buttons[index]
        style = button.styleSheet()
        if "background-color:" in style:
            parts = style.split("background-color:")[1].split(";")[0].strip()
            color = QColor(parts)
            # print(f"DEBUG: Applying Picker Swatch {index}, color string: '{parts}', QColor valid: {color.isValid()}, name: {color.name()}")
            if color.isValid() and not ("dashed" in style or (parts.lower() == "#333333" and "dashed" not in style)):
                h_float, s_float, v_float, _ = color.getHsvF()
                self._set_internal_hsv(h_float, s_float, v_float, source_widget_id=f"swatch_apply_{index}")

    def show_color_picker_swatch_context_menu(self, button_widget, index, position):
        menu = QMenu(); save_action = menu.addAction("Save Current Color Here")
        clear_action = menu.addAction("Clear This Swatch")
        action = menu.exec(button_widget.mapToGlobal(position))
        if action == save_action: self.save_color_to_color_picker_swatch(index, self.selected_qcolor)
        elif action == clear_action: self.clear_color_picker_swatch(index)

    def save_color_to_color_picker_swatch(self, index, color: QColor):
        button = self.custom_swatch_buttons[index]
        button.setStyleSheet(f"background-color: {color.name()}; border: 1px solid #888;")
        self.save_color_picker_swatches_to_config()

    def clear_color_picker_swatch(self, index):
        button = self.custom_swatch_buttons[index]
        button.setStyleSheet(f"QPushButton#CustomSwatchButton {{ background-color: #333; border: 1px dashed #666; }}")
        self.save_color_picker_swatches_to_config()

    def update_all_color_picker_swatch_buttons_ui(self, colors_hex_list):
        default_empty_style = "QPushButton#CustomSwatchButton { background-color: #333; border: 1px dashed #666; }"
        for i, button in enumerate(self.custom_swatch_buttons):
            if i < len(colors_hex_list) and colors_hex_list[i] and QColor(colors_hex_list[i]).isValid():
                button.setStyleSheet(f"background-color: {QColor(colors_hex_list[i]).name()}; border: 1px solid #888;")
            else: button.setStyleSheet(default_empty_style)

    def get_color_picker_swatches_config_path(self):
        base_path = os.path.dirname(os.path.abspath(sys.argv[0]))
        return os.path.join(base_path, CONFIG_FILE_NAME)

    def save_color_picker_swatches_to_config(self):
        swatch_colors_hex = []
        for button in self.custom_swatch_buttons:
            style = button.styleSheet(); color_str = None
            if "background-color:" in style and "dashed" not in style:
                color_part = style.split("background-color:")[1].split(";")[0].strip()
                q_color_obj = QColor(color_part)
                if q_color_obj.isValid() and color_part.lower() != "#333333": color_str = q_color_obj.name()
            swatch_colors_hex.append(color_str)
        config_path = self.get_color_picker_swatches_config_path()
        config_data = {}
        if os.path.exists(config_path):
            try: config_data = json.load(open(config_path, "r"))
            except: pass
        config_data["color_picker_swatches"] = swatch_colors_hex
        try:
            with open(config_path, "w") as f: json.dump(config_data, f, indent=4)
        except Exception as e: print(f"Error saving color picker swatches: {e}")

    def load_color_picker_swatches_from_config(self):
        config_path = self.get_color_picker_swatches_config_path()
        default_swatches = [None] * self.num_custom_swatches
        loaded_swatches = default_swatches
        if os.path.exists(config_path):
            try:
                with open(config_path, "r") as f: config_data = json.load(f)
                loaded_hex = config_data.get("color_picker_swatches", [])
                loaded_swatches = (loaded_hex + [None] * self.num_custom_swatches)[:self.num_custom_swatches]
            except Exception as e: print(f"Error loading color picker swatches: {e}")
        self.update_all_color_picker_swatch_buttons_ui(loaded_swatches)

    def sanitize_filename(self, name):
        name = re.sub(r'[^\w\s-]', '', name).strip()
        name = re.sub(r'[-\s]+', '_', name)
        return name if name else "untitled_layout"

    def get_user_pad_layouts_dir(self):
        base_path = os.path.dirname(os.path.abspath(sys.argv[0]))
        return os.path.join(base_path, USER_PRESETS_DIR)

    def load_all_static_pad_layouts(self):
        self.loaded_static_presets.clear()
        base_path = os.path.dirname(os.path.abspath(sys.argv[0]))
        prefab_dir_abs = os.path.join(base_path, PREFAB_STATIC_PRESETS_DIR)
        if os.path.isdir(prefab_dir_abs):
            for filepath in glob.glob(os.path.join(prefab_dir_abs, "*.json")):
                try:
                    with open(filepath, "r") as f: data = json.load(f)
                    name = data.get("name", os.path.splitext(os.path.basename(filepath))[0])
                    if name and data.get("colors"): self.loaded_static_presets[f"[Prefab] {name}"] = {"path": filepath, "data": data, "type": "prefab"}
                except Exception as e: print(f"Error loading prefab layout {filepath}: {e}")
        user_dir_abs = self.get_user_pad_layouts_dir()
        if os.path.isdir(user_dir_abs):
            for filepath in glob.glob(os.path.join(user_dir_abs, "*.json")):
                try:
                    with open(filepath, "r") as f: data = json.load(f)
                    name = data.get("name", os.path.splitext(os.path.basename(filepath))[0])
                    if name and data.get("colors"): self.loaded_static_presets[name] = {"path": filepath, "data": data, "type": "user"}
                except Exception as e: print(f"Error loading user layout {filepath}: {e}")
        self.update_static_presets_combo()

    def update_static_presets_combo(self):
        self.static_presets_combo.blockSignals(True)
        self.static_presets_combo.clear()
        if not self.loaded_static_presets:
            self.static_presets_combo.addItem("No layouts available"); self.static_presets_combo.setEnabled(False)
        else:
            sorted_keys = sorted(self.loaded_static_presets.keys(), key=lambda k: (self.loaded_static_presets[k]['type'] == 'user', k))
            self.static_presets_combo.addItems(sorted_keys); self.static_presets_combo.setEnabled(True)
        self.static_presets_combo.blockSignals(False)

    def apply_selected_static_pad_layout(self):
        self.stop_current_animation()
        current_preset_name = self.static_presets_combo.currentText()
        if current_preset_name in self.loaded_static_presets:
            preset_info = self.loaded_static_presets[current_preset_name]
            colors_hex = preset_info["data"]["colors"]
            pads_to_set_hw = []
            for i, hex_str in enumerate(colors_hex):
                if i >= 64: break
                r_idx, c_idx = divmod(i, 16)
                try:
                    color = QColor(hex_str if hex_str else "#000000")
                    if not color.isValid(): color = QColor("#000000")
                    self.update_gui_pad_color(r_idx, c_idx, color.red(), color.green(), color.blue())
                    pads_to_set_hw.append((r_idx, c_idx, color.red(), color.green(), color.blue()))
                except: self.update_gui_pad_color(r_idx, c_idx, 0,0,0); pads_to_set_hw.append((r_idx,c_idx,0,0,0))
            if self.akai_controller.is_connected() and pads_to_set_hw: self.akai_controller.set_multiple_pads_color(pads_to_set_hw)
            self.status_bar.showMessage(f"Applied layout: {current_preset_name}", 2000)

    def save_current_layout_as_user_pad_layout(self):
        self.stop_current_animation()
        text, ok = QInputDialog.getText(self, "Save Pad Layout", "Enter layout name:")
        if not (ok and text): return
        profile_name_raw = text.strip()
        if not profile_name_raw: QMessageBox.warning(self, "Save Error", "Layout name empty."); return
        profile_filename_base = self.sanitize_filename(profile_name_raw)
        profile_filename = f"{profile_filename_base}.json"
        user_dir = self.get_user_pad_layouts_dir()
        profile_path = os.path.join(user_dir, profile_filename)
        if os.path.exists(profile_path):
            reply = QMessageBox.question(self, "Overwrite?", f"'{profile_name_raw}' exists. Overwrite?",
                                         QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.No: return
        if f"[Prefab] {profile_name_raw}" in self.loaded_static_presets:
            QMessageBox.warning(self, "Save Error", f"Name clashes with prefab. Choose different."); return
        current_colors_hex = []
        for r_idx in range(4):
            for c_idx in range(16):
                button = self.pad_buttons[(r_idx, c_idx)]; style = button.styleSheet(); color_hex = "#000000"
                try:
                    if "background-color: rgb(" in style:
                        rgb_part = style.split("background-color: rgb(")[1].split(");")[0]; r,g,b = map(int, rgb_part.split(","))
                        color_hex = QColor(r,g,b).name()
                    elif "background-color: #" in style:
                        hex_part = style.split("background-color: #")[1].split(";")[0]
                        if len(hex_part) == 6: color_hex = f"#{hex_part}"
                        else: color_hex = QColor(hex_part.replace("!important","").strip()).name()
                except: pass
                current_colors_hex.append(color_hex)
        profile_data = {"name": profile_name_raw, "description": "User saved layout", "colors": current_colors_hex}
        try:
            with open(profile_path, "w") as f: json.dump(profile_data, f, indent=4)
            self.status_bar.showMessage(f"Layout '{profile_name_raw}' saved.", 2000)
            self.load_all_static_pad_layouts(); self.static_presets_combo.setCurrentText(profile_name_raw)
        except Exception as e: QMessageBox.critical(self, "Save Error", f"Could not save: {e}")

    def delete_selected_user_pad_layout(self):
        current_display_name = self.static_presets_combo.currentText()
        if not current_display_name or current_display_name == "No layouts available": return
        preset_info = self.loaded_static_presets.get(current_display_name)
        if not preset_info or preset_info["type"] != "user":
            QMessageBox.warning(self, "Delete Error", "Only user layouts can be deleted."); return
        profile_name_to_delete = current_display_name
        reply = QMessageBox.question(self, "Confirm Delete", f"Delete '{profile_name_to_delete}'?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            profile_path = preset_info["path"]
            try:
                if os.path.exists(profile_path): os.remove(profile_path)
                self.status_bar.showMessage(f"Layout '{profile_name_to_delete}' deleted.", 2000)
                self.load_all_static_pad_layouts()
            except Exception as e: QMessageBox.critical(self, "Delete Error", f"Could not delete: {e}")
    
    def next_animation_frame_slot(self): pass
    def stop_current_animation(self):
        if self.animation_timer.isActive(): self.animation_timer.stop()
        self.current_animation_name = None

    def show_pad_context_menu(self, pad_button_widget, row, col, position):
        menu = QMenu(); set_black_action = QAction("Set Pad to Black (Off)", self)
        set_black_action.triggered.connect(lambda: self.set_single_pad_black(row, col))
        menu.addAction(set_black_action); menu.exec(pad_button_widget.mapToGlobal(position))

    def set_single_pad_black(self, row, col):
        if self.akai_controller.is_connected():
            self.akai_controller.set_pad_color(row, col, 0,0,0); self.update_gui_pad_color(row, col, 0,0,0)

    def update_gui_pad_color(self, row, col, r, g, b):
        button = self.pad_buttons.get((row, col))
        if button:
            # Define base style parts that are consistent for PadButton
            base_pad_style = "QPushButton#PadButton {{ border-radius: 2px; {dynamic_style} }}"
            hover_pad_style = "QPushButton#PadButton:hover {{ border: 1px solid {hover_border_color}; }}"
            
            dynamic_part = ""
            hover_border = ""

            if r==0 and g==0 and b==0: # Unlit
                dynamic_part = "background-color: #1C1C1C; border: 1px solid #404040; color: transparent;"
                hover_border = "#666666"
            else: # Lit
                lum = 0.299*r+0.587*g+0.114*b; tc = "#E0E0E0" if lum < 128 else "#1C1C1C"
                dynamic_part = (f"background-color: rgb({r},{g},{b}); "
                                f"border: 1px solid qlineargradient(x1:0,y1:0,x2:1,y2:1,"
                                f"stop:0 rgba({max(0,r-20)},{max(0,g-20)},{max(0,b-20)},255),"
                                f"stop:1 rgba({min(255,r+20)},{min(255,g+20)},{min(255,b+20)},255)); "
                                f"color:{tc};")
                hover_border = tc
            
            final_style = base_pad_style.format(dynamic_style=dynamic_part) + " " + hover_pad_style.format(hover_border_color=hover_border)
            button.setStyleSheet(final_style)


    def clear_all_hardware_and_gui_pads(self):
        self.stop_current_animation()
        if self.akai_controller.is_connected():
            self.akai_controller.clear_all_pads()
            for r_idx in range(4):
                for c_idx in range(16): self.update_gui_pad_color(r_idx, c_idx, 0,0,0)
            self.status_bar.showMessage("All device pads cleared.", 2000)

    def populate_midi_ports(self):
        self.port_combo.clear(); ports = AkaiFireController.get_available_ports()
        if ports:
            self.port_combo.addItems(ports)
            for i, name in enumerate(ports):
                if ("fire" in name.lower() or "akai" in name.lower()) and "midiin" not in name.lower(): self.port_combo.setCurrentIndex(i); break
        else: self.port_combo.addItem("No MIDI ports found"); self.port_combo.setEnabled(False)
    
    def toggle_connection(self):
        if self.akai_controller.is_connected(): self.akai_controller.disconnect()
        else:
            port = self.port_combo.currentText()
            if port and port != "No MIDI ports found": self.akai_controller.connect(port)
            else: self.status_bar.showMessage("Select valid MIDI port.", 3000)
        self.update_connection_status()

    def update_connection_status(self):
        is_c = self.akai_controller.is_connected()
        self.connect_button.setText("Disconnect" if is_c else "Connect")
        self.status_bar.showMessage(f"Connected to {self.akai_controller.port_name_used}" if is_c else "Disconnected.")
        self.port_combo.setEnabled(not is_c); self.pad_grid_frame.setEnabled(is_c); self.clear_all_button.setEnabled(is_c)
        
        # Ensure preset related buttons are stored as self attributes to be reliably found
        preset_controls_to_toggle = [self.static_presets_combo, self.apply_layout_button, 
                                     self.save_layout_button, self.delete_layout_button]

        for w in [self.sv_picker_widget, self.hue_slider_widget, self.r_input, self.g_input, self.b_input,
                  self.h_input, self.s_input, self.v_input, self.hex_input_lineedit, self.main_color_preview_swatch,
                  self.findChild(QPushButton, "+ Add Current Color"), self.color_button_off] + preset_controls_to_toggle:
            if w: w.setEnabled(is_c)
        for sw in self.custom_swatch_buttons: sw.setEnabled(is_c)
        if not is_c: self.populate_midi_ports()

    def closeEvent(self, event):
        print("Closing application...")
        self.stop_current_animation(); self.save_color_picker_swatches_to_config()
        if self.akai_controller.is_connected(): self.akai_controller.disconnect()
        event.accept()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    gui_dir_path = os.path.dirname(os.path.abspath(__file__)) 
    project_root_path = os.path.dirname(gui_dir_path) 
    style_sheet_path_abs = os.path.join(project_root_path, "resources", "styles", "style.qss")
    try:
        with open(style_sheet_path_abs, "r") as f: app.setStyleSheet(f.read())
        # print(f"DEBUG: Stylesheet loaded from: {style_sheet_path_abs}") 
    except FileNotFoundError: print(f"Warning: Stylesheet '{style_sheet_path_abs}' not found.")
    except Exception as e: print(f"Error loading stylesheet: {e}")
    main_win = MainWindow()
    main_win.show()
    sys.exit(app.exec())