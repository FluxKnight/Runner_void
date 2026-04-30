# src/transition.py

import math
import random

import pygame

from src.settings import SCREEN_WIDTH, SCREEN_HEIGHT, BLACK, RED, WHITE


class ScreenTransition:
    def __init__(self, duration=0.72):
        self.duration = duration
        self.elapsed = 0
        self.active = False
        self.old_surface = None
        self.transition_type = "slide"
        self.particles = []

    def start(self, old_surface, transition_type="slide"):
        self.old_surface = old_surface.copy()
        self.elapsed = 0
        self.active = True
        self.transition_type = transition_type
        self.duration = self.get_duration(transition_type)
        self.particles = self.make_particles(transition_type)

    def get_duration(self, transition_type):
        durations = {
            "warp": 1.02,
            "neon_wipe": 0.82,
            "cyber_grid": 0.90,
            "soft_pause": 0.54,
            "resume_flash": 0.50,
            "return_slide": 0.72,
            "crash_glitch": 1.12,
            "fade_black": 0.98,
            "slide": 0.70,
        }

        return durations.get(transition_type, 0.50)

    def make_particles(self, transition_type):
        count = 80

        if transition_type == "warp":
            count = 140
        elif transition_type == "crash_glitch":
            count = 120
        elif transition_type == "soft_pause":
            count = 35

        particles = []

        for _ in range(count):
            particles.append(
                {
                    "x": random.randint(0, SCREEN_WIDTH),
                    "y": random.randint(0, SCREEN_HEIGHT),
                    "speed": random.uniform(80, 420),
                    "size": random.randint(1, 4),
                    "angle": random.uniform(0, math.tau),
                    "life": random.uniform(0.35, 1.0),
                }
            )

        return particles

    def update(self, dt):
        if not self.active:
            return

        self.elapsed += dt

        if self.elapsed >= self.duration:
            self.active = False
            self.old_surface = None
            self.particles = []

    def progress(self):
        if self.duration <= 0:
            return 1

        return min(1, self.elapsed / self.duration)

    def ease_out_cubic(self, t):
        return 1 - pow(1 - t, 3)

    def ease_in_out_cubic(self, t):
        if t < 0.5:
            return 4 * t * t * t

        return 1 - pow(-2 * t + 2, 3) / 2

    def draw(self, screen, new_surface):
        if not self.active or self.old_surface is None:
            screen.blit(new_surface, (0, 0))
            return

        if self.transition_type == "warp":
            self.draw_warp(screen, new_surface)
        elif self.transition_type == "neon_wipe":
            self.draw_neon_wipe(screen, new_surface)
        elif self.transition_type == "cyber_grid":
            self.draw_cyber_grid(screen, new_surface)
        elif self.transition_type == "soft_pause":
            self.draw_soft_pause(screen, new_surface)
        elif self.transition_type == "resume_flash":
            self.draw_resume_flash(screen, new_surface)
        elif self.transition_type == "return_slide":
            self.draw_return_slide(screen, new_surface)
        elif self.transition_type == "crash_glitch":
            self.draw_crash_glitch(screen, new_surface)
        elif self.transition_type == "fade_black":
            self.draw_fade_black(screen, new_surface)
        else:
            self.draw_slide(screen, new_surface)

    def draw_slide(self, screen, new_surface):
        progress = self.progress()
        eased = self.ease_out_cubic(progress)
        offset = int(SCREEN_WIDTH * eased)

        screen.fill(BLACK)
        screen.blit(self.old_surface, (-offset, 0))
        screen.blit(new_surface, (SCREEN_WIDTH - offset, 0))

        edge_x = SCREEN_WIDTH - offset
        pygame.draw.rect(screen, RED, (edge_x - 3, 0, 6, SCREEN_HEIGHT))
        self.draw_scan_lines(screen, progress)
        self.draw_label(screen, "VOID SHIFT", progress)

    def draw_return_slide(self, screen, new_surface):
        progress = self.progress()
        eased = self.ease_out_cubic(progress)
        offset = int(SCREEN_WIDTH * eased)

        screen.fill(BLACK)
        screen.blit(self.old_surface, (offset, 0))
        screen.blit(new_surface, (-SCREEN_WIDTH + offset, 0))

        edge_x = offset
        pygame.draw.rect(screen, (80, 190, 255), (edge_x - 3, 0, 6, SCREEN_HEIGHT))
        self.draw_scan_lines(screen, progress, color=(80, 190, 255))
        self.draw_label(screen, "RETURNING", progress, color=(80, 190, 255))

    def draw_warp(self, screen, new_surface):
        progress = self.progress()
        eased = self.ease_in_out_cubic(progress)

        screen.fill(BLACK)

        old_alpha = int(255 * max(0, 1 - progress * 1.25))
        old = self.old_surface.copy()
        old.set_alpha(old_alpha)
        screen.blit(old, (0, 0))

        center_x = SCREEN_WIDTH // 2
        center_y = SCREEN_HEIGHT // 2

        radius = int(max(SCREEN_WIDTH, SCREEN_HEIGHT) * 1.15 * eased)
        if radius > 0:
            mask = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            pygame.draw.circle(mask, (255, 255, 255, 255), (center_x, center_y), radius)

            revealed = new_surface.copy()
            revealed.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
            screen.blit(revealed, (0, 0))

        pulse_radius = int(50 + radius * 0.72)
        for i in range(4):
            ring_radius = pulse_radius - i * 34
            if ring_radius > 0:
                alpha = max(0, int(150 * (1 - progress) - i * 22))
                color = (255, 42, 42, alpha)
                ring = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
                pygame.draw.circle(ring, color, (center_x, center_y), ring_radius, 2)
                screen.blit(ring, (0, 0))

        self.draw_particles(screen, progress, mode="radial")
        self.draw_scan_lines(screen, progress)
        self.draw_label(screen, "ENTER THE VOID", progress)

    def draw_neon_wipe(self, screen, new_surface):
        progress = self.progress()
        eased = self.ease_out_cubic(progress)

        screen.blit(self.old_surface, (0, 0))

        wipe_x = int((SCREEN_WIDTH + 220) * eased) - 110
        points = [
            (wipe_x - 220, 0),
            (wipe_x + 80, 0),
            (wipe_x + 220, SCREEN_HEIGHT),
            (wipe_x - 80, SCREEN_HEIGHT),
        ]

        clip = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        pygame.draw.polygon(clip, (255, 255, 255, 255), points)

        revealed = new_surface.copy()
        revealed.blit(clip, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        screen.blit(revealed, (0, 0))

        glow = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        pygame.draw.polygon(glow, (255, 42, 42, 72), points)
        pygame.draw.line(glow, (255, 42, 42, 220), (wipe_x + 80, 0), (wipe_x + 220, SCREEN_HEIGHT), 4)
        pygame.draw.line(glow, (80, 190, 255, 180), (wipe_x - 220, 0), (wipe_x - 80, SCREEN_HEIGHT), 2)
        screen.blit(glow, (0, 0))

        self.draw_particles(screen, progress, mode="left")
        self.draw_label(screen, "LOADING PANEL", progress, color=(80, 190, 255))

    def draw_cyber_grid(self, screen, new_surface):
        progress = self.progress()
        eased = self.ease_in_out_cubic(progress)

        screen.fill(BLACK)

        old = self.old_surface.copy()
        old.set_alpha(int(255 * (1 - eased)))
        screen.blit(old, (0, 0))

        new = new_surface.copy()
        new.set_alpha(int(255 * eased))
        screen.blit(new, (0, 0))

        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        cell = 42
        alpha = int(145 * math.sin(progress * math.pi))

        for x in range(0, SCREEN_WIDTH, cell):
            pygame.draw.line(overlay, (255, 42, 42, alpha), (x, 0), (x, SCREEN_HEIGHT), 1)

        for y in range(0, SCREEN_HEIGHT, cell):
            pygame.draw.line(overlay, (80, 190, 255, alpha), (0, y), (SCREEN_WIDTH, y), 1)

        sweep_y = int(SCREEN_HEIGHT * eased)
        pygame.draw.rect(overlay, (255, 42, 42, 120), (0, sweep_y - 3, SCREEN_WIDTH, 6))
        screen.blit(overlay, (0, 0))

        self.draw_scan_lines(screen, progress, color=(80, 190, 255))
        self.draw_label(screen, "SYNCING", progress)

    def draw_soft_pause(self, screen, new_surface):
        progress = self.progress()
        eased = self.ease_out_cubic(progress)

        screen.blit(self.old_surface, (0, 0))

        dark = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        dark.fill((0, 0, 0, int(155 * eased)))
        screen.blit(dark, (0, 0))

        panel = new_surface.copy()
        panel.set_alpha(int(255 * eased))
        screen.blit(panel, (0, 0))

        self.draw_label(screen, "PAUSED", progress, color=(230, 230, 230))

    def draw_resume_flash(self, screen, new_surface):
        progress = self.progress()
        eased = self.ease_out_cubic(progress)

        screen.blit(new_surface, (0, 0))

        flash_alpha = int(190 * (1 - eased))
        flash = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        flash.fill((255, 42, 42, flash_alpha))
        screen.blit(flash, (0, 0))

        self.draw_scan_lines(screen, progress)
        self.draw_label(screen, "RUN", progress)

    def draw_crash_glitch(self, screen, new_surface):
        progress = self.progress()
        glitch_strength = math.sin(progress * math.pi)

        screen.fill(BLACK)

        old_alpha = int(255 * max(0, 1 - progress * 1.1))
        old = self.old_surface.copy()
        old.set_alpha(old_alpha)

        shake = int(16 * glitch_strength)
        screen.blit(old, (random.randint(-shake, shake), random.randint(-shake, shake)))

        if progress > 0.35:
            new_alpha = int(255 * min(1, (progress - 0.35) / 0.65))
            new = new_surface.copy()
            new.set_alpha(new_alpha)
            screen.blit(new, (0, 0))

        strips = int(10 + 28 * glitch_strength)

        for _ in range(strips):
            source = self.old_surface if progress < 0.55 else new_surface

            source_width = source.get_width()
            source_height = source.get_height()

            if source_width <= 0 or source_height <= 0:
                continue

            strip_width = min(SCREEN_WIDTH, source_width)
            max_y = max(0, source_height - 1)

            y = random.randint(0, max_y)
            h = random.randint(3, 18)

            # Final safety clamp:
            # pygame.subsurface crashes if x + width or y + height is outside the source surface.
            h = min(h, source_height - y)

            if h <= 0:
                continue

            dx = random.randint(-35, 35)

            strip = source.subsurface((0, y, strip_width, h)).copy()
            strip.set_alpha(int(80 + 150 * glitch_strength))
            screen.blit(strip, (dx, y))

        red = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        red.fill((255, 0, 30, int(90 * glitch_strength)))
        screen.blit(red, (0, 0))

        self.draw_particles(screen, progress, mode="fall")
        self.draw_label(screen, "SIGNAL LOST", progress)

    def draw_fade_black(self, screen, new_surface):
        progress = self.progress()

        if progress < 0.5:
            local = progress / 0.5
            screen.blit(self.old_surface, (0, 0))

            black_alpha = int(255 * self.ease_in_out_cubic(local))
            overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, black_alpha))
            screen.blit(overlay, (0, 0))
        else:
            local = (progress - 0.5) / 0.5
            screen.blit(new_surface, (0, 0))

            black_alpha = int(255 * (1 - self.ease_in_out_cubic(local)))
            overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, black_alpha))
            screen.blit(overlay, (0, 0))

        self.draw_label(screen, "VOID RESET", progress, color=(230, 230, 230))

    def draw_scan_lines(self, screen, progress, color=(255, 42, 42)):
        glitch_strength = math.sin(progress * math.pi)

        for i in range(14):
            y = int((i * 67 + self.elapsed * 900) % SCREEN_HEIGHT)
            width = int(90 + 280 * glitch_strength)
            x = int((i * 173 + self.elapsed * 620) % SCREEN_WIDTH)

            glitch = pygame.Surface((width, 3), pygame.SRCALPHA)
            glitch.fill((*color, int(90 * glitch_strength)))
            screen.blit(glitch, (x, y))

    def draw_particles(self, screen, progress, mode="radial"):
        strength = math.sin(progress * math.pi)
        center_x = SCREEN_WIDTH // 2
        center_y = SCREEN_HEIGHT // 2

        for particle in self.particles:
            life = particle["life"]
            alpha = int(155 * strength * life)
            if alpha <= 0:
                continue

            distance = particle["speed"] * progress
            angle = particle["angle"]

            if mode == "radial":
                x = center_x + math.cos(angle) * distance
                y = center_y + math.sin(angle) * distance
            elif mode == "left":
                x = particle["x"] + distance * 0.7
                y = particle["y"] + math.sin(progress * 12 + particle["x"]) * 14
            elif mode == "fall":
                x = particle["x"] + math.sin(progress * 9 + particle["y"]) * 20
                y = particle["y"] + distance
            else:
                x = particle["x"]
                y = particle["y"]

            pygame.draw.circle(
                screen,
                (255, 42, 42, alpha),
                (int(x) % SCREEN_WIDTH, int(y) % SCREEN_HEIGHT),
                particle["size"],
            )

    def draw_label(self, screen, text, progress, color=WHITE):
        if not 0.14 < progress < 0.88:
            return

        alpha = int(255 * math.sin(progress * math.pi))
        font = pygame.font.SysFont(None, 26, bold=True)
        rendered = font.render(text, True, color)
        rendered.set_alpha(alpha)

        rect = rendered.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2))
        screen.blit(rendered, rect)
