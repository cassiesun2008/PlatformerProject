import pygame
import sys

# -------------- Config --------------
WIDTH, HEIGHT = 960, 540
TITLE = "Pygame Platformer Starter"
FPS = 60

# World physics
GRAVITY = 2000.0          # px/s^2
MOVE_SPEED = 300.0        # px/s
AIR_CONTROL = 0.65        # fraction of MOVE_SPEED allowed while airborne
JUMP_VELOCITY = -800.0    # px/s (negative goes up)
MAX_FALL_SPEED = 2000.0

# Player
PLAYER_SIZE = (40, 56)
PLAYER_SIZE_SMALL = (20, 28)
SHRINK_DURATION = 5.0  # seconds
START_POS = (96, 96)

BG_COLOR = (28, 28, 40)
FG_COLOR = (230, 230, 230)
ACCENT = (120, 180, 255)
PLATFORM_COLOR = (70, 120, 160)
LADDER_COLOR = (150, 75, 0)
MONSTER_COLOR = (255, 50, 50)
ENEMY_SIZE = (36, 36)
PROJECTILE_COLOR = (255, 100, 0)
POWERUP_COLOR = (147, 112, 219)

# -------------- Level data --------------
# Use simple ASCII tiles: '#' = solid, 'P' = player start, '-' = empty, 'L' = ladder, '*' = powerup, 'E' = enemy, 'F' = shooting enemy
LEVEL_MAP = [
    "##--------------------------------------------------------------",
    "##--------------------------------------------------------------------------------------------------------------------",
    "##----------------*---------------------------------------------------------------------------------------------------",
    "##---------------###--------------------------------------------------------------------------------------------------",
    "##------------------L#------------------------------------------------------------------------------------------------",
    "##------------------L---------------###-------------------------------------------------------------------------------",
    "##------------------L-------------------------------------------------------------------------------------------------",
    "##------------------L---------------F---------------------------------------------------------------------------------",
    "##-----------------####-------###---------------------###-------------------------------------------------------------",
    "##----------------------------------------------------###-------------------------------------------------------------",
    "##-----------L###---------###-------------------------###-----##------------------------------------------------------",
    "##-----------L--------------------------###-----------###-------------------------------------------------------------",
    "##-----------L-----------------E----F-----------------###-------------------------------------------------------------",
    "##------P----L--------------------------------------------------------------------------------------------------------",
    "####################------###################---######################################################################",
    "####################------###################---######################################################################",
]

TILE_SIZE = 48


# -------------- Helpers --------------
def rect_from_grid(x, y, w=1, h=1):
    return pygame.Rect(x * TILE_SIZE, y * TILE_SIZE, w * TILE_SIZE, h * TILE_SIZE)


# -------------- Game Objects --------------
class Platform(pygame.sprite.Sprite):
    def __init__(self, rect, is_ladder=False):
        super().__init__()
        self.rect = rect
        self.is_ladder = is_ladder

    def draw(self, surf, camera):
        r = self.rect.move(-camera.x, -camera.y)
        if not self.is_ladder:
            pygame.draw.rect(surf, PLATFORM_COLOR, r, border_radius=6)
        else:
            pygame.draw.rect(surf, LADDER_COLOR, r, border_radius=6)


class Enemy(pygame.sprite.Sprite):
    def __init__(self, pos):
        super().__init__()
        self.rect = pygame.Rect(pos[0], pos[1], *ENEMY_SIZE)
        self.color = MONSTER_COLOR

    def draw(self, surf, camera):
        r = self.rect.move(-camera.x, -camera.y)
        pygame.draw.rect(surf, MONSTER_COLOR, r, border_radius=6)


class ShootingEnemy(pygame.sprite.Sprite):
    def __init__(self, pos, direction):
        super().__init__()
        self.rect = pygame.Rect(pos[0], pos[1], *ENEMY_SIZE)
        self.direction = direction  # 1 for down-right, -1 for down-left
        self.shoot_timer = 0
        self.shoot_interval = 2.0  # shoot every 2 seconds

    def update(self, dt, projectiles):
        self.shoot_timer += dt
        if self.shoot_timer >= self.shoot_interval:
            self.shoot_timer = 0
            # Create a new projectile
            proj_x = self.rect.centerx
            proj_y = self.rect.centery
            projectiles.append(Projectile((proj_x, proj_y), self.direction))

    def draw(self, surf, camera):
        r = self.rect.move(-camera.x, -camera.y)
        # Draw differently to distinguish from regular enemies
        pygame.draw.rect(surf, (255, 150, 0), r, border_radius=6)


class Projectile(pygame.sprite.Sprite):
    def __init__(self, pos, direction):
        super().__init__()
        self.rect = pygame.Rect(pos[0], pos[1], 12, 12)
        self.direction = direction
        self.speed = 300  # pixels per second

    def update(self, dt):
        # Move diagonally (down and left/right based on direction)
        self.rect.x += self.speed * self.direction * dt
        self.rect.y += self.speed * dt  # always move down


class Powerup(pygame.sprite.Sprite):
    def __init__(self, rect):
        super().__init__()
        self.rect = rect

    def draw(self, surf, cam):
        pygame.draw.ellipse(surf, POWERUP_COLOR, self.rect.move(-cam.x, -cam.y))


class Player(pygame.sprite.Sprite):
    def __init__(self, pos):
        super().__init__()
        self.rect = pygame.Rect(pos[0], pos[1], *PLAYER_SIZE)
        self.vel = pygame.Vector2(0, 0)
        self.on_ground = False
        self.facing = 1  # 1 right, -1 left
        self.can_double_jump = False
        self.has_double_jump = False
        self.jump_was_pressed = False
        self.is_colliding_ladder = False
        self.is_small = False
        self.shrink_timer = 0

        # Health
        self.max_health = 100
        self.health = self.max_health
        self.invuln_timer = 0

    def update(self, dt, solids, input_dir, jump_pressed, shrink_pressed):
        if self.invuln_timer > 0:
            self.invuln_timer -= dt

        if shrink_pressed and not self.is_small:
            # Activate shrink
            old_bottom = self.rect.bottom
            self.is_small = True
            self.rect.width = PLAYER_SIZE_SMALL[0]
            self.rect.height = PLAYER_SIZE_SMALL[1]
            self.rect.bottom = old_bottom  # Keep feet in same position
            self.shrink_timer = SHRINK_DURATION

        # Update shrink timer
        if self.is_small:
            self.shrink_timer -= dt
            if self.shrink_timer <= 0:
                # Return to normal size
                old_bottom = self.rect.bottom
                self.is_small = False
                self.rect.width = PLAYER_SIZE[0]
                self.rect.height = PLAYER_SIZE[1]
                self.rect.bottom = old_bottom

        self.is_colliding_ladder = False

        probe = self.rect.inflate(6, 0)  # widen a bit
        self.is_colliding_ladder = any(
            getattr(s, "is_ladder", False) and probe.colliderect(s.rect) for s in solids
        )

        # ---- Horizontal movement
        target_speed = MOVE_SPEED * input_dir

        if not self.is_colliding_ladder:
            if not self.on_ground:
                target_speed *= AIR_CONTROL

        accel = 5000.0  # quick responsive accel
        if abs(target_speed - self.vel.x) < accel * dt:
            self.vel.x = target_speed
        else:
            self.vel.x += accel * dt * (1 if target_speed > self.vel.x else -1)

        if input_dir != 0:
            self.facing = 1 if input_dir > 0 else -1

        # Jumping
        keys = pygame.key.get_pressed()
        on_ladder_input = keys[pygame.K_UP] or keys[pygame.K_w] or keys[pygame.K_DOWN] or keys[pygame.K_s]
        if self.is_colliding_ladder:
            ladder = next((s for s in solids if getattr(s, "is_ladder", False) and self.rect.colliderect(s.rect)), None)
            if ladder:
                lerp_factor = 0.2
                self.rect.centerx += (ladder.rect.centerx - self.rect.centerx) * lerp_factor

            if keys[pygame.K_SPACE] or keys[pygame.K_w] or keys[pygame.K_UP]:
                self.vel.y = -150
            elif keys[pygame.K_DOWN] or keys[pygame.K_s]:
                self.vel.y = 150
            else:
                self.vel.y += GRAVITY * dt
                self.vel.y = min(self.vel.y, MAX_FALL_SPEED)

            if jump_pressed and not self.jump_was_pressed:
                self.vel.y = JUMP_VELOCITY
                self.on_ground = False
                self.has_double_jump = self.can_double_jump
                self.is_colliding_ladder = False
        else:
            if jump_pressed and not self.jump_was_pressed:
                if self.on_ground:
                    self.vel.y = JUMP_VELOCITY
                    self.on_ground = False
                    self.has_double_jump = self.can_double_jump
                elif self.has_double_jump:
                    self.vel.y = JUMP_VELOCITY
                    self.has_double_jump = False

            # ---- Gravity
            self.vel.y += GRAVITY * dt
            self.vel.y = min(self.vel.y, MAX_FALL_SPEED)

        keys = pygame.key.get_pressed()
        if self.is_colliding_ladder:
            if keys[pygame.K_UP]:
                self.vel.y = -150
            else:
                self.vel.y = 150

        # X axis
        self.rect.x += round(self.vel.x * dt)
        for s in solids:
            if self.rect.colliderect(s.rect) and not s.is_ladder:
                if self.vel.x > 0:
                    self.rect.right = s.rect.left
                elif self.vel.x < 0:
                    self.rect.left = s.rect.right
                self.vel.x = 0

        # Y axis
        self.rect.y += round(self.vel.y * dt)
        for s in solids:
            if self.rect.colliderect(s.rect) and not s.is_ladder:
                if self.vel.y > 0:
                    self.rect.bottom = s.rect.top
                    self.on_ground = True
                    self.vel.y = 0
                    self.has_double_jump = True  # reset on landing
                elif self.vel.y < 0:
                    self.rect.top = s.rect.bottom
                    self.vel.y = 0

        # Fall damage (small, proportional)
        if self.on_ground:
            fall_distance = self.last_y - self.rect.y
            if fall_distance < -300:  # fell more than 300 px
                damage = int(abs(fall_distance) / 50)  # much smaller damage
                self.health -= damage
                if self.health < 0:
                    self.health = 0
            self.last_y = self.rect.y
        else:
            if self.vel.y > 0:
                self.last_y = min(self.last_y, self.rect.y)

        # Instant death if fallen into pit
        if self.rect.top > len(LEVEL_MAP) * TILE_SIZE:
            self.health = 0

        self.jump_was_pressed = jump_pressed

    def take_damage(self, dmg, knockback):
        if self.invuln_timer <= 0 and self.health > 0:
            self.health = max(0, self.health - dmg)
            self.vel = pygame.Vector2(knockback)
            self.invuln_timer = 0.5

    def draw(self, surf, cam):
        r = self.rect.move(-cam.x, -cam.y)
        # body
        color = FG_COLOR if not self.is_small else (150, 220, 255)  # Blue tint when small
        pygame.draw.rect(surf, color, r, border_radius=8)
        # face accent
        eye_w = 6 if not self.is_small else 3
        eye_h = 8 if not self.is_small else 4
        y = r.y + r.height // 3
        eye_x = r.centerx + (r.width // 4) * self.facing - (eye_w // 2)
        pygame.draw.rect(surf, ACCENT, (eye_x, y, eye_w, eye_h), border_radius=2)

        # Prevent leaving the level boundaries
        # Prevent leaving level horizontally and top only
        world_w = max(len(row) for row in LEVEL_MAP) * TILE_SIZE
        world_h = len(LEVEL_MAP) * TILE_SIZE

        # Clamp horizontally
        if self.rect.left < 0:
            self.rect.left = 0
            self.vel.x = 0
        if self.rect.right > world_w:
            self.rect.right = world_w
            self.vel.x = 0

        # Clamp at the top
        if self.rect.top < 0:
            self.rect.top = 0
            self.vel.y = 0

        # Allow falling off the bottom — instant health to 0
        if self.rect.top > world_h:
            self.health = 0

class Powerup(pygame.sprite.Sprite):
    def __init__(self, rect: pygame.Rect):
        super().__init__()
        self.rect = rect

    def draw(self, surf, camera):
        r = self.rect.move(-camera.x, -camera.y)
        pygame.draw.ellipse(surf, (255, 200, 50), r)  # gold orb

# -------------- Camera --------------
class Camera:
    def __init__(self):
        self.x = 0
        self.y = 0

    def update(self, target_rect):
        # Smooth-follow camera (lerp)
        margin_x, margin_y = WIDTH * 0.35, HEIGHT * 0.4
        target_x = target_rect.centerx - WIDTH // 2
        target_y = target_rect.centery - HEIGHT // 2

        # Keep player within soft margins to reduce camera jitter
        if target_rect.centerx - self.x < margin_x:
            self.x = target_rect.centerx - margin_x
        elif target_rect.centerx - self.x > WIDTH - margin_x:
            self.x = target_rect.centerx - (WIDTH - margin_x)

        if target_rect.centery - self.y < margin_y:
            self.y = target_rect.centery - margin_y
        elif target_rect.centery - self.y > HEIGHT - margin_y:
            self.y = target_rect.centery - (HEIGHT - margin_y)

        # Clamp to world bounds (compute from level)
        world_w = max(len(row) for row in LEVEL_MAP) * TILE_SIZE
        world_h = len(LEVEL_MAP) * TILE_SIZE
        self.x = max(0, min(self.x, world_w - WIDTH))
        self.y = max(0, min(self.y, world_h - HEIGHT))


def build_level():
    solids, powerups, enemies, shooters = [], [], [], []
    player_start = START_POS
    for y, row in enumerate(LEVEL_MAP):
        for x, ch in enumerate(row):
            if ch == '#':
                solids.append(Platform(rect_from_grid(x, y)))
            elif ch == 'L':
                solids.append(Platform(rect_from_grid(x, y), True))
            elif ch == 'P':
                player_start = (x * TILE_SIZE, y * TILE_SIZE - (PLAYER_SIZE[1] - TILE_SIZE))
            elif ch == '*':
                powerups.append(Powerup(rect_from_grid(x, y)))
            elif ch == 'E':
                enemies.append(Enemy((x * TILE_SIZE, y * TILE_SIZE)))
            elif ch == 'F':
                dir = 1 if x > len(row) / 2 else -1
                shooters.append(ShootingEnemy((x * TILE_SIZE, y * TILE_SIZE), dir))
    return solids, powerups, enemies, shooters, player_start


# -------------- Main --------------
def main():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption(TITLE)
    clock = pygame.time.Clock()
    font = pygame.font.SysFont("verdana", 16)

    # reset_game rebuilds everything including powerups
    def reset_game():
        solids, powerups, enemies, shooters, start = build_level()
        player = Player(start)
        projectiles = []
        camera = Camera()
        spawn_protect = 0.15  # short window after reset to avoid immediate pickup
        return solids, powerups, enemies, shooters, player, projectiles, camera, spawn_protect

    solids, powerups, enemies, shooters, player, projectiles, cam, spawn_protect = reset_game()

    running = True
    while running:
        dt = clock.tick(FPS) / 1000.0
        if spawn_protect > 0:
            spawn_protect -= dt

        jump = False
        input_dir = 0

        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                running = False
            elif e.type == pygame.KEYDOWN:
                if e.key in (pygame.K_ESCAPE, pygame.K_q):
                    running = False
                if e.key == pygame.K_r:
                    solids, powerups, enemies, shooters, player, projectiles, cam, spawn_protect = reset_game()
                if e.key in (pygame.K_SPACE, pygame.K_w, pygame.K_UP):
                    jump = True
                if e.key == pygame.K_s:
                    shrink_pressed = True

        # Continuous input
        keys = pygame.key.get_pressed()
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            input_dir -= 1
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            input_dir += 1
        if keys[pygame.K_SPACE] or keys[pygame.K_w] or keys[pygame.K_UP]:
            jump = True

        # Update player
        player.update(dt, solids, input_dir, jump)

        # Powerup pickup (only when spawn_protect elapsed)
        if spawn_protect <= 0:
            for p in powerups[:]:
                if player.rect.colliderect(p.rect):
                    player.can_double_jump = True
                    powerups.remove(p)

        # Enemies: melee (red)
        for e in enemies:
            if player.rect.colliderect(e.rect):
                knock_dir = 1 if player.rect.centerx < e.rect.centerx else -1
                player.take_damage(10, (-knock_dir * 300, -400))

        # Shooting enemies + projectiles
        for s in shooters:
            s.update(dt, projectiles)
            if player.rect.colliderect(s.rect):
                knock_dir = 1 if player.rect.centerx < s.rect.centerx else -1
                player.take_damage(10, (-knock_dir * 300, -400))

        for proj in projectiles[:]:
            proj.update(dt)
            if proj.rect.colliderect(player.rect):
                player.take_damage(10, (300 if proj.direction < 0 else -300, -400))
                projectiles.remove(proj)
            elif proj.rect.y > HEIGHT + cam.y:
                projectiles.remove(proj)

        cam.update(player.rect)

        # ---------- Draw ----------
        screen.fill(BG_COLOR)
        for s in solids:
            s.draw(screen, cam)
        for e in enemies:
            e.draw(screen, cam)
        for s in shooters:
            s.draw(screen, cam)
        for proj in projectiles:
            proj.draw(screen, cam)
        for p in powerups:
            p.draw(screen, cam)
        player.draw(screen, cam)

        # --- UI ---
        pad = 10
        info = [
            f"FPS: {clock.get_fps():.0f}",
            "Move: ← → or A/D   Jump: Space/W/↑",
            "Reset: R   Quit: Esc or Q",
        ]
        for i, line in enumerate(info):
            screen.blit(font.render(line, True, (200, 200, 210)), (pad, pad + i * 18))

        # Health bar
        bar_w, bar_h = 200, 20
        bx, by = pad, pad + len(info) * 18 + 5
        pygame.draw.rect(screen, (100, 0, 0), (bx, by, bar_w, bar_h))
        ratio = player.health / player.max_health
        pygame.draw.rect(screen, (255, 0, 0), (bx, by, int(bar_w * ratio), bar_h))
        pygame.draw.rect(screen, (255, 255, 255), (bx, by, bar_w, bar_h), 2)

        pygame.display.flip()

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()