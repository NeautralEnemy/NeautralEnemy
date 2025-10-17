"""Base classes for scenes."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import pygame

from core import gfx
from core.audio import AudioSystem
from core.ui import MessageLog
from core.debug import DebugConsole


@dataclass
class SceneContext:
    app: "App"
    gfx: gfx
    audio: AudioSystem
    message_log: MessageLog
    debug: DebugConsole


class SceneBase:
    def __init__(self, context: SceneContext) -> None:
        self.context = context

    def rebind(self, context: SceneContext) -> None:
        self.context = context

    def on_enter(self, **kwargs) -> None:
        pass

    def handle_event(self, event: pygame.event.Event) -> None:
        pass

    def update(self, dt: float) -> None:
        pass

    def draw(self, surface: pygame.Surface, alpha: float) -> None:
        pass

    def on_escape(self) -> bool:
        return False

    def on_exit(self) -> None:
        pass

    @property
    def app(self):
        return self.context.app

    @property
    def message_log(self):
        return self.context.message_log

    @property
    def debug(self):
        return self.context.debug
