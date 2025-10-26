import warnings
from collections import defaultdict, deque
from collections.abc import Callable
from graphlib import TopologicalSorter
from inspect import getfile, getsourcelines, isclass, isfunction, signature
from pathlib import Path
from typing import Any, TypeVar, get_type_hints

from fastapi.params import Depends as FastapiDepends

from .ctx import AsyncResolveContext, SyncResolveContext
from .dependency import Dependency
from .exceptions import CannotResolveDependency, CannotResolveGenericDependency
from .utils import ParamInfo


class DependencyGraph:
    """Class to build dependency graph from a function."""

    dep_graph = True

    def __init__(
        self,
        target: Callable[..., Any],
        replaced_deps: dict[Any, Any] | None = None,
    ) -> None:
        self.target = target
        # Ordinary dependencies with cache.
        self.dependencies: dict[Any, list[Dependency]] = defaultdict(list)
        # Dependencies without cache.
        # Can be considered as sub graphs.
        self.subgraphs: dict[Any, DependencyGraph] = {}
        self.ordered_deps: list[Dependency] = []
        self.replaced_deps = replaced_deps
        self._build_graph()

    def is_empty(self) -> bool:
        """
        Checks that target function depends on at least something.

        :return: True if depends.
        """
        return len(self.ordered_deps) <= 1

    def _resolve_generic_origin(self, dep: Dependency, origin: Any) -> Any:
        """Resolve a TypeVar origin against its parent generic arguments.

        Mutates dep.dependency when a matching substituted generic is found and
        returns the resolved origin (or the original origin if nothing to do).
        """
        if not isinstance(origin, TypeVar):
            return origin

        if dep.parent is None:
            raise CannotResolveGenericDependency(dep.dependency)

        parent_cls = dep.parent.dependency
        parent_cls_origin = getattr(parent_cls, "__origin__", None)
        if parent_cls_origin is None:
            raise CannotResolveGenericDependency(
                origin,
                param_name=dep.parent.param_name,
                parent=dep.parent.dependency,
            )

        # We zip together names of parameters and the substituted values
        # for generics.
        generics = zip(
            parent_cls_origin.__parameters__,
            parent_cls.__args__, strict=False,  # type: ignore
        )
        for tvar, type_param in generics:
            if tvar == origin:
                dep.dependency = type_param
                origin = getattr(type_param, "__origin__", None)
                if origin is None:
                    origin = type_param
                break

        return origin

    def _get_hints_and_sign(self, dep: Dependency, origin: Any, signature_kwargs: dict[str, Any]) -> tuple[Any | None, Any | None]:
        """Return (hints, sign) for the given dependency and origin.

        Returns (None, None) when type hints couldn't be resolved and the
        caller should continue to the next dependency.
        """
        # Class case: try to read __annotations__ (avoids evaluating forward refs)
        if isclass(origin):
            try:
                hints = getattr(origin, "__annotations__", {})
            except NameError:
                _, src_lineno = getsourcelines(origin)
                src_file = Path(getfile(origin))
                cwd = Path.cwd()
                if src_file.is_relative_to(cwd):
                    src_file = src_file.relative_to(cwd)
                warnings.warn(
                    "Cannot resolve type hints for "
                    f"a class {origin.__name__} defined "
                    f"at {src_file}:{src_lineno}.",
                    RuntimeWarning,
                    stacklevel=2,
                )
                return None, None

            sign = signature(origin.__init__, **signature_kwargs)
            return hints, sign

        # Function case
        if isfunction(dep.dependency):
            try:
                hints = get_type_hints(dep.dependency)
            except NameError:
                _, src_lineno = getsourcelines(dep.dependency)
                src_file = Path(getfile(dep.dependency))
                cwd = Path.cwd()
                if src_file.is_relative_to(cwd):
                    src_file = src_file.relative_to(cwd)
                warnings.warn(
                    "Cannot resolve type hints for "
                    f"a function {dep.dependency.__name__} defined "
                    f"at {src_file}:{src_lineno}.",
                    RuntimeWarning,
                    stacklevel=2,
                )
                return None, None

            sign = signature(origin, **signature_kwargs)
            return hints, sign

        # Callable object case
        try:
            hints = get_type_hints(dep.dependency.__call__)
        except NameError:
            _, src_lineno = getsourcelines(dep.dependency.__class__)
            src_file = Path(getfile(dep.dependency.__class__))
            cwd = Path.cwd()
            if src_file.is_relative_to(cwd):
                src_file = src_file.relative_to(cwd)
            cls_name = dep.dependency.__class__.__name__
            warnings.warn(
                "Cannot resolve type hints for "
                f"an object of class {cls_name} defined "
                f"at {src_file}:{src_lineno}.",
                RuntimeWarning,
                stacklevel=2,
            )
            return None, None

        sign = signature(origin, **signature_kwargs)
        return hints, sign

    def _prepare_dep(self, dep: Dependency) -> Any | None:
        """Apply replacements and quick skips for a dependency; return origin or None.

        This centralizes small pre-processing steps so the main loop is shorter.
        """
        # If we have replaced dependencies, we need to replace
        # them in the current dependency.
        if self.replaced_deps and dep.dependency in self.replaced_deps:
            dep.dependency = self.replaced_deps[dep.dependency]

        # We can say for sure that ParamInfo doesn't have any dependencies,
        # so we skip it.
        if dep.dependency == ParamInfo:
            return None

        origin = getattr(dep.dependency, "__origin__", None)
        if origin is None:
            origin = dep.dependency

        return origin

    def _collect_param_dependencies(self, dep: Dependency, hints: dict[str, Any], sign: Any, dep_deque: deque[Dependency]) -> None:
        """Iterate over a signature's parameters and populate self.dependencies.

        This extracts the large parameter-processing block from `_build_graph`.
        """
        for param_name, param in sign.parameters.items():
            default_value = param.default
            if hasattr(param.annotation, "__metadata__"):
                # We go backwards, because you may want to override your annotation
                # and the overriden value will appear to be after the original
                # `Depends` annotation.
                for meta in reversed(param.annotation.__metadata__):
                    if isinstance(meta, Dependency):
                        default_value = meta
                        break
                    if isinstance(meta, FastapiDepends):
                        default_value = meta
                        break

            # FastAPI integration: allow using FastAPI's Depends.
            if isinstance(default_value, FastapiDepends):
                default_value = Dependency(
                    dependency=default_value.dependency,
                    use_cache=default_value.use_cache,
                    signature=param,
                )

            # Only proceed if default_value is a Dependency instance.
            if not isinstance(default_value, Dependency):
                continue

            # If user hasn't set the dependency in TaskiqDepends constructor,
            # we need to find variable's type hint.
            if default_value.dependency is None:
                if hints.get(param_name) is None:
                    dep_mod = "unknown"
                    dep_name = "unknown"
                    if dep.dependency is not None:
                        dep_mod = dep.dependency.__module__
                        if isclass(dep.dependency):
                            dep_name = dep.dependency.__class__.__name__
                        else:
                            dep_name = dep.dependency.__name__
                    raise CannotResolveDependency(
                        param_name,
                        dep_mod,
                        dep_name,
                    )
                dependency_func = hints[param_name]
            else:
                dependency_func = default_value.dependency

            dep_obj = Dependency(
                dependency_func,
                use_cache=default_value.use_cache,
                kwargs=default_value.kwargs,
                signature=param,
                parent=dep,
            )
            dep_obj.param_name = param_name

            self.dependencies[dep].append(dep_obj)
            if dep_obj.use_cache:
                dep_deque.append(dep_obj)
            else:
                self.subgraphs[dep_obj] = DependencyGraph(dependency_func)

    def _should_skip_dep(self, dep: Dependency) -> bool:
        """Decide whether a dependency should be skipped early in the loop."""
        if dep in self.dependencies:
            return True
        return dep.dependency is None

    def _process_dep(self, dep: Dependency, dep_deque: deque[Dependency], signature_kwargs: dict[str, Any]) -> None:
        """Process a single dependency: prepare, resolve generics, get hints and collect params."""
        origin = self._prepare_dep(dep)
        if origin is None:
            return

        origin = self._resolve_generic_origin(dep, origin)

        hints, sign = self._get_hints_and_sign(dep, origin, signature_kwargs)
        if hints is None or sign is None:
            return

        self._collect_param_dependencies(dep, hints, sign, dep_deque)

    def async_ctx(
        self,
        initial_cache: dict[Any, Any] | None = None,
        replaced_deps: dict[Any, Any] | None = None,
        *,
        exception_propagation: bool = True,
    ) -> AsyncResolveContext:
        """
        Create dependency resolver context.

        This context is used to actually resolve dependencies.

        :param initial_cache: initial cache dict.
        :param exception_propagation: If true, all found errors within
            context will be propagated to dependencies.
        :param replaced_deps: Dependencies to replace during runtime.
        :return: new resolver context.
        """
        graph = self
        if replaced_deps:
            graph = DependencyGraph(self.target, replaced_deps)
        return AsyncResolveContext(
            graph,
            graph,
            initial_cache,
            exception_propagation=exception_propagation,
        )

    def sync_ctx(
        self,
        initial_cache: dict[Any, Any] | None = None,
        replaced_deps: dict[Any, Any] | None = None,
        *,
        exception_propagation: bool = True,
    ) -> SyncResolveContext:
        """
        Create dependency resolver context.

        This context is used to actually resolve dependencies.

        :param initial_cache: initial cache dict.
        :param exception_propagation: If true, all found errors within
            context will be propagated to dependencies.
        :param replaced_deps: Dependencies to replace during runtime.
        :return: new resolver context.
        """
        graph = self
        if replaced_deps:
            graph = DependencyGraph(self.target, replaced_deps)
        return SyncResolveContext(
            graph,
            graph,
            initial_cache,
            exception_propagation=exception_propagation,
        )

    def _build_graph(self) -> None:
        """
        Builds actual graph.

        This function collects all dependencies
        and adds it the the _deps variable.

        After all dependencies are found,
        it runs topological sort, to get the
        dependency resolving order.

        :raises ValueError: if something happened.
        """
        dep_deque = deque([Dependency(self.target, use_cache=True)])
        # This is for `from __future__ import annotations` support.
        # We need to use `eval_str` argument, because
        # signature of the function is a string, not an object.
        signature_kwargs: dict[str, Any] = {"eval_str": True}

        while dep_deque:
            dep: Dependency = dep_deque.popleft()
            # Delegate early-skip logic to helper.
            if self._should_skip_dep(dep):
                continue

            # Process the dependency: prepare, resolve generics,
            # get hints and collect parameter dependencies.
            # `_process_dep` will append new cache-using deps to
            # `dep_deque` and build subgraphs for non-cached deps.
            self._process_dep(dep, dep_deque, signature_kwargs)

        # Now we perform topological sort of all dependencies.
        # Now we know the order we'll be using to resolve dependencies.
        self.ordered_deps = list(TopologicalSorter(self.dependencies).static_order())
