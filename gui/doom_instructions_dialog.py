### START OF FILE doom_instructions_dialog.py ###
# AKAI_Fire_RGB_Controller/gui/doom_instructions_dialog.py
import os
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QLabel, QPushButton,
                             QDialogButtonBox, QHBoxLayout, QFrame, QComboBox,
                             QScrollArea, QWidget)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap

# --- Project-specific Imports for get_resource_path ---
try:
    from .main_window import get_resource_path
except ImportError:
    try:
        from utils import get_resource_path
    except ImportError:
        print("DoomInstructionsDialog WARNING: Could not import get_resource_path. Image paths may fail.")

        def get_resource_path(relative_path):
            return os.path.join(os.path.abspath("."), relative_path.replace("/", os.path.sep))

# Constants for difficulty levels
DIFFICULTY_NORMAL_DIALOG = "Normal"
DIFFICULTY_HARD_DIALOG = "Hard"
DIFFICULTY_VERY_HARD_DIALOG = "Very Hard"

# Color Constants for Styling
COLOR_RED = "#FF4136"
COLOR_ORANGE = "#FF851B"
COLOR_WHITE = "#DDDDDD"
COLOR_GRAY = "#AAAAAA"


class DoomInstructionsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("👹 LazyDOOM - Instructions & Difficulty")
        self.setMinimumWidth(520)
        # Set a maximum height to prevent it from exceeding the main window's height
        if parent:
            self.setMaximumHeight(int(parent.height() * 0.95))
        else:
            self.setMaximumHeight(850)

        self.setModal(True)
        self.resize(520, 880) # <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<< WIDTH, HEIGHT
        self.selected_difficulty = DIFFICULTY_NORMAL_DIALOG

        # --- UI Element Declarations ---
        self.difficulty_combo: QComboBox | None = None
        self.button_box: QDialogButtonBox | None = None

        self._init_ui()

    def _init_ui(self):
        # --- Main Dialog Layout (will contain only the scroll area) ---
        dialog_layout = QVBoxLayout(self)
        dialog_layout.setContentsMargins(0, 0, 10, 10)

        # --- Scroll Area Setup ---
        scroll_area = QScrollArea(self)
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setStyleSheet("QScrollArea { border: none; }")

        # --- Content Container Widget (the "canvas" that will scroll) ---
        content_widget = QWidget()
        scroll_area.setWidget(content_widget)

        # --- Content Layout (all our widgets go in here) ---
        content_layout = QVBoxLayout(content_widget)
        # Add padding inside the scroll area
        content_layout.setContentsMargins(15, 15, 15, 15)
        content_layout.setSpacing(15)

# --- 1. Title ---
        # We now include all styling directly in the HTML string.
        # This will override the global QSS font-size.
        title_html = f"""
            <div style='
                font-size: 20pt;
                font-weight: bold;
                color: {COLOR_RED};
            '>
                Welcome to LazyDOOM!
            </div>
        """
        title_label = QLabel(title_html)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        content_layout.addWidget(title_label)

        # 2. OLED Preview Image
        oled_preview_label = QLabel()
        oled_preview_label.setObjectName("DoomImagePreview")
        try:
            oled_icon_path = get_resource_path(
                os.path.join("resources", "icons", "doomoled.png"))
            if os.path.exists(oled_icon_path):
                pixmap = QPixmap(oled_icon_path)
                scaled_pixmap = pixmap.scaledToHeight(
                    64, Qt.TransformationMode.SmoothTransformation)
                oled_preview_label.setPixmap(scaled_pixmap)
                oled_preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                content_layout.addWidget(oled_preview_label)
        except Exception as e:
            print(f"DoomDialog ERROR: Could not load doomoled.png: {e}")

        # 3. Difficulty Dropdown
        difficulty_layout = QHBoxLayout()
        difficulty_label = QLabel(f"<b>Select Difficulty:</b>")
        difficulty_layout.addWidget(difficulty_label)
        self.difficulty_combo = QComboBox()
        self.difficulty_combo.addItems(
            [DIFFICULTY_NORMAL_DIALOG, DIFFICULTY_HARD_DIALOG, DIFFICULTY_VERY_HARD_DIALOG])
        self.difficulty_combo.setCurrentText(DIFFICULTY_NORMAL_DIALOG)
        self.difficulty_combo.currentTextChanged.connect(
            self._on_difficulty_changed)
        difficulty_layout.addWidget(self.difficulty_combo)
        difficulty_layout.addStretch(1)
        content_layout.addLayout(difficulty_layout)

        # 4. Text Instructions with Difficulty Descriptions
        instructions_text = f"""
        <p style="color:{COLOR_WHITE};">
            <b style="color:{COLOR_ORANGE};">Objective:</b> Kill all the Imps to win! Watch your HP.
        </p>
        <p style="color:{COLOR_GRAY}; line-height: 150%;">
            <b style="color:{COLOR_WHITE};"><u>Difficulty Levels:</u></b><br>
            <b style="color:{COLOR_ORANGE};">Normal:</b> A balanced hunt. You have time to think, but not too much.<br>
            <b style="color:{COLOR_ORANGE};">Hard:</b> The onslaught begins. Imps are more numerous and shoot faster.<br>
            <b style="color:{COLOR_ORANGE};">Very Hard:</b> Welcome to Hell. Overwhelming numbers and relentless attacks.
        </p>
        <p>
            <b style="color:{COLOR_RED};"><u>Akai Fire Pad Controls:</u></b><br/>
            <ul style="color:{COLOR_WHITE};">
                <li><b style="color:{COLOR_ORANGE};">Top-Middle Pad (Left):</b> Move Forward</li>
                <li><b style="color:{COLOR_ORANGE};">Bottom-Middle Pad (Left):</b> Move Backward</li>
                <li><b style="color:{COLOR_ORANGE};">Left/Right Pads (Middle Row):</b> Strafe Left/Right</li>
                <li><b style="color:{COLOR_ORANGE};">Top-Left/Right Pads (Main):</b> Turn Left/Right</li>
                <li><b style="color:{COLOR_ORANGE};">Run Pad (Right):</b> Hold to Run</li>
                <li><b style="color:{COLOR_ORANGE};">Shoot Pad (Right):</b> Shoot / Restart Game</li>
            </ul>
            <i style="color:{COLOR_GRAY};">Note: Bottom 4 pads show your <b style="color:{COLOR_RED};">HP Bar</b>.</i>
            <br/><br/>
            <b style="color:{COLOR_RED};"><u>Keyboard Controls:</u></b>
            <ul style="color:{COLOR_WHITE};">
                <li><b style="color:{COLOR_ORANGE};">W, A, S, D:</b> Forward, Strafe L/R, Backward</li>
                <li><b style="color:{COLOR_ORANGE};">Q, E or Left/Right Arrows:</b> Turn Left/Right</li>
                <li><b style="color:{COLOR_ORANGE};">Shift:</b> Hold to Run</li>
                <li><b style="color:{COLOR_ORANGE};">F:</b> Shoot</li>
            </ul>
        </p>
        """
        instructions_label = QLabel(instructions_text)
        instructions_label.setWordWrap(True)
        instructions_label.setTextFormat(Qt.TextFormat.RichText)
        instructions_label.setOpenExternalLinks(False)
        content_layout.addWidget(instructions_label)

        # 5. Controls Image
        controls_image_label = QLabel()
        controls_image_label.setObjectName("DoomImagePreview")
        try:
            controls_icon_path = get_resource_path(
                os.path.join("resources", "icons", "doomcontrol.png"))
            if os.path.exists(controls_icon_path):
                pixmap = QPixmap(controls_icon_path)
                scaled_pixmap = pixmap.scaledToWidth(
                    450, Qt.TransformationMode.SmoothTransformation)
                controls_image_label.setPixmap(scaled_pixmap)
                controls_image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                content_layout.addWidget(controls_image_label)
        except Exception as e:
            print(f"DoomDialog ERROR: Could not load doomcontrol.png: {e}")

        # --- Final widgets that should NOT scroll ---
        # Separator Line
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)

        # Button Box
        self.button_box = QDialogButtonBox()
        start_button = self.button_box.addButton(
            "Start Game!", QDialogButtonBox.ButtonRole.AcceptRole)
        cancel_button = self.button_box.addButton(
            "Back to PixelForge", QDialogButtonBox.ButtonRole.RejectRole)
        start_button.clicked.connect(self.accept)
        cancel_button.clicked.connect(self.reject)

        # Add the scroll area and the non-scrolling widgets to the main dialog layout
        dialog_layout.addWidget(scroll_area)  # The scrollable content
        dialog_layout.addWidget(line)        # The separator
        dialog_layout.addWidget(self.button_box)  # The buttons

    def _on_difficulty_changed(self, text: str):
        self.selected_difficulty = text

    def get_selected_difficulty(self) -> str:
        return self.selected_difficulty
