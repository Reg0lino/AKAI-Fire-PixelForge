====================================================
 PIXELFORGE FOR AKAI FIRE - README & QUICK GUIDE
====================================================
Version: 2.0.0
Release Date: 07-05-2025
Project by: Reg0lino
GitHub: https://github.com/Reg0lino/AKAI-Fire-PixelForge
----------------------------------------------------

Thank you for downloading PixelForge for Akai Fire!

** IMPORTANT: ANTIVIRUS / WINDOWS SMARTSCREEN NOTICE **
----------------------------------------------------
Because this software is from an independent developer and is not digitally signed, your antivirus or Windows SmartScreen might show a warning when you run the installer or the application.

*   This is usually a false positive. The application is safe if downloaded from the official GitHub Releases page.
*   Why does this happen? The app is bundled using standard tools (PyInstaller), and it legitimately saves your custom presets to your "My Documents" folder, which some security programs monitor closely.
*   What to do:
    *   On Windows SmartScreen: Click "More info," then "Run anyway."
    *   For Antivirus: Please choose to "Allow" the action or "Trust" the application.

Thank you for your understanding!

----------------------------------------------------
🚀 WHAT IS PIXELFORGE FOR AKAI FIRE?
----------------------------------------------------
PixelForge transforms your Akai Fire controller into a dynamic visual instrument.
It allows you to:
*   Import GIFs from your computer or the web to create complex animations.
*   Paint directly onto the 4x16 RGB pads.
*   Use the real-time Audio Visualizer to turn your computer's sound into a light show.
*   Apply non-destructive, real-time Color Grading & FX to all visual output.
*   Use the Screen Sampler to reflect colors from your desktop onto the pads.
*   Customize the 128x64 OLED screen with custom text, images, and animated GIFs.
*   Play "LazyDOOM," a retro first-person shooter, directly on your Akai Fire's OLED!

----------------------------------------------------
⚙️ GETTING STARTED (AFTER INSTALLATION)
----------------------------------------------------
1.  **Connect Your Akai Fire:** Ensure your controller is plugged into your PC.
2.  **Launch PixelForge for Akai Fire:** Use the Start Menu or Desktop shortcut.
3.  **MIDI Connection:**
    *   The app should auto-select the "FL STUDIO FIRE" port.
    *   The "Connect" button will be animated. Click it.
    *   A startup visual should play on your Fire's OLED, and the button will change to "Disconnect."
4.  **Explore!**
    *   **App Guide:** Click the "🚀 App Guide" button on the top-right of the menu bar for a full tour and a list of all controls & hotkeys!
    *   **Color Picker:** Select a primary (left-click) and secondary (right-click) color.
    *   **Animator Studio:** Use the dropdown to manage your animations, or click "GIF Import" to start creating from a GIF.
    *   **Screen Sampler:** In the bottom-left panel, click "Screen Sampling" to toggle it on.
    *   **Audio Visualizer:** In the right panel, select your main audio device and click "▶ Enable Visualizer".
    *   **LazyDOOM:** In the bottom-left panel, click the "👹 Launch LazyDOOM" button to start the game!

----------------------------------------------------
✨ KEY FEATURES & HOW TO USE THEM (v2.0.0)
----------------------------------------------------

**GIF Importer (NEW!):**
*   Click the "GIF Import" button in the Animator Studio to open the importer.
*   Load a GIF from a local file or paste a URL.
*   Click and drag on the main preview to select a region to sample.
*   Use the sliders to adjust colors and speed in real-time. The hardware pads will mirror your changes live!

**Audio Visualizer:**
*   **How to Use:** Select your main sound device (usually a "Loopback" or "Stereo Mix") and click "▶ Enable Visualizer".
*   **Live Settings:** Click the "Setup..." button to open a dialog where you can tweak all settings IN REAL TIME.

**Screen Sampler (Ambient Mode):**
*   **How to Use:** Click "Screen Sampling" to start. Use the "Mode" dropdown to choose between different algorithms like "Thumbnail" for a fast screen mirror or "Region" for precise selection.
*   **Hardware Control:** Toggle with `PERFORM`, cycle monitors with `DRUM`, and cycle modes with `NOTE`.

**Hardware Controls (Summary - See App Guide for full details):**
*   **Top Knobs:** Context-sensitive. They control Sampler parameters, Animator Speed, or the main Color FX. The OLED provides real-time feedback.
*   **SELECT Knob/Press:** Used for navigating and selecting items in the Animator and Static Layouts panels.

----------------------------------------------------
🚧 KNOWN ISSUES / FUTURE
----------------------------------------------------
This version is feature-complete. Future work will focus on maintenance, bug fixes, and performance optimization.

----------------------------------------------------
⚖️ LICENSE
----------------------------------------------------
This project is licensed under the MIT License. See the LICENSE file for details.