# src/settings.py

SCREEN_WIDTH = 1500
SCREEN_HEIGHT = 860
FPS = 60
GAME_TITLE = "VOID RUNNER"

BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
LIGHT_GRAY = (205, 205, 210)
GRAY = (120, 120, 130)
RED = (220, 40, 40)
DARK_GRAY = (28, 28, 36)

SMALL_FONT_SIZE = 16

DIFFICULTY_SETTINGS = {
    "EASY": {"obstacle_count": 3, "obstacle_speed": 3},
    "MEDIUM": {"obstacle_count": 4, "obstacle_speed": 4},
    "HARD": {"obstacle_count": 5, "obstacle_speed": 5},
}

OBSTACLE_SPEED_INCREMENT = 0.02
