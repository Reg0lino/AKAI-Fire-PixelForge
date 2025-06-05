# utils/image_processing.py
import os
from PIL import Image, ImageOps, ImageSequence, ImageFont, ImageDraw, ImageEnhance, ImageFilter
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

ATKINSON_DISTRIBUTION = [
    ((1, 0), 1/8), ((2, 0), 1/8),
    ((-1, 1), 1/8), ((0, 1), 1/8), ((1, 1), 1/8),
    ((0, 2), 1/8)
]

# Bayer matrix (2x2)
BAYER_MATRIX_2X2 = np.array([
    [0, 2],
    [3, 1]
])
NORMALIZED_BAYER_MATRIX_2X2 = BAYER_MATRIX_2X2 / 4.0

# Bayer matrix (8x8)
BAYER_MATRIX_8X8 = np.array([
    [0, 32,  8, 40,  2, 34, 10, 42],
    [48, 16, 56, 24, 50, 18, 58, 26],
    [12, 44,  4, 36, 14, 46,  6, 38],
    [60, 28, 52, 20, 62, 30, 54, 22],
    [3, 35, 11, 43,  1, 33,  9, 41],
    [51, 19, 59, 27, 49, 17, 57, 25],
    [15, 47,  7, 39, 13, 45,  5, 37],
    [63, 31, 55, 23, 61, 29, 53, 21]
])
NORMALIZED_BAYER_MATRIX_8X8 = BAYER_MATRIX_8X8 / 64.0

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

def _apply_atkinson_dither(grayscale_image: Image.Image, dither_strength: float = 1.0) -> Image.Image:
    """
    Applies Atkinson dithering to a grayscale PIL Image with variable strength.
    Returns a 1-bit monochrome PIL Image.
    dither_strength: 0.0 (threshold) to 1.0 (full Atkinson).
    """
    if grayscale_image.mode != 'L':
        grayscale_image = grayscale_image.convert('L')

    img_np = np.array(grayscale_image, dtype=float)
    rows, cols = img_np.shape

    for r in range(rows):
        for c in range(cols):
            old_pixel = img_np[r, c]
            new_pixel = 255.0 if old_pixel > 127.5 else 0.0
            img_np[r, c] = new_pixel
            quant_error = old_pixel - new_pixel

            # Apply dither strength to the error being distributed
            error_to_distribute = quant_error * dither_strength

            for dr_dc, weight in ATKINSON_DISTRIBUTION:
                nc, nr = c + dr_dc[0], r + dr_dc[1]
                if 0 <= nr < rows and 0 <= nc < cols:
                    img_np[nr, nc] += error_to_distribute * weight

    final_binary_np = np.where(img_np > 127.5, 255, 0).astype(np.uint8)
    monochrome_frame = Image.fromarray(final_binary_np, mode='L').convert('1')
    return monochrome_frame

# New function to be ADDED to oled_utils/image_processing.py


def _apply_floyd_steinberg_dither(grayscale_image: Image.Image, dither_strength: float = 1.0) -> Image.Image:
    """
    Applies Floyd-Steinberg dithering to a grayscale PIL Image with variable strength.
    Returns a 1-bit monochrome PIL Image.
    dither_strength: 0.0 (results in thresholding) to 1.0 (full Floyd-Steinberg).
    """
    if grayscale_image.mode != 'L':
        grayscale_image = grayscale_image.convert('L')

    # Use float for error accumulation
    img_np = np.array(grayscale_image, dtype=float)
    rows, cols = img_np.shape

    # Floyd-Steinberg distribution coefficients and coordinates (dx, dy)
    #       *   7/16
    #   3/16 5/16 1/16
    fs_distribution = [
        ((1, 0), 7/16),  # Pixel to the right
        ((-1, 1), 3/16),  # Pixel below-left
        ((0, 1), 5/16),  # Pixel directly below
        ((1, 1), 1/16)   # Pixel below-right
    ]

    for r in range(rows):
        for c in range(cols):
            old_pixel = img_np[r, c]
            new_pixel = 255.0 if old_pixel > 127.5 else 0.0
            img_np[r, c] = new_pixel  # Set the dithered pixel value
            quant_error = old_pixel - new_pixel

            # Apply dither strength to the error being distributed
            error_to_distribute = quant_error * dither_strength

            for dr_dc, weight in fs_distribution:
                nc, nr = c + dr_dc[0], r + dr_dc[1]  # dx, dy
                if 0 <= nr < rows and 0 <= nc < cols:
                    img_np[nr, nc] += error_to_distribute * weight

    # After error diffusion, ensure values are binary by thresholding the result
    final_binary_np = np.where(img_np > 127.5, 255, 0).astype(np.uint8)
    monochrome_frame = Image.fromarray(final_binary_np, mode='L').convert('1')
    return monochrome_frame

# Replacement for 'def process_single_frame(...)' in oled_utils/image_processing.py


def process_single_frame(frame: Image.Image,
                         resize_mode: str,
                         mono_conversion_mode: str,
                         threshold_value: int,
                         invert_colors: bool,
                         contrast_factor: float,
                         brightness_factor: float,
                         sharpen_factor: float,
                         gamma_value: float,
                         blur_radius: float,
                         noise_amount: int,
                         noise_type: str,
                         dither_strength: float
                         ) -> Image.Image | None:
    """Processes a single PIL Image frame to a 128x64 1-bit PIL Image, with pre-processing."""
    try:
        # 1. Ensure RGBA for consistent transparency handling
        if frame.mode != 'RGBA':
            frame = frame.convert("RGBA")

        # 2. Resize
        processed_frame = frame
        if resize_mode == "Stretch to Fit":
            processed_frame = frame.resize(
                TARGET_SIZE, Image.Resampling.LANCZOS)
        elif resize_mode == "Fit (Keep Aspect, Pad)":
            img_copy = frame.copy()
            img_copy.thumbnail(TARGET_SIZE, Image.Resampling.LANCZOS)
            processed_frame = Image.new("RGBA", TARGET_SIZE, (0, 0, 0, 255))
            paste_x = (TARGET_SIZE[0] - img_copy.width) // 2
            paste_y = (TARGET_SIZE[1] - img_copy.height) // 2
            processed_frame.paste(img_copy, (paste_x, paste_y), img_copy)
        elif resize_mode == "Crop to Center":
            original_width, original_height = frame.size
            target_aspect = TARGET_SIZE[0] / TARGET_SIZE[1]
            original_aspect = original_width / original_height
            if original_aspect > target_aspect:
                new_height_temp = TARGET_SIZE[1]
                new_width_temp = int(new_height_temp * original_aspect)
            else:
                new_width_temp = TARGET_SIZE[0]
                new_height_temp = int(new_width_temp / original_aspect)
            resized_temp = frame.resize(
                (new_width_temp, new_height_temp), Image.Resampling.LANCZOS)
            crop_x = (new_width_temp - TARGET_SIZE[0]) / 2
            crop_y = (new_height_temp - TARGET_SIZE[1]) / 2
            crop_box = (crop_x, crop_y, crop_x +
                        TARGET_SIZE[0], crop_y + TARGET_SIZE[1])
            processed_frame = resized_temp.crop(crop_box)
        else:  # Default
            processed_frame = frame.resize(
                TARGET_SIZE, Image.Resampling.LANCZOS)

        # 3. Convert to Grayscale
        if processed_frame.mode == 'RGBA':
            background = Image.new("RGB", processed_frame.size, (0, 0, 0))
            background.paste(processed_frame, mask=processed_frame.split()[3])
            grayscale_frame = background.convert("L")
        else:
            grayscale_frame = processed_frame.convert("L")

        # --- Pre-Dithering Adjustments ---
        if brightness_factor != 1.0:
            enhancer = ImageEnhance.Brightness(grayscale_frame)
            grayscale_frame = enhancer.enhance(brightness_factor)
        if gamma_value != 1.0:
            gamma_corrected = bytearray(256)
            for i in range(256):
                gamma_corrected[i] = int(((i / 255.0) ** gamma_value) * 255.0)
            grayscale_frame = grayscale_frame.point(gamma_corrected)
        if sharpen_factor > 0:
            pil_sharpen_factor = 1.0 + (sharpen_factor / 100.0) * 1.0
            if pil_sharpen_factor != 1.0:
                enhancer = ImageEnhance.Sharpness(grayscale_frame)
                grayscale_frame = enhancer.enhance(pil_sharpen_factor)
        if contrast_factor != 1.0:
            enhancer = ImageEnhance.Contrast(grayscale_frame)
            grayscale_frame = enhancer.enhance(contrast_factor)
        if noise_type == "Pre-Dither" and noise_amount > 0:
            img_np = np.array(grayscale_frame, dtype=np.float32)
            noise_intensity = noise_amount * 2.55
            noise = np.random.normal(0, noise_intensity / 6, img_np.shape)
            img_np += noise
            img_np = np.clip(img_np, 0, 255)
            grayscale_frame = Image.fromarray(
                img_np.astype(np.uint8), mode='L')
        if blur_radius > 0.0:  # Apply blur if radius is greater than 0
            grayscale_frame = grayscale_frame.filter(
                ImageFilter.GaussianBlur(radius=blur_radius))
        if invert_colors:
            grayscale_frame = ImageOps.invert(grayscale_frame)

        # 5. Monochrome Conversion / Dithering
        monochrome_frame: Image.Image
        if mono_conversion_mode == "Floyd-Steinberg Dither":
            monochrome_frame = _apply_floyd_steinberg_dither(
                grayscale_frame, dither_strength)  # Call new custom function
        elif mono_conversion_mode == "Atkinson Dither":
            monochrome_frame = _apply_atkinson_dither(
                grayscale_frame, dither_strength)
        elif mono_conversion_mode == "Simple Threshold":
            monochrome_frame = grayscale_frame.point(
                lambda p: 255 if p > threshold_value else 0, '1')
        elif mono_conversion_mode.startswith("Ordered Dither"):
            bayer_matrix_to_use = NORMALIZED_BAYER_MATRIX_4X4
            if "Bayer 2x2" in mono_conversion_mode:
                bayer_matrix_to_use = NORMALIZED_BAYER_MATRIX_2X2
            elif "Bayer 8x8" in mono_conversion_mode:
                bayer_matrix_to_use = NORMALIZED_BAYER_MATRIX_8X8
            gray_np = np.array(grayscale_frame, dtype=np.float32) / 255.0
            output_np = np.zeros_like(gray_np, dtype=np.uint8)
            bayer_rows, bayer_cols = bayer_matrix_to_use.shape
            for r_idx in range(gray_np.shape[0]):
                for c_idx in range(gray_np.shape[1]):
                    if gray_np[r_idx, c_idx] > bayer_matrix_to_use[r_idx % bayer_rows, c_idx % bayer_cols]:
                        output_np[r_idx, c_idx] = 255
            monochrome_frame = Image.fromarray(
                output_np, mode='L').convert('1')
        else:
            print(
                f"IPROC Warning: Unknown mono_conversion_mode '{mono_conversion_mode}', defaulting to Floyd-Steinberg (custom with strength).")
            monochrome_frame = _apply_floyd_steinberg_dither(
                grayscale_frame, dither_strength)

        # 6. Post-Dither Noise (if selected)
        if noise_type == "Post-Dither" and noise_amount > 0:
            img_np = np.array(monochrome_frame)
            num_pixels_to_flip = int((noise_amount / 100.0) * img_np.size)
            row_indices = np.random.randint(
                0, img_np.shape[0], size=num_pixels_to_flip)
            col_indices = np.random.randint(
                0, img_np.shape[1], size=num_pixels_to_flip)
            for r, c in zip(row_indices, col_indices):
                img_np[r, c] = 255 - img_np[r, c]
            monochrome_frame = Image.fromarray(img_np, mode='1')

        return monochrome_frame

    except Exception as e:
        print(f"Error processing single frame: {e}")
        import traceback
        traceback.print_exc()
        return None


def process_image_to_oled_data(filepath: str,
                                resize_mode: str,
                                mono_conversion_mode: str,
                                threshold_value: int,
                                invert_colors: bool,
                                contrast_factor: float,
                                brightness_factor: float,
                                sharpen_factor: float,
                                gamma_value: float,
                                blur_radius: float,
                                noise_amount: int,
                                noise_type: str,
                                dither_strength: float,
                                max_frames_to_import: int = 0
                                ) -> tuple[list[list[str]] | None, float | None, int | None]:
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

        frames_to_process = num_frames
        if is_animated and max_frames_to_import > 0:
            frames_to_process = min(num_frames, max_frames_to_import)

        if is_animated:
            try:
                duration_ms = img.info.get('duration', 100)
                if duration_ms > 0:
                    source_fps = 1000.0 / duration_ms
                else:
                    source_fps = 10.0
                source_loop_count = img.info.get('loop', 0)
            except Exception as e_info:
                print(
                    f"IPROC Warning: Could not read GIF duration/loop for '{filepath}': {e_info}. Using defaults.")
                source_fps = 10.0
                source_loop_count = 0

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
                contrast_factor,
                brightness_factor,
                sharpen_factor,
                gamma_value,
                blur_radius,
                noise_amount,
                noise_type,
                dither_strength
            )

            if monochrome_pil_frame:
                logical_frames_output.append(
                    logical_frame_to_string_list(monochrome_pil_frame))
            else:
                print(
                    f"IPROC Warning: Skipping frame {i} for '{filepath}' due to processing error.")

        if not logical_frames_output:
            print(
                f"IPROC Error: No frames successfully processed for '{filepath}'.")
            return None, source_fps, source_loop_count

        return logical_frames_output, source_fps, source_loop_count

    except FileNotFoundError:
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
    from PIL import ImageDraw, ImageFont

    print("--- Testing Image Processing Utility ---")

    PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    YOUR_STATIC_IMAGE_PATH = os.path.join(PROJECT_ROOT, "my_test_image.png")
    YOUR_GIF_PATH = os.path.join(PROJECT_ROOT, "my_test_gif.gif")
    DUMMY_STATIC_IMAGE_PATH = os.path.join(
        PROJECT_ROOT, "test_static_image_generated_iproc.png")
    DUMMY_GIF_PATH = os.path.join(
        PROJECT_ROOT, "test_animation_generated_iproc.gif")

    # (create_dummy_assets_if_needed function can remain as is)
    def create_dummy_assets_if_needed():
        assets_actually_created = False
        if not os.path.exists(YOUR_STATIC_IMAGE_PATH) and not os.path.exists(DUMMY_STATIC_IMAGE_PATH):
            try:
                img_static = Image.new("RGB", (200, 100), "teal")
                draw_static = ImageDraw.Draw(img_static)
                try:
                    font = ImageFont.truetype("arial.ttf", 30)
                except IOError:
                    font = ImageFont.load_default()
                draw_static.text((10, 10), "Static!", fill="yellow", font=font)
                img_static.save(DUMMY_STATIC_IMAGE_PATH)
                print(f"Created dummy static image: {DUMMY_STATIC_IMAGE_PATH}")
                assets_actually_created = True
            except Exception as e:
                print(f"Could not create dummy static image: {e}")
        if not os.path.exists(YOUR_GIF_PATH) and not os.path.exists(DUMMY_GIF_PATH):
            try:
                frames = []
                try:
                    font = ImageFont.truetype("arial.ttf", 18)
                except IOError:
                    font = ImageFont.load_default()
                for i in range(5):
                    img_gif_frame = Image.new(
                        "RGB", (100, 50), (255 - i * 40, i * 40, 128))
                    draw_gif = ImageDraw.Draw(img_gif_frame)
                    draw_gif.text(
                        (5, 5), f"Anim {i+1}", fill="white", font=font)
                    frames.append(img_gif_frame)
                frames[0].save(DUMMY_GIF_PATH, save_all=True,
                               append_images=frames[1:], duration=200, loop=0)
                print(f"Created dummy GIF: {DUMMY_GIF_PATH}")
                assets_actually_created = True
            except Exception as e:
                print(f"Could not create dummy GIF: {e}")
        return assets_actually_created

    create_dummy_assets_if_needed()

    test_files_to_process = []
    if os.path.exists(YOUR_STATIC_IMAGE_PATH):
        test_files_to_process.append(YOUR_STATIC_IMAGE_PATH)
    elif os.path.exists(DUMMY_STATIC_IMAGE_PATH):
        test_files_to_process.append(DUMMY_STATIC_IMAGE_PATH)
    if os.path.exists(YOUR_GIF_PATH):
        test_files_to_process.append(YOUR_GIF_PATH)
    elif os.path.exists(DUMMY_GIF_PATH):
        test_files_to_process.append(DUMMY_GIF_PATH)

    if not test_files_to_process:
        print("\nNo test files to process.")

    for test_file_path in test_files_to_process:
        print(f"\n--- Testing with: {os.path.basename(test_file_path)} ---")
        options_to_test = [
            {"resize": "Stretch to Fit", "mono": "Floyd-Steinberg Dither", "thresh": 128,
                "invert": False, "contrast": 1.0, "brightness": 1.0, "sharpen": 0},
            {"resize": "Fit (Keep Aspect, Pad)", "mono": "Atkinson Dither", "thresh": 128,
             "invert": False, "contrast": 1.2, "brightness": 1.1, "sharpen": 50},
            {"resize": "Crop to Center",
                "mono": "Ordered Dither (Bayer 2x2)", "thresh": 128, "invert": True, "contrast": 1.0, "brightness": 0.9, "sharpen": 0},
            {"resize": "Stretch to Fit", "mono": "Ordered Dither (Bayer 8x8)", "thresh": 128,
             "invert": False, "contrast": 1.0, "brightness": 1.0, "sharpen": 100},
            {"resize": "Fit (Keep Aspect, Pad)", "mono": "Simple Threshold", "thresh": 100,
             "invert": False, "contrast": 1.0, "brightness": 1.0, "sharpen": 0},
        ]

        for i, opts in enumerate(options_to_test):
            print(
                f"\n  Test Case {i+1}: Resize='{opts['resize']}', Mono='{opts['mono']}', Thresh={opts['thresh']}, Invert={opts['invert']}, Contrast={opts['contrast']:.2f}, Bright={opts['brightness']:.2f}, Sharpen={opts['sharpen']}")
            logical_frames, fps, loop = process_image_to_oled_data(
                test_file_path,
                resize_mode=opts['resize'],
                mono_conversion_mode=opts['mono'],
                threshold_value=opts['thresh'],
                invert_colors=opts['invert'],
                contrast_factor=opts['contrast'],
                brightness_factor=opts['brightness'],
                sharpen_factor=opts['sharpen'],
                max_frames_to_import=3  # Limit frames for faster testing
            )
            if logical_frames:
                print(
                    f"    Processed {len(logical_frames)} frames. FPS: {fps}, Loop: {loop}")
                if logical_frames[0]:
                    try:
                        img_out = Image.new('1', TARGET_SIZE)
                        pixels_out = img_out.load()
                        for y_idx, row_str in enumerate(logical_frames[0]):
                            for x_idx, char_val in enumerate(row_str):
                                pixels_out[x_idx,
                                            y_idx] = 255 if char_val == '1' else 0
                        output_filename_base = os.path.basename(
                            test_file_path).split('.')[0]
                        output_filename_suffix = opts['mono'].replace(" ", "_").replace(
                            "(", "").replace(")", "").replace("/", "_")
                        output_filepath = os.path.join(
                            PROJECT_ROOT, f"preview_iproc_{output_filename_base}_case{i+1}_{output_filename_suffix}.png")
                        img_out.save(output_filepath)
                        print(f"    Saved preview: {output_filepath}")
                    except Exception as e_save:
                        print(f"    Could not save preview: {e_save}")
            else:
                print("    Processing failed.")
    # (Cleanup dummy files logic can remain as is)
    if os.path.exists(DUMMY_STATIC_IMAGE_PATH) and "generated_iproc" in DUMMY_STATIC_IMAGE_PATH:
        os.remove(DUMMY_STATIC_IMAGE_PATH)
    if os.path.exists(DUMMY_GIF_PATH) and "generated_iproc" in DUMMY_GIF_PATH:
        os.remove(DUMMY_GIF_PATH)
    print("\n--- Image Processing Test Finished ---")
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