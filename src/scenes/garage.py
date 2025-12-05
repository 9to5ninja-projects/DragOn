import pygame
from src.settings import *

def run_garage(screen, clock, profile):
    """Garage scene loop."""
    running = True
    font_title = pygame.font.Font(None, 64)
    font_main = pygame.font.Font(None, 36)
    font_small = pygame.font.Font(None, 24)
    
    while running:
        screen.fill(COLOR_BG)
        
        # Title
        title = font_title.render("GARAGE", True, COLOR_TEXT)
        screen.blit(title, (20, 20))
        
        # Money
        money_text = font_main.render(f"FUNDS: ${profile.money}", True, (100, 255, 100))
        screen.blit(money_text, (SCREEN_WIDTH - 250, 30))
        
        # Car Status
        status_y = 100
        pygame.draw.rect(screen, COLOR_SIDEBAR_BG, (20, status_y, SCREEN_WIDTH - 40, 300))
        
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
        pygame.draw.rect(screen, repair_col, (40, status_y + 150, 200, 40))
        screen.blit(font_main.render(f"REPAIR (${repair_cost})", True, (255,255,255)), (50, status_y + 158))
        
        # Upgrade Button
        upg_cost = profile.upgrade_engine_cost()
        upg_col = (0, 100, 200) if profile.money >= upg_cost else (100, 100, 100)
        pygame.draw.rect(screen, upg_col, (260, status_y + 150, 200, 40))
        screen.blit(font_main.render(f"ENGINE +1 (${upg_cost})", True, (255,255,255)), (270, status_y + 158))
        screen.blit(font_small.render(f"Lvl: {profile.engine_level}", True, (200, 200, 255)), (270, status_y + 195))
        
        # Nitro Button
        nitro_x = 480
        if not profile.nitro_installed:
            nitro_cost = 2000
            nitro_col = (200, 0, 200) if profile.money >= nitro_cost else (100, 100, 100)
            pygame.draw.rect(screen, nitro_col, (nitro_x, status_y + 150, 200, 40))
            screen.blit(font_main.render(f"BUY NITRO ($2k)", True, (255,255,255)), (nitro_x + 10, status_y + 158))
        else:
            # Refill
            charges_missing = profile.max_nitro_charges - profile.nitro_charges
            if charges_missing > 0:
                refill_cost = charges_missing * 100
                refill_col = (200, 0, 200) if profile.money >= 100 else (100, 100, 100)
                pygame.draw.rect(screen, refill_col, (nitro_x, status_y + 150, 200, 40))
                screen.blit(font_main.render(f"REFILL (${refill_cost})", True, (255,255,255)), (nitro_x + 10, status_y + 158))
            else:
                pygame.draw.rect(screen, (50, 50, 50), (nitro_x, status_y + 150, 200, 40))
                screen.blit(font_main.render("NITRO FULL", True, (150, 150, 150)), (nitro_x + 20, status_y + 158))
        
        screen.blit(font_small.render(f"Charges: {profile.nitro_charges}/{profile.max_nitro_charges}", True, (255, 200, 255)), (nitro_x + 10, status_y + 195))
        
        # Race Selection (Career Mode)
        # Simple toggle for now: 1v1 or Pack
        pygame.draw.rect(screen, (200, 100, 0), (SCREEN_WIDTH - 200, SCREEN_HEIGHT - 100, 180, 80))
        screen.blit(font_main.render("RACE", True, (255,255,255)), (SCREEN_WIDTH - 150, SCREEN_HEIGHT - 75))
        
        # Input
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return "QUIT"
            if event.type == pygame.MOUSEBUTTONDOWN:
                mx, my = pygame.mouse.get_pos()
                
                # Repair Click
                if 40 <= mx <= 240 and status_y + 150 <= my <= status_y + 190:
                    if repair_cost > 0:
                        profile.repair_all()
                        
                # Upgrade Click
                if 260 <= mx <= 460 and status_y + 150 <= my <= status_y + 190:
                    profile.upgrade_engine()
                    
                # Nitro Click
                if nitro_x <= mx <= nitro_x + 200 and status_y + 150 <= my <= status_y + 190:
                    if not profile.nitro_installed:
                        profile.buy_nitro_system()
                    else:
                        profile.refill_nitro()
                        
                # Race Click
                if SCREEN_WIDTH - 200 <= mx <= SCREEN_WIDTH - 20 and SCREEN_HEIGHT - 100 <= my <= SCREEN_HEIGHT - 20:
                    return "RACE"
                    
        pygame.display.flip()
        clock.tick(60)
