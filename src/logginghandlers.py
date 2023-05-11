import logging


def create_handler(level: str | int) -> logging.StreamHandler:
    handler = logging.StreamHandler()
    handler.setLevel(level)
    return handler
