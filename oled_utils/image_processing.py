# utils/image_processing.py
import os
from PIL import Image, ImageOps, ImageSequence, ImageFont, ImageDraw, ImageEnhance
import numpy as np # For Bayer matrix and efficient operations

TARGET_SIZE = (128, 64) # OLED dimensions

# Bayer matrix (4x4) for 16 levels of perceived grayscale
BAYER_MATRIX_4X4 = np.array([
    [ 0,  8,  2, 10],
    [12,  4, 14,  6],
    [ 3, 11,  1,  9],
    [15,  7, 13,  5]
])
NORMALIZED_BAYER_MATRIX_4X4 = BAYER_MATRIX_4X4 / 16.0

def logical_frame_to_string_list(pil_image_1bit: Image.Image) -> list[str]:
    """Converts a 128x64 1-bit PIL Image to a list of 64 strings, each 128 chars ('0' or '1')."""
    if pil_image_1bit.mode != '1' or pil_image_1bit.size != TARGET_SIZE:
        raise ValueError(f"Image must be 1-bit and {TARGET_SIZE[0]}x{TARGET_SIZE[1]} pixels.")
    
    string_list_frame = []
    pixels = pil_image_1bit.load()
    for y in range(TARGET_SIZE[1]):
        row_string = ""
        for x in range(TARGET_SIZE[0]):
            # In '1' mode, Pillow pixels are 0 (black) or 255 (white).
            # We want '1' for white (on) and '0' for black (off).
            row_string += '1' if pixels[x, y] != 0 else '0'
        string_list_frame.append(row_string)
    return string_list_frame

# In oled_utils/image_processing.py


def process_single_frame(frame: Image.Image,
                         resize_mode: str,
                         mono_conversion_mode: str,
                         threshold_value: int,
                         invert_colors: bool,
                         contrast_factor: float) -> Image.Image | None:  # <<< ADDED contrast_factor
    """Processes a single PIL Image frame to a 128x64 1-bit PIL Image, with contrast adjustment."""
    try:
        # 1. Ensure RGBA for consistent transparency handling
        if frame.mode != 'RGBA':
            frame = frame.convert("RGBA")

        # 2. Resize (Your existing resize logic)
        processed_frame = frame
        if resize_mode == "Stretch to Fit":
            processed_frame = frame.resize(
                TARGET_SIZE, Image.Resampling.LANCZOS)
        elif resize_mode == "Fit (Keep Aspect, Pad)":
            img_copy = frame.copy()
            img_copy.thumbnail(TARGET_SIZE, Image.Resampling.LANCZOS)
            processed_frame = Image.new(
                "RGBA", TARGET_SIZE, (0, 0, 0, 255))  # Black background
            paste_x = (TARGET_SIZE[0] - img_copy.width) // 2
            paste_y = (TARGET_SIZE[1] - img_copy.height) // 2
            # Ensure alpha channel is used for pasting if source has it
            processed_frame.paste(
                img_copy, (paste_x, paste_y), img_copy if img_copy.mode == 'RGBA' else None)
        elif resize_mode == "Crop to Center":
            original_width, original_height = frame.size
            target_aspect = TARGET_SIZE[0] / TARGET_SIZE[1]
            original_aspect = original_width / original_height
            if original_aspect > target_aspect:
                new_height = TARGET_SIZE[1]
                new_width = int(new_height * original_aspect)
            else:
                new_width = TARGET_SIZE[0]
                new_height = int(new_width / original_aspect)
            resized_temp = frame.resize(
                (new_width, new_height), Image.Resampling.LANCZOS)
            crop_x = (new_width - TARGET_SIZE[0]) / 2
            crop_y = (new_height - TARGET_SIZE[1]) / 2
            crop_box = (crop_x, crop_y, crop_x +
                        TARGET_SIZE[0], crop_y + TARGET_SIZE[1])
            processed_frame = resized_temp.crop(crop_box)
        else:  # Default to Stretch if unknown mode
            processed_frame = frame.resize(
                TARGET_SIZE, Image.Resampling.LANCZOS)

        # 3. Convert to Grayscale
        grayscale_frame = processed_frame.convert("L")

        # --- NEW: 3.5. Apply Contrast Adjustment ---
        # Apply contrast if factor is not 1.0 (no change)
        if contrast_factor != 1.0:
            try:
                enhancer = ImageEnhance.Contrast(grayscale_frame)
                grayscale_frame = enhancer.enhance(contrast_factor)
                # print(f"IPROC DEBUG: Applied contrast factor: {contrast_factor:.2f} to frame.") # Optional
            except Exception as e_contrast:
                print(
                    f"IPROC WARNING: Failed to apply contrast (factor: {contrast_factor:.2f}): {e_contrast}")
        # --- END NEW ---

        # 4. Invert Colors (if checked) - applied AFTER contrast, BEFORE monochrome conversion
        if invert_colors:
            grayscale_frame = ImageOps.invert(grayscale_frame)

        # 5. Monochrome Conversion (Your existing dithering logic)
        monochrome_frame: Image.Image
        if mono_conversion_mode == "Floyd-Steinberg Dither":
            monochrome_frame = grayscale_frame.convert(
                '1', dither=Image.Dither.FLOYDSTEINBERG)
        elif mono_conversion_mode == "Simple Threshold":
            monochrome_frame = grayscale_frame.point(
                lambda p: 255 if p > threshold_value else 0, '1')
        elif mono_conversion_mode == "Ordered Dither (Bayer 4x4)":
            gray_np = np.array(grayscale_frame, dtype=np.float32) / 255.0
            output_np = np.zeros_like(gray_np, dtype=np.uint8)
            bayer_rows, bayer_cols = NORMALIZED_BAYER_MATRIX_4X4.shape
            for r_idx in range(gray_np.shape[0]):
                for c_idx in range(gray_np.shape[1]):
                    if gray_np[r_idx, c_idx] > NORMALIZED_BAYER_MATRIX_4X4[r_idx % bayer_rows, c_idx % bayer_cols]:
                        output_np[r_idx, c_idx] = 255
                    # else: output_np[r_idx, c_idx] = 0 # Already initialized to 0
            monochrome_frame = Image.fromarray(
                output_np, mode='L').convert('1')
        # Add other dithering methods here as elif blocks in the future
        else:  # Default to Floyd-Steinberg
            # print(f"IPROC Warning: Unknown mono_conversion_mode '{mono_conversion_mode}', defaulting to Floyd-Steinberg.")
            monochrome_frame = grayscale_frame.convert(
                '1', dither=Image.Dither.FLOYDSTEINBERG)

        return monochrome_frame

    except Exception as e:
        print(f"Error processing single frame: {e}")
        import traceback
        traceback.print_exc()
        return None

# In oled_utils/image_processing.py


def process_image_to_oled_data(filepath: str,
                               resize_mode: str,
                               mono_conversion_mode: str,
                               threshold_value: int,
                               invert_colors: bool,
                               contrast_factor: float,        # <<< ADDED contrast_factor
                               max_frames_to_import: int = 0
                               ) -> tuple[list[list[str]] | None, float | None, int | None]:
    """
    Processes an image or GIF into a list of logical OLED frames.
    Includes contrast adjustment before monochrome conversion.

    Args:
        filepath: Path to the image or GIF.
        resize_mode: "Stretch to Fit", "Fit (Keep Aspect, Pad)", "Crop to Center".
        mono_conversion_mode: Dithering/thresholding mode.
        threshold_value: Value for simple thresholding (0-255).
        invert_colors: Boolean, whether to invert black/white.
        contrast_factor: Float, e.g., 1.0 for no change, >1 for more, <1 for less.
        max_frames_to_import: Max number of frames to process from a GIF (0 for all).

    Returns:
        A tuple: (list_of_logical_frames, source_fps, source_loop_count)
    """
    if not os.path.exists(filepath):
        print(f"IPROC Error: File not found at {filepath}")
        return None, None, None

    logical_frames_output = []
    source_fps = None
    source_loop_count = None

    try:
        img = Image.open(filepath)
        is_animated = hasattr(img, "is_animated") and img.is_animated
        num_frames = img.n_frames if is_animated else 1
        # print(f"IPROC Processing '{os.path.basename(filepath)}'. Animated: {is_animated}, Frames: {num_frames}, Contrast: {contrast_factor:.2f}") # Optional

        frames_to_process = num_frames
        if is_animated and max_frames_to_import > 0:
            frames_to_process = min(num_frames, max_frames_to_import)

        if is_animated:
            try:
                duration_ms = img.info.get('duration', 100)
                if duration_ms > 0:
                    source_fps = 1000.0 / duration_ms
                source_loop_count = img.info.get('loop', 0)
            except Exception as e_info:
                print(
                    f"IPROC Warning: Could not read GIF duration/loop: {e_info}")

        for i in range(frames_to_process):
            if is_animated:
                img.seek(i)
            current_frame_pil = img.copy()

            monochrome_pil_frame = process_single_frame(
                current_frame_pil,
                resize_mode,
                mono_conversion_mode,
                threshold_value,
                invert_colors,
                contrast_factor  # <<< PASS contrast_factor HERE
            )

            if monochrome_pil_frame:
                logical_frames_output.append(
                    logical_frame_to_string_list(monochrome_pil_frame))
            else:
                print(
                    f"IPROC Warning: Skipping frame {i} due to processing error.")

        if not logical_frames_output:
            print(
                f"IPROC Error: No frames successfully processed for '{filepath}'.")
            return None, source_fps, source_loop_count

        return logical_frames_output, source_fps, source_loop_count

    except FileNotFoundError:  # Should be caught by os.path.exists, but good defense
        print(
            f"IPROC Error: File not found at {filepath} (during Image.open).")
        return None, None, None
    except IOError as e_io:
        print(
            f"IPROC Error: PIL cannot open/read file '{filepath}'. Unsupported or corrupt? Error: {e_io}")
        return None, None, None
    except Exception as e:
        print(
            f"IPROC Error: Unexpected error processing image '{filepath}': {e}")
        import traceback
        traceback.print_exc()
        return None, None, None


if __name__ == '__main__':
    from PIL import ImageDraw, ImageFont # Add ImageDraw, ImageFont here for dummy asset creation

    print("--- Testing Image Processing Utility ---")
    
    # Define paths for your custom test files, relative to the project root
    # Assumes this script (image_processing.py) is in oled_utils, 
    # so project root is one level up.
    PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    YOUR_STATIC_IMAGE_PATH = os.path.join(PROJECT_ROOT, "my_test_image.png")
    YOUR_GIF_PATH = os.path.join(PROJECT_ROOT, "my_test_gif.gif")

    # Paths for dummy files if your files aren't found
    DUMMY_STATIC_IMAGE_PATH = os.path.join(PROJECT_ROOT, "test_static_image_generated.png")
    DUMMY_GIF_PATH = os.path.join(PROJECT_ROOT, "test_animation_generated.gif")

    def create_dummy_assets_if_needed():
        assets_actually_created = False
        # Create dummy static image if your specific one isn't found
        if not os.path.exists(YOUR_STATIC_IMAGE_PATH) and not os.path.exists(DUMMY_STATIC_IMAGE_PATH) :
            try:
                img_static = Image.new("RGB", (200, 100), "blue")
                draw_static = ImageDraw.Draw(img_static)
                try: font = ImageFont.truetype("arial.ttf", 40)
                except IOError: font = ImageFont.load_default()
                draw_static.text((10, 10), "TEST", fill="white", font=font)
                img_static.save(DUMMY_STATIC_IMAGE_PATH)
                print(f"Created dummy static image: {DUMMY_STATIC_IMAGE_PATH}")
                assets_actually_created = True
            except Exception as e:
                print(f"Could not create dummy static image: {e}")
        
        # Create dummy GIF if your specific one isn't found
        if not os.path.exists(YOUR_GIF_PATH) and not os.path.exists(DUMMY_GIF_PATH):
            try:
                frames = []
                try: font = ImageFont.truetype("arial.ttf", 20) # Smaller font for GIF frames
                except IOError: font = ImageFont.load_default()
                for i in range(10):
                    img_gif_frame = Image.new("RGB", (150, 75), (i * 20, 128, 255 - i * 20)) # More color variation
                    draw_gif = ImageDraw.Draw(img_gif_frame)
                    draw_gif.text((5,5), f"Frame {i}", fill="black", font=font)
                    frames.append(img_gif_frame)
                frames[0].save(DUMMY_GIF_PATH, save_all=True, append_images=frames[1:], duration=150, loop=0) # 150ms/frame
                print(f"Created dummy GIF: {DUMMY_GIF_PATH}")
                assets_actually_created = True
            except Exception as e:
                print(f"Could not create dummy GIF: {e}")
        return assets_actually_created

    create_dummy_assets_if_needed() # Try to create dummies if yours are missing

    test_files_to_process = []
    if os.path.exists(YOUR_STATIC_IMAGE_PATH):
        print(f"Using specified static image: {YOUR_STATIC_IMAGE_PATH}")
        test_files_to_process.append(YOUR_STATIC_IMAGE_PATH)
    elif os.path.exists(DUMMY_STATIC_IMAGE_PATH):
        print(f"Using generated dummy static image: {DUMMY_STATIC_IMAGE_PATH}")
        test_files_to_process.append(DUMMY_STATIC_IMAGE_PATH)
    else:
        print(f"Static test image not found or generated: {YOUR_STATIC_IMAGE_PATH} / {DUMMY_STATIC_IMAGE_PATH}")

    if os.path.exists(YOUR_GIF_PATH):
        print(f"Using specified GIF: {YOUR_GIF_PATH}")
        test_files_to_process.append(YOUR_GIF_PATH)
    elif os.path.exists(DUMMY_GIF_PATH):
        print(f"Using generated dummy GIF: {DUMMY_GIF_PATH}")
        test_files_to_process.append(DUMMY_GIF_PATH)
    else:
        print(f"GIF test image not found or generated: {YOUR_GIF_PATH} / {DUMMY_GIF_PATH}")
    
    if not test_files_to_process:
        print("\nNo test files to process. Please place 'my_test_image.png' and 'my_test_gif.gif' in the project root, or ensure Pillow can create dummy assets.")
    
    for test_file_path in test_files_to_process:
        print(f"\n--- Testing with: {test_file_path} ---")
        
        # Test cases (same as before)
        options_to_test = [
            {"resize": "Stretch to Fit", "mono": "Floyd-Steinberg Dither", "thresh": 128, "invert": False},
            {"resize": "Fit (Keep Aspect, Pad)", "mono": "Simple Threshold", "thresh": 100, "invert": True},
            {"resize": "Crop to Center", "mono": "Floyd-Steinberg Dither", "thresh": 128, "invert": False},
            {"resize": "Fit (Keep Aspect, Pad)", "mono": "Ordered Dither (Bayer 4x4)", "thresh": 128, "invert": False}, # New Test
            {"resize": "Stretch to Fit", "mono": "Ordered Dither (Bayer 4x4)", "thresh": 128, "invert": True},   # New Test Inverted
        ]

        for i, opts in enumerate(options_to_test):
            print(f"\n  Test Case {i+1}: Resize='{opts['resize']}', Mono='{opts['mono']}', Thresh={opts['thresh']}, Invert={opts['invert']}")
            logical_frames, fps, loop = process_image_to_oled_data(
                test_file_path, # Use the determined test_file_path
                resize_mode=opts['resize'],
                mono_conversion_mode=opts['mono'],
                threshold_value=opts['thresh'],
                invert_colors=opts['invert'],
                max_frames_to_import=5 
            )

            if logical_frames:
                print(f"    Successfully processed {len(logical_frames)} frames.")
                if fps is not None: print(f"    Source FPS (approx): {fps:.2f}", end="")
                if loop is not None: print(f", Source Loop: {loop if loop != 0 else 'Infinite'}")
                else: print() # Newline if only one of fps/loop was printed
                
                print(f"    First frame data (first 3 lines, first 32 chars):")
                for line_idx, line_str in enumerate(logical_frames[0][:3]):
                    print(f"      Line {line_idx}: {line_str[:32]}...")
                
                if logical_frames[0]:
                    try:
                        img_out = Image.new('1', TARGET_SIZE)
                        pixels_out = img_out.load()
                        for y_idx, row_str in enumerate(logical_frames[0]):
                            for x_idx, char_val in enumerate(row_str):
                                pixels_out[x_idx, y_idx] = 255 if char_val == '1' else 0
                        
                        output_filename_base = os.path.basename(test_file_path).split('.')[0]
                        # Save processed previews in the project root for easy access
                        output_filepath = os.path.join(PROJECT_ROOT, f"processed_preview_{output_filename_base}_case{i+1}.png")
                        img_out.save(output_filepath)
                        print(f"    Saved preview of first processed frame to: {output_filepath}")
                    except Exception as e_save:
                        print(f"    Could not save preview image: {e_save}")
            else:
                print("    Processing failed.")
    
    # Cleanup dummy files if they were generated and you don't want to keep them
    # (Be careful if your actual test files are named the same as dummy files)
    if os.path.exists(DUMMY_STATIC_IMAGE_PATH) and "generated" in DUMMY_STATIC_IMAGE_PATH: 
        # print(f"Cleaning up {DUMMY_STATIC_IMAGE_PATH}")
        os.remove(DUMMY_STATIC_IMAGE_PATH)
    if os.path.exists(DUMMY_GIF_PATH) and "generated" in DUMMY_GIF_PATH:
        # print(f"Cleaning up {DUMMY_GIF_PATH}")
        os.remove(DUMMY_GIF_PATH)
        
    print("\n--- Image Processing Test Finished ---")