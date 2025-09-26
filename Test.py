import tkinter as tk

# Game window size
WINDOW_WIDTH = 800
WINDOW_HEIGHT = 600
rwretwretg = 5
# Player settings
PLAYER_WIDTH = 50
PLAYER_HEIGHT = 60
PLAYER_COLOR = "blue"
GRAVITY = 1
JUMP_STRENGTH = -20
MOVE_SPEED = 10

# Platform settings
PLATFORM_COLOR = "green"

class PlatformerGame:
    def __init__(self, root):
        self.root = root
        self.root.title("Platformer - No Pygame")
        self.canvas = tk.Canvas(root, width=WINDOW_WIDTH, height=WINDOW_HEIGHT, bg="white")
        self.canvas.pack()

        # Player setup
        self.player = self.canvas.create_rectangle(100, 500, 100 + PLAYER_WIDTH, 500 + PLAYER_HEIGHT, fill=PLAYER_COLOR)
        self.player_vel_y = 0
        self.on_ground = False

        # Platform setup
        self.platforms = []
        self.create_platform(0, WINDOW_HEIGHT - 40, WINDOW_WIDTH, 40)  # Ground
        self.create_platform(300, 450, 200, 20)
        self.create_platform(150, 300, 150, 20)
        self.create_platform(500, 200, 150, 20)

        # Input state
        self.left_pressed = False
        self.right_pressed = False

        # Key bindings
        self.root.bind("<KeyPress>", self.key_down)
        self.root.bind("<KeyRelease>", self.key_up)

        # Start game loop
        self.update()

    def create_platform(self, x, y, width, height):
        platform = self.canvas.create_rectangle(x, y, x + width, y + height, fill=PLATFORM_COLOR)
        self.platforms.append(platform)

    def key_down(self, event):
        if event.keysym == "Left":
            self.left_pressed = True
        elif event.keysym == "Right":
            self.right_pressed = True
        elif event.keysym == "Up":
            if self.on_ground:
                self.player_vel_y = JUMP_STRENGTH

    def key_up(self, event):
        if event.keysym == "Left":
            self.left_pressed = False
        elif event.keysym == "Right":
            self.right_pressed = False

    def update(self):
        # Horizontal movement
        dx = 0
        if self.left_pressed:
            dx -= MOVE_SPEED
        if self.right_pressed:
            dx += MOVE_SPEED
        self.canvas.move(self.player, dx, 0)

        # Apply gravity
        self.player_vel_y += GRAVITY
        self.canvas.move(self.player, 0, self.player_vel_y)

        # Collision detection
        self.on_ground = False
        player_coords = self.canvas.coords(self.player)
        for platform in self.platforms:
            platform_coords = self.canvas.coords(platform)
            if self.check_collision(player_coords, platform_coords):
                if self.player_vel_y >= 0:  # falling down
                    self.canvas.coords(self.player,
                        player_coords[0],
                        platform_coords[1] - PLAYER_HEIGHT,
                        player_coords[2],
                        platform_coords[1]
                    )
                    self.player_vel_y = 0
                    self.on_ground = True
                    break

        self.root.after(20, self.update)

    def check_collision(self, player, platform):
        # Simple AABB collision check
        px1, py1, px2, py2 = player
        fx1, fy1, fx2, fy2 = platform
        return (
            px2 > fx1 and
            px1 < fx2 and
            py2 >= fy1 and
            py1 < fy1
        )

# Run the game
root = tk.Tk()
game = PlatformerGame(root)
root.mainloop()
