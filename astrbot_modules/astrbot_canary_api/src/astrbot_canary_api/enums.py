from enum import Enum


class AstrBotModuleType(Enum):
    UNKNOWN = "unknown"
    CORE = "core"
    LOADER = "loader"
    WEB = "web"
    TUI = "tui"