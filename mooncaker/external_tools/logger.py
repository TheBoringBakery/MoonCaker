import logging
from os import getcwd, path
from . import LOGGER_NAME, LOG_FILENAME


# app.config['LOG_FILENAME'] = LOG_FILENAME
handler = logging.FileHandler(LOG_FILENAME)
handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)-8s %(message)s'))
logger = logging.getLogger(LOGGER_NAME)
logger.setLevel(logging.DEBUG)
logger.addHandler(handler)


def log(domain, level: int, text):
    logger.log(level=level, msg=f"{domain}: "
               + text)


def get_log():
    with open(path.join(getcwd(), LOG_FILENAME)) as logfile:
        return logfile.readlines()
