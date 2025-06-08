# AKAI_Fire_RGB_Controller/managers/audio_visualizer_manager.py

import pyaudiowpatch as pyaudio
import numpy as np
import time
import json
import os
from PyQt6.QtCore import QObject, pyqtSignal, QTimer, QThread, Qt
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
        
        # Operational parameters for Classic Spectrum Bars
        self.band_colors: list[QColor] = []
        self.global_sensitivity: float = DEFAULT_MANAGER_SENSITIVITY
        self.smoothing_factor: float = DEFAULT_MANAGER_SMOOTHING
        self.classic_bars_grow_downwards: bool = False
        self._smoothed_band_powers = np.zeros(NUMBER_OF_BANDS)

        # Operational parameters for Pulse Wave
        self.pulse_wave_color: QColor = QColor("cyan")
        self.pulse_wave_speed_factor: float = 0.5 
        self.pulse_wave_brightness_sensitivity: float = 1.0
        self.pulse_current_column_index: int = 0
        self.pulse_last_update_time: float = time.monotonic()
        self.pulse_time_accumulator: float = 0.0
        
        # --- ADDED: Operational parameters for Dual VU ---
        self.dvu_low_color: QColor = QColor(Qt.GlobalColor.green)
        self.dvu_mid_color: QColor = QColor(Qt.GlobalColor.yellow)
        self.dvu_high_color: QColor = QColor(Qt.GlobalColor.red)
        self.dvu_threshold_mid_factor: float = 0.60 # Manager scale 0.0-1.0
        self.dvu_threshold_high_factor: float = 0.85 # Manager scale 0.0-1.0
        self.dvu_falloff_speed_factor: float = 0.5 # Manager scale 0.0-1.0 (higher = faster falloff)
        
        # State for VU meters (mono-driven for now, so one value)
        self.dvu_current_level: float = 0.0 # Smoothed VU level (0.0-1.0)
        # (Spectrum part operational parameters for this mode will be added later)
        # --- END ADD ---
        
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

# In class AudioVisualizerManager:

    def _load_all_mode_settings_from_persistence(self) -> dict:
        filepath = self._get_main_settings_filepath()
        default_settings_structure = {
            "classic_spectrum_bars": {
                "band_colors": [c.name() for c in DEFAULT_MANAGER_BAND_COLORS_QCOLOR],
                "sensitivity": DEFAULT_MANAGER_SENSITIVITY,
                "smoothing": DEFAULT_MANAGER_SMOOTHING,
                "grow_downwards": False
            },
            "pulse_wave_matrix": {
                "color": QColor("cyan").name(),
                "speed": 0.5,  # Manager scale
                "brightness_sensitivity": 1.0  # Manager scale
            },
            "dual_vu_spectrum": {  # ADDED Default structure for Dual VU
                "vu_low_color": QColor(Qt.GlobalColor.green).name(),
                "vu_mid_color": QColor(Qt.GlobalColor.yellow).name(),
                "vu_high_color": QColor(Qt.GlobalColor.red).name(),
                "vu_threshold_mid": 0.60,       # Manager scale (0.0-1.0)
                "vu_threshold_high": 0.85,      # Manager scale (0.0-1.0)
                "vu_falloff_speed": 0.5         # Manager scale (0.0-1.0)
                # Spectrum part settings for this mode will be added later
            }
        }

        if os.path.exists(filepath):
            try:
                with open(filepath, 'r') as f:
                    loaded_settings = json.load(f)
                if isinstance(loaded_settings, dict):
                    for mode_key, default_mode_settings in default_settings_structure.items():
                        if mode_key not in loaded_settings:
                            loaded_settings[mode_key] = default_mode_settings.copy(
                            )
                        else:
                            for sub_key, default_sub_value in default_mode_settings.items():
                                if sub_key not in loaded_settings[mode_key]:
                                    loaded_settings[mode_key][sub_key] = default_sub_value
                    return loaded_settings
                else:
                    print(
                        f"AVM WARN: visualizer_main_settings.json is not a valid dictionary. Using full defaults.")
            except Exception as e:
                print(
                    f"AVM WARN: Error loading visualizer_main_settings.json: {e}. Using full defaults.")

        return {k: v.copy() for k, v in default_settings_structure.items()}

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
        for mode_key, dialog_mode_settings in new_settings_from_dialog.items():
            if not isinstance(dialog_mode_settings, dict): continue
            if mode_key not in self.all_mode_settings_cache:
                self.all_mode_settings_cache[mode_key] = {}

            cache_for_mode = self.all_mode_settings_cache[mode_key]
            
            if mode_key == "classic_spectrum_bars":
                if "band_colors" in dialog_mode_settings:
                    cache_for_mode["band_colors"] = list(dialog_mode_settings["band_colors"])
                if "sensitivity" in dialog_mode_settings: # UI 0-100 to manager 0.0-2.0
                    cache_for_mode["sensitivity"] = dialog_mode_settings["sensitivity"] / 50.0
                if "smoothing" in dialog_mode_settings: # UI 0-99 to manager 0.0-0.99
                    cache_for_mode["smoothing"] = dialog_mode_settings["smoothing"] / 100.0
                if "grow_downwards" in dialog_mode_settings:
                    cache_for_mode["grow_downwards"] = dialog_mode_settings["grow_downwards"]
                else:
                    cache_for_mode.setdefault("grow_downwards", False)
            
            elif mode_key == "pulse_wave_matrix":
                if "color" in dialog_mode_settings:
                    cache_for_mode["color"] = dialog_mode_settings["color"]
                if "speed" in dialog_mode_settings: # UI 0-100 to manager 0.0-1.0
                    cache_for_mode["speed"] = dialog_mode_settings["speed"] / 100.0
                if "brightness_sensitivity" in dialog_mode_settings: # UI 0-100 to manager 0.0-2.0
                    cache_for_mode["brightness_sensitivity"] = dialog_mode_settings["brightness_sensitivity"] / 50.0
            
            # --- ADDED: Handle Dual VU Settings ---
            elif mode_key == "dual_vu_spectrum":
                if "vu_low_color" in dialog_mode_settings:
                    cache_for_mode["vu_low_color"] = dialog_mode_settings["vu_low_color"]
                if "vu_mid_color" in dialog_mode_settings:
                    cache_for_mode["vu_mid_color"] = dialog_mode_settings["vu_mid_color"]
                if "vu_high_color" in dialog_mode_settings:
                    cache_for_mode["vu_high_color"] = dialog_mode_settings["vu_high_color"]
                
                if "vu_threshold_mid" in dialog_mode_settings: # UI 0-100 (%) to manager 0.0-1.0
                    cache_for_mode["vu_threshold_mid"] = dialog_mode_settings["vu_threshold_mid"] / 100.0
                if "vu_threshold_high" in dialog_mode_settings: # UI 0-100 (%) to manager 0.0-1.0
                    cache_for_mode["vu_threshold_high"] = dialog_mode_settings["vu_threshold_high"] / 100.0
                
                if "vu_falloff_speed" in dialog_mode_settings: # UI 0-100 to manager 0.0-1.0
                    # Higher UI value means faster falloff.
                    # We can map this to a factor that determines how much the level drops per update.
                    # For now, let's store it as 0.0 (slow falloff) to 1.0 (fast falloff).
                    cache_for_mode["vu_falloff_speed"] = dialog_mode_settings["vu_falloff_speed"] / 100.0
                # Spectrum part settings for this mode will be added later
            # --- END ADD ---

            else: # Fallback for unhandled modes
                for key, value in dialog_mode_settings.items():
                    cache_for_mode[key] = value 

        self._apply_settings_for_current_mode()
        self._save_all_mode_settings_to_persistence()

# In class AudioVisualizerManager:

    def _apply_settings_for_current_mode(self):
        current_mode_key_to_check = self.current_visualization_mode
        mode_settings = self.all_mode_settings_cache.get(
            current_mode_key_to_check)

        if not mode_settings:
            print(
                f"AVM WARN: No settings in cache for '{current_mode_key_to_check}'. Using fallbacks.")
            # Fallbacks for Classic Spectrum Bars
            self.band_colors = list(DEFAULT_MANAGER_BAND_COLORS_QCOLOR)
            self.global_sensitivity = DEFAULT_MANAGER_SENSITIVITY
            self.smoothing_factor = DEFAULT_MANAGER_SMOOTHING
            self.classic_bars_grow_downwards = False
            # Fallbacks for Pulse Wave
            self.pulse_wave_color = QColor("cyan")
            self.pulse_wave_speed_factor = 0.5
            self.pulse_wave_brightness_sensitivity = 1.0
            # --- ADDED: Fallbacks for Dual VU ---
            self.dvu_low_color = QColor(Qt.GlobalColor.green)
            self.dvu_mid_color = QColor(Qt.GlobalColor.yellow)
            self.dvu_high_color = QColor(Qt.GlobalColor.red)
            self.dvu_threshold_mid_factor = 0.60
            self.dvu_threshold_high_factor = 0.85
            self.dvu_falloff_speed_factor = 0.5
            self.dvu_current_level = 0.0  # Reset state
            # --- END ADD ---
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
            self.classic_bars_grow_downwards = mode_settings.get(
                "grow_downwards", False)

        elif self.current_visualization_mode == "pulse_wave_matrix":
            self.pulse_wave_color = QColor(
                mode_settings.get("color", QColor("cyan").name()))
            self.pulse_wave_speed_factor = mode_settings.get("speed", 0.5)
            self.pulse_wave_brightness_sensitivity = mode_settings.get(
                "brightness_sensitivity", 1.0)
            self.pulse_current_column_index = 0
            self.pulse_last_update_time = time.monotonic()
            self.pulse_time_accumulator = 0.0

        # --- ADDED: Apply Dual VU Settings ---
        elif self.current_visualization_mode == "dual_vu_spectrum":
            self.dvu_low_color = QColor(mode_settings.get(
                "vu_low_color", QColor(Qt.GlobalColor.green).name()))
            self.dvu_mid_color = QColor(mode_settings.get(
                "vu_mid_color", QColor(Qt.GlobalColor.yellow).name()))
            self.dvu_high_color = QColor(mode_settings.get(
                "vu_high_color", QColor(Qt.GlobalColor.red).name()))
            self.dvu_threshold_mid_factor = mode_settings.get(
                "vu_threshold_mid", 0.60)
            self.dvu_threshold_high_factor = mode_settings.get(
                "vu_threshold_high", 0.85)
            self.dvu_falloff_speed_factor = mode_settings.get(
                "vu_falloff_speed", 0.5)
            self.dvu_current_level = 0.0  # Reset VU level state when settings change
            print(
                f"AVM DEBUG (_apply_settings_for_current_mode): Dual VU operational settings applied.")
        # --- END ADD ---

        # Add other modes as needed


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
        if not self.is_capturing:
            return

        if self.current_visualization_mode == "classic_spectrum_bars":
            band_powers_raw = self._calculate_n_band_powers( 
                fft_magnitudes, rate, mono_chunk_size, NUMBER_OF_BANDS)
            self._smoothed_band_powers = (self.smoothing_factor * band_powers_raw) + \
                                         ((1.0 - self.smoothing_factor) * self._smoothed_band_powers)
            pad_colors = self._map_spectrum_bars_to_pads(self._smoothed_band_powers)
            self.pad_data_ready.emit(pad_colors)

        elif self.current_visualization_mode == "pulse_wave_matrix":
            if mono_chunk_size > 0 and len(fft_magnitudes) > 0:
                loudness_scaling_factor = 20000.0 
                overall_loudness = np.mean(fft_magnitudes) / loudness_scaling_factor
            else:
                overall_loudness = 0.0
            overall_loudness_norm = min(1.0, max(0.0, overall_loudness / 1.0)) 
            pad_colors = self._map_pulse_wave_to_pads(overall_loudness_norm) 
            self.pad_data_ready.emit(pad_colors)

        elif self.current_visualization_mode == "dual_vu_spectrum":
            # Calculate overall loudness (simple average for now)
            if mono_chunk_size > 0 and len(fft_magnitudes) > 0:
                # This scaling factor might need to be different from pulse wave's
                # or spectrum bar's internal scaling. Let's use a common approach for now.
                loudness_scaling_factor_vu = 20000.0 # Tunable
                overall_loudness_raw = np.mean(fft_magnitudes) / loudness_scaling_factor_vu
            else:
                overall_loudness_raw = 0.0
            
            # Normalize loudness for VU meter (0.0 to 1.0)
            # The '1.0' divisor here means overall_loudness_raw is expected to be around 0-1.
            # Adjust if raw values are much larger.
            vu_level_input = min(1.0, max(0.0, overall_loudness_raw / 1.0)) 

            # For Phase 1, we don't have the central spectrum yet, so pass None or empty array
            # Later, we'll calculate spectrum_band_powers here for the central part.
            # For now, let's pass a dummy array for spectrum_band_powers if the map function expects it.
            # If _map_dual_vu_to_pads will only handle VU for now, this can be simpler.
            # Let's assume _map_dual_vu_to_pads will primarily use vu_level_input for now.
            
            # For the eventual spectrum part (5 bands):
            # num_spectrum_bands_for_dvu = 5
            # spectrum_band_powers = self._calculate_n_band_powers(
            #     fft_magnitudes, rate, mono_chunk_size, num_spectrum_bands_for_dvu
            # )
            # For now, as spectrum part is not drawn:
            spectrum_band_powers = np.array([]) # Empty for now

            pad_colors = self._map_dual_vu_to_pads(vu_level_input, spectrum_band_powers)
            self.pad_data_ready.emit(pad_colors)



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

# In class AudioVisualizerManager:

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

        cols_per_band, extra_cols = divmod(16, bands_to_render)

        current_col_start_on_grid = 0
        for i in range(bands_to_render):
            power = band_powers[i]
            base_color = operational_band_colors[i % len(
                operational_band_colors)]

            # --- MODIFIED rows_to_light_count calculation ---
            # If power is 1.0, we want 4 rows.
            # If power is >= 0.75, effectively 4 rows.
            # If power is >= 0.50 and < 0.75, effectively 3 rows.
            # If power is >= 0.25 and < 0.50, effectively 2 rows.
            # If power is > 0.00 and < 0.25, effectively 1 row.
            if power >= 0.999:  # Treat as full power if extremely close to 1.0
                rows_to_light_count = 4
            else:
                # power * 4 will give a float from 0.0 to almost 4.0
                # Add a small epsilon to handle floating point inaccuracies near integers
                # then int() will truncate. min(4,...) ensures it's capped.
                rows_to_light_count = min(4, int(power * 4.0 + 0.0001))
            # --- END MODIFICATION ---

            current_band_width_on_grid = cols_per_band + \
                (1 if i < extra_cols else 0)

            for col_offset_within_band in range(current_band_width_on_grid):
                actual_col_on_grid = current_col_start_on_grid + col_offset_within_band
                if actual_col_on_grid >= 16:
                    continue

                for r_gui in range(4):
                    pad_1d_index = r_gui * 16 + actual_col_on_grid
                    is_lit_this_segment = False

                    if self.classic_bars_grow_downwards:
                        if r_gui < rows_to_light_count:
                            is_lit_this_segment = True
                    else:
                        if r_gui >= (4 - rows_to_light_count):
                            is_lit_this_segment = True

                    if is_lit_this_segment:
                        h, s, _, a = base_color.getHsvF()
                        val_comp = 0.25 + \
                            (power * 0.75) if power > 0.01 else 0.0
                        final_val = min(1.0, max(0.0, val_comp))
                        if final_val < 0.25 and power > 0.01:
                            final_val = 0.25

                        pad_colors_hex[pad_1d_index] = QColor.fromHsvF(
                            h, s, final_val, a).name() if final_val > 0 else "#000000"
                    else:
                        pad_colors_hex[pad_1d_index] = "#000000"

            current_col_start_on_grid += current_band_width_on_grid

        # --- TEMPORARY DEBUG for 4th row issue ---
        # (You can re-enable this if the issue persists after the change)
        # if bands_to_render > 0 and band_powers[0] > 0.95:
        #     debug_power_band0 = band_powers[0]
        #     if debug_power_band0 >= 0.999: debug_rows_calc = 4
        #     else: debug_rows_calc = min(4, int(debug_power_band0 * 4.0 + 0.0001))
        #     print(f"DEBUG AVM (PostFix): High power for band 0: {debug_power_band0:.4f}. rows_to_light_count (for band 0): {debug_rows_calc}")
        #     first_band_first_col_idx_top = 0
        #     first_band_first_col_idx_bottom = 3*16 + 0
        #     print(f"  Pad 0 (top): {pad_colors_hex[first_band_first_col_idx_top]}, Pad 48 (bottom): {pad_colors_hex[first_band_first_col_idx_bottom]}")
        # --- END TEMPORARY DEBUG ---

        return pad_colors_hex


    # --- MODIFIED: update_band_color (if it exists, ensure it handles the new setting if relevant) ---
    # This method seems to be for a different context (direct updates from a non-dialog source).
    # For 'grow_downwards', it's part of the profile/general settings, not per-band.
    # So, no changes needed here for 'grow_downwards'.

    def _map_pulse_wave_to_pads(self, loudness_norm: float) -> list[str]:
        pad_colors_hex = ["#000000"] * 64  # Start with all pads black

        # --- Speed Control ---
        # self.pulse_wave_speed_factor is 0.0 (slowest) to 1.0 (fastest)
        # Map this to a delay between column advances.
        # Example: max_delay = 0.5s (for speed 0), min_delay = 0.02s (for speed 1.0)
        min_update_delay_s = 0.02  # Corresponds to ~50 FPS updates if pulse moves every frame
        max_update_delay_s = 0.5
        # Inverted relationship: higher speed_factor means lower delay
        current_update_target_delay_s = max_update_delay_s - \
            (self.pulse_wave_speed_factor * (max_update_delay_s - min_update_delay_s))

        current_time = time.monotonic()
        delta_time = current_time - self.pulse_last_update_time
        self.pulse_time_accumulator += delta_time
        self.pulse_last_update_time = current_time

        if self.pulse_time_accumulator >= current_update_target_delay_s:
            self.pulse_current_column_index = (
                self.pulse_current_column_index + 1) % 16  # Cycle through 0-15
            # Subtract consumed time, keep remainder
            self.pulse_time_accumulator -= current_update_target_delay_s

        # --- Brightness Modulation ---
        # self.pulse_wave_brightness_sensitivity is e.g., 0.0 (no reaction) to 2.0 (strong reaction)
        # loudness_norm is 0.0 to 1.0
        effective_brightness = loudness_norm * self.pulse_wave_brightness_sensitivity
        effective_brightness = min(
            1.0, max(0.0, effective_brightness))  # Clamp to 0.0-1.0

        # Get base color and apply brightness
        base_h, base_s, _, base_a = self.pulse_wave_color.getHsvF()

        # Ensure a minimum visibility if brightness is very low but non-zero
        # And scale base_v by effective_brightness
        # Let's make it so effective_brightness directly scales the color's original value.
        # If the base color is already dim, high effective_brightness won't make it super bright.
        # We want effective_brightness to scale towards the QColor's V.
        original_v = self.pulse_wave_color.valueF()
        final_v = original_v * effective_brightness

        # A very dim pulse might be hard to see. Ensure a minimum visibility.
        min_pulse_v_if_active = 0.1  # If brightness > 0, ensure at least this value
        if effective_brightness > 0.01 and final_v < min_pulse_v_if_active:
            final_v = min_pulse_v_if_active

        final_v = min(1.0, max(0.0, final_v))  # Clamp final value

        pulse_final_color_hex = QColor.fromHsvF(
            base_h, base_s, final_v, base_a).name() if final_v > 0.001 else "#000000"

        # Light up the current column
        # For Phase 1, pulse width is 1 column
        target_col = self.pulse_current_column_index
        for r in range(4):  # All 4 rows in that column
            pad_1d_index = r * 16 + target_col
            pad_colors_hex[pad_1d_index] = pulse_final_color_hex

        return pad_colors_hex



    def _map_dual_vu_to_pads(self, vu_level_input: float, spectrum_band_powers: np.ndarray) -> list[str]:
        pad_colors_hex = ["#000000"] * 64  # Initialize all pads to black

        # --- VU Meter Logic (Mono-driven for now) ---
        # vu_level_input is normalized 0.0 to 1.0

        # Apply falloff/smoothing to the VU level
        # self.dvu_falloff_speed_factor: 0.0 (slow) to 1.0 (fast)
        # A simple linear interpolation for smoothing/falloff:
        falloff_rate = (self.dvu_falloff_speed_factor * 0.2) + 0.01 # Map 0-1 to e.g. 0.01-0.21
                                                                # Higher falloff_rate means faster drop
        
        if vu_level_input > self.dvu_current_level:
            # Rise quickly, or with some attack smoothing if desired later
            self.dvu_current_level = vu_level_input 
        else:
            # Falloff
            self.dvu_current_level -= falloff_rate
            if self.dvu_current_level < 0:
                self.dvu_current_level = 0.0
        
        # Ensure it doesn't exceed the input if input suddenly drops low after being high
        if self.dvu_current_level < vu_level_input and vu_level_input - self.dvu_current_level > 0.1: # If input is significantly higher
             pass # Allow it to catch up if input is much higher
        elif self.dvu_current_level > vu_level_input : # Only apply falloff if current is higher than input
             pass
        else: # If current is lower than input, but not by much, let it rise to input
             self.dvu_current_level = vu_level_input


        # Define VU meter layout (Example: 2 VUs, each 3 cols wide, 4 rows high)
        # Left VU: cols 0, 1, 2. Right VU: cols 13, 14, 15
        vu_cols_left = [0, 1, 2]
        vu_cols_right = [13, 14, 15]
        vu_height_rows = 4 # Each VU uses 4 rows

        # Calculate number of segments to light for each VU (0 to 12 for a 3x4 VU)
        num_segments_total = len(vu_cols_left) * vu_height_rows # e.g., 3*4 = 12 segments
        segments_to_light = int(round(self.dvu_current_level * num_segments_total))

        vu_pad_tuples = [] # Store (col, row_gui) tuples for lit VU segments

        # Determine lit segments for Left VU (growing upwards)
        # Segments are numbered 0 (bottom-left of VU) to 11 (top-left of VU, then next col, etc.)
        segment_counter = 0
        for r_vu_internal in range(vu_height_rows): # 0,1,2,3 (bottom to top for VU logic)
            for c_vu_internal in range(len(vu_cols_left)): # 0,1,2 (left to right within VU block)
                if segment_counter < segments_to_light:
                    gui_row = (vu_height_rows - 1) - r_vu_internal # Map to GUI row (3 down to 0)
                    gui_col_left = vu_cols_left[c_vu_internal]
                    gui_col_right = vu_cols_right[c_vu_internal]
                    vu_pad_tuples.append({'col': gui_col_left, 'row_gui': gui_row, 'segment_prop': (segment_counter + 1) / num_segments_total})
                    vu_pad_tuples.append({'col': gui_col_right, 'row_gui': gui_row, 'segment_prop': (segment_counter + 1) / num_segments_total})
                segment_counter += 1
        
        # Color the VU segments
        for pad_info in vu_pad_tuples:
            col = pad_info['col']
            row_gui = pad_info['row_gui']
            segment_proportion = pad_info['segment_prop'] # How far up the VU this segment is (0.0 to 1.0)
            pad_1d_index = row_gui * 16 + col
            
            chosen_color = self.dvu_low_color
            if segment_proportion > self.dvu_threshold_mid_factor:
                chosen_color = self.dvu_mid_color
            if segment_proportion > self.dvu_threshold_high_factor:
                chosen_color = self.dvu_high_color
            
            # For now, full brightness for lit segments. Brightness modulation can be added later.
            # Or, use self.dvu_current_level to modulate brightness of all lit segments.
            h_vu, s_vu, _, a_vu = chosen_color.getHsvF()
            # Simple brightness: use the current VU level for brightness of all lit segments
            v_vu_mod = self.dvu_current_level 
            # Ensure minimum brightness if lit
            if v_vu_mod > 0.01 and v_vu_mod < 0.2: v_vu_mod = 0.2
            v_vu_mod = min(1.0, max(0.0, v_vu_mod * chosen_color.valueF())) # Scale original value

            pad_colors_hex[pad_1d_index] = QColor.fromHsvF(h_vu, s_vu, v_vu_mod, a_vu).name() if v_vu_mod > 0.001 else "#000000"


        # --- Central Spectrum Logic (Placeholder for Phase 2) ---
        # if spectrum_band_powers.any(): # Check if we have spectrum data
        #     num_spec_bands_to_draw = 5
        #     spec_cols_start = 3
        #     spec_cols_width_total = 10 # Cols 3-12
        #     cols_per_spec_band = spec_cols_width_total // num_spec_bands_to_draw # Should be 2

        #     for i in range(min(len(spectrum_band_powers), num_spec_bands_to_draw)):
        #         power = spectrum_band_powers[i]
        #         # ... similar logic to _map_spectrum_bars_to_pads ...
        #         # ... adapting for different number of rows, column start, and colors ...
        #         pass

        return pad_colors_hex


    def update_visualization_mode(self, mode_name: str):
        if self.current_visualization_mode == mode_name:
            return
        self.current_visualization_mode = mode_name
        self._smoothed_band_powers = np.zeros(NUMBER_OF_BANDS)
        self._apply_settings_for_current_mode()

    def update_band_color(self, band_idx: int, color: QColor):
        # This method updates the "band_colors" list in the cache for the current mode.
        # The "grow_downwards" setting is a separate boolean, not part of "band_colors".
        cache = self.all_mode_settings_cache.get(
            self.current_visualization_mode)
        if not cache or "band_colors" not in cache or not (0 <= band_idx < len(cache["band_colors"])):
            return

        cache["band_colors"][band_idx] = color.name()

        # If the current mode IS classic_spectrum_bars, also update the operational self.band_colors
        if self.current_visualization_mode == "classic_spectrum_bars" and \
           hasattr(self, 'band_colors') and 0 <= band_idx < len(self.band_colors):
            self.band_colors[band_idx] = color

        self._save_all_mode_settings_to_persistence()

    # --- MODIFIED: update_sensitivity (no changes needed for 'grow_downwards') ---
    # sens_val_mgr is manager scale (0.0-2.0)
    def update_sensitivity(self, sens_val_mgr: float):
        cache = self.all_mode_settings_cache.get(
            self.current_visualization_mode)
        if not cache or "sensitivity" not in cache:
            return

        # Ensure it's a float and non-negative
        new_sens = max(0.0, float(sens_val_mgr))
        cache["sensitivity"] = new_sens

        if self.current_visualization_mode == "classic_spectrum_bars":
            self.global_sensitivity = new_sens

        self._save_all_mode_settings_to_persistence()

    # --- MODIFIED: update_smoothing (no changes needed for 'grow_downwards') ---
    # smooth_val_mgr is manager scale (0.0-0.99)
    def update_smoothing(self, smooth_val_mgr: float):
        cache = self.all_mode_settings_cache.get(
            self.current_visualization_mode)
        if not cache or "smoothing" not in cache:
            return

        new_smooth = max(0.0, min(float(smooth_val_mgr), 0.99)
                         )  # Clamp to 0.0-0.99
        cache["smoothing"] = new_smooth

        if self.current_visualization_mode == "classic_spectrum_bars":
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