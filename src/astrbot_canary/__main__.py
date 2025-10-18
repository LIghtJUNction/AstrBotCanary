"""
title: AstrbotCanary root -- 根模块
version: v0.1.1
status: dev
authors: [LIghtJUNction]
owners: [LIghtJUNction]
created: 2025-10-09
updated: 2025-10-18
"""
from importlib.metadata import EntryPoints
from logging import INFO, getLogger , basicConfig
from pluggy import PluginManager as ModuleManager # 为了区分加载器的 PluginManager...
import rich.traceback
from rich.logging import RichHandler

from atexit import register
from click import Choice, confirm, prompt

# import cProfile
from astrbot_canary_helper import AstrbotCanaryHelper
from astrbot_canary.core.db import AstrbotDatabase
from astrbot_canary.core.log_handler import AsyncAstrbotLogHandler
from astrbot_canary.core.models import AstrbotRootConfig, AstrbotTasksConfig
from astrbot_canary.core.paths import AstrbotPaths
from astrbot_canary.core.config import AstrbotConfigEntry
from astrbot_canary.core.tasks import AstrbotTasks

from astrbot_canary_api import ASTRBOT_MODULES_HOOK_NAME, IAstrbotModule, AstrbotModuleType
from astrbot_canary_api.decorators import AstrbotInjector, AstrbotModule
from astrbot_canary_api.enums import AstrbotBrokerType
from astrbot_canary_api.interface import AstrbotModuleSpec, IAstrbotConfigEntry

# region 注入实现
AstrbotModule.ConfigEntry = AstrbotConfigEntry
AstrbotModule.Paths = AstrbotPaths
AstrbotModule.Database = AstrbotDatabase

# 安装错误堆栈追踪器
# enable rich tracebacks and pretty console logging
rich.traceback.install()
# rich + logging
basicConfig(
    level=INFO,
    format="%(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[RichHandler(rich_tracebacks=True, markup=True)],
)

logger = getLogger("astrbot")



#region Awake
class AstrbotRootModule:
    """ Astrbot根模块
    请勿参考本模块进行开发
    本模块为入口模块  
    """
    mm = ModuleManager(ASTRBOT_MODULES_HOOK_NAME)
    @classmethod
    def Awake(cls) -> None:
        """ AstrbotCanary 主入口函数，负责加载模块并调用其生命周期方法 """

        logger.info("AstrbotCanary 正在启动，加载模块...")
        cls.mm.add_hookspecs(AstrbotModuleSpec)
        cls.paths = AstrbotModule.Paths.getPaths("astrbot_canary")
        cls.ConfigEntry = AstrbotModule.ConfigEntry

        cls.cfg_root: IAstrbotConfigEntry[AstrbotRootConfig] = cls.ConfigEntry.bind(
            group="core",
            name="boot",
            default=AstrbotRootConfig(
                modules=["canary_core", "canary_loader", "canary_web", "canary_tui"],
                boot=["canary_core", "canary_loader", "canary_web"],
                log_what="astrbot",
                log_maxsize=500,
            ),
            description="核心模块配置项" \
            "modules: 已发现的全部模块" \
            "boot: 启动模块列表" \
            "log_what: 抓取谁的日志？（这会显示在webui的控制台中）" \
            "  可选：astrbot（默认，抓取全部），astrbot.module（抓取所有模块日志）" \
            "  astrbot.plugin（抓取插件日志）" \
            "  或者：" \
            "  astrbot.module.core（抓取指定模块日志）" \
            "  astrbot.plugin.xxx（抓取指定插件日志）" \
            "  none表示：我不需要用到这个功能！" \
            "log_maxsize: 日志缓存最大数量--这里是给web模块特供的handler使用的",
            cfg_dir=cls.paths.config,
        )

        cls.cfg_tasks : IAstrbotConfigEntry[AstrbotTasksConfig] = cls.ConfigEntry.bind(
            group="core",
            name="tasks",
            default=AstrbotTasksConfig(
                broker_type=AstrbotBrokerType.INMEMORY.value,
            ), 
            description="任务队列配置项",
            cfg_dir=cls.paths.config,
        )

        AstrbotTasks.init(cls.cfg_tasks)
        AstrbotModule.broker = AstrbotTasks.broker
        AstrbotInjector.set("broker", AstrbotModule.broker)

        handler = AsyncAstrbotLogHandler(maxsize=cls.cfg_root.value.log_maxsize)
        # 注入日志处理器
        AstrbotInjector.set("AsyncAstrbotLogHandler", handler)

        match cls.cfg_root.value.log_what:
            case "astrbot":
                logger.addHandler(handler)
            case "none":
                del handler
                AstrbotInjector.remove("AsyncAstrbotLogHandler")
            case _:
                _logger = getLogger(cls.cfg_root.value.log_what)
                _logger.addHandler(handler)

        # mm.load_setuptools_entrypoints(ASTRBOT_MODULES_HOOK_NAME)
        # 这里不用这个加载逻辑

        boot : list[IAstrbotModule] = []
        """ 启动列表 """

        # 决定是否发现模块启动还是直接从配置启动
        if confirm("从配置文件启动？",default=True):
            _boot = cls.cfg_root.value.boot
            for i in _boot:
                ep = AstrbotCanaryHelper.getSingleEntryPoint(ASTRBOT_MODULES_HOOK_NAME,i)
                if ep is None:
                    continue
                module = ep.load()
                boot.append(module)
        else:

            module_eps: EntryPoints = AstrbotCanaryHelper.getAllEntryPoints(group=ASTRBOT_MODULES_HOOK_NAME)
            _, core_module, loader_module, web_module, tui_module = cls.group_modules(module_eps)
            logger.debug(f"core:{core_module}\nloader:{loader_module}\nweb:{web_module}\ntui:{tui_module}")

            if _:
                logger.warning(f"发现未知模块{_}")

            # --- CORE: 仅选一个 ---
            if len(core_module) > 1:
                core_names = [getattr(m, "pypi_name", getattr(m, "__name__", repr(m))) for m in core_module]
                sel = prompt("请选择一个核心模块加载", type=Choice(core_names))
                core = next(m for m in core_module if getattr(m, "pypi_name", None) == sel or getattr(m, "__name__", None) == sel)
                boot.append(core)
            elif len(core_module) == 1:
                boot.append(core_module[0])

            # --- LOADER: 仅选一个 ---
            if len(loader_module) > 1:
                loader_names = [getattr(m, "pypi_name", getattr(m, "__name__", repr(m))) for m in loader_module]
                sel = prompt("请选择一个加载器模块", type=Choice(loader_names))
                loader = next(m for m in loader_module if getattr(m, "pypi_name", None) == sel or getattr(m, "__name__", None) == sel)
                boot.append(loader)
            elif len(loader_module) == 1:
                boot.append(loader_module[0])

            # --- UI: web + tui 合并，从中仅选一个 ---
            ui_candidates = web_module + tui_module
            if len(ui_candidates) > 1:
                ui_names = [getattr(m, "pypi_name", getattr(m, "__name__", repr(m))) for m in ui_candidates]
                sel = prompt("请选择一个UI模块 (web/tui)", type=Choice(ui_names))
                ui = next(m for m in ui_candidates if getattr(m, "pypi_name", None) == sel or getattr(m, "__name__", None) == sel)
                boot.append(ui)

            elif len(ui_candidates) == 1:
                boot.append(ui_candidates[0])

        for astrbot_module in boot:
            cls.mm.register(astrbot_module)

        _boot = [i.name for i in boot]
        cls.cfg_root.value.boot = _boot
        cls.mm.hook.Awake()
        """ 根模块仅负责唤醒，不负责启动，核心模块负责启动 """

    #region Start
    @classmethod
    def Start(cls):
        cls.mm.hook.Start()

    @classmethod
    def group_modules(cls, eps: EntryPoints) -> tuple[list[IAstrbotModule], list[IAstrbotModule], list[IAstrbotModule], list[IAstrbotModule], list[IAstrbotModule]]:
        """ 分组模块 """
        unknown_module: list[IAstrbotModule] = []
        core_module: list[IAstrbotModule] = []
        loader_module: list[IAstrbotModule] = []
        web_module: list[IAstrbotModule] = []
        tui_module: list[IAstrbotModule] = []

        for ep in eps:
            module: IAstrbotModule = ep.load()
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
        return unknown_module,core_module,loader_module,web_module,tui_module

    #region Destroy
    @staticmethod
    @register
    def atExit() -> None:
        logger.info("AstrbotCanary 正在退出，执行清理操作...")
        AstrbotRootModule.mm.hook.OnDestroy()
        # AstrbotRootModule.cfg_root.save()

if __name__ == "__main__":
    # profiler = cProfile.Profile()
    # profiler.enable()
    AstrbotRootModule.Awake()
    # profiler.disable()
    # profiler.print_stats(sort="cumtime")

    # profiler = cProfile.Profile()
    # profiler.enable()
    AstrbotRootModule.Start()
    # profiler.disable()
    # profiler.print_stats(sort="cumtime")