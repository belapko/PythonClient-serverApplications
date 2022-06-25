import argparse
import configparser
import os
import select
import sys
import socket
import threading

from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import QApplication, QMessageBox

from common.variables import USER, ACTION, ACCOUNT_NAME, PRESENCE, TIME, ERROR, DEFAULT_PORT, MESSAGE, MESSAGE_TEXT, \
    SENDER, DESTINATION, RESPONSE_200, RESPONSE_400, EXIT, GET_CONTACTS, LIST_INFO, RESPONSE_202, ADD_CONTACT, \
    REMOVE_CONTACT, USERS_REQUEST
from common.utils import get_message, send_message
import logging
from server_db import ServerStorage
from descriptors import Port
from log_decorator import log
from metaclasses import ServerVerifier
from servgui import MainWindow, gui_create_model, ConfigWindow, HistoryWindow, create_stat_model

SERVER_LOGGER = logging.getLogger('server')

new_connection = False
conflag_lock = threading.Lock()


@log
def arg_parser(default_port, default_address):
    """Парсер аргументов командной строки"""
    parser = argparse.ArgumentParser()
    parser.add_argument('-p', default=default_port, type=int, nargs='?')
    parser.add_argument('-a', default=default_address, nargs='?')
    namespace = parser.parse_args(sys.argv[1:])
    listen_address = namespace.a
    listen_port = namespace.p
    return listen_address, listen_port


class Server(threading.Thread, metaclass=ServerVerifier):
    port = Port()

    def __init__(self, listen_address, listen_port, database):
        self.sock = None
        self.addr = listen_address
        self.port = listen_port
        self.clients = []  # Список подключенных клиентов
        self.messages = []
        self.names = dict()  # {client_name: client_socket}
        self.database = database
        super().__init__()

    def init_socket(self):
        SERVER_LOGGER.info(f'Порт для подключения к серверу: {self.port}\nАдрес сервера: {self.addr}')

        transport = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        transport.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        transport.bind((self.addr, self.port))
        transport.settimeout(0.5)

        self.sock = transport
        self.sock.listen()

    def run(self):
        self.init_socket()

        while True:
            # Ждём подключения, если таймаут вышел, ловим исключение.
            try:
                client, client_address = self.sock.accept()
            except OSError:
                pass
            else:
                SERVER_LOGGER.info(f'Установлено соединение с клиентом: {client_address}')
                self.clients.append(client)

            data_to_receive = []
            data_to_send = []
            errors_lst = []
            # Проверяем на наличие ждущих клиентов
            try:
                if self.clients:
                    data_to_receive, data_to_send, errors_lst = select.select(self.clients, self.clients, [], 0)
            except OSError:
                pass
            # принимаем сообщения и если ошибка, исключаем клиента
            if data_to_receive:
                for client_with_message in data_to_receive:
                    try:
                        self.process_client_message(get_message(client_with_message), client_with_message)
                    except Exception as e:
                        SERVER_LOGGER.info(f'Клиент {client_with_message.getpeername()} отключился.')
                        self.clients.remove(client_with_message)

            for message in self.messages:
                try:
                    self.process_message(message, data_to_send)
                except Exception as e:
                    SERVER_LOGGER.info(f'Связь с клиентом {message[DESTINATION]} была потеряна. Ошибка {e}')
                    self.clients.remove(self.names[message[DESTINATION]])
                    del self.names[message[DESTINATION]]
            self.messages.clear()

    # Функция адресной отправки сообщения определённому клиенту
    def process_message(self, message, listen_socks):
        if message[DESTINATION] in self.names and self.names[message[DESTINATION]] in listen_socks:
            send_message(self.names[message[DESTINATION]], message)
            SERVER_LOGGER.info(f'Отправлено сообщение пользователю: {message[DESTINATION]} от: {message[SENDER]}')
        elif message[DESTINATION] in self.names and self.names[message[DESTINATION]] not in listen_socks:
            raise ConnectionError
        else:
            SERVER_LOGGER.info(f'Пользователя {message[DESTINATION]} не существует. Отправка невозможна.')

    def process_client_message(self, message, client):
        global new_connection
        SERVER_LOGGER.debug(f'Разбор сообщения: {message} от клиента')
        if ACTION in message and message[ACTION] == PRESENCE and TIME in message and USER in message:
            # Регистрация пользователя, если такого ещё не существует
            if message[USER][ACCOUNT_NAME] not in self.names.keys():
                client_ip, client_port = client.getpeername()
                self.database.user_login(message[USER][ACCOUNT_NAME], client_ip, client_port)
                self.names[message[USER][ACCOUNT_NAME]] = client
                send_message(client, RESPONSE_200)
                with conflag_lock:
                    new_connection = True
            # Пользователь уже существует - отправляем ответ и завершаем соединение
            else:
                response = RESPONSE_400
                response[ERROR] = f'Такое имя уже занято.'
                send_message(client, response)
                self.clients.remove(client)
                client.close()
            return
        # Если пользователь отправил какое-то сообщение, то добавляем в очередь сообщений
        elif ACTION in message and message[ACTION] == MESSAGE \
                and DESTINATION in message and TIME in message and SENDER in message and MESSAGE_TEXT in message and \
                self.names[message[ACCOUNT_NAME]] == client:
            SERVER_LOGGER.info(f'Сообщение добавлено в очередь')
            self.messages.append(message)
            self.database.process_message(message[SENDER], message[DESTINATION])
            return
        # Если клиент хочет выйти, удаляем его из списка клиентов и закрываем соединение
        elif ACTION in message and message[ACTION] == EXIT and ACCOUNT_NAME in message and self.names[
            message[ACCOUNT_NAME]] == client:
            self.database.user_logout(message[ACCOUNT_NAME])
            self.clients.remove(self.names[message[ACCOUNT_NAME]])
            self.names[message[ACCOUNT_NAME]].close()
            SERVER_LOGGER.info(f'Клиент {self.names[message[ACCOUNT_NAME]]} вышел.')
            del self.names[message[ACCOUNT_NAME]]
            with conflag_lock:
                new_connection = True
            return
        # Запрос контактов
        elif ACTION in message and message[ACTION] == GET_CONTACTS and USER in message and self.names[
            message[USER]] == client:
            response = RESPONSE_202
            response[LIST_INFO] = self.database.get_contacts(message[USER])
            send_message(client, response)
        # Если добавление контакта
        elif ACTION in message and message[ACTION] == ADD_CONTACT and ACCOUNT_NAME in message and USER in message and \
                self.names[message[USER]] == client:
            self.database.add_contact(message[USER], message[ACCOUNT_NAME])
            send_message(client, RESPONSE_200)
        # Если удаление контакта
        elif ACTION in message and message[ACTION] == REMOVE_CONTACT and ACCOUNT_NAME in message and USER in message and \
                self.names[message[USER]] == client:
            self.database.remove_contact(message[USER], message[ACCOUNT_NAME])
            send_message(client, RESPONSE_200)
        # Запрос известных пользователей
        elif ACTION in message and message[ACTION] == USERS_REQUEST and ACCOUNT_NAME in message and self.names[
            message[ACCOUNT_NAME]] == client:
            response = RESPONSE_202
            response[LIST_INFO] = [name[0] for name in self.database.users_list()]
            send_message(client, response)
        # Если всё плохо и непонятно - Bad request
        else:
            response = RESPONSE_400
            response[ERROR] = f'Неверный запрос.'
            send_message(client, response)
            return


# def print_help():
#     print(f'Команды:')
#     print(f'users - все пользователи')
#     print(f'active - активные пользователи')
#     print(f'history - история')
#     print(f'exit - закрыть сервер')
#     print(f'help')
#

def main():
    config = configparser.ConfigParser()
    dir_path = os.path.dirname(os.path.realpath(__file__))
    config.read(f"{dir_path}/{'server.ini'}")
    listen_address, listen_port = arg_parser(
        config['SETTINGS']['Default_port'], config['SETTINGS']['Listen_Address'])
    database = ServerStorage(
        os.path.join(
            config['SETTINGS']['Database_path'],
            config['SETTINGS']['Database_file']))
    server = Server(listen_address, listen_port, database)
    server.daemon = True
    server.start()

    server_app = QApplication(sys.argv)
    main_window = MainWindow()

    main_window.statusBar().showMessage('Server Working')
    main_window.active_clients_table.setModel(gui_create_model(database))
    main_window.active_clients_table.resizeColumnsToContents()
    main_window.active_clients_table.resizeRowsToContents()

    # Функция, обновляющая список подключённых, проверяет флаг подключения, и
    # если надо обновляет список
    def list_update():
        global new_connection
        if new_connection:
            main_window.active_clients_table.setModel(
                gui_create_model(database))
            main_window.active_clients_table.resizeColumnsToContents()
            main_window.active_clients_table.resizeRowsToContents()
            with conflag_lock:
                new_connection = False

    # Функция, создающая окно со статистикой клиентов
    def show_statistics():
        global stat_window
        stat_window = HistoryWindow()
        stat_window.history_table.setModel(create_stat_model(database))
        stat_window.history_table.resizeColumnsToContents()
        stat_window.history_table.resizeRowsToContents()
        stat_window.show()

    def save_server_config():
        global config_window
        message = QMessageBox()
        config['SETTINGS']['Database_path'] = config_window.db_path.text()
        config['SETTINGS']['Database_file'] = config_window.db_file.text()
        try:
            port = int(config_window.port.text())
        except ValueError:
            message.warning(config_window, 'Ошибка', 'Порт должен быть числом')
        else:
            config['SETTINGS']['Listen_Address'] = config_window.ip.text()
            if 1023 < port < 65536:
                config['SETTINGS']['Default_port'] = str(port)
                print(port)
                with open('server.ini', 'w') as conf:
                    config.write(conf)
                    message.information(
                        config_window, 'OK', 'Настройки успешно сохранены!')
            else:
                message.warning(
                    config_window,
                    'Ошибка',
                    'Порт должен быть от 1024 до 65536')

    # Функция создающяя окно с настройками сервера.
    def server_config():
        global config_window
        # Создаём окно и заносим в него текущие параметры
        config_window = ConfigWindow()
        config_window.db_path.insert(config['SETTINGS']['Database_path'])
        config_window.db_file.insert(config['SETTINGS']['Database_file'])
        config_window.port.insert(config['SETTINGS']['Default_port'])
        config_window.ip.insert(config['SETTINGS']['Listen_Address'])
        config_window.save_btn.clicked.connect(save_server_config)



    # print_help()
    #
    # while True:
    #     command = input(f'Введите команду: ')
    #     if command == 'help':
    #         print_help()
    #     elif command == 'exit':
    #         break
    #     elif command == 'users':
    #         for user in sorted(database.users_list()):
    #             print(f'{user[0]}, last_login: {user[1]}')
    #     elif command == 'active':
    #         for user in sorted(database.active_users_list()):
    #             print(f'{user[0]}, подключен: {user[1]}:{user[2]}, login_time: {user[3]}')
    #     elif command == 'history':
    #         name = input(f'Для просмотра всей истории нажмите Enter\nИмя пользователя для просмотра его истории: ')
    #         for user in sorted(database.login_history_list(name)):
    #             print(f'{user[0]}, {user[2]}:{user[3]}, {user[1]}')
    #     else:
    #         print(f'Команда не распознана!')

    # Таймер, обновляющий список клиентов 1 раз в секунду
    timer = QTimer()
    timer.timeout.connect(list_update)
    timer.start(1000)

    # Связываем кнопки с процедурами
    main_window.refresh_button.triggered.connect(list_update)
    main_window.show_history_button.triggered.connect(show_statistics)
    main_window.config_btn.triggered.connect(server_config)

    # Запускаем GUI
    server_app.exec_()


if __name__ == '__main__':
    main()
