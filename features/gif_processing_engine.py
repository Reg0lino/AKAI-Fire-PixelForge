# AKAI_Fire_PixelForge/features/gif_processing_engine.py
import io
import os
import requests
import numpy as np
from PIL import Image, ImageSequence, ImageEnhance

# Constants for the target pad grid
NUM_GRID_ROWS = 4
NUM_GRID_COLS = 16
PAD_BUTTON_WIDTH = 40  # From interactive_pad_grid.py
PAD_BUTTON_HEIGHT = 50  # From interactive_pad_grid.py

# Calculate the effective display aspect ratio of the entire pad grid
# This is (total_width_of_pads / total_height_of_pads)
# where total_width_of_pads = NUM_GRID_COLS * PAD_BUTTON_WIDTH
# and total_height_of_pads = NUM_GRID_ROWS * PAD_BUTTON_HEIGHT
DISPLAY_GRID_ASPECT_RATIO = (
    NUM_GRID_COLS * PAD_BUTTON_WIDTH) / (NUM_GRID_ROWS * PAD_BUTTON_HEIGHT)
# For 16x4 pads (40x50px each) -> (16*40) / (4*50) = 640 / 200 = 3.2


class GifProcessingEngine:
    """
    Handles downloading, parsing, and processing GIF frames for display on the 4x16 pads.
    Applies "Display-Aspect-Ratio-Corrected Smart Fill" and optional color adjustments.
    """

    def __init__(self):
        self.original_frames_pil: list[Image.Image] = []
        self.original_frame_delays_ms: list[int] = []
        self.original_gif_loop_count: int = 0
        self.original_gif_dimensions: tuple[int, int] = (0, 0)
        self.sequence_name: str = "Imported GIF"
        self.gif_data_in_memory: bytes | None = None

    def load_gif_from_source(self, source_path_or_url: str):
        """
        Loads a GIF from a local path or URL, extracting all frames and metadata.
        Resets previous GIF data.
        """
        # print(f"GIF_ENGINE: Attempting to load GIF from: {source_path_or_url}")
        self.original_frames_pil = []
        self.original_frame_delays_ms = []
        self.original_gif_loop_count = 0
        self.original_gif_dimensions = (0, 0)
        self.sequence_name = "Imported GIF"  # Default name
        gif_data = None
        is_url = source_path_or_url.startswith(
            'http://') or source_path_or_url.startswith('https://')
        try:
            if is_url:
                print("GIF_ENGINE: Downloading from URL...")
                response = requests.get(source_path_or_url)
                response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
                self.gif_data_in_memory = response.content
                gif_data = io.BytesIO(response.content)
                self.sequence_name = os.path.basename(
                    source_path_or_url).split('.')[0] or "Web GIF"
            else:
                # print(f"GIF_ENGINE: Loading local file: {source_path_or_url}")
                with open(source_path_or_url, 'rb') as f:
                    gif_data = io.BytesIO(f.read())
                self.sequence_name = os.path.basename(
                    source_path_or_url).split('.')[0] or "Local GIF"
            with Image.open(gif_data) as img:
                if not getattr(img, 'is_animated', False):
                    raise ValueError("Provided file is not an animated GIF.")
                self.original_gif_dimensions = img.size
                self.original_gif_loop_count = img.info.get(
                    'loop', 1)  # Default loop to 1 if not specified
                # print(
                #     f"GIF_ENGINE: Original GIF dimensions: {self.original_gif_dimensions}, Loop count: {self.original_gif_loop_count}")
                # Use ImageSequence.Iterator to correctly extract all frames
                for i, frame in enumerate(ImageSequence.Iterator(img)):
                    # Convert to RGB to handle palette GIFs and ensure consistency
                    # Make sure to copy the frame, as ImageSequence.Iterator provides a reference to the current frame.
                    self.original_frames_pil.append(
                        frame.copy().convert("RGB"))
                    # Duration is in milliseconds
                    # Default to 100ms if no duration found
                    delay = frame.info.get('duration', 100)
                    self.original_frame_delays_ms.append(delay)
                    # print(f"GIF_ENGINE: Extracted frame {i}, delay: {delay}ms")
            # If no frames found (e.g., corrupted GIF), raise an error
            if not self.original_frames_pil:
                raise ValueError(
                    "No frames could be extracted from the GIF. It might be corrupted or empty.")
            # print(
            #     f"GIF_ENGINE: Successfully extracted {len(self.original_frames_pil)} frames.")
        except requests.exceptions.RequestException as e:
            raise IOError(f"Failed to download GIF from URL: {e}")
        except FileNotFoundError as e:
            raise FileNotFoundError(f"Local GIF file not found: {e}")
        except ValueError as e:  # Catch specific ValueError from Image.open or internal checks
            raise ValueError(f"Invalid GIF file or format: {e}")
        except Exception as e:  # Catch any other unexpected errors
            import traceback
            traceback.print_exc()
            raise Exception(
                f"An unexpected error occurred while loading GIF: {e}")

    def get_first_frame_pil(self) -> Image.Image | None:
        """Returns the first original PIL frame for preview display."""
        return self.original_frames_pil[0] if self.original_frames_pil else None

    def get_original_gif_info(self) -> dict:
        """Returns metadata about the loaded GIF."""
        if not self.original_frames_pil:
            return {'frames': 0, 'width': 0, 'height': 0, 'loop': 'N/A', 'avg_delay_ms': 0, 'fps': 0.0}
        total_delay = sum(self.original_frame_delays_ms)
        frame_count = len(self.original_frame_delays_ms)
        avg_delay_ms = total_delay / frame_count if frame_count > 0 else 0
        fps = 1000 / avg_delay_ms if avg_delay_ms > 0 else 0
        # Convert loop count of 0 to the user-friendly "Infinite" display string
        loop_display = "Infinite" if self.original_gif_loop_count == 0 else str(
            self.original_gif_loop_count)
        return {
            'frames': len(self.original_frames_pil),
            'width': self.original_gif_dimensions[0],
            'height': self.original_gif_dimensions[1],
            'loop': loop_display,
            'avg_delay_ms': int(round(avg_delay_ms)),
            'fps': round(fps, 2)
        }

    def process_frames_for_pads(self,
                                region_rect_percentage: dict,
                                adjustments: dict,
                                source_frames: list[Image.Image] | None = None
                                ) -> list[tuple[list[str], int]]:
        frames_to_process = source_frames if source_frames is not None else self.original_frames_pil
        if not frames_to_process:
            return []
        processed_sequence_data = []
        for i, original_frame_pil in enumerate(frames_to_process):
            # --- Create a copy to avoid modifying the original preview frame in memory ---
            frame_to_process = original_frame_pil.copy()
            orig_w, orig_h = frame_to_process.size
            crop_x = int(region_rect_percentage['x'] * orig_w)
            crop_y = int(region_rect_percentage['y'] * orig_h)
            crop_w = int(region_rect_percentage['width'] * orig_w)
            crop_h = int(region_rect_percentage['height'] * orig_h)
            crop_w = max(1, crop_w)
            crop_h = max(1, crop_h)
            cropped_frame = frame_to_process.crop(
                (crop_x, crop_y, crop_x + crop_w, crop_y + crop_h))
            final_pad_image_pil = cropped_frame.resize(
                (NUM_GRID_COLS, NUM_GRID_ROWS), resample=Image.Resampling.LANCZOS)
            if adjustments.get('brightness', 1.0) != 1.0:
                enhancer = ImageEnhance.Brightness(final_pad_image_pil)
                final_pad_image_pil = enhancer.enhance(
                    adjustments['brightness'])
            if adjustments.get('contrast', 1.0) != 1.0:
                enhancer = ImageEnhance.Contrast(final_pad_image_pil)
                final_pad_image_pil = enhancer.enhance(adjustments['contrast'])
            if adjustments.get('saturation', 1.0) != 1.0:
                enhancer = ImageEnhance.Color(final_pad_image_pil)
                final_pad_image_pil = enhancer.enhance(
                    adjustments['saturation'])
            img_np = np.array(final_pad_image_pil.convert("RGB"))
            pad_colors_rgb_tuples = [tuple(p) for p in img_np.reshape(-1, 3)]
            hue_shift_degrees = adjustments.get('hue_shift', 0)
            if hue_shift_degrees != 0:
                pad_colors_final_rgb = [self._apply_hue_shift(
                    c, hue_shift_degrees) for c in pad_colors_rgb_tuples]
            else:
                pad_colors_final_rgb = pad_colors_rgb_tuples
            pad_colors_hex = ['#{:02x}{:02x}{:02x}'.format(
                r, g, b) for r, g, b in pad_colors_final_rgb]
            delay = self.original_frame_delays_ms[i] if i < len(
                self.original_frame_delays_ms) else 100
            processed_sequence_data.append((pad_colors_hex, delay))
        return processed_sequence_data

    @staticmethod
    def _apply_hue_shift(rgb_tuple: tuple[int, int, int], hue_shift_degrees: int) -> tuple[int, int, int]:
        """Applies hue shift to an RGB tuple. (Copied from ScreenSamplerCore)"""
        import colorsys  # Local import to avoid circular dependency / keep function self-contained
        if hue_shift_degrees == 0:
            return rgb_tuple
        r_norm, g_norm, b_norm = rgb_tuple[0] / \
            255.0, rgb_tuple[1]/255.0, rgb_tuple[2]/255.0
        h, s, v = colorsys.rgb_to_hsv(r_norm, g_norm, b_norm)
        h_shifted = (h + (hue_shift_degrees / 360.0)) % 1.0
        if h_shifted < 0:
            h_shifted += 1.0
        r_fin_norm, g_fin_norm, b_fin_norm = colorsys.hsv_to_rgb(
            h_shifted, s, v)
        return (int(r_fin_norm*255), int(g_fin_norm*255), int(b_fin_norm*255))