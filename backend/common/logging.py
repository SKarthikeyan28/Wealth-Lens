import logging
import sys

from pythonjsonlogger import jsonlogger


def configure_logging() -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        jsonlogger.JsonFormatter("%(asctime)s %(name)s %(levelname)s %(message)s")
    )
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.handlers = [handler]
