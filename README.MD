# Akai Fire PixelForge

## 🚀 Download Latest Release!

**Get the latest standalone executable for Windows from the [GitHub Releases Page](https://github.com/Reg0lino/AKAI-Fire-PixelForge/releases/latest)!** 
*(See "Getting Started (Standalone Executable)" below for installation instructions.)*
![Image](https://github.com/user-attachments/assets/16759301-d11a-4260-aab8-803e2cc5c84f)

## 🎛️ Overview

**Akai Fire PixelForge** (developed by Reg0lino & Gemini AI) is a Python desktop application designed to provide comprehensive control over an Akai Fire MIDI controller. It allows users to customize its 4x16 RGB pad matrix with static color layouts and frame-by-frame animations, and dynamically reflect desktop colors onto the pads using a screen sampler. Critically, it now offers advanced customization of the Akai Fire's 128x64 monochrome OLED display. The application features a modern, dark-themed, and intuitive user interface built with PyQt6.

This project aims to unlock the full visual potential of the Akai Fire, transforming it from just a MIDI controller into a versatile lighting instrument and a rich visual feedback tool, especially through its newly enhanced OLED capabilities.

![Image](https://github.com/user-attachments/assets/fcec95de-555b-4066-87a9-aa0419526ef4)
![Image](https://github.com/user-attachments/assets/f3bbcca6-abad-454e-b441-ec2d4533f6b0)


## ✨ Features

*   **Direct Pad/Button Painting:** Easily paint individual pads with a chosen color using a smooth, canvas-like drag interface (left-click to paint, right-click to erase).
*   **Sophisticated Color Picker:** Includes SV (Saturation/Value) map, Hue slider, RGB/Hex inputs, and "My Colors" swatches for saving favorite colors (right-click swatches for options).
*   **Static Color Layouts:** Create, save, load, and manage static color presets for the entire 4x16 pad grid.
*   **Frame-by-Frame Pad Animation Sequencer ("Animator Studio"):**
![Image](https://github.com/user-attachments/assets/bd3e8232-df5d-4a1d-ba4b-05975b16d59b)
![Image](https://github.com/user-attachments/assets/bd3e8232-df5d-4a1d-ba4b-05975b16d59b)
    *   Visual timeline for arranging frames (supports multi-selection).
    *   Add (snapshot/blank), delete, duplicate, copy, cut, and paste frames.
    *   **Improved Undo/Redo:** Undo functionality now operates on a "per paint stroke" basis for smoother drawing performance, while still supporting undo for other major actions.
    *   Control animation speed (FPS) and looping.
    *   Integrated sequence file management: Save, load, create new, and delete animation sequences.
    *   **Performance Note:** Pad drawing responsiveness in the Animator is significantly improved.
*   **Interactive Screen Sampler ("Ambient Mode"):**
    *   Visually select a region on any connected monitor.
    *   Dropdown to select the target monitor for sampling.
    *   Live preview of the sampled region within the configuration dialog.
    *   Adjust Saturation, Contrast, Brightness, and Hue Shift for the sampled colors (settings saved per monitor).
    *   Colors from the screen region are reflected onto the Akai Fire pads.
*   **Sampler Recording:** Record sampler output as new animation sequences.
*   **Advanced OLED Display Customization (New & Enhanced!):**
![Image](https://github.com/user-attachments/assets/bd4aa2e4-a4fb-47e6-909b-2d501bb30c99)
    *   **OLED Content Library Manager:** Create, edit, manage, and save custom "Text Items" and "Image Animation Items" (from static images or GIFs) as JSON presets. Includes live previews and a "Save & Apply" feature. Single-frame image items are now distinctly labeled "(Image)".
    *   **Custom Text Items:** Define text, select system fonts, set size, alignment, and scrolling behavior (with speed/pause overrides).
    *   **Custom Image & GIF Animations:** Import images/GIFs with processing options (resize, contrast, invert, multiple dithering algorithms like Floyd-Steinberg, Threshold, Bayer). Set playback FPS and loop behavior.
    *   **"Active Graphic" System:** Designate any custom item as your persistent default OLED display after the built-in startup visual.
    *   **Manual Play/Pause for OLED Active Graphic:** A new clickable icon on the main UI allows users to manually pause/resume the OLED's Active Graphic. This can be useful for performance if the OLED animation (especially high FPS) impacts other interactions like pad animator drawing.
    *   **Temporary System Messages:** Clear, large "TomThumb" font feedback for hardware actions and status updates, gracefully reverting to the Active Graphic.
    *   **Application Default Message:** A default scrolling message if no Active Graphic is set.
*   **Hardware Integration & Contextual Control:**
    *   MIDI connection with port selection and auto-detection.
    *   **Dynamic Knob Control:** Top hardware knobs adapt to control Global Pad Brightness, Sampler Parameters (Brightness, Saturation, Contrast, Hue), or Animator Speed.
    *   **OLED Feedback:** Real-time feedback for knob turns and system events on the OLED.
    *   **Hardware Button Mapping:** BROWSER/PERFORM for sampler toggle; DRUM for monitor cycle; GRID L/R & SELECT Encoder for UI list navigation; PATTERN UP/DOWN & BROWSER for OLED item cueing/activation.
*   **Modern UI & Persistent Settings:** Dark-themed PyQt6 interface, QSS styling. User settings (color swatches, sampler prefs, OLED config) saved.
*   **Global Hotkeys:** For common animator operations.

## 🛠️ Technology Stack

*   **Language:** Python 3 (developed with 3.13)
*   **GUI Framework:** PyQt6
*   **MIDI Communication:** `python-rtmidi` (via `mido`)
*   **Screen Capture:** `mss`
*   **Image Manipulation:** `Pillow (PIL)`, `NumPy`
*   **Configuration & Presets:** JSON
*   **Styling:** QSS
*   **User Directory Management:** `appdirs`
*   **Packaging:** `PyInstaller`

## 🚀 Getting Started (Standalone Executable - Windows)

1.  Go to the [**GitHub Releases Page**](https://github.com/Reg0lino/AKAI-Fire-PixelForge/releases/latest).
2.  Download the `Akai.Fire.PixelForge.Release.zip` (or `...DEBUG.zip` for a console window).
3.  Extract the ZIP archive to a folder on your computer.
4.  **IMPORTANT (Windows Users):** You may need to "unblock" the executable.
    *   Right-click on `Akai Fire PixelForge.exe` inside the extracted folder.
    *   Select "Properties."
    *   On the "General" tab, if you see an "Unblock" checkbox or button near the bottom, check/click it, then click "Apply" and "OK."
    *   (A more detailed `INSTRUCTIONS_TO_UNBLOCK.MD` is included in the ZIP).
5.  Connect your Akai Fire controller.
6.  Run `Akai Fire PixelForge.exe`.

## ⚙️ Setup & Installation (From Source - For Developers)

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/Reg0lino/AKAI-Fire-PixelForge.git
    cd AKAI-Fire-PixelForge
    ```
2.  **Create and activate a virtual environment (highly recommended):**
    *   Create: `python -m venv .venv`
    *   Activate (Windows CMD): `.\.venv\Scripts\activate.bat`
    *   Activate (Windows PowerShell): `.\.venv\Scripts\Activate.ps1`
    *   Activate (macOS/Linux): `source .venv/bin/activate`
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
```
AKAI-Fire-PixelForge/
├── animator/               # Animator logic & UI
├── features/               # Screen sampler core
├── gui/                    # Main GUI components (MainWindow, dialogs)
├── hardware/               # Akai Fire MIDI communication
├── managers/               # Logic managers (input, OLED)
├── oled_utils/             # OLED image processing, rendering
├── presets/                # Bundled prefab sequences & layouts
├── resources/              # Fonts, Icons (including play-pause.png), Stylesheets
├── fire_control_app.py     # Main entry point
├── README.md, CHANGELOG.md, LICENSE, requirements.txt
...
```
User-generated presets (Animator Sequences, Static Layouts, OLED Items) are saved in `Documents/Akai Fire RGB Controller User Presets/`.

## 🎮 Usage

1.  Launch, connect to Akai Fire (ports should auto-select). OLED shows startup, then Active Graphic.
2.  **OLED Customization:** Click OLED mirror. Create/edit Text or Image/GIF items. Use "Set as Active Graphic" or "Save & Apply". Manually pause/play OLED via icon next to mirror.
3.  **Pad Control:** Use Color Picker, Static Layouts, or Animator Studio.
4.  **Screen Sampler:** Toggle via UI/hardware. Configure region/adjustments. Record animations.
5.  **Hardware Controls:** Utilize top knobs and buttons for context-sensitive control.

## 📝 TODO / Future Enhancements

*   Additional dithering algorithms (e.g., Atkinson).
*   Advanced animation editing (interpolation, effects).
*   More prefab content.
*   Cross-platform packaging (macOS, Linux).
*   Investigate Base64 frame storage for large OLED animations.

## ⚖️ License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgements

*   Developers of PyQt, Pillow, python-rtmidi, mido, mss, appdirs, NumPy.
*   Akai Pro for the Fire controller.
*   The SEGGER Blog for initial OLED SysEx insights.
*   This project was largely envisioned, directed, and debugged by Reg0lino, with Google's Gemini AI acting as an intensive coding and refactoring partner to implement many of the complex features.

---
*Developed by Reg0lino (RegularRegs)*

