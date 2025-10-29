from collections.abc import Callable, Generator
from inspect import Parameter
from typing import Annotated, Any, Final, TypeVar

import wrapt
from dishka import AsyncContainer, FromDishka, Provider, Scope, from_context
from dishka.integrations.base import wrap_injection
from strawberry import Info
from taskiq import (
    AsyncBroker,
    Context,
    TaskiqDepends,
    TaskiqMessage,
    TaskiqMiddleware,
    TaskiqResult,
)

CONTAINER_NAME: Final = "astrnet_container"

__all__ = [
    "AstrnetProvider",
    "FromDishka",
    "inject",
    "setup_astrnet",
]

_F = TypeVar("_F", bound=Callable[..., Any])


class AstrnetProvider(Provider):
    request = from_context(Info, scope=Scope.REQUEST)


class AstrnetMiddleware(TaskiqMiddleware):
    def __init__(self, container: AsyncContainer) -> None:
        super().__init__()
        self._container = container

    async def pre_execute(
        self,
        message: TaskiqMessage,
    ) -> TaskiqMessage:
        # 创建基本的 GraphQL 上下文
        # Strawberry 会自动创建 Info 对象
        basic_context = {
            "request": getattr(message, "request", None),
            "variables": getattr(message, "variables", {}),
            "operation_name": getattr(message, "operation_name", None),
        }
        message.labels[CONTAINER_NAME] = await self._container(
            context=basic_context,
        ).__aenter__()
        return message

    async def on_error(
        self,
        message: TaskiqMessage,
        result: TaskiqResult[Any],
        exception: BaseException,
    ) -> None:  # type: ignore[unused-argument]
        if CONTAINER_NAME in result.labels:
            await result.labels[CONTAINER_NAME].close()
            del result.labels[CONTAINER_NAME]

    async def post_execute(
        self,
        message: TaskiqMessage,
        result: TaskiqResult[Any],
    ) -> None:
        if CONTAINER_NAME in result.labels:
            await result.labels[CONTAINER_NAME].close()
            del result.labels[CONTAINER_NAME]


def _get_container(
    context: Annotated[Context, TaskiqDepends()],
) -> Generator[AsyncContainer]:
    yield context.message.labels[CONTAINER_NAME]

@wrapt.decorator
def inject[**P, R](
    wrapped: Callable[P, R],
    _instance: object,
    args: P.args,
    kwargs: P.kwargs,
) -> R:
    annotation = Annotated[
        AsyncContainer, TaskiqDepends(_get_container),
    ]
    additional_params = [Parameter(
        name=CONTAINER_NAME,
        annotation=annotation,
        kind=Parameter.KEYWORD_ONLY,
    )]

    # 检测是否为异步函数
    import asyncio
    is_async = asyncio.iscoroutinefunction(wrapped)

    def container_getter(args_: tuple[Any, ...], kwargs_: dict[str, Any]) -> AsyncContainer:
        return kwargs_[CONTAINER_NAME]

    wrapper = wrap_injection(
        func=wrapped,
        is_async=is_async,
        remove_depends=True,
        additional_params=additional_params,
        container_getter=container_getter,
    )

    return wrapper(*args, **kwargs)


def setup_astrnet(
    container: AsyncContainer,
    broker: AsyncBroker,
) -> None:
    broker.add_middlewares(AstrnetMiddleware(container))
