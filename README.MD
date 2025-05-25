# AKAI Fire RGB Controller

## 🛑 Release Temporarily Down
**The standalone executable is temporarily unavailable while I address issues with file structure for saved user data and refine the packaging process. Development from source is still the primary way to run the application. Working on it!**

## 🎛️ Overview

The AKAI Fire RGB Controller is a Python desktop application designed to provide comprehensive control over the RGB LEDs of an Akai Fire MIDI controller. It allows users to create static color layouts, design frame-by-frame animations, and utilize a screen sampler to reflect desktop colors onto the device pads dynamically. The application features a modern, dark-themed, and intuitive user interface built with PyQt6.

This project aims to unlock the full visual potential of the Akai Fire, transforming it from just a MIDI controller into a versatile lighting instrument and visual feedback tool.

*(Screenshots will be updated once new executable is available)*
<!-- ![Animation Creator Screenshot](https://github.com/user-attachments/assets/d428fdef-93e1-4a24-ac58-8d9c86f7651e) -->
<!-- ![Screen Sampling Screenshot](https://github.com/user-attachments/assets/c02538a7-1de9-4cbc-865e-4a3a7ca2b418) -->
<!-- ![Photo of everything working](https://github.com/user-attachments/assets/f42bbf86-b30a-43b2-808d-8f6871431bb8) -->

## ✨ Features

*   **Direct Pad/Button Painting:** Easily paint individual pads with a chosen color using a smooth, canvas-like drag interface (left-click to paint, right-click to erase).
*   **Sophisticated Color Picker:** Includes SV (Saturation/Value) map, Hue slider, RGB/Hex inputs, and "My Colors" swatches for saving favorite colors (right-click swatches for options).
*   **Static Color Layouts:** Create, save, load, and manage static color presets for the entire 4x16 pad grid.
*   **Frame-by-Frame Animation Sequencer ("Animator Studio"):**
    *   Visual timeline for arranging frames (supports multi-selection).
    *   Add (snapshot/blank), delete, duplicate, copy, cut, and paste frames.
    *   Undo/Redo functionality for frame edits and sequence property changes.
    *   Control animation speed (FPS) and looping.
    *   Integrated sequence file management: Save, load, create new, and delete animation sequences (user, prefab, sampler-recorded).
*   **Interactive Screen Sampler ("Ambient Mode"):**
    *   Visually select a region on any connected monitor using a resizable and snappable selection box.
    *   Dropdown to select the target monitor for sampling.
    *   Live preview of the sampled region within the configuration dialog (when sampling is active).
    *   Adjust Saturation, Contrast, Brightness, and Hue Shift for the sampled colors. These settings are saved per monitor.
    *   Colors from the selected screen region are reflected onto the Akai Fire pads (4x16 grid).
*   **Sampler Recording:**
    *   Record the output of the screen sampler over a sequence of frames.
    *   Automatically save the recording as a new animation sequence into a dedicated user folder.
    *   Recorded sequences are listed in the Animator Studio and can be played, edited, and re-saved.
*   **Hardware Integration & OLED Control:**
    *   Connects to the Akai Fire via MIDI, with port selection and auto-detection.
    *   **Customizable OLED Startup:** Define custom text, font (system fonts), size, and global scroll speed for the default OLED message. Settings are saved and persist.
    *   **Dynamic Knob Control:** Top hardware knobs change function based on context:
        *   **Global Mode:** Knob 1 controls global physical pad brightness.
        *   **Sampler Active Mode:** Knobs 1-4 control Sampler Brightness, Saturation, Contrast, and Hue Shift.
        *   **Animator Playing Mode (Planned):** Knob 4 controls animation speed (FPS).
    *   **OLED Feedback:** Knobs provide real-time value feedback on the OLED display using a dedicated "TomThumb" retro font.
    *   Physical BROWSER and PERFORM buttons can toggle the screen sampler. Other hardware buttons (DRUM, GRID L/R, SELECT Encoder) are mapped to sampler/OLED navigation functions.
*   **Modern UI:** Dark-themed and user-friendly interface using PyQt6 and QSS styling.
*   **Persistent User Settings:**
    *   Color picker swatches.
    *   Screen sampler configurations (region, adjustments per monitor).
    *   OLED customization settings (startup text, font, scroll speed).
    *   All saved to platform-specific user configuration directories.
*   **Global Hotkeys:** Standard shortcuts for common operations.

## 🛠️ Technology Stack

*   **Language:** Python 3 (developed with 3.13)
*   **GUI Framework:** PyQt6
*   **MIDI Communication:** `python-rtmidi` (via `mido`)
*   **Screen Capture:** `mss`
*   **Image Manipulation:** `Pillow (PIL)`
*   **Configuration:** JSON
*   **Styling:** QSS
*   **User Directory Management:** `appdirs`
*   **Packaging (Future):** `PyInstaller`

## 🚀 Getting Started (Standalone Executable - Windows)

*(Currently unavailable - see note at the top. Please use "Setup From Source" for now.)*

<!-- 
1.  Go to the [**Releases**](https://github.com/Reg0lino/AKAI-Fire-RGB-Controller/releases/tag/release) page of this repository.
2.  Download the latest `AkaiFireControllerApp.exe` (or debug) exe file.(Unblock if needed)
3.  Connect your Akai Fire controller.
4.  Run `AkaiFireControllerApp.exe`. 
-->

## ⚙️ Setup & Installation (From Source - For Developers)

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/Reg0lino/AKAI-Fire-RGB-Controller.git
    cd AKAI-Fire-RGB-Controller
    ```
2.  **Create a virtual environment (highly recommended):**
    ```bash
    python -m venv .venv
    ```
    Activate it:
    *   Windows (Command Prompt): `.\.venv\Scripts\activate.bat`
    *   Windows (PowerShell): `.\.venv\Scripts\Activate.ps1`
        *(You might need to run `Set-ExecutionPolicy RemoteSigned -Scope CurrentUser` in an admin PowerShell first)*
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
├── animator/               # Animator-specific logic & UI
├── features/               # Screen sampler core & thread
├── gui/                    # Main GUI components (MainWindow, dialogs, managers)
├── hardware/               # Akai Fire MIDI communication
├── managers/               # Higher-level logic managers (input, OLED)
├── oled_utils/             # OLED rendering utilities
├── presets/                # Default/prefab static layouts and animation sequences
├── resources/              # Fonts, Icons, Stylesheets (QSS)
├── utils.py                # Utility functions (e.g., get_resource_path)
├── user_settings/          # (Dev only) Local user configs (gitignore'd)
│                           # Bundled app uses platform-specific appdirs location.
├── fire_control_app.py     # Main application entry point
├── AkaiFireControllerApp.spec # PyInstaller specification file (for future packaging)
├── README.md
├── CHANGELOG.md
├── LICENSE
├── requirements.txt
└── .gitignore
```
*(User-generated presets like custom animations, static layouts, and OLED items will be saved in their Documents folder under an application-specific directory, e.g., `Documents/AKAI_Fire_RGB_Controller_User_Files/`).*

## 🎮 Usage

1.  Launch the application.
2.  Select the "AKAI Fire" MIDI output and input ports from the "MIDI Connection" section (it should auto-select if "Fire" is in the name) and click "Connect".
3.  **Color Picker:** Select colors. Use "My Colors" to save/load custom swatches.
4.  **Static Pad Layouts:** Apply, save, or load static grid color configurations.
5.  **Animator Studio:** Create and manage frame-by-frame animations. Control playback and speed.
6.  **Screen Sampler (Ambient):**
    *   Toggle ON/OFF using the "Toggle Ambient Sampling" button, or the physical PERFORM/BROWSER buttons on the Fire.
    *   Click "Configure Region & Adjustments..." to open the visual configuration dialog.
    *   Select monitor, define region, and adjust Saturation, Contrast, Brightness, Hue Shift. These can also be controlled by the top four hardware knobs when the sampler is active.
7.  **Sampler Recording:** Record sampler output as an animation sequence.
8.  **OLED Customizer:**
    *   Click the OLED mirror on the main GUI to open the "OLED Startup & Global Settings" dialog.
    *   Customize the default text, font (system fonts), size, and global scroll speed for the OLED display. These settings are saved and persist.
9.  **Quick Tools:** Set paint color to black, clear all pads, or use the eyedropper.

## 📝 TODO / Future Enhancements

*   **OLED Content Library:** Evolve the `OLEDCustomizerDialog` to manage a library of user-created static text items and (eventually) frame-by-frame OLED animations, stored as individual JSON files.
*   **OLED Item Triggering:** Implement PATTERN UP/DOWN button functionality to cycle through saved custom OLED text/animation items, and use the BROWSER button to activate the selected item.
*   **Advanced Animation Editing:** For both pad animator and OLED animator (e.g., interpolation, effects).
*   More screen sampling modes.
*   MIDI input mapping for triggering application functions.
*   More prefab content.
*   Cross-platform testing and packaging (macOS, Linux).

## ⚖️ License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgements

*   The developers of PyQt, Pillow, python-rtmidi, mido, mss, and appdirs.
*   The Akai Pro team for creating the Fire controller.
*   The SEGGER Blog that informed the initial steps to understanding how to fire these animations and particularly the OLED customization!
*   AI Assistants (Gemini models from Google) for extensive assistance with coding, debugging, refactoring, and planning throughout all stages of this project.

---
*Developed by Reg0lino (RegularRegs)*
