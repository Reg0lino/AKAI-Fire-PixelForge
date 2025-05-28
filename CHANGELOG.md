# Changelog - Akai Fire PixelForge by Reg0lino & Gemini 2.5 Pro

## [Version 0.9.0] - 2025-05-28

This major update focuses on a comprehensive overhaul of the Akai Fire's OLED display capabilities, transforming it into a highly customizable visual element, alongside significant stability improvements and refined hardware control.

### ✨ Features & Enhancements

*   **Advanced OLED Display Customization (Phase 2 - Content Library & Active Graphic System):**
    *   **OLED Content Library Manager (`OLEDCustomizerDialog`):**
        *   Introduced a dedicated dialog (accessed by clicking the OLED mirror) to create, manage, and preview custom OLED content.
        *   Supports two main item types: "Text Items" and "Image Animation Items."
        *   User-created items are saved as JSON presets in `Documents/Akai Fire RGB Controller User Presets/OLEDCustomPresets/`.
        *   Dialog features live preview of selected library items (including playing animations) and items being edited.
        *   Includes a "Save & Apply" button to save an edited item and immediately set it as the Active Graphic.
        *   The "Set as Active Graphic" dropdown selection is now persistent within the dialog session across library modifications.
    *   **Custom Text Items:**
        *   Users can define text content, select from available system fonts, and set font size in pixels.
        *   Configuration for text alignment (left, center, right) for static display.
        *   Scrolling animation for long text, with options to override the global scroll speed and define pause durations at scroll ends for individual items.
    *   **Custom Image & GIF Animations for OLED:**
        *   Import various static image formats (PNG, JPG, BMP, etc.) and **animated GIFs** via `oled_utils/image_processing.py`.
        *   Comprehensive image processing options during import:
            *   **Resize Modes:** Stretch to Fit, Fit (Keep Aspect & Pad), Crop to Center for the 128x64 OLED.
            *   **Contrast Adjustment:** Pre-dithering contrast enhancement slider.
            *   **Color Inversion:** Option to invert black and white.
            *   **Monochrome Conversion & Dithering:**
                *   Floyd-Steinberg Dither.
                *   Simple Threshold (with an adjustable threshold slider).
                *   Ordered Dither (Bayer 4x4 matrix).
        *   Processed images/GIFs are converted into sequences of 1-bit logical frames.
        *   Users can set target playback FPS and loop behavior (Loop Infinitely, Play Once) for animations displayed on the hardware OLED.
        *   GIF metadata (original FPS, loop count) is extracted where available.
    *   **"Active Graphic" System (`OLEDDisplayManager`):**
        *   Users can select any custom Text Item or Image Animation Item from their library to be the persistent "Active Graphic."
        *   This Active Graphic automatically displays on the hardware OLED after an initial built-in startup visual.
        *   The chosen Active Graphic path is saved to `oled_config.json` and loaded on application start.
    *   **Built-in Visual Startup Animation:**
        *   A fixed, dynamic visual animation (pulse/grid) now plays on the OLED upon successful MIDI connection before transitioning to the user's Active Graphic or the application default.
    *   **Unified Temporary System Messages (`OLEDDisplayManager`):**
        *   Robust system for displaying transient feedback (e.g., knob feedback, operational cues like sampler status, animator status, hardware button interactions).
        *   All temporary messages now use a specific, clear "TomThumb" 60pt retro font for high visibility and consistent branding.
        *   Messages display briefly, scrolling automatically if necessary, and then gracefully allow the user's chosen "Active Graphic" (or application default) to resume.
    *   **Application Default OLED Message:**
        *   If no "Active Graphic" is set by the user, a scrolling message "Fire RGB Customizer by Reg0lino =^.^=" (using TomThumb 60pt) is displayed.
    *   **Qt-based Text Rendering for Active Graphics:** User-defined text items set as the "Active Graphic" are now rendered by `OLEDDisplayManager` using Qt's `QFont` and `QPainter` to an off-screen `QImage`, then converted to a 1-bit PIL `Image` for packing. This significantly improves system font compatibility and rendering fidelity on the hardware OLED compared to previous direct Pillow rendering for user fonts.
*   **OLED Customization - Phase 1 (Foundational Startup Text & Font - from "Unreleased" section):**
    *   Initial `OLEDCustomizerDialog` allowing users to edit default startup text, select system font/size, and set global scroll speed. (This has now been superseded and integrated into the broader "Active Graphic" system).
    *   OLED settings (active graphic path, global scroll delay) saved to and loaded from `user_settings/oled_config.json`.
*   **Enhanced Hardware Control & OLED Feedback Integration:**
    *   **Dynamic Knob Control:** Context-sensitive knob functions refined:
        *   **Global Mode:** Knob 1 (Volume) controls global physical pad brightness. Physical Akai Fire Encoder 1 (CC 0x10) mapped.
        *   **Sampler Active Mode:** Knobs 1-4 control Sampler Brightness, Saturation, Contrast, Hue Shift. Physical Encoders 1-4 (CC 0x10-0x13) mapped.
        *   **Animator Playing Mode:** Knob 4 (Resonance) controls animation playback speed (FPS). Physical Encoder 4 (CC 0x13) mapped.
    *   **OLED Feedback for Hardware Actions:**
        *   Knob turns provide real-time value feedback on the OLED (e.g., "GlbBr: 50%", "Sat: 1.20x", "Spd: 15.0") using the TomThumb 60pt font.
        *   Sampler ON/OFF, Animator Play/Pause/Stop cues, and UI navigation cues (Grid L/R, Select Encoder) also display as temporary messages on the OLED.
    *   **OLED Item Navigation via Hardware:**
        *   PATTERN UP/DOWN buttons now cycle through a cued OLED item (Text/Animation) from the user's library, showing a temporary "Cue: ItemName" message.
        *   BROWSER button (when contextually appropriate) activates the currently cued OLED item, setting it as the new "Active Graphic" and showing a confirmation message.
        *   (Note: `HardwareInputManager` requires signals like `oled_pattern_up_pressed` to be fully defined for this).
    *   The physical BROWSER button (Note 0x21) on the Akai Fire also toggles the Screen Sampler ON/OFF (behavior might be shared/prioritized with OLED activation).
*   **UI and UX Refinements:**
    *   `OLEDCustomizerDialog` layout stabilized, particularly concerning dynamic content visibility (e.g., threshold slider) using fixed minimum heights for editor panels.
    *   Improved clarity of terms (e.g., "Default Startup Item" to "Set as Active Graphic").
    *   Dialog now correctly remembers the "Set as Active Graphic" choice during the session even if other library items are modified.

### 🐛 Bug Fixes & Stability

*   **OLED System Stability:**
    *   Resolved various `AttributeError`s and `TypeError`s in `OLEDDisplayManager` and `oled_renderer.py` related to font loading, text rendering paths, and animation playback.
    *   Corrected OLED text scrolling direction (now consistently right-to-left for overflow) and looping behavior for Active Graphics.
    *   Ensured `OLEDCustomizerDialog` animation previews for library items play correctly.
*   **Type Errors for Hue Shift:** Corrected `TypeError` and `ValueError` when setting/displaying Hue Shift values by ensuring consistent data types and proper rounding for UI elements.
*   **Missing Method Definitions & NameErrors:** Addressed various `AttributeError`s and `NameError`s in `MainWindow` and other modules by implementing missing handlers or correcting variable names, leading to improved UI initialization and interaction stability.
*   **Animator Play/Pause Crash:** Fixed `AttributeError` related to `clear_led_suppression_and_update` by removing the call, aligning with the Play/Stop LEDs being forced off.
*   **Dialog Initialization:** `OLEDCustomizerDialog` now correctly loads and reflects initial global settings (Active Graphic selection, scroll speed).
*   **Packaging Preparation:**
    *   Refined `utils.get_resource_path` for robustness in finding bundled resources.
    *   Reviewed `.spec` file for PyInstaller, adding necessary hidden imports (Pillow submodules, `mss` platform specifics, standard libraries like `io`, `colorsys`) and data file inclusions (especially `resources/fonts`).

### 💬 Developer Notes

*   `OLEDDisplayManager` state machine (`_apply_current_oled_state`) now robustly manages display priorities: Built-in Startup Visual -> Persistent Override Text -> Temporary System Message -> User's Chosen "Active Graphic" -> Hardcoded Application Default Message.
*   The `AkaiFireController` now forces Play/Stop LEDs OFF to prevent conflicts with application-driven feedback. Pad brightness control is centralized.
*   User preset paths (OLED items, sequences, static layouts) standardized to a main folder in "Documents" (`Akai Fire RGB Controller User Presets`).

---

## [Version 0.8.0] - 2025-05-19 - Sampler Stability & Preference Refinement

### ✨ Features & Enhancements

*   **Screen Sampler Functionality Restored & Improved:**
    *   **Monitor Selection:** "Target Monitor" dropdown now fully interactive.
    *   **Preference Loading:** Saved region/adjustment preferences per monitor correctly loaded/applied.
    *   **Live Preview in Dialog:** Correctly shows live preview of sampled area.
    *   Preferences saved immediately on change and on application exit.
*   **Modularization and Refactoring:**
    *   Screen sampler logic moved from `MainWindow` into dedicated `ScreenSamplerManager` and `ScreenSamplerUIManager`.
*   **Debuggability:** More robust import handling and placeholder classes.

### 🐛 Bug Fixes & Stability

*   **Resolved Critical Initialization Errors:** Fixed multiple `AttributeError`s and circular import errors in sampler components.
*   **Fixed Sampler Preference "Snap Back":** Resolved issues with dialogs reverting to stale settings by improving cache updates and signal blocking.
*   **Improved Preference Handling Logic:** Refined logic for loading `last_active_monitor_key`.
*   **Virtual Environment Usage:** Emphasized, resolving "ghost" errors.

### Known Issues

*   Sampler Recording feature functional but needs more edge-case testing.

---

## [Version 0.7.0] - (Date Inferred)

### ✨ Features & Enhancements

*   **Sampler Recording Auto-Save & Listing:** Recordings saved to `presets/sequences/sampler_recordings/`, listed with `[Sampler]` prefix, auto-loaded.
*   **Persistent User Settings for Sampler & Color Picker:** Sampler configs per-monitor (`sampler_user_prefs.json`), color picker swatches (`fire_controller_config.json`) saved via `appdirs`.
*   **Color Picker "My Colors" Swatch Management:** Right-click context menu ("Clear", "Set to Current").
*   **Screen Sampler Default Adjustments:** Dialog sliders default to "boosted" look.

### 🐛 Bug Fixes & Stability

*   **Color Picker Visuals & Functionality Fixed.**
*   **`NameError`s for Directory Constants & `SequenceFileManager` Robustness.**
*   **General Stability (Resolved Multiple UI Initialization Bugs in `MainWindow`).**

---

## Previous Versions (Summary - Pre-0.7.0)

*   **Feature Phase: Sampler Recording Framework** (Conceptualized, partial implementation)
*   **Feature Phase: Granular Grid Sampling & Monitor View Refinement**
*   **Feature Phase: Interactive Screen Sampler MVP** (Dialog with S/C/B/H sliders)
*   **Bugfix & Refactor Phase: JSON Loading, Recursion, UI Glitches**
*   **Feature Phase: Animator UI Enhancements & Core Logic**
*   **Major Refactoring & Early Bug Squashing** (`MainWindow` modularization)
*   **Initial Development Phase** (Project Setup, Basic Hardware Control, GUI Foundation)

---
*Akai Fire PixelForge - Developed by Reg0lino with extensive AI assistance from Gemini models.*