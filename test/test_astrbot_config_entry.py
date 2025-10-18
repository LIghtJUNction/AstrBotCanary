import pytest
from pathlib import Path
from pydantic import BaseModel, Field
from enum import Enum
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
    # 重新加载
    entry.load()
    assert entry.value.port == 3306
    # 重置
    entry.reset()
    assert entry.value.port == 5432
    # 检查类型
    assert isinstance(entry.value, NestedConfig)
    assert isinstance(entry.value.path2, Path)
    assert isinstance(entry.value.type_2, Type2)
    assert entry.value.sub_config.sub_field1 == "nested_value"
    print("pytest: AstrbotConfigEntry 测试通过")
