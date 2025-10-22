from collections.abc import Iterable
from importlib.metadata import EntryPoint, EntryPoints, entry_points


class AstrbotCanaryHelper:
    eps: EntryPoints = entry_points()

    @classmethod
    def _ensure_loaded(cls, *, refresh: bool = False) -> None:
        if refresh:
            cls.eps = entry_points()

    @classmethod
    def getSingleEntryPoint(
        cls,
        group: str,
        name: str,
        *,
        refresh: bool = False,
    ) -> EntryPoint | None:
        """获取指定组-名字的单个入口点,找不到返回 None.."""
        cls._ensure_loaded(refresh=refresh)
        for ep in cls.eps.select(group=group, name=name):
            return ep
        return None

    @classmethod
    def getAllEntryPoints(cls, group: str, *, refresh: bool = False) -> EntryPoints:
        """获取指定组的所有入口点(EntryPoints 对象).."""
        cls._ensure_loaded(refresh=refresh)
        return cls.eps.select(group=group)

    @classmethod
    def getMultiGroupAllEntryPoints(
        cls,
        groups: list[str],
        *,
        refresh: bool = False,
    ) -> EntryPoints:
        """获取多个组的所有入口点并合并,保持首次出现顺序且去重.."""
        cls._ensure_loaded(refresh=refresh)
        merged: list[EntryPoint] = []
        seen: set[tuple[str | None, str | None, str | None]] = set()
        for group in groups:
            for ep in cls.eps.select(group=group):
                key = (ep.group, ep.name, ep.value)
                if key in seen:
                    continue
                seen.add(key)
                merged.append(ep)
        return EntryPoints(merged)

    @staticmethod
    def mergeEntryPoints(*args: Iterable[EntryPoint]) -> EntryPoints:
        """合并多个 EntryPoints/迭代器,按首次出现去重,返回 EntryPoints.."""
        merged: list[EntryPoint] = []
        seen: set[tuple[str | None, str | None, str | None]] = set()
        for iterable in args:
            for ep in iterable:
                key = (ep.group, ep.name, ep.value)
                if key in seen:
                    continue
                seen.add(key)
                merged.append(ep)
        return EntryPoints(merged)
