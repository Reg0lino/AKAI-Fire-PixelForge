# AKAI_Fire_RGB_Controller/gui/screen_sampler_manager.py
import os
import sys
import json
import mss
import time
from PyQt6.QtCore import QObject, pyqtSignal, QTimer
from PyQt6.QtWidgets import QMessageBox, QInputDialog # Keep these for dialogs shown by SSM
from PyQt6.QtGui import QColor
from PIL import Image
# --- GUI Component Imports ---
try:
    from gui.screen_sampler_ui_manager import ScreenSamplerUIManager
    from gui.capture_preview_dialog import CapturePreviewDialog
    from gui.set_max_frames_dialog import SetMaxFramesDialog
    from animator.model import SequenceModel, AnimationFrame
    GUI_IMPORTS_OK = True
except ImportError as e:
    print(f"CRITICAL ERROR (ScreenSamplerManager): Could not import essential GUI/Model components: {e}")
    GUI_IMPORTS_OK = False
    # Placeholder definitions (as you had them)
    class ScreenSamplerUIManager(QObject): # ... (minimal placeholder) ...
        sampling_control_changed = pyqtSignal(bool, dict); status_message_requested = pyqtSignal(str, int)
        request_monitor_list_population = pyqtSignal(); show_capture_preview_requested = pyqtSignal()
        record_button_clicked = pyqtSignal(); set_max_frames_button_clicked = pyqtSignal()
        enable_sampling_button = None; 
        def __init__(self, parent=None): super().__init__(parent)
        def set_overall_enabled_state(self, enabled): pass; 
        def populate_monitors_combo_external(self, monitors): pass
        def set_selected_monitor_ui(self, monitor_id): pass; 
        def set_sampling_frequency_ui(self, freq_ms): pass
        def update_record_button_ui(self, is_recording, can_record): pass; 
        def set_recording_status_text(self, text): pass
        def force_disable_sampling_ui(self): pass; 
        def isEnabled(self): return False; 
        def setEnabled(self, enabled): pass
    class CapturePreviewDialog(QObject): # ... (minimal placeholder) ...
        sampling_parameters_changed = pyqtSignal(dict); dialog_closed = pyqtSignal()
        def __init__(self, parent=None): super().__init__(parent); 
        def set_initial_monitor_data(self, monitors, current_id): pass
        def set_current_parameters_from_main(self, params): pass; 
        def update_preview_image(self, img): pass
        def isVisible(self): return False; 
        def show(self): pass; 
        def activateWindow(self): pass; 
        def raise_(self): pass
        def close(self): pass; 
        def deleteLater(self): pass
    class SetMaxFramesDialog(QObject): # ... (minimal placeholder) ...
        @staticmethod
        def get_max_frames(parent_widget, current_value): return current_value, False
    class SequenceModel: # ... (minimal placeholder) ...
        def __init__(self, name=""): self.name=name; self.frames=[]; self.frame_delay_ms=0; self.loop=False
        def save_to_file(self, path): return False
    class AnimationFrame: # ... (minimal placeholder) ...
        def __init__(self, colors=None): self.colors=colors or []

# --- Feature Component Imports ---
try:
    from features.screen_sampler_core import ScreenSamplerCore
    from features.screen_sampler_thread import ScreenSamplerThread
    FEATURES_IMPORTS_OK = True
except ImportError as e:
    print(f"Warning (ScreenSamplerManager): Could not import feature components: {e}. Using placeholders.")
    FEATURES_IMPORTS_OK = False
    class ScreenSamplerCore: # ... (minimal placeholder) ...
        DEFAULT_ADJUSTMENTS = {'brightness': 1.0, 'contrast': 1.0, 'saturation': 1.0, 'hue_shift': 0} # Ensure defaults exist
        NUM_GRID_ROWS = 4; NUM_GRID_COLS = 16
        @staticmethod
        def get_available_monitors(sct_instance): return []
    class ScreenSamplerThread(QObject): # ... (minimal placeholder) ...
        pad_colors_sampled = pyqtSignal(list); processed_image_ready = pyqtSignal(object); error_occurred = pyqtSignal(str)
        def __init__(self, parent=None): super().__init__(parent); 
        def start_sampling(self, **kwargs): pass
        def stop_sampling(self, **kwargs): pass; 
        def isRunning(self): return False

# --- Constants ---
SAMPLER_PREFS_FILENAME = "sampler_user_prefs.json"
APP_NAME_FOR_CONFIG = "AKAI_Fire_RGB_Controller"
APP_AUTHOR_FOR_CONFIG = "YourProjectAuthorName" # Replace if needed
DEFAULT_SAMPLING_FPS = 10

class ScreenSamplerManager(QObject):
    sampled_colors_for_display = pyqtSignal(list)
    processed_image_for_preview = pyqtSignal(Image.Image if GUI_IMPORTS_OK and 'Image' in globals() else object)
    sampler_status_update = pyqtSignal(str, int)
    sampling_activity_changed = pyqtSignal(bool)
    new_sequence_from_recording_ready = pyqtSignal(str)
    sampler_monitor_changed = pyqtSignal(str)
    
    # --- NEW SIGNAL for when adjustments are changed internally or by dialog ---
    sampler_adjustments_changed = pyqtSignal(dict) # Emits the full 'adjustments' dictionary

    def __init__(self,
                 presets_base_path: str,
                 animator_manager_ref,
                 parent: QObject | None = None):
        super().__init__(parent)
        # ... (rest of __init__ as before)
        self.presets_base_path = presets_base_path
        self.animator_manager_ref = animator_manager_ref
        self.is_sampling_thread_active = False
        self.is_actively_recording = False
        self.screen_sampler_monitor_list_cache = []
        self.current_sampler_params = {
            'monitor_id': 1,
            'region_rect_percentage': {'x': 0.4, 'y': 0.4, 'width': 0.2, 'height': 0.2},
            'adjustments': ScreenSamplerCore.DEFAULT_ADJUSTMENTS.copy(),
            'frequency_ms': self._fps_to_ms(DEFAULT_SAMPLING_FPS)
        }
        self.sampler_monitor_prefs = {}
        self.recorded_sampler_frames: list[list[str]] = []
        self.current_recording_frame_count: int = 0
        self.captured_sampler_frequency_ms: int = self.current_sampler_params['frequency_ms']
        self.MAX_RECORDING_FRAMES: int = 200
        self.ui_manager = ScreenSamplerUIManager(parent=None) # Assuming parent=None is okay if it's not added to a layout by SSM
        self.sampling_thread = ScreenSamplerThread(parent=self)
        self.capture_preview_dialog: CapturePreviewDialog | None = None
        self._last_processed_pil_image: Image.Image | None = None
        self._config_dir_path = self._get_user_config_dir_path()
        self.sampler_prefs_file_path = os.path.join(self._config_dir_path, SAMPLER_PREFS_FILENAME)
        self._load_sampler_preferences() # This calls _apply_prefs_for_current_monitor which might emit
        self._connect_signals()
        
        # Connect sampler_adjustments_changed to update dialog sliders if visible
        self.sampler_adjustments_changed.connect(self._update_preview_dialog_sliders_if_visible)
        
        if hasattr(self.ui_manager, 'set_sampling_frequency_ui'):
            self.ui_manager.set_sampling_frequency_ui(self.current_sampler_params['frequency_ms'])
        if hasattr(self.ui_manager, 'update_record_button_ui'):
            self.ui_manager.update_record_button_ui(is_recording=False, can_record=False)
        if hasattr(self.ui_manager, 'set_recording_status_text'):
            self.ui_manager.set_recording_status_text("Sampler Off / Device Disconnected")

    # ... (_get_user_config_dir_path, get_ui_widget, _connect_signals as before) ...
    def _get_user_config_dir_path(self) -> str: # Unchanged
        config_dir_to_use = ""
        try:
            is_packaged = getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS')
            if is_packaged: from appdirs import user_config_dir; config_dir_to_use = user_config_dir(APP_NAME_FOR_CONFIG, APP_AUTHOR_FOR_CONFIG)
            else: current_file_dir = os.path.dirname(os.path.abspath(__file__)); project_root = os.path.dirname(current_file_dir); config_dir_to_use = os.path.join(project_root, "user_settings")
            os.makedirs(config_dir_to_use, exist_ok=True); return config_dir_to_use
        except Exception: fallback_dir=os.path.join(os.getcwd(),"user_settings_sampler_fallback"); os.makedirs(fallback_dir,exist_ok=True); return fallback_dir
    def get_ui_widget(self) -> ScreenSamplerUIManager: return self.ui_manager # Unchanged
    def _connect_signals(self): # Unchanged
        if not GUI_IMPORTS_OK: return
        self.ui_manager.sampling_control_changed.connect(self._handle_ui_sampling_control_changed)
        self.ui_manager.request_monitor_list_population.connect(self.populate_monitor_list_for_ui)
        self.ui_manager.show_capture_preview_requested.connect(self._show_capture_preview_dialog)
        self.ui_manager.record_button_clicked.connect(self._on_ui_record_button_clicked)
        self.ui_manager.set_max_frames_button_clicked.connect(self._on_ui_set_max_frames_button_clicked)
        self.ui_manager.status_message_requested.connect(self.sampler_status_update)
        self.sampling_thread.pad_colors_sampled.connect(self._handle_thread_pad_colors_sampled)
        self.sampling_thread.processed_image_ready.connect(self._handle_thread_processed_image_ready)
        self.sampling_thread.error_occurred.connect(self._handle_thread_error_occurred)

    # --- NEW METHOD to update individual sampler adjustments ---
    def update_sampler_adjustment(self, adjustment_key: str, new_value: float):
        """
        Updates a specific sampler adjustment (brightness, contrast, saturation, hue_shift).
        Called by MainWindow when corresponding GUI knob is changed.
        """
        if adjustment_key not in self.current_sampler_params['adjustments']:
            print(f"SSM WARNING: Invalid adjustment key '{adjustment_key}' in update_sampler_adjustment.")
            return

        # Potentially clamp or validate new_value based on adjustment_key if necessary
        # For now, assume MainWindow sends valid, mapped values.
        self.current_sampler_params['adjustments'][adjustment_key] = new_value
        
        print(f"SSM INFO: Sampler adjustment '{adjustment_key}' updated to {new_value}")

        self._save_prefs_for_current_monitor()  # Save the change to persistent storage for this monitor
        
        # If sampling is currently active, restart the thread with the new parameters
        if self.is_sampling_thread_active:
            self._synchronize_and_control_sampling_thread(True) 
            
        # Emit signal so MainWindow can update its knobs if this change came from somewhere else (e.g., dialog)
        # or to confirm the change if it came from a knob.
        self.sampler_adjustments_changed.emit(self.current_sampler_params['adjustments'].copy())

    # --- Modify _handle_dialog_full_params_changed ---
    def _handle_dialog_full_params_changed(self, full_dialog_params: dict):
        # ... (existing logic to update self.current_sampler_params from full_dialog_params) ...
        new_monitor_id = full_dialog_params.get('monitor_id', self.current_sampler_params['monitor_id'])
        self.current_sampler_params['monitor_id'] = new_monitor_id
        self.current_sampler_params['region_rect_percentage'] = full_dialog_params.get(
            'region_rect_percentage', self.current_sampler_params['region_rect_percentage']
        )
        self.current_sampler_params['adjustments'] = full_dialog_params.get(
            'adjustments', self.current_sampler_params['adjustments']
        ).copy() # Ensure it's a copy


        self._save_prefs_for_current_monitor()

        if hasattr(self.ui_manager, 'set_selected_monitor_ui'): # Check if method exists
            self.ui_manager.set_selected_monitor_ui(self.current_sampler_params['monitor_id'])

        if self.is_sampling_thread_active:
            self._synchronize_and_control_sampling_thread(True)
        
        # --- ADD: Emit the new signal ---
        self.sampler_adjustments_changed.emit(self.current_sampler_params['adjustments'].copy())

    # --- Modify _apply_prefs_for_current_monitor ---
    def _apply_prefs_for_current_monitor(self):
        # ... (existing logic to load prefs for the current_sampler_params['monitor_id']) ...
        # print(f"DEBUG SSM._apply_prefs: Current monitor_id to apply for: {self.current_sampler_params['monitor_id']}") # Optional
        monitor_key = self._generate_monitor_key(self.current_sampler_params['monitor_id'])
        # print(f"DEBUG SSM._apply_prefs: Generated key: {monitor_key}") # Optional
        # print(f"DEBUG SSM._apply_prefs: Available keys in prefs: {list(self.sampler_monitor_prefs.keys())}") # Optional

        if monitor_key and monitor_key in self.sampler_monitor_prefs:
            saved_prefs = self.sampler_monitor_prefs[monitor_key]
            # print(f"DEBUG SSM._apply_prefs: Found prefs for key '{monitor_key}': {saved_prefs}") # Optional
            self.current_sampler_params['region_rect_percentage'] = saved_prefs.get('region_rect_percentage', self.current_sampler_params['region_rect_percentage'])
            self.current_sampler_params['adjustments'] = saved_prefs.get('adjustments', ScreenSamplerCore.DEFAULT_ADJUSTMENTS.copy()).copy() # Ensure copy
            # print(f"DEBUG SSM._apply_prefs: AFTER apply, current_sampler_params[region]: {self.current_sampler_params['region_rect_percentage']}") # Optional
        else:
            # print(f"DEBUG SSM._apply_prefs: No prefs found for key '{monitor_key}'. Using defaults.") # Optional
            self.current_sampler_params['region_rect_percentage'] = {'x': 0.4, 'y': 0.4, 'width': 0.2, 'height': 0.2}
            self.current_sampler_params['adjustments'] = ScreenSamplerCore.DEFAULT_ADJUSTMENTS.copy()
            # print(f"DEBUG SSM._apply_prefs: AFTER default, current_sampler_params[region]: {self.current_sampler_params['region_rect_percentage']}") # Optional

        # --- ADD: Emit signal after applying preferences ---
        # This ensures GUI knobs update if preferences were loaded/applied (e.g., on startup or monitor change)
        self.sampler_adjustments_changed.emit(self.current_sampler_params['adjustments'].copy())

    def set_overall_enabled_state(self, enabled_from_main_window: bool, device_connected: bool):
        if not GUI_IMPORTS_OK: return

        sampler_core_can_be_active = enabled_from_main_window and device_connected
        
        if hasattr(self.ui_manager, 'set_overall_enabled_state'):
            self.ui_manager.set_overall_enabled_state(sampler_core_can_be_active)
        else:
            print(f"WARNING (SSM.set_overall_enabled_state): self.ui_manager missing 'set_overall_enabled_state'")


        if sampler_core_can_be_active:
            if not self.screen_sampler_monitor_list_cache:
                self.populate_monitor_list_for_ui()
        else:
            if self.is_sampling_thread_active:
                self._synchronize_and_control_sampling_thread(False)
        
        if not hasattr(self.ui_manager, 'set_recording_status_text') or \
           not hasattr(self.ui_manager, 'update_record_button_ui'):
            print(f"WARNING (SSM.set_overall_enabled_state): self.ui_manager missing text/button update methods")
            return

        if not device_connected:
            self.ui_manager.set_recording_status_text("Device Disconnected")
            self.ui_manager.update_record_button_ui(is_recording=False, can_record=False)
        elif not sampler_core_can_be_active:
             self.ui_manager.set_recording_status_text("Sampler UI Disabled")
             self.ui_manager.update_record_button_ui(is_recording=False, can_record=False)
        elif not self.is_sampling_thread_active:
            self.ui_manager.set_recording_status_text("Sampler OFF")
            self.ui_manager.update_record_button_ui(is_recording=False, can_record=False)
        elif self.is_actively_recording:
            self.ui_manager.set_recording_status_text(f"REC 🔴 {self.current_recording_frame_count}/{self.MAX_RECORDING_FRAMES}")
            self.ui_manager.update_record_button_ui(is_recording=True, can_record=False)
        else:
            self.ui_manager.set_recording_status_text("Idle. Ready to record.")
            self.ui_manager.update_record_button_ui(is_recording=False, can_record=True)
            
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
            self.ui_manager.enable_sampling_button.setEnabled(actual_toggle_button_state)

            # If the toggle button is being disabled WHILE it's checked (i.e., sampling is active),
            # then force sampling off.
            if not actual_toggle_button_state and self.ui_manager.enable_sampling_button.isChecked():
                self.ui_manager.enable_sampling_button.setChecked(False) # This will trigger its toggle signal
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
                can_record=(overall_sampler_ui_enabled and \
                            can_toggle_sampling_button_enabled and \
                            self.is_sampling_thread_active and \
                            not self.is_actively_recording) or \
                           (overall_sampler_ui_enabled and \
                            self.is_actively_recording) # Can always stop if recording
            )
        
        # Update configure button state too (might be part of ui_manager.set_overall_enabled_state)
        if hasattr(self.ui_manager, 'configure_preview_button') and self.ui_manager.configure_preview_button:
             self.ui_manager.configure_preview_button.setEnabled(overall_sampler_ui_enabled)

    def is_sampling_active(self) -> bool:
        return self.is_sampling_thread_active

    def is_currently_recording(self) -> bool:
        return self.is_actively_recording

    def _handle_ui_sampling_control_changed(self, enable_toggle: bool, basic_ui_params: dict):
        newly_selected_monitor_id = basic_ui_params.get('monitor_capture_id', self.current_sampler_params['monitor_id'])

        if newly_selected_monitor_id != self.current_sampler_params.get('monitor_id'):
            self.current_sampler_params['monitor_id'] = newly_selected_monitor_id
            self._apply_prefs_for_current_monitor()

        self.current_sampler_params['frequency_ms'] = basic_ui_params.get('frequency_ms', self.current_sampler_params['frequency_ms'])

        if self.capture_preview_dialog and self.capture_preview_dialog.isVisible():
            self.capture_preview_dialog.set_current_parameters_from_main(self.current_sampler_params)

        self._synchronize_and_control_sampling_thread(enable_toggle)


#  and reflect the success of critical imports, as discussed previously)

    def populate_monitor_list_for_ui(self, force_fetch: bool = False):
        # print(f"--- SSM populate_monitor_list_for_ui ENTER --- (force_fetch={force_fetch}, cache_exists={bool(self.screen_sampler_monitor_list_cache)})")

        if not GUI_IMPORTS_OK or not FEATURES_IMPORTS_OK:
            # print("DEBUG SSM.populate_monitor_list_for_ui: Skipping due to missing critical imports.")
            return

        # Determine if a fetch is truly needed
        needs_fetch = force_fetch or not self.screen_sampler_monitor_list_cache
        
        if needs_fetch:
            # print(f"DEBUG SSM.populate_monitor_list_for_ui: Needs fetch. force_fetch={force_fetch}, cache_empty={not self.screen_sampler_monitor_list_cache}")
            try:
                # print("DEBUG SSM.populate_monitor_list_for_ui: Attempting to fetch monitors with mss...")
                with mss.mss() as sct:
                    # This line updates the cache:
                    self.screen_sampler_monitor_list_cache = ScreenSamplerCore.get_available_monitors(sct)
                # print(f"DEBUG SSM.populate_monitor_list_for_ui: Monitors fetched: {self.screen_sampler_monitor_list_cache}")
                if not self.screen_sampler_monitor_list_cache:
                    self.sampler_status_update.emit("No monitors detected for screen sampler.", 3000)
            except Exception as e:
                # print(f"DEBUG SSM.populate_monitor_list_for_ui: Exception during mss monitor fetch: {e}")
                self.sampler_status_update.emit(f"Error getting monitor list: {str(e)[:100]}", 5000)
                self.screen_sampler_monitor_list_cache = [] # Ensure cache is empty on error
        # else:
            # print(f"DEBUG SSM.populate_monitor_list_for_ui: No fetch needed. Using cached monitors: {self.screen_sampler_monitor_list_cache}")

        # Update the UI manager's combo box with the (potentially new) cache
        if hasattr(self.ui_manager, 'populate_monitors_combo_external'):
            # print(f"DEBUG SSM.populate_monitor_list_for_ui: Calling ui_manager.populate_monitors_combo_external with cache.")
            self.ui_manager.populate_monitors_combo_external(self.screen_sampler_monitor_list_cache)
        else:
            print("CRITICAL WARNING (SSM.populate_monitor_list_for_ui): self.ui_manager is missing 'populate_monitors_combo_external' method. UI cannot be updated.")
            # If ui_manager is a placeholder due to import errors, this might happen.
            # Or if the real ScreenSamplerUIManager is missing the method.
            return # Cannot proceed without this UI update method

        # Logic to select a default monitor in the UI and apply its preferences,
        # especially if the current selection is invalid or after a fresh fetch.
        if self.screen_sampler_monitor_list_cache: # Only proceed if we have monitors
            current_monitor_ids_in_cache = [m['id'] for m in self.screen_sampler_monitor_list_cache]
            
            monitor_id_to_apply_prefs_for = self.current_sampler_params.get('monitor_id', 1) # Start with current or default
            apply_prefs_needed = False

            if monitor_id_to_apply_prefs_for not in current_monitor_ids_in_cache:
                # print(f"DEBUG SSM.populate_monitor_list_for_ui: Current monitor_id {monitor_id_to_apply_prefs_for} not in cache. Setting to default: {self.screen_sampler_monitor_list_cache[0]['id']}")
                monitor_id_to_apply_prefs_for = self.screen_sampler_monitor_list_cache[0]['id']
                self.current_sampler_params['monitor_id'] = monitor_id_to_apply_prefs_for
                apply_prefs_needed = True # ID changed, so prefs for this new ID need to be applied.
            
            # Update the UI to select the (potentially new) current monitor_id
            if hasattr(self.ui_manager, 'set_selected_monitor_ui'):
                # print(f"DEBUG SSM.populate_monitor_list_for_ui: Calling ui_manager.set_selected_monitor_ui with ID: {monitor_id_to_apply_prefs_for}")
                self.ui_manager.set_selected_monitor_ui(monitor_id_to_apply_prefs_for)
            else:
                print("WARNING (SSM.populate_monitor_list_for_ui): self.ui_manager missing 'set_selected_monitor_ui'")

            # If the monitor ID changed to a default, or if this was a forced refresh that might change what's "current"
            # we should re-apply preferences for the now-current monitor_id.
            # Also, apply if it's the very first time (needs_fetch was true due to empty cache initially).
            if apply_prefs_needed or (needs_fetch and not force_fetch and not self.screen_sampler_monitor_list_cache): # Check if cache was empty before this successful fetch
                # print(f"DEBUG SSM.populate_monitor_list_for_ui: Applying preferences for monitor ID: {monitor_id_to_apply_prefs_for}. Needs fetch was: {needs_fetch}, apply_prefs_needed was: {apply_prefs_needed}")
                self._apply_prefs_for_current_monitor() # Apply prefs for this monitor_id
        else: # No monitors in cache (either never found or error during fetch)
            print("DEBUG SSM.populate_monitor_list_for_ui: No monitors in cache to select or apply prefs for.")
            # self.current_sampler_params['monitor_id'] could be left as is, or reset to a default like 1.
            # The UI will show "No monitors found".

        # Update the capture preview dialog if it's open and visible
        if self.capture_preview_dialog and hasattr(self.capture_preview_dialog, 'isVisible') and self.capture_preview_dialog.isVisible():
            if hasattr(self.capture_preview_dialog, 'set_initial_monitor_data'):
                # print(f"DEBUG SSM.populate_monitor_list_for_ui: Updating visible capture preview dialog with monitor data.")
                self.capture_preview_dialog.set_initial_monitor_data(
                    self.screen_sampler_monitor_list_cache,
                    self.current_sampler_params.get('monitor_id', 1)
                )
            else:
                print("WARNING (SSM.populate_monitor_list_for_ui): capture_preview_dialog missing 'set_initial_monitor_data'")
        
        print(f"--- SSM populate_monitor_list_for_ui EXIT ---")

    def toggle_sampling_state(self):
        """Toggles the screen sampler ON or OFF."""
        if not GUI_IMPORTS_OK or not hasattr(self.ui_manager, 'enable_sampling_button'):
            print("SSM ERROR: UI Manager or toggle button not available for toggle_sampling_state.")
            self.sampler_status_update.emit("Error: Sampler UI not ready.", 3000)
            return

        current_state_is_on = self.ui_manager.enable_sampling_button.isChecked()
        new_state_to_set = not current_state_is_on
        
        # print(f"SSM TRACE: toggle_sampling_state called. Current visual state is ON: {current_state_is_on}. Setting to: {new_state_to_set}") # Optional
        
        # Update the UI button state, which in turn triggers _handle_ui_sampling_control_changed
        # This ensures the logic flow is consistent with a GUI click.
        if hasattr(self.ui_manager.enable_sampling_button, 'setChecked'):
            self.ui_manager.enable_sampling_button.setChecked(new_state_to_set)
        else: # Fallback if button is somehow not checkable (should not happen)
            self._handle_ui_sampling_control_changed(new_state_to_set, {
                'monitor_capture_id': self.current_sampler_params.get('monitor_id', 1),
                'frequency_ms': self.current_sampler_params.get('frequency_ms', self._fps_to_ms(DEFAULT_SAMPLING_FPS))
            })
        
        # Status update is handled by _synchronize_and_control_sampling_thread via _handle_ui_sampling_control_changed

    def cycle_target_monitor(self):
        """Cycles to the next available monitor for sampling."""
        if not self.is_sampling_thread_active:
            self.sampler_status_update.emit("Enable sampler to cycle monitors.", 2000)
            return

        if not self.screen_sampler_monitor_list_cache:
            self.populate_monitor_list_for_ui(force_fetch=True) # Try to get monitors if cache is empty
            if not self.screen_sampler_monitor_list_cache:
                self.sampler_status_update.emit("No monitors available to cycle.", 3000)
                return
        
        if len(self.screen_sampler_monitor_list_cache) <= 1:
            self.sampler_status_update.emit("Only one monitor available.", 2000)
            # Optionally, still emit current monitor name if needed for OLED refresh
            current_monitor_id = self.current_sampler_params.get('monitor_id', 1)
            current_monitor_info = next((m for m in self.screen_sampler_monitor_list_cache if m['id'] == current_monitor_id), None)
            if current_monitor_info:
                self.sampler_monitor_changed.emit(current_monitor_info.get('name_for_ui', f"Monitor {current_monitor_id}"))
            return

        current_monitor_id = self.current_sampler_params.get('monitor_id', 1)
        current_idx = -1
        for i, monitor in enumerate(self.screen_sampler_monitor_list_cache):
            if monitor['id'] == current_monitor_id:
                current_idx = i
                break
        
        next_idx = (current_idx + 1) % len(self.screen_sampler_monitor_list_cache)
        new_monitor_info = self.screen_sampler_monitor_list_cache[next_idx]
        new_monitor_id = new_monitor_info['id']

        self.current_sampler_params['monitor_id'] = new_monitor_id
        
        # Update the UI ComboBox to reflect the new selection
        if GUI_IMPORTS_OK and hasattr(self.ui_manager, 'set_selected_monitor_ui'):
            self.ui_manager.set_selected_monitor_ui(new_monitor_id)
        
        # Apply preferences for the newly selected monitor
        self._apply_prefs_for_current_monitor() 
        
        # If sampling is active, restart it with the new monitor settings
        if self.is_sampling_thread_active:
            self._synchronize_and_control_sampling_thread(True) # True to (re)start sampling

        new_monitor_name = new_monitor_info.get('name_for_ui', f"Monitor {new_monitor_id}")
        self.sampler_status_update.emit(f"Sampler switched to: {new_monitor_name}", 2500)
        self.sampler_monitor_changed.emit(new_monitor_name) # Emit signal for OLED update
        # print(f"SSM TRACE: Cycled monitor to ID: {new_monitor_id}, Name: {new_monitor_name}") # Optional
        
    def _show_capture_preview_dialog(self):
        if not GUI_IMPORTS_OK: return

        if not self.screen_sampler_monitor_list_cache:
            self.populate_monitor_list_for_ui(force_fetch=True)
            if not self.screen_sampler_monitor_list_cache:
                if hasattr(self.ui_manager, 'isEnabled') and self.ui_manager.isEnabled():
                    QMessageBox.warning(self.ui_manager, "Monitor Info", "No monitor data for sampler config.")
                else:
                    self.sampler_status_update.emit("Cannot open preview: No monitor data.", 3000)
                return

        if not self.capture_preview_dialog:
            self.capture_preview_dialog = CapturePreviewDialog(parent=self.ui_manager if isinstance(self.ui_manager, QObject) else None)
            self.capture_preview_dialog.sampling_parameters_changed.connect(self._handle_dialog_full_params_changed)
            self.capture_preview_dialog.dialog_closed.connect(self._on_capture_preview_dialog_closed)

        # 1. Apply preferences for the currently selected monitor to self.current_sampler_params
        # This ensures self.current_sampler_params has the latest loaded/saved state for this monitor.
        self._apply_prefs_for_current_monitor()
        
        # ADD THIS DEBUG PRINT:
        # print(f"DEBUG SSM._show_capture_preview_dialog: AFTER apply_prefs, current_sampler_params BEING PASSED IS: monitor_id={self.current_sampler_params.get('monitor_id')}, region={self.current_sampler_params.get('region_rect_percentage')}, adjustments={self.current_sampler_params.get('adjustments')}")

        # 2. Inform the dialog about all available monitors and which one is currently targeted.
        #    The dialog uses this to set up its MonitorViewWidget.
        if hasattr(self.capture_preview_dialog, 'set_initial_monitor_data'):
            self.capture_preview_dialog.set_initial_monitor_data(
            self.screen_sampler_monitor_list_cache,
            self.current_sampler_params['monitor_id'] 
            )
        # else:
        #     print("CRITICAL WARNING (SSM._show_capture_preview_dialog): capture_preview_dialog missing 'set_initial_monitor_data'")


        # 3. Pass the specific parameters (including region and adjustments for the target monitor)
        #    to the dialog so it can set its sliders and the MonitorViewWidget's selection box.
        if hasattr(self.capture_preview_dialog, 'set_current_parameters_from_main'):
            self.capture_preview_dialog.set_current_parameters_from_main(self.current_sampler_params)
        # else:
        #     print("CRITICAL WARNING (SSM._show_capture_preview_dialog): capture_preview_dialog missing 'set_current_parameters_from_main'")


        if self._last_processed_pil_image:
            if hasattr(self.capture_preview_dialog, 'update_preview_image'):
                self.capture_preview_dialog.update_preview_image(self._last_processed_pil_image)
            else:
                print("WARNING (SSM._show_capture_preview_dialog): capture_preview_dialog missing 'update_preview_image'")

        self.capture_preview_dialog.show()
        self.capture_preview_dialog.activateWindow()
        self.capture_preview_dialog.raise_()


    def _on_capture_preview_dialog_closed(self):
        if self.capture_preview_dialog:
            try: # Gracefully disconnect signals
                self.capture_preview_dialog.sampling_parameters_changed.disconnect(self._handle_dialog_full_params_changed)
                self.capture_preview_dialog.dialog_closed.disconnect(self._on_capture_preview_dialog_closed)
            except TypeError: # Signals might have already been disconnected or never connected
                pass 
            self.capture_preview_dialog.deleteLater()
            self.capture_preview_dialog = None

    def _handle_dialog_full_params_changed(self, full_dialog_params: dict):
        new_monitor_id = full_dialog_params.get('monitor_id', self.current_sampler_params['monitor_id'])
        self.current_sampler_params['monitor_id'] = new_monitor_id
        self.current_sampler_params['region_rect_percentage'] = full_dialog_params.get('region_rect_percentage', self.current_sampler_params['region_rect_percentage'])
        self.current_sampler_params['adjustments'] = full_dialog_params.get('adjustments', self.current_sampler_params['adjustments'])

        self._save_prefs_for_current_monitor()

        if hasattr(self.ui_manager, 'set_selected_monitor_ui'):
            self.ui_manager.set_selected_monitor_ui(self.current_sampler_params['monitor_id'])
        else:
            print(f"WARNING (SSM._handle_dialog_full_params_changed): self.ui_manager missing 'set_selected_monitor_ui'")


        if self.is_sampling_thread_active:
            self._synchronize_and_control_sampling_thread(True)

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
                adjustments=self.current_sampler_params['adjustments']
            )
            self.sampler_status_update.emit("Screen sampling active.", 0)
        else:
            if self.is_sampling_thread_active:
                if self.is_actively_recording:
                    self._stop_recording_logic(inform_user=False)

                if self.sampling_thread.isRunning():
                    self.sampling_thread.stop_sampling()

                self.is_sampling_thread_active = False
                self.sampling_activity_changed.emit(False)
                self.sampler_status_update.emit("Screen sampling stopped.", 2000)

        if GUI_IMPORTS_OK and hasattr(self.ui_manager, 'update_record_button_ui') and hasattr(self.ui_manager, 'set_recording_status_text'):
            if self.is_sampling_thread_active and not self.is_actively_recording:
                self.ui_manager.set_recording_status_text("Idle. Ready to record.")
                self.ui_manager.update_record_button_ui(is_recording=False, can_record=True)
            elif not self.is_sampling_thread_active:
                self.ui_manager.set_recording_status_text("Sampler OFF")
                self.ui_manager.update_record_button_ui(is_recording=False, can_record=False)

    def force_disable_sampling_ui(self):
        if not GUI_IMPORTS_OK: return

        if hasattr(self.ui_manager, 'enable_sampling_button') and self.ui_manager.enable_sampling_button and \
           hasattr(self.ui_manager.enable_sampling_button, 'isChecked') and \
           hasattr(self.ui_manager.enable_sampling_button, 'setChecked'):
            if self.ui_manager.enable_sampling_button.isChecked():
                 self.ui_manager.enable_sampling_button.setChecked(False)
        else:
            self._synchronize_and_control_sampling_thread(False)


    def stop_sampling_thread(self):
        self._synchronize_and_control_sampling_thread(False)

    def _handle_thread_pad_colors_sampled(self, colors_list: list):
        if self.is_actively_recording:
            if self.current_recording_frame_count < self.MAX_RECORDING_FRAMES:
                if colors_list and len(colors_list) == ScreenSamplerCore.NUM_GRID_ROWS * ScreenSamplerCore.NUM_GRID_COLS:
                    hex_frame = [QColor(r, g, b).name() for r, g, b in colors_list]
                    self.recorded_sampler_frames.append(hex_frame)
                    self.current_recording_frame_count += 1
                    if GUI_IMPORTS_OK and hasattr(self.ui_manager, 'set_recording_status_text'):
                        self.ui_manager.set_recording_status_text(
                            f"REC 🔴 {self.current_recording_frame_count}/{self.MAX_RECORDING_FRAMES}")
                if self.current_recording_frame_count >= self.MAX_RECORDING_FRAMES:
                    self.sampler_status_update.emit(f"Max recording frames ({self.MAX_RECORDING_FRAMES}) reached.", 3000)
                    self._stop_recording_logic()

        if self.is_sampling_thread_active:
            self.sampled_colors_for_display.emit(colors_list)

    def _handle_thread_processed_image_ready(self, pil_image: Image.Image):
        self._last_processed_pil_image = pil_image
        if self.capture_preview_dialog and self.capture_preview_dialog.isVisible():
            self.capture_preview_dialog.update_preview_image(pil_image)
        self.processed_image_for_preview.emit(pil_image)

    def _handle_thread_error_occurred(self, error_message: str):
        self.sampler_status_update.emit(f"Sampler Thread Error: {error_message}", 7000)
        if "FATAL: mss library init failed" in error_message or "No monitors found" in error_message:
            if GUI_IMPORTS_OK:
                if hasattr(self.ui_manager, 'force_disable_sampling_ui'):
                    self.ui_manager.force_disable_sampling_ui()
                if hasattr(self.ui_manager, 'setEnabled'): # QGroupBox method
                    self.ui_manager.setEnabled(False)
            if self.capture_preview_dialog: self.capture_preview_dialog.close()

    def _on_ui_record_button_clicked(self):
        if not GUI_IMPORTS_OK: return

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
                    QTimer.singleShot(250, self._start_recording_logic_if_sampler_active)
                else:
                    self.sampler_status_update.emit("Recording cancelled; sampler not started.", 2000)
                return
            self._start_recording_logic()

    def _start_recording_logic_if_sampler_active(self):
        if self.is_sampling_thread_active:
            self._start_recording_logic()
        else:
            self.sampler_status_update.emit("Failed to start sampler for recording.", 3000)
            if GUI_IMPORTS_OK and hasattr(self.ui_manager, 'update_record_button_ui'):
                self.ui_manager.update_record_button_ui(is_recording=False, can_record=False)

    def _start_recording_logic(self):
        if not self.is_sampling_thread_active:
            self.sampler_status_update.emit("Cannot record: Sampler not active.", 3000)
            if GUI_IMPORTS_OK and hasattr(self.ui_manager, 'update_record_button_ui'):
                self.ui_manager.update_record_button_ui(is_recording=False, can_record=False)
            return

        self.is_actively_recording = True
        self.recorded_sampler_frames.clear()
        self.current_recording_frame_count = 0
        self.captured_sampler_frequency_ms = self.current_sampler_params['frequency_ms']

        self.sampler_status_update.emit("Sampler recording started...", 0)
        if GUI_IMPORTS_OK and hasattr(self.ui_manager, 'update_record_button_ui') and hasattr(self.ui_manager, 'set_recording_status_text'):
            self.ui_manager.update_record_button_ui(is_recording=True, can_record=False)
            self.ui_manager.set_recording_status_text(f"REC 🔴 0/{self.MAX_RECORDING_FRAMES}")

    def _stop_recording_logic(self, inform_user=True):
        was_recording = self.is_actively_recording
        self.is_actively_recording = False
        final_frame_count = self.current_recording_frame_count

        if GUI_IMPORTS_OK and hasattr(self.ui_manager, 'update_record_button_ui') and hasattr(self.ui_manager, 'set_recording_status_text'):
            self.ui_manager.update_record_button_ui(is_recording=False, can_record=self.is_sampling_thread_active)

            if not was_recording and final_frame_count == 0:
                if self.is_sampling_thread_active:
                    self.ui_manager.set_recording_status_text("Idle.")
                return

            if inform_user:
                self.sampler_status_update.emit(f"Recording stopped. {final_frame_count} frames captured.", 5000)
            
            if self.is_sampling_thread_active :
                self.ui_manager.set_recording_status_text(f"Idle. ({final_frame_count} frames recorded)")
            else:
                self.ui_manager.set_recording_status_text(f"Sampler OFF ({final_frame_count} frames recorded)")
        
        if self.recorded_sampler_frames:
            self._process_and_save_recorded_frames()
        elif inform_user:
            self.sampler_status_update.emit("No frames were recorded.", 2000)

    def _process_and_save_recorded_frames(self):
        if not self.recorded_sampler_frames or not GUI_IMPORTS_OK: return

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
                self.recorded_sampler_frames.clear(); self.current_recording_frame_count = 0
                if hasattr(self.ui_manager, 'set_recording_status_text'):
                    self.ui_manager.set_recording_status_text("Recording discarded.")
                self.sampler_status_update.emit("Recorded frames discarded.", 2000)
            else:
                if hasattr(self.ui_manager, 'set_recording_status_text') and hasattr(self.ui_manager, 'update_record_button_ui'):
                    self.ui_manager.set_recording_status_text(f"Ready to save {num_frames} frames. Click Record again to re-prompt.")
                    self.is_actively_recording = True 
                    self.ui_manager.update_record_button_ui(is_recording=True, can_record=False)
            return

        final_name_base = user_name.strip()
        if not self.animator_manager_ref:
            self.sampler_status_update.emit("Error: Animator reference missing for saving.", 5000); return

        try:
            sanitized_base = self.animator_manager_ref._sanitize_filename(final_name_base)
            sampler_dir = self.animator_manager_ref._get_sequence_dir_path("sampler")
        except AttributeError:
            print("WARNING: AnimatorManagerWidget utility methods not found. Using basic fallback for saving.")
            sanitized_base = "".join(c if c.isalnum() or c in (' ', '_', '-') else '_' for c in final_name_base).rstrip()
            sampler_dir = os.path.join(self.presets_base_path, "sequences", "sampler_recordings")

        os.makedirs(sampler_dir, exist_ok=True)
        actual_filepath = os.path.join(sampler_dir, f"{sanitized_base}.json")
        actual_model_name = final_name_base
        counter = 0
        while os.path.exists(actual_filepath):
            counter += 1
            actual_model_name = f"{final_name_base}_{counter}"
            new_sanitized_base_name_part = "".join(c if c.isalnum() or c in (' ', '_', '-') else '_' for c in actual_model_name).rstrip()
            actual_filepath = os.path.join(sampler_dir, f"{new_sanitized_base_name_part}.json")
            if counter > 100: self.sampler_status_update.emit("Save Error: Too many filename collisions.", 5000); return

        temp_model = SequenceModel(name=actual_model_name)
        for frame_hex_data in self.recorded_sampler_frames:
            temp_model.frames.append(AnimationFrame(colors=frame_hex_data))
        temp_model.frame_delay_ms = self.captured_sampler_frequency_ms
        temp_model.loop = True

        if temp_model.save_to_file(actual_filepath):
            self.sampler_status_update.emit(f"Sequence '{actual_model_name}' saved.", 3000)
            self.new_sequence_from_recording_ready.emit(actual_filepath)
            if hasattr(self.ui_manager, 'set_recording_status_text'):
                self.ui_manager.set_recording_status_text(f"Saved: {actual_model_name}")
        else:
            self.sampler_status_update.emit(f"Error saving to '{actual_filepath}'.", 5000)
            if hasattr(self.ui_manager, 'set_recording_status_text'):
                self.ui_manager.set_recording_status_text("Error saving recording.")

        self.recorded_sampler_frames.clear()
        self.current_recording_frame_count = 0

    def _on_ui_set_max_frames_button_clicked(self):
        if not GUI_IMPORTS_OK: return
        new_max, ok = SetMaxFramesDialog.get_max_frames(
            parent_widget=self.ui_manager if isinstance(self.ui_manager, QObject) else None, 
            current_value=self.MAX_RECORDING_FRAMES
        )
        if ok and new_max is not None:
            self.MAX_RECORDING_FRAMES = new_max
            self.sampler_status_update.emit(f"Max recording frames set to {self.MAX_RECORDING_FRAMES}.", 3000)
            if self.is_actively_recording and hasattr(self.ui_manager, 'set_recording_status_text'):
                self.ui_manager.set_recording_status_text(
                    f"REC 🔴 {self.current_recording_frame_count}/{self.MAX_RECORDING_FRAMES}")

# In ScreenSamplerManager
    def _generate_monitor_key(self, monitor_id: int) -> str | None:
        # If cache is empty, it's okay to try and populate it ONCE.
        # But do not use force_fetch=True here, as that creates the loop if called from populate_monitor_list_for_ui flow.
        # populate_monitor_list_for_ui itself will decide if a fetch is needed based on its own force_fetch flag and cache state.
        if not self.screen_sampler_monitor_list_cache:
            # print(f"DEBUG SSM._generate_monitor_key: Cache empty, calling populate_monitor_list_for_ui(force_fetch=False)")
            # Call with force_fetch=False. If populate_monitor_list_for_ui was *just* called and filled the cache,
            # it won't re-fetch. If it's a genuine first call from somewhere else, it will fetch if needed.
            self.populate_monitor_list_for_ui(force_fetch=False) 
            # After the call, the cache should be populated if monitors were found. Check again.
            if not self.screen_sampler_monitor_list_cache: # Still empty after attempt?
                 # print(f"DEBUG SSM._generate_monitor_key: Cache still empty after pop attempt. Returning None.")
                 return None
        
        monitor_info = next((m for m in self.screen_sampler_monitor_list_cache if m['id'] == monitor_id), None)
        if monitor_info:
            return f"{monitor_info['width']}x{monitor_info['height']}_{monitor_info['left']}_{monitor_info['top']}"
        return None

    def _apply_prefs_for_current_monitor(self):
        # print(f"DEBUG SSM._apply_prefs: Current monitor_id to apply for: {self.current_sampler_params['monitor_id']}")
        monitor_key = self._generate_monitor_key(self.current_sampler_params['monitor_id'])
        # print(f"DEBUG SSM._apply_prefs: Generated key: {monitor_key}")
        # print(f"DEBUG SSM._apply_prefs: Available keys in prefs: {list(self.sampler_monitor_prefs.keys())}")

        if monitor_key and monitor_key in self.sampler_monitor_prefs:
            saved_prefs = self.sampler_monitor_prefs[monitor_key]
            # print(f"DEBUG SSM._apply_prefs: Found prefs for key '{monitor_key}': {saved_prefs}")
            self.current_sampler_params['region_rect_percentage'] = saved_prefs.get('region_rect_percentage', self.current_sampler_params['region_rect_percentage'])
            self.current_sampler_params['adjustments'] = saved_prefs.get('adjustments', ScreenSamplerCore.DEFAULT_ADJUSTMENTS.copy())
            # print(f"DEBUG SSM._apply_prefs: AFTER apply, current_sampler_params[region]: {self.current_sampler_params['region_rect_percentage']}")
        else:
            # print(f"DEBUG SSM._apply_prefs: No prefs found for key '{monitor_key}'. Using defaults.")
            self.current_sampler_params['region_rect_percentage'] = {'x': 0.4, 'y': 0.4, 'width': 0.2, 'height': 0.2}
            self.current_sampler_params['adjustments'] = ScreenSamplerCore.DEFAULT_ADJUSTMENTS.copy()
            # print(f"DEBUG SSM._apply_prefs: AFTER default, current_sampler_params[region]: {self.current_sampler_params['region_rect_percentage']}")


    def _save_prefs_for_current_monitor(self):
        """Saves the current_sampler_params (region/adjustments) for the current monitor_id
           AND updates the in-memory cache of all monitor preferences."""
        monitor_key = self._generate_monitor_key(self.current_sampler_params['monitor_id'])
        if monitor_key:
            # Create the data to save for this specific monitor
            current_monitor_data_to_save = {
                'region_rect_percentage': self.current_sampler_params['region_rect_percentage'].copy(),
                'adjustments': self.current_sampler_params['adjustments'].copy()
            }
            
            # Update the in-memory cache
            self.sampler_monitor_prefs[monitor_key] = current_monitor_data_to_save
            # print(f"DEBUG SSM._save_prefs_for_current_monitor: Updated in-memory self.sampler_monitor_prefs[{monitor_key}] to: {current_monitor_data_to_save}")

            # Persist all monitor preferences (including this update) to disk
            self._save_sampler_preferences_to_file()

    def _load_sampler_preferences(self):
        if os.path.exists(self.sampler_prefs_file_path):
            try:
                with open(self.sampler_prefs_file_path, 'r') as f:
                    loaded_prefs = json.load(f)
                self.sampler_monitor_prefs = loaded_prefs.get("monitor_configurations", {})
                last_active_key = loaded_prefs.get("last_active_monitor_key")
                if last_active_key and last_active_key in self.sampler_monitor_prefs and self.screen_sampler_monitor_list_cache:
                     for mon_info in self.screen_sampler_monitor_list_cache:
                        key_check = f"{mon_info['width']}x{mon_info['height']}_{mon_info['left']}_{mon_info['top']}"
                        if key_check == last_active_key:
                            self.current_sampler_params['monitor_id'] = mon_info['id']
                            break
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
                "last_active_monitor_key": self._generate_monitor_key(self.current_sampler_params['monitor_id'])
            }
            os.makedirs(os.path.dirname(self.sampler_prefs_file_path), exist_ok=True)
            with open(self.sampler_prefs_file_path, 'w') as f:
                json.dump(data_to_save, f, indent=4)
        except Exception as e:
            self.sampler_status_update.emit(f"Error saving sampler prefs: {e}", 3000)

    def _fps_to_ms(self, fps: int) -> int:
        if fps <= 0: return 1000
        return int(1000.0 / fps)

    def on_application_exit(self):
        if self.is_sampling_thread_active:
            self.stop_sampling_thread()
        self._save_sampler_preferences_to_file()
        print("ScreenSamplerManager: Preferences saved on exit.")

    def _update_preview_dialog_sliders_if_visible(self, adjustments: dict):
        """
        Updates the preview dialog's sliders if the dialog is currently visible.
        Called when sampler adjustments are changed externally (e.g., by MainWindow knobs).
        """
        if self.capture_preview_dialog and self.capture_preview_dialog.isVisible():
            if hasattr(self.capture_preview_dialog, 'update_sliders_from_external_adjustments'):
                self.capture_preview_dialog.update_sliders_from_external_adjustments(adjustments)
            else:
                print("SSM WARNING: CapturePreviewDialog missing 'update_sliders_from_external_adjustments'")