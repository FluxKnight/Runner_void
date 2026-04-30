# src/audio.py

from pathlib import Path
import pygame


class AudioManager:
    def __init__(self):
        self.available = False
        self.current_track = None
        self.muted = False
        self.target_volume = 0.32
        self.boss_active = False

        self.root_dir = Path(__file__).resolve().parent.parent
        self.music_dir = self.root_dir / "assets" / "music"
        self.sfx_dir = self.root_dir / "assets" / "sfx"

        self.tracks = {
            "LOBBY": self.music_dir / "void_lobby_loop.wav",
            "GAME": self.music_dir / "void_run_loop.wav",
            "BOSS": self.music_dir / "void_boss_loop.wav",
        }

        self.sfx_paths = {
            "GEM": self.sfx_dir / "gem_collect.wav",
            "BURST": self.sfx_dir / "player_burst.wav",
            "UI_TAP": self.sfx_dir / "ui_tap.wav",
            "PISTOL": self.sfx_dir / "gun_pistol.wav",
            "RIFLE": self.sfx_dir / "gun_rifle.wav",
            "BURST_GUN": self.sfx_dir / "gun_burst.wav",
            "ENEMY_HIT": self.sfx_dir / "enemy_hit.wav",
            "SKILL": self.sfx_dir / "skill_pickup.wav",
            "BOSS_WARNING": self.sfx_dir / "boss_warning.wav",
            "BUY": self.sfx_dir / "buy.wav",
        }
        self.sfx = {}

        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
            self.available = True
            pygame.mixer.music.set_volume(self.target_volume)
            self.sfx = self.load_sfx()
        except pygame.error:
            self.available = False

    def load_sfx(self):
        sounds = {}
        for name, path in self.sfx_paths.items():
            if not path.exists():
                continue
            try:
                sounds[name] = pygame.mixer.Sound(str(path))
            except pygame.error:
                continue
        return sounds

    def set_boss_active(self, active):
        self.boss_active = active

    def get_track_for_state(self, state):
        if state in ("HOME", "HOW_TO_PLAY", "SETTINGS", "SHOP", "GAME_OVER"):
            return "LOBBY"
        if state in ("PLAYING", "PAUSED"):
            return "BOSS" if self.boss_active else "GAME"
        return "LOBBY"

    def get_volume_for_state(self, state):
        if self.muted:
            return 0.0
        if state == "PAUSED":
            return 0.14
        if state == "PLAYING":
            return 0.30 if self.boss_active else 0.28
        return 0.34

    def play_for_state(self, state):
        if not self.available:
            return

        track_name = self.get_track_for_state(state)
        track_path = self.tracks.get(track_name)

        if not track_path or not track_path.exists():
            return

        desired_volume = self.get_volume_for_state(state)
        self.target_volume = desired_volume

        try:
            if self.current_track != track_name:
                pygame.mixer.music.fadeout(260)
                pygame.mixer.music.load(str(track_path))
                pygame.mixer.music.set_volume(desired_volume)
                pygame.mixer.music.play(-1, fade_ms=850)
                self.current_track = track_name
            else:
                pygame.mixer.music.set_volume(desired_volume)
        except pygame.error:
            self.available = False

    def update_for_state(self, state):
        if not self.available:
            return

        desired_volume = self.get_volume_for_state(state)
        current_volume = pygame.mixer.music.get_volume()

        if abs(current_volume - desired_volume) < 0.01:
            pygame.mixer.music.set_volume(desired_volume)
            return

        step = 0.006
        if current_volume < desired_volume:
            current_volume = min(desired_volume, current_volume + step)
        else:
            current_volume = max(desired_volume, current_volume - step)

        pygame.mixer.music.set_volume(current_volume)

    def set_muted(self, muted):
        self.muted = muted
        if not self.available:
            return
        pygame.mixer.music.set_volume(0.0 if self.muted else self.target_volume)

    def toggle_mute(self):
        self.set_muted(not self.muted)

    def play_sfx(self, name, volume=0.45):
        # Music mute only affects background music, not gameplay feedback SFX.
        if not self.available:
            return
        sound = self.sfx.get(name)
        if sound is None:
            return
        sound.set_volume(volume)
        sound.play()

    def play_gem_collect(self):
        self.play_sfx("GEM", 0.48)

    def play_player_burst(self):
        self.play_sfx("BURST", 0.55)

    def play_ui_tap(self):
        self.play_sfx("UI_TAP", 0.20)

    def play_weapon(self, weapon_sfx):
        volume = 0.32 if weapon_sfx == "PISTOL" else 0.25
        self.play_sfx(weapon_sfx, volume)

    def play_enemy_hit(self):
        self.play_sfx("ENEMY_HIT", 0.22)

    def play_skill_pickup(self):
        self.play_sfx("SKILL", 0.42)

    def play_boss_warning(self):
        self.play_sfx("BOSS_WARNING", 0.50)

    def play_buy(self):
        self.play_sfx("BUY", 0.45)

    def stop(self):
        if not self.available:
            return
        try:
            pygame.mixer.music.stop()
        except pygame.error:
            pass
