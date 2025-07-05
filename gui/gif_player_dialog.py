# AKAI_Fire_PixelForge/gui/gif_player_dialog.py

from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QDialogButtonBox
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QMovie


class GifPlayerDialog(QDialog):
    """A simple dialog to play a GIF using QMovie."""

    def __init__(self, gif_path: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Original GIF Preview")
        layout = QVBoxLayout(self)
        self.movie_label = QLabel("Loading GIF...")
        self.movie_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.movie_label)
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        button_box.accepted.connect(self.accept)
        layout.addWidget(button_box)
        self.movie = QMovie(gif_path)
        if self.movie.isValid():
            self.movie_label.setMovie(self.movie)
            # --- THE DEFINITIVE FIX for reliable resizing ---
            gif_size = self.movie.frameRect().size()
            # Get the available screen geometry to clamp the max size
            screen_geometry = self.screen().availableGeometry()
            max_w = int(screen_geometry.width() * 0.9)
            max_h = int(screen_geometry.height() * 0.9)
            # Scale the GIF size down if it's larger than our max
            if gif_size.width() > max_w or gif_size.height() > max_h:
                gif_size.scale(QSize(max_w, max_h),
                                Qt.AspectRatioMode.KeepAspectRatio)
            # Get the size of the other widgets and layout margins
            button_box_height = button_box.sizeHint().height()
            layout_margins = layout.contentsMargins()
            total_vertical_margin = layout_margins.top() + layout_margins.bottom() + \
                layout.spacing()
            # Calculate the final dialog size and set it directly
            final_width = gif_size.width() + layout_margins.left() + layout_margins.right()
            final_height = gif_size.height() + button_box_height + total_vertical_margin
            self.resize(final_width, final_height)
            self.movie.start()
        else:
            self.movie_label.setText(
                f"Error: Could not load GIF from\n{gif_path}")

    def closeEvent(self, event):
        """Ensure the movie stops when the dialog is closed."""
        self.movie.stop()
        super().closeEvent(event)
