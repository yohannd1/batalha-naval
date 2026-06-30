from __future__ import annotations
from dataclasses import dataclass
from typing import TypeAlias
from string import ascii_lowercase

import pygame
from pygame.event import Event


@dataclass
class KeyState:
    held: bool = False
    pressed: bool = False

    def update(self, held: bool) -> None:
        self.pressed = held and not self.held
        self.held = held


class InputManager:
    def __init__(self) -> None:
        self.mouse_l = KeyState()
        self.queued_input_keys: list[str | int] = []

    def on_keydown(self, ev: Event) -> None:
        if ev.key in {pygame.K_BACKSPACE, pygame.K_RETURN}:
            self.queued_input_keys.append(ev.key)
        elif (t := ev.unicode) in ascii_lowercase:
            # qualquer tecla ASCII lowercase digitada
            self.queued_input_keys.append(t)

    def pre_update(self) -> None:
        self.queued_input_keys.clear()

    def update(self) -> None:
        self.mouse_l.update(pygame.mouse.get_pressed(3)[0])
