from astrbot_canary_api.enums import AstrbotModuleType


def test_is_ui() -> None:
    # WEB 和 TUI 都应为 UI
    assert AstrbotModuleType.WEB.is_ui is True
    assert AstrbotModuleType.TUI.is_ui is True
    # CORE/LOADER/UNKNOWN 都不是 UI
    assert AstrbotModuleType.CORE.is_ui is False
    assert AstrbotModuleType.LOADER.is_ui is False
    assert AstrbotModuleType.UNKNOWN.is_ui is False
    # 组合类型 WEB|CORE 也应为 UI
    assert (AstrbotModuleType.WEB | AstrbotModuleType.CORE).is_ui is True
    # 组合类型 TUI|LOADER 也应为 UI
    assert (AstrbotModuleType.TUI | AstrbotModuleType.LOADER).is_ui is True
    # 只有 CORE|LOADER 不是 UI
    assert (AstrbotModuleType.CORE | AstrbotModuleType.LOADER).is_ui is False
