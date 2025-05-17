### START OF FILE gui/set_max_frames_dialog.py ###
# AKAI_Fire_RGB_Controller/gui/set_max_frames_dialog.py
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QSlider, QPushButton,
    QDialogButtonBox, QSpinBox, QWidget
)
from PyQt6.QtCore import Qt, pyqtSignal

class SetMaxFramesDialog(QDialog):
    # Signal to emit the new max frames value when accepted
    max_frames_value_changed = pyqtSignal(int)

    MIN_FRAMES = 1
    MAX_FRAMES = 500 # As per your requirement
    DEFAULT_FRAMES = 200 # As per previous handover

    def __init__(self, current_max_frames: int = DEFAULT_FRAMES, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Set Max Recording Frames")
        self.setMinimumWidth(300)
        self.setModal(True) # Make it a modal dialog

        self._initial_value = max(self.MIN_FRAMES, min(current_max_frames, self.MAX_FRAMES))

        # Main layout
        layout = QVBoxLayout(self)

        # Slider and SpinBox layout
        controls_layout = QHBoxLayout()

        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setRange(self.MIN_FRAMES, self.MAX_FRAMES)
        self.slider.setValue(self._initial_value)
        self.slider.setSingleStep(1)
        self.slider.setPageStep(10)
        self.slider.setTickInterval((self.MAX_FRAMES - self.MIN_FRAMES) // 20 if self.MAX_FRAMES > self.MIN_FRAMES + 19 else 1)
        self.slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        controls_layout.addWidget(self.slider, 1) # Slider takes more space

        self.spinbox = QSpinBox()
        self.spinbox.setRange(self.MIN_FRAMES, self.MAX_FRAMES)
        self.spinbox.setValue(self._initial_value)
        self.spinbox.setButtonSymbols(QSpinBox.ButtonSymbols.UpDownArrows)
        controls_layout.addWidget(self.spinbox)

        layout.addLayout(controls_layout)

        # Value display label
        self.value_label = QLabel(f"Current Max: {self._initial_value} frames")
        self.value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.value_label)

        # Dialog buttons (OK, Cancel)
        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        layout.addWidget(self.button_box)

        # Connect signals
        self.slider.valueChanged.connect(self._on_slider_value_changed)
        self.spinbox.valueChanged.connect(self._on_spinbox_value_changed)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)

        self.resize(350, 150) # A reasonable default size

    def _on_slider_value_changed(self, value: int):
        self.spinbox.blockSignals(True)
        self.spinbox.setValue(value)
        self.spinbox.blockSignals(False)
        self.value_label.setText(f"Current Max: {value} frames")

    def _on_spinbox_value_changed(self, value: int):
        self.slider.blockSignals(True)
        self.slider.setValue(value)
        self.slider.blockSignals(False)
        self.value_label.setText(f"Current Max: {value} frames")

    def get_selected_value(self) -> int:
        return self.slider.value() # Or self.spinbox.value()

    def accept(self):
        """Overrides QDialog.accept() to emit signal before closing."""
        self.max_frames_value_changed.emit(self.get_selected_value())
        super().accept()

    @staticmethod
    def get_max_frames(parent_widget, current_value: int) -> tuple[int | None, bool]:
        """
        Static method to conveniently show the dialog and get the value.
        Returns: (new_value, accepted_bool)
                 new_value is None if dialog was cancelled.
        """
        dialog = SetMaxFramesDialog(current_max_frames=current_value, parent=parent_widget)
        accepted = dialog.exec() # exec() returns QDialog.DialogCode.Accepted or QDialog.DialogCode.Rejected
        if accepted == QDialog.DialogCode.Accepted:
            return dialog.get_selected_value(), True
        return None, False

if __name__ == '__main__':
    import sys
    from PyQt6.QtWidgets import QApplication, QMainWindow, QPushButton

    app = QApplication(sys.argv)

    # Create a dummy main window to test the dialog
    test_main_window = QMainWindow()
    test_main_window.setWindowTitle("Dialog Test")
    central_widget = QWidget()
    test_main_window.setCentralWidget(central_widget)
    layout = QVBoxLayout(central_widget)

    current_max_frames_for_test = 150
    label = QLabel(f"Main Window - Current Max: {current_max_frames_for_test}")
    layout.addWidget(label)

    def open_dialog():
        global current_max_frames_for_test # Allow modification of the global variable
        new_val, ok = SetMaxFramesDialog.get_max_frames(test_main_window, current_max_frames_for_test)
        if ok and new_val is not None:
            print(f"Dialog accepted. New max frames: {new_val}")
            current_max_frames_for_test = new_val
            label.setText(f"Main Window - Current Max: {current_max_frames_for_test}")
        else:
            print("Dialog cancelled or no value.")

    button = QPushButton("Open Set Max Frames Dialog")
    button.clicked.connect(open_dialog)
    layout.addWidget(button)

    test_main_window.setGeometry(300, 300, 400, 200)
    test_main_window.show()

    sys.exit(app.exec())
### END OF FILE gui/set_max_frames_dialog.py ###