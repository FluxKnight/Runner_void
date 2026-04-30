# src/screens.py

import math
import pygame
from src import settings as S

SCREEN_WIDTH = getattr(S, "SCREEN_WIDTH", 1500)
SCREEN_HEIGHT = getattr(S, "SCREEN_HEIGHT", 860)
BLACK = getattr(S, "BLACK", (0, 0, 0))
WHITE = getattr(S, "WHITE", (255, 255, 255))
LIGHT_GRAY = getattr(S, "LIGHT_GRAY", (205, 205, 210))
RED = getattr(S, "RED", (220, 40, 40))


def font(size, bold=False):
    return pygame.font.SysFont("arial", size, bold=bold)


def draw_text(surface, text, size, x, y, color, center=True, bold=False):
    img = font(size, bold).render(str(text), True, color)
    rect = img.get_rect()
    if center:
        rect.center = (x, y)
    else:
        rect.topleft = (x, y)
    surface.blit(img, rect)
    return rect


def draw_background(surface):
    t = pygame.time.get_ticks() * 0.001

    for y in range(SCREEN_HEIGHT):
        k = y / max(1, SCREEN_HEIGHT - 1)
        r = int(3 + 12 * k)
        g = int(4 + 8 * k)
        b = int(11 + 22 * k)
        pygame.draw.line(surface, (r, g, b), (0, y), (SCREEN_WIDTH, y))

    glow = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
    cx = SCREEN_WIDTH // 2
    cy = SCREEN_HEIGHT // 2 - 18
    pulse = 0.72 + 0.28 * ((math.sin(t * 1.4) + 1) / 2)
    pygame.draw.circle(glow, (44, 14, 28, int(58 * pulse)), (cx, cy), 300)
    pygame.draw.circle(glow, (80, 20, 28, int(34 * pulse)), (cx, cy - 10), 200)
    pygame.draw.circle(glow, (36, 110, 255, 18), (cx, cy + 42), 145)
    surface.blit(glow, (0, 0))

    horizon_y = SCREEN_HEIGHT - 150
    grid = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
    pygame.draw.line(grid, (65, 65, 82, 60), (90, horizon_y), (SCREEN_WIDTH - 90, horizon_y), 1)

    for i in range(-10, 11):
        x = cx + i * 96
        pygame.draw.line(grid, (38, 38, 54, 48), (cx, horizon_y), (x, SCREEN_HEIGHT), 1)

    for j in range(1, 8):
        yy = horizon_y + int((j / 8) ** 1.7 * 240)
        pygame.draw.line(grid, (34, 34, 48, max(15, 55 - j * 5)), (110, yy), (SCREEN_WIDTH - 110, yy), 1)

    surface.blit(grid, (0, 0))

    for i in range(26):
        px = int((i * 97 + t * (16 + (i % 4) * 6)) % (SCREEN_WIDTH + 160)) - 80
        py = int((i * 59 + t * (10 + (i % 3) * 4)) % (SCREEN_HEIGHT + 180)) - 90
        size = 2 + (i % 3)
        tail = 18 + (i % 5) * 12
        alpha = 60 + (i % 4) * 20
        particle = pygame.Surface((30, tail + 24), pygame.SRCALPHA)
        pygame.draw.line(particle, (140, 18, 30, alpha // 2), (15, 0), (15, tail), 1)
        pygame.draw.rect(particle, (135, 20, 30, alpha), (15 - size, tail - size, size * 2 + 1, size * 2 + 1), border_radius=2)
        surface.blit(particle, (px - 15, py - 8))

    for i in range(34):
        sx = int((i * 141 + t * (6 + i % 5)) % SCREEN_WIDTH)
        sy = int((i * 83 + (i % 4) * 37) % SCREEN_HEIGHT)
        twinkle = 105 + int(70 * ((math.sin(t * 2 + i) + 1) / 2))
        dot = pygame.Surface((2, 2), pygame.SRCALPHA)
        dot.fill((170, 185, 255, twinkle))
        surface.blit(dot, (sx, sy))

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


class TextInput:
    def __init__(self, x, y, w, h, placeholder="", password=False):
        self.rect = pygame.Rect(x, y, w, h)
        self.placeholder = placeholder
        self.password = password
        self.text = ""
        self.active = False

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self.active = self.rect.collidepoint(event.pos)

        if event.type == pygame.KEYDOWN and self.active:
            if event.key == pygame.K_BACKSPACE:
                self.text = self.text[:-1]
            elif event.key == pygame.K_RETURN:
                return "ENTER"
            elif len(self.text) < 24 and event.unicode and event.unicode.isprintable():
                self.text += event.unicode

        return None

    def draw(self, surface):
        border = (80, 190, 255) if self.active else (84, 84, 98)
        fill = (13, 13, 20)
        pygame.draw.rect(surface, fill, self.rect, border_radius=12)
        pygame.draw.rect(surface, border, self.rect, 2, border_radius=12)

        shown = self.text
        if self.password:
            shown = "*" * len(self.text)

        if shown:
            draw_text(surface, shown, 22, self.rect.x + 16, self.rect.y + 13, WHITE, center=False)
        else:
            draw_text(surface, self.placeholder, 20, self.rect.x + 16, self.rect.y + 15, (120, 120, 132), center=False)


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
        draw_text(surface, self.title, 64, SCREEN_WIDTH // 2, 112, WHITE, bold=True)
        pygame.draw.line(surface, RED, (SCREEN_WIDTH // 2 - 88, 170), (SCREEN_WIDTH // 2 - 18, 170), 3)
        pygame.draw.circle(surface, RED, (SCREEN_WIDTH // 2, 170), 4)
        pygame.draw.line(surface, RED, (SCREEN_WIDTH // 2 + 18, 170), (SCREEN_WIDTH // 2 + 88, 170), 3)
        if self.subtitle:
            draw_text(surface, self.subtitle, 21, SCREEN_WIDTH // 2, 194, LIGHT_GRAY)

    def draw(self, surface):
        self.draw_header(surface)
        for button in self.buttons:
            button.draw(surface)


class LoginScreen:
    def __init__(self):
        bx = SCREEN_WIDTH // 2 - 220
        self.username_input = TextInput(bx, 290, 440, 56, "Username")
        self.password_input = TextInput(bx, 362, 440, 56, "Password", password=True)
        self.login_button = Button(bx, 444, 440, 58, "LOGIN", "LOGIN")
        self.create_button = Button(bx + 92, 518, 256, 42, "CREATE ACCOUNT", "CREATE_ACCOUNT")
        self.exit_button = Button(bx + 140, 574, 160, 42, "EXIT", "EXIT")
        self.message = ""

    @property
    def username(self):
        return self.username_input.text

    @property
    def password(self):
        return self.password_input.text

    def clear(self):
        self.username_input.text = ""
        self.password_input.text = ""
        self.message = ""

    def update(self, mouse_pos):
        self.login_button.update(mouse_pos)
        self.create_button.update(mouse_pos)
        self.exit_button.update(mouse_pos)

    def handle_event(self, event):
        enter1 = self.username_input.handle_event(event)
        enter2 = self.password_input.handle_event(event)
        if enter1 == "ENTER" or enter2 == "ENTER":
            return "LOGIN"

        for button in (self.login_button, self.create_button, self.exit_button):
            action = button.handle_event(event)
            if action:
                return action
        return None

    def draw(self, surface):
        draw_background(surface)
        draw_text(surface, "VOID RUNNER", 68, SCREEN_WIDTH // 2, 120, WHITE, bold=True)
        draw_text(surface, "Login to save gems, ranks, skins and guns.", 23, SCREEN_WIDTH // 2, 178, LIGHT_GRAY)

        panel = pygame.Rect(SCREEN_WIDTH // 2 - 280, 235, 560, 390)
        pygame.draw.rect(surface, (10, 10, 16), panel, border_radius=22)
        pygame.draw.rect(surface, (80, 80, 98), panel, 2, border_radius=22)

        self.username_input.draw(surface)
        self.password_input.draw(surface)
        self.login_button.draw(surface)
        self.create_button.draw(surface)
        self.exit_button.draw(surface)

        if self.message:
            color = (255, 110, 110) if "wrong" in self.message.lower() or "not" in self.message.lower() else (120, 255, 170)
            draw_text(surface, self.message, 19, SCREEN_WIDTH // 2, 645, color, bold=True)


class CreateAccountScreen:
    def __init__(self):
        bx = SCREEN_WIDTH // 2 - 230
        self.username_input = TextInput(bx, 265, 460, 54, "Username")
        self.password_input = TextInput(bx, 335, 460, 54, "Password", password=True)
        self.confirm_input = TextInput(bx, 405, 460, 54, "Confirm password", password=True)
        self.create_button = Button(bx, 486, 460, 58, "CREATE ACCOUNT", "CREATE")
        self.back_button = Button(bx + 120, 560, 220, 46, "BACK", "BACK")
        self.message = ""

    @property
    def username(self):
        return self.username_input.text

    @property
    def password(self):
        return self.password_input.text

    @property
    def confirm_password(self):
        return self.confirm_input.text

    def clear(self):
        self.username_input.text = ""
        self.password_input.text = ""
        self.confirm_input.text = ""
        self.message = ""

    def update(self, mouse_pos):
        self.create_button.update(mouse_pos)
        self.back_button.update(mouse_pos)

    def handle_event(self, event):
        enter = None
        for field in (self.username_input, self.password_input, self.confirm_input):
            if field.handle_event(event) == "ENTER":
                enter = "CREATE"
        if enter:
            return enter

        for button in (self.create_button, self.back_button):
            action = button.handle_event(event)
            if action:
                return action
        return None

    def draw(self, surface):
        draw_background(surface)
        draw_text(surface, "CREATE ACCOUNT", 58, SCREEN_WIDTH // 2, 118, WHITE, bold=True)
        draw_text(surface, "Your account is saved locally on this computer.", 22, SCREEN_WIDTH // 2, 170, LIGHT_GRAY)

        panel = pygame.Rect(SCREEN_WIDTH // 2 - 300, 220, 600, 420)
        pygame.draw.rect(surface, (10, 10, 16), panel, border_radius=22)
        pygame.draw.rect(surface, (80, 80, 98), panel, 2, border_radius=22)

        self.username_input.draw(surface)
        self.password_input.draw(surface)
        self.confirm_input.draw(surface)
        self.create_button.draw(surface)
        self.back_button.draw(surface)

        if self.message:
            color = (255, 110, 110) if "must" in self.message.lower() or "match" in self.message.lower() or "exists" in self.message.lower() else (120, 255, 170)
            draw_text(surface, self.message, 19, SCREEN_WIDTH // 2, 660, color, bold=True)


class HomeScreen(BaseMenuScreen):
    def __init__(self):
        super().__init__("VOID RUNNER", "Arcade shooter: simple WASD movement, auto-target shooting.")
        bx, by, bw, bh, gap = SCREEN_WIDTH // 2 - 190, 240, 380, 56, 13
        labels = [
            ("PLAY", "PLAY"),
            ("SHOP", "SHOP"),
            ("RANKS", "RANKS"),
            ("HOW TO PLAY", "HOW_TO_PLAY"),
            ("SETTINGS", "SETTINGS"),
            ("EXIT", "EXIT"),
        ]
        self.profile_button = Button(SCREEN_WIDTH - 202, 28, 168, 46, "PROFILE", "PROFILE")
        self.buttons = [Button(bx, by + i * (bh + gap), bw, bh, label, action) for i, (label, action) in enumerate(labels)]
        self.buttons.append(self.profile_button)

    def draw(self, surface, display_name="Player", server_online=False, server_url=""):
        self.draw_header(surface)
        draw_text(surface, f"Welcome, {display_name}", 22, SCREEN_WIDTH // 2, 220, (255, 230, 120), bold=True)

        status = "SERVER: GLOBAL ONLINE" if server_online else "SERVER: CONNECTING / OFFLINE"
        status_color = (120, 255, 170) if server_online else (255, 170, 90)
        draw_text(surface, status, 17, 26, 92, status_color, center=False, bold=True)
        draw_text(surface, server_url, 13, 26, 116, LIGHT_GRAY, center=False)

        for button in self.buttons:
            button.draw(surface)


class HowToPlayScreen(BaseMenuScreen):
    def __init__(self):
        super().__init__("HOW TO PLAY", "Adventure shooter controls.")
        self.back_button = Button(SCREEN_WIDTH // 2 - 160, SCREEN_HEIGHT - 112, 320, 58, "BACK", "BACK")
        self.buttons = [self.back_button]

    def draw(self, surface):
        self.draw_header(surface)
        panel = pygame.Rect(SCREEN_WIDTH // 2 - 390, 230, 780, 330)
        pygame.draw.rect(surface, (15, 15, 22), panel, border_radius=18)
        pygame.draw.rect(surface, (75, 75, 88), panel, 2, border_radius=18)

        lines = [
            "Simple movement: W up, S down, A left, D right.",
            "Gameplay hides and locks the mouse cursor inside the window.",
            "Gun auto-targets the nearest zombie. SPACE / Click also shoots.",
            "Each level has a fixed zombie and boss count.",
            "LV1 starts with 100 zombies and 4 bosses.",
            "Every new level adds +50 zombies and +3 bosses.",
            "After clearing a level, a cinematic ship scene starts.",
        ]

        start_y = 270
        for i, line in enumerate(lines):
            pygame.draw.circle(surface, (80, 190, 255), (SCREEN_WIDTH // 2 - 330, start_y + i * 36), 5)
            draw_text(surface, line, 22, SCREEN_WIDTH // 2 - 312, start_y - 11 + i * 36, WHITE, center=False)

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
        super().__init__("GAME OVER", "The zombies got you this time.")
        bx, by, bw, bh, gap = SCREEN_WIDTH // 2 - 190, 380, 380, 60, 18
        labels = [("RETRY", "RETRY"), ("HOME", "HOME"), ("EXIT", "EXIT")]
        self.buttons = [Button(bx, by + i * (bh + gap), bw, bh, label, action) for i, (label, action) in enumerate(labels)]

    def update(self, mouse_pos, wallet_gems=0):
        super().update(mouse_pos)

    def draw(self, surface, score, best_score, run_gems, wallet_gems):
        draw_background(surface)
        draw_text(surface, self.title, 66, SCREEN_WIDTH // 2, 112, WHITE, bold=True)
        draw_text(surface, self.subtitle, 22, SCREEN_WIDTH // 2, 152, LIGHT_GRAY)

        score_panel = pygame.Rect(SCREEN_WIDTH // 2 - 240, 198, 480, 134)
        pygame.draw.rect(surface, (16, 16, 22), score_panel, border_radius=18)
        pygame.draw.rect(surface, (78, 78, 90), score_panel, 2, border_radius=18)
        draw_text(surface, f"SCORE: {score}", 30, SCREEN_WIDTH // 2, 230, WHITE, bold=True)
        draw_text(surface, f"BEST: {best_score}", 23, SCREEN_WIDTH // 2, 266, (80, 190, 255), bold=True)
        draw_text(surface, f"RUN GEMS: +{run_gems}   WALLET: {wallet_gems}", 22, SCREEN_WIDTH // 2, 302, (255, 220, 90), bold=True)

        for button in self.buttons:
            button.draw(surface)


class ProfileScreen:
    def __init__(self):
        self.display_input = TextInput(SCREEN_WIDTH // 2 - 220, 320, 440, 56, "Display name")
        self.save_button = Button(SCREEN_WIDTH // 2 - 220, 398, 440, 56, "SAVE DISPLAY NAME", "SAVE_NAME")
        self.logout_button = Button(SCREEN_WIDTH // 2 - 220, 470, 440, 56, "LOGOUT", "LOGOUT")
        self.back_button = Button(SCREEN_WIDTH // 2 - 150, 548, 300, 52, "BACK", "BACK")
        self.message = ""

    @property
    def display_name(self):
        return self.display_input.text

    @display_name.setter
    def display_name(self, value):
        self.display_input.text = value

    def update(self, mouse_pos):
        self.save_button.update(mouse_pos)
        self.logout_button.update(mouse_pos)
        self.back_button.update(mouse_pos)

    def handle_event(self, event):
        if self.display_input.handle_event(event) == "ENTER":
            return "SAVE_NAME"
        for button in (self.save_button, self.logout_button, self.back_button):
            action = button.handle_event(event)
            if action:
                return action
        return None

    def draw(self, surface, profile, username):
        draw_background(surface)
        draw_text(surface, "PROFILE", 62, SCREEN_WIDTH // 2, 110, WHITE, bold=True)
        draw_text(surface, f"Account: {username}", 22, SCREEN_WIDTH // 2, 164, LIGHT_GRAY, bold=True)

        panel = pygame.Rect(SCREEN_WIDTH // 2 - 310, 230, 620, 405)
        pygame.draw.rect(surface, (10, 10, 16), panel, border_radius=22)
        pygame.draw.rect(surface, (80, 80, 98), panel, 2, border_radius=22)

        draw_text(surface, f"Wallet Gems: {profile.get('wallet_gems', 0)}", 22, SCREEN_WIDTH // 2, 266, (80, 190, 255), bold=True)
        draw_text(surface, f"Best Level: {profile.get('best_level', 1)}   Best Score: {profile.get('best_score', 0)}", 21, SCREEN_WIDTH // 2, 296, WHITE, bold=True)

        self.display_input.draw(surface)
        self.save_button.draw(surface)
        self.logout_button.draw(surface)
        self.back_button.draw(surface)

        if self.message:
            draw_text(surface, self.message, 19, SCREEN_WIDTH // 2, 660, (120, 255, 170), bold=True)


class RanksScreen:
    def __init__(self):
        self.category = "BEST_LEVEL"
        self.buttons = [
            Button(SCREEN_WIDTH // 2 - 390, 168, 240, 50, "BEST LV", "BEST_LEVEL"),
            Button(SCREEN_WIDTH // 2 - 120, 168, 240, 50, "BEST GEM", "BEST_GEMS"),
            Button(SCREEN_WIDTH // 2 + 150, 168, 240, 50, "BEST SCORE", "BEST_SCORE"),
            Button(SCREEN_WIDTH // 2 - 145, SCREEN_HEIGHT - 78, 290, 50, "BACK", "BACK"),
        ]

    def update(self, mouse_pos):
        for button in self.buttons:
            button.update(mouse_pos)

    def handle_event(self, event):
        for button in self.buttons:
            action = button.handle_event(event)
            if action:
                return action
        return None

    def draw(self, surface, entries, status_message=""):
        draw_background(surface)
        draw_text(surface, "RANKS", 64, SCREEN_WIDTH // 2, 100, WHITE, bold=True)
        if status_message:
            color = (120, 255, 170) if "GLOBAL" in status_message else (255, 170, 90)
            draw_text(surface, status_message, 17, SCREEN_WIDTH // 2, 142, color, bold=True)

        title = {
            "BEST_LEVEL": "BEST LEVEL",
            "BEST_GEMS": "BEST GEMS",
            "BEST_SCORE": "BEST SCORE",
        }.get(self.category, "BEST LEVEL")

        for button in self.buttons:
            button.draw(surface)

        panel = pygame.Rect(SCREEN_WIDTH // 2 - 360, 245, 720, 410)
        pygame.draw.rect(surface, (10, 10, 16), panel, border_radius=22)
        pygame.draw.rect(surface, (80, 80, 98), panel, 2, border_radius=22)

        draw_text(surface, title, 30, SCREEN_WIDTH // 2, 282, (255, 230, 120), bold=True)

        if not entries:
            draw_text(surface, "No ranks yet. Play with an account first.", 24, SCREEN_WIDTH // 2, 420, LIGHT_GRAY, bold=True)
        else:
            start_y = 330
            for i, (name, value, username) in enumerate(entries):
                y = start_y + i * 32
                rank_color = (255, 230, 120) if i == 0 else WHITE
                draw_text(surface, f"{i + 1}.", 22, SCREEN_WIDTH // 2 - 290, y, rank_color, center=False, bold=True)
                draw_text(surface, name, 22, SCREEN_WIDTH // 2 - 240, y, rank_color, center=False, bold=True)
                draw_text(surface, str(value), 22, SCREEN_WIDTH // 2 + 230, y, rank_color, center=False, bold=True)


class ShopScreen:
    def __init__(self, gun_catalog, skin_palette):
        self.gun_catalog = gun_catalog
        self.skin_palette = skin_palette
        self.tab = "GUNS"
        self.tabs = {
            "GUNS": pygame.Rect(SCREEN_WIDTH // 2 - 250, 155, 230, 52),
            "SKINS": pygame.Rect(SCREEN_WIDTH // 2 + 20, 155, 230, 52),
        }
        self.back_button = Button(SCREEN_WIDTH // 2 - 145, SCREEN_HEIGHT - 78, 290, 50, "BACK", "BACK")
        self.card_rects = {}
        self.hovered_key = None
        self.build_cards()

    def build_cards(self):
        self.card_rects = {}
        data = self.gun_catalog if self.tab == "GUNS" else self.skin_palette
        keys = list(data.keys())
        card_w = 200
        card_h = 142
        gap = 22
        columns = 3
        total_w = columns * card_w + (columns - 1) * gap
        start_x = SCREEN_WIDTH // 2 - total_w // 2
        start_y = 248

        for i, key in enumerate(keys):
            row, col = divmod(i, columns)
            self.card_rects[key] = pygame.Rect(start_x + col * (card_w + gap), start_y + row * (card_h + gap), card_w, card_h)

    def update(self, mouse_pos):
        self.build_cards()
        self.hovered_key = None
        for key, rect in self.card_rects.items():
            if rect.collidepoint(mouse_pos):
                self.hovered_key = key
        self.back_button.update(mouse_pos)

    def handle_event(self, event):
        if self.back_button.handle_event(event):
            return "BACK"

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for tab, rect in self.tabs.items():
                if rect.collidepoint(event.pos):
                    self.tab = tab
                    self.build_cards()
                    return ("SHOP_TAB", tab)

            for key, rect in self.card_rects.items():
                if rect.collidepoint(event.pos):
                    return ("SHOP_ITEM", self.tab, key)

        return None

    def draw_tab(self, surface, name, rect):
        active = self.tab == name
        fill = (30, 20, 28) if active else (18, 18, 25)
        border = RED if active else (85, 85, 98)
        pygame.draw.rect(surface, fill, rect, border_radius=14)
        pygame.draw.rect(surface, border, rect, 3 if active else 2, border_radius=14)
        draw_text(surface, name, 23, rect.centerx, rect.centery, WHITE, bold=True)

    def draw_skin_preview(self, surface, item, cx, cy):
        fill = item["fill"]
        glow = item["glow"]
        accent = item.get("accent", WHITE)
        style = item.get("style", "orb")
        pygame.draw.circle(surface, glow, (cx, cy), 29)
        pygame.draw.circle(surface, fill, (cx, cy), 21)

        if style == "smile":
            pygame.draw.circle(surface, (35, 28, 22), (cx - 6, cy - 4), 3)
            pygame.draw.circle(surface, (35, 28, 22), (cx + 6, cy - 4), 3)
            pygame.draw.arc(surface, (35, 28, 22), pygame.Rect(cx - 9, cy - 4, 18, 15), 0.3, 2.8, 2)
        elif style == "speedster":
            pygame.draw.polygon(surface, accent, [(cx - 2, cy - 18), (cx + 11, cy - 2), (cx + 4, cy - 2), (cx + 12, cy + 17), (cx - 11, cy - 4), (cx - 2, cy - 4)])
        elif style == "fire":
            pygame.draw.polygon(surface, accent, [(cx, cy - 18), (cx + 11, cy - 4), (cx + 7, cy + 14), (cx, cy + 8), (cx - 8, cy + 14), (cx - 11, cy - 4)])

        pygame.draw.circle(surface, WHITE, (cx - 7, cy - 8), 4)
        pygame.draw.circle(surface, (245, 245, 255), (cx, cy), 21, 2)

    def draw_gun_preview(self, surface, item, cx, cy):
        pygame.draw.line(surface, (220, 220, 230), (cx - 38, cy), (cx + 38, cy), 8)
        pygame.draw.line(surface, (70, 70, 82), (cx - 38, cy), (cx + 38, cy), 2)
        pygame.draw.rect(surface, (255, 220, 120), (cx + 33, cy - 6, 13, 12), border_radius=3)
        pygame.draw.rect(surface, (100, 100, 116), (cx - 8, cy + 5, 18, 24), border_radius=3)
        if "AK" in item["name"] or "M4" in item["name"]:
            pygame.draw.rect(surface, (130, 90, 50), (cx - 42, cy + 6, 24, 8), border_radius=3)
        if "BURST" in item["name"]:
            pygame.draw.circle(surface, (80, 190, 255), (cx + 46, cy), 5)

    def draw(self, surface, wallet_gems, owned_guns, active_gun, owned_skins, active_skin):
        draw_background(surface)
        draw_text(surface, "SHOP", 64, SCREEN_WIDTH // 2, 92, WHITE, bold=True)
        draw_text(surface, f"WALLET GEMS: {wallet_gems}", 24, SCREEN_WIDTH // 2, 130, (255, 220, 90), bold=True)

        for tab, rect in self.tabs.items():
            self.draw_tab(surface, tab, rect)

        data = self.gun_catalog if self.tab == "GUNS" else self.skin_palette

        for key, rect in self.card_rects.items():
            item = data[key]
            owned = key in (owned_guns if self.tab == "GUNS" else owned_skins)
            active = key == (active_gun if self.tab == "GUNS" else active_skin)
            hovered = key == self.hovered_key

            fill = (18, 18, 25) if not hovered else (25, 25, 35)
            border = (255, 220, 90) if active else ((80, 190, 255) if owned else (85, 85, 98))
            pygame.draw.rect(surface, fill, rect, border_radius=16)
            pygame.draw.rect(surface, border, rect, 3 if active else 2, border_radius=16)

            cx = rect.centerx
            cy = rect.y + 40

            if self.tab == "GUNS":
                self.draw_gun_preview(surface, item, cx, cy)
                draw_text(surface, item["name"], 20, cx, rect.y + 74, WHITE, bold=True)
                draw_text(surface, item["desc"], 15, cx, rect.y + 98, LIGHT_GRAY, bold=True)
            else:
                self.draw_skin_preview(surface, item, cx, cy)
                draw_text(surface, item["name"], 20, cx, rect.y + 82, WHITE, bold=True)

            if active:
                status = "EQUIPPED"
            elif owned:
                status = "EQUIP"
            else:
                status = f"BUY {item['cost']}G"

            draw_text(surface, status, 18, cx, rect.bottom - 24, (255, 220, 90) if not active else (80, 255, 160), bold=True)

        self.back_button.draw(surface)
