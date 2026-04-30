# src/screens.py

import pygame
from src import settings as S

SCREEN_WIDTH = getattr(S, "SCREEN_WIDTH", 1280)
SCREEN_HEIGHT = getattr(S, "SCREEN_HEIGHT", 720)
BLACK = getattr(S, "BLACK", (0, 0, 0))
WHITE = getattr(S, "WHITE", (255, 255, 255))
LIGHT_GRAY = getattr(S, "LIGHT_GRAY", (205, 205, 210))
RED = getattr(S, "RED", (220, 40, 40))


def font(size, bold=False):
    return pygame.font.SysFont("arial", size, bold=bold)


def draw_text(surface, text, size, x, y, color, center=True, bold=False):
    img = font(size, bold).render(text, True, color)
    rect = img.get_rect()
    if center:
        rect.center = (x, y)
    else:
        rect.topleft = (x, y)
    surface.blit(img, rect)
    return rect


def draw_background(surface):
    t = pygame.time.get_ticks() * 0.001

    # Deep vertical gradient background.
    for y in range(SCREEN_HEIGHT):
        k = y / max(1, SCREEN_HEIGHT - 1)
        r = int(4 + 10 * k)
        g = int(5 + 6 * k)
        b = int(12 + 18 * k)
        pygame.draw.line(surface, (r, g, b), (0, y), (SCREEN_WIDTH, y))

    # Soft central glow behind the menu stack.
    glow = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
    center_x = SCREEN_WIDTH // 2
    center_y = SCREEN_HEIGHT // 2 - 18
    pulse = 0.72 + 0.28 * ((pygame.math.Vector2(1, 0).rotate(t * 48).x + 1) / 2)
    pygame.draw.circle(glow, (44, 14, 28, int(58 * pulse)), (center_x, center_y), 250)
    pygame.draw.circle(glow, (80, 20, 28, int(34 * pulse)), (center_x, center_y - 10), 165)
    pygame.draw.circle(glow, (36, 110, 255, 14), (center_x, center_y + 42), 118)
    surface.blit(glow, (0, 0))

    # Futuristic grid near the bottom.
    horizon_y = SCREEN_HEIGHT - 150
    grid = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
    pygame.draw.line(grid, (65, 65, 82, 60), (90, horizon_y), (SCREEN_WIDTH - 90, horizon_y), 1)
    for i in range(-8, 9):
        x = center_x + i * 86
        pygame.draw.line(grid, (38, 38, 54, 48), (center_x, horizon_y), (x, SCREEN_HEIGHT), 1)
    for j in range(1, 8):
        yy = horizon_y + int((j / 8) ** 1.7 * 220)
        pygame.draw.line(grid, (34, 34, 48, max(15, 55 - j * 5)), (110, yy), (SCREEN_WIDTH - 110, yy), 1)
    surface.blit(grid, (0, 0))

    # Floating cyber particles / red data nodes.
    for i in range(18):
        px = int((i * 97 + t * (16 + (i % 4) * 6)) % (SCREEN_WIDTH + 160)) - 80
        py = int((i * 59 + t * (10 + (i % 3) * 4)) % (SCREEN_HEIGHT + 180)) - 90
        size = 2 + (i % 3)
        tail = 18 + (i % 5) * 12
        alpha = 60 + (i % 4) * 20
        particle = pygame.Surface((30, tail + 24), pygame.SRCALPHA)
        pygame.draw.line(particle, (140, 18, 30, alpha // 2), (15, 0), (15, tail), 1)
        pygame.draw.rect(particle, (135, 20, 30, alpha), (15 - size, tail - size, size * 2 + 1, size * 2 + 1), border_radius=2)
        surface.blit(particle, (px - 15, py - 8))

    # Tiny stars / ambient dots.
    for i in range(26):
        sx = int((i * 141 + t * (6 + i % 5)) % SCREEN_WIDTH)
        sy = int((i * 83 + (i % 4) * 37) % SCREEN_HEIGHT)
        twinkle = 105 + int(70 * ((pygame.math.Vector2(1, 0).rotate(t * 70 + i * 17).x + 1) / 2))
        surface.fill((170, 185, 255, twinkle), ((sx, sy), (2, 2)), special_flags=pygame.BLEND_RGBA_ADD)

    # Decorative footer line.
    pygame.draw.line(surface, (54, 56, 72), (120, SCREEN_HEIGHT - 86), (SCREEN_WIDTH - 120, SCREEN_HEIGHT - 86), 1)


class Button:
    def __init__(self, x, y, w, h, text, action):
        self.rect = pygame.Rect(x, y, w, h)
        self.text = text
        self.action = action
        self.hovered = False

    def update(self, mouse_pos):
        self.hovered = self.rect.collidepoint(mouse_pos)

    def draw(self, surface):
        fill_color = (22, 22, 30) if not self.hovered else (32, 14, 20)
        border_color = (84, 84, 98) if not self.hovered else RED
        pygame.draw.rect(surface, fill_color, self.rect, border_radius=16)
        pygame.draw.rect(surface, border_color, self.rect, 2, border_radius=16)
        draw_text(surface, self.text, 22, self.rect.centerx, self.rect.centery, WHITE, bold=True)

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and self.rect.collidepoint(event.pos):
            return self.action
        return None


class BaseMenuScreen:
    def __init__(self, title, subtitle=""):
        self.title = title
        self.subtitle = subtitle
        self.buttons = []

    def update(self, mouse_pos):
        for button in self.buttons:
            button.update(mouse_pos)

    def handle_event(self, event):
        for button in self.buttons:
            action = button.handle_event(event)
            if action:
                return action
        return None

    def draw_header(self, surface):
        draw_background(surface)
        draw_text(surface, self.title, 64, SCREEN_WIDTH // 2, 118, WHITE, bold=True)
        pygame.draw.line(surface, RED, (SCREEN_WIDTH // 2 - 88, 176), (SCREEN_WIDTH // 2 - 18, 176), 3)
        pygame.draw.circle(surface, RED, (SCREEN_WIDTH // 2, 176), 4)
        pygame.draw.line(surface, RED, (SCREEN_WIDTH // 2 + 18, 176), (SCREEN_WIDTH // 2 + 88, 176), 3)
        if self.subtitle:
            draw_text(surface, self.subtitle, 21, SCREEN_WIDTH // 2, 198, LIGHT_GRAY)

    def draw(self, surface):
        self.draw_header(surface)
        for button in self.buttons:
            button.draw(surface)


class HomeScreen(BaseMenuScreen):
    def __init__(self):
        super().__init__("VOID RUNNER", "Dodge red enemies, collect blue gems, survive longer.")
        bx, by, bw, bh, gap = SCREEN_WIDTH // 2 - 190, 266, 380, 62, 18
        labels = [
            ("PLAY", "PLAY"),
            ("HOW TO PLAY", "HOW_TO_PLAY"),
            ("SETTINGS", "SETTINGS"),
            ("SKINS", "SKINS"),
            ("EXIT", "EXIT"),
        ]
        self.buttons = [Button(bx, by + i * (bh + gap), bw, bh, label, action) for i, (label, action) in enumerate(labels)]


class HowToPlayScreen(BaseMenuScreen):
    def __init__(self):
        super().__init__("HOW TO PLAY", "Simple controls, clean survival gameplay.")
        self.back_button = Button(SCREEN_WIDTH // 2 - 160, SCREEN_HEIGHT - 120, 320, 58, "BACK", "BACK")
        self.buttons = [self.back_button]

    def draw(self, surface):
        self.draw_header(surface)
        panel = pygame.Rect(SCREEN_WIDTH // 2 - 310, 246, 620, 270)
        pygame.draw.rect(surface, (15, 15, 22), panel, border_radius=18)
        pygame.draw.rect(surface, (75, 75, 88), panel, 2, border_radius=18)
        lines = [
            "Move with WASD or Arrow Keys.",
            "Collect blue diamonds to earn more score.",
            "Avoid red enemy blocks at all costs.",
            "Press P or ESC to pause the game.",
            "Press M to mute/unmute background music.",
            "Press F11 to toggle fullscreen.",
        ]
        start_y = 286
        for i, line in enumerate(lines):
            pygame.draw.circle(surface, (80, 190, 255), (SCREEN_WIDTH // 2 - 248, start_y + i * 34), 5)
            draw_text(surface, line, 24, SCREEN_WIDTH // 2 - 228, start_y - 11 + i * 34, WHITE, center=False)
        self.back_button.draw(surface)


class SettingsScreen(BaseMenuScreen):
    def __init__(self):
        super().__init__("SETTINGS", "Basic options for the game.")
        self.sound_on = True
        self.fullscreen_on = False
        self.difficulties = ["EASY", "NORMAL", "HARD"]
        self.difficulty_index = 1
        self._build_buttons()

    def _build_buttons(self):
        bx, by, bw, bh, gap = SCREEN_WIDTH // 2 - 190, 286, 380, 62, 22
        self.buttons = [
            Button(bx, by, bw, bh, f"SOUND: {'ON' if self.sound_on else 'OFF'}", "TOGGLE_SOUND"),
            Button(bx, by + (bh + gap), bw, bh, f"FULLSCREEN: {'ON' if self.fullscreen_on else 'OFF'}", "TOGGLE_FULLSCREEN"),
            Button(bx, by + 2 * (bh + gap), bw, bh, f"DIFFICULTY: {self.difficulties[self.difficulty_index]}", "CHANGE_DIFFICULTY"),
            Button(bx, by + 4 * (bh + gap), bw, bh, "BACK", "BACK"),
        ]

    def update(self, mouse_pos):
        self._build_buttons()
        super().update(mouse_pos)

    def handle_event(self, event):
        self._build_buttons()
        action = super().handle_event(event)
        if action == "TOGGLE_SOUND":
            self.sound_on = not self.sound_on
        elif action == "TOGGLE_FULLSCREEN":
            self.fullscreen_on = not self.fullscreen_on
        elif action == "CHANGE_DIFFICULTY":
            self.difficulty_index = (self.difficulty_index + 1) % len(self.difficulties)
        return action


class PauseScreen(BaseMenuScreen):
    def __init__(self):
        super().__init__("PAUSED", "Take a breath. Jump back in when ready.")
        bx, by, bw, bh, gap = SCREEN_WIDTH // 2 - 190, 280, 380, 60, 18
        labels = [("RESUME", "RESUME"), ("RESTART", "RESTART"), ("HOME", "HOME"), ("EXIT", "EXIT")]
        self.buttons = [Button(bx, by + i * (bh + gap), bw, bh, label, action) for i, (label, action) in enumerate(labels)]

    def draw(self, surface):
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 155))
        surface.blit(overlay, (0, 0))
        panel = pygame.Rect(SCREEN_WIDTH // 2 - 250, 120, 500, 500)
        pygame.draw.rect(surface, (10, 10, 16), panel, border_radius=22)
        pygame.draw.rect(surface, (85, 85, 98), panel, 2, border_radius=22)
        draw_text(surface, self.title, 58, SCREEN_WIDTH // 2, 182, WHITE, bold=True)
        draw_text(surface, self.subtitle, 21, SCREEN_WIDTH // 2, 218, LIGHT_GRAY)
        for button in self.buttons:
            button.draw(surface)


class GameOverScreen(BaseMenuScreen):
    def __init__(self):
        super().__init__("GAME OVER", "The void got you this time.")
        bx, by, bw, bh, gap = SCREEN_WIDTH // 2 - 190, 362, 380, 60, 18
        labels = [("RETRY", "RETRY"), ("HOME", "HOME"), ("EXIT", "EXIT")]
        self.buttons = [Button(bx, by + i * (bh + gap), bw, bh, label, action) for i, (label, action) in enumerate(labels)]

    def draw(self, surface, score, best_score):
        draw_background(surface)
        draw_text(surface, self.title, 66, SCREEN_WIDTH // 2, 128, WHITE, bold=True)
        draw_text(surface, self.subtitle, 22, SCREEN_WIDTH // 2, 168, LIGHT_GRAY)
        score_panel = pygame.Rect(SCREEN_WIDTH // 2 - 220, 214, 440, 104)
        pygame.draw.rect(surface, (16, 16, 22), score_panel, border_radius=18)
        pygame.draw.rect(surface, (78, 78, 90), score_panel, 2, border_radius=18)
        draw_text(surface, f"SCORE: {score}", 30, SCREEN_WIDTH // 2, 248, WHITE, bold=True)
        draw_text(surface, f"BEST: {best_score}", 24, SCREEN_WIDTH // 2, 287, (80, 190, 255), bold=True)
        for button in self.buttons:
            button.draw(surface)


class SkinsScreen:
    def __init__(self, skin_palette, selected_skin="WHITE"):
        self.skin_palette = skin_palette
        self.selected_skin = selected_skin
        self.back_button = Button(SCREEN_WIDTH // 2 - 150, SCREEN_HEIGHT - 86, 300, 52, "BACK", "BACK")
        self.card_rects = {}
        self.hovered_skin = None
        self._build_cards()

    def _build_cards(self):
        self.card_rects = {}
        keys = list(self.skin_palette.keys())
        card_w = 150
        card_h = 142
        gap = 22
        columns = 4
        total_w = card_w * columns + gap * (columns - 1)
        start_x = SCREEN_WIDTH // 2 - total_w // 2
        start_y = 232

        for i, key in enumerate(keys):
            row = i // columns
            col = i % columns
            x = start_x + col * (card_w + gap)
            y = start_y + row * (card_h + gap)
            self.card_rects[key] = pygame.Rect(x, y, card_w, card_h)

    def update(self, mouse_pos):
        self.hovered_skin = None
        for key, rect in self.card_rects.items():
            if rect.collidepoint(mouse_pos):
                self.hovered_skin = key

        self.back_button.update(mouse_pos)

    def handle_event(self, event):
        action = self.back_button.handle_event(event)
        if action:
            return action

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for key, rect in self.card_rects.items():
                if rect.collidepoint(event.pos):
                    self.selected_skin = key
                    return ("SELECT_SKIN", key)

        return None

    def draw_preview(self, surface, palette, cx, cy):
        fill = palette["fill"]
        glow = palette["glow"]
        accent = palette.get("accent", WHITE)
        style = palette.get("style", "orb")

        pygame.draw.circle(surface, glow, (cx, cy), 31)
        pygame.draw.circle(surface, fill, (cx, cy), 22)

        if style == "smile":
            pygame.draw.circle(surface, (35, 28, 22), (cx - 7, cy - 4), 3)
            pygame.draw.circle(surface, (35, 28, 22), (cx + 7, cy - 4), 3)
            pygame.draw.arc(surface, (35, 28, 22), pygame.Rect(cx - 10, cy - 4, 20, 16), 0.3, 2.8, 2)

        elif style == "speedster":
            bolt = [
                (cx - 2, cy - 19),
                (cx + 12, cy - 2),
                (cx + 5, cy - 2),
                (cx + 13, cy + 18),
                (cx - 12, cy - 4),
                (cx - 2, cy - 4),
            ]
            pygame.draw.polygon(surface, accent, bolt)

        elif style == "fire":
            flame = [
                (cx, cy - 18),
                (cx + 11, cy - 4),
                (cx + 7, cy + 15),
                (cx, cy + 8),
                (cx - 8, cy + 15),
                (cx - 11, cy - 4),
            ]
            pygame.draw.polygon(surface, accent, flame)

        pygame.draw.circle(surface, WHITE, (cx - 7, cy - 8), 4)
        pygame.draw.circle(surface, (245, 245, 255), (cx, cy), 22, 2)

    def draw(self, surface):
        draw_background(surface)
        draw_text(surface, "SKINS", 64, SCREEN_WIDTH // 2, 100, WHITE, bold=True)
        draw_text(surface, "Pick a skin. The trail uses the same color while you move.", 22, SCREEN_WIDTH // 2, 146, LIGHT_GRAY)

        for key, rect in self.card_rects.items():
            palette = self.skin_palette[key]
            hovered = self.hovered_skin == key
            active = self.selected_skin == key

            fill = (16, 16, 22) if not hovered else (23, 23, 32)
            border = palette["glow"] if active else ((100, 100, 112) if not hovered else WHITE)
            border_width = 4 if active else 2

            pygame.draw.rect(surface, fill, rect, border_radius=18)
            pygame.draw.rect(surface, border, rect, border_width, border_radius=18)

            cx = rect.centerx
            cy = rect.y + 48

            self.draw_preview(surface, palette, cx, cy)

            draw_text(surface, palette["name"], 17, cx, rect.y + 92, WHITE, bold=True)

            if active:
                badge = pygame.Rect(rect.centerx - 46, rect.bottom - 30, 92, 22)
                pygame.draw.rect(surface, palette["glow"], badge, border_radius=11)
                draw_text(surface, "ACTIVE", 14, badge.centerx, badge.centery, BLACK, bold=True)
            else:
                draw_text(surface, "CLICK", 14, cx, rect.bottom - 19, LIGHT_GRAY, bold=True)

        self.back_button.draw(surface)
