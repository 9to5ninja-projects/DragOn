import pygame
import random
from src.settings import *
from src.models.car import Car, AIDriver
from src.models.player_profile import TIER_1_STARTER
from src.models.obstacle import Obstacle
from src.models.particle import ParticleSystem
from src.utils.physics import handle_physics
from src.utils.ui import draw_track, draw_dashboard, draw_stats_panel

# Import global particles from car (hacky)
from src.models.car import particles

def run_race(screen, clock, profile):
    """Main race loop."""
    track_center = TRACK_X + TRACK_WIDTH // 2
    
    # Setup Race (Career Logic)
    # Beginner Race: 2 Legs (15000m), 6 Racers
    race_length = LEG_DISTANCE * 2
    num_ai = 5
    prize_money = 500
    
    # Grid Start Logic
    total_cars = num_ai + 1
    grid_spacing_y = 80
    grid_spacing_x = 80
    
    grid_positions = []
    for i in range(total_cars):
        row = i // 2
        col = i % 2
        x_offset = -grid_spacing_x/2 if col == 0 else grid_spacing_x/2
        gx = track_center + x_offset
        gy = 200 + row * grid_spacing_y
        grid_positions.append((gx, gy))
    
    grid_positions.reverse()
    
    # Player
    p_start = grid_positions[-1]
    player_stats = profile.get_modified_stats()
    player = Car(p_start[0], p_start[1], COLOR_PLAYER, player_stats, race_length, is_player=True, profile=profile)
    
    # AI
    ai_cars = []
    for i in range(num_ai):
        pos = grid_positions[i]
        # AI uses base tier
        ai_cars.append(AIDriver(Car(pos[0], pos[1], (0,0,0), TIER_1_STARTER, race_length))) # Color randomized in Car init
    
    # Obstacles
    obstacles = []
    track_left = TRACK_X
    track_right = TRACK_X + TRACK_WIDTH
    
    for _ in range(40):
        oy = random.randint(2000, race_length - 1000)
        ox = random.randint(track_left + 20, track_right - 50)
        otype = random.choice(["rock", "barrier"])
        obstacles.append(Obstacle(ox, oy, otype))
        
    # Checkpoints (Every Leg)
    checkpoints = [LEG_DISTANCE * (i+1) for i in range(race_length // LEG_DISTANCE)]
    
    # Reset Particles
    particles.particles = []
        
    running = True
    race_over = False
    race_time = 0
    
    # Game States
    STATE_COUNTDOWN = 0
    STATE_RACING = 1
    game_state = STATE_COUNTDOWN
    countdown_timer = 300 # 5 seconds at 60fps
    
    player_rank = total_cars
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
                    # Save state
                    profile.health = player.health
                    profile.comp_front = player.comp_front
                    profile.comp_rear = player.comp_rear
                    profile.comp_fl = player.comp_fl
                    profile.comp_fr = player.comp_fr
                    profile.comp_rl = player.comp_rl
                    profile.comp_rr = player.comp_rr
                    
                    # Save Nitro
                    if profile.nitro_installed:
                        profile.nitro_charges = player.nitro_charges
                    
                    if player.finished:
                        rank_factor = max(0, 1.0 - (player_rank - 1) * 0.1)
                        winnings = int(prize_money * rank_factor)
                        profile.money += winnings
                    
                    return "GARAGE"
                    
        keys = pygame.key.get_pressed()
        
        if game_state == STATE_RACING:
            if keys[pygame.K_LEFT]:
                player.steer(-1)
            if keys[pygame.K_RIGHT]:
                player.steer(1)
                
        if keys[pygame.K_UP]:
            player.adjust_throttle(1)
        if keys[pygame.K_DOWN]:
            player.adjust_throttle(-1)
            
        all_cars = [player] + [ai.car for ai in ai_cars]

        if game_state == STATE_COUNTDOWN:
            countdown_timer -= 1
            
            # Launch Logic
            if countdown_timer == 0:
                game_state = STATE_RACING
                # Check throttle for optimal launch
                if 80 <= player.throttle <= 90:
                    popup_text = "PERFECT LAUNCH!"
                    popup_timer = 60
                    player.speed = player.stats.max_speed * 0.5 # Boost
                elif player.throttle > 95:
                    popup_text = "WHEELSPIN!"
                    popup_timer = 60
                    player.speed = 0 # Stall/Spin
                    player.heat += 10
                else:
                    player.speed = 0
            
            player.update_resources()
            # Keep player stationary but allow engine revving
            # We need to prevent movement but allow resource update? 
            # Actually update_resources burns fuel.
            # Let's just clamp speed to 0
            player.speed = 0
            
        elif game_state == STATE_RACING:
            race_time += 1
            player.update()
            
            # Checkpoints
            if player.next_checkpoint_idx < len(checkpoints):
                cp_y = checkpoints[player.next_checkpoint_idx]
                if player.y >= cp_y:
                    player.next_checkpoint_idx += 1
                    player.fuel = min(player.stats.fuel_capacity, player.fuel + 40.0)
                    player.heat = max(0.0, player.heat - 50.0)
                    popup_text = "CHECKPOINT!"
                    popup_timer = 60
            
            for ai in ai_cars:
                ai.update(track_center, obstacles, all_cars)
                ai.car.update()
                
            handle_physics(all_cars, obstacles)
            particles.update()
            
            for car in all_cars:
                car.check_finish(race_time)
            
            if player.finished or player.dead or (player.fuel <= 0 and player.speed < 0.1):
                race_over = True
                if player.fuel <= 0 and player.speed < 0.1:
                    player.dead = True
        
        # Sorting
        all_cars.sort(key=lambda c: (0, c.finish_time) if c.finished else (1, -c.y))
        player_rank = all_cars.index(player) + 1

        camera_y = player.y - SCREEN_HEIGHT // 3
                
        # Draw
        draw_track(screen, camera_y, race_length, checkpoints)
        
        for obs in obstacles:
            obs.draw(screen, camera_y)
            
        for ai in ai_cars:
            ai.car.draw(screen, camera_y)
            
        player.draw(screen, camera_y)
        particles.draw(screen, camera_y)
        
        # UI Overlays
        draw_dashboard(screen, player)
        draw_stats_panel(screen, player, all_cars, race_time, total_cars)
        
        # Popup
        if popup_timer > 0:
            popup_timer -= 1
            p_font = pygame.font.Font(None, 64)
            p_surf = p_font.render(popup_text, True, COLOR_HIGHLIGHT)
            p_rect = p_surf.get_rect(center=(TRACK_X + TRACK_WIDTH // 2, SCREEN_HEIGHT // 2))
            screen.blit(p_surf, p_rect)
            
        # Countdown
        if game_state == STATE_COUNTDOWN:
            c_font = pygame.font.Font(None, 150)
            secs = (countdown_timer // 60) + 1
            c_text = c_font.render(str(secs), True, (255, 50, 50))
            if secs == 1:
                c_text = c_font.render("SET", True, (255, 200, 0))
            
            c_rect = c_text.get_rect(center=(TRACK_X + TRACK_WIDTH // 2, SCREEN_HEIGHT // 2))
            screen.blit(c_text, c_rect)
            
            hint_font = pygame.font.Font(None, 40)
            hint = hint_font.render("Target 80-90% RPM!", True, COLOR_TEXT)
            screen.blit(hint, (TRACK_X + TRACK_WIDTH // 2 - 150, SCREEN_HEIGHT // 2 + 80))
        
        if race_over:
            font = pygame.font.Font(None, 64)
            msg = "FINISHED!" if player.finished else "DNF"
            col = (50, 255, 50) if player.finished else (255, 50, 50)
            text = font.render(msg, True, col)
            text_rect = text.get_rect(center=(TRACK_X + TRACK_WIDTH // 2, SCREEN_HEIGHT // 3))
            pygame.draw.rect(screen, (0, 0, 0), text_rect.inflate(20, 10))
            screen.blit(text, text_rect)
            
            hint = pygame.font.Font(None, 32).render("Press R to Return", True, COLOR_TEXT)
            screen.blit(hint, (TRACK_X + TRACK_WIDTH // 2 - 100, SCREEN_HEIGHT // 3 + 50))
        
        pygame.display.flip()
        clock.tick(FPS)
