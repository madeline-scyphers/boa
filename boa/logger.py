import logging

DEFAULT_LOG_LEVEL: int = logging.WARNING


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

    ch = logging.StreamHandler()
    ch.setLevel(level)
    # create formatter and add it to the handlers
    formatter = get_formatter()
    ch.setFormatter(formatter)
    # add the handlers to the logger
    logger.addHandler(ch)
    return logger


def get_formatter():
    fmt = "[%(levelname)s %(asctime)s] %(output_name)s %(processName)s %(threadName)s: %(message)s"
    formatter = logging.Formatter(fmt=fmt)
    return formatter
