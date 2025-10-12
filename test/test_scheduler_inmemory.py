
from astrbot_canary_api.scheduler import CeleryResultHandle, CeleryTaskScheduler
import importlib


def test_immediate_result_handle_metadata():
    # When creating a CeleryResultHandle wrapping an immediate result,
    # the internal id uses the immediate- prefix by default.
    h = CeleryResultHandle('ok')
    # id should include prefix and be unique-ish
    assert h.id().startswith('immediate-')
    assert h.ready() is True
    assert h.get() == 'ok'
    # with_task attaches metadata
    h.with_task('examples.hello', args=('a',), kwargs={'k': 1})
    assert h.metadata['task_name'] == 'examples.hello'
    assert h.metadata['args'] == ('a',)
    assert h.metadata['kwargs'] == {'k': 1}


def test_scheduler_eager_apply_and_send(tmp_path, monkeypatch):
    # import example tasks and ensure eager mode
    examples = importlib.import_module('examples.celery_tasks')
    app = examples.app
    app.conf.update(task_always_eager=True)
    sched = CeleryTaskScheduler(app=app)

    # apply_async with task object should return InMemoryResultHandle
    h = sched.apply_async(examples.hello, args=('x',))
    assert h.ready() is True
    assert h.get() == 'hello x'

    # send_task by name should also run in-process and return immediate result
    h2 = sched.send_task('examples.hello', args=('y',))
    assert h2.ready() is True
    assert h2.get() == 'hello y'
