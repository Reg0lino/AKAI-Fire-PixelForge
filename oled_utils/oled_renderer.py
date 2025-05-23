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

_FONT_OBJECT = None
CUSTOM_FONT_FILENAME = "TomThumb.ttf" 
DESIRED_FONT_SIZE = 64 # As per your last update for the scrolling text

try:
    from utils import get_resource_path as resource_path_func
    font_path = resource_path_func(os.path.join("resources", "fonts", CUSTOM_FONT_FILENAME))
    if os.path.exists(font_path):
        _FONT_OBJECT = ImageFont.truetype(font_path, DESIRED_FONT_SIZE)
        # print(f"INFO (oled_renderer): Loaded custom font '{CUSTOM_FONT_FILENAME}' size {DESIRED_FONT_SIZE}")
    else: raise IOError(f"Custom font file '{CUSTOM_FONT_FILENAME}' not found at '{font_path}'")
except (ImportError, IOError) as e:
    print(f"WARNING (oled_renderer): Custom font '{CUSTOM_FONT_FILENAME}' not loaded ({e}). Falling back.")
    try:
        _FONT_NAME_SYSTEM_MONO = "Consolas" # Example fallback
        if sys.platform == "darwin": _FONT_NAME_SYSTEM_MONO = "Menlo"
        elif "linux" in sys.platform: _FONT_NAME_SYSTEM_MONO = "DejaVu Sans Mono"
        # Fallback size for system font if custom 64px one fails
        _FONT_OBJECT = ImageFont.truetype(_FONT_NAME_SYSTEM_MONO, DESIRED_FONT_SIZE // 4 if DESIRED_FONT_SIZE > 32 else 10) 
        # print(f"INFO (oled_renderer): Loaded system font '{_FONT_NAME_SYSTEM_MONO}'")
    except IOError:
        _FONT_OBJECT = ImageFont.load_default()
        print("WARNING (oled_renderer): Using Pillow load_default font as final fallback.")

def _generate_fire_packed_stream_from_logical_pixels(pixel_accessor_func, width, height) -> bytearray:
    """
    Core function to generate the Fire's 1176-byte packed stream
    from a logical 128x64 pixel representation.
    pixel_accessor_func(x, y) should return True if pixel (x,y) is ON, False otherwise.
    """
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

def get_bitmap_for_text(text: str, scroll_offset_x: int = 0, target_line_idx: int = 0) -> bytearray:
    if _FONT_OBJECT is None: 
        print("ERROR (oled_renderer): Font object is None in get_bitmap_for_text.")
        return get_blank_packed_bitmap()

    logical_image = Image.new('1', (OLED_WIDTH, OLED_HEIGHT), 0)
    draw = ImageDraw.Draw(logical_image)
    
    text_y = 0 
    if hasattr(_FONT_OBJECT, 'getbbox'): # More robust positioning
        try:
            # Get bounding box for text to help center it vertically for large fonts
            bbox = draw.textbbox((0,0), text, font=_FONT_OBJECT) # Left, Top, Right, Bottom
            text_height = bbox[3] - bbox[1]
            if text_height < OLED_HEIGHT: # Only adjust if text is not already full height
                 text_y = (OLED_HEIGHT - text_height) // 2 - bbox[1] 
            else: # If text is tall, try to align top
                text_y = -bbox[1]
        except Exception:
             # Fallback if bbox fails, less accurate for very large fonts
             font_size = _FONT_OBJECT.size if hasattr(_FONT_OBJECT, 'size') else DESIRED_FONT_SIZE
             text_y = (OLED_HEIGHT - font_size) // 2 if font_size < OLED_HEIGHT else 0


    draw.text((-scroll_offset_x, text_y), text, font=_FONT_OBJECT, fill=1)
    pixels = logical_image.load()
    def pixel_is_on(x, y): return 0 <= x < OLED_WIDTH and 0 <= y < OLED_HEIGHT and pixels[x, y] != 0
    return _generate_fire_packed_stream_from_logical_pixels(pixel_is_on, OLED_WIDTH, OLED_HEIGHT)

def get_blank_packed_bitmap() -> bytearray:
    return bytearray(PACKED_BITMAP_SIZE_BYTES)

def generate_fire_startup_animation(width=OLED_WIDTH, height=OLED_HEIGHT) -> list[bytearray]:
    all_frames_packed = []
    center_x, center_y = width // 2, height // 2

    # --- Stage 1: Pulse ---
    num_pulse_frames = 8
    max_pulse_radius = min(center_x, center_y) - 2 # Leave a small border
    for i in range(num_pulse_frames):
        logical_pixels = [[False for _ in range(width)] for _ in range(height)]
        current_radius = (i + 1) * (max_pulse_radius / num_pulse_frames)
        # Draw a circle/ring for the pulse
        for y in range(height):
            for x in range(width):
                dist = math.sqrt((x - center_x)**2 + (y - center_y)**2)
                # Make a ring pulse
                if current_radius - 2 <= dist <= current_radius + 1 : # Ring thickness
                    logical_pixels[y][x] = True
        def pulse_pixel_on(px,py): return logical_pixels[py][px]
        all_frames_packed.append(_generate_fire_packed_stream_from_logical_pixels(pulse_pixel_on, width, height))
    all_frames_packed.append(get_blank_packed_bitmap()) # Blank after pulse

    # --- Stage 2: Expanding Grid Lines ---
    num_grid_expand_frames = 10
    num_grid_lines_h, num_grid_lines_v = 3, 5 # e.g., 3 horizontal, 5 vertical + borders
    
    for i in range(num_grid_expand_frames):
        logical_pixels = [[False for _ in range(width)] for _ in range(height)]
        progress = (i + 1) / num_grid_expand_frames

        # Draw border lines always
        for x in range(width): logical_pixels[0][x] = logical_pixels[height-1][x] = True
        for y in range(height): logical_pixels[y][0] = logical_pixels[y][width-1] = True

        # Expanding horizontal lines
        for line_idx in range(1, num_grid_lines_h + 1):
            line_y = int(line_idx * (height / (num_grid_lines_h + 1)))
            current_len_h = int(width * progress)
            start_x_h = center_x - current_len_h // 2
            for x in range(start_x_h, start_x_h + current_len_h):
                if 0 <= x < width: logical_pixels[line_y][x] = True
        
        # Expanding vertical lines
        for line_idx in range(1, num_grid_lines_v + 1):
            line_x = int(line_idx * (width / (num_grid_lines_v + 1)))
            current_len_v = int(height * progress)
            start_y_v = center_y - current_len_v // 2
            for y in range(start_y_v, start_y_v + current_len_v):
                if 0 <= y < height: logical_pixels[y][line_x] = True
        
        def grid_pixel_on(px,py): return logical_pixels[py][px]
        all_frames_packed.append(_generate_fire_packed_stream_from_logical_pixels(grid_pixel_on, width, height))
    
    grid_hold_frames = 5
    if all_frames_packed: # Hold the last grid frame
        for _ in range(grid_hold_frames): all_frames_packed.append(all_frames_packed[-1])

    # --- Stage 3: Fizzle with Sparkles ---
    num_fizzle_frames = 15
    num_sparkle_frames = 10 # Overlap with fizzle or after
    sparkle_density_initial = 0.05 # Percentage of pixels that could be sparkles
    
    # Get the last grid frame as a logical pixel grid to fizzle from
    if all_frames_packed:
        # Need to unpack the last frame to a logical grid to modify it
        # For simplicity, let's re-render the final grid state
        final_grid_pixels = [[False for _ in range(width)] for _ in range(height)]
        for x_b in range(width): final_grid_pixels[0][x_b] = final_grid_pixels[height-1][x_b] = True # Borders
        for y_b in range(height): final_grid_pixels[y_b][0] = final_grid_pixels[y_b][width-1] = True
        for line_idx in range(1, num_grid_lines_h + 1):
            line_y = int(line_idx * (height / (num_grid_lines_h + 1)))
            for x in range(width): final_grid_pixels[line_y][x] = True
        for line_idx in range(1, num_grid_lines_v + 1):
            line_x = int(line_idx * (width / (num_grid_lines_v + 1)))
            for y in range(height): final_grid_pixels[y][line_x] = True
        
        current_fizzle_pixels = [row[:] for row in final_grid_pixels]
    else: # Should not happen if grid was generated
        current_fizzle_pixels = [[False for _ in range(width)] for _ in range(height)]


    for i in range(num_fizzle_frames + num_sparkle_frames):
        logical_pixels = [row[:] for row in current_fizzle_pixels] # Start with current fizzle state

        # Fizzle effect (mostly during first num_fizzle_frames)
        if i < num_fizzle_frames:
            fizzle_amount = int( (sum(row.count(True) for row in current_fizzle_pixels)) * 0.25 ) # Fizzle 25% of remaining
            for _ in range(fizzle_amount):
                # Naive fizzle: pick random on pixel and turn off.
                # Better: iterate and randomly turn off.
                on_pixels_coords = [(r, c) for r in range(height) for c in range(width) if current_fizzle_pixels[r][c]]
                if not on_pixels_coords: break
                r_off, c_off = random.choice(on_pixels_coords)
                current_fizzle_pixels[r_off][c_off] = False 
                logical_pixels[r_off][c_off] = False # Update current frame's base

        # Sparkle effect (mostly during last num_sparkle_frames, or throughout)
        current_sparkle_density = sparkle_density_initial * ((num_fizzle_frames + num_sparkle_frames - i) / (num_fizzle_frames + num_sparkle_frames)) # Fade out sparkles
        if i >= num_fizzle_frames // 2 : # Start sparkles midway through fizzle
             for r in range(height):
                for c in range(width):
                    if random.random() < current_sparkle_density:
                        logical_pixels[r][c] = not logical_pixels[r][c] # Toggle for sparkle effect

        def fizz_spark_pixel_on(px,py): return logical_pixels[py][px]
        all_frames_packed.append(_generate_fire_packed_stream_from_logical_pixels(fizz_spark_pixel_on, width, height))

    all_frames_packed.append(get_blank_packed_bitmap()) # Ensure it ends blank
    print(f"INFO (oled_renderer): Generated {len(all_frames_packed)} frames for new startup animation.")
    return all_frames_packed


# For local testing/visualization 
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
    
    # Test NEW startup animation generation
    animation_frames = generate_fire_startup_animation(OLED_WIDTH, OLED_HEIGHT)
    
    if animation_frames:
        # Preview a few key frames
        preview_indices = {
            "pulse_mid": 3,
            "grid_mid_expand": 8 + 4, # after pulse, mid grid expansion
            "grid_full": 8 + 10 -1, # after pulse, end of grid expansion
            "fizzle_mid_sparkle_start": 8 + 10 + 5 + (15+10)//2 - 5 , # approx
            "fizzle_late_sparkle_mid": 8 + 10 + 5 + (15+10) - 5, # approx
        }
        for name, idx in preview_indices.items():
            if 0 <= idx < len(animation_frames):
                try:
                    img_vis_anim = _unpack_fire_7bit_stream_to_logical_image(animation_frames[idx], OLED_WIDTH, OLED_HEIGHT)
                    img_vis_anim.save(f"oled_startup_{name}_preview.png")
                    print(f"Saved 'oled_startup_{name}_preview.png'")
                except IndexError:
                     print(f"Could not generate preview for '{name}' at index {idx}, list length {len(animation_frames)}")
                except Exception as e_img:
                     print(f"Error saving preview image '{name}': {e_img}")

            else:
                print(f"Index {idx} for '{name}' out of bounds (total frames: {len(animation_frames)}).")
        
        # Test text rendering (still useful)
        text_frame = get_bitmap_for_text("CTRL Ready", 0, 0)
        img_vis_text = _unpack_fire_7bit_stream_to_logical_image(text_frame, OLED_WIDTH, OLED_HEIGHT)
        img_vis_text.save("oled_text_preview.png")
        print(f"Saved 'oled_text_preview.png'")