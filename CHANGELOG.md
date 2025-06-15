# Changelog - Akai Fire PixelForge

## [Internal Build] - June 15, 2025

This major internal build represents a significant push in both new feature development and user experience refinement. It completes the core implementation of all planned Audio Visualizer modes, introduces a major UI/UX overhaul for key interface elements like the top "Device Controls" strip, and includes numerous stability fixes that address a cascade of bugs discovered during the iterative process.

### ✨ NEW FEATURES & ENHANCEMENTS

*   **Audio Visualizer - "Dual VU + Spectrum" Mode (Phase 2 Complete):**
    *   **Core Logic (`AudioVisualizerManager`):** The "Dual VU" mode is now fully implemented.
        *   The central 10 columns of the pad grid now render a 5-band audio spectrum, working in concert with the two VU meters on the sides.
        *   The logic for calculating the 5-band powers now uses its own dedicated sensitivity and smoothing factors, making it fully independent from the "Classic Spectrum Bars" mode.
        *   The `_calculate_n_band_powers` utility method was refactored to accept an optional `sensitivity_override` parameter, making it a more robust and reusable function.
    *   **UI & Settings (`VisualizerSettingsDialog`):** The "🎶 Dual VU + Spectrum" tab is now feature-complete.
        *   The "Central Spectrum Settings" group box is now active, providing 5 `ColorGradientButton`s for band colors, a "Sensitivity" slider, a "Smoothing Factor" slider, and a "Grow Bars Downwards" checkbox, all specific to the central spectrum.
        *   The "Scheme Palette Management" group box is now fully functional. Users can save, load, and delete comprehensive "schemes" (which are presets containing all VU meter *and* central spectrum settings together). This uses a `QComboBox` for a clean, integrated preset selection experience.
        *   All new settings are correctly persisted to and loaded from the user's configuration files.

*   **Audio Visualizer - "Pulse Wave" Mode Enhancement:**
    *   The pulse visualization in `_map_pulse_wave_to_pads` has been visually enhanced. It now renders with a soft "fade" effect, where the columns immediately adjacent to the main pulse light up with reduced brightness, creating a smoother and more appealing visual.

*   **Audio Visualizer - Expanded Prefab Palettes:**
    *   Greatly expanded the creative options for the "Classic Spectrum Bars" mode by adding 8 new built-in prefab palettes.
    *   New additions include: **"DOOM Inferno"**, **"Grayscale"**, **"Cool Blues"**, **"Matrix Code"**, **"Retro Sunset"**, **"Emerald Depths"**, **"Pastel Dreams"**, and **"Cyberpunk Neon"**, each with a unique color scheme and tailored sensitivity/smoothing settings.

*   **Main Window UI/UX Overhaul:**
    *   **"Device Controls" Strip Redesign:** The entire top strip has been rebuilt for professional appearance and stability.
        *   **Custom-Rendered Knobs:** Replaced the default system `QDial` widgets with a custom-drawn `StaticKnobWidget`. This provides a consistent, dark, "look-alike" appearance that is immune to style changes upon connecting the controller, changing application modes, or being disabled. The new visual is decoupled from the underlying functional `QDial`.
        *   **Dynamic Knob Labels:** Added text labels ("Brightness", "Saturation", "Hue", "Speed", "Select") beneath each of the top 5 hardware knobs. These labels dynamically appear, change, or become blank (`""`) based on the current application context (Global, Sampler, or Animator Playing), providing clear, at-a-glance feedback on knob function.
        *   **Layout & Alignment:** The layout logic was completely reworked multiple times, culminating in a stable structure that perfectly centers all knobs and controls vertically, resolving all previous alignment and overlapping issues.
        *   **Enhanced User Feedback:** Implemented dynamic tooltips for all hardware knobs that update with their current function and value. Added descriptive status bar messages that appear when knob functions change (e.g., "Knobs now control Sampler..."), improving overall usability.
    *   **"Global Controls" Widget:**
        *   Added a new "Global Controls" `QGroupBox` to the right-hand panel, providing an explicit, always-visible `QSlider` for "Global Pad Brightness".
        *   This slider is intelligently enabled/disabled based on context (e.g., it is greyed out when the Screen Sampler or Audio Visualizer is active).
        *   The slider, the physical brightness knob, and the GUI knob visual are now all perfectly synced.
    *   **Audio Visualizer Control Panel:**
        *   The `AudioVisualizerUIManager` widget was redesigned from a simple vertical stack to a clean, two-row grid layout, resolving all widget overlapping issues.
        *   The "Enable Visualizer" button was changed to a stateful toggle button (`▶ Enable` / `⏹️ Disable`) with QSS styling for better visual feedback.
    *   **Live Visualizer Settings:** The application now allows the `VisualizerSettingsDialog` to be opened while the visualizer is running, enabling real-time tweaking of colors, sensitivity, and other parameters. The `MainWindow`'s UI state logic was updated to keep the `Setup...` button enabled during visualization while correctly disabling disruptive controls (audio source, mode).

### 🐛 BUG FIXES & STABILITY

*   **Fixed All Knob-Related Crashes and Bugs:**
    *   Systematically eliminated a cascade of `AttributeError` and `TypeError` crashes that occurred when interacting with knobs after refactoring the UI. This was caused by lingering references to old `gui_knobX` alias attributes, which have now all been removed.
    *   Resolved a critical logic flaw where programmatic `setValue()` calls during context switches would trigger `valueChanged` signals, causing spurious OLED feedback and preventing GUI mouse interaction from working. The fix involved blocking signals during configuration updates.
    *   Corrected the `StaticKnobWidget`'s `paintEvent` to ensure knob indicators and tick marks are oriented correctly (12 o'clock "zero" position).
    *   Restored full functionality to all physical knobs and the new global brightness slider, ensuring they correctly control their assigned parameters and that all visual elements stay in sync.
*   **Fixed `VisualizerSettingsDialog` Bugs:**
    *   Resolved an issue where the "Scheme Preset" `QComboBox` on the "Dual VU" tab was not populating or updating correctly after saving a new scheme.
    *   Fixed multiple `AttributeError` and `TypeError` crashes that occurred when opening the settings dialog due to incorrect widget references and method calls during initialization.
*   **Fixed `MainWindow` Layout & Initialization:**
    *   Resolved multiple critical layout bugs in the top "Device Controls" strip that caused widgets to overlap, disappear, or align incorrectly. The final implementation uses a robust and predictable layout structure.
    *   Corrected several `AttributeError` and `TypeError` crashes during application startup caused by incorrect initialization order of various attributes and UI components.

---

## [Version 1.0.1] - June 8, 2025

This version introduced a significant overhaul and initial detailed implementation of the Audio Visualizer feature, focusing on the "Classic Spectrum Bars" mode, robust settings management, and user profile/prefab support.

*   **NEW FEATURE: Advanced Audio Visualizer - Classic Spectrum Bars (Part 1):**
    *   **Core Visualization Engine (`AudioVisualizerManager`):** Successful audio capture from loopback devices (`pyaudiowpatch`), FFT processing, 8-band power calculation, and mapping to the Akai Fire pad grid.
    *   **Comprehensive Settings Management (`AudioVisualizerManager`):** Introduced `all_mode_settings_cache` for all visualizer modes, persisted to `visualizer_main_settings.json`.
    *   **Detailed Settings Dialog (`VisualizerSettingsDialog`):** A new dialog with a dedicated tab for "Spectrum Bars" providing UI for individual bar colors, sensitivity, and smoothing. Implemented an integrated palette management system with support for user-saved profiles and built-in prefab palettes.
    *   **Main Application Integration:** `AudioVisualizerUIManager` added to the main window for device/mode selection and visualizer activation. Implemented robust state management using signals for starting/stopping the capture thread.
*   **BUG FIXES & STABILITY (Audio Visualizer):**
    *   Resolved critical key mismatches that prevented settings from being applied.
    *   Corrected profile list update logic in the settings dialog.
    *   Fixed premature stopping of the audio processing thread.

---

## [Version 1.0.0] - June 5, 2025

This landmark v1.0.0 release introduced the highly anticipated **"LazyDOOM" on OLED** feature and finalized the advanced OLED image processing pipeline.

*   **NEW FEATURE: LazyDOOM on OLED! 👹:**
    *   A fully playable, DOOM-themed first-person raycaster game running on the Akai Fire's 128x64 OLED display.
    *   Features procedural map generation, combat mechanics, and selectable difficulty levels.
    *   Includes deep hardware integration with pad-based controls and RGB feedback for health and game events.
*   **OTHER FEATURES & ENHANCEMENTS (v1.0.0):**
    *   **Advanced OLED Image Processing & Dithering Finalized:** The full suite of image processing tools (Gamma, Blur, Sharpen, Noise, new Dithering algorithms) was stabilized and fully integrated into the `OLEDCustomizerDialog`.
    *   **UI/UX Refinements:** Restructured the `OLEDCustomizerDialog` for better usability and improved the appearance of various UI elements.
*   **BUG FIXES & STABILITY (v1.0.0):**
    *   Fixed a critical initialization bug in the `OLEDCustomizerDialog` that prevented the item library from functioning correctly.

---

## Previous Versions (Pre-v1.0.0 Summary)

*   **v0.9.x Releases:** Focused on experimental features that would be stabilized in v1.0.0, including advanced OLED dithering options and the initial integration of the LazyDOOM game. Major work was done on improving the usability of the `OLEDCustomizerDialog`, optimizing Animator Studio performance, and fixing numerous UI/signal handling bugs.
*   **v0.8.0 & v0.7.0:** Focused on stabilizing the Screen Sampler, implementing persistent user settings for the sampler and color picker, and adding "My Colors" swatch management.
*   **Pre-v0.7.0:** Initial development phases, including the creation of the core Animator Studio, the first MVP of the Screen Sampler, and major refactoring efforts to establish the modular architecture of the application.

---
*Akai Fire PixelForge - Developed by Reg0lino with extensive AI assistance from Gemini models.*