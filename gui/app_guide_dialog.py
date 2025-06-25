# AKAI_Fire_PixelForge/gui/app_guide_dialog.py
import sys
from PyQt6.QtWidgets import (
    QApplication, QDialog, QVBoxLayout, QTextBrowser, QDialogButtonBox,
    QTabWidget, QWidget, QScrollArea, QGridLayout, QLabel, QFrame, QGroupBox
)
from PyQt6.QtCore import QUrl, Qt
from PyQt6.QtGui import QDesktopServices, QFont

# --- Main App Guide HTML Content ---
# This is the detailed user manual for the first tab.
APP_GUIDE_HTML_CONTENT = """
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<style>
    /* Style block remains large but is necessary for rich text formatting */
    body {
        background: #131313;
        color: #D0D0D0;
        font-family: 'Segoe UI', Arial, sans-serif;
        font-size: 11pt;
        line-height: 1.4;
    }
    .container {
        max-width: 900px;
        margin: 20px auto;
        padding: 20px 28px;
        background: #181818;
        border-radius: 8px;
        border: 1px solid #2a2a2a;
    }
    h1 {
        color: #4FC3F7; /* Blue accent */
        font-size: 2em;
        text-align: center;
        margin-bottom: 20px;
    }
    h2 {
        color: #FFD166; /* Gold/yellow accent */
        font-size: 1.4em;
        margin-top: 30px;
        margin-bottom: 12px;
        border-bottom: 1.5px solid #282828;
        padding-bottom: 4px;
    }
    h3 {
        color: #A259F7; /* Purple accent */
        font-size: 1.1em;
        font-weight: 600;
        margin-top: 20px;
        margin-bottom: 8px;
    }
    p, li {
        color: #D0D0D0;
    }
    ul {
        list-style-type: disc;
        padding-left: 25px;
    }
    code, .key-cap {
        background: #282828;
        color: #A259F7;
        border-radius: 4px;
        padding: 2px 6px;
        font-size: 0.95em;
        font-family: 'Consolas', 'Courier New', monospace;
        border: 1px solid #333;
    }
    a {
        color: #4FC3F7;
        text-decoration: none;
    }
    a:hover {
        text-decoration: underline;
    }
    .note {
        background: rgba(255, 209, 102, 0.1);
        border-left: 4px solid #FFD166;
        padding: 10px 15px;
        margin: 15px 0;
        border-radius: 4px;
    }
    .doom-title { color: #FF1744; }
</style>
</head>
<body>
<div class="container">
    <h1>🚀 Akai Fire PixelForge - App Guide</h1>
    <p>Welcome to <b>Akai Fire PixelForge</b>! This guide explains the features of the application. For a quick reference of all keyboard shortcuts and hardware button functions, please see the <b>🎛️ Controls & Hotkeys</b> tab.</p>
    <p class="note">Many features, including file operations (New, Save, Export), editing tools (Copy, Paste), and mode toggles, are also accessible via the standard top menu bar (<code>File</code>, <code>Edit</code>, <code>Tools</code>, etc.) for a familiar workflow.</p>

    <h2>🎨 Pad Painting & Animator Studio</h2>
    <p>The core of PixelForge is a complete studio for creating 4x16 pixel art and animations.</p>
    <h3>Primary/Secondary Colors</h3>
    <p>The Color Picker uses a <b>Primary/Secondary</b> color system. Left-click (or drag) on the main grid paints with the Primary Color. Right-click (or drag) paints with the Secondary Color. By default, the secondary color is black, acting as an eraser.</p>
    <h3>Animator Timeline</h3>
    <p>The timeline is your main workspace for building animations. You can select, multi-select (with <code>Ctrl</code> or <code>Shift</code>), and drag-and-drop frames to reorder them. Use the buttons or hotkeys for operations like adding, duplicating, and deleting frames.</p>

    <h2>🎵 Audio Visualizer</h2>
    <p>Unleash your music visually! The Audio Visualizer listens to your computer's sound output and transforms it into dynamic, colorful light shows on the pads.</p>
    <ul>
        <li><b>Audio Source:</b> Select the sound device you want to visualize (often labeled "Loopback" or "Stereo Mix").</li>
        <li><b>Enable/Disable:</b> Use the "Enable Visualizer" button or press the <span class="key-cap">NOTE</span> button on the hardware.</li>
        <li><b>Live Settings:</b> Click the <code>Setup...</code> button to open a dialog where you can tweak all settings in <b>real-time</b> while the visualizer is running.</li>
    </ul>
    <h3>Visualization Modes</h3>
    <ul>
        <li><b>Classic Spectrum Bars:</b> The iconic look of a graphic equalizer.</li>
        <li><b>Pulse Wave:</b> A smooth, sweeping bar of color that travels across the grid, reacting to loudness.</li>
        <li><b>Dual VU + Spectrum:</b> A powerful mode with classic VU meters on the sides and a mini-spectrum in the center.</li>
    </ul>

    <h2>💡 Screen Sampler (Ambient Mode)</h2>
    <p>Dynamically mirror colors from your screen onto the pads and record the output into new animations.</p>
    <ul>
        <li><b>Activation:</b> Toggle using the "Screen Sampling" button in the UI or the <span class="key-cap">PERFORM</span> / <span class="key-cap">BROWSER</span> buttons on the hardware.</li>
        <li><b>Configuration:</b> Click <code>Configure...</code> to open a dialog where you can select a monitor, drag to define a capture area, and adjust Brightness, Saturation, Contrast, and Hue.</li>
        <li><b>Record Output:</b> Click "Record" to capture the sampler's visual output directly into a new animation sequence in the Animator Studio.</li>
    </ul>
    <p class="note"><b>Power User Tip:</b> Websites like GIPHY are a goldmine for sampler content. Play an abstract color GIF, position the sampler region over it, and record the output to create amazing pad animations with ease!</p>

    <h2>⚙️ Advanced OLED Customization</h2>
    <ul>
        <li><b>Active Graphic System:</b> In the OLED Customizer, you can designate any of your creations (Text, Image, or Animation) to be the persistent default display on your Fire's OLED.</li>
        <li><b>Manual Play/Pause:</b> A clickable play/pause icon appears next to the UI's OLED mirror, allowing you to manually pause or resume your active animated graphic.</li>
        <li><b>Export as GIF:</b> You can export your active OLED animation as a GIF file via <code>File > Export Active OLED as GIF...</code>.</li>
    </ul>

    <h2 class="doom-title">👹 LazyDOOM - Retro FPS Game</h2>
    <p>A fully playable, DOOM-themed retro first-person shooter that runs entirely on the controller's OLED display, using the pads for input. Click the "Launch LazyDOOM" button and read the instructions carefully before playing!</p>

    <h2>🎛️ In-Depth Hardware Controls (Contextual Knobs)</h2>
    <p>The top row of physical knobs on the Akai Fire have special functions depending on the application's current state. The OLED will briefly show their function and value when a knob is turned.</p>
    <h3>Default / Animator Editing Mode</h3>
    <ul>
        <li><b>Knob 1 (Volume):</b> Adjusts Global Pad Brightness.</li>
        <li><b>Knobs 2-4:</b> Unassigned.</li>
    </ul>
    <h3>Screen Sampler Mode (Active)</h3>
    <ul>
        <li><b>Knob 1 (Volume):</b> Sampler Output Brightness</li>
        <li><b>Knob 2 (Pan):</b> Sampler Output Saturation</li>
        <li><b>Knob 3 (Filter):</b> Sampler Output Contrast</li>
        <li><b>Knob 4 (Resonance):</b> Sampler Output Hue Shift</li>
    </ul>
    <h3>Animator Playback Mode (Active)</h3>
    <ul>
        <li><b>Knob 4 (Resonance):</b> Adjusts active Animation Playback Speed (FPS).</li>
    </ul>
     <h3>Audio Visualizer Mode (Active)</h3>
    <ul>
        <li>Knob control is disabled. Use the "Setup..." dialog for all real-time adjustments.</li>
    </ul>
</div>
</body>
</html>
"""

# --- Main Dialog Class ---


class AppGuideDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(
            "🚀 Akai Fire PixelForge - App Guide & Hotkeys (v1.7.0)")
        self.setMinimumSize(900, 700)
        self.resize(1000, 850)

        # Main Layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)

        # Tab Widget
        self.tab_widget = QTabWidget()
        main_layout.addWidget(self.tab_widget)

        # --- Tab 1: App Guide (HTML) ---
        guide_widget = QWidget()
        guide_layout = QVBoxLayout(guide_widget)
        guide_layout.setContentsMargins(0, 0, 0, 0)
        self.text_browser = QTextBrowser()
        self.text_browser.setOpenExternalLinks(True)
        self.text_browser.setHtml(APP_GUIDE_HTML_CONTENT)
        self.text_browser.anchorClicked.connect(self.handle_link_clicked)
        guide_layout.addWidget(self.text_browser)
        self.tab_widget.addTab(guide_widget, "🚀 App Guide")

        # --- Tab 2: Controls & Hotkeys (Grid) ---
        self.controls_widget = self._create_controls_tab()
        self.tab_widget.addTab(self.controls_widget, "🎛️ Controls && Hotkeys")

        # OK Button
        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        self.button_box.accepted.connect(self.accept)
        main_layout.addWidget(self.button_box)

        self.setLayout(main_layout)
        self._apply_styling()

    def _create_controls_tab(self) -> QWidget:
        # Main container and scroll area for the controls tab
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setObjectName("ControlsScrollArea")

        container_widget = QWidget()
        main_controls_layout = QVBoxLayout(container_widget)
        main_controls_layout.setSpacing(20)
        main_controls_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # --- Keyboard Hotkeys Section ---
        kbd_group = QGroupBox("⌨️ Keyboard Hotkeys")
        kbd_layout = QGridLayout(kbd_group)
        kbd_layout.setColumnStretch(1, 1)  # Allow description to expand
        kbd_layout.setVerticalSpacing(8)
        kbd_layout.setHorizontalSpacing(15)

        hotkeys = [
            ("Ctrl + N", "New Animation Sequence"),
            ("Ctrl + O", "Load Animation Sequence"),
            ("Ctrl + Shift + S", "Save Sequence As..."),
            ("Spacebar", "Play / Pause Animation"),
            ("Ctrl + Z", "Undo last paint stroke or frame operation"),
            ("Ctrl + Y", "Redo last paint stroke or frame operation"),
            ("Ctrl + C", "Copy selected frame(s)"),
            ("Ctrl + X", "Cut selected frame(s)"),
            ("Ctrl + V", "Paste frame(s) from clipboard"),
            ("Ctrl + D", "Duplicate selected frame(s)"),
            ("Delete", "Delete selected frame(s)"),
            ("I", "Toggle Eyedropper tool for color picking")
        ]

        for i, (key, desc) in enumerate(hotkeys):
            self._add_control_row(kbd_layout, i, key, desc)

        main_controls_layout.addWidget(kbd_group)

        # --- Hardware Controls Section ---
        hw_group = QGroupBox("🔥 Akai Fire Hardware Controls")
        hw_layout = QGridLayout(hw_group)
        hw_layout.setColumnStretch(1, 1)
        hw_layout.setVerticalSpacing(8)
        hw_layout.setHorizontalSpacing(15)

        hw_buttons = [
            ("PERFORM / BROWSER", "Toggle Screen Sampler (Ambient Mode) ON/OFF."),
            ("DRUM", "Cycle through available monitors for Screen Sampler."),
            ("NOTE", "Toggle Audio Visualizer ON/OFF."),
            ("STEP", "Toggle the 'Enable Color FX' checkbox."),
            ("PLAY", "Play / Pause Animator."),
            ("STOP", "Stop Animator playback."),
            ("PATTERN UP", "Cycle to the NEXT Active OLED Graphic."),
            ("PATTERN DOWN", "Cycle to the PREVIOUS Active OLED Graphic."),
            ("GRID ▶", "Cycle Navigation Focus (e.g., Animator vs. Static Layouts)."),
            ("GRID ◀", "Cycle Navigation Focus (e.g., Animator vs. Static Layouts)."),
            ("SELECT (Turn)", "Scroll through items in the focused panel."),
            ("SELECT (Press)", "Load / Apply the currently highlighted item.")
        ]

        for i, (key, desc) in enumerate(hw_buttons):
            self._add_control_row(hw_layout, i, key, desc)

        main_controls_layout.addWidget(hw_group)
        scroll_area.setWidget(container_widget)
        return scroll_area

    def _add_control_row(self, layout, row, key_text, desc_text):
        """Helper to add a styled row to a grid layout."""
        key_label = QLabel(f"<span class='key-cap'>{key_text}</span>")
        desc_label = QLabel(desc_text)

        layout.addWidget(key_label, row, 0, Qt.AlignmentFlag.AlignRight)
        layout.addWidget(desc_label, row, 1)

    def _apply_styling(self):
        """Apply QSS styling to the dialog components."""
        self.setStyleSheet("""
            AppGuideDialog {
                background-color: #131313;
            }
            QTabWidget::pane {
                border: 1px solid #161616;
                background-color: #0f0f0f;
            }
            QTabBar::tab {
                background-color: #2D2D2D;
                color: #A0A0A0;
                border: 1px solid #2a2a2a;
                border-bottom: none;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
                min-width: 150px;
                padding: 8px 15px;
                font-size: 10pt;
                font-weight: bold;
            }
            QTabBar::tab:hover {
                background-color: #303030;
                color: #E0E0E0;
            }
            QTabBar::tab:selected {
                background-color: #181818; /* Match pane background */
                color: #39effc; /* Blue accent for selected tab */
                margin-bottom: -1px; /* Pull tab down to connect with pane */
            }
            QScrollArea#ControlsScrollArea {
                border: none;
                background-color: #181818;
            }
            QGroupBox {
                font-size: 12pt;
                font-weight: bold;
                color: #73ff66; 
                background-color: #1D1D1D;
                border: 1px solid #2a2a2a;
                border-radius: 6px;
                margin-top: 10px;
                padding: 20px 15px 15px 15px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 10px;
                left: 15px;
            }
            QLabel {
                font-size: 10pt;
                color: #D0D0D0;
                background-color: transparent;
            }
            .key-cap {
                background-color: #282828;
                color: #A259F7; /* Purple */
                border-radius: 4px;
                padding: 3px 8px;
                font-size: 10pt;
                font-weight: bold;
                font-family: 'Consolas', 'Courier New', monospace;
                border: 1px solid #272727;
            }
        """)

    def handle_link_clicked(self, url: QUrl):
        """Ensure external links are opened by the system's default browser."""
        if url.scheme() in ["http", "https"]:
            QDesktopServices.openUrl(url)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    # The main app's stylesheet will handle the dialog's base styles (like buttons)
    # when run from within the main application. This is for standalone testing.
    try:
        import os
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root_dir = os.path.dirname(current_dir)
        style_file_path = os.path.join(project_root_dir, "resources", "styles", "style.qss")
        if os.path.exists(style_file_path):
            with open(style_file_path, "r") as f_style:
                app.setStyleSheet(f_style.read())
    except Exception:
        pass # It's okay if it fails in standalone test
        
    dialog = AppGuideDialog()
    dialog.show()
    sys.exit(app.exec())