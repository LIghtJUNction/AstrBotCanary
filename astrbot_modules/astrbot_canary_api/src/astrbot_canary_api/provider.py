"""Container registry for dependency injection across AstrBot modules.

This module provides a centralized registry for Dishka containers
organized by components. Each component represents an isolated
dependency graph, preventing implicit cross-component dependencies
while allowing explicit component-based dependency resolution.

Architecture:
    - Components isolate providers (e.g., "core", "web", "tui")
    - AsyncContainer supports both sync and async providers
    - Container instances are registered by component name
    - Multiple containers can coexist for different components

References:
    - Dishka Components: https://dishka.readthedocs.io/en/stable/advanced/components
"""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

if TYPE_CHECKING:
    from dishka import AsyncContainer, Container

__all__ = ["ContainerRegistry"]


class ContainerRegistry:
    """Central registry for Dishka containers organized by components.

    Dishka uses components to isolate dependency graphs. Each component has its own
    providers and dependencies that don't interfere with other components. This registry
    manages containers for different components across the application.

    Container Types:
        - AsyncContainer: Supports both sync and async providers (recommended)
        - Container: Sync-only container (legacy support)

    Component Design:
        Components represent logical modules (e.g., "core", "web").
        Use `container.get(Type, component="name")` for components.

    Example:
        >>> # Register async container for "core" component
        >>> ContainerRegistry.register_async("core", async_container)
        >>>
        >>> # Get container for "core" component
        >>> container = ContainerRegistry.get_async("core")
        >>>
        >>> # Check if component exists
        >>> if ContainerRegistry.has("core"):
        ...     container = ContainerRegistry.get_async("core")

    Thread Safety:
        Use `lock_factory=threading.Lock` or `asyncio.Lock` when creating containers
        for concurrent environments.
    """

    _sync_containers: ClassVar[dict[str, Container]] = {}
    _async_containers: ClassVar[dict[str, AsyncContainer]] = {}

    @classmethod
    def register_sync(cls, component: str, container: Container) -> None:
        """Register a synchronous Dishka container for a component.

        Args:
            component: Component name (e.g., "core", "web", "loader")
            container: Dishka Container instance created with make_container()

        Note:
            Sync containers only support synchronous providers.
            Consider using AsyncContainer for broader compatibility.

        Example:
            >>> from dishka import make_container
            >>> container = make_container(MyProvider())
            >>> ContainerRegistry.register_sync("core", container)
        """
        cls._sync_containers[component] = container

    @classmethod
    def register_async(cls, component: str, container: AsyncContainer) -> None:
        """Register an asynchronous Dishka container for a component.

        Args:
            component: Component name (e.g., "core", "web", "loader")
            container: AsyncContainer from make_async_container()

        Note:
            AsyncContainer supports BOTH sync and async providers.
            This is the recommended approach for most use cases.

        Example:
            >>> from dishka import make_async_container
            >>> container = make_async_container(MyProvider(), FastapiProvider())
            >>> ContainerRegistry.register_async("core", container)
        """
        cls._async_containers[component] = container

    @classmethod
    def get_sync(cls, component: str) -> Container:
        """Get synchronous container for a component.

        Args:
            component: Component name

        Returns:
            Dishka Container instance for the specified component

        Raises:
            KeyError: If component not registered

        Example:
            >>> container = ContainerRegistry.get_sync("core")
            >>> service = container.get(MyService)
        """
        if component not in cls._sync_containers:
            msg = (
                f"Sync container for component '{component}' not found. "
                f"Available components: {list(cls._sync_containers.keys())}"
            )
            raise KeyError(msg)
        return cls._sync_containers[component]

    @classmethod
    def get_async(cls, component: str) -> AsyncContainer:
        """Get asynchronous container for a component.

        Args:
            component: Component name

        Returns:
            Dishka AsyncContainer instance for the specified component

        Raises:
            KeyError: If component not registered

        Example:
            >>> container = ContainerRegistry.get_async("core")
            >>> service = await container.get(MyService)
        """
        if component not in cls._async_containers:
            msg = (
                f"Async container for component '{component}' not found. "
                f"Available components: {list(cls._async_containers.keys())}"
            )
            raise KeyError(msg)
        return cls._async_containers[component]

    @classmethod
    def has(cls, component: str) -> bool:
        """Check if a component has any registered container.

        Args:
            component: Component name

        Returns:
            True if component has sync or async container

        Example:
            >>> if ContainerRegistry.has("web"):
            ...     container = ContainerRegistry.get_async("web")
        """
        return component in cls._sync_containers or component in cls._async_containers

    @classmethod
    def has_sync(cls, component: str) -> bool:
        """Check if a component has a synchronous container.

        Args:
            component: Component name

        Returns:
            True if component has sync container

        Example:
            >>> if ContainerRegistry.has_sync("core"):
            ...     container = ContainerRegistry.get_sync("core")
        """
        return component in cls._sync_containers

    @classmethod
    def has_async(cls, component: str) -> bool:
        """Check if a component has an asynchronous container.

        Args:
            component: Component name

        Returns:
            True if component has async container

        Example:
            >>> if ContainerRegistry.has_async("web"):
            ...     container = ContainerRegistry.get_async("web")
        """
        return component in cls._async_containers

    @classmethod
    def list_components(cls) -> list[str]:
        """List all registered component names.

        Returns:
            List of component names with registered containers

        Example:
            >>> components = ContainerRegistry.list_components()
            >>> print(f"Available components: {components}")
        """
        return sorted(
            set(cls._sync_containers.keys())
            | set(cls._async_containers.keys()),
        )

    @classmethod
    def clear(cls) -> None:
        """Clear all registered containers.

        Warning:
            This does NOT call close() on containers. Ensure proper cleanup
            before calling this method to avoid resource leaks.

        Example:
            >>> # Proper cleanup
            >>> for component in ContainerRegistry.list_components():
            ...     if ContainerRegistry.has_async(component):
            ...         await ContainerRegistry.get_async(component).close()
            >>> ContainerRegistry.clear()
        """
        cls._sync_containers.clear()
        cls._async_containers.clear()
