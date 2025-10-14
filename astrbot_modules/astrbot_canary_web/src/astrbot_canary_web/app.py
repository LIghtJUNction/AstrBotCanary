from typing import Any
from uuid import uuid4

from robyn import Request, Response, Robyn
from taskiq import BrokerMessage, InMemoryBroker, TaskiqMessage, TaskiqResult
from taskiq.decor import AsyncTaskiqDecoratedTask
from astrbot_canary_api.types import BROKER_TYPE
from logging import getLogger , Logger

from astrbot_canary_web.api import (
    auth_router,
    chat_router,
    config_router,
    conversation_router,
    file_router,
    live_log_router,
    log_history_router,
    persona_router,
    plugin_router,
    session_router,
    stat_router,
    t2i_router,
    tools_router,
    update_router,
)

logger: Logger = getLogger("astrbot_canary.module.web.app")

web_app = Robyn(__file__)

@web_app.startup_handler  # type: ignore[reportUnknownMemberType]
async def startup_handler() -> None:
    try:
        logger.info("Web app startup handler called")
        broker: BROKER_TYPE = web_app.dependencies.get_global_dependencies()["BROKER"]
        await broker.startup()

        await broker.result_backend.startup()
    except Exception as e:
        logger.error(f"未加载注入的Broker: {e}")

# region root

@web_app.get("/", const=True)
async def index() -> Response:
    return Response(
        status_code=307,
        description="",
        headers={"Location": "/home"},
    )



# region main

@web_app.get("/api/", const=True)
async def api() -> str:
    return "Hello Astrbot Canary Web!"


@web_app.post("/api/echo")
async def echo(request: Request):
    return {
        "body": request.body,
        "method": request.method,
        "identity": request.identity,
        "path_params": request.path_params,
        "ip": request.ip_addr,
        "form_data": request.form_data,
        "doc": request.__doc__,
        "size": request.__sizeof__()
    }

web_app.include_router(chat_router) #type: ignore
# include_router 参数未标类型
web_app.include_router(auth_router) #type: ignore
web_app.include_router(config_router) #type: ignore
web_app.include_router(conversation_router) #type: ignore
web_app.include_router(file_router) #type: ignore
web_app.include_router(live_log_router) #type: ignore
web_app.include_router(log_history_router) #type: ignore
web_app.include_router(persona_router) #type: ignore
web_app.include_router(plugin_router) #type: ignore
web_app.include_router(session_router) #type: ignore
web_app.include_router(stat_router) #type: ignore
web_app.include_router(t2i_router) #type: ignore
web_app.include_router(tools_router) #type: ignore
web_app.include_router(update_router) #type: ignore
# endregion

# region debug
@web_app.get("/debug/ping")
async def ping(global_dependencies: dict[str, Any]) -> str | None:
    broker: BROKER_TYPE = global_dependencies["BROKER"]
    if not isinstance(broker, InMemoryBroker):
        return "其他Broker可以监听，因此不需要使用此接口来测试"

    task_id = uuid4().hex
    taskiq_msg = TaskiqMessage(
        task_id=task_id,
        task_name="astrbot://canary_loader/ping",
        labels={},
        args=[], kwargs={}
    )
    payload = broker.serializer.dumpb(taskiq_msg.model_dump())

    await broker.kick(
        message=BrokerMessage(
            task_id=task_id,
            task_name="astrbot://canary_loader/ping",
            message=payload,
            labels={},
        )
    )

    # https://github.com/taskiq-python/taskiq/pull/514 缺少类型标注 
    # ctrl+左键点击result_backend 调转查看，broker.result_backend : InmemoryResultBackend[Any]
    if await broker.result_backend.get_progress(task_id) is not None:
        logger.info(f"Ping task {task_id} sent, progress available.")

    await broker.wait_all()

    if await broker.result_backend.is_result_ready(task_id):
        result: TaskiqResult[Any]= await broker.result_backend.get_result(task_id)
        return result.return_value
    else:
        return "???"

@web_app.get("/debug/task/list")
async def list_tasks(global_dependencies: dict[str, Any]) -> list[str]:
    broker: BROKER_TYPE = global_dependencies["BROKER"]
    tasks: dict[str, AsyncTaskiqDecoratedTask[Any, Any]] = broker.get_all_tasks()
    task_list = list(tasks.keys())
    return task_list

# endregion

if __name__ == "__main__":
    # create a configured "Session" class
    web_app.start(host="0.0.0.0", port=8080)
