# In a new file: managers/color_fx_utils.py

import colorsys
from PyQt6.QtGui import QColor


def apply_fx_filter(source_colors_hex: list[str], fx_params: dict) -> list[str]:
    """
    A standalone utility function that applies a dictionary of FX parameters
    to a list of hex color strings and returns the new list.
    """
    brightness_adj = fx_params.get('brightness', 0)
    saturation_adj = fx_params.get('saturation', 0)
    contrast_adj = fx_params.get('contrast', 0)
    hue_shift = fx_params.get('hue_shift', 0.0)

    brightness_factor = 1.0 + (brightness_adj / 100.0)
    saturation_factor = 1.0 + (saturation_adj / 100.0)
    contrast_factor = 1.0 + (contrast_adj / 100.0)

    modified_colors_hex = []
    for hex_str in source_colors_hex:
        if not hex_str:
            modified_colors_hex.append("#000000")
            continue

        try:
            color = QColor(hex_str)
            if not color.isValid():
                modified_colors_hex.append("#000000")
                continue

            r, g, b, a_val = color.redF(), color.greenF(), color.blueF(), color.alphaF()

            # 1. Apply Brightness and Contrast in RGB space
            r, g, b = r * brightness_factor, g * brightness_factor, b * brightness_factor
            if contrast_factor != 1.0:
                r = 0.5 + contrast_factor * (r - 0.5)
                g = 0.5 + contrast_factor * (g - 0.5)
                b = 0.5 + contrast_factor * (b - 0.5)

            # CLAMP before HSV conversion
            r, g, b = max(0.0, min(1.0, r)), max(
                0.0, min(1.0, g)), max(0.0, min(1.0, b))

            # 2. Convert to HSV for Saturation and Hue
            h, s, v = colorsys.rgb_to_hsv(r, g, b)

            # 3. Apply Saturation and Hue
            s *= saturation_factor
            s = max(0.0, min(1.0, s))

            if hue_shift != 0:
                h += (hue_shift / 360.0)
                h %= 1.0  # Use modulo for clean wrapping

            # 4. Convert back and finalize
            final_r, final_g, final_b = colorsys.hsv_to_rgb(h, s, v)
            final_color = QColor.fromRgbF(final_r, final_g, final_b, a_val)
            modified_colors_hex.append(final_color.name())
        except Exception:
            # Fallback to original color on error
            modified_colors_hex.append(hex_str)

    return modified_colors_hex
