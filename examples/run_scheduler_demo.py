"""Run a quick demo of CeleryTaskScheduler with the examples.celery_tasks app (eager/memory mode).

This script is intended to be run inside the project's virtualenv. It exercise both
apply_async and send_task paths in eager/in-memory mode and prints results.
"""
from astrbot_canary_api.scheduler import CeleryTaskScheduler

import celery_tasks as mod

app = getattr(mod, 'app')

sched = CeleryTaskScheduler(app=app)

print('App eager?', bool(app.conf.get('task_always_eager')))

# apply_async with task object
h = sched.apply_async(mod.hello, args=('demo-user',))
print('apply_async id', h.id())
print('apply_async ready', h.ready())
print('apply_async result', h.get(timeout=5))

# send_task by name (should fallback to in-process run)
h2 = sched.send_task('examples.hello', args=('demo-send',))
print('send_task id', h2.id())
print('send_task ready', h2.ready())
print('send_task result', h2.get(timeout=5))

print('demo finished')
