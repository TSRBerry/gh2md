import logging

logformat = "[%(asctime)s] [%(levelname)s] %(msg)s"
logging.basicConfig(level=logging.INFO, format=logformat)

logger: logging.Logger


def init_logger(logger_name: str):
    global logger
    logger = logging.getLogger(logger_name)
