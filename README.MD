# AKAI Fire RGB Controller

## 🎛️ Overview

The AKAI Fire RGB Controller is a Python desktop application designed to provide comprehensive control over the RGB LEDs of an Akai Fire MIDI controller. It allows users to create static color layouts, design frame-by-frame animations, and utilize a screen sampler to reflect desktop colors onto the device pads dynamically. The application features a modern, dark-themed, and intuitive user interface built with PyQt6.

This project aims to unlock the full visual potential of the Akai Fire, transforming it from just a MIDI controller into a versatile lighting instrument and visual feedback tool.

## ✨ Features

*   **Direct Pad/Button Painting:** Easily paint individual pads with a chosen color.
*   **Sophisticated Color Picker:** Includes SV (Saturation/Value) map, Hue slider, RGB/Hex inputs, and "My Colors" swatches for saving favorite colors.
*   **Static Color Layouts:** Create, save, load, and manage static color presets for the entire 4x16 pad grid.
*   **Frame-by-Frame Animation Sequencer:**
    *   Visual timeline for arranging frames.
    *   Add, delete, duplicate, and edit frames.
    *   Control animation speed (FPS) and looping.
    *   Save and load animation sequences.
    *   Undo/Redo functionality for frame edits.
*   **Interactive Screen Sampler:**
    *   Visually select a region on any connected monitor.
    *   Resizable and snappable selection box for precise sampling.
    *   Live preview of the sampled region within the configuration dialog.
    *   Adjust Saturation, Contrast, Brightness, and Hue Shift for the sampled colors.
    *   Colors from the selected screen region are reflected onto the Akai Fire pads (currently as a 4x16 grid, where each pad gets color from its corresponding sub-region of the sampler view).
*   **Sampler Recording (New!):**
    *   Record the output of the screen sampler over a sequence of frames (up to 200).
    *   Automatically save the recording as a new animation sequence (prefixed with `[Sampler]`).
    *   Recorded sequences can be played, edited, and re-saved like any other animation.
*   **MIDI Communication:** Connects to the Akai Fire via MIDI SysEx and CC messages.
*   **Modern UI:** Dark-themed and user-friendly interface using PyQt6 and QSS styling.
*   **Persistent User Settings:**
    *   Color picker swatches are saved between sessions.
    *   Screen sampler configurations (region, adjustments) are saved per monitor.

## 🛠️ Technology Stack

*   **Language:** Python 3
*   **GUI Framework:** PyQt6
*   **MIDI Communication:** `python-rtmidi`
*   **Screen Capture:** `mss`
*   **Image Manipulation:** `Pillow (PIL)`, `numpy`
*   **Configuration:** JSON
*   **Styling:** QSS
*   **User Directory Management:** `appdirs`

## ⚙️ Setup & Installation

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/Reg0lino/AKAI-Fire-RGB-Controller.git
    cd AKAI-Fire-RGB-Controller
    ```
2.  **Create a virtual environment (recommended):**
    ```bash
    python -m venv .venv
    # Activate it:
    # Windows:
    # .\.venv\Scripts\activate
    # macOS/Linux:
    # source .venv/bin/activate
    ```
3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
4.  **Connect your Akai Fire controller.**
5.  **Run the application:**
    ```bash
    python fire_control_app.py
    ```

## 📂 Project Structure (Key Files)

AKAI_Fire_RGB_Controller/
├── animator/ # Animator-specific logic & UI
├── features/ # Screen sampler core & thread
├── gui/ # Main GUI components (MainWindow, dialogs, managers)
├── hardware/ # Akai Fire MIDI communication
├── presets/ # Default/prefab static layouts and animation sequences
│ ├── sequences/
│ │ ├── prefab/
│ │ ├── sampler_recordings/ (Auto-saved sampler recordings)
│ │ └── user/
│ └── static/
│ ├── prefab/
│ └── user/
├── resources/ # Icons and stylesheets
├── user_settings/ # (Created locally during dev for user configs - IGNORED BY GIT)
├── fire_control_app.py # Main application entry point
├── README.md
├── LICENSE
├── requirements.txt
└── .gitignore
*(User configuration files like `sampler_user_prefs.json` and `fire_controller_config.json` will be saved in a platform-specific user application data directory when running the packaged application, or in `user_settings/` during development.)*

## 🎮 Usage

1.  Launch the application (`python fire_control_app.py`).
2.  Select the "AKAI Fire" MIDI output port from the dropdown in the "MIDI Connection" section and click "Connect".
3.  Once connected, the controls will become active.
4.  **Color Picker:** Select colors using the visual pickers or numeric input. Click "➕ Add" in "My Colors" to save the current color to a swatch. Right-click swatches to manage them.
5.  **Static Pad Layouts:** Select a prefab or user layout and click "Apply Layout". To save the current grid as a new static layout, click "Save Current As...".
6.  **Animator Sequencer:**
    *   Use the "Frame Editing" buttons to add (snapshot/blank), duplicate, or delete frames.
    *   Click on a frame in the timeline to select it for editing. Paint on the main 4x16 pad grid to set colors for the selected frame.
    *   Use "Frame Navigation" to move between frames.
    *   Use "Playback" controls to play, pause, or stop the animation. Adjust speed with the slider.
    *   Save your work using "💾 Save Seq As..." under "Animator Sequences". Load existing sequences using the dropdown and "📲 Load Selected".
7.  **Screen Sampler (Ambient):**
    *   Toggle "Toggle Ambient Sampling" to enable/disable.
    *   Select the "Target Monitor" for the configuration view.
    *   Click "Configure Region & Adjustments..." to open the visual sampler dialog.
    *   In the dialog, drag and resize the blue selection box on the monitor preview to define the sampling area.
    *   Adjust Saturation, Contrast, Brightness, and Hue Shift sliders. The preview on the right shows the S/C/B adjusted image. The pads will reflect the 4x16 gridded sample from this region with all adjustments.
    *   Sampler settings (region, adjustments) are saved per monitor and reloaded.
8.  **Sampler Recording:**
    *   While the Screen Sampler is active, click "🎬 Record Sample".
    *   A sequence of up to 200 frames will be captured.
    *   Click "🔴 Stop Recording" or let it auto-stop.
    *   You'll be prompted to name the new sequence, which is then automatically saved and loaded into the animator. These appear with a `[Sampler]` prefix in the sequence list.
9.  **Quick Tools:**
    *   "Paint: Black (Off)": Quickly sets the painting color to black.
    *   "Clear Device Pads": Turns all pads on the Akai Fire off and clears the current view/animator frame.

## TODO / Future Enhancements

*   More advanced animation editing tools (e.g., copy/paste multiple frames, layer effects).
*   Option for different screen sampling modes (e.g., single average color for whole grid vs. 4x16 grid).
*   MIDI input mapping for triggering sequences/layouts.
*   More prefab animations and static layouts.
*   Further UI/UX refinements for the animator timeline.
*   Executable packaging for easier distribution.

## ⚖️ License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgements

*   The developers of PyQt, Pillow, NumPy, python-rtmidi, mss, and appdirs.
*   The Akai Pro team for creating the versatile Fire controller.
*   Google Gemini 2.5 for helping me crack this finally.

---
*Developed by [REGULARREGS/Reg0lino]*