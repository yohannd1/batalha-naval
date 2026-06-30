from threading import Thread

import pygame

from bnaval.client.res import ResourceManager, SoundPlayer
from bnaval.client.input import InputManager
from bnaval.client.interface.ui import Ui
from bnaval.client.interface.game import Game
from bnaval.client.interface.menu import Menu, MenuResponse
from bnaval.client.utils import FRAME_RATE, ClientConn, RESOLUTION
from bnaval.common import JsonObject


class Main:
    """Classe principal para o client."""

    def __init__(self) -> None:
        pygame.init()
        self.screen = pygame.display.set_mode(RESOLUTION)
        self.resm = ResourceManager()
        self.snd = SoundPlayer(self.resm)
        self.inm = InputManager()
        self.ui = Ui(self.screen, self.inm)
        self.conn: ClientConn | None = None

        pygame.display.set_caption("Batalha Naval")

        self._menu = Menu(self.screen, self.ui, self.resm, self.snd)
        self._game: Game | None = None
        self.current: Menu | Game = self._menu
        self.snd.play_bgm("mus_titlescreen")

        self.running = True
        self.clock = pygame.time.Clock()

    def try_begin_game(
        self,
        response: MenuResponse.JoinRoom | MenuResponse.CreateRoom,
    ) -> None:
        room_id: str | None = None
        to_send: JsonObject

        if isinstance(response, MenuResponse.JoinRoom):
            to_send = {"type": "ROOM_JOIN", "data": response.room}
            room_id = response.room
        elif isinstance(response, MenuResponse.CreateRoom):
            to_send = {"type": "ROOM_CREATE"}

        try:
            if self.conn is not None:
                # fechar conexão antiga para evitar erros
                self.conn.close()
            self.conn = ClientConn()

            game = Game(
                screen=self.screen,
                conn=self.conn,
                input_manager=self.inm,
                resource_manager=self.resm,
                menu=self._menu,
                sound_player=self.snd,
            )

            # tentar se comunicar com o servidor
            game.n.send(to_send)
            r = game.n.receive()

            # inicialmente limpar a mensagem de erro
            self._menu.error_msg = None

            if isinstance(r, dict):
                typ = r.get("type")

                if typ == "ROOM_CREATED":
                    payl = r.get("data")
                    if not isinstance(payl, str):
                        self._menu.error_msg = "Resposta inválida"
                        print(f"Resposta inválida: sala inválida: {repr(payl)}")
                        return
                    room_id = payl
                elif typ == "ROOM_WAIT":
                    pass  # não precisa fazer nada aqui
                elif typ == "ROOM_INVALID":
                    self._menu.error_msg = "Sala desconhecida"
                    return
                elif typ == "ROOM_FULL":
                    self._menu.error_msg = "Sala cheia"
                    return
                else:
                    self._menu.error_msg = "Resposta desconhecida"
                    print(f"Resposta desconhecida: {repr(r)}")
                    return
            else:
                self._menu.error_msg = "Resposta desconhecida"
                print(f"Resposta desconhecida: {repr(r)}")
                return

            # conseguimos conectar!
            assert room_id is not None
            self.current = self._game = game
            self.current.set_room_wait(room_id)
            self.current.start_recv_thread()
        except ConnectionRefusedError as exc:
            self._menu.error_msg = "Não foi possível conectar ao servidor"
            print(f"Erro ao conectar: {exc}")

    def run(self) -> None:
        while self.running:
            self.ui.pre_update()

            if isinstance(self.current, Menu):
                rm = self.current.run()
                if isinstance(rm, MenuResponse.Quit):
                    self.running = False
                    break
                elif isinstance(rm, MenuResponse.JoinRoom | MenuResponse.CreateRoom):
                    self.try_begin_game(rm)

            elif isinstance(self.current, Game):
                rg = self.current.run()

                if rg == "MENU":
                    # resetar o jogo
                    self._menu.reset()
                    self.snd.play("mus_titlescreen")
                    if self._game is not None:
                        self._game.reset()
                    self.current = self._menu

            self.inm.pre_update()
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    if self.conn is not None:
                        self.conn.close()
                    self.running = False
                elif event.type == pygame.KEYDOWN:
                    self.inm.on_keydown(event)
            self.inm.update()
            self.ui.post_update()
            pygame.display.flip()
            self.clock.tick(FRAME_RATE)

        return pygame.quit()


if __name__ == "__main__":
    Main().run()
