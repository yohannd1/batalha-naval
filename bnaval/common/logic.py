"""Arquivo com lógica comum ao client e o servidor."""

from __future__ import annotations
from typing import TypeAlias, Any, Iterator
from dataclasses import dataclass
from enum import Enum

from bnaval.common import JsonObject, AssertVal


class ShipType(Enum):
    _value_: tuple[str, int]  # nome, tamanho
    PORTA_AVIOES = ("Porta-Aviões", 5)
    ENCOURACADO = ("Encouraçado", 4)
    CRUZADOR = ("Cruzador", 3)
    SUBMARINO = ("Submarino", 3)
    CONTRATORPEDEIRO = ("Contratorpedeiro", 2)

    @staticmethod
    def from_name(name: str) -> ShipType:
        for st in ShipType:
            if st.value[0] == name:
                return st
        raise ValueError(f"nenhum tipo de navio tem o nome {repr(name)}")

    def get_name(self) -> str:
        return self.value[0]

    def get_size(self) -> int:
        return self.value[1]


class ShotState(Enum):
    CLEAN = 0  # nunca foi atirado aqui
    HIT_OK = 1  # atirou e destruiu algo
    HIT_MISS = 2  # atirou mas não tinha nada


@dataclass
class Cell:
    ship: ShipType | None = None
    """O tipo de navio ali, ou None se for água."""

    state: ShotState = ShotState.CLEAN

    def has_aimed(self) -> bool:
        return self.state in (ShotState.HIT_OK, ShotState.HIT_MISS)

    def shoot(self) -> None:
        if self.ship is not None:
            self.state = ShotState.HIT_OK
        else:
            self.state = ShotState.HIT_MISS

    def to_json(self) -> JsonObject:
        ship = None if self.ship is None else self.ship.get_name()
        return {"ship": ship}

    @staticmethod
    def from_json(d: JsonObject) -> Cell:
        assert isinstance(d, dict)

        if d["ship"] is None:
            ship = None
        else:
            assert isinstance(d["ship"], str)
            ship = ShipType.from_name(d["ship"])
        return Cell(ship=ship)


class PlayerBoard:
    """Representa a grade de um jogador."""

    def __init__(self, width: int, height: int, data: list[Cell] | None = None) -> None:
        self.width = width
        self.height = height

        if data is not None:
            assert len(data) == width * height
            self._data = data
        else:
            self._data = [
                Cell() for _ in range(width * height)
            ]  # representação row-first

    def get(self, x: int, y: int) -> Any:
        return self._data[y * self.width + x]

    def set(self, x: int, y: int, val: Any) -> Any:
        self._data[y * self.width + x] = val

    def items(self) -> Iterator[tuple[int, int, Cell]]:
        w = self.width
        return ((i % w, i // w, val) for (i, val) in enumerate(self._data))

    def is_all_sunken(self) -> bool:
        """Verifica se, para todas as casas, ou ela está vazia ou ela tem um navio afundado."""
        return all(x.ship is None or x.has_aimed() for (_, _, x) in self.items())

    def is_ship_sunken(self, sht: ShipType) -> bool:
        """Verifica se um navio está completamente afundado, pelo seu tipo.
        Se ele não existe, retorna verdadeiro também."""

        def pred(x: Cell) -> bool:
            if x.ship != sht:
                return True
            return x.has_aimed()

        return all(pred(x) for (_, _, x) in self.items())

    def to_json(self) -> JsonObject:
        return {
            "width": self.width,
            "height": self.height,
            "cells": [cell.to_json() for cell in self._data],  # row-first
        }

    @staticmethod
    def from_json(d: JsonObject) -> PlayerBoard:
        width = AssertVal.int_(d["width"])
        height = AssertVal.int_(d["height"])
        cells = d["cells"]
        assert isinstance(cells, list)
        return PlayerBoard(
            width=width,
            height=height,
            data=[Cell.from_json(AssertVal.json_object(c)) for c in cells],
        )


def _logic_test() -> None:
    """Alguns testes de consistência..."""

    g = PlayerBoard(width=2, height=2)
    assert g.is_ship_sunken(ShipType.PORTA_AVIOES)
    g.set(0, 0, Cell(ship=ShipType.PORTA_AVIOES))
    assert not g.is_ship_sunken(ShipType.PORTA_AVIOES)
    g.get(0, 0).state = ShotState.HIT_OK
    assert g.is_ship_sunken(ShipType.PORTA_AVIOES)

    ls = list(g.items())
    assert ls[0][0:2] == (0, 0)
    assert ls[1][0:2] == (1, 0)
    assert ls[2][0:2] == (0, 1)
    assert ls[3][0:2] == (1, 1)


_logic_test()
