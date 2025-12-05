"""
Racing Scaffold - Throttle/Fuel/Heat Prototype
Arrow keys: Left/Right to steer, Up/Down to adjust throttle (Hold for fine control)
Space: Nitro burst
"""

import pygame
import random

# ============================================================================
# VERSION INFO
# ============================================================================
VERSION = "0.2.0"

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
COLLISION_DAMAGE_BASE = 2.0
COLLISION_DAMAGE_FACTOR = 0.5

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
    def __init__(self, name, max_speed, accel, fuel_cap, heat_cap, cooling_factor=1.0, durability=100.0):
        self.name = name
        self.max_speed = max_speed
        self.acceleration = accel
        self.fuel_capacity = fuel_cap
        self.heat_capacity = heat_cap
        self.cooling_factor = cooling_factor # Multiplier for cooling rate
        self.durability = durability

# Tier Definitions
TIER_1_STARTER = CarStats(
    name="Rusty Hatchback",
    max_speed=7.0,
    accel=0.12,
    fuel_cap=80.0,
    heat_cap=80.0,
    cooling_factor=0.9,
    durability=80.0
)

TIER_2_STREET = CarStats(
    name="Street Tuner",
    max_speed=8.0,
    accel=0.15,
    fuel_cap=100.0,
    heat_cap=100.0,
    cooling_factor=1.0,
    durability=100.0
)

TIER_3_PRO = CarStats(
    name="Track Spec",
    max_speed=9.5,
    accel=0.20,
    fuel_cap=120.0,
    heat_cap=120.0,
    cooling_factor=1.2,
    durability=120.0
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
    def __init__(self, x, y, color, stats, race_length, is_player=False, profile=None):
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
        
        if is_player and profile:
            # Load from profile
            self.health = profile.health
            self.comp_front = profile.comp_front
            self.comp_rear = profile.comp_rear
            self.comp_fl = profile.comp_fl
            self.comp_fr = profile.comp_fr
            self.comp_rl = profile.comp_rl
            self.comp_rr = profile.comp_rr
        else:
            # Fresh car (AI or new)
            self.health = self.stats.durability
            self.comp_front = 1.0
            self.comp_rear = 1.0
            self.comp_fl = 1.0
            self.comp_fr = 1.0
            self.comp_rl = 1.0
            self.comp_rr = 1.0
        
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
        
        # Engine Damage Penalty (Front)
        if self.comp_front < 1.0:
            # Linear penalty up to 50% speed loss
            base *= (0.5 + 0.5 * self.comp_front)
        
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
    
    def apply_damage(self, amount, sector):
        """Apply damage to specific sector and overall health."""
        self.health -= amount
        
        # Component damage (scaled relative to durability)
        # If durability is 100, 20 damage = 0.2 component loss
        comp_loss = amount / self.stats.durability
        
        if sector == "FRONT":
            self.comp_front = max(0.0, self.comp_front - comp_loss)
        elif sector == "REAR":
            self.comp_rear = max(0.0, self.comp_rear - comp_loss)
        elif sector == "FL":
            self.comp_fl = max(0.0, self.comp_fl - comp_loss)
        elif sector == "FR":
            self.comp_fr = max(0.0, self.comp_fr - comp_loss)
        elif sector == "RL":
            self.comp_rl = max(0.0, self.comp_rl - comp_loss)
        elif sector == "RR":
            self.comp_rr = max(0.0, self.comp_rr - comp_loss)
            
    def update_resources(self):
        """Burn fuel, generate/dissipate heat based on throttle."""
        if self.dead or self.finished:
            return
            
        # Check Health
        if self.health <= 0:
            self.dead = True
            self.health = 0
            
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
        
        # Fuel Leak (Rear Damage)
        if self.comp_rear < 0.8:
            # Leak increases as damage gets worse
            leak_rate = (0.8 - self.comp_rear) * 0.1
            fuel_burn += leak_rate
        
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
            # Out of fuel is NOT instant death, just engine cut
            # self.dead = True 
            
        if self.heat >= self.stats.heat_capacity:
            self.dead = True # Overheat kills engine permanently
            
    def steer(self, direction):
        """Apply lateral force."""
        if self.dead or self.finished:
            return
            
        # Steering Authority
        # Reduced at high speeds (stability)
        # Reduced at very low speeds (need movement to turn)
        
        speed_factor = 1.0
        if self.speed > 8.0:
            speed_factor = 1.0 - ((self.speed - 8.0) * 0.15) # Reduce at high speed
        elif self.speed < 2.0:
            speed_factor = self.speed / 2.0 # Reduce at low speed
            
        # Tire Damage Penalty
        # Average of front tires affects turn-in
        tire_health = (self.comp_fl + self.comp_fr) / 2.0
        speed_factor *= (0.3 + 0.7 * tire_health)
            
        force = direction * 0.4 * max(0.1, speed_factor)
        self.lateral_speed += force
        
    def update(self):
        """Physics update per frame."""
        # 1. Longitudinal Physics
        target = self.get_target_speed()
        
        # If out of fuel or dead, target speed is 0 (coasting)
        if self.fuel <= 0 or self.dead:
            target = 0
        
        # Acceleration / Deceleration
        if self.speed < target:
            # Can only accelerate if engine is running
            if not self.dead and self.fuel > 0:
                self.speed += self.stats.acceleration
            else:
                # Coasting friction (no engine power)
                self.speed -= 0.05
        elif self.speed > target:
            # Coasting friction
            self.speed -= 0.05
            
        # 2. Lateral Physics (Inertia)
        self.x += self.lateral_speed
        
        # Tire Grip / Drag (Lateral friction)
        # Rear tires affect stability/grip
        rear_grip = (self.comp_rl + self.comp_rr) / 2.0
        friction = 0.90 * (0.8 + 0.2 * rear_grip)
        
        self.lateral_speed *= friction 
        
        # Track Limits (Bounce)
        track_left = (SCREEN_WIDTH - TRACK_WIDTH) // 2
        track_right = track_left + TRACK_WIDTH
        
        if self.x < track_left:
            self.x = track_left
            self.lateral_speed *= -0.5
        elif self.x + self.width > track_right:
            self.x = track_right - self.width
            self.lateral_speed *= -0.5
            
        # Move forward
        self.y += self.speed
        
        # Clamp position to track
        if self.x < 0:
            self.x = 0
            self.lateral_speed = -self.lateral_speed * 0.5
        elif self.x > SCREEN_WIDTH:
            self.x = SCREEN_WIDTH
            self.lateral_speed = -self.lateral_speed * 0.5
            
        # Move forward
        self.y -= self.speed
        
        # Update resources
        self.update_resources()
        
        # Smoke Effects
        if self.health < self.stats.durability * 0.5:
            # Damaged smoke
            if random.random() < 0.3:
                particles.add(self.x + random.randint(-10, 10), self.y + 10, 
                              random.uniform(-1, 1), random.uniform(1, 3), 
                              random.randint(30, 60), (100, 100, 100), random.randint(5, 10))
        
        if self.health < self.stats.durability * 0.2:
             # Heavy smoke / Fire
             if random.random() < 0.5:
                particles.add(self.x + random.randint(-10, 10), self.y + 10, 
                              random.uniform(-1, 1), random.uniform(1, 3), 
                              random.randint(30, 60), (50, 50, 50), random.randint(8, 15))
        
        # If wrecked (0 health), force stop faster
        if self.health <= 0:
            self.speed *= 0.9 # Rapid deceleration
            if self.speed < 0.1:
                self.speed = 0
            
        # Nitro timer
        if self.nitro_active > 0:
            self.nitro_active -= 1
            
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
                
            # Damage Visuals (Smoke/Fire)
            if self.health < self.stats.durability * 0.5:
                # Smoke
                smoke_color = (100, 100, 100)
                if self.health <= 0:
                    smoke_color = (50, 50, 50) # Dark smoke for dead
                    
                # Random puff
                if random.random() < 0.3:
                    sx = screen_x + random.randint(0, self.width)
                    sy = screen_y + random.randint(0, self.height)
                    pygame.draw.circle(surface, smoke_color, (sx, sy), random.randint(2, 6))
                    
            if self.health <= 0:
                # Fire if wrecked
                if random.random() < 0.2:
                    fx = screen_x + random.randint(0, self.width)
                    fy = screen_y + random.randint(0, self.height)
                    pygame.draw.circle(surface, (255, 100, 0), (fx, fy), random.randint(3, 8))
                    pygame.draw.circle(surface, (255, 255, 0), (fx, fy), random.randint(1, 4))


class AIDriver:
    """Simple AI behavior wrapper for a car."""
    def __init__(self, car):
        self.car = car
        self.target_speed_offset = random.uniform(-AI_SPEED_VARIANCE, AI_SPEED_VARIANCE)
        self.lane_preference = random.choice([-1, 0, 1])  # left, center, right tendency
        
    def update(self, track_center, obstacles, other_cars):
        """Update AI decision making."""
        if self.car.dead or self.car.finished:
            return
            
        # Simple AI: maintain speed with slight variance
        target_throttle = 85 + random.randint(-5, 10)  # AI runs 80-95% mostly
        
        if self.car.throttle < target_throttle:
            self.car.adjust_throttle(10)
        elif self.car.throttle > target_throttle:
            self.car.adjust_throttle(-10)
            
        # Steering Logic
        steer_dir = 0
        avoiding = False
        
        # 1. Obstacle Avoidance (High Priority)
        look_ahead = 400 # Increased lookahead
        
        # Combine obstacles and dead cars for avoidance
        all_hazards = list(obstacles)
        for other in other_cars:
            if other != self.car and other.dead:
                all_hazards.append(other)
        
        for obs in all_hazards:
            # Only care if it's ahead of us
            if obs.y > self.car.y and obs.y < self.car.y + look_ahead:
                # Check lateral overlap with INCREASED margin
                # Use a wider safety net (1.5x width)
                safe_dist = (self.car.width + obs.width) * 0.8
                if abs(obs.x - self.car.x) < safe_dist: 
                    avoiding = True
                    # Steer away from center of obstacle
                    # Stronger steering response
                    if self.car.x < obs.x + obs.width/2:
                        steer_dir = -1 # Go left
                    else:
                        steer_dir = 1 # Go right
                    break
        
        # 2. Car Avoidance (Medium Priority)
        if not avoiding:
            for other in other_cars:
                if other == self.car or other.dead or other.finished:
                    continue
                # Only avoid if they are slower or we are drafting too close
                if other.y > self.car.y and other.y < self.car.y + look_ahead:
                     if abs(other.x - self.car.x) < self.car.width + 15: # Increased margin
                         # Car ahead!
                         avoiding = True
                         if self.car.x < other.x + other.width/2:
                             steer_dir = -1
                         else:
                             steer_dir = 1
                         break

        # 3. Lane Preference (Low Priority)
        if not avoiding:
            target_x = track_center + (self.lane_preference * 60)
            if self.car.x < target_x - 10:
                steer_dir = 1
            elif self.car.x > target_x + 10:
                steer_dir = -1
                
        # Apply steer
        if steer_dir != 0:
            self.car.steer(steer_dir)


class Obstacle:
    def __init__(self, x, y, type="rock"):
        self.x = x
        self.y = y
        self.type = type
        self.width = 30
        self.height = 30
        self.color = (100, 50, 0) # Brown rock
        self.damage = 20.0
        
        if type == "barrier":
            self.width = 40
            self.height = 20
            self.color = (200, 200, 200)
            self.damage = 40.0
            
    def get_rect(self):
        return pygame.Rect(self.x, self.y, self.width, self.height)
        
    def draw(self, surface, camera_y):
        screen_y = SCREEN_HEIGHT - (self.y - camera_y)
        if -50 < screen_y < SCREEN_HEIGHT + 50:
            pygame.draw.rect(surface, self.color, (self.x, screen_y, self.width, self.height))
            # Simple detail
            pygame.draw.rect(surface, (0,0,0), (self.x, screen_y, self.width, self.height), 1)


def handle_physics(cars, obstacles=None):
    """Resolve collisions and drafting for all cars."""
    if obstacles is None:
        obstacles = []
        
    # Reset drafting state
    for car in cars:
        car.is_drafting = False
        
    # Check every pair
    for i, car_a in enumerate(cars):
        if car_a.finished:
            continue
            
        rect_a = car_a.get_rect()
        
        # Check Obstacles
        for obs in obstacles:
            if rect_a.colliderect(obs.get_rect()):
                # Hit obstacle
                # Determine if head-on
                # If car is moving forward and hits obstacle with front
                # A.y < Obs.y (A is behind Obs)
                # Overlap in X is significant
                
                is_head_on = False
                if car_a.y < obs.y:
                    x_overlap = min(car_a.x + car_a.width, obs.x + obs.width) - max(car_a.x, obs.x)
                    if x_overlap > car_a.width * 0.8:
                        is_head_on = True
                
                if is_head_on:
                    car_a.health = 0
                    car_a.dead = True
                    car_a.speed = 0
                    particles.add_explosion(car_a.x + car_a.width/2, car_a.y + car_a.height, 20, (255, 50, 0))
                else:
                    # Glancing blow
                    # Ensure minimum damage even at low speed to prevent infinite stuck loops
                    dmg_amount = max(1.0, obs.damage) 
                    car_a.apply_damage(dmg_amount, "FRONT") 
                    car_a.speed *= 0.5
                    particles.add_explosion(car_a.x + car_a.width/2, car_a.y + car_a.height/2, 5, (200, 200, 200))
                    
                    # Bounce back slightly
                    if car_a.y < obs.y: 
                        car_a.y = obs.y - car_a.height - 5 # Increased bounce back distance
                
        for j, car_b in enumerate(cars):
            if i == j or car_b.finished:
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
                    particles.add_explosion(car_a.x + (0 if dx > 0 else car_a.width), car_a.y + car_a.height/2, 5, (255, 200, 0))
                    if dx > 0: # A is to the right
                        car_a.x += push
                        car_b.x -= push
                        # A hit Left side, B hit Right side
                        car_a.apply_damage(5.0, "FL" if car_a.y > car_b.y else "RL") # Rough approx
                        car_b.apply_damage(5.0, "FR" if car_b.y > car_a.y else "RR")
                    else: # A is to the left
                        car_a.x -= push
                        car_b.x += push
                        car_a.apply_damage(5.0, "FR" if car_a.y > car_b.y else "RR")
                        car_b.apply_damage(5.0, "FL" if car_b.y > car_a.y else "RL")
                        
                else:
                    # Rear-end collision
                    particles.add_explosion(car_a.x + car_a.width/2, car_a.y + (car_a.height if dy < 0 else 0), 8, (255, 100, 0))
                    if dy < 0: # A is behind B
                        car_a.speed *= 0.9
                        car_a.y = car_b.y - car_a.height - 1 # Force separate
                        
                        # A hits with Front, B hits with Rear
                        impact = abs(car_a.speed - car_b.speed) * 2.0
                        car_a.apply_damage(impact, "FRONT")
                        car_b.apply_damage(impact, "REAR")
                        
                    else: # A is ahead of B
                        car_b.speed *= 0.9
                        car_b.y = car_a.y - car_b.height - 1
                        
                        # B hits with Front, A hits with Rear
                        impact = abs(car_a.speed - car_b.speed) * 2.0
                        car_b.apply_damage(impact, "FRONT")
                        car_a.apply_damage(impact, "REAR")
                        
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
# PARTICLES & VISUALS
# ============================================================================

class Particle:
    def __init__(self, x, y, vx, vy, life, color, size, decay=0.95):
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.life = life
        self.max_life = life
        self.color = color
        self.size = size
        self.decay = decay

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.vx *= self.decay
        self.vy *= self.decay
        self.life -= 1

    def draw(self, screen, camera_y):
        if self.life > 0:
            # Simple size fade
            s = max(1, int(self.size * (self.life / self.max_life)))
            # Fix coordinate system: y increases upwards in world, so screen_y is inverted
            screen_y = SCREEN_HEIGHT - (self.y - camera_y)
            pygame.draw.circle(screen, self.color, (int(self.x), int(screen_y)), s)

class ParticleSystem:
    def __init__(self):
        self.particles = []

    def add(self, x, y, vx, vy, life, color, size):
        self.particles.append(Particle(x, y, vx, vy, life, color, size))
        
    def add_explosion(self, x, y, count=10, color=(255, 100, 0)):
        for _ in range(count):
            vx = random.uniform(-3, 3)
            vy = random.uniform(-3, 3)
            life = random.randint(20, 40)
            size = random.randint(2, 5)
            self.add(x, y, vx, vy, life, color, size)

    def update(self):
        self.particles = [p for p in self.particles if p.life > 0]
        for p in self.particles:
            p.update()

    def draw(self, screen, camera_y):
        for p in self.particles:
            p.draw(screen, camera_y)

# Global particle system for simplicity in this script
particles = ParticleSystem()

# ============================================================================
# HUD DRAWING
# ============================================================================

def draw_hud(surface, player, split_text=None):
    """Draw resource bars and info."""
    hud_height = 100 # Increased height for 3 bars
    hud_rect = pygame.Rect(0, SCREEN_HEIGHT - hud_height, SCREEN_WIDTH, hud_height)
    pygame.draw.rect(surface, COLOR_HUD_BG, hud_rect)
    
    bar_width = 120
    bar_height = 12
    bar_x = 20
    
    # Health bar
    health_pct = max(0.0, player.health / player.stats.durability)
    pygame.draw.rect(surface, (40, 40, 40), (bar_x, SCREEN_HEIGHT - 85, bar_width, bar_height))
    pygame.draw.rect(surface, (50, 255, 50), (bar_x, SCREEN_HEIGHT - 85, int(bar_width * health_pct), bar_height))
    
    # Draw Car Diagram (Damage Status)
    diag_x = 300
    diag_y = SCREEN_HEIGHT - 85
    diag_w = 30
    diag_h = 50
    
    # Helper to get color from health (1.0=Green, 0.0=Red)
    def get_dmg_color(val):
        r = min(255, int(255 * (1.0 - val) * 2))
        g = min(255, int(255 * val * 2))
        return (r, g, 0)
        
    # Front (Engine)
    pygame.draw.rect(surface, get_dmg_color(player.comp_front), (diag_x + 5, diag_y, 20, 15))
    # Rear (Fuel)
    pygame.draw.rect(surface, get_dmg_color(player.comp_rear), (diag_x + 5, diag_y + 35, 20, 15))
    # FL Tire
    pygame.draw.rect(surface, get_dmg_color(player.comp_fl), (diag_x, diag_y + 10, 5, 10))
    # FR Tire
    pygame.draw.rect(surface, get_dmg_color(player.comp_fr), (diag_x + 25, diag_y + 10, 5, 10))
    # RL Tire
    pygame.draw.rect(surface, get_dmg_color(player.comp_rl), (diag_x, diag_y + 30, 5, 10))
    # RR Tire
    pygame.draw.rect(surface, get_dmg_color(player.comp_rr), (diag_x + 25, diag_y + 30, 5, 10))
    # Body Outline
    pygame.draw.rect(surface, (200, 200, 200), (diag_x + 5, diag_y + 15, 20, 20), 1)
    
    # Fuel bar
    fuel_pct = player.fuel / player.stats.fuel_capacity
    pygame.draw.rect(surface, (40, 40, 40), (bar_x, SCREEN_HEIGHT - 65, bar_width, bar_height))
    pygame.draw.rect(surface, COLOR_FUEL, (bar_x, SCREEN_HEIGHT - 65, int(bar_width * fuel_pct), bar_height))
    
    # Heat bar
    heat_pct = player.heat / player.stats.heat_capacity
    heat_color = COLOR_HEAT if player.heat < HEAT_WARNING else (255, 50, 50)
    pygame.draw.rect(surface, (40, 40, 40), (bar_x, SCREEN_HEIGHT - 45, bar_width, bar_height))
    pygame.draw.rect(surface, heat_color, (bar_x, SCREEN_HEIGHT - 45, int(bar_width * heat_pct), bar_height))
    
    # Throttle indicator
    throttle_x = 160
    pygame.draw.rect(surface, (40, 40, 40), (throttle_x, SCREEN_HEIGHT - 85, 30, 52))
    throttle_height = int(52 * (player.throttle / 100))
    pygame.draw.rect(surface, COLOR_THROTTLE, 
                    (throttle_x, SCREEN_HEIGHT - 33 - throttle_height + 33, 30, throttle_height))
    
    # Draw throttle text value
    font = pygame.font.Font(None, 20)
    throt_text = font.render(f"{int(player.throttle)}%", True, (255, 255, 255))
    surface.blit(throt_text, (throttle_x, SCREEN_HEIGHT - 98))
    
    # Nitro charges
    nitro_x = 210
    for i in range(NITRO_CHARGES):
        color = (255, 200, 0) if i < player.nitro_charges else (60, 60, 60)
        pygame.draw.rect(surface, color, (nitro_x + i * 25, SCREEN_HEIGHT - 85, 20, 52))
    
    # Speed / position readout
    font = pygame.font.Font(None, 24)
    speed_text = font.render(f"SPD: {player.speed:.1f}", True, (200, 200, 200))
    pos_text = font.render(f"POS: {int(player.y)}/{player.race_length}", True, (200, 200, 200))
    tier_text = font.render(f"TIER: {player.stats.name}", True, (150, 150, 255))
    surface.blit(speed_text, (SCREEN_WIDTH - 100, SCREEN_HEIGHT - 85))
    surface.blit(pos_text, (SCREEN_WIDTH - 100, SCREEN_HEIGHT - 65))
    surface.blit(tier_text, (SCREEN_WIDTH - 150, SCREEN_HEIGHT - 45))
    
    # Split Time
    if split_text:
        split_surf = font.render(split_text, True, (255, 255, 0))
        surface.blit(split_surf, (SCREEN_WIDTH - 250, SCREEN_HEIGHT - 85))
    
    # Status
    if player.dead:
        if player.health <= 0:
            status = font.render("WRECKED!", True, (255, 50, 50))
        else:
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
# GAME STATE & PERSISTENCE
# ============================================================================

class PlayerProfile:
    def __init__(self):
        self.money = 1000
        self.current_tier = TIER_1_STARTER
        
        # Persistent Car State
        self.health = self.current_tier.durability
        self.comp_front = 1.0
        self.comp_rear = 1.0
        self.comp_fl = 1.0
        self.comp_fr = 1.0
        self.comp_rl = 1.0
        self.comp_rr = 1.0
        
        self.engine_level = 0
        
    def get_modified_stats(self):
        import copy
        new_stats = copy.copy(self.current_tier)
        new_stats.max_speed += self.engine_level * 0.5
        new_stats.acceleration += self.engine_level * 0.02
        return new_stats
        
    def upgrade_engine_cost(self):
        return (self.engine_level + 1) * 500
        
    def upgrade_engine(self):
        cost = self.upgrade_engine_cost()
        if self.money >= cost:
            self.money -= cost
            self.engine_level += 1
        
    def get_repair_cost(self):
        # Calculate cost based on damage
        total_damage = 0.0
        total_damage += (1.0 - self.comp_front)
        total_damage += (1.0 - self.comp_rear)
        total_damage += (1.0 - self.comp_fl)
        total_damage += (1.0 - self.comp_fr)
        total_damage += (1.0 - self.comp_rl)
        total_damage += (1.0 - self.comp_rr)
        
        # Health damage
        health_pct = self.health / self.current_tier.durability
        total_damage += (1.0 - health_pct) * 2.0 # Health is expensive
        
        return int(total_damage * 100)

    def repair_all(self):
        """Repair everything if affordable."""
        cost = self.get_repair_cost()
        if self.money >= cost:
            self.money -= cost
            self.health = self.current_tier.durability
            self.comp_front = 1.0
            self.comp_rear = 1.0
            self.comp_fl = 1.0
            self.comp_fr = 1.0
            self.comp_rl = 1.0
            self.comp_rr = 1.0
            return True
        return False
        
    def get_repair_cost(self):
        """Calculate total repair cost."""
        total_loss = 0.0
        # Base health
        total_loss += (1.0 - (self.health / self.current_tier.durability)) * 100
        # Components
        total_loss += (1.0 - self.comp_front) * 50
        total_loss += (1.0 - self.comp_rear) * 50
        total_loss += (1.0 - self.comp_fl) * 25
        total_loss += (1.0 - self.comp_fr) * 25
        total_loss += (1.0 - self.comp_rl) * 25
        total_loss += (1.0 - self.comp_rr) * 25
        
        return int(total_loss * 2.0) # Multiplier


# ============================================================================
# SCENES
# ============================================================================

def run_garage(screen, clock, profile):
    """Garage scene loop."""
    running = True
    font_title = pygame.font.Font(None, 64)
    font_main = pygame.font.Font(None, 36)
    font_small = pygame.font.Font(None, 24)
    
    while running:
        screen.fill((20, 20, 30))
        
        # Title
        title = font_title.render("GARAGE", True, (200, 200, 200))
        screen.blit(title, (20, 20))
        
        # Money
        money_text = font_main.render(f"FUNDS: ${profile.money}", True, (100, 255, 100))
        screen.blit(money_text, (SCREEN_WIDTH - 200, 30))
        
        # Car Status
        status_y = 100
        pygame.draw.rect(screen, (40, 40, 50), (20, status_y, SCREEN_WIDTH - 40, 200))
        
        # Health Bar
        hp_pct = max(0.0, profile.health / profile.current_tier.durability)
        pygame.draw.rect(screen, (100, 0, 0), (40, status_y + 20, 300, 20))
        pygame.draw.rect(screen, (0, 200, 0), (40, status_y + 20, int(300 * hp_pct), 20))
        screen.blit(font_small.render(f"Health: {int(profile.health)}/{int(profile.current_tier.durability)}", True, (255,255,255)), (40, status_y + 45))
        
        # Component Status
        def draw_comp_stat(name, val, x, y):
            col = (0, 255, 0) if val > 0.8 else (255, 255, 0) if val > 0.4 else (255, 0, 0)
            txt = font_small.render(f"{name}: {int(val*100)}%", True, col)
            screen.blit(txt, (x, y))
            
        draw_comp_stat("ENGINE", profile.comp_front, 40, status_y + 80)
        draw_comp_stat("FUEL TANK", profile.comp_rear, 200, status_y + 80)
        draw_comp_stat("TIRES (F)", (profile.comp_fl + profile.comp_fr)/2, 40, status_y + 110)
        draw_comp_stat("TIRES (R)", (profile.comp_rl + profile.comp_rr)/2, 200, status_y + 110)
        
        # Repair Button
        repair_cost = profile.get_repair_cost()
        repair_col = (0, 150, 0) if profile.money >= repair_cost and repair_cost > 0 else (100, 100, 100)
        pygame.draw.rect(screen, repair_col, (40, status_y + 150, 150, 40))
        screen.blit(font_main.render(f"REPAIR (${repair_cost})", True, (255,255,255)), (50, status_y + 158))
        
        # Upgrade Button
        upg_cost = profile.upgrade_engine_cost()
        upg_col = (0, 100, 200) if profile.money >= upg_cost else (100, 100, 100)
        pygame.draw.rect(screen, upg_col, (220, status_y + 150, 160, 40))
        screen.blit(font_main.render(f"ENGINE +1 (${upg_cost})", True, (255,255,255)), (230, status_y + 158))
        screen.blit(font_small.render(f"Lvl: {profile.engine_level}", True, (200, 200, 255)), (230, status_y + 195))
        
        # Race Button
        pygame.draw.rect(screen, (200, 100, 0), (SCREEN_WIDTH - 140, SCREEN_HEIGHT - 80, 120, 60))
        screen.blit(font_main.render("RACE", True, (255,255,255)), (SCREEN_WIDTH - 110, SCREEN_HEIGHT - 65))
        
        # Input
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return "QUIT"
            if event.type == pygame.MOUSEBUTTONDOWN:
                mx, my = pygame.mouse.get_pos()
                
                # Repair Click
                if 40 <= mx <= 190 and status_y + 150 <= my <= status_y + 190:
                    if repair_cost > 0:
                        profile.repair_all()
                        
                # Upgrade Click
                if 220 <= mx <= 380 and status_y + 150 <= my <= status_y + 190:
                    profile.upgrade_engine()
                        
                # Race Click
                if SCREEN_WIDTH - 140 <= mx <= SCREEN_WIDTH - 20 and SCREEN_HEIGHT - 80 <= my <= SCREEN_HEIGHT - 20:
                    return "RACE"
                    
        pygame.display.flip()
        clock.tick(60)

def run_race(screen, clock, profile):
    """Main race loop."""
    track_center = SCREEN_WIDTH // 2
    
    # Setup Race
    current_tier = profile.current_tier
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
    # Use modified stats from profile (upgrades)
    player_stats = profile.get_modified_stats()
    player = Car(p_start[0], p_start[1], COLOR_PLAYER, player_stats, current_race.length, is_player=True, profile=profile)
    
    # Create AI opponent pack
    ai_cars = []
    for i in range(current_race.num_ai):
        pos = grid_positions[i]
        # AI uses same tier for now
        ai_cars.append(AIDriver(Car(pos[0], pos[1], COLOR_AI, current_tier, current_race.length)))
    
    # Generate Obstacles
    obstacles = []
    track_left = (SCREEN_WIDTH - TRACK_WIDTH) // 2
    track_right = track_left + TRACK_WIDTH
    
    # Start placing after the grid (e.g. 2000) up to finish
    for _ in range(30): # 30 obstacles
        oy = random.randint(2000, current_race.length - 1000)
        ox = random.randint(track_left + 20, track_right - 50)
        otype = random.choice(["rock", "barrier"])
        obstacles.append(Obstacle(ox, oy, otype))
        
    # Reset Particles
    particles.particles = []
        
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
                return "QUIT"
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    player.use_nitro()
                elif event.key == pygame.K_r and race_over:
                    # Return to garage
                    # Save damage state back to profile
                    profile.health = player.health
                    profile.comp_front = player.comp_front
                    profile.comp_rear = player.comp_rear
                    profile.comp_fl = player.comp_fl
                    profile.comp_fr = player.comp_fr
                    profile.comp_rl = player.comp_rl
                    profile.comp_rr = player.comp_rr
                    
                    # Award Money (Simple logic for now)
                    if player.finished:
                        # Prize based on rank
                        # 1st: 100%, 2nd: 70%, 3rd: 50%, etc.
                        rank_factor = max(0, 1.0 - (player_rank - 1) * 0.1)
                        winnings = int(current_race.prize_money * rank_factor)
                        profile.money += winnings
                    
                    return "GARAGE"
                    
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
                    
                    # If we were coasting on empty, we are back in the game!
                    # But NOT if we are wrecked (health <= 0) or overheated (dead=True)
                    if not player.dead and player.health > 0:
                         pass # Fuel added above is enough to keep going
                    
                    popup_text = "CHECKPOINT! +FUEL -HEAT"
                    popup_timer = 120 # 2 seconds
            
            for ai in ai_cars:
                ai.update(track_center, obstacles, all_cars)
                ai.car.update()
                
            # Physics
            handle_physics(all_cars, obstacles)
            
            # Particles
            particles.update()
            
            # Update finish status
            for car in all_cars:
                car.check_finish(race_time)
            
            # Check race end (Player finished)
            # Only end if player finished or is WRECKED (dead from health)
            # If just out of fuel, we wait until speed is 0
            if player.finished:
                race_over = True
            elif player.dead: # Wrecked or Overheated
                race_over = True
            elif player.fuel <= 0 and player.speed < 0.1:
                # Out of fuel and stopped
                player.dead = True # Now we are officially dead
                race_over = True
        
        # Rank Tracking & Sorting (Always update for HUD/Splits)
        # Sort by: 1. Finished (Time ascending), 2. Racing (Distance descending)
        all_cars.sort(key=lambda c: (0, c.finish_time) if c.finished else (1, -c.y))
        player_rank = all_cars.index(player) + 1

        # Camera follows player
        camera_y = player.y - SCREEN_HEIGHT // 3
                
        # Draw
        draw_track(screen, camera_y, current_race.length, current_race.checkpoints)
        
        # Draw Obstacles
        for obs in obstacles:
            obs.draw(screen, camera_y)
            
        # Draw AI cars
        for ai in ai_cars:
            ai.car.draw(screen, camera_y)
            
        # Draw player
        player.draw(screen, camera_y)
        
        # Draw Particles
        particles.draw(screen, camera_y)
        
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
            
            hint = pygame.font.Font(None, 24).render("Press R to Return to Garage", True, (150, 150, 150))
            screen.blit(hint, (SCREEN_WIDTH // 2 - 100, SCREEN_HEIGHT // 3 + 30))
        
        pygame.display.flip()
        clock.tick(60)


def main():
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption(f"DragOn v{VERSION} - Death Rally Style")
    clock = pygame.time.Clock()
    
    # Initialize Profile
    profile = PlayerProfile()
    
    # State Machine
    current_scene = "GARAGE"
    
    while True:
        if current_scene == "GARAGE":
            result = run_garage(screen, clock, profile)
            if result == "RACE":
                current_scene = "RACE"
            elif result == "QUIT":
                break
        elif current_scene == "RACE":
            result = run_race(screen, clock, profile)
            if result == "GARAGE":
                current_scene = "GARAGE"
            elif result == "QUIT":
                break
                
    pygame.quit()


if __name__ == "__main__":
    main()
