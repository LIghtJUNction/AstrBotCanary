from collections.abc import Callable
from typing import Any, cast
import socket
from kombu import Connection, Exchange, Queue, Producer  # type: ignore
# https://github.com/celery/kombu/issues/1511
from astrbot_canary_api.interface import IAstrbotMessageBus

class AstrbotMessageBus(IAstrbotMessageBus):
    """基于 Kombu 的简易单线程消息总线封装。
    行为与契约：
    - send(msg) 将一个可被 JSON 序列化的 dict 发布到配置的 exchange/routing key。
    - receive(callback) 进入阻塞循环，等待消息到达并对每条消息调用 `callback(body, message)`。
        回调负责确认消息（调用 message.ack()）。
    - 本类刻意不启动线程或后台任务；采用 Kombu 的同步 drain_events 循环。
    输入/输出：
    - url: kombu 连接 URL（例如 "memory://" 或 "amqp://..."）
    - send: dict[str, Any] -> None
    - receive: Callable[[dict[str, Any], object], None] -> None（阻塞）
    """

    def __new__(cls, url: str = "memory://") -> "AstrbotMessageBus":
        # 类级别单例：保证同一个类只会创建一次实例
        if getattr(cls, "_instance", None) is None:
            cls._instance = super().__new__(cls)
        return cast(AstrbotMessageBus, cls._instance)

    def __init__(self, url: str = "memory://") -> None:
        # 防止在单例模式下多次 __init__ 重复初始化
        if getattr(self, "_singleton_initialized", False):
            return

        self.url: str = url
        self.conn: Connection = Connection(self.url)
        self.exchange: Exchange = Exchange("astrbot", type="direct")
        self.queue: Queue = Queue("astrbot_queue", self.exchange, routing_key="astrbot_key")

        self._singleton_initialized = True

    def send(self,
         msg: dict[str, Any],
         exchange: Exchange | None = None,
         routing_key: str | None = None,
         declare: list[object] | None = None) -> None:
        """Publish a message to the configured exchange and routing key.

        This opens a connection, publishes, and closes the connection.
        """
        exch = exchange or self.exchange
        rk = routing_key or "astrbot_key"
        declare = declare or [self.queue]
        with self.conn:
            producer = self.conn.Producer(serializer="json")  # type: ignore
            producer.publish( # type: ignore
                msg,
                exchange=exch,
                routing_key=rk,
                declare=declare,
                serializer="json",
            )

    def publish(self, topic: str, msg: dict[str, Any]) -> None:
        """按主题/队列名发布消息的快捷方法（语义糖）。"""
        self.send(msg, routing_key=topic)

    def subscribe(self,
                  queue: str,
                  callback: Callable[[dict[str, Any], object], None],
                  accept: list[str] | None = None) -> None:
        """注册并阻塞式启动一个消费者，直到回调被触发或超时。

        说明：这是一个同步阻塞的简单实现；复杂场景可在外部创建线程或事件循环来托管消费者。
        """
        with self.conn:
            q = Queue(queue, exchange=self.exchange, routing_key=queue)
            q(self.conn).declare()  # type: ignore
            with self.conn.Consumer(q, callbacks=[callback], accept=accept or ["json"]):  # type: ignore
                # 这里进行一次 drain_events 以触发回调（适合演示/测试）
                try:
                    self.conn.drain_events(timeout=5.0)  # type: ignore
                except Exception:
                    # 超时或其它连接问题，直接返回
                    return

    def receive_once(self, queue: str, timeout: float | None = None) -> dict[str, Any] | None:
        """从指定队列接收一条消息并返回 body，未收到返回 None。"""
        result: dict[str, Any] | None = None

        def _cb(body: dict[str, Any], message: object) -> None:
            nonlocal result
            result = body
            try:
                message.ack()  # type: ignore
            except Exception:
                pass

        with self.conn:
            q = Queue(queue, exchange=self.exchange, routing_key=queue)
            q(self.conn).declare()  # type: ignore
            with self.conn.Consumer(q, callbacks=[_cb], accept=["json"]):  # type: ignore
                try:
                    if timeout is None:
                        self.conn.drain_events()  # type: ignore
                    else:
                        self.conn.drain_events(timeout=timeout)  # type: ignore
                except Exception:
                    return None

        return result

    def close(self) -> None:
        """释放连接资源（如果需要）。"""
        try:
            self.conn.close()
        except Exception:
            pass

    def receive(self, callback: Callable[[dict[str, Any], object], None], timeout: float | None = None) -> None:
        """Start consuming messages and call callback for each message.

        This method blocks, using `connection.drain_events()` internally. If
        `timeout` is provided it will pass it to drain_events to periodically
        wake up (useful for graceful shutdowns).
        """
        with self.conn:
            # 确保声明队列/交换以便消息能被路由
            self.queue(self.conn).declare() # type: ignore
            with self.conn.Consumer(self.queue, callbacks=[callback], accept=["json"]): # type: ignore
                print("等待消息...（按 Ctrl-C 停止）")
                while True:
                    # drain_events will block until a message arrives or timeout
                    try:
                        if timeout is None:
                            self.conn.drain_events()  # type: ignore
                        else:
                            self.conn.drain_events(timeout=timeout)  # type: ignore
                    except socket.timeout:
                        # 在超时时间内没有收到消息；优雅返回给调用方，由上层决定下一步操作。
                        print("接收超时（无消息）")
                        return

    @classmethod
    def getBus(cls, url: str = "memory://") -> "AstrbotMessageBus":
        # 返回类级单例（若尚未创建则使用 url 构造）
        if getattr(cls, "_instance", None) is None:
            cls._instance = cls(url)
        return cast(AstrbotMessageBus, cls._instance)

    @classmethod
    def resetBus(cls) -> None:
        """关闭并清除类级单例（用于测试或需要重连时）。"""
        inst = getattr(cls, "_instance", None)
        if inst is not None:
            try:
                inst.close()
            except Exception:
                pass
        cls._instance = None


if __name__ == "__main__":
    # 示例 1：默认通道（使用类内默认 exchange 和 routing_key）
    print("示例 1：使用默认通道（exchange='astrbot', routing_key='astrbot_key'）")
    bus_default: AstrbotMessageBus = AstrbotMessageBus.getBus("memory://")

    def cb_default(body: dict[str, Any], message: object) -> None:
        print(f"[默认通道] 收到消息: {body}")
        try:
            message.ack()  # type: ignore
        except Exception:
            pass

    bus_default.send({"msg": "from default"})
    try:
        bus_default.receive(cb_default, timeout=2.0)
    except KeyboardInterrupt:
        print("示例 1 已停止")

    # 示例 2：自定义通道（在运行时指定 exchange 与 routing_key）
    print("\n示例 2：自定义通道（exchange='other', routing_key='other_key'）")
    bus_custom: AstrbotMessageBus = AstrbotMessageBus.getBus("memory://")
    other_exchange = Exchange("other", type="direct")
    other_queue = Queue("other_q", other_exchange, routing_key="other_key")

    def cb_other(body: dict[str, Any], message: object) -> None:
        print(f"[自定义通道] 收到消息: {body}")
        try:
            message.ack()  # type: ignore
        except Exception:
            pass

    # 在内存传输中，发布者和消费者必须都声明相同的队列/交换。
    bus_custom.send({"msg": "from other"}, exchange=other_exchange, routing_key="other_key", declare=[other_queue])
    try:
        # 使用与发布者相同的队列来接收消息
        with bus_custom.conn:
            other_queue(bus_custom.conn).declare()  # type: ignore
            with bus_custom.conn.Consumer(other_queue, callbacks=[cb_other], accept=["json"]):  # type: ignore
                print("等待自定义通道消息...（按 Ctrl-C 停止）")
                try:
                    bus_custom.conn.drain_events(timeout=2.0)  # type: ignore
                except socket.timeout:
                    print("自定义通道接收超时（无消息）")
    except KeyboardInterrupt:
        print("示例 2 已停止")