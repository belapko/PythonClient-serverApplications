import argparse
import json
import socket
import sys
import threading
import time
from common.variables import ACTION, PRESENCE, TIME, USER, ACCOUNT_NAME, RESPONSE, ERROR, DEFAULT_IP_ADDRESS, \
    DEFAULT_PORT, SENDER, MESSAGE_TEXT, MESSAGE, DESTINATION, EXIT
from common.utils import get_message, send_message
import logging

from errors import ServerError, ReqFieldMissingError
from logs import config_client_log
from log_decorator import log

CLIENT_LOGGER = logging.getLogger('client')


@log
def create_presence(account_name):  # Генерация запроса о присутствии клиента
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
def message_from_server(sock, my_username):
    """Функция - обработчик сообщений других пользователей, поступающих с сервера"""
    while True:
        try:
            message = get_message(sock)
            if ACTION in message and message[ACTION] == MESSAGE and \
                    SENDER in message and MESSAGE_TEXT in message and DESTINATION in message and message[DESTINATION] == my_username:
                print(f'\nПолучено сообщение от пользователя '
                      f'{message[SENDER]}:\n{message[MESSAGE_TEXT]}')
                CLIENT_LOGGER.info(f'Получено сообщение от пользователя '
                                   f'{message[SENDER]}:\n{message[MESSAGE_TEXT]}')
                print(f'Введите команду: ')
            else:
                CLIENT_LOGGER.error(f'Получено некорректное сообщение с сервера: {message}')
        except (OSError, ConnectionError, ConnectionAbortedError, ConnectionResetError, json.JSONDecodeError):
            CLIENT_LOGGER.critical(f'Потеряно соединение с сервером')
            break


@log
def create_message(sock, account_name):
    """Функция запрашивает текст сообщения и возвращает его."""
    to_user = input('Введите получателя: ')
    message = input('Введите сообщение: ')
    message_dict = {
        ACTION: MESSAGE,
        SENDER: account_name,
        DESTINATION: to_user,
        TIME: time.time(),
        MESSAGE_TEXT: message
    }
    CLIENT_LOGGER.debug(f'Сформирован словарь сообщения: {message_dict}')
    try:
        send_message(sock, message_dict)
    except Exception as e:
        print(e)
        CLIENT_LOGGER.critical(f'Потеряно соединение с сервером')
        sys.exit(1)

@log
def create_exit_message(account_name):
    """Функция создаёт словарь с сообщением о выходе"""
    return {
        ACTION: EXIT,
        TIME: time.time(),
        ACCOUNT_NAME: account_name
    }

def print_help():
    print('Поддерживаемые команды:')
    print('message - отправить сообщение. Кому и текст будет запрошены отдельно.')
    print('help - вывести подсказки по командам')
    print('exit - выход из программы')

@log
def user_interactive(sock, username):
    while True:
        command = input('Введите команду: ')
        if command == 'message':
            create_message(sock, username)
        elif command == 'help':
            print_help()
        elif command == 'exit':
            send_message(sock, create_exit_message(username))
            print('Завершение соединения.')
            CLIENT_LOGGER.info('Завершение работы по команде пользователя.')
            # Задержка неоходима, чтобы успело уйти сообщение о выходе
            time.sleep(0.5)
            break
        else:
            print('Команда не распознана, попробойте снова. help - вывести поддерживаемые команды.')

@log
def arg_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument('addr', default=DEFAULT_IP_ADDRESS, nargs='?')
    parser.add_argument('port', default=DEFAULT_PORT, type=int, nargs='?')
    parser.add_argument('-n', '--name', nargs='?')
    namespace = parser.parse_args(sys.argv[1:])
    server_address = namespace.addr
    server_port = namespace.port
    client_name = namespace.name

    if server_port < 1024 or server_port > 65535:
        CLIENT_LOGGER.critical(f'Неподходящий номер порта: {server_port}')
        sys.exit(1)

    return server_address, server_port, client_name

def main():
    server_address, server_port, client_name = arg_parser()
    if not client_name:
        client_name = input('Введите имя пользователя: ')
    CLIENT_LOGGER.info(f'Запущен клиент с параметрами: {server_address}, {server_port}, {client_name}')

    print(f'Консольный месседжер. Клиентский модуль. Имя пользователя: {client_name}')
    print_help()

    # Сокет и обмен
    try:
        transport = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        transport.connect((server_address, server_port))
        send_message(transport, create_presence(client_name))
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
        # if client_mode == 'send':
        #     print('Готов к отправке сообщений!')
        # elif client_mode == 'listen':
        #     print('Готов к приёму сообщений!')
        # while True:
        #     if client_mode == 'send':
        #         try:
        #             send_message(transport, create_message(transport))
        #         except (ConnectionError, ConnectionResetError, ConnectionAbortedError):
        #             CLIENT_LOGGER.error(f'Соединение с сервером {server_address}, {server_port} прервано!')
        #             sys.exit(1)
        #     if client_mode == 'listen':
        #         try:
        #             message_from_server(get_message(transport))
        #         except (ConnectionError, ConnectionResetError, ConnectionAbortedError):
        #             CLIENT_LOGGER.error(f'Соединение с сервером {server_address}, {server_port} прервано!')
        #             sys.exit(1)
        receiver = threading.Thread(target=message_from_server, args=(transport, client_name))
        receiver.daemon = True
        receiver.start()

        user_interface = threading.Thread(target=user_interactive, args=(transport, client_name))
        user_interface.daemon = True
        user_interface.start()
        CLIENT_LOGGER.debug(f'Запущены потоки')

        while True:
            time.sleep(1)
            if receiver.is_alive() and user_interface.is_alive():
                continue
            break

if __name__ == '__main__':
    main()
