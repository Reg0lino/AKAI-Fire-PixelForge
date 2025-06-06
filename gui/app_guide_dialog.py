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
    html {
        background-color: #181818; 
        color: #B3B3B3; 
    }
    body {
        font-family: "Segoe UI", Arial, sans-serif;
        background-color: #181818; 
        color: #B3B3B3; 
        font-size: 10pt;
        line-height: 1.0;  
        margin: 8px;          
        padding: 10px 15px; 
    }

    /* Aggressive Reset for common block elements */
    h1, h2, h3, p, ul, li, div {
        background-color: transparent !important; 
        margin: 0;
        padding: 0;
    }

    /* Re-apply specific styles and spacing */
    h1 {
        color: #E0E0E0;
        text-align: center;
        font-size: 16pt;
        margin-top: 5px;
        margin-bottom: 8px; 
        padding: 2px 0; 
    }
    h2 {
        font-size: 13pt;
        border-bottom: 1px solid #404040;
        padding-bottom: 2px;
        margin-top: 18px;    
        margin-bottom: 8px;  
        line-height: 1.0;    
    }
    h3 { 
        font-size: 11pt;
        color: #C8C8C8;
        margin-top: 12px;    
        margin-bottom: 5px;  
        line-height: 1.3;    
    }
    /* Styling for lists that REMAIN lists (e.g., Core Features, Shortcuts) */
    ul.styled-list { /* Added a class to target only specific ULs if needed */
        list-style-type: disc;
        padding-left: 25px;   
        margin-top: 3px;     
        margin-bottom: 5px;  
    }
    ul.styled-list ul.styled-list { /* Nested styled lists */
        margin-top: 2px;
        margin-bottom: 3px;
        padding-left: 20px;   
    }
    ul.styled-list li {
        margin-bottom: 2px;   
        line-height: 1.0;   
    }
    /* Default paragraph styling */
    p {
        margin-top: 3px;      
        margin-bottom: 3px;  
    }
    /* Specific styling for paragraphs used INSTEAD of lists for tips/controls */
    p.info-block-item {
        margin-top: 1px;
        margin-bottom: 3px; /* Tighter spacing for these faux-list items */
        padding-left: 20px; /* Indent them slightly like list items */
        text-indent: -4px; /* Creates a hanging indent for a bullet-like feel */
    }
    p.info-block-item::before {
        content: "▪ "; /* Small square bullet, or "• ", or "– " */
        color: #888888; /* Bullet color */
        padding-right: 4px;
    }


    strong, b { 
        color: #D8D8D8; 
    }
    code { 
        background-color: #2A2A2A;
        padding: 1px 4px;    
        border-radius: 3px;
        font-family: "Consolas", "Courier New", monospace;
        color: #C5C5C5; 
    }
    a {
        color: #4FC3F7; 
        text-decoration: none;
    }
    a:hover {
        text-decoration: underline;
        color: #81D4FA; 
    }
    .emoji { 
        /* font-size: 1.1em; */ 
    }
    .note {
        background-color: #222222;
        border-left: 3px solid #FFCA28; 
        padding: 8px 12px;  
        margin: 8px 0;      
        border-radius: 3px;
        font-size: 9.5pt;
        line-height: 1.0;   
    }

    /* ScrollBar Styling - Dark, Thin, No Arrows */
    QScrollBar:vertical {
        border: none; 
        background: #222222; 
        width: 8px;          
        margin: 0px 0px 0px 0px;
    }
    QScrollBar::handle:vertical {
        background: #4A4A4A;    
        min-height: 25px;       
        border-radius: 4px;     
    }
    QScrollBar::handle:vertical:hover {
        background: #5A5A5A;    
    }
    QScrollBar::handle:vertical:pressed {
        background: #383838;    
    }
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
        border: none;
        background: none;
        height: 0px;
        width: 0px;
        subcontrol-position: top; 
        subcontrol-origin: margin;
    }
    QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
        background: none; 
    }
    QScrollBar:horizontal {
        border: none;
        background: #222222;
        height: 8px;         
        margin: 0px 0px 0px 0px;
    }
    QScrollBar::handle:horizontal {
        background: #4A4A4A;
        min-width: 25px;
        border-radius: 4px;
    }
    QScrollBar::handle:horizontal:hover {
        background: #5A5A5A;
    }
    QScrollBar::handle:horizontal:pressed {
        background: #383838;
    }
    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
        border: none;
        background: none;
        width: 0px;
        height: 0px;
        subcontrol-position: left; 
        subcontrol-origin: margin;
    }
    QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {
        background: none;
    }
</style>
</head>
<body>

<h1>🚀 Akai Fire PixelForge - App Guide (v1.0.0) 🚀</h1>

<p>Welcome to Akai Fire PixelForge! This guide will help you unlock the creative power and new gaming dimension of your Akai Fire controller.</p>

<h2 style="color: #66BB6A;">Core Features At a Glance</h2>
<p>PixelForge transforms your Akai Fire into a versatile tool for visual expression and retro gaming:</p>
<ul class="styled-list">
    <li>🎨 <strong>Direct Pad Painting:</strong> Instantly paint colors onto the 4x16 pad grid.</li>
    <li>🖼️ <strong>Static Pad Layouts:</strong> Design, save, and load full-color static images for your pads.</li>
    <li>🎬 <strong>Animator Studio:</strong> A powerful frame-by-frame sequencer for designing intricate RGB pad animations.</li>
    <li>💡 <strong style="color: #FFCA28;">Screen Sampler (Ambient Mode):</strong> Dynamically mirror colors from your screen onto the pads and record the output.</li>
    <li>⚙️ <strong>Advanced OLED Screen Customization:</strong> Create custom Text, Image, and GIF items with a rich processing pipeline including multiple dithering options.</li>
    <li>👹 <strong style="color: #EF5350;">NEW! LazyDOOM Game Mode:</strong> Play a retro first-person shooter directly on your Akai Fire's OLED!</li>
    <li>🎛️ <strong>Hardware Integration:</strong> Contextual knob controls and button mapping for seamless interaction.</li>
</ul>

<h2 style="color: #FF7043;">🎨 Pad Painting & Animator Studio 🎬</h2>
<h3>Direct Pad Painting</h3>
<p>Select a color from the robust Color Picker (includes SV map, Hue slider, RGB/Hex inputs, and savable "My Colors" swatches). Then, simply left-click (or drag) on the main 4x16 GUI grid to paint pads. Right-click (or drag) erases pads to black. Use the <code>I</code> key to toggle the Eyedropper tool and pick colors directly from the grid.</p>
<h3>Static Pad Layouts</h3>
<p>Design full static color images for your pads. Save your creations as presets and load them instantly. Great for setting up default states or visual templates.</p>
<h3>Animator Studio</h3>
<p>Unleash your creativity with frame-by-frame RGB animations:</p>
<ul class="styled-list">
    <li><strong>Visual Timeline:</strong> Easily manage your animation frames. Select, multi-select, and reorder.</li>
    <li><strong>Frame Operations:</strong> Add blank frames, add snapshots of the current grid, Delete, Duplicate, Copy (<code>Ctrl</code>+<code>C</code>), Cut (<code>Ctrl</code>+<code>X</code>), and Paste (<code>Ctrl</code>+<code>V</code>) frames.</li>
    <li><strong>Smooth Workflow:</strong> Undo (<code>Ctrl</code>+<code>Z</code>) and Redo (<code>Ctrl</code>+Y) support for paint strokes and most frame operations.</li>
    <li><strong>Playback Control:</strong> Adjust animation speed (FPS) and looping behavior. Play/pause with the <code>Spacebar</code>.</li>
    <li><strong>Sequence Management:</strong> Save, load, create new (<code>Ctrl</code>+<code>N</code>), and delete animation sequence files (stored in your Documents).</li>
</ul>

<h2 style="color: #FFEE58;">💡 Screen Sampler (Ambient Mode) ✨</h2>
<p>Transform your Akai Fire pads into a real-time reflection of your desktop activity!</p>
<ul class="styled-list">
    <li><strong>Activation:</strong> Toggle using the "Toggle Ambient Sampling" button in the UI or the <code>PERFORM</code>/<code>BROWSER</code> buttons on your Akai Fire.</li>
    <li><strong>Configuration:</strong> Click "Configure Region & Adjustments."
        <ul class="styled-list">
            <li>Select the target monitor to sample from (cycle with the <code>DRUM</code> button on the Fire).</li>
            <li>Visually drag and resize the selection box on your screen to define the capture area.</li>
            <li>Fine-tune the visual output with real-time sliders for <strong>Brightness, Saturation, Contrast,</strong> and <strong>Hue Shift</strong> of the sampled colors. These settings are saved per monitor.</li>
        </ul>
    </li>
    <li>🌟 <strong>Record Sampler Output:</strong> This is where the magic happens! Click "Record" to capture the dynamic visuals from the sampler directly into a new animation sequence in the Animator Studio. This is perfect for creating unique animations from videos, music visualizers, or any on-screen content.</li>
</ul>

<h2 style="color: #26C6DA;">⚙️ Advanced OLED Screen Customization 🖼️</h2>
<p>Take full command of your Akai Fire's 128x64 monochrome OLED display! Access the "OLED Active Graphic Manager" by clicking the on-screen OLED mirror in the application's top strip.</p>
<p class="info-block-item"><strong>Active Graphic System:</strong> Designate any of your custom creations (text, image, or animation) to be the persistent default display on your Fire's OLED after the initial startup visual. Use the "Save & Apply" button for quick changes.</p>
<p class="info-block-item"><strong>Manual Play/Pause:</strong> A clickable icon next to the UI's OLED mirror allows you to manually pause or resume your current Active Graphic.</p>
<h3>Content Library:</h3>
<p class="info-block-item"><strong>Text Items:</strong> Design scrolling or static text. Choose from available system fonts, set pixel-perfect font sizes, and define alignment (for static text) or scrolling parameters (speed override, end pauses).</p>
<p class="info-block-item"><strong>Image & GIF Animation Items:</strong> Import your favorite static images (PNG, JPG, etc.) or animated GIFs. PixelForge v1.0.0 introduces an <strong>Advanced Processing Pipeline</strong> for unparalleled control:</p>
<div style="padding-left: 30px;"> <!-- Indent further for sub-details -->
    <p class="info-block-item"><strong>Pre-Dithering Adjustments:</strong> Fine-tune your source image <em>before</em> 1-bit conversion using sliders for Brightness, Contrast, <strong>Gamma Correction</strong> (for mid-tone balance), <strong>Sharpening</strong> (to enhance details), and **Pre-Dither Blur** (to soften images for smoother dithering).</p>
    <p class="info-block-item"><strong>Expanded Dithering Arsenal:</strong> Choose from a wider range of algorithms: Classics like Floyd-Steinberg, Simple Threshold (adjustable), AND New Additions like **Atkinson Dither** (sharper, high-contrast), **Ordered Dithering** (Bayer 2x2 for retro blockiness, Bayer 4x4, and Bayer 8x8 for finer patterns).</p>
    <p class="info-block-item"><strong>Variable Dither Strength:</strong> For error-diffusion algorithms (Floyd-Steinberg, Atkinson), a slider lets you blend between a simple threshold (0% strength) and the full dithering effect (100%).</p>
    <p class="info-block-item"><strong>Noise Injection:</strong> Add stylistic "Pre-Dither" (subtle) or "Post-Dither" (grainy) noise with adjustable intensity.</p>
    <p class="info-block-item">Standard options like Resize Modes (Stretch, Fit/Pad, Crop) and Color Inversion are also available.</p>
</div>
<p class="info-block-item"><strong>System Messages:</strong> Clear, temporary messages using a retro "TomThumb" font provide feedback for application actions (like knob turns or sampler status changes), overlaying your Active Graphic and then gracefully reverting.</p>
<p class="note"><strong>Tip for OLEDs:</strong> Experiment! Different combinations of pre-dithering adjustments and dithering algorithms can produce vastly different artistic results on the monochrome display. Short, seamlessly looping GIFs often work best for animations.</p>


<h2 style="color: #EF5350;">👹 NEW! LazyDOOM - Retro FPS on Your Fire! 🎮</h2>
<p>PixelForge v1.0.0 now includes **LazyDOOM**, a custom-built retro first-person shooter experience playable directly on your Akai Fire controller!</p>
<p class="info-block-item"><strong>How to Launch:</strong> Find and click the "👹 LazyDOOM" button located in the main application's right-hand panel.</p>
<p class="info-block-item"><strong>Pre-Game Instructions:</strong> Before the action starts, an **Instructions Dialog** will appear. <strong>Please read this carefully!</strong> It explains all game controls (both pad and keyboard), gameplay objectives, and tips for survival.</p>
<h3>Gameplay Overview:</h3>
<p class="info-block-item">Navigate unique, procedurally generated maze-like levels displayed on the 128x64 OLED screen.</p>
<p class="info-block-item">Hunt down and eliminate "Imp" enemies using your trusty hitscan weapon.</p>
<p class="info-block-item">Manage your Health (HP), which is shown on the OLED HUD and also visually represented on a dedicated row of pads on your Akai Fire.</p>
<p class="info-block-item">Defeat all Imps on the current level to emerge victorious!</p>
<h3>Controls & Feedback:</h3>
<p class="info-block-item"><strong>Pad-Powered Action:</strong> All primary game functions (movement, strafing, turning, running, shooting) are mapped to the Akai Fire's pads.</p>
<p class="info-block-item"><strong>Keyboard Support:</strong> Standard FPS keyboard controls (e.g., <code>WASD</code> for movement, <code>F</code> to shoot, <code>Shift</code> to run) are also active during gameplay.</p>
<p class="info-block-item"><strong>Visual Immersion:</strong> Get real-time feedback with on-OLED screen glitches when you take damage, and dynamic RGB pad lighting for health status and game events.</p>
<p class="info-block-item"><strong>Game Over & Restart:</strong> If you fall in battle, the "SHOOT" pad will blink – press it to jump right back in and try again!</p>
<h3>Choose Your Challenge:</h3>
<p class="info-block-item">Select from three difficulty levels (Normal, Hard, Nightmare!) when launching LazyDOOM. Harder modes feature more aggressive and/or numerous enemies.</p>
<h3>Dedicated Game Mode:</h3>
<p class="info-block-item">While LazyDOOM is active, other PixelForge features (Animator, Sampler, etc.) are temporarily paused to ensure optimal game performance. Exiting LazyDOOM smoothly restores your previous PixelForge setup.</p>

<h2 style="color: #42A5F5;">🎛️ Hardware Controls Explained (PixelForge Modes)</h2>
<p>Your Akai Fire controller's knobs and buttons have special functions within PixelForge's main creative modes (Animator, Sampler, Static Layouts). The OLED will briefly show their current function when a top knob is turned.</p>
<h3>Knobs (Top Row):</h3>
<p>These are context-sensitive!</p>
<p class="info-block-item"><strong>Default/Editing Mode</strong> (Screen Sampler OFF & Animator NOT Playing):</p>
<div style="padding-left: 30px;">
    <p class="info-block-item"><strong>Knob 1 (Volume):</strong> 🌟 Adjusts Global Pad Brightness for all non-sampler pad visuals.</p>
    <p class="info-block-item"><strong>Knob 4 (Resonance):</strong> ⏱️ Adjusts the current Animator Sequence's properties for playback Speed (FPS/delay).</p>
    <p class="info-block-item"><em>Knobs 2 (Pan) & 3 (Filter) are currently unassigned in this mode.</em></p>
</div>
<p class="info-block-item"><strong>Screen Sampler ON:</strong></p>
<div style="padding-left: 30px;">
    <p class="info-block-item"><strong>Knob 1 (Volume):</strong> 💡 Sampler Output Brightness</p>
    <p class="info-block-item"><strong>Knob 2 (Pan):</strong> 🌈 Sampler Output Saturation</p>
    <p class="info-block-item"><strong>Knob 3 (Filter):</strong> 🎚️ Sampler Output Contrast</p>
    <p class="info-block-item"><strong>Knob 4 (Resonance):</strong> 🎨 Sampler Output Hue Shift</p>
</div>
<p class="info-block-item"><strong>Animator PLAYING (Screen Sampler is automatically OFF):</strong></p>
<div style="padding-left: 30px;">
    <p class="info-block-item"><strong>Knob 4 (Resonance):</strong> ⏱️ Adjusts active Animation Playback Speed (FPS) in real-time (temporary change for current playback).</p>
    <p class="info-block-item"><em>Knobs 1-3 are inactive or control their default functions if applicable and not overridden by playback.</em></p>
</div>

<h3>Buttons:</h3>
<p class="info-block-item"><strong>PERFORM / BROWSER Button:</strong> 💡 Toggles the Screen Sampler ON/OFF.</p>
<p class="info-block-item"><strong>DRUM Button:</strong> 🖥️ Cycles through available computer monitors for the Screen Sampler (when Sampler is ON).</p>
<p class="info-block-item"><strong>GRID LEFT / GRID RIGHT Buttons:</strong> ◀️▶️ Navigates between item categories in the right panel (e.g., "Animator Sequences" list vs. "Static Pad Layouts" list).</p>
<p class="info-block-item"><strong>SELECT Knob (Turn):</strong> 📜 Scrolls through items within the currently focused category's list. The OLED will briefly display the cued item name.</p>
<p class="info-block-item"><strong>SELECT Knob (Press):</strong> ✔️ Loads/Applies the currently highlighted item from the focused list.</p>
<p class="info-block-item"><strong>PLAY (Physical Button):</strong> ▶️ Plays/Pauses the current animation in the Animator Studio.</p>
<p class="info-block-item"><strong>STOP (Physical Button):</strong> ⏹️ Stops animation playback in Animator Studio.</p>
<p class="info-block-item"><strong>PATTERN UP / PATTERN DOWN Buttons:</strong> (🚧 Future Feature: Planned for OLED item navigation.)</p>

<h2 style="color: #AB47BC;">⌨️ Keyboard Shortcuts (Hotkeys - PixelForge Modes)</h2>
<h3>Animator Studio:</h3>
<ul class="styled-list">
    <li><strong>Undo:</strong> <code>Ctrl</code> + <code>Z</code></li>
    <li><strong>Redo:</strong> <code>Ctrl</code> + <code>Y</code></li>
    <li><strong>Copy Frame(s):</strong> <code>Ctrl</code> + <code>C</code></li>
    <li><strong>Cut Frame(s):</strong> <code>Ctrl</code> + <code>X</code></li>
    <li><strong>Paste Frame(s):</strong> <code>Ctrl</code> + <code>V</code></li>
    <li><strong>Duplicate Frame(s):</strong> <code>Ctrl</code> + <code>D</code></li>
    <li><strong>Delete Frame(s):</strong> <code>Delete</code></li>
    <li><strong>Add New Blank Frame:</strong> <code>Ctrl</code> + <code>Shift</code> + <code>B</code></li>
    <li><strong>Select All Frames:</strong> <code>Ctrl</code> + <code>A</code></li>
    <li><strong>Play/Pause Animation:</strong> <code>Spacebar</code></li>
    <li><strong>New Sequence:</strong> <code>Ctrl</code> + <code>N</code></li>
    <li><strong>Save Sequence As...:</strong> <code>Ctrl</code> + <code>Shift</code> + <code>S</code></li>
</ul>
<h3>Pad Grid / Painting Mode:</h3>
<p class="info-block-item"><strong>Toggle Eyedropper Mode:</strong> <code>I</code> (Press 'I', click pad to pick color. Mode deactivates after pick.)</p>
<p class="note"><strong>LazyDOOM Mode:</strong> While LazyDOOM is active, it uses its own keyboard control scheme (e.g., <code>WASD</code> for movement, <code>F</code> to shoot, <code>Shift</code> to run). Refer to the pre-game Instructions Dialog for the complete mapping for LazyDOOM.</p>


<h2 style="color: #FFCA28;">🌟 Super User Tips & Tricks 🌟</h2>
<h3>Master the Sampler for Animations:</h3>
<p class="info-block-item"><strong>Record Everything:</strong> Music visualizers, movie scenes, abstract art videos, even other pixel art apps!</p>
<p class="info-block-item"><strong>GIPHY & Beyond:</strong> Short video loops are goldmines. Play full screen, sample, and record!</p>
<p class="info-block-item"><strong>Sampler Adjustments are Key:</strong> Tweak Brightness, Saturation, Contrast, Hue *before* recording for unique styles.</p>
<h3>Animator Workflow:</h3>
<p class="info-block-item"><strong>Start Simple:</strong> Keyframes first, then duplicate/modify. "Duplicate" is your friend!</p>
<p class="info-block-item"><strong>Experiment with FPS:</strong> Drastically changes animation feel. Remember Knob 4!</p>
<h3>OLED Creativity Unleashed:</h3>
<p class="info-block-item"><strong>Font Choice:</strong> Experiment with system fonts and sizes. Pixel-style fonts can look great.</p>
<p class="info-block-item"><strong>Dithering Deep Dive:</strong> For pixel art, 'Simple Threshold' or 'Ordered Dither (Bayer 2x2)' can give crisp results. For photos/gradients, experiment with 'Floyd-Steinberg' or 'Atkinson' and adjust the 'Dither Strength' slider. Use 'Pre-Dither Blur' (gently!) on photos for smoother tones. 'Sharpen' can help preserve details in graphic logos.</p>
<p class="info-block-item"><strong>Short & Sweet Loops:</strong> For animated OLED graphics, short, seamlessly looping GIFs often work best.</p>
<h3>LazyDOOM Tactics:</h3>
<p class="info-block-item">Strafing is your best friend! Use it to dodge projectiles and peek around corners.</p>
<p class="info-block-item">Don't forget to use the Run button in open areas or when retreating.</p>
<h3>General Tips:</h3>
<p class="info-block-item"><strong>Color Picker Power:</strong> Save favorites to "My Colors." Use Eyedropper (<code>I</code> key) on the grid.</p>
<p class="info-block-item"><strong>Hardware Knob Context:</strong> Watch the OLED! It tells you what the top knobs are controlling.</p>
<p class="info-block-item"><strong>Backup Your Presets:</strong> Your creations are in "<code>Documents\\Akai Fire RGB Controller User Presets</code>". Backup this folder!</p>

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
