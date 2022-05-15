import sys
import os
sys.path.insert(0, os.path.join(os.getcwd(), '..'))
import logging
import logging.handlers
from common.variables import LOGGING_LEVEL

server_formatter = logging.Formatter('%(asctime)s %(levelname)s %(filename)s %(message)s')
path = os.path.dirname(os.path.abspath(__file__))
path = os.path.join(path, 'server.log')

logstream = logging.StreamHandler()
logstream.setFormatter(server_formatter)
logstream.setLevel(logging.DEBUG)

logfile = logging.handlers.TimedRotatingFileHandler(path, encoding='utf8', interval=1, when='D')
logfile.setFormatter(server_formatter)

logger = logging.getLogger('server')
logger.addHandler(logstream)
logger.addHandler(logfile)
logger.setLevel(LOGGING_LEVEL)

if __name__ == '__main__':
    logger.debug('debug message')
    logger.info('info message')
    logger.warning('warning message')
    logger.error('error message')
    logger.critical('critical message')