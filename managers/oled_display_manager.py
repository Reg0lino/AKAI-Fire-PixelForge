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

# In class OLEDDisplayManager(QObject):
    # In managers/oled_display_manager.py

    def __init__(self, 
                 akai_fire_controller_ref, 
                 available_app_fonts: list[str], # <<< ARGUMENT ADDED HERE
                 parent: QObject | None = None):
        super().__init__(parent)
        
        self.akai_fire_controller = akai_fire_controller_ref
        self._app_font_files: list[str] = available_app_fonts # <<< STORED HERE

        # --- Core State Attributes ---
        self._active_graphic_item_data: dict | None = None
        self._active_graphic_item_type: str | None = None # "text" or "image_animation"
        
        # For text-based Active Graphics specifically
        self._active_graphic_pil_font: ImageFont.FreeTypeFont | ImageFont.ImageFont | None = None
        self._active_graphic_text_content: str | None = None
        self._active_graphic_text_scroll_if_needed: bool = True # Default, will be set by item
        self._active_graphic_text_is_scrolling: bool = False
        self._active_graphic_text_current_scroll_offset: int = 0
        self._active_graphic_text_pixel_width: int = 0
        self._active_graphic_text_scroll_timer = QTimer(self)
        self._active_graphic_text_scroll_timer.timeout.connect(self._scroll_active_graphic_text_step)
        self._active_graphic_text_step_delay_ms: int = self.DEFAULT_TEXT_ITEM_SCROLL_STEP_DELAY_MS
        self._active_graphic_text_restart_delay_ms: int = self.DEFAULT_TEXT_ITEM_SCROLL_RESTART_DELAY_MS
        self._active_graphic_text_alignment: str = "center" # Default if item doesn't specify

        # For image_animation-based Active Graphics
        self._custom_animation_logical_frames: list[list[str]] | None = None
        self._custom_animation_current_frame_index: int = 0
        self._custom_animation_playback_fps: float = 15.0
        self._custom_animation_loop_behavior: str = "Loop Infinitely"
        self._custom_animation_timer = QTimer(self)
        self._custom_animation_timer.timeout.connect(self._play_next_custom_animation_frame)
        self._is_custom_animation_playing: bool = False

        # For built-in visual startup animation
        self._is_builtin_startup_animation_playing = False
        self._builtin_startup_animation_frames: list[bytearray] = []
        self._current_builtin_startup_animation_frame_index: int = 0
        self._builtin_startup_animation_frame_duration: int = 60

        # For temporary system messages
        self.feedback_pil_font: ImageFont.FreeTypeFont | ImageFont.ImageFont | None = None # This is TomThumb 60pt
        self._app_default_message_pil_font: ImageFont.FreeTypeFont | ImageFont.ImageFont | None = None # For "Fire CTRL" style messages

        self._temporary_message_timer = QTimer(self)
        self._temporary_message_timer.setSingleShot(True)
        self._temporary_message_timer.timeout.connect(self._revert_from_temporary_display)
        self._is_temporary_message_active = False
        self._current_temporary_message_text: str | None = None
        self._temporary_message_text_scroll_timer = QTimer(self)
        self._temporary_message_text_scroll_timer.timeout.connect(self._scroll_temporary_message_step)
        self._temporary_message_is_scrolling: bool = False
        self._temporary_message_current_scroll_offset: int = 0
        self._temporary_message_text_pixel_width: int = 0
        self._temporary_message_total_duration_ms: int = 0 
        self._temporary_message_has_scrolled_once: bool = False

        # For persistent overrides (e.g., "SAMPLING")
        self.persistent_override_text: str | None = None
        self.persistent_override_pil_font: ImageFont.FreeTypeFont | ImageFont.ImageFont | None = None
        # --- End Core State Attributes ---
        
        self.oled_width = oled_renderer.OLED_WIDTH if OLED_RENDERER_AVAILABLE else 128
        self.oled_height = oled_renderer.OLED_HEIGHT if OLED_RENDERER_AVAILABLE else 64
        
        # Load fonts
        self._load_feedback_font() # Loads TomThumb 60pt into self.feedback_pil_font
        self._load_persistent_override_font() # Loads Arial 10px (or fallback) into self.persistent_override_pil_font
        self._load_app_default_message_font() # Loads a font for "Fire CTRL" style messages

        # Global scroll delay for text items (can be overridden by item's settings)
        self.global_text_item_scroll_delay_ms: int = self.DEFAULT_TEXT_ITEM_SCROLL_STEP_DELAY_MS
        
        print(f"OLEDDisplayManager: Initialized. FeedbackFont: {self.feedback_pil_font is not None}, AppDefaultFont: {self._app_default_message_pil_font is not None}")
       
    # In class OLEDDisplayManager(QObject):

    # Or a bundled small pixel font if you have one
    APP_DEFAULT_MSG_FONT_FAMILY = "Impact"
    APP_DEFAULT_MSG_FONT_SIZE_PX = 24

    def _load_app_default_message_font(self):
        """Loads a font for the application's hardcoded default message."""
        self._app_default_message_pil_font = None
        try:
            # Try to load a common system font directly with Pillow
            self._app_default_message_pil_font = ImageFont.truetype(
                self.APP_DEFAULT_MSG_FONT_FAMILY,
                self.APP_DEFAULT_MSG_FONT_SIZE_PX
            )
            print(
                f"OLED Mgr INFO: Loaded App Default Message Font '{self.APP_DEFAULT_MSG_FONT_FAMILY}' @ {self.APP_DEFAULT_MSG_FONT_SIZE_PX}px.")
        except IOError:
            print(
                f"OLED Mgr WARNING: System font '{self.APP_DEFAULT_MSG_FONT_FAMILY}' for app default message not found. Using Pillow default.")
            try:
                self._app_default_message_pil_font = ImageFont.load_default()
            except:
                pass  # Remains None if Pillow default also fails
        except Exception as e:
            print(
                f"OLED Mgr WARNING: Error loading app default message font: {e}. Using Pillow default.")
            try:
                self._app_default_message_pil_font = ImageFont.load_default()
            except:
                pass

        if not self._app_default_message_pil_font:  # Ultimate fallback if all else failed
            print("OLED Mgr WARNING: No App Default Message font loaded; will use Feedback Font as last resort for app default message.")
            # Fallback to TomThumb if app default fails badly
            self._app_default_message_pil_font = self.feedback_pil_font

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
# In class OLEDDisplayManager(QObject):

    def _load_pil_font_for_text_item(self, font_family: str, font_size_px: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont | None:
        """
        Attempts to load a PIL ImageFont object for a given text item's font settings.
        Priority: Bundled app fonts (using self._app_font_files), 
                  specified system font, common system fallback, Pillow default.
        """
        loaded_font: ImageFont.FreeTypeFont | ImageFont.ImageFont | None = None
        font_family_lower_no_ext = os.path.splitext(font_family.lower())[
            0]  # Compare base names

        print(
            f"OLED Mgr DEBUG: Attempting to load font for text item: Family='{font_family}', Size={font_size_px}px")

        # 1. Check Bundled Application Fonts (self._app_font_files was populated from MainWindow's cache)
        if hasattr(self, '_app_font_files') and self._app_font_files:
            for app_font_filename in self._app_font_files:
                app_font_filename_lower_no_ext = os.path.splitext(
                    app_font_filename.lower())[0]
                if app_font_filename_lower_no_ext == font_family_lower_no_ext:
                    try:
                        if UTILS_AVAILABLE:
                            font_path = resource_path_func(os.path.join(
                                "resources", "fonts", app_font_filename))
                            if os.path.exists(font_path):
                                loaded_font = ImageFont.truetype(
                                    font_path, font_size_px)
                                print(
                                    f"OLED Mgr INFO: Loaded BUNDLED font '{app_font_filename}' (matched '{font_family}') @{font_size_px}px for text item.")
                                return loaded_font
                            # else: # Font file listed in cache but not found at path (should not happen if cache is from valid scan)
                                # print(f"OLED Mgr WARNING: Bundled font '{app_font_filename}' for '{font_family}' in cache but not found at '{font_path}'.")
                        # else: # UTILS_AVAILABLE is False, cannot load by path
                            # print(f"OLED Mgr WARNING: Cannot load bundled font '{app_font_filename}', utils not available.")
                    except Exception as e_res:
                        print(
                            f"OLED Mgr WARNING: Exception loading BUNDLED font '{app_font_filename}' for '{font_family}': {e_res}")
                    if loaded_font:
                        break

        # 2. Attempt to Load Specified System Font by Name
        if not loaded_font:
            try:
                # font_family can be "Arial" or "algerian.ttf"
                loaded_font = ImageFont.truetype(font_family, font_size_px)
                print(
                    f"OLED Mgr INFO: Successfully loaded SYSTEM font '{font_family}' @{font_size_px}px for text item.")
                return loaded_font
            except IOError:
                print(
                    f"OLED Mgr WARNING: System font '{font_family}' not found by Pillow directly or IOError.")
            except Exception as e_sys_target:
                print(
                    f"OLED Mgr WARNING: Other error loading target system font '{font_family}': {e_sys_target}")

        # 3. Try Common Fallback System Fonts
        if not loaded_font:
            common_fallbacks = ["Arial", "Verdana", "DejaVu Sans"]
            # Avoid retrying original if it was a common one
            fallbacks_to_try = [
                f for f in common_fallbacks if f.lower() != font_family.lower()]

            for fallback_name in fallbacks_to_try:
                try:
                    loaded_font = ImageFont.truetype(
                        fallback_name, font_size_px)
                    print(
                        f"OLED Mgr INFO: Used FALLBACK system font '{fallback_name}' @{font_size_px}px for original target '{font_family}'.")
                    return loaded_font
                except IOError:
                    pass
                except Exception as e_sys_fallback:
                    print(
                        f"OLED Mgr WARNING: Error loading fallback system font '{fallback_name}': {e_sys_fallback}")

        # 4. Pillow's Default (Last Resort)
        if not loaded_font:
            try:
                loaded_font = ImageFont.load_default()
                print(
                    f"OLED Mgr WARNING: Using Pillow's load_default() font for text item originally requesting '{font_family}' @{font_size_px}px.")
            except Exception as e_def:
                print(
                    f"OLED Mgr CRITICAL: Failed to load Pillow's default font: {e_def}")

        if not loaded_font:
            print(
                f"OLED Mgr CRITICAL: NO FONT LOADED for text item '{font_family}' @{font_size_px}px. Display will likely be blank.")
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

# In class OLEDDisplayManager(QObject):

    def set_active_graphic(self, item_data: dict | None):
        # print(f"OLED Mgr INFO: set_active_graphic called. Item Name: '{item_data.get('item_name', 'None') if item_data else 'None'}'") # Log item name

        self.stop_all_activity()
        self._active_graphic_item_data = item_data

        if item_data:
            self._active_graphic_item_type = item_data.get("item_type")
            item_name_log = item_data.get("item_name", "Unnamed Item")
            # print(f"OLED Mgr INFO: Processing Active Graphic '{item_name_log}' (Type: {self._active_graphic_item_type})") # Already printed

            if self._active_graphic_item_type == "text":
                self._active_graphic_text_content = item_data.get(
                    "text_content", " ")
                font_family = item_data.get("font_family", "Arial")
                font_size_px = item_data.get("font_size_px", 10)

                self._active_graphic_pil_font = self._load_pil_font_for_text_item(
                    font_family, font_size_px)
                if not self._active_graphic_pil_font:
                    print(
                        f"OLED Mgr CRITICAL: Failed to load any font for text item '{item_name_log}'. Text display will likely use a basic fallback or be blank.")
                    # If _load_pil_font_for_text_item returns None, rendering might use a placeholder or fail.
                    # For robustness, ensure _load_pil_font_for_text_item *always* returns some font, even if basic.
                    # My provided _load_pil_font_for_text_item does attempt to always return ImageFont.load_default()

                self._active_graphic_text_alignment = item_data.get(
                    "alignment", "center").lower()
                anim_style = item_data.get("animation_style", "static")
                self._active_graphic_text_scroll_if_needed = (
                    anim_style == "scroll_left")

                anim_params = item_data.get("animation_params", {})
                self._active_graphic_text_step_delay_ms = anim_params.get(
                    "speed_override_ms", self.global_text_item_scroll_delay_ms
                )
                self._active_graphic_text_restart_delay_ms = anim_params.get(
                    "pause_at_ends_ms", self.DEFAULT_TEXT_ITEM_SCROLL_RESTART_DELAY_MS
                )
                # print(f"OLED Mgr DEBUG: Text item '{item_name_log}' params parsed: scroll={self._active_graphic_text_scroll_if_needed}, align='{self._active_graphic_text_alignment}', step_delay={self._active_graphic_text_step_delay_ms}ms") # Optional

            elif self._active_graphic_item_type == "image_animation":
                self._custom_animation_logical_frames = item_data.get(
                    "frames_logical")
                import_options = item_data.get("import_options_used", {})
                self._custom_animation_playback_fps = float(
                    import_options.get("playback_fps", 15.0))
                if self._custom_animation_playback_fps <= 0:
                    self._custom_animation_playback_fps = 15.0
                self._custom_animation_loop_behavior = import_options.get(
                    "loop_behavior", "Loop Infinitely")

                if not self._custom_animation_logical_frames:
                    print(
                        f"OLED Mgr WARNING: Animation item '{item_name_log}' has no logical frames. Will likely display blank.")

            else:
                print(
                    f"OLED Mgr WARNING: Unknown Active Graphic type '{self._active_graphic_item_type}' for item '{item_name_log}'. Clearing.")
                self._active_graphic_item_type = None
                self._active_graphic_item_data = None

        if not self._active_graphic_item_data:
            self._active_graphic_item_type = None
            self._active_graphic_text_content = None
            self._active_graphic_pil_font = None
            self._custom_animation_logical_frames = None
            # print("OLED Mgr INFO: Active Graphic is effectively None or cleared.") # Optional

        if not self._is_builtin_startup_animation_playing and \
           not self._is_temporary_message_active:
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
        # print("ODM DEBUG: _play_active_graphic_animation CALLED")  # <<< ADD
        if not self._active_graphic_item_data or \
           self._active_graphic_item_type != "image_animation" or \
           not self._custom_animation_logical_frames:
            # <<< MODIFIED
            print(
                "ODM ERROR: Cannot play active graphic animation - invalid data or no logical frames.")
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
        
        # <<< ADD
        # print(
        #     f"ODM DEBUG: Custom animation timer_interval_ms: {timer_interval_ms}ms for {self._custom_animation_playback_fps} FPS")

        self._custom_animation_timer.start(timer_interval_ms)
        self._play_next_custom_animation_frame()  # Display first frame

# In class OLEDDisplayManager(QObject):

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
        
# In class OLEDDisplayManager(QObject):
    def _start_or_display_active_graphic_text_internal(self):
        if not self._active_graphic_item_data or \
           self._active_graphic_item_type != "text" or \
           self._active_graphic_text_content is None or \
           not OLED_RENDERER_AVAILABLE: # Check renderer availability
            # print("OLED Mgr DEBUG: Conditions not met for _start_or_display_active_graphic_text_internal (missing data/renderer).")
            if not self._active_graphic_pil_font: # Specifically if font failed to load
                 print("OLED Mgr WARNING: Active graphic PIL font is None. Cannot display text item.")
            # No active text graphic to display, so ODM should fall to its own default or be blank.
            # This might happen if _load_pil_font_for_text_item returned None.
            # We should trigger _apply_current_oled_state to ensure it shows *something* (app default or blank).
            # However, to avoid recursion if this method is called *from* _apply_current_oled_state,
            # simply send a blank frame for now. _apply_current_oled_state handles the main logic.
            if OLED_RENDERER_AVAILABLE:
                self.request_send_bitmap_to_fire.emit(oled_renderer.get_blank_packed_bitmap())
            return

        text_to_display = self._active_graphic_text_content
        font_to_use = self._active_graphic_pil_font # This should now be correctly loaded or a fallback

        if not font_to_use: # Double check if font loading failed and resulted in None
            print("OLED Mgr CRITICAL: No PIL font available for Active Graphic text. Sending blank.")
            if OLED_RENDERER_AVAILABLE:
                self.request_send_bitmap_to_fire.emit(oled_renderer.get_blank_packed_bitmap())
            return
            
        self._active_graphic_text_pixel_width = oled_renderer.get_text_actual_width(text_to_display, font_to_use)
        
        # Determine if scrolling is needed based on stored item property
        needs_scroll = self._active_graphic_text_scroll_if_needed and \
                       self._active_graphic_text_pixel_width > self.oled_width and \
                       text_to_display.strip() != ""

        # print(f"OLED Mgr DEBUG Text Display: Content='{text_to_display[:20]}...', Width={self._active_graphic_text_pixel_width}, NeedsScroll={needs_scroll}, ScrollIfNedAttr={self._active_graphic_text_scroll_if_needed}")

        if needs_scroll:
            self._active_graphic_text_is_scrolling = True
            # For text scrolling left, offset_x in render_text_to_packed_buffer should be positive and increasing.
            # To start off-screen right, the initial content rendering point is to the right of the screen.
            # If render_text_to_packed_buffer draws at (-offset_x), and text starts at 0,
            # an initial offset_x of -self.oled_width makes the text start at self.oled_width (off-screen right).
            self._active_graphic_text_current_scroll_offset = -self.oled_width 
            self._render_and_send_active_graphic_text_frame() 
            self._active_graphic_text_scroll_timer.start(self._active_graphic_text_step_delay_ms)
        else:
            self._active_graphic_text_is_scrolling = False
            self._active_graphic_text_current_scroll_offset = 0 
            self._render_and_send_active_graphic_text_frame()
            
            
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

# In class OLEDDisplayManager(QObject):

    def _display_hardcoded_app_default_message(self):
        default_text = "Fire CTRL"  # Or load from a constant

        # Use the dedicated font for app default messages
        font_to_use = self._app_default_message_pil_font

        if not font_to_use:  # Fallback if _app_default_message_pil_font failed to load
            print("OLED Mgr WARNING: App default message font not loaded, using feedback font as fallback for app default.")
            # TomThumb 60pt as last resort if other default fails
            font_to_use = self.feedback_pil_font

        if not font_to_use or not OLED_RENDERER_AVAILABLE:
            if OLED_RENDERER_AVAILABLE:
                self.request_send_bitmap_to_fire.emit(
                    oled_renderer.get_blank_packed_bitmap())
            print(
                "OLED Mgr WARNING: Cannot display hardcoded app default message, no suitable font or renderer.")
            return

        bitmap = oled_renderer.render_text_to_packed_buffer(
            text=default_text,
            font_override=font_to_use,
            offset_x=0,
            center_if_not_scrolling=True  # Typically centered
        )
        if bitmap:
            self.request_send_bitmap_to_fire.emit(bitmap)
        else:
            if OLED_RENDERER_AVAILABLE:
                self.request_send_bitmap_to_fire.emit(
                    oled_renderer.get_blank_packed_bitmap())
                

    def show_system_message(self, text: str, duration_ms: int, scroll_if_needed: bool = True):
        print(
            f"OLED Mgr INFO: show_system_message: '{text}', Duration: {duration_ms}ms, Scroll: {scroll_if_needed}")

        if self._is_builtin_startup_animation_playing:
            print(
                "OLED Mgr INFO: Built-in startup playing, system message deferred/skipped.")
            return

        # Stops current Active Graphic, other temp messages, and their timers
        self.stop_all_activity()

        self._is_temporary_message_active = True
        self._current_temporary_message_text = text  # Store the text
        self._temporary_message_total_duration_ms = duration_ms  # Store requested duration
        self._temporary_message_has_scrolled_once = False  # Reset scroll completion flag

        if not self.feedback_pil_font or not OLED_RENDERER_AVAILABLE:
            print(
                "OLED Mgr WARNING: Feedback font or renderer not available for system message.")
            # Still set the main timer to revert state even if we can't display
            self._temporary_message_timer.start(
                self._temporary_message_total_duration_ms)
            if OLED_RENDERER_AVAILABLE:  # Try to send a blank screen
                self.request_send_bitmap_to_fire.emit(
                    oled_renderer.get_blank_packed_bitmap())
            return

        self._temporary_message_text_pixel_width = oled_renderer.get_text_actual_width(
            self._current_temporary_message_text, self.feedback_pil_font
        )

        self._temporary_message_is_scrolling = scroll_if_needed and \
            self._temporary_message_text_pixel_width > self.oled_width and \
            self._current_temporary_message_text.strip() != ""

        if self._temporary_message_is_scrolling:
            print(
                f"OLED Mgr DEBUG: System message '{text}' needs scrolling (width: {self._temporary_message_text_pixel_width}px).")
            self._temporary_message_current_scroll_offset = - \
                self.oled_width  # Start off-screen right
            # Display first (off-screen) frame
            self._render_and_send_temporary_message_frame()
            # Use a fixed, reasonable scroll speed for temp messages
            self._temporary_message_text_scroll_timer.start(
                self.DEFAULT_TEXT_ITEM_SCROLL_STEP_DELAY_MS)
            # The _temporary_message_timer (for overall duration) will be started by _scroll_temporary_message_step
            # once scrolling completes.
        else:  # Not scrolling
            print(
                f"OLED Mgr DEBUG: System message '{text}' is static (width: {self._temporary_message_text_pixel_width}px).")
            self._temporary_message_is_scrolling = False  # Ensure flag is correct
            self._temporary_message_current_scroll_offset = 0
            self._render_and_send_temporary_message_frame()  # Display static centered text
            # Start the main duration timer immediately for static messages
            self._temporary_message_timer.start(
                self._temporary_message_total_duration_ms)

# In class OLEDDisplayManager(QObject):

    # Text now comes from self._current_temporary_message_text
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


# In class OLEDDisplayManager(QObject):


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
            print(
                f"OLED Mgr DEBUG: Temporary message '{self._current_temporary_message_text[:20]}...' finished scrolling once.")
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

# In class OLEDDisplayManager(QObject):

    def _revert_from_temporary_display(self):
        # This slot is connected to self._temporary_message_timer.timeout()
        print(
            "OLED Mgr INFO: Reverting from temporary display (main duration timer expired).")

        # Stop any lingering scroll timer for the temporary message (should be already stopped if scroll completed)
        if self._temporary_message_text_scroll_timer.isActive():
            self._temporary_message_text_scroll_timer.stop()

        self._is_temporary_message_active = False
        self._temporary_message_is_scrolling = False
        self._current_temporary_message_text = None  # Clear the stored text
        self._temporary_message_has_scrolled_once = False

        # Now, apply the persistent OLED state (Active Graphic, Persistent Override, or App Default)
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
