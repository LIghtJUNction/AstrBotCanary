"""
title: AstrbotCanary root -- 根模块
version: v0.1.1
status: dev
authors: [LIghtJUNction]
owners: [LIghtJUNction]
created: 2025-10-09
updated: 2025-10-11
"""
from logging import INFO, getLogger , basicConfig
from pluggy import PluginManager as ModuleManager # 为了区分加载器的 PluginManager...
import rich.traceback
from atexit import register
# import cProfile

from astrbot_canary.core.db import AstrbotDatabase
from astrbot_canary.core.paths import AstrbotPaths
from astrbot_canary.core.config import AstrbotConfig, AstrbotConfigEntry

from astrbot_canary_api import ASTRBOT_MODULES_HOOK_NAME
from astrbot_canary_api.decorators import AstrbotModule
from astrbot_canary_api.interface import ModuleSpec

# region 注入实现
AstrbotModule.Config = AstrbotConfig
AstrbotModule.ConfigEntry = AstrbotConfigEntry
AstrbotModule.Paths = AstrbotPaths
AstrbotModule.Database = AstrbotDatabase

# 安装错误堆栈追踪器
rich.traceback.install()
basicConfig(level=INFO)

logger = getLogger("astrbot_canary.module.root")

mm = ModuleManager(ASTRBOT_MODULES_HOOK_NAME)

""" 核心模块管理器实例 """


def main() -> None:
    """ AstrbotCanary 主入口函数，负责加载模块并调用其生命周期方法 """
    logger.info("AstrbotCanary 正在启动，加载模块...")
    mm.add_hookspecs(ModuleSpec)
    mm.load_setuptools_entrypoints(ASTRBOT_MODULES_HOOK_NAME)
    """ setuptools是早期的打包工具,现在推荐使用UV,这个函数没改名 """
    modules = mm.get_plugins()
    logger.info(f"已加载模块列表：{modules}")
    mm.hook.Awake()
    """ 根模块仅负责唤醒，不负责启动，核心模块负责启动 """

@register
def atExit() -> None:
    logger.info("AstrbotCanary 正在退出，执行清理操作...")
    mm.hook.OnDestroy()





if __name__ == "__main__":
    # profiler = cProfile.Profile()
    # profiler.enable()
    main()
    # profiler.disable()
    # profiler.print_stats(sort="cumtime")

