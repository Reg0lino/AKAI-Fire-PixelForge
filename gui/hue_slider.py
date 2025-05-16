
# AKAI_Fire_RGB_Controller/gui/hue_slider.py
from PyQt6.QtWidgets import QWidget, QSizePolicy
from PyQt6.QtGui import QPainter, QColor, QLinearGradient, QPen, QBrush, QMouseEvent
from PyQt6.QtCore import Qt, pyqtSignal, QPoint, QRectF, QSize

class HueSlider(QWidget):
    hue_changed = pyqtSignal(int)  # Emits hue value from 0 to 359

    def __init__(self, parent=None):
        super().__init__(parent)
        self._hue = 0  # Current hue value (0-359)
        self.setMinimumSize(20, 100) # Width, Height
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self._gradient_rect = QRectF()
        self._handle_y_pos = 0

    def get_hue(self) -> int:
        return self._hue

    def set_hue(self, hue_val_0_359: int, emit_signal: bool = True):
        """
        Sets the hue value for the slider.
        :param hue_val_0_359: Hue value between 0 and 359.
        :param emit_signal: If True, emits the hue_changed signal. Set to False
                            when updating from an external source that shouldn't
                            trigger a reciprocal signal emission.
        """
        hue_val_0_359 = max(0, min(int(hue_val_0_359), 359))
        # print(f"HueSlider set_hue: val={hue_val_0_359}, current_hue={self._hue}, emit={emit_signal}") # Debug
        
        # Always update internal hue and repaint, even if value is same, 
        # to ensure consistency if called externally.
        # Signal emission is conditional.
        needs_update = self._hue != hue_val_0_359
        self._hue = hue_val_0_359
        self._update_handle_position()
        self.update() # Trigger repaint

        if emit_signal and needs_update:
            self.hue_changed.emit(self._hue)

    def _calculate_gradient_and_handle(self):
        padding = 8 # Padding for handle to not be cut off
        self._gradient_rect = QRectF(
            self.rect().left() + padding // 2,
            self.rect().top() + padding,
            self.rect().width() - padding,
            self.rect().height() - 2 * padding
        )
        self._update_handle_position()

    def _update_handle_position(self):
        if self._gradient_rect.height() > 0:
            # Map hue (0-359) to y-position within the gradient_rect
            # Y is inverted: 0 hue (red) at top, 359 hue (almost red) at bottom
            self._handle_y_pos = self._gradient_rect.top() + \
                                 (self._hue / 359.0) * self._gradient_rect.height()
        else:
            self._handle_y_pos = self._gradient_rect.top()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        if self._gradient_rect.isNull() or \
           self._gradient_rect.width() != self.width() - 8 or \
           self._gradient_rect.height() != self.height() - 16: 
            self._calculate_gradient_and_handle()

        if self._gradient_rect.isEmpty():
            return 

        hue_gradient = QLinearGradient(0, self._gradient_rect.top(), 0, self._gradient_rect.bottom())
        for i in range(7): 
            hue_gradient.setColorAt(i / 6.0, QColor.fromHsvF(i / 6.0, 1.0, 1.0))
        
        painter.fillRect(self._gradient_rect, hue_gradient)

        handle_width = self._gradient_rect.width() + 4 
        handle_height = 4 
        
        handle_rect = QRectF(
            self._gradient_rect.left() - 2, 
            self._handle_y_pos - (handle_height / 2.0),
            handle_width,
            handle_height
        )

        handle_base_color_for_luminance = QColor.fromHsvF(self._hue / 360.0, 1.0, 1.0) # Use a QColor to get luminance
        luminance = (0.299 * handle_base_color_for_luminance.redF() +
                     0.587 * handle_base_color_for_luminance.greenF() +
                     0.114 * handle_base_color_for_luminance.blueF())
        
        # Convert Qt.GlobalColor to QColor before using QColor methods
        if luminance > 0.5: # If the hue is light, use black for contrast
            actual_handle_border_color = QColor(Qt.GlobalColor.black)
            handle_fill_color = actual_handle_border_color.darker(120) # Darker black (still black or very dark grey)
        else: # If the hue is dark, use white for contrast
            actual_handle_border_color = QColor(Qt.GlobalColor.white)
            handle_fill_color = actual_handle_border_color.lighter(120) # Lighter white (still white or very light grey)

        painter.setPen(QPen(actual_handle_border_color, 1))
        painter.setBrush(QBrush(handle_fill_color)) # Use the fill color derived from the QColor object
        painter.drawRect(handle_rect)

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self._update_hue_from_pos(event.position().y())
            event.accept()

    def mouseMoveEvent(self, event: QMouseEvent):
        if event.buttons() & Qt.MouseButton.LeftButton:
            self._update_hue_from_pos(event.position().y())
            event.accept()

    def _update_hue_from_pos(self, y_pos: float):
        if self._gradient_rect.height() <= 0:
            return

        relative_y = y_pos - self._gradient_rect.top()
        normalized_y = max(0.0, min(1.0, relative_y / self._gradient_rect.height()))
        
        new_hue = int(round(normalized_y * 359.0)) # Map 0.0-1.0 to 0-359
        self.set_hue(new_hue, emit_signal=True) # This will update self._hue and emit if changed

    def resizeEvent(self, event):
        self._calculate_gradient_and_handle()
        super().resizeEvent(event)

    def minimumSizeHint(self):
        return QSize(25, 100)