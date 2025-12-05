import random
import pygame
from src.settings import *

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
            s = max(1, int(self.size * (self.life / self.max_life)))
            # Fix coordinate system: y increases upwards in world
            screen_y = SCREEN_HEIGHT - (self.y - camera_y)
            
            # Only draw if on screen
            if -50 < screen_y < SCREEN_HEIGHT + 50:
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
