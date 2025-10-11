"""BASE package for Astrbot Canary.
注意：插件开发者不应该调用此模块内的任何内容.
仅供 Astrbot canary 模块使用
关于模块与插件的区别，请参考DOCS/README.md
插件依赖的API应由负责加载插件的加载器模块提供，从约定的入口点动态导入

"""


from .paths import Paths
from .api import AstrbotModuleAPI
from .config import AstrbotConfig

__all__ = ["Paths", "AstrbotModuleAPI", "AstrbotConfig"]