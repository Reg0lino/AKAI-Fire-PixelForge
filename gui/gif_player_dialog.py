# AKAI_Fire_PixelForge/gui/gif_player_dialog.py

from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QDialogButtonBox
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QMovie


class GifPlayerDialog(QDialog):
    """A simple dialog to play a GIF using QMovie."""

    def __init__(self, gif_path: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Original GIF Preview")
        self.setMinimumSize(400, 400)
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
            # Resize the dialog to fit the GIF, up to a max size
            gif_size = self.movie.frameRect().size()
            max_size = QSize(800, 800)
            if gif_size.width() > max_size.width() or gif_size.height() > max_size.height():
                gif_size.scale(max_size, Qt.AspectRatioMode.KeepAspectRatio)
            self.resize(gif_size)
            self.movie.start()
        else:
            self.movie_label.setText(
                f"Error: Could not load GIF from\n{gif_path}")

    def closeEvent(self, event):
        """Ensure the movie stops when the dialog is closed."""
        self.movie.stop()
        super().closeEvent(event)
