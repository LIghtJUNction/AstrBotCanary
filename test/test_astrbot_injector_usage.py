import pytest
from astrbot_injector.depends import Depends


class Service:
    dep = Depends(lambda: "provided")
    other = Depends()  # 无显式 dependency，仅用于属性注册测试


def test_descriptor_registered_on_class() -> None:
    assert hasattr(Service, "__depends__")
    assert "dep" in Service.__depends__
    assert isinstance(Service.__depends__["dep"], Depends)
    assert "other" in Service.__depends__


def test_get_on_class_returns_descriptor() -> None:
    # 通过类访问应返回描述符本身
    assert Service.dep is Service.__depends__["dep"]


def test_instance_access_and_injection_lifecycle() -> None:
    s = Service()

    # 未注入时实例访问应报错
    with pytest.raises(AttributeError):
        _ = s.dep

    # 未授权写入应报错
    with pytest.raises(AttributeError):
        s.dep = "x"

    # 授权后可写入并且读取返回写入值
    s.__injection__ = True
    s.dep = "injected"
    # 清理授权（容器约定：注入后移除标记）
    del s.__injection__
    assert s.dep == "injected"

    # 未授权删除应报错
    with pytest.raises(AttributeError):
        del s.dep

    # 授权删除成功，之后访问再报错
    s.__injection__ = True
    del s.dep
    del s.__injection__
    with pytest.raises(AttributeError):
        _ = s.dep

    # 授权删除但值不存在时应抛出特定错误
    s.__injection__ = True
    with pytest.raises(AttributeError):
        del s.dep
    del s.__injection__