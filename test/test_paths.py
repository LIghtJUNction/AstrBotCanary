import shutil
from pathlib import Path

import pytest

from astrbot_paths.src.astrbot_paths.paths import AstrbotPaths


def test_astrbot_paths(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # 设置环境变量，确保 astrbot_root 在临时目录下
    monkeypatch.setenv("ASTRBOT_ROOT", str(tmp_path / ".astrbot_test"))
    pypi_name = "testmod"
    paths = AstrbotPaths.getPaths(pypi_name)
    # 检查根目录
    assert paths.astrbot_root.exists()
    # 检查 config 目录
    config_dir = paths.config
    assert config_dir.exists()
    assert config_dir.name == pypi_name
    # 检查 data 目录
    data_dir = paths.data
    assert data_dir.exists()
    assert data_dir.name == pypi_name
    # 检查 log 目录
    log_dir = paths.log
    assert log_dir.exists()
    assert log_dir.name == pypi_name
    # 清理
    shutil.rmtree(tmp_path / ".astrbot_test", ignore_errors=True)
