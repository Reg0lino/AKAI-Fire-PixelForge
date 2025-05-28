### START OF FILE gui/oled_customizer_dialog.py ###

import sys
import os
import json
from PyQt6.QtWidgets import (
    QApplication, QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QLineEdit, QPushButton,
    QDialogButtonBox, QFontComboBox, QSpinBox, QWidget, QSizePolicy, QFrame,
    QSlider, QGroupBox, QListWidget, QListWidgetItem, QSplitter, QComboBox,
    QTextEdit, QCheckBox, QFileDialog, QMessageBox, QStackedWidget
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
    print(f"OLEDCustomizerDialog WARNING: image_processing module not found: {e}. Animation import will be disabled.")
    IMAGE_PROCESSING_AVAILABLE = False
    # Minimal placeholder if image_processing is not available
    class image_processing_placeholder:
        @staticmethod
        def process_image_to_oled_data(*args, **kwargs): return None, None, None
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

PREVIEW_LABEL_SCALE_FACTOR = 2 # For the main preview label
ANIM_EDITOR_PREVIEW_WIDTH = NATIVE_OLED_WIDTH # Native size for in-editor preview
ANIM_EDITOR_PREVIEW_HEIGHT = NATIVE_OLED_HEIGHT

USER_OLED_TEXT_ITEMS_SUBDIR = "TextItems"           # <<< ADD THIS
USER_OLED_ANIM_ITEMS_SUBDIR = "ImageAnimations"     # <<< ADD THIS

MIN_SPEED_LEVEL = 1 # Example, ensure these are defined if used by sliders
MAX_SPEED_LEVEL = 20

#  Dialog Size ---
DIALOG_INITIAL_WIDTH = 850
DIALOG_INITIAL_HEIGHT = 900 
DIALOG_MINIMUM_WIDTH = 800
DIALOG_MINIMUM_HEIGHT = 850 


class OLEDCustomizerDialog(QDialog):
    global_settings_changed = pyqtSignal(str, int) # (default_item_relative_path, global_scroll_delay_ms)
    dialog_closed = pyqtSignal()

# In class OLEDCustomizerDialog(QDialog):
    # In gui/oled_customizer_dialog.py

    def __init__(self,
                 current_active_graphic_path: str | None,
                 current_global_scroll_delay_ms: int,
                 available_oled_items: list, # This is actually not used directly by the dialog anymore
                 user_oled_presets_base_path: str,
                 available_app_fonts: list[str],
                 parent: QWidget | None = None):
        super().__init__(parent)
        self.setWindowTitle("⚙️ OLED Active Graphic Manager")
        
        # --- SET INITIAL AND MINIMUM DIALOG SIZE ---
        self.resize(DIALOG_INITIAL_WIDTH, DIALOG_INITIAL_HEIGHT)
        self.setMinimumSize(DIALOG_MINIMUM_WIDTH, DIALOG_MINIMUM_HEIGHT)
        # --- END SET DIALOG SIZE ---

        self._initial_active_graphic_path = current_active_graphic_path
        self._initial_global_scroll_delay_ms = current_global_scroll_delay_ms
        
        # Store the current dialog's choice for active graphic
        self._current_dialog_chosen_active_graphic_relative_path: str | None = self._initial_active_graphic_path
        
        self.user_oled_presets_base_path = user_oled_presets_base_path
        self.text_items_dir = os.path.join(self.user_oled_presets_base_path, USER_OLED_TEXT_ITEMS_SUBDIR)
        self.animation_items_dir = os.path.join(self.user_oled_presets_base_path, USER_OLED_ANIM_ITEMS_SUBDIR)
        self.available_app_fonts = available_app_fonts

        # Declare UI Element Attributes (initialized to None or default by _init_ui)
        self.default_startup_item_combo: QComboBox
        self.global_scroll_speed_level_slider: QSlider
        self.global_scroll_speed_display_label: QLabel
        self.item_library_list: QListWidget
        self.new_text_item_button: QPushButton
        self.new_anim_item_button: QPushButton
        self.edit_selected_item_button: QPushButton
        self.delete_selected_item_button: QPushButton
        self.splitter: QSplitter
        self.item_editor_group: QGroupBox
        self.editor_stacked_widget: QStackedWidget
        self.text_editor_widget: QWidget
        self.item_name_edit: QLineEdit
        self.text_content_edit: QLineEdit
        self.text_font_family_combo: QFontComboBox
        self.text_font_size_spinbox: QSpinBox
        self.text_scroll_checkbox: QCheckBox
        self.text_alignment_combo: QComboBox
        self.text_anim_override_speed_checkbox: QCheckBox
        self.text_anim_item_scroll_speed_spinbox: QSpinBox
        self.text_anim_pause_at_ends_spinbox: QSpinBox
        self.save_this_text_item_button: QPushButton
        self.animation_editor_widget_container: QWidget
        self.anim_item_name_edit: QLineEdit
        self.anim_source_file_label: QLabel
        self.anim_browse_button: QPushButton
        self.anim_resize_mode_combo: QComboBox
        self.anim_mono_conversion_combo: QComboBox
        self.anim_threshold_widget: QWidget
        self.anim_threshold_slider: QSlider
        self.anim_threshold_value_label: QLabel
        self.anim_contrast_slider: QSlider | None = None
        self.anim_contrast_value_label: QLabel | None = None
        self.anim_invert_colors_checkbox: QCheckBox
        self.anim_playback_fps_spinbox: QSpinBox
        self.anim_loop_behavior_combo: QComboBox
        self.anim_process_button: QPushButton
        self.anim_play_preview_button: QPushButton | None = None
        self.anim_frame_info_label: QLabel
        self.save_this_animation_button: QPushButton
        self.oled_preview_label: QLabel 
        self.button_box: QDialogButtonBox
        self.save_and_apply_button: QPushButton | None = None # For Save & Apply

        # State Variables
        self._preview_scroll_timer = QTimer(self); self._preview_scroll_timer.timeout.connect(self._scroll_preview_step)
        self._preview_current_scroll_offset = 0; self._preview_text_pixel_width = 0
        self._preview_is_scrolling = False; self._current_preview_font_object = None
        self._current_preview_anim_logical_frame = None
        self._current_edited_item_path = None; self._current_edited_item_type = None
        self._is_editing_new_item = False; self._editor_has_unsaved_changes = False
        self._current_anim_source_filepath = None; self._processed_logical_frames = None
        self._processed_anim_source_fps = None; self._processed_anim_source_loop_count = None
        self._anim_editor_preview_timer = QTimer(self); self._anim_editor_preview_timer.timeout.connect(self._play_next_anim_editor_preview_frame)
        self._is_anim_editor_preview_playing = False; self._current_anim_editor_preview_frame_index = 0
        self._library_preview_anim_timer = QTimer(self); self._library_preview_anim_timer.timeout.connect(self._play_next_library_preview_anim_frame)
        self._current_library_preview_anim_frames = None; self._current_library_preview_anim_frame_index = 0
        self._library_preview_anim_fps = 15.0; self._library_preview_anim_loop_behavior = "Loop Infinitely"
        self._is_library_preview_anim_playing = False

        # Call UI setup methods
        self._init_ui() # This method will create and assign to the UI element attributes declared above
        self._connect_signals() 
        
        # Load initial data after UI is constructed
        QTimer.singleShot(0, self._load_initial_data) 
        
        # Hide editor initially
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
        self.new_anim_item_button = QPushButton("🎬 New Animation Item")
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
            self._current_dialog_chosen_active_graphic_relative_path = current_data.get('path')
            # print(f"Dialog TRACE: Stored current dialog chosen active graphic path: {self._current_dialog_chosen_active_graphic_relative_path}") # Optional
        elif index == 0 and self.default_startup_item_combo.itemText(index) == "None (Show Default Text)": # Special case for "None"
            self._current_dialog_chosen_active_graphic_relative_path = None
            # print(f"Dialog TRACE: Stored current dialog chosen active graphic path: None") # Optional
        
        # Mark editor dirty is NOT needed here, as this is a global setting change, not an item edit.
        # The "Save" button of the dialog (QDialogButtonBox.StandardButton.Save) will handle saving this.
        # The new "Save & Apply" button will also incorporate this.

    def _speed_level_to_delay_ms(self, level: int) -> int:
        if level <= MIN_SPEED_LEVEL: return MAX_ACTUAL_DELAY_MS
        if level >= MAX_SPEED_LEVEL: return MIN_ACTUAL_DELAY_MS
        norm_level = (level - MIN_SPEED_LEVEL) / (MAX_SPEED_LEVEL - MIN_SPEED_LEVEL)
        delay = MAX_ACTUAL_DELAY_MS - norm_level * (MAX_ACTUAL_DELAY_MS - MIN_ACTUAL_DELAY_MS)
        return int(round(delay))

    def _delay_ms_to_speed_level(self, delay_ms: int) -> int:
        if delay_ms <= MIN_ACTUAL_DELAY_MS: return MAX_SPEED_LEVEL
        if delay_ms >= MAX_ACTUAL_DELAY_MS: return MIN_SPEED_LEVEL
        norm_delay = (delay_ms - MIN_ACTUAL_DELAY_MS) / (MAX_ACTUAL_DELAY_MS - MIN_ACTUAL_DELAY_MS)
        level = MAX_SPEED_LEVEL - norm_delay * (MAX_SPEED_LEVEL - MIN_SPEED_LEVEL)
        return int(round(level))

    def _create_text_editor_panel(self) -> QWidget:
        widget = QWidget()
        # <<< NEW: Set minimum height for this content panel
        widget.setMinimumHeight(INNER_EDITOR_PANEL_CONTENT_MIN_HEIGHT)
        # <<< NEW: Allow vertical expansion within its minimum height constraint
        widget.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding) 

        text_editor_layout = QVBoxLayout(widget)
        text_editor_layout.setContentsMargins(0,0,0,0) # Keep tight margins

        text_editor_layout.addWidget(QLabel("Item Name (used for filename):"))
        self.item_name_edit = QLineEdit()
        text_editor_layout.addWidget(self.item_name_edit)

        text_editor_layout.addWidget(QLabel("Text Content:"))
        self.text_content_edit = QLineEdit()
        text_editor_layout.addWidget(self.text_content_edit)

        font_layout = QHBoxLayout()
        font_layout.addWidget(QLabel("Font:"))
        self.text_font_family_combo = QFontComboBox()
        self.text_font_family_combo.setFontFilters(QFontComboBox.FontFilter.ScalableFonts)
        font_layout.addWidget(self.text_font_family_combo, 1)
        font_layout.addWidget(QLabel("Size:"))
        self.text_font_size_spinbox = QSpinBox()
        self.text_font_size_spinbox.setRange(6, 72); self.text_font_size_spinbox.setSuffix(" px")
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
        anim_params_group.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        anim_params_layout = QVBoxLayout(anim_params_group)
        self.text_anim_override_speed_checkbox = QCheckBox("Override Global Scroll Speed for this item")
        anim_params_layout.addWidget(self.text_anim_override_speed_checkbox)
        item_speed_layout = QHBoxLayout()
        item_speed_layout.addWidget(QLabel("Item Scroll Speed (per step):"))
        self.text_anim_item_scroll_speed_spinbox = QSpinBox()
        self.text_anim_item_scroll_speed_spinbox.setRange(MIN_ACTUAL_DELAY_MS, MAX_ACTUAL_DELAY_MS)
        self.text_anim_item_scroll_speed_spinbox.setSuffix(" ms"); self.text_anim_item_scroll_speed_spinbox.setSingleStep(10)
        item_speed_layout.addWidget(self.text_anim_item_scroll_speed_spinbox)
        anim_params_layout.addLayout(item_speed_layout)
        pause_ends_layout = QHBoxLayout()
        pause_ends_layout.addWidget(QLabel("Pause at Scroll Ends:"))
        self.text_anim_pause_at_ends_spinbox = QSpinBox()
        self.text_anim_pause_at_ends_spinbox.setRange(0, 5000); self.text_anim_pause_at_ends_spinbox.setSuffix(" ms")
        self.text_anim_pause_at_ends_spinbox.setSingleStep(100)
        pause_ends_layout.addWidget(self.text_anim_pause_at_ends_spinbox)
        anim_params_layout.addLayout(pause_ends_layout)
        text_editor_layout.addWidget(anim_params_group)
        
        text_editor_layout.addStretch(1) # Push content up

        self.save_this_text_item_button = QPushButton("💾 Save Text Item")
        text_editor_layout.addWidget(self.save_this_text_item_button, 0, Qt.AlignmentFlag.AlignRight)
        return widget

    def _create_animation_editor_panel(self) -> QWidget:
        widget = QWidget()
        # <<< NEW: Set minimum height for this content panel
        widget.setMinimumHeight(INNER_EDITOR_PANEL_CONTENT_MIN_HEIGHT)
        # <<< NEW: Allow vertical expansion within its minimum height constraint
        widget.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)

        anim_editor_layout = QVBoxLayout(widget)
        anim_editor_layout.setContentsMargins(0, 0, 0, 0) # Keep tight margins
        anim_editor_layout.setSpacing(8)

        # --- Animation Name ---
        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("Animation Name:"))
        self.anim_item_name_edit = QLineEdit()
        name_layout.addWidget(self.anim_item_name_edit)
        anim_editor_layout.addLayout(name_layout)

        # --- Source File ---
        source_file_layout = QHBoxLayout()
        source_file_layout.addWidget(QLabel("Source Image/GIF:"))
        self.anim_source_file_label = QLabel("<i>No file selected</i>")
        self.anim_source_file_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.anim_source_file_label.setWordWrap(True)
        source_file_layout.addWidget(self.anim_source_file_label, 1)
        self.anim_browse_button = QPushButton("Browse...")
        source_file_layout.addWidget(self.anim_browse_button)
        anim_editor_layout.addLayout(source_file_layout)

        # --- Import Options Group ---
        import_options_group = QGroupBox("Import & Processing Options")
        # Let this group box take preferred size
        import_options_group.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        import_options_layout = QGridLayout(import_options_group)

        row = 0
        import_options_layout.addWidget(QLabel("Resize Mode:"), row, 0)
        self.anim_resize_mode_combo = QComboBox()
        self.anim_resize_mode_combo.addItems(["Stretch to Fit", "Fit (Keep Aspect, Pad)", "Crop to Center"])
        import_options_layout.addWidget(self.anim_resize_mode_combo, row, 1, 1, 2)
        row += 1

        import_options_layout.addWidget(QLabel("Monochrome:"), row, 0)
        self.anim_mono_conversion_combo = QComboBox()
        self.anim_mono_conversion_combo.addItems(["Floyd-Steinberg Dither", "Simple Threshold", "Ordered Dither (Bayer 4x4)"])
        import_options_layout.addWidget(self.anim_mono_conversion_combo, row, 1, 1, 2)
        row += 1

        self.anim_threshold_widget = QWidget()
        threshold_layout_internal = QHBoxLayout(self.anim_threshold_widget)
        threshold_layout_internal.setContentsMargins(0, 0, 0, 0)
        threshold_layout_internal.addWidget(QLabel("Threshold (0-255):"))
        self.anim_threshold_slider = QSlider(Qt.Orientation.Horizontal)
        self.anim_threshold_slider.setRange(0, 255); self.anim_threshold_slider.setValue(128)
        threshold_layout_internal.addWidget(self.anim_threshold_slider, 1)
        self.anim_threshold_value_label = QLabel("128")
        self.anim_threshold_value_label.setMinimumWidth(30)
        self.anim_threshold_value_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        threshold_layout_internal.addWidget(self.anim_threshold_value_label)
        import_options_layout.addWidget(self.anim_threshold_widget, row, 0, 1, 3)
        self.anim_threshold_widget.setVisible(False)
        row += 1

        import_options_layout.addWidget(QLabel("Contrast:"), row, 0)
        self.anim_contrast_slider = QSlider(Qt.Orientation.Horizontal)
        self.anim_contrast_slider.setRange(0, 200); self.anim_contrast_slider.setValue(100)
        self.anim_contrast_slider.setToolTip("Adjust image contrast before dithering (0.0x to 2.0x)")
        import_options_layout.addWidget(self.anim_contrast_slider, row, 1)
        self.anim_contrast_value_label = QLabel("1.00x")
        self.anim_contrast_value_label.setMinimumWidth(45)
        self.anim_contrast_value_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        import_options_layout.addWidget(self.anim_contrast_value_label, row, 2)
        row += 1
        
        self.anim_invert_colors_checkbox = QCheckBox("Invert Colors (Black/White)")
        import_options_layout.addWidget(self.anim_invert_colors_checkbox, row, 0, 1, 3)
        row += 1
        
        import_options_layout.setColumnStretch(1, 1)
        anim_editor_layout.addWidget(import_options_group)

        playback_options_group = QGroupBox("Playback Options")
        playback_options_layout = QGridLayout(playback_options_group)
        playback_options_layout.addWidget(QLabel("Target Playback FPS:"), 0, 0)
        self.anim_playback_fps_spinbox = QSpinBox()
        self.anim_playback_fps_spinbox.setRange(1, 60); self.anim_playback_fps_spinbox.setValue(15)
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

        anim_editor_layout.addStretch(1) # Push content up

        self.save_this_animation_button = QPushButton("💾 Save Animation Item")
        anim_editor_layout.addWidget(self.save_this_animation_button, 0, Qt.AlignmentFlag.AlignRight)

        if not IMAGE_PROCESSING_AVAILABLE:
            # Disable relevant controls if image processing is not available
            for w in [self.anim_browse_button, self.anim_resize_mode_combo, 
                      self.anim_mono_conversion_combo, self.anim_threshold_slider, 
                      self.anim_contrast_slider, self.anim_invert_colors_checkbox, 
                      self.anim_process_button, self.anim_play_preview_button,
                      self.save_this_animation_button]:
                if w: w.setEnabled(False)
            if self.anim_source_file_label: self.anim_source_file_label.setText("<i>Image processing unavailable</i>")
        return widget

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
        newly_selected_editor_page: QWidget | None = None # Ensure type hint

        if item_type_to_show == 'text':
            current_editor_index = 0 
            new_title = "Text Item Editor"
            newly_selected_editor_page = self.text_editor_widget
        elif item_type_to_show == 'animation':
            current_editor_index = 1 
            new_title = "Animation Item Editor"
            newly_selected_editor_page = self.animation_editor_widget_container
        
        if current_editor_index != -1 and newly_selected_editor_page is not None:
            self.editor_stacked_widget.setCurrentWidget(newly_selected_editor_page) 
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
        if self.layout() is not None: self.layout().activate() # Ensure dialog's main layout is active

    def _on_anim_contrast_slider_changed(self, value: int):
        if not IMAGE_PROCESSING_AVAILABLE or self.anim_contrast_value_label is None:
            return
        # Convert slider value (0-200) to contrast factor (0.0 to 2.0)
        # Slider value 100 corresponds to factor 1.0
        contrast_factor = value / 100.0
        self.anim_contrast_value_label.setText(f"{contrast_factor:.2f}x")
        self._mark_editor_dirty_if_needed()  # Changing contrast is an edit

    def _connect_signals(self):
        # Global Settings
        # self.default_startup_item_combo.currentIndexChanged.connect(self._mark_editor_dirty_if_needed) # Moved to _init_ui
        # Connection for default_startup_item_combo is now in _init_ui to update _current_dialog_chosen_active_graphic_relative_path
        self.global_scroll_speed_level_slider.valueChanged.connect(self._on_global_scroll_speed_level_slider_changed)

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

        # Animation Editor (if IMAGE_PROCESSING_AVAILABLE)
        if IMAGE_PROCESSING_AVAILABLE:
            self.anim_item_name_edit.textChanged.connect(self._mark_editor_dirty_if_needed)
            self.anim_browse_button.clicked.connect(self._handle_anim_browse_source_file)
            self.anim_resize_mode_combo.currentIndexChanged.connect(self._mark_editor_dirty_if_needed)
            self.anim_mono_conversion_combo.currentIndexChanged.connect(self._on_anim_mono_conversion_changed)
            self.anim_threshold_slider.valueChanged.connect(self._on_anim_threshold_slider_changed)
            if self.anim_contrast_slider:
                self.anim_contrast_slider.valueChanged.connect(self._on_anim_contrast_slider_changed)
            self.anim_invert_colors_checkbox.stateChanged.connect(self._mark_editor_dirty_if_needed)
            self.anim_playback_fps_spinbox.valueChanged.connect(self._mark_editor_dirty_if_needed)
            self.anim_loop_behavior_combo.currentIndexChanged.connect(self._mark_editor_dirty_if_needed)
            self.anim_process_button.clicked.connect(self._handle_anim_process_and_preview)
            if self.anim_play_preview_button:
                self.anim_play_preview_button.toggled.connect(self._handle_anim_play_pause_preview_toggled)
            self.save_this_animation_button.clicked.connect(self._handle_save_this_animation_item)

        # Dialog Buttons (QDialogButtonBox handles Save/Cancel via standard roles)
        self.button_box.accepted.connect(self.accept) # Standard Save button
        self.button_box.rejected.connect(self.reject) # Standard Cancel button
        
        # <<< NEW: Connect the "Save & Apply" button
        if self.save_and_apply_button:
            self.save_and_apply_button.clicked.connect(self._handle_save_and_apply)
            
    def _load_initial_data(self):
        initial_speed_level = self._delay_ms_to_speed_level(self._initial_global_scroll_delay_ms)
        self.global_scroll_speed_level_slider.setValue(initial_speed_level)
        self._update_scroll_speed_display_label(initial_speed_level, self._initial_global_scroll_delay_ms)
        
        self._populate_font_family_combo() 
        self._populate_item_library_list() # This also populates default_startup_item_combo

        # Use the new attribute name to find the initially selected active graphic
        if self._initial_active_graphic_path: # <<< CHANGED ATTRIBUTE NAME
            for i in range(self.default_startup_item_combo.count()):
                item_data = self.default_startup_item_combo.itemData(i)
                if item_data and item_data.get('path') == self._initial_active_graphic_path: # <<< CHANGED
                    self.default_startup_item_combo.setCurrentIndex(i)
                    break
        
        self._update_library_button_states()
        self._update_save_this_item_button_state() 

    def _populate_font_family_combo(self):
        self.text_font_family_combo.blockSignals(True)
        # QFontComboBox populates itself. We just set a default.
        default_font = QFont("Arial") # A common default
        self.text_font_family_combo.setCurrentFont(default_font)
        # If Arial wasn't found, it might select something else or be empty.
        # This is generally okay as QFontComboBox handles fallbacks.
        self.text_font_family_combo.blockSignals(False)

    def _populate_item_library_list(self):
        # Block signals on the combo box during repopulation to avoid unwanted triggers
        self.default_startup_item_combo.blockSignals(True)
        
        self.item_library_list.clear()
        self.default_startup_item_combo.clear()
        # First item is always "None"
        self.default_startup_item_combo.addItem("None (Show Default Text)", userData=None) 
        
        os.makedirs(self.text_items_dir, exist_ok=True)
        os.makedirs(self.animation_items_dir, exist_ok=True)

        found_items_for_combo = [] # To sort before adding to combo

        item_sources = [
            {"dir": self.text_items_dir, "type": "text", "label": "Text"},
            {"dir": self.animation_items_dir, "type": "animation", "label": "Animation"}
        ]

        for source in item_sources:
            if not os.path.isdir(source["dir"]): continue
            for filename in os.listdir(source["dir"]):
                if filename.endswith(".json"):
                    filepath = os.path.join(source["dir"], filename) 
                    try:
                        with open(filepath, 'r', encoding='utf-8') as f: data = json.load(f)
                        item_name = data.get("item_name", os.path.splitext(filename)[0])
                        
                        qlist_item = QListWidgetItem(f"{item_name} ({source['label']})")
                        relative_path = os.path.join(os.path.basename(source["dir"]), filename)
                        qlist_item.setData(Qt.ItemDataRole.UserRole, {
                            'path': filepath, 
                            'relative_path': relative_path, 
                            'type': source['type'], 
                            'name': item_name
                        })
                        self.item_library_list.addItem(qlist_item)
                        
                        found_items_for_combo.append({
                            'name': item_name, 
                            'path': relative_path, # Relative path for combo userData
                            'type': source['type']
                        })
                    except Exception as e: 
                        print(f"Dialog Error loading item metadata from {filepath}: {e}")
        
        found_items_for_combo.sort(key=lambda x: x['name'].lower())
        for item_info in found_items_for_combo:
            self.default_startup_item_combo.addItem(
                f"{item_info['name']} ({item_info['type'].capitalize()})", 
                userData={'path': item_info['path'], 'type': item_info['type']} # Store relative path
            )

        # <<< NEW: Restore the previously selected active graphic in the combo box
        restored_selection = False
        if self._current_dialog_chosen_active_graphic_relative_path:
            for i in range(self.default_startup_item_combo.count()):
                item_data = self.default_startup_item_combo.itemData(i)
                if item_data and isinstance(item_data, dict) and \
                   item_data.get('path') == self._current_dialog_chosen_active_graphic_relative_path:
                    self.default_startup_item_combo.setCurrentIndex(i)
                    restored_selection = True
                    # print(f"Dialog TRACE: Restored active graphic selection to: {self._current_dialog_chosen_active_graphic_relative_path}") # Optional
                    break
        
        if not restored_selection and self._current_dialog_chosen_active_graphic_relative_path is not None:
            # If the previously chosen path is no longer in the list (e.g., deleted),
            # default to "None" and update our internal state variable.
            print(f"Dialog INFO: Previously chosen active graphic '{self._current_dialog_chosen_active_graphic_relative_path}' not found. Defaulting to 'None'.")
            self.default_startup_item_combo.setCurrentIndex(0) # Select "None"
            self._current_dialog_chosen_active_graphic_relative_path = None # Update state
        elif self._current_dialog_chosen_active_graphic_relative_path is None and self.default_startup_item_combo.count() > 0:
             self.default_startup_item_combo.setCurrentIndex(0) # Ensure "None" is selected if path is None

        # Unblock signals after repopulation and potential selection restoration
        self.default_startup_item_combo.blockSignals(False)
        
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
        if self.oled_preview_label:
            pixmap = QPixmap(self.oled_preview_label.size())
            pixmap.fill(Qt.GlobalColor.black)
            self.oled_preview_label.setPixmap(pixmap)
            self.oled_preview_label.setText("") # Ensure no fallback text shows

    def _update_editor_panel_visibility(self, item_type_to_show: str | None):
        # Stop library animation preview if editor is becoming visible
        if item_type_to_show is not None: # Implies an editor is about to be shown
            if self._is_library_preview_anim_playing and self._library_preview_anim_timer.isActive():
                self._library_preview_anim_timer.stop()
            self._is_library_preview_anim_playing = False
            self._current_library_preview_anim_frames = None

        # Stop editor's own animation preview when changing editor visibility or hiding editor
        if self._is_anim_editor_preview_playing and self._anim_editor_preview_timer.isActive():
            self._anim_editor_preview_timer.stop()
        self._is_anim_editor_preview_playing = False
        if self.anim_play_preview_button: 
            self.anim_play_preview_button.setChecked(False)
            self.anim_play_preview_button.setText("▶️ Play Preview")

        current_editor_index = -1
        new_title = "Item Editor"
        newly_selected_editor_page = None

        if item_type_to_show == 'text':
            # ... (rest of the logic as before for setting up text editor) ...
            current_editor_index = 0 
            new_title = "Text Item Editor"
            newly_selected_editor_page = self.text_editor_widget
        elif item_type_to_show == 'animation':
            # ... (rest of the logic as before for setting up animation editor) ...
            current_editor_index = 1 
            new_title = "Animation Item Editor"
            newly_selected_editor_page = self.animation_editor_widget_container
        
        if current_editor_index != -1 and newly_selected_editor_page is not None:
            self.editor_stacked_widget.setCurrentWidget(newly_selected_editor_page) 
            self.item_editor_group.setTitle(new_title)
            self.item_editor_group.setVisible(True)
            # ... (rest of your existing geometry/size update logic for the panels) ...
            newly_selected_editor_page.layout().activate() 
            newly_selected_editor_page.adjustSize() 
            needed_height = newly_selected_editor_page.sizeHint().height() 
            self.item_editor_group.setMinimumHeight(needed_height) 
            self.item_editor_group.layout().activate() 
        else: 
            self.item_editor_group.setVisible(False)
            self._current_edited_item_path = None
            self._current_edited_item_type = None
            self._is_editing_new_item = False
            self._editor_has_unsaved_changes = False
            # When editor is hidden, the preview should reflect library selection (or be blank)
            # This is handled by _on_library_selection_changed calling _preview_item_from_path or _clear_preview
            # Or if library has no selection, _update_preview will clear.
            self._update_preview() # Ensure preview updates based on library or is cleared
        
        self._update_save_this_item_button_state()
        if self.layout() is not None: self.layout().activate()
        self.adjustSize() # Dialog adjusts to content

    def _clear_text_editor_fields(self):
        self.item_name_edit.setText("")
        self.text_content_edit.clear()
        self.text_font_family_combo.setCurrentFont(QFont("Arial")) # Default font
        self.text_font_size_spinbox.setValue(10)
        self.text_scroll_checkbox.setChecked(True)
        self.text_alignment_combo.setCurrentIndex(1) # Center
        self.text_anim_override_speed_checkbox.setChecked(False)
        
        # Use the initial global scroll delay as the default for item-specific speed
        default_delay = self._initial_global_scroll_delay_ms if hasattr(self, '_initial_global_scroll_delay_ms') else DEFAULT_GLOBAL_SCROLL_DELAY_MS_FALLBACK
        self.text_anim_item_scroll_speed_spinbox.setValue(default_delay)
        self.text_anim_pause_at_ends_spinbox.setValue(1000) # Default pause
        
        self._on_text_scroll_checkbox_changed() # Update dependent UI enabled states
        self._on_text_anim_override_speed_changed()

    def _clear_animation_editor_fields(self):
        if not IMAGE_PROCESSING_AVAILABLE:
            return

        # Stop any in-dialog preview playback timer if it was running
        if hasattr(self, '_anim_editor_preview_timer') and self._anim_editor_preview_timer.isActive():
            self._anim_editor_preview_timer.stop()
        self._is_anim_editor_preview_playing = False
        self._current_anim_editor_preview_frame_index = 0

        if hasattr(self, 'anim_play_preview_button') and self.anim_play_preview_button:
            self.anim_play_preview_button.setChecked(False)
            self.anim_play_preview_button.setText("▶️ Play Preview")
            # Becomes enabled after successful processing
            self.anim_play_preview_button.setEnabled(False)

        # UI field resets
        self.anim_item_name_edit.setText("")
        self.anim_source_file_label.setText("<i>No file selected</i>")
        self.anim_source_file_label.setToolTip("")
        self._current_anim_source_filepath = None

        self.anim_resize_mode_combo.setCurrentIndex(0)
        self.anim_mono_conversion_combo.setCurrentIndex(0)
        self.anim_threshold_slider.setValue(128)  # Resets slider position
        self.anim_threshold_value_label.setText("128")  # Updates label
        self.anim_invert_colors_checkbox.setChecked(False)

        # --- NEW: Reset Contrast Slider ---
        if hasattr(self, 'anim_contrast_slider') and self.anim_contrast_slider:
            self.anim_contrast_slider.setValue(100)  # Default to 1.0x factor (slider value 100)
        if hasattr(self, 'anim_contrast_value_label') and self.anim_contrast_value_label:
            self.anim_contrast_value_label.setText("1.00x")
        # --- END NEW ---

        self.anim_playback_fps_spinbox.setValue(15)
        self.anim_loop_behavior_combo.setCurrentIndex(0)

        self.anim_frame_info_label.setText("Frames: N/A | Source FPS: N/A")

        # Clear processed data
        self._processed_logical_frames = None
        self._processed_anim_source_fps = None
        self._processed_anim_source_loop_count = None

        self._on_anim_mono_conversion_changed()  # Update threshold visibility

        # Main dialog preview will be updated by _update_preview when editor visibility changes

    def _handle_new_text_item(self):
        if self._prompt_save_unsaved_editor_changes() == QMessageBox.StandardButton.Cancel: return
        
        self.item_library_list.clearSelection() # Deselect any library item
        self._clear_text_editor_fields()
        self._update_editor_panel_visibility('text') # Show text editor
        
        self._current_edited_item_path = None
        self._current_edited_item_type = 'text'
        self._is_editing_new_item = True
        self._editor_has_unsaved_changes = False # New item isn't "dirty" until changed
        
        self.item_name_edit.setFocus()
        self._update_save_this_item_button_state()
        self._update_preview() # Preview the blank/default state

    def _handle_new_animation_item(self):
        if not IMAGE_PROCESSING_AVAILABLE:
            QMessageBox.warning(self, "Feature Disabled", "Image processing module is not available.")
            return
            
        if self._prompt_save_unsaved_editor_changes() == QMessageBox.StandardButton.Cancel: return
        
        self.item_library_list.clearSelection()
        self._clear_animation_editor_fields()
        self._update_editor_panel_visibility('animation') # Show animation editor
        
        self._current_edited_item_path = None
        self._current_edited_item_type = 'animation'
        self._is_editing_new_item = True
        self._editor_has_unsaved_changes = False
        
        self.anim_item_name_edit.setFocus()
        self._update_save_this_item_button_state()
        self._update_preview() # Preview (will be blank for new animation)

    def _handle_anim_play_pause_preview_toggled(self, checked: bool):
        if not IMAGE_PROCESSING_AVAILABLE or not self._processed_logical_frames or len(self._processed_logical_frames) == 0:
            self.anim_play_preview_button.setChecked(False) # Uncheck if no frames
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
               self._current_anim_editor_preview_frame_index == 0: # If at end or explicitly stopped/restarted
                self._current_anim_editor_preview_frame_index = 0
            
            target_fps = self.anim_playback_fps_spinbox.value()
            if target_fps <= 0: target_fps = 15 # Fallback FPS
            interval_ms = int(1000.0 / target_fps)
            min_interval = 33 # approx 30 FPS
            self._anim_editor_preview_timer.start(max(min_interval, interval_ms))
            self._play_next_anim_editor_preview_frame() # Show current/first frame immediately
        else: # Paused
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
            QMessageBox.information(self, "Edit Item", "Please select an item from the library to edit.")
            return

        if self._prompt_save_unsaved_editor_changes() == QMessageBox.StandardButton.Cancel:
            return

        item_data_from_list = selected_qlist_item.data(Qt.ItemDataRole.UserRole)
        item_full_path = item_data_from_list.get('path') 
        item_type = item_data_from_list.get('type')

        if not item_full_path or not os.path.exists(item_full_path):
            QMessageBox.warning(self, "Edit Error", f"Selected item file not found at '{item_full_path}'.")
            self._populate_item_library_list() 
            return

        self._current_edited_item_path = item_full_path
        self._current_edited_item_type = item_type
        self._is_editing_new_item = False # Editing an existing item

        try:
            with open(item_full_path, 'r', encoding='utf-8') as f:
                item_json_data = json.load(f)
        except Exception as e:
            QMessageBox.critical(self, "Load Error", f"Could not load item data from '{item_full_path}': {e}")
            self._update_editor_panel_visibility(None) # Hide editor on error
            return

        if item_type == 'text':
            self._update_editor_panel_visibility('text')
            self.item_editor_group.setTitle(f"Edit Text Item: {item_json_data.get('item_name', 'Untitled')}")
            self._load_text_item_into_editor(item_json_data)
        elif item_type == 'animation':
            if IMAGE_PROCESSING_AVAILABLE:
                self._update_editor_panel_visibility('animation')
                self.item_editor_group.setTitle(f"Edit Animation Item: {item_json_data.get('item_name', 'Untitled')}")
                self._load_animation_item_into_editor(item_json_data)
            else:
                 QMessageBox.warning(self, "Edit Error", "Cannot edit animation items: Image processing module unavailable.")
                 self._update_editor_panel_visibility(None)
                 return
        else:
            QMessageBox.warning(self, "Edit Error", f"Unsupported item type for editing: {item_type}")
            self._update_editor_panel_visibility(None)
            return

        self._editor_has_unsaved_changes = False # Reset flag after loading
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
        default_speed_for_item = self._initial_global_scroll_delay_ms if hasattr(self, '_initial_global_scroll_delay_ms') else DEFAULT_GLOBAL_SCROLL_DELAY_MS_FALLBACK
        self.text_anim_item_scroll_speed_spinbox.setValue(anim_params.get("speed_override_ms", default_speed_for_item))
        self.text_anim_pause_at_ends_spinbox.setValue(anim_params.get("pause_at_ends_ms", 1000))
        
        alignment_str = data.get("alignment", "center").lower()
        align_map = {"left": 0, "center": 1, "right": 2}
        self.text_alignment_combo.setCurrentIndex(align_map.get(alignment_str, 1)) # Default to center
        
        self._on_text_scroll_checkbox_changed() # Update UI based on loaded scroll state
        self._on_text_anim_override_speed_changed() # Update UI based on loaded override state

    def _load_animation_item_into_editor(self, data: dict):
        if not IMAGE_PROCESSING_AVAILABLE: return

        # ... (stop preview timers, set anim_item_name_edit, anim_source_file_label, etc. as before) ...
        if self._is_anim_editor_preview_playing: # Stop editor's own preview
            self._anim_editor_preview_timer.stop()
        self._is_anim_editor_preview_playing = False
        if self.anim_play_preview_button:
            self.anim_play_preview_button.setChecked(False); self.anim_play_preview_button.setText("▶️ Play Preview")
        self._current_anim_editor_preview_frame_index = 0

        self.anim_item_name_edit.setText(data.get("item_name", ""))
        source_ref = data.get("source_file_path_for_reference", "N/A (processed data only)")
        base_source_ref = os.path.basename(source_ref)
        self.anim_source_file_label.setText(base_source_ref if len(base_source_ref) < 40 else "..." + base_source_ref[-37:])
        self.anim_source_file_label.setToolTip(source_ref)
        # Store the original source path if available and it exists, for easy re-processing
        if os.path.exists(source_ref):
            self._current_anim_source_filepath = source_ref
        else:
            self._current_anim_source_filepath = None # Original source not found

        import_opts = data.get("import_options_used", {})
        self.anim_resize_mode_combo.setCurrentText(import_opts.get("resize_mode", "Stretch to Fit"))
        mono_mode_val = import_opts.get("mono_conversion_mode", import_opts.get("dithering", "Floyd-Steinberg Dither"))
        self.anim_mono_conversion_combo.setCurrentText(mono_mode_val)
        self.anim_threshold_slider.setValue(import_opts.get("threshold_value", 128))
        self.anim_invert_colors_checkbox.setChecked(import_opts.get("invert_colors", False))

        # --- NEW: Load Contrast Factor ---
        contrast_factor_loaded = float(import_opts.get("contrast_factor", 1.0))
        if self.anim_contrast_slider:
            # Convert factor (e.g., 0.0-2.0) back to slider value (0-200)
            self.anim_contrast_slider.setValue(int(round(contrast_factor_loaded * 100)))
        if self.anim_contrast_value_label:
            self.anim_contrast_value_label.setText(f"{contrast_factor_loaded:.2f}x")
        # --- END NEW ---

        self.anim_playback_fps_spinbox.setValue(import_opts.get("playback_fps", 15))
        self.anim_loop_behavior_combo.setCurrentText(import_opts.get("loop_behavior", "Loop Infinitely"))
        self._on_anim_mono_conversion_changed()

        self._processed_logical_frames = data.get("frames_logical")
        # ... (update frame info label, enable play preview button, as before) ...
        if self._processed_logical_frames:
            fps_text = f"{import_opts.get('source_fps'):.2f}" if import_opts.get('source_fps') is not None else "N/A"
            loop_text = str(import_opts.get('source_loop_count')) if import_opts.get('source_loop_count') is not None else \
                        ("Infinite" if import_opts.get('source_fps') is not None and import_opts.get('source_loop_count') == 0 else "N/A")
            self.anim_frame_info_label.setText(f"Frames: {len(self._processed_logical_frames)} | Src FPS: {fps_text} | Loop: {loop_text}")
            if self.anim_play_preview_button: self.anim_play_preview_button.setEnabled(True)
        else:
            self.anim_frame_info_label.setText("Frames: N/A (Reload or Re-process)")
            if self.anim_play_preview_button: self.anim_play_preview_button.setEnabled(False)
            
    def _handle_delete_selected_item(self):
        selected_qlist_item = self.item_library_list.currentItem()
        if not selected_qlist_item:
            QMessageBox.information(self, "Delete Item", "Please select an item to delete.")
            return
            
        item_data_from_list = selected_qlist_item.data(Qt.ItemDataRole.UserRole)
        item_name_for_prompt = item_data_from_list.get('name', 'this item')
        item_full_path_to_delete = item_data_from_list.get('path') # This is the full path

        reply = QMessageBox.question(self, "Delete Item", f"Are you sure you want to delete '{item_name_for_prompt}'?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                     QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.No:
            return

        if item_full_path_to_delete and os.path.exists(item_full_path_to_delete):
            try:
                os.remove(item_full_path_to_delete)
                QMessageBox.information(self, "Delete Item", f"Item '{item_name_for_prompt}' deleted successfully.")
                
                # If the deleted item was being edited, clear the editor
                if self._current_edited_item_path == item_full_path_to_delete:
                    self._update_editor_panel_visibility(None) # Hide editor
                    self._current_edited_item_path = None
                    self._current_edited_item_type = None
                    self._is_editing_new_item = False
                    self._editor_has_unsaved_changes = False # No more unsaved changes for this non-existent item
            except Exception as e:
                QMessageBox.critical(self, "Delete Error", f"Could not delete item file: {e}")
        else:
            QMessageBox.warning(self, "Delete Error", "Item file not found or path is invalid. It might have been already deleted.")

        self._populate_item_library_list() # Refresh list
        self._update_library_button_states()
        self._update_save_this_item_button_state() # Update save button state

    def _preview_item_from_path(self, item_filepath: str | None):
        # This method is now primarily for previewing TEXT items from the library,
        # or for setting up the static first frame if called from _update_preview for the editor.
        # print(f"Dialog DEBUG: _preview_item_from_path called for: {item_filepath}") 

        if not self.oled_preview_label: # Should always exist after _init_ui
            self._clear_preview_label_content() # Use the explicit clearer
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

            self._preview_scroll_timer.stop() # Stop any text scrolling from previous item
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
                
                anim_style = data.get("animation_style", "static") # Default to static
                # Use the item's scroll settings for preview
                should_scroll_preview = (anim_style == "scroll_left") and \
                                        preview_text_width > NATIVE_OLED_WIDTH and \
                                        text_to_preview.strip() != ""
                
                if should_scroll_preview:
                    self._preview_is_scrolling = True
                    self._preview_current_scroll_offset = NATIVE_OLED_WIDTH # Start off-screen right
                    self._preview_text_pixel_width = preview_text_width # Store for scrolling logic

                    preview_scroll_delay = self._initial_global_scroll_delay_ms # Global default
                    anim_params = data.get("animation_params", {})
                    if anim_params.get("speed_override_ms") is not None:
                        preview_scroll_delay = anim_params.get("speed_override_ms")
                    
                    if self._preview_scroll_timer.isActive(): self._preview_scroll_timer.stop() # Defensive stop
                    self._preview_scroll_timer.start(max(20, preview_scroll_delay))
                else:
                    self._preview_is_scrolling = False
                    self._preview_current_scroll_offset = 0
                
                # print(f"Dialog DEBUG: Text preview setup: scroll={self._preview_is_scrolling}, width={preview_text_width}")
                self._render_preview_frame(override_text=text_to_preview) # Render initial state of text

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
                    self._current_preview_anim_logical_frame = frames[0] # For _render_preview_frame's static anim part
                    # print(f"Dialog DEBUG: _preview_item_from_path setting STATIC first frame for animation '{item_name_debug}'")
                else:
                    self._current_preview_anim_logical_frame = None
                self._render_preview_frame() # Render the static first frame
            else:
                print(f"Dialog WARNING: _preview_item_from_path encountered unknown item type '{item_type}' for '{item_name_debug}'. Clearing preview.")
                self._clear_preview_label_content()

        except Exception as e:
            print(f"Dialog ERROR: Exception in _preview_item_from_path for '{item_filepath}': {e}")
            import traceback
            traceback.print_exc()
            self._clear_preview_label_content()

    def _render_preview_frame(self, override_text: str | None = None):
        # print(f"Dialog DEBUG: _render_preview_frame called. Override text: '{override_text is not None}', PreviewFont: '{self._current_preview_font_object is not None}', AnimFrame: '{self._current_preview_anim_logical_frame is not None}'") # DEBUG
        if not self.oled_preview_label: return

        preview_pixmap_native = QPixmap(NATIVE_OLED_WIDTH, NATIVE_OLED_HEIGHT)
        preview_pixmap_native.fill(Qt.GlobalColor.black)
        painter = QPainter(preview_pixmap_native)
        
        rendered_something = False # DEBUG flag

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
                painter.end() # Close painter before returning if nothing to render
                scaled_preview = preview_pixmap_native.scaled(self.oled_preview_label.size(), Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.FastTransformation)
                self.oled_preview_label.setPixmap(scaled_preview)
                return
            painter.setFont(current_font_for_render)
            painter.setPen(QColor("white"))
            fm = painter.fontMetrics()
            text_render_y = fm.ascent() + (NATIVE_OLED_HEIGHT - fm.height()) // 2
            text_render_x = 0
            if self._preview_is_scrolling: text_render_x = self._preview_current_scroll_offset
            else: 
                text_width = fm.horizontalAdvance(text_for_frame)
                alignment_str = "center" 
                if self.item_editor_group.isVisible() and self.editor_stacked_widget.currentWidget() == self.text_editor_widget:
                     alignment_str = self.text_alignment_combo.currentText().lower()
                if text_width < NATIVE_OLED_WIDTH:
                    if alignment_str == "center": text_render_x = (NATIVE_OLED_WIDTH - text_width) // 2
                    elif alignment_str == "right": text_render_x = NATIVE_OLED_WIDTH - text_width
            painter.drawText(text_render_x, text_render_y, text_for_frame)
            rendered_something = True # DEBUG

        elif self._current_preview_anim_logical_frame: # Animation frame for main preview
            print("Dialog DEBUG: Rendering animation frame to main preview.") # DEBUG
            q_image = QImage(NATIVE_OLED_WIDTH, NATIVE_OLED_HEIGHT, QImage.Format.Format_Mono)
            q_image.fill(0) 
            for y, row_str in enumerate(self._current_preview_anim_logical_frame):
                if y >= NATIVE_OLED_HEIGHT: break
                for x, pixel_char in enumerate(row_str):
                    if x >= NATIVE_OLED_WIDTH: break
                    if pixel_char == '1':
                        q_image.setPixel(x, y, 1)
            painter.drawImage(0,0, q_image)
            rendered_something = True # DEBUG
        
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
        if not self.oled_preview_label:
            self._clear_preview() 
            return

        # Always stop the text scroll timer before updating the main preview with new content.
        self._preview_scroll_timer.stop()
        self._preview_is_scrolling = False # Reset text scroll flag

        # Default to clearing animation frame unless explicitly set
        self._current_preview_anim_logical_frame = None
        self._current_preview_font_object = None # Default to no text font

        if self.item_editor_group.isVisible(): # An editor panel is active
            active_editor_widget = self.editor_stacked_widget.currentWidget()
            if active_editor_widget == self.text_editor_widget:
                # --- TEXT EDITOR IS ACTIVE ---
                text_to_preview = self.text_content_edit.text()
                font_family = self.text_font_family_combo.currentFont().family()
                font_size_px = self.text_font_size_spinbox.value()
                
                if not font_family or font_size_px <= 0: 
                    self._clear_main_preview_content()
                    return

                self._current_preview_font_object = QFont(font_family)
                self._current_preview_font_object.setPixelSize(font_size_px)
                
                fm = QFontMetrics(self._current_preview_font_object)
                self._preview_text_pixel_width = fm.horizontalAdvance(text_to_preview)
                should_scroll_preview = self.text_scroll_checkbox.isChecked() and \
                                        self._preview_text_pixel_width > NATIVE_OLED_WIDTH and \
                                        text_to_preview.strip() != ""

                if should_scroll_preview:
                    self._preview_is_scrolling = True
                    self._preview_current_scroll_offset = NATIVE_OLED_WIDTH 
                    preview_scroll_delay = self._initial_global_scroll_delay_ms
                    if self.text_anim_override_speed_checkbox.isChecked():
                        preview_scroll_delay = self.text_anim_item_scroll_speed_spinbox.value()
                    self._preview_scroll_timer.start(max(20, preview_scroll_delay)) 
                else:
                    self._preview_current_scroll_offset = 0
                self._render_preview_frame(override_text=text_to_preview) # Render the text

            elif active_editor_widget == self.animation_editor_widget_container:
                # --- ANIMATION EDITOR IS ACTIVE ---
                # If the in-dialog animation preview ISN'T playing, show the static first frame
                # of the currently *processed* frames in the editor.
                if not self._is_anim_editor_preview_playing:
                    if self._processed_logical_frames and len(self._processed_logical_frames) > 0:
                        self._current_preview_anim_logical_frame = self._processed_logical_frames[0]
                    # else: _current_preview_anim_logical_frame remains None (cleared at start of method)
                    self._render_preview_frame() # Render (static first anim frame or blank)
                # If _is_anim_editor_preview_playing is True, its timer is updating the main preview, so do nothing here.
            else: # Some other unknown widget in stack? Should not happen.
                self._clear_main_preview_content()
        
        else: # Editor is NOT visible (implies library selection drives the preview)
            selected_lib_item = self.item_library_list.currentItem()
            if selected_lib_item:
                item_data = selected_lib_item.data(Qt.ItemDataRole.UserRole)
                # _preview_item_from_path will set _current_preview_font_object OR _current_preview_anim_logical_frame
                # and then call _render_preview_frame itself.
                self._preview_item_from_path(item_data.get('path')) 
            else: # No library item selected, editor hidden
                self._clear_main_preview_content()
                
    def _clear_main_preview_content(self):
        if self.oled_preview_label:
            pixmap = QPixmap(self.oled_preview_label.size())
            pixmap.fill(Qt.GlobalColor.black)
            self.oled_preview_label.setPixmap(pixmap)
            self.oled_preview_label.setText("Preview") # Reset text if pixmap is cleared

    def _mark_editor_dirty_if_needed(self, *args):
        sender = self.sender()

        # Ignore changes from global settings affecting the editor's dirty state directly
        if sender == self.default_startup_item_combo or sender == self.global_scroll_speed_level_slider:
            # However, if the Active Graphic dropdown changes, we might want to save global settings.
            # This is handled by the main dialog's Save button.
            # For now, this method only cares about item editor dirtiness.
            return

        if self.item_editor_group.isVisible() and \
           (self._is_editing_new_item or self._current_edited_item_path is not None):

            # print(f"Dialog DEBUG: _mark_editor_dirty_if_needed triggered by: {sender}") # Optional
            self._editor_has_unsaved_changes = True

            active_editor_widget = self.editor_stacked_widget.currentWidget()
            if active_editor_widget == self.animation_editor_widget_container:
                # List of controls whose changes require reprocessing the animation
                anim_processing_option_senders = [
                    self.anim_resize_mode_combo,
                    self.anim_mono_conversion_combo,
                    self.anim_threshold_slider,
                    self.anim_invert_colors_checkbox,
                    self.anim_contrast_slider  # <<< ADD CONTRAST SLIDER HERE
                ]
                if sender in anim_processing_option_senders:
                    if self._processed_logical_frames:  # Only if frames were already processed
                        print(
                            "Dialog DEBUG: Animation processing option changed, invalidating processed frames.")
                        self._processed_logical_frames = None
                        self.anim_frame_info_label.setText(
                            "Frames: N/A | Options changed. Re-process.")
                        if self.anim_play_preview_button:
                            if self._is_anim_editor_preview_playing:  # Stop preview if it was playing
                                self.anim_play_preview_button.setChecked(
                                    False)  # This will trigger toggled signal
                            self.anim_play_preview_button.setEnabled(False)
                        # Update main preview to clear animation
                        self._current_preview_anim_logical_frame = None
                        self._update_preview()  # This will clear the animation part of preview

            self._update_save_this_item_button_state()
            # Update preview only if it's not an option that invalidates frames (handled above for anim)
            # For text items, or anim options that don't invalidate frames (like name, FPS), update preview directly.
            if not (active_editor_widget == self.animation_editor_widget_container and sender in anim_processing_option_senders):
                self._update_preview()

    def _update_save_this_item_button_state(self):
        # This method now also controls the "Save & Apply" button state
        
        # Default states
        can_save_text_item_locally = False
        can_save_anim_item_locally = False
        can_apply_something = False # For "Save & Apply"

        if not self.editor_stacked_widget: # Should not happen if UI initialized
            if hasattr(self, 'save_this_text_item_button'): self.save_this_text_item_button.setEnabled(False)
            if hasattr(self, 'save_this_animation_button'): self.save_this_animation_button.setEnabled(False)
            if hasattr(self, 'save_and_apply_button') and self.save_and_apply_button: self.save_and_apply_button.setEnabled(False)
            return

        if self.item_editor_group.isVisible(): # An editor panel is active
            active_widget = self.editor_stacked_widget.currentWidget()
            
            if active_widget == self.text_editor_widget:
                is_name_valid = bool(self.item_name_edit.text().strip())
                # Enable local save if dirty or new, AND name is valid
                can_save_text_item_locally = (self._editor_has_unsaved_changes or self._is_editing_new_item) and is_name_valid
                # Enable "Save & Apply" if editor is active and name is valid (even if not dirty, for "apply existing but maybe name changed")
                # OR if a library item is selected (for applying library item directly)
                can_apply_something = is_name_valid or (self.item_library_list.currentItem() is not None)

            elif active_widget == self.animation_editor_widget_container:
                is_name_valid_anim = bool(self.anim_item_name_edit.text().strip())
                has_processed_frames = self._processed_logical_frames is not None and len(self._processed_logical_frames) > 0
                # Enable local save if dirty or new, AND name valid, AND frames processed
                can_save_anim_item_locally = IMAGE_PROCESSING_AVAILABLE and \
                    (self._editor_has_unsaved_changes or self._is_editing_new_item) and \
                    is_name_valid_anim and has_processed_frames
                # Enable "Save & Apply" if editor active, name valid, frames processed
                # OR if a library item is selected
                can_apply_something = (is_name_valid_anim and has_processed_frames) or \
                                      (self.item_library_list.currentItem() is not None)
        else: # Editor is not visible, only library selection matters for "Save & Apply"
            can_apply_something = (self.item_library_list.currentItem() is not None)

        # Set enabled states for local save buttons
        if hasattr(self, 'save_this_text_item_button'):
            self.save_this_text_item_button.setEnabled(can_save_text_item_locally)
        if hasattr(self, 'save_this_animation_button'):
            self.save_this_animation_button.setEnabled(can_save_anim_item_locally)

        # <<< NEW: Set enabled state for "Save & Apply" button
        if hasattr(self, 'save_and_apply_button') and self.save_and_apply_button:
            self.save_and_apply_button.setEnabled(can_apply_something)

    def _on_text_scroll_checkbox_changed(self):
        is_scrolling = self.text_scroll_checkbox.isChecked()
        self.text_alignment_combo.setEnabled(not is_scrolling)
        self.text_anim_override_speed_checkbox.setEnabled(is_scrolling)
        self._on_text_anim_override_speed_changed() # Update speed spinbox based on override
        self.text_anim_pause_at_ends_spinbox.setEnabled(is_scrolling)
        self._mark_editor_dirty_if_needed()

    def _on_text_anim_override_speed_changed(self):
        is_override = self.text_anim_override_speed_checkbox.isChecked()
        is_scrolling = self.text_scroll_checkbox.isChecked()
        self.text_anim_item_scroll_speed_spinbox.setEnabled(is_override and is_scrolling)
        self._mark_editor_dirty_if_needed()

    def _handle_save_this_text_item(self) -> bool: # <<< MODIFIED: Added return type bool
        item_name = self.item_name_edit.text().strip()
        if not item_name:
            QMessageBox.warning(self, "Save Error",
                                "Text Item Name cannot be empty.")
            self.item_name_edit.setFocus()
            return False # <<< MODIFIED: Return False

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
                return False # <<< MODIFIED: User cancelled Save As
            target_filepath = target_filepath_new
        elif not target_filepath : # If it was new and somehow became None, or existing item path lost
             save_path_suggestion = os.path.join(self.text_items_dir, suggested_filename)
             target_filepath_new, _ = QFileDialog.getSaveFileName(self, "Save Text Item", save_path_suggestion, "JSON files (*.json)")
             if not target_filepath_new: return False # <<< MODIFIED: User cancelled
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
            return True # <<< MODIFIED: Return True on success
        except Exception as e:
            QMessageBox.critical(self, "Save Error",
                                 f"Failed to save text item: {e}")
            return False # <<< MODIFIED: Return False on failure

    def _handle_save_this_animation_item(self) -> bool: # <<< MODIFIED: Added return type bool
        if not IMAGE_PROCESSING_AVAILABLE: return False
        item_name = self.anim_item_name_edit.text().strip()
        if not item_name: 
            QMessageBox.warning(self, "Save Error", "Animation Item Name cannot be empty.")
            return False # <<< MODIFIED
        if not self._processed_logical_frames or len(self._processed_logical_frames) == 0: 
            QMessageBox.warning(self, "Save Error", "No frames processed. Please process an image/GIF.")
            return False # <<< MODIFIED

        contrast_factor_to_save = 1.0
        if self.anim_contrast_slider:
            contrast_factor_to_save = self.anim_contrast_slider.value() / 100.0
        
        source_fps_for_json = self._processed_anim_source_fps if isinstance(self._processed_anim_source_fps, (int, float)) else None
        source_loop_for_json = self._processed_anim_source_loop_count if isinstance(self._processed_anim_source_loop_count, int) else None


        import_options_used = {
            "resize_mode": self.anim_resize_mode_combo.currentText(),
            "mono_conversion_mode": self.anim_mono_conversion_combo.currentText(),
            "threshold_value": self.anim_threshold_slider.value() if self.anim_threshold_widget.isVisible() else 128,
            "invert_colors": self.anim_invert_colors_checkbox.isChecked(),
            "contrast_factor": contrast_factor_to_save,
            "source_fps": source_fps_for_json, 
            "source_loop_count": source_loop_for_json, # <<< ADDED source_loop_count
            "playback_fps": self.anim_playback_fps_spinbox.value(),
            "loop_behavior": self.anim_loop_behavior_combo.currentText(),
        }

        item_data_to_save = {
            "item_name": item_name,
            "item_type": "image_animation",
            "source_file_path_for_reference": self._current_anim_source_filepath if self._current_anim_source_filepath else "N/A",
            "import_options_used": import_options_used,
            "frames_logical": self._processed_logical_frames
        }

        target_filepath = self._current_edited_item_path if self._current_edited_item_type == 'image_animation' and not self._is_editing_new_item else None
        # If it's an animation item, make sure type is 'image_animation' before reusing path
        if self._current_edited_item_type != 'image_animation': target_filepath = None

        safe_filename_base = "".join(c if c.isalnum() or c in [' ', '_', '-'] else '' for c in item_name).replace(' ', '_')
        if not safe_filename_base: safe_filename_base = "untitled_animation"
        suggested_filename = f"{safe_filename_base}.json"

        if self._is_editing_new_item or \
           (target_filepath and os.path.basename(target_filepath).lower() != suggested_filename.lower() and \
            os.path.normpath(os.path.dirname(target_filepath)) != os.path.normpath(self.animation_items_dir)):
            save_path_suggestion = os.path.join(self.animation_items_dir, suggested_filename)
            target_filepath_new, _ = QFileDialog.getSaveFileName(self, "Save Animation Item As...", save_path_suggestion, "JSON files (*.json)")
            if not target_filepath_new: return False # <<< MODIFIED
            target_filepath = target_filepath_new
        elif not target_filepath : 
             target_filepath = os.path.join(self.animation_items_dir, suggested_filename)


        try:
            os.makedirs(os.path.dirname(target_filepath), exist_ok=True)
            with open(target_filepath, 'w', encoding='utf-8') as f:
                json.dump(item_data_to_save, f, indent=4) 
            QMessageBox.information(self, "Item Saved", f"Animation item '{item_name}' saved.")
            self._current_edited_item_path = target_filepath
            self._current_edited_item_type = 'image_animation'
            self._is_editing_new_item = False
            self._editor_has_unsaved_changes = False
            self._update_save_this_item_button_state()
            self.item_editor_group.setTitle(f"Edit Animation Item: {item_name}")
            self._populate_item_library_list()
            for i in range(self.item_library_list.count()):
                q_item = self.item_library_list.item(i)
                if q_item and q_item.data(Qt.ItemDataRole.UserRole).get('path') == target_filepath:
                    self.item_library_list.setCurrentItem(q_item); break
            return True # <<< MODIFIED
        except Exception as e:
            QMessageBox.critical(self, "Save Error", f"Failed to save animation item: {e}")
            return False # <<< MODIFIED

    def _handle_save_and_apply(self):
        """
        Handles the "Save & Apply" button click.
        1. Determines the target item (editor content or library selection).
        2. Saves the item if it's from the editor and has changes or is new.
        3. Sets the target item as the choice in the "Set as Active Graphic" dropdown.
        4. Accepts and closes the dialog.
        """
        print("Dialog TRACE: _handle_save_and_apply called.") # Optional debug

        target_item_relative_path: str | None = None
        target_item_type_for_combo: str | None = None # 'text' or 'animation'
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
            print("Dialog TRACE: Save & Apply - Target is editor content.") # Optional debug
            if self._current_edited_item_type == 'text':
                save_was_successful_or_not_needed = self._handle_save_this_text_item()
            elif self._current_edited_item_type == 'animation':
                save_was_successful_or_not_needed = self._handle_save_this_animation_item()
            
            if not save_was_successful_or_not_needed:
                print("Dialog TRACE: Save & Apply - Save from editor failed or was cancelled. Aborting apply.") # Optional
                return # Stop if save failed/cancelled

            # After successful save, _current_edited_item_path (full) and _current_edited_item_type are set.
            # We need the relative path for the combo box.
            if self._current_edited_item_path:
                base_dir_for_type = self.text_items_dir if self._current_edited_item_type == 'text' else self.animation_items_dir
                try:
                    # Ensure paths are normalized for robust relative path calculation
                    full_item_path_norm = os.path.normpath(self._current_edited_item_path)
                    base_presets_path_norm = os.path.normpath(self.user_oled_presets_base_path)
                    target_item_relative_path = os.path.relpath(full_item_path_norm, base_presets_path_norm)
                    target_item_relative_path = target_item_relative_path.replace(os.path.sep, '/') # Ensure forward slashes
                    target_item_type_for_combo = self._current_edited_item_type
                    print(f"Dialog TRACE: Save & Apply - Saved item relative path: {target_item_relative_path}") # Optional
                except ValueError as e_rel: # Can happen if paths are on different drives on Windows
                    print(f"Dialog ERROR: Could not determine relative path for saved item '{self._current_edited_item_path}': {e_rel}")
                    QMessageBox.warning(self, "Apply Error", "Could not determine relative path for the saved item. Cannot apply.")
                    return
            else: # Should not happen if save was successful
                print("Dialog ERROR: Save & Apply - Editor save successful, but _current_edited_item_path is None.")
                return
        
        else: # Editor not active/valid, or no unsaved changes. Use library selection.
            print("Dialog TRACE: Save & Apply - Target is library selection (or editor was clean).") # Optional
            selected_qlist_item = self.item_library_list.currentItem()
            if selected_qlist_item:
                item_data = selected_qlist_item.data(Qt.ItemDataRole.UserRole)
                if item_data:
                    target_item_relative_path = item_data.get('relative_path')
                    target_item_type_for_combo = item_data.get('type')
                    # print(f"Dialog TRACE: Save & Apply - Library item relative path: {target_item_relative_path}") # Optional
            else: # No editor content, no library selection
                QMessageBox.information(self, "Save & Apply", "Please select an item from the library or save an edited item first.")
                return

        if not target_item_relative_path:
            QMessageBox.warning(self, "Save & Apply Error", "Could not determine an item to apply.")
            return

        # --- Step 4: Set "Active Graphic" Dropdown ---
        print(f"Dialog TRACE: Save & Apply - Attempting to set dropdown to: {target_item_relative_path}") # Optional
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
                print(f"Dialog TRACE: Save & Apply - Set dropdown index to {i} for path '{target_item_relative_path}'") # Optional
                break
        
        if not found_in_combo:
            print(f"Dialog ERROR: Save & Apply - Target item '{target_item_relative_path}' not found in Active Graphic dropdown after save/selection.")
            QMessageBox.warning(self, "Apply Error", "Could not find the target item in the Active Graphic list after processing. Please check the library.")
            return

        # --- Step 5: Accept and Close Dialog ---
        print("Dialog TRACE: Save & Apply - Calling self.accept()") # Optional
        self.accept()

    def _on_anim_mono_conversion_changed(self):
        if not IMAGE_PROCESSING_AVAILABLE:
            return

        current_selection = self.anim_mono_conversion_combo.currentText()
        show_threshold = (current_selection == "Simple Threshold")

        # Only proceed if visibility actually changes, to avoid unnecessary layout updates
        if self.anim_threshold_widget.isVisible() == show_threshold:
            self._mark_editor_dirty_if_needed() # Still mark as dirty
            return 

        self.anim_threshold_widget.setVisible(show_threshold)

        # The animation_editor_widget_container (the QWidget page) now has a fixed minimum height.
        # When a child's visibility changes, its internal layout should adjust.
        # We might still want to give the container a nudge to re-evaluate its layout.
        if self.animation_editor_widget_container:
            # Request the layout to activate/update. This should respect the panel's minimum height.
            if self.animation_editor_widget_container.layout() is not None:
                 self.animation_editor_widget_container.layout().activate()
            # self.animation_editor_widget_container.updateGeometry() # May also help
            # self.animation_editor_widget_container.adjustSize() # This might try to shrink if content allows, but minHeight should prevent it.
                                                               # Let's see if just activate() is enough.

        # The QStackedWidget should also update its size hint if its current page's hint changes.
        # self.editor_stacked_widget.updateGeometry()

        # The item_editor_group (QGroupBox) will adjust to the QStackedWidget.
        # self.item_editor_group.updateGeometry()

        # The main dialog's adjustSize() might be called if the overall preferred size changes,
        # but since we have a fixed dialog minimum height, it's less critical here unless
        # content GROWS beyond the current dialog size.
        # self.adjustSize() 

        self._mark_editor_dirty_if_needed()

    def _on_anim_threshold_slider_changed(self, value: int):
        if not IMAGE_PROCESSING_AVAILABLE:
            return
        self.anim_threshold_value_label.setText(str(value))
        self._mark_editor_dirty_if_needed()

    def _handle_anim_browse_source_file(self):
        if not IMAGE_PROCESSING_AVAILABLE: return
        
        # Determine current directory to open file dialog
        current_browse_dir = ""
        if self._current_anim_source_filepath and os.path.exists(os.path.dirname(self._current_anim_source_filepath)):
            current_browse_dir = os.path.dirname(self._current_anim_source_filepath)
        elif self.animation_items_dir and os.path.exists(self.animation_items_dir): # Fallback to anim items dir
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
            self.anim_source_file_label.setToolTip(filepath) # Full path in tooltip

            # Auto-fill name if the name field is empty
            if not self.anim_item_name_edit.text().strip():
                self.anim_item_name_edit.setText(os.path.splitext(base_name)[0])
            
            # Clear previously processed frames and related info as new source is selected
            self._processed_logical_frames = None 
            self._processed_anim_source_fps = None
            self._processed_anim_source_loop_count = None
            

            # Update the frame info label
            self.anim_frame_info_label.setText("Frames: N/A | Source FPS: N/A | Press 'Process Frames'")
            
            # Update the main dialog preview to show nothing or a placeholder
            self._current_preview_anim_logical_frame = None # Clear for main preview
            self._update_preview() # This will clear or show placeholder on main preview

            # Mark editor dirty and update save button state
            self._editor_has_unsaved_changes = True # New source is a change
            self._update_save_this_item_button_state() # Save should be disabled until processed
            if self.anim_play_preview_button: # Disable play preview until processed
                self.anim_play_preview_button.setEnabled(False)
                self.anim_play_preview_button.setChecked(False)
                self.anim_play_preview_button.setText("▶️ Play Preview")

    def _handle_anim_process_and_preview(self):
        # print("Dialog DEBUG: _handle_anim_process_and_preview called.") # Optional
        if not IMAGE_PROCESSING_AVAILABLE:  # ... (return if not available) ...
            return
        # ... (return if no source) ...
        if not self._current_anim_source_filepath or not os.path.exists(self._current_anim_source_filepath):
            return

        # ... (stop ongoing editor preview timer as before) ...
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

        # --- NEW: Get Contrast Factor ---
        contrast_factor = 1.0  # Default
        if self.anim_contrast_slider:
            contrast_factor = self.anim_contrast_slider.value() / 100.0
        # --- END NEW ---

        print(f"Dialog DEBUG: Processing '{os.path.basename(self._current_anim_source_filepath)}' with options: resize='{resize_mode}', mono='{mono_mode}', thresh={threshold}, invert={invert}, contrast={contrast_factor:.2f}") # Optional

        # ... (set process button to "Processing...", QApplication.processEvents()) ...
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
            contrast_factor=contrast_factor,  # <<< PASS contrast_factor
            max_frames_to_import=0
        )
        # ... (process frames, fps, loop_count) ...
        self.anim_process_button.setText("Process Frames")
        self.anim_process_button.setEnabled(True)
        if frames and len(frames) > 0:
            # ... (store frames, fps, loop_count) ...
            self._processed_logical_frames = frames
            self._processed_anim_source_fps = fps
            self._processed_anim_source_loop_count = loop_count
            # ... (update anim_frame_info_label) ...
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
            # ... (handle processing failure) ...
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
        if self._preview_scroll_timer.isActive(): self._preview_scroll_timer.stop()
        if hasattr(self, '_anim_editor_preview_timer') and self._anim_editor_preview_timer.isActive(): self._anim_editor_preview_timer.stop()
        if hasattr(self, '_library_preview_anim_timer') and self._library_preview_anim_timer.isActive(): self._library_preview_anim_timer.stop()

        selected_active_graphic_data = self.default_startup_item_combo.currentData()
        # Ensure currentData() returns the dict {'path': relative_path, 'type': item_type} or None
        selected_active_graphic_relative_path = selected_active_graphic_data.get('path') if selected_active_graphic_data else None

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

if __name__ == '__main__':
    app = QApplication(sys.argv)
    dummy_presets_base = os.path.join(
        os.getcwd(), "TEMP_OLED_PRESETS_TEST_FULL_DIALOG")
    dummy_text_items_dir = os.path.join(dummy_presets_base, "TextItems")
    dummy_anim_items_dir = os.path.join(dummy_presets_base, "ImageAnimations")
    os.makedirs(dummy_text_items_dir, exist_ok=True)
    os.makedirs(dummy_anim_items_dir, exist_ok=True)

    with open(os.path.join(dummy_text_items_dir, "greeting_test.json"), 'w') as f:
        json.dump({
            "item_name": "Greeting Test", "item_type": "text", "text_content": "Hello from test JSON!",
            "font_family": "Arial", "font_size_px": 16, "animation_style": "scroll_left",
            "animation_params": {"speed_override_ms": 60, "pause_at_ends_ms": 1200}, "alignment": "left"
        }, f, indent=4)

    with open(os.path.join(dummy_anim_items_dir, "dummy_anim.json"), 'w') as f:
        json.dump({
            "item_name": "Dummy Animation", "item_type": "image_animation",
            "source_file_path_for_reference": "N/A",
            "import_options_used": {"resize_mode": "Stretch to Fit", "mono_conversion_mode": "Floyd-Steinberg Dither"},
            "frames_logical": []
        }, f, indent=4)

    dialog = OLEDCustomizerDialog(
        current_default_startup_item_path='TextItems/greeting_test.json',
        current_global_scroll_delay_ms=150,
        available_oled_items=[],
        user_oled_presets_base_path=dummy_presets_base,
        available_app_fonts=['TomThumb.ttf', 'AnotherAppFont.otf'],
        parent=None
    )

    def on_settings_changed(path, delay):
        print(
            f"Dialog Saved: Default Relative Path='{path}', Global Delay={delay}ms")
    dialog.global_settings_changed.connect(on_settings_changed)

    if dialog.exec():
        print("Dialog accepted.")
    else:
        print("Dialog cancelled.")

    import shutil
    if os.path.exists(dummy_presets_base):
        shutil.rmtree(dummy_presets_base)
    sys.exit()