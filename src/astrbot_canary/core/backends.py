from __future__ import annotations
from typing import Any
from pydantic import BaseModel, Field

from astrbot_canary_api.types import BROKER_TYPE
from astrbot_canary_api import AstrbotResultBackendType

# 开发者必读：
# https://taskiq-python.github.io/available-components/result-backends.html#nats-result-backend


class RedisBackendReturnType(BaseModel):
    """定义 Redis 任务结果的返回类型"""
    status: str
    result: Any

class AstrbotRedisBackendConfig(BaseModel):
    redis_url: str | None = Field(None, description="Redis 连接 URL")


class AstrbotNatsBackendConfig(BaseModel):
    """NATS result backend configuration (JetStream or basic)."""
    # full NATS connection URL, e.g. nats://user:pass@host:4222
    nats_url: str | None = Field(None, description="NATS 连接 URL")
    # when using JetStream pull mode you may want to control durable name / queue
    jetstream: bool = Field(False, description="是否使用 JetStream")
    durable_name: str | None = Field(None, description="JetStream durable consumer name (可选)")


class AstrbotPostgresBackendConfig(BaseModel):
    """PostgreSQL backend configuration."""
    dsn: str | None = Field(None, description="PostgreSQL DSN (e.g. postgresql://user:pass@host:5432/db)")


class AstrbotS3BackendConfig(BaseModel):
    """S3/result-object storage backend configuration."""
    bucket: str | None = Field(None, description="S3 bucket name to store task results")
    region: str | None = Field(None, description="S3 region (optional)")


class AstrbotYdbBackendConfig(BaseModel):
    endpoint: str | None = Field(None, description="YDB endpoint")
    database: str | None = Field(None, description="YDB database name")


class AstrbotBackendConfig(BaseModel):
    backend_type: str = Field(default=AstrbotResultBackendType.NONE.value, description="The type of backend to use, e.g., 'sqlalchemy', 'mongodb', etc.")
    redis: AstrbotRedisBackendConfig = AstrbotRedisBackendConfig(redis_url=None)
    nats: AstrbotNatsBackendConfig = AstrbotNatsBackendConfig(nats_url=None, jetstream=False, durable_name=None)
    postgres: AstrbotPostgresBackendConfig = AstrbotPostgresBackendConfig(dsn=None)
    s3: AstrbotS3BackendConfig = AstrbotS3BackendConfig(bucket=None, region=None)
    ydb: AstrbotYdbBackendConfig = AstrbotYdbBackendConfig(endpoint=None, database=None)


class AstrbotBackends:
    backend_cfg: AstrbotBackendConfig
    # backend 可用于存放不同实现的 result backend（类型在运行时确定）
    backend: Any | None

    @classmethod
    def setup(cls, backend_cfg: AstrbotBackendConfig, broker: Any) -> BROKER_TYPE:
        cls.backend_cfg = backend_cfg
        match cls.backend_cfg.backend_type:
            case AstrbotResultBackendType.NONE.value:
                cls.backend = None

            case AstrbotResultBackendType.REDIS.value:
                try:
                    from taskiq_redis import RedisAsyncResultBackend
                except Exception as exc:  # pragma: no cover - dependency error
                    raise ImportError(
                        "taskiq-redis is required for Redis result backend; install it with 'pip install taskiq-redis'"
                    ) from exc

                if not cls.backend_cfg.redis or not cls.backend_cfg.redis.redis_url:
                    raise ValueError("backend_type 为 redis 时，redis_url 不能为空")

                cls.backend = RedisAsyncResultBackend(
                    redis_url=cls.backend_cfg.redis.redis_url,
                )

            case AstrbotResultBackendType.NATS.value:
                # NATS backend may be provided by taskiq-nats. Try to import the package
                try:
                    import taskiq_nats as _taskiq_nats  # type: ignore
                except Exception as exc:  # pragma: no cover - dependency error
                    raise ImportError(
                        "taskiq-nats is required for NATS result backend; install it with 'pip install taskiq-nats'"
                    ) from exc

                # prefer named backend classes used by common versions
                backend_cls = getattr(_taskiq_nats, "NatsAsyncResultBackend", None) or getattr(
                    _taskiq_nats, "NatsResultBackend", None
                )
                if backend_cls is None:
                    raise ImportError("taskiq-nats found but no suitable backend class was detected; check the installed package version")

                # try to obtain a nats_url from backend_cfg.nats or from provided broker
                nats_url = None
                if hasattr(cls.backend_cfg, "nats"):
                    nats_cfg = getattr(cls.backend_cfg, "nats")
                    nats_url = getattr(nats_cfg, "nats_url", None)

                if nats_url is None and broker is not None:
                    # common broker objects may expose a url or connection attribute
                    nats_url = getattr(broker, "nats_url", None) or getattr(broker, "url", None) or None

                if nats_url is None:
                    # instantiate without URL if backend supports connecting via existing client
                    try:
                        cls.backend = backend_cls()
                    except TypeError:
                        raise ValueError(
                            "backend_type 为 nats 时，必须在 backend config 中提供 nats_url 或传入已配置的 nats broker"
                        )
                else:
                    cls.backend = backend_cls(nats_url=nats_url)

            case AstrbotResultBackendType.DUMMY.value:

                cls.backend = None
            case AstrbotResultBackendType.POSTGRESQL.value:
                # PostgreSQL backend (third-party: taskiq-postgresql)
                try:
                    import taskiq_postgresql as _pg  # type: ignore
                except Exception as exc:  # pragma: no cover - dependency error
                    raise ImportError(
                        "PostgreSQL result backend requires 'taskiq-postgresql'. Install with 'pip install taskiq-postgresql'."
                    ) from exc

                pg_cls = getattr(_pg, "PostgresResultBackend", None) or getattr(_pg, "PostgresqlResultBackend", None) or getattr(_pg, "PostgresAsyncResultBackend", None)
                if pg_cls is None:
                    raise ImportError("taskiq-postgresql found but no suitable backend class was detected; check the package version")

                # attempt to extract DSN from nested postgres config
                dsn = getattr(cls.backend_cfg.postgres, "dsn", None)
                if dsn is None:
                    raise ValueError("backend_type 为 postgresql 时，需要在 backend config 中提供 postgres.dsn")

                cls.backend = pg_cls(dsn=dsn)
            case AstrbotResultBackendType.S3.value:
                # S3/result-object storage backend (third-party). Try common packages.
                # Possible packages: taskiq-s3, taskiq_aio_s3, taskiq_aio_sqs (some projects use S3-like storage)
                s3_pkg = None
                for mod_name in ("taskiq_s3", "taskiq_aio_s3", "taskiq_aio_sqs", "taskiq_s3_backend"):
                    try:
                        s3_pkg = __import__(mod_name)
                        break
                    except Exception:
                        s3_pkg = None

                if s3_pkg is None:
                    raise ImportError(
                        "S3 result backend requires a third-party package (e.g. 'taskiq-s3'); install the appropriate package."
                    )

                s3_cls = getattr(s3_pkg, "S3ResultBackend", None) or getattr(s3_pkg, "AioS3ResultBackend", None) or getattr(s3_pkg, "S3AsyncResultBackend", None)
                if s3_cls is None:
                    raise ImportError("S3 backend package found but no suitable backend class detected; check the package name and version")

                # require bucket name in nested s3 config
                bucket = getattr(cls.backend_cfg.s3, "bucket", None)
                if bucket is None:
                    raise ValueError("backend_type 为 s3 时，需要在 backend config 中提供 s3.bucket")

                cls.backend = s3_cls(bucket=bucket)
            case AstrbotResultBackendType.YDB.value:
                try:
                    import taskiq_ydb as _ydb  # type: ignore
                except Exception as exc:  # pragma: no cover - dependency error
                    raise ImportError(
                        "YDB result backend requires 'taskiq-ydb'. Install with 'pip install taskiq-ydb'."
                    ) from exc

                ydb_cls = getattr(_ydb, "YdbResultBackend", None) or getattr(_ydb, "YDBResultBackend", None)
                if ydb_cls is None:
                    raise ImportError("taskiq-ydb found but no suitable backend class was detected; check the installed package version")

                ydb_cfg = getattr(cls.backend_cfg, "ydb", None)
                if ydb_cfg is None:
                    raise ValueError("backend_type 为 ydb 时，需要在 backend config 中提供 ydb 配置（endpoint/database 等）")

                # try to pull common settings
                endpoint = getattr(ydb_cfg, "endpoint", None)
                database = getattr(ydb_cfg, "database", None)
                if endpoint is None or database is None:
                    raise ValueError("ydb 配置需要包含 endpoint 和 database")

                cls.backend = ydb_cls(endpoint=endpoint, database=database)
            

            case _:
                raise ValueError(f"Unsupported backend type: {cls.backend_cfg.backend_type}")

        # 如果后端不为 None，尝试绑定
        if cls.backend is not None:
            broker = broker.with_result_backend(cls.backend)
        return broker
            