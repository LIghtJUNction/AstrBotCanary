from __future__ import annotations
from collections.abc import AsyncGenerator, Callable
from typing import Any, cast
import socket
import threading
import queue as _threading_queue

from kombu import Connection, Exchange, Queue  # type: ignore
# https://github.com/celery/kombu/issues/1511
# 这是由于 kombu 内部annotation不完善导致的类型检查报错，
# 因此使用# type: ignore 避免 类型检查报错，其余情况禁止使用# type: ignore
import anyio
from anyio import to_thread
import inspect


from logging import Logger , getLogger

from astrbot_canary_api.interface import IAstrbotMessageBus
from astrbot_canary_api.models import Message
logger: Logger = getLogger("astrbot_canary_api.msgbus")

__all__ = ["AstrbotMessageBus"]
class AstrbotMessageBus(IAstrbotMessageBus):
    """Kombu-backed message bus adapter with async iterator support.

    - 同步核心使用 Kombu (Connection/Producer/Consumer)
    - 为异步使用提供 anyio-based wrappers 和一个 async iterator `iterate`
    - 异常原则：库层不吞掉重要异常（除非是 iterate 的内部 loop 中用于保持持续接收的 socket.timeout），
      其它异常会传播给调用方。
    
    查看交互式文档：/examples/*msgbus_*.ipynb
    """
    def __new__(cls, url: str = "memory://astrbot") -> AstrbotMessageBus:
        if getattr(cls, "_instance", None) is None:
            cls._instance = super().__new__(cls)
        return cast(AstrbotMessageBus, cls._instance)

    def __init__(self, url: str = "memory://astrbot") -> None:
        if getattr(self, "_singleton_initialized", False):
            return
        self.url: str = url
        self.conn: Connection = Connection(self.url)
        self.exchange: Exchange = Exchange("astrbot", type="direct")
        self.queue: Queue = Queue("astrbot_queue", self.exchange, routing_key="astrbot_key")
        self._singleton_initialized = True

    # --- publishing ---
    def send(self, msg: dict[str, Any], exchange: Exchange | None = None,
             routing_key: str | None = None, declare: list[object] | None = None) -> None:
        exch = exchange or self.exchange
        rk = routing_key or "astrbot_key"
        declare = declare or [self.queue]
        with self.conn:
            producer = self.conn.Producer(serializer="json")  # type: ignore
            producer.publish(  # type: ignore
                msg,
                exchange=exch,
                routing_key=rk,
                declare=declare,
                serializer="json",
            )

    def publish(self, topic: str, msg: dict[str, Any]) -> None:
        self.send(msg, routing_key=topic)

    async def async_send(self, msg: dict[str, Any], exchange: Exchange | None = None,
                         routing_key: str | None = None, declare: list[object] | None = None) -> None:
        await to_thread.run_sync(self.send, msg, exchange, routing_key, declare)  # type: ignore

    async def async_publish(self, topic: str, msg: dict[str, Any]) -> None:
        await self.async_send(msg, routing_key=topic)

    # --- subscribe / receive once ---
    def subscribe(self, queue: str, callback: Callable[[dict[str, Any], object], None],
                  accept: list[str] | None = None) -> None:
        with self.conn:
            q = Queue(queue, exchange=self.exchange, routing_key=queue)
            q(self.conn).declare()  # type: ignore
            with self.conn.Consumer(q, callbacks=[callback], accept=accept or ["json"]):  # type: ignore
                # drain_events 会在超时时抛出 socket.timeout，库层不吞异常
                self.conn.drain_events(timeout=5.0)  # type: ignore

    async def async_subscribe(self, queue: str, callback: Callable[[dict[str, Any], object], None],
                              accept: list[str] | None = None) -> None:
        def _bridge_cb(body: dict[str, Any], message: object) -> None:
            # 调度回调到事件循环；如回调抛异常则向上抛出（在线程内）
            if inspect.iscoroutinefunction(callback):
                anyio.from_thread.run(callback, body, message)  # type: ignore
            else:
                anyio.from_thread.run_sync(callback, body, message)  # type: ignore
            # ack 交给调用方的回调执行以保持语义一致
            message.ack()  # type: ignore

        await to_thread.run_sync(self.subscribe, queue, _bridge_cb, accept)  # type: ignore

    def receive_once(self, queue: str, timeout: float | None = None) -> dict[str, Any] | None:
        result: dict[str, Any] | None = None

        def _cb(body: dict[str, Any], message: object) -> None:
            nonlocal result
            result = body
            message.ack()  # type: ignore

        with self.conn:
            q = Queue(queue, exchange=self.exchange, routing_key=queue)
            q(self.conn).declare()  # type: ignore
            with self.conn.Consumer(q, callbacks=[_cb], accept=["json"]):  # type: ignore
                if timeout is None:
                    self.conn.drain_events()  # type: ignore
                else:
                    self.conn.drain_events(timeout=timeout)  # type: ignore

        return result

    async def async_receive_once(self, queue: str, timeout: float | None = None) -> dict[str, Any] | None:
        return await to_thread.run_sync(self.receive_once, queue, timeout)  # type: ignore

    # --- async iterator (continuous receive) ---
    async def iterate(self, queue: str, accept: list[str] | None = None, timeout: float | None = None) -> AsyncGenerator[Message, None]:
        msg_q: _threading_queue.Queue[tuple[dict[str, Any], object]] = _threading_queue.Queue()
        ack_q: _threading_queue.Queue[tuple[str, tuple[Any, ...]]] = _threading_queue.Queue()
        stop_event = threading.Event()

        def _producer() -> None:
            q = Queue(queue, exchange=self.exchange, routing_key=queue)
            q(self.conn).declare()  # type: ignore

            def _on_msg(body: dict[str, Any], message: object) -> None:
                msg_q.put((body, message))

            with self.conn:
                with self.conn.Consumer(q, callbacks=[_on_msg], accept=accept or ["json"]):  # type: ignore
                    while not stop_event.is_set():
                        # 允许超时作为常态以便检测 stop_event
                        try:
                            if timeout is None:
                                self.conn.drain_events(timeout=1.0)  # type: ignore
                            else:
                                self.conn.drain_events(timeout=timeout)  # type: ignore
                        except socket.timeout:
                            # 超时用于轮询控制，继续循环
                            pass

                        # 执行 ack/reject 请求（非阻塞）
                        while not ack_q.empty():
                            action, args = ack_q.get_nowait()
                            try:
                                if action == "ack":
                                    args[0].ack()  # type: ignore
                                elif action == "reject":
                                    args[0].reject(args[1])  # type: ignore
                            except Exception:
                                # 让异常在后台线程表面化；上层可在 iterate 中检测
                                raise

        thread = threading.Thread(target=_producer, daemon=True)
        thread.start()

        try:
            while True:
                # 从线程队列取数据；使用命名本地函数以便类型检查器能推断返回类型
                def _get_from_queue() -> tuple[dict[str, Any], object]:
                    return msg_q.get()

                raw: tuple[dict[str, Any], object] = await to_thread.run_sync(_get_from_queue)  # type: ignore
                body: dict[str, Any] = raw[0]
                message: object = raw[1]

                # 明确的调度器：把操作放入 ack_q，由后台线程执行
                def _schedule_ack(msg_obj: object) -> None:
                    ack_q.put(("ack", (msg_obj,)))

                def _schedule_reject(msg_obj: object, requeue: bool = False) -> None:
                    ack_q.put(("reject", (msg_obj, requeue)))

                # 在事件循环中调用的包装函数（它会把请求传回后台线程的 ack_q）
                def _ack_callable() -> None:
                    to_thread.run_sync(_schedule_ack, message)  # type: ignore

                def _reject_callable(requeue: bool = False) -> None:
                    to_thread.run_sync(_schedule_reject, message, requeue)  # type: ignore

                # 构建 Pydantic Message 实例并显式注解类型
                msg: Message = Message(
                    body=body,
                    headers=getattr(message, "headers", None),
                    properties=getattr(message, "properties", None),
                    delivery_info=getattr(message, "delivery_info", None),
                    _ack=_ack_callable,
                    _reject=_reject_callable,
                )

                yield msg

        finally:
            stop_event.set()
            # 等待后台线程退出（在后台线程里会定期检查 stop_event）
            await to_thread.run_sync(thread.join, 0.1)  # type: ignore

    # --- closing / lifecycle ---
    def close(self) -> None:
        self.conn.close()

    async def async_close(self) -> None:
        await to_thread.run_sync(self.close)  # type: ignore

    @classmethod
    def getBus(cls, url: str = "memory://astrbot") -> AstrbotMessageBus:
        if getattr(cls, "_instance", None) is None:
            cls._instance = cls(url)
        return cast(AstrbotMessageBus, cls._instance)

    @classmethod
    def resetBus(cls) -> None:
        inst = getattr(cls, "_instance", None)
        if inst is not None:
            inst.close()
        cls._instance = None
