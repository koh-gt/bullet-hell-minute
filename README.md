# bullet-hell-minute ⏱️🔫
80% Vibe Coded Bullet Hell - 20% Debug/Bugfix by koh-gt

A high-octane, intensely fast-paced 2D rogue-lite shooter built in Python and Pygame. 
Survive a quadratically scaling bullet hell where an average run lasts just 20 to 60 seconds. Collect coins, die, upgrade your ship, and drop back in!

## 🌟 Features

*   **Intense Micro-Runs:** The difficulty scales quadratically. 20 seconds is intense, 40 seconds is bullet-hell, and 60 seconds is near-impossible.
*   **Bullet-Time Shop:** Hold `E` to enter a 0.1x slow-motion state. The game doesn't pause—you must frantically buy upgrades while dodging incoming fire!
*   **Meta-Progression:** Your coins and upgrade levels permanently persist across runs. Grind short runs to build an unstoppable ship.
*   **Dynamic Leveling System:** Collect blue XP drops to instantly heal, increase your Max HP, and boost your base fire rate.
*   **Juicy Game Feel:** Experience camera shake, hit particles, flashing i-frames, and a massive translucent central survival clock.

---

## 🛠️ Installation & Running

### Prerequisites
You will need **Python 3.x** installed on your system.

### 1. Install Dependencies
The game only requires the `pygame` library. Install it via pip:
```bash
pip install pygame
```

### 2. Run the Game
Save the Python script as `lofi_shooter.py` and run it from your terminal:
```bash
python lofi_shooter.py
```

---

## 🎮 Controls

| Action | Input |
| :--- | :--- |
| **Move** | `W` `A` `S` `D` |
| **Aim** | `Mouse Cursor` |
| **Shoot** | `Left Mouse Click` (Hold for auto-fire) |
| **Bullet-Time Shop** | Hold `E` (Click upgrades while holding) |
| **Start / Restart** | `Spacebar` (from the Main Menu) |

---

## 🧬 Gameplay Mechanics

### The Shop & Upgrades
While holding `E`, click on the upgrade cards to spend your hard-earned yellow coins. 
*   **Weapon Type:** Single Shot ➔ Double Parallel ➔ Triple Parallel 
*   **Bullet Piercing:** Bullets pass through 1, 2, or Infinite enemies.
*   **Weapon Spread:** Increases the amount of projectiles fired in a cone.
*   **HP Regen:** Passively restores your ship's hull over time.
*   **Deflect Chance:** Grants a % chance to completely ignore an incoming hit.
*   **Thorns / Spikes:** Deals massive continuous DPS to any enemy that touches you.

### Enemy Types
The enemy swarm is composed of 4 unique geometries, each requiring a different strategy:

*   🟥 **Type A (The Grunt):** Spawns moving in a random straight line. Very fast, but easy to dodge. Despawns if it hits the edge of the world.
*   🟧 **Type B (The Bomber):** Homes in directly on your ship. If it gets too close, it stops and violently explodes into 8 radial shrapnel bullets.
*   🟪 **Type C (The Tactician):** A highly intelligent ranged unit. It actively maintains an optimal distance, strafes around you, and will rapidly dodge your bullets if they get too close.
*   🟦 **Type D (The Carrier):** Orbits the player perfectly out of visual range. Every 7 seconds, it fires a hyper-fast, pink homing missile. Missiles have a wide turn radius—dodge them so they crash into the world boundary!

---

## 🧑‍💻 Customization (For Developers)

Want to tweak the game? Open `lofi_shooter.py` and modify the constants at the top of the file:
*   `FPS = 60` (Game speed and physics calculation rate)
*   `UNIT = 20` (Change this to scale the size of everything in the game)
*   `WORLD_W, WORLD_H` (Change the size of the enclosed arena)
*   `UPGRADES` dictionary (Tweak costs, max levels, and starting stats)

---

### License
This project is open-source and available under the MIT License. 
Feel free to fork, modify, and use the code to learn Pygame!
