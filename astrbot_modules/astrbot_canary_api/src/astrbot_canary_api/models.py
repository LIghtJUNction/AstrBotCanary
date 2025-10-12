from collections.abc import Callable
from typing import Any
from pydantic import BaseModel

class Message(BaseModel):
    """轻量消息容器，包含 body 与可选元数据，以及 ack/reject 的委托。
    注意：ack/reject 的具体执行上下文由实现决定；若实现将阻塞驱动放到后台线程，
    ack 方法会把请求发送回后台线程执行，用户无需直接访问底层 kombu message 对象。
    """
    body: dict[str, Any]
    headers: dict[str, Any] | None = None
    properties: dict[str, Any] | None = None
    delivery_info: Any | None = None
    _ack: Callable[[], None] | None = None
    _reject: Callable[[bool], None] | None = None
    def ack(self) -> None:
        if self._ack is None:
            raise RuntimeError("ack not available for this Message")
        self._ack()
    def reject(self, requeue: bool = False) -> None:
        if self._reject is None:
            raise RuntimeError("reject not available for this Message")
        self._reject(requeue)