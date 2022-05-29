import argparse
import json
import socket
import sys
import time
from common.variables import ACTION, PRESENCE, TIME, USER, ACCOUNT_NAME, RESPONSE, ERROR, DEFAULT_IP_ADDRESS, \
    DEFAULT_PORT, SENDER, MESSAGE_TEXT, MESSAGE
from common.utils import get_message, send_message
import logging

from errors import ServerError, ReqFieldMissingError
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
        elif message[RESPONSE] == 400:
            raise ServerError(f'400 : {message[ERROR]}')
    raise ReqFieldMissingError(RESPONSE)


@log
def message_from_server(message):
    """Функция - обработчик сообщений других пользователей, поступающих с сервера"""
    if ACTION in message and message[ACTION] == MESSAGE and \
            SENDER in message and MESSAGE_TEXT in message:
        print(f'Получено сообщение от пользователя '
              f'{message[SENDER]}:\n{message[MESSAGE_TEXT]}')
        CLIENT_LOGGER.info(f'Получено сообщение от пользователя '
                           f'{message[SENDER]}:\n{message[MESSAGE_TEXT]}')
    else:
        CLIENT_LOGGER.error(f'Получено некорректное сообщение с сервера: {message}')


@log
def create_message(sock, account_name='Guest'):
    """Функция запрашивает текст сообщения и возвращает его."""
    message = input('Введите сообщение для отправки или \'!!!\' для завершения работы: ')
    if message == '!!!':
        sock.close()
        CLIENT_LOGGER.info('Завершение работы по команде пользователя.')
        print('Пока!')
        sys.exit(0)
    message_dict = {
        ACTION: MESSAGE,
        TIME: time.time(),
        ACCOUNT_NAME: account_name,
        MESSAGE_TEXT: message
    }
    CLIENT_LOGGER.debug(f'Сформирован словарь сообщения: {message_dict}')
    return message_dict


@log
def arg_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument('addr', default=DEFAULT_IP_ADDRESS, nargs='?')
    parser.add_argument('port', default=DEFAULT_PORT, type=int, nargs='?')
    parser.add_argument('-m', '--mode', default='listen', nargs='?')
    namespace = parser.parse_args(sys.argv[1:])
    server_address = namespace.addr
    server_port = namespace.port
    client_mode = namespace.mode

    if server_port < 1024 or server_port > 65535:
        CLIENT_LOGGER.critical(f'Неподходящий номер порта: {server_port}')
        sys.exit(1)

    if client_mode not in ('listen', 'send'):
        CLIENT_LOGGER.critical(f'Недопустимый режим работы {client_mode}')
        sys.exit(1)

    return server_address, server_port, client_mode


def main():
    # Загрузка параметров командной строки
    # try:
    #     server_address = sys.argv[1]
    #     server_port = int(sys.argv[2])
    #     if server_port < 1024 or server_port > 65535:
    #         CLIENT_LOGGER.critical(f'Неподходящий номер порта: {server_port}')
    #         raise ValueError
    # except IndexError:
    #     server_address = DEFAULT_IP_ADDRESS
    #     server_port = DEFAULT_PORT
    # except ValueError:
    #     print('В качестве порта может быть указано число в диапазоне от 1024 до 65535.')
    #     sys.exit(1)
    # CLIENT_LOGGER.info(f'Запущен сервер с параметрами {server_address}, {server_port}')

    server_address, server_port, client_mode = arg_parser()
    CLIENT_LOGGER.info(f'Запущен клиент с параметрами: {server_address}, {server_port}, {client_mode}')

    # Сокет и обмен
    try:
        transport = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        transport.connect((server_address, server_port))
        message_to_server = create_presence()
        send_message(transport, create_presence())
        answer = process_ans(get_message(transport))
        CLIENT_LOGGER.info(f'Ответ от сервера: {answer}')
        print(f'Установлено соединение с сервером')
    except (ValueError, json.JSONDecodeError):
        print('Ошибка декодирования сообщения от сервера')
        sys.exit(1)
    except ServerError as error:
        CLIENT_LOGGER.error(f'Сервер вернул ошибку при попытке соединения. Ошибка {error.text}')
        sys.exit(1)
    except ReqFieldMissingError as missing_error:
        CLIENT_LOGGER.error(f'В ответе от сервера отсутствует необходимое поле {missing_error.missing_field}')
        sys.exit(1)
    except ConnectionRefusedError:
        CLIENT_LOGGER.critical(f'Не удалось подключиться к серверу {server_address}, {server_port}')
        sys.exit(1)
    else:
        if client_mode == 'send':
            print('Готов к отправке сообщений!')
        elif client_mode == 'listen':
            print('Готов к приёму сообщений!')
        while True:
            if client_mode == 'send':
                try:
                    send_message(transport, create_message(transport))
                except (ConnectionError, ConnectionResetError, ConnectionAbortedError):
                    CLIENT_LOGGER.error(f'Соединение с сервером {server_address}, {server_port} прервано!')
                    sys.exit(1)
            if client_mode == 'listen':
                try:
                    message_from_server(get_message(transport))
                except (ConnectionError, ConnectionResetError, ConnectionAbortedError):
                    CLIENT_LOGGER.error(f'Соединение с сервером {server_address}, {server_port} прервано!')
                    sys.exit(1)

if __name__ == '__main__':
    main()
