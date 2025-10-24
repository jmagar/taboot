from typing import Any


class Encoding:
    def encode(self, text: str) -> list[int]: ...


def get_encoding(name: str) -> Encoding: ...

