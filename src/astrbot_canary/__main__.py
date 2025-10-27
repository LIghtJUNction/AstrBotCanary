"""title: AstrbotCanary root -- 根模块.

version: v0.1.1
status: dev
authors: [LIghtJUNction]
owners: [LIghtJUNction]
created: 2025-10-09
updated: 2025-10-21
"""

from __future__ import annotations

from atexit import register
from logging import INFO, basicConfig, getLogger
from typing import TYPE_CHECKING

import rich.traceback
from astrbot_canary_api import (
    ASTRBOT_MODULES_HOOK_NAME,
    AstrbotModuleType,
    IAstrbotModule,
    IAstrbotPaths,
)
from astrbot_canary_api.enums import AstrbotBrokerType, AstrbotResultBackendType
from astrbot_canary_api.interface import (
    AstrbotModuleSpec,
    IAstrbotConfigEntry,
)
from astrbot_canary_helper import AstrbotCanaryHelper
from click import Choice, prompt
from pluggy import PluginManager as ModuleManager  # 为了区分加载器的 PluginManager...
from pydantic import BaseModel
from rich.logging import RichHandler

from astrbot_config.src.astrbot_config.config import AstrbotConfigEntry
from astrbot_canary.core.log_handler import AsyncAstrbotLogHandler
from astrbot_canary.core.models import AstrbotRootConfig, AstrbotTasksConfig
from astrbot_paths.src.astrbot_paths.paths import AstrbotPaths
from astrbot_canary.core.tasks import AstrbotTasks
from astrbot_injector import AstrbotInjector

if TYPE_CHECKING:
    from importlib.metadata import EntryPoints

    from taskiq import AsyncBroker


# region 注入实现
AstrbotInjector.set("Paths", AstrbotPaths)
AstrbotInjector.set("ConfigEntry", AstrbotConfigEntry)

# 安装错误堆栈追踪器
# enable rich tracebacks and pretty console logging
_ = rich.traceback.install()
# rich + logging
basicConfig(
    level=INFO,
    format="%(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[RichHandler(rich_tracebacks=True, markup=True)],
)

logger = getLogger("astrbot")


@AstrbotInjector.inject
class AstrbotRootModule[T: BaseModel]:
    mm: ModuleManager = ModuleManager(ASTRBOT_MODULES_HOOK_NAME)
    pypi_name: str = "astrbot_canary"
    name: str = "canary_root"
    module_type: AstrbotModuleType = AstrbotModuleType.CORE

    ConfigEntry: type[IAstrbotConfigEntry[T]]
    Paths: type[IAstrbotPaths]

    # Dynamically set in Awake
    cfg_root: IAstrbotConfigEntry[AstrbotRootConfig]
    paths: IAstrbotPaths
    cfg_tasks: IAstrbotConfigEntry[AstrbotTasksConfig]
    broker: AsyncBroker

    """Astrbot根模块
    请勿参考本模块进行开发
    本模块为入口模块.
    """

    @classmethod
    def Awake(cls) -> None:
        """AstrbotCanary 主入口函数,负责加载模块并调用其生命周期方法."""
        logger.info("AstrbotCanary 正在启动,加载模块...")
        cls.mm.add_hookspecs(AstrbotModuleSpec)
        cls.paths = cls.Paths.getPaths(cls.pypi_name)

        cls.cfg_root = cls.ConfigEntry[AstrbotRootConfig].bind(
            group="core",
            name="boot",
            default=AstrbotRootConfig(
                modules=["canary_core", "canary_loader", "canary_web", "canary_tui"],
                boot=["canary_core", "canary_loader", "canary_web"],
                log_what="astrbot",
                log_maxsize=500,
            ),
            description=(
                "核心模块配置项"
                "modules: 已发现的全部模块"
                "boot: 启动模块列表"
                "log_what: 抓取谁的日志?(这会显示在webui的控制台中)"
                "  可选:astrbot(默认,抓取全部),astrbot.module(抓取所有模块日志)"
                "  astrbot.plugin(抓取插件日志)"
                "  或者:"
                "  astrbot.module.core(抓取指定模块日志)"
                "  astrbot.plugin.xxx(抓取指定插件日志)"
                "  none表示:我不需要用到这个功能!"
                "log_maxsize: 日志缓存最大数量--这里是给web模块特供的handler使用的"
            ),
            cfg_dir=cls.paths.config,
        )

        cls.cfg_tasks = cls.ConfigEntry[AstrbotTasksConfig].bind(
            group="core",
            name="tasks",
            default=AstrbotTasksConfig(
                broker_type=AstrbotBrokerType.INMEMORY.value,
                backend_type=AstrbotResultBackendType.INMEMORY.value,
            ),
            description="任务队列配置项",
            cfg_dir=cls.paths.config,
        )

        AstrbotTasks.init(cls.cfg_tasks)

        cls.broker = AstrbotTasks.broker
        AstrbotInjector.set("broker", cls.broker)

        handler = AsyncAstrbotLogHandler(maxsize=cls.cfg_root.value.log_maxsize)
        AstrbotInjector.set("AsyncAstrbotLogHandler", handler)
        cls._setup_logging(handler, cls.cfg_root.value.log_what)

        boot: list[type[IAstrbotModule]] = []
        # 自动选择默认值 True, 避免阻塞
        boot = cls._boot_from_config(cls.cfg_root.value.boot)

        for astrbot_module in boot:
            cls.mm.register(astrbot_module)

        _boot = [i.name for i in boot]
        cls.cfg_root.value.boot = _boot

        # region Start

    @classmethod
    def Start(cls) -> None:
        cls.mm.hook.Awake()
        cls.mm.hook.Start()

    @classmethod
    def OnDestroy(cls) -> None:
        cls.mm.hook.OnDestroy()

        cls.cfg_root.save()

    @classmethod
    def _setup_logging(cls, handler: AsyncAstrbotLogHandler, log_what: str) -> None:
        match log_what:
            case "astrbot":
                logger.addHandler(handler)
            case "none":
                del handler
                AstrbotInjector.remove("AsyncAstrbotLogHandler")
            case _:
                _logger = getLogger(log_what)
                _logger.addHandler(handler)

    @classmethod
    def _boot_from_config(cls, boot_names: list[str]) -> list[type[IAstrbotModule]]:
        boot: list[type[IAstrbotModule]] = []
        for i in boot_names:
            ep = AstrbotCanaryHelper.getSingleEntryPoint(
                ASTRBOT_MODULES_HOOK_NAME,
                i,
            )
            if ep is None:
                continue
            module = ep.load()
            # ep.load() should return a class (module implementation). 进行安全检查:
            if module is None:
                continue
            if isinstance(module, type):
                boot.append(module)
        return boot

    @classmethod
    def _boot_from_entrypoints(cls) -> list[type[IAstrbotModule]]:
        boot: list[type[IAstrbotModule] | None] = []
        module_eps: EntryPoints = AstrbotCanaryHelper.getAllEntryPoints(
            group=ASTRBOT_MODULES_HOOK_NAME,
        )
        _, core_module, loader_module, web_module, tui_module = cls.group_modules(
            module_eps,
        )
        logger.debug(
            "core:%s\nloader:%s\nweb:%s\ntui:%s",
            core_module,
            loader_module,
            web_module,
            tui_module,
        )

        # 发现未知模块
        if _:
            logger.warning("发现未知模块%s", _)

        boot.append(cls._select_single_module(core_module, "请选择一个核心模块加载"))
        boot.append(cls._select_single_module(loader_module, "请选择一个加载器模块"))
        ui_candidates = web_module + tui_module
        boot.append(
            cls._select_single_module(ui_candidates, "请选择一个UI模块 (web/tui)"),
        )
        # 过滤掉None
        return [m for m in boot if m is not None]

    @classmethod
    def _select_single_module(
        cls,
        modules: list[type[IAstrbotModule]],
        prompt_msg: str,
    ) -> type[IAstrbotModule] | None:
        if not modules:
            return None
        if len(modules) == 1:
            return modules[0]
        names = [
            getattr(m, "pypi_name", getattr(m, "__name__", repr(m))) for m in modules
        ]
        sel: str = prompt(prompt_msg, type=Choice(names))
        for m in modules:
            if (
                getattr(m, "pypi_name", None) == sel
                or getattr(m, "__name__", None) == sel
            ):
                return m
        return None

    @classmethod
    def group_modules(
        cls,
        eps: EntryPoints,
    ) -> tuple[
        list[type[IAstrbotModule]],
        list[type[IAstrbotModule]],
        list[type[IAstrbotModule]],
        list[type[IAstrbotModule]],
        list[type[IAstrbotModule]],
    ]:
        """分组模块."""
        unknown_module: list[type[IAstrbotModule]] = []
        core_module: list[type[IAstrbotModule]] = []
        loader_module: list[type[IAstrbotModule]] = []
        web_module: list[type[IAstrbotModule]] = []
        tui_module: list[type[IAstrbotModule]] = []

        for ep in eps:
            module = ep.load()
            # ep.load() can return different things depending on the entrypoint.
            # We expect a class that implements IAstrbotModule (subclass or registered).
            if isinstance(module, type):
                match module.module_type:
                    case AstrbotModuleType.CORE:
                        core_module.append(module)
                    case AstrbotModuleType.LOADER:
                        loader_module.append(module)
                    case AstrbotModuleType.WEB:
                        web_module.append(module)
                    case AstrbotModuleType.TUI:
                        tui_module.append(module)
                    case _:
                        unknown_module.append(module)
            else:
                # treat unexpected values as unknown modules
                unknown_module.append(module)
        return unknown_module, core_module, loader_module, web_module, tui_module

    # region Destroy
    @staticmethod
    @register
    def atExit() -> None:
        logger.info("AstrbotCanary 正在退出,执行清理操作...")
        AstrbotRootModule.OnDestroy()

    # region Destroy


if __name__ == "__main__":
    AstrbotRootModule.Awake()
    AstrbotRootModule.Start()
