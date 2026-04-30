# src/player.py

import math
import pygame
from src import settings as S

SCREEN_WIDTH = getattr(S, "SCREEN_WIDTH", 1280)
SCREEN_HEIGHT = getattr(S, "SCREEN_HEIGHT", 720)
WHITE = getattr(S, "WHITE", (255, 255, 255))
BLACK = getattr(S, "BLACK", (0, 0, 0))


class Player:
    def __init__(self):
        self.radius = 18

        # Smooth movement tuning.
        self.max_speed = 430
        self.acceleration = 14.5
        self.friction = 12.5

        self.skin_key = "WHITE"
        self.skin_style = "orb"
        self.fill_color = WHITE
        self.glow_color = (210, 210, 220)
        self.accent_color = (255, 255, 255)

        self.x = SCREEN_WIDTH // 2
        self.y = SCREEN_HEIGHT - 150
        self.vx = 0
        self.vy = 0

        self.trail = []
        self.trail_timer = 0
        self.trail_interval = 0.018

        self.reset()

    def reset(self):
        self.x = SCREEN_WIDTH // 2
        self.y = SCREEN_HEIGHT - 150
        self.vx = 0
        self.vy = 0
        self.trail = []
        self.trail_timer = 0

    def set_skin(self, skin_key, palette):
        self.skin_key = skin_key
        self.skin_style = palette.get("style", "orb")
        self.fill_color = tuple(palette.get("fill", WHITE))
        self.glow_color = tuple(palette.get("glow", (210, 210, 220)))
        self.accent_color = tuple(palette.get("accent", WHITE))

    def update(self, keys, dt=None):
        if dt is None:
            dt = 1 / 60

        dt = max(0.001, min(dt, 0.05))

        input_x = 0
        input_y = 0

        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            input_x -= 1
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            input_x += 1
        if keys[pygame.K_UP] or keys[pygame.K_w]:
            input_y -= 1
        if keys[pygame.K_DOWN] or keys[pygame.K_s]:
            input_y += 1

        input_active = input_x != 0 or input_y != 0

        if input_active:
            length = math.hypot(input_x, input_y)
            input_x /= length
            input_y /= length

            target_vx = input_x * self.max_speed
            target_vy = input_y * self.max_speed

            lerp_amount = min(1, self.acceleration * dt)
            self.vx += (target_vx - self.vx) * lerp_amount
            self.vy += (target_vy - self.vy) * lerp_amount
        else:
            decay = max(0, 1 - self.friction * dt)
            self.vx *= decay
            self.vy *= decay

            if abs(self.vx) < 3:
                self.vx = 0
            if abs(self.vy) < 3:
                self.vy = 0

        self.x += self.vx * dt
        self.y += self.vy * dt

        if self.x < self.radius:
            self.x = self.radius
            self.vx = max(0, self.vx)
        elif self.x > SCREEN_WIDTH - self.radius:
            self.x = SCREEN_WIDTH - self.radius
            self.vx = min(0, self.vx)

        if self.y < self.radius:
            self.y = self.radius
            self.vy = max(0, self.vy)
        elif self.y > SCREEN_HEIGHT - self.radius:
            self.y = SCREEN_HEIGHT - self.radius
            self.vy = min(0, self.vy)

        self.update_trail(dt, input_active)

    def update_trail(self, dt, input_active):
        speed = math.hypot(self.vx, self.vy)
        should_emit = input_active and speed > 65

        self.trail_timer += dt

        if should_emit and self.trail_timer >= self.trail_interval:
            self.trail_timer = 0
            self.trail.append(
                {
                    "x": self.x,
                    "y": self.y,
                    "life": 0.38,
                    "max_life": 0.38,
                    "radius": self.radius * 0.92,
                    "color": self.glow_color,
                }
            )

        alive = []
        for particle in self.trail:
            particle["life"] -= dt
            particle["radius"] *= 0.985

            if particle["life"] > 0:
                alive.append(particle)

        self.trail = alive[-28:]

    def draw_trail(self, surface):
        if not self.trail:
            return

        trail_surface = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)

        for particle in self.trail:
            progress = max(0, min(1, particle["life"] / particle["max_life"]))
            alpha = int(105 * progress)
            radius = max(2, int(particle["radius"] * (0.55 + 0.55 * progress)))
            x = int(particle["x"])
            y = int(particle["y"])
            color = particle["color"]

            pygame.draw.circle(trail_surface, (*color, int(alpha * 0.32)), (x, y), radius + 12)
            pygame.draw.circle(trail_surface, (*color, alpha), (x, y), radius)
            pygame.draw.circle(trail_surface, (255, 255, 255, int(alpha * 0.26)), (x, y), max(1, radius // 3))

        surface.blit(trail_surface, (0, 0))

    def draw_base_glow(self, surface):
        glow_surface = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        gx, gy = int(self.x), int(self.y)

        speed = math.hypot(self.vx, self.vy)
        pulse = min(1, speed / self.max_speed)

        outer_alpha = int(25 + 20 * pulse)
        inner_alpha = int(35 + 24 * pulse)

        pygame.draw.circle(glow_surface, (*self.glow_color, outer_alpha), (gx, gy), 36)
        pygame.draw.circle(glow_surface, (*self.glow_color, inner_alpha), (gx, gy), 27)

        surface.blit(glow_surface, (0, 0))

    def draw_orb(self, surface, gx, gy):
        pygame.draw.circle(surface, self.fill_color, (gx, gy), self.radius)
        pygame.draw.circle(surface, WHITE, (gx - 6, gy - 6), 5)
        pygame.draw.circle(surface, (245, 245, 255), (gx, gy), self.radius, 2)

    def draw_smile(self, surface, gx, gy):
        pygame.draw.circle(surface, self.fill_color, (gx, gy), self.radius)
        pygame.draw.circle(surface, (35, 28, 22), (gx - 6, gy - 4), 3)
        pygame.draw.circle(surface, (35, 28, 22), (gx + 6, gy - 4), 3)
        smile_rect = pygame.Rect(gx - 9, gy - 3, 18, 15)
        pygame.draw.arc(surface, (35, 28, 22), smile_rect, math.radians(20), math.radians(160), 2)
        pygame.draw.circle(surface, (255, 255, 255), (gx - 7, gy - 9), 4)
        pygame.draw.circle(surface, (255, 250, 190), (gx, gy), self.radius, 2)

    def draw_speedster(self, surface, gx, gy):
        pygame.draw.circle(surface, self.fill_color, (gx, gy), self.radius)
        bolt = [
            (gx - 2, gy - 18),
            (gx + 11, gy - 2),
            (gx + 4, gy - 2),
            (gx + 12, gy + 17),
            (gx - 11, gy - 4),
            (gx - 2, gy - 4),
        ]
        pygame.draw.polygon(surface, self.accent_color, bolt)
        pygame.draw.circle(surface, WHITE, (gx - 7, gy - 8), 4)
        pygame.draw.circle(surface, (235, 245, 255), (gx, gy), self.radius, 2)

    def draw_fire(self, surface, gx, gy):
        pygame.draw.circle(surface, self.fill_color, (gx, gy), self.radius)
        flame = [
            (gx, gy - 18),
            (gx + 11, gy - 4),
            (gx + 7, gy + 14),
            (gx, gy + 8),
            (gx - 8, gy + 14),
            (gx - 11, gy - 4),
        ]
        pygame.draw.polygon(surface, self.accent_color, flame)
        pygame.draw.circle(surface, WHITE, (gx - 6, gy - 8), 4)
        pygame.draw.circle(surface, (255, 235, 210), (gx, gy), self.radius, 2)

    def draw(self, surface):
        self.draw_trail(surface)
        self.draw_base_glow(surface)

        gx, gy = int(self.x), int(self.y)

        if self.skin_style == "smile":
            self.draw_smile(surface, gx, gy)
        elif self.skin_style == "speedster":
            self.draw_speedster(surface, gx, gy)
        elif self.skin_style == "fire":
            self.draw_fire(surface, gx, gy)
        else:
            self.draw_orb(surface, gx, gy)

    def get_position(self):
        return self.x, self.y

    def get_radius(self):
        return self.radius
