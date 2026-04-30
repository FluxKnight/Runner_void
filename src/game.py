# src/game.py

import json
import math
import random
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

import pygame

from src import settings as S
from src.audio import AudioManager
from src.player import Player
from src.screens import (
    LoginScreen,
    CreateAccountScreen,
    HomeScreen,
    HowToPlayScreen,
    SettingsScreen,
    PauseScreen,
    GameOverScreen,
    ShopScreen,
    ProfileScreen,
    RanksScreen,
    draw_text,
)
from src.transition import ScreenTransition

SCREEN_WIDTH = getattr(S, "SCREEN_WIDTH", 1280)
SCREEN_HEIGHT = getattr(S, "SCREEN_HEIGHT", 720)
FPS = getattr(S, "FPS", 60)
GAME_TITLE = getattr(S, "GAME_TITLE", "VOID RUNNER")
BLACK = getattr(S, "BLACK", (0, 0, 0))
WHITE = getattr(S, "WHITE", (255, 255, 255))
LIGHT_GRAY = getattr(S, "LIGHT_GRAY", (205, 205, 210))
GRAY = getattr(S, "GRAY", (120, 120, 130))
RED = getattr(S, "RED", (220, 40, 40))
DARK_GRAY = getattr(S, "DARK_GRAY", (28, 28, 36))
SMALL_FONT_SIZE = getattr(S, "SMALL_FONT_SIZE", 16)


class Game:
    def __init__(self):
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption(GAME_TITLE)
        pygame.mouse.set_visible(True)
        self.clock = pygame.time.Clock()
        self.running = True
        self.state = "LOGIN"
        self.is_fullscreen = False

        self.users_path = Path.cwd() / "data" / "users.json"
        self.session_path = Path.cwd() / "data" / "session.json"
        self.server_config_path = Path.cwd() / "data" / "server_config.json"
        self.server_url = self.load_server_url()
        self.server_online = False

        # Anti-freeze server sync state.
        # Never let gameplay freeze because of slow/offline internet.
        self.last_server_sync_time = 0
        self.server_sync_cooldown = 8.0
        self.pending_server_sync = False

        self.current_user = None
        self.login_error = ""
        self.profile_message = ""
        self.profile_path = Path.cwd() / "data" / "profile.json"

        self.skin_palette = {
            "WHITE": {"name": "WHITE", "cost": 0, "fill": (245, 245, 255), "glow": (210, 210, 225), "style": "orb"},
            "BLUE": {"name": "BLUE", "cost": 35, "fill": (90, 180, 255), "glow": (80, 190, 255), "style": "orb"},
            "GREEN": {"name": "GREEN", "cost": 45, "fill": (100, 230, 145), "glow": (80, 255, 160), "style": "orb"},
            "PINK": {"name": "PINK", "cost": 55, "fill": (255, 120, 200), "glow": (255, 110, 210), "style": "orb"},
            "PURPLE": {"name": "PURPLE", "cost": 65, "fill": (180, 110, 255), "glow": (190, 120, 255), "style": "orb"},
            "SMILE": {"name": "SMILE", "cost": 90, "fill": (255, 220, 70), "glow": (255, 220, 90), "style": "smile"},
            "SPEEDSTER": {"name": "SPEEDSTER", "cost": 130, "fill": (65, 150, 255), "glow": (60, 185, 255), "accent": (255, 225, 65), "style": "speedster"},
            "FIRE": {"name": "FIRE", "cost": 150, "fill": (255, 120, 55), "glow": (255, 90, 45), "accent": (255, 220, 70), "style": "fire"},
        }

        self.gun_catalog = {
            "PISTOL": {
                "name": "SMALL PISTOL",
                "cost": 0,
                "damage": 26,
                "cooldown": 0.28,
                "bullet_speed": 1050,
                "magazine": 60,
                "reload": 0.45,
                "bullets": 1,
                "spread": 0.0,
                "sfx": "PISTOL",
                "desc": "Free starter gun",
            },
            "GLOCK": {
                "name": "GLOCK",
                "cost": 80,
                "damage": 23,
                "cooldown": 0.17,
                "bullet_speed": 1080,
                "magazine": 70,
                "reload": 0.42,
                "bullets": 1,
                "spread": 0.02,
                "sfx": "PISTOL",
                "desc": "Fast handgun",
            },
            "AK47": {
                "name": "AK-47",
                "cost": 165,
                "damage": 17,
                "cooldown": 0.085,
                "bullet_speed": 1120,
                "magazine": 95,
                "reload": 0.55,
                "bullets": 1,
                "spread": 0.075,
                "sfx": "RIFLE",
                "desc": "High fire rate",
            },
            "M4A4": {
                "name": "M4A4",
                "cost": 230,
                "damage": 19,
                "cooldown": 0.075,
                "bullet_speed": 1160,
                "magazine": 105,
                "reload": 0.50,
                "bullets": 1,
                "spread": 0.045,
                "sfx": "RIFLE",
                "desc": "Stable rifle",
            },
            "BURST": {
                "name": "BURST GUN",
                "cost": 300,
                "damage": 22,
                "cooldown": 0.36,
                "bullet_speed": 1120,
                "magazine": 72,
                "reload": 0.55,
                "bullets": 1,
                "spread": 0.03,
                "burst_count": 3,
                "burst_gap": 0.065,
                "sfx": "BURST_GUN",
                "desc": "Three-round burst",
            },
        }

        self.users = self.load_users()
        self.sync_users_from_server()
        self.profile = self.default_profile()

        # Auto-login on this device if a previous session exists.
        self.try_auto_login_session()

        self.player = Player()
        self.apply_active_skin()

        self.login_screen = LoginScreen()
        self.create_account_screen = CreateAccountScreen()
        self.home_screen = HomeScreen()
        self.how_to_play_screen = HowToPlayScreen()
        self.settings_screen = SettingsScreen()
        self.pause_screen = PauseScreen()
        self.game_over_screen = GameOverScreen()
        self.shop_screen = ShopScreen(self.gun_catalog, self.skin_palette)
        self.profile_screen = ProfileScreen()
        self.ranks_screen = RanksScreen()

        self.transition = ScreenTransition(duration=0.82)
        self.audio = AudioManager()
        self.audio.set_muted(not self.settings_screen.sound_on)
        self.audio.play_for_state(self.state)

        self.pause_button_rect = pygame.Rect(SCREEN_WIDTH - 72, 24, 46, 46)
        self.reset_game()

    def default_profile(self):
        return {
            "wallet_gems": 0,
            "best_score": 0,
            "owned_skins": ["WHITE"],
            "active_skin": "WHITE",
            "owned_guns": ["PISTOL"],
            "active_gun": "PISTOL",
        }

    def load_server_url(self):
        default_url = "https://void-runner-server.onrender.com"

        try:
            self.server_config_path.parent.mkdir(parents=True, exist_ok=True)
            if not self.server_config_path.exists():
                self.server_config_path.write_text(
                    json.dumps({"server_url": default_url}, indent=2),
                    encoding="utf-8",
                )
                return default_url

            data = json.loads(self.server_config_path.read_text(encoding="utf-8"))
            return data.get("server_url", default_url).rstrip("/")
        except Exception:
            return default_url

    def server_request(self, path, payload=None, timeout=0.55):
        url = self.server_url.rstrip("/") + path

        try:
            if payload is None:
                request = urllib.request.Request(url, method="GET")
            else:
                body = json.dumps(payload).encode("utf-8")
                request = urllib.request.Request(
                    url,
                    data=body,
                    method="POST",
                    headers={"Content-Type": "application/json"},
                )

            with urllib.request.urlopen(request, timeout=timeout) as response:
                data = response.read().decode("utf-8")
                self.server_online = True
                return json.loads(data)

        except Exception:
            self.server_online = False
            return None

    def can_sync_now(self):
        return time.time() - self.last_server_sync_time >= self.server_sync_cooldown

    def mark_server_sync(self):
        self.last_server_sync_time = time.time()


    def sync_users_from_server(self, force=False):
        # RANKS needs force=True so it always shows the real global leaderboard.
        if not force and hasattr(self, "can_sync_now") and not self.can_sync_now():
            return False

        if hasattr(self, "mark_server_sync"):
            self.mark_server_sync()

        data = self.server_request("/users", timeout=1.4)

        if not data or not data.get("ok"):
            return False

        users = data.get("users", {})
        if isinstance(users, dict):
            self.users = users
            self.save_users()
            return True

        return False

    def sync_current_user_to_server(self, force=False):
        if not self.current_user:
            return False

        # Critical anti-freeze rule:
        # never do blocking internet sync while actively playing.
        if getattr(self, "state", "") == "PLAYING" and not force:
            self.pending_server_sync = True
            return False

        if not force and not self.can_sync_now():
            self.pending_server_sync = True
            return False

        self.mark_server_sync()
        self.pending_server_sync = False

        payload = {
            "username": self.current_user,
            "profile": self.profile,
        }
        data = self.server_request("/sync_profile", payload, timeout=0.8)

        if data and data.get("ok"):
            # Keep local users updated, but do not immediately call another server request.
            users = data.get("users")
            if isinstance(users, dict):
                self.users = users
                self.save_users()
            return True

        return False

    def load_users(self):
        try:
            if self.users_path.exists():
                data = json.loads(self.users_path.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    return data
        except Exception:
            pass
        return {}

    def save_users(self):
        try:
            self.users_path.parent.mkdir(parents=True, exist_ok=True)
            self.users_path.write_text(json.dumps(self.users, indent=2), encoding="utf-8")
        except Exception:
            pass

    def load_session(self):
        try:
            if self.session_path.exists():
                data = json.loads(self.session_path.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    return data
        except Exception:
            pass
        return {}

    def save_session(self):
        if not self.current_user:
            return

        try:
            self.session_path.parent.mkdir(parents=True, exist_ok=True)
            self.session_path.write_text(
                json.dumps({"username": self.current_user}, indent=2),
                encoding="utf-8",
            )
        except Exception:
            pass

    def clear_session(self):
        try:
            if self.session_path.exists():
                self.session_path.unlink()
        except Exception:
            pass

    def try_auto_login_session(self):
        session = self.load_session()
        username = session.get("username")

        if username and username in self.users:
            self.current_user = username
            self.profile = self.normalize_profile(self.users[username])
            self.users[username] = self.profile
            self.save_users()
            self.state = "HOME"
        else:
            self.current_user = None
            self.profile = self.default_profile()
            self.state = "LOGIN"
            self.clear_session()

    def make_new_user_profile(self, username, password):
        profile = self.default_profile()
        profile.update({
            "username": username,
            "password": password,
            "display_name": username,
            "best_level": 1,
            "best_gems": 0,
            "best_score": 0,
            "total_gems_collected": 0,
        })
        return profile

    def create_account(self, username, password, confirm_password):
        username = username.strip()
        password = password.strip()
        confirm_password = confirm_password.strip()

        if len(username) < 3:
            return False, "Username must be at least 3 characters."
        if len(password) < 3:
            return False, "Password must be at least 3 characters."
        if password != confirm_password:
            return False, "Passwords do not match."

        # Try server registration first.
        server_data = self.server_request(
            "/create_account",
            {"username": username, "password": password, "confirm_password": confirm_password},
        )

        if server_data:
            if server_data.get("ok"):
                users = server_data.get("users")
                if isinstance(users, dict):
                    self.users = users
                    self.save_users()
                else:
                    self.sync_users_from_server(force=True)
                return True, "Account created on server. Please log in."
            return False, server_data.get("message", "Server create failed.")

        # Offline fallback.
        if username in self.users:
            return False, "Username already exists."

        self.users[username] = self.make_new_user_profile(username, password)
        self.save_users()
        return True, "Account created offline. Server not connected."

    def login_user(self, username, password):
        username = username.strip()
        password = password.strip()

        # Try server login first.
        server_data = self.server_request(
            "/login",
            {"username": username, "password": password},
        )

        if server_data:
            if not server_data.get("ok"):
                return False, server_data.get("message", "Login failed.")

            self.users = server_data.get("users", self.users)
            user = server_data.get("profile", {})
            self.current_user = username
            self.profile = self.normalize_profile(user)
            self.users[username] = self.profile
            self.save_users()
            self.save_session()
            self.apply_active_skin()
            self.current_ammo = self.get_active_gun()["magazine"] if hasattr(self, "current_ammo") else 0
            return True, "Logged in with server."

        # Offline fallback.
        user = self.users.get(username)
        if not user:
            return False, "Account not found. Server offline?"
        if user.get("password") != password:
            return False, "Wrong password."

        self.current_user = username
        self.profile = self.normalize_profile(user)
        self.users[username] = self.profile
        self.save_users()
        self.save_session()
        self.apply_active_skin()
        self.current_ammo = self.get_active_gun()["magazine"] if hasattr(self, "current_ammo") else 0
        return True, "Logged in offline."

    def normalize_profile(self, profile):
        default = self.default_profile()
        default.update(profile)

        default["owned_skins"] = sorted(set(default.get("owned_skins", ["WHITE"]) + ["WHITE"]))
        default["owned_guns"] = sorted(set(default.get("owned_guns", ["PISTOL"]) + ["PISTOL"]))

        if default.get("active_skin") not in self.skin_palette:
            default["active_skin"] = "WHITE"
        if default.get("active_gun") not in self.gun_catalog:
            default["active_gun"] = "PISTOL"

        default.setdefault("display_name", default.get("username", "Player"))
        default.setdefault("best_level", 1)
        default.setdefault("best_gems", 0)
        default.setdefault("best_score", 0)
        default.setdefault("total_gems_collected", 0)
        return default

    def logout_user(self):
        self.save_profile()
        self.clear_session()
        self.current_user = None
        self.profile = self.default_profile()
        self.login_screen.clear()
        self.change_state("LOGIN", transition_type="fade_black")

    def update_leaderboard_stats(self):
        if not self.current_user:
            return

        self.profile["best_level"] = max(self.profile.get("best_level", 1), self.level)
        self.profile["best_score"] = max(self.profile.get("best_score", 0), int(self.score))
        self.profile["best_gems"] = max(self.profile.get("best_gems", 0), self.profile.get("wallet_gems", 0))

    def get_rank_entries(self, category):
        # First push this account's latest stats, then force pull all global users.
        if self.current_user:
            self.sync_current_user_to_server(force=True)

        self.sync_users_from_server(force=True)

        entries = []
        for username, profile in self.users.items():
            display_name = profile.get("display_name", username)
            if category == "BEST_LEVEL":
                value = profile.get("best_level", 1)
            elif category == "BEST_GEMS":
                value = profile.get("best_gems", profile.get("wallet_gems", 0))
            else:
                value = profile.get("best_score", 0)

            entries.append((display_name, int(value or 0), username))

        entries.sort(key=lambda item: item[1], reverse=True)
        return entries[:10]


    def load_profile(self):
        if self.current_user and self.current_user in self.users:
            return self.normalize_profile(self.users[self.current_user])
        return self.default_profile()

    def save_profile(self):
        self.update_leaderboard_stats()
        if self.current_user:
            self.users[self.current_user] = self.profile
            self.save_users()
            self.sync_current_user_to_server()
            return

        # Guest fallback.
        try:
            self.profile_path.parent.mkdir(parents=True, exist_ok=True)
            self.profile_path.write_text(json.dumps(self.profile, indent=2), encoding="utf-8")
        except Exception:
            pass

    def get_active_skin(self):
        return self.profile.get("active_skin", "WHITE")

    def get_active_gun_key(self):
        return self.profile.get("active_gun", "PISTOL")

    def get_active_gun(self):
        return self.gun_catalog[self.get_active_gun_key()]

    def apply_active_skin(self):
        skin_key = self.get_active_skin()
        palette = self.skin_palette.get(skin_key, self.skin_palette["WHITE"])
        self.player.set_skin(skin_key, palette)

    def reset_game(self):
        self.player.reset()
        self.apply_active_skin()

        self.score = 0
        self.run_gems = 0
        self.game_time = 0
        self.player_hp = 100
        self.max_hp = 100

        self.level = 1
        self.level_scene_active = False
        self.level_scene_timer = 0
        self.next_level_fade_timer = 0

        # Simple auto-target system.
        # No hard mouse radius/cone control anymore.
        # The player moves with WASD; the gun auto-targets the nearest zombie.
        self.auto_target_range = 620
        self.auto_fire_enabled = True
        self.auto_aim_enabled = True
        self.current_auto_target = None

        self.shoot_cooldown = 0
        self.reload_timer = 0
        self.current_ammo = self.get_active_gun()["magazine"]
        self.burst_queue = []

        self.active_skills = {
            "RAPID": 0,
            "INFINITE": 0,
            "IMMORTAL": 0,
        }

        self.death_sequence_active = False
        self.death_sequence_elapsed = 0
        self.death_sequence_duration = 0.85
        self.death_particles = []
        self.death_position = (SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)

        self.setup_level(self.level, first_level=True)

        self.audio.set_boss_active(False)
        self.audio.play_for_state("PLAYING")

    def get_level_targets(self, level):
        return {
            "zombies": 100 + (level - 1) * 50,
            "bosses": 4 + (level - 1) * 3,
        }

    def setup_level(self, level, first_level=False):
        targets = self.get_level_targets(level)

        self.level_zombie_total = targets["zombies"]
        self.level_boss_total = targets["bosses"]
        self.level_zombies_spawned = 0
        self.level_zombies_killed = 0
        self.level_bosses_spawned = 0
        self.level_bosses_killed = 0

        self.zombies = []
        self.bullets = []
        self.gems = []
        self.skills = []
        self.floating_texts = []
        self.particles = []

        self.spawn_timer = 0.45 if first_level else 0.85
        self.gem_spawn_timer = 1.4
        self.skill_spawn_timer = 5.5

        self.boss_active = False
        self.boss = None
        self.boss_warning_timer = 0

        self.current_ammo = self.get_active_gun()["magazine"]
        self.reload_timer = 0
        self.burst_queue = []

        # Give a small heal between levels but keep the player from farming full easy HP forever.
        if not first_level:
            self.player_hp = min(self.max_hp, self.player_hp + 40)

        self.player.x = SCREEN_WIDTH // 2
        self.player.y = SCREEN_HEIGHT // 2 + 110
        self.player.vx = 0
        self.player.vy = 0
        self.player.trail = []

        self.add_floating_text(f"LEVEL {self.level}", SCREEN_WIDTH // 2, 190, (255, 230, 120))
        self.audio.set_boss_active(False)
        self.audio.play_for_state("PLAYING")

    def get_level_remaining(self):
        zombie_remaining = max(0, self.level_zombie_total - self.level_zombies_killed)
        boss_remaining = max(0, self.level_boss_total - self.level_bosses_killed)
        return zombie_remaining, boss_remaining

    def check_level_complete(self):
        zombie_remaining, boss_remaining = self.get_level_remaining()

        if zombie_remaining <= 0 and boss_remaining <= 0 and not self.zombies and not self.level_scene_active:
            self.start_level_clear_scene()

    def start_level_clear_scene(self):
        self.level_scene_active = True
        self.level_scene_timer = 0
        self.zombies = []
        self.bullets = []
        self.skills = []
        self.gems = []
        self.particles = []
        self.audio.set_boss_active(False)
        self.audio.play_for_state("PLAYING")
        self.add_floating_text("LEVEL CLEAR", SCREEN_WIDTH // 2, 190, (255, 230, 120))

    def finish_level_scene(self):
        self.level += 1
        self.profile["best_level"] = max(self.profile.get("best_level", 1), self.level)
        self.save_profile()
        self.sync_current_user_to_server(force=True)
        self.level_scene_active = False
        self.level_scene_timer = 0
        self.next_level_fade_timer = 1.15
        self.setup_level(self.level, first_level=False)


    def run(self):
        while self.running:
            dt = self.clock.tick(FPS) / 1000
            mouse_pos = pygame.mouse.get_pos()

            self.handle_events()
            self.update(mouse_pos, dt)
            self.draw()

            pygame.display.flip()

    def update_cursor_visibility(self):
        # During gameplay, the OS cursor is hidden and locked inside the game window.
        # This prevents the cursor from escaping left/right when playing windowed.
        playing = self.state == "PLAYING" and not self.transition.active

        try:
            pygame.mouse.set_visible(not playing)
            pygame.event.set_grab(playing)
        except pygame.error:
            pass

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

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.exit_game()

            if event.type == pygame.KEYDOWN and event.key == pygame.K_m:
                self.toggle_sound()

            if event.type == pygame.KEYDOWN and event.key == pygame.K_F11:
                try:
                    self.toggle_fullscreen()
                    self.settings_screen.fullscreen_on = self.is_fullscreen
                    self.update_cursor_visibility()
                except Exception:
                    self.is_fullscreen = False
                    self.settings_screen.fullscreen_on = False

            if self.transition.active:
                continue

            if self.state == "LOGIN":
                action = self.login_screen.handle_event(event)
                if action:
                    self.audio.play_ui_tap()
                self.handle_login_action(action)

            elif self.state == "CREATE_ACCOUNT":
                action = self.create_account_screen.handle_event(event)
                if action:
                    self.audio.play_ui_tap()
                self.handle_create_account_action(action)

            elif self.state == "HOME":
                action = self.home_screen.handle_event(event)
                if action:
                    self.audio.play_ui_tap()
                self.handle_home_action(action)

            elif self.state == "PLAYING":
                self.handle_playing_event(event)

            elif self.state == "SHOP":
                action = self.shop_screen.handle_event(event)
                if action:
                    self.audio.play_ui_tap()
                self.handle_shop_action(action)

            elif self.state == "PROFILE":
                action = self.profile_screen.handle_event(event)
                if action:
                    self.audio.play_ui_tap()
                self.handle_profile_action(action)

            elif self.state == "RANKS":
                action = self.ranks_screen.handle_event(event)
                if action:
                    self.audio.play_ui_tap()
                self.handle_ranks_action(action)

            elif self.state == "HOW_TO_PLAY":
                action = self.how_to_play_screen.handle_event(event)
                if action:
                    self.audio.play_ui_tap()
                if action == "BACK":
                    self.change_state("HOME", transition_type="return_slide")

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

    def handle_login_action(self, action):
        if action == "LOGIN":
            ok, message = self.login_user(self.login_screen.username, self.login_screen.password)
            self.login_error = message
            self.login_screen.message = message
            if ok:
                self.change_state("HOME", transition_type="fade_black")
        elif action == "CREATE_ACCOUNT":
            self.create_account_screen.clear()
            self.change_state("CREATE_ACCOUNT", transition_type="cyber_grid")
        elif action == "EXIT":
            self.exit_game()

    def handle_create_account_action(self, action):
        if action == "CREATE":
            ok, message = self.create_account(
                self.create_account_screen.username,
                self.create_account_screen.password,
                self.create_account_screen.confirm_password,
            )
            self.create_account_screen.message = message
            if ok:
                self.login_screen.message = message
                self.change_state("LOGIN", transition_type="return_slide")
        elif action == "BACK":
            self.change_state("LOGIN", transition_type="return_slide")

    def handle_profile_action(self, action):
        if action == "SAVE_NAME":
            new_name = self.profile_screen.display_name.strip()
            if len(new_name) >= 2:
                self.profile["display_name"] = new_name
                self.save_profile()
                self.profile_screen.message = "Display name saved."
            else:
                self.profile_screen.message = "Name must be at least 2 characters."
        elif action == "LOGOUT":
            self.logout_user()
        elif action == "BACK":
            self.change_state("HOME", transition_type="return_slide")

    def handle_ranks_action(self, action):
        if action in ("BEST_LEVEL", "BEST_GEMS", "BEST_SCORE"):
            self.ranks_screen.category = action
            self.sync_current_user_to_server(force=True)
            self.sync_users_from_server(force=True)
        elif action == "BACK":
            self.change_state("HOME", transition_type="return_slide")

    def handle_home_action(self, action):
        if action == "PLAY":
            self.change_state("PLAYING", before_change=self.reset_game, transition_type="warp")
        elif action == "SHOP":
            self.change_state("SHOP", transition_type="cyber_grid")
        elif action == "PROFILE":
            self.profile_screen.display_name = self.profile.get("display_name", self.current_user or "Player")
            self.profile_screen.message = ""
            self.change_state("PROFILE", transition_type="cyber_grid")
        elif action == "RANKS":
            self.sync_current_user_to_server(force=True)
            self.sync_users_from_server(force=True)
            self.change_state("RANKS", transition_type="neon_wipe")
        elif action == "HOW_TO_PLAY":
            self.change_state("HOW_TO_PLAY", transition_type="neon_wipe")
        elif action == "SETTINGS":
            self.change_state("SETTINGS", transition_type="cyber_grid")
        elif action == "EXIT":
            self.exit_game()

    def handle_playing_event(self, event):
        if self.death_sequence_active:
            return

        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_ESCAPE, pygame.K_p):
                self.change_state("PAUSED", transition_type="soft_pause")
            if event.key == pygame.K_r:
                self.start_reload()

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.pause_button_rect.collidepoint(event.pos):
                self.change_state("PAUSED", transition_type="soft_pause")

    def handle_settings_action(self, action):
        if action == "BACK":
            self.change_state("HOME", transition_type="return_slide")
        elif action == "TOGGLE_SOUND":
            self.toggle_sound()
        elif action == "TOGGLE_FULLSCREEN":
            self.set_fullscreen(self.settings_screen.fullscreen_on)
        elif action == "CHANGE_DIFFICULTY":
            pass

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

    def handle_shop_action(self, action):
        if action == "BACK":
            self.change_state("HOME", transition_type="return_slide")
            return

        if isinstance(action, tuple) and action[0] == "SHOP_ITEM":
            category, key = action[1], action[2]

            if category == "GUNS":
                item = self.gun_catalog[key]
                owned = key in self.profile["owned_guns"]

                if owned:
                    self.profile["active_gun"] = key
                    self.current_ammo = item["magazine"]
                    self.audio.play_buy()
                elif self.profile["wallet_gems"] >= item["cost"]:
                    self.profile["wallet_gems"] -= item["cost"]
                    self.profile["owned_guns"].append(key)
                    self.profile["active_gun"] = key
                    self.current_ammo = item["magazine"]
                    self.audio.play_buy()
                else:
                    self.add_floating_text("NEED MORE GEMS", SCREEN_WIDTH // 2, 168, (255, 110, 110))
                    self.audio.play_ui_tap()

            elif category == "SKINS":
                item = self.skin_palette[key]
                owned = key in self.profile["owned_skins"]

                if owned:
                    self.profile["active_skin"] = key
                    self.apply_active_skin()
                    self.audio.play_buy()
                elif self.profile["wallet_gems"] >= item["cost"]:
                    self.profile["wallet_gems"] -= item["cost"]
                    self.profile["owned_skins"].append(key)
                    self.profile["active_skin"] = key
                    self.apply_active_skin()
                    self.audio.play_buy()
                else:
                    self.add_floating_text("NEED MORE GEMS", SCREEN_WIDTH // 2, 168, (255, 110, 110))
                    self.audio.play_ui_tap()

            self.save_profile()

    def update(self, mouse_pos, dt):
        self.update_cursor_visibility()
        self.audio.update_for_state(self.state)

        if self.pending_server_sync and self.state != "PLAYING":
            self.sync_current_user_to_server(force=False)

        if self.transition.active:
            self.transition.update(dt)
            return

        if self.state == "LOGIN":
            self.login_screen.update(mouse_pos)
        elif self.state == "CREATE_ACCOUNT":
            self.create_account_screen.update(mouse_pos)
        elif self.state == "HOME":
            self.home_screen.update(mouse_pos)
        elif self.state == "PLAYING":
            self.update_gameplay(mouse_pos, dt)
        elif self.state == "SHOP":
            self.shop_screen.update(mouse_pos)
            self.update_floating_texts(dt)
        elif self.state == "PROFILE":
            self.profile_screen.update(mouse_pos)
        elif self.state == "RANKS":
            self.ranks_screen.update(mouse_pos)
        elif self.state == "HOW_TO_PLAY":
            self.how_to_play_screen.update(mouse_pos)
        elif self.state == "SETTINGS":
            self.settings_screen.update(mouse_pos)
        elif self.state == "PAUSED":
            self.pause_screen.update(mouse_pos)
        elif self.state == "GAME_OVER":
            self.game_over_screen.update(mouse_pos, self.profile["wallet_gems"])

    def update_gameplay(self, mouse_pos, dt):
        if self.death_sequence_active:
            self.update_death_sequence(dt)
            self.update_particles(dt)
            return

        if self.level_scene_active:
            self.update_level_clear_scene(dt)
            self.update_floating_texts(dt)
            return

        if self.next_level_fade_timer > 0:
            self.next_level_fade_timer = max(0, self.next_level_fade_timer - dt)

        self.game_time += dt
        self.score += dt * (2.0 + self.level * 0.12)

        keys = pygame.key.get_pressed()
        self.current_auto_target = self.get_nearest_enemy(max_range=self.auto_target_range)
        aim_target = None
        if self.current_auto_target:
            aim_target = (self.current_auto_target["x"], self.current_auto_target["y"])
        self.player.update(keys, dt, mouse_pos, aim_target=aim_target)

        for skill in list(self.active_skills):
            if self.active_skills[skill] > 0:
                self.active_skills[skill] = max(0, self.active_skills[skill] - dt)

        self.update_spawns(dt)
        self.update_shooting(mouse_pos, dt)
        self.update_bullets(dt)
        self.update_zombies(dt)
        self.update_gems(dt)
        self.update_skills(dt)
        self.update_particles(dt)
        self.update_floating_texts(dt)
        self.check_level_complete()

        if self.player_hp <= 0:
            self.start_death_sequence()

    def update_level_clear_scene(self, dt):
        self.level_scene_timer += dt

        # Cinematic timing:
        # 0.0-0.8 game fades to black
        # 0.8-1.5 cinematic fades in
        # 1.5-3.6 ship descends
        # 3.6-5.5 player walks to ship
        # 5.5-7.2 ship lifts away
        # 7.2-8.2 fade to next level
        if self.level_scene_timer >= 8.2:
            self.finish_level_scene()

    def update_spawns(self, dt):
        active_normal = sum(1 for zombie in self.zombies if not zombie.get("boss"))
        active_boss = sum(1 for zombie in self.zombies if zombie.get("boss"))

        # Level-based active caps. Infinite levels keep increasing, but active enemies stay readable.
        normal_active_cap = min(12 + self.level * 2, 32)
        boss_active_cap = 1 + min(2, self.level // 5)

        self.spawn_timer -= dt
        if self.spawn_timer <= 0:
            if self.level_zombies_spawned < self.level_zombie_total and active_normal < normal_active_cap:
                self.spawn_zombie()
                self.level_zombies_spawned += 1

            base = max(0.28, 0.70 - self.level * 0.018)
            self.spawn_timer = random.uniform(base * 0.75, base * 1.25)

        # Boss spawning is tied to progress. Example LV1 has 4 bosses, spread through the level.
        if self.level_bosses_spawned < self.level_boss_total and active_boss < boss_active_cap:
            next_threshold = int(self.level_zombie_total * ((self.level_bosses_spawned + 1) / (self.level_boss_total + 1)))
            if self.level_zombies_killed >= next_threshold:
                self.spawn_boss()
                self.level_bosses_spawned += 1

        self.gem_spawn_timer -= dt
        if self.gem_spawn_timer <= 0:
            self.spawn_gem()
            self.gem_spawn_timer = random.uniform(3.8, 6.5)

        self.skill_spawn_timer -= dt
        if self.skill_spawn_timer <= 0:
            self.spawn_skill()
            self.skill_spawn_timer = random.uniform(10.0, 15.0)

        if self.boss_warning_timer > 0:
            self.boss_warning_timer -= dt

    def spawn_at_edge(self):
        side = random.choice(["top", "bottom", "left", "right"])
        if side == "top":
            return random.randint(20, SCREEN_WIDTH - 20), -40
        if side == "bottom":
            return random.randint(20, SCREEN_WIDTH - 20), SCREEN_HEIGHT + 40
        if side == "left":
            return -40, random.randint(20, SCREEN_HEIGHT - 20)
        return SCREEN_WIDTH + 40, random.randint(20, SCREEN_HEIGHT - 20)

    def spawn_zombie(self):
        x, y = self.spawn_at_edge()
        level_bonus = max(0, self.level - 1)
        hp = 30 + level_bonus * 6
        speed = random.uniform(54, 76) + min(36, level_bonus * 3.5)

        self.zombies.append({
            "x": x,
            "y": y,
            "radius": random.randint(15, 20),
            "hp": hp,
            "max_hp": hp,
            "speed": speed,
            "damage": 10 + min(8, level_bonus),
            "hit_cd": 0,
            "boss": False,
        })

    def spawn_boss(self):
        x, y = self.spawn_at_edge()
        level_bonus = max(0, self.level - 1)
        hp = 420 + level_bonus * 90
        boss = {
            "x": x,
            "y": y,
            "radius": 46,
            "hp": hp,
            "max_hp": hp,
            "speed": 42 + min(16, level_bonus * 1.8),
            "damage": 18 + min(14, level_bonus * 2),
            "hit_cd": 0,
            "boss": True,
        }
        self.boss = boss
        self.zombies.append(boss)
        self.boss_active = True
        self.boss_warning_timer = 4.0
        self.audio.play_boss_warning()
        self.audio.set_boss_active(True)
        self.audio.play_for_state("PLAYING")
        self.add_floating_text("BOSS INCOMING", SCREEN_WIDTH // 2, 210, (255, 75, 75))

    def spawn_gem(self, x=None, y=None, amount=1):
        if x is None:
            x = random.randint(70, SCREEN_WIDTH - 70)
        if y is None:
            y = random.randint(110, SCREEN_HEIGHT - 90)

        self.gems.append({
            "x": x,
            "y": y,
            "amount": amount,
            "life": 14,
            "bob": random.random() * math.tau,
        })

    def spawn_skill(self):
        skill_type = random.choice(["RAPID", "INFINITE", "IMMORTAL"])
        x = random.randint(80, SCREEN_WIDTH - 80)
        y = random.randint(120, SCREEN_HEIGHT - 100)

        self.skills.append({
            "x": x,
            "y": y,
            "type": skill_type,
            "life": 13,
            "bob": random.random() * math.tau,
        })

    def get_nearest_enemy(self, max_range=9999, reticle_pos=None, require_reticle=False):
        if not self.zombies:
            return None

        px, py = self.player.get_position()
        best = None
        best_distance = max_range

        for zombie in self.zombies:
            distance = math.hypot(zombie["x"] - px, zombie["y"] - py)
            if distance < best_distance:
                best_distance = distance
                best = zombie

        return best

    def get_assisted_aim_point(self, mouse_pos=None, target=None):
        if target is None:
            target = self.get_nearest_enemy(max_range=self.auto_target_range)

        if target is None:
            px, py = self.player.get_position()
            return (
                px + math.cos(self.player.aim_angle) * 200,
                py + math.sin(self.player.aim_angle) * 200,
            )

        return (target["x"], target["y"])

    def update_shooting(self, mouse_pos, dt):
        self.shoot_cooldown = max(0, self.shoot_cooldown - dt)

        if self.reload_timer > 0:
            self.reload_timer -= dt
            if self.reload_timer <= 0:
                self.current_ammo = self.get_active_gun()["magazine"]
                self.add_floating_text("RELOADED", self.player.x, self.player.y - 42, (180, 220, 255))
            return

        self.update_burst_queue(dt)

        mouse_buttons = pygame.mouse.get_pressed()
        keys = pygame.key.get_pressed()

        target = self.get_nearest_enemy(max_range=self.auto_target_range)
        self.current_auto_target = target

        wants_manual_fire = mouse_buttons[0] or keys[pygame.K_SPACE]
        wants_auto_fire = self.auto_fire_enabled and target is not None

        if wants_manual_fire or wants_auto_fire:
            aim_point = self.get_assisted_aim_point(mouse_pos, target)
            self.try_shoot(aim_point)

    def has_skill(self, skill_name):
        return self.active_skills.get(skill_name, 0) > 0

    def try_shoot(self, mouse_pos):
        gun = self.get_active_gun()
        cooldown = gun["cooldown"] * (0.45 if self.has_skill("RAPID") else 1.0)

        if self.shoot_cooldown > 0:
            return

        if self.current_ammo <= 0 and not self.has_skill("INFINITE"):
            self.start_reload()
            return

        self.shoot_cooldown = cooldown

        if gun.get("burst_count", 1) > 1:
            count = gun["burst_count"]
            gap = gun.get("burst_gap", 0.06)
            self.burst_queue = [{"timer": i * gap, "mouse": mouse_pos} for i in range(count)]
        else:
            self.fire_bullet(mouse_pos)

    def update_burst_queue(self, dt):
        if not self.burst_queue:
            return

        remaining = []
        for shot in self.burst_queue:
            shot["timer"] -= dt
            if shot["timer"] <= 0:
                if self.current_ammo > 0 or self.has_skill("INFINITE"):
                    self.fire_bullet(shot["mouse"])
                else:
                    self.start_reload()
                    break
            else:
                remaining.append(shot)

        self.burst_queue = remaining

    def fire_bullet(self, mouse_pos):
        gun = self.get_active_gun()
        px, py = self.player.get_position()
        angle = math.atan2(mouse_pos[1] - py, mouse_pos[0] - px)

        bullets = gun.get("bullets", 1)
        spread = gun.get("spread", 0)

        for i in range(bullets):
            shot_angle = angle + random.uniform(-spread, spread)
            speed = gun["bullet_speed"]
            muzzle_x = px + math.cos(shot_angle) * 24
            muzzle_y = py + math.sin(shot_angle) * 24

            self.bullets.append({
                "x": muzzle_x,
                "y": muzzle_y,
                "vx": math.cos(shot_angle) * speed,
                "vy": math.sin(shot_angle) * speed,
                "damage": gun["damage"],
                "life": 1.05,
                "radius": 7,
                "color": self.player.glow_color,
                "homing": 0.0,
            })

            self.spawn_muzzle_particle(muzzle_x, muzzle_y, shot_angle)

        if not self.has_skill("INFINITE"):
            self.current_ammo -= 1

        self.audio.play_weapon(gun.get("sfx", "PISTOL"))

    def start_reload(self):
        if self.has_skill("INFINITE"):
            return

        gun = self.get_active_gun()
        if self.current_ammo >= gun["magazine"]:
            return

        if self.reload_timer <= 0:
            self.reload_timer = gun["reload"]
            self.add_floating_text("RELOADING", self.player.x, self.player.y - 42, (220, 220, 220))

    def update_bullets(self, dt):
        alive_bullets = []

        for bullet in self.bullets:
            bullet["x"] += bullet["vx"] * dt
            bullet["y"] += bullet["vy"] * dt
            bullet["life"] -= dt

            if bullet["life"] <= 0:
                continue

            if not (-120 <= bullet["x"] <= SCREEN_WIDTH + 120 and -120 <= bullet["y"] <= SCREEN_HEIGHT + 120):
                continue

            hit = False

            for zombie in list(self.zombies):
                # Forgiving hitbox: makes shooting feel much less frustrating.
                hit_padding = 8 if not zombie.get("boss") else 12
                if math.hypot(bullet["x"] - zombie["x"], bullet["y"] - zombie["y"]) <= bullet["radius"] + zombie["radius"] + hit_padding:
                    zombie["hp"] -= bullet["damage"]
                    self.spawn_hit_particles(zombie["x"], zombie["y"], zombie.get("boss", False))
                    self.audio.play_enemy_hit()
                    hit = True

                    if zombie["hp"] <= 0:
                        self.kill_zombie(zombie)

                    break

            if not hit:
                alive_bullets.append(bullet)

        self.bullets = alive_bullets

    def update_zombies(self, dt):
        px, py = self.player.get_position()

        for zombie in list(self.zombies):
            dx = px - zombie["x"]
            dy = py - zombie["y"]
            distance = max(0.001, math.hypot(dx, dy))

            zombie["x"] += dx / distance * zombie["speed"] * dt
            zombie["y"] += dy / distance * zombie["speed"] * dt
            zombie["hit_cd"] = max(0, zombie["hit_cd"] - dt)

            if distance < self.player.radius + zombie["radius"]:
                if zombie["hit_cd"] <= 0:
                    zombie["hit_cd"] = 0.75 if not zombie.get("boss") else 1.05
                    if not self.has_skill("IMMORTAL"):
                        self.player_hp -= zombie["damage"]
                        self.add_floating_text(f"-{int(zombie['damage'])} HP", self.player.x, self.player.y - 54, (255, 100, 100))
                    else:
                        self.add_floating_text("IMMORTAL", self.player.x, self.player.y - 54, (255, 245, 120))

    def kill_zombie(self, zombie):
        if zombie in self.zombies:
            self.zombies.remove(zombie)

        if zombie.get("boss"):
            self.level_bosses_killed = min(self.level_boss_total, self.level_bosses_killed + 1)
            self.boss_active = any(z.get("boss") for z in self.zombies)
            self.boss = next((z for z in self.zombies if z.get("boss")), None)

            if not self.boss_active:
                self.audio.set_boss_active(False)
                self.audio.play_for_state("PLAYING")

            self.add_floating_text("BOSS DEFEATED +25G", SCREEN_WIDTH // 2, 210, (255, 230, 120))
            for _ in range(25):
                self.spawn_gem(zombie["x"] + random.randint(-80, 80), zombie["y"] + random.randint(-80, 80), amount=1)
            self.score += 500 + self.level * 70
            self.check_level_complete()
            return

        self.level_zombies_killed = min(self.level_zombie_total, self.level_zombies_killed + 1)
        self.score += 25 + self.level * 3
        if random.random() < 0.58:
            self.spawn_gem(zombie["x"], zombie["y"], amount=1)

        self.check_level_complete()

    def update_gems(self, dt):
        alive = []
        px, py = self.player.get_position()

        for gem in self.gems:
            gem["life"] -= dt
            gem["bob"] += dt * 4

            if gem["life"] <= 0:
                continue

            distance = math.hypot(px - gem["x"], py - gem["y"])

            if distance < 120:
                pull = min(1, 8 * dt)
                gem["x"] += (px - gem["x"]) * pull
                gem["y"] += (py - gem["y"]) * pull

            if distance <= self.player.radius + 34:
                amount = gem["amount"]
                self.run_gems += amount
                self.profile["wallet_gems"] += amount
                self.profile["total_gems_collected"] = self.profile.get("total_gems_collected", 0) + amount
                self.profile["best_gems"] = max(self.profile.get("best_gems", 0), self.profile["wallet_gems"])
                self.save_profile()
                self.audio.play_gem_collect()
                self.add_floating_text(f"+{amount} GEM", gem["x"], gem["y"] - 24, (80, 190, 255))
                continue

            alive.append(gem)

        self.gems = alive

    def update_skills(self, dt):
        alive = []
        px, py = self.player.get_position()

        for skill in self.skills:
            skill["life"] -= dt
            skill["bob"] += dt * 5

            if skill["life"] <= 0:
                continue

            if math.hypot(px - skill["x"], py - skill["y"]) <= self.player.radius + 38:
                duration = {"RAPID": 10.0, "INFINITE": 10.0, "IMMORTAL": 7.5}[skill["type"]]
                self.active_skills[skill["type"]] = duration
                self.audio.play_skill_pickup()
                self.add_floating_text(skill["type"], skill["x"], skill["y"] - 28, (255, 230, 120))
                continue

            alive.append(skill)

        self.skills = alive

    def spawn_muzzle_particle(self, x, y, angle):
        for _ in range(3):
            a = angle + random.uniform(-0.45, 0.45)
            s = random.uniform(80, 180)
            self.particles.append({
                "x": x,
                "y": y,
                "vx": math.cos(a) * s,
                "vy": math.sin(a) * s,
                "life": 0.16,
                "max": 0.16,
                "size": random.randint(2, 4),
                "color": (255, 220, 120),
            })

    def spawn_hit_particles(self, x, y, boss=False):
        count = 12 if boss else 6
        color = (255, 70, 70) if not boss else (255, 55, 120)
        for _ in range(count):
            a = random.uniform(0, math.tau)
            s = random.uniform(45, 160)
            self.particles.append({
                "x": x,
                "y": y,
                "vx": math.cos(a) * s,
                "vy": math.sin(a) * s,
                "life": 0.28,
                "max": 0.28,
                "size": random.randint(2, 5),
                "color": color,
            })

    def update_particles(self, dt):
        alive = []
        for p in self.particles:
            p["life"] -= dt
            if p["life"] <= 0:
                continue
            p["x"] += p["vx"] * dt
            p["y"] += p["vy"] * dt
            p["vx"] *= 0.96
            p["vy"] *= 0.96
            alive.append(p)
        self.particles = alive[-220:]

    def add_floating_text(self, text, x, y, color):
        self.floating_texts.append({
            "text": text,
            "x": x,
            "y": y,
            "color": color,
            "life": 1.05,
            "max": 1.05,
        })

    def update_floating_texts(self, dt):
        alive = []
        for item in self.floating_texts:
            item["life"] -= dt
            item["y"] -= 32 * dt
            if item["life"] > 0:
                alive.append(item)
        self.floating_texts = alive[-20:]

    def start_death_sequence(self):
        if self.death_sequence_active:
            return

        x, y = self.player.get_position()
        self.death_position = (x, y)
        self.death_sequence_active = True
        self.death_sequence_elapsed = 0
        self.death_particles = []
        self.audio.play_player_burst()

        for _ in range(60):
            angle = random.uniform(0, math.tau)
            speed = random.uniform(90, 430)
            self.death_particles.append({
                "x": x,
                "y": y,
                "vx": math.cos(angle) * speed,
                "vy": math.sin(angle) * speed,
                "life": random.uniform(0.35, self.death_sequence_duration),
                "max": self.death_sequence_duration,
                "size": random.randint(2, 7),
            })

    def update_death_sequence(self, dt):
        self.death_sequence_elapsed += dt

        alive = []
        for p in self.death_particles:
            p["life"] -= dt
            if p["life"] <= 0:
                continue
            p["x"] += p["vx"] * dt
            p["y"] += p["vy"] * dt
            p["vx"] *= 0.985
            p["vy"] *= 0.985
            alive.append(p)
        self.death_particles = alive

        if self.death_sequence_elapsed >= self.death_sequence_duration:
            self.game_over()

    def game_over(self):
        final_score = int(self.score)
        self.profile["best_score"] = max(self.profile.get("best_score", 0), final_score)
        self.profile["best_level"] = max(self.profile.get("best_level", 1), self.level)
        self.profile["best_gems"] = max(self.profile.get("best_gems", 0), self.profile.get("wallet_gems", 0))
        self.save_profile()
        self.sync_current_user_to_server(force=True)
        self.audio.set_boss_active(False)
        self.change_state("GAME_OVER", transition_type="crash_glitch")

    def draw(self):
        if self.transition.active:
            self.draw_current_state()
            new_surface = self.screen.copy()
            self.transition.draw(self.screen, new_surface)
            return

        self.draw_current_state()

    def draw_current_state(self):
        if self.state == "LOGIN":
            self.login_screen.draw(self.screen)
        elif self.state == "CREATE_ACCOUNT":
            self.create_account_screen.draw(self.screen)
        elif self.state == "HOME":
            self.home_screen.draw(self.screen, display_name=self.profile.get("display_name", self.current_user or "Player"), server_online=self.server_online, server_url=self.server_url)

        elif self.state == "PLAYING":
            self.draw_gameplay()

        elif self.state == "SHOP":
            self.shop_screen.draw(
                self.screen,
                wallet_gems=self.profile["wallet_gems"],
                owned_guns=self.profile["owned_guns"],
                active_gun=self.profile["active_gun"],
                owned_skins=self.profile["owned_skins"],
                active_skin=self.profile["active_skin"],
            )
            self.draw_floating_texts()

        elif self.state == "PROFILE":
            self.profile_screen.draw(self.screen, self.profile, self.current_user)

        elif self.state == "RANKS":
            self.ranks_screen.draw(self.screen, self.get_rank_entries(self.ranks_screen.category))

        elif self.state == "HOW_TO_PLAY":
            self.how_to_play_screen.draw(self.screen)

        elif self.state == "SETTINGS":
            self.settings_screen.draw(self.screen)

        elif self.state == "PAUSED":
            self.draw_gameplay()
            self.pause_screen.draw(self.screen)

        elif self.state == "GAME_OVER":
            self.game_over_screen.draw(
                self.screen,
                int(self.score),
                self.profile.get("best_score", 0),
                self.run_gems,
                self.profile["wallet_gems"],
            )

        self.draw_music_hint()

    def draw_gameplay(self):
        if self.level_scene_active:
            self.draw_level_clear_scene()
            return

        self.draw_gameplay_background()
        self.draw_auto_target_system()

        for gem in self.gems:
            self.draw_gem(gem)

        for skill in self.skills:
            self.draw_skill(skill)

        for bullet in self.bullets:
            pygame.draw.circle(self.screen, bullet["color"], (int(bullet["x"]), int(bullet["y"])), bullet["radius"])
            pygame.draw.circle(self.screen, WHITE, (int(bullet["x"]), int(bullet["y"])), max(1, bullet["radius"] // 2))

        for zombie in self.zombies:
            self.draw_zombie(zombie)

        self.draw_particles()

        if self.death_sequence_active:
            self.draw_death_explosion()
        else:
            self.player.draw(self.screen)

        self.draw_hud()
        self.draw_pause_button()
        self.draw_floating_texts()

        if self.next_level_fade_timer > 0:
            fade = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            alpha = int(230 * min(1, self.next_level_fade_timer / 1.15))
            fade.fill((0, 0, 0, alpha))
            self.screen.blit(fade, (0, 0))
            draw_text(self.screen, f"LEVEL {self.level}", 54, SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2, WHITE, bold=True)

    def draw_auto_target_system(self):
        px, py = self.player.get_position()
        px, py = int(px), int(py)

        target = self.current_auto_target or self.get_nearest_enemy(max_range=self.auto_target_range)

        surface = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)

        # Cool but simple auto-target ring around player.
        pygame.draw.circle(surface, (80, 190, 255, 22), (px, py), self.auto_target_range, 1)
        pygame.draw.circle(surface, (80, 190, 255, 70), (px, py), 44, 2)

        # Small rotating scanner ticks.
        t = pygame.time.get_ticks() * 0.001
        for i in range(4):
            angle = t * 1.7 + i * math.pi / 2
            x1 = px + math.cos(angle) * 50
            y1 = py + math.sin(angle) * 50
            x2 = px + math.cos(angle) * 70
            y2 = py + math.sin(angle) * 70
            pygame.draw.line(surface, (80, 190, 255, 120), (x1, y1), (x2, y2), 2)

        if target:
            tx, ty = int(target["x"]), int(target["y"])
            pygame.draw.line(surface, (255, 90, 90, 90), (px, py), (tx, ty), 2)
            pygame.draw.circle(surface, (255, 80, 80, 125), (tx, ty), int(target["radius"]) + 12, 2)
            pygame.draw.circle(surface, (255, 220, 120, 110), (tx, ty), int(target["radius"]) + 22, 1)

        self.screen.blit(surface, (0, 0))

    def draw_level_clear_scene(self):
        t = self.level_scene_timer
        self.draw_gameplay_background()

        # Cinematic background stars.
        for i in range(34):
            x = int((i * 107 + t * 18) % SCREEN_WIDTH)
            y = int((i * 61 + t * 9) % SCREEN_HEIGHT)
            pygame.draw.circle(self.screen, (90, 95, 125), (x, y), 1)

        center_x = SCREEN_WIDTH // 2
        ground_y = SCREEN_HEIGHT // 2 + 140

        # Ship position and player position by phase.
        if t < 1.5:
            ship_y = -120
            player_x = center_x
            player_y = ground_y
        elif t < 3.6:
            k = min(1, (t - 1.5) / 2.1)
            ship_y = -120 + k * 250
            player_x = center_x
            player_y = ground_y
        elif t < 5.5:
            ship_y = 130
            k = min(1, (t - 3.6) / 1.9)
            player_x = center_x + k * 145
            player_y = ground_y - k * 55
        else:
            k = min(1, (t - 5.5) / 1.7)
            ship_y = 130 - k * 360
            player_x = center_x + 145
            player_y = ground_y - 55 - k * 360

        self.draw_cinematic_ship(center_x + 145, ship_y)
        self.draw_cinematic_player(player_x, player_y)

        draw_text(self.screen, f"LEVEL {self.level} CLEAR", 44, SCREEN_WIDTH // 2, 92, WHITE, bold=True)
        draw_text(self.screen, "Extraction complete. Next sector incoming...", 24, SCREEN_WIDTH // 2, 134, LIGHT_GRAY, bold=True)

        # Fade in/out.
        if t < 0.8:
            alpha = int(255 * (t / 0.8))
        elif t < 1.5:
            alpha = int(255 * (1 - (t - 0.8) / 0.7))
        elif t > 7.2:
            alpha = int(255 * min(1, (t - 7.2) / 1.0))
        else:
            alpha = 0

        if alpha > 0:
            overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, alpha))
            self.screen.blit(overlay, (0, 0))

    def draw_cinematic_ship(self, x, y):
        x, y = int(x), int(y)
        ship = pygame.Surface((230, 150), pygame.SRCALPHA)

        # Glowing UFO / flying vehicle.
        pygame.draw.ellipse(ship, (60, 80, 110, 210), (20, 55, 190, 58))
        pygame.draw.ellipse(ship, (130, 170, 230, 230), (52, 30, 126, 58))
        pygame.draw.ellipse(ship, (235, 245, 255, 210), (78, 42, 74, 24))
        pygame.draw.ellipse(ship, (25, 28, 38, 255), (20, 55, 190, 58), 3)

        for lx in (52, 88, 124, 160):
            pygame.draw.circle(ship, (80, 190, 255, 230), (lx, 88), 7)

        beam = pygame.Surface((180, 210), pygame.SRCALPHA)
        pygame.draw.polygon(beam, (80, 190, 255, 38), [(60, 0), (120, 0), (180, 210), (0, 210)])
        self.screen.blit(beam, (x - 90, y + 78))
        self.screen.blit(ship, (x - 115, y - 75))

    def draw_cinematic_player(self, x, y):
        x, y = int(x), int(y)
        glow = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        pygame.draw.circle(glow, (*self.player.glow_color, 55), (x, y), 36)
        self.screen.blit(glow, (0, 0))
        pygame.draw.circle(self.screen, self.player.fill_color, (x, y), self.player.radius)
        pygame.draw.circle(self.screen, WHITE, (x - 6, y - 6), 5)
        pygame.draw.circle(self.screen, WHITE, (x, y), self.player.radius, 2)

    def draw_gameplay_background(self):
        self.screen.fill(BLACK)
        t = pygame.time.get_ticks() * 0.001

        for i in range(24):
            x = int((i * 117 + t * 32) % SCREEN_WIDTH)
            y = int((i * 77 + t * 26) % SCREEN_HEIGHT)
            pygame.draw.circle(self.screen, (22, 22, 32), (x, y), 1)

        for i in range(14):
            x = int((i * 141 + t * 18) % SCREEN_WIDTH)
            pygame.draw.line(self.screen, (20, 20, 30), (x, 0), (x + 55, SCREEN_HEIGHT), 1)

    def draw_zombie(self, zombie):
        x, y = int(zombie["x"]), int(zombie["y"])
        r = int(zombie["radius"])
        boss = zombie.get("boss", False)

        body_color = (185, 30, 40) if not boss else (185, 20, 90)
        glow_color = (255, 45, 55) if not boss else (255, 45, 150)

        glow = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        pygame.draw.circle(glow, (*glow_color, 30), (x, y), r + 14)
        self.screen.blit(glow, (0, 0))

        if boss:
            pygame.draw.circle(self.screen, body_color, (x, y), r)
            pygame.draw.circle(self.screen, (90, 5, 20), (x, y), r, 4)
            pygame.draw.circle(self.screen, WHITE, (x - 14, y - 9), 5)
            pygame.draw.circle(self.screen, WHITE, (x + 14, y - 9), 5)
        else:
            rect = pygame.Rect(x - r, y - r, r * 2, r * 2)
            pygame.draw.rect(self.screen, body_color, rect, border_radius=7)
            pygame.draw.rect(self.screen, (95, 10, 16), rect, 2, border_radius=7)
            pygame.draw.circle(self.screen, WHITE, (x - 6, y - 4), 3)
            pygame.draw.circle(self.screen, WHITE, (x + 6, y - 4), 3)

        # HP bar.
        width = r * 2
        hp_ratio = max(0, zombie["hp"] / zombie["max_hp"])
        bar = pygame.Rect(x - width // 2, y - r - 14, width, 5)
        pygame.draw.rect(self.screen, (35, 35, 42), bar, border_radius=3)
        pygame.draw.rect(self.screen, (255, 70, 70), (bar.x, bar.y, int(width * hp_ratio), 5), border_radius=3)

    def draw_gem(self, gem):
        x = int(gem["x"])
        y = int(gem["y"] + math.sin(gem["bob"]) * 5)
        points = [(x, y - 12), (x + 12, y), (x, y + 12), (x - 12, y)]
        pygame.draw.polygon(self.screen, (80, 190, 255), points)
        pygame.draw.polygon(self.screen, WHITE, points, 1)

    def draw_skill(self, skill):
        x = int(skill["x"])
        y = int(skill["y"] + math.sin(skill["bob"]) * 6)
        colors = {
            "RAPID": (255, 210, 70),
            "INFINITE": (80, 220, 255),
            "IMMORTAL": (255, 110, 220),
        }
        color = colors.get(skill["type"], WHITE)
        pygame.draw.circle(self.screen, color, (x, y), 17)
        pygame.draw.circle(self.screen, WHITE, (x, y), 17, 2)
        label = {"RAPID": "R", "INFINITE": "∞", "IMMORTAL": "I"}[skill["type"]]
        draw_text(self.screen, label, 20, x, y - 1, BLACK, bold=True)

    def draw_particles(self):
        surface = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        for p in self.particles:
            progress = max(0, min(1, p["life"] / p["max"]))
            alpha = int(180 * progress)
            pygame.draw.circle(surface, (*p["color"], alpha), (int(p["x"]), int(p["y"])), p["size"])
        self.screen.blit(surface, (0, 0))

    def draw_death_explosion(self):
        progress = min(1, self.death_sequence_elapsed / self.death_sequence_duration)
        x, y = self.death_position

        surface = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        pygame.draw.circle(surface, (255, 255, 255, int(210 * (1 - progress))), (int(x), int(y)), int(20 + 110 * progress), 3)

        for p in self.death_particles:
            ratio = max(0, min(1, p["life"] / p["max"]))
            pygame.draw.circle(surface, (255, 255, 255, int(230 * ratio)), (int(p["x"]), int(p["y"])), p["size"])
            pygame.draw.circle(surface, (255, 55, 55, int(90 * ratio)), (int(p["x"]), int(p["y"])), max(1, p["size"] // 2))

        self.screen.blit(surface, (0, 0))

    def draw_hud(self):
        # Top panels.
        pygame.draw.rect(self.screen, (12, 12, 18), (18, 18, 284, 108), border_radius=14)
        pygame.draw.rect(self.screen, (70, 70, 86), (18, 18, 284, 108), 2, border_radius=14)

        draw_text(self.screen, f"HP {max(0, int(self.player_hp))}/100", 18, 34, 30, WHITE, center=False, bold=True)
        hp_w = int(188 * max(0, self.player_hp / self.max_hp))
        pygame.draw.rect(self.screen, (40, 40, 48), (34, 56, 188, 10), border_radius=6)
        pygame.draw.rect(self.screen, (255, 70, 70), (34, 56, hp_w, 10), border_radius=6)

        gun = self.get_active_gun()
        ammo_text = "∞" if self.has_skill("INFINITE") else f"{self.current_ammo}/{gun['magazine']}"
        if self.reload_timer > 0:
            ammo_text = "RELOAD"
        draw_text(self.screen, f"{gun['name']}  {ammo_text}", 16, 34, 76, LIGHT_GRAY, center=False, bold=True)
        draw_text(self.screen, "WASD MOVE  |  AUTO TARGET ON", 13, 34, 96, (130, 210, 255), center=False, bold=True)
        draw_text(self.screen, f"SCORE {int(self.score)}", 16, 34, 112, LIGHT_GRAY, center=False, bold=True)

        pygame.draw.rect(self.screen, (12, 12, 18), (SCREEN_WIDTH - 214, 18, 190, 62), border_radius=14)
        pygame.draw.rect(self.screen, (70, 70, 86), (SCREEN_WIDTH - 214, 18, 190, 62), 2, border_radius=14)
        draw_text(self.screen, f"GEMS {self.profile['wallet_gems']}", 19, SCREEN_WIDTH - 198, 32, (80, 190, 255), center=False, bold=True)
        draw_text(self.screen, f"RUN +{self.run_gems}", 15, SCREEN_WIDTH - 198, 57, LIGHT_GRAY, center=False, bold=True)

        self.draw_level_status()
        self.draw_skill_status()

        if self.boss_warning_timer > 0:
            alpha = int(160 + 80 * math.sin(pygame.time.get_ticks() * 0.018))
            warning = pygame.Surface((SCREEN_WIDTH, 58), pygame.SRCALPHA)
            warning.fill((120, 0, 20, alpha))
            self.screen.blit(warning, (0, 132))
            draw_text(self.screen, "BOSS INCOMING", 34, SCREEN_WIDTH // 2, 160, WHITE, bold=True)

    def draw_level_status(self):
        zombie_remaining, boss_remaining = self.get_level_remaining()

        panel = pygame.Rect(18, 138, 288, 126)
        pygame.draw.rect(self.screen, (12, 12, 18), panel, border_radius=14)
        pygame.draw.rect(self.screen, (70, 70, 86), panel, 2, border_radius=14)

        draw_text(self.screen, f"LEVEL {self.level}", 27, 34, 152, (255, 230, 120), center=False, bold=True)
        draw_text(self.screen, f"ZOMBIES: {zombie_remaining}", 20, 34, 187, WHITE, center=False, bold=True)
        draw_text(self.screen, f"BOSSES: {boss_remaining}", 20, 34, 215, (255, 110, 130), center=False, bold=True)
        draw_text(self.screen, "NEXT: +50Z / +3B", 15, 34, 242, (130, 210, 255), center=False, bold=True)

    def draw_skill_status(self):
        x = SCREEN_WIDTH // 2 - 190
        y = 24
        labels = [("RAPID", (255, 210, 70)), ("INFINITE", (80, 220, 255)), ("IMMORTAL", (255, 110, 220))]
        for i, (name, color) in enumerate(labels):
            remaining = self.active_skills.get(name, 0)
            if remaining <= 0:
                continue
            rect = pygame.Rect(x, y + i * 32, 380, 23)
            pygame.draw.rect(self.screen, (15, 15, 22), rect, border_radius=10)
            pygame.draw.rect(self.screen, color, rect, 2, border_radius=10)
            draw_text(self.screen, f"{name}: {remaining:.1f}s", 16, rect.centerx, rect.centery, WHITE, bold=True)

    def draw_pause_button(self):
        mouse_pos = pygame.mouse.get_pos()
        hovered = self.pause_button_rect.collidepoint(mouse_pos)
        fill_color = (25, 10, 14) if hovered else DARK_GRAY
        border_color = RED if hovered else GRAY

        pygame.draw.rect(self.screen, fill_color, self.pause_button_rect, border_radius=10)
        pygame.draw.rect(self.screen, border_color, self.pause_button_rect, 2, border_radius=10)

        cx, cy = self.pause_button_rect.center
        pygame.draw.rect(self.screen, WHITE, pygame.Rect(cx - 9, cy - 10, 5, 20), border_radius=2)
        pygame.draw.rect(self.screen, WHITE, pygame.Rect(cx + 4, cy - 10, 5, 20), border_radius=2)

    def draw_floating_texts(self):
        for item in self.floating_texts:
            ratio = max(0, min(1, item["life"] / item["max"]))
            color = item["color"]
            draw_text(self.screen, item["text"], 19, int(item["x"]), int(item["y"]), color, bold=True)

    def draw_music_hint(self):
        if not self.audio.available:
            return
        label = "M: MUSIC OFF" if self.audio.muted else "M: MUSIC ON"
        color = GRAY if self.audio.muted else LIGHT_GRAY
        draw_text(self.screen, label, SMALL_FONT_SIZE, 18, SCREEN_HEIGHT - 30, color, center=False)

    def set_fullscreen(self, enabled):
        # SAFE fullscreen toggle.
        # pygame.SCALED can crash on some Windows computers with:
        # "failed to create renderer", so we do NOT use SCALED here.
        try:
            if enabled:
                try:
                    self.screen = pygame.display.set_mode(
                        (SCREEN_WIDTH, SCREEN_HEIGHT),
                        pygame.FULLSCREEN,
                    )
                    self.is_fullscreen = True
                    self.settings_screen.fullscreen_on = True
                except Exception:
                    self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
                    self.is_fullscreen = False
                    self.settings_screen.fullscreen_on = False
                    try:
                        self.add_floating_text(
                            "FULLSCREEN NOT SUPPORTED ON THIS PC",
                            SCREEN_WIDTH // 2,
                            180,
                            (255, 110, 110),
                        )
                    except Exception:
                        pass
            else:
                self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
                self.is_fullscreen = False
                self.settings_screen.fullscreen_on = False

        except Exception:
            # Last-resort safety: keep game alive no matter what.
            try:
                self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
            except Exception:
                pass
            self.is_fullscreen = False
            try:
                self.settings_screen.fullscreen_on = False
            except Exception:
                pass

        try:
            pygame.display.set_caption(GAME_TITLE)
            self.update_cursor_visibility()
        except Exception:
            pass

        self.pause_button_rect = pygame.Rect(SCREEN_WIDTH - 72, 24, 46, 46)

    def toggle_fullscreen(self):
        try:
            self.set_fullscreen(not self.is_fullscreen)
        except Exception:
            self.is_fullscreen = False
            try:
                self.settings_screen.fullscreen_on = False
                self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
            except Exception:
                pass

    def toggle_sound(self):
        self.audio.set_muted(not self.audio.muted)
        self.settings_screen.sound_on = not self.audio.muted
        self.audio.play_for_state(self.state)

    def exit_game(self):
        try:
            pygame.mouse.set_visible(True)
            pygame.event.set_grab(False)
        except pygame.error:
            pass
        self.save_profile()
        self.audio.stop()
        self.running = False
        pygame.quit()
        sys.exit()
