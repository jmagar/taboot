from typing import Any, Callable, TypeVar


F = TypeVar("F", bound=Callable[..., Any])


class Typer:
    def __init__(self, *args: Any, **kwargs: Any) -> None: ...
    def command(self, *args: Any, **kwargs: Any) -> Callable[[F], F]: ...
    def add_typer(self, app: "Typer", *args: Any, **kwargs: Any) -> None: ...
    def __call__(self, *args: Any, **kwargs: Any) -> None: ...


def Argument(*args: Any, **kwargs: Any) -> Any: ...


def Option(*args: Any, **kwargs: Any) -> Any: ...


class Exit(Exception):
    code: int

    def __init__(self, code: int = ...) -> None: ...


class BadParameter(Exception):
    def __init__(self, message: str) -> None: ...
