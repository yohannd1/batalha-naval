from __future__ import annotations
from typing import TypeAlias
from socket import socket, AF_INET, SOCK_STREAM

from pygame import Rect

from bnaval.common.network import Conn
from bnaval.common import JsonValue
from bnaval.common.config import SERVER_ADDR, SERVER_PORT, MAX_PLAYERS

ColorRGB: TypeAlias = tuple[int, int, int]
"""Um trio de valores RGB entre 0 e 255"""

RESOLUTION = (450, 740)

FRAME_RATE = 30
"""A taxa de quadros do jogo."""


class AssetPaths:
    """Caminhos para todos os assets do jogo (fontes, sprites e SFXs)."""

    FONT = "bnaval/client/assets/font/retrofont.ttf"
    BARCO = "bnaval/client/assets/img/barco.png"
    BARCO1 = "bnaval/client/assets/img/barco1.png"
    BARCO_FOGO = "bnaval/client/assets/img/barco_fogo.png"
    SFX_HIT_OK = "bnaval/client/assets/sfx_hit_ok.mp3"
    SFX_HIT_MISS = "bnaval/client/assets/sfx_hit_miss.mp3"
    MUS_TITLESCREEN = "bnaval/client/assets/mus_titlescreen.mp3"


class Colors:
    RED = (191, 97, 106)
    GREEN = (163, 190, 140)
    WHITE = (229, 233, 240)
    FG_LIGHT = (76, 86, 106)
    BACKGROUND = (56, 66, 82)
    DARK = (46, 52, 64)
    AQUA = (143, 188, 187)
    BLUE = (129, 161, 193)
    CYAN = (136, 192, 208)

    BUTTON_FG = (76, 86, 106)
    BUTTON_BG = (224, 255, 255)
    BUTTON_BG_HOVER = (195, 210, 220)
    BUTTON_BG_PRESS = (150, 150, 170)

    HIT_OK = RED
    HIT_MISS = WHITE
    CASA_BG = (76, 86, 106)
    CASA_BG_HOVER = (85, 92, 108)


def point_in_rect(p: tuple[int, int], r: tuple[int, int, int, int] | Rect) -> bool:
    """Verifica se o ponto `p` está contido no retângulo `r`."""
    px, py = p
    rx, ry, rw, rh = r
    return py > ry and py < ry + rh and px > rx and px < rx + rw


class ClientConn:
    """Wrapper para as conexões feitas pelo client."""

    def __init__(self, sock: socket = socket(AF_INET, SOCK_STREAM)):
        sock.connect((SERVER_ADDR, SERVER_PORT))
        self.conn = Conn(sock)

    def receive(self) -> JsonValue:
        return self.conn.recv()

    def send(self, data: JsonValue) -> None:
        self.conn.send(data)

    def close(self) -> None:
        self.conn.close()
