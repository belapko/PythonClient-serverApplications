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
from errors import ServerError, ReqFieldMissingError, IncorrectDataReceivedError
from log_decorator import log
from metaclasses import ClientVerifier

CLIENT_LOGGER = logging.getLogger('client')


def print_help():
    print('Поддерживаемые команды:')
    print('message - отправить сообщение')
    print('help - подсказки по командам')
    print('next - выйти')


class ClientSender(threading.Thread, metaclass=ClientVerifier):
    def __init__(self, account_name, sock):
        self.account_name = account_name
        self.sock = sock
        super().__init__()

    # Сообщение о выходе
    def create_exit_message(self):
        return {
            ACTION: EXIT,
            TIME: time.time(),
            ACCOUNT_NAME: self.account_name
        }

    def create_message(self):
        to = input(f'Введите имя получателя: ')
        message = input(f'Введите сообщение: ')
        message_dict = {
            ACTION: MESSAGE,
            SENDER: self.account_name,
            DESTINATION: to,
            TIME: time.time(),
            MESSAGE_TEXT: message
        }
        CLIENT_LOGGER.info(f'Сформирован словарь сообщения: {message_dict}')
        try:
            send_message(self.sock, message_dict)
            CLIENT_LOGGER.info(f'Отправлено сообщение пользователю {to}')
        except:
            CLIENT_LOGGER.critical(f'Потеряно соединение с сервером.')
            exit(1)

    def run(self):
        print_help()
        while True:
            command = input(f'Введите команду: ')
            if command == 'message':
                self.create_message()
            elif command == 'help':
                print_help()
            elif command == 'exit':
                try:
                    send_message(self.sock, self.create_exit_message())
                except:
                    pass
                print(f'Завершение соединения.')
                CLIENT_LOGGER.info(f'Соединение было прервано по запросу пользователя')
                time.sleep(0.5)
                break
            else:
                print(f'Неизвестная команда. Введите "help" для получения списка команд.')


class ClientReader(threading.Thread, metaclass=ClientVerifier):
    def __init__(self, account_name, sock):
        self.account_name = account_name
        self.sock = sock
        super().__init__()

    def run(self):
        while True:
            try:
                message = get_message(self.sock)
                if ACTION in message and message[ACTION] == MESSAGE and SENDER in message and DESTINATION in message \
                        and MESSAGE_TEXT in message and message[DESTINATION] == self.account_name:
                    print(f'\nСообщение от {message[SENDER]}: {message[MESSAGE_TEXT]}')
                    CLIENT_LOGGER.info(f'Получено сообщение от {message[SENDER]}: {message[MESSAGE_TEXT]}')
                else:
                    CLIENT_LOGGER.error(f'Получено некорректное сообщение {message}')
            except IncorrectDataReceivedError:
                CLIENT_LOGGER.error(f'Ошибка декодирования сообщения.')
            except (OSError, ConnectionError, ConnectionAbortedError, ConnectionResetError, json.JSONDecodeError):
                CLIENT_LOGGER.critical(f'Потеряно соединение с сервером.')
                break


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
def process_response_answer(message):  # Разбор ответа от сервера
    CLIENT_LOGGER.debug(f'Разбор сообщения от сервера: {message}')
    if RESPONSE in message:
        if message[RESPONSE] == 200:
            return '200 : OK'
        elif message[RESPONSE] == 400:
            raise ServerError(f'400 : {message[ERROR]}')
    raise ReqFieldMissingError(RESPONSE)


@log
def arg_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument('addr', default=DEFAULT_IP_ADDRESS, nargs='?')
    parser.add_argument('port', default=DEFAULT_PORT, type=int, nargs='?')
    parser.add_argument('-n', '--name', default=None, nargs='?')
    namespace = parser.parse_args(sys.argv[1:])
    server_address = namespace.addr
    server_port = namespace.port
    client_name = namespace.name

    # if server_port < 1024 or server_port > 65535:
    if not 1023 < server_port < 65536:
        CLIENT_LOGGER.critical(f'Неподходящий номер порта: {server_port}')
        sys.exit(1)

    return server_address, server_port, client_name


def main():
    print(f'Клиентский модуль запущен!')

    server_address, server_port, client_name = arg_parser()
    if not client_name:
        client_name = input(f'Введите имя пользователя: ')
    CLIENT_LOGGER.info(f'Запущен клиент с параметрами: {server_address}, {server_port}, {client_name}')
    print(f'Ваше имя пользователя: {client_name}')

    try:
        print(f'Попытка соединения с сервером...')
        transport = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        transport.connect((server_address, server_port))
        send_message(transport, create_presence(client_name))
        answer = process_response_answer(get_message(transport))
        CLIENT_LOGGER.info(f'Установлено соединение с сервером. Ответ сервера: {answer}')
        print(f'Установлено соединение с сервером.')
    except json.JSONDecodeError:
        CLIENT_LOGGER.error(f'Ошибка декодирования полученной json строки.')
        exit(1)
    except ServerError as e:
        CLIENT_LOGGER.error(f'Ошибка при соединении с сервером: {e}')
        exit(1)
    except ReqFieldMissingError as e:
        CLIENT_LOGGER.error(f'Ошибка. Отсутствие необходимого поля в ответе сервера {e.missing_field}')
        exit(1)
    except (ConnectionError, ConnectionRefusedError):
        CLIENT_LOGGER.critical(f'Не удалось подключиться к серверу {server_address}:{server_port}')
        exit(1)
    else:
        # Соединение установлено. Запускаем процесс приёма сообщений
        receiver = ClientReader(account_name=client_name, sock=transport)
        receiver.daemon = True
        receiver.start()

        sender = ClientSender(account_name=client_name, sock=transport)
        sender.daemon = True
        sender.start()

        CLIENT_LOGGER.debug(f'Запущены все процессы.')

        while True:
            time.sleep(1)
            if receiver.is_alive() and sender.is_alive():
                continue
            break


if __name__ == '__main__':
    main()
