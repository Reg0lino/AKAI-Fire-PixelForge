# Changelog - Akai Fire PixelForge

## [Version 0.9.1] - 2025-05-29

This version focuses on critical usability enhancements for the OLED Customizer Dialog, performance improvements in the Animator Studio, and fixes for UI stability and appearance.

### ✨ Features & Enhancements

*   **OLED Customizer Dialog UX Improvements:**
    *   ✨ **"Save & Apply" Functionality:** Added a "Save & Apply" button to the OLED Customizer Dialog. This allows users to save the currently edited Text or Animation item and immediately set it as the "Active Graphic" in one step. The editor content takes precedence if active and modified; otherwise, the library selection is used.
    *   🔄 **Persistent "Active Graphic" Choice:** The selection made in the "Set as Active Graphic" dropdown within the OLED Customizer Dialog now persists throughout the dialog session, even when new items are created, edited, or deleted from the library.
    *   🖼️ **Clearer Item Labels:** Single-frame items imported/saved via the "Image Animation Items" workflow are now labeled with an "(Image)" suffix (e.g., "My Cool Pic (Image)") in the OLED item library and "Set as Active Graphic" dropdown, distinguishing them from multi-frame "(Animation)" items. The internal `item_type` remains `image_animation` for consistent data handling.
*   **Manual OLED Active Graphic Control:**
    *   ⏯️ **Play/Pause Indicator for OLED:** Added a clickable icon (using `play-pause.png`) next to the OLED mirror in the main window's top strip. This allows users to manually pause or resume the currently playing/scrolling OLED "Active Graphic".
        *   The icon's tooltip dynamically updates to "Pause..." or "Resume..." based on the current state.
        *   The icon is styled to be clean and borderless, positioned to the right of the OLED mirror and below the Browser button (as per user mockup).
    *   🚫 **Removed Automatic OLED Pausing:** The feature where the OLED Active Graphic would automatically pause when a frame was selected in the Animator Studio has been removed in favor of user-controlled manual pausing. The tooltip on the new Play/Pause icon can suggest using it for performance if needed.
*   **Animator Studio Performance:**
    *   ⚡ **Optimized Pad Painting Speed:** Significantly improved responsiveness when drawing on pads while a frame is selected in the Animator.
        *   The timeline thumbnail for *only the edited frame* is now updated, instead of redrawing all thumbnails.
        *   Undo state (`_push_undo_state` in `SequenceModel`) is now captured once at the *start* of a continuous paint stroke (mouse down) rather than on every individual pad paint, greatly reducing overhead during dragging. Undo now reverts the entire last stroke.
*   **UI & OLED Message Refinements:**
    *   ✨ **"New Sequence" OLED Cue:** When a new sequence is created in the Animator, the OLED now briefly displays a short message like "New Seq*" instead of the longer, scrolling "Seq: Untitled*".

### 🐛 Bug Fixes & Stability

*   **OLED Customizer Dialog Stability:**
    *   Fixed `TypeError: 'current_active_graphic_path' is an unknown keyword argument` that occurred when opening the OLED Customizer Dialog due to a parameter name mismatch.
    *   Fixed `AttributeError: 'OLEDCustomizerDialog' object has no attribute '_clear_main_preview_content'` by correcting the method call to `_clear_preview_label_content`.
    *   **Resolved Save Button Visibility:** Ensured the "Save Text Item" and "Save Animation Item" buttons within the OLED Customizer Dialog editor panels are consistently visible and not cut off, by adjusting internal layout stretch factors and confirming panel minimum heights are adequate.
*   **Top Strip UI Layout & Functionality:**
    *   Fixed `TypeError: addLayout(...) too many arguments` in `MainWindow._create_hardware_top_strip` by correctly using `addWidget` for QWidget containers of layouts or by removing the erroneous alignment flag from `addLayout` calls.
    *   **OLED Play/Pause Icon:**
        *   Fixed click functionality for the new QLabel-based Play/Pause icon by correcting event handling in `MainWindow.eventFilter` and ensuring the label is enabled when the device is connected.
        *   Addressed appearance issues (e.g., blue focus outlines) via more specific QSS and by using a QLabel with a Pixmap for a cleaner look.
        *   Refined the layout of the Play/Pause icon to be positioned at the bottom-right of the OLED mirror, with the Browser button to its right and vertically centered.
*   **Animator Performance & Signal Handling:**
    *   Reduced "signal echo" and redundant UI updates when selecting frames in the Animator timeline or when the model's edit frame changed, leading to a smoother experience.
    *   Optimized the emission of `sequence_modified_status_changed` from `AnimatorManagerWidget` to only fire when the sequence name or its `is_modified` boolean state actually changes, preventing excessive OLED updates during pad painting.

### 💬 Developer Notes

*   The manual OLED Play/Pause functionality is now the primary way to control OLED Active Graphic playback state during application use.
*   Further optimization of the `SequenceModel._push_undo_state()` deep copy operation could be considered if sequences with a very large number of frames still exhibit a slight hitch at the beginning of a paint stroke, but the current "undo per stroke" is a significant improvement.

---

## [Version 0.9.0] - 2025-05-28 
*(Previously "Unreleased - 2025-05-25")*

This major update focuses on a comprehensive overhaul of the Akai Fire's OLED display capabilities, transforming it into a highly customizable visual element, alongside significant stability improvements and refined hardware control.

### ✨ Features & Enhancements

*   **Advanced OLED Display Customization (Phase 2 - Content Library & Active Graphic System):**
    *   **OLED Content Library Manager (`OLEDCustomizerDialog`):**
        *   Introduced a dedicated dialog (accessed by clicking the OLED mirror) to create, manage, and preview custom OLED content.
        *   Supports two main item types: "Text Items" and "Image Animation Items."
        *   User-created items are saved as JSON presets in `Documents/Akai Fire RGB Controller User Presets/OLEDCustomPresets/`.
        *   Dialog features live preview of selected library items (including playing animations) and items being edited.
    *   **Custom Text Items:**
        *   Users can define text content, select from available system fonts, and set font size in pixels.
        *   Configuration for text alignment (left, center, right) for static display.
        *   Scrolling animation for long text, with options to override the global scroll speed and define end-pause durations for individual items.
    *   **Custom Image & GIF Animations for OLED:**
        *   Import various static image formats (PNG, JPG, BMP, etc.) and **animated GIFs** via `oled_utils/image_processing.py`.
        *   Comprehensive image processing options during import:
            *   **Resize Modes:** Stretch to Fit, Fit (Keep Aspect & Pad), Crop to Center for the 128x64 OLED.
            *   **Contrast Adjustment:** Pre-dithering contrast enhancement slider.
            *   **Color Inversion:** Option to invert black and white.
            *   **Monochrome Conversion & Dithering:** Floyd-Steinberg Dither, Simple Threshold (adjustable), Ordered Dither (Bayer 4x4).
        *   Processed images/GIFs are converted into sequences of 1-bit logical frames.
        *   Users can set target playback FPS and loop behavior (Loop Infinitely, Play Once) for animations on the hardware OLED.
        *   GIF metadata (original FPS, loop count) is extracted where available.
    *   **"Active Graphic" System (`OLEDDisplayManager`):**
        *   Users can select any custom Text Item or Image Animation Item from their library to be the persistent "Active Graphic."
        *   This Active Graphic automatically displays on the hardware OLED after an initial built-in startup visual.
        *   The chosen Active Graphic path is saved to `oled_config.json` and loaded on application start.
    *   **Built-in Visual Startup Animation:**
        *   A fixed, dynamic visual animation (pulse/grid) now plays on the OLED upon successful MIDI connection.
    *   **Unified Temporary System Messages (`OLEDDisplayManager`):**
        *   Robust system for displaying transient feedback using a specific "TomThumb" 60pt retro font.
        *   Messages display briefly (scrolling if necessary) and then gracefully revert to the user's chosen "Active Graphic".
    *   **Application Default OLED Message:**
        *   If no "Active Graphic" is set, a scrolling message "Fire RGB Customizer by Reg0lino =^.^=" (TomThumb 60pt) is displayed.
    *   **Qt-based Text Rendering for Active Graphics:** Improves system font compatibility and rendering fidelity.
*   **Enhanced Hardware Control & OLED Feedback Integration:**
    *   **Dynamic Knob Control:** Context-sensitive knobs for Global Brightness, Sampler Parameters, or Animator Speed.
    *   **OLED Feedback for Hardware Actions:** Knob turns, sampler status, animator status, UI navigation cues show temporary messages.
    *   **OLED Item Navigation via Hardware:** PATTERN UP/DOWN to cue OLED items, BROWSER to activate cued item.
*   **UI and UX Refinements:**
    *   `OLEDCustomizerDialog` layout stabilized.
    *   Terms like "Set as Active Graphic" clarified.

### 🐛 Bug Fixes & Stability

*   **OLED System Stability:** Resolved various errors in `OLEDDisplayManager` and `oled_renderer.py`. Corrected OLED text scrolling. Ensured `OLEDCustomizerDialog` animation previews work.
*   **Type Errors & NameErrors:** Addressed multiple `TypeError`s (e.g., Hue Shift) and `NameError`s, improving stability.
*   **Dialog Initialization:** `OLEDCustomizerDialog` correctly loads initial global settings.
*   **Packaging Preparation:** Refined `utils.get_resource_path`, updated `.spec` file.

### 💬 Developer Notes

*   `OLEDDisplayManager` state machine robustly manages display priorities.
*   User preset paths standardized to "Documents".

---

## [Version 0.8.0] - 2025-05-19 - Sampler Stability & Preference Refinement
*(Details as previously provided)*

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

## [Version 0.7.0] - (Date Inferred)
*(Details as previously provided)*

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
*(Details as previously provided)*
*   Sampler Recording Framework
*   Granular Grid Sampling & Monitor View Refinement
*   Interactive Screen Sampler MVP
*   Bugfix & Refactor Phase (JSON Loading, Recursion, UI Glitches)
*   Animator UI Enhancements & Core Logic
*   Major Refactoring & Early Bug Squashing
*   Initial Development Phase

---
*Akai Fire PixelForge - Developed by Reg0lino with extensive AI assistance from Gemini models.*