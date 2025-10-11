"""
title: AstrbotCanary root -- 根模块
version: v1.0.0
status: dev
authors: [LIghtJUNction]
owners: [LIghtJUNction]
created: 2025-10-09
updated: 2025-10-11
"""
# from importlib.metadata import EntryPoint
import logging
import rich.traceback

# 安装错误堆栈追踪器
rich.traceback.install()
logger = logging.getLogger("astrbot_canary.loader")

