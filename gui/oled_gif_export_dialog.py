# AKAI_Fire_RGB_Controller/gui/oled_gif_export_dialog.py
import sys
from PyQt6.QtWidgets import (
    QApplication, QDialog, QVBoxLayout, QFormLayout, QLabel,
    QSpinBox, QCheckBox, QDialogButtonBox, QWidget, QHBoxLayout
)
from PyQt6.QtCore import Qt


class OLEDGifExportDialog(QDialog):
    """
    A dialog for gathering user options before exporting an OLED animation to GIF.
    """

    def __init__(self, initial_fps: int, parent: QWidget | None = None):
        super().__init__(parent)
        self.setWindowTitle("Export OLED Graphic to GIF")
        self.setWindowFlags(self.windowFlags() & ~
                            Qt.WindowType.WindowContextHelpButtonHint)
        self.setMinimumWidth(350)
        # --- UI Widget Declarations ---
        self.scale_spinbox = QSpinBox()
        self.fps_spinbox = QSpinBox()
        self.delay_label = QLabel()
        self.invert_checkbox = QCheckBox("Invert Colors (B/W)")
        self.loop_checkbox = QCheckBox("Loop Animation Infinitely")
        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self._init_ui(initial_fps)
        self._connect_signals()

    def _init_ui(self, initial_fps: int):
        """Initializes and lays out the UI widgets."""
        main_layout = QVBoxLayout(self)
        form_layout = QFormLayout()
        form_layout.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapAllRows)
        form_layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        # Scale Factor
        self.scale_spinbox.setRange(1, 16)
        self.scale_spinbox.setValue(4)
        self.scale_spinbox.setSuffix(" x")
        self.scale_spinbox.setToolTip(
            "The multiplier for the output GIF dimensions (e.g., 4x results in 512x256).")
        form_layout.addRow(QLabel("Output Scale:"), self.scale_spinbox)
        # FPS and Delay
        self.fps_spinbox.setRange(1, 60)
        self.fps_spinbox.setValue(initial_fps)
        self.fps_spinbox.setSuffix(" FPS")
        self.fps_spinbox.setToolTip("Frames Per Second for the exported GIF.")
        self.delay_label.setMinimumWidth(80)
        self.delay_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        self._update_delay_label(initial_fps)  # Set initial text
        # Add FPS and delay label in a single row
        fps_layout = QHBoxLayout()
        fps_layout.addWidget(self.fps_spinbox, 1)  # Give spinbox stretch
        fps_layout.addWidget(self.delay_label)
        form_layout.addRow(QLabel("Playback Speed:"), fps_layout)
        # Invert Colors
        self.invert_checkbox.setChecked(False)
        self.invert_checkbox.setToolTip(
            "If checked, renders white pixels on a black background. Otherwise, black on white.")
        form_layout.addRow(self.invert_checkbox)
        # Looping
        self.loop_checkbox.setChecked(True)
        self.loop_checkbox.setToolTip(
            "If checked, the generated GIF will loop forever.")
        form_layout.addRow(self.loop_checkbox)
        main_layout.addLayout(form_layout)
        main_layout.addWidget(self.button_box)

    def _connect_signals(self):
        """Connects signals from the dialog widgets to the dialog's slots."""
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        self.fps_spinbox.valueChanged.connect(self._update_delay_label)

    def _update_delay_label(self, fps: int):
        """Updates the delay label based on the current FPS value."""
        if fps > 0:
            delay_ms = int(1000.0 / fps)
            self.delay_label.setText(f"({delay_ms} ms)")
        else:
            self.delay_label.setText("(--- ms)")

    def get_export_options(self) -> dict:
        """
        Returns the user-selected export options in a dictionary.
        """
        fps = self.fps_spinbox.value()
        delay_ms = int(1000.0 / fps) if fps > 0 else 1000
        return {
            'scale': self.scale_spinbox.value(),
            'invert': self.invert_checkbox.isChecked(),
            'delay': delay_ms,
            # Pillow: 0=infinite, 1=play once
            'loop': 0 if self.loop_checkbox.isChecked() else 1
        }
    @staticmethod
    def get_options(parent: QWidget, initial_fps: int) -> tuple[dict | None, bool]:
        """
        A static method to create, show, and get results from the dialog.
        """
        dialog = OLEDGifExportDialog(initial_fps, parent)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            return dialog.get_export_options(), True
        return None, False

if __name__ == '__main__':
    # A simple test to check the dialog's appearance and functionality
    app = QApplication(sys.argv)
    # Attempt to load the main application stylesheet for a consistent look
    try:
        import os
        style_file_path = os.path.join(
            os.getcwd(), "resources", "styles", "style.qss")
        if os.path.exists(style_file_path):
            with open(style_file_path, "r") as f_style:
                app.setStyleSheet(f_style.read())
    except Exception:
        pass
    print("Showing OLED GIF Export Dialog with initial FPS of 15...")
    options, ok = OLEDGifExportDialog.get_options(None, 15)
    if ok:
        print("\nUser clicked OK. Export options:")
        print(f"  - Scale:  {options['scale']}x")
        print(f"  - Invert: {options['invert']}")
        print(f"  - Delay:  {options['delay']} ms")
        print(
            f"  - Loop:   {'Infinite' if options['loop'] == 0 else 'Play Once'}")
    else:
        print("\nUser clicked Cancel.")
    sys.exit()
