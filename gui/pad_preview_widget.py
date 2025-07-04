# AKAI_Fire_PixelForge/gui/pad_preview_widget.py

from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPainter, QColor, QPalette
from PIL.Image import Image
from PIL.ImageQt import ImageQt


class PadPreviewWidget(QWidget):
    """
    A custom widget to reliably draw and scale the 16x4 pad preview,
    maintaining the correct portrait aspect ratio for each individual pad.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._colors: list[tuple[int, int, int]] | None = None
        self.setMinimumSize(240, 60)
        # --- Import QSizePolicy and use the correct reference ---
        from PyQt6.QtWidgets import QSizePolicy
        self.setSizePolicy(QSizePolicy.Policy.Expanding,
                            QSizePolicy.Policy.Expanding)
        self.setAutoFillBackground(True)
        palette = self.palette()
        palette.setColor(QPalette.ColorRole.Window, QColor('black'))
        self.setPalette(palette)
        self.pad_aspect_ratio = 40 / 50

    def set_colors(self, rgb_tuples: list[tuple[int, int, int]] | None):
        """Sets the list of 64 RGB tuples to be drawn."""
        self._colors = rgb_tuples
        self.update()

    def paintEvent(self, event):
        """Overrides paintEvent to draw 64 individual pads with the correct aspect ratio."""
        painter = QPainter(self)
        if not self._colors or len(self._colors) != 64:
            painter.fillRect(self.rect(), Qt.GlobalColor.black)
            return

        widget_w = self.width()
        widget_h = self.height()

        # --- Calculate pad dimensions based on widget size and aspect ratio ---
        # Total grid aspect ratio is (16 * pad_width) / (4 * pad_height)
        # (16 * 40) / (4 * 50) = 640 / 200 = 3.2
        grid_aspect_ratio = (16 * self.pad_aspect_ratio) / 4

        grid_h = widget_h
        grid_w = grid_h * grid_aspect_ratio

        if grid_w > widget_w:
            grid_w = widget_w
            grid_h = grid_w / grid_aspect_ratio

        pad_w = grid_w / 16
        pad_h = grid_h / 4

        start_x = (widget_w - grid_w) / 2
        start_y = (widget_h - grid_h) / 2

        grid_line_color = QColor(40, 40, 40)

        for i, rgb in enumerate(self._colors):
            col = i % 16
            row = i // 16

            x = start_x + (col * pad_w)
            y = start_y + (row * pad_h)

            painter.setBrush(QColor(*rgb))
            painter.setPen(grid_line_color)
            painter.drawRect(int(x), int(y), int(pad_w), int(pad_h))
