# AKAI Fire RGB Controller

## 🎛️ Overview

The AKAI Fire RGB Controller is a Python desktop application designed to provide comprehensive control over the RGB LEDs of an Akai Fire MIDI controller. It allows users to create static color layouts, design frame-by-frame animations, and utilize a screen sampler to reflect desktop colors onto the device pads dynamically. The application features a modern, dark-themed, and intuitive user interface built with PyQt6.

This project aims to unlock the full visual potential of the Akai Fire, transforming it from just a MIDI controller into a versatile lighting instrument and visual feedback tool.

**Now available as a standalone executable for Windows! See the [Releases](https://github.com/Reg0lino/AKAI-Fire-RGB-Controller/releases/tag/release) page.**

## Animations
![Animation Creator Screenshot](https://github.com/user-attachments/assets/d428fdef-93e1-4a24-ac58-8d9c86f7651e)
## Screen Sampler
*(With monitor choosing, area selection & recording option)*
![Screen Sampling Screenshot](https://github.com/user-attachments/assets/c02538a7-1de9-4cbc-865e-4a3a7ca2b418)
![Photo of everything working](https://github.com/user-attachments/assets/f42bbf86-b30a-43b2-808d-8f6871431bb8)

## ✨ Features

*   **Direct Pad/Button Painting:** Easily paint individual pads with a chosen color using a smooth, canvas-like drag interface (left-click to paint, right-click to erase).
*   **Sophisticated Color Picker:** Includes SV (Saturation/Value) map, Hue slider, RGB/Hex inputs, and "My Colors" swatches for saving favorite colors.
*   **Static Color Layouts:** Create, save, load, and manage static color presets for the entire 4x16 pad grid.
*   **Frame-by-Frame Animation Sequencer ("Animator Studio"):**
    *   Visual timeline for arranging frames (supports multi-selection).
    *   Add (snapshot/blank), delete, duplicate, copy, cut, and paste frames.
    *   Undo/Redo functionality for frame edits and sequence property changes.
    *   Control animation speed (FPS) and looping.
    *   Integrated sequence file management: Save, load, create new, and delete animation sequences (user, prefab, sampler-recorded).
*   **Interactive Screen Sampler:**
    *   Visually select a region on any connected monitor using a resizable and snappable selection box.
    *   Dropdown to select the target monitor for sampling.
    *   Live preview of the sampled region within the configuration dialog (when sampling is active).
    *   Adjust Saturation, Contrast, Brightness, and Hue Shift for the sampled colors.
    *   Colors from the selected screen region are reflected onto the Akai Fire pads (4x16 grid).
*   **Sampler Recording:**
    *   Record the output of the screen sampler over a sequence of frames.
    *   Automatically save the recording as a new animation sequence into a dedicated "sampler_recordings" folder.
    *   Recorded sequences are listed in the Animator Studio and can be played, edited, and re-saved.
*   **MIDI Communication:** Connects to the Akai Fire via MIDI, with port selection and auto-detection of "Fire" port.
*   **Modern UI:** Dark-themed and user-friendly interface using PyQt6 and QSS styling.
*   **Persistent User Settings:**
    *   Color picker swatches are saved between sessions.
    *   Screen sampler configurations (region, adjustments per monitor) are saved between sessions.
*   **Global Hotkeys:** Standard shortcuts for operations like Copy, Paste, Undo, Redo, New, Save As, Duplicate, Delete frames, Play/Pause for animator, and Eyedropper toggle.

## 🛠️ Technology Stack

*   **Language:** Python 3 (developed with 3.13)
*   **GUI Framework:** PyQt6
*   **MIDI Communication:** `python-rtmidi` (via `mido`)
*   **Screen Capture:** `mss`
*   **Image Manipulation:** `Pillow (PIL)`
*   **Configuration:** JSON
*   **Styling:** QSS
*   **User Directory Management:** `appdirs`
*   **Packaging:** `PyInstaller`

## 🚀 Getting Started (Standalone Executable - Windows)

1.  Go to the [**Releases**](https://github.com/Reg0lino/AKAI-Fire-RGB-Controller/releases/tag/release) page of this repository.
2.  Download the latest `AkaiFireControllerApp.exe` (or debug) exe file.(Unblock if needed)
3.  Connect your Akai Fire controller.
4.  Run `AkaiFireControllerApp.exe`.

## ⚙️ Setup & Installation (From Source - For Developers)

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/reg0lino/AKAI-Fire-RGB-Controller.git
    cd AKAI-Fire-RGB-Controller
    ```
2.  **Create a virtual environment (highly recommended):**
    ```bash
    python -m venv .venv
    ```
    Activate it:
    *   Windows (Command Prompt): `.\.venv\Scripts\activate.bat`
    *   Windows (PowerShell): `.\.venv\Scripts\Activate.ps1` (You might need to run `Set-ExecutionPolicy RemoteSigned -Scope CurrentUser` in an admin PowerShell first)
    *   macOS/Linux: `source .venv/bin/activate`
3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
4.  **Connect your Akai Fire controller.**
5.  **Run the application:**
    ```bash
    python fire_control_app.py
    ```
    Or, on Windows, you can use `FIRE_RGB.bat` (included in the project root) to launch without a persistent command window during development.

## 📂 Project Structure (Key Files)

```
AKAI_Fire_RGB_Controller/
├── animator/               # Animator-specific logic & UI (model, timeline, controls)
├── features/               # Screen sampler core & thread
├── gui/                    # Main GUI components (MainWindow, dialogs, managers)
│   ├── animator_manager_widget.py
│   ├── interactive_pad_grid.py
│   ├── screen_sampler_manager.py
│   └── ... (other ui files)
├── hardware/               # Akai Fire MIDI communication
├── presets/                # Default/prefab static layouts and animation sequences
│   ├── sequences/
│   │   ├── prefab/
│   │   ├── sampler_recordings/ (Auto-saved sampler recordings)
│   │   └── user/
│   └── static/
│       ├── prefab/
│       └── user/
├── resources/              # Icons and stylesheets
├── utils.py                # Utility functions (e.g., get_resource_path)
├── user_settings/          # (Created locally for user configs during dev - IGNORED BY GIT)
├── fire_control_app.py     # Main application entry point
├── AkaiFireControllerApp.spec # PyInstaller specification file
├── README.md
├── CHANGELOG.md
├── LICENSE
├── requirements.txt
└── .gitignore
```
*(User configuration files like `sampler_user_prefs.json` and `fire_controller_config.json` will be saved in a platform-specific user application data directory when running the packaged application, or in `user_settings/` during local development if not packaged.)*

## 🎮 Usage

1.  Launch the application.
2.  Select the "AKAI Fire" MIDI output port from the "MIDI Connection" section (it should auto-select if "Fire" is in the name) and click "Connect".
3.  **Color Picker:** Select colors using the visual pickers or numeric inputs. Use "My Colors" to save/load custom swatches (right-click a swatch for options).
4.  **Static Pad Layouts:** Apply prefab layouts or save/load your own static grid color configurations.
5.  **Animator Studio:**
    *   **Sequence Management:** Use the "Sequence:" dropdown and Load/New/Save As.../Delete buttons.
    *   **Timeline & Frame Ops:** Click frames to select for editing. Use toolbar buttons (Add, Duplicate, Delete, Copy, Cut, Paste) or hotkeys.
    *   **Playback:** Control animation playback and speed (FPS) using the transport controls.
6.  **Screen Sampler (Ambient):**
    *   Click "Toggle Ambient Sampling" to activate.
    *   Click "Configure Region & Adjustments..." to open the visual configuration dialog.
    *   In the dialog, select the target monitor (if multiple), drag and resize the selection box, and adjust color parameters (Saturation, Contrast, Brightness, Hue Shift). Changes are reflected live on the Akai Fire pads if sampling is active.
    *   Settings are saved per monitor and will be reloaded.
7.  **Sampler Recording:**
    *   While ambient sampling is active, click "🎬 Record" in the "Screen Sampler" panel.
    *   Click "🔴 Stop" to finish recording. You'll be prompted to name the sequence.
    *   The recording is saved as an animation and automatically loaded into the Animator Studio.
8.  **Quick Tools:**
    *   "Set Black": Sets current painting color to black.
    *   "Clear Pads": Clears hardware pads and the current GUI/Animator frame to black.
    *   "💧 Eyedropper": Toggle to pick colors directly from the pad grid.

## 📝 TODO / Future Enhancements

*   More advanced animation editing tools (e.g., interpolation, multi-frame property editing, effects).
*   Option for different screen sampling modes (e.g., average color of entire region, dominant color).
*   MIDI input mapping for triggering sequences/layouts.
*   More prefab content (animations, static layouts).
*   Refine UI/UX for Animator Studio based on "Animator UI/UX Overhaul (Phase 1)" in Changelog.
*   Cross-platform testing and packaging (macOS, Linux).

## ⚖️ License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgements

*   The developers of PyQt, Pillow, python-rtmidi, mido, mss, and appdirs.
*   The Akai Pro team for creating the Fire controller.
*   AI Assistants for invaluable coding, debugging, and refactoring support.

---
*Developed by Reg0lino (RegularRegs)*
```
