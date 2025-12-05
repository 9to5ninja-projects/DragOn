from src.settings import *
from src.models.particle import ParticleSystem

# We need to pass the particle system in or use the global one from car.py (which is bad practice but quick refactor)
# Better: Pass it in. For now, let's import the one from car.py to maintain state
from src.models.car import particles

def handle_physics(cars, obstacles=None):
    if obstacles is None:
        obstacles = []
        
    for car in cars:
        car.is_drafting = False
        car.is_side_drafting = False
        
    for i, car_a in enumerate(cars):
        if car_a.finished:
            continue
            
        rect_a = car_a.get_rect()
        
        for obs in obstacles:
            if rect_a.colliderect(obs.get_rect()):
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
                    dmg_amount = max(1.0, obs.damage) 
                    car_a.apply_damage(dmg_amount, "FRONT") 
                    car_a.speed *= 0.5
                    particles.add_explosion(car_a.x + car_a.width/2, car_a.y + car_a.height/2, 5, (200, 200, 200))
                    
                    if car_a.y < obs.y: 
                        car_a.y = obs.y - car_a.height - 5
                
        for j, car_b in enumerate(cars):
            if i == j or car_b.finished:
                continue
                
            rect_b = car_b.get_rect()
            
            if rect_a.colliderect(rect_b):
                dx = car_a.x - car_b.x
                dy = car_a.y - car_b.y
                
                if abs(dx) > abs(dy):
                    push = COLLISION_BOUNCE
                    particles.add_explosion(car_a.x + (0 if dx > 0 else car_a.width), car_a.y + car_a.height/2, 5, (255, 200, 0))
                    if dx > 0:
                        car_a.x += push
                        car_b.x -= push
                        car_a.apply_damage(5.0, "FL" if car_a.y > car_b.y else "RL")
                        car_b.apply_damage(5.0, "FR" if car_b.y > car_a.y else "RR")
                    else:
                        car_a.x -= push
                        car_b.x += push
                        car_a.apply_damage(5.0, "FR" if car_a.y > car_b.y else "RR")
                        car_b.apply_damage(5.0, "FL" if car_b.y > car_a.y else "RL")
                        
                else:
                    particles.add_explosion(car_a.x + car_a.width/2, car_a.y + (car_a.height if dy < 0 else 0), 8, (255, 100, 0))
                    if dy < 0:
                        car_a.speed *= 0.9
                        car_a.y = car_b.y - car_a.height - 1
                        impact = abs(car_a.speed - car_b.speed) * 2.0
                        car_a.apply_damage(impact, "FRONT")
                        car_b.apply_damage(impact, "REAR")
                    else:
                        car_b.speed *= 0.9
                        car_b.y = car_a.y - car_b.height - 1
                        impact = abs(car_a.speed - car_b.speed) * 2.0
                        car_b.apply_damage(impact, "FRONT")
                        car_a.apply_damage(impact, "REAR")
            
            # Drafting Logic
            dy = car_b.y - car_a.y
            dx = abs(car_a.x - car_b.x)
            
            # Rear Draft (Slipstream)
            if 0 < dy < DRAFTING_DIST:
                if dx < DRAFTING_WIDTH:
                    car_a.is_drafting = True
                    
            # Side Draft (Aerodynamic Push)
            # Must be overlapping in Y (alongside) and close in X
            if abs(dy) < car_a.height * 0.8:
                if dx < car_a.width * 2.0: # Close proximity
                    car_a.is_side_drafting = True
