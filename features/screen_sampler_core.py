# AKAI_Fire_RGB_Controller/features/screen_sampler_core.py
import mss
import numpy as np
from PIL import Image, ImageEnhance
import colorsys 
import os 

class ScreenSamplerCore:
    VALID_QUADRANTS_FOR_DEFAULT_REGIONS = ["top-left", "top-right", "bottom-left", "bottom-right", "center", "full-screen"]
    DEFAULT_FALLBACK_LOGICAL_WIDTH = 128 
    DEFAULT_FALLBACK_LOGICAL_HEIGHT = 128
    DEFAULT_FULLSCREEN_DOWNSCALE_DIMENSIONS = (100, 100) # For the single averaged color if overall region is full
    DEFAULT_ADJUSTMENTS = {
        'saturation': 1.0, 'contrast': 1.0, 'brightness': 1.0, 'hue_shift': 0
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
    ) -> tuple[list[tuple[int,int,int]] | None, Image.Image | None]:
        """
        Captures the overall region, applies S/C/B, then subdivides this adjusted image
        into a 4x16 grid, calculates average color for each cell, applies hue shift,
        and returns the list of 64 colors along with the S/C/B adjusted full preview image.
        """
        
        pad_colors_final = None
        pil_full_preview_scb_adjusted = None 

        if not sct_instance: print("ScreenSamplerCore: mss instance not provided."); return None, None
        
        current_adjustments = ScreenSamplerCore.DEFAULT_ADJUSTMENTS.copy()
        if adjustments: current_adjustments.update(adjustments)

        try:
            all_monitors_info = sct_instance.monitors
            if not (0 <= monitor_capture_id < len(all_monitors_info)):
                print(f"ScreenSamplerCore: Invalid monitor_id '{monitor_capture_id}'."); return None, None
            selected_monitor_info = all_monitors_info[monitor_capture_id]
        except Exception as e: print(f"ScreenSamplerCore: Error accessing monitor info: {e}"); return None, None
        
        overall_pixel_bbox = ScreenSamplerCore._calculate_pixel_bounding_box_from_percentage(
            selected_monitor_info, overall_region_percentage
        )
        if not overall_pixel_bbox: return None, None

        try:
            # 1. Capture the entire user-defined region once
            sct_overall_img = sct_instance.grab(overall_pixel_bbox)
            if sct_overall_img.width == 0 or sct_overall_img.height == 0: return None, None
            
            # 2. Convert to PIL & apply R/B channel swap fix
            pil_img_raw = Image.frombytes("RGB", (sct_overall_img.width, sct_overall_img.height), sct_overall_img.rgb, "raw", "BGR")
            if pil_img_raw.mode == 'RGB': # Should always be true after frombytes
                r, g, b = pil_img_raw.split()
                pil_img_corrected_rgb = Image.merge("RGB", (b, g, r)) 
            else:
                pil_img_corrected_rgb = pil_img_raw 

            # 3. Apply S/C/B adjustments to this entire corrected image
            pil_full_preview_scb_adjusted = pil_img_corrected_rgb
            if current_adjustments['brightness'] != 1.0:
                enhancer_b = ImageEnhance.Brightness(pil_full_preview_scb_adjusted)
                pil_full_preview_scb_adjusted = enhancer_b.enhance(current_adjustments['brightness'])
            if current_adjustments['contrast'] != 1.0:
                enhancer_c = ImageEnhance.Contrast(pil_full_preview_scb_adjusted)
                pil_full_preview_scb_adjusted = enhancer_c.enhance(current_adjustments['contrast'])
            if current_adjustments['saturation'] != 1.0:
                enhancer_s = ImageEnhance.Color(pil_full_preview_scb_adjusted)
                pil_full_preview_scb_adjusted = enhancer_s.enhance(current_adjustments['saturation'])

            # (Optional: Save this full preview image for diagnosis)
            if ScreenSamplerCore._save_temp_preview_image_for_diagnosis and pil_full_preview_scb_adjusted:
                try:
                    # ... (save logic as before, name it e.g., _temp_full_scb_preview.png)
                    pass
                except: pass
            
            # 4. Subdivide, Average, and Hue Shift for each grid cell
            pad_colors_final = []
            sub_width_pil = pil_full_preview_scb_adjusted.width / ScreenSamplerCore.NUM_GRID_COLS
            sub_height_pil = pil_full_preview_scb_adjusted.height / ScreenSamplerCore.NUM_GRID_ROWS

            if sub_width_pil < 1 or sub_height_pil < 1:
                # If overall region is too small for meaningful grid, send black for all pads
                print("ScreenSamplerCore: Overall region too small for 4x16 grid. Sending black.")
                pad_colors_final = [(0,0,0)] * (ScreenSamplerCore.NUM_GRID_ROWS * ScreenSamplerCore.NUM_GRID_COLS)
                return pad_colors_final, pil_full_preview_scb_adjusted

            for r_idx in range(ScreenSamplerCore.NUM_GRID_ROWS):
                for c_idx in range(ScreenSamplerCore.NUM_GRID_COLS):
                    left = c_idx * sub_width_pil
                    top = r_idx * sub_height_pil
                    right = (c_idx + 1) * sub_width_pil
                    bottom = (r_idx + 1) * sub_height_pil
                    
                    # Ensure box coordinates are integers and within bounds of the pil_full_preview_scb_adjusted
                    # PIL's crop is forgiving but good to be explicit.
                    crop_box = (
                        int(round(left)), int(round(top)),
                        int(round(right)), int(round(bottom))
                    )
                    # Ensure crop box is valid (e.g. left < right)
                    if crop_box[0] >= crop_box[2] or crop_box[1] >= crop_box[3]:
                        pad_colors_final.append((0,0,0)) # Black for invalid sub-region
                        continue

                    sub_image_pil = pil_full_preview_scb_adjusted.crop(crop_box)

                    if sub_image_pil.width == 0 or sub_image_pil.height == 0:
                        pad_colors_final.append((0,0,0)) # Black for empty sub-region
                        continue
                    
                    # Average the sub-image
                    sub_img_np = np.array(sub_image_pil)
                    if sub_img_np.size == 0:
                        pad_colors_final.append((0,0,0)); continue
                    
                    avg_r = int(np.mean(sub_img_np[:, :, 0]))
                    avg_g = int(np.mean(sub_img_np[:, :, 1]))
                    avg_b = int(np.mean(sub_img_np[:, :, 2]))
                    
                    # Apply Hue shift to this averaged color
                    hue_shifted_color = ScreenSamplerCore._apply_hue_shift(
                        (avg_r, avg_g, avg_b),
                        current_adjustments['hue_shift']
                    )
                    pad_colors_final.append(hue_shifted_color)
            
            return pad_colors_final, pil_full_preview_scb_adjusted

        except mss.exception.ScreenShotError: pass # Usually due to invalid region, already handled by size check
        except Exception as e: print(f"ScreenSamplerCore: Error in grid sampling: {e}")
        
        # Fallback if error: return None for colors, but still return preview if available
        return None, pil_full_preview_scb_adjusted


    # --- Old capture_average_color (for single color output) - CAN BE REMOVED if not used elsewhere ---
    # For now, let's keep it commented out or decide if it's needed as a separate feature path.
    # If MainWindow always expects a list of colors now, this is redundant.
    """
    @staticmethod
    def capture_average_color(
        sct_instance, monitor_capture_id: int, region_rect_percentage: dict, 
        adjustments: dict | None = None,
        fullscreen_downscale_dimensions: tuple[int, int] = DEFAULT_FULLSCREEN_DOWNSCALE_DIMENSIONS
    ) -> tuple[tuple[int, int, int] | None, Image.Image | None]:
        # ... (previous implementation for single average color) ...
        pass 
    """

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
