from typing import Any, Callable, TypeVar

T = TypeVar("T")


class RetryCallState: ...


def retry(*args: Any, **kwargs: Any) -> Callable[[Callable[..., T]], Callable[..., T]]: ...


def retry_if_exception_type(exc_types: Any) -> Any: ...


def stop_after_attempt(attempts: int) -> Any: ...


def wait_exponential(*, multiplier: int = ..., min: int = ..., max: int = ...) -> Any: ...


def before_sleep_log(logger: Any, level: int) -> Any: ...

