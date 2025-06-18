import sys
from PyQt6.QtWidgets import QApplication, QDialog, QVBoxLayout, QTextBrowser, QDialogButtonBox
from PyQt6.QtCore import QUrl
from PyQt6.QtGui import QDesktopServices

APP_GUIDE_HTML_CONTENT = """
<!DOCTYPE html >
<html >
<head >
<meta charset = "UTF-8" >
<style >
    html, body {
        background:  # 131313; /* Main background */
        color:  # D0D0D0;      /* Main text */
        font-family: 'Segoe UI', Arial, sans-serif;
        font-size: 11pt;
        margin: 0;
        padding: 0;
        height: 100 % ;
    }
    body {
        padding: 0 0 30px 0;
        min-height: 100vh;
    }
    .container {
        max-width: 900px;
        margin: 32px auto 32px auto;
        padding: 32px 28px 28px 28px;
        background:  # 181818; /* Card background */
        border-radius: 18px;
        box-shadow: 0 6px 32px 0 rgba(0, 10, 26, 0.2), 0 1.5px 0  # 232323;
    }
    h1 {
        color:  # FF6EC7; /* Synthwave pink */
        font-size: 2.1em;
        font-weight: 900;
        text-align: center;
        margin-bottom: 14px;
        letter-spacing: 0.01em;
        text-shadow: 0 2px 8px rgba(0, 0, 0, 0.53);
    }
    h2 {
        color:  # FFD166; /* Gold/yellow (synthwave accent) */
        font-size: 1.18em;
        font-weight: 700;
        margin-top: 24px;
        margin-bottom: 8px;
        border-bottom: 1.5px solid  # 232323;
        padding-bottom: 2px;
        letter-spacing: 0.01em;
        text-shadow: 0 1px 8px rgba(0, 0, 0, 0.4);
    }
    h3 {
        color:  # A259F7; /* Synthwave purple */
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
        color:  # D0D0D0;
        line-height: 1.1;
        margin-top: 1px;
        margin-bottom: 1px;
        background: none !important;
    }
    .card {
        background:  # 181818; /* Match main background */
        border-radius: 12px;
        box-shadow: 0 1.5px 8px rgba(0, 0, 0, 0.25);
        padding: 10px 10px 4px 10px;
        margin-bottom: 8px;
        border: 1px solid  # 232323;
    }
    .info-block-item {
        background: none !important;
        border-left: 4px solid  # FF6EC7; /* Synthwave pink accent */
        border-radius: 0 6px 6px 0;
        margin: 2px 0 2px 0;
        padding: 3px 8px 3px 10px;
        font-size: 1em;
        color:  # D0D0D0;
        box-shadow: none;
    }
    .note {
        background: none !important;
        border-left: 4px solid  # FFD166;
        border-radius: 0 6px 6px 0;
        margin: 6px 0 6px 0;
        padding: 4px 10px 4px 12px;
        color:  # FFD166;
        font-size: 1em;
        font-style: italic;
        box-shadow: none;
    }
    code {
        background:  # 232B3A;
        color:  # A259F7; /* Synthwave purple for code */
        border-radius: 4px;
        padding: 1px 5px;
        font-size: 0.98em;
        font-family: 'Fira Mono', 'Consolas', 'Courier New', monospace;
        margin: 0 1px;
    }
    a, a: visited {
        color:  # 4FC3F7; /* Cyan/blue synthwave accent */
        text-decoration: underline;
        font-weight: 600;
        transition: color 0.15s;
    }
    a: hover {
        color:  # FFD166;
        text-decoration: underline;
    }
    .emoji {
        font-size: 1.1em;
        vertical-align: middle;
    }
    /* DOOM section special styles * /
    .doom-section h2, .doom-section .doom-title, .doom-section .doom-imp {
        color:  # FF1744 !important;
        text-shadow: 0 0 8px rgba(255, 23, 68, 0.53), 0 0 2px  # 000;
        letter-spacing: 0.03em;
    }
    .doom-section .info-block-item, .doom-section ul.styled-list li {
        color:  # FF8A80;
        background: none !important;
    }
    .doom-section .doom-imp {
        font-weight: bold;
        color:  # FF5252 !important;
    }
    .tip-accent {
        color:  # FFD166;
        font-weight: bold;
    }
    .blue-accent {
        color:  # 4FC3F7;
        font-weight: bold;
    }
    .green-accent {
        color:  # 7ED957;
        font-weight: bold;
    }
    .purple-accent {
        color:  # A259F7;
        font-weight: bold;
    }
    .pink-accent {
        color:  # FF6EC7;
        font-weight: bold;
    }

    @media(max-width: 700px) {
        .container {
            padding: 10px 2vw 10px 2vw;
        }
        h1 {font-size: 1.3em;}
        h2 {font-size: 1.1em;}
        h3 {font-size: 1em;}
    }
</style >
</head >
<body >
<div class = "container" >
<h1 > 🚀 Akai Fire PixelForge - App Guide(v1.5.0) 🚀 < /h1 >

<p > Welcome to < b class = "blue-accent" > Akai Fire PixelForge < /b > ! This guide will help you unlock the creative power and new gaming dimension of your Akai Fire controller. < /p >

<div class = "card" >
<h2 > Core Features At a Glance < /h2 >
<ul class = "styled-list" >
    <li > 🎨 < b class = "green-accent" > Primary/Secondary Pad Painting: < /b > Paint with two different colors using left-click and right-click. < /li >
    <li > 🎵 < b class = "pink-accent" > NEW! Audio Visualizer: < /b > A powerful, real-time audio-reactive light show on your pads with multiple modes. < /li >
    <li > 🎬 < b class = "blue-accent" > Animator Studio: < /b > A powerful frame-by-frame sequencer for designing intricate RGB pad animations. < /li >
    <li > 💡 < b class = "tip-accent" > Screen Sampler(Ambient Mode): < /b > Dynamically mirror colors from your screen onto the pads and record the output. < /li >
    <li > ⚙️ < b > Advanced OLED Screen Customization: < /b > Create custom Text, Image, and GIF items for the OLED. < /li >
    <li > 👹 < b class = "doom-title" > LazyDOOM Game Mode: < /b > Play a retro first-person shooter directly on your Akai Fire's OLED!</li>
    <li>🎛️ <b>Hardware Integration:</b> Contextual knob controls and button mapping for seamless interaction.</li>
</ul>
</div>

<div class="card">
<h2>🎨 Pad Painting & Animator Studio 🎬</h2>
<h3 class="blue-accent">Direct Pad Painting</h3>
<p>The Color Picker now features a <b class="green-accent">Primary/Secondary</b> color system. Left-click (or drag) on the main grid paints with the Primary Color. Right-click (or drag) paints with the Secondary Color. By default, the secondary color is black, acting as an eraser. Use the new color well in the picker to swap colors or set a new secondary color. Use the <code>I</code> key to toggle the Eyedropper tool and pick colors from the grid.</p>
<h3>Static Pad Layouts</h3>
<p>Design full static color images for your pads. Save your creations as presets and load them instantly. Great for setting up default states or visual templates.</p>
<h3 class="blue-accent">Animator Studio</h3>
<ul class="styled-list">
    <li><b>Visual Timeline:</b> Easily manage your animation frames. Select, multi-select, and reorder.</li>
    <li><b>Frame Operations:</b> Add blank frames, add snapshots of the current grid, Delete, Duplicate, Copy (<code>Ctrl</code>+<code>C</code>), Cut (<code>Ctrl</code>+<code>X</code>), and Paste (<code>Ctrl</code>+<code>V</code>) frames.</li>
    <li><b>Smooth Workflow:</b> Undo (<code>Ctrl</code>+<code>Z</code>) and Redo (<code>Ctrl</code>+Y) support for paint strokes and most frame operations.</li>
    <li><b>Playback Control:</b> Adjust animation speed (FPS) and looping behavior. Play/pause with the <code>Spacebar</code>.</li>
    <li><b>Sequence Management:</b> Save, load, create new (<code>Ctrl</code>+<code>N</code>), and delete animation sequence files.</li>
</ul>
</div>

<div class="card">
<h2 class="pink-accent">🎵 NEW! Audio Visualizer ✨</h2>
<p class="info-block-item">Unleash your music visually! The Audio Visualizer listens to your computer's sound output and transforms it into dynamic, colorful light shows on your Akai Fire's pads. Access the controls in the right-hand panel.</p>
<ul class="styled-list">
    <li><b>Audio Source:</b> Select the sound device you want to visualize. This is typically your main speakers or headphones, often labeled as a "Loopback" or "Stereo Mix" device.</li>
    <li><b>Enable/Disable:</b> Use the main toggle button to start and stop the visualizer.</li>
    <li>🌟 <b class="tip-accent">Live Settings:</b> Click the <code>Setup...</code> button to open the detailed settings window. You can tweak all of these settings in <b class="tip-accent">real-time</b> while the visualizer is running!</li>
</ul>
<h3 class="purple-accent">Visualization Modes:</h3>
<ul class="styled-list">
    <li><b>📊 Classic Spectrum Bars:</b> The iconic look of a graphic equalizer. 8 vertical bars dance to different frequency ranges. In the Setup window, you can customize the color of each bar, change the sensitivity and smoothness, and even save your favorite color schemes as palettes!</li>
    <li><b>🌊 Pulse Wave:</b> A smooth, sweeping bar of color that travels across the grid. The brightness of the pulse reacts to the overall loudness of the audio. In the Setup window, you can change the pulse color, its travel speed, and how strongly its brightness reacts to sound.</li>
    <li><b>🎶 Dual VU + Spectrum:</b> The ultimate tool for the audiophile. This mode features two classic VU meters on the sides of the grid that show the overall volume. In the center, a 5-band mini-spectrum provides a detailed look at the frequencies. The Setup window is extensive, allowing you to customize colors and responsiveness for all elements independently and save the entire configuration as a "scheme."</li>
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
            <li>Fine-tune the visual output with real-time sliders for <b>Brightness, Saturation, Contrast,</b> and <b>Hue Shift</b> of the sampled colors.</li>
        </ul>
    </li>
    <li>🌟 <b class="tip-accent">Record Sampler Output:</b> This is where the magic happens! Click "Record" to capture the dynamic visuals from the sampler directly into a new animation sequence in the Animator Studio. This is perfect for creating unique animations from videos, music visualizers, or any on-screen content.</li>
</ul>
<p class="note"><b>Power User Tip:</b> Websites like <a href="https://giphy.com" target="_blank">GIPHY.com</a> are a goldmine for sampler content. Play a GIF (abstract colors are best), position the sampler region over it, and record the output to create amazing, complex pad animations with ease!</p>
</div>

<div class="card">
<h2>⚙️ Advanced OLED Screen Customization 🖼️</h2>
<p class="info-block-item"><b>Active Graphic System:</b> Designate any of your custom creations (text, image, or animation) to be the persistent default display on your Fire's OLED.</p>
<p class="info-block-item"><b>Manual Play/Pause:</b> A clickable icon next to the UI's OLED mirror allows you to manually pause or resume your current Active Graphic.</p>
<p class="info-block-item"><b>Content Library:</b> Create "Text Items" and "Image & GIF Animation Items" with a rich processing pipeline including multiple dithering options, gamma correction, and sharpening.</p>
</div>

<div class="card doom-section">
<h2>👹 <span class="doom-title">LazyDOOM</span> - Retro FPS on Your Fire! 🎮</h2>
<p class="info-block-item"><b>How to Launch:</b> Click the "<span class="doom-imp">👹 LazyDOOM</span>" button in the right-hand panel.</p>
<p class="info-block-item"><b>Pre-Game Instructions:</b> An <b>Instructions Dialog</b> will appear. <b>Please read this carefully!</b> It explains all game controls, objectives, and tips.</p>
<h3 class="doom-title">Gameplay Overview:</h3>
<ul class="styled-list">
    <li class="doom-imp">Navigate unique, procedurally generated levels and hunt down Imp enemies.</li>
    <li class="doom-imp">Manage your Health (HP), shown on the OLED and on a dedicated row of pads.</li>
    <li class="doom-imp">Defeat all Imps on the level to win!</li>
</ul>
</div>

<div class="card">
<h2>🎛️ Hardware Controls Explained (PixelForge Modes)</h2>
<p>Your Akai Fire controller's physical knobs and buttons have special functions. Hover over them to get info on anything that isnt labeled. The OLED will briefly show their current function and value when a top knob is turned. (Most gui elements are for show, except the graphics switching buttons [Pattern up and down])</p>
<h3 class="blue-accent">Global Controls & Knobs (Top Row):</h3>
<p class="info-block-item">A new <b class="green-accent">"Global Controls"</b> panel on the right side of the window contains a dedicated <b class="green-accent">Brightness Slider</b>. This slider and physical <b>Knob 1</b> are always synced.</p>
<ul class="styled-list">
    <li><b>Default/Editing Mode</b> (Sampler/Visualizer OFF & Animator NOT Playing):
        <ul class="styled-list">
            <li><b>Knob 1 (Volume):</b> 🌟 Adjusts Global Pad Brightness for all non-sampler/visualizer pad visuals.</li>
            <li><em>Other knobs are unassigned unless the animator is playing.</em></li>
        </ul>
    </li>
    <li><b>Audio Visualizer ON:</b>
        <ul class="styled-list">
            <li>Knob control is disabled to prevent conflicts. Use the "Setup..." dialog for real-time adjustments.</li>
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
    <li><b>Animator PLAYING (Sampler/Visualizer are OFF):</b>
        <ul class="styled-list">
            <li><b>Knob 4 (Resonance):</b> ⏱️ Adjusts active Animation Playback Speed (FPS) in real-time.</li>
        </ul>
    </li>
</ul>
<h3>Physical Buttons:</h3>
<ul class="styled-list">
    <li><b>PERFORM / BROWSER Button:</b> 💡 Toggles the Screen Sampler ON/OFF.</li>
    <li><b>DRUM Button:</b> 🖥️ Cycles through available computer monitors for the Screen Sampler (when Sampler is ON).</li>
    <li><b>GRID LEFT / GRID RIGHT Buttons:</b> ◀️▶️ Navigates between item categories (e.g., "Animator Sequences" vs. "Static Layouts").</li>
    <li><b>SELECT Knob (Turn):</b> 📜 Scrolls through items in the focused list.</li>
    <li><b>SELECT Knob (Press):</b> ✔️ Loads/Applies the highlighted item.</li>
    <li><b>PLAY (Physical Button):</b> ▶️ Plays/Pauses the current animation.</li>
    <li><b>STOP (Physical Button):</b> ⏹️ Stops animation playback.</li>
    <li><b>PATTERN UP / PATTERN DOWN Buttons:</b> 🔼🔽 Cycle through your active OLED graphics.</li>
</ul>
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
