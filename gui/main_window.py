# AKAI_Fire_RGB_Controller/gui/main_window.py
import sys
import json
import os
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QComboBox, QLabel, QStatusBar, QGridLayout, QFrame,
    QLineEdit, QFormLayout, QGroupBox, QMenu, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal, QRegularExpression, QPoint
from PyQt6.QtGui import QColor, QPalette, QRegularExpressionValidator, QAction, QMouseEvent

# Import our new custom widgets
from gui.hue_slider import HueSlider
from gui.sv_picker import SVPicker

from hardware.akai_fire_controller import AkaiFireController

CONFIG_FILE_NAME = "fire_controller_config.json"

# --- PadButton Class (SIMPLIFIED) ---
class PadButton(QPushButton):
    request_paint_on_press = pyqtSignal(int, int)

    def __init__(self, row, col, parent=None):
        super().__init__(parent)
        self.row = row
        self.col = col
        self.setObjectName("PadButton")
        self.setFixedSize(35, 35)
        self.setCheckable(False)

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self.request_paint_on_press.emit(self.row, self.col)
        super().mousePressEvent(event)
# --- END OF MODIFIED PadButton ---

class MainWindow(QMainWindow):
    final_color_selected_signal = pyqtSignal(QColor)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("AKAI Fire RGB Controller - Advanced Picker")
        self.setGeometry(100, 100, 750, 700)

        self.akai_controller = AkaiFireController(auto_connect=False)
        self.pad_buttons = {}

        self._current_h = 0
        self._current_s = 1.0
        self._current_v = 1.0
        self.selected_qcolor = QColor.fromHsvF(self._current_h / 360.0, self._current_s, self._current_v)

        self.hue_slider_widget = None
        self.sv_picker_widget = None
        
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

        self.init_ui()
        self.update_connection_status()
        self.populate_midi_ports()
        
        self.final_color_selected_signal.connect(self.handle_final_color_selection)
        self.load_custom_swatches()
        self._update_all_color_ui_elements(self.selected_qcolor, "init")

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_app_layout = QHBoxLayout(central_widget)

        # --- Left Side: Pad Grid ---
        pad_grid_container = QWidget()
        pad_grid_main_layout = QVBoxLayout(pad_grid_container)
        
        self.pad_grid_frame = QFrame()
        self.pad_grid_frame.setObjectName("PadGridFrame")
        pad_grid_layout = QGridLayout()
        pad_grid_layout.setSpacing(2)
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
        pad_grid_main_layout.addWidget(self.pad_grid_frame)
        pad_grid_main_layout.addStretch(1)
        main_app_layout.addWidget(pad_grid_container, 2)

        # --- Right Side: All Controls ---
        controls_container = QWidget()
        controls_layout_main_v = QVBoxLayout(controls_container)
        controls_container.setMinimumWidth(300)
        controls_container.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Preferred)

        # Connection Controls
        connection_layout = QHBoxLayout()
        self.port_combo = QComboBox(); self.port_combo.setPlaceholderText("Select MIDI Port")
        self.connect_button = QPushButton("Connect"); self.connect_button.clicked.connect(self.toggle_connection)
        connection_layout.addWidget(QLabel("Port:")); connection_layout.addWidget(self.port_combo,1); connection_layout.addWidget(self.connect_button)
        controls_layout_main_v.addLayout(connection_layout)

        # Advanced Color Picker Group
        adv_color_picker_group = QGroupBox("Advanced Color Picker")
        adv_color_picker_group_layout = QHBoxLayout(adv_color_picker_group)

        self.sv_picker_widget = SVPicker()
        self.sv_picker_widget.setMinimumSize(150,150)
        self.sv_picker_widget.sv_changed.connect(self.sv_picker_value_changed)
        adv_color_picker_group_layout.addWidget(self.sv_picker_widget, 1)

        self.hue_slider_widget = HueSlider(orientation=Qt.Orientation.Vertical)
        self.hue_slider_widget.setMinimumWidth(35)
        self.hue_slider_widget.hue_changed.connect(self.hue_slider_value_changed)
        adv_color_picker_group_layout.addWidget(self.hue_slider_widget)
        
        controls_layout_main_v.addWidget(adv_color_picker_group)

        # Numeric Inputs and Main Preview Group
        numeric_preview_group = QGroupBox("Color Values & Preview")
        numeric_preview_layout = QGridLayout(numeric_preview_group)

        # HSV Inputs
        self.h_input = QLineEdit(); self.h_input.setValidator(QRegularExpressionValidator(QRegularExpression("[0-9]{1,3}")))
        self.s_input = QLineEdit(); self.s_input.setValidator(QRegularExpressionValidator(QRegularExpression("[0-9]{1,3}")))
        self.v_input = QLineEdit(); self.v_input.setValidator(QRegularExpressionValidator(QRegularExpression("[0-9]{1,3}")))
        self.h_input.editingFinished.connect(self.hsv_inputs_edited)
        self.s_input.editingFinished.connect(self.hsv_inputs_edited)
        self.v_input.editingFinished.connect(self.hsv_inputs_edited)
        numeric_preview_layout.addWidget(QLabel("H (0-359):"), 0, 0); numeric_preview_layout.addWidget(self.h_input, 0, 1)
        numeric_preview_layout.addWidget(QLabel("S (0-100%):"), 1, 0); numeric_preview_layout.addWidget(self.s_input, 1, 1)
        numeric_preview_layout.addWidget(QLabel("V (0-100%):"), 2, 0); numeric_preview_layout.addWidget(self.v_input, 2, 1)

        # RGB Inputs
        self.r_input = QLineEdit(); self.r_input.setValidator(QRegularExpressionValidator(QRegularExpression("[0-9]{1,3}")))
        self.g_input = QLineEdit(); self.g_input.setValidator(QRegularExpressionValidator(QRegularExpression("[0-9]{1,3}")))
        self.b_input = QLineEdit(); self.b_input.setValidator(QRegularExpressionValidator(QRegularExpression("[0-9]{1,3}")))
        self.r_input.editingFinished.connect(self.rgb_inputs_edited)
        self.g_input.editingFinished.connect(self.rgb_inputs_edited)
        self.b_input.editingFinished.connect(self.rgb_inputs_edited)
        numeric_preview_layout.addWidget(QLabel("R (0-255):"), 0, 2); numeric_preview_layout.addWidget(self.r_input, 0, 3)
        numeric_preview_layout.addWidget(QLabel("G (0-255):"), 1, 2); numeric_preview_layout.addWidget(self.g_input, 1, 3)
        numeric_preview_layout.addWidget(QLabel("B (0-255):"), 2, 2); numeric_preview_layout.addWidget(self.b_input, 2, 3)

        # HEX Input
        self.hex_input_lineedit = QLineEdit()
        hex_validator = QRegularExpressionValidator(QRegularExpression("#?[0-9A-Fa-f]{0,6}"))
        self.hex_input_lineedit.setValidator(hex_validator); self.hex_input_lineedit.setMaxLength(7)
        self.hex_input_lineedit.editingFinished.connect(self.hex_input_edited_handler)
        numeric_preview_layout.addWidget(QLabel("HEX:"), 3, 0); numeric_preview_layout.addWidget(self.hex_input_lineedit, 3, 1, 1, 3)

        # Main Color Preview
        self.main_color_preview_swatch = QLabel()
        self.main_color_preview_swatch.setMinimumHeight(40)
        self.main_color_preview_swatch.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.main_color_preview_swatch.setAutoFillBackground(True)
        self.main_color_preview_swatch.setObjectName("MainColorPreview")
        numeric_preview_layout.addWidget(self.main_color_preview_swatch, 4, 0, 1, 4)
        
        controls_layout_main_v.addWidget(numeric_preview_group)

        # "My Colors" (Custom Swatches) Group
        my_colors_group = QGroupBox("My Colors")
        my_colors_layout = QVBoxLayout(my_colors_group)

        add_swatch_button = QPushButton("+ Add Current Color")
        add_swatch_button.clicked.connect(self.add_current_color_to_swatches)
        my_colors_layout.addWidget(add_swatch_button, 0, Qt.AlignmentFlag.AlignRight)

        custom_swatches_grid_layout = QGridLayout()
        custom_swatches_grid_layout.setSpacing(3)
        for i in range(self.num_custom_swatches):
            swatch_button = QPushButton()
            swatch_button.setFixedSize(30, 30)
            swatch_button.setObjectName(f"CustomSwatchButton")
            swatch_button.clicked.connect(lambda checked=False, idx=i: self.apply_custom_swatch(idx))
            swatch_button.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
            swatch_button.customContextMenuRequested.connect(lambda pos, idx=i: self.show_swatch_context_menu(self.custom_swatch_buttons[idx], idx, pos))
            self.custom_swatch_buttons.append(swatch_button)
            row, col = divmod(i, self.swatches_per_row)
            custom_swatches_grid_layout.addWidget(swatch_button, row, col)
        my_colors_layout.addLayout(custom_swatches_grid_layout)
        controls_layout_main_v.addWidget(my_colors_group)
        
        # Utility Buttons (Set Off, Clear All)
        tool_buttons_layout = QHBoxLayout()
        self.color_button_off = QPushButton("Set Active Color to Black"); 
        self.color_button_off.clicked.connect(lambda: self.final_color_selected_signal.emit(QColor("black")))
        tool_buttons_layout.addWidget(self.color_button_off)
        self.clear_all_button = QPushButton("Clear All Device Pads")
        self.clear_all_button.clicked.connect(self.clear_all_hardware_pads)
        tool_buttons_layout.addWidget(self.clear_all_button)
        controls_layout_main_v.addLayout(tool_buttons_layout)

        controls_layout_main_v.addStretch(1)

        main_app_layout.addWidget(controls_container, 1)

        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready.")

    # --- NEW METHOD to start drawing state ---
    def handle_pad_press_for_drawing(self, row, col):
        self.is_drawing_with_left_button_down = True
        self._last_painted_pad_on_drag = (row, col)
        self.apply_paint_to_pad(row, col)

    # --- RENAME handle_pad_paint_request to apply_paint_to_pad ---
    def apply_paint_to_pad(self, row, col):
        if self.akai_controller.is_connected():
            r, g, b, _ = self.selected_qcolor.getRgb()
            self.akai_controller.set_pad_color(row, col, r, g, b)
            self.update_gui_pad_color(row, col, r, g, b)

    def on_pad_single_clicked(self, row, col):
        # Paint is handled by mousePressEvent -> handle_pad_press_for_drawing
        pass

    # --- OVERRIDE mouseMoveEvent and mouseReleaseEvent for drag-drawing ---
    def mouseMoveEvent(self, event: QMouseEvent):
        if self.is_drawing_with_left_button_down:
            pos_in_grid_frame = self.pad_grid_frame.mapFromGlobal(event.globalPosition().toPoint())
            if self.pad_grid_frame.rect().contains(pos_in_grid_frame):
                child_widget = self.pad_grid_frame.childAt(pos_in_grid_frame)
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

    # --- Color Model Synchronization ---
    def _set_internal_hsv(self, h, s, v, source_widget=None):
        self._current_h = int(max(0, min(359, h)))
        self._current_s = float(max(0.0, min(1.0, s)))
        self._current_v = float(max(0.0, min(1.0, v)))
        self.selected_qcolor = QColor.fromHsvF(self._current_h / 360.0, self._current_s, self._current_v)
        self._update_all_color_ui_elements(self.selected_qcolor, source_widget)
        self.final_color_selected_signal.emit(self.selected_qcolor)

    def _update_all_color_ui_elements(self, color: QColor, originating_widget_id=None):
        if self._block_ui_updates: return
        self._block_ui_updates = True

        h, s_float, v_float, _ = color.getHsvF()
        h_int = int(h * 359) if h != -1 else 0

        if originating_widget_id != "hue_slider": self.hue_slider_widget.setHue(h_int)
        if originating_widget_id != "sv_picker": self.sv_picker_widget.setSV(s_float, v_float)
        if originating_widget_id != "sv_picker" : self.sv_picker_widget.setHue(h_int)

        if originating_widget_id != "h_input": self.h_input.setText(str(h_int))
        if originating_widget_id != "s_input": self.s_input.setText(str(int(s_float * 100)))
        if originating_widget_id != "v_input": self.v_input.setText(str(int(v_float * 100)))
        
        if originating_widget_id != "rgb_inputs":
            self.r_input.setText(str(color.red()))
            self.g_input.setText(str(color.green()))
            self.b_input.setText(str(color.blue()))
        
        if originating_widget_id != "hex_input": self.hex_input_lineedit.setText(color.name())
        
        self.update_main_color_preview_swatch_ui(color)
        
        self._block_ui_updates = False

    def hue_slider_value_changed(self, hue_val):
        if self._block_ui_updates: return
        self._set_internal_hsv(hue_val, self._current_s, self._current_v, "hue_slider")

    def sv_picker_value_changed(self, saturation, value):
        if self._block_ui_updates: return
        self._set_internal_hsv(self._current_h, saturation, value, "sv_picker")

    def hsv_inputs_edited(self):
        if self._block_ui_updates: return
        try:
            h = int(self.h_input.text())
            s = int(self.s_input.text()) / 100.0
            v = int(self.v_input.text()) / 100.0
            self._set_internal_hsv(h, s, v, "hsv_inputs")
        except ValueError:
            self._update_all_color_ui_elements(self.selected_qcolor, "hsv_inputs_error")

    def rgb_inputs_edited(self):
        if self._block_ui_updates: return
        try:
            r = int(self.r_input.text())
            g = int(self.g_input.text())
            b = int(self.b_input.text())
            color = QColor(r,g,b)
            if color.isValid():
                h, s, v, _ = color.getHsvF()
                h_int = int(h*359) if h!=-1 else self._current_h
                self._set_internal_hsv(h_int, s, v, "rgb_inputs")
        except ValueError:
            self._update_all_color_ui_elements(self.selected_qcolor, "rgb_inputs_error")

    def hex_input_edited_handler(self):
        if self._block_ui_updates: return
        color_name = self.hex_input_lineedit.text()
        if not color_name.startswith("#"): color_name = "#" + color_name
        
        color = QColor(color_name)
        if color.isValid():
            h, s, v, _ = color.getHsvF()
            h_int = int(h*359) if h!=-1 else self._current_h
            self._set_internal_hsv(h_int, s, v, "hex_input")
        else:
            self.hex_input_lineedit.setText(self.selected_qcolor.name())
            self.status_bar.showMessage("Invalid HEX color.", 2000)

    def update_main_color_preview_swatch_ui(self, color: QColor):
        if self.main_color_preview_swatch:
            palette = self.main_color_preview_swatch.palette()
            palette.setColor(QPalette.ColorRole.Window, color)
            self.main_color_preview_swatch.setPalette(palette)
            luminance = 0.299 * color.red() + 0.587 * color.green() + 0.114 * color.blue()
            text_color = "#1C1C1C" if luminance > 128 else "#E0E0E0"
            self.main_color_preview_swatch.setStyleSheet(f"background-color: {color.name()}; color: {text_color}; border: 1px solid #777; font-weight: bold;")
            self.main_color_preview_swatch.setText(color.name().upper())

    def handle_final_color_selection(self, color: QColor):
        self.selected_qcolor = color
        self.status_bar.showMessage(f"Active color: {color.name()}", 3000)

    def add_current_color_to_swatches(self):
        empty_idx = -1
        for i, button in enumerate(self.custom_swatch_buttons):
            style = button.styleSheet()
            if "dashed" in style or "#333333" in style.lower():
                empty_idx = i
                break
        
        if empty_idx != -1:
            self.save_color_to_swatch(empty_idx, self.selected_qcolor)
        else:
            self.save_color_to_swatch(self.num_custom_swatches - 1, self.selected_qcolor)
            self.status_bar.showMessage("Swatches full. Last swatch overwritten.", 2000)

    def apply_custom_swatch(self, index):
        button = self.custom_swatch_buttons[index]
        style = button.styleSheet()
        if "background-color:" in style:
            parts = style.split("background-color:")[1].split(";")[0].strip()
            color = QColor(parts)
            if color.isValid() and not ("dashed" in style or "#333333" in style.lower()):
                self.final_color_selected_signal.emit(color)

    def show_swatch_context_menu(self, button_widget, index, position):
        menu = QMenu()
        save_action = menu.addAction("Save Current Color Here")
        clear_action = menu.addAction("Clear This Swatch")
        
        action = menu.exec(button_widget.mapToGlobal(position))
        if action == save_action:
            self.save_color_to_swatch(index, self.selected_qcolor)
        elif action == clear_action:
            self.clear_swatch(index)

    def save_color_to_swatch(self, index, color: QColor):
        button = self.custom_swatch_buttons[index]
        button.setStyleSheet(f"background-color: {color.name()}; border: 1px solid #888;")
        self.save_custom_swatches_to_config()

    def clear_swatch(self, index):
        button = self.custom_swatch_buttons[index]
        button.setStyleSheet(f"QPushButton#CustomSwatchButton {{ background-color: #333; border: 1px dashed #666; }}")
        self.save_custom_swatches_to_config()

    def update_all_custom_swatch_buttons_ui(self, colors_hex_list):
        default_empty_style = "QPushButton#CustomSwatchButton { background-color: #333; border: 1px dashed #666; }"
        for i, button in enumerate(self.custom_swatch_buttons):
            if i < len(colors_hex_list) and colors_hex_list[i] and QColor(colors_hex_list[i]).isValid():
                color = QColor(colors_hex_list[i])
                button.setStyleSheet(f"background-color: {color.name()}; border: 1px solid #888;")
            else:
                button.setStyleSheet(default_empty_style)

    def get_config_path(self):
        base_path = os.path.dirname(os.path.abspath(sys.argv[0]))
        return os.path.join(base_path, CONFIG_FILE_NAME)

    def save_custom_swatches_to_config(self):
        swatch_colors_hex = []
        for button in self.custom_swatch_buttons:
            style = button.styleSheet()
            if "background-color:" in style and "dashed" not in style:
                color_str = style.split("background-color:")[1].split(";")[0].strip()
                q_color_obj = QColor(color_str)
                if q_color_obj.isValid() and color_str.lower() != "#333333":
                     swatch_colors_hex.append(q_color_obj.name())
                else:
                    swatch_colors_hex.append(None) 
            else:
                swatch_colors_hex.append(None)
        
        config_path = self.get_config_path()
        try:
            with open(config_path, "w") as f:
                json.dump({"custom_swatches": swatch_colors_hex, "prefab_swatches_editable": True}, f, indent=4)
        except Exception as e:
            print(f"Error saving custom swatches: {e}")

    def load_custom_swatches(self):
        config_path = self.get_config_path()
        
        prefabs_hex = ["#FF0000", "#00FF00", "#0000FF", "#FFFF00", "#00FFFF", "#FF00FF", "#FFFFFF", "#808080"]
        
        initial_swatches = [None] * self.num_custom_swatches 

        try:
            if os.path.exists(config_path):
                with open(config_path, "r") as f:
                    config_data = json.load(f)
                    if config_data.get("prefab_swatches_editable", False) and "custom_swatches" in config_data:
                        loaded_swatches_hex = config_data.get("custom_swatches", [])
                        initial_swatches = (loaded_swatches_hex + [None] * self.num_custom_swatches)[:self.num_custom_swatches]
                    else:
                        for i in range(min(len(prefabs_hex), self.num_custom_swatches)):
                            initial_swatches[i] = prefabs_hex[i]
            else:
                for i in range(min(len(prefabs_hex), self.num_custom_swatches)):
                     initial_swatches[i] = prefabs_hex[i]
        except Exception as e:
            print(f"Error loading/initializing custom swatches: {e}")
            for i in range(min(len(prefabs_hex), self.num_custom_swatches)):
                initial_swatches[i] = prefabs_hex[i]

        self.update_all_custom_swatch_buttons_ui(initial_swatches)

    def show_pad_context_menu(self, pad_button_widget, row, col, position):
        menu = QMenu()
        set_black_action = QAction("Set Pad to Black (Off)", self)
        set_black_action.triggered.connect(lambda: self.set_single_pad_black(row, col))
        menu.addAction(set_black_action)
        menu.exec(pad_button_widget.mapToGlobal(position))

    def set_single_pad_black(self, row, col):
        if self.akai_controller.is_connected():
            self.akai_controller.set_pad_color(row, col, 0, 0, 0)
            self.update_gui_pad_color(row, col, 0, 0, 0)

    def update_gui_pad_color(self, row, col, r, g, b):
        button = self.pad_buttons.get((row, col))
        if button:
            if r == 0 and g == 0 and b == 0:
                button.setStyleSheet(f"""QPushButton#PadButton {{ background-color: #1C1C1C; border: 1px solid #404040; border-radius: 2px; color: transparent; }} QPushButton#PadButton:hover {{ border: 1px solid #666666; }}""")
            else:
                luminance = 0.299 * r + 0.587 * g + 0.114 * b
                text_color = "#E0E0E0" if luminance < 128 else "#1C1C1C"
                button.setStyleSheet(f"""QPushButton#PadButton {{ background-color: rgb({r},{g},{b}); border: 1px solid qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:1, stop:0 rgba({max(0,r-20)}, {max(0,g-20)}, {max(0,b-20)}, 255), stop:1 rgba({min(255,r+20)}, {min(255,g+20)}, {min(255,b+20)}, 255)); color: {text_color}; border-radius: 2px; }} QPushButton#PadButton:hover {{ border: 1px solid {text_color}; }}""")

    def clear_all_hardware_pads(self):
        if self.akai_controller.is_connected():
            self.akai_controller.clear_all_pads()
            for r_idx in range(4):
                for c_idx in range(16):
                    self.update_gui_pad_color(r_idx, c_idx, 0, 0, 0)
            self.status_bar.showMessage("All device pads cleared.", 2000)
        else:
            self.status_bar.showMessage("Not connected to AKAI Fire.", 2000)

    def populate_midi_ports(self):
        self.port_combo.clear()
        ports = AkaiFireController.get_available_ports()
        if ports:
            self.port_combo.addItems(ports)
            for i, port_name in enumerate(ports):
                if ("fire" in port_name.lower() or "akai" in port_name.lower()) and "midiin" not in port_name.lower():
                    self.port_combo.setCurrentIndex(i)
                    break
        else:
            self.port_combo.addItem("No MIDI ports found"); self.port_combo.setEnabled(False)
    
    def toggle_connection(self):
        if self.akai_controller.is_connected(): self.akai_controller.disconnect()
        else:
            selected_port = self.port_combo.currentText()
            if selected_port and selected_port != "No MIDI ports found": self.akai_controller.connect(selected_port)
            else: self.status_bar.showMessage("Please select a valid MIDI port.", 3000)
        self.update_connection_status()

    def update_connection_status(self):
        is_connected = self.akai_controller.is_connected()
        self.connect_button.setText("Disconnect" if is_connected else "Connect")
        self.status_bar.showMessage(f"Connected to {self.akai_controller.port_name_used}" if is_connected else "Disconnected.")
        self.port_combo.setEnabled(not is_connected)
        self.pad_grid_frame.setEnabled(is_connected)
        self.clear_all_button.setEnabled(is_connected)
        
        for widget in [self.sv_picker_widget, self.hue_slider_widget, 
                       self.r_input, self.g_input, self.b_input,
                       self.h_input, self.s_input, self.v_input,
                       self.hex_input_lineedit, self.main_color_preview_swatch,
                       self.findChild(QPushButton, "+ Add Current Color"),
                       self.color_button_off]:
            if widget: widget.setEnabled(is_connected)
        for swatch in self.custom_swatch_buttons:
            swatch.setEnabled(is_connected)

        if not is_connected: self.populate_midi_ports()

    def closeEvent(self, event):
        self.save_custom_swatches_to_config()
        if self.akai_controller.is_connected(): self.akai_controller.disconnect()
        event.accept()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    try:
        with open("../resources/styles/style.qss", "r") as f:
            app.setStyleSheet(f.read())
    except FileNotFoundError:
         try:
            with open("resources/styles/style.qss", "r") as f:
                app.setStyleSheet(f.read())
         except FileNotFoundError:
            print("Warning: Stylesheet not found. Using default styles.")
        
    main_win = MainWindow()
    main_win.show()
    sys.exit(app.exec())