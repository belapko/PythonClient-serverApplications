import json
import socket
import sys
import time
from common.variables import ACTION, PRESENCE, TIME, USER, ACCOUNT_NAME, RESPONSE, ERROR, DEFAULT_IP_ADDRESS, \
    DEFAULT_PORT
from common.utils import get_message, send_message
import logging
from logs import config_client_log
from log_decorator import log

CLIENT_LOGGER = logging.getLogger('client')

@log
def create_presence(account_name='Guest'):  # Генерация запроса о присутствии клиента
    out = {
        ACTION: PRESENCE,
        TIME: time.time(),
        USER: {
            ACCOUNT_NAME: account_name
        }
    }
    CLIENT_LOGGER.debug(f'Сформировано {PRESENCE} сообщение для пользователя {ACCOUNT_NAME}')
    return out

@log
def process_ans(message):  # Разбор ответа от сервера
    CLIENT_LOGGER.debug(f'Разбор сообщения от сервера: {message}')
    if RESPONSE in message:
        if message[RESPONSE] == 200:
            return '200 : OK'
        return f'400 : {message[ERROR]}'
    raise ValueError


def main():
    # Загрузка параметров командной строки
    try:
        server_address = sys.argv[1]
        server_port = int(sys.argv[2])
        if server_port < 1024 or server_port > 65535:
            CLIENT_LOGGER.critical(f'Неподходящий номер порта: {server_port}')
            raise ValueError
    except IndexError:
        server_address = DEFAULT_IP_ADDRESS
        server_port = DEFAULT_PORT
    except ValueError:
        print('В качестве порта может быть указано число в диапазоне от 1024 до 65535.')
        sys.exit(1)
    CLIENT_LOGGER.info(f'Запущен сервер с параметрами {server_address}, {server_port}')

    # Сокет и обмен
    transport = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    transport.connect((server_address, server_port))
    message_to_server = create_presence()
    send_message(transport, message_to_server)
    try:
        answer = process_ans(get_message(transport))
        CLIENT_LOGGER.info(f'Ответ от сервера: {answer}')
        print(answer)
    except (ValueError, json.JSONDecodeError):
        print('Ошибка декодирования сообщения от сервера')


if __name__ == '__main__':
    main()
