"""Minimal audio helper."""
from __future__ import annotations

import array
import math
from typing import Dict, Optional

import pygame


class AudioSystem:
    """Small wrapper for Pygame mixer playing generated tones."""

    def __init__(self, muted: bool = False) -> None:
        self.muted = muted
        self.cache: Dict[str, pygame.mixer.Sound] = {}
        self._available = True
        if not pygame.mixer.get_init():
            try:
                pygame.mixer.init(frequency=44100, size=-16, channels=1)
            except Exception:
                # Gracefully handle environments without an audio device.
                self._available = False
                self.muted = True

    def set_muted(self, muted: bool) -> None:
        self.muted = muted

    def play(self, name: str, frequency: int = 440, duration: float = 0.15) -> None:
        if self.muted or not self._available:
            return
        sound = self.cache.get(name)
        if sound is None:
            sound = self._generate_tone(frequency, duration)
            if sound is None:
                self._available = False
                self.muted = True
                return
            self.cache[name] = sound
        sound.play()

    def _generate_tone(self, frequency: int, duration: float) -> Optional[pygame.mixer.Sound]:
        init = pygame.mixer.get_init()
        if not init:
            return None
        sample_rate = abs(init[0]) or 44100
        n_samples = int(duration * sample_rate)
        if n_samples <= 0:
            n_samples = 1
        samples = array.array("h")
        amplitude = 32767
        for i in range(n_samples):
            t = i / sample_rate
            value = int(amplitude * math.sin(2 * math.pi * frequency * t))
            samples.append(value)
        try:
            return pygame.mixer.Sound(buffer=samples)
        except Exception:
            return None
