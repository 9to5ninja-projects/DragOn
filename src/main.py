import pygame
from src.settings import *
from src.models.player_profile import PlayerProfile
from src.scenes.garage import run_garage
from src.scenes.race import run_race

def main():
    pygame.init()
    # Fullscreen support
    # screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
    # For development/windowed mode use settings
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    
    pygame.display.set_caption(f"DragOn v{VERSION} - Career Mode")
    clock = pygame.time.Clock()
    
    profile = PlayerProfile()
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
