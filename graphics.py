"""Drawn sprites: grass, sod, flags, bombs, break shards, and decoy splats."""

from __future__ import annotations

import math
import random

import pygame

from constants import (
    BOMB_BODY,
    BOMB_GLOSS,
    BREAK_MS,
    DECOY_BOMB,
    DECOY_BOMB_EDGE,
    DECOY_GLOSS,
    DIRT,
    DIRT_DARK,
    FLAG_POLE,
    FLAG_RED,
    GRASS_BASE,
    GRASS_BLADE,
    GRASS_DARK,
    GRASS_LIGHT,
    HINT,
    HIDDEN,
    HIDDEN_BORDER,
    HIDDEN_TOP,
    MINE_BG,
    SPLAT_COLORS,
    SPLAT_MS,
    TEXT,
)


def make_grass(width: int, height: int, seed: int = 7) -> pygame.Surface:
    """Build a cached grassy field of patches and blades."""
    rng = random.Random(seed)
    surf = pygame.Surface((width, height))
    surf.fill(GRASS_BASE)
    for _ in range(max(80, width * height // 1800)):
        x = rng.randint(-40, width)
        y = rng.randint(-40, height)
        w = rng.randint(50, 160)
        h = rng.randint(30, 90)
        color = rng.choice((GRASS_DARK, GRASS_LIGHT, GRASS_BLADE))
        pygame.draw.ellipse(surf, color, (x, y, w, h))
    for _ in range(width * height // 18):
        x = rng.randint(0, width - 1)
        y = rng.randint(0, height - 1)
        length = rng.randint(4, 11)
        lean = rng.randint(-3, 3)
        pygame.draw.line(surf, GRASS_BLADE, (x, y), (x + lean, y - length), 1)
    for _ in range(width * height // 90):
        x = rng.randint(0, width - 1)
        y = rng.randint(0, height - 1)
        pygame.draw.line(surf, GRASS_LIGHT, (x, y), (x + rng.randint(-2, 2), y - rng.randint(3, 8)), 1)
    return surf


def draw_sod(surface: pygame.Surface, rect: pygame.Rect) -> None:
    """Unopened grassy tile with a raised highlight."""
    pygame.draw.rect(surface, HIDDEN, rect, border_radius=4)
    highlight = pygame.Rect(rect.x + 2, rect.y + 2, rect.width - 4, max(4, rect.height // 4))
    pygame.draw.rect(surface, HIDDEN_TOP, highlight, border_radius=3)
    pygame.draw.rect(surface, HIDDEN_BORDER, rect, 2, border_radius=4)


def draw_dirt(surface: pygame.Surface, rect: pygame.Rect) -> None:
    """Opened soil under a broken sod tile."""
    pygame.draw.rect(surface, DIRT, rect, border_radius=3)
    pygame.draw.rect(surface, DIRT_DARK, rect, 2, border_radius=3)
    inset = rect.inflate(-rect.width // 3, -rect.height // 2)
    pygame.draw.ellipse(surface, DIRT_DARK, inset)


def draw_flag(surface: pygame.Surface, rect: pygame.Rect) -> None:
    """Red triangular flag on a wooden pole."""
    pole_x = rect.x + rect.width * 0.32
    top = rect.y + rect.height * 0.18
    bottom = rect.y + rect.height * 0.82
    pygame.draw.line(surface, FLAG_POLE, (pole_x, top), (pole_x, bottom), max(2, rect.width // 14))
    tip = (rect.x + rect.width * 0.78, rect.y + rect.height * 0.34)
    mid = (pole_x, rect.y + rect.height * 0.50)
    pygame.draw.polygon(surface, FLAG_RED, [(pole_x, top), tip, mid])


def draw_bomb(surface: pygame.Surface, rect: pygame.Rect, exploded: bool = False, decoy: bool = False) -> None:
    """Round bomb with spikes; decoys are white, real mines are dark (red crater if exploded)."""
    if decoy:
        fill = (210, 216, 224)
        body, gloss, spike = DECOY_BOMB, DECOY_GLOSS, DECOY_BOMB_EDGE
    else:
        fill = MINE_BG if exploded else (90, 72, 48)
        body, gloss, spike = BOMB_BODY, BOMB_GLOSS, BOMB_BODY
    pygame.draw.rect(surface, fill, rect, border_radius=3)
    cx, cy = rect.center
    r = max(5, rect.width // 4)
    pygame.draw.circle(surface, body, (cx, cy + 1), r)
    pygame.draw.circle(surface, gloss, (cx - r // 3, cy - r // 4), max(2, r // 4))
    fuse = (cx + r - 1, cy - r + 2)
    pygame.draw.line(surface, spike, (cx, cy - r + 2), fuse, 2)
    pygame.draw.circle(surface, (240, 180, 70), fuse, max(2, r // 5))
    for angle in range(0, 360, 45):
        rad = math.radians(angle)
        pygame.draw.line(
            surface,
            spike,
            (cx + math.cos(rad) * r * 0.7, cy + math.sin(rad) * r * 0.7),
            (cx + math.cos(rad) * r * 1.25, cy + math.sin(rad) * r * 1.25),
            2,
        )


def draw_decoy_hint(surface: pygame.Surface, rect: pygame.Rect, font: pygame.font.Font) -> None:
    """Tiny ? in the top-right of a tile that touches a decoy."""
    mark = font.render("?", True, HINT)
    surface.blit(mark, (rect.right - mark.get_width() - 3, rect.top + 1))


class TileBreak:
    """Sod shards that fly apart so a reveal eases in instead of popping."""

    def __init__(self, rect: pygame.Rect, start_ms: int, duration_ms: int = BREAK_MS):
        self.start_ms = start_ms
        self.duration_ms = duration_ms
        rng = random.Random(start_ms * 17 + rect.x * 13 + rect.y)
        cx, cy = rect.center
        self.shards: list[dict] = []
        corners = [
            (rect.topleft, rect.midtop, rect.center, rect.midleft),
            (rect.midtop, rect.topright, rect.midright, rect.center),
            (rect.midleft, rect.center, rect.midbottom, rect.bottomleft),
            (rect.center, rect.midright, rect.bottomright, rect.midbottom),
        ]
        for points in corners:
            dx = sum(p[0] for p in points) / 4 - cx
            dy = sum(p[1] for p in points) / 4 - cy
            self.shards.append(
                {
                    "points": [(p[0] - cx, p[1] - cy) for p in points],
                    "vx": dx * 0.08 + rng.uniform(-0.6, 0.6),
                    "vy": dy * 0.08 + rng.uniform(0.4, 1.6),
                    "spin": rng.uniform(-8, 8),
                }
            )

    def progress(self, now_ms: int) -> float:
        """0–1 clock for this crack, clamped."""
        t = (now_ms - self.start_ms) / self.duration_ms
        return max(0.0, min(1.0, t))

    def waiting(self, now_ms: int) -> bool:
        """True before the stagger delay elapses."""
        return now_ms < self.start_ms

    def done(self, now_ms: int) -> bool:
        """True after shards have finished flying."""
        return now_ms >= self.start_ms + self.duration_ms

    def draw(self, surface: pygame.Surface, rect: pygame.Rect, now_ms: int) -> None:
        """Paint the fading, spinning sod pieces over the opened tile."""
        if self.waiting(now_ms) or self.done(now_ms):
            return
        t = self.progress(now_ms)
        eased = 1 - (1 - t) ** 3
        alpha = int(255 * (1 - t * t))
        cx, cy = rect.center
        shard_surf = pygame.Surface((rect.width * 3, rect.height * 3), pygame.SRCALPHA)
        ox, oy = rect.width * 1.5, rect.height * 1.5
        for shard in self.shards:
            angle = shard["spin"] * eased
            shift_x = shard["vx"] * eased * rect.width
            shift_y = shard["vy"] * eased * rect.height + eased * eased * rect.height * 0.4
            points = []
            for px, py in shard["points"]:
                rad = math.radians(angle)
                rx = px * math.cos(rad) - py * math.sin(rad)
                ry = px * math.sin(rad) + py * math.cos(rad)
                points.append((ox + rx + shift_x, oy + ry + shift_y))
            color = (*HIDDEN_TOP, alpha) if shard is self.shards[0] or shard is self.shards[1] else (*HIDDEN, alpha)
            pygame.draw.polygon(shard_surf, color, points)
        surface.blit(shard_surf, (cx - ox, cy - oy))


class Splat:
    """White paint burst used when a decoy bomb is clicked."""

    def __init__(self, rect: pygame.Rect, start_ms: int, duration_ms: int = SPLAT_MS):
        self.start_ms = start_ms
        self.duration_ms = duration_ms
        rng = random.Random(start_ms + rect.x * 31 + rect.y)
        self.drops = []
        for _ in range(14):
            angle = rng.uniform(0, math.tau)
            self.drops.append(
                {
                    "angle": angle,
                    "dist": rng.uniform(0.15, 0.95),
                    "size": rng.uniform(0.12, 0.34),
                    "color": rng.choice(SPLAT_COLORS),
                    "stretch": rng.uniform(0.6, 1.4),
                }
            )

    def done(self, now_ms: int) -> bool:
        """True once the splat has faded."""
        return now_ms >= self.start_ms + self.duration_ms

    def draw(self, surface: pygame.Surface, rect: pygame.Rect, now_ms: int) -> None:
        """Expand white blobs from the tile center, then fade them."""
        if now_ms < self.start_ms or self.done(now_ms):
            return
        t = max(0.0, min(1.0, (now_ms - self.start_ms) / self.duration_ms))
        grow = 1 - (1 - t) ** 2
        fade = 1 - t * t
        cx, cy = rect.center
        radius = rect.width * 0.9 * grow
        blob = pygame.Surface((rect.width * 3, rect.height * 3), pygame.SRCALPHA)
        ox, oy = rect.width * 1.5, rect.height * 1.5
        core_r = int(rect.width * 0.22 * (1.1 - t * 0.3))
        pygame.draw.circle(blob, (*DECOY_BOMB, int(220 * fade)), (int(ox), int(oy)), max(4, core_r))
        for drop in self.drops:
            dist = radius * drop["dist"]
            x = ox + math.cos(drop["angle"]) * dist
            y = oy + math.sin(drop["angle"]) * dist
            w = max(3, int(rect.width * drop["size"] * (1.15 - t * 0.4)))
            h = max(3, int(w * drop["stretch"]))
            pygame.draw.ellipse(blob, (*drop["color"], int(240 * fade)), (x - w / 2, y - h / 2, w, h))
        surface.blit(blob, (cx - ox, cy - oy))
        pygame.draw.circle(surface, TEXT, (cx, cy), max(2, int(rect.width * 0.08 * fade)))
