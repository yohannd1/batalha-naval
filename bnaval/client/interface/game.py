from __future__ import annotations
from typing import Any, cast, Literal, TypeAlias
from threading import Thread

import pygame
from pygame import Surface
from pygame.font import Font

from bnaval.client.input import InputManager
from bnaval.client.res import SoundPlayer, ResourceManager
from bnaval.client.interface.ui import Ui
from bnaval.client.interface.players import Player, Enemy
from bnaval.client.interface.menu import Menu
from bnaval.client.utils import ClientConn, Colors, point_in_rect, ColorRGB
from bnaval.common import JsonValue, AssertVal
from bnaval.common.logic import PlayerBoard, ShotState

GameResponse: TypeAlias = Literal["MENU", None]


class Game:
    def __init__(
        self,
        screen: Surface,
        conn: ClientConn,
        input_manager: InputManager,
        resource_manager: ResourceManager,
        sound_player: SoundPlayer,
        menu: Menu,
    ) -> None:
        self.menu = menu

        self.ui = Ui(screen, input_manager)
        self.snd = sound_player
        self.resm = resource_manager
        self.inm = input_manager

        self.screen = screen
        self.game_over = False
        self.waiting = True
        self.disconnected_msg: str | None = None
        self.room_id = ""

        self.player = Player(self.resm)
        self.enemy = Enemy(self.resm)
        self.n = conn

        self.game_over_text = ""
        self.notice_text: str | None = None

        self.font1 = self.resm.get_font("font1")
        self.font2 = self.resm.get_font("font2")
        self.font3 = self.resm.get_font("font3")

        self.menu_button = pygame.Rect(125, 0, 200, 28)

        self.recv_thread: Thread | None = None

    def start_recv_thread(self) -> None:
        if self.recv_thread is not None:
            return

        self.recv_thread = Thread(target=self.receiving_thread)
        self.recv_thread.daemon = (
            True  # TODO: acho que não é bom fazer isso mas tá ok por agora
        )
        self.recv_thread.start()

    def receiving_thread(self, menu: Any = None) -> None:
        while True:
            conn_end = False
            try:
                received = self.n.receive()
            except ConnectionError:
                conn_end = True

            if conn_end:
                self.disconnected_msg = "Conexão perdida"
            elif isinstance(received, dict):
                typ = received["type"]
                if typ == "DISCONNECTED":
                    self.disconnected_msg = "O oponente desconectou"
                elif typ == "GAME_STARTED":
                    if not self.waiting:
                        print("Recebeu layout no meio de uma partida?")
                        continue
                    self.waiting = False

                    self.player.id = AssertVal.int_(received["your_id"])
                    first_player = AssertVal.int_(received["first_player"])
                    self.player.is_turn = self.player.id == first_player

                    board_json = AssertVal.json_object(received["your_board"])
                    self.player.board = PlayerBoard.from_json(board_json)
                elif typ == "ROOM_CREATED":
                    assert isinstance(received["data"], str)
                    self.room_id = received["data"]
                elif typ == "SHOT_RESULT":
                    result = received["result"]
                    who_shot = AssertVal.int_(received["who_shot"])
                    is_you = self.player.id == who_shot
                    x, y = AssertVal.list_int(received["pos"])
                    sunk_ship = received["sunk_ship"]
                    winner = received["winner"]
                    next_player = AssertVal.int_(received["next_player"])
                    target = self.enemy.board if is_you else self.player.board
                    snd_name: str | None = None

                    self.notice_text = None  # limpar texto de aviso
                    if result == "INVALID":
                        if is_you:
                            self.notice_text = "Tiro inválido"
                    elif result == "MISS":
                        if is_you:
                            snd_name = "snd_hit_miss"
                        target.get(x, y).state = ShotState.HIT_MISS
                    elif result == "HIT":
                        if is_you:
                            snd_name = "snd_hit_ok"
                            if sunk_ship is not None:
                                self.notice_text = f"Você afundou o {sunk_ship}"
                        target.get(x, y).state = ShotState.HIT_OK
                    else:
                        print(f"SHOT_RESULT meio inválido: {repr(result)}")

                    if snd_name is not None:
                        self.snd.play(snd_name)

                    self.player.is_turn = self.player.id == next_player

                    if winner is not None:
                        self.game_over = True
                        winner_is_you = winner == self.player.id
                        self.game_over_text = (
                            "Você Ganhou!" if winner_is_you else "Você Perdeu!"
                        )
                else:
                    print(f"Mensagem desconhecida recebida: {received}")
            else:
                print(f"Mensagem desconhecida recebida: {repr(received)}")

    def draw_game(self) -> None:
        pygame.draw.line(self.screen, Colors.FG_LIGHT, (0, 384), (450, 384), 10)

        # desenhar a área do player
        self.player.draw_board(self.screen)

        # desenhar a área do oponente (e possivelmente interagir)
        for x, y, casa in self.enemy.board.items():
            r = self.enemy.board_pos_to_rect(x, y)
            if (
                casa.state == ShotState.CLEAN
                and point_in_rect(pygame.mouse.get_pos(), r)
                and self.inm.mouse_l.pressed
                and self.player.is_turn
            ):
                self.n.send({"type": "SHOOT_AT", "position": [x, y]})

        self.enemy.draw_board(self.screen)

    def draw_disconnected(self) -> JsonValue:
        """Desenha a tela de desconexão."""

        INFO_CENTER = (225, 370)

        self.screen.fill(Colors.BACKGROUND)
        self.ui.draw_text(
            center=INFO_CENTER,
            text=self.disconnected_msg or "...",
            font=self.font1,
            color=Colors.RED,
        )
        self.ui.draw_button(
            center=(225, 400),
            size=(150, 30),
            text="Voltar",
            font=self.font2,
        )
        if self.ui.last_btn_clicked:
            return "MENU"
        else:
            return None

    def draw_game_over(self) -> JsonValue:
        """Renderiza e possibilita interações com a tela de fim de jogo."""

        if self.game_over_text == "Você Perdeu!":
            # só desenhar as casas destruídas, caso você perdeu (consertando um bug meio ruim...)
            for x, y, casa in self.player.board.items():
                if casa.ship:
                    r = self.player.board_pos_to_rect(x, y)
                    self.screen.blit(self.player.ship_destroyed_img, r)

        pygame.draw.rect(self.screen, Colors.BACKGROUND, (0, 0, 450, 20))
        pygame.draw.rect(self.screen, Colors.FG_LIGHT, self.menu_button, 2)

        self.ui.draw_text(
            center=(225, 370),
            text=self.game_over_text,
            font=self.font1,
            color=Colors.GREEN,
        )

        self.ui.draw_button(
            center=(225, 400),
            size=(150, 30),
            text="Voltar",
            font=self.font2,
        )
        if self.ui.last_btn_clicked:
            return "MENU"
        else:
            return None

    def set_room_wait(self, room_id: str) -> None:
        self.room_id = room_id
        self.waiting = True

    def run(self) -> JsonValue:
        INFO_CENTER = (225, 370)

        if self.disconnected_msg is not None:
            return self.draw_disconnected()
        elif self.game_over:
            return self.draw_game_over()
        elif self.waiting:
            self.screen.fill(Colors.BACKGROUND)
            self.ui.draw_text(
                center=INFO_CENTER,
                text="Esperando Jogador",
                font=self.font1,
                color=Colors.GREEN,
            )
            self.ui.draw_text(
                center=(INFO_CENTER[0], INFO_CENTER[1] + 100),
                text=self.room_id,
                font=self.font2,
                color=Colors.GREEN,
            )
            return None
        else:
            self.screen.fill(Colors.BACKGROUND)
            self.draw_game()

            self.ui.draw_text(
                center=(225, 10),
                text=("Sua vez" if self.player.is_turn else "Vez do oponente"),
                font=self.font3,
                color=Colors.WHITE,
            )

            if self.notice_text is not None:
                self.ui.draw_text(
                    center=(225, 30),
                    text=self.notice_text,
                    font=self.font3,
                    color=Colors.WHITE,
                )
            return None

    def reset(self) -> None:
        self.game_over = False
        self.waiting = True
        self.disconnected_msg = None
        self.room_id = ""
        self.player = Player(self.resm)
        self.enemy = Enemy(self.resm)
        self.game_over_text = ""
