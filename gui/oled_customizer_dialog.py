### START OF FILE gui/oled_customizer_dialog.py ###
### PART 1 OF 4 ###

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


# Constants for Scroll Speed Configuration
MIN_SPEED_LEVEL = 1
MAX_SPEED_LEVEL = 20
MIN_ACTUAL_DELAY_MS = 20
MAX_ACTUAL_DELAY_MS = 500
DEFAULT_GLOBAL_SCROLL_DELAY_MS_FALLBACK = 180

PREVIEW_LABEL_SCALE_FACTOR = 2 # For the main preview label
ANIM_EDITOR_PREVIEW_WIDTH = NATIVE_OLED_WIDTH # Native size for in-editor preview
ANIM_EDITOR_PREVIEW_HEIGHT = NATIVE_OLED_HEIGHT


class OLEDCustomizerDialog(QDialog):
    global_settings_changed = pyqtSignal(str, int) # (default_item_relative_path, global_scroll_delay_ms)
    dialog_closed = pyqtSignal()

    def __init__(self,
                 current_default_startup_item_path: str | None,
                 current_global_scroll_delay_ms: int,
                 available_oled_items: list, # This list is now just for initial state, dialog re-scans
                 user_oled_presets_base_path: str,
                 available_app_fonts: list[str],
                 parent: QWidget | None = None):
        super().__init__(parent)
        self.setWindowTitle("⚙️ OLED Content Library Manager")
        self.setMinimumSize(850, 700)

        self._initial_default_startup_item_path = current_default_startup_item_path
        self._initial_global_scroll_delay_ms = current_global_scroll_delay_ms
        self.user_oled_presets_base_path = user_oled_presets_base_path
        self.text_items_dir = os.path.join(self.user_oled_presets_base_path, "TextItems")
        self.animation_items_dir = os.path.join(self.user_oled_presets_base_path, "ImageAnimations")
        self.available_app_fonts = available_app_fonts

        # UI Elements - Common
        self.default_startup_item_combo: QComboBox
        self.global_scroll_speed_level_slider: QSlider
        self.global_scroll_speed_display_label: QLabel
        self.item_library_list: QListWidget
        self.new_text_item_button: QPushButton
        self.new_anim_item_button: QPushButton
        self.edit_selected_item_button: QPushButton
        self.delete_selected_item_button: QPushButton
        self.item_editor_group: QGroupBox
        self.oled_preview_label: QLabel # Main dialog preview
        self.button_box: QDialogButtonBox

        # Editor Stack
        self.editor_stacked_widget: QStackedWidget

        # Text Editor UI Elements
        self.text_editor_widget: QWidget
        self.item_name_edit: QLineEdit # For text item name
        self.text_content_edit: QLineEdit
        self.text_font_family_combo: QFontComboBox
        self.text_font_size_spinbox: QSpinBox
        self.text_scroll_checkbox: QCheckBox
        self.text_alignment_combo: QComboBox
        self.text_anim_override_speed_checkbox: QCheckBox
        self.text_anim_item_scroll_speed_spinbox: QSpinBox
        self.text_anim_pause_at_ends_spinbox: QSpinBox
        self.save_this_text_item_button: QPushButton

        # Animation Editor UI Elements
        self.animation_editor_widget_container: QWidget
        self.anim_item_name_edit: QLineEdit
        self.anim_source_file_label: QLabel
        self.anim_browse_button: QPushButton
        self.anim_resize_mode_combo: QComboBox
        self.anim_mono_conversion_combo: QComboBox
        self.anim_threshold_widget: QWidget
        self.anim_threshold_slider: QSlider
        self.anim_threshold_value_label: QLabel
        self.anim_invert_colors_checkbox: QCheckBox
        self.anim_playback_fps_spinbox: QSpinBox
        self.anim_loop_behavior_combo: QComboBox
        self.anim_process_button: QPushButton
        self.anim_frame_info_label: QLabel
        self.save_this_animation_button: QPushButton

        # State Variables
        self._preview_scroll_timer = QTimer(self)
        self._preview_scroll_timer.timeout.connect(self._scroll_preview_step)
        self._preview_current_scroll_offset = 0
        self._preview_text_pixel_width = 0
        self._preview_is_scrolling = False
        self._current_preview_font_object: QFont | None = None
        self._current_preview_anim_logical_frame: list[str] | None = None

        self._current_edited_item_path: str | None = None
        self._current_edited_item_type: str | None = None
        self._is_editing_new_item = False
        self._editor_has_unsaved_changes = False

        # Animation processing state
        self._current_anim_source_filepath: str | None = None
        self._processed_logical_frames: list[list[str]] | None = None
        self._processed_anim_source_fps: float | None = None
        self._processed_anim_source_loop_count: int | None = None
        
        # --- NEW: For In-Dialog Animation Preview Playback ---
        self._anim_editor_preview_timer = QTimer(self)
        self._anim_editor_preview_timer.timeout.connect(
            self._play_next_anim_editor_preview_frame)
        self._is_anim_editor_preview_playing: bool = False
        self._current_anim_editor_preview_frame_index: int = 0
        # Define the button attribute
        self.anim_play_preview_button: QPushButton | None = None

        self._init_ui()
        self._connect_signals()
        QTimer.singleShot(0, self._load_initial_data)
        self._update_editor_panel_visibility(None)

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
        text_editor_layout = QVBoxLayout(widget)
        text_editor_layout.setContentsMargins(0,0,0,0)

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
        text_editor_layout.addStretch(1)
        self.save_this_text_item_button = QPushButton("💾 Save Text Item")
        text_editor_layout.addWidget(self.save_this_text_item_button, 0, Qt.AlignmentFlag.AlignRight)
        return widget

    def _create_animation_editor_panel(self) -> QWidget:
        widget = QWidget()
        anim_editor_layout = QVBoxLayout(widget) # Main vertical layout for the panel
        anim_editor_layout.setContentsMargins(0,0,0,0)
        anim_editor_layout.setSpacing(8) # Consistent spacing

        # --- Animation Name ---
        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("Animation Name (used for filename):"))
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
        # import_options_group.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed) # Let content dictate height
        import_options_layout = QGridLayout(import_options_group)
        # ... (add widgets to import_options_layout as before: Resize, Mono, Threshold, Invert) ...
        import_options_layout.addWidget(QLabel("Resize Mode:"), 0, 0)
        self.anim_resize_mode_combo = QComboBox()
        self.anim_resize_mode_combo.addItems(["Stretch to Fit", "Fit (Keep Aspect, Pad)", "Crop to Center"])
        import_options_layout.addWidget(self.anim_resize_mode_combo, 0, 1, 1, 2) 

        import_options_layout.addWidget(QLabel("Monochrome Conversion:"), 1, 0)
        self.anim_mono_conversion_combo = QComboBox()
        self.anim_mono_conversion_combo.addItems(["Floyd-Steinberg Dither", "Simple Threshold", "Ordered Dither (Bayer 4x4)"])
        import_options_layout.addWidget(self.anim_mono_conversion_combo, 1, 1, 1, 2)

        self.anim_threshold_widget = QWidget() 
        threshold_layout_internal = QHBoxLayout(self.anim_threshold_widget) 
        threshold_layout_internal.setContentsMargins(0,0,0,0)
        threshold_layout_internal.addWidget(QLabel("Threshold (0-255):"))
        self.anim_threshold_slider = QSlider(Qt.Orientation.Horizontal)
        self.anim_threshold_slider.setRange(0, 255); self.anim_threshold_slider.setValue(128)
        threshold_layout_internal.addWidget(self.anim_threshold_slider, 1)
        self.anim_threshold_value_label = QLabel("128")
        self.anim_threshold_value_label.setMinimumWidth(30)
        threshold_layout_internal.addWidget(self.anim_threshold_value_label)
        import_options_layout.addWidget(self.anim_threshold_widget, 2, 0, 1, 3)
        self.anim_threshold_widget.setVisible(False) 

        self.anim_invert_colors_checkbox = QCheckBox("Invert Colors (Black/White)")
        import_options_layout.addWidget(self.anim_invert_colors_checkbox, 3, 0, 1, 3)
        
        import_options_layout.setColumnStretch(1, 1) 
        import_options_layout.setColumnStretch(2, 0) 
        anim_editor_layout.addWidget(import_options_group) # Add group to main vertical layout

        # --- Playback Options Group ---
        playback_options_group = QGroupBox("Playback Options")
        # playback_options_group.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed) # Let content dictate height
        playback_options_layout = QGridLayout(playback_options_group)
        # ... (add widgets to playback_options_layout as before: FPS, Loop) ...
        playback_options_layout.addWidget(QLabel("Target Playback FPS:"), 0, 0)
        self.anim_playback_fps_spinbox = QSpinBox()
        self.anim_playback_fps_spinbox.setRange(1, 60); self.anim_playback_fps_spinbox.setValue(15)
        playback_options_layout.addWidget(self.anim_playback_fps_spinbox, 0, 1)
        
        playback_options_layout.addWidget(QLabel("Loop Behavior:"), 1, 0)
        self.anim_loop_behavior_combo = QComboBox()
        self.anim_loop_behavior_combo.addItems(["Loop Infinitely", "Play Once"])
        playback_options_layout.addWidget(self.anim_loop_behavior_combo, 1, 1)
        
        playback_options_layout.setColumnStretch(1, 1) 
        anim_editor_layout.addWidget(playback_options_group) # Add group to main vertical layout

        # --- Action Buttons Layout (Process, Play Preview) ---
        action_buttons_layout = QHBoxLayout()
        self.anim_process_button = QPushButton("Process Frames")
        action_buttons_layout.addWidget(self.anim_process_button)
        
        self.anim_play_preview_button = QPushButton("▶️ Play Preview")
        self.anim_play_preview_button.setEnabled(False) 
        self.anim_play_preview_button.setCheckable(True) 
        self.anim_play_preview_button.toggled.connect(self._handle_anim_play_pause_preview_toggled)
        action_buttons_layout.addWidget(self.anim_play_preview_button)
        anim_editor_layout.addLayout(action_buttons_layout) # Add this HBox to main VBox

        # Frame Info Label
        self.anim_frame_info_label = QLabel("Frames: N/A | Source FPS: N/A")
        self.anim_frame_info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        anim_editor_layout.addWidget(self.anim_frame_info_label)
        
        # This stretch will push the save button to the bottom if there's extra space
        anim_editor_layout.addStretch(1) 
        
        # Save Button (at the very bottom of this panel)
        self.save_this_animation_button = QPushButton("💾 Save Animation Item")
        anim_editor_layout.addWidget(self.save_this_animation_button, 0, Qt.AlignmentFlag.AlignRight)

        if not IMAGE_PROCESSING_AVAILABLE: # Disable controls if module missing
            self.anim_item_name_edit.setEnabled(True) 
            for child_widget in widget.findChildren(QWidget):
                if child_widget != self.anim_item_name_edit:
                    child_widget.setEnabled(False)
            self.anim_source_file_label.setText("<i>Image processing module not available.</i>")
            self.anim_frame_info_label.setText("<i>(Processing Disabled)</i>")
            if self.anim_play_preview_button: self.anim_play_preview_button.setEnabled(False)
        return widget
    
    def _init_ui(self):
        main_layout = QVBoxLayout(self)

        # Global Settings Group (remains the same)
        global_settings_group = QGroupBox("Global OLED Settings")
        global_settings_layout = QHBoxLayout(global_settings_group)
        global_settings_layout.addWidget(QLabel("Active Graphic:"))
        self.default_startup_item_combo = QComboBox()
        self.default_startup_item_combo.setMinimumWidth(200)
        self.default_startup_item_combo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        global_settings_layout.addWidget(self.default_startup_item_combo, 1)
        global_settings_layout.addSpacing(20)
        global_settings_layout.addWidget(QLabel("Global Scroll Speed:"))
        self.global_scroll_speed_level_slider = QSlider(Qt.Orientation.Horizontal)
        self.global_scroll_speed_level_slider.setRange(MIN_SPEED_LEVEL, MAX_SPEED_LEVEL)
        self.global_scroll_speed_level_slider.setSingleStep(1); self.global_scroll_speed_level_slider.setPageStep(2)
        self.global_scroll_speed_level_slider.setTickInterval(max(1, (MAX_SPEED_LEVEL - MIN_SPEED_LEVEL) // 10))
        self.global_scroll_speed_level_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        global_settings_layout.addWidget(self.global_scroll_speed_level_slider, 1)
        self.global_scroll_speed_display_label = QLabel()
        self.global_scroll_speed_display_label.setMinimumWidth(90)
        self.global_scroll_speed_display_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        global_settings_layout.addWidget(self.global_scroll_speed_display_label)
        main_layout.addWidget(global_settings_group)

        self.splitter = QSplitter(Qt.Orientation.Horizontal)

        # Library Group (Left - remains the same)
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
        library_buttons_layout.addWidget(self.delete_selected_item_button, 1, 1)
        library_layout.addLayout(library_buttons_layout)
        self.splitter.addWidget(library_group)

        # Item Editor Group (Right)
        self.item_editor_group = QGroupBox("Item Editor") 
        # Allow the group box itself to expand vertically if its content needs it
        self.item_editor_group.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding) # <<< NEW
        item_editor_main_layout = QVBoxLayout(self.item_editor_group)
        
        self.editor_stacked_widget = QStackedWidget()
        # Allow stacked widget to expand based on its content's preference
        self.editor_stacked_widget.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding) # <<< NEW

        self.text_editor_widget = self._create_text_editor_panel()
        self.text_editor_widget.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred) 
        
        self.animation_editor_widget_container = self._create_animation_editor_panel()
        self.animation_editor_widget_container.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred) 
        
        self.editor_stacked_widget.addWidget(self.text_editor_widget)
        self.editor_stacked_widget.addWidget(self.animation_editor_widget_container)
        item_editor_main_layout.addWidget(self.editor_stacked_widget, 1) # Give stack stretch within group
        
        self.splitter.addWidget(self.item_editor_group)
        
        self.splitter.setStretchFactor(0, 1) # Library group (adjust as needed, e.g. 1 or 2)
        self.splitter.setStretchFactor(1, 3) # Editor group (give it more initial proportion, e.g. 3 or 5)
        
        # Comment out setSizes to let initial hints and stretch factors drive the size
        # self.splitter.setSizes([280, 570]) # <<< COMMENT OUT OR REMOVE

        main_layout.addWidget(self.splitter, 1) 

        # Live Preview Group (Main Dialog Preview - remains the same)
        preview_group = QGroupBox("Live Preview (Main)")
        preview_layout = QVBoxLayout(preview_group)
        self.oled_preview_label = QLabel("Preview")
        preview_label_width = NATIVE_OLED_WIDTH * PREVIEW_LABEL_SCALE_FACTOR
        preview_label_height = NATIVE_OLED_HEIGHT * PREVIEW_LABEL_SCALE_FACTOR
        self.oled_preview_label.setFixedSize(preview_label_width, preview_label_height)
        self.oled_preview_label.setStyleSheet("background-color: black; border: 1px solid #555555;")
        self.oled_preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        preview_layout.addWidget(self.oled_preview_label, 0, Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(preview_group)

        # Dialog Buttons (remains the same)
        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        main_layout.addWidget(self.button_box)

    def _update_editor_panel_visibility(self, item_type_to_show: str | None):
        current_editor_index = -1
        new_title = "Item Editor"
        newly_selected_editor_page = None

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

            # Force the new page and its container (the stacked widget) to recalculate size needs
            newly_selected_editor_page.layout().activate()
            # Let the page determine its best size first
            newly_selected_editor_page.adjustSize()

            # Now that the page has its size, the stacked widget should update its hint
            # Ask stacked widget to update based on current page
            self.editor_stacked_widget.updateGeometry()

            # Then the group box containing the stack
            self.item_editor_group.updateGeometry()
            self.item_editor_group.layout().activate()

            if hasattr(self, 'splitter') and self.splitter:

                self.splitter.updateGeometry()              
                pass

        else:
            self.item_editor_group.setVisible(False)
            self._current_edited_item_path = None
            self._current_edited_item_type = None
            self._is_editing_new_item = False
            self._editor_has_unsaved_changes = False
            self._clear_preview()

        self._update_save_this_item_button_state()

        # After everything, try to make the dialog adjust to its new overall content hint
        # This should be the last step.
        self.adjustSize()

    
    def _connect_signals(self):
        # Global Settings
        self.default_startup_item_combo.currentIndexChanged.connect(self._mark_editor_dirty_if_needed)
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
            self.anim_mono_conversion_combo.currentIndexChanged.connect(self._on_anim_mono_conversion_changed)
            self.anim_threshold_slider.valueChanged.connect(self._on_anim_threshold_slider_changed)
            
            self.anim_resize_mode_combo.currentIndexChanged.connect(self._mark_editor_dirty_if_needed)
            self.anim_invert_colors_checkbox.stateChanged.connect(self._mark_editor_dirty_if_needed)
            self.anim_playback_fps_spinbox.valueChanged.connect(self._mark_editor_dirty_if_needed)
            self.anim_loop_behavior_combo.currentIndexChanged.connect(self._mark_editor_dirty_if_needed)

            self.anim_process_button.clicked.connect(self._handle_anim_process_and_preview)
            self.save_this_animation_button.clicked.connect(self._handle_save_this_animation_item)

        # Dialog Buttons
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)

    def _load_initial_data(self):
        initial_speed_level = self._delay_ms_to_speed_level(self._initial_global_scroll_delay_ms)
        self.global_scroll_speed_level_slider.setValue(initial_speed_level)
        self._update_scroll_speed_display_label(initial_speed_level, self._initial_global_scroll_delay_ms)
        
        self._populate_font_family_combo() 
        self._populate_item_library_list() 

        if self._initial_default_startup_item_path:
            for i in range(self.default_startup_item_combo.count()):
                item_data = self.default_startup_item_combo.itemData(i)
                # itemData stores {'path': relative_path, 'type': item_type}
                if item_data and item_data.get('path') == self._initial_default_startup_item_path:
                    self.default_startup_item_combo.setCurrentIndex(i)
                    break
        
        self._update_library_button_states()
        self._update_save_this_item_button_state() # Initialize save button states

    def _populate_font_family_combo(self):
        self.text_font_family_combo.blockSignals(True)
        # QFontComboBox populates itself. We just set a default.
        default_font = QFont("Arial") # A common default
        self.text_font_family_combo.setCurrentFont(default_font)
        # If Arial wasn't found, it might select something else or be empty.
        # This is generally okay as QFontComboBox handles fallbacks.
        self.text_font_family_combo.blockSignals(False)

    def _populate_item_library_list(self):
        self.item_library_list.clear()
        self.default_startup_item_combo.clear()
        self.default_startup_item_combo.addItem("None (Show Default Text)", userData=None) # UserData is None for this
        
        os.makedirs(self.text_items_dir, exist_ok=True)
        os.makedirs(self.animation_items_dir, exist_ok=True)

        found_items_for_combo = []

        item_sources = [
            {"dir": self.text_items_dir, "type": "text", "label": "Text"},
            {"dir": self.animation_items_dir, "type": "animation", "label": "Animation"}
        ]

        for source in item_sources:
            if not os.path.isdir(source["dir"]): continue
            for filename in os.listdir(source["dir"]):
                if filename.endswith(".json"):
                    filepath = os.path.join(source["dir"], filename) # Full path
                    try:
                        with open(filepath, 'r', encoding='utf-8') as f: data = json.load(f)
                        item_name = data.get("item_name", os.path.splitext(filename)[0])
                        
                        qlist_item = QListWidgetItem(f"{item_name} ({source['label']})")
                        # Store full path for direct loading by dialog, relative path for config
                        relative_path = os.path.join(os.path.basename(source["dir"]), filename)
                        qlist_item.setData(Qt.ItemDataRole.UserRole, {
                            'path': filepath, 
                            'relative_path': relative_path, 
                            'type': source['type'], 
                            'name': item_name
                        })
                        self.item_library_list.addItem(qlist_item)
                        
                        # For default startup combo, store relative path and type
                        found_items_for_combo.append({
                            'name': item_name, 
                            'path': relative_path, 
                            'type': source['type']
                        })
                    except Exception as e: 
                        print(f"Error loading item metadata from {filepath}: {e}")
        
        found_items_for_combo.sort(key=lambda x: x['name'].lower())
        for item_info in found_items_for_combo:
            self.default_startup_item_combo.addItem(
                f"{item_info['name']} ({item_info['type'].capitalize()})", 
                userData={'path': item_info['path'], 'type': item_info['type']}
            )

    def _update_library_button_states(self):
        selected_item = self.item_library_list.currentItem()
        can_edit_delete = selected_item is not None
        self.edit_selected_item_button.setEnabled(can_edit_delete)
        self.delete_selected_item_button.setEnabled(can_edit_delete)

    def _on_library_selection_changed(self, current: QListWidgetItem | None, previous: QListWidgetItem | None):
        self._update_library_button_states()
        if self._prompt_save_unsaved_editor_changes() == QMessageBox.StandardButton.Cancel:
            if previous: self.item_library_list.setCurrentItem(previous)
            return
        
        # --- STOP any active in-dialog animation preview ---
        if self._is_anim_editor_preview_playing:
            self._anim_editor_preview_timer.stop()
            self._is_anim_editor_preview_playing = False
            if self.anim_play_preview_button: # Ensure button state is reset
                self.anim_play_preview_button.setChecked(False)
                self.anim_play_preview_button.setText("▶️ Play Preview")
        # --- END STOP ---
        
        self._update_editor_panel_visibility(None) 
        if current:
            item_data = current.data(Qt.ItemDataRole.UserRole)
            if item_data: 
                self._preview_item_from_path(item_data.get('path'))
        else:
            self._clear_preview() # Clears main preview

    # Modify _update_editor_panel_visibility:
    def _update_editor_panel_visibility(self, item_type_to_show: str | None):
        # --- STOP any active in-dialog animation preview when changing editor visibility ---
        if self._is_anim_editor_preview_playing:
            self._anim_editor_preview_timer.stop()
            self._is_anim_editor_preview_playing = False
            if self.anim_play_preview_button: # Ensure button state is reset
                self.anim_play_preview_button.setChecked(False)
                self.anim_play_preview_button.setText("▶️ Play Preview")
        # --- END STOP ---

        current_editor_index = -1
        # ... (rest of the method as before) ...
        new_title = "Item Editor"
        newly_selected_editor_page = None

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
            
            newly_selected_editor_page.layout().activate() 
            newly_selected_editor_page.adjustSize() 
            
            needed_height = newly_selected_editor_page.sizeHint().height() 
            
            self.item_editor_group.setMinimumHeight(needed_height) 
            self.item_editor_group.layout().activate() 
            self.item_editor_group.setVisible(True)
        else: 
            self.item_editor_group.setVisible(False)
            self._current_edited_item_path = None
            self._current_edited_item_type = None
            self._is_editing_new_item = False
            self._editor_has_unsaved_changes = False
            self._clear_preview() 
        
        self._update_save_this_item_button_state()
        
        if self.layout() is not None:
            self.layout().activate()
            
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

    # Modify _load_animation_item_into_editor:
    def _load_animation_item_into_editor(self, data: dict):
        if not IMAGE_PROCESSING_AVAILABLE:
            return

        # <<< ADD: Stop any ongoing preview when loading a new item >>>
        if self._is_anim_editor_preview_playing:
            self._anim_editor_preview_timer.stop()
            self._is_anim_editor_preview_playing = False
        if self.anim_play_preview_button:
            self.anim_play_preview_button.setChecked(False)
            self.anim_play_preview_button.setText("▶️ Play Preview")
        self._current_anim_editor_preview_frame_index = 0
        # <<< END ADD >>>

        self.anim_item_name_edit.setText(data.get("item_name", ""))
        # ... (rest of the method as before, loading options and first frame) ...
        source_ref = data.get("source_file_path_for_reference",
                              "<i>N/A (processed data loaded)</i>")
        base_source_ref = os.path.basename(source_ref)
        self.anim_source_file_label.setText(base_source_ref if len(
            base_source_ref) < 40 else "..." + base_source_ref[-37:])
        self.anim_source_file_label.setToolTip(source_ref)
        self._current_anim_source_filepath = None

        import_opts = data.get("import_options_used", {})
        self.anim_resize_mode_combo.setCurrentText(
            import_opts.get("resize_mode", "Stretch to Fit"))

        mono_mode_val = import_opts.get(
            "mono_conversion_mode", import_opts.get("dithering"))
        if mono_mode_val:
            self.anim_mono_conversion_combo.setCurrentText(mono_mode_val)
        else:
            self.anim_mono_conversion_combo.setCurrentIndex(0)

        self.anim_threshold_slider.setValue(
            import_opts.get("threshold_value", 128))
        self.anim_threshold_value_label.setText(
            str(self.anim_threshold_slider.value()))
        self.anim_invert_colors_checkbox.setChecked(
            import_opts.get("invert_colors", False))

        self.anim_playback_fps_spinbox.setValue(
            import_opts.get("playback_fps", 15))
        self.anim_loop_behavior_combo.setCurrentText(
            import_opts.get("loop_behavior", "Loop Infinitely"))

        self._on_anim_mono_conversion_changed()

        self._processed_logical_frames = data.get("frames_logical")
        self._processed_anim_source_fps = import_opts.get("source_fps")
        self._processed_anim_source_loop_count = import_opts.get(
            "source_loop_count")

        if self._processed_logical_frames:
            fps_text = f"{self._processed_anim_source_fps:.2f}" if self._processed_anim_source_fps is not None else "N/A"
            loop_text = str(self._processed_anim_source_loop_count) if self._processed_anim_source_loop_count is not None else \
                ("Infinite" if self._processed_anim_source_fps is not None and self._processed_anim_source_loop_count == 0 else "N/A")
            self.anim_frame_info_label.setText(
                f"Frames: {len(self._processed_logical_frames)} | Src FPS: {fps_text} | Loop: {loop_text}")
            # self._display_logical_frame_in_anim_preview(self._processed_logical_frames[0]) # <<< LINE REMOVED
            # The main _update_preview, called after _load_animation_item_into_editor finishes,
            # will handle showing the first frame on self.oled_preview_label.
            if self.anim_play_preview_button:
                self.anim_play_preview_button.setEnabled(True)
        else:

            self.anim_frame_info_label.setText("Frames: N/A | Source FPS: N/A")
            if self.anim_play_preview_button:
                self.anim_play_preview_button.setEnabled(False)

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
        
    ### START OF MISSING METHODS FOR oled_customizer_dialog.py ###

    # Place these methods within the OLEDCustomizerDialog class.
    # For example, after _connect_signals() and before _load_initial_data()

    def _preview_item_from_path(self, item_filepath: str | None):
        print(f"Dialog DEBUG: _preview_item_from_path called for: {item_filepath}") # DEBUG
        if not item_filepath or not os.path.exists(item_filepath) or not self.oled_preview_label:
            self._clear_preview()
            return
        try:
            with open(item_filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            item_type = data.get("item_type")
            item_name_debug = data.get("item_name", "Unknown") # DEBUG
            print(f"Dialog DEBUG: Item type '{item_type}', name '{item_name_debug}'") # DEBUG

            self._preview_scroll_timer.stop()
            self._preview_is_scrolling = False
            self._current_preview_anim_logical_frame = None 
            self._current_preview_font_object = None

            if item_type == "text":
                # ... (existing text preview logic - no changes needed here for now) ...
                text_to_preview = data.get("text_content", "")
                font_family = data.get("font_family", "Arial")
                font_size_px = data.get("font_size_px", 10)
                if not font_family or font_size_px <= 0: self._clear_preview(); return
                self._current_preview_font_object = QFont(font_family)
                self._current_preview_font_object.setPixelSize(font_size_px)
                fm = QFontMetrics(self._current_preview_font_object)
                self._preview_text_pixel_width = fm.horizontalAdvance(text_to_preview)
                anim_style = data.get("animation_style", "scroll_left")
                should_scroll_preview = anim_style != "static" and self._preview_text_pixel_width > NATIVE_OLED_WIDTH and text_to_preview.strip() != ""
                if should_scroll_preview:
                    self._preview_is_scrolling = True
                    self._preview_current_scroll_offset = NATIVE_OLED_WIDTH
                    preview_scroll_delay = self._initial_global_scroll_delay_ms
                    anim_params = data.get("animation_params", {})
                    if anim_params.get("speed_override_ms") is not None: preview_scroll_delay = anim_params.get("speed_override_ms")
                    self._preview_scroll_timer.start(max(20, preview_scroll_delay))
                else: self._preview_current_scroll_offset = 0
                self._render_preview_frame(override_text=text_to_preview)

            elif item_type == "image_animation":
                frames = data.get("frames_logical")
                if frames and isinstance(frames, list) and len(frames) > 0:
                    self._current_preview_anim_logical_frame = frames[0]
                    print(f"Dialog DEBUG: Set _current_preview_anim_logical_frame with {len(frames[0]) if frames[0] else 'no'} rows for main preview.") # DEBUG
                else:
                    self._current_preview_anim_logical_frame = None 
                    print("Dialog DEBUG: No logical frames found in animation item for main preview.") # DEBUG
                self._render_preview_frame() 
            else:
                print(f"Dialog DEBUG: Unknown item type '{item_type}' in _preview_item_from_path, clearing preview.") # DEBUG
                self._clear_preview() 

        except Exception as e:
            print(f"Error previewing item from path '{item_filepath}': {e}")
            self._clear_preview()

    # Find and REPLACE _render_preview_frame:
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
        
    def _clear_preview(self):
        self._preview_scroll_timer.stop()
        if self.oled_preview_label:  # Check if it exists
            pixmap = QPixmap(self.oled_preview_label.size())
            pixmap.fill(Qt.GlobalColor.black)
            self.oled_preview_label.setPixmap(pixmap)
        self._preview_text_pixel_width = 0
        self._preview_is_scrolling = False
        self._current_preview_font_object = None
        self._current_preview_anim_logical_frame = None

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
        
        
### START OF MISSING _update_preview METHOD for oled_customizer_dialog.py ###

    # Place this method within the OLEDCustomizerDialog class.
    # For example, before _preview_item_from_path()

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
                
    # Add a helper to just clear the main preview label's content
    def _clear_main_preview_content(self):
        if self.oled_preview_label:
            pixmap = QPixmap(self.oled_preview_label.size())
            pixmap.fill(Qt.GlobalColor.black)
            self.oled_preview_label.setPixmap(pixmap)
            self.oled_preview_label.setText("Preview") # Reset text if pixmap is cleared

    def _mark_editor_dirty_if_needed(self, *args):
        sender = self.sender()

        if sender == self.default_startup_item_combo or sender == self.global_scroll_speed_level_slider:
            return

        if self.item_editor_group.isVisible() and \
           (self._is_editing_new_item or self._current_edited_item_path is not None):

            self._editor_has_unsaved_changes = True

            active_editor_widget = self.editor_stacked_widget.currentWidget()

            if active_editor_widget == self.animation_editor_widget_container:
                anim_processing_option_senders = [
                    self.anim_resize_mode_combo,
                    self.anim_mono_conversion_combo,
                    self.anim_threshold_slider,
                    self.anim_invert_colors_checkbox
                ]
                if sender in anim_processing_option_senders:
                    if self._processed_logical_frames:
                        print(
                            "Dialog DEBUG: Animation processing option changed, invalidating processed frames.")
                        self._processed_logical_frames = None
                        # self.anim_preview_label.setText("<i>Options changed. Re-process.</i>") # REMOVED
                        # if self.anim_preview_label.pixmap() and not self.anim_preview_label.pixmap().isNull(): # REMOVED
                        #    self.anim_preview_label.clear() # REMOVED

                        self.anim_frame_info_label.setText(
                            "Frames: N/A | Source FPS: N/A | Options changed. Re-process.")  # Update info label
                        # Ensure main preview clears animation
                        self._current_preview_anim_logical_frame = None
                        if self.anim_play_preview_button:  # Disable play if options changed
                            self.anim_play_preview_button.setEnabled(False)
                            self.anim_play_preview_button.setChecked(False)
                            self.anim_play_preview_button.setText(
                                "▶️ Play Preview")

            self._update_save_this_item_button_state()
            self._update_preview()
    
    
    def _update_save_this_item_button_state(self):
        if not self.editor_stacked_widget or not self.item_editor_group.isVisible():
            self.save_this_text_item_button.setEnabled(False)
            if hasattr(self, 'save_this_animation_button') and self.save_this_animation_button:
                self.save_this_animation_button.setEnabled(False)
            return

        active_widget = self.editor_stacked_widget.currentWidget()
        can_save_text = False
        can_save_anim = False

        if active_widget == self.text_editor_widget:
            is_name_valid = bool(self.item_name_edit.text().strip())
            can_save_text = (
                self._editor_has_unsaved_changes or self._is_editing_new_item) and is_name_valid

        elif active_widget == self.animation_editor_widget_container:
            is_name_valid_anim = bool(self.anim_item_name_edit.text().strip())
            can_save_anim = IMAGE_PROCESSING_AVAILABLE and \
                (self._editor_has_unsaved_changes or self._is_editing_new_item) and \
                is_name_valid_anim and \
                (self._processed_logical_frames is not None and len(
                    self._processed_logical_frames) > 0)

        self.save_this_text_item_button.setEnabled(can_save_text)
        if hasattr(self, 'save_this_animation_button') and self.save_this_animation_button:
            self.save_this_animation_button.setEnabled(can_save_anim)
    
    
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
        
### START OF FILE gui/oled_customizer_dialog.py ###
### PART 4 OF 4 ###

    def _handle_save_this_text_item(self):
        item_name = self.item_name_edit.text().strip()
        if not item_name:
            QMessageBox.warning(self, "Save Error",
                                "Text Item Name cannot be empty.")
            self.item_name_edit.setFocus()
            return

        text_content = self.text_content_edit.text()  # Can be empty
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
            # Fallback if name is all special chars
            safe_filename_base = "untitled_text_item"
        suggested_filename = f"{safe_filename_base}.json"

        if self._is_editing_new_item or \
           (target_filepath and os.path.basename(target_filepath).lower() != suggested_filename.lower()):
            # "Save As" dialog needed
            save_path_suggestion = os.path.join(
                self.text_items_dir, suggested_filename)
            target_filepath_new, _ = QFileDialog.getSaveFileName(
                self, "Save Text Item As...", save_path_suggestion, "JSON files (*.json)")
            if not target_filepath_new:
                return  # User cancelled Save As
            target_filepath = target_filepath_new

        # Should only happen if it was existing and became None (e.g. file deleted outside)
        if not target_filepath:
            save_path_suggestion = os.path.join(
                self.text_items_dir, suggested_filename)
            target_filepath_new, _ = QFileDialog.getSaveFileName(
                self, "Save Text Item", save_path_suggestion, "JSON files (*.json)")
            if not target_filepath_new:
                return
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
                f"Edit Text Item: {item_name}")  # Update title

            # Refresh library and select the saved item
            # This also repopulates default_startup_item_combo
            self._populate_item_library_list()
            # Reselect in library
            for i in range(self.item_library_list.count()):
                q_item = self.item_library_list.item(i)
                # Compare full path for selection
                if q_item and q_item.data(Qt.ItemDataRole.UserRole).get('path') == target_filepath:
                    self.item_library_list.setCurrentItem(q_item)
                    break
        except Exception as e:
            QMessageBox.critical(self, "Save Error",
                                 f"Failed to save text item: {e}")

    def _handle_save_this_animation_item(self):
        if not IMAGE_PROCESSING_AVAILABLE:
            return

        item_name = self.anim_item_name_edit.text().strip()
        if not item_name:
            QMessageBox.warning(self, "Save Error",
                                "Animation Item Name cannot be empty.")
            self.anim_item_name_edit.setFocus()
            return

        if not self._processed_logical_frames or len(self._processed_logical_frames) == 0:
            QMessageBox.warning(
                self, "Save Error", "No frames have been processed. Please process an image/GIF first.")
            return

        import_options_used = {
            "resize_mode": self.anim_resize_mode_combo.currentText(),
            "mono_conversion_mode": self.anim_mono_conversion_combo.currentText(),
            "threshold_value": self.anim_threshold_slider.value() if self.anim_threshold_widget.isVisible() else 128,
            "invert_colors": self.anim_invert_colors_checkbox.isChecked(),
            "source_fps": self._processed_anim_source_fps,  # Can be None
            "playback_fps": self.anim_playback_fps_spinbox.value(),
            "loop_behavior": self.anim_loop_behavior_combo.currentText(),
            # max_frames_imported is an input to processing, not really an "option used" for playback
            # but can be stored for reference if needed.
        }

        item_data_to_save = {
            "item_name": item_name,
            "item_type": "image_animation",
            "source_file_path_for_reference": self._current_anim_source_filepath or "N/A",
            "import_options_used": import_options_used,
            "frames_logical": self._processed_logical_frames
        }

        target_filepath = self._current_edited_item_path if self._current_edited_item_type == 'animation' and not self._is_editing_new_item else None

        safe_filename_base = "".join(c if c.isalnum() or c in [
                                     ' ', '_', '-'] else '' for c in item_name).replace(' ', '_')
        if not safe_filename_base:
            safe_filename_base = "untitled_animation"
        suggested_filename = f"{safe_filename_base}.json"

        if self._is_editing_new_item or \
           (target_filepath and os.path.basename(target_filepath).lower() != suggested_filename.lower()):
            save_path_suggestion = os.path.join(
                self.animation_items_dir, suggested_filename)
            target_filepath_new, _ = QFileDialog.getSaveFileName(
                self, "Save Animation Item As...", save_path_suggestion, "JSON files (*.json)")
            if not target_filepath_new:
                return
            target_filepath = target_filepath_new

        if not target_filepath:
            save_path_suggestion = os.path.join(
                self.animation_items_dir, suggested_filename)
            target_filepath_new, _ = QFileDialog.getSaveFileName(
                self, "Save Animation Item", save_path_suggestion, "JSON files (*.json)")
            if not target_filepath_new:
                return
            target_filepath = target_filepath_new

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
                if q_item and q_item.data(Qt.ItemDataRole.UserRole).get('path') == target_filepath:
                    self.item_library_list.setCurrentItem(q_item)
                    break
        except Exception as e:
            QMessageBox.critical(self, "Save Error",
                                 f"Failed to save animation item: {e}")

    def _on_anim_mono_conversion_changed(self):
        if not IMAGE_PROCESSING_AVAILABLE:
            return
        show_threshold = self.anim_mono_conversion_combo.currentText() == "Simple Threshold"
        self.anim_threshold_widget.setVisible(show_threshold)
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
        print("Dialog DEBUG: _handle_anim_process_and_preview called.")
        if not IMAGE_PROCESSING_AVAILABLE:
            QMessageBox.warning(self, "Processing Error", "Image processing module is not available.")
            print("Dialog DEBUG: Image processing module not available for _handle_anim_process_and_preview.")
            return
        if not self._current_anim_source_filepath or not os.path.exists(self._current_anim_source_filepath):
            QMessageBox.warning(self, "Processing Error", "No valid source file selected to process.")
            print(f"Dialog DEBUG: No valid source file in _handle_anim_process_and_preview. Path: {self._current_anim_source_filepath}")
            return

        # Stop any ongoing in-dialog animation preview before processing new frames
        if hasattr(self, '_is_anim_editor_preview_playing') and self._is_anim_editor_preview_playing: # Check attribute existence
            if hasattr(self, '_anim_editor_preview_timer'): self._anim_editor_preview_timer.stop()
            self._is_anim_editor_preview_playing = False
            if hasattr(self, 'anim_play_preview_button') and self.anim_play_preview_button:
                self.anim_play_preview_button.setChecked(False)
                self.anim_play_preview_button.setText("▶️ Play Preview")
        if hasattr(self, '_current_anim_editor_preview_frame_index'): self._current_anim_editor_preview_frame_index = 0 


        resize_mode = self.anim_resize_mode_combo.currentText()
        mono_mode = self.anim_mono_conversion_combo.currentText()
        threshold = self.anim_threshold_slider.value() if self.anim_threshold_widget.isVisible() else 128
        invert = self.anim_invert_colors_checkbox.isChecked()
        
        print(f"Dialog DEBUG: Processing '{os.path.basename(self._current_anim_source_filepath)}' with options: resize='{resize_mode}', mono='{mono_mode}', thresh={threshold}, invert={invert}")

        self.anim_process_button.setEnabled(False)
        self.anim_process_button.setText("Processing...")
        
        if self.oled_preview_label: # Update main preview label to show processing status
             self.oled_preview_label.setText("<i>Processing image/GIF... Please wait.</i>")
             if self.oled_preview_label.pixmap() and not self.oled_preview_label.pixmap().isNull():
                 self.oled_preview_label.clear() # Clear any old image
        QApplication.processEvents() 

        frames, fps, loop_count = image_processing.process_image_to_oled_data(
            filepath=self._current_anim_source_filepath,
            resize_mode=resize_mode,
            mono_conversion_mode=mono_mode,
            threshold_value=threshold,
            invert_colors=invert,
            max_frames_to_import=0 
        )
        
        self.anim_process_button.setText("Process Frames") 
        self.anim_process_button.setEnabled(True)

        if frames and len(frames) > 0:
            print(f"Dialog DEBUG: Processing SUCCESS. Frames returned: {len(frames)}, FPS: {fps}, Loop: {loop_count}")
            self._processed_logical_frames = frames
            self._processed_anim_source_fps = fps
            self._processed_anim_source_loop_count = loop_count
            
            fps_text = f"{fps:.2f}" if fps is not None else "N/A"
            loop_text = str(loop_count) if loop_count is not None else ("Infinite" if fps is not None and loop_count == 0 else "N/A")

            self.anim_frame_info_label.setText(f"Frames: {len(frames)} | Src FPS: {fps_text} | Loop: {loop_text}")
            
            if self.anim_play_preview_button: self.anim_play_preview_button.setEnabled(True)
            
            self._editor_has_unsaved_changes = True 
            # Set the first frame of the processed animation for the main preview
            self._current_preview_anim_logical_frame = frames[0] 
            self._update_preview() # This will render the first frame on self.oled_preview_label
        else:
            print(f"Dialog DEBUG: Processing FAILED or returned no frames for '{self._current_anim_source_filepath}'. Frames object: {frames}")
            self._processed_logical_frames = None # Ensure it's cleared on failure
            if self.anim_play_preview_button: self.anim_play_preview_button.setEnabled(False)
            
            QMessageBox.critical(self, "Processing Failed", 
                                 f"Could not process the selected file: {os.path.basename(self._current_anim_source_filepath or '')}\n"
                                 "No frames were generated. Check console for details from image_processing module or try a different file/options.")
            
            self.anim_frame_info_label.setText("Frames: Error | Source FPS: Error")
            self._current_preview_anim_logical_frame = None 
            self._update_preview() # Update main preview to show nothing or placeholder

        self._update_save_this_item_button_state() 
        print(f"Dialog DEBUG: Save button enabled state after process: {self.save_this_animation_button.isEnabled() if hasattr(self, 'save_this_animation_button') else 'N/A (button not found)'}")
        
        
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
        # Prompt for item editor changes first
        if self.item_editor_group.isVisible() and self._editor_has_unsaved_changes:
            prompt_result = self._prompt_save_unsaved_editor_changes()
            if prompt_result == QMessageBox.StandardButton.Cancel:
                return  # Don't close dialog if user cancelled save prompt

        # Proceed with saving global settings
        selected_startup_path_data = self.default_startup_item_combo.currentData()
        selected_startup_relative_path = selected_startup_path_data.get(
            'path') if selected_startup_path_data else None

        # Get the most current global scroll delay from the slider
        current_global_delay_from_slider = self._speed_level_to_delay_ms(
            self.global_scroll_speed_level_slider.value())

        self.global_settings_changed.emit(
            selected_startup_relative_path, current_global_delay_from_slider)
        self._preview_scroll_timer.stop()
        super().accept()

    def reject(self):
        if self._prompt_save_unsaved_editor_changes() == QMessageBox.StandardButton.Cancel:
            return

        self._preview_scroll_timer.stop()
        self.dialog_closed.emit()
        super().reject()

    def closeEvent(self, event: QCloseEvent):  # Corrected type hint
        if self._prompt_save_unsaved_editor_changes() == QMessageBox.StandardButton.Cancel:
            event.ignore()
            return

        self._preview_scroll_timer.stop()
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