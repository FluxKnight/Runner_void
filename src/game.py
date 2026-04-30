# src/game.py

import sys
import random
import math

import pygame

from src.settings import (
    SCREEN_WIDTH,
    SCREEN_HEIGHT,
    FPS,
    GAME_TITLE,
    BLACK,
    WHITE,
    LIGHT_GRAY,
    GRAY,
    RED,
    DARK_GRAY,
    DIFFICULTY_SETTINGS,
    OBSTACLE_SPEED_INCREMENT,
    SMALL_FONT_SIZE,
)
from src.player import Player
from src.obstacle import Obstacle
from src.gem import Gem
from src.storage import load_highscore, save_highscore
from src.ui import draw_text, draw_hud, draw_difficulty_badge, draw_progress_bar
from src.screens import (
    HomeScreen,
    HowToPlayScreen,
    SettingsScreen,
    PauseScreen,
    GameOverScreen,
    SkinsScreen,
)
from src.transition import ScreenTransition
from src.audio import AudioManager


class Game:
    def __init__(self):
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption(GAME_TITLE)
        self.is_fullscreen = False

        self.clock = pygame.time.Clock()
        self.running = True
        self.state = "HOME"

        self.player = Player()
        self.obstacles = []
        self.gem = Gem()

        self.score = 0
        self.survival_score = 0
        self.gem_score = 0
        self.gems_collected = 0
        self.best_score = load_highscore()
        self.game_time = 0

        self.death_sequence_active = False
        self.death_sequence_elapsed = 0
        self.death_sequence_duration = 0.78
        self.death_particles = []
        self.death_position = (SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)
        self.gem_collect_particles = []

        self.skin_palette = {
            "WHITE": {"name": "WHITE", "fill": (245, 245, 255), "glow": (210, 210, 225), "style": "orb"},
            "BLUE": {"name": "BLUE", "fill": (90, 180, 255), "glow": (80, 190, 255), "style": "orb"},
            "GREEN": {"name": "GREEN", "fill": (100, 230, 145), "glow": (80, 255, 160), "style": "orb"},
            "PINK": {"name": "PINK", "fill": (255, 120, 200), "glow": (255, 110, 210), "style": "orb"},
            "PURPLE": {"name": "PURPLE", "fill": (180, 110, 255), "glow": (190, 120, 255), "style": "orb"},
            "SMILE": {"name": "SMILE", "fill": (255, 220, 70), "glow": (255, 220, 90), "style": "smile"},
            "SPEEDSTER": {"name": "SPEEDSTER", "fill": (65, 150, 255), "glow": (60, 185, 255), "accent": (255, 225, 65), "style": "speedster"},
            "FIRE": {"name": "FIRE", "fill": (255, 120, 55), "glow": (255, 90, 45), "accent": (255, 220, 70), "style": "fire"},
        }
        self.active_skin_key = "WHITE"

        self.home_screen = HomeScreen()
        self.how_to_play_screen = HowToPlayScreen()
        self.settings_screen = SettingsScreen()
        self.pause_screen = PauseScreen()
        self.game_over_screen = GameOverScreen()
        self.skins_screen = SkinsScreen(self.skin_palette, self.active_skin_key)

        self.transition = ScreenTransition(duration=0.72)
        self.audio = AudioManager()
        self.audio.set_muted(not self.settings_screen.sound_on)
        self.sync_sound_setting()
        self.audio.play_for_state(self.state)
        self.apply_active_skin()

        self.pause_button_rect = pygame.Rect(SCREEN_WIDTH - 72, 24, 46, 46)

        self.reset_game()

    def get_balanced_obstacle_count(self, base_count):
        difficulty = self.get_current_difficulty()

        # Original obstacle counts were visually too crowded.
        # This keeps the game challenging, but makes the enemy field cleaner and more IO-like.
        max_obstacles_by_difficulty = {
            "EASY": 3,
            "MEDIUM": 4,
            "HARD": 5,
        }

        max_count = max_obstacles_by_difficulty.get(difficulty, 4)
        return max(1, min(base_count, max_count))

    def get_current_difficulty(self):
        difficulty = self.settings_screen.difficulties[self.settings_screen.difficulty_index]

        if difficulty == "NORMAL":
            difficulty = "MEDIUM"

        return difficulty

    def get_difficulty_config(self):
        difficulty = self.get_current_difficulty()
        return DIFFICULTY_SETTINGS.get(difficulty, DIFFICULTY_SETTINGS["MEDIUM"])

    def reset_game(self):
        self.player.reset()
        self.apply_active_skin()
        self.score = 0
        self.survival_score = 0
        self.gem_score = 0
        self.gems_collected = 0
        self.game_time = 0
        self.death_sequence_active = False
        self.death_sequence_elapsed = 0
        self.death_particles = []
        self.gem_collect_particles = []

        config = self.get_difficulty_config()
        obstacle_count = self.get_balanced_obstacle_count(config["obstacle_count"])

        self.obstacles = [Obstacle() for _ in range(obstacle_count)]
        self.gem.reset(start_above_screen=True)

    def change_state(self, new_state, before_change=None, transition_type="slide"):
        if self.transition.active:
            return

        self.draw_current_state()
        old_surface = self.screen.copy()

        if before_change:
            before_change()

        self.state = new_state
        self.audio.play_for_state(self.state)
        self.transition.start(old_surface, transition_type=transition_type)

    def run(self):
        while self.running:
            dt = self.clock.tick(FPS) / 1000
            mouse_pos = pygame.mouse.get_pos()

            self.handle_events()
            self.update(mouse_pos, dt)
            self.draw()

            pygame.display.flip()

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.exit_game()

            if event.type == pygame.KEYDOWN and event.key == pygame.K_m:
                self.toggle_sound()

            if event.type == pygame.KEYDOWN and event.key == pygame.K_F11:
                self.toggle_fullscreen()
                self.settings_screen.fullscreen_on = self.is_fullscreen

            if self.transition.active:
                continue

            if self.state == "HOME":
                action = self.home_screen.handle_event(event)
                if action:
                    self.audio.play_ui_tap()
                self.handle_home_action(action)

            elif self.state == "PLAYING":
                self.handle_playing_event(event)

            elif self.state == "HOW_TO_PLAY":
                action = self.how_to_play_screen.handle_event(event)
                if action:
                    self.audio.play_ui_tap()
                self.handle_simple_screen_action(action)

            elif self.state == "SETTINGS":
                action = self.settings_screen.handle_event(event)
                if action:
                    self.audio.play_ui_tap()
                self.handle_settings_action(action)

            elif self.state == "PAUSED":
                action = self.pause_screen.handle_event(event)
                if action:
                    self.audio.play_ui_tap()
                self.handle_pause_action(action)

            elif self.state == "GAME_OVER":
                action = self.game_over_screen.handle_event(event)
                if action:
                    self.audio.play_ui_tap()
                self.handle_game_over_action(action)

            elif self.state == "SKINS":
                action = self.skins_screen.handle_event(event)
                if action:
                    self.audio.play_ui_tap()
                self.handle_skins_action(action)

    def handle_home_action(self, action):
        if action == "PLAY":
            self.change_state("PLAYING", before_change=self.reset_game, transition_type="warp")

        elif action == "HOW_TO_PLAY":
            self.change_state("HOW_TO_PLAY", transition_type="neon_wipe")

        elif action == "SETTINGS":
            self.change_state("SETTINGS", transition_type="cyber_grid")

        elif action == "SKINS":
            self.change_state("SKINS", transition_type="cyber_grid")

        elif action == "EXIT":
            self.exit_game()

    def handle_playing_event(self, event):
        if self.death_sequence_active:
            return

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE or event.key == pygame.K_p:
                self.change_state("PAUSED", transition_type="soft_pause")

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.pause_button_rect.collidepoint(event.pos):
                self.change_state("PAUSED", transition_type="soft_pause")

    def handle_simple_screen_action(self, action):
        if action == "BACK":
            self.change_state("HOME", transition_type="return_slide")

    def handle_settings_action(self, action):
        if action == "BACK":
            self.change_state("HOME", transition_type="return_slide")

        elif action == "TOGGLE_SOUND":
            self.toggle_sound()

        elif action == "TOGGLE_FULLSCREEN":
            self.set_fullscreen(self.settings_screen.fullscreen_on)

        elif action == "CHANGE_DIFFICULTY":
            # The SettingsScreen already cycles the selected difficulty.
            # The new difficulty is used when the player starts/restarts a run.
            self.reset_game()

    def handle_skins_action(self, action):
        if action == "BACK":
            self.change_state("HOME", transition_type="return_slide")

        elif isinstance(action, tuple) and action[0] == "SELECT_SKIN":
            self.active_skin_key = action[1]
            self.skins_screen.selected_skin = self.active_skin_key
            self.apply_active_skin()

    def handle_pause_action(self, action):
        if action == "RESUME":
            self.change_state("PLAYING", transition_type="resume_flash")

        elif action == "RESTART":
            self.change_state("PLAYING", before_change=self.reset_game, transition_type="warp")

        elif action == "HOME":
            self.change_state("HOME", transition_type="return_slide")

        elif action == "EXIT":
            self.exit_game()

    def handle_game_over_action(self, action):
        if action == "RETRY":
            self.change_state("PLAYING", before_change=self.reset_game, transition_type="warp")

        elif action == "HOME":
            self.change_state("HOME", transition_type="fade_black")

        elif action == "EXIT":
            self.exit_game()

    def update(self, mouse_pos, dt):
        self.audio.update_for_state(self.state)

        if self.transition.active:
            self.transition.update(dt)
            return

        if self.state == "HOME":
            self.home_screen.update(mouse_pos)

        elif self.state == "PLAYING":
            self.update_gameplay(dt)

        elif self.state == "HOW_TO_PLAY":
            self.how_to_play_screen.update(mouse_pos)

        elif self.state == "SETTINGS":
            self.settings_screen.update(mouse_pos)

        elif self.state == "SKINS":
            self.skins_screen.update(mouse_pos)

        elif self.state == "PAUSED":
            self.pause_screen.update(mouse_pos)

        elif self.state == "GAME_OVER":
            self.game_over_screen.update(mouse_pos)

    def update_gameplay(self, dt):
        if self.death_sequence_active:
            self.update_death_sequence(dt)
            self.update_gem_collect_particles(dt)
            return

        config = self.get_difficulty_config()

        keys = pygame.key.get_pressed()
        self.player.update(keys, dt)

        self.game_time += dt
        self.survival_score += dt * config["survival_score_rate"]
        self.score = int(self.gem_score + self.survival_score)

        extra_speed = self.score * OBSTACLE_SPEED_INCREMENT
        extra_speed += config["speed_bonus"]
        extra_speed = max(0, extra_speed)

        self.gem.update(dt, extra_speed=extra_speed)
        self.update_gem_collect_particles(dt)

        if self.gem.is_collected_by(self.player):
            self.gems_collected += 1
            self.gem_score += config["gem_value"]
            self.audio.play_gem_collect()
            self.start_gem_collect_effect()
            self.gem.reset(start_above_screen=False)
            self.score = int(self.gem_score + self.survival_score)

        for obstacle in self.obstacles:
            obstacle.update(extra_speed=extra_speed)

            if self.check_collision(self.player, obstacle):
                self.start_death_sequence()
                break

    def start_gem_collect_effect(self):
        player_x, player_y = self.player.get_position()

        for _ in range(18):
            angle = random.uniform(0, math.tau)
            speed = random.uniform(70, 230)

            self.gem_collect_particles.append(
                {
                    "x": player_x,
                    "y": player_y,
                    "vx": math.cos(angle) * speed,
                    "vy": math.sin(angle) * speed,
                    "life": random.uniform(0.28, 0.55),
                    "max_life": 0.55,
                    "size": random.randint(2, 5),
                }
            )

    def update_gem_collect_particles(self, dt):
        alive_particles = []

        for particle in self.gem_collect_particles:
            particle["life"] -= dt
            if particle["life"] <= 0:
                continue

            particle["x"] += particle["vx"] * dt
            particle["y"] += particle["vy"] * dt
            particle["vy"] += 95 * dt
            alive_particles.append(particle)

        self.gem_collect_particles = alive_particles

    def draw_gem_collect_particles(self):
        if not self.gem_collect_particles:
            return

        surface = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)

        for particle in self.gem_collect_particles:
            progress = max(0, min(1, particle["life"] / particle["max_life"]))
            alpha = int(220 * progress)
            radius = max(1, int(particle["size"] * (0.7 + 0.8 * progress)))

            pygame.draw.circle(
                surface,
                (80, 190, 255, alpha),
                (int(particle["x"]), int(particle["y"])),
                radius,
            )

            pygame.draw.circle(
                surface,
                (255, 255, 255, int(alpha * 0.65)),
                (int(particle["x"]), int(particle["y"])),
                max(1, radius // 2),
            )

        self.screen.blit(surface, (0, 0))

    def start_death_sequence(self):
        if self.death_sequence_active:
            return

        player_x, player_y = self.player.get_position()
        self.death_sequence_active = True
        self.death_sequence_elapsed = 0
        self.death_position = (player_x, player_y)
        self.death_particles = []

        self.audio.play_player_burst()

        for _ in range(52):
            angle = random.uniform(0, math.tau)
            speed = random.uniform(90, 420)

            self.death_particles.append(
                {
                    "x": player_x,
                    "y": player_y,
                    "vx": math.cos(angle) * speed,
                    "vy": math.sin(angle) * speed,
                    "life": random.uniform(0.45, self.death_sequence_duration),
                    "max_life": self.death_sequence_duration,
                    "size": random.randint(2, 7),
                }
            )

    def update_death_sequence(self, dt):
        self.death_sequence_elapsed += dt

        alive_particles = []

        for particle in self.death_particles:
            particle["life"] -= dt

            if particle["life"] <= 0:
                continue

            particle["x"] += particle["vx"] * dt
            particle["y"] += particle["vy"] * dt
            particle["vx"] *= 0.985
            particle["vy"] *= 0.985

            alive_particles.append(particle)

        self.death_particles = alive_particles

        if self.death_sequence_elapsed >= self.death_sequence_duration:
            self.game_over()

    def draw_death_explosion(self):
        if not self.death_sequence_active:
            return

        progress = min(1, self.death_sequence_elapsed / self.death_sequence_duration)
        x, y = self.death_position

        surface = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)

        ring_radius = int(18 + 110 * progress)
        ring_alpha = int(210 * max(0, 1 - progress))
        pygame.draw.circle(surface, (255, 255, 255, ring_alpha), (int(x), int(y)), ring_radius, 3)

        core_radius = max(1, int(22 * max(0, 1 - progress)))
        pygame.draw.circle(surface, (255, 255, 255, 235), (int(x), int(y)), core_radius)

        for particle in self.death_particles:
            particle_progress = max(0, min(1, particle["life"] / particle["max_life"]))
            alpha = int(235 * particle_progress)
            radius = max(1, int(particle["size"] * (0.8 + particle_progress)))

            pygame.draw.circle(
                surface,
                (255, 255, 255, alpha),
                (int(particle["x"]), int(particle["y"])),
                radius,
            )

            pygame.draw.circle(
                surface,
                (255, 42, 42, int(alpha * 0.38)),
                (int(particle["x"]), int(particle["y"])),
                max(1, radius // 2),
            )

        flash_alpha = int(95 * max(0, 1 - progress * 2))
        if flash_alpha > 0:
            flash = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            flash.fill((255, 255, 255, flash_alpha))
            self.screen.blit(flash, (0, 0))

        self.screen.blit(surface, (0, 0))

    def game_over(self):
        if self.score > self.best_score:
            self.best_score = self.score
            save_highscore(self.best_score)

        self.change_state("GAME_OVER", transition_type="crash_glitch")

    def check_collision(self, player, obstacle):
        player_x, player_y = player.get_position()
        player_radius = player.get_radius()
        rect = obstacle.get_rect()

        closest_x = max(rect.left, min(player_x, rect.right))
        closest_y = max(rect.top, min(player_y, rect.bottom))

        distance_x = player_x - closest_x
        distance_y = player_y - closest_y
        distance_squared = distance_x * distance_x + distance_y * distance_y

        return distance_squared < player_radius * player_radius

    def draw(self):
        if self.transition.active:
            self.draw_current_state()
            new_surface = self.screen.copy()
            self.transition.draw(self.screen, new_surface)
            return

        self.draw_current_state()

    def draw_current_state(self):
        if self.state == "HOME":
            self.home_screen.draw(self.screen)

        elif self.state == "PLAYING":
            self.draw_gameplay()

        elif self.state == "HOW_TO_PLAY":
            self.how_to_play_screen.draw(self.screen)

        elif self.state == "SETTINGS":
            self.settings_screen.draw(self.screen)

        elif self.state == "SKINS":
            self.skins_screen.draw(self.screen)

        elif self.state == "PAUSED":
            self.draw_gameplay()
            self.pause_screen.draw(self.screen)

        elif self.state == "GAME_OVER":
            self.game_over_screen.draw(self.screen, self.score, self.best_score)

        self.draw_music_hint()

    def draw_gameplay(self):
        self.draw_gameplay_background()

        self.gem.draw(self.screen)

        for obstacle in self.obstacles:
            obstacle.draw(self.screen)

        self.draw_gem_collect_particles()

        if self.death_sequence_active:
            self.draw_death_explosion()
        else:
            self.player.draw(self.screen)

        draw_hud(self.screen, self.score, self.best_score)
        self.draw_gem_counter()
        self.draw_pause_button()
        self.draw_bottom_status()

    def draw_gameplay_background(self):
        self.screen.fill(BLACK)

        time = pygame.time.get_ticks() * 0.001

        for i in range(18):
            x = (i * 83 + int(time * 25)) % SCREEN_WIDTH
            y1 = int((i * 47 + time * 80) % SCREEN_HEIGHT)
            y2 = y1 + 60

            pygame.draw.line(
                self.screen,
                (20, 20, 28),
                (x, y1),
                (x, min(y2, SCREEN_HEIGHT)),
                1,
            )

        pygame.draw.line(
            self.screen,
            (30, 30, 38),
            (120, SCREEN_HEIGHT - 72),
            (SCREEN_WIDTH - 120, SCREEN_HEIGHT - 72),
            1,
        )

        for i in range(22):
            x = int((i * 157 + time * 18) % SCREEN_WIDTH)
            y = int((i * 97 + time * 32) % SCREEN_HEIGHT)

            pygame.draw.circle(
                self.screen,
                (55, 7, 12),
                (x, y),
                1,
            )

    def draw_gem_counter(self):
        rect = pygame.Rect(SCREEN_WIDTH // 2 - 90, 28, 180, 58)

        pygame.draw.rect(self.screen, (14, 14, 20), rect, border_radius=14)
        pygame.draw.rect(self.screen, (80, 190, 255), rect, width=2, border_radius=14)

        gem_x = rect.x + 35
        gem_y = rect.y + 29

        points = [
            (gem_x, gem_y - 10),
            (gem_x + 10, gem_y),
            (gem_x, gem_y + 10),
            (gem_x - 10, gem_y),
        ]

        pygame.draw.polygon(self.screen, (80, 190, 255), points)
        pygame.draw.polygon(self.screen, WHITE, points, width=1)

        draw_text(
            self.screen,
            f"x {self.gems_collected}",
            26,
            rect.x + 62,
            rect.y + 16,
            WHITE,
            center=False,
            bold=True,
        )

    def draw_pause_button(self):
        mouse_pos = pygame.mouse.get_pos()
        hovered = self.pause_button_rect.collidepoint(mouse_pos)

        fill_color = (25, 10, 14) if hovered else DARK_GRAY
        border_color = RED if hovered else GRAY

        pygame.draw.rect(self.screen, fill_color, self.pause_button_rect, border_radius=10)
        pygame.draw.rect(self.screen, border_color, self.pause_button_rect, width=2, border_radius=10)

        bar_width = 5
        bar_height = 20
        center_x = self.pause_button_rect.centerx
        center_y = self.pause_button_rect.centery

        pygame.draw.rect(
            self.screen,
            WHITE,
            pygame.Rect(center_x - 9, center_y - bar_height // 2, bar_width, bar_height),
            border_radius=2,
        )

        pygame.draw.rect(
            self.screen,
            WHITE,
            pygame.Rect(center_x + 4, center_y - bar_height // 2, bar_width, bar_height),
            border_radius=2,
        )

    def draw_bottom_status(self):
        difficulty = self.get_current_difficulty()
        config = self.get_difficulty_config()

        draw_difficulty_badge(
            self.screen,
            difficulty,
            SCREEN_WIDTH // 2 - 105,
            SCREEN_HEIGHT - 58,
        )

        progress = min(1, (self.score % 100) / 100)

        draw_progress_bar(
            self.screen,
            x=SCREEN_WIDTH // 2 - 150,
            y=SCREEN_HEIGHT - 90,
            width=300,
            progress=progress,
            label=f"GEM VALUE: +{config['gem_value']}",
        )

    def apply_active_skin(self):
        palette = self.skin_palette.get(self.active_skin_key, self.skin_palette["WHITE"])
        self.player.set_skin(self.active_skin_key, palette)
        self.skins_screen.selected_skin = self.active_skin_key

    def sync_sound_setting(self):
        self.settings_screen.sound_on = not self.audio.muted

    def toggle_sound(self):
        self.audio.set_muted(not self.audio.muted)
        self.sync_sound_setting()
        self.audio.play_for_state(self.state)

    def set_fullscreen(self, enabled):
        self.is_fullscreen = enabled

        if enabled:
            self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.FULLSCREEN)
        else:
            self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))

        pygame.display.set_caption(GAME_TITLE)
        self.pause_button_rect = pygame.Rect(SCREEN_WIDTH - 72, 24, 46, 46)

    def toggle_fullscreen(self):
        self.set_fullscreen(not self.is_fullscreen)

    def draw_music_hint(self):
        if not self.audio.available:
            return

        label = "M: MUSIC OFF" if self.audio.muted else "M: MUSIC ON"
        color = GRAY if self.audio.muted else LIGHT_GRAY

        draw_text(
            self.screen,
            label,
            SMALL_FONT_SIZE,
            18,
            SCREEN_HEIGHT - 30,
            color,
            center=False,
            bold=False,
        )

    def exit_game(self):
        self.audio.stop()
        self.running = False
        pygame.quit()
        sys.exit()
