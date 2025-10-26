from __future__ import annotations

import inspect
from logging import getLogger
from typing import TYPE_CHECKING, ClassVar, ParamSpec, TypeVar

from wrapt.decorators import decorator

if TYPE_CHECKING:
    from collections.abc import Callable

# Generic typing helpers for decorator signatures
P = ParamSpec("P")
R = TypeVar("R")
T = TypeVar("T", bound=type)

logger = getLogger("astrbot.injector")


class Dep:
    """依赖注入标记类,用于在默认值中指定依赖键或动态解析器。

    支持静态键注入和动态依赖解析，可选缓存。
    """

    def __init__(
        self,
        key_or_resolver: str | Callable[[], object],
        *,
        cache: bool = False,
    ) -> None:
        if callable(key_or_resolver):
            self.resolver: Callable[[], object] | None = key_or_resolver
            self.key: str | None = None
        else:
            self.key = key_or_resolver
            self.resolver = None
        self.cache = cache
        self._cached_value: object | None = None
        self._computed = False

    def __repr__(self) -> str:
        if self.resolver:
            return f"Dep(resolver=<callable>, cache={self.cache!r})"
        return f"Dep({self.key!r})"

    def get_resolved_value(self, dependencies: dict[str, object]) -> object:
        if self.resolver:
            if self.cache and self._computed:
                return self._cached_value
            else:
                value = self.resolver()
                if self.cache:
                    self._cached_value = value
                    self._computed = True
                return value
        if self.key is None:
            msg = "Invalid Dep state"
            raise ValueError(msg)
        return dependencies[self.key]


class AstrbotInjector:
    """Astrbot依赖注入器..

    推荐用法:@AstrbotInjector.inject 或 @AstrbotInjector().inject
    支持全局依赖注入和局部依赖注入,类型安全

    例子:
        # 全局
        @AstrbotInjector.inject
        def my_function(db, config):
            ...

        AstrbotInjector.set("db", my_database_instance)
        my_function()  # 自动注入

        # 局部
        injector = AstrbotInjector()
        @injector.inject
        def my_function(db, config):
            ...
    """

    global_dependencies: ClassVar[dict[str, object]] = {}
    local_injector: ClassVar[dict[str, AstrbotInjector]] = {}

    def __init__(self, name: str = "") -> None:
        """初始化注入器."""
        self.name: str = name
        self.local_dependencies: dict[str, object] = {}

    @decorator
    @classmethod
    def inject(cls, wrapped: object, instance: object) -> object:
        """装饰器 (使用依赖)。"""





        if inspect.isclass(wrapped):
            # 支持只在类中使用类型注解声明的属性,没有显式赋值.
            # Python 将这些保存在 __annotations__ 而不是 __dict__,因此
            # 我们需要检查两者的键集合。
            names = list(wrapped.__dict__.keys())
            names += list(getattr(wrapped, "__annotations__", {}).keys())
            for name in set(names):
                if name.startswith("__"):
                    continue
                value = getattr(wrapped, name, None)
                if isinstance(value, Dep):
                    resolved = value.get_resolved_value(dependencies)
                    setattr(wrapped, name, resolved)
                elif value is None and name in dependencies:
                    setattr(wrapped, name, dependencies[name])
            return wrapped

        @decorator
        def wrapper(
            wrapped_func: Callable[..., object],
            _instance: object,
            args: tuple[object, ...],
            kwargs: dict[str, object],
        ) -> object:
            sig = inspect.signature(wrapped_func)
            bound = sig.bind_partial(*args, **kwargs)
            for param in sig.parameters.values():
                if isinstance(param.default, Dep) and param.name not in bound.arguments:
                    dep = param.default
                    value = dep.get_resolved_value(dependencies)
                    kwargs[param.name] = value
                elif (
                    param.name not in bound.arguments
                    and param.name in dependencies
                    and param.default is inspect.Parameter.empty
                ):
                    kwargs[param.name] = dependencies[param.name]
            return wrapped_func(*args, **kwargs)

        return wrapper(wrapped)

    def _inject_local(self, wrapped: object) -> object:
        """装饰器 (使用实例依赖)。"""
        dependencies = self.dependencies

        if inspect.isclass(wrapped):
            names = list(wrapped.__dict__.keys())
            names += list(getattr(wrapped, "__annotations__", {}).keys())
            for name in set(names):
                if name.startswith("__"):
                    continue
                value = getattr(wrapped, name, None)
                if isinstance(value, Dep):
                    resolved = value.get_resolved_value(dependencies)
                    setattr(wrapped, name, resolved)
                elif value is None and name in dependencies:
                    setattr(wrapped, name, dependencies[name])
            return wrapped

        @decorator
        def wrapper(
            wrapped_func: Callable[..., object],
            _instance: object,
            args: tuple[object, ...],
            kwargs: dict[str, object],
        ) -> object:
            sig = inspect.signature(wrapped_func)
            bound = sig.bind_partial(*args, **kwargs)
            for param in sig.parameters.values():
                if isinstance(param.default, Dep) and param.name not in bound.arguments:
                    dep = param.default
                    value = dep.get_resolved_value(dependencies)
                    kwargs[param.name] = value
                elif (
                    param.name not in bound.arguments
                    and param.name in dependencies
                    and param.default is inspect.Parameter.empty
                ):
                    kwargs[param.name] = dependencies[param.name]
            return wrapped_func(*args, **kwargs)

        return wrapper(wrapped)

    def set(self, name: str, value: object) -> None:
        if hasattr(self, "global_dependencies"):
            self.global_dependencies[name] = value
        else:
            self.local_dependencies[name] = value

    def get(self, name: str) -> object | None:
        if hasattr(self, "global_dependencies"):
            return self.global_dependencies.get(name)
        else:
            return self.local_dependencies.get(name)

    def remove(self, name: str) -> None:
        if hasattr(self, "global_dependencies"):
            self.global_dependencies.pop(name, None)
        else:
            self.local_dependencies.pop(name, None)

    @classmethod
    def getInjector(cls, injector_name: str) -> AstrbotInjector:
        if injector_name not in cls.local_injector:
            cls.local_injector[injector_name] = AstrbotInjector(injector_name)
        return cls.local_injector[injector_name]
