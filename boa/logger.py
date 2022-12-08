import logging

DEFAULT_LOG_LEVEL: int = logging.INFO


def get_logger(name: str, level: int = DEFAULT_LOG_LEVEL) -> logging.Logger:
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
    logger.setLevel(level)

    stream_handle: logging.StreamHandler = build_stream_handler()
    logger.addHandler(stream_handle)

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
    console = logging.StreamHandler()
    console.setLevel(level=level)
    formatter = get_formatter()
    console.setFormatter(formatter)
    return console
