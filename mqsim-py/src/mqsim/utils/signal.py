class Signal:
    """
    A simple implementation of the Observer pattern to mirror
    MQSim's function-pointer based signals.
    """
    def __init__(self):
        self._handlers = []

    def connect(self, handler):
        self._handlers.append(handler)

    def fire(self, *args, **kwargs):
        for handler in self._handlers:
            handler(*args, **kwargs)
