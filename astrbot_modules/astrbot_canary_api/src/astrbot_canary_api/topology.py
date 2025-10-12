from __future__ import annotations
from kombu import Exchange, Queue  # type: ignore
# https://github.com/celery/kombu/issues/1511

"""
消息拓扑常量：
其他模块从此处 import，避免重复声明或属性不一致导致的问题。

注意：此模块不要 import msgbus（或其它可能导入此模块的实现），
以免产生循环依赖。
"""

# Exchanges
EXCHANGE_MAIN = Exchange("astrbot", type="direct")
""" 主交换机，所有常规消息使用此交换机。 """

EXCHANGE_EVENTS = Exchange("events", type="topic")
""" 事件交换机。 """

EXCHANGE_BROADCAST = Exchange("broadcasts", type="fanout")
""" 广播交换机。 """


QUEUE_DEFAULT = Queue("astrbot_queue", EXCHANGE_MAIN, routing_key="astrbot_key")
QUEUE_TASKS = Queue("tasks", EXCHANGE_MAIN, routing_key="tasks")
QUEUE_USER_EVENTS = Queue("user-events", EXCHANGE_EVENTS, routing_key="user.*")
QUEUE_SVCA_NOTIFY = Queue("svcA-notify", EXCHANGE_BROADCAST)
QUEUE_SVCB_NOTIFY = Queue("svcB-notify", EXCHANGE_BROADCAST)

__all__ = [
    "EXCHANGE_MAIN",
    "EXCHANGE_EVENTS",
    "EXCHANGE_BROADCAST",
    "QUEUE_DEFAULT",
    "QUEUE_TASKS",
    "QUEUE_USER_EVENTS",
    "QUEUE_SVCA_NOTIFY",
    "QUEUE_SVCB_NOTIFY",
]