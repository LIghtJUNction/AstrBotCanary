from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar

from astrbot_canary_api import (
    AstrbotInvalidPathError,
    AstrbotInvalidProviderPathError,
    ProviderNotSetError,
)
from dishka import (
    AsyncContainer,
    Container,
    make_async_container,
    make_container,
)
from dishka.plotter import render_d2, render_mermaid
from dishka.provider.provider import Provider

if TYPE_CHECKING:
    from dishka.provider import Provider


class ContainerNode:
    """递归的容器节点"""

    def __init__(self) -> None:
        self.children: dict[str, ContainerNode] = {}
        self.providers: dict[str, Provider | None] = {}

    def get_or_create_child(self, name: str) -> ContainerNode:
        if name not in self.children:
            self.children[name] = ContainerNode()
        return self.children[name]

    def get_child(self, name: str) -> ContainerNode | None:
        """获取子节,如果不存在返回 None."""
        return self.children.get(name)

    def get_provider(self, name: str) -> Provider | None:
        return self.providers.get(name)

    def set_provider(self, name: str, provider: Provider | None) -> None:
        self.providers[name] = provider

    def remove_provider(self, name: str) -> None:
        self.providers[name] = None

    def get_container(self, context: dict[Any, Any] | None = None) -> Container:
        """从当前节点的 providers 构建容器。"""
        provider_list = [
            provider for provider in self.providers.values() if provider is not None
        ]
        if not provider_list:
            raise ProviderNotSetError(provider_name="current node")
        return make_container(*provider_list, context=context)

    def get_all_providers(self) -> dict[str, Provider | None]:
        """递归获取当前节点及其所有子节点的所有提供者。"""
        all_providers = dict(self.providers)  # 复制当前节点的providers
        print(f"DEBUG get_all_providers: self={id(self)}, self.providers={self.providers}, all_providers={all_providers}")
        for child_name, child in self.children.items():
            print(f"DEBUG child {child_name}: {id(child)}, providers={child.providers}")
            child_providers = child.get_all_providers()
            # merge child providers, later ones override if conflict
            all_providers.update(child_providers)
        print(f"DEBUG final all_providers={all_providers}")
        return all_providers


class ContainerGetter:
    """类似 pathlib.Path 的容器获取器, 支持链式 / 操作。"""

    def __init__(
        self, *, is_async: bool = False, context: dict[Any, Any] | None = None,
    ) -> None:
        self.is_async = is_async
        self.path: list[str] = []
        self.context = context

    def __truediv__(self, value: str) -> ContainerGetter:
        """链式构建路径, 返回新的 ContainerGetter。"""
        new_getter = ContainerGetter(is_async=self.is_async, context=self.context)
        new_getter.path = [*self.path, value]
        return new_getter

    @property
    def provider(self) -> Provider | None:
        """获取当前路径的 provider (路径以 .p 后缀结尾)。"""
        if self.path and self.path[-1].endswith(".p"):
            provider_name_with_suffix = self.path[-1]
            provider_name = provider_name_with_suffix[:-2]  # 去掉 .p
            container_parts = self.path[:-1]

            node = AstrbotContainers.providers
            for part in container_parts:
                node = node.get_or_create_child(part)
            return node.get_provider(provider_name)
        raise AstrbotInvalidPathError(path="/".join(self.path) if self.path else "")

    @property
    def container(self) -> Container:
        """获取当前路径的容器 (不以 .p 后缀结尾)。"""
        if self.path:
            # Check if the last part ends with .p (should be a provider, not container)
            last_part = self.path[-1]
            if last_part.endswith(".p"):
                raise AstrbotInvalidPathError(path="/".join(self.path))

            # Navigate through the node hierarchy
            node = AstrbotContainers.providers
            for part in self.path:
                node = node.get_or_create_child(part)
            return node.get_container(context=self.context)
        raise AstrbotInvalidPathError(path="/".join(self.path))

class AstrbotContainers:
    providers: ClassVar[ContainerNode] = ContainerNode()

    def __init__(self) -> None:
        self.EXPECTED_TUPLE_LENGTH = 3

    # Initialize default structure
    @classmethod
    def _init_defaults(cls) -> None:
        canary_root = cls.providers.get_or_create_child("canary_root")
        canary_root.set_provider("config_entry", None)
        canary_root.set_provider("paths", None)

    @property
    def sync_container(self) -> ContainerGetter:
        return ContainerGetter(is_async=False)

    def sync_container_with_context(self, context: dict[Any, Any]) -> ContainerGetter:
        """获取带上下文的同步容器获取器。"""
        return ContainerGetter(is_async=False, context=context)

    @property
    def async_container(self) -> ContainerGetter:
        return ContainerGetter(is_async=True)

    def async_container_with_context(self, context: dict[Any, Any]) -> ContainerGetter:
        """获取带上下文的异步容器获取器。"""
        return ContainerGetter(is_async=True, context=context)

    def __lshift__(self, value: tuple[str, Provider]) -> AstrbotContainers:
        """支持 << 运算符, 设置 provider。
        value 应为 (path, provider) 元组, path 以 .p 结尾表示 provider。
        """
        path, provider = value
        if not path.endswith(".p"):
            raise AstrbotInvalidProviderPathError(path=path)

        # Split path into container parts and provider name
        parts = path.split("/")
        provider_name_with_suffix = parts[-1]
        provider_name = provider_name_with_suffix[:-2]  # Remove .p
        container_parts = parts[:-1]

        # Navigate to the correct node
        node = AstrbotContainers.providers
        for part in container_parts:
            node = node.get_or_create_child(part)

        # Set the provider
        node.set_provider(provider_name, provider)
        return self

    def __rshift__(self, path: str) -> None:
        """支持 >> 运算符, 移除 provider。
        path 以 .p 结尾表示 provider。
        """
        if not path.endswith(".p"):
            raise AstrbotInvalidProviderPathError(path=path)
        if "/" in path:
            parts = path.split("/")
            container_name = "/".join(parts[:-1])
            provider_name = parts[-1][:-2]
        else:
            container_name = ""
            provider_name = path[:-2]
        self.removeProvider(provider_name, container_name)

    @classmethod
    def getProvider(
        cls, container_name: str = "canary_root",
        provider_name: str = "",
    ) -> Provider | None:
        node = cls.providers.get_or_create_child(container_name)
        return node.get_provider(provider_name)

    @classmethod
    def getProviders(
        cls,
        container_name: str = "canary_root",
    ) -> dict[str, Provider | None]:
        """获取指定容器的所有提供者，包括子节点."""
        node = cls.providers.get_or_create_child(container_name)
        return node.get_all_providers()

    @classmethod
    def setProvider(cls, container_name: str = "astrbot_root",
                    provider_name: str = "",
                    provider: Provider | None = None,
                ) -> None:
        node = cls.providers.get_or_create_child(container_name)
        node.set_provider(provider_name, provider)

    @classmethod
    def removeProvider(
        cls, provider_name: str, container_name: str = "",
    ) -> None:
        node = cls.providers.get_child(container_name)
        if node and provider_name in node.providers:
            node.set_provider(provider_name, None)

    @classmethod
    def getContainer(cls, container_name: str = "") -> Container:
        """获取指定名称和组件的同步 Container.

        Sync container can use only synchronous dependency sources.
        同步容器只能使用同步依赖源。
        异步依赖源会被忽略, 因此避免在同步函数中进行网络 I/O。
        """

        providers = cls.getProviders(container_name)
        # 生成元组
        provider_list = [
            (provider) for provider in providers.values() if provider is not None
        ]

        print(f"DEBUG: container_name={container_name}, providers={providers}, provider_list={provider_list}")

        if not provider_list:
            raise ProviderNotSetError(provider_name=f"{container_name}")
        return make_container(*provider_list)

    @classmethod
    def getAsyncContainer(cls, name: str, container: str = "") -> AsyncContainer:
        """获取指定名称和组件的 AsyncContainer.

        # https://dishka.readthedocs.io/en/stable/container/index.html
        Async container can use any type of dependency sources: both sync and
        async are supported.
        Sync methods are called directly and no executors are used, so avoid
        network I/O in synchronous functions.
        异步容器可以使用任何类型的依赖源: 同步和异步都支持。
        同步方法是直接调用的, 不使用执行器, 因此避免在同步函数中进行网络 I/O。

        Sync container can use only synchronous dependency sources.
        同步容器只能使用同步依赖源, 所以不使用make_container来创建同步容器.
        """

        provider = cls.getProvider(name, container)
        if provider is None:
            raise ProviderNotSetError(provider_name=f"{container}:{name}")
        return make_async_container(provider)

    @classmethod
    def renderD2(cls, container_name: str = "") -> str:
        """获取指定名称和组件容器的 D2 渲染结果."""
        container = cls.getContainer(container_name)
        return render_d2(container)

    @classmethod
    def renderMermaid(cls, container_name: str = "") -> str:
        """获取指定名称和组件容器的 Mermaid 渲染结果."""
        container = cls.getContainer(container_name)
        return render_mermaid(container)
