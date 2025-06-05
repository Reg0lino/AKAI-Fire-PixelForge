# Akai Fire PixelForge

## 🚀 Download Latest Release v1.0.0!

**Get the latest standalone executable for Windows from the [GitHub Releases Page](https://github.com/Reg0lino/AKAI-Fire-PixelForge/releases/latest)!**
*(See "Getting Started (Standalone Executable)" below for installation instructions.)*
![Image](https://github.com/user-attachments/assets/16759301-d11a-4260-aab8-803e2cc5c84f)

## 🎛️ Overview

**Akai Fire PixelForge v1.0.0** (developed by Reg0lino & Gemini AI) is a Python desktop application providing comprehensive control over an Akai Fire MIDI controller. It allows users to customize its 4x16 RGB pad matrix with static color layouts and frame-by-frame animations, and dynamically reflect desktop colors onto the pads using a screen sampler. A cornerstone of this release is the **vastly enhanced customization of the Akai Fire's 128x64 monochrome OLED display**, featuring a rich library system, advanced image processing (including new dithering algorithms, gamma, blur, sharpen, noise injection), and now, the ability to **play the "LazyDOOM" retro FPS directly on the OLED!**

This project transforms the Akai Fire into a versatile lighting instrument, a rich visual feedback tool, and even a mini retro gaming console.

![Image](https://github.com/user-attachments/assets/fcec95de-555b-4066-87a9-aa0419526ef4)
![Image](https://github.com/user-attachments/assets/f3bbcca6-abad-454e-b441-ec2d4533f6b0)

## ✨ Features (v1.0.0)

*   **👹 NEW: LazyDOOM Game Mode!**
    *   Play a retro-style first-person shooter directly on your Akai Fire!
    *   Features procedural map generation, enemies, health, and full control via pads.
    *   Game view rendered on the OLED, with RGB pad feedback for health and actions.
    *   Includes instructions dialog and selectable difficulty levels.
    *   PixelForge's other functions are paused during gameplay for dedicated performance.
*   **Advanced OLED Display Customization (Enhanced & Finalized!):**
![Image](https://github.com/user-attachments/assets/bd4aa2e4-a4fb-47e6-909b-2d501bb30c99)
    *   **OLED Content Library Manager:** Create, edit, manage, and save custom "Text Items" and "Image Animation Items" (from static images or GIFs) as JSON presets. Includes live previews, a "Save & Apply" feature, and distinct labeling for single-frame "(Image)" items.
    *   **Custom Text Items:** Define text, select system fonts, set size, alignment, and scrolling behavior (with speed/pause overrides).
    *   **Custom Image & GIF Animations (Full Suite):**
        *   Import images/GIFs with extensive processing options:
            *   **Pre-Dithering Adjustments:** Sliders for Brightness, Contrast, **Gamma Correction**, **Sharpening**, and **Pre-Dither Blur**.
            *   **Monochrome Conversion & Dithering:** Floyd-Steinberg, **Atkinson**, Simple Threshold (adjustable), and multiple **Ordered Dithering (Bayer 2x2, 4x4, 8x8)** options.
            *   **Variable Dither Strength:** Control the intensity of error-diffusion dithers.
            *   **Noise Injection:** Add "Pre-Dither" or "Post-Dither" noise with adjustable amount.
            *   Standard options like Resize Modes and Color Inversion remain.
        *   Set playback FPS and loop behavior for animations.
    *   **"Active Graphic" System:** Designate any custom item as your persistent default OLED display.
    *   **Manual Play/Pause for OLED Active Graphic:** Clickable icon on the main UI.
    *   **Temporary System Messages:** Clear "TomThumb" font feedback, reverting to Active Graphic.
*   **Direct Pad/Button Painting:** Canvas-like drag interface (left-click paint, right-click erase).
*   **Sophisticated Color Picker:** SV map, Hue slider, RGB/Hex inputs, "My Colors" swatches.
*   **Static Color Layouts:** Create, save, load, and manage static color presets.
*   **Frame-by-Frame Pad Animation Sequencer ("Animator Studio"):**
![Image](https://github.com/user-attachments/assets/bd3e8232-df5d-41d-ba4b-05975b16d59b)
    *   Visual timeline, frame operations (add, delete, duplicate, copy/paste), undo/redo (per paint stroke).
    *   Control animation speed (FPS) and looping. Sequence file management.
*   **Interactive Screen Sampler ("Ambient Mode"):**
    *   Visually select screen regions, choose monitor, live preview.
    *   Adjust Saturation, Contrast, Brightness, Hue Shift (settings saved per monitor).
    *   Record sampler output as animations.
*   **Hardware Integration & Contextual Control:**
    *   MIDI connection with port selection and auto-detection.
    *   **Dynamic Knob Control:** Global Pad Brightness, Sampler Parameters, or Animator Speed.
    *   **OLED Feedback:** Real-time feedback for knob turns and system events.
    *   **Hardware Button Mapping:** BROWSER/PERFORM for sampler, DRUM for monitor cycle, etc.
*   **Modern UI & Persistent Settings:** Dark-themed PyQt6 interface, QSS styling. User settings saved.
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

## 🚀 Getting Started (Standalone Executable - Windows for v1.0.0)

1.  Go to the [**GitHub Releases Page**](https://github.com/Reg0lino/AKAI-Fire-PixelForge/releases/latest).
2.  Download `Setup_Akai_Fire_PixelForge_v1.0.0.exe`.
3.  Run the installer. It will guide you through the setup process.
4.  (Optional but Recommended) During installation, ensure the "Install Example Presets" component is checked to get the latest Starter Pack content. You can also download `Starter_Pack_Examples_v1.0.0.zip` separately from the release assets.
5.  **IMPORTANT (Windows Users - Antivirus/SmartScreen):**
    *   As an independently developed application, Windows SmartScreen or your antivirus might show a warning.
    *   If downloaded from the official GitHub release, the application is safe.
    *   Click "More info" then "Run anyway" on SmartScreen. For antivirus, choose to "Allow" or "Trust" the application.
    *   A more detailed `README.txt` is installed with the application, including notes on this.
6.  Connect your Akai Fire controller.
7.  Launch "Akai Fire PixelForge" from your Start Menu or Desktop shortcut.

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
    python forge.py 
    ```
    (Note: Entry point might be `fire_control_app.py` in older branches, now it's `forge.py`)


## 📂 Project Structure (Key Files)
```
AKAI-Fire-PixelForge/
├── animator/               # Animator logic & UI
├── doom_feature/           # LazyDOOM game logic & assets
├── features/               # Screen sampler core
├── gui/                    # Main GUI components (MainWindow, dialogs)
├── hardware/               # Akai Fire MIDI communication
├── managers/               # Logic managers (input, OLED)
├── oled_utils/             # OLED image processing, rendering
├── presets/                # Bundled prefab sequences & layouts
├── resources/              # Fonts, Icons, Stylesheets
├── forge.py                # Main entry point (formerly fire_control_app.py)
├── README.md, CHANGELOG.md, LICENSE, requirements.txt
...
```
User-generated presets (Animator Sequences, Static Layouts, OLED Items) are saved in `Documents/Akai Fire RGB Controller User Presets/`.

## 🎮 Usage

1.  Launch, connect to Akai Fire (ports should auto-select). OLED shows startup, then Active Graphic.
2.  **OLED Customization:** Click the on-screen OLED mirror. Create/edit Text or Image/GIF items.
    *   Explore the "Import & Processing Options": Try different **Monochrome** dithering algorithms, adjust **Brightness**, **Contrast**, **Gamma**, **Sharpening**, **Dither Strength**, **Pre-Dither Blur**, and **Noise Injection**.
    *   Use "Set as Active Graphic" or "Save & Apply". Manually pause/play OLED via icon.
3.  **Pad Control:** Use Color Picker, Static Layouts, or Animator Studio.
4.  **Screen Sampler:** Toggle via UI/hardware. Configure region/adjustments. Record.
5.  **LazyDOOM:** Click the "👹 LazyDOOM" button on the right panel. Follow instructions.
6.  **Hardware Controls:** Utilize top knobs and buttons for context-sensitive control.

## 📝 Future Ideas

*   Cross-platform packaging (macOS, Linux).
*   More advanced animation features (e.g., easing, layer blending).
*   Further LazyDOOM enhancements (more enemy types, pickups, sound).

## ⚖️ License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgements

*   Developers of PyQt, Pillow, python-rtmidi, mido, mss, appdirs, NumPy.
*   Akai Pro for the Fire controller.
*   The SEGGER Blog for initial OLED SysEx insights.
*   This project was largely envisioned, directed, and debugged by Reg0lino, with Google's Gemini AI acting as an intensive coding and refactoring partner.

---
*Developed by Reg0lino (RegularRegs)*
