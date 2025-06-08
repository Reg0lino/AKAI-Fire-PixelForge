import sys
from PyQt6.QtWidgets import QApplication, QDialog, QVBoxLayout, QTextBrowser, QDialogButtonBox
from PyQt6.QtCore import QUrl
from PyQt6.QtGui import QDesktopServices

APP_GUIDE_HTML_CONTENT = """
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<style>
    html, body {
        background: #131313; /* Main background */
        color: #D0D0D0;      /* Main text */
        font-family: 'Segoe UI', Arial, sans-serif;
        font-size: 11pt;
        margin: 0;
        padding: 0;
        height: 100%;
    }
    body {
        padding: 0 0 30px 0;
        min-height: 100vh;
    }
    .container {
        max-width: 900px;
        margin: 32px auto 32px auto;
        padding: 32px 28px 28px 28px;
        background: #181818; /* Card background */
        border-radius: 18px;
        box-shadow: 0 6px 32px 0 rgba(0,10,26,0.2), 0 1.5px 0 #232323;
    }
    h1 {
        color: #FF6EC7; /* Synthwave pink */
        font-size: 2.1em;
        font-weight: 900;
        text-align: center;
        margin-bottom: 14px;
        letter-spacing: 0.01em;
        text-shadow: 0 2px 8px rgba(0,0,0,0.53);
    }
    h2 {
        color: #FFD166; /* Gold/yellow (synthwave accent) */
        font-size: 1.18em;
        font-weight: 700;
        margin-top: 24px;
        margin-bottom: 8px;
        border-bottom: 1.5px solid #232323;
        padding-bottom: 2px;
        letter-spacing: 0.01em;
        text-shadow: 0 1px 8px rgba(0,0,0,0.4);
    }
    h3 {
        color: #A259F7; /* Synthwave purple */
        font-size: 1em;
        font-weight: 600;
        margin-top: 12px;
        margin-bottom: 4px;
        letter-spacing: 0.01em;
    }
    ul.styled-list {
        list-style: disc inside;
        margin: 2px 0 2px 18px;
        padding: 0;
    }
    ul.styled-list li {
        margin-bottom: 0px;
        line-height: 1.1;
        background: none !important;
    }
    p, li {
        color: #D0D0D0;
        line-height: 1.1;
        margin-top: 1px;
        margin-bottom: 1px;
        background: none !important;
    }
    .card {
        background: #181818; /* Match main background */
        border-radius: 12px;
        box-shadow: 0 1.5px 8px rgba(0,0,0,0.25);
        padding: 10px 10px 4px 10px;
        margin-bottom: 8px;
        border: 1px solid #232323;
    }
    .info-block-item {
        background: none !important;
        border-left: 4px solid #FF6EC7; /* Synthwave pink accent */
        border-radius: 0 6px 6px 0;
        margin: 2px 0 2px 0;
        padding: 3px 8px 3px 10px;
        font-size: 1em;
        color: #D0D0D0;
        box-shadow: none;
    }
    .note {
        background: none !important;
        border-left: 4px solid #FFD166;
        border-radius: 0 6px 6px 0;
        margin: 6px 0 6px 0;
        padding: 4px 10px 4px 12px;
        color: #FFD166;
        font-size: 1em;
        font-style: italic;
        box-shadow: none;
    }
    code {
        background: #232B3A;
        color: #A259F7; /* Synthwave purple for code */
        border-radius: 4px;
        padding: 1px 5px;
        font-size: 0.98em;
        font-family: 'Fira Mono', 'Consolas', 'Courier New', monospace;
        margin: 0 1px;
    }
    a, a:visited {
        color: #4FC3F7; /* Cyan/blue synthwave accent */
        text-decoration: underline;
        font-weight: 600;
        transition: color 0.15s;
    }
    a:hover {
        color: #FFD166;
        text-decoration: underline;
    }
    .emoji {
        font-size: 1.1em;
        vertical-align: middle;
    }
    /* DOOM section special styles */
    .doom-section h2, .doom-section .doom-title, .doom-section .doom-imp {
        color: #FF1744 !important;
        text-shadow: 0 0 8px rgba(255,23,68,0.53), 0 0 2px #000;
        letter-spacing: 0.03em;
    }
    .doom-section .info-block-item, .doom-section ul.styled-list li {
        color: #FF8A80;
        background: none !important;
    }
    .doom-section .doom-imp {
        font-weight: bold;
        color: #FF5252 !important;
    }
    .tip-accent {
        color: #FFD166;
        font-weight: bold;
    }
    .blue-accent {
        color: #4FC3F7;
        font-weight: bold;
    }
    .green-accent {
        color: #7ED957;
        font-weight: bold;
    }
    .purple-accent {
        color: #A259F7;
        font-weight: bold;
    }
    .pink-accent {
        color: #FF6EC7;
        font-weight: bold;
    }
    @media (max-width: 700px) {
        .container {
            padding: 10px 2vw 10px 2vw;
        }
        h1 { font-size: 1.3em; }
        h2 { font-size: 1.1em; }
        h3 { font-size: 1em; }
    }
</style>
</head>
<body>
<div class="container">
<h1>🚀 Akai Fire PixelForge - App Guide (v1.0.0) 🚀</h1>

<p>Welcome to <b class="blue-accent">Akai Fire PixelForge</b>! This guide will help you unlock the creative power and new gaming dimension of your Akai Fire controller.</p>

<div class="card">
<h2>Core Features At a Glance</h2>
<ul class="styled-list">
    <li>🎨 <b class="green-accent">Direct Pad Painting:</b> Instantly paint colors onto the 4x16 pad grid.</li>
    <li>🖼️ <b>Static Pad Layouts:</b> Design, save, and load full-color static images for your pads.</li>
    <li>🎬 <b class="blue-accent">Animator Studio:</b> A powerful frame-by-frame sequencer for designing intricate RGB pad animations.</li>
    <li>💡 <b class="tip-accent">Screen Sampler (Ambient Mode):</b> Dynamically mirror colors from your screen onto the pads and record the output.</li>
    <li>⚙️ <b>Advanced OLED Screen Customization:</b> Create custom Text, Image, and GIF items with a rich processing pipeline including multiple dithering options. <b class="blue-accent">Animated GIFs are supported for OLED animations!</b></li>
    <li>👹 <b class="doom-title">NEW! LazyDOOM Game Mode:</b> Play a retro first-person shooter directly on your Akai Fire's OLED!</li>
    <li>🎛️ <b>Hardware Integration:</b> Contextual knob controls and button mapping for seamless interaction.</li>
</ul>
</div>

<div class="card">
<h2>🎨 Pad Painting & Animator Studio 🎬</h2>
<h3 class="blue-accent">Direct Pad Painting</h3>
<p>Select a color from the robust Color Picker (includes SV map, Hue slider, RGB/Hex inputs, and savable "My Colors" swatches). Then, simply left-click (or drag) on the main 4x16 GUI grid to paint pads. Right-click (or drag) erases pads to black. Use the <code>I</code> key to toggle the Eyedropper tool and pick colors directly from the grid.</p>
<h3>Static Pad Layouts</h3>
<p>Design full static color images for your pads. Save your creations as presets and load them instantly. Great for setting up default states or visual templates.</p>
<h3 class="blue-accent">Animator Studio</h3>
<ul class="styled-list">
    <li><b>Visual Timeline:</b> Easily manage your animation frames. Select, multi-select, and reorder.</li>
    <li><b>Frame Operations:</b> Add blank frames, add snapshots of the current grid, Delete, Duplicate, Copy (<code>Ctrl</code>+<code>C</code>), Cut (<code>Ctrl</code>+<code>X</code>), and Paste (<code>Ctrl</code>+<code>V</code>) frames.</li>
    <li><b>Smooth Workflow:</b> Undo (<code>Ctrl</code>+<code>Z</code>) and Redo (<code>Ctrl</code>+Y) support for paint strokes and most frame operations.</li>
    <li><b>Playback Control:</b> Adjust animation speed (FPS) and looping behavior. Play/pause with the <code>Spacebar</code>.</li>
    <li><b>Sequence Management:</b> Save, load, create new (<code>Ctrl</code>+<code>N</code>), and delete animation sequence files (stored in your Documents).</li>
</ul>
</div>

<div class="card">
<h2>💡 Screen Sampler (Ambient Mode) ✨</h2>
<ul class="styled-list">
    <li><b>Activation:</b> Toggle using the "Toggle Ambient Sampling" button in the UI or the <code>PERFORM</code>/<code>BROWSER</code> buttons on your Akai Fire.</li>
    <li><b>Configuration:</b> Click "Configure Region & Adjustments."
        <ul class="styled-list">
            <li>Select the target monitor to sample from (cycle with the <code>DRUM</code> button on the Fire).</li>
            <li>Visually drag and resize the selection box on your screen to define the capture area.</li>
            <li>Fine-tune the visual output with real-time sliders for <b>Brightness, Saturation, Contrast,</b> and <b>Hue Shift</b> of the sampled colors. These settings are saved per monitor.</li>
        </ul>
    </li>
    <li>🌟 <b class="tip-accent">Record Sampler Output:</b> This is where the magic happens! Click "Record" to capture the dynamic visuals from the sampler directly into a new animation sequence in the Animator Studio. This is perfect for creating unique animations from videos, music visualizers, or any on-screen content.</li>
</ul>
</div>

<div class="card">
<h2>⚙️ Advanced OLED Screen Customization 🖼️</h2>
<p class="info-block-item"><b>Active Graphic System:</b> Designate any of your custom creations (text, image, or animation) to be the persistent default display on your Fire's OLED after the initial startup visual. Use the "Save & Apply" button for quick changes.</p>
<p class="info-block-item"><b>Manual Play/Pause:</b> A clickable icon next to the UI's OLED mirror allows you to manually pause or resume your current Active Graphic.</p>
<h3 class="blue-accent">Content Library:</h3>
<p class="info-block-item"><b>Text Items:</b> Design scrolling or static text. Choose from available system fonts, set pixel-perfect font sizes, and define alignment (for static text) or scrolling parameters (speed override, end pauses).</p>
<p class="info-block-item"><b>Image & GIF Animation Items:</b> Import your favorite static images (PNG, JPG, etc.) or <b class="blue-accent">animated GIFs</b>. PixelForge v1.0.0 introduces an <b>Advanced Processing Pipeline</b> for unparalleled control:</p>
<ul class="styled-list">
    <li><b>Pre-Dithering Adjustments:</b> Fine-tune your source image <em>before</em> 1-bit conversion using sliders for Brightness, Contrast, <b>Gamma Correction</b> (for mid-tone balance), <b>Sharpening</b> (to enhance details), and <b>Pre-Dither Blur</b> (to soften images for smoother dithering).</li>
    <li><b>Expanded Dithering Arsenal:</b> Choose from a wider range of algorithms: Classics like Floyd-Steinberg, Simple Threshold (adjustable), AND New Additions like <b>Atkinson Dither</b> (sharper, high-contrast), <b>Ordered Dithering</b> (Bayer 2x2 for retro blockiness, Bayer 4x4, and Bayer 8x8 for finer patterns).</li>
    <li><b>Variable Dither Strength:</b> For error-diffusion algorithms (Floyd-Steinberg, Atkinson), a slider lets you blend between a simple threshold (0% strength) and the full dithering effect (100%).</li>
    <li><b>Noise Injection:</b> Add stylistic "Pre-Dither" (subtle) or "Post-Dither" (grainy) noise with adjustable intensity.</li>
    <li>Standard options like Resize Modes (Stretch, Fit/Pad, Crop) and Color Inversion are also available.</li>
</ul>
<p class="info-block-item"><b>System Messages:</b> Clear, temporary messages using a retro "TomThumb" font provide feedback for application actions (like knob turns or sampler status changes), overlaying your Active Graphic and then gracefully reverting.</p>
<p class="note"><b>Tip for OLEDs:</b> Experiment! Different combinations of pre-dithering adjustments and dithering algorithms can produce vastly different artistic results on the monochrome display. <b>Short, seamlessly looping animated GIFs often work best for OLED animations.</b></p>
</div>

<div class="card doom-section">
<h2>👹 NEW! <span class="doom-title">LazyDOOM</span> - Retro FPS on Your Fire! 🎮</h2>
<p class="info-block-item"><b>How to Launch:</b> Find and click the "<span class="doom-imp">👹 LazyDOOM</span>" button located in the main application's right-hand panel.</p>
<p class="info-block-item"><b>Pre-Game Instructions:</b> Before the action starts, an <b>Instructions Dialog</b> will appear. <b>Please read this carefully!</b> It explains all game controls (both pad and keyboard), gameplay objectives, and tips for survival.</p>
<h3 class="doom-title">Gameplay Overview:</h3>
<ul class="styled-list">
    <li class="doom-imp">Navigate unique, procedurally generated maze-like levels displayed on the 128x64 OLED screen.</li>
    <li class="doom-imp">Hunt down and eliminate "Imp" enemies using your trusty hitscan weapon.</li>
    <li class="doom-imp">Manage your Health (HP), which is shown on the OLED HUD and also visually represented on a dedicated row of pads on your Akai Fire.</li>
    <li class="doom-imp">Defeat all Imps on the current level to emerge victorious!</li>
</ul>
<h3 class="doom-title">Controls & Feedback:</h3>
<ul class="styled-list">
    <li><b>Pad-Powered Action:</b> All primary game functions (movement, strafing, turning, running, shooting) are mapped to the Akai Fire's pads.</li>
    <li><b>Keyboard Support:</b> Standard FPS keyboard controls (e.g., <code>WASD</code> for movement, <code>F</code> to shoot, <code>Shift</code> to run) are also active during gameplay.</li>
    <li><b>Visual Immersion:</b> Get real-time feedback with on-OLED screen glitches when you take damage, and dynamic RGB pad lighting for health status and game events.</li>
    <li><b>Game Over & Restart:</b> If you fall in battle, the "SHOOT" pad will blink – press it to jump right back in and try again!</li>
</ul>
<h3 class="doom-title">Choose Your Challenge:</h3>
<ul class="styled-list">
    <li>Select from three difficulty levels (Normal, Hard, Nightmare!) when launching LazyDOOM. Harder modes feature more aggressive and/or numerous enemies.</li>
</ul>
<h3 class="doom-title">Dedicated Game Mode:</h3>
<ul class="styled-list">
    <li>While LazyDOOM is active, other PixelForge features (Animator, Sampler, etc.) are temporarily paused to ensure optimal game performance. Exiting LazyDOOM smoothly restores your previous PixelForge setup.</li>
</ul>
</div>

<div class="card">
<h2>🎛️ Hardware Controls Explained (PixelForge Modes)</h2>
<p>Your Akai Fire controller's knobs and buttons have special functions within PixelForge's main creative modes (Animator, Sampler, Static Layouts). The OLED will briefly show their current function when a top knob is turned.</p>
<h3 class="blue-accent">Knobs (Top Row):</h3>
<ul class="styled-list">
    <li><b>Default/Editing Mode</b> (Screen Sampler OFF & Animator NOT Playing):
        <ul class="styled-list">
            <li><b>Knob 1 (Volume):</b> 🌟 Adjusts Global Pad Brightness for all non-sampler pad visuals.</li>
            <li><b>Knob 4 (Resonance):</b> ⏱️ Adjusts the current Animator Sequence's properties for playback Speed (FPS/delay).</li>
            <li><em>Knobs 2 (Pan) & 3 (Filter) are currently unassigned in this mode.</em></li>
        </ul>
    </li>
    <li><b>Screen Sampler ON:</b>
        <ul class="styled-list">
            <li><b>Knob 1 (Volume):</b> 💡 Sampler Output Brightness</li>
            <li><b>Knob 2 (Pan):</b> 🌈 Sampler Output Saturation</li>
            <li><b>Knob 3 (Filter):</b> 🎚️ Sampler Output Contrast</li>
            <li><b>Knob 4 (Resonance):</b> 🎨 Sampler Output Hue Shift</li>
        </ul>
    </li>
    <li><b>Animator PLAYING (Screen Sampler is automatically OFF):</b>
        <ul class="styled-list">
            <li><b>Knob 4 (Resonance):</b> ⏱️ Adjusts active Animation Playback Speed (FPS) in real-time (temporary change for current playback).</li>
            <li><em>Knobs 1-3 are inactive or control their default functions if applicable and not overridden by playback.</em></li>
        </ul>
    </li>
</ul>
<h3>Buttons:</h3>
<ul class="styled-list">
    <li><b>PERFORM / BROWSER Button:</b> 💡 Toggles the Screen Sampler ON/OFF.</li>
    <li><b>DRUM Button:</b> 🖥️ Cycles through available computer monitors for the Screen Sampler (when Sampler is ON).</li>
    <li><b>GRID LEFT / GRID RIGHT Buttons:</b> ◀️▶️ Navigates between item categories in the right panel (e.g., "Animator Sequences" list vs. "Static Pad Layouts" list).</li>
    <li><b>SELECT Knob (Turn):</b> 📜 Scrolls through items within the currently focused category's list. The OLED will briefly display the cued item name.</li>
    <li><b>SELECT Knob (Press):</b> ✔️ Loads/Applies the currently highlighted item from the focused list.</li>
    <li><b>PLAY (Physical Button):</b> ▶️ Plays/Pauses the current animation in the Animator Studio.</li>
    <li><b>STOP (Physical Button):</b> ⏹️ Stops animation playback in Animator Studio.</li>
    <li><b>PATTERN UP / PATTERN DOWN Buttons:</b> 🔼🔽 <b class="tip-accent">Cycle through your active OLED animations (to the left of the OLED screen) without any code changes required!</b></li>
</ul>
</div>

<div class="card">
<h2>⌨️ Keyboard Shortcuts (Hotkeys - PixelForge Modes)</h2>
<h3 class="blue-accent">Animator Studio:</h3>
<ul class="styled-list">
    <li><b>Undo:</b> <code>Ctrl</code> + <code>Z</code></li>
    <li><b>Redo:</b> <code>Ctrl</code> + <code>Y</code></li>
    <li><b>Copy Frame(s):</b> <code>Ctrl</code> + <code>C</code></li>
    <li><b>Cut Frame(s):</b> <code>Ctrl</code> + <code>X</code></li>
    <li><b>Paste Frame(s):</b> <code>Ctrl</code> + <code>V</code></li>
    <li><b>Duplicate Frame(s):</b> <code>Ctrl</code> + <code>D</code></li>
    <li><b>Delete Frame(s):</b> <code>Delete</code></li>
    <li><b>Add New Blank Frame:</b> <code>Ctrl</code> + <code>Shift</code> + <code>B</code></li>
    <li><b>Select All Frames:</b> <code>Ctrl</code> + <code>A</code></li>
    <li><b>Play/Pause Animation:</b> <code>Spacebar</code></li>
    <li><b>New Sequence:</b> <code>Ctrl</code> + <code>N</code></li>
    <li><b>Save Sequence As...:</b> <code>Ctrl</code> + <code>Shift</code> + <code>S</code></li>
</ul>
<h3>Pad Grid / Painting Mode:</h3>
<p class="info-block-item"><b>Toggle Eyedropper Mode:</b> <code>I</code> (Press 'I', click pad to pick color. Mode deactivates after pick.)</p>
<p class="note"><b>LazyDOOM Mode:</b> While LazyDOOM is active, it uses its own keyboard control scheme (e.g., <code>WASD</code> for movement, <code>F</code> to shoot, <code>Shift</code> to run). Refer to the pre-game Instructions Dialog for the complete mapping for LazyDOOM.</p>
</div>

<div class="card">
<h2>🌟 Super User Tips & Tricks 🌟</h2>
<h3 class="tip-accent">Master the Sampler for Animations:</h3>
<p class="info-block-item"><b>Record Everything:</b> Music visualizers, movie scenes, abstract art videos, even other pixel art apps!</p>
<p class="info-block-item"><b>GIPHY & Beyond:</b> <a href="https://giphy.com" target="_blank"><font color="#2196F3"><b>GIPHY</b></font></a> is a goldmine for <b>screen sampling</b> (for pad animations) <em>and</em> for finding <b>animated GIFs</b> to use in the OLED customizer. Play short loops full screen, sample, and record, or download GIFs for OLED animations!</p>
<p class="info-block-item"><b>Sampler Adjustments are Key:</b> Tweak Brightness, Saturation, Contrast, Hue <i>before</i> recording for unique styles.</p>
<h3 class="blue-accent">Animator Workflow:</h3>
<p class="info-block-item"><b>Start Simple:</b> Keyframes first, then duplicate/modify. "Duplicate" is your friend!</p>
<p class="info-block-item"><b>Experiment with FPS:</b> Drastically changes animation feel. Remember Knob 4!</p>
<h3 class="blue-accent">OLED Creativity Unleashed:</h3>
<p class="info-block-item"><b>Font Choice:</b> Experiment with system fonts and sizes. Pixel-style fonts can look great.</p>
<p class="info-block-item"><b>Dithering Deep Dive:</b> For pixel art, 'Simple Threshold' or 'Ordered Dither (Bayer 2x2)' can give crisp results. For photos/gradients, experiment with 'Floyd-Steinberg' or 'Atkinson' and adjust the 'Dither Strength' slider. Use 'Pre-Dither Blur' (gently!) on photos for smoother tones. 'Sharpen' can help preserve details in graphic logos.</p>
<p class="info-block-item"><b>Short & Sweet Loops:</b> For animated OLED graphics, short, seamlessly looping GIFs often work best. <a href="https://giphy.com" target="_blank"><font color="#2196F3"><b>GIPHY</b></font></a> is a great source!</p>
<h3 class="doom-title">LazyDOOM Tactics:</h3>
<p class="info-block-item doom-imp">Strafing is your best friend! Use it to dodge projectiles and peek around corners.</p>
<p class="info-block-item doom-imp">Don't forget to use the Run button in open areas or when retreating.</p>
<h3 class="tip-accent">General Tips:</h3>
<p class="info-block-item"><b>Color Picker Power:</b> Save favorites to "My Colors." Use Eyedropper (<code>I</code> key) on the grid.</p>
<p class="info-block-item"><b>Hardware Knob Context:</b> Watch the OLED! It tells you what the top knobs are controlling.</p>
<p class="info-block-item"><b>Backup Your Presets:</b> Your creations are in "<code>Documents\\Akai Fire RGB Controller User Presets</code>". Backup this folder!</p>
</div>

</div>
</body>
</html>
"""

class AppGuideDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(
            "🚀 Akai Fire PixelForge - App Guide (v1.0.0)")  # Updated Title
        self.setMinimumSize(900, 650) # the first value is width, the second is height
        self.resize(1000, 850)  # Slightly larger default size for more content
        layout = QVBoxLayout(self)
        self.text_browser = QTextBrowser()
        self.text_browser.setOpenExternalLinks(True)
        self.text_browser.setHtml(APP_GUIDE_HTML_CONTENT)
        # Ensure links open in external browser
        self.text_browser.anchorClicked.connect(self.handle_link_clicked)
        layout.addWidget(self.text_browser)
        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        self.button_box.accepted.connect(self.accept)
        layout.addWidget(self.button_box)
        self.setLayout(layout)

    def handle_link_clicked(self, url: QUrl):
        """Ensure external links are opened by the system's default browser."""
        if url.scheme() in ["http", "https"]:  # Only open http/https links externally
            QDesktopServices.openUrl(url)
        else:
            # For internal anchors or other schemes, let QTextBrowser handle it
            # (though we don't have internal anchors here right now)
            pass

    def set_guide_content(self, html_content: str):
        self.text_browser.setHtml(html_content)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    try:
        import os
        current_dir = os.path.dirname(os.path.abspath(__file__))
        # Assumes gui folder is one level down from root
        project_root_dir = os.path.dirname(current_dir)
        # Go up one more level if this script is in a sub-sub-directory like gui/dialogs
        # project_root_dir = os.path.dirname(os.path.dirname(current_dir))
        style_file_path = os.path.join(
            project_root_dir, "resources", "styles", "style.qss")
        if os.path.exists(style_file_path):
            with open(style_file_path, "r") as f_style:
                app.setStyleSheet(f_style.read())
                print(
                    f"AppGuideDialog Test: Loaded style.qss from '{style_file_path}'")
        else:
            print(
                f"AppGuideDialog Test: style.qss not found at '{style_file_path}' (expected project structure).")
    except Exception as e_style:
        print(f"AppGuideDialog Test: Error loading style.qss: {e_style}")
    dialog = AppGuideDialog()
    dialog.show()
    sys.exit(app.exec())
