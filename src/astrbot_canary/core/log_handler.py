from asyncio import Queue, get_running_loop
from datetime import UTC, datetime
from logging import Handler, LogRecord

import orjson

from astrbot_canary_api.interface import LogHistoryItem, LogHistoryResponseData, LogSSEItem

class AsyncAstrbotLogHandler(Handler):
    queue: Queue[LogHistoryItem]
    """ 日志处理器 """
    def __init__(self,maxsize: int = 500):
        super().__init__()
        self.queue: Queue[LogHistoryItem] = Queue(maxsize=maxsize)

    def emit(self, record: LogRecord):
        msg = record.getMessage()
        log_item = LogHistoryItem(
            level=record.levelname,
            time=datetime.now(UTC).isoformat(),
            data=msg
        )
        print(f"[DEBUG] Log added: {log_item.level} {log_item.time} {log_item.data}")

        try:
            loop = get_running_loop()
            loop.create_task(self.queue.put(log_item))
        except RuntimeError:
            self.queue.put_nowait(log_item)

    async def event_stream(self):
        while True:
            log_item = await self.queue.get()
            sse_item = LogSSEItem(
                type="log",
                time=log_item.time,
                level=log_item.level,
                data=log_item.data
            )
            json_str = orjson.dumps(sse_item.model_dump()).decode()
            yield f"data: {json_str}\n\n"

    async def get_log_history(self) -> LogHistoryResponseData:
        """
        获取结构化日志历史，返回 LogHistoryResponseData
        """
        items: list[LogHistoryItem] = []
        while not self.queue.empty():
            items.append(await self.queue.get())
        return LogHistoryResponseData(logs=items)

