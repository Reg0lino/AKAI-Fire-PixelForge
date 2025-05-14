# AKAI_Fire_RGB_Controller/gui/sv_picker.py
from PyQt6.QtWidgets import QWidget, QSizePolicy
from PyQt6.QtGui import QPainter, QColor, QLinearGradient, QPen, QBrush, QPixmap, QImage
from PyQt6.QtCore import Qt, pyqtSignal, QPoint, QRectF, QPointF, QSize

class SVPicker(QWidget):
    # Emits saturation (0.0-1.0) and value (0.0-1.0)
    sv_changed = pyqtSignal(float, float) 

    def __init__(self, parent=None):
        super().__init__(parent)
        self._hue = 0  # 0-359, set externally
        self._saturation = 1.0 # 0.0 - 1.0
        self._value = 1.0      # 0.0 - 1.0
        self._handle_pos = QPointF(0,0) # Position based on S and V

        self.setMinimumSize(150, 100)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        
        self._gradient_pixmap = QPixmap() # To cache the complex gradient
        self._rebuild_gradient_pixmap()

    def setHue(self, hue_val):
        hue_val = max(0, min(359, int(hue_val)))
        if self._hue != hue_val:
            self._hue = hue_val
            self._rebuild_gradient_pixmap()
            self.update() # Redraw with new hue

    def setSV(self, saturation, value):
        saturation = max(0.0, min(1.0, float(saturation)))
        value = max(0.0, min(1.0, float(value)))
        
        # print(f"SVPicker setSV: S={saturation}, V={value}") # DEBUG

        if self._saturation != saturation or self._value != value:
            self._saturation = saturation
            self._value = value
            self._update_handle_pos_from_sv()
            self.sv_changed.emit(self._saturation, self._value)
            self.update()

    def saturation(self):
        return self._saturation

    def value(self):
        return self._value

    def _rebuild_gradient_pixmap(self):
        # Create an image to draw the gradient onto
        # Use a fixed size for image cache for performance, then scale if needed.
        # Or, rebuild on every resize, but that can be slow.
        # For now, let's try rebuilding on resize within paintEvent or a separate call.
        # This is simpler for now:
        if self.width() <=0 or self.height() <=0:
            return

        img = QImage(self.width(), self.height(), QImage.Format.Format_RGB32)
        painter = QPainter(img)

        # Saturation gradient (left to right)
        saturation_gradient = QLinearGradient(0, 0, self.width(), 0)
        saturation_gradient.setColorAt(0, QColor.fromHsvF(self._hue / 360.0, 0.0, 1.0)) # White (S=0, V=1) at fixed hue
        saturation_gradient.setColorAt(1, QColor.fromHsvF(self._hue / 360.0, 1.0, 1.0)) # Full color (S=1, V=1) at fixed hue
        painter.fillRect(img.rect(), saturation_gradient)

        # Value gradient (top to bottom, black overlay)
        value_gradient = QLinearGradient(0, 0, 0, self.height())
        value_gradient.setColorAt(0, QColor(0, 0, 0, 0))    # Transparent black at top (V=1)
        value_gradient.setColorAt(1, QColor(0, 0, 0, 255)) # Opaque black at bottom (V=0)
        painter.fillRect(img.rect(), value_gradient)
        
        painter.end()
        self._gradient_pixmap = QPixmap.fromImage(img)
        self._update_handle_pos_from_sv() # Ensure handle is correct for current S,V

    def _update_handle_pos_from_sv(self):
        # Value (brightness) typically maps to Y axis (0 at bottom, 1 at top)
        # Saturation typically maps to X axis (0 at left, 1 at right)
        x = self._saturation * self.width()
        y = (1.0 - self._value) * self.height() # Invert Y as 0,0 is top-left
        self._handle_pos = QPointF(x, y)

    def _update_sv_from_pos(self, pos: QPointF):
        s = max(0.0, min(1.0, pos.x() / self.width() if self.width() > 0 else 0))
        v = 1.0 - max(0.0, min(1.0, pos.y() / self.height() if self.height() > 0 else 0)) # Invert Y
        self.setSV(s, v) # This will emit signal if changed

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Draw the cached gradient pixmap
        if not self._gradient_pixmap.isNull() and \
           (self._gradient_pixmap.width() != self.width() or self._gradient_pixmap.height() != self.height()):
            self._rebuild_gradient_pixmap() # Rebuild if size changed

        if not self._gradient_pixmap.isNull():
            painter.drawPixmap(0, 0, self._gradient_pixmap)
        else: # Fallback if pixmap is not ready
            painter.fillRect(self.rect(), Qt.GlobalColor.gray)


        # Draw handle (small circle)
        handle_radius = 6
        pen_color = Qt.GlobalColor.white if self._value > 0.5 or self._saturation < 0.5 else Qt.GlobalColor.black
        
        painter.setPen(QPen(pen_color, 1.5))
        painter.setBrush(Qt.BrushStyle.NoBrush) # No fill for the circle, just an outline
        
        # Ensure handle_pos is within bounds before drawing
        draw_x = max(handle_radius, min(self._handle_pos.x(), self.width() - handle_radius))
        draw_y = max(handle_radius, min(self._handle_pos.y(), self.height() - handle_radius))
        
        painter.drawEllipse(QPointF(draw_x, draw_y), handle_radius, handle_radius)
        painter.end()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._update_sv_from_pos(event.position())
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.MouseButton.LeftButton:
            self._update_sv_from_pos(event.position())
            event.accept()

    def resizeEvent(self, event):
        # print(f"SVPicker Resized: {event.size()}") # DEBUG
        self._rebuild_gradient_pixmap() # Rebuild gradient when widget is resized
        self._update_handle_pos_from_sv() # Recalculate handle position
        self.update()
        super().resizeEvent(event)

    def minimumSizeHint(self):
        return QSize(100, 80)