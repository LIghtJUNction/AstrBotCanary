"""Broker configuration helpers and a central factory for Astrbot brokers.

This module centralizes broker config models and a helper `AstrbotBrokers` that
constructs a Taskiq-compatible broker based on `AstrbotBrokerConfig`.

It supports:
- InMemory
- Redis (taskiq_redis)
- RabbitMQ (taskiq_aio_pika)
- ZeroMQ (taskiq.brokers.zmq_broker)
- NATS (taskiq_nats) with optional JetStream modes (push/pull)
"""

from __future__ import annotations
import inspect

from pydantic import AmqpDsn, BaseModel, Field, PostgresDsn, RedisDsn
from taskiq import InMemoryBroker, ZeroMQBroker
from taskiq_aio_pika import AioPikaBroker
from taskiq_nats import NatsBroker, PullBasedJetStreamBroker, PushBasedJetStreamBroker
from taskiq_redis import RedisStreamBroker
from astrbot_canary_api.types import BROKER_TYPE
from astrbot_canary_api import AstrbotBrokerType

# 开发者必读：
# https://taskiq-python.github.io/available-components/brokers.html


class RedisBrokerConfig(BaseModel):
    redis_url: RedisDsn = Field(..., description="Redis 连接 URL")

class RabbitmqBrokerConfig(BaseModel):
    rabbitmq_url: AmqpDsn = Field(..., description="RabbitMQ 连接 URL")

class SqsBrokerConfig(BaseModel):
    queue_name: str | None = Field(None, description="SQS 队列名 (name)")
    queue_url: str | None = Field(None, description="SQS 队列完整 URL (优先)")

class ZeromqBrokerConfig(BaseModel):
    zmq_pub_host: str = Field("tcp://0.0.0.0:5555", description="ZeroMQ 发布 (PUB) 绑定地址，例如 tcp://")
    zmq_sub_host: str = Field("tcp://localhost:5555", description="ZeroMQ 订阅 (SUB) 绑定地址，例如 tcp://")


class NatsBrokerConfig(BaseModel):
    servers: list[str] = Field(..., description="NATS servers 列表，例如 ['nats://127.0.0.1:4222']")
    subject_prefix: str | None = Field(default="astrbot_tasks", description="可选的 subject 前缀")
    # jetstream 模式: None/False 表示不使用 JetStream，'push' 使用 PushBasedJetStreamBroker，'pull' 使用 PullBasedJetStreamBroker
    jetstream: str | bool | None = Field(None, description="是否使用 JetStream（'push'、'pull' 或 False/None 表示不使用）")
    # 普通 NatsBroker 与 PushBasedJetStreamBroker 的队列名
    queue: str | None = Field(None, description="用于 NATS 的队列名（可选）")
    # Pull-based JetStream 所需的 durable consumer 名称
    durable: str | None = Field(None, description="Pull-based JetStream 的 durable consumer 名称（可选）")

class PostgresBrokerConfig(BaseModel):
    dsn: PostgresDsn = Field(..., description="Postgres DSN，用于 PostgreSQL broker")

class YdbBrokerConfig(BaseModel):
    endpoint: str = Field(..., description="YDB 连接端点或连接字符串")
    database: str | None = Field(None, description="YDB 数据库名（如适用）")
    options: dict[str, str] | None = Field(default_factory=dict, description="其他可选参数")

class CustomBrokerConfig(BaseModel):
    path: str = Field(..., description="自定义 broker 路径，例如 module.path:ClassName")
    options: dict[str, str] | None = Field(default_factory=dict, description="传递给自定义 broker 的可选参数")

class AstrbotBrokerConfig(BaseModel):
    broker_type: str = Field(AstrbotBrokerType.INMEMORY.value, description="消息代理类型")
    redis: RedisBrokerConfig | None = None
    rabbitmq: RabbitmqBrokerConfig | None = None
    sqs: SqsBrokerConfig | None = None
    zeromq: ZeromqBrokerConfig | None = None
    nats: NatsBrokerConfig | None = None
    postgresql: PostgresBrokerConfig | None = None
    ydb: YdbBrokerConfig | None = None

    custom: CustomBrokerConfig | None = None


class AstrbotBrokers:
    """Central broker holder.

    Usage:
        AstrbotBrokers.setup(cfg)
        await AstrbotBrokers.startup()
        # use AstrbotBrokers.broker to register tasks
        await AstrbotBrokers.shutdown()
    """

    broker_cfg: AstrbotBrokerConfig
    broker: BROKER_TYPE | None = None
    @classmethod
    def setup(cls, broker_cfg: AstrbotBrokerConfig) -> BROKER_TYPE:
        cls.broker_cfg = broker_cfg
        match cls.broker_cfg.broker_type:
            case AstrbotBrokerType.INMEMORY.value:
                cls.broker = InMemoryBroker()
            case AstrbotBrokerType.RABBITMQ.value:
                if not cls.broker_cfg.rabbitmq:
                    raise ValueError("broker_type 为 rabbitmq 时，rabbitmq 配置不能为空")
                if not cls.broker_cfg.rabbitmq.rabbitmq_url:
                    raise ValueError("broker_type 为 rabbitmq 时，rabbitmq_url 不能为空")
                cls.broker = AioPikaBroker(
                    rabbitmq_url=cls.broker_cfg.rabbitmq,
                    exchange_name="astrbot_tasks",
                    queue_name="astrbot_task_queue"
                )
            case AstrbotBrokerType.REDIS.value:
                if not cls.broker_cfg.redis:
                    raise ValueError("broker_type 为 redis 时，redis 配置不能为空")
                if not cls.broker_cfg.redis.redis_url:
                    raise ValueError("broker_type 为 redis 时，redis_url 不能为空")
                cls.broker = RedisStreamBroker(
                    url=str(cls.broker_cfg.redis.redis_url),
                    queue_name="astrbot_tasks",
                    consumer_group_name="astrbot_consumer_group"
                )
            case AstrbotBrokerType.ZEROMQ.value:
                if not cls.broker_cfg.zeromq:
                    raise ValueError("broker_type 为 zeromq 时，zeromq 配置不能为空")
                if not getattr(cls.broker_cfg.zeromq, "zmq_pub_host", None) or not getattr(cls.broker_cfg.zeromq, "zmq_sub_host", None):
                    raise ValueError("broker_type 为 zeromq 时，zmq_pub_host 和 zmq_sub_host 不能为空")
                cls.broker = ZeroMQBroker(
                    zmq_pub_host=str(cls.broker_cfg.zeromq.zmq_pub_host),
                    zmq_sub_host=str(cls.broker_cfg.zeromq.zmq_sub_host),
                )
            case AstrbotBrokerType.NATS.value:
                if not cls.broker_cfg.nats:
                    raise ValueError("broker_type 为 nats 时，nats 配置不能为空")
                nats_cfg = cls.broker_cfg.nats
                if not getattr(nats_cfg, "servers", None):
                    raise ValueError("broker_type 为 nats 时，servers 不能为空")

                # 根据配置选择具体实现
                if not nats_cfg.jetstream:
                    # 普通 NatsBroker

                    cls.broker = NatsBroker(
                        servers=nats_cfg.servers,
                        queue=nats_cfg.queue or "astrbot_tasks",
                        subject=nats_cfg.subject_prefix or "astrbot_tasks",
                    )
                else:
                    mode = str(nats_cfg.jetstream).lower()
                    if mode == "push":
                        cls.broker = PushBasedJetStreamBroker(
                            servers=nats_cfg.servers,
                            queue=nats_cfg.queue or "astrbot_tasks",
                        )
                    elif mode == "pull":
                        cls.broker = PullBasedJetStreamBroker(
                            servers=nats_cfg.servers,
                            durable=nats_cfg.durable or "astrbot_durable",
                        )
                    else:
                        raise ValueError(f"未知的 nats.jetstream 模式: {nats_cfg.jetstream}")

            
            case AstrbotBrokerType.CUSTOM.value:
                ...

            case _:
                raise ValueError(f"不支持的 broker_type: {cls.broker_cfg.broker_type}")

        if cls.broker is None:
            raise RuntimeError("Broker 初始化失败，结果为 None")
        return cls.broker


    @classmethod
    async def startup(cls) -> None:
        """Start underlying broker if it exposes a startup method.

        This will call broker.startup() if present and await it when it's awaitable.
        """
        if cls.broker is None:
            return
        start = getattr(cls.broker, "startup", None)
        if start is None:
            return
        result = start()
        if inspect.isawaitable(result):
            await result

    @classmethod
    async def shutdown(cls) -> None:
        """Shutdown underlying broker if it exposes a shutdown method.

        This will call broker.shutdown() if present and await it when it's awaitable.
        """
        if cls.broker is None:
            return
        stop = getattr(cls.broker, "shutdown", None)
        if stop is None:
            return
        result = stop()
        if inspect.isawaitable(result):
            await result

# 关键，当启动worker时，尝试获取 broker 实例（新进程内--需要not InMemoryBroker）

def __getattr__(name: str) -> BROKER_TYPE | None:
    if name == "broker":
        if AstrbotBrokers.broker is None:
            raise RuntimeError("Broker 未初始化，无法获取实例")
        if isinstance(AstrbotBrokers.broker, InMemoryBroker):
            raise RuntimeError("InMemoryBroker 不能跨进程使用，请选择其他 broker 类型")
        return AstrbotBrokers.broker
    
