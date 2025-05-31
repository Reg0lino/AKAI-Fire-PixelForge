# AKAI_Fire_RGB_Controller/oled_utils/oled_renderer.py
import os
from PIL import Image, ImageDraw, ImageFont
import sys
import random
import math

OLED_WIDTH = 128
OLED_HEIGHT = 64
PACKED_BITMAP_SIZE_BYTES = 1176
A_BIT_MUTATE = [
    [13, 19, 25, 31, 37, 43, 49], [0,  20, 26, 32,
                                   38, 44, 50], [1,  7,  27, 33, 39, 45, 51],
    [2,  8,  14, 34, 40, 46, 52], [3,  9,  15, 21,
                                   41, 47, 53], [4,  10, 16, 22, 28, 48, 54],
    [5,  11, 17, 23, 29, 35, 55], [6,  12, 18, 24, 30, 36, 42]
]
_FONT_OBJECT: ImageFont.FreeTypeFont | ImageFont.ImageFont | None = None
CUSTOM_FONT_FILENAME = "TomThumb.ttf"
_PRIMARY_FONT_OBJECT = None
_SECONDARY_TEXT_FONT_OBJECT = None
DEFAULT_SECONDARY_FONT_SIZE_PX = 10
CUSTOM_FONT_TARGET_HEIGHT_PX = 50
DEFAULT_TEXT_FONT_SIZE_PX = 12

# --- Simplified import for get_resource_path ---
try:
    from utils import get_resource_path as resource_path_func
    print(f"DEBUG (oled_renderer.py): Successfully imported get_resource_path from utils.")
except ImportError as e_utils:
    print(f"ERROR (oled_renderer.py): Could not import get_resource_path from utils: {e_utils}")
    print(f"  Current sys.path for oled_renderer: {sys.path}")
    print(f"  Location of oled_renderer.py: {__file__}")
    # Fallback if direct import fails (e.g., running oled_renderer.py standalone without project root in path)
    def resource_path_func(relative_path_from_project_root: str) -> str:
        oled_utils_dir = os.path.dirname(os.path.abspath(__file__))
        project_root_guess = os.path.dirname(oled_utils_dir)
        fallback_path = os.path.join(project_root_guess, relative_path_from_project_root)
        print(f"DEBUG (oled_renderer.py): Using FALLBACK resource_path_func. Path for '{relative_path_from_project_root}' -> '{fallback_path}'")
        return fallback_path
    print(f"WARNING (oled_renderer): Using fallback resource_path_func. This might not be reliable for all scenarios.")
# --- End simplified import ---

try:
    # Try common system monospaced fonts
    font_name_fallbacks = ["Consolas", "Menlo",
                           "DejaVu Sans Mono", "Liberation Mono"]
    if not _SECONDARY_TEXT_FONT_OBJECT:
        _SECONDARY_TEXT_FONT_OBJECT = ImageFont.load_default()
except Exception as e:
    print(f"WARNING (oled_renderer): Could not load secondary text font: {e}")
    _SECONDARY_TEXT_FONT_OBJECT = ImageFont.load_default()

try:
    # --- TomThumb Font Loading with Enhanced Debugging ---
    print(f"DEBUG (oled_renderer.py): Attempting to load TomThumb font.")
    tom_thumb_relative_path = os.path.join("resources", "fonts", CUSTOM_FONT_FILENAME)
    print(f"DEBUG (oled_renderer.py): Relative path for TomThumb: '{tom_thumb_relative_path}'")
    font_path = resource_path_func(tom_thumb_relative_path)
    print(f"DEBUG (oled_renderer.py): Path returned by resource_path_func for TomThumb: '{font_path}'")
    if os.path.exists(font_path):
        _FONT_OBJECT = ImageFont.truetype(
            font_path, CUSTOM_FONT_TARGET_HEIGHT_PX)
        print(
            f"INFO (oled_renderer): Loaded custom font '{CUSTOM_FONT_FILENAME}' @ {CUSTOM_FONT_TARGET_HEIGHT_PX}px from '{font_path}'")
    else:
        print(
            f"WARNING (oled_renderer): Custom font file '{CUSTOM_FONT_FILENAME}' NOT FOUND at resolved path: '{font_path}'.")
        raise IOError(f"Custom font file not found via resource_path_func at '{font_path}'")
    # --- End TomThumb Font Loading ---
except (IOError, OSError) as e:
    print(
        f"WARNING (oled_renderer): Custom font '{CUSTOM_FONT_FILENAME}' loading failed ({e}). Falling back to system/default.")
    try:
        font_name_fallbacks = ["Consolas", "Menlo",
                               "DejaVu Sans Mono", "Liberation Mono"]
        if sys.platform == "darwin":
            font_name_fallbacks = ["Menlo", "Monaco"] + font_name_fallbacks
        elif "linux" in sys.platform:
            font_name_fallbacks = ["DejaVu Sans Mono",
                                   "Liberation Mono"] + font_name_fallbacks
        font_loaded = False
        for fname in font_name_fallbacks:
            try:
                _FONT_OBJECT = ImageFont.truetype(
                    fname, DEFAULT_TEXT_FONT_SIZE_PX)
                print(
                    f"INFO (oled_renderer): Loaded system font '{fname}' size {DEFAULT_TEXT_FONT_SIZE_PX}px as fallback.")
                font_loaded = True
                break
            except IOError:
                continue
        if not font_loaded:
            _FONT_OBJECT = ImageFont.load_default()
            print("WARNING (oled_renderer): Using Pillow load_default() font.")
    except Exception as e_fallback:
        _FONT_OBJECT = ImageFont.load_default()
        print(
            f"CRITICAL (oled_renderer): Error loading fallback ({e_fallback}). Using Pillow default.")

# --- PUBLIC API for OLED Rendering ---
def show_temporary_knob_value(self, text: str, use_status_font: bool = False):
    if self.is_startup_animation_playing: return
    self.is_knob_feedback_active = True 
    self.stop_scrolling()
    font_to_use = self.ascii_status_font if use_status_font else self.primary_font # Or just self.font if it's unified
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
    """
    actual_font = font_override if font_override is not None else _FONT_OBJECT
    if actual_font is None:
        print("ERROR (oled_renderer.render_text_to_packed_buffer): Font object (actual_font) is None.")
        return get_blank_packed_bitmap()
    logical_image = Image.new('1', (OLED_WIDTH, OLED_HEIGHT), 0); draw = ImageDraw.Draw(logical_image)
    text_x = -offset_x; text_y = 0
    try:
        bbox = draw.textbbox((0,0), text, font=actual_font); text_pixel_width = bbox[2] - bbox[0]; text_pixel_height = bbox[3] - bbox[1]
        if text_pixel_height < OLED_HEIGHT: text_y = (OLED_HEIGHT - text_pixel_height) // 2 - bbox[1]
        else: text_y = -bbox[1]
        if center_if_not_scrolling and offset_x == 0:
            if text_pixel_width < OLED_WIDTH: text_x = (OLED_WIDTH - text_pixel_width) // 2 - bbox[0]
            else: text_x = -bbox[0]
        else: text_x = -offset_x - bbox[0]
    except AttributeError:
        text_pixel_width = get_text_actual_width(text, actual_font); font_size_approx = getattr(actual_font, 'size', DEFAULT_TEXT_FONT_SIZE_PX) 
        text_y = (OLED_HEIGHT - font_size_approx) // 2 if font_size_approx < OLED_HEIGHT else 0
        if center_if_not_scrolling and offset_x == 0 and text_pixel_width < OLED_WIDTH: text_x = (OLED_WIDTH - text_pixel_width) // 2
        else: text_x = -offset_x
    draw.text((text_x, text_y), text, font=actual_font, fill=1)
    pixels = logical_image.load()
    def pixel_is_on(x_coord, y_coord): return 0 <= x_coord < OLED_WIDTH and 0 <= y_coord < OLED_HEIGHT and pixels[x_coord, y_coord] != 0
    return _generate_fire_packed_stream_from_logical_pixels(pixel_is_on, OLED_WIDTH, OLED_HEIGHT)

def pack_pil_image_to_7bit_stream(pil_monochrome_image: Image.Image) -> bytearray | None:
    """
    Takes a pre-rendered 1-bit PIL Image and converts it to the Akai Fire's
    7-bit packed byte stream.
    """
    if pil_monochrome_image is None:
        print("ERROR (oled_renderer.pack_pil_image_to_7bit_stream): Input PIL image is None.")
        return None
    if pil_monochrome_image.mode != '1':
        print(f"WARNING (oled_renderer.pack_pil_image_to_7bit_stream): Input PIL image mode is '{pil_monochrome_image.mode}', attempting to convert to '1'.")
        try:
            pil_monochrome_image = pil_monochrome_image.convert('1')
        except Exception as e_conv:
            print(f"ERROR (oled_renderer.pack_pil_image_to_7bit_stream): Failed to convert image to '1' mode: {e_conv}")
            return None
            
    if pil_monochrome_image.width != OLED_WIDTH or pil_monochrome_image.height != OLED_HEIGHT:
        print(f"ERROR (oled_renderer.pack_pil_image_to_7bit_stream): Image dimensions ({pil_monochrome_image.width}x{pil_monochrome_image.height}) do not match OLED ({OLED_WIDTH}x{OLED_HEIGHT}).")
        # Optional: resize/crop, but for now, expect correct size
        return None

    try:
        pixels = pil_monochrome_image.load()
        def pixel_is_on(x_coord, y_coord):
            # For '1' mode, Pillow pixels are 0 (black) or 255 (white).
            # We consider non-black as 'on'.
            return pixels[x_coord, y_coord] != 0 
            
        return _generate_fire_packed_stream_from_logical_pixels(pixel_is_on, OLED_WIDTH, OLED_HEIGHT)
    except Exception as e:
        print(f"ERROR (oled_renderer.pack_pil_image_to_7bit_stream): Exception during packing: {e}")
        return None

def get_bitmap_for_text(text: str, scroll_offset_x: int = 0, target_line_idx: int = 0) -> bytearray:
    """Wrapper for backward compatibility if needed. Prefers render_text_to_packed_buffer."""
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
    print(f"Font: {_FONT_OBJECT.font.family if _FONT_OBJECT and hasattr(_FONT_OBJECT, 'font') else 'None'}, Size: {_FONT_OBJECT.size if _FONT_OBJECT else 'N/A'}")
    animation_frames = generate_fire_startup_animation(OLED_WIDTH, OLED_HEIGHT)
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