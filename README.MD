# Akai Fire PixelForge

## 🚀 Download Latest Release v1.5.0!

**Get the latest standalone executable for Windows from the [GitHub Releases Page](https://github.com/Reg0lino/AKAI-Fire-PixelForge/releases/latest)!**
*(See "Getting Started (Standalone Executable)" below for installation instructions.)*
![Image](https://github.com/Reg0lino/AKAI-Fire-PixelForge/blob/main/images/boring.png)

## 🎛️ Overview

**Akai Fire PixelForge v1.5.0** (developed by Reg0lino & Gemini AI) is a Python desktop application that transforms the Akai Fire controller into a versatile creative tool. It allows users to paint on the 4x16 RGB pads, create frame-by-frame animations, mirror desktop colors, and now, drive a powerful **real-time audio visualizer**. A cornerstone of the project is the enhanced customization of the 128x64 OLED display, featuring a rich library system, advanced image processing, and the ability to **play the "LazyDOOM" retro FPS directly on the OLED!**

This project turns the Akai Fire into a dynamic lighting instrument, a rich visual feedback tool, and even a mini retro gaming console.

![Image](https://raw.githubusercontent.com/Reg0lino/AKAI-Fire-PixelForge/refs/heads/main/images/full.png)
![Image](https://raw.githubusercontent.com/Reg0lino/AKAI-Fire-PixelForge/refs/heads/main/images/oled.png)

## ✨ Features (v1.5.0)

*   **🎵 NEW: Advanced Audio Visualizer!**
    *   Turns system audio into a real-time light show on the pads.
![Image](https://raw.githubusercontent.com/Reg0lino/AKAI-Fire-PixelForge/refs/heads/main/images/audiovis.png)
    *   **Three Modes:** Choose from "Classic Spectrum Bars", "Pulse Wave", or the comprehensive "Dual VU + Spectrum".
    *   **Live Settings:** A detailed settings dialog allows for real-time tweaking of colors, sensitivity, smoothness, and more while the visualizer is running.
    *   Includes a robust preset system for saving and loading custom palettes and schemes.
*   **🎨 NEW: Primary/Secondary Color System!**
    *   The color picker now supports both a primary (left-click) and a secondary (right-click) color for a more intuitive painting workflow, similar to professional image editors.
*   **🔆 NEW: Global Controls Panel**
    *   A dedicated "Global Controls" panel provides an explicit slider for master pad brightness, synced with the hardware knob.
*   **👹 LazyDOOM Game Mode!**
![Image](https://raw.githubusercontent.com/Reg0lino/AKAI-Fire-PixelForge/refs/heads/main/images/doomoled.png)
![Image](https://raw.githubusercontent.com/Reg0lino/AKAI-Fire-PixelForge/refs/heads/main/images/doomcontrol.png)
    *   Play a retro-style first-person shooter directly on your Akai Fire!
    *   Features procedural map generation, enemies, and full control via pads and keyboard.
*   **Advanced OLED Display Customization:**
![Image](https://raw.githubusercontent.com/Reg0lino/AKAI-Fire-PixelForge/refs/heads/main/images/oled.png)
    *   **OLED Content Library:** Create, edit, and manage custom "Text Items" and "Image Animation Items" (from static images or GIFs).
    *   **Advanced Image Processing:** Sliders for Brightness, Contrast, Gamma, Sharpen, and Blur. Multiple dithering algorithms (Floyd-Steinberg, Atkinson, Ordered Dithering) with variable strength.
*   **Direct Pad Painting & Static Layouts:**
    *   Canvas-like drag interface and savable static color layouts.
*   **Frame-by-Frame Pad Animation Sequencer ("Animator Studio"):**
![Image](https://raw.githubusercontent.com/Reg0lino/AKAI-Fire-PixelForge/refs/heads/main/images/animatorUI.png)
    *   Visual timeline, frame operations (copy/paste, duplicate), and undo/redo support.
*   **Interactive Screen Sampler ("Ambient Mode"):**
    *   Visually select screen regions and mirror them onto the pads.
    *   Adjust Brightness, Saturation, Contrast, and Hue Shift.
    *   Record sampler output directly into a new animation.
![Image](https://raw.githubusercontent.com/Reg0lino/AKAI-Fire-PixelForge/refs/heads/main/images/sample.png)
*   **Hardware Integration & Revamped UI:**
    *   **Custom-Rendered Knobs:** Top-strip knobs have been rebuilt for a professional look and feel, providing stable visual feedback.
    *   **Dynamic Knob Control:** Knobs contextually control Global Brightness, Sampler Parameters, or Animator Speed.
    *   **OLED Feedback:** Real-time feedback for knob turns and system events.
![Image](https://raw.githubusercontent.com/Reg0lino/AKAI-Fire-PixelForge/refs/heads/main/images/toprow.png)

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
2.  Download `Setup_Akai_Fire_PixelForge_v1.5.0.exe`.
3.  Run the installer.
4.  **IMPORTANT (Windows Users - Antivirus/SmartScreen):**
    *   As an independently developed application, Windows SmartScreen or your antivirus might show a warning.
    *   If downloaded from the official GitHub release, the application is safe.
    *   Click "More info" then "Run anyway" on SmartScreen. For antivirus, choose to "Allow" or "Trust" the application.
5.  Connect your Akai Fire controller.
6.  Launch "Akai Fire PixelForge" from your Start Menu or Desktop shortcut.

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
├── features/               # Screen sampler core
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

*   Developers of PyQt, Pillow, python-rtmidi, mido, mss, appdirs, NumPy.
*   Akai Pro for the Fire controller.
*   The SEGGER Blog for initial OLED SysEx insights. (and everything else the AI scrubbed from that blog)
*   This project was largely envisioned, directed, and debugged by Reg0lino, with Google's Gemini AI acting as an intensive coding and refactoring partner.

---
*Developed by Reg0lino (RegularRegs)*
