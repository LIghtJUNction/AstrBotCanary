class CannotResolveGenericDependency(Exception):
    """Raised when a generic dependency cannot be resolved.

    This exception can carry optional context about which parameter and
    parent dependency failed to provide a concrete generic type. When that
    extra context is provided, the message mirrors the original ValueError
    message used in the codebase.
    """

    def __init__(
        self,
        dependency: object,
        param_name: str | None = None,
        parent: object | None = None,
    ) -> None:
        if param_name is not None and parent is not None:
            # Preserve the original, detailed message for callers that
            # relied on the three-argument ValueError format.
            message = (
                f"Unknown generic argument {dependency}. "
                f"Please provide a type in param `{param_name}` of `{parent}`"
            )
        else:
            message = (
                f"Cannot resolve generic dependency: {dependency!r}. "
                "Make sure to provide concrete types for all generic parameters."
            )
        super().__init__(message)


class CannotResolveDependency(Exception):
    """Raised when a dependency parameter cannot be resolved from annotations.

    This mirrors the original ValueError message used across the codebase and
    accepts explicit strings for module and dependency names to produce a
    stable, testable error message.
    """

    def __init__(self, param_name: str, owner_module: str, owner_name: str) -> None:
        message = (
            f"The dependency {param_name} of "
            f"{owner_module}:{owner_name} cannot be resolved."
        )
        super().__init__(message)
