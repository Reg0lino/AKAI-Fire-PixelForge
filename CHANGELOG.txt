# Changelog - Akai Fire PixelForge

## [Version 1.8.0] - June 1, 2025

This is a major feature and performance release that introduces two new high-performance "Ambient" sampling modes, designed to be extremely fast for use-cases like gaming. This version also includes a significant refactoring of the entire sampler UI and state management system to be more robust, intuitive, and bug-free.

### ✨ **NEW FEATURES & ENHANCEMENTS**

*   **NEW: High-Performance Ambient Sampling Modes:**
    *   The Screen Sampler now features a "Sampling Mode" dropdown to choose between algorithms.
    *   **"Thumbnail (Fast)" Mode:** A new, ultra-fast mode that captures the screen, resizes it to a `16x4` thumbnail, and maps it directly to the pads. This provides a beautiful, low-resolution mirror of the screen with minimal CPU impact, perfect for gaming.
    *   **"Palette (Creative)" Mode:** A new, creative mode that uses the `colorthief` library to find the 5 most dominant colors on screen and then generates a smooth, aesthetically pleasing gradient across the 64 pads.
*   **NEW: Dedicated "Ambient Mode" Configuration Dialog:**
    *   When a high-performance mode ("Thumbnail" or "Palette") is selected, the "Configure..." button now opens a new, streamlined dialog that contains *only* the color adjustment sliders.
    *   This provides a clean, focused UI for tuning the look of ambient modes without the unnecessary complexity of the region selector.
    *   Added a "Cycle Monitor" button to this new dialog for complete functionality.
*   **Major Sampler UI/UX Overhaul:**
    *   The "Monitor" and "Mode" dropdown menus are now **always enabled** when the device is connected, allowing the user to pre-select their desired configuration *before* starting the sampler.
    *   The monitor list now correctly populates immediately upon connecting the device, rather than waiting for the sampler to be enabled.
    *   The dropdowns now correctly update the manager's state in real-time, even when the sampler is off.

### 🐛 **BUG FIXES & STABILITY**

*   **CRITICAL: Fixed Sampler State Management:**
    *   Completely refactored the interaction between the UI and the logic manager to use a "pull" strategy, eliminating all "stale state" bugs. The manager now always acts on the most current UI settings.
    *   Fixed a critical `AttributeError` crash that occurred when starting the sampler or changing modes due to an incorrect initialization order.
    *   Fixed the bug where changing the "Mode" dropdown had no effect until the sampler was restarted.
*   **CRITICAL: Fixed `ValueError` in Palette Sampling:**
    *   Resolved a `numpy` broadcasting error that caused the "Palette (Creative)" mode to crash continuously. The gradient interpolation math is now correct and stable.
*   **Fixed Sampler Dialog Resizing:**
    *   Stabilized the `VisualSamplerConfiguration` (Grid Mode) dialog. It now correctly snaps to a compact, user-resizable window on open and on monitor cycle, fixing a long-standing bug that caused it to lock up or resize uncontrollably.

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
*Akai Fire PixelForge - Developed by Reg0lino with extensive AI assistance from Gemini models.*