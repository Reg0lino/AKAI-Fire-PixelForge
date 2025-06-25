# AKAI_Fire_RGB_Controller/managers/oled_display_manager.py
from PyQt6.QtCore import QObject, pyqtSignal, QTimer, Qt, QBuffer, QIODevice
# Keep QFont for fallback text items
from PyQt6.QtGui import QImage, QPainter, QColor, QFont, QFontMetrics, QFontDatabase, QFontInfo
from PIL import Image, ImageFont, ImageDraw  # Crucial for PIL font objects
import os
import sys
import io
from utils import get_resource_path
# For get_resource_path (ensure this works for your project structure)
try:
    from ..utils import get_resource_path as resource_path_func
    UTILS_AVAILABLE = True
except ImportError:
    try:
        from utils import get_resource_path as resource_path_func
        UTILS_AVAILABLE = True
    except ImportError:
        print("OLEDDisplayManager WARNING: Could not import 'get_resource_path' from 'utils'. Resource font loading will likely fail.")
        UTILS_AVAILABLE = False
        def resource_path_func(relative_path):
            print(
                f"OLEDDisplayManager DUMMY resource_path_func for: {relative_path}")
            return os.path.join(".", relative_path)
try:
    from oled_utils import oled_renderer
    OLED_RENDERER_AVAILABLE = True
except ImportError as e:
    print(
        f"OLEDDisplayManager WARNING: Could not import oled_renderer: {e}. OLED functionality will be limited.")
    OLED_RENDERER_AVAILABLE = False

    class oled_renderer_placeholder:  # Minimal placeholder
        OLED_WIDTH = 128
        OLED_HEIGHT = 64
        @staticmethod
        def render_text_to_packed_buffer(
            text, font_override, offset_x, center_if_not_scrolling): return None
        @staticmethod
        def pack_pil_image_to_7bit_stream(pil_image): return None
        @staticmethod
        def get_text_actual_width(text, font): return len(text) * 6
        @staticmethod
        def get_blank_packed_bitmap(): return bytearray(1176)  # Placeholder size
    if 'oled_renderer' not in globals():
        oled_renderer = oled_renderer_placeholder()

class OLEDDisplayManager(QObject):
    request_send_bitmap_to_fire = pyqtSignal(bytearray)
    request_update_mirror_widget = pyqtSignal(bytearray) 
    builtin_startup_animation_finished = pyqtSignal()
    active_graphic_pause_state_changed = pyqtSignal(
        bool)  # True if paused, False if resumed/playing
    # Default scroll delays for user-defined TEXT Active Graphics
    DEFAULT_TEXT_ITEM_SCROLL_STEP_DELAY_MS = 50
    DEFAULT_TEXT_ITEM_SCROLL_RESTART_DELAY_MS = 2000
    FEEDBACK_FONT_FILENAME = "TomThumb.ttf"
    FEEDBACK_FONT_SIZE_PX = 60
    PERSISTENT_OVERRIDE_FONT_FAMILY = "Arial"  # Or another small, clear system font
    PERSISTENT_OVERRIDE_FONT_SIZE_PX = 10
    APP_DEFAULT_OLED_MESSAGE_TEXT = "AKAI  Fire  PixelForge  by  Reg0lino  =^.^= "
    TOMTHUMB_FAMILY_NAME = "Tom Thumb"

    def __init__(self, akai_fire_controller_ref, available_app_fonts: list[str], parent: QObject | None = None):
        super().__init__(parent)
        # --- Core References and Constants ---
        self.OLED_WIDTH = 128
        self.OLED_HEIGHT = 64
        self.akai_controller = akai_fire_controller_ref
        self.available_app_fonts = available_app_fonts # This is still needed for the customizer dialog
        
        # --- Font Objects (now QFont) ---
        self.feedback_qfont: QFont | None = None
        self.persistent_override_qfont: QFont | None = None
        # --- Timers (Initialized once) ---
        self._animation_timer = QTimer(self)
        self._text_scroll_timer = QTimer(self)
        self._temporary_message_revert_timer = QTimer(self)
        self._temporary_message_revert_timer.setSingleShot(True)
        self._startup_anim_timer = QTimer(self)
        # --- Initialize All State Attributes ---
        self.full_reset()
        # --- Connect Signals to Consolidated Handlers ---
        self._animation_timer.timeout.connect(self._play_next_animation_frame)
        self._text_scroll_timer.timeout.connect(self._scroll_text_step)
        self._temporary_message_revert_timer.timeout.connect(self._revert_from_temporary_display)
        self._startup_anim_timer.timeout.connect(self._play_next_startup_frame)
        # --- Final Setup: Load QFont objects ---
        self._load_feedback_font()
        self._load_persistent_override_font()

    def _play_next_startup_frame(self):
        """Displays the next frame of the built-in startup animation."""
        if not self.is_startup_animation_playing or self._startup_anim_frame_index >= len(self._startup_anim_frames):
            self._startup_anim_timer.stop()
            self.is_startup_animation_playing = False
            self.builtin_startup_animation_finished.emit()
            # Restore active graphic after animation
            self.set_active_graphic(self._active_graphic_item_data)
            return

        packed_bitmap = self._startup_anim_frames[self._startup_anim_frame_index]
        self.request_send_bitmap_to_fire.emit(packed_bitmap)
        self.request_update_mirror_widget.emit(packed_bitmap)
        self._startup_anim_frame_index += 1

    def _revert_from_temporary_display(self):
        """
        Restores the persistent OLED state after a temporary message's timer expires.
        """
        self._is_temporary_message_active = False
        self._temp_message_text = None
        # Safely re-apply the correct persistent state.
        self._apply_current_oled_state(called_by_revert=True)

    def _get_text_pixel_width(self, text: str, font: QFont) -> int:
        """Calculates the pixel width of a string for a given QFont."""
        if not font or not text:
            return 0
        fm = QFontMetrics(font)
        return fm.horizontalAdvance(text)

    def _render_and_send_text_frame(self, font, alignment="center", text_override=None):
        """Renders and sends a single text frame."""
        text_to_render = text_override if text_override is not None else self.current_text_for_scrolling
        
        logical_image = Image.new('1', (self.OLED_WIDTH, self.OLED_HEIGHT), 0)
        draw = ImageDraw.Draw(logical_image)
        
        text_width = self._get_text_pixel_width(text_to_render, font)
        try:
            bbox = font.getbbox(text_to_render)
            text_height = bbox[3] - bbox[1]
            y_pos = (self.OLED_HEIGHT - text_height) // 2 - bbox[1]
        except AttributeError:
            text_height = font.size
            y_pos = (self.OLED_HEIGHT - text_height) // 2
        x_pos = self.current_scroll_offset_x
        if not self.current_text_is_scrolling and text_override is None: 
            if alignment == "center":
                x_pos = (self.OLED_WIDTH - text_width) // 2
            elif alignment == "right":
                x_pos = self.OLED_WIDTH - text_width
        draw.text((x_pos, y_pos), text_to_render, font=font, fill=1)
        packed_bitmap = self._pack_pil_image_to_7bit_stream(logical_image)
        if packed_bitmap:
            self.request_send_bitmap_to_fire.emit(packed_bitmap)
            self.request_update_mirror_widget.emit(packed_bitmap)

    def _render_and_send_logical_frame(self, logical_frame: list[str]):
        """Renders a single logical frame and sends it to the hardware."""
        image = Image.new('1', (self.OLED_WIDTH, self.OLED_HEIGHT), 0)
        pixels = image.load()
        for y, row_str in enumerate(logical_frame):
            for x, char in enumerate(row_str):
                if char == '1':
                    pixels[x, y] = 1
        packed_bitmap = self._pack_pil_image_to_7bit_stream(image)
        if packed_bitmap:
            self.request_send_bitmap_to_fire.emit(packed_bitmap)
            self.request_update_mirror_widget.emit(packed_bitmap)

    def _pack_pil_image_to_7bit_stream(self, pil_image: Image.Image) -> bytearray | None:
        """Packs a 1-bit PIL image into the Fire's 7-bit SysEx format."""
        if pil_image.mode != '1' or pil_image.size != (self.OLED_WIDTH, self.OLED_HEIGHT):
            return None
            
        pixels = pil_image.load()
        def pixel_accessor(x, y):
            return pixels[x, y] != 0
        packed_stream = bytearray(1176)
        a_bit_mutate = [
            [13, 19, 25, 31, 37, 43, 49], [0, 20, 26, 32, 38, 44, 50],
            [1, 7, 27, 33, 39, 45, 51], [2, 8, 14, 34, 40, 46, 52],
            [3, 9, 15, 21, 41, 47, 53], [4, 10, 16, 22, 28, 48, 54],
            [5, 11, 17, 23, 29, 35, 55], [6, 12, 18, 24, 30, 36, 42]
        ]
        for y_coord in range(self.OLED_HEIGHT):
            for x_coord in range(self.OLED_WIDTH):
                if pixel_accessor(x_coord, y_coord):
                    fire_col = x_coord + self.OLED_WIDTH * (y_coord // 8)
                    fire_y = y_coord % 8
                    k = a_bit_mutate[fire_y][fire_col % 7]
                    group_offset = (fire_col // 7) * 8
                    byte_offset = k // 7
                    bit_in_byte = k % 7
                    packed_idx = group_offset + byte_offset
                    if 0 <= packed_idx < len(packed_stream):
                        packed_stream[packed_idx] |= (1 << bit_in_byte)
        return packed_stream

    def _load_feedback_font(self):
        """Loads the TomThumb.ttf as a QFont for system feedback messages."""
        self.feedback_qfont = QFont() # Start with a default
        try:
            font_path = resource_path_func(os.path.join("resources", "fonts", self.FEEDBACK_FONT_FILENAME))
            if os.path.exists(font_path):
                font_id = QFontDatabase.addApplicationFont(font_path)
                if font_id != -1:
                    family = QFontDatabase.applicationFontFamilies(font_id)[0]
                    self.feedback_qfont = QFont(family, pointSize=-1)
                    self.feedback_qfont.setPixelSize(self.FEEDBACK_FONT_SIZE_PX)
                else:
                    print(f"OLED Mgr WARNING: Failed to register feedback font '{self.FEEDBACK_FONT_FILENAME}'.")
            else:
                print(f"OLED Mgr WARNING: Feedback font file not found at '{font_path}'.")
        except Exception as e:
            print(f"OLED Mgr ERROR: Exception loading feedback font: {e}")

    def _load_persistent_override_font(self):
        """Creates a standard QFont for persistent override messages (e.g. SAMPLING)."""
        # This will not fail or warn, as Qt can always find a suitable substitute for "Arial".
        self.persistent_override_qfont = QFont(self.PERSISTENT_OVERRIDE_FONT_FAMILY)
        self.persistent_override_qfont.setPixelSize(self.PERSISTENT_OVERRIDE_FONT_SIZE_PX)

    def _load_pil_font_for_text_item(self, font_family: str, font_size_px: int) -> QFont:
        """
        Creates a QFont object for the given parameters. This is now the primary
        method for preparing a font for rendering, leveraging Qt's robust font engine.
        """
        font = QFont(font_family)
        font.setPixelSize(int(font_size_px))
        # Optional: For very crisp, non-aliased rendering of pixel fonts
        # font.setStyleStrategy(QFont.StyleStrategy.NoAntialias)
        return font

    def update_global_text_item_scroll_delay(self, new_delay_ms: int):
        """
        Updates the global default scroll speed for text items.
        This is called by MainWindow from the OLED Customizer dialog.
        """
        if new_delay_ms is None:
            new_delay_ms = self.DEFAULT_TEXT_ITEM_SCROLL_STEP_DELAY_MS
        
        # This global setting is not used directly by timers anymore.
        # Instead, it's read by _start_text_display when a new text item begins.
        # So we just need to store it. We'll rename the attribute for clarity.
        self.global_default_scroll_delay_ms = max(20, int(new_delay_ms))
        # The old logic to check for active scrolling and update the timer
        # is no longer needed here, as _start_text_display handles setting
        # the initial timer interval correctly based on the item's properties
        # or this new global default.

    def begin_external_oled_override(self):
        """
        Called when an external module (e.g., a game) wants to take full control of the OLED.
        Stops all current ODM activity and prepares for external updates.
        """
        # print("OLED Mgr INFO: Beginning external OLED override.")
        self.stop_all_activity()  # Stops all internal timers (text scroll, anim, temp messages)
        # Optionally, store the very last bitmap ODM sent if needed for a flicker-free transition,
        # or just expect the external controller to send its first frame immediately.
        # For now, stop_all_activity should leave the OLED as is or blanked by the last action.
        # Set a flag to indicate external control (ODM should not try to render anything itself)
        if not hasattr(self, '_is_external_override_active'):  # Define if not exists
            self._is_external_override_active = False
        self._is_external_override_active = True
        # It's good practice to send a blank frame if the external controller might take time.
        # However, our DOOM game will likely send its first frame very quickly.
        # If you see a flicker or old content, uncommenting this might help:
        # if OLED_RENDERER_AVAILABLE:
        #     blank_bitmap = oled_renderer.get_blank_packed_bitmap()
        #     if blank_bitmap:
        #         self.request_send_bitmap_to_fire.emit(blank_bitmap)

    def end_external_oled_override(self):
        """
        Called when an external module relinquishes control of the OLED.
        ODM should resume its normal operation (e.g., display Active Graphic or default).
        """
        # print("OLED Mgr INFO: Ending external OLED override.")
        if not hasattr(self, '_is_external_override_active'):
            self._is_external_override_active = True  # Should have been set by begin_
        self._is_external_override_active = False
        # Re-apply the current persistent state (Active Graphic, Persistent App Override, or App Default)
        # This will re-start any necessary animations or scrolling.
        # called_by_revert ensures it bypasses temp msg check
        self._apply_current_oled_state(called_by_revert=True)

    def play_builtin_startup_animation(self, frames: list[bytearray], frame_duration_ms: int):
        self.stop_all_activity()
        self._startup_anim_frames = frames
        self._startup_anim_frame_index = 0
        self.is_startup_animation_playing = True
        self._startup_anim_timer.start(frame_duration_ms)
        self._play_next_startup_frame()

    def _play_next_builtin_startup_frame(self):
        if not self._is_builtin_startup_animation_playing or \
            self._current_builtin_startup_animation_frame_index >= len(self._builtin_startup_animation_frames):
            self._is_builtin_startup_animation_playing = False
            self._builtin_startup_animation_frames.clear()
            self.builtin_startup_animation_finished.emit()  # Signal completion
            # Transition to the persistent state (Active Graphic or app default)
            self._apply_current_oled_state()
            return
        frame_bitmap = self._builtin_startup_animation_frames[
            self._current_builtin_startup_animation_frame_index]
        if frame_bitmap:
            self.request_send_bitmap_to_fire.emit(frame_bitmap)
        self._current_builtin_startup_animation_frame_index += 1
        QTimer.singleShot(self._builtin_startup_animation_frame_duration,
                            self._play_next_builtin_startup_frame)

    def set_active_graphic(self, item_data: dict | None):
        """
        The main entry point to set the persistent graphic on the OLED.
        This method is a simple, non-blocking dispatcher.
        """
        self.stop_all_activity()
        self._active_graphic_item_data = item_data
        self._apply_current_oled_state()

    def set_display_text(self, text: str | None, font_family=None, font_size_px=None, animation_style=None, animation_params=None, alignment=None):
        """Handles the logic for displaying a text item."""
        self.stop_all_activity()
        self.current_text_for_scrolling = text or "AKAI Fire"
        
        try:
            if font_family and font_size_px:
                font = ImageFont.truetype(font_family, font_size_px)
            else:
                font = self.primary_font
        except (IOError, OSError):
            font = self.primary_font
            
        text_width = self._get_text_pixel_width(self.current_text_for_scrolling, font)
        self.current_text_pixel_width = text_width
        is_scrolling = (animation_style == "scroll_left") and (text_width > self.OLED_WIDTH)
        self.current_text_is_scrolling = is_scrolling
        if is_scrolling:
            anim_params = animation_params or {}
            self.current_text_item_scroll_delay_ms = anim_params.get("speed_override_ms", self.global_text_item_scroll_delay_ms)
            self.current_text_pause_at_ends_ms = anim_params.get("pause_at_ends_ms", 1000)
            self.current_scroll_offset_x = -self.OLED_WIDTH
            self.text_scroll_timer.start(max(20, self.current_text_item_scroll_delay_ms))
        else:
            self.current_scroll_offset_x = 0
            self._render_and_send_text_frame(font, alignment)

    def _apply_current_oled_state(self, called_by_revert: bool = False):
        """
        Central dispatcher to determine and apply the correct OLED content.
        This method is now non-recursive and handles state priority.
        """
        # Priority 1: Do nothing if a temporary message is active.
        if self._is_temporary_message_active and not called_by_revert:
            return
        # Priority 2: Do nothing if an external override (like DOOM) is active.
        if self._is_external_override_active and not called_by_revert:
            return
        # Priority 3: Do nothing if the startup animation is playing.
        if self._is_startup_animation_playing:
            return
        # If manually paused, show a static frame but don't start timers.
        if self._is_manually_paused:
            self._render_current_state_as_static_frame()
            return
        # Stop any lingering activity from a previous state.
        self.stop_all_activity()
        # Priority 4: Display the persistent override text if it exists.
        if self.persistent_override_text is not None:
            self._display_persistent_override_text()
            return
        # Priority 5: Display the active graphic if it exists.
        if self._active_graphic_item_data:
            item_type = self._active_graphic_item_data.get("item_type")
            if item_type == "image_animation":
                self._start_animation_display(self._active_graphic_item_data)
                return
            elif item_type == "text":
                self._start_text_display(self._active_graphic_item_data)
                return
        # Priority 6 (Fallback): Display the hardcoded app default message.
        self._display_hardcoded_app_default_message()

    def _display_persistent_override_text(self):
        if self.persistent_override_text is None or not OLED_RENDERER_AVAILABLE:
            self.clear_display_content()
            return
        # Use the dedicated persistent override QFont
        font_to_use = self.persistent_override_qfont or QFont()
        self._render_text_frame(
            text=self.persistent_override_text,
            font=font_to_use,
            alignment="center",
            offset_x=0
        )

    def _play_next_custom_animation_frame(self): # For Active Graphic Animations
        # print(f"ODM DEBUG: _play_next_custom_animation_frame CALLED. Playing: {self._is_custom_animation_playing}") # <<< ADD
        if not self._is_custom_animation_playing or \
            not self._custom_animation_logical_frames: # Check if frames exist
            print("ODM DEBUG: _play_next_custom_animation_frame - Bailing early: Not playing or no frames.") # <<< ADD
            if self._custom_animation_timer.isActive(): # Stop timer if it was somehow running
                self._custom_animation_timer.stop()
            self._is_custom_animation_playing = False # Ensure flag is false
            return
        # Check frame index before accessing
        if self._custom_animation_current_frame_index >= len(self._custom_animation_logical_frames):
            # print(f"ODM DEBUG: Frame index {self._custom_animation_current_frame_index} >= frame count {len(self._custom_animation_logical_frames)}. Checking loop behavior.") # <<< ADD
            if self._is_custom_animation_playing and self._custom_animation_logical_frames and \
                self._custom_animation_current_frame_index >= len(self._custom_animation_logical_frames):
                
                if self._custom_animation_loop_behavior == "Loop Infinitely":
                    # print("ODM DEBUG: Looping animation.") # <<< ADD
                    self._custom_animation_current_frame_index = 0
                else: # Play Once
                    # print(f"OLED Mgr INFO: Active Graphic Animation finished (played once). Stopping timer.") # <<< MODIFIED (was INFO)
                    self._custom_animation_timer.stop()
                    self._is_custom_animation_playing = False
                    self._active_graphic_item_data = None 
                    self._active_graphic_item_type = None
                    # self._custom_animation_logical_frames = None # Clearing frames here means it cannot be restarted by set_active_graphic again without reloading
                    self._apply_current_oled_state() 
                    return
            else: # Should not be reached if above conditions are met, but as a safeguard
                print("ODM DEBUG: _play_next_custom_animation_frame - Bailing (unexpected state after index check).") # <<< ADD
                self._custom_animation_timer.stop()
                self._is_custom_animation_playing = False
                return
        # After loop check, re-verify index just in case logical_frames became empty or very short
        if self._custom_animation_current_frame_index >= len(self._custom_animation_logical_frames):
            print(f"ODM WARNING: Frame index {self._custom_animation_current_frame_index} still out of bounds after loop for {len(self._custom_animation_logical_frames)} frames. Stopping.") # <<< ADD
            self._custom_animation_timer.stop(); self._is_custom_animation_playing = False
            self._apply_current_oled_state() 
            return
        # print(f"ODM DEBUG: Attempting to display frame {self._custom_animation_current_frame_index}/{len(self._custom_animation_logical_frames) -1}") # <<< ADD
        logical_frame = self._custom_animation_logical_frames[self._custom_animation_current_frame_index]
        # print(f"ODM DEBUG: Logical frame data (first row sample): {logical_frame[0][:20] if logical_frame and logical_frame[0] else 'N/A'}") # <<< ADD (optional, can be noisy)
        pil_image = self._logical_frame_to_pil_image(logical_frame)
        # print(f"ODM DEBUG: _logical_frame_to_pil_image returned: {'PIL.Image object' if pil_image else 'None'}") # <<< ADD
        if pil_image and OLED_RENDERER_AVAILABLE:
            packed_data = oled_renderer.pack_pil_image_to_7bit_stream(pil_image)
            # print(f"ODM DEBUG: pack_pil_image_to_7bit_stream returned: Data with length {len(packed_data) if packed_data else 0} bytes") # <<< ADD
            if packed_data:
                # print(f"ODM DEBUG: Emitting request_send_bitmap_to_fire for frame {self._custom_animation_current_frame_index}") # <<< ADD
                self.request_send_bitmap_to_fire.emit(packed_data)
            # else:
                # print(f"ODM ERROR: Failed to pack PIL image for custom animation frame {self._custom_animation_current_frame_index}.") # <<< ADD
        # elif not pil_image:
            # print(f"ODM ERROR: pil_image is None for frame {self._custom_animation_current_frame_index}.") # <<< ADD
        # elif not OLED_RENDERER_AVAILABLE:
            # print("ODM WARNING: OLED_RENDERER_AVAILABLE is False, cannot pack/send frame.") # <<< ADD
        self._custom_animation_current_frame_index += 1

    def _scroll_active_graphic_text_step(self):
        if not self._active_graphic_text_is_scrolling or \
            self._active_graphic_text_content is None:
            if self._active_graphic_text_scroll_timer.isActive():
                self._active_graphic_text_scroll_timer.stop()
            self._active_graphic_text_is_scrolling = False
            return
        # To scroll RIGHT TO LEFT, the X drawing coordinate decreases.
        self._active_graphic_text_current_scroll_offset -= 2  # <<< CHANGE HERE (decrement)
        if self._active_graphic_text_pixel_width == 0: # Recalculate if needed
            q_font_for_metrics = QFont(self._active_graphic_text_font_family, pointSize=-1)
            q_font_for_metrics.setPixelSize(self._active_graphic_text_font_size_px or 10)
            fm = QFontMetrics(q_font_for_metrics)
            self._active_graphic_text_pixel_width = fm.horizontalAdvance(self._active_graphic_text_content)
        # Loop condition: when the RIGHT edge of the text has passed the LEFT edge of the screen.
        # Text is drawn starting at self._active_graphic_text_current_scroll_offset.
        # Its right edge is at self._active_graphic_text_current_scroll_offset + self._active_graphic_text_pixel_width.
        # This should be < 0 for it to be fully off-screen left.
        if (self._active_graphic_text_current_scroll_offset + self._active_graphic_text_pixel_width) < 0: # <<< CHANGE HERE
            self._active_graphic_text_current_scroll_offset = self.OLED_WIDTH # Reset to off-screen right
            self._active_graphic_text_scroll_timer.setInterval(self._active_graphic_text_restart_delay_ms) 
        else:
            self._active_graphic_text_scroll_timer.setInterval(self._active_graphic_text_step_delay_ms)
        
        self._render_and_send_active_graphic_text_frame()

    def _display_hardcoded_app_default_message(self):
        print(f"OLED Mgr INFO: Displaying hardcoded app default message using '{self.TOMTHUMB_FAMILY_NAME}' @ {self.FEEDBACK_FONT_SIZE_PX}px.")
        print(f"  Current self.global_text_item_scroll_delay_ms BEFORE setting _active_graphic_text_step_delay_ms: {self.global_text_item_scroll_delay_ms}") #<<< DEBUG
        default_item_data_simulated = {
            "item_name": "AppDefaultMessage", "item_type": "text",
            "text_content": self.APP_DEFAULT_OLED_MESSAGE_TEXT,
            "font_family": self.TOMTHUMB_FAMILY_NAME, 
            "font_size_px": self.FEEDBACK_FONT_SIZE_PX,
            "animation_style": "scroll_left", "alignment": "left",
            "animation_params": {
                "speed_override_ms": None, # This means it should use global
                "pause_at_ends_ms": self.DEFAULT_TEXT_ITEM_SCROLL_RESTART_DELAY_MS
            }
        }
        self._active_graphic_item_data = default_item_data_simulated
        self._active_graphic_item_type = "text"
        self._active_graphic_text_content = default_item_data_simulated["text_content"]
        self._active_graphic_text_font_family = default_item_data_simulated["font_family"]
        self._active_graphic_text_font_size_px = default_item_data_simulated["font_size_px"]
        self._active_graphic_text_alignment = default_item_data_simulated["alignment"]
        self._active_graphic_text_scroll_if_needed = (default_item_data_simulated["animation_style"] == "scroll_left")
        anim_params = default_item_data_simulated["animation_params"]
        # Explicitly check global_text_item_scroll_delay_ms
        delay_to_use_for_default_msg = self.global_text_item_scroll_delay_ms
        if delay_to_use_for_default_msg is None:
            print("ODM WARNING (_display_hardcoded_app_default_message): self.global_text_item_scroll_delay_ms is None! Using fallback.")
            delay_to_use_for_default_msg = self.DEFAULT_TEXT_ITEM_SCROLL_STEP_DELAY_MS # Fallback
        self._active_graphic_text_step_delay_ms = anim_params.get("speed_override_ms") \
            if anim_params.get("speed_override_ms") is not None \
            else delay_to_use_for_default_msg # Use the checked/fallback value
        print(f"  Set _active_graphic_text_step_delay_ms FOR DEFAULT MSG to: {self._active_graphic_text_step_delay_ms}") #<<< DEBUG
        self._active_graphic_text_restart_delay_ms = anim_params.get(
            "pause_at_ends_ms", self.DEFAULT_TEXT_ITEM_SCROLL_RESTART_DELAY_MS
        )
        self._start_or_display_active_graphic_text_internal()

    def show_system_message(self, text: str, duration_ms: int = 1500, scroll_if_needed: bool = True):
        """
        Displays a high-priority, temporary message, safely pausing any current activity.
        """
        if self._is_startup_animation_playing:
            return
        # Stop current activity and set the high-priority flag
        self.stop_all_activity()
        self._is_temporary_message_active = True
        self._temp_message_text = text
        # Use the dedicated feedback QFont
        font_to_use = self.feedback_qfont or QFont()
        
        # We will simply center temporary messages. If they are too long, they will be clipped.
        # This simplifies the state machine immensely.
        self._render_text_frame(
            text=self._temp_message_text,
            font=font_to_use,
            alignment="center",
            offset_x=0
        )
        # Schedule the revert action
        self._temporary_message_revert_timer.start(duration_ms)

    def _render_and_send_temporary_message_frame(self):
        if not self._is_temporary_message_active or \
            self._current_temporary_message_text is None or \
            not self.feedback_pil_font or \
            not OLED_RENDERER_AVAILABLE:
            # print("OLED Mgr DEBUG: Conditions not met for _render_and_send_temporary_message_frame.") # Optional
            if OLED_RENDERER_AVAILABLE and self._is_temporary_message_active:  # Send blank if active but can't render
                self.request_send_bitmap_to_fire.emit(
                    oled_renderer.get_blank_packed_bitmap())
            return
        bitmap = oled_renderer.render_text_to_packed_buffer(
            text=self._current_temporary_message_text,
            font_override=self.feedback_pil_font,
            offset_x=self._temporary_message_current_scroll_offset,
            # Center only if not scrolling
            center_if_not_scrolling=not self._temporary_message_is_scrolling
        )
        if bitmap:
            self.request_send_bitmap_to_fire.emit(bitmap)
        else:  # Render failed, send blank
            # print(f"OLED Mgr WARNING: Failed to render temporary message: '{self._current_temporary_message_text}'") # Optional
            self.request_send_bitmap_to_fire.emit(
                oled_renderer.get_blank_packed_bitmap())

    def _scroll_temporary_message_step(self):
        if not self._is_temporary_message_active or \
            not self._temporary_message_is_scrolling or \
            self._current_temporary_message_text is None or \
            self._temporary_message_has_scrolled_once:  # If already scrolled once, text scroll timer should be stopped
            if self._temporary_message_text_scroll_timer.isActive():
                self._temporary_message_text_scroll_timer.stop()
            self._temporary_message_is_scrolling = False  # Ensure scrolling flag is false
            return
        self._temporary_message_current_scroll_offset += 2  # Scroll amount per step
        # Render the current frame of the scrolling temporary message
        self._render_and_send_temporary_message_frame()
        # Check if the text has fully scrolled off to the left
        if self._temporary_message_current_scroll_offset > self._temporary_message_text_pixel_width:
            # print(
            #     f"OLED Mgr DEBUG: Temporary message '{self._current_temporary_message_text[:20]}...' finished scrolling once.")
            self._temporary_message_text_scroll_timer.stop()
            self._temporary_message_is_scrolling = False
            self._temporary_message_has_scrolled_once = True
            # Option: Display a blank screen or the first part of the message statically after scroll.
            # For simplicity, let's just ensure the last rendered frame (which is now off-screen)
            # is followed by the revert timer. Or, send a blank now.
            if OLED_RENDERER_AVAILABLE:
                self.request_send_bitmap_to_fire.emit(
                    oled_renderer.get_blank_packed_bitmap())  # Clear after scroll
            # Now that scrolling is complete, start the main duration timer for the message to "linger" (or effectively, time out).
            # The message itself is visually gone after scrolling off. This timer determines when to revert state.
            # Start only if not already started (e.g. for a non-scrolling message)
            if not self._temporary_message_timer.isActive():
                self._temporary_message_timer.start(
                    self._temporary_message_total_duration_ms)
            # If the timer was already running (e.g. a very short static message that then got scrolled for some reason), let it be.
        else:
            # Continue scrolling with the same step delay
            if not self._temporary_message_text_scroll_timer.isActive():  # Should not happen if is_scrolling is true
                self._temporary_message_text_scroll_timer.start(
                    self.DEFAULT_TEXT_ITEM_SCROLL_STEP_DELAY_MS)
            # No need to setInterval here if it's already running with the correct interval

    def set_persistent_override(self, text: str | None, scroll_if_needed: bool = True):
        # `scroll_if_needed` for persistent override is tricky with current simple display.
        # Assuming persistent overrides are short and centered for now.
        # print(f"OLED Mgr INFO: set_persistent_override: '{text}'")
        self.stop_all_activity()  # Stop Active Graphic before setting override
        self.persistent_override_text = text
        # Apply immediately if no higher priority display is active
        if not self._is_builtin_startup_animation_playing and not self._is_temporary_message_active:
            self._apply_current_oled_state()

    def clear_persistent_override(self):
        # print("OLED Mgr INFO: clear_persistent_override called.")
        if self.persistent_override_text is not None:
            self.persistent_override_text = None
            # Re-apply current state, which will now be Active Graphic or app default
            if not self._is_builtin_startup_animation_playing and not self._is_temporary_message_active:
                self._apply_current_oled_state()

    def clear_display_content(self):
        """Sends a blank screen to the OLED."""
        blank_bitmap = bytearray(1176)
        self.request_send_bitmap_to_fire.emit(blank_bitmap)
        self.request_update_mirror_widget.emit(blank_bitmap)

    def pause_active_graphic(self):
        if self.is_active_graphic_paused:
            return
        self.is_active_graphic_paused = True
        if self.text_scroll_timer.isActive():
            self.text_scroll_timer.stop()
        if self.gif_anim_timer.isActive():
            self.gif_anim_timer.stop()
        self.active_graphic_pause_state_changed.emit(True)

    def resume_active_graphic(self):
        if not self.is_active_graphic_paused:
            return
        self.is_active_graphic_paused = False
        if self.current_text_is_scrolling:
            self.text_scroll_timer.start(
                max(20, self.current_text_item_scroll_delay_ms))
        elif self._active_graphic_item_type == "image_animation":
            self.gif_anim_timer.start(self.current_gif_frame_delay_ms)
        self.active_graphic_pause_state_changed.emit(False)

    def is_active_graphic_paused(self) -> bool:
        """Returns True if the Active Graphic is currently paused by a call to pause_active_graphic()."""
        return self._active_graphic_is_manually_paused

    def _play_active_graphic_animation(self):
        if self._active_graphic_is_manually_paused:  # <<< ADD CHECK
            # print("ODM DEBUG: _play_active_graphic_animation - Paused, not starting timer.")
            # Mark that it *would* be playing
            self._active_graphic_was_playing_before_pause = True
            return
        # print("ODM DEBUG: _play_active_graphic_animation CALLED")
        if not self._active_graphic_item_data or \
            self._active_graphic_item_type != "image_animation" or \
            not self._custom_animation_logical_frames:
            # print("ODM ERROR: Cannot play active graphic animation - invalid data or no logical frames.")
            self._is_custom_animation_playing = False
            self._apply_current_oled_state()
            return
        item_name = self._active_graphic_item_data.get(
            "item_name", "Unnamed Animation")
        # print(f"OLED Mgr INFO: Starting Active Graphic Animation '{item_name}' (or resuming if timer starts)")
        # This indicates it's the active *type*
        self._is_custom_animation_playing = True
        self._custom_animation_current_frame_index = 0
        timer_interval_ms = int(
            1000.0 / self._custom_animation_playback_fps) if self._custom_animation_playback_fps > 0 else 100
        min_interval = 33
        timer_interval_ms = max(min_interval, timer_interval_ms)
        self._custom_animation_timer.start(timer_interval_ms)
        self._play_next_custom_animation_frame()

    def stop_all_activity(self):
        """Stops all timers and resets volatile playback states."""
        if self._animation_timer.isActive():
            self._animation_timer.stop()
        if self._text_scroll_timer.isActive():
            self._text_scroll_timer.stop()
        if self._temporary_message_revert_timer.isActive():
            self._temporary_message_revert_timer.stop()
        if self._startup_anim_timer.isActive():
            self._startup_anim_timer.stop()
        self._animation_is_playing = False
        self._text_is_scrolling = False

    def _render_current_state_as_static_frame(self):
        """Renders a single, static frame of the current state when paused."""
        if not self._active_graphic_item_data:
            self.clear_display_content()
            return
        item_type = self._active_graphic_item_data.get("item_type")
        if item_type == "image_animation":
            frames = self._active_graphic_item_data.get("frames_logical")
            if frames:
                # Show the first frame of the animation
                self._render_logical_frame(frames[0])
            else:
                self.clear_display_content()
        elif item_type == "text":
            # Re-use the text display logic but ensure it doesn't start a scroll timer
            self._start_text_display(
                self._active_graphic_item_data, respect_pause=True)
        else:
            self.clear_display_content()

    def _start_text_display(self, item_data: dict, respect_pause: bool = False):
        """Consolidated method to handle displaying a text item."""
        self._text_content = item_data.get("text_content", "")
        font_family = item_data.get("font_family")
        font_size_px = item_data.get("font_size_px")
        self._text_pil_font = self._load_pil_font_for_text_item(
            font_family, font_size_px)
        if not self._text_pil_font:
            self._text_pil_font = self.feedback_pil_font or ImageFont.load_default()
        self._text_alignment = item_data.get("alignment", "center")
        animation_style = item_data.get("animation_style")
        self._text_pixel_width = self._get_text_pixel_width(
            self._text_content, self._text_pil_font)
        needs_scroll = (animation_style == "scroll_left") and (
            self._text_pixel_width > self.OLED_WIDTH)
        self._text_is_scrolling = needs_scroll
        if needs_scroll and not respect_pause:
            anim_params = item_data.get("animation_params", {})
            self._text_step_delay_ms = anim_params.get(
                "speed_override_ms") or self.DEFAULT_TEXT_ITEM_SCROLL_STEP_DELAY_MS
            self._text_restart_delay_ms = anim_params.get(
                "pause_at_ends_ms") or self.DEFAULT_TEXT_ITEM_SCROLL_RESTART_DELAY_MS
            self._text_current_scroll_offset = self.OLED_WIDTH
            self._text_scroll_timer.start(self._text_step_delay_ms)
            self._scroll_text_step()  # Render first frame immediately
        else:
            self._text_is_scrolling = False
            self._text_current_scroll_offset = 0
            self._render_text_frame(self._text_content, self._text_pil_font,
                                    self._text_alignment, self._text_current_scroll_offset)

    def _start_animation_display(self, item_data: dict):
        """Consolidated method to handle playing an animation item."""
        self._animation_logical_frames = item_data.get("frames_logical")
        if not self._animation_logical_frames:
            self._display_hardcoded_app_default_message()  # SAFE FALLBACK
            return
        import_options = item_data.get("import_options_used", {})
        playback_fps = import_options.get("playback_fps", 15)
        self._animation_frame_delay_ms = int(
            1000.0 / playback_fps) if playback_fps > 0 else 100
        self._animation_loop_behavior = import_options.get(
            "loop_behavior", "Loop Infinitely")
        self._animation_current_frame_index = 0
        self._animation_is_playing = True
        self._animation_timer.start(self._animation_frame_delay_ms)
        self._play_next_animation_frame()  # Render first frame immediately

    def _play_next_animation_frame(self):
        """Worker method for the animation timer."""
        if not self._animation_is_playing or not self._animation_logical_frames:
            self._animation_timer.stop()
            return
        num_frames = len(self._animation_logical_frames)
        if self._animation_current_frame_index >= num_frames:
            if self._animation_loop_behavior == "Loop Infinitely":
                self._animation_current_frame_index = 0
            else:  # Play Once
                self._animation_timer.stop()
                self._animation_is_playing = False
                return
        logical_frame = self._animation_logical_frames[self._animation_current_frame_index]
        self._render_logical_frame(logical_frame)
        self._animation_current_frame_index += 1

    def _scroll_text_step(self):
        """Worker method for the text scroll timer."""
        if not self._text_is_scrolling:
            self._text_scroll_timer.stop()
            return
        self._text_current_scroll_offset -= 2
        if (self._text_current_scroll_offset + self._text_pixel_width) < 0:
            self._text_current_scroll_offset = self.OLED_WIDTH
            self._text_scroll_timer.setInterval(self._text_restart_delay_ms)
        else:
            self._text_scroll_timer.setInterval(self._text_step_delay_ms)
        self._render_text_frame(self._text_content, self._text_pil_font,
                                self._text_alignment, self._text_current_scroll_offset)

    def _render_text_frame(self, text: str, font: QFont, alignment: str, offset_x: int):
        """
        Renders a text string to a 1-bit monochrome image using Qt's QPainter
        for superior system font handling, then packs it for the Akai Fire.
        """
        if not text or not font or not OLED_RENDERER_AVAILABLE:
            self.clear_display_content()
            return
        # 1. Render text to a QImage using QPainter
        q_image = QImage(self.OLED_WIDTH, self.OLED_HEIGHT, QImage.Format.Format_Mono)
        q_image.fill(0)  # 0 = Black background
        painter = QPainter(q_image)
        painter.setFont(font)
        painter.setPen(QColor(Qt.GlobalColor.white)) # 1 = White text
        fm = QFontMetrics(font)
        text_width = fm.horizontalAdvance(text)
        # Use bounding rect for more accurate vertical centering
        # Let Qt handle the vertical alignment calculations.
        # Create the full rectangle of the OLED screen.
        display_rect = q_image.rect()
        # For horizontal alignment, we still need to calculate the x position for scrolling.
        # For static text, Qt's alignment flags will handle it.
        x_pos = offset_x
        if not self._text_is_scrolling:
            # If not scrolling, create the rect where text should be drawn.
            # Qt will center it within this rect.
            painter.drawText(display_rect, int(Qt.AlignmentFlag.AlignVCenter), text)
        else:
            # If scrolling, we can't use Qt's alignment flags as they override the x_pos.
            # We must calculate y manually but can use a simpler formula.
            bounding_rect = fm.boundingRect(text)
            y_pos = (self.OLED_HEIGHT - bounding_rect.height()) // 2 + fm.ascent()
            painter.drawText(int(x_pos), int(y_pos), text)
        painter.end()
        # 2. Convert the QImage to a PIL Image
        buffer = QBuffer()
        buffer.open(QIODevice.OpenModeFlag.WriteOnly)
        q_image.save(buffer, "BMP")
        pil_image = Image.open(io.BytesIO(buffer.data()))
        pil_image = pil_image.convert('1') # Ensure it's 1-bit mode
        # 3. Pack the PIL Image and send to the hardware
        if pil_image:
            packed_bitmap = self._pack_pil_image_to_7bit_stream(pil_image)
            if packed_bitmap:
                self.request_send_bitmap_to_fire.emit(packed_bitmap)

    def _render_logical_frame(self, logical_frame: list[str]):
        """Renders a single logical frame (list of '1's and '0's) and sends it to the hardware."""
        if not OLED_RENDERER_AVAILABLE or not logical_frame:
            self.clear_display_content()
            return
        pil_image = self._logical_frame_to_pil_image(logical_frame)
        if pil_image:
            packed_bitmap = self._pack_pil_image_to_7bit_stream(pil_image)
            if packed_bitmap:
                self.request_send_bitmap_to_fire.emit(packed_bitmap)
            else:
                # This case is unlikely if logical_frame_to_pil_image succeeds, but for safety:
                self.clear_display_content()
        else:
            self.clear_display_content()

    def full_reset(self):
        """
        Resets the manager to a pristine state. This is the single source of
        truth for the object's initial state.
        """
        self.stop_all_activity()
        # --- High-Level State Flags ---
        self._active_graphic_item_data: dict | None = None
        self._is_temporary_message_active: bool = False
        self._is_external_override_active: bool = False
        self._is_startup_animation_playing: bool = False
        self._is_manually_paused: bool = False
        self.persistent_override_text: str | None = None
        # This attribute holds the global default scroll speed from the customizer.
        self.global_default_scroll_delay_ms: int = self.DEFAULT_TEXT_ITEM_SCROLL_STEP_DELAY_MS
        # --- Animation State ---
        self._animation_is_playing: bool = False
        self._animation_logical_frames: list[list[str]] | None = None
        self._animation_current_frame_index: int = 0
        self._animation_frame_delay_ms: int = 100
        self._animation_loop_behavior: str = "Loop Infinitely"
        # --- Text Display State ---
        self._text_is_scrolling: bool = False
        self._text_content: str | None = None
        self._text_pil_font: ImageFont.FreeTypeFont | ImageFont.ImageFont | None = None
        self._text_alignment: str = "center"
        self._text_current_scroll_offset: int = 0
        self._text_pixel_width: int = 0
        self._text_step_delay_ms: int = 50
        self._text_restart_delay_ms: int = 2000
        # --- Temporary Message State ---
        self._temp_message_text: str | None = None
        # --- Built-in Startup Animation State ---
        self._startup_anim_frames: list = []
        self._startup_anim_frame_index: int = 0
        # After a full reset, explicitly tell the UI that the state is not paused.
        self.active_graphic_pause_state_changed.emit(False)

    def _logical_frame_to_pil_image(self, logical_frame: list[str]) -> Image.Image | None:
        # (Keep this method as it was provided, it's correct)
        if not isinstance(logical_frame, list) or len(logical_frame) != self.OLED_HEIGHT:
            # print(f"OLED Mgr ERROR (_logical_frame_to_pil_image): Invalid logical frame format or height. Expected {self.OLED_HEIGHT} rows.")
            return None
        try:
            pil_image = Image.new('1', (self.OLED_WIDTH, self.OLED_HEIGHT), 0)
            pixels = pil_image.load()
            for y, row_str in enumerate(logical_frame):
                if not isinstance(row_str, str) or len(row_str) != self.OLED_WIDTH:
                    # print(f"OLED Mgr ERROR (_logical_frame_to_pil_image): Invalid row in logical frame at y={y}.")
                    continue
                for x, pixel_char in enumerate(row_str):
                    if pixel_char == '1':
                        pixels[x, y] = 1
            return pil_image
        except Exception as e:
            # print(f"OLED Mgr ERROR (_logical_frame_to_pil_image): Exception during conversion: {e}")
            return None

    def play_animation_item_temporarily(self, item_data: dict, duration_ms: int):
        """Plays an animation item for a fixed duration then reverts."""
        # print("OLED Mgr WARNING: play_animation_item_temporarily is complex with new model, consider text cues.")
        item_name = item_data.get("item_name", "Animation")
        self.show_system_message(f"Playing: {item_name}", duration_ms)

    def get_active_graphic_logical_frames(self) -> list[list[str]] | None:
        """
        Retrieves the logical frame data for the currently active graphic.
        Returns None if no active graphic or if it's not an animation type.
        """
        if self._active_graphic_item_data and self._active_graphic_item_data.get("item_type") == "image_animation":
            return self._active_graphic_item_data.get("frames_logical")
        return None

    def render_logical_frames_to_gif(self, logical_frames: list[list[str]], export_path: str, options: dict):
        """
        Renders a list of logical 1-bit frames to a GIF file.
        Args:
            logical_frames: A list of frames, where each frame is a list of 64 strings.
            export_path: The full path to save the GIF file.
            options: A dictionary from OLEDGifExportDialog with 'scale', 'invert', 'delay', 'loop'.
        """
        if not logical_frames:
            raise ValueError("No logical frames provided to render.")
        scale = options.get('scale', 1)
        invert = options.get('invert', False)
        delay_ms = options.get('delay', 100)
        loop = options.get('loop', 0)
        output_width = self.OLED_WIDTH * scale
        output_height = self.OLED_HEIGHT * scale
        # Define ON/OFF colors based on the 'invert' option
        on_color = (0, 0, 0) if invert else (255, 255, 255)
        off_color = (255, 255, 255) if invert else (0, 0, 0)
        pil_frames = []
        for frame_data in logical_frames:
            # Create a new blank image for this frame using the 'OFF' color
            frame_image = Image.new(
                'RGB', (output_width, output_height), color=off_color)
            draw = ImageDraw.Draw(frame_image)
            for y, row_str in enumerate(frame_data):
                for x, pixel_char in enumerate(row_str):
                    # Only draw the 'ON' pixels
                    if pixel_char == '1':
                        x0, y0 = x * scale, y * scale
                        x1, y1 = x0 + scale, y0 + scale
                        draw.rectangle([x0, y0, x1, y1], fill=on_color)
            pil_frames.append(frame_image)
        if not pil_frames:
            raise ValueError(
                "Frame rendering resulted in an empty image list.")
        # Save the collected Pillow frames as an animated GIF
        pil_frames[0].save(
            export_path,
            save_all=True,
            append_images=pil_frames[1:],
            duration=delay_ms,
            loop=loop,
            optimize=False  # Optimization can be slow; keep it simple for reliability
        )