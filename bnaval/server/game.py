from __future__ import annotations
from random import Random
from typing import TypedDict, cast, Literal

from bnaval.common.config import MAX_PLAYERS, BOARD_SIZE
from bnaval.common.logic import PlayerBoard, ShipType, ShotState
from bnaval.common import JsonObject, JsonValue


class ShotResultResponse(TypedDict):
    type: Literal["SHOT_RESULT"]
    result: Literal["MISS", "HIT", "INVALID"]
    pos: list[int]
    who_shot: int
    sunk_ship: str | None
    winner: int | None
    next_player: int


class GameStartedResponse(TypedDict):
    type: Literal["GAME_STARTED"]
    your_id: int
    your_board: JsonObject
    first_player: int


class GameState:
    """
    Lógica central do jogo usada pelo servidor para coordenar os turnos e
    validar os tiros recebidos.

    Responsabildades:
    - geração e processamento dos tabuleiros de cada jogador;
    - controle de turnos (quem começa, e de quem é a vez);
    - processamento e validação de cada tiro (se acertou ou não);
    - detecção de fim de jogo;
    """

    def __init__(self, rng: Random) -> None:
        self.vez: int = rng.choice(list(range(MAX_PLAYERS)))  # sorteando quem começa...
        self.grades: list[PlayerBoard] = [
            self._make_board(rng) for _ in range(MAX_PLAYERS)
        ]
        self.acabou: bool = False
        self.winner: int | None = None

    @staticmethod
    def _make_board(rng: Random) -> PlayerBoard:
        """Cria uma board aleatorizada para um jogador."""

        w, h = BOARD_SIZE
        g = PlayerBoard(width=w, height=h)

        # alocar cada navio em posições aleatórias no tabuleiro
        #
        # FIXME: com falta de sorte, isso aqui pode demorar uma eternidade.
        for st in ShipType:
            tamanho = st.get_size()
            while True:
                casas: list[tuple[int, int]] = []

                # sortear posição inicial
                livre = rng.randint(0, w - 1)
                base = rng.randint(0, h - tamanho)

                # sortear orientação
                if rng.choice((True, False)):
                    # horizontal
                    x, y = livre, base
                    dx, dy = 0, 1
                else:
                    # vertical
                    x, y = base, livre
                    dx, dy = 1, 0

                # verificar se tem alguma colisão
                colisao = False
                for i in range(tamanho):
                    nx, ny = x + dx * i, y + dy * i
                    if g.get(nx, ny).ship is not None:
                        colisao = True
                        break
                    casas.append((nx, ny))

                if not colisao:
                    break

            for cx, cy in casas:
                g.get(cx, cy).ship = st

        return g

    @staticmethod
    def _get_enemy(player_id: int) -> int:
        # se formos colocar mais de 2 jogadores, parar de usar isso aqui...
        assert MAX_PLAYERS == 2
        return 1 if player_id == 0 else 0

    def make_game_started_response(self, player_id: int) -> GameStartedResponse:
        """Monta a informação a ser mandada a um jogador no início do jogo."""
        return {
            "type": "GAME_STARTED",
            "your_id": player_id,
            "your_board": self.grades[player_id].to_json(),
            "first_player": self.vez,
        }

    def process_shot(self, player_id: int, x: int, y: int) -> ShotResultResponse:
        """
        Processa o tiro do jogador na casa dada, e devolve uma ret que
        pode ser enviada a todos. Também altera o estado do jogo, que pode ser
        verificado externamente (a vez, se acabou, o winner etc.)

        Regras:
          - só atira quem tem a vez (senão INVALID);
          - casa já acertada ou fora do tabuleiro resulta em INVALID (não troca a vez);
          - acertando ou errando, a vez passa para o adversário;
          - se a frota do adversário acabou, o jogo termina.
        """

        ret: ShotResultResponse = {
            "type": "SHOT_RESULT",
            "result": "INVALID",
            "pos": [x, y],
            "who_shot": player_id,
            "sunk_ship": None,
            "winner": None,
            "next_player": self.vez,
        }

        w, h = BOARD_SIZE

        if self.acabou or player_id != self.vez:
            # não é a sua vez, ou o jogo acabou
            return ret

        if not (0 <= x < w and 0 <= y < h):
            # tiro fora do mapa
            return ret

        tab_inimigo = self.grades[self._get_enemy(player_id)]
        casa = tab_inimigo.get(x, y)
        if casa.has_aimed():  # já atiraram aqui
            return ret

        casa.shoot()
        # FIXME: remover cast aqui. resultante de bug no mypy (eu acho que é um
        # bug, né...)
        if cast(ShotState, casa.state) == ShotState.HIT_MISS:
            ret["result"] = "MISS"
        else:
            ret["result"] = "HIT"
            if tab_inimigo.is_ship_sunken(casa.ship):
                ret["sunk_ship"] = casa.ship.get_name()

        if tab_inimigo.is_all_sunken():
            self.acabou = True
            self.winner = player_id
            ret["winner"] = player_id
            return ret

        self.vez = self._get_enemy(player_id)
        ret["next_player"] = self.vez
        return ret
