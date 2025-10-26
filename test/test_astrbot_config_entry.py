import warnings
from enum import Enum
from pathlib import Path

import pytest
from pydantic import BaseModel, Field

from astrbot_canary.core.config import AstrbotConfigEntry


class SubConfig(BaseModel):
    sub_field1: str = Field("sub_value1", description="子配置字段1")
    sub_field2: int = Field(42, description="子配置字段2")


class Type1(Enum):
    OPTION_A = "option_a"
    OPTION_B = "option_b"


class Type2(Enum):
    OPTION_X = "option_x"
    OPTION_Y = "option_y"


class NestedConfig(BaseModel):
    type_1: str = Field(Type1.OPTION_A.value, description="类型1选项")
    type_2: Type2 = Field(Type2.OPTION_X, description="类型2选项")
    path1: str = Field("some/path", description="示例路径字段")
    path2: Path = Field(Path("another/path"), description="示例Path字段")
    host: str = Field("localhost", description="数据库主机")
    port: int = Field(5432, description="数据库端口")
    user: str = Field("user", description="数据库用户")
    password: str = Field("password", description="数据库密码")
    sub_config: SubConfig = SubConfig(sub_field1="nested_value", sub_field2=100)


@pytest.fixture
def tmp_cfg_dir(tmp_path: Path):
    cfg_dir = tmp_path / "test_cfg"
    cfg_dir.mkdir(parents=True, exist_ok=True)
    return cfg_dir


def test_astrbot_config_entry(tmp_cfg_dir: Path):
    nested_default = NestedConfig(
        type_1=Type1.OPTION_A.value,
        type_2=Type2.OPTION_X,
        path1="some/path",
        path2=Path("another/path"),
        host="localhost",
        port=5432,
        user="user",
        password="password",
        sub_config=SubConfig(sub_field1="nested_value", sub_field2=100),
    )
    entry = AstrbotConfigEntry[NestedConfig].bind(
        group="database",
        name="main",
        default=nested_default,
        description="主数据库配置",
        cfg_dir=tmp_cfg_dir,
    )
    # 检查初始值
    assert entry.value.port == 5432
    assert entry.value.type_2 == Type2.OPTION_X
    assert entry.value.path2 == Path("another/path")
    # 修改并保存
    entry.value.port = 3306
    entry.save()
    # 重置
    entry.reset()
    assert entry.value.port == 5432
    # 检查类型
    assert isinstance(entry.value, NestedConfig)
    assert isinstance(entry.value.path2, Path)
    assert isinstance(entry.value.type_2, Type2)
    assert entry.value.sub_config.sub_field1 == "nested_value"
    print("pytest: AstrbotConfigEntry 测试通过")


def test_repr_str():
    dummy = NestedConfig(
        type_1=Type1.OPTION_A.value,
        type_2=Type2.OPTION_X,
        path1="some/path",
        path2=Path("another/path"),
        host="localhost",
        port=5432,
        user="user",
        password="password",
        sub_config=SubConfig(sub_field1="nested_value", sub_field2=100),
    )
    entry = AstrbotConfigEntry[NestedConfig](
        name="n",
        group="g",
        value=dummy,
        default=dummy,
        description="d",
        cfg_file=None,
    )
    assert isinstance(repr(entry), str)
    assert isinstance(str(entry), str)


def test_save_no_cfg_file():
    dummy = NestedConfig(
        type_1=Type1.OPTION_A.value,
        type_2=Type2.OPTION_X,
        path1="some/path",
        path2=Path("another/path"),
        host="localhost",
        port=5432,
        user="user",
        password="password",
        sub_config=SubConfig(sub_field1="nested_value", sub_field2=100),
    )
    entry = AstrbotConfigEntry[NestedConfig](
        name="n",
        group="g",
        value=dummy,
        default=dummy,
        description="d",
        cfg_file=None,
    )
    entry.save()  # 不应抛异常


def test_load_file_not_exist(tmp_path: Path):
    dummy = NestedConfig(
        type_1=Type1.OPTION_A.value,
        type_2=Type2.OPTION_X,
        path1="some/path",
        path2=Path("another/path"),
        host="localhost",
        port=5432,
        user="user",
        password="password",
        sub_config=SubConfig(sub_field1="nested_value", sub_field2=100),
    )
    entry = AstrbotConfigEntry[NestedConfig](
        name="n",
        group="g",
        value=dummy,
        default=dummy,
        description="d",
        cfg_file=tmp_path / "not_exist.toml",
    )
    entry.load()  # 不应抛异常


def test_load_invalid_data(tmp_path: Path):
    dummy = NestedConfig(
        type_1=Type1.OPTION_A.value,
        type_2=Type2.OPTION_X,
        path1="some/path",
        path2=Path("another/path"),
        host="localhost",
        port=5432,
        user="user",
        password="password",
        sub_config=SubConfig(sub_field1="nested_value", sub_field2=100),
    )
    cfg_file = tmp_path / "invalid.toml"
    cfg_file.write_text("not_a_valid_toml = 123")
    entry = AstrbotConfigEntry[NestedConfig](
        name="n",
        group="g",
        value=dummy,
        default=dummy,
        description="d",
        cfg_file=cfg_file,
    )
    with pytest.raises(Exception):
        entry.load()


def test_save_invalid_type(tmp_path: Path):
    class Dummy(BaseModel):
        x: int = 1

    entry = AstrbotConfigEntry[Dummy](
        name="n",
        group="g",
        value=Dummy(),
        default=Dummy(),
        description="d",
        cfg_file=tmp_path / "f.toml",
    )
    entry.value = "not_a_model"  # 故意测试非法类型
    with warnings.catch_warnings(record=True) as w:
        entry.save()
        assert any(
            "PydanticSerializationUnexpectedValue" in str(warn.message) for warn in w
        )


def test_reset_invalid_default():
    class Dummy(BaseModel):
        x: int = 1

    entry = AstrbotConfigEntry[Dummy](
        name="n",
        group="g",
        value=Dummy(),
        default=Dummy(),
        description="d",
        cfg_file=None,
    )
    entry.default = "not_a_model"  # 故意测试非法类型
    with pytest.raises(Exception):
        entry.reset()


def test_save_no_cfg_file_logs_error(caplog: pytest.LogCaptureFixture):
    dummy = NestedConfig(
        type_1=Type1.OPTION_A.value,
        type_2=Type2.OPTION_X,
        path1="some/path",
        path2=Path("another/path"),
        host="localhost",
        port=5432,
        user="user",
        password="password",
        sub_config=SubConfig(sub_field1="nested_value", sub_field2=100),
    )
    entry = AstrbotConfigEntry[NestedConfig](
        name="n",
        group="g",
        value=dummy,
        default=dummy,
        description="d",
        cfg_file=None,
    )
    with caplog.at_level("ERROR"):
        entry.save()
        assert any("配置文件路径未设置" in m for m in caplog.messages)


def test_bind_file_exists(tmp_path: Path):
    # 构造一个已存在的 toml 文件，包含 value/default 字段为 dict
    from toml import dump

    dummy_dict = {
        "type_1": Type1.OPTION_A.value,
        "type_2": Type2.OPTION_X.value,
        "path1": "some/path",
        "path2": "another/path",
        "host": "localhost",
        "port": 5432,
        "user": "user",
        "password": "password",
        "sub_config": {"sub_field1": "nested_value", "sub_field2": 100},
    }
    data = {
        "name": "main",
        "group": "database",
        "value": dummy_dict,
        "default": dummy_dict,
        "description": "主数据库配置",
    }
    cfg_file = tmp_path / "database.toml"
    with cfg_file.open("w", encoding="utf-8") as f:
        dump(data, f)
    # bind 时应走到文件存在分支
    entry = AstrbotConfigEntry[NestedConfig].bind(
        group="database",
        name="main",
        default=NestedConfig(
            type_1=Type1.OPTION_A.value,
            type_2=Type2.OPTION_X,
            path1="some/path",
            path2=Path("another/path"),
            host="localhost",
            port=5432,
            user="user",
            password="password",
            sub_config=SubConfig(sub_field1="nested_value", sub_field2=100),
        ),
        description="主数据库配置",
        cfg_dir=tmp_path,
    )
    assert entry.value.port == 5432
    assert (
        entry.value.type_2 == Type2.OPTION_X
        or entry.value.type_2 == Type2.OPTION_X.value
    )
