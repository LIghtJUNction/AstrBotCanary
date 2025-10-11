"""本API为模块开发使用API

"""
from __future__ import annotations
from abc import ABC, abstractmethod
from enum import Enum
from importlib.metadata import EntryPoint, EntryPoints, entry_points

import logging
from pathlib import Path

from pydantic_core import Url
import aiohttp
import aiofiles
from tqdm import tqdm

logger = logging.getLogger("AstrbotCanary.ModuleAPI")

class AstrbotModuleAPI:
    class ModuleType(Enum):
        LOADER = "loader"   # 001 #加载插件
        CORE = "core"       # 002 #核心组件
        WEB = "web"         # 003 #Web模块
        TUI = "tui"         # 004 #终端富交互
        GUI = "gui"         # 005 #桌面GUI
    
    class AstrbotBaseModule(ABC):
        """
        AstrbotCanary模块基类
        """
        TYPE : AstrbotModuleAPI.ModuleType

        @classmethod
        @abstractmethod
        def Awake(cls):
            """自身初始化
            """
            pass
        
        @classmethod
        @abstractmethod
        def Start(cls,args: list[str]):
            """在Awake之后调用
            args: 启动参数
            """
            pass

    class Utils:
        """
        工具集
        """

        @staticmethod
        def load_from_entrypoint(group: str, name: str) -> EntryPoint | None:
            """返回指定 group 和 name 的 entry point 加载后的对象（或 None）。
    
            要求运行时的 `entry_points()` 返回支持 `select(group=..., name=...)` 的 EntryPoints 对象。
            如果找不到匹配项或加载失败，返回 None 并记录日志。
            注意：不对加载到的类进行实例化，仅返回 ep 。
            """
            try:
                eps_all: EntryPoints = entry_points()
                if not hasattr(eps_all, "select"):
                    raise RuntimeError(
                        "entry_points() does not provide EntryPoints.select(); "
                        "update to a Python/importlib_metadata version that supports EntryPoints.select()"
                    )
                # 使用新版 API 的 name 过滤器（直接筛选单个条目）
                matches = list(eps_all.select(group=group, name=name))
                if not matches:
                    logger.debug(f"no entry point found for group={group!r} name={name!r}")
                    return None
    
                ep: EntryPoint = matches[0]
                try:
                    return ep
                except Exception:
                    logger.exception(f"failed to load entry point: {getattr(ep, 'name', repr(ep))}")
                    return None
            except Exception:
                logger.exception(
                    "entry_points discovery failed (requires EntryPoints.select support)."
                )
                return None
            
        
        @staticmethod
        def set_logging_basic_config(level: int = logging.INFO, format: str = "<%(asctime)s> [%(levelname)s] %(message)s" ) -> None:
            """设置全局日志配置。
            level: 日志级别，如 logging.DEBUG, logging.INFO 等
            """
            logging.basicConfig(level=level, format=format)


        @staticmethod
        def download(url: Url, dest: Path) -> None:
            """同步下载文件到指定路径
            url: 下载链接
            dest: 保存路径
            """
            import urllib.request
            dest.parent.mkdir(parents=True, exist_ok=True)
            req = urllib.request.Request(str(url), headers={"User-Agent": "astrbot-canary/1.0"})
            try:
                with urllib.request.urlopen(req, timeout=60) as resp:
                    length = resp.getheader("Content-Length")
                    total = int(length) if length and length.isdigit() else None
                    chunk_size = 64 * 1024
                    with open(dest, "wb") as f, tqdm(total=total, unit='B', unit_scale=True, desc=dest.name, dynamic_ncols=True) as pbar:
                        while True:
                            chunk = resp.read(chunk_size)
                            if not chunk:
                                break
                            f.write(chunk)
                            pbar.update(len(chunk))
            except urllib.request.HTTPError as e:
                logger.error("HTTP error while downloading %s: %s", url, e)
                raise

        @staticmethod
        async def async_download(url: Url, dest: Path) -> None:
            """异步下载文件到指定路径
            url: 下载链接
            dest: 保存路径
            """
            dest.parent.mkdir(parents=True, exist_ok=True)

            timeout = aiohttp.ClientTimeout(total=60)  # 根据需要调整
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(str(url)) as resp:
                    resp.raise_for_status()
                    # 尝试从响应头获取总大小
                    total = None
                    length = resp.headers.get("Content-Length")
                    try:
                        if length is not None:
                            total = int(length)
                    except Exception:
                        total = None

                    # 按块流式写入，避免一次性读入内存
                    async with aiofiles.open(dest, mode="wb") as f:
                        # tqdm 本身是同步的，但在异步循环中更新进度条是可行的
                        with tqdm(total=total, unit='B', unit_scale=True, desc=dest.name, dynamic_ncols=True) as pbar:
                            async for chunk in resp.content.iter_chunked(64 * 1024):
                                if not chunk:
                                    continue
                                await f.write(chunk)
                                pbar.update(len(chunk))
