import logging
import logging.config
import logging.handlers
import random

from boa.definitions import PathLike

DEFAULT_LOG_LEVEL: int = logging.INFO
ROOT_LOGGER_NAME = "boa"


def worker_process(q):
    qh = logging.handlers.QueueHandler(q)
    root = logging.getLogger()
    root.setLevel(logging.DEBUG)
    root.addHandler(qh)
    levels = [logging.DEBUG, logging.INFO, logging.WARNING, logging.ERROR, logging.CRITICAL]
    loggers = ["foo", "foo.bar", "foo.bar.baz", "spam", "spam.ham", "spam.ham.eggs"]
    for i in range(100):
        lvl = random.choice(levels)
        logger = logging.getLogger(random.choice(loggers))
        logger.log(lvl, "Message no. %d", i)


def get_logger(name: str = ROOT_LOGGER_NAME, level: int = DEFAULT_LOG_LEVEL, filename=None) -> logging.Logger:
    """Get a logger.

    To set a human-readable "output_name" that appears in logger outputs,
    add `{"output_name": "[MY_OUTPUT_NAME]"}` to the logger's contextual
    information. By default, we use the logger's `name`

    NOTE: To change the log level on particular outputs (e.g. STDERR logs),
    set the proper log level on the relevant handler, instead of the logger
    e.g. logger.handers[0].setLevel(INFO)

    Args:
        name: The name of the logger.

    Returns:
        The logging.Logger object.
    """
    logger = logging.getLogger(name)
    logger = set_handlers(logger=logger, level=level, filename=filename)
    logger.setLevel(level)

    return logger


def set_handlers(logger, level=DEFAULT_LOG_LEVEL, filename=None):
    if not any(isinstance(h, logging.StreamHandler) for h in logger.handlers):
        sh: logging.StreamHandler = build_stream_handler(level=level)
        logger.addHandler(sh)

    if filename is not None:
        fh = build_file_handler(level=level, filename=filename)
        logger.addHandler(fh)

    return logger


def get_formatter():
    fmt = "[%(levelname)s %(asctime)s %(processName)s] %(name)s: %(message)s"
    formatter = logging.Formatter(fmt=fmt)
    return formatter


def build_stream_handler(level: int = DEFAULT_LOG_LEVEL) -> logging.StreamHandler:
    """Build the default stream handler used for most BOA logging. Sets
    default level to INFO, instead of WARNING.

    Args:
        level: The log level. By default, sets level to INFO

    Returns:
        A logging.StreamHandler instance
    """
    handler = logging.StreamHandler()
    handler.setLevel(level=level)
    formatter = get_formatter()
    handler.setFormatter(formatter)
    return handler


def build_file_handler(filename: PathLike, level: int = DEFAULT_LOG_LEVEL) -> logging.handlers.QueueHandler:
    handler = logging.FileHandler(filename)
    handler.setLevel(level=level)
    formatter = get_formatter()
    handler.setFormatter(formatter)
    return handler
