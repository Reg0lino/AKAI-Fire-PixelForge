====================================================
 AKAI FIRE PIXELFORGE - README & QUICK GUIDE
====================================================
Version: 1.7.0
Release Date: 2025-06-21
Project by: Reg0lino
GitHub: https://github.com/Reg0lino/AKAI-Fire-PixelForge
----------------------------------------------------

Thank you for downloading Akai Fire PixelForge!

** IMPORTANT: ANTIVIRUS / WINDOWS SMARTSCREEN NOTICE **
----------------------------------------------------
Because this software is from an independent developer and is not digitally signed, your antivirus or Windows SmartScreen might show a warning when you run the installer or the application.

*   **This is usually a false positive.** The application is safe if downloaded from the official GitHub Releases page.
*   **Why does this happen?** The app is bundled using standard tools (PyInstaller), and it legitimately saves your custom presets to your "My Documents" folder, which some security programs monitor closely.
*   **What to do:**
    *   On Windows SmartScreen: Click "More info," then "Run anyway."
    *   For Antivirus: Please choose to "Allow" the action or "Trust" the application.

Thank you for your understanding!

----------------------------------------------------
🚀 WHAT IS AKAI FIRE PIXELFORGE?
----------------------------------------------------
PixelForge transforms your Akai Fire controller into a dynamic visual instrument.
It allows you to:
*   Paint directly onto the 4x16 RGB pads.
*   Use the real-time Audio Visualizer to turn your computer's sound into a light show.
*   Create and play frame-by-frame pad animations in the "Animator Studio."
*   Apply non-destructive, real-time Color Grading & FX (Brightness, Saturation, Contrast, Hue) to all visual output.
*   Use the Screen Sampler to reflect colors from your desktop onto the pads.
*   Customize the 128x64 OLED screen with custom text, images, and animated GIFs.
*   Play "LazyDOOM," a retro first-person shooter, directly on your Akai Fire's OLED!

----------------------------------------------------
⚙️ GETTING STARTED (AFTER INSTALLATION)
----------------------------------------------------
1.  **Connect Your Akai Fire:** Ensure your controller is plugged into your PC.
2.  **Launch Akai Fire PixelForge:** Use the Start Menu or Desktop shortcut.
3.  **MIDI Connection:**
    *   The app should auto-select the "FL STUDIO FIRE" port.
    *   The "Connect" button will be animated. Click it.
    *   A startup visual should play on your Fire's OLED, and the button will change to "Disconnect."
4.  **Explore!**
    *   **App Guide:** Click the "🚀 App Guide" button on the top-right of the menu bar for a full tour and a list of all controls & hotkeys!
    *   **Color Picker:** Select a primary (left-click) and secondary (right-click) color.
    *   **Animator Studio:** Click "New" to start a new animation, add frames, and start painting.
    *   **Screen Sampler:** In the bottom-left panel, click "Screen Sampling" to toggle it on.
    *   **Audio Visualizer:** In the right panel, select your main audio device (e.g., Speakers Loopback) and click "▶ Enable Visualizer" to start the show!
    *   **LazyDOOM:** In the bottom-left panel, click the "👹 Launch LazyDOOM" button to start the game!

----------------------------------------------------
✨ KEY FEATURES & HOW TO USE THEM (v1.7.0)
----------------------------------------------------

**Color Grading / FX (NEW!):**
*   Located in the right-hand panel, this allows you to apply real-time, non-destructive Brightness, Saturation, Contrast, and Hue effects to all pad visuals.
*   Click the "Enable Color FX" checkbox to turn it on.
*   Click "Apply to Selected Frames" to permanently "bake in" the effects to your animation.

**Audio Visualizer:**
*   **How to Use:** Select your main sound device (usually a "Loopback" or "Stereo Mix") from the "Source" dropdown and click "▶ Enable Visualizer".
*   **Live Settings:** Click the "Setup..." button to open a dialog where you can tweak all settings IN REAL TIME.
*   **Modes:** Classic Spectrum Bars, Pulse Wave, or Dual VU + Spectrum.

**LazyDOOM Game Mode:**
*   Launch via the "👹 Launch LazyDOOM" button in the bottom-left panel.
*   READ the Instructions Dialog that appears for controls and objectives!
*   Use Akai Fire pads or your keyboard (WASD) for full control.

**Advanced OLED Customization:**
*   **Access:** Click the on-screen OLED mirror or go to `Tools > OLED Display > Customize OLED...`
*   **Image/GIF Processing:** When importing, explore options for Brightness, Contrast, Gamma, Sharpen, and multiple Dithering algorithms.
*   **Active Graphic:** Set your favorite creation as the default OLED display.
*   **Export to GIF:** Export your custom OLED animations as GIFs from the `File` menu.

**Hardware Controls (Summary - See App Guide for full details):**
*   **Top Knobs:** Context-sensitive. They control Sampler parameters, Animator Speed, or the main Color FX. The OLED provides real-time feedback.
*   **PERFORM / BROWSER button:** Toggles the Screen Sampler.
*   **DRUM button:** Cycles through monitors for the Screen Sampler.
*   **NOTE button:** Toggles the Audio Visualizer.
*   **STEP button:** Toggles the "Enable Color FX" checkbox.
*   **PATTERN UP/DOWN buttons:** Cycles through your saved OLED Active Graphics.
*   **GRID L/R & SELECT Knob/Press:** Used for navigating and selecting items in the Animator and Static Layouts panels.

----------------------------------------------------
🚧 KNOWN ISSUES / FUTURE
----------------------------------------------------
This version is feature-complete. Future work will focus on maintenance, bug fixes, and performance optimization.

----------------------------------------------------
⚖️ LICENSE
----------------------------------------------------
This project is licensed under the MIT License. See the LICENSE file for details.