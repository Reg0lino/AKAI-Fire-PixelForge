from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QLabel, QPushButton,
                            QDialogButtonBox, QHBoxLayout, QFrame, QComboBox)
from PyQt6.QtCore import Qt

# Constants for difficulty levels
DIFFICULTY_NORMAL_DIALOG = "Normal"
DIFFICULTY_HARD_DIALOG = "Hard"
DIFFICULTY_VERY_HARD_DIALOG = "Very Hard"

class DoomInstructionsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(
            "👹 LazyDOOM - Instructions & Difficulty")  # Updated title
        self.setMinimumWidth(480)  # Slightly wider for difficulty
        self.setModal(True)
        self.selected_difficulty = DIFFICULTY_NORMAL_DIALOG  # Default
        main_layout = QVBoxLayout(self)
        title_label = QLabel("Welcome to LazyDOOM!")
        title_font = title_label.font()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(title_label)
        difficulty_layout = QHBoxLayout()
        difficulty_layout.addWidget(QLabel("<b>Select Difficulty:</b>"))
        self.difficulty_combo = QComboBox()
        self.difficulty_combo.addItems(
            [DIFFICULTY_NORMAL_DIALOG, DIFFICULTY_HARD_DIALOG, DIFFICULTY_VERY_HARD_DIALOG])
        self.difficulty_combo.setCurrentText(
            DIFFICULTY_NORMAL_DIALOG)  # Default selection
        self.difficulty_combo.currentTextChanged.connect(
            self._on_difficulty_changed)
        difficulty_layout.addWidget(self.difficulty_combo)
        difficulty_layout.addStretch(1)
        main_layout.addLayout(difficulty_layout)
        instructions_text = """
        <p><b>Objective:</b> Kill all the Imps to win! Watch your HP.</p>
        <p><b><u>Akai Fire Pad Controls:</u></b></p>
        <p>
            (Assumes a D-Pad like layout on the left, actions on the right)
            <ul>
                <li><b>Top-Middle Pad (Left Group):</b> Move Forward</li>
                <li><b>Bottom-Middle Pad (Left Group):</b> Move Backward</li>
                <li><b>Left/Right Pads (Middle Row, Left Group):</b> Strafe Left/Right</li>
                <li><b>Top-Left/Right Pads (Left Group):</b> Turn Left/Right (Main)</li>
                <li><b>Top-Left/Right Pads (Right Group):</b> Turn Left/Right (Alt)</li>
                <li><b>Run Pad (Right Group):</b> Hold to Run</li>
                <li><b>Shoot Pad (Right Group):</b> Press to Shoot / Restart after Game Over</li>
            </ul>
            <i>Note: The exact physical pads depend on your setup in the script.</i>
            <br/>
            <b>HP Bar:</b> Bottom 4 pads on the Akai Fire show your health (Red = Health).
        </p>
        <p><b><u>Keyboard Controls (Alternative):</u></b></p>
        <ul>
            <li><b>W, A, S, D:</b> Forward, Strafe Left, Backward, Strafe Right</li>
            <li><b>Q, E:</b> Turn Left/Right (Main)</li>
            <li><b>Left/Right Arrow Keys:</b> Turn Left/Right (Alt)</li>
            <li><b>Shift:</b> Hold to Run</li>
            <li><b>F:</b> Shoot</li>
        </ul>
        """
        instructions_label = QLabel(instructions_text)
        instructions_label.setWordWrap(True)
        instructions_label.setTextFormat(Qt.TextFormat.RichText)
        instructions_label.setOpenExternalLinks(False)
        main_layout.addWidget(instructions_label)
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        main_layout.addWidget(line)
        self.button_box = QDialogButtonBox()
        self.start_button = self.button_box.addButton(
            "Start Game!", QDialogButtonBox.ButtonRole.AcceptRole)
        self.cancel_button = self.button_box.addButton(
            "Back to PixelForge", QDialogButtonBox.ButtonRole.RejectRole)
        main_layout.addWidget(self.button_box)
        self.start_button.clicked.connect(self.accept)
        self.cancel_button.clicked.connect(self.reject)
        self.setLayout(main_layout)

    def _on_difficulty_changed(self, text: str):
        self.selected_difficulty = text
        print(
            f"DoomInstructionsDialog: Difficulty selected - {self.selected_difficulty}")

    def get_selected_difficulty(self) -> str:
        return self.selected_difficulty