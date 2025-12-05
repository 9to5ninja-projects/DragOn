import copy
from src.settings import *

class CarStats:
    def __init__(self, name, max_speed, accel, fuel_cap, heat_cap, cooling_factor=1.0, durability=100.0):
        self.name = name
        self.max_speed = max_speed
        self.acceleration = accel
        self.fuel_capacity = fuel_cap
        self.heat_capacity = heat_cap
        self.cooling_factor = cooling_factor
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
        
        # Nitro System
        self.nitro_installed = False
        self.nitro_charges = 0
        self.max_nitro_charges = 3
        
    def get_modified_stats(self):
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
            
    def buy_nitro_system(self):
        cost = 2000
        if not self.nitro_installed and self.money >= cost:
            self.money -= cost
            self.nitro_installed = True
            self.nitro_charges = self.max_nitro_charges # Comes full? Sure.
            return True
        return False
        
    def refill_nitro(self):
        cost_per_charge = 100
        if self.nitro_installed and self.nitro_charges < self.max_nitro_charges:
            needed = self.max_nitro_charges - self.nitro_charges
            cost = needed * cost_per_charge
            if self.money >= cost:
                self.money -= cost
                self.nitro_charges = self.max_nitro_charges
                return True
            # Partial refill?
            can_afford = self.money // cost_per_charge
            if can_afford > 0:
                self.money -= can_afford * cost_per_charge
                self.nitro_charges += can_afford
                return True
        return False
            
    def get_repair_cost(self):
        """Calculate total repair cost."""
        total_loss = 0.0
        # Base health (Clamped to 0 to prevent massive costs from negative health)
        effective_health = max(0.0, self.health)
        total_loss += (1.0 - (effective_health / self.current_tier.durability)) * 100
        # Components
        total_loss += (1.0 - self.comp_front) * 50
        total_loss += (1.0 - self.comp_rear) * 50
        total_loss += (1.0 - self.comp_fl) * 25
        total_loss += (1.0 - self.comp_fr) * 25
        total_loss += (1.0 - self.comp_rl) * 25
        total_loss += (1.0 - self.comp_rr) * 25
        
        return int(total_loss * 2.0)

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
