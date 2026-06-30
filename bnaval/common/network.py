from __future__ import annotations
from typing import Callable, Any, cast
from socket import socket, AF_INET, SOCK_STREAM
from threading import Thread
from queue import Queue
import json

from bnaval.common import JsonObject, JsonValue


def make_socket(addr: str, port: int) -> socket:
    """Cria um socket TCP com o endereço e porta especificados."""
    sock = socket(AF_INET, SOCK_STREAM)
    sock.bind((addr, port))
    return sock


def serve_loop(
    sock: socket,
    on_connect: Callable[[Conn], None],
    threaded: bool,
) -> None:
    """Lógica base para o loop de conexão do servidor. Roda infinitamente e,
    para cada conexão recebida, roda `on_connect` com ela."""
    sock.listen()
    while True:
        conn_sock, address = sock.accept()
        print(f"Conectado a {address}")
        conn = Conn(conn_sock)

        def wrapper() -> None:
            on_connect(conn)

        if threaded:
            Thread(target=wrapper).start()
        else:
            wrapper()


class Conn:
    """Abstração sobre uma conexão utilizada pelo jogo. Troca de dados é feita em JSON."""

    def __init__(self, sock: socket) -> None:
        self._sock = sock
        self._is_closed = False

    def close(self) -> None:
        if self._is_closed:
            return
        print(f"CLOSING SOCKET {self._sock}")
        self._sock.close()
        self._is_closed = True

    def is_closed(self) -> bool:
        return self._is_closed

    def __enter__(self) -> Conn:
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()

    def send(self, data: JsonValue) -> None:
        # codificar como um inteiro de 32 bits, big-endian; depois mandar os dados
        buf = bytearray()
        data_s = json.dumps(data)

        buf.extend(len(data_s).to_bytes(8, "big"))
        buf.extend(bytes(data_s, encoding="utf-8"))
        # print(f"Conn.send(): sending...")
        self._sock.send(buf)

        # print("Conn.send(): sent!")

    def recv(self) -> JsonValue:
        # print("Conn.recv(): waiting...")
        buf = bytearray()
        self._recv_exactly(self._sock, 8, buf)
        n = int.from_bytes(buf, "big")

        buf = bytearray()
        self._recv_exactly(self._sock, n, buf)
        bufd = buf.decode()
        # print(f"Conn.recv(): got something")
        return cast("JsonValue", json.loads(bufd))

    def recv_dict(self) -> JsonObject:
        ret = self.recv()
        assert isinstance(ret, dict)
        return ret

    @staticmethod
    def _recv_exactly(sock: socket, n: int, target: bytearray) -> None:
        n_to_read = n
        while n_to_read > 0:
            got = sock.recv(n_to_read)
            if got == b"":
                raise ConnectionError("conexão terminada pelo peer")
            target.extend(got)
            n_to_read -= len(got)


class MultiConn:
    """Classe para se comunicar com múltiplas conexões ao mesmo tempo."""

    def __init__(self, conns: list[Conn]) -> None:
        self._conns = conns
        self._send_queues = [Queue[JsonValue]() for _ in conns]
        self._recv_queue = Queue[tuple[int, JsonValue]]()
        self._threads = list[Thread]()

        for ci, c in enumerate(conns):
            q = self._send_queues[ci]
            c = self._conns[ci]

            def send_thread(ci: int, c: Conn, q: Queue[JsonValue]) -> None:
                while True:
                    val = q.get()  # pegar o valor
                    # print(f"WILL SEND {val} to #{ci} ({c})")
                    try:
                        c.send(val)  # e enviar ele para a conexão
                    except ConnectionError:
                        # XXX: não é o melhor lugar para colocar isso, mas serve por agora
                        self._recv_queue.put((ci, {"type": "DISCONNECTED"}))
                        break

            def recv_thread(ci: int, c: Conn) -> None:
                while True:
                    try:
                        val = c.recv()
                    except ConnectionError:
                        # TODO: não é o melhor lugar para colocar isso, mas serve por agora
                        self._recv_queue.put((ci, {"type": "DISCONNECTED"}))
                        break
                    # print(f"Got value for #{ci}: {val}")
                    self._recv_queue.put((ci, val))

            t1 = Thread(target=send_thread, args=(ci, c, q))
            t2 = Thread(target=recv_thread, args=(ci, c))
            t1.start()
            t2.start()
            self._threads.extend((t1, t2))

    def __enter__(self) -> MultiConn:
        return self

    def __exit__(self, *args: Any) -> None:
        # TODO: parar todos os threads

        for c in self._conns:
            c.close()

    def send(self, id: int, data: JsonValue) -> None:
        """Envia dados para uma conexão específica."""
        self._send_queues[id].put(data)

    def send_all(self, data: JsonValue) -> None:
        """Envia dados para todas as conexões."""
        for q in self._send_queues:
            q.put(data)

    def recv(self) -> tuple[int, JsonValue]:
        """Recebe dados de alguma conexão. Retorna o índice e os dados."""
        return self._recv_queue.get()

    def recv_dict(self) -> tuple[int, JsonObject]:
        """Recebe dados de alguma conexão, em forma de dicionário. Retorna o índice e os dados."""
        ci, obj = self._recv_queue.get()
        assert isinstance(obj, dict), f"expected a json dict, got {obj}"
        return (ci, obj)
