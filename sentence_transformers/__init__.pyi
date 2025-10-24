from typing import Any, Sequence


class Tokenizer:
    pad_token: str | None
    pad_token_id: int | None
    eos_token: str | None
    eos_token_id: int | None


class _Model:
    config: Any


class CrossEncoder:
    tokenizer: Tokenizer
    model: _Model

    def __init__(self, *args: Any, **kwargs: Any) -> None: ...
    def predict(self, pairs: Sequence[Sequence[str]], *, batch_size: int, show_progress_bar: bool = ...) -> Sequence[float]: ...
