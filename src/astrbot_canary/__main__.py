"""
title: AstrbotCanary root -- 根模块
version: v0.1.1
status: dev
authors: [LIghtJUNction]
owners: [LIghtJUNction]
created: 2025-10-09
updated: 2025-10-11
"""
import logging
import rich.traceback
# 安装错误堆栈追踪器
rich.traceback.install()

logger = logging.getLogger("astrbot_canary")

# 设置日志等级
logging.basicConfig(level=logging.INFO)

logger = logging.getLogger("astrbot_canary.loader")

from astrbot_canary.core import AstrbotCoreModule

core_module = AstrbotCoreModule()
core_module.Awake()
core_module.Start()
core_module.OnDestroy()