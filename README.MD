# AKAI Fire RGB Controller

## 🎛️ Overview

The AKAI Fire RGB Controller is a Python desktop application designed to provide comprehensive control over the RGB LEDs of an Akai Fire MIDI controller. It allows users to create static color layouts, design frame-by-frame animations, and utilize a screen sampler to reflect desktop colors onto the device pads dynamically. The application features a modern, dark-themed, and intuitive user interface built with PyQt6.

This project aims to unlock the full visual potential of the Akai Fire, transforming it from just a MIDI controller into a versatile lighting instrument and visual feedback tool.

## ✨ Features

*   **Direct Pad/Button Painting:** Easily paint individual pads with a chosen color.
*   **Sophisticated Color Picker:** Includes SV (Saturation/Value) map, Hue slider, RGB/Hex inputs, and "My Colors" swatches for saving favorite colors.
*   **Static Color Layouts:** Create, save, load, and manage static color presets for the entire 4x16 pad grid.
*   **Frame-by-Frame Animation Sequencer ("Animator Studio"):**
    *   Visual timeline for arranging frames (supports multi-selection).
    *   Add (snapshot/blank), delete, duplicate, copy, cut, and paste frames.
    *   Undo/Redo functionality for frame edits and sequence property changes.
    *   Control animation speed (FPS) and looping.
    *   Integrated sequence file management: Save, load, create new, and delete animation sequences (user, prefab, sampler-recorded).
*   **Interactive Screen Sampler:**
    *   Visually select a region on any connected monitor.
    *   Resizable and snappable selection box for precise sampling.
    *   Live preview of the sampled region within the configuration dialog.
    *   Adjust Saturation, Contrast, Brightness, and Hue Shift for the sampled colors.
    *   Colors from the selected screen region are reflected onto the Akai Fire pads (4x16 grid).
*   **Sampler Recording:** <<---CURRENTLY BUGGED
    *   Record the output of the screen sampler over a sequence of frames. <<---CURRENTLY BUGGED
    *   Automatically save the recording as a new animation sequence. <<---CURRENTLY BUGGED
    *   Recorded sequences can be played, edited, and re-saved. <<---CURRENTLY BUGGED
*   **MIDI Communication:** Connects to the Akai Fire via MIDI.
*   **Modern UI:** Dark-themed and user-friendly interface using PyQt6 and QSS styling.
*   **Persistent User Settings:**
    *   Color picker swatches are saved between sessions.
    *   Screen sampler configurations (region, adjustments) are saved per monitor.
*   **Global Hotkeys:** Standard shortcuts for operations like Copy, Paste, Undo, Redo, New, Save As, Duplicate, Delete frames, and Play/Pause.

## 🛠️ Technology Stack

*   **Language:** Python 3 (tested with 3.13)
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
2.  **Create a virtual environment (highly recommended):**
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
    Or, on Windows, you can create a `run_no_console.bat` file with the following content (adjust path to `.venv` if needed) to launch without a persistent command window:
    ```batch
    @echo off
    start "" ".venv\Scripts\pythonw.exe" "fire_control_app.py"
    ```

## 📂 Project Structure (Key Files)

AKAI_Fire_RGB_Controller/
├── animator/ # Animator-specific logic & UI (model, timeline, controls)
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
├── user_settings/ # (Created locally for user configs - IGNORED BY GIT)
├── fire_control_app.py # Main application entry point
├── README.md
├── LICENSE
├── requirements.txt
└── .gitignore
*(User configuration files like `sampler_user_prefs.json` and `fire_controller_config.json` will be saved in a platform-specific user application data directory when running a packaged application, or in `user_settings/` during local development.)*

## 🎮 Usage

1.  Launch the application.
2.  Select the "AKAI Fire" MIDI output port and click "Connect".
3.  **Color Picker:** Select colors. Use "My Colors" to save/manage swatches.
4.  **Static Pad Layouts:** Apply or save static grid color layouts.
5.  **Animator Studio:**
    *   **Sequence Management:** Use the "Sequence:" dropdown and Load/New/Save As.../Delete buttons to manage animation files.
    *   **Timeline & Frame Ops:** Click frames to edit. Use buttons (Add, Dup, Del, Copy, Cut, Paste) or hotkeys for frame operations.
    *   **Playback:** Control playback and speed.
6.  **Screen Sampler (Ambient):**
    *   Toggle sampling. Configure region and color adjustments in the dialog.
7.  **Sampler Recording:**
    *   While sampling, click "🎬 Record Sample" to capture frames into a new animation.
8.  **Quick Tools:**
    *   "Paint: Black (Off)": Sets paint color to black.
    *   "Clear Device Pads": Clears hardware and current GUI/frame.

## TODO / Future Enhancements

*   More advanced animation editing tools (e.g., interpolation, effects).
*   Option for different screen sampling modes (e.g., average color).
*   MIDI input mapping for triggering sequences/layouts.
*   More prefab content.
*   Executable packaging.

## ⚖️ License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgements

*   The developers of PyQt, Pillow, NumPy, python-rtmidi, mss, and appdirs.
*   The Akai Pro team.
*   AI Assistants for debugging support.

---
*Developed by Reg0lino (RegularRegs)*
---