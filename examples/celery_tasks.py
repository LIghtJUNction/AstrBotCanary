"""Example Celery tasks used by notebooks/examples.

This file configures a Celery app in eager (in-process) mode by default so the
notebook examples can run without an external broker or worker. To switch to a
real broker (RabbitMQ/Redis), change the broker/backend arguments when creating
`app` or override `app.conf.task_always_eager`.
"""
from celery import Celery # type: ignore
from typing import Any

# Eager (in-process) configuration is ideal for demos/tests inside a notebook.
# To use a real broker, replace broker='memory://' with e.g. 'amqp://guest@localhost//'
app: Any = Celery('examples.tasks', broker='memory://', backend='cache+memory://')
# Prefer explicit eager flag for notebooks/tests
# Use cache+memory backend so results are stored short-term in-process
# (suitable for demos/notebooks; not persistent across process restarts)
app.conf.update(task_always_eager=True, task_eager_propagates=True)

@app.task(name='examples.hello')
def hello(name: str = 'world') -> str:
    """Return a greeting string. Used by examples and notebooks.

    This runs immediately when `task_always_eager=True`.
    """
    return f'hello {name}'
