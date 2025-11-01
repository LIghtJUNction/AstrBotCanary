from .abc import IAstrbotConfigEntry, IAstrbotModule, IAstrbotPaths
from .enums import AstrbotModuleType
from .exceptions import (
    AstrbotContainerNotFoundError,
    AstrbotInvalidPathError,
    AstrbotInvalidProviderPathError,
    ProviderNotSetError,
    SecretError,
)
from .interface import (
    ASTRBOT_MODULES_HOOK_NAME,
    IAstrbotLogHandler,
    moduleimpl,
    modulespec,
)
from .models import LogHistoryItem, LogHistoryResponseData, LogSSEItem
from .provider import ContainerRegistry

# Backward compatibility alias
DepProviderRegistry = ContainerRegistry

__all__ = [
    "ASTRBOT_MODULES_HOOK_NAME",
    "AstrbotContainerNotFoundError",
    "AstrbotInvalidPathError",
    "AstrbotInvalidProviderPathError",
    "AstrbotModuleType",
    "ContainerRegistry",
    "DepProviderRegistry",  # Deprecated: use ContainerRegistry
    "IAstrbotConfigEntry",
    "IAstrbotLogHandler",
    "IAstrbotModule",
    "IAstrbotPaths",
    "LogHistoryItem",
    "LogHistoryResponseData",
    "LogSSEItem",
    "ProviderNotSetError",
    "SecretError",
    "moduleimpl",
    "modulespec",

]

