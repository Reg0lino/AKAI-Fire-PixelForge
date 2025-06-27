# Akai Fire PixelForge

## 🚀 Download Latest Release v1.7.0!

**Get the latest version for Windows from the [GitHub Releases Page](https://github.com/Reg0lino/AKAI-Fire-PixelForge/releases/latest)!**

![PixelForge Main UI](https://raw.githubusercontent.com/Reg0lino/AKAI-Fire-PixelForge/refs/heads/main/images/full.png)

## 🎛️ Overview

**Akai Fire PixelForge v1.7.0** (developed by Reg0lino & Gemini AI) is a powerful desktop application that transforms the Akai Fire controller from a dedicated FL Studio accessory into a versatile, standalone instrument for visual and creative expression.

This project allows users to paint on the 4x16 RGB pads, create complex frame-by-frame animations, mirror desktop colors for ambient lighting, and drive a powerful real-time audio visualizer. A cornerstone of the project is the enhanced customization of the 128x64 OLED display, featuring a rich library system, advanced image processing, and the ability to **play the "LazyDOOM" retro FPS directly on the OLED!**

This application turns the Akai Fire into a dynamic lighting instrument, a rich visual feedback tool, and a mini retro gaming console, all driven by a stable, professional-grade user interface.

## ✨ Features (v1.7.0)

*   **🎨 NEW: Full UI Overhaul & Color Grading System!**
    *   **Universal Color Grading / Live FX:** A new panel provides real-time, non-destructive control over **Brightness, Saturation, Contrast, and Hue** for all visual output.
    *   **"Bake In" Effects:** Permanently apply the current FX settings to selected animator frames, complete with full Undo/Redo support.
    *   **Redesigned Layout:** The entire application has been re-architected for a more logical and scalable workflow, with a new full-featured menu bar.

    ![Color FX Panel](https://raw.githubusercontent.com/Reg0lino/AKAI-Fire-PixelForge/refs/heads/main/images/color_grading_fx.png)

*   **🎵 Advanced Audio Visualizer**
    *   Turns system audio into a real-time light show on the pads.
    *   **Three Modes:** "Classic Spectrum Bars", "Pulse Wave", or the comprehensive "Dual VU + Spectrum".
    *   **Live Settings:** A detailed settings dialog allows for real-time tweaking of colors, sensitivity, smoothness, and more while the visualizer is running.
    *   Includes a robust preset system for saving and loading custom palettes and schemes.

    ![Audio Visualizer](https://raw.githubusercontent.com/Reg0lino/AKAI-Fire-PixelForge/refs/heads/main/images/audiovis.png)

*   **👹 LazyDOOM Game Mode!**
    *   Play a retro-style first-person shooter directly on your Akai Fire!
    *   Features procedural map generation, enemies, and full control via pads and keyboard.

    ![LazyDOOM OLED](https://raw.githubusercontent.com/Reg0lino/AKAI-Fire-PixelForge/refs/heads/main/images/doomoled.png)

    ![LazyDOOM Controls](https://raw.githubusercontent.com/Reg0lino/AKAI-Fire-PixelForge/refs/heads/main/images/doomcontrol.png)

*   **Advanced OLED Display Customization**
    *   **Content Library:** Create, edit, and manage custom "Text Items" and "Image Animation Items" (from static images or GIFs).
    *   **Advanced Image Processing:** Sliders for Brightness, Contrast, Gamma, and Sharpen, plus multiple dithering algorithms (Floyd-Steinberg, Atkinson, etc.).
    *   **Active Graphic System:** Set any custom OLED creation as your persistent default display.
    *   **Export to GIF:** Export your custom OLED animations as GIF files directly from the application.

    ![OLED Customizer](https://raw.githubusercontent.com/Reg0lino/AKAI-Fire-PixelForge/refs/heads/main/images/oled.png)

*   **Frame-by-Frame Pad Animation Sequencer ("Animator Studio")**
    *   Visual timeline, frame operations (copy/paste, duplicate), and robust undo/redo support.
    *   **Primary/Secondary Color System:** A professional painting workflow with separate colors for left-click and right-click.

    ![Animator UI](https://raw.githubusercontent.com/Reg0lino/AKAI-Fire-PixelForge/refs/heads/main/images/animatorUI.png)
    ![Image](https://raw.githubusercontent.com/Reg0lino/AKAI-Fire-PixelForge/refs/heads/main/images/redbluepurpleburst.gif)
*   **Interactive Screen Sampler ("Ambient Mode")**
    *   Visually select screen regions and mirror them onto the pads.
    *   Adjust Brightness, Saturation, Contrast, and Hue Shift in real-time.
    *   Record sampler output directly into a new animation.

    ![Screen Sampler](https://raw.githubusercontent.com/Reg0lino/AKAI-Fire-PixelForge/refs/heads/main/images/sample.png)

*   **Full Hardware Integration & Revamped UI**
    *   **Smart, Context-Aware Knobs:** The top-strip knobs automatically control Global Brightness, Sampler Parameters, or Animator Speed depending on the active mode.
    *   **Complete Button Mapping:** All major features, including mode-switching (Sampler/Visualizer) and FX toggling, are mapped to physical hardware buttons for a screen-free workflow.
    *   **Real-time OLED Feedback:** The OLED provides instant feedback for knob turns, mode changes, and other system events.

    ![Hardware Top Strip](https://raw.githubusercontent.com/Reg0lino/AKAI-Fire-PixelForge/refs/heads/main/images/toprow.png)

## 🛠️ Technology Stack

*   **Language:** Python 3
*   **GUI Framework:** PyQt6
*   **Audio Capture:** `pyaudiowpatch` (for Windows loopback)
*   **MIDI Communication:** `python-rtmidi` (via `mido`)
*   **Screen Capture:** `mss`
*   **Image Manipulation:** `Pillow (PIL)`, `NumPy`
*   **Configuration & Presets:** JSON
*   **User Directory Management:** `appdirs`
*   **Packaging:** `PyInstaller`

## 🚀 Getting Started (Standalone Executable - Windows)

1.  Go to the [**GitHub Releases Page**](https://github.com/Reg0lino/AKAI-Fire-PixelForge/releases/latest).
2.  Download `Setup_Akai_Fire_PixelForge_v1.7.0.exe`.
3.  Run the installer.
4.  **IMPORTANT (Windows Users - Antivirus/SmartScreen):**
    *   As an independently developed application, Windows SmartScreen or your antivirus might show a warning.
    *   If downloaded from the official GitHub release, the application is safe.
    *   Click "More info" then "Run anyway" on SmartScreen. For antivirus, choose to "Allow" or "Trust" the application.
5.  Connect your Akai Fire controller.
6.  Launch "Akai Fire PixelForge" from your Start Menu or Desktop shortcut.
7.  Click the **"🚀 App Guide"** button on the menu bar for a full tour and hotkey list!

## ⚙️ Setup & Installation (From Source - For Developers)

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/Reg0lino/AKAI-Fire-PixelForge.git
    cd AKAI-Fire-PixelForge
    ```
2.  **Create and activate a virtual environment.**
3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
4.  **Run the application:**
    ```bash
    python forge.py
    ```

## 📂 Project Structure (Key Files)
```
AKAI-Fire-PixelForge/
├── animator/               # Animator logic & UI
├── doom_feature/           # LazyDOOM game logic
├── features/               # Screen sampler core & thread
├── gui/                    # Main GUI components (MainWindow, dialogs)
├── hardware/               # Akai Fire MIDI communication
├── managers/               # Logic managers (input, OLED, audio)
├── oled_utils/             # OLED image processing
├── resources/              # Fonts, Icons, Stylesheets
├── forge.py                # Main entry point
...
```
User-generated presets are saved in `Documents/Akai Fire RGB Controller User Presets/`.

## ⚖️ License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgements

*   Developers of PyQt, Pillow, python-rtmidi, mido, mss, appdirs, and NumPy.
*   Akai Pro for creating the versatile Fire controller.
*   The SEGGER Blog for initial insights into the OLED SysEx protocol.
*   This project was envisioned, directed, and debugged by Reg0lino, with Google's Gemini AI acting as an intensive coding and refactoring partner.

---
*Developed by Reg0lino (RegularRegs)*
