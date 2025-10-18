from collections.abc import Sequence

from pydantic import BaseModel, Field
from taskiq.cli.common_args import LogLevel
from taskiq.acks import AcknowledgeType

from astrbot_canary_api.types import BROKER_TYPE
from taskiq.cli.worker.args import WorkerArgs
from taskiq.cli.worker.run import run_worker

from logging import getLogger
logger = getLogger("astrbot.module.core.worker")



# 基于WorkerArgs定义一个pydantic模型 方便集成到AstrbotCanary
class AstrbotWorkerConfig(BaseModel):
    # core
    count: int = Field(2, description="Number of worker threads for taskiq")
    log_level: LogLevel = Field(
        LogLevel.INFO, description="Logging level for the worker (e.g., DEBUG, INFO, WARNING, ERROR)"
    )

    # discovery / modules
    modules: list[str] = Field(default_factory=list, description="Module import paths to scan for tasks")
    tasks_pattern: Sequence[str] = Field(("**/tasks.py",), description="Glob patterns to locate tasks files")
    fs_discover: bool = Field(False, description="Enable filesystem discovery")

    # logging / parsing
    configure_logging: bool = Field(True, description="Whether the worker should configure logging")
    log_format: str = Field(
        "[%(asctime)s][%(name)s][%(levelname)-7s][%(processName)s] %(message)s",
        description="Log format used by the worker",
    )

    # pools / threading
    max_threadpool_threads: int | None = Field(None, description="Max threads in threadpool")
    max_process_pool_processes: int | None = Field(None, description="Max processes in process pool")

    # parsing / reload
    no_parse: bool = Field(False, description="Skip parsing modules for tasks")
    shutdown_timeout: float = Field(5.0, description="Seconds to wait for graceful shutdown")
    reload: bool = Field(False, description="Enable hot-reload")
    reload_dirs: list[str] = Field(default_factory=list, description="Directories to watch for reload")
    no_gitignore: bool = Field(False, description="Don't respect .gitignore when discovering files")

    # receiver / runtime
    max_async_tasks: int = Field(100, description="Max concurrent async tasks")
    receiver: str = Field("taskiq.receiver:Receiver", description="Receiver import path")
    receiver_arg: list[tuple[str, str]] = Field(
        default_factory=list[tuple[str, str]],
        description="Extra args passed to receiver",
    )
    max_prefetch: int = Field(0, description="Receiver prefetch")
    no_propagate_errors: bool = Field(False, description="Don't propagate task errors")
    max_fails: int = Field(-1, description="Max fails before stopping the worker")
    ack_type: AcknowledgeType = Field(AcknowledgeType.WHEN_SAVED, description="Acknowledge policy")
    max_tasks_per_child: int | None = Field(None, description="Max tasks a child process will handle")
    wait_tasks_timeout: float | None = Field(None, description="How long to wait for tasks to finish on shutdown")
    hardkill_count: int = Field(3, description="Number of forced termination attempts before kill")
    use_process_pool: bool = Field(False, description="Use process pool for task execution")

class AstrbotWorker:
    broker: BROKER_TYPE
    cfg_worker: AstrbotWorkerConfig
    args: WorkerArgs

    @classmethod
    def setup(cls, cfg_worker: AstrbotWorkerConfig, broker: BROKER_TYPE) -> None:
        cls.cfg_worker = cfg_worker
        cls.broker = broker

        cls.args = WorkerArgs(
            broker="astrbot_canary.core.brokers:broker",
            modules=[],
            log_level=cfg_worker.log_level,
            workers=cfg_worker.count,
        )

    @classmethod
    def start(cls) -> int | None:

        if not cls.args:
            raise ValueError("Worker args not set up. Call setup() first.")
        result = run_worker(args=cls.args)
        logger.info(f"Worker started with result: {result}")
        return result
    
