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
LADDAR_COLOR = (150, 75, 0)

# -------------- Level data --------------
# Use simple ASCII tiles: '#' = solid, 'P' = player start, '-' = empty, 'L' = ladder, '*' = powerup
LEVEL_MAP = [
    "----------------------------------------------------------------",
    "----------------------------------------------------------------",
    "------------------*--------------------------------------------",
    "-----------------###--------------------------------------------",
    "----------------------------------------------------------------",
    "----------------------------------------------------------------",
    "--------------------L-------------------------------------------",
    "--------------------L-------------------------------------------",
    "-------------------####-------###-------------------------------",
    "----------------------------------------------------------------",
    "--------------##----------###-----------------------------------",
    "-------------L--------------------------###---------------------",
    "-------------L--------------------------------------------------",
    "--------P----L--------------------------------------------------",
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
            pygame.draw.rect(surf, LADDAR_COLOR, r, border_radius=6)

# class Laddar(Platform):
#     def __init__(self, rect: pygame.Rect):


class Player(pygame.sprite.Sprite):
    def __init__(self, pos):
        super().__init__()
        self.rect = pygame.Rect(pos[0], pos[1], *PLAYER_SIZE)
        self.vel = pygame.Vector2(0, 0)
        self.on_ground = False
        self.facing = 1  # 1 right, -1 left
        self.is_colliding_ladder = False
        self.can_double_jump = False
        self.has_double_jump = True
        self.jump_was_pressed = False


    def update(self, dt, solids, input_dir, jump_pressed):

        for s in solids:
            if self.rect.colliderect(s.rect) and s.is_ladder:
                is_colliding_ladder = True

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

        # ---- Jump (only on key press, no hold spam)
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
        if self.vel.y > MAX_FALL_SPEED:
            self.vel.y = MAX_FALL_SPEED

        # ---- Move & resolve collisions (separate axis)
        self.on_ground = False

        # X axis
        self.rect.x += round(self.vel.x * dt)
        for s in solids:
            if self.rect.colliderect(s.rect):
                if self.vel.x > 0:
                    self.rect.right = s.rect.left
                elif self.vel.x < 0:
                    self.rect.left = s.rect.right
                self.vel.x = 0

        # Y axis
        self.rect.y += round(self.vel.y * dt)
        for s in solids:
            if self.rect.colliderect(s.rect):
                if self.vel.y > 0:
                    self.rect.bottom = s.rect.top
                    self.on_ground = True
                    self.vel.y = 0
                    self.has_double_jump = True  # reset on landing
                elif self.vel.y < 0:
                    self.rect.top = s.rect.bottom
                    self.vel.y = 0

        # ---- Update key state (for edge detection)
        self.jump_was_pressed = jump_pressed


    def draw(self, surf, camera):
        r = self.rect.move(-camera.x, -camera.y)
        # body
        pygame.draw.rect(surf, FG_COLOR, r, border_radius=8)
        # face accent
        eye_w = 6
        eye_h = 8
        y = r.y + r.height // 3
        eye_x = r.centerx + (r.width // 4) * self.facing - (eye_w // 2)
        pygame.draw.rect(surf, ACCENT, (eye_x, y, eye_w, eye_h), border_radius=2)

class Powerup(pygame.sprite.Sprite):
    def __init__(self, rect: pygame.Rect):
        super().__init__()
        self.rect = rect

    def draw(self, surf, camera):
        r = self.rect.move(-camera.x, -camera.y)
        pygame.draw.ellipse(surf, (255, 200, 50), r)  # gold orb


# -------------- Level builder --------------
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


# -------------- Main --------------
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

    # Turn platforms into a sprite group for easy iteration/draw
    solid_group = pygame.sprite.Group(solids)

    def reset():
        nonlocal player
        player = Player(start)

    running = True
    while running:
        dt = clock.tick(FPS) / 1000.0  # seconds
        jump_pressed = False
        input_dir = 0

        # ---------- Events ----------
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

        # Continuous input
        keys = pygame.key.get_pressed()
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            input_dir -= 1
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            input_dir += 1
        if keys[pygame.K_SPACE] or keys[pygame.K_w] or keys[pygame.K_UP]:
            jump_pressed = True

        # ---------- Update ----------
        player.update(dt, solid_group, input_dir, jump_pressed)
        # Check powerup collisions
        for p in powerups[:]:
            if player.rect.colliderect(p.rect):
                player.can_double_jump = True
                powerups.remove(p)
                powerup_group.remove(p)
        camera.update(player.rect)

        # ---------- Draw ----------
        screen.fill(BG_COLOR)


        # Parallax-ish background stripes (cheap depth)
        stripe_h = 80
        for i in range(0, HEIGHT // stripe_h + 2):
            y = i * stripe_h - int(camera.y * 0.15) % stripe_h
            pygame.draw.rect(screen, (24, 24, 34), (0, y, WIDTH, stripe_h), border_radius=0)

        # Platforms
        for s in solids:
            s.draw(screen, camera)

        #Powerups
        for p in powerups:
            p.draw(screen, camera)

        # Player
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

        pygame.display.flip()

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()