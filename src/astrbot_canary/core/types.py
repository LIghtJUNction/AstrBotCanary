from taskiq import InMemoryBroker, ZeroMQBroker
from taskiq_aio_pika import AioPikaBroker
from taskiq_nats import NatsBroker, PullBasedJetStreamBroker, PushBasedJetStreamBroker
from taskiq_redis import RedisStreamBroker

__all__ = [
    "BROKER_TYPE",
]

type BROKER_TYPE = InMemoryBroker | AioPikaBroker | RedisStreamBroker | ZeroMQBroker | NatsBroker | PushBasedJetStreamBroker | PullBasedJetStreamBroker