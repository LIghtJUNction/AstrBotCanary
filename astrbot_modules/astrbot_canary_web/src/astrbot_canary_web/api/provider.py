"""Dishka provider for web API dependencies."""

from __future__ import annotations

from typing import TYPE_CHECKING

from dishka import Provider, Scope, provide

if TYPE_CHECKING:
    from astrbot_canary_api.interface import IAstrbotLogHandler


class WebAPIProvider(Provider):
    """Provider for web API dependencies."""

    scope = Scope.APP

    def __init__(self) -> None:
        super().__init__()
        self._log_handler: IAstrbotLogHandler | None = None
        self._db: object | None = None
        self._jwt_exp_days: int = 7

    def set_log_handler(self, handler: IAstrbotLogHandler | None) -> None:
        """Set the log handler instance."""
        self._log_handler = handler

    def set_db(self, db: object | None) -> None:
        """Set the database instance."""
        self._db = db

    def set_jwt_exp_days(self, days: int) -> None:
        """Set JWT expiration days."""
        self._jwt_exp_days = days

    @provide
    def get_log_handler(self) -> object | None:  # IAstrbotLogHandler
        """Provide the log handler."""
        return self._log_handler

    @provide
    def get_db(self) -> object | None:
        """Provide the database instance."""
        return self._db

    @provide
    def get_jwt_exp_days(self) -> int:
        """Provide JWT expiration days."""
        return self._jwt_exp_days
