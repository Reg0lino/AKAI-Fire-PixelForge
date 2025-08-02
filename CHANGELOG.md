# Changelog - PixelForge for Akai Fire

## [Version 2.1.0] - August 2, 2025

This is a critical quality-of-life and stability release that resolves a long-standing bug preventing real-time animation speed control. The core logic for how the animator panel interacts with the main window and hardware has been refactored to be more robust, responsive, and intuitive, perfecting the workflow introduced in v2.0.0.

### ✨ **NEW FEATURES & ENHANCEMENTS**

*   **Animator Workflow & Usability Enhancements:**
    *   The on-screen **`Speed` slider** in the Animator Studio is now **fully interactive and unlocked** during animation playback, allowing for real-time speed adjustments with the mouse.
    *   The physical `SELECT` knob's on-screen label now correctly and instantly changes from `Select` to **`Speed`** the moment playback begins.
    *   The knob's visual indicator now correctly initializes to the current animation speed, preventing the "snapping" effect on the first turn.
    *   The physical knob now provides correct, real-time FPS feedback on the OLED display during playback.

### 🐛 **BUG FIXES & STABILITY**

*   **CRITICAL: Fixed Animator Speed Control Regression:**
    *   Resolved a deep-seated architectural flaw where the main window's global UI update would incorrectly override the animator's local UI state during playback.
    *   Fixed a broken signal connection between the `SequenceModel` and the `AnimatorManagerWidget`, which was the root cause of the UI failing to update automatically on playback state changes.
    *   Refactored the animator's UI update logic into a direct, brute-force call chain, bypassing the failing signal/slot system and ensuring the UI state is always correct and responsive.
*   **Fixed Conflicting Hardware Feedback:**
    *   Resolved an issue where turning the `SELECT` knob during playback would incorrectly display "idle" navigation feedback (the sequence name) on the OLED screen. It now correctly displays the current animation FPS.

---

## [Version 2.0.0] - July 5, 2025

This is a release that introduces a **GIF Importer for Pads**, allowing users to create complex animations from existing GIFs with ease. This version also includes a major overhaul of the Animator Studio's sequence management system, making it far more robust and intuitive. A cascade of critical bug fixes for application startup, state management, and UI logic have been resolved, resulting in the most stable and feature-rich version of PixelForge.

### ✨ **NEW FEATURES & ENHANCEMENTS**

*   **NEW: GIF Importer for Pad Animations:**
    *   A new `GIF Import` button in the Animator Studio opens a powerful new dialog.
    *   Load GIFs from a local file or directly from a URL.
    *   Visually select a region of the GIF to sample using a draggable and resizable selection box.
    *   Pre-process the GIF with real-time controls for Brightness, Saturation, Contrast, and Hue.
    *   Override the GIF's native speed with a custom FPS slider.
    *   A "Live Pad Preview" shows the final 16x4 output, including a live mirror on the physical hardware pads.
    *   Includes a "Play Original GIF" button to open the source GIF in a separate player for easy reference.
    *   Includes a "Download GIF" button to save a local copy of a GIF loaded from a URL.
*   **NEW: Animator Sequence Management Overhaul:**
    *   The Animator Studio now features a dropdown menu to browse and load all saved sequences.
    *   The dropdown is automatically populated with `[User]`, `[Sampler]`, and `[Prefab]` sequences.
    *   The dropdown now correctly displays the currently loaded sequence name.
    *   An asterisk (`*`) now appears next to the sequence name in the dropdown to indicate unsaved changes, providing clear visual feedback.
    *   A "Delete" button has been added to allow users to permanently remove sequences from their library.
    *   The "Save As..." dialog has been restored to a more user-friendly name input prompt.

### 🐛 **BUG FIXES & STABILITY**

*   **CRITICAL: Fixed All `AttributeError` Crashes on Startup:**
    *   Completely re-architected the initialization and state management logic within the `AnimatorManagerWidget`.
    *   Resolved a cascade of `AttributeError` and `TypeError` crashes that occurred when loading the application or interacting with the animator UI for the first time.
*   **CRITICAL: Fixed GIF Importer Logic:**
    *   Fixed a `TypeError` in the GIF region selector caused by a `QSize`/`QSizeF` mismatch.
    *   Fixed `IndexError` in the preview rendering logic, ensuring the pad preview now correctly displays the full 16x4 grid.
    *   Fixed an image corruption bug where adjusting sliders would permanently alter the main GIF preview image. The source image is now protected.
    *   Resolved layout bugs that caused the preview area to be sized incorrectly or misaligned on window resize.
    *   Fixed a bug that prevented the "Play Preview" button from working.
*   **Fixed Animator Dropdown State:**
    *   Fixed the bug where loading a sequence would incorrectly reset the dropdown to show "Unsaved New Sequence". The dropdown now correctly selects the name of the loaded sequence.

---

## [Version 1.8.0] - June 1, 2025

This is a major feature and performance release that introduces two new high-performance "Ambient" sampling modes, designed to be extremely fast for use-cases like gaming. This version also includes a significant refactoring of the entire sampler UI and state management system to be more robust, intuitive, and bug-free.

### ✨ **NEW FEATURES & ENHANCEMENTS**

*   **NEW: High-Performance Ambient Sampling Modes:**
    *   The Screen Sampler now features a "Sampling Mode" dropdown to choose between algorithms.
    *   **"Thumbnail (Fast)" Mode:** A new, ultra-fast mode that captures the screen, resizes it to a `16x4` thumbnail, and maps it directly to the pads.
    *   **"Palette (Creative)" Mode:** A new, creative mode that uses `colorthief` to find dominant colors and generate a smooth gradient.
*   **NEW: Dedicated "Ambient Mode" Configuration Dialog:**
    *   A new, streamlined dialog for ambient modes containing only color adjustment sliders.
*   **Major Sampler UI/UX Overhaul:**
    *   Dropdowns are now always enabled, allowing pre-selection of monitor/mode.

### 🐛 **BUG FIXES & STABILITY**

*   **CRITICAL: Fixed Sampler State Management:**
    *   Completely refactored state management to eliminate stale state bugs.
    *   Fixed `AttributeError` crash on sampler start.
*   **CRITICAL: Fixed `ValueError` in Palette Sampling:**
    *   Resolved `numpy` broadcasting error in gradient math.
*   **Fixed Sampler Dialog Resizing:**
    *   Stabilized the `VisualSamplerConfiguration` dialog resizing.

---

## [Version 1.7.0] - Master Stability & Final Polish 

This is a landmark release focused on achieving master-level stability across the entire application and adding the final layer of professional polish before release. It addresses deep architectural flaws in the state management systems, particularly for the OLED display, resulting in a significantly more robust and crash-free user experience. This version also introduces a completely redesigned and comprehensive in-app guide to empower users.

### ✨ **NEW FEATURES & ENHANCEMENTS**

*   **NEW: Blinking/Pulsing "Connect" Button:**
    *   The "Connect" button now features a vibrant, color-shifting animation when the device is disconnected, providing a clear and attractive visual cue to the user.
    *   The animation automatically stops upon successful connection, and the button reverts to a standard "Disconnect" style.

*   **NEW: Top-Level "App Guide" Menu Button:**
    *   The "App Guide & Hotkeys" button has been promoted to a permanent, top-level position on the far right of the main menu bar for high visibility and easy access.

*   **NEW: Comprehensive In-App Guide & Hotkey Reference:**
    *   The App Guide dialog has been completely redesigned with a `QTabWidget` interface.
    *   **"App Guide" Tab:** Contains a fully updated, detailed user manual explaining all major features, including the previously undocumented Audio Visualizer and advanced OLED/Hardware controls.
    *   **"Controls & Hotkeys" Tab:** A new, dedicated "cheat sheet" tab provides a clean, scannable list of all keyboard shortcuts and physical hardware button functions.

*   **NEW: Hardware Button for FX Toggle:**
    *   The "Enable Color FX" checkbox can now be toggled directly from the hardware using the physical `STEP` button.

### 🐛 **BUG FIXES & CRITICAL STABILITY OVERHAUL**

*   **CRITICAL: OLED State Machine Refactor:**
    *   Completely re-architected the `OLEDDisplayManager`'s state machine to eliminate a critical `RecursionError` that caused crashes on disconnect/reconnect and when reverting from temporary messages.
    *   Consolidated all text rendering to use a single, robust "Qt-first" pipeline, fixing all `TypeError` crashes and font-loading failures (e.g., for Wingdings, Stencil). All system fonts now render correctly on the hardware display.
    *   Fixed a bug where temporary OLED messages (like "New Seq") would get "stuck" and not revert to the active graphic. All temporary messages now correctly expire and revert.

*   **CRITICAL: Cross-Feature Stability (Sampler/Visualizer):**
    *   Fixed all `AttributeError` and `TypeError` crashes that occurred when trying to enable one master feature (like the Audio Visualizer) while another (like the Screen Sampler) was running.
    *   The application now intelligently and seamlessly handles switching between these modes from either the GUI or hardware buttons without crashing.

*   **Fixed Hardware Control Regressions:**
    *   Restored full functionality to the `SELECT` encoder for navigating and loading animator sequences and layouts.
    *   Fixed the OLED "SAVE?" cue, which now reliably appears on the hardware display when loading a sequence with unsaved changes via the `SELECT` encoder.
    *   Restored missing OLED feedback for all top-row knob adjustments, providing clear visual confirmation of value changes.
    *   Tuned the sensitivity of the sampler adjustment knobs to be less "laggy" and prevent overshooting, resulting in a much more precise and responsive feel.

*   **Fixed UI & Dialog Bugs:**
    *   Resolved `NameError` and `SyntaxError` crashes in the `AppGuideDialog`, making it fully functional.
    *   Corrected the vertical alignment of non-scrolling text on the OLED display, preventing it from being cut off at the top.
    *   Fixed highlight colors in the App Guide's text to match the application's aesthetic.

---

## [Version 1.6.0] - UI & FX Overhaul 

This is a landmark release focused on a massive professional-grade overhaul of the application's user interface, user experience, and creative capabilities. The entire application layout has been re-architected for a more logical, clean, and scalable workflow. This version introduces a powerful, non-destructive "Color Grading / FX" system, a fully-featured menu bar, and a cascade of stability fixes that solidify the entire application.

### ✨ **NEW FEATURES & ENHANCEMENTS**

*   **NEW: Universal Color Grading / Live FX System:**
    *   A new "🎨 Color Grading / FX" panel has been added, replacing the old "Global Controls" widget.
    *   This panel provides real-time, non-destructive control over **Brightness, Saturation, Contrast, and Hue**.
    *   **Universal Filter:** When enabled, these effects apply globally to all visual output on the hardware, including static layouts, individually painted pads, and animator playback.
    *   **"Apply to Selected Frames" Action:** A new button allows users to permanently "bake in" the current FX settings to selected animator frames. This action shows a confirmation dialog and is fully integrated with the existing **Undo/Redo system**.
    *   **Intelligent Knob Control:** The top-strip knobs automatically sync with and control the FX sliders.

*   **NEW: Full-Featured Application Menu Bar:**
    *   A professional menu bar (`File`, `Edit`, `Animation`, `Tools`, `Help`) has been added to the top of the window, providing a logical home for every application feature.
    *   **New File Operations:** Includes actions for "📂 Load Sequence..." from a file dialog and a placeholder for "⬇️ Export Animation as GIF...".
    *   **Reorganized Edit/Animation Menus:** "Edit" now handles universal actions like Undo/Redo, while a new dedicated "Animation" menu contains all frame-specific operations (Cut, Copy, Paste, Duplicate, etc.).
    *   **Tools Menu:** Provides direct access to toggle or configure all major features: Screen Sampler, Audio Visualizer, OLED Customizer, and LazyDOOM.
    *   **Help Menu:** Includes an "About" dialog and a link to the project's GitHub page.

*   **NEW: Enhanced Hardware Workflow & Feedback:**
    *   **Context-Aware "Select/Speed" Knob:** The fifth knob now intelligently switches function. In the animator, it controls list navigation when idle, but automatically becomes a **Speed** controller with full visual feedback during playback.
    *   **OLED "SAVE?" Cue:** When a user tries to load a new sequence via the hardware knob while having unsaved changes, the OLED now displays a "SAVE?" message, directing them to the confirmation dialog on the main screen.

*   **NEW: Default Animator State on Connect:**
    *   Upon connecting the device, the animator now automatically creates and selects a single, blank frame. This provides a ready-to-use "canvas" and fixes numerous bugs related to starting with an empty state (e.g., non-functional Undo, FX, and painting).
    *   **Intelligent Save Prompt:** The "Unsaved Changes" dialog will no longer appear for this initial, untouched blank frame, providing a smoother startup experience.

### 🎨 **UI/UX REDESIGN & POLISH**

*   **Major Layout Overhaul:**
    *   The main window has been restructured. The `Animator Studio` is now the primary expanding widget, ensuring maximum space for timeline editing.
    *   A new "Control Deck" at the bottom of the left panel now logically groups the `Screen Sampler` and `LazyDOOM` widgets.
*   **Color Grading / FX Panel Refinement:**
    *   The panel layout has been redesigned into a compact 2x2 grid to maximize slider length and provide a professional, clean appearance.
    *   Includes a single "⟳ All" master reset button for convenience.
*   **Top-Strip Device Controls Polish:**
    *   The labels for the four main knobs now display the full words ("Brightness", "Saturation", etc.) for improved clarity.
*   **Menu Bar Styling:** The menu bar and its dropdowns are now fully custom-styled to match the application's dark theme, with proper hover and selection highlights for an intuitive, professional feel.

### 🐛 **BUG FIXES & STABILITY**

*   **Fixed All Knob Control & Sync Bugs:**
    *   Completely resolved the logical feedback loop that caused knobs to feel "dead" or unresponsive.
    *   Fixed the visual synchronization of the Speed knob, which now correctly snaps to the animation's current FPS and updates in real-time.
    *   Fixed the initial startup position of the four main knobs, which now correctly default to their centered, neutral position.
    *   Fixed the Select knob press action, which is now correctly ignored during animation playback.
*   **Fixed Animator Selection & UI Bugs:**
    *   Resolved the critical bug that prevented drag-selection in the animator timeline from working correctly in all directions.
    *   Fixed the infinite-loop crash caused by the "Unsaved Changes" dialog re-appearing when loading a new sequence.
*   **Fixed "Black vs. Grey" Pad Color:**
    *   Corrected the pad drawing logic to ensure that pads with a black color (`#000000`) are rendered as true black on the GUI, not dark grey.
*   **Fixed Cross-Feature Crashes:**
    *   Resolved multiple `AttributeError` and `TypeError` crashes that occurred when trying to enable one master feature (like the Audio Visualizer) while another (like the Screen Sampler) was running. The new state management system now correctly grays out and disables conflicting actions.
*   **Architectural Refactoring:**
    *   Completely refactored the `ScreenSamplerManager` and its UI components to resolve a critical startup crash caused by an initialization paradox. This has made the entire feature stable and robust.

---

## [Version 1.5.0] - June 17, 2025

This major release completed the powerful Audio Visualizer feature, overhauled the Color Picker with a professional primary/secondary color system, and introduced a significant UI/UX redesign of core components like the top "Device Controls" strip.

*   **NEW FEATURES & ENHANCEMENTS:**
    *   **Advanced Audio Visualizer (Feature Complete):** "Dual VU + Spectrum" mode implemented, "Pulse Wave" mode enhanced, 8 new prefab palettes added, and live settings dialog enabled.
    *   **Color Picker Overhaul:** Upgraded to a professional Primary (Left-Click) and Secondary (Right-Click) color system with a redesigned UI.
    *   **Main Window UI/UX Overhaul:** Rebuilt "Device Controls" strip with custom-rendered knobs, added a global brightness slider, and implemented dynamic tooltips.
*   **BUG FIXES & STABILITY:**
    *   Fixed all knob-related crashes and logic flaws.
    *   Fixed critical bugs in the Color Picker where the UI would not update in real-time.
    *   Resolved preset management and initialization crashes in the `VisualizerSettingsDialog`.

---

## [Version 1.0.1] - June 8, 2025

This version introduced a significant overhaul and initial detailed implementation of the Audio Visualizer feature, focusing on the "Classic Spectrum Bars" mode.

*   **NEW FEATURE:** Advanced Audio Visualizer - Classic Spectrum Bars (Part 1).
*   **BUG FIXES & STABILITY:** Resolved critical key mismatches and profile list update logic in the visualizer.

---

## [Version 1.0.0] - June 5, 2025

This landmark v1.0.0 release introduced the highly anticipated **"LazyDOOM" on OLED** feature and finalized the advanced OLED image processing pipeline.

*   **NEW FEATURE:** LazyDOOM on OLED! 👹
*   **OTHER FEATURES:** Advanced OLED Image Processing & Dithering Finalized.
*   **BUG FIXES:** Fixed a critical initialization bug in the `OLEDCustomizerDialog`.

---

## Previous Versions (Pre-v1.0.0 Summary)

*   **v0.9.x Releases:** Focused on experimental features that would be stabilized in v1.0.0, including advanced OLED dithering options and the initial integration of the LazyDOOM game.
*   **v0.8.0 & v0.7.0:** Focused on stabilizing the Screen Sampler, implementing persistent user settings for the sampler and color picker, and adding "My Colors" swatch management.
*   **Pre-v0.7.0:** Initial development phases, including the creation of the core Animator Studio, the first MVP of the Screen Sampler, and major refactoring efforts to establish the modular architecture.

---
*Akai Fire PixelForge - Developed by Reg0lino with AI assistance from Gemini models.*