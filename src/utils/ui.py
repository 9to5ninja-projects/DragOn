import pygame
import math
from src.settings import *

def draw_track(surface, camera_y, race_length, checkpoints):
    # Fill background
    surface.fill(COLOR_BG)
    
    # Draw Sidebars Background
    pygame.draw.rect(surface, COLOR_SIDEBAR_BG, (0, 0, SIDEBAR_WIDTH, SCREEN_HEIGHT))
    pygame.draw.rect(surface, COLOR_SIDEBAR_BG, (SCREEN_WIDTH - SIDEBAR_WIDTH, 0, SIDEBAR_WIDTH, SCREEN_HEIGHT))
    
    # Track Area
    track_left = TRACK_X
    track_right = TRACK_X + TRACK_WIDTH
    
    # Main track surface
    pygame.draw.rect(surface, COLOR_TRACK, (track_left, 0, TRACK_WIDTH, SCREEN_HEIGHT))
    
    # Edge lines
    pygame.draw.rect(surface, COLOR_TRACK_EDGE, (track_left, 0, 3, SCREEN_HEIGHT))
    pygame.draw.rect(surface, COLOR_TRACK_EDGE, (track_right - 3, 0, 3, SCREEN_HEIGHT))
    
    # Distance markers
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
            pygame.draw.line(surface, (0, 100, 255), 
                           (track_left, screen_y), (track_right, screen_y), 5)
            text = font.render("CHECKPOINT", True, (0, 200, 255))
            surface.blit(text, (track_left + 10, screen_y - 20))
            
    # Finish Line
    finish_screen_y = SCREEN_HEIGHT - (race_length - camera_y)
    if -50 < finish_screen_y < SCREEN_HEIGHT + 50:
        check_size = 20
        rows = 3
        cols = TRACK_WIDTH // check_size
        for r in range(rows):
            for c in range(cols):
                color = (255, 255, 255) if (r + c) % 2 == 0 else (0, 0, 0)
                pygame.draw.rect(surface, color, 
                               (track_left + c * check_size, finish_screen_y - r * check_size, check_size, check_size))

def draw_dashboard(surface, player):
    """Draw Left Sidebar Dashboard."""
    x_offset = 20
    y_offset = 20
    width = SIDEBAR_WIDTH - 40
    
    font_header = pygame.font.Font(None, 36)
    font_val = pygame.font.Font(None, 28)
    
    # Car Name
    surface.blit(font_header.render(player.stats.name, True, COLOR_HIGHLIGHT), (x_offset, y_offset))
    y_offset += 40
    
    # Health
    hp_pct = max(0, player.health / player.stats.durability)
    pygame.draw.rect(surface, (50, 0, 0), (x_offset, y_offset, width, 20))
    pygame.draw.rect(surface, (200, 0, 0) if hp_pct < 0.3 else (0, 200, 0), (x_offset, y_offset, int(width * hp_pct), 20))
    surface.blit(font_val.render(f"HP: {int(player.health)}", True, COLOR_TEXT), (x_offset, y_offset + 25))
    y_offset += 60
    
    # Fuel
    fuel_pct = max(0, player.fuel / player.stats.fuel_capacity)
    pygame.draw.rect(surface, (0, 50, 0), (x_offset, y_offset, width, 20))
    pygame.draw.rect(surface, (0, 200, 0), (x_offset, y_offset, int(width * fuel_pct), 20))
    surface.blit(font_val.render(f"FUEL: {int(player.fuel)}", True, COLOR_TEXT), (x_offset, y_offset + 25))
    y_offset += 60
    
    # Heat
    heat_pct = min(1.0, player.heat / player.stats.heat_capacity)
    pygame.draw.rect(surface, (50, 0, 0), (x_offset, y_offset, width, 20))
    pygame.draw.rect(surface, (255, 100, 0) if heat_pct > 0.8 else (100, 100, 200), (x_offset, y_offset, int(width * heat_pct), 20))
    surface.blit(font_val.render(f"HEAT: {int(player.heat)}", True, COLOR_TEXT), (x_offset, y_offset + 25))
    y_offset += 60
    
    # Analog Gauges (Speedometer / Tachometer)
    center_x = x_offset + width // 2
    center_y = y_offset + 80
    radius = 60
    
    # Tachometer (Throttle)
    pygame.draw.circle(surface, (20, 20, 20), (center_x, center_y), radius)
    pygame.draw.circle(surface, (100, 100, 100), (center_x, center_y), radius, 2)
    
    # Tacho markings
    for i in range(11):
        angle = 225 - (i * 27) # 225 to -45 degrees
        rad = math.radians(angle)
        sx = center_x + math.cos(rad) * (radius - 10)
        sy = center_y - math.sin(rad) * (radius - 10)
        ex = center_x + math.cos(rad) * radius
        ey = center_y - math.sin(rad) * radius
        col = (255, 0, 0) if i >= 8 else (200, 200, 200)
        pygame.draw.line(surface, col, (sx, sy), (ex, ey), 2)
        
    # Needle
    throttle_angle = 225 - (player.throttle / 100.0 * 270)
    rad = math.radians(throttle_angle)
    nx = center_x + math.cos(rad) * (radius - 5)
    ny = center_y - math.sin(rad) * (radius - 5)
    pygame.draw.line(surface, (255, 50, 0), (center_x, center_y), (nx, ny), 3)
    
    surface.blit(font_val.render("RPM", True, (100, 100, 100)), (center_x - 20, center_y + 20))
    
    y_offset += 180
    
    # Speedometer (Digital for now, simpler)
    surface.blit(font_header.render(f"{player.speed:.1f} KM/H", True, COLOR_HIGHLIGHT), (x_offset, y_offset))
    
    # Nitro
    y_offset += 50
    for i in range(NITRO_CHARGES):
        col = (255, 200, 0) if i < player.nitro_charges else (50, 50, 50)
        pygame.draw.circle(surface, col, (x_offset + 20 + i*40, y_offset), 15)
    surface.blit(font_val.render("NITRO", True, COLOR_TEXT), (x_offset + 140, y_offset - 10))

def draw_stats_panel(surface, player, all_cars, race_time, total_cars):
    """Draw Right Sidebar Stats."""
    x_offset = SCREEN_WIDTH - SIDEBAR_WIDTH + 20
    y_offset = 20
    
    font_header = pygame.font.Font(None, 36)
    font_row = pygame.font.Font(None, 24)
    
    # Time
    mins = race_time // 3600
    secs = (race_time % 3600) / 60.0
    surface.blit(font_header.render(f"TIME: {mins:02d}:{secs:05.2f}", True, COLOR_HIGHLIGHT), (x_offset, y_offset))
    y_offset += 50
    
    # Leaderboard
    surface.blit(font_header.render("STANDINGS", True, COLOR_TEXT), (x_offset, y_offset))
    y_offset += 30
    
    # Sort cars by position
    # Helper to get the underlying car object
    def get_car(obj):
        return obj.car if hasattr(obj, 'car') else obj

    sorted_cars = sorted(all_cars, key=lambda c: (0, get_car(c).finish_time) if get_car(c).finished else (1, -get_car(c).y))
    
    for i, car_obj in enumerate(sorted_cars):
        if i > 9: break # Show top 10
        
        car = get_car(car_obj)
        
        col = COLOR_HIGHLIGHT if car.is_player else COLOR_TEXT
        if car.dead: col = (100, 100, 100)
        elif car.finished: col = (0, 255, 0)
        
        name = "PLAYER" if car.is_player else f"Racer {i+1}"
        
        status_text = car.get_status_text()
        if status_text == "RACING":
            # Show distance or checkpoint
            # Calculate checkpoint index (approximate)
            cp_idx = int(car.y / LEG_DISTANCE)
            status = f"{int(car.y)}m (CP:{cp_idx})"
        else:
            status = status_text
        
        text = f"{i+1}. {name} - {status}"
        surface.blit(font_row.render(text, True, col), (x_offset, y_offset))
        y_offset += 25
        
    # Minimap (Simplified vertical line)
    y_offset += 50
    map_height = 300
    map_width = 20
    pygame.draw.rect(surface, (0, 0, 0), (x_offset, y_offset, map_width, map_height))
    pygame.draw.rect(surface, (100, 100, 100), (x_offset, y_offset, map_width, map_height), 1)
    
    race_len = player.race_length
    for car_obj in all_cars:
        car = get_car(car_obj)
        if car.dead: continue
        p_y = min(1.0, max(0.0, car.y / race_len))
        screen_y = y_offset + map_height - (p_y * map_height)
        col = (0, 255, 0) if car.is_player else (255, 0, 0)
        pygame.draw.rect(surface, col, (x_offset, screen_y - 2, map_width, 4))
