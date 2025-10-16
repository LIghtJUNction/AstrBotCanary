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
from logging import Logger
import rich.traceback
# import cProfile
from astrbot_canary.core import AstrbotCoreModule

#region 注入核心实现


# 安装错误堆栈追踪器
rich.traceback.install()

logger: Logger = getLogger("astrbot_canary")
# 设置日志等级
basicConfig(level=INFO)

logger = getLogger("astrbot_canary.loader")

def main() -> None:
    core_module = AstrbotCoreModule()
    core_module.Awake()
    core_module.Start()

if __name__ == "__main__":
    # profiler = cProfile.Profile()
    # profiler.enable()
    main()
    # profiler.disable()
    # profiler.print_stats(sort="cumtime")

