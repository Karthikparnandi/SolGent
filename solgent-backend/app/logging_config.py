import logging
import sys

from pythonjsonlogger import jsonlogger


def configure_logging() -> logging.Logger:
    logger = logging.getLogger("solgent")
    logger.setLevel(logging.INFO)

    if logger.handlers:
        return logger

    handler = logging.StreamHandler(sys.stdout)
    formatter = jsonlogger.JsonFormatter(
        "%(asctime)s %(levelname)s %(name)s %(message)s",
        rename_fields={"asctime": "timestamp", "levelname": "level"},
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    return logger


logger = configure_logging()
