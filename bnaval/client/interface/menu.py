import random
from typing import NamedTuple, TypeAlias, Literal

import pygame

from bnaval.client.res import ResourceManager, SoundPlayer
from bnaval.client.interface.ui import Ui
from bnaval.client.utils import Colors, ColorRGB
from bnaval.common import JsonValue


class MenuResponse:
    class Quit: ...

    class CreateRoom: ...

    class JoinRoom(NamedTuple):
        room: str

    Any: TypeAlias = "Quit | JoinRoom | CreateRoom | None"


class Menu:
    """Interface do menu principal do jogo."""

    def __init__(
        self,
        screen: pygame.Surface,
        ui: Ui,
        resm: ResourceManager,
        sound_player: SoundPlayer,
    ) -> None:
        self.resm = resm
        self.font1 = resm.get_font("font1")
        self.font2 = resm.get_font("font2")
        self.font3 = resm.get_font("font3")
        self.screen = screen
        self.ui = ui
        self.snd = sound_player

        self.show_menu = True
        self.lanes = [280, 420, 560]
        self.ships = [Ship(self.lanes[i], resm) for i in range(3)]
        self.join_code = ""

        self.error_msg: str | None = None

    def draw_bg_gradient(self, top_color: ColorRGB, bottom_color: ColorRGB) -> None:
        """Desenha o gradiente do fundo, linha a linha."""

        height = self.screen.get_height()
        width = self.screen.get_width()

        tr, tg, tb = top_color
        br, bg, bb = bottom_color

        for y in range(height):
            t = y / height

            r = int(tr * (1 - t) + br * t)
            g = int(tg * (1 - t) + bg * t)
            b = int(tb * (1 - t) + bb * t)

            pygame.draw.line(self.screen, (r, g, b), (0, y), (width, y))

    def run(self) -> MenuResponse.Any:
        """Atualiza e renderiza o menu a cada frame."""

        COLOR_BG_TOP = (38, 50, 70)
        COLOR_BG_BOT = (12, 25, 45)
        self.draw_bg_gradient(COLOR_BG_TOP, COLOR_BG_BOT)
        self.draw_ships()
        title = self.font1.render("BATALHA NAVAL", True, Colors.WHITE)
        self.screen.blit(title, (225 - title.get_width() // 2, 220))

        # posição das coisas
        MUSIC_OFF_BTN_CENTER = (222, 20)
        MUSIC_OFF_BTN_SIZE = (200, 30)
        CREATE_BTN_CENTER = (222, 350)
        CREATE_BTN_SIZE = (320, 50)
        TEXTBOX_CENTER = (222, 470)
        TEXTBOX_SIZE = (320, 50)
        JOIN_BTN_CENTER = (222, 530)
        JOIN_BTN_SIZE = (320, 50)

        self.ui.draw_button(
            center=MUSIC_OFF_BTN_CENTER,
            size=MUSIC_OFF_BTN_SIZE,
            text="Desativar música",
            font=self.font3,
        )
        if self.ui.last_btn_clicked:
            self.snd.disable_bgm()

        self.ui.draw_button(
            center=CREATE_BTN_CENTER,
            size=CREATE_BTN_SIZE,
            text="CRIAR PARTIDA",
            font=self.font2,
        )
        create_btn_clicked = self.ui.last_btn_clicked

        self.ui.draw_textbox(
            center=TEXTBOX_CENTER,
            size=TEXTBOX_SIZE,
            text=self.join_code,
            font=self.font2,
        )
        self.join_code = self.ui.last_textbox_text
        textbox_ok = self.ui.last_textbox_ok

        self.ui.draw_button(
            center=JOIN_BTN_CENTER,
            size=JOIN_BTN_SIZE,
            text="ENTRAR NA PARTIDA",
            font=self.font2,
        )
        join_btn_clicked = self.ui.last_btn_clicked

        if textbox_ok or join_btn_clicked:
            if len(self.join_code) == 6:
                return MenuResponse.JoinRoom(self.join_code)
            else:
                self.error_msg = "Código inválido (tem que ter 6 chars)"

        if self.error_msg is not None:
            text = self.font3.render(self.error_msg, True, Colors.RED)
            self.screen.blit(text, (230 - text.get_width() // 2, 600))

        if create_btn_clicked:
            return MenuResponse.CreateRoom()

        return None

    def reset(self) -> None:
        """Reseta o estado do menu para valores iniciais."""
        self.join_code = ""
        self.error_msg = None

    def draw_ships(self) -> None:
        """Renderiza os navios e gerencia sua criação e remoção."""
        for ship in self.ships:
            ship.draw(self.screen)

        self.ships = [ship for ship in self.ships if ship.visible]

        if len(self.ships) < 3:
            used_lanes = [ship.y for ship in self.ships]
            for lane in self.lanes:
                if lane not in used_lanes:
                    self.ships.append(Ship(lane, self.resm))


class Ship:
    """Representa um navio que se movimenta pela tela."""

    x: float
    y: float

    def __init__(self, y_pos: float, resm: ResourceManager) -> None:
        original_image = resm.get_image("barco1")
        new_width = int(original_image.get_width() * 0.4)
        new_height = int(original_image.get_height() * 0.4)
        self.image = pygame.transform.scale(original_image, (new_width, new_height))

        self.dir = random.choice(["<", ">"])
        if self.dir == ">":
            self.image = pygame.transform.flip(self.image, True, False)

        atraso = random.randint(40, 450)

        if self.dir == "<":
            self.x = 750 + self.image.get_width() + atraso
        else:
            self.x = -self.image.get_width() - atraso

        self.y = y_pos
        self.visible = True

        self.velocidade = random.uniform(2.0, 3.0)

    def draw(self, screen: pygame.Surface) -> None:
        """Atualiza o estado do navio (movimento) e o desenha na tela."""

        if self.dir == ">":
            self.x += self.velocidade
            if self.x > 750 + self.image.get_width() + 10:
                self.visible = False
        else:
            self.x -= self.velocidade
            if self.x < -self.image.get_width() - 10:
                self.visible = False

        screen.blit(self.image, (int(self.x), int(self.y)))
