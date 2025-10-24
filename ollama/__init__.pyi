from typing import Any, TypedDict


class ChatMessage(TypedDict):
    role: str
    content: str


class AsyncClient:
    async def chat(self, *, model: str, messages: list[ChatMessage], options: dict[str, Any]) -> dict[str, Any]: ...
