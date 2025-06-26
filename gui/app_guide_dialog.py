# AKAI_Fire_PixelForge/gui/app_guide_dialog.py
import sys
from PyQt6.QtWidgets import (
    QApplication, QDialog, QVBoxLayout, QTextBrowser, QDialogButtonBox,
    QTabWidget, QWidget, QScrollArea, QGridLayout, QLabel, QFrame, QGroupBox
)
from PyQt6.QtCore import QUrl, Qt, QSize
from PyQt6.QtGui import QDesktopServices, QFont, QFontDatabase, QMovie

# --- Main App Guide HTML Content ---
# The <img> tag for the title has been REMOVED from the HTML.
# It will be replaced by a live QMovie widget.
APP_GUIDE_HTML_CONTENT = """
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<style>
    body {
        background: #0A0A10;
        color: #E2E8F0;
        font-family: 'Inter', 'Segoe UI', Arial, sans-serif;
        font-size: 11pt;
        line-height: 1.45;
    }
    .container {
        max-width: 900px;
        margin: 10px auto;
        padding: 0 28px 20px 28px; /* Removed top padding */
        background: #111118;
        border-radius: 8px;
    }
    h2 {
        color: #ec4899; 
        font-family: 'Press Start 2P', 'Courier New', monospace;
        font-size: 1.5em;
        text-shadow: 1px 1px #000, 0 0 8px #ec4899;
        margin-top: 35px;
        margin-bottom: 15px;
        border-bottom: 1.5px solid #111118;
        padding-bottom: 6px;
    }
    h3 {
        color: #a78bfa; 
        font-size: 1.2em;
        font-weight: 600;
        margin-top: 25px;
        margin-bottom: 10px;
    }
    p, li {
        color: #cbd5e1;
    }
    ul {
        list-style-type: '⯈ ';
        padding-left: 20px;
    }
    li {
        padding-left: 10px;
        margin-bottom: 5px;
    }
    code, .key-cap {
        background: #111118;
        color: #a78bfa;
        border-radius: 4px;
        padding: 3px 7px;
        font-size: 0.95em;
        font-family: 'Consolas', 'Courier New', monospace;
        border: 1px solid #111118;
    }
    a {
        color: #6366f1;
        text-decoration: none;
        font-weight: 600;
    }
    a:hover {
        text-decoration: underline;
    }
    .note {
        background: rgba(236, 72, 154, 0.479);
        border-left: 4px solid #ec4899;
        padding: 12px 18px;
        margin: 20px 0;
        border-radius: 4px;
    }
    .doom-title { color: #FF1744; }
</style>
</head>
<body>
<div class="container">
    <!-- The title image is now handled by a QMovie widget in the application code -->
    <p>Welcome to <b>Akai Fire PixelForge</b>! This guide explains the features of the application. For a quick reference of all keyboard shortcuts and hardware button functions, please see the <b>🎛️ Controls & Hotkeys</b> tab.</p>
    <p class="note">Many features, including file operations (New, Save, Export), editing tools (Copy, Paste), and mode toggles, are also accessible via the standard top menu bar for a familiar workflow.</p>

    <h2>🎨 Animator Studio</h2>
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

    <h2>🖥️ Screen Sampler</h2>
    <p>Dynamically mirror colors from your screen onto the pads and record the output into new animations.</p>
    <ul>
        <li><b>Activation:</b> Toggle using the "Screen Sampling" button in the UI or the <span class="key-cap">PERFORM</span> button on the hardware.</li>
        <li><b>Configuration:</b> Click <code>Configure...</code> to open a dialog where you can select a monitor, drag to define a capture area, and adjust color processing.</li>
        <li><b>Record Output:</b> Click "Record" to capture the sampler's visual output directly into a new animation sequence in the Animator Studio.</li>
    </ul>
    <p class="note"><b>Power User Tip:</b> Websites like <a href="https://giphy.com" target="_blank">GIPHY</a> are a goldmine for sampler content. Play an abstract color GIF, position the sampler region over it, and record the output to create amazing pad animations with ease!</p>

    <h2>⚙️ Advanced OLED Customization</h2>
    <ul>
        <li><b>OLED Customizer:</b> Click the <span class="key-cap">BROWSER</span> button on the hardware (or the OLED mirror in the UI) to open the Customizer. Here you can create, edit, and manage a library of Text items, Image sprites, and dithered GIF animations.</li>
        <li><b>Active Graphic:</b> In the Customizer, you can designate any creation to be the persistent default display on your Fire's OLED screen.</li>
        <li><b>Live Controls:</b> Use <span class="key-cap">PATTERN UP</span> / <span class="key-cap">DOWN</span> to cycle the Active Graphic. Click the Play/Pause icon next to the UI mirror to freeze/unfreeze animations.</li>
    </ul>

    <h2 class="doom-title">👹 LazyDOOM</h2>
    <p>A fully playable, DOOM-themed retro first-person shooter that runs entirely on the controller's OLED display, using the pads for input. Click the "Launch LazyDOOM" button and read the instructions carefully before playing!</p>

    <h2>🎛️ In-Depth Hardware Controls</h2>
    <p>The top row of physical knobs on the Akai Fire have special functions depending on the application's current state. The OLED will briefly show their function and value when a knob is turned.</p>
    <h3>FX Panel / Default Mode</h3>
    <p>This is the default mode when no other master mode (Sampler, Animator Playback) is active. The knobs directly control the sliders in the <b>Color Grading / FX</b> panel.</p>
    <ul>
        <li><b>Knob 1 (Volume):</b> Controls the <b>Brightness</b> slider.</li>
        <li><b>Knob 2 (Pan):</b> Controls the <b>Saturation</b> slider.</li>
        <li><b>Knob 3 (Filter):</b> Controls the <b>Contrast</b> slider.</li>
        <li><b>Knob 4 (Resonance):</b> Controls the <b>Hue Shift</b> slider.</li>
    </ul>
    <h3>Screen Sampler Mode (Active)</h3>
    <p>When the Screen Sampler is running, the knobs control its live color processing engine.</p>
    <ul>
        <li><b>Knob 1:</b> Sampler Output Brightness</li>
        <li><b>Knob 2:</b> Sampler Output Saturation</li>
        <li><b>Knob 3:</b> Sampler Output Contrast</li>
        <li><b>Knob 4:</b> Sampler Output Hue Shift</li>
    </ul>
    <h3>Animator Playback Mode (Active)</h3>
    <ul>
        <li><b>Knob 5 (Select):</b> Adjusts active Animation Playback Speed (FPS).</li>
    </ul>
</div>
</body>
</html>
"""

# --- Main Dialog Class ---

class AppGuideDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("🚀 Akai Fire PixelForge - App Guide & Hotkeys (v1.7.0)")
        self.setMinimumSize(900, 700)
        self.resize(1000, 850)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)

        self.tab_widget = QTabWidget()
        main_layout.addWidget(self.tab_widget)

        # --- Tab 1: App Guide (with live QMovie animation) ---
        guide_widget = self._create_guide_tab()
        self.tab_widget.addTab(guide_widget, "🚀 App Guide")

        # --- Tab 2: Controls & Hotkeys (Grid) ---
        self.controls_widget = self._create_controls_tab()
        self.tab_widget.addTab(self.controls_widget, "🎛️ Controls & Hotkeys")

        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        self.button_box.accepted.connect(self.accept)
        main_layout.addWidget(self.button_box)
        self.setLayout(main_layout)
        self._apply_styling()

    def _create_guide_tab(self) -> QWidget:
        # This widget will hold the new layout for the first tab
        guide_container = QWidget()
        guide_layout = QVBoxLayout(guide_container)
        guide_layout.setContentsMargins(0, 0, 0, 0)
        guide_layout.setSpacing(10)

        # 1. Create the QLabel for the animation
        self.title_animation_label = QLabel()
        self.title_animation_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # 2. Create the QMovie object, loading the GIF from the resource file
        # The ":/" prefix tells Qt to look in the compiled resources.
        # We store the movie as an instance attribute to prevent it from being garbage-collected.
        self.title_movie = QMovie(":/images/title_animation.gif")
        
        # Optional: Set a scaled size to ensure it's not too large
        self.title_movie.setScaledSize(QSize(600, 150))
        
        # 3. Set the movie on the label and start it
        self.title_animation_label.setMovie(self.title_movie)
        self.title_movie.start()
        
        # 4. Create the QTextBrowser for the text content
        self.text_browser = QTextBrowser()
        self.text_browser.setOpenExternalLinks(True)
        self.text_browser.setHtml(APP_GUIDE_HTML_CONTENT)
        self.text_browser.anchorClicked.connect(self.handle_link_clicked)
        # Set a transparent background for the text browser
        self.text_browser.setStyleSheet("QTextBrowser { background-color: transparent; border: none; }")

        # 5. Add the animation label and the text browser to the layout
        guide_layout.addWidget(self.title_animation_label)
        guide_layout.addWidget(self.text_browser)
        
        return guide_container

    def _create_controls_tab(self) -> QWidget:
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setObjectName("ControlsScrollArea")
        container_widget = QWidget()
        main_controls_layout = QVBoxLayout(container_widget)
        main_controls_layout.setSpacing(20)
        main_controls_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        top_strip_group = QGroupBox("🎛️ Top Strip Hardware Controls")
        top_strip_layout = QGridLayout(top_strip_group)
        top_strip_layout.setColumnStretch(1, 1)
        top_strip_layout.setVerticalSpacing(8)
        top_strip_layout.setHorizontalSpacing(15)
        top_strip_buttons = [
            ("BROWSER", "Open the OLED Customizer dialog."),
            ("PATTERN UP", "Cycle to the NEXT Active OLED Graphic."),
            ("PATTERN DOWN", "Cycle to the PREVIOUS Active OLED Graphic."),
            ("GRID ▶ / ◀", "Cycle Navigation Focus (e.g., Animator vs. Static Layouts)."),
            ("SELECT (Turn)", "Scroll through items in the focused panel (e.g., animations, layouts)."),
            ("SELECT (Press)", "Load / Apply the currently highlighted item."),
        ]
        for i, (key, desc) in enumerate(top_strip_buttons):
            self._add_control_row(top_strip_layout, i, key, desc)
        main_controls_layout.addWidget(top_strip_group)

        hw_group = QGroupBox("🔥 Main Function Hardware Controls")
        hw_layout = QGridLayout(hw_group)
        hw_layout.setColumnStretch(1, 1)
        hw_layout.setVerticalSpacing(8)
        hw_layout.setHorizontalSpacing(15)
        hw_buttons = [
            ("PERFORM", "Toggle Screen Sampler (Ambient Mode) ON/OFF."),
            ("DRUM", "While Sampler is active, cycle through available monitors."),
            ("NOTE", "Toggle Audio Visualizer ON/OFF."),
            ("STEP", "Toggle the 'Enable Color FX' checkbox."),
            ("PLAY", "Play / Pause Animator."),
            ("STOP", "Stop Animator playback."),
        ]
        for i, (key, desc) in enumerate(hw_buttons):
            self._add_control_row(hw_layout, i, key, desc)
        main_controls_layout.addWidget(hw_group)

        kbd_group = QGroupBox("⌨️ Keyboard Hotkeys")
        kbd_layout = QGridLayout(kbd_group)
        kbd_layout.setColumnStretch(1, 1)
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
        
        scroll_area.setWidget(container_widget)
        return scroll_area

    def _add_control_row(self, layout, row, key_text, desc_text):
        key_label = QLabel(f"<span class='key-cap'>{key_text}</span>")
        desc_label = QLabel(desc_text)
        layout.addWidget(key_label, row, 0, Qt.AlignmentFlag.AlignRight)
        layout.addWidget(desc_label, row, 1)

    def _apply_styling(self):
        # We try to load fonts here to apply them to the QSS.
        # This is safe because if it fails, Qt uses a fallback.
        try:
            # We don't need to addApplicationFont again, just create QFont objects
            inter_font = QFont("Inter")
            press_start_font = QFont("Press Start 2P")
            self.setStyleSheet(f"""
                AppGuideDialog {{
                    background-color: #0A0A10;
                }}
                QTabWidget::pane {{
                    border: 1px solid #161616;
                    background-color: #111118;
                }}
                QTabBar::tab {{
                    background-color: #1a1a2e;
                    color: #A0A0A0;
                    font-family: '{inter_font.family()}';
                    border: 1px solid #111118;
                    border-bottom: none;
                    border-top-left-radius: 4px;
                    border-top-right-radius: 4px;
                    min-width: 150px;
                    padding: 8px 15px;
                    font-size: 10pt;
                    font-weight: bold;
                }}
                QTabBar::tab:hover {{
                    background-color: #24243e;
                    color: #E0E0E0;
                }}
                QTabBar::tab:selected {{
                    background-color: #111118;
                    color: #6366f1;
                    margin-bottom: -1px;
                }}
                QScrollArea#ControlsScrollArea {{
                    border: none;
                    background-color: #111118;
                }}
                QGroupBox {{
                    font-family: '{press_start_font.family()}';
                    font-size: 11pt;
                    color: #22d3ee;
                    background-color: #18181b;
                    border: 1px solid #111118;
                    border-radius: 6px;
                    margin-top: 10px;
                    padding: 20px 15px 15px 15px;
                }}
                QGroupBox::title {{
                    subcontrol-origin: margin;
                    subcontrol-position: top left;
                    padding: 0 10px;
                    left: 15px;
                }}
                QLabel {{
                    font-family: '{inter_font.family()}';
                    font-size: 10pt;
                    color: #cbd5e1;
                    background-color: transparent;
                }}
                .key-cap {{
                    background-color: #111118;
                    color: #a78bfa;
                    border-radius: 4px;
                    padding: 3px 8px;
                    font-size: 10pt;
                    font-weight: bold;
                    font-family: 'Consolas', 'Courier New', monospace;
                    border: 1px solid #111118;
                }}
            """)
        except Exception as e:
            print(f"AppGuideDialog styling error: {e}")

    def handle_link_clicked(self, url: QUrl):
        if url.scheme() in ["http", "https"]:
            QDesktopServices.openUrl(url)

if __name__ == '__main__':
    import os
    project_root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if project_root_dir not in sys.path:
        sys.path.insert(0, project_root_dir)
    
    # We must import resources_rc after setting up the path, if needed for testing
    try:
        import resources_rc
    except ImportError:
        print("WARNING: resources_rc.py not found. Run the resource compiler first.")

    app = QApplication(sys.argv)
    
    # Load fonts for standalone testing
    try:
        from utils import get_resource_path
        QFontDatabase.addApplicationFont(get_resource_path("resources/fonts/Inter-Regular.ttf"))
        QFontDatabase.addApplicationFont(get_resource_path("resources/fonts/PressStart2P-Regular.ttf"))
    except Exception as e:
        print(f"Standalone Test WARN: Could not load custom fonts. Error: {e}")
        
    dialog = AppGuideDialog()
    dialog.show()
    sys.exit(app.exec())