"""
title: AstrbotCanary Loader Specs
version: v1.0.0
status: dev
authors: [LIghtJUNction]
owners: [LIghtJUNction]
created: 2025-10-08
updated: 2025-10-08
"""
# 命名空间Name Space
# 能用pydantic就用pydantic的了，保持一致
from pydantic.dataclasses import dataclass
import pluggy

ASTRBOT_CANARY_HOOK_NS = "astrbot_canary"
# 定义插件规范
PLUGINSPEC = pluggy.HookspecMarker(ASTRBOT_CANARY_HOOK_NS)
# 定义插件实现
PLUGINIMPL = pluggy.HookimplMarker(ASTRBOT_CANARY_HOOK_NS)

@dataclass
class LoaderInfo:
    Name: str
    VersionCode: str
    Author: str
    Description: str

@dataclass
class PluginInfo:
    Name: str
    VersionCode: str
    Author: str
    Description: str
    Url: str

class PluginSpec:
    @PLUGINSPEC
    def Awake(self, LOADER_INFO: LoaderInfo)-> PluginInfo:
        """插件初始化"""
        return PluginInfo(
            Name="PluginName",
            VersionCode="100",
            Author="YourName",
            Description="No Description",
            Url="https://github.com/YourName/YourPlugin",
        )

    @PLUGINSPEC
    def Start(self):
        """在Awake之后调用"""
        pass


"""
插件实现规范：
from astrbot_canary.loader.specs import ASTRBOT_CANARY_HOOK_NS
import pluggy
# 插件实现
PLUGINIMPL = pluggy.HookimplMarker(ASTRBOT_CANARY_HOOK_NS)
class YourPlugin:
    @PLUGINIMPL
    def Awake(self):
        pass
    @PLUGINIMPL
    def Start(self):
        pass

"""
__all__ = ["PluginSpec", "ASTRBOT_CANARY_HOOK_NS", "PLUGINSPEC"]