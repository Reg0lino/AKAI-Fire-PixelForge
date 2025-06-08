# AKAI_Fire_RGB_Controller/managers/audio_visualizer_manager.py

import pyaudiowpatch as pyaudio
import numpy as np
import time
import json
import os
from PyQt6.QtCore import QObject, pyqtSignal, QTimer, QThread
from PyQt6.QtGui import QColor

# --- Configuration Constants ---
DEFAULT_CHUNK_SIZE = 1024 * 2
DEFAULT_FORMAT = pyaudio.paInt16
DEFAULT_CHANNELS = 2
NUMBER_OF_BANDS = 8

DEFAULT_MANAGER_BAND_COLORS_QCOLOR = [
    QColor("red"), QColor("orange"), QColor("yellow"), QColor("green"),
    QColor("cyan"), QColor("blue"), QColor("magenta"), QColor("purple")
]
DEFAULT_MANAGER_SENSITIVITY = 1.0
DEFAULT_MANAGER_SMOOTHING = 0.2

APP_NAME_FOR_CONFIG = "Akai Fire RGB Controller"
APP_AUTHOR_FOR_CONFIG = "Reg0lino"


class AudioProcessingThread(QThread):
    fft_data_ready = pyqtSignal(np.ndarray, int, int)
    error_occurred = pyqtSignal(str)

    def __init__(self, device_index, rate, channels, chunk_size, format_pa, parent=None):
        super().__init__(parent)
        self.device_index = device_index
        self.rate = rate
        self.channels = channels
        self.chunk_size = chunk_size
        self.format_pa = format_pa
        self.p_audio = None
        self.stream = None
        self._is_running = False
        self.setObjectName(f"AudioProcessingThread_Dev{device_index}")
        print(f"APT DEBUG ({self.objectName()}): __init__ called. _is_running = {self._is_running}") # DIAGNOSTIC


    def run(self):
        self._is_running = True
        thread_name = self.objectName()  # Get object name for cleaner logs
        # print(
        #     f"APT TRACE ({thread_name}): run() started. _is_running = {self._is_running}. Device: {self.device_index}")
        self.p_audio = pyaudio.PyAudio()

        loop_iteration_count = 0  # Counter for iterations

        try:
            # print(f"APT TRACE ({thread_name}): Attempting to open stream...")
            self.stream = self.p_audio.open(format=self.format_pa,
                                            channels=self.channels,
                                            rate=self.rate,
                                            input=True,
                                            frames_per_buffer=self.chunk_size,
                                            input_device_index=self.device_index,
                                            stream_callback=None)  # Explicitly no callback
            # print(
            #     f"APT TRACE ({thread_name}): Stream opened successfully. Entering while loop.")

            while self._is_running:
                loop_iteration_count += 1
                # print(f"APT TRACE ({thread_name}): Loop iteration {loop_iteration_count}. _is_running = {self._is_running}") # Can be very noisy

                try:
                #     print(f"APT TRACE ({thread_name}): Attempting self.stream.read({self.chunk_size})...") # Very noisy if working
                    raw_data = self.stream.read(
                        self.chunk_size, exception_on_overflow=False)
                #     print(f"APT TRACE ({thread_name}): self.stream.read() returned {len(raw_data)} bytes.") # Very noisy if working

                    if not self._is_running:  # Check again after blocking read
                #         print(
                #             f"APT TRACE ({thread_name}): _is_running became False during/after stream.read(). Exiting loop.")
                        break

                    if len(raw_data) == 0:
                        print(
                            f"APT WARN ({thread_name}): stream.read() returned 0 bytes. Loop iteration {loop_iteration_count}.")
                        # Small sleep if no data, to prevent tight spin
                        QThread.msleep(10)
                        continue

                    data_np = np.frombuffer(raw_data, dtype=np.int16)

                    if self.channels == 2:
                        data_mono = data_np.astype(np.float32)
                        if len(data_mono) > 0:
                            data_mono = (
                                data_mono[0::2] + data_mono[1::2]) / 2.0
                        else:
                            data_mono = np.array([], dtype=np.float32)
                    else:
                        data_mono = data_np.astype(np.float32)

                    if len(data_mono) > 0:
                        fft_result = np.fft.fft(data_mono)
                        fft_magnitudes = np.abs(
                            fft_result[:len(data_mono) // 2])
                        # print(f"APT TRACE ({thread_name}): Emitting fft_data_ready. Iteration: {loop_iteration_count}") # Noisy
                        self.fft_data_ready.emit(
                            fft_magnitudes, self.rate, len(data_mono))
                    # else:
                        # print(f"APT TRACE ({thread_name}): data_mono was empty after processing. Iteration: {loop_iteration_count}.")

                except IOError as e:
                    if hasattr(pyaudio, 'paInputOverflowed') and e.errno == pyaudio.paInputOverflowed:
                        # print(f"APT WARN ({thread_name}): Input overflowed.")
                        continue
                    else:
                        err_msg = f"IOError in stream read: {e}"
                        # print(f"APT ERROR ({thread_name}): {err_msg}")
                        self.error_occurred.emit(err_msg)
                        break
                except Exception as e_loop:
                    err_msg = f"Error in audio loop: {e_loop}"
                    # print(f"APT ERROR ({thread_name}): {err_msg}")
                    self.error_occurred.emit(err_msg)
                    break

            # print(
                # f"APT TRACE ({thread_name}): Exited while loop. _is_running is {self._is_running}. Total iterations: {loop_iteration_count}.")

        except Exception as e_stream:
            error_msg = f"Failed to open audio stream on device {self.device_index}: {e_stream}"
            # print(f"APT ERROR ({thread_name}): {error_msg}")
            self.error_occurred.emit(error_msg)
        finally:
            # ... (cleanup remains the same) ...
            if self.stream:
                try:
                    if self.stream.is_active():
                        self.stream.stop_stream()
                    self.stream.close()
                except Exception as e_close:
                    print(
                        f"APT WARN ({thread_name}): Error closing stream: {e_close}")
            if self.p_audio:
                try:
                    self.p_audio.terminate()
                except Exception as e_term:
                    print(
                        f"APT WARN ({thread_name}): Error terminating PyAudio: {e_term}")
            self._is_running = False  # Ensure it's false on exit
            # print(
            #     f"APT TRACE ({thread_name}): run() method finished. _is_running = {self._is_running}")


    def stop(self):
        # print(f"APT DEBUG ({self.objectName()}): stop() called. Setting _is_running to False.") # DIAGNOSTIC
        self._is_running = False


class AudioVisualizerManager(QObject):
    pad_data_ready = pyqtSignal(list)
    available_devices_updated = pyqtSignal(list)
    capture_error = pyqtSignal(str)
    capture_started_signal = pyqtSignal()
    capture_stopped_signal = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.p_audio_instance = None
        self.devices_info_cache = []
        self.selected_device_index: int | None = None
        self.is_capturing = False
        self.audio_thread: AudioProcessingThread | None = None

        self.all_mode_settings_cache = self._load_all_mode_settings_from_persistence()
        
        self.current_visualization_mode = "classic_spectrum_bars"
        self.band_colors: list[QColor] = []
        self.global_sensitivity: float = DEFAULT_MANAGER_SENSITIVITY
        self.smoothing_factor: float = DEFAULT_MANAGER_SMOOTHING
        self._smoothed_band_powers = np.zeros(NUMBER_OF_BANDS)
        self._apply_settings_for_current_mode()
        self.refresh_audio_devices()

    def _get_main_settings_filepath(self) -> str:
        try:
            from appdirs import user_config_dir
            config_dir = user_config_dir(
                APP_NAME_FOR_CONFIG, APP_AUTHOR_FOR_CONFIG, roaming=True)
            os.makedirs(config_dir, exist_ok=True)
            return os.path.join(config_dir, "visualizer_main_settings.json")
        except ImportError:
            return "visualizer_main_settings_fallback.json"
        except Exception:
            return "visualizer_main_settings_fallback.json"


    def _load_all_mode_settings_from_persistence(self) -> dict:
        filepath = self._get_main_settings_filepath()
        default_settings_structure = {  # Define default structure once
            "classic_spectrum_bars": {"band_colors": [c.name() for c in DEFAULT_MANAGER_BAND_COLORS_QCOLOR], "sensitivity": DEFAULT_MANAGER_SENSITIVITY, "smoothing": DEFAULT_MANAGER_SMOOTHING},
            "pulse_wave_matrix": {"palette": [QColor("cyan").name(), QColor("magenta").name()], "pulse_speed": 0.5},
            "dual_vu_spectrum": {"vu_low_color": QColor("green").name(), "bass_spectrum_color": QColor("red").name()}
        }

        if os.path.exists(filepath):
            try:
                with open(filepath, 'r') as f:
                    loaded_settings = json.load(f)
                    if isinstance(loaded_settings, dict):
                        # DIAGNOSTIC
                        print(
                            f"AVM DEBUG (_load_all_mode_settings_from_persistence): Loaded from file: {loaded_settings}")
                        # Ensure all primary mode keys exist, if not, add them from default
                        for mode_key, default_mode_settings in default_settings_structure.items():
                            if mode_key not in loaded_settings:
                                print(
                                    f"AVM DEBUG: Mode key '{mode_key}' not in loaded file, adding defaults for it.")
                                loaded_settings[mode_key] = default_mode_settings
                        return loaded_settings
                    else:
                        print(
                            f"AVM WARN: visualizer_main_settings.json is not a valid dictionary. Using full defaults.")
            except Exception as e:
                print(
                    f"AVM WARN: Error loading visualizer_main_settings.json: {e}. Using full defaults.")

        # DIAGNOSTIC
        print(
            f"AVM DEBUG (_load_all_mode_settings_from_persistence): File not found or error. Returning hardcoded defaults: {default_settings_structure}")
        return default_settings_structure

    def _save_all_mode_settings_to_persistence(self):
        filepath = self._get_main_settings_filepath()
        try:
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            with open(filepath, 'w') as f:
                json.dump(self.all_mode_settings_cache, f, indent=4)
        except Exception as e:
            print(f"AVM ERROR: Could not save main settings: {e}")

    def get_all_mode_settings(self) -> dict:
        copied_settings = {}
        for mode, settings_dict in self.all_mode_settings_cache.items():
            copied_settings[mode] = settings_dict.copy()
            for key, value in settings_dict.items():
                if isinstance(value, list):
                    copied_settings[mode][key] = list(value)
        return copied_settings

    def update_all_settings_from_dialog(self, new_settings_from_dialog: dict):
        # DIAGNOSTIC
        print(
            f"AVM DEBUG (update_all_settings_from_dialog): Received (UI scale): {new_settings_from_dialog}")
        for mode_key, dialog_mode_settings in new_settings_from_dialog.items():
            if not isinstance(dialog_mode_settings, dict):
                continue
            if mode_key not in self.all_mode_settings_cache:
                self.all_mode_settings_cache[mode_key] = {}

            cache = self.all_mode_settings_cache[mode_key]
            if mode_key == "classic_spectrum_bars":
                if "band_colors" in dialog_mode_settings:
                    cache["band_colors"] = list(
                        dialog_mode_settings["band_colors"])
                if "sensitivity" in dialog_mode_settings:
                    cache["sensitivity"] = dialog_mode_settings["sensitivity"] / 50.0
                if "smoothing" in dialog_mode_settings:
                    cache["smoothing"] = dialog_mode_settings["smoothing"] / 100.0
                # DIAGNOSTIC
                print(
                    f"AVM DEBUG (update_all_settings_from_dialog): classic_spectrum_bars cache updated to: {cache}")
            elif mode_key == "pulse_wave_matrix":
                if "palette" in dialog_mode_settings:
                    cache["palette"] = list(dialog_mode_settings["palette"])
                if "pulse_speed" in dialog_mode_settings:
                    cache["pulse_speed"] = dialog_mode_settings["pulse_speed"] / 100.0
            else:  # Fallback for unhandled modes
                for key, value in dialog_mode_settings.items():
                    cache[key] = value

        self._apply_settings_for_current_mode()
        self._save_all_mode_settings_to_persistence()

    def _apply_settings_for_current_mode(self):
        # Should be "classic_spectrum_bars"
        current_mode_key_to_check = self.current_visualization_mode
        print(f"AVM DEEP DEBUG (_apply_settings_for_current_mode): Current mode key to check is: '{current_mode_key_to_check}' (Type: {type(current_mode_key_to_check)})")

        cache_keys = list(self.all_mode_settings_cache.keys())
        print(f"AVM DEEP DEBUG (_apply_settings_for_current_mode): Cache keys BEFORE access: {cache_keys}")
        for key_in_cache in cache_keys:
            print(f"    Cache Key: '{key_in_cache}' (Type: {type(key_in_cache)}), Match with current_mode_key_to_check: {key_in_cache == current_mode_key_to_check}")

        mode_settings = None
        if current_mode_key_to_check in self.all_mode_settings_cache:
            mode_settings = self.all_mode_settings_cache[current_mode_key_to_check]
            print(f"AVM DEEP DEBUG (_apply_settings_for_current_mode): Successfully accessed settings for '{current_mode_key_to_check}' using direct key access.")
        else:
            print(f"AVM DEEP DEBUG (_apply_settings_for_current_mode): Key '{current_mode_key_to_check}' NOT FOUND in cache using 'in' operator.")

        if not mode_settings:
            print(f"AVM WARN: No settings in cache for '{current_mode_key_to_check}'. Using fallbacks. (This means mode_settings is None or empty after checks)")
            self.band_colors = list(DEFAULT_MANAGER_BAND_COLORS_QCOLOR)
            self.global_sensitivity = DEFAULT_MANAGER_SENSITIVITY
            self.smoothing_factor = DEFAULT_MANAGER_SMOOTHING
            # --- ADDED DIAGNOSTIC FOR FALLBACK ---
            # print(
            #     f"AVM DIAGNOSTIC (_apply_settings_for_current_mode FALLBACK): Operational Band Colors set to default: {[c.name() for c in self.band_colors]}")
            # --- END DIAGNOSTIC ---
            return

        if self.current_visualization_mode == "classic_spectrum_bars":
            hex_colors = mode_settings.get(
                "band_colors", [c.name() for c in DEFAULT_MANAGER_BAND_COLORS_QCOLOR])
            self.band_colors = [QColor(hc) for hc in hex_colors]
            if len(self.band_colors) < NUMBER_OF_BANDS:
                self.band_colors.extend(
                    DEFAULT_MANAGER_BAND_COLORS_QCOLOR[len(self.band_colors):NUMBER_OF_BANDS])
            self.band_colors = self.band_colors[:NUMBER_OF_BANDS]
            self.global_sensitivity = mode_settings.get(
                "sensitivity", DEFAULT_MANAGER_SENSITIVITY)
            self.smoothing_factor = mode_settings.get(
                "smoothing", DEFAULT_MANAGER_SMOOTHING)
            # --- MODIFIED DIAGNOSTIC TO ALWAYS PRINT ---
            # print(
            #     f"AVM DIAGNOSTIC (_apply_settings_for_current_mode SUCCESS): Operational Band Colors: {[c.name() for c in self.band_colors]}")
            # print(
            #     f"AVM DIAGNOSTIC (_apply_settings_for_current_mode SUCCESS): Operational Sensitivity: {self.global_sensitivity}, Smoothing: {self.smoothing_factor}")
            # --- END MODIFIED DIAGNOSTIC ---

        elif self.current_visualization_mode == "pulse_wave_matrix":
            print(f"AVM DEBUG (_apply_settings_for_current_mode): Pulse Wave settings applied (details TBD).")
            pass


    def refresh_audio_devices(self):
        if self.is_capturing:
            self.stop_capture()
        if self.p_audio_instance:
            try:
                self.p_audio_instance.terminate()
            except Exception:
                pass
        self.p_audio_instance = pyaudio.PyAudio()
        self.devices_info_cache = []
        try:
            num_devices = self.p_audio_instance.get_host_api_info_by_index(
                0).get('deviceCount', 0)
            for i in range(num_devices):
                try:
                    dev_info = self.p_audio_instance.get_device_info_by_index(
                        i)
                    if dev_info.get('maxInputChannels', 0) > 0:
                        entry = {'name': dev_info.get('name'), 'index': dev_info.get('index'),
                                 'max_input_channels': dev_info.get('maxInputChannels'),
                                 'default_sample_rate': dev_info.get('defaultSampleRate'),
                                 'is_loopback_flag': dev_info.get('isLoopbackDevice', False),
                                 'type': 'standard_input'}
                        if not any(d['index'] == entry['index'] for d in self.devices_info_cache):
                            self.devices_info_cache.append(entry)
                except Exception:
                    pass
        except Exception:
            pass
        try:
            for gen_info in self.p_audio_instance.get_loopback_device_info_generator():
                idx, name = gen_info.get('index'), gen_info.get('name')
                if idx is not None:
                    try:
                        actual_info = self.p_audio_instance.get_device_info_by_index(
                            idx)
                        existing = next(
                            (d for d in self.devices_info_cache if d['index'] == idx), None)
                        if existing:
                            existing['is_loopback_flag'] = True
                            existing['name'] = f"{actual_info.get('name')} (Loopback for: {name})"
                            existing['type'] = 'loopback_gen_updated'
                        else:
                            self.devices_info_cache.append({
                                'name': f"{actual_info.get('name')} (Loopback for: {name})", 'index': idx,
                                'max_input_channels': actual_info.get('maxInputChannels'),
                                'default_sample_rate': actual_info.get('defaultSampleRate'),
                                'is_loopback_flag': True, 'type': 'loopback_gen_new'})
                    except Exception:
                        pass
        except AttributeError:
            pass  # Older pyaudiowpatch might not have generator
        except Exception:
            pass
        self.devices_info_cache.sort(key=lambda x: x['index'])
        self.available_devices_updated.emit(self.devices_info_cache)

    def get_default_loopback_device_info(self) -> dict | None:
        if not self.p_audio_instance:
            self.p_audio_instance = pyaudio.PyAudio()
        if not self.devices_info_cache:
            self.refresh_audio_devices()
        try:
            default_out_info = self.p_audio_instance.get_default_output_device_info()
            default_out_name = default_out_info['name']
            for candidate_info in self.p_audio_instance.get_loopback_device_info_generator():
                loop_out_name = candidate_info.get("name", "")
                loop_in_idx = candidate_info.get('index')
                orig_out_idx = candidate_info.get('deviceIndex')
                if orig_out_idx == default_out_info['index'] or loop_out_name.startswith(default_out_name):
                    if loop_in_idx is not None:
                        try:
                            actual_info = self.p_audio_instance.get_device_info_by_index(
                                loop_in_idx)
                            return {'name': actual_info.get('name'), 'index': loop_in_idx,
                                    'max_input_channels': actual_info.get('maxInputChannels'),
                                    'default_sample_rate': actual_info.get('defaultSampleRate'),
                                    'is_loopback_flag': True}
                        except Exception:
                            pass
        except AttributeError:
            pass
        except Exception:
            pass
        if self.devices_info_cache:
            for dev in self.devices_info_cache:
                if dev.get('is_loopback_flag', False):
                    return dev
            keywords = ["stereo mix", "wave out", "what u hear", "loopback"]
            for dev in self.devices_info_cache:
                if any(k in dev.get('name', '').lower() for k in keywords):
                    return dev
        return None

    def set_selected_device_index(self, idx: int | None):
        if self.selected_device_index == idx:
            return
        was_capturing = self.is_capturing
        if was_capturing:
            self.stop_capture()
        self.selected_device_index = idx
        if was_capturing and idx is not None:
            QTimer.singleShot(200, self.start_capture)

    def start_capture(self):
        print(f"AVM DEBUG (start_capture): Called. is_capturing: {self.is_capturing}, selected_device_index: {self.selected_device_index}") # DIAGNOSTIC
        if self.is_capturing:
            print("AVM INFO (start_capture): Capture already in progress.")
            return False
        if self.selected_device_index is None:
            self.capture_error.emit("No audio device selected to start capture.")
            print("AVM ERROR (start_capture): Cannot start, no audio device selected.")
            return False

        selected_device_info_list = [dev for dev in self.devices_info_cache if dev['index'] == self.selected_device_index]
        if not selected_device_info_list:
            err_msg = f"Selected device index {self.selected_device_index} not found in current device cache."
            self.capture_error.emit(err_msg)
            print(f"AVM ERROR (start_capture): {err_msg}")
            return False

        device_info = selected_device_info_list[0]
        rate = int(device_info.get('default_sample_rate', 44100))
        channels = min(device_info.get('max_input_channels', 0), DEFAULT_CHANNELS)
        if channels == 0:
            err_msg = f"Device '{device_info['name']}' reports 0 input channels. Cannot capture."
            self.capture_error.emit(err_msg)
            print(f"AVM ERROR (start_capture): {err_msg}")
            return False

        print(f"AVM INFO (start_capture): Preparing: Device='{device_info['name']}', Index={self.selected_device_index}, Rate={rate}, Ch={channels}") # DIAGNOSTIC

        if self.audio_thread and self.audio_thread.isRunning():
            print("AVM WARN (start_capture): Old audio thread still running. Attempting stop again.")
            self.audio_thread.stop()
            if not self.audio_thread.wait(750):
                print("AVM WARN (start_capture): Old thread termination timed out.")
                self.audio_thread.terminate()
                self.audio_thread.wait()
            self.audio_thread = None

        print(f"AVM DEBUG (start_capture): Creating new AudioProcessingThread instance.") # DIAGNOSTIC
        self.audio_thread = AudioProcessingThread(
            device_index=self.selected_device_index, rate=rate, channels=channels,
            chunk_size=DEFAULT_CHUNK_SIZE, format_pa=DEFAULT_FORMAT, parent=self
        )
        self.audio_thread.fft_data_ready.connect(self._process_audio_data)
        self.audio_thread.error_occurred.connect(self._handle_audio_thread_error)
        self.audio_thread.finished.connect(self._on_audio_thread_finished)

        print(f"AVM DEBUG (start_capture): Attempting to start audio_thread...") # DIAGNOSTIC
        self.audio_thread.start()

        QTimer.singleShot(100, self._check_thread_started_status)
        return True


    def _check_thread_started_status(self):
        if self.audio_thread and self.audio_thread.isRunning():
            if not self.is_capturing:  # Only change state and emit if not already marked as capturing
                self.is_capturing = True
                print(
                    f"AVM INFO (_check_thread_started_status): Audio capture thread started successfully. self.is_capturing = {self.is_capturing}")
                self.capture_started_signal.emit()  # <<< EMIT NEW SIGNAL
            # else:
                # print("AVM DEBUG (_check_thread_started_status): Thread running, but already marked as capturing.")
        else:
            # If it was marked as capturing but thread isn't running (e.g. failed immediately)
            if self.is_capturing:
                self.is_capturing = False  # Correct the state

            device_name = "Unknown Device"
            if self.selected_device_index is not None:
                selected_device_info_list = [
                    dev for dev in self.devices_info_cache if dev['index'] == self.selected_device_index]
                if selected_device_info_list:
                    device_name = selected_device_info_list[0]['name']

            err_msg = f"Audio thread FAILED to start for device '{device_name}'."
            print(
                f"AVM ERROR (_check_thread_started_status): {err_msg} self.is_capturing = {self.is_capturing}")
            self.capture_error.emit(err_msg)
            # Note: capture_error will trigger MainWindow._handle_visualizer_capture_error,
            # which in turn ensures AVM.stop_capture() is called if needed, which then emits capture_stopped_signal.

            if self.audio_thread:
                try:
                    self.audio_thread.fft_data_ready.disconnect(
                        self._process_audio_data)
                except:
                    pass
                try:
                    self.audio_thread.error_occurred.disconnect(
                        self._handle_audio_thread_error)
                except:
                    pass
                try:
                    self.audio_thread.finished.disconnect(
                        self._on_audio_thread_finished)
                except:
                    pass
            self.audio_thread = None

# In class AudioVisualizerManager(QObject):

    def stop_capture(self):
        print(
            f"AVM DEBUG (stop_capture): Called. self.is_capturing (before stop): {self.is_capturing}, audio_thread exists: {self.audio_thread is not None}")
        # Check if audio_thread is not None before calling isRunning
        if self.audio_thread and self.audio_thread is not None:
            print(
                f"AVM DEBUG (stop_capture): audio_thread isRunning: {self.audio_thread.isRunning()}")

        # Store the state before we change it
        was_capturing_logically = self.is_capturing

        if not self.is_capturing and not (self.audio_thread and self.audio_thread is not None and self.audio_thread.isRunning()):
            print(
                "AVM INFO (stop_capture): Capture not in progress or thread already stopped.")
            self.is_capturing = False  # Ensure state is false
            if self.audio_thread and self.audio_thread is not None:
                try:
                     self.audio_thread.finished.disconnect(
                         self._on_audio_thread_finished)
                except:
                    pass
            self.audio_thread = None
            if was_capturing_logically:  # If we thought it was capturing but it wasn't, still emit stopped
                print(
                    "AVM DEBUG (stop_capture): Emitting capture_stopped_signal (was logically capturing).")
                self.capture_stopped_signal.emit()
            return

        if self.audio_thread and self.audio_thread is not None:
            print(f"AVM DEBUG (stop_capture): Calling audio_thread.stop()")
            self.audio_thread.stop()

            if not self.audio_thread.wait(1500):
                print(
                    "AVM WARN (stop_capture): Audio thread did not finish gracefully, terminating.")
                self.audio_thread.terminate()
                self.audio_thread.wait()
            else:
                print("AVM INFO (stop_capture): Audio thread finished gracefully.")

            try:
                self.audio_thread.fft_data_ready.disconnect(
                    self._process_audio_data)
            except:
                pass 
            try:
                self.audio_thread.error_occurred.disconnect(
                    self._handle_audio_thread_error)
            except:
                pass
            try:
                self.audio_thread.finished.disconnect(
                    self._on_audio_thread_finished)
            except:
                pass
            self.audio_thread = None

        self.is_capturing = False  # Set to false AFTER attempting to stop thread
        self._smoothed_band_powers = np.zeros(NUMBER_OF_BANDS)
        print(
            "AVM INFO (stop_capture): Audio capture stopped and thread resources released.")
        self.capture_stopped_signal.emit()  # <<< EMIT NEW SIGNAL

    def _on_audio_thread_finished(self):
        print(f"AVM INFO (_on_audio_thread_finished): AudioProcessingThread's 'finished' signal received.")
        self.is_capturing = False
        self.audio_thread = None


    def _handle_audio_thread_error(self, error_message: str):
        print(f"AVM Error from audio thread: {error_message}")
        # Emit the error message for MainWindow to display
        self.capture_error.emit(error_message)
        
        # If an error occurs in the thread, it should stop itself.
        # We call stop_capture() here to ensure manager state is consistent,
        # resources are cleaned, and capture_stopped_signal is emitted.
        # Check if it's already in the process of stopping to avoid recursion if stop_capture itself causes an error.
        if self.is_capturing or (self.audio_thread and self.audio_thread.isRunning()):
            print("AVM DEBUG (_handle_audio_thread_error): Calling stop_capture due to thread error.")
            self.stop_capture() # This will set self.is_capturing = False and emit capture_stopped_signal
        else:
            print("AVM DEBUG (_handle_audio_thread_error): Thread error received, but capture already seems stopped.")
            # Ensure state is false and signal is emitted if it wasn't already
            if self.is_capturing: # Should not happen if logic above is correct
                self.is_capturing = False
                self.capture_stopped_signal.emit()




    def _process_audio_data(self, fft_magnitudes: np.ndarray, rate: int, mono_chunk_size: int):
        # --- ADDED DIAGNOSTIC PRINTS AT THE START ---
        # print(f"AVM TRACE (_process_audio_data): ENTERED. self.is_capturing = {self.is_capturing}, self.current_visualization_mode = '{self.current_visualization_mode}'")
        # Optional: print raw fft_magnitudes characteristics if needed for deeper audio debug
        # if len(fft_magnitudes) > 0:
            # print(f"AVM TRACE (_process_audio_data): fft_magnitudes - shape: {fft_magnitudes.shape}, max: {np.max(fft_magnitudes):.2f}, mean: {np.mean(fft_magnitudes):.2f}")
        # --- END DIAGNOSTIC PRINTS ---

        if not self.is_capturing:
            # print("AVM TRACE (_process_audio_data): EXITING because not self.is_capturing.") # DIAGNOSTIC
            return

        # --- ADDED PRINT BEFORE IF/ELIF ---
        # print(f"AVM TRACE (_process_audio_data): Proceeding with mode: '{self.current_visualization_mode}'") # DIAGNOSTIC
        # --- END PRINT ---

        if self.current_visualization_mode == "classic_spectrum_bars": # Note: Ensure exact string match
            # print("AVM TRACE (_process_audio_data): Matched 'classic_spectrum_bars'") # DIAGNOSTIC
            band_powers_raw = self._calculate_n_band_powers( 
                fft_magnitudes, rate, mono_chunk_size, NUMBER_OF_BANDS)
            self._smoothed_band_powers = (self.smoothing_factor * band_powers_raw) + \
                                         ((1.0 - self.smoothing_factor) * self._smoothed_band_powers)
            pad_colors = self._map_spectrum_bars_to_pads(self._smoothed_band_powers)
            self.pad_data_ready.emit(pad_colors)

        elif self.current_visualization_mode == "pulse_wave_matrix":
            # print("AVM TRACE (_process_audio_data): Matched 'pulse_wave_matrix'") # DIAGNOSTIC
            overall_loudness = np.mean(fft_magnitudes) / (mono_chunk_size / 2) if mono_chunk_size > 0 else 0
            overall_loudness_norm = min(1.0, overall_loudness / 100.0) 
            pad_colors = self._map_pulse_wave_to_pads(overall_loudness_norm) 
            self.pad_data_ready.emit(pad_colors)

        elif self.current_visualization_mode == "dual_vu_spectrum": # Note: Ensure exact string match from UIManager
            # print("AVM TRACE (_process_audio_data): Matched 'dual_vu_spectrum'") # DIAGNOSTIC
            overall_loudness = np.mean(fft_magnitudes) / (mono_chunk_size / 2) if mono_chunk_size > 0 else 0
            overall_loudness_norm = min(1.0, overall_loudness / 100.0)
            temp_8_bands = self._calculate_n_band_powers(fft_magnitudes, rate, mono_chunk_size, 8)
            bass_approx = np.mean(temp_8_bands[0:3]) if len(temp_8_bands) >=3 else 0
            mid_approx = np.mean(temp_8_bands[3:6]) if len(temp_8_bands) >=6 else 0
            treble_approx = np.mean(temp_8_bands[6:8]) if len(temp_8_bands) >=8 else 0
            pad_colors = self._map_dual_vu_to_pads(overall_loudness_norm, overall_loudness_norm, bass_approx, mid_approx, treble_approx)
            self.pad_data_ready.emit(pad_colors)
        # else:
            # --- ADDED ELSE FOR UNMATCHED MODE ---
            # print(f"AVM WARN (_process_audio_data): Unknown or unhandled visualization mode: '{self.current_visualization_mode}'") # DIAGNOSTIC
            # --- END ADDED ELSE ---


    def _calculate_n_band_powers(self, fft_mags: np.ndarray, sr: int, fft_size: int, num_bands: int) -> np.ndarray:
        if len(fft_mags) == 0 or fft_size == 0 or sr == 0: return np.zeros(num_bands)
        freqs = np.fft.fftfreq(fft_size, 1.0/sr)[:fft_size // 2]
        if len(freqs) == 0: return np.zeros(num_bands)
        min_f, max_f = 20.0, min(sr / 2.0, 20000.0)
        if min_f >= max_f: return np.zeros(num_bands)
        edges = np.logspace(np.log10(min_f), np.log10(max_f), num_bands + 1)
        
        raw_band_powers_fft_avg = np.zeros(num_bands) 
        for i in range(num_bands):
            low_idx, high_idx = np.searchsorted(freqs, edges[i]), np.searchsorted(freqs, edges[i+1])
            if low_idx < high_idx and high_idx <= len(fft_mags): 
                avg_p = np.mean(fft_mags[low_idx:high_idx])
                raw_band_powers_fft_avg[i] = avg_p if not np.isnan(avg_p) else 0.0
            else: raw_band_powers_fft_avg[i] = 0.0
        
        # print(f"AVM DIAGNOSTIC (_calculate_n_band_powers): Raw Avg FFT Band Powers (before scaling/sensitivity): {raw_band_powers_fft_avg}")
        scaling_factor = 200000.0
        normalized_powers = raw_band_powers_fft_avg / scaling_factor 
        # print(f"AVM DIAGNOSTIC (_calculate_n_band_powers): Powers after scaling_factor: {normalized_powers}")
        normalized_powers *= (self.global_sensitivity * 2.0)
        # print(f"AVM DIAGNOSTIC (_calculate_n_band_powers): Powers after sensitivity ({self.global_sensitivity:.2f}): {normalized_powers}")
        return np.clip(normalized_powers, 0.0, 1.0)

    def _map_spectrum_bars_to_pads(self, band_powers: np.ndarray) -> list[str]:
        pad_colors_hex = ["#000000"] * 64
        num_bands_from_data = len(band_powers)
        bands_to_render = min(num_bands_from_data, NUMBER_OF_BANDS, 16)
        if bands_to_render == 0:
            return pad_colors_hex

        if not self.band_colors:
            operational_band_colors = DEFAULT_MANAGER_BAND_COLORS_QCOLOR
        else:
            operational_band_colors = self.band_colors

        cols_band, extra_cols = 16 // bands_to_render, 16 % bands_to_render
        curr_col_start = 0
        for i in range(bands_to_render):
            power = band_powers[i]
            base_color = operational_band_colors[i % len(operational_band_colors)]
            rows_light = min(3, int(power * 3.999))
            width = cols_band + (1 if i < extra_cols else 0)
            for col_off in range(width):
                col = curr_col_start + col_off
                if col >= 16:
                    break
                for r in range(4):
                    idx = r * 16 + col
                    if r <= rows_light:
                        h, s, _, a = base_color.getHsvF()
                        val_comp = 0.25 + (power * 0.75) if power > 0.01 else 0.0
                        final_val = min(1.0, max(0.0, val_comp))
                        if final_val < 0.25 and power > 0.01:
                            final_val = 0.25
                        pad_colors_hex[idx] = QColor.fromHsvF(
                            h, s, final_val, a).name() if final_val > 0 else "#000000"
                    else:
                        pad_colors_hex[idx] = "#000000"
            curr_col_start += width

        return pad_colors_hex

    def _map_pulse_wave_to_pads(self, loud_norm: float) -> list[str]:
        colors_hex = ["#000000"] * 64
        return colors_hex

    def _map_dual_vu_to_pads(self, l_norm: float, r_norm: float, bass: float, mid: float, treble: float) -> list[str]:
        colors_hex = ["#080808"] * 64
        return colors_hex

    def update_visualization_mode(self, mode_name: str):
        if self.current_visualization_mode == mode_name:
            return
        self.current_visualization_mode = mode_name
        self._smoothed_band_powers = np.zeros(NUMBER_OF_BANDS)
        self._apply_settings_for_current_mode()

    def update_band_color(self, band_idx: int, color: QColor):
        cache = self.all_mode_settings_cache.get(
            self.current_visualization_mode)
        if not cache or "band_colors" not in cache or not (0 <= band_idx < len(cache["band_colors"])):
            return
        cache["band_colors"][band_idx] = color.name()
        if self.current_visualization_mode == "Classic Spectrum Bars" and 0 <= band_idx < len(self.band_colors):
            self.band_colors[band_idx] = color
        self._save_all_mode_settings_to_persistence()

    def update_sensitivity(self, sens_val_mgr: float):
        cache = self.all_mode_settings_cache.get(
            self.current_visualization_mode)
        if not cache or "sensitivity" not in cache:
            return
        new_sens = max(0.0, float(sens_val_mgr))
        cache["sensitivity"] = new_sens
        if self.current_visualization_mode == "Classic Spectrum Bars":
            self.global_sensitivity = new_sens
        self._save_all_mode_settings_to_persistence()

    def update_smoothing(self, smooth_val_mgr: float):
        cache = self.all_mode_settings_cache.get(
            self.current_visualization_mode)
        if not cache or "smoothing" not in cache:
            return
        new_smooth = max(0.0, min(float(smooth_val_mgr), 0.99))
        cache["smoothing"] = new_smooth
        if self.current_visualization_mode == "Classic Spectrum Bars":
            self.smoothing_factor = new_smooth
        self._save_all_mode_settings_to_persistence()

    def on_application_exit(self):
        self.stop_capture()
        self._save_all_mode_settings_to_persistence()
        if self.p_audio_instance:
            try:
                self.p_audio_instance.terminate()
                self.p_audio_instance = None
            except Exception:
                pass