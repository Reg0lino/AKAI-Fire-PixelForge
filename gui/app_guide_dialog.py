# AKAI_Fire_RGB_Controller/gui/app_guide_dialog.py
import sys
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QTextBrowser, QDialogButtonBox, QApplication
)
from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtGui import QDesktopServices

# --- HTML Content for the App Guide ---
# (We'll use the draft from our previous discussion here)
# Note: For long HTML strings, Python's triple quotes are excellent.
# For even better organization with very long content, you could load this from a separate .html file.

APP_GUIDE_HTML_CONTENT = """
<!DOCTYPE html>
<html>
<head>
<style>
    body {{
        font-family: "Segoe UI", Arial, sans-serif;
        background-color: #181818; /* Match main app background */
        color: #B3B3B3; /* Match main app text color */
        font-size: 10pt;
        line-height: 1.6;
    }}
    h1 {{
        color: #E0E0E0; /* Lighter for main title */
        text-align: center;
        font-size: 16pt;
        margin-bottom: 15px;
    }}
    h2 {{
        font-size: 13pt;
        border-bottom: 1px solid #404040;
        padding-bottom: 3px;
        margin-top: 20px;
        margin-bottom: 10px;
    }}
    ul {{
        list-style-type: disc; /* Or 'circle' or 'square' */
        padding-left: 20px; /* Indent list items */
        margin-top: 5px;
        margin-bottom: 10px;
    }}
    li {{
        margin-bottom: 4px;
    }}
    p {{
        margin-bottom: 10px;
    }}
    strong, b {{ /* For hotkey emphasis */
        color: #D0D0D0; /* Slightly brighter for keys */
    }}
    code {{ /* For inline code or key names if desired */
        background-color: #282828;
        padding: 1px 3px;
        border-radius: 3px;
        font-family: "Consolas", "Courier New", monospace;
    }}
    a {{
        color: #42A5F5; /* Link color */
        text-decoration: none;
    }}
    a:hover {{
        text-decoration: underline;
    }}
    .emoji {{ /* If we need to style specific emojis later, though unicode usually fine */
        /* font-size: 1.1em; */
    }}
</style>
</head>
<body>

<h1>🚀 Akai Fire PixelForge - App Guide 🚀</h1>

<p>Welcome to Akai Fire PixelForge! This guide will help you unlock the creative power of your Akai Fire controller.</p>

<h2 style="color: #66BB6A;">Core Features At a Glance</h2>
<p>PixelForge transforms your Akai Fire into a versatile tool for visual expression:</p>
<ul>
    <li>🎨 <strong>Direct Pad Painting:</strong> Instantly paint colors onto the 4x16 pad grid. Left-click (or drag) applies your selected color; right-click (or drag) erases to black.</li>
    <li>🖼️ <strong>Static Pad Layouts:</strong> Design, save, and load full-color static images for your pads – great for templates or fixed visual states.</li>
    <li>🎬 <strong>Animator Studio:</strong> A powerful frame-by-frame sequencer for designing intricate RGB pad animations.
        <ul>
            <li>Visual timeline to manage animation frames.</li>
            <li>Tools: Add, Delete, Duplicate, Copy, Cut, and Paste frames.</li>
            <li>Control playback speed (FPS) and looping.</li>
        </ul>
    </li>
    <li>💡 <strong style="color: #FFCA28;">Screen Sampler (Ambient Mode) - ✨ The Heart of PixelForge! ✨</strong>
        <ul>
            <li>Select any region of your computer screen.</li>
            <li>PixelForge dynamically samples colors from this region and mirrors them onto the Akai Fire's pads in real-time.</li>
            <li>Fine-tune the look with adjustments for <strong>Brightness, Saturation, Contrast, and Hue</strong> of the sampled colors.</li>
            <li><strong>Record Sampler Output:</strong> Capture your dynamic sampler visuals directly into new animation sequences in the Animator Studio! This is where the magic happens – create limitless, unique pad animations.</li>
        </ul>
    </li>
    <li>⚙️ <strong>OLED Screen Customization:</strong> Take control of your Fire's 128x64 OLED display! Click the on-screen OLED mirror to access the Customizer.
        <ul>
            <li><strong>Active Graphic System:</strong> Set a persistent custom image, animation, or text item as your default OLED display.</li>
            <li><strong>Text Items:</strong> Design scrolling or static text using system fonts, custom sizes, and alignment.</li>
            <li><strong>Image & GIF Items:</strong> Import static images (PNG, JPG, etc.) and animated GIFs. PixelForge processes them with various resize modes, contrast adjustments, and multiple dithering options for optimal monochrome display.</li>
            <li><strong>System Messages:</strong> Clear, temporary messages (using a retro "TomThumb" font) provide feedback for application actions, overlaying your Active Graphic.</li>
        </ul>
    </li>
    <li>🎛️ <strong>Hardware Integration:</strong> Your Akai Fire controller becomes a true extension of the software.</li>
</ul>

<h2 style="color: #42A5F5;">Hardware Controls Explained</h2>
<p>Your Akai Fire controller's knobs and buttons have special functions within PixelForge:</p>
<h3>Knobs (Top Row):</h3>
<p>These are context-sensitive! The OLED will briefly show their current function when turned.</p>
<ul>
    <li><strong>Default/Editing Mode</strong> (Screen Sampler OFF & Animator NOT Playing):
        <ul>
            <li><strong>Knob 1 (Volume):</strong> 🌟 Adjusts Global Pad Brightness for all non-sampler pad visuals. <em>(Note: Global Brightness is temporarily inactive when an animation is playing).</em></li>
            <li><strong>Knob 2 (Pan):</strong> (Currently Unassigned)</li>
            <li><strong>Knob 3 (Filter):</strong> (Currently Unassigned)</li>
            <li><strong>Knob 4 (Resonance):</strong> ⏱️ Adjusts the current Animator Sequence's properties for playback Speed (FPS/delay).</li>
        </ul>
    </li>
    <li><strong>Screen Sampler ON:</strong>
        <ul>
            <li><strong>Knob 1 (Volume):</strong> 💡 Sampler Output Brightness</li>
            <li><strong>Knob 2 (Pan):</strong> 🌈 Sampler Output Saturation</li>
            <li><strong>Knob 3 (Filter):</strong> 🎚️ Sampler Output Contrast</li>
            <li><strong>Knob 4 (Resonance):</strong> 🎨 Sampler Output Hue Shift</li>
        </ul>
    </li>
    <li><strong>Animator PLAYING (Screen Sampler is automatically OFF):</strong>
        <ul>
            <li><strong>Knob 1 (Volume):</strong> (Global Pad Brightness control is inactive during animation playback)</li>
            <li><strong>Knob 2 (Pan):</strong> (Currently Unassigned)</li>
            <li><strong>Knob 3 (Filter):</strong> (Currently Unassigned)</li>
            <li><strong>Knob 4 (Resonance):</strong> ⏱️ Adjusts active Animation Playback Speed (FPS) in real-time (this change is temporary for the current playback session and does not alter saved sequence properties).</li>
        </ul>
    </li>
</ul>

<h3>Buttons:</h3>
<ul>
    <li><strong>PERFORM Button:</strong> 💡 Toggles the Screen Sampler ON/OFF.</li>
    <li><strong>BROWSER Button:</strong> 💡 Also toggles the Screen Sampler ON/OFF. <em>(Future functionality for this button, like OLED item activation, is planned).</em></li>
    <li><strong>DRUM Button:</strong> 🖥️ Cycles through available computer monitors for the Screen Sampler (when Sampler is ON).</li>
    <li><strong>GRID LEFT Button:</strong> ◀️ Navigates to the previous item category (e.g., from "Animator Sequences" list to "Static Pad Layouts" list).</li>
    <li><strong>GRID RIGHT Button:</strong> ▶️ Navigates to the next item category (e.g., from "Static Pad Layouts" list to "Animator Sequences" list).</li>
    <li><strong>SELECT Knob (Turn):</strong> 📜 Scrolls through items within the currently focused category's list. The OLED will briefly display the cued item name.</li>
    <li><strong>SELECT Knob (Press):</strong> ✔️ Loads/Applies the currently highlighted item from the focused list. <em>(If the current Animator sequence has unsaved changes, a confirmation dialog will appear on your computer screen).</em></li>
    <li><strong>PLAY (Physical Button):</strong> ▶️ Plays/Pauses the current animation in the Animator Studio.</li>
    <li><strong>STOP (Physical Button):</strong> ⏹️ Stops animation playback in Animator Studio and resets the view to the currently selected edit frame.
        <em>(Note: The physical PLAY/STOP LEDs on the Akai Fire are intentionally kept off by this application).</em></li>
    <li><strong>PATTERN UP / PATTERN DOWN Buttons:</strong> (🚧 <strong>Future Feature:</strong> These buttons are planned for navigating and cueing custom OLED items. Currently, all OLED item management and "Active Graphic" selection is done via mouse in the OLED Customizer Dialog.)</li>
</ul>

<h2 style="color: #EF5350;">Keyboard Shortcuts (Hotkeys)</h2>
<h3>Animator Studio:</h3>
<ul>
    <li><strong>Undo Last Action:</strong> <code>Ctrl</code> + <code>Z</code></li>
    <li><strong>Redo Last Action:</strong> <code>Ctrl</code> + <code>Y</code></li>
    <li><strong>Copy Selected Frame(s):</strong> <code>Ctrl</code> + <code>C</code></li>
    <li><strong>Cut Selected Frame(s):</strong> <code>Ctrl</code> + <code>X</code></li>
    <li><strong>Paste Frame(s) from Clipboard:</strong> <code>Ctrl</code> + <code>V</code></li>
    <li><strong>Duplicate Selected Frame(s):</strong> <code>Ctrl</code> + <code>D</code></li>
    <li><strong>Delete Selected Frame(s):</strong> <code>Delete</code></li>
    <li><strong>Add New Blank Frame:</strong> <code>Ctrl</code> + <code>Shift</code> + <code>B</code></li>
    <li><strong>Select All Frames in Timeline:</strong> <code>Ctrl</code> + <code>A</code></li>
    <li><strong>Play/Pause Current Animation:</strong> <code>Spacebar</code></li>
    <li><strong>Create New Animation Sequence:</strong> <code>Ctrl</code> + <code>N</code></li>
    <li><strong>Save Current Animation Sequence As...:</strong> <code>Ctrl</code> + <code>Shift</code> + <code>S</code></li>
</ul>
<h3>Pad Grid / Painting Mode:</h3>
<ul>
    <li><strong>Toggle Eyedropper Mode:</strong> <code>I</code>
        <em>(Press 'I' to activate, then click a pad to pick its color for painting. Mode deactivates automatically after picking. Press 'I' again to toggle off if no pick is made).</em>
    </li>
</ul>

<h2 style="color: #FFCA28;">🌟 Super User Tips & Tricks 🌟</h2>
<ul>
    <li><strong>Master the Sampler for Animations:</strong>
        <ul>
            <li><strong>Record Everything:</strong> Play music visualizers, movie scenes, abstract art videos, or even other pixel art applications on your screen and record the sampler's output. This is the fastest way to generate complex and organic animations.</li>
            <li><strong>GIPHY & Beyond:</strong> Websites like <a href="https://giphy.com">GIPHY</a>, or any source of short video loops, are goldmines. Find a cool GIF, play it full screen (or in the sampler region), and record!</li>
            <li><strong>Sampler Adjustments are Key:</strong> Before recording, tweak the Sampler's Brightness, Saturation, Contrast, and Hue. Drastically different visual styles can be achieved.</li>
            <li><strong>Layering Recordings:</strong> Record a base animation. Then, play that animation back on your screen and sample <em>that</em> with different adjustments or a different screen region to create layered effects.</li>
        </ul>
    </li>
    <li><strong>Animator Workflow:</strong>
        <ul>
            <li><strong>Start Simple:</strong> If hand-drawing, begin with keyframes and then duplicate/modify them.</li>
            <li><strong>Use "Duplicate" Liberally:</strong> It's often easier to duplicate an existing frame and make small changes than to paint everything from scratch.</li>
            <li><strong>Experiment with FPS:</strong> Slow, smooth transitions or fast, flickering effects can dramatically change the feel. Remember Knob 4 adjusts sequence properties when editing, and live playback speed when an animation is playing.</li>
        </ul>
    </li>
    <li><strong>OLED Creativity:</strong>
        <ul>
            <li><strong>Font Choice Matters:</strong> Experiment with different system fonts and sizes for your OLED Text Items. Some pixel-style fonts can look exceptionally good.</li>
            <li><strong>GIF Processing:</strong> When importing GIFs for the OLED, try all the dithering modes. Adjusting contrast <em>before</em> dithering can make a huge difference.</li>
            <li><strong>Short & Sweet:</strong> For animated OLED graphics, short, seamlessly looping GIFs often work best.</li>
        </ul>
    </li>
    <li><strong>Color Picker Power:</strong>
        <ul>
            <li><strong>Save "My Colors":</strong> Don't forget to save your favorite painting colors to the "My Colors" swatches for quick access.</li>
            <li><strong>Eyedropper (<code>I</code> key):</strong> Quickly grab a color from an existing pad on the grid to continue painting with it.</li>
        </ul>
    </li>
    <li><strong>Hardware Knob Context:</strong> Pay attention to the OLED! It will briefly tell you what the top four knobs are controlling as their context changes.</li>
    <li><strong>Backup Your Presets:</strong> Your custom creations (Animator sequences, Static Layouts, OLED items) are saved in your "<code>Documents\\Akai Fire RGB Controller User Presets</code>" folder. Back this folder up periodically!</li>
</ul>

</body>
</html>
"""


class AppGuideDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("🚀 Akai Fire PixelForge - App Guide")
        self.setMinimumSize(700, 550)  # Adjust as needed
        self.resize(800, 600)       # Default starting size

        layout = QVBoxLayout(self)

        self.text_browser = QTextBrowser()
        self.text_browser.setOpenExternalLinks(True)  # For the GIPHY link
        self.text_browser.setHtml(APP_GUIDE_HTML_CONTENT)
        layout.addWidget(self.text_browser)

        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        self.button_box.accepted.connect(self.accept)
        layout.addWidget(self.button_box)

        self.setLayout(layout)

    def set_guide_content(self, html_content: str):
        """Allows updating the content dynamically if needed in the future."""
        self.text_browser.setHtml(html_content)


# --- For standalone testing of this dialog ---
if __name__ == '__main__':
    app = QApplication(sys.argv)
    # You'll need your main style.qss to be discoverable if you want to test with it.
    # For simplicity, this test won't load the main QSS by default.
    # If you want to test with styles, you'd add similar QSS loading logic here
    # as in your fire_control_app.py or main_window.py.

    # Example: Rudimentary style loading for testing
    try:
        import os
        # Assuming this script is in gui, and resources is in ../resources
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root_dir = os.path.dirname(current_dir)
        style_file_path = os.path.join(
            project_root_dir, "resources", "styles", "style.qss")
        if os.path.exists(style_file_path):
            with open(style_file_path, "r") as f_style:
                app.setStyleSheet(f_style.read())
                print(f"AppGuideDialog Test: Loaded style.qss")
        else:
            print(
                f"AppGuideDialog Test: style.qss not found at '{style_file_path}'")
    except Exception as e_style:
        print(f"AppGuideDialog Test: Error loading style.qss: {e_style}")

    dialog = AppGuideDialog()
    dialog.show()
    sys.exit(app.exec())