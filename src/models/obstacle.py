import pygame
from src.settings import *

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
            pygame.draw.rect(surface, (0,0,0), (self.x, screen_y, self.width, self.height), 1)
