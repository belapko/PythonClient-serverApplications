import sys
import logging
import logs.config_client_log, logs.config_server_log
import inspect


def log(func):
    def logger_save(*args, **kwargs):
        logger = logging.getLogger('server' if 'server.py' in sys.argv[0] else 'client')
        logger.debug(f'Вызвана функция {func.__name__} с параметрами {args}, {kwargs} из модуля {func.__module__}\n'
                     f'Вызов из функции {inspect.stack()[1][3]}')
        args_return = func(*args, **kwargs)
        return args_return
    return logger_save

