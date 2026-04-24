# 📜 Changelog | Bullet Hell Minute v2

## The Refactoring & Asteroid Update
**🛠️ Under the Hood**
*   **Major Architecture Overhaul:** Completely refactored the monolithic `Enemy` class into a robust Object-Oriented framework with a `BaseEnemy` class and dedicated subclasses (`ChaserEnemy`, `SniperEnemy`, `SplitterLargeEnemy`, etc.). Code is now highly modular and documented.

**✨ New Features & Mechanics**
*   **New Enemy - Splitter:** Added asteroid-like enemies that drift in random directions. When destroyed, they violently fracture into 4 smaller, faster fragments. They also fire a 5-bullet spread.
*   **New Enemy - Sweeper:** Replaced Flankers with Sweepers that maintain a specific distance and rapid-fire bullets in a sweeping arc pattern.
*   **Instant XP:** XP is now injected directly into the player upon killing an enemy. XP square drops were removed to reduce visual clutter.

**🎨 Visuals & UI**
*   **Font Upgrade:** Replaced the monospace Courier font with a clean, modern Sans-Serif font stack (`Segoe UI`, `Helvetica`, `Arial`).
*   **Color Clarity:** Coins are now strictly pure Yellow `(255, 255, 0)`. Removed yellow coloring from all enemies to ensure loot is instantly identifiable.

**⚖️ Balancing**
*   Removed the active player shield to emphasize raw dodging mechanics.
*   Reduced the spawn weight and base speed of standard Kamikaze Chasers to balance the screen-fill of the new Splitter and Sweeper bullets.

---

## The Phantom & Shield Update
**✨ New Features & Mechanics**
*   **Active Deflector Shield:** Added a player shield (Hold `SPACEBAR`) that absorbs bullets and creates a directional glowing arc where impacted. Drains energy at the same rate as the laser.
*   **New Enemy - Phantom:** Introduced a rare, high-speed ambusher that spawns late-game. It rushes in, freezes to fire a rapid volley, and instantly teleports to a new bearing.
*   **Downgrade System:** Players can now Right-Click upgrades in the Bullet-Time shop to downgrade them, receiving a 100% refund of the previous level's cost. Removed `max_slots` limitation.

**⚖️ Balancing**
*   **Stat Curve Overhaul:** Greatly increased base stats for a much more forgiving early game. 
*   **Nerfed Upgrades:** Upgrades now cap at providing a maximum +50% boost to base stats. Uses a diminishing returns curve where early levels provide the biggest jumps.
*   Upgrading Hull no longer heals the player.
*   Buffed the Coin Magnet radius and pull speed.

**🎨 Visuals & UI**
*   **Immersive Main Menu:** Added a continuously scrolling toroidal background grid and dummy enemies floating around the title screen. Added on-screen control instructions.

---

## The Fibonacci & Burst-Fire Update
**✨ New Features & Mechanics**
*   **Fibonacci Economy:** Replaced the multiplier-based economy with a strict Fibonacci sequence cost curve (1, 2, 3, 5, 8, 13...).
*   **Burst Fire AI:** Ranged enemies (Orbiters, Diagonals, Artillery, Miners) now utilize terrifying rapid burst-fire clusters instead of shooting single continuous bullets.
*   **Stylistic Sniper:** Snipers now feature a distinct 3-phase attack: Aim -> Telegraph a map-wide red laser (deals no damage) -> Fire full-power thick beam.

**⚖️ Balancing**
*   **Linear Difficulty:** Reverted difficulty scaling from quadratic back to linear, but it now directly scales bullet damage and enemy speed rather than exponential time-warping.
*   **Early Game Mercy:** Strictly constrained enemy spawn caps in the first 10 seconds of a run to allow players to set up.
*   Decreased collision damage, but increased enemy bullet damage to prioritize dodging over ramming avoidance.

---

## The "Bullet Hell Minute" Update
**✨ New Features & Mechanics**
*   **Game Renamed:** Officially dubbed "Bullet Hell Minute".
*   **Homing Missiles Returned:** Brought back the `Launcher` enemy. Missiles actively track the player but can be melted mid-air by the player's laser. If dodged long enough, they fizzle out into smoke.
*   **Explosive Collisions:** Crashing into an enemy now detonates them instantly. They yield *no XP and no coins* if they die this way.
*   **Smart Kiting:** Ranged enemies now actively backpedal to maintain their optimal firing range, while melee enemies aggressively kamikaze.

**⚖️ Balancing**
*   **I-Frame Bypass:** Enemy bullets completely ignore player invulnerability frames. Getting hit by a spread shotgun blast hits multiple times instantly.
*   Loot (Coins) only drops if the player explicitly killed the enemy with the laser.
*   Coin magnet was heavily nerfed.
*   Enemy base HP reduced across the board, offset by extreme bullet density.

---

## The Sniper & Diminishing Returns Update
**🛠️ Under the Hood**
*   **True Delta Time (dt):** Fixed a critical bug where FPS drops would slow down game time. Game simulation is now completely frame-rate independent.

**✨ New Features & Mechanics**
*   **New Enemy - Sniper:** Replaced Attractor/Repulser with Snipers. Projects a red lock-on laser that zaps player HP if stood inside.
*   **New Enemy - Emitter:** Renamed Booster to Emitter. Periodically releases expanding AoE energy pulses that deal damage.
*   **Directional Spawning:** Enemies now dynamically spawn just outside the visible area *in the direction the player is traveling*, forcing confrontation.

**⚖️ Balancing**
*   **Diminishing Upgrades:** Split upgrades into 10 smaller levels. Early levels give massive bonuses, later levels taper off via an asymptotic curve. Maxing the Laser widens the beam significantly but drastically spikes energy drain.
*   Regeneration and Max Regen heavily nerfed.
*   I-Frames drastically shortened.
*   Player laser range is now strictly constrained to the edge of the visible screen.

---

## The Chunk Optimization & Artillery Update
**🛠️ Under the Hood**
*   **Toroidal Spatial Partitioning:** Upgraded the collision detection to use chunked spatial partitioning that natively calculates Toroidal (wrap-around) geometry. O(1) adjacency checks vastly increased FPS limits.
*   Added a relaxed hardcap (150) to max enemies on screen to protect performance.

**✨ New Features & Mechanics**
*   **Ramming Mechanics:** Intersecting with an enemy now damages the player, but *also* damages the enemy.
*   **New Enemy - Artillery:** Launches overhead ballistic shells that project a pulsing red warning zone on the ground before exploding into 8-way shrapnel.
*   **New Enemy - Miner:** Actively flees the player while dropping proximity mines.

---

## The Toroidal Map Update
**✨ New Features & Mechanics**
*   **Seamless Toroidal Map:** Removed the map boundaries. The entire map now wraps around seamlessly on the X and Y axes for both the player and enemies.
*   **Audio Engine:** Implemented an optional `.mp3` sound engine with support for `shoot`, `hit`, `coin`, `xp`, `laser`, and `bgm` files.
*   **Shield Weakness:** The Shield Enemy's deflector bubble now takes full damage if the player physically flies *inside* the bubble to shoot them.
*   **New Enemies:** Added Attractor (pulls player), Repulser (pushes player), and Laser (locks on and fires thick red beams).

**🎨 Visuals & UI**
*   Added a real-time Minimap in the top right corner.
*   Brought back the high-performance circular Race Watch timer.
*   Drastically increased overall game speed and energy regeneration rates for a more aggressive pacing.

---

## The Component Booster Update
**✨ New Features & Mechanics**
*   **Laser Only Combat:** Removed standard bullets, spread, and piercing. The player's only weapon is a continuous ray-cast Laser.
*   **Energy System:** Firing the laser rapidly drains Energy. If empty, the beam becomes thin and weak until allowed to recharge.
*   **Bullet-Time Shop Revamp:** Replaced old upgrades with Hardware Components (Laser, Reactor, Hull, Engine, Regen). Upgrades visually equip into slots hovering around the player ship in real-time.
*   **Advanced AI:** Added complex swarming behaviors including encirclement, flanking, and interception (aiming ahead of player trajectory).

**🎨 Visuals & UI**
*   Added minimalist line-bar HUD in the bottom right corner for HP/Energy.
*   Added Parallax scrolling background layers and a screen Vignette.
*   Camera shake tuned down slightly for visibility.

---

## The Industrial Cube Core Update
**✨ New Features & Mechanics**
*   **Combat Shift:** Left-click fires individual bullets, holding Left-click charges the Epic Laser.
*   **New Enemies:** Added the Splitter Cargo ('E') which absorbs damage and breaks into Micro-bots ('e').
*   Added map hazards: Stray industrial defense lasers that occasionally sweep across the map.

**🛠️ Under the Hood**
*   Shrunk the map from 200x200 to 100x100 to drastically increase combat density.
*   Added the first iteration of basic chunked spatial partitioning for bullet collisions.

**🎨 Visuals & UI**
*   Theme shift to "Cube Robot / Industrial". Colors shifted to dark grays, teals, and neons. Background changed to a riveted industrial grid.
*   Implemented a circular, rapidly spinning "Race Watch" UI around the central clock.

---

## The Bullet Time & Meta-Progression Update
**✨ New Features & Mechanics**
*   **Bullet Time Shop:** Holding 'E' now slows time down to 0.1x (Bullet Time) instead of pausing, allowing the player to buy upgrades while dodging.
*   **Rogue-lite Meta-Progression:** Dying resets the round, but collected coins and upgrade levels permanently persist across runs.
*   **Run Pacing:** Tuned the difficulty scaling so games last an intense 20-60 seconds instead of indefinite survival.

**🎨 Visuals & UI**
*   Added massive translucent game timer to the center of the screen.
*   Added violent Screen Shake and impact particle bursts.

**⚖️ Balancing**
*   Vastly increased base movement speeds for players, enemies, and bullets.
*   Ranged enemies now actively dart to maintain optimal distance.
*   Homing missiles made harder to turn and despawn if they hit map edges.
