import pygame
import random
from src.settings import *
from src.models.particle import ParticleSystem

# Global particle system reference (hacky but works for now)
particles = ParticleSystem()

class Car:
    def __init__(self, x, y, color, stats, race_length, is_player=False, profile=None):
        self.x = x
        self.y = y  # world position (0 = start, race_length = finish)
        self.width = 20
        self.height = 35
        
        # Random color for AI if not specified
        if not is_player and color == COLOR_PLAYER: # Should not happen but safety
             self.color = (random.randint(50, 200), random.randint(50, 200), random.randint(50, 200))
        elif not is_player:
             # Randomize AI colors
             self.color = (random.randint(50, 200), random.randint(50, 200), random.randint(50, 200))
        else:
             self.color = color

        self.stats = stats
        self.race_length = race_length
        self.is_player = is_player
        
        # Movement
        self.speed = 0.0
        self.lateral_speed = 0.0
        self.throttle = 100 if not is_player else 50
        
        # Resources
        self.fuel = self.stats.fuel_capacity
        self.heat = 20.0
        
        if is_player and profile:
            self.health = profile.health
            self.comp_front = profile.comp_front
            self.comp_rear = profile.comp_rear
            self.comp_fl = profile.comp_fl
            self.comp_fr = profile.comp_fr
            self.comp_rl = profile.comp_rl
            self.comp_rr = profile.comp_rr
            # Load Nitro
            self.nitro_charges = profile.nitro_charges if profile.nitro_installed else 0
        else:
            self.health = self.stats.durability
            self.comp_front = 1.0
            self.comp_rear = 1.0
            self.comp_fl = 1.0
            self.comp_fr = 1.0
            self.comp_rl = 1.0
            self.comp_rr = 1.0
            # AI Nitro
            self.nitro_charges = NITRO_CHARGES if not is_player else 0
        
        # Nitro State
        self.nitro_active = 0
        
        # State
        self.finished = False
        self.finish_time = 0
        self.dead = False
        self.is_drafting = False
        self.is_side_drafting = False
        self.next_checkpoint_idx = 0
        
    def get_target_speed(self):
        base = self.stats.max_speed * (self.throttle / 100.0)
        if self.comp_front < 1.0:
            base *= (0.5 + 0.5 * self.comp_front)
            
        # Drafting Bonuses
        if self.is_drafting:
            base *= DRAFTING_SPEED_BONUS
        
        if self.is_side_drafting:
            base *= 1.15 # 15% speed boost for side drafting
            
        return base

    def apply_damage(self, amount, sector):
        if self.dead:
            return
            
        self.health -= amount
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
            
        if self.health <= 0:
            self.health = 0
            self.dead = True
            
    def update_resources(self):
        if self.dead or self.finished:
            return
            
        if self.health <= 0:
            self.dead = True
            self.health = 0
            
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
        
        if heat_delta < 0:
            heat_delta *= self.stats.cooling_factor
        
        if self.comp_rear < 0.8:
            leak_rate = (0.8 - self.comp_rear) * 0.1
            fuel_burn += leak_rate
        
        if self.is_drafting:
            fuel_burn *= DRAFTING_FUEL_SAVER
        
        if self.nitro_active > 0:
            fuel_burn *= 2.0
            heat_delta = abs(heat_delta) + 0.1
        
        self.fuel -= fuel_burn
        self.heat += heat_delta
        self.heat = max(0.0, min(self.stats.heat_capacity, self.heat))
        
        if self.fuel <= 0:
            self.fuel = 0
            
        if self.heat >= self.stats.heat_capacity:
            self.dead = True
            
    def steer(self, direction):
        if self.dead or self.finished:
            return
            
        # Calculate steering effectiveness based on speed
        speed_factor = 1.0
        
        if self.speed < 2.0:
            # Low speed: poor steering (need movement to turn)
            speed_factor = self.speed / 2.0
        elif self.speed > 8.0:
            # High speed: stiff steering for stability
            # Decay from 1.0 down to 0.2 as speed increases
            speed_factor = max(0.2, 1.0 - ((self.speed - 8.0) * 0.08))
            
        tire_health = (self.comp_fl + self.comp_fr) / 2.0
        speed_factor *= (0.3 + 0.7 * tire_health)
        
        # Apply force
        # Increased base force to compensate for lateral friction
        force = direction * 0.6 * speed_factor
        self.lateral_speed += force
        
    def update(self):
        target = self.get_target_speed()
        if self.fuel <= 0 or self.dead:
            target = 0
        
        if self.speed < target:
            if not self.dead and self.fuel > 0:
                self.speed += self.stats.acceleration
            else:
                self.speed -= 0.05
        elif self.speed > target:
            self.speed -= 0.05
            
        # Apply Lateral Friction (Drag)
        # Prevents infinite sliding ("hovering")
        self.lateral_speed *= 0.92
            
        self.x += self.lateral_speed
        
        # Track Boundaries
        # Left Wall
        if self.x < TRACK_X + self.width/2:
            self.x = TRACK_X + self.width/2
            self.lateral_speed = -self.lateral_speed * 0.5
            self.apply_damage(2.0, "FL")
            particles.add_explosion(self.x, self.y, 5, (200, 200, 200))
            
        # Right Wall
        elif self.x > TRACK_X + TRACK_WIDTH - self.width/2:
            self.x = TRACK_X + TRACK_WIDTH - self.width/2
            self.lateral_speed = -self.lateral_speed * 0.5
            self.apply_damage(2.0, "FR")
            particles.add_explosion(self.x, self.y, 5, (200, 200, 200))
        
        self.y += self.speed
        self.update_resources()
        
        # Smoke
        if self.health < self.stats.durability * 0.5:
            if random.random() < 0.3:
                particles.add(self.x + random.randint(-10, 10), self.y + 10, 
                              random.uniform(-1, 1), random.uniform(1, 3), 
                              random.randint(30, 60), (100, 100, 100), random.randint(5, 10))
        
        if self.health < self.stats.durability * 0.2:
             if random.random() < 0.5:
                particles.add(self.x + random.randint(-10, 10), self.y + 10, 
                              random.uniform(-1, 1), random.uniform(1, 3), 
                              random.randint(30, 60), (50, 50, 50), random.randint(8, 15))
        
        if self.health <= 0:
            self.speed *= 0.9
            if self.speed < 0.1:
                self.speed = 0
        
        # Prevent negative speed runaway
        if self.speed < 0:
            self.speed = 0
            
        if self.nitro_active > 0:
            self.nitro_active -= 1

    def get_status_text(self):
        if self.finished:
            return "FINISHED"
        if self.health <= 0:
            return "WRECKED"
        if self.heat >= self.stats.heat_capacity:
            return "OVERHEAT"
        if self.fuel <= 0:
            return "NO FUEL"
        return "RACING"

    def check_finish(self, current_time):
        if not self.finished and self.y >= self.race_length:
            self.finished = True
            self.finish_time = current_time
            return True
        return False
            
    def use_nitro(self):
        if self.nitro_charges > 0 and self.nitro_active == 0 and not self.dead:
            self.nitro_charges -= 1
            self.nitro_active = NITRO_DURATION
            self.fuel -= NITRO_FUEL_COST
            self.heat += NITRO_HEAT_SPIKE
            return True
        return False
    
    def adjust_throttle(self, delta):
        self.throttle = max(0, min(100, self.throttle + delta))
        
    def get_rect(self):
        return pygame.Rect(self.x - self.width // 2, self.y - self.height // 2, self.width, self.height)
    
    def draw(self, surface, camera_y):
        screen_y = SCREEN_HEIGHT - (self.y - camera_y) - self.height // 2
        screen_x = self.x - self.width // 2
        
        if -self.height < screen_y < SCREEN_HEIGHT + self.height:
            color = self.color
            if self.is_player and self.heat > HEAT_WARNING:
                heat_factor = (self.heat - HEAT_WARNING) / (self.stats.heat_capacity - HEAT_WARNING)
                color = (
                    int(self.color[0] + (COLOR_PLAYER_HOT[0] - self.color[0]) * heat_factor),
                    int(self.color[1] + (COLOR_PLAYER_HOT[1] - self.color[1]) * heat_factor),
                    int(self.color[2] + (COLOR_PLAYER_HOT[2] - self.color[2]) * heat_factor),
                )
            
            pygame.draw.rect(surface, color, (screen_x, screen_y, self.width, self.height))
            
            if self.nitro_active > 0:
                pygame.draw.rect(surface, (255, 200, 0), (screen_x - 2, screen_y + self.height - 5, self.width + 4, 5))
            
            if self.is_drafting:
                pygame.draw.circle(surface, (100, 255, 255), (screen_x + self.width//2, screen_y - 5), 3)

class AIDriver:
    def __init__(self, car):
        self.car = car
        self.target_speed_offset = random.uniform(-AI_SPEED_VARIANCE, AI_SPEED_VARIANCE)
        self.lane_preference = random.choice([-1, 0, 1]) # -1 Left, 0 Center, 1 Right
        self.reaction_timer = 0
        self.target_x = None
        self.cooling_mode = False # State for hysteresis
        
    def update(self, track_center, obstacles, other_cars):
        if self.car.dead or self.car.finished:
            return
            
        # Determine Rank/Urgency
        cars_ahead = 0
        for c in other_cars:
            if c.finished or (not c.dead and c.y > self.car.y):
                cars_ahead += 1
        
        # Urgency: Behind anyone OR close to finish
        is_urgent = (cars_ahead > 0) or (self.car.y > self.car.race_length * 0.85)
        
        # Throttle Logic (Heat Management with Hysteresis)
        heat_pct = self.car.heat / self.car.stats.heat_capacity
        
        # Thresholds
        if is_urgent:
            limit_heat = 0.92  # Push harder
            resume_heat = 0.75 # Resume sooner
            cruise_throttle = 95
        else:
            limit_heat = 0.85
            resume_heat = 0.60 # Cool down more thoroughly
            cruise_throttle = 85
            
        # State Machine
        if self.cooling_mode:
            if heat_pct < resume_heat:
                self.cooling_mode = False
                target_throttle = cruise_throttle + random.randint(-5, 5)
            else:
                target_throttle = 50 # Continue cooling
        else:
            if heat_pct > limit_heat:
                self.cooling_mode = True
                target_throttle = 40 # Cut throttle
            else:
                target_throttle = cruise_throttle + random.randint(-5, 5)
            
        if self.car.throttle < target_throttle:
            self.car.adjust_throttle(5) 
        elif self.car.throttle > target_throttle:
            self.car.adjust_throttle(-10) 
            
        # Steering Logic
        # We want to determine a target_x and steer towards it
        
        # 1. Identify Hazards and Opportunities
        look_ahead = 400
        my_rect = self.car.get_rect()
        
        hazard_ahead = None
        hazard_dist = float('inf')
        
        draft_target = None
        draft_dist = float('inf')
        
        side_draft_target = None
        
        # Check Obstacles (Hazards)
        for obs in obstacles:
            if obs.y > self.car.y and obs.y < self.car.y + look_ahead:
                # Check if it blocks our current path
                if abs(obs.x - self.car.x) < (self.car.width + obs.width) * 0.8:
                    dist = obs.y - self.car.y
                    if dist < hazard_dist:
                        hazard_dist = dist
                        hazard_ahead = obs

        # Check Cars (Hazards or Draft Targets)
        for other in other_cars:
            if other == self.car or other.finished:
                continue
                
            if other.dead:
                # Treat as obstacle
                if other.y > self.car.y and other.y < self.car.y + look_ahead:
                    if abs(other.x - self.car.x) < (self.car.width + other.width) * 0.8:
                        dist = other.y - self.car.y
                        if dist < hazard_dist:
                            hazard_dist = dist
                            hazard_ahead = other
            else:
                # Active Car
                dy = other.y - self.car.y
                dx = other.x - self.car.x
                
                # Check for Side Draft (Overlap in Y)
                if abs(dy) < self.car.height * 0.8:
                    # We are alongside
                    # Check if close enough to side draft but not hit
                    # Ideal side draft distance: width + 5-10 pixels
                    if abs(dx) < self.car.width * 2.5:
                        side_draft_target = other
                
                # Check for Rear Draft (Ahead)
                elif 0 < dy < look_ahead:
                    # If it's in front of us
                    if abs(dx) < self.car.width * 2:
                        # It's alignable
                        if dy < draft_dist:
                            draft_dist = dy
                            draft_target = other

        # 2. Determine Target X
        # Track Boundaries for AI
        track_min_x = TRACK_X + self.car.width
        track_max_x = TRACK_X + TRACK_WIDTH - self.car.width
        
        # Default: Lane Preference
        if self.target_x is None:
            self.target_x = track_center + (self.lane_preference * 60)

        # Priority 1: Avoid Hazards
        if hazard_ahead:
            avoid_margin = self.car.width * 1.5
            
            # Check if we can go right
            can_go_right = (hazard_ahead.x + hazard_ahead.width + avoid_margin) < track_max_x
            # Check if we can go left
            can_go_left = (hazard_ahead.x - avoid_margin) > track_min_x
            
            if can_go_right and can_go_left:
                # Go to side with more space or closer to current preference
                if abs(self.car.x - (hazard_ahead.x - avoid_margin)) < abs(self.car.x - (hazard_ahead.x + hazard_ahead.width + avoid_margin)):
                     self.target_x = hazard_ahead.x - avoid_margin
                else:
                     self.target_x = hazard_ahead.x + hazard_ahead.width + avoid_margin
            elif can_go_right:
                self.target_x = hazard_ahead.x + hazard_ahead.width + avoid_margin
            elif can_go_left:
                self.target_x = hazard_ahead.x - avoid_margin
            else:
                # Stuck? Just try to squeeze?
                self.target_x = track_center # Panic center
                
        # Priority 2: Side Draft (if safe)
        elif side_draft_target:
            # Try to get close to the side
            # User requested tighter side drafting (1-2 pixels max gap)
            # But we need to be careful not to grind.
            # Let's aim for a 4 pixel gap.
            margin = 4 
            if side_draft_target.x > self.car.x:
                self.target_x = side_draft_target.x - self.car.width - margin
            else:
                self.target_x = side_draft_target.x + side_draft_target.width + margin
                
        # Priority 3: Rear Draft (if safe)
        elif draft_target:
            # Slingshot Logic
            # If we are drafting, we want to stay in the slipstream until we are close
            # But not TOO close (grinding).
            
            # Safe following distance (gap)
            # 8-10 pixels gap requested.
            # Distance is center-to-center in Y? No, dy is other.y - self.car.y (front to back approx if origin is top left?)
            # Actually y is usually center or bottom?
            # Let's assume y is world position.
            # dy = other.y - self.car.y.
            # If dy is positive, other is ahead.
            # Gap = dy - self.car.height (approx).
            
            gap = draft_dist - self.car.height
            
            # Slingshot Threshold: When to peel out
            # If we are faster than them and close, peel out.
            # Or if we are just too close.
            
            slingshot_gap = 15 # Start steering out when 15px away
            
            if gap < slingshot_gap:
                # Overtake / Slingshot
                overtake_margin = self.car.width * 1.5 # Give plenty of room
                
                # Choose side:
                # If we are already slightly to one side, commit to it.
                # Else go to the side with more track space.
                
                bias = self.car.x - draft_target.x
                
                if abs(bias) > 5:
                    # Commit to current offset
                    direction = 1 if bias > 0 else -1
                else:
                    # Choose open side
                    dist_to_left = draft_target.x - track_min_x
                    dist_to_right = track_max_x - (draft_target.x + draft_target.width)
                    direction = 1 if dist_to_right > dist_to_left else -1
                    
                self.target_x = draft_target.x + (direction * (self.car.width + overtake_margin))
                
            else:
                # Draft! Align with them
                # But add a tiny bit of noise so they don't stack perfectly like robots
                self.target_x = draft_target.x + random.uniform(-2, 2)
                
        # Priority 4: Cruise (Lane Preference)
        else:
            # Slowly drift back to preference if nothing else is happening
            preferred_x = track_center + (self.lane_preference * 60)
            # Only change if we are far off
            if abs(self.car.x - preferred_x) > 20:
                self.target_x = preferred_x
                
        # Final Clamp to Track Boundaries
        self.target_x = max(track_min_x, min(track_max_x, self.target_x))

        # 3. Apply Steering
        # Smooth steering using Proportional Control based on lateral speed
        # This prevents the "bouncy" behavior of overcorrecting
        
        # Desired lateral velocity is proportional to distance to target
        # k_p = 0.05 means for 100px error, we want 5px/frame lateral speed
        desired_lateral_speed = (self.target_x - self.car.x) * 0.05
        
        # Clamp desired speed to max steering capability roughly
        desired_lateral_speed = max(-3.0, min(3.0, desired_lateral_speed))
        
        # Calculate error in velocity
        speed_error = desired_lateral_speed - self.car.lateral_speed
        
        steer_dir = 0
        threshold = 0.1
        
        if speed_error > threshold:
            steer_dir = 1
        elif speed_error < -threshold:
            steer_dir = -1
            
        if steer_dir != 0:
            self.car.steer(steer_dir)
