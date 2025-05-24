### START OF FILE oled_renderer.py ###
# AKAI_Fire_RGB_Controller/oled_utils/oled_renderer.py
import os
from PIL import Image, ImageDraw, ImageFont
import sys
import random # For animation
import math   # For pulse/grid calculations

OLED_WIDTH = 128
OLED_HEIGHT = 64
PACKED_BITMAP_SIZE_BYTES = 1176 

A_BIT_MUTATE = [
    [13, 19, 25, 31, 37, 43, 49], [0,  20, 26, 32, 38, 44, 50], [1,  7,  27, 33, 39, 45, 51],
    [2,  8,  14, 34, 40, 46, 52], [3,  9,  15, 21, 41, 47, 53], [4,  10, 16, 22, 28, 48, 54],
    [5,  11, 17, 23, 29, 35, 55], [6,  12, 18, 24, 30, 36, 42]
]

_FONT_OBJECT: ImageFont.FreeTypeFont | ImageFont.ImageFont | None = None # Type hint
CUSTOM_FONT_FILENAME = "TomThumb.ttf" 
_PRIMARY_FONT_OBJECT = None # This would be your TomThumb
_SECONDARY_TEXT_FONT_OBJECT = None # For ASCII art
DEFAULT_SECONDARY_FONT_SIZE_PX = 10 # Or whatever looks good


# --- ADJUSTED FONT SIZING ---
# If TomThumb.ttf is a pixel font designed for a specific height (e.g., to fill OLED height with one char):
CUSTOM_FONT_TARGET_HEIGHT_PX = 50 # Example: if TomThumb is designed to be ~50px tall at "size 50"
# For general purpose text, a smaller size is better for readability of multiple characters
DEFAULT_TEXT_FONT_SIZE_PX = 12 # For system fallback or general use text
# --- END ADJUSTED FONT SIZING ---
try:
    # Try common system monospaced fonts
    font_name_fallbacks = ["Consolas", "Menlo", "DejaVu Sans Mono", "Liberation Mono"]
    # ... (logic to find and load one of these into _SECONDARY_TEXT_FONT_OBJECT
    #      at DEFAULT_SECONDARY_FONT_SIZE_PX) ...
    if not _SECONDARY_TEXT_FONT_OBJECT:
         _SECONDARY_TEXT_FONT_OBJECT = ImageFont.load_default() # Ultimate fallback
except Exception as e:
    print(f"WARNING (oled_renderer): Could not load secondary text font: {e}")
    _SECONDARY_TEXT_FONT_OBJECT = ImageFont.load_default()
    
try:
    # Ensure utils.get_resource_path is available
    # This assumes oled_renderer.py is in oled_utils, and utils.py is at the project root.
    # Adjust path if necessary: from ..utils import get_resource_path as resource_path_func
    try:
        from utils import get_resource_path as resource_path_func
    except ImportError: # Fallback if running script directly from oled_utils for testing
        sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
        from utils import get_resource_path as resource_path_func

    font_path = resource_path_func(os.path.join("resources", "fonts", CUSTOM_FONT_FILENAME))
    if os.path.exists(font_path):
        # For pixel fonts like TomThumb, the 'size' parameter might directly map to pixel height.
        # If TomThumb at size 64 was your intention for large text, use that.
        # For now, let's use CUSTOM_FONT_TARGET_HEIGHT_PX if it's TomThumb.
        _FONT_OBJECT = ImageFont.truetype(font_path, CUSTOM_FONT_TARGET_HEIGHT_PX)
        print(f"INFO (oled_renderer): Loaded custom font '{CUSTOM_FONT_FILENAME}' target height ~{CUSTOM_FONT_TARGET_HEIGHT_PX}px")
    else:
        # This path means get_resource_path worked, but the file wasn't there.
        print(f"WARNING (oled_renderer): Custom font file '{CUSTOM_FONT_FILENAME}' not found at '{font_path}'.")
        raise IOError(f"Custom font file not found") # Trigger fallback

except (ImportError, IOError, OSError) as e: # Added OSError for broader font loading issues
    print(f"WARNING (oled_renderer): Custom font '{CUSTOM_FONT_FILENAME}' not loaded ({e}). Falling back.")
    try:
        # Try common system monospaced fonts
        font_name_fallbacks = ["Consolas", "Menlo", "DejaVu Sans Mono", "Liberation Mono"]
        if sys.platform == "darwin": font_name_fallbacks = ["Menlo", "Monaco"] + font_name_fallbacks
        elif "linux" in sys.platform: font_name_fallbacks = ["DejaVu Sans Mono", "Liberation Mono"] + font_name_fallbacks
        
        font_loaded = False
        for fname in font_name_fallbacks:
            try:
                _FONT_OBJECT = ImageFont.truetype(fname, DEFAULT_TEXT_FONT_SIZE_PX)
                print(f"INFO (oled_renderer): Loaded system font '{fname}' size {DEFAULT_TEXT_FONT_SIZE_PX}px as fallback.")
                font_loaded = True
                break
            except IOError:
                continue
        if not font_loaded:
            _FONT_OBJECT = ImageFont.load_default() # Final fallback
            print("WARNING (oled_renderer): Using Pillow load_default() font as ultimate fallback.")
    except Exception as e_fallback:
        _FONT_OBJECT = ImageFont.load_default()
        print(f"CRITICAL (oled_renderer): Error loading system fallback font ({e_fallback}). Using Pillow load_default().")

# --- PUBLIC API for OLED Rendering ---



def show_temporary_knob_value(self, text: str, use_status_font: bool = False):
    if self.is_startup_animation_playing: return
    self.is_knob_feedback_active = True 
    self.stop_scrolling()
    
    font_to_use = self.ascii_status_font if use_status_font else self.primary_font # Or just self.font if it's unified
    
    # Call _render_text_to_bitmap, passing the chosen font
    # This means _render_text_to_bitmap needs to accept a font_override
    bitmap = self._render_text_to_bitmap(text, font_override=font_to_use)
    if bitmap:
        self.request_send_bitmap_to_fire.emit(bitmap)


def get_text_actual_width(text: str, font_to_use: ImageFont.FreeTypeFont | ImageFont.ImageFont | None = None) -> int:
    """Calculates the pixel width of a given text string using the specified font."""
    if font_to_use is None:
        font_to_use = _FONT_OBJECT
    
    if font_to_use is None or not text:
        return 0
    
    try:
        # Use textbbox to get accurate width
        # Need a dummy image to get a draw context for textbbox
        dummy_image = Image.new('1', (1, 1)) # Minimal size
        draw_context = ImageDraw.Draw(dummy_image)
        bbox = draw_context.textbbox((0, 0), text, font=font_to_use)
        return bbox[2] - bbox[0]  # width = right - left
    except Exception as e:
        print(f"ERROR (oled_renderer.get_text_actual_width): Could not get textbbox: {e}. Estimating width.")
        # Fallback crude estimation if textbbox fails (e.g., font issue)
        avg_char_width = getattr(font_to_use, 'size', DEFAULT_TEXT_FONT_SIZE_PX) * 0.6
        return int(len(text) * avg_char_width)


def render_text_to_packed_buffer(text: str, 
                                 font_override: ImageFont.FreeTypeFont | ImageFont.ImageFont | None = None, 
                                 offset_x: int = 0, 
                                 center_if_not_scrolling: bool = True) -> bytearray:
    """
    Renders text to the 7-bit packed buffer for the Akai Fire OLED.
    - text: The string to render.
    - font_override: Optional PIL ImageFont object to use. Defaults to internally loaded font.
    - offset_x: Horizontal scroll offset (negative for scrolling left).
    - center_if_not_scrolling: If True and offset_x is 0, text will be horizontally centered.
    """
    actual_font = font_override if font_override is not None else _FONT_OBJECT
    if actual_font is None:
        print("ERROR (oled_renderer.render_text_to_packed_buffer): Font object is None.")
        return get_blank_packed_bitmap()

    logical_image = Image.new('1', (OLED_WIDTH, OLED_HEIGHT), 0) # 0 = black background
    draw = ImageDraw.Draw(logical_image)
    
    text_x = -offset_x
    text_y = 0 # Default top alignment

    try:
        # Calculate text dimensions using textbbox for accurate positioning
        # Parameters for textbbox: xy, text, font. xy is the top-left anchor.
        bbox = draw.textbbox((0,0), text, font=actual_font) # (left, top, right, bottom)
        text_pixel_width = bbox[2] - bbox[0]
        text_pixel_height = bbox[3] - bbox[1] # Actual height of the glyphs
        
        # Vertical centering
        if text_pixel_height < OLED_HEIGHT:
            text_y = (OLED_HEIGHT - text_pixel_height) // 2 - bbox[1] # Adjust by bbox[1] (top offset of glyph)
        else:
            text_y = -bbox[1] # Align top of glyphs with top of screen if text is tall

        # Horizontal centering (if not scrolling and requested)
        if center_if_not_scrolling and offset_x == 0:
            if text_pixel_width < OLED_WIDTH:
                text_x = (OLED_WIDTH - text_pixel_width) // 2 - bbox[0] # Adjust by bbox[0] (left offset of glyph)
            else:
                text_x = -bbox[0] # Align left of glyphs with left of screen if text is wide
        else: # Scrolling or left-aligning
            text_x = -offset_x - bbox[0]

    except AttributeError: # Fallback if font object doesn't have getbbox (e.g. older PIL, basic font)
        print("WARNING (oled_renderer): Font object does not support 'getbbox'. Using simpler text positioning.")
        text_pixel_width = get_text_actual_width(text, actual_font) # Use our own function
        font_size_approx = getattr(actual_font, 'size', DEFAULT_TEXT_FONT_SIZE_PX) 
        text_y = (OLED_HEIGHT - font_size_approx) // 2 if font_size_approx < OLED_HEIGHT else 0
        if center_if_not_scrolling and offset_x == 0 and text_pixel_width < OLED_WIDTH:
            text_x = (OLED_WIDTH - text_pixel_width) // 2
        else:
            text_x = -offset_x

    draw.text((text_x, text_y), text, font=actual_font, fill=1) # 1 = white
    
    pixels = logical_image.load()
    def pixel_is_on(x_coord, y_coord):
        return 0 <= x_coord < OLED_WIDTH and 0 <= y_coord < OLED_HEIGHT and pixels[x_coord, y_coord] != 0
        
    return _generate_fire_packed_stream_from_logical_pixels(pixel_is_on, OLED_WIDTH, OLED_HEIGHT)


# Renamed `get_bitmap_for_text` to `render_text_to_packed_buffer` to match expected name.
# Kept a wrapper for backward compatibility if any internal part of oled_renderer still uses old name.
def get_bitmap_for_text(text: str, scroll_offset_x: int = 0, target_line_idx: int = 0) -> bytearray:
    """Wrapper for backward compatibility if needed. Prefers render_text_to_packed_buffer."""
    # target_line_idx is not directly used by the new render_text_to_packed_buffer's primary logic.
    # For single line text, it's effectively 0.
    # If multi-line was intended, render_text_to_packed_buffer would need changes.
    # print("WARNING (oled_renderer): get_bitmap_for_text is deprecated, use render_text_to_packed_buffer.")
    return render_text_to_packed_buffer(text, offset_x=scroll_offset_x, center_if_not_scrolling=(scroll_offset_x==0))


def get_blank_packed_bitmap() -> bytearray:
    return bytearray(PACKED_BITMAP_SIZE_BYTES)


def _generate_fire_packed_stream_from_logical_pixels(pixel_accessor_func, width, height) -> bytearray:
    packed_7bit_stream = bytearray(PACKED_BITMAP_SIZE_BYTES)
    for logical_y in range(height):
        for logical_x in range(width):
            if pixel_accessor_func(logical_x, logical_y): 
                fire_global_col_idx = logical_x + width * (logical_y // 8)
                fire_y_in_page = logical_y % 8
                k = A_BIT_MUTATE[fire_y_in_page][fire_global_col_idx % 7]
                packed_group_offset = (fire_global_col_idx // 7) * 8
                target_byte_offset_in_group = k // 7
                target_bit_in_packed_byte = k % 7
                packed_stream_idx = packed_group_offset + target_byte_offset_in_group
                if 0 <= packed_stream_idx < PACKED_BITMAP_SIZE_BYTES:
                    packed_7bit_stream[packed_stream_idx] |= (1 << target_bit_in_packed_byte)
    return packed_7bit_stream

def generate_fire_startup_animation(width=OLED_WIDTH, height=OLED_HEIGHT) -> list[bytearray]:
    # ... (Your existing animation logic - kept as is for brevity) ...
    all_frames_packed = []
    center_x, center_y = width // 2, height // 2
    num_pulse_frames = 8; max_pulse_radius = min(center_x, center_y) - 2
    for i in range(num_pulse_frames):
        logical_pixels = [[False for _ in range(width)] for _ in range(height)]; current_radius = (i + 1) * (max_pulse_radius / num_pulse_frames)
        for y_p in range(height):
            for x_p in range(width):
                dist = math.sqrt((x_p - center_x)**2 + (y_p - center_y)**2)
                if current_radius - 2 <= dist <= current_radius + 1 : logical_pixels[y_p][x_p] = True
        def pulse_pixel_on(px,py): return logical_pixels[py][px]
        all_frames_packed.append(_generate_fire_packed_stream_from_logical_pixels(pulse_pixel_on, width, height))
    all_frames_packed.append(get_blank_packed_bitmap())
    num_grid_expand_frames = 10; num_grid_lines_h, num_grid_lines_v = 3, 5
    for i in range(num_grid_expand_frames):
        logical_pixels = [[False for _ in range(width)] for _ in range(height)]; progress = (i + 1) / num_grid_expand_frames
        for x_b in range(width): logical_pixels[0][x_b] = logical_pixels[height-1][x_b] = True
        for y_b in range(height): logical_pixels[y_b][0] = logical_pixels[y_b][width-1] = True
        for line_idx in range(1, num_grid_lines_h + 1):
            line_y = int(line_idx * (height / (num_grid_lines_h + 1))); current_len_h = int(width * progress); start_x_h = center_x - current_len_h // 2
            for x_g in range(start_x_h, start_x_h + current_len_h):
                if 0 <= x_g < width: logical_pixels[line_y][x_g] = True
        for line_idx in range(1, num_grid_lines_v + 1):
            line_x = int(line_idx * (width / (num_grid_lines_v + 1))); current_len_v = int(height * progress); start_y_v = center_y - current_len_v // 2
            for y_g in range(start_y_v, start_y_v + current_len_v):
                if 0 <= y_g < height: logical_pixels[y_g][line_x] = True
        def grid_pixel_on(px,py): return logical_pixels[py][px]
        all_frames_packed.append(_generate_fire_packed_stream_from_logical_pixels(grid_pixel_on, width, height))
    if all_frames_packed:
        for _ in range(5): all_frames_packed.append(all_frames_packed[-1]) # Hold last grid
    # Fizzle/Sparkle (simplified for brevity, assuming your original logic is more complex)
    last_grid_pixels = [[False for _ in range(width)] for _ in range(height)] # Placeholder for last grid
    if all_frames_packed : # Reconstruct final grid for fizzle base
        for x_b_f in range(width): last_grid_pixels[0][x_b_f] = last_grid_pixels[height-1][x_b_f] = True
        for y_b_f in range(height): last_grid_pixels[y_b_f][0] = last_grid_pixels[y_b_f][width-1] = True
        for line_idx in range(1, num_grid_lines_h + 1):
            line_y_f = int(line_idx * (height / (num_grid_lines_h + 1)))
            for x_f in range(width): last_grid_pixels[line_y_f][x_f] = True
        for line_idx in range(1, num_grid_lines_v + 1):
            line_x_f = int(line_idx * (width / (num_grid_lines_v + 1)))
            for y_f in range(height): last_grid_pixels[y_f][line_x_f] = True

    current_fizzle_pixels = [row[:] for row in last_grid_pixels]
    num_fizzle_frames = 15; num_sparkle_frames = 10; sparkle_density_initial = 0.05
    for i in range(num_fizzle_frames + num_sparkle_frames):
        logical_pixels_fizz = [row[:] for row in current_fizzle_pixels]
        if i < num_fizzle_frames:
            on_pixels_coords = [(r, c) for r in range(height) for c in range(width) if current_fizzle_pixels[r][c]]
            fizzle_amount = int(len(on_pixels_coords) * 0.20)
            for _ in range(fizzle_amount):
                if not on_pixels_coords: break
                r_off, c_off = random.choice(on_pixels_coords); current_fizzle_pixels[r_off][c_off] = False
                logical_pixels_fizz[r_off][c_off] = False; on_pixels_coords.remove((r_off, c_off))
        current_sparkle_density = sparkle_density_initial * ((num_fizzle_frames + num_sparkle_frames - i) / (num_fizzle_frames + num_sparkle_frames))
        if i >= num_fizzle_frames // 3:
            for r_s in range(height):
                for c_s in range(width):
                    if random.random() < current_sparkle_density: logical_pixels_fizz[r_s][c_s] = not logical_pixels_fizz[r_s][c_s]
        def fizz_pixel_on(px,py): return logical_pixels_fizz[py][px]
        all_frames_packed.append(_generate_fire_packed_stream_from_logical_pixels(fizz_pixel_on, width, height))
    all_frames_packed.append(get_blank_packed_bitmap())
    print(f"INFO (oled_renderer): Generated {len(all_frames_packed)} frames for new startup animation.")
    return all_frames_packed


def _unpack_fire_7bit_stream_to_logical_image(packed_stream: bytearray, width: int, height: int) -> Image.Image:
    logical_image = Image.new('1', (width, height), 0); pixels = logical_image.load()
    for logical_y in range(height):
        for logical_x in range(width):
            fire_global_col_idx = logical_x + width * (logical_y // 8); fire_y_in_page = logical_y % 8
            k = A_BIT_MUTATE[fire_y_in_page][fire_global_col_idx % 7]
            packed_group_offset = (fire_global_col_idx // 7) * 8
            target_byte_offset_in_group = k // 7; target_bit_in_packed_byte = k % 7
            packed_stream_idx = packed_group_offset + target_byte_offset_in_group
            if 0 <= packed_stream_idx < len(packed_stream) and (packed_stream[packed_stream_idx] >> target_bit_in_packed_byte) & 1:
                pixels[logical_x, logical_y] = 1
    return logical_image

if __name__ == '__main__':
    # ... (Your existing __main__ test block, make sure it uses the new function names if needed) ...
    print(f"Font: {_FONT_OBJECT.font.family if _FONT_OBJECT and hasattr(_FONT_OBJECT, 'font') else 'None'}, Size: {_FONT_OBJECT.size if _FONT_OBJECT else 'N/A'}")
    
    animation_frames = generate_fire_startup_animation(OLED_WIDTH, OLED_HEIGHT)
    # ... (rest of your test saving previews) ...
    
    # Test new text rendering function
    text_frame_new = render_text_to_packed_buffer("Test New", offset_x=10, center_if_not_scrolling=False)
    if text_frame_new:
        img_vis_text_new = _unpack_fire_7bit_stream_to_logical_image(text_frame_new, OLED_WIDTH, OLED_HEIGHT)
        img_vis_text_new.save("oled_text_preview_new_render.png")
        print(f"Saved 'oled_text_preview_new_render.png'")

    text_frame_centered = render_text_to_packed_buffer("Centered", center_if_not_scrolling=True)
    if text_frame_centered:
        img_vis_text_centered = _unpack_fire_7bit_stream_to_logical_image(text_frame_centered, OLED_WIDTH, OLED_HEIGHT)
        img_vis_text_centered.save("oled_text_preview_centered.png")
        print(f"Saved 'oled_text_preview_centered.png'")

    width_test = get_text_actual_width("Test Width")
    print(f"Calculated width for 'Test Width': {width_test} pixels")