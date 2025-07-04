# AKAI_Fire_PixelForge/gui/gif_import_dialog.py
import sys
import os
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QGroupBox, 
    QFileDialog, QProgressBar, QDialogButtonBox, QSizePolicy, QSlider, QCheckBox, QComboBox, QSpacerItem, QMessageBox, QApplication
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize, QTimer, QUrl
from PyQt6.QtGui import QImage, QPixmap, QFont
from PIL import Image
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

MIN_DIALOG_HEIGHT = 855 # -------- HEIGHT VARIABLE TODO********

class GifImportDialog(QDialog):
    # processed_frames_data, delay_ms, sequence_name
    gif_import_requested = pyqtSignal(list, int, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("📥 Import GIF Animation")
        self.setMinimumSize(800, MIN_DIALOG_HEIGHT)
        # --- NEW ATTRIBUTES FOR PATH PERSISTENCE ---
        self.config_file_path = self._get_user_config_path(
            'gif_import_settings.json')
        self.last_used_browse_path = self._load_last_path()
        self.gif_engine = GifProcessingEngine()
        # Cache of PIL frames for live preview
        self.current_gif_frames_pil: list[Image.Image] = []
        self.current_gif_frame_delays_ms: list[int] = []  # Cache of delays
        self.current_preview_frame_index = 0
        self.current_preview_timer = QTimer(self)
        self.current_preview_timer.timeout.connect(self._update_preview_frame)
        self._is_preview_playing = False
        self.initial_sequence_name = "Imported GIF"
        self.region_rect_percentage = {
            'x': 0.0, 'y': 0.0, 'width': 1.0, 'height': 1.0}
        self.adjustments = {
            'brightness': DEFAULT_BRIGHTNESS_FACTOR,
            'saturation': DEFAULT_SATURATION_FACTOR,
            'contrast': DEFAULT_CONTRAST_FACTOR,
            'hue_shift': DEFAULT_HUE_SHIFT
        }
        self._init_ui()
        self._connect_signals()
        self._update_adjustment_value_labels()
        self.set_ui_elements_enabled(False)

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        # --- GIF Source Group ---
        source_group = QGroupBox("GIF Source")
        source_layout = QHBoxLayout(source_group)
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("Paste GIF URL here")
        self.local_file_button = QPushButton("Browse Local GIF...")
        self.load_gif_button = QPushButton("Load GIF")
        source_layout.addWidget(self.url_input)
        source_layout.addWidget(self.local_file_button)
        source_layout.addWidget(self.load_gif_button)
        main_layout.addWidget(source_group)
        # --- Main Content Area (GIF Display, Preview, Settings) ---
        content_layout = QHBoxLayout()
        main_layout.addLayout(content_layout)
        # --- Left Panel: GIF Frame Display (with Region Selection Concept) ---
        self.gif_display_label = QLabel(
            "Load a GIF to see its first frame here...")
        self.gif_display_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        # Adequate size for a scaled GIF frame
        self.gif_display_label.setMinimumSize(320, 240)
        self.gif_display_label.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.gif_display_label.setStyleSheet(
            "background-color: #282828; border: 1px solid #444;")
        content_layout.addWidget(self.gif_display_label, 3)  # Takes more space
        # --- Right Panel: Controls and Live Preview ---
        controls_panel_layout = QVBoxLayout()
        content_layout.addLayout(controls_panel_layout, 2)  # Takes less space
        # --- Original GIF Info ---
        info_group = QGroupBox("Original GIF Info")
        info_layout = QVBoxLayout(info_group)
        self.info_width_height = QLabel("Dimensions: N/A")
        self.info_frames_loop = QLabel("Frames: N/A, Loop: N/A")
        self.info_avg_delay_fps = QLabel("Delay: N/A, FPS: N/A")
        info_layout.addWidget(self.info_width_height)
        info_layout.addWidget(self.info_frames_loop)
        info_layout.addWidget(self.info_avg_delay_fps)
        controls_panel_layout.addWidget(info_group)
        # --- Region Selection Controls (Simple Sliders for now, will enhance later if desired) ---
        region_group = QGroupBox("Region Selection")
        region_layout = QVBoxLayout(region_group)
        # Reusing the idea of sliders for region, but for now fixed to full GIF.
        # This will be replaced by an actual draggable widget if it's high priority.
        # For this version, we will have fixed values and just a "Full GIF" button.
        self.full_gif_button = QPushButton("Select Full GIF")
        region_layout.addWidget(self.full_gif_button)
        controls_panel_layout.addWidget(region_group)
        # --- Color Adjustments Group ---
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
        # --- Animation Options Group ---
        anim_options_group = QGroupBox("Animation Options")
        anim_options_layout = QVBoxLayout(anim_options_group)
        # FPS Override
        fps_override_layout = QHBoxLayout()
        self.override_fps_checkbox = QCheckBox("Override GIF Speed")
        fps_override_layout.addWidget(self.override_fps_checkbox)
        self.original_fps_label = QLabel("Original: N/A")
        fps_override_layout.addWidget(self.original_fps_label)
        anim_options_layout.addLayout(fps_override_layout)
        self.playback_fps_slider = QSlider(Qt.Orientation.Horizontal)
        self.playback_fps_slider.setRange(1, 90)  # 1 to 90 FPS
        self.playback_fps_slider.setValue(20)  # Default to 20 FPS
        self.playback_fps_label = QLabel("20 FPS")
        playback_fps_h_layout = QHBoxLayout()
        playback_fps_h_layout.addWidget(self.playback_fps_slider)
        playback_fps_h_layout.addWidget(self.playback_fps_label)
        anim_options_layout.addLayout(playback_fps_h_layout)
        controls_panel_layout.addWidget(anim_options_group)
        # --- Live Pad Preview ---
        live_preview_group = QGroupBox("Live Pad Preview")
        live_preview_layout = QVBoxLayout(live_preview_group)
        self.pad_preview_label = QLabel("Processed frames will play here...")
        self.pad_preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.pad_preview_label.setMinimumSize(
            NUM_GRID_COLS * 15, NUM_GRID_ROWS * 15)  # Example scaled size
        self.pad_preview_label.setStyleSheet(
            "background-color: #000000; border: 1px solid #444;")
        live_preview_layout.addWidget(self.pad_preview_label)
        preview_controls_layout = QHBoxLayout()
        self.play_preview_button = QPushButton("Play Preview")
        self.pause_preview_button = QPushButton("Pause Preview")
        preview_controls_layout.addWidget(self.play_preview_button)
        preview_controls_layout.addWidget(self.pause_preview_button)
        live_preview_layout.addLayout(preview_controls_layout)
        controls_panel_layout.addWidget(live_preview_group)
        controls_panel_layout.addStretch(1)  # Push everything up
        # --- Sequence Name & Dialog Buttons ---
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
        self.full_gif_button.clicked.connect(self._select_full_gif_region)
        # Color Adjustment Sliders
        self.brightness_slider.valueChanged.connect(
            self._on_adjustment_changed)
        self.saturation_slider.valueChanged.connect(
            self._on_adjustment_changed)
        self.contrast_slider.valueChanged.connect(self._on_adjustment_changed)
        self.hue_slider.valueChanged.connect(self._on_adjustment_changed)
        self.brightness_reset_button.clicked.connect(lambda: self.brightness_slider.setValue(
            self._factor_to_slider(DEFAULT_BRIGHTNESS_FACTOR)))
        self.saturation_reset_button.clicked.connect(lambda: self.saturation_slider.setValue(
            self._factor_to_slider(DEFAULT_SATURATION_FACTOR)))
        self.contrast_reset_button.clicked.connect(lambda: self.contrast_slider.setValue(
            self._factor_to_slider(DEFAULT_CONTRAST_FACTOR)))
        self.hue_reset_button.clicked.connect(
            lambda: self.hue_slider.setValue(DEFAULT_HUE_SHIFT))
        # Animation Options
        self.override_fps_checkbox.toggled.connect(
            self._on_override_fps_toggled)
        self.playback_fps_slider.valueChanged.connect(
            self._on_playback_fps_changed)
        # Preview Controls
        self.play_preview_button.clicked.connect(self._play_preview)
        self.pause_preview_button.clicked.connect(self._pause_preview)

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
        # Always starts paused or when playing
        self.pause_preview_button.setEnabled(False)
        # Only enable FPS slider if override is checked AND dialog is enabled
        self.playback_fps_slider.setEnabled(
            enabled and self.override_fps_checkbox.isChecked())
        self.playback_fps_label.setEnabled(
            enabled and self.override_fps_checkbox.isChecked())
        self.button_box.button(
            QDialogButtonBox.StandardButton.Ok).setEnabled(enabled)

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
            self.gif_display_label.setText(
                "Please enter a GIF URL or select a local file.")
            return
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("Loading GIF...")
        self.set_ui_elements_enabled(False)  # Disable controls during load
        try:
            self.gif_engine.load_gif_from_source(source)
            info = self.gif_engine.get_original_gif_info()
            # Cache original frames and delays for live preview
            self.current_gif_frames_pil = self.gif_engine.original_frames_pil
            self.current_gif_frame_delays_ms = self.gif_engine.original_frame_delays_ms
            # Update info labels
            self.info_width_height.setText(
                f"Dimensions: {info['width']}x{info['height']}")
            self.info_frames_loop.setText(
                f"Frames: {info['frames']}, Loop: {'Infinite' if info['loop'] == 0 else info['loop']}")
            self.original_fps_label.setText(
                f"Original: {info['fps']:.1f} FPS ({info['avg_delay_ms']}ms)")
            self.sequence_name_input.setText(self.gif_engine.sequence_name)
            # Display first frame
            first_frame_pil = self.gif_engine.get_first_frame_pil()
            if first_frame_pil:
                # Scale first frame to fit label, maintaining aspect ratio
                scaled_pixmap = self._convert_pil_to_scaled_pixmap(
                    first_frame_pil, self.gif_display_label.size())
                self.gif_display_label.setPixmap(scaled_pixmap)
                self.gif_display_label.setText("")  # Clear "Loading..." text
            self._select_full_gif_region()  # Default to full GIF selection
            self._update_pad_preview()  # Update preview with initial adjustments
            self.set_ui_elements_enabled(True)
            self.progress_bar.setValue(100)
            self.progress_bar.setFormat("GIF Loaded!")
            self._play_preview()  # Auto-play preview on load
        except (IOError, ValueError, requests.exceptions.RequestException) as e:
            self.gif_display_label.setText(f"Error loading GIF: {e}")
            self.progress_bar.setValue(0)
            self.progress_bar.setFormat("Error")
            self.set_ui_elements_enabled(False)  # Keep disabled on error
        except Exception as e:
            self.gif_display_label.setText(
                f"An unexpected error occurred: {e}")
            self.progress_bar.setValue(0)
            self.progress_bar.setFormat("Error")
            self.set_ui_elements_enabled(False)  # Keep disabled on error

    def _convert_pil_to_scaled_pixmap(self, pil_image: Image.Image, target_size: QSize) -> QPixmap:
        if pil_image.mode != "RGB":
            pil_image = pil_image.convert("RGB")
        image_data_bytes = pil_image.tobytes("raw", "RGB")
        q_image = QImage(image_data_bytes, pil_image.width, pil_image.height,
                         pil_image.width * 3, QImage.Format.Format_RGB888)
        pixmap = QPixmap.fromImage(q_image)
        return pixmap.scaled(target_size, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)

    def _select_full_gif_region(self):
        self.region_rect_percentage = {
            'x': 0.0, 'y': 0.0, 'width': 1.0, 'height': 1.0}
        self._update_pad_preview()  # Trigger preview update

    def _on_adjustment_changed(self):
        self.adjustments['brightness'] = self._slider_to_factor(
            self.brightness_slider.value())
        self.adjustments['saturation'] = self._slider_to_factor(
            self.saturation_slider.value())
        self.adjustments['contrast'] = self._slider_to_factor(
            self.contrast_slider.value())
        self.adjustments['hue_shift'] = float(self.hue_slider.value())
        self._update_adjustment_value_labels()
        self._update_pad_preview()  # Update preview based on new adjustments

    def _on_override_fps_toggled(self, checked: bool):
        self.playback_fps_slider.setEnabled(checked)
        self.playback_fps_label.setEnabled(checked)
        self._update_pad_preview()  # Preview speed might change

    def _on_playback_fps_changed(self, value: int):
        self.playback_fps_label.setText(f"{value} FPS")
        self._update_pad_preview()  # Preview speed will change

    def _update_preview_frame(self):
        """Advances the live pad preview to the next frame."""
        if not self.current_gif_frames_pil:
            return
        self.current_preview_frame_index = (
            self.current_preview_frame_index + 1) % len(self.current_gif_frames_pil)
        # Get the current frame and apply processing *for the preview*.
        # The processing engine will handle the necessary aspect ratio correction and color adjustments.
        temp_processed_sequence = self.gif_engine.process_frames_for_pads(
            self.region_rect_percentage,
            self.adjustments
        )
        if temp_processed_sequence:
            # We only need the current frame from the processed sequence
            current_pad_colors_hex = temp_processed_sequence[self.current_preview_frame_index][0]
            # Convert hex colors to a PIL Image (16x4 pixels) for display
            # Create a blank 16x4 image
            pad_preview_pil = Image.new('RGB', (NUM_GRID_COLS, NUM_GRID_ROWS))
            pixels = pad_preview_pil.load()
            for i, hex_color in enumerate(current_pad_colors_hex):
                r, g, b = Image.new('RGB', (1, 1), hex_color).getpixel(
                    (0, 0))  # Convert hex to RGB tuple
                row, col = divmod(i, NUM_GRID_COLS)
                pixels[col, row] = (r, g, b)  # PIL uses (x,y) not (row,col)
            # Scale up the 16x4 image for display in the QLabel
            scaled_pixmap = self._convert_pil_to_scaled_pixmap(
                pad_preview_pil, self.pad_preview_label.size())
            self.pad_preview_label.setPixmap(scaled_pixmap)
            self.pad_preview_label.setText("")  # Clear "Loading..." text
            # Adjust timer interval for live preview playback
            if self.override_fps_checkbox.isChecked():
                fps = self.playback_fps_slider.value()
                delay_ms = int(1000 / fps) if fps > 0 else 100
                self.current_preview_timer.setInterval(delay_ms)
            else:
                original_delay_ms = self.current_gif_frame_delays_ms[self.current_preview_frame_index]
                self.current_preview_timer.setInterval(original_delay_ms)
        else:
            self.pad_preview_label.setText(
                "Preview Error: No processed frames.")
            self._pause_preview()

    def _update_pad_preview(self):
        """Triggers a re-render of the current preview frame based on settings."""
        # This will recalculate the current frame based on new settings.
        # It's called when adjustments change.
        if self._is_preview_playing:
            # If playing, the timer will call _update_preview_frame automatically.
            # We just need to restart the timer to apply potential speed changes.
            self.current_preview_timer.stop()
            # Small delay to re-evaluate speed
            self.current_preview_timer.start(1)
        else:
            # If not playing, just render the current frame statically (first frame).
            self.current_preview_frame_index = 0  # Show first frame statically
            self._update_preview_frame()  # Force update of just the current frame

    def _play_preview(self):
        if not self.current_gif_frames_pil:
            return
        if not self._is_preview_playing:
            self._is_preview_playing = True
            self.play_preview_button.setEnabled(False)
            self.pause_preview_button.setEnabled(True)
            # Start with a small initial delay to immediately show first frame
            self.current_preview_timer.start(1)
            self._update_preview_frame()  # Show first frame immediately

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
        if not self.current_gif_frames_pil:
            QMessageBox.warning(self, "Import Error",
                                "Please load a GIF before importing.")
            return

        sequence_name = self.sequence_name_input.text().strip()
        if not sequence_name:
            sequence_name = self.gif_engine.sequence_name  # Fallback to original GIF name

        # Process ALL frames for the final output
        self.progress_bar.setFormat("Processing frames...")
        self.progress_bar.setValue(0)
        QApplication.processEvents()  # Update UI

        processed_gif_sequence = self.gif_engine.process_frames_for_pads(
            self.region_rect_percentage,
            self.adjustments
        )

        # Determine the final playback delay for the entire sequence
        final_delay_ms = 0
        if self.override_fps_checkbox.isChecked():
            fps = self.playback_fps_slider.value()
            final_delay_ms = int(1000 / fps) if fps > 0 else 100
        else:
            final_delay_ms = self.gif_engine.get_original_gif_info().get('avg_delay_ms', 100)

        self.progress_bar.setValue(100)
        self.progress_bar.setFormat("Ready for Import!")
        QApplication.processEvents()  # Update UI

        self.gif_import_requested.emit(
            processed_gif_sequence, final_delay_ms, sequence_name)
        self.accept()


# For standalone testing
if __name__ == '__main__':
    app = QApplication(sys.argv)
    dialog = GifImportDialog()
    # To test loading a GIF immediately on startup:
    # dialog.url_input.setText("https://i.giphy.com/media/v1.gif")
    # dialog._load_gif_from_input()
    dialog.show()
    sys.exit(app.exec())
