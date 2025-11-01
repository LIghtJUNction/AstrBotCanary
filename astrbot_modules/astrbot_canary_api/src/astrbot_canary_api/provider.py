"""Provider registry for dependency injection across AstrBot modules."""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

if TYPE_CHECKING:
    from dishka import AsyncContainer, Container

__all__ = ["DepProviderRegistry"]


class DepProviderRegistry:
    """Central registry for module providers and dishka containers."""

    _providers: ClassVar[dict[str, object]] = {}
    _container: ClassVar[Container | None] = None
    _async_container: ClassVar[AsyncContainer | None] = None

    @classmethod
    def register(cls, name: str, provider: object) -> None:
        """Register a provider by name.

        Args:
            name: Provider name identifier
            provider: The provider instance or class
        """
        cls._providers[name] = provider

    @classmethod
    def get(cls, name: str) -> object:
        """Get a provider by name.

        Args:
            name: Provider name identifier

        Returns:
            The registered provider

        Raises:
            KeyError: If provider not found
        """
        return cls._providers[name]

    @classmethod
    def has(cls, name: str) -> bool:
        """Check if a provider is registered.

        Args:
            name: Provider name identifier

        Returns:
            True if provider exists
        """
        return name in cls._providers

    @classmethod
    def set_container(cls, container: Container) -> None:
        """Set the dishka sync container.

        Args:
            container: Dishka Container instance
        """
        cls._container = container

    @classmethod
    def set_async_container(cls, container: AsyncContainer) -> None:
        """Set the dishka async container.

        Args:
            container: Dishka AsyncContainer instance
        """
        cls._async_container = container

    @classmethod
    def get_container(cls) -> Container:
        """Get the dishka sync container.

        Returns:
            Dishka Container instance

        Raises:
            RuntimeError: If container not set
        """
        if cls._container is None:
            msg = "Dishka container not set. Call set_container first."
            raise RuntimeError(msg)
        return cls._container

    @classmethod
    def get_async_container(cls) -> AsyncContainer:
        """Get the dishka async container.

        Returns:
            Dishka AsyncContainer instance

        Raises:
            RuntimeError: If async container not set
        """
        if cls._async_container is None:
            msg = "Dishka async container not set. Call set_async_container first."
            raise RuntimeError(msg)
        return cls._async_container
