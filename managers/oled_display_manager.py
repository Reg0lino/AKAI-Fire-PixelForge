# AKAI_Fire_RGB_Controller/managers/oled_display_manager.py
from PyQt6.QtCore import QObject, pyqtSignal, QTimer, Qt 
from oled_utils import oled_renderer 

OLED_WIDTH_PIXELS = 128 
SCROLL_TIMER_INTERVAL_MS = 50 
SCROLL_PIXELS_PER_UPDATE = 2  

class OLEDDisplayManager(QObject):
    request_send_bitmap_to_fire = pyqtSignal(bytearray)
    startup_animation_finished = pyqtSignal()

    def __init__(self, akai_fire_controller_ref, parent=None):
        super().__init__(parent)
        
        # --- Normal Text State (sequence names, default welcome) ---
        self.normal_display_text = "" # This stores the intended "background" text
        self.default_scrolling_text = "READY" 
        self.is_displaying_default_normal_text = False # True if normal_display_text is the default
        
        self.scroll_timer = QTimer(self)
        self.scroll_timer.timeout.connect(self._update_scroll_and_render)
        
        self.current_scroll_offset_x = 0
        self.current_text_pixel_width = 0 # Width of the text currently being scrolled/displayed
        self._is_scrolling = False
        self._active_rendered_text_content = "" # Tracks what was last sent to render to avoid re-renders

        # --- Persistent Override State (for sampler active, etc.) ---
        self._persistent_override_text: str | None = None
        self._is_override_scrolling = False
        self._override_text_pixel_width = 0
        # self.override_scroll_offset_x = 0 # If override text needs independent scrolling (future)

        # --- Startup Animation State ---
        self._startup_animation_timer = QTimer(self)
        self._startup_animation_timer.timeout.connect(self._update_startup_animation_frame)
        self._startup_frames_list = []
        self._current_startup_frame_idx = 0
        self._is_playing_startup_animation = False
        
        self.get_text_width_func = lambda text_str: len(text_str) * (oled_renderer.DESIRED_FONT_SIZE // 2 if hasattr(oled_renderer, 'DESIRED_FONT_SIZE') else 32)
        if hasattr(oled_renderer, '_FONT_OBJECT') and oled_renderer._FONT_OBJECT:
            font_obj = oled_renderer._FONT_OBJECT
            if hasattr(font_obj, 'getlength'): self.get_text_width_func = font_obj.getlength
            elif hasattr(font_obj, 'getsize'): self.get_text_width_func = lambda s: font_obj.getsize(s)[0]

    # --- Public Methods for Controlling Display ---

    def set_display_text(self, text: str | None, scroll_if_needed: bool = True):
        """
        Sets the "normal" underlying display text (e.g., sequence name or default welcome).
        This will be shown if no persistent override is active.
        """
        if self._is_playing_startup_animation: return

        effective_normal_text = text if text is not None and text.strip() else self.default_scrolling_text
        if not effective_normal_text.strip(): effective_normal_text = " " # Ensure not truly empty

        self.is_displaying_default_normal_text = (effective_normal_text == self.default_scrolling_text)
        
        # Only update and re-evaluate if the normal text actually changes
        if self.normal_display_text == effective_normal_text:
            # If persistent override is active, don't re-render normal text unnecessarily
            if self._persistent_override_text is None:
                 self._trigger_render_with_current_state(scroll_if_needed)
            return

        self.normal_display_text = effective_normal_text
        
        # If there's no persistent override, this new normal text should be displayed.
        if self._persistent_override_text is None:
            self._trigger_render_with_current_state(scroll_if_needed)

    def set_persistent_override(self, text: str | None, scroll_if_needed: bool = True):
        """
        Sets a persistent message that overrides the normal display text.
        Pass None to clear the override.
        """
        if self._is_playing_startup_animation: return

        if text is None or not text.strip():
            self.clear_persistent_override() # Handles clearing and reverting
            return

        self._persistent_override_text = text
        # print(f"OLEDMan TRACE: Persistent override SET to: '{text}'") # Optional
        self._trigger_render_with_current_state(scroll_if_needed)

    def clear_persistent_override(self):
        """Clears any persistent override message and reverts to normal display text."""
        if self._persistent_override_text is None and not self._is_playing_startup_animation: # No override to clear
             # Ensure normal text is still rendered if it was the active one
             self._trigger_render_with_current_state(True) # Assume normal text might need scroll
             return

        # print("OLEDMan TRACE: Persistent override CLEARED.") # Optional
        self._persistent_override_text = None
        self._is_playing_startup_animation = False # Ensure this is false if we are clearing override
        self._trigger_render_with_current_state(True) # Re-render with normal text, allow scroll

    def _trigger_render_with_current_state(self, scroll_if_needed: bool = True):
        """
        Internal method to determine what text to show (override or normal)
        and then set up scrolling and initiate rendering.
        """
        self._stop_scrolling_timer()

        text_to_display = ""
        is_this_text_override = False

        if self._persistent_override_text is not None:
            text_to_display = self._persistent_override_text
            is_this_text_override = True
        else:
            text_to_display = self.normal_display_text
        
        if not text_to_display.strip(): # Should not happen if defaults are set
            text_to_display = " " 
        
        # Prevent re-render of exact same static text or restarting identical scroll
        if self._active_rendered_text_content == text_to_display and \
           self._is_scrolling == (scroll_if_needed and self.get_text_width_func(text_to_display) > OLED_WIDTH_PIXELS):
            # print(f"OLEDMan TRACE: _trigger_render - text '{text_to_display}' already active with same scroll state.") # Optional
            # Still need to ensure timer is running if it's supposed to be scrolling
            if self._is_scrolling and not self.scroll_timer.isActive():
                self.scroll_timer.start(SCROLL_TIMER_INTERVAL_MS)
            return

        self._active_rendered_text_content = text_to_display
        self.current_text_pixel_width = self.get_text_width_func(text_to_display)

        if scroll_if_needed and self.current_text_pixel_width > OLED_WIDTH_PIXELS:
            self._is_scrolling = True
            # If it's a new text or override, reset scroll. If it's the same text that just
            # stopped being overridden, its scroll position might need to be preserved (more complex).
            # For now, always reset scroll when text content source changes.
            self.current_scroll_offset_x = 0 
            if not self.scroll_timer.isActive():
                self.scroll_timer.start(SCROLL_TIMER_INTERVAL_MS)
        else:
            self._is_scrolling = False
            self.current_scroll_offset_x = 0
        
        self._render_actual_text(text_to_display, self.current_scroll_offset_x)


    def _stop_scrolling_timer(self):
        if self.scroll_timer.isActive():
            self.scroll_timer.stop()

    def _update_scroll_and_render(self):
        """Called by the scroll_timer for continuous scrolling."""
        if self._is_playing_startup_animation: self._stop_scrolling_timer(); return
        
        text_to_scroll = self._persistent_override_text if self._persistent_override_text is not None else self.normal_display_text
        
        if not self._is_scrolling or not text_to_scroll.strip():
            self._stop_scrolling_timer()
            return

        self.current_scroll_offset_x += SCROLL_PIXELS_PER_UPDATE 
        
        # Use self.current_text_pixel_width which was set based on the text_to_scroll
        if self.current_scroll_offset_x > self.current_text_pixel_width :
             self.current_scroll_offset_x = -OLED_WIDTH_PIXELS + \
                (self.current_scroll_offset_x - self.current_text_pixel_width) % SCROLL_PIXELS_PER_UPDATE
        
        self._render_actual_text(text_to_scroll, self.current_scroll_offset_x)
        
    def _render_actual_text(self, text_content: str, scroll_offset: int):
        """Shared rendering call used by scrolling and static display updates."""
        if self._is_playing_startup_animation: return
        try:
            packed_bitmap = oled_renderer.get_bitmap_for_text(
                text_content, 
                scroll_offset_x=scroll_offset, 
                target_line_idx=0 
            )
            self.request_send_bitmap_to_fire.emit(packed_bitmap)
        except Exception as e:
            print(f"OLEDMan ERROR: Error in _render_actual_text: {e}")

    def clear_display_content(self): 
        if self._is_playing_startup_animation: return
        # print("OLEDMan TRACE: clear_display_content called - clearing all text states and OLED.") # Optional
        self._stop_scrolling_timer()
        self._persistent_override_text = None # Clear override
        self.normal_display_text = ""      # Clear normal text
        self._active_rendered_text_content = "" 
        self._is_scrolling = False
        self.is_displaying_default_normal_text = False 
        try:
            self.request_send_bitmap_to_fire.emit(oled_renderer.get_blank_packed_bitmap())
        except Exception as e:
            print(f"OLEDMan ERROR: Error sending blank bitmap on clear_display_content: {e}")

    def set_default_scrolling_text_after_startup(self, text: str):
        self.default_scrolling_text = text if text and text.strip() else "READY"
        # print(f"OLEDMan INFO: Default text set to: '{self.default_scrolling_text}'") # Optional
        if not self._persistent_override_text: # Only apply if no override is active
            # print("OLEDMan INFO: Applying new default text to display immediately (no override).") # Optional
            self.set_display_text(self.default_scrolling_text, scroll_if_needed=True)

    # --- Startup Animation Methods ---
    def play_startup_animation(self, frames_data: list, frame_duration_ms: int = 80):
        if self._is_playing_startup_animation: return 
        if not frames_data: self.startup_animation_finished.emit(); return

        self._stop_scrolling_timer() 
        self.clear_persistent_override() # Ensure no override during startup animation
        self.normal_display_text = ""    # Clear normal text during startup
        self._active_rendered_text_content = "" # Clear what was last rendered

        self._is_playing_startup_animation = True
        self._startup_frames_list = frames_data
        self._current_startup_frame_idx = 0
        
        self._startup_animation_timer.setTimerType(Qt.TimerType.PreciseTimer)
        self._startup_animation_timer.start(frame_duration_ms)
        self._update_startup_animation_frame()

    def _update_startup_animation_frame(self):
        if not self._is_playing_startup_animation or \
           self._current_startup_frame_idx >= len(self._startup_frames_list):
            if self._startup_animation_timer.isActive(): self._startup_animation_timer.stop()
            self._is_playing_startup_animation = False 
            self.startup_animation_finished.emit() 
            return

        packed_bitmap_frame = self._startup_frames_list[self._current_startup_frame_idx]
        if isinstance(packed_bitmap_frame, bytearray):
            self.request_send_bitmap_to_fire.emit(packed_bitmap_frame)
        else:
            self.request_send_bitmap_to_fire.emit(oled_renderer.get_blank_packed_bitmap())
        self._current_startup_frame_idx += 1

    def stop_all_activity(self):
        self._stop_scrolling_timer()
        if self._startup_animation_timer.isActive():
            self._startup_animation_timer.stop()
        self._is_playing_startup_animation = False
        # No temporary message timer to stop in this version.