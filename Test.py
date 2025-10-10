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
START_POS = (96, 96)

BG_COLOR = (28, 28, 40)
FG_COLOR = (230, 230, 230)
ACCENT = (120, 180, 255)
PLATFORM_COLOR = (70, 120, 160)
LADDER_COLOR = (150, 75, 0)

# -------------- Level data --------------
LEVEL_MAP = [
    "##--------------------------------------------------------------",
    "##--------------------------------------------------------------",
    "##----------------*--------------------------------------------",
    "##---------------###-------------------------------------------",
    "##------------------L#------------------------------------------",
    "##------------------L-------------------------------------------",
    "##------------------L-------------------------------------------",
    "##------------------L-------------------------------------------",
    "##-----------------####-------###-------------------------------",
    "##--------------------------------------------------------------",
    "##-------------#----------###-----------------------------------",
    "##-----------L#-------------------------###---------------------",
    "##-----------L--------------------------------------------------",
    "##------P----L--------------------------------------------------",
    "####################------###################---------##########",
    "####################------###################---------##########",
    "####################------###################---------##########",
]

TILE_SIZE = 48

# -------------- Helpers --------------
def rect_from_grid(x, y, w=1, h=1):
    return pygame.Rect(x * TILE_SIZE, y * TILE_SIZE, w * TILE_SIZE, h * TILE_SIZE)

# -------------- Game Objects --------------
class Platform(pygame.sprite.Sprite):
    def __init__(self, rect: pygame.Rect, is_ladder=False):
        super().__init__()
        self.rect = rect
        self.is_ladder = is_ladder

    def draw(self, surf, camera):
        r = self.rect.move(-camera.x, -camera.y)
        if not self.is_ladder:
            pygame.draw.rect(surf, PLATFORM_COLOR, r, border_radius=6)
        else:
            pygame.draw.rect(surf, LADDER_COLOR, r, border_radius=6)

class Player(pygame.sprite.Sprite):
    def __init__(self, pos):
        super().__init__()
        self.rect = pygame.Rect(pos[0], pos[1], *PLAYER_SIZE)
        self.vel = pygame.Vector2(0, 0)
        self.on_ground = False
        self.facing = 1
        self.can_double_jump = False
        self.has_double_jump = True
        self.jump_was_pressed = False
        self.is_colliding_ladder = False

        # Health
        self.max_health = 100
        self.health = self.max_health
        self.last_y = pos[1]

    def update(self, dt, solids, input_dir, jump_pressed):
        self.is_colliding_ladder = False
        probe = self.rect.inflate(6, 0)
        self.is_colliding_ladder = any(
            getattr(s, "is_ladder", False) and probe.colliderect(s.rect) for s in solids
        )

        # Horizontal movement
        target_speed = MOVE_SPEED * input_dir
        if not self.is_colliding_ladder and not self.on_ground:
            target_speed *= AIR_CONTROL

        accel = 5000.0
        if abs(target_speed - self.vel.x) < accel * dt:
            self.vel.x = target_speed
        else:
            self.vel.x += accel * dt * (1 if target_speed > self.vel.x else -1)

        if input_dir != 0:
            self.facing = 1 if input_dir > 0 else -1

        if not self.is_colliding_ladder:
            # Jump
            if jump_pressed and not self.jump_was_pressed:
                if self.on_ground:
                    self.vel.y = JUMP_VELOCITY
                    self.on_ground = False
                    self.has_double_jump = self.can_double_jump
                elif self.has_double_jump:
                    self.vel.y = JUMP_VELOCITY
                    self.has_double_jump = False

            # Gravity
            self.vel.y += GRAVITY * dt
            if self.vel.y > MAX_FALL_SPEED:
                self.vel.y = MAX_FALL_SPEED

            self.on_ground = False

        keys = pygame.key.get_pressed()
        if self.is_colliding_ladder:
            if keys[pygame.K_UP]:
                self.vel.y = -150
            else:
                self.vel.y = 150

        # X axis collisions
        self.rect.x += round(self.vel.x * dt)
        for s in solids:
            if self.rect.colliderect(s.rect) and not s.is_ladder:
                if self.vel.x > 0:
                    self.rect.right = s.rect.left
                elif self.vel.x < 0:
                    self.rect.left = s.rect.right
                self.vel.x = 0

        # Y axis collisions
        self.rect.y += round(self.vel.y * dt)
        for s in solids:
            if self.rect.colliderect(s.rect) and not s.is_ladder:
                if self.vel.y > 0:
                    self.rect.bottom = s.rect.top
                    self.on_ground = True
                    self.vel.y = 0
                    self.has_double_jump = True
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

    def draw(self, surf, camera):
        r = self.rect.move(-camera.x, -camera.y)
        pygame.draw.rect(surf, FG_COLOR, r, border_radius=8)
        eye_w, eye_h = 6, 8
        y = r.y + r.height // 3
        eye_x = r.centerx + (r.width // 4) * self.facing - (eye_w // 2)
        pygame.draw.rect(surf, ACCENT, (eye_x, y, eye_w, eye_h), border_radius=2)

class Powerup(pygame.sprite.Sprite):
    def __init__(self, rect: pygame.Rect):
        super().__init__()
        self.rect = rect

    def draw(self, surf, camera):
        r = self.rect.move(-camera.x, -camera.y)
        pygame.draw.ellipse(surf, (147, 112, 219), r)

# Level builder
def build_level(level_map):
    solids = []
    powerups = []
    player_start = START_POS
    h = len(level_map)
    w = max(len(row) for row in level_map)
    for y in range(h):
        for x in range(len(level_map[y])):
            ch = level_map[y][x]
            if ch == '#':
                solids.append(Platform(rect_from_grid(x, y)))
            elif ch == 'P':
                player_start = (x * TILE_SIZE, y * TILE_SIZE - (PLAYER_SIZE[1] - TILE_SIZE))
            elif ch == 'L':
                solids.append(Platform(rect_from_grid(x, y), True))
            elif ch == '*':
                powerups.append(Powerup(rect_from_grid(x, y, 1, 1)))
    return solids, powerups, player_start

# Camera
class Camera:
    def __init__(self):
        self.x = 0
        self.y = 0

    def update(self, target_rect):
        margin_x, margin_y = WIDTH * 0.35, HEIGHT * 0.4
        if target_rect.centerx - self.x < margin_x:
            self.x = target_rect.centerx - margin_x
        elif target_rect.centerx - self.x > WIDTH - margin_x:
            self.x = target_rect.centerx - (WIDTH - margin_x)
        if target_rect.centery - self.y < margin_y:
            self.y = target_rect.centery - margin_y
        elif target_rect.centery - self.y > HEIGHT - margin_y:
            self.y = target_rect.centery - (HEIGHT - margin_y)
        world_w = max(len(row) for row in LEVEL_MAP) * TILE_SIZE
        world_h = len(LEVEL_MAP) * TILE_SIZE
        self.x = max(0, min(self.x, world_w - WIDTH))
        self.y = max(0, min(self.y, world_h - HEIGHT))

# Main
def main():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption(TITLE)
    clock = pygame.time.Clock()
    font = pygame.font.SysFont("verdana", 16)

    solids, powerups, start = build_level(LEVEL_MAP)
    powerup_group = pygame.sprite.Group(powerups)
    player = Player(start)
    camera = Camera()
    solid_group = pygame.sprite.Group(solids)

    def reset():
        nonlocal player
        player = Player(start)

    running = True
    while running:
        dt = clock.tick(FPS) / 1000.0
        jump_pressed = False
        input_dir = 0

        # Events
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_ESCAPE, pygame.K_q):
                    running = False
                if event.key == pygame.K_r:
                    reset()
                if event.key in (pygame.K_SPACE, pygame.K_w, pygame.K_UP):
                    jump_pressed = True

        keys = pygame.key.get_pressed()
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            input_dir -= 1
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            input_dir += 1
        if keys[pygame.K_SPACE] or keys[pygame.K_w] or keys[pygame.K_UP]:
            jump_pressed = True

        # Update
        player.update(dt, solid_group, input_dir, jump_pressed)
        for p in powerups[:]:
            if player.rect.colliderect(p.rect):
                player.can_double_jump = True
                powerups.remove(p)
                powerup_group.remove(p)
        camera.update(player.rect)

        # Draw
        screen.fill(BG_COLOR)
        stripe_h = 80
        for i in range(0, HEIGHT // stripe_h + 2):
            y = i * stripe_h - int(camera.y * 0.15) % stripe_h
            pygame.draw.rect(screen, (24, 24, 34), (0, y, WIDTH, stripe_h), border_radius=0)

        for s in solids:
            s.draw(screen, camera)
        for p in powerups:
            p.draw(screen, camera)
        player.draw(screen, camera)

        # UI
        ui_pad = 10
        info = [
            f"FPS: {clock.get_fps():.0f}",
            "Move: ← → or A/D   Jump: Space/W/↑",
            "Reset: R   Quit: Esc or Q",
        ]
        for i, line in enumerate(info):
            text_surf = font.render(line, True, (200, 200, 210))
            screen.blit(text_surf, (ui_pad, ui_pad + i * 18))

        # Health bar under Reset/Quit
        bar_width = 200
        bar_height = 20
        bar_x = ui_pad
        bar_y = ui_pad + len(info) * 18 + 5
        pygame.draw.rect(screen, (100, 0, 0), (bar_x, bar_y, bar_width, bar_height))
        health_ratio = player.health / player.max_health
        pygame.draw.rect(screen, (255, 0, 0), (bar_x, bar_y, int(bar_width * health_ratio), bar_height))
        pygame.draw.rect(screen, (255, 255, 255), (bar_x, bar_y, bar_width, bar_height), 2)

        pygame.display.flip()

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()

