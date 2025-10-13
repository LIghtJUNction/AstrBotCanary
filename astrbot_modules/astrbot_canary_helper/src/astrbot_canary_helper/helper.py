from importlib.metadata import entry_points, EntryPoint , EntryPoints

class AstrbotCanaryHelper:
    eps = entry_points()
    @classmethod
    def getSingleEntryPoint(cls, group: str,name: str) -> EntryPoint | None:
        """获取指定组-名字的单个入口点"""
        for ep in cls.eps.select(group=group,name=name):
            return ep
        return None

    @classmethod
    def getAllEntryPoints(cls, group: str) -> EntryPoints:
        """获取指定组的所有入口点
        eps = entry_points()  # 获取所有入口点
        """
        return cls.eps.select(group=group)

    @classmethod
    def getMultiGroupAllEntryPoints(cls, groups: list[str]) -> EntryPoints:
        """获取多个组的所有入口点，返回合并后的列表"""
        _ : list[EntryPoints] = []
        for group in groups:
            _eps = cls.eps.select(group=group)
            _ .append(_eps)
        return cls.mergeEntryPoints(*_)
            
    @staticmethod
    def mergeEntryPoints(*args: EntryPoints) -> EntryPoints:
        """合并多个 EntryPoints 对象"""
        merged_list: list[EntryPoint] = []
        for eps in args:
            merged_list.extend(eps)
        return EntryPoints(merged_list)
    
