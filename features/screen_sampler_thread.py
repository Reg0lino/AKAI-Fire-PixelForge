# AKAI_Fire_RGB_Controller/features/screen_sampler_thread.py
import time
import mss 
from PyQt6.QtCore import QThread, pyqtSignal, QMutex, QMutexLocker, QObject
from PIL import Image 

from .screen_sampler_core import ScreenSamplerCore # Assuming core is in the same directory or path is set

class ScreenSamplerThread(QThread):
    # UPDATED SIGNAL: Emits list of 64 (r,g,b) tuples
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
        # fullscreen_downscale_dimensions is not directly used by grid sampler, but core might use it for preview
        self.fullscreen_downscale_dimensions = ScreenSamplerCore.DEFAULT_FULLSCREEN_DOWNSCALE_DIMENSIONS

    def run(self):
        print("ScreenSamplerThread: Thread started (for gridded sampling).")
        try:
            with mss.mss() as sct_instance:
                print("ScreenSamplerThread: mss instance created successfully.")
                while True:
                    current_monitor_id = 0 # Default init
                    with QMutexLocker(self._parameters_mutex):
                        # print(f"DEBUG Thread: run() loop check. self._is_running: {self._is_running}") # Can be very noisy
                        if not self._is_running: 
                            print(f"DEBUG Thread: run() loop - self._is_running is False, breaking loop.")
                            break 
                        current_monitor_id = self.monitor_capture_id_to_sample
                        current_region_rect_perc = self.region_rect_percentage.copy()
                        current_frequency_ms = self.sampling_frequency_ms
                        current_adjustments = self.adjustments.copy()
                    
                    start_time = time.perf_counter()
                    try:
                        # UPDATED: Call the new grid sampling method in Core
                        list_of_pad_colors, full_preview_image = ScreenSamplerCore.capture_and_grid_sample_colors(
                            sct_instance,
                            current_monitor_id,
                            current_region_rect_perc,
                            adjustments=current_adjustments
                            # fullscreen_downscale_dimensions is implicitly handled by core if needed for preview
                        )

                        if list_of_pad_colors:
                            self.pad_colors_sampled.emit(list_of_pad_colors) # Emit list
                        
                        if full_preview_image:
                            self.processed_image_ready.emit(full_preview_image) 
                        
                    except Exception as e_capture:
                        self.error_occurred.emit(f"Capture Core Error: {str(e_capture)[:200]}")
                        self.msleep(500) 
                    
                    elapsed_time_ms = (time.perf_counter() - start_time) * 1000
                    sleep_duration_ms = max(0, current_frequency_ms - elapsed_time_ms)
                    if sleep_duration_ms > 0: self.msleep(int(sleep_duration_ms))
        
        except Exception as e_mss_init:
            errMsg = f"FATAL: mss library init failed: {e_mss_init}"
            self.error_occurred.emit(errMsg); print(errMsg) 
        print("ScreenSamplerThread: Thread finished.")

    def start_sampling(self, 
                       monitor_capture_id: int, region_rect_percentage: dict, 
                       frequency_ms: int, adjustments: dict | None = None,
                       fullscreen_downscale: tuple[int, int] | None = None): # fs_downscale kept for consistency
        with QMutexLocker(self._parameters_mutex):
            self.monitor_capture_id_to_sample = monitor_capture_id
            self.region_rect_percentage = region_rect_percentage.copy()
            self.sampling_frequency_ms = max(16, frequency_ms)
            self.adjustments = ScreenSamplerCore.DEFAULT_ADJUSTMENTS.copy()
            if adjustments: self.adjustments.update(adjustments)
            if fullscreen_downscale: self.fullscreen_downscale_dimensions = fullscreen_downscale
            else: self.fullscreen_downscale_dimensions = ScreenSamplerCore.DEFAULT_FULLSCREEN_DOWNSCALE_DIMENSIONS
            print(f"DEBUG Thread: start_sampling() - setting self._is_running = True. Was: {self._is_running}")
            self._is_running = True
        if not self.isRunning(): self.start()

    def stop_sampling(self):
        print(f"DEBUG Thread: stop_sampling() - setting self._is_running = False. Was: {self._is_running}")
        with QMutexLocker(self._parameters_mutex): self._is_running = False

    def update_parameters(self, 
                          monitor_capture_id: int, region_rect_percentage: dict, 
                          frequency_ms: int, adjustments: dict | None = None,
                          fullscreen_downscale: tuple[int, int] | None = None):
        with QMutexLocker(self._parameters_mutex):
            self.monitor_capture_id_to_sample = monitor_capture_id
            self.region_rect_percentage = region_rect_percentage.copy()
            self.sampling_frequency_ms = max(16, frequency_ms)
            if adjustments: self.adjustments.update(adjustments)
            if fullscreen_downscale: self.fullscreen_downscale_dimensions = fullscreen_downscale
            # print(f"ScreenSamplerThread: Params updated for grid sampling.")


if __name__ == '__main__':
    from PyQt6.QtWidgets import QApplication
    from PyQt6.QtCore import QTimer 
    import sys

    app = QApplication(sys.argv)
    print("ScreenSamplerThread: Main example for gridded sampling started.")
    
    initial_monitors = []
    try:
        with mss.mss() as sct_for_setup: initial_monitors = ScreenSamplerCore.get_available_monitors(sct_for_setup)
    except Exception as e_setup: print(f"Example: Failed to init mss: {e_setup}"); sys.exit(1)
    if not initial_monitors: print("Example: No monitors found."); sys.exit(1)
        
    target_monitor_id = initial_monitors[0]['id'] 
    print(f"Example: Targeting monitor mss ID: {target_monitor_id} ({initial_monitors[0]['name']})")
    sampler_thread = ScreenSamplerThread()

    def handle_pad_colors_test(colors_list: list):
        if colors_list and len(colors_list) == 64:
            print(f"Example (Thread): Got {len(colors_list)} pad colors. First: {colors_list[0]}, Last: {colors_list[63]}")
        else:
            print(f"Example (Thread): Received invalid colors list or None: {colors_list}")

    def handle_image_test(p_img: Image.Image):
        print(f"Example (Thread): S/C/B Processed Full Image - Mode={p_img.mode}, Size={p_img.size}")

    sampler_thread.pad_colors_sampled.connect(handle_pad_colors_test) # Connect to new signal
    sampler_thread.processed_image_ready.connect(handle_image_test)
    sampler_thread.error_occurred.connect(lambda err: print(f"Example (Thread): Error - {err}"))

    initial_region = {'x': 0.25, 'y': 0.25, 'width': 0.5, 'height': 0.5} 
    initial_adjustments = {'saturation': 1.0, 'contrast': 1.0, 'brightness': 1.0, 'hue_shift': 0}
    sampler_thread.start_sampling(target_monitor_id, initial_region, 500, initial_adjustments)
    
    QTimer.singleShot(3000, lambda: sampler_thread.stop_sampling())
    QTimer.singleShot(3500, lambda: app.quit() if not sampler_thread.isRunning() else None)
    sys.exit(app.exec())
