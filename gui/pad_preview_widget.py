# AKAI_Fire_PixelForge/gui/pad_preview_widget.py

from PyQt6.QtWidgets import QWidget, QSizePolicy
from PyQt6.QtCore import QSize, Qt
from PyQt6.QtGui import QPainter, QColor, QPalette
from PIL.Image import Image


class PadPreviewWidget(QWidget):
    """
    A custom widget to reliably draw and scale the 16x4 pad preview,
    maintaining the correct aspect ratio for the pads and the overall grid.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self._colors: list[tuple[int, int, int]] | None = None
        # The overall grid has a 3.2:1 aspect ratio (16*40 / 4*50)
        self.grid_aspect_ratio = 3.2
        # --- Implement smart resizing ---
        self.setSizePolicy(QSizePolicy.Policy.Expanding,
                            QSizePolicy.Policy.MinimumExpanding)
        self.setMinimumSize(240, int(240 / self.grid_aspect_ratio))

        self.setAutoFillBackground(True)
        palette = self.palette()
        palette.setColor(QPalette.ColorRole.Window, QColor('black'))
        self.setPalette(palette)

    def set_colors(self, rgb_tuples: list[tuple[int, int, int]] | None):
        """Sets the list of 64 RGB tuples to be drawn."""
        self._colors = rgb_tuples
        self.update()  # Trigger a repaint

    # --- Implement smart height calculation for proportional resizing ---
    def hasHeightForWidth(self) -> bool:
        return True

    def heightForWidth(self, width: int) -> int:
        return int(width / self.grid_aspect_ratio)

    def paintEvent(self, event):
        """Overrides paintEvent to draw 64 individual pads, filling the width."""
        painter = QPainter(self)
        if not self._colors or len(self._colors) != 64:
            painter.fillRect(self.rect(), Qt.GlobalColor.black)
            return
        widget_w = self.width()
        # --- Calculate dimensions based on WIDTH first ---
        grid_w = widget_w
        grid_h = self.heightForWidth(grid_w)
        pad_w = grid_w / 16
        pad_h = grid_h / 4
        # Center the grid vertically if there's extra space
        start_y = (self.height() - grid_h) / 2
        start_x = 0
        grid_line_color = QColor(40, 40, 40)
        for i, rgb in enumerate(self._colors):
            col = i % 16
            row = i // 16
            x = start_x + (col * pad_w)
            y = start_y + (row * pad_h)
            painter.setBrush(QColor(*rgb))
            painter.setPen(grid_line_color)
            # Add 1 to width/height to fill tiny gaps from integer conversion
            painter.drawRect(int(x), int(y), int(pad_w + 1), int(pad_h + 1))
