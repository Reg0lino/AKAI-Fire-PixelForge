# AKAI_Fire_RGB_Controller/features/screen_sampler_thread.py
import time
import sys
import mss
from PyQt6.QtCore import QThread, pyqtSignal, QMutex, QMutexLocker, QObject, QTimer
from PyQt6.QtWidgets import QApplication
from PIL import Image

from .screen_sampler_core import ScreenSamplerCore

class ScreenSamplerThread(QThread):
    pad_colors_sampled = pyqtSignal(list)
    processed_image_ready = pyqtSignal(Image.Image)
    error_occurred = pyqtSignal(str)

    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)
        self._is_running = False
        self._parameters_mutex = QMutex()
        self.monitor_capture_id_to_sample = 1
        self.region_rect_percentage = {'x': 0.4, 'y': 0.4, 'width': 0.2, 'height': 0.2}
        self.sampling_frequency_ms = 200
        self.adjustments = ScreenSamplerCore.DEFAULT_ADJUSTMENTS.copy()
        self.fullscreen_downscale_dimensions = ScreenSamplerCore.DEFAULT_FULLSCREEN_DOWNSCALE_DIMENSIONS
        self.sampling_mode = "grid"  # Add this line

    def run(self):
        print("ScreenSamplerThread: Thread started.")
        try:
            with mss.mss() as sct_instance:
                print("ScreenSamplerThread: mss instance created successfully.")
                while True:
                    with QMutexLocker(self._parameters_mutex):
                        if not self._is_running:
                            break
                        # Copy all parameters for this loop iteration
                        current_monitor_id = self.monitor_capture_id_to_sample
                        current_region_rect_perc = self.region_rect_percentage.copy()
                        current_frequency_ms = self.sampling_frequency_ms
                        current_adjustments = self.adjustments.copy()
                        current_mode = self.sampling_mode
                    start_time = time.perf_counter()
                    try:
                        pad_colors = None
                        preview_image = None
                        # --- NEW: Call the correct core function based on mode ---
                        if current_mode == "grid":
                            pad_colors, preview_image = ScreenSamplerCore.capture_and_grid_sample_colors(
                                sct_instance, current_monitor_id, current_region_rect_perc, current_adjustments
                            )
                        elif current_mode == "thumbnail":
                            pad_colors, preview_image = ScreenSamplerCore.capture_and_thumbnail_sample(
                                sct_instance, current_monitor_id, current_adjustments
                            )
                        elif current_mode == "palette":
                            pad_colors, preview_image = ScreenSamplerCore.capture_and_palette_sample(
                                sct_instance, current_monitor_id, current_adjustments
                            )
                        if pad_colors:
                            self.pad_colors_sampled.emit(pad_colors)
                        if preview_image:  # Only grid mode returns a useful preview
                            self.processed_image_ready.emit(preview_image)
                    except Exception as e_capture:
                        error_msg = f"Capture Core Error: {str(e_capture)[:200]}"
                        self.error_occurred.emit(error_msg)
                        self.msleep(500)
                    elapsed_time_ms = (time.perf_counter() - start_time) * 1000
                    sleep_duration_ms = max(
                        0, current_frequency_ms - elapsed_time_ms)
                    if sleep_duration_ms > 0:
                        self.msleep(int(sleep_duration_ms))
        except Exception as e_mss_init:
            errMsg = f"FATAL (ScreenSamplerThread): mss library init failed: {e_mss_init}"
            self.error_occurred.emit(errMsg)
            print(errMsg)
        finally:
            print("ScreenSamplerThread: Thread finished.")
            with QMutexLocker(self._parameters_mutex):
                self._is_running = False

    def start_sampling(self,
                        monitor_capture_id: int, region_rect_percentage: dict,
                        frequency_ms: int, sampling_mode: str,
                        adjustments: dict | None = None):
        with QMutexLocker(self._parameters_mutex):
            self.monitor_capture_id_to_sample = monitor_capture_id
            self.region_rect_percentage = region_rect_percentage.copy()
            self.sampling_frequency_ms = max(16, frequency_ms)
            self.sampling_mode = sampling_mode  # Store the mode
            self.adjustments = ScreenSamplerCore.DEFAULT_ADJUSTMENTS.copy()
            if adjustments:
                self.adjustments.update(adjustments)
            if not self._is_running:
                self._is_running = True
        if not self.isRunning():
            self.start()

    def stop_sampling(self, emit_status_on_finish: bool = True):
        # print(f"DEBUG Thread: stop_sampling() called. Setting self._is_running = False. Was: {self._is_running}") # Quieter
        with QMutexLocker(self._parameters_mutex):
            self._is_running = False
        # The thread's run() loop will see self._is_running is False and break, then the thread will finish.

if __name__ == '__main__':
    app = QApplication(sys.argv)
    print("ScreenSamplerThread: Main example for gridded sampling started.")
    initial_monitors = []
    try:
        with mss.mss() as sct_for_setup:
            initial_monitors = ScreenSamplerCore.get_available_monitors(sct_for_setup)
    except Exception as e_setup:
        print(f"Example: Failed to init mss: {e_setup}"); sys.exit(1)
    if not initial_monitors:
        print("Example: No monitors found."); sys.exit(1)
    target_monitor_id = initial_monitors[0]['id']
    print(f"Example: Targeting monitor mss ID: {target_monitor_id} ({initial_monitors[0]['name']})")
    sampler_thread = ScreenSamplerThread()

    def handle_pad_colors_test(colors_list: list):
        if colors_list and len(colors_list) == 64: # Assuming 64 pads
            print(f"Example (Thread): Got {len(colors_list)} pad colors. First: {colors_list[0]}, Last: {colors_list[-1]}")
        else:
            print(f"Example (Thread): Received invalid colors list length ({len(colors_list) if colors_list else 'None'})")

    def handle_image_test(p_img: Image.Image):
        print(f"Example (Thread): S/C/B Processed Full Image - Mode={p_img.mode}, Size={p_img.size}")
    sampler_thread.pad_colors_sampled.connect(handle_pad_colors_test)
    sampler_thread.processed_image_ready.connect(handle_image_test)
    sampler_thread.error_occurred.connect(lambda err: print(f"Example (Thread): Error - {err}"))
    initial_region = {'x': 0.25, 'y': 0.25, 'width': 0.5, 'height': 0.5}
    initial_adjustments = {'saturation': 1.8, 'contrast': 1.2, 'brightness': 1.0, 'hue_shift': 10}
    sampler_thread.start_sampling(target_monitor_id, initial_region, 200, initial_adjustments) # Sample every 200ms

    # Example of updating parameters while running
    def update_test_params():
        print("\nExample: Updating thread parameters...\n")
        new_adjustments = {'saturation': 0.5, 'contrast': 2.0, 'brightness': 1.1, 'hue_shift': -20}
        # Use start_sampling to update params and ensure it's running
        sampler_thread.start_sampling(target_monitor_id, initial_region, 100, new_adjustments) # Faster sampling
    QTimer.singleShot(2000, update_test_params)
    QTimer.singleShot(5000, sampler_thread.stop_sampling)
    QTimer.singleShot(5500, lambda: app.quit() if not sampler_thread.isRunning() else None)
    sys.exit(app.exec())