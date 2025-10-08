"""Graphics helpers for Colonial Command."""
from __future__ import annotations

from typing import Dict, List, Tuple

import pygame

Palette = List[Tuple[int, int, int]]

_PALETTES: Dict[str, Palette] = {
    "sunset": [
        (12, 8, 20),
        (26, 16, 48),
        (52, 24, 68),
        (92, 34, 88),
        (140, 46, 110),
        (196, 69, 130),
        (230, 110, 140),
        (248, 174, 158),
        (255, 220, 176),
        (255, 252, 224),
        (60, 38, 54),
        (88, 58, 74),
        (116, 78, 90),
        (144, 102, 108),
        (172, 130, 132),
        (200, 162, 158),
        (228, 196, 188),
        (32, 16, 32),
        (64, 40, 52),
        (108, 64, 68),
        (152, 92, 76),
        (204, 126, 86),
        (236, 164, 108),
        (252, 208, 140),
        (244, 236, 176),
        (196, 216, 192),
        (144, 188, 196),
        (88, 154, 190),
        (48, 118, 180),
        (28, 84, 156),
        (16, 52, 120),
        (8, 28, 72),
    ],
    "jade": [
        (4, 12, 20),
        (12, 24, 36),
        (20, 40, 52),
        (28, 60, 68),
        (40, 84, 88),
        (60, 112, 104),
        (84, 148, 120),
        (120, 188, 136),
        (164, 224, 156),
        (220, 248, 188),
        (60, 32, 28),
        (92, 48, 40),
        (128, 64, 52),
        (164, 84, 68),
        (200, 108, 88),
        (228, 144, 120),
        (248, 184, 160),
        (12, 12, 12),
        (32, 28, 24),
        (56, 52, 48),
        (80, 80, 76),
        (108, 112, 108),
        (136, 148, 140),
        (168, 188, 176),
        (200, 224, 208),
        (232, 248, 236),
        (44, 64, 48),
        (64, 92, 64),
        (88, 120, 84),
        (120, 156, 108),
        (152, 188, 132),
        (184, 220, 160),
    ],
    "dusk": [
        (10, 8, 24),
        (20, 16, 44),
        (34, 26, 64),
        (56, 40, 84),
        (82, 60, 104),
        (112, 84, 120),
        (148, 112, 136),
        (184, 144, 156),
        (216, 180, 180),
        (244, 216, 208),
        (44, 20, 28),
        (72, 32, 40),
        (102, 48, 52),
        (134, 64, 64),
        (168, 84, 76),
        (204, 108, 92),
        (236, 136, 108),
        (12, 16, 24),
        (28, 32, 40),
        (48, 48, 60),
        (68, 68, 84),
        (92, 92, 112),
        (120, 120, 140),
        (152, 152, 172),
        (188, 188, 204),
        (224, 224, 232),
        (28, 40, 68),
        (40, 60, 96),
        (54, 84, 124),
        (70, 112, 152),
        (88, 144, 180),
        (112, 180, 208),
    ],
}

_default_palette = _PALETTES["sunset"]

_bitmap_font = {
    "A": [0b01110, 0b10001, 0b11111, 0b10001, 0b10001],
    "B": [0b11110, 0b10001, 0b11110, 0b10001, 0b11110],
    "C": [0b01110, 0b10001, 0b10000, 0b10001, 0b01110],
    "D": [0b11100, 0b10010, 0b10001, 0b10010, 0b11100],
    "E": [0b11111, 0b10000, 0b11110, 0b10000, 0b11111],
    "F": [0b11111, 0b10000, 0b11110, 0b10000, 0b10000],
    "G": [0b01110, 0b10000, 0b10111, 0b10001, 0b01111],
    "H": [0b10001, 0b10001, 0b11111, 0b10001, 0b10001],
    "I": [0b11111, 0b00100, 0b00100, 0b00100, 0b11111],
    "J": [0b11111, 0b00010, 0b00010, 0b10010, 0b01100],
    "K": [0b10001, 0b10010, 0b11100, 0b10010, 0b10001],
    "L": [0b10000, 0b10000, 0b10000, 0b10000, 0b11111],
    "M": [0b10001, 0b11011, 0b10101, 0b10001, 0b10001],
    "N": [0b10001, 0b11001, 0b10101, 0b10011, 0b10001],
    "O": [0b01110, 0b10001, 0b10001, 0b10001, 0b01110],
    "P": [0b11110, 0b10001, 0b11110, 0b10000, 0b10000],
    "Q": [0b01110, 0b10001, 0b10001, 0b10011, 0b01111],
    "R": [0b11110, 0b10001, 0b11110, 0b10010, 0b10001],
    "S": [0b01111, 0b10000, 0b01110, 0b00001, 0b11110],
    "T": [0b11111, 0b00100, 0b00100, 0b00100, 0b00100],
    "U": [0b10001, 0b10001, 0b10001, 0b10001, 0b01110],
    "V": [0b10001, 0b10001, 0b10001, 0b01010, 0b00100],
    "W": [0b10001, 0b10001, 0b10101, 0b11011, 0b10001],
    "X": [0b10001, 0b01010, 0b00100, 0b01010, 0b10001],
    "Y": [0b10001, 0b01010, 0b00100, 0b00100, 0b00100],
    "Z": [0b11111, 0b00010, 0b00100, 0b01000, 0b11111],
}
_bitmap_font.update({str(i): _bitmap_font[ch] for i, ch in enumerate("0123456789") if ch in _bitmap_font})


def get_palette(name: str) -> Palette:
    return _PALETTES.get(name, _default_palette)


def draw_text(surface: pygame.Surface, text: str, position: Tuple[int, int], color_index: int = 9) -> None:
    palette = get_palette("sunset")
    color = palette[color_index % len(palette)]
    x, y = position
    for char in text.upper():
        glyph = _bitmap_font.get(char)
        if glyph is None:
            x += 4
            continue
        for row, bits in enumerate(glyph):
            for col in range(5):
                if bits & (1 << (4 - col)):
                    surface.set_at((x + col, y + row), color)
        x += 6


def draw_panel(surface: pygame.Surface, rect: pygame.Rect, palette_name: str, bevel: bool = True) -> None:
    palette = get_palette(palette_name)
    bg = palette[3]
    surface.fill(bg, rect)
    if bevel:
        light = palette[8]
        dark = palette[1]
        pygame.draw.line(surface, light, rect.topleft, (rect.right - 1, rect.top))
        pygame.draw.line(surface, light, rect.topleft, (rect.left, rect.bottom - 1))
        pygame.draw.line(surface, dark, (rect.left, rect.bottom - 1), (rect.right - 1, rect.bottom - 1))
        pygame.draw.line(surface, dark, (rect.right - 1, rect.top), (rect.right - 1, rect.bottom - 1))


def draw_tooltip(surface: pygame.Surface, text: str, position: Tuple[int, int]) -> None:
    lines = text.split("\n")
    width = max(len(line) for line in lines) * 6 + 6
    height = len(lines) * 8 + 4
    rect = pygame.Rect(position[0], position[1] - height, width, height)
    draw_panel(surface, rect, "sunset")
    for i, line in enumerate(lines):
        draw_text(surface, line, (rect.x + 4, rect.y + 4 + i * 8), color_index=15)


def apply_scanlines(surface: pygame.Surface) -> pygame.Surface:
    scan = surface.copy()
    dark = pygame.Surface(scan.get_size(), flags=pygame.SRCALPHA)
    dark.fill((0, 0, 0, 40))
    for y in range(0, scan.get_height(), 2):
        scan.blit(dark, (0, y), area=pygame.Rect(0, y, scan.get_width(), 1))
    vignette = pygame.Surface(scan.get_size(), pygame.SRCALPHA)
    pygame.draw.rect(vignette, (0, 0, 0, 35), vignette.get_rect(), border_radius=20)
    scan.blit(vignette, (0, 0), special_flags=pygame.BLEND_RGBA_SUB)
    return scan


def draw_icon(surface: pygame.Surface, center: Tuple[int, int], icon: str, palette_name: str) -> None:
    palette = get_palette(palette_name)
    color = palette[12]
    x, y = center
    if icon == "infantry":
        pygame.draw.rect(surface, color, pygame.Rect(x - 3, y - 6, 6, 10))
        pygame.draw.circle(surface, color, (x, y - 7), 3)
    elif icon == "cavalry":
        pygame.draw.polygon(surface, color, [(x - 6, y + 4), (x, y - 6), (x + 6, y + 4)])
    elif icon == "artillery":
        pygame.draw.circle(surface, color, (x - 5, y + 3), 3)
        pygame.draw.circle(surface, color, (x + 5, y + 3), 3)
        pygame.draw.rect(surface, color, pygame.Rect(x - 4, y - 2, 8, 4))
    elif icon == "ship":
        pygame.draw.polygon(surface, color, [(x - 6, y + 4), (x + 6, y + 4), (x, y - 6)])
    else:
        pygame.draw.circle(surface, color, (x, y), 4)
