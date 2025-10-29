#region AstrbotSecret
class SecretError(Exception):
    """密钥相关异常.

    可选参数:
      - key_id: 相关密钥标识
      - backend: 使用的密钥后端名称
      - cause: 原始异常
    """
    def __init__(
        self,
        message: str = "Secret key Error",
        *,
        key_id: str | None = None,
        backend: str | None = None,
        cause: Exception | None = None,
    ) -> None:
        self.key_id = key_id
        self.backend = backend
        self.cause = cause

        parts: list[str] = []
        if key_id:
            parts.append(f"key_id={key_id}")
        if backend:
            parts.append(f"backend={backend}")
        if parts:
            message = f"{message} ({', '.join(parts)})"

        super().__init__(message)
        if cause is not None:
            # 保留原始异常为 __cause__ 以便链式异常追踪
            self.__cause__ = cause


#region AstrbotInjector

class ProviderNotSetError(Exception):
    """提供者未设置异常.

    可选参数:
      - provider_name: 未设置的提供者名称
    """
    def __init__(
        self,
        message: str = "Provider not set",
        *,
        provider_name: str | None = None,
    ) -> None:
        self.provider_name = provider_name

        if provider_name:
            message = f"{message}: {provider_name}"

        super().__init__(message)


class AstrbotContainerNotFoundError(Exception):
    """容器未找到异常.

    可选参数:
      - container_name: 未找到的容器名称
    """
    def __init__(
        self,
        message: str = "Container not found",
        *,
        container_name: str | None = None,
    ) -> None:
        self.container_name = container_name

        if container_name:
            message = f"{message}: {container_name}"

        super().__init__(message)


class AstrbotInvalidPathError(Exception):
    """无效路径异常.

    可选参数:
      - path: 无效的路径
    """
    def __init__(
        self,
        message: str = "Invalid path",
        *,
        path: str | None = None,
    ) -> None:
        self.path = path

        if path:
            message = f"{message}: {path}"

        super().__init__(message)


class AstrbotInvalidProviderPathError(Exception):
    """无效的 provider 路径异常.

    可选参数:
      - path: 无效的路径
    """
    def __init__(
        self,
        message: str = "Invalid provider path",
        *,
        path: str | None = None,
    ) -> None:
        self.path = path

        if path:
            message = f"{message}: {path}"

        super().__init__(message)
