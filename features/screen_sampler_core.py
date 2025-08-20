# AKAI_Fire_RGB_Controller/features/screen_sampler_core.py
import mss
import numpy as np
from PIL import Image, ImageEnhance
import colorsys 
import os 
from oled_utils import oled_renderer

try:
    from colorthief import ColorThief
    COLORTHIEF_AVAILABLE = True
except ImportError:
    COLORTHIEF_AVAILABLE = False
    print("ScreenSamplerCore WARNING: colorthief library not found. 'Palette' mode will be unavailable.")

class ScreenSamplerCore:
    INTERMEDIATE_DOWNSAMPLE_SIZE = (320, 180)  # <<< ADD THIS LINE
    VALID_QUADRANTS_FOR_DEFAULT_REGIONS = ["top-left", "top-right", "bottom-left", "bottom-right", "center", "full-screen"]
    DEFAULT_FALLBACK_LOGICAL_WIDTH = 128 
    DEFAULT_FALLBACK_LOGICAL_HEIGHT = 128
    DEFAULT_FULLSCREEN_DOWNSCALE_DIMENSIONS = (100, 100) # For the single averaged color if overall region is full
    DEFAULT_ADJUSTMENTS = {
        'saturation': 2.0, 'contrast': 1.0, 'brightness': 1.5, 'hue_shift': 0
    }
    _save_temp_preview_image_for_diagnosis = False 
    NUM_GRID_ROWS = 4
    NUM_GRID_COLS = 16

    @staticmethod
    def get_available_monitors(sct_instance) -> list[dict]:
        if not sct_instance: return []
        monitors = []
        for i, monitor_info in enumerate(sct_instance.monitors):
            if i == 0: continue
            monitors.append({
                "id": i, "name": f"Monitor {i} ({monitor_info['width']}x{monitor_info['height']})",
                "top": monitor_info["top"], "left": monitor_info["left"],
                "width": monitor_info["width"], "height": monitor_info["height"],
                "monitor_dict": monitor_info 
            })
        return monitors

    @staticmethod
    def _calculate_pixel_bounding_box_from_percentage(
            monitor_info: dict, region_rect_percentage: dict) -> dict | None:
        if not all(key in region_rect_percentage for key in ['x', 'y', 'width', 'height']): return None
        mon_orig_w, mon_orig_h = monitor_info['width'], monitor_info['height']
        mon_orig_left, mon_orig_top = monitor_info['left'], monitor_info['top']
        abs_x = mon_orig_left + int(region_rect_percentage['x'] * mon_orig_w)
        abs_y = mon_orig_top + int(region_rect_percentage['y'] * mon_orig_h)
        abs_w = int(region_rect_percentage['width'] * mon_orig_w)
        abs_h = int(region_rect_percentage['height'] * mon_orig_h)
        if abs_w <= 0 or abs_h <= 0:
            abs_w = ScreenSamplerCore.DEFAULT_FALLBACK_LOGICAL_WIDTH
            abs_h = ScreenSamplerCore.DEFAULT_FALLBACK_LOGICAL_HEIGHT
            abs_w = min(abs_w, mon_orig_w - (abs_x - mon_orig_left))
            abs_h = min(abs_h, mon_orig_h - (abs_y - mon_orig_top))
            if abs_w <=0 : abs_w = min(ScreenSamplerCore.DEFAULT_FALLBACK_LOGICAL_WIDTH, mon_orig_w)
            if abs_h <=0 : abs_h = min(ScreenSamplerCore.DEFAULT_FALLBACK_LOGICAL_HEIGHT, mon_orig_h)
        abs_x = max(mon_orig_left, min(abs_x, mon_orig_left + mon_orig_w - 1)) 
        abs_y = max(mon_orig_top, min(abs_y, mon_orig_top + mon_orig_h - 1))
        abs_w = min(abs_w, mon_orig_left + mon_orig_w - abs_x)
        abs_h = min(abs_h, mon_orig_top + mon_orig_h - abs_y)
        abs_w = max(1, abs_w); abs_h = max(1, abs_h)
        return {"top": int(abs_y), "left": int(abs_x), "width": int(abs_w), "height": int(abs_h), "mon": monitor_info.get("id", 1)}

    @staticmethod
    def _apply_hue_shift(rgb_tuple: tuple[int,int,int], hue_shift_degrees: int) -> tuple[int,int,int]:
        if hue_shift_degrees == 0:
            return rgb_tuple
        
        r_norm, g_norm, b_norm = rgb_tuple[0]/255.0, rgb_tuple[1]/255.0, rgb_tuple[2]/255.0
        h, s, v = colorsys.rgb_to_hsv(r_norm, g_norm, b_norm)
        h_shifted = (h + (hue_shift_degrees / 360.0)) % 1.0 
        if h_shifted < 0: h_shifted += 1.0 
        r_fin_norm, g_fin_norm, b_fin_norm = colorsys.hsv_to_rgb(h_shifted, s, v)
        return (int(r_fin_norm*255), int(g_fin_norm*255), int(b_fin_norm*255))

    @staticmethod
    def capture_and_grid_sample_colors(
        sct_instance, monitor_capture_id: int, overall_region_percentage: dict,
        adjustments: dict | None = None
    ) -> tuple[list[tuple[int, int, int]] | None, Image.Image | None]:
        """
        Captures a screen region, immediately downsamples it for massive performance
        gains, applies color enhancements to the small image, and then samples it.
        """
        if not sct_instance:
            return None, None
        current_adjustments = ScreenSamplerCore.DEFAULT_ADJUSTMENTS.copy()
        if adjustments:
            current_adjustments.update(adjustments)
        try:
            all_monitors_info = sct_instance.monitors
            if not (0 <= monitor_capture_id < len(all_monitors_info)):
                return None, None
            selected_monitor_info = all_monitors_info[monitor_capture_id]
            overall_pixel_bbox = ScreenSamplerCore._calculate_pixel_bounding_box_from_percentage(
                selected_monitor_info, overall_region_percentage
            )
            if not overall_pixel_bbox:
                return None, None
            # --- STEP 1: Capture the (potentially large) region ---
            sct_overall_img = sct_instance.grab(overall_pixel_bbox)
            # --- This check remains important ---
            if sct_overall_img.width < ScreenSamplerCore.NUM_GRID_COLS or sct_overall_img.height < ScreenSamplerCore.NUM_GRID_ROWS:
                return [(0, 0, 0)] * 64, None
            # --- STEP 2: Convert to PIL and IMMEDIATELY downsample ---
            # The BGR -> RGB swap must be done before resizing to maintain color integrity.
            pil_img_raw = Image.frombytes(
                "RGB", sct_overall_img.size, sct_overall_img.rgb, "raw", "BGR")
            b, g, r = pil_img_raw.split()
            # Re-merge in correct R,G,B order
            pil_img_bgr_fixed = Image.merge("RGB", (r, g, b))
            # THE CORE OPTIMIZATION: Resize to a small, manageable intermediate image
            pil_img_small = pil_img_bgr_fixed.resize(
                ScreenSamplerCore.INTERMEDIATE_DOWNSAMPLE_SIZE,
                resample=Image.Resampling.NEAREST  # NEAREST is fastest and good enough for this
            )
            # --- STEP 3: Apply all enhancements to the SMALL image ---
            pil_preview_adjusted = pil_img_small  # Start with the small image
            if current_adjustments['brightness'] != 1.0:
                enhancer = ImageEnhance.Brightness(pil_preview_adjusted)
                pil_preview_adjusted = enhancer.enhance(
                    current_adjustments['brightness'])
            if current_adjustments['contrast'] != 1.0:
                enhancer = ImageEnhance.Contrast(pil_preview_adjusted)
                pil_preview_adjusted = enhancer.enhance(
                    current_adjustments['contrast'])
            if current_adjustments['saturation'] != 1.0:
                enhancer = ImageEnhance.Color(pil_preview_adjusted)
                pil_preview_adjusted = enhancer.enhance(
                    current_adjustments['saturation'])
            # --- STEP 4: Grid sample from the small, enhanced image ---
            img_np = np.array(pil_preview_adjusted)
            cell_height = img_np.shape[0] // ScreenSamplerCore.NUM_GRID_ROWS
            cell_width = img_np.shape[1] // ScreenSamplerCore.NUM_GRID_COLS
            # This logic should now be safe since we control the intermediate size
            if cell_height == 0 or cell_width == 0:
                return [(0, 0, 0)] * 64, pil_preview_adjusted
            cropped_height = cell_height * ScreenSamplerCore.NUM_GRID_ROWS
            cropped_width = cell_width * ScreenSamplerCore.NUM_GRID_COLS
            img_cropped = img_np[:cropped_height, :cropped_width]
            reshaped = img_cropped.reshape(ScreenSamplerCore.NUM_GRID_ROWS, cell_height,
                                            ScreenSamplerCore.NUM_GRID_COLS, cell_width, 3)
            grid_cells = reshaped.swapaxes(
                1, 2).reshape(-1, cell_height * cell_width, 3)
            avg_colors_np = np.mean(grid_cells, axis=1).astype(int)
            hue_shift_degrees = current_adjustments.get('hue_shift', 0)
            if hue_shift_degrees != 0:
                pad_colors_final = [ScreenSamplerCore._apply_hue_shift(
                    tuple(color), hue_shift_degrees) for color in avg_colors_np]
            else:
                pad_colors_final = [tuple(color) for color in avg_colors_np]
            # Return the final colors and the SMALL adjusted image for the preview window
            return pad_colors_final, pil_preview_adjusted
        except mss.exception.ScreenShotError:
            pass
        except Exception as e:
            print(f"ScreenSamplerCore: Error in grid sampling: {e}")
            import traceback
            traceback.print_exc()
        return None, None

    @staticmethod
    def capture_and_thumbnail_sample(
        sct_instance, monitor_capture_id: int, adjustments: dict | None = None
    ) -> tuple[list[tuple[int, int, int]] | None, Image.Image | None]:
        """
        Captures the entire monitor, uses Pillow to efficiently resize to the 16x4
        pad grid, applies color adjustments, and returns the list of 64 colors.
        """
        if not sct_instance:
            return None, None
        current_adjustments = ScreenSamplerCore.DEFAULT_ADJUSTMENTS.copy()
        if adjustments:
            current_adjustments.update(adjustments)
        try:
            monitor_bbox = sct_instance.monitors[monitor_capture_id]
            # --- FIX: Grab the full resolution image (mss v10 compatible) ---
            sct_img = sct_instance.grab(monitor_bbox)
            # Convert to a Pillow Image
            pil_img_raw = Image.frombytes(
                "RGB", sct_img.size, sct_img.rgb, "raw", "BGR")
            b, g, r = pil_img_raw.split()
            thumbnail = Image.merge("RGB", (r, g, b))
            # --- FIX: Re-introduce the resize step using Pillow's optimized method ---
            thumbnail = thumbnail.resize(
                (ScreenSamplerCore.NUM_GRID_COLS, ScreenSamplerCore.NUM_GRID_ROWS),
                resample=Image.Resampling.LANCZOS  # High quality downsampling
            )
            if current_adjustments['brightness'] != 1.0:
                enhancer = ImageEnhance.Brightness(thumbnail)
                thumbnail = enhancer.enhance(current_adjustments['brightness'])
            if current_adjustments['contrast'] != 1.0:
                enhancer = ImageEnhance.Contrast(thumbnail)
                thumbnail = enhancer.enhance(current_adjustments['contrast'])
            if current_adjustments['saturation'] != 1.0:
                enhancer = ImageEnhance.Color(thumbnail)
                thumbnail = enhancer.enhance(current_adjustments['saturation'])
            img_np = np.array(thumbnail)
            pad_colors_tuples = [tuple(p) for p in img_np.reshape(-1, 3)]
            hue_shift_degrees = current_adjustments.get('hue_shift', 0)
            if hue_shift_degrees != 0:
                pad_colors_final = [ScreenSamplerCore._apply_hue_shift(
                    c, hue_shift_degrees) for c in pad_colors_tuples]
            else:
                pad_colors_final = pad_colors_tuples
            return pad_colors_final, None
        except Exception as e:
            print(f"ScreenSamplerCore: Error in thumbnail sampling: {e}")
            return None, None

    @staticmethod
    def capture_and_palette_sample(
        sct_instance, monitor_capture_id: int, adjustments: dict | None = None
    ) -> tuple[list[tuple[int, int, int]] | None, Image.Image | None]:
        """
        Captures the screen, uses Pillow to downsample, finds the 5 most dominant
        colors, and creates a smooth gradient across the pads.
        """
        if not sct_instance or not COLORTHIEF_AVAILABLE:
            if not COLORTHIEF_AVAILABLE:
                print("Palette mode unavailable: colorthief library missing.")
            return None, None
        current_adjustments = ScreenSamplerCore.DEFAULT_ADJUSTMENTS.copy()
        if adjustments:
            current_adjustments.update(adjustments)
        try:
            monitor_bbox = sct_instance.monitors[monitor_capture_id]
            # --- FIX: Grab the full resolution image (mss v10 compatible) ---
            sct_img = sct_instance.grab(monitor_bbox)
            # Convert to a Pillow Image
            pil_img_raw = Image.frombytes(
                "RGB", sct_img.size, sct_img.rgb, "raw", "BGR")
            b, g, r = pil_img_raw.split()
            thumbnail = Image.merge("RGB", (r, g, b))
            # --- FIX: Re-introduce the resize step using Pillow's optimized method ---
            thumbnail = thumbnail.resize(
                (150, 84), resample=Image.Resampling.LANCZOS)
            if current_adjustments['brightness'] != 1.0:
                thumbnail = ImageEnhance.Brightness(thumbnail).enhance(
                    current_adjustments['brightness'])
            if current_adjustments['contrast'] != 1.0:
                thumbnail = ImageEnhance.Contrast(thumbnail).enhance(
                    current_adjustments['contrast'])
            if current_adjustments['saturation'] != 1.0:
                thumbnail = ImageEnhance.Color(thumbnail).enhance(
                    current_adjustments['saturation'])
            from io import BytesIO
            with BytesIO() as f:
                thumbnail.save(f, format='PNG')
                f.seek(0)
                color_thief = ColorThief(f)
                palette = color_thief.get_palette(color_count=5, quality=10)
            if not palette or len(palette) < 5:
                avg_color = np.array(thumbnail).mean(axis=(0, 1)).astype(int)
                return [tuple(avg_color)] * 64, None
            tl, tr, bl, br, c = [np.array(color) for color in palette]
            x = np.linspace(0, 1, ScreenSamplerCore.NUM_GRID_COLS)
            y = np.linspace(0, 1, ScreenSamplerCore.NUM_GRID_ROWS)
            xv, yv = np.meshgrid(x, y)
            top_interp = (1 - xv[..., np.newaxis]) * \
                tl + xv[..., np.newaxis] * tr
            bottom_interp = (1 - xv[..., np.newaxis]) * \
                bl + xv[..., np.newaxis] * br
            corner_gradient = (1 - yv[..., np.newaxis]) * \
                top_interp + yv[..., np.newaxis] * bottom_interp
            center_dist = np.sqrt((xv - 0.5)**2 + (yv - 0.4)**2)
            center_weight = 1 - np.clip(center_dist * 1.5, 0, 1)
            final_gradient_np = (
                1 - center_weight[..., np.newaxis]) * corner_gradient + center_weight[..., np.newaxis] * c
            final_gradient_np = np.clip(final_gradient_np, 0, 255).astype(int)
            pad_colors_tuples = [tuple(p)
                                for p in final_gradient_np.reshape(-1, 3)]
            hue_shift_degrees = current_adjustments.get('hue_shift', 0)
            if hue_shift_degrees != 0:
                pad_colors_final = [ScreenSamplerCore._apply_hue_shift(
                    c, hue_shift_degrees) for c in pad_colors_tuples]
            else:
                pad_colors_final = pad_colors_tuples
            return pad_colors_final, None
        except Exception as e:
            print(f"ScreenSamplerCore: Error in palette sampling: {e}")
            import traceback
            traceback.print_exc()
            return None, None
        

    @staticmethod
    def capture_and_process_for_oled(
        sct_instance, monitor_capture_id: int, overall_region_percentage: dict,
        dither_settings: dict
    ) -> tuple[bytearray | None, Image.Image | None]:
        """
        Captures a screen region, resizes to 128x64, applies dithering based
        on settings, packs it into the 7-bit SysEx format for the OLED, and
        returns the packed data along with a preview image.
        """
        if not sct_instance:
            return None, None
        try:
            # 1. Calculate the capture region
            all_monitors_info = sct_instance.monitors
            if not (0 <= monitor_capture_id < len(all_monitors_info)):
                return None, None
            selected_monitor_info = all_monitors_info[monitor_capture_id]
            pixel_bbox = ScreenSamplerCore._calculate_pixel_bounding_box_from_percentage(
                selected_monitor_info, overall_region_percentage
            )
            if not pixel_bbox:
                return None, None
            # 2. Capture and convert to PIL
            sct_img = sct_instance.grab(pixel_bbox)
            pil_img_raw = Image.frombytes(
                "RGB", sct_img.size, sct_img.rgb, "raw", "BGR")
            b, g, r = pil_img_raw.split()
            pil_img_color = Image.merge("RGB", (r, g, b))
            # 3. Resize and convert to grayscale
            pil_img_resized = pil_img_color.resize(
                (oled_renderer.OLED_WIDTH, oled_renderer.OLED_HEIGHT),
                resample=Image.Resampling.LANCZOS
            )
            pil_img_grayscale = pil_img_resized.convert("L")
            # 4. Apply dithering based on settings
            method = dither_settings.get('method', 'threshold')
            threshold = dither_settings.get('threshold_value', 128)
            if method == 'floyd_steinberg':
                # (Placeholder for future implementation)
                pil_img_dithered = pil_img_grayscale.convert(
                    '1', dither=Image.Dither.FLOYDSTEINBERG)
            else:  # Default to simple threshold
                pil_img_dithered = pil_img_grayscale.point(
                    lambda p: 255 if p > threshold else 0, '1')
            # 5. Pack the final 1-bit image for the hardware
            packed_data = oled_renderer.pack_pil_image_to_7bit_stream(
                pil_img_dithered)
            # Return both the packed data for the hardware and the dithered image for a potential preview
            return packed_data, pil_img_dithered
        except mss.exception.ScreenShotError:
            pass  # Ignore errors if the screen is locked, etc.
        except Exception as e:
            print(f"ScreenSamplerCore: Error in OLED processing: {e}")
        return None, None

if __name__ == '__main__':
    print("ScreenSamplerCore: Main example for GR 그리드 샘플링 started.")
    # ScreenSamplerCore._save_temp_preview_image_for_diagnosis = True 
    try:
        with mss.mss() as sct:
            available_monitors = ScreenSamplerCore.get_available_monitors(sct)
            if not available_monitors: print("No monitors found."); exit()
            target_monitor = available_monitors[0]
            print(f"Sampling from: {target_monitor['name']} (mss ID: {target_monitor['id']})")
            # Test with a region that's a good portion of the screen
            test_overall_region_perc = {'x': 0.25, 'y': 0.25, 'width': 0.5, 'height': 0.5} # Center 50%
            test_adjustments = {'saturation': 1.0, 'contrast': 1.0, 'brightness': 1.0, 'hue_shift': 0}
            print(f"Using overall region: {test_overall_region_perc}, adjustments: {test_adjustments}")
            list_of_pad_colors, full_preview_img = ScreenSamplerCore.capture_and_grid_sample_colors(
                sct, target_monitor['id'], test_overall_region_perc, adjustments=test_adjustments
            )
            if list_of_pad_colors:
                print(f"  Successfully got {len(list_of_pad_colors)} pad colors.")
                # print(f"  First few colors: {list_of_pad_colors[:5]}")
                if len(list_of_pad_colors) == 64:
                    print("  Color for pad (0,0) (top-left): ", list_of_pad_colors[0])
                    print("  Color for pad (3,15) (bottom-right): ", list_of_pad_colors[63])
            else:
                print(f"  Failed to get list of pad colors.")
            if full_preview_img:
                print(f"  Full S/C/B Adjusted Preview Image: Mode={full_preview_img.mode}, Size={full_preview_img.size}")
                # full_preview_img.save(f"_test_grid_full_preview.png")
                # print(f"  Saved full preview image to _test_grid_full_preview.png")
            else:
                print(f"  No full preview image returned.")
    except Exception as e: print(f"Error in ScreenSamplerCore GR 그리드 샘플링 example: {e}")
    print("\nScreenSamplerCore: Example finished.")