import pygame

# ============================================================================
# VERSION INFO
# ============================================================================
VERSION = "0.3.0"

# ============================================================================
# DISPLAY SETTINGS
# ============================================================================
# We will use a 1280x720 base for windowed, but support fullscreen
SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 720
FPS = 60

# Layout
SIDEBAR_WIDTH = 300
TRACK_WIDTH = 600 # Wider track for better racing
TRACK_X = SIDEBAR_WIDTH # Starts after left sidebar

# ============================================================================
# PHYSICS & TUNING
# ============================================================================
DRAFTING_DIST = 120
DRAFTING_WIDTH = 25
DRAFTING_SPEED_BONUS = 1.5
DRAFTING_FUEL_SAVER = 0.5
COLLISION_BOUNCE = 2.0
COLLISION_DAMAGE_BASE = 2.0
COLLISION_DAMAGE_FACTOR = 0.5

# Consumption rates per frame at different throttle levels
EFFICIENCY_CURVE = {
    100: (0.08, 0.12),
    90:  (0.06, 0.08),
    80:  (0.04, 0.04),
    70:  (0.03, 0.02),
    60:  (0.025, 0.0),
    50:  (0.02, -0.02),
    40:  (0.015, -0.04),
    30:  (0.01, -0.06),
    20:  (0.008, -0.08),
    10:  (0.005, -0.10),
    0:   (0.0, -0.12),
}

HEAT_WARNING = 80.0
HEAT_CRITICAL = 95.0
OVERHEAT_SPEED_PENALTY = 0.5

NITRO_CHARGES = 3
NITRO_DURATION = 45
NITRO_SPEED_BOOST = 4.0
NITRO_FUEL_COST = 10.0
NITRO_HEAT_SPIKE = 15.0

AI_SPEED_VARIANCE = 1.0

# ============================================================================
# COLORS
# ============================================================================
COLOR_BG = (20, 20, 30)
COLOR_SIDEBAR_BG = (30, 30, 40)
COLOR_TRACK = (60, 60, 60)
COLOR_TRACK_EDGE = (120, 120, 120)
COLOR_PLAYER = (80, 180, 80)
COLOR_PLAYER_HOT = (180, 80, 80)
COLOR_TEXT = (200, 200, 200)
COLOR_HIGHLIGHT = (255, 200, 0)

# ============================================================================
# CAREER CONSTANTS
# ============================================================================
LEG_DISTANCE = 7500 # 1 Leg = 7500 meters/pixels
