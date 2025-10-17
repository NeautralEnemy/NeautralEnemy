"""Core application loop and scene management."""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional

import pygame

from . import gfx
from .audio import AudioSystem
from .debug import DebugConsole
from .saveio import save_autosave
from .state import GameState
from .ui import MessageLog
from scenes.base import SceneBase, SceneContext

FPS = 60
INTERNAL_WIDTH = 320
INTERNAL_HEIGHT = 200
TIME_STEP = 1.0 / 30.0
WINDOW_SCALE_MIN = 2
WINDOW_SCALE_MAX = 5


@dataclass
class SceneEntry:
    factory: Callable[[SceneContext], SceneBase]
    instance: Optional[SceneBase] = None


class App:
    """Main application object that owns surfaces, scenes, and global services."""

    def __init__(self, config: dict) -> None:
        self.config = config
        self.clock = pygame.time.Clock()
        self.internal_surface = pygame.Surface((INTERNAL_WIDTH, INTERNAL_HEIGHT))
        self.window_scale = self._coerce_window_scale(config.get("window_scale", 3))
        self.window = self._create_window()
        self.config["window_scale"] = self.window_scale
        self.running = True
        self.accumulator = 0.0
        self.audio = AudioSystem(muted=not self._coerce_bool(config.get("audio", True), default=True))
        self.config["audio"] = not self.audio.muted
        self.message_log = MessageLog(max_lines=6)
        self.debug = DebugConsole()
        self._debug_timer = 0.0
        self.palette_id = self._coerce_palette(config.get("palette", "sunset"))
        self.config["palette"] = self.palette_id
        self.scanlines = self._coerce_bool(config.get("scanlines", False), default=False)
        self.config["scanlines"] = self.scanlines
        self.skip_ai = self._coerce_bool(config.get("skip_ai_moves", False), default=False)
        self.config["skip_ai_moves"] = self.skip_ai
        self.state: Optional[GameState] = None
        self.scene_registry: Dict[str, SceneEntry] = {}
        self.active_scene: Optional[SceneBase] = None
        self._register_scenes()
        self.switch_scene("menu")

    @staticmethod
    def _coerce_window_scale(value: Any) -> int:
        try:
            scale = int(value)
        except (TypeError, ValueError):
            scale = 3
        return max(WINDOW_SCALE_MIN, min(WINDOW_SCALE_MAX, scale))

    @staticmethod
    def _coerce_bool(value: Any, *, default: bool) -> bool:
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            lowered = value.strip().lower()
            if lowered in {"1", "true", "yes", "on"}:
                return True
            if lowered in {"0", "false", "no", "off"}:
                return False
        return default

    @staticmethod
    def _coerce_palette(value: Any) -> str:
        return value if isinstance(value, str) else "sunset"

    def _create_window(self) -> pygame.Surface:
        size = (INTERNAL_WIDTH * self.window_scale, INTERNAL_HEIGHT * self.window_scale)
        try:
            return pygame.display.set_mode(size)
        except pygame.error:
            # Retry with a scaled software surface (works around some driver issues).
            pygame.display.quit()
            pygame.display.init()
            flags = getattr(pygame, "SCALED", 0)
            try:
                return pygame.display.set_mode(size, flags)
            except pygame.error as exc:
                raise RuntimeError(
                    "Unable to create the game window. Try updating your graphics drivers or "
                    "running with a different SDL_VIDEODRIVER."
                ) from exc

    def _register_scenes(self) -> None:
        from scenes.menu import MenuScene
        from scenes.campaign import CampaignScene
        from scenes.settings import SettingsScene
        from scenes.help import HelpScene
        from scenes.tactical import TacticalScene

        self.scene_registry = {
            "menu": SceneEntry(lambda ctx: MenuScene(ctx)),
            "campaign": SceneEntry(lambda ctx: CampaignScene(ctx)),
            "settings": SceneEntry(lambda ctx: SettingsScene(ctx)),
            "help": SceneEntry(lambda ctx: HelpScene(ctx)),
            "tactical": SceneEntry(lambda ctx: TacticalScene(ctx)),
        }

    def _context_factory(self) -> SceneContext:
        return SceneContext(
            app=self,
            gfx=gfx,
            audio=self.audio,
            message_log=self.message_log,
            debug=self.debug,
        )

    def set_window_scale(self, scale: int) -> None:
        self.window_scale = self._coerce_window_scale(scale)
        self.config["window_scale"] = self.window_scale
        self.window = self._create_window()

    def set_palette(self, palette_id: str) -> None:
        self.palette_id = palette_id
        self.config["palette"] = palette_id

    def set_scanlines(self, enabled: bool) -> None:
        self.scanlines = enabled
        self.config["scanlines"] = enabled

    def set_audio(self, enabled: bool) -> None:
        self.audio.set_muted(not enabled)
        self.config["audio"] = enabled

    def set_skip_ai(self, enabled: bool) -> None:
        self.skip_ai = enabled
        self.config["skip_ai_moves"] = enabled

    def run(self) -> None:
        last_time = time.perf_counter()
        while self.running:
            now = time.perf_counter()
            frame_time = min(0.25, now - last_time)
            last_time = now
            self.accumulator += frame_time
            self._process_events()
            while self.accumulator >= TIME_STEP:
                self._update(TIME_STEP)
                self.accumulator -= TIME_STEP
            alpha = self.accumulator / TIME_STEP
            self._render(alpha)
            pygame.display.flip()
            elapsed = self.clock.tick(FPS) / 1000.0
            if self.debug.visible:
                self._debug_timer += elapsed
                if self._debug_timer >= 1.0:
                    fps = self.clock.get_fps()
                    self.debug.add(f"FPS {fps:.1f}")
                    self._debug_timer = 0.0

    def _process_events(self) -> None:
        for event in pygame.event.get():
            if event.type in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP, pygame.MOUSEMOTION):
                scale = self.window_scale
                if scale > 1:
                    x, y = event.pos
                    new_event = pygame.event.Event(
                        event.type,
                        {**event.dict, "pos": (x // scale, y // scale)}
                    )
                    event = new_event
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                if self.active_scene and self.active_scene.on_escape():
                    continue
                self.running = False
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_BACKQUOTE:
                self.debug.toggle()
                if self.state:
                    self.debug.add(f"Seed {self.state.rng_seed}")
            if self.active_scene:
                self.active_scene.handle_event(event)

    def _update(self, dt: float) -> None:
        self.message_log.update(dt)
        if self.active_scene:
            self.active_scene.update(dt)

    def _render(self, alpha: float) -> None:
        palette = gfx.get_palette(self.palette_id)
        self.internal_surface.fill(palette[0])
        if self.active_scene:
            self.active_scene.draw(self.internal_surface, alpha)
        self.debug.draw(self.internal_surface)
        surface = self.internal_surface
        if self.scanlines:
            surface = gfx.apply_scanlines(surface)
        scaled = pygame.transform.scale(
            surface, (INTERNAL_WIDTH * self.window_scale, INTERNAL_HEIGHT * self.window_scale)
        )
        self.window.blit(scaled, (0, 0))

    def switch_scene(self, name: str, **kwargs) -> None:
        if name not in self.scene_registry:
            raise KeyError(f"Unknown scene '{name}'")
        if self.active_scene is not None:
            self.active_scene.on_exit()
        entry = self.scene_registry[name]
        context = self._context_factory()
        if entry.instance is None:
            entry.instance = entry.factory(context)
        else:
            entry.instance.rebind(context)
        if kwargs:
            entry.instance.on_enter(**kwargs)
        else:
            entry.instance.on_enter()
        self.active_scene = entry.instance

    def start_new_game(self, seed: Optional[int] = None) -> None:
        self.state = GameState.new_game(seed)
        save_autosave(self.state)
        self.config["last_save_slot"] = "autosave"
        self.switch_scene("campaign")

    def load_game(self, slot: str) -> bool:
        state = GameState.load(slot)
        if state:
            self.state = state
            self.switch_scene("campaign")
            return True
        return False

    def continue_battle(self, battle_state: dict) -> None:
        self.switch_scene("tactical", battle_state=battle_state)

    def exit(self) -> None:
        self.running = False
