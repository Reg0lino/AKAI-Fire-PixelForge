import random
import math
import os
import sys
import time
from PIL import Image, ImageDraw, ImageFont
from PyQt6.QtCore import QObject, pyqtSignal, QTimer, Qt

CURRENT_SCRIPT_DIR_DGC = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT_DGC = os.path.dirname(CURRENT_SCRIPT_DIR_DGC)

if PROJECT_ROOT_DGC not in sys.path:
    sys.path.insert(0, PROJECT_ROOT_DGC)
# print(f"DEBUG DGC_SYS_PATH: Added to sys.path: {PROJECT_ROOT_DGC}")
# print(f"DEBUG DGC_SYS_PATH: Current sys.path: {sys.path}")

# --- Module Imports & Checks (Scoped for this module) ---
AKAI_FIRE_CONTROLLER_LOADED_DGC = False
OLED_RENDERER_LOADED_OK_DGC = False
FIRE_BUTTON_PLAY = 0x33 # Default value

try:
    from hardware.akai_fire_controller import AkaiFireController, FIRE_BUTTON_PLAY as FBP_imported
    AKAI_FIRE_CONTROLLER_LOADED_DGC = True
    FIRE_BUTTON_PLAY = FBP_imported # Use imported value if successful
    # print("DEBUG DGC: AkaiFireController & FIRE_BUTTON_PLAY imported successfully from hardware.")
except ImportError as e_afc_dgc:
    print(f"ERROR DGC: Could not import AkaiFireController or FIRE_BUTTON_PLAY: {e_afc_dgc}. Using fallback FIRE_BUTTON_PLAY={FIRE_BUTTON_PLAY}.")
    # Dummy AkaiFireController if needed by RaycasterEngine/DoomGameController directly (they expect a ref)
    class AkaiFireController:
        def __init__(self, *args, **kwargs): pass
        def connect(self, *args, **kwargs): return False
        def is_connected(self): return False
        def oled_send_full_bitmap(self, *args, **kwargs): pass
        def set_pad_color(self, r, c, r_val, g_val, b_val): pass
        def set_multiple_pads_color(self, data_list, bypass_global_brightness=False): pass
        def disconnect(self): pass
        @staticmethod
        def get_available_output_ports(): return []
        @staticmethod
        def get_available_input_ports(): return []
    AKAI_FIRE_CONTROLLER_LOADED_DGC = False

try:
    from oled_utils import oled_renderer
    OLED_RENDERER_LOADED_OK_DGC = True
    # print("DEBUG DGC: oled_renderer imported successfully.")
except ImportError as e_oled_dgc:
    print(f"ERROR DGC: Could not import oled_renderer: {e_oled_dgc}.")
    class oled_renderer:
        OLED_WIDTH = 128; OLED_HEIGHT = 64
        @staticmethod
        def pack_pil_image_to_7bit_stream(pil_image): return None
        @staticmethod
        def get_blank_packed_bitmap(): return bytearray(1176)
        @staticmethod
        def resource_path_func(relative_path): return os.path.join(PROJECT_ROOT_DGC, relative_path)
    OLED_RENDERER_LOADED_OK_DGC = False

# --- Game Configuration Constants (Exported or used by classes below) ---
SCREEN_WIDTH = 128
SCREEN_HEIGHT = 64
TARGET_FPS = 15
FOV_rad = math.pi / 2.8
MAX_RAY_DEPTH = 20
PLAYER_MAX_HP = 4
ENEMY_MAX_HP = 4
PAD_DOOM_FORWARD = 55
PAD_DOOM_BACKWARD = 71
PAD_DOOM_STRAFE_LEFT = 70   # User corrected: RED
PAD_DOOM_STRAFE_RIGHT = 72  # User corrected: RED
PAD_DOOM_TURN_LEFT_MAIN = 54  # User corrected: ORANGE
PAD_DOOM_TURN_RIGHT_MAIN = 56  # User corrected: ORANGE
PAD_DOOM_RUN = 84
PAD_DOOM_SHOOT = 85
PAD_DOOM_TURN_LEFT_ALT = 68
PAD_DOOM_TURN_RIGHT_ALT = 69
PAD_COLOR_DPAD_RED = (200, 0, 0)
PAD_COLOR_ORANGE = (255, 100, 0)
PAD_COLOR_BLUE_RUN = (0, 100, 255)
PAD_COLOR_SHOOT_GREEN = (0, 200, 0)
PAD_COLOR_OFF = (0, 0, 0)
PAD_COLOR_HEALTH_RED = (200, 0, 0)
PAD_COLOR_HIT_FLASH_RED = (255, 0, 0)

DIFFICULTY_NORMAL = "Normal"
DIFFICULTY_HARD = "Hard"
DIFFICULTY_VERY_HARD = "Very Hard"

# Difficulty settings dictionary
DIFFICULTY_PARAMS = {
    DIFFICULTY_NORMAL:    {"enemy_count": 5, "shoot_chance": 0.35, "shoot_timer_factors": (2.0, 4.0)},
    DIFFICULTY_HARD:      {"enemy_count": 5, "shoot_chance": 0.50, "shoot_timer_factors": (1.5, 3.0)},
    DIFFICULTY_VERY_HARD: {"enemy_count": 9, "shoot_chance": 0.75, "shoot_timer_factors": (1.0, 2.5)},
}


class MapGenerator:
    def __init__(self, width: int, height: int):
        self.width = width if width % 2 != 0 else width - 1
        self.height = height if height % 2 != 0 else height - 1
        if self.width < 5: self.width = 5
        if self.height < 5: self.height = 5
        self.map_grid = []
        self.player_start_coords_map = None
        self.player_start_angle_rad = 0
        self.enemy_spawn_candidates = []
        self.exit_coords_map = None

    def _is_valid(self, r: int, c: int, check_bounds_only=False) -> bool:
        if not (0 <= r < self.height and 0 <= c < self.width):
            return False
        if check_bounds_only:
            return True
        return self.map_grid[r][c] == 1

    def generate_maze(self):
        self.map_grid = [[1 for _ in range(self.width)] for _ in range(self.height)]
        self.enemy_spawn_candidates = []
        start_r, start_c = 1, 1 
        self.player_start_coords_map = (start_c, start_r)
        self.map_grid[start_r][start_c] = 0 
        self.enemy_spawn_candidates.append((start_c, start_r))
        stack = [(start_r, start_c)]
        first_carve_direction_vector = None
        while stack:
            current_r, current_c = stack[-1]
            possible_moves = [
                (0, 2, 0, 1, 0), (0, -2, 0, -1, math.pi),
                (2, 0, 1, 0, math.pi / 2), (-2, 0, -1, 0, -math.pi / 2)
            ]
            random.shuffle(possible_moves)
            moved = False
            for dr, dc, wall_dr, wall_dc, angle_sugg in possible_moves:
                next_r, next_c = current_r + dr, current_c + dc
                wall_r, wall_c = current_r + wall_dr, current_c + wall_dc
                if self._is_valid(next_r, next_c) and self.map_grid[next_r][next_c] == 1:
                    self.map_grid[wall_r][wall_c] = 0 
                    self.map_grid[next_r][next_c] = 0 
                    self.enemy_spawn_candidates.append((wall_c, wall_r))
                    self.enemy_spawn_candidates.append((next_c, next_r))
                    if (current_r, current_c) == (start_r, start_c) and first_carve_direction_vector is None:
                        self.player_start_angle_rad = angle_sugg
                        first_carve_direction_vector = (dc, dr)
                    stack.append((next_r, next_c))
                    moved = True
                    break
            if not moved:
                stack.pop()
        for r_idx in range(self.height):
            self.map_grid[r_idx][0] = 1
            self.map_grid[r_idx][self.width - 1] = 1
        for c_idx in range(self.width):
            self.map_grid[0][c_idx] = 1
            self.map_grid[self.height - 1][c_idx] = 1
        self.enemy_spawn_candidates = list(set(self.enemy_spawn_candidates))

    def get_map_as_text_list(self) -> list[str]:
        text_map = [["#" for _ in range(self.width)] for _ in range(self.height)]
        for r in range(self.height):
            for c in range(self.width):
                if self.map_grid[r][c] == 0:
                    text_map[r][c] = "."
        if self.player_start_coords_map:
            pc, pr = self.player_start_coords_map
            if 0 <= pr < self.height and 0 <= pc < self.width:
                text_map[pr][pc] = "S"
                if (pc,pr) in self.enemy_spawn_candidates:
                    self.enemy_spawn_candidates.remove((pc,pr))
        valid_exit_candidates = [
            (c,r) for c,r in self.enemy_spawn_candidates if (c,r) != self.player_start_coords_map
        ]
        if valid_exit_candidates:
            best_exit_candidate = None; max_dist_sq = -1
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
                if self.exit_coords_map in self.enemy_spawn_candidates:
                    self.enemy_spawn_candidates.remove(self.exit_coords_map)
        return ["".join(row) for row in text_map]

class RaycasterEngine(QObject):
    player_took_damage_signal = pyqtSignal()

    def __init__(self, screen_width=SCREEN_WIDTH, screen_height=SCREEN_HEIGHT, parent=None):
        super().__init__(parent)
        self.screen_width = screen_width
        self.screen_height = screen_height
        
        map_gen_width = 17
        map_gen_height = 11
        self.map_generator = MapGenerator(map_gen_width, map_gen_height)
        # generate_maze and get_map_as_text_list will be called in _parse_map_and_init_state
        
        self.player_angle_rad = 0 # Will be updated by map generator during parse
        
        self.game_map_tiles = [] 
        self.player_x = 1.5 
        self.player_y = 1.5 
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
            "pixels": ["00000000000000000000","00000001111110000000","00000011111111000000","00000111000011100000","00001100000000110000","00011000000000011000","00111111111111111100","01100000000000000110","01100000000000000110","01100000000000000110","00111000000000111000","0000111111111100000","0000011111111000000","00000000000000000000"]
        }
        self.gun_sprite_fire_data = { # Unchanged
            "width": 26, "height": 18,
            "pixels": ["00000000000000000000000000","00000000000110000000000000","00000000011111100000000000","00000001111111111000000000","00000111110001111100000000","00001111000000111100000000","00001100000000001100000000","0001100000000000011000000","001111111111111111110000","0110000000000000000110000","0110000000000000000110000","0110000000000000000110000","0011100000000000111000000","0000111111111111000000000","0000011111111100000000000","00000000000000000000000000","00000000000000000000000000","00000000000000000000000000"]
        }
        self.gun_fire_animation_frames = 2 
        self.gun_fire_timer = 0

        self.hardcoded_enemy_pixels = [[0,0,0,1,1,1,0,0,0],[0,0,1,1,1,1,1,0,0],[0,0,1,1,1,1,1,0,0],[0,0,0,1,1,1,0,0,0],[0,1,1,1,1,1,1,1,0],[1,1,0,1,1,1,0,1,1],[0,0,0,1,1,1,0,0,0],[0,0,0,1,1,1,0,0,0],[0,0,1,0,0,0,1,0,0],[0,1,1,0,0,0,1,1,0],[1,1,0,0,0,0,0,1,1],[1,0,0,0,0,0,0,0,1]]
        if self.hardcoded_enemy_pixels and len(self.hardcoded_enemy_pixels) > 0 and isinstance(self.hardcoded_enemy_pixels[0], list):
            self.hardcoded_enemy_width = len(self.hardcoded_enemy_pixels[0])
        else: self.hardcoded_enemy_width = 0 
        self.hardcoded_enemy_height = len(self.hardcoded_enemy_pixels)
        
        self.sprites = [] 

        # --- Difficulty Handling ---
        self.difficulty_level_name = DIFFICULTY_NORMAL # Default
        self.current_difficulty_params = DIFFICULTY_PARAMS[self.difficulty_level_name]
        # --- End Difficulty Handling ---
        
        self._parse_map_and_init_state() # Initial parse using the generated map & default difficulty

        self.z_buffer = [float('inf')] * self.screen_width 
        self.game_message = "" 
        self.game_over = False
        self.game_won = False

        self.message_font = ImageFont.load_default() 
        try:
            if OLED_RENDERER_LOADED_OK_DGC and hasattr(oled_renderer, 'resource_path_func'): 
                font_path = oled_renderer.resource_path_func(os.path.join("resources", "fonts", "TomThumb.ttf"))
                if os.path.exists(font_path): self.message_font = ImageFont.truetype(font_path, 48) 
            if not self.message_font or isinstance(self.message_font, str): self.message_font = ImageFont.truetype("arial.ttf", 24)
        except Exception: self.message_font = ImageFont.load_default()

    def _parse_map_and_init_state(self): # Removed num_enemies_to_place argument
        # If called on reset, regenerate the map
        if hasattr(self, 'map_generator'):
            self.map_generator.generate_maze()
            self.game_map_text_initial = self.map_generator.get_map_as_text_list()
            self.player_angle_rad = self.map_generator.player_start_angle_rad
        else: 
            print("WARNING: map_generator not found in _parse_map_and_init_state, using existing map text.")
        self.game_map_tiles = []
        self.sprites = [] 
        player_start_found = False
        temp_enemy_spawn_candidates = [] 
        for r_idx, row_str in enumerate(self.game_map_text_initial):
            map_row_tiles = []
            for c_idx, char_val in enumerate(row_str):
                tile_type = 0 
                if char_val == '#': tile_type = 1 
                elif char_val == 'S': self.player_x=c_idx+0.5; self.player_y=r_idx+0.5; player_start_found=True; tile_type=0 
                elif char_val == 'E': tile_type = 2; temp_enemy_spawn_candidates.append((c_idx, r_idx))
                elif char_val == '.': tile_type = 0; temp_enemy_spawn_candidates.append((c_idx, r_idx))
                map_row_tiles.append(tile_type)
            self.game_map_tiles.append(map_row_tiles)
        if not player_start_found: 
            print("CRITICAL WARNING: Player start 'S' not found. Defaulting."); self.player_x=1.5; self.player_y=1.5
            for r_f in range(len(self.game_map_tiles)):
                for c_f in range(len(self.game_map_tiles[0])):
                    if self.game_map_tiles[r_f][c_f] == 0:
                        self.player_x, self.player_y = c_f + 0.5, r_f + 0.5; player_start_found = True; break
                if player_start_found: break
            if not player_start_found: self.player_x, self.player_y = 1.5,1.5
            
        self.map_height=len(self.game_map_tiles); self.map_width=len(self.game_map_tiles[0]) if self.map_height > 0 else 0
        num_enemies_to_spawn = self.current_difficulty_params.get("enemy_count", 5)
        random.shuffle(temp_enemy_spawn_candidates); enemies_placed = 0
        for spawn_c, spawn_r in temp_enemy_spawn_candidates:
            if enemies_placed >= num_enemies_to_spawn: break # Use num_enemies_to_spawn
            if int(self.player_x) == spawn_c and int(self.player_y) == spawn_r: continue
            if not self._has_line_of_sight(spawn_c+0.5,spawn_r+0.5,self.player_x,self.player_y,max_los_distance=5.0):
                self.sprites.append({"x":spawn_c+0.5,"y":spawn_r+0.5,"type":"imp","id":f"imp_gen_{spawn_r}_{spawn_c}","width_def":self.hardcoded_enemy_width,"height_def":self.hardcoded_enemy_height,"pixels_def":self.hardcoded_enemy_pixels,"height_factor":0.7,"state":"idle","health":ENEMY_MAX_HP,"target_x":spawn_c+0.5,"target_y":spawn_r+0.5,"move_timer":random.randint(TARGET_FPS,TARGET_FPS*3),"shoot_timer":random.randint(TARGET_FPS*2,TARGET_FPS*4)}) # Shoot timer will be adjusted in update_ai
                enemies_placed +=1
        if enemies_placed < num_enemies_to_spawn: print(f"WARNING: Could only place {enemies_placed}/{num_enemies_to_spawn} enemies with no initial LOS.")
        self.player_hp=PLAYER_MAX_HP; self.game_message=""; self.game_over=False; self.game_won=False; self.player_hit_animation_timer=0; self.gun_fire_timer=0
        print(f"INFO: Game state re-initialized (Difficulty: {self.difficulty_level_name}). Map: {self.map_width}x{self.map_height}. Player Angle: {self.player_angle_rad:.2f}. Enemies: {enemies_placed}")

    def set_difficulty(self, difficulty_level_name: str):
        """Sets the game difficulty and updates relevant parameters."""
        self.difficulty_level_name = difficulty_level_name
        self.current_difficulty_params = DIFFICULTY_PARAMS.get(difficulty_level_name, DIFFICULTY_PARAMS[DIFFICULTY_NORMAL])
        print(f"RaycasterEngine: Difficulty set to {self.difficulty_level_name}. Params: {self.current_difficulty_params}")

    def _render_to_internal_buffer(self):
        for i in range(self.screen_width): self.z_buffer[i] = float('inf')
        self.draw_context.rectangle([(0,0), (self.screen_width, self.screen_height)], fill=0)
        for x in range(self.screen_width):
            camera_x = (2*x/self.screen_width)-1
            ray_a = self.player_angle_rad + math.atan(camera_x*math.tan(self.fov_rad/2.0))
            rdx, rdy = math.cos(ray_a), math.sin(ray_a)
            mcx, mcy = int(self.player_x), int(self.player_y)
            ddx = abs(1/rdx)if rdx!=0 else float('inf'); ddy = abs(1/rdy)if rdy!=0 else float('inf')
            sx, sy = 0,0; sdx, sdy = 0.0, 0.0
            if rdx<0: sx=-1; sdx=(self.player_x-mcx)*ddx 
            else: sx=1; sdx=(mcx+1.0-self.player_x)*ddx
            if rdy<0: sy=-1; sdy=(self.player_y-mcy)*ddy
            else: sy=1; sdy=(mcy+1.0-self.player_y)*ddy
            hit, side = False,0; wt=0
            for _ in range(self.max_ray_depth*max(self.map_width, self.map_height)):
                if sdx < sdy: sdx+=ddx; mcx+=sx; side=0
                else: sdy+=ddy; mcy+=sy; side=1
                if not(0<=mcx<self.map_width and 0<=mcy<self.map_height): break
                wt = self.game_map_tiles[mcy][mcx]
                if wt==1: hit=True; break
            if hit:
                pwd=0.0
                if side==0: pwd=(mcx-self.player_x+(1-sx)/2)/rdx if rdx!=0 else float('inf')
                else: pwd=(mcy-self.player_y+(1-sy)/2)/rdy if rdy!=0 else float('inf')
                if pwd<=0.01: pwd=0.01
                self.z_buffer[x]=pwd; lh=int(self.screen_height/pwd)
                ds=int(-lh/2+self.screen_height/2); de=int(lh/2+self.screen_height/2)
                if ds<0: ds=0
                if de>=self.screen_height: de=self.screen_height-1
                if side==1: self.draw_context.line([(x,ds),(x,de)],fill=255,width=1)
                else: 
                    for yp in range(ds,de+1):
                        if(x+yp)%2==0: self.draw_context.point((x,yp),fill=255)

    def _render_sprites(self):
        if not self.sprites: return
        visible_sprites=[s for s in self.sprites if s.get("state")!="dead"]
        if not visible_sprites: return
        sorted_sprites=sorted(visible_sprites,key=lambda s:math.sqrt((s["x"]-self.player_x)**2+(s["y"]-self.player_y)**2),reverse=True)
        for sprite in sorted_sprites:
            is_hardcoded_render_candidate=(sprite.get("type")=="imp" and sprite.get("pixels_def") is not None)
            if not is_hardcoded_render_candidate: continue
            sprite_x_rel,sprite_y_rel=sprite["x"]-self.player_x,sprite["y"]-self.player_y
            angle_to_sprite=math.atan2(sprite_y_rel,sprite_x_rel); angle_diff=angle_to_sprite-self.player_angle_rad
            while angle_diff < -math.pi: angle_diff+=2*math.pi
            while angle_diff > math.pi: angle_diff-=2*math.pi
            if abs(angle_diff) > (self.fov_rad/1.8): continue
            sprite_dist=math.sqrt(sprite_x_rel**2+sprite_y_rel**2)
            if sprite_dist < 0.5: continue
            try: sprite_screen_x=int((self.screen_width/2)*(1+math.tan(angle_diff)/math.tan(self.fov_rad/2)))
            except ZeroDivisionError: continue
            base_sprite_height_def=sprite.get("height_def",1)
            if base_sprite_height_def==0: base_sprite_height_def=1
            sprite_pixel_height_on_screen=int((self.screen_height/sprite_dist)*sprite.get('height_factor',1.0))
            if sprite_pixel_height_on_screen<=0: continue
            scale_factor_for_def_pixel=sprite_pixel_height_on_screen/base_sprite_height_def
            base_sprite_width_def=sprite.get("width_def",1)
            sprite_pixel_width_on_screen=int(base_sprite_width_def*scale_factor_for_def_pixel)
            if sprite_pixel_width_on_screen<=0: continue
            draw_start_y_sprite=int((self.screen_height-sprite_pixel_height_on_screen)/2)
            draw_start_x_sprite=sprite_screen_x-(sprite_pixel_width_on_screen//2)
            if sprite_pixel_width_on_screen>0 and sprite_pixel_height_on_screen>0:
                try:
                    sprite_definition_pixels=sprite.get("pixels_def")
                    if not sprite_definition_pixels: continue
                    outline_offsets=[(-1,-1),(0,-1),(1,-1),(-1,0),(1,0),(-1,1),(0,1),(1,1)]
                    outline_color_fill=255; body_color_fill=0
                    body_pixels_drawn_on_screen=set()
                    for def_y in range(len(sprite_definition_pixels)):
                        for def_x in range(len(sprite_definition_pixels[0])):
                            if sprite_definition_pixels[def_y][def_x]==1:
                                screen_px_start_x=draw_start_x_sprite+int(def_x*scale_factor_for_def_pixel)
                                screen_px_end_x=draw_start_x_sprite+int((def_x+1)*scale_factor_for_def_pixel)-1
                                screen_px_start_y=draw_start_y_sprite+int(def_y*scale_factor_for_def_pixel)
                                screen_px_end_y=draw_start_y_sprite+int((def_y+1)*scale_factor_for_def_pixel)-1
                                for current_screen_x in range(screen_px_start_x,screen_px_end_x+1):
                                    if 0<=current_screen_x<self.screen_width:
                                        if sprite_dist < self.z_buffer[current_screen_x]:
                                            for current_screen_y in range(screen_px_start_y,screen_px_end_y+1):
                                                if 0<=current_screen_y<self.screen_height:
                                                    self.draw_context.point((current_screen_x,current_screen_y),fill=body_color_fill)
                                                    body_pixels_drawn_on_screen.add((current_screen_x,current_screen_y))
                    pixels_for_outline_pass=list(body_pixels_drawn_on_screen)
                    for(body_x,body_y) in pixels_for_outline_pass:
                        for off_x,off_y in outline_offsets:
                            outline_x=body_x+off_x; outline_y=body_y+off_y
                            if 0<=outline_x<self.screen_width and 0<=outline_y<self.screen_height:
                                if(outline_x,outline_y) not in body_pixels_drawn_on_screen:
                                    if sprite_dist < self.z_buffer.get(outline_x,float('inf')):
                                        self.draw_context.point((outline_x,outline_y),fill=outline_color_fill)
                except Exception as e_sprite_render: pass

    def _draw_gun_sprite(self):
        gdu=self.gun_sprite_idle_data
        if self.gun_fire_timer>0: gdu=self.gun_sprite_fire_data; self.gun_fire_timer-=1
        gw,gh,gpx=gdu["width"],gdu["height"],gdu["pixels"]
        bco=self.gun_sprite_idle_data["width"]//2; fco=gw//2
        sx=(self.screen_width//2)-bco+(bco-fco); sy=self.screen_height-gh-self.gun_y_offset
        for r,rs in enumerate(gpx):
            for c,pc in enumerate(rs):
                if pc=='1':
                    ax,ay=sx+c,sy+r
                    if 0<=ax<self.screen_width and 0<=ay<self.screen_height: self.draw_context.point((ax,ay),fill=255)

    def _draw_hud(self):
        hpbh=3; hpby=self.screen_height-hpbh-1; hp_px_wph=(self.screen_width//3)//PLAYER_MAX_HP
        for i in range(self.player_hp):
            hpxs=2+(i*(hp_px_wph+1))
            self.draw_context.rectangle([(hpxs,hpby),(hpxs+hp_px_wph-1,hpby+hpbh-1)],fill=255)
        if self.player_hit_animation_timer > 0:
            if self.player_hit_animation_timer%2==0:
                for ig in range(0,self.screen_width,4):
                    self.draw_context.line([(ig,self.screen_height//2),(ig+2,self.screen_height//2)],fill=0)
                    self.draw_context.line([(ig,10),(ig+2,10)],fill=0)
                    self.draw_context.line([(ig,self.screen_height-10),(ig+2,self.screen_height-10)],fill=0)
            self.player_hit_animation_timer-=1
        if self.game_over and self.game_message:
            fnt=self.message_font if self.message_font else ImageFont.load_default()
            try:
                bb=self.draw_context.textbbox((0,0),self.game_message,font=fnt)
                tw=bb[2]-bb[0]; th=bb[3]-bb[1]
                tx=(self.screen_width-tw)//2; ty=(self.screen_height-th)//2
                self.draw_context.text((tx,ty),self.game_message,font=fnt,fill=255)
            except Exception as e: # Fallback if textbbox fails
                est_char_w = fnt.getsize("A")[0] if hasattr(fnt, 'getsize') else 6
                tw = len(self.game_message) * est_char_w
                th = fnt.getsize("A")[1] if hasattr(fnt, 'getsize') else 8
                tx=(self.screen_width-tw)//2; ty=(self.screen_height-th)//2
                self.draw_context.text((tx,ty),self.game_message,font=fnt,fill=255)

    def fire_gun(self):
        if self.game_over: return
        self.gun_fire_timer=self.gun_fire_animation_frames; print("Player fires!")
        mhr=10.0; htsi=-1; mdths=float('inf')
        for i,sp in enumerate(self.sprites):
            if sp.get("state")=="dead" or sp.get("type")!="imp": continue
            dx,dy=sp["x"]-self.player_x,sp["y"]-self.player_y; dtsc=math.sqrt(dx*dx+dy*dy)
            if not(0.1<dtsc<=mhr): continue
            ats=math.atan2(dy,dx); ad=ats-self.player_angle_rad
            while ad<-math.pi:ad+=2*math.pi
            while ad>math.pi:ad-=2*math.pi
            hca=0.25
            if abs(ad)<hca:
                if dtsc<mdths: htsi=i; mdths=dtsc
        if htsi!=-1:
            hs=self.sprites[htsi]; print(f"Hit Imp {hs.get('id','unk')}!")
            hs["health"]-=1
            if hs["health"]<=0: hs["state"]="dead";print(f"Imp {hs.get('id','unk')} DIES!")
        else: print("Missed!")

    def update_movement_speed(self, is_running: bool):
        self.is_running = is_running
        self.current_move_speed = self.base_move_speed * (self.run_speed_multiplier if self.is_running else 1.0)

    def move_forward(self): nx=self.player_x+math.cos(self.player_angle_rad)*self.current_move_speed; ny=self.player_y+math.sin(self.player_angle_rad)*self.current_move_speed; self._try_move(nx,ny)

    def move_backward(self): nx=self.player_x-math.cos(self.player_angle_rad)*self.current_move_speed; ny=self.player_y-math.sin(self.player_angle_rad)*self.current_move_speed; self._try_move(nx,ny)

    def turn_left(self): self.player_angle_rad=(self.player_angle_rad-self.turn_speed)%(2*math.pi)

    def turn_right(self): self.player_angle_rad=(self.player_angle_rad+self.turn_speed)%(2*math.pi)

    def strafe_left(self): sa=self.player_angle_rad-math.pi/2; nx=self.player_x+math.cos(sa)*self.current_move_speed; ny=self.player_y+math.sin(sa)*self.current_move_speed; self._try_move(nx,ny)

    def strafe_right(self): sa=self.player_angle_rad+math.pi/2; nx=self.player_x+math.cos(sa)*self.current_move_speed; ny=self.player_y+math.sin(sa)*self.current_move_speed; self._try_move(nx,ny)

    def _try_move(self, new_x, new_y):
        current_map_x, current_map_y = int(self.player_x), int(self.player_y)
        target_map_x, target_map_y = int(new_x), int(new_y)
        # print(
            # f"DEBUG_MOVE: Attempting move from ({self.player_x:.2f}, {self.player_y:.2f}) -> ({new_x:.2f}, {new_y:.2f})")
        # print(
            # f"DEBUG_MOVE: Current map tile: ({current_map_x}, {current_map_y}). Target map tile: ({target_map_x}, {target_map_y})")
        if not (0 <= target_map_x < self.map_width and 0 <= target_map_y < self.map_height):
            # print(
                # f"DEBUG_MOVE: Blocked! Target ({target_map_x},{target_map_y}) is out of map bounds ({self.map_width}x{self.map_height}).")
            return
        tile_type_at_target = self.game_map_tiles[target_map_y][target_map_x]
        if tile_type_at_target == 1:
            # print(
                # f"DEBUG_MOVE: Blocked! Target map tile ({target_map_x},{target_map_y}) is a WALL (type {tile_type_at_target}).")
            return
        # print(
            # f"DEBUG_MOVE: Allowed! Moving to ({new_x:.2f}, {new_y:.2f}). Target tile type: {tile_type_at_target}")
        self.player_x, self.player_y = new_x, new_y

    def _has_line_of_sight(self, x1: float, y1: float, x2: float, y2: float, max_los_distance: float) -> bool:
        dx=x2-x1; dy=y2-y1; distance_to_target=math.sqrt(dx*dx+dy*dy)
        if distance_to_target==0: return True 
        if distance_to_target > max_los_distance: return False
        ray_dir_x=dx/distance_to_target; ray_dir_y=dy/distance_to_target
        current_check_x=x1; current_check_y=y1; map_check_x=int(current_check_x); map_check_y=int(current_check_y)
        delta_dist_x=abs(1/ray_dir_x) if ray_dir_x!=0 else float('inf'); delta_dist_y=abs(1/ray_dir_y) if ray_dir_y!=0 else float('inf')
        step_x,step_y=0,0; side_dist_x,side_dist_y=0.0,0.0
        if ray_dir_x < 0: step_x=-1; side_dist_x=(current_check_x-map_check_x)*delta_dist_x
        else: step_x=1; side_dist_x=(map_check_x+1.0-current_check_x)*delta_dist_x
        if ray_dir_y < 0: step_y=-1; side_dist_y=(current_check_y-map_check_y)*delta_dist_y
        else: step_y=1; side_dist_y=(map_check_y+1.0-current_check_y)*delta_dist_y
        dist_travelled=0
        while dist_travelled < distance_to_target:
            if side_dist_x < side_dist_y: dist_travelled=side_dist_x; side_dist_x+=delta_dist_x; map_check_x+=step_x
            else: dist_travelled=side_dist_y; side_dist_y+=delta_dist_y; map_check_y+=step_y
            if not (0 <= map_check_x < self.map_width and 0 <= map_check_y < self.map_height): return False
            if self.game_map_tiles[map_check_y][map_check_x] == 1: return False
            if map_check_x == int(x2) and map_check_y == int(y2): return True
        return True

    def get_current_frame_pil(self) -> Image.Image :
        if not self.game_over: 
            self._render_to_internal_buffer(); self._render_sprites(); self._draw_gun_sprite()          
        else: self.draw_context.rectangle([(0,0),(self.screen_width,self.screen_height)],fill=0)
        self._draw_hud() 
        return self.current_frame_image

    def get_packed_oled_frame(self) -> bytearray | None:
        if not OLED_RENDERER_LOADED_OK_DGC:  # Use the flag scoped to this file
            print(
                "DEBUG_ENGINE: OLED_RENDERER_LOADED_OK_DGC is False, returning None for packed_frame.")
            return None
        img = self.get_current_frame_pil()
        if img is None:
            print("DEBUG_ENGINE: get_current_frame_pil() returned None.")
            return None
        # print(f"DEBUG_ENGINE: get_current_frame_pil() returned Image: Mode={img.mode}, Size={img.size}") # Optional detailed
        packed_data = oled_renderer.pack_pil_image_to_7bit_stream(img)
        if packed_data is None:
            print(
                "DEBUG_ENGINE: oled_renderer.pack_pil_image_to_7bit_stream(img) returned None.")
        # else:
            # print(f"DEBUG_ENGINE: pack_pil_image_to_7bit_stream returned data of length {len(packed_data)}")
        return packed_data

    def update_ai_and_game_state(self):
        if self.game_over: return
        # Get difficulty-specific parameters for AI
        shoot_chance = self.current_difficulty_params.get("shoot_chance", 0.35)
        timer_factor_min, timer_factor_max = self.current_difficulty_params.get("shoot_timer_factors", (2.0, 4.0))
        
        min_shoot_timer_ticks = int(TARGET_FPS * timer_factor_min)
        max_shoot_timer_ticks = int(TARGET_FPS * timer_factor_max)
        if min_shoot_timer_ticks < 1 : min_shoot_timer_ticks = 1 # Ensure timer is at least 1 tick
        if max_shoot_timer_ticks < min_shoot_timer_ticks : max_shoot_timer_ticks = min_shoot_timer_ticks + int(TARGET_FPS) # Ensure max > min
        for i, sprite in reversed(list(enumerate(self.sprites))): 
            if sprite["type"] == "imp" and sprite["state"] != "dead":
                sprite["move_timer"] -= 1
                sprite["shoot_timer"] -= 1
                if sprite["move_timer"] <= 0:
                    sprite["move_timer"] = random.randint(TARGET_FPS, TARGET_FPS * 3) # Movement jitter unchanged by difficulty for now
                    rox, roy = (random.random()-0.5)*0.8, (random.random()-0.5)*0.8
                    nsx, nsy = sprite["x"]+rox, sprite["y"]+roy
                    mtx, mty = int(nsx), int(nsy)
                    if 0<=mtx<self.map_width and 0<=mty<self.map_height and self.game_map_tiles[mty][mtx]==0:
                        sprite["x"], sprite["y"] = nsx, nsy
                
                if sprite["shoot_timer"] <= 0:
                    # Reset shoot timer based on difficulty
                    sprite["shoot_timer"] = random.randint(min_shoot_timer_ticks, max_shoot_timer_ticks)
                    
                    dist_to_player = math.sqrt((self.player_x - sprite["x"])**2 + (self.player_y - sprite["y"])**2)
                    
                    can_shoot_player = False
                    if dist_to_player < 7.0: 
                        if self._has_line_of_sight(sprite["x"], sprite["y"], self.player_x, self.player_y, dist_to_player + 0.1):
                            if random.random() < shoot_chance: # Use difficulty-based shoot_chance
                                can_shoot_player = True
                    
                    if can_shoot_player:
                        print(f"Imp {sprite.get('id','unknown')} shoots at player (LOS confirmed, Diff: {self.difficulty_level_name})!")
                        self.player_hp -= 1
                        self.player_hit_animation_timer = self.player_hit_animation_frames
                        self.player_took_damage_signal.emit()
                        if self.player_hp <= 0:
                            self.player_hp = 0; self.game_message = "YOU DIED"; self.game_over = True; self.game_won = False
                            print("GAME OVER - Player Died"); return 
        imps_alive = any(s["type"] == "imp" and s.get("state") != "dead" for s in self.sprites)
        if not imps_alive:
            initial_imps_existed = any(s["type"] == "imp" for s in self.sprites)
            if initial_imps_existed: 
                self.game_message="YOU WIN!"; self.game_over=True; self.game_won=True
                print("GAME OVER - Player Won! (All Imps Defeated)")

class DoomGameController(QObject):
    frame_ready_for_oled_signal = pyqtSignal(bytes)
    game_over_signal = pyqtSignal(str, bool)
    HP_PAD_COORDS_DGC = [(3,0), (3,1), (3,2), (3,3)]
    PAD_COLOR_HEALTH_RED_DGC = (200, 0, 0)
    PAD_COLOR_OFF_DGC = (0, 0, 0)

    DOOM_CONTROL_PAD_LAYOUT = {
        (0, 1): PAD_DOOM_FORWARD, (1, 1): PAD_DOOM_BACKWARD,
        (1, 0): PAD_DOOM_STRAFE_LEFT, (1, 2): PAD_DOOM_STRAFE_RIGHT,  # These are RED
        # These are ORANGE
        (0, 0): PAD_DOOM_TURN_LEFT_MAIN, (0, 2): PAD_DOOM_TURN_RIGHT_MAIN,
        # These are ORANGE
        (0, 14): PAD_DOOM_TURN_LEFT_ALT, (0, 15): PAD_DOOM_TURN_RIGHT_ALT,
        (1, 14): PAD_DOOM_RUN, (1, 15): PAD_DOOM_SHOOT,
    }

    def __init__(self, akai_controller_ref, initial_difficulty_level: str = DIFFICULTY_NORMAL, parent=None): # Add initial_difficulty
        super().__init__(parent)
        print(f"DoomGameController: Initializing with difficulty '{initial_difficulty_level}'...")
        self.akai_controller = akai_controller_ref
        
        self.current_difficulty_level = initial_difficulty_level # Store difficulty
        # Pass difficulty to RaycasterEngine when creating it
        self.engine = RaycasterEngine() # RaycasterEngine's __init__ now sets its own default
        self.engine.set_difficulty(self.current_difficulty_level) # Explicitly set it
        
        self.game_timer = QTimer(self)
        self.game_timer.timeout.connect(self._game_loop_tick)
        
        self.is_game_running = False
        self.is_restart_prompt_active = False
        self.pad_key_states = {
            PAD_DOOM_FORWARD: False, PAD_DOOM_BACKWARD: False, 
            PAD_DOOM_STRAFE_LEFT: False, PAD_DOOM_STRAFE_RIGHT: False,
            PAD_DOOM_TURN_LEFT_MAIN: False, PAD_DOOM_TURN_RIGHT_MAIN: False, 
            PAD_DOOM_TURN_LEFT_ALT: False, PAD_DOOM_TURN_RIGHT_ALT: False,
            PAD_DOOM_RUN: False, PAD_DOOM_SHOOT: False,
        }
        self.game_over_effects_timer = QTimer(self)
        self.game_over_effects_timer.timeout.connect(self._handle_game_over_effects_on_pads)
        self.death_flash_count = 0
        self.restart_pad_blink_state = False
        
        self._pad_hit_flash_timer = QTimer(self)
        self._pad_hit_flash_timer.setSingleShot(True)
        self._pad_hit_flash_timer.timeout.connect(self._clear_hit_flash_and_restore_lights)
        print("DoomGameController: Initialization complete.")

    def start_game(self): # Removed difficulty_level_override argument
        """Starts/Resets the DOOM game using the currently set difficulty."""
        print(f"DoomGameController: Starting game with difficulty '{self.current_difficulty_level}'...")
        if not self.akai_controller or not self.akai_controller.is_connected():
            print("DoomGameController ERROR: Akai Fire not connected. Cannot start game.")
            return
        if hasattr(self.akai_controller, 'clear_all_pads'): 
            self.akai_controller.clear_all_pads() 
            time.sleep(0.02) 
        self.is_game_running = True
        self.is_restart_prompt_active = False
        if self.game_over_effects_timer.isActive():
            self.game_over_effects_timer.stop()
        for key in self.pad_key_states: 
            self.pad_key_states[key] = False
        
        # Ensure engine has the correct difficulty BEFORE parsing map (which places enemies)
        if hasattr(self.engine, 'set_difficulty'):
            self.engine.set_difficulty(self.current_difficulty_level)
        else: # Fallback or error if method is missing
            print("DGC WARNING: RaycasterEngine missing set_difficulty method!")
        self.engine._parse_map_and_init_state() # Engine now uses its internal difficulty
        if hasattr(self.engine, 'player_took_damage_signal'):
            try: 
                self.engine.player_took_damage_signal.disconnect(self._on_player_took_damage)
            except TypeError: pass 
            self.engine.player_took_damage_signal.connect(self._on_player_took_damage)
        self._setup_doom_control_pad_lights() 
        self._update_doom_hp_on_pads()      
        self.game_timer.start(int(1000 / TARGET_FPS))
        print("DoomGameController: Game started.")

    def stop_game(self):
        """Stops the DOOM game and cleans up."""
        print("DoomGameController: Stopping game...")
        self.is_game_running = False
        if self.game_timer.isActive():
            self.game_timer.stop()
        if self.game_over_effects_timer.isActive():
            self.game_over_effects_timer.stop()
        if self._pad_hit_flash_timer.isActive():
            self._pad_hit_flash_timer.stop()

        self.is_restart_prompt_active = False

        if hasattr(self.engine, 'player_took_damage_signal'):
            try:
                self.engine.player_took_damage_signal.disconnect(
                    self._on_player_took_damage)
            except TypeError:
                pass

        self._clear_all_doom_game_pads()

        if OLED_RENDERER_LOADED_OK_DGC:
            blank_pil = Image.new(
                '1', (oled_renderer.OLED_WIDTH, oled_renderer.OLED_HEIGHT), 0)
            packed_blank_bytearray = oled_renderer.pack_pil_image_to_7bit_stream(
                blank_pil)
            if packed_blank_bytearray:
                # --- CONVERT TO bytes ---
                packed_blank_bytes = bytes(packed_blank_bytearray)
                self.frame_ready_for_oled_signal.emit(packed_blank_bytes)
                # --- END CONVERSION ---
        print("DoomGameController: Game stopped.")

    def _on_player_took_damage(self):
        self._update_doom_hp_on_pads(); self._flash_hit_effect_on_pads()

    def _game_loop_tick(self):
        if not self.is_game_running:
            return

        # Handle game over state transition
        if self.engine.game_over and not self.is_restart_prompt_active:
            if self.game_timer.isActive():
                self.game_timer.stop()
            print(
                f"DoomGameController: Game Over! Message: '{self.engine.game_message}'")

            # Inform MainWindow about the game over state
            self.game_over_signal.emit(
                self.engine.game_message, self.engine.game_won)

            # Start the pad effects sequence for game over
            self.death_flash_count = 0
            self.game_over_effects_timer.start(120)
            self.is_game_running = False  # Mark as not running main game logic
            return

        # If restart prompt is active (from game over effects), main game logic should not run
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
        # Render and emit frame for OLED
        # This returns bytearray | None
        packed_frame_bytearray = self.engine.get_packed_oled_frame()
        if packed_frame_bytearray is not None and isinstance(packed_frame_bytearray, bytearray):
            # print(f"DEBUG_DGC_TICK: Got packed_frame_bytearray, len={len(packed_frame_bytearray)}") # Optional
            packed_frame_bytes = bytes(packed_frame_bytearray)
            self.frame_ready_for_oled_signal.emit(packed_frame_bytes)
        else:
            print(
                f"DEBUG_DGC_TICK: packed_frame_bytearray is None or not a bytearray. Type: {type(packed_frame_bytearray)}. Skipping emit.")

    def handle_pad_event(self, note: int, is_pressed: bool):
        # Keep one main print to see if events are reaching DGC, can be commented later
        # print(f"DGC_PAD_EVENT: Note={note}(0x{note:02X}), Pressed={is_pressed}, RestartPrompt={self.is_restart_prompt_active}, GameRun={self.is_game_running}")

        if self.is_restart_prompt_active:
            if note == PAD_DOOM_SHOOT and is_pressed:
                # Keep this important action print
                print("DoomGameController: ACTION - Restart triggered by SHOOT Button!")
                self.is_restart_prompt_active = False
                if self.game_over_effects_timer.isActive():
                    self.game_over_effects_timer.stop()

                # --- THIS IS THE CRITICAL FIX ---
                self.start_game()  # This re-initializes engine, lights, and starts game_timer
                # --- END CRITICAL FIX ---
            return  # Always return after handling/checking restart prompt input

        # If game is not actually running (e.g., before first start, or after game over effects finished but before restart),
        # don't process normal game inputs.
        # self.engine.game_over will be true during the game over effects sequence.
        if not self.is_game_running:
            # If it's game over, and we are NOT in restart prompt, something is odd, but still ignore game input.
            # print(f"DGC_PAD_EVENT: Game not running (is_game_running={self.is_game_running}). Ignoring normal input.") # Optional debug
            return

        # If game is over (engine flag) but we're somehow not in restart_prompt_active state yet,
        # also ignore regular game inputs. The game_loop_tick will handle transitioning to effects.
        if self.engine.game_over:
            # print(f"DGC_PAD_EVENT: Engine game_over is True, but not in restart prompt. Ignoring normal input.") # Optional debug
            return

        # Process normal game inputs if game is running and not game over
        if note in self.pad_key_states:
            self.pad_key_states[note] = is_pressed
            # print(f"DGC_PAD_EVENT: Updated pad_key_states[{note}] to {is_pressed}") # Can comment this out
            if note == PAD_DOOM_SHOOT and is_pressed:
                self.engine.fire_gun()
        # else:
            # print(f"DGC_PAD_EVENT: Note {note} not in pad_key_states.") # Can comment this out

    def _setup_doom_control_pad_lights(self):
        if not self.akai_controller or not self.akai_controller.is_connected(): return
        pad_colors = {
            PAD_DOOM_FORWARD: PAD_COLOR_DPAD_RED, PAD_DOOM_BACKWARD: PAD_COLOR_DPAD_RED,
            PAD_DOOM_STRAFE_LEFT: PAD_COLOR_DPAD_RED, PAD_DOOM_STRAFE_RIGHT: PAD_COLOR_DPAD_RED # Corrected
            ,PAD_DOOM_TURN_LEFT_MAIN: PAD_COLOR_ORANGE, PAD_DOOM_TURN_RIGHT_MAIN: PAD_COLOR_ORANGE # Corrected
            ,PAD_DOOM_TURN_LEFT_ALT: PAD_COLOR_ORANGE, PAD_DOOM_TURN_RIGHT_ALT: PAD_COLOR_ORANGE,
            PAD_DOOM_RUN: PAD_COLOR_BLUE_RUN, PAD_DOOM_SHOOT: PAD_COLOR_SHOOT_GREEN,
        }
        pads_to_set = []
        # Using DoomOLEDTestWindow.PAD_LAYOUT_FOR_DOOM_GAME as the source of truth for layout
        # This constant should ideally be moved to this file or a shared constants file later.
        temp_pad_layout = { # Copied from previous DoomOLEDTestWindow for direct use
            (0,1):PAD_DOOM_FORWARD,(1,1):PAD_DOOM_BACKWARD,(1,0):PAD_DOOM_STRAFE_LEFT,(1,2):PAD_DOOM_STRAFE_RIGHT,
            (0,0):PAD_DOOM_TURN_LEFT_MAIN,(0,2):PAD_DOOM_TURN_RIGHT_MAIN,(0,14):PAD_DOOM_TURN_LEFT_ALT,
            (0,15):PAD_DOOM_TURN_RIGHT_ALT,(1,14):PAD_DOOM_RUN,(1,15):PAD_DOOM_SHOOT,
        }
        all_doom_coords = set(temp_pad_layout.keys()) | set(self.HP_PAD_COORDS_DGC)
        for r in range(4):
            for c in range(16):
                if (r,c) in all_doom_coords: pads_to_set.append((r,c, *self.PAD_COLOR_OFF_DGC))
        for (r,c), note in temp_pad_layout.items():
            color = pad_colors.get(note, self.PAD_COLOR_OFF_DGC)
            # Update if exists, else append (safer: build list of (r,c,color) then send)
            updated_in_list = False
            for i_s, (pr_s, pc_s, _,_,_) in enumerate(pads_to_set):
                if pr_s == r and pc_s == c:
                    pads_to_set[i_s] = (r,c, *color); updated_in_list = True; break
            if not updated_in_list: pads_to_set.append((r,c, *color))
        if hasattr(self.akai_controller,'set_multiple_pads_color') and pads_to_set: self.akai_controller.set_multiple_pads_color(pads_to_set,False)

    def _update_doom_hp_on_pads(self):
        if not self.akai_controller or not self.akai_controller.is_connected(): return
        hp = self.engine.player_hp; data = []
        for i in range(PLAYER_MAX_HP):
            if i < len(self.HP_PAD_COORDS_DGC):
                r,c = self.HP_PAD_COORDS_DGC[i]
                color = self.PAD_COLOR_HEALTH_RED_DGC if i < hp else self.PAD_COLOR_OFF_DGC
                data.append((r,c, *color))
        if hasattr(self.akai_controller,'set_multiple_pads_color') and data: self.akai_controller.set_multiple_pads_color(data,False)

    def _flash_hit_effect_on_pads(self):
        if not self.akai_controller or not self.akai_controller.is_connected() or self.engine.game_over: return
        flash_data = []
        # Use temp_pad_layout as defined in _setup_doom_control_pad_lights for consistency
        temp_pad_layout = { (0,1):PAD_DOOM_FORWARD,(1,1):PAD_DOOM_BACKWARD,(1,0):PAD_DOOM_STRAFE_LEFT,(1,2):PAD_DOOM_STRAFE_RIGHT,(0,0):PAD_DOOM_TURN_LEFT_MAIN,(0,2):PAD_DOOM_TURN_RIGHT_MAIN,(0,14):PAD_DOOM_TURN_LEFT_ALT,(0,15):PAD_DOOM_TURN_RIGHT_ALT,(1,14):PAD_DOOM_RUN,(1,15):PAD_DOOM_SHOOT, }
        control_coords = set(temp_pad_layout.keys()); hp_coords = set(self.HP_PAD_COORDS_DGC)
        for r in range(4):
            for c in range(16):
                if (r,c) not in control_coords and (r,c) not in hp_coords: flash_data.append((r,c,*PAD_COLOR_HIT_FLASH_RED))
        if hasattr(self.akai_controller,'set_multiple_pads_color') and flash_data: self.akai_controller.set_multiple_pads_color(flash_data,True)
        if self._pad_hit_flash_timer.isActive():self._pad_hit_flash_timer.stop()
        self._pad_hit_flash_timer.start(80)

    def _clear_hit_flash_and_restore_lights(self):
        print("DGC_DEBUG: _clear_hit_flash_and_restore_lights called.")
        if not self.akai_controller or not self.akai_controller.is_connected():
            return

        # Check engine existence before accessing attributes
        if not hasattr(self, 'engine') or self.engine.game_over:
            if hasattr(self, '_clear_all_doom_game_pads'):  # Check if method exists
                self._clear_all_doom_game_pads()
            return

        pads_to_turn_off_after_flash = []
        temp_pad_layout_keys = self._get_current_pad_layout_keys()
        hp_coords_set = set(self.HP_PAD_COORDS_DGC)

        for r in range(4):
            for c in range(16):
                if (r, c) not in temp_pad_layout_keys and (r, c) not in hp_coords_set:
                    pads_to_turn_off_after_flash.append(
                        (r, c, *self.PAD_COLOR_OFF_DGC))

        if hasattr(self.akai_controller, 'set_multiple_pads_color') and pads_to_turn_off_after_flash:
            self.akai_controller.set_multiple_pads_color(
                pads_to_turn_off_after_flash, bypass_global_brightness=True)
        elif pads_to_turn_off_after_flash:
            for r_off, c_off, _, _, _ in pads_to_turn_off_after_flash:
                self.akai_controller.set_pad_color(
                    r_off, c_off, *self.PAD_COLOR_OFF_DGC)

        if hasattr(self, '_setup_doom_control_pad_lights'):  # Check method existence
            self._setup_doom_control_pad_lights()

        if hasattr(self, '_update_doom_hp_on_pads'):  # Check method existence
            self._update_doom_hp_on_pads()

    def _get_current_pad_layout_keys(self) -> set:
        # This should ideally fetch from a constant defined within DGC or passed to it.
        # Using the corrected color mapping for consistency checks if needed later:
        # PAD_DOOM_STRAFE_LEFT/RIGHT = RED
        # PAD_DOOM_TURN_LEFT/RIGHT_MAIN = ORANGE
        temp_pad_layout = {
            (0, 1): PAD_DOOM_FORWARD, (1, 1): PAD_DOOM_BACKWARD,
            (1, 0): PAD_DOOM_STRAFE_LEFT, (1, 2): PAD_DOOM_STRAFE_RIGHT,
            (0, 0): PAD_DOOM_TURN_LEFT_MAIN, (0, 2): PAD_DOOM_TURN_RIGHT_MAIN,
            (0, 14): PAD_DOOM_TURN_LEFT_ALT, (0, 15): PAD_DOOM_TURN_RIGHT_ALT,
            (1, 14): PAD_DOOM_RUN, (1, 15): PAD_DOOM_SHOOT,
        }
        return set(temp_pad_layout.keys())

    def _handle_game_over_effects_on_pads(self):
        if not self.akai_controller or not self.akai_controller.is_connected():
            if self.game_over_effects_timer.isActive():
                self.game_over_effects_timer.stop()
            return

        # Phase 1: Full pad flashes - GREEN for win, RED for lose
        if self.death_flash_count < 10: 
            effect_data = []
            is_flash_on = (self.death_flash_count % 2 == 0)
            
            # Choose color based on win/lose state
            if self.engine.game_won:
                color_for_effect = PAD_COLOR_SHOOT_GREEN if is_flash_on else self.PAD_COLOR_OFF_DGC
            else:
                color_for_effect = PAD_COLOR_HIT_FLASH_RED if is_flash_on else self.PAD_COLOR_OFF_DGC

            for r in range(4): 
                for c in range(16): 
                    effect_data.append((r, c, *color_for_effect))
            
            if hasattr(self.akai_controller, 'set_multiple_pads_color') and effect_data:
                self.akai_controller.set_multiple_pads_color(effect_data, bypass_global_brightness=is_flash_on) 

            self.death_flash_count += 1
            # Ensure timer interval is set correctly for flashing
            if not self.game_over_effects_timer.isActive() or self.game_over_effects_timer.interval() != 120:
                self.game_over_effects_timer.setInterval(120)
        
        # Phase 2: Restart Prompt on OLED and blinking SHOOT pad
        else:
            self.is_restart_prompt_active = True 
            
            self.engine.game_message = "Restart?" 
            packed_frame_bytearray = self.engine.get_packed_oled_frame() # Returns bytearray | None
             
            # --- CONVERT TO bytes BEFORE EMITTING ---
            if packed_frame_bytearray:
                packed_frame_bytes = bytes(packed_frame_bytearray)
                self.frame_ready_for_oled_signal.emit(packed_frame_bytes)
            # --- END CONVERSION ---

            self.restart_pad_blink_state = not self.restart_pad_blink_state 
            
            blink_pad_rc_to_use = None
            # Get the layout keys from our helper or use the temp_pad_layout directly
            temp_pad_layout_keys = self._get_current_pad_layout_keys() # Assuming this returns the (r,c) set for D-Pad
            
            # To find the (r,c) for PAD_DOOM_SHOOT, we need the actual layout mapping
            # For now, using the hardcoded reference from _get_current_pad_layout_keys if it were to return the full dict
            # Better: Define PAD_LAYOUT_FOR_DOOM_GAME within DGC or pass it.
            # Using the known (1,15) for PAD_DOOM_SHOOT from earlier setup.
            # This needs to be robust by actually looking up PAD_DOOM_SHOOT in the layout used by _setup_doom_control_pad_lights
            
            # Robust way to find the SHOOT pad coordinates:
            dgc_pad_layout = { # This should ideally be a class constant or passed in
                (0,1):PAD_DOOM_FORWARD,(1,1):PAD_DOOM_BACKWARD,(1,0):PAD_DOOM_STRAFE_LEFT,(1,2):PAD_DOOM_STRAFE_RIGHT,
                (0,0):PAD_DOOM_TURN_LEFT_MAIN,(0,2):PAD_DOOM_TURN_RIGHT_MAIN,(0,14):PAD_DOOM_TURN_LEFT_ALT,
                (0,15):PAD_DOOM_TURN_RIGHT_ALT,(1,14):PAD_DOOM_RUN,(1,15):PAD_DOOM_SHOOT,
            }
            for (r_search, c_search), note_val_search in dgc_pad_layout.items():
                if note_val_search == PAD_DOOM_SHOOT: 
                    blink_pad_rc_to_use = (r_search, c_search)
                    break
            
            # Clear all pads first (except the one that will blink if for_restart_blink is smart)
            self._clear_all_doom_game_pads(for_restart_blink=True) 

            if blink_pad_rc_to_use:
                # Use GREEN for win, original GREEN for lose (SHOOT button color)
                color_for_blink = PAD_COLOR_SHOOT_GREEN if self.restart_pad_blink_state else self.PAD_COLOR_OFF_DGC
                self.akai_controller.set_pad_color(blink_pad_rc_to_use[0], blink_pad_rc_to_use[1], *color_for_blink)
            else:
                print("DGC WARNING: Could not find SHOOT pad coordinates for blinking restart prompt.")
            
            # Ensure timer interval is set correctly for blinking
            if not self.game_over_effects_timer.isActive() or self.game_over_effects_timer.interval() != 350:
                self.game_over_effects_timer.setInterval(350)

    def _clear_all_doom_game_pads(self, for_restart_blink=False):
        if not self.akai_controller or not self.akai_controller.is_connected(): return
        pads_to_clear=[]
        # Use temp_pad_layout again
        temp_pad_layout = { (0,1):PAD_DOOM_FORWARD,(1,1):PAD_DOOM_BACKWARD,(1,0):PAD_DOOM_STRAFE_LEFT,(1,2):PAD_DOOM_STRAFE_RIGHT,(0,0):PAD_DOOM_TURN_LEFT_MAIN,(0,2):PAD_DOOM_TURN_RIGHT_MAIN,(0,14):PAD_DOOM_TURN_LEFT_ALT,(0,15):PAD_DOOM_TURN_RIGHT_ALT,(1,14):PAD_DOOM_RUN,(1,15):PAD_DOOM_SHOOT, }
        all_coords = set(temp_pad_layout.keys()) | set(self.HP_PAD_COORDS_DGC)
        for r in range(4):
            for c in range(16):
                if (r,c) in all_coords:
                    if for_restart_blink:
                        is_shoot=False
                        for (sr,sc),note in temp_pad_layout.items():
                            if note == PAD_DOOM_SHOOT and sr==r and sc==c: is_shoot=True; break
                        if not is_shoot: pads_to_clear.append((r,c,*self.PAD_COLOR_OFF_DGC))
                    else: pads_to_clear.append((r,c,*self.PAD_COLOR_OFF_DGC))
        if hasattr(self.akai_controller,'set_multiple_pads_color') and pads_to_clear: self.akai_controller.set_multiple_pads_color(pads_to_clear,True)
