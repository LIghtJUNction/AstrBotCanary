from astrbot_canary_api import IAstrbotConfigEntry
from taskiq import AsyncBroker, InMemoryBroker

from astrbot_canary.core.models import AstrbotTasksConfig

# AstrbotBrokerType
# INMEMORY = "inmemory"
# ZEROMQ = "zeromq"
# REDIS = "redis"
# RABBITMQ = "rabbitmq"
# NATS = "nats"
# POSTGRESQL = "postgresql"
# SQS = "sqs"
# YDB = "ydb"
# CUSTOM = "custom"

# AstrbotResultBackendType
# INMEMORY = "inmemory"
# DUMMY = "dummy"
# REDIS = "redis"
# NATS = "nats"
# POSTGRESQL = "postgresql"
# S3 = "s3"
# YDB = "ydb"


# Astrbot 任务管理器
class AstrbotTasks:
    """Astrbot 任务管理器
    提供全局任务队列和结果后端
    """

    broker: AsyncBroker = InMemoryBroker()

    @classmethod
    def init(cls, cfg_tasks: IAstrbotConfigEntry[AstrbotTasksConfig]) -> None:
        match cfg_tasks.value.broker_type:
            case "inmemory":
                cls.init_inmemory_broker(cfg_tasks.value)
            case "zeromq":
                cls.init_zeromq_broker(cfg_tasks.value)
            case "redis":
                cls.init_redis_broker(cfg_tasks.value)
            case "rabbitmq":
                cls.init_rabbitmq_broker(cfg_tasks.value)
            case "nats":
                cls.init_nats_broker(cfg_tasks.value)
            case "postgresql":
                cls.init_postgresql_broker(cfg_tasks.value)
            case "sqs":
                cls.init_sqs_broker(cfg_tasks.value)
            case "ydb":
                cls.init_ydb_broker(cfg_tasks.value)
            case "custom":
                cls.init_custom_broker(cfg_tasks.value)
            case _:
                raise ValueError(f"不支持的任务队列类型：{cfg_tasks.value.broker_type}")

        match cfg_tasks.value.backend_type:
            case "inmemory":
                cls.init_inmemory_backend(cfg_tasks.value)
            case "dummy":
                cls.init_dummy_backend(cfg_tasks.value)
            case "redis":
                cls.init_redis_backend(cfg_tasks.value)
            case "nats":
                cls.init_nats_backend(cfg_tasks.value)
            case "postgresql":
                cls.init_postgresql_backend(cfg_tasks.value)
            case "s3":
                cls.init_s3_backend(cfg_tasks.value)
            case "ydb":
                cls.init_ydb_backend(cfg_tasks.value)
            case _:
                raise ValueError(
                    f"不支持的结果后端类型：{cfg_tasks.value.backend_type}",
                )

        @cls.broker.task(
            "astrbot://echo",
            description="Echo --Welcome to Astrbot Tasks!",
            group="core",
        )
        def echo(msg: str) -> str:
            return msg

        # 注册到全局！
        AsyncBroker.global_task_registry["astrbot://echo"] = echo

    # region broker

    @classmethod
    def init_inmemory_broker(cls, cfg: AstrbotTasksConfig) -> None:
        # 默认就是这个，无需额外操作
        pass

    @classmethod
    def init_zeromq_broker(cls, cfg: AstrbotTasksConfig) -> None:
        raise NotImplementedError("ZEROMQ broker暂未实现")

    @classmethod
    def init_redis_broker(cls, cfg: AstrbotTasksConfig) -> None:
        raise NotImplementedError("REDIS broker暂未实现")

    @classmethod
    def init_rabbitmq_broker(cls, cfg: AstrbotTasksConfig) -> None:
        raise NotImplementedError("RABBITMQ broker暂未实现")

    @classmethod
    def init_nats_broker(cls, cfg: AstrbotTasksConfig) -> None:
        raise NotImplementedError("NATS broker暂未实现")

    @classmethod
    def init_postgresql_broker(cls, cfg: AstrbotTasksConfig) -> None:
        raise NotImplementedError("POSTGRESQL broker暂未实现")

    @classmethod
    def init_sqs_broker(cls, cfg: AstrbotTasksConfig) -> None:
        raise NotImplementedError("SQS broker暂未实现")

    @classmethod
    def init_ydb_broker(cls, cfg: AstrbotTasksConfig) -> None:
        raise NotImplementedError("YDB broker暂未实现")

    @classmethod
    def init_custom_broker(cls, cfg: AstrbotTasksConfig) -> None:
        raise NotImplementedError("CUSTOM broker暂未实现")

    # region backend

    @classmethod
    def init_inmemory_backend(cls, cfg: AstrbotTasksConfig) -> None:
        # InMemoryBroker 默认已初始化，无需额外操作
        pass

    @classmethod
    def init_dummy_backend(cls, cfg: AstrbotTasksConfig) -> None:
        # 除了 InMemoryBroker 外， 默认 Dummy 结果后端（不存储结果）
        pass

    @classmethod
    def init_redis_backend(cls, cfg: AstrbotTasksConfig) -> None:
        raise NotImplementedError("REDIS 结果后端暂未实现")

    @classmethod
    def init_nats_backend(cls, cfg: AstrbotTasksConfig) -> None:
        raise NotImplementedError("NATS 结果后端暂未实现")

    @classmethod
    def init_postgresql_backend(cls, cfg: AstrbotTasksConfig) -> None:
        raise NotImplementedError("POSTGRESQL 结果后端暂未实现")

    @classmethod
    def init_s3_backend(cls, cfg: AstrbotTasksConfig) -> None:
        raise NotImplementedError("S3 结果后端暂未实现")

    @classmethod
    def init_ydb_backend(cls, cfg: AstrbotTasksConfig) -> None:
        raise NotImplementedError("YDB 结果后端暂未实现")
