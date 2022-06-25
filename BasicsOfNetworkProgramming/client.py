import argparse
import json
import socket
import sys
import threading
import time
from common.variables import ACTION, PRESENCE, TIME, USER, ACCOUNT_NAME, RESPONSE, ERROR, DEFAULT_IP_ADDRESS, \
    DEFAULT_PORT, SENDER, MESSAGE_TEXT, MESSAGE, DESTINATION, EXIT, GET_CONTACTS, LIST_INFO, REMOVE_CONTACT, \
    ADD_CONTACT, USERS_REQUEST
from common.utils import get_message, send_message
import logging
from errors import ServerError, ReqFieldMissingError, IncorrectDataReceivedError
from log_decorator import log
from metaclasses import ClientVerifier
from client_db import ClientStorage

CLIENT_LOGGER = logging.getLogger('client')

sock_lock = threading.Lock()
db_lock = threading.Lock()


def print_help():
    print('Поддерживаемые команды:')
    print('message - отправить сообщение')
    print('history - история сообщений')
    print('contacts - список контактов')
    print('edit - редактирование списка контактов')
    print('help - подсказки по командам')
    print('next - выйти')


class ClientSender(threading.Thread, metaclass=ClientVerifier):
    def __init__(self, account_name, sock, database):
        self.account_name = account_name
        self.sock = sock
        self.database = database
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

        with db_lock:
            if not self.database.is_known_user(to):
                CLIENT_LOGGER.error(f'Попытка отправить сообщение незарегистрированному пользователю {to}')
                return

        message_dict = {
            ACTION: MESSAGE,
            SENDER: self.account_name,
            DESTINATION: to,
            TIME: time.time(),
            MESSAGE_TEXT: message
        }
        CLIENT_LOGGER.info(f'Сформирован словарь сообщения: {message_dict}')

        with db_lock:
            self.database.save_message(self.account_name, to, message)

        with sock_lock:
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
                with sock_lock:
                    try:
                        send_message(self.sock, self.create_exit_message())
                    except:
                        pass
                    print(f'Завершение соединения.')
                    CLIENT_LOGGER.info(f'Соединение было прервано по запросу пользователя')
                    time.sleep(0.5)
                    break
            elif command == 'contacts':
                with db_lock:
                    contacts_list = self.database.get_contacts()
                for contact in contacts_list:
                    print(contact)
            elif command == 'edit':
                self.edit_contacts()
            elif command == 'history':
                self.print_history()
            else:
                print(f'Неизвестная команда. Введите "help" для получения списка команд.')

    def edit_contacts(self):
        answer = input(f'Для удаления введите del, для добавления add: ')
        if answer == 'del':
            edit = input(f'Введите имя контакта для удаления: ')
            with db_lock:
                if self.database.is_known_contact(edit):
                    self.database.del_contact(edit)
                else:
                    CLIENT_LOGGER.error(f'Попытка удаления несуществующего контакта')
        elif answer == 'add':
            edit = input(f'Введите имя контакта для создания: ')
            if self.database.is_known_user(edit):
                with db_lock:
                    self.database.add_contact(edit)
                with sock_lock:
                    try:
                        add_contact(self.sock, self.account_name, edit)
                    except ServerError:
                        CLIENT_LOGGER.error(f'Не удалось отправить информацию на сервер')

    def print_history(self):
        answer = input(f'Показать входящие сообщения - in, исходящие - out, все - Enter: ')
        with db_lock:
            if answer == 'in':
                history = self.database.get_history(to_user=self.account_name)
                for message in history:
                    print(f'Сообщение от пользователя {message[0]} от {message[3]}:{message[2]} ')
            elif answer == 'out':
                history = self.database.get_history(from_user=self.account_name)
                for message in history:
                    print(f'Сообщение пользователю {message[0]} от {message[3]}:{message[2]}')
            else:
                history = self.database.get_history()
                for message in history:
                    print(
                        f'Сообщение от пользователя {message[0]} пользователю {message[1]} от {message[3]}:{message[2]}')


class ClientReader(threading.Thread, metaclass=ClientVerifier):
    def __init__(self, account_name, sock, database):
        self.account_name = account_name
        self.sock = sock
        self.database = database
        super().__init__()

    def run(self):
        while True:
            time.sleep(1)
            with sock_lock:
                try:
                    message = get_message(self.sock)
                except IncorrectDataReceivedError:
                    CLIENT_LOGGER.error(f'Ошибка декодирования сообщения.')
                except (OSError, ConnectionError, ConnectionAbortedError, ConnectionResetError, json.JSONDecodeError):
                    CLIENT_LOGGER.critical(f'Потеряно соединение с сервером.')
                    break
                else:
                    if ACTION in message and message[ACTION] == MESSAGE and SENDER in message and DESTINATION in message \
                            and MESSAGE_TEXT in message and message[DESTINATION] == self.account_name:
                        print(f'\nСообщение от {message[SENDER]}: {message[MESSAGE_TEXT]}')
                        CLIENT_LOGGER.info(f'Получено сообщение от {message[SENDER]}: {message[MESSAGE_TEXT]}')
                        with db_lock:
                            try:
                                self.database.save_message(message[SENDER], self.account_name, message[MESSAGE_TEXT])
                            except Exception as e:
                                print(e)
                                CLIENT_LOGGER.error(f'Ошибка взаимодействия с БД')
                    else:
                        CLIENT_LOGGER.error(f'Получено некорректное сообщение {message}')

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


def users_list_request(sock, username):
    CLIENT_LOGGER.debug(f'Запрос списка известных пользователей {username}')
    request = {
        ACTION: USERS_REQUEST,
        TIME: time.time(),
        ACCOUNT_NAME: username
    }
    send_message(sock, request)
    answer = get_message(sock)
    if RESPONSE in answer and answer[RESPONSE] == 202:
        return answer[LIST_INFO]
    else:
        raise ServerError


def contacts_list_request(sock, username):
    CLIENT_LOGGER.debug(f'Запрос контактов пользователя {username}')
    request = {
        ACTION: GET_CONTACTS,
        TIME: time.time(),
        USER: username
    }
    send_message(sock, request)
    answer = get_message(sock)
    if RESPONSE in answer and answer[RESPONSE] == 202:
        return answer[LIST_INFO]
    else:
        raise ServerError


def add_contact(sock, username, contact):
    CLIENT_LOGGER.debug(f'Создание контакта')
    request = {
        ACTION: ADD_CONTACT,
        TIME: time.time(),
        USER: username,
        ACCOUNT_NAME: contact
    }
    send_message(sock, request)
    answer = get_message(sock)
    if RESPONSE in answer and answer[RESPONSE] == 200:
        pass
    else:
        raise ServerError(f'Ошибка создания контакта')
    print(f'Контакт удачно создан')


def remove_contact(sock, username, contact):
    CLIENT_LOGGER.debug(f'Удаление контакта {contact}')
    request = {
        ACTION: REMOVE_CONTACT,
        TIME: time.time(),
        USER: username,
        ACCOUNT_NAME: contact
    }
    send_message(sock, request)
    answer = get_message(sock)
    if RESPONSE in answer and answer[RESPONSE] == 200:
        pass
    else:
        raise ServerError('Ошибка удаления контакта')
    print('Контакт удачно удалён')


def database_load(sock, database, username):
    try:
        users_list = users_list_request(sock, username)
    except ServerError:
        CLIENT_LOGGER.error(f'Ошибка запроса списка известных пользователей')
    else:
        database.add_users(users_list)

    try:
        contacts_list = contacts_list_request(sock, username)
    except ServerError:
        CLIENT_LOGGER.error(f'Ошибка запроса списка контактов')
    else:
        for contact in contacts_list:
            database.add_contact(contact)


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
        transport.settimeout(1)
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
        database = ClientStorage(client_name)
        database_load(transport, database, client_name)
        # Соединение установлено. Запускаем процесс приёма сообщений
        receiver = ClientReader(account_name=client_name, sock=transport, database=database)
        receiver.daemon = True
        receiver.start()

        sender = ClientSender(account_name=client_name, sock=transport, database=database)
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
