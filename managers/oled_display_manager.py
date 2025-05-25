### START OF FILE oled_display_manager.py ###
# AKAI_Fire_RGB_Controller/managers/oled_display_manager.py
from PyQt6.QtCore import QObject, pyqtSignal, QTimer, Qt
from PyQt6.QtGui import QImage, QPainter, QColor, QFont # Ensure QFont is imported

# It's good practice to handle potential import errors for project-specific modules
try:
    from oled_utils import oled_renderer
    # Assuming AkaiFireController is not directly used by OLEDDisplayManager itself,
    # but rather its signals are connected externally by MainWindow.
    # If it were directly used, an import would be here:
    # from hardware.akai_fire_controller import AkaiFireController
    OLED_RENDERER_AVAILABLE = True
except ImportError as e:
    print(f"OLEDDisplayManager WARNING: Could not import oled_renderer: {e}. OLED functionality will be limited.")
    OLED_RENDERER_AVAILABLE = False
    # Define a placeholder for oled_renderer if critical functions are called
    class oled_renderer_placeholder:
        OLED_WIDTH = 128
        OLED_HEIGHT = 64
        @staticmethod
        def load_font(prefer_custom=True, size_px=10): return QFont("Arial", 10) # Fallback font
        @staticmethod
        def render_text_to_7bit_packed_buffer(text, font_override, offset_x, center_if_not_scrolling): return None
        @staticmethod
        def get_text_width_pixels(text, font): return len(text) * 6 # Rough estimate
    if 'oled_renderer' not in globals(): # If import failed, assign placeholder
        oled_renderer = oled_renderer_placeholder


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
        # self.akai_fire_controller = akai_fire_controller_ref # Not directly used, connection is external

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
        self._animation_frame_duration: int = 60 # Default, can be set by play_startup_animation

        self.oled_width = oled_renderer.OLED_WIDTH
        self.oled_height = oled_renderer.OLED_HEIGHT
        
        # Attempt to load font using oled_renderer
        # self.font = QFont("Arial", 10) # Fallback font
        # if OLED_RENDERER_AVAILABLE:
        #     try:
                # Try to load a taller font for better readability on the small display
        #         font_to_use = oled_renderer.load_font(prefer_custom=True, size_px=max(10, self.oled_height - 12))
        #         if font_to_use:
        #             self.font = font_to_use
        #     except Exception as e:
        #         print(f"OLEDDisplayManager: Error loading font via oled_renderer: {e}. Using default.")
        
        # print(f"OLEDDisplayManager: Initialized. Font: {self.font.family()}, Size: {self.font.pointSize()}pt / {self.font.pixelSize()}px")


    # oled_width and oled_height can still be useful if oled_renderer isn't available
        self.oled_width = 128 
        self.oled_height = 64
        if OLED_RENDERER_AVAILABLE: # Use constants from renderer if available
            self.oled_width = oled_renderer.OLED_WIDTH
            self.oled_height = oled_renderer.OLED_HEIGHT
        
        # print(f"OLEDDisplayManager: Initialized.") # Simplified print

    def _render_text_to_bitmap(self, text_to_render: str | None) -> bytearray | None:
        if not OLED_RENDERER_AVAILABLE: return None # Guard clause
        if text_to_render is None: text_to_render = "" 
        
        try:
            # from oled_utils import oled_renderer # Already imported or handled by OLED_RENDERER_AVAILABLE
            
            offset_to_pass = self.current_scroll_offset if self.is_scrolling_active and self.text_width_pixels > self.oled_width else 0
            center_text = not (self.is_scrolling_active and self.text_width_pixels > self.oled_width)
            
            # --- CHANGE FUNCTION CALL AND PARAMETERS ---
            packed_data = oled_renderer.render_text_to_packed_buffer(
                text=text_to_render,
                # font_override is None, so oled_renderer's internal _FONT_OBJECT will be used
                font_override=None, 
                offset_x=offset_to_pass,
                center_if_not_scrolling=center_text
            )
            # --- END CHANGE ---
            return packed_data
        except Exception as e:
            print(f"OLEDDisplayManager Error: Rendering text '{text_to_render}': {e}")
            # import traceback # Uncomment for full traceback during debugging
            # traceback.print_exc()
            return None

    def _update_display(self, text_to_show: str | None):
        self.current_display_text = text_to_show
        bitmap = self._render_text_to_bitmap(text_to_show)
        if bitmap:
            self.request_send_bitmap_to_fire.emit(bitmap)
        # else: # Optional: send blank if render failed
            # self.clear_display_content() # Or some error message bitmap

    def _needs_scrolling(self, text: str | None) -> bool:
        if not OLED_RENDERER_AVAILABLE: return False # Guard clause
        if not text: 
            self.text_width_pixels = 0
            return False
        try:
            # from oled_utils import oled_renderer # Already imported or handled
            
            # --- CHANGE FUNCTION CALL ---
            # self.font attribute is removed, oled_renderer uses its internal font
            self.text_width_pixels = oled_renderer.get_text_actual_width(text) 
            # --- END CHANGE ---
            return self.text_width_pixels > self.oled_width
        except Exception as e:
            print(f"OLEDDisplayManager Error: Calculating text width for '{text}': {e}")
            self.text_width_pixels = len(text) * 6 
            return self.text_width_pixels > self.oled_width

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
            self.scroll_timer.start(self.DEFAULT_SCROLL_DELAY_MS)
            # print(f"OLED Mgr: Started scrolling '{text}' from offset {self.current_scroll_offset}")
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
            self.scroll_timer.setInterval(self.DEFAULT_SCROLL_DELAY_MS)
        
        self._update_display(self.current_display_text)



    def stop_scrolling(self):
        self.scroll_timer.stop()
        self.is_scrolling_active = False
        # Do not reset current_scroll_offset here if we want temporary static text to not jump
        # self.text_width_pixels = 0 # Keep text_width_pixels if current_display_text is still valid

    def set_display_text(self, text: str | None, scroll_if_needed: bool = True, temporary_duration_ms: int = 0):
        # ... (handle is_knob_feedback_active as before) ...
        
        self.normal_display_text = text 
        text_to_actually_show = self.persistent_override_text if self.persistent_override_text is not None else self.normal_display_text
        
        if text_to_actually_show is None or text_to_actually_show.strip() == "":
             text_to_actually_show = " "

        # --- ADD CHECK TO PREVENT REDUNDANT SCROLL START ---
        if self.current_display_text == text_to_actually_show and \
           ((self.is_scrolling_active and self._needs_scrolling(text_to_actually_show)) or \
            (not self.is_scrolling_active and not self._needs_scrolling(text_to_actually_show))):
            # print(f"OLED Mgr: set_display_text - Text '{text_to_actually_show}' is already active with correct scroll state. No change.")
            if temporary_duration_ms > 0: # Still honor temporary duration for existing display
                QTimer.singleShot(temporary_duration_ms, self._revert_from_temporary_text)
            return 
        # --- END ADD CHECK ---

        self.stop_scrolling() # Now, only stop if we are actually changing text/scroll state

        if scroll_if_needed:
            self._start_scrolling_if_needed(text_to_actually_show)
        else:
            self._update_display(text_to_actually_show) # Render static

        if temporary_duration_ms > 0:
            QTimer.singleShot(temporary_duration_ms, self._revert_from_temporary_text)

    def set_persistent_override(self, text: str | None, scroll_if_needed: bool = True):
        # ... (handle is_knob_feedback_active as before) ...
        self.persistent_override_text = text
        text_to_show = self.persistent_override_text
        if text_to_show is None: 
            text_to_show = self.normal_display_text if self.normal_display_text is not None else " "
        
        # --- ADD CHECK TO PREVENT REDUNDANT SCROLL START ---
        if self.current_display_text == text_to_show and \
           ((self.is_scrolling_active and self._needs_scrolling(text_to_show)) or \
            (not self.is_scrolling_active and not self._needs_scrolling(text_to_show))):
            # print(f"OLED Mgr: set_persistent_override - Text '{text_to_show}' is already active with correct scroll state. No change.")
            return
        # --- END ADD CHECK ---

        self.stop_scrolling() # Now, only stop if we are actually changing text/scroll state

        if scroll_if_needed: self._start_scrolling_if_needed(text_to_show)
        else: self._update_display(text_to_show)
        
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

    def set_persistent_override(self, text: str | None, scroll_if_needed: bool = True):
        # print(f"OLED Mgr: set_persistent_override('{text}') called.")
        self.is_knob_feedback_active = False # Persistent override takes precedence
        self.stop_scrolling()
        self.persistent_override_text = text

        text_to_show = self.persistent_override_text
        if text_to_show is None: # Clearing persistent override
            text_to_show = self.normal_display_text if self.normal_display_text is not None else " "
        
        if scroll_if_needed: self._start_scrolling_if_needed(text_to_show)
        else: self._update_display(text_to_show)

    def clear_persistent_override(self):
        self.set_persistent_override(None, scroll_if_needed=True)

    # --- METHODS FOR KNOB FEEDBACK ---
    def show_temporary_knob_value(self, text: str):
        # print(f"OLED Mgr: show_temporary_knob_value with '{text}'")
        if self.is_startup_animation_playing: return # Don't interfere with startup animation

        self.is_knob_feedback_active = True 
        self.stop_scrolling() 
        self._update_display(text) 

    def get_current_intended_display_text(self) -> str | None:
        """Returns what should be displayed if knob feedback or startup animation wasn't active."""
        if self.is_startup_animation_playing:
            return None # Or a placeholder like "Starting..." if needed
        if self.persistent_override_text is not None:
            return self.persistent_override_text
        return self.normal_display_text

    def revert_after_knob_feedback(self):
        """
        Called by MainWindow's timer to restore display after knob feedback.
        It retrieves what *should* be displayed and re-applies it.
        """
        # print("OLED Mgr: revert_after_knob_feedback called.")
        if self.is_startup_animation_playing: return # Don't revert if startup is still going

        self.is_knob_feedback_active = False
        text_to_restore = self.get_current_intended_display_text()
        
        if text_to_restore is None or text_to_restore.strip() == "":
            text_to_restore = " " # Default to blank if nothing else intended

        # print(f"OLED Mgr: Reverting to: '{text_to_restore}'")
        
        self.stop_scrolling() # Stop current (knob feedback) display
        # Now, set the display text, allowing it to scroll if needed.
        # This will correctly use persistent_override_text if it's set, or normal_display_text.
        if self.persistent_override_text is not None and text_to_restore == self.persistent_override_text:
            self.set_persistent_override(text_to_restore, scroll_if_needed=True)
        else:
            self.set_display_text(text_to_restore, scroll_if_needed=True)

    # --- END METHODS FOR KNOB FEEDBACK ---

    def play_startup_animation(self, frames_data: list[bytearray], frame_duration_ms: int):
        if not frames_data: 
            self.startup_animation_finished.emit()
            return
        if self.is_startup_animation_playing: return # Already playing

        print("OLED Mgr: play_startup_animation called.")
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
            # print("OLED Mgr: Startup animation finished or stopped.")
            self.is_startup_animation_playing = False
            self._animation_frames.clear() # Clear frames
            self.startup_animation_finished.emit()
            # After animation, restore intended display
            # self.revert_after_knob_feedback() # This will pick up normal/persistent text
            # More direct:
            text_to_show_after_anim = self.get_current_intended_display_text()
            self.set_display_text(text_to_show_after_anim, scroll_if_needed=True)
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