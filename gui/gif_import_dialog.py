# AKAI_Fire_PixelForge/gui/gif_import_dialog.py
import sys
import os
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QGroupBox, QWidget,
    QFileDialog, QProgressBar, QDialogButtonBox, QSizePolicy, QSlider, QCheckBox, QComboBox, QSpacerItem, QMessageBox, QApplication
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize, QTimer, QUrl, QTemporaryFile
from PyQt6.QtGui import QImage, QPixmap, QFont, QDesktopServices
from PIL import Image, ImageSequence, ImageEnhance, ImageColor, ImageDraw
from PIL.ImageQt import ImageQt
from .gif_region_selector import GifRegionSelectorLabel
from .pad_preview_widget import PadPreviewWidget
from .gif_player_dialog import GifPlayerDialog
import json
import requests  
# Import the new GIF Processing Engine
try:
    from features.gif_processing_engine import GifProcessingEngine, NUM_GRID_ROWS, NUM_GRID_COLS
except ImportError as e:
    print(
        f"GifImportDialog WARNING: Could not import GifProcessingEngine: {e}. GIF import will be non-functional.")

    class GifProcessingEngine:  # Placeholder for safety
        def __init__(self): pass
        def load_gif_from_source(
            self, src): raise Exception("Engine not loaded")
        def get_first_frame_pil(self): return None
        def get_original_gif_info(self): return {
            'frames': 0, 'width': 0, 'height': 0, 'loop': 0, 'avg_delay_ms': 0, 'fps': 0}
        def process_frames_for_pads(self, region, adjustments): return []
    NUM_GRID_ROWS = 4
    NUM_GRID_COLS = 16

# --- Re-use Slider Constants from capture_preview_dialog.py ---
SLIDER_MIN_FACTOR_VAL = 0
SLIDER_MAX_FACTOR_VAL = 400
SLIDER_MIN_HUE = -180
SLIDER_MAX_HUE = 180
DEFAULT_BRIGHTNESS_FACTOR = 1.0
DEFAULT_SATURATION_FACTOR = 1.75
DEFAULT_CONTRAST_FACTOR = 1.0
DEFAULT_HUE_SHIFT = 0

MIN_DIALOG_HEIGHT = 810 # <-- HEIGHT VARIABLE

class GifImportDialog(QDialog):
    # processed_frames_data, delay_ms, sequence_name
    preview_pads_updated = pyqtSignal(list)  # Emits a list of 64 hex colors
    gif_import_requested = pyqtSignal(list, int, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("📥 Import GIF Animation")
        self.setMinimumSize(950, 780)
        # --- PATH MANAGEMENT (RELIABLE VERSION) ---
        self.config_file_path = self._get_user_config_path(
            'gif_import_settings.json')
        self.last_used_browse_path = self._load_last_path()
        # --- Use the new helper to get the correct base path ---
        user_presets_base = self._get_user_documents_path()
        self.web_cache_dir = os.path.join(user_presets_base, "WebCache")
        os.makedirs(self.web_cache_dir, exist_ok=True)
        self.temp_file_path = None
        self.gif_engine = GifProcessingEngine()
        self.original_pil_frames: list[Image.Image] = []
        self.preview_pil_frames: list[Image.Image] = []
        self.processed_preview_frames: list[list[str]] = []
        self.current_gif_frame_delays_ms: list[int] = []
        self.current_preview_frame_index = 0
        self.current_preview_timer = QTimer(self)
        self.current_preview_timer.timeout.connect(self._update_preview_frame)
        self._is_preview_playing = False
        self.initial_sequence_name = "Imported GIF"
        self.region_rect_percentage = {
            'x': 0.0, 'y': 0.0, 'width': 1.0, 'height': 1.0}
        self.adjustments = {'brightness': DEFAULT_BRIGHTNESS_FACTOR, 'saturation': DEFAULT_SATURATION_FACTOR,
                            'contrast': DEFAULT_CONTRAST_FACTOR, 'hue_shift': DEFAULT_HUE_SHIFT}
        self._init_ui()
        self._connect_signals()
        self._update_adjustment_value_labels()
        self.set_ui_elements_enabled(False)

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        # --- Inspiration Link ---
        self.inspiration_label = QLabel(
            "Find cool patterns on <a href='https://giphy.com/search/abstract-color'>GIPHY</a> or <a href='https://tenor.com/search/abstract-color-gifs?format=gifs'>Tenor</a>.")
        self.inspiration_label.setOpenExternalLinks(True)
        main_layout.addWidget(self.inspiration_label)
        source_group = QGroupBox("GIF Source")
        source_layout = QHBoxLayout(source_group)
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText(
            "Paste GIF URL or select a local file...")
        self.local_file_button = QPushButton("Browse Local GIF...")
        self.load_gif_button = QPushButton("Load GIF")
        source_layout.addWidget(self.url_input)
        source_layout.addWidget(self.local_file_button)
        source_layout.addWidget(self.load_gif_button)
        main_layout.addWidget(source_group)
        content_layout = QHBoxLayout()
        main_layout.addLayout(content_layout)
        left_panel_widget = QWidget()
        left_panel_widget.setFixedWidth(500)
        left_panel_widget.setFixedHeight(620)
        left_panel_v_layout = QVBoxLayout(left_panel_widget)
        left_panel_v_layout.setContentsMargins(0, 0, 0, 0)
        self.gif_display_label = GifRegionSelectorLabel(
            "Load a GIF to see its first frame here...")
        self.gif_display_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.gif_display_label.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.gif_display_label.setStyleSheet(
            "background-color: #282828; border: 1px solid #444;")
        left_panel_v_layout.addWidget(self.gif_display_label)
        preview_buttons_layout = QHBoxLayout()
        self.play_original_button = QPushButton("▶️ Play Original")
        self.play_original_button.setToolTip(
            "Play the original GIF in a new window for reference")
        preview_buttons_layout.addWidget(self.play_original_button)
        # --- NEW: Download GIF Button ---
        self.download_gif_button = QPushButton("⬇️ Download GIF")
        self.download_gif_button.setToolTip(
            "Save a local copy of a GIF loaded from a URL")
        preview_buttons_layout.addWidget(self.download_gif_button)
        preview_buttons_layout.addStretch()
        self.full_gif_button = QPushButton("Select Full GIF")
        preview_buttons_layout.addWidget(self.full_gif_button)
        left_panel_v_layout.addLayout(preview_buttons_layout)
        content_layout.addWidget(left_panel_widget)
        right_panel_widget = QWidget()
        controls_panel_layout = QVBoxLayout(right_panel_widget)
        right_panel_widget.setMinimumWidth(400)
        content_layout.addWidget(right_panel_widget)
        info_group = QGroupBox("Original GIF Info")
        info_layout = QVBoxLayout(info_group)
        self.info_width_height = QLabel("Dimensions: N/A")
        self.info_frames_loop = QLabel("Frames: N/A, Loop: N/A")
        self.info_avg_delay_fps = QLabel("Delay: N/A, FPS: N/A")
        info_layout.addWidget(self.info_width_height)
        info_layout.addWidget(self.info_frames_loop)
        info_layout.addWidget(self.info_avg_delay_fps)
        controls_panel_layout.addWidget(info_group)
        adj_group = QGroupBox("Color Adjustments")
        adj_layout = QVBoxLayout(adj_group)

        def create_slider_row(label_text, min_val, max_val, initial_val):
            layout = QHBoxLayout()
            label = QLabel(label_text)
            label.setMinimumWidth(70)
            slider = QSlider(Qt.Orientation.Horizontal)
            slider.setRange(min_val, max_val)
            slider.setValue(initial_val)
            value_label = QLabel()
            value_label.setMinimumWidth(55)
            reset_button = QPushButton("⟳")
            reset_button.setFixedSize(24, 24)
            reset_button.setObjectName("ResetButton")
            layout.addWidget(label)
            layout.addWidget(slider)
            layout.addWidget(value_label)
            layout.addWidget(reset_button)
            return layout, slider, value_label, reset_button
        bri_row_layout, self.brightness_slider, self.brightness_value_label, self.brightness_reset_button = create_slider_row(
            "Brightness:", SLIDER_MIN_FACTOR_VAL, SLIDER_MAX_FACTOR_VAL, self._factor_to_slider(DEFAULT_BRIGHTNESS_FACTOR))
        adj_layout.addLayout(bri_row_layout)
        sat_row_layout, self.saturation_slider, self.saturation_value_label, self.saturation_reset_button = create_slider_row(
            "Saturation:", SLIDER_MIN_FACTOR_VAL, SLIDER_MAX_FACTOR_VAL, self._factor_to_slider(DEFAULT_SATURATION_FACTOR))
        adj_layout.addLayout(sat_row_layout)
        con_row_layout, self.contrast_slider, self.contrast_value_label, self.contrast_reset_button = create_slider_row(
            "Contrast:", SLIDER_MIN_FACTOR_VAL, SLIDER_MAX_FACTOR_VAL, self._factor_to_slider(DEFAULT_CONTRAST_FACTOR))
        adj_layout.addLayout(con_row_layout)
        hue_row_layout, self.hue_slider, self.hue_value_label, self.hue_reset_button = create_slider_row(
            "Hue Shift:", SLIDER_MIN_HUE, SLIDER_MAX_HUE, int(round(DEFAULT_HUE_SHIFT)))
        adj_layout.addLayout(hue_row_layout)
        controls_panel_layout.addWidget(adj_group)
        anim_options_group = QGroupBox("Animation Options")
        anim_options_layout = QVBoxLayout(anim_options_group)
        fps_override_layout = QHBoxLayout()
        self.override_fps_checkbox = QCheckBox("Override GIF Speed")
        fps_override_layout.addWidget(self.override_fps_checkbox)
        self.original_fps_label = QLabel("Original: N/A")
        fps_override_layout.addWidget(self.original_fps_label)
        anim_options_layout.addLayout(fps_override_layout)
        self.playback_fps_slider = QSlider(Qt.Orientation.Horizontal)
        self.playback_fps_slider.setRange(1, 90)
        self.playback_fps_slider.setValue(20)
        self.playback_fps_label = QLabel("20 FPS")
        playback_fps_h_layout = QHBoxLayout()
        playback_fps_h_layout.addWidget(self.playback_fps_slider)
        playback_fps_h_layout.addWidget(self.playback_fps_label)
        anim_options_layout.addLayout(playback_fps_h_layout)
        controls_panel_layout.addWidget(anim_options_group)
        live_preview_group = QGroupBox("Live Pad Preview")
        live_preview_layout = QVBoxLayout(live_preview_group)
        self.pad_preview_widget = PadPreviewWidget()
        live_preview_layout.addWidget(self.pad_preview_widget)
        preview_controls_layout = QHBoxLayout()
        self.play_preview_button = QPushButton("Play Preview")
        self.pause_preview_button = QPushButton("Pause Preview")
        preview_controls_layout.addWidget(self.play_preview_button)
        preview_controls_layout.addWidget(self.pause_preview_button)
        live_preview_layout.addLayout(preview_controls_layout)
        controls_panel_layout.addWidget(live_preview_group)
        controls_panel_layout.addStretch(1)
        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("Sequence Name:"))
        self.sequence_name_input = QLineEdit()
        self.sequence_name_input.setPlaceholderText("Enter sequence name")
        name_layout.addWidget(self.sequence_name_input)
        main_layout.addLayout(name_layout)
        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(self.progress_bar)
        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.button_box.accepted.connect(self._on_accept)
        self.button_box.rejected.connect(self.reject)
        main_layout.addWidget(self.button_box)

    def _connect_signals(self):
        self.local_file_button.clicked.connect(self._browse_local_gif)
        self.load_gif_button.clicked.connect(self._load_gif_from_input)
        self.full_gif_button.clicked.connect(self.gif_display_label.set_full_region)
        self.gif_display_label.region_changed.connect(self._on_region_changed)
        self.play_original_button.clicked.connect(self._on_play_original_clicked)
        self.download_gif_button.clicked.connect(self._on_download_gif_clicked) # New connection
        self.brightness_slider.valueChanged.connect(self._on_adjustment_changed)
        self.saturation_slider.valueChanged.connect(self._on_adjustment_changed)
        self.contrast_slider.valueChanged.connect(self._on_adjustment_changed)
        self.hue_slider.valueChanged.connect(self._on_adjustment_changed)
        self.brightness_reset_button.clicked.connect(lambda: self.brightness_slider.setValue(self._factor_to_slider(DEFAULT_BRIGHTNESS_FACTOR)))
        self.saturation_reset_button.clicked.connect(lambda: self.saturation_slider.setValue(self._factor_to_slider(DEFAULT_SATURATION_FACTOR)))
        self.contrast_reset_button.clicked.connect(lambda: self.contrast_slider.setValue(self._factor_to_slider(DEFAULT_CONTRAST_FACTOR)))
        self.hue_reset_button.clicked.connect(lambda: self.hue_slider.setValue(DEFAULT_HUE_SHIFT))
        self.override_fps_checkbox.toggled.connect(self._on_override_fps_toggled)
        self.playback_fps_slider.valueChanged.connect(self._on_playback_fps_changed)
        self.play_preview_button.clicked.connect(self._play_preview)
        self.pause_preview_button.clicked.connect(self._pause_preview)

    def _get_user_documents_path(self) -> str:
        """Reliably finds the user's 'Documents' folder and the app-specific presets folder within it."""
        app_specific_folder_name = "Akai Fire RGB Controller User Presets"
        try:
            if sys.platform == "win32":
                import ctypes.wintypes
                CSIDL_PERSONAL = 5
                SHGFP_TYPE_CURRENT = 0
                buf = ctypes.create_unicode_buffer(ctypes.wintypes.MAX_PATH)
                ctypes.windll.shell32.SHGetFolderPathW(
                    None, CSIDL_PERSONAL, None, SHGFP_TYPE_CURRENT, buf)
                documents_path = buf.value
            else:  # For macOS and Linux
                documents_path = os.path.join(
                    os.path.expanduser("~"), "Documents")
            # Final fallback if the above fails for any reason
            if not os.path.isdir(documents_path):
                documents_path = os.path.expanduser("~")
            app_presets_dir = os.path.join(
                documents_path, app_specific_folder_name)
            os.makedirs(app_presets_dir, exist_ok=True)
            return app_presets_dir
        except Exception as e:
            print(
                f"GifImportDialog WARNING: User documents path error, falling back to current directory: {e}")
            fallback_dir = os.path.join(
                os.getcwd(), "user_presets_fallback_gid")
            os.makedirs(fallback_dir, exist_ok=True)
            return fallback_dir

    def _get_user_config_path(self, filename: str) -> str:
        """Helper to get a consistent user config path."""
        # This is a simplified version of the logic in MainWindow
        try:
            from appdirs import user_config_dir
            # Using a subfolder for our app's specific config
            app_name = "AkaiFirePixelForge"
            app_author = "Reg0lino"
            config_dir = user_config_dir(app_name, app_author, roaming=True)
            os.makedirs(config_dir, exist_ok=True)
            return os.path.join(config_dir, filename)
        except (ImportError, Exception):
            # Fallback to a local file if appdirs fails
            return filename

    def _load_last_path(self) -> str:
        """Loads the last used directory path from the config file."""
        try:
            if os.path.exists(self.config_file_path):
                with open(self.config_file_path, 'r') as f:
                    config = json.load(f)
                return config.get('last_gif_browse_path', os.path.expanduser('~/Downloads'))
        except (json.JSONDecodeError, Exception):
            pass
        return os.path.expanduser('~/Downloads')

    def _save_last_path(self, path: str):
        """Saves the last used directory path to the config file."""
        try:
            with open(self.config_file_path, 'w') as f:
                json.dump({'last_gif_browse_path': path}, f, indent=4)
        except Exception as e:
            print(f"Warning: Could not save last GIF path: {e}")

    def _factor_to_slider(self, factor_float_val: float) -> int:
        return int(round(factor_float_val * 100.0))

    def _slider_to_factor(self, slider_int_val: int) -> float:
        return float(slider_int_val) / 100.0

    def _update_adjustment_value_labels(self):
        self.brightness_value_label.setText(
            f"{self._slider_to_factor(self.brightness_slider.value()):.2f}x")
        self.saturation_value_label.setText(
            f"{self._slider_to_factor(self.saturation_slider.value()):.2f}x")
        self.contrast_value_label.setText(
            f"{self._slider_to_factor(self.contrast_slider.value()):.2f}x")
        self.hue_value_label.setText(f"{self.hue_slider.value():+d}°")

    def set_ui_elements_enabled(self, enabled: bool):
        is_url = self.url_input.text().strip().startswith('http')
        self.full_gif_button.setEnabled(enabled)
        self.brightness_slider.setEnabled(enabled)
        self.saturation_slider.setEnabled(enabled)
        self.contrast_slider.setEnabled(enabled)
        self.hue_slider.setEnabled(enabled)
        self.brightness_reset_button.setEnabled(enabled)
        self.saturation_reset_button.setEnabled(enabled)
        self.contrast_reset_button.setEnabled(enabled)
        self.hue_reset_button.setEnabled(enabled)
        self.sequence_name_input.setEnabled(enabled)
        self.override_fps_checkbox.setEnabled(enabled)
        self.play_preview_button.setEnabled(enabled)
        self.play_original_button.setEnabled(enabled)
        self.download_gif_button.setEnabled(enabled and is_url) # Only enable for URLs
        self.pause_preview_button.setEnabled(False)
        self.playback_fps_slider.setEnabled(enabled and self.override_fps_checkbox.isChecked())
        self.playback_fps_label.setEnabled(enabled and self.override_fps_checkbox.isChecked())
        self.button_box.button(QDialogButtonBox.StandardButton.Ok).setEnabled(enabled)

    def _browse_local_gif(self):
        """Opens a file dialog, starting in the last used directory."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select GIF File",
            self.last_used_browse_path,  # Use the loaded path
            "GIF Files (*.gif);;All Files (*)"
        )
        if file_path:
            self.url_input.setText(QUrl.fromLocalFile(file_path).toLocalFile())
            self.url_input.setCursorPosition(0)
            # Save the new path for next time
            new_path = os.path.dirname(file_path)
            self.last_used_browse_path = new_path
            self._save_last_path(new_path)
            self.load_gif_button.click()

    def _load_gif_from_input(self):
        source = self.url_input.text().strip()
        if not source:
            self.gif_display_label.setText("Please enter a GIF URL or select a local file.")
            return
        self.progress_bar.setValue(0); self.progress_bar.setFormat("Loading GIF...")
        self.set_ui_elements_enabled(False)
        self.info_width_height.setText("Dimensions: N/A"); self.info_frames_loop.setText("Frames: N/A, Loop: N/A")
        self.info_avg_delay_fps.setText("Delay: N/A, FPS: N/A"); self.original_fps_label.setText("Original: N/A")
        self.gif_display_label.setText("Loading..."); QApplication.processEvents()
        try:
            self.gif_engine.load_gif_from_source(source)
            info = self.gif_engine.get_original_gif_info()
            self.info_width_height.setText(f"Dimensions: {info['width']}x{info['height']}")
            self.info_frames_loop.setText(f"Frames: {info['frames']}, Loop: {info['loop']}")
            self.info_avg_delay_fps.setText(f"Delay: {info['avg_delay_ms']}ms, FPS: {info['fps']:.1f}")
            self.original_fps_label.setText(f"Original: {info['fps']:.1f} FPS ({info['avg_delay_ms']}ms)")
            self.original_pil_frames = self.gif_engine.original_frames_pil
            self.current_gif_frame_delays_ms = self.gif_engine.original_frame_delays_ms
            self.preview_pil_frames = []
            max_preview_width = 480
            for frame in self.original_pil_frames:
                if frame.width > max_preview_width:
                    aspect_ratio = frame.height / frame.width; new_height = int(max_preview_width * aspect_ratio)
                    self.preview_pil_frames.append(frame.resize((max_preview_width, new_height), Image.Resampling.LANCZOS))
                else:
                    self.preview_pil_frames.append(frame)
            self.sequence_name_input.setText(self.gif_engine.sequence_name)
            if self.preview_pil_frames:
                # --- Use the new method to set the image for manual drawing ---
                display_frame = self.preview_pil_frames[0].copy()
                self.gif_display_label.set_image_to_display(display_frame)
            self._pre_process_all_preview_frames()
            self.set_ui_elements_enabled(True)
            self.progress_bar.setValue(100); self.progress_bar.setFormat("GIF Loaded!")
            self._play_preview()
        except Exception as e:
            error_message = f"Error loading GIF: {e}"
            self.gif_display_label.set_image_to_display(None) # Clear image on error
            self.gif_display_label.setText(error_message)
            self.progress_bar.setValue(0); self.progress_bar.setFormat("Error")
            self.set_ui_elements_enabled(False)
            print(error_message)

    def _on_play_original_clicked(self):
        """
        Opens a new simple dialog to play the original source GIF.
        Handles web URLs by saving to a predictable, permission-safe cache folder.
        """
        if not self.original_pil_frames:
            QMessageBox.warning(self, "No GIF Loaded",
                                "Please load a GIF before trying to play it.")
            return
        source_path = self.url_input.text().strip()
        is_url = source_path.startswith('http')
        if is_url:
            gif_data = self.gif_engine.gif_data_in_memory
            if not gif_data:
                QMessageBox.critical(
                    self, "Error", "In-memory GIF data not found for URL source.")
                return
            try:
                # --- Use our new safe cache directory ---
                # Create a predictable filename based on the sequence name
                filename = self.gif_engine.sequence_name + ".gif"
                self.temp_file_path = os.path.join(
                    self.web_cache_dir, filename)
                # Write the in-memory data to this new file path
                with open(self.temp_file_path, 'wb') as f:
                    f.write(gif_data)
                # Now play from this safe, newly created file
                player = GifPlayerDialog(self.temp_file_path, self)
                player.exec()
            except Exception as e:
                QMessageBox.critical(
                    self, "Playback Error", f"Could not write or play temporary GIF:\n{e}")
        else:  # For local files, the logic is unchanged
            if not os.path.isfile(source_path):
                QMessageBox.warning(
                    self, "Invalid Path", "The source is not a valid local file path.")
                return
            player = GifPlayerDialog(source_path, self)
            player.exec()

    def _on_download_gif_clicked(self):
        """Opens a 'Save As' dialog to save the web GIF locally."""
        if not self.gif_engine.gif_data_in_memory:
            QMessageBox.warning(self, "Download Error", "No GIF data from a URL is currently loaded.")
            return
        suggested_name = self.gif_engine.sequence_name + ".gif"
        save_path, _ = QFileDialog.getSaveFileName(
            self,
            "Download GIF As...",
            os.path.join(self.last_used_browse_path, suggested_name),
            "GIF Files (*.gif)"
        )
        if save_path:
            try:
                with open(save_path, 'wb') as f:
                    f.write(self.gif_engine.gif_data_in_memory)
                QMessageBox.information(self, "Download Complete", f"Successfully saved GIF to:\n{save_path}")
            except Exception as e:
                QMessageBox.critical(self, "Download Failed", f"Could not save file:\n{e}")

    def _pre_process_all_preview_frames(self):
        """
        Processes all lightweight preview frames at once with the current settings.
        This populates self.processed_preview_frames for fast playback.
        """
        if not self.preview_pil_frames:
            self.processed_preview_frames = []
            return
        # This call processes the entire list of small frames and is still fast
        processed_sequence = self.gif_engine.process_frames_for_pads(
            self.region_rect_percentage,
            self.adjustments,
            source_frames=self.preview_pil_frames
        )
        # Store just the hex color lists
        self.processed_preview_frames = [frame_data[0]
                                        for frame_data in processed_sequence]

    def _select_full_gif_region(self):
        self.region_rect_percentage = {
            'x': 0.0, 'y': 0.0, 'width': 1.0, 'height': 1.0}
        self._update_pad_preview()  # Trigger preview update

    def _on_region_changed(self, region_dict: dict):
        self.region_rect_percentage = region_dict
        self._pre_process_all_preview_frames()  # Re-process with new region
        self._update_pad_preview()

    def _on_adjustment_changed(self):
        self.adjustments['brightness'] = self._slider_to_factor(
            self.brightness_slider.value())
        self.adjustments['saturation'] = self._slider_to_factor(
            self.saturation_slider.value())
        self.adjustments['contrast'] = self._slider_to_factor(
            self.contrast_slider.value())
        self.adjustments['hue_shift'] = float(self.hue_slider.value())
        self._update_adjustment_value_labels()
        self._pre_process_all_preview_frames()  # Re-process with new adjustments
        self._update_pad_preview()

    def _on_override_fps_toggled(self, checked: bool):
        self.playback_fps_slider.setEnabled(checked)
        self.playback_fps_label.setEnabled(checked)
        self._update_pad_preview()  # Preview speed might change

    def _on_playback_fps_changed(self, value: int):
        self.playback_fps_label.setText(f"{value} FPS")
        self._update_pad_preview()  # Preview speed will change

    def _update_preview_frame(self):
        if not self.processed_preview_frames:
            self.pad_preview_widget.set_colors(None)
            return
        self.current_preview_frame_index = (
            self.current_preview_frame_index + 1) % len(self.processed_preview_frames)
        current_pad_colors_hex = self.processed_preview_frames[self.current_preview_frame_index]
        self.preview_pads_updated.emit(current_pad_colors_hex)
        # Convert hex colors to RGB tuples for the preview widget
        rgb_tuples = []
        for hex_color in current_pad_colors_hex:
            try:
                rgb_tuples.append(ImageColor.getrgb(hex_color))
            except (ValueError, TypeError):
                rgb_tuples.append((0, 0, 0))  # Black on error
        self.pad_preview_widget.set_colors(rgb_tuples)
        if self.override_fps_checkbox.isChecked():
            fps = self.playback_fps_slider.value()
            delay_ms = int(1000 / fps) if fps > 0 else 100
            self.current_preview_timer.setInterval(delay_ms)
        else:
            original_delay_ms = self.current_gif_frame_delays_ms[self.current_preview_frame_index]
            self.current_preview_timer.setInterval(original_delay_ms)

    def _update_pad_preview(self):
        """
        Triggers a re-render of the current preview frame based on settings.
        Now uses the downscaled preview frames for performance.
        """
        # This is now just a trigger. _update_preview_frame does the real work.
        if self._is_preview_playing:
            if self.current_preview_timer.isActive():
                self.current_preview_timer.stop()
            self.current_preview_timer.start(1)
        else:
            self.current_preview_frame_index = 0
            self._update_preview_frame()

    def _play_preview(self):
        if not self.preview_pil_frames:
            return
        if not self._is_preview_playing:
            self._is_preview_playing = True
            self.play_preview_button.setEnabled(False)
            self.pause_preview_button.setEnabled(True)
            # --- Reset index to -1 so the first tick advances to 0 ---
            self.current_preview_frame_index = -1 
            self.current_preview_timer.start(1) # Start with a small delay

    def _pause_preview(self):
        if self._is_preview_playing:
            self._is_preview_playing = False
            self.play_preview_button.setEnabled(True)
            self.pause_preview_button.setEnabled(False)
            self.current_preview_timer.stop()
            # Optionally, reset to the first frame when paused
            self.current_preview_frame_index = 0
            self._update_preview_frame()

    def _on_accept(self):
        # --- Check the definitive list of original frames ---
        if not self.original_pil_frames:
            QMessageBox.warning(self, "Import Error",
                                "Please load a GIF before importing.")
            return
        sequence_name = self.sequence_name_input.text().strip()
        if not sequence_name:
            sequence_name = self.gif_engine.sequence_name
        self.progress_bar.setFormat("Processing frames for final import...")
        self.progress_bar.setValue(0)
        QApplication.processEvents()
        # Use the full-resolution original frames for the final output
        processed_gif_sequence = self.gif_engine.process_frames_for_pads(
            self.region_rect_percentage,
            self.adjustments,
            source_frames=self.original_pil_frames  # Explicitly use originals
        )
        if self.override_fps_checkbox.isChecked():
            fps = self.playback_fps_slider.value()
            final_delay_ms = int(1000 / fps) if fps > 0 else 100
        else:
            final_delay_ms = self.gif_engine.get_original_gif_info().get('avg_delay_ms', 100)
        self.progress_bar.setValue(100)
        self.progress_bar.setFormat("Ready for Import!")
        QApplication.processEvents()
        self.gif_import_requested.emit(
            processed_gif_sequence, final_delay_ms, sequence_name)
        self.accept()

    def closeEvent(self, event):
        """
        Overrides the close event to clean up any temporary files created in the WebCache.
        """
        print("GIF Import Dialog closing, cleaning up cache...")
        if self.temp_file_path and os.path.exists(self.temp_file_path):
            try:
                os.remove(self.temp_file_path)
                print(
                    f"Successfully removed temporary file: {self.temp_file_path}")
            except OSError as e:
                print(
                    f"Error removing temporary file '{self.temp_file_path}': {e}")
        # We must also stop the preview timer to prevent it from running after the dialog is gone
        if self.current_preview_timer.isActive():
            self.current_preview_timer.stop()
        super().closeEvent(event)  # IMPORTANT: Continue with the normal close procedure

# For standalone testing
if __name__ == '__main__':
    app = QApplication(sys.argv)
    dialog = GifImportDialog()
    # To test loading a GIF immediately on startup:
    # dialog.url_input.setText("https://i.giphy.com/media/v1.gif")
    # dialog._load_gif_from_input()
    dialog.show()
    sys.exit(app.exec())
