"""schema: Astrbot
Astrbot协议
"""

from .astrnet import AstrnetApp

# 创建Astrnet应用实例
app = AstrnetApp()

@app.task
async def echo_task(message: str) -> str:
    """基于TaskIQ的任务: 处理回声消息."""
    return message

@app.query
async def echo(message: str) -> str:
    """回声查询, 使用TaskIQ处理消息."""
    # 自动运行任务
    return await app.run_task("echo_task", message)

schema = app.create_schema()
