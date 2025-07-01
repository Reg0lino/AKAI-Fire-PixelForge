# AKAI_Fire_RGB_Controller/gui/screen_sampler_manager.py
import os
import sys
import json
import mss
import time
from PyQt6.QtCore import QObject, pyqtSignal, QTimer
# Keep these for dialogs shown by SSM
from PyQt6.QtWidgets import QMessageBox, QInputDialog
from PyQt6.QtGui import QColor
from PIL import Image
# --- GUI Component Imports ---
try:
    from gui.screen_sampler_ui_manager import ScreenSamplerUIManager
    from gui.capture_preview_dialog import CapturePreviewDialog
    from gui.set_max_frames_dialog import SetMaxFramesDialog
    from animator.model import SequenceModel, AnimationFrame
    from gui.ambient_mode_settings_dialog import AmbientModeSettingsDialog
    GUI_IMPORTS_OK = True
except ImportError as e:
    print(
        f"CRITICAL ERROR (ScreenSamplerManager): Could not import essential GUI/Model components: {e}")
    GUI_IMPORTS_OK = False
    # Placeholder definitions (as you had them)

    class ScreenSamplerUIManager(QObject):  # ... (minimal placeholder) ...
        sampling_control_changed = pyqtSignal(bool, dict)
        status_message_requested = pyqtSignal(str, int)
        request_monitor_list_population = pyqtSignal()
        show_capture_preview_requested = pyqtSignal()
        record_button_clicked = pyqtSignal()
        set_max_frames_button_clicked = pyqtSignal()
        enable_sampling_button = None
        def __init__(self, parent=None): super().__init__(parent)
        def set_overall_enabled_state(self, enabled): pass
        def populate_monitors_combo_external(self, monitors): pass
        def set_selected_monitor_ui(self, monitor_id): pass
        def set_sampling_frequency_ui(self, freq_ms): pass
        def update_record_button_ui(self, is_recording, can_record): pass
        def set_recording_status_text(self, text): pass
        def force_disable_sampling_ui(self): pass
        def isEnabled(self): return False
        def setEnabled(self, enabled): pass

    class CapturePreviewDialog(QObject):  # ... (minimal placeholder) ...
        sampling_parameters_changed = pyqtSignal(dict)
        dialog_closed = pyqtSignal()
        def __init__(self, parent=None): super().__init__(parent)
        def set_initial_monitor_data(self, monitors, current_id): pass
        def set_current_parameters_from_main(self, params): pass
        def update_preview_image(self, img): pass
        def isVisible(self): return False
        def show(self): pass
        def activateWindow(self): pass
        def raise_(self): pass
        def close(self): pass
        def deleteLater(self): pass

    class SetMaxFramesDialog(QObject):  # ... (minimal placeholder) ...
        @staticmethod
        def get_max_frames(
            parent_widget, current_value): return current_value, False

    class SequenceModel:  # ... (minimal placeholder) ...
        def __init__(self, name=""): self.name = name; self.frames = [
        ]; self.frame_delay_ms = 0; self.loop = False

        def save_to_file(self, path): return False

    class AnimationFrame:  # ... (minimal placeholder) ...
        def __init__(self, colors=None): self.colors = colors or []

# --- Feature Component Imports ---
try:
    from features.screen_sampler_core import ScreenSamplerCore
    from features.screen_sampler_thread import ScreenSamplerThread
    FEATURES_IMPORTS_OK = True
except ImportError as e:
    print(
        f"Warning (ScreenSamplerManager): Could not import feature components: {e}. Using placeholders.")
    FEATURES_IMPORTS_OK = False

    class ScreenSamplerCore:  # ... (minimal placeholder) ...
        DEFAULT_ADJUSTMENTS = {'brightness': 1.0, 'contrast': 1.0,
                                'saturation': 1.0, 'hue_shift': 0}  # Ensure defaults exist
        NUM_GRID_ROWS = 4
        NUM_GRID_COLS = 16
        @staticmethod
        def get_available_monitors(sct_instance): return []

    class ScreenSamplerThread(QObject):  # ... (minimal placeholder) ...
        pad_colors_sampled = pyqtSignal(list)
        processed_image_ready = pyqtSignal(object)
        error_occurred = pyqtSignal(str)
        def __init__(self, parent=None): super().__init__(parent)
        def start_sampling(self, **kwargs): pass
        def stop_sampling(self, **kwargs): pass
        def isRunning(self): return False

# --- Constants ---
SAMPLER_PREFS_FILENAME = "sampler_user_prefs.json"
APP_NAME_FOR_CONFIG = "AKAI_Fire_RGB_Controller"
APP_AUTHOR_FOR_CONFIG = "YourProjectAuthorName"  # Replace if needed
DEFAULT_SAMPLING_FPS = 20


class ScreenSamplerManager(QObject):
    sampled_colors_for_display = pyqtSignal(list)
    processed_image_for_preview = pyqtSignal(
        Image.Image if GUI_IMPORTS_OK and 'Image' in globals() else object)
    sampler_status_update = pyqtSignal(str, int)
    sampling_activity_changed = pyqtSignal(bool)
    new_sequence_from_recording_ready = pyqtSignal(str)
    sampler_monitor_display_name_changed = pyqtSignal(str)
    # Emits the full 'adjustments' dictionary
    sampler_adjustments_changed = pyqtSignal(dict)
    sampler_parameters_updated_externally = pyqtSignal(dict)

    def __init__(self,
                presets_base_path: str,
                animator_manager_ref,
                parent: QObject | None = None):
        super().__init__(parent)
        self.presets_base_path = presets_base_path
        self.animator_manager_ref = animator_manager_ref
        self.is_sampling_thread_active = False
        self.is_actively_recording = False
        self.screen_sampler_monitor_list_cache = []
        self.current_sampler_params = {
            'monitor_id': 1,
            'region_rect_percentage': {'x': 0.4, 'y': 0.4, 'width': 0.2, 'height': 0.2},
            'adjustments': ScreenSamplerCore.DEFAULT_ADJUSTMENTS.copy(),
            'frequency_ms': self._fps_to_ms(DEFAULT_SAMPLING_FPS),
            'sampling_mode': 'grid'  # Add this new key
        }
        self.sampler_monitor_prefs = {}
        self._emit_status_on_next_stop: bool = True
        self.recorded_sampler_frames: list[list[str]] = []
        self.current_recording_frame_count: int = 0
        self.captured_sampler_frequency_ms: int = self.current_sampler_params['frequency_ms']
        self.MAX_RECORDING_FRAMES: int = 200
        # Assuming parent=None is okay if it's not added to a layout by SSM
        self.ui_manager = ScreenSamplerUIManager(parent=None)
        self.sampling_thread = ScreenSamplerThread(parent=self)
        self.visual_sampler_dialog: CapturePreviewDialog | None = None
        self.ambient_settings_dialog: AmbientModeSettingsDialog | None = None
        self._last_processed_pil_image: Image.Image | None = None
        self._config_dir_path = self._get_user_config_dir_path()
        self.sampler_prefs_file_path = os.path.join(
            self._config_dir_path, SAMPLER_PREFS_FILENAME)
        # This calls _apply_prefs_for_current_monitor which might emit
        self._load_sampler_preferences()
        self.ui_manager.set_sampling_mode_ui(
            self.current_sampler_params.get('sampling_mode', 'grid'))
        self._connect_signals()
        # Connect sampler_adjustments_changed to update dialog sliders if visible
        self.sampler_adjustments_changed.connect(
            self._update_preview_dialog_sliders_if_visible)
        if hasattr(self.ui_manager, 'set_sampling_frequency_ui'):
            self.ui_manager.set_sampling_frequency_ui(
                self.current_sampler_params['frequency_ms'])
        if hasattr(self.ui_manager, 'update_record_button_ui'):
            self.ui_manager.update_record_button_ui(
                is_recording=False, can_record=False)
        if hasattr(self.ui_manager, 'set_recording_status_text'):
            self.ui_manager.set_recording_status_text(
                "Sampler Off / Device Disconnected")

    def _get_user_config_dir_path(self) -> str:  # Unchanged
        config_dir_to_use = ""
        try:
            is_packaged = getattr(
                sys, 'frozen', False) and hasattr(sys, '_MEIPASS')
            if is_packaged:
                from appdirs import user_config_dir
                config_dir_to_use = user_config_dir(
                    APP_NAME_FOR_CONFIG, APP_AUTHOR_FOR_CONFIG)
            else:
                current_file_dir = os.path.dirname(os.path.abspath(__file__))
                project_root = os.path.dirname(current_file_dir)
                config_dir_to_use = os.path.join(project_root, "user_settings")
            os.makedirs(config_dir_to_use, exist_ok=True)
            return config_dir_to_use
        except Exception:
            fallback_dir = os.path.join(
                os.getcwd(), "user_settings_sampler_fallback")
            os.makedirs(fallback_dir, exist_ok=True)
            return fallback_dir

    def get_ui_widget(
        self) -> ScreenSamplerUIManager: return self.ui_manager  # Unchanged

    def update_start_button_state(self, enabled: bool):
        """
        Public method to allow MainWindow to control the enabled state of the
        'Sampling' button within this manager's UI component.
        This provides compatibility with the main window's state controller.
        """
        if self.ui_manager and hasattr(self.ui_manager, 'enable_sampling_button'):
            self.ui_manager.enable_sampling_button.setEnabled(enabled)

    def _connect_signals(self):
        if not GUI_IMPORTS_OK or not FEATURES_IMPORTS_OK: return
        # UI Manager Signals
        self.ui_manager.sampling_control_changed.connect(self._handle_ui_sampling_control_changed)
        # self.ui_manager.request_monitor_list_population.connect(self.populate_monitor_list_for_ui) # <<< REMOVED: This is now called explicitly on connect
        self.ui_manager.show_capture_preview_requested.connect(self._show_configuration_dialog)
        self.ui_manager.record_button_clicked.connect(self._on_ui_record_button_clicked)
        self.ui_manager.set_max_frames_button_clicked.connect(self._on_ui_set_max_frames_button_clicked)
        self.ui_manager.status_message_requested.connect(self.sampler_status_update)
        # Connect the new UI Cycle Monitor button
        self.ui_manager.request_cycle_monitor.connect(self.cycle_target_monitor) # <<< NEW
        # Sampling Thread Signals
        self.sampling_thread.pad_colors_sampled.connect(self._handle_thread_pad_colors_sampled)
        self.sampling_thread.processed_image_ready.connect(self._handle_thread_processed_image_ready)
        self.sampling_thread.error_occurred.connect(self._handle_thread_error_occurred)
        if hasattr(self.sampling_thread, 'finished'):
            self.sampling_thread.finished.connect(self._on_thread_finished)
        # Connect the sampler_adjustments_changed signal to update dialog sliders if visible
        self.sampler_adjustments_changed.connect(self._update_preview_dialog_sliders_if_visible)

    def get_current_adjustments(self) -> dict:
        """
        Safely returns a copy of the current sampler's adjustment parameters.
        This allows other parts of the UI, like MainWindow, to sync with the sampler's state.
        """
        # The 'adjustments' are stored within the larger 'current_sampler_params' dictionary.
        # We provide a fallback to the defaults from ScreenSamplerCore just in case.
        return self.current_sampler_params.get('adjustments', ScreenSamplerCore.DEFAULT_ADJUSTMENTS).copy()

    def update_sampler_adjustment(self, adjustment_key: str, new_value: float):
        """
        Updates a specific sampler adjustment (brightness, contrast, saturation, hue_shift).
        Called by MainWindow when corresponding GUI knob is changed.
        """
        if adjustment_key not in self.current_sampler_params['adjustments']:
            print(
                f"SSM WARNING: Invalid adjustment key '{adjustment_key}' in update_sampler_adjustment.")
            return
        # Potentially clamp or validate new_value based on adjustment_key if necessary
        # For now, assume MainWindow sends valid, mapped values.
        self.current_sampler_params['adjustments'][adjustment_key] = new_value
        # print(f"SSM INFO: Sampler adjustment '{adjustment_key}' updated to {new_value}")
        # Save the change to persistent storage for this monitor
        self._save_prefs_for_current_monitor()
        # If sampling is currently active, restart the thread with the new parameters
        if self.is_sampling_thread_active:
            self._synchronize_and_control_sampling_thread(True)
        # Emit signal so MainWindow can update its knobs if this change came from somewhere else (e.g., dialog)
        # or to confirm the change if it came from a knob.
        self.sampler_adjustments_changed.emit(
            self.current_sampler_params['adjustments'].copy())

    def _apply_prefs_for_current_monitor(self):
        """
        Applies saved preferences for the currently active monitor AND mode.
        If no preferences exist, it creates and applies defaults.
        """
        monitor_key = self._generate_monitor_key(
            self.current_sampler_params['monitor_id'])
        current_mode = self.current_sampler_params.get('sampling_mode', 'grid')
        # Get the full preferences for the current monitor, or a new empty dict
        monitor_prefs = self.sampler_monitor_prefs.get(monitor_key, {})
        # Set region (only used by grid mode, but harmless to set for others)
        self.current_sampler_params['region_rect_percentage'] = monitor_prefs.get(
            'region_rect_percentage', {'x': 0.4, 'y': 0.4, 'width': 0.2, 'height': 0.2})
        # --- NEW PER-MODE LOGIC ---
        # Get the adjustments dictionary for ALL modes, or a new empty dict
        all_mode_adjustments = monitor_prefs.get('adjustments', {})
        # Get the specific adjustments for the CURRENT mode
        mode_specific_adjustments = all_mode_adjustments.get(current_mode)
        if mode_specific_adjustments:
            # If we have saved adjustments for this specific mode, use them
            self.current_sampler_params['adjustments'] = mode_specific_adjustments.copy(
            )
        else:
            # Otherwise, use the global defaults and they will be saved for this mode later
            self.current_sampler_params['adjustments'] = ScreenSamplerCore.DEFAULT_ADJUSTMENTS.copy(
            )
        # Emit signal so UI (like main window knobs) can update
        self.sampler_adjustments_changed.emit(
            self.current_sampler_params['adjustments'].copy())

    def _save_prefs_for_current_monitor(self):
        """Saves the current parameters (region/adjustments) for the currently active monitor and mode."""
        monitor_key = self._generate_monitor_key(self.current_sampler_params['monitor_id'])
        current_mode = self.current_sampler_params.get('sampling_mode', 'grid')
        if monitor_key:
            # Ensure the top-level key for the monitor exists
            if monitor_key not in self.sampler_monitor_prefs:
                self.sampler_monitor_prefs[monitor_key] = {}
            
            # Ensure the 'adjustments' sub-dictionary exists
            if 'adjustments' not in self.sampler_monitor_prefs[monitor_key]:
                self.sampler_monitor_prefs[monitor_key]['adjustments'] = {}
            # Save the current adjustments under the specific key for the current mode
            self.sampler_monitor_prefs[monitor_key]['adjustments'][current_mode] = self.current_sampler_params['adjustments'].copy()
            # Also save the region (for grid mode)
            self.sampler_monitor_prefs[monitor_key]['region_rect_percentage'] = self.current_sampler_params['region_rect_percentage'].copy()
            # Persist the entire preferences structure to disk
            self._save_sampler_preferences_to_file()
            
        # Emit signal so UI (like main window knobs) can update
        self.sampler_adjustments_changed.emit(self.current_sampler_params['adjustments'].copy())

    def _on_thread_finished(self):
        """
        Handles the graceful shutdown of the sampling thread. This is connected
        to the thread's 'finished' signal or called directly if the thread was
        already stopped. It respects the _emit_status_on_next_stop flag.
        """
        # Read the flag to determine if a status message should be shown.
        should_emit_status = self._emit_status_on_next_stop
        # Update internal state and emit signals.
        self.is_sampling_thread_active = False
        self.sampling_activity_changed.emit(False) # Let MainWindow know the state changed
        # Update the UI elements within this manager.
        if GUI_IMPORTS_OK and hasattr(self.ui_manager, 'update_record_button_ui') and hasattr(self.ui_manager, 'set_recording_status_text'):
            self.ui_manager.update_record_button_ui(is_recording=False, can_record=False)
            self.ui_manager.set_recording_status_text("Sampler OFF")
        # Show status message ONLY if requested.
        if should_emit_status:
            self.sampler_status_update.emit("Screen sampling stopped.", 2000)
        # IMPORTANT: Reset the flag to its default state for the next operation.
        self._emit_status_on_next_stop = True

    def open_config_dialog(self):
        """
        Public slot to allow external widgets (like the main menu bar)
        to trigger the opening of the configuration dialog by programmatically
        clicking the button on the UI manager widget.
        """
        if self.ui_manager and hasattr(self.ui_manager, 'configure_preview_button'):
            # This is the restored, correct logic: the manager tells its UI to "click" its own button.
            self.ui_manager.configure_preview_button.click()
        else:
            self.sampler_status_update.emit(
                "Cannot open config: UI not ready.", 3000)

    def set_overall_enabled_state(self, enabled_from_main_window: bool, device_connected: bool):
        if not GUI_IMPORTS_OK:
            return
        sampler_core_can_be_active = enabled_from_main_window and device_connected
        if hasattr(self.ui_manager, 'set_overall_enabled_state'):
            self.ui_manager.set_overall_enabled_state(
                sampler_core_can_be_active)
        else:
            print(
                f"WARNING (SSM.set_overall_enabled_state): self.ui_manager missing 'set_overall_enabled_state'")
        if sampler_core_can_be_active:
            if not self.screen_sampler_monitor_list_cache:
                self.populate_monitor_list_for_ui()
        else:
            if self.is_sampling_thread_active:
                self._synchronize_and_control_sampling_thread(False)
        if not hasattr(self.ui_manager, 'set_recording_status_text') or \
                not hasattr(self.ui_manager, 'update_record_button_ui'):
            print(
                f"WARNING (SSM.set_overall_enabled_state): self.ui_manager missing text/button update methods")
            return
        if not device_connected:
            self.ui_manager.set_recording_status_text("Device Disconnected")
            self.ui_manager.update_record_button_ui(
                is_recording=False, can_record=False)
        elif not sampler_core_can_be_active:
            self.ui_manager.set_recording_status_text("Sampler UI Disabled")
            self.ui_manager.update_record_button_ui(
                is_recording=False, can_record=False)
        elif not self.is_sampling_thread_active:
            self.ui_manager.set_recording_status_text("Sampler OFF")
            self.ui_manager.update_record_button_ui(
                is_recording=False, can_record=False)
        elif self.is_actively_recording:
            self.ui_manager.set_recording_status_text(
                f"REC 🔴 {self.current_recording_frame_count}/{self.MAX_RECORDING_FRAMES}")
            self.ui_manager.update_record_button_ui(
                is_recording=True, can_record=False)
        else:
            self.ui_manager.set_recording_status_text("Idle. Ready to record.")
            self.ui_manager.update_record_button_ui(
                is_recording=False, can_record=True)

    def update_ui_for_global_state(self, overall_sampler_ui_enabled: bool, can_toggle_sampling_button_enabled: bool):
        """
        Updates the ScreenSamplerUIManager based on global application state.
        - overall_sampler_ui_enabled: Should the main sampler groupbox be enabled (e.g., based on MIDI connection).
        - can_toggle_sampling_button_enabled: Specific flag for the 'Toggle Ambient Sampling' button 
                                                (e.g., disabled if animator is playing).
        """
        if not GUI_IMPORTS_OK or not hasattr(self.ui_manager, 'set_overall_enabled_state'):
            return
        # 1. Set the overall enabled state of the sampler's QGroupBox UI
        self.ui_manager.set_overall_enabled_state(overall_sampler_ui_enabled)
        # 2. Specifically set the enabled state of the "Toggle Ambient Sampling" button
        if hasattr(self.ui_manager, 'enable_sampling_button') and self.ui_manager.enable_sampling_button:
            # If overall_sampler_ui_enabled is False, the button will be disabled by its parent QGroupBox.
            # This logic primarily handles the case where the group *is* enabled, but the toggle specifically
            # needs to be controlled (e.g., by animator playback).
            actual_toggle_button_state = overall_sampler_ui_enabled and can_toggle_sampling_button_enabled
            self.ui_manager.enable_sampling_button.setEnabled(
                actual_toggle_button_state)
            # If the toggle button is being disabled WHILE it's checked (i.e., sampling is active),
            # then force sampling off.
            if not actual_toggle_button_state and self.ui_manager.enable_sampling_button.isChecked():
                self.ui_manager.enable_sampling_button.setChecked(
                    False)  # This will trigger its toggle signal
        # and ScreenSamplerManager will stop sampling.
        # 3. Update other sampler UI elements like record button based on current states
        #    The set_overall_enabled_state method in ScreenSamplerUIManager already handles
        #    some of this, but we might need to re-evaluate its internal logic or call it here.
        #    For now, relying on ScreenSamplerUIManager's set_overall_enabled_state to cascade
        #    and its internal logic reacting to the enable_sampling_button state.
        #    We might also need to refresh the record button state specifically.
        if hasattr(self.ui_manager, 'update_record_button_ui'):
            self.ui_manager.update_record_button_ui(
                is_recording=self.is_actively_recording,
                can_record=(overall_sampler_ui_enabled and
                            can_toggle_sampling_button_enabled and
                            self.is_sampling_thread_active and
                            not self.is_actively_recording) or
                (overall_sampler_ui_enabled and
                self.is_actively_recording)  # Can always stop if recording
            )
        # Update configure button state too (might be part of ui_manager.set_overall_enabled_state)
        if hasattr(self.ui_manager, 'configure_preview_button') and self.ui_manager.configure_preview_button:
            self.ui_manager.configure_preview_button.setEnabled(
                overall_sampler_ui_enabled)

    def is_sampling_active(self) -> bool:
        return self.is_sampling_thread_active

    def is_currently_recording(self) -> bool:
        return self.is_actively_recording

    def _handle_ui_sampling_control_changed(self, enable_toggle: bool, basic_ui_params: dict):
        """
        Orchestrates sampler state changes. Handles state updates when sampler is
        off, and restarts the thread on parameter changes when it's on.
        """
        # --- THE FIX: We need to know if parameters changed while the sampler was ON ---
        params_changed_while_active = False
        if self.is_sampling_thread_active and enable_toggle:
            # Check if any key parameter from the UI is different from our current state
            if (basic_ui_params.get('monitor_capture_id') != self.current_sampler_params.get('monitor_id') or
                basic_ui_params.get('sampling_mode') != self.current_sampler_params.get('sampling_mode') or
                    basic_ui_params.get('frequency_ms') != self.current_sampler_params.get('frequency_ms')):
                params_changed_while_active = True
        # Always update internal params with the latest from the UI, regardless of state.
        self.current_sampler_params.update(basic_ui_params)
        # If the mode or monitor changed, we need to load the correct adjustments for it.
        # This is safe to run even if the values are the same.
        self._apply_prefs_for_current_monitor()
        # If we are simply disabling the sampler, stop the thread and save.
        if not enable_toggle:
            self._synchronize_and_control_sampling_thread(False)
            self._save_sampler_preferences_to_file()
            return
        # --- Logic for ENABLING or UPDATING the sampler ---
        # If this is the initial "turn on" press, ensure monitor data is available.
        if not self.is_sampling_thread_active:
            if not self.screen_sampler_monitor_list_cache:
                self.populate_monitor_list_for_ui(force_fetch=True)
                if not self.screen_sampler_monitor_list_cache:
                    self.sampler_status_update.emit(
                        "Cannot start sampler: No monitors found.", 3000)
                    if hasattr(self.ui_manager, 'force_disable_sampling_ui'):
                        self.ui_manager.force_disable_sampling_ui()
                    return
        # Save the current state (it might be new if we just turned on or changed params).
        self._save_sampler_preferences_to_file()
        # Start the thread if it's not running, or restart it if parameters changed while it was active.
        if not self.is_sampling_thread_active or params_changed_while_active:
            self._synchronize_and_control_sampling_thread(True)

    def populate_monitor_list_for_ui(self, force_fetch: bool = False):
        """
        Fetches the monitor list and updates the current_sampler_params.
        Also emits a signal to update the UI display label.
        """
        if not GUI_IMPORTS_OK or not FEATURES_IMPORTS_OK: return
            
        needs_fetch = force_fetch or not self.screen_sampler_monitor_list_cache
        if needs_fetch:
            try:
                with mss.mss() as sct:
                    self.screen_sampler_monitor_list_cache = ScreenSamplerCore.get_available_monitors(sct)
                if not self.screen_sampler_monitor_list_cache:
                    self.sampler_status_update.emit("No monitors detected for screen sampler.", 3000)
            except Exception as e:
                self.sampler_status_update.emit(f"Error getting monitor list: {e}", 5000)
                self.screen_sampler_monitor_list_cache = []
        # After fetching, ensure current_sampler_params['monitor_id'] is valid or defaults.
        # This makes sure we don't start with a monitor ID that no longer exists.
        if self.screen_sampler_monitor_list_cache:
            current_id_exists = any(m['id'] == self.current_sampler_params['monitor_id'] for m in self.screen_sampler_monitor_list_cache)
            if not current_id_exists:
                # Default to the first monitor found if the saved one doesn't exist.
                self.current_sampler_params['monitor_id'] = self.screen_sampler_monitor_list_cache[0]['id']
        else:
            self.current_sampler_params['monitor_id'] = 1 # Fallback to 1 if no monitors found
        # --- NEW: Update the UI display name immediately ---
        current_monitor_info = next(
            (m for m in self.screen_sampler_monitor_list_cache if m['id'] == self.current_sampler_params['monitor_id']),
            {'name': 'No Monitor', 'id': 0, 'width': 0, 'height': 0} # Fallback info
        )
        display_name = current_monitor_info.get('name', f"Monitor {current_monitor_info.get('id', '?')}")
        self.sampler_monitor_display_name_changed.emit(display_name)
        
        # If the visual dialog is open, update its initial monitor data
        if self.visual_sampler_dialog and self.visual_sampler_dialog.isVisible():
            if hasattr(self.visual_sampler_dialog, 'set_initial_monitor_data'):
                self.visual_sampler_dialog.set_initial_monitor_data(
                    self.screen_sampler_monitor_list_cache,
                    self.current_sampler_params['monitor_id']
                )

    def toggle_sampling_state(self):
        """Toggles the screen sampler ON or OFF."""
        if not GUI_IMPORTS_OK or not hasattr(self.ui_manager, 'enable_sampling_button'):
            print(
                "SSM ERROR: UI Manager or toggle button not available for toggle_sampling_state.")
            self.sampler_status_update.emit(
                "Error: Sampler UI not ready.", 3000)
            return
        current_state_is_on = self.ui_manager.enable_sampling_button.isChecked()
        new_state_to_set = not current_state_is_on
        # print(f"SSM TRACE: toggle_sampling_state called. Current visual state is ON: {current_state_is_on}. Setting to: {new_state_to_set}") # Optional
        # Update the UI button state, which in turn triggers _handle_ui_sampling_control_changed
        # This ensures the logic flow is consistent with a GUI click.
        if hasattr(self.ui_manager.enable_sampling_button, 'setChecked'):
            self.ui_manager.enable_sampling_button.setChecked(new_state_to_set)
        # Fallback if button is somehow not checkable (should not happen)
        else:
            self._handle_ui_sampling_control_changed(new_state_to_set, {
                'monitor_capture_id': self.current_sampler_params.get('monitor_id', 1),
                'frequency_ms': self.current_sampler_params.get('frequency_ms', self._fps_to_ms(DEFAULT_SAMPLING_FPS))
            })
        # Status update is handled by _synchronize_and_control_sampling_thread via _handle_ui_sampling_control_changed

    def cycle_target_monitor(self):
        """Cycles to the next available monitor for sampling."""
        if not self.screen_sampler_monitor_list_cache:
            self.populate_monitor_list_for_ui(force_fetch=True) # Attempt to populate if empty
            if not self.screen_sampler_monitor_list_cache:
                self.sampler_status_update.emit("No monitors available to cycle.", 3000)
                return
        if len(self.screen_sampler_monitor_list_cache) <= 1:
            self.sampler_status_update.emit("Only one monitor available.", 2000)
            current_monitor_info = next(
                (m for m in self.screen_sampler_monitor_list_cache if m['id'] == self.current_sampler_params['monitor_id']), None)
            if current_monitor_info:
                display_name = current_monitor_info.get('name', f"Monitor {current_monitor_info.get('id', '?')}")
                self.sampler_monitor_display_name_changed.emit(display_name) # Ensure UI is updated even if no cycle
            return
        current_monitor_id = self.current_sampler_params.get('monitor_id', 1)
        current_idx = next((i for i, m in enumerate(self.screen_sampler_monitor_list_cache) if m['id'] == current_monitor_id), -1)
        next_idx = (current_idx + 1) % len(self.screen_sampler_monitor_list_cache)
        new_monitor_info = self.screen_sampler_monitor_list_cache[next_idx]
        new_monitor_id = new_monitor_info['id']
        self.current_sampler_params['monitor_id'] = new_monitor_id
        self._apply_prefs_for_current_monitor() # Apply prefs for the new monitor
        # If sampler is active, restart thread to apply new monitor
        if self.is_sampling_thread_active:
            self._synchronize_and_control_sampling_thread(True)
        # --- NEW: Emit signal to update UI's display label ---
        new_monitor_name = new_monitor_info.get('name', f"Monitor {new_monitor_id}")
        self.sampler_monitor_display_name_changed.emit(new_monitor_name)
        self.sampler_status_update.emit(f"Sampler switched to: {new_monitor_name}", 2500)
        # This signal is for dialogs that need to update their own state after external monitor changes.
        self.sampler_parameters_updated_externally.emit(self.current_sampler_params)

    def cycle_sampling_mode(self):
        """
        Cycles to the next available sampling mode in the UI dropdown.
        This is typically triggered by a hardware button.
        """
        if not self.ui_manager: return # Safety check
        # Get the current index and count of items in the mode dropdown
        current_idx = self.ui_manager.sampling_mode_combo.currentIndex()
        item_count = self.ui_manager.sampling_mode_combo.count()
        if item_count <= 1:
            self.sampler_status_update.emit("Only one sampling mode available.", 2000)
            return
        # Calculate the next index
        next_idx = (current_idx + 1) % item_count
        # Set the new index in the UI dropdown.
        # This will automatically trigger _on_setting_changed in the UI manager,
        # which will then emit sampling_control_changed, updating the manager's state.
        self.ui_manager.sampling_mode_combo.setCurrentIndex(next_idx)
        
        # Get the new mode's display name for status update
        new_mode_name = self.ui_manager.sampling_mode_combo.currentText()
        self.sampler_status_update.emit(f"Sampling Mode: {new_mode_name}", 2500)

    def _show_configuration_dialog(self):
        """
        Shows the appropriate configuration dialog based on the currently
        selected sampling mode, pulling the latest state from the UI.
        """
        if not GUI_IMPORTS_OK: return
        # --- PROACTIVE PULL ---
        # Get the latest parameters from the UI right before opening the dialog.
        latest_params = self.ui_manager.get_current_ui_parameters()
        self.current_sampler_params.update(latest_params)
        mode = self.current_sampler_params.get('sampling_mode', 'grid')
        # Ensure monitor data is available for all modes
        if not self.screen_sampler_monitor_list_cache:
            self.populate_monitor_list_for_ui(force_fetch=True)
            if not self.screen_sampler_monitor_list_cache:
                QMessageBox.warning(self.ui_manager, "Monitor Info", "No monitor data available for sampler.")
                return
        self._apply_prefs_for_current_monitor()
        if mode == 'grid':
            if not self.visual_sampler_dialog:
                self.visual_sampler_dialog = CapturePreviewDialog(parent=self.ui_manager)
                self.visual_sampler_dialog.sampling_parameters_changed.connect(self._handle_dialog_params_changed)
                self.visual_sampler_dialog.dialog_closed.connect(self._on_visual_sampler_dialog_closed)
                self.sampler_parameters_updated_externally.connect(self.visual_sampler_dialog.set_current_parameters_from_main)
                if self.sampler_adjustments_changed:
                    self.sampler_adjustments_changed.connect(self.visual_sampler_dialog.update_sliders_from_external_adjustments)
            self.visual_sampler_dialog.set_initial_monitor_data(
                self.screen_sampler_monitor_list_cache,
                self.current_sampler_params['monitor_id']
            )
            self.visual_sampler_dialog.set_current_parameters_from_main(self.current_sampler_params)
            if self._last_processed_pil_image:
                self.visual_sampler_dialog.update_preview_image(self._last_processed_pil_image)
            self.visual_sampler_dialog.show()
            self.visual_sampler_dialog.activateWindow()
            self.visual_sampler_dialog.raise_()
        else: # For 'thumbnail' and 'palette' modes
            if not self.ambient_settings_dialog:
                self.ambient_settings_dialog = AmbientModeSettingsDialog(parent=self.ui_manager)
                self.ambient_settings_dialog.sampling_parameters_changed.connect(self._handle_dialog_params_changed)
                self.ambient_settings_dialog.cycle_monitor_requested.connect(
                    self.cycle_target_monitor)
                self.ambient_settings_dialog.dialog_closed.connect(
                    self._on_ambient_settings_dialog_closed)
                if self.sampler_adjustments_changed:
                    self.sampler_adjustments_changed.connect(
                        self.ambient_settings_dialog.update_sliders_from_external_adjustments)
                self.ambient_settings_dialog.dialog_closed.connect(self._on_ambient_settings_dialog_closed)
                if self.sampler_adjustments_changed:
                    self.sampler_adjustments_changed.connect(self.ambient_settings_dialog.update_sliders_from_external_adjustments)
            self.ambient_settings_dialog.set_current_parameters_from_main(self.current_sampler_params)
            self.ambient_settings_dialog.show()
            self.ambient_settings_dialog.activateWindow()
            self.ambient_settings_dialog.raise_()

    def _on_visual_sampler_dialog_closed(self):
        if self.visual_sampler_dialog:
            # Safely disconnect all signals to prevent dangling references
            try: self.visual_sampler_dialog.sampling_parameters_changed.disconnect(self._handle_dialog_params_changed)
            except TypeError: pass
            try: self.visual_sampler_dialog.dialog_closed.disconnect(self._on_visual_sampler_dialog_closed)
            except TypeError: pass
            try: self.sampler_parameters_updated_externally.disconnect(self.visual_sampler_dialog.set_current_parameters_from_main)
            except TypeError: pass
            if self.sampler_adjustments_changed:
                try: self.sampler_adjustments_changed.disconnect(self.visual_sampler_dialog.update_sliders_from_external_adjustments)
                except TypeError: pass
            self.visual_sampler_dialog.deleteLater()
            self.visual_sampler_dialog = None

    def _on_ambient_settings_dialog_closed(self):
        if self.ambient_settings_dialog:
            try: self.ambient_settings_dialog.sampling_parameters_changed.disconnect(self._handle_dialog_params_changed)
            except TypeError: pass
            # --- ADD THE DISCONNECT ---
            try: self.ambient_settings_dialog.cycle_monitor_requested.disconnect(self.cycle_target_monitor)
            except TypeError: pass
            try: self.ambient_settings_dialog.dialog_closed.disconnect(self._on_ambient_settings_dialog_closed)
            except TypeError: pass
            if self.sampler_adjustments_changed:
                try: self.sampler_adjustments_changed.disconnect(self.ambient_settings_dialog.update_sliders_from_external_adjustments)
                except TypeError: pass
            self.ambient_settings_dialog.deleteLater()
            self.ambient_settings_dialog = None

    def _handle_dialog_params_changed(self, dialog_params: dict):
        """
        Universal handler for parameter changes from ANY dialog.
        """
        new_monitor_id = dialog_params.get('monitor_id', self.current_sampler_params['monitor_id'])
        
        if new_monitor_id != self.current_sampler_params['monitor_id']:
            self.current_sampler_params['monitor_id'] = new_monitor_id
            self._apply_prefs_for_current_monitor()
            if self.visual_sampler_dialog and self.visual_sampler_dialog.isVisible():
                self.visual_sampler_dialog.set_current_parameters_from_main(self.current_sampler_params)
            
            # --- REMOVED: No longer need to call set_selected_monitor_ui here ---
            # self.ui_manager.set_selected_monitor_ui(self.current_sampler_params['monitor_id']) 
            
            # Emit signal to update UI's monitor display label
            current_monitor_info = next(
                (m for m in self.screen_sampler_monitor_list_cache if m['id'] == new_monitor_id), None)
            if current_monitor_info:
                display_name = current_monitor_info.get('name', f"Monitor {current_monitor_info.get('id', '?')}")
                self.sampler_monitor_display_name_changed.emit(display_name)
        else:
            if 'region_rect_percentage' in dialog_params:
                self.current_sampler_params['region_rect_percentage'] = dialog_params['region_rect_percentage']
            if 'adjustments' in dialog_params:
                self.current_sampler_params['adjustments'] = dialog_params['adjustments'].copy()
        self._save_prefs_for_current_monitor()
        
        if self.is_sampling_thread_active:
            self._synchronize_and_control_sampling_thread(True)
        self.sampler_adjustments_changed.emit(self.current_sampler_params['adjustments'].copy())

    def _synchronize_and_control_sampling_thread(self, should_be_enabled: bool):
        if not FEATURES_IMPORTS_OK: return
        if should_be_enabled:
            if not self.is_sampling_thread_active:
                self.is_sampling_thread_active = True
                self.sampling_activity_changed.emit(True)
            self.sampling_thread.start_sampling(
                monitor_capture_id=self.current_sampler_params['monitor_id'],
                region_rect_percentage=self.current_sampler_params['region_rect_percentage'],
                frequency_ms=self.current_sampler_params['frequency_ms'],
                sampling_mode=self.current_sampler_params['sampling_mode'], # Pass the mode
                adjustments=self.current_sampler_params['adjustments']
            )
            self.sampler_status_update.emit("Screen sampling active.", 0)
        else:
            if self.is_sampling_thread_active:
                if self.is_actively_recording: self._stop_recording_logic(inform_user=False)
                if self.sampling_thread.isRunning(): self.sampling_thread.stop_sampling()
                self.is_sampling_thread_active = False
                self.sampling_activity_changed.emit(False)
                self.sampler_status_update.emit("Screen sampling stopped.", 2000)
        # Update UI (unchanged)
        if GUI_IMPORTS_OK and hasattr(self.ui_manager, 'update_record_button_ui') and hasattr(self.ui_manager, 'set_recording_status_text'):
            if self.is_sampling_thread_active and not self.is_actively_recording:
                self.ui_manager.set_recording_status_text("Idle. Ready to record.")
                self.ui_manager.update_record_button_ui(is_recording=False, can_record=True)
            elif not self.is_sampling_thread_active:
                self.ui_manager.set_recording_status_text("Sampler OFF")
                self.ui_manager.update_record_button_ui(is_recording=False, can_record=False)

    def force_disable_sampling_ui(self):
        if not GUI_IMPORTS_OK:
            return
        if hasattr(self.ui_manager, 'enable_sampling_button') and self.ui_manager.enable_sampling_button and \
                hasattr(self.ui_manager.enable_sampling_button, 'isChecked') and \
                hasattr(self.ui_manager.enable_sampling_button, 'setChecked'):
            if self.ui_manager.enable_sampling_button.isChecked():
                self.ui_manager.enable_sampling_button.setChecked(False)
        else:
            self._synchronize_and_control_sampling_thread(False)

    def stop_sampling_thread(self, emit_status: bool = True):
        """
        Stops the screen sampling thread and updates the UI. This method is now safe
        to be called multiple times and handles the thread already being stopped.
        Args:
            emit_status (bool): If True, a status update message will be shown when the
                                thread finishes. If False, it stops silently.
        """
        # Store the desired status outcome for when the thread actually finishes.
        self._emit_status_on_next_stop = emit_status
        if self.sampling_thread and self.sampling_thread.isRunning():
            # THE FIX: Call the correct method name 'stop_sampling()'
            self.sampling_thread.stop_sampling()
        else:
            # If the thread isn't running, we still need to ensure the manager's
            # state is correct and respects the emit_status flag.
            self._on_thread_finished()

    def _handle_thread_pad_colors_sampled(self, colors_list: list):
        if self.is_actively_recording:
            if self.current_recording_frame_count < self.MAX_RECORDING_FRAMES:
                if colors_list and len(colors_list) == ScreenSamplerCore.NUM_GRID_ROWS * ScreenSamplerCore.NUM_GRID_COLS:
                    hex_frame = [QColor(r, g, b).name()
                                for r, g, b in colors_list]
                    self.recorded_sampler_frames.append(hex_frame)
                    self.current_recording_frame_count += 1
                    if GUI_IMPORTS_OK and hasattr(self.ui_manager, 'set_recording_status_text'):
                        self.ui_manager.set_recording_status_text(
                            f"REC 🔴 {self.current_recording_frame_count}/{self.MAX_RECORDING_FRAMES}")
                if self.current_recording_frame_count >= self.MAX_RECORDING_FRAMES:
                    self.sampler_status_update.emit(
                        f"Max recording frames ({self.MAX_RECORDING_FRAMES}) reached.", 3000)
                    self._stop_recording_logic()
        if self.is_sampling_thread_active:
            self.sampled_colors_for_display.emit(colors_list)

    def _handle_thread_processed_image_ready(self, pil_image: Image.Image):
        self._last_processed_pil_image = pil_image
        # --- FIX: Use the correct attribute name for the visual dialog ---
        if self.visual_sampler_dialog and self.visual_sampler_dialog.isVisible():
            self.visual_sampler_dialog.update_preview_image(pil_image)
        # This signal is for other potential listeners, like a main window preview.
        self.processed_image_for_preview.emit(pil_image)

    def _handle_thread_error_occurred(self, error_message: str):
        self.sampler_status_update.emit(
            f"Sampler Thread Error: {error_message}", 7000)
        if "FATAL: mss library init failed" in error_message or "No monitors found" in error_message:
            if GUI_IMPORTS_OK:
                if hasattr(self.ui_manager, 'force_disable_sampling_ui'):
                    self.ui_manager.force_disable_sampling_ui()
                if hasattr(self.ui_manager, 'setEnabled'):  # QGroupBox method
                    self.ui_manager.setEnabled(False)
            if self.capture_preview_dialog:
                self.capture_preview_dialog.close()

    def _on_ui_record_button_clicked(self):
        if not GUI_IMPORTS_OK:
            return
        if self.is_actively_recording:
            self._stop_recording_logic()
        else:
            if not self.is_sampling_thread_active:
                reply = QMessageBox.question(self.ui_manager if isinstance(self.ui_manager, QObject) else None,
                                             "Sampler Inactive",
                                             "Screen sampler is not active.\nStart sampling to begin recording?",
                                             QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                             QMessageBox.StandardButton.No)
                if reply == QMessageBox.StandardButton.Yes:
                    if hasattr(self.ui_manager, 'enable_sampling_button') and self.ui_manager.enable_sampling_button and \
                            hasattr(self.ui_manager.enable_sampling_button, 'setChecked'):
                        self.ui_manager.enable_sampling_button.setChecked(True)
                    else:
                        self._handle_ui_sampling_control_changed(True, {
                            'monitor_capture_id': self.current_sampler_params['monitor_id'],
                            'frequency_ms': self.current_sampler_params['frequency_ms']
                        })
                    QTimer.singleShot(
                        250, self._start_recording_logic_if_sampler_active)
                else:
                    self.sampler_status_update.emit(
                        "Recording cancelled; sampler not started.", 2000)
                return
            self._start_recording_logic()

    def _start_recording_logic_if_sampler_active(self):
        if self.is_sampling_thread_active:
            self._start_recording_logic()
        else:
            self.sampler_status_update.emit(
                "Failed to start sampler for recording.", 3000)
            if GUI_IMPORTS_OK and hasattr(self.ui_manager, 'update_record_button_ui'):
                self.ui_manager.update_record_button_ui(
                    is_recording=False, can_record=False)

    def _start_recording_logic(self):
        if not self.is_sampling_thread_active:
            self.sampler_status_update.emit(
                "Cannot record: Sampler not active.", 3000)
            if GUI_IMPORTS_OK and hasattr(self.ui_manager, 'update_record_button_ui'):
                self.ui_manager.update_record_button_ui(
                    is_recording=False, can_record=False)
            return
        self.is_actively_recording = True
        self.recorded_sampler_frames.clear()
        self.current_recording_frame_count = 0
        self.captured_sampler_frequency_ms = self.current_sampler_params['frequency_ms']
        self.sampler_status_update.emit("Sampler recording started...", 0)
        if GUI_IMPORTS_OK and hasattr(self.ui_manager, 'update_record_button_ui') and hasattr(self.ui_manager, 'set_recording_status_text'):
            self.ui_manager.update_record_button_ui(
                is_recording=True, can_record=False)
            self.ui_manager.set_recording_status_text(
                f"REC 🔴 0/{self.MAX_RECORDING_FRAMES}")

    def _stop_recording_logic(self, inform_user=True):
        was_recording = self.is_actively_recording
        self.is_actively_recording = False
        final_frame_count = self.current_recording_frame_count
        if GUI_IMPORTS_OK and hasattr(self.ui_manager, 'update_record_button_ui') and hasattr(self.ui_manager, 'set_recording_status_text'):
            self.ui_manager.update_record_button_ui(
                is_recording=False, can_record=self.is_sampling_thread_active)
            if not was_recording and final_frame_count == 0:
                if self.is_sampling_thread_active:
                    self.ui_manager.set_recording_status_text("Idle.")
                return
            if inform_user:
                self.sampler_status_update.emit(
                    f"Recording stopped. {final_frame_count} frames captured.", 5000)
            if self.is_sampling_thread_active:
                self.ui_manager.set_recording_status_text(
                    f"Idle. ({final_frame_count} frames recorded)")
            else:
                self.ui_manager.set_recording_status_text(
                    f"Sampler OFF ({final_frame_count} frames recorded)")
        if self.recorded_sampler_frames:
            self._process_and_save_recorded_frames()
        elif inform_user:
            self.sampler_status_update.emit("No frames were recorded.", 2000)

    def _process_and_save_recorded_frames(self):
        if not self.recorded_sampler_frames or not GUI_IMPORTS_OK:
            return
        num_frames = len(self.recorded_sampler_frames)
        timestamp_str = time.strftime("%Y%m%d-%H%M")
        default_name = f"Sampled {timestamp_str} ({num_frames}f)"
        user_name, ok = QInputDialog.getText(self.ui_manager if isinstance(self.ui_manager, QObject) else None,
                                            "Name Recorded Sequence",
                                            "Enter name:", text=default_name)
        if not (ok and user_name and user_name.strip()):
            if QMessageBox.question(self.ui_manager if isinstance(self.ui_manager, QObject) else None,
                                    "Discard?", "Discard recorded frames?",
                                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                    QMessageBox.StandardButton.No) == QMessageBox.StandardButton.Yes:
                self.recorded_sampler_frames.clear()
                self.current_recording_frame_count = 0
                if hasattr(self.ui_manager, 'set_recording_status_text'):
                    self.ui_manager.set_recording_status_text(
                        "Recording discarded.")
                self.sampler_status_update.emit(
                    "Recorded frames discarded.", 2000)
            else:
                if hasattr(self.ui_manager, 'set_recording_status_text') and hasattr(self.ui_manager, 'update_record_button_ui'):
                    self.ui_manager.set_recording_status_text(
                        f"Ready to save {num_frames} frames. Click Record again to re-prompt.")
                    self.is_actively_recording = True
                    self.ui_manager.update_record_button_ui(
                        is_recording=True, can_record=False)
            return
        final_name_base = user_name.strip()
        if not self.animator_manager_ref:
            self.sampler_status_update.emit(
                "Error: Animator reference missing for saving.", 5000)
            return
        try:
            sanitized_base = self.animator_manager_ref._sanitize_filename(
                final_name_base)
            sampler_dir = self.animator_manager_ref._get_sequence_dir_path(
                "sampler")
        except AttributeError:
            print(
                "WARNING: AnimatorManagerWidget utility methods not found. Using basic fallback for saving.")
            sanitized_base = "".join(c if c.isalnum() or c in (
                ' ', '_', '-') else '_' for c in final_name_base).rstrip()
            sampler_dir = os.path.join(
                self.presets_base_path, "sequences", "sampler_recordings")
        os.makedirs(sampler_dir, exist_ok=True)
        actual_filepath = os.path.join(sampler_dir, f"{sanitized_base}.json")
        actual_model_name = final_name_base
        counter = 0
        while os.path.exists(actual_filepath):
            counter += 1
            actual_model_name = f"{final_name_base}_{counter}"
            new_sanitized_base_name_part = "".join(c if c.isalnum() or c in (
                ' ', '_', '-') else '_' for c in actual_model_name).rstrip()
            actual_filepath = os.path.join(
                sampler_dir, f"{new_sanitized_base_name_part}.json")
            if counter > 100:
                self.sampler_status_update.emit(
                    "Save Error: Too many filename collisions.", 5000)
                return
        temp_model = SequenceModel(name=actual_model_name)
        for frame_hex_data in self.recorded_sampler_frames:
            temp_model.frames.append(AnimationFrame(colors=frame_hex_data))
        temp_model.frame_delay_ms = self.captured_sampler_frequency_ms
        temp_model.loop = True
        if temp_model.save_to_file(actual_filepath):
            self.sampler_status_update.emit(
                f"Sequence '{actual_model_name}' saved.", 3000)
            self.new_sequence_from_recording_ready.emit(actual_filepath)
            if hasattr(self.ui_manager, 'set_recording_status_text'):
                self.ui_manager.set_recording_status_text(
                    f"Saved: {actual_model_name}")
        else:
            self.sampler_status_update.emit(
                f"Error saving to '{actual_filepath}'.", 5000)
            if hasattr(self.ui_manager, 'set_recording_status_text'):
                self.ui_manager.set_recording_status_text(
                    "Error saving recording.")
        self.recorded_sampler_frames.clear()
        self.current_recording_frame_count = 0

    def _on_ui_set_max_frames_button_clicked(self):
        if not GUI_IMPORTS_OK:
            return
        new_max, ok = SetMaxFramesDialog.get_max_frames(
            parent_widget=self.ui_manager if isinstance(
                self.ui_manager, QObject) else None,
            current_value=self.MAX_RECORDING_FRAMES
        )
        if ok and new_max is not None:
            self.MAX_RECORDING_FRAMES = new_max
            self.sampler_status_update.emit(
                f"Max recording frames set to {self.MAX_RECORDING_FRAMES}.", 3000)
            if self.is_actively_recording and hasattr(self.ui_manager, 'set_recording_status_text'):
                self.ui_manager.set_recording_status_text(
                    f"REC 🔴 {self.current_recording_frame_count}/{self.MAX_RECORDING_FRAMES}")

    def _load_sampler_preferences(self):
        self.sampler_monitor_prefs = {}
        if os.path.exists(self.sampler_prefs_file_path):
            try:
                with open(self.sampler_prefs_file_path, 'r') as f:
                    loaded_prefs = json.load(f)
                self.sampler_monitor_prefs = loaded_prefs.get("monitor_configurations", {})
                self.current_sampler_params['monitor_id'] = loaded_prefs.get("last_active_monitor_id", 1)
                self.current_sampler_params['sampling_mode'] = loaded_prefs.get("last_sampling_mode", 'grid') # Load mode
                self.sampler_status_update.emit("Sampler preferences loaded.", 1500)
            except Exception as e:
                self.sampler_status_update.emit(f"Error loading sampler prefs: {e}", 3000)
                self.sampler_monitor_prefs = {}
        else:
            self.sampler_status_update.emit("Sampler prefs file not found. Using defaults.", 1500)
        self._apply_prefs_for_current_monitor()

    def _save_sampler_preferences_to_file(self):
        try:
            data_to_save = {
                "monitor_configurations": self.sampler_monitor_prefs,
                "last_active_monitor_id": self.current_sampler_params['monitor_id'],
                "last_sampling_mode": self.current_sampler_params.get('sampling_mode', 'grid') # Save mode
            }
            os.makedirs(os.path.dirname(self.sampler_prefs_file_path), exist_ok=True)
            with open(self.sampler_prefs_file_path, 'w') as f:
                json.dump(data_to_save, f, indent=4)
        except Exception as e:
            self.sampler_status_update.emit(f"Error saving sampler prefs: {e}", 3000)

    def _fps_to_ms(self, fps: int) -> int:
        if fps <= 0:
            return 1000
        return int(1000.0 / fps)

    def on_application_exit(self):
        if self.is_sampling_thread_active:
            self.stop_sampling_thread()
        self._save_sampler_preferences_to_file()
        print("ScreenSamplerManager: Preferences saved on exit.")

    def _update_preview_dialog_sliders_if_visible(self, adjustments: dict):
        """
        Updates the sliders in whichever configuration dialog is currently visible.
        This is called when adjustments are changed externally (e.g., by MainWindow knobs).
        """
        # --- FIX: Check for BOTH dialogs and update the one that is visible ---
        if self.visual_sampler_dialog and self.visual_sampler_dialog.isVisible():
            if hasattr(self.visual_sampler_dialog, 'update_sliders_from_external_adjustments'):
                self.visual_sampler_dialog.update_sliders_from_external_adjustments(adjustments)
            else:
                print("SSM WARNING: VisualSamplerConfiguration missing 'update_sliders_from_external_adjustments'")
        if self.ambient_settings_dialog and self.ambient_settings_dialog.isVisible():
            if hasattr(self.ambient_settings_dialog, 'update_sliders_from_external_adjustments'):
                self.ambient_settings_dialog.update_sliders_from_external_adjustments(adjustments)
            else:
                print("SSM WARNING: AmbientModeSettingsDialog missing 'update_sliders_from_external_adjustments'")

    def _generate_monitor_key(self, monitor_id: int) -> str | None:
        """
        Generates a stable, unique key for a monitor based on its geometry,
        using the existing monitor cache.
        """
        if not self.screen_sampler_monitor_list_cache:
            # If cache is empty, we cannot generate a key.
            # The calling function is now responsible for populating the cache first.
            return None
        monitor_info = next(
            (m for m in self.screen_sampler_monitor_list_cache if m['id'] == monitor_id), None)
        if monitor_info:
            return f"{monitor_info['width']}x{monitor_info['height']}_{monitor_info['left']}_{monitor_info['top']}"
        return None
        """Generates a stable, unique key for a monitor based on its geometry."""
        if not self.screen_sampler_monitor_list_cache:
            # This should ideally be populated before this is called, but as a fallback:
            self.populate_monitor_list_for_ui(force_fetch=False)
        monitor_info = next(
            (m for m in self.screen_sampler_monitor_list_cache if m['id'] == monitor_id), None)
        if monitor_info:
            # Key format: "widthxheight_left_top" e.g., "1920x1080_0_0"
            return f"{monitor_info['width']}x{monitor_info['height']}_{monitor_info['left']}_{monitor_info['top']}"
        return None