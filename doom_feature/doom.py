import random # Ensure random is imported at the top of your script
import math   # Ensure math is imported

class MapGenerator:
    def __init__(self, width: int, height: int):
        # Ensure width and height are odd to allow for wall borders and even path carving
        self.width = width if width % 2 != 0 else width - 1
        self.height = height if height % 2 != 0 else height - 1
        if self.width < 5: self.width = 5 # Minimum practical size
        if self.height < 5: self.height = 5

        self.map_grid = [] # Will be list of lists (rows) of integers (0=floor, 1=wall, 2=exit, S=start)
        self.player_start_coords_map = None # (col, row) in map_grid terms
        self.player_start_angle_rad = 0     # Suggested starting angle
        self.enemy_spawn_candidates = []    # List of (col, row) for potential enemy spawns
        self.exit_coords_map = None         # (col, row) for exit

    def _is_valid(self, r: int, c: int, check_bounds_only=False) -> bool:
        """Checks if (r,c) is within map boundaries and optionally if it's a wall (for carving)."""
        if not (0 <= r < self.height and 0 <= c < self.width):
            return False
        if check_bounds_only:
            return True
        return self.map_grid[r][c] == 1 # For carving, check if it's a wall we can carve into

    def generate_maze(self):
        # Initialize grid with all walls
        self.map_grid = [[1 for _ in range(self.width)] for _ in range(self.height)]
        self.enemy_spawn_candidates = []

        # Choose a random starting cell (must be odd coordinates to ensure path carving works with step 2)
        # For player start, let's pick something consistent near a corner for now, e.g., (1,1)
        start_r, start_c = 1, 1 
        self.player_start_coords_map = (start_c, start_r) # Store as (col, row) for consistency with game coords later
        
        self.map_grid[start_r][start_c] = 0 # Carve out player start
        self.enemy_spawn_candidates.append((start_c, start_r)) # Player start is a floor tile

        stack = [(start_r, start_c)]
        
        first_carve_direction_vector = None

        while stack:
            current_r, current_c = stack[-1]
            neighbors = []

            # Check potential neighbors (2 cells away)
            # (dr, dc, wall_dr, wall_dc, angle_suggestion_if_first_move)
            # angle_suggestion: 0=Right, PI/2=Down, PI=Left, -PI/2=Up
            possible_moves = [
                (0, 2, 0, 1, 0),         # Right
                (0, -2, 0, -1, math.pi), # Left
                (2, 0, 1, 0, math.pi / 2), # Down
                (-2, 0, -1, 0, -math.pi / 2) # Up
            ]
            random.shuffle(possible_moves)

            moved = False
            for dr, dc, wall_dr, wall_dc, angle_sugg in possible_moves:
                next_r, next_c = current_r + dr, current_c + dc
                wall_r, wall_c = current_r + wall_dr, current_c + wall_dc

                if self._is_valid(next_r, next_c) and self.map_grid[next_r][next_c] == 1: # Check if next cell is a wall to carve
                    self.map_grid[wall_r][wall_c] = 0 # Carve wall between
                    self.map_grid[next_r][next_c] = 0 # Carve next cell
                    self.enemy_spawn_candidates.append((wall_c, wall_r))
                    self.enemy_spawn_candidates.append((next_c, next_r))

                    if (current_r, current_c) == (start_r, start_c) and first_carve_direction_vector is None:
                        self.player_start_angle_rad = angle_sugg
                        first_carve_direction_vector = (dc, dr) # Store direction of first move

                    stack.append((next_r, next_c))
                    moved = True
                    break
            
            if not moved:
                stack.pop()
        
        # Ensure the very outer border is always a wall (defensive)
        for r in range(self.height):
            self.map_grid[r][0] = 1
            self.map_grid[r][self.width - 1] = 1
        for c in range(self.width):
            self.map_grid[0][c] = 1
            self.map_grid[self.height - 1][c] = 1
        
        # Remove duplicates from enemy spawn candidates
        self.enemy_spawn_candidates = list(set(self.enemy_spawn_candidates))


    def get_map_as_text_list(self, num_enemies=5) -> list[str]:
        """Converts the generated grid to the text list format, placing S, I, E."""
        text_map = [["#" for _ in range(self.width)] for _ in range(self.height)]

        # Place floor tiles
        for r in range(self.height):
            for c in range(self.width):
                if self.map_grid[r][c] == 0:
                    text_map[r][c] = "."
        
        # Place Player Start 'S'
        if self.player_start_coords_map:
            pc, pr = self.player_start_coords_map
            if 0 <= pr < self.height and 0 <= pc < self.width:
                text_map[pr][pc] = "S"
                # Remove player start from enemy spawn candidates
                if (pc,pr) in self.enemy_spawn_candidates:
                    self.enemy_spawn_candidates.remove((pc,pr))

        # Place Exit 'E' - find a floor tile furthest from player start
        # For simplicity, we'll just pick a random valid floor tile for now,
        # ensuring it's not the player start. More complex logic for "furthest" can be added.
        valid_exit_candidates = [
            (c,r) for c,r in self.enemy_spawn_candidates if (c,r) != self.player_start_coords_map
        ]
        if valid_exit_candidates:
            # Attempt to place exit somewhat far from player
            best_exit_candidate = None
            max_dist_sq = -1
            if self.player_start_coords_map:
                px_s, py_s = self.player_start_coords_map
                for ex_c, ex_r in valid_exit_candidates:
                    dist_sq = (ex_c - px_s)**2 + (ex_r - py_s)**2
                    if dist_sq > max_dist_sq:
                        max_dist_sq = dist_sq
                        best_exit_candidate = (ex_c, ex_r)
            if best_exit_candidate:
                self.exit_coords_map = best_exit_candidate
                text_map[self.exit_coords_map[1]][self.exit_coords_map[0]] = "E"
                if self.exit_coords_map in self.enemy_spawn_candidates: # Remove from enemy list
                    self.enemy_spawn_candidates.remove(self.exit_coords_map)


        # Place Enemies 'I' - use _has_line_of_sight from RaycasterEngine instance
        # This part is tricky as MapGenerator doesn't have the engine instance.
        # For now, we'll just mark candidate spots. The RaycasterEngine will handle LOS check.
        # Or, we can pass the LOS check function if MapGenerator becomes more independent.
        
        # Let's return the text_map and let RaycasterEngine place Imps
        # from self.enemy_spawn_candidates after doing its own LOS check.

        return ["".join(row) for row in text_map]
    
from PyQt6.QtGui import QKeyEvent, QFont, QColor
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QObject
from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QComboBox, QMessageBox
import sys
import os
import math
import time
from PIL import Image, ImageDraw, ImageFont  # Ensure ImageFont is imported
import random

# --- Add project root to sys.path for standalone execution ---
CURRENT_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CURRENT_SCRIPT_DIR)

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
print(f"INFO: Added to sys.path: {PROJECT_ROOT}")

# --- Module Imports & Checks ---
RAYCASTER_ENGINE_DEFINED = False
AKAI_FIRE_CONTROLLER_LOADED = False
OLED_RENDERER_LOADED_OK = False
HARDWARE_INPUT_MANAGER_LOADED = False

try:
    from hardware.akai_fire_controller import AkaiFireController, FIRE_BUTTON_PLAY
    AKAI_FIRE_CONTROLLER_LOADED = True
    print("INFO: AkaiFireController imported successfully.")
except ImportError as e_afc:
    print(f"ERROR: Could not import AkaiFireController: {e_afc}")
    FIRE_BUTTON_PLAY = 0x33  # Default MIDI note for physical PLAY button if import fails

    class AkaiFireController:  # Dummy class if import fails
        def __init__(self, *args, **
                    kwargs): print("DUMMY AkaiFireController instantiated")

        def connect(self, *args, **kwargs):
            print("DUMMY AkaiFireController: connect called")
            return False

        def is_connected(self): return False
        def oled_send_full_bitmap(self, *args, **kwargs): pass
        def set_pad_color(self, r, c, r_val, g_val, b_val): pass

        def set_multiple_pads_color(
            self, data_list, bypass_global_brightness=False): pass

        def disconnect(self): print(
            "DUMMY AkaiFireController: disconnect called")

        @staticmethod
        def get_available_output_ports(): print("DUMMY AkaiFireController: get_available_output_ports called"); return [
            "Error: Controller Mod Not Loaded"]

        @staticmethod
        def get_available_input_ports(): print("DUMMY AkaiFireController: get_available_input_ports called"); return [
            "Error: Controller Mod Not Loaded"]
    # Ensure flag is correctly set if dummy is used
    AKAI_FIRE_CONTROLLER_LOADED = False


try:
    from oled_utils import oled_renderer
    OLED_RENDERER_LOADED_OK = True
    print("INFO: oled_renderer imported successfully.")
except ImportError as e_oled:
    print(f"ERROR: Could not import oled_renderer: {e_oled}")

    class oled_renderer:  # Dummy class if import fails
        OLED_WIDTH = 128
        OLED_HEIGHT = 64
        @staticmethod
        def pack_pil_image_to_7bit_stream(pil_image): return None
        @staticmethod
        def get_blank_packed_bitmap(): return bytearray(1176)

        @staticmethod
        def resource_path_func(relative_path): return os.path.join(
            PROJECT_ROOT, relative_path)  # Dummy for RaycasterEngine font loading
    # Ensure flag is correctly set if dummy is used
    OLED_RENDERER_LOADED_OK = False

try:
    from managers.hardware_input_manager import HardwareInputManager
    HARDWARE_INPUT_MANAGER_LOADED = True
    print("INFO: HardwareInputManager class imported successfully.")
except ImportError as e_him:
    print(f"ERROR: Could not import HardwareInputManager class: {e_him}")

    class HardwareInputManager:  # Dummy class if import fails
        def __init__(self, *args, **
                    kwargs): print("DUMMY HardwareInputManager instantiated")
    # Ensure flag is correctly set if dummy is used
    HARDWARE_INPUT_MANAGER_LOADED = False


CRITICAL_MODULES_LOADED = AKAI_FIRE_CONTROLLER_LOADED and OLED_RENDERER_LOADED_OK and HARDWARE_INPUT_MANAGER_LOADED


# --- Game Configuration ---
SCREEN_WIDTH = 128
SCREEN_HEIGHT = 64
TARGET_FPS = 15  # Target ~15-20 FPS
FOV_rad = math.pi / 2.8  # Field of View in radians
MAX_RAY_DEPTH = 20    # Max distance for raycasting
PLAYER_MAX_HP = 4
ENEMY_MAX_HP = 4

# --- Pad Control Note Definitions ---
# These are the MIDI notes your Akai Fire sends for the pads you want to use
PAD_DOOM_FORWARD = 55       # Red
PAD_DOOM_BACKWARD = 71      # Red
PAD_DOOM_STRAFE_LEFT = 70   # Orange (WASD-like Strafe)
PAD_DOOM_STRAFE_RIGHT = 72  # Orange (WASD-like Strafe)
PAD_DOOM_TURN_LEFT_MAIN = 54  # Red (Main Turn)
PAD_DOOM_TURN_RIGHT_MAIN = 56  # Red (Main Turn)
PAD_DOOM_RUN = 84           # Blue
PAD_DOOM_SHOOT = 85         # Green (also Restart Button Visual)
PAD_DOOM_TURN_LEFT_ALT = 68  # Orange (Alt Turn)
PAD_DOOM_TURN_RIGHT_ALT = 69  # Orange (Alt Turn)

# Physical Play button (0x33 / 51) for triggering restart initially (will be changed)
# Note: This RESTART_PAD_TRIGGER_NOTE will be updated to PAD_DOOM_SHOOT in upcoming steps.
RESTART_PAD_TRIGGER_NOTE = FIRE_BUTTON_PLAY  # placeholder for now

# --- Pad Color Definitions ---
PAD_COLOR_DPAD_RED = (200, 0, 0)
PAD_COLOR_ORANGE = (255, 100, 0)
PAD_COLOR_BLUE_RUN = (0, 100, 255)
PAD_COLOR_SHOOT_GREEN = (0, 200, 0)  # Used for Shoot and Blinking Restart
PAD_COLOR_OFF = (0, 0, 0)
PAD_COLOR_HEALTH_RED = (200, 0, 0)  # Bright Red for active HP segments
PAD_COLOR_HIT_FLASH_RED = (255, 0, 0)  # For player hit effect

# --- RaycasterEngine Class Definition ---
class RaycasterEngine(QObject):
    player_took_damage_signal = pyqtSignal() # Emitted when player HP decreases

    def __init__(self, screen_width=SCREEN_WIDTH, screen_height=SCREEN_HEIGHT, parent=None):
        super().__init__(parent)
        self.screen_width = screen_width
        self.screen_height = screen_height
        # --- MAP GENERATION ---
        # Define map dimensions for the generator (must be odd for this generator)
        # Max size should consider performance. 15x9 or 17x11 is a good start.
        # Let's use slightly larger than original hardcoded for more space.
        # Max size could be like 31x21 for a really big maze, but start smaller.
        map_gen_width = 17  # e.g., 15, 17, 19...
        map_gen_height = 11 # e.g., 9, 11, 13...
        self.map_generator = MapGenerator(map_gen_width, map_gen_height)
        self.map_generator.generate_maze()
        self.game_map_text_initial = self.map_generator.get_map_as_text_list() # Get initial map
        # Player start angle is now suggested by the map generator
        self.player_angle_rad = self.map_generator.player_start_angle_rad
        # Player x,y will be set by 'S' in _parse_map_and_init_state
        self.game_map_tiles = [] 
        self.player_x = 1.5 # Default, will be overridden by 'S'
        self.player_y = 1.5 # Default
        self.player_hp = PLAYER_MAX_HP
        self.player_hit_animation_timer = 0 
        self.player_hit_animation_frames = 3 
        self.fov_rad = FOV_rad
        self.max_ray_depth = MAX_RAY_DEPTH
        self.base_move_speed = 0.15
        self.run_speed_multiplier = 1.8
        self.current_move_speed = self.base_move_speed
        self.turn_speed = math.pi / 10 
        self.is_running = False
        self.current_frame_image = Image.new('1', (self.screen_width, self.screen_height), 0) 
        self.draw_context = ImageDraw.Draw(self.current_frame_image)
        self.gun_y_offset = 2 
        self.gun_sprite_idle_data = { # Unchanged
            "width": 20, "height": 14,
            "pixels": [ 
                "00000000000000000000", "00000001111110000000", "00000011111111000000",
                "00000111000011100000", "00001100000000110000", "00011000000000011000",
                "00111111111111111100", "01100000000000000110", "01100000000000000110",
                "01100000000000000110", "00111000000000111000", "0000111111111100000",
                "0000011111111000000", "00000000000000000000",
            ]
        }
        self.gun_sprite_fire_data = { # Unchanged
            "width": 26, "height": 18,
            "pixels": [
                "00000000000000000000000000", "00000000000110000000000000", "00000000011111100000000000",
                "00000001111111111000000000", "00000111110001111100000000", "00001111000000111100000000",
                "00001100000000001100000000", "0001100000000000011000000", "001111111111111111110000",
                "0110000000000000000110000", "0110000000000000000110000", "0110000000000000000110000",
                "0011100000000000111000000", "0000111111111111000000000", "0000011111111100000000000",
                "00000000000000000000000000", "00000000000000000000000000", "00000000000000000000000000",
            ]
        }
        self.gun_fire_animation_frames = 2 
        self.gun_fire_timer = 0
        self.hardcoded_enemy_pixels = [ # Using the more detailed 9x12 definition
            [0,0,0,1,1,1,0,0,0], [0,0,1,1,1,1,1,0,0], [0,0,1,1,1,1,1,0,0], 
            [0,0,0,1,1,1,0,0,0], [0,1,1,1,1,1,1,1,0], [1,1,0,1,1,1,0,1,1], 
            [0,0,0,1,1,1,0,0,0], [0,0,0,1,1,1,0,0,0], [0,0,1,0,0,0,1,0,0], 
            [0,1,1,0,0,0,1,1,0], [1,1,0,0,0,0,0,1,1], [1,0,0,0,0,0,0,0,1]  
        ]
        if self.hardcoded_enemy_pixels and len(self.hardcoded_enemy_pixels) > 0 and \
            isinstance(self.hardcoded_enemy_pixels[0], list):
            self.hardcoded_enemy_width = len(self.hardcoded_enemy_pixels[0])
        else:
            self.hardcoded_enemy_width = 0 
        self.hardcoded_enemy_height = len(self.hardcoded_enemy_pixels)
        self.sprites = [] 
        self._parse_map_and_init_state() # Initial parse using the generated map
        self.z_buffer = [float('inf')] * self.screen_width 
        self.game_message = "" 
        self.game_over = False
        self.game_won = False
        self.message_font = ImageFont.load_default() 
        try:
            if OLED_RENDERER_LOADED_OK and hasattr(oled_renderer, 'resource_path_func'):
                font_path = oled_renderer.resource_path_func(os.path.join("resources", "fonts", "TomThumb.ttf"))
                if os.path.exists(font_path):
                    self.message_font = ImageFont.truetype(font_path, 48) 
            if not self.message_font or isinstance(self.message_font, str): 
                self.message_font = ImageFont.truetype("arial.ttf", 24)
        except Exception:
            self.message_font = ImageFont.load_default()

    def _parse_map_and_init_state(self, num_enemies_to_place=5): # Added enemy count
        # If called on reset, regenerate the map
        if hasattr(self, 'map_generator'): # Check if map_generator exists (it should from __init__)
            self.map_generator.generate_maze()
            self.game_map_text_initial = self.map_generator.get_map_as_text_list()
            self.player_angle_rad = self.map_generator.player_start_angle_rad # Get new suggested angle
            # Player x,y will be re-parsed from 'S' below
        else: # Fallback if map_generator somehow not initialized (should not happen)
            print("WARNING: map_generator not found in _parse_map_and_init_state, using existing map text.")
        self.game_map_tiles = []
        self.sprites = [] 
        player_start_found = False
        temp_enemy_spawn_candidates = [] # From the '.' tiles
        for r_idx, row_str in enumerate(self.game_map_text_initial):
            map_row_tiles = []
            for c_idx, char_val in enumerate(row_str):
                tile_type = 0 
                if char_val == '#':
                    tile_type = 1 
                elif char_val == 'S':
                    self.player_x = c_idx + 0.5 
                    self.player_y = r_idx + 0.5
                    player_start_found = True
                    tile_type = 0 
                elif char_val == 'E': # Exit is now just a normal floor tile visually unless rendered differently
                    tile_type = 2 # Still mark it as type 2 for potential different rendering
                    temp_enemy_spawn_candidates.append((c_idx, r_idx)) # Exit can be a spawn candidate if not used as exit
                elif char_val == '.': # Empty floor, potential enemy spawn
                    tile_type = 0
                    temp_enemy_spawn_candidates.append((c_idx, r_idx))
                # 'I' characters from the map generator's output are ignored here;
                # we will place enemies based on LOS and spawn candidates.
                map_row_tiles.append(tile_type)
            self.game_map_tiles.append(map_row_tiles)
        if not player_start_found: 
            # This should ideally not happen if MapGenerator places 'S'
            print("CRITICAL WARNING: Player start 'S' not found in generated map. Defaulting player position.")
            self.player_x = 1.5 # Fallback
            self.player_y = 1.5 # Fallback
            # Attempt to find a valid floor tile if S is missing
            for r in range(len(self.game_map_tiles)):
                for c in range(len(self.game_map_tiles[0])):
                    if self.game_map_tiles[r][c] == 0:
                        self.player_x, self.player_y = c + 0.5, r + 0.5
                        player_start_found = True; break
                if player_start_found: break
            if not player_start_found: # Still no floor tile, something is very wrong
                self.player_x, self.player_y = 1.5,1.5 # Last resort
        self.map_height = len(self.game_map_tiles)
        self.map_width = len(self.game_map_tiles[0]) if self.map_height > 0 else 0
        # --- Place Enemies with LOS Check ---
        random.shuffle(temp_enemy_spawn_candidates) # Shuffle to get random placement
        enemies_placed = 0
        for spawn_c, spawn_r in temp_enemy_spawn_candidates:
            if enemies_placed >= num_enemies_to_place:
                break
            
            # Ensure spawn point is not player's current tile (even if 'S' was overwritten)
            if int(self.player_x) == spawn_c and int(self.player_y) == spawn_r:
                continue
            # Check LOS from this candidate spawn point to player's actual start
            # Use a slightly shorter distance for LOS check than typical enemy sight range
            # to ensure they aren't *immediately* aggressive or visible.
            if not self._has_line_of_sight(spawn_c + 0.5, spawn_r + 0.5, 
                                            self.player_x, self.player_y, 
                                            max_los_distance=5.0): # Max distance for initial non-LOS
                self.sprites.append({
                    "x": spawn_c + 0.5, "y": spawn_r + 0.5, 
                    "type": "imp", 
                    "id": f"imp_gen_{spawn_r}_{spawn_c}", 
                    "width_def": self.hardcoded_enemy_width,    
                    "height_def": self.hardcoded_enemy_height,
                    "pixels_def": self.hardcoded_enemy_pixels,  
                    "height_factor": 0.7, 
                    "state": "idle", "health": ENEMY_MAX_HP,
                    "target_x": spawn_c + 0.5, "target_y": spawn_r + 0.5, 
                    "move_timer": random.randint(TARGET_FPS, TARGET_FPS * 3), 
                    "shoot_timer": random.randint(TARGET_FPS * 2, TARGET_FPS * 4) 
                })
                enemies_placed += 1
        if enemies_placed < num_enemies_to_place:
            print(f"WARNING: Could only place {enemies_placed}/{num_enemies_to_place} enemies with no initial LOS.")
        # --- End Enemy Placement ---
        self.player_hp = PLAYER_MAX_HP
        self.game_message = ""
        self.game_over = False
        self.game_won = False
        self.player_hit_animation_timer = 0
        self.gun_fire_timer = 0
        print(f"INFO: Game state initialized/reset with procedurally generated map ({self.map_width}x{self.map_height}). Player angle: {self.player_angle_rad:.2f} rad. Enemies: {enemies_placed}")

    def update_ai_and_game_state(self):
        if self.game_over:  # If game is already over, do nothing
            return
        # Enemy AI (Imps)
        for i, sprite in reversed(list(enumerate(self.sprites))):
            if sprite["type"] == "imp" and sprite["state"] != "dead":
                sprite["move_timer"] -= 1
                sprite["shoot_timer"] -= 1
                # Simple random jitter movement
                if sprite["move_timer"] <= 0:
                    sprite["move_timer"] = random.randint(
                        TARGET_FPS, TARGET_FPS * 3)
                    rand_offset_x, rand_offset_y = (
                        random.random() - 0.5) * 0.8, (random.random() - 0.5) * 0.8
                    new_sprite_x, new_sprite_y = sprite["x"] + \
                        rand_offset_x, sprite["y"] + rand_offset_y
                    map_tile_x, map_tile_y = int(
                        new_sprite_x), int(new_sprite_y)
                    if 0 <= map_tile_x < self.map_width and \
                        0 <= map_tile_y < self.map_height and \
                        self.game_map_tiles[map_tile_y][map_tile_x] == 0:
                        sprite["x"], sprite["y"] = new_sprite_x, new_sprite_y
                # Shooting logic with Line-of-Sight
                if sprite["shoot_timer"] <= 0:
                    sprite["shoot_timer"] = random.randint(
                        TARGET_FPS * 2, TARGET_FPS * 4)
                    dist_to_player = math.sqrt(
                        (self.player_x - sprite["x"])**2 + (self.player_y - sprite["y"])**2)
                    can_shoot_player = False
                    # Check distance first (shooting range)
                    if dist_to_player < 7.0:
                        if self._has_line_of_sight(sprite["x"], sprite["y"], self.player_x, self.player_y, dist_to_player + 0.1):
                            if random.random() < 0.35:
                                can_shoot_player = True
                    if can_shoot_player:
                        print(
                            f"Imp {sprite.get('id', 'unknown')} shoots at player (LOS confirmed)!")
                        self.player_hp -= 1
                        self.player_hit_animation_timer = self.player_hit_animation_frames
                        self.player_took_damage_signal.emit()
                        if self.player_hp <= 0:
                            self.player_hp = 0
                            self.game_message = "YOU DIED"
                            self.game_over = True
                            self.game_won = False
                            print("GAME OVER - Player Died")
                            return  # Stop further updates if game over
        # --- MODIFIED WIN CONDITION ---
        # Check if all enemies of type "imp" are dead.
        # The 'E' tile is no longer part of the win condition.
        imps_alive = any(s["type"] == "imp" and s.get(
            "state") != "dead" for s in self.sprites)
        if not imps_alive:  # If no imps are alive
            # Check if there were any imps to begin with to prevent winning on an empty map instantly
            # This assumes sprites are populated from the map. If map can be empty of 'I', this is fine.
            # For a more robust check, you could see if self.sprites ever contained an "imp".
            # However, for this game, if the map parsing correctly adds imps, this is sufficient.
            # Check if any imps were ever on the map
            initial_imps_existed = any(
                s["type"] == "imp" for s in self.sprites)
            if initial_imps_existed:  # Only win if there were imps to kill
                self.game_message = "YOU WIN!"
                self.game_over = True
                self.game_won = True
                print("GAME OVER - Player Won! (All Imps Defeated)")
        # Note: The old player_on_exit check has been removed from the win condition.
        # The 'E' tile in the map will now just be a normal empty space unless you give it other properties.

    def _render_to_internal_buffer(self):
        for i in range(self.screen_width): self.z_buffer[i] = float('inf')
        self.draw_context.rectangle([(0,0), (self.screen_width, self.screen_height)], fill=0)
        for x in range(self.screen_width):
            camera_x = (2 * x / self.screen_width) - 1 
            ray_angle = self.player_angle_rad + math.atan(camera_x * math.tan(self.fov_rad / 2.0)) 
            ray_dir_x, ray_dir_y = math.cos(ray_angle), math.sin(ray_angle)
            map_check_x, map_check_y = int(self.player_x), int(self.player_y)
            delta_dist_x = abs(1 / ray_dir_x) if ray_dir_x != 0 else float('inf')
            delta_dist_y = abs(1 / ray_dir_y) if ray_dir_y != 0 else float('inf')
            step_x, step_y = 0, 0
            side_dist_x, side_dist_y = 0.0, 0.0
            if ray_dir_x < 0:
                step_x = -1
                side_dist_x = (self.player_x - map_check_x) * delta_dist_x
            else:
                step_x = 1
                side_dist_x = (map_check_x + 1.0 - self.player_x) * delta_dist_x
            if ray_dir_y < 0:
                step_y = -1
                side_dist_y = (self.player_y - map_check_y) * delta_dist_y
            else:
                step_y = 1
                side_dist_y = (map_check_y + 1.0 - self.player_y) * delta_dist_y
            hit_wall, side_hit = False, 0 
            wall_type_hit = 0
            for _ in range(self.max_ray_depth * max(self.map_width, self.map_height)): 
                if side_dist_x < side_dist_y:
                    side_dist_x += delta_dist_x
                    map_check_x += step_x
                    side_hit = 0 
                else:
                    side_dist_y += delta_dist_y
                    map_check_y += step_y
                    side_hit = 1 
                if not (0 <= map_check_x < self.map_width and 0 <= map_check_y < self.map_height):
                    break 
                wall_type_hit = self.game_map_tiles[map_check_y][map_check_x]
                if wall_type_hit == 1: 
                    hit_wall = True
                    break
            if hit_wall:
                perp_wall_dist = 0.0
                if side_hit == 0: 
                    perp_wall_dist = (map_check_x - self.player_x + (1 - step_x) / 2) / ray_dir_x if ray_dir_x != 0 else float('inf')
                else: 
                    perp_wall_dist = (map_check_y - self.player_y + (1 - step_y) / 2) / ray_dir_y if ray_dir_y != 0 else float('inf')
                if perp_wall_dist <= 0.01: perp_wall_dist = 0.01 
                self.z_buffer[x] = perp_wall_dist 
                line_height = int(self.screen_height / perp_wall_dist)
                draw_start_y = int(-line_height / 2 + self.screen_height / 2)
                draw_end_y = int(line_height / 2 + self.screen_height / 2)
                if draw_start_y < 0: draw_start_y = 0
                if draw_end_y >= self.screen_height: draw_end_y = self.screen_height - 1
                if side_hit == 1: 
                    self.draw_context.line([(x, draw_start_y), (x, draw_end_y)], fill=255, width=1)
                else: 
                    for y_coord in range(draw_start_y, draw_end_y + 1):
                        if (x + y_coord) % 2 == 0: 
                            self.draw_context.point((x, y_coord), fill=255)

    def _render_sprites(self):
        if not self.sprites:
            return
        visible_sprites = [s for s in self.sprites if s.get("state") != "dead"]
        if not visible_sprites:
            return
        sorted_sprites = sorted(
            visible_sprites,
            key=lambda s: math.sqrt((s["x"] - self.player_x)**2 + (s["y"] - self.player_y)**2),
            reverse=True
        )
        for sprite in sorted_sprites:
            is_hardcoded_render_candidate = (sprite.get("type") == "imp" and 
                                            sprite.get("pixels_def") is not None)
            
            if not is_hardcoded_render_candidate: 
                continue 
            sprite_x_rel, sprite_y_rel = sprite["x"] - self.player_x, sprite["y"] - self.player_y
            angle_to_sprite = math.atan2(sprite_y_rel, sprite_x_rel)
            angle_diff = angle_to_sprite - self.player_angle_rad
            
            while angle_diff < -math.pi: angle_diff += 2 * math.pi
            while angle_diff > math.pi: angle_diff -= 2 * math.pi
            if abs(angle_diff) > (self.fov_rad / 1.8):
                continue
            sprite_dist = math.sqrt(sprite_x_rel**2 + sprite_y_rel**2)
            if sprite_dist < 0.5:
                continue
            try:
                sprite_screen_x = int((self.screen_width / 2) * (1 + math.tan(angle_diff) / math.tan(self.fov_rad / 2)))
            except ZeroDivisionError:
                continue
            
            base_sprite_height_def = sprite.get("height_def", 1) 
            if base_sprite_height_def == 0: base_sprite_height_def = 1 
            
            sprite_pixel_height_on_screen = int((self.screen_height / sprite_dist) * sprite.get('height_factor', 1.0))
            if sprite_pixel_height_on_screen <= 0:
                continue
            scale_factor_for_def_pixel = sprite_pixel_height_on_screen / base_sprite_height_def
            
            base_sprite_width_def = sprite.get("width_def", 1)
            sprite_pixel_width_on_screen = int(base_sprite_width_def * scale_factor_for_def_pixel)
            if sprite_pixel_width_on_screen <= 0:
                continue
            
            draw_start_y_sprite = int((self.screen_height - sprite_pixel_height_on_screen) / 2)
            draw_start_x_sprite = sprite_screen_x - (sprite_pixel_width_on_screen // 2)
            if sprite_pixel_width_on_screen > 0 and sprite_pixel_height_on_screen > 0:
                try:
                    sprite_definition_pixels = sprite.get("pixels_def")
                    if not sprite_definition_pixels:
                        continue
                    outline_offsets = [
                        (-1, -1), (0, -1), (1, -1),
                        (-1,  0),          (1,  0),
                        (-1,  1), (0,  1), (1,  1)
                    ]
                    outline_color_fill = 255 
                    body_color_fill = 0      
                    body_pixels_drawn_on_screen = set()
                    for def_y in range(len(sprite_definition_pixels)):        
                        for def_x in range(len(sprite_definition_pixels[0])): 
                            if sprite_definition_pixels[def_y][def_x] == 1: 
                                screen_px_start_x = draw_start_x_sprite + int(def_x * scale_factor_for_def_pixel)
                                screen_px_end_x   = draw_start_x_sprite + int((def_x + 1) * scale_factor_for_def_pixel) -1
                                screen_px_start_y = draw_start_y_sprite + int(def_y * scale_factor_for_def_pixel)
                                screen_px_end_y   = draw_start_y_sprite + int((def_y + 1) * scale_factor_for_def_pixel) -1
                                for current_screen_x in range(screen_px_start_x, screen_px_end_x + 1):
                                    if 0 <= current_screen_x < self.screen_width:
                                        if sprite_dist < self.z_buffer[current_screen_x]: 
                                            for current_screen_y in range(screen_px_start_y, screen_px_end_y + 1):
                                                if 0 <= current_screen_y < self.screen_height:
                                                    self.draw_context.point((current_screen_x, current_screen_y), fill=body_color_fill)
                                                    body_pixels_drawn_on_screen.add((current_screen_x, current_screen_y))
                    
                    pixels_for_outline_pass = list(body_pixels_drawn_on_screen) 
                    for (body_x, body_y) in pixels_for_outline_pass:
                        for off_x, off_y in outline_offsets:
                            outline_x = body_x + off_x
                            outline_y = body_y + off_y
                            if 0 <= outline_x < self.screen_width and \
                                0 <= outline_y < self.screen_height:
                                if (outline_x, outline_y) not in body_pixels_drawn_on_screen: 
                                    if sprite_dist < self.z_buffer.get(outline_x, float('inf')):
                                        self.draw_context.point((outline_x, outline_y), fill=outline_color_fill)
                except Exception as e_sprite_render:
                    pass # print(f"Err hardcode sprite: {e_sprite_render}")

    def _draw_gun_sprite(self):
        gun_data_to_use = self.gun_sprite_idle_data
        if self.gun_fire_timer > 0:
            gun_data_to_use = self.gun_sprite_fire_data
            self.gun_fire_timer -= 1 
        gun_width, gun_height, gun_pixels_str = gun_data_to_use["width"], gun_data_to_use["height"], gun_data_to_use["pixels"]
        base_center_offset_x = self.gun_sprite_idle_data["width"] // 2
        fire_center_offset_x = gun_width // 2
        start_x = (self.screen_width // 2) - base_center_offset_x + (base_center_offset_x - fire_center_offset_x)
        start_y = self.screen_height - gun_height - self.gun_y_offset
        for r_idx, row_str in enumerate(gun_pixels_str):
            for c_idx, pixel_char in enumerate(row_str):
                if pixel_char == '1':
                    abs_x, abs_y = start_x + c_idx, start_y + r_idx
                    if 0 <= abs_x < self.screen_width and 0 <= abs_y < self.screen_height:
                        self.draw_context.point((abs_x, abs_y), fill=255) 

    def _draw_hud(self):
        hp_bar_height = 3
        hp_bar_y_pos = self.screen_height - hp_bar_height - 1 
        hp_pixel_width_per_hp = (self.screen_width // 3) // PLAYER_MAX_HP 
        for i in range(self.player_hp):
            hp_rect_start_x = 2 + (i * (hp_pixel_width_per_hp + 1)) 
            self.draw_context.rectangle([
                (hp_rect_start_x, hp_bar_y_pos),
                (hp_rect_start_x + hp_pixel_width_per_hp -1, hp_bar_y_pos + hp_bar_height -1)
            ], fill=255)
        if self.player_hit_animation_timer > 0:
            if self.player_hit_animation_timer % 2 == 0: 
                for i_glitch in range(0, self.screen_width, 4): 
                    self.draw_context.line([(i_glitch, self.screen_height // 2), (i_glitch + 2, self.screen_height // 2)], fill=0)
                    self.draw_context.line([(i_glitch, 10), (i_glitch + 2, 10)], fill=0)
                    self.draw_context.line([(i_glitch, self.screen_height - 10), (i_glitch + 2, self.screen_height - 10)], fill=0)
            self.player_hit_animation_timer -= 1
        if self.game_over and self.game_message:
            font_to_use = self.message_font if self.message_font else ImageFont.load_default()
            try:
                bbox = self.draw_context.textbbox((0,0), self.game_message, font=font_to_use)
                text_width = bbox[2] - bbox[0]
                text_height = bbox[3] - bbox[1]
                text_x = (self.screen_width - text_width) // 2
                text_y = (self.screen_height - text_height) // 2
                self.draw_context.text((text_x, text_y), self.game_message, font=font_to_use, fill=255)
            except Exception as e_msg: 
                est_char_w = font_to_use.getsize("A")[0] if hasattr(font_to_use, 'getsize') else 6
                text_width = len(self.game_message) * est_char_w
                text_height = font_to_use.getsize("A")[1] if hasattr(font_to_use, 'getsize') else 8
                text_x = (self.screen_width - text_width) // 2
                text_y = (self.screen_height - text_height) // 2
                self.draw_context.text((text_x, text_y), self.game_message, font=font_to_use, fill=255)

    def fire_gun(self):
        if self.game_over: return 
        self.gun_fire_timer = self.gun_fire_animation_frames
        print("Player fires gun!")
        max_hit_range = 10.0 
        hit_target_sprite_idx = -1
        min_dist_to_hit_sprite = float('inf')
        for i, sprite in enumerate(self.sprites):
            if sprite.get("state") == "dead" or sprite.get("type") != "imp": 
                continue
            dx, dy = sprite["x"] - self.player_x, sprite["y"] - self.player_y
            dist_to_sprite_center = math.sqrt(dx*dx + dy*dy)
            if not (0.1 < dist_to_sprite_center <= max_hit_range): 
                continue
            angle_to_sprite = math.atan2(dy, dx)
            angle_diff = angle_to_sprite - self.player_angle_rad
            while angle_diff < -math.pi: angle_diff += 2 * math.pi
            while angle_diff > math.pi: angle_diff -= 2 * math.pi
            hit_cone_angle_rad = 0.25 
            if abs(angle_diff) < hit_cone_angle_rad:
                if dist_to_sprite_center < min_dist_to_hit_sprite:
                    hit_target_sprite_idx = i
                    min_dist_to_hit_sprite = dist_to_sprite_center
        if hit_target_sprite_idx != -1:
            hit_sprite = self.sprites[hit_target_sprite_idx]
            print(f"HIT Imp {hit_sprite.get('id', 'unknown')}!")
            hit_sprite["health"] -= 1
            if hit_sprite["health"] <= 0:
                hit_sprite["state"] = "dead"
                print(f"Imp {hit_sprite.get('id', 'unknown')} DIES!")
        else:
            print("Missed!")

    def update_movement_speed(self, is_running: bool):
        self.is_running = is_running
        self.current_move_speed = self.base_move_speed * (self.run_speed_multiplier if self.is_running else 1.0)

    def move_forward(self):
        new_x = self.player_x + math.cos(self.player_angle_rad) * self.current_move_speed
        new_y = self.player_y + math.sin(self.player_angle_rad) * self.current_move_speed
        self._try_move(new_x, new_y)

    def move_backward(self):
        new_x = self.player_x - math.cos(self.player_angle_rad) * self.current_move_speed
        new_y = self.player_y - math.sin(self.player_angle_rad) * self.current_move_speed
        self._try_move(new_x, new_y)

    def turn_left(self):
        self.player_angle_rad = (self.player_angle_rad - self.turn_speed) % (2 * math.pi)

    def turn_right(self):
        self.player_angle_rad = (self.player_angle_rad + self.turn_speed) % (2 * math.pi)

    def strafe_left(self):
        strafe_angle = self.player_angle_rad - math.pi / 2 
        new_x = self.player_x + math.cos(strafe_angle) * self.current_move_speed
        new_y = self.player_y + math.sin(strafe_angle) * self.current_move_speed
        self._try_move(new_x, new_y)

    def strafe_right(self):
        strafe_angle = self.player_angle_rad + math.pi / 2 
        new_x = self.player_x + math.cos(strafe_angle) * self.current_move_speed
        new_y = self.player_y + math.sin(strafe_angle) * self.current_move_speed
        self._try_move(new_x, new_y)

    def _try_move(self, new_x, new_y):
        current_map_x, current_map_y = int(self.player_x), int(self.player_y)
        target_map_x, target_map_y = int(new_x), int(new_y)
        # print(f"DEBUG_MOVE: Attempting move from ({self.player_x:.2f}, {self.player_y:.2f}) -> ({new_x:.2f}, {new_y:.2f})")
        # print(f"DEBUG_MOVE: Current map tile: ({current_map_x}, {current_map_y}). Target map tile: ({target_map_x}, {target_map_y})")
        if not (0 <= target_map_x < self.map_width and 0 <= target_map_y < self.map_height):
            print(f"DEBUG_MOVE: Blocked! Target ({target_map_x},{target_map_y}) is out of map bounds ({self.map_width}x{self.map_height}).")
            return 
        tile_type_at_target = self.game_map_tiles[target_map_y][target_map_x]
        if tile_type_at_target == 1: 
            print(f"DEBUG_MOVE: Blocked! Target map tile ({target_map_x},{target_map_y}) is a WALL (type {tile_type_at_target}).")
            return 
        print(f"DEBUG_MOVE: Allowed! Moving to ({new_x:.2f}, {new_y:.2f}). Target tile type: {tile_type_at_target}")
        self.player_x, self.player_y = new_x, new_y

    def _has_line_of_sight(self, x1: float, y1: float, x2: float, y2: float, max_los_distance: float) -> bool:
        """
        Checks if there is a clear line of sight between (x1, y1) and (x2, y2)
        up to max_los_distance, without hitting a wall (tile type 1).
        Uses a DDA-like algorithm.
        """
        dx = x2 - x1
        dy = y2 - y1
        distance_to_target = math.sqrt(dx*dx + dy*dy)
        if distance_to_target == 0:  # Same point
            return True
        if distance_to_target > max_los_distance:  # Target is beyond max LOS range
            return False
        ray_dir_x = dx / distance_to_target
        ray_dir_y = dy / distance_to_target
        # Current position of the ray check, starts at (x1, y1)
        current_check_x = x1
        current_check_y = y1
        # Which box of the map we're in
        map_check_x = int(current_check_x)
        map_check_y = int(current_check_y)
        # Length of ray from current position to next x or y-side
        # Avoid division by zero by using a very small number if ray_dir is 0 (though normalized shouldn't be 0 unless dist is 0)
        delta_dist_x = abs(1 / ray_dir_x) if ray_dir_x != 0 else float('inf')
        delta_dist_y = abs(1 / ray_dir_y) if ray_dir_y != 0 else float('inf')
        step_x, step_y = 0, 0
        # Length of ray from one x or y-side to next x or y-side
        side_dist_x, side_dist_y = 0.0, 0.0
        if ray_dir_x < 0:
            step_x = -1
            side_dist_x = (current_check_x - map_check_x) * delta_dist_x
        else:
            step_x = 1
            side_dist_x = (map_check_x + 1.0 - current_check_x) * delta_dist_x
        if ray_dir_y < 0:
            step_y = -1
            side_dist_y = (current_check_y - map_check_y) * delta_dist_y
        else:
            step_y = 1
            side_dist_y = (map_check_y + 1.0 - current_check_y) * delta_dist_y
        dist_travelled = 0
        # Perform DDA
        while dist_travelled < distance_to_target:
            # Jump to next map square, OR in x-direction, OR in y-direction
            if side_dist_x < side_dist_y:
                dist_travelled = side_dist_x  # Store current distance before incrementing
                side_dist_x += delta_dist_x
                map_check_x += step_x
            else:
                dist_travelled = side_dist_y  # Store current distance before incrementing
                side_dist_y += delta_dist_y
                map_check_y += step_y
            # Check if ray is out of bounds (should ideally not happen if target is in bounds)
            if not (0 <= map_check_x < self.map_width and 0 <= map_check_y < self.map_height):
                # print(f"DEBUG_LOS: Ray out of bounds at ({map_check_x},{map_check_y})")
                return False  # Hit edge of map before target
            # Check if the ray has hit a wall
            if self.game_map_tiles[map_check_y][map_check_x] == 1:  # 1 is wall
                # print(f"DEBUG_LOS: Blocked by wall at ({map_check_x},{map_check_y})")
                return False  # LOS is blocked by a wall
            # If we've checked the tile where the target (x2,y2) resides, and haven't hit a wall,
            # then LOS is clear up to the target's tile.
            # We compare map_check_x/y with int(x2)/int(y2)
            if map_check_x == int(x2) and map_check_y == int(y2):
                # print(f"DEBUG_LOS: Reached target tile ({map_check_x},{map_check_y}) clear.")
                return True
        # If loop finishes, it means we've travelled up to distance_to_target
        # without hitting a wall that's *not* the target's own tile (if target is in a wall)
        # The check for target's tile above should catch clear LOS.
        # This return implies we reached the target distance without being blocked by an intermediate wall.
        # print(f"DEBUG_LOS: Reached target distance clear.")
        return True

    def get_current_frame_pil(self) -> Image.Image :
        if not self.game_over: 
            self._render_to_internal_buffer() 
            self._render_sprites()            
            self._draw_gun_sprite()           
        else: 
            self.draw_context.rectangle([(0,0), (self.screen_width, self.screen_height)], fill=0)
        self._draw_hud() 
        return self.current_frame_image

    def get_packed_oled_frame(self) -> bytearray | None:
        if not OLED_RENDERER_LOADED_OK: return None
        img = self.get_current_frame_pil()
        return oled_renderer.pack_pil_image_to_7bit_stream(img) if img else None

RAYCASTER_ENGINE_DEFINED = True # Mark as defined after class body

# --- PyQt6 Test Window ---
class DoomOLEDTestWindow(QWidget):
    # --- User-Configured Pad Layout for DOOM Game ---
    # This dictionary maps the PHYSICAL (row, col) of the pad to light up
    # to the MIDI NOTE CONSTANT that action corresponds to.
    # (row, col) are the hardware coordinates for AkaiFireController.set_pad_color()
    PAD_LAYOUT_FOR_DOOM_GAME = {
        # Left Hand D-Pad Area 
        # Physical pad (0,1) is FORWARD (Note 55)
        (0, 1): PAD_DOOM_FORWARD,
        # Physical pad (1,1) is BACKWARD (Note 71)
        (1, 1): PAD_DOOM_BACKWARD,
        # Physical pad (1,0) is STRAFE_LEFT (Note 70)
        (1, 0): PAD_DOOM_STRAFE_LEFT,
        # Physical pad (1,2) is STRAFE_RIGHT (Note 72)
        (1, 2): PAD_DOOM_STRAFE_RIGHT,
        # Physical pad (0,0) is TURN_LEFT_MAIN (Note 54)
        (0, 0): PAD_DOOM_TURN_LEFT_MAIN,
        # Physical pad (0,2) is TURN_RIGHT_MAIN (Note 56)
        (0, 2): PAD_DOOM_TURN_RIGHT_MAIN,
        # Right Hand Action/Alt-Turn Area 
        # Physical pad (0,14) is TURN_LEFT_ALT (Note 68)
        (0, 14): PAD_DOOM_TURN_LEFT_ALT,
        # Physical pad (0,15) is TURN_RIGHT_ALT (Note 69)
        (0, 15): PAD_DOOM_TURN_RIGHT_ALT,
        (1, 14): PAD_DOOM_RUN,            # Physical pad (1,14) is RUN (Note 84)
        (1, 15): PAD_DOOM_SHOOT,          # Physical pad (1,15) is SHOOT (Note 85)
    }
    HP_PAD_COORDS = [(3,0), (3,1), (3,2), (3,3)] # As identified: (row=3, col=0 to 3)
    # --- Restart Trigger and Visual Configuration ---
    RESTART_PAD_TRIGGER_NOTE = PAD_DOOM_SHOOT  # Changed from FIRE_BUTTON_PLAY
    RESTART_PAD_BLINK_VISUAL_NOTE = PAD_DOOM_SHOOT

    def __init__(self, parent=None):
        super().__init__(parent)
        print("DEBUG_INIT: DoomOLEDTestWindow __init__ START")
        self.setWindowTitle("DOOM OLED Test - Pad Input & Restart Logic")
        self.setGeometry(200, 200, 400, 250) # Default window size

        print("DEBUG_INIT: Checking critical modules...")
        if not CRITICAL_MODULES_LOADED or not RAYCASTER_ENGINE_DEFINED:
            print("DEBUG_INIT: Critical modules FAILED. Calling setup_error_ui.")
            self.setup_error_ui("Core modules (Controller, Renderer, Raycaster) failed to load. Check console.")
            return 
        print("DEBUG_INIT: Critical modules OK.")

        print("DEBUG_INIT: Creating RaycasterEngine...")
        self.engine = RaycasterEngine(parent=self)
        print("DEBUG_INIT: RaycasterEngine created.")
        
        print("DEBUG_INIT: Creating AkaiFireController...")
        self.fire_controller = AkaiFireController(auto_connect=False)
        print("DEBUG_INIT: AkaiFireController created.")
        
        self.him = None 
        if HARDWARE_INPUT_MANAGER_LOADED and AKAI_FIRE_CONTROLLER_LOADED:
            print("DEBUG_INIT: Creating HardwareInputManager...")
            self.him = HardwareInputManager(self.fire_controller) 
            print("DEBUG_INIT: HardwareInputManager created.")

        print("DEBUG_INIT: Setting up fire_button_event connection...")
        if hasattr(self.fire_controller, 'fire_button_event'):
            self.fire_controller.fire_button_event.connect(self.handle_fire_pad_event)
            print("DEBUG_INIT: fire_button_event connected.")
        else:
            print("DEBUG_INIT: CRITICAL - fire_button_event missing from controller!")
            QMessageBox.critical(self, "Fatal Error", "AkaiFireController is missing 'fire_button_event'. Cannot proceed.")
            return 

        print("DEBUG_INIT: Setting up UI layout...")
        layout = QVBoxLayout(self) # Main layout for the window

        self.status_label = QLabel("Connect Akai Fire to start.")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.status_label)

        # --- MIDI Output Port Selection ---
        out_port_layout = QHBoxLayout()
        out_port_layout.addWidget(QLabel("Output Port:"))
        self.out_port_combo = QComboBox(self) # Assign to self.out_port_combo
        out_ports = AkaiFireController.get_available_output_ports() if AKAI_FIRE_CONTROLLER_LOADED else ["Error: No Controller"]
        if out_ports and out_ports[0] != "Error: No Controller":
            self.out_port_combo.addItems(out_ports)
            idx_out = next((i for i, p in enumerate(out_ports) if "fire" in p.lower() and "midiin" not in p.lower()), -1)
            self.out_port_combo.setCurrentIndex(idx_out if idx_out != -1 else (0 if self.out_port_combo.count() > 0 else -1))
        else:
            self.out_port_combo.addItem(out_ports[0] if out_ports else "No MIDI outputs")
            self.out_port_combo.setEnabled(False)
        out_port_layout.addWidget(self.out_port_combo)
        layout.addLayout(out_port_layout)
        print("DEBUG_INIT: Output port UI created.")

        # --- MIDI Input Port Selection ---
        in_port_layout = QHBoxLayout()
        in_port_layout.addWidget(QLabel("Input Port:  "))
        self.in_port_combo = QComboBox(self) # Assign to self.in_port_combo
        in_ports = AkaiFireController.get_available_input_ports() if AKAI_FIRE_CONTROLLER_LOADED else ["Error: No Controller"]
        if in_ports and in_ports[0] != "Error: No Controller":
            self.in_port_combo.addItems(in_ports)
            idx_in = next((i for i, p in enumerate(in_ports) if "fire" in p.lower()), -1)
            self.in_port_combo.setCurrentIndex(idx_in if idx_in != -1 else (0 if self.in_port_combo.count() > 0 else -1))
        else:
            self.in_port_combo.addItem(in_ports[0] if in_ports else "No MIDI inputs")
            self.in_port_combo.setEnabled(False)
        in_port_layout.addWidget(self.in_port_combo)
        layout.addLayout(in_port_layout)
        print("DEBUG_INIT: Input port UI created.")

        # --- Connect Button ---
        self.connect_button = QPushButton("Connect & Start DOOM", self) # Assign to self.connect_button
        self.connect_button.clicked.connect(self.toggle_connection_and_doom)
        layout.addWidget(self.connect_button)
        print("DEBUG_INIT: Connect button created.")
        
        self.setLayout(layout)
        print("DEBUG_INIT: Main UI layout set.")

        print("DEBUG_INIT: Initializing game_timer...")
        self.game_timer = QTimer(self)
        self.game_timer.timeout.connect(self.game_loop_tick)
        print("DEBUG_INIT: game_timer initialized.")
        self.is_doom_running = False

        print("DEBUG_INIT: Initializing pad_key_states...")
        self.pad_key_states = { 
            PAD_DOOM_FORWARD: False, PAD_DOOM_BACKWARD: False, 
            PAD_DOOM_STRAFE_LEFT: False, PAD_DOOM_STRAFE_RIGHT: False,
            PAD_DOOM_TURN_LEFT_MAIN: False, PAD_DOOM_TURN_RIGHT_MAIN: False, 
            PAD_DOOM_TURN_LEFT_ALT: False, PAD_DOOM_TURN_RIGHT_ALT: False,
            PAD_DOOM_RUN: False, PAD_DOOM_SHOOT: False, 
        }
        print("DEBUG_INIT: pad_key_states initialized.")

        print("DEBUG_INIT: Setting focus policy...")
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        print("DEBUG_INIT: Focus policy set.")

        print("DEBUG_INIT: Initializing _pad_flash_timer...")
        self._pad_flash_timer = QTimer(self)
        self._pad_flash_timer.setSingleShot(True)
        self._pad_flash_timer.timeout.connect(self._clear_hit_flash_and_restore_dpad_lights)
        print("DEBUG_INIT: _pad_flash_timer initialized.")

        self.is_restart_prompt_active = False
        print("DEBUG_INIT: Initializing game_over_effects_timer...")
        self.game_over_effects_timer = QTimer(self)
        self.game_over_effects_timer.timeout.connect(self._handle_game_over_effects)
        print("DEBUG_INIT: game_over_effects_timer initialized.")
        self.death_flash_count = 0
        self.restart_pad_blink_state = False

        print("DEBUG_INIT: DoomOLEDTestWindow __init__ COMPLETE.")

    def setup_error_ui(self, message):
        layout = QVBoxLayout(self)
        error_label = QLabel(
            f"<h2 style='color:red;'>Initialization Error</h2><p>{message}</p>")
        # Allow HTML for formatting
        error_label.setTextFormat(Qt.TextFormat.RichText)
        error_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        error_label.setWordWrap(True)
        layout.addWidget(error_label)
        self.setLayout(layout)
        self.setWindowTitle("DOOM Test - CRITICAL ERROR")

    def toggle_connection_and_doom(self):
        if not AKAI_FIRE_CONTROLLER_LOADED:
            QMessageBox.critical(
                self, "Fatal Error", "AkaiFireController module not loaded. Cannot connect.")
            return
        if self.fire_controller.is_connected() and not self.is_restart_prompt_active:
            # If connected and game is running (not in restart prompt), stop and disconnect
            self.stop_doom_loop()
            self.fire_controller.disconnect()
            self.status_label.setText(
                "Disconnected. Connect Akai Fire to start.")
            self.connect_button.setText("Connect & Start DOOM")
            self.out_port_combo.setEnabled(True)
            self.in_port_combo.setEnabled(True)
        else:
            # If restart prompt is active and button is clicked (acting as a UI restart)
            if self.is_restart_prompt_active:
                print("Restarting game (from UI button while prompt active)...")
                self.is_restart_prompt_active = False
                self.game_over_effects_timer.stop()
                for key_note in self.pad_key_states:
                    self.pad_key_states[key_note] = False  # Reset pad states
                self.start_doom_loop()  # Restart the game
                self.connect_button.setText("Disconnect & Stop DOOM")
                # Should be enabled after restart
                self.connect_button.setEnabled(True)
                self.status_label.setText(
                    "Connected! DOOM Running! (Use Akai Fire Pads)")
                return
            # Attempt to connect
            selected_out_port = self.out_port_combo.currentText()
            selected_in_port = self.in_port_combo.currentText()
            if not selected_out_port or "No MIDI" in selected_out_port or "Error:" in selected_out_port:
                QMessageBox.warning(
                    self, "MIDI Error", "No valid MIDI output port selected or available.")
                return
            if not selected_in_port or "No MIDI" in selected_in_port or "Error:" in selected_in_port:
                QMessageBox.warning(
                    self, "MIDI Error", "No valid MIDI input port selected or available.")
                return
            if self.fire_controller.connect(selected_out_port, selected_in_port):
                self.status_label.setText(
                    "Connected! DOOM Running! (Use Akai Fire Pads)")
                self.connect_button.setText("Disconnect & Stop DOOM")
                self.connect_button.setEnabled(True)
                self.out_port_combo.setEnabled(False)
                self.in_port_combo.setEnabled(False)
                self.start_doom_loop()  # This will also call setup_dpad_lights
            else:
                QMessageBox.critical(
                    self, "Connection Failed", f"Could not connect to Akai Fire.\nOutput: {selected_out_port}\nInput: {selected_in_port}")

    def setup_dpad_lights(self):
        if not self.fire_controller.is_connected():
            return
        print("INFO: Setting up D-Pad lights on Akai Fire...")
        # Define colors for each action type
        pad_to_light_color = {
            PAD_DOOM_FORWARD: PAD_COLOR_DPAD_RED,
            PAD_DOOM_BACKWARD: PAD_COLOR_DPAD_RED,
            PAD_DOOM_STRAFE_LEFT: PAD_COLOR_DPAD_RED,   
            PAD_DOOM_STRAFE_RIGHT: PAD_COLOR_DPAD_RED,
            PAD_DOOM_TURN_LEFT_MAIN: PAD_COLOR_ORANGE, 
            PAD_DOOM_TURN_RIGHT_MAIN: PAD_COLOR_ORANGE,
            PAD_DOOM_TURN_LEFT_ALT: PAD_COLOR_ORANGE,  
            PAD_DOOM_TURN_RIGHT_ALT: PAD_COLOR_ORANGE,  
            PAD_DOOM_RUN: PAD_COLOR_BLUE_RUN,
            PAD_DOOM_SHOOT: PAD_COLOR_SHOOT_GREEN,
        }
        # Clear all pads first (important for clean state)
        for r_idx in range(4):  # Assuming 4 rows on Fire
            for c_idx in range(16):  # Assuming 16 columns
                self.fire_controller.set_pad_color(
                    r_idx, c_idx, *PAD_COLOR_OFF)
        time.sleep(0.01)  # Small delay to ensure clear command processes
        # Light up pads defined in PAD_LAYOUT_FOR_DOOM_GAME
        for (r, c), note_for_action in self.PAD_LAYOUT_FOR_DOOM_GAME.items():
            # Default to OFF if note not in map
            color_to_set = pad_to_light_color.get(
                note_for_action, PAD_COLOR_OFF)
            self.fire_controller.set_pad_color(r, c, *color_to_set)
            # print(f"  Lit ({r},{c}) for note {note_for_action} with {color_to_set}") # Debug

    def clear_all_game_pads(self):
        if not self.fire_controller.is_connected():
            return
        print("INFO: Clearing ALL game pads on Akai Fire...")
        all_pads_off_data = [(r, c, *PAD_COLOR_OFF)
                            for r in range(4) for c in range(16)]
        if hasattr(self.fire_controller, 'set_multiple_pads_color') and all_pads_off_data:
            # Bypass global brightness to ensure they go completely off
            self.fire_controller.set_multiple_pads_color(
                all_pads_off_data, bypass_global_brightness=True)
        else:  # Fallback if set_multiple_pads_color not available
            for r_idx in range(4):
                for c_idx in range(16):
                    self.fire_controller.set_pad_color(
                        r_idx, c_idx, *PAD_COLOR_OFF)

    def _update_hp_pad_lights(self):
        """Updates the physical HP pads based on current player HP."""
        if not self.fire_controller.is_connected() or not hasattr(self, 'engine'):
            return
        current_hp = self.engine.player_hp
        # PLAYER_MAX_HP is a global constant, or could be self.engine.PLAYER_MAX_HP if defined there
        pads_to_update_colors = []
        for i in range(PLAYER_MAX_HP):  # Iterate from 0 up to PLAYER_MAX_HP - 1
            if i < len(self.HP_PAD_COORDS):  # Ensure we don't go out of bounds for HP_PAD_COORDS
                pad_r, pad_c = self.HP_PAD_COORDS[i]
                if i < current_hp:
                    # This segment of HP is active, light it RED
                    pads_to_update_colors.append(
                        (pad_r, pad_c, *PAD_COLOR_HEALTH_RED))
                else:
                    # This segment of HP is lost, turn it OFF
                    pads_to_update_colors.append(
                        (pad_r, pad_c, *PAD_COLOR_OFF))
            # Should not happen if PLAYER_MAX_HP matches len(HP_PAD_COORDS)
            else:
                print(
                    f"WARNING: PLAYER_MAX_HP ({PLAYER_MAX_HP}) > number of defined HP pads ({len(self.HP_PAD_COORDS)}). HP segment {i} not shown.")
                break
        if hasattr(self.fire_controller, 'set_multiple_pads_color') and pads_to_update_colors:
            # Do not bypass global brightness for HP bar, let it be consistent with other lights
            self.fire_controller.set_multiple_pads_color(
                pads_to_update_colors, bypass_global_brightness=False)
        elif pads_to_update_colors:  # Fallback to individual calls
            for r, c, r_val, g_val, b_val in pads_to_update_colors:
                self.fire_controller.set_pad_color(r, c, r_val, g_val, b_val)
        # print(f"DEBUG: Updated HP pads. Current HP: {current_hp}") # Optional debug

    def _flash_pads_red_on_hit(self):
        if not self.fire_controller.is_connected() or self.engine.game_over: return
        print("EFFECT: Flashing non-D-Pad/HP pads RED (Player Hit)")
        flash_data = []
        control_pad_coords = set(self.PAD_LAYOUT_FOR_DOOM_GAME.keys())
        hp_pad_coords_set = set(self.HP_PAD_COORDS) # Convert HP_PAD_COORDS to a set for efficient lookup
        for r in range(4): 
            for c in range(16): 
                current_coord = (r,c)
                # Flash only if NOT a defined control pad AND NOT an HP pad
                if current_coord not in control_pad_coords and current_coord not in hp_pad_coords_set: 
                    flash_data.append((r, c, *PAD_COLOR_HIT_FLASH_RED))
        if hasattr(self.fire_controller, 'set_multiple_pads_color') and flash_data:
            self.fire_controller.set_multiple_pads_color(flash_data, bypass_global_brightness=True) 
        
        self._pad_flash_timer.start(80) 

    def _clear_hit_flash_and_restore_dpad_lights(self):
        if not hasattr(self, 'engine') or self.engine.game_over: 
            # If engine doesn't exist or game is over, just clear all and stop
            if hasattr(self, 'clear_all_game_pads'):
                self.clear_all_game_pads() 
            return
        if hasattr(self, 'setup_dpad_lights'):
            self.setup_dpad_lights()      # Restores D-Pad lights (this also clears non-D-Pad pads)
        if hasattr(self, '_update_hp_pad_lights'):
            self._update_hp_pad_lights()  # Explicitly redraw the HP bar lights

    def start_doom_loop(self):
        if self.is_doom_running or not RAYCASTER_ENGINE_DEFINED: return
        print("GAME: Starting DOOM game loop...")
        self.is_doom_running = True
        self.is_restart_prompt_active = False 
        self.game_over_effects_timer.stop() 
        for key in self.pad_key_states: self.pad_key_states[key] = False 
        self.engine._parse_map_and_init_state() 
        if hasattr(self.engine, 'player_took_damage_signal'):
            try: 
                self.engine.player_took_damage_signal.disconnect(self._flash_pads_red_on_hit)
                self.engine.player_took_damage_signal.disconnect(self._update_hp_pad_lights) # Also disconnect HP update
            except TypeError: pass 
            self.engine.player_took_damage_signal.connect(self._flash_pads_red_on_hit)
            self.engine.player_took_damage_signal.connect(self._update_hp_pad_lights) # Connect HP update on damage
        self.setup_dpad_lights() 
        self._update_hp_pad_lights() # <<< ADD THIS CALL to set initial HP lights
        self.game_timer.start(int(1000 / TARGET_FPS))
        self.setFocus() 
        print("GAME: DOOM loop started.")

    def stop_doom_loop(self):
        print("GAME: Stopping DOOM game loop...")
        self.is_doom_running = False
        # --- Defensive check for game_timer ---
        if hasattr(self, 'game_timer') and self.game_timer is not None:
            self.game_timer.stop()
        else:
            print("WARNING: stop_doom_loop - game_timer not found or not initialized.")
        # --- Defensive check for game_over_effects_timer ---
        if hasattr(self, 'game_over_effects_timer') and self.game_over_effects_timer is not None:
            self.game_over_effects_timer.stop()
        else:
            print(
                "WARNING: stop_doom_loop - game_over_effects_timer not found or not initialized.")
        self.is_restart_prompt_active = False
        if hasattr(self, 'engine') and hasattr(self.engine, 'player_took_damage_signal'):  # Check engine too
            try:
                self.engine.player_took_damage_signal.disconnect(
                    self._flash_pads_red_on_hit)
            except TypeError:
                pass
        # Check fire_controller before calling methods on it
        if hasattr(self, 'fire_controller') and self.fire_controller is not None:
            self.clear_all_game_pads()
            if self.fire_controller.is_connected() and OLED_RENDERER_LOADED_OK:
                blank_pil = Image.new(
                    '1', (oled_renderer.OLED_WIDTH, oled_renderer.OLED_HEIGHT), 0)
                packed_blank = oled_renderer.pack_pil_image_to_7bit_stream(
                    blank_pil)
                if packed_blank:
                    self.fire_controller.oled_send_full_bitmap(packed_blank)
        else:
            print(
                "WARNING: stop_doom_loop - fire_controller not found or not initialized.")
        print("GAME: DOOM loop stopped (or was not running).")

    def _handle_game_over_effects(self):
        if not self.fire_controller.is_connected():
            self.game_over_effects_timer.stop()  # Stop if controller disconnects
            return

        # Phase 1: Full pad red flashes (5 times = 10 steps for on/off)
        if self.death_flash_count < 10:
            if self.death_flash_count % 2 == 0:  # Even: Flash Red
                all_pads_red_data = [(r, c, *PAD_COLOR_HIT_FLASH_RED)
                                    for r in range(4) for c in range(16)]
                if hasattr(self.fire_controller, 'set_multiple_pads_color'):
                    self.fire_controller.set_multiple_pads_color(
                        all_pads_red_data, bypass_global_brightness=True)
            else:  # Odd: Turn All Off
                self.clear_all_game_pads()
            self.death_flash_count += 1
            self.game_over_effects_timer.setInterval(
                120)  # Speed of death flashes

        # Phase 2: Restart Prompt on OLED and blinking SHOOT pad
        else:
            self.is_restart_prompt_active = True  # Activate restart prompt state
            # Update OLED message (engine will use "Restart?")
            # Set message for engine to draw
            self.engine.game_message = "Restart?"
            # Get frame with new message
            packed_frame_restart_prompt = self.engine.get_packed_oled_frame()
            if packed_frame_restart_prompt and self.fire_controller.is_connected():
                self.fire_controller.oled_send_full_bitmap(
                    packed_frame_restart_prompt)

            # Blink the SHOOT pad (visual cue for restart)
            self.restart_pad_blink_state = not self.restart_pad_blink_state  # Toggle blink state

            blink_pad_rc_to_use = None
            # Find the (row,col) for the RESTART_PAD_BLINK_VISUAL_NOTE
            for (r_search, c_search), note_val_search in self.PAD_LAYOUT_FOR_DOOM_GAME.items():
                if note_val_search == self.RESTART_PAD_BLINK_VISUAL_NOTE:  # Should be PAD_DOOM_SHOOT
                    blink_pad_rc_to_use = (r_search, c_search)
                    break

            if blink_pad_rc_to_use:
                color_for_blink = PAD_COLOR_SHOOT_GREEN if self.restart_pad_blink_state else PAD_COLOR_OFF
                self.fire_controller.set_pad_color(
                    blink_pad_rc_to_use[0], blink_pad_rc_to_use[1], *color_for_blink)
            # Fallback if RESTART_PAD_BLINK_VISUAL_NOTE somehow not in layout (shouldn't happen)
            else:
                print(
                    f"WARNING: RESTART_PAD_BLINK_VISUAL_NOTE {self.RESTART_PAD_BLINK_VISUAL_NOTE} not found in PAD_LAYOUT. Cannot blink designated pad.")

            self.game_over_effects_timer.setInterval(
                350)  # Blinking speed for SHOOT pad

            # Update UI button to reflect restart prompt state
            self.connect_button.setText("Restart Game (Press SHOOT Pad)")
            self.connect_button.setEnabled(True)  # Allow UI restart too

    def game_loop_tick(self):
        if not self.is_doom_running or not RAYCASTER_ENGINE_DEFINED:
            return

        # Handle game over state transition
        if self.engine.game_over and not self.is_restart_prompt_active:
            if self.game_timer.isActive():
                self.game_timer.stop()  # Stop main game loop
            print(
                f"GAME STATE: Game Over! Message: '{self.engine.game_message}'")
            self.status_label.setText(
                f"GAME OVER: {self.engine.game_message}. Waiting for restart prompt...")
            self.connect_button.setText("Processing Game Over...")
            # Disable normal connect/disconnect during this
            self.connect_button.setEnabled(False)
            self.out_port_combo.setEnabled(False)
            self.in_port_combo.setEnabled(False)

            self.death_flash_count = 0  # Reset for flashing sequence
            # Start game over effects sequence
            self.game_over_effects_timer.start(120)
            self.is_doom_running = False  # Mark as not running to prevent further game logic
            return

        # If restart prompt is active, main game logic should not run
        if self.is_restart_prompt_active:
            return

        # --- Game Logic (Only if game is running and not in restart prompt) ---
        self.engine.update_movement_speed(
            self.pad_key_states.get(PAD_DOOM_RUN, False))
        if self.pad_key_states.get(PAD_DOOM_FORWARD):
            self.engine.move_forward()
        if self.pad_key_states.get(PAD_DOOM_BACKWARD):
            self.engine.move_backward()
        if self.pad_key_states.get(PAD_DOOM_TURN_LEFT_MAIN) or self.pad_key_states.get(PAD_DOOM_TURN_LEFT_ALT):
            self.engine.turn_left()
        if self.pad_key_states.get(PAD_DOOM_TURN_RIGHT_MAIN) or self.pad_key_states.get(PAD_DOOM_TURN_RIGHT_ALT):
            self.engine.turn_right()
        if self.pad_key_states.get(PAD_DOOM_STRAFE_LEFT):
            self.engine.strafe_left()
        if self.pad_key_states.get(PAD_DOOM_STRAFE_RIGHT):
            self.engine.strafe_right()

        # AI and other game state updates (win/lose conditions checked here)
        self.engine.update_ai_and_game_state()

        # Render and send to OLED
        packed_frame = self.engine.get_packed_oled_frame(
        ) if OLED_RENDERER_LOADED_OK else None
        if packed_frame and self.fire_controller.is_connected():
            self.fire_controller.oled_send_full_bitmap(packed_frame)

    def handle_fire_pad_event(self, note: int, is_pressed: bool):
        print(
            f"PAD_INPUT: Note={note} (0x{note:02X}), Pressed={is_pressed}, RestartPromptActive={self.is_restart_prompt_active}")

        # Handle restart if prompt is active
        if self.is_restart_prompt_active:
            # --- MODIFICATION: Check if the pressed note is the NEW RESTART_PAD_TRIGGER_NOTE ---
            if note == self.RESTART_PAD_TRIGGER_NOTE and is_pressed:  # Now PAD_DOOM_SHOOT (Note 85)
                print(
                    f"ACTION: Restart triggered by SHOOT Button (Note {self.RESTART_PAD_TRIGGER_NOTE}) while prompt active!")
                self.is_restart_prompt_active = False
                self.game_over_effects_timer.stop()
                for key_note_val in self.pad_key_states:
                    self.pad_key_states[key_note_val] = False  # Reset all pad states
                self.start_doom_loop()  # Restart the game
                self.connect_button.setText("Disconnect & Stop DOOM")
                self.connect_button.setEnabled(True)
                self.status_label.setText(
                    "Connected! DOOM Running! (Use Akai Fire Pads)")
            return  # Ignore other pad events during restart prompt

        # Ignore events if game is not running or is over (but not yet in restart prompt)
        if not self.is_doom_running or (hasattr(self, 'engine') and self.engine.game_over):
            return

        # Update pad state for game actions
        if note in self.pad_key_states:
            self.pad_key_states[note] = is_pressed
            if note == PAD_DOOM_SHOOT and is_pressed:
                self.engine.fire_gun()

    def keyPressEvent(self, event: QKeyEvent):
        # Allow 'R' for manual restart testing if game is over but prompt not yet fully active
        if hasattr(self, 'engine') and self.engine.game_over and \
            not self.is_restart_prompt_active and event.key() == Qt.Key.Key_R:
            print(
                "KEYBOARD: 'R' pressed for manual game over effects re-trigger (debug).")
            # Ensure it's false before starting effects
            self.is_restart_prompt_active = False
            self.game_over_effects_timer.stop()
            self.death_flash_count = 0
            self.game_over_effects_timer.start(120)  # Start effects sequence
            return
        if not self.is_doom_running:
            super().keyPressEvent(event)
            return
        # Map keyboard keys to pad note constants for game actions
        key_map = {
            Qt.Key.Key_W: PAD_DOOM_FORWARD, Qt.Key.Key_S: PAD_DOOM_BACKWARD,
            Qt.Key.Key_A: PAD_DOOM_STRAFE_LEFT, Qt.Key.Key_D: PAD_DOOM_STRAFE_RIGHT,
            Qt.Key.Key_Q: PAD_DOOM_TURN_LEFT_MAIN, Qt.Key.Key_E: PAD_DOOM_TURN_RIGHT_MAIN,  # Main turn
            # Using Left/Right arrows for Alt Turn might be more intuitive than separate keys
            Qt.Key.Key_Left: PAD_DOOM_TURN_LEFT_ALT, Qt.Key.Key_Right: PAD_DOOM_TURN_RIGHT_ALT,
            Qt.Key.Key_F: PAD_DOOM_SHOOT, Qt.Key.Key_Shift: PAD_DOOM_RUN
        }
        if event.key() in key_map and not event.isAutoRepeat():
            # Simulate a pad press event
            self.handle_fire_pad_event(key_map[event.key()], True)
        super().keyPressEvent(event)

    def keyReleaseEvent(self, event: QKeyEvent):
        if not self.is_doom_running:
            super().keyReleaseEvent(event)
            return
        key_map = {
            Qt.Key.Key_W: PAD_DOOM_FORWARD, Qt.Key.Key_S: PAD_DOOM_BACKWARD,
            Qt.Key.Key_A: PAD_DOOM_STRAFE_LEFT, Qt.Key.Key_D: PAD_DOOM_STRAFE_RIGHT,
            Qt.Key.Key_Q: PAD_DOOM_TURN_LEFT_MAIN, Qt.Key.Key_E: PAD_DOOM_TURN_RIGHT_MAIN,
            Qt.Key.Key_Left: PAD_DOOM_TURN_LEFT_ALT, Qt.Key.Key_Right: PAD_DOOM_TURN_RIGHT_ALT,
            Qt.Key.Key_F: PAD_DOOM_SHOOT, Qt.Key.Key_Shift: PAD_DOOM_RUN
        }
        if event.key() in key_map and not event.isAutoRepeat():
            self.handle_fire_pad_event(
                key_map[event.key()], False)  # Simulate pad release
        super().keyReleaseEvent(event)

    def closeEvent(self, event):  # QCloseEvent
        print("WINDOW: Close event triggered.")
        self.stop_doom_loop()  # Ensure game loop and timers are stopped
        if hasattr(self, 'fire_controller') and self.fire_controller and self.fire_controller.is_connected():
            print("WINDOW: Disconnecting Akai Fire controller on close.")
            self.fire_controller.disconnect()
        super().closeEvent(event)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    # Check if critical modules loaded before creating window
    if not CRITICAL_MODULES_LOADED or not RAYCASTER_ENGINE_DEFINED:
        # Simplified error display if core components failed very early
        error_dialog = QWidget()
        error_layout = QVBoxLayout(error_dialog)
        error_message_text = ("<h2 style='color:red;'>Fatal Initialization Failure</h2>"
                                "<p>One or more critical modules could not be loaded. "
                                "The DOOM feature cannot run. Please check the console output for details.</p>"
                                "<p>Specifically, ensure these are available:</p><ul>")
        if not AKAI_FIRE_CONTROLLER_LOADED:
            error_message_text += "<li style='color:yellow;'>- AkaiFireController (from hardware/)</li>"
        if not OLED_RENDERER_LOADED_OK:
            error_message_text += "<li style='color:yellow;'>- oled_renderer (from oled_utils/)</li>"
        # HardwareInputManager is less critical for standalone DOOM pad input but good to note
        if not HARDWARE_INPUT_MANAGER_LOADED:
            error_message_text += "<li style='color:orange;'>- HardwareInputManager (optional for this test if pads work)</li>"
        if not RAYCASTER_ENGINE_DEFINED:
            error_message_text += "<li style='color:yellow;'>- RaycasterEngine (defined in this script)</li>"
        error_message_text += "</ul>"
        error_label = QLabel(error_message_text)
        error_label.setTextFormat(Qt.TextFormat.RichText)
        error_label.setWordWrap(True)
        error_layout.addWidget(error_label)
        error_dialog.setWindowTitle("DOOM Test - Startup Error")
        error_dialog.resize(480, 250)  # Make error dialog reasonably sized
        error_dialog.show()
        print("\nExiting application due to critical module/class loading failures.")
    else:
        # Attempt to load stylesheet (optional, for consistent look if running standalone)
        try:
            style_path = os.path.join(
                PROJECT_ROOT, "resources", "styles", "style.qss")
            if os.path.exists(style_path):
                with open(style_path, "r") as f_style:
                    app.setStyleSheet(f_style.read())
        except Exception as e_style_load:
            print(
                f"WARNING: Could not load stylesheet for standalone test: {e_style_load}")
        window = DoomOLEDTestWindow()
        window.show()
    sys.exit(app.exec())