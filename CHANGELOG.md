# Changelog - AKAI Fire RGB Controller

## [Unreleased] - 2025-05-25 (Current Development)

### ✨ Features & Enhancements

*   **OLED Customization - Phase 1 (Startup Text & Font):**
    *   Implemented `OLEDCustomizerDialog` allowing users to:
        *   Edit the default startup text displayed on the Akai Fire's OLED.
        *   Select any system font family and pixel size for this startup text.
        *   Set a global scroll speed (delay per step) for all OLED scrolling text.
        *   View a live preview of the customized text within the dialog, including scrolling.
    *   These OLED settings (text, font family, font size, scroll delay) are saved to and loaded from `user_settings/oled_config.json`, persisting across sessions.
    *   `OLEDDisplayManager` now dynamically loads the user's chosen system font by rendering text to a `QImage` using Qt's `QFont` and `QPainter`, then converting this `QImage` to a 1-bit PIL `Image` for packing by `oled_renderer`. This resolves previous issues with Pillow's inconsistent system font loading. Resource fonts like "TomThumb.ttf" are still loaded directly as PIL `ImageFont` objects.
    *   `oled_renderer.py` was updated with a new `pack_pil_image_to_7bit_stream()` function to handle pre-rendered PIL images and `get_text_actual_width()` was refined.
*   **Dynamic Knob Control for OLED Feedback & Global Brightness:**
    *   The top four GUI knobs in `MainWindow` are now context-sensitive.
    *   **Global Pad Brightness:** The first GUI knob (previously "Volume") now controls the global brightness of the physical Akai Fire pads. Its tooltip and value range (0-100%) update accordingly. Physical Akai Fire Encoder 1 (CC 0x10) now controls this GUI knob and the pad brightness.
    *   **OLED Knob Feedback:** When GUI knobs (Global Brightness, or Sampler Adjustments when sampler is active) are turned, the OLED temporarily displays the knob's current value (e.g., "GlbBr: 50%", "Br: 1.20x") using a dedicated font ("TomThumb.ttf" @ 60px) for consistent appearance. The display reverts to its normal state after a short timeout.
    *   **Sampler Adjustments via Knobs (Foundation):**
        *   When the Screen Sampler is active, the top four GUI knobs are reconfigured (tooltips, ranges, values) to control Sampler Brightness, Saturation, Contrast, and Hue Shift.
        *   The corresponding physical Akai Fire Encoders (CC 0x10-0x13) now control these GUI knobs and sampler parameters.
        *   `HardwareInputManager` was updated to emit a generic `physical_encoder_rotated(encoder_id, delta)` signal for these encoders.
        *   `MainWindow` now has a central dispatcher (`_on_physical_encoder_rotated`) to route physical knob inputs based on application context (Global, Sampler Active, or Animator Playing).
        *   `ScreenSamplerManager` updated with `update_sampler_adjustment()` method and `sampler_adjustments_changed` signal to facilitate external control and UI synchronization.
        *   `CapturePreviewDialog` (sampler config) sliders have been reordered to Brightness, Saturation, Contrast, Hue to match knob assignment. The dialog's sliders now sync with changes made via the main window knobs.
*   **Hardware Control Enhancements:**
    *   The physical BROWSER button (Note 0x21) on the Akai Fire now also toggles the Screen Sampler ON/OFF, in addition to the PERFORM button.

### 🐛 Bug Fixes & Stability

*   **OLED Text Rendering:** Resolved `AttributeError`s in `OLEDDisplayManager` related to missing functions (`render_text_to_7bit_packed_buffer`, `get_text_width_pixels`) in `oled_renderer.py` by aligning function calls and adding the necessary utilities to `oled_renderer.py`.
*   **OLED Scrolling:** Fixed incorrect OLED text scrolling direction and looping behavior by correcting the offset logic in `OLEDDisplayManager._scroll_text_step` and `_start_scrolling_if_needed`.
*   **Type Errors for Hue Shift:** Corrected `TypeError` and `ValueError` when setting/displaying Hue Shift values (which are floats) on `QSlider`/`QDial` (which expect ints) and in f-string formatting for tooltips/labels by implementing `int(round(value))` casting in `MainWindow`, `CapturePreviewDialog`, and ensuring consistent data types.
*   **Missing Method Definitions:** Added several missing handler methods in `MainWindow` (e.g., `_handle_paint_black_button`, `clear_all_hardware_and_gui_pads`, `_handle_final_color_selection_from_manager`, `_handle_apply_static_layout_data`, `_provide_grid_colors_for_static_save`, `apply_colors_to_main_pad_grid`) that were causing `AttributeError`s during UI initialization or interaction.
*   **`NameError` Resolution:** Fixed `NameError` for `FIRE_BUTTON_BROWSER` in `HardwareInputManager`.
*   **`UnboundLocalError` Resolution:** Fixed `UnboundLocalError` for `ScreenSamplerCore` in `MainWindow._on_sampler_activity_changed_for_knobs` by ensuring `ScreenSamplerCore` is imported at the module level of `main_window.py`.
*   **Animator Play/Pause Crash:** Fixed `AttributeError` for `clear_led_suppression_and_update` in `MainWindow.action_animator_play_pause_toggle` by removing the call, as hardware Play/Stop LEDs are currently forced off by `AkaiFireController`.
*   **Dialog Initialization:** Ensured `OLEDCustomizerDialog` correctly loads and displays the current startup font family and size settings when opened.

### 💬 Developer Notes

*   The `OLEDDisplayManager` now uses a dual strategy for font rendering:
    1.  **Resource Fonts (e.g., "TomThumb.ttf"):** Loaded as PIL `ImageFont` and rendered directly by `oled_renderer`.
    2.  **System Fonts:** Rendered by Qt (`QFont`/`QPainter`) to a `QImage`, then converted to a 1-bit PIL `Image` (via `QBuffer` with PNG format), and finally packed by `oled_renderer`. This provides robust system font support.
*   The "Global Pad Brightness" now applies to all physical pad outputs, including those from the Screen Sampler, unless an explicit bypass is implemented for the sampler path in `AkaiFireController.set_multiple_pads_color`. Current implementation defaults to global brightness always applying.

---

## [Version 0.8.0] - 2025-05-19 - Sampler Stability & Preference Refinement

### ✨ Features & Enhancements

*   **Screen Sampler Functionality Restored & Improved:**
    *   **Monitor Selection:** The "Target Monitor" dropdown in the Screen Sampler UI is now fully interactive after connecting to the Akai Fire and toggling ambient sampling ON.
    *   **Preference Loading:** Saved region and adjustment preferences for each monitor are now correctly loaded and applied when the "Configure Region & Adjustments" dialog is opened. Changes made in the dialog for a specific monitor are correctly associated with that monitor.
    *   **Live Preview in Dialog:** The "Configure Region & Adjustments" dialog now correctly shows a live preview of the sampled area (when sampling is active).
    *   Preferences are saved immediately upon change in the configuration dialog and also on application exit.
*   **Modularization and Refactoring:**
    *   Significant refactoring to move screen sampler logic from `MainWindow` into a dedicated `ScreenSamplerManager` and its UI into `ScreenSamplerUIManager`.
    *   `MainWindow` now acts primarily as an orchestrator, improving code organization and maintainability.
*   **Debuggability:** Added more robust import handling and placeholder classes to `ScreenSamplerManager` to aid in diagnosing missing dependencies without immediate crashes during development. Reduced noisy debug prints from previous debugging sessions.

### 🐛 Bug Fixes & Stability

*   **Resolved Critical Initialization Errors:**
    *   Fixed multiple `AttributeError` instances (e.g., `set_monitor_combo_enabled_state`, `set_current_parameters_from_main`) that were occurring due to incorrect method calls or mismatches between component interfaces during `ScreenSamplerManager` and `CapturePreviewDialog` initialization.
    *   Addressed and fixed circular import errors between `screen_sampler_manager.py` and `screen_sampler_ui_manager.py` by correcting self-import patterns.
*   **Fixed Sampler Preference "Snap Back":** Resolved an issue where the "Configure Region & Adjustments" dialog would revert to default or stale settings. This was fixed by:
    *   Ensuring `ScreenSamplerManager` updates its in-memory cache (`self.sampler_monitor_prefs`) immediately when preferences are saved via the dialog.
    *   Using `blockSignals` in `CapturePreviewDialog` during programmatic state updates to prevent premature signal emissions from `MonitorViewWidget` that would overwrite freshly loaded parameters.
*   **Improved Preference Handling Logic:** Refined the logic in `ScreenSamplerManager` for loading `last_active_monitor_key` and applying preferences to ensure it happens robustly after the monitor list is available.
*   **Virtual Environment Usage:** Emphasized and guided setup of a virtual environment, which helped resolve persistent "ghost" errors likely caused by stale bytecode or conflicting global packages.

### Known Issues

*   The "Sampler Recording" feature was previously marked as "CURRENTLY BUGGED". It should now be functional but requires further testing for edge cases.

---

## [Version 0.7.0] - (Date Inferred: Pre-2025-05-19)

### ✨ Features & Enhancements

*   **Sampler Recording Auto-Save & Listing:**
    *   Sampler recordings automatically saved to `presets/sequences/sampler_recordings/`.
    *   Listed with `[Sampler]` prefix in sequence selection.
    *   Newly recorded sequences auto-loaded.
*   **Persistent User Settings for Sampler & Color Picker:**
    *   Screen sampler configurations (region, S/C/B/H) saved per-monitor to `sampler_user_prefs.json`.
    *   Color picker swatches (`fire_controller_config.json`) saved to user config directory via `appdirs`.
*   **Color Picker "My Colors" Swatch Management:**
    *   Right-click context menu for swatches ("Clear", "Set to Current").
*   **Screen Sampler Default Adjustments:**
    *   `CapturePreviewDialog` sliders default to "boosted" look (e.g., 2.0x saturation).

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

### I used Gemini (specifically version from May 2025 timeframe) HEAVILY for basically every stage of this project development, debugging, and refactoring. ( o Y o )