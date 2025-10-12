from __future__ import annotations
from typing import Any, cast
import uuid
import time
from collections.abc import Sequence, Mapping, Callable
from datetime import datetime
from anyio import to_thread
from celery import Celery  # type: ignore
from astrbot_canary_api.interface import (
    IAstrbotTaskScheduler,
    TaskID,
    ResultHandleProtocol,
    TaskTimeoutError,
    TaskNotFoundError
)
__all__ = [
    "CeleryResultHandle",
    "InMemoryResultHandle", 
    "CeleryTaskScheduler", 
    "TaskTimeoutError", 
    "TaskNotFoundError", 
    "TaskID"
]

class CeleryResultHandle(ResultHandleProtocol):
    def __init__(self, async_result: Any) -> None:
        self._r = async_result
        # metadata to mirror InMemoryResultHandle for unified API
        self.metadata: dict[str, Any] = {
            "task_id": str(getattr(self._r, 'id', None)),
            "task_name": None,
            "args": None,
            "kwargs": None,
            "created_at": time.time(),
        }
    def id(self) -> TaskID:
        return str(self._r.id)
    def ready(self) -> bool:
        return bool(self._r.ready())
    def get(self, timeout: float | None = None) -> Any:
        try:
            return self._r.get(timeout=timeout)
        except Exception as e:  # pragma: no cover - external runtime behavior
            # Celery raises various exceptions; wrap timeouts specifically
            if isinstance(e, TimeoutError):
                raise TaskTimeoutError() from e
            raise

    def with_task(self, task_name: str | None, args: Sequence[Any] | None = None, kwargs: Mapping[str, Any] | None = None) -> "CeleryResultHandle":
        """Attach optional metadata so callers can treat CeleryResultHandle
        and InMemoryResultHandle uniformly."""
        self.metadata["task_name"] = task_name
        self.metadata["args"] = tuple(args or ())
        self.metadata["kwargs"] = dict(kwargs or {})
        return self

class InMemoryResultHandle(ResultHandleProtocol):
    """Wrap a direct in-process result so callers can use the same API."""
    def __init__(self, result: Any, task_id: TaskID | None = None) -> None:
        self._result = result
        # generate a unique id with a uuid prefix for better traceability
        self._id = task_id or f"inmemory-{uuid.uuid4()}"
        self._ready = True
        # metadata for debugging/logging
        self.metadata: dict[str, Any] = {
            "task_id": str(self._id),
            "task_name": None,
            "args": None,
            "kwargs": None,
            "created_at": time.time(),
        }
    def with_task(self, task_name: str | None, args: Sequence[Any] | None = None, kwargs: Mapping[str, Any] | None = None) -> "InMemoryResultHandle":
        # attach task metadata and return self for fluent use
        self.metadata["task_name"] = task_name
        self.metadata["args"] = tuple(args or ())
        self.metadata["kwargs"] = dict(kwargs or {})
        return self
    def id(self) -> TaskID:
        return str(self._id)
    def ready(self) -> bool:
        return True
    def get(self, timeout: float | None = None) -> Any:
        return self._result

class CeleryTaskScheduler(IAstrbotTaskScheduler):
    """Celery-backed IAstrbotTaskScheduler adapter.
    Usage: scheduler = CeleryTaskScheduler(broker='amqp://guest@localhost//', backend='rpc://')
    """
    def __init__(self, broker: str | None = None, backend: str | None = None, app: Any | None = None, **opts: Any) -> None:
        # Use Any for app to avoid static type failures when Celery stubs are absent
        if app is not None:
            self.app: Any = app
        else:
            if broker is None:
                raise ValueError("broker is required when no Celery app is provided")
            self.app = Celery("astrbot", broker=broker, backend=backend, **opts)
    def send_task(self,
                  name: str,
                  args: Sequence[Any] | None = None,
                  kwargs: Mapping[str, Any] | None = None,
                  queue: str | None = None,
                  retry: bool = False,
                  countdown: float | None = None,
                  headers: Mapping[str, Any] | None = None,
                  ) -> TaskID | ResultHandleProtocol:
        args = tuple(args or ())
        kwargs = dict(kwargs or {})
        # If Celery is configured eager (single-process/demo), prefer calling the
        # registered task object's apply_async so the task runs locally instead of
        # being sent to a broker which would require a worker.
        try:
            eager = bool(self.app.conf.get('task_always_eager'))
        except Exception:
            eager = False

        # Try to resolve a registered task object by name. If found, use its
        # apply_async so behavior is consistent between eager (in-process)
        # and non-eager (worker) modes. Only fall back to app.send_task when
        # the name is not registered (or when the caller explicitly wants
        # send_task semantics).
        task_obj = getattr(self.app, 'tasks', {}).get(name)  # type: ignore[attr-defined]
        if task_obj is not None:
            # eager: prefer direct run to return an in-memory handle
            if eager:
                run_fn = getattr(task_obj, 'run', None)
                if callable(run_fn):
                    result = run_fn(*tuple(args), **dict(kwargs))
                    return InMemoryResultHandle(result).with_task(name, args, kwargs)
            # non-eager or eager but no run(): dispatch via task.apply_async
            try:
                ar = task_obj.apply_async(args=args, kwargs=kwargs, queue=queue)  # type: ignore[attr-defined]
            except Exception:
                # If apply_async fails for some reason, fall back to send_task
                ar = self.app.send_task(name, args=args, kwargs=kwargs, queue=queue, countdown=countdown, headers=headers)  # type: ignore[attr-defined]
            return CeleryResultHandle(ar)

        # Fallback: name not found among registered tasks -> use send_task
        ar = self.app.send_task(name, args=args, kwargs=kwargs, queue=queue, countdown=countdown, headers=headers)  # type: ignore[attr-defined]
        return CeleryResultHandle(ar)
    async def async_send_task(self,
                              name: str,
                              args: Sequence[Any] | None = None,
                              kwargs: Mapping[str, Any] | None = None,
                              queue: str | None = None,
                              retry: bool = False,
                              countdown: float | None = None,
                              headers: Mapping[str, Any] | None = None,
                              ) -> TaskID | ResultHandleProtocol:
        # Prefer the apply_async path (which in eager mode will execute locally)
        # Use async_apply_async which already wraps apply_async in a thread.
        return await self.async_apply_async(name, args=args, kwargs=kwargs, queue=queue, registered_only=False)
    def apply_async(self,
                    func: Callable[..., Any] | str,
                    args: Sequence[Any] | None = None,
                    kwargs: Mapping[str, Any] | None = None,
                    queue: str | None = None,
                    registered_only: bool = True,
                    ) -> TaskID | ResultHandleProtocol:
        args = tuple(args or ())
        kwargs = dict(kwargs or {})
        # If func is a string, treat as registered task name
        if isinstance(func, str):
            # Resolve registered task object first to unify behavior between
            # same-process (eager) and cross-process usage. If not found,
            # fall back to send_task which targets the broker directly.
            try:
                eager = bool(self.app.conf.get('task_always_eager'))
            except Exception:
                eager = False

            task_obj = getattr(self.app, 'tasks', {}).get(func)  # type: ignore[attr-defined]
            if task_obj is not None:
                if eager:
                    run_fn = getattr(task_obj, 'run', None)
                    if callable(run_fn):
                        result = run_fn(*tuple(args), **dict(kwargs))
                        return InMemoryResultHandle(result).with_task(func, args, kwargs)
                ar = task_obj.apply_async(args=args, kwargs=kwargs, queue=queue)  # type: ignore[attr-defined]
                return CeleryResultHandle(ar)

            # Not registered: fall back to send_task (cross-process semantics)
            ar = self.app.send_task(func, args=args, kwargs=kwargs, queue=queue)  # type: ignore[attr-defined]
            return CeleryResultHandle(ar)
        # If Celery task object (has apply_async), call it
        apply_async = getattr(func, "apply_async", None)
        if callable(apply_async):
            # If the passed-in func looks like a Celery task object and we're
            # in eager mode prefer calling its run() directly; otherwise call
            # apply_async and return a CeleryResultHandle.
            try:
                # check eager flag again to decide behavior
                try:
                    eager = bool(self.app.conf.get('task_always_eager'))
                except Exception:
                    eager = False
                if eager:
                    run_fn = getattr(func, 'run', None)
                    if callable(run_fn):
                        result = run_fn(*tuple(args), **dict(kwargs))
                        return InMemoryResultHandle(result)
                ar = func.apply_async(args=args, kwargs=kwargs, queue=queue)  # type: ignore[attr-defined]
                return CeleryResultHandle(ar)
            except Exception:
                # Fallback to calling run directly if available
                run_fn = getattr(func, 'run', None)
                if callable(run_fn):
                    result = run_fn(*tuple(args), **dict(kwargs))
                    return InMemoryResultHandle(result)
                raise
        if registered_only:
            raise RuntimeError("apply_async requires a registered Celery task or task name when registered_only=True")
        # Not supported to auto-register arbitrary callables
        raise RuntimeError("apply_async cannot submit unregistered callables in Celery adapter")
    async def async_apply_async(self,
                                func: Callable[..., Any] | str,
                                args: Sequence[Any] | None = None,
                                kwargs: Mapping[str, Any] | None = None,
                                queue: str | None = None,
                                registered_only: bool = True,
                                ) -> TaskID | ResultHandleProtocol:
        return await to_thread.run_sync(self.apply_async, func, args, kwargs, queue, registered_only)
    def schedule(self,
                 name: str,
                 eta: datetime | float | None = None,
                 cron: str | None = None,
                 args: Sequence[Any] | None = None,
                 kwargs: Mapping[str, Any] | None = None,
                 ) -> TaskID | ResultHandleProtocol:
        # Map eta/cron to Celery countdown/eta; cron scheduling typically uses celery beat (out of scope)
        args = tuple(args or ())
        kwargs = dict(kwargs or {})
        if isinstance(eta, (int, float)):
            ar = self.app.send_task(name, args=args, kwargs=kwargs, countdown=float(eta))  # type: ignore[attr-defined]
            return CeleryResultHandle(ar)
        if isinstance(eta, datetime):
            ar = self.app.send_task(name, args=args, kwargs=kwargs, eta=eta)  # type: ignore[attr-defined]
            return CeleryResultHandle(ar)
        raise RuntimeError("schedule: provide eta (datetime or seconds) or use external periodic scheduler (celery beat) for cron")
    def get_result(self, task_id: TaskID, timeout: float | None = None) -> Any:
        ar = self.app.AsyncResult(task_id)  # type: ignore[attr-defined]
        try:
            return ar.get(timeout=timeout)
        except Exception as e:  # pragma: no cover - external runtime behavior
            if isinstance(e, TimeoutError):
                raise TaskTimeoutError() from e
            raise
    async def async_get_result(self, task_id: TaskID, timeout: float | None = None) -> Any:
        return await to_thread.run_sync(self.get_result, task_id, timeout)
    def revoke(self, task_id: TaskID, terminate: bool = False) -> None:
        # control.revoke accepts terminate flag
        self.app.control.revoke(task_id, terminate=terminate)  # type: ignore[attr-defined]
    async def async_revoke(self, task_id: TaskID, terminate: bool = False) -> None:
        return await to_thread.run_sync(self.revoke, task_id, terminate)
    def inspect_workers(self) -> Mapping[str, Any]:
        insp = self.app.control.inspect()  # type: ignore[attr-defined]
        # Return summary structure with available information
        try:
            active = cast(Mapping[str, Any], insp.active() or {})
            registered = cast(Mapping[str, Any], insp.registered() or {})
            
            return {"active": active, "registered": registered}
        except Exception:
            return {}
    async def async_inspect_workers(self) -> Mapping[str, Any]:
        return await to_thread.run_sync(self.inspect_workers)
    def close(self) -> None:
        # Celery app doesn't need explicit close; if custom resources exist, user should manage them
        return None
    async def async_close(self) -> None:
        return None