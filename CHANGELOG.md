# Changelog

All notable changes to this project will be documented in this file.

## [0.3.0] - 2025-12-05

### Added
- **Nitro System**:
    - Added Nitro purchase ($2000) and refill ($100/charge) in Garage.
    - Implemented Nitro physics (Speed boost, Fuel burn, Heat spike).
- **Advanced Physics**:
    - **Side Drafting**: Added 1.15x speed boost when racing door-to-door.
    - **Lateral Friction**: Added tire grip simulation to prevent "hovering".
    - **Speed-Sensitive Steering**: Steering becomes stiffer at high speeds for stability.
- **AI Improvements**:
    - **Heat Management**: AI now manages engine temp, cooling down when safe and pushing when urgent.
    - **Advanced Drafting**: AI now performs "Slingshot" overtakes and tighter side-drafting.
    - **Steering Control**: Implemented PID-like control to reduce "bounciness" and wall impacts.
- **UI Enhancements**:
    - Added detailed Race Status (WRECKED, NO FUEL, OVERHEAT) to leaderboard.
    - Added Checkpoint tracking to leaderboard.

### Fixed
- **Economy**: Fixed bug where negative health caused astronomical repair bills.
- **Physics**: Fixed "Flying Backwards" bug where wrecked cars accelerated in reverse.
- **Drafting**: Fixed Rear Draft speed bonus not applying correctly.
- **UI**: Fixed Garage button layout to prevent text clipping.

## [0.2.0] - 2025-12-05

### Added
- **Game Loop**: Split monolithic main loop into distinct `Garage` and `Race` scenes.
- **Economy System**:
    - Added `PlayerProfile` to track money ($1000 start) and persistent car state.
    - Added Repair system with variable costs based on damage severity.
    - Added Engine Upgrade system (Level based stats boost).
- **Visual Effects**:
    - Implemented `ParticleSystem` for smoke, fire, and explosions.
    - Added visual damage indicators (smoke intensity increases with damage).
    - Added "Head-on" collision explosions.
- **Gameplay Mechanics**:
    - **Persistent Damage**: Car health and component damage (Tires, Engine, Fuel Tank) persist between races.
    - **Obstacles**: Added Rocks and Barriers to the track generation.
    - **Wreck Logic**: Added "Dead" state for wrecked cars (become solid obstacles).
    - **Coasting**: Running out of fuel now allows coasting; 0 Health is a hard stop.
    - **Checkpoints**: Added fuel/heat restore on checkpoints.

### Changed
- **Physics**:
    - Improved collision resolution to prevent "sticky" cars.
    - Added "bounce back" on impact.
    - Fixed particle rendering coordinate system (sparks now fly correctly relative to camera).
- **UI/HUD**:
    - New Garage Interface with component status bars.
    - Updated Race HUD with split times and rank.

### Fixed
- Fixed entry point bug where game would not launch after refactoring.
- Fixed particle y-axis rendering direction.

## [0.1.0] - Initial Prototype
- Basic racing physics (Acceleration, Drag, Steering).
- Resource management (Fuel, Heat).
- Simple AI opponents.
- Infinite scrolling track.
