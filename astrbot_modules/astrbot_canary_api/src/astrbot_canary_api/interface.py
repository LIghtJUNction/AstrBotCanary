from __future__ import annotations

from collections.abc import Callable, Sequence, Mapping, AsyncGenerator

from pathlib import Path
from types import TracebackType
from typing import Any, Protocol, runtime_checkable, ClassVar
from datetime import datetime

from sqlalchemy.orm import Session

from astrbot_canary_api.enums import AstrBotModuleType

from astrbot_canary_api.models import Message

#region Interfaces

#region Module
@runtime_checkable
class IAstrbotModule(Protocol):
    """Interface for Astrbot modules."""
    name: ClassVar[str]
    pypi_name: ClassVar[str]
    module_type: ClassVar[AstrBotModuleType]
    version: ClassVar[str]
    authors: ClassVar[list[str]]
    description: ClassVar[str]
    enabled: bool

    def Awake(self) -> None:
        """Called when the module is loaded."""
        ...
    def Start(self) -> None:
        """Called when the module is started."""
        ...
    def OnDestroy(self) -> None:
        """Called when the module is unloaded."""
        ...


@runtime_checkable
class IAstrbotLoaderModule(IAstrbotModule, Protocol):
    """Interface for Astrbot loader modules."""
    api_version: ClassVar[str]

    def Load(self, name: str) -> None:
        ...
    def Unload(self, name: str) -> None:
        ...
    def Reload(self, name: str) -> None:
        ...

@runtime_checkable
class IAstrbotUIModule(IAstrbotModule, Protocol):
    """Interface for Astrbot UI modules."""
    ...

#endregion

#region Paths

@runtime_checkable
class IAstrbotPaths(Protocol):
    """Interface for Astrbot path management."""

    astrbot_root: Path
    pypi_name: str
    
    @classmethod
    def root(cls, pypi_name: str) -> IAstrbotPaths:
        """ 返回模块路径根实例，用于访问模块的各类目录 """
        ...

    @property
    def config(self) -> Path:
        """ 返回模块配置目录 """
        ...

    @property
    def log(self) -> Path:
        """ 返回模块日志目录 """
        ...


#endregion
#region Config
@runtime_checkable
class IAstrbotConfigEntry(Protocol):
    """Interface for a single configuration entry."""
    pypi_name: str
    name: str
    group: str
    value: Any
    default: Any
    description: str

    @classmethod
    def bind(cls, pypi_name: str, group: str, name: str, default: Any, description: str , config_dir: Path) -> 'IAstrbotConfigEntry':
        """ 建议设置value时先从本地文件读取，不要直接使用默认值 """
        ...

    def load(self, pypi_name: str , config_dir: Path) -> None:
        """从本地文件加载配置"""
        ...

    def save(self , config_dir: Path) -> None:
        """将配置保存回本地文件"""
        ...

    def reset(self, config_dir: Path) -> None:
        """重置配置为默认值并保存"""
        ...


@runtime_checkable
class IAstrbotConfig(Protocol):
    """Interface for Astrbot configuration management."""
    _pypi_name: str
    configs: dict[str, dict[str, IAstrbotConfigEntry]]

    @classmethod
    def getConfig(cls, pypi_name: str) -> 'IAstrbotConfig':
        """获取自己的配置实例并注册到全局配置字典中"""
        ...

    def findEntry(self, group: str, name: str) -> IAstrbotConfigEntry | None:
        """找到指定组和名称的配置项，找不到返回None"""
        ...

    def bindEntry(self, entry: IAstrbotConfigEntry) -> IAstrbotConfigEntry:
        """绑定一个配置项"""
        ...



#endregion

#region database

@runtime_checkable
class IAstrbotDatabase(Protocol):
    """Interface for Astrbot database management, optimized for SQLAlchemy ORM."""
    database_url: str
    engine: Any  # sqlalchemy.engine.Engine
    session: Session | None  # sqlalchemy.orm.Session

    @classmethod
    def connect(cls, db_path: Path) -> 'IAstrbotDatabase':
        """连接数据库，返回数据库实例"""
        ...

    @classmethod
    def init_db(cls, db_path: Path, base: Any) -> None:
        """初始化数据库表结构"""
        ...

    def execute(self, query: str, params: Any = ()) -> Any:
        """执行原生SQL或ORM查询"""
        ...

    def close(self) -> None:
        """关闭数据库连接和会话"""
        ...

    def get_session(self) -> Session:
        """获取当前SQLAlchemy会话对象"""
        ...

    def transaction(self) -> Any:
        """上下文管理器/装饰器：自动提交/回滚事务
        用法：
        @db.transaction()
        def do_something(session): ...
        或 with db.transaction() as session: ...
        """
        ...

    def __enter__(self) -> 'IAstrbotDatabase':
        ...
    def __exit__(self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None
    ) -> None:
        ...
    async def __aenter__(self) -> 'IAstrbotDatabase':
        ...
    async def __aexit__(self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None
    ) -> None:
        ...


#endregion

#region MessageBus


@runtime_checkable
class IAstrbotMessageBus(Protocol):
    """消息总线接口（抽象）。

    目的：为项目提供一套可替换的消息传输抽象层（既可用 Kombu，也可用其他实现）。

    设计要点：
    - send/publish: 发布消息到指定通道（exchange/routing_key 或 topic/queue）。
    - subscribe/receive_once: 提供订阅回调或一次性接收接口，满足同步阻塞或轮询场景。
    - 实现可以选择阻塞式（drain_events）或基于回调的消费。

    注意：消息体以 dict[str, Any] 为常用格式，具体序列化策略由实现决定（JSON/pickle），跨进程请优先使用 JSON。
    """

    def send(self,
             msg: dict[str, Any],
             exchange: Any | None = None,
             routing_key: str | None = None,
             declare: list[Any] | None = None) -> None:
        """发布一条消息。

        参数：
        - msg: 要发布的消息（可 JSON 序列化的 dict）。
        - exchange: 可选，表示目标交换机/通道对象或标识符。
        - routing_key: 可选，路由键或主题名称。
        - declare: 可选，声明所需的队列/交换机列表，以确保在虚拟/内存传输中可路由。
        """
        ...

    async def async_send(self,
                         msg: dict[str, Any],
                         exchange: Any | None = None,
                         routing_key: str | None = None,
                         declare: list[Any] | None = None) -> None:
        """异步版本的 send。实现可以选择在内部使用线程池、异步客户端或直接以同步方式执行并返回。

        说明：接口不强制实现必须使用真正的异步 broker；如果底层为同步库，适配器可在内部将同步调用封装到线程池。
        """
        ...

    def publish(self, topic: str, msg: dict[str, Any]) -> None:
        """按主题/队列名直接发布消息（语义糖），等同于 send(...routing_key=topic)。"""
        ...

    async def async_publish(self, topic: str, msg: dict[str, Any]) -> None:
        """异步版本的 publish。"""
        ...

    def subscribe(self,
                  queue: str,
                  callback: Callable[[dict[str, Any], Any], None],
                  accept: list[str] | None = None) -> None:
        """注册一个回调，用于接收并处理队列中的消息。

        实现可以选择把回调立即注册并在后台处理（如果实现支持），也可以作为同步接口由调用方驱动。
        """
        ...

    async def async_subscribe(self,
                              queue: str,
                              callback: Callable[[dict[str, Any], Any], Any],
                              accept: list[str] | None = None) -> None:
        """异步订阅：回调可以是协程（async def）或普通函数。

        实现可选择在后台任务或事件循环中注册消费者以异步驱动回调。
        """
        ...

    def receive_once(self, queue: str, timeout: float | None = None) -> dict[str, Any] | None:
        """以阻塞或带超时的方式从队列接收单条消息并返回消息 body；未收到返回 None。"""
        ...

    async def async_receive_once(self, queue: str, timeout: float | None = None) -> dict[str, Any] | None:
        """异步单次接收：在异步事件循环中等待消息并返回 body 或 None。"""
        ...


    def iterate(self, queue: str, accept: list[str] | None = None, timeout: float | None = None) -> AsyncGenerator[Message, None]:
        """异步迭代器风格的持续接收：

        用法示例：
            async for msg in bus.iterate("myq"):
                try:
                    await handle(msg.body)
                    msg.ack()
                except Exception:
                    raise

        说明：实现可以在内部对同步库使用线程桥接（如 Kombu），并保证 msg.ack() 会在线程侧安全执行。
        """
        ...

    def close(self) -> None:
        """关闭内部连接/资源。"""
        ...

    async def async_close(self) -> None:
        """异步关闭资源的版本。"""
        ...


#endregion

#region TaskScheduler

# --- types and small helper protocols ---
type TaskID = str

class ResultHandleProtocol(Protocol):
    """A minimal protocol describing a task result handle / AsyncResult-like object."""
    def id(self) -> TaskID: ...
    def ready(self) -> bool: ...
    def get(self, timeout: float | None = None) -> Any: ...

class TaskNotFoundError(RuntimeError):
    """Raised when a requested task cannot be found by the scheduler.

    Attributes:
        task_id: str | None -- the id of the missing task (if known)
        reason: str | None -- optional human readable reason message
    """

    def __init__(self, task_id: str | None = None, reason: str | None = None) -> None:
        self.task_id = task_id
        self.reason = reason
        msg = "Task not found" + (f": {task_id}" if task_id else "")
        if reason:
            msg = msg + f" ({reason})"
        super().__init__(msg)

class TaskTimeoutError(TimeoutError):
    """Raised when waiting for a task result times out.

    Attributes:
        task_id: str | None -- the id of the timed-out task (if known)
        timeout: float | None -- seconds waited before timing out
    """

    def __init__(self, task_id: str | None = None, timeout: float | None = None) -> None:
        self.task_id = task_id
        self.timeout = timeout
        msg = "Task result timeout"
        if task_id:
            msg += f": {task_id}"
        if timeout is not None:
            msg += f" after {timeout}s"
        super().__init__(msg)

@runtime_checkable
class IAstrbotTaskScheduler(Protocol):
    """任务调度/函数执行接口（抽象）。

    说明：此接口用于把“可执行任务”调度到后台 worker（例如 Celery），并提供查询、撤销等操作。

    语义约定：
    - send_task 返回 TaskID 或一个 ResultHandle（实现可选择）；async_send_task 返回相同语义的 awaitable。 
    - get_result 在超时时应抛出 TaskTimeoutError（或实现选择返回 None，但需在实现文档中说明）。
    """

    def send_task(self,
                  name: str,
                  args: Sequence[Any] | None = None,
                  kwargs: Mapping[str, Any] | None = None,
                  queue: str | None = None,
                  retry: bool = False,
                  countdown: float | None = None,
                  headers: Mapping[str, Any] | None = None,
                  ) -> TaskID | ResultHandleProtocol:
        """按任务名发送任务（返回 TaskID 或 ResultHandle）。"""
        ...

    async def async_send_task(self,
                              name: str,
                              args: Sequence[Any] | None = None,
                              kwargs: Mapping[str, Any] | None = None,
                              queue: str | None = None,
                              retry: bool = False,
                              countdown: float | None = None,
                              headers: Mapping[str, Any] | None = None,
                              ) -> TaskID | ResultHandleProtocol:
        """异步发送任务的版本。"""
        ...

    def apply_async(self,
                    func: Callable[..., Any],
                    args: Sequence[Any] | None = None,
                    kwargs: Mapping[str, Any] | None = None,
                    queue: str | None = None,
                    registered_only: bool = True,
                    ) -> TaskID | ResultHandleProtocol:
        """把本地可调用提交为异步任务（实现可选择是否支持）；
        如果 registered_only=True, 未注册的可调用可能被拒绝。"""
        ...

    async def async_apply_async(self,
                                func: Callable[..., Any],
                                args: Sequence[Any] | None = None,
                                kwargs: Mapping[str, Any] | None = None,
                                queue: str | None = None,
                                registered_only: bool = True,
                                ) -> TaskID | ResultHandleProtocol:
        """异步版本的 apply_async。"""
        ...

    def schedule(self,
                 name: str,
                 eta: datetime | float | None = None,
                 cron: str | None = None,
                 args: Sequence[Any] | None = None,
                 kwargs: Mapping[str, Any] | None = None,
                 ) -> TaskID | ResultHandleProtocol:
        """安排未来执行的任务（由 eta/cron 指定时间）。

        eta 可以是 datetime（绝对时间）或 float（以秒为单位的倒计时）。
        """
        ...

    def get_result(self, task_id: TaskID, timeout: float | None = None) -> Any:
        """查询任务结果；超时应抛出 TaskTimeoutError。"""
        ...

    async def async_get_result(self, task_id: TaskID, timeout: float | None = None) -> Any:
        """异步查询任务结果。"""
        ...

    def revoke(self, task_id: TaskID, terminate: bool = False) -> None:
        """撤销任务（可选强制终止 worker 执行）。"""
        ...

    async def async_revoke(self, task_id: TaskID, terminate: bool = False) -> None:
        """异步撤销任务。"""
        ...

    def inspect_workers(self) -> Mapping[str, Any]:
        """返回当前 worker 状态的概要（实现可以返回空或有限信息）。"""
        ...

    async def async_inspect_workers(self) -> Mapping[str, Any]:
        """异步版本的 inspect_workers。"""
        ...

    def close(self) -> None:
        """释放调度器相关资源（同步）。"""
        ...

    async def async_close(self) -> None:
        """异步释放资源的版本（注意：实现可以选择实现异步或同步 close）。"""
        ...

#endregion
#endregion
#endregion