# AKAI_Fire_RGB_Controller/gui/hue_slider.py
from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt, pyqtSignal, QRect, QPoint
from PyQt6.QtGui import QPainter, QColor, QMouseEvent

class HueSlider(QWidget):
    hue_changed = pyqtSignal(int)  # Emits hue value (0-359)

    def __init__(self, orientation=Qt.Orientation.Vertical, parent=None):
        super().__init__(parent)
        self._hue = 0
        self._orientation = orientation
        self.setMinimumWidth(24)
        self.setMinimumHeight(120)
        self.setMaximumWidth(40)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    def setHue(self, hue):
        hue = int(max(0, min(359, hue)))
        if self._hue != hue:
            self._hue = hue
            self.hue_changed.emit(self._hue)
            self.update()

    def hue(self):
        return self._hue

    def paintEvent(self, event):
        painter = QPainter(self)
        if self._orientation == Qt.Orientation.Vertical:
            for y in range(self.height()):
                hue = int(359 * (1 - y / (self.height() - 1)))
                color = QColor.fromHsv(hue, 255, 255)
                painter.setPen(color)
                painter.drawLine(0, y, self.width(), y)
            # Draw handle
            handle_y = int((1 - self._hue / 359) * (self.height() - 1))
            painter.setPen(Qt.GlobalColor.black)
            painter.drawRect(0, handle_y - 2, self.width() - 1, 4)
        else:
            for x in range(self.width()):
                hue = int(359 * (x / (self.width() - 1)))
                color = QColor.fromHsv(hue, 255, 255)
                painter.setPen(color)
                painter.drawLine(x, 0, x, self.height())
            handle_x = int((self._hue / 359) * (self.width() - 1))
            painter.setPen(Qt.GlobalColor.black)
            painter.drawRect(handle_x - 2, 0, 4, self.height() - 1)

    def mousePressEvent(self, event: QMouseEvent):
        self._set_hue_from_pos(event.position())
        event.accept()

    def mouseMoveEvent(self, event: QMouseEvent):
        if event.buttons() & Qt.MouseButton.LeftButton:
            self._set_hue_from_pos(event.position())
            event.accept()

    def _set_hue_from_pos(self, pos):
        if self._orientation == Qt.Orientation.Vertical:
            y = int(pos.y())
            y = max(0, min(self.height() - 1, y))
            hue = int(359 * (1 - y / (self.height() - 1)))
        else:
            x = int(pos.x())
            x = max(0, min(self.width() - 1, x))
            hue = int(359 * (x / (self.width() - 1)))
        self.setHue(hue)