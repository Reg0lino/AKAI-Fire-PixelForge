# AKAI_Fire_RGB_Controller/gui/gif_export_dialog.py
import sys
from PyQt6.QtWidgets import (
    QApplication, QDialog, QVBoxLayout, QFormLayout, QLabel,
    QSpinBox, QCheckBox, QDialogButtonBox, QWidget
)
from PyQt6.QtCore import Qt


class GifExportDialog(QDialog):
    """
    A dialog for gathering user options before exporting a pad animation to GIF.
    """

    def __init__(self, initial_frame_delay_ms: int, parent: QWidget | None = None):
        super().__init__(parent)

        self.setWindowTitle("Export Pad Animation to GIF")
        self.setWindowFlags(self.windowFlags() & ~
                            Qt.WindowType.WindowContextHelpButtonHint)
        self.setMinimumWidth(350)

        # --- UI Widget Declarations ---
        self.pixel_size_spinbox = QSpinBox()
        self.spacing_spinbox = QSpinBox()
        self.delay_spinbox = QSpinBox()
        self.loop_checkbox = QCheckBox("Loop Animation Infinitely")
        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)

        self._init_ui(initial_frame_delay_ms)
        self._connect_signals()

    def _init_ui(self, initial_frame_delay_ms: int):
        """Initializes and lays out the UI widgets."""
        main_layout = QVBoxLayout(self)
        form_layout = QFormLayout()
        form_layout.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapAllRows)
        form_layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        # Pixel Size
        self.pixel_size_spinbox.setRange(5, 100)
        self.pixel_size_spinbox.setValue(20)
        self.pixel_size_spinbox.setSuffix(" px")
        self.pixel_size_spinbox.setToolTip(
            "The width and height of each individual pad pixel in the final GIF.")
        form_layout.addRow(QLabel("Pixel Size:"), self.pixel_size_spinbox)

        # Spacing
        self.spacing_spinbox.setRange(0, 20)
        self.spacing_spinbox.setValue(2)
        self.spacing_spinbox.setSuffix(" px")
        self.spacing_spinbox.setToolTip(
            "The size of the gap between each pad pixel.")
        form_layout.addRow(QLabel("Pixel Spacing:"), self.spacing_spinbox)

        # Frame Delay
        self.delay_spinbox.setRange(10, 5000)  # 100 FPS to 0.2 FPS
        self.delay_spinbox.setValue(initial_frame_delay_ms)
        self.delay_spinbox.setSuffix(" ms")
        self.delay_spinbox.setToolTip(
            "The time each frame is displayed in the GIF (in milliseconds).")
        form_layout.addRow(QLabel("Frame Delay:"), self.delay_spinbox)

        # Looping
        self.loop_checkbox.setChecked(True)
        self.loop_checkbox.setToolTip(
            "If checked, the generated GIF will loop forever.")
        form_layout.addRow(self.loop_checkbox)

        main_layout.addLayout(form_layout)
        main_layout.addWidget(self.button_box)

    def _connect_signals(self):
        """Connects signals from the dialog buttons to the dialog's slots."""
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)

    def get_export_options(self) -> dict:
        """
        Returns the user-selected export options in a dictionary.
        
        Returns:
            A dictionary containing keys: 'pixel_size', 'spacing', 'delay', 'loop'.
        """
        return {
            'pixel_size': self.pixel_size_spinbox.value(),
            'spacing': self.spacing_spinbox.value(),
            'delay': self.delay_spinbox.value(),
            # Pillow: 0=infinite, 1=play once
            'loop': 0 if self.loop_checkbox.isChecked() else 1
        }

    @staticmethod
    def get_options(parent: QWidget, initial_delay: int) -> tuple[dict | None, bool]:
        """
        A static method to create, show, and get results from the dialog.
        
        Args:
            parent: The parent widget for the dialog.
            initial_delay: The current animation frame delay in ms to pre-fill the form.
            
        Returns:
            A tuple containing (options_dict, ok_pressed).
            options_dict is None if the user cancelled.
            ok_pressed is True if the user clicked OK, False otherwise.
        """
        dialog = GifExportDialog(initial_delay, parent)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            return dialog.get_export_options(), True
        return None, False


if __name__ == '__main__':
    # A simple test to check the dialog's appearance and functionality
    app = QApplication(sys.argv)

    # --- Attempt to load the main application stylesheet for a consistent look ---
    try:
        import os
        # This path assumes the test is run from the project root
        style_file_path = os.path.join(
            os.getcwd(), "resources", "styles", "style.qss")
        if os.path.exists(style_file_path):
            with open(style_file_path, "r") as f_style:
                app.setStyleSheet(f_style.read())
                print("Test: Loaded style.qss for preview.")
    except Exception as e:
        print(
            f"Test: Could not load stylesheet. Using default style. Error: {e}")

    print("Showing GIF Export Dialog with initial delay of 50ms (20 FPS)...")

    options, ok = GifExportDialog.get_options(None, 50)

    if ok:
        print("\nUser clicked OK. Export options:")
        print(f"  - Pixel Size: {options['pixel_size']}")
        print(f"  - Spacing:    {options['spacing']}")
        print(f"  - Delay:      {options['delay']} ms")
        print(
            f"  - Loop:       {'Infinite' if options['loop'] == 0 else 'Play Once'}")
    else:
        print("\nUser clicked Cancel.")

    sys.exit()
