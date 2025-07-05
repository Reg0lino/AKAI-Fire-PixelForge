# PixelForge for Akai Fire

## 🚀 Download Latest Release v2.0.0!

**Get the latest version for Windows from the [GitHub Releases Page](https://github.com/Reg0lino/AKAI-Fire-PixelForge/releases/latest)!**

![PixelForge Main UI](https://raw.githubusercontent.com/Reg0lino/AKAI-Fire-PixelForge/refs/heads/main/images/full.png)

## 🎛️ Overview

**PixelForge for Akai Fire v2.0.0** (developed by Reg0lino & Gemini AI) is a powerful desktop application that transforms the Akai Fire controller from a dedicated FL Studio accessory into a versatile, standalone instrument for visual and creative expression.

This project allows users to paint on the 4x16 RGB pads, create complex frame-by-frame animations, mirror desktop colors for ambient lighting, and drive a powerful real-time audio visualizer. This version introduces a powerful **GIF Importer**, allowing you to create stunning animations from existing files on your computer or the web. A cornerstone of the project is the enhanced customization of the 128x64 OLED display, featuring a rich library system, advanced image processing, and the ability to **play the "LazyDOOM" retro FPS directly on the OLED!**

This application turns the Akai Fire into a dynamic lighting instrument, a rich visual feedback tool, and a mini retro gaming console, all driven by a stable, professional-grade user interface.

## ✨ Features (v2.0.0)

*   **📥 NEW: GIF Importer for Pad Animations!**
    *   **Create Complex Animations Instantly:** A new dialog allows you to import GIFs from a local file or directly from a URL.
    *   **Visual Region Selection:** Click and drag on the GIF preview to sample only the area you want.
    *   **Live Previews:** See a real-time preview of the final 16x4 animation on-screen and on the physical hardware pads as you adjust settings.
    *   **Full Customization:** Tweak brightness, saturation, contrast, hue, and playback speed before importing.

    ![New Gif-To-Pad Importer](https://raw.githubusercontent.com/Reg0lino/AKAI-Fire-PixelForge/refs/heads/main/images/gif_importer.png)

*   **🎨 Redesigned Animator Studio & Workflow**
    *   A new dropdown menu lets you browse, load, and manage all your saved animation sequences.
    *   The dropdown provides instant visual feedback (`*`) for unsaved changes.
    *   A "Delete" button has been added for easy sequence management.

    ![Animator UI](https://raw.githubusercontent.com/Reg0lino/AKAI-Fire-PixelForge/refs/heads/main/images/animator_v2.png)

*   **🖥️ High-Performance Screen Sampler ("Ambient Mode")**
    *   **Multiple Modes:** Choose between "Region" (classic visual selection), "Thumbnail" (a beautiful, low-CPU mirror of your screen), or "Palette" (a creative gradient of dominant colors).
    *   Adjust Brightness, Saturation, Contrast, and Hue Shift in real-time.
    *   Record sampler output directly into a new animation.

    ![Screen Sampler](https://raw.githubusercontent.com/Reg0lino/AKAI-Fire-PixelForge/refs/heads/main/images/sample.png)

*   **🎵 Advanced Audio Visualizer**
    *   Turns system audio into a real-time light show on the pads.
    *   **Three Modes:** "Classic Spectrum Bars", "Pulse Wave", or the comprehensive "Dual VU + Spectrum".
    *   **Live Settings:** A detailed settings dialog allows for real-time tweaking of colors, sensitivity, smoothness, and more while the visualizer is running.

    ![Audio Visualizer](https://raw.githubusercontent.com/Reg0lino/AKAI-Fire-PixelForge/refs/heads/main/images/audiovis.png)

*   **👹 LazyDOOM Game Mode!**
    *   Play a retro-style first-person shooter directly on your Akai Fire!
    *   Features procedural map generation, enemies, and full control via pads and keyboard.

    ![LazyDOOM OLED](https://raw.githubusercontent.com/Reg0lino/AKAI-Fire-PixelForge/refs/heads/main/images/doomoled.png)

*   **Advanced OLED Display Customization**
    *   **Content Library:** Create, edit, and manage custom "Text Items" and "Image Animation Items" (from static images or GIFs).
    *   **Advanced Image Processing:** Sliders for Brightness, Contrast, Gamma, and Sharpen, plus multiple dithering algorithms.
    *   **Active Graphic System:** Set any custom OLED creation as your persistent default display.

    ![OLED Customizer](https://raw.githubusercontent.com/Reg0lino/AKAI-Fire-PixelForge/refs/heads/main/images/oled.png)

*   **Full Hardware Integration & Revamped UI**
    *   **Smart, Context-Aware Knobs:** The top-strip knobs automatically control Global Brightness, Sampler Parameters, or Animator Speed depending on the active mode.
    *   **Complete Button Mapping:** All major features are mapped to physical hardware buttons for a screen-free workflow.
    *   **Real-time OLED Feedback:** The OLED provides instant feedback for knob turns, mode changes, and other system events.

    ![Hardware Top Strip](https://raw.githubusercontent.com/Reg0lino/AKAI-Fire-PixelForge/refs/heads/main/images/toprow.png)

## 🛠️ Technology Stack

*   **Language:** Python 3.12
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
2.  Download `Setup_PixelForge_for_Akai_Fire_v2.0.0.exe`.
3.  Run the installer.
4.  **IMPORTANT (Windows Users - Antivirus/SmartScreen):**
    *   As an independently developed application, Windows SmartScreen or your antivirus might show a warning.
    *   If downloaded from the official GitHub release, the application is safe.
    *   Click "More info" then "Run anyway" on SmartScreen. For antivirus, choose to "Allow" or "Trust" the application.
5.  Connect your Akai Fire controller.
6.  Launch "PixelForge for Akai Fire" from your Start Menu or Desktop shortcut.
7.  Click the **"🚀 App Guide"** button on the menu bar for a full tour and hotkey list!

## ⚙️ Setup & Installation (From Source - For Developers)

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/Reg0lino/AKAI-Fire-PixelForge.git
    cd AKAI-Fire-PixelForge
    ```
2.  **Create and activate a virtual environment (Python 3.12 recommended).**
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
PixelForge-for-Akai-Fire/
├── animator/               # Animator logic & UI
├── doom_feature/           # LazyDOOM game logic
├── features/               # Screen sampler, GIF processor
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
*   The SEGGER Blog for initial insights into the OLED SysEx protocol (and probably more that the AI scraped to get started).
*   This project was envisioned, directed, and debugged by Reg0lino, with Google's Gemini AI 2.5 acting as an intensive coding and refactoring partner.

---
*Developed by Reg0lino (RegularRegs)*
