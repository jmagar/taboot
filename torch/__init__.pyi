from typing import Any, ContextManager


class _CudaModule:
    def is_available(self) -> bool: ...


cuda: _CudaModule


def inference_mode() -> ContextManager[None]: ...


class Tensor:
    def tolist(self) -> list[float]: ...
