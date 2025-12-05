"""
Racing Scaffold - Throttle/Fuel/Heat Prototype
Arrow keys: Left/Right to steer, Up/Down to adjust throttle (Hold for fine control)
Space: Nitro burst
"""

import pygame
import random

# ============================================================================
# TUNING CONSTANTS - tweak these to feel out the systems
# ============================================================================

SCREEN_WIDTH = 400
SCREEN_HEIGHT = 600
TRACK_WIDTH = 300

# Physics & Pack Tuning
DRAFTING_DIST = 120       # pixels behind another car to draft
DRAFTING_WIDTH = 25       # lateral distance to catch draft
DRAFTING_SPEED_BONUS = 1.5 # extra speed when drafting
DRAFTING_FUEL_SAVER = 0.5 # multiplier for fuel burn when drafting (50% savings)
COLLISION_BOUNCE = 2.0    # bounce speed when hitting side-to-side

# Consumption rates per frame at different throttle levels
# Format: throttle% -> (fuel_burn, heat_gain)
EFFICIENCY_CURVE = {
    100: (0.08, 0.12),    # burning hot, drinking fuel
    90:  (0.06, 0.08),
    80:  (0.04, 0.04),    # sustainable cruise
    70:  (0.03, 0.02),
    60:  (0.025, 0.0),    # heat neutral
    50:  (0.02, -0.02),   # cooling down
    40:  (0.015, -0.04),
    30:  (0.01, -0.06),
    20:  (0.008, -0.08),
    10:  (0.005, -0.10),
    0:   (0.0, -0.12),    # coasting, max cooling
}

# Heat penalties
HEAT_WARNING = 80.0       # above this, engine starts struggling
HEAT_CRITICAL = 95.0      # above this, forced throttle reduction
OVERHEAT_SPEED_PENALTY = 0.5  # multiplier when overheating

# Nitro
NITRO_CHARGES = 3
NITRO_DURATION = 45       # frames
NITRO_SPEED_BOOST = 4.0   # added to max speed during nitro
NITRO_FUEL_COST = 10.0    # flat fuel cost per use
NITRO_HEAT_SPIKE = 15.0   # instant heat gain

# AI tuning
AI_SPEED_VARIANCE = 1.0   # randomness in AI speed

# Colors
COLOR_TRACK = (60, 60, 60)
COLOR_TRACK_EDGE = (120, 120, 120)
COLOR_PLAYER = (80, 180, 80)
COLOR_PLAYER_HOT = (180, 80, 80)
COLOR_AI = (80, 80, 180)
COLOR_HUD_BG = (30, 30, 30)
COLOR_FUEL = (100, 200, 100)
COLOR_HEAT = (200, 100, 100)
COLOR_THROTTLE = (200, 200, 100)

# ============================================================================
# PROGRESSION & STATS
# ============================================================================

class CarStats:
    def __init__(self, name, max_speed, accel, fuel_cap, heat_cap, cooling_factor=1.0):
        self.name = name
        self.max_speed = max_speed
        self.acceleration = accel
        self.fuel_capacity = fuel_cap
        self.heat_capacity = heat_cap
        self.cooling_factor = cooling_factor # Multiplier for cooling rate

# Tier Definitions
TIER_1_STARTER = CarStats(
    name="Rusty Hatchback",
    max_speed=7.0,
    accel=0.12,
    fuel_cap=80.0,
    heat_cap=80.0,
    cooling_factor=0.9
)

TIER_2_STREET = CarStats(
    name="Street Tuner",
    max_speed=8.0,
    accel=0.15,
    fuel_cap=100.0,
    heat_cap=100.0,
    cooling_factor=1.0
)

TIER_3_PRO = CarStats(
    name="Track Spec",
    max_speed=9.5,
    accel=0.20,
    fuel_cap=120.0,
    heat_cap=120.0,
    cooling_factor=1.2
)

class RaceConfig:
    def __init__(self, length, num_ai, prize_money, checkpoints=None):
        self.length = length
        self.num_ai = num_ai
        self.prize_money = prize_money
        self.checkpoints = checkpoints if checkpoints else []

# Race Definitions
RACE_ROOKIE = RaceConfig(
    length=30000, 
    num_ai=15, 
    prize_money=500,
    checkpoints=[7500, 15000, 22500] # 4 legs of 7500
)
RACE_AMATEUR = RaceConfig(
    length=30000, 
    num_ai=5, 
    prize_money=1500,
    checkpoints=[10000, 20000] # Two stops
)
RACE_PRO = RaceConfig(
    length=50000, 
    num_ai=7, 
    prize_money=5000,
    checkpoints=[12500, 25000, 37500] # Three stops
)

# ============================================================================
# GAME CLASSES
# ============================================================================

class Car:
    def __init__(self, x, y, color, stats, race_length, is_player=False):
        self.x = x
        self.y = y  # world position (0 = start, race_length = finish)
        self.width = 20
        self.height = 35
        self.color = color
        self.stats = stats
        self.race_length = race_length
        self.is_player = is_player
        
        # Movement
        self.speed = 0.0
        self.lateral_speed = 0.0
        self.throttle = 100 if not is_player else 50  # AI floors it, player starts mid
        
        # Resources (player only really uses these)
        self.fuel = self.stats.fuel_capacity
        self.heat = 20.0  # start warm
        
        # Nitro
        self.nitro_charges = NITRO_CHARGES
        self.nitro_active = 0  # frames remaining
        
        # State
        self.finished = False
        self.finish_time = 0 # Frames to finish
        self.dead = False  # out of fuel or overheated
        self.is_drafting = False
        self.next_checkpoint_idx = 0 # Track which checkpoint we are aiming for
        
    def get_target_speed(self):
        """Calculate target speed based on throttle percentage."""
        base = self.stats.max_speed * (self.throttle / 100.0)
        
        # Heat penalty
        if self.heat >= HEAT_CRITICAL:
            base *= OVERHEAT_SPEED_PENALTY
        elif self.heat >= HEAT_WARNING:
            penalty_factor = (self.heat - HEAT_WARNING) / (HEAT_CRITICAL - HEAT_WARNING)
            base *= (1.0 - (penalty_factor * (1.0 - OVERHEAT_SPEED_PENALTY)))
        
        # Nitro boost
        if self.nitro_active > 0:
            base += NITRO_SPEED_BOOST
            
        # Drafting boost (slipstream)
        if self.is_drafting:
            base += DRAFTING_SPEED_BONUS
            
        return base
    
    def update_resources(self):
        """Burn fuel, generate/dissipate heat based on throttle."""
        if self.dead or self.finished:
            return
            
        # Interpolate consumption rates for current throttle
        t = self.throttle
        lower_key = int((t // 10) * 10)
        upper_key = min(100, lower_key + 10)
        
        if lower_key == upper_key:
             fuel_burn, heat_delta = EFFICIENCY_CURVE.get(lower_key, (0.04, 0.04))
        else:
            val_low = EFFICIENCY_CURVE.get(lower_key, (0.04, 0.04))
            val_high = EFFICIENCY_CURVE.get(upper_key, (0.04, 0.04))
            
            fraction = (t - lower_key) / 10.0
            
            fuel_burn = val_low[0] + (val_high[0] - val_low[0]) * fraction
            heat_delta = val_low[1] + (val_high[1] - val_low[1]) * fraction
        
        # Apply cooling factor if cooling down (negative heat delta)
        if heat_delta < 0:
            heat_delta *= self.stats.cooling_factor
        
        # Drafting saves fuel
        if self.is_drafting:
            fuel_burn *= DRAFTING_FUEL_SAVER
        
        # Nitro increases burn rate
        if self.nitro_active > 0:
            fuel_burn *= 2.0
            heat_delta = abs(heat_delta) + 0.1  # always heating during nitro
        
        # Apply
        self.fuel -= fuel_burn
        self.heat += heat_delta
        
        # Clamp
        self.heat = max(0.0, min(self.stats.heat_capacity, self.heat))
        
        # Check death conditions
        if self.fuel <= 0:
            self.fuel = 0
            self.dead = True
        if self.heat >= self.stats.heat_capacity:
            self.dead = True
            
    def update(self):
        """Update car physics."""
        # Calculate Drag Coefficient
        # Drag coefficient derived so that Max Power = Max Speed
        # Force = Drag * Speed  =>  Accel = (Accel/MaxSpeed) * MaxSpeed
        drag_coeff = self.stats.acceleration / self.stats.max_speed
        
        # Drafting reduces drag
        if self.is_drafting:
            drag_coeff *= 0.5 # 50% less drag
            
        drag_force = self.speed * drag_coeff
        
        # Calculate Engine Force
        engine_force = 0.0
        
        if not self.dead and not self.finished:
            # Normal driving
            power_factor = self.throttle / 100.0
            
            # Heat penalty reduces effective power
            if self.heat >= HEAT_CRITICAL:
                power_factor *= OVERHEAT_SPEED_PENALTY
            elif self.heat >= HEAT_WARNING:
                penalty_factor = (self.heat - HEAT_WARNING) / (HEAT_CRITICAL - HEAT_WARNING)
                power_factor *= (1.0 - (penalty_factor * (1.0 - OVERHEAT_SPEED_PENALTY)))
            
            engine_force = self.stats.acceleration * power_factor
            
            # Nitro adds raw force
            if self.nitro_active > 0:
                engine_force += self.stats.acceleration * 0.5 # 50% extra power
        
        # Net Acceleration
        accel = engine_force - drag_force
        
        # Apply
        self.speed += accel
        
        # Min speed clamp (friction stops you eventually)
        if self.speed < 0.05:
            self.speed = 0
        
        # Move forward
        self.y += self.speed
        
        # Lateral Physics
        self.x += self.lateral_speed
        self.lateral_speed *= 0.92 # Lateral friction/drag
        
        # Clamp to track bounds
        track_left = (SCREEN_WIDTH - TRACK_WIDTH) // 2
        track_right = track_left + TRACK_WIDTH
        
        if self.x < track_left + self.width // 2:
            self.x = track_left + self.width // 2
            self.lateral_speed = 0 # Hit wall
        elif self.x > track_right - self.width // 2:
            self.x = track_right - self.width // 2
            self.lateral_speed = 0
        
        # Update nitro timer
        if self.nitro_active > 0:
            self.nitro_active -= 1
            
        # Update resources
        if self.is_player:
            self.update_resources()
            
    def check_finish(self, current_time):
        """Check if car has crossed finish line."""
        if not self.finished and self.y >= self.race_length:
            self.finished = True
            self.finish_time = current_time
            return True
        return False
            
    def use_nitro(self):
        """Activate nitro if available."""
        if self.nitro_charges > 0 and self.nitro_active == 0 and not self.dead:
            self.nitro_charges -= 1
            self.nitro_active = NITRO_DURATION
            self.fuel -= NITRO_FUEL_COST
            self.heat += NITRO_HEAT_SPIKE
            return True
        return False
    
    def adjust_throttle(self, delta):
        """Adjust throttle by delta (typically +/-10)."""
        self.throttle = max(0, min(100, self.throttle + delta))
        
    def steer(self, direction):
        """Apply lateral force. Direction: -1 = left, 1 = right."""
        # Must be moving to steer effectively
        if self.speed < 0.1:
            return
            
        # High speed makes it harder to adjust trajectory (heavier feel)
        # Scale authority: 100% at low speed -> 40% at max speed
        speed_ratio = min(1.0, self.speed / self.stats.max_speed)
        steering_authority = 1.0 - (speed_ratio * 0.6)
        
        force = 0.4 * steering_authority
        self.lateral_speed += direction * force
    
    def get_rect(self):
        """Get collision rect in world coords."""
        return pygame.Rect(
            self.x - self.width // 2,
            self.y - self.height // 2,
            self.width,
            self.height
        )
    
    def draw(self, surface, camera_y):
        """Draw car relative to camera."""
        screen_y = SCREEN_HEIGHT - (self.y - camera_y) - self.height // 2
        screen_x = self.x - self.width // 2
        
        # Only draw if on screen
        if -self.height < screen_y < SCREEN_HEIGHT + self.height:
            # Color shift based on heat for player
            color = self.color
            if self.is_player and self.heat > HEAT_WARNING:
                heat_factor = (self.heat - HEAT_WARNING) / (self.stats.heat_capacity - HEAT_WARNING)
                color = (
                    int(self.color[0] + (COLOR_PLAYER_HOT[0] - self.color[0]) * heat_factor),
                    int(self.color[1] + (COLOR_PLAYER_HOT[1] - self.color[1]) * heat_factor),
                    int(self.color[2] + (COLOR_PLAYER_HOT[2] - self.color[2]) * heat_factor),
                )
            
            pygame.draw.rect(surface, color, (screen_x, screen_y, self.width, self.height))
            
            # Nitro indicator
            if self.nitro_active > 0:
                pygame.draw.rect(surface, (255, 200, 0), 
                               (screen_x - 2, screen_y + self.height - 5, self.width + 4, 5))
            
            # Drafting indicator
            if self.is_drafting:
                pygame.draw.circle(surface, (100, 255, 255), (screen_x + self.width//2, screen_y - 5), 3)


class AIDriver:
    """Simple AI behavior wrapper for a car."""
    def __init__(self, car):
        self.car = car
        self.target_speed_offset = random.uniform(-AI_SPEED_VARIANCE, AI_SPEED_VARIANCE)
        self.lane_preference = random.choice([-1, 0, 1])  # left, center, right tendency
        
    def update(self, track_center):
        """Update AI decision making."""
        if self.car.dead or self.car.finished:
            return
            
        # Simple AI: maintain speed with slight variance
        target_throttle = 85 + random.randint(-5, 10)  # AI runs 80-95% mostly
        
        if self.car.throttle < target_throttle:
            self.car.adjust_throttle(10)
        elif self.car.throttle > target_throttle:
            self.car.adjust_throttle(-10)
            
        # Drift toward lane preference
        target_x = track_center + (self.lane_preference * 60)
        if self.car.x < target_x - 10:
            self.car.steer(1)
        elif self.car.x > target_x + 10:
            self.car.steer(-1)


def handle_physics(cars):
    """Resolve collisions and drafting for all cars."""
    # Reset drafting state
    for car in cars:
        car.is_drafting = False
        
    # Check every pair
    for i, car_a in enumerate(cars):
        if car_a.dead or car_a.finished:
            continue
            
        rect_a = car_a.get_rect()
        
        for j, car_b in enumerate(cars):
            if i == j or car_b.dead or car_b.finished:
                continue
                
            rect_b = car_b.get_rect()
            
            # 1. Collision Resolution (Simple AABB push)
            if rect_a.colliderect(rect_b):
                # Determine relative position
                dx = car_a.x - car_b.x
                dy = car_a.y - car_b.y
                
                if abs(dx) > abs(dy):
                    # Side collision - bounce
                    push = COLLISION_BOUNCE
                    if dx > 0: # A is to the right
                        car_a.x += push
                        car_b.x -= push
                    else: # A is to the left
                        car_a.x -= push
                        car_b.x += push
                else:
                    # Rear-end collision
                    # The one behind (smaller y) slows down, one ahead speeds up slightly
                    if dy < 0: # A is behind B
                        car_a.speed *= 0.9
                        car_a.y = car_b.y - car_a.height - 1 # Force separate
                    else: # A is ahead of B
                        car_b.speed *= 0.9
                        car_b.y = car_a.y - car_b.height - 1
                        
            # 2. Drafting Check
            # Check if A is drafting B (A is behind B)
            # A.y < B.y because Y increases forward? 
            # Wait, in this code:
            # self.y += self.speed
            # 0 = start, TRACK_LENGTH = finish. So Y increases as you go forward.
            # So the car AHEAD has a LARGER Y.
            # So if A is drafting B, A.y < B.y
            
            dist = car_b.y - car_a.y
            if 0 < dist < DRAFTING_DIST:
                if abs(car_a.x - car_b.x) < DRAFTING_WIDTH:
                    car_a.is_drafting = True


# ============================================================================
# HUD DRAWING
# ============================================================================

def draw_hud(surface, player, split_text=None):
    """Draw resource bars and info."""
    hud_height = 80
    hud_rect = pygame.Rect(0, SCREEN_HEIGHT - hud_height, SCREEN_WIDTH, hud_height)
    pygame.draw.rect(surface, COLOR_HUD_BG, hud_rect)
    
    bar_width = 120
    bar_height = 15
    bar_x = 20
    
    # Fuel bar
    fuel_pct = player.fuel / player.stats.fuel_capacity
    pygame.draw.rect(surface, (40, 40, 40), (bar_x, SCREEN_HEIGHT - 70, bar_width, bar_height))
    pygame.draw.rect(surface, COLOR_FUEL, (bar_x, SCREEN_HEIGHT - 70, int(bar_width * fuel_pct), bar_height))
    
    # Heat bar
    heat_pct = player.heat / player.stats.heat_capacity
    heat_color = COLOR_HEAT if player.heat < HEAT_WARNING else (255, 50, 50)
    pygame.draw.rect(surface, (40, 40, 40), (bar_x, SCREEN_HEIGHT - 50, bar_width, bar_height))
    pygame.draw.rect(surface, heat_color, (bar_x, SCREEN_HEIGHT - 50, int(bar_width * heat_pct), bar_height))
    
    # Throttle indicator
    throttle_x = 160
    pygame.draw.rect(surface, (40, 40, 40), (throttle_x, SCREEN_HEIGHT - 70, 30, 35))
    throttle_height = int(35 * (player.throttle / 100))
    pygame.draw.rect(surface, COLOR_THROTTLE, 
                    (throttle_x, SCREEN_HEIGHT - 35 - throttle_height + 35, 30, throttle_height))
    
    # Draw throttle text value
    font = pygame.font.Font(None, 20)
    throt_text = font.render(f"{int(player.throttle)}%", True, (255, 255, 255))
    surface.blit(throt_text, (throttle_x, SCREEN_HEIGHT - 85))
    
    # Nitro charges
    nitro_x = 210
    for i in range(NITRO_CHARGES):
        color = (255, 200, 0) if i < player.nitro_charges else (60, 60, 60)
        pygame.draw.rect(surface, color, (nitro_x + i * 25, SCREEN_HEIGHT - 70, 20, 35))
    
    # Speed / position readout
    font = pygame.font.Font(None, 24)
    speed_text = font.render(f"SPD: {player.speed:.1f}", True, (200, 200, 200))
    pos_text = font.render(f"POS: {int(player.y)}/{player.race_length}", True, (200, 200, 200))
    tier_text = font.render(f"TIER: {player.stats.name}", True, (150, 150, 255))
    surface.blit(speed_text, (SCREEN_WIDTH - 100, SCREEN_HEIGHT - 70))
    surface.blit(pos_text, (SCREEN_WIDTH - 100, SCREEN_HEIGHT - 50))
    surface.blit(tier_text, (SCREEN_WIDTH - 150, SCREEN_HEIGHT - 30))
    
    # Split Time
    if split_text:
        split_surf = font.render(split_text, True, (255, 255, 0))
        surface.blit(split_surf, (SCREEN_WIDTH - 250, SCREEN_HEIGHT - 70))
    
    # Status
    if player.dead:
        status = font.render("ENGINE DEAD", True, (255, 50, 50))
        surface.blit(status, (SCREEN_WIDTH // 2 - 50, SCREEN_HEIGHT - 30))
    elif player.finished:
        status = font.render("FINISHED!", True, (50, 255, 50))
        surface.blit(status, (SCREEN_WIDTH // 2 - 40, SCREEN_HEIGHT - 30))


def draw_track(surface, camera_y, race_length, checkpoints):
    """Draw the track background."""
    surface.fill((40, 40, 40))
    
    track_left = (SCREEN_WIDTH - TRACK_WIDTH) // 2
    track_right = track_left + TRACK_WIDTH
    
    # Main track surface
    pygame.draw.rect(surface, COLOR_TRACK, (track_left, 0, TRACK_WIDTH, SCREEN_HEIGHT))
    
    # Edge lines
    pygame.draw.rect(surface, COLOR_TRACK_EDGE, (track_left, 0, 3, SCREEN_HEIGHT))
    pygame.draw.rect(surface, COLOR_TRACK_EDGE, (track_right - 3, 0, 3, SCREEN_HEIGHT))
    
    # Distance markers every 1000 units
    font = pygame.font.Font(None, 20)
    marker_spacing = 1000
    start_marker = (int(camera_y) // marker_spacing) * marker_spacing
    
    for marker_y in range(start_marker, start_marker + SCREEN_HEIGHT + marker_spacing, marker_spacing):
        screen_y = SCREEN_HEIGHT - (marker_y - camera_y)
        if 0 < screen_y < SCREEN_HEIGHT:
            pygame.draw.line(surface, COLOR_TRACK_EDGE, 
                           (track_left + 10, screen_y), (track_left + 40, screen_y), 2)
            text = font.render(str(marker_y), True, (100, 100, 100))
            surface.blit(text, (track_left + 45, screen_y - 8))
            
    # Checkpoints
    for cp_y in checkpoints:
        screen_y = SCREEN_HEIGHT - (cp_y - camera_y)
        if -50 < screen_y < SCREEN_HEIGHT + 50:
            # Blue line for checkpoint
            pygame.draw.line(surface, (0, 100, 255), 
                           (track_left, screen_y), (track_right, screen_y), 5)
            text = font.render("CHECKPOINT", True, (0, 200, 255))
            surface.blit(text, (track_left + 10, screen_y - 20))
            
    # Finish Line
    finish_screen_y = SCREEN_HEIGHT - (race_length - camera_y)
    if -50 < finish_screen_y < SCREEN_HEIGHT + 50:
        # Checkerboard
        check_size = 20
        rows = 3
        cols = TRACK_WIDTH // check_size
        for r in range(rows):
            for c in range(cols):
                color = (255, 255, 255) if (r + c) % 2 == 0 else (0, 0, 0)
                pygame.draw.rect(surface, color, 
                               (track_left + c * check_size, finish_screen_y - r * check_size, check_size, check_size))


def draw_minimap(surface, player, ai_cars, race_length):
    """Draw race position minimap on right edge."""
    map_width = 20
    map_height = 400
    map_x = SCREEN_WIDTH - map_width - 10
    map_y = 50
    
    # Background
    pygame.draw.rect(surface, (30, 30, 30), (map_x, map_y, map_width, map_height))
    pygame.draw.rect(surface, (60, 60, 60), (map_x, map_y, map_width, map_height), 1)
    
    # Finish line
    pygame.draw.line(surface, (255, 255, 255), (map_x, map_y + 5), (map_x + map_width, map_y + 5), 2)
    
    # All cars
    def y_to_map(world_y, track_len):
        pct = world_y / track_len
        return map_y + map_height - int(pct * map_height)
    
    # AI cars
    for ai in ai_cars:
        my = y_to_map(ai.car.y, race_length) 
        color = (60, 60, 150) if not ai.car.dead else (80, 80, 80)
        pygame.draw.rect(surface, color, (map_x + 4, my - 3, map_width - 8, 6))
    
    # Player (drawn last, on top)
    py = y_to_map(player.y, race_length)
    color = COLOR_PLAYER if not player.dead else (80, 80, 80)
    pygame.draw.rect(surface, color, (map_x + 2, py - 4, map_width - 4, 8))


# ============================================================================
# MAIN GAME LOOP
# ============================================================================

def main():
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("Racing Scaffold - Throttle/Fuel/Heat")
    clock = pygame.time.Clock()
    
    track_center = SCREEN_WIDTH // 2
    
    # Setup Race
    current_tier = TIER_1_STARTER
    current_race = RACE_ROOKIE
    
    # Update global track length for drawing (hacky, but works for prototype)
    global TRACK_LENGTH
    TRACK_LENGTH = current_race.length
    
    # Create player
    # Grid Start Logic
    # Rows of 2
    # Player starts in last position for challenge
    total_cars = current_race.num_ai + 1
    grid_spacing_y = 60
    grid_spacing_x = 60
    
    # Calculate grid positions
    grid_positions = []
    for i in range(total_cars):
        row = i // 2
        col = i % 2
        # Center the grid
        x_offset = -grid_spacing_x/2 if col == 0 else grid_spacing_x/2
        gx = track_center + x_offset
        gy = 200 + row * grid_spacing_y
        grid_positions.append((gx, gy))
    
    # Reverse grid so index 0 is front, index -1 is back
    # This ensures player (at -1) starts at the back
    grid_positions.reverse()
        
    # Assign player to last spot
    p_start = grid_positions[-1]
    player = Car(p_start[0], p_start[1], COLOR_PLAYER, current_tier, current_race.length, is_player=True)
    
    # Create AI opponent pack
    ai_cars = []
    for i in range(current_race.num_ai):
        pos = grid_positions[i]
        # AI uses same tier for now
        ai_cars.append(AIDriver(Car(pos[0], pos[1], COLOR_AI, current_tier, current_race.length)))
    
    running = True
    race_over = False
    race_time = 0
    
    # Game States
    STATE_COUNTDOWN = 0
    STATE_RACING = 1
    game_state = STATE_COUNTDOWN
    countdown_timer = 180 # 3 seconds at 60fps
    
    # Initial Rank
    player_rank = total_cars
    
    # Checkpoint popup state
    popup_timer = 0
    popup_text = ""
    
    while running:
        # Input
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    player.use_nitro()
                elif event.key == pygame.K_r:
                    # Reset race
                    # Re-calculate grid
                    grid_positions = []
                    for i in range(total_cars):
                        row = i // 2
                        col = i % 2
                        x_offset = -grid_spacing_x/2 if col == 0 else grid_spacing_x/2
                        gx = track_center + x_offset
                        gy = 200 + row * grid_spacing_y
                        grid_positions.append((gx, gy))
                        
                    p_start = grid_positions[-1]
                    player = Car(p_start[0], p_start[1], COLOR_PLAYER, current_tier, current_race.length, is_player=True)
                    ai_cars = []
                    for i in range(current_race.num_ai):
                        pos = grid_positions[i]
                        ai_cars.append(AIDriver(Car(pos[0], pos[1], COLOR_AI, current_tier, current_race.length)))
                    race_over = False
                    race_time = 0
                    popup_timer = 0
                    game_state = STATE_COUNTDOWN
                    countdown_timer = 180
                    
        # Continuous steering input
        keys = pygame.key.get_pressed()
        
        # Only steer if racing
        if game_state == STATE_RACING:
            if keys[pygame.K_LEFT]:
                player.steer(-1)
            if keys[pygame.K_RIGHT]:
                player.steer(1)
                
        # Throttle allowed always (for revving)
        if keys[pygame.K_UP]:
            player.adjust_throttle(1)
        if keys[pygame.K_DOWN]:
            player.adjust_throttle(-1)
            
        # Update
        all_cars = [player] + [ai.car for ai in ai_cars]

        if game_state == STATE_COUNTDOWN:
            countdown_timer -= 1
            if countdown_timer <= 0:
                game_state = STATE_RACING
            
            # Allow revving (resources update) but clamp speed
            player.update_resources()
            player.speed = 0
            
        elif game_state == STATE_RACING:
            race_time += 1
                
            player.update()
            
            # Checkpoint Logic
            if player.next_checkpoint_idx < len(current_race.checkpoints):
                cp_y = current_race.checkpoints[player.next_checkpoint_idx]
                if player.y >= cp_y:
                    # Crossed checkpoint!
                    player.next_checkpoint_idx += 1
                    
                    # Reward: +40 Fuel, -50 Heat
                    fuel_gain = 40.0
                    heat_loss = 50.0
                    
                    player.fuel = min(player.stats.fuel_capacity, player.fuel + fuel_gain)
                    player.heat = max(0.0, player.heat - heat_loss)
                    
                    popup_text = "CHECKPOINT! +FUEL -HEAT"
                    popup_timer = 120 # 2 seconds
            
            for ai in ai_cars:
                ai.update(track_center)
                ai.car.update()
                
            # Physics
            handle_physics(all_cars)
            
            # Update finish status
            for car in all_cars:
                car.check_finish(race_time)
            
            # Check race end (Player finished)
            if player.finished or player.dead:
                race_over = True
        
        # Rank Tracking & Sorting (Always update for HUD/Splits)
        # Sort by: 1. Finished (Time ascending), 2. Racing (Distance descending)
        all_cars.sort(key=lambda c: (0, c.finish_time) if c.finished else (1, -c.y))
        player_rank = all_cars.index(player) + 1

        # Camera follows player
        camera_y = player.y - SCREEN_HEIGHT // 3
                
        # Draw
        draw_track(screen, camera_y, current_race.length, current_race.checkpoints)
        
        # Draw AI cars
        for ai in ai_cars:
            ai.car.draw(screen, camera_y)
            
        # Draw player
        player.draw(screen, camera_y)
        
        # Draw minimap
        draw_minimap(screen, player, ai_cars, current_race.length)
        
        # Calculate Split
        split_text = ""
        if len(all_cars) > 1:
            leader = all_cars[0]
            if player == leader:
                # Gap to 2nd
                second = all_cars[1]
                dist = player.y - second.y
                if player.speed > 1:
                    gap_time = dist / player.speed / 60.0
                    split_text = f"GAP: +{gap_time:.2f}s"
                else:
                    split_text = f"GAP: +{int(dist)}m"
            else:
                # Gap to Leader
                dist = leader.y - player.y
                if player.speed > 1:
                    gap_time = dist / player.speed / 60.0
                    split_text = f"GAP: -{gap_time:.2f}s"
                else:
                    split_text = f"GAP: -{int(dist)}m"

        # Draw HUD
        draw_hud(screen, player, split_text)
        
        # Draw Rank & Time
        font = pygame.font.Font(None, 36)
        rank_color = (50, 255, 50) if player_rank == 1 else (200, 200, 200)
        rank_text = font.render(f"POS: {player_rank}/{total_cars}", True, rank_color)
        screen.blit(rank_text, (20, 20))
        
        time_secs = race_time / 60.0
        time_text = font.render(f"TIME: {time_secs:.2f}", True, (200, 200, 200))
        screen.blit(time_text, (SCREEN_WIDTH - 150, 20))
        
        # Draw Popup
        if popup_timer > 0:
            popup_timer -= 1
            p_font = pygame.font.Font(None, 48)
            p_surf = p_font.render(popup_text, True, (0, 255, 255))
            p_rect = p_surf.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2))
            # Draw background for popup
            bg_rect = p_rect.inflate(20, 10)
            pygame.draw.rect(screen, (0, 0, 0), bg_rect)
            pygame.draw.rect(screen, (0, 255, 255), bg_rect, 2)
            screen.blit(p_surf, p_rect)
            
        # Draw Countdown
        if game_state == STATE_COUNTDOWN:
            c_font = pygame.font.Font(None, 120)
            secs = (countdown_timer // 60) + 1
            c_text = c_font.render(str(secs), True, (255, 50, 50))
            if secs == 1:
                c_text = c_font.render("SET", True, (255, 200, 0))
            
            c_rect = c_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2))
            screen.blit(c_text, c_rect)
            
            hint_font = pygame.font.Font(None, 30)
            hint = hint_font.render("Hold Throttle to Rev!", True, (200, 200, 200))
            screen.blit(hint, (SCREEN_WIDTH // 2 - 100, SCREEN_HEIGHT // 2 + 60))
        
        # Race end message
        if race_over:
            font = pygame.font.Font(None, 48)
            if player.finished:
                finish_seconds = player.finish_time / 60.0
                msg = f"FINISHED! Rank: {player_rank} Time: {finish_seconds:.2f}s"
                color = (50, 255, 50)
            else:
                msg = "DNF"
                color = (255, 50, 50)
            text = font.render(msg, True, color)
            text_rect = text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 3))
            pygame.draw.rect(screen, (0, 0, 0), text_rect.inflate(20, 10))
            screen.blit(text, text_rect)
            
            hint = pygame.font.Font(None, 24).render("Press R to restart", True, (150, 150, 150))
            screen.blit(hint, (SCREEN_WIDTH // 2 - 60, SCREEN_HEIGHT // 3 + 30))
        
        pygame.display.flip()
        clock.tick(60)
        
    pygame.quit()


if __name__ == "__main__":
    main()
