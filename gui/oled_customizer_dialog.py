### START OF FILE gui/oled_customizer_dialog.py ###

import sys
import os
import json
from PyQt6.QtWidgets import (
    QApplication, QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QLineEdit, QPushButton,
    QDialogButtonBox, QFontComboBox, QSpinBox, QWidget, QSizePolicy, QFrame,
    QSlider, QGroupBox, QListWidget, QListWidgetItem, QSplitter, QComboBox,
    QTextEdit, QCheckBox, QFileDialog, QMessageBox, QStackedWidget, QScrollArea
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QSize
from PyQt6.QtGui import QFont, QColor, QPixmap, QPainter, QFontMetrics, QImage, QIcon, QCloseEvent

# Attempt to import oled_renderer for previewing
try:
    from oled_utils import oled_renderer
    OLED_RENDERER_AVAILABLE_FOR_DIALOG = True
    NATIVE_OLED_WIDTH = oled_renderer.OLED_WIDTH
    NATIVE_OLED_HEIGHT = oled_renderer.OLED_HEIGHT
except ImportError:
    print("OLEDCustomizerDialog WARNING: oled_renderer not found. Live preview will be basic.")
    OLED_RENDERER_AVAILABLE_FOR_DIALOG = False
    NATIVE_OLED_WIDTH = 128
    NATIVE_OLED_HEIGHT = 64

# Attempt to import image_processing utility
try:
    from oled_utils import image_processing
    IMAGE_PROCESSING_AVAILABLE = True
    print("OLEDCustomizerDialog INFO: image_processing module loaded successfully.")
except ImportError as e:
    print(
        f"OLEDCustomizerDialog WARNING: image_processing module not found: {e}. Animation import will be disabled.")
    IMAGE_PROCESSING_AVAILABLE = False
    # Minimal placeholder if image_processing is not available

    class image_processing_placeholder:
        @staticmethod
        def process_image_to_oled_data(
            *args, **kwargs): return None, None, None
    image_processing = image_processing_placeholder()

#  should be enough to show all controls in the animation editor, including the threshold slider.
#  try 500px for now, you can adjust this.
INNER_EDITOR_PANEL_CONTENT_MIN_HEIGHT = 500

# Constants for Scroll Speed Configuration
MIN_SPEED_LEVEL = 1
MAX_SPEED_LEVEL = 20
MIN_ACTUAL_DELAY_MS = 20
MAX_ACTUAL_DELAY_MS = 500
DEFAULT_GLOBAL_SCROLL_DELAY_MS_FALLBACK = 180

PREVIEW_LABEL_SCALE_FACTOR = 2  # For the main preview label
# Native size for in-editor preview
ANIM_EDITOR_PREVIEW_WIDTH = NATIVE_OLED_WIDTH
ANIM_EDITOR_PREVIEW_HEIGHT = NATIVE_OLED_HEIGHT

USER_OLED_TEXT_ITEMS_SUBDIR = "TextItems"           # <<< ADD THIS
USER_OLED_ANIM_ITEMS_SUBDIR = "ImageAnimations"     # <<< ADD THIS

MIN_SPEED_LEVEL = 1  # Example, ensure these are defined if used by sliders
MAX_SPEED_LEVEL = 20

#  Dialog Size ---
DIALOG_INITIAL_WIDTH = 870
DIALOG_INITIAL_HEIGHT = 1060
DIALOG_MINIMUM_WIDTH = 800
DIALOG_MINIMUM_HEIGHT = 700


class OLEDCustomizerDialog(QDialog):
    # (default_item_relative_path, global_scroll_delay_ms)
    global_settings_changed = pyqtSignal(str, int)
    dialog_closed = pyqtSignal()

    # Replacement for 'def __init__(...)' in OLEDCustomizerDialog class
    def __init__(self,
                 current_active_graphic_path: str | None,
                 current_global_scroll_delay_ms: int,
                 # This is actually not used directly by the dialog anymore
                 available_oled_items: list,
                 user_oled_presets_base_path: str,
                 available_app_fonts: list[str],
                 parent: QWidget | None = None):
        super().__init__(parent)
        self.setWindowTitle("⚙️ OLED Active Graphic Manager")

        self.resize(DIALOG_INITIAL_WIDTH, DIALOG_INITIAL_HEIGHT)
        self.setMinimumSize(DIALOG_MINIMUM_WIDTH, DIALOG_MINIMUM_HEIGHT)

        self._initial_active_graphic_path = current_active_graphic_path
        self._initial_global_scroll_delay_ms = current_global_scroll_delay_ms
        self._current_dialog_chosen_active_graphic_relative_path: str | None = self._initial_active_graphic_path

        # --- Explicitly initialize UI attributes to None before _init_ui ---
        self.default_startup_item_combo: QComboBox | None = None
        self.global_scroll_speed_level_slider: QSlider | None = None
        self.global_scroll_speed_display_label: QLabel | None = None
        self.item_library_list: QListWidget | None = None
        self.new_text_item_button: QPushButton | None = None
        self.new_anim_item_button: QPushButton | None = None
        self.edit_selected_item_button: QPushButton | None = None
        self.delete_selected_item_button: QPushButton | None = None
        self.splitter: QSplitter | None = None
        self.item_editor_group: QGroupBox | None = None
        self.editor_stacked_widget: QStackedWidget | None = None
        self.text_editor_widget: QWidget | None = None
        self.item_name_edit: QLineEdit | None = None
        self.text_content_edit: QLineEdit | None = None
        self.text_font_family_combo: QFontComboBox | None = None
        self.text_font_size_spinbox: QSpinBox | None = None
        self.text_scroll_checkbox: QCheckBox | None = None
        self.text_alignment_combo: QComboBox | None = None
        self.text_anim_override_speed_checkbox: QCheckBox | None = None
        self.text_anim_item_scroll_speed_spinbox: QSpinBox | None = None
        self.text_anim_pause_at_ends_spinbox: QSpinBox | None = None
        self.save_this_text_item_button: QPushButton | None = None
        self.animation_editor_widget_container: QWidget | None = None
        self.anim_item_name_edit: QLineEdit | None = None
        self.anim_source_file_label: QLabel | None = None
        self.anim_browse_button: QPushButton | None = None
        self.anim_resize_mode_combo: QComboBox | None = None
        self.anim_mono_conversion_combo: QComboBox | None = None
        self.anim_threshold_widget: QWidget | None = None
        self.anim_threshold_slider: QSlider | None = None
        self.anim_threshold_value_label: QLabel | None = None
        self.anim_contrast_slider: QSlider | None = None
        self.anim_contrast_value_label: QLabel | None = None
        # --- New UI attribute placeholders ---
        self.anim_brightness_slider: QSlider | None = None
        self.anim_brightness_value_label: QLabel | None = None
        self.anim_sharpen_slider: QSlider | None = None
        self.anim_sharpen_value_label: QLabel | None = None
        # --- End New UI attribute placeholders ---
        self.anim_invert_colors_checkbox: QCheckBox | None = None
        self.anim_playback_fps_spinbox: QSpinBox | None = None
        self.anim_loop_behavior_combo: QComboBox | None = None
        self.anim_process_button: QPushButton | None = None
        self.anim_play_preview_button: QPushButton | None = None
        self.anim_frame_info_label: QLabel | None = None
        self.save_this_animation_button: QPushButton | None = None
        self.oled_preview_label: QLabel | None = None
        self.button_box: QDialogButtonBox | None = None
        self.save_and_apply_button: QPushButton | None = None

        self.user_oled_presets_base_path = user_oled_presets_base_path
        self.text_items_dir = os.path.join(
            self.user_oled_presets_base_path, USER_OLED_TEXT_ITEMS_SUBDIR)
        self.animation_items_dir = os.path.join(
            self.user_oled_presets_base_path, USER_OLED_ANIM_ITEMS_SUBDIR)
        self.available_app_fonts = available_app_fonts

        # State Variables
        self._preview_scroll_timer = QTimer(self)
        self._preview_scroll_timer.timeout.connect(self._scroll_preview_step)
        self._preview_current_scroll_offset = 0
        self._preview_text_pixel_width = 0
        self._preview_is_scrolling = False
        self._current_preview_font_object = None
        self._current_preview_anim_logical_frame = None
        self._current_edited_item_path = None
        self._current_edited_item_type = None
        self._is_editing_new_item = False
        self._editor_has_unsaved_changes = False
        self._current_anim_source_filepath = None
        self._processed_logical_frames = None
        self._processed_anim_source_fps = None
        self._processed_anim_source_loop_count = None
        self._anim_editor_preview_timer = QTimer(self)
        self._anim_editor_preview_timer.timeout.connect(
            self._play_next_anim_editor_preview_frame)
        self._is_anim_editor_preview_playing = False
        self._current_anim_editor_preview_frame_index = 0
        self._library_preview_anim_timer = QTimer(self)
        self._library_preview_anim_timer.timeout.connect(
            self._play_next_library_preview_anim_frame)
        self._current_library_preview_anim_frames = None
        self._current_library_preview_anim_frame_index = 0
        self._library_preview_anim_fps = 15.0
        self._library_preview_anim_loop_behavior = "Loop Infinitely"
        self._is_library_preview_anim_playing = False

        self._init_ui()
        self._connect_signals()
        QTimer.singleShot(0, self._load_initial_data)
        self._update_editor_panel_visibility(None)


    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        # Dialog min/initial size is set in __init__

        # Global Settings Group
        global_settings_group = QGroupBox("Global OLED Settings")
        global_settings_layout = QHBoxLayout(global_settings_group)
        global_settings_layout.addWidget(QLabel("Set as Active Graphic:"))
        self.default_startup_item_combo = QComboBox()
        self.default_startup_item_combo.setMinimumWidth(200)
        self.default_startup_item_combo.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        global_settings_layout.addWidget(self.default_startup_item_combo, 1)
        global_settings_layout.addSpacing(20)
        global_settings_layout.addWidget(QLabel("Global Scroll Speed:"))
        self.global_scroll_speed_level_slider = QSlider(
            Qt.Orientation.Horizontal)
        self.global_scroll_speed_level_slider.setRange(
            MIN_SPEED_LEVEL, MAX_SPEED_LEVEL)
        self.global_scroll_speed_level_slider.setSingleStep(1)
        self.global_scroll_speed_level_slider.setPageStep(2)
        self.global_scroll_speed_level_slider.setTickInterval(
            max(1, (MAX_SPEED_LEVEL - MIN_SPEED_LEVEL) // 10))
        self.global_scroll_speed_level_slider.setTickPosition(
            QSlider.TickPosition.TicksBelow)
        global_settings_layout.addWidget(
            self.global_scroll_speed_level_slider, 1)
        self.global_scroll_speed_display_label = QLabel()
        self.global_scroll_speed_display_label.setMinimumWidth(90)
        self.global_scroll_speed_display_label.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        global_settings_layout.addWidget(
            self.global_scroll_speed_display_label)
        main_layout.addWidget(global_settings_group)

        # <<< NEW: Connect signal for default_startup_item_combo
        self.default_startup_item_combo.currentIndexChanged.connect(
            self._on_active_graphic_combo_changed)

        self.splitter = QSplitter(Qt.Orientation.Horizontal)

        # Library Group (Left)
        library_group = QGroupBox("Item Library")
        library_layout = QVBoxLayout(library_group)
        self.item_library_list = QListWidget()
        library_layout.addWidget(self.item_library_list)
        library_buttons_layout = QGridLayout()
        self.new_text_item_button = QPushButton("✨ New Text Item")
        self.new_anim_item_button = QPushButton(
            "🎬 New Animation or Image Item")
        self.new_anim_item_button.setEnabled(IMAGE_PROCESSING_AVAILABLE)
        self.edit_selected_item_button = QPushButton("✏️ Edit Selected")
        self.delete_selected_item_button = QPushButton("🗑️ Delete Selected")
        library_buttons_layout.addWidget(self.new_text_item_button, 0, 0)
        library_buttons_layout.addWidget(self.new_anim_item_button, 0, 1)
        library_buttons_layout.addWidget(self.edit_selected_item_button, 1, 0)
        library_buttons_layout.addWidget(
            self.delete_selected_item_button, 1, 1)
        library_layout.addLayout(library_buttons_layout)
        self.splitter.addWidget(library_group)

        # Item Editor Group (Right)
        self.item_editor_group = QGroupBox("Item Editor")
        self.item_editor_group.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        item_editor_main_layout = QVBoxLayout(self.item_editor_group)

        self.editor_stacked_widget = QStackedWidget()
        self.editor_stacked_widget.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        self.text_editor_widget = self._create_text_editor_panel()
        self.text_editor_widget.setSizePolicy(
            QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)

        self.animation_editor_widget_container = self._create_animation_editor_panel()
        self.animation_editor_widget_container.setSizePolicy(
            QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)

        self.editor_stacked_widget.addWidget(self.text_editor_widget)
        self.editor_stacked_widget.addWidget(
            self.animation_editor_widget_container)
        item_editor_main_layout.addWidget(self.editor_stacked_widget, 1)

        self.splitter.addWidget(self.item_editor_group)

        library_initial_width = 280
        editor_initial_width = DIALOG_INITIAL_WIDTH - \
            library_initial_width - self.splitter.handleWidth() - 20
        self.splitter.setSizes(
            [library_initial_width, max(100, editor_initial_width)])

        main_layout.addWidget(self.splitter, 1)

        # Live Preview Group
        preview_group = QGroupBox("Live Preview (Main)")
        preview_layout = QVBoxLayout(preview_group)
        self.oled_preview_label = QLabel("Preview")
        preview_label_width = NATIVE_OLED_WIDTH * PREVIEW_LABEL_SCALE_FACTOR
        preview_label_height = NATIVE_OLED_HEIGHT * PREVIEW_LABEL_SCALE_FACTOR
        self.oled_preview_label.setFixedSize(
            preview_label_width, preview_label_height)
        self.oled_preview_label.setStyleSheet(
            "background-color: black; border: 1px solid #555555;")
        self.oled_preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        preview_layout.addWidget(
            self.oled_preview_label, 0, Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(preview_group)

        # Dialog Buttons
        self.button_box = QDialogButtonBox()
        # <<< NEW: Add Save & Apply button (will be styled as "Apply" by default on some OS)
        self.save_and_apply_button = self.button_box.addButton(
            "Save && Apply", QDialogButtonBox.ButtonRole.ApplyRole)
        # Add standard Save and Cancel buttons
        self.button_box.addButton(QDialogButtonBox.StandardButton.Save)
        self.button_box.addButton(QDialogButtonBox.StandardButton.Cancel)
        main_layout.addWidget(self.button_box)

    def _on_active_graphic_combo_changed(self, index: int):
        """
        Slot for when the 'Set as Active Graphic' QComboBox selection changes.
        Updates the internal state variable that tracks the dialog's chosen active graphic.
        """
        # print(f"Dialog TRACE: _on_active_graphic_combo_changed - Index: {index}") # Optional debug
        current_data = self.default_startup_item_combo.itemData(index)
        if current_data and isinstance(current_data, dict):
            self._current_dialog_chosen_active_graphic_relative_path = current_data.get(
                'path')
            # print(f"Dialog TRACE: Stored current dialog chosen active graphic path: {self._current_dialog_chosen_active_graphic_relative_path}") # Optional
        # Special case for "None"
        elif index == 0 and self.default_startup_item_combo.itemText(index) == "None (Show Default Text)":
            self._current_dialog_chosen_active_graphic_relative_path = None
            # print(f"Dialog TRACE: Stored current dialog chosen active graphic path: None") # Optional

        # Mark editor dirty is NOT needed here, as this is a global setting change, not an item edit.
        # The "Save" button of the dialog (QDialogButtonBox.StandardButton.Save) will handle saving this.
        # The new "Save & Apply" button will also incorporate this.

    def _speed_level_to_delay_ms(self, level: int) -> int:
        if level <= MIN_SPEED_LEVEL:
            return MAX_ACTUAL_DELAY_MS
        if level >= MAX_SPEED_LEVEL:
            return MIN_ACTUAL_DELAY_MS
        norm_level = (level - MIN_SPEED_LEVEL) / \
            (MAX_SPEED_LEVEL - MIN_SPEED_LEVEL)
        delay = MAX_ACTUAL_DELAY_MS - norm_level * \
            (MAX_ACTUAL_DELAY_MS - MIN_ACTUAL_DELAY_MS)
        return int(round(delay))

    def _delay_ms_to_speed_level(self, delay_ms: int) -> int:
        if delay_ms <= MIN_ACTUAL_DELAY_MS:
            return MAX_SPEED_LEVEL
        if delay_ms >= MAX_ACTUAL_DELAY_MS:
            return MIN_SPEED_LEVEL
        norm_delay = (delay_ms - MIN_ACTUAL_DELAY_MS) / \
            (MAX_ACTUAL_DELAY_MS - MIN_ACTUAL_DELAY_MS)
        level = MAX_SPEED_LEVEL - norm_delay * \
            (MAX_SPEED_LEVEL - MIN_SPEED_LEVEL)
        return int(round(level))

    def _create_text_editor_panel(self) -> QWidget:
        widget = QWidget()
        # <<< NEW: Set minimum height for this content panel
        widget.setMinimumHeight(INNER_EDITOR_PANEL_CONTENT_MIN_HEIGHT)
        # <<< NEW: Allow vertical expansion within its minimum height constraint
        widget.setSizePolicy(QSizePolicy.Policy.Preferred,
                             QSizePolicy.Policy.Expanding)

        text_editor_layout = QVBoxLayout(widget)
        text_editor_layout.setContentsMargins(0, 0, 0, 0)  # Keep tight margins

        text_editor_layout.addWidget(QLabel("Item Name (used for filename):"))
        self.item_name_edit = QLineEdit()
        text_editor_layout.addWidget(self.item_name_edit)

        text_editor_layout.addWidget(QLabel("Text Content:"))
        self.text_content_edit = QLineEdit()
        text_editor_layout.addWidget(self.text_content_edit)

        font_layout = QHBoxLayout()
        font_layout.addWidget(QLabel("Font:"))
        self.text_font_family_combo = QFontComboBox()
        self.text_font_family_combo.setFontFilters(
            QFontComboBox.FontFilter.ScalableFonts)
        font_layout.addWidget(self.text_font_family_combo, 1)
        font_layout.addWidget(QLabel("Size:"))
        self.text_font_size_spinbox = QSpinBox()
        self.text_font_size_spinbox.setRange(6, 72)
        self.text_font_size_spinbox.setSuffix(" px")
        font_layout.addWidget(self.text_font_size_spinbox)
        text_editor_layout.addLayout(font_layout)

        self.text_scroll_checkbox = QCheckBox("Scroll This Text")
        text_editor_layout.addWidget(self.text_scroll_checkbox)
        alignment_layout = QHBoxLayout()
        alignment_layout.addWidget(QLabel("Alignment (if not scrolling):"))
        self.text_alignment_combo = QComboBox()
        self.text_alignment_combo.addItems(["Left", "Center", "Right"])
        alignment_layout.addWidget(self.text_alignment_combo, 1)
        text_editor_layout.addLayout(alignment_layout)

        anim_params_group = QGroupBox("Scroll Animation Parameters")
        # Let this group box take preferred size, the outer panel has the min height
        anim_params_group.setSizePolicy(
            QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        anim_params_layout = QVBoxLayout(anim_params_group)
        self.text_anim_override_speed_checkbox = QCheckBox(
            "Override Global Scroll Speed for this item")
        anim_params_layout.addWidget(self.text_anim_override_speed_checkbox)
        item_speed_layout = QHBoxLayout()
        item_speed_layout.addWidget(QLabel("Item Scroll Speed (per step):"))
        self.text_anim_item_scroll_speed_spinbox = QSpinBox()
        self.text_anim_item_scroll_speed_spinbox.setRange(
            MIN_ACTUAL_DELAY_MS, MAX_ACTUAL_DELAY_MS)
        self.text_anim_item_scroll_speed_spinbox.setSuffix(" ms")
        self.text_anim_item_scroll_speed_spinbox.setSingleStep(10)
        item_speed_layout.addWidget(self.text_anim_item_scroll_speed_spinbox)
        anim_params_layout.addLayout(item_speed_layout)
        pause_ends_layout = QHBoxLayout()
        pause_ends_layout.addWidget(QLabel("Pause at Scroll Ends:"))
        self.text_anim_pause_at_ends_spinbox = QSpinBox()
        self.text_anim_pause_at_ends_spinbox.setRange(0, 5000)
        self.text_anim_pause_at_ends_spinbox.setSuffix(" ms")
        self.text_anim_pause_at_ends_spinbox.setSingleStep(100)
        pause_ends_layout.addWidget(self.text_anim_pause_at_ends_spinbox)
        anim_params_layout.addLayout(pause_ends_layout)
        text_editor_layout.addWidget(anim_params_group)

        text_editor_layout.addStretch(1)  # Push content up

        self.save_this_text_item_button = QPushButton("💾 Save Text Item")
        text_editor_layout.addWidget(
            self.save_this_text_item_button, 0, Qt.AlignmentFlag.AlignRight)
        return widget

# Replacement for 'def _create_animation_editor_panel(...)' in OLEDCustomizerDialog class


    def _create_animation_editor_panel(self) -> QWidget:
        page_widget = QWidget()
        # Increased for new controls
        page_widget.setMinimumHeight(INNER_EDITOR_PANEL_CONTENT_MIN_HEIGHT + 100)
        page_widget.setSizePolicy(
            QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
        outer_layout = QVBoxLayout(page_widget)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(8)
        scroll_content_widget = QWidget()
        anim_editor_layout = QVBoxLayout(scroll_content_widget)
        anim_editor_layout.setContentsMargins(5, 5, 5, 5)
        anim_editor_layout.setSpacing(8)

        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("Animation Name:"))
        self.anim_item_name_edit = QLineEdit()
        name_layout.addWidget(self.anim_item_name_edit)
        anim_editor_layout.addLayout(name_layout)

        source_file_layout = QHBoxLayout()
        source_file_layout.addWidget(QLabel("Source Image/GIF:"))
        self.anim_source_file_label = QLabel("<i>No file selected</i>")
        self.anim_source_file_label.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.anim_source_file_label.setWordWrap(True)
        source_file_layout.addWidget(self.anim_source_file_label, 1)
        self.anim_browse_button = QPushButton("Browse...")
        source_file_layout.addWidget(self.anim_browse_button)
        anim_editor_layout.addLayout(source_file_layout)

        # --- Import & Processing Options Group ---
        import_options_group = QGroupBox("Import & Processing Options")
        import_options_group.setSizePolicy(
            QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        import_options_layout = QGridLayout(import_options_group)

        row = 0
        import_options_layout.addWidget(QLabel("Resize Mode:"), row, 0)
        self.anim_resize_mode_combo = QComboBox()
        self.anim_resize_mode_combo.addItems(
            ["Stretch to Fit", "Fit (Keep Aspect, Pad)", "Crop to Center"])
        import_options_layout.addWidget(self.anim_resize_mode_combo, row, 1, 1, 2)

        # --- Dithering Controls ---
        row += 1
        import_options_layout.addWidget(QLabel("Monochrome:"), row, 0)
        self.anim_mono_conversion_combo = QComboBox()
        self.anim_mono_conversion_combo.addItems([
            "Floyd-Steinberg Dither", "Atkinson Dither", "Simple Threshold",
            "Ordered Dither (Bayer 2x2)", "Ordered Dither (Bayer 4x4)", "Ordered Dither (Bayer 8x8)"
        ])
        import_options_layout.addWidget(
            self.anim_mono_conversion_combo, row, 1, 1, 2)

        row += 1  # Dither Strength (conditionally visible)
        self.anim_dither_strength_widget = QWidget()
        dither_strength_layout_internal = QHBoxLayout(
            self.anim_dither_strength_widget)
        dither_strength_layout_internal.setContentsMargins(0, 0, 0, 0)
        dither_strength_layout_internal.addWidget(QLabel("Dither Strength:"))
        self.anim_dither_strength_slider = QSlider(Qt.Orientation.Horizontal)
        self.anim_dither_strength_slider.setRange(0, 100)  # 0% to 100%
        self.anim_dither_strength_slider.setValue(100)
        self.anim_dither_strength_slider.setToolTip(
            "Adjust strength for error diffusion dithers (0=Threshold, 100=Full)")
        dither_strength_layout_internal.addWidget(
            self.anim_dither_strength_slider, 1)
        self.anim_dither_strength_value_label = QLabel("100%")
        self.anim_dither_strength_value_label.setMinimumWidth(45)
        self.anim_dither_strength_value_label.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        dither_strength_layout_internal.addWidget(
            self.anim_dither_strength_value_label)
        import_options_layout.addWidget(
            self.anim_dither_strength_widget, row, 0, 1, 3)
        self.anim_dither_strength_widget.setVisible(False)  # Initially hidden

        row += 1  # Threshold (conditionally visible)
        self.anim_threshold_widget = QWidget()
        threshold_layout_internal = QHBoxLayout(self.anim_threshold_widget)
        threshold_layout_internal.setContentsMargins(0, 0, 0, 0)
        threshold_layout_internal.addWidget(QLabel("Threshold (0-255):"))
        self.anim_threshold_slider = QSlider(Qt.Orientation.Horizontal)
        self.anim_threshold_slider.setRange(0, 255)
        self.anim_threshold_slider.setValue(128)
        threshold_layout_internal.addWidget(self.anim_threshold_slider, 1)
        self.anim_threshold_value_label = QLabel("128")
        self.anim_threshold_value_label.setMinimumWidth(30)
        self.anim_threshold_value_label.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        threshold_layout_internal.addWidget(self.anim_threshold_value_label)
        import_options_layout.addWidget(self.anim_threshold_widget, row, 0, 1, 3)
        self.anim_threshold_widget.setVisible(False)

        # --- Tonal & Detail Adjustments ---
        row += 1
        import_options_layout.addWidget(QLabel("Brightness:"), row, 0)
        self.anim_brightness_slider = QSlider(Qt.Orientation.Horizontal)
        self.anim_brightness_slider.setRange(0, 200)
        self.anim_brightness_slider.setValue(100)
        self.anim_brightness_slider.setToolTip(
            "Adjust image brightness (0.0x to 2.0x)")
        import_options_layout.addWidget(self.anim_brightness_slider, row, 1)
        self.anim_brightness_value_label = QLabel("1.00x")
        self.anim_brightness_value_label.setMinimumWidth(45)
        self.anim_brightness_value_label.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        import_options_layout.addWidget(self.anim_brightness_value_label, row, 2)

        row += 1
        import_options_layout.addWidget(QLabel("Gamma:"), row, 0)
        self.anim_gamma_slider = QSlider(Qt.Orientation.Horizontal)
        self.anim_gamma_slider.setRange(50, 200)  # Represents 0.5 to 2.0
        self.anim_gamma_slider.setValue(100)    # Default to 1.0
        self.anim_gamma_slider.setToolTip("Adjust image gamma (0.5 to 2.0)")
        import_options_layout.addWidget(self.anim_gamma_slider, row, 1)
        self.anim_gamma_value_label = QLabel("1.00")
        self.anim_gamma_value_label.setMinimumWidth(45)
        self.anim_gamma_value_label.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        import_options_layout.addWidget(self.anim_gamma_value_label, row, 2)

        row += 1
        import_options_layout.addWidget(QLabel("Contrast:"), row, 0)
        self.anim_contrast_slider = QSlider(Qt.Orientation.Horizontal)
        self.anim_contrast_slider.setRange(0, 200)
        self.anim_contrast_slider.setValue(100)
        self.anim_contrast_slider.setToolTip(
            "Adjust image contrast (0.0x to 2.0x)")
        import_options_layout.addWidget(self.anim_contrast_slider, row, 1)
        self.anim_contrast_value_label = QLabel("1.00x")
        self.anim_contrast_value_label.setMinimumWidth(45)
        self.anim_contrast_value_label.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        import_options_layout.addWidget(self.anim_contrast_value_label, row, 2)

        row += 1
        import_options_layout.addWidget(QLabel("Sharpen:"), row, 0)
        self.anim_sharpen_slider = QSlider(Qt.Orientation.Horizontal)
        self.anim_sharpen_slider.setRange(0, 100)
        self.anim_sharpen_slider.setValue(0)
        self.anim_sharpen_slider.setToolTip(
            "Adjust image sharpness (0 for none, higher for more)")
        import_options_layout.addWidget(self.anim_sharpen_slider, row, 1)
        self.anim_sharpen_value_label = QLabel("0")
        self.anim_sharpen_value_label.setMinimumWidth(45)
        self.anim_sharpen_value_label.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        import_options_layout.addWidget(self.anim_sharpen_value_label, row, 2)

        row += 1
        import_options_layout.addWidget(QLabel("Pre-Dither Blur:"), row, 0)
        self.anim_blur_slider = QSlider(Qt.Orientation.Horizontal)
        self.anim_blur_slider.setRange(0, 20)  # Represents 0.0 to 2.0 radius
        self.anim_blur_slider.setValue(0)    # Default to no blur
        self.anim_blur_slider.setToolTip(
        "Apply Gaussian blur before dithering (0 for none)")
        import_options_layout.addWidget(self.anim_blur_slider, row, 1)
        self.anim_blur_value_label = QLabel("0.0")
        self.anim_blur_value_label.setMinimumWidth(45)
        self.anim_blur_value_label.setAlignment(
        Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        import_options_layout.addWidget(self.anim_blur_value_label, row, 2)

        # --- Noise Controls ---
        row += 1
        import_options_layout.addWidget(QLabel("Noise Type:"), row, 0)
        self.anim_noise_type_combo = QComboBox()
        self.anim_noise_type_combo.addItems(
            ["Off", "Pre-Dither (Subtle)", "Post-Dither (Grainy)"])
        import_options_layout.addWidget(self.anim_noise_type_combo, row, 1, 1, 2)

        row += 1
        import_options_layout.addWidget(QLabel("Noise Amount:"), row, 0)
        self.anim_noise_amount_slider = QSlider(Qt.Orientation.Horizontal)
        self.anim_noise_amount_slider.setRange(0, 100)  # Percentage
        self.anim_noise_amount_slider.setValue(0)
        self.anim_noise_amount_slider.setToolTip(
            "Amount of noise to apply (0-100%)")
        import_options_layout.addWidget(self.anim_noise_amount_slider, row, 1)
        self.anim_noise_amount_value_label = QLabel("0%")
        self.anim_noise_amount_value_label.setMinimumWidth(45)
        self.anim_noise_amount_value_label.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        import_options_layout.addWidget(self.anim_noise_amount_value_label, row, 2)
        # Enabled when noise type is not "Off"
        self.anim_noise_amount_slider.setEnabled(False)

        row += 1
        self.anim_invert_colors_checkbox = QCheckBox("Invert Colors (Black/White)")
        import_options_layout.addWidget(
            self.anim_invert_colors_checkbox, row, 0, 1, 3)

        import_options_layout.setColumnStretch(1, 1)
        anim_editor_layout.addWidget(import_options_group)

        # --- Playback Options Group (Remains the same) ---
        playback_options_group = QGroupBox("Playback Options")
        playback_options_group.setSizePolicy(
            QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        playback_options_layout = QGridLayout(playback_options_group)
        playback_options_layout.addWidget(QLabel("Target Playback FPS:"), 0, 0)
        self.anim_playback_fps_spinbox = QSpinBox()
        self.anim_playback_fps_spinbox.setRange(1, 60)
        self.anim_playback_fps_spinbox.setValue(15)
        playback_options_layout.addWidget(self.anim_playback_fps_spinbox, 0, 1)
        playback_options_layout.addWidget(QLabel("Loop Behavior:"), 1, 0)
        self.anim_loop_behavior_combo = QComboBox()
        self.anim_loop_behavior_combo.addItems(["Loop Infinitely", "Play Once"])
        playback_options_layout.addWidget(self.anim_loop_behavior_combo, 1, 1)
        playback_options_layout.setColumnStretch(1, 1)
        anim_editor_layout.addWidget(playback_options_group)

        action_buttons_layout = QHBoxLayout()
        self.anim_process_button = QPushButton("Process Frames")
        action_buttons_layout.addWidget(self.anim_process_button)
        self.anim_play_preview_button = QPushButton("▶️ Play Preview")
        self.anim_play_preview_button.setEnabled(False)
        self.anim_play_preview_button.setCheckable(True)
        action_buttons_layout.addWidget(self.anim_play_preview_button)
        anim_editor_layout.addLayout(action_buttons_layout)

        self.anim_frame_info_label = QLabel("Frames: N/A | Source FPS: N/A")
        self.anim_frame_info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        anim_editor_layout.addWidget(self.anim_frame_info_label)
        anim_editor_layout.addStretch(1)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setWidget(scroll_content_widget)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        scroll_area.setSizePolicy(
            QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
        outer_layout.addWidget(scroll_area, 1)

        self.save_this_animation_button = QPushButton("💾 Save Animation Item")
        outer_layout.addWidget(self.save_this_animation_button,
                               0, Qt.AlignmentFlag.AlignRight)

        if not IMAGE_PROCESSING_AVAILABLE:
            for w_idx, w in enumerate([
                self.anim_browse_button, self.anim_resize_mode_combo, self.anim_mono_conversion_combo,
                self.anim_threshold_slider, self.anim_brightness_slider, self.anim_sharpen_slider,
                self.anim_gamma_slider, self.anim_blur_slider, self.anim_noise_amount_slider,
                self.anim_noise_type_combo, self.anim_dither_strength_slider, self.anim_contrast_slider,
                self.anim_invert_colors_checkbox, self.anim_process_button,
                self.anim_play_preview_button, self.save_this_animation_button
            ]):
                if w:
                    w.setEnabled(False)
            if self.anim_source_file_label:
                self.anim_source_file_label.setText(
                    "<i>Image processing unavailable</i>")
        return page_widget

    def _update_editor_panel_visibility(self, item_type_to_show: str | None):
        if item_type_to_show is not None:
            if self._is_library_preview_anim_playing and self._library_preview_anim_timer.isActive():
                self._library_preview_anim_timer.stop()
            self._is_library_preview_anim_playing = False
            self._current_library_preview_anim_frames = None

        if self._is_anim_editor_preview_playing and self._anim_editor_preview_timer.isActive():
            self._anim_editor_preview_timer.stop()
        self._is_anim_editor_preview_playing = False
        if self.anim_play_preview_button:
            self.anim_play_preview_button.setChecked(False)
            self.anim_play_preview_button.setText("▶️ Play Preview")

        current_editor_index = -1
        new_title = "Item Editor"
        newly_selected_editor_page: QWidget | None = None  # Ensure type hint

        if item_type_to_show == 'text':
            current_editor_index = 0
            new_title = "Text Item Editor"
            newly_selected_editor_page = self.text_editor_widget
        elif item_type_to_show == 'animation':
            current_editor_index = 1
            new_title = "Animation Item Editor"
            newly_selected_editor_page = self.animation_editor_widget_container

        if current_editor_index != -1 and newly_selected_editor_page is not None:
            self.editor_stacked_widget.setCurrentWidget(
                newly_selected_editor_page)
            self.item_editor_group.setTitle(new_title)
            self.item_editor_group.setVisible(True)

            # The newly_selected_editor_page now has a fixed minimumHeight.
            # Its layout should adjust internally. We might just need to ensure
            # the QStackedWidget and QGroupBox are aware of any potential size hint changes
            # if the content *could* grow beyond the minimum.
            if newly_selected_editor_page.layout():
                newly_selected_editor_page.layout().activate()
            # newly_selected_editor_page.adjustSize() # This might not be needed if minHeight is set

            # self.editor_stacked_widget.updateGeometry() # Let parent layouts adjust
            # self.item_editor_group.updateGeometry()     # Let parent layouts adjust

        else:
            self.item_editor_group.setVisible(False)
            self._current_edited_item_path = None
            self._current_edited_item_type = None
            self._is_editing_new_item = False
            self._editor_has_unsaved_changes = False
            self._update_preview()

        self._update_save_this_item_button_state()
        # No self.adjustSize() for the whole dialog here, as its size is meant to be more fixed.
        # The splitter will manage the internal distribution.
        if self.layout() is not None:
            self.layout().activate()  # Ensure dialog's main layout is active

    def _on_anim_contrast_slider_changed(self, value: int):
        if not IMAGE_PROCESSING_AVAILABLE or self.anim_contrast_value_label is None:
            return
        # Convert slider value (0-200) to contrast factor (0.0 to 2.0)
        # Slider value 100 corresponds to factor 1.0
        contrast_factor = value / 100.0
        self.anim_contrast_value_label.setText(f"{contrast_factor:.2f}x")
        self._mark_editor_dirty_if_needed()  # Changing contrast is an edit

    # New method to be ADDED to OLEDCustomizerDialog class
    def _on_anim_brightness_slider_changed(self, value: int):
        if not IMAGE_PROCESSING_AVAILABLE or self.anim_brightness_value_label is None:
            return
        # Convert slider value (0-200) to factor (0.0x to 2.0x), 100 = 1.0x
        brightness_factor = value / 100.0
        self.anim_brightness_value_label.setText(f"{brightness_factor:.2f}x")
        self._mark_editor_dirty_if_needed() # Changing brightness is an edit that requires reprocessing

    # New method to be ADDED to OLEDCustomizerDialog class
    def _on_anim_sharpen_slider_changed(self, value: int):
        if not IMAGE_PROCESSING_AVAILABLE or self.anim_sharpen_value_label is None:
            return
        # Slider value is 0-100.
        # We display the raw value for now. The image_processing module will interpret this.
        # (e.g., 0 = no sharpen, 100 = max sharpen effect as defined there)
        self.anim_sharpen_value_label.setText(str(value))
        self._mark_editor_dirty_if_needed() # Changing sharpen is an edit that requires reprocessing

    # New slot methods to be ADDED to OLEDCustomizerDialog class
    def _on_anim_gamma_slider_changed(self, value: int):
        if not IMAGE_PROCESSING_AVAILABLE or self.anim_gamma_value_label is None:
            return
        # Slider value 50-200 maps to gamma 0.5-2.0
        gamma_factor = value / 100.0
        self.anim_gamma_value_label.setText(f"{gamma_factor:.2f}")
        self._mark_editor_dirty_if_needed()

    def _on_anim_blur_slider_changed(self, value: int):
        if not IMAGE_PROCESSING_AVAILABLE or self.anim_blur_value_label is None:
            return
        # Slider value 0-20 maps to blur radius 0.0-2.0
        blur_radius = value / 10.0
        self.anim_blur_value_label.setText(f"{blur_radius:.1f}")
        self._mark_editor_dirty_if_needed()


    def _on_anim_noise_type_changed(self):
        if not IMAGE_PROCESSING_AVAILABLE or self.anim_noise_amount_slider is None:
            return
        noise_type = self.anim_noise_type_combo.currentText()
        self.anim_noise_amount_slider.setEnabled(noise_type != "Off")
        self._mark_editor_dirty_if_needed()


    def _on_anim_noise_amount_slider_changed(self, value: int):
        if not IMAGE_PROCESSING_AVAILABLE or self.anim_noise_amount_value_label is None:
            return
        self.anim_noise_amount_value_label.setText(f"{value}%")
        self._mark_editor_dirty_if_needed()


    def _on_anim_dither_strength_slider_changed(self, value: int):
        if not IMAGE_PROCESSING_AVAILABLE or self.anim_dither_strength_value_label is None:
            return
        self.anim_dither_strength_value_label.setText(f"{value}%")
        self._mark_editor_dirty_if_needed()

    # Replacement for 'def _connect_signals(...)' in OLEDCustomizerDialog class
# Replacement for 'def _connect_signals(...)' in OLEDCustomizerDialog class
    def _connect_signals(self):
        # Global Settings
        self.global_scroll_speed_level_slider.valueChanged.connect(self._on_global_scroll_speed_level_slider_changed)
        self.default_startup_item_combo.currentIndexChanged.connect(self._on_active_graphic_combo_changed) # Already connected in _init_ui, ensure one place or check if redundant

        # Library
        self.item_library_list.currentItemChanged.connect(self._on_library_selection_changed)
        self.item_library_list.itemDoubleClicked.connect(self._handle_edit_selected_item)
        self.new_text_item_button.clicked.connect(self._handle_new_text_item)
        self.new_anim_item_button.clicked.connect(self._handle_new_animation_item)
        self.edit_selected_item_button.clicked.connect(self._handle_edit_selected_item)
        self.delete_selected_item_button.clicked.connect(self._handle_delete_selected_item)

        # Text Editor
        self.item_name_edit.textChanged.connect(self._mark_editor_dirty_if_needed)
        self.text_content_edit.textChanged.connect(self._mark_editor_dirty_if_needed)
        self.text_font_family_combo.currentFontChanged.connect(self._mark_editor_dirty_if_needed)
        self.text_font_size_spinbox.valueChanged.connect(self._mark_editor_dirty_if_needed)
        self.text_scroll_checkbox.stateChanged.connect(self._on_text_scroll_checkbox_changed)
        self.text_alignment_combo.currentIndexChanged.connect(self._mark_editor_dirty_if_needed)
        self.text_anim_override_speed_checkbox.stateChanged.connect(self._on_text_anim_override_speed_changed)
        self.text_anim_item_scroll_speed_spinbox.valueChanged.connect(self._mark_editor_dirty_if_needed)
        self.text_anim_pause_at_ends_spinbox.valueChanged.connect(self._mark_editor_dirty_if_needed)
        self.save_this_text_item_button.clicked.connect(self._handle_save_this_text_item)

        # Animation Editor
        if IMAGE_PROCESSING_AVAILABLE:
            self.anim_item_name_edit.textChanged.connect(self._mark_editor_dirty_if_needed)
            self.anim_browse_button.clicked.connect(self._handle_anim_browse_source_file)
            self.anim_resize_mode_combo.currentIndexChanged.connect(self._mark_editor_dirty_if_needed)
            self.anim_mono_conversion_combo.currentIndexChanged.connect(self._on_anim_mono_conversion_changed)
            self.anim_threshold_slider.valueChanged.connect(self._on_anim_threshold_slider_changed)
            if self.anim_contrast_slider:
                self.anim_contrast_slider.valueChanged.connect(self._on_anim_contrast_slider_changed)
            if self.anim_brightness_slider:
                self.anim_brightness_slider.valueChanged.connect(self._on_anim_brightness_slider_changed)
            if self.anim_sharpen_slider:
                self.anim_sharpen_slider.valueChanged.connect(self._on_anim_sharpen_slider_changed)
            # --- Connect New Animation Editor Controls ---
            if self.anim_gamma_slider:
                self.anim_gamma_slider.valueChanged.connect(self._on_anim_gamma_slider_changed)
            if self.anim_blur_slider:
                self.anim_blur_slider.valueChanged.connect(self._on_anim_blur_slider_changed)
            if self.anim_noise_type_combo:
                self.anim_noise_type_combo.currentIndexChanged.connect(self._on_anim_noise_type_changed)
            if self.anim_noise_amount_slider:
                self.anim_noise_amount_slider.valueChanged.connect(self._on_anim_noise_amount_slider_changed)
            if self.anim_dither_strength_slider: # This is inside anim_dither_strength_widget
                 self.anim_dither_strength_slider.valueChanged.connect(self._on_anim_dither_strength_slider_changed)
            # --- End Connect New Animation Editor Controls ---
            self.anim_invert_colors_checkbox.stateChanged.connect(self._mark_editor_dirty_if_needed)
            self.anim_playback_fps_spinbox.valueChanged.connect(self._mark_editor_dirty_if_needed)
            self.anim_loop_behavior_combo.currentIndexChanged.connect(self._mark_editor_dirty_if_needed)
            self.anim_process_button.clicked.connect(self._handle_anim_process_and_preview)
            if self.anim_play_preview_button:
                self.anim_play_preview_button.toggled.connect(self._handle_anim_play_pause_preview_toggled)
            self.save_this_animation_button.clicked.connect(self._handle_save_this_animation_item)

        # Dialog Buttons
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        if self.save_and_apply_button:
            self.save_and_apply_button.clicked.connect(self._handle_save_and_apply)

    def _load_initial_data(self):
        initial_speed_level = self._delay_ms_to_speed_level(
            self._initial_global_scroll_delay_ms)
        self.global_scroll_speed_level_slider.setValue(initial_speed_level)
        self._update_scroll_speed_display_label(
            initial_speed_level, self._initial_global_scroll_delay_ms)

        self._populate_font_family_combo()
        # This also populates default_startup_item_combo
        self._populate_item_library_list()

        # Use the new attribute name to find the initially selected active graphic
        if self._initial_active_graphic_path:  # <<< CHANGED ATTRIBUTE NAME
            for i in range(self.default_startup_item_combo.count()):
                item_data = self.default_startup_item_combo.itemData(i)
                # <<< CHANGED
                if item_data and item_data.get('path') == self._initial_active_graphic_path:
                    self.default_startup_item_combo.setCurrentIndex(i)
                    break

        self._update_library_button_states()
        self._update_save_this_item_button_state()

    def _populate_font_family_combo(self):
        self.text_font_family_combo.blockSignals(True)
        # QFontComboBox populates itself. We just set a default.
        default_font = QFont("Arial")  # A common default
        self.text_font_family_combo.setCurrentFont(default_font)
        # If Arial wasn't found, it might select something else or be empty.
        # This is generally okay as QFontComboBox handles fallbacks.
        self.text_font_family_combo.blockSignals(False)

    def _populate_item_library_list(self):
        # print("DIALOG DEBUG: _populate_item_library_list CALLED")

        if self.default_startup_item_combo is None or self.item_library_list is None:
            print("DIALOG CRITICAL ERROR: UI elements for library list/combo not initialized before _populate_item_library_list! Aborting population.")
            return

        self.default_startup_item_combo.blockSignals(True)
        self.item_library_list.clear()
        self.default_startup_item_combo.clear()
        self.default_startup_item_combo.addItem(
            "None (Show Default Text)", userData=None)

        os.makedirs(self.text_items_dir, exist_ok=True)
        os.makedirs(self.animation_items_dir, exist_ok=True)

        found_items_for_combo = []

        item_sources = [
            {"dir": self.text_items_dir, "internal_type": "text", "base_label": "Text"},
            {"dir": self.animation_items_dir,
                "internal_type": "animation", "base_label": "Animation"}
        ]

        for source in item_sources:
            if not os.path.isdir(source["dir"]):
                continue
            for filename in os.listdir(source["dir"]):
                if filename.endswith(".json"):
                    filepath = os.path.join(source["dir"], filename)
                    display_label_suffix = source["base_label"]
                    item_name_from_json = os.path.splitext(filename)[0]
                    actual_item_type_from_json = None

                    try:
                        with open(filepath, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                        item_name_from_json = data.get(
                            "item_name", item_name_from_json)
                        actual_item_type_from_json = data.get("item_type")

                        if actual_item_type_from_json == "image_animation":
                            frames = data.get("frames_logical")
                            if isinstance(frames, list) and len(frames) == 1:
                                display_label_suffix = "Image"
                            else:
                                display_label_suffix = "Animation"
                        elif actual_item_type_from_json == "text":
                            display_label_suffix = "Text"

                    except Exception as e_read:
                        print(
                            f"Dialog Info: Could not properly read JSON content from {filepath}: {e_read}. Using default label '{display_label_suffix}'.")

                    qlist_item_text = f"{item_name_from_json} ({display_label_suffix})"
                    qlist_item = QListWidgetItem(qlist_item_text)
                    relative_path = os.path.join(
                        os.path.basename(source["dir"]), filename)
                    qlist_item.setData(Qt.ItemDataRole.UserRole, {
                        'path': filepath, 'relative_path': relative_path,
                        'type': source['internal_type'], 'name': item_name_from_json
                    })
                    self.item_library_list.addItem(qlist_item)

                    found_items_for_combo.append({
                        'name': item_name_from_json,
                        'path': os.path.join(os.path.basename(source["dir"]), filename),
                        'type_label_for_combo': display_label_suffix,
                        'internal_type_for_combo': source['internal_type']
                    })

        found_items_for_combo.sort(key=lambda x: x['name'].lower())

        for item_info in found_items_for_combo:
            combo_text = f"{item_info['name']} ({item_info['type_label_for_combo']})"
            self.default_startup_item_combo.addItem(
                combo_text,
                userData={
                    'path': item_info['path'], 'type': item_info['internal_type_for_combo']}
            )

        restored_selection = False
        if self._current_dialog_chosen_active_graphic_relative_path:
            for i in range(self.default_startup_item_combo.count()):
                item_data = self.default_startup_item_combo.itemData(i)
                if item_data and isinstance(item_data, dict) and \
                   item_data.get('path') == self._current_dialog_chosen_active_graphic_relative_path:
                    self.default_startup_item_combo.setCurrentIndex(i)
                    restored_selection = True
                    break
        if not restored_selection and self._current_dialog_chosen_active_graphic_relative_path is not None:
            self.default_startup_item_combo.setCurrentIndex(0)
            self._current_dialog_chosen_active_graphic_relative_path = None
        elif self._current_dialog_chosen_active_graphic_relative_path is None and self.default_startup_item_combo.count() > 0:
            self.default_startup_item_combo.setCurrentIndex(0)

        self.default_startup_item_combo.blockSignals(False)
        # print("DIALOG DEBUG: _populate_item_library_list FINISHED")

    def _play_next_library_preview_anim_frame(self):
        if not self._is_library_preview_anim_playing or \
           not self._current_library_preview_anim_frames or \
           len(self._current_library_preview_anim_frames) == 0:
            if self._library_preview_anim_timer.isActive():
                self._library_preview_anim_timer.stop()
            self._is_library_preview_anim_playing = False
            # print("Dialog DEBUG: Library preview animation stopped (no frames or not playing).") # Optional
            return

        # Loop or stop based on behavior and frame index
        if self._current_library_preview_anim_frame_index >= len(self._current_library_preview_anim_frames):
            if self._library_preview_anim_loop_behavior == "Loop Infinitely":
                self._current_library_preview_anim_frame_index = 0
            elif self._library_preview_anim_loop_behavior == "Play Once":
                self._library_preview_anim_timer.stop()
                self._is_library_preview_anim_playing = False
                # print("Dialog DEBUG: Library preview animation finished (Play Once).") # Optional
                # Optionally, keep showing the last frame statically.
                # For now, it will just stop, and the preview label won't update further from this timer.
                # If another action clears the preview label, it will go blank.
                return
            else:  # Should not happen, but stop if unknown loop behavior
                self._library_preview_anim_timer.stop()
                self._is_library_preview_anim_playing = False
                return

        # After loop/stop check, ensure index is still valid (e.g., if frames became empty)
        if self._current_library_preview_anim_frame_index >= len(self._current_library_preview_anim_frames):
            self._library_preview_anim_timer.stop()
            self._is_library_preview_anim_playing = False
            return

        logical_frame_to_display = self._current_library_preview_anim_frames[
            self._current_library_preview_anim_frame_index]

        if self.oled_preview_label:
            try:
                # Render this logical_frame onto self.oled_preview_label (MAIN PREVIEW)
                q_image = QImage(NATIVE_OLED_WIDTH,
                                 NATIVE_OLED_HEIGHT, QImage.Format.Format_Mono)
                q_image.fill(0)  # Black background
                for y, row_str in enumerate(logical_frame_to_display):
                    if y >= NATIVE_OLED_HEIGHT:
                        break
                    for x, pixel_char in enumerate(row_str):
                        if x >= NATIVE_OLED_WIDTH:
                            break
                        if pixel_char == '1':
                            q_image.setPixel(x, y, 1)  # White pixel

                native_pixmap = QPixmap.fromImage(q_image)
                scaled_pixmap = native_pixmap.scaled(
                    self.oled_preview_label.size(),
                    # Or KeepAspectRatio depending on preference
                    Qt.AspectRatioMode.IgnoreAspectRatio,
                    Qt.TransformationMode.FastTransformation
                )
                self.oled_preview_label.setPixmap(scaled_pixmap)
            except Exception as e:
                print(
                    f"Dialog ERROR: Exception in _play_next_library_preview_anim_frame rendering: {e}")
                self.oled_preview_label.setText(
                    "Preview Error")  # Show error on label

        self._current_library_preview_anim_frame_index += 1

    def _update_library_button_states(self):
        selected_item = self.item_library_list.currentItem()
        can_edit_delete = selected_item is not None
        self.edit_selected_item_button.setEnabled(can_edit_delete)
        self.delete_selected_item_button.setEnabled(can_edit_delete)

    def _on_library_selection_changed(self, current: QListWidgetItem | None, previous: QListWidgetItem | None):
        self._update_library_button_states()

        if self.item_editor_group.isVisible() and self._editor_has_unsaved_changes:
            if self._prompt_save_unsaved_editor_changes() == QMessageBox.StandardButton.Cancel:
                if previous:
                    self.item_library_list.setCurrentItem(previous)
                return

        # Stop all previous preview activity
        if self._preview_scroll_timer.isActive():
            self._preview_scroll_timer.stop()
        self._preview_is_scrolling = False
        self._current_preview_font_object = None
        if self._anim_editor_preview_timer.isActive():
            self._anim_editor_preview_timer.stop()
        self._is_anim_editor_preview_playing = False
        if self.anim_play_preview_button:
            self.anim_play_preview_button.setChecked(False)
            self.anim_play_preview_button.setText("▶️ Play Preview")
        if self._library_preview_anim_timer.isActive():
            self._library_preview_anim_timer.stop()
        self._is_library_preview_anim_playing = False
        self._current_library_preview_anim_frames = None

        self._current_preview_anim_logical_frame = None
        self._update_editor_panel_visibility(None)

        if current:
            item_data_from_list = current.data(Qt.ItemDataRole.UserRole)
            if item_data_from_list:
                item_full_path = item_data_from_list.get('path')
                # This 'type' comes from _populate_item_library_list
                item_type_from_list_data = item_data_from_list.get('type')
                item_name_debug = item_data_from_list.get('name', 'Unknown')

                print(
                    f"Dialog DEBUG: Library selection: Name='{item_name_debug}', Type from list data='{item_type_from_list_data}', Path='{item_full_path}'")

                # Ensure we use a consistent check, perhaps by normalizing the type string
                # The 'type' in item_data_from_list should be "text" or "animation" (from your _populate_item_library_list)
                # The JSON item_type is "image_animation". This might be the mismatch.
                # Let's load the JSON to get its actual item_type if path is valid.

                actual_item_json_type = None
                if item_full_path and os.path.exists(item_full_path):
                    try:
                        with open(item_full_path, 'r', encoding='utf-8') as f_json:
                            item_json_content = json.load(f_json)
                        actual_item_json_type = item_json_content.get(
                            "item_type")
                        print(
                            f"Dialog DEBUG: Loaded JSON for '{item_name_debug}', actual JSON item_type='{actual_item_json_type}'")
                    except Exception as e_load:
                        print(
                            f"Dialog ERROR: Could not load JSON for '{item_name_debug}' from '{item_full_path}': {e_load}")
                        self._clear_preview_label_content()
                        return  # Stop if we can't load the item

                # Now, use actual_item_json_type for the decision
                if actual_item_json_type == "image_animation":  # <<< CHECK AGAINST JSON's TYPE
                    print(
                        f"Dialog INFO: Handling library item '{item_name_debug}' as image_animation for preview.")
                    # ... (rest of your animation loading and timer starting logic)
                    # This part from previous suggestion should be mostly correct:
                    try:
                        # anim_item_json is already loaded as item_json_content
                        self._current_library_preview_anim_frames = item_json_content.get(
                            "frames_logical")
                        import_opts = item_json_content.get(
                            "import_options_used", {})
                        self._library_preview_anim_fps = float(
                            import_opts.get("playback_fps", 15.0))
                        if self._library_preview_anim_fps <= 0:
                            self._library_preview_anim_fps = 15.0
                        self._library_preview_anim_loop_behavior = import_opts.get(
                            "loop_behavior", "Loop Infinitely")

                        if self._current_library_preview_anim_frames and len(self._current_library_preview_anim_frames) > 0:
                            self._current_library_preview_anim_frame_index = 0
                            self._is_library_preview_anim_playing = True
                            interval_ms = int(
                                1000.0 / self._library_preview_anim_fps)
                            self._library_preview_anim_timer.start(
                                max(33, interval_ms))
                            self._play_next_library_preview_anim_frame()
                        else:
                            print(
                                f"Dialog WARNING: Library animation item '{item_name_debug}' has no frames.")
                            self._clear_preview_label_content()
                    except Exception as e:
                        print(
                            f"Dialog ERROR: Processing library animation '{item_name_debug}' for preview: {e}")
                        self._clear_preview_label_content()

                elif actual_item_json_type == "text":
                    print(
                        f"Dialog INFO: Handling library item '{item_name_debug}' as text for preview.")
                    self._preview_item_from_path(
                        item_full_path)  # This will render text

                else:
                    print(
                        f"Dialog WARNING: Unknown JSON item type '{actual_item_json_type}' for '{item_name_debug}'. Clearing preview.")
                    self._clear_preview_label_content()
            else:
                self._clear_preview_label_content()
        else:
            self._clear_preview_label_content()

    def _clear_preview_label_content(self):
        """Clears the main oled_preview_label to black."""
        if self.oled_preview_label:  # Check if it exists
            pixmap = QPixmap(self.oled_preview_label.size())
            pixmap.fill(Qt.GlobalColor.black)
            self.oled_preview_label.setPixmap(pixmap)
            # Ensure no fallback text shows (like "Preview")
            self.oled_preview_label.setText("")

    def _clear_text_editor_fields(self):
        self.item_name_edit.setText("")
        self.text_content_edit.clear()
        self.text_font_family_combo.setCurrentFont(
            QFont("Arial"))  # Default font
        self.text_font_size_spinbox.setValue(10)
        self.text_scroll_checkbox.setChecked(True)
        self.text_alignment_combo.setCurrentIndex(1)  # Center
        self.text_anim_override_speed_checkbox.setChecked(False)

        # Use the initial global scroll delay as the default for item-specific speed
        default_delay = self._initial_global_scroll_delay_ms if hasattr(
            self, '_initial_global_scroll_delay_ms') else DEFAULT_GLOBAL_SCROLL_DELAY_MS_FALLBACK
        self.text_anim_item_scroll_speed_spinbox.setValue(default_delay)
        self.text_anim_pause_at_ends_spinbox.setValue(1000)  # Default pause

        self._on_text_scroll_checkbox_changed()  # Update dependent UI enabled states
        self._on_text_anim_override_speed_changed()

    def _clear_animation_editor_fields(self):
        if not IMAGE_PROCESSING_AVAILABLE:
            return

        if hasattr(self, '_anim_editor_preview_timer') and self._anim_editor_preview_timer.isActive():
            self._anim_editor_preview_timer.stop()
        self._is_anim_editor_preview_playing = False
        self._current_anim_editor_preview_frame_index = 0

        if hasattr(self, 'anim_play_preview_button') and self.anim_play_preview_button:
            self.anim_play_preview_button.setChecked(False)
            self.anim_play_preview_button.setText("▶️ Play Preview")
            self.anim_play_preview_button.setEnabled(False)

        if self.anim_item_name_edit:
            self.anim_item_name_edit.setText("")
        if self.anim_source_file_label:
            self.anim_source_file_label.setText("<i>No file selected</i>")
            self.anim_source_file_label.setToolTip("")
        self._current_anim_source_filepath = None

        if self.anim_resize_mode_combo:
            self.anim_resize_mode_combo.setCurrentIndex(0)
        if self.anim_mono_conversion_combo:
            self.anim_mono_conversion_combo.setCurrentIndex(0)
        if self.anim_threshold_slider:
            self.anim_threshold_slider.setValue(128)
        if self.anim_threshold_value_label:
            self.anim_threshold_value_label.setText("128")
        if self.anim_invert_colors_checkbox:
            self.anim_invert_colors_checkbox.setChecked(False)

        if self.anim_brightness_slider:
            self.anim_brightness_slider.setValue(100)
        if self.anim_brightness_value_label:
            self.anim_brightness_value_label.setText("1.00x")
        if self.anim_sharpen_slider:
            self.anim_sharpen_slider.setValue(0)
        if self.anim_sharpen_value_label:
            self.anim_sharpen_value_label.setText("0")
        if self.anim_contrast_slider:
            self.anim_contrast_slider.setValue(100)
        if self.anim_contrast_value_label:
            self.anim_contrast_value_label.setText("1.00x")

        # --- Reset New Controls ---
        if self.anim_gamma_slider:
            self.anim_gamma_slider.setValue(100)  # 1.0 gamma
        if self.anim_gamma_value_label:
            self.anim_gamma_value_label.setText("1.00")
        if self.anim_blur_slider:
            self.anim_blur_slider.setValue(0)  # 0.0 blur radius
        if self.anim_blur_value_label:
            self.anim_blur_value_label.setText("0.0")
        if self.anim_noise_type_combo:
            self.anim_noise_type_combo.setCurrentIndex(0)  # "Off"
        if self.anim_noise_amount_slider:
            self.anim_noise_amount_slider.setValue(0)
        if self.anim_noise_amount_value_label:
            self.anim_noise_amount_value_label.setText("0%")
        if self.anim_dither_strength_slider:
            self.anim_dither_strength_slider.setValue(100)  # 100%
        if self.anim_dither_strength_value_label:
            self.anim_dither_strength_value_label.setText("100%")
        # --- End Reset New Controls ---

        if self.anim_playback_fps_spinbox:
            self.anim_playback_fps_spinbox.setValue(15)
        if self.anim_loop_behavior_combo:
            self.anim_loop_behavior_combo.setCurrentIndex(0)

        if self.anim_frame_info_label:
            self.anim_frame_info_label.setText("Frames: N/A | Source FPS: N/A")
        self._processed_logical_frames = None
        self._processed_anim_source_fps = None
        self._processed_anim_source_loop_count = None
        self._on_anim_mono_conversion_changed()

    def _handle_new_text_item(self):
        if self._prompt_save_unsaved_editor_changes() == QMessageBox.StandardButton.Cancel:
            return

        self.item_library_list.clearSelection()  # Deselect any library item
        self._clear_text_editor_fields()
        self._update_editor_panel_visibility('text')  # Show text editor

        self._current_edited_item_path = None
        self._current_edited_item_type = 'text'
        self._is_editing_new_item = True
        # New item isn't "dirty" until changed
        self._editor_has_unsaved_changes = False

        self.item_name_edit.setFocus()
        self._update_save_this_item_button_state()
        self._update_preview()  # Preview the blank/default state

    def _handle_new_animation_item(self):
        if not IMAGE_PROCESSING_AVAILABLE:
            QMessageBox.warning(self, "Feature Disabled",
                                "Image processing module is not available.")
            return

        if self._prompt_save_unsaved_editor_changes() == QMessageBox.StandardButton.Cancel:
            return

        self.item_library_list.clearSelection()
        self._clear_animation_editor_fields()
        self._update_editor_panel_visibility(
            'animation')  # Show animation editor

        self._current_edited_item_path = None
        self._current_edited_item_type = 'animation'
        self._is_editing_new_item = True
        self._editor_has_unsaved_changes = False

        self.anim_item_name_edit.setFocus()
        self._update_save_this_item_button_state()
        self._update_preview()  # Preview (will be blank for new animation)

    def _handle_anim_play_pause_preview_toggled(self, checked: bool):
        if not IMAGE_PROCESSING_AVAILABLE or not self._processed_logical_frames or len(self._processed_logical_frames) == 0:
            self.anim_play_preview_button.setChecked(
                False)  # Uncheck if no frames
            self.anim_play_preview_button.setText("▶️ Play Preview")
            self._is_anim_editor_preview_playing = False
            self._anim_editor_preview_timer.stop()
            return

        self._is_anim_editor_preview_playing = checked

        if self._is_anim_editor_preview_playing:
            self.anim_play_preview_button.setText("⏸️ Pause Preview")

            # If starting from a paused state and not at the beginning, let it resume.
            # Otherwise, (re)start from frame 0.
            if self._current_anim_editor_preview_frame_index >= len(self._processed_logical_frames) or \
               self._current_anim_editor_preview_frame_index == 0:  # If at end or explicitly stopped/restarted
                self._current_anim_editor_preview_frame_index = 0

            target_fps = self.anim_playback_fps_spinbox.value()
            if target_fps <= 0:
                target_fps = 15  # Fallback FPS
            interval_ms = int(1000.0 / target_fps)
            min_interval = 33  # approx 30 FPS
            self._anim_editor_preview_timer.start(
                max(min_interval, interval_ms))
            # Show current/first frame immediately
            self._play_next_anim_editor_preview_frame()
        else:  # Paused
            self.anim_play_preview_button.setText("▶️ Play Preview")
            self._anim_editor_preview_timer.stop()

    def _play_next_anim_editor_preview_frame(self):
        if not self._is_anim_editor_preview_playing or \
           not self._processed_logical_frames or \
           self._current_anim_editor_preview_frame_index >= len(self._processed_logical_frames):

            if self._is_anim_editor_preview_playing and \
               self._processed_logical_frames and \
               self._current_anim_editor_preview_frame_index >= len(self._processed_logical_frames):

                if self.anim_loop_behavior_combo.currentText() == "Play Once":
                    self._anim_editor_preview_timer.stop()
                    self._is_anim_editor_preview_playing = False
                    self.anim_play_preview_button.setChecked(False)
                    self.anim_play_preview_button.setText("▶️ Play Preview")
                    self._current_anim_editor_preview_frame_index = 0
                    # Show last frame statically on the main preview
                    if self._processed_logical_frames:
                        self._current_preview_anim_logical_frame = self._processed_logical_frames[-1]
                        self._render_preview_frame()  # Update main preview label
                    return

            if not self._is_anim_editor_preview_playing:
                self.anim_play_preview_button.setChecked(False)
                self.anim_play_preview_button.setText("▶️ Play Preview")

            if self._anim_editor_preview_timer.isActive() and not self._is_anim_editor_preview_playing:
                self._anim_editor_preview_timer.stop()
            return

        logical_frame_to_display = self._processed_logical_frames[
            self._current_anim_editor_preview_frame_index]

        # --- Render this logical_frame onto self.oled_preview_label (MAIN PREVIEW) ---
        if self.oled_preview_label:
            q_image = QImage(NATIVE_OLED_WIDTH,
                             NATIVE_OLED_HEIGHT, QImage.Format.Format_Mono)
            q_image.fill(0)
            for y, row_str in enumerate(logical_frame_to_display):
                if y >= NATIVE_OLED_HEIGHT:
                    break
                for x, pixel_char in enumerate(row_str):
                    if x >= NATIVE_OLED_WIDTH:
                        break
                    if pixel_char == '1':
                        q_image.setPixel(x, y, 1)

            native_pixmap = QPixmap.fromImage(q_image)
            scaled_pixmap = native_pixmap.scaled(
                self.oled_preview_label.size(),
                # Or KeepAspectRatio depending on preference
                Qt.AspectRatioMode.IgnoreAspectRatio,
                Qt.TransformationMode.FastTransformation
            )
            self.oled_preview_label.setPixmap(scaled_pixmap)
        # --- END RENDER TO MAIN PREVIEW ---

        self._current_anim_editor_preview_frame_index += 1

        if self._current_anim_editor_preview_frame_index >= len(self._processed_logical_frames):
            if self.anim_loop_behavior_combo.currentText() == "Loop Infinitely":
                self._current_anim_editor_preview_frame_index = 0
            # "Play Once" is handled at the start of the next tick or by button toggle

    def _handle_edit_selected_item(self):
        selected_qlist_item = self.item_library_list.currentItem()
        if not selected_qlist_item:
            QMessageBox.information(
                self, "Edit Item", "Please select an item from the library to edit.")
            return

        if self._prompt_save_unsaved_editor_changes() == QMessageBox.StandardButton.Cancel:
            return

        item_data_from_list = selected_qlist_item.data(
            Qt.ItemDataRole.UserRole)
        item_full_path = item_data_from_list.get('path')
        item_type = item_data_from_list.get('type')

        if not item_full_path or not os.path.exists(item_full_path):
            QMessageBox.warning(
                self, "Edit Error", f"Selected item file not found at '{item_full_path}'.")
            self._populate_item_library_list()
            return

        self._current_edited_item_path = item_full_path
        self._current_edited_item_type = item_type
        self._is_editing_new_item = False  # Editing an existing item

        try:
            with open(item_full_path, 'r', encoding='utf-8') as f:
                item_json_data = json.load(f)
        except Exception as e:
            QMessageBox.critical(
                self, "Load Error", f"Could not load item data from '{item_full_path}': {e}")
            self._update_editor_panel_visibility(None)  # Hide editor on error
            return

        if item_type == 'text':
            self._update_editor_panel_visibility('text')
            self.item_editor_group.setTitle(
                f"Edit Text Item: {item_json_data.get('item_name', 'Untitled')}")
            self._load_text_item_into_editor(item_json_data)
        elif item_type == 'animation':
            if IMAGE_PROCESSING_AVAILABLE:
                self._update_editor_panel_visibility('animation')
                self.item_editor_group.setTitle(
                    f"Edit Animation Item: {item_json_data.get('item_name', 'Untitled')}")
                self._load_animation_item_into_editor(item_json_data)
            else:
                QMessageBox.warning(
                    self, "Edit Error", "Cannot edit animation items: Image processing module unavailable.")
                self._update_editor_panel_visibility(None)
                return
        else:
            QMessageBox.warning(
                self, "Edit Error", f"Unsupported item type for editing: {item_type}")
            self._update_editor_panel_visibility(None)
            return

        self._editor_has_unsaved_changes = False  # Reset flag after loading
        self._update_save_this_item_button_state()
        self._update_preview()

    def _load_text_item_into_editor(self, data: dict):
        self.item_name_edit.setText(data.get("item_name", ""))
        self.text_content_edit.setText(data.get("text_content", ""))

        font_family = data.get("font_family", "Arial")
        font_size = data.get("font_size_px", 10)
        self.text_font_family_combo.setCurrentFont(QFont(font_family))
        self.text_font_size_spinbox.setValue(font_size)

        anim_style = data.get("animation_style", "scroll_left")
        self.text_scroll_checkbox.setChecked(anim_style != "static")

        anim_params = data.get("animation_params", {})
        override_speed = anim_params.get("speed_override_ms") is not None
        self.text_anim_override_speed_checkbox.setChecked(override_speed)

        # Use current global scroll speed as fallback if item doesn't have override
        default_speed_for_item = self._initial_global_scroll_delay_ms if hasattr(
            self, '_initial_global_scroll_delay_ms') else DEFAULT_GLOBAL_SCROLL_DELAY_MS_FALLBACK
        self.text_anim_item_scroll_speed_spinbox.setValue(
            anim_params.get("speed_override_ms", default_speed_for_item))
        self.text_anim_pause_at_ends_spinbox.setValue(
            anim_params.get("pause_at_ends_ms", 1000))

        alignment_str = data.get("alignment", "center").lower()
        align_map = {"left": 0, "center": 1, "right": 2}
        self.text_alignment_combo.setCurrentIndex(
            align_map.get(alignment_str, 1))  # Default to center

        # Update UI based on loaded scroll state
        self._on_text_scroll_checkbox_changed()
        # Update UI based on loaded override state
        self._on_text_anim_override_speed_changed()



    def _load_animation_item_into_editor(self, data: dict):
        if not IMAGE_PROCESSING_AVAILABLE:
            return

        if self._is_anim_editor_preview_playing:
            self._anim_editor_preview_timer.stop()
        self._is_anim_editor_preview_playing = False
        if self.anim_play_preview_button:
            self.anim_play_preview_button.setChecked(False)
            self.anim_play_preview_button.setText("▶️ Play Preview")
        self._current_anim_editor_preview_frame_index = 0

        self.anim_item_name_edit.setText(data.get("item_name", ""))
        source_ref = data.get("source_file_path_for_reference", "N/A")
        base_source_ref = os.path.basename(source_ref)
        self.anim_source_file_label.setText(base_source_ref if len(base_source_ref) < 40 else "..." + base_source_ref[-37:])
        self.anim_source_file_label.setToolTip(source_ref)
        self._current_anim_source_filepath = source_ref if os.path.exists(source_ref) else None

        import_opts = data.get("import_options_used", {})
        self.anim_resize_mode_combo.setCurrentText(import_opts.get("resize_mode", "Stretch to Fit"))
        mono_mode_val = import_opts.get("mono_conversion_mode", import_opts.get("dithering", "Floyd-Steinberg Dither"))
        combo_items = [self.anim_mono_conversion_combo.itemText(i) for i in range(self.anim_mono_conversion_combo.count())]
        if mono_mode_val not in combo_items:
            mono_mode_val = combo_items[0] if combo_items else "Floyd-Steinberg Dither"
        self.anim_mono_conversion_combo.setCurrentText(mono_mode_val)

        self.anim_threshold_slider.setValue(import_opts.get("threshold_value", 128))
        self.anim_invert_colors_checkbox.setChecked(import_opts.get("invert_colors", False))

        contrast_factor_loaded = float(import_opts.get("contrast_factor", 1.0))
        if self.anim_contrast_slider:
            self.anim_contrast_slider.setValue(int(round(contrast_factor_loaded * 100)))
        if self.anim_contrast_value_label:
            self.anim_contrast_value_label.setText(f"{contrast_factor_loaded:.2f}x")

        brightness_factor_loaded = float(import_opts.get("brightness_factor", 1.0))
        if self.anim_brightness_slider:
            self.anim_brightness_slider.setValue(int(round(brightness_factor_loaded * 100)))
        if self.anim_brightness_value_label:
            self.anim_brightness_value_label.setText(f"{brightness_factor_loaded:.2f}x")

        sharpen_factor_loaded = float(import_opts.get("sharpen_factor", 0.0))
        if self.anim_sharpen_slider:
            self.anim_sharpen_slider.setValue(int(round(sharpen_factor_loaded)))
        if self.anim_sharpen_value_label:
            self.anim_sharpen_value_label.setText(str(int(round(sharpen_factor_loaded))))

        # --- Load New Control Values ---
        gamma_value_loaded = float(import_opts.get("gamma_value", 1.0))  # Default to 1.0 (no change)
        if self.anim_gamma_slider:
            self.anim_gamma_slider.setValue(int(round(gamma_value_loaded * 100)))
        if self.anim_gamma_value_label:
            self.anim_gamma_value_label.setText(f"{gamma_value_loaded:.2f}")

        blur_radius_loaded = float(import_opts.get("blur_radius", 0.0))  # Default to 0.0 (no blur)
        if self.anim_blur_slider:
            self.anim_blur_slider.setValue(int(round(blur_radius_loaded * 10)))
        if self.anim_blur_value_label:
            self.anim_blur_value_label.setText(f"{blur_radius_loaded:.1f}")

        noise_type_loaded = import_opts.get("noise_type", "Off")
        if self.anim_noise_type_combo:
            self.anim_noise_type_combo.setCurrentText(noise_type_loaded)

        noise_amount_loaded = int(import_opts.get("noise_amount", 0))
        if self.anim_noise_amount_slider:
            self.anim_noise_amount_slider.setValue(noise_amount_loaded)
        if self.anim_noise_amount_value_label:
            self.anim_noise_amount_value_label.setText(f"{noise_amount_loaded}%")
        if self.anim_noise_amount_slider:
            self.anim_noise_amount_slider.setEnabled(noise_type_loaded != "Off")

        dither_strength_loaded = float(import_opts.get("dither_strength", 1.0))  # Default to 1.0 (100%)
        if self.anim_dither_strength_slider:
            self.anim_dither_strength_slider.setValue(int(round(dither_strength_loaded * 100)))
        if self.anim_dither_strength_value_label:
            self.anim_dither_strength_value_label.setText(f"{int(round(dither_strength_loaded * 100))}%")
        # --- End Load New Control Values ---

        self.anim_playback_fps_spinbox.setValue(import_opts.get("playback_fps", 15))
        self.anim_loop_behavior_combo.setCurrentText(import_opts.get("loop_behavior", "Loop Infinitely"))

        self._on_anim_mono_conversion_changed()  # This will also handle dither_strength_widget visibility

        self._processed_logical_frames = data.get("frames_logical")
        if self._processed_logical_frames:
            fps_text = f"{import_opts.get('source_fps'):.2f}" if import_opts.get('source_fps') is not None else "N/A"
            loop_text = str(import_opts.get('source_loop_count')) if import_opts.get('source_loop_count') is not None else (
                "Infinite" if import_opts.get('source_fps') is not None and import_opts.get('source_loop_count') == 0 else "N/A")
            self.anim_frame_info_label.setText(
                f"Frames: {len(self._processed_logical_frames)} | Src FPS: {fps_text} | Loop: {loop_text}")
            if self.anim_play_preview_button:
                self.anim_play_preview_button.setEnabled(True)
        else:
            self.anim_frame_info_label.setText("Frames: N/A (Reload or Re-process)")
            if self.anim_play_preview_button:
                self.anim_play_preview_button.setEnabled(False)

    def _handle_delete_selected_item(self):
        selected_qlist_item = self.item_library_list.currentItem()
        if not selected_qlist_item:
            QMessageBox.information(
                self, "Delete Item", "Please select an item to delete.")
            return

        item_data_from_list = selected_qlist_item.data(
            Qt.ItemDataRole.UserRole)
        item_name_for_prompt = item_data_from_list.get('name', 'this item')
        item_full_path_to_delete = item_data_from_list.get(
            'path')  # This is the full path

        reply = QMessageBox.question(self, "Delete Item", f"Are you sure you want to delete '{item_name_for_prompt}'?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                     QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.No:
            return

        if item_full_path_to_delete and os.path.exists(item_full_path_to_delete):
            try:
                os.remove(item_full_path_to_delete)
                QMessageBox.information(
                    self, "Delete Item", f"Item '{item_name_for_prompt}' deleted successfully.")

                # If the deleted item was being edited, clear the editor
                if self._current_edited_item_path == item_full_path_to_delete:
                    self._update_editor_panel_visibility(None)  # Hide editor
                    self._current_edited_item_path = None
                    self._current_edited_item_type = None
                    self._is_editing_new_item = False
                    # No more unsaved changes for this non-existent item
                    self._editor_has_unsaved_changes = False
            except Exception as e:
                QMessageBox.critical(self, "Delete Error",
                                     f"Could not delete item file: {e}")
        else:
            QMessageBox.warning(
                self, "Delete Error", "Item file not found or path is invalid. It might have been already deleted.")

        self._populate_item_library_list()  # Refresh list
        self._update_library_button_states()
        self._update_save_this_item_button_state()  # Update save button state

    def _preview_item_from_path(self, item_filepath: str | None):
        # This method is now primarily for previewing TEXT items from the library,
        # or for setting up the static first frame if called from _update_preview for the editor.
        # print(f"Dialog DEBUG: _preview_item_from_path called for: {item_filepath}")

        if not self.oled_preview_label:  # Should always exist after _init_ui
            self._clear_preview_label_content()  # Use the explicit clearer
            return

        # Stop any ongoing library animation preview if this is called for text.
        # (This should also be handled by the caller, _on_library_selection_changed, but good defense)
        if self._is_library_preview_anim_playing and self._library_preview_anim_timer.isActive():
            self._library_preview_anim_timer.stop()
        self._is_library_preview_anim_playing = False
        self._current_library_preview_anim_frames = None

        if not item_filepath or not os.path.exists(item_filepath):
            self._clear_preview_label_content()
            return

        try:
            with open(item_filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)

            item_type = data.get("item_type")
            item_name_debug = data.get("item_name", "Unknown")
            # print(f"Dialog DEBUG: _preview_item_from_path - Item type '{item_type}', name '{item_name_debug}'")

            self._preview_scroll_timer.stop()  # Stop any text scrolling from previous item
            self._preview_is_scrolling = False
            # self._current_preview_anim_logical_frame = None # This is for editor's static frame, not library anim
            self._current_preview_font_object = None

            if item_type == "text":
                text_to_preview = data.get("text_content", "")
                font_family = data.get("font_family", "Arial")
                font_size_px = data.get("font_size_px", 10)

                if not font_family or font_size_px <= 0:
                    self._clear_preview_label_content()
                    return

                self._current_preview_font_object = QFont(font_family)
                self._current_preview_font_object.setPixelSize(font_size_px)

                fm = QFontMetrics(self._current_preview_font_object)
                # Ensure self._preview_text_pixel_width is specific to this text preview
                preview_text_width = fm.horizontalAdvance(text_to_preview)

                # Default to static
                anim_style = data.get("animation_style", "static")
                # Use the item's scroll settings for preview
                should_scroll_preview = (anim_style == "scroll_left") and \
                    preview_text_width > NATIVE_OLED_WIDTH and \
                    text_to_preview.strip() != ""

                if should_scroll_preview:
                    self._preview_is_scrolling = True
                    self._preview_current_scroll_offset = NATIVE_OLED_WIDTH  # Start off-screen right
                    self._preview_text_pixel_width = preview_text_width  # Store for scrolling logic

                    preview_scroll_delay = self._initial_global_scroll_delay_ms  # Global default
                    anim_params = data.get("animation_params", {})
                    if anim_params.get("speed_override_ms") is not None:
                        preview_scroll_delay = anim_params.get(
                            "speed_override_ms")

                    if self._preview_scroll_timer.isActive():
                        self._preview_scroll_timer.stop()  # Defensive stop
                    self._preview_scroll_timer.start(
                        max(20, preview_scroll_delay))
                else:
                    self._preview_is_scrolling = False
                    self._preview_current_scroll_offset = 0

                # print(f"Dialog DEBUG: Text preview setup: scroll={self._preview_is_scrolling}, width={preview_text_width}")
                # Render initial state of text
                self._render_preview_frame(override_text=text_to_preview)

            # THIS METHOD NO LONGER HANDLES image_animation for library preview.
            # It's only for text, or for the static first frame from _update_preview if editor active.
            # The "Unknown library item type" warning for "animation" should now come from
            # _on_library_selection_changed if it fails to find the "image_animation" type correctly there.
            elif item_type == "image_animation":
                # If _preview_item_from_path is EVER called for an animation item (e.g. by _update_preview
                # when an editor is visible), it should only show the STATIC first frame.
                # The library selection path should NOT call this for animations.
                frames = data.get("frames_logical")
                if frames and isinstance(frames, list) and len(frames) > 0:
                    # For _render_preview_frame's static anim part
                    self._current_preview_anim_logical_frame = frames[0]
                    # print(f"Dialog DEBUG: _preview_item_from_path setting STATIC first frame for animation '{item_name_debug}'")
                else:
                    self._current_preview_anim_logical_frame = None
                self._render_preview_frame()  # Render the static first frame
            else:
                print(
                    f"Dialog WARNING: _preview_item_from_path encountered unknown item type '{item_type}' for '{item_name_debug}'. Clearing preview.")
                self._clear_preview_label_content()

        except Exception as e:
            print(
                f"Dialog ERROR: Exception in _preview_item_from_path for '{item_filepath}': {e}")
            import traceback
            traceback.print_exc()
            self._clear_preview_label_content()

    def _render_preview_frame(self, override_text: str | None = None):
        # print(f"Dialog DEBUG: _render_preview_frame called. Override text: '{override_text is not None}', PreviewFont: '{self._current_preview_font_object is not None}', AnimFrame: '{self._current_preview_anim_logical_frame is not None}'") # DEBUG
        if not self.oled_preview_label:
            return

        preview_pixmap_native = QPixmap(NATIVE_OLED_WIDTH, NATIVE_OLED_HEIGHT)
        preview_pixmap_native.fill(Qt.GlobalColor.black)
        painter = QPainter(preview_pixmap_native)

        rendered_something = False  # DEBUG flag

        if self._current_preview_font_object and (override_text is not None or self._preview_is_scrolling):
            # ... (existing text rendering logic - ensure it's correct) ...
            text_for_frame = override_text
            current_font_for_render = self._current_preview_font_object
            if override_text is None and self.item_editor_group.isVisible() and \
               self.editor_stacked_widget.currentWidget() == self.text_editor_widget:
                text_for_frame = self.text_content_edit.text()
                editor_font_family = self.text_font_family_combo.currentFont().family()
                editor_font_size = self.text_font_size_spinbox.value()
                current_font_for_render = QFont(editor_font_family)
                current_font_for_render.setPixelSize(editor_font_size)
            if text_for_frame is None or current_font_for_render is None:
                painter.end()  # Close painter before returning if nothing to render
                scaled_preview = preview_pixmap_native.scaled(self.oled_preview_label.size(
                ), Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.FastTransformation)
                self.oled_preview_label.setPixmap(scaled_preview)
                return
            painter.setFont(current_font_for_render)
            painter.setPen(QColor("white"))
            fm = painter.fontMetrics()
            text_render_y = fm.ascent() + (NATIVE_OLED_HEIGHT - fm.height()) // 2
            text_render_x = 0
            if self._preview_is_scrolling:
                text_render_x = self._preview_current_scroll_offset
            else:
                text_width = fm.horizontalAdvance(text_for_frame)
                alignment_str = "center"
                if self.item_editor_group.isVisible() and self.editor_stacked_widget.currentWidget() == self.text_editor_widget:
                    alignment_str = self.text_alignment_combo.currentText().lower()
                if text_width < NATIVE_OLED_WIDTH:
                    if alignment_str == "center":
                        text_render_x = (NATIVE_OLED_WIDTH - text_width) // 2
                    elif alignment_str == "right":
                        text_render_x = NATIVE_OLED_WIDTH - text_width
            painter.drawText(text_render_x, text_render_y, text_for_frame)
            rendered_something = True  # DEBUG

        elif self._current_preview_anim_logical_frame:  # Animation frame for main preview
            print("Dialog DEBUG: Rendering animation frame to main preview.")  # DEBUG
            q_image = QImage(NATIVE_OLED_WIDTH,
                             NATIVE_OLED_HEIGHT, QImage.Format.Format_Mono)
            q_image.fill(0)
            for y, row_str in enumerate(self._current_preview_anim_logical_frame):
                if y >= NATIVE_OLED_HEIGHT:
                    break
                for x, pixel_char in enumerate(row_str):
                    if x >= NATIVE_OLED_WIDTH:
                        break
                    if pixel_char == '1':
                        q_image.setPixel(x, y, 1)
            painter.drawImage(0, 0, q_image)
            rendered_something = True  # DEBUG

        # if not rendered_something: print("Dialog DEBUG: _render_preview_frame did not render text or anim.") # DEBUG

        painter.end()
        scaled_preview = preview_pixmap_native.scaled(
            self.oled_preview_label.size(), Qt.AspectRatioMode.IgnoreAspectRatio,
            Qt.TransformationMode.FastTransformation
        )
        self.oled_preview_label.setPixmap(scaled_preview)

    def _clear_preview(self):  # This is your existing method
        # Stop ALL preview timers
        if self._preview_scroll_timer.isActive():
            self._preview_scroll_timer.stop()
        if self._anim_editor_preview_timer.isActive():
            self._anim_editor_preview_timer.stop()
        if self._library_preview_anim_timer.isActive():
            self._library_preview_anim_timer.stop()

        self._preview_is_scrolling = False
        self._is_anim_editor_preview_playing = False
        self._is_library_preview_anim_playing = False

        self._current_preview_font_object = None
        # For static first frame from editor
        self._current_preview_anim_logical_frame = None
        self._current_library_preview_anim_frames = None  # For playing library anim

        self._clear_preview_label_content()  # Use the helper

        self._preview_text_pixel_width = 0

    def _render_preview_frame(self, override_text: str | None = None):
        if not self.oled_preview_label:
            return

        preview_pixmap_native = QPixmap(NATIVE_OLED_WIDTH, NATIVE_OLED_HEIGHT)
        preview_pixmap_native.fill(Qt.GlobalColor.black)
        painter = QPainter(preview_pixmap_native)

        text_mode_active = False
        if self._current_preview_font_object and (override_text is not None or self._preview_is_scrolling):
            text_mode_active = True
        elif self.item_editor_group.isVisible() and self.editor_stacked_widget.currentWidget() == self.text_editor_widget and self.text_content_edit and self.text_font_family_combo:
            # Check if text editor is active and has valid font info for preview
            font_family_check = self.text_font_family_combo.currentFont().family()
            font_size_check = self.text_font_size_spinbox.value()
            if font_family_check and font_size_check > 0:
                text_mode_active = True

        if text_mode_active:
            text_for_frame = override_text
            current_font_for_render = self._current_preview_font_object

            if override_text is None and self.item_editor_group.isVisible() and \
               self.editor_stacked_widget.currentWidget() == self.text_editor_widget:
                text_for_frame = self.text_content_edit.text()
                # Use font from editor if rendering editor content directly
                editor_font_family = self.text_font_family_combo.currentFont().family()
                editor_font_size = self.text_font_size_spinbox.value()
                current_font_for_render = QFont(editor_font_family)
                current_font_for_render.setPixelSize(editor_font_size)

            if text_for_frame is None or current_font_for_render is None:
                painter.end()
                scaled_preview = preview_pixmap_native.scaled(
                    self.oled_preview_label.size(), Qt.AspectRatioMode.IgnoreAspectRatio,
                    Qt.TransformationMode.FastTransformation)
                self.oled_preview_label.setPixmap(scaled_preview)
                return

            painter.setFont(current_font_for_render)
            painter.setPen(QColor("white"))
            fm = painter.fontMetrics()
            text_render_y = fm.ascent() + (NATIVE_OLED_HEIGHT - fm.height()) // 2
            text_render_x = 0

            if self._preview_is_scrolling:
                text_render_x = self._preview_current_scroll_offset
            else:
                text_width = fm.horizontalAdvance(text_for_frame)
                alignment_str = "center"
                if self.item_editor_group.isVisible() and \
                   self.editor_stacked_widget.currentWidget() == self.text_editor_widget:
                    alignment_str = self.text_alignment_combo.currentText().lower()

                if text_width < NATIVE_OLED_WIDTH:
                    if alignment_str == "center":
                        text_render_x = (NATIVE_OLED_WIDTH - text_width) // 2
                    elif alignment_str == "right":
                        text_render_x = NATIVE_OLED_WIDTH - text_width
            painter.drawText(text_render_x, text_render_y, text_for_frame)

        elif self._current_preview_anim_logical_frame:  # Animation frame for main preview
            q_image = QImage(NATIVE_OLED_WIDTH,
                             NATIVE_OLED_HEIGHT, QImage.Format.Format_Mono)
            q_image.fill(0)
            for y, row_str in enumerate(self._current_preview_anim_logical_frame):
                if y >= NATIVE_OLED_HEIGHT:
                    break
                for x, pixel_char in enumerate(row_str):
                    if x >= NATIVE_OLED_WIDTH:
                        break
                    if pixel_char == '1':
                        q_image.setPixel(x, y, 1)
            painter.drawImage(0, 0, q_image)

        painter.end()
        scaled_preview = preview_pixmap_native.scaled(
            self.oled_preview_label.size(), Qt.AspectRatioMode.IgnoreAspectRatio,
            Qt.TransformationMode.FastTransformation
        )
        self.oled_preview_label.setPixmap(scaled_preview)

    def _scroll_preview_step(self):
        if not self._preview_is_scrolling or not self._current_preview_font_object:
            self._preview_scroll_timer.stop()
            return

        self._preview_current_scroll_offset -= 2

        text_to_scroll_for_render = None
        pause_delay_ms = 1000
        step_delay_ms = self._initial_global_scroll_delay_ms

        is_editor_active_text_mode = self.item_editor_group.isVisible() and \
            self.editor_stacked_widget.currentWidget() == self.text_editor_widget and \
            self._current_edited_item_type == 'text'

        if is_editor_active_text_mode and self.text_content_edit:  # Check text_content_edit exists
            text_to_scroll_for_render = self.text_content_edit.text()
            if self.text_anim_override_speed_checkbox.isChecked():
                step_delay_ms = self.text_anim_item_scroll_speed_spinbox.value()
            pause_delay_ms = self.text_anim_pause_at_ends_spinbox.value()
        else:
            # If not editing text, we must be previewing a text item from the library that needs scrolling.
            # We need to re-fetch its content and params for scrolling.
            selected_lib_item = self.item_library_list.currentItem()
            if selected_lib_item:
                item_data_json_path = selected_lib_item.data(
                    Qt.ItemDataRole.UserRole).get('path')
                try:
                    with open(item_data_json_path, 'r') as f_item:
                        item_json = json.load(f_item)
                    if item_json.get('item_type') == 'text' and item_json.get('animation_style') != 'static':
                        text_to_scroll_for_render = item_json.get(
                            'text_content', '')
                        # Update _preview_text_pixel_width if it changed (e.g. library selection changed during scroll)
                        if self._current_preview_font_object:
                            fm = QFontMetrics(
                                self._current_preview_font_object)
                            self._preview_text_pixel_width = fm.horizontalAdvance(
                                text_to_scroll_for_render)

                        anim_params = item_json.get('animation_params', {})
                        if anim_params.get('speed_override_ms') is not None:
                            step_delay_ms = anim_params['speed_override_ms']
                        pause_delay_ms = anim_params.get(
                            'pause_at_ends_ms', 1000)
                    else:  # Not a scrollable text item from library, stop.
                        self._preview_is_scrolling = False
                        self._preview_scroll_timer.stop()
                        return
                except Exception as e:
                    print(f"Error fetching item details for scroll step: {e}")
                    self._preview_is_scrolling = False
                    self._preview_scroll_timer.stop()
                    return
            else:  # No item selected, stop scrolling.
                self._preview_is_scrolling = False
                self._preview_scroll_timer.stop()
                return

        if (self._preview_current_scroll_offset + self._preview_text_pixel_width) < 0:
            self._preview_current_scroll_offset = NATIVE_OLED_WIDTH
            self._preview_scroll_timer.setInterval(max(20, pause_delay_ms))
        else:
            self._preview_scroll_timer.setInterval(max(20, step_delay_ms))

        self._render_preview_frame(override_text=text_to_scroll_for_render)

    def _update_preview(self):
        if not self.oled_preview_label:  # Guard clause
            self._clear_preview()  # This will also try to clear the label if it exists
            return

        self._preview_scroll_timer.stop()
        self._preview_is_scrolling = False

        self._current_preview_anim_logical_frame = None
        self._current_preview_font_object = None

        if self.item_editor_group.isVisible():
            active_editor_widget = self.editor_stacked_widget.currentWidget()
            if active_editor_widget == self.text_editor_widget:
                text_to_preview = self.text_content_edit.text()
                font_family = self.text_font_family_combo.currentFont().family()
                font_size_px = self.text_font_size_spinbox.value()

                if not font_family or font_size_px <= 0:
                    self._clear_preview_label_content()  # <<< CORRECTED METHOD NAME
                    return

                self._current_preview_font_object = QFont(font_family)
                self._current_preview_font_object.setPixelSize(font_size_px)

                fm = QFontMetrics(self._current_preview_font_object)
                self._preview_text_pixel_width = fm.horizontalAdvance(
                    text_to_preview)
                should_scroll_preview = self.text_scroll_checkbox.isChecked() and \
                    self._preview_text_pixel_width > NATIVE_OLED_WIDTH and \
                    text_to_preview.strip() != ""

                if should_scroll_preview:
                    self._preview_is_scrolling = True
                    self._preview_current_scroll_offset = NATIVE_OLED_WIDTH
                    preview_scroll_delay = self._initial_global_scroll_delay_ms
                    if self.text_anim_override_speed_checkbox.isChecked():
                        preview_scroll_delay = self.text_anim_item_scroll_speed_spinbox.value()
                    self._preview_scroll_timer.start(
                        max(20, preview_scroll_delay))
                else:
                    self._preview_current_scroll_offset = 0
                self._render_preview_frame(override_text=text_to_preview)

            elif active_editor_widget == self.animation_editor_widget_container:
                if not self._is_anim_editor_preview_playing:
                    if self._processed_logical_frames and len(self._processed_logical_frames) > 0:
                        self._current_preview_anim_logical_frame = self._processed_logical_frames[
                            0]
                    self._render_preview_frame()
            else:
                self._clear_preview_label_content()  # <<< CORRECTED METHOD NAME

        else:
            selected_lib_item = self.item_library_list.currentItem()
            if selected_lib_item:
                item_data = selected_lib_item.data(Qt.ItemDataRole.UserRole)
                if item_data:  # Ensure item_data is not None
                    self._preview_item_from_path(item_data.get('path'))
                else:  # item_data was None
                    self._clear_preview_label_content()  # <<< CORRECTED METHOD NAME
            else:
                self._clear_preview_label_content()  # <<< CORRECTED METHOD NAME

    def _mark_editor_dirty_if_needed(self, *args):
        sender = self.sender()
        if sender == self.default_startup_item_combo or sender == self.global_scroll_speed_level_slider:
            return  # Global settings don't make the *item* editor dirty

        if self.item_editor_group.isVisible() and \
           (self._is_editing_new_item or self._current_edited_item_path is not None):

            self._editor_has_unsaved_changes = True
            active_editor_widget = self.editor_stacked_widget.currentWidget()

            if active_editor_widget == self.animation_editor_widget_container:
                # List of controls whose changes require reprocessing the animation
                anim_processing_option_senders = [
                    self.anim_resize_mode_combo,
                    self.anim_mono_conversion_combo,
                    self.anim_threshold_slider,
                    self.anim_invert_colors_checkbox,
                    self.anim_contrast_slider,
                    self.anim_brightness_slider,  # New
                    self.anim_sharpen_slider,    # New
                    self.anim_gamma_slider,      # New
                    self.anim_blur_slider,       # New
                    self.anim_noise_type_combo,  # New
                    self.anim_noise_amount_slider,  # New (if type isn't "Off")
                    self.anim_dither_strength_slider  # New (if visible)
                ]

                # Special handling for noise amount: only dirty if noise type is not "Off"
                if sender == self.anim_noise_amount_slider and \
                   self.anim_noise_type_combo and self.anim_noise_type_combo.currentText() == "Off":
                    # If noise type is off, changing amount doesn't invalidate frames
                    pass
                elif sender in anim_processing_option_senders:
                    if self._processed_logical_frames:
                        print(
                            "Dialog DEBUG: Animation processing option changed, invalidating processed frames.")
                        self._processed_logical_frames = None
                        self.anim_frame_info_label.setText(
                            "Frames: N/A | Options changed. Re-process.")
                        if self.anim_play_preview_button:
                            if self._is_anim_editor_preview_playing:
                                self.anim_play_preview_button.setChecked(
                                    False)  # Triggers toggled
                            self.anim_play_preview_button.setEnabled(False)
                        self._current_preview_anim_logical_frame = None
                        self._update_preview()

            self._update_save_this_item_button_state()
            # Update preview if the change doesn't automatically invalidate frames
            # (e.g., changing item name, FPS, loop behavior, or text editor fields)
            # For animation processing options, the preview is cleared/updated above when frames are invalidated.
            if not (active_editor_widget == self.animation_editor_widget_container and
                    sender in anim_processing_option_senders and
                    not (sender == self.anim_noise_amount_slider and self.anim_noise_type_combo and self.anim_noise_type_combo.currentText() == "Off")):
                self._update_preview()


    def _update_save_this_item_button_state(self):
        # This method now also controls the "Save & Apply" button state

        # Default states
        can_save_text_item_locally = False
        can_save_anim_item_locally = False
        can_apply_something = False  # For "Save & Apply"

        if not self.editor_stacked_widget:  # Should not happen if UI initialized
            if hasattr(self, 'save_this_text_item_button'):
                self.save_this_text_item_button.setEnabled(False)
            if hasattr(self, 'save_this_animation_button'):
                self.save_this_animation_button.setEnabled(False)
            if hasattr(self, 'save_and_apply_button') and self.save_and_apply_button:
                self.save_and_apply_button.setEnabled(False)
            return

        if self.item_editor_group.isVisible():  # An editor panel is active
            active_widget = self.editor_stacked_widget.currentWidget()

            if active_widget == self.text_editor_widget:
                is_name_valid = bool(self.item_name_edit.text().strip())
                # Enable local save if dirty or new, AND name is valid
                can_save_text_item_locally = (
                    self._editor_has_unsaved_changes or self._is_editing_new_item) and is_name_valid
                # Enable "Save & Apply" if editor is active and name is valid (even if not dirty, for "apply existing but maybe name changed")
                # OR if a library item is selected (for applying library item directly)
                can_apply_something = is_name_valid or (
                    self.item_library_list.currentItem() is not None)

            elif active_widget == self.animation_editor_widget_container:
                is_name_valid_anim = bool(
                    self.anim_item_name_edit.text().strip())
                has_processed_frames = self._processed_logical_frames is not None and len(
                    self._processed_logical_frames) > 0
                # Enable local save if dirty or new, AND name valid, AND frames processed
                can_save_anim_item_locally = IMAGE_PROCESSING_AVAILABLE and \
                    (self._editor_has_unsaved_changes or self._is_editing_new_item) and \
                    is_name_valid_anim and has_processed_frames
                # Enable "Save & Apply" if editor active, name valid, frames processed
                # OR if a library item is selected
                can_apply_something = (is_name_valid_anim and has_processed_frames) or \
                                      (self.item_library_list.currentItem() is not None)
        else:  # Editor is not visible, only library selection matters for "Save & Apply"
            can_apply_something = (
                self.item_library_list.currentItem() is not None)

        # Set enabled states for local save buttons
        if hasattr(self, 'save_this_text_item_button'):
            self.save_this_text_item_button.setEnabled(
                can_save_text_item_locally)
        if hasattr(self, 'save_this_animation_button'):
            self.save_this_animation_button.setEnabled(
                can_save_anim_item_locally)

        # <<< NEW: Set enabled state for "Save & Apply" button
        if hasattr(self, 'save_and_apply_button') and self.save_and_apply_button:
            self.save_and_apply_button.setEnabled(can_apply_something)

    def _on_text_scroll_checkbox_changed(self):
        is_scrolling = self.text_scroll_checkbox.isChecked()
        self.text_alignment_combo.setEnabled(not is_scrolling)
        self.text_anim_override_speed_checkbox.setEnabled(is_scrolling)
        # Update speed spinbox based on override
        self._on_text_anim_override_speed_changed()
        self.text_anim_pause_at_ends_spinbox.setEnabled(is_scrolling)
        self._mark_editor_dirty_if_needed()

    def _on_text_anim_override_speed_changed(self):
        is_override = self.text_anim_override_speed_checkbox.isChecked()
        is_scrolling = self.text_scroll_checkbox.isChecked()
        self.text_anim_item_scroll_speed_spinbox.setEnabled(
            is_override and is_scrolling)
        self._mark_editor_dirty_if_needed()

    # <<< MODIFIED: Added return type bool
    def _handle_save_this_text_item(self) -> bool:
        item_name = self.item_name_edit.text().strip()
        if not item_name:
            QMessageBox.warning(self, "Save Error",
                                "Text Item Name cannot be empty.")
            self.item_name_edit.setFocus()
            return False  # <<< MODIFIED: Return False

        text_content = self.text_content_edit.text()
        font_family = self.text_font_family_combo.currentFont().family()
        font_size = self.text_font_size_spinbox.value()
        is_scrolling = self.text_scroll_checkbox.isChecked()
        alignment = self.text_alignment_combo.currentText(
        ).lower() if not is_scrolling else "left"
        anim_style = "scroll_left" if is_scrolling else "static"

        anim_params = {}
        if is_scrolling:
            if self.text_anim_override_speed_checkbox.isChecked():
                anim_params["speed_override_ms"] = self.text_anim_item_scroll_speed_spinbox.value(
                )
            anim_params["pause_at_ends_ms"] = self.text_anim_pause_at_ends_spinbox.value()

        item_data_to_save = {
            "item_name": item_name, "item_type": "text", "text_content": text_content,
            "font_family": font_family, "font_size_px": font_size,
            "animation_style": anim_style, "animation_params": anim_params,
            "alignment": alignment
        }

        target_filepath = self._current_edited_item_path if self._current_edited_item_type == 'text' and not self._is_editing_new_item else None

        safe_filename_base = "".join(c if c.isalnum() or c in [
                                    ' ', '_', '-'] else '' for c in item_name).replace(' ', '_')
        if not safe_filename_base:
            safe_filename_base = "untitled_text_item"
        suggested_filename = f"{safe_filename_base}.json"

        if self._is_editing_new_item or \
            (target_filepath and os.path.basename(target_filepath).lower() != suggested_filename.lower()):
            save_path_suggestion = os.path.join(
                self.text_items_dir, suggested_filename)
            target_filepath_new, _ = QFileDialog.getSaveFileName(
                self, "Save Text Item As...", save_path_suggestion, "JSON files (*.json)")
            if not target_filepath_new:
                return False  # <<< MODIFIED: User cancelled Save As
            target_filepath = target_filepath_new
        elif not target_filepath:  # If it was new and somehow became None, or existing item path lost
            save_path_suggestion = os.path.join(
                self.text_items_dir, suggested_filename)
            target_filepath_new, _ = QFileDialog.getSaveFileName(
                self, "Save Text Item", save_path_suggestion, "JSON files (*.json)")
            if not target_filepath_new:
                return False  # <<< MODIFIED: User cancelled
            target_filepath = target_filepath_new

        try:
            os.makedirs(os.path.dirname(target_filepath), exist_ok=True)
            with open(target_filepath, 'w', encoding='utf-8') as f:
                json.dump(item_data_to_save, f, indent=4)

            QMessageBox.information(
                self, "Item Saved", f"Text item '{item_name}' saved successfully.")
            self._current_edited_item_path = target_filepath
            self._current_edited_item_type = 'text'
            self._is_editing_new_item = False
            self._editor_has_unsaved_changes = False
            self._update_save_this_item_button_state()
            self.item_editor_group.setTitle(
                f"Edit Text Item: {item_name}")

            self._populate_item_library_list()
            for i in range(self.item_library_list.count()):
                q_item = self.item_library_list.item(i)
                if q_item and q_item.data(Qt.ItemDataRole.UserRole).get('path') == target_filepath:
                    self.item_library_list.setCurrentItem(q_item)
                    break
            return True  # <<< MODIFIED: Return True on success
        except Exception as e:
            QMessageBox.critical(self, "Save Error",
                                 f"Failed to save text item: {e}")
            return False  # <<< MODIFIED: Return False on failure

    def _handle_save_this_animation_item(self) -> bool:
        if not IMAGE_PROCESSING_AVAILABLE:
            return False
        item_name = self.anim_item_name_edit.text().strip()
        if not item_name:
            QMessageBox.warning(self, "Save Error",
                                "Animation Item Name cannot be empty.")
            return False
        if not self._processed_logical_frames or len(self._processed_logical_frames) == 0:
            QMessageBox.warning(
                self, "Save Error", "No frames processed. Please process an image/GIF.")
            return False

        contrast_factor_to_save = self.anim_contrast_slider.value(
        )/100.0 if self.anim_contrast_slider else 1.0
        brightness_factor_to_save = self.anim_brightness_slider.value(
        )/100.0 if self.anim_brightness_slider else 1.0
        sharpen_factor_to_save = float(
            self.anim_sharpen_slider.value()) if self.anim_sharpen_slider else 0.0

        # --- Get New Parameters for Saving ---
        gamma_value_to_save = self.anim_gamma_slider.value(
        ) / 100.0 if self.anim_gamma_slider else 1.0
        blur_radius_to_save = self.anim_blur_slider.value(
        ) / 10.0 if self.anim_blur_slider else 0.0
        noise_type_to_save = self.anim_noise_type_combo.currentText(
        ) if self.anim_noise_type_combo else "Off"
        noise_amount_to_save = self.anim_noise_amount_slider.value(
        ) if self.anim_noise_amount_slider else 0
        dither_strength_to_save = self.anim_dither_strength_slider.value(
        ) / 100.0 if self.anim_dither_strength_slider and self.anim_dither_strength_widget.isVisible() else 1.0
        # --- End Get New Parameters for Saving ---

        source_fps_for_json = self._processed_anim_source_fps if isinstance(
            self._processed_anim_source_fps, (int, float)) else None
        source_loop_for_json = self._processed_anim_source_loop_count if isinstance(
            self._processed_anim_source_loop_count, int) else None

        import_options_used = {
            "resize_mode": self.anim_resize_mode_combo.currentText(),
            "mono_conversion_mode": self.anim_mono_conversion_combo.currentText(),
            "threshold_value": self.anim_threshold_slider.value() if self.anim_threshold_widget.isVisible() else 128,
            "invert_colors": self.anim_invert_colors_checkbox.isChecked(),
            "contrast_factor": contrast_factor_to_save,
            "brightness_factor": brightness_factor_to_save,
            "sharpen_factor": sharpen_factor_to_save,
            "gamma_value": gamma_value_to_save,         # Add to JSON
            "blur_radius": blur_radius_to_save,         # Add to JSON
            "noise_type": noise_type_to_save,           # Add to JSON
            "noise_amount": noise_amount_to_save,       # Add to JSON
            "dither_strength": dither_strength_to_save,  # Add to JSON
            "source_fps": source_fps_for_json,
            "source_loop_count": source_loop_for_json,
            "playback_fps": self.anim_playback_fps_spinbox.value(),
            "loop_behavior": self.anim_loop_behavior_combo.currentText()
        }
        item_data_to_save = {
            "item_name": item_name, "item_type": "image_animation",
            "source_file_path_for_reference": self._current_anim_source_filepath or "N/A",
            "import_options_used": import_options_used, "frames_logical": self._processed_logical_frames
        }

        target_filepath = self._current_edited_item_path if self._current_edited_item_type == 'animation' and not self._is_editing_new_item else None
        if self._current_edited_item_type != 'animation':
            target_filepath = None  # Ensure correct type for path reuse

        safe_filename_base = "".join(c for c in item_name if c.isalnum() or c in [
                                     ' ', '_', '-']).replace(' ', '_') or "untitled_animation"
        suggested_filename = f"{safe_filename_base}.json"

        if self._is_editing_new_item or \
           (target_filepath and os.path.basename(target_filepath).lower() != suggested_filename.lower()) or \
           (target_filepath and os.path.normpath(os.path.dirname(target_filepath)) != os.path.normpath(self.animation_items_dir)):
            save_path_suggestion = os.path.join(
                self.animation_items_dir, suggested_filename)
            target_filepath_new, _ = QFileDialog.getSaveFileName(
                self, "Save Animation Item As...", save_path_suggestion, "JSON files (*.json)")
            if not target_filepath_new:
                return False
            target_filepath = target_filepath_new
        elif not target_filepath:
            target_filepath = os.path.join(
                self.animation_items_dir, suggested_filename)

        try:
            os.makedirs(os.path.dirname(target_filepath), exist_ok=True)
            with open(target_filepath, 'w', encoding='utf-8') as f:
                json.dump(item_data_to_save, f, indent=4)
            QMessageBox.information(
                self, "Item Saved", f"Animation item '{item_name}' saved successfully.")
            self._current_edited_item_path = target_filepath
            self._current_edited_item_type = 'animation'
            self._is_editing_new_item = False
            self._editor_has_unsaved_changes = False
            self._update_save_this_item_button_state()
            self.item_editor_group.setTitle(
                f"Edit Animation Item: {item_name}")
            self._populate_item_library_list()
            for i in range(self.item_library_list.count()):
                q_item = self.item_library_list.item(i)
                list_item_data = q_item.data(Qt.ItemDataRole.UserRole)
                if list_item_data and list_item_data.get('path') == target_filepath:
                    self.item_library_list.setCurrentItem(q_item)
                    break
            return True
        except Exception as e:
            QMessageBox.critical(self, "Save Error",
                                 f"Failed to save animation item: {e}")
            return False


    def _handle_save_and_apply(self):
        """
        Handles the "Save & Apply" button click.
        1. Determines the target item (editor content or library selection).
        2. Saves the item if it's from the editor and has changes or is new.
        3. Sets the target item as the choice in the "Set as Active Graphic" dropdown.
        4. Accepts and closes the dialog.
        """
        print("Dialog TRACE: _handle_save_and_apply called.")  # Optional debug

        target_item_relative_path: str | None = None
        target_item_type_for_combo: str | None = None  # 'text' or 'animation'
        save_was_successful_or_not_needed = True

        # --- Step 1: Determine the "Target Item" ---
        is_editor_active_and_valid = False
        if self.item_editor_group.isVisible() and self._current_edited_item_type:
            if self._current_edited_item_type == 'text' and self.item_name_edit.text().strip():
                is_editor_active_and_valid = True
            elif self._current_edited_item_type == 'animation' and self.anim_item_name_edit.text().strip() and \
                    IMAGE_PROCESSING_AVAILABLE and self._processed_logical_frames:
                is_editor_active_and_valid = True

        if is_editor_active_and_valid and (self._editor_has_unsaved_changes or self._is_editing_new_item):
            # --- Editor content takes precedence ---
            # Optional debug
            print("Dialog TRACE: Save & Apply - Target is editor content.")
            if self._current_edited_item_type == 'text':
                save_was_successful_or_not_needed = self._handle_save_this_text_item()
            elif self._current_edited_item_type == 'animation':
                save_was_successful_or_not_needed = self._handle_save_this_animation_item()

            if not save_was_successful_or_not_needed:
                # Optional
                print(
                    "Dialog TRACE: Save & Apply - Save from editor failed or was cancelled. Aborting apply.")
                return  # Stop if save failed/cancelled

            # After successful save, _current_edited_item_path (full) and _current_edited_item_type are set.
            # We need the relative path for the combo box.
            if self._current_edited_item_path:
                base_dir_for_type = self.text_items_dir if self._current_edited_item_type == 'text' else self.animation_items_dir
                try:
                    # Ensure paths are normalized for robust relative path calculation
                    full_item_path_norm = os.path.normpath(
                        self._current_edited_item_path)
                    base_presets_path_norm = os.path.normpath(
                        self.user_oled_presets_base_path)
                    target_item_relative_path = os.path.relpath(
                        full_item_path_norm, base_presets_path_norm)
                    target_item_relative_path = target_item_relative_path.replace(
                        os.path.sep, '/')  # Ensure forward slashes
                    target_item_type_for_combo = self._current_edited_item_type
                    # Optional
                    print(
                        f"Dialog TRACE: Save & Apply - Saved item relative path: {target_item_relative_path}")
                except ValueError as e_rel:  # Can happen if paths are on different drives on Windows
                    print(
                        f"Dialog ERROR: Could not determine relative path for saved item '{self._current_edited_item_path}': {e_rel}")
                    QMessageBox.warning(
                        self, "Apply Error", "Could not determine relative path for the saved item. Cannot apply.")
                    return
            else:  # Should not happen if save was successful
                print(
                    "Dialog ERROR: Save & Apply - Editor save successful, but _current_edited_item_path is None.")
                return

        # Editor not active/valid, or no unsaved changes. Use library selection.
        else:
            # Optional
            print(
                "Dialog TRACE: Save & Apply - Target is library selection (or editor was clean).")
            selected_qlist_item = self.item_library_list.currentItem()
            if selected_qlist_item:
                item_data = selected_qlist_item.data(Qt.ItemDataRole.UserRole)
                if item_data:
                    target_item_relative_path = item_data.get('relative_path')
                    target_item_type_for_combo = item_data.get('type')
                    # print(f"Dialog TRACE: Save & Apply - Library item relative path: {target_item_relative_path}") # Optional
            else:  # No editor content, no library selection
                QMessageBox.information(
                    self, "Save & Apply", "Please select an item from the library or save an edited item first.")
                return

        if not target_item_relative_path:
            QMessageBox.warning(self, "Save & Apply Error",
                                "Could not determine an item to apply.")
            return

        # --- Step 4: Set "Active Graphic" Dropdown ---
        # Optional
        print(
            f"Dialog TRACE: Save & Apply - Attempting to set dropdown to: {target_item_relative_path}")
        found_in_combo = False
        for i in range(self.default_startup_item_combo.count()):
            combo_item_data = self.default_startup_item_combo.itemData(i)
            if combo_item_data and isinstance(combo_item_data, dict) and \
               combo_item_data.get('path') == target_item_relative_path:
                # Prevent _on_active_graphic_combo_changed from re-marking editor dirty if it triggers
                self.default_startup_item_combo.blockSignals(True)
                self.default_startup_item_combo.setCurrentIndex(i)
                self.default_startup_item_combo.blockSignals(False)

                # Manually update our internal tracker for the dialog's choice
                self._current_dialog_chosen_active_graphic_relative_path = target_item_relative_path
                found_in_combo = True
                # Optional
                print(
                    f"Dialog TRACE: Save & Apply - Set dropdown index to {i} for path '{target_item_relative_path}'")
                break

        if not found_in_combo:
            print(
                f"Dialog ERROR: Save & Apply - Target item '{target_item_relative_path}' not found in Active Graphic dropdown after save/selection.")
            QMessageBox.warning(
                self, "Apply Error", "Could not find the target item in the Active Graphic list after processing. Please check the library.")
            return

        # --- Step 5: Accept and Close Dialog ---
        print("Dialog TRACE: Save & Apply - Calling self.accept()")  # Optional
        self.accept()

    def _on_anim_mono_conversion_changed(self):
        if not IMAGE_PROCESSING_AVAILABLE:
            return

        current_selection = self.anim_mono_conversion_combo.currentText()
        show_threshold = (current_selection == "Simple Threshold")

        # Show Dither Strength slider for error diffusion methods
        show_dither_strength = (current_selection in [
                                "Floyd-Steinberg Dither", "Atkinson Dither"])

        visibility_changed = False
        if self.anim_threshold_widget.isVisible() != show_threshold:
            self.anim_threshold_widget.setVisible(show_threshold)
            visibility_changed = True

        if self.anim_dither_strength_widget:  # Check if it exists
            if self.anim_dither_strength_widget.isVisible() != show_dither_strength:
                self.anim_dither_strength_widget.setVisible(
                    show_dither_strength)
                visibility_changed = True

        if visibility_changed:
            # Allow the layout to adjust. The QScrollArea should handle content size changes.
            # No explicit adjustSize() on parent panels is usually needed here.
            pass

        # Always mark dirty as the option itself changed
        self._mark_editor_dirty_if_needed()


    def _on_anim_threshold_slider_changed(self, value: int):
        if not IMAGE_PROCESSING_AVAILABLE:
            return
        self.anim_threshold_value_label.setText(str(value))
        self._mark_editor_dirty_if_needed()

    def _handle_anim_browse_source_file(self):
        if not IMAGE_PROCESSING_AVAILABLE:
            return

        # Determine current directory to open file dialog
        current_browse_dir = ""
        if self._current_anim_source_filepath and os.path.exists(os.path.dirname(self._current_anim_source_filepath)):
            current_browse_dir = os.path.dirname(
                self._current_anim_source_filepath)
        # Fallback to anim items dir
        elif self.animation_items_dir and os.path.exists(self.animation_items_dir):
            current_browse_dir = self.animation_items_dir

        filepath, _ = QFileDialog.getOpenFileName(
            self, "Select Image or GIF", current_browse_dir,
            "Images (*.png *.jpg *.jpeg *.bmp *.gif);;All Files (*)"
        )

        if filepath:
            print(f"Dialog DEBUG: Browsed and selected file: {filepath}")
            self._current_anim_source_filepath = filepath
            base_name = os.path.basename(filepath)

            # Truncate displayed path if too long for the label
            display_path = base_name
            # Rough estimate for label width, adjust if necessary
            max_label_chars = 35
            if len(base_name) > max_label_chars:
                display_path = f"...{base_name[-(max_label_chars-3):]}"
            self.anim_source_file_label.setText(display_path)
            self.anim_source_file_label.setToolTip(
                filepath)  # Full path in tooltip

            # Auto-fill name if the name field is empty
            if not self.anim_item_name_edit.text().strip():
                self.anim_item_name_edit.setText(
                    os.path.splitext(base_name)[0])

            # Clear previously processed frames and related info as new source is selected
            self._processed_logical_frames = None
            self._processed_anim_source_fps = None
            self._processed_anim_source_loop_count = None

            # Update the frame info label
            self.anim_frame_info_label.setText(
                "Frames: N/A | Source FPS: N/A | Press 'Process Frames'")

            # Update the main dialog preview to show nothing or a placeholder
            self._current_preview_anim_logical_frame = None  # Clear for main preview
            self._update_preview()  # This will clear or show placeholder on main preview

            # Mark editor dirty and update save button state
            self._editor_has_unsaved_changes = True  # New source is a change
            # Save should be disabled until processed
            self._update_save_this_item_button_state()
            if self.anim_play_preview_button:  # Disable play preview until processed
                self.anim_play_preview_button.setEnabled(False)
                self.anim_play_preview_button.setChecked(False)
                self.anim_play_preview_button.setText("▶️ Play Preview")


    def _handle_anim_process_and_preview(self):
        if not IMAGE_PROCESSING_AVAILABLE or not self._current_anim_source_filepath or not os.path.exists(self._current_anim_source_filepath):
            QMessageBox.warning(self, "Processing Error",
                                "No source file selected or file not found.")
            return

        if hasattr(self, '_is_anim_editor_preview_playing') and self._is_anim_editor_preview_playing:
            if hasattr(self, '_anim_editor_preview_timer'):
                self._anim_editor_preview_timer.stop()
            self._is_anim_editor_preview_playing = False
            if hasattr(self, 'anim_play_preview_button') and self.anim_play_preview_button:
                self.anim_play_preview_button.setChecked(False)
                self.anim_play_preview_button.setText("▶️ Play Preview")
        if hasattr(self, '_current_anim_editor_preview_frame_index'):
            self._current_anim_editor_preview_frame_index = 0

        resize_mode = self.anim_resize_mode_combo.currentText()
        mono_mode = self.anim_mono_conversion_combo.currentText()
        threshold = self.anim_threshold_slider.value(
        ) if self.anim_threshold_widget.isVisible() else 128
        invert = self.anim_invert_colors_checkbox.isChecked()
        contrast_factor = self.anim_contrast_slider.value(
        ) / 100.0 if self.anim_contrast_slider else 1.0
        brightness_factor = self.anim_brightness_slider.value(
        ) / 100.0 if self.anim_brightness_slider else 1.0
        sharpen_factor = float(
            self.anim_sharpen_slider.value()) if self.anim_sharpen_slider else 0.0

        # --- Get New Parameter Values ---
        gamma_value = self.anim_gamma_slider.value(
        ) / 100.0 if self.anim_gamma_slider else 1.0
        blur_radius = self.anim_blur_slider.value() / 10.0 if self.anim_blur_slider else 0.0
        noise_type = self.anim_noise_type_combo.currentText(
        ) if self.anim_noise_type_combo else "Off"
        noise_amount = self.anim_noise_amount_slider.value(
        ) if self.anim_noise_amount_slider else 0
        dither_strength = self.anim_dither_strength_slider.value(
        ) / 100.0 if self.anim_dither_strength_slider and self.anim_dither_strength_widget.isVisible() else 1.0
        # --- End Get New Parameter Values ---

        print(f"Dialog DEBUG: Processing with: resize='{resize_mode}', mono='{mono_mode}', thresh={threshold}, invert={invert}, "
              f"contrast={contrast_factor:.2f}, brightness={brightness_factor:.2f}, sharpen={sharpen_factor}, "
              f"gamma={gamma_value:.2f}, blur={blur_radius:.1f}, noise_type='{noise_type}', noise_amt={noise_amount}, dither_str={dither_strength:.2f}")

        self.anim_process_button.setEnabled(False)
        self.anim_process_button.setText("Processing...")
        if self.oled_preview_label:
            self.oled_preview_label.setText(
                "<i>Processing image/GIF... Please wait.</i>")
            if self.oled_preview_label.pixmap() and not self.oled_preview_label.pixmap().isNull():
                self.oled_preview_label.clear()
        QApplication.processEvents()

        frames, fps, loop_count = image_processing.process_image_to_oled_data(
            filepath=self._current_anim_source_filepath,
            resize_mode=resize_mode,
            mono_conversion_mode=mono_mode,
            threshold_value=threshold,
            invert_colors=invert,
            contrast_factor=contrast_factor,
            brightness_factor=brightness_factor,
            sharpen_factor=sharpen_factor,
            gamma_value=gamma_value,          # Pass new
            blur_radius=blur_radius,          # Pass new
            noise_amount=noise_amount,        # Pass new
            noise_type=noise_type,            # Pass new
            dither_strength=dither_strength,  # Pass new
            max_frames_to_import=0
        )
        self.anim_process_button.setText("Process Frames")
        self.anim_process_button.setEnabled(True)
        if frames and len(frames) > 0:
            self._processed_logical_frames = frames
            self._processed_anim_source_fps = fps
            self._processed_anim_source_loop_count = loop_count
            fps_text = f"{fps:.2f}" if fps is not None else "N/A"
            loop_text = str(loop_count) if loop_count is not None else (
                "Infinite" if fps is not None and loop_count == 0 else "N/A")
            self.anim_frame_info_label.setText(
                f"Frames: {len(frames)} | Src FPS: {fps_text} | Loop: {loop_text}")
            if self.anim_play_preview_button:
                self.anim_play_preview_button.setEnabled(True)
            self._editor_has_unsaved_changes = True
            self._current_preview_anim_logical_frame = frames[0]
            self._update_preview()
        else:
            self._processed_logical_frames = None
            if self.anim_play_preview_button:
                self.anim_play_preview_button.setEnabled(False)
            QMessageBox.critical(
                self, "Processing Failed",  f"Could not process: {os.path.basename(self._current_anim_source_filepath or '')}")
            self.anim_frame_info_label.setText(
                "Frames: Error | Source FPS: Error")
            self._current_preview_anim_logical_frame = None
            self._update_preview()
        self._update_save_this_item_button_state()

    def _on_global_scroll_speed_level_slider_changed(self, speed_level_value: int):
        delay_ms = self._speed_level_to_delay_ms(speed_level_value)
        self._update_scroll_speed_display_label(speed_level_value, delay_ms)
        # self._initial_global_scroll_delay_ms = delay_ms # This will be set on accept()

        # Update preview scroll speed IF text editor is active and not overriding
        if self.editor_stacked_widget.currentWidget() == self.text_editor_widget and \
           self._preview_is_scrolling and not self.text_anim_override_speed_checkbox.isChecked():
            self._preview_scroll_timer.start(max(20, delay_ms))
        # No direct _mark_editor_dirty_if_needed() call here for global slider,
        # as it's a global setting, not an item edit. Accept() handles it.

    def _update_scroll_speed_display_label(self, speed_level: int, delay_ms: int):
        self.global_scroll_speed_display_label.setText(
            f"Lvl {speed_level} ({delay_ms}ms)")

    def _prompt_save_unsaved_editor_changes(self) -> QMessageBox.StandardButton:
        if not self.item_editor_group.isVisible() or not self._editor_has_unsaved_changes:
            return QMessageBox.StandardButton.NoButton

        item_name_for_prompt = "current item"
        active_editor_widget = self.editor_stacked_widget.currentWidget()
        save_handler = None

        if active_editor_widget == self.text_editor_widget:
            item_name_for_prompt = self.item_name_edit.text().strip() or "current text item"
            save_handler = self._handle_save_this_text_item
        elif active_editor_widget == self.animation_editor_widget_container and IMAGE_PROCESSING_AVAILABLE:
            item_name_for_prompt = self.anim_item_name_edit.text(
            ).strip() or "current animation item"
            save_handler = self._handle_save_this_animation_item
        else:
            return QMessageBox.StandardButton.NoButton  # No active editor to save from

        reply = QMessageBox.question(self, "Unsaved Changes",
                                     f"The '{item_name_for_prompt}' has unsaved changes. Save now?",
                                     QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel,
                                     QMessageBox.StandardButton.Save)

        if reply == QMessageBox.StandardButton.Save:
            if save_handler:
                save_handler()  # Call the appropriate save method
            # Check if save failed (e.g., user cancelled Save As)
            if self._editor_has_unsaved_changes:
                return QMessageBox.StandardButton.Cancel
            return QMessageBox.StandardButton.Save

        elif reply == QMessageBox.StandardButton.Cancel:
            return QMessageBox.StandardButton.Cancel

        # Discarded
        self._editor_has_unsaved_changes = False
        self._update_save_this_item_button_state()
        return QMessageBox.StandardButton.Discard

    def accept(self):
        if self.item_editor_group.isVisible() and self._editor_has_unsaved_changes:
            prompt_result = self._prompt_save_unsaved_editor_changes()
            if prompt_result == QMessageBox.StandardButton.Cancel:
                return

        # Stop all dialog-specific timers
        # ... (stop timers as before) ...
        if self._preview_scroll_timer.isActive():
            self._preview_scroll_timer.stop()
        if hasattr(self, '_anim_editor_preview_timer') and self._anim_editor_preview_timer.isActive():
            self._anim_editor_preview_timer.stop()
        if hasattr(self, '_library_preview_anim_timer') and self._library_preview_anim_timer.isActive():
            self._library_preview_anim_timer.stop()

        selected_active_graphic_data = self.default_startup_item_combo.currentData()
        # Ensure currentData() returns the dict {'path': relative_path, 'type': item_type} or None
        selected_active_graphic_relative_path = selected_active_graphic_data.get(
            'path') if selected_active_graphic_data else None

        current_global_delay_from_slider = self._speed_level_to_delay_ms(
            self.global_scroll_speed_level_slider.value())

        # The signal signature in MainWindow._on_oled_global_settings_changed expects:
        # (new_active_graphic_item_path: str | None, new_global_scroll_delay_ms: int)
        self.global_settings_changed.emit(
            selected_active_graphic_relative_path,
            current_global_delay_from_slider
        )
        super().accept()

    def reject(self):
        if self.item_editor_group.isVisible() and self._editor_has_unsaved_changes:
            if self._prompt_save_unsaved_editor_changes() == QMessageBox.StandardButton.Cancel:
                return

        # Stop all dialog-specific timers before rejecting
        if self._preview_scroll_timer.isActive():
            self._preview_scroll_timer.stop()
        if self._anim_editor_preview_timer.isActive():
            self._anim_editor_preview_timer.stop()
        if self._library_preview_anim_timer.isActive():
            self._library_preview_anim_timer.stop()

        self.dialog_closed.emit()
        super().reject()

    def closeEvent(self, event: QCloseEvent):
        if self.item_editor_group.isVisible() and self._editor_has_unsaved_changes:
            if self._prompt_save_unsaved_editor_changes() == QMessageBox.StandardButton.Cancel:
                event.ignore()
                return

        # Stop all dialog-specific timers on close
        if self._preview_scroll_timer.isActive():
            self._preview_scroll_timer.stop()
        if self._anim_editor_preview_timer.isActive():
            self._anim_editor_preview_timer.stop()
        if self._library_preview_anim_timer.isActive():
            self._library_preview_anim_timer.stop()

        self.dialog_closed.emit()
        super().closeEvent(event)


# Standard test harness for the dialog (ensure this is at the very end of the file, after the class definition)
if __name__ == '__main__':
    app = QApplication(sys.argv)

    # Define a temporary directory for test presets
    dummy_presets_base = os.path.join(
        os.getcwd(), "TEMP_OLED_PRESETS_TEST_FULL_DIALOG")
    dummy_text_items_dir = os.path.join(
        dummy_presets_base, USER_OLED_TEXT_ITEMS_SUBDIR)
    dummy_anim_items_dir = os.path.join(
        dummy_presets_base, USER_OLED_ANIM_ITEMS_SUBDIR)
    os.makedirs(dummy_text_items_dir, exist_ok=True)
    os.makedirs(dummy_anim_items_dir, exist_ok=True)

    # Create a dummy text item for testing
    dummy_text_item_path = os.path.join(
        dummy_text_items_dir, "greeting_test.json")
    with open(dummy_text_item_path, 'w', encoding='utf-8') as f:
        json.dump({
            "item_name": "Greeting Test", "item_type": "text", "text_content": "Hello from test JSON!",
            "font_family": "Arial", "font_size_px": 16, "animation_style": "scroll_left",
            "animation_params": {"speed_override_ms": 60, "pause_at_ends_ms": 1200}, "alignment": "left"
        }, f, indent=4)

    # Create a dummy animation item
    dummy_anim_item_path = os.path.join(
        dummy_anim_items_dir, "dummy_anim.json")
    # Create a simple logical frame (e.g., a checkerboard pattern for testing)
    dummy_logical_frame = []
    for r_idx in range(NATIVE_OLED_HEIGHT):  # Use NATIVE_OLED_HEIGHT
        row_str = ""
        for c_idx in range(NATIVE_OLED_WIDTH):  # Use NATIVE_OLED_WIDTH
            row_str += '1' if (r_idx // 8 + c_idx // 8) % 2 == 0 else '0'
        dummy_logical_frame.append(row_str)

    with open(dummy_anim_item_path, 'w', encoding='utf-8') as f:
        json.dump({
            "item_name": "Dummy Animation Test", "item_type": "image_animation",
            "source_file_path_for_reference": "N/A",
            "import_options_used": {
                "resize_mode": "Stretch to Fit",
                "mono_conversion_mode": "Floyd-Steinberg Dither",  # Default
                "contrast_factor": 1.0,
                "brightness_factor": 1.0,
                "sharpen_factor": 0.0,
                "threshold_value": 128,  # Add if missing from original test
                "invert_colors": False,  # Add if missing
                "playback_fps": 10,
                "loop_behavior": "Loop Infinitely"
            },
            # Few frames for test
            "frames_logical": [dummy_logical_frame, dummy_logical_frame]
        }, f, indent=4)

    # available_oled_items is not directly used by __init__ anymore,
    # as the dialog scans its own preset directories.

    dialog = OLEDCustomizerDialog(
        current_active_graphic_path=f"{USER_OLED_TEXT_ITEMS_SUBDIR}/greeting_test.json",
        current_global_scroll_delay_ms=150,
        available_oled_items=[],  # Pass empty list as it's not directly used by __init__
        user_oled_presets_base_path=dummy_presets_base,
        # Provide a list of font names for testing QFontComboBox if needed
        available_app_fonts=['Arial', 'Courier New',
                             'Times New Roman', 'Tom Thumb'],
        parent=None
    )

    def on_settings_changed_test(path, delay):
        print(
            f"Dialog TEST Saved: Active Graphic Relative Path='{path}', Global Scroll Delay={delay}ms")

    dialog.global_settings_changed.connect(on_settings_changed_test)

    dialog.show()
    app_result = app.exec()

    # Clean up the temporary preset directory
    import shutil
    if os.path.exists(dummy_presets_base):
        try:
            shutil.rmtree(dummy_presets_base)
            print(f"Cleaned up temporary test directory: {dummy_presets_base}")
        except Exception as e_cleanup:
            print(f"Error cleaning up test directory: {e_cleanup}")

    sys.exit(app_result)
