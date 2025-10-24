from typing import Any, ClassVar


class SettingsConfigDict(dict[str, Any]): ...


class BaseSettings:
    model_config: ClassVar[Any]

    def __init__(self, *args: Any, **kwargs: Any) -> None: ...
    def model_post_init(self, __context: Any) -> None: ...

