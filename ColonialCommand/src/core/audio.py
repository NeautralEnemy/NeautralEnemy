"""Minimal audio helper."""
from __future__ import annotations

import math
from typing import Dict

import pygame


class AudioSystem:
    """Small wrapper for Pygame mixer playing generated tones."""

    def __init__(self, muted: bool = False) -> None:
        self.muted = muted
        self.cache: Dict[str, pygame.mixer.Sound] = {}
        if not pygame.mixer.get_init():
            pygame.mixer.init()

    def set_muted(self, muted: bool) -> None:
        self.muted = muted

    def play(self, name: str, frequency: int = 440, duration: float = 0.15) -> None:
        if self.muted:
            return
        sound = self.cache.get(name)
        if sound is None:
            sound = self._generate_tone(frequency, duration)
            self.cache[name] = sound
        sound.play()

    def _generate_tone(self, frequency: int, duration: float) -> pygame.mixer.Sound:
        sample_rate = 22050
        n_samples = int(duration * sample_rate)
        buffer = bytearray()
        for i in range(n_samples):
            t = i / sample_rate
            value = int(127 * math.sin(2 * math.pi * frequency * t)) + 128
            buffer.append(max(0, min(255, value)))
        return pygame.mixer.Sound(buffer=bytes(buffer))
