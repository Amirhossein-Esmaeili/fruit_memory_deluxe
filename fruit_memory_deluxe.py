import os
import sys
import math
import array
import random
from enum import Enum
from typing import List, Tuple, Optional, Dict, Callable

import pygame
import pygame.gfxdraw


SCREEN_WIDTH = 1024
SCREEN_HEIGHT = 768
FPS = 60
TITLE = "Fruit Memory Deluxe - Studio Edition"

MISMATCH_DELAY_MS = 800
HINT_PEEK_MS = 1050

PALETTE = {
    "sky_zenith": (28, 128, 228),
    "sky_horizon": (122, 212, 252),
    "sky_haze": (218, 248, 255),
    "sun_core": (255, 255, 232),
    "sun_glow": (255, 232, 128),
    "hill_far_top": (108, 206, 126),
    "hill_far_bot": (62, 146, 88),
    "hill_mid_top": (80, 184, 90),
    "hill_mid_bot": (36, 116, 56),
    "hill_near_top": (56, 156, 66),
    "hill_near_bot": (20, 80, 36),
    "wood_deep": (44, 20, 8),
    "wood_dark": (76, 36, 14),
    "wood_mid": (126, 64, 26),
    "wood_light": (170, 96, 42),
    "wood_highlight": (214, 140, 76),
    "gold_shadow": (122, 74, 8),
    "gold_dark": (176, 116, 14),
    "gold_mid": (244, 192, 38),
    "gold_light": (255, 238, 118),
    "gold_shine": (255, 252, 216),
    "jade_deep": (12, 58, 48),
    "jade_dark": (20, 92, 74),
    "jade_mid": (34, 138, 106),
    "jade_light": (74, 188, 142),
    "jade_glow": (148, 238, 192),
    "cream_bright": (255, 254, 246),
    "cream": (252, 246, 228),
    "cream_dark": (224, 212, 184),
    "botanical_border": (64, 142, 92),
    "leaf_dark": (20, 88, 36),
    "leaf_mid": (46, 148, 62),
    "leaf_light": (108, 212, 92),
    "white": (255, 255, 255),
}

BASE_FRUITS = [
    "Strawberry",
    "Pineapple",
    "Watermelon",
    "Kiwi",
    "Blueberry",
    "Mango",
    "Orange",
    "Cherry",
    "Dragonfruit",
    "Coconut",
    "Banana",
    "Grapes",
    "Peach",
    "Pear",
    "Lemon",
    "Lime",
    "Pomegranate",
    "Papaya",
    "Plum",
    "Passionfruit",
    "Starfruit",
    "Guava",
    "Fig",
    "GreenApple",
    "Lychee",
]

FRUIT_THEME_COLORS = {
    "Strawberry": (240, 44, 68),
    "Pineapple": (248, 198, 32),
    "Watermelon": (72, 204, 84),
    "Kiwi": (136, 204, 48),
    "Blueberry": (70, 108, 236),
    "Mango": (255, 150, 32),
    "Orange": (255, 132, 18),
    "Cherry": (214, 24, 58),
    "Dragonfruit": (236, 48, 138),
    "Coconut": (142, 96, 58),
    "Banana": (252, 216, 44),
    "Grapes": (148, 64, 212),
    "Peach": (255, 138, 108),
    "Pear": (164, 214, 54),
    "Lemon": (250, 224, 38),
    "Lime": (82, 208, 64),
    "Pomegranate": (196, 28, 48),
    "Papaya": (252, 118, 42),
    "Plum": (132, 46, 168),
    "Passionfruit": (162, 54, 128),
    "Starfruit": (244, 212, 48),
    "Guava": (246, 98, 118),
    "Fig": (118, 56, 138),
    "GreenApple": (104, 214, 62),
    "Lychee": (242, 78, 104),
}


class GameState(Enum):
    MENU = 1
    PLAYING = 2
    VICTORY = 3


def clamp(val: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, val))


def lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * clamp(t, 0.0, 1.0)


def lerp_color(c1: Tuple[int, ...], c2: Tuple[int, ...], t: float) -> Tuple[int, ...]:
    t = clamp(t, 0.0, 1.0)
    return tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(len(c1)))


class Spring:
    def __init__(self, initial: float = 0.0, stiffness: float = 220.0, damping: float = 16.0):
        self.value = float(initial)
        self.target = float(initial)
        self.velocity = 0.0
        self.stiffness = stiffness
        self.damping = damping

    def update(self, dt: float) -> float:
        steps = 2
        sub_dt = min(dt, 0.05) / steps
        for _ in range(steps):
            force = (self.target - self.value) * self.stiffness
            self.velocity += force * sub_dt
            self.velocity *= max(0.0, 1.0 - self.damping * sub_dt)
            self.value += self.velocity * sub_dt
        return self.value

    def impulse(self, vel: float):
        self.velocity += vel

    def set_target(self, target: float):
        self.target = float(target)

    def snap(self, val: float):
        self.value = float(val)
        self.target = float(val)
        self.velocity = 0.0


def draw_aa_circle(surface: pygame.Surface, color: Tuple[int, ...], center: Tuple[float, float], radius: float):
    r = int(round(radius))
    if r <= 0:
        return
    x, y = int(round(center[0])), int(round(center[1]))
    pygame.gfxdraw.aacircle(surface, x, y, r, color)
    pygame.gfxdraw.filled_circle(surface, x, y, r, color)


def draw_aa_polygon(surface: pygame.Surface, color: Tuple[int, ...], points: List[Tuple[float, float]]):
    if len(points) < 3:
        return
    int_pts = [(int(round(px)), int(round(py))) for px, py in points]
    pygame.gfxdraw.aapolygon(surface, int_pts, color)
    pygame.gfxdraw.filled_polygon(surface, int_pts, color)


def draw_radial_sphere(
    surf: pygame.Surface,
    center: Tuple[float, float],
    radius: float,
    shadow_col: Tuple[int, int, int],
    mid_col: Tuple[int, int, int],
    highlight_col: Tuple[int, int, int],
    rim_col: Optional[Tuple[int, int, int]] = None,
    light_offset: Tuple[float, float] = (-0.32, -0.32),
):
    cx, cy = center
    r = int(round(radius))
    if r <= 1:
        return

    if rim_col is not None:
        draw_aa_circle(surf, rim_col, (cx, cy), r)
        inner_start = max(1, int(r * 0.94))
        draw_aa_circle(surf, shadow_col, (cx - r * 0.02, cy - r * 0.02), inner_start)
    else:
        draw_aa_circle(surf, shadow_col, (cx, cy), r)

    steps = max(12, min(36, r // 2))
    ox = light_offset[0] * r
    oy = light_offset[1] * r

    for i in range(steps):
        t = i / float(steps - 1)
        cur_r = r * (1.0 - t * 0.88)
        cur_x = lerp(cx, cx + ox, t)
        cur_y = lerp(cy, cy + oy, t)

        if t < 0.58:
            col = lerp_color(shadow_col, mid_col, t / 0.58)
        else:
            col = lerp_color(mid_col, highlight_col, (t - 0.58) / 0.42)

        draw_aa_circle(surf, col, (cur_x, cur_y), cur_r)


def draw_glossy_specular(
    surf: pygame.Surface,
    center: Tuple[float, float],
    rx: float,
    ry: float,
    angle_deg: float = 32.0,
    alpha: int = 215,
):
    w = max(4, int(rx * 2.6))
    h = max(4, int(ry * 2.6))
    spec = pygame.Surface((w, h), pygame.SRCALPHA)
    pygame.draw.ellipse(spec, (255, 255, 255, int(alpha * 0.48)), (0, 0, w, h))
    pygame.draw.ellipse(
        spec,
        (255, 255, 255, alpha),
        (int(w * 0.18), int(h * 0.18), int(w * 0.64), int(h * 0.64)),
    )
    rotated = pygame.transform.rotozoom(spec, angle_deg, 1.0)
    surf.blit(rotated, rotated.get_rect(center=(int(center[0]), int(center[1]))))


def create_linear_gradient_rect(
    width: int,
    height: int,
    stops: List[Tuple[float, Tuple[int, ...]]],
    border_radius: int = 0,
    vertical: bool = True,
) -> pygame.Surface:
    width = max(1, int(width))
    height = max(1, int(height))
    surf = pygame.Surface((width, height), pygame.SRCALPHA)
    length = height if vertical else width

    for i in range(length):
        t = i / float(max(1, length - 1))
        col = stops[-1][1]
        for idx in range(len(stops) - 1):
            t0, c0 = stops[idx]
            t1, c1 = stops[idx + 1]
            if t0 <= t <= t1:
                local_t = (t - t0) / max(0.0001, t1 - t0)
                col = lerp_color(c0, c1, local_t)
                break
        if vertical:
            pygame.draw.line(surf, col, (0, i), (width, i))
        else:
            pygame.draw.line(surf, col, (i, 0), (i, height))

    if border_radius > 0:
        mask = pygame.Surface((width, height), pygame.SRCALPHA)
        pygame.draw.rect(mask, (255, 255, 255, 255), (0, 0, width, height), border_radius=border_radius)
        surf.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)

    return surf


def create_soft_shadow(
    width: int, height: int, border_radius: int, blur_steps: int = 6, max_alpha: int = 115
) -> pygame.Surface:
    pad = blur_steps * 3
    surf = pygame.Surface((width + pad * 2, height + pad * 2), pygame.SRCALPHA)
    for i in range(blur_steps, 0, -1):
        inflate = i * 3
        alpha = int(max_alpha * ((1.0 - (i / float(blur_steps + 1))) ** 1.7) / blur_steps * 2.2)
        rect = pygame.Rect(
            pad - inflate // 2,
            pad - inflate // 2,
            width + inflate,
            height + inflate,
        )
        pygame.draw.rect(
            surf,
            (8, 22, 14, clamp(alpha, 0, 255)),
            rect,
            border_radius=border_radius + i * 2,
        )
    return surf


def render_arcade_text(
    font: pygame.font.Font,
    text: str,
    top_col: Tuple[int, int, int],
    bot_col: Tuple[int, int, int],
    outline_col: Tuple[int, int, int] = (38, 18, 6),
    outline_px: int = 3,
    drop_shadow: int = 3,
) -> pygame.Surface:
    base_mask = font.render(text, True, (255, 255, 255))
    tw, th = base_mask.get_size()

    grad_face = pygame.Surface((tw, th), pygame.SRCALPHA)
    for y in range(th):
        t = y / float(max(1, th - 1))
        col = lerp_color(top_col, bot_col, t)
        pygame.draw.line(grad_face, col, (0, y), (tw, y))
    grad_face.blit(base_mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)

    bevel = font.render(text, True, (255, 255, 255))
    bevel.set_alpha(95)

    outline_surf = font.render(text, True, outline_col)
    shadow_surf = font.render(text, True, (14, 8, 4))

    w = tw + outline_px * 2 + 4
    h = th + outline_px * 2 + drop_shadow + 4
    result = pygame.Surface((w, h), pygame.SRCALPHA)

    if drop_shadow > 0:
        for dx in range(-outline_px, outline_px + 1):
            for dy in range(-outline_px, outline_px + 1):
                if dx * dx + dy * dy <= (outline_px + 1) ** 2:
                    result.blit(shadow_surf, (outline_px + dx + 1, outline_px + dy + drop_shadow))

    for dx in range(-outline_px, outline_px + 1):
        for dy in range(-outline_px, outline_px + 1):
            if dx * dx + dy * dy <= outline_px * outline_px + 1:
                result.blit(outline_surf, (outline_px + dx + 1, outline_px + dy + 1))

    result.blit(grad_face, (outline_px + 1, outline_px + 1))
    result.blit(bevel, (outline_px + 1, outline_px))
    return result


class SoundManager:
    def __init__(self):
        self.enabled = True
        self.sounds: Dict[str, Optional[pygame.mixer.Sound]] = {}
        self.available = False

        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(frequency=44100, size=-16, channels=1, buffer=512)
            self.available = True
            self._build_sounds()
        except Exception:
            self.available = False

    def _generate_tone(
        self,
        freq_start: float,
        freq_end: float,
        duration: float,
        volume: float = 0.28,
        wave_type: str = "rich",
    ) -> Optional[pygame.mixer.Sound]:
        if not self.available:
            return None
        sample_rate = 44100
        num_samples = int(sample_rate * duration)
        buf = array.array("h", [0] * num_samples)
        phase = 0.0

        for i in range(num_samples):
            progress = i / max(1, num_samples)
            freq = freq_start + (freq_end - freq_start) * (progress ** 0.85)
            phase += 2.0 * math.pi * freq / sample_rate

            attack = min(1.0, i / (sample_rate * 0.008))
            decay = math.pow(1.0 - progress, 1.55)
            env = attack * decay

            if wave_type == "sine":
                val = math.sin(phase)
            elif wave_type == "triangle":
                val = 2.0 * abs(2.0 * (phase / math.tau - math.floor(phase / math.tau + 0.5))) - 1.0
            else:
                val = 0.68 * math.sin(phase) + 0.22 * math.sin(phase * 2.0) + 0.10 * math.sin(phase * 3.0)

            sample = int(val * env * volume * 32767)
            buf[i] = max(-32768, min(32767, sample))

        return pygame.mixer.Sound(buffer=buf)

    def _generate_arpeggio(
        self, freqs: List[float], note_duration: float, volume: float = 0.28
    ) -> Optional[pygame.mixer.Sound]:
        if not self.available:
            return None
        sample_rate = 44100
        note_samples = int(sample_rate * note_duration)
        overlap = int(note_samples * 0.5)
        total_samples = note_samples * len(freqs) + overlap
        buf = array.array("h", [0] * total_samples)

        for idx, freq in enumerate(freqs):
            start_idx = idx * int(note_samples * 0.62)
            phase = 0.0
            dur = note_samples + overlap
            for i in range(dur):
                if start_idx + i >= total_samples:
                    break
                progress = i / dur
                phase += 2.0 * math.pi * freq / sample_rate
                attack = min(1.0, i / (sample_rate * 0.008))
                decay = math.pow(1.0 - progress, 1.35)
                val = 0.70 * math.sin(phase) + 0.20 * math.sin(phase * 2.0) + 0.10 * math.sin(phase * 3.0)
                sample = int(val * attack * decay * volume * 32767)
                mixed = buf[start_idx + i] + sample
                buf[start_idx + i] = max(-32768, min(32767, mixed))

        return pygame.mixer.Sound(buffer=buf)

    def _build_sounds(self):
        self.sounds["flip"] = self._generate_tone(320, 740, 0.08, 0.22, "rich")
        self.sounds["deal"] = self._generate_tone(250, 490, 0.045, 0.12, "sine")
        self.sounds["click"] = self._generate_tone(580, 920, 0.06, 0.24, "triangle")
        self.sounds["hint"] = self._generate_arpeggio([659.25, 880.0, 1174.66, 1567.98], 0.075, 0.26)
        self.sounds["mismatch"] = self._generate_arpeggio([285, 220], 0.13, 0.24)
        self.sounds["match"] = self._generate_arpeggio([523.25, 659.25, 783.99, 1046.50], 0.085, 0.26)
        self.sounds["combo"] = self._generate_arpeggio([587.33, 783.99, 987.77, 1174.66, 1567.98], 0.08, 0.28)
        self.sounds["victory"] = self._generate_arpeggio(
            [523.25, 659.25, 783.99, 1046.50, 1318.51, 1567.98], 0.13, 0.28
        )
        self.sounds["star"] = self._generate_tone(660, 1480, 0.18, 0.26, "rich")

    def play(self, name: str):
        if self.enabled and self.available and name in self.sounds and self.sounds[name]:
            self.sounds[name].play()

    def toggle(self) -> bool:
        self.enabled = not self.enabled
        if self.enabled:
            self.play("click")
        return self.enabled


class AssetGenerator:
    BASE_CARD_W = 112
    BASE_CARD_H = 136

    @staticmethod
    def _draw_ssaa_leaf(
        surf: pygame.Surface,
        start: Tuple[float, float],
        end: Tuple[float, float],
        width: float,
        dark_col: Tuple[int, int, int] = PALETTE["leaf_dark"],
        mid_col: Tuple[int, int, int] = PALETTE["leaf_mid"],
        light_col: Tuple[int, int, int] = PALETTE["leaf_light"],
    ):
        sx, sy = start
        ex, ey = end
        dx, dy = ex - sx, ey - sy
        dist = math.hypot(dx, dy)
        if dist < 2:
            return
        ux, uy = dx / dist, dy / dist
        px, py = -uy, ux

        p_base = (sx, sy)
        p_tip = (ex, ey)
        p_left1 = (sx + ux * dist * 0.32 + px * width * 0.55, sy + uy * dist * 0.32 + py * width * 0.55)
        p_left2 = (sx + ux * dist * 0.68 + px * width * 0.42, sy + uy * dist * 0.68 + py * width * 0.42)
        p_right1 = (sx + ux * dist * 0.68 - px * width * 0.42, sy + uy * dist * 0.68 - py * width * 0.42)
        p_right2 = (sx + ux * dist * 0.32 - px * width * 0.55, sy + uy * dist * 0.32 - py * width * 0.55)

        draw_aa_polygon(surf, dark_col, [p_base, p_left1, p_left2, p_tip, p_right1, p_right2])
        draw_aa_polygon(surf, mid_col, [p_base, p_left1, p_left2, p_tip])
        pygame.draw.line(surf, light_col, (int(sx), int(sy)), (int(ex), int(ey)), max(2, int(width * 0.12)))

    @staticmethod
    def create_master_card_back() -> pygame.Surface:
        ss = 2
        W = AssetGenerator.BASE_CARD_W * ss
        H = AssetGenerator.BASE_CARD_H * ss
        surf = pygame.Surface((W, H), pygame.SRCALPHA)
        rect = pygame.Rect(0, 0, W, H)
        rad = 18 * ss

        outer_bezel = create_linear_gradient_rect(
            W,
            H,
            [
                (0.0, PALETTE["gold_shine"]),
                (0.25, PALETTE["gold_mid"]),
                (0.55, PALETTE["gold_dark"]),
                (0.82, PALETTE["gold_light"]),
                (1.0, PALETTE["gold_shadow"]),
            ],
            border_radius=rad,
        )
        surf.blit(outer_bezel, (0, 0))
        pygame.draw.rect(surf, PALETTE["wood_mid"], rect, width=3, border_radius=rad)
        pygame.draw.rect(surf, PALETTE["gold_shine"], rect.inflate(-6, -6), width=2, border_radius=rad - 3)

        jade_rim = rect.inflate(-16, -16)
        pygame.draw.rect(surf, PALETTE["jade_deep"], jade_rim, border_radius=rad - 6)

        inner = rect.inflate(-22, -22)
        inner_rad = 12 * ss
        jade_grad = create_linear_gradient_rect(
            inner.width,
            inner.height,
            [
                (0.0, PALETTE["jade_light"]),
                (0.42, PALETTE["jade_mid"]),
                (0.85, PALETTE["jade_dark"]),
                (1.0, PALETTE["jade_deep"]),
            ],
            border_radius=inner_rad,
        )

        mcx, mcy = inner.width // 2, inner.height // 2
        for r_glow, alpha in [(88, 22), (66, 36), (44, 52)]:
            draw_aa_circle(jade_grad, (*PALETTE["jade_glow"], alpha), (mcx, mcy), r_glow)

        step = 34
        for y in range(-step, inner.height + step, step):
            for x in range(-step, inner.width + step, step):
                pts = [(x, y - 12), (x + 12, y), (x, y + 12), (x - 12, y)]
                draw_aa_polygon(jade_grad, (16, 74, 58, 115), pts)
                pts_hi = [(x, y - 7), (x + 7, y), (x, y + 7), (x - 7, y)]
                draw_aa_polygon(jade_grad, (98, 212, 162, 85), pts_hi)

        mask = pygame.Surface(inner.size, pygame.SRCALPHA)
        pygame.draw.rect(mask, (255, 255, 255, 255), mask.get_rect(), border_radius=inner_rad)
        jade_grad.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        surf.blit(jade_grad, inner.topleft)

        filigree_rect = inner.inflate(-10, -10)
        pygame.draw.rect(surf, PALETTE["gold_light"], filigree_rect, width=3, border_radius=inner_rad - 4)

        corners = [
            (filigree_rect.left + 12, filigree_rect.top + 12, 1, 1),
            (filigree_rect.right - 12, filigree_rect.top + 12, -1, 1),
            (filigree_rect.left + 12, filigree_rect.bottom - 12, 1, -1),
            (filigree_rect.right - 12, filigree_rect.bottom - 12, -1, -1),
        ]
        for cx, cy, dx, dy in corners:
            AssetGenerator._draw_ssaa_leaf(
                surf,
                (cx, cy),
                (cx + dx * 22, cy + dy * 8),
                10,
                PALETTE["gold_dark"],
                PALETTE["gold_mid"],
                PALETTE["gold_shine"],
            )
            AssetGenerator._draw_ssaa_leaf(
                surf,
                (cx, cy),
                (cx + dx * 8, cy + dy * 22),
                10,
                PALETTE["gold_dark"],
                PALETTE["gold_mid"],
                PALETTE["gold_shine"],
            )
            draw_radial_sphere(surf, (cx, cy), 6, PALETTE["gold_shadow"], PALETTE["gold_mid"], PALETTE["gold_shine"])

        cx, cy = W // 2, H // 2
        draw_aa_circle(surf, (10, 42, 34, 175), (cx, cy + 5), 58)
        draw_radial_sphere(surf, (cx, cy), 54, PALETTE["gold_shadow"], PALETTE["gold_mid"], PALETTE["gold_shine"])
        draw_radial_sphere(surf, (cx, cy), 43, PALETTE["jade_deep"], PALETTE["jade_dark"], PALETTE["jade_mid"])
        pygame.draw.circle(surf, PALETTE["gold_light"], (cx, cy), 43, width=3)

        for deg in range(0, 360, 45):
            rad_ang = math.radians(deg)
            sx = cx + math.cos(rad_ang) * 14
            sy = cy + math.sin(rad_ang) * 14
            ex = cx + math.cos(rad_ang) * 36
            ey = cy + math.sin(rad_ang) * 36
            AssetGenerator._draw_ssaa_leaf(
                surf,
                (sx, sy),
                (ex, ey),
                12,
                PALETTE["leaf_dark"],
                PALETTE["jade_light"],
                PALETTE["gold_light"],
            )

        draw_radial_sphere(surf, (cx, cy), 18, PALETTE["gold_dark"], PALETTE["gold_mid"], PALETTE["gold_shine"])
        draw_glossy_specular(surf, (cx - 6, cy - 6), 6, 3.5, 35, 230)

        sheen = pygame.Surface((W - 24, H // 2), pygame.SRCALPHA)
        pygame.draw.ellipse(sheen, (255, 255, 255, 42), (0, -H // 4, W - 24, H // 2))
        surf.blit(sheen, (12, 10))

        return surf

    @staticmethod
    def create_master_card_front(card_key: str) -> pygame.Surface:
        if ":" in card_key:
            fruit_type, variant = card_key.split(":", 1)
        else:
            fruit_type, variant = card_key, "base"

        ss = 2
        W = AssetGenerator.BASE_CARD_W * ss
        H = AssetGenerator.BASE_CARD_H * ss
        surf = pygame.Surface((W, H), pygame.SRCALPHA)
        rect = pygame.Rect(0, 0, W, H)
        rad = 18 * ss
        accent = FRUIT_THEME_COLORS.get(fruit_type, PALETTE["gold_mid"])

        outer_frame = create_linear_gradient_rect(
            W,
            H,
            [
                (0.0, PALETTE["gold_shine"]),
                (0.32, PALETTE["gold_mid"]),
                (0.72, PALETTE["gold_dark"]),
                (1.0, PALETTE["gold_shadow"]),
            ],
            border_radius=rad,
        )
        surf.blit(outer_frame, (0, 0))
        pygame.draw.rect(surf, PALETTE["botanical_border"], rect.inflate(-6, -6), width=3, border_radius=rad - 3)

        inner = rect.inflate(-18, -18)
        inner_rad = 13 * ss
        parchment = create_linear_gradient_rect(
            inner.width,
            inner.height,
            [
                (0.0, PALETTE["cream_bright"]),
                (0.65, PALETTE["cream"]),
                (1.0, PALETTE["cream_dark"]),
            ],
            border_radius=inner_rad,
        )
        surf.blit(parchment, inner.topleft)

        cx, cy = W // 2, H // 2 - 2
        for r_step, alpha in [(88, 20), (68, 34), (48, 52)]:
            draw_aa_circle(surf, (*accent, alpha), (cx, cy), r_step)

        if variant == "gold":
            for deg in range(0, 360, 30):
                ang = math.radians(deg)
                p1 = (cx, cy)
                p2 = (cx + math.cos(ang - 0.12) * 84, cy + math.sin(ang - 0.12) * 84)
                p3 = (cx + math.cos(ang + 0.12) * 84, cy + math.sin(ang + 0.12) * 84)
                draw_aa_polygon(surf, (255, 222, 75, 55), [p1, p2, p3])
            pygame.draw.circle(surf, PALETTE["gold_mid"], (cx, cy), 72, width=4)

        frame_rect = inner.inflate(-10, -10)
        border_col = PALETTE["gold_mid"] if variant == "gold" else PALETTE["botanical_border"]
        pygame.draw.rect(surf, (*border_col, 165), frame_rect, width=3, border_radius=inner_rad - 4)

        for px, py in [
            (frame_rect.left + 14, frame_rect.top + 14),
            (frame_rect.right - 14, frame_rect.top + 14),
            (frame_rect.left + 14, frame_rect.bottom - 14),
            (frame_rect.right - 14, frame_rect.bottom - 14),
        ]:
            pip_col = PALETTE["gold_mid"] if variant == "gold" else accent
            draw_radial_sphere(surf, (px, py), 6, PALETTE["jade_dark"], pip_col, (255, 255, 255))

        AssetGenerator._draw_fruit_ssaa(surf, fruit_type, cx, cy + 4)

        if variant == "gold":
            star_cx, star_cy = frame_rect.right - 26, frame_rect.top + 26
            draw_radial_sphere(surf, (star_cx, star_cy), 18, PALETTE["gold_shadow"], PALETTE["gold_mid"], PALETTE["gold_shine"])
            pts = []
            for i in range(10):
                a = -math.pi / 2 + i * (math.pi / 5)
                r = 13 if i % 2 == 0 else 5.5
                pts.append((star_cx + math.cos(a) * r, star_cy + math.sin(a) * r))
            draw_aa_polygon(surf, (255, 255, 240), pts)

        return surf

    @staticmethod
    def _draw_fruit_ssaa(surf: pygame.Surface, fruit_type: str, cx: int, cy: int):
        for i in range(6, 0, -1):
            sw = 90 + i * 10
            sh = 24 + i * 4
            s_surf = pygame.Surface((sw, sh), pygame.SRCALPHA)
            pygame.draw.ellipse(s_surf, (28, 42, 24, int(17 * (7 - i))), (0, 0, sw, sh))
            surf.blit(s_surf, s_surf.get_rect(center=(cx, cy + 56)))

        if fruit_type == "Strawberry":
            lobes = [
                (cx - 21, cy - 14, 34),
                (cx + 21, cy - 14, 34),
                (cx - 12, cy + 12, 30),
                (cx + 12, cy + 12, 30),
                (cx, cy + 32, 23),
                (cx, cy - 4, 38),
            ]
            for lx, ly, lr in lobes:
                draw_radial_sphere(
                    surf, (lx, ly), lr, (145, 12, 32), (235, 32, 58), (255, 105, 120), rim_col=(190, 20, 42)
                )
            draw_radial_sphere(surf, (cx - 10, cy - 12), 28, (235, 38, 60), (255, 75, 92), (255, 155, 165))
            seeds = [(-24, -14), (-8, -10), (10, -14), (25, -10), (-18, 5), (0, 6), (18, 4), (-11, 22), (9, 21), (0, 36)]
            for sx, sy in seeds:
                px, py = cx + sx, cy + sy
                draw_aa_circle(surf, (125, 10, 25), (px, py - 1), 5)
                draw_aa_polygon(surf, (255, 225, 85), [(px, py - 4), (px + 3, py + 1), (px, py + 4), (px - 3, py + 1)])
            draw_glossy_specular(surf, (cx - 24, cy - 22), 13, 7, 38, 220)
            pygame.draw.line(surf, (28, 105, 35), (cx, cy - 42), (cx + 8, cy - 66), 9)
            for tx, ty in [(-48, -42), (-26, -60), (26, -60), (48, -42), (0, -24)]:
                AssetGenerator._draw_ssaa_leaf(surf, (cx, cy - 42), (cx + tx, cy + ty), 18)

        elif fruit_type == "Pineapple":
            for start, end, w in [
                ((cx, cy - 26), (cx - 46, cy - 62), 20),
                ((cx, cy - 26), (cx + 46, cy - 62), 20),
                ((cx, cy - 32), (cx - 30, cy - 78), 22),
                ((cx, cy - 32), (cx + 30, cy - 78), 22),
                ((cx, cy - 36), (cx, cy - 86), 24),
            ]:
                AssetGenerator._draw_ssaa_leaf(surf, start, end, w)
            body_surf = pygame.Surface((120, 140), pygame.SRCALPHA)
            draw_radial_sphere(body_surf, (60, 72), 48, (175, 92, 8), (245, 175, 22), (255, 238, 115), rim_col=(135, 65, 5))
            stretched_body = pygame.transform.smoothscale(body_surf, (104, 118))
            surf.blit(stretched_body, stretched_body.get_rect(center=(cx, cy + 12)))
            for ry, x_list in [(-16, [-20, 0, 20]), (2, [-30, -10, 10, 30]), (20, [-20, 0, 20]), (38, [-12, 12])]:
                for rx in x_list:
                    px, py = cx + rx, cy + ry
                    draw_aa_polygon(surf, (165, 82, 8), [(px, py - 12), (px + 13, py), (px, py + 12), (px - 13, py)])
                    draw_aa_polygon(surf, (250, 190, 32), [(px, py - 9), (px + 10, py), (px, py + 9), (px - 10, py)])
                    draw_aa_circle(surf, (255, 240, 145), (px - 3, py - 3), 4)
            draw_glossy_specular(surf, (cx - 22, cy - 10), 12, 6, 60, 195)

        elif fruit_type == "Watermelon":
            wedge = pygame.Surface((168, 168), pygame.SRCALPHA)
            wcx, wcy = 84, 52
            draw_radial_sphere(wedge, (wcx, wcy), 70, (18, 95, 32), (42, 158, 58), (95, 215, 95), rim_col=(12, 65, 22))
            draw_radial_sphere(wedge, (wcx, wcy), 58, (205, 238, 180), (238, 252, 220), (255, 255, 245))
            draw_radial_sphere(wedge, (wcx, wcy), 50, (175, 18, 42), (242, 48, 72), (255, 120, 138))
            pygame.draw.rect(wedge, (0, 0, 0, 0), (0, 0, 168, wcy - 2))
            for sx, sy in [(-26, 16), (-10, 26), (10, 26), (26, 16), (-18, 34), (0, 38), (18, 34)]:
                draw_aa_circle(wedge, (32, 22, 26), (wcx + sx, wcy + sy), 4)
            draw_glossy_specular(wedge, (wcx - 22, wcy + 12), 12, 5, 12, 185)
            rotated = pygame.transform.rotozoom(wedge, -14, 1.0)
            surf.blit(rotated, rotated.get_rect(center=(cx, cy + 6)))

        elif fruit_type == "Kiwi":
            draw_aa_circle(surf, (88, 52, 24), (cx + 3, cy + 5), 58)
            draw_radial_sphere(surf, (cx, cy), 56, (112, 68, 32), (158, 104, 52), (195, 142, 82))
            draw_radial_sphere(surf, (cx, cy), 48, (78, 145, 20), (138, 208, 48), (195, 245, 95), rim_col=(55, 108, 14))
            for deg in range(0, 360, 20):
                rad = math.radians(deg)
                pygame.draw.line(surf, (218, 250, 145), (cx, cy), (int(cx + math.cos(rad) * 34), int(cy + math.sin(rad) * 34)), 3)
                draw_aa_circle(surf, (28, 22, 18), (cx + math.cos(rad) * 25, cy + math.sin(rad) * 25), 3)
            draw_radial_sphere(surf, (cx, cy), 16, (215, 242, 155), (242, 252, 210), (255, 255, 248))
            draw_glossy_specular(surf, (cx - 18, cy - 18), 14, 7, 40, 175)

        elif fruit_type == "Blueberry":
            AssetGenerator._draw_ssaa_leaf(surf, (cx, cy - 10), (cx - 56, cy - 46), 24)
            AssetGenerator._draw_ssaa_leaf(surf, (cx, cy - 10), (cx + 56, cy - 42), 24)
            draw_radial_sphere(surf, (cx + 24, cy - 10), 33, (25, 38, 118), (58, 88, 205), (135, 178, 255), rim_col=(18, 26, 85))
            draw_radial_sphere(surf, (cx - 14, cy + 12), 39, (28, 42, 132), (68, 102, 225), (155, 198, 255), rim_col=(20, 30, 95))
            draw_glossy_specular(surf, (cx - 28, cy - 2), 12, 6, 38, 235)

        elif fruit_type == "Mango":
            pygame.draw.line(surf, (92, 54, 24), (cx - 16, cy - 42), (cx - 8, cy - 62), 8)
            AssetGenerator._draw_ssaa_leaf(surf, (cx - 12, cy - 46), (cx + 46, cy - 38), 22)
            draw_radial_sphere(surf, (cx + 16, cy + 20), 31, (215, 125, 15), (252, 188, 28), (215, 235, 65))
            draw_radial_sphere(surf, (cx - 6, cy - 4), 45, (205, 52, 22), (252, 125, 24), (255, 205, 75))
            draw_radial_sphere(surf, (cx - 16, cy - 16), 28, (215, 42, 38), (248, 78, 48), (255, 165, 95))
            draw_glossy_specular(surf, (cx - 24, cy - 20), 14, 7, 42, 225)

        elif fruit_type == "Orange":
            draw_radial_sphere(surf, (cx, cy + 4), 52, (185, 68, 6), (255, 138, 16), (255, 215, 75), rim_col=(145, 48, 4))
            for px, py in [(14, 12), (26, 4), (18, 26), (6, 30), (30, -10), (22, -20), (-8, 28)]:
                draw_aa_circle(surf, (205, 82, 8), (cx + px, cy + 4 + py), 2.5)
            pygame.draw.line(surf, (88, 52, 22), (cx, cy - 42), (cx + 2, cy - 60), 7)
            AssetGenerator._draw_ssaa_leaf(surf, (cx + 2, cy - 46), (cx + 52, cy - 36), 22)
            draw_glossy_specular(surf, (cx - 20, cy - 16), 15, 8, 38, 230)

        elif fruit_type == "Cherry":
            top_x, top_y = cx + 6, cy - 56
            pygame.draw.lines(surf, (46, 138, 34), False, [(top_x, top_y), (cx - 10, cy - 24), (cx - 26, cy + 14)], 6)
            pygame.draw.lines(surf, (46, 138, 34), False, [(top_x, top_y), (cx + 18, cy - 24), (cx + 28, cy + 8)], 6)
            AssetGenerator._draw_ssaa_leaf(surf, (top_x, top_y), (cx + 56, cy - 44), 22)
            draw_radial_sphere(surf, (cx + 26, cy + 20), 29, (92, 6, 22), (188, 16, 44), (255, 85, 108), rim_col=(65, 4, 14))
            draw_radial_sphere(surf, (cx - 22, cy + 26), 32, (102, 6, 24), (208, 18, 48), (255, 98, 118), rim_col=(68, 4, 15))
            draw_glossy_specular(surf, (cx - 33, cy + 15), 10, 5, 36, 240)
            draw_glossy_specular(surf, (cx + 17, cy + 10), 8, 4, 35, 225)

        elif fruit_type == "Dragonfruit":
            for sx, sy in [(-38, -28), (38, -28), (-44, 6), (44, 6), (0, -54)]:
                AssetGenerator._draw_ssaa_leaf(surf, (cx, cy), (cx + sx * 1.4, cy + sy * 1.4), 18, (42, 145, 52), (95, 210, 75), (175, 245, 120))
            draw_radial_sphere(surf, (cx, cy + 4), 50, (155, 14, 78), (236, 42, 128), (255, 135, 190))
            draw_radial_sphere(surf, (cx, cy + 4), 38, (210, 215, 225), (245, 248, 255), (255, 255, 255))
            for deg in range(0, 360, 36):
                for r_d in (12, 24, 31):
                    ang = math.radians(deg + r_d * 2)
                    draw_aa_circle(surf, (28, 24, 32), (cx + math.cos(ang) * r_d, cy + 4 + math.sin(ang) * r_d), 2.5)
            draw_glossy_specular(surf, (cx - 18, cy - 14), 12, 6, 38, 210)

        elif fruit_type == "Coconut":
            draw_radial_sphere(surf, (cx, cy + 4), 52, (68, 38, 18), (118, 72, 38), (168, 112, 68), rim_col=(48, 26, 12))
            draw_radial_sphere(surf, (cx, cy + 6), 40, (205, 215, 220), (245, 250, 252), (255, 255, 255))
            draw_radial_sphere(surf, (cx, cy + 8), 24, (165, 218, 238), (210, 242, 255), (245, 255, 255))
            draw_glossy_specular(surf, (cx - 14, cy - 10), 12, 6, 35, 215)

        elif fruit_type == "Banana":
            pts_outer = []
            pts_inner = []
            for i in range(15):
                t = i / 14.0
                ang = lerp(-2.3, 0.5, t)
                pts_outer.append((cx + 12 + math.cos(ang) * 56, cy - 12 + math.sin(ang) * 56))
                pts_inner.append((cx + 4 + math.cos(ang) * 32, cy - 6 + math.sin(ang) * 32))
            poly = pts_outer + list(reversed(pts_inner))
            draw_aa_polygon(surf, (215, 158, 12), [(x, y + 5) for x, y in poly])
            draw_aa_polygon(surf, (252, 218, 42), poly)
            draw_aa_polygon(surf, (255, 246, 145), pts_outer[:10] + list(reversed(pts_inner[:10])))
            draw_aa_circle(surf, (115, 78, 24), pts_outer[0], 6)
            draw_aa_circle(surf, (115, 78, 24), pts_outer[-1], 5)

        elif fruit_type == "Grapes":
            AssetGenerator._draw_ssaa_leaf(surf, (cx, cy - 38), (cx - 46, cy - 58), 22)
            AssetGenerator._draw_ssaa_leaf(surf, (cx, cy - 38), (cx + 46, cy - 58), 22)
            grape_pos = [
                (-28, -18), (0, -20), (28, -18),
                (-20, 2), (8, 2), (24, 4),
                (-12, 22), (12, 22), (0, 38),
            ]
            for gx, gy in grape_pos:
                draw_radial_sphere(surf, (cx + gx, cy + gy), 19, (68, 18, 118), (138, 52, 205), (212, 152, 255))
                draw_aa_circle(surf, (255, 245, 255), (cx + gx - 6, cy + gy - 6), 3)

        elif fruit_type == "Peach":
            AssetGenerator._draw_ssaa_leaf(surf, (cx, cy - 42), (cx + 48, cy - 36), 22)
            draw_radial_sphere(surf, (cx - 16, cy + 4), 42, (215, 52, 48), (255, 128, 88), (255, 212, 158))
            draw_radial_sphere(surf, (cx + 16, cy + 4), 42, (215, 52, 48), (255, 138, 92), (255, 218, 165))
            draw_aa_polygon(surf, (252, 105, 75), [(cx - 22, cy + 32), (cx + 22, cy + 32), (cx, cy + 54)])
            draw_glossy_specular(surf, (cx - 24, cy - 14), 14, 7, 38, 220)

        elif fruit_type == "Pear":
            pygame.draw.line(surf, (92, 54, 22), (cx, cy - 38), (cx + 6, cy - 62), 7)
            AssetGenerator._draw_ssaa_leaf(surf, (cx + 2, cy - 48), (cx + 46, cy - 38), 20)
            draw_radial_sphere(surf, (cx, cy + 16), 44, (98, 152, 18), (162, 216, 48), (225, 252, 128))
            draw_radial_sphere(surf, (cx, cy - 18), 28, (108, 162, 22), (172, 222, 56), (235, 255, 148))
            draw_glossy_specular(surf, (cx - 16, cy + 6), 13, 6, 42, 215)

        elif fruit_type in ("Lemon", "Lime"):
            is_lemon = fruit_type == "Lemon"
            c_sh = (185, 148, 8) if is_lemon else (22, 118, 28)
            c_mid = (250, 222, 32) if is_lemon else (72, 198, 54)
            c_hi = (255, 252, 155) if is_lemon else (175, 248, 135)
            draw_aa_circle(surf, c_mid, (cx - 46, cy + 4), 14)
            draw_aa_circle(surf, c_mid, (cx + 46, cy + 4), 14)
            draw_radial_sphere(surf, (cx, cy + 4), 46, c_sh, c_mid, c_hi)
            AssetGenerator._draw_ssaa_leaf(surf, (cx, cy - 40), (cx + 46, cy - 34), 20)
            draw_glossy_specular(surf, (cx - 18, cy - 14), 15, 7, 35, 230)

        elif fruit_type == "Pomegranate":
            crown_pts = [(cx - 18, cy - 38), (cx - 12, cy - 56), (cx, cy - 44), (cx + 12, cy - 56), (cx + 18, cy - 38)]
            draw_aa_polygon(surf, (158, 18, 36), crown_pts)
            draw_radial_sphere(surf, (cx, cy + 6), 50, (118, 10, 26), (198, 24, 48), (255, 98, 115), rim_col=(88, 6, 18))
            draw_radial_sphere(surf, (cx + 10, cy + 14), 26, (235, 195, 185), (252, 228, 220), (255, 248, 245))
            for rx, ry in [(4, 8), (16, 8), (10, 18), (2, 18), (18, 18), (10, 26)]:
                draw_radial_sphere(surf, (cx + rx, cy + ry), 6, (125, 6, 22), (225, 18, 48), (255, 165, 180))
            draw_glossy_specular(surf, (cx - 22, cy - 14), 14, 7, 38, 220)

        elif fruit_type == "Papaya":
            draw_radial_sphere(surf, (cx, cy + 4), 50, (42, 128, 38), (238, 148, 28), (255, 205, 85))
            draw_radial_sphere(surf, (cx, cy + 6), 40, (215, 68, 18), (255, 118, 38), (255, 178, 95))
            draw_radial_sphere(surf, (cx, cy + 8), 20, (55, 28, 18), (85, 48, 32), (115, 68, 45))
            for deg in range(0, 360, 36):
                ang = math.radians(deg)
                draw_aa_circle(surf, (28, 22, 24), (cx + math.cos(ang) * 14, cy + 8 + math.sin(ang) * 14), 4)
            draw_glossy_specular(surf, (cx - 20, cy - 14), 13, 6, 38, 215)

        elif fruit_type == "Plum":
            AssetGenerator._draw_ssaa_leaf(surf, (cx, cy - 42), (cx + 46, cy - 34), 22)
            draw_radial_sphere(surf, (cx - 10, cy + 4), 44, (58, 14, 88), (128, 38, 168), (212, 128, 248))
            draw_radial_sphere(surf, (cx + 12, cy + 6), 42, (52, 12, 82), (118, 34, 158), (198, 118, 242))
            draw_glossy_specular(surf, (cx - 22, cy - 14), 14, 7, 38, 230)

        elif fruit_type == "Passionfruit":
            draw_radial_sphere(surf, (cx, cy + 4), 50, (78, 18, 62), (142, 38, 108), (205, 98, 168))
            draw_radial_sphere(surf, (cx, cy + 4), 42, (235, 228, 215), (252, 248, 238), (255, 255, 252))
            draw_radial_sphere(surf, (cx, cy + 4), 35, (215, 128, 12), (252, 188, 28), (255, 232, 95))
            for deg in range(0, 360, 30):
                ang = math.radians(deg)
                r_d = 18 if deg % 60 == 0 else 26
                draw_aa_circle(surf, (185, 72, 12), (cx + math.cos(ang) * r_d, cy + 4 + math.sin(ang) * r_d), 5)
                draw_aa_circle(surf, (32, 18, 14), (cx + math.cos(ang) * r_d, cy + 4 + math.sin(ang) * r_d), 3)
            draw_glossy_specular(surf, (cx - 16, cy - 12), 12, 6, 35, 210)

        elif fruit_type == "Starfruit":
            pts_outer = []
            pts_inner = []
            for i in range(10):
                ang = -math.pi / 2 + i * (math.pi / 5)
                r_o = 56 if i % 2 == 0 else 25
                r_i = 46 if i % 2 == 0 else 20
                pts_outer.append((cx + math.cos(ang) * r_o, cy + 4 + math.sin(ang) * r_o))
                pts_inner.append((cx + math.cos(ang) * r_i, cy + 4 + math.sin(ang) * r_i))
            draw_aa_polygon(surf, (165, 138, 12), [(x, y + 4) for x, y in pts_outer])
            draw_aa_polygon(surf, (238, 198, 24), pts_outer)
            draw_aa_polygon(surf, (255, 242, 118), pts_inner)
            for sx, sy in [(-6, -4), (6, -4), (0, 8)]:
                draw_aa_circle(surf, (118, 68, 22), (cx + sx, cy + 4 + sy), 3)

        elif fruit_type == "Guava":
            AssetGenerator._draw_ssaa_leaf(surf, (cx, cy - 42), (cx - 46, cy - 34), 22)
            draw_radial_sphere(surf, (cx, cy + 4), 50, (38, 128, 42), (98, 192, 68), (175, 238, 118))
            draw_radial_sphere(surf, (cx, cy + 4), 42, (238, 245, 215), (248, 252, 232), (255, 255, 245))
            draw_radial_sphere(surf, (cx, cy + 4), 35, (205, 48, 68), (248, 92, 112), (255, 162, 175))
            for deg in range(0, 360, 40):
                ang = math.radians(deg)
                draw_aa_circle(surf, (255, 235, 145), (cx + math.cos(ang) * 20, cy + 4 + math.sin(ang) * 20), 2.5)
            draw_glossy_specular(surf, (cx - 16, cy - 12), 13, 6, 38, 215)

        elif fruit_type == "Fig":
            pygame.draw.line(surf, (78, 138, 38), (cx, cy - 38), (cx + 4, cy - 58), 7)
            draw_radial_sphere(surf, (cx, cy + 14), 44, (58, 22, 78), (112, 48, 138), (178, 108, 205))
            draw_radial_sphere(surf, (cx, cy - 16), 26, (68, 28, 88), (128, 62, 148), (188, 128, 195))
            draw_radial_sphere(surf, (cx, cy + 16), 28, (238, 218, 198), (252, 242, 228), (255, 252, 245))
            draw_radial_sphere(surf, (cx, cy + 16), 22, (185, 22, 48), (238, 52, 78), (255, 128, 145))
            draw_glossy_specular(surf, (cx - 18, cy + 2), 12, 5, 38, 210)

        elif fruit_type == "GreenApple":
            pygame.draw.line(surf, (88, 52, 22), (cx, cy - 38), (cx + 6, cy - 58), 7)
            AssetGenerator._draw_ssaa_leaf(surf, (cx + 2, cy - 44), (cx + 48, cy - 34), 22)
            draw_radial_sphere(surf, (cx - 14, cy + 4), 43, (32, 128, 28), (92, 198, 52), (195, 252, 118))
            draw_radial_sphere(surf, (cx + 14, cy + 4), 43, (32, 128, 28), (98, 205, 56), (198, 252, 122))
            draw_glossy_specular(surf, (cx - 22, cy - 14), 15, 8, 38, 235)

        else:
            AssetGenerator._draw_ssaa_leaf(surf, (cx, cy - 42), (cx + 46, cy - 34), 22)
            draw_radial_sphere(surf, (cx, cy + 4), 48, (168, 22, 48), (238, 64, 92), (255, 148, 168))
            for dy in range(-28, 36, 14):
                for dx in range(-28, 36, 14):
                    if dx * dx + dy * dy <= 38 * 38:
                        draw_aa_circle(surf, (188, 28, 56), (cx + dx, cy + 4 + dy), 4)
                        draw_aa_circle(surf, (255, 175, 188), (cx + dx - 1, cy + 3 + dy), 2)
            draw_radial_sphere(surf, (cx + 12, cy + 12), 24, (215, 228, 235), (248, 252, 255), (255, 255, 255))
            draw_radial_sphere(surf, (cx + 14, cy + 14), 11, (68, 28, 14), (118, 52, 28), (168, 92, 58))
            draw_glossy_specular(surf, (cx - 18, cy - 14), 12, 6, 38, 220)

    @staticmethod
    def create_wooden_banner(width: int, height: int, has_vines: bool = True) -> pygame.Surface:
        ss = 2
        pad_x, pad_y = 26, 20
        W = (width + pad_x * 2) * ss
        H = (height + pad_y * 2) * ss
        surf = pygame.Surface((W, H), pygame.SRCALPHA)

        rx, ry = pad_x * ss, pad_y * ss
        rw, rh = width * ss, height * ss
        rect = pygame.Rect(rx, ry, rw, rh)
        rad = 20 * ss

        shadow = create_soft_shadow(rw, rh, rad, blur_steps=7, max_alpha=130)
        surf.blit(shadow, shadow.get_rect(center=(rect.centerx, rect.centery + 10)))

        pygame.draw.rect(surf, PALETTE["wood_deep"], rect, border_radius=rad)
        gold_rim = create_linear_gradient_rect(
            rw - 8,
            rh - 8,
            [
                (0.0, PALETTE["gold_light"]),
                (0.45, PALETTE["gold_mid"]),
                (0.8, PALETTE["gold_dark"]),
                (1.0, PALETTE["gold_shadow"]),
            ],
            border_radius=rad - 3,
        )
        surf.blit(gold_rim, (rx + 4, ry + 4))

        inner = rect.inflate(-20, -20)
        wood_grad = create_linear_gradient_rect(
            inner.width,
            inner.height,
            [
                (0.0, PALETTE["wood_light"]),
                (0.18, PALETTE["wood_mid"]),
                (0.85, PALETTE["wood_dark"]),
                (1.0, PALETTE["wood_deep"]),
            ],
            border_radius=rad - 8,
        )

        for gy in range(16, inner.height - 12, 22):
            pts = []
            for gx in range(12, inner.width - 12, 16):
                wy = gy + math.sin(gx * 0.025 + gy) * 4.0
                pts.append((gx, wy))
            if len(pts) > 2:
                pygame.draw.lines(wood_grad, (92, 44, 18, 140), False, pts, 3)
                pygame.draw.lines(wood_grad, (182, 106, 50, 90), False, [(x, y + 3) for x, y in pts], 2)

        surf.blit(wood_grad, inner.topleft)
        pygame.draw.rect(surf, PALETTE["wood_highlight"], inner, width=3, border_radius=rad - 8)
        pygame.draw.rect(surf, PALETTE["wood_deep"], inner.inflate(4, 4), width=3, border_radius=rad - 7)

        bolt_inset = 26
        for bx, by in [
            (rect.left + bolt_inset, rect.top + bolt_inset),
            (rect.right - bolt_inset, rect.top + bolt_inset),
            (rect.left + bolt_inset, rect.bottom - bolt_inset),
            (rect.right - bolt_inset, rect.bottom - bolt_inset),
        ]:
            draw_aa_circle(surf, PALETTE["wood_deep"], (bx, by + 3), 10)
            draw_radial_sphere(surf, (bx, by), 9, PALETTE["gold_shadow"], PALETTE["gold_mid"], PALETTE["gold_shine"])

        if has_vines:
            for side in (-1, 1):
                lx = rect.left + 8 if side == -1 else rect.right - 8
                ly = rect.centery
                AssetGenerator._draw_ssaa_leaf(surf, (lx, ly), (lx + side * 44, ly - 32), 24)
                AssetGenerator._draw_ssaa_leaf(surf, (lx, ly + 6), (lx + side * 38, ly + 30), 20)

        return pygame.transform.smoothscale(surf, (width + pad_x * 2, height + pad_y * 2))

    @staticmethod
    def create_board_frame(
        grid_w: int,
        grid_h: int,
        rows: int,
        cols: int,
        card_w: int,
        card_h: int,
        gap_x: int,
        gap_y: int,
    ) -> pygame.Surface:
        pad = 24
        fw, fh = grid_w + pad * 2, grid_h + pad * 2
        surf = pygame.Surface((fw + 24, fh + 24), pygame.SRCALPHA)
        ox, oy = 12, 10
        rect = pygame.Rect(ox, oy, fw, fh)

        shadow = create_soft_shadow(fw, fh, 26, blur_steps=7, max_alpha=115)
        surf.blit(shadow, shadow.get_rect(center=(rect.centerx, rect.centery + 6)))

        pygame.draw.rect(surf, (38, 22, 10, 230), rect, border_radius=26)
        pygame.draw.rect(surf, (*PALETTE["gold_mid"], 235), rect.inflate(-6, -6), width=3, border_radius=23)
        pygame.draw.rect(surf, (108, 60, 26, 220), rect.inflate(-10, -10), width=6, border_radius=20)

        tray = rect.inflate(-20, -20)
        pygame.draw.rect(surf, (16, 48, 32, 150), tray, border_radius=16)
        pygame.draw.rect(surf, (8, 24, 16, 185), tray, width=3, border_radius=16)
        pygame.draw.line(
            surf,
            (185, 242, 195, 85),
            (tray.left + 14, tray.bottom - 2),
            (tray.right - 14, tray.bottom - 2),
            2,
        )

        slot_start_x = ox + pad
        slot_start_y = oy + pad
        slot_rad = max(5, int(14 * (card_w / 112.0)))
        for r in range(rows):
            for c in range(cols):
                sx = slot_start_x + c * (card_w + gap_x)
                sy = slot_start_y + r * (card_h + gap_y)
                slot_rect = pygame.Rect(sx + 2, sy + 2, card_w - 4, card_h - 4)
                pygame.draw.rect(surf, (10, 30, 20, 95), slot_rect, border_radius=slot_rad)
                pygame.draw.rect(surf, (210, 255, 220, 24), slot_rect.inflate(2, 2), width=1, border_radius=slot_rad + 1)

        return surf

    @staticmethod
    def create_star_sprite(radius: int, earned: bool = True) -> pygame.Surface:
        ss = 2
        R = radius * ss
        size = R * 3
        surf = pygame.Surface((size, size), pygame.SRCALPHA)
        cx, cy = size // 2, size // 2

        if earned:
            for r_glow in range(int(R * 1.35), int(R * 0.5), -6):
                t = 1.0 - (r_glow / (R * 1.35))
                draw_aa_circle(surf, (255, 235, 110, int(85 * t * t)), (cx, cy), r_glow)

        pts_outer = []
        for i in range(10):
            ang = -math.pi / 2.0 + i * (math.pi / 5.0)
            r = R if i % 2 == 0 else R * 0.44
            pts_outer.append((cx + math.cos(ang) * r, cy + math.sin(ang) * r))

        if not earned:
            draw_aa_polygon(surf, (38, 20, 8, 210), [(x, y + 3) for x, y in pts_outer])
            draw_aa_polygon(surf, (68, 38, 18, 230), pts_outer)
            pygame.draw.polygon(surf, (115, 68, 32, 180), pts_outer, width=3)
            return pygame.transform.smoothscale(surf, (size // ss, size // ss))

        draw_aa_polygon(surf, (75, 36, 6, 180), [(x, y + 6) for x, y in pts_outer])

        facet_lights = [
            (255, 248, 165), (215, 148, 18),
            (255, 235, 115), (185, 118, 12),
            (245, 195, 35), (165, 98, 10),
            (230, 172, 24), (195, 128, 14),
            (255, 225, 95), (225, 160, 20),
        ]
        for i in range(10):
            p1 = pts_outer[i]
            p2 = pts_outer[(i + 1) % 10]
            draw_aa_polygon(surf, facet_lights[i], [(cx, cy), p1, p2])

        draw_radial_sphere(surf, (cx, cy), int(R * 0.32), (245, 185, 25), (255, 232, 110), (255, 255, 235))
        draw_glossy_specular(surf, (cx - R * 0.14, cy - R * 0.16), R * 0.18, R * 0.09, 35, 235)

        return pygame.transform.smoothscale(surf, (size // ss, size // ss))


class GraphicalButton:
    THEMES = {
        "green_gem": ((12, 78, 28), (22, 128, 46), (48, 198, 76), (145, 252, 142)),
        "orange_gem": ((118, 42, 6), (185, 76, 12), (248, 138, 24), (255, 214, 112)),
        "red_gem": ((104, 12, 24), (168, 24, 42), (232, 52, 72), (255, 148, 162)),
        "blue_gem": ((14, 48, 118), (28, 88, 188), (62, 148, 248), (158, 218, 255)),
        "purple_gem": ((64, 18, 108), (108, 38, 172), (168, 78, 238), (224, 172, 255)),
        "gold_gem": ((118, 68, 8), (182, 118, 14), (248, 192, 34), (255, 244, 148)),
        "teal_gem": ((12, 64, 54), (22, 108, 88), (44, 168, 132), (138, 236, 198)),
        "wood_plaque": (PALETTE["wood_deep"], PALETTE["wood_dark"], PALETTE["wood_mid"], PALETTE["wood_highlight"]),
    }

    def __init__(
        self,
        center: Tuple[int, int],
        size: Tuple[int, int],
        text: str = "",
        icon_type: Optional[str] = None,
        theme: str = "green_gem",
        callback: Optional[Callable[[], None]] = None,
        font: Optional[pygame.font.Font] = None,
        badge_text: str = "",
        is_selected: bool = False,
    ):
        self.center = list(center)
        self.size = size
        self.text = text
        self.icon_type = icon_type
        self.theme = theme
        self.callback = callback
        self.font = font
        self.badge_text = badge_text
        self.is_selected = is_selected

        self.scale_spring = Spring(1.0, stiffness=320.0, damping=18.0)
        self.hover_alpha = 0.0
        self.is_hovered = False
        self.is_pressed = False

        self.pad = 10
        self.lip_h = 6
        self._rebuild_surfaces()

    def _rebuild_surfaces(self):
        self.face_surface, self.lip_surface, self.shadow_surface = self._generate_ssaa_parts()
        self.glow_surface = self._build_glow_surface()

    def set_icon(self, new_icon: str):
        if self.icon_type != new_icon:
            self.icon_type = new_icon
            self._rebuild_surfaces()

    def set_badge(self, badge: str):
        if self.badge_text != badge:
            self.badge_text = badge
            self._rebuild_surfaces()

    def set_selected(self, selected: bool, theme: Optional[str] = None):
        changed = self.is_selected != selected or (theme is not None and self.theme != theme)
        self.is_selected = selected
        if theme is not None:
            self.theme = theme
        if changed:
            self._rebuild_surfaces()

    def _generate_ssaa_parts(self) -> Tuple[pygame.Surface, pygame.Surface, pygame.Surface]:
        ss = 2
        w, h = self.size
        pad = self.pad
        W, H = (w + pad * 2) * ss, (h + pad * 2) * ss

        rx, ry = pad * ss, pad * ss
        rw, rh = w * ss, (h - self.lip_h) * ss
        radius = rh // 2 if rw <= rh * 1.35 else 18 * ss

        c_lip, c_dark, c_mid, c_light = self.THEMES.get(self.theme, self.THEMES["green_gem"])

        shadow_hi = create_soft_shadow(rw, rh + self.lip_h * ss, radius, blur_steps=5, max_alpha=120)
        shadow_down = pygame.transform.smoothscale(
            shadow_hi, (shadow_hi.get_width() // ss, shadow_hi.get_height() // ss)
        )

        lip_surf_hi = pygame.Surface((W, H), pygame.SRCALPHA)
        lip_rect = pygame.Rect(rx, ry + self.lip_h * ss, rw, rh)
        pygame.draw.rect(lip_surf_hi, PALETTE["gold_shadow"], lip_rect, border_radius=radius)
        pygame.draw.rect(lip_surf_hi, c_lip, lip_rect.inflate(-8, -8), border_radius=max(6, radius - 4))
        lip_down = pygame.transform.smoothscale(lip_surf_hi, (w + pad * 2, h + pad * 2))

        face_surf_hi = pygame.Surface((W, H), pygame.SRCALPHA)
        face_rect = pygame.Rect(rx, ry, rw, rh)

        rim_stops = (
            [
                (0.0, (255, 255, 240)),
                (0.35, PALETTE["gold_light"]),
                (0.75, PALETTE["gold_mid"]),
                (1.0, PALETTE["gold_dark"]),
            ]
            if self.is_selected
            else [
                (0.0, PALETTE["gold_shine"]),
                (0.35, PALETTE["gold_mid"]),
                (0.75, PALETTE["gold_dark"]),
                (1.0, PALETTE["gold_shadow"]),
            ]
        )
        gold_rim = create_linear_gradient_rect(rw, rh, rim_stops, border_radius=radius)
        face_surf_hi.blit(gold_rim, face_rect.topleft)

        inner_body = face_rect.inflate(-12, -12)
        b_rad = max(6, radius - 6)
        body_grad = create_linear_gradient_rect(
            inner_body.width,
            inner_body.height,
            [
                (0.0, c_light),
                (0.28, c_mid),
                (0.85, c_dark),
                (1.0, c_mid),
            ],
            border_radius=b_rad,
        )
        face_surf_hi.blit(body_grad, inner_body.topleft)

        pygame.draw.rect(face_surf_hi, (*c_light, 190), inner_body, width=3, border_radius=b_rad)

        gloss_w = inner_body.width - 24
        gloss_h = max(8, int(inner_body.height * 0.44))
        if gloss_w > 10:
            gloss = pygame.Surface((gloss_w, gloss_h), pygame.SRCALPHA)
            for y in range(gloss_h):
                a = int(lerp(170, 8, y / float(gloss_h)))
                pygame.draw.line(gloss, (255, 255, 255, a), (0, y), (gloss_w, y))
            g_mask = pygame.Surface((gloss_w, gloss_h), pygame.SRCALPHA)
            pygame.draw.rect(g_mask, (255, 255, 255, 255), g_mask.get_rect(), border_radius=max(4, b_rad - 5))
            gloss.blit(g_mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
            face_surf_hi.blit(gloss, (inner_body.left + 12, inner_body.top + 5))

        face_down = pygame.transform.smoothscale(face_surf_hi, (w + pad * 2, h + pad * 2))
        cx = pad + w // 2
        cy = pad + (h - self.lip_h) // 2

        if self.icon_type and self.text:
            icon_x = pad + 30
            self._draw_icon(face_down, self.icon_type, (icon_x, cy))
            if self.font:
                txt = render_arcade_text(self.font, self.text, (255, 255, 255), (255, 236, 175), (38, 18, 6), 2, 2)
                face_down.blit(txt, txt.get_rect(center=(cx + 14, cy)))
        elif self.icon_type:
            self._draw_icon(face_down, self.icon_type, (cx, cy))
        elif self.text and self.font:
            top_c = (255, 255, 255)
            bot_c = (255, 244, 165) if self.is_selected else (245, 228, 175)
            txt = render_arcade_text(self.font, self.text, top_c, bot_c, (38, 18, 6), 2, 2)
            face_down.blit(txt, txt.get_rect(center=(cx, cy)))

        if self.badge_text:
            bx = pad + w - 10
            by = pad + 10
            draw_aa_circle(face_down, PALETTE["gold_shadow"], (bx, by + 1), 12)
            draw_aa_circle(face_down, PALETTE["gold_light"], (bx, by), 11)
            draw_aa_circle(face_down, (215, 38, 58), (bx, by), 9)
            b_font = pygame.font.SysFont("trebuchetms,verdana,arial", 13, bold=True)
            b_txt = b_font.render(self.badge_text, True, (255, 255, 255))
            face_down.blit(b_txt, b_txt.get_rect(center=(bx, by)))

        return face_down, lip_down, shadow_down

    def _draw_icon(self, surf: pygame.Surface, icon_type: str, center: Tuple[int, int]):
        cx, cy = center
        shadow_col = (26, 12, 6, 185)
        white = (255, 252, 240)

        if icon_type == "play":
            pts_sh = [(cx - 6, cy - 8), (cx - 6, cy + 12), (cx + 12, cy + 2)]
            pts = [(cx - 6, cy - 10), (cx - 6, cy + 10), (cx + 12, cy)]
            draw_aa_polygon(surf, shadow_col, pts_sh)
            draw_aa_polygon(surf, white, pts)

        elif icon_type == "restart":
            pygame.draw.arc(surf, shadow_col, (cx - 11, cy - 9, 22, 22), 0.7, 5.4, 4)
            pygame.draw.arc(surf, white, (cx - 11, cy - 11, 22, 22), 0.7, 5.4, 4)
            arrow = [(cx + 4, cy - 12), (cx + 13, cy - 11), (cx + 9, cy - 3)]
            draw_aa_polygon(surf, white, arrow)

        elif icon_type == "hint":
            for deg in range(0, 360, 45):
                ang = math.radians(deg)
                x1 = cx + math.cos(ang) * 10
                y1 = (cy - 2) + math.sin(ang) * 10
                x2 = cx + math.cos(ang) * 14
                y2 = (cy - 2) + math.sin(ang) * 14
                pygame.draw.line(surf, (255, 245, 150), (int(x1), int(y1)), (int(x2), int(y2)), 2)
            draw_aa_circle(surf, shadow_col, (cx, cy), 8)
            draw_aa_circle(surf, (255, 245, 130), (cx, cy - 2), 8)
            draw_aa_circle(surf, white, (cx - 2, cy - 4), 5)
            pygame.draw.rect(surf, (220, 220, 230), (cx - 4, cy + 5, 8, 5), border_radius=2)

        elif icon_type in ("sound_on", "sound_off"):
            spk = [
                (cx - 11, cy - 4), (cx - 5, cy - 4), (cx + 2, cy - 10),
                (cx + 2, cy + 10), (cx - 5, cy + 4), (cx - 11, cy + 4),
            ]
            draw_aa_polygon(surf, shadow_col, [(x, y + 2) for x, y in spk])
            draw_aa_polygon(surf, white, spk)
            if icon_type == "sound_on":
                pygame.draw.arc(surf, white, (cx - 1, cy - 7, 10, 14), -1.0, 1.0, 2)
                pygame.draw.arc(surf, white, (cx + 2, cy - 11, 13, 22), -1.0, 1.0, 2)
            else:
                pygame.draw.line(surf, (255, 95, 95), (cx + 5, cy - 6), (cx + 13, cy + 6), 3)
                pygame.draw.line(surf, (255, 95, 95), (cx + 13, cy - 6), (cx + 5, cy + 6), 3)

        elif icon_type == "quit":
            pygame.draw.line(surf, shadow_col, (cx - 8, cy - 6), (cx + 8, cy + 10), 5)
            pygame.draw.line(surf, shadow_col, (cx + 8, cy - 6), (cx - 8, cy + 10), 5)
            pygame.draw.line(surf, white, (cx - 8, cy - 8), (cx + 8, cy + 8), 4)
            pygame.draw.line(surf, white, (cx + 8, cy - 8), (cx - 8, cy + 8), 4)

        elif icon_type == "menu":
            for dy in (-7, 0, 7):
                pygame.draw.rect(surf, shadow_col, (cx - 10, cy + dy + 1, 20, 4), border_radius=2)
                pygame.draw.rect(surf, white, (cx - 10, cy + dy - 1, 20, 4), border_radius=2)

    def _build_glow_surface(self) -> pygame.Surface:
        w, h = self.face_surface.get_size()
        glow = pygame.Surface((w + 20, h + 20), pygame.SRCALPHA)
        rect = pygame.Rect(6, 6, w + 8, h + 8)
        radius = h // 2 if self.size[0] <= self.size[1] * 1.35 else 24
        pygame.draw.rect(glow, (255, 242, 145, 75), rect, border_radius=radius)
        pygame.draw.rect(glow, (255, 255, 215, 135), rect.inflate(-6, -6), width=3, border_radius=max(4, radius - 3))
        return glow

    def get_rect(self) -> pygame.Rect:
        return pygame.Rect(
            self.center[0] - self.size[0] // 2,
            self.center[1] - self.size[1] // 2,
            self.size[0],
            self.size[1],
        )

    def handle_event(self, event: pygame.event.Event, sound_mgr: SoundManager) -> bool:
        rect = self.get_rect()
        if event.type == pygame.MOUSEMOTION:
            was_hovered = self.is_hovered
            self.is_hovered = rect.collidepoint(event.pos)
            if self.is_hovered and not was_hovered:
                self.scale_spring.impulse(0.6)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if rect.collidepoint(event.pos):
                self.is_pressed = True
                self.scale_spring.set_target(0.95)
                return True
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            was_pressed = self.is_pressed
            self.is_pressed = False
            if was_pressed and rect.collidepoint(event.pos):
                self.scale_spring.impulse(1.35)
                sound_mgr.play("click")
                if self.callback:
                    self.callback()
                return True
        return False

    def update(self, dt: float, mouse_pos: Tuple[int, int]):
        self.is_hovered = self.get_rect().collidepoint(mouse_pos)
        if self.is_pressed and self.is_hovered:
            self.scale_spring.set_target(0.96)
        elif self.is_hovered:
            self.scale_spring.set_target(1.07)
        elif self.is_selected:
            self.scale_spring.set_target(1.04)
        else:
            self.scale_spring.set_target(1.0)

        self.scale_spring.update(dt)
        target_hover = 1.0 if (self.is_hovered or self.is_selected) else 0.0
        self.hover_alpha += (target_hover - self.hover_alpha) * min(1.0, dt * 14.0)

    def draw(self, screen: pygame.Surface):
        scale = max(0.5, self.scale_spring.value)
        press_disp = (self.lip_h - 1) if (self.is_pressed and self.is_hovered) else 0
        cx, cy = self.center[0], self.center[1]

        sh_w = max(1, int(self.shadow_surface.get_width() * scale))
        sh_h = max(1, int(self.shadow_surface.get_height() * scale))
        sh_surf = (
            self.shadow_surface
            if abs(scale - 1.0) < 0.005
            else pygame.transform.smoothscale(self.shadow_surface, (sh_w, sh_h))
        )
        screen.blit(sh_surf, sh_surf.get_rect(center=(cx, cy + 5)))

        if self.hover_alpha > 0.02:
            gw = max(1, int(self.glow_surface.get_width() * scale))
            gh = max(1, int(self.glow_surface.get_height() * scale))
            scaled_glow = pygame.transform.smoothscale(self.glow_surface, (gw, gh))
            scaled_glow.set_alpha(int(255 * self.hover_alpha))
            screen.blit(scaled_glow, scaled_glow.get_rect(center=(cx, cy)))

        bw, bh = self.face_surface.get_size()
        sw, sh = max(1, int(bw * scale)), max(1, int(bh * scale))
        if abs(scale - 1.0) < 0.005:
            lip_s = self.lip_surface
            face_s = self.face_surface
        else:
            lip_s = pygame.transform.smoothscale(self.lip_surface, (sw, sh))
            face_s = pygame.transform.smoothscale(self.face_surface, (sw, sh))

        screen.blit(lip_s, lip_s.get_rect(center=(cx, cy)))
        screen.blit(face_s, face_s.get_rect(center=(cx, cy + press_disp)))


class ShockwaveRing:
    def __init__(self, x: float, y: float, color: Tuple[int, int, int], max_radius: float = 120.0):
        self.x = x
        self.y = y
        self.color = color
        self.radius = 10.0
        self.max_radius = max_radius
        self.lifetime = 0.42
        self.max_lifetime = 0.42

    def update(self, dt: float) -> bool:
        self.lifetime -= dt
        progress = 1.0 - max(0.0, self.lifetime / self.max_lifetime)
        self.radius = lerp(10.0, self.max_radius, 1.0 - pow(1.0 - progress, 3))
        return self.lifetime > 0

    def draw(self, screen: pygame.Surface):
        ratio = max(0.0, self.lifetime / self.max_lifetime)
        width = max(1, int(6 * ratio))
        r = int(self.radius)
        if r <= width:
            return
        ring_surf = pygame.Surface((r * 2 + 8, r * 2 + 8), pygame.SRCALPHA)
        alpha = int(225 * (ratio ** 0.8))
        pygame.draw.circle(ring_surf, (*self.color, alpha), (r + 4, r + 4), r, width=width)
        screen.blit(ring_surf, ring_surf.get_rect(center=(int(self.x), int(self.y))))


class Particle:
    def __init__(
        self,
        x: float,
        y: float,
        vx: float,
        vy: float,
        color: Tuple[int, int, int],
        size: float,
        lifetime: float,
        gravity: float = 320.0,
        shape: str = "star",
        additive: bool = False,
    ):
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.color = color
        self.size = size
        self.lifetime = lifetime
        self.max_lifetime = lifetime
        self.gravity = gravity
        self.shape = shape
        self.additive = additive
        self.angle = random.uniform(0, math.tau)
        self.spin = random.uniform(-7.0, 7.0)

    def update(self, dt: float) -> bool:
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.vy += self.gravity * dt
        self.vx *= max(0.0, 1.0 - 0.9 * dt)
        self.angle += self.spin * dt
        self.lifetime -= dt
        return self.lifetime > 0

    def draw(self, screen: pygame.Surface, glow_cache: pygame.Surface):
        ratio = max(0.0, self.lifetime / self.max_lifetime)
        cur_size = max(1.0, self.size * ratio)

        if self.additive:
            gs = max(4, int(cur_size * 3.6))
            tinted = pygame.transform.smoothscale(glow_cache, (gs, gs))
            tinted.fill((*self.color, int(215 * ratio)), special_flags=pygame.BLEND_RGBA_MULT)
            screen.blit(tinted, tinted.get_rect(center=(int(self.x), int(self.y))), special_flags=pygame.BLEND_RGBA_ADD)

        if self.shape == "droplet":
            vel_ang = math.atan2(self.vy, self.vx)
            cos_a, sin_a = math.cos(vel_ang), math.sin(vel_ang)
            r = cur_size
            tip = (self.x - cos_a * r * 2.1, self.y - sin_a * r * 2.1)
            side1 = (self.x - sin_a * r * 0.85, self.y + cos_a * r * 0.85)
            side2 = (self.x + sin_a * r * 0.85, self.y - cos_a * r * 0.85)
            draw_aa_polygon(screen, self.color, [tip, side1, side2])
            draw_aa_circle(screen, self.color, (self.x, self.y), r * 0.85)
            draw_aa_circle(screen, (255, 255, 255), (self.x - r * 0.25, self.y - r * 0.25), max(1, r * 0.3))

        elif self.shape == "ribbon":
            w = cur_size * 1.6
            h = cur_size * 0.75 * math.sin(self.angle * 2.5)
            cos_a, sin_a = math.cos(self.angle), math.sin(self.angle)
            pts = []
            for dx, dy in [(-w, -h), (w, -h), (w, h), (-w, h)]:
                rx = self.x + dx * cos_a - dy * sin_a
                ry = self.y + dx * sin_a + dy * cos_a
                pts.append((rx, ry))
            draw_aa_polygon(screen, self.color, pts)

        elif self.shape == "circle":
            draw_aa_circle(screen, self.color, (self.x, self.y), cur_size)

        else:
            pts = []
            for i in range(8):
                r = cur_size * 1.45 if i % 2 == 0 else cur_size * 0.42
                ang = self.angle + i * (math.pi / 4.0)
                pts.append((self.x + math.cos(ang) * r, self.y + math.sin(ang) * r))
            draw_aa_polygon(screen, self.color, pts)


class FloatingPopup:
    def __init__(
        self,
        x: float,
        y: float,
        text: str,
        font: pygame.font.Font,
        top_col: Tuple[int, int, int],
        bot_col: Tuple[int, int, int],
    ):
        self.x = x
        self.y = y
        self.lifetime = 1.2
        self.max_lifetime = 1.2
        self.scale_spring = Spring(0.2, stiffness=340.0, damping=15.0)
        self.scale_spring.set_target(1.0)
        self.scale_spring.impulse(2.5)
        self.surf = render_arcade_text(font, text, top_col, bot_col, (45, 18, 6), 3, 3)

    def update(self, dt: float) -> bool:
        self.y -= 44.0 * dt
        self.scale_spring.update(dt)
        self.lifetime -= dt
        return self.lifetime > 0

    def draw(self, screen: pygame.Surface):
        ratio = max(0.0, self.lifetime / self.max_lifetime)
        alpha = int(255 * min(1.0, ratio * 2.4))
        scale = max(0.1, self.scale_spring.value)
        w = max(1, int(self.surf.get_width() * scale))
        h = max(1, int(self.surf.get_height() * scale))
        scaled = pygame.transform.smoothscale(self.surf, (w, h))
        scaled.set_alpha(alpha)
        screen.blit(scaled, scaled.get_rect(center=(int(self.x), int(self.y))))


class ParticleSystem:
    def __init__(self):
        self.particles: List[Particle] = []
        self.shockwaves: List[ShockwaveRing] = []
        self.popups: List[FloatingPopup] = []
        self.glow_cache = self._build_glow_cache()

    @staticmethod
    def _build_glow_cache() -> pygame.Surface:
        size = 64
        surf = pygame.Surface((size, size), pygame.SRCALPHA)
        cx, cy = size // 2, size // 2
        for r in range(size // 2, 1, -2):
            t = 1.0 - (r / float(size // 2))
            a = int(255 * (t ** 2.1))
            draw_aa_circle(surf, (255, 255, 255, a), (cx, cy), r)
        return surf

    def clear(self):
        self.particles.clear()
        self.shockwaves.clear()
        self.popups.clear()

    def emit_match_burst(self, center: Tuple[float, float], base_color: Tuple[int, int, int], scale: float = 1.0):
        cx, cy = center
        self.shockwaves.append(ShockwaveRing(cx, cy, PALETTE["gold_light"], max_radius=115.0 * scale))
        self.shockwaves.append(ShockwaveRing(cx, cy, base_color, max_radius=85.0 * scale))

        for _ in range(14):
            angle = random.uniform(0, math.tau)
            speed = random.uniform(80.0, 260.0) * scale
            vx = math.cos(angle) * speed
            vy = math.sin(angle) * speed - random.uniform(35.0, 95.0)
            size = random.uniform(4.5, 8.5) * max(0.65, scale)
            self.particles.append(
                Particle(
                    cx, cy, vx, vy, base_color, size, random.uniform(0.45, 0.85),
                    gravity=410.0, shape="droplet", additive=False
                )
            )

        sparkle_cols = [base_color, PALETTE["gold_light"], PALETTE["gold_mid"], (255, 255, 255)]
        for _ in range(18):
            angle = random.uniform(0, math.tau)
            speed = random.uniform(50.0, 220.0) * scale
            vx = math.cos(angle) * speed
            vy = math.sin(angle) * speed - random.uniform(20.0, 70.0)
            col = random.choice(sparkle_cols)
            self.particles.append(
                Particle(
                    cx, cy, vx, vy, col, random.uniform(5.0, 9.5) * max(0.65, scale),
                    random.uniform(0.5, 0.95), gravity=210.0, shape="star", additive=True
                )
            )

    def emit_trail_sparkle(
        self, x: float, y: float, color: Tuple[int, int, int] = (255, 235, 130)
    ):
        vx = random.uniform(-28.0, 28.0)
        vy = random.uniform(-35.0, 10.0)
        self.particles.append(
            Particle(
                x, y, vx, vy, color, random.uniform(3.2, 6.0),
                random.uniform(0.25, 0.45), gravity=40.0, shape="star", additive=True
            )
        )

    def emit_confetti_rain(self):
        confetti_cols = [
            (255, 65, 90), (255, 210, 45), (65, 225, 95),
            (65, 175, 255), (255, 135, 35), (225, 85, 255),
        ]
        for _ in range(3):
            x = random.uniform(30, SCREEN_WIDTH - 30)
            y = random.uniform(-25, -5)
            vx = random.uniform(-55.0, 55.0)
            vy = random.uniform(95.0, 195.0)
            col = random.choice(confetti_cols)
            self.particles.append(
                Particle(
                    x, y, vx, vy, col, random.uniform(6.5, 10.5),
                    4.2, gravity=38.0, shape="ribbon", additive=False
                )
            )

    def add_popup(
        self,
        x: float,
        y: float,
        text: str,
        font: pygame.font.Font,
        top_col: Tuple[int, int, int],
        bot_col: Tuple[int, int, int],
    ):
        self.popups.append(FloatingPopup(x, y, text, font, top_col, bot_col))

    def update(self, dt: float):
        self.shockwaves = [sw for sw in self.shockwaves if sw.update(dt)]
        self.particles = [p for p in self.particles if p.update(dt)]
        self.popups = [pop for pop in self.popups if pop.update(dt)]

    def draw(self, screen: pygame.Surface):
        for sw in self.shockwaves:
            sw.draw(screen)
        for p in self.particles:
            p.draw(screen, self.glow_cache)
        for pop in self.popups:
            pop.draw(screen)


class AnimatedBackground:
    def __init__(self, width: int, height: int):
        self.width = width
        self.height = height
        self.time = 0.0
        self.parallax_x = 0.0
        self.parallax_y = 0.0

        self.sky_layer = self._build_sky_layer()
        self.hill_layers = self._build_parallax_hill_layers()
        self.god_ray_beams = self._build_god_rays()
        self.clouds = self._init_clouds()
        self.petals = self._init_petals()
        self.light_motes = self._init_light_motes()
        self.leaf_sprites = self._build_leaf_sprites()

    def _build_sky_layer(self) -> pygame.Surface:
        surf = create_linear_gradient_rect(
            self.width,
            self.height,
            [
                (0.0, PALETTE["sky_zenith"]),
                (0.55, PALETTE["sky_horizon"]),
                (0.82, PALETTE["sky_haze"]),
                (1.0, PALETTE["sky_haze"]),
            ],
        )
        sun_pos = (145, 112)
        glow_surf = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        for radius, alpha in [(220, 16), (165, 28), (118, 48), (82, 85), (56, 230)]:
            draw_aa_circle(glow_surf, (*PALETTE["sun_glow"], alpha), sun_pos, radius)
        draw_aa_circle(glow_surf, PALETTE["sun_core"], sun_pos, 44)
        surf.blit(glow_surf, (0, 0))
        return surf

    def _build_parallax_hill_layers(self) -> List[Dict]:
        pad = 48
        W = self.width + pad * 2
        H = self.height + pad * 2

        far_surf = pygame.Surface((W, H), pygame.SRCALPHA)
        self._draw_shaded_hill(
            far_surf, W, H, base_y=495, amp1=42, amp2=24, phase=0.0,
            top_col=PALETTE["hill_far_top"], bot_col=PALETTE["hill_far_bot"],
        )
        for tx, ty, sc in [(165, 475, 0.78), (350, 455, 0.88), (780, 470, 0.82), (945, 460, 0.92)]:
            self._draw_volumetric_tree(far_surf, tx + pad, ty + pad, sc, far=True)

        mid_surf = pygame.Surface((W, H), pygame.SRCALPHA)
        self._draw_shaded_hill(
            mid_surf, W, H, base_y=568, amp1=38, amp2=20, phase=1.8,
            top_col=PALETTE["hill_mid_top"], bot_col=PALETTE["hill_mid_bot"],
        )
        for tx, ty, sc in [(95, 550, 1.12), (265, 572, 0.98), (855, 545, 1.15), (985, 565, 1.05)]:
            self._draw_volumetric_tree(mid_surf, tx + pad, ty + pad, sc, far=False)

        near_surf = pygame.Surface((W, H), pygame.SRCALPHA)
        self._draw_shaded_hill(
            near_surf, W, H, base_y=668, amp1=28, amp2=12, phase=3.5,
            top_col=PALETTE["hill_near_top"], bot_col=PALETTE["hill_near_bot"],
        )

        return [
            {"surf": far_surf, "factor": 0.25, "pad": pad},
            {"surf": mid_surf, "factor": 0.52, "pad": pad},
            {"surf": near_surf, "factor": 0.85, "pad": pad},
        ]

    @staticmethod
    def _draw_shaded_hill(
        surf: pygame.Surface,
        W: int,
        H: int,
        base_y: int,
        amp1: float,
        amp2: float,
        phase: float,
        top_col: Tuple[int, int, int],
        bot_col: Tuple[int, int, int],
    ):
        pts = [(0, H)]
        crest_pts = []
        for x in range(0, W + 12, 12):
            y = base_y + math.sin(x * 0.0055 + phase) * amp1 + math.cos(x * 0.0032 + phase) * amp2
            pts.append((x, y))
            crest_pts.append((x, y))
        pts.append((W, H))

        grad = create_linear_gradient_rect(W, H, [(0.0, top_col), (0.55, top_col), (1.0, bot_col)])
        mask = pygame.Surface((W, H), pygame.SRCALPHA)
        draw_aa_polygon(mask, (255, 255, 255, 255), pts)
        grad.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        surf.blit(grad, (0, 0))

        if len(crest_pts) > 2:
            rim_col = (
                min(255, top_col[0] + 45),
                min(255, top_col[1] + 45),
                min(255, top_col[2] + 35),
                140,
            )
            pygame.draw.lines(surf, rim_col, False, crest_pts, 4)

    @staticmethod
    def _draw_volumetric_tree(surf: pygame.Surface, x: int, y: int, scale: float, far: bool):
        trunk_w = int(16 * scale)
        trunk_h = int(52 * scale)
        pygame.draw.rect(surf, (78, 42, 20), (x - trunk_w // 2, y, trunk_w, trunk_h), border_radius=4)
        pygame.draw.rect(surf, (125, 72, 36), (x - trunk_w // 2, y, max(2, trunk_w // 2), trunk_h), border_radius=3)

        c_shadow = (38, 118, 56) if far else (22, 88, 38)
        c_mid = (68, 165, 82) if far else (48, 148, 62)
        c_hi = (128, 222, 110) if far else (112, 212, 92)

        puffs = [
            (x - int(22 * scale), y - int(4 * scale), int(26 * scale)),
            (x + int(22 * scale), y - int(4 * scale), int(26 * scale)),
            (x, y - int(22 * scale), int(34 * scale)),
        ]
        for px, py, pr in puffs:
            draw_radial_sphere(surf, (px, py), pr, c_shadow, c_mid, c_hi, light_offset=(-0.35, -0.35))

        f_col = (255, 75, 65) if (x % 2 == 0) else (255, 175, 35)
        for fx, fy in [(-15, -10), (14, -12), (-2, -28), (7, -2)]:
            px, py = x + int(fx * scale), y + int(fy * scale)
            draw_aa_circle(surf, f_col, (px, py), max(3, int(4.5 * scale)))
            draw_aa_circle(surf, (255, 245, 200), (px - 1, py - 1), max(1, int(2 * scale)))

    def _build_god_rays(self) -> List[Dict]:
        beams = []
        angles = [18, 31, 44, 58, 72]
        for idx, deg in enumerate(angles):
            beam_surf = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
            rad = math.radians(deg)
            spread = math.radians(5.5 + (idx % 2) * 2.5)
            ox, oy = 145, 112
            length = 1150
            p1 = (ox, oy)
            p2 = (ox + math.cos(rad - spread) * length, oy + math.sin(rad - spread) * length)
            p3 = (ox + math.cos(rad + spread) * length, oy + math.sin(rad + spread) * length)
            draw_aa_polygon(beam_surf, (255, 240, 175, 18), [p1, p2, p3])

            p2_in = (ox + math.cos(rad - spread * 0.45) * length, oy + math.sin(rad - spread * 0.45) * length)
            p3_in = (ox + math.cos(rad + spread * 0.45) * length, oy + math.sin(rad + spread * 0.45) * length)
            draw_aa_polygon(beam_surf, (255, 250, 210, 14), [p1, p2_in, p3_in])
            beams.append({"surf": beam_surf, "phase": idx * 1.3, "speed": 0.9 + idx * 0.18})
        return beams

    def _init_clouds(self) -> List[Dict]:
        clouds = []
        for i in range(6):
            scale = random.uniform(0.75, 1.25)
            cw, ch = int(190 * scale), int(86 * scale)
            csurf = pygame.Surface((cw, ch), pygame.SRCALPHA)
            puffs = [
                (0.28, 0.58, 22),
                (0.48, 0.46, 30),
                (0.68, 0.56, 23),
                (0.38, 0.62, 20),
                (0.58, 0.62, 20),
            ]
            for px, py, pr in puffs:
                draw_radial_sphere(
                    csurf,
                    (cw * px, ch * py),
                    pr * scale,
                    shadow_col=(198, 224, 245),
                    mid_col=(238, 248, 255),
                    highlight_col=(255, 255, 255),
                    light_offset=(-0.25, -0.35),
                )
            clouds.append({
                "x": i * (self.width / 5.0) + random.uniform(-40, 40),
                "y": random.uniform(42, 245),
                "speed": random.uniform(11.0, 24.0),
                "depth": random.uniform(0.15, 0.35),
                "surf": csurf,
            })
        return clouds

    def _init_petals(self) -> List[Dict]:
        petals = []
        colors = [(255, 205, 222), (255, 238, 195), (255, 182, 205), (242, 255, 215)]
        for _ in range(24):
            petals.append({
                "x": random.uniform(0, self.width),
                "y": random.uniform(0, self.height),
                "vx": random.uniform(15.0, 34.0),
                "vy": random.uniform(16.0, 35.0),
                "phase": random.uniform(0, math.tau),
                "size": random.uniform(4.5, 7.5),
                "color": random.choice(colors),
            })
        return petals

    def _init_light_motes(self) -> List[Dict]:
        motes = []
        for _ in range(28):
            motes.append({
                "x": random.uniform(0, self.width),
                "y": random.uniform(90, self.height - 30),
                "vy": random.uniform(-20.0, -8.0),
                "phase": random.uniform(0, math.tau),
                "radius": random.randint(2, 5),
            })
        return motes

    def _build_leaf_sprites(self) -> List[Dict]:
        base_leaf = pygame.Surface((200, 110), pygame.SRCALPHA)
        AssetGenerator._draw_ssaa_leaf(base_leaf, (10, 55), (186, 55), 38)

        configs = [
            {"anchor": (-22, 35), "base_angle": -22, "amp": 5.5, "speed": 1.7, "phase": 0.0, "scale": 1.0},
            {"anchor": (-32, 120), "base_angle": -8, "amp": 4.5, "speed": 1.4, "phase": 1.2, "scale": 0.85},
            {"anchor": (-28, 680), "base_angle": 24, "amp": 5.0, "speed": 1.6, "phase": 2.1, "scale": 0.95},
            {"anchor": (self.width + 22, 40), "base_angle": 202, "amp": 5.5, "speed": 1.65, "phase": 0.7, "scale": 1.0},
            {"anchor": (self.width + 32, 125), "base_angle": 188, "amp": 4.5, "speed": 1.35, "phase": 2.4, "scale": 0.85},
            {"anchor": (self.width + 28, 685), "base_angle": 156, "amp": 5.0, "speed": 1.55, "phase": 1.5, "scale": 0.95},
        ]
        for cfg in configs:
            s = cfg["scale"]
            cfg["surf"] = pygame.transform.smoothscale(base_leaf, (int(200 * s), int(110 * s)))
        return configs

    def update(self, dt: float, mouse_pos: Tuple[int, int]):
        self.time += dt

        target_px = ((mouse_pos[0] - self.width * 0.5) / (self.width * 0.5)) * -26.0
        target_py = ((mouse_pos[1] - self.height * 0.5) / (self.height * 0.5)) * -14.0
        self.parallax_x += (target_px - self.parallax_x) * min(1.0, dt * 5.0)
        self.parallax_y += (target_py - self.parallax_y) * min(1.0, dt * 5.0)

        for c in self.clouds:
            c["x"] += c["speed"] * dt
            if c["x"] > self.width + 140:
                c["x"] = -c["surf"].get_width() - 60
                c["y"] = random.uniform(42, 240)

        for p in self.petals:
            p["x"] += (p["vx"] + math.sin(self.time * 1.8 + p["phase"]) * 20.0) * dt
            p["y"] += p["vy"] * dt
            if p["y"] > self.height + 20:
                p["y"] = -15
                p["x"] = random.uniform(-40, self.width - 60)
            if p["x"] > self.width + 20:
                p["x"] = -15

        for m in self.light_motes:
            m["y"] += m["vy"] * dt
            m["x"] += math.sin(self.time * 1.4 + m["phase"]) * 14.0 * dt
            if m["y"] < 65:
                m["y"] = self.height + 10
                m["x"] = random.uniform(0, self.width)

    def draw_backdrop(self, screen: pygame.Surface):
        screen.blit(self.sky_layer, (0, 0))

        for c in self.clouds:
            cx = int(c["x"] + self.parallax_x * c["depth"])
            cy = int(c["y"] + self.parallax_y * c["depth"])
            screen.blit(c["surf"], (cx, cy))

        for beam in self.god_ray_beams:
            pulse = 0.55 + 0.45 * math.sin(self.time * beam["speed"] + beam["phase"])
            beam["surf"].set_alpha(int(215 * pulse))
            screen.blit(beam["surf"], (0, 0), special_flags=pygame.BLEND_RGBA_ADD)

        for layer in self.hill_layers:
            pad = layer["pad"]
            ox = int(-pad + self.parallax_x * layer["factor"])
            oy = int(-pad + self.parallax_y * layer["factor"])
            screen.blit(layer["surf"], (ox, oy))

        mote_layer = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        for m in self.light_motes:
            pulse = 0.55 + 0.45 * math.sin(self.time * 2.6 + m["phase"])
            alpha = int(145 * pulse)
            mx = m["x"] + self.parallax_x * 0.6
            my = m["y"] + self.parallax_y * 0.6
            draw_aa_circle(mote_layer, (255, 245, 175, alpha), (mx, my), m["radius"] + 3)
            draw_aa_circle(mote_layer, (255, 255, 240, min(255, alpha + 60)), (mx, my), m["radius"])
        screen.blit(mote_layer, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)

        for p in self.petals:
            ang = self.time * 2.3 + p["phase"]
            rx = p["size"]
            ry = max(2.0, p["size"] * 0.6 * abs(math.cos(ang)))
            px = p["x"] + self.parallax_x * 0.75
            py = p["y"] + self.parallax_y * 0.75
            pts = [(px - rx, py), (px, py - ry), (px + rx, py), (px, py + ry)]
            draw_aa_polygon(screen, p["color"], pts)

    def draw_foreground_vines(self, screen: pygame.Surface):
        for leaf in self.leaf_sprites:
            sway_angle = leaf["base_angle"] + math.sin(self.time * leaf["speed"] + leaf["phase"]) * leaf["amp"]
            rotated = pygame.transform.rotate(leaf["surf"], sway_angle)
            ax = leaf["anchor"][0] + self.parallax_x * 1.15
            ay = leaf["anchor"][1] + self.parallax_y * 1.15
            screen.blit(rotated, rotated.get_rect(center=(int(ax), int(ay))))


class Card:
    def __init__(
        self,
        card_key: str,
        grid_pos: Tuple[int, int],
        target_center: Tuple[int, int],
        card_size: Tuple[int, int],
        front_surf: pygame.Surface,
        back_surf: pygame.Surface,
        shadow_surf: pygame.Surface,
        entrance_delay: float,
    ):
        self.card_key = card_key
        self.base_fruit = card_key.split(":")[0] if ":" in card_key else card_key
        self.grid_pos = grid_pos
        self.target_center = target_center
        self.card_w, self.card_h = card_size
        self.front_surf = front_surf
        self.back_surf = back_surf
        self.shadow_surf = shadow_surf

        self.flip_spring = Spring(0.0, stiffness=215.0, damping=19.0)
        self.scale_spring = Spring(1.0, stiffness=310.0, damping=16.0)
        self.deal_y_spring = Spring(-180.0, stiffness=190.0, damping=15.5)
        self.deal_y_spring.set_target(float(target_center[1]))

        self.is_matched = False
        self.entrance_delay = max(0.0, float(entrance_delay))
        self.has_entered = self.entrance_delay <= 0.0

        self.tilt_x = 0.0
        self.tilt_y = 0.0
        self.is_hovered = False

        self.shake_timer = 0.0
        self.shake_offset_x = 0.0
        self.hint_timer = 0.0
        self.shine_timer = random.uniform(0.0, 6.0)

    @property
    def is_ready(self) -> bool:
        return (
            self.has_entered
            and abs(self.deal_y_spring.value - self.target_center[1]) < 24.0
            and not self.is_matched
            and self.flip_spring.target == 0.0
            and self.flip_spring.value < 0.08
        )

    def get_rect(self) -> pygame.Rect:
        return pygame.Rect(
            self.target_center[0] - self.card_w // 2,
            int(self.deal_y_spring.value) - self.card_h // 2,
            self.card_w,
            self.card_h,
        )

    def flip_face_up(self):
        self.flip_spring.set_target(1.0)
        self.scale_spring.impulse(1.1)

    def flip_face_down(self):
        self.flip_spring.set_target(0.0)
        self.scale_spring.impulse(0.6)

    def set_matched(self):
        self.is_matched = True
        self.hint_timer = 0.0
        self.flip_spring.set_target(1.0)
        self.scale_spring.impulse(2.6)
        self.shine_timer = 0.0

    def trigger_mismatch_shake(self):
        self.shake_timer = 0.46
        self.scale_spring.impulse(-0.9)

    def trigger_hint_aura(self, duration: float = 1.35):
        self.hint_timer = duration
        self.scale_spring.impulse(1.8)

    def update(
        self,
        dt: float,
        mouse_pos: Tuple[int, int],
        can_hover: bool,
        particles: ParticleSystem,
        sound_mgr: SoundManager,
        allow_deal_sfx: bool = True,
    ):
        if not self.has_entered:
            self.entrance_delay -= dt
            if self.entrance_delay <= 0.0:
                self.has_entered = True
                if allow_deal_sfx:
                    sound_mgr.play("deal")
            else:
                return

        self.deal_y_spring.update(dt)
        if allow_deal_sfx and abs(self.deal_y_spring.velocity) > 220.0 and random.random() < 0.22:
            particles.emit_trail_sparkle(
                self.target_center[0] + random.uniform(-self.card_w * 0.22, self.card_w * 0.22),
                self.deal_y_spring.value,
                PALETTE["gold_light"],
            )

        self.flip_spring.update(dt)
        rect = self.get_rect()
        self.is_hovered = can_hover and self.is_ready and rect.collidepoint(mouse_pos)
        self.scale_spring.set_target(1.075 if self.is_hovered else 1.0)
        self.scale_spring.update(dt)

        if self.is_hovered:
            rel_x = (mouse_pos[0] - rect.centerx) / max(1.0, self.card_w * 0.5)
            rel_y = (mouse_pos[1] - rect.centery) / max(1.0, self.card_h * 0.5)
            target_tx = clamp(rel_x, -1.0, 1.0)
            target_ty = clamp(rel_y, -1.0, 1.0)
        else:
            target_tx, target_ty = 0.0, 0.0

        self.tilt_x += (target_tx - self.tilt_x) * min(1.0, dt * 14.0)
        self.tilt_y += (target_ty - self.tilt_y) * min(1.0, dt * 14.0)

        if self.shake_timer > 0.0:
            self.shake_timer = max(0.0, self.shake_timer - dt)
            damp = self.shake_timer / 0.46
            self.shake_offset_x = math.sin(self.shake_timer * 62.0) * 10.0 * damp
        else:
            self.shake_offset_x = 0.0

        if self.hint_timer > 0.0:
            self.hint_timer = max(0.0, self.hint_timer - dt)
            if random.random() < 0.35:
                particles.emit_trail_sparkle(
                    self.target_center[0] + random.uniform(-self.card_w * 0.4, self.card_w * 0.4),
                    self.deal_y_spring.value + random.uniform(-self.card_h * 0.4, self.card_h * 0.4),
                    PALETTE["jade_glow"],
                )

        self.shine_timer = (self.shine_timer + dt) % 5.5

    def draw(self, screen: pygame.Surface):
        if not self.has_entered:
            return

        cx = int(self.target_center[0] + self.shake_offset_x + self.tilt_x * 4.0)
        cy = int(self.deal_y_spring.value + self.tilt_y * 4.0)

        flip_val = clamp(self.flip_spring.value, -0.15, 1.15)
        cos_flip = math.cos(clamp(flip_val, 0.0, 1.0) * math.pi)
        sin_flip = math.sin(clamp(flip_val, 0.0, 1.0) * math.pi)

        pinch_x = abs(cos_flip)
        perspective_boost_y = 1.0 + 0.13 * sin_flip
        total_scale = max(0.5, self.scale_spring.value)

        tilt_squeeze_x = 1.0 - abs(self.tilt_x) * 0.04
        tilt_squeeze_y = 1.0 - abs(self.tilt_y) * 0.04

        scaled_w = max(3, int(self.card_w * pinch_x * total_scale * tilt_squeeze_x))
        scaled_h = max(3, int(self.card_h * perspective_boost_y * total_scale * tilt_squeeze_y))

        size_ratio = self.card_w / 112.0
        lift = int((5 + 10 * sin_flip + max(0.0, total_scale - 1.0) * 40) * size_ratio)

        sh_w = max(4, int(self.shadow_surf.get_width() * pinch_x * total_scale))
        sh_h = max(4, int(self.shadow_surf.get_height() * total_scale))
        scaled_sh = pygame.transform.smoothscale(self.shadow_surf, (sh_w, sh_h))
        screen.blit(scaled_sh, scaled_sh.get_rect(center=(cx - int(self.tilt_x * 4), cy + lift)))

        edge_rad = max(3, int(16 * size_ratio * pinch_x * total_scale))

        if self.hint_timer > 0.0:
            pulse = 0.55 + 0.45 * math.sin(self.hint_timer * 18.0)
            pad_a = max(8, int(16 * size_ratio))
            aura = pygame.Surface((scaled_w + pad_a * 2, scaled_h + pad_a * 2), pygame.SRCALPHA)
            pygame.draw.rect(
                aura,
                (*PALETTE["jade_glow"], int(195 * pulse)),
                aura.get_rect(),
                width=max(2, int(4 * size_ratio)),
                border_radius=edge_rad + 5,
            )
            pygame.draw.rect(
                aura,
                (*PALETTE["gold_shine"], int(230 * pulse)),
                aura.get_rect().inflate(-4, -4),
                width=max(2, int(3 * size_ratio)),
                border_radius=edge_rad + 3,
            )
            screen.blit(aura, aura.get_rect(center=(cx, cy)))

        elif self.is_matched:
            pad_a = max(6, int(12 * size_ratio))
            aura_surf = pygame.Surface((scaled_w + pad_a, scaled_h + pad_a), pygame.SRCALPHA)
            pygame.draw.rect(
                aura_surf,
                (*PALETTE["gold_light"], 120),
                aura_surf.get_rect(),
                width=max(2, int(3 * size_ratio)),
                border_radius=edge_rad + 2,
            )
            screen.blit(aura_surf, aura_surf.get_rect(center=(cx, cy)))

        side_thickness = int(max(1, 5 * size_ratio) * sin_flip * (1 if cos_flip >= 0 else -1) - self.tilt_x * 3)
        bot_thickness = max(2, int(5 * size_ratio * total_scale - self.tilt_y * 2))
        edge_rect = pygame.Rect(
            cx - scaled_w // 2 + side_thickness,
            cy - scaled_h // 2 + bot_thickness,
            scaled_w,
            scaled_h,
        )
        pygame.draw.rect(screen, PALETTE["gold_shadow"], edge_rect, border_radius=edge_rad)
        pygame.draw.rect(screen, PALETTE["gold_mid"], edge_rect.inflate(-2, -2), width=max(1, int(2 * size_ratio)), border_radius=edge_rad)

        active_surf = self.front_surf if flip_val >= 0.5 else self.back_surf
        if scaled_w == self.card_w and scaled_h == self.card_h:
            card_img = active_surf.copy()
        else:
            card_img = pygame.transform.smoothscale(active_surf, (scaled_w, scaled_h))

        if abs(self.tilt_x) > 0.02 or abs(self.tilt_y) > 0.02:
            sheen_surf = pygame.Surface((scaled_w, scaled_h), pygame.SRCALPHA)
            sx = int(scaled_w * (0.5 - self.tilt_x * 0.38))
            sy = int(scaled_h * (0.5 - self.tilt_y * 0.38))
            draw_aa_circle(sheen_surf, (255, 255, 255, 42), (sx, sy), int(max(scaled_w, scaled_h) * 0.46))
            card_img.blit(sheen_surf, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)

        if self.shine_timer < 0.65 and pinch_x > 0.45 and self.card_w >= 64:
            sweep_t = self.shine_timer / 0.65
            sweep_surf = pygame.Surface((scaled_w, scaled_h), pygame.SRCALPHA)
            band_x = lerp(-scaled_h, scaled_w + scaled_h, sweep_t)
            pts = [
                (band_x, 0),
                (band_x + 20, 0),
                (band_x + 20 - scaled_h * 0.65, scaled_h),
                (band_x - scaled_h * 0.65, scaled_h),
            ]
            draw_aa_polygon(sweep_surf, (255, 250, 215, 65), pts)
            card_img.blit(sweep_surf, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)

        if pinch_x < 0.38:
            darkness = int((1.0 - pinch_x / 0.38) * 75)
            shade = pygame.Surface((scaled_w, scaled_h), pygame.SRCALPHA)
            pygame.draw.rect(shade, (12, 24, 16, darkness), shade.get_rect(), border_radius=edge_rad)
            card_img.blit(shade, (0, 0))

        if abs(self.tilt_x) > 0.03 and pinch_x > 0.8 and self.card_w >= 64:
            card_img = pygame.transform.rotozoom(card_img, -self.tilt_x * 2.5, 1.0)

        screen.blit(card_img, card_img.get_rect(center=(cx, cy)))


class FruitMemoryDeluxeGame:
    GRID_OPTIONS = [4, 6, 8, 10]

    def __init__(self):
        pygame.init()
        pygame.display.set_caption(TITLE)
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        self.canvas = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        self.clock = pygame.time.Clock()
        self.running = True

        self.font_title = pygame.font.SysFont("trebuchetms,arialroundedmtbold,verdana", 52, bold=True)
        self.font_subtitle = pygame.font.SysFont("trebuchetms,verdana,arial", 21, bold=True)
        self.font_hud_label = pygame.font.SysFont("trebuchetms,verdana,arial", 13, bold=True)
        self.font_hud_value = pygame.font.SysFont("trebuchetms,verdana,arial", 23, bold=True)
        self.font_button = pygame.font.SysFont("trebuchetms,verdana,arial", 22, bold=True)
        self.font_grid_btn = pygame.font.SysFont("trebuchetms,verdana,arial", 20, bold=True)
        self.font_popup = pygame.font.SysFont("trebuchetms,verdana,arial", 25, bold=True)

        self.sound_mgr = SoundManager()
        self.background = AnimatedBackground(SCREEN_WIDTH, SCREEN_HEIGHT)
        self.particles = ParticleSystem()

        self.master_card_back = AssetGenerator.create_master_card_back()
        self.master_card_fronts: Dict[str, pygame.Surface] = {}
        self.scaled_card_cache: Dict[Tuple[str, int, int], pygame.Surface] = {}
        self.scaled_shadow_cache: Dict[Tuple[int, int], pygame.Surface] = {}
        self.board_frame_cache: Dict[int, Tuple[pygame.Surface, Tuple[int, int]]] = {}

        for ft in BASE_FRUITS[:8]:
            self.master_card_fronts[ft] = AssetGenerator.create_master_card_front(ft)

        self.hud_banner_surf = AssetGenerator.create_wooden_banner(610, 82)
        self.victory_panel_surf = AssetGenerator.create_wooden_banner(540, 445)
        self.menu_plaque_surf = AssetGenerator.create_wooden_banner(650, 150)

        self.star_earned_surf = AssetGenerator.create_star_sprite(36, earned=True)
        self.star_empty_surf = AssetGenerator.create_star_sprite(36, earned=False)

        self.lbl_moves = render_arcade_text(
            self.font_hud_label, "MOVES", PALETTE["gold_shine"], PALETTE["gold_mid"], (45, 18, 6), 2, 1
        )
        self.lbl_time = render_arcade_text(
            self.font_hud_label, "TIME", PALETTE["gold_shine"], PALETTE["gold_mid"], (45, 18, 6), 2, 1
        )
        self.lbl_score = render_arcade_text(
            self.font_hud_label, "SCORE", PALETTE["gold_shine"], PALETTE["gold_mid"], (45, 18, 6), 2, 1
        )
        self.lbl_grid_select = render_arcade_text(
            self.font_hud_label, "SELECT BOARD SIZE", PALETTE["gold_shine"], PALETTE["gold_mid"], (42, 18, 6), 2, 2
        )

        self.menu_showcase_fruits = ["Strawberry", "Pineapple", "Watermelon", "Mango"]
        self.menu_showcase_surfs = [
            self._get_scaled_card_surface(ft, 112, 136) for ft in self.menu_showcase_fruits
        ]
        self.menu_showcase_shadow = self._get_scaled_shadow(112, 136)

        self.state = GameState.MENU
        self.grid_dim = 4
        self.total_pairs = 8

        self.cards: List[Card] = []
        self.selected_cards: List[Card] = []
        self.hint_peek_cards: List[Card] = []
        self.is_checking = False
        self.is_hint_peeking = False
        self.mismatch_timer_start = 0
        self.hint_timer_start = 0

        self.hints_remaining = 3
        self.moves = 0
        self.score = 0
        self.displayed_score = 0.0
        self.combo = 0
        self.fever_meter = 0.0
        self.matched_pairs = 0
        self.elapsed_seconds = 0.0
        self.timer_active = False

        self.board_frame_surf: Optional[pygame.Surface] = None
        self.board_center = (SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 40)

        self.camera_trauma = 0.0
        self.hit_stop_timer = 0.0

        self.iris_radius = float(math.hypot(SCREEN_WIDTH, SCREEN_HEIGHT))
        self.iris_max_radius = self.iris_radius
        self.iris_closing = False
        self.pending_transition_action: Optional[Callable[[], None]] = None
        self.iris_mask = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)

        self.victory_timer = 0.0
        self.victory_panel_spring = Spring(0.0, stiffness=240.0, damping=16.0)
        self.star_springs = [
            Spring(0.0, stiffness=280.0, damping=14.0),
            Spring(0.0, stiffness=280.0, damping=14.0),
            Spring(0.0, stiffness=280.0, damping=14.0),
        ]
        self.earned_stars = 3
        self.stars_triggered = [False, False, False]

        self._init_buttons()

    def _get_scaled_card_surface(self, key: str, w: int, h: int) -> pygame.Surface:
        cache_key = (key, w, h)
        if cache_key in self.scaled_card_cache:
            return self.scaled_card_cache[cache_key]

        if key == "__BACK__":
            master = self.master_card_back
        else:
            if key not in self.master_card_fronts:
                self.master_card_fronts[key] = AssetGenerator.create_master_card_front(key)
            master = self.master_card_fronts[key]

        scaled = pygame.transform.smoothscale(master, (w, h))
        self.scaled_card_cache[cache_key] = scaled
        return scaled

    def _get_scaled_shadow(self, w: int, h: int) -> pygame.Surface:
        key = (w, h)
        if key not in self.scaled_shadow_cache:
            rad = max(5, int(18 * (w / 112.0)))
            blur = max(3, int(6 * (w / 112.0)))
            self.scaled_shadow_cache[key] = create_soft_shadow(w, h, rad, blur_steps=blur, max_alpha=115)
        return self.scaled_shadow_cache[key]

    def _compute_grid_metrics(self, dim: int) -> Tuple[int, int, int, int, int, int]:
        top_margin = 122
        bottom_margin = 24
        side_margin = 56
        avail_w = SCREEN_WIDTH - side_margin * 2
        avail_h = SCREEN_HEIGHT - top_margin - bottom_margin

        if dim <= 4:
            gap_x, gap_y = 20, 16
        elif dim <= 6:
            gap_x, gap_y = 12, 10
        elif dim <= 8:
            gap_x, gap_y = 8, 7
        else:
            gap_x, gap_y = 6, 5

        max_card_h = (avail_h - (dim - 1) * gap_y) // dim
        max_card_w = (avail_w - (dim - 1) * gap_x) // dim

        aspect = 112.0 / 136.0
        card_h = min(136, max_card_h)
        card_w = int(round(card_h * aspect))
        if card_w > max_card_w:
            card_w = max_card_w
            card_h = int(round(card_w / aspect))

        grid_w = dim * card_w + (dim - 1) * gap_x
        grid_h = dim * card_h + (dim - 1) * gap_y
        return card_w, card_h, gap_x, gap_y, grid_w, grid_h

    def _init_buttons(self):
        self.grid_selector_buttons: List[GraphicalButton] = []
        selector_w = 108
        selector_gap = 18
        total_sel_w = len(self.GRID_OPTIONS) * selector_w + (len(self.GRID_OPTIONS) - 1) * selector_gap
        start_sel_x = SCREEN_WIDTH // 2 - total_sel_w // 2 + selector_w // 2

        for idx, dim in enumerate(self.GRID_OPTIONS):
            bx = start_sel_x + idx * (selector_w + selector_gap)
            selected = dim == self.grid_dim
            btn = GraphicalButton(
                center=(bx, 456),
                size=(selector_w, 52),
                text=f"{dim}x{dim}",
                theme="gold_gem" if selected else "teal_gem",
                callback=lambda d=dim: self.select_grid_size(d),
                font=self.font_grid_btn,
                is_selected=selected,
            )
            self.grid_selector_buttons.append(btn)

        self.menu_buttons = [
            GraphicalButton(
                center=(SCREEN_WIDTH // 2, 548),
                size=(260, 68),
                text="PLAY GAME",
                icon_type="play",
                theme="green_gem",
                callback=lambda: self.start_iris_transition(self._setup_new_game),
                font=self.font_button,
            ),
            GraphicalButton(
                center=(SCREEN_WIDTH // 2 - 74, 636),
                size=(116, 56),
                icon_type="sound_on",
                theme="blue_gem",
                callback=self.toggle_sound,
                font=self.font_button,
            ),
            GraphicalButton(
                center=(SCREEN_WIDTH // 2 + 74, 636),
                size=(116, 56),
                icon_type="quit",
                theme="red_gem",
                callback=self.quit_game,
                font=self.font_button,
            ),
        ]

        self.hint_button = GraphicalButton(
            center=(142, 54),
            size=(62, 56),
            icon_type="hint",
            theme="purple_gem",
            callback=self.trigger_hint,
            badge_text="3",
        )

        self.hud_buttons = [
            GraphicalButton(
                center=(68, 54),
                size=(58, 56),
                icon_type="menu",
                theme="wood_plaque",
                callback=lambda: self.start_iris_transition(self._enter_menu_state),
            ),
            self.hint_button,
            GraphicalButton(
                center=(SCREEN_WIDTH - 142, 54),
                size=(58, 56),
                icon_type="restart",
                theme="orange_gem",
                callback=lambda: self.start_iris_transition(self._setup_new_game),
            ),
            GraphicalButton(
                center=(SCREEN_WIDTH - 68, 54),
                size=(58, 56),
                icon_type="sound_on",
                theme="blue_gem",
                callback=self.toggle_sound,
            ),
        ]

        self.victory_buttons = [
            GraphicalButton(
                center=(SCREEN_WIDTH // 2 - 122, 540),
                size=(218, 62),
                text="PLAY AGAIN",
                icon_type="restart",
                theme="green_gem",
                callback=lambda: self.start_iris_transition(self._setup_new_game),
                font=self.font_button,
            ),
            GraphicalButton(
                center=(SCREEN_WIDTH // 2 + 122, 540),
                size=(218, 62),
                text="MAIN MENU",
                icon_type="menu",
                theme="orange_gem",
                callback=lambda: self.start_iris_transition(self._enter_menu_state),
                font=self.font_button,
            ),
        ]

    def select_grid_size(self, dim: int):
        self.grid_dim = dim
        for idx, d in enumerate(self.GRID_OPTIONS):
            is_sel = d == dim
            self.grid_selector_buttons[idx].set_selected(is_sel, "gold_gem" if is_sel else "teal_gem")

    def start_iris_transition(self, action: Callable[[], None]):
        if self.iris_closing:
            return
        self.pending_transition_action = action
        self.iris_closing = True

    def toggle_sound(self):
        enabled = self.sound_mgr.toggle()
        icon = "sound_on" if enabled else "sound_off"
        self.menu_buttons[1].set_icon(icon)
        self.hud_buttons[3].set_icon(icon)

    def quit_game(self):
        self.running = False

    def _enter_menu_state(self):
        self.state = GameState.MENU
        self.particles.clear()

    def _build_deck_keys(self, num_pairs: int) -> List[str]:
        pool: List[str] = []
        for f in BASE_FRUITS:
            pool.append(f)
        for f in BASE_FRUITS:
            pool.append(f"{f}:gold")

        chosen = pool[:num_pairs]
        deck = chosen * 2
        random.shuffle(deck)
        return deck

    def _setup_new_game(self):
        self.state = GameState.PLAYING
        self.particles.clear()
        self.selected_cards.clear()
        self.hint_peek_cards.clear()
        self.is_checking = False
        self.is_hint_peeking = False
        self.mismatch_timer_start = 0
        self.hint_timer_start = 0

        dim = self.grid_dim
        total_cards = dim * dim
        self.total_pairs = total_cards // 2

        self.hints_remaining = 3 if dim <= 4 else (4 if dim <= 6 else (5 if dim <= 8 else 6))
        self.hint_button.set_badge(str(self.hints_remaining))

        self.moves = 0
        self.score = 0
        self.displayed_score = 0.0
        self.combo = 0
        self.fever_meter = 0.0
        self.matched_pairs = 0
        self.elapsed_seconds = 0.0
        self.timer_active = False

        card_w, card_h, gap_x, gap_y, grid_w, grid_h = self._compute_grid_metrics(dim)
        top_area = 118
        avail_h = SCREEN_HEIGHT - top_area - 16
        board_cy = top_area + avail_h // 2
        self.board_center = (SCREEN_WIDTH // 2, board_cy)

        if dim not in self.board_frame_cache:
            frame_surf = AssetGenerator.create_board_frame(
                grid_w, grid_h, dim, dim, card_w, card_h, gap_x, gap_y
            )
            self.board_frame_cache[dim] = (frame_surf, self.board_center)
        self.board_frame_surf, self.board_center = self.board_frame_cache[dim]

        deck = self._build_deck_keys(self.total_pairs)
        back_surf = self._get_scaled_card_surface("__BACK__", card_w, card_h)
        shadow_surf = self._get_scaled_shadow(card_w, card_h)

        start_x = SCREEN_WIDTH // 2 - grid_w // 2 + card_w // 2
        start_y = board_cy - grid_h // 2 + card_h // 2

        total_deal_duration = 0.72
        stagger_step = total_deal_duration / float(max(1, total_cards))

        self.cards.clear()
        for idx in range(total_cards):
            card_key = deck[idx]
            row = idx // dim
            col = idx % dim
            cx = start_x + col * (card_w + gap_x)
            cy = start_y + row * (card_h + gap_y)
            stagger = idx * stagger_step
            front_surf = self._get_scaled_card_surface(card_key, card_w, card_h)

            card = Card(
                card_key=card_key,
                grid_pos=(row, col),
                target_center=(cx, cy),
                card_size=(card_w, card_h),
                front_surf=front_surf,
                back_surf=back_surf,
                shadow_surf=shadow_surf,
                entrance_delay=stagger,
            )
            self.cards.append(card)

    def trigger_hint(self):
        if (
            self.state != GameState.PLAYING
            or self.is_checking
            or self.is_hint_peeking
            or self.hints_remaining <= 0
        ):
            return

        unmatched = [c for c in self.cards if not c.is_matched and c.has_entered]
        if len(unmatched) < 2:
            return

        target_pair: List[Card] = []
        if len(self.selected_cards) == 1:
            first = self.selected_cards[0]
            matches = [c for c in unmatched if c is not first and c.card_key == first.card_key]
            if matches:
                target_pair = [first, matches[0]]
        else:
            by_key: Dict[str, List[Card]] = {}
            for c in unmatched:
                by_key.setdefault(c.card_key, []).append(c)
            valid_groups = [grp for grp in by_key.values() if len(grp) >= 2]
            if valid_groups:
                chosen_grp = random.choice(valid_groups)
                target_pair = chosen_grp[:2]

        if len(target_pair) == 2:
            self.hints_remaining -= 1
            self.hint_button.set_badge(str(self.hints_remaining))
            self.sound_mgr.play("hint")

            self.is_hint_peeking = True
            self.hint_timer_start = pygame.time.get_ticks()
            self.hint_peek_cards.clear()

            for c in target_pair:
                c.trigger_hint_aura(1.4)
                if c not in self.selected_cards:
                    c.flip_face_up()
                    self.hint_peek_cards.append(c)
                self.particles.emit_match_burst(c.target_center, PALETTE["jade_glow"], scale=0.65)

    def trigger_victory(self):
        self.state = GameState.VICTORY
        self.timer_active = False
        self.victory_timer = 0.0
        self.victory_panel_spring.snap(0.1)
        self.victory_panel_spring.set_target(1.0)
        self.victory_panel_spring.impulse(2.0)

        for sp in self.star_springs:
            sp.snap(0.0)
        self.stars_triggered = [False, False, False]

        three_star_limit = int(self.total_pairs * 1.75)
        two_star_limit = int(self.total_pairs * 2.5)
        if self.moves <= three_star_limit:
            self.earned_stars = 3
        elif self.moves <= two_star_limit:
            self.earned_stars = 2
        else:
            self.earned_stars = 1

        self.sound_mgr.play("victory")

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
                return

            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                if self.state in (GameState.PLAYING, GameState.VICTORY):
                    self.start_iris_transition(self._enter_menu_state)
                else:
                    self.running = False
                return

            if self.iris_closing or self.iris_radius < self.iris_max_radius * 0.65:
                continue

            if self.state == GameState.MENU:
                handled = False
                for btn in self.grid_selector_buttons:
                    if btn.handle_event(event, self.sound_mgr):
                        handled = True
                        break
                if not handled:
                    for btn in self.menu_buttons:
                        if btn.handle_event(event, self.sound_mgr):
                            break

            elif self.state == GameState.PLAYING:
                button_handled = False
                for btn in self.hud_buttons:
                    if btn.handle_event(event, self.sound_mgr):
                        button_handled = True
                        break

                if not button_handled and event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    self._handle_card_click(event.pos)

            elif self.state == GameState.VICTORY:
                for btn in self.victory_buttons:
                    if btn.handle_event(event, self.sound_mgr):
                        break

    def _handle_card_click(self, mouse_pos: Tuple[int, int]):
        if self.is_checking or self.is_hint_peeking or len(self.selected_cards) >= 2:
            return

        for card in self.cards:
            if card.is_ready and card.get_rect().collidepoint(mouse_pos):
                if not self.timer_active:
                    self.timer_active = True

                card.flip_face_up()
                self.selected_cards.append(card)
                self.sound_mgr.play("flip")

                if len(self.selected_cards) == 2:
                    self.moves += 1
                    self.is_checking = True
                    self._evaluate_selected_pair()
                break

    def _evaluate_selected_pair(self):
        c1, c2 = self.selected_cards[0], self.selected_cards[1]

        if c1.card_key == c2.card_key:
            c1.set_matched()
            c2.set_matched()
            self.matched_pairs += 1
            self.combo += 1
            self.fever_meter = min(1.0, self.fever_meter + 0.34)

            fever_bonus = 2 if self.fever_meter >= 0.95 else 1
            points_gained = 100 * self.combo * fever_bonus
            self.score += points_gained

            self.camera_trauma = min(1.0, 0.25 + self.combo * 0.12)
            if self.combo >= 2:
                self.hit_stop_timer = 0.035

            theme_col = FRUIT_THEME_COLORS.get(c1.base_fruit, PALETTE["gold_mid"])
            scale_fx = clamp(c1.card_w / 112.0, 0.55, 1.0)
            self.particles.emit_match_burst(c1.target_center, theme_col, scale=scale_fx)
            self.particles.emit_match_burst(c2.target_center, theme_col, scale=scale_fx)

            mid_x = (c1.target_center[0] + c2.target_center[0]) / 2.0
            mid_y = (c1.target_center[1] + c2.target_center[1]) / 2.0
            if self.combo > 1:
                label = f"+{points_gained}  {self.combo}x FEVER!"
                top_c, bot_c = (255, 255, 190), (255, 130, 20)
                self.sound_mgr.play("combo")
            else:
                label = f"+{points_gained}"
                top_c, bot_c = PALETTE["gold_shine"], PALETTE["gold_mid"]
                self.sound_mgr.play("match")

            self.particles.add_popup(mid_x, mid_y - 16, label, self.font_popup, top_c, bot_c)

            self.selected_cards.clear()
            self.is_checking = False

            if self.matched_pairs >= self.total_pairs:
                self.trigger_victory()
        else:
            self.combo = 0
            self.fever_meter = max(0.0, self.fever_meter - 0.35)
            self.camera_trauma = 0.18
            self.mismatch_timer_start = pygame.time.get_ticks()
            c1.trigger_mismatch_shake()
            c2.trigger_mismatch_shake()
            self.sound_mgr.play("mismatch")

    def update(self, dt: float):
        if self.iris_closing:
            self.iris_radius = max(0.0, self.iris_radius - 1950.0 * dt)
            if self.iris_radius <= 2.0:
                if self.pending_transition_action:
                    self.pending_transition_action()
                    self.pending_transition_action = None
                self.iris_closing = False
        elif self.iris_radius < self.iris_max_radius:
            self.iris_radius = min(self.iris_max_radius, self.iris_radius + 1950.0 * dt)

        if self.hit_stop_timer > 0.0:
            self.hit_stop_timer = max(0.0, self.hit_stop_timer - dt)
            return

        mouse_pos = pygame.mouse.get_pos()
        self.background.update(dt, mouse_pos)
        self.particles.update(dt)

        self.camera_trauma = max(0.0, self.camera_trauma - 2.2 * dt)
        self.displayed_score += (self.score - self.displayed_score) * min(1.0, dt * 14.0)

        if self.state == GameState.MENU:
            for btn in self.grid_selector_buttons:
                btn.update(dt, mouse_pos)
            for btn in self.menu_buttons:
                btn.update(dt, mouse_pos)

        elif self.state == GameState.PLAYING:
            for btn in self.hud_buttons:
                btn.update(dt, mouse_pos)

            if self.timer_active:
                self.elapsed_seconds += dt
                self.fever_meter = max(0.0, self.fever_meter - 0.032 * dt)
                if self.fever_meter > 0.65 and random.random() < 0.35:
                    fx = SCREEN_WIDTH // 2 + random.uniform(-110, 110)
                    self.particles.emit_trail_sparkle(fx, 80, (255, 165, 35))

            now = pygame.time.get_ticks()
            if self.is_hint_peeking and now - self.hint_timer_start >= HINT_PEEK_MS:
                for c in self.hint_peek_cards:
                    if not c.is_matched and c not in self.selected_cards:
                        c.flip_face_down()
                self.sound_mgr.play("flip")
                self.hint_peek_cards.clear()
                self.is_hint_peeking = False

            if self.is_checking and len(self.selected_cards) == 2:
                if now - self.mismatch_timer_start >= MISMATCH_DELAY_MS:
                    for card in self.selected_cards:
                        card.flip_face_down()
                    self.sound_mgr.play("flip")
                    self.selected_cards.clear()
                    self.is_checking = False

            can_hover = (
                not self.is_checking
                and not self.is_hint_peeking
                and len(self.selected_cards) < 2
            )
            allow_sfx = self.grid_dim <= 6
            for idx, card in enumerate(self.cards):
                play_sfx = allow_sfx or (idx % 4 == 0)
                card.update(dt, mouse_pos, can_hover, self.particles, self.sound_mgr, allow_deal_sfx=play_sfx)

        elif self.state == GameState.VICTORY:
            for card in self.cards:
                card.update(dt, mouse_pos, False, self.particles, self.sound_mgr, allow_deal_sfx=False)
            for btn in self.victory_buttons:
                btn.update(dt, mouse_pos)

            self.victory_timer += dt
            self.victory_panel_spring.update(dt)

            if random.random() < 0.48:
                self.particles.emit_confetti_rain()

            for i in range(self.earned_stars):
                star_trigger_t = 0.32 + i * 0.30
                if self.victory_timer >= star_trigger_t and not self.stars_triggered[i]:
                    self.stars_triggered[i] = True
                    self.star_springs[i].set_target(1.0)
                    self.star_springs[i].impulse(3.2)
                    self.sound_mgr.play("star")
                    sx = SCREEN_WIDTH // 2 + (i - 1) * 102
                    sy = SCREEN_HEIGHT // 2 - 74 + (0 if i == 1 else 14)
                    self.particles.emit_match_burst((sx, sy), PALETTE["gold_light"])

            for sp in self.star_springs:
                sp.update(dt)

    def draw(self):
        self.background.draw_backdrop(self.canvas)

        if self.state == GameState.MENU:
            self._draw_menu(self.canvas)
            self.background.draw_foreground_vines(self.canvas)
        elif self.state == GameState.PLAYING:
            self._draw_playing(self.canvas)
            self.background.draw_foreground_vines(self.canvas)
        elif self.state == GameState.VICTORY:
            self._draw_playing(self.canvas)
            self.background.draw_foreground_vines(self.canvas)
            self._draw_victory_overlay(self.canvas)

        self.particles.draw(self.canvas)

        if self.camera_trauma > 0.01:
            shake_mag = (self.camera_trauma ** 2) * 14.0
            ox = int(random.uniform(-shake_mag, shake_mag))
            oy = int(random.uniform(-shake_mag, shake_mag))
            self.screen.fill((18, 28, 18))
            self.screen.blit(self.canvas, (ox, oy))
        else:
            self.screen.blit(self.canvas, (0, 0))

        if self.iris_radius < self.iris_max_radius - 2.0:
            self.iris_mask.fill((12, 24, 16, 255))
            r = max(1, int(self.iris_radius))
            pygame.draw.circle(self.iris_mask, (0, 0, 0, 0), (SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2), r)
            pygame.draw.circle(
                self.iris_mask, (*PALETTE["gold_mid"], 220), (SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2), r, width=5
            )
            self.screen.blit(self.iris_mask, (0, 0))

        pygame.display.flip()

    def _draw_menu(self, surf: pygame.Surface):
        t = self.background.time
        bob = math.sin(t * 2.4) * 5.0

        plaque_rect = self.menu_plaque_surf.get_rect(center=(SCREEN_WIDTH // 2, int(132 + bob)))
        surf.blit(self.menu_plaque_surf, plaque_rect)

        title_surf = render_arcade_text(
            self.font_title, "FRUIT MEMORY", (255, 252, 200), (245, 165, 20), (52, 20, 6), 4, 4
        )
        sub_surf = render_arcade_text(
            self.font_subtitle,
            "D E L U X E   S T U D I O   E D I T I O N",
            (255, 255, 255),
            (255, 215, 130),
            (52, 20, 6),
            2,
            2,
        )
        surf.blit(title_surf, title_surf.get_rect(center=(SCREEN_WIDTH // 2, int(115 + bob))))
        surf.blit(sub_surf, sub_surf.get_rect(center=(SCREEN_WIDTH // 2, int(166 + bob))))

        spacing = 134
        base_x = SCREEN_WIDTH // 2 - int(1.5 * spacing)
        for i, card_s in enumerate(self.menu_showcase_surfs):
            cx = base_x + i * spacing
            cy = 298 + int(math.sin(t * 2.8 + i * 0.9) * 10.0)
            angle = math.sin(t * 1.9 + i * 1.1) * 6.0
            rot_card = pygame.transform.rotozoom(card_s, angle, 0.90)
            rot_sh = pygame.transform.rotozoom(self.menu_showcase_shadow, angle, 0.90)
            surf.blit(rot_sh, rot_sh.get_rect(center=(cx, cy + 10)))
            surf.blit(rot_card, rot_card.get_rect(center=(cx, cy)))

        surf.blit(self.lbl_grid_select, self.lbl_grid_select.get_rect(center=(SCREEN_WIDTH // 2, 408)))
        for btn in self.grid_selector_buttons:
            btn.draw(surf)

        for btn in self.menu_buttons:
            btn.draw(surf)

    def _draw_playing(self, surf: pygame.Surface):
        if self.board_frame_surf is not None:
            surf.blit(self.board_frame_surf, self.board_frame_surf.get_rect(center=self.board_center))

        banner_rect = self.hud_banner_surf.get_rect(center=(SCREEN_WIDTH // 2, 54))
        surf.blit(self.hud_banner_surf, banner_rect)

        mins = int(self.elapsed_seconds) // 60
        secs = int(self.elapsed_seconds) % 60
        time_str = f"{mins:02d}:{secs:02d}"
        score_int = int(round(self.displayed_score))

        cols = [
            (self.lbl_moves, f"{self.moves}", SCREEN_WIDTH // 2 - 195),
            (self.lbl_time, time_str, SCREEN_WIDTH // 2),
            (self.lbl_score, f"{score_int}", SCREEN_WIDTH // 2 + 195),
        ]
        for lbl_s, val_str, x_pos in cols:
            val_s = render_arcade_text(
                self.font_hud_value, val_str, (255, 255, 255), (255, 232, 165), (48, 20, 6), 2, 2
            )
            surf.blit(lbl_s, lbl_s.get_rect(center=(x_pos, 31)))
            surf.blit(val_s, val_s.get_rect(center=(x_pos, 54)))

        for div_x in (SCREEN_WIDTH // 2 - 100, SCREEN_WIDTH // 2 + 100):
            pygame.draw.line(surf, PALETTE["wood_deep"], (div_x, 22), (div_x, 66), 3)
            pygame.draw.line(surf, PALETTE["gold_mid"], (div_x + 2, 22), (div_x + 2, 66), 1)

        bar_w, bar_h = 236, 12
        bar_rect = pygame.Rect(SCREEN_WIDTH // 2 - bar_w // 2, 74, bar_w, bar_h)
        pygame.draw.rect(surf, PALETTE["wood_deep"], bar_rect.inflate(4, 4), border_radius=8)
        pygame.draw.rect(surf, (32, 16, 8), bar_rect, border_radius=6)
        if self.fever_meter > 0.01:
            fill_w = max(8, int(bar_w * self.fever_meter))
            pulse_c = (255, int(185 + 65 * math.sin(self.background.time * 10.0)), 45)
            fill_grad = create_linear_gradient_rect(
                fill_w,
                bar_h,
                [(0.0, (44, 198, 122)), (0.5, pulse_c), (1.0, (255, 248, 150))],
                border_radius=6,
                vertical=False,
            )
            surf.blit(fill_grad, bar_rect.topleft)
        pygame.draw.rect(surf, PALETTE["gold_mid"], bar_rect.inflate(2, 2), width=2, border_radius=7)

        for btn in self.hud_buttons:
            btn.draw(surf)

        idle_cards = []
        elevated_cards = []
        for card in self.cards:
            if (
                card.is_hovered
                or card.hint_timer > 0.0
                or abs(card.flip_spring.velocity) > 0.2
                or card.scale_spring.value > 1.02
            ):
                elevated_cards.append(card)
            else:
                idle_cards.append(card)

        for card in idle_cards:
            card.draw(surf)
        for card in elevated_cards:
            card.draw(surf)

    def _draw_victory_overlay(self, surf: pygame.Surface):
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        fade_alpha = int(min(185.0, self.victory_timer * 440.0))
        overlay.fill((10, 22, 16, fade_alpha))
        surf.blit(overlay, (0, 0))

        scale = max(0.05, self.victory_panel_spring.value)
        cx, cy = SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 8

        if abs(scale - 1.0) > 0.008:
            pw = max(1, int(self.victory_panel_surf.get_width() * scale))
            ph = max(1, int(self.victory_panel_surf.get_height() * scale))
            scaled_panel = pygame.transform.smoothscale(self.victory_panel_surf, (pw, ph))
            surf.blit(scaled_panel, scaled_panel.get_rect(center=(cx, cy)))
        else:
            surf.blit(self.victory_panel_surf, self.victory_panel_surf.get_rect(center=(cx, cy)))

        if scale < 0.65:
            return

        header_surf = render_arcade_text(
            self.font_title, "VICTORY!", (255, 255, 205), (245, 170, 20), (52, 20, 6), 4, 4
        )
        surf.blit(header_surf, header_surf.get_rect(center=(cx, cy - 156)))

        star_positions = [(cx - 102, cy - 68), (cx, cy - 82), (cx + 102, cy - 68)]
        for i in range(3):
            sx, sy = star_positions[i]
            surf.blit(self.star_empty_surf, self.star_empty_surf.get_rect(center=(sx, sy)))

            if i < self.earned_stars and self.star_springs[i].value > 0.02:
                s_val = max(0.05, self.star_springs[i].value)
                sw = max(1, int(self.star_earned_surf.get_width() * s_val))
                sh = max(1, int(self.star_earned_surf.get_height() * s_val))
                st_img = pygame.transform.smoothscale(self.star_earned_surf, (sw, sh))
                surf.blit(st_img, st_img.get_rect(center=(sx, sy)))

        mins = int(self.elapsed_seconds) // 60
        secs = int(self.elapsed_seconds) % 60
        stats = [
            f"FINAL SCORE:   {self.score}",
            f"TOTAL MOVES:   {self.moves}  ({self.grid_dim}x{self.grid_dim})",
            f"CLEAR TIME:    {mins:02d}:{secs:02d}",
        ]
        for idx, line in enumerate(stats):
            st_surf = render_arcade_text(
                self.font_subtitle, line, (255, 255, 255), (255, 225, 155), (48, 20, 6), 2, 2
            )
            surf.blit(st_surf, st_surf.get_rect(center=(cx, cy + 14 + idx * 38)))

        for btn in self.victory_buttons:
            btn.draw(surf)

    def run(self):
        while self.running:
            dt = self.clock.tick(FPS) / 1000.0
            dt = min(dt, 0.05)
            self.handle_events()
            self.update(dt)
            self.draw()

        pygame.quit()
        sys.exit()


if __name__ == "__main__":
    game = FruitMemoryDeluxeGame()
    game.run()