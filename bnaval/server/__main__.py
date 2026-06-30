"""
Módulo principal do servidor, envolvendo a lógica de criação de salas e a
comunicação com os clients.
"""

from __future__ import annotations

from dataclasses import dataclass
from threading import Thread, Lock
from random import Random
from string import ascii_lowercase
from queue import Queue
from socket import socket
from typing import cast

from bnaval.server.game import GameState
from bnaval.common import JsonObject, JsonValue, AssertVal
from bnaval.common.config import SERVER_ADDR, SERVER_PORT, MAX_PLAYERS
from bnaval.common.network import make_socket, serve_loop, Conn, MultiConn


class Room:
    name: str
    players: list[Conn]
    is_open: bool
    finished_queue: Queue[str]

    def __init__(self, name: str) -> None:
        self.name = name
        self.players = []
        self.is_open = True
        self.finished_queue = Queue()


class Server:
    rooms: dict[str, Room]

    def __init__(self, addr: str, port: int) -> None:
        self.rng = Random()
        self.sock = make_socket(SERVER_ADDR, SERVER_PORT)
        print(f"Rodando servidor em {SERVER_ADDR}:{SERVER_PORT}")
        self.rooms = {}
        self.room_lock = Lock()

    def main(self) -> None:
        with self.sock:
            serve_loop(self.sock, self.on_connect, threaded=True)

    def on_connect(self, conn: Conn) -> None:
        print(f"Connection started! {conn=}")

        # ao início de toda conexão, não há nada muito a ser feito, a não ser aguardar o início de uma partida.
        while not conn.is_closed():
            msg = conn.recv_dict()
            # print(f"Server got {msg=}")

            if msg["type"] == "ROOM_CREATE":
                room = self.make_room()
                room.players.append(conn)

                # indicar o nome da sala, e que deve esperar
                conn.send({"type": "ROOM_CREATED", "data": room.name})

                return  # fechar o thread; essa conexão vai ser cuidada depois

            elif msg["type"] == "ROOM_JOIN":
                name = msg["data"]
                assert isinstance(name, str)

                gs: GameState | None = None

                with self.room_lock:
                    if name not in self.rooms:
                        conn.send({"type": "ROOM_INVALID"})  # sala inexistente
                        continue

                    room = self.rooms[name]
                    if len(room.players) >= MAX_PLAYERS:
                        conn.send({"type": "ROOM_FULL"})  # sala cheia
                        continue

                    # indicar que deve esperar (incluindo o último jogador)
                    conn.send({"type": "ROOM_WAIT"})
                    room.players.append(conn)

                    if len(room.players) >= MAX_PLAYERS:
                        # indicar que a partida deve começar (fora do escopo do lock...)
                        gs = GameState(self.rng)
                    else:
                        return  # fechar o thread; essa conexão vai ser cuidada mais à frente

                if gs is not None:
                    # começar a partida!
                    self.run_match(gs, room.players)
                    for _ in room.players:
                        room.finished_queue.put("DONE")
                    with self.room_lock:
                        del self.rooms[name]
            else:
                print(f"Mensagem recebida desconhecida: {repr(msg)}")

    def _make_room_name(self) -> str:
        return "".join(self.rng.choice(ascii_lowercase) for _ in range(6))

    def make_room(self) -> Room:
        with self.room_lock:
            name = self._make_room_name()
            while name in self.rooms:
                name = self._make_room_name()
            r = Room(name)
            self.rooms[name] = r
            return r

    def run_match(self, gs: GameState, players: list[Conn]) -> None:
        print(f"Partida iniciada!")

        with MultiConn(players) as mc:
            nplayers = len(players)

            # inicialmente, mandar o board para cada jogador
            print("Enviando board para todos...")
            for ci in range(nplayers):
                mc.send(ci, cast(JsonObject, gs.make_game_started_response(ci)))
            print("...pronto.")

            while True:
                ci, msg = mc.recv_dict()
                typ = msg["type"]

                if typ == "DISCONNECTED":
                    # repassar a mensagem para todos - a conexão terminou
                    for i in range(nplayers):
                        mc.send(ci, msg)
                    break
                elif typ == "SHOOT_AT":
                    x, y = AssertVal.list_int(msg["position"])
                    res = gs.process_shot(ci, x, y)
                    if res["result"] == "INVALID":
                        # só mandar para ele
                        mc.send(ci, cast(JsonObject, res))
                    else:
                        # mandar parat odos
                        for i in range(nplayers):
                            mc.send(i, cast(JsonObject, res))
                else:
                    print(f"Warning: (client #{ci}) skipping unknown message: {msg}")


if __name__ == "__main__":
    sv = Server(SERVER_ADDR, SERVER_PORT)
    sv.main()
