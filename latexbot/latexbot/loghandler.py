import collections
import logging


global_log_queue = collections.deque(maxlen=200)


class CircularLogHandler(logging.Handler):
    """
    A log handler that logs to a deque.
    """

    def __init__(self, queue: collections.deque, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.queue = queue

    def emit(self, record: logging.LogRecord):
        msg = self.format(record)
        self.queue.appendleft(msg)
