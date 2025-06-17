# Changelog - Akai Fire PixelForge

## [Version 1.5.0] - June 17, 2025

This major release completes the powerful Audio Visualizer feature, overhauls the Color Picker with a professional primary/secondary color system, and introduces a significant UI/UX redesign of core components like the top "Device Controls" strip. This version represents a substantial leap forward in both creative features and application stability.

### ✨ NEW FEATURES & ENHANCEMENTS

*   **Advanced Audio Visualizer (Feature Complete):**
    *   **"Dual VU + Spectrum" Mode:** The final visualizer mode is now fully implemented. It features two VU meters on the sides and a central 5-band audio spectrum, each with its own independent settings for colors, sensitivity, and smoothing.
    *   **"Pulse Wave" Mode Enhancement:** The visualization has been visually enhanced with a soft "fade" effect on adjacent columns for a smoother look.
    *   **Expanded Prefab Palettes:** Added 8 new creative, built-in color palettes for the "Classic Spectrum Bars" mode, including "DOOM Inferno", "Matrix Code", and "Cyberpunk Neon".
    *   **Live Settings:** The `Setup...` dialog can now be opened while the visualizer is running, allowing for real-time tweaking of all parameters.

*   **Color Picker Overhaul (Primary/Secondary Colors):**
    *   The painting workflow has been upgraded to a professional **Primary (Left-Click)** and **Secondary (Right-Click)** color system.
    *   The Color Picker UI has been redesigned with a new interactive color well to show and select the active color, and a `⇄` button to instantly swap them.
    *   The overall layout of the widget has been significantly improved for a more compact, logical, and polished appearance.

*   **Main Window UI/UX Overhaul:**
    *   **"Device Controls" Strip Redesign:** The entire top strip has been rebuilt for a professional look and stability using custom-rendered knob widgets that are immune to system style changes.
    *   **Global Controls Panel:** Added a new `QGroupBox` on the right-hand panel with a dedicated `QSlider` for "Global Pad Brightness," which is perfectly synced with the physical hardware knob.
    *   **Enhanced User Feedback:** Implemented dynamic tooltips for hardware knobs that update with their current function and value.

### 🐛 BUG FIXES & STABILITY

*   **Fixed All Knob-Related Crashes and Bugs:** Systematically eliminated a cascade of crashes that occurred when interacting with the top-strip knobs. Resolved logic flaws that caused spurious OLED feedback and prevented GUI interaction.
*   **Fixed Color Picker Functionality:**
    *   Resolved a critical bug where the color picker UI (SV-picker, sliders, input fields) would not update in real-time as a color was being changed.
    *   Fixed an issue where moving the SV-picker would incorrectly cause the Hue slider to flicker or jump ("cross-talk").
    *   Corrected tooltip styling to ensure consistent, readable tooltips for all color picker elements, especially the swap button and color swatches.
*   **Fixed `VisualizerSettingsDialog` Bugs:** Resolved issues with preset management and initialization crashes in the audio visualizer settings.
*   **Fixed `MainWindow` Layout & Initialization:** Resolved multiple critical layout bugs and `AttributeError` crashes during application startup.

---

## [Version 1.0.1] - June 8, 2025

This version introduced a significant overhaul and initial detailed implementation of the Audio Visualizer feature, focusing on the "Classic Spectrum Bars" mode, robust settings management, and user profile/prefab support.

*   **NEW FEATURE: Advanced Audio Visualizer - Classic Spectrum Bars (Part 1):**
    *   **Core Visualization Engine (`AudioVisualizerManager`):** Successful audio capture from loopback devices, FFT processing, 8-band power calculation, and mapping to the Akai Fire pad grid.
    *   **Comprehensive Settings Management (`AudioVisualizerManager`):** Introduced `all_mode_settings_cache` for all visualizer modes, persisted to `visualizer_main_settings.json`.
    *   **Detailed Settings Dialog (`VisualizerSettingsDialog`):** A new dialog with a dedicated tab for "Spectrum Bars" providing UI for individual bar colors, sensitivity, and smoothing. Implemented an integrated palette management system.
    *   **Main Application Integration:** `AudioVisualizerUIManager` added to the main window for device/mode selection and visualizer activation.
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
*   **OTHER FEATURES & ENHANCEMENTS (v1.0.0):**
    *   **Advanced OLED Image Processing & Dithering Finalized:** The full suite of image processing tools (Gamma, Blur, Sharpen, Noise, new Dithering algorithms) was stabilized and fully integrated into the `OLEDCustomizerDialog`.
*   **BUG FIXES & STABILITY (v1.0.0):**
    *   Fixed a critical initialization bug in the `OLEDCustomizerDialog` that prevented the item library from functioning correctly.

---

## Previous Versions (Pre-v1.0.0 Summary)

*   **v0.9.x Releases:** Focused on experimental features that would be stabilized in v1.0.0, including advanced OLED dithering options and the initial integration of the LazyDOOM game.
*   **v0.8.0 & v0.7.0:** Focused on stabilizing the Screen Sampler, implementing persistent user settings for the sampler and color picker, and adding "My Colors" swatch management.
*   **Pre-v0.7.0:** Initial development phases, including the creation of the core Animator Studio, the first MVP of the Screen Sampler, and major refactoring efforts to establish the modular architecture of the application.

---
*Akai Fire PixelForge - Developed by Reg0lino with extensive AI assistance from Gemini models.*