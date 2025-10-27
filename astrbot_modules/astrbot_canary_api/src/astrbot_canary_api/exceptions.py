#region AstrbotSecret
class SecretError(Exception):
    """Raised when a secret key is not found in the backend.

    可选参数:
      - key_id: 相关密钥标识
      - backend: 使用的密钥后端名称
      - cause: 原始异常
    """
    def __init__(
        self,
        message: str = "Secret key not found",
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