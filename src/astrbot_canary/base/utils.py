from importlib.metadata import EntryPoint, EntryPoints, entry_points
from logging import getLogger
import logging
logger = getLogger("AstrbotCanary.Utils")

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