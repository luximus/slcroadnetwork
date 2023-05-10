import logging
import tqdm


class TqdmLoggingHandler(logging.Handler):
    def __init__(self, level=logging.NOTSET):
        super().__init__(level)

    def emit(self, record) -> None:
        # noinspection PyBroadException
        try:
            msg = self.format(record)
            tqdm.tqdm.write(msg)
            self.flush()
        except Exception:
            self.handleError(record)


def create_handler(level: str | int) -> logging.StreamHandler:
    handler = logging.StreamHandler()
    handler.setLevel(level)
    return handler
