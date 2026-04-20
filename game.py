import pygame
import math
import random
import sys

pygame.init()

# --- Configuration ---
WIDTH, HEIGHT = 1000, 800
FPS = 60
UNIT = 20  # 1 game unit = 20 pixels
WORLD_W, WORLD_H = 200 * UNIT, 200 * UNIT

# Colors
BG_COLOR = (20, 20, 25)
GRID_COLOR = (40, 40, 50)
PLAYER_COLOR = (0, 255, 150)
BULLET_COLOR = (255, 255, 0)
ENEMY_BULLET_COLOR = (255, 100, 0)
LASER_COLOR = (0, 255, 255)
XP_COLOR = (0, 150, 255)
COIN_COLOR = (255, 215, 0)
FLASH_COLOR = (255, 255, 255)

# Upgrades Setup
# W1: Base(1) -> Double(2) -> Triple(3) -> Laser Pulse(4) -> Continuous Laser(5)
# W2: Pen 0(0) -> Pen 1(1) -> Pen 2(2) -> Infinite Pen(3)
# W3: 1 Spread(0) -> 3 Spread(1) -> 5 Spread(2) -> 7 Spread(3)
# A1: Regen 0 -> 0.5/s -> 1.0/s -> 2.0/s
# A2: Deflect 0% -> 25% -> 40% -> 50%
# A3: Spikes 0 -> 1 DPS -> 3 DPS -> 5 DPS
UPGRADES = {
    "W1": {"name": "Weapon 1: Type", "costs": [10, 30, 70, 150], "max": 5, "start": 1},
    "W2": {"name": "Weapon 2: Piercing", "costs":[20, 50, 100], "max": 3, "start": 0},
    "W3": {"name": "Weapon 3: Spread", "costs":[20, 50, 100], "max": 3, "start": 0},
    "A1": {"name": "Armor 1: HP Regen", "costs":[15, 40, 80], "max": 3, "start": 0},
    "A2": {"name": "Armor 2: Deflect", "costs": [15, 40, 80], "max": 3, "start": 0},
    "A3": {"name": "Armor 3: Spikes", "costs": [15, 40, 80], "max": 3, "start": 0},
}

# --- Utility Functions ---
def dist(p1, p2):
    return math.hypot(p1[0] - p2[0], p1[1] - p2[1])

def normalize(vx, vy):
    m = math.hypot(vx, vy)
    return (vx / m, vy / m) if m != 0 else (0, 0)

# --- Classes ---
class Player:
    def __init__(self):
        self.x, self.y = WORLD_W / 2, WORLD_H / 2
        self.radius = 0.5 * UNIT
        self.speed = 10 * UNIT
        self.max_hp = 10.0
        self.hp = 10.0
        
        self.xp = 0
        self.level = 1
        self.coins = 1000
        
        # Stats
        self.base_firerate = 1.0 # Hz
        
        # Upgrade Levels
        self.upgrades = {k: v["start"] for k, v in UPGRADES.items()}
        
        self.shoot_cooldown = 0
        self.invuln_timer = 0

    def next_level_xp(self):
        return int(10 * (1.5 ** (self.level - 1)))

    def add_xp(self, amount):
        self.xp += amount
        while self.xp >= self.next_level_xp():
            self.xp -= self.next_level_xp()
            self.level += 1
            self.max_hp += 2.0
            self.hp = self.max_hp
            self.base_firerate += 0.2

    def get_firerate(self):
        return self.base_firerate

    def get_regen(self):
        levels =[0, 0.5, 1.0, 2.0]
        return levels[self.upgrades["A1"]]

    def get_deflect_chance(self):
        levels =[0.0, 0.25, 0.40, 0.50]
        return levels[self.upgrades["A2"]]

    def get_spikes_dps(self):
        levels = [0, 1, 3, 5]
        return levels[self.upgrades["A3"]]

    def take_damage(self, amount, discrete=True):
        if discrete and random.random() < self.get_deflect_chance():
            return # Deflected
        self.hp -= amount
        if self.hp < 0: self.hp = 0

    def update(self, dt, keys):
        # Movement
        vx, vy = 0, 0
        if keys[pygame.K_w]: vy -= 1
        if keys[pygame.K_s]: vy += 1
        if keys[pygame.K_a]: vx -= 1
        if keys[pygame.K_d]: vx += 1
        vx, vy = normalize(vx, vy)
        
        self.x += vx * self.speed * dt
        self.y += vy * self.speed * dt
        
        # Clamp to world
        self.x = max(self.radius, min(WORLD_W - self.radius, self.x))
        self.y = max(self.radius, min(WORLD_H - self.radius, self.y))
        
        # Cooldowns and Regen
        if self.shoot_cooldown > 0:
            self.shoot_cooldown -= dt
            
        regen = self.get_regen()
        if regen > 0 and self.hp < self.max_hp:
            self.hp = min(self.max_hp, self.hp + regen * dt)

    def draw(self, surface, cam_x, cam_y, mouse_x, mouse_y):
        sx, sy = self.x - cam_x, self.y - cam_y
        angle = math.atan2(mouse_y - sy, mouse_x - sx)
        
        # Calculate triangle points
        pts =[
            (sx + math.cos(angle) * UNIT, sy + math.sin(angle) * UNIT),
            (sx + math.cos(angle + 2.5) * UNIT*0.8, sy + math.sin(angle + 2.5) * UNIT*0.8),
            (sx + math.cos(angle - 2.5) * UNIT*0.8, sy + math.sin(angle - 2.5) * UNIT*0.8)
        ]
        pygame.draw.polygon(surface, PLAYER_COLOR, pts)

class Projectile:
    def __init__(self, x, y, vx, vy, is_player, damage, pen):
        self.x, self.y = x, y
        self.vx, self.vy = vx, vy
        self.is_player = is_player
        self.damage = damage
        self.pen = pen # -1 for infinite
        self.radius = 4
        self.life = 3.0
        self.dead = False
        self.hit_enemies = set()

    def update(self, dt):
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.life -= dt
        if self.life <= 0 or not (0 <= self.x <= WORLD_W and 0 <= self.y <= WORLD_H):
            self.dead = True

    def draw(self, surface, cam_x, cam_y):
        color = BULLET_COLOR if self.is_player else ENEMY_BULLET_COLOR
        pygame.draw.circle(surface, color, (int(self.x - cam_x), int(self.y - cam_y)), self.radius)

class LaserEffect:
    def __init__(self, x1, y1, x2, y2, duration):
        self.x1, self.y1 = x1, y1
        self.x2, self.y2 = x2, y2
        self.life = duration
        self.max_life = duration

    def draw(self, surface, cam_x, cam_y):
        alpha = max(0, int(255 * (self.life / self.max_life)))
        if alpha > 0:
            surf = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            pygame.draw.line(surf, (*LASER_COLOR, alpha), (self.x1 - cam_x, self.y1 - cam_y), (self.x2 - cam_x, self.y2 - cam_y), 5)
            surface.blit(surf, (0, 0))

class Drop:
    def __init__(self, x, y, type_):
        self.x, self.y = x, y
        self.type = type_ # "xp" or "coin"
        self.radius = 6

    def draw(self, surface, cam_x, cam_y):
        sx, sy = int(self.x - cam_x), int(self.y - cam_y)
        if self.type == "xp":
            pygame.draw.rect(surface, XP_COLOR, (sx-4, sy-4, 8, 8))
        else:
            pygame.draw.circle(surface, COIN_COLOR, (sx, sy), 6)

class Enemy:
    def __init__(self, x, y, e_type, diff_mult):
        self.x, self.y = x, y
        self.type = e_type
        self.radius = UNIT * 0.6
        self.flash_timer = 0
        self.dead = False
        self.timer = 0
        
        if e_type == 'A':
            self.max_hp = 3 * diff_mult
            self.speed = 6 * UNIT * (1 + diff_mult * 0.2)
            self.color = (200, 50, 50)
            angle = random.uniform(0, math.pi * 2)
            self.vx, self.vy = math.cos(angle)*self.speed, math.sin(angle)*self.speed
        elif e_type == 'B':
            self.max_hp = 4 * diff_mult
            self.speed = 7 * UNIT * (1 + diff_mult * 0.2)
            self.color = (255, 150, 0)
        elif e_type == 'C':
            self.max_hp = 5 * diff_mult
            self.speed = 4 * UNIT * (1 + diff_mult * 0.2)
            self.color = (150, 50, 255)
        elif e_type == 'D':
            self.max_hp = 8 * diff_mult
            self.speed = 3 * UNIT * (1 + diff_mult * 0.2)
            self.color = (50, 200, 255)
            self.orbit_angle = random.uniform(0, math.pi * 2)
        elif e_type == 'Missile':
            self.max_hp = 1
            self.speed = 10 * UNIT
            self.color = (255, 50, 255)
            self.radius = UNIT * 0.3
            
        self.hp = self.max_hp

    def hit(self, amount):
        self.hp -= amount
        self.flash_timer = 0.1
        if self.hp <= 0:
            self.dead = True

    def update(self, dt, player, bullets, game_state):
        if self.flash_timer > 0: self.flash_timer -= dt
        self.timer += dt
        
        px, py = player.x, player.y
        dist_to_p = dist((self.x, self.y), (px, py))
        
        if self.type == 'A':
            self.x += self.vx * dt
            self.y += self.vy * dt
            if not (0 <= self.x <= WORLD_W and 0 <= self.y <= WORLD_H):
                self.dead = True # despawn
                
        elif self.type == 'B' or self.type == 'Missile':
            vx, vy = normalize(px - self.x, py - self.y)
            self.x += vx * self.speed * dt
            self.y += vy * self.speed * dt
            
            if self.type == 'B' and dist_to_p < 1.5 * UNIT:
                # Explode 8 bullets
                for i in range(8):
                    angle = i * (math.pi / 4)
                    bx, by = math.cos(angle)*10*UNIT, math.sin(angle)*10*UNIT
                    bullets.append(Projectile(self.x, self.y, bx, by, False, 1.0, 0))
                self.dead = True
                
            if self.type == 'Missile' and dist_to_p < self.radius + player.radius:
                player.take_damage(1.0, True)
                self.dead = True
                
        elif self.type == 'C':
            # Keep distance
            vx, vy = normalize(px - self.x, py - self.y)
            if dist_to_p > 15 * UNIT:
                self.x += vx * self.speed * dt
                self.y += vy * self.speed * dt
            elif dist_to_p < 10 * UNIT:
                self.x -= vx * self.speed * dt
                self.y -= vy * self.speed * dt
                
            # Dodge closest bullet
            closest_b, closest_d = None, 10 * UNIT
            for b in bullets:
                if b.is_player:
                    d = dist((self.x, self.y), (b.x, b.y))
                    if d < closest_d:
                        closest_d = d
                        closest_b = b
            if closest_b:
                # Move perpendicular
                pvx, pvy = normalize(closest_b.vy, -closest_b.vx)
                self.x += pvx * self.speed * 0.8 * dt
                self.y += pvy * self.speed * 0.8 * dt
                
            # Shoot every 2s
            if self.timer > 2.0:
                self.timer = 0
                bx, by = vx * 12 * UNIT, vy * 12 * UNIT
                bullets.append(Projectile(self.x, self.y, bx, by, False, 1.0, 0))
                
        elif self.type == 'D':
            self.orbit_angle += 0.5 * dt
            tx = px + math.cos(self.orbit_angle) * 15 * UNIT
            ty = py + math.sin(self.orbit_angle) * 15 * UNIT
            vx, vy = normalize(tx - self.x, ty - self.y)
            self.x += vx * self.speed * dt
            self.y += vy * self.speed * dt
            
            if self.timer > 5.0:
                self.timer = 0
                game_state["enemies"].append(Enemy(self.x, self.y, 'Missile', 1.0))

        # Clamp
        self.x = max(0, min(WORLD_W, self.x))
        self.y = max(0, min(WORLD_H, self.y))

    def draw(self, surface, cam_x, cam_y):
        sx, sy = int(self.x - cam_x), int(self.y - cam_y)
        color = FLASH_COLOR if self.flash_timer > 0 else self.color
        
        if self.type == 'A':
            pygame.draw.rect(surface, color, (sx-int(self.radius), sy-int(self.radius), int(self.radius*2), int(self.radius*2)))
        elif self.type == 'B':
            pygame.draw.polygon(surface, color,[(sx, sy-self.radius), (sx-self.radius, sy+self.radius), (sx+self.radius, sy+self.radius)])
        elif self.type == 'C':
            pygame.draw.circle(surface, color, (sx, sy), int(self.radius))
            pygame.draw.circle(surface, (255,255,255), (sx, sy), int(self.radius*0.5))
        elif self.type == 'D':
            pygame.draw.polygon(surface, color,[(sx-self.radius, sy), (sx, sy-self.radius), (sx+self.radius, sy), (sx, sy+self.radius)])
        elif self.type == 'Missile':
            pygame.draw.circle(surface, color, (sx, sy), int(self.radius))

# --- Main Game Manager ---
class Game:
    def __init__(self):
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("Lo-Fi Shooter")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont(None, 24)
        self.large_font = pygame.font.SysFont(None, 48)
        
        self.player = Player()
        self.enemies = []
        self.bullets = []
        self.drops =[]
        self.lasers =[]
        
        self.game_time = 0
        self.spawn_timer = 0
        self.state = "PLAYING" # PLAYING, SHOP, GAMEOVER
        
    def raycast(self, x, y, dx, dy, max_pen):
        # Ray-circle intersection for enemies
        hits =[]
        for e in self.enemies:
            vx, vy = e.x - x, e.y - y
            proj = vx * dx + vy * dy
            if proj > 0:
                closest_x = x + dx * proj
                closest_y = y + dy * proj
                dist_sq = (closest_x - e.x)**2 + (closest_y - e.y)**2
                r_sq = e.radius**2
                if dist_sq <= r_sq:
                    d = math.sqrt(r_sq - dist_sq)
                    t = proj - d
                    if t >= 0:
                        hits.append((t, e))
                        
        hits.sort(key=lambda item: item[0])
        pen_count = max_pen if max_pen != -1 else len(hits)
        
        hit_enemies =[]
        end_t = 800 * UNIT # max range
        for i in range(min(len(hits), pen_count + 1)):
            if i <= pen_count - 1 or max_pen == -1:
                hit_enemies.append(hits[i][1])
            if i == pen_count and max_pen != -1:
                end_t = hits[i][0] # Stop visually at the one it fails to pierce
                break
                
        return hit_enemies, x + dx * end_t, y + dy * end_t

    def player_shoot(self, mx, my, cam_x, cam_y, is_click_held):
        if self.player.shoot_cooldown > 0:
            return

        w1 = self.player.upgrades["W1"]
        w2 = self.player.upgrades["W2"]
        w3 = self.player.upgrades["W3"]
        
        # Pen mapping: 0, 1, 2, Infinite(-1)
        pen = -1 if w2 == 3 else w2
        
        # Spread mapping
        spreads =[1, 3, 5, 7]
        num_spread = spreads[w3]
        spread_angle = math.radians(15)
        
        px, py = self.player.x, self.player.y
        base_angle = math.atan2(my + cam_y - py, mx + cam_x - px)
        
        fired = False
        
        if w1 <= 3:
            # Projectiles
            speed = 20 * UNIT
            offsets = [0]
            if w1 == 2: offsets = [-0.3, 0.3]
            elif w1 == 3: offsets =[-0.4, 0, 0.4]
            
            for i in range(num_spread):
                angle = base_angle + (i - num_spread//2) * spread_angle
                dx, dy = math.cos(angle), math.sin(angle)
                right_x, right_y = math.cos(angle + math.pi/2), math.sin(angle + math.pi/2)
                
                for off in offsets:
                    spawn_x = px + right_x * off * UNIT
                    spawn_y = py + right_y * off * UNIT
                    self.bullets.append(Projectile(spawn_x, spawn_y, dx * speed, dy * speed, True, 1.0, pen))
            fired = True
            
        elif w1 == 4 or w1 == 5:
            # Lasers
            for i in range(num_spread):
                angle = base_angle + (i - num_spread//2) * spread_angle
                dx, dy = math.cos(angle), math.sin(angle)
                hit_enemies, end_x, end_y = self.raycast(px, py, dx, dy, pen)
                
                if w1 == 4: # Pulse
                    for e in hit_enemies: e.hit(1.0)
                    self.lasers.append(LaserEffect(px, py, end_x, end_y, 0.1))
                    fired = True
                elif w1 == 5: # Continuous
                    # Deals DPS equivalent to firerate
                    dps = 1.0 * self.player.get_firerate()
                    for e in hit_enemies: e.hit(dps * (1/FPS))
                    self.lasers.append(LaserEffect(px, py, end_x, end_y, 0.02)) # very short life
                    # Continuous doesn't trigger base cooldown the same way, we just draw every frame
                    
        if w1 == 5:
            self.player.shoot_cooldown = 0
        elif fired:
            self.player.shoot_cooldown = 1.0 / self.player.get_firerate()

    def update(self):
        dt = 1.0 / FPS
        self.game_time += dt
        
        keys = pygame.key.get_pressed()
        mouse_x, mouse_y = pygame.mouse.get_pos()
        click = pygame.mouse.get_pressed()[0]
        
        # --- Upgrades Shop Toggle ---
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_e:
                    if self.state == "PLAYING": self.state = "SHOP"
                    elif self.state == "SHOP": self.state = "PLAYING"
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if self.state == "SHOP":
                    self.handle_shop_click(mouse_x, mouse_y)
                elif self.state == "GAMEOVER":
                    self.__init__() # Restart
        
        if self.state != "PLAYING":
            return
            
        cam_x, cam_y = self.player.x - WIDTH/2, self.player.y - HEIGHT/2

        self.player.update(dt, keys)
        if click:
            self.player_shoot(mouse_x, mouse_y, cam_x, cam_y, click)
            
        # --- Spawning Logic ---
        difficulty = self.game_time / 60.0
        cap = int(10 + difficulty * 20)
        
        self.spawn_timer -= dt
        spawn_rate = max(0.1, 1.0 - difficulty * 0.4)
        
        if self.spawn_timer <= 0 and len(self.enemies) < cap:
            self.spawn_timer = spawn_rate
            
            # Choose type
            wA = max(10, 100 - difficulty * 20)
            wB = difficulty * 20
            wC = max(0, difficulty * 15 - 5)
            wD = max(0, difficulty * 10 - 10)
            types, weights = ['A','B','C','D'],[wA, wB, wC, wD]
            e_type = random.choices(types, weights=weights)[0]
            
            # Random position > 20 units away
            while True:
                sx = random.uniform(0, WORLD_W)
                sy = random.uniform(0, WORLD_H)
                if dist((sx, sy), (self.player.x, self.player.y)) > 20 * UNIT:
                    self.enemies.append(Enemy(sx, sy, e_type, 1.0 + difficulty))
                    break

        # --- Update Entities ---
        game_state = {"enemies": self.enemies}
        
        for e in self.enemies:
            e.update(dt, self.player, self.bullets, game_state)
            
            # Collision with Player
            if dist((e.x, e.y), (self.player.x, self.player.y)) < e.radius + self.player.radius:
                # Type A discrete/DPS check. Prompt: "Type A: 1 damage per second on collision"
                # For simplicity, deal DPS on contact for all standard enemies.
                self.player.take_damage(1.0 * dt, discrete=False)
                # Spikes damage
                spikes_dps = self.player.get_spikes_dps()
                if spikes_dps > 0:
                    e.hit(spikes_dps * dt)

        for b in self.bullets:
            b.update(dt)
            if b.is_player:
                for e in self.enemies:
                    if e not in b.hit_enemies and dist((b.x, b.y), (e.x, e.y)) < e.radius + b.radius:
                        e.hit(b.damage)
                        b.hit_enemies.add(e)
                        if b.pen != -1 and len(b.hit_enemies) > b.pen:
                            b.dead = True
                            break
            else:
                if dist((b.x, b.y), (self.player.x, self.player.y)) < self.player.radius + b.radius:
                    self.player.take_damage(b.damage, discrete=True)
                    b.dead = True

        for d in self.drops:
            # Magnet
            if dist((d.x, d.y), (self.player.x, self.player.y)) < 5 * UNIT:
                vx, vy = normalize(self.player.x - d.x, self.player.y - d.y)
                d.x += vx * 15 * UNIT * dt
                d.y += vy * 15 * UNIT * dt
            
            if dist((d.x, d.y), (self.player.x, self.player.y)) < self.player.radius + d.radius:
                if d.type == "xp": self.player.add_xp(1)
                elif d.type == "coin": self.player.coins += 1
                d.dead = True

        for l in self.lasers:
            l.life -= dt

        # --- Cleanup ---
        for e in[e for e in self.enemies if e.dead]:
            # Drops
            self.drops.append(Drop(e.x, e.y, "xp"))
            if random.random() < 0.3:
                self.drops.append(Drop(e.x + random.uniform(-5,5), e.y + random.uniform(-5,5), "coin"))
        
        self.enemies =[e for e in self.enemies if not e.dead]
        self.bullets =[b for b in self.bullets if not b.dead]
        self.drops =[d for d in self.drops if not getattr(d, 'dead', False)]
        self.lasers =[l for l in self.lasers if l.life > 0]
        
        if self.player.hp <= 0:
            self.state = "GAMEOVER"

    def draw(self):
        self.screen.fill(BG_COLOR)
        
        cam_x, cam_y = self.player.x - WIDTH/2, self.player.y - HEIGHT/2
        
        # Grid
        for x in range(0, int(WORLD_W), UNIT * 5):
            sx = x - cam_x
            if 0 <= sx <= WIDTH: pygame.draw.line(self.screen, GRID_COLOR, (sx, 0), (sx, HEIGHT))
        for y in range(0, int(WORLD_H), UNIT * 5):
            sy = y - cam_y
            if 0 <= sy <= HEIGHT: pygame.draw.line(self.screen, GRID_COLOR, (0, sy), (WIDTH, sy))
            
        # Entities
        for d in self.drops: d.draw(self.screen, cam_x, cam_y)
        for e in self.enemies: e.draw(self.screen, cam_x, cam_y)
        for b in self.bullets: b.draw(self.screen, cam_x, cam_y)
        for l in self.lasers: l.draw(self.screen, cam_x, cam_y)
        
        if self.state != "GAMEOVER":
            mouse_x, mouse_y = pygame.mouse.get_pos()
            self.player.draw(self.screen, cam_x, cam_y, mouse_x, mouse_y)
            
        # UI Overlay
        ui_y = 10
        self.draw_text(f"HP: {self.player.hp:.1f} / {self.player.max_hp:.1f}", 10, ui_y, (0, 255, 100))
        ui_y += 25
        self.draw_text(f"Level: {self.player.level}  (XP: {self.player.xp}/{self.player.next_level_xp()})", 10, ui_y, XP_COLOR)
        ui_y += 25
        self.draw_text(f"Coins: {self.player.coins}", 10, ui_y, COIN_COLOR)
        ui_y += 25
        self.draw_text(f"Time: {int(self.game_time)}s", 10, ui_y, (200, 200, 200))
        
        self.draw_text("Press 'E' to open Upgrades Shop", WIDTH - 250, 10, (255, 255, 255))
        
        if self.state == "SHOP":
            self.draw_shop()
        elif self.state == "GAMEOVER":
            s = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            s.fill((0, 0, 0, 150))
            self.screen.blit(s, (0, 0))
            t = self.large_font.render("GAME OVER", True, (255, 50, 50))
            self.screen.blit(t, (WIDTH/2 - t.get_width()/2, HEIGHT/2 - 50))
            t2 = self.font.render("Click to Restart", True, (255, 255, 255))
            self.screen.blit(t2, (WIDTH/2 - t2.get_width()/2, HEIGHT/2 + 20))

        pygame.display.flip()

    def draw_text(self, text, x, y, color):
        img = self.font.render(text, True, color)
        self.screen.blit(img, (x, y))

    def draw_shop(self):
        s = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        s.fill((0, 0, 0, 200))
        self.screen.blit(s, (0, 0))
        
        title = self.large_font.render("UPGRADES SHOP", True, (255, 255, 255))
        self.screen.blit(title, (WIDTH/2 - title.get_width()/2, 50))
        self.draw_text(f"Your Coins: {self.player.coins}", WIDTH/2 - 50, 100, COIN_COLOR)
        
        self.shop_rects = {}
        
        x_start, y_start = 100, 150
        y_step = 80
        
        for i, (k, v) in enumerate(UPGRADES.items()):
            col = i % 2
            row = i // 2
            
            x = x_start + col * 420
            y = y_start + row * y_step
            
            lvl = self.player.upgrades[k]
            rect = pygame.Rect(x, y, 380, 60)
            pygame.draw.rect(self.screen, (50, 50, 70), rect, border_radius=5)
            
            name_txt = f"{v['name']} (Lvl {lvl}/{v['max']})"
            self.draw_text(name_txt, x + 10, y + 10, (255, 255, 255))
            
            if lvl < v['max']:
                # Cost is offset by the 'start' index logic. 
                # e.g. W1 starts at 1, max 5, costs len 4. index = lvl - 1
                cost_idx = lvl - v['start']
                cost = v['costs'][cost_idx]
                color = (0, 255, 0) if self.player.coins >= cost else (255, 0, 0)
                self.draw_text(f"Cost: {cost} Coins", x + 10, y + 35, color)
                self.shop_rects[k] = (rect, cost)
            else:
                self.draw_text("MAXED OUT", x + 10, y + 35, (100, 100, 100))

    def handle_shop_click(self, mx, my):
        for k, (rect, cost) in self.shop_rects.items():
            if rect.collidepoint(mx, my):
                if self.player.coins >= cost:
                    self.player.coins -= cost
                    self.player.upgrades[k] += 1
                break

    def run(self):
        while True:
            self.update()
            self.draw()
            self.clock.tick(FPS)

if __name__ == "__main__":
    Game().run()