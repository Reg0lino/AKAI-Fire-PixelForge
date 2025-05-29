# Akai Fire PixelForge by Reg0lino & Gemini 2.5 Pro

## 🚀 Download Latest Release!

**Get the latest standalone executable for Windows from the [GitHub Releases Page](https://github.com/Reg0lino/AKAI-Fire-RGB-Controller/releases/latest)!** 
*(See "Getting Started (Standalone Executable)" below for installation instructions.)*
![Image](https://github.com/user-attachments/assets/16759301-d11a-4260-aab8-803e2cc5c84f)
## 🎛️ Overview

The "Akai Fire PixelForge by Reg0lino & Gemini 2.5 Pro" is a Python desktop application designed to provide comprehensive control over an Akai Fire MIDI controller. It allows users to customize its 4x16 RGB pad matrix with static color layouts and frame-by-frame animations, and dynamically reflect desktop colors onto the pads using a screen sampler. Critically, it now offers advanced customization of the Akai Fire's 128x64 monochrome OLED display. The application features a modern, dark-themed, and intuitive user interface built with PyQt6.

This project aims to unlock the full visual potential of the Akai Fire, transforming it from just a MIDI controller into a versatile lighting instrument and a rich visual feedback tool, especially through its newly enhanced OLED capabilities.

![Image](https://github.com/user-attachments/assets/fcec95de-555b-4066-87a9-aa0419526ef4)
![Image](https://github.com/user-attachments/assets/f3bbcca6-abad-454e-b441-ec2d4533f6b0)

## ✨ Features

*   **Direct Pad/Button Painting:** Easily paint individual pads with a chosen color using a smooth, canvas-like drag interface (left-click to paint, right-click to erase).
*   **Sophisticated Color Picker:** Includes SV (Saturation/Value) map, Hue slider, RGB/Hex inputs, and "My Colors" swatches for saving favorite colors (right-click swatches for options).
*   **Static Color Layouts:** Create, save, load, and manage static color presets for the entire 4x16 pad grid.
*   **Frame-by-Frame Pad Animation Sequencer ("Animator Studio"):**
![Image](https://github.com/user-attachments/assets/bd3e8232-df5d-4a1d-ba4b-05975b16d59b)
    *   Visual timeline for arranging frames (supports multi-selection).
    *   Add (snapshot/blank), delete, duplicate, copy, cut, and paste frames.
    *   Undo/Redo functionality for frame edits and sequence property changes.
    *   Control animation speed (FPS) and looping.
    *   Integrated sequence file management: Save, load, create new, and delete animation sequences (user, prefab, sampler-recorded).
*   **Interactive Screen Sampler ("Ambient Mode"):**
    *   Visually select a region on any connected monitor using a resizable and snappable selection box.
    *   Dropdown to select the target monitor for sampling.
    *   Live preview of the sampled region within the configuration dialog.
    *   Adjust Saturation, Contrast, Brightness, and Hue Shift for the sampled colors. These settings are saved per monitor.
    *   Colors from the selected screen region are reflected onto the Akai Fire pads.
*   **Sampler Recording:**
    *   Record the output of the screen sampler over a sequence of frames.
    *   Automatically save the recording as a new animation sequence into a dedicated user folder.
*   **Advanced OLED Display Customization (New & Enhanced!):**
    *   **OLED Content Library Manager:**
        *   Create, edit, and manage a library of custom OLED content items.
        *   Supports two main item types: "Text Items" and "Image Animation Items."
        *   Save items as JSON presets in user-accessible "Documents" subfolders.
        *   Live preview area within the dialog for selected/edited items (including playing animations).
        <!-- Placeholder for OLED Customizer Dialog screenshot -->
        <!-- Suggested: ![OLED Customizer Dialog](link_to_oled_customizer_dialog.png) -->
    *   **Custom Text Items:**
        *   Define text content, select system fonts, set font size.
        *   Configure alignment (left, center, right) for static text.
        *   Enable scrolling for long text, with options to override global scroll speed and set end-pause durations.
    *   **Custom Image & GIF Animations:**
        *   Import various static image formats (PNG, JPG, BMP) and animated GIFs.
        *   Image processing options:
            *   Resize modes: Stretch, Fit (Keep Aspect & Pad), Crop to Center.
            *   Contrast adjustment.
            *   Color inversion.
            *   Monochrome conversion with multiple dithering algorithms: Floyd-Steinberg, Simple Threshold (adjustable), Ordered Dither (Bayer 4x4).
        *   Set target playback FPS and loop behavior (Loop Infinitely, Play Once) for animations on the OLED.
    *   **"Active Graphic" System:**
        *   Select any custom Text Item or Image Animation Item from your library to be the persistent "Active Graphic."
        *   This Active Graphic automatically displays on the OLED after the initial hardware boot-up sequence.
    *   **Built-in Visual Startup:** A fixed, dynamic visual animation plays on the OLED upon MIDI connection before transitioning to the Active Graphic.
    *   **Temporary System Messages:**
        *   Robust system for displaying transient feedback (e.g., knob turns, sampler status, UI navigation cues).
        *   Uses a clear, large "TomThumb" 60pt retro font for high visibility.
        *   Messages display briefly (scrolling if necessary) and then gracefully revert to the user's chosen "Active Graphic" (or application default).
    *   **Application Default Message:** If no Active Graphic is set, a scrolling "Fire RGB Customizer by Reg0lino =^.^=" message (TomThumb 60pt) displays.
*   **Hardware Integration & Contextual Control:**
    *   Connects to the Akai Fire via MIDI, with port selection and auto-detection.
    *   **Dynamic Knob Control:** Top hardware knobs (Volume, Pan, Filter, Resonance) change function based on context:
        *   **Global Mode:** Knob 1 controls global physical pad brightness. Knobs 2-4 are currently unassigned globally.
        *   **Sampler Active Mode:** Knobs 1-4 control Sampler Brightness, Saturation, Contrast, and Hue Shift respectively.
        *   **Animator Playing Mode:** Knob 4 controls animation playback speed (FPS).
    *   **OLED Feedback for Hardware Actions:** Knobs provide real-time value feedback on the OLED using the TomThumb font. Sampler ON/OFF, animator Play/Pause/Stop, and UI navigation cues also show temporary messages.
    *   **Hardware Button Mapping:**
        *   Physical BROWSER/PERFORM buttons toggle the screen sampler ON/OFF.
        *   Physical DRUM button cycles through available monitors for the screen sampler.
        *   GRID L/R buttons cycle focus for on-screen list navigation (Animator sequences, Static Layouts).
        *   SELECT Encoder navigates items within the focused list and SELECT press applies/loads the item.
        *   PATTERN UP/DOWN buttons cycle through cued OLED items (Text/Animation from user library).
        *   BROWSER button (when not toggling sampler due to context) activates the currently cued OLED item as the "Active Graphic."
*   **Modern UI:** Dark-themed and user-friendly interface using PyQt6 and QSS styling.
*   **Persistent User Settings:**
    *   Color picker swatches.
    *   Screen sampler configurations (region, adjustments per monitor).
    *   OLED customization settings (selected Active Graphic path, global scroll speed, cued items).
    *   All saved to platform-specific user configuration directories.
*   **Global Hotkeys:** Standard shortcuts for common operations (Undo/Redo, Copy/Cut/Paste for animator, etc.).

## 🛠️ Technology Stack

*   **Language:** Python 3 (developed with 3.13)
*   **GUI Framework:** PyQt6
*   **MIDI Communication:** `python-rtmidi` (via `mido`)
*   **Screen Capture:** `mss`
*   **Image Manipulation:** `Pillow (PIL)`, `NumPy` (for some dithering)
*   **Configuration & Presets:** JSON
*   **Styling:** QSS
*   **User Directory Management:** `appdirs`
*   **Packaging:** `PyInstaller`

## 🚀 Getting Started (Standalone Executable - Windows)

<!-- 
1.  Go to the [**Releases**](https://github.com/Reg0lino/AKAI-Fire-RGB-Controller/releases) page of this repository.
2.  Download the latest `AkaiFireControllerApp.exe` file.
3.  Ensure your Akai Fire controller is connected to your PC.
4.  Run `AkaiFireControllerApp.exe`. (You might need to "unblock" the file in its properties if Windows SmartScreen flags it).
-->

## ⚙️ Setup & Installation (From Source - For Developers)

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/Reg0lino/AKAI-Fire-RGB-Controller.git
    cd AKAI-Fire-RGB-Controller
    ```
2.  **Create and activate a virtual environment (highly recommended):**
    *   Create: `python -m venv .venv` (or your preferred venv name, e.g., `c:\venvs\akai_fire_build_venv`)
    *   Activate (Windows CMD): `.\.venv\Scripts\activate.bat`
    *   Activate (Windows PowerShell): `.\.venv\Scripts\Activate.ps1` (May require `Set-ExecutionPolicy RemoteSigned -Scope CurrentUser`)
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
    Or, on Windows, you can use `FIRE_RGB.bat` (included in the project root) to launch.

## 📂 Project Structure (Key Files)

```
AKAI_Fire_RGB_Controller/
├── animator/               # Animator-specific logic & UI components
├── features/               # Screen sampler core & thread logic
├── gui/                    # Main GUI components (MainWindow, dialogs, UI managers)
├── hardware/               # Akai Fire MIDI communication layer (akai_fire_controller.py)
├── managers/               # Higher-level logic managers (hardware_input_manager.py, oled_display_manager.py)
├── oled_utils/             # OLED image processing and rendering utilities
├── presets/                # Default/prefab static layouts and animation sequences (bundled with app)
├── resources/              # Fonts (e.g., TomThumb.ttf), Icons, Stylesheets (QSS)
├── utils.py                # Utility functions (e.g., get_resource_path)
├── user_settings/          # (Dev only for some configs) Local user configs (e.g. oled_config.json)
│                           # Bundled app uses platform-specific appdirs location for most user configs.
├── fire_control_app.py     # Main application entry point
├── AkaiFireControllerApp.spec # PyInstaller specification file
├── README.md
├── CHANGELOG.md
├── LICENSE
├── requirements.txt
└── .gitignore
```
User-generated presets (Static Layouts, Animator Sequences, OLED Text Items, OLED Image Animations) are saved in a dedicated folder within the user's "Documents" directory (e.g., `Documents/Akai Fire RGB Controller User Presets/`).

## 🎮 Usage

1.  Launch the application.
2.  Select the "AKAI Fire" MIDI output and input ports (should auto-select if "Fire" is in the name) and click "Connect". A startup animation will play on the OLED.
3.  **OLED Customization:**
    *   Click the OLED mirror on the main GUI (top strip) to open the "OLED Active Graphic Manager."
    *   Create new "Text Items" or "Image Animation Items" using the respective buttons.
    *   Edit their properties (text, font, size, scroll for text; source image/GIF, resize, dither, contrast, FPS for animations).
    *   Save your custom items. They will appear in the "Item Library."
    *   Select an item from the library and choose it from the "Set as Active Graphic" dropdown to make it your default OLED display.
    *   Use the "Save & Apply" button to save an edited item and immediately set it as the Active Graphic.
    *   The "Global Scroll Speed" slider affects text items that don't have their own speed override.
    <!-- Placeholder for OLED in action on hardware -->
    <!-- Suggested: ![Custom OLED Text Example](link_to_custom_text_on_fire.jpg) -->
    <!-- Suggested: ![Custom OLED Animation Example](link_to_custom_animation_on_fire.jpg) -->
4.  **Pad Control & Animation:**
    *   Use the **Color Picker** to select colors.
    *   Apply **Static Pad Layouts**.
    *   Use the **Animator Studio** to create and manage frame-by-frame animations.
5.  **Screen Sampler (Ambient Mode):**
![Image](https://github.com/user-attachments/assets/0fc30392-e115-4352-b988-a7b7965f5215)
    *   Toggle ON/OFF using the UI button or hardware PERFORM/BROWSER buttons.
    *   Configure the sampling region and color adjustments. Hardware knobs control adjustments when active.
    *   Use the **Record** feature to save sampler output as an animation.
6.  **Hardware Controls:** Utilize the top knobs and buttons for contextual control over brightness, sampler parameters, animation speed, and OLED navigation/selection as described in Features.

## 📝 TODO / Future Enhancements

*   Additional dithering algorithms (e.g., Atkinson) for OLED image processing.
*   More advanced animation editing features (interpolation, effects).
*   Refined UI/UX for OLED item management.
*   Enhanced MIDI input mapping for triggering application functions.
*   More prefab content (pad animations, OLED items).
*   Cross-platform testing and official packaging for macOS and Linux.
*   Investigate performance for very long/complex OLED animations (e.g., Base64 frame storage).

## ⚖️ License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgements

*   The developers of PyQt, Pillow, python-rtmidi, mido, mss, appdirs, and NumPy.
*   The Akai Pro team for creating the Fire controller.
*   The SEGGER Blog that provided initial insights into Fire's OLED SysEx commands.
*   AI Assistants (Gemini models from Google) for extensive assistance with coding, debugging, refactoring, planning, and documentation throughout all stages of this project.

---
*Developed by Reg0lino (RegularRegs)*
```
