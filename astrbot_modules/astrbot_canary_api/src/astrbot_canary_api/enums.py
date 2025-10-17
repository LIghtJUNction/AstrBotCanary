from enum import Enum, IntFlag

__all__ = [
    "AstrbotModuleType",
    "AstrbotBrokerType",
    "AstrbotResultBackendType"
]

class AstrbotModuleType(IntFlag):
    UNKNOWN = 0
    CORE = 1 << 0# 1 
    LOADER = 1 << 1# 2
    WEB = 1 << 2# 4
    TUI = 1 << 3# 8

    UI_MASK = WEB | TUI
    @property
    def is_ui(self) -> bool:
        return bool(self & self.UI_MASK)
    
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
    INMEMORY = "inmemory"
    DUMMY = "dummy"
    REDIS = "redis"
    NATS = "nats"
    POSTGRESQL = "postgresql"
    S3 = "s3"
    YDB = "ydb"

if __name__ == "__main__":
    ...