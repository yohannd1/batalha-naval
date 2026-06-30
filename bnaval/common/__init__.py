from __future__ import annotations
from typing import TypeAlias, Any, cast

JsonValue: TypeAlias = "None | str | int | float | bool | list[JsonValue] | JsonObject"
JsonObject: TypeAlias = "dict[str, JsonValue]"


class AssertVal:
    @staticmethod
    def json_object(x: JsonValue) -> JsonObject:
        assert isinstance(x, dict)
        return x

    @staticmethod
    def str_(val: JsonValue) -> str:
        assert isinstance(val, str)
        return val

    @staticmethod
    def int_(val: JsonValue) -> int:
        assert isinstance(val, int)
        return val

    @staticmethod
    def bool_(val: JsonValue) -> bool:
        assert isinstance(val, bool)
        return val

    @staticmethod
    def list_any(val: JsonValue) -> list[Any]:
        assert isinstance(val, list)
        return val

    @staticmethod
    def list_int(val: JsonValue) -> list[int]:
        assert isinstance(val, list)
        for x in val:
            assert isinstance(x, int)
        return cast("list[int]", val)
