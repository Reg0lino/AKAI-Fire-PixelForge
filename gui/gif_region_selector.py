# AKAI_Fire_PixelForge/gui/gif_region_selector.py

from PyQt6.QtWidgets import QLabel
from PyQt6.QtCore import Qt, pyqtSignal, QRectF, QPointF, QSize, QSizeF
from PyQt6.QtGui import QPainter, QPen, QColor, QCursor, QMouseEvent

class GifRegionSelectorLabel(QLabel):
    """
    A custom QLabel that displays a pixmap and allows the user to draw, move,
    and resize a selection rectangle on top of it. Emits the final region
    as a percentage of the label's dimensions.
    """
    # Emits a dict: {'x': float, 'y': float, 'width': float, 'height': float}
    region_changed = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMouseTracking(True)
        # Selection stored in absolute pixel coordinates
        self.selection_rect = QRectF(0.0, 0.0, 0.0, 0.0)
        # The actual rect of the displayed pixmap
        self.pixmap_rect = QRectF(0.0, 0.0, 0.0, 0.0)
        self._is_dragging = False
        self._is_resizing = False
        self._drag_start_pos = QPointF()
        self._resize_handle = None
        self.handle_size = 8  # Size of resize handles

    def setPixmap(self, pixmap):
        """Overrides setPixmap to also calculate the displayed image's geometry."""
        super().setPixmap(pixmap)
        if not pixmap or pixmap.isNull():
            self.pixmap_rect = QRectF(0, 0, 0, 0)
            return
        # Calculate the rect where the pixmap is actually drawn (centered, aspect-ratio preserved)
        pixmap_size = pixmap.size()
        label_size = self.size()
        scaled_size = pixmap_size.scaled(
            label_size, Qt.AspectRatioMode.KeepAspectRatio)
        x = (label_size.width() - scaled_size.width()) / 2
        y = (label_size.height() - scaled_size.height()) / 2
        self.pixmap_rect = QRectF(
            x, y, scaled_size.width(), scaled_size.height())
        self.set_full_region()  # Default to full region when a new pixmap is set

    def set_full_region(self):
        """Sets the selection to cover the entire displayed pixmap."""
        self.selection_rect = QRectF(self.pixmap_rect)
        self._emit_region_change()
        self.update()

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton and self.pixmap_rect.contains(event.position()):
            self._resize_handle = self._get_handle_at(event.position())
            if self._resize_handle:
                self._is_resizing = True
            elif self.selection_rect.contains(event.position()):
                self._is_dragging = True
            else:
                # Start drawing a new rectangle
                self._is_dragging = False
                self._is_resizing = False
                self.selection_rect.setTopLeft(event.position())
                self.selection_rect.setBottomRight(event.position())
            self._drag_start_pos = event.position()
            self.update()

    def mouseMoveEvent(self, event: QMouseEvent):
        pos = event.position()
        # Determine cursor style based on position
        handle = self._get_handle_at(pos)
        if handle:
            if handle in ('topLeft', 'bottomRight'):
                self.setCursor(Qt.CursorShape.SizeFDiagCursor)
            elif handle in ('topRight', 'bottomLeft'):
                self.setCursor(Qt.CursorShape.SizeBDiagCursor)
            elif handle in ('top', 'bottom'):
                self.setCursor(Qt.CursorShape.SizeVerCursor)
            else:
                self.setCursor(Qt.CursorShape.SizeHorCursor)
        elif self.selection_rect.contains(pos):
            self.setCursor(QCursor(Qt.CursorShape.SizeAllCursor))
        else:
            self.setCursor(QCursor(Qt.CursorShape.CrossCursor))
        # Handle dragging/resizing logic if the left mouse button is pressed
        if event.buttons() & Qt.MouseButton.LeftButton:
            if self._is_resizing:
                self._resize_selection(pos)
            elif self._is_dragging:
                self._move_selection(pos)
            else:  # Drawing a new rectangle
                self.selection_rect.setBottomRight(
                    self._constrain_point_to_pixmap(pos))
        # --- FIX: Unconditionally update the widget to force a repaint on every mouse move ---
        self.update()

    def mouseReleaseEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self._is_dragging = False
            self._is_resizing = False
            self._resize_handle = None
            self.setCursor(QCursor(Qt.CursorShape.ArrowCursor))
            # Ensure the rectangle is normalized (topLeft is actually top-left)
            self.selection_rect = self.selection_rect.normalized()
            self._emit_region_change()
            self.update()

    def paintEvent(self, event):
        # First, let the parent QLabel draw the pixmap
        super().paintEvent(event)
        if self.pixmap_rect.width() > 0 and not self.selection_rect.isNull():
            painter = QPainter(self)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            # --- Draw the Selection Outline ---
            pen = QPen(QColor(0, 120, 215, 255), 2, Qt.PenStyle.SolidLine)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)  # No fill color
            painter.drawRect(self.selection_rect)
            # --- Draw Resize Handles ---
            painter.setBrush(QColor(0, 120, 215, 255))
            painter.setPen(Qt.PenStyle.NoPen)
            for handle_pos in self._get_handle_positions().values():
                painter.drawRect(QRectF(handle_pos, QPointF(
                    handle_pos.x() + self.handle_size, handle_pos.y() + self.handle_size)))

    def _constrain_point_to_pixmap(self, point: QPointF) -> QPointF:
        """Constrains a point to be within the bounds of the displayed pixmap."""
        x = max(self.pixmap_rect.left(), min(
            point.x(), self.pixmap_rect.right()))
        y = max(self.pixmap_rect.top(), min(
            point.y(), self.pixmap_rect.bottom()))
        return QPointF(x, y)

    def _emit_region_change(self):
        """Calculates region as a percentage of the pixmap and emits it."""
        if self.pixmap_rect.width() > 0 and self.pixmap_rect.height() > 0:
            x_pct = (self.selection_rect.left() -
                    self.pixmap_rect.left()) / self.pixmap_rect.width()
            y_pct = (self.selection_rect.top() -
                    self.pixmap_rect.top()) / self.pixmap_rect.height()
            w_pct = self.selection_rect.width() / self.pixmap_rect.width()
            h_pct = self.selection_rect.height() / self.pixmap_rect.height()
            # Clamp values to be within [0.0, 1.0]
            x_pct = max(0.0, min(x_pct, 1.0))
            y_pct = max(0.0, min(y_pct, 1.0))
            w_pct = max(0.0, min(w_pct, 1.0))
            h_pct = max(0.0, min(h_pct, 1.0))
            self.region_changed.emit(
                {'x': x_pct, 'y': y_pct, 'width': w_pct, 'height': h_pct})

    # --- Helper methods for resizing and moving ---
    def _get_handle_positions(self):
        x, y, w, h = self.selection_rect.x(), self.selection_rect.y(
        ), self.selection_rect.width(), self.selection_rect.height()
        hs = self.handle_size / 2
        return {
            'topLeft': QPointF(x - hs, y - hs), 'top': QPointF(x + w/2 - hs, y - hs), 'topRight': QPointF(x + w - hs, y - hs),
            'left': QPointF(x - hs, y + h/2 - hs), 'right': QPointF(x + w - hs, y + h/2 - hs),
            'bottomLeft': QPointF(x - hs, y + h - hs), 'bottom': QPointF(x + w/2 - hs, y + h - hs), 'bottomRight': QPointF(x + w - hs, y + h - hs)
        }

    def _get_handle_at(self, pos: QPointF):
        for handle, handle_pos in self._get_handle_positions().items():
            if QRectF(handle_pos, QSizeF(self.handle_size, self.handle_size)).contains(pos):
                return handle
        return None

    def _move_selection(self, pos: QPointF):
        delta = pos - self._drag_start_pos
        self._drag_start_pos = pos
        new_rect = self.selection_rect.translated(delta)
        # Constrain movement within pixmap bounds
        if new_rect.left() < self.pixmap_rect.left():
            new_rect.moveLeft(self.pixmap_rect.left())
        if new_rect.top() < self.pixmap_rect.top():
            new_rect.moveTop(self.pixmap_rect.top())
        if new_rect.right() > self.pixmap_rect.right():
            new_rect.moveRight(self.pixmap_rect.right())
        if new_rect.bottom() > self.pixmap_rect.bottom():
            new_rect.moveBottom(self.pixmap_rect.bottom())
        self.selection_rect = new_rect

    def _resize_selection(self, pos: QPointF):
        pos = self._constrain_point_to_pixmap(pos)
        if self._resize_handle == 'topLeft':
            self.selection_rect.setTopLeft(pos)
        elif self._resize_handle == 'topRight':
            self.selection_rect.setTopRight(pos)
        elif self._resize_handle == 'bottomLeft':
            self.selection_rect.setBottomLeft(pos)
        elif self._resize_handle == 'bottomRight':
            self.selection_rect.setBottomRight(pos)
        elif self._resize_handle == 'top':
            self.selection_rect.setTop(pos.y())
        elif self._resize_handle == 'bottom':
            self.selection_rect.setBottom(pos.y())
        elif self._resize_handle == 'left':
            self.selection_rect.setLeft(pos.x())
        elif self._resize_handle == 'right': self.selection_rect.setRight(pos.x())