# Changelog - AKAI Fire RGB Controller

## [Version 0.8.0] - 5/19/2025 - Sampler Stability & Preference Refinement

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

*   The "Sampler Recording" feature in the README was previously marked as "CURRENTLY BUGGED". It should now be functional but may require further testing for edge cases. (Updating README to reflect this).

---
*(Previous changelog entries for "Version X.Y.Z (Based on our recent interactions - October 26, 2023 simulated)" and older versions would follow here, reflecting the history from the user's original `CHANGELOG - Copy.md.txt`)*
---

## [Version 0.7.0]

### ✨ Features & Enhancements

*   **Sampler Recording Auto-Save & Listing:**
    *   Sampler recordings are now automatically saved to `presets/sequences/sampler_recordings/` after the user provides a name.
    *   `SequenceFileManager` now scans this directory and lists these recordings with a `[Sampler]` prefix in the sequence selection dropdown.
    *   Newly recorded and auto-saved sequences are immediately loaded into the animator and selected in the dropdown.
    *   `MainWindow.ensure_user_dirs_exist` updated to create `sampler_recordings` directory.
    *   Constants for sequence directory names (`USER_SEQUENCES_DIR_NAME`, etc.) centralized in `sequence_file_manager.py` and imported into `main_window.py` to resolve `NameError`s.
*   **Persistent User Settings for Sampler & Color Picker:**
    *   Implemented saving and loading of screen sampler configurations (region, S/C/B/H adjustments) on a per-monitor basis to `sampler_user_prefs.json`. Monitors are keyed by their geometry string.
    *   `fire_controller_config.json` (for color picker swatches) is now also saved to the platform-specific user configuration directory (or `user_settings/` during development) via `appdirs`.
    *   `MainWindow` now uses a `get_user_config_file_path` helper function to manage these paths.
    *   `ColorPickerManager` now accepts a `config_save_path_func` for standardized config file placement.
*   **Color Picker "My Colors" Swatch Management:**
    *   Added right-click context menu to `ColorSwatchButton` instances to "Clear This Swatch" or "Set to Current Picker Color".
    *   Consolidated "Add to Swatch" and "Clear All Swatches" buttons with icons and improved tooltips/status tips.
*   **Screen Sampler Default Adjustments:**
    *   `CapturePreviewDialog` sliders now default to values that provide a "boosted" look (e.g., 2.0x saturation, 1.5x contrast) for the pads and the preview image. Reset button now reverts to these new defaults. Slider ranges adjusted.

### 🐛 Bug Fixes & Stability

*   **Color Picker Visuals:**
    *   Resolved issue where "My Colors" swatches did not display their saved colors on application startup. Ensured `ColorSwatchButton.set_color()` correctly updates visual style when global QSS is active.
    *   Fixed `NameError: name 'ICON_DELETE' is not defined` in `ColorPickerManager` by making icon constants class attributes.
    *   Corrected `ValueError: too many values to unpack (expected 3)` from `QColor.getHsvF()` calls in `ColorPickerManager` by unpacking all four HSVA components.
    *   Fixed `AttributeError: 'HueSlider' object has no attribute 'set_hue_external'` by updating `ColorPickerManager` to use the correct `HueSlider.set_hue(..., emit_signal=False)` method. `HueSlider.set_hue` updated to support `emit_signal` parameter.
    *   Resolved issue where numeric input fields (R,G,B,Hex) in `ColorPickerManager` were not populating or updating from slider changes. This was primarily due to fixing underlying multiple UI initialization bugs in `MainWindow`.
*   **`NameError` for Directory Constants:** Fixed `NameError` in `MainWindow.ensure_user_dirs_exist()` by correctly importing `USER_SEQUENCES_DIR_NAME`, etc., from `sequence_file_manager.py`.
*   **`SequenceFileManager` Robustness:**
    *   Fixed `NameError: name 'data' is not defined` in `load_all_sequences_metadata` by ensuring `data` variable is initialized correctly within the loop and improving error handling for malformed JSONs.
*   **General Stability (Ongoing for Multiple Inits):**
    *   Addressed several instances of `RuntimeError: wrapped C/C++ object ... has been deleted` by correcting the order of UI initialization and ensuring UI element creation methods (like `_init_direct_controls_right_panel`) are called only once from their designated orchestrator methods (like `_init_managers_right_panel`) within `MainWindow.__init__`. This resolved issues where UI elements were being created multiple times, leading to orphaned objects and crashes.
*   **Fixed `SyntaxError: invalid syntax` in `hue_slider.py`** by removing `--- START OF FILE ---` marker.
*   **Fixed `NameError: name 'QSize' is not defined` in `hue_slider.py`** by adding `QSize` to imports.
*   **Restored "Quick Tools" visibility** by correcting its placement logic in `MainWindow._init_managers_right_panel`.

## Previous Versions (Inferred & AI-Summarized from project history)

### Feature Phase: Sampler Recording Framework
*   Conceptualized and partially implemented sampler recording: UI elements added, `MainWindow` logic to capture frames, prompt for name, and load into animator.

### Feature Phase: Granular Grid Sampling & Monitor View Refinement
*   Implemented 4x16 Gridded Screen Sampling.
*   Resizable & Snappable `MonitorViewWidget`.
*   Fixed Screen Sampler Preview Color Discrepancy.

### Feature Phase: Interactive Screen Sampler MVP
*   Introduced `CapturePreviewDialog` with `MonitorViewWidget`.
*   Added S/C/B/H sliders affecting sampler output and a live preview image.

### Bugfix & Refactor Phase: JSON Loading, Recursion, UI Glitches
*   Robust JSON Loading for static layouts and color picker.
*   Animator recursion fixes.
*   `SequenceModel` Undo/Redo & `is_modified` flag improvements.

### Feature Phase: Animator UI Enhancements & Core Logic
*   `SequenceTimelineWidget` with frame thumbnails.
*   `SequenceControlsWidget` with animation speed slider.

### Major Refactoring & Early Bug Squashing
*   `MainWindow` Refactor for modularity (ColorPickerManager, StaticLayoutsManager, etc.).
*   Resolved numerous early `NameError`s, `AttributeError`s.

### Initial Development Phase
*   Project Setup, Hardware Control, GUI Foundation, Static Layouts (Initial), Animator (Initial).

### I used Gemini 2.5 HEAVILY for basically every stage of this ....  ( o Y o )