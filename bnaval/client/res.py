from __future__ import annotations
from typing import TypeAlias

import pygame
from pygame import Surface
from pygame.mixer import Sound
from pygame.font import Font

from bnaval.common.config import BGM_ENABLED
from bnaval.client.utils import AssetPaths

Resource: TypeAlias = "Sound | Font | Surface"


class SoundPlayer:
    def __init__(self, rm: ResourceManager) -> None:
        self.rm = rm
        self.known: dict[str, Sound] = {}
        self.current_bgm: str | None = None
        self.bgm_enabled = BGM_ENABLED
        pygame.mixer.init()

    def get(self, name: str) -> Sound:
        snd = self.known.get(name)
        if snd is not None:
            return snd
        res = self.rm.get(name)
        if isinstance(res, Sound):
            return res
        raise KeyError(f"não foi encontrado nenhum som com o nome {repr(name)}")

    def play(self, name: str, loop: bool = False) -> None:
        snd = self.get(name)
        snd.stop()
        snd.play(loops=-1 if loop else 0)

    def stop(self, name: str) -> None:
        self.get(name).stop()

    def disable_bgm(self) -> None:
        self.bgm_enabled = False
        self.stop_bgm()

    def play_bgm(self, name: str) -> None:
        if not self.bgm_enabled:
            return
        self.stop_bgm()
        self.play(name, loop=True)
        self.current_bgm = name

    def stop_bgm(self) -> None:
        if self.current_bgm is None:
            return
        self.stop(self.current_bgm)
        self.current_bgm = None


class ResourceManager:
    def __init__(self) -> None:
        self.known: dict[str, Resource] = {}
        self._load_all()

    def get(self, name: str) -> Resource | None:
        return self.known.get(name)

    def get_image(self, name: str) -> Surface:
        ret = self.get(name)
        assert isinstance(ret, Surface)
        return ret

    def get_font(self, name: str) -> Font:
        ret = self.get(name)
        assert isinstance(ret, Font)
        return ret

    def _load_all(self) -> None:
        def load_sound(path: str, volume: float) -> Sound:
            ret = Sound(path)
            ret.set_volume(volume)
            return ret

        self.known["snd_hit_ok"] = load_sound(AssetPaths.SFX_HIT_OK, 0.6)
        self.known["snd_hit_miss"] = load_sound(AssetPaths.SFX_HIT_MISS, 0.6)
        self.known["mus_titlescreen"] = load_sound(AssetPaths.MUS_TITLESCREEN, 0.5)

        # fontes de maior para menor
        self.known["font1"] = Font(AssetPaths.FONT, 34)
        self.known["font2"] = Font(AssetPaths.FONT, 20)
        self.known["font3"] = Font(AssetPaths.FONT, 15)

        self.known["barco1"] = pygame.image.load(AssetPaths.BARCO1)
        self.known["barco"] = pygame.image.load(AssetPaths.BARCO)
        self.known["barco_fogo"] = pygame.image.load(AssetPaths.BARCO_FOGO)
