import sys
import os

sys.path.insert(0, os.path.join(os.getcwd(), '..'))
import logging.handlers
from common.variables import LOGGING_LEVEL

client_formatter = logging.Formatter('%(asctime)s %(levelname)s %(filename)s %(message)s')
path = os.path.dirname(os.path.abspath(__file__))
path = os.path.join(path, 'client.log')

# logstream = logging.StreamHandler()
# logstream.setFormatter(client_formatter)
# logstream.setLevel(logging.DEBUG)

logfile = logging.handlers.TimedRotatingFileHandler(path, encoding='utf-8', interval=1, when='D')
logfile.setFormatter(client_formatter)

logger = logging.getLogger('client')
# logger.addHandler(logstream)
logger.addHandler(logfile)
logger.setLevel(LOGGING_LEVEL)

if __name__ == '__main__':
    logger.debug('debug message')
    logger.info('info message')
    logger.warning('warning message')
    logger.error('error message')
    logger.critical('critical message')
