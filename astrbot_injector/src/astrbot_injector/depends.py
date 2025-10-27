""" 基于Wrapt的依赖注入库
简洁易用的依赖注入框架
支持:
    - 类和函数的依赖注入
    - 单例和多例注入模式
    - 基于自定义依赖描述器的递归依赖解析

原型构建阶段

"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable

class Depends:
    """ 依赖描述器（支持嵌套/依赖图）
    每个 Depends 实例可以通过 build_graph() 构建其完整的子依赖树，
    并能通过 parent/children 访问上下文。
    """
    def __init__(self, dependency: Any = None) -> None:
        self.dependency = dependency
        self.parent: Depends | None = None
        self.children: list[Depends] = []
        self._built: bool = False

        # 以下字段由 __set_name__ 填充，用于实例注入存储与类级注册
        self.name: str | None = None
        self.owner: type | None = None
        self._private_name: str | None = None

    def __set_name__(self, owner: type[object], name: str) -> None:
        """
        记录描述符被绑定到哪个类与属性名，并在 owner 上注册该依赖描述符。
        Container 可以通过 owner.__depends__ 发现类上的所有 Depends。
        """
        self.owner = owner
        self.name = name
        # 私有存储名（避免与用户属性冲突）
        self._private_name = f"__depends_{owner.__name__}_{name}"
        # 在类上注册（字典: name -> Depends），便于构建类级依赖图
        deps = getattr(owner, "__depends__", None)
        if deps is None:
            deps = {}
            setattr(owner, "__depends__", deps)
        deps[name] = self

    def __set__(self, instance: object, value: object) -> None:
        """
        正常情况下不鼓励手动赋值（应由容器注入）。
        为了安全，只有在 instance.__injection__ 为 True 时才允许写入，
        这是与 Container 约定的轻量授权机制：
          container 在注入前设置 instance.__injection__ = True，注入后清理该标记。
        """
        if not getattr(instance, "__injection__", False):
            raise AttributeError("Cannot set value to Depends descriptor; use the Container to inject.")
        if not self._private_name:
            raise RuntimeError("Depends descriptor not initialized via __set_name__")
        instance.__dict__[self._private_name] = value

    def __get__(self, instance: object | None, owner: type) -> object:
        # 在类访问时返回描述器本身,便于在类型层面查看依赖树
        if instance is None:
            return self
        # 实例访问时返回注入后的值（若已注入）
        if self._private_name and self._private_name in instance.__dict__:
            return instance.__dict__[self._private_name]
        # 未注入时保持不可直接读取，鼓励通过容器解析
        raise AttributeError("Dependency not injected; use the Container to resolve this dependency")

    def __delete__(self, instance: object) -> None:
        """
        仅允许容器在授权（instance.__injection__ 为 True）时删除注入的值。
        这样容器可以在销毁/重置实例状态时安全地清理注入字段，其他场景仍禁止删除。
        """
        if not getattr(instance, "__injection__", False):
            raise AttributeError("Cannot delete value from Depends descriptor; use the Container to manage lifecycle.")
        if not self._private_name:
            raise RuntimeError("Depends descriptor not initialized via __set_name__")
        if self._private_name in instance.__dict__:
            del instance.__dict__[self._private_name]
        else:
            raise AttributeError("Dependency value not set; nothing to delete.")