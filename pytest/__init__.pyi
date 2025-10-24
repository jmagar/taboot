from collections.abc import Callable
from typing import Any, Generic, TypeVar

_F = TypeVar("_F", bound=Callable[..., Any])


class MarkDecorator(Generic[_F]):
    def __call__(self, func: _F, /) -> _F: ...
    def __getattr__(self, name: str) -> MarkDecorator[_F]: ...
    def with_args(self, *args: Any, **kwargs: Any) -> MarkDecorator[_F]: ...


class MarkGenerator:
    def __call__(self, *args: Any, **kwargs: Any) -> MarkDecorator[Any]: ...
    def __getattr__(self, name: str) -> MarkDecorator[Any]: ...


mark: MarkGenerator


def fixture(*args: Any, **kwargs: Any) -> Callable[[_F], _F]: ...


class RaisesContext:
    def __enter__(self) -> Any: ...
    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> bool: ...


def raises(*args: Any, **kwargs: Any) -> RaisesContext: ...


class _SkipModule:
    def __call__(self, reason: str | None = ...) -> None: ...


skip = _SkipModule()


class _FailModule:
    def __call__(self, msg: str = ...) -> None: ...


fail = _FailModule()


class Item: ...


class Session: ...


class Config: ...


class FixtureRequest:
    app: Any
    config: Config
