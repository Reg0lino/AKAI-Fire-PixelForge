# Changelog - Akai Fire PixelForge

## [Version 1.0.0] - 2025-06-05

This landmark v1.0.0 release introduces the highly anticipated **"LazyDOOM" on OLED** feature, transforming your Akai Fire into a mini retro gaming console! This version also finalizes and fully integrates the advanced OLED image processing and dithering capabilities previously in experimentation, solidifying PixelForge as a powerful platform for creative and interactive experiences on the Akai Fire.

### 🚀 NEW FEATURE: LazyDOOM on OLED! 👹

*   **Playable First-Person Experience:**
    *   Integrated a DOOM-themed, first-person raycaster game, "LazyDOOM," playable directly on the Akai Fire's 128x64 monochrome OLED display.
    *   Features a custom Python-based 2.5D raycasting engine (not a direct DOOM port), offering a unique retro feel.
*   **Procedural Map Generation:**
    *   Each game session features a unique, procedurally generated maze-like map using a Depth-First Search algorithm, ensuring high replayability.
    *   Player always spawns facing a clear hallway, enhancing initial playability and fairness.
*   **Gameplay Mechanics:**
    *   **Movement:** Full player movement including Forward, Backward, Strafing (Left/Right), and Turning (Primary and Alternate turn speeds/methods).
    *   **Run Functionality:** Hold the "Run" pad for increased movement speed.
    *   **Combat:** Hitscan "shooting" mechanic to engage enemies.
    *   **Health System:** Player Health (HP) system; taking damage reduces HP, and reaching zero results in game over.
    *   **Enemies ("Imps"):**
        *   Basic "Imp" type enemies populate the map, each with their own health.
        *   Imps exhibit simple random jitter movement to make them less static targets.
        *   AI-controlled shooting behavior, including Line-of-Sight (LOS) checks – Imps will no longer shoot through solid walls.
        *   Enemies are strategically placed during map generation to avoid immediate, unavoidable LOS to the player at their spawn point.
*   **Akai Fire Hardware Integration & Feedback:**
    *   **Pad Controls:** The game is primarily controlled using the Akai Fire's 4x16 pad matrix, configured for D-Pad style movement, strafing, turning, and action buttons (Shoot, Run).
    *   **RGB Pad Lighting for Controls & Status:**
        *   Control pads light up with distinct, intuitive colors (e.g., Red for primary movement/turn, Orange for strafe/alternate-turn, Blue for Run, Green for Shoot).
        *   Player HP is visually represented on a dedicated row of 4 pads, typically lighting up in Red to indicate current health levels (e.g., 4 red pads = full HP, 1 red pad = low HP).
        *   Visual feedback on pads when the player takes damage (e.g., non-control/HP pads flash red briefly).
        *   Game over sequence includes distinct full-pad RGB effects (e.g., flashing all red).
    *   **OLED Display for Gameplay & HUD:**
        *   The game world is rendered directly to the physical OLED display and mirrored in the main application's GUI OLED preview.
        *   Includes an on-screen Heads-Up Display (HUD) showing current player HP.
        *   Visual "screen glitch" or flash effect on the OLED when the player takes damage.
        *   Clear "YOU DIED!" or "YOU WIN!" messages displayed prominently on the OLED at game conclusion.
        *   "Restart? (SHOOT)" prompt displayed on the OLED after game over, with the physical "SHOOT" pad blinking (e.g., green) to indicate it as the restart trigger.
*   **Selectable Difficulty Levels:**
    *   Three difficulty levels (e.g., "Normal," "Hard," "Nightmare!") are available for selection when launching LazyDOOM.
    *   Harder difficulties can influence factors such as enemy aggression (shooting frequency/chance), enemy health, or the number of enemies spawned (e.g., "Nightmare!" spawns additional enemies).
*   **Seamless Integration into PixelForge:**
    *   LazyDOOM is launched via a dedicated button (e.g., "👹 LazyDOOM") in the main PixelForge application UI.
    *   An instructions dialog, detailing game controls, objectives, and tips, is presented to the user before the game session begins.
    *   When LazyDOOM is active, other core PixelForge functionalities (Animator Studio, Screen Sampler, Static Layouts, Direct Pad Painting, and the main OLED Active Graphic display) are temporarily disabled or suspended. This dedicates hardware resources (MIDI communication, pad processing, OLED updates) to the game for optimal performance.
    *   The application ensures a smooth transition into and out of DOOM mode. Upon exiting LazyDOOM, the previous PixelForge state (OLED display content, pad lighting for the active mode) is restored.
*   **Clear Win Condition:**
    *   The game is won by successfully defeating all "Imp" enemies on the currently generated map.
    *   The previous concept of needing to find a specific "Exit" tile has been removed to provide a more straightforward and combat-focused win condition.

### ✨ Other Features & Enhancements (v1.0.0)

*   **Advanced OLED Image Processing & Dithering Finalized:** The full suite of image processing capabilities for OLED content, previously in experimental stages (as seen in v0.9.2 development), is now fully integrated and considered stable. This includes:
    *   Gamma Correction, Pre-Dither Blur, Sharpening, and Noise Injection (Pre/Post).
    *   Expanded Dithering Algorithms: Atkinson Dither, Ordered Dither (Bayer 2x2, 4x4, 8x8).
    *   Variable Dither Strength for error-diffusion algorithms.
    *   All options are integrated into the OLED Customizer, with parameters saved to and loaded from JSON presets.
*   **Layout Restructuring (`OLEDCustomizerDialog`):** The "Live Preview (Main)" section in the OLED Customizer Dialog has been relocated to the left pane, under the Item Library. This provides significantly more vertical space for the "Item Editor" (especially the Animation Editor's numerous options) in the right pane, improving usability on various screen resolutions.
*   **UI Refinements (`OLEDCustomizerDialog`):** Improved the appearance and clarity of the small "reset" buttons next to sliders in the Animation Item editor by using QSS for a flatter look and adjusting font size/weight for better symbol visibility.

### 🐛 Bug Fixes & Stability (v1.0.0)

*   **Critical `OLEDCustomizerDialog` Initialization Fix:** Resolved a persistent issue where the `item_library_list` (QListWidget) reference could become invalid or evaluate as `False` during signal connection in `_connect_signals`. This was due to the underlying C++ object becoming a "zombie," and has been fixed by explicitly checking `is not None` and adding robust error handling around signal connections. This restores full functionality to the "Edit Selected" and "Delete Selected" buttons and ensures proper library interaction.

### 💬 Developer Notes

*   The LazyDOOM raycasting engine is a bespoke implementation optimized for the Akai Fire's constraints and monochrome display. It's designed for fun, retro gameplay rather than being a feature-complete DOOM clone.
*   The image processing pipeline in `image_processing.py` now robustly handles all new pre-dithering steps in a logical order: Brightness -> Gamma -> Sharpen -> Contrast -> Pre-Dither Blur -> Pre-Dither Noise -> Invert -> Dither -> Post-Dither Noise.

---

## [Version 0.9.2] - 2025-05-29

This version significantly expanded the image processing capabilities for OLED content, introducing new pre-dithering adjustments and a wider array of dithering algorithms for enhanced visual customization. (Note: These features are now considered stable and fully integrated in v1.0.0).

### ✨ Features & Enhancements

*   **Advanced OLED Image Processing & Dithering Options (`OLEDCustomizerDialog` & `image_processing.py`):**
    *   🎨 **Gamma Correction:** Added a "Gamma" slider (0.5 to 2.0).
    *   🌫️ **Pre-Dither Blur:** Introduced a "Pre-Dither Blur" slider (0.0 to 2.0 radius).
    *   ✨ **Sharpening:** Added a "Sharpen" slider (0 to 100 strength).
    *   🔊 **Noise Injection:** "Noise Type" dropdown and "Noise Amount" slider.
    *   🔢 **Expanded Dithering Algorithms:** Atkinson Dither, Ordered Dither (Bayer 2x2, 8x8) added.
    *   💪 **Variable Dither Strength:** For Floyd-Steinberg, Atkinson.
    *   ⚙️ **UI Integration:** All new sliders and options integrated.
    *   💾 **Preset Compatibility:** New parameters saved/loaded.
*   **DOOM Feature Integration (LazyDOOM - Initial experimental integration):**
    *   Integrated an early playable version of a DOOM-like game.
    *   Included startup dialog, keyboard controls, and dedicated game mode.

### 🐛 Bug Fixes & Stability

*   **OLED Customizer Dialog Robustness:** Addressed `AttributeError` issues.
*   **Indentation & Code Structure:** Ensured proper Python code structure.

### 💬 Developer Notes

*   Image processing pipeline updated for new pre-dithering steps.
*   Conditional visibility of Dither Strength/Threshold sliders handled.

---

## [Version 0.9.1] - 2025-05-28

This version focused on critical usability enhancements for the OLED Customizer Dialog, performance improvements in the Animator Studio, and fixes for UI stability and appearance.

### ✨ Features & Enhancements

*   **OLED Customizer Dialog UX Improvements:** "Save & Apply" functionality, Persistent "Active Graphic" choice, Clearer Item Labels for Image vs. Animation.
*   **Manual OLED Active Graphic Control:** Play/Pause indicator and functionality for OLED Active Graphic. Removed automatic OLED pausing in Animator.
*   **Animator Studio Performance:** Optimized pad painting speed (undo per stroke, targeted thumbnail update).
*   **UI & OLED Message Refinements:** "New Sequence" OLED cue.

### 🐛 Bug Fixes & Stability

*   **OLED Customizer Dialog Stability:** Fixed `TypeError` on open, `AttributeError` for preview clearing, Resolved Save Button visibility.
*   **Top Strip UI Layout & Functionality:** Fixed `TypeError` in layout, improved OLED Play/Pause icon functionality and appearance.
*   **Animator Performance & Signal Handling:** Reduced "signal echo" and redundant UI updates.

### 💬 Developer Notes

*   Manual OLED Play/Pause is now primary control method.

---

## [Version 0.9.0] - 2025-05-28
*(Previously "Unreleased - 2025-05-25")*

This major update focused on a comprehensive overhaul of the Akai Fire's OLED display capabilities, transforming it into a highly customizable visual element, alongside significant stability improvements and refined hardware control.

### ✨ Features & Enhancements

*   **Advanced OLED Display Customization (Phase 2 - Content Library & Active Graphic System):**
    *   OLED Content Library Manager (`OLEDCustomizerDialog`): Text Items, Image Animation Items, JSON presets.
    *   Custom Text Items: Fonts, size, alignment, scrolling with overrides.
    *   Custom Image & GIF Animations for OLED: Import, resize, contrast, inversion, initial dithering set (Floyd-Steinberg, Threshold, Bayer 4x4).
    *   "Active Graphic" System (`OLEDDisplayManager`): Persistent user-chosen OLED display.
    *   Built-in Visual Startup Animation.
    *   Unified Temporary System Messages (TomThumb font).
    *   Application Default OLED Message.
    *   Qt-based Text Rendering for Active Graphics.
*   **Enhanced Hardware Control & OLED Feedback Integration:** Dynamic Knob Control, OLED Feedback for Hardware Actions, OLED Item Navigation via Hardware.
*   **UI and UX Refinements:** `OLEDCustomizerDialog` layout stabilized.

### 🐛 Bug Fixes & Stability

*   OLED System Stability, TypeErrors, NameErrors, Dialog Initialization, Packaging Prep.

### 💬 Developer Notes

*   `OLEDDisplayManager` state machine robustly manages display priorities.

---

## [Version 0.8.0] - 2025-05-19 - Sampler Stability & Preference Refinement

### ✨ Features & Enhancements
*   Screen Sampler Functionality Restored & Improved (Monitor Selection, Preference Loading, Live Preview).
*   Modularization: Screen sampler logic moved to `ScreenSamplerManager` and `ScreenSamplerUIManager`.
*   Debuggability improved.

### 🐛 Bug Fixes & Stability
*   Resolved Critical Initialization Errors in sampler components.
*   Fixed Sampler Preference "Snap Back" issue.
*   Improved Preference Handling Logic.
*   Addressed "ghost" errors with virtual environment usage.

---

## [Version 0.7.0]

### ✨ Features & Enhancements
*   Sampler Recording Auto-Save & Listing.
*   Persistent User Settings for Sampler & Color Picker.
*   Color Picker "My Colors" Swatch Management.
*   Screen Sampler Default Adjustments.

### 🐛 Bug Fixes & Stability
*   Color Picker Visuals & Functionality Fixed.
*   `NameError`s & `SequenceFileManager` Robustness.
*   General UI Initialization Bug Fixes in `MainWindow`.

---

## Previous Versions (Summary - Pre-0.7.0)
*   Sampler Recording Framework
*   Granular Grid Sampling & Monitor View Refinement
*   Interactive Screen Sampler MVP
*   Bugfix & Refactor Phase (JSON Loading, Recursion, UI Glitches)
*   Animator UI Enhancements & Core Logic
*   Major Refactoring & Early Bug Squashing
*   Initial Development Phase

---
*Akai Fire PixelForge - Developed by Reg0lino with extensive AI assistance from Gemini models.*5
