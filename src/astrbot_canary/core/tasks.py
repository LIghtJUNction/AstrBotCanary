from __future__ import annotations

from typing import TYPE_CHECKING, Any

from taskiq import AsyncBroker, InMemoryBroker

if TYPE_CHECKING:
    from astrbot_canary_api import IAstrbotConfigEntry

    from astrbot_canary.core.models import AstrbotTasksConfig


# Astrbot 任务管理器
class AstrbotTasks:
    """Astrbot 任务管理器
    提供全局任务队列和结果后端.
    """

    broker: AsyncBroker = InMemoryBroker()

    @classmethod
    def init(cls, cfg_tasks: IAstrbotConfigEntry[Any]) -> None:
        """初始化任务系统, 接受任何包含 broker_type 和 backend_type 属性的配置."""
        broker_map = {
            "inmemory": cls.init_inmemory_broker,
            "zeromq": cls.init_zeromq_broker,
            "redis": cls.init_redis_broker,
            "rabbitmq": cls.init_rabbitmq_broker,
            "nats": cls.init_nats_broker,
            "postgresql": cls.init_postgresql_broker,
            "sqs": cls.init_sqs_broker,
            "ydb": cls.init_ydb_broker,
            "custom": cls.init_custom_broker,
        }
        backend_map = {
            "inmemory": cls.init_inmemory_backend,
            "dummy": cls.init_dummy_backend,
            "redis": cls.init_redis_backend,
            "nats": cls.init_nats_backend,
            "postgresql": cls.init_postgresql_backend,
            "s3": cls.init_s3_backend,
            "ydb": cls.init_ydb_backend,
        }

        broker_type = cfg_tasks.value.broker_type
        backend_type = cfg_tasks.value.backend_type

        broker_func = broker_map.get(broker_type)
        if broker_func is None:
            msg = f"不支持的任务队列类型:{broker_type}"
            raise ValueError(msg)
        broker_func(cfg_tasks.value)

        backend_func = backend_map.get(backend_type)
        if backend_func is None:
            msg = f"不支持的结果后端类型:{backend_type}"
            raise ValueError(msg)
        backend_func(cfg_tasks.value)

        @cls.broker.task(
            "astrbot://echo",
            description="Echo --Welcome to Astrbot Tasks!",
            group="core",
        )
        def echo(msg: str) -> str:
            return msg

        # 注册到全局!
        AsyncBroker.global_task_registry["astrbot://echo"] = echo

    # region broker

    @classmethod
    def init_inmemory_broker(cls, cfg: AstrbotTasksConfig) -> None:
        # 默认就是这个,无需额外操作
        pass

    @classmethod
    def init_zeromq_broker(cls, cfg: AstrbotTasksConfig) -> None:
        msg = "ZEROMQ broker暂未实现"
        raise NotImplementedError(msg)

    @classmethod
    def init_redis_broker(cls, cfg: AstrbotTasksConfig) -> None:
        msg = "REDIS broker暂未实现"
        raise NotImplementedError(msg)

    @classmethod
    def init_rabbitmq_broker(cls, cfg: AstrbotTasksConfig) -> None:
        msg = "RABBITMQ broker暂未实现"
        raise NotImplementedError(msg)

    @classmethod
    def init_nats_broker(cls, cfg: AstrbotTasksConfig) -> None:
        msg = "NATS broker暂未实现"
        raise NotImplementedError(msg)

    @classmethod
    def init_postgresql_broker(cls, cfg: AstrbotTasksConfig) -> None:
        msg = "POSTGRESQL broker暂未实现"
        raise NotImplementedError(msg)

    @classmethod
    def init_sqs_broker(cls, cfg: AstrbotTasksConfig) -> None:
        msg = "SQS broker暂未实现"
        raise NotImplementedError(msg)

    @classmethod
    def init_ydb_broker(cls, cfg: AstrbotTasksConfig) -> None:
        msg = "YDB broker暂未实现"
        raise NotImplementedError(msg)

    @classmethod
    def init_custom_broker(cls, cfg: AstrbotTasksConfig) -> None:
        msg = "CUSTOM broker暂未实现"
        raise NotImplementedError(msg)

    # region backend

    @classmethod
    def init_inmemory_backend(cls, cfg: AstrbotTasksConfig) -> None:
        # InMemoryBroker 默认已初始化,无需额外操作
        pass

    @classmethod
    def init_dummy_backend(cls, cfg: AstrbotTasksConfig) -> None:
        # 除了 InMemoryBroker 外, 默认 Dummy 结果后端(不存储结果)
        pass

    @classmethod
    def init_redis_backend(cls, cfg: AstrbotTasksConfig) -> None:
        msg = "REDIS 结果后端暂未实现"
        raise NotImplementedError(msg)

    @classmethod
    def init_nats_backend(cls, cfg: AstrbotTasksConfig) -> None:
        msg = "NATS 结果后端暂未实现"
        raise NotImplementedError(msg)

    @classmethod
    def init_postgresql_backend(cls, cfg: AstrbotTasksConfig) -> None:
        msg = "POSTGRESQL 结果后端暂未实现"
        raise NotImplementedError(msg)

    @classmethod
    def init_s3_backend(cls, cfg: AstrbotTasksConfig) -> None:
        msg = "S3 结果后端暂未实现"
        raise NotImplementedError(msg)

    @classmethod
    def init_ydb_backend(cls, cfg: AstrbotTasksConfig) -> None:
        msg = "YDB 结果后端暂未实现"
        raise NotImplementedError(msg)
