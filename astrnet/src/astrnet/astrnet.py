from taskiq import AsyncBroker


class AstrNet:
    """AstrNet应用类, 底层基于TaskIQ."""
    broker: AsyncBroker
    def __init__(self,broker: AsyncBroker) -> None:
        """ 初始化AstrNet应用. """
        self.broker = broker


