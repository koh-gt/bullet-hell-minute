"""
BULLET HELL MINUTE
A fast-paced, toroidal 2D shooter.
Maintainable Modular Edition.
"""

import pygame
import math
import random
import sys
import os

pygame.init()
pygame.mixer.init()

# ==========================================
# SECTION 1: CONFIGURATION & CONSTANTS
# ==========================================
WIDTH, HEIGHT = 1000, 800
FPS = 60
UNIT = 20
WORLD_W, WORLD_H = 100 * UNIT, 100 * UNIT
MAX_ENEMIES = 150

# Theme Colors
BG_COLOR = (12, 14, 18)
PLAYER_COLOR = (0, 255, 200)
LASER_COLOR = (0, 255, 255)
WEAK_LASER_COLOR = (0, 100, 100)
ENEMY_LASER_COLOR = (255, 50, 50)
COIN_COLOR = (255, 255, 0) # Pure Yellow (Strictly reserved for coins)
HP_COLOR = (50, 255, 100)
XP_UI_COLOR = (0, 180, 255)

# Upgrades System
COMPONENTS = {
    "Laser": {"name": "Laser Emitter", "desc": "Wider Laser, Higher DPS, High Drain"},
    "Reactor": {"name": "Reactor Core", "desc": "More Max Energy & Faster Regen"},
    "Hull": {"name": "Hull Plating", "desc": "Increases Max HP"},
    "Engine": {"name": "Thrusters", "desc": "Increases Movement Speed"},
    "Regen": {"name": "Nano-Repair", "desc": "Increases HP Regeneration"},
}

MAX_LEVEL = 10
FIB_COSTS =[1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144]

def get_upgrade_cost(lvl):
    """Returns cost for the given level based on the Fibonacci sequence."""
    return FIB_COSTS[lvl]


# ==========================================
# SECTION 2: UTILITIES & MATH (TOROIDAL)
# ==========================================
def shortest_dist_vec(p1, p2):
    """Calculates the shortest directional vector between two points on a wrapping map."""
    dx, dy = p1[0] - p2[0], p1[1] - p2[1]
    if dx > WORLD_W / 2: dx -= WORLD_W
    elif dx < -WORLD_W / 2: dx += WORLD_W
    if dy > WORLD_H / 2: dy -= WORLD_H
    elif dy < -WORLD_H / 2: dy += WORLD_H
    return dx, dy

def dist_sq_wrap(p1, p2):
    dx, dy = shortest_dist_vec(p1, p2)
    return dx**2 + dy**2

def dist_wrap(p1, p2):
    dx, dy = shortest_dist_vec(p1, p2)
    return math.hypot(dx, dy)

def normalize(vx, vy):
    m = math.hypot(vx, vy)
    return (vx / m, vy / m) if m != 0 else (0, 0)

def get_rel_pos(x, y, cam_x, cam_y):
    """Maps world coordinates to screen coordinates relative to the camera."""
    dx, dy = shortest_dist_vec((x, y), (cam_x, cam_y))
    return WIDTH/2 + dx, HEIGHT/2 + dy


# ==========================================
# SECTION 3: SPATIAL PARTITIONING
# ==========================================
class ToroidalChunkManager:
    """Optimizes proximity queries (O(N) vs O(N^2)) by chunking the wrapping map."""
    def __init__(self, cell_size):
        self.cell_size = cell_size
        self.cols = int(WORLD_W // cell_size) + 1
        self.rows = int(WORLD_H // cell_size) + 1
        self.chunks = {}

    def clear(self):
        self.chunks.clear()

    def add(self, entity):
        cx = int((entity.x % WORLD_W) // self.cell_size)
        cy = int((entity.y % WORLD_H) // self.cell_size)
        if (cx, cy) not in self.chunks: 
            self.chunks[(cx, cy)] = []
        self.chunks[(cx, cy)].append(entity)

    def get_nearby(self, x, y):
        cx = int((x % WORLD_W) // self.cell_size)
        cy = int((y % WORLD_H) // self.cell_size)
        nearby =[]
        for dx in [-1, 0, 1]:
            for dy in [-1, 0, 1]:
                nx, ny = (cx + dx) % self.cols, (cy + dy) % self.rows
                if (nx, ny) in self.chunks: 
                    nearby.extend(self.chunks[(nx, ny)])
        return nearby


# ==========================================
# SECTION 4: AUDIO & VFX
# ==========================================
class AudioManager:
    """Handles sound effects and soundtrack, ignoring missing files gracefully."""
    def __init__(self):
        self.sounds = {}
        for f in['shoot', 'hit', 'coin', 'xp', 'laser', 'explode']:
            if os.path.exists(f"{f}.mp3"): 
                self.sounds[f] = pygame.mixer.Sound(f"{f}.mp3")
        
        if os.path.exists("game.mp3"):
            pygame.mixer.music.load("game.mp3")
            pygame.mixer.music.play(-1)

    def play(self, name):
        if name in self.sounds and self.sounds[name].get_num_channels() < 4:
            self.sounds[name].play()

audio = AudioManager()

class Particle:
    def __init__(self, x, y, color, speed_mult=1.0, size=4):
        self.x, self.y = x, y
        angle = random.uniform(0, math.pi * 2)
        speed = random.uniform(5 * UNIT, 30 * UNIT) * speed_mult
        self.vx, self.vy = math.cos(angle) * speed, math.sin(angle) * speed
        self.life = random.uniform(0.1, 0.4)
        self.max_life = self.life
        self.color = color
        self.size = size

    def update(self, dt):
        self.x = (self.x + self.vx * dt) % WORLD_W
        self.y = (self.y + self.vy * dt) % WORLD_H
        self.life -= dt

    def draw(self, surface, cam_x, cam_y):
        if self.life > 0:
            alpha = max(0, int(255 * (self.life / self.max_life)))
            surf = pygame.Surface((self.size, self.size), pygame.SRCALPHA)
            surf.fill((*self.color[:3], alpha))
            sx, sy = get_rel_pos(self.x, self.y, cam_x, cam_y)
            surface.blit(surf, (int(sx), int(sy)))


# ==========================================
# SECTION 5: PLAYER
# ==========================================
class Player:
    def __init__(self):
        self.x, self.y = WORLD_W / 2, WORLD_H / 2
        self.radius = 0.6 * UNIT
        self.xp, self.level, self.coins = 0, 1, 0
        self.vx, self.vy = 0, 0
        self.comps = {k: 0 for k in COMPONENTS.keys()}
        self.equipped =[]
        self.invuln_timer = 0
        
        self.hp = self.get_max_hp()
        self.energy = self.get_max_energy()
        self.max_laser_dist = math.hypot(WIDTH, HEIGHT) / 2 + 50

    def dim_return(self, level, max_bonus):
        """Asymptotic diminishing returns curve for components."""
        return max_bonus * (1 - math.exp(-0.25 * level))

    def get_max_hp(self): return 20.0 * (1.0 + min(self.comps["Hull"], 10) * 0.05)
    def get_hp_regen(self): return 0.5 * (1.0 + min(self.comps["Regen"], 10) * 0.05)
    def get_max_energy(self): return 200.0 * (1.0 + min(self.comps["Reactor"], 10) * 0.05)
    def get_energy_regen(self): return 120.0 * (1.0 + min(self.comps["Reactor"], 10) * 0.05)
    def get_speed(self): return (40 * UNIT) * (1.0 + min(self.comps["Engine"], 10) * 0.05)
    def get_laser_dps(self): return 40.0 * (1.0 + min(self.comps["Laser"], 10) * 0.05)
    def get_laser_thickness(self): return int(6 * (1.0 + min(self.comps["Laser"], 10) * 0.05))
    def get_laser_drain(self): return 60.0 * (1.0 + min(self.comps["Laser"], 10) * 0.05)

    def next_level_xp(self): return int(10 * (1.3 ** (self.level - 1)))

    def add_xp(self, amount):
        self.xp += amount
        while self.xp >= self.next_level_xp():
            self.xp -= self.next_level_xp()
            self.level += 1
            audio.play('xp')
            ratio = self.hp / self.get_max_hp()
            self.hp = self.get_max_hp() * ratio

    def take_damage(self, amount, is_bullet=False):
        if not is_bullet and self.invuln_timer > 0: return False
        self.hp = max(0, self.hp - amount)
        if not is_bullet: self.invuln_timer = 0.05
        audio.play('hit')
        return True

    def update(self, dt, keys):
        vx, vy = 0, 0
        if keys[pygame.K_w]: vy -= 1
        if keys[pygame.K_s]: vy += 1
        if keys[pygame.K_a]: vx -= 1
        if keys[pygame.K_d]: vx += 1
        self.vx, self.vy = normalize(vx, vy)
        
        speed = self.get_speed()
        self.x = (self.x + self.vx * speed * dt) % WORLD_W
        self.y = (self.y + self.vy * speed * dt) % WORLD_H
        
        if self.invuln_timer > 0: self.invuln_timer -= dt
        if self.hp < self.get_max_hp():
            self.hp = min(self.get_max_hp(), self.hp + self.get_hp_regen() * dt)

    def draw(self, surface, cam_x, cam_y, mouse_x, mouse_y):
        sx, sy = get_rel_pos(self.x, self.y, cam_x, cam_y)
        angle = math.atan2(mouse_y - sy, mouse_x - sx)
        pts =[
            (sx + math.cos(angle) * UNIT*1.3, sy + math.sin(angle) * UNIT*1.3),
            (sx + math.cos(angle + 2.6) * UNIT*1.1, sy + math.sin(angle + 2.6) * UNIT*1.1),
            (sx + math.cos(angle - 2.6) * UNIT*1.1, sy + math.sin(angle - 2.6) * UNIT*1.1)
        ]
        color = (255, 255, 255) if self.invuln_timer > 0 else PLAYER_COLOR
        pygame.draw.polygon(surface, color, pts)
        pygame.draw.polygon(surface, (0,0,0), pts, 2)


# ==========================================
# SECTION 6: PROJECTILES & HAZARDS
# ==========================================
class Pulse:
    def __init__(self, x, y, damage, max_radius, expansion_rate):
        self.x, self.y = x % WORLD_W, y % WORLD_H
        self.radius = 0
        self.max_radius = max_radius
        self.expansion_rate = expansion_rate
        self.damage = damage
        self.dead = False
        self.hit_player = False

    def update(self, dt, sys_state):
        self.radius += self.expansion_rate * dt
        if self.radius >= self.max_radius:
            self.dead = True
        elif not self.hit_player:
            player = sys_state['player']
            dist_p = dist_wrap((self.x, self.y), (player.x, player.y))
            if abs(dist_p - self.radius) < player.radius + 8:
                player.take_damage(self.damage, is_bullet=True)
                self.hit_player = True

    def draw(self, surface, cam_x, cam_y):
        sx, sy = get_rel_pos(self.x, self.y, cam_x, cam_y)
        pygame.draw.circle(surface, (255, 100, 255), (int(sx), int(sy)), int(self.radius), max(1, int(4 - (self.radius/self.max_radius)*3)))

class Projectile:
    def __init__(self, x, y, vx, vy, damage, radius=4, proj_type='standard', hp=0):
        self.x, self.y = x % WORLD_W, y % WORLD_H
        self.vx, self.vy = vx, vy
        self.damage = damage
        self.radius = radius
        self.type = proj_type
        self.hp = hp 
        self.life = 2.0 if proj_type not in ['mine', 'missile'] else 6.0
        self.dead = False
        self.can_hit_player = True

    def update(self, dt, sys_state):
        if self.type == 'mine':
            player = sys_state['player']
            if dist_sq_wrap((self.x, self.y), (player.x, player.y)) < (6 * UNIT)**2:
                self.life = 0
        elif self.type == 'missile':
            player = sys_state['player']
            dx, dy = shortest_dist_vec((player.x, player.y), (self.x, self.y))
            target_angle = math.atan2(dy, dx)
            current_angle = math.atan2(self.vy, self.vx)
            
            diff = (target_angle - current_angle + math.pi) % (2*math.pi) - math.pi
            turn_rate = 2.5 * dt * sys_state['time_scale']
            new_angle = current_angle + max(-turn_rate, min(turn_rate, diff))
            
            speed = math.hypot(self.vx, self.vy)
            self.vx = math.cos(new_angle) * speed
            self.vy = math.sin(new_angle) * speed
            self.x = (self.x + self.vx * dt) % WORLD_W
            self.y = (self.y + self.vy * dt) % WORLD_H
        else:
            self.x = (self.x + self.vx * dt) % WORLD_W
            self.y = (self.y + self.vy * dt) % WORLD_H
        
        self.life -= dt
        if self.life <= 0: 
            self.dead = True
            self.on_death(sys_state)

    def on_death(self, sys_state):
        if self.type == 'explosive' or self.type == 'mine':
            audio.play('explode')
            num_bullets = 8 if self.type == 'explosive' else 12
            dmg = self.damage * 0.5
            for i in range(num_bullets):
                angle = i * (2 * math.pi / num_bullets)
                sys_state['bullets'].append(Projectile(self.x, self.y, math.cos(angle)*15*UNIT, math.sin(angle)*15*UNIT, dmg))
            for _ in range(10):
                sys_state['particles'].append(Particle(self.x, self.y, (255, 100, 0), speed_mult=1.5))
                
        elif self.type == 'missile':
            if self.hp <= 0:  # Destroyed by laser
                audio.play('explode')
                for _ in range(5):
                    sys_state['particles'].append(Particle(self.x, self.y, (255, 150, 50), speed_mult=1.0))
            else:  # Fizzled out over time
                for _ in range(4):
                    sys_state['particles'].append(Particle(self.x, self.y, (100, 100, 100), speed_mult=0.5))

    def draw(self, surface, cam_x, cam_y):
        sx, sy = get_rel_pos(self.x, self.y, cam_x, cam_y)
        color = ENEMY_LASER_COLOR if self.type == 'standard' else (255, 100, 0)
        
        if self.type == 'mine':
            pygame.draw.circle(surface, (255, 50, 50), (int(sx), int(sy)), self.radius)
            pygame.draw.circle(surface, (255, 255, 255), (int(sx), int(sy)), self.radius, 1)
        elif self.type == 'missile':
            pygame.draw.circle(surface, (255, 150, 50), (int(sx), int(sy)), self.radius)
            pygame.draw.circle(surface, (255, 255, 255), (int(sx), int(sy)), self.radius-2)
        else:
            pygame.draw.circle(surface, color, (int(sx), int(sy)), self.radius)


class ArtilleryShell:
    """Overhead ballistic shell that flies to a locked target zone, then explodes."""
    def __init__(self, x, y, tx, ty, damage):
        self.x, self.y = x % WORLD_W, y % WORLD_H
        self.tx, self.ty = tx % WORLD_W, ty % WORLD_H
        self.damage = damage
        self.speed = 15 * UNIT
        self.radius = 8
        self.dead = False
        self.can_hit_player = False  # Overheads don't hit player mid-flight
        self.timer = 0
        
        dx, dy = shortest_dist_vec((self.tx, self.ty), (self.x, self.y))
        self.dist_left = math.hypot(dx, dy)
        if self.dist_left > 0:
            self.vx = (dx / self.dist_left) * self.speed
            self.vy = (dy / self.dist_left) * self.speed
        else:
            self.vx, self.vy = 0, 0

    def update(self, dt, sys_state):
        move_dist = self.speed * dt * sys_state['time_scale']
        self.dist_left -= move_dist
        self.x = (self.x + self.vx * dt * sys_state['time_scale']) % WORLD_W
        self.y = (self.y + self.vy * dt * sys_state['time_scale']) % WORLD_H
        self.timer += dt
        
        if self.dist_left <= 0:
            self.dead = True
            audio.play('explode')
            num_bullets = 12
            dmg = self.damage * 0.5
            for i in range(num_bullets):
                angle = i * (2 * math.pi / num_bullets)
                sys_state['bullets'].append(Projectile(self.tx, self.ty, math.cos(angle)*15*UNIT, math.sin(angle)*15*UNIT, dmg))
            for _ in range(15):
                sys_state['particles'].append(Particle(self.tx, self.ty, (255, 50, 50), speed_mult=2.0))

    def draw(self, surface, cam_x, cam_y):
        # Draw overhead shell
        sx, sy = get_rel_pos(self.x, self.y, cam_x, cam_y)
        pygame.draw.circle(surface, (150, 50, 50), (int(sx), int(sy)), self.radius)
        pygame.draw.circle(surface, (0, 0, 0), (int(sx), int(sy)), self.radius//2)
        
        # Draw pulsing target warning zone
        tx_s, ty_s = get_rel_pos(self.tx, self.ty, cam_x, cam_y)
        pulse = int(100 + 155 * abs(math.sin(self.timer * 10)))
        pygame.draw.circle(surface, (pulse, 0, 0), (int(tx_s), int(ty_s)), int(30 * UNIT), 2)
        pygame.draw.line(surface, (pulse, 0, 0), (int(tx_s)-10, int(ty_s)), (int(tx_s)+10, int(ty_s)))
        pygame.draw.line(surface, (pulse, 0, 0), (int(tx_s), int(ty_s)-10), (int(tx_s), int(ty_s)+10))


# ==========================================
# SECTION 7: ENEMY ARCHITECTURE
# ==========================================
class BaseEnemy:
    """Base framework for enemy behavior and shared parameters."""
    def __init__(self, x, y):
        self.x, self.y = x, y
        self.radius = UNIT * 0.7
        self.flash_timer = 0
        self.dead = False
        self.killed_by_player = False
        self.timer = random.uniform(0, 2)
        self.angle = random.uniform(0, math.pi*2)
        self.burst_shots = 0
        self.burst_timer = 0
        
        self.max_hp = 1.0 
        self.base_speed = 10 * UNIT 
        self.color = (255, 255, 255)
        self.xp_value = 1
        
        self.hp = self.max_hp

    def hit(self, amount, player):
        self.hp -= amount
        self.flash_timer = 0.1
        if self.hp <= 0: 
            self.killed_by_player = True
            self.dead = True

    def calculate_separation(self, nearby_enemies):
        sep_x, sep_y = 0, 0
        for other in nearby_enemies:
            if other is not self:
                d = dist_wrap((self.x, self.y), (other.x, other.y))
                if 0 < d < self.radius * 3:
                    dx, dy = shortest_dist_vec((self.x, self.y), (other.x, other.y))
                    sep_x += dx / d; sep_y += dy / d
        return sep_x, sep_y

    def apply_movement(self, dt, tx, ty, eff_speed, sep_x, sep_y):
        dir_x, dir_y = shortest_dist_vec((tx, ty), (self.x, self.y))
        move_x, move_y = normalize(dir_x + sep_x * 0.5, dir_y + sep_y * 0.5)
        self.x = (self.x + move_x * eff_speed * dt) % WORLD_W
        self.y = (self.y + move_y * eff_speed * dt) % WORLD_H

    def update(self, dt, sys_state, time_scale):
        if self.flash_timer > 0: self.flash_timer -= dt
        self.timer += dt * time_scale
        self.behavior(dt, sys_state, time_scale)

    def behavior(self, dt, sys_state, time_scale):
        raise NotImplementedError

    def draw(self, surface, cam_x, cam_y):
        sx, sy = get_rel_pos(self.x, self.y, cam_x, cam_y)
        color = (255, 255, 255) if self.flash_timer > 0 else self.color
        self.draw_shape(surface, sx, sy, color)

    def draw_shape(self, surface, sx, sy, color):
        pygame.draw.circle(surface, color, (int(sx), int(sy)), int(self.radius))


class ChaserEnemy(BaseEnemy):
    def __init__(self, x, y):
        super().__init__(x, y)
        self.color = (200, 50, 50)
        self.base_speed = 15 * UNIT 
        
    def behavior(self, dt, sys_state, time_scale):
        player = sys_state['player']
        sep_x, sep_y = self.calculate_separation(sys_state['nearby_enemies'])
        self.apply_movement(dt, player.x, player.y, self.base_speed * time_scale, sep_x, sep_y)

    def draw_shape(self, surface, sx, sy, color):
        pygame.draw.polygon(surface, color,[(sx, sy-self.radius), (sx-self.radius, sy+self.radius), (sx+self.radius, sy+self.radius)])


class SweeperEnemy(BaseEnemy):
    def __init__(self, x, y):
        super().__init__(x, y)
        self.color = (150, 50, 255)
        self.base_speed = 18 * UNIT
        self.max_hp = 2.0
        self.hp = self.max_hp

    def behavior(self, dt, sys_state, time_scale):
        player = sys_state['player']
        px, py = player.x, player.y
        dist_p = dist_wrap((self.x, self.y), (px, py))
        dx_to_p, dy_to_p = shortest_dist_vec((px, py), (self.x, self.y))
        
        optimal = 25 * UNIT
        if dist_p < optimal - 2*UNIT: tx = self.x - dx_to_p; ty = self.y - dy_to_p
        elif dist_p > optimal + 2*UNIT: tx = px; ty = py
        else: tx = self.x; ty = self.y

        if self.timer > 3.0:
            self.timer = 0
            self.burst_shots = 6
            self.burst_timer = 0
            
        if self.burst_shots > 0:
            self.burst_timer += dt * time_scale
            if self.burst_timer > 0.1:
                self.burst_timer = 0
                self.burst_shots -= 1
                progress = (6 - self.burst_shots) / 6.0
                angle_offset = -0.5 + progress * 1.0
                angle = math.atan2(dy_to_p, dx_to_p) + angle_offset
                sys_state['bullets'].append(Projectile(self.x, self.y, math.cos(angle)*25*UNIT, math.sin(angle)*25*UNIT, 2.0 * time_scale))

        sep_x, sep_y = self.calculate_separation(sys_state['nearby_enemies'])
        self.apply_movement(dt, tx, ty, self.base_speed * time_scale, sep_x, sep_y)

    def draw_shape(self, surface, sx, sy, color):
        pygame.draw.polygon(surface, color,[(sx, sy-self.radius), (sx-self.radius, sy+self.radius), (sx+self.radius, sy+self.radius)])


class SplitterLargeEnemy(BaseEnemy):
    def __init__(self, x, y):
        super().__init__(x, y)
        self.color = (139, 69, 19)
        self.radius = 1.5 * UNIT
        self.base_speed = 8 * UNIT
        self.max_hp = 4.0
        self.hp = self.max_hp
        self.xp_value = 3
        angle = random.uniform(0, math.pi * 2)
        self.vx = math.cos(angle) * self.base_speed
        self.vy = math.sin(angle) * self.base_speed

    def behavior(self, dt, sys_state, time_scale):
        if self.dead and self.killed_by_player:
            for _ in range(4):
                sys_state['new_enemies'].append(SplitterSmallEnemy(self.x, self.y))
        
        self.x = (self.x + self.vx * dt * time_scale) % WORLD_W
        self.y = (self.y + self.vy * dt * time_scale) % WORLD_H
        
        if self.timer > 3.0:
            self.timer = 0
            player = sys_state['player']
            dx_to_p, dy_to_p = shortest_dist_vec((player.x, player.y), (self.x, self.y))
            base_angle = math.atan2(dy_to_p, dx_to_p)
            for i in range(5):
                angle = base_angle - 0.4 + (i / 4.0) * 0.8
                sys_state['bullets'].append(Projectile(self.x, self.y, math.cos(angle)*15*UNIT, math.sin(angle)*15*UNIT, 2.0 * time_scale))

    def draw_shape(self, surface, sx, sy, color):
        pygame.draw.circle(surface, color, (int(sx), int(sy)), int(self.radius))
        pygame.draw.circle(surface, (100, 50, 10), (int(sx), int(sy)), int(self.radius-4))


class SplitterSmallEnemy(BaseEnemy):
    def __init__(self, x, y):
        super().__init__(x, y)
        self.color = (160, 82, 45)
        self.radius = 0.6 * UNIT
        self.base_speed = 25 * UNIT
        self.max_hp = 1.0
        self.hp = self.max_hp
        angle = random.uniform(0, math.pi * 2)
        self.vx = math.cos(angle) * self.base_speed
        self.vy = math.sin(angle) * self.base_speed

    def behavior(self, dt, sys_state, time_scale):
        self.x = (self.x + self.vx * dt * time_scale) % WORLD_W
        self.y = (self.y + self.vy * dt * time_scale) % WORLD_H

    def draw_shape(self, surface, sx, sy, color):
        pygame.draw.circle(surface, color, (int(sx), int(sy)), int(self.radius))


class SniperEnemy(BaseEnemy):
    def __init__(self, x, y):
        super().__init__(x, y)
        self.color = (255, 50, 100)
        self.base_speed = 15 * UNIT
        self.max_hp = 2.0
        self.hp = self.max_hp
        self.locked_angle = None

    def behavior(self, dt, sys_state, time_scale):
        player = sys_state['player']
        px, py = player.x, player.y
        dist_p = dist_wrap((self.x, self.y), (px, py))
        dx_to_p, dy_to_p = shortest_dist_vec((px, py), (self.x, self.y))
        
        if self.timer > 5.5: 
            self.timer = 0
            self.locked_angle = None
            
        if self.timer < 3.0:
            optimal = 35 * UNIT
            if dist_p < optimal: tx = self.x - dx_to_p; ty = self.y - dy_to_p
            elif dist_p > optimal + 5*UNIT: tx = px; ty = py
            else: tx = self.x; ty = self.y
            
            sep_x, sep_y = self.calculate_separation(sys_state['nearby_enemies'])
            self.apply_movement(dt, tx, ty, self.base_speed * time_scale, sep_x, sep_y)
            
        elif self.timer < 5.0:
            # Lock aim exactly ONCE and hold it
            if self.locked_angle is None:
                self.locked_angle = math.atan2(dy_to_p, dx_to_p)
                
        else:
            # Full power fire
            if self.locked_angle is not None:
                beam_dx, beam_dy = math.cos(self.locked_angle), math.sin(self.locked_angle)
                proj = dx_to_p * beam_dx + dy_to_p * beam_dy
                if 0 < proj < 150 * UNIT: 
                    closest_x, closest_y = beam_dx * proj, beam_dy * proj
                    if (dx_to_p - closest_x)**2 + (dy_to_p - closest_y)**2 < (player.radius + 5)**2:
                        player.take_damage(8.0 * dt * time_scale, is_bullet=True)

    def draw_shape(self, surface, sx, sy, color):
        pygame.draw.rect(surface, color, (sx-self.radius, sy-self.radius, self.radius*2, self.radius*2))
        if self.timer >= 3.0 and self.timer < 5.0 and self.locked_angle is not None: 
            intensity = int(255 * abs(math.sin(self.timer * 15)))
            pygame.draw.line(surface, (intensity, 0, 0), (sx, sy), (sx + math.cos(self.locked_angle)*(150*UNIT), sy + math.sin(self.locked_angle)*(150*UNIT)), 1)
        elif self.timer >= 5.0 and self.timer < 5.5 and self.locked_angle is not None:
            pygame.draw.line(surface, (255, 100, 100), (sx, sy), (sx + math.cos(self.locked_angle)*(150*UNIT), sy + math.sin(self.locked_angle)*(150*UNIT)), 6)
            pygame.draw.line(surface, (255, 255, 255), (sx, sy), (sx + math.cos(self.locked_angle)*(150*UNIT), sy + math.sin(self.locked_angle)*(150*UNIT)), 2)


class EmitterEnemy(BaseEnemy):
    def __init__(self, x, y):
        super().__init__(x, y)
        self.color = (255, 100, 255)
        self.base_speed = 12 * UNIT
        self.max_hp = 3.0
        self.hp = self.max_hp

    def behavior(self, dt, sys_state, time_scale):
        player = sys_state['player']
        px, py = player.x, player.y
        dist_p = dist_wrap((self.x, self.y), (px, py))
        dx_to_p, dy_to_p = shortest_dist_vec((px, py), (self.x, self.y))
        
        optimal = 20 * UNIT
        if dist_p < optimal: tx = self.x - dx_to_p; ty = self.y - dy_to_p
        elif dist_p > optimal + 5*UNIT: tx = px; ty = py
        else: tx = self.x; ty = self.y
        
        if self.timer > 3.0:
            self.timer = 0
            pulse_dmg = 5.0 * time_scale
            sys_state['pulses'].append(Pulse(self.x, self.y, pulse_dmg, max_radius=25*UNIT, expansion_rate=15*UNIT))
            
        sep_x, sep_y = self.calculate_separation(sys_state['nearby_enemies'])
        self.apply_movement(dt, tx, ty, self.base_speed * time_scale, sep_x, sep_y)

    def draw_shape(self, surface, sx, sy, color):
        pygame.draw.circle(surface, color, (int(sx), int(sy)), int(self.radius))
        pygame.draw.circle(surface, color, (int(sx), int(sy)), int(8*UNIT), 1)


class LauncherEnemy(BaseEnemy):
    """Keeps distance and fires destructible homing missiles that fizzle out."""
    def __init__(self, x, y):
        super().__init__(x, y)
        self.color = (255, 150, 50)
        self.base_speed = 12 * UNIT
        self.max_hp = 3.0
        self.hp = self.max_hp

    def behavior(self, dt, sys_state, time_scale):
        player = sys_state['player']
        px, py = player.x, player.y
        dist_p = dist_wrap((self.x, self.y), (px, py))
        dx_to_p, dy_to_p = shortest_dist_vec((px, py), (self.x, self.y))
        
        optimal = 25 * UNIT
        if dist_p < optimal: tx = self.x - dx_to_p; ty = self.y - dy_to_p
        elif dist_p > optimal + 5*UNIT: tx = px; ty = py
        else: tx = self.x; ty = self.y
        
        if self.timer > 4.5:
            self.timer = 0
            angle = math.atan2(dy_to_p, dx_to_p)
            dmg = 2.0 * time_scale
            sys_state['bullets'].append(Projectile(self.x, self.y, math.cos(angle)*8*UNIT, math.sin(angle)*8*UNIT, dmg, radius=6, proj_type='missile', hp=1.0))
            
        sep_x, sep_y = self.calculate_separation(sys_state['nearby_enemies'])
        self.apply_movement(dt, tx, ty, self.base_speed * time_scale, sep_x, sep_y)

    def draw_shape(self, surface, sx, sy, color):
        pygame.draw.rect(surface, color, (sx-self.radius, sy-self.radius, self.radius*2, self.radius*2))
        pygame.draw.circle(surface, (255,255,255), (int(sx), int(sy)), int(self.radius//2), 1)


class ArtilleryEnemy(BaseEnemy):
    """Targets a static zone and launches an overhead explosive shell."""
    def __init__(self, x, y):
        super().__init__(x, y)
        self.color = (150, 50, 50)
        self.base_speed = 10 * UNIT
        self.max_hp = 3.0
        self.hp = self.max_hp
        self.radius = 1.2 * UNIT
        self.locked_tx = None
        self.locked_ty = None

    def behavior(self, dt, sys_state, time_scale):
        player = sys_state['player']
        px, py = player.x, player.y
        dist_p = dist_wrap((self.x, self.y), (px, py))
        dx_to_p, dy_to_p = shortest_dist_vec((px, py), (self.x, self.y))
        
        if self.timer > 5.0:
            self.timer = 0
            self.locked_tx = None
            self.locked_ty = None
            
        if self.timer < 3.0:
            optimal = 35 * UNIT
            if dist_p < optimal: tx = self.x - dx_to_p; ty = self.y - dy_to_p
            elif dist_p > optimal + 5*UNIT: tx = px; ty = py
            else: tx = self.x; ty = self.y
            
            sep_x, sep_y = self.calculate_separation(sys_state['nearby_enemies'])
            self.apply_movement(dt, tx, ty, self.base_speed * time_scale, sep_x, sep_y)
            
        elif self.timer < 4.0:
            # Lock the exact position to fire shell at
            if self.locked_tx is None:
                self.locked_tx = px
                self.locked_ty = py
                
        elif self.timer >= 4.0 and self.locked_tx is not None:
            dmg = 4.0 * time_scale
            sys_state['bullets'].append(ArtilleryShell(self.x, self.y, self.locked_tx, self.locked_ty, dmg))
            self.locked_tx = None 

    def draw_shape(self, surface, sx, sy, color):
        pygame.draw.rect(surface, color, (sx-self.radius, sy-self.radius, self.radius*2, self.radius*2))
        pygame.draw.circle(surface, (0,0,0), (int(sx), int(sy)), int(self.radius//2))


class PhantomEnemy(BaseEnemy):
    """High speed teleporting ambusher."""
    def __init__(self, x, y):
        super().__init__(x, y)
        self.color = (255, 255, 255)
        self.base_speed = 40 * UNIT
        self.max_hp = 2.5
        self.hp = self.max_hp

    def behavior(self, dt, sys_state, time_scale):
        player = sys_state['player']
        px, py = player.x, player.y
        dist_p = dist_wrap((self.x, self.y), (px, py))
        dx_to_p, dy_to_p = shortest_dist_vec((px, py), (self.x, self.y))
        
        if self.timer > 3.0: 
            self.timer = 0
            angle = random.uniform(0, math.pi*2)
            dist_tp = random.uniform(20*UNIT, 35*UNIT)
            self.x = (px + math.cos(angle)*dist_tp) % WORLD_W
            self.y = (py + math.sin(angle)*dist_tp) % WORLD_H
            for _ in range(12): 
                sys_state['particles'].append(Particle(self.x, self.y, (255,255,255), speed_mult=2.0))
        elif self.timer > 2.0:
            # Stand still and fire
            self.burst_timer += dt * time_scale
            if self.burst_timer > 0.1:
                self.burst_timer = 0
                angle = math.atan2(dy_to_p, dx_to_p) + random.uniform(-0.15, 0.15)
                sys_state['bullets'].append(Projectile(self.x, self.y, math.cos(angle)*28*UNIT, math.sin(angle)*28*UNIT, 4.0 * time_scale))
        else:
            # Approach
            if dist_p < 18 * UNIT: tx = self.x - dx_to_p; ty = self.y - dy_to_p
            else: tx = px; ty = py
            sep_x, sep_y = self.calculate_separation(sys_state['nearby_enemies'])
            self.apply_movement(dt, tx, ty, self.base_speed * time_scale, sep_x, sep_y)

    def draw_shape(self, surface, sx, sy, color):
        pygame.draw.polygon(surface, color,[(sx, sy-self.radius*1.2), (sx-self.radius, sy+self.radius), (sx, sy), (sx+self.radius, sy+self.radius)])


# ==========================================
# SECTION 8: LOOT & PICKUPS
# ==========================================
class Drop:
    """Represents purely visual economy items (Coins). XP is instant."""
    def __init__(self, x, y):
        self.x, self.y = x, y
        self.radius = 6
        self.dead = False

    def draw(self, surface, cam_x, cam_y):
        sx, sy = get_rel_pos(self.x, self.y, cam_x, cam_y)
        pygame.draw.circle(surface, COIN_COLOR, (int(sx), int(sy)), self.radius)


# ==========================================
# SECTION 9: MAIN GAME ENGINE
# ==========================================
class Game:
    def __init__(self):
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("BULLET HELL MINUTE")
        self.clock = pygame.time.Clock()
        
        font_name = 'Segoe UI, Helvetica, Arial, sans-serif'
        self.font = pygame.font.SysFont(font_name, 16, bold=True)
        self.large_font = pygame.font.SysFont(font_name, 32, bold=True)
        self.huge_font = pygame.font.SysFont(font_name, 100, bold=True)
        
        self.state = "MAIN_MENU" 
        self.shake = 0
        self.chunk_mgr = ToroidalChunkManager(cell_size=10*UNIT)
        self.menu_timer = 0
        self.dummy_enemies =[ChaserEnemy(random.uniform(0, WORLD_W), random.uniform(0, WORLD_H)) for _ in range(15)]

    def start_run(self):
        self.player = Player()
        self.enemies, self.bullets, self.pulses, self.drops, self.particles = [], [], [], [],[]
        self.game_time, self.spawn_timer = 0, 0
        self.state = "PLAYING"

    def fire_laser(self, mx, my, cam_x, cam_y, dt):
        px, py = self.player.x, self.player.y
        psx, psy = get_rel_pos(px, py, cam_x, cam_y)
        angle = math.atan2(my - psy, mx - psx)
        dx, dy = math.cos(angle), math.sin(angle)
        
        max_dist = self.player.max_laser_dist
        drain_rate = self.player.get_laser_drain()
        
        if self.player.energy > 0:
            self.player.energy -= drain_rate * dt
            thick = True
            dps = self.player.get_laser_dps()
            thickness = self.player.get_laser_thickness()
            color = LASER_COLOR
            audio.play('shoot')
        else:
            self.player.energy = 0
            thick = False
            dps = self.player.get_laser_dps() * 0.1 
            thickness = 1
            color = WEAK_LASER_COLOR

        # Enemy Hits
        for e in self.enemies:
            edx, edy = shortest_dist_vec((e.x, e.y), (px, py))
            proj = max(0, min(max_dist, edx*dx + edy*dy))
            closest_x, closest_y = dx * proj, dy * proj
            if math.hypot(edx - closest_x, edy - closest_y) < e.radius + thickness/2:
                e.hit(dps * dt, self.player)
                if thick: 
                    self.particles.append(Particle(e.x, e.y, color, speed_mult=1.5, size=2))

        # Projectile Intersection (Only destructibles)
        for b in self.bullets:
            if getattr(b, 'hp', 0) > 0:
                bdx, bdy = shortest_dist_vec((b.x, b.y), (px, py))
                proj = max(0, min(max_dist, bdx*dx + bdy*dy))
                closest_x, closest_y = dx * proj, dy * proj
                if math.hypot(bdx - closest_x, bdy - closest_y) < b.radius + thickness/2:
                    b.hp -= dps * dt
                    if b.hp <= 0: b.dead = True
                    if thick: self.particles.append(Particle(b.x, b.y, color, speed_mult=1.5, size=2))

        if thick:
            for _ in range(3):
                dist_rnd = random.uniform(0, max_dist)
                lx, ly = (px + dx * dist_rnd) % WORLD_W, (py + dy * dist_rnd) % WORLD_H
                self.particles.append(Particle(lx, ly, color, speed_mult=0.5, size=2))
            self.shake = min(4, self.shake + 0.5) 

        return psx, psy, dx, dy, max_dist, thickness, color

    def process_collisions(self, time_multiplier):
        for e in self.enemies:
            if dist_sq_wrap((e.x, e.y), (self.player.x, self.player.y)) < (e.radius + self.player.radius)**2:
                self.player.take_damage(4.0 * time_multiplier, is_bullet=False) 
                e.dead = True
                e.killed_by_player = False 
                self.shake = min(25, self.shake + 12)
                for _ in range(15): 
                    self.particles.append(Particle(e.x, e.y, (255, 50, 50), speed_mult=2.0))

        for b in self.bullets:
            if getattr(b, 'can_hit_player', True):
                if dist_sq_wrap((b.x, b.y), (self.player.x, self.player.y)) < (self.player.radius + b.radius)**2:
                    if self.player.take_damage(b.damage, is_bullet=True):
                        self.shake = min(10, self.shake + 5)
                    b.dead = True

    def process_spawner(self, dt):
        if self.game_time < 10.0:
            current_cap = max(3, int(self.game_time))
        else:
            current_cap = min(MAX_ENEMIES, int(15 + (self.game_time / 15.0) * 20))
            
        self.spawn_timer -= dt
        if self.spawn_timer <= 0 and len(self.enemies) < current_cap:
            self.spawn_timer = max(0.01, 0.2 - (self.game_time / 60.0) * 0.15)
            
            e_classes =[ChaserEnemy, SweeperEnemy, SplitterLargeEnemy, SniperEnemy, EmitterEnemy, LauncherEnemy, ArtilleryEnemy, PhantomEnemy]
            w_phantom = min(15, max(0, int(self.game_time - 20))) 
            weights = [15, 10, 8, 10, 8, 8, 8, w_phantom]
            
            EnemyClass = random.choices(e_classes, weights=weights)[0]
            
            if self.player.vx != 0 or self.player.vy != 0: 
                base_angle = math.atan2(self.player.vy, self.player.vx)
            else: 
                base_angle = random.uniform(0, 2*math.pi)
                
            angle = base_angle + random.uniform(-0.8, 0.8)
            dist_spawn = random.uniform(35 * UNIT, 45 * UNIT)
            sx = (self.player.x + math.cos(angle) * dist_spawn) % WORLD_W
            sy = (self.player.y + math.sin(angle) * dist_spawn) % WORLD_H
            self.enemies.append(EnemyClass(sx, sy))

    def update(self, real_dt):
        keys = pygame.key.get_pressed()
        mouse_x, mouse_y = pygame.mouse.get_pos()
        click = pygame.mouse.get_pressed()[0]
        
        if self.state == "MAIN_MENU":
            self.menu_timer += real_dt
            for event in pygame.event.get():
                if event.type == pygame.QUIT: pygame.quit(); sys.exit()
                if event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
                    self.start_run()
            for e in self.dummy_enemies:
                e.x = (e.x + math.cos(e.angle)*e.base_speed*0.5*real_dt) % WORLD_W
                e.y = (e.y + math.sin(e.angle)*e.base_speed*0.5*real_dt) % WORLD_H
                if random.random() < 0.01: e.angle = random.uniform(0, 2*math.pi)
            return

        for event in pygame.event.get():
            if event.type == pygame.QUIT: pygame.quit(); sys.exit()
            if event.type == pygame.MOUSEBUTTONDOWN:
                if keys[pygame.K_e]:
                    self.handle_shop_click(mouse_x, mouse_y, event.button)
        
        is_shop_open = keys[pygame.K_e]
        dt = real_dt * (0.05 if is_shop_open else 1.0)
        self.game_time += dt
        
        time_multiplier = 1.0 + (self.game_time / 40.0)
        self.shake = max(0, self.shake - 30 * real_dt)
        base_cam_x, base_cam_y = self.player.x, self.player.y

        if not is_shop_open:
            if click:
                self.active_laser = self.fire_laser(mouse_x, mouse_y, base_cam_x, base_cam_y, dt)
            else:
                self.active_laser = None
                self.player.energy = min(self.player.get_max_energy(), self.player.energy + self.player.get_energy_regen() * dt)
        else:
            self.active_laser = None

        self.player.update(dt, keys)
        self.process_spawner(dt)

        self.chunk_mgr.clear()
        for e in self.enemies: 
            self.chunk_mgr.add(e)

        sys_state = {
            'player': self.player, 'bullets': self.bullets, 
            'particles': self.particles, 'pulses': self.pulses,
            'time_scale': time_multiplier, 'nearby_enemies': [],
            'new_enemies':[]
        }
        
        for e in self.enemies:
            sys_state['nearby_enemies'] = self.chunk_mgr.get_nearby(e.x, e.y)
            e.update(dt, sys_state, time_multiplier)

        self.enemies.extend(sys_state['new_enemies'])

        for b in self.bullets: b.update(dt, sys_state)
        for p in self.pulses: p.update(dt, sys_state)
        for p in self.particles: p.update(dt)

        self.process_collisions(time_multiplier)

        # Coin Magnet
        for d in self.drops:
            dist_p = dist_wrap((self.player.x, self.player.y), (d.x, d.y))
            if dist_p < 12 * UNIT:
                dx, dy = shortest_dist_vec((self.player.x, self.player.y), (d.x, d.y))
                dir_x, dir_y = normalize(dx, dy)
                d.x = (d.x + dir_x * 25 * UNIT * dt) % WORLD_W
                d.y = (d.y + dir_y * 25 * UNIT * dt) % WORLD_H
            if dist_p < self.player.radius + d.radius:
                self.player.coins += 1
                audio.play('coin')
                d.dead = True

        for e in[e for e in self.enemies if e.dead]:
            if e.killed_by_player:
                self.player.add_xp(e.xp_value) 
                if random.random() < 0.25: 
                    self.drops.append(Drop(e.x+random.uniform(-5,5), e.y+random.uniform(-5,5)))
            
            for _ in range(8): 
                self.particles.append(Particle(e.x, e.y, e.color))
        
        # Cull dead entities
        self.enemies = [e for e in self.enemies if not e.dead]
        self.bullets = [b for b in self.bullets if not b.dead]
        self.pulses = [p for p in self.pulses if not p.dead]
        self.drops =[d for d in self.drops if not getattr(d, 'dead', False)]
        self.particles =[p for p in self.particles if p.life > 0]
        
        if self.player.hp <= 0: 
            self.state = "MAIN_MENU"

    # ==========================================
    # SECTION 9: RENDERING & UI
    # ==========================================
    def draw(self):
        self.screen.fill(BG_COLOR)
        if self.state == "MAIN_MENU":
            self.draw_main_menu()
            pygame.display.flip()
            return
            
        cam_x = self.player.x + random.uniform(-self.shake, self.shake)
        cam_y = self.player.y + random.uniform(-self.shake, self.shake)
        
        for speed, color in[(1.0, (30,35,40)), (0.5, (20,25,30))]:
            cx = (cam_x * speed) % (UNIT * 4)
            cy = (cam_y * speed) % (UNIT * 4)
            for x in range(0, WIDTH + UNIT*4, UNIT * 4): 
                pygame.draw.line(self.screen, color, (x - cx, 0), (x - cx, HEIGHT), 2)
            for y in range(0, HEIGHT + UNIT*4, UNIT * 4): 
                pygame.draw.line(self.screen, color, (0, y - cy), (WIDTH, y - cy), 2)

        for d in self.drops: d.draw(self.screen, cam_x, cam_y)
        for e in self.enemies: e.draw(self.screen, cam_x, cam_y)
        for b in self.bullets: b.draw(self.screen, cam_x, cam_y)
        for p in self.pulses: p.draw(self.screen, cam_x, cam_y)
        for p in self.particles: p.draw(self.screen, cam_x, cam_y)
        
        if getattr(self, 'active_laser', None):
            psx, psy, dx, dy, max_dist, thick, color = self.active_laser
            pygame.draw.line(self.screen, color, (psx, psy), (psx + dx * max_dist, psy + dy * max_dist), thick)
            if thick > 1: 
                pygame.draw.line(self.screen, (255, 255, 255), (psx, psy), (psx + dx * max_dist, psy + dy * max_dist), thick//2)

        mouse_x, mouse_y = pygame.mouse.get_pos()
        self.player.draw(self.screen, cam_x, cam_y, mouse_x, mouse_y)
            
        self.draw_timer()
        self.draw_minimap()

        if pygame.key.get_pressed()[pygame.K_e]: 
            self.draw_shop()
        self.draw_minimal_hud()

        pygame.display.flip()

    def draw_timer(self):
        cx, cy = WIDTH // 2, HEIGHT // 2
        mins, secs, ms = int(self.game_time // 60), int(self.game_time % 60), int((self.game_time % 1) * 100)
        
        timer_surf = self.huge_font.render(f"{mins:02d}:{secs:02d}:{ms:02d}", True, (255, 255, 255))
        timer_surf.set_alpha(30)
        self.screen.blit(timer_surf, (cx - timer_surf.get_width()//2, cy - timer_surf.get_height()//2))

        radius, radius_in = 250, 230
        rect = pygame.Rect(cx - radius, cy - radius, radius * 2, radius * 2)
        pygame.draw.arc(self.screen, (50, 50, 50), rect, 0, 2*math.pi, 2)
        pygame.draw.arc(self.screen, PLAYER_COLOR, rect, math.pi/2 - ((secs / 60) * 2 * math.pi), math.pi/2, 6)
        
        rect_in = pygame.Rect(cx - radius_in, cy - radius_in, radius_in * 2, radius_in * 2)
        pygame.draw.arc(self.screen, (50, 50, 50), rect_in, 0, 2*math.pi, 1)
        pygame.draw.arc(self.screen, XP_UI_COLOR, rect_in, math.pi/2 - ((ms / 100) * 2 * math.pi), math.pi/2, 4)

    def draw_minimap(self):
        map_w, map_h = 200, 200
        mx, my = WIDTH - map_w - 20, 20
        s = pygame.Surface((map_w, map_h), pygame.SRCALPHA)
        s.fill((0, 0, 0, 150))
        pygame.draw.rect(s, (100, 100, 100), (0, 0, map_w, map_h), 2)
        
        scale_x, scale_y = map_w / WORLD_W, map_h / WORLD_H
        for e in self.enemies: 
            pygame.draw.circle(s, e.color, (int(e.x * scale_x), int(e.y * scale_y)), 2)
        pygame.draw.circle(s, PLAYER_COLOR, (int(self.player.x * scale_x), int(self.player.y * scale_y)), 3)
        self.screen.blit(s, (mx, my))

    def draw_minimal_hud(self):
        w, h, bx, by = 250, 8, WIDTH - 270, HEIGHT - 40
        self.screen.blit(self.font.render(f"COINS: {self.player.coins}  LVL: {self.player.level} ({self.player.xp}/{self.player.next_level_xp()})", True, (200, 200, 200)), (bx - 50, by - 25))
        
        pygame.draw.rect(self.screen, (30, 30, 30), (bx, by, w, h))
        pygame.draw.rect(self.screen, LASER_COLOR, (bx, by, w * (self.player.energy / self.player.get_max_energy()), h))
        
        by += 16
        pygame.draw.rect(self.screen, (30, 30, 30), (bx, by, w, h))
        pygame.draw.rect(self.screen, HP_COLOR, (bx, by, w * (self.player.hp / self.player.get_max_hp()), h))

    def draw_main_menu(self):
        menu_cam_x = self.menu_timer * 60
        menu_cam_y = self.menu_timer * 40
        
        for speed, color in[(1.0, (30,35,40)), (0.5, (20,25,30))]:
            cx = (menu_cam_x * speed) % (UNIT * 4)
            cy = (menu_cam_y * speed) % (UNIT * 4)
            for x in range(0, WIDTH + UNIT*4, UNIT * 4): 
                pygame.draw.line(self.screen, color, (x - cx, 0), (x - cx, HEIGHT), 2)
            for y in range(0, HEIGHT + UNIT*4, UNIT * 4): 
                pygame.draw.line(self.screen, color, (0, y - cy), (WIDTH, y - cy), 2)
            
        for e in self.dummy_enemies:
            sx, sy = get_rel_pos(e.x, e.y, menu_cam_x, menu_cam_y)
            pygame.draw.polygon(self.screen, e.color,[(sx, sy-e.radius), (sx-e.radius, sy+e.radius), (sx+e.radius, sy+e.radius)])
        
        title = self.huge_font.render("BULLET HELL", True, ENEMY_LASER_COLOR)
        subtitle = self.large_font.render("MINUTE", True, LASER_COLOR)
        self.screen.blit(title, (WIDTH//2 - title.get_width()//2, HEIGHT//3 - 30))
        self.screen.blit(subtitle, (WIDTH//2 - subtitle.get_width()//2, HEIGHT//3 + 70))
        
        controls = [
            "PRESS[SPACE] TO DEPLOY",
            "",
            "[W A S D] to Move",
            "[HOLD LEFT CLICK] to Fire Laser",
            "[HOLD E] to Open Bullet-Time Shop"
        ]
        
        for i, text in enumerate(controls):
            color = (255, 255, 255) if i == 0 else (150, 150, 150)
            font = self.large_font if i == 0 else self.font
            img = font.render(text, True, color)
            self.screen.blit(img, (WIDTH//2 - img.get_width()//2, HEIGHT//2 + i*30))

    def draw_shop(self):
        s = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        s.fill((10, 15, 20, 200))
        self.screen.blit(s, (0, 0))
        
        self.screen.blit(self.large_font.render("SYSTEM COMPONENT INTEGRATION", True, (200, 200, 255)), (40, 40))
        self.screen.blit(self.font.render("LEFT-CLICK: Upgrade  |  RIGHT-CLICK: Downgrade (100% Refund)", True, (150, 150, 150)), (40, 75))
        
        self.shop_rects = {}
        for i, (k, v) in enumerate(COMPONENTS.items()):
            x, y, lvl = 40, 120 + i * 90, self.player.comps[k]
            rect = pygame.Rect(x, y, 380, 80)
            pygame.draw.rect(self.screen, (30, 35, 45), rect, border_radius=5)
            
            if lvl < MAX_LEVEL:
                cost_up = get_upgrade_cost(lvl)
                cost_down = get_upgrade_cost(lvl - 1) if lvl > 0 else 0
                color = HP_COLOR if self.player.coins >= cost_up else (255, 50, 50)
                
                self.screen.blit(self.font.render(f"{v['name']} (Lvl {lvl}/{MAX_LEVEL})", True, (255, 255, 255)), (x + 10, y + 10))
                self.screen.blit(self.font.render(v['desc'], True, (150, 150, 150)), (x + 10, y + 30))
                self.screen.blit(self.font.render(f"UPGRADE: {cost_up} CR", True, color), (x + 10, y + 55))
                self.shop_rects[k] = (rect, cost_up, cost_down, lvl)
            else:
                cost_down = get_upgrade_cost(MAX_LEVEL - 1)
                self.screen.blit(self.font.render(f"{v['name']} (MAX)", True, (255, 255, 255)), (x + 10, y + 10))
                self.screen.blit(self.font.render("COMPONENT MAXED", True, (100, 100, 100)), (x + 10, y + 30))
                self.shop_rects[k] = (rect, 99999, cost_down, MAX_LEVEL)

    def handle_shop_click(self, mx, my, button):
        for k, (rect, cost_up, cost_down, lvl) in self.shop_rects.items():
            if rect.collidepoint(mx, my):
                if button == 1 and lvl < MAX_LEVEL and self.player.coins >= cost_up:
                    self.player.coins -= cost_up
                    self.player.comps[k] += 1
                    return True
                elif button == 3 and lvl > 0: 
                    self.player.coins += cost_down
                    self.player.comps[k] -= 1
                    self.player.hp = min(self.player.hp, self.player.get_max_hp())
                    return True
        return False

    def run(self):
        while True:
            real_dt = min(self.clock.tick(FPS) / 1000.0, 0.1)
            self.update(real_dt)
            self.draw()

if __name__ == "__main__":
    Game().run()
