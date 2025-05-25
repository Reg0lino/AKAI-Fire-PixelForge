# AKAI_Fire_RGB_Controller/managers/oled_display_manager.py
from PyQt6.QtCore import QObject, pyqtSignal, QTimer, Qt, QBuffer, QIODevice
from PyQt6.QtGui import QImage, QPainter, QColor, QFont, QFontMetrics # Keep QFont for Qt rendering path
from PIL import Image, ImageFont # Crucial for PIL font objects
import os
import sys # For sys.path manipulation if needed for utils import
import io  # For QImage to PIL conversion via QBuffer

# For get_resource_path (ensure this works for your project structure)
try:
    # If oled_display_manager.py is in 'managers' and utils.py is in project root:
    from ..utils import get_resource_path as resource_path_func 
    UTILS_AVAILABLE = True
except ImportError:
    # Fallback if the above doesn't work (e.g. running script directly or different structure)
    try:
        from utils import get_resource_path as resource_path_func
        UTILS_AVAILABLE = True
    except ImportError:
        print("OLEDDisplayManager WARNING: Could not import 'get_resource_path' from 'utils'. Resource font loading will likely fail.")
        UTILS_AVAILABLE = False
        def resource_path_func(relative_path): 
            print(f"OLEDDisplayManager DUMMY resource_path_func for: {relative_path}")
            return os.path.join(".", relative_path) 

try:
    from oled_utils import oled_renderer
    OLED_RENDERER_AVAILABLE = True
except ImportError as e:
    print(f"OLEDDisplayManager WARNING: Could not import oled_renderer: {e}. OLED functionality will be limited.")
    OLED_RENDERER_AVAILABLE = False
    class oled_renderer_placeholder: # Minimal placeholder
        OLED_WIDTH = 128; OLED_HEIGHT = 64
        @staticmethod
        def render_text_to_packed_buffer(text, font_override, offset_x, center_if_not_scrolling): return None
        @staticmethod
        def pack_pil_image_to_7bit_stream(pil_image): return None
        @staticmethod
        def get_text_actual_width(text, font): return len(text) * 6
    if 'oled_renderer' not in globals(): oled_renderer = oled_renderer_placeholder()


class OLEDDisplayManager(QObject):
    request_send_bitmap_to_fire = pyqtSignal(bytearray)
    startup_animation_finished = pyqtSignal()

    DEFAULT_SCROLL_DELAY_MS = 50 # adjust to increase/decrease scroll speed/ the behavior is as follows if you increase the delay:
    # This is the time interval (in milliseconds) between each small movement (step) of the scrolling text.
    # Increasing this value:
    #   - Makes the text scroll slower because there's a longer pause between each tiny shift.
    #   - The animation will appear less fluid and more "steppy" if the delay is too high for the step size
    #     (e.g., if you scroll 2 pixels every 500ms, it's very jerky).
    # Decreasing this value:
    #   - Makes the text scroll faster and appear smoother (more updates per second).
    #   - If too low (e.g., below ~30-50ms, depending on processing), it might not have a visible effect
    #     or could strain resources if updates are too frequent.
    # This is the duration (in milliseconds) the scroll timer pauses after the text has completely
    # scrolled off one side and before it reappears from the other side to start the next loop.
    # Increasing this value: Creates a longer "empty screen" or "waiting" period between full passes of the text.
    # Decreasing this value: Makes the text loop around more quickly with less of a pause.
    # Key point: This specifically controls the pause between full scroll cycles,
    # not the speed of the text itself while it's moving.
    DEFAULT_SCROLL_RESTART_DELAY_MS = 2000

    # Duration for static text display before scrolling starts again (if needed elsewhere)
    STATIC_TEXT_DISPLAY_DURATION_MS = 2500
    # STATIC_TEXT_DISPLAY_DURATION_MS is used by set_display_text(..., temporary_duration_ms=...).
    # It defines how long a temporary, non-scrolling (static) message (e.g., "Sequence Saved!") is shown
    # before the display automatically reverts to normal_display_text (which may scroll if long).
    # Increasing this value: The temporary static message stays visible longer.
    # Decreasing this value: The temporary static message disappears more quickly.
    # Key point: This is for temporary static messages only, not for the looping scroll of persistent text.
    # The _revert_from_temporary_text slot is triggered after this duration.

    def __init__(self, akai_fire_controller_ref, parent: QObject | None = None):
        super().__init__(parent)
        
        self.current_display_text: str | None = None      
        self.normal_display_text: str | None = None       
        self.persistent_override_text: str | None = None  
        self.is_knob_feedback_active: bool = False 

        self.scroll_timer = QTimer(self)
        self.scroll_timer.timeout.connect(self._scroll_text_step)
        self.current_scroll_offset = 0
        self.text_width_pixels = 0 
        self.is_scrolling_active = False
        self.is_startup_animation_playing = False

        self._animation_frames: list[bytearray] = []
        self._current_animation_frame_index: int = 0
        self._animation_frame_duration: int = 60

        self.oled_width = oled_renderer.OLED_WIDTH if OLED_RENDERER_AVAILABLE else 128
        self.oled_height = oled_renderer.OLED_HEIGHT if OLED_RENDERER_AVAILABLE else 64
        
        self.startup_text: str = "Fire CTRL Ready!" 
        self.startup_font_family: str = "Arial"    
        self.startup_font_size_px: int = 12        
        
        # --- ADD: Attribute for effective scroll delay ---
        self.effective_scroll_delay_ms: int = self.DEFAULT_SCROLL_DELAY_MS # Initialize with class default
        # --- END ADD ---

        self.active_pil_font_object: ImageFont.FreeTypeFont | ImageFont.ImageFont | None = None 
        self.knob_feedback_pil_font: ImageFont.FreeTypeFont | ImageFont.ImageFont | None = None
        
        # --- ADD: Load dedicated font for knob feedback ---
        if UTILS_AVAILABLE and OLED_RENDERER_AVAILABLE: # Only try if utils and renderer are available
            try:
                feedback_font_path = resource_path_func(os.path.join("resources", "fonts", "TomThumb.ttf"))
                if os.path.exists(feedback_font_path):
                    self.knob_feedback_pil_font = ImageFont.truetype(feedback_font_path, 60) # Use 60px as requested
                    print(f"OLED Mgr INFO: Loaded TomThumb.ttf @ 60px for knob feedback.")
                else:
                    print(f"OLED Mgr WARNING: TomThumb.ttf for knob feedback not found at '{feedback_font_path}'.")
                    raise IOError("Knob feedback font file not found.")
            except Exception as e_kf:
                print(f"OLED Mgr WARNING: Failed to load TomThumb.ttf @ 60px for knob feedback: {e_kf}. Using Pillow default for feedback.")
                try:
                    self.knob_feedback_pil_font = ImageFont.load_default()
                except: # Should not happen
                    self.knob_feedback_pil_font = None 
        elif not UTILS_AVAILABLE:
            print("OLED Mgr WARNING: Utils not available, cannot load specific knob feedback font by path.")
            try: self.knob_feedback_pil_font = ImageFont.load_default()
            except: self.knob_feedback_pil_font = None
        # --- END ADD ---
        
        self._try_load_resource_font_for_startup() 
        
        print(f"OLEDDisplayManager: Initialized. Startup Font Target: '{self.startup_font_family}' @ {self.startup_font_size_px}px, ScrollDelay: {self.effective_scroll_delay_ms}ms")
        # ... (logging for active_pil_font_object as before)

    def _try_load_resource_font_for_startup(self):
        """
        Attempts to load self.startup_font_family as a resource font into self.active_pil_font_object.
        Called on init and when default text settings are updated.
        """
        self.active_pil_font_object = None # Reset
        font_family_to_load = self.startup_font_family
        font_size_to_load = self.startup_font_size_px

        known_resource_fonts = {"tomthumb.ttf": "TomThumb.ttf"} # Can expand this
        is_known_resource = font_family_to_load.lower() in known_resource_fonts

        if is_known_resource:
            actual_resource_filename = known_resource_fonts[font_family_to_load.lower()]
            print(f"OLED Mgr DEBUG: _try_load_resource_font - Attempting RESOURCE: '{actual_resource_filename}'")
            try:
                # Ensure resource_path_func is available
                if 'resource_path_func' not in globals() or not callable(globals().get('resource_path_func')):
                    from ..utils import get_resource_path as resource_path_func # Adjust if utils path is different
                
                font_path = resource_path_func(os.path.join("resources", "fonts", actual_resource_filename))
                if os.path.exists(font_path):
                    self.active_pil_font_object = ImageFont.truetype(font_path, font_size_to_load)
                    print(f"OLED Mgr INFO: _try_load_resource_font - SUCCESS - Loaded RESOURCE font '{actual_resource_filename}' into PIL ImageFont.")
                else:
                    print(f"OLED Mgr WARNING: _try_load_resource_font - Resource font file NOT FOUND: '{font_path}'")
            except Exception as e_res:
                print(f"OLED Mgr WARNING: _try_load_resource_font - Failed to load resource font '{actual_resource_filename}': {e_res}")
        # else: # Optional: print if it's not a known resource, will be handled by Qt rendering path
            # print(f"OLED Mgr DEBUG: _try_load_resource_font - '{font_family_to_load}' is not a known resource filename. Will use Qt rendering.")

    def update_scroll_speed(self, new_delay_ms: int):
        """
        Updates the effective scroll delay for scrolling text.
        Called by MainWindow when the global scroll speed setting changes.
        """
        min_practical_delay = 30  # e.g., prevents trying to scroll faster than ~33 FPS updates
        max_practical_delay = 1000 # e.g., 1 second per step is very slow
        
        self.effective_scroll_delay_ms = max(min_practical_delay, min(new_delay_ms, max_practical_delay))
        
        print(f"OLED Mgr INFO: Scroll speed (effective_scroll_delay_ms) updated to {self.effective_scroll_delay_ms} ms per step.")
        
        # If scrolling is currently active, update the timer's interval immediately.
        # This ensures the new speed takes effect on the next scroll step if changed mid-scroll.
        if self.is_scrolling_active and self.scroll_timer.isActive():
            # Check if the timer is in its long "restart_delay" phase
            current_interval = self.scroll_timer.interval()
            if current_interval == self.DEFAULT_SCROLL_RESTART_DELAY_MS:
                # If it's in the long pause between loops, don't change that specific long pause.
                # The next time it starts a normal scroll step, _scroll_text_step will use the new effective_scroll_delay_ms.
                print(f"OLED Mgr DEBUG: Scroll timer currently in restart delay ({current_interval}ms), new speed will apply on next scroll cycle.")
            else:
                # It's in its normal step-by-step scrolling phase, so update the interval.
                self.scroll_timer.setInterval(self.effective_scroll_delay_ms)
                print(f"OLED Mgr DEBUG: Active scroll timer interval updated to {self.effective_scroll_delay_ms}ms.")

                
    def _render_text_to_bitmap(self, text_to_render: str | None) -> bytearray | None:
        if not OLED_RENDERER_AVAILABLE: return None
        if text_to_render is None: text_to_render = " "

        use_pil_direct_render = False
        known_resource_fonts = {"tomthumb.ttf": "TomThumb.ttf"}
        # Check if the current startup font is a known resource and if its PIL font object was loaded
        if self.startup_font_family and \
           self.startup_font_family.lower() in known_resource_fonts and \
           self.active_pil_font_object:
            use_pil_direct_render = True

        offset_to_pass = self.current_scroll_offset if self.is_scrolling_active and self.text_width_pixels > self.oled_width else 0
        center_text_if_not_scrolling = not (self.is_scrolling_active and self.text_width_pixels > self.oled_width)

        if use_pil_direct_render:
            # print(f"OLED Mgr DEBUG: Rendering '{text_to_render}' using PIL direct.") # Optional
            try:
                return oled_renderer.render_text_to_packed_buffer(
                    text=text_to_render,
                    font_override=self.active_pil_font_object,
                    offset_x=offset_to_pass,
                    center_if_not_scrolling=center_text_if_not_scrolling
                )
            except Exception as e_pil_render:
                print(f"OLED Mgr ERROR: PIL direct render failed: {e_pil_render}. Falling back to Qt render.")
                # Fallthrough to Qt render path
        
        # Path 2: System Font or Failed Resource - Render with Qt then convert to PIL
        # print(f"OLED Mgr DEBUG: Rendering '{text_to_render}' using Qt text render path for font '{self.startup_font_family}'.") # Optional
        try:
            q_font = QFont(self.startup_font_family, pointSize=-1) # Let Qt find system font
            q_font.setPixelSize(self.startup_font_size_px)

            # Render to QImage (monochrome)
            q_image = QImage(self.oled_width, self.oled_height, QImage.Format.Format_Mono)
            q_image.fill(0) # 0 is black for Format_Mono
            painter = QPainter(q_image)
            painter.setFont(q_font)
            painter.setPen(QColor(Qt.GlobalColor.white)) # 1 is white for Format_Mono

            fm = painter.fontMetrics()
            text_pixel_width = fm.horizontalAdvance(text_to_render)
            text_draw_y = fm.ascent() + (self.oled_height - fm.height()) // 2
            text_draw_x = 0
            if center_text_if_not_scrolling and offset_to_pass == 0:
                if text_pixel_width < self.oled_width:
                    text_draw_x = (self.oled_width - text_pixel_width) // 2
            else: 
                text_draw_x = -offset_to_pass
            
            painter.drawText(text_draw_x, text_draw_y, text_to_render)
            painter.end()

            # --- ROBUST QImage to PIL Image conversion using QBuffer ---
            buffer = QBuffer()
            # QIODevice.OpenModeFlag for PyQt6
            if hasattr(QIODevice, 'OpenModeFlag'): # PyQt6 v6.2+
                 buffer.open(QIODevice.OpenModeFlag.ReadWrite)
                 q_image.save(buffer, "PNG") # Save QImage to buffer as PNG
            else: # Older PyQt6 or fallback
                 buffer.open(QBuffer.OpenMode.ReadWrite) # type: ignore
                 q_image.save(buffer, "PNG") # type: ignore
            
            # Ensure you have 'import io' at the top of your file
            pil_image_from_qimage = Image.open(io.BytesIO(buffer.data()))
            
            # Convert to 1-bit monochrome if it's not already (PNG might be RGBA or L)
            if pil_image_from_qimage.mode != '1':
                pil_monochrome_image = pil_image_from_qimage.convert('1')
            else:
                pil_monochrome_image = pil_image_from_qimage
            # --- END ROBUST CONVERSION ---
            
            if pil_monochrome_image is None:
                print("OLED Mgr ERROR: Conversion from QImage to PIL monochrome image failed.")
                return None

            return oled_renderer.pack_pil_image_to_7bit_stream(pil_monochrome_image)

        except Exception as e_qt_render:
            print(f"OLEDDisplayManager Error: Qt rendering or QImage->PIL conversion for '{text_to_render}': {e_qt_render}")
            import traceback
            traceback.print_exc() # Get full traceback for this error
            return None


    def _update_display(self, text_to_show: str | None):
        self.current_display_text = text_to_show
        bitmap = self._render_text_to_bitmap(text_to_show)
        if bitmap:
            self.request_send_bitmap_to_fire.emit(bitmap)
        # else: # Optional: send blank if render failed
            # self.clear_display_content() # Or some error message bitmap

    def _needs_scrolling(self, text: str | None) -> bool:
        if not text: 
            self.text_width_pixels = 0
            return False
        
        use_pil_direct_render_for_width = False
        known_resource_fonts = {"tomthumb.ttf": "TomThumb.ttf"}
        if self.startup_font_family.lower() in known_resource_fonts and self.active_pil_font_object:
            use_pil_direct_render_for_width = True

        try:
            if use_pil_direct_render_for_width and OLED_RENDERER_AVAILABLE:
                # print(f"OLED Mgr DEBUG: _needs_scrolling using PIL font for width: {self.active_pil_font_object.font.family if hasattr(self.active_pil_font_object, 'font') else 'PillowBitmapFont'}")
                self.text_width_pixels = oled_renderer.get_text_actual_width(text, self.active_pil_font_object)
            else:
                # Use Qt QFontMetrics for system fonts
                q_font = QFont(self.startup_font_family, pointSize=-1)
                q_font.setPixelSize(self.startup_font_size_px)
                fm = QFontMetrics(q_font)
                self.text_width_pixels = fm.horizontalAdvance(text)
                # print(f"OLED Mgr DEBUG: _needs_scrolling using QFontMetrics for width. Font: {self.startup_font_family} {self.startup_font_size_px}px, Calculated Width: {self.text_width_pixels}")

            return self.text_width_pixels > self.oled_width
        except Exception as e:
            print(f"OLEDDisplayManager Error: Calculating text width for '{text}': {e}")
            self.text_width_pixels = len(text) * 6 # Crude fallback
            return self.text_width_pixels > self.oled_width


    def update_default_text_settings(self, text: str, font_family: str, font_size_px: int):
        self.startup_text = text if text is not None else " "
        self.startup_font_family = font_family if font_family else "Arial" 
        self.startup_font_size_px = font_size_px if font_size_px > 0 else 10
        
        self._try_load_resource_font_for_startup() # Attempt to load if it's a resource font
        
        self.normal_display_text = self.startup_text
        if self.persistent_override_text is None and \
           not self.is_knob_feedback_active and \
           not self.is_startup_animation_playing:
            self.set_display_text(self.startup_text, scroll_if_needed=True)
        
        print(f"OLED Mgr: Default text settings updated. Text: '{self.startup_text}', Font Target: '{self.startup_font_family}' {self.startup_font_size_px}px")
    
    def _create_active_font(self):
        """
        Creates/updates self.active_font_object (a PIL ImageFont) based on
        self.startup_font_family and self.startup_font_size_px.
        Prioritizes known resource fonts, then tries selected system font,
        then common system fallbacks, then Pillow's default.
        """
        font_family_to_load = self.startup_font_family
        font_size_to_load = self.startup_font_size_px
        loaded_successfully = False
        temp_font_object = None # Use a temporary variable to build the font

        print(f"OLED Mgr DEBUG: _create_active_font - START - Target: Family='{font_family_to_load}', Size={font_size_to_load}px")

        if not font_family_to_load or font_size_to_load <= 0:
            print(f"OLED Mgr DEBUG: _create_active_font - Invalid font family ('{font_family_to_load}') or size ({font_size_to_load}px). Attempting Pillow default immediately.")
            try:
                temp_font_object = ImageFont.load_default()
                if temp_font_object:
                    print("OLED Mgr INFO: _create_active_font - SUCCESS using Pillow load_default() (due to invalid input).")
                    loaded_successfully = True
                else:
                    print("OLED Mgr CRITICAL: _create_active_font - Pillow load_default() returned None (due to invalid input).")
            except Exception as e_def_early:
                print(f"OLED Mgr CRITICAL: _create_active_font - Failed to load Pillow default font (early fallback): {e_def_early}")
            self.active_font_object = temp_font_object # Assign whatever we got (even if None)
            return

        # --- Priority 1: Check if it's our known bundled resource font by filename ---
        known_resource_fonts = {"tomthumb.ttf": "TomThumb.ttf"} 
        
        if font_family_to_load.lower() in known_resource_fonts:
            actual_resource_filename = known_resource_fonts[font_family_to_load.lower()]
            print(f"OLED Mgr DEBUG: _create_active_font - Attempting as KNOWN RESOURCE font: '{actual_resource_filename}'")
            try:
                # Ensure resource_path_func is available -
                # Best to have 'from ..utils import get_resource_path as resource_path_func' at module top
                if 'resource_path_func' not in globals() or not callable(globals().get('resource_path_func')):
                    print("OLED Mgr WARNING: _create_active_font - 'resource_path_func' not found or not callable in globals. Attempting local import.")
                    # This import structure assumes 'managers' is a subdir of project root where 'utils.py' also is.
                    # If project root is not in sys.path, this might fail.
                    # fire_control_app.py should add project root to sys.path.
                    try:
                        from utils import get_resource_path as resource_path_func
                    except ImportError:
                        # Last resort relative import attempt
                        from ..utils import get_resource_path as resource_path_func

                font_path = resource_path_func(os.path.join("resources", "fonts", actual_resource_filename))
                print(f"OLED Mgr DEBUG: _create_active_font - Resource path for '{actual_resource_filename}': '{font_path}'")
                if os.path.exists(font_path):
                    temp_font_object = ImageFont.truetype(font_path, font_size_to_load)
                    print(f"OLED Mgr INFO: _create_active_font - SUCCESS - Loaded RESOURCE font '{actual_resource_filename}' size {font_size_to_load}px")
                    loaded_successfully = True
                else:
                    print(f"OLED Mgr WARNING: _create_active_font - Resource font file NOT FOUND at '{font_path}'")
            except NameError as ne: 
                print(f"OLED Mgr ERROR: _create_active_font - NameError for 'resource_path_func'. Cannot load resource. {ne}")
            except ImportError as ie:
                 print(f"OLED Mgr ERROR: _create_active_font - ImportError for 'utils' or 'resource_path_func'. {ie}")
            except Exception as e_res:
                print(f"OLED Mgr WARNING: _create_active_font - Exception loading resource font '{actual_resource_filename}': {e_res}")
        
        # --- Priority 2: Try to load as a system font (if not a known resource or resource load failed) ---
        if not loaded_successfully:
            font_names_to_try = [font_family_to_load]
            # Add common fallbacks if the initial one isn't 'Arial' or 'Consolas' (case-insensitive check)
            if font_family_to_load.lower() != "arial" and "Arial" not in font_names_to_try : font_names_to_try.append("Arial")
            if font_family_to_load.lower() != "consolas" and "Consolas" not in font_names_to_try: font_names_to_try.append("Consolas")

            for fname_try in font_names_to_try:
                if loaded_successfully: break 
                print(f"OLED Mgr DEBUG: _create_active_font - Attempting as SYSTEM font: '{fname_try}' with size {font_size_to_load}px")
                try:
                    temp_font_object = ImageFont.truetype(fname_try, font_size_to_load)
                    print(f"OLED Mgr INFO: _create_active_font - SUCCESS - Loaded SYSTEM font '{fname_try}' size {font_size_to_load}px")
                    loaded_successfully = True
                    if fname_try.lower() != font_family_to_load.lower(): # If a fallback was used
                        print(f"OLED Mgr INFO: _create_active_font - Note: Original target system font '{font_family_to_load}' failed, used fallback '{fname_try}'.")
                        # Optionally update self.startup_font_family here if you want the state to reflect the fallback.
                        # self.startup_font_family = fname_try 
                except IOError: 
                    print(f"OLED Mgr WARNING: _create_active_font - System font '{fname_try}' NOT FOUND by Pillow or Pillow IOError.")
                except Exception as e_sys: 
                    print(f"OLED Mgr WARNING: _create_active_font - Other error loading system font '{fname_try}': {e_sys}")

        # --- Priority 3: Pillow's load_default ---
        if not loaded_successfully:
            print(f"OLED Mgr DEBUG: _create_active_font - All specific loads failed. Falling back to Pillow load_default().")
            try:
                temp_font_object = ImageFont.load_default() 
                if temp_font_object:
                    print(f"OLED Mgr INFO: _create_active_font - SUCCESS - Using Pillow load_default() font.")
                    loaded_successfully = True # To be precise, it was loaded
                else:
                    print(f"OLED Mgr CRITICAL: _create_active_font - Pillow load_default() returned None.")
            except Exception as e_def:
                print(f"OLED Mgr CRITICAL: _create_active_font - Exception loading Pillow default font: {e_def}")
                temp_font_object = None 
        
        self.active_font_object = temp_font_object # Assign the result to the instance attribute
        
        # Logging the final chosen font
        if self.active_font_object:
            font_name_log = "Unknown PIL Font"
            font_size_log = "N/A" # For basic bitmap fonts, size might not be directly available as an int
            try:
                if hasattr(self.active_font_object, 'font') and hasattr(self.active_font_object.font, 'family'): # For FreeTypeFont
                    font_name_log = self.active_font_object.font.family
                    font_size_log = str(self.active_font_object.size)
                elif isinstance(self.active_font_object, ImageFont.ImageFont): # For basic ImageFont from load_default
                     font_name_log = "Pillow Default Bitmap"
                     # Heuristic: try to report the size it was *intended* to be if it was a fallback for a specific size request
                     if not loaded_successfully or (font_family_to_load.lower() in known_resource_fonts and not temp_font_object.path.endswith(font_family_to_load)): # if it's pillow default after trying a specific size
                        font_size_log = f"approx {font_size_to_load}px (intended for '{font_family_to_load}')"
                     else: # True pillow default without specific prior size request
                        font_size_log = f"approx 10px (Pillow default actual)"

                print(f"OLED Mgr TRACE: _create_active_font - FINISHED. Final self.active_font_object: Name='{font_name_log}', Size='{font_size_log}'")
            except Exception as e_log:
                print(f"OLED Mgr TRACE: _create_active_font - FINISHED. Final self.active_font_object loaded, but error logging its details: {e_log}")

        else:
             print("OLED Mgr CRITICAL: _create_active_font - FINISHED. Final self.active_font_object is None (NO FONT LOADED).")

    def _start_scrolling_if_needed(self, text: str):
        self.stop_scrolling() 
        if self._needs_scrolling(text): # This correctly sets self.text_width_pixels
            self.is_scrolling_active = True
            # --- CHANGE: Initial offset for text to start off-screen right ---
            # The 'offset_x' in render_text_to_packed_buffer is how much the text's
            # natural starting point (0 for left-aligned) is shifted *left* of the screen edge.
            # So, to start text off-screen right, its drawing start point should be OLED_WIDTH.
            # If render_text_to_packed_buffer draws at (-offset_x + centering_adjust),
            # we want -offset_x to be OLED_WIDTH. So, offset_x should be -OLED_WIDTH.
            self.current_scroll_offset = -self.oled_width 
            # print(f"DEBUG OLED: _start_scrolling_if_needed - Text: '{text}', Initial offset: {self.current_scroll_offset}, TextWidth: {self.text_width_pixels}")
            # --- END CHANGE ---
            self._update_display(text) # Initial render (text will be off-screen left due to renderer logic for offset_x)
            # --- CHANGE: Use effective_scroll_delay_ms ---
            self.scroll_timer.start(self.effective_scroll_delay_ms)
            # --- END CHANGE ---
        else:
            self.is_scrolling_active = False
            self._update_display(text) # Render static centered text

    def _scroll_text_step(self):
        if not self.is_scrolling_active or self.current_display_text is None:
            self.stop_scrolling()
            return

        # --- CHANGE: To scroll text left, the effective drawing position moves left. ---
        # If render_text_to_packed_buffer draws at (-offset_x + centering_adjust),
        # to move text left, -offset_x must decrease. So, offset_x must INCREASE.
        self.current_scroll_offset += 2 # Increase offset_x
        # --- END CHANGE ---
        
        if self.text_width_pixels == 0: # Safety if text changed and width wasn't updated
            if not self._needs_scrolling(self.current_display_text): # Also updates text_width_pixels
                self.stop_scrolling() # Text no longer needs scrolling
                self._update_display(self.current_display_text) # Display it statically
                return
        
        # Loop condition: when the text has completely passed the left edge.
        # The text starts effectively at -self.current_scroll_offset.
        # It is off-screen left when -self.current_scroll_offset + self.text_width_pixels < 0
        # which means text_width_pixels < self.current_scroll_offset
        if self.text_width_pixels > 0 and self.current_scroll_offset > self.text_width_pixels:
            # print(f"OLED Mgr: Text '{self.current_display_text}' scrolled off. Resetting.")
            # Reset to start off-screen right again
            self.current_scroll_offset = -self.oled_width 
            self.scroll_timer.setInterval(self.DEFAULT_SCROLL_RESTART_DELAY_MS) 
        else:
            # --- CHANGE: Use effective_scroll_delay_ms ---
            self.scroll_timer.setInterval(self.effective_scroll_delay_ms)
            # --- END CHANGE ---
        
        self._update_display(self.current_display_text)

    def stop_scrolling(self):
        self.scroll_timer.stop()
        self.is_scrolling_active = False
        # Do not reset current_scroll_offset here if we want temporary static text to not jump
        # self.text_width_pixels = 0 # Keep text_width_pixels if current_display_text is still valid

    def _revert_from_temporary_text(self):
        # print("OLED Mgr: _revert_from_temporary_text called.")
        # This is ONLY for temporary messages set via set_display_text(..., temporary_duration_ms > 0)
        # It should revert to the established normal_display_text or persistent_override_text.
        self.is_knob_feedback_active = False # Ensure this is off
        
        text_to_show_after_temp = self.persistent_override_text if self.persistent_override_text is not None else self.normal_display_text
        
        if text_to_show_after_temp is None or text_to_show_after_temp.strip() == "":
            text_to_show_after_temp = " "
            
        self.stop_scrolling() # Stop current scroll (which was the temporary text)
        if self._needs_scrolling(text_to_show_after_temp):
            self._start_scrolling_if_needed(text_to_show_after_temp)
        else:
            self._update_display(text_to_show_after_temp)

    def clear_persistent_override(self):
        self.set_persistent_override(None, scroll_if_needed=True)

    # --- METHODS FOR KNOB FEEDBACK ---
    def show_temporary_knob_value(self, text: str):
        """Displays text immediately for knob feedback, does not alter normal/persistent state."""
        # print(f"OLED Mgr TRACE: show_temporary_knob_value with '{text}'") # Optional
        if self.is_startup_animation_playing: 
            # print("OLED Mgr TRACE: Startup animation playing, knob feedback deferred.") # Optional
            return 

        self.is_knob_feedback_active = True 
        self.stop_scrolling() # Knob values are usually short and static
        
        # Use the dedicated knob feedback font
        font_for_feedback = self.knob_feedback_pil_font
        if font_for_feedback is None: # Fallback if dedicated knob font failed to load
            print("OLED Mgr WARNING: Knob feedback font not loaded, using Pillow default for feedback text.")
            try:
                font_for_feedback = ImageFont.load_default()
            except: # Ultimate fallback
                self._update_display("ERR:Font") # Show font error if even default fails
                return

        if OLED_RENDERER_AVAILABLE:
            bitmap = oled_renderer.render_text_to_packed_buffer(
                text=text,
                font_override=font_for_feedback, # Explicitly pass the knob feedback font
                offset_x=0, 
                center_if_not_scrolling=True
            )
            if bitmap:
                self.request_send_bitmap_to_fire.emit(bitmap)
                self.current_display_text = text # Update what's currently shown
            else:
                print(f"OLED Mgr WARNING: Failed to render knob feedback text: '{text}' with dedicated font.")
                # Optionally, try to render with a very basic font or show "..."
                self._update_display("...") # Fallback display for knob feedback render error
        else:
            print("OLED Mgr WARNING: OLED Renderer not available for knob feedback.")


    def get_current_intended_display_text(self) -> str | None:
        """Returns what should be displayed if knob feedback or startup animation wasn't active."""
        if self.is_startup_animation_playing:
            return self.normal_display_text # Or specific "loading" text
        if self.persistent_override_text is not None:
            return self.persistent_override_text
        return self.normal_display_text

    def revert_after_knob_feedback(self):
        """
        Called by MainWindow's timer to restore display after knob feedback.
        It retrieves what *should* be displayed and re-applies it.
        """
        # print("OLED Mgr TRACE: revert_after_knob_feedback called.") # Optional
        if self.is_startup_animation_playing: return 

        self.is_knob_feedback_active = False # Crucial: turn off knob feedback mode
        text_to_restore = self.get_current_intended_display_text() 
        
        # If text_to_restore is None (e.g. normal_display_text was never set after init),
        # use the startup_text as the ultimate fallback.
        if text_to_restore is None:
             text_to_restore = self.startup_text if self.startup_text else " "
        
        if text_to_restore.strip() == "": # Ensure some content or clear space
            text_to_restore = " "

        # print(f"OLED Mgr: Reverting display to: '{text_to_restore}'") # Optional
        
        # This call will re-evaluate scrolling and use the correct font (active_pil_font_object or Qt render)
        self.set_display_text(text_to_restore, scroll_if_needed=True)


    def set_display_text(self, text: str | None, scroll_if_needed: bool = True, temporary_duration_ms: int = 0):
        # print(f"OLED Mgr: set_display_text('{text}') called. Knob feedback: {self.is_knob_feedback_active}, Startup anim: {self.is_startup_animation_playing}") # Optional
        
        if self.is_startup_animation_playing:
            # If startup animation is playing, just update normal_display_text for when it finishes
            self.normal_display_text = text
            return

        # If this call is to revert from knob feedback AND the text matches normal_display_text
        if self.is_knob_feedback_active and text == self.normal_display_text:
            self.is_knob_feedback_active = False # Knob feedback period is over OR explicitly cancelled by this call
        elif self.is_knob_feedback_active: 
            self.is_knob_feedback_active = False # Any other call to set_display_text cancels knob feedback mode
        
        self.stop_scrolling() 
        self.normal_display_text = text 

        text_to_actually_show = self.persistent_override_text if self.persistent_override_text is not None else self.normal_display_text
        
        if text_to_actually_show is None or text_to_actually_show.strip() == "":
             text_to_actually_show = " " 

        if scroll_if_needed:
            self._start_scrolling_if_needed(text_to_actually_show)
        else:
            self._update_display(text_to_actually_show)

        if temporary_duration_ms > 0:
            QTimer.singleShot(temporary_duration_ms, self._revert_from_temporary_text)

    def set_persistent_override(self, text: str | None, scroll_if_needed: bool = True):
        # print(f"OLED Mgr: set_persistent_override('{text}') called.") # Optional
        if self.is_startup_animation_playing:
            # If startup animation is playing, just update persistent_override_text for when it finishes
            self.persistent_override_text = text
            return

        self.is_knob_feedback_active = False 
        self.stop_scrolling()
        self.persistent_override_text = text

        text_to_show = self.persistent_override_text
        if text_to_show is None: 
            text_to_show = self.normal_display_text if self.normal_display_text is not None else " "
        
        if scroll_if_needed: self._start_scrolling_if_needed(text_to_show)
        else: self._update_display(text_to_show)

    def play_startup_animation(self, frames_data: list[bytearray], frame_duration_ms: int):
        if not frames_data: 
            self.startup_animation_finished.emit()
            return
        if self.is_startup_animation_playing: return 

        # print("OLED Mgr: play_startup_animation called.") # Optional
        self.is_startup_animation_playing = True
        self.is_knob_feedback_active = False # Startup anim overrides knob feedback
        self.stop_scrolling()

        self._animation_frames = frames_data
        self._current_animation_frame_index = 0
        self._animation_frame_duration = frame_duration_ms
        QTimer.singleShot(0, self._play_next_startup_frame)
    
    def _play_next_startup_frame(self):
        if not self.is_startup_animation_playing or \
           self._current_animation_frame_index >= len(self._animation_frames):
            self.is_startup_animation_playing = False
            self._animation_frames.clear()
            self.startup_animation_finished.emit() # MainWindow will call set_default_scrolling_text_after_startup
            return

        frame_bitmap = self._animation_frames[self._current_animation_frame_index]
        if frame_bitmap:
            self.request_send_bitmap_to_fire.emit(frame_bitmap)
        self._current_animation_frame_index += 1
        QTimer.singleShot(self._animation_frame_duration, self._play_next_startup_frame)
        
    def set_default_scrolling_text_after_startup(self, text: str):
        if not self.is_startup_animation_playing: # Only if startup is not active
             # This becomes the new normal text
            self.set_display_text(text, scroll_if_needed=True)
        # else: print("OLED Mgr: Startup anim playing, default text deferred.") # Optional

    def clear_display_content(self):
        # print("OLED Mgr: clear_display_content called.")
        self.stop_all_activity() # Stops animation and scrolling
        self.normal_display_text = " "      # Set normal to blank
        self.persistent_override_text = None # Clear persistent
        self.is_knob_feedback_active = False
        self._update_display(" ")           # Send blank space to OLED

    def stop_all_activity(self):
        # print("OLED Mgr: stop_all_activity called.")
        self.is_startup_animation_playing = False # Stops animation loop
        self._animation_frames.clear()
        self.stop_scrolling() # Stops text scrolling timer