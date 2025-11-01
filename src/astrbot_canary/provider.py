
"""Core module dishka providers."""

from __future__ import annotations

from astrbot_canary_api import (
    IAstrbotConfigEntry,
    IAstrbotLogHandler,
    IAstrbotPaths,
)
from dishka import Provider, Scope, provide
from taskiq import AsyncBroker

from astrbot_canary.core.log_handler import AsyncAstrbotLogHandler
from astrbot_config import AstrbotConfigEntry
from astrbot_paths import AstrbotPaths


class AstrobotCoreProvider(Provider):
    """Dishka Provider for core AstrBot services."""

    scope = Scope.APP

    def __init__(
        self,
        jwt_exp_days: int = 7,
        broker: AsyncBroker | None = None,
        log_handler: AsyncAstrbotLogHandler | None = None,
        paths: AstrbotPaths | None = None,
        config_entry: type[AstrbotConfigEntry] | None = None,
    ) -> None:
        super().__init__()
        self._jwt_exp_days = jwt_exp_days
        self._broker = broker
        self._log_handler = log_handler
        self._paths = paths
        self._config_entry = config_entry

    @provide(scope=Scope.APP)
    def get_jwt_exp_days(self) -> int:
        """Provide JWT expiration days."""
        return self._jwt_exp_days

    @provide(scope=Scope.APP)
    def get_broker(self) -> AsyncBroker | None:
        """Provide AsyncBroker instance."""
        return self._broker

    @provide(scope=Scope.APP, provides=IAstrbotLogHandler)
    def get_log_handler(self) -> AsyncAstrbotLogHandler | None:
        """Provide AsyncAstrbotLogHandler as IAstrbotLogHandler."""
        return self._log_handler

    @provide(scope=Scope.APP, provides=IAstrbotPaths)
    def get_paths(self) -> AstrbotPaths | None:
        """Provide AstrbotPaths as IAstrbotPaths."""
        return self._paths

    @provide(scope=Scope.APP, provides=type[IAstrbotConfigEntry])
    def get_config_entry(self) -> type[AstrbotConfigEntry] | None:
        """Provide AstrbotConfigEntry as IAstrbotConfigEntry."""
        return self._config_entry
