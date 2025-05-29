# AKAI_Fire_RGB_Controller/gui/interactive_pad_grid.py
from PyQt6.QtWidgets import QFrame, QPushButton, QGridLayout, QSizePolicy
from PyQt6.QtCore import Qt, pyqtSignal, QPoint
from PyQt6.QtGui import QMouseEvent, QColor # Added QColor for styling logic
import re # Added for parsing color in get_current_grid_colors_hex

# --- Constants ---
PAD_BUTTON_WIDTH = 40
PAD_BUTTON_HEIGHT = 50
PAD_GRID_SPACING = 3
GRID_ROWS = 4
GRID_COLS = 16

class PadButton(QPushButton):
    request_context_action = pyqtSignal(int, int, QPoint) # row, col, local_pos_to_button
    single_click_action = pyqtSignal(int, int)      # row, col

    def __init__(self, row: int, col: int, parent=None):
        super().__init__(parent)
        self.row = row
        self.col = col
        self.setObjectName("PadButton")
        self.setFixedSize(PAD_BUTTON_WIDTH, PAD_BUTTON_HEIGHT)
        self.setCheckable(False)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)

    def mousePressEvent(self, event: QMouseEvent):
        # This is PadButton's mousePressEvent
        if event.button() == Qt.MouseButton.LeftButton:
            self.single_click_action.emit(self.row, self.col) # 'self' here is a PadButton
        event.ignore()

    def contextMenuEvent(self, event: QMouseEvent):
        # This is PadButton's contextMenuEvent
        self.request_context_action.emit(self.row, self.col, event.pos())
        event.accept()
class InteractivePadGridFrame(QFrame):
    pad_action_requested = pyqtSignal(
        int, int, Qt.MouseButton)  # row, col, button_type
    pad_context_menu_requested_from_button = pyqtSignal(
        object, int, int, QPoint)  # PadButton_obj, row, col, local_pos
    pad_single_left_click_action_requested = pyqtSignal(int, int)  # row, col
    # <<< NEW SIGNALS FOR PAINT STROKES >>>
    # row, col, button_type (of initial pad)
    paint_stroke_started = pyqtSignal(int, int, Qt.MouseButton)
    # button_type that ended the stroke
    paint_stroke_ended = pyqtSignal(Qt.MouseButton)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("PadGridFrame")
        self._pad_buttons: dict[tuple[int, int], PadButton] = {}
        self._is_left_dragging = False
        self._is_right_dragging = False
        self._last_actioned_pad_coords: tuple[int, int] | None = None
        self._init_ui()

    def _init_ui(self):
        self.pad_grid_layout = QGridLayout()
        self.pad_grid_layout.setSpacing(PAD_GRID_SPACING)
        self.pad_grid_layout.setContentsMargins(0,0,0,0)

        for r_idx in range(GRID_ROWS):
            for c_idx in range(GRID_COLS):
                pad_button = PadButton(row=r_idx, col=c_idx, parent=self)
                pad_button.request_context_action.connect(self._handle_pad_button_context_request)
                pad_button.single_click_action.connect(self._handle_pad_button_single_left_click)
                self._pad_buttons[(r_idx, c_idx)] = pad_button
                self.pad_grid_layout.addWidget(pad_button, r_idx, c_idx)
        
        self.setLayout(self.pad_grid_layout)

        margins = self.pad_grid_layout.contentsMargins()
        grid_width = (GRID_COLS * PAD_BUTTON_WIDTH) + ((GRID_COLS -1) * PAD_GRID_SPACING if GRID_COLS > 0 else 0) + margins.left() + margins.right()
        grid_height = (GRID_ROWS * PAD_BUTTON_HEIGHT) + ((GRID_ROWS -1) * PAD_GRID_SPACING if GRID_ROWS > 0 else 0) + margins.top() + margins.bottom()
        self.setFixedSize(grid_width, grid_height)

    def _handle_pad_button_context_request(self, row: int, col: int, local_pos: QPoint):
        button = self._pad_buttons.get((row, col))
        if button:
            self.pad_context_menu_requested_from_button.emit(button, row, col, local_pos)

    def _handle_pad_button_single_left_click(self, row: int, col: int):
        self.pad_single_left_click_action_requested.emit(row, col)

    def _get_pad_at_event_pos(self, event: QMouseEvent) -> PadButton | None:
        local_pos = event.position().toPoint() 
        child = self.childAt(local_pos)
        if isinstance(child, PadButton):
            return child
        return None

    def mousePressEvent(self, event: QMouseEvent):
        button_type = event.button()
        pad_button_widget = self._get_pad_at_event_pos(event)
        action_taken = False

        if button_type == Qt.MouseButton.LeftButton or button_type == Qt.MouseButton.RightButton:
            print(f"GRID DEBUG: mousePressEvent - Button: {button_type}") # <<< ADD DEBUG
            if button_type == Qt.MouseButton.LeftButton:
                self._is_left_dragging = True
                self._is_right_dragging = False
            else: 
                self._is_right_dragging = True
                self._is_left_dragging = False

            if pad_button_widget:
                print(f"GRID DEBUG: mousePressEvent - Emitting paint_stroke_started for pad ({pad_button_widget.row},{pad_button_widget.col})") # <<< ADD DEBUG
                self.paint_stroke_started.emit(pad_button_widget.row, pad_button_widget.col, button_type)
                self.pad_action_requested.emit(pad_button_widget.row, pad_button_widget.col, button_type)
                self._last_actioned_pad_coords = (pad_button_widget.row, pad_button_widget.col)
            else: 
                self._last_actioned_pad_coords = None
            action_taken = True
        
        if action_taken:
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent):
        action_taken_on_release = False
        button_released = event.button()
        # print(f"GRID DEBUG: mouseReleaseEvent - Button: {button_released}, LeftDragging: {self._is_left_dragging}, RightDragging: {self._is_right_dragging}") # <<< ADD DEBUG

        if button_released == Qt.MouseButton.LeftButton and self._is_left_dragging:
            self._is_left_dragging = False
            self._last_actioned_pad_coords = None
            action_taken_on_release = True
            # print(f"GRID DEBUG: mouseReleaseEvent - Emitting paint_stroke_ended for LeftButton") # <<< ADD DEBUG
            self.paint_stroke_ended.emit(Qt.MouseButton.LeftButton)
        elif button_released == Qt.MouseButton.RightButton and self._is_right_dragging:
            self._is_right_dragging = False
            self._last_actioned_pad_coords = None
            action_taken_on_release = True
            # print(f"GRID DEBUG: mouseReleaseEvent - Emitting paint_stroke_ended for RightButton") # <<< ADD DEBUG
            self.paint_stroke_ended.emit(Qt.MouseButton.RightButton)
        
        if action_taken_on_release:
            event.accept()
        else:
            super().mouseReleaseEvent(event)
    def mouseMoveEvent(self, event: QMouseEvent):
        # This is InteractivePadGridFrame's mouseMoveEvent
        pad_button_widget = self._get_pad_at_event_pos(event)
        action_taken_on_move = False

        if self._is_left_dragging and (event.buttons() & Qt.MouseButton.LeftButton):
            if pad_button_widget:
                current_coords = (pad_button_widget.row, pad_button_widget.col)
                if current_coords != self._last_actioned_pad_coords:
                    self.pad_action_requested.emit(pad_button_widget.row, pad_button_widget.col, Qt.MouseButton.LeftButton)
                    self._last_actioned_pad_coords = current_coords
            else: # Moving over spacing while dragging
                self._last_actioned_pad_coords = None
            action_taken_on_move = True
            
        elif self._is_right_dragging and (event.buttons() & Qt.MouseButton.RightButton):
            if pad_button_widget:
                current_coords = (pad_button_widget.row, pad_button_widget.col)
                if current_coords != self._last_actioned_pad_coords:
                    self.pad_action_requested.emit(pad_button_widget.row, pad_button_widget.col, Qt.MouseButton.RightButton)
                    self._last_actioned_pad_coords = current_coords
            else: # Moving over spacing
                self._last_actioned_pad_coords = None
            action_taken_on_move = True

        if action_taken_on_move:
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def update_pad_gui_color(self, row: int, col: int, r_val: int, g_val: int, b_val: int):
        button = self._pad_buttons.get((row, col))
        if button:
            current_color = QColor(r_val, g_val, b_val)
            style_parts = ["border-radius:2px;"]
            is_off = (r_val == 0 and g_val == 0 and b_val == 0)
            if is_off:
                style_parts.append("background-color: #1C1C1C; border: 1px solid #404040; color: transparent;")
                hover_border_color = "#666666"
            else:
                style_parts.append(f"background-color: {current_color.name()};")
                border_color_dark = current_color.darker(110).name()
                border_color_light = current_color.lighter(110).name()
                style_parts.append(f"border: 1px solid qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 {border_color_dark}, stop:1 {border_color_light});")
                luminance = 0.299 * r_val + 0.587 * g_val + 0.114 * b_val
                text_color = "#E0E0E0" if luminance < 128 else "#1C1C1C"
                style_parts.append(f"color: {text_color};")
                hover_border_color = text_color
            final_style = f"QPushButton#PadButton {{{';'.join(style_parts)}}}" \
                          f"QPushButton#PadButton:hover {{border: 1px solid {hover_border_color};}}"
            button.setStyleSheet(final_style)

    def get_current_grid_colors_hex(self) -> list[str]:
        colors_hex = []
        for r_idx in range(GRID_ROWS):
            for c_idx in range(GRID_COLS):
                button = self._pad_buttons.get((r_idx, c_idx))
                hex_color_str = QColor("black").name() 
                if button:
                    style = button.styleSheet()
                    match = re.search(r"background-color\s*:\s*(#[0-9a-fA-F]{6})", style, re.IGNORECASE)
                    if match:
                        parsed_hex = match.group(1)
                        temp_c = QColor(parsed_hex)
                        if temp_c.isValid():
                            hex_color_str = temp_c.name()
                    elif "#1C1C1C" in style: 
                        hex_color_str = QColor("black").name()
                colors_hex.append(hex_color_str)
        return colors_hex

    def get_pad_button_instance(self, row: int, col: int) -> PadButton | None:
        return self._pad_buttons.get((row, col))