from typing import Any, cast

import pygame
from pygame import mixer
from pygame import Surface, Rect
from pygame.mixer import Sound
from pygame.font import Font

from bnaval.common.config import BOARD_SIZE
from bnaval.client.utils import Colors, point_in_rect
from bnaval.client.res import ResourceManager
from bnaval.common.logic import PlayerBoard, ShipType, ShotState

_CASA_SIZE = 35


class Player:
    TOP_LEFT = (50, 390)

    def __init__(self, resource_manager: ResourceManager) -> None:
        self.board = PlayerBoard(
            width=0, height=0
        )  # vazia inicialmente... vai preencher quando receber os dados definitivamente
        self.is_turn = False
        self.id = 0
        self.rm = resource_manager

        self.ship_img = self.rm.get_image("barco")
        self.ship_destroyed_img = self.rm.get_image("barco_fogo")

    def board_pos_to_rect(self, x: int, y: int) -> Rect:
        bx, by = self.TOP_LEFT
        return Rect(bx + x * _CASA_SIZE, by + y * _CASA_SIZE, _CASA_SIZE, _CASA_SIZE)

    def draw_board(self, screen: Surface) -> None:
        for x, y, casa in self.board.items():
            br = self.board_pos_to_rect(x, y)
            cx, cy = (br.left + _CASA_SIZE // 2, br.top + _CASA_SIZE // 2)

            # https://www.pygame.org/docs/ref/draw.html#pygame.draw.rect
            pygame.draw.rect(screen, Colors.CASA_BG, br, 1)

            has_ship = casa.ship is not None
            if casa.state == ShotState.CLEAN and has_ship:
                # desenhando navio
                screen.blit(self.ship_img, br)
            elif casa.state == ShotState.HIT_OK:
                # desenhando navio destruído
                r = Rect(br)
                screen.blit(self.ship_destroyed_img, r)
            elif casa.state == ShotState.HIT_MISS:
                # desenhando mira errada (círculo leve)
                pygame.draw.circle(screen, Colors.WHITE, (cx, cy), 10, 1)


class Enemy:
    TOP_LEFT = (50, 30)

    def __init__(self, resource_manager: ResourceManager) -> None:
        bw, bh = BOARD_SIZE

        self.sunk_text: str | None = None
        self.rm = resource_manager
        self.board = PlayerBoard(width=bw, height=bh)
        self.start_ticks = pygame.time.get_ticks()

    def board_pos_to_rect(self, x: int, y: int) -> Rect:
        bx, by = self.TOP_LEFT
        return Rect(bx + x * _CASA_SIZE, by + y * _CASA_SIZE, _CASA_SIZE, _CASA_SIZE)

    def draw_board(self, screen: Surface) -> None:
        for x, y, casa in self.board.items():
            br = self.board_pos_to_rect(x, y)
            bg_color = Colors.CASA_BG
            fill = False

            if point_in_rect(pygame.mouse.get_pos(), br):
                bg_color = Colors.CASA_BG_HOVER
                fill = True
            pygame.draw.rect(screen, bg_color, br, 0 if fill else 1)

            cx, cy = (br.left + _CASA_SIZE // 2, br.top + _CASA_SIZE // 2)

            if casa.state == ShotState.HIT_OK:
                pygame.draw.circle(screen, Colors.HIT_OK, (cx, cy), 10, 0)
            elif casa.state == ShotState.HIT_MISS:
                width = 3
                offset = 8

                p1 = (cx - offset, cy - offset)
                p2 = (cx + offset, cy + offset)
                pygame.draw.line(screen, Colors.HIT_MISS, p1, p2, width)

                p1 = (cx - offset, cy + offset)
                p2 = (cx + offset, cy - offset)
                pygame.draw.line(screen, Colors.HIT_MISS, p1, p2, width)
