"""PaKeT logging."""
import logging
import os

import coloredlogs

LOG_DIR_NAME = './'
LOG_FILE_NAME = 'paket.log'
FORMAT = '%(asctime)s %(levelname).3s: %(message)s - %(name)s +%(lineno)03d'
DATE_FORMAT = '%Y-%m-%d %H:%M:%S'
LEVEL = logging.DEBUG


def setup():
    """Setup the root logger."""
    # Colored logs for terminal. Do this first, because it messes with the logger's level.
    stream_formatter = coloredlogs.ColoredFormatter(
        fmt=FORMAT, datefmt=DATE_FORMAT, level_styles={
            'info': {'color': 'green'}, 'warning': {'color': 'yellow', 'bold': True},
            'error': {'color': 'red', 'bold': True}, 'critical': {'color': 'red', 'bold': True},
        }, field_styles={'name': {'color': 'cyan'}, 'lineno': {'color': 'cyan'}})
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(stream_formatter)

    # Logging to file.
    file_formatter = logging.Formatter(FORMAT, DATE_FORMAT)
    file_handler = logging.FileHandler(os.path.join(LOG_DIR_NAME, LOG_FILE_NAME))
    file_handler.setFormatter(file_formatter)

    # Remove werkzeug and flask default handlers.
    logging.getLogger('werkzeug').handlers = []
    logging.getLogger('flask').handlers = []

    logger = logging.getLogger()
    logger.handlers = []
    logger.addHandler(stream_handler)
    logger.addHandler(file_handler)
    logger.setLevel(LEVEL)
