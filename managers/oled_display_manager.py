# AKAI_Fire_RGB_Controller/managers/oled_display_manager.py
from PyQt6.QtCore import QObject, pyqtSignal, QTimer, Qt, QBuffer, QIODevice
# Keep QFont for fallback text items
from PyQt6.QtGui import QImage, QPainter, QColor, QFont, QFontMetrics
from PIL import Image, ImageFont  # Crucial for PIL font objects
import os
import sys
import io

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
    # startup_animation_finished signal is now primarily for internal transition,
    # MainWindow might not need to connect if ODM handles the next step.
    # We can keep it if other parts of MW rely on knowing when built-in visual is done.
    builtin_startup_animation_finished = pyqtSignal()

    # Default scroll delays for user-defined TEXT Active Graphics
    DEFAULT_TEXT_ITEM_SCROLL_STEP_DELAY_MS = 50
    DEFAULT_TEXT_ITEM_SCROLL_RESTART_DELAY_MS = 2000

    # Constants for system feedback messages
    FEEDBACK_FONT_FILENAME = "TomThumb.ttf"
    FEEDBACK_FONT_SIZE_PX = 60
    PERSISTENT_OVERRIDE_FONT_FAMILY = "Arial"  # Or another small, clear system font
    PERSISTENT_OVERRIDE_FONT_SIZE_PX = 10

    def __init__(self, akai_fire_controller_ref, parent: QObject | None = None):
        super().__init__(parent)

        self.akai_fire_controller = akai_fire_controller_ref

        # --- Core State Attributes ---
        self._active_graphic_item_data: dict | None = None
        self._active_graphic_item_type: str | None = None  # "text" or "image_animation"

        # For text-based Active Graphics specifically
        self._active_graphic_pil_font: ImageFont.FreeTypeFont | ImageFont.ImageFont | None = None
        self._active_graphic_text_content: str | None = None
        self._active_graphic_text_scroll_if_needed: bool = True
        self._active_graphic_text_is_scrolling: bool = False
        self._active_graphic_text_current_scroll_offset: int = 0
        self._active_graphic_text_pixel_width: int = 0
        self._active_graphic_text_scroll_timer = QTimer(self)
        self._active_graphic_text_scroll_timer.timeout.connect(
            self._scroll_active_graphic_text_step)
        self._active_graphic_text_step_delay_ms: int = self.DEFAULT_TEXT_ITEM_SCROLL_STEP_DELAY_MS
        self._active_graphic_text_restart_delay_ms: int = self.DEFAULT_TEXT_ITEM_SCROLL_RESTART_DELAY_MS
        self._active_graphic_text_alignment: str = "center"  # "left", "center", "right"

        # For image_animation-based Active Graphics
        self._custom_animation_logical_frames: list[list[str]] | None = None
        self._custom_animation_current_frame_index: int = 0
        self._custom_animation_playback_fps: float = 15.0
        self._custom_animation_loop_behavior: str = "Loop Infinitely"
        self._custom_animation_timer = QTimer(self)
        self._custom_animation_timer.timeout.connect(
            self._play_next_custom_animation_frame)
        self._is_custom_animation_playing: bool = False

        # For built-in visual startup animation
        self._is_builtin_startup_animation_playing = False
        self._builtin_startup_animation_frames: list[bytearray] = []
        self._current_builtin_startup_animation_frame_index: int = 0
        self._builtin_startup_animation_frame_duration: int = 60

        # For temporary system messages
        self.feedback_pil_font: ImageFont.FreeTypeFont | ImageFont.ImageFont | None = None
        self._temporary_message_timer = QTimer(self)
        self._temporary_message_timer.setSingleShot(True)
        self._temporary_message_timer.timeout.connect(
            self._revert_from_temporary_display)
        self._is_temporary_message_active = False
        self._temporary_message_text_scroll_timer = QTimer(
            self)  # For scrolling long temp messages
        self._temporary_message_text_scroll_timer.timeout.connect(
            self._scroll_temporary_message_step)
        self._temporary_message_is_scrolling: bool = False
        self._temporary_message_current_scroll_offset: int = 0
        self._temporary_message_text_pixel_width: int = 0

        # For persistent overrides (e.g., "SAMPLING")
        self.persistent_override_text: str | None = None
        self.persistent_override_pil_font: ImageFont.FreeTypeFont | ImageFont.ImageFont | None = None
        # --- End Core State Attributes ---

        self.oled_width = oled_renderer.OLED_WIDTH if OLED_RENDERER_AVAILABLE else 128
        self.oled_height = oled_renderer.OLED_HEIGHT if OLED_RENDERER_AVAILABLE else 64

        # Load fonts
        self._load_feedback_font()
        self._load_persistent_override_font()

        # Global scroll delay for text items (can be overridden by item's settings)
        self.global_text_item_scroll_delay_ms: int = self.DEFAULT_TEXT_ITEM_SCROLL_STEP_DELAY_MS

        print(
            f"OLEDDisplayManager: Initialized. Feedback Font Loaded: {self.feedback_pil_font is not None}")

    def _load_feedback_font(self):
        """Loads TomThumb.ttf 60pt for system feedback messages."""
        self.feedback_pil_font = None
        if UTILS_AVAILABLE and OLED_RENDERER_AVAILABLE:
            try:
                font_path = resource_path_func(os.path.join(
                    "resources", "fonts", self.FEEDBACK_FONT_FILENAME))
                if os.path.exists(font_path):
                    self.feedback_pil_font = ImageFont.truetype(
                        font_path, self.FEEDBACK_FONT_SIZE_PX)
                    print(
                        f"OLED Mgr INFO: Loaded Feedback Font '{self.FEEDBACK_FONT_FILENAME}' @ {self.FEEDBACK_FONT_SIZE_PX}px.")
                else:
                    print(
                        f"OLED Mgr WARNING: Feedback Font '{self.FEEDBACK_FONT_FILENAME}' not found at '{font_path}'.")
            except Exception as e:
                print(
                    f"OLED Mgr WARNING: Failed to load Feedback Font '{self.FEEDBACK_FONT_FILENAME}': {e}")

        if not self.feedback_pil_font:
            print("OLED Mgr WARNING: Feedback font (TomThumb 60pt) failed to load. Using Pillow default for feedback.")
            try:
                self.feedback_pil_font = ImageFont.load_default()  # Basic fallback
            except:
                pass  # If even this fails, it remains None

    def _load_persistent_override_font(self):
        """Loads a standard small font for persistent override messages (e.g. SAMPLING)."""
        self.persistent_override_pil_font = None
        try:
            # Try to load a common system font directly with Pillow
            self.persistent_override_pil_font = ImageFont.truetype(
                self.PERSISTENT_OVERRIDE_FONT_FAMILY,
                self.PERSISTENT_OVERRIDE_FONT_SIZE_PX
            )
            print(
                f"OLED Mgr INFO: Loaded Persistent Override Font '{self.PERSISTENT_OVERRIDE_FONT_FAMILY}' @ {self.PERSISTENT_OVERRIDE_FONT_SIZE_PX}px.")
        except IOError:  # Pillow couldn't find/load it
            print(
                f"OLED Mgr WARNING: System font '{self.PERSISTENT_OVERRIDE_FONT_FAMILY}' for persistent override not found by Pillow. Using Pillow default.")
            try:
                self.persistent_override_pil_font = ImageFont.load_default()
            except:
                pass
        except Exception as e:
            print(
                f"OLED Mgr WARNING: Error loading persistent override font: {e}. Using Pillow default.")
            try:
                self.persistent_override_pil_font = ImageFont.load_default()
            except:
                pass

        if not self.persistent_override_pil_font:
            print("OLED Mgr CRITICAL: No font loaded for persistent override messages.")

    def _load_pil_font_for_text_item(self, font_family: str, font_size_px: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont | None:
        """
        Attempts to load a PIL ImageFont object for a given text item's font settings.
        Prioritizes resource fonts if font_family matches a known filename pattern.
        """
        loaded_font = None
        is_potential_resource = isinstance(
            font_family, str) and font_family.lower().endswith((".ttf", ".otf"))

        if is_potential_resource and UTILS_AVAILABLE:
            try:
                font_path = resource_path_func(
                    os.path.join("resources", "fonts", font_family))
                if os.path.exists(font_path):
                    loaded_font = ImageFont.truetype(font_path, font_size_px)
                    # print(f"OLED Mgr DEBUG: Loaded RESOURCE font '{font_family}' for text item.")
            except Exception as e_res:
                print(
                    f"OLED Mgr WARNING: Failed to load resource font '{font_family}' for text item: {e_res}")

        if not loaded_font:  # Try as system font if not resource or resource failed
            try:
                loaded_font = ImageFont.truetype(font_family, font_size_px)
                # print(f"OLED Mgr DEBUG: Loaded SYSTEM font '{font_family}' for text item.")
            except IOError:  # Pillow couldn't find/load system font by that name
                print(
                    f"OLED Mgr WARNING: System font '{font_family}' for text item not found by Pillow.")
            except Exception as e_sys:
                print(
                    f"OLED Mgr WARNING: Error loading system font '{font_family}' for text item: {e_sys}")

        if not loaded_font:  # Ultimate fallback
            print(
                f"OLED Mgr WARNING: Using Pillow load_default() for text item font '{font_family}'.")
            try:
                loaded_font = ImageFont.load_default()
            except:
                pass

        return loaded_font

    def update_global_text_item_scroll_delay(self, new_delay_ms: int):
        """Called by MainWindow to set the global default scroll speed for text items."""
        self.global_text_item_scroll_delay_ms = max(
            20, new_delay_ms)  # Ensure a minimum
        # If an active graphic text item is currently scrolling AND not using an override, update its timer
        if self._active_graphic_text_is_scrolling and \
           self._active_graphic_item_data and \
           self._active_graphic_item_data.get("item_type") == "text":

            item_anim_params = self._active_graphic_item_data.get(
                "animation_params", {})
            if item_anim_params.get("speed_override_ms") is None:  # Not using override
                self._active_graphic_text_step_delay_ms = self.global_text_item_scroll_delay_ms
                if self._active_graphic_text_scroll_timer.isActive() and \
                   self._active_graphic_text_scroll_timer.interval() != self._active_graphic_text_restart_delay_ms:
                    self._active_graphic_text_scroll_timer.setInterval(
                        self._active_graphic_text_step_delay_ms)

    def stop_all_activity(self):
        """Stops all current OLED activities (scrolling, animations)."""
        # print("OLED Mgr TRACE: stop_all_activity called.")

        # Built-in startup animation
        self._is_builtin_startup_animation_playing = False
        # QTimer.singleShot in _play_next_builtin_startup_frame will naturally stop

        # Active Graphic: Text Scrolling
        self._active_graphic_text_scroll_timer.stop()
        self._active_graphic_text_is_scrolling = False

        # Active Graphic: Custom Animation
        self._custom_animation_timer.stop()
        self._is_custom_animation_playing = False
        # self._custom_animation_logical_frames = None # Don't clear here, set_active_graphic handles it

        # Temporary Message
        # Stop the timer that reverts from temp message
        self._temporary_message_timer.stop()
        self._temporary_message_text_scroll_timer.stop()  # Stop scrolling of temp message
        self._is_temporary_message_active = False
        self._temporary_message_is_scrolling = False

        # Does NOT clear persistent_override_text or _active_graphic_item_data

    def play_builtin_startup_animation(self, frames_data: list[bytearray], frame_duration_ms: int):
        if not frames_data:
            self.builtin_startup_animation_finished.emit()
            self._apply_current_oled_state()  # Directly apply active graphic or default
            return

        print("OLED Mgr INFO: play_builtin_startup_animation called.")
        self.stop_all_activity()

        self._is_builtin_startup_animation_playing = True
        self._builtin_startup_animation_frames = frames_data
        self._current_builtin_startup_animation_frame_index = 0
        self._builtin_startup_animation_frame_duration = frame_duration_ms

        if OLED_RENDERER_AVAILABLE:
            blank_bitmap = oled_renderer.get_blank_packed_bitmap()
            if blank_bitmap:
                self.request_send_bitmap_to_fire.emit(blank_bitmap)

        QTimer.singleShot(50, self._play_next_builtin_startup_frame)

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
        Sets the user's chosen Active Graphic.
        item_data: Full JSON data of the item, or None to clear.
        """
        print(
            f"OLED Mgr INFO: set_active_graphic called with item_data: {'Set' if item_data else 'None'}")
        self.stop_all_activity()  # Stop whatever was playing before applying new active graphic

        self._active_graphic_item_data = item_data
        if item_data:
            self._active_graphic_item_type = item_data.get("item_type")
            item_name = item_data.get("item_name", "Unnamed Item")
            print(
                f"OLED Mgr INFO: Active Graphic set to '{item_name}' (Type: {self._active_graphic_item_type})")

            if self._active_graphic_item_type == "text":
                self._active_graphic_text_content = item_data.get(
                    "text_content", " ")
                font_family = item_data.get("font_family", "Arial")
                font_size_px = item_data.get("font_size_px", 10)
                self._active_graphic_pil_font = self._load_pil_font_for_text_item(
                    font_family, font_size_px)

                self._active_graphic_text_alignment = item_data.get(
                    "alignment", "center")
                anim_style = item_data.get("animation_style", "static")
                self._active_graphic_text_scroll_if_needed = (
                    anim_style != "static")

                anim_params = item_data.get("animation_params", {})
                self._active_graphic_text_step_delay_ms = anim_params.get(
                    "speed_override_ms", self.global_text_item_scroll_delay_ms)
                self._active_graphic_text_restart_delay_ms = anim_params.get(
                    "pause_at_ends_ms", self.DEFAULT_TEXT_ITEM_SCROLL_RESTART_DELAY_MS)

            elif self._active_graphic_item_type == "image_animation":
                self._custom_animation_logical_frames = item_data.get(
                    "frames_logical")
                import_options = item_data.get("import_options_used", {})
                self._custom_animation_playback_fps = float(
                    import_options.get("playback_fps", 15.0))
                self._custom_animation_loop_behavior = import_options.get(
                    "loop_behavior", "Loop Infinitely")
        else:
            self._active_graphic_item_type = None
            self._active_graphic_text_content = None
            self._active_graphic_pil_font = None
            self._custom_animation_logical_frames = None
            print("OLED Mgr INFO: Active Graphic cleared.")

        # Apply the new state if no higher priority display is active
        if not self._is_builtin_startup_animation_playing and \
           not self._is_temporary_message_active:  # Don't interrupt ongoing built-in startup or temp message
            self._apply_current_oled_state()

    def _apply_current_oled_state(self, called_by_revert: bool = False):
        """
        Central dispatcher to determine and apply the correct OLED content.
        Priority: Built-in Startup -> Persistent Override -> Temporary Message (handled externally by its timer) -> Active Graphic -> App Default.
        """
        # print(f"OLED Mgr TRACE: _apply_current_oled_state called. Revert: {called_by_revert}, StartupPlaying: {self._is_builtin_startup_animation_playing}, TempMsgActive: {self._is_temporary_message_active}, Persistent: {self.persistent_override_text is not None}")

        if self._is_builtin_startup_animation_playing:
            # print("OLED Mgr TRACE: Built-in startup animation is active, deferring _apply_current_oled_state.")
            # Built-in startup takes precedence, will call this when done.
            return

        if self._is_temporary_message_active and not called_by_revert:
            # print("OLED Mgr TRACE: Temporary message is active (and not being reverted from), deferring _apply_current_oled_state.")
            return  # Let temporary message finish or be explicitly stopped.

        # Stop any other activity before applying new state (unless it's the activity we're about to start)
        # This is nuanced. If called_by_revert, we might have just finished a temp message.
        # If applying persistent override, we want to stop current Active Graphic.
        # If applying Active Graphic, we want to stop previous Active Graphic or app default.

        # Tentative: Always stop current specific display before changing to another type.
        # play_animation_item and _start_or_display_active_graphic_text_internal should handle their own setup.

        if self.persistent_override_text is not None:
            print(
                f"OLED Mgr INFO: Applying persistent override: '{self.persistent_override_text}'")
            self.stop_all_activity()  # Ensure active graphic is stopped
            self._display_persistent_override_text()
        elif self._active_graphic_item_data:
            if self._active_graphic_item_type == "image_animation":
                print(
                    f"OLED Mgr INFO: Applying Active Graphic (Animation): '{self._active_graphic_item_data.get('item_name')}'")
                self.stop_all_activity()  # Stop other active graphic types
                self._play_active_graphic_animation()
            elif self._active_graphic_item_type == "text":
                print(
                    f"OLED Mgr INFO: Applying Active Graphic (Text): '{self._active_graphic_item_data.get('item_name')}'")
                self.stop_all_activity()  # Stop other active graphic types
                self._start_or_display_active_graphic_text_internal()
            else:
                print(
                    f"OLED Mgr WARNING: Unknown Active Graphic type: {self._active_graphic_item_type}. Applying app default.")
                self.stop_all_activity()
                self._display_hardcoded_app_default_message()
        else:
            print(
                "OLED Mgr INFO: No Active Graphic or Persistent Override. Applying app default message.")
            self.stop_all_activity()
            self._display_hardcoded_app_default_message()

    def _display_persistent_override_text(self):
        if self.persistent_override_text is None or not OLED_RENDERER_AVAILABLE:
            if OLED_RENDERER_AVAILABLE:
                self.request_send_bitmap_to_fire.emit(
                    oled_renderer.get_blank_packed_bitmap())
            return

        # For persistent override, we assume it's short and doesn't need complex scrolling logic here.
        # If it could be long, a similar scrolling mechanism to active graphic text would be needed.
        # Using the dedicated persistent_override_pil_font.
        font_to_use = self.persistent_override_pil_font if self.persistent_override_pil_font else self.feedback_pil_font  # Fallback

        bitmap = oled_renderer.render_text_to_packed_buffer(
            text=self.persistent_override_text,
            font_override=font_to_use,
            offset_x=0,
            center_if_not_scrolling=True  # Center short overrides
        )
        if bitmap:
            self.request_send_bitmap_to_fire.emit(bitmap)
        else:  # Send blank if render failed
            self.request_send_bitmap_to_fire.emit(
                oled_renderer.get_blank_packed_bitmap())

    def _play_active_graphic_animation(self):
        if not self._active_graphic_item_data or \
           self._active_graphic_item_type != "image_animation" or \
           not self._custom_animation_logical_frames:
            print("OLED Mgr ERROR: Cannot play active graphic animation - invalid data.")
            self._is_custom_animation_playing = False
            self._apply_current_oled_state()  # Fallback to app default if this fails
            return

        item_name = self._active_graphic_item_data.get(
            "item_name", "Unnamed Animation")
        print(
            f"OLED Mgr INFO: Starting Active Graphic Animation '{item_name}'")

        self._is_custom_animation_playing = True
        self._custom_animation_current_frame_index = 0  # Always start from beginning

        timer_interval_ms = int(
            1000.0 / self._custom_animation_playback_fps) if self._custom_animation_playback_fps > 0 else 100
        min_interval = 33
        timer_interval_ms = max(min_interval, timer_interval_ms)

        self._custom_animation_timer.start(timer_interval_ms)
        self._play_next_custom_animation_frame()  # Display first frame

    # For Active Graphic Animations
    def _play_next_custom_animation_frame(self):
        if not self._is_custom_animation_playing or \
           not self._custom_animation_logical_frames or \
           self._custom_animation_current_frame_index >= len(self._custom_animation_logical_frames):

            if self._is_custom_animation_playing and self._custom_animation_logical_frames and \
               self._custom_animation_current_frame_index >= len(self._custom_animation_logical_frames):

                if self._custom_animation_loop_behavior == "Loop Infinitely":
                    self._custom_animation_current_frame_index = 0
                else:  # Play Once
                    print(
                        f"OLED Mgr INFO: Active Graphic Animation finished (played once).")
                    self._custom_animation_timer.stop()
                    self._is_custom_animation_playing = False
                    # After "Play Once" finishes, it should ideally revert to a default state
                    # or perhaps the *next* configured item if a playlist concept existed.
                    # For now, let's make it revert to the application's hardcoded default.
                    # Or, better, if no other active graphic is set, it could just stay on last frame.
                    # For simplicity now, let it "finish" and _apply_current_oled_state will decide next.
                    # Effectively, if this was the active graphic, it just stops.
                    # MainWindow might then set a new active graphic or it shows app default.
                    # The key is it *stops* being the active animation.
                    self._active_graphic_item_data = None  # Mark it as "done" if play once
                    self._active_graphic_item_type = None
                    # This will now go to app default if no new active graphic
                    self._apply_current_oled_state()
                    return
            else:
                self._custom_animation_timer.stop()
                self._is_custom_animation_playing = False
                return

        # Safety after loop check
        if self._custom_animation_current_frame_index >= len(self._custom_animation_logical_frames):
            self._custom_animation_timer.stop()
            self._is_custom_animation_playing = False
            print(
                "OLED Mgr WARNING: Animation frame index out of bounds after loop logic. Stopping.")
            self._apply_current_oled_state()  # Fallback
            return

        logical_frame = self._custom_animation_logical_frames[
            self._custom_animation_current_frame_index]
        pil_image = self._logical_frame_to_pil_image(logical_frame)

        if pil_image and OLED_RENDERER_AVAILABLE:
            packed_data = oled_renderer.pack_pil_image_to_7bit_stream(
                pil_image)
            if packed_data:
                self.request_send_bitmap_to_fire.emit(packed_data)

        self._custom_animation_current_frame_index += 1

    def _start_or_display_active_graphic_text_internal(self):
        if not self._active_graphic_item_data or \
           self._active_graphic_item_type != "text" or \
           self._active_graphic_text_content is None or \
           self._active_graphic_pil_font is None or \
           not OLED_RENDERER_AVAILABLE:
            print(
                "OLED Mgr ERROR: Cannot display active graphic text - invalid data or font.")
            self._apply_current_oled_state()  # Fallback
            return

        text_to_display = self._active_graphic_text_content
        font_to_use = self._active_graphic_pil_font

        self._active_graphic_text_pixel_width = oled_renderer.get_text_actual_width(
            text_to_display, font_to_use)

        needs_scroll = self._active_graphic_text_scroll_if_needed and \
            self._active_graphic_text_pixel_width > self.oled_width and \
            text_to_display.strip() != ""

        if needs_scroll:
            self._active_graphic_text_is_scrolling = True
            self._active_graphic_text_current_scroll_offset = - \
                self.oled_width  # Start off-screen right for left scroll
            # Display first (off-screen) frame
            self._render_and_send_active_graphic_text_frame()
            self._active_graphic_text_scroll_timer.start(
                self._active_graphic_text_step_delay_ms)
        else:
            self._active_graphic_text_is_scrolling = False
            self._active_graphic_text_current_scroll_offset = 0  # For centering
            self._render_and_send_active_graphic_text_frame()  # Display static text

    def _render_and_send_active_graphic_text_frame(self):
        if not self._active_graphic_text_content or \
           not self._active_graphic_pil_font or \
           not OLED_RENDERER_AVAILABLE:
            return

        text_to_render = self._active_graphic_text_content
        font_override = self._active_graphic_pil_font
        offset_x = self._active_graphic_text_current_scroll_offset

        center_statically = False
        if not self._active_graphic_text_is_scrolling:
            if self._active_graphic_text_alignment == "center":
                center_statically = True
            # Note: oled_renderer.render_text_to_packed_buffer handles left/right alignment for static text based on offset_x=0 if not centered.
            # If explicitly right-aligned static text is needed, renderer might need adjustment or pre-calc offset_x.
            # For now, if not scrolling and not center, it's effectively left-aligned.
            # If alignment is "right", we'd need: offset_x = self.oled_width - self._active_graphic_text_pixel_width
            if self._active_graphic_text_alignment == "right":
                # Negative offset means text starts further right
                offset_x = -(self.oled_width -
                             self._active_graphic_text_pixel_width)

        bitmap = oled_renderer.render_text_to_packed_buffer(
            text=text_to_render,
            font_override=font_override,
            # Positive for scrolling left (text's start moves more left)
            offset_x=offset_x,
            center_if_not_scrolling=center_statically
        )
        if bitmap:
            self.request_send_bitmap_to_fire.emit(bitmap)

    def _scroll_active_graphic_text_step(self):
        if not self._active_graphic_text_is_scrolling or \
           not self._active_graphic_text_content or \
           not self._active_graphic_pil_font:
            self._active_graphic_text_scroll_timer.stop()
            self._active_graphic_text_is_scrolling = False
            return

        self._active_graphic_text_current_scroll_offset += 2  # Scroll left

        if self._active_graphic_text_current_scroll_offset > self._active_graphic_text_pixel_width:
            self._active_graphic_text_current_scroll_offset = - \
                self.oled_width  # Reset to off-screen right
            self._active_graphic_text_scroll_timer.setInterval(
                self._active_graphic_text_restart_delay_ms)
        else:
            self._active_graphic_text_scroll_timer.setInterval(
                self._active_graphic_text_step_delay_ms)

        self._render_and_send_active_graphic_text_frame()

    def _display_hardcoded_app_default_message(self):
        # This message uses the feedback_pil_font (TomThumb 60pt) or a specific app default font
        default_text = "Fire CTRL"  # Or your DEFAULT_OLED_WELCOME_MESSAGE from MainWindow
        font_to_use = self.feedback_pil_font  # Or load a dedicated small font for this

        if not font_to_use or not OLED_RENDERER_AVAILABLE:
            if OLED_RENDERER_AVAILABLE:
                self.request_send_bitmap_to_fire.emit(
                    oled_renderer.get_blank_packed_bitmap())
            return

        # This specific default message likely doesn't need to scroll.
        bitmap = oled_renderer.render_text_to_packed_buffer(
            text=default_text,
            font_override=font_to_use,
            offset_x=0,
            center_if_not_scrolling=True
        )
        if bitmap:
            self.request_send_bitmap_to_fire.emit(bitmap)
        else:
            self.request_send_bitmap_to_fire.emit(
                oled_renderer.get_blank_packed_bitmap())

    def show_system_message(self, text: str, duration_ms: int, scroll_if_needed: bool = True):
        print(
            f"OLED Mgr INFO: show_system_message: '{text}', Duration: {duration_ms}ms")
        if self._is_builtin_startup_animation_playing:
            return  # Don't interrupt built-in startup

        self.stop_all_activity()  # Stop current Active Graphic or other temp messages
        self._is_temporary_message_active = True

        if not self.feedback_pil_font or not OLED_RENDERER_AVAILABLE:
            print(
                "OLED Mgr WARNING: Feedback font or renderer not available for system message.")
            # Set timer to revert anyway
            self._temporary_message_timer.start(duration_ms)
            if OLED_RENDERER_AVAILABLE:
                self.request_send_bitmap_to_fire.emit(
                    oled_renderer.get_blank_packed_bitmap())
            return

        self._temporary_message_text_pixel_width = oled_renderer.get_text_actual_width(
            text, self.feedback_pil_font)

        self._temporary_message_is_scrolling = scroll_if_needed and \
            self._temporary_message_text_pixel_width > self.oled_width and \
            text.strip() != ""

        if self._temporary_message_is_scrolling:
            self._temporary_message_current_scroll_offset = - \
                self.oled_width  # Start off-screen right
            self._render_and_send_temporary_message_frame(
                text)  # Display first frame
            # Use a fixed, reasonable scroll speed for temp messages
            self._temporary_message_text_scroll_timer.start(
                self.DEFAULT_TEXT_ITEM_SCROLL_STEP_DELAY_MS)
        else:
            self._temporary_message_current_scroll_offset = 0
            self._render_and_send_temporary_message_frame(
                text)  # Display static centered text

        self._temporary_message_timer.start(duration_ms)

    def _render_and_send_temporary_message_frame(self, text: str):
        if not self._is_temporary_message_active or \
           not self.feedback_pil_font or \
           not OLED_RENDERER_AVAILABLE:
            return

        bitmap = oled_renderer.render_text_to_packed_buffer(
            text=text,
            font_override=self.feedback_pil_font,
            offset_x=self._temporary_message_current_scroll_offset,
            center_if_not_scrolling=not self._temporary_message_is_scrolling
        )
        if bitmap:
            self.request_send_bitmap_to_fire.emit(bitmap)
        else:
            self.request_send_bitmap_to_fire.emit(
                oled_renderer.get_blank_packed_bitmap())

    def _scroll_temporary_message_step(self):
        if not self._is_temporary_message_active or \
           not self._temporary_message_is_scrolling or \
           not self.feedback_pil_font:  # Check font just in case
            self._temporary_message_text_scroll_timer.stop()
            self._temporary_message_is_scrolling = False
            return

        # Get the text that's supposed to be showing for the temp message.
        # This is a bit tricky as show_system_message doesn't store the text globally.
        # For now, we assume the _temporary_message_timer will fire and revert.
        # If a temp message needs to scroll *beyond* its duration, this logic is flawed.
        # Let's assume temporary messages are short enough or their duration allows full scroll.
        # A cleaner way would be for show_system_message to store self._current_temporary_message_text.
        # For now, this scroll step might not have the text to re-render if it's complex.
        # This indicates a design improvement: show_system_message should store its text while active.

        # Simplified: Assume the _temporary_message_timer will handle cleanup.
        # This scroll step is more about advancing visual offset if the message is still "valid".
        # This part needs to be more robust if long scrolling temp messages are common.

        self._temporary_message_current_scroll_offset += 2  # Scroll left

        # We need the text to re-render. This is a missing piece if we don't store it.
        # Placeholder: Re-rendering logic for scrolling temp message needs the text.
        # Let's assume for now that the initial render was enough, or the message is short.
        # If `_temporary_message_timer` fires, it calls `_revert_from_temporary_display`
        # which stops all activity including this scroll timer.

        # To make it scroll, we *must* re-render with the new offset.
        # This requires knowing the text. Let's assume for now it's not implemented for long scrolling temp messages.
        # If text were stored in `self._current_temporary_message_text`:
        # self._render_and_send_temporary_message_frame(self._current_temporary_message_text)

        # Loop condition (if we had the text and width)
        # if self._temporary_message_current_scroll_offset > self._temporary_message_text_pixel_width:
        #     self._temporary_message_current_scroll_offset = -self.oled_width
        #     self._temporary_message_text_scroll_timer.setInterval(self.DEFAULT_TEXT_ITEM_SCROLL_RESTART_DELAY_MS)
        # else:
        #     self._temporary_message_text_scroll_timer.setInterval(self.DEFAULT_TEXT_ITEM_SCROLL_STEP_DELAY_MS)

    def _revert_from_temporary_display(self):
        print("OLED Mgr INFO: Reverting from temporary display.")
        self._temporary_message_text_scroll_timer.stop()  # Stop scrolling of temp message
        self._is_temporary_message_active = False
        self._temporary_message_is_scrolling = False
        self._apply_current_oled_state(called_by_revert=True)

    def set_persistent_override(self, text: str | None, scroll_if_needed: bool = True):
        # `scroll_if_needed` for persistent override is tricky with current simple display.
        # Assuming persistent overrides are short and centered for now.
        print(f"OLED Mgr INFO: set_persistent_override: '{text}'")
        self.stop_all_activity()  # Stop Active Graphic before setting override

        self.persistent_override_text = text

        # Apply immediately if no higher priority display is active
        if not self._is_builtin_startup_animation_playing and not self._is_temporary_message_active:
            self._apply_current_oled_state()

    def clear_persistent_override(self):
        print("OLED Mgr INFO: clear_persistent_override called.")
        if self.persistent_override_text is not None:
            self.persistent_override_text = None
            # Re-apply current state, which will now be Active Graphic or app default
            if not self._is_builtin_startup_animation_playing and not self._is_temporary_message_active:
                self._apply_current_oled_state()

    def clear_display_content(self):  # Called on disconnect by MainWindow
        self.stop_all_activity()
        self.persistent_override_text = None
        # Do not clear _active_graphic_item_data here, MainWindow will decide if it needs to be reset.
        # Just send a blank screen.
        if OLED_RENDERER_AVAILABLE:
            blank_bitmap = oled_renderer.get_blank_packed_bitmap()
            if blank_bitmap:
                self.request_send_bitmap_to_fire.emit(blank_bitmap)

    def _logical_frame_to_pil_image(self, logical_frame: list[str]) -> Image.Image | None:
        # (Keep this method as it was provided, it's correct)
        if not isinstance(logical_frame, list) or len(logical_frame) != self.oled_height:
            # print(f"OLED Mgr ERROR (_logical_frame_to_pil_image): Invalid logical frame format or height. Expected {self.oled_height} rows.")
            return None
        try:
            pil_image = Image.new('1', (self.oled_width, self.oled_height), 0)
            pixels = pil_image.load()
            for y, row_str in enumerate(logical_frame):
                if not isinstance(row_str, str) or len(row_str) != self.oled_width:
                    # print(f"OLED Mgr ERROR (_logical_frame_to_pil_image): Invalid row in logical frame at y={y}.")
                    continue
                for x, pixel_char in enumerate(row_str):
                    if pixel_char == '1':
                        pixels[x, y] = 1
            return pil_image
        except Exception as e:
            # print(f"OLED Mgr ERROR (_logical_frame_to_pil_image): Exception during conversion: {e}")
            return None

    # --- Methods kept for direct use by MainWindow if it bypasses the new state model (should be rare) ---
    # These are largely superseded by the new state machine but kept for specific direct calls if absolutely needed.
    def play_animation_item_temporarily(self, item_data: dict, duration_ms: int):
        """Plays an animation item for a fixed duration then reverts."""
        # This is a convenience. Internally, it should behave like show_system_message
        # but with animation content. This is complex to integrate cleanly with the
        # "Active Graphic" model if the temporary item is *also* an animation.
        # For now, let's assume temporary items are text-based system messages.
        # If MainWindow needs to play a one-shot animation that isn't the "Active Graphic",
        # this would require more thought on how it interacts with the active graphic's state.
        print("OLED Mgr WARNING: play_animation_item_temporarily is complex with new model, consider text cues.")
        # Fallback: show item name as a system message
        item_name = item_data.get("item_name", "Animation")
        self.show_system_message(f"Playing: {item_name}", duration_ms)

    # old set_display_text, update_default_text_settings, etc. are effectively replaced
    # by set_active_graphic and show_system_message.
    # If MainWindow was calling update_default_text_settings, it should now call
    # set_active_graphic with the text item's data.
