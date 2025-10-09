"""Loader package for Astrbot Canary.
注意：插件开发者应该使用本插件加载器模块提供的API入口点
如果直接导入
意味着插件基于插件加载器开发，与插件加载器绑定
不同的插件加载器可能提供不同的API
因此为了了最大兼容性，插件开发者应当使用入口点调用API以实现各种插件加载器之间的互兼容性
"""

from .specs import ASTRBOT_CANARY_HOOK_NS, PluginInfo , LoaderInfo

__all__ = ["ASTRBOT_CANARY_HOOK_NS", "PluginInfo", "LoaderInfo"]

