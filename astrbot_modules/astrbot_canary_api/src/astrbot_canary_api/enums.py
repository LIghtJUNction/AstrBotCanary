from enum import Enum

__all__ = [
    "AstrBotModuleType",
    "AstrbotBrokerType",
    "AstrbotResultBackendType"
]


class AstrBotModuleType(Enum):
    UNKNOWN = "unknown"
    CORE = "core"
    LOADER = "loader"
    WEB = "web"
    TUI = "tui"

class AstrbotBrokerType(Enum):
    INMEMORY = "inmemory"
    ZEROMQ = "zeromq"
    REDIS = "redis"
    RABBITMQ = "rabbitmq"
    NATS = "nats"
    POSTGRESQL = "postgresql"
    SQS = "sqs"
    YDB = "ydb"
    CUSTOM = "custom"

class AstrbotResultBackendType(Enum):
    NONE = "none"
    DUMMY = "dummy"
    REDIS = "redis"
    NATS = "nats"
    POSTGRESQL = "postgresql"
    S3 = "s3"
    YDB = "ydb"

